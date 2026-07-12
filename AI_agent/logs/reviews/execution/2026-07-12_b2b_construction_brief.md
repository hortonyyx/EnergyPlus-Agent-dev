# B2b 施工简报（terra，2026-07-12）

基线：`6df4398`；动工前工作树干净；未创建 commit。§0.2 B2/B3/Vg 前置门通过（真实 v3 `finalize_correction_draw` 产出 Vg populated segments，release map 为 stage `3`）；步骤 1 后 §0.3 三容差自检通过。

## 改动映射

| 定稿章节 | 代码/测试落点 |
|---|---|
| §3、§4.2、§8.2bis | `envelope.py` 增 wing-break evidence/resolution、显式 chain closure、projection-frame hash；新增 `reading/constants.py`，reading validator 改共用常量；reading guide 写 exact marker producer 义务 |
| §4.1、§8.1、§9 | `config.py`/`correction.yaml` 三个 required B2b tolerance 与交叉校验；A0 registry 登记三项和 B3 area owner |
| §5–§7、§8.4 | 新 `envelope_transform.py`：intent、shared-axis component、window host、candidate copy、hard gates、单条成功 audit、rollback conflict；`deterministic.py` v3 late dispatch，legacy B1 helper 原路径保留 |
| §8.3、§8.5 | `envelope.py` overall agreement 改显式同一 `CoreTolerances`；`finalize.py` 将同一 tol 传入 extraction；未动 Vg materialize/release-map block |
| §10–§11 | 新 `test_c2_b2b_envelope_transform.py`；既有 B2/B1/Vg/core helper 显式补齐 required tolerances；B1 legacy guard 与 v3 blanket-reject 窄化回归 |

## 备份

修改前备份在 `backup/src_history/2026-07-12_b2b_envelope_transform/`，按仓库相对路径保存所有既有将改的 `src/`、`tests/`、config、A0 和 reading guide 文件。新建的 `envelope_transform.py`、`reading/constants.py`、B2b 测试和本简报无前身，未做伪备份。

## 验收与测试

- §0.2 precondition gate：PASS。
- §0.3 post-step-1 tolerance self-check：PASS。
- `pytest -q tests/test_c2_b2b_envelope_transform.py tests/test_envelope_extraction.py tests/test_c2_b2_v3.py tests/test_deterministic_core.py`：**67 passed**（1 个既有 Pydantic serializer warning）。
- `pytest -q tests/test_c2_b1_cell_polygon.py tests/test_c2_b1_winding.py tests/test_kernel_guards.py tests/test_c2_vg_visibility.py`：**166 passed**。
- `pytest -q tests/test_run_manifest_v2.py tests/test_checks_reading_correction.py tests/test_geometry_kernel.py`：**88 passed**。
- `git diff --check`：PASS。B2b static tolerance grep：新 `envelope_transform.py` 无命中；`envelope.py` 唯一 `1e-9` 是 B2b 前既有 footprint span gate，未改动。
- 未运行 full pytest：按派发纪律，此环境约 30 秒杀前台；主控全量为唯一权威门。

### 定稿章节 → 测试映射

| 定稿 | 覆盖测试组 |
|---|---|
| §0.2/§0.3、§8.1/§9 | 施工前 Python assertions；`test_deterministic_core.py` required `CoreTolerances` fixtures/validation |
| §3/§4.2 | `test_c2_b2b_envelope_transform.py` marker raw JSON → `parse_reading_view` → evidence、chain closure signature/explicit tol；`test_envelope_extraction.py` overall agreement |
| §4.1、§5–§7 | `test_c2_b2b_envelope_transform.py` L-ring overall atomic transform、hard-gate audit、input non-mutation、segment fail-closed；`test_c2_b2_v3.py` v3 blanket reject removal |
| §6/§7 legacy locks | `test_c2_b2_v3.py::test_f1_legacy_polygon_envelope_rejection_is_preserved`；`test_deterministic_core.py` envelope legacy variants |
| §8.3/§8.5、§10.8/§11.15 | `test_c2_b2_v3.py` finalize/Vg post-core materialize and feature-state/release-map regressions；`test_c2_vg_visibility.py` |
| §10.7/§11.11/§11.16 | `test_c2_b1_cell_polygon.py`、`test_c2_b1_winding.py`、`test_kernel_guards.py`、`test_geometry_kernel.py`、`test_run_manifest_v2.py` targeted legacy/kernel/writer regressions |

## 预期行为变化

- v3 rectangle 与 non-rectangle 都由同一 fresh-copy envelope transaction 处理；eligible L-ring overall evidence可原子更新 ring、attached cell、bbox 与 audit。
- post-Vg segments/segment refs 送入 B2b private transaction 时 fail-closed，保留原几何并追加 rollback conflict；正常 finalize 仍在 core 后由 Vg 首次 materialize。
- exact `wing_break` extras 才进入 endpoint evidence；ordinary dimensions、note/OCR 文字不触发内部轴移动。overall agreement 的 0.05m 改由 named config 供应。
- v1/v2 legacy 继续使用原 B1 reconcile helper；v2 polygon 原文 reject 保留。

## 未决·偏离事项

