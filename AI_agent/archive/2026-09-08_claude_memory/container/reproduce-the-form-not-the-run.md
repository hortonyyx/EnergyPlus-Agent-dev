---
name: reproduce-the-form-not-the-run
description: 2026-08-18 用户三次纠正——目标是「重复出好成绩的那个形式」不是复刻某一次；07-02 Sonnet 无工具箱是该形式的【来源】不得当参照；用完整 worktree 而非手搓复现，否则还掺着自己的判断
metadata:
  type: feedback
---

**用户 2026-08-18 三句纠正，每句拆掉 orchestrator 一个错。**

## ① 目标 = 形式，不是某一次

> 「reading 的目的不是说要保证跟之前的某一次一模一样，而是要恢复到**之前能稳定出好成绩的形式**，
> 之前不是偶然，是好几次共同出了好结果，我们现在不知道哪里改坏了，是要做**修复**，而不是回滚到某一次具体形式。」

**形式 = CV 工具箱 + 指令要求使用（measure-before-draw）+ pilot 停等 + 一次流程返工。**
三实例、跨**两家族两建筑**：07-07 haiku(sm21) 9/9·7/7 · 07-08 gpt54mini(sm21) 9/9·6/7 ·
**07-07 haiku(sm24) 人工肉检满分（当时无 gt）**。

⇒ orchestrator 因为把目标读成「复刻 07-07 那一次」，去恢复了图片原尺寸，
**把 F-51 修好的帧错位又打开了**（两次）。

## ② ⛔ 07-02 Sonnet 不是该形式的实例，是它的【来源】

07-07 README 对照表明写：`run_2026-07-02_sonnet_flow_e2e` = 「完全恢复版，**无工具箱**」。
好 reading 最先是 **Sonnet 自发**做到的，我们把它**拆解固化成 CV 工具箱**。
⇒ 拿它当「工具箱这条路通不通」的判别臂 = **用产物的来源去验产物**，confounded。
⇒ 正确的判别臂 = **07-08 的 gpt-5.4-mini（codex）**，同形式、不同家族。

## ③ ⭐⭐⭐ 用完整 worktree，别手搓复现

> 「你别用复现的，直接用源头的，排除一切干扰」

`git worktree add <path> <commit>` 一开就查出：orchestrator 手搓的复现用的是 **`891356d`**，
而 07-07 实际跑在 **`723b0f9`**（891356d 是**记录**这次跑的提交，多 **+330 行 prescan 实现**
和 13 行 `cv_toolbox.md`）⇒ **orchestrator 把 07-07 跑完之后才加的东西喂了进去。**

⇒ **判据：只要还是由我挑哪些文件、哪个提交，复现里就还掺着我的判断。**
完整树把这个环节整个去掉。**同族** [[green-suite-is-a-property-of-tree-and-launcher]]。

## ⭐ 附带最值钱的一条：git 里存着过程记录

`AI_agent/logs/experiments/2026-07-07_haiku_cv_retest/README.md` 一份文件推翻三条推断：
打回**只有一次** · directive **没丢**（「指令全文记 run llm.yaml provenance」）·
**r1 难看是基线行为**（「弱 VLM 首抽散漫……是跨 case 复现的稳定短板，流程纪律可拉回」）。

⇒ **判据：翻历史先找当时的实验 README，别从产物反推。** 我从产物反推出的三条全错。

相关 [[read-the-diff-before-guessing-variables]] · [[baseline-unauditable-dont-chase-its-number]] ·
[[reading-lever-is-measurement-enforcement]] · [[vlm-pixel-frame-differs-from-file-pixel-frame]]
