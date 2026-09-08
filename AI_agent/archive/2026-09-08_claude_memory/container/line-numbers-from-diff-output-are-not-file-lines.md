---
name: line-numbers-from-diff-output-are-not-file-lines
description: 对 git show 的输出 grep -n 得到的是 diff 文本里的位置，不是文件行号；引用位置必须回文件里查
metadata:
  type: feedback
---

2026-08-28 实犯：写跨家族复核单时，我用
`git show <sha> -- <file> | grep -n "^+" | grep -E ...`
拿到的编号当成**文件行号**写进了单子，**四个全错**
（我写 95/115/117/118，实际 394/414/415/417；`_REPO_ROOT` 那条我写 89、实际 476）。

⛔ **`grep -n` 数的是它收到的那段文本的行**。`git show` 的输出前面还有
commit header + 提交说明 + diff header + hunk 头，且只含**改动过的**行 ——
它和文件行号**没有任何固定偏移关系**。

⭐ **正确做法**：位置要引用时**回文件本身查** ——
`grep -n "<锚点字符串>" path/to/file.py`，或 `git show <sha>:<path> | grep -n`。
用 diff 只用来看**改了什么**，⛔ 不用来取**在哪一行**。

⭐ 复核方（GLM）当场逐条核出来了，并按分层触发器**只记一行、没停工**（判据：内容全部属实，只有行号错）
—— 这正是「外围数值错只记不停」那一档设计对了的证据。

同族：[[grep-zero-hits-conflates-unused-with-nonexistent]]（引用标识符前先查它的**定义**）·
[[proxy-mistaken-for-the-thing]]（我量的是它本身还是它的影子）。
