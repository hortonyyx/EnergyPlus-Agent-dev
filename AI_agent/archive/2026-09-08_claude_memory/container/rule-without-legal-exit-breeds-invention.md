---
name: rule-without-legal-exit-breeds-invention
description: 2026-08-15 一天内三次现形——门/规则提了要求却没给合法出口，模型就自己发明一个出口（绕过、造词、退回目测）
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9d92b917-9cde-4300-9937-0407cec6a78f
  modified: 2026-08-15T13:01:55.681Z
---

**判据**：**给模型立一个硬要求时，必须同时给出「满足它的合法形式」。**
只说「必须 X」而不说「X 长什么样 / 做不到时走哪」，模型不会停下 ——
**它会发明一个出口**，而那个出口通常在你的观测面之外。

**2026-08-15 一天内三次现形（同一形状）**：

1. **F-34 · 门有第二个入口**：`px_m_calibrator` 的跨轴一致性校验（超 0.30% 就 raise）。
   读图器把标定**拆成两次单轴调用** ⇒ 每次只有一个轴、无从比较 ⇒ **两次都 0 warning**，
   门形同虚设。合并成一次调用实测必 raise（偏差 23.07%）。
2. **F-34 变体 · 门挂在可选工具上**：另一轮里读图器**根本不调那个工具**，
   直接手算 px→m 写进产物 ⇒ 门连被绕过的机会都没有。
   ⇒ **挂在「模型选择调用的工具」里的校验不是门，是建议。**
3. **打回措辞诱发 schema 违规**：orchestrator 的打回写
   *"the label has to match how you got the number"*，**却没给合法词表**。
   模型用像素量了、又不是从尺寸链推的，觉得 `seen` / `dimension_derived` 都不贴切，
   于是**自己造了 `provenance: "pixel-measured"`** —— 六张图全中，gate① 全拒，多花一轮返工。

**同族既有条目**：[[reading-intervention-does-not-transfer]] 里「硬纪律诱发伪造，
立规则须给合法退出口」；F-34 那两条同时也是 [[lock-must-exercise-real-entry-point]]
（锁必须走真实入口）与 [[cache-in-front-of-a-gate-is-a-second-entrance]] 的同族。

**How to apply**：
- 写 directive / feedback / prompt 级要求时，**每条硬要求后面跟一句「合法形式是什么」**
  （枚举值、示例、或"做不到就写 null 并在 uncaptured 记一条"）。
- 设计确定性门时问两句：
  ① **「不调用这个工具，这道门还在吗」** —— 在，才是门；
  ② **「把输入拆开分几次喂，这道门还成立吗」** —— 成立，才是门。
- ⛔ 别把校验放在「模型自愿调用的工具」内部；要放在**产物必经的那一层**。
