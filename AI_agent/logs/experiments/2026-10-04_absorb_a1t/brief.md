# 派工：吸收包第一批 A1-T（平面尺度检查）

派工人：Opus 5.5。工作树 `.worktrees/astra-a1t`，分支 `dev/astra-a1t-20261004`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a1r` 做 A1-R（底座），两包文件范围不重叠。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第一批 A1-T”一节交付。** 先读节点回归记录 `AI_agent/logs/experiments/2026-10-04_node_regression_c2/README.md` 的 sm25 一节。sm25 新底座的原始运行在证据分支 `evidence/node-regression-2026-10-04`（三段压缩包，拼接说明见主线 `evidence/sm25_runtime_subscription_manifest.json`），其他历史运行的位置见各实验目录与 `evidence/migration-2026-10-03`。解包放本工作树的临时目录，用完删掉。

要点：检查要保守、可解释、不自动换算；零误拒比多拦更重要。改写给模型的文字坚持“替换不追加”。0 次模型请求，不改几何内核的计算方式。在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。

约 100 分钟内交付。报告放 `AI_agent/logs/experiments/2026-10-04_absorb_a1t/README.md`，最终回复按验收 A–D 给结果、重放条数、新版本号、检查与提交列表。
