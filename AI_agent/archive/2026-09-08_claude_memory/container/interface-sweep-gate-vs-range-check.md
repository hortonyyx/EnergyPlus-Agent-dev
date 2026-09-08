---
name: interface-sweep-gate-vs-range-check
description: 接线摸排的机械判据会假绿——范围校验不是语义门；暴露面比 schema 窄本身就是防线；轴 B 要含模型输出内部的冗余表示
metadata: 
  node_type: memory
  type: project
  originSessionId: 53f7e084-3355-477f-817a-213aa11758bf
  modified: 2026-08-08T05:24:19.866Z
---

2026-08-08 接线摸排第一轮（步骤 1/2/3/5 + F-16 定性）跑完，三条会反复用到的判据。
全档 `AI_agent/logs/experiments/2026-08-08_interface_sweep/README.md`（commit `d61c2fe`）。

**① 「有门」必须落到具体那一行在约束什么。**
机械判据把 `multiplier: int = Field(1, ge=1)` + `raise ValueError("Multiplier must be at least 1.")`
算成了「有保护」，于是步骤 3 初筛出 **0 条候选 —— 是假的**。
范围/格式/枚举校验管的是**值合不合法**，不是**值该等于什么**。
⇒ 与 [[lock-must-exercise-real-entry-point]] 的「非 None ≠ 成功」同型：
**断言写在合法性上等于没断言。** 机械初筛只配用来排序，逐条实看才算数。

**② 暴露面比 schema 窄，本身就是有效防线（省事且可复制）。**
`SurfaceSchema` 有 `multiplier` 而 `create_surface` 工具**不暴露这个参数** ⇒ 模型碰不到 ⇒ 不是候选。
这是 [[model-visible-but-not-its-business]] 那条「让它看不见」的**最便宜形态**，
应作为默认设计习惯。正面样板 = `create_zone` 的 frame 四字段三层防护
（换 prompt + 工具侧拒绝 + 段尾无条件 normalizer），全项目唯一。

**③ 轴 B 要扩写成「同一*事实*的多处声明，含模型输出内部」。**
F-16 定性：窗的层归属有 **4 处独立声明**（模型写 name、模型写 id、代码按 z_floor 排的 rank、
reading manifest 的 floor_ref），三道门在维持一致。
⇒ 已见三形态：代码 vs 代码（F-13）· schema vs 门（F-15②）· **模型输出内部（F-16）**。

**另两条实况**（下轮直接用，别重查）：
- **下游 9 节点的暴露面是「工具参数 schema」不是字段**（它们是 ReAct + MCP 工具）
  ⇒ **F-15 的 JSON-Schema 机械剥除法在下游用不上**，要在工具定义侧动。
- **工具定义不是 prompt** ⇒ 不受 CLAUDE.md §3 协作者权属限制（`zone_tools` 已有先例）
  ⇒ 下游修法走工具侧可绕开权属阻塞。
- `construction`/`material`/`schedule` 三节点**完全不碰几何** ⇒ 同族缺陷射程为零，不用再看。
