# 权威全量 · 2026-09-06（A-11 返工 1 合并后）

主树 `/workspaces/EnergyPlus-Agent-dev`，HEAD `c21b93ae`（合并提交 `3ca8abda` 之后）。
⭐ 权威全量**只在主树**跑（[[green-suite-is-a-property-of-tree-and-launcher]]）。

## 命令与读数

```sh
# 先把 editable 安装收回主树（上一轮两个 Claude 审阅席位把 .pth 指向了自己的 worktree）
uv run python -c "pass"
python -c "import src.agent.judge.as_measured as m; print(m.__file__); import src.agent.judge.answer_compiler as a; print(a.__file__)"
python -m pytest -q -n 6 -p no:cacheprovider
```

```
3863 passed, 2 skipped, 13 xfailed, 212 warnings in 1065.96s (0:17:45)
FAILED / ERROR 行数 = 0
```

## 四道哨兵（全部对上）

| 哨兵 | 值 |
|---|---|
| `.pth` 跑**前** | `/workspaces/EnergyPlus-Agent-dev` · `58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43` |
| `.pth` 跑**后** | **同上，逐位相同** |
| `m.__file__` 跑前 | `/workspaces/EnergyPlus-Agent-dev/src/agent/judge/{as_measured,answer_compiler}.py` |
| `m.__file__` 跑后 | 同上 |

⭐ **承重不变量是 `m.__file__` 落在主树**，⛔ `.pth` 哈希只是代理量（[[green-suite-is-a-property-of-tree-and-launcher]]）。
跑测全程 `git status --short` 为空、HEAD 未变。

## 逐位闭合

```
独立 --collect-only  = 3878 tests collected
3863 passed + 2 skipped + 13 xfailed = 3878   ✓ 差额 0
```

三方读数一致：A-11 施工席 `3863` · 跨家族复核方独立复算 `3863` · 本次主树权威 `3863`。

## ⚠️ 耗时说明（⛔ 不是信号）

1065.96s 对比席位侧的 476.53s —— 本次跑测期间 `gpt-6-astra` 的 A-6 返工席位
正在 `/tmp/a6_tickclaim_astra` 并行工作，两边争 CPU。⭐ codex 家族席位**不翻 `.pth`**，
所以并行不影响本次读数的有效性（哨兵前后一致即为证）。

---

# 第二次权威全量 · 同日 · A-6 整条线合并后

主树 HEAD `d5675286`（合并提交 `09.06f_merge_A6_tick_claim_block`）。

```
3907 passed, 2 skipped, 13 xfailed, 212 warnings in 908.51s (0:15:08)
FAILED / ERROR 行数 = 0
```

原文 → `full_suite_after_A6.txt`。

## 四道哨兵（全部对上）

| 哨兵 | 值 |
|---|---|
| `.pth` 跑前 / 跑后 | `/workspaces/EnergyPlus-Agent-dev` · `58f547fa…`，**前后逐位相同** |
| `m.__file__` 跑前 / 跑后 | `src/agent/correction/{tick_claim,opening_adjudication}.py` + `src/agent/judge/as_measured.py`，**均落主树** |

⚠️ 跑前先 `uv run python -c "pass"` 把 editable 安装收回主树 ——
A-6 返工的 Claude 复核席位启动时把 `.pth` 指到了 `/tmp/a6rw1_review_claude`（⭐ 已知副作用，⛔ 不是违纪）。
跑测全程 `git status --short` 为空、HEAD 未变。

## 逐位闭合

```
独立 --collect-only  = 3922 tests collected
3907 passed + 2 skipped + 13 xfailed = 3922   ✓ 差额 0
```

⭐ **合并前的预测值与实测逐位吻合**：`3863`（A-11 后）`+ 27`（A-6 整块）`+ 17`（A-6 返工）`= 3907`。
三个来源的分项数各自可查：A-6 块 27 条（`resume_test_collection.txt`）· 返工 17 条
（`2026-09-06a_A6_rework1/test_collection.txt`）· A-11 净 +13（`3850 → 3863`）。
