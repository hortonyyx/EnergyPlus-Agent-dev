---
name: truncated-tool-call-desyncs-provider-ledger
description: 本地历史逐位完美配对、provider 仍报「tool 结果不足」——因为被 finish_reason=length 截断的那次调用只存在于 provider 的账上；一天里前三种解释全被推翻
metadata: 
  node_type: memory
  type: project
  originSessionId: cc9a6b0d-6528-4c5f-a729-647c4bb3c4a6
  modified: 2026-08-13T13:59:19.984Z
---

2026-08-13。下游 `surface` 节点（要建 100 个面）反复被 DeepSeek 400
`"An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'"`。

**⭐ 真因（有 `finish_reason='length'` 实测支撑）**：**单轮生成内容过大 ⇒ 工具调用在生成中途被截断
⇒ provider 服务端的工具调用记账里有它、我们本地 transcript 里没有 ⇒ 下一轮报「结果不足」。**
⇒ 解释了最反常的现象：**本地历史逐位完美配对（3 调用↔3 结果、零未配对/零重复/零孤儿），provider 仍坚持缺结果 ——
缺的那条只存在于它那边的账上。** 也解释了间歇性（取决于该轮生成多大）与「重发同一份历史 3/3 全失败」。
⚠️ `max_tokens=64000` **不是**约束点（100 项批次仅 ~15–25k token）⇒ 是**我们看不见的另一个 provider 侧限制**。

**⛔ 一天之内前三种解释全被推翻，每一种都曾看起来成立**：
① 「provider 无视 `parallel_tool_calls=False` 的批量是触发条件」⇒ **被它自己加的诊断证伪**
（干净跑里每轮仅 1 个调用、配对完美，照样 400）；
② 「provider 记着它下发过的全部 id，我们丢弃就必然被拒」⇒ **被活体探针证伪**
（28 调用+28 回应被接受；客户端截断成 1 个也被接受 ⇒ 它校验的是**提交上来的历史**，不是隐藏账本）；
③ 「历史规模超限」⇒ 方向对但不是根因。

⭐ **判别问法 =「错误消息指名的那件事，我核过它是不是真的坏了吗？」**
本例中错误消息说「配对不足」，而**配对恰恰是好的** ⇒ **provider 的错误消息可以系统性误导**，
把它当线索可以，⛔ 当结论必错。

**结构性诱因（真正缺的那件东西）**：仓里有 `update_surfaces_batch`、`create_fenestration_surfaces_batch`，
**唯独没有「批量创建面」** ⇒ 100 个面 = 100 次调用堆进同一段对话。
用户 08-13 拍板加 `create_surfaces_batch`，并把「每次至多 4 项」**做成代码里的硬上限**
（⛔ 不是提示词约束 —— 本仓反复实证 [[model-visible-but-not-its-business]] 那条「prompt 不是防线」）。
「4」如实标注为**经验取值非严格推导**（≤4 时 n=1 零截断 / ≤8 时 2 次截断 1 次）。

与 [[real-chain-run-exposes-what-tests-cannot]] 同族：**2589 条单测全绿，一条都测不出这个**。
