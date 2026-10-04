# 派工：吸收包第三批 A3-T（降摩擦：工具返回瘦身、平面格式、参数可选值）

派工人：Opus 5.5。工作树 `.worktrees/astra-a3t`，分支 `dev/astra-a3t-20261004`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a3r` 做 A3-R（底座的缓存与流式），两包文件范围不重叠；`scripts/tool_scripts/` 与 `src/agent/runtime_tools.py` 归本包。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第三批 A3-T”一节交付。** 先读首次完整审查 [Opus 报告](../../reviews/2026-10-03_first_full_review/opus.md)的 L1、L3 两条与[汇总](../../reviews/2026-10-03_first_full_review/summary.md)第四节，以及 [10-04 节点回归记录](../2026-10-04_node_regression_a1/README.md)。行为记录与原始运行：节点回归 GLM 两次与 27B 摸底的压缩包在证据分支 `evidence/node-regression-a1-2026-10-04`（拼接与哈希见主线 `2026-10-04_node_regression_a1/evidence/`、`2026-10-04_qwen27b_probe/evidence/` 的清单）；T1 两次的行为记录在 `AI_agent/logs/experiments/2026-10-01_behaviour_records/records/2026-10-03_sm2{4,5}_glm_tools_t1/`；历史平面输入的重放材料在 `AI_agent/logs/experiments/2026-10-04_absorb_a1t/`。解包放本工作树的临时目录，用完删掉。

要点：
- A 是主要工作。挪字段前先按行为记录核对模型用没用到，宁可多留，不可挪掉模型确实在用的东西；两底座都要生效。
- B 的别名只收极少几个、一律注明；“不自动吸附”的原则不变。
- 改写给模型的文字坚持“替换不追加”，四项合计不得增加。
- 不改几何计算；不碰运行底座；0 次模型请求。
- 在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。同机还在跑整案，检查别开太多并发。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-04_absorb_a3t/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点没做完的，先保证 A 完整提交，其余已完成部分小步提交并在报告里写清剩余。最终回复按验收 A–E 给结果、逐工具改前改后的字符数、重放条数、新版本号、检查与提交列表。
