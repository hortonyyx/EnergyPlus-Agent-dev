---
name: harness-upgrade-is-the-goal-not-the-score
description: ⭐⭐⭐ 2026-08-21 用户战略换挡——跑测是为了升级 harness，分数只是读数；四步循环=最强模型先下场造 SOP，再固化，再降智验收
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 447bc096-3f6f-4b71-bc17-622c569596ee
  modified: 2026-08-21T16:24:57.517Z
---

**跑测的目的 = 升级这套 harness，不是拿分。分数只是「harness 硬不硬」的读数。**

**开发循环（此后按此走）**：
1. **最强的模型（orchestrator 本人）亲自下场做**这个 case 的 reading —— 边做边定：
   要不要造新工具？工具怎么调？最好的 SOP 是什么？哪里易翻车、该用什么约束住？
2. **先摸出工作流，并且自己真做出一份不错的输出**（不是纸上谈兵）。
3. **把能固化的固化进 harness**：工具、skill、提示词、门与约束。
   ⭐ 用户原话「沉淀哪些东西怎么沉淀我这里是举例子，不是说一定要拆分成这样，**以加强这套 harness 为目标**」
   ⇒ 拆分方式由 orchestrator 定，用户只给目标。
4. **逐级降低模型智力验收**。弱模型也能做出来 = 固化成功。

**Why**：⛔ 反过来做（一上来让低级模型跑、指望它做对、砸了再猜为什么）**是许愿，不是开发**。
项目一年来反复在做第 4 步而跳过 1–3，所以每次失败都变成「猜是哪个变量」。

**How to apply**：
- **模型强度从干扰项变成自变量**：以前「换模型 ⇒ 三变量未控、不下结论」；
  现在「这套 harness 能撑到多低的模型」**本身就是质量指标**，降档跑是设计动作。
- ⇒ **三种 reading 模式作废**（autonomous / controlled / dev 职能）——
  模型强度是**一根连续刻度**，不是并列赛道。覆盖 [[reading-batch-target-controlled-lane]] 与
  [[707-mode-accepted-reading-agent-deferred]]。
- **不再纠结「复原 07-07」**（覆盖 [[research-first-p0-is-speed-not-completeness]] §0.0 那个第一目标）：
  07-07 的身份从「靶子」变成「样本」—— 要解剖它为什么干净，不是复现那个分数。
- ⛔ **硬约束（用户同日加）：harness 只做增量升级，不为新 case 特化，历史 case 也要照样做得好。**
  ⇒ 每条沉淀物都要先过一遍「拿它去跑 sm21/sm24 会不会反而变差」——
  实操手段见 [[offline-fixtures-test-gate-discriminating-power]]。
- ⭐ **我亲自下场时的硬约束（用户 08-21 补充）**：要拿出的是**尽量降低模型智力依赖的 harness 方案**，
  ⛔ 不能「我靠目视全做对了，然后说就这么做就行」—— 目视做对不可移植，弱模型接不住。
  实证支撑：07-02 那次 9/9 的精度来自**自己写代码去量**，不来自感知（[[offline-fixtures-test-gate-discriminating-power]]）。
- **多路径可行时的处置（用户 08-21）**：**先做成工具**，后续逐渐升级后再对比取舍 / 综合 /
  或干脆留成**不同 case 的适配性选项**（哪种图纸类型更适合哪条路）。⛔ 别过早钉死一条。
- **隔离铁律的适用范围（用户已同意放开）**：探索/造 SOP 阶段 orchestrator **可亲自看图亲自做**；
  仍受 08-02 四条铁律约束：不给生产喂**信息**（可给思路/方法/工具）· 这类跑**不作成绩** ·
  **一个 case 的收官验收必须 orchestrator 不在场时完成**（跑已固化工序 + 已冻结工具箱）。
  ⇒ 这不是推翻 [[controller-must-stay-out-of-product]]，是把 08-02 写好却从没当主线用的
  「dev 期开发者职能」扶正。
