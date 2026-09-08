---
name: gt-itself-can-violate-its-own-quantisation
description: gt 是判卷权威，但它自己可能违反入库量化——用户一问就翻出 8 个未量化坐标
metadata:
  type: project
---

**2026-09-08，用户两句话翻出来的**：
「内墙墙厚都是 120mm」＋「**gt 不都是按 1mm 入库了吗？为什么还有那种浮点数？**」

**主控实测**（`case_tests/test_baseline/gt/sm25-L_anchor/gt.json`，312 个顶点坐标全扫）：

```
⛔ 非 1 mm 整数倍 = 8 个，全部在 floors[0]（1f）：
   15.9996 × 4（zones[2]/[3]）   离 16.000 差 0.4 mm
    9.9999 × 4（zones[8]/[9]）   离 10.000 差 0.1 mm
2f 一个都没有。
```

**为什么重要**：`15.9996` 那一处让 `2_modelling` 切出 65 mm 薄片、撞 `kernel.pairing_gate`
（EnergyPlus 对 <0.1 m 的面可能 segfault）。而更要紧的是——
**gt 是判卷的唯一权威**：8 个未量化坐标里 4 个还偏了 60 mm（= 半个 120 mm 墙厚）
⇒ **所有以它为参照的分数都带这个偏差，且它躲过了 gt 复核。**

⭐ **零阈值判据（可直接复用）**：gt 的每个坐标都应是整毫米 ——
`abs(v*1000 - round(v*1000)) > 1e-6` 即违规。**⛔ 不需要发明容差**，312 个里挑出 8 个只用一行。

**How to apply**：
- ⭐ 下游出现「零点几毫米级说不清的量」时，**先回头量 gt 自己合不合它自己的规矩**，
  ⛔ 别默认参照物是干净的（[[baseline-unauditable-dont-chase-its-number]] 的近亲：
  那条说基准不可审计时别追它的分，这条说**基准可审计时要真的去审**）。
- ⚠️ 待办（未做）：① gt 入库量化门为何没拦住这 8 个；
  ② 那两处 zone 边界为何记的是墙**面**而不是**轴线**（gt 全局用轴线基准）——
  ⛔ 后者是推的（60 = 120/2），**尚无直接读数证实**。

配套：[[wall-thickness-dimension-basis-direction]] · [[judge-gt-authoritative-images-auxiliary]]
· [[gt-standard-artifact-checklist]]
