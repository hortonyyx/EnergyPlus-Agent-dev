---
name: reading-scaffold-restore-policy
description: reading 脚手架补全口径——为弱模型北极星补全有效约束、先补全后精简、sm21_pre=回归地板
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 92906b65-e3a9-4c4e-97ff-68ebac314559
---

用户 2026-06-27 ratify 的 reading 脚手架恢复口径(改了我原来的框架):

**不是"补到 Sonnet 达 sm21_pre 就停"**。北极星 = 弱/开源 VLM,脚手架=降智补偿;按 Sonnet 调到"刚好够"= 给真正目标欠配,且易过拟合 Sonnet 失败模式。

- **先补全**:把旧脚手架(`127ba06` sm21_pre 时代)里 **`有效 ∧ 与新架构兼容`** 的约束**一条不漏**补进当前脚手架。
- **后精简**:"弱模型文字约束多会否适得其反"的顾虑 **不预先砍**,留后期用检索库/代码化精简。本轮先不要有缺漏。
- **载体优先**:能做确定性代码门的优先代码门(弱模型跟 prose 更差)。
- **sm21_pre = 回归地板不是天花板**:`score_reading_vs_gt` 实测 = 回归地板 + 攒换弱模型要复用的评测 harness,**不是逐条补一点测一次的门**。
- **排除**:与新架构冲突/有意删的(如 facade 世界轴表——硬编码正交、斜交/多边形上主动误导)+ 已查实无效杠杆(prompt 强度)不补。

已落地 `6.27_ReadingScaffoldFullRestore`(走 [[codex-execution-protocol]]:Claude 出方案→Codex 审→Codex 执行→Claude 全面审)。详 plan.md N1e/N1f。续接 [[reading-quality-investigation-2026-06-24]]。
