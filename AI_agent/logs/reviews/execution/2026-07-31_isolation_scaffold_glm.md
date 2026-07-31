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


## S3 · prescan 落点语义收口（F-1）— DONE

**做了什么**
- `scripts/tool_scripts/cv_probe.py`：新增 `_reject_nested_prescan_out_dir`（`--out-dir` 末级目录名 ∈ {`cv_evidence`,`prescan`} ⇒ 返回错误信息）；合并 prescan-plan/prescan-elevation 两分支为一条：先查 nested（命中则 stderr 打错误样例 + `return 2`，**不写任何文件**），再调库函数，最后 `print` 落点绝对路径（candidates.json）。
- `AI_agent/guides/new_case_guide.md` §2.1：写死命令行样例 `--out-dir <RUN>/0_reading`，注明工具自行追加 `cv_evidence/<stem>/prescan/`、套娃会 fail-closed、CLI 会回显落点。
- 库函数 `prescan_plan/elevation`（recipes.py）与 `evidence_dir`（sidecar.py）**不动**——派工单指明改 cv_probe.py（唯一生产调用方），库层无其他生产 caller。

**新增锁（S3）**
1. `test_cv_probe_rejects_nested_prescan_out_dir`（参数化 `cv_evidence`/`prescan`）：套娃 `--out-dir` ⇒ 非零退出 + `run_x` 下零 `candidates.json` + 不建套娃目录。
2. `test_cv_probe_prescan_echoes_landing_matching_copy_guard`：正常 `--out-dir=<RUN>/0_reading` ⇒ 退出 0 + stdout 落点存在且 `_is_run_prescan_path(落点)==True`（**真正要防的回归**：CLI 落点与隔离拷贝守卫口径一致）。

**neuter 自查（S3）**
| 锁 | neuter（生产码定点） | 变红的测试 |
|---|---|---|
| 套娃拒绝 | `cv_probe.py` 把 `_reject_nested_prescan_out_dir(args.out_dir)` 改为常空串（跳过拒绝门） | `test_cv_probe_rejects_nested_prescan_out_dir[cv_evidence]` + `[prescan]` 均 **FAILED**（退出 0、stdout 现套娃路径 `.../prescan/cv_evidence/plan/prescan/candidates.json`） |
| 落点↔守卫口径一致 | `isolation.py` `_is_run_prescan_path` 强制 `return False`（关 oracle） | `test_cv_probe_prescan_echoes_landing_matching_copy_guard` **FAILED** + 既有 `test_run_prescan_source_path_is_allowed` **FAILED**（证明 parity 锁真耦合 oracle、非空套） |

两 neuter 均工作树临时破坏→跑→还原（cv_probe.py +28/−13；isolation.py 还原到 S2 态无残留）。

**跑了哪些测试 + 数字**：受影响子集（`affected_tests.py --changed cv_probe.py isolation.py`）= `test_affected_tests_map + test_cv_toolbox + test_gt_discipline + test_isolation` → **90 passed**。

**偏差 / review-ask（S3）**
- 锁 #2 的 neuter 在 **oracle 侧**（`_is_run_prescan_path` 关掉）而非改 CLI 落点布局。理由：锁本质是「CLI 实际落点 ↔ 拷贝守卫」的跨模块一致性断言，oracle-side neuter 证明锁真耦合守卫、非空套；CLI 落点由 `evidence_dir`+`label` 独立算出并 print，两侧独立 ⇒ 锁确在交叉核。如实登记。
- 嵌套检测只查末级目录名 ∈ {`cv_evidence`,`prescan`}（派工单给定的判定）。若调用方传 `<RUN>/0_reading/cv_evidence/1f_view`（末级是 stem）仍会套娃但不被本门拦——派工单只要求这两类，未扩；现实手册已写死 `--out-dir <RUN>/0_reading`，照搬未自行加宽。


## S4 · merge 目录形态自聚合（F-5）— DONE

