# 派工：吸收包第二批 A2-T（依据手续合并、高度覆盖合一）

派工人：Opus 5.5。工作树 `.worktrees/astra-a2t`，分支 `dev/astra-a2t-20261004`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a2r` 做 A2-R（底座），两包文件范围不重叠；`src/agent/runtime_tools.py` 归本包。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第二批 A2-T”一节交付。** 先读首次完整审查的 [Astra 报告](../../reviews/2026-10-03_first_full_review/astra.md) 2.3 节与[汇总](../../reviews/2026-10-03_first_full_review/summary.md)第一、四节里关于依据和高度覆盖的条目。T1 sm25（审查里的 T25）与 sm24（T24）的完整行为记录在 `AI_agent/logs/experiments/2026-10-01_behaviour_records/records/2026-10-03_sm2{4,5}_glm_tools_t1/`；节点回归新底座两次的原始运行在证据分支 `evidence/node-regression-2026-10-04`（拼接说明见主线 `AI_agent/logs/experiments/2026-10-04_node_regression_c2/evidence/`）。解包放本工作树的临时目录，用完删掉。

要点：
- 先做 A（依据），再做 B（高度表）。版本检查是为防止依据被错继承，只放宽“目标确实没变”的情形，宁可多作废，不可错继承。
- 改写给模型的文字坚持“替换不追加”，写明针对哪次失败；四项合计不得增加。
- 不改几何内核的计算方式；不碰运行底座；0 次模型请求。
- 在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。同机还在跑整案，检查别开太多并发。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-04_absorb_a2t/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点 B 没做完，先保证 A 完整提交，B 已完成的部分小步提交并在报告里写清剩余。最终回复按验收 A–E 给结果、重放与反例条数、改前改后的数字、新版本号、检查与提交列表。
