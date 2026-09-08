---
name: ep-zero-severe-is-not-physical-correctness
description: EnergyPlus 跑完 0 Severe 只说明模型能算，不说明物理输入对——全链没有一道门在管 MEP 数值合理性
metadata: 
  node_type: memory
  type: project
  originSessionId: 88303e82-7787-4f6b-a409-b4861f320753
  modified: 2026-08-15T05:44:23.643Z
---

**2026-08-14 验收 3/3 全过的当天，最后一刻查出来的**（F-32）。

三次跑（`accept_D/E/F`）**几何顶点 400+60 逐位同序全同**、六条验收条件全中，
但 **`accept_F` 的 EnergyPlus 警告是 18 条、D/E 是 4 条**。差别来源查实：

- D/E：`Sch_ActivityLevel` = 恒定 **120 W/人** ✅
- F：模型把它写成**作息曲线** —— 上班时段 120、其余时段 **0**
  ⇒ EnergyPlus 报 14 条「活动水平超出 70–1000 W/人 典型范围」。

**⭐ 这是语义错误**：活动水平是「**每个人的**代谢率」，**不该随作息归零**；
人数的变化应该写在**人数时间表**里。模型把作息套到了单位人的代谢率上。

**⛔ 而全链没有任何一道门在管这件事**：`mep.reasonability_bands` 的实际状态是
**`not_applicable`**，message 写着 "reasonability bands deferred until MEP input is richer (§5.2)"
⇒ 唯一提了一句的是 **EnergyPlus 自己，而且只是 Warning**；
**验收条件只看 `0 Severe` ⇒ 结构上看不见它。**

## ⭐ 结论（把项目老洞察推进一格）

老的：**「EP 通过 ≠ 几何对」**（几何以 InterZone 门 + gate① 不变量为准）。
新的：**「`EP 0 Severe` ≠ 物理输入对」** —— 几何可以逐位相同，而**物理输入逐次在变**，
其中一次是错的，**没有任何确定性门看得见**。

## ⭐ 判别问法

**「这条链路上，谁在管【数值本身合不合理】？如果答案是『EnergyPlus 会警告』，那就等于没人管
—— 因为验收只看 Severe。」**

推论：
- **warning 数量的跑间差异是一个免费的观测量**，值得当例行对账项（本例正是靠 18 vs 4 才发现）；
- ⛔ 别把「验收条件全中」读成「这次跑是对的」—— 验收条件度量的是**可靠性**（能不能跑完），
  不是**正确性**（算得对不对）。两者今天第一次被明确区分开。

## 同族

- [[artifact-severity-depends-on-real-consumer]] —— 同日同一批：**危害等级取决于谁消费、怎么消费**。
- [[absence-conflates-causes-in-observables]] —— 「没有门报警」= 「没问题」+「没人管」两件事被压成同一个空白。
- [[real-chain-run-exposes-what-tests-cannot]] —— 又一次：**真链路跑一次撞出单测永远撞不出的东西**。
