---
name: removing-a-restriction-needs-the-allow-side-logged-first
description: 撤一道限制之前先问「放行面留不留证据」——限制在时被拒的都有记录，限制一撤，唯一能带出信息的那面往往恰好是不记录的那面
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f5b071ce-3665-4033-97eb-863ba3d5d2a0
  modified: 2026-08-16T03:16:54.065Z
---

**判据**：**准备放宽一道门时，先查「被放行的调用留下了什么」。**
门紧的时候，你看到的证据几乎全来自 **deny**；门一松，行为都走 **allow**，
而 allow 那面常常**什么都不记**——于是刚放开的这一步同时也是**观测失明**的一步。

**2026-08-16 实例（EnergyPlus-Agent，撤 reading 沙箱的「能力封口」）**：
`guard.py::_append_log` 原来 `if decision == "deny": entry["tool_input_excerpt"] = ...`
—— 放行只留一个 payload 哈希。哈希能证明两条记录相同，**说不出跑的是什么**。
撤封口后 `python -c` / 自写脚本变成主要通道 ⇒ **恰好是唯一能把信息带出净室的那面，事后不可复算**。
先修（allow 也记原文 + 新增 `executed_code` = 每份被扫文件的 `{path, sha256}`），
当天的核心结论（**能力被用了 4 次、零次用于测量**）才读得出来 —— 不修就只剩「跑了 4 次 python」。

**⇒ 怎么用**：
- 放宽前问三句：**① 放行条目记内容吗？② 记的是内容还是哈希？③ 内容会被截断吗？**
  （本例 excerpt 上限 500 字符，装不下一段 `-c` 程序，一并提到 8000。）
- 若被执行的是**文件**，只记命令行不够 —— 记**文件内容的哈希**，
  否则事后改文件就改写了「当时跑的是什么」。
- 同族 [[absence-conflates-causes-in-observables]]（**没记录 ≠ 没发生**）·
  [[hash-of-whole-report-is-not-an-equality-test-for-its-parts]]（哈希只判相等、不判内容）·
  [[freeze-only-what-has-external-trust-root]]。

**⚠️ 连带**：这条也是「**产物要可审计**」那条目标口径的落地位置 ——
见 [[baseline-unauditable-dont-chase-its-number]]：07-07 那份基准之所以不可审计，
根因之一正是「当时连访问记录这套东西都不存在」。
今天若不补放行面，等于把同一个坑再挖一次，只是这次是自己动手挖的。
