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


## S2 · 守卫：收紧写保护 + 放松散文扫描（F-4 + K）— DONE

**做了什么（两半配对，净效果更严 + 更好用）**

2a 写保护（收紧）：
- `guard.py`：加 `WRITE_TOOLS`/`WRITE_TARGET_KEYS`/`WRITE_ALLOWED_DIRS`；新增 `_write_target`（取 file_path/notebook_path 并经 `_path_arg` 解析+越界+symlink 校验）+ `_check_write_target`（resolved target 必须落在 `out/` 或 `requests/` 下，否则 deny）；`evaluate` 对 Write/Edit/MultiEdit/NotebookEdit 先做写保护门。
- `isolation.py`：build 预建 `requests/` 目录；`_write_kickoff` 改写明「reading 输出写 out/、CV probe 请求 JSON 写 requests/、经 `python tools/run_cv_probe.py --request requests/<name>.json` 调用」；`_write_settings` 的 allow 列表加 `Write/Edit(requests/**)`（否则子代理写 requests/ 到不了 guard，与 out/ 对称）。

2b 放松散文扫描（放松）：
- `guard.py`：`evaluate` 非 Bash 分支只对 `_looks_like_path(value)==True` 的串跑 `_lexical_check`（DENY_TOKENS/`~`/`..`）；非路径散文（Write/Edit 的 content、note）不扫这三类。
- **不动**：`_lexical_check` 本身（仍严格）、`_check_bash`（Bash command 整串仍严格：COMPOUND_TOKENS/命令白名单/`python -c`/`_validate_request_file` 全保留）、`DENY_TOKENS` 表（对路径仍有效，未删条目）。

**新增锁（S2）**
- `test_build_precreates_requests_dir_and_kickoff_mentions_it`：build 建 requests/、kickoff 含 requests/ 与 out/、settings allow 含 requests 写权限。
- `test_guard_denies_write_outside_out_or_requests`（参数化 12 目标）：tools/run_cv_probe.py、tools/cv_probe.py、guard.py、isolation_settings.json、MANIFEST.json、binding.json、skills/**、src/**、case_data/**、prescan/**、reference/**、staging 根文件 —— 全 deny。
- `test_guard_denies_overwrite_of_tools_run_cv_probe`：F-4/K 头条洞（改造前 allow）现 deny。
- `test_guard_allows_write_under_out_or_requests`（参数化 4）：out/、out/sub/、requests/、requests/sub/ 全 allow。
- `test_guard_allows_reading_summary_with_prose_forbidden_tokens`：可用性正例（content 含 `~`、`grade line`、`..`、分号 ⇒ allow）—— 直击 07-30 三连拒。
- `test_guard_security_properties_stay_denied`（参数化 6）：gt.json Read deny / case_tests Read deny / 越界绝对路径 deny / 非白名单命令 deny / `python -c` deny / 复合 token deny。
- `test_guard_denies_read_of_symlink_escaping_staging`：性质 4（越界 symlink）非 Bash 侧 deny。
- `test_guard_denies_bash_request_file_with_forbidden_token`：性质 8（请求 JSON 含禁词）deny（`_validate_request_file` 严格扫描不动）。
  - 性质 4 的 Bash 侧 = 既有 `test_guard_rejects_symlink_and_request_paths_outside_staging`（未动，仍绿）。

**八条安全性质清单（改造前后均红→deny）**：①gt.json ②case_tests ③越界绝对路径 ④越界 symlink（Bash 既有 + 非 Bash 新增）⑤非白名单命令 ⑥python -c ⑦复合 token ⑧请求 JSON 禁词 —— 八条均有锁钉死。

**neuter 自查（S2）**
| 锁族 | neuter（生产码定点） | 变红的测试 |
|---|---|---|
| 2a 写保护 | 删 `evaluate` 里 `if tool in WRITE_TOOLS:` 整块 | `test_guard_denies_overwrite_of_tools_run_cv_probe` + `test_guard_denies_write_outside_out_or_requests`（全部 12 参数）= **13 FAILED**（Write 到 tools/ 等变 allow，K 洞复现）；4 个 allow-under 测试仍绿（与 neuter 无关） |
| 2b 放松扫描 | 去掉 `if not _looks_like_path(value): continue`（退回对全部非 Bash 串严格扫描） | `test_guard_allows_reading_summary_with_prose_forbidden_tokens` **FAILED**（content 里 `..` 触发 "parent traversal token is forbidden"）；八条安全性质 + allow-under 全绿（严格更严，不翻 allow） |

两 neuter 均经工作树临时破坏→跑→还原（guard.py diff 始终 +59/−5 无残留），还原后 `tests/test_isolation.py` 全量 **67 passed**。

**跑了哪些测试 + 数字**：`tests/test_isolation.py` 全量 **67 passed**（40 既有 + 27 新）；受影响子集（`affected_tests.py --changed isolation.py guard.py`）= `tests/test_isolation.py`。

**偏差 / review-ask（S2）**
- **settings.json 加 requests/ 写权限**：派工单 §3-S2a 只明列「build 预建 requests/ + kickoff 写明」，未提 settings.json。但 fact F 证明 guard 会触发 Write 工具（out/ 写被 guard 拒 3 次），故子代理写 requests/ 要真到 guard，settings.json 的 allow 必须含 requests/**（与 out/ 对称）。这是为让该功能可用而做的最小一致改动，非放松安全（guard 仍是权威写保护门）。
- **S2b 路径判定的边界**：`_looks_like_path` 对「整串」判定（含 `/`/起首 `.`/末尾扩展名）。故 content 整串不含 `/` 时才免扫；若 reading 摘要或立面 JSON 整串里恰好含 `/`（如备注 "south/north"），仍会被当路径扫到 `grade` 等。派工单给的就是这条规则（"只作用于被 `_looks_like_path` 判定为路径的字符串"），我照搬；现实 reading 产物整串含 `/` 罕见（坐标/中文 note 无 `/`），fact F 的 `grade line`/`~` 场景正好命中免扫。如实登记，未自行加宽。

