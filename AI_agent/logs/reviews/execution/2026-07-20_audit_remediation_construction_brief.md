# 施工简报 — C2 体检 4 MAJOR + 配套

- 日期：2026-07-20
- 施工：sol
- 基线：`f59a7c1`（派工单给定 `1434 passed + 9 xfailed`）
- 结论：**7/7 finding COMPLETE**
- 越界核对：未改 gate①/judge/verdict 语义、未改 `run_pipeline` 契约、未改 golden、未改 9 个 legacy xfail、未做派工单 §8 项。

## F1-1 — COMPLETE

- 改动：`_ensure_orientation_enriched` 的早退契约集合加入 `correction_b5_orientation_v1`。
- 锁：`test_b5_orientation_enrichment_is_idempotent_on_reentry` 注入已 enriched B5 verified，并把 resolver 设为一旦调用就报错；断言返回原 verified。
- neuter：撤掉 B5 契约分支后，该锁单独红；同跑 `test_stepwise_enrichment_and_assembly_identity` 仍绿。恢复后锁绿。

## F2-1 — COMPLETE

- 改动：新增 `verify_reading_stage_root_against_accepted_attempt`。有 0_reading accepted 指针时：
  1. 复核 accepted `attempts/NNN/output.json` 原始字节 hash 与 manifest；
  2. 按 `StageRunner` 的真实归档形状，把 flat `*_view.json` 重建为同一 JSON payload，再与 accepted `output_hash` 对账；
  3. 无 manifest / 无 accepted 时直接放行，保留 standalone/exploratory 行为。
- 两处消费接线：`_draw_correction` 在 `run_correction` 前调用；`build_verified_window_inputs_from_run` 在读取 raw reading 前调用。
- 锁：
  - `test_draw_correction_rejects_nonaccepted_reading_before_llm_consumes_it`
  - `test_window_source_builder_rejects_nonaccepted_reading_at_its_own_entry`
  - `test_draw_correction_without_accepted_reading_preserves_standalone_path`
  - `test_reading_guard_rejects_tampered_accepted_archive`
- neuter：
  - stage-root hash 门恒通过：两个消费入口拒绝锁红，standalone 放行锁绿；
  - accepted archive hash 门恒通过：archive tamper 锁红，stage-root mismatch 锁绿；
  - 恢复后四锁全绿。

## F2-2 — COMPLETE

- 改动：S5 要求 4_mep accepted record，读取 accepted attempt 归档而非 `mep_output.json` root 镜像，复核归档 hash；`AssemblyE4Write.input_hashes` 加 `("4_mep", accepted.output_hash)`。
- 锁：
  - `test_assembly_reads_and_binds_accepted_mep_not_stage_root` 用合法但不同的 blocked-later root，断言实际装配 accepted MEP 且 hash 绑定存在；
  - `test_assembly_rejects_tampered_accepted_mep_archive` 锁 accepted 归档 hash 门。
- neuter：
  - 改回 stage-root 读取：两锁红；
  - accepted hash 比较恒通过：tamper 锁红，accepted-root/binding 锁绿；
  - 删除 4_mep `input_hashes`：binding 锁红，tamper 锁绿；
  - 恢复后两锁全绿。

## F5-1 — COMPLETE

- schema 锁：`test_v3_schema_rejects_divergent_per_floor_footprints` 构造两层不同 footprint，锁 `CorrectedGeometryV3._v3_integrity` 的 identical-geometry 门。
- envelope 纵深锁：`test_transaction_rejects_divergent_footprints_after_schema_is_bypassed` 先构造合法对象，再原位制造 footprint 分歧，并 monkeypatch `CorrectedGeometryV3.model_validate` 绕过入口 schema 重校验；断言事务自己的 `correction.envelope_schema_scope` rollback。
- API 语义说明：`apply_v3_envelope_transaction` 内部抛 `EnvelopeTransformRejected`，但既有公共事务契约会捕获并返回 `failed_gate_id`；本批遵守“门本体已活只补锁”，未改变为向外抛异常。锁精确断言捕获后的目标 gate id 与 reason。
- neuter：
  - schema identical 门恒通过：schema 锁红，envelope 锁绿；
  - envelope identical 门恒通过：envelope 锁红（落到后续 `correction.envelope_axis_attachment`），schema 锁绿；
  - 恢复后双锁绿，证明 envelope 负例确实抵达纵深门。

