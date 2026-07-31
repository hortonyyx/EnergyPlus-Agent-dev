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
| 正例聚合 / glob 枚举 | `glob("*_view.json")` 改 `glob("*_NOPE.json")` | **2 FAILED**：`test_merge_assembles_per_image_views_byte_equal_and_accepts`（ValueError: missing all）+ `test_merge_per_image_extra_is_rejected`（预期 `unexpected`，实得 `missing`） |
| 零内容改动（==） | 聚合时给每个 view 注入 `{"_mutated": True, **…}` | 同正例测试 **FAILED**（`assembled["views"][eid] == view` AssertionError） |

四 neuter 均工作树临时破坏→跑→还原（isolation.py 回到 +53/−12 S4 态、无残留），还原后正例 **1 passed**。

**跑了哪些测试 + 数字**：`tests/test_isolation.py` 全量 **71 passed**（67 既含 S2 + 4 S4 新）；既有 11 个 merge 老路径测试全绿（老路径不破）。

**偏差 / review-ask（S4）**
- 多件扫描用 `*_view.json`（派工单给定）。对当前语料成立（floor/cardinal 的 expected_output_id=identity 保留 `_view` 词干、supplementary 的 append_view 加 `_view`）。若未来某 family 的 expected_output_id 不以 `_view` 结尾，其 per-image 件不会被多件扫描命中、也不会被正例聚合命中（缺件报错）——派工单的口径即此，未自行改成 `*.json`（那会误伤 output.json/其他）。如实登记。
- 损坏的 `output.json`（非法 JSON）现在落 assembly 而非硬报「not valid JSON」（原老路径会报）。理由：assembly 是新主路径，损坏聚合件不该阻断「per-image 件齐」的正常聚合；若 per-image 也缺 ⇒ missing 报错 fail-closed。这是比原行为更宽容但仍 fail-closed 的取舍，如实登记。


## 全仓交付前自跑 + neuter 总账

**全仓（HEAD，含并行 sol 席位的 judge WIP）**：1823 passed / 10 xfailed / **6 failed**。
- 6 failed 全在 `tests/test_reading_typed_scoring_slice0.py`（reading 类型化判卷层）。
- **归因核实（不是我）**：该文件在 baseline `f98d248` **不存在**，6 个失败用例名 baseline 全部**缺席**；文件仅由 sol 的两个并行 commit（`e355654 ReadingTypedScoringSlice0RedLocks` / `6ed37a9 ReadingTypedScoringSlice0U13Correction`）创建/修改；`git diff f98d248..HEAD -- src/ scripts/ skills/` 显示**除我 3 个文件外 sol 零源码改动**（sol 在 TDD red-lock 阶段：给尚未实现的判卷代码写会红的锁）⇒ 6 failed 是 sol 的并行 WIP、派工单明令我不得碰的判卷层，非本批回归。
- 并行交错如实登记：sol 在我跑测期间提交了两次（`e355654` 插在我 S2 与 S3 之间、`6ed37a9` 在我 S4 之后=当前 HEAD）；我 4 个 commit（`78967eb/c42de85/f2a4efb/c9974fd`）完整在册、未受影响。

**全仓（忽略 sol WIP 文件）= 本批净验证**：`--ignore=tests/test_reading_typed_scoring_slice0.py` → **1823 passed / 10 xfailed / 0 failed**。
- = baseline 1786 + 本批新增 37（S1×3 + S2×27 + S3×3 + S4×4）⇒ **零回归**。

**neuter 自查总账（每把新锁经实跑核）**

| Slice | 锁族 | neuter（生产码定点） | 变红测试（实跑） |
|---|---|---|---|
| S1 | 正例+一致性 | 注释 `_copy_worked_example(...)` 调用 | 2 FAILED（staged 件存在 / kickoff 路径 stat） |
| S2a | 写保护 | 删 `evaluate` 的 `if tool in WRITE_TOOLS:` 块 | 13 FAILED（12 deny-write 参数 + K 头条） |
| S2b | 散文放松 | 去掉 `if not _looks_like_path(value): continue` | 1 FAILED（reading_summary 散文锁） |
| S3 | 套娃拒绝 | `_reject_nested_prescan_out_dir` 返回常空串 | 2 FAILED（cv_evidence/prescan 两参数） |
| S3 | 落点↔守卫 | `_is_run_prescan_path` 强制 `return False` | 2 FAILED（parity 锁 + 既有 isolation 测试） |
| S4 | 缺件 | 删 missing 检查块 | 1 FAILED（KeyError 非 ValueError） |
| S4 | 多件 | 删 extra 检查块 | 1 FAILED（DID NOT RAISE） |
| S4 | 正例聚合 / glob 枚举 | `glob("*_view.json")`→`glob("*_NOPE.json")` | **2 FAILED**：`test_merge_assembles_per_image_views_byte_equal_and_accepts` + `test_merge_per_image_extra_is_rejected` |
| S4 | 零改动(==) | 聚合时注入 `{"_mutated":True,**…}` | 1 FAILED（== AssertionError） |

全部 neuter 工作树临时破坏→跑→还原（每 Slice commit 前文件回净、无残留）。

