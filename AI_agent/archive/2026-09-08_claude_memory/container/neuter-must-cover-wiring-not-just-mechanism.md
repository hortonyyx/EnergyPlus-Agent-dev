---
name: neuter-must-cover-wiring-not-just-mechanism
description: ⭐⭐ neuter 必须同时覆盖「机制」与「接线」——只 neuter 函数内部会漏掉「调用点没传对参数」整类假锁
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9d75dcca-e6c9-45d8-90f4-0ac5a43ebc8f
  modified: 2026-08-11T09:39:19.427Z
---

**2026-08-06 轻门实犯坐实（F-11）。**

施工席做了**四个方向**的 neuter，全部落在**函数内部**（机制层）；
orchestrator 换到**调用点**（接线层）一做就照出假锁：

- 那把锁 `test_foundations_path_skips_terminal_vertex_drift` **自己传 `include_vertex_drift=False`**
  去直调 validator，**从不经过 `cross_ref_foundations_node`**；
- 把调用点的 `include_vertex_drift=False` 删掉 —— **这就是原样复原缺陷本尊** —— **8/8 依然全绿**；
- 全仓唯一驱动该节点的另一个测试喂的 state 无 snapshot ⇒ 两种情况都不产 drift、也照不出来。

**⇒ 判别问法：把调用点改回缺陷形态，锁红不红？**

**Why**：缺陷复发最常见的形态不是「函数写错了」，而是**「调用点没传对参数 / 没接上」**。
只锁机制 = 锁住「这个参数管不管用」，锁不住「谁负责传它」。
这是 [[lock-must-exercise-real-entry-point]] 的**精确化**：真实入口不只是「走产品路径」，
还要求 **neuter 打在接线上**。也是 [[neuter-proves-wiring-not-discriminating-power]] 的第三个方向
（前两个：变红≠有分辨力 · 分辨力通过≠每个抛出点分得对）。

## ⛔⛔ 2026-08-11 orchestrator 实犯：**判「是否已接线／已合并」用了形状匹配（grep），被 sol 用行为验证推翻**

F-9 S1 要把 4 处 facade sign convention 副本合并成单源。我做轻门时 **grep `_BASE_SIGN\s*=` / `mirrored\s*\^`
⇒ 零残留、XOR 全仓只剩一处** ⇒ 判「合并完成」。**错。**

sol 的判据是**行为验证**：把共享的 `facade_convention.resolve_sign` monkeypatch 掉，看哪些 call site 跟着变。
orchestrator 独立复现：
- `derive_view_projection_frame`（新入口）`-1 → 1` **跟着变** ✅
- **`derive_facade_frame`（legacy 入口）`-1 → -1` 纹丝不动** ⛔ ⇒ **它根本没接线**

原因：那处用**两次条件取反**等价实现了同一个 XOR ⇒ **任何形状匹配都抓不到**。
而它**不是死代码**（`validator/checks/correction.py` 在真实 correction 检查里调它）。
**施工席自己写的 AST 结构锁同样漏检**（只认 `ast.Assign(value=ast.Dict)` 的三个精确变量名 + `ast.BinOp(BitXor)`）
⇒ sol 实测 `AnnAssign + operator.xor + dead import` 的变体**照样放行**。

⇒ **判别问法：「把共享实现中和掉，这个调用点的输出会不会跟着变？」**
不变 = 没接线，**无论 grep 多干净**。等价实现的写法无穷多（连续取反 / `operator.xor` / `!=` /
`AnnAssign` / `dict()` / alias），**形状匹配注定漏**。
配套：AST 锁若保留，要断言**目标函数确实调用了 module attribute**，而不是搜精确语法；
**只检查 import 形状不检查调用 ⇒ dead import 也能过**。
与 08-10 那条「**行号定位优于形状匹配**」同源，这次是**行为验证优于形状匹配**。

**How to apply**：
1. 每个「参数/开关/标志」类修法，**必须有一把锁真实驱动那个调用点**，⛔ 不许在测试里自己传那个参数
   —— 让被测节点自己决定传什么，**那才是被保护的行为**。
2. orchestrator 独立 neuter **必须换一个方向**，不重复施工席做过的方向。08-06 是这条纪律
   第一次真正兑现价值（此前更像仪式）。
3. 同族的两条：**夹具必须覆盖真实产出的形态分布**（墙 3：夹具全是人手写的 IDD-correct 顺序，
   而真实 LLM 从不产出这种形态 ⇒ 测试永远绿、真链路必崩）· 判别问法
   **「这个夹具的形状，真实生产方真的会产出吗？」**

相关：[[real-chain-run-exposes-what-tests-cannot]] · [[lock-must-exercise-real-entry-point]] ·
[[neuter-proves-wiring-not-discriminating-power]] · [[stop-and-report-catches-dispatcher-errors]]

## 2026-08-24 再犯，形状更隐蔽

写了一个「单像素作弊」变异去证明判据免疫，**它写的键叫 `opening_ink`，而消费者读的是
`ink_by_family`** ⇒ 变异**从没走到被测分支**，它拿到的 0.0 分是**别的原因**（挖空本身）挣来的，
我却据此写下「一个像素推不动这条判据」，还当作「二审意见已解决」送进第三轮审。
跨家族审一 grep 就看穿。改写成消费者真实读取的 schema 后实测：**36/194 个伪造空档确实越过了阈值**。

**How to apply**：写变异前先 `grep` 消费者读的**字段名**，并让变异**自己报出「有几条真的命中了被测分支」**——
「免疫」这个结论只有在命中数 > 0 时才成立。同族 [[two-kinds-of-latency-no-ruler-vs-never-reached]]。
