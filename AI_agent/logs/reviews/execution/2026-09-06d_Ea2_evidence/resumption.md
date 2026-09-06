# 口径更正后恢复施工

用户已受理上次停报（第 71 次），明确授权 pytest / 隔离门使用 `/var/tmp/ea2_astra_pytest`。代码与交件仍限本 worktree；禁止访问主树及其他 worktree。

生产代码未改时重跑：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/authorized_baseline
```

原文：`authorized_baseline.log`。完整汇总：

```text
3907 passed, 2 skipped, 13 xfailed, 211 warnings in 468.57s (0:07:48)
```

逐位闭合：3907 + 2 + 13 = 3922。相对上次：passed 增加 440，failed 减少 300，errors 减少 140，skip/xfail 不变，总数差 0。原停报中的目录冲突已解除，允许继续源入口施工；本结果是修改前基线，不是施工验收。
