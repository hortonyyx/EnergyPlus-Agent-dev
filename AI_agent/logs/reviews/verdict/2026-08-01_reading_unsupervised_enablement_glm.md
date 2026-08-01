# 跨家族对抗审裁决书 · reading unsupervised enablement（W1 + W3 + W4 r1/r2）

- **日期**：2026-08-01
- **审阅席**：GLM-5.2（GLM 侧）
- **施工席**：GPT 侧 terra（谁写谁不批，跨家族）
- **性质**：验证性对抗审（每条命题写死「验什么 / 什么算不成立」）
- **范围**：`15cfcb8`(W1) · `0763164`(W3) · `2d2137e`(W4) · `3b7d930`(r1) · `2cb1f82`(r2)
- **基线**：全仓 2046 passed / 10 xfailed / 0 failed（主控独立复跑；本席独立复算见末尾）

**取证纪律**：所有破坏性探针（neuter / 篡改冻结件 / 构造反例）一律在 `/tmp` 副本或临时 staging 执行，工作树零改动、零 commit、零 push。证据均为真实命令输出，非推理。

---

## 逐条命题判定

### A 组（W1 · skill 文档）

| # | 判定 | 证据 |
|---|---|---|
| **A1** | **成立** | `session_kickoff.md:33-36` 把「Calibrate and measure before writing meter coordinates on clean vector CAD PNGs」列为 **Non-negotiables 清单的第一条**（"Do not memorize … the durable text lives in the rule docs"，强语气、非可选）；line 25 的 CV-tool bullet 也直接陈述。读者无需跳到别的文件才知道要做。 |
| **A2** | **成立（带 NIT 级注记）** | `cv_toolbox.md:3` 与 `:61` 确有该例外文本（"On noisy scans, hand drawings, or other degraded inputs, defer the required/optional judgment until a robustness profile exists"）—— **非悬空引用**。且 line 3 明确 clean vector CAD **必须**先用工具箱，例外只对降质输入 ⇒ 不存在「让读者对干净矢量 CAD 也免测」的失效模式。**注记**：该「档位」当前形态是「暂缓判断、profile 尚不存在」，更像 deferral 而非完整档位；但指针落地、出口真实，命题成立。 |
| **A3** | **成立** | `git show 15cfcb8` 全文仅出现泛化词（clean vector CAD PNGs / dimension-chain extension-line intersections or ticks / noisy scans / degraded inputs）。零 case 名、零尺寸、零坐标、零期望数量、零「上轮错在哪」。 |
| **A4** | **成立** | `15cfcb8` 仅改动 1 行 bullet（line 25）+ 新增 1 条 Non-negotiable（line 33-36），未触碰本项之外的任何规则句。（kickoff 的 Workflow 段另有未跟踪改动，属 `95ba3dc` 的去污染修，非本批 W1、已被排除在 staged diff 外——执行日志如实说明。） |

### B 组（W3 · guard.py · 命脉 = 零扩权）

> 探针在 `/tmp/glm_guard_probe`（真实 guard.py + 完整 staging 结构）实跑。

