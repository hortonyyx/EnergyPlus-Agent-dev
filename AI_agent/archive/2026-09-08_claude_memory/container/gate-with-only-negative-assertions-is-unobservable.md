---
name: gate-with-only-negative-assertions-is-unobservable
description: 一道门若只有「断言它 fail」的测试、没有「断言它 pass」的测试，则它恒红结构上不可能被测试发现，且所有 fail 断言会因此全部永远绿
metadata: 
  node_type: memory
  type: feedback
  originSessionId: eea2abdd-9543-43c7-99a6-72a452378a47
  modified: 2026-08-10T06:07:24.046Z
---

**2026-08-10 F-19 实证，新的假锁形态**：`kernel.window_parent_binding` 在真实产物上
**15/15 恒红**（几何其实是对的），而全仓 2339 绿一条没抓到。

**原因**：该门的 **7 条测试全部只断言 `fail`**（无 proof / 契约不符 / 载荷坏 / 删父面 /
把顶点改成 `(9,9,9)`…），**零正向锁**。orchestrator 在 `/tmp` 实测：拿它自己的夹具、
**零改动**跑这道门 ⇒ 本来就红 ⇒ **唯一测顶点的那条把 mutation 整行删掉照样绿。**

> ⭐ **一道门若只有「断言它 fail」的测试、没有「断言它 pass」的测试，
> 那么它【恒红】这件事结构上不可能被测试发现 —— 而且所有 fail 断言会因此全部永远绿。**

**⭐ 判别问法（补锁前先问）**：**「不加这处改动，这道门本来红不红？」**
—— 与 [[regression-case-must-prove-its-own-premise]] 是同一条的两个面：
那条说「回归用例必须自证前提」，这条说「一整道门可能连前提都没人立过」。

**比 08-09 sol 抓的那个 MAJOR 更隐蔽**：那次至少**有**正向锁，只是夹具选错了
（用了变换前的宿主线）；这次是**正向锁根本不存在** ⇒ 连「锁绑错了」都谈不上。

**⛔ 配套**：补正向锁时夹具必须走**真实构造入口**（F-19 里 = 必须经过 `build_geometry`，
手搓对象塞顶点会绕过规范化 ⇒ 锁的是另一回事），见 [[lock-must-exercise-real-entry-point]]。