## F4-1 — COMPLETE

- 改动：typed GT identity 先于 sidecar existence 判断；仅当 `typed_gt is not None` 且 base/bindings 缺失时分档：
  - exploratory/dev：`RuntimeWarning`，明确 v3 GT 存在、judge sidecar 缺失、判卷层被跳过；
  - golden/regression：`RuntimeError` fail-closed；
  - 非 v3 GT：保持静默 None。
- profile 接线：`run_profile` 从 cmd/flow policy 传到 packet、per-attempt grade render 与 typed assembler。
- SOP：`AI_agent/guides/new_case_guide.md` 新增 §0.3，写清 GT bundle `score_inputs/view_bindings.json`、人工/reviewer 核对、显式落位 `<run>/_run/judge_score_bindings.json`，并如实注明当前无自动搬运 bridge。
- 锁：exploratory/dev 两参数 warning 锁、golden/regression 两参数 fail 锁、非 v3 静默兼容锁。
- neuter：缺 sidecar 分支恒不进后，四个 v3 profile 参数锁红；非 v3 静默锁仍绿。恢复后五参数全绿。

## F1-2 — COMPLETE

- 改动：`RunConfig.capability_profile: str | None`，支持顶层 `capability_profile`，值域仅 `rectangular|orthogonal_polygon`；缺键为 `None`，非法值 warning 后回退 CLI/default。`cmd_run` 与 `cmd_flow` 在键存在时用 config 覆盖 CLI，否则保留 CLI/默认。
- 锁：RunConfig 解析/非法值锁；flow 参数化锁分别覆盖“present 覆盖 CLI 默认”和“absent 保留 CLI”。
- neuter：flow 改回纯 CLI 后，present 参数锁红，absent 参数锁绿。恢复后双参数绿。

## B4b MINOR-1 — COMPLETE

- 测试：`test_correction_v3_runstage_scoring_e2e_emits_real_grade` 使用真实 accepted `correction_b5_orientation_v1` attempt、真实六件 B5 proof、typed GroundTruthV3 与 reviewed score bindings，端到端调用 `_grade_typed_attempt_artifacts(stage="1_correction")`，断言 v8 `c2_scored` sidecar、product stage=`correction`、非 None PNG grade。
- 配套必要接线：e2e 暴露 run-stage assembler 未把 scorer 已要求的 verified `window_host_proof` 传给 `score_attempt_service`。现从当前 accepted correction 的六件 artifact verifier 取得 proof，并核对 accepted attempt index 后传入。未改 scorer 算法、policy 或 verdict。
- neuter：把 request 的 `window_host_proof` 改为 None，correction e2e 红（`official_b5_requires_verified_six_artifact_input`），既有 reading typed e2e 绿；恢复后两者绿。

## 测试结果

- targeted：
  - `pytest -q tests/test_audit_remediation_accepted_inputs.py tests/test_run_config.py tests/test_run_stage_flow.py tests/test_c2_b2_v3.py tests/test_c2_b2b_envelope_transform.py tests/test_c2_b4b_phase_d.py tests/test_output_coordinate_identity.py`
  - **114 passed，PYTEST_EXIT=0**（12 个既有/预期 warning）
- 全量：
  - `pytest -q`
  - **1452 passed + 9 xfailed，PYTEST_EXIT=0**，146 warnings，552.26s
  - 相对派工单基线：passed +18，xfail 保持 9。

## 未竟项

- 无。本批 finding 全部 COMPLETE。
- 派工单 §8 明确不做项均未触碰。

---

