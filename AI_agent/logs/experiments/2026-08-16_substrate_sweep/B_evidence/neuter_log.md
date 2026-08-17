# neuter 记录 —— 摊 B 锁分辨力验证（2026-08-16）

判据（派工单 §6-3）：把被测实现临时改坏 ⇒ 锁真变红 ⇒ 还原 ⇒ `git diff` 零残留。
被 neuter 的文件均为 `src/agent/execution/isolation_templates/guard.py`（模板——staging 里的 guard 从它拷贝，
锁测试每次新建 staging，因此改模板立即生效）。每把快进快出：改 → 跑对应单测 → `git checkout` 还原。

## Neuter 1 — G8 锁（`test_g8_dead_keys_and_no_missing_keys`）

- 改法：从 `PROBE_DIRECT_PARAM_KEYS` 元组删掉 `"axis",`（制造「工具接受但 guard 不认」的缺键）。
- 结果：`1 failed`（方向 B 的 `assert not missing` 命中 `['axis']`）✅ 锁真绑。
- 还原：`git checkout` 后 `git diff` = 0 行 ✅。

## Neuter 2 — G6 锁（`test_g6_batch_edges_denied_and_zero_sidecars`）

- 改法：`MAX_PROBE_BATCH_SIZE = 32` → `64`（33 条不再被拒）。
- 结果：`1 failed`，**恰好红 `[33-entries]` 格**，其余 4 格仍绿（dup-id/bad-id/empty/partial-illegal 与上限无关）✅ 精确命中、零连带。
- 还原：diff = 0 ✅。

## Neuter 3 — G3 锁（`test_g3_out_dir_escapes_denied_by_both_sides`）

- 改法：`REQUEST_OUTPUT_ROLE_KEYS = ("out_dir",)` → `()`（out_dir 不再走 writable-root 检查）。
- 结果：`2 failed`，红 `[tools]` `[requests]` 两格；`[abs-tmp]` `[traversal]` 仍绿——符合分层（绝对路径/`..` 由更早的词法层拦，与输出角色检查独立），锁测的正是「staging 内但不在 out/」这一层 ✅。
- 还原：diff = 0 ✅。

## 收尾验证

三把还原后重跑整个锁文件：

```
$ /opt/venv/bin/python -m pytest tests/test_substrate_sweep_policy.py -n0 -q
38 passed, 4 xfailed in ~2min
```

全绿；`git status` 仅新增 `tests/test_substrate_sweep_policy.py`（未跟踪）。
