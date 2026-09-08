---
name: validate_geometry_closure 临时放宽 (B0')
description: 2026-05-07 把 manifold ≥3 closure 检查从 raise 降到 warn，待 idfpy 切换后整体删除
type: feedback
originSessionId: 7dd08f4a-2004-433d-a281-03e9103623c8
---
[src/validator/data_model.py validate_geometry_closure](../../../src/validator/data_model.py) 从 `raise ValueError` 改成 `logger.warning`。原因 = EnergyPlus 本身不要求 zone polyhedral manifoldness（只检查 surface-pair InterZone 配对），项目原 validator 比 EP 严格。这条约束阻止了 sm_16_newarch 等存在 T-vertex 的几何（详见 plan.md B0' / architecture.md §8 Q5）写出 IDF，但实际 EP 能跑。

**Why:** 不应该自加比 EP 更严格的检查 + 阻塞 simulate。临时放宽是为了让 sm_16_newarch / sm_17 真跑通 EP 取得"T-vertex 不插 EP 也能跑"的实测证据；最终 idfpy 切换时 [src/validator/data_model.py 整体删](idfpy_embed.md#L77)，检查自然消失。

**实证补强 2026-05-07 晚**：直接拿 sm_16_newarch IDF（含 12/19 zones unclosed T-vertex）喂 EnergyPlus 25.2.0，warm-up 阶段 0 几何 severe，全年 RunPeriod 跑完（用 glazingfix 排除 fenestration 干扰后）。这是"EP 不在乎 manifold closure"的硬实测证据。**永久放宽，不再考虑恢复 raise**。

**How to apply:**
- 修改 surface 几何相关代码时**不要恢复 raise**，除非确认 idfpy 切换被永久放弃
- 如果之后某次跑 sm_X 出现 `[node=simulate] Error ... GeometrySchema` 之外的几何报错，先看是不是 EP runtime 真的有问题（看 eplusout.err），再决定是否要恢复某些检查
- Validator 里有 NOTICE 注释块（`===== TEMPORARILY LOOSENED 2026-05-07 =====`）；不要清掉 NOTICE，作为"不是设计如此"的标记
- 这条临时性约束**与 idfpy 切换强绑定**：协作者交付 idfpy MCP 重写后，连同 `src/validator/data_model.py` 整体删除即可
