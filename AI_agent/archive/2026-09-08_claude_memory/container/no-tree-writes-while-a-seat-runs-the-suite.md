---
name: no-tree-writes-while-a-seat-runs-the-suite
description: 席位跑全量期间 orchestrator 连【文档提交】都不做——纯 md 也会造出假红
metadata:
  type: feedback
---

2026-08-29 同型**第三次**：我在施工席位跑全量期间提交了 `6b5d9bd`（**纯 `AI_agent/*.md`**），
造成 `test_record_baseline_marker_merge_...` 一条假红。

**机理已读代码坐实**：该用例断言「连续两次 `record_baseline` 生成的 REPORT.md 逐字相同」，
而 `_collect_git_provenance()` 每次都跑真实共享主树的 `git rev-parse HEAD` + `git status --porcelain`，
行数进报告 ⇒ **窗口内任何一次树变化都让两次生成不同**。施工方的失败差分 `dirty:4→5` 与我的提交吻合。

**Why**：此前的口径是「席位在飞时只做文档」，**不够** ——
那条用例把「整棵共享树在 ~90 秒内不许变」写进了前提。

**How to apply**：**有席位在跑全量时，orchestrator 连文档提交都不做**；
草稿留 scratchpad，等席位交件后一并入库。反过来也告诉席位别在别人可能跑测时动树。
⭐ 正确次序：先补完文档并提交 → 树干净 → 再启动全量 → 全程不碰。
同族 [[green-suite-is-a-property-of-tree-and-launcher]] · [[wrapup-commit-sweeps-other-seats-wip]]。
