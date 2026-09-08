---
name: mutation-shape-silent-swallow-beats-deleted-check
description: 验牙变异要造「静默吞掉」形态，不是「删掉检查」——删检查常让 None 落进下游崩成 AttributeError，红得真假难辨
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ff8fa46e-70b6-44b6-bb86-c79dd062cbc1
---

09-07 跨家族复核 G-c 返工 1 时，对「unavailable cavity 不上报」这把锁做生产侧变异：

- 形态一（删检查）：`if projected is None:` 改 `and False` ⇒ projected=None 落进
  下一行 `symmetric_difference` ⇒ `AttributeError`。锁确实 FAILED，但红的是崩溃不是断言。
- 形态二（静默吞掉）：保留 `continue`、只删 `structural.append` ⇒ `assert 0 == 2`
  在锁自己的断言上红。

**Why:** 被审对象的退化形态里，「检查被删」往往让非法值流到下游崩掉——崩溃
掩盖了「锁到底能不能看见这个退化」；真实世界里生产代码的回归更常是「静默跳过/
漏报」，那才是锁要抓的形态。

**How to apply:** 造变异时先问「真实回归长什么样」——通常是静默漏报而非删分支；
红落在锁自己的断言行（`--tb=short` 确认）才算验到牙，落在 AttributeError/TypeError
要换形态重做。同轮有效配套：外部喂损坏产物（测断言助手）+ 生产侧变异（测传播/
透传半区），两者互补，见 [[feed-the-answer-in-to-test-the-code-alone]]、
[[gate-with-only-negative-assertions-is-unobservable]]。
