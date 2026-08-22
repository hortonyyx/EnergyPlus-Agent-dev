# 跨家族复核裁决 · 判卷路径三缺陷修复（2026-08-22）

**审阅席位**：GLM（glm-5.3）· **施工**：`19932a2`（父 `2156989`）· **规约**：谁写谁不批
**方法声明**：只看 §一原始需求 + diff + 测试输出 + 我自己的实测。**所有 neuter 与端到端全部在一次性
`git worktree`（`/tmp/epx_glm_A_2156989` @2156989、`/tmp/epx_glm_B_19932a2` @19932a2）里做，用完即删；
主树 `scripts/ src/ tests/` 全程零接触**（收尾核验：`git status --short -- scripts/ src/ tests/` 为空）。
这比「就地改完改回」更强：不存在改不回来 / 中断留脏的风险，worktree 内容与提交逐字节一致，验证等价。

**溯源记录**（per run-provenance 纪律）：审阅期间主树被并行席位推进到 `8f9f5d4`（19932a2 的直接子提交，
`git diff 19932a2..8f9f5d4 --stat -- scripts/ src/ tests/` 为空）；主树 case_tests 下有并行席位未跟踪 WIP
（sm25 run 的 North/South/West view 等）。全量在主树带着这些 WIP 跑出 2994 绿，与声称一致。

---

## 裁决：**APPROVE**

0 BLOCKER · 1 MAJOR · 5 MINOR。三修法本身（F-74/F-75/F-76）全部独立证实成立；端到端、全量、neuter
三件实测全部通过。MAJOR 是锁覆盖缺口（validation_run.py 那条接线无锁），不阻塞本提交，建议下一批补一把锁。

---

## 一、原始需求三前提 —— 逐条独立复现（不是转述施工方）

| # | 前提 | 实测 | 输出 |
|---|---|---|---|
| 1 | flat-flow 合法声明 scope 仍必然 BLOCK | 读 2156989 已提交产物 | `attempts/001/checks.json`：`reading.view_manifest_coverage = fail`，`missing_expected_output_ids: ['East_view','North_view','South_view','West_view']` —— 冻结范围只考 1f/2f，仍按全部六张图要求 |
| 2 | 权威 typed 层静默跳过 | 读 2156989 已提交产物 | `attempts/001/score_vs_gt.json`：`payload.kind = not_applicable`，`reason = unsupported_reading_contract` |
| 3 | legacy 判卷器报误导性 floor 提示 | worktree A 实跑 | `python scripts/tool_scripts/score_reading_vs_gt.py …/1f_view.json --case sm25-L_anchor --floor F1` → **已经传了 `--floor F1` 仍输出** `could not map image to a gt floor; pass --floor`（exit 2）——提示纯噪音，真因被吞 |

施工后同命令（worktree B）输出：`legacy reading scorer refused this input: gt_v3_requires_typed_consumer at /schema_version` —— F-76 修复前后行为对照实测成立。

## 二、三件必测（§四）

### 1. neuter 实测 —— 四组，全部在 worktree B

**基线**：七把新锁在未动树上 7/7 绿（命令：按 node id 逐一指定，`pytest -q -p no:cacheprovider`）。

**Neuter A（摘 F-74 接线）**：`run_stage.py:_draw_reading` 里 `exam_scope=exam_scope` 改为 `exam_scope=None`。
```
FAILED tests/test_run_stage_flow.py::test_flat_flow_gate1_honours_the_frozen_reading_exam_scope
1 failed, 1 passed in 5.70s     # 失败信息: missing_expected_output_ids: ['2f_view']
```
→ 前向锁红 ✅；反向锁绿（它管另一种失败模式，见 Neuter C）。

**Neuter B（摘 F-75 接线）**：删除 `_grade_typed_attempt_artifacts` 里 `if stage == "0_reading": output = _as_reading_views_envelope(output)` 三行。
```
FAILED tests/test_reading_typed_score_integration.py::test_flat_layout_of_the_same_reading_scores_identically
1 failed, 2 passed in 7.57s     # 断言差: - c2_scored  + not_applicable
```
→ **重写后的锁确实咬住接线** ✅（同一 run 里两个 helper 级测试仍绿——正是第一版锁漏接线的那两个，证明新锁与 helper 锁分工正确）。施工方在这里犯过的错（只测 helper、摘接线全绿）已被其重写修掉，我独立复核属实。

