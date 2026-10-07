# 提速第一步：思考档位实测（10-07，Opus）

**依据：** 用户 10-07：“思考档位这个事情你动态来判断吧，因为要靠测试和行为来判断”“目前时间太久了，几个小时完全无法接受”。GLM 订阅开发调试，Agent.md 已授权；不是节点对照。

**迭代范围：** 只改运行设置（各角色的思考档），不改 runtime、domain 代码。Agent 版本 `t1-20261007-n1.1`（D1j、D1k、RT1、N1 合入后）。

**为什么先测这个：**
- 三例对照里，分工模式的关键路径是平面读图员，它约九成时间花在第一次试建之前反复看图：sm24 第 1.4 分钟开工、第 15.1 分钟才首次试建；sm21 两层分别到第 24.1、19.9 分钟。
- 每次请求 45–72 秒，主要是 medium 档的思考。
- 10-03 同一请求实测：low 13–44 秒，medium 74 秒，high 140 秒（[标定](../2026-10-03_migration_comparison/subscription_effort_calibration.json)）。整案此前从未在 low 跑过。

**条件：** 配置 [speed_effort.json](speed_effort.json)，从 [三例对照](../2026-10-07_three_case_comparison/README.md) 的 sm24 两个案例复制，只改思考档、版本和时限（每次 1 小时保护线）。从 D 盘固定提交的运行工作树依次跑，一次一个整案。

| 案例 | 模式 | 思考档 | 对照（10-07 medium） |
|---|---|---|---|
| `sm24_role_low` | 分工 | 全部 low | sm24 分工 23.0 分钟 |
| `sm24_single_low` | 单模型 | low | sm24 单模型 35.7 分钟 |
| `sm24_role_readers_low` | 分工 | 读图员 low，调度员 medium | 视前两次结果决定跑不跑 |

**看点：** 用时与关键路径（平面读图员首次试建时刻、交付时刻，调度员收尾）；质量按 5/10/30 三档与实质错误，不得比 medium 差；请求数、token。

## 结果（10-07 22:06–22:30，只跑了 `sm24_role_low`）

| 运行 | 用时 | 请求 | 空间 | 实质错误 | 门窗位置 ≤5／5–10／10–30／>30 cm | 外墙高度 |
|---|---|---|---|---|---|---|
| sm24 分工全 low | 23.3 分钟 | 61 | 8/8/8 | 多 1 扇门窗 | 4／7／4／**6** | 14/14 在 5 cm 内 |
| 对照：10-07 sm24 分工 medium | 23.0 分钟 | 59 | 8/8/8 | 无 | 14／3／4／0 | 14/14 |

成果查看：[平面图](../../../archive/local_backup/speed/sm24_role_low/dev_evaluation/display/plan_F1.png)、回叠图 [平面](../../../archive/local_backup/speed/sm24_role_low/dev_evaluation/overlays/plan_F1.png)、[南](../../../archive/local_backup/speed/sm24_role_low/dev_evaluation/overlays/elevation_South.png)、[东](../../../archive/local_backup/speed/sm24_role_low/dev_evaluation/overlays/elevation_East.png)（北、西两面运行中没有登记立面标定，补不出）、[BIM 查看页](../../../archive/local_backup/speed/sm24_role_low/dev_evaluation/display/viewer.html)。

**行为观察：** 平面读图员每次请求中位 17 秒（medium 约 45 秒），但请求 28 次、第 11.2 分钟首次试建、第 16.2 分钟交出（medium 15.1／18.0 分钟），只快了约 2 分钟；四个立面读图员 2–4 分钟交出、高度全对；调度员 4.3 分钟模型用时，交付 22.7 分钟。整案没有变快，是因为平面读图员想得少了、看得更多，且调度员收尾时间不变。

**结论（思考档由 Opus 按实测定）：** 平面读图员不能用 low——6 扇门窗沿墙偏差超过 30 cm，正是精度三档里要专门处理的那一档。立面读图员在 low 下质量未见下降，但不在关键路径上，降档省不了时间。思考档不是提速的主要杠杆；`sm24_single_low`、`sm24_role_readers_low` 不再跑，提速转向平面读图员的做法（D1l，以 Sonnet 5.5 标杆的做法为范本）。