## 返工 r1 — Fable REWORK 出口闭环

- 依据：`AI_agent/logs/reviews/verdict/2026-07-20_audit_remediation_fable_review.md`
- 结论：**M1 CLOSED / M2 CLOSED / m1 CLOSED**
- 边界：首轮生产改动全部保留；返工只新增测试与 `_grade_typed_attempt_artifacts` 一处 correction-only 早退。未改 scorer、judge/verdict、golden 或 legacy xfail。

### M1 — F2-1 happy-path parity 锁 — CLOSED

- 改动：新增 `test_real_draw_reading_archive_is_accepted_by_correction_guard`。
- 锁绑定：复制真实 sm21 `case_data` 与六份真实 reading view；调用生产 `_draw_reading` 得到原样 `output_obj` 与 report，直接交给真实 `StageRunner.record` 归档，保持 stage-root 忠实不篡改；随后调用 `_draw_correction`，以 probe 证明已越过 accepted-reading guard 并抵达 `run_correction`。测试没有手搓 `{stem: view}` 归档对象。
- neuter：把 guard 的 stage-root 重建顺序从 `sorted(...)` 改为 `reversed(sorted(...))`，只有该 happy-path parity 锁红（`accepted_attempt_mismatch`）；既有 stage-root 篡改双入口负锁与 standalone 放行锁共 3 条均绿。恢复后全绿。

### M2 — F-R1 非 accepted correction 判卷循环 — CLOSED

- 改动：`_grade_typed_attempt_artifacts` 在 `stage == "1_correction" and accepted_record is None` 时静默返回 None 三元组。作用域仅 correction；reading 的非 accepted attempt 继续进入 scorer。
- 锁绑定：新增 `test_correction_v3_grade_loop_skips_nonaccepted_attempt_and_scores_accepted`，复用真实 `_stepwise_e4_run`：001=base correction、002=`correction_b5_orientation_v1` accepted，并 provision 真实 typed GT / view manifest / judge bindings。完整调用 `_render_all_typed_attempt_grades`，断言 attempts 确为 `001,002`、accepted=2、001 返回 None、002 产真实 score 与 PNG grade。
- neuter：删除 correction-only 早退后，只有 P7x 循环锁红，红因精确为 001 的 `ScoreContractError: score_unsupported_combination at scoring.capability`；accepted correction e2e 与 reading typed e2e 均绿。恢复后全绿。
- P7x 尾态复跑：完整两 attempt 循环不 raise，`artifacts[1]` 为 None 三元组，`artifacts[2]` 为真分与真 PNG。

### m1 — cmd_run capability_profile 孪生锁 — CLOSED

- 改动：新增参数化 `test_cmd_run_config_capability_profile_overrides_only_when_present`，用 capture `_make_draw_fn` 检查 cmd_run 构造出的真实 policy。
- 锁绑定：present `orthogonal_polygon` 覆盖 CLI `rectangular`；键 absent 时保留 CLI `orthogonal_polygon`。
- neuter：cmd_run 单独退回纯 CLI 后，只有 present 参数锁红；cmd_run absent 参数与 cmd_flow present/absent 两参数共 3 条均绿。恢复后四参数全绿。

### 返工 r1 测试

- 出口 focused：M1 + P7x + accepted correction/reading e2e + cmd_run/cmd_flow 双支，**8 passed**。
- touched targeted：
  - `pytest -q tests/test_audit_remediation_accepted_inputs.py tests/test_run_config.py tests/test_run_stage_flow.py tests/test_c2_b2_v3.py tests/test_c2_b2b_envelope_transform.py tests/test_c2_b4b_phase_d.py tests/test_output_coordinate_identity.py`
  - **118 passed，PYTEST_EXIT=0**（12 个既有/预期 warning）。
- 全量：`pytest -q` → **1456 passed + 9 xfailed，PYTEST_EXIT=0**，146 warnings，414.75s。
- 相对首轮交付尾态：passed +4，xfail 保持 9。
