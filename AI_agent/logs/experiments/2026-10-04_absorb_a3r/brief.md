# 派工：吸收包第三批 A3-R（缓存与流式，提速线第一项）

派工人：Opus 5.5。工作树 `.worktrees/astra-a3r`，分支 `dev/astra-a3r-20261004`，基于主线。只在本分支小步提交，不合入、不推送。另一个 Astra 会话同时在 `.worktrees/astra-a3t` 做 A3-T（工具），两包文件范围不重叠；本包不碰 `scripts/tool_scripts/` 与 `src/agent/runtime_tools.py`。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“吸收包第三批 A3-R”一节交付。** 先读 [10-04 节点回归记录](../2026-10-04_node_regression_a1/README.md)（sm24 的缓存一节与结论第 2 条）、[A2-R 报告](../2026-10-04_absorb_a2r/README.md)第 E 节，以及 Claude Code 抓包 `AI_agent/logs/experiments/2026-10-03_migration_comparison/evidence/claude_code_request_capture/`。新线路 sm24、sm25 的原始运行在证据分支 `evidence/node-regression-a1-2026-10-04`（拼接与哈希见主线 `2026-10-04_node_regression_a1/evidence/` 的清单）。解包放本工作树的临时目录，用完删掉。

要点：
- 先做 A（离线，不花请求），A 里查到我方问题就先修，再决定 B 怎么设计。
- B 的方案和采纳门槛先写进报告并提交，再发请求；超出请求或 token 上限就停。只用 GLM 订阅；Paratera、DeepSeek 为 0；凭据不打印、不入仓。
- 会话标识只用 Anthropic 公开的 `metadata.user_id`，按运行随机生成；不加 Claude Code 的会话头或 User-Agent。
- 在本工作树跑检查时 `PYTHONPATH` 指向本工作树，pytest 显式 `-n 2 -s`，临时目录放本工作树内。同机还在跑整案，检查别开太多并发。

**开工就把报告初稿提交到 `AI_agent/logs/experiments/2026-10-04_absorb_a3r/README.md`，过程中随进度更新**（后台会话 2 小时会被强停）。约 110 分钟内交付；到点没做完的，已完成部分小步提交并在报告里写清剩余。最终回复按验收 A–D 给结果、序列对照的数字（每组每步缓存读取）、实际请求与 token、检查与提交列表。
