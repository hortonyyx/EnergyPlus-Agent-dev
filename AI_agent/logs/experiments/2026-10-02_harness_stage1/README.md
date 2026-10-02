# 阶段 1 交付入口

本目录属于 `dev/astra-stage1-20261002`，实施依据为 [派工单](brief.md)。Astra 提交实现和自评，正式验收由 Opus 维护。本阶段没有整案模型实验。

- [交付报告](delivery_report.md)：结果、A–I、阶段 0 跟进、用量和下一阶段边界。
- [运行设计](../../../design/unified_agent_stage1_runtime.md)：入口、分层、记录、预算和恢复。
- [离线 viewer](offline_run/bim/candidate_01/viewer.html)：脚本模型桩经真实冻结 MCP 生成的两个空间、一个门，仅用于验证闭环。
- [离线核查](offline_run/verification.json)、[行为报告](offline_run/behaviour/timeline.md)。
- [真实接口小测](paratera_probe_01/probe_receipt.json)：Qwen3.8-27B，2 请求、12,129 tokens；仅颜色卡，没有建模。
- [工具与白名单](tools_report.md)、[完整四种工具表及哈希](frozen_materials/tool_catalog_manifest.json)。
- [保存 BIM 快照](building_report.md)、[七组历史重放](history/README.md)。
- [联合 131 项测试](pytest_final.log)、[历史包定稿 8 项检查](pytest_history_final.log)（新增一项，合计 132 个不同检查）、[记录和范围核查](delivery_audit.json)、[环境](validation_environment.json)。
- [完整改动文件名单](changed_files.txt)、[提交列表](commits.txt)。

复核现有新日志和附件（不调用模型、不覆盖原运行）：

```bash
PYTHONDONTWRITEBYTECODE=1 python AI_agent/logs/experiments/2026-10-02_harness_stage1/audit_delivery.py
```

另建一次离线闭环（原 `offline_run` 不覆盖）：

```bash
PYTHONDONTWRITEBYTECODE=1 python AI_agent/logs/experiments/2026-10-02_harness_stage1/verify_closed_loop.py AI_agent/logs/experiments/2026-10-02_harness_stage1/offline_review
```

读取统一日志、旧 CLI 记录或旧桥接记录：`python AI_agent/logs/experiments/2026-10-02_harness_stage1/record.py --help`。

`probe_paratera.py` 是本批接口小测脚本，现有证据已满足小测，不需再执行。程序会累计既有请求、最多允许本批 20 次；脚本中的凭据路径只读，凭据不在此目录。普通入口 `python -m src.agent.runtime_entry --help` 不会触发模型调用。

事件和按哈希保存的附件是原始证据。`pytest_initial.log`、`pytest_fixture_race.log` 保留先前失败，最终通过见 `pytest_final.log`。冻结参考字符串保留原有末尾空行，原始失败输出也保留空白；源码、测试、设计与工作记录的 `git diff --check` 通过，没有为通过空白检查改写这些原件。
