---
name: absent-file-read-as-passing-check
description: 用 `grep ... || echo 通过` 验证时，文件不存在会落到「通过」分支——我把「文件没了」读成了「检查通过」
metadata:
  type: feedback
---

2026-08-19 删 prescan 时，正则多吃一行、把 `_write_generated(kickoff_prompt.md, ...)` 整句删掉，
⇒ staging 不再生成 kickoff。**当场没发现**，因为我的验证是：

```bash
grep -c prescan <staging>/kickoff_prompt.md || echo "kickoff 零提及 prescan"
```

文件不存在 ⇒ `grep` 非零退出 ⇒ `||` 落到 echo ⇒ 打印「零提及」。**「文件没了」被读成「检查通过」。**

**Why**：这是 [[absence-conflates-causes-in-observables]] 在**我自己的验证命令**里的形态——
「读不到」和「读到且干净」被压进同一个分支。同族还有 [[gate-with-only-negative-assertions-is-unobservable]]
（只有负向断言的门恒绿）。⭐ 抓住它的是既有测试锁（`FileNotFoundError`），不是我的检查。

**How to apply**：
- 验「某文件内容合规」必须**两步**：`test -f X` 先断言存在，**再**断言内容。
  ⛔ 禁 `grep ... || echo 通过` / `find ... | head` 这类把空结果当成好结果的写法。
- 删代码后的验收，**先列产物清单比对**（`ls` 前后 diff），再看内容——我当时的 `ls` 输出里
  kickoff_prompt.md 确实已经不见了，是我没逐项比对。
- 正则删块**禁止跨越函数内的其他语句**：用锚点成对匹配或按 AST 删，⛔ 不用 `.*?` 贪到下一行。
