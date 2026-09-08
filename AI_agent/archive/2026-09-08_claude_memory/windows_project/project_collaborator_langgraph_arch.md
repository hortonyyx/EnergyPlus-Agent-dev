---
name: 协作者侧 LangGraph 10 节点拓扑
description: 协作者在 LangSmith 上的下游 EnergyPlus-Agent 架构 — 10 个 subagent + 各自专属 prompt + 隔离 MCP 工具集
type: project
originSessionId: 2f29c1f2-5734-4e74-8f34-8053b6ea2e7f
---
协作者维护的下游建模流水线是 **10 节点 LangGraph + Supervisor**，节点顺序：
`intake → schedule → material → construction → zone → surface → fenestration → lights → people → hvac`

**Why**：2026-04-14 协作者跑了一次 5 层办公楼端到端 trace（`20260414_192502/`，335 run JSON），thread_id `export-demo`，模型 `gpt-5.4-2026-03-05` via `model_provider: anthropic`。本项目助手于 2026-05-05 解码这批日志，确认架构。

**架构关键事实**：
- 每个 subagent 独立 system prompt + 严格隔离的 MCP 工具子集（schedule 只见 schedule_*；material 只见 create_*_material；…）
- 每个 subagent 输入合同：`--- <Subsystem> specifications (primary task) ---` + `--- Downstream specs (reference only) ---`，下游 specs 当只读引用以保命名一致
- intake 节点用单次 LLM tool-call 产出 `IntakeOutput` Pydantic，含 `building` + `site_location` + 10 个 `*_specs` 自然语言段（每段 1-3KB）
- 共享 thread_id / checkpoint 让前面 subagent 建出的对象（如 schedule）被后面引用

**How to apply**：
- 谈到"下游"/"协作者侧"/"intake"/"subagent" 时按此架构思考
- 改 `src/agent/nodes/intake.py` 时把 `IntakeOutput` schema 对齐协作者侧 10 字段
- LangSmith run JSON 在 `20260414_192502/`（已 .gitignore），需要再分析时去那里抽样
- 详见 [CLAUDE.md §7.12](../AI_agent/CLAUDE.md)（仓库内同步文档）