**改了哪些文件（生产码 + 测试 + 文档）**
- `src/agent/execution/isolation.py`（S1 worked-example 拷入+改写 kickoff 路径 / S2 build 预建 requests+settings+ kickoff 文本 / S4 merge 自聚合）
- `src/agent/execution/isolation_templates/guard.py`（S2 写保护 + 散文放松）
- `scripts/tool_scripts/cv_probe.py`（S3 prescan 套娃拒绝 + 回显落点）
- `tests/test_isolation.py`（S1+S2+S4 锁）、`tests/test_cv_toolbox.py`（S3 锁）
- `AI_agent/guides/new_case_guide.md`（S3 §2.1 命令样例写死）
- 本执行日志


## 返工 r1 · S2b 路径判定改「按参数角色」而非「按整串形状」（主控轻门裁定）— DONE

> 返工单：`AI_agent/logs/reviews/request/2026-07-31_isolation_scaffold_rework_r1.md`
> 主控裁定：我在 S2 review-ask 里登记的 S2b 边界（`_looks_like_path` 对「整串」判定）比我估计的更差——主控用活体探针实证推翻「现实 reading 产物整串含 `/` 罕见」：content 里同时出现任意一个 `/`（一个日期 `2026/07/31` 即足）与任意一个禁词 ⇒ 仍被当路径扫到、`grade line` 仍被拒、F-4 在真实产物上仍复发。这是主控骨架写窄、非我施工错。
> 裁定（修到根因、不再加豁免词）：**按参数角色判，不按字符串长相判**。content 角色参数整个排除出路径形状扫描、一个字符都不扫。

**做了什么（`guard.py`）**
- 新增常量 `CONTENT_ROLE_KEYS = ("content", "old_string", "new_string", "new_source")`（content 角色参数名；`new_source`=NotebookEdit 同类文本体参数）。
- 新增 `_walk_items(value, key=None)`：键感知遍历器，yield `(key, value)`；list 元素继承外层 dict key（MultiEdit 的 `edits` 列表递归进每个 edit dict、按名命中 `old_string`/`new_string`）。原 `_walk_values`（无键）保留给 `_validate_request_file`（cv_probe 请求 JSON 是另一攻击面、严格扫描不动）。
- `evaluate()` 的 S2b 扫描循环：由「`_walk_values` + `_looks_like_path` 整串门」改为「`_walk_items` + 按 key 跳过 content 角色 + 再 `_looks_like_path`」。即 content 角色参数**在 `_looks_like_path` 之前**就被排除，一个字符都不扫。
- 不动：`_lexical_check`（仍严格）/`_check_bash`（Bash command 整串仍严格）/`_write_target`+`_check_write_target`（S2a 写保护仍权威）/`_validate_request_file`（请求 JSON 仍全扫）/`DENY_TOKENS` 表（对路径仍有效、未删条目）。

**新增锁（r1，4 把）**
1. `test_guard_r1_allows_reading_summary_content_with_slash_and_grade_line`：主控活体探针 case —— content = `"Windows on 2026/07/31: grade line at z=0, span 1.2 m."` 写 out/reading_summary.md ⇒ **ALLOW**（原 S2b 整串 `_looks_like_path` 命中 `/`→扫到 `grade`→DENY）。**返工单锁 1**。
2. `test_guard_r1_excludes_content_role_params_from_path_scan`（参数化 5：Write `content` / Edit `old_string` / Edit `new_string` / MultiEdit `edits[]` / NotebookEdit `new_source`）：每个 payload 文本体都同时含 `/` 与一个 DENY_TOKEN（`grade`/`case_tests`）⇒ 全 **ALLOW**。钉死「按参数角色」跨工具、非 `content` 一刀切特例。
3. `test_guard_r1_denies_write_to_tools_with_innocent_prose_content`：写 `tools/run_cv_probe.py` 且 content 是纯净散文（无 `/` 无禁词）⇒ 仍 **DENY**（`write target must be under out/ or requests/`）。证明放松的是内容扫描、不是写保护。**返工单锁 2**。
4. `test_guard_r1_bash_command_with_case_tests_still_denied`：Bash `ls case_tests/x` ⇒ **DENY**（`forbidden token: case_tests`）。证明 content-role 放松不沾 Bash 路径。**返工单锁 3**。

**neuter 自查（r1，每把新锁经实跑核；工作树临时破坏→跑→还原、diff 无残留）**
| 锁 | neuter（生产码定点） | 变红的测试（实跑） |
|---|---|---|
| 锁 1+2（角色排除） | `evaluate` 里 `if key in CONTENT_ROLE_KEYS:` 改 `and False`（恢复扫 content 串） | **6 FAILED**：锁 1（date+grade line）+ 参数化 5（write_content/edit_old/edit_new/multiedit/notebook）全 DENY；既有散文锁（content 无 `/`）仍绿——**精确坐实原 S2b 边界**（无 `/` 的散文原就过、含 `/` 的才崩） |
| 锁 3（写保护） | `_check_write_target` 首行强 `return True,"neutered"`（写保护门全开） | **14 FAILED**：锁 3（tools/run_cv_probe.py 写变 allow）+ S2a 头条（denies_overwrite_of_tools_run_cv_probe）+ 12 参数（denies_write_outside_out_or_requests）；4 个 allows_write_under 仍绿（out//requests 本就 allow、不受影响） |
| 锁 4（Bash 严格） | `_check_bash` 首行 `ok,reason = _lexical_check(...)` 改 `True,"neutered"`（跳过 Bash 整串扫） | **1 FAILED**：锁 4（`ls case_tests/x` 变 allow）；其余 Bash DENY 测试（非白名单命令/`python -c`/复合 token/请求 JSON 禁词/symlink 越界）**全仍红**——它们由 Bash 的**其他**独立防线（命令白名单/COMPOUND_TOKENS/`_validate_request_file`/`_path_arg` 越界）兜住 ⇒ 锁 4 是 Bash 命令里 DENY_TOKEN 的**唯一**锁、精确无冗余 |

