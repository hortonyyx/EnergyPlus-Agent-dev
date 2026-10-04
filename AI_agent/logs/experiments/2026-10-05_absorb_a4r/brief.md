# 派工：吸收包第四批 A4-R（按金额封顶、压缩参数评估）

派工人：Opus 5.5。工作树 `.worktrees/astra-a4r`，分支 `dev/astra-a4r-20261005`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a4t` 做 A4-T（工具），文件范围不重叠：本包只改 `src/agent_runtime/`（`agent_versions.json` 除外）、`src/harness_contracts/`、`src/agent/runtime_*.py`（`runtime_tools.py` 除外）与对应测试，不碰 `scripts/tool_scripts/`。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第四批 A4-R”一节交付。** 先读 [27B 摸底](../2026-10-04_qwen27b_probe/README.md)与 [A2 后重跑](../2026-10-04_qwen27b_after_a2/README.md)的结果、[A3-R 报告](../2026-10-04_absorb_a3r/README.md)的 A 节，以及 `AI_agent/workflow/models.md` 里 Paratera 的单价与图片收两次的记账口径。历史运行：节点回归新线路与 27B 摸底的压缩包在证据分支 `evidence/node-regression-a1-2026-10-04`，A2 后重跑的压缩包在主线 `2026-10-04_qwen27b_after_a2/evidence/`（哈希清单都在主线）。解包放本工作树的临时目录，用完删掉。

要点：
- A 是主要工作：金额上限要可解释、保守，到上限前停下并交出最近完整稿；不能悄悄放宽现有的预算保护。
- B 只做离线评估，证据不足就不改默认值。
- 0 次模型请求；凭据不打印、不入仓。在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。同机还有别的检查在跑，别开太多并发。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-05_absorb_a4r/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 100 分钟内交付。最终回复按验收 A–C 给结果、反例条数、回放对比的数字、检查与提交列表。
