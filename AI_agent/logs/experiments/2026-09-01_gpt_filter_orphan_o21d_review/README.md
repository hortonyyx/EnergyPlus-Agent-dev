# 孤儿件隔离 · GPT 席位复核 ②-1d 时被 provider 过滤中断

- **日期**：2026-09-01 · **席位**：GPT 家族（`gpt-5.6-sol` / effort high）
- **工作目录**：`/tmp/o21d_review_gpt`（主控自建 worktree，detached `8028bab`）
- **复核单**：[`../../reviews/request/2026-09-01f_o21d_ruleify_crossreview.md`](../../reviews/request/2026-09-01f_o21d_ruleify_crossreview.md)

## ⛔⛔ 本目录里的一切都是【线索】，⛔ 不是【证据】

**它没有交出裁决。** 席位在做到一半时被 **provider 的内容过滤**打断：

```
ERROR: This content was flagged for possible cybersecurity risk.
       If this seems wrong, try rephrasing your request.
```
（同族已知坑：规约记过 2026-08-16「审隔离壳的活被 GPT provider 过滤拦死 6 次」。）

⇒ **任何要用这里面的东西的人，必须自己重新实现 + 重新论证 + 自己补锁。**
⛔ 不许把 `orphan.diff` 或 `seat_session.log.txt` 里的任何读数当作已核实的事实引用。

## 里面是什么

| 文件 | 内容 |
|---|---|
| `orphan.diff` | 它留在 worktree 里未还原的改动，**`+128 / −466`** —— 是被审改动（`+466/−128`）的**逆向**，即它把 `tests/test_o21d_exclusion_gap.py` **还原到 `5ac0885^` 的版本**去跑第①格 |
| ~~`seat_session.log`~~ | ⛔ **未入库**：`.gitignore:81` 的 `*.log` 与 `:258` 的 `*.txt` 都排除它，**这是仓库既定约定，主控没有 `git add -f` 绕过**。它本来就是「线索非证据」，README 的摘要已足够；原始日志只在本次会话的 scratchpad 里，**换会话即失** |

## 它跑到哪一步（⚠️ 复述，⛔ 未经主控独立复现）

- 开工自检**全过**：`8028bab` · worktree 干净 · `answer_compiler.__file__` 落在自己 worktree ·
  ⭐ 本轮改用 `__file__` 判据后**没有再被哨兵挡住**（上一轮它据旧哨兵 A 层停报，停得对 = 题错 #69）。
- 做到了**攻击面 2**（`grep` 全文 `assert .*passed` 的落点）与**攻击面 3**
  （实测 `LIVE_REGISTERED_EXCLUSIONS 2`，并打印了两条 exclusion 的 cavity/zone/reason/area）。
- 在还原后的父版本上得到 `5 failed, 2 passed`，其中至少两条死在
  `assert reconcile_boundary_basis(...).passed` / `assert aligned.passed` 上。
- ⛔ **攻击面 1（25 腔底料喂进 11 条锁）没有读数** —— 那是本单的必答题。

## 处置

- 主控**只**还原了它动过的那一个文件（`git checkout -- tests/test_o21d_exclusion_gap.py`），
  ⛔ 没有用 `git checkout -- .`；还原后 worktree `git status --porcelain` 为空。
- ②-1d 的复核**改派 GLM 家族**重做（⛔ 非 Claude —— 施工方与主控都是 Claude）。
- ⭐ 派 GLM 时**不复用**本目录任何一段：新席位从头做，理由同上。
