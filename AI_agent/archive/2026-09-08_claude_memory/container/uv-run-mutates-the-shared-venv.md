---
name: uv-run-mutates-the-shared-venv
description: 跑测约定里的 `uv run` 会重同步共享 /opt/venv —— 与「禁写 site-packages」自相矛盾，且是并行席位互踢的根因
metadata:
  type: feedback
---

**2026-09-08 GPT 席位停下上报翻出来的**（第 72 次停报，仍然是派工方的错，而且是我的）：

派工单同时写了两条，**它们互相矛盾**：
- ⛔ 禁 `pip install -e .` 或**任何写 `site-packages` 的命令**（venv 全机共享）
- 跑测用 `PYTHONPATH=<树> uv run pytest -n 6 -q`

实测：`uv run` **本身**会重新同步共享 `/opt/venv` 的 editable 安装，输出里明写
`Uninstalled 1 package in 2ms` / `Installed 1 package in 10ms`
⇒ **我给的跑测命令违反了我给的硬约束。**

⚠️ **更严重的是它的连带后果**：主控与席位在**不同 worktree** 上各自 `uv run`，
就在来回改写同一个 `_editable_impl_energyplus_agent.pth` ——
**这就是这一整天并行席位互相踢、`.pth` 反复翻面的根因**，
⛔ 不是「谁忘了复位」的纪律问题，是**约定本身在改共享资源**。

**正解（实测）**：
```bash
PYTHONPATH=<树绝对路径> /opt/venv/bin/python -m pytest -n 6 -q
```
- 解析正确（`src.agent.__file__` 落在该树内）
- **零 `Uninstalled`/`Installed` 输出，`.pth` 跑完未被改**
- `PYTHONPATH` 优先于 `.pth` ⇒ 承重不变量照旧成立，且**并行树互不干扰**

**How to apply**：
- 派工单里的跑测命令**一律用 `/opt/venv/bin/python -m pytest`**，⛔ 不再写 `uv run pytest`。
- ⭐ 自查话术：「我写的**命令**，会不会违反我写的**约束**？」——
  两条都在同一张单子上，读的时候却分处两节，⛔ 不并排看就发现不了。
- 一次性脚本同理：`uv run python -c ...` 也会同步，改用 `/opt/venv/bin/python -c ...`。

⚠️ 本条**修正**了 [[green-suite-is-a-property-of-tree-and-launcher]] 里
「`.pth` 会被席位启动重指、用完复位」的处理方式：**根本不该让它被重指**。

配套：[[dont-touch-the-tree-while-a-review-runs]] · [[stop-and-report-catches-dispatcher-errors]]
