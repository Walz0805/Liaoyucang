# -*- coding: utf-8 -*-
import json
import random
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from _physiology_mock import channel_average, generate_physiology_payload, validate_schema

SEED = 20260819
PHYSIOLOGY_DURATION_SEC = 60
LEXICON_PATH = Path(__file__).with_name("_nlp_polarity_lexicon.json")
SCORING_DATA_DIR = Path(__file__).with_name("scoring_v2")
RECOMMENDATION_DATA_DIR = Path(__file__).with_name("recommendation")
random.seed(SEED)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def round3(x):
    return round(float(x), 3)


def load_polarity_lexicon():
    with LEXICON_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


POLARITY_LEXICON = load_polarity_lexicon()


def split_sentences(text):
    separators = "。！？!?；;\n"
    sentences = []
    current = []
    for char in text:
        if char in separators:
            if current:
                sentences.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        sentences.append("".join(current))
    return [sentence.strip(" ，,：:") for sentence in sentences if sentence.strip(" ，,：:")]


def find_non_overlapping_terms(text, terms):
    matches = []
    occupied = set()
    for term in sorted(terms, key=len, reverse=True):
        start = text.find(term)
        while start >= 0:
            positions = set(range(start, start + len(term)))
            if not positions.intersection(occupied):
                matches.append((start, term))
                occupied.update(positions)
            start = text.find(term, start + 1)
    return sorted(matches)


def analyze_text_polarity(text, lexicon):
    positive_terms = lexicon["positive_terms"]
    negative_terms = lexicon["negative_terms"]
    all_terms = {**positive_terms, **negative_terms}
    intensifiers = lexicon["intensifiers"]
    negations = lexicon["negations"]
    sentence_scores = []
    evidence = []

    for sentence in split_sentences(text):
        matches = find_non_overlapping_terms(sentence, all_terms)
        term_scores = []
        for start, term in matches:
            score = float(all_terms[term])
            context_start = max(0, start - 4)
            context = sentence[context_start:start]
            intensity = 1.0
            for word, factor in intensifiers.items():
                if word in context:
                    intensity = max(intensity, float(factor))
            negation = 1.0
            for word, factor in negations.items():
                if word in context:
                    negation = min(negation, float(factor))

            adjusted_score = clamp(score * intensity * negation, -1.0, 1.0)
            term_scores.append(adjusted_score)
            evidence.append(
                {
                    "sentence": sentence,
                    "term": term,
                    "base_score": round3(score),
                    "intensity": round3(intensity),
                    "negation": round3(negation),
                    "score": round3(adjusted_score),
                }
            )

        if term_scores:
            sentence_scores.append(sum(term_scores) / len(term_scores))

    if not sentence_scores:
        return {"polarity": 0.0, "confidence": 0.25, "evidence": []}

    polarity = clamp(sum(sentence_scores) / len(sentence_scores), -1.0, 1.0)
    evidence_coverage = min(1.0, len(evidence) / 3.0)
    confidence = 0.45 + 0.35 * evidence_coverage + 0.20 * min(1.0, len(sentence_scores) / 3.0)
    return {
        "polarity": round3(polarity),
        "confidence": round3(confidence),
        "evidence": evidence,
    }


def generate_series(target_avg, low, high, count, seed):
    """Generate a deterministic mock series constrained by an existing summary."""
    if count < 2 or low > high or not low <= target_avg <= high:
        raise ValueError("series bounds and target average are invalid")

    rng = random.Random(seed)
    span = high - low
    values = [
        clamp(rng.gauss(target_avg, max(span / 6.0, 1e-6)), low, high)
        for _ in range(count)
    ]
    values[0] = low
    values[1] = high

    # Adjust the interior values so the generated sequence remains close to the source average.
    for _ in range(20):
        residual = target_avg * count - sum(values)
        if abs(residual) < 1e-6:
            break
        adjustable = range(2, count)
        step = residual / (count - 2)
        for index in adjustable:
            values[index] = clamp(values[index] + step, low, high)

    return [round3(value) for value in values]


def calc_expression_valence(dist):
    # Positive: happy; Neutral: neutral; Negative: sadness/fear/disgust
    return (
        dist["happy"] * 1.0
        + dist["neutral"] * 0.0
        + dist["surprise"] * 0.1
        - dist["sadness"] * 1.0
        - dist["fear"] * 1.0
        - dist["disgust"] * 0.6
    )


