# GLM 交叉对抗审报告 — 2026-07-20 批施工产物

- **审阅者**: GLM（第三方交叉审阅者，独立于施工家族）
- **审阅对象**: 工作区未提交改动（`git diff` 9 文件 + 新增 `tests/test_audit_remediation_accepted_inputs.py`）
- **需求来源**: `REVIEW_DISPATCH.md`（7 条 finding + 每条测试要求 + §9 审阅重点）
- **基线**: `ddf6b23`；全量 **1452 passed, 9 xfailed**（审前=审后，零回归）

---

## 总裁决：**APPROVE**

7 条 finding **全部真正闭合**。每一条新负锁都做了活体 neuter 探针，确认「改坏目标门 → 对应测试红、且只红对应测试」——**未发现任何 false-lock**。未引入 BLOCKER / MAJOR 级新缺陷，未改动任何算法本体或 golden，零回归，探针后工作树指纹与审前逐字节一致（零残留）。

下方列出 **3 条 MINOR + 4 条 NIT**，均为加固建议，不构成退回理由。

---

## 审阅方法（可复现）

对每条新增「锁」执行两步活体验真，全程**手动改回**（未用任何 git 回滚）：

1. **活体探针**：写脚本跑真实调用路径（非手搓复刻），观察真实行为。
2. **neuter 探针**：把锁声称守护的那条生产码约定改坏，确认对应测试红、且只红它（无连带）。

探针后用 `diff <(git diff) baseline.diff` 验指纹回归，确认零残留（见末尾「操作纪律」）。

| Finding | 活体探针 | neuter 探针（改坏 → 红的测试） | 连带 |
|---|---|---|---|
| F1-1 | — | 去 b5 契约 → `test_b5_orientation_enrichment_is_idempotent_on_reentry` 红 | 无 |
| F2-1 | `/tmp/probe_f21_legit.py`（合法多视图路径不误伤） | neuter 守卫 → 3 条 F2-1 锁红 | **全量 0 连带** |
| F2-2 | — | A: 还原读 accepted→2 条 mep 锁红（全量 0 连带）；B: 去输入哈希→仅绑定锁红 | 无 |
| F5-1 | — | schema 层→schema 锁红（envelope 锁仍绿）；envelope 层→envelope 锁红（schema 锁仍绿） | 无跨层连带 |
| F4-1 | — | A: 还原静默→4 条 warn/fail 锁红；B: 关掉「无 v3 GT 静默」门→仅 silent 锁红 | 无 |
| F1-2 | — | cmd_flow 还原→「yaml 覆盖」参数化红 | 无 |
| B4b | `/tmp/probe_b4b.py`（实跑产真 grade） | 去 window_host_proof 接线→e2e 红（ScoreContractError fail-closed） | 无 |

---

## 逐条 finding 验证

### F1-1 [MAJOR] B5 orientation 再入守卫 — ✅ 闭合

- **代码** `scripts/tool_scripts/run_stage.py:458-461`：早退守卫现在同时认 `correction_e4_orientation_v1` 与 `correction_b5_orientation_v1`。
- **对照核验** `src/agent/output_coordinates.py:165-168`：`relative_north_axis` 契约本体确实两个 orientation 契约都认。守卫与出口契约本体一致——改的只是漏掉的 run_stage 守卫，无越界。
- **neuter**：把元组改回只含 e4 → `test_b5_orientation_enrichment_is_idempotent_on_reentry` 红（重入 `resolve_orientation_from_run_dir` → `must_not_enrich` AssertionError）。
- → 锁真绑在 b5 契约早退门上。

> **NIT-1**（F1-1 测试深度）：该回归测试用 `SimpleNamespace` mock 了 `verified`，未走真实 `load_verified_accepted_correction → resolve → finalize` 链。它证明「守卫会早退」，但未独立复现派工单所述的下游 `ValueError` 崩溃。修复本身仍正确（已 enriched 的契约早退是显而易见对的），只是测试偏浅。

### F2-1 [MAJOR] reading→correction accepted 对账 — ✅ 闭合

