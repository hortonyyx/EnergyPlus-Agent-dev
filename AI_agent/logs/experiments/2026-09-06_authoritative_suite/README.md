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