def calc_dim6(phq9, theta):
    if phq9 >= 10 and theta < 15:
        return 0.2
    if 5 <= phq9 <= 9 and 15 <= theta <= 35:
        return 0.5
    if phq9 < 5 and theta > 20:
        return 0.8
    # fallback for mixed conditions
    if phq9 >= 10:
        return 0.3
    if phq9 >= 5:
        return 0.45
    return 0.7


def compute_user_vector(phq9, nlp_polarity, expr_dist, eeg, respiration_avg, keywords):
    expr_valence = calc_expression_valence(expr_dist)

    alpha_weight = 0.7
    dim1 = alpha_weight * nlp_polarity + (1 - alpha_weight) * expr_valence

    # Follow the provided formula in the framework file.
    dim2 = clamp((eeg["alpha"] - 10.0) / (50.0 - 10.0), 0.0, 1.0)
    if "易疲劳" in keywords:
        dim2 = min(1.0, dim2 + 0.2)

    dim3 = 1.0 - clamp((eeg["beta"] - 15.0) / (40.0 - 15.0), 0.0, 1.0)
    if respiration_avg > 22:
        dim3 *= 0.8

    dim4_base = phq9 / 27.0
    critical = any(k in keywords for k in ["自责", "无价值感", "绝望"])
    maintain = "能维持日常活动" in keywords
    if critical:
        dim4 = 1.0
    else:
        dim4 = dim4_base
        if maintain:
            dim4 *= 0.7

    dim5 = 1.0 - clamp((eeg["gamma"] - 5.0) / (20.0 - 5.0), 0.0, 1.0)
    if "注意力不集中" in keywords:
        dim5 = min(dim5, 0.3)

    dim6 = calc_dim6(phq9, eeg["theta"])

    return {
        "dim1_valence": round3(clamp(dim1, -1.0, 1.0)),
        "dim2_relaxation_inducibility": round3(clamp(dim2, 0.0, 1.0)),
        "dim3_arousal_tolerance": round3(clamp(dim3, 0.0, 1.0)),
        "dim4_safety_need": round3(clamp(dim4, 0.0, 1.0)),
        "dim5_visual_rhythm_tolerance": round3(clamp(dim5, 0.0, 1.0)),
        "dim6_function_orientation_need": round3(clamp(dim6, 0.0, 1.0)),
    }


def normalize_distribution(raw):
    s = sum(raw.values())
    if s == 0:
        return {k: 0.0 for k in raw}
    return {k: round3(v / s) for k, v in raw.items()}


def make_real_sample():
    keywords = ["情绪略低沉", "兴趣减退", "易疲劳", "偶有自责", "能维持日常活动"]
    summary = "存在轻度抑郁症状，情绪略低沉并伴随兴趣减退和易疲劳，偶有自责，但整体仍可维持基本日常活动。"
    polarity_result = analyze_text_polarity(summary, POLARITY_LEXICON)
    expr = normalize_distribution(
        {
            "happy": 0.32,
            "surprise": 0.14,
            "neutral": 0.08,
            "sadness": 0.25,
            "fear": 0.09,
            "disgust": 0.12,
        }
    )
    eeg = {
        "delta": 28.4,
        "theta": 31.2,
        "alpha": 30.6,
        "beta": 38.7,
        "gamma": 33.1,
    }
    physiology = generate_physiology_payload(
        {
            "heart_rate_avg": 73.4,
            "heart_rate_range": [62, 97],
            "respiration_avg": 18.7,
            "respiration_range": [11, 24],
            "temperature_avg": 36.91,
            "temperature_range": [36.3, 37.68],
        },
        seed=SEED + 1,
        eeg=eeg,
        expressions=expr,
    )

    return {
        "sample_id": "U001",
        "source_type": "real_extracted",
        "profile": {
            "subject_code": "100003",
            "name": "测试人员3",
            "gender": "女",
            "test_time": "2026-06-24 16:21:19",
            "health_status": "一般",
            "education_level": "未标注",
        },
        "scales": {
            "phq9_total": 9,
            "depression_level": "轻度抑郁症状",
        },
        "text_assessment": {
            "raw_text": summary,
            "summary": summary,
            "keywords": keywords,
            "nlp_polarity": polarity_result["polarity"],
            "polarity_model": {
                "version": POLARITY_LEXICON["version"],
                "confidence": polarity_result["confidence"],
                "evidence": polarity_result["evidence"],
            },
        },
        "physiology": physiology,
        "eeg_relative_power_percent": eeg,
        "expression_distribution": expr,
        "algorithm_features": {
            "user_state_vector": compute_user_vector(
                phq9=9,
                nlp_polarity=polarity_result["polarity"],
                expr_dist=expr,
                eeg=eeg,
                respiration_avg=18.7,
                keywords=keywords,
            ),
            "rule_flags": {
                "high_risk_keywords": True,
                "can_maintain_daily_activity": True,
                "attention_issue": False,
                "fatigue": True,
            },
        },
        "extraction_notes": {
            "from_pdf": "心理测评报告(1).pdf",
            "page_refs": [
                "page_1: 姓名与测试时间",
                "page_2: 生理与脑电曲线",
                "page_3: PHQ-9分数与评估文本",
            ],
            "note": "报告摘要及生理范围由图片版报告近似提取；连续传感器序列为基于摘要生成的结构化模拟数据。",
        },
    }


