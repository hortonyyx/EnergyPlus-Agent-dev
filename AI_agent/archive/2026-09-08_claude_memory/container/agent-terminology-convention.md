---
name: agent-terminology-convention
description: 2026-08-02 用户定的 agent 术语规范：orchestrator / <子环节>-agent / <子环节>-<功能>-agent
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7c43fd4b-cc3a-48bc-98d3-9e471fe5febd
  modified: 2026-08-02T14:16:51.984Z
---

**2026-08-02 用户拍板的术语规范（全项目统一，避免指代错误）**：

| 术语 | 指什么 |
|---|---|
| **orchestrator** | 端到端主控（以前叫「主控」）。只能启动与接收，不得伸手进子环节内部 |
| **`<子环节>-agent`** | 子环节（0–5）内部的**调度**，如 `reading-agent`（= 旧称「reading 内部 controller」） |
| **`<子环节>-<功能>-agent`** | 子环节内部**实际执行某功能**的，如 `reading-worker-agent`（读图并产出观测的 VLM） |

**用户对命名的说明**：`reading-worker-agent` 而非 `reading-vision-agent`，因为**它不止看图、还产出**。

**Why**：此前「主控 / controller / worker」三个词在不同文档里指代不一，多次造成排查分类错误
（08-01 那次整份排查分类全错，部分即源于此）。

**How to apply**：新写的问题书 / 派工单 / 细稿 / 管理文档一律用上表；引用历史记录时保留原文但加注。
已按此改写的文档：`logs/reviews/request/2026-08-02_reading_architecture_design_brief.md`、
`logs/reviews/request/2026-08-02_reading_ruler_r1_construction_dispatch.md`。

相关：[[quality-first-descend-from-strong-model]] · [[controller-must-stay-out-of-product]]
