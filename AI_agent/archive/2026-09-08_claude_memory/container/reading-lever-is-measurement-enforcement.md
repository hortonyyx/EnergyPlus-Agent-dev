---
name: reading-lever-is-measurement-enforcement
description: 2026-08-03 定论——reading 的杠杆是「工作模式」不是「纠偏次数」，修法=接口层强制测量（读图器不写公制坐标）；controller 存废靠实验说话
metadata: 
  node_type: memory
  type: project
  originSessionId: c8741583-100a-4fe8-944f-bdd3786a2506
  modified: 2026-08-03T14:46:10.574Z
---

**2026-08-03 用户与 orchestrator 当面达成，凌驾于此前 controller 设计辩论之上。**

**⭐ 三条判决性事实（本轮新查明）**：

1. **07-07 的事前 prompt 没丢，在 git 里**（推翻 sol 架构审 P-2 BLOCKER 的前提、也推翻 [[reading-supervision-contamination]]
   里「事前完整 prompt 从未落盘」那条）。启动命令 = 老 `new_case_guide.md` 附录 A 三行
   「Read `skills/intake_pipeline/0_reading/session_kickoff.md` and follow it for case X」，
   而 kickoff 当时**已是版本化单文件**，逐字可查：`git show 891356d:skills/intake_pipeline/0_reading/session_kickoff.md`。
   用户确认「后面被做成 kickoff.md，没有额外的东西」。
2. **⭐ 那份 kickoff 的 Workflow 段逐字写着 "Do one pilot image first / Stop and wait for review of that pilot"**
   ⇒ **07-07 的「打回」不是临场干预，是产品 skill 里写死的 review 环。**
   ⇒ P-2 三个缺口关掉两个；**仅剩「我那次 review 说了哪几句原文」未落盘**，该条维持「待验假设」。
3. **打回起的作用不是修错、是切换工作模式**。同尺对照：07-07 = 内墙 100%/多画 0m/13 条
   `dimension_derived`（单条引 ≤12 条尺寸标注）/19 次工具调用（crop_zoom 11）；
   今天 Sonnet 无监督 = 92.1%/多画 6.77m/10 条全 `seen`/引用 ≤2/crop_zoom **0 次**。
   **这个差别返工两轮造不出来——它从第一笔就不同。**

**⇒ 结论（用户认可）**：
- 用户原判「杠杆不在那一两次纠偏上」**成立**；「Haiku 是合格 worker」**成立**（带工具箱与 Sonnet 逐项相同、不带全线归零）。
- 但「长程任务不行需要领导」这个说法**改掉**：真因是**任务被分解成「扫一遍描述」而不是「枚举候选逐条量」**——
  形状问题，不是耐力问题。
- **⛔ 回纠不该是主机制，应退化成异常路径**（依赖「事后有人发现」的机制，在没人看的那轮自动失效——07-08 至今就是）。

**⭐⭐ 主修法 = 接口层强制测量（= 升级版 R1.5，用户 08-03 同意）**：
**读图器不写公制坐标**，只写「源图像素锚点 + 引用了哪几条尺寸标注」+ 标定变换，
**公制坐标由确定性代码唯一换算**。三个后果同时发生：
① 目测在接口上表达不出来（`dimension_derived` 从可乱填的 provenance 标签变成**唯一输入形式**）；
② 左右反向表达不出来（sol N-6 的原始目的，见 [[one-ruler-replay-old-artifact-perfect]]）；
③ **不需要任何 controller** 就能把 07-07 的模式变成默认模式。
排期：R1（批 B/C）之后**立即**，R3/R4 冻结接口之前；**⛔ 不得先跑新基线再补**（否则「方向错」与「画错」混成同一低分）。

**残留缺口（真的剩下）** = sol P-1 反例：CV 工具找到真墙、读图器 crop 看了、判成家具、老实写 `rejected`。
测量强制解决「没去量」，**解决不了「量了但语义判错」**。该块需要眼睛，但性质变了：**逐候选、有界**
⇒ 形态是「**只看被点名 crop 的小复核**」（无指挥权，只对代码点名的候选说 yes/no），**不是一个 Flash 档领导**。
**⇒ 顺序：先做测量强制、跑两抽、看剩下的错是什么形状，再决定要不要建这块。**（这同时化解架构审 F-3。）

**⭐ 用户定的决策机制：「reading 到底怎么解决，靠实验说话」**
⇒ **controller 存废不再靠设计辩论，靠 R1.5 之后的实测两抽决定。**

**⭐⭐ 2026-08-03 晚补：R1.5 的必要性已从「设计判断」升为已坐实的接口缺陷（出 R1.5 问题书时查实）**
—— gate① **本来就有**一条检查在管「声称按尺寸推导的墙必须真的引用得到标注」
（`_dimension_derived_refs`，`src/validator/checks/reading.py:793`，⚠️行号会漂、按函数名找），
**但它第一行是** `if provenance != "dimension_derived": continue`
⇒ **读图器把 provenance 写成 `seen`，这道题整个跳过、落成 `NOT_APPLICABLE`。**
今天 Sonnet 那 10 条墙全写 `seen` ⇒ 该检查零压力零阻断。
**⇒ 考生自己填的一个字符串，决定了这道题考不考**（与批 B 修的 L-22「产品内容不得决定考卷」**同形**）。
**这是本项目第五次撞见「规范写了、没有机器验证」**（前四 = `self_check.*` 自评字段 / CV 证据 /
`access_log.jsonl` / 立面方向契约，见 [[reading-supervision-contamination]]）。
⇒ 问题书里最承重的一问 = **能否用确定性代码验证「被引用的标注确实在锚点附近、且其数值与两锚点像素距离一致」**
（若成立即把「尺寸链自洽」升级成「与像素一致」，正面回答 sol「自洽但每个数字都错的链照样 pass」的反例）。
问题书已就绪：`AI_agent/logs/reviews/request/2026-08-03_reading_coordinate_source_r1_5_design_brief.md`，
**等 R1 全绿即派跨家族双独立出案**。

**确定性代码能不能撑复杂度（用户第二问）的答案 = 分三类**：
- **确定性换算**（像素→公制、尺寸链闭合、标定 RMSE、跨图对齐）= 纯算术、不含建筑学假设 ⇒ **随复杂度长得很好，该多投**（测量强制属此类，踩在不变量 #6 正确一侧：**约束形式，不烤死内容**）；
- **确定性判据**（什么算画完/这条墙合法）= 含建筑学假设 ⇒ 复杂度上来会失效，**必须带 profile + 适用域 + 允许弃权**（批 B 的 applicability 机制就是在建这个）；
- **代码永远看不见「漏了什么」**（没有 GT，只看得见「工具找到的候选里哪些没处置」），且**复杂度上来盲区会变大**（现已 5 候选 vs 16 段墙）⇒ 出口只有 GT（dev 期）与人（生产期），**不该指望代码接管**。
