# sm25 连续走廊缺口辅助修复

[三维源模型](viewer.html) · [独立分区对照](partition.html) · [开口及未完成项](index.html) · [辅助判读输入](../2026-09-09_m0_wall_gap_review_inputs/README.md)

实现提交 `dcbf4a81`，独立新 run。复用冻结 reading/编墙决定，开发助手直接查看两张原始平面图后补充三条连续空间决定；没有修改原始图纸、reading、旧候选或 GT。未重新运行产品读图模型、模型 judge 或 EnergyPlus；不属于冷启动成绩。

```sh
python scripts/tool_scripts/diagnose_reading_openings.py --out AI_agent/logs/experiments/2026-09-09_m0_wall_gap_review_run01 --rebuild-partitions --wall-gap-decisions AI_agent/logs/experiments/2026-09-09_m0_wall_gap_review_inputs/reviews.json
python AI_agent/logs/experiments/2026-09-09_m0_wall_gap_review_run01/validate_artifacts.py
```

第一条命令要求新目录；重做须换独立目录，不能覆盖本 run。

| 项目 | 前一程端点修复候选 | 本程辅助修复 |
|---|---:|---:|
| 空间 | 32（16 / 16） | 29（14 / 15） |
| 面 | 236 | 223 |
| 窗 | 31 | 31，最终三维顶点逐一相同 |
| 门/空开口 | 29 门 + 1 空开口 | 29 门 |
| 开口派生片 | 57 | 55 |
| 明确正观测 | 61 | 61，全部一次记账 |
| 未建门组 | 2 | 2，继续阻塞完整性 |

原 L042g0 passage 位置在同一连续走廊内，明确改判为连续源空间，没有横穿走廊的宿主墙；旧分类、图像/读图来源和理由保存在 [改判台账](opening_account.json)。61 条正观测对应 29 建成、29 已建重复、2 未建、1 改判，没有静默省略。

三条决定只拆开原编墙对象的连续分组，原实墙段几何不改；真实门窗所在边界仍可续接。坐标由冻结墙线推导，不填 GT 坐标或人工房间列表。来源配方与候选同步保存，实际 writer 已独立重建并验证全部候选；校正状态仍未接受。

[独立评价](partition_evidence.json) 只在模型生成后读 GT：两层内部边界缺失/额外长度均为 0，没有拆并发现；原始外边界/参考面差异完整保留，整体为 not_evaluated，不宣称全部通过。一般 as-drawn 独立墙面语义评价仍未接入。

[产物验证](artifact_validation.json)：31 窗三维顶点保留、55 张扣洞墙的可见面积差为 0、4 段查看器脚本语法通过、源映射通过、正观测全部记账。尚未验证浏览器实际渲染与交互。两组门、两条 65 mm 短边、门高假设 2.1 m、门状态未知、Stage 2 正式确认与新门洞 EP 出口仍保留。

本 run 的诊断 CLI 同时包含从最早 27 空间档案起算的端点修复，所以 report 的旧新数量为 27 → 29；上表独立选择前一程 32 空间产物，专门比较本程补线变化。原图辅助判读的三条决定已单独记账，不将本程包装成自动分区恢复。
