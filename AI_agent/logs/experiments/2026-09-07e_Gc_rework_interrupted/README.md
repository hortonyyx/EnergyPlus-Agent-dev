# G-c 返工 1：Astra 席位撞额度中断 —— 落地状态与接手指南

> **档位 = 探索档**。本文是**主控实测的状态档**，⛔ 不是交件（交件席位没来得及写）。
> **分支 `wt/09.07d_gc_rework`（工作树 `/tmp/gc_rework_astra`）⛔ 未合并、⛔ 不绿。**

## 0. 一句话

**T0（rebase）做完且干净；T1–T4 零落库；零孤儿件。**
⚠️ **同一天第二个施工席位撞额度** —— 上午 Claude（月度上限），下午 GPT-6 Astra（**锁到 2026-09-12 10:13**）。

## 1. 中断的情形

| | |
|---|---|
| 席位 | GPT-6 Astra（`codex exec`，effort 横幅回读 **`xhigh`**，⛔ 非默认 `low`）|
| 单号 | [G-c 返工 1](../../reviews/request/2026-09-07d_Gc_rework1_dispatch.md) |
| 结束方式 | **撞 usage limit**（`ERROR: You've hit your usage limit ... try again at Sep 12th, 2026 10:13 AM`），⛔ 非它判断做完了 |
| token | 107,647（主要花在读，⛔ 不是写）|
| **未提交半成品** | ⭐ **零**（`git status --short --ignored` 只剩 `__pycache__` / `AI_agent/logs/runtime/`；`git stash list` 里两条是 6 月老分支的，⛔ 与本轮无关）|
| 交件 | ⛔ **没写** |

## 2. 落地了什么

### ✅ T0 · rebase 完成，⭐ 且**零冲突**（派工方的预判被证实）

```
fd5c3388 09.07_Gc_locks_staging          （8 段全部 pick 成功）
e2a6f7fe 09.07_Gc_locks_readout
ccb4abef 09.07_Gc_locks_facts
889de1ff 09.07_Gc_locks_p1
afc0e867 09.07_Gc_reemit_trios
960e7cf6 09.07_Gc_joint_follows
ea52e885 09.07_Gc_facts_layer
c79fa965 09.07_Gc_ladder_core
fde2f24c ← 主线（含 883d4e51「拆钉」+ GLM 裁决）
```

⭐ **主控实测 rebase 没有丢东西**：`git diff --numstat fde2f24c..HEAD` 的 15 个文件与
rebase 前 `git diff --numstat 43b3384b..f2188df5` **逐行相同**
（`tarch_normalize.py` +597/−180 · `as_measured.py` +192/−8 · 4 个测试文件 · 6 个 gt_staging json · 3 个脚本）。

### ⛔ T1 / T2 / T3 / T4 · 零落库

日志尾部它正在起草测试代码（`test_gate_must_red` / `TARCH_NEUTER_GATE` 一类），
但**没有落盘、没有提交** —— 工作树干净可证。⇒ **那部分构思随会话一起没了，接手方要重做。**

## 3. ⭐⭐⭐ 红的面目（rebase 之后，主控实测）

```sh
cd /tmp/gc_rework_astra
python -m pytest -q -n 6 -p no:cacheprovider \
  tests/test_answer_compiler_profiles.py tests/test_as_drawn_denominator_f126.py \
  tests/test_a11_gt_1mm_ingest_resolution.py tests/test_f156_ring_from_intersection.py \
  tests/test_boundary_condition_facts.py
⇒ 6 failed, 47 passed in 6.26s
```

**与 rebase 前逐条相同**（同样 6 条、同样的函数名、同样的三分类）：

