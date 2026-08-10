# reading 脚手架完整恢复 — 实测验证（plan N1f/N1e 残留①）— 2026-06-30

## 目的
`6.27_ReadingScaffoldFullRestore` 把旧脚手架（`127ba06` sm21_pre 时代）里 **有效 ∧ 与新架构兼容** 的约束
一条不漏补回当前脚手架后，**实测**冷启 Sonnet 用恢复后脚手架重读 sm21，`score_reading_vs_gt` 对 gt 逐元素对账。
口径（用户 ratify，[[reading-scaffold-restore-policy]]）：**sm21_pre = 回归地板不是天花板**；本实测 = 回归地板 + 弱模型评测 harness，**非逐条门**。

## 设计（单变量）
- 唯一变量 = **脚手架版本**：当前 HEAD `56a34dd` 的全恢复版 vs 06-25 弱/强 prompt A/B 基线。
- skill 四件套 = 恢复后版本（md5 见 `_provenance.txt`）；启动经版本化 `session_kickoff.md`。
- 执行 = **2 个冷启隔离 Sonnet 子代理**（model `claude-sonnet-4-6`），物理沙箱隔离（只喂 images+skill+worked-example+testdata，gt 留仓库外、prompt 硬禁读）。主控 orchestrator = Opus 4.8。
- 测量 = `score_reading_vs_gt` 按 gt 坐标逐元素对账（权威口径，[[judge-gt-authoritative-images-auxiliary]]）。
- 注：硬隔离仍是 prompt 级（contamination 机制化是 backlog）；n=2/run 方差大。

## 结果（score_reading_vs_gt 对 sm21_anchor gt）

| run | 墙命中 | 过度分割（多余墙） | 窗命中(plan) | 1f 竖墙偏移 | 2f 竖墙偏移 |
|---|---|---|---|---|---|
| **sm21_pre 标杆** | 9/9 | **0** | 14/15* | ~0 | ~0 |
| 06-25 weak_2（弱臂最好） | 9/9 | +2 | 11/15 | −0.06/−0.18 | 0 |
| 06-25 strong_1（强臂） | 9/9 | +1 | 7/15 | −0.06/−0.18 | +0.15 |
| **r1（恢复后脚手架）** | **9/9** | **0** | 8/15 | −0.06/−0.18 | **0.0** |
| **r2（恢复后脚手架）** | **9/9** | +4（1f） | **12/15** | −0.06/−0.18 | −0.16/+0.16 |

\* sm21_pre 标杆窗 14/15 来自老脚手架全图轮的立面口径；本 harness 按 plan-view 窗计数，绝对值不直接可比，看趋势。

详分见 `score_r1.txt` / `score_r2.txt`；原始 reading 在 `readings/sonnet_r{1,2}/`。

## 结论

1. **墙结构达回归地板**：两轮**墙均 9/9**、坐标偏移 ≤0.18m（r1 2f 竖墙 0.0m 完美）——恢复后脚手架稳定把
   真隔墙全找对，达 sm21_pre 墙标准。这是脚手架恢复要守的核心，**守住了**。
2. **过度分割仍受 run 方差主导，未被脚手架根治**：r1 过度分割 **0**（= sm21_pre 干净）、r2 却 **+4**
   （1f 把窗洞位置 3.44/6.3/8.7/11.36 当竖墙）。同一恢复后脚手架、同一图，两轮一干净一过度分割
   → **run 间方差 > 脚手架增益**，与 N1d/N1e「受控隔离下 Sonnet 戏剧性缺陷不复现/方差主导」同结论。
   恢复后脚手架使"达 sm21_pre 干净"**可达但不必然**。
3. **窗位仍是残留弱项（指向模型）**：plan 窗 8 / 12 /15，跨度大、run 方差重，与 06-25「窗位残留=模型」一致。
4. **回归地板 + harness 已建立**：恢复后脚手架 + `score_reading_vs_gt` 组成可复跑的弱模型评测 harness；
   sm21_pre 量化标杆（墙9/9·过度分割0·竖墙偏移~0）已被 r1 复现，证明地板真实可达。

## 启示（下一步候选，非本轮）
- 脚手架（prose 约束）已把**墙/结构**这条线推到地板；剩余 **过度分割方差 + 窗位** 是**模型/输入**侧 lever，
  非更多 prose：杂物/尺寸链 tick 掩膜 · 局部放大裁图 · 加 reread 预算 · 换强模型（Opus 一次干净）—— 见 N1d 末。
- 弱模型北极星：把本 harness 复用到开源 VLM（plan 远期），看恢复后脚手架对弱模型的补偿幅度。