def random_keywords(phq9):
    pool_neg = ["情绪低落", "兴趣减退", "睡眠不稳", "易疲劳", "注意力不集中", "自责"]
    pool_pos = ["能维持日常活动", "愿意寻求帮助", "仍有社交", "可完成学习任务"]

    k = random.sample(pool_neg, k=random.randint(2, 4))
    if phq9 <= 10:
        k += random.sample(pool_pos, k=random.randint(1, 2))
    return list(dict.fromkeys(k))


def build_simulated_sample(idx):
    sample_id = f"U{idx:03d}"
    subject_code = f"1000{idx:02d}"

    test_time = datetime(2026, 6, 24, 14, 0, 0) + timedelta(hours=idx, minutes=random.randint(0, 45))
    gender = random.choice(["女", "男"])
    phq9 = random.randint(3, 18)

    if phq9 <= 4:
        level = "无明显抑郁"
    elif phq9 <= 9:
        level = "轻度抑郁症状"
    elif phq9 <= 14:
        level = "中度抑郁症状"
    else:
        level = "中重度抑郁症状"

    hr_low = random.randint(58, 68)
    hr_high = random.randint(85, 110)
    rr_low = random.randint(10, 14)
    rr_high = random.randint(18, 28)
    temp_low = round(random.uniform(36.1, 36.6), 2)
    temp_high = round(random.uniform(37.0, 37.8), 2)

    eeg = {
        "delta": round(random.uniform(12, 38), 1),
        "theta": round(random.uniform(10, 42), 1),
        "alpha": round(random.uniform(12, 46), 1),
        "beta": round(random.uniform(16, 55), 1),
        "gamma": round(random.uniform(8, 36), 1),
    }

    # Shape expression distribution according to mood severity.
    if phq9 >= 15:
        raw_expr = {
            "happy": random.uniform(0.05, 0.18),
            "surprise": random.uniform(0.05, 0.12),
            "neutral": random.uniform(0.06, 0.16),
            "sadness": random.uniform(0.28, 0.45),
            "fear": random.uniform(0.10, 0.20),
            "disgust": random.uniform(0.10, 0.18),
        }
    elif phq9 >= 10:
        raw_expr = {
            "happy": random.uniform(0.10, 0.24),
            "surprise": random.uniform(0.06, 0.14),
            "neutral": random.uniform(0.08, 0.20),
            "sadness": random.uniform(0.20, 0.35),
            "fear": random.uniform(0.08, 0.16),
            "disgust": random.uniform(0.08, 0.15),
        }
    else:
        raw_expr = {
            "happy": random.uniform(0.20, 0.40),
            "surprise": random.uniform(0.08, 0.18),
            "neutral": random.uniform(0.10, 0.22),
            "sadness": random.uniform(0.10, 0.25),
            "fear": random.uniform(0.04, 0.12),
            "disgust": random.uniform(0.04, 0.10),
        }

    expr = normalize_distribution(raw_expr)
    keywords = random_keywords(phq9)

    summary = "；".join(keywords)
    if phq9 >= 10:
        summary = "存在明显抑郁倾向，" + summary
    else:
        summary = "整体状态可维持，" + summary
    polarity_result = analyze_text_polarity(summary, POLARITY_LEXICON)
    nlp = polarity_result["polarity"]

    physiology_summary = {
        "heart_rate_avg": round((hr_low + hr_high) / 2 + random.uniform(-2.5, 2.5), 1),
        "heart_rate_range": [hr_low, hr_high],
        "respiration_avg": round((rr_low + rr_high) / 2 + random.uniform(-1.2, 1.2), 1),
        "respiration_range": [rr_low, rr_high],
        "temperature_avg": round((temp_low + temp_high) / 2 + random.uniform(-0.08, 0.08), 2),
        "temperature_range": [temp_low, temp_high],
    }
    physiology = generate_physiology_payload(
        physiology_summary,
        seed=SEED + idx * 100,
        eeg=eeg,
        expressions=expr,
        start_time=test_time,
    )

    return {
        "sample_id": sample_id,
        "source_type": "simulated",
        "profile": {
            "subject_code": subject_code,
            "name": f"模拟用户{idx}",
            "gender": gender,
            "test_time": test_time.strftime("%Y-%m-%d %H:%M:%S"),
            "health_status": random.choice(["一般", "较好", "易疲劳"]),
            "education_level": random.choice(["本科", "硕士", "未标注"]),
        },
        "scales": {
            "phq9_total": phq9,
            "depression_level": level,
        },
        "text_assessment": {
            "raw_text": summary,
            "summary": summary,
            "keywords": keywords,
            "nlp_polarity": round3(nlp),
            "polarity_model": {
                "version": POLARITY_LEXICON["version"],
                "confidence": polarity_result["confidence"],
                "evidence": polarity_result["evidence"],
            },
        },
        "physiology": physiology,
        "eeg_relative_power_percent": eeg,
        "expression_distribution": expr,
        "algorithm_features": {
            "user_state_vector": compute_user_vector(
                phq9=phq9,
                nlp_polarity=nlp,
                expr_dist=expr,
                eeg=eeg,
                respiration_avg=physiology_summary["respiration_avg"],
                keywords=keywords,
            ),
            "rule_flags": {
                "high_risk_keywords": any(k in keywords for k in ["自责", "绝望", "无价值感"]),
                "can_maintain_daily_activity": "能维持日常活动" in keywords,
                "attention_issue": "注意力不集中" in keywords,
                "fatigue": "易疲劳" in keywords,
            },
        },
    }