| # | 判定 | 证据（真实命令输出） |
|---|---|---|
| **B1** | **成立**（PROBE_TOOL_NAMES **不是**授权表） | 直接证伪尝试：`--tool evil_tool`（既不在 PROBE_TOOL_NAMES 也不在 wrapper ALLOWED_TOOLS）⇒ **guard 仍 exit=0 ALLOW**。证明 guard 的 allow/deny 不依赖 PROBE_TOOL_NAMES 成员资格——它只塑形 bare-arg 的 hint 文案。真正授权 = wrapper 的 `ALLOWED_TOOLS`：`python tools/run_cv_probe.py --tool evil_tool ...` ⇒ wrapper **exit=1 拒绝**。即「加进 PROBE_TOOL_NAMES 就能跑」不成立。 |
| **B2** | **成立**（--help 恰为精确三 token 形式） | 精确形式 `python tools/run_cv_probe.py --help` ⇒ ALLOW。邻近变体全部 DENY：`--help --tool x`（"unknown probe parameter --help"）、`--HELP`（同）、bare `help`（"unexpected bare argument"）、`--request --help`（"request must be a JSON file"）。唯一「放行」的是空白折叠后的等价命令（shlex 归一），逻辑同形。 |
| **B3** | **成立**（mkdir/find 仍被拒） | `mkdir out/sub` ⇒ DENY "command is not allowlisted: mkdir; out/ and requests/ are already provisioned…"；`find case_data -name x` ⇒ DENY "…use ls case_data…"；`ls case_data` ⇒ ALLOW（被点名的合规替代步骤确实放行）。 |
| **B4** | **成立（带 NIT）** | `_BATCH_TEMPLATE` 含 `px_a:100 / px_b:700 / value_m:15.0 / dimension_ref:"overall_width"`。核验目标 case：**sm24 gt.json 无 "overall_width"、无 15.0、[14.5,15.5] 区间无数值、无 width 键** ⇒ **不喂 sm24 答案**。15.0m/overall_width 实为**worked-example 楼（smalloffice_20）**的真实宽度（其墙坐标 0→15m，reader 经 style-anchor 合法可见），模板只是借用该楼的宽度做语法样例。**NIT**：建议改用显式占位值（如 `value_m:12.345 / "example_span"`），以免与未来某目标 case 偶然撞数。 |
| **B5** | **成立**（新锁皆真） | 逐条 neuter（在 `/tmp/glm_repo`）每条新守卫 ⇒ 各自目标测试红、零假锁：help 分支 neuter→`test_probe_help_is_allowlisted…` 红；`_BATCH_TEMPLATE` 清空→`test_guard_probe_shape_receipts…` 红（2/3 参数化）；缺值 hint neuter→`test_guard_missing_direct_value…` 红；shell denial next-step neuter→`test_guard_real_shell_denials…` 红。无「摘掉守卫仍全绿」。 |
| **B6** | **成立** | 所有新错误串均为**形式指引**：「names go after --tool」「write --{spelling} <value>」「remove the pipe and rerun…directly」「use ls case_data」「write requests/<name>.json」。模板用占位 `<image>`。无任何「量哪里 / 几道墙 / 上次漏了什么」内容指引。（`_BATCH_TEMPLATE` 的 15.0/overall_width 见 B4，属语法样例数值非内容指引。） |

### C 组（W4 + r1/r2）

> resolver/neuter 探针在 `/tmp/glm_repo`；篡改/反例在 `/tmp` 临时 case 副本。