还原后 `diff` guard.py 与修好态逐字节相同（`grep -c NEUTER` = 0）。

**跑了哪些测试 + 数字**
- 受影响子集（`affected_tests.py --changed guard.py test_isolation.py`）= `tests/test_isolation.py` → **79 passed**（71 S4 尾态 + 8 r1 新）。
- **全仓 = 1880 passed / 10 xfailed / 0 failed**（5:02）。= baseline 1786 + 本批 45（S1×3+S2×27+S3×3+S4×4=37 + r1×8）+ sol 并行 reading-typed-scoring Slice0–5 净增 ≈49。**零回归**。
- ⚠️ 主控告并行 sol 席位正改 judge/scoring 测试；本轮全仓 **judge/scoring 零 failed**（两批当前态不撞）；工作树里 sol-scope 文件（`src/agent/judge/opening_claim_score.py`·`reading_typed_score.py`·`tests/test_c2_b4b_score_inputs.py`·`tests/test_reading_typed_scoring_slice1.py`）有未提交改动——**我未触碰、未 stage、未 commit**，commit 只含我自己的两个文件 + 本日志。

**偏差 / review-ask（r1）**
- `CONTENT_ROLE_KEYS` 含 `new_source`（NotebookEdit 的文本体参数），返工单只点名 `content`/`new_string`/`old_string` +「同类文本体参数」。`new_source` 即同类、纳入排除（不扫）；如主控认为 NotebookEdit 不在隔离 reader 的工具面、不该纳入，可删该 key——但纳入是「按角色」的自然结果、且更严（少一个误伤面）非放松安全。如实登记。
- 非 content 角色串仍走 `_looks_like_path` 整串门（仅作 secondary filter、扫 file_path 等路径角色串）。返工单裁定的是「content 角色整个排除」，未要求删 `_looks_like_path`；保留它对 file_path 等仍提供 DENY_TOKEN 兜底（如 `out/case_tests/x` 写名仍被拦）。`_looks_like_path` 同时仍被 `_validate_request_file` 用、未动。如实登记。

**改了哪些文件（r1）**
- `src/agent/execution/isolation_templates/guard.py`（`CONTENT_ROLE_KEYS` + `_walk_items` + `evaluate` S2b 循环改键感知）
- `tests/test_isolation.py`（4 把 r1 锁）
- 本执行日志（本节）


## 返工 r2 · sol 对抗审四项 MAJOR + 三项 MINOR 收口 — DONE

> 返工单：`AI_agent/logs/reviews/request/2026-07-31_isolation_scaffold_rework_r2.md`
> 施工交接：前一施工席完成并提交 R2-1～R2-5 后额度中断；sol 经主控明确切换为 builder，续做 R2-2 E2E 锁、R2-6、全轮 neuter 复核与本日志。独立验收仍由主控执行。
> r2 起点：`6da9136`（`40e1470^`）；提交：`40e1470`、`141f019`、`e3f3a3a`、`05ae23e`、`eb6c9e2`、`2676e04`、`5ecebb9`。

### R2-1 · 参数角色全函数（MAJOR-2）

**实现**
- `guard.py` 的 `_param_role(key)` 只有 `content` / `path` 两种结果：`CONTENT_ROLE_KEYS` 明列的文本体参数完全免扫；其余 key（包括未知 key、`None`）全部按 path 角色处理。
- `evaluate()` 对 path 角色无条件执行 `_lexical_check` + `_path_arg`，不再以 `_looks_like_path()` 猜形状；`_looks_like_path()` 只留在 CV request 的非输出参数规范化分支。
- 新锁覆盖 `file_path="case_tests"` 与 `case_tests/x`、`escape` 与 `./escape`、未知/嵌套未知 key，以及 `_param_role` 的结构全函数；r1 的 prose ALLOW 锁保留。

**定点 neuter 实跑**
- 复原 r1 的形状门（path 角色先走 `_looks_like_path()`）后运行：

```text
pytest -q tests/test_isolation.py -k 'guard_r2_bare or guard_r2_unknown or guard_r2_param_role or guard_r1_allows_reading_summary or guard_r1_excludes_content'
```

结果 **5 failed, 9 passed**；真实变红：
`test_guard_r2_bare_and_slashed_forbidden_path_both_denied[case_tests]`、
`test_guard_r2_bare_extensionless_escaping_symlink_denied[escape]`、
`test_guard_r2_unknown_key_defaults_to_path_role[unknown_key_bare_deny_token-tool_input0]`、
`test_guard_r2_unknown_key_defaults_to_path_role[unknown_key_bare_escaping_symlink-tool_input1]`、
`test_guard_r2_unknown_key_defaults_to_path_role[unknown_nested_key_bare_deny_token-tool_input2]`。
带斜杠的对照形状与 r1 prose ALLOW 锁保持绿，准确复现原洞而非泛化破坏。
- 再把 `_param_role()` 定点 neuter 为恒 `return "content"`，同命令结果 **8 failed, 6 passed**：上述三个 live 测试族的 2+2+3 个参数全部红，另有 `test_guard_r2_param_role_is_total_over_keys` 红。证明结构锁和每种 live 形状都不是空锁。