def generate_assessment_samples():
    samples = [make_real_sample()]
    for i in range(2, 11):
        samples.append(build_simulated_sample(i))

    return {
        "dataset": "psych_assessment_samples",
        "version": "v2_input_schema",
        "seed": SEED,
        "sample_count": len(samples),
        "physiology_schema": "channel_payload_v1",
        "vector_definition": "与初步算法框架中的6维用户状态向量一致",
        "samples": samples,
    }


AFTER_TEXTS = {
    "U001": "刚才情绪有些低落，现在平静了一些，呼吸也舒服了，但仍有一点疲惫。",
    "U002": "比刚才放松了一些，焦虑减轻了，不过还是有一点自责，我可以继续。",
    "U003": "现在比之前稳定一些，注意力比刚才集中了一点，但还有些紧张。",
    "U004": "感觉比刚才舒服多了，情绪平静了一些，愿意继续完成疗愈。",
    "U005": "和刚才相比没有明显变化，还是有些低落，但可以接受。",
    "U006": "比刚才平静了一些，虽然仍然疲惫，但现在感觉更安全。",
    "U007": "感觉好一点了，呼吸舒服了一些，不过情绪还是有些低落。",
    "U008": "现在比刚才放松，心情稳定了一些，我愿意继续。",
    "U009": "比刚才更焦虑，头晕而且不舒服，我无法继续。",
    "U010": "没有明显变化，还是有些紧张，但目前可以接受。",
}


