# 派工：统一 Agent 阶段 2（长任务与恢复）

派工人：Opus 5.5（总主导、验收与质量）。阶段 1 已由 Opus 验收通过并合入主线（`54de1f99`）。你（Astra）牵头阶段 2，内部分工和子代理自定。

## 先读

1. `AI_agent/Agent.md`。
2. `AI_agent/project/unified_agent_harness_plan.md` 第三节阶段 2。
3. `AI_agent/project/unified_agent_acceptance.md`：阶段 1 验收结论与跟进项，以及**阶段 2 验收标准（按它交付）**。该文件由 Opus 维护，你不要改。
4. 你的阶段 1 交付：`AI_agent/logs/experiments/2026-10-02_harness_stage1/`、`src/agent_runtime/`、`src/agent/runtime_*.py`；阶段 0 接口说明三篇。
5. 你在调研报告中关于上下文的建议：`AI_agent/logs/experiments/2026-10-02_harness_research/astra_report.md` 第三节第 3 部分（完整历史 + 当前状态 + 活动窗口、图片按任务保留、请求前检查）。
6. `AI_agent/project/terminology.md`：名词规范（草案，待用户确认）。新写的说明和代码按它取名；已有类型名在用户确认前先不动。

## 工作位置

- 工作树 `/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage2`，分支 `dev/astra-stage2-20261002`，基于主线上加入本派工单的提交。
- 只在该工作树内改动，小步提交（英文 commit message）。不合入 main、不 push。
- 主工作树里 Opus 同时在用现有运行器跑 GLM 测试：不要动主工作树，也不要改冻结的工具和指引。

## 任务

按验收标准完成阶段 2。长记录的真实来源可选：

- run99（`2026-09-30_sm21_instruction_fix_run99`，Claude Code 命令行，116 轮）；
- GLM sm25（`2026-10-02_sm25_glm_baseline`，51 次工具调用，时限截停，流已无损压缩）；
- GLM sm24（`2026-10-02_sm24_glm_baseline`）。

改编成脚本化模型序列时，图片的大小、数量和返回顺序保持真实。历史实验目录只读。

## 可改范围

- 可改：`src/agent_runtime/`、`src/agent/runtime_*.py`、阶段 0–1 的契约与测试（需要时）；新增测试、`AI_agent/design/` 下的新说明、`AI_agent/logs/experiments/2026-10-02_harness_stage2/` 下的交付材料（本派工单除外）、`AI_agent/logs/worklog/` 下的开发记录。
- 不改：`scripts/tool_scripts/`、`src/agent/geometry/`、`src/agent/correction/`、现有 `src/agent/execution/` 模块（冻结基准）；`AI_agent/Agent.md` 与 `AI_agent/project/`；本派工单。

## 模型、子代理与外部调用

- 子代理按 `AI_agent/workflow/models.md` 的偏好自选，开发记录写明型号、推理档和用途。
- Paratera 小测按需，累计不超过 20 次请求，事后报用量；凭据只读引用主工作树 `.env`，不打印、不入仓。不跑整案。
- 不用 DeepSeek；GLM 订阅不能接自有底座。

## 交付（最终回复）

最终回复就是交付报告，中文、白话，约 2000–4000 字：做成了什么及所在文件；对照阶段 2 验收标准 A–H 逐条自评（附证据）；阶段 1 跟进项的处理；提交列表、改动文件名单、实际测试与结果；Paratera 用量；未决技术问题与需用户拍板的事（分开列）；阶段 3 估算与最大风险；子代理与用量。

不确定的写“未核实”。会改变范围的决定写进报告，不自行扩大范围；能做完的部分照常做完并提交。
