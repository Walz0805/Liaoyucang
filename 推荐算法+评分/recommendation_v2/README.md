# 推荐算法 v2

推荐 v2 使用 `score_v2` 的状态、基线和风险输出，并读取 `video_tags_natural_scenery_v2.json`。

```powershell
python run_recommendation_v2.py `
  --scores ..\scoring_v2\scoring_v2_results_befor.json `
  --videos video_tags_natural_scenery_v2.json `
  --stage before `
  --output recommendation_v2_results.json
```

核心行为：

- `baseline_context` 用于安全门控和长期个性化；
- `state_components` 用于当前会话匹配；
- `critical_risk`/`negative_reaction` 触发保守过滤；
- C/D/E/沉浸阶段不使用表情；
- 缺失状态量表时使用生理和基线并保守降级；
- 按用户历史视频去重，并做场景多样性重排；
- 输出过滤原因、缺失指标、回退模式和推荐理由。