def build_after_physiology(before_physiology, idx):
    before_hr = channel_average(before_physiology, "心率")
    before_rr = channel_average(before_physiology, "呼吸")
    before_temp = channel_average(before_physiology, "体温")

    if idx == 9:
        hr_avg, rr_avg = min(105.0, before_hr + 8.0), min(30.0, before_rr + 5.0)
        hr_width, rr_width = 35.0, 14.0
    elif idx in {5, 10}:
        hr_avg, rr_avg = before_hr, before_rr
        hr_width, rr_width = 25.0, 10.0
    else:
        hr_avg = 70.0 + (before_hr - 70.0) * 0.35
        rr_avg = 14.0 + (before_rr - 14.0) * 0.30
        hr_width, rr_width = 14.0, 6.0

    hr_low, hr_high = round(hr_avg - hr_width / 2, 1), round(hr_avg + hr_width / 2, 1)
    rr_low, rr_high = round(rr_avg - rr_width / 2, 1), round(rr_avg + rr_width / 2, 1)
    temp_avg = 36.7 + (before_temp - 36.7) * 0.30
    temp_low, temp_high = round(temp_avg - 0.12, 2), round(temp_avg + 0.12, 2)

    return generate_physiology_payload(
        {
            "heart_rate_avg": round(hr_avg, 1),
            "heart_rate_range": [hr_low, hr_high],
            "respiration_avg": round(rr_avg, 1),
            "respiration_range": [rr_low, rr_high],
            "temperature_avg": round(temp_avg, 2),
            "temperature_range": [temp_low, temp_high],
        },
        seed=SEED + 10000 + idx * 100,
        start_time=datetime(2026, 6, 24, 23, 0, 0),
    )


def build_after_sample(before_sample, idx):
    sample_id = before_sample["sample_id"]
    after = deepcopy(before_sample)
    after["sample_id"] = f"{sample_id}_after"
    after["before_sample_id"] = sample_id
    after["assessment_stage"] = "after"
    after["source_type"] = "simulated_after"
    after["profile"]["test_time"] = "2026-06-24 23:00:00"

    after["physiology"] = build_after_physiology(before_sample["physiology"], idx)
    after_text = AFTER_TEXTS[sample_id]
    polarity_result = analyze_text_polarity(after_text, POLARITY_LEXICON)
    after["text_assessment"] = {
        "raw_text": after_text,
        "summary": after_text,
        "keywords": [],
        "nlp_polarity": polarity_result["polarity"],
        "polarity_model": {
            "version": POLARITY_LEXICON["version"],
            "confidence": polarity_result["confidence"],
            "evidence": polarity_result["evidence"],
        },
    }

    # Keep PHQ-9 for seven paired cases; omit it for U008-U010 to test the optional path.
    if idx >= 8:
        after.pop("scales", None)

    after["extraction_notes"] = {
        "derived_from": sample_id,
        "note": "疗愈后模拟文本和生理数据，用于评分规则全流程测试。",
    }
    return after


def generate_after_assessment_samples(before_samples):
    samples = [build_after_sample(sample, idx) for idx, sample in enumerate(before_samples, start=1)]
    return {
        "dataset": "psych_assessment_after_samples",
        "version": "v2_input_schema",
        "seed": SEED + 10000,
        "sample_count": len(samples),
        "physiology_schema": "channel_payload_v1",
        "paired_before_dataset": "psych_assessment_samples_10.json",
        "samples": samples,
    }


def sample_vector_by_mode(mode):
    if mode == "安抚":
        return {
            "dim1_valence": random.uniform(-0.15, 0.75),
            "dim2_relaxation_inducibility": random.uniform(0.75, 1.0),
            "dim3_arousal": random.uniform(0.05, 0.35),
            "dim4_safety": random.uniform(0.85, 1.0),
            "dim5_visual_rhythm": random.uniform(0.02, 0.30),
            "dim6_function": random.uniform(0.00, 0.25),
        }
    if mode == "正念":
        return {
            "dim1_valence": random.uniform(0.0, 0.8),
            "dim2_relaxation_inducibility": random.uniform(0.55, 0.9),
            "dim3_arousal": random.uniform(0.15, 0.5),
            "dim4_safety": random.uniform(0.75, 0.95),
            "dim5_visual_rhythm": random.uniform(0.15, 0.45),
            "dim6_function": random.uniform(0.30, 0.55),
        }
    if mode == "认知重构":
        return {
            "dim1_valence": random.uniform(-0.10, 0.70),
            "dim2_relaxation_inducibility": random.uniform(0.35, 0.75),
            "dim3_arousal": random.uniform(0.30, 0.70),
            "dim4_safety": random.uniform(0.60, 0.90),
            "dim5_visual_rhythm": random.uniform(0.30, 0.65),
            "dim6_function": random.uniform(0.60, 0.85),
        }
    return {
        "dim1_valence": random.uniform(0.20, 1.00),
        "dim2_relaxation_inducibility": random.uniform(0.20, 0.60),
        "dim3_arousal": random.uniform(0.65, 1.00),
        "dim4_safety": random.uniform(0.55, 0.90),
        "dim5_visual_rhythm": random.uniform(0.65, 1.00),
        "dim6_function": random.uniform(0.90, 1.00),
    }


