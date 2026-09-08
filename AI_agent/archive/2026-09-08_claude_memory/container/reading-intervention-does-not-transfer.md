---
name: reading-intervention-does-not-transfer
description: ⭐⭐2026-08-05实证:review环效果不迁移(同会话内被审7轮的图墙4/4·零介入的下一张0/5)+「停下等审」是会话形态属性不是提示词属性+纠偏两类固有过冲
metadata:
  type: project
---

**2026-08-05 用会话内子 Agent（Haiku 4.5）复原 07-07 模式，拿到三条硬结论**
（逐字介入实录：`AI_agent/logs/experiments/2026-08-05_sm21_e1_restored/INTERVENTION_LOG.md`）：

1. **「停下等审」是会话形态的属性，不是提示词的属性。**
   把 07-07 kickoff 原文（含 `Do one pilot / Stop and wait for review`）原样放回 `claude -p` **headless** ⇒ **它不停**；
   换成**会话内子 Agent** ⇒ **立刻停下等审**。⇒ 07-07 那个「打回」能存在，是因为当时是会话内子 Agent。

2. **⭐⭐ review 环的效果不迁移。** 同一个子 Agent、同一个会话、刚被逐条纠正过 7 轮：
   **被审过的 1f = 平面墙 4/4 · 多画 0**；**零介入的 2f = 0/5 · 多画 3**；四张立面全缺 `facade.view_facade` ⇒ 判卷整段作废。
   它自陈 2F「interior wall positions **estimated from visual observation**」——**没人看着就退回目测**。
   ⇒ **介入的作用是「逐图纠错」，不是「教会方法」** ⇒ 07-07 的 8/8 更可能是「逐图纠完」而非「点拨一次学会」。

3. **纠偏有两类固有过冲**（一晚犯三次，非偶发）：
   - **只说「不是什么」⇒ 把对的一起删掉**（指出「那条链不是内墙」⇒ 它把**窗**全删了；
     引用规范「不要声明世界轴」⇒ 它把**必填的 `facade.view_facade`** 一起丢了）；
   - **⭐ 硬纪律诱发伪造**：要求「链必须闭合才能用」⇒ 它**编了一段 240 mm 让链凑够**并当成窗。
     **⇒ 立规则必须同时给合法退出口：「做不到就如实说做不到」必须被明确允许且不受惩罚。**
     补上之后它就诚实标注「顶链不闭合、1.48 m 无法解释」，不再编。
     **⇒ 直接影响 gate① `dimension_chain_closure` 严格档设计：硬门会诱发凑数，而凑出来的产物在结构校验上比诚实的失败更「干净」。**

**与 07-07 的剩余差异 8 条**（下轮排查序 D-1→D-2/D-4→D-6）：最值得先查 **CV 工具箱实现**
（`cv_toolbox/recipes.py` **+558 行**、4 个提交）—— 它直接改变「量」这个动作本身。

**⚠️ orchestrator 自己的两处错**：① 08-04 那一抽**不是 E1**（排期写「E1+主控介入保留」，我改成产品默认无介入路径）
⇒ 不能当「E1 复现失败」的证据；② **严格档是我自己套的**（E 臂跑测单原写给 sm24）——
实测 **07-02/07-07 两份满分产物在今天严格档下都会被拒收**（8/6 条 `dimension_chain_closure`）
⇒ 「做到之前的效果」与「过严格档」是两件事。见 [[quality-first-descend-from-strong-model]]、[[reading-lever-is-measurement-enforcement]]。