**Neuter C（§三.3 专项：模拟「范围把检查关掉」）**：`check_view_manifest_coverage` 里 scoped 分支改 `expected = {}`（范围一声明 → 检查空转）。
```
FAILED test_flat_flow_still_blocks_a_view_missing_from_inside_the_declared_scope
FAILED test_flat_flow_gate1_honours_the_frozen_reading_exam_scope
2 failed in 6.03s
```
→ 反向锁红 ✅（其专职失败模式）。三态区分表（实测）：

| 状态 | 前向锁 | 反向锁 |
|---|---|---|
| 不传 scope（=施工前 / Neuter A） | 🔴 | 🟢 |
| 正确缩小（19932a2） | 🟢 | 🟢 |
| 缩小变关闭（Neuter C） | 🔴 | 🔴 |

→ **该锁对能分开「缩小」与「关掉」**；「不传」由前向锁兜住。锁对（两把合起来）充分。

**Neuter D（validation_run.py 的 F-74 接线）**：`validate_case` 改传 `exam_scope=None`，跑
`tests/test_validation_run_baseline.py tests/test_check_parity.py tests/test_run_stage_flow.py`：
```
1 failed, 51 passed, 8 xfailed    # 唯一红 = test_downstream_only_scope_skips_geometry
```
对照实验：该测试在**恢复后**的 worktree B、以及**父提交 2156989** 上单跑同样红
（`IntakeOutput invalid: 'ModelPrivateAttr' object has no attribute 'Building'`，根因 = `data_model.py:191`
依赖 `set_idf` 全局初始化，单跑时未初始化；与本案 diff 无关的预存顺序依赖，全量里绿）。
⇒ **摘掉 validation_run.py 的接线，没有任何锁变红** → MAJOR-1。

### 2. 全量（主树独立跑）

```
python -m pytest -q -n auto
→ 2994 passed, 13 xfailed, 212 warnings in 837.67s (0:13:57)   exit=0
```
与声称 `2994 passed / 13 xfailed` **逐字对账一致** ✅。

### 3. 端到端（worktree B = 纯净 19932a2，避开并行席位在主树的未跟踪 WIP）

```
python scripts/tool_scripts/run_stage.py --base-dir case_tests/e2e_tests \
  flow sm25-L_anchor run_2026-08-22_orchestrator_handson_H1 --to 0_reading --judge stop
→ [0_reading] awaiting_judge (attempts=1, accepted=1)
   gate①: {'passed': True, 'block': 0, 'flag': 4}
```
`attempts/001/score_vs_gt.json`：`payload.kind == "c2_scored"` ✅
且 §三.1 的身份绑定实测：sidecar `output_sha256 = 139a94ca…87401` **== sha256(output.json 原始字节)**，
而该 output.json 是 flat 形态（顶层键 = `['1f_view','2f_view']`，无 `views` 包装）——包裹只发生在内存呈现层。

## 三、§三五条证伪 —— 逐条结论

### 1. F-75 会不会洗白错产物？—— **不会（证伪成立），实测+代码双重证实**

- 代码链：`output_text` 先读文件（run_stage.py:2074）→ 包裹只改内存对象（:2080）→ `output_hash = hash_text(output_text)`（:2092）取**文件字节**；accepted 记录比对（:2093-2099）同样对文件字节；typed 侧 `normalize_reading_attempt` 收到的 `source_output_sha256 = product_identity.output_sha256`（reading_typed_score.py:1127-1131）= 文件字节。
- 端到端实测：flat 文件判成 `c2_scored` 且身份哈希 == 文件字节哈希（见 §二.3）。
- **对抗探针**（`_grade_payload` harness，worktree B）：
  - 垃圾 flat（`{"1f_view":{"nonsense":…},"2f_view":{"zzz":{}}}`）→ `c2_scored`，判卷结果 `walls_complete: 0.0/57.86 verdict=fail`、`boundary_complete: 0.0/60.0 fail` —— **诚实零分，不是被洗成通过**。判分从来不是放行门（放行在 gate①+judge），包裹去掉的只是「拒收」，判卷该多差还是多差。
  - 空 `{}` → 仍 `not_applicable/unsupported_reading_contract`（F-64「零产物不红」没有被重新引进）。
  - 带标量字段产物（`{"schema_version":"3",…}`）→ 仍被拒收（不满足全-dict 条件，不误包）。
  - 视图键越界（产物含 manifest 外的键）→ adapter 记 `unbound_reading_view` finding（reading_typed_adapter.py:1136-1142），可见不静默。
