# 派工：统一 Agent 阶段 0（接口与验收样例）

派工人：Opus 5.5（统一 Agent 开发总主导、验收与质量负责）。用户本轮：“开工吧，开始开发”。按 10-02 用户安排，主体开发交 GPT 侧，由你（Astra）牵头并自定分工；我负责验收和质量。

## 先读

1. `AI_agent/Agent.md`（入口与权限）。
2. `AI_agent/project/unified_agent_harness_plan.md`（开发计划，阶段 0 见第三节）。
3. `AI_agent/project/unified_agent_acceptance.md`：**阶段 0 验收标准，按它交付**。该文件由 Opus 维护，你不要改。
4. 你自己的调研报告与三轮讨论：`AI_agent/logs/experiments/2026-10-02_harness_research/`。
5. `AI_agent/logs/worklog/2026-10-02_reconstruction_discussion.md`（规整原则、底座讨论、收工）。
6. 按需：`AI_agent/design/model.md`（源模型；“10-02 规整原则与容差分层”一节）、`AI_agent/design/evaluation.md`、`AI_agent/design/model_configuration.md`、`AI_agent/design/architecture.md`、`AI_agent/design/partial_inference_framework_start.md`、`AI_agent/workflow/models.md` 顶部（子代理选型偏好）、`AI_agent/workflow/development.md`。

## 工作位置

- 工作树 `/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage0`，分支 `dev/astra-stage0-20261002`，基于 main 上加入本派工单的提交。代码与冻结基准 `5bb10538`（标签 `checkpoint/2026-10-02-harness-baseline`）相同，之后只有文档提交。
- 只在该工作树内改动，小步提交（英文 commit message，写清做了什么）。不要合入 main、不要 push；验收通过后再定合入。
- 沿用现有 Dev Container 环境，不重装依赖。测试用 `python -m pytest <文件> -n 4`（或更少 worker）。共享 editable 安装可能让 `src` 指向主工作树，必要时检查模块 `__file__`。

## 任务

按验收标准完成阶段 0：接口说明、可机器校验的接口定义、三类主样例加三个专项样例、检查与反例、验收材料。包名、文件布局、具体字段由你设计；技术细节之后我们一起定稿，新增的产品取舍交用户。

阶段 0 定的是阶段 1 起要用的正式接口：宁可少而准，不要为将来铺满字段。推理侧专属内容按计划标为待验证假设。

## 可改范围

- 新增：底座核心包、建筑共用层接口模块、`tests/` 下的新测试与样例、`AI_agent/design/` 下的新接口说明、`AI_agent/logs/experiments/2026-10-02_harness_stage0/` 下的交付材料（本派工单除外）、`AI_agent/logs/worklog/` 下的开发记录。
- 现有共享模块尽量不改；确需改（如 `src/agent/model_routes.py`）要写明理由并跑相关旧测试。
- 不改：`scripts/tool_scripts/`、`src/agent/geometry/`、`src/agent/correction/`、现有 `src/agent/execution/` 模块（冻结基准）；`AI_agent/Agent.md` 与 `AI_agent/project/` 下的文件（计划、目标、路线和验收记录由 Opus 维护）；本派工单。
- 历史实验目录只读，不覆盖原始输入和旧结果。

## 模型与子代理

- 内部分工和子代理由你决定。按 `AI_agent/workflow/models.md` 的偏好：成块实现、分析可用 5.6 Sol/Terra，轻量整理用 5.6 Luna，Astra 留给难点；派工时明确型号与推理档，并在开发记录里写明实际型号、用途和原因。
- 不调用工作模型或付费 API；确需 Paratera 接口小测时在交付中提出，由 Opus 安排。不用 DeepSeek。GLM 订阅不能接自有底座。
- 本阶段不需要联网；查公开文档以外不要联网。

## 交付（最终回复）

最终回复就是交付报告（程序会存成文件）：中文、白话，约 2000–4000 字，细节放仓库文件里。

1. 做成了什么：接口清单（一句话一个）及所在文件；
2. 对照验收标准 A–J 逐条自评（满足／部分满足／未满足），附证据（文件、测试名）；
3. 接口 × 样例覆盖表、历史记录映射表的位置；
4. 提交列表（hash 与一句话）、diff 文件名单、实际跑过的测试与结果；
5. 未决技术问题（需要和 Opus 定的）与需用户拍板的产品取舍，分开列；
6. 阶段 1–3 细化估算（按会话轮数）与最大风险；
7. 子代理：型号、推理档、用途、结果；本次能拿到的用量。

不确定的写“未核实”，不用推测填空。遇到会改变范围的决定，写进报告，不要自行扩大范围；能做完的部分照常做完并提交。
