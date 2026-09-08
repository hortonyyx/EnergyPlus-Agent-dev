---
name: review-worktree-cannot-contain-its-own-review-order
description: 复核 worktree detach 在被审提交上，按构造就读不到之后才写的复核单；而 pytest staging 里有整仓快照，席位会读到过期版本
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 53d05c89-0efb-4c2a-8620-6fd4187f91c0
  modified: 2026-09-06T15:59:16.102Z
---

**复核 worktree 天生读不到复核单。** 复核树是 `git worktree add --detach <被审提交>` 建的，
而复核单是**被审提交之后**才写进主线的 ⇒ **按构造它就不在那棵树里**。

2026-09-06 E-a′ 复核实撞：我在 prompt 里写「复核单在 `/tmp/ea2_review_glm/AI_agent/logs/reviews/request/...`」，
那个路径**不存在**。复核方没停报，而是自己去别处找——**在 pytest staging 副本里找到了一份**，
但那份是**改派前的 GLM 版**（我后来把它改派给了 Claude）。它比对主树版后发现
「仅分工署名与裁决落点两处不同、复核要求逐字相同」才继续。

**Why:** 这次它自己发现了不一致是**运气**。下一次如果两版的**要求正文**有实质差异，
席位就会照着过期单子干完一整轮——而且**日志上看不出任何异常**，交件会显得完全合规。
⚠️ 更普遍的坑：**pytest staging 里有整个仓库的快照**（隔离门要求 staging 在仓库外，
于是把仓库拷了一份进去），所以「席位读到过期文件」这条路**一直存在**，不只复核单。

**How to apply:**
- ⭐ **复核 / 施工 prompt 里点名要读的文档，一律给【主树绝对路径】**
  （`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/request/<单名>`），
  ⛔ 不要写成席位工作目录下的相对路径。
- ⭐ 或者建复核树时用一个**同时含被审提交与复核单**的基点（先 merge 再 detach）。
- ⭐ 单子开头加一句：「**若你在工作目录里找不到本单，去主树绝对路径读；
  ⛔ 不要用 staging 里找到的任何副本，那可能是过期版**」。
- 席位报告里出现「我在某处找到了一份副本」这类话 ⇒ **当场核它读的是哪一版**。

同族：[[worktree-base-must-postdate-the-doc-you-cite]]（同一病根的另一面：施工树基点太早）·
[[dont-touch-the-tree-while-a-review-runs]] · [[absent-file-read-as-passing-check]]
