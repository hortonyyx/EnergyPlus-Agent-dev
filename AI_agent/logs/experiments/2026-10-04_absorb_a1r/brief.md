# 派工：吸收包第一批 A1-R（图片按引用保存、智谱 Anthropic 兼容线路）

派工人：Opus 5.5。工作树 `.worktrees/astra-a1r`，分支 `dev/astra-a1r-20261004`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a1t` 做 A1-T（工具），两包文件范围不重叠。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第一批 A1-R”一节交付。** 先读节点回归记录 `AI_agent/logs/experiments/2026-10-04_node_regression_c2/README.md`（结论一节）和迁移对照记录里的抓包说明。节点回归 sm24 新底座的原始运行在证据分支 `evidence/node-regression-2026-10-04`（`sm24_runtime_subscription_run.tar.xz`），解包放本工作树的临时目录，用完删掉。

要点：
- A 和 B 都改动底座，先做 A（体积小、风险低），再做 B。
- B 的目标是与 Claude Code 实际请求尽量同条件，抓包里有的字段按抓包来；拿不准的写明，不猜。凭据不打印、不入仓。
- 最多 6 次 GLM 订阅小请求；Paratera、DeepSeek 为 0；不跑整案。
- 在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。

约 110 分钟内交付；如果到点还没做完 B，先保证 A 完整提交，B 已完成的部分小步提交并在报告里写清剩余。报告放 `AI_agent/logs/experiments/2026-10-04_absorb_a1r/README.md`，最终回复按验收 A–E 给结果、改前改后的数字、小测结果、检查与提交列表。
