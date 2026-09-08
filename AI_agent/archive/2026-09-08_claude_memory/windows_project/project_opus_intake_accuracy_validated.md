---
name: Opus intake_output 准确度的当前验证手段
description: 现阶段用外部 LLM 读 output 做矢量判断；最终判定要走 IDF → OpenStudio；正式 eval 方案 TBD
type: project
originSessionId: 7dd08f4a-2004-433d-a281-03e9103623c8
---
现阶段 Opus 产出的 `intake_output.json` 准确度**当前验证手段** = 用户用其他大模型读 IntakeOutput 做矢量判断，结论"当前测试难度下 Opus 已准确"。但这是**临时手段**，不是终局：

- **最终验收一定走** IDF → OpenStudio 三维视察（[architecture.md §6.1 L3](../../AI_agent/architecture.md)）
- **正式 eval 方案 TBD**：用户在考虑两条路 — ①中途拆出来看几何（在 surface 之后 export YAML 做几何对比）②其他方案（GT diff / EP 仿真结果对比 / 其他）

**Why:** 2026-05-07 sm_16_newarch 首跑后用户明确：外部 LLM 是 stop-gap；正式评测方案还没拍板，但终局必含 OpenStudio。助手不要把"外部 LLM 已验证"当成永久结论或 baseline 锚点。

**How to apply:**
- 与用户讨论 Plan B 评测路径时：①认 Opus 当前输出经验上准确（已外部验证）②不把外部 LLM 判断当成可重复 / CI 友好的指标 ③推进 B1-B3 时**保留弹性**——可能不只是字段级 diff，还可能要在 surface_agent 后插几何抽取节点
- B6 开源模型对比时，**Opus baseline 必须用 OpenStudio 视察过的 case**（[CLAUDE.md §8.1](../../AI_agent/CLAUDE.md) `dimensions_check` 那一栏），不是"外部 LLM 说准的"那批
- 用户问"评测怎么做"时不要急着推某个方案，先确认他对"中途几何抽取 vs 其他"的最新倾向