- **代码** `src/agent/correction/window_sources.py:498-552` `verify_reading_stage_root_against_accepted_attempt`，在**两处消费入口**都接上：`run_stage.py:231`（`_draw_correction` 入口，在 `run_correction` 读字节之前）、`window_sources.py:470`（`build_verified_window_inputs_from_run` 入口）。无 accepted 记录 → 早退放行（不误伤 standalone）。
- **活体探针** `/tmp/probe_f21_legit.py`（关键：单测**没覆盖合法路径**，只覆盖篡改路径；本项目最怕的 false-green 正是「合法输入被误伤」）：

  ```
  [OK ] A legit single-view (no tamper): NO-RAISE
  [OK ] B legit two-view (no tamper): NO-RAISE
  [OK ] C tampered stage-root (blocked later draw): RAISE(...accepted_attempt_mismatch)
  [OK ] D standalone (no manifest/accepted): NO-RAISE
  [OK ] E legit value, different whitespace/key-order in flat file: NO-RAISE
  RESULT: ALL OK
  ```

  即：合法 reading（含多视图、whitespace 变体、standalone）**不误伤**；stage-root 被覆写才 fail-closed。证明守卫在真实生产键序下不会 false-reject。
- **neuter（全量）**：把守卫改成立即 `return` → **恰好 3 条测试红**（`test_draw_correction_rejects_nonaccepted_reading_before_llm_consumes_it`、`test_window_source_builder_rejects_nonaccepted_reading_at_its_own_entry`、`test_reading_guard_rejects_tampered_accepted_archive`），`1449 passed, 9 xfailed`——**零连带**。standalone 放行测试正确保持绿。

> **MINOR-1**（F2-1 隐含耦合 / latent）：守卫的重构 `json.dumps({stem:json.loads(flat) for flat in sorted(glob("*_view.json"))}, indent=2, ensure_ascii=False)` 要与 accepted `output.json` 逐字节一致，**隐含依赖** `_draw_reading`（`run_stage.py:178-189`）也按 `sorted(glob)` 同序构建 `output_obj`。今天两者都排序、匹配；但一旦 `_draw_reading` 改成不排序（或新增别的 reading 生产者），**每个多视图 run 都会被静默 false-reject**，而现有单测全是单视图、抓不到这个耦合。
> - **失败场景**：`_draw_reading` 改键序 → 合法多视图 run（sm25-L 的 plan+多立面正是多视图）在 correction 入口被 `source_identity_invalid` 误杀。
> - **出口条件（改动面最小）**：补一条「多视图合法 reading → correction 入口守卫放行」回归测试（我那份 `/tmp/probe_f21_legit.py` case B 可直接转正）；或在守卫两侧都用 `sort_keys=True` 的规范形比较、解掉对生产者键序的依赖。

### F2-2 [MINOR] S5 mep accepted + input_hashes 绑定 — ✅ 闭合

- **代码** `run_stage.py:538-549`（manifest accepted 记录 + `_accepted_output_path` 读字节 + `hash_bytes` 身份对账）+ `:585-588`（`input_hashes` 加 `("4_mep", mep_record.output_hash)`）。旧 bug「stage-root 被 blocked draw 覆写 → 静默消费」通过**改读 accepted 归档**根治，身份对账是纵深防御。
- **neuter A（还原为 stage-root 读，全量）**：`test_assembly_reads_and_binds_accepted_mep_not_stage_root` + `test_assembly_rejects_tampered_accepted_mep_archive` 红，`1450 passed, 9 xfailed`——**零连带**（无任何既有装配测试依赖新读路径，也无回归）。
- **neuter B（仅去掉 input_hashes 的 4_mep 条目）**：**只** `test_assembly_reads_and_binds_accepted_mep_not_stage_root` 红（`KeyError: '4_mep'`），归档篡改测试保持绿——干净隔离出「输入哈希绑定」这条子锁。
- → 两个子锁（读 accepted / 绑哈希）各自真绑在目标约定上。

### F5-1 [MAJOR·缺锁] 逐层 footprint 一致门两层负锁 — ✅ 闭合