| 测试 | 断言实况 | 类 |
|---|---|---|
| `test_answer_compiler_profiles::test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na` | `assert set() >= {'rev-13ad','rev-13ae','rev-13af'}` | A |
| `test_as_drawn_denominator_f126::test_l4_discarded_non_orthogonal_segments_are_itemised` | `assert set() == {'tarch_wall_free_end'}` | A |
| `test_a11_gt_1mm_ingest_resolution::test_external_quantities_are_bit_identical` | 身份串比对 | A |
| `test_a11_gt_1mm_ingest_resolution::test_the_scan_goes_red_when_the_snap_is_removed` | `assert 48 == 46` | C |
| `test_f156_ring_from_intersection::test_projected_ring_identity_holds_with_no_tolerance_at_all` | `assert 2 == 4` | B |
| `test_boundary_condition_facts::test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches` | `assert 2 == 4` | B |

### ⛔⛔ 派工方勘误：类 B 那两条**不会**自己指名是哪一支

我在派工单 T1 里写「rebase 后红的那条**会指名** `SM25_DEFERRED_F153_FORM_B_COUNT`」。
**实测是错的**：两条仍先红在**总数行** `assert len(deferred) == SM25_DEFERRED_CAVITY_COUNT`
⇒ `assert 2 == 4`，**per-code 两行根本没被求值**（pytest 在首个失败断言处停）。

⚠️⚠️ **这正是 GLM 拆钉裁决的不阻断-3**，我在 `09.07j` 里刚把它登记成 `plan.md` 的 **G-d3**，
**半小时后写派工单时就违反了它**。⇒ [[stop-and-report-catches-dispatcher-errors]] 第 ⑩ 条
**「写下自检 ≠ 执行自检」**，本项目第 N 次。已在派工单里落勘误段（`b2ec9eb4`）。

⭐ **实质不受影响**：归因路径仍成立 —— 总数行红 ⇒ **去读两个 per-code 钉与实际数据的对账**，
就看得出是 **F-153 form B 那一支 2→0**、F-157 纹丝不动。⛔ 只是「红的那行自己写出是哪一支」这个说法不对。

## 4. 接手指南（下一个席位）

1. **⛔ 不要合并这条分支** —— 它不绿。
2. **T0 已完成，⛔ 不要重做 rebase**（基点已是 `fde2f24c`）。
3. 从 **T1** 开始，派工单原文照用（含 §三 的勘误段）：
   [2026-09-07d_Gc_rework1_dispatch.md](../../reviews/request/2026-09-07d_Gc_rework1_dispatch.md)。
4. ⭐ **分段提交纪律照旧** —— 本项目连续两个席位撞额度，这条是唯一让活不丢的东西
   （上一程第四次兑现，本程 Astra 因为还没做出东西所以没东西可丢）。
5. 全量绿之后才谈交件与跨家族复核（**复核仍派 GLM**，用户 2026-09-07 指定）。
6. ⚠️ **主控仍未逐行审 G-c 那 8 段的后 4 段**（约 1340 行测试改动）——
   审过/没审过的分界写在派工单 §二，⛔ 别当整块审过。

## 5. ⚠️ 席位额度盘面（2026-09-07 实测，接手前先看）

| 家族 | 状态 |
|---|---|
| **GPT / Astra** | ⛔ **锁到 2026-09-12 10:13**（本次撞的就是它）|
| **Claude 施工** | ⚠️ 2026-09-07 撞月度支出上限（G-c 首轮），**恢复与否未探针实测** |
| **GLM** | ✅ 可用（本日刚做完拆钉复核）—— ⚠️ 但它是用户指定的 **G-c 复核方**，改派它施工需要用户重新拍板 |
| **DeepSeek** | ⚠️ `scripts/deepseek_code.sh`（默认 `deepseek-v4-pro`），⛔ **按量扣余额、与管线共用** |

⇒ **这是一个需要用户拍板的排工决策，⛔ 主控不自行改派复核方。**

## 6. 复现命令

```sh
cd /tmp/gc_rework_astra
git log --oneline -1                                                        # fd5c3388
python -c "import src.agent.judge.tarch_normalize as m; print(m.__file__)"  # 必须落在本树
python -m pytest -q -n 6 -p no:cacheprovider                                # 全量
```

⚠️ 若工作树已被清掉：`git worktree add /tmp/gc_rework_astra wt/09.07d_gc_rework`（分支仍在）。
