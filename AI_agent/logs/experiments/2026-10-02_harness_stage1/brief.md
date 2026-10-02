# 派工：统一 Agent 阶段 1（冻结工具的单角色闭环）

派工人：Opus 5.5（总主导、验收与质量）。阶段 0 已由 Opus 验收通过并合入主线（`359e772e`）。按开发计划，你（Astra）牵头阶段 1，内部分工和子代理自定。

## 先读

1. `AI_agent/Agent.md`。
2. `AI_agent/project/unified_agent_harness_plan.md` 第三节阶段 1。
3. `AI_agent/project/unified_agent_acceptance.md`：阶段 0 验收结论里的 8 个跟进项，以及**阶段 1 验收标准（按它交付）**。该文件由 Opus 维护，你不要改。
4. 阶段 0 的三篇接口说明：`AI_agent/design/unified_agent_stage0_interfaces.md`、`harness_core_contracts.md`、`building_contracts.md`，以及你的阶段 0 交付材料 `AI_agent/logs/experiments/2026-10-02_harness_stage0/`。
5. `AI_agent/project/terminology.md`：名词规范（草案，待用户确认）。新写的说明和代码按它取名；用户确认前，阶段 0 已有的类型名先不动，确认后由 Opus 通知，再统一改名（跟进项 1）。
6. 按需：`src/agent/execution/chat_mcp.py`、`src/agent/model_routes.py`、`src/configs/llm_paratera.yaml`、`scripts/tool_scripts/run_bim_agent.py`（冻结，只读）、`AI_agent/logs/experiments/2026-10-01_behaviour_records/record.py`、`AI_agent/workflow/models.md` 顶部。

## 工作位置

- 工作树 `/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage1`，分支 `dev/astra-stage1-20261002`，基于主线上加入本派工单的提交。
- 只在该工作树内改动，小步提交（英文 commit message）。不合入 main、不 push。
- 主工作树里 Opus 同时在用现有运行器跑 GLM 测试：不要动主工作树，也不要改冻结的工具和指引。

## 任务

按验收标准完成阶段 1。历史重放样本：

- run99（`2026-09-30_sm21_instruction_fix_run99`）、run100（`2026-09-30_sm24_instruction_fix_run100`）：Claude Code 命令行运行；
- Opus 10-01 三例（`2026-10-01_opus_dev_sm21`、`_sm24`、`_sm25`）：开发模型经桥接器的调用记录；
- 两次 Sol 测试（`2026-10-01_partial_inference_developer_tests/run_61sol`、`run_6sol`）：桥接的逐步请求与返回。

历史实验目录只读，重放在独立目录进行，不覆盖原始输入和旧结果。

## 可改范围

- 新增：运行底座代码（包名自定，核心与建筑层的依赖方向保持阶段 0 的约定）、新的运行入口、`tests/` 下的新测试、`AI_agent/design/` 下的新说明、`AI_agent/logs/experiments/2026-10-02_harness_stage1/` 下的交付材料（本派工单除外）、`AI_agent/logs/worklog/` 下的开发记录。
- 可改：阶段 0 新增的契约与测试（跟进项需要）；`record.py` 可以复制到新位置演进，原文件保留可用。
- 尽量不改：`chat_mcp.py`、`model_routes.py` 等现有共享模块；确需改时写明理由，并跑相关旧测试。
- 不改：`scripts/tool_scripts/`、`src/agent/geometry/`、`src/agent/correction/`、现有 `src/agent/execution/` 模块的行为（冻结基准）；`AI_agent/Agent.md` 与 `AI_agent/project/`；本派工单。

## 模型、子代理与外部调用

- 子代理按 `AI_agent/workflow/models.md` 的偏好自选，开发记录写明型号、推理档和用途。
- Paratera 接口小测已获用户同意（按需、事后报用量）：累计不超过 20 次请求，只做工具调用、图片回传、思考字段三项；凭据在主工作树 `.env`（不入仓、不打印）。不跑整案。
- 不用 DeepSeek；GLM 订阅不能接自有底座。
- 联网只用于 Paratera 小测和查公开文档。

## 交付（最终回复）

最终回复就是交付报告，中文、白话，约 2000–4000 字：

1. 做成了什么（一句话一项）及所在文件；
2. 对照阶段 1 验收标准 A–I 逐条自评，附证据（文件、测试名、日志）；
3. 阶段 0 跟进项 1–8 的处理结果；
4. 提交列表、改动文件名单、实际跑过的测试与结果；
5. Paratera 小测的请求次数与用量；
6. 未决技术问题和需用户拍板的事，分开列；
7. 阶段 2–3 估算更新与最大风险；
8. 子代理与用量。

不确定的写“未核实”。会改变范围的决定写进报告，不自行扩大范围；能做完的部分照常做完并提交。
