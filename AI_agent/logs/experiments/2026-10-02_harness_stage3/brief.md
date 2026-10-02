# 派工：统一 Agent 阶段 3（带图委派与首版验收准备）

派工人：Opus 5.5（总主导、验收与质量）。阶段 0–2 已由 Opus 验收通过并合入主线（`16a185f2`）。你（Astra）牵头阶段 3，内部分工和子代理自定。

## 先读

1. `AI_agent/Agent.md`。
2. `AI_agent/project/unified_agent_harness_plan.md` 第三节阶段 3、第四节部分推理探索线。
3. `AI_agent/project/unified_agent_acceptance.md`：阶段 2 验收结论里的跟进项，以及**阶段 3 验收标准（按它交付）**。该文件由 Opus 维护，你不要改。
4. 你的阶段 0–2 交付与说明：`AI_agent/design/unified_agent_stage0_interfaces.md`、`harness_core_contracts.md`、`building_contracts.md`、`runtime_long_tasks.md`，以及 `AI_agent/logs/experiments/2026-10-02_harness_stage{0,1,2}/`。
5. 同日 Opus 做的两份材料，可直接用来出角色小测题：
   - [GLM 基线](../2026-10-02_glm_baseline/README.md)：GLM 在 sm24 把东、西立面两扇 4800 大窗的窗顶套成 2.8 m（实际 3.4 m），sm25 漏了两扇西窗；
   - [目标档局部小测](../2026-10-02_paratera_elevation_probe/README.md)：同一读窗高问题，Qwen3.8-27B 与 Qwen3.8-Flash 两张立面全对，GLM-5.3-Flash（low）东立面错。
6. `AI_agent/project/terminology.md`：名词规范（草案，待用户确认）。新写的说明和代码按它取名；已有类型名在用户确认前先不动。

## 工作位置

- 工作树 `/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-stage3`，分支 `dev/astra-stage3-20261002`，基于主线上加入本派工单的提交。
- 只在该工作树内改动，小步提交（英文 commit message）。不合入 main、不 push。
- 主工作树里 Opus 可能同时用现有运行器跑 GLM 测试：不要动主工作树，也不要改冻结的工具和指引。

## 任务

按验收标准完成阶段 3。要点：

- 先做按模型的请求估算并校准，再接真实子角色。
- 外层协调演示可以由你自己经 MCP 充当协调者，但不跑整案；演示只用离线桩或角色小测的额度。
- 角色小测出题尽量取自已有资产和已知参照：sm24 立面窗高、sm21 或 sm24 平面尺寸链、Voimatalo 已验收精细档的局部（层数、窗列、门位）、信息不足题（只给少量照片或渲染，问无法确定的量，看是否如实说不确定）。真实照片的选样仍待用户决定，代替品要标明。
- 首批整案方案写进交付目录，交 Opus 汇总后报用户批准。方案里的协调模型建议用你（Codex 订阅），以节省用户的 Claude 额度；工作模型默认 Qwen3.8-27B。

## 可改范围

- 可改：`src/agent_runtime/`、`src/agent/runtime_*.py`、阶段 0–2 的契约与测试（需要时）；新增 MCP 服务入口、测试、`AI_agent/design/` 下的新说明、`AI_agent/logs/experiments/2026-10-02_harness_stage3/` 下的交付材料（本派工单除外）、`AI_agent/logs/worklog/` 下的开发记录。
- 不改：`scripts/tool_scripts/`、`src/agent/geometry/`、`src/agent/correction/`、现有 `src/agent/execution/` 模块（冻结基准）；`AI_agent/Agent.md` 与 `AI_agent/project/`；本派工单。
- 新增证据按哈希引用仓库已有字节，不重复打包；新增证据尽量控制在 10 MB 左右。

## 模型、子代理与外部调用

- 子代理按 `AI_agent/workflow/models.md` 的偏好自选，开发记录写明型号、推理档和用途。
- Paratera：角色小测累计不超过 60 次请求，估算校准另计、不超过 20 次；事后报用量。凭据只读引用主工作树 `.env`，不打印、不入仓。
- 不跑整案；不用 DeepSeek；GLM 订阅不能接自有底座。

## 交付（最终回复）

最终回复就是交付报告，中文、白话，约 2000–4000 字：做成了什么及所在文件；对照阶段 3 验收标准 A–I 逐条自评（附证据）；阶段 2 跟进项的处理；角色小测结果表（按输入种类与推理程度分列，对错都报）；Paratera 请求次数与用量；首批整案方案的位置与要点；提交列表、改动文件名单、实际测试与结果；未决技术问题与需用户拍板的事（分开列）；阶段 4–5 估算与最大风险；子代理与用量。

不确定的写“未核实”。会改变范围的决定写进报告，不自行扩大范围；能做完的部分照常做完并提交。
