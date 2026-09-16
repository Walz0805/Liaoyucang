"""Scoring v2 engine for state scales and channel-oriented physiology data."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


VERSION = "score_v2"
CONFIG: Dict[str, Any] = {
    "state_weights": {"stai_s": 0.30, "mood": 0.25, "physiology": 0.35, "hrv": 0.10},
    "physiology_weights": {"heart_rate": 0.35, "respiration": 0.35, "eda": 0.30},
    "physiology_channels": {
        "heart_rate": {"labels": ["心率"], "date_types": [1], "valid_range": [30, 220], "target": [60, 80], "tolerance": [10, 20]},
        "respiration": {"labels": ["呼吸"], "date_types": [2], "valid_range": [4, 60], "target": [10, 18], "tolerance": [4, 8]},
        "eda": {"labels": ["皮电", "EDA", "GSR"], "date_types": [31], "valid_range": [0, 100], "target": [1, 10], "tolerance": [1, 15]},
        "temperature": {"labels": ["体温"], "date_types": [3], "valid_range": [30, 43]},
        "spo2": {"labels": ["血氧", "SpO2"], "date_types": [41], "valid_range": [70, 100]},
        "ibi": {"labels": ["IBI", "RR", "RR间期", "心搏间期"], "date_types": [6, 7], "valid_range": [300, 2000]},
    },
    "quality": {"min_valid_ratio": 0.80, "min_duration_sec": 30, "flat_repeat_ratio": 0.90, "min_hrv_intervals": 30},
    "hrv_lnrmssd_reference": [2.5, 4.5],
    "effect_thresholds": {"marked_improvement": 15, "mild_improvement": 5, "mild_decline": -5, "marked_decline": -15},
    "immersion_stages": ["C", "D", "E", "immersion", "after_immersion"],
}

NEGATIVE_REACTIONS = {
    "physical_discomfort": [r"强烈不适", r"严重头晕", r"胸闷加重", r"恶心", r"明显不舒服"],
    "emotional_worsening": [r"强烈恐慌", r"无法平复", r"情绪明显变差", r"明显恶化", r"更焦虑", r"更难受"],
    "session_interruption": [r"无法继续", r"必须停止", r"要求停止", r"想暂停"],
}


def finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def round3(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(float(value), 3)


def weighted_mean(values: Dict[str, Optional[float]], weights: Dict[str, float], keys: Optional[Iterable[str]] = None) -> Optional[float]:
    selected = list(keys if keys is not None else values)
    pairs = [(values[key], weights[key]) for key in selected if values.get(key) is not None and weights.get(key, 0) > 0]
    return None if not pairs else sum(value * weight for value, weight in pairs) / sum(weight for _, weight in pairs)


def interval_score(value: Optional[float], target: Sequence[float], tolerance: Sequence[float]) -> Optional[float]:
    if value is None:
        return None
    low, high = target
    if low <= value <= high:
        return 100.0
    distance = low - value if value < low else value - high
    margin = tolerance[0] if value < low else tolerance[1]
    return max(0.0, min(100.0, 100.0 * (1.0 - distance / margin)))


def parse_time(value: Any) -> Optional[float]:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})(?:\.(\d+))?", value.strip())
    if not match:
        return None
    hour, minute, second = map(int, match.group(1, 2, 3))
    fraction = float("0." + match.group(4)) if match.group(4) else 0.0
    return hour * 3600 + minute * 60 + second + fraction


def duration_seconds(points: Sequence[Dict[str, Any]]) -> Optional[float]:
    times = [parsed for point in points if (parsed := parse_time(point.get("time"))) is not None]
    if len(times) < 2:
        return None
    duration = max(times) - min(times)
    return duration + 86400 if duration < 0 else duration


def channel_map(physiology: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = physiology.get("data")
    return data if isinstance(data, list) else []


def find_channel(physiology: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    labels = {str(label).lower() for label in spec["labels"]}
    types = set(spec["date_types"])
    for channel in channel_map(physiology):
        if str(channel.get("label", "")).lower() in labels or channel.get("dateType") in types:
            return channel
    return None


def channel_values(channel: Optional[Dict[str, Any]], fields: Sequence[str] = ("value",)) -> List[float]:
    if not channel:
        return []
    values: List[float] = []
    for point in channel.get("dateValues", []):
        for field in fields:
            value = finite(point.get(field))
            if value is not None:
                values.append(value)
                break
    return values


def channel_statistics(channel: Optional[Dict[str, Any]], spec: Dict[str, Any], fields: Sequence[str] = ("value",)) -> Dict[str, Any]:
    raw = channel_values(channel, fields)
    low, high = spec["valid_range"]
    valid = [value for value in raw if low <= value <= high]
    ratio = len(valid) / len(raw) if raw else 0.0
    mean = sum(valid) / len(valid) if valid else None
    std = math.sqrt(sum((value - mean) ** 2 for value in valid) / len(valid)) if mean is not None else None
    repeat = sum(a == b for a, b in zip(valid, valid[1:])) / (len(valid) - 1) if len(valid) > 1 else None
    points = channel.get("dateValues", []) if channel else []
    return {
        "raw_count": len(raw), "valid_count": len(valid), "valid_ratio": round3(ratio),
        "duration_sec": round3(duration_seconds(points)), "mean": round3(mean), "std": round3(std),
        "adjacent_repeat_ratio": round3(repeat), "values": valid,
    }


def quality_flags(name: str, stats: Dict[str, Any]) -> List[str]:
    flags: List[str] = []
    if not stats["raw_count"]:
        return [f"missing_{name}"]
    if stats["valid_ratio"] < CONFIG["quality"]["min_valid_ratio"]:
        flags.append(f"low_valid_ratio_{name}")
    if stats["duration_sec"] is not None and stats["duration_sec"] < CONFIG["quality"]["min_duration_sec"]:
        flags.append("window_too_short")
    if stats["adjacent_repeat_ratio"] is not None and stats["adjacent_repeat_ratio"] >= CONFIG["quality"]["flat_repeat_ratio"]:
        flags.append(f"quantized_or_flat_{name}")
    return flags


def hrv_score(physiology: Dict[str, Any]) -> Dict[str, Any]:
    spec = CONFIG["physiology_channels"]["ibi"]
    channel = find_channel(physiology, spec)
    stats = channel_statistics(channel, spec)
    intervals = stats.pop("values")
    flags = [flag for flag in quality_flags("hrv", stats) if flag != "missing_hrv"]
    if len(intervals) < CONFIG["quality"]["min_hrv_intervals"] or stats["valid_ratio"] < CONFIG["quality"]["min_valid_ratio"]:
        return {"score": None, "rmssd_ms": None, "lnrmssd": None, "quality": stats, "risk_flags": sorted(set(flags + ["hrv_unavailable"]))}
    rmssd = math.sqrt(sum((right - left) ** 2 for left, right in zip(intervals, intervals[1:])) / (len(intervals) - 1))
    lnrmssd = math.log(rmssd) if rmssd > 0 else None
    low, high = CONFIG["hrv_lnrmssd_reference"]
    score = None if lnrmssd is None else max(0.0, min(100.0, (lnrmssd - low) / (high - low) * 100.0))
    return {"score": round3(score), "rmssd_ms": round3(rmssd), "lnrmssd": round3(lnrmssd), "quality": stats, "risk_flags": sorted(set(flags))}


def physiology_score(physiology: Dict[str, Any]) -> Dict[str, Any]:
    scores: Dict[str, Optional[float]] = {}
    components: Dict[str, Any] = {}
    flags: List[str] = []
    for name in ("heart_rate", "respiration", "eda"):
        spec = CONFIG["physiology_channels"][name]
        stats = channel_statistics(find_channel(physiology, spec), spec)
        stats.pop("values")
        flags.extend(quality_flags(name, stats))
        score = interval_score(stats["mean"], spec["target"], spec["tolerance"])
        if stats["valid_ratio"] < CONFIG["quality"]["min_valid_ratio"]:
            score = None
        scores[name] = round3(score)
        components[name] = {**stats, "score": round3(score)}

    for name in ("temperature", "spo2"):
        spec = CONFIG["physiology_channels"][name]
        stats = channel_statistics(find_channel(physiology, spec), spec)
        stats.pop("values")
        components[name] = stats
        if stats["raw_count"] and stats["valid_ratio"] < 1:
            flags.append(f"{name}_artifact_removed")
    score = weighted_mean(scores, CONFIG["physiology_weights"])
    return {"score": round3(score), "components": components, "used_metrics": [key for key, value in scores.items() if value is not None], "risk_flags": sorted(set(flags))}


def valid_range(value: Any, low: float, high: float) -> Optional[float]:
    number = finite(value)
    return number if number is not None and low <= number <= high else None


def state_measures(sample: Dict[str, Any]) -> Dict[str, Any]:
    source = sample.get("state_measures") or sample.get("state") or {}
    stai_raw = source.get("stai_s_total", source.get("stai_s"))
    stai = valid_range(stai_raw, 20, 80)
    vas_raw = source.get("vas_mood", source.get("vas_emotion"))
    vas = valid_range(vas_raw, 0, 10)
    sam_raw = source.get("sam_valence")
    sam = valid_range(sam_raw, 1, 9)
    sam_10_raw = source.get("sam_valence_0_10")
    sam_10 = valid_range(sam_10_raw, 0, 10)
    arousal = valid_range(source.get("sam_arousal"), 1, 9)
    arousal_10 = valid_range(source.get("sam_arousal_0_10"), 0, 10)
    stai_score = None if stai is None else (80 - stai) / 60 * 100
    mood_candidates = []
    if vas is not None: mood_candidates.append(("vas_mood", vas * 10))
    if sam is not None: mood_candidates.append(("sam_valence", (sam - 1) / 8 * 100))
    if sam_10 is not None: mood_candidates.append(("sam_valence_0_10", sam_10 * 10))
    mood_score = sum(value for _, value in mood_candidates) / len(mood_candidates) if mood_candidates else None
    invalid = []
    for name, raw, parsed in (("stai_s", stai_raw, stai), ("vas_mood", vas_raw, vas), ("sam_valence", sam_raw, sam), ("sam_valence_0_10", sam_10_raw, sam_10)):
        if raw is not None and parsed is None: invalid.append(name)
    return {
        "scores": {"stai_s": round3(stai_score), "mood": round3(mood_score)},
        "raw": {"stai_s": stai_raw, "vas_mood": vas_raw, "sam_valence": sam_raw, "sam_valence_0_10": sam_10_raw, "sam_arousal": arousal, "sam_arousal_0_10": arousal_10},
        "mood_sources": [name for name, _ in mood_candidates], "invalid_fields": invalid,
    }


def baseline_context(sample: Dict[str, Any]) -> Dict[str, Any]:
    context = dict(sample.get("baseline_context") or {})
    context.update(sample.get("scales") or {})
    for key in ("stai_s", "stai_s_total", "vas_mood", "vas_emotion", "sam_valence", "sam_arousal"):
        context.pop(key, None)
    return context


def feedback_risk(sample: Dict[str, Any]) -> Dict[str, Any]:
    assessment = sample.get("text_assessment") or {}
    text = str(assessment.get("raw_text") or assessment.get("summary") or "")
    evidence: Dict[str, List[str]] = {}
    for category, patterns in NEGATIVE_REACTIONS.items():
        matches = [match.group(0) for pattern in patterns if (match := re.search(pattern, text))]
        if matches: evidence[category] = matches
    flags: List[str] = []
    if evidence: flags.append("negative_reaction")
    if "session_interruption" in evidence or "physical_discomfort" in evidence: flags.append("critical_risk")
    return {"text_present": bool(text), "evidence": evidence, "risk_flags": flags}


def is_immersion(stage: Any) -> bool:
    return str(stage).strip() in set(CONFIG["immersion_stages"])


def score_sample(sample: Dict[str, Any], stage: str) -> Dict[str, Any]:
    measures = state_measures(sample)
    physiology = physiology_score(sample.get("physiology") or {})
    hrv = hrv_score(sample.get("physiology") or {})
    component_scores = {"stai_s": measures["scores"]["stai_s"], "mood": measures["scores"]["mood"], "physiology": physiology["score"], "hrv": hrv["score"]}
    flags = physiology["risk_flags"] + hrv["risk_flags"]
    if measures["invalid_fields"]: flags.append("invalid_input")
    if is_immersion(stage): flags.append("expression_unavailable_in_immersion")
    feedback = feedback_risk(sample)
    flags.extend(feedback["risk_flags"])
    used = [key for key, value in component_scores.items() if value is not None]
    missing = [key for key, value in component_scores.items() if value is None]
    if not used: flags.extend(["missing_data", "invalid_input"])
    score = weighted_mean(component_scores, CONFIG["state_weights"])
    return {
        "stage": stage, "state_score": round3(score), "state_components": component_scores,
        "raw_state_measures": measures["raw"], "mood_sources": measures["mood_sources"],
        "sam_arousal": measures["raw"]["sam_arousal"], "sam_arousal_0_10": measures["raw"]["sam_arousal_0_10"],
        "baseline_context": baseline_context(sample), "physiology": physiology, "hrv": hrv,
        "immediate_feedback": feedback, "used_metrics": used, "missing_metrics": missing,
        "risk_flags": sorted(set(flags)), "data_quality": "invalid" if not used else "good" if len(used) >= 3 else "fair",
    }


def effect_label(change: Optional[float]) -> str:
    if change is None: return "不可比较"
    limits = CONFIG["effect_thresholds"]
    if change >= limits["marked_improvement"]: return "明显改善"
    if change >= limits["mild_improvement"]: return "轻度改善"
    if change > limits["mild_decline"]: return "基本稳定"
    if change > limits["marked_decline"]: return "轻度下降"
    return "明显下降"


def compare(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    common = [key for key in CONFIG["state_weights"] if before["state_components"].get(key) is not None and after["state_components"].get(key) is not None]
    before_common = weighted_mean(before["state_components"], CONFIG["state_weights"], common)
    after_common = weighted_mean(after["state_components"], CONFIG["state_weights"], common)
    change = None if before_common is None or after_common is None else after_common - before_common
    flags = before["risk_flags"] + after["risk_flags"]
    if change is None: flags.append("data_insufficient_for_change")
    return {
        "change_score": round3(change), "state_change": round3(change), "before_common_score": round3(before_common),
        "after_common_score": round3(after_common), "common_metrics": common,
        "metric_set_equal": before["used_metrics"] == after["used_metrics"], "phq9_change": None,
        "label": effect_label(change), "comparable": change is not None, "risk_flags": sorted(set(flags)),
    }


def load_document(path: str) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    start = text.find("{")
    if start < 0: raise ValueError(f"No JSON object in {path}")
    return json.loads(text[start:])


def samples(document: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
    if isinstance(document.get("samples"), list): return document["samples"]
    if isinstance(document.get("data"), list): return [{"sample_id": Path(path).stem, "physiology": document}]
    raise ValueError(f"Unsupported input structure: {path}")


def score_before(input_path: str) -> Dict[str, Any]:
    before_samples = samples(load_document(input_path), input_path)
    results = []
    for sample in before_samples:
        before_result = score_sample(sample, sample.get("assessment_stage", "before"))
        results.append({"before_sample_id": sample["sample_id"], "before": before_result})
    return {
        "version": VERSION,
        "stage": "befor",
        "input_file": input_path,
        "config": CONFIG,
        "sample_count": len(results),
        "results": results,
    }


def score_after(input_path: str, before_scores_path: str) -> Dict[str, Any]:
    after_samples = samples(load_document(input_path), input_path)
    before_document = load_document(before_scores_path)
    if before_document.get("version") != VERSION or before_document.get("stage") not in {"befor", "before"}:
        raise ValueError("--before-scores must be a score_v2 befor-stage result")
    before_map = {
        item["before_sample_id"]: item["before"]
        for item in before_document.get("results", [])
        if item.get("before_sample_id") and isinstance(item.get("before"), dict)
    }
    results = []
    for index, sample in enumerate(after_samples):
        before_id = sample.get("before_sample_id")
        if before_id is None and len(before_map) == len(after_samples):
            before_id = list(before_map)[index]
        if before_id not in before_map:
            continue
        after_result = score_sample(sample, sample.get("assessment_stage", "after"))
        before_result = before_map[before_id]
        results.append({
            "before_sample_id": before_id,
            "after_sample_id": sample.get("sample_id"),
            "before": before_result,
            "after": after_result,
            "effect": compare(before_result, after_result),
        })
    return {
        "version": VERSION,
        "stage": "after",
        "input_file": input_path,
        "before_scores_file": before_scores_path,
        "config": CONFIG,
        "sample_count": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run therapy scoring rule v2")
    parser.add_argument("--mode", required=True, choices=["befor", "before", "after"])
    parser.add_argument("--input", required=True, help="the dataset for the selected stage")
    parser.add_argument("--before-scores", help="befor-stage score JSON; required in after mode")
    parser.add_argument("--output", help="output JSON path")
    args = parser.parse_args()
    mode = "befor" if args.mode == "before" else args.mode
    if mode == "befor":
        output = score_before(args.input)
        output_path = args.output or "scoring_v2_results_befor.json"
    else:
        if not args.before_scores:
            parser.error("--before-scores is required in after mode")
        output = score_after(args.input, args.before_scores)
        output_path = args.output or "scoring_v2_results_after.json"
    Path(output_path).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {output_path}; stage: {mode}; samples: {output['sample_count']}")
