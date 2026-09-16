# 评分规则 v2

入口：`scoring_v2.py`；核心实现：`engine.py`；完整规则：`评分规则v2.md`。

推荐前只评分前测数据：

```powershell
python scoring_v2.py --mode befor --input psych_assessment_before_samples_10.json --output scoring_v2_results_befor.json
```

`scoring_v2_results_befor.json` 只包含 `before`，不会包含 `after` 或 `effect`。

推荐完成后，只读取后测原始数据，并读取已经保存的前测评分进行对比：

```powershell
python scoring_v2.py --mode after --input psych_assessment_after_samples_10.json --before-scores scoring_v2_results_befor.json --output scoring_v2_results_after.json
```

`scoring_v2_results_after.json` 包含前测评分、后测评分和 `effect` 对比，但不会重新读取前测原始数据。

输入生理字段使用与 `评估报告数据/生理数据.txt` 一致的 `data[]/dateValues[]` 通道结构。没有 IBI/RR 时 HRV 不计算；PHQ-9 仅保存在基线中；表情不进入评分，C/D/E 阶段明确标记不可用。
