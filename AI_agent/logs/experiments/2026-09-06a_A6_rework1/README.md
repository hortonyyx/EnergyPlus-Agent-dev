# A-6 返工 1 · 工程验证证据

工作树 `/tmp/a6_tickclaim_astra`，基点 `94e899e5`。仅处理 consume 出口不变量；阻断①、E-a 接线及非阻断项不在本单范围。

## 改前复现（源码仍为 94e899e5）

原探针用对象库 `git show 6ffb1429:AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/attack_probe_2_chain_reorder.py` 取出，逐字节保存为 `attack_probe_2_chain_reorder.original.py`。
`replay_review_probe.py` 只把其中两处 `/tmp/a6_review_claude` 改为当前工作树，避免导入或读取别的 worktree；输出原件 SHA256 与双模块导入路径。

实际命令：

```sh
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/replay_review_probe.py
```

原文见 `reviewer_before.txt`：`FORGED consume() result: x0=30000 x1=0 inverted=True`（原日志两个字段间为双空格）。确认阻断②的承重前提成立，不触发 A 层停报。

本目录为软件行为证据，模型响应均为诊断输入，不是图像语义裁定或 sm25 成绩。