### R2-2 · helper 输出副作用约束 + 真 E2E 锁（MAJOR-1）

**实现**
- 审计 `run_cv_probe.py` 的全部 `ALLOWED_TOOLS` 后，确认唯一输出落点参数是 `out_dir`；guard 的 `_validate_request_file()` 对该角色执行 `_path_arg` 后再要求落入真实 `out/**`，`requests/**` 只承载 request JSON，不是 helper 输出根。
- staged wrapper `isolation_templates/run_cv_probe.py` 独立执行同一 `out/**` 边界；输入参数仍只要求在 staging 内。
- E2E 锁 `_staging_snapshot()` 对整棵 staging 的目录、文件内容哈希与 symlink target 建签名；`_protected_tree_diff()` 同时抓 added / removed / rewritten。唯一显式豁免为：
  - `_E2E_WRITABLE_PREFIXES = ("out/", "requests/")`
  - `_E2E_EXEMPT_NAMES = ("access_log.jsonl",)`
  - `_E2E_EXEMPT_PARTS = ("__pycache__",)`
- `test_e2e_hook_then_helper_changes_only_writable_tree` 构造真实 staging/request，先跑 hook，只对 hook ALLOW 的形状执行真实 helper，再比较全树。`inside_out` 还要求 helper 真在 `out/**` 新增文件，防止“不执行 helper 也绿”的空锁。`test_wrapper_independently_refuses_outside_output_and_tree_is_unchanged` 绕过 hook 直接核 wrapper。

**正常态实跑**

```text
pytest -q tests/test_isolation.py -k 'request_output_dir_outside_writable_root or wrapper_independently_refuses_outside_output or e2e_hook_then_helper_changes_only_writable_tree'
```

结果 **11 passed**。

**定点 neuter 实跑**

| 破坏点 | 命令 / 结果 | 真实变红测试 |
|---|---|---|
| guard `_check_output_target()` 恒 ALLOW | 上述 11-test 命令：**9 failed, 2 passed** | `test_guard_denies_request_output_dir_outside_writable_root` 的 7 参数 + `test_e2e_hook_then_helper_changes_only_writable_tree[outside_tools-tools-False]` + `[outside_reference-reference-False]` |
| wrapper `_resolve_output()` 退回普通 `_resolve()` | 上述 11-test 命令：**1 failed, 10 passed** | `test_wrapper_independently_refuses_outside_output_and_tree_is_unchanged`；全树 diff 真看到 `added:tools/**`（共 5 个受保护条目），不是只看返回码 |
| wrapper 在 `cv_main(cv_argv)` 调用点直接 `return 0`（成功但不执行） | `pytest -q tests/test_isolation.py -k 'e2e_hook_then_helper_changes_only_writable_tree'`：**1 failed, 2 passed** | `test_e2e_hook_then_helper_changes_only_writable_tree[inside_out-out/cv-True]`，报 `the helper wrote no files under out/ — the E2E diff would be vacuous` |

### R2-3 · 可写根必须是真目录且自解析（MAJOR-3）

**实现**
- `_writable_root()` 要求 `out/`、`requests/` 均为真实目录、非 symlink、`resolve(strict=True)` 等于字面路径且仍在 staging 内。
- `_assert_writable_roots()` 每次 `evaluate()` 都重验授权根；任一异常时整次调用 fail-closed，不能跳过坏根后继续。
- 锁同时覆盖 build 前预置 `out -> tools` / `requests -> tools`，以及正常 build 后把 `out` 换成 symlink。

**定点 neuter 实跑**：把 `_writable_root()` 退回 `(root / name).resolve(strict=False)` 后：

```text
pytest -q tests/test_isolation.py -k 'allowed_root_is_a_symlink or allowed_root_symlinked_after_build'
```

结果 **3 failed**：
`test_guard_denies_writes_when_an_allowed_root_is_a_symlink[out]`、
`test_guard_denies_writes_when_an_allowed_root_is_a_symlink[requests]`、
`test_guard_denies_writes_when_allowed_root_symlinked_after_build`。

### R2-4 · kickoff 指针一致性锁改为解析实值（MAJOR-4）

**实现**
- `test_build_kickoff_points_at_staged_worked_example_path` 用 `_KICKOFF_POINTER_RE.search()` 从 kickoff 的 `Canonical worked-example file:` 语法槽解析实际路径，随后对解析值执行 `is_file()` 与字节同一性检查，不再拿测试常量自证。

**定点 neuter 实跑**：仅把生产 kickoff 指针改成 `WORKED_EXAMPLE_STAGED + ".missing"` 后：

```text
pytest -q tests/test_isolation.py -k 'build_stages_worked_example_byte_identical_and_in_manifest or build_kickoff_points_at_staged_worked_example_path or worked_example_staged_path_is_not_guard_denied'
```

结果 **1 failed, 2 passed**；唯一变红为 `test_build_kickoff_points_at_staged_worked_example_path`，错误明确指向解析出的 `reference/worked_example_plan.json.missing` 不存在。

### R2-5 · 多个 write target key 一律拒绝（MINOR-1）

