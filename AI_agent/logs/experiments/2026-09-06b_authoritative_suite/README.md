# 2026-09-06 第七程 · 权威全量（主树）

**读数：`3989 passed / 2 skipped / 13 xfailed / 0 failed`**（14m29s，`-n auto`，exit 0）

## 逐位闭合

```
3989 + 2 + 13 = 4004   =   独立 --collect-only 实测 4004   ⇒ 差额 0
```

## 与合并前的预测逐位吻合（⭐ 先预测、后测量）

```
3907（第六程收口读数）
 + 47（J 判分接线+补立面，主控与复核方各自独立 collect 均为 47）
 + 35（E-a′ 源契约对齐，同上）
 = 3989
```

## 哨兵（⭐ 前后必须同值才算数）

| | 跑前 | 跑后 |
|---|---|---|
| UTC | 2026-09-06 15:15:08 | 2026-09-06 15:30:07 |
| HEAD | `14edd219` | `14edd219` |
| 工作树变动文件数 | 0 | 0 |
| `.pth` md5 | `5198f6f9bf773d07…` | `5198f6f9bf773d07…` |

⭐ **跑前已把 `.pth` 恢复指向主树**（`/workspaces/EnergyPlus-Agent-dev`）——本程有三个 claude 家族席位
以 worktree 为工作目录启动过，按 [CLAUDE.md §5#8.6](../../CLAUDE.md) 那条已知机制，**启动即改 `.pth`**，
⛔ 不是谁违纪。

⭐⭐⭐ **承重不变量不是 `.pth` 哈希，是 `m.__file__`**（跑前实测）：

```
src.agent.correction.tick_claim        -> /workspaces/EnergyPlus-Agent-dev/src/agent/correction/tick_claim.py
src.agent.judge.as_drawn.elevation_grade -> /workspaces/EnergyPlus-Agent-dev/src/agent/judge/as_drawn/elevation_grade.py
```

## 纪律

- 跑测全程**未动树**（工作树前后均 0、HEAD 未变）——本项目已三次因「全量跑着时提交文档」造出假红。
- 跑测时**无席位在飞**，故用 `-n auto`；有席位同机时一律 `-n 6`。

原文 → [`run_raw.log`](run_raw.log)
