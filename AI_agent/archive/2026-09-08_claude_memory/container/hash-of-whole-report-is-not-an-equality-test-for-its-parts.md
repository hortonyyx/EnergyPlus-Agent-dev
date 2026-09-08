---
name: hash-of-whole-report-is-not-an-equality-test-for-its-parts
description: 哈希整份报告得到的 digest 不能当作它内部某个子事实的相等判据——判几何是否相同必须比顶点，不能比 geometry digest
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 36572af3-39b0-4e52-b733-2f4d3e4cfc1e
  modified: 2026-08-11T04:08:06.749Z
---

**2026-08-11 实证。** 两次跑同一个 case，我拿 `geometry_checkpoint_digest` 判「几何是不是同一个」：

```
用户批过的  3409f90b…
新 run 的    f05e8187…     ⇒ 我据此停下核查（条件设得对）
```

**实际几何：460 个顶点逐个、逐位、同顺序完全相同。**
唯一差异 = 1_correction 的 LLM 给两个房间换了叫法（`Meeting` → `Conference`）。

**根因**：`geometry_checkpoint_digest` = `hash_obj(kernel_check_report)`（`approval.py:37-54`）——
它哈希的是**整份内核检查报告**，而**房间名嵌在报告里** ⇒ 任何非几何字段变了 digest 就变。
（同一事实的另一面 = F-20 设计审 sol 抓到的「往内核报告加**任何**一行，
哪怕 legacy 上一条无害的 `NOT_APPLICABLE`，**所有历史几何批准会一次性失效**」。）

**Why**：digest 的设计目的是**防篡改 / 绑定批准**，它要的是「**任何**变化都能察觉」——
这跟「判断某个**子事实**是否相等」是**相反方向的需求**。
拿它当子事实的判据，会把一切无关变化都读成「子事实变了」（假阳性），
反过来也永远证明不了「子事实没变」。

**How to apply**：
- ⭐ **判「两次跑的几何是不是同一个」必须比顶点**（提坐标三元组逐个逐位同顺序比），
  ⛔ 不许比 geometry digest、⛔ 不许比 `geometry_specs.md` 的文件哈希（房间名也在里面）。
- ⭐ 通用问法：**「这个 hash 覆盖的范围，是不是正好等于我要判的那件事？」**
  覆盖面**大于**待判事实 ⇒ 假阳性；**小于** ⇒ 漏判。
- ✅ **但「预先把 digest 相等写进验收条件」这件事本身是对的** ——
  本轮正因为 run_config 里写死了它，digest 一变就**强制停下核查**，
  才顺藤摸出「房间角色 meeting→conference 会进下游影响负荷 ⇒ 两个 run 能耗不可直接对比」。
  ⇒ **结论不是「别用 digest 当哨兵」，是「digest 报警之后必须换判据去核实，不能直接下结论」**。
- 同族：[[lock-must-exercise-real-entry-point]] 的「恒等锁≠正确性锁」·
  [[interface-sweep-gate-vs-range-check]] 的「有门必须落到那一行在约束什么」。