**实现**
- `_write_targets()` 先收集所有 present target key；出现两个或以上即报 `ambiguous write target`，单目标才解析和校验，不能再由首个 key 遮蔽另一个落点。
- 参数锁覆盖合法 `file_path` 遮蔽非法 `notebook_path`、反向顺序、以及两个目标都合法但调用语义仍歧义。

**定点 neuter 实跑**：删除 `len(present) > 1` 拒绝，并退回只返回 `present[0]` 后：

```text
pytest -q tests/test_isolation.py -k 'guard_denies_ambiguous_multiple_write_targets'
```

结果 **3 failed**：
`test_guard_denies_ambiguous_multiple_write_targets[decoy_file_path_masks_notebook_path-tool_input0]`、
`test_guard_denies_ambiguous_multiple_write_targets[decoy_notebook_path_masks_file_path-tool_input1]`、
`test_guard_denies_ambiguous_multiple_write_targets[both_targets_legal_still_ambiguous-tool_input2]`。
第一、第三形状直接变 ALLOW；第二形状虽由非法 `file_path` 得到 DENY，但理由退化为 `write target must be under out/ or requests/`，仍被锁要求的歧义拒绝语义抓住。

### R2-6 · 既存损坏 aggregate 必须响亮失败 + S4 表更正（MINOR-2 / MINOR-3）

**实现**
- `_load_isolated_views()` 只在 `out/output.json` **不存在**时进入 per-image assembly。
- 文件存在时只读一次：非法 JSON 报 `aggregate output.json is not valid JSON`；外形不是 `{"views": dict}` 报 `aggregate output.json must be shaped ...`。即使所有 per-image 文件齐全，也不把 corruption 解释成 absence。
- 新锁 `test_merge_existing_corrupt_aggregate_is_rejected_instead_of_assembled` 参数化 `invalid_json` / `wrong_shape`，并断言失败前不创建 attempt。

**正常态实跑**

```text
pytest -q tests/test_isolation.py -k 'merge_existing_corrupt_aggregate or merge_assembles_per_image or merge_per_image_missing or merge_per_image_extra or merge_single_aggregate'
```

结果 **6 passed**。

**定点 neuter 实跑**
- 把 aggregate 存在分支改成 `if False and output_path.exists():`，同一 6-test 命令结果 **2 failed, 4 passed**：
  - `test_merge_existing_corrupt_aggregate_is_rejected_instead_of_assembled[invalid_json]`
  - `test_merge_existing_corrupt_aggregate_is_rejected_instead_of_assembled[wrong_shape]`
  两者均为 `DID NOT RAISE`。
- 独立复跑旧 S4 glob neuter：

```text
pytest -q tests/test_isolation.py -k 'merge_assembles_per_image_views_byte_equal_and_accepts or merge_per_image_missing_is_rejected or merge_per_image_extra_is_rejected or merge_single_aggregate_still_accepted_alongside_per_image'
```

把 `glob("*_view.json")` 改为 `glob("*_NOPE.json")` 后结果 **2 failed, 2 passed**，真实红测是：
`test_merge_assembles_per_image_views_byte_equal_and_accepts` 与
`test_merge_per_image_extra_is_rejected`。前面 S4 局部表和总账现已一并从“1 FAILED”更正为“2 FAILED”。

### r2 跑测、范围与交付

- 受影响映射：

```text
python scripts/tool_scripts/affected_tests.py --changed src/agent/execution/isolation.py tests/test_isolation.py
```

输出 `tests/test_affected_tests_map.py tests/test_cv_toolbox.py tests/test_isolation.py`；实跑 **144 passed**。
- 最终全仓只跑一次：

```text
pytest -q
```

结果 **1908 passed / 10 xfailed / 0 failed**（291.12s），相对主控 r2 基线 `1881 passed / 10 xfailed / 0 failed` 净增 27 tests，零回归。
- 范围核：

```text
git diff --quiet 40e1470^..HEAD -- src/agent/judge case_tests/test_baseline/gt AI_agent/CLAUDE.md
```

退出码 **0**；r2 未改判卷批、受保护人签 GT 树或 `AI_agent/CLAUDE.md`。
- r2 改动文件：`src/agent/execution/isolation.py`、`src/agent/execution/isolation_templates/guard.py`、`src/agent/execution/isolation_templates/run_cv_probe.py`、`tests/test_isolation.py`、本执行日志。`scripts/tool_scripts/cv_probe.py` 无 r2 改动。
- 所有 neuter 均只在 `/tmp/isolation-scaffold-r2-neuter.lXmNfo/repo` 做；结束时 `isolation.py`、`guard.py`、`run_cv_probe.py`、`tests/test_isolation.py` 分别与主工作树 `cmp` 一致。主工作树未做实验性破坏，未写 `case_tests/test_baseline/gt/**`。
- **偏差 / review-ask（r2）**：none。四个已确认 MAJOR 出口、MINOR-1、R2-2 E2E lock 与 R2-6 均按返工单闭合；请主控按既定独立 gate 复跑。

---

## 返工 r3 · r2 复审的 2 MINOR + 3 NIT 收口 — DONE

> 施工席 · 2026-07-31 · 依据 [返工单 r3](../request/2026-07-31_isolation_scaffold_rework_r3.md)
> 基线 = **1908 passed / 10 xfailed / 0 failed**（主控已独立复核）

