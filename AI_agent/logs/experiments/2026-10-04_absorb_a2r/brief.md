# 派工：吸收包第二批 A2-R（运行目录瘦身与稳健性小项）

派工人：Opus 5.5。工作树 `.worktrees/astra-a2r`，分支 `dev/astra-a2r-20261004`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a2t` 做 A2-T（工具与依据），两包文件范围不重叠；`src/agent/runtime_tools.py` 归 A2-T，本包不碰 `scripts/tool_scripts/`。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第二批 A2-R”一节交付。** 先读 [A1-R 报告](../2026-10-04_absorb_a1r/README.md)（体积一节）与 [C1 验收](../../../project/unified_agent_acceptance.md)里的失败分类。节点回归新底座的原始运行在证据分支 `evidence/node-regression-2026-10-04`（拼接说明见主线 `AI_agent/logs/experiments/2026-10-04_node_regression_c2/evidence/`）；本次节点回归（`AI_agent/logs/experiments/2026-10-04_node_regression_a1/runs/`，主工作树里、被忽略）跑完的运行也可以只读取用，不要改动它。解包放本工作树的临时目录，用完删掉。

要点：
- A 是主要工作：先量清楚体积来自哪里，再改；恢复运行与请求逐字节重建不能受影响。
- B 只依据官方文档和已存的真实错误正文判断，拿不准的照停，不猜。
- 0 次模型请求；凭据不打印、不入仓。
- 在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。同机还在跑整案，检查别开太多并发。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-04_absorb_a2r/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 100 分钟内交付；到点没做完的，已完成部分小步提交并在报告里写清剩余。最终回复按验收 A–E 给结果、改前改后的体积、反例条数、检查与提交列表。
