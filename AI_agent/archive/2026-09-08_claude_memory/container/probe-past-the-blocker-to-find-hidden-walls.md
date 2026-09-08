---
name: probe-past-the-blocker-to-find-hidden-walls
description: 用历史跑通产物绕开卡点先撞后段——当场撞出已潜伏一个月的 4_mep 签名崩；串行修墙会让后段缺陷无限期潜伏
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2a823d9a-5699-4868-9da3-62b70d1ab41c
  modified: 2026-08-05T15:31:06.106Z
---

**2026-08-05 用户定的打法**：「**能不能直接拿之前端到端跑通的中间产物直接来试呢？反正是探工程问题。**」

拿 6 月那个真跑到 EP 的 golden run（`sm21_anchor/run_2026-06-16_opus_e2e`）的中间产物，**绕开当前卡点**，
把后面的段先撞一遍。两条探针：

- **探针 B（零改动零脚本）**：`5_intakeoutput/intake_output.json` → `run_full_pipeline.py --intake-from`
  ⇒ **`EnergyPlus Completed Successfully-- 6 Warning; 0 Severe Errors`** ⇒ **下游半边健康**。
  可行的前提 = `IntakeOutput` 11 字段是**稳定交接契约**（不变量 #3），逐字未变。
- **探针 A（需播种）**：`1_correction/correction_geometry_snapped.json`（**内核之后**那份，⛔ 不是 `correction_geometry.json`）
  → 播种成 accepted attempt → `flow --from 2_modelling`。老件是 schema v1 ⇒ 走 `rectangular` 档。

**⭐ 当场兑现**：撞出 **F-10** —— `check_mep() got an unexpected keyword argument 'run_profile'`
（调用方 `run_stage.py:577` 07-06 加、被调方 `checks/mep.py:95` 07-01 签名没有）
⇒ **任何走 flow 跑到 4_mep 的 run 必崩，已断整整一个月无人发现** —— 因为这一个月没有东西走到过 4_mep。

**Why**：前一堵墙（F-9，卡在 1_correction）**一直遮着** F-10。
**⇒ 「串行修墙」会让后段缺陷无限期潜伏**；每修好一条只推进一小段，后段永远拿不到证据。

**How to apply**：
1. **任何「链路卡在某一段」的局面，都先问：能不能拿历史跑通产物绕过去，把后段并行撞一遍？**
   代价极低（探针 B 零改动），收益是把「未知空间」一次砍掉一大块。
2. **选对产物**：要**内核之后 / 段输出**那一份，不是 LLM 原始抽签。稳定契约点（如 `IntakeOutput`）最好用。
3. **播种必须走真实归档入口**（`StageRunner.record` + `manifest.save`），⛔ 不手搓 `attempts/NNN/output.json`
   —— 手搓的东西证明不了真实入口能吃它。
4. **明写局限**：老件多是旧契约档（v1），**查不到新契约（v3）专有接线**的问题。
   ⛔ 不得把「探针绿」说成「真实那条路通了」。
5. **探针是「探」不是「修」**：撞到墙逐条记录、⛔ 不修、⛔ 不放宽 gate 让它过去 —— 被拦住本身就是要的信息。

相关：[[real-chain-run-exposes-what-tests-cannot]] · [[neuter-proves-wiring-not-discriminating-power]] ·
[[stop-and-report-catches-dispatcher-errors]] · [[pipeline-0-5-refactor-status]]
