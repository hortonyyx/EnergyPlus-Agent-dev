# 项目入口（兼容 Claude 的旧入口）

2026-09-08：用户要求 Codex 接手并重新整理。本文件只作索引，不再另存一套治理、进度或模型分工。

按顺序读取：

1. [AGENTS.md](../AGENTS.md)：共同约定、Git 全权授权、收工动作。
2. [项目说明](README.md)：轻量 BIM 目标、现有代码位置和文档职责。
3. [当前计划](plan.md)：实际进度、当前问题、下一步。
4. 按任务读取 [开发手册](guides/development.md)、[case 操作](guides/new_case_guide.md) 或 [架构](architecture/pipeline_stage_contracts.md)。

当前唯一开发主干为 `main`，工作目录为 `/workspaces/EnergyPlus-Agent-dev`。
接手基线、旧树清单和回退方法见 [接手记录](logs/worklog/2026-09-08_takeover.md)。

旧版“主控只能派工”“跨家族必审”“每席一次全量”“先清完旧债才能跑 case”等规则已撤销。
旧 memory 和历史文档仅作线索；与新入口冲突的规则不执行。不得继续向本文件追加日更 banner。
