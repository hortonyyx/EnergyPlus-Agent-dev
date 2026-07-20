# Fable 对抗审派单 — C2 体检 4 MAJOR + 配套（sol 施工）

- **日期**: 2026-07-20
- **审者**: Fable 5（顶档对抗审）
- **施工**: sol（已交付，7 finding 自报全 COMPLETE）
- **你的裁量权**: 你是本批唯一权威对抗审。主控（Opus）不做技术裁决，只编排/传话/轻门。**迭代到你 APPROVE 为止**。
- **基线**: 分支 `6.15_ValidationArchM0toM4`；派工单基线 1434 passed + 9 xfailed；主控独立全量复跑本轮尾态（附测试输出）。

## 你看什么（复核纪律：只看需求 + diff + 测试输出，别被执行者自述带偏）

1. **原始需求（权威规格）**: `AI_agent/logs/reviews/request/2026-07-20_audit_remediation_construction_dispatch.md`（7 finding 逐条 file:line / 修法 / 负锁要求 / §0 缺锁即未交付纪律 / §8 不做项 / §9 审阅钩子）。
2. **diff**: `git diff`（生产码 = run_stage.py / window_sources.py / run_config.py / new_case_guide.md；测试 = test_audit_remediation_accepted_inputs.py〔新〕/ test_run_stage_flow.py / test_run_config.py / test_c2_b2_v3.py / test_c2_b2b_envelope_transform.py / test_c2_b4b_phase_d.py）。
3. **测试输出**: 见本单末「主控独立全量」。
4. sol 的施工简报（`.../execution/2026-07-20_audit_remediation_construction_brief.md`）**只在你要核对它的 neuter 自报是否属实时看，别当结论**。

## 审法要求（本仓 B5 Phase C/D 标准）

- **每条新负锁做 neuter 活体探针**：把目标门/守卫改成恒通过 → 跑对应测试 → **必须且只有对应锁红**（余绿）；恢复 → 全绿。
- **重点抓 false-lock**（本仓反复翻车点）：简报声称锁在 A 门、实际停在上一道 B 门，A 门 neuter 后仍全绿。
- **零算法改动 / 零 golden / 无越界 / 零回归**（≥ 1434+9，本批 +18 测→1452+9）。

## 主控预扫已定位的探针（供你复核，非替代你独立审）

**P1〔头号·F2-1 正例锁缺失〕**：`verify_reading_stage_root_against_accepted_attempt`（window_sources.py）在有 accepted 0_reading 时，用 `{path.stem: parsed for sorted(glob("*_view.json"))}` + `json.dumps(indent=2, ensure_ascii=False)` 重建 stage-root 字节，与 accepted `output_hash` 对账。
- 主控已核：真实 `_draw_reading`（run_stage.py:178-189）组的归档 `output_obj` = `{stem: parsed for sorted glob}`，StageRunner 纯 dict 归档用 `json.dumps(indent=2, ensure_ascii=False)`（stage_runner.py:560）——**与 guard 重建逐字对位，故合法未篡改 run 会放行（非 run 级 BLOCKER）**。
- **但**：新测试文件 F2-1 全是「拒绝」或「无 accepted standalone 放行」，**没有一条正例锁**证明「未篡改的 accepted reading + 忠实 stage-root → guard 放行返回 None」，也没有测试把 guard 重建约定与 `_draw_reading` 的 output_obj 约定**绑在一起**。将来任一侧改约定（`_draw_reading` 停止 sorted / guard 改序列化）无锁可抓 → 合法 run 静默误拒、无回归防护。请裁：这是否 REWORK 级补一条「真 `_draw_reading` 归档 + 忠实 stage-root → 放行」的正例锁（用真实归档路径，别手搓 `{stem:view}` 自指 fixture）。

**P2〔F5-1 envelope 纵深锁真抵达目标门〕**：envelope 负锁（test_c2_b2b_envelope_transform.py）声称 neuter envelope identical 门后锁红、但「落到后续 `correction.envelope_axis_attachment`」。请复核：该锁断言的是**目标 gate id `correction.envelope_schema_scope`**（非「任意拒绝」），且负例**真绕过 schema 层抵达 envelope 事务层**（否则测的是 schema 层不是 envelope 层 = false-lock）。schema 层负锁（test_c2_b2_v3.py）neuter schema identical 门后须单独红、不连带 envelope 锁。

**P3〔F4-1 只在「有 v3 GT 但缺 bindings」告警/fail、不误伤〕**：`_grade_typed_attempt_artifacts` 现把 gt identity 前置，`typed_gt is None`（本就无 v3 GT）→ 维持静默 None；`typed_gt is not None` 且 base/bindings 缺 → exploratory/dev `RuntimeWarning`、golden/regression `RuntimeError`。请核：① run_profile 是否在**所有**相关调用链（cmd_run/cmd_flow → _judge_packet / _render_stage_grade_artifacts → _render_all_typed_attempt_grades → _grade_typed_attempt_artifacts）真传导到位（默认 "exploratory" 会不会让某条 golden/regression 路径静默不 fail-closed）；② 负锁覆盖 golden/regression fail + exploratory warn + 非 v3 静默三态。

**P4〔F2-2 mep accepted 绑定〕**：S5 新增 `assembly.mep_accepted_required`（无 accepted 4_mep record 即拒）+ 读 accepted 归档 + hash 校验 + input_hashes 补 `("4_mep", ...)`。正例锁 `test_assembly_reads_and_binds_accepted_mep_not_stage_root` 已在（断言真读 accepted 而非 blocked root + hash 绑定）；负锁 tamper。请核这不误伤既有合法 S5（4_mep 正常 accept 的 run），且 neuter「删 input_hashes 4_mep」binding 锁红、neuter「hash 门恒通过」tamper 锁红、互不连带。

**P5〔F1-1 再入回归〕**：早退守卫加 `correction_b5_orientation_v1`。回归锁 `test_b5_orientation_enrichment_is_idempotent_on_reentry` 把 resolver 设为一调即 raise，断言返回原 verified。请核 neuter「撤 b5 分支」该锁单独红。

**P6〔F1-2〕**：`run_config.capability_profile`（present 覆盖 CLI、absent 保留 CLI、非法值 warn 回退）。请核 flow 参数化锁真覆盖「present 覆盖」与「absent 保留」两支，neuter「flow 改回纯 CLI」present 支锁红。

**P7〔B4b MINOR-1〕**：correction v3 判卷 e2e（test_c2_b4b_phase_d.py）用真 accepted `correction_b5_orientation_v1` + 真六件 proof + typed GroundTruthV3 + reviewed bindings，端到端断真 v8 sidecar/非 None grade。sol 诚实披露此 e2e 暴露并补了「assembler 把 verified window_host_proof 传给 scorer」的接线（run_stage.py:1354+）。请核：① 该接线未改 scorer 算法/policy/verdict，只补传参；② neuter「proof 传 None」correction e2e 红、reading typed e2e 绿。

## 输出

给出 verdict：**APPROVE** 或 **REWORK**（逐条 finding，标 BLOCKER/MAJOR/MINOR/NIT + 出口条件）。落 `AI_agent/logs/reviews/verdict/2026-07-20_audit_remediation_fable_review.md`。若 REWORK，主控转派 sol 返工、续循环到你点头。
