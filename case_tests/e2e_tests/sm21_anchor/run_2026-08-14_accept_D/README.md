# run_2026-08-14_accept_D — 验收跑（第 1/3 次）

**性质 = 用户口径的验收跑**（2026-08-13 定：「验收要一口气推完不出错才算」
= 单次 flow 调用 · 单一代码基线 · 中途不干预 · 禁用重试掩盖崩溃 · 连跑 ≥3 次全过）。
⛔ 刻意不走 `--record`（承 08-10 用户口径「非正式的不用记，写明测什么就行」）。

## 结果：✅ 六条全中

- **A1** 单次 `flow` 调用 `--from 1_correction --judge off --geometry auto --with-ep`，中途零干预
- **A2** 真实退出码 **0**（独占 `.rc`；⛔ 不看后台通知里的 exit code）
- **A3** 除 `1_correction` 两次法定写入外**零重试**（`2_modelling`/`3_split_pairing`/`4_mep`/`5_intakeoutput` 各 1）
- **A4** EnergyPlus `Completed Successfully — 0 Severe`；IDF **100 面 / 15 窗 / 14 区**
- **A5** 顶点与 `run_2026-08-11_continuous_e2e` **400 面顶点 + 60 窗顶点逐位同序全同**
- **A6** 连跑 3 次（D/E/F）**全过**

## 本次跑测的是什么

**唯一变量 = F-28 修法**：`hvac_specs` 不再由 4_mep 的 LLM 撰写，改由代码按内核区列表
确定性渲染（`HVACTemplate:Thermostat` ×1 + 每区一个 `HVACTemplate:Zone:IdealLoadsAirSystem`），
其引用的 3 张 `Schedule:Compact` + 2 个专属 `ScheduleTypeLimits` 一并代码拥有。
⇒ 直接针对 08-13 验收 C 的死因（模型给恒温器漏写一格 ⇒ 整行位移 ⇒ 门读到不存在的时间表 ⇒ 三次重抽用尽）。

## ⛔ 口径限制（⛔ 引用本 run 时必须一并说）

1. **识图是冻结的老件**（`run_2026-08-11_continuous_e2e/0_reading` 逐字节复制，`cmp` 30/30 一致），
   **本轮一次图都没识** ⇒ 本 run **⛔ 不产生任何识图成绩**，成立的是「好 reading → EnergyPlus 通」。
2. **F-27（协议层未处理生成期截断）未修** ⇒ 按 sol 第五轮裁定，三次全过**只算经验样本**，
   ⛔ **不得声称「surface 400 已根治」**。
3. **摊 B 的 `mep.idd_field_alignment` 当前阻塞档结构上恒绿** ⇒ ⛔ 不得把跑通算作它的功劳。
4. **F-32**：全链无门校验 MEP 数值物理合理性（`mep.reasonability_bands` = `not_applicable`）。
   本三次里 **`accept_F` 的活动水平时间表被写成会归零的作息曲线** ⇒ EnergyPlus 报 14 条 Warning
   （18 Warning vs D/E 的 4 Warning），**而六条验收条件只看 `0 Severe`、看不见它**。
