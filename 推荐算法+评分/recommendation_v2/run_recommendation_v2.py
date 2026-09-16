"""Recommendation algorithm v2 driven by score_v2 output."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


FUNCTION_MODES = [(0.25, "安抚"), (0.55, "正念"), (0.85, "认知重构"), (1.01, "能量激活")]


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def value(mapping: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        raw = mapping.get(key)
        if isinstance(raw, (int, float)):
            return float(raw)
    return default


def mode_for_need(need: float) -> str:
    for upper, mode in FUNCTION_MODES:
        if need < upper:
            return mode
    return "安抚"


def baseline_values(context: Dict[str, Any]) -> Tuple[float, float, Set[str]]:
    phq9 = value(context, "phq9_total", "phq9", default=0.0)
    gad7 = value(context, "gad7_total", "gad7", default=0.0)
    risk_terms: Set[str] = set()
    for key in ("risk_terms", "keywords", "high_risk_keywords"):
        raw = context.get(key)
        if isinstance(raw, list): risk_terms.update(str(item) for item in raw)
    return phq9, gad7, risk_terms


def risk_profile(result: Dict[str, Any], stage: str) -> Dict[str, Any]:
    before = result.get("before", {})
    after = result.get("after", {})
    use_after = stage in {"after", "after_immersion"}
    selected = after if use_after else before
    flags = set(selected.get("risk_flags", []))
    if use_after:
        flags.update(result.get("effect", {}).get("risk_flags", []))
    context = dict(selected.get("baseline_context") or {})
    phq9, gad7, terms = baseline_values(context)
    terms.update(str(x) for x in context.get("high_risk_keywords", []) if isinstance(context.get("high_risk_keywords"), list))
    critical = bool(flags & {"critical_risk", "negative_reaction"})
    high = critical or phq9 >= 15 or gad7 >= 15 or bool(terms & {"绝望", "无价值感", "自责", "自伤", "自杀"})
    moderate = high or phq9 >= 10 or gad7 >= 10 or bool(flags & {"missing_data", "data_insufficient_for_change"})
    level = "critical" if critical else "high" if high else "moderate" if moderate else "normal"
    return {"level": level, "phq9": phq9, "gad7": gad7, "risk_flags": sorted(flags), "risk_terms": sorted(terms)}


def user_profile(result: Dict[str, Any], stage: str) -> Dict[str, Any]:
    risk = risk_profile(result, stage)
    state = result.get("after" if stage in {"after", "after_immersion"} else "before", {})
    components = state.get("state_components", {})
    physiology = value(components, "physiology", default=50.0)
    mood = components.get("mood")
    mood = float(mood) if isinstance(mood, (int, float)) else None
    risk_level = risk["level"]
    safe_need = min(1.0, 0.35 + risk["phq9"] / 27.0 * 0.45 + risk["gad7"] / 21.0 * 0.20)
    if risk_level in {"critical", "high"}: safe_need = max(safe_need, 0.85)
    relaxation_need = min(1.0, max(0.0, 1.0 - physiology / 100.0) + (0.25 if risk_level != "normal" else 0.0))
    arousal_limit = 0.35 if risk_level == "critical" else 0.50 if risk_level == "high" else 0.65 if risk_level == "moderate" else 0.85
    if mood is not None and mood < 40: relaxation_need = min(1.0, relaxation_need + 0.15)
    function_need = 0.20 if risk_level in {"critical", "high"} else 0.40 if relaxation_need >= 0.55 else 0.55
    return {
        "risk": risk, "risk_level": risk_level, "dim1_valence": ((mood or 50.0) / 50.0 - 1.0),
        "dim2_relaxation_need": relaxation_need, "dim3_arousal_limit": arousal_limit,
        "dim4_safety_need": safe_need, "dim5_visual_rhythm_limit": arousal_limit,
        "dim6_function_need": function_need, "source_metrics": state.get("used_metrics", []),
        "missing_metrics": state.get("missing_metrics", []),
        "expression_used": False if stage in {"C", "D", "E", "immersion", "after_immersion"} else True,
    }


def safety_filter(videos: Iterable[Dict[str, Any]], profile: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    level = profile["risk_level"]
    limit = profile["dim3_arousal_limit"]
    kept, blocked = [], {}
    for video in videos:
        reasons = []
        vector = video.get("vector", {})
        flags = video.get("safety_flags", {})
        if flags.get("contains_dark_threatening_elements"): reasons.append("dark_or_threatening")
        if flags.get("contains_flashing"): reasons.append("flashing")
        if float(vector.get("dim3_arousal", 0.0)) > limit: reasons.append("arousal_exceeds_limit")
        if level in {"critical", "high"} and video.get("function_tag") in {"认知重构", "能量激活"}: reasons.append("high_risk_function_blocked")
        if reasons: blocked[video.get("video_id", "")] = reasons
        else: kept.append(video)
    return kept, blocked


def function_recall(videos: List[Dict[str, Any]], target: str, profile: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool, str]:
    primary = [video for video in videos if video.get("function_tag") == target]
    if primary: return primary, False, target
    allowed = ["安抚", "正念"] if profile["risk_level"] in {"critical", "high"} else ["正念", "安抚", "认知重构", "能量激活"]
    for fallback in allowed:
        candidates = [video for video in videos if video.get("function_tag") == fallback]
        if candidates: return candidates, True, fallback
    return videos, True, "all_safe"


def similarity(video: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[float, List[str]]:
    vector = video.get("vector", {})
    valence = float(vector.get("dim1_valence", 0.0))
    relaxation = float(vector.get("dim2_relaxation_inducibility", 0.0))
    arousal = float(vector.get("dim3_arousal", 0.0))
    safety = float(vector.get("dim4_safety", 0.0))
    rhythm = float(vector.get("dim5_visual_rhythm", 0.0))
    function = float(vector.get("dim6_function", 0.0))
    valence_score = 1.0 - min(1.0, abs(valence - profile["dim1_valence"]) / 2.0)
    relaxation_score = 1.0 - abs(relaxation - profile["dim2_relaxation_need"])
    arousal_score = max(0.0, 1.0 - max(0.0, arousal - profile["dim3_arousal_limit"]) * 2.0)
    safety_score = safety * profile["dim4_safety_need"] + (1.0 - profile["dim4_safety_need"]) * 0.5
    rhythm_score = 1.0 - max(0.0, rhythm - profile["dim5_visual_rhythm_limit"])
    function_score = 1.0 - abs(function - profile["dim6_function_need"])
    score = 0.15 * valence_score + 0.20 * relaxation_score + 0.25 * arousal_score + 0.25 * safety_score + 0.10 * rhythm_score + 0.05 * function_score
    reasons = []
    if relaxation_score >= 0.8: reasons.append("放松诱导力匹配")
    if safety >= 0.85: reasons.append("高安全感")
    if arousal <= profile["dim3_arousal_limit"]: reasons.append("唤醒度在当前上限内")
    if rhythm <= profile["dim5_visual_rhythm_limit"]: reasons.append("视觉节奏适配")
    return score, reasons


def recommend(result: Dict[str, Any], videos: List[Dict[str, Any]], history: Dict[str, Any], stage: str, top_k: int) -> Dict[str, Any]:
    profile = user_profile(result, stage)
    safe, blocked = safety_filter(videos, profile)
    target = mode_for_need(profile["dim6_function_need"])
    recalled, fallback, recalled_mode = function_recall(safe, target, profile)
    played: Set[str] = set(history.get("played_video_ids", []))
    recent_scenes: Set[str] = set(history.get("recent_scene_categories", []))
    ranked = []
    history_filtered = 0
    for video in recalled:
        if video.get("video_id") in played:
            history_filtered += 1
            continue
        score, reasons = similarity(video, profile)
        if video.get("scene_category") in recent_scenes: score -= 0.08
        ranked.append((score, video, reasons))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = []
    used_scenes: Set[str] = set()
    for score, video, reasons in ranked:
        scene = video.get("scene_category", "")
        if scene in used_scenes and len(selected) < top_k: continue
        used_scenes.add(scene)
        selected.append({"rank": len(selected) + 1, "video_id": video["video_id"], "title": video.get("title"), "function_tag": video.get("function_tag"), "scene_category": scene, "score": round(score, 6), "reasons": reasons})
        if len(selected) >= top_k: break
    return {"risk_level": profile["risk_level"], "user_profile": profile, "target_function_mode": target, "recalled_function_mode": recalled_mode, "fallback_used": fallback, "recommendations": selected, "audit": {"blocked_videos": blocked, "history_filtered_count": history_filtered, "safe_candidate_count": len(safe), "recalled_count": len(recalled), "expression_used": profile["expression_used"]}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run recommendation algorithm v2")
    parser.add_argument("--scores", default="..\\scoring_v2\\scoring_v2_results_befor.json")
    parser.add_argument("--videos", default="video_tags_natural_scenery_v2.json")
    parser.add_argument("--history", default="")
    parser.add_argument("--stage", default="before", choices=["before", "after", "C", "D", "E", "immersion", "after_immersion"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default="recommendation_v2_results.json")
    args = parser.parse_args()
    scores, video_data = load_json(args.scores), load_json(args.videos)
    history = load_json(args.history) if args.history else {}
    results = []
    for item in scores.get("results", []):
        result = recommend(item, video_data.get("videos", []), history.get(item.get("before_sample_id"), history) if isinstance(history, dict) else {}, args.stage, args.top_k)
        results.append({"before_sample_id": item.get("before_sample_id"), "after_sample_id": item.get("after_sample_id"), **result})
    output = {"version": "recommendation_v2", "scores_file": args.scores, "videos_file": args.videos, "stage": args.stage, "video_count": len(video_data.get("videos", [])), "results": results}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {args.output}; users processed: {len(results)}")


if __name__ == "__main__": main()
