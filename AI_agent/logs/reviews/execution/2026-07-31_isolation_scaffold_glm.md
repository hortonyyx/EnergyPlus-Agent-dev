# 执行日志 · 硬隔离识图脚手架修复批（GLM-5.2 施工）

> 派工单：`AI_agent/logs/reviews/request/2026-07-31_isolation_scaffold_construction_dispatch.md`
> 施工方：GLM-5.2（执行档）· 审阅方：sol（GPT 侧顶档，升一档交叉对抗审）· 主控轻门
> 基线：1786 passed / 10 xfailed / 0 failed
> 每个 Slice 做完即停、commit、记本日志。

## 开工前事实复核（主控派工单 §2 已逐条读码，我复验关键条目）

- sha256(worked-example) = `d3424c42…853b5ab` —— 与派工单 §2 一致。
- `_assert_source_allowed(Path("case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json"))` → **ALLOWED**（实跑）。确认 build 可经正规 `_copy_file` 拷入，不需放宽污染断言。
- worked-example 内容 = smalloffice_20（另一栋楼），无 sm24 信息；内容字符串不含任何 DENY_TOKEN（`grade`/`gt.json`/`case_tests`/`verdict`/`attempts`/`judge` 均无）。
- guard 现状：`evaluate()` 对非 Bash 工具只走 `_lexical_check`（扫整串）+ `_path_arg`（仅判在 staging 内），**不限写哪里** ⇒ 派工单 K 属实。
- prescan 落点 = `evidence_dir(out_dir, source) / label` = `out_dir/cv_evidence/<stem>/prescan/`；唯一生产调用方 = `cv_probe.py`（库函数 `prescan_plan/elevation` 无其他生产 caller）。
- `_is_run_prescan_path`：认 `run_*/0_reading/cv_evidence/<stem>/prescan/**`。正常 `--out-dir <RUN>/0_reading` 落点与之口径一致。
- merge 现状：硬要求单一聚合件 `{"views": {<expected_output_id>: <ReadingView>}}`；`expected_output_ids()` 对 sm21 = `{1f_view,2f_view,East_view,North_view,South_view,West_view}`（全部 `_view` 结尾，故派工单「多件扫 `*_view.json`」对当前语料成立）。

无前提被证伪。按 S1→S2→S3→S4 施工。

---

## S1 · 样板件进 staging（F-2）— DONE

**做了什么**
- `isolation.py`：加常量 `WORKED_EXAMPLE_SOURCE` / `WORKED_EXAMPLE_STAGED`；新增 `_copy_worked_example`（经正规 `_copy_file` 拷到 `reference/worked_example_plan.json`、category=`reference`、进 MANIFEST）；新增 `_copy_skill_kickoff`（拷 `session_kickoff.md` 时把仓库路径改写成 staging 路径）；`_copy_reading_skill` 对 `session_kickoff.md` 走改写分支；`build_isolation_workspace` 调 `_copy_worked_example`。
- 选派工单 §3-S1 出口 (b)：改写拷入的 `session_kickoff.md` 路径（kickoff 规则的 single source of truth 即此文件，子代理被令「先读三件套」，故必须改这里；只改 `_write_kickoff` 会让 `session_kickoff.md` 仍指墙外路径 ⇒ 二次同型缺陷）。

**新增锁（3）**
1. `test_build_stages_worked_example_byte_identical_and_in_manifest`：staged 件存在 + 字节与源相同 + 在 MANIFEST（category=`reference`、source_path=仓库相对路径、sha256 现算）。
2. `test_build_kickoff_points_at_staged_worked_example_path`：staged kickoff 文本不含仓库路径、含 staging 路径、且该路径真去 `stat` 存在；`case_tests/` 不进 staging。
3. `test_worked_example_staged_path_is_not_guard_denied`：`reference/worked_example_plan.json` 不触任何 DENY_TOKEN，guard 放行 Read（子代理被 kickoff 指到这里，必须可达）。

**neuter 自查（S1）**
| 锁 | neuter（生产码定点） | 变红的测试 |
|---|---|---|
| 正例 + 一致性 | 注释 `build_isolation_workspace` 里的 `_copy_worked_example(...)` 调用 | `test_build_stages_worked_example_byte_identical_and_in_manifest`、`test_build_kickoff_points_at_staged_worked_example_path` 均 **FAILED**（实跑 / 工作树临时 neuter 后还原，diff 仅 +40 无残留） |

锁 #3（guard 放行）是 guard 语义锁、不依赖文件存在，故该 neuter 下仍绿——符合预期（它测的是路径不被禁词误伤，不是文件落盘）。

**跑了哪些测试 + 数字**：`tests/test_isolation.py` 全量 **40 passed**（37 既有 + 3 新）；neuter 子集 2 failed 1 passed（还原后 40 passed）。

**偏差 / review-ask（S1）**：none——派工单给的两条出口里选 (b)，理由见上「先读三件套」。