- **schema 层** `src/agent/correction/schema.py:262-263` + 测试 `test_v3_schema_rejects_divergent_per_floor_footprints`。
- **envelope 事务层** `src/agent/correction/envelope_transform.py:519-520` + 测试 `test_transaction_rejects_divergent_footprints_after_schema_is_bypassed`（monkeypatch `CorrectedGeometryV3.model_validate` 绕过 schema）。
- **neuter schema 层**：schema 测试红（`DID NOT RAISE`），**envelope 测试仍绿** → envelope 测试真的绕过了 schema、不靠 schema 挡。
- **neuter envelope 层**：envelope 测试红——事务越过 scope 门、撞到下游 `correction.envelope_axis_attachment` 门 → `failed_gate_id` 与断言不符不上；**schema 测试仍绿**。
- → 这正是派工单 §9/§4 反复警告的 false-lock 险点：测试用 `failed_gate_id == "correction.envelope_schema_scope"` 精确绑死目标门，neuter 后会落到别的门而红。锁设计正确，两层互不连带。

### F4-1 [MAJOR] v3 判卷 bindings 缺失兜底 + SOP 文档 — ✅ 闭合

- **代码** `run_stage.py:1357-1377`：**重排**为「先 `load_score_gt_identity` → `typed_gt is None` 才静默 None（即本就没有可判的 v3 GT）；v3 GT 在但 base/bindings 缺 → exploratory/dev `warnings.warn`、golden/regression `raise RuntimeError`」。`run_profile` 经 `cmd_run/cmd_flow → _render_stage_grade_artifacts → _render_all_typed_attempt_grades / _judge_packet → _grade_typed_attempt_artifacts` 正确穿线（两个生产调用点 `run_stage.py:1781`、`:1989` 都传了 `run_profile=policy.run_profile`）。
- **neuter A（还原为静默 return）**：4 条 warn/fail 参数化测试红，silent 测试绿。
- **neuter B（关掉 `if typed_gt is None` 早退门）**：**只** `test_missing_bindings_remains_silent_when_gt_is_not_v3` 红——它吃到了「无 v3 GT 却被告警」的误伤（`RuntimeError: ... v3 GT is present ... under run_profile=golden`），正是 §9 ③ 要防的假阳性；4 条 warn/fail 测试保持绿。
- → §9 ③「只在有 v3 GT 缺 bindings 时告警/fail、不误伤本就无 v3 GT 的静默 None」这条**顺序约定被精确锁住**（这是本仓翻车点，锁很到位）。
- **SOP 文档** `AI_agent/guides/new_case_guide.md` §0.3：如实写明 bundle 路径 `gt/<case>/score_inputs/view_bindings.json`、需人工/脚本搬运到 `<run>/_run/judge_score_bindings.json`（**没有 provision bridge**，诚实标注）、exploratory warn / golden fail-closed。锚点 `c2_b4b_detail_spec.md#63-judge-score-view-bindings` 实存（line 343），内容与 spec 一致。

> **NIT-2**（F4-1 fail-closed 形态）：golden/regression 缺 bindings 时是裸 `RuntimeError` 从 `_grade_typed_attempt_artifacts` 经 `_judge_packet` 冒上来，而非一条 graded `ERROR` verdict。属 fail-closed（符合派工单），但语义上不如 CheckReport ERROR 干净。可后续优化，不阻塞。

### F1-2 [MINOR] capability_profile 进 run_config — ✅ 闭合

- **代码** `run_config.py:85,112,169,_parse_capability_profile`（值域校验 `("rectangular","orthogonal_polygon")`，非法→警告并 None，缺省 None）；`run_stage.py:1742-1743`（cmd_run）、`:1925-1926`（cmd_flow）用 `run_config.capability_profile or CLI`。顺序正确：`load_run_config` 在 `_make_policy` 之前（cmd_run `1738<1739`、cmd_flow `1912<1922`）。
- **neuter**（cmd_flow 还原为 CLI-only）：「yaml 覆盖」参数化红（`'rectangular' != 'orthogonal_polygon'`，CLI 被错用）；「缺省 CLI 生效」+ 解析器两条测试绿。
- → 锁真绑在 run_config 覆盖 CLI 这条约定上。

