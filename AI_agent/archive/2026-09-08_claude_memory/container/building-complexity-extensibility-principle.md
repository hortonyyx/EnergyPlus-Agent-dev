---
name: building-complexity-extensibility-principle
description: "硬约束——每个决策必须为未来建筑复杂度升级(非方形/退台/挑空/中庭)留路,禁烤死\"共底面盒子\"简化假设;纯当前解无意义"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 16a8a6b7-f8cd-464e-b033-3bac6b878530
---

**用户硬约束（2026-07-03 定）**：**每个决策必须考虑未来建筑复杂度升级的可扩展性，不做纯只适用当前情况的方案——那没有任何意义。**

**背景**：现架构适用范围 = 正交·**共底面盒子**多层建筑（隐式 3D 模型 = "共用 footprint 的一摞拉伸楼板"，correction 每层 2D 分区 + 层高 → kernel 拉伸）。复杂体量各捅破一条假设：**退台**破"共用 footprint"（envelope 会把上层错误撑回满 footprint）、**挑空双层高**破"每层满铺楼板+固定层高"（z=3 硬塞楼板切成上下两区）、**中庭竖井**破"满铺楼板+跨层墙对齐"（贯通竖井作为一个 EP 热区没法统一）。

**关键判断**：这些**不是缺世界坐标**（我们有：铁律#2 单一世界原点 + `_reconcile_cross_floor` 已在世界坐标做多层对齐）——世界坐标必要但不充分。真正卡的是**表示法**（extrude-per-plate schema 没槽位表达退台量/双层高/void）。

**Why**：核心架构（判断-几何分工 / 单一世界坐标 / 版本化 schema / 稳定契约）**保留了升级路径、不需架构推翻**；复杂体量 = schema 加槽位 + kernel 扩展（含休眠支线 geometry_first 热区积木 = kernel 策略替换非推翻），都在接缝内长。**真正风险不在架构、在"烤死的假设"**——若为图省事把"共用 footprint/每层满铺楼板/固定层高"渗进每个角落，以后松动就疼。本原则=那道保险。

**How to apply**：任何 src/skills/schema/kernel 决策落地前，过一遍**"这条路以后能不能长到非方形/退台/挑空/中庭？"**；能扩展就留干净接缝、别硬编码当前简化假设；若某方案只在共底面盒子成立、扩展即需重写，就是危险信号、要么改要么显式标 backlog。复杂体量本身远期 defer，但**决策纪律现在就生效**。落 [[CLAUDE.md §1.5 不变量#6]]。

关联 [[recognition-modeling-capability]]（识图→建模质量主线）· `proposals/geometry_first_zonification.md`（热区积木支线，对复杂 3D 更合身）· memory 里"建筑升级非方形"远期项。
