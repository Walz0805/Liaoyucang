import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "推荐算法+评分"
RECOMMENDATION = SOURCE / "recommendation_v2"
SCORING = SOURCE / "scoring_v2"
LIBRARY = SOURCE / "星璇律动VR -- 视频素材库" / "自然风景"
VIDEO_OUT = ROOT / "assets" / "video" / "library"
DATA_OUT = ROOT / "assets" / "data"

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def main():
    VIDEO_OUT.mkdir(parents=True, exist_ok=True)
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    tags = read_json(RECOMMENDATION / "video_tags_natural_scenery_v2.json")
    recommendations = read_json(RECOMMENDATION / "recommendation_v2_results.json")
    scores = read_json(SCORING / "scoring_v2_results_befor.json")
    samples = read_json(SCORING / "psych_assessment_before_samples_10.json")

    recommendation_by_id = {item["before_sample_id"]: item for item in recommendations["results"]}
    score_by_id = {item["before_sample_id"]: item["before"] for item in scores["results"]}
    source_by_id = {item["sample_id"]: item.get("source_type", "unknown") for item in samples["samples"]}

    videos = []
    for item in tags["videos"]:
        source_file = LIBRARY / item["file_name"]
        if not source_file.exists():
            raise FileNotFoundError(source_file)
        shutil.copy2(source_file, VIDEO_OUT / item["file_name"])
        videos.append({
            "videoId": item["video_id"],
            "fileName": item["file_name"],
            "title": item["title"],
            "sceneCategory": item["scene_category"],
            "functionTag": item["function_tag"],
            "contentKeywords": item.get("content_keywords", []),
            "moodKeywords": item.get("mood_keywords", []),
            "vector": item["vector"],
            "safetyFlags": item["safety_flags"],
            "url": f"assets/video/library/{item['file_name']}"
        })

    compact_samples = []
    for sample_id, recommendation in recommendation_by_id.items():
        compact_samples.append({
            "sampleId": sample_id,
            "sourceType": source_by_id.get(sample_id, "unknown"),
            "score": score_by_id.get(sample_id),
            "recommendation": recommendation
        })

    catalog = {
        "version": "recommendation_catalog_v2",
        "defaultSampleId": "U002",
        "notes": "U001 is the real extracted pretest; all other pretests and every posttest are simulated.",
        "videos": videos,
        "samples": compact_samples
    }
    (DATA_OUT / "recommendation-catalog-v2.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"catalog: {len(compact_samples)} samples, {len(videos)} videos")

if __name__ == "__main__":
    main()
