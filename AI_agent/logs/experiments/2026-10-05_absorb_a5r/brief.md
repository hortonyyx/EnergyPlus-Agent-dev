# 派工：吸收包第五批 A5-R（两底座共用输入准备、评价侧约定差）

派工人：Opus 5.5。工作树 `.worktrees/astra-a5r`，分支 `dev/astra-a5r-20261005`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a5t` 做 A5-T；**文件归属**：本包只改新的共用输入模块、`src/agent/runtime_entry.py`、`src/agent/runtime_context.py`、`scripts/tool_scripts/run_bim_agent.py` 里**只限 `run_experiment` 函数**、`scripts/tool_scripts/evaluate_bim_agent.py`、`src/agent/judge/` 与对应测试；工具目录、指引、命名、`agent_versions.json` 归 A5-T。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第五批 A5-R”一节交付。** 这是分界前最后一批底座与评价侧吸收项。先读[首次完整审查](../../reviews/2026-10-03_first_full_review/opus.md)的 L4、`AI_agent/design/evaluation.md` 的约定差一节、`AI_agent/design/model.md` 的 10-02 规整原则，以及 `AI_agent/logs/experiments/2026-10-04_node_regression_a1/evaluate_runtime.py`（`compat_view` 现在补了哪些字段）。重评用的运行：10-04 节点回归与两次 27B（证据分支 `evidence/node-regression-a1-2026-10-04` 与主线压缩包，哈希清单在各实验目录 `evidence/`）、10-01 亲做三例。解包放本工作树的临时目录，用完删掉。

要点：
- A 不能让 Claude Code 线跑不起来；历史运行的评分照旧可用。
- B 参照照图不改；约定差只限 `evaluation.md` 写明的类别与容差，超出容差或改变房间、门窗、连通的照旧报告。
- 0 次模型请求；凭据不打印、不入仓。在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-05_absorb_a5r/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点没做完的，已完成部分小步提交并在报告里写清剩余。最终回复按验收 A–C 给结果、重评的差异清单、检查与提交列表。