**做了什么**
- `isolation.py`：新增 `_load_isolated_views(output_path, out_dir, view_manifest) -> (payload, out_text)`：
  - 老路径（不破）：`out/output.json` 形如 `{"views": {<expected_output_id>: <ReadingView>}}` ⇒ 原样用（逐字节 out_text）。
  - 新路径（S4）：无有效聚合件时，按 view_manifest 的 `expected_output_ids()` 机械搬运 `out/` 下 `<expected_output_id>.json`（即 `*_view.json`，对当前语料 expected_output_id 全 `_view` 结尾成立）为 `{"views": {…}}`。纯搬运（`json.loads` 每个源文件、不规范化/不补默认/不排序）。
  - fail-closed：缺件（manifest 某 id 无文件）⇒ ValueError("missing …")；多件（`*_view.json` 不在 manifest）⇒ ValueError("unexpected …")。
- `merge_isolated_output`：`output_path.resolve(strict=False)`（assembly 路径无 output.json）；用 `_load_isolated_views` 替换原硬要求单一聚合件的块。
- 定为 merge 侧自聚合（非 kickoff 多要一个文件）——对齐不变量「强制约束别交给 LLM 记得」（派工单明令）。

**新增锁（S4）**
1. `test_merge_assembles_per_image_views_byte_equal_and_accepts`：正例——五+图目录（sm21 六图）无聚合件 ⇒ 自聚合；每个 view `== json.loads(源文件)` 且 `== 原始 view`（零改动）；accepted、artifact_contract、output_hash 钉死。
2. `test_merge_per_image_missing_is_rejected`：缺件 ⇒ ValueError("missing") + 不落 attempt。
3. `test_merge_per_image_extra_is_rejected`：多件（`rogue_view.json`）⇒ ValueError("unexpected")。
4. `test_merge_single_aggregate_still_accepted_alongside_per_image`：老路径不破——有有效聚合件时原样用（per-image 件被忽略、不聚合），attempt 的 output.json 与聚合件逐字节相同。

**neuter 自查（S4）**
| 锁 | neuter（生产码定点） | 变红的测试 |
|---|---|---|
| 缺件 fail-closed | 删 `_load_isolated_views` 里 missing 检查块 | `test_merge_per_image_missing_is_rejected` **FAILED**（KeyError，非 ValueError "missing"） |
| 多件 fail-closed | 删 extra 检查块 | `test_merge_per_image_extra_is_rejected` **FAILED**（DID NOT RAISE，多件被静默忽略、merge 推进） |
| 正例聚合 | `glob("*_view.json")` 改 `glob("*_NOPE.json")` | `test_merge_assembles_per_image_views_byte_equal_and_accepts` **FAILED**（ValueError: missing all） |
| 零内容改动（==） | 聚合时给每个 view 注入 `{"_mutated": True, **…}` | 同正例测试 **FAILED**（`assembled["views"][eid] == view` AssertionError） |

四 neuter 均工作树临时破坏→跑→还原（isolation.py 回到 +53/−12 S4 态、无残留），还原后正例 **1 passed**。

**跑了哪些测试 + 数字**：`tests/test_isolation.py` 全量 **71 passed**（67 既含 S2 + 4 S4 新）；既有 11 个 merge 老路径测试全绿（老路径不破）。

**偏差 / review-ask（S4）**
- 多件扫描用 `*_view.json`（派工单给定）。对当前语料成立（floor/cardinal 的 expected_output_id=identity 保留 `_view` 词干、supplementary 的 append_view 加 `_view`）。若未来某 family 的 expected_output_id 不以 `_view` 结尾，其 per-image 件不会被多件扫描命中、也不会被正例聚合命中（缺件报错）——派工单的口径即此，未自行改成 `*.json`（那会误伤 output.json/其他）。如实登记。
- 损坏的 `output.json`（非法 JSON）现在落 assembly 而非硬报「not valid JSON」（原老路径会报）。理由：assembly 是新主路径，损坏聚合件不该阻断「per-image 件齐」的正常聚合；若 per-image 也缺 ⇒ missing 报错 fail-closed。这是比原行为更宽容但仍 fail-closed 的取舍，如实登记。

