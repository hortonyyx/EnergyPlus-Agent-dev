---
name: one-shot-acceptance-bar-kills-false-claims
description: 用户定的「一口气推完不出错才算」在一天内连续打掉四个已经写好的结论；拼接多次调用的「跑通」是假的
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cc9a6b0d-6528-4c5f-a729-647c4bb3c4a6
  modified: 2026-08-13T13:59:44.562Z
---

2026-08-13 用户逐字定的验收口径：**「验收要一口气推完不出错才算」**。

**当天它打掉的东西（按顺序）**：
1. orchestrator 已准备把「全链跑到 EnergyPlus 0 Severe」记为达成 —— 用户一句
   「这是一次好 reading 产物一口气跑完端到端、中间没出问题对吗」逼出时间戳对账：
   **那是三次调用拼出来的**（0–5 段跑在旧代码、下游跑在修法后），中途 4_mep 还崩过一次靠重试自愈
   ⇒ **没有任何一次连续执行、在同一代码基线上覆盖过整条链。**
2. 干净单次跑立刻复现故障 ⇒ 证明前一次「跑通」是**运气边缘**不是能力。
3. 施工席的机制结论、以及 orchestrator 自己的首要假设，**都在随后被证据推翻**
   （详 [[truncated-tool-call-desyncs-provider-ledger]]）。

⭐ **为什么这条口径有效**：多次调用之间**允许改代码、允许重试自愈**，
于是「拼起来到过终点」与「这套代码能走完」被混为一谈。**一口气 = 冻结代码基线 + 禁止中途干预**，
**不出错 = 禁止用重试掩盖崩溃**（4_mep 的裸 `TypeError` 正是靠重试自愈、在"全绿"的跑里没人看得见）。

⭐ **且必须连跑 ≥3 次** —— 该链路已多次证明间歇性，**一次通过不算**
（08-11 与 08-13 09:02 都曾"通过"过，随后同一代码干净跑仍失败）。

⛔ **写验收条件时 orchestrator 犯过的错（同日）**：写「每一段 attempts 必须=1，出现 002 即不通过」
—— **对 `1_correction` 是错的**，该段正常就写两次（基础写入 + 方位增强写入）。
⇒ **验收条件本身也要先对着盘上的正常形态核一遍**，否则会把合法行为判成失败。

与 [[two-kinds-of-latency-no-ruler-vs-never-reached]]、[[real-chain-run-exposes-what-tests-cannot]] 同族。