def generate_video_tags():
    counts = {
        "安抚": 18,
        "正念": 14,
        "认知重构": 10,
        "能量激活": 8,
    }

    scene_pool = {
        "安抚": ["海浪", "林间", "雨后", "云海", "篝火", "夜空"],
        "正念": ["呼吸引导", "身体扫描", "冥想室", "慢步行", "茶室", "湖畔"],
        "认知重构": ["隐喻动画", "心理教育", "叙事短片", "认知卡片", "对话引导"],
        "能量激活": ["晨光跑道", "跃动舞台", "山巅风景", "城市律动", "激励演讲"],
    }

    mood_pool = {
        "安抚": ["平静", "温暖", "安全", "放松", "舒缓"],
        "正念": ["专注", "觉察", "呼吸", "内观", "稳定"],
        "认知重构": ["理解", "重建", "接纳", "释义", "反思"],
        "能量激活": ["行动", "希望", "振奋", "启动", "积极"],
    }

    videos = []
    vid = 1
    mode_seq = {mode: 0 for mode in counts}
    for mode, n in counts.items():
        for _ in range(n):
            mode_seq[mode] += 1
            scene = random.choice(scene_pool[mode])
            moods = random.sample(mood_pool[mode], k=3)
            vec = sample_vector_by_mode(mode)
            vector = {k: round3(v) for k, v in vec.items()}

            videos.append(
                {
                    "video_id": f"V{vid:03d}",
                    "title": f"{mode}片段{mode_seq[mode]:02d}",
                    "scene_category": scene,
                    "function_tag": mode,
                    "mood_keywords": moods,
                    "duration_sec": random.randint(90, 520),
                    "vector": vector,
                    "safety_flags": {
                        "contains_sudden_transition": vector["dim5_visual_rhythm"] > 0.75,
                        "contains_dark_threatening_elements": vector["dim4_safety"] < 0.65,
                    },
                }
            )
            vid += 1

    return {
        "dataset": "video_tags_mock",
        "version": "v1",
        "seed": SEED,
        "video_count": len(videos),
        "vector_definition": "与初步算法框架中的6维视频标签向量一致",
        "videos": videos,
    }


def main():
    video_tags = generate_video_tags()
    assessment_samples = generate_assessment_samples()
    after_assessment_samples = generate_after_assessment_samples(assessment_samples["samples"])

    for sample in assessment_samples["samples"] + after_assessment_samples["samples"]:
        validate_schema(sample["physiology"])

    with (RECOMMENDATION_DATA_DIR / "video_tags_mock_50.json").open("w", encoding="utf-8") as f:
        json.dump(video_tags, f, ensure_ascii=False, indent=2)

    with (SCORING_DATA_DIR / "psych_assessment_before_samples_10.json").open("w", encoding="utf-8") as f:
        json.dump(assessment_samples, f, ensure_ascii=False, indent=2)

    with (SCORING_DATA_DIR / "psych_assessment_after_samples_10.json").open("w", encoding="utf-8") as f:
        json.dump(after_assessment_samples, f, ensure_ascii=False, indent=2)

    print(f"written: {RECOMMENDATION_DATA_DIR / 'video_tags_mock_50.json'}")
    print(f"written: {SCORING_DATA_DIR / 'psych_assessment_before_samples_10.json'}")
    print(f"written: {SCORING_DATA_DIR / 'psych_assessment_after_samples_10.json'}")


if __name__ == "__main__":
    main()
