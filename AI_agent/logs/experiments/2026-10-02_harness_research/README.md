# 10-02 Agent 运行底座调研与讨论

Opus 按用户要求派 Astra（`gpt-6-astra`、max、只读、联网搜索）调研成熟 harness 方案，随后双方在同一线程讨论三轮，形成[统一 Agent 开发计划](../../../project/unified_agent_harness_plan.md)。

- [派工单](brief.md)，[调研报告](astra_report.md)
- 讨论：[第一轮 Opus](discussion_01_opus.md) / [Astra](discussion_01_astra.md)，[第二轮 Opus](discussion_02_opus.md) / [Astra](discussion_02_astra.md)，[第三轮 Opus](discussion_03_opus.md) / [Astra](discussion_03_astra.md)
- [调用回执与用量](run_receipt.json)

报告附表 B 中 `/tmp/claude-0/...scratchpad/harness_repos/` 下的本地源码路径是会话临时目录，已不保留；以表中各仓库固定提交的网址为准（pi `9b3c19d`，deepseek-harness `639ed01`，codex `ca46606`，qwen-code `b3dda46`，mini-swe-agent `04d809c`）。