1. **全量 pytest 未在本环境运行**：派发明确禁止反复全量；主控须在不受 30 秒限制环境执行 authoritative full suite。
2. §11 的穷尽故障注入/每一 hard-gate 独立负例、完整 v1/v2 × 五状态 snapshot 矩阵、U-shape multi-floor endpoint、T-junction materialization 与所有 window ambiguity fixture 未全部逐项新增；当前专项覆盖 L success、segment rollback、endpoint producer path、existing legacy/Vg/core regressions。终审应按该清单补核或要求后续补齐。

## review-ask

1. 请重点核对 `envelope_transform.py` 对复杂 T-junction/partial-edge 的 planarization 是否足够覆盖 §5.2；当前实现以 shared constant-axis intervals fail-closed，未另建显式 split graph owner。
2. 请核对 endpoint projection 的 accepted-overall in-memory extent 覆写与 `ViewProjectionFrame` 的 frame hash 口径是否与 Vg 后续 canonical serialization 完全一致。
3. 请在非受限环境跑全量 pytest，并重点审查 §11 尚未逐条显式 fixture 化的 hard-gate/fault/legacy matrix 覆盖。

---

## 返工 r1（2026-07-12）

依据主控 r1 判词 C1–C9 继续施工；返工前快照保存于 `backup/src_history/2026-07-12_b2b_envelope_transform/r1/`。未创建 commit。

### 返工改动映射

| 判词/定稿 | r1 落点与测试锁 |
|---|---|
| C1 / §5.2–§5.3 | `envelope_transform.py` 将 footprint + polygon/bbox cell 边纳入每层 constant-axis interval closure；重叠/T-junction endpoint split materialization、重复/collinear 清理、open-CCW canonicalization。`test_u_wing_break_cross_floor_moves_internal_axis_without_notch_depth_drift` 与 `test_t_junction_cell_edge_is_in_component_successfully` 均为成功提交路径。 |
| C2 / §5.4 | transform 后显式拒绝 window span/z 小于 `min_edge_length_m`、span 跨 internal wing break；`test_post_transform_window_min_width_and_wing_crossing_reject` 锁两例。 |
| C3 / §6.2、§7.4、§10–§11 | `test_each_hard_gate_rolls_back` 覆盖八个 §6.2 gate；`test_fault_injection_propagates_unexpected_and_preserves_input` 锁非预期异常零 mutation；v1/v2 × none/accepted/skipped/conflict/over-tol matrix 新增。 |
| C4 / §7.3 | `_conflict_shape` 按 window/identity/attachment → `reference_or_identity_ambiguity`，topology/ring/shared-boundary/min-edge/notch → `unsupported_geometry`+`topology_identity`；有 identity 分类测试。 |
| C5 / §4.3 | `_append_evidence_audit` 为 v3 axis skip/conflict、over-tol 和 endpoint conflict 追加 legacy 同类 `unsupported`/`conflicts` audit；有 axis conflict 测试。 |
| C6 / §4.1 | source facade 改用 envelope 的词界 facade regex，`Southeast` 子串不再误认 `South`；有拒绝测试。 |
| C7 / §4.2 | frame hash preimage 从完整 vertices 改为 canonical `projection_extent`（x/y extrema）及 frame fields。 |
| C8/C9 / §6.1、§8.4 | transaction Phase A 按 schema→evidence/intent→segment binding→window host→axis attachment 排序；生产 v3 late dispatch 调用 `_apply_envelope_reconcile` dispatcher，时序注释锁定为 canonical cell/window 后。 |

### r1 验收与测试

- `pytest -q tests/test_c2_b2b_envelope_transform.py`：**27 passed**。
- `pytest -q tests/test_c2_b2b_envelope_transform.py tests/test_envelope_extraction.py tests/test_c2_b2_v3.py tests/test_deterministic_core.py`：**91 passed**（1 个既有 Pydantic serializer warning）。
- `pytest -q tests/test_envelope_extraction.py tests/test_c2_vg_visibility.py`：**136 passed**。
- `git diff --check`：PASS；B2b static tolerance grep 仍仅命中 `envelope.py` 的既有 footprint span gate `+1e-9`，r1 新 transform 无命中。
- 未运行 full pytest；主控继续拥有 authoritative full-suite 门。

### r1 预期行为变化

- U 形内部 wing endpoint 3.00→3.10 在两层同步移动；notch-depth（cross-axis y）逐值保持，和 footprint side 共线相接的内墙/T-junction 一起移动并通过 coverage/topology gates。
- 所有 v3 evidence 非动作状态现在可审计；安全回滚 conflict 使用门语义分类而不再全部坍缩为 facade-plan mismatch。

### r1 未决·偏离事项

无新增接口或 wire 偏离。仍由主控在非 30 秒受限环境运行全量 pytest；golden/gt/case anchors 未改。

### r1 review-ask

1. 请重点核对 planar interval closure 对复杂多 owner overlap 的边界：当前按 configured attach tolerance 合并共线相接区间，垂直交叉不会传播。
2. 请核对 endpoint match 的 U 形 3.00→3.10 reconciliation delta 与 evidence matching 口径，以及 extent-only `frame_transform_hash` preimage 是否符合下游稳定性要求。
3. 请以新增 U/T 成功 fixture、八 gate rollback、window 两负例和 legacy matrix 为重点运行独立全量与逐行复核。