### R3-1 · MINOR-2 · 把自由文本参数按名枚举进豁免表（缺省仍 fail-closed）

**枚举依据（不靠猜，两侧取并集，逐条落进 `guard.py` 注释）**

- `isolation._write_settings` 的 `permissions.allow` 实际只放行
  `Read(<staging>/**)` / `Write(out|requests/**)` / `Edit(out|requests/**)` / `Bash`；
  `deny` 里是 `WebFetch` / `WebSearch` / `Agent` / `Task` / `mcp__*`。
  免权限的常驻工具（`Glob` / `Grep` / `TodoWrite`）不在 allow 表里但 hook 的 `"matcher": ""` 一样拦得到。
- 07-30 那轮 `access_log.jsonl`（attempt 003，82 条）实际出现的 `tool_name` =
  `Read` 37 / `Bash` 26 / `Write` 18 / `Edit` 1；日志只在 deny 条目记参数名，
  出现过的参数名 = `command` 与 `content`。该轮全部非 Bash 拒绝理由
  （`forbidden token: grade`、`home token is forbidden`）**都落在自由文本参数上，没有一条落在路径参数上**。

**落地**

- `CONTENT_ROLE_KEYS` 由 4 个文本体扩到 8 个：新增 `activeForm`（TodoWrite）、
  `description`（Bash / Agent）、`prompt`（Agent / WebFetch）、`query`（WebSearch）。
  收录判据 = **该名字在所有用到它的工具下都是自由文本**，所以豁免这个名字不可能让某个路径漏检。
- 新增 `TOOL_FREE_TEXT_KEYS = {"Grep": ("pattern",)}` = **按工具生效的豁免**。
  `pattern` 在 `Grep` 是正则（`wall_..[0-9]`、`z ~ 0.0`），在 `Glob` 是路径 glob（`**/gt.json` 必须继续拒），
  只按 key 名分不开这两者 ⇒ `_param_role(key, tool)` 增加 `tool` 参数。
  未登记的工具拿不到任何按工具豁免（仍 fail-closed）。
- `Bash` 的 `command` **不进任何豁免表**，仍走 `_check_bash` 全串严格检查（结构锁里显式钉住）。
- **缺省方向零改动**：`_param_role` 仍是「不在两张表里 ⇒ path 角色 ⇒ 无条件 `_lexical_check` + `_path_arg`」。

**新增锁**

- `test_guard_r3_free_text_params_of_non_write_tools_are_allowed`（3 参数）——可用性正例：
  `TodoWrite.activeForm`（禁词只放在 `activeForm`，`content` 保持无辜，锁才真绑新表项）、
  `Grep.pattern`、非 Bash 工具的 `description`，均含 `grade line` / `..` / `~` ⇒ **ALLOW**。
- `test_guard_r3_default_stays_fail_closed_after_free_text_exemptions`（5 参数）——负锁：
  未知 key 携带越界绝对路径 / 禁词 / `..`，`file_path="case_tests"`，
  以及 `Glob {"pattern": "**/gt.json"}` ⇒ 全部 **DENY**。
- `test_guard_r2_param_role_is_total_over_keys` 改造见 R3-3 ①。

**neuter 自查（全部在 `/tmp/.../scratchpad/neuter/repo` 的 `git clone` 副本上做）**

子集命令：`python -m pytest -q -n0 tests/test_isolation.py -k 'guard_r3 or param_role or guard_r2 or guard_r1 or security_properties'`，
基线 **30 passed**。

| # | 定点破坏 | 结果 | 实际变红测试名 |
|---|---|---|---|
| N0 | 不打破坏，直接把 **r2 的 HEAD `guard.py`（85b6695）** 换回来（= 本项修复前的生产码） | 4 failed, 26 passed | `test_guard_r2_param_role_is_total_over_keys`；`test_guard_r3_free_text_params_of_non_write_tools_are_allowed` 全 3 参数 |
| N1 | `CONTENT_ROLE_KEYS` 删掉 `"activeForm"` | 2 failed, 28 passed | `test_guard_r2_param_role_is_total_over_keys`；`…free_text_params…[todowrite_activeform-payload0]`（**只红这一格，Grep/description 两格保持绿 ⇒ 锁精确绑到该表项**）|
| N2 | `TOOL_FREE_TEXT_KEYS = {}` | 2 failed, 28 passed | `test_guard_r2_param_role_is_total_over_keys`；`…free_text_params…[grep_regex_pattern-payload1]` |
| N3 | 把 `"pattern"` 从按工具表挪进全局 `CONTENT_ROLE_KEYS`（即取消按工具作用域） | 2 failed, 28 passed | `test_guard_r2_param_role_is_total_over_keys`；`…default_stays_fail_closed…[glob_pattern_is_still_a_path-payload4]`（**证明按工具作用域是承重的、不是装饰**）|
| N4 | `_param_role` 恒 `return "content"` | 16 failed, 14 passed | R2-1 老锁 7 条（`bare_and_slashed…` ×2、`bare_extensionless_escaping_symlink…` ×2、`unknown_key_defaults_to_path_role` ×3）+ `param_role` 结构锁 + R3-1 新负锁全 5 格 + `security_properties_stay_denied[read_gt_json / read_case_tests / abs_outside]` |

N4 是 **R2-1 fail-closed 缺省未被本项削弱的活体证明**：缺省一旦被改成豁免，老负锁与新负锁同时红。

