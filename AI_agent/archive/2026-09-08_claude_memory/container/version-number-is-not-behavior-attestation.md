---
name: version-number-is-not-behavior-attestation
description: 格式版本号/配置声明证明不了「产生它的代码是修好之后的版本」——修 bug 不改版本号，所以同一个版本号横跨修复前后
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 95485813-f489-466d-bdeb-288b7236b5e3
  modified: 2026-08-12T03:09:59.495Z
---

**2026-08-12 sol 复审抓的 BLOCKER，orchestrator 已独立复现。**

判卷要判「这份产物的坐标量到墙外皮还是墙中线」（差 0.12 m，判错整圈偏）。
昨天的修法 = **看产物自己声明的 `schema_version == "3"`**，是就信、不是就拒判。
代码注释里自己写着 **"`schema_version` is used as the capability_profile proxy"** —— **没人去证这个 proxy。**

**真实反例（两份产物都在仓里）**：

| run | `schema_version` | run_config `capability_profile` | 实际 footprint |
|---|---|---|---|
| `f17_e2e_verify`（08-09）| `3` | `orthogonal_polygon` | **`[0.12,14.88]` 中线框** |
| `continuous_e2e`（08-11）| `3` | `orthogonal_polygon` | **`[0,15]` 外皮框** |

**版本号一样、配置逐字一样，坐标框不同** —— 因为差别不在格式、不在配置，
**而在中间修好了一个 bug（F-17）**。⇒ 08-09 那份被判**五项全 pass**，实际每条外边差 0.12 m。

> ⭐ **版本号 / 配置声明是「我是什么形状」的声明，不是「产生我的代码有没有那个 bug」的证明。
> 修 bug 从来不改版本号 ⇒ 同一个版本号必然横跨修复前后。**

**⭐ 判别问法**：**「我拿 A 当 B 的证据，那么 A 变过而 B 没变（或反过来）的产物，盘上有没有？」**
—— 本例 5 分钟就在仓里找到了，而且**翻转点早就写在 plan.md 里**
（「f17 run 及以前全是 `[0.12,14.88]`，f18 run 起变 `[0,15]`」）⇒
**⛔ 我自己写下的记录，在我自己写派工单时没去查。**

**⛔ 修法的岔口也踩了同一个坑**：想拿「产物里有没有 `deterministic_core.envelope_atomic_transform` 记录」
当 post-transform 证据 —— **实测 `if not intents: return` 早返回不留记录**
⇒ 图纸本来就按外皮标注时，核什么都不用改，合法产物同样没记录。
**今天所有 `deterministic_core.*` 记录全是有条件的，一条无条件的都没有。**
⇒ 见 [[absence-conflates-causes-in-observables]]（同一天第三次现形）。
**⇒ 用户拍板修法 = 让确定性核盖一个【无条件】的「我跑过、版本是 X」印章。**

配套：[[free-correctness-evaporates-when-representation-changes]]（F-17 正是那次换表示，
版本号没跟）· [[stop-and-report-catches-dispatcher-errors]]（本条是派工方错误率第 14 例，
且是**我的分类穷举了「身份不合法」的各种形态、漏掉「身份合法但过时」**）。
