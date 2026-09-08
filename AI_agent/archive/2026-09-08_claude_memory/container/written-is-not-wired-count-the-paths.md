---
name: written-is-not-wired-count-the-paths
description: 「写好了」与「接上了」之间有个不报错的缺口——一天之内出现七次
metadata:
  type: feedback
---

**2026-09-08 一天之内，同一形状出现七次**（as_drawn 腿补窗那条线）：

| # | 表现 | 为什么没被发现 |
|---|---|---|
| 1 | `build_verified_window_inputs_as_drawn` 写好了、**全仓零调用者** | 是死代码，不报错 |
| 2 | `_corner_only_ring` 只用在**足迹环**，cells 那行没动 | 足迹先挡住，症状驱动就停手了 |
| 3 | 归档重放门在 as_drawn 上**空转** | 两条腿都产空目录 ⇒「空==空」永远通过 |
| 4 | 造窗**没接进 flow** | 归档 `attempts=3/accepted=3` 看着像跑通，实际 `windows=0` |
| 5 | 重放路**不跑**造窗 ⇒ `chain_replay_producer_drift` | 防篡改锁替我发现的 |
| 6 | 腿分派只加在**一个**校验函数，而 `_catalog` 有**五个**重建点 | 主路径先通了，第二个校验点在 `2_modelling` 才爆 |
| 7 | 渲染器仍读 legacy `strokes` ⇒ 产 400×80 **空白图** | 判卷看空白图，不报错 |

**Why**：新增一个确定性推导后，只把它接上**主路径**就会「看起来работает」。
而同一份产物往往被**多条路径**消费：生产 / 归档重放 / 判卷 / 渲染 / 各处校验函数。
⛔ 缺哪一条都不报「你忘了接」，只会在**很远的地方**以别的名字爆出来。

⚠️ 第 4 条最险：**成功的读数（`accepted=3`）比失败更容易骗人** ——
它之所以成功，恰恰**因为**那段代码没执行（没有窗就没有冲突）。

**How to apply**：
- ⭐ 新增确定性推导，先问「**它有几条路径应该经过？**」，逐条列出再逐条确认。
  典型清单：生产路径 / 归档重放 / 判卷 / 渲染 / 所有「重建后比对」的校验函数。
- ⭐ **判据必须是「只有那段代码执行了才会出现的读数」**（本例 = `windows` 从 0 变 31），
  ⛔ 不是「跑通了没报错」。
- ⭐ **同一个 helper 有几个调用点，就 grep 出来数一遍** —— 第 6 条正是没数。
  （我上午刚要求席位把降维「从例子提到那一类」，自己却在腿分派上修了例子没修类。）

配套：[[enumerate-the-class-not-the-example-found-six-more]] · [[neuter-must-cover-wiring-not-just-mechanism]]
· [[gate-teeth-direction-follows-fixture-inventory]]
