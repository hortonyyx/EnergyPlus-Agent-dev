---
name: shadow-module-swap-must-touch-parent-attr
description: sys.modules 影子替换只换了一半——from pkg import mod 走父包属性，monkeypatch 打错对象造成假红
metadata: 
  node_type: memory
  type: reference
  originSessionId: d1ad54e7-585f-430b-b531-0de8da4d2911
---

2026-08-29 F-126b 变异矩阵实测撞上：把变异模块塞进
`sys.modules['src.agent.judge.as_drawn.denominator']` 后，测试里
`from src.agent.judge.as_drawn import denominator as den_mod` 拿到的**仍是原模块**——
`from X import Y`（Y=子模块）读的是**父包 X 的属性**（import 时 setattr 上去的），
不是 sys.modules。于是 L2b 的 `monkeypatch.setattr(den_mod, "run_p1_plan_view", ...)`
打在原模块上、被测函数走影子模块的全局 ⇒ geometry 照真跑 ⇒ `DID NOT RAISE` 假红，
四个变异的「旧锁」读数全被污染。

**修法**（两行）：换 sys.modules 的同时 `setattr(sys.modules[parent], leaf, mod)`。
判别信号：假红集中在**带 monkeypatch 的 seam 测试**、且报 DID NOT RAISE。

配套教训：变异方向本身也要实测——GROUP_QUANT 粗化（→2）实测**无牙**（夹具无 1 cm
内相邻 const）、细化（→5/6）数学恒等（值已量化到 4 位）；有牙方向是**回到历史真实
缺陷形状**（→4，即 2026-08-24 修过的分组裂开）。相关：[[cross-representation-mutation-must-be-equivalent]]、[[lock-must-exercise-real-entry-point]]。
