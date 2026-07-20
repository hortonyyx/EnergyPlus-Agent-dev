# 派工单 — C2 体检 4 MAJOR + 配套 一把全上（sol 施工）

- **日期**: 2026-07-20
- **主控**: Opus 4.8
- **施工档**: sol（GPT 最高档，经 `mcp__codex__codex`，`danger-full-access`）
- **对抗审**: Fable 5（顶档，迭代到 APPROVE；主控不做技术裁决，只编排/传话/轻门）
- **主控轻门**: 独立全量 pytest + 亲核 diff/探针 → commit
- **基线**: 分支 `6.15_ValidationArchM0toM4`，HEAD `f59a7c1`，**1434 passed + 9 strict xfailed**
- **来源**: [logs/experiments/2026-07-19_c2_landing_quality_audit/C2_AUDIT_REPORT.md](../../experiments/2026-07-19_c2_landing_quality_audit/C2_AUDIT_REPORT.md)
- **拍板**: 用户 2026-07-20 定「一把全上 + sol 最高档一把」

---

## 0. 总纲 / 纪律（必读）

1. **审阶梯 = 缺锁即未交付**：本仓 B5 Phase C/D 的验收标准 = **spec/门点名的每一条安全拒绝分支必须有测试负锁**（neuter 门 → 对应测试即红）。你补的每一处门/守卫，都要有能证明「把门拆了测试就红」的负锁。Fable 会对每个锁做 neuter 活体探针；**false-lock**（简报声称锁在 A 门、实际停在上一道 B 门，A 门 neuter 后全绿）是本仓反复翻车点，务必自查「锁真的绑在目标门上」。
2. **诚实优先**：啃不下的部分**如实标 PARTIAL**、精确列未竟项，**绝不藏假绿**。对标 B4b Phase D / B5 Phase D 的正面样板（诚实部分交付 → 主控退回续作）。宁可 PARTIAL 也不要伪 COMPLETE。
3. **越界纪律**：**不改算法本体**（体检结论：这批全是「新接线漏网/老区未巡」型，无一算法 bug）。守卫/门本体已活的，只补锁；接线漏的，只补接线；不重构。改动面越小越好。
4. **零回归**：全量 pytest 必须 ≥ 1434 passed + 9 xfailed（除非你新增测试使总数上升）。**gate①/judge/verdict 语义、run_pipeline 契约、任何 golden 不得动**。9 个 xfail 是 legacy golden，别碰。
5. **交付物**：① 全部改动 + 新测试；② 一份诚实施工简报（每 finding：改了什么、锁绑在哪道门、neuter 自验结果）；③ 全量 pytest 输出（`PYTEST_EXIT` + 计数）。

---

## 1. F1-1 [MAJOR] B5 orientation 再入守卫漏网 —— 1 行 + 回归测试

- **位置**: `scripts/tool_scripts/run_stage.py:452`，`_ensure_orientation_enriched` 的早退守卫：
  ```python
  if verified.ref.schema_version != "3" or verified.ref.artifact_contract == "correction_e4_orientation_v1":
      return verified
  ```
- **故障**: 早退只认 `correction_e4_orientation_v1`，不认 `correction_b5_orientation_v1`。B5 v3 run 再入（`--from 5_intakeoutput` 重跑 / 修 4_mep 后重装配 / `--with-ep` 复跑）时 accepted 契约已是 `correction_b5_orientation_v1` → 守卫不早退 → 走 `resolve_orientation_from_run_dir` → `finalize_orientation_enrichment`（`src/agent/correction/orientation.py:396-419`：base 契约不在 `{correction_b2_v1, correction_b5_v1}` 就 raise ValueError，且已填充 north_axis 也 raise）→ 抛未捕获 ValueError（`_draw_assembly` 只捕 `OrientationNeedsInputError`，run_stage.py:526）→ flow 崩溃（fail-closed，非错值，但 sm25-L 实跑必踩重装配路径）。
- **对照**: E4 出口契约本体两个 orientation 契约都认（`src/agent/output_coordinates.py:165-168`），漏的只是这处 run_stage 守卫。
- **修法**: `artifact_contract in ("correction_e4_orientation_v1", "correction_b5_orientation_v1")`。
- **测试要求**: 一条「已 enriched 的 B5（accepted=`correction_b5_orientation_v1`）再入 `_ensure_orientation_enriched`」回归测试 → 断言**早退返回原 verified、不再触发 enrichment/不 raise**。全仓当前唯一提及 b5_orientation 契约的是 `tests/test_output_coordinate_identity.py:314`（只测 identity 链方向），此再入路径零测试。