> **NIT-3**（F1-2 范围不一致）：`cmd_judge`（`run_stage.py:1836-1839`）仍用 `getattr(args,"capability_profile","rectangular")`、未读 run_config。该路径是 judge-only 只读重放、不画几何，大概率无碍，但与 F1-2 修复范围不一致。建议确认 judge 重放是否需要与 run 的 capability 一致；如需要，顺手补上同款覆盖。
>
> **NIT-4**（F1-2 覆盖）：cmd_run 的同款接线（`:1742`）没有直接测试（只 `test_flow_run_config_capability_profile_overrides_only_when_present` 覆盖了 cmd_flow）。两者代码同形，风险低，但 cmd_run 路径零直测。

### B4b MINOR-1 [升格] correction v3 判卷 e2e fixture — ✅ 闭合

- **活体探针** `/tmp/probe_b4b.py`（实跑 fixture，dump 产出）：

  ```
  --- sidecar payload.kind: c2_scored
  --- sidecar identity.product.stage: correction
  --- sidecar identity.product.accepted: True
  n score_criteria: 8
  --- grade.png bytes: 15143 magic: b'\x89PNG...'
  REAL_GRADE: True
  ```

  即产出的不是桩：`c2_scored` payload、correction stage、accepted、8 条 score_criteria、claim/segment ledger、15KB 真 PNG。判卷测量仪链路实通。
- **neuter**（去掉新增的 `window_host_proof` 接线）：e2e 红 `ScoreContractError: ... official_b5_requires_verified_six_artifact_input`——证明 e2e 真走 correction 计分路径，且新增接线是「让 correction v3 计分能跑通」的必要接线（缺了就 fail-closed）。
- **附注**：本批在 `_grade_typed_attempt_artifacts` 新增了 `window_host_proof` 接线（`:1385-1394`）+ 一个 `RuntimeError` 守卫（accepted_attempt 不符即抛）。派工单 F4-1/B4b 没显式单列这两处，但它们是**必要接线**（把已算好的 `verified.window_host_proof` 喂给既有 scorer），非算法改动，且 fail-closed。可接受。

---

## 横切检查（新缺陷 / 回归 / 越界）

- **零算法改动、零 golden 改动**：diff 只动 `run_stage.py`（接线）、`window_sources.py`（守卫）、`run_config.py`（配置字段）、`new_case_guide.md`（文档）+ 测试。未触 `score_service.py / score_policy.py / score_schema.py` 等判卷算法，未触任何 golden/fixture 数据文件。
- **既有测试未被放松**：对既有测试文件的改动全是**纯加法**（新函数/新参数），无删除/放宽既有断言。
- **无全局 warning 过滤**：`pyproject.toml [tool.pytest.ini_options]` 只有 `pythonpath`/`testpaths`，无 `filterwarnings`——F4-1 的 `RuntimeWarning` 在生产/测试都会冒头，不会被吞。
- **load_score_gt_identity raise 安全**：F4-1 把 gt 加载挪到 bindings 检查之前。该函数仅在文件读/解析失败时抛 `ScoreContractError`；而 typed 路径只在 `isinstance(document, GroundTruthV3)` 为真时进入（`run_stage.py:1309`/`:1439`），即 gt 文件已成功加载过一次，重载不会再抛——重排不引入新失败面。
- **零残留**：所有 neuter 手动改回后，`diff <(git diff) /tmp/REVIEW_baseline_full.diff` 逐字节一致；`git status --porcelain` 与审前一致。
- **审前=审后全量**：1452 passed, 9 xfailed。

---

## 操作纪律自证

- 待审产物是**未提交**工作区改动；全程**未使用** `git checkout / stash / restore`。
- 每个 neuter 探针：记原文 → 手改 → 跑 → 手改回。审毕指纹核验：

  ```
  WORKTREE == BASELINE (all neuters restored, zero residual)
  STATUS == BASELINE
  ```

  审阅现场完整保留。

---

## 结论

7 条 finding 全部真正闭合；7 把新负锁经活体 neuter 验证**真绑在目标门上、且只红对应测试**（无 false-lock、无连带）；F2-1 合法多视图路径经活体探针确认不误伤；B4b e2e 产真 grade。零算法/golden 改动，零回归，零残留。

**APPROVE**。下方 MINOR/NIT 为加固项（最有价值的是 **MINOR-1**：给 F2-1 守卫补一条多视图合法路径回归测试，或解掉对生产者键序的隐含耦合），可在后续批次处理，不影响本批交付。