- 「不该被判分的产物因此被判分」的路径：不存在。唯一行为变化 = 以前被拒收的 flat 形态现在被**照实判低分**，与同内容的 envelope 形态行为对称（修复前 envelope 垃圾也照样被判）。

### 2. 包裹条件是否过宽、误伤非 reading 产物？—— **不误伤：结构性收口在调用点**

- `_as_reading_views_envelope` 全仓**唯一**生产调用点 = run_stage.py:2080，且前置 `if stage == "0_reading"`。
- 该 seam（`_grade_typed_attempt_artifacts`）的 stage 论域只有 `{0_reading, 1_correction}`（:2198 `if stage not in {"0_reading","1_correction"}: return {}` 与 `_judge_packet` 路径）；1_correction 被 stage 门排除。
- flat 键 = `*_view.json` 的 stem（必以 `_view` 结尾）⇒ **永不可能与 envelope 的 `views` 键碰撞**、不可能被误识别为已包裹形态。
- 条件本身（非空 dict 且全 value 为 dict）比渲染侧 `_extract_reading_views` 的 flat 分支（过滤非 dict）**更窄**：混入任何标量键的产物不包、照旧拒收。
- MINOR-4：这份收口住在调用点的 stage 门里，helper 自身对任意 dict-of-dicts 都会包；其 docstring「Non-reading … payloads are returned unchanged」的承诺只在当前调用语境下为真。若未来第二处调用出现，须自带 stage 判据。

### 3. F-74 反向锁能否分开「缩小」与「关掉」？—— **能**（Neuter C 实测，见 §二.1 状态表）

反向锁单独不抓「接线被删」（Neuter A 下它绿）——但那是前向锁的职责，两把都在。三态两两可分，锁对充分。

### 4. `check_view_manifest_merge` 零调用者 ⇒ 第三条入口？—— **该函数不存在（幽灵名），且无未修入口**

- 全仓 grep（src/scripts/tests，含 git 全历史 `-S`）：`check_view_manifest_merge` **只出现在文档里**
  （`tool_gaps.md:34`、`plan.md:157`，即施工方自己的缺口登记），代码中从来没有过这个函数。
- 真正的「merge 同门」检查器是 `check_reading_stage`（其 docstring 自称 merge 同门，view_manifest.py:43）。
  完整入口枚举（生产调用者）：
  - `check_reading_stage` ← `isolation.py:823`（隔离壳 merge 路径，**修复前就已传** `exam_scope=verification.exam_scope`）+ `run_stage.py:399`（F-74 ✅）
  - `check_view_manifest_coverage` ← `check_reading_stage` 内部 + `validation_run.py:329`（F-74 ✅）
  ⇒ **不存在第三条没传范围的入口**。§三.4 的前提「施工方发现但未处理」本身不成立——没有这个函数可供「零调用」。
- 遗留：plan.md/tool_gaps.md 仍在引用一个不存在的函数名 → MINOR-1（文档债：下一个照名字 grep 的人会空手而归）。

### 5. F-76 的 `str(exc) == "floor mapping"` 字符串判据 —— **可接受**（MINOR-3，附改进建议）

- raise 点（score_reading_vs_gt.py:156 `raise ValueError("floor mapping")`）与 catch 点（:172）**同文件相距 17 行**，raise 全仓唯一。
- 漂移时的退化形态：真消息仍按原样打印（`legacy reading scorer refused this input: <真因>`），只丢 `--floor` 提示——**降级不误诊**。修复前的行为（一切 ValueError 都翻译成 floor 提示）才是真 bug。
- 建议非阻塞改进：模块级 `class _FloorMappingNeeded(ValueError)` 哨兵异常，同样小的改动、不钉字符串。按 §0 P0 口径不强制。

## 四、Findings

