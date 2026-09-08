---
name: fenestration glazing Construction layer 兼容性 bug — 已知,deferred to idfpy
description: 2026-05-07 sm_16_newarch simulate 真因; SimpleGlazing 被 fenestration_agent 当一层叠加 → EP window NaN fatal; 决策不修 prompt 等 idfpy schema 覆盖
type: project
---
**bug**：fenestration_agent（或上游 construction_agent）把 `WindowMaterial:SimpleGlazingSystem` 当作"一层单片玻璃"，在 Construction 中与 `Material:AirGap` + 第二片 SimpleGlazing 叠加成 玻璃→空气→玻璃 三明治。实例 `Window_Double_Glazing` Construction（sm_16_newarch [`temp_20260507_154141.idf`](../../../test_data/SmallOffice/smalloffice_16_newarch/output/temp_20260507_154141.idf)）。

EP IDD 硬约束：`WindowMaterial:SimpleGlazingSystem` 是"整窗系统等效模型"（U+SHGC+VT 三参数代表整个窗），**Construction 中必须 standalone**，不能与 air gap / 第二片玻璃叠加。违反时 EP window 求解器拿到错配 layer 物性 → 温度发散到 NaN → fatal `Convergence error in SolveForWindowTemperatures`。

副 bug：`Glass_Clear_6mm` 命名 `Double_Glazing` 但 U=5.7 W/m²K 是单层透明玻璃值（双层中空玻璃应 U≈2.7、SHGC≈0.5）—— 命名/数值不一致。

**Why:** 不修 prompt 的原因 = idfpy 自带 schema 校验，切换后会原生拒绝该组合；短期改 prompt 属重复投资。用户 2026-05-07 决策：当前焦点切到几何正确性（plan.md B1/B2/B3），simulate 跑通暂不作短期目标。

**How to apply:**
- 后续跑 sm_X simulate 卡 `Convergence error in SolveForWindowTemperatures` 或 glazing face 温度 NaN（`-N0ANC` 等乱码）→ 直接判定本 bug，不重新 debug
- 临时绕过两条路：
  - A. Construction 改成只引用一层 SimpleGlazing material（保持 SimpleGlazing 等效整窗语义）
  - B. fenestration 输出改用 detailed glazing：`WindowMaterial:Glazing × 2 + WindowMaterial:Gas × 1` 三层结构
- 验证用 IDF：[`temp_20260507_154141_glazingfix.idf`](../../../test_data/SmallOffice/smalloffice_16_newarch/output/temp_20260507_154141_glazingfix.idf)（manual single-layer fix，EP `Completed Successfully` / 0 severe / 9 warnings / 14.8 秒）
- **启动正式修复条件**：idfpy MCP 重写交付（[idfpy_embed.md](../../../AI_agent/idfpy_embed.md)）一并解；plan.md §C 已立卷；CLAUDE.md §8.2 同步登记
- 不要私下改 fenestration / construction prompt，会与用户的"几何优先"决策冲突