| # | 判定 | 证据 |
|---|---|---|
| **C1** | **成立**（开考前定死、考中不可变更被强制） | 直接构造六种考后改法，`resolve_frozen_reading_exam_scope` **逐一 raise**：改 `input_ids`→"does not match the current declaration"；改 `reason`→同；删声明→"has no reading_exam_scope declaration"；删冻结件→"frozen scope artifact is missing"；损坏冻结件→"is corrupt"；换绑另一份 base manifest→"bound to a different base view manifest"。无一条能照常出分。 |
| **C2** | **成立**（六道守卫各摘即红、零连带） | 六道 resolver/consumer 守卫逐道 neuter：G1 removed-decl→`test_frozen_exam_scope_resolver_rejects_removed_declaration` 红（1 failed 60 passed）；G2 missing-frozen→`…requires_matching_declaration_and_base` 红；G3 corrupt→`…rejects_corrupt_frozen_artifact` 红；G4 other-base→`…rejects_other_base_manifest` 红；G5 content-drift→`test_run_level_exam_scope_is_frozen…` 红；G6 consumer narrowing（run_stage.py:1409）→`test_typed_reading_scorer_consumes_only_frozen_exam_scope_bindings` 红，且 `select_score_view_bindings` 单元测试仍绿（锁绑的是 wiring 不是函数）。每次恰好红 1 条、零连带、零假锁。 |
| **C3** | **成立**（r2 删 declaration_sha256 比较是安全的——**证伪失败**） | 命题要求构造「declaration_sha256 不等而 content_sha256 相等」。两种篡改尝试**均被挡**：(A) 仅改 on-disk declaration_sha256、留 stale content ⇒ 加载期 `model_validator` 重算 content_sha256 不符 ⇒ 判 corrupt（G3）；(B) 改 declaration_sha256 并重算 content_sha256 使对象自洽 ⇒ 该 content 与 declared（由 run_config.yaml 重建）的 content 不符 ⇒ G5 挡。因 content_sha256 覆盖 declaration_sha256 字段且模型层强制自洽，二者**结构上不可分**。**无法构造反例，删除安全。** |
| **C4** | **成立**（未声明 = 逐字不变） | 临时 case 副本不声明 scope：`provision` 不写 `_run/reading_exam_scope.json`（exists=False）；manifest content_sha256 与未声明前一致；`verify_view_manifest.ok=True`、`exam_scope is None`；`resolve_frozen_reading_exam_scope→None`；`derive_input_inventory(manifest, None)` 含**全部** required view（无收窄）。 |
| **C5** | **成立**（签名件不动） | `select_score_view_bindings(input_ids={1f,South})` 在真实 sm24 bindings 上实跑：产物为 2 条（源 5 条）的**内存子集**，源文件 `judge_score_bindings.json` 字节 **before==after 完全相同**（无任何回写）。`score_inputs.py` 全文零文件写。 |
| **C6** | **成立**（范围外=显式缺席；范围内缺产物仍 BLOCK） | `check_view_manifest_coverage`：范围外 view 记 `NOT_APPLICABLE` + `evidence.source=run_config.yaml:reading_exam_scope`（显式声明的缺席，非静默跳过）；`missing = expected(收窄后) - produced` ⇒ `add_fail`（INVARIANT，BLOCK）。`test_formal_scope_stages_only_declared_images…` 活体印证：缺 in-scope South_view ⇒ coverage fail `missing=[South_view]`；East/North/West 记 not_applicable。 |
| **C7** | **成立**（声明不携答案） | schema 仅 `input_ids + reason`。`reason` 仅存于冻结件、**不进** input_inventory（只 input_id/file/view_type/dir_token/floor_ref/expected_output_id）、不进 kickoff、不进 staging（`_run/` 不被 `_copy_*`）。计分路径（`select_score_view_bindings`/coverage）只消费 `input_ids`/`base_view_manifest_sha256`/`source`，**`reason` 零数值参与**。 |
| **C8** | **成立**（三个身份哈希逐字不变） | 本席独立重算 sm24：`case_metadata_sha256=f2efff86…` ✓、`base_view_manifest_sha256=459513f1…` ✓、`gt_content_sha256=dd32135d…` ✓ —— 与执行日志所载**逐位相同**。 |
| **C9** | **成立**（判卷侧不依赖固定 case 布局） | `_grade_typed_attempt_artifacts` 计分体（run_stage.py:1324-1430）grep `case_tests/e2e_tests` 命中=0；输入路径全部 `run_dir/_run/…`（base/bindings/overlay）+ `resolve_frozen_reading_exam_scope(run_dir, base)`。`--base-dir` 实跑：向仓库外 `/tmp/c9bd_*` provision sm24 ⇒ 成功、manifest 写入该处、content_sha256=459513f1… 正确。**注**：`gt_path(case)` 默认指向仓库 `case_tests/test_baseline/gt`（可 `gt_dir=` 覆盖）——这是 judge-only gt 信任根的既有设计、非 r1 所修的「case 布局」依赖，不计为命题失效。 |
| **C10** | **成立**（跟进债属实、未更严重） | 独立核读：`_stage_advance_ready`（run_stage.py:1588）对已 accepted 的 stage 返回 True ⇒ `_auto_start_stage` 跳过该 stage ⇒ `_draw_reading` 不调 ⇒ 其内 `provision_view_manifest`（:183）不执行 ⇒ 该路径的 on-disk-vs-rebuilt 漂移门（view_manifest.py:1044-1049）不经过。漂移门仍由 `_ensure_run_identity`（:155）、`cmd_judge` 的 `verify_view_manifest(case_dir,run_dir)`（:1870）、isolation build/merge 承担。声称的可达性准确，未发现比声称更广的常用路径缺口。 |

---

## 清单外自主发现（Section 4）

### Finding S-1（MINOR · 假锁）— merge-time exam-scope 漂移门无 neuter-red 锁

- **位置**：`src/agent/execution/isolation.py:340-343`
  `if binding.get("reading_exam_scope_sha256") != (verification.exam_scope.content_sha256 if verification.exam_scope else None): raise ValueError("merge refused: the reading exam scope changed…")`
