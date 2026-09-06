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

## 修后及自设同形输入

- `reviewer_after.txt`：同一复核探针，当前实现以 `TICK_INTERVAL_NOT_ORDERED` 拒绝。
- `probe_own_inputs.py --baseline`：从对象库把 `94e899e5` 的两个模块加载到独立进程内存，不写旧版本源码、不进入其他 worktree；用与修后相同的测试构造函数产生输入。原文 `own_before.txt`。
- `probe_own_inputs.py`：在当前实现执行相同构造。原文 `own_after.txt`。
- 两个主要新增同形输入是 `vertical_inversion` 和 `duplicate_choice_owner`：前者更换轴与数值，后者区间全部合法但响应内两个选择指同一边，验证跨行全集/关联而非只测倒置。
- 其余输入覆盖整份响应遗漏、响应/行分歧、重复行、假债/假退债、证据元数据、代次与响应 schema；逐项说明见 `submit_consume_checks.md`。
- 正常批次的前后 SHA256 同为 `0461de0422b2dfbf253532b16da904af566ac4769e7f7ee343ecee39ffe0f76b`（两份 own 日志第 2 行）；该控制说明修法不要求正常输入改表示或改数值。

实际命令原文：

```sh
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/probe_own_inputs.py --baseline
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/probe_own_inputs.py
python AI_agent/logs/experiments/2026-09-06a_A6_rework1/replay_review_probe.py
python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_tick_claim_a6.py tests/test_opening_adjudication_a6.py tests/test_tick_claim_consumption_recheck.py
python -m pytest --collect-only -q -n 6 -p no:cacheprovider tests/test_tick_claim_consumption_recheck.py
```

`targeted.txt:8`：44 passed（原有 27 + 新增 17）；`test_collection.txt` 保留新增 17 个唯一 nodeid 及收集汇总。全量只以 `full_suite.txt` 的完整汇总为准，最终对账见执行档。

完整全量已完成（实现 38bd8f5f）：`3894 passed, 2 skipped, 13 xfailed, 211 warnings in 540.28s (0:09:00)`，`EXIT_CODE=0`；导入哨兵在本树，逐位闭合 `3877 + 17 = 3894`。原文 `full_suite.txt:442` / `:444`。