### R3-3 ① / ③ · 两条 NIT 随 R3-1 一起清

- **NIT-1**：`test_guard_r2_param_role_is_total_over_keys` 首条断言
  `{_param_role(k) for k in CONTENT_ROLE_KEYS} == {"content"}` 是同义反复（`_param_role` 的实现就是
  「在不在这个元组里」）⇒ 改成**逐字面量**断言 8 个豁免名 + `pattern` 的两种工具语义 +
  `command`/`file_path` 必须是 path 角色。现在从生产元组里删任一名字该测试就红（N1/N2/N3 实证）。
- **NIT-3**：`_write_targets` 返回 list、`evaluate()` 逐 target 循环，而 `len(present) > 1` 直接 raise
  ⇒ 多元素分支按构造不可达 ⇒ 改名 `_sole_write_target`，返回 `Path | None`，签名即结论；
  歧义拒绝规则原地不动。
  - neuter（子集 `-k 'ambiguous or write_target or denies_write or allows_write'`，基线 **23 passed**）：
    删掉 `len(present) > 1` 的 raise ⇒ **3 failed** =
    `test_guard_denies_ambiguous_multiple_write_targets` 全 3 参数（**R2-5 性质未被这次重构削弱**）；
    `_sole_write_target` 恒 `return None` ⇒ **20 failed**（写保护 12 条负锁 + 4 条正例 + 散文正例 + 歧义 3 条）。
- **NIT-2**（`__pycache__` 豁免不限深度）：r2 已授权，本轮**只登记**，
  在 `tests/test_isolation.py` 的 `_E2E_EXEMPT_PARTS` 处注明语义与为何可接受，零行为改动。

### R3-2 · MINOR-1 · 可写根语义抽成一处共享实现

**实现**

- `guard.py` 的 `_writable_root` 改名为**公开** `writable_root`（R2-3 钉死语义一字未改：
  必须是 staging 内的真实目录、非 symlink、`resolve(strict=True)` 等于自身字面路径）。
  guard 内三处调用（`_check_write_target` / `_assert_writable_roots` / `_check_output_target`）同步改名。
- `isolation_templates/run_cv_probe.py` 的 `_writable_root` **不再自带实现**，
  改为把 staging root 加进 `sys.path` 后 `from guard import writable_root` 并转调。
  ⇒ **全仓只有一个可写根实现**，不存在「照抄一遍再各自漂移」的第二份策略。
  `guard.py` 缺失/不可导入时 `ImportError` 直接冒出、wrapper 拒绝执行 = fail-closed。
- 顺手修一处会掩盖真因的写法：`_resolve_output` 把 `writable_root(...)` 调用移出 `try`，
  否则「可写根本身被换掉」会被 `except ValueError` 重贴成
  `output path must land under out/` 的错误标签。

**新增锁**：`test_wrapper_refuses_when_the_writable_root_is_a_symlink`
= 预置 `out -> tools` 正式 build → **绕过 hook 直调 `tools/run_cv_probe.py`** ⇒
受保护树零变化 + `tools/cv` 不存在 + 退出码非零 + 理由含 `real directory`。
断言顺序刻意把**树差分放在第一条**，回归时报出的是真实落盘清单而不是退出码。

**neuter 自查**（同一 `/tmp` 副本，子集
`-k 'wrapper or e2e_hook or run_cv_probe or output_dir or symlink'`，基线 **29 passed**）