- **形状**：**门是真的、锁是缺的**（正是本批治理教训「探针≠锁 / 门真锁缺」的同一族）。该守卫由 W4 `2d2137e` 引入（`git show 2d2137e -- isolation.py` 确认 `+` 行）。
- **复现**（`/tmp/glm_repo`）：neuter 该 raise ⇒ `tests/test_isolation.py -k "merge or scope or formal"` **20 passed, 0 failed**——无任何测试变红。`test_formal_scope_stages_only_declared_images…` 只断言 binding **记录**了 scope sha（:558），未断言**改了会被拒**。
- **影响边界（为何只评 MINOR 而非更高）**：该门是**纵深防御**——(a) 实际的 scope 不可变更性已由 6 道 resolver 守卫（C2 全部 neuter-red 锁定）保证；(b) `binding.json` 位于 staging **根**（不在 `out/`|`requests/`），reader 写保护下不可改；(c) merge 的 coverage 检查用当前已验证的 frozen scope。故单独移除该门的可达成危害被上游已测守卫 + 写保护包住。但按本批自定的「每条新守卫必须有摘掉即红的锁」标准，这是一个应补锁的一致性缺口。
- **建议出口**：补一条 `test_merge_rejects_reading_exam_scope_changed_since_build`（build 后、merge 前篡改 run 的 frozen scope 或换 base → 断言 raise "reading exam scope changed"），并 neuter 验真。

### NIT-1（B4 卫生）— `_BATCH_TEMPLATE` 用真实楼宽做语法样例
见 B4。建议模板改用显式占位数值，避免与未来目标 case 偶然撞数。非污染（目标 sm24 无此值，且 worked-example 楼宽 reader 本就可见）。

### 未发现的项目
- **白名单换皮**：除已验的 `PROBE_TOOL_NAMES`（B1，非授权表）外，未发现其他「不是授权表却决定行为」的集合。`PROBE_DIRECT_PARAM_KEYS` 是 fail-closed 允许列（未知 key 即拒，派工单背书此设计）；`CONTENT_ROLE_KEYS`/`TOOL_FREE_TEXT_KEYS` 是把命名自由文本参数免扫描（R3-1 设计），默认仍 path-role 扫描，非授权换皮。
- **假绿（让错答案过门）**：未发现。scope 子集消费 + coverage BLOCK + 三哈希绑定构成闭合。

---

## 测试基线独立复算

- **W4/W3 受影响子集**（`/tmp/glm_repo`，4 文件）：`test_view_manifest_generator.py` + `test_isolation.py` + `test_reading_typed_scoring_slice1.py` + `test_c2_b4b_phase_d.py` ⇒ **280 passed / 1 failed**；唯一红 = `test_d5_va_…_judge_modules_stay_judge_only`，失败原因是 `/tmp` 副本**无 `.git`** 致其 `git diff` 退出 129 —— **环境假红、与 W4/W3 无关**（真实工作树该测试为绿）。
- **W4 resolver+consumer 锁子集**：`test_view_manifest_generator.py` + `test_reading_typed_scoring_slice1.py` ⇒ 61 passed。
- **全仓**：见末尾附注（独立复跑）。

---

## 总裁决

# **APPROVE-WITH-CHANGES**

- **命题**：A 组 4/4、B 组 6/6、C 组 10/10 **全部成立**（含两条要求证伪的承重命题 B1、C3——本席主动证伪均失败，反向坐实）。
- **finding 计数**：**0 BLOCKER / 0 MAJOR / 1 MINOR（S-1）/ 1 NIT（NIT-1）**。
- **最重一条**：S-1——W4 引入的 merge-time exam-scope 漂移门（isolation.py:340）无 neuter-red 锁，是本批治理教训「门真锁缺」的漏网之鱼；影响被上游已测 resolver 守卫 + 写保护包住，故 MINOR，建议补一条 merge-拒绝锁。
- **次重**：NIT-1——`_BATCH_TEMPLATE` 用 worked-example 楼的真实宽度 15.0m 做语法样例（非目标 case 泄题，但建议换占位值）。

施工方两轮（W4 原 + r1 修缺陷 + r2 补锁）的质量**经独立破坏性验证站得住**：六道 scope 守卫全锁真、声明哈希删除经证伪坐实安全、三身份哈希逐位复算吻合、零扩权成立。唯一漏点是同批自定锁标准在 merge 门上未贯彻到底——补一锁即闭。

---

### 附：全仓独立复跑

本席在**真实工作树**只读复跑（`python -m pytest -p no:cacheprovider -q -n auto`，零改动零 commit）：

```
2046 passed, 10 xfailed, 150 warnings in 310.81s (0:05:10)
```

**与主控基线 2046/10/0 逐字一致**（W3 参数化回执锁 + W4 scope 锁相对先前 2028 基线新增 18 绿，零红）。