### MAJOR-1 · validation_run.py 的 F-74 接线无锁（建议下一批补，不阻塞）
- 事实：施工方给 run_stage 路径配了锁对，但同一修复在 `validation_run.py:309-336` 的第二条接线**没有任何锁**。
  Neuter D 实测：摘掉它，`test_validation_run_baseline / test_check_parity / test_run_stage_flow` 共 52 例无一因它变红
  （唯一红是预存无关失败，见 §二.1）。
- 为何算 MAJOR：这正是本项目「已经真咬过人的坑」形状——F-74 本身就是这条接线漏传造成的；未来重构可再静默丢参而无测试报警。`validate_case` 是活入口（`step_orchestrator.py:486,507` 几何确认、`record_baseline.py:564`）。
- 建议：给 `_scoped_run` 夹具加一条 validate_case 级用例（scope 声明 + 只产范围内视图 ⇒ `vm_rep` coverage PASS；反向同 run_stage 锁）。一把锁的量。

### MINOR-1 · plan.md:157 / tool_gaps.md:34 引用不存在的函数 `check_view_manifest_merge`
文档登记应改为实际结论（merge 路径 = `check_reading_stage` @ isolation.py:823，已传 scope；无第三入口）。

### MINOR-2 · F-76 锁依赖 sm25 run 产物、缺产物时静默 skip
`test_v3_gt_refusal_…` 读 `case_tests/.../1f_view.json`，不存在即 `pytest.skip`。当前主树有该产物（已跟踪）锁是活的；
但 run 目录将来重组时这把锁**无声蒸发**（skip 不红）。建议改用测试夹具自造一份 v3 gt + view（或至少断言产物存在的原因写进 skip 文案）。

### MINOR-3 · F-76 字符串判据（§三.5 结论：可接受，建议哨兵异常，非阻塞）

### MINOR-4 · `_as_reading_views_envelope` 的收口住在调用点、helper 文档承诺略宽（§三.2 结论段）

### MINOR-5 · sidecar `identity.product.output_schema = "reading_views_v2"` 而磁盘文件是 flat
该字段语义 = 「按哪份判卷契约判的」，身份哈希仍指向 flat 原文件字节，可审计；但未来若有人拿 sidecar 的
schema 标签去反推文件字节形态会对不上。建议在 F-75 注释或 harness 文档里写明这层语义（一行的事）。

### 观察登记（本案范围外，附实测证据）
- **预存顺序依赖测试**：`test_downstream_only_scope_skips_geometry` 单跑/本文件内跑在 **2156989 与 19932a2 都红**
  （`IntakeOutput invalid: 'ModelPrivateAttr' … Building`，根因 `data_model.py:191` 的 `_idf_field` 依赖
  `set_idf` 全局初始化），全量里因跨文件初始化而绿。与本案 diff 无关，建议登记（「全仓绿」是树+启动器的属性的又一例）。
- 审阅期间并行席位在主树同 run 目录留有未跟踪 WIP（North/South/West view 等）——若在主树直接重跑端到端，
  gate① 会因 scope 外产物判 extra 而 BLOCK；我在隔离 worktree 验证，未受影响。两席位合流时需注意。

## 五、neuter 改动对账（我改了什么 · 全部在一次性 worktree，已随 worktree 一并销毁）

| # | 文件（worktree B 内） | 改动 | 跑了什么 | 输出 | 恢复方式 |
|---|---|---|---|---|---|
| A | `run_stage.py` `_draw_reading` | `exam_scope=exam_scope` → `exam_scope=None` | F-74 两锁 | 前向红/反向绿 | `git checkout --` 后复跑全绿 |
| B | `run_stage.py` `_grade_typed_attempt_artifacts` | 删 F-75 三行包裹调用 | F-75 三锁 | 重写锁红（c2_scored→not_applicable）、helper 锁绿 | 同上 |
| C | `src/validator/checks/view_manifest.py` | scoped 分支 `expected={}`（模拟关掉） | F-74 两锁 | 双红 | 同上 |
| D | `src/agent/execution/validation_run.py` | `exam_scope=None` 硬编码 | 三个相关测试文件 | 无锁变红（唯一红为预存无关失败） | 同上 |

主树 `scripts/ src/ tests/` 零改动（`git status --short -- scripts/ src/ tests/` 空；两 worktree 已 `git worktree remove`）。
