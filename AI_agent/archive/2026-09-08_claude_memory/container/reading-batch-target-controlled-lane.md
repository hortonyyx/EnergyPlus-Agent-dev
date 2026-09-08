---
name: reading-batch-target-controlled-lane
description: 2026-08-02 用户更正：autonomous 是北极星非本批目标；本批 = reading-agent 在场下 sm21+sm24 接近满分
metadata: 
  node_type: memory
  type: project
  originSessionId: 7c43fd4b-cc3a-48bc-98d3-9e471fe5febd
  modified: 2026-08-02T14:17:15.547Z
---

**2026-08-02 用户当面更正 reading 攻坚的目标口径**（推翻 orchestrator 此前的理解）：

**① autonomous（零 `reading-agent`）是北极星长期目标，不是本批次目标。**
用户原话：目前看来**长期还是依赖 controlled**（有 `reading-agent`）；
等这条路先拿到好 reading 之后，**再尝试撤掉 `reading-agent` 看能不能行**。

**② 本批次验收 = 在 sm21 和 sm24 两个 case 上，`reading-agent` 在场，都拿到接近满分。**
本质 = **先恢复到「Haiku 做 sm21/sm24 满分」那个状态**（那时本来就有高档模型部分介入），
只不过把当时的介入换形态：

| | 当时（07-07） | 本批 |
|---|---|---|
| 谁介入 | orchestrator 临场看着失败现调 | **固化成 `reading-agent`** |
| 与 orchestrator 关系 | 就是本人 | **彻底隔离** |
| 介入者档位 | 最高档 | **降档（Flash 级）** |
| 读图的 | Haiku | Haiku 不变 |

⇒ **本批不是「提高分数」，是「把已达到过的分数用合规形态重新达到一次」。**
⇒ Q-D 的问法是**「怎么把当时那次临场介入正确固化下来」**，不是「要不要 `reading-agent`」。

**③ ⭐ tool-invention 不是成绩 lane，是 dev 期开发者职能**（orchestrator 此前记成三条并列 lane，**是错的**）。
= 允许**最强模型观察 reading（乃至其他环节）内部过程**，提炼方法论、搓适配工具、改进流程，
**作为成果资产纳入项目开发本身**。角色归属用户**倾向 orchestrator 兼任**（可再讨论）。
**四条原则**：⛔不能给生产本身提供**信息** · ✅可以提供思路/方法/工具 ·
⛔这种模式的跑测**不作为正式成绩** · ⛔**一个 case 收官验收必须脱离这个角色完成**。

⇒ 正式成绩只有两条 lane：**autonomous**（北极星）· **controlled**（本批验收 lane）。

**Why**：orchestrator 原先按「autonomous 在 sm24 两抽 ≥95%」定判据，目标定错了一档
（既想恢复历史水平又想同时证明无监督，两件事混成一件）。

**How to apply**：所有 reading 相关的问题书 / 派工单 / 实验设计以本条为准；
[[quality-first-descend-from-strong-model]] 的「降档阶梯」方法论不变，但**每一档的终点是 controlled 达标**。
术语见 [[agent-terminology-convention]]。相关 [[one-ruler-replay-old-artifact-perfect]] · [[controller-must-stay-out-of-product]]
