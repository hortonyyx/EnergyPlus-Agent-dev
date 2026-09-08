---
name: enumerate-the-class-not-the-example-found-six-more
description: 把返工题从「修这个例子」提到「枚举这一类」，复核方找到 1 个洞、枚举找出另外 6 个
metadata:
  type: feedback
---

2026-09-06 A-6 返工的实证：跨家族审只找到**一个**缺口（`submit()` 核过跨行 `lo<hi`、`consume()` 没重核）。
返工单没写「补一个 `lo<hi`」，写的是 **「`submit()` 做过的每项检查，`consume()` 各自重做了没有？逐项列表」**。
施工方交回 **17 项**表，除已知那 1 项外**另外 6 项** `consume()` 从未重做
（响应类型/packet 对应 · `reperceive` 不能冻结 · 补证债必须有 missing_chains · `debt_id` 生成 ·
`retired_debt_id` 条件 · 逐行来源字段），且新增 17 条测试**零既有测试被改**。

**Why:** 复核方是**按症状**找到洞的（它造了一个区间倒置的攻击）。症状只暴露它自己那一条路径；
**把同一个位置的【全部承诺】枚举一遍**才暴露这一类。⭐ 这是 [[gate-measures-a-proxy-not-the-thing-it-guards}]] 的
施工侧对偶：复核方量的是「这条攻击能不能过」，而要守的是「入口检查过的，出口是不是都重检了」。

**How to apply:**
- **返工单的题面要写成【对账】而不是【修复】**：「A 处做过的每项 X，B 处各自做了没有」，
  ⭐ **那张对照表本身就是交付物**。
- 表里必须允许「结构上不必重做」这一档，但**每条要写清「若真被绕过，坏数据流到哪、被谁接住」**，
  ⛔ 否则「不必」就成了免检通道。
- ⚠️ **表的外延是施工方自己划的** ⇒ 复核单第一优先必须是「**这张表是不是全部**」，
  且要求复核方**用两套互不依赖的口径独立枚举**（逐行读 + 具名 code 集合差集），
  ⛔ 不许照着它的表核。这是 [[gate-measures-right-but-carrier-gets-swapped]] 的第 ② 问落在文档上。

配套：[[rework-review-needs-the-same-shape-input]] · [[gpt6-astra-takes-large-blocks]]