---

## 2. F2-1 [MAJOR] reading→correction / B5 消费未绑 accepted attempt —— 同 sm24 族洞的另一半

- **背景**: 2026-07-08 sm24 实锤过此族洞（blocked draw 经 stage-root 镜像喂进内核），当时修法 = `_load_snapped` **manifest-first**（`run_stage.py:308-321` 注释自述），但只修了 **correction 出口** 这一边，**最上游 reading→correction 这级仍是裸的**。
- **两处消费点**:
  - `run_stage.py:255-269` `_draw_correction`：`rdir = run_dir/"0_reading"`，`run_correction(rdir, ...)` 与 `build_verified_window_inputs_from_run(reading_dir=rdir)` 直接消费 stage-root 的 `*_view.json`（最后一次 draw 的镜像，可能非 accepted attempt）。
  - `src/agent/correction/window_sources.py:477-484` `build_verified_window_inputs_from_run`：从 `reading_dir/f"{entry.expected_output_id}.json"` 直读 reading 字节，**只对 view_manifest 做 content hash 绑定，对 reading 字节 vs 0_reading accepted attempt 的 output_hash 零对账**。
- **修法（保守 guard，非重构）**: 消费 reading 时经 manifest accepted attempt 对账——**有 accepted 记录时 verify 字节 hash（不符即 fail-closed）；无 accepted 记录（standalone/exploratory）时维持现状放行**。参照现有 `_accepted_output_path`（run_stage.py:288-305）+ `_load_snapped`（308-321）的 manifest-first 范式；reading 侧需先摸清 0_reading attempt 的归档形状（`attempts/NNN/output.json` 与 flat `*_view.json` 的关系）再设计对账点。
- **注意**: B5 writer 的 replay（十步独立重算）也从同一 stage-root 字节重算——replay 对上只证明「与 stage root 一致」，不证明「与 accepted reading 一致」（这正是 MINOR-3 相邻但不覆盖的洞）。所以对账要绑在**读 reading 字节的入口**，不能只靠 replay。
- **测试要求**: ① accepted 记录存在 + stage-root 被覆写为非 accepted 字节 → 消费侧 fail-closed（负锁）；② 无 accepted 记录 → 放行（不误伤 standalone）。两处消费点都要覆盖。

---

## 3. F2-2 [MINOR] S5 消费 mep 走 stage-root、input_hashes 只绑 correction —— F2-1 同族，顺手

- **位置**: `run_stage.py:529-533`（`mep_path = run_dir/"4_mep"/"mep_output.json"` 直读）+ `:564-568`（`AssemblyE4Write.input_hashes` 只有 `("1_correction", verified.ref.output_sha256)` 一条）。
- **故障**: mep blocked draw 覆写 root 后 `--from 5_intakeoutput` 再入会静默消费非 accepted mep。E4 审计只管 north_axis 归零（`output_coordinates.py:825-832`），不绑 mep 字节。较 F2-1 低危（mep 非几何字段、4_mep 门序紧邻 S5）。
- **修法**: S5 经 accepted attempt 读 mep（同 `_accepted_output_path(run_dir, "4_mep")` 范式）+ `input_hashes` 加 `("4_mep", <accepted mep output_hash>)` 一条（manifest StageRecordV2 本就有 hash 可引）。
- **测试要求**: mep stage-root 被非 accepted 覆写 → S5 拒绝 / 绑定 hash 不符即 fail（负锁）。

---

## 4. F5-1 [MAJOR·缺锁] 逐层 footprint 一致门 两层守卫零负锁 —— 补两条负锁

