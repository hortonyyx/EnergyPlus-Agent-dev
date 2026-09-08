---
name: 本项目侧职责边界 — 产 IntakeOutput 而非 epJSON
description: 本项目（多模态 intake）真正的输出是 IntakeOutput Pydantic 对象，不再产几何 epJSON / 完整 IDF
type: project
originSessionId: 2f29c1f2-5734-4e74-8f34-8053b6ea2e7f
---
本项目侧（`src/agent/nodes/intake.py` 多模态 intake）的输出契约是 **`IntakeOutput` Pydantic 对象**，含：
- `building` (BuildingSchema) + `site_location` (SiteLocationSchema)
- 10 个 `*_specs` 自然语言段：`zone_specs` / `material_specs` / `construction_specs` / `surface_specs` / `fenestration_specs` / `schedule_specs` / `lights_specs` / `people_specs` / `hvac_specs`

**Why**：2026-05-05 解码协作者 LangSmith trace 推翻了 CLAUDE.md §1.2 / §6 #9 旧描述（"本项目产 epJSON 给协作者侧 intake"）。事实是：协作者已经做完 intake → 10 subagent 建模全链；本项目只需把多模态视觉理解结果转为 IntakeOutput 同形结构，不需要自己跑 zone/surface/fenestration MCP 构 epJSON。

**How to apply**：
- 改 `intake.py` 的 `IntakeOutput` schema 时按 10 字段对齐
- 不要再写 zone/surface/fenestration 几何 IDF 构建逻辑（那是协作者 subagent 的事）
- §8.1 idfpy 替换主线（原计划 P1 `mcp_v2/` 起步 + sm_15 几何阶段重跑）的本项目侧工作量大幅缩减——大半在协作者侧 MCP 重写
- 与协作者对齐 IntakeOutput 字段名 + 类型时，建议直接复用协作者侧 schema（从 trace 里 OUTPUT['parsed'] 反推）
- 详见 [CLAUDE.md §7.12.D](../AI_agent/CLAUDE.md)