| # | 定点破坏 | 结果 | 实际变红测试名 |
|---|---|---|---|
| N8 | wrapper 的 `_writable_root` 退回自带的 `(root / name).resolve(strict=False)`（= 本项修复前形状） | 1 failed, 28 passed | `test_wrapper_refuses_when_the_writable_root_is_a_symlink`，失败信息 = `assert ['added:tools/cv', … 共 6 项] == []` ⇒ **复审方 MINOR-1 的「真在 tools/** 下落了 6 个条目」被本锁逐条抓住** |
| N9 | wrapper 的 `_resolve_output` 退回普通 `_resolve`（R2-2b 复核） | 2 failed, 27 passed | `test_wrapper_independently_refuses_outside_output_and_tree_is_unchanged`；新锁 |
| N10 | **只破坏 guard 的 `writable_root`**（退回 `resolve(strict=False)`） | 4 failed, 25 passed | `test_wrapper_refuses_when_the_writable_root_is_a_symlink`；`test_guard_denies_writes_when_an_allowed_root_is_a_symlink[out]`、`[requests]`；`test_guard_denies_writes_when_allowed_root_symlinked_after_build` |

**N10 是「确实共享同一份实现」的判决性证据**：破坏 guard 一侧的定义，wrapper 侧的锁同时变红 ——
两个执行点走的是同一个函数对象，不是两份长得像的代码。

### r3 跑测、范围与交付

- **中间轮受影响子集（工具算，非手挑）**：

```text
python scripts/tool_scripts/affected_tests.py --changed \
    src/agent/execution/isolation_templates/guard.py \
    src/agent/execution/isolation_templates/run_cv_probe.py \
    tests/test_isolation.py
```

输出 `SCOPE: SUBSET` → `python -m pytest -p no:cacheprovider -q tests/test_isolation.py`；
实跑 **115 passed**（r2 尾态 106 → R3-1 新增 8 参数 + R3-2 新增 1 = 115）。

- **交付前全仓**：

```text
python -m pytest -q
```

结果 **1917 passed / 10 xfailed / 0 failed**（287.25s）。相对主控基线
`1908 passed / 10 xfailed / 0 failed` 净增 **+9**，零回归。

- ⚠️ **首次全仓跑抓到一条子集看不见的红**（如实登记，非事后修饰）：
  `tests/test_gt_discipline.py::test_executors_do_not_reference_gt` 变红，原因是我在
  `guard.py` 的 R3-1 注释里把答案文件名**逐字写了出来**（生产码本体一直用 `"gt" + ".json"` 拼接来规避）。
  已改写注释措辞，复跑全绿。**这条纪律门是词法扫描执行器源码文件，与 `guard.py` 之间没有 import 边也没有字符串路径边**，
  所以 `affected_tests.py` 结构上路由不到它 —— 登记为跟进债（见下）。

- **范围核**：

```text
git diff --quiet 85b6695..HEAD -- src/agent/judge case_tests/test_baseline/gt AI_agent/CLAUDE.md
```

退出码 **0**。受保护人签答案树逐字节未动：

```text
find case_tests/test_baseline/gt/sm24_anchor -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
e78c6e7e015746c14d8f70521551a71ee77b6e726259000ecf6133f91d61771f  -   （14 个文件）
```

与复审裁决书 §6 的基准值逐字相同。

- **r3 改动文件（4 个）**：`src/agent/execution/isolation_templates/guard.py`、
  `src/agent/execution/isolation_templates/run_cv_probe.py`、`tests/test_isolation.py`、本执行日志。
  **`scripts/tool_scripts/cv_probe.py` 无 r3 改动**（见下方偏差第 1 条）。
- 全部 neuter 只在 `/tmp/.../scratchpad/neuter/repo` 的 `git clone` 副本上做；主工作树未做任何实验性破坏，
  未写 `case_tests/test_baseline/gt/**`。

### 偏差 / review-ask（r3）

1. **返工单 R3-2 的文件指向有一处笔误**（不影响执行）：单里写「`scripts/tool_scripts/cv_probe.py` 侧
   （staging 内为 `tools/run_cv_probe.py`）的 `_writable_root`」。实际上
   `scripts/tool_scripts/cv_probe.py` 里**没有** `_writable_root`，它被拷成 staging 的 `tools/cv_probe.py`；
   带 `_writable_root` 的是 `src/agent/execution/isolation_templates/run_cv_probe.py`（拷成 `tools/run_cv_probe.py`），
   也正是复审裁决书 §4 MINOR-1 逐行引用的那个文件。**我改的是后者**，`scripts/tool_scripts/cv_probe.py` 一行未动。
2. **R3-1 的枚举依据，盘上实际能拿到的比骨架描述的窄** —— 如实登记，未自行改骨架：
   `access_log.jsonl` **只在 deny 条目记参数名**，那一轮出现过的参数名只有 `command` 与 `content`；
   `_write_settings` 的 allow 表只点名 `Read`/`Write`/`Edit`/`Bash` 四个工具、不列参数。
   ⇒ 单靠这两处**推不出** `activeForm` / `pattern` 这些名字，它们来自骨架自己给的显式最低清单
   与对应工具的参数表（也正是复审方活体探针实测被拒的那些形状）。两处依据我都据实写进了 `guard.py` 注释。
3. **判断取舍：`pattern` 做成按工具豁免，而不是全局豁免。** 骨架写的是「补进 `CONTENT_ROLE_KEYS`」，
   但 `Grep.pattern` 是正则、`Glob.pattern` 是路径 glob，同名不同义；全局豁免会让
   `Glob {"pattern": "**/<答案文件名>"}` 从 DENY 变 ALLOW ——
   那是复审裁决书 §1/§3.2 已验证的安全性质，属于「削弱既有断言」。
   故新增 `TOOL_FREE_TEXT_KEYS` 只对 `Grep` 生效，并补了 `glob_pattern_is_still_a_path` 负锁 + N3 neuter 钉住。
   **这是严格加强、不是放宽**，但确实偏离了骨架字面的「一张表」写法，请主控确认。
4. **共享实现的落法：让 wrapper 反向 import guard，而不是新起第三个共享模块。**
   理由 = 不必往 staging 多塞一个文件/多一条 MANIFEST 条目，且语义上「策略归守卫所有」更直白；
   代价 = wrapper 对 `guard.py` 有了硬依赖（缺失即 `ImportError` ⇒ 拒绝执行 ⇒ fail-closed）。
   若主控更希望是中立的第三方模块，这是一处可返工的形状选择。
5. **跟进债（不阻断，本轮未做）**：`test_gt_discipline` 这类**词法扫描生产码**的纪律门，
   与被扫文件之间没有 import/字符串路径边 ⇒ `affected_tests.py` 结构上算不进子集，
   只有全仓跑才会暴露。本轮已被它抓到一次真红。
6. **未纳入豁免表的残留自由文本参数**（刻意不做，避免超出骨架）：`ExitPlanMode.plan`、
   `Skill.args` 之类。这些工具不在 `_write_settings` 的 allow 表内、也未在 07-30 的 access log 出现，
   按「枚举依据不许靠猜」的要求就不该进表；将来若识图子代理真用到，会以 fail-closed 缺省被拒并在
   `access_log.jsonl` 留痕 ⇒ **复验轮读拒绝计数时可直接发现**。
