# skills/energyplus_mcp_twostep — 两步法 intake skill 文档库

> 与 [`../energyplus_mcp/`](../energyplus_mcp/) 并列。该文件夹是**两步法 intake** 的演进 skill 源（phase1 矢量化重绘 → phase2 拓扑建模）。
>
> 旧的 [`../energyplus_mcp/`](../energyplus_mcp/) 是**单步法 intake** 的 skill 源（`intake_node` 当前运行时加载）。两步法切到主线后，旧 skill 可逐步退场。

## 文件清单

| 文件 | 作用 | 何时用 |
|---|---|---|
| [`phase1_vector_schema.md`](phase1_vector_schema.md) | Phase 1 矢量 JSON 输出格式定义（strokes / pen 类型 / 立面 facade_axis_note 规范 / 自检）| 作为 phase 1 prompt 的硬约束，描述 LLM 应产出什么 |
| [`phase2_rules.md`](phase2_rules.md) | Phase 2 推理规则（vector JSON → IntakeOutput，字段推导顺序 / 命名 / vertex 合成 / InterZone single-construction 等）| 作为 phase 2 prompt 的硬约束，描述 LLM 拿矢量 JSON 后如何推 IntakeOutput |
| [`phase1_prompt_template.md`](phase1_prompt_template.md) | Phase 1 启动 prompt 模板（粘进新 Claude Code 会话）| 新 case 复制后改路径即可 |
| [`phase2_prompt_template.md`](phase2_prompt_template.md) | Phase 2 启动 prompt 模板（同上）| 新 case 复制后改路径即可 |

## 当前版本

- `phase1_vector_schema.md`：v1.2（2026-05-12，sm_20 跑后微调）
- `phase2_rules.md`：v1.3（2026-05-12，sm_20 Step 6 后加 InterZone single-construction 硬约束）

详细版本历史在各文件首段。

## 演进流程

1. 跑新 case 时**从本文件夹复制最新版**到 `test_data/SmallOffice_TwoStep/<case>/` 作 audit anchor（运行时副本，记录该次跑用的版本）
2. 跑出新 bug / 暴露规则漏洞时（如 sm_20 Step 6 暴露的 InterZone construction asymmetry）：
   - 在本文件夹更新源文档（版本号 +0.1）
   - 在版本历史段加 changelog 一行（日期 + 缘起 case + 修复内容）
   - **不动**已存的 case 目录里的副本（保留作 audit anchor）

## 与代码的关系（目前 vs 未来）

**当前状态（2026-05-12）**：本 skill 文件夹**未被 intake_node 自动加载**。两步法目前是手工运行（phase1 Claude Code 会话 + phase2 `Tool_scripts/run_phase2_deepseek.py` 或会话）。详见 [`AI_agent/floorplan_redraw_strategy.md`](../../AI_agent/floorplan_redraw_strategy.md) §8 架构影响前瞻。

**未来计划**（[`AI_agent/plan.md`](../../AI_agent/plan.md) B1.5）：把 [`src/agent/nodes/intake.py`](../../src/agent/nodes/intake.py) 改为运行时加载本文件夹，phase1 + phase2 串行调用。届时 `intake_node` 会读取本目录所有 `*.md` 作为 system prompt rule library，与现有 `_load_intake_rule_library()` 机制一致。

## 与 `../energyplus_mcp/` 的关系

| 维度 | `energyplus_mcp/`（旧）| `energyplus_mcp_twostep/`（新）|
|---|---|---|
| Intake 模型 | 单步：图 + 文本 → IntakeOutput | 两步：图 → vector JSON → IntakeOutput |
| 当前 intake_node 是否加载 | ✅ | ❌（手工运行）|
| skill 内容 | 视觉识图规则（D 段）+ 输出契约（intake_output_contract）+ vertex 合成（zonetool）混合 | 拆开：phase1 schema 专管视觉描摹 / phase2_rules 专管拓扑推理 |
| 主线计划 | 切到两步法后逐步退场 | 切到主线 |
| 何时退役 | 两步法 intake_node 重写完成 + 全量回归 ≥ Opus 80% 后 | — |

## POC 验证

详见 [`test_data/SmallOffice_TwoStep/smalloffice_20/`](../../test_data/SmallOffice_TwoStep/smalloffice_20/) + [`AI_agent/floorplan_redraw_strategy.md`](../../AI_agent/floorplan_redraw_strategy.md) §9。
