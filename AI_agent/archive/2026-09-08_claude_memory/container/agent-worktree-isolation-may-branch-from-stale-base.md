---
name: agent-worktree-isolation-may-branch-from-stale-base
description: 派子 agent 时用内置 worktree 隔离，那棵树可能建在几百个提交之前的基点上；派工前必须让它自检关键文件在不在
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ed0c0b1a-0217-446e-b0a8-7735c47e73fc
  modified: 2026-08-24T13:55:02.601Z
---

2026-08-25 实测：用 Agent 工具的 `isolation: "worktree"` 派一个施工席位，
它拿到的 worktree **HEAD 停在 560 个提交、约 2.5 个月之前**（六月的检出点），
分支是自动建的 `worktree-agent-<id>`、被标 `locked`。

后果：任务书、源代码目录、目标目录**全都不在那棵树上**——
连 `CLAUDE.md` 都是旧编号体系（没有 §0 治理条款、没有 gt 铁律）。
**不是缺几个文件，是整整两代架构的落差。**

**施工席位的处置是对的**：只跑只读命令、零改动、不 commit、
⛔ **不凭记忆重建那几份文件假装搬运**，然后停下上报，
并说明「分支手术不在施工席位授权范围内」。⇒ 「停下上报」累计 **23/23 全是派工方题错**。

**有效解**（当天用的）：**主控自己建 worktree**
（`git worktree add -b <name> <dir> HEAD`），派工时**不用内置隔离**、
在提示里**显式写工作目录**，并要求**开工第一步先自检关键文件在不在、缺任何一样立刻停**——
把上一次那个坑做成它自己能查的门。

⚠️ 另有一个配套坑：venv 的 editable-install `.pth` 可能**硬编码指向主树**
（实测 `_editable_impl_energyplus_agent.pth` 内容 = 主树绝对路径）⇒ 在任何非主树的工作树里
**裸跑**（非 `-m`、非 pytest）一个 `from src.xxx import …` 的脚本会**静默从主树解析 src**。
⇒ 席位在 worktree 里的验证一律走 `python3 -m <dotted.path>` + 显式 `cwd=`。
⭐ 且这条在**合并回主线后会从响亮失败变静默串台**（同名文件两棵树都有了）。

相关：[[green-suite-is-a-property-of-tree-and-launcher]]（权威全量只在主树）·
[[stop-and-report-catches-dispatcher-errors]] · [[verify-the-path-works-before-blaming-the-model]]