- **门是真的**（正向已验）：构造两层不同 footprint 的 v3 payload → 现网 raise。
- **锁是缺的**（全仓 grep `"identical geometry"` tests/ 零命中）：两层守卫双 neuter 均零红。
  - **schema 层**: `src/agent/correction/schema.py:262-263`
    ```python
    if len({fingerprint(floor) for floor in self.floors}) != 1:
        raise ValueError("v3 per-floor footprints must have identical geometry")
    ```
    → 负锁：构造两层 divergent footprint 的 v3 payload，`ensure_corrected_geometry(...)` **raise ValueError**（断言 message 或异常类型）。
  - **envelope 事务层**: `src/agent/correction/envelope_transform.py:519-520`
    ```python
    if len({floor_footprint_fingerprint(before, f) for f in before.floors}) != 1:
        raise EnvelopeTransformRejected("correction.envelope_schema_scope", "per-floor footprints are not identical")
    ```
    → 该层因 schema 层挡在前面属**纵深防御不可达**；负锁要用 **monkeypatch 绕过 schema 层**（或直接构造已过 schema 的对象再手工令 footprint 分歧）后直调事务层，断言 **raise `EnvelopeTransformRejected`**。
- **验收**: 你补锁后，**neuter schema 层守卫 → 你的 schema 负锁必须红；neuter envelope 层守卫 → 你的 envelope 负锁必须红**，且互不连带（各只红对应新锁）。这是 Fable 会复现的 neuter 探针。
- **注意（防 false-lock）**: envelope 负锁若 schema 层没被真正绕过，会「看似过实则被 schema 挡住」→ 你的锁其实测的是 schema 层不是 envelope 层。务必确保负例真的抵达 envelope 事务层（构造已 divergent 但能过 schema 的路径，或 monkeypatch `schema` 的一致门为恒真）。
- **不在本批**: B2/B2b/B-M 老 spec 点名拒绝分支的同标准负锁补扫（开放式、单列跟进债，主控已登记）。本 finding 只做上述两条 footprint 负锁。

---

## 5. F4-1 [MAJOR] v3 判卷断链：bindings 缺失静默跳过 —— 代码兜底 + SOP 文档（素材不在本批）

- **位置**: `run_stage.py:1337-1342`（`_grade_typed_attempt_artifacts`）：
  ```python
  base_path, bindings_path, overlay_path = _typed_score_input_paths(attempt_dir.parents[2])
  if not base_path.exists() or not bindings_path.exists():
      return {"score_vs_gt": None, "grade": None, "score_criteria": []}
  ...
  gt_identity, typed_gt = load_score_gt_identity(gt_file)
  if typed_gt is None:
      return {"score_vs_gt": None, "grade": None, "score_criteria": []}
  ```
- **故障**: `judge_score_bindings.json` 缺失时**静默返回 None、不告警、不 fail**；全仓无任何生产代码/CLI 写这个文件（grep `judge_score_bindings` 唯一出现点就是 run_stage.py:1299）。sm25-L 若忘作 bindings，整个 v3 判卷层无声消失、跑完全绿。**违「judge 以 gt 为权威」硬规约**。
- **可修的两件（本批）**:
  1. **断链兜底**：当 **case 有 v3 GT**（`typed_gt is not None`）**但 bindings/base 缺失** → **不能静默 None**。改为按 run_profile 分档：exploratory/dev **打 loud warning**（明确「v3 GT 在但 judge bindings 缺失、v3 判卷层被跳过」），golden/regression **fail-closed**。注意当前 bindings 检查（1337）在 gt 加载（1340）**之前**，需重排/重构以先判「是否有 v3 GT」再决定「缺 bindings 是静默还是告警」——静默 None 只允许在「本就没有 v3 GT（typed_gt is None）」时。run_profile 目前没线程进这个函数，需要顺着调用链（`_render_all_typed_attempt_grades` 1363 / `_judge_packet` 1377…）把 profile 或一个 warning sink 传进来（选副作用最小的路子）。
  2. **SOP 文档**：`AI_agent/guides/new_case_guide.md` 补一节「v3 case 判卷需 judge sidecar」——说明 `score_inputs/view_bindings.json`（judge-reviewed，设计口径见 `proposals/c2_b4b_detail_spec.md:345`）+ 落位到 `<run>/_run/judge_score_bindings.json` 的步骤。**注意 spec 说的 bundle 路径（`gt/<case>/score_inputs/view_bindings.json`）与 run_stage 读的路径（`<run>/_run/judge_score_bindings.json`）之间目前没有搬运桥**——文档要如实写「需人工/脚本把 bindings 落位到 `_run/`」，或若你判定该补一个 provision 步骤/CLI，可提议但先在简报里标出（属设计增量、Fable 会审）。
