# 施工交件报告 · 装机路径止血（F-94 A 案）

- **派工单**：[`../request/2026-08-25_f94_bootstrap_dispatch.md`](../request/2026-08-25_f94_bootstrap_dispatch.md)
- **席位**：Claude 家族执行档　**交件 commit**：**`91ae82d`**
- **复核**：GLM 跨家族 → [`../request/2026-08-25_f94_bootstrap_crossreview_glm.md`](../request/2026-08-25_f94_bootstrap_crossreview_glm.md)
- ⛔ 席位自述按 §5#8 **一律以 `git diff` 为准**。orchestrator 已机械核对部分见文末。

## ① 开工自检

`CLAUDE.md` **先读**（§0/§5#8/§5#12）再读派工单 ✅（⭐ 上一轮席位在此处被 GLM 点名，本单改成硬自检，已生效）·
`pwd` ✅ · 分支 `08.23_AsDrawnReading`、开工 HEAD `8c780ba` ✅ ·
**独立复现机制**：读 `.pth`（内容=主树绝对路径）+ `python3 -c "print(sys.path)"` 确认它被追加在**末尾** ✅

## ② 改了哪 16 个 + 判据（席位独立数的）

`scripts/**/*.py` 共 **32** → AST 扫出含 `from src`/`import src` 的 **22** → 其中 **6** 个原有自举
（`cv_probe` / `build_judge_score_inputs` / `run_stage` / `score_reading_vs_gt` /
`spawn_isolated_reader` / `run_pipeline_deepseek`）⇒ **净需改 16**，与实际改动数一致。

其余 10 个（`_grade_transform` / `affected_tests` / `baseline_record` / `preprocess_images` /
`reading_process_metrics` / `reading_regression` / `render_building_3d` / `render_geometry_viewer` /
`render_vector_to_png` / `render_vector_to_svg`）**逐个核过源码，零处真导入**
（有的只是变量名 `src` 或 docstring 提及）。

## ③ 新锁红/绿两段

- **红**（stash 出 16 个修复文件、还原 pre-fix 后跑）：`RED: 16 offending script(s)` —— 与改动的 16 个**逐一对应**；
  pytest 同步 `1 failed, 1 passed`（扫描器自检那条**绿** ⇒ 证明扫描逻辑本身没坏）
- **绿**（pop 恢复后）：`GREEN: no offending scripts.` / `2 passed in 3.71s`

## ④ ⭐⭐ 非主树行为验证（真 subprocess，⛔ 非只读代码）

`git worktree add --detach` 造物理独立树，并**在该 worktree 的 `src/__init__.py` 里加一行仅存在于 worktree 的打印标记**
（主树 `src/__init__.py` 保持空、未触碰），用来**无歧义区分导入的是哪棵树**：

| 脚本 | 结果 |
|---|---|
| 改过的 `gt_promote.py` | `F94-MARKER: src package resolved from **WORKTREE** tree: …/f94_behavior_wt/src/__init__.py`，`exit=0` |
| 改过的 `record_baseline.py` | 同样打出 worktree marker，`exit=0` |
| **对照**（未改、保留 pre-fix 的 `gt_review_sign.py`）| 裸跑 `--help` **`exit=0` 看似成功** —— ⭐ **这正是危险之处：它没有响亮失败，而是安静地导入了错的树**。同 cwd 下 `python3 -c "import src; print(src.__file__)"` 直接验证 ⇒ `/workspaces/EnergyPlus-Agent-dev/src/__init__.py` = **主树** |

⇒ **坐实了派工单描述的机制**。事后 `git worktree remove --force` 清理。

## ⑤ 全量（席位自己跑的）

```
========== 3016 passed, 13 xfailed, 212 warnings in 789.39s (0:13:09) ==========
```
0 failed / 0 errors；xfailed 13 与修前一致；passed **净增 2** = 新增的两条锁测试。

## ⑥ Commit

`91ae82d` `08.25_F94AcaseBootstrapExtendedTo16ScriptsPlusMechanicalLock` —
`git add` **逐个点名 17 个文件**（16 脚本 + 1 新测试），⛔ 未用 `-A`/`.`；
提交前完整通读 `git status`（未截断），确认 orchestrator 并行产生的审阅单**未被扫入**。未 push。

## ⑦ 与派工单说法不符（席位上报）

派工单 §一「其余 **26** 个脚本没有自举」**是错的**。真实是 32 总 / 22 含 src 导入 / 6 原有 ⇒ **需改 16**；
那「26 个」里有 **10 个根本不 import `src`**。⇒ **派工方（orchestrator）之错，已自认。**

## ⑧ 走了本单没给的路（席位主动单列）

`report_assembly.py` **从不被裸跑**（无 `__main__`，只被已修的 `record_baseline.py` 与 pytest 导入），
严格按字面标准可以不改；席位仍给它加了同款自举，理由是
**让机械锁的判据保持「零例外、纯按有无 `from src` + 有无自举」**，
避免锁本身携带「是否有 `__main__`」这类需要持续维护的豁免逻辑（⭐ **豁免逻辑本身就是未来出错的新缝**）。

## ⭐ 附加（席位主动做，非派工单要求）

新锁自带 `test_lock_has_discriminating_power_on_a_synthetic_offender`
（正例 / 反例 / **延迟导入**三态合成 offender 自检）—— 在信任这把锁去扫真实仓库之前，
**先证明扫描逻辑本身不是恒真恒假**。
⭐ 这正是 GLM 上一轮对另一把锁提的 findings #2。

---

## ⭐ orchestrator 的机械核对（⛔ 不是「审」）

| 核了什么 | 结果 |
|---|---|
| `git show --stat 91ae82d` | ✅ **17 个文件、300 insertions**，仅 `scripts/**` 16 个 + `tests/test_scripts_bootstrap_lock.py`；⛔ 未碰 venv / `.pth` / `src/` / 交接契约 |
| `git status` | ✅ 只剩 orchestrator 自己未跟踪的审阅单 ⇒ **它没扫走我的文件** |
| ⭐ **主树 `src/__init__.py` 有没有被那个 marker 污染** | ✅ **干净**：**0 字节**，最后一次改动是 `299149c`（4 月），`git diff HEAD` 为空 |
| 它造的临时 worktree | ✅ 已清理（`git worktree list` 里已无 `f94_behavior_wt`）|
| 全量数字自洽 | ✅ 3014 → **3016**，净增 2 = 新增的两条锁测试；xfailed 13→13 |
| 「16」这个数 | ✅ orchestrator **独立数过**：32 / 22 / 6 ⇒ 16，与席位一致 ⇒ **派工单的「26」确系我错** |
| ⚠️ 顺带发现 | `git worktree list` 里 `/tmp/glm_review/mut_wt` 是**上一轮 GLM 审阅**留下的、未清理的 worktree。⛔ 与本单无关，登记提醒 |