- **不在本批**: 真正 sm25-L 的 `view_bindings.json` 素材（judge-reviewed 内容）——那是主控+用户带真实 sm25 素材做的。本批只做「缺失兜底告警 + SOP 文档」。
- **测试要求**: 有 v3 GT 但 bindings 缺失 → golden/regression fail / exploratory 产 warning（负锁：证明不再静默 no-op）。

---

## 6. F1-2 [MINOR] capability_profile 只在 CLI 旗标、不入 run_config.yaml

- **位置**: `run_stage.py:2119-2124`（`--capability-profile` 全局旗标，默认 `rectangular`）；`src/agent/execution/run_config.py:88-110`（RunConfig 无 capability_profile 字段）；`src/agent/execution/policy.py:43`（默认 rectangular）。
- **故障**: sm25-L 每次 flow 都要手带 `--capability-profile orthogonal_polygon`；漏带则**静默走 v1 rectangular target**——L 形被拆成多矩形 cell（退回 B1 之前的过度分区）而**全绿通过**。与「跑前必确认配置」纪律相悖。
- **修法**: `capability_profile` 进 `RunConfig`（从 `<run>/run_config.yaml` 读；**present 时覆盖 CLI 默认**，缺省维持 CLI/rectangular 向后兼容）。校验值域 `("rectangular","orthogonal_polygon")`。参照 RunConfig 现有字段（`orientation_completion_mode` 是已有的「进 run_config 的确定性配置」样板，run_config.py:103-109）。
- **测试要求**: run_config.yaml 带 `capability_profile: orthogonal_polygon` → policy/flow 实际用 orthogonal_polygon（覆盖 CLI 默认）；无该键 → 维持 CLI/默认。

---

## 7. B4b MINOR-1 [升格·强烈建议] correction v3 判卷 e2e fixture —— 判卷是 sm25-L 的测量仪器

- **背景**: sm25-L 是 correction v3 判卷的**生产首用**；identity/proof 门有全套负锁（崩溃向 fail-closed），但**语义级静默错分**（判错也全绿）是真剩余风险，而判卷正是 sm25-L 的测量仪器。
- **现状**: `tests/` 无 correction-stage v3 计分 e2e fixture（`_grade_typed_attempt_artifacts` / `score_attempt_service` 走 `stage="correction"` 的 v3 端到端零覆盖）。
- **修法**: 补一个 correction v3 判卷 e2e 测试——真实（fixture）v3 GT + view_bindings + correction v3 attempt output，端到端跑 `_grade_typed_attempt_artifacts`(stage=`1_correction`) 或 `score_attempt_service`，断言产出合理的 score/grade（至少证明链路通、identity 门放行真 v3、分数非 None）。可复用 B4b 已有的 fixture 工装（`b4b_contract_fixture.py` 等，grep 现有 v3 GT/bindings fixture）。
- **注意**: 这是**测试补强**，不改判卷算法。

---

## 8. 明确不在本批（勿做）

- sm25-L 真实素材（图 / case_data / reading / `gt.json` GroundTruthV3 / 真 `view_bindings.json` 内容）——主控+用户带真图做。
- `no_oversplit` 永久 NA 的人工兜底——判读纪律，主控写进跑测单。
- F5-1 的 B2/B2b/B-M 老门负锁补扫——开放式，主控单列跟进债。
- §3.2 五条漏记债 + F1-3（ElevationViewBindingV1 同名两型改名）——主控自己落文档/登记。

---

## 9. 审阅需求（给 Fable 的钩子）

Fable 对抗审重点：① 每条新负锁**真绑在目标门上**（neuter 目标门 → 对应且仅对应锁红，防 false-lock）；② F2-1/F2-2 的 accepted 对账**真在读字节的入口**、无 accepted 时不误伤 standalone；③ F4-1 兜底**只在「有 v3 GT 但缺 bindings」时告警/fail**、不误伤「本就无 v3 GT」的静默 None；④ F1-1 早退回归测试真断「不再触发 enrichment」；⑤ 零算法改动、零 golden 改动、无越界。
