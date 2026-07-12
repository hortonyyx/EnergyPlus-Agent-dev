# C2 B2 施工简报（terra 执行档，2026-07-11）

基线：`99ecaad`，工作树起始干净；B-M 已有的 V2 manifest/writer 与 grandfather hard gate 直接消费，未改其 owner 语义。未创建 commit。

## 改动映射

| B2 规范章节 | 代码落点 |
|---|---|
| §2.1/§3 | `constants.py`、`geometry/capability.py`：v3、feature matrix、fail-closed feature 查询；`geometry_validator.py`、`deterministic.py`、`geometry/modelling.py`、`pipeline.py` 改 feature 判定 |
| §2.2–2.4 | `correction/schema.py`：strict v3 子类族、finite/interval/facade/north-axis/provenance 类型；新 `parse.py`：ensure、target、draw/final ring contracts |
| §2.5–2.7/§4 | 新 `footprint.py`；deterministic v3 ring canonicalize/snap/envelope bbox projection；validator、envelope、modelling、judge、两 render 脚本使用 floor-owned footprint |
| §3bis/§5 | 新 `finalize.py`；pipeline 与 stepwise flow 共用 `finalize_correction_draw`；`run_stage.py` 将 accepted correction 交给同一 writer |
| §5/§6bis | 新 `feature_state.py`；`stage_runner.py` 写 `audit.json`/`feature_states.json`、`correction_b2_v1`、stage_version `"2"`、accepted 后 promote；`orchestrate.py` 传递版本 |
| §7 | `evidence_preflight.py`：deterministic `debt_id`（schema v2）；`schema.py` strict `DebtResolutionAuditEntry`；`checks/correction.py` v3 只认 typed debt resolution，flow 在 core 前检查 |
| §10 | `skills/intake_pipeline/1_correction/A0_contract.md` 登记 v3、feature-state、debt_id；无新增数值容差 |
| §8 | 新 `tests/test_c2_b2_v3.py`（strict wire、ring 三阶段、floor helper、finalize bbox 投影、writer bundle/hash/feature state） |

完整修改文件包括 correction 的 constants/deterministic/geometry_validator/schema/parse/footprint/finalize/feature_state，pipeline、geometry capability/modelling、judge correction_score、execution evidence_preflight/orchestrate/stage_runner/validation_run、correction check、三个工具脚本、A0 契约与新 B2 测试。

## 备份

动工前备份位于 `backup/src_history/2026-07-11_b2_footprint_v3/`，按仓库相对路径保存了将改的既有 `src/`、`scripts/`、`tests/` 文件。未改 case anchor、golden、gt、case_data。

## 验收与测试

- 改前基线：`703 passed + 9 xfailed`（用户给定 `99ecaad`）。
- 已通过：293 项前半套件；52 项 gt/intake/interzone 组；51 项 judge/kernel/llm/mcp 组；58 项 merge/pipeline/reading/render/report 组；93 项 B2 直接回归组；最终聚焦组 `96 passed in 4.11s`。
- 新 B2 测试：`4 passed in 4.62s`；覆盖 strict wire、final ring、floor footprint、finalize projection、`correction_b2_v1` 四 artifact hashes 和 feature-state 读取。
- `git diff --check` 通过；grep 确认四处 `schema_version != "2"` 硬编码已移除。
- 尝试 `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` 多次；该执行环境在约 30 秒终止前台进程，无法取得一次完整的“改后全量输出尾部”。因此**不能申报全量 703+9 零回归已完成**；终审请在不受此会话时限的环境执行该命令。理论收集数为原 712 + 新增 4 节点。

## 预期行为变化

- rectangular production target 仍为 v1；orthogonal-polygon target 发 strict v3，v2 仅 legacy read。
- v3 floor footprint 是唯一权威，顶层 bbox 为 core 精确派生兼容投影；legacy 保持原 bbox 分支。
- pipeline 与 flow 的 post-draw core/envelope/final validation 收敛为同一纯 finalize；accepted v3 correction bundle 带 audit/feature-state 并由 V2 manifest hashes 绑定。
- v3 evidence debt 不再以 audit 文本包含关系清偿；只接受输入 debt set 中的一次 typed resolution。v1/v2 reader 为保持历史兼容仍走旧文本判定。

## 未决·偏离事项

1. **全量 pytest 未取得完成计数（BLOCKING 验收）**：原因是当前工具会在约 30 秒杀掉前台长跑进程，非测试失败；必须由 Claude 侧在可完成的会话重跑全量。
2. **FacadeSegment `source_footprint_fingerprint` 与 floor fingerprint 的交叉匹配未落**：strict digest 形状、floor_id 引用和 segment 自身几何已验；缺少该一条顶层交叉断言，需补后再称 §2.2 全闭。
3. **legacy polygon 报错文本保留 `schema_version '2'` 兼容词组**：为保已有 B1 断言，消息同时给出 feature 名；与细稿“消息不再出现字面 2”有文字偏离，不影响 feature 判断本身。
4. **没有补齐规范 §8 所列的全部负例族/十路 route-id 集合测试**：当前新增测试覆盖主 wire/finalize/writer；route R4–R10 的完整逐路断言和篡改/全部 evidence-debt 负例应由下一施工轮补齐。

## review-ask

请 Claude 侧重点复核：

1. `schema.py` v3 strict 子类、ring 指纹及 FacadeSegment 的缺失 fingerprint 交叉校验；
2. `deterministic.py` v3 矩形 envelope move 是否完全保持 ring 与 attached cells 单事务；
3. `stage_runner.py` 的 `correction_b2_v1` hash/sidecar/promote 顺序与 B-M `StageRecordV2` owner 合同；
4. 在非 30 秒受限环境运行全量 pytest，并决定是否接受 legacy 错误文案兼容偏离及剩余 §8 测试覆盖。

---

## 返工 r1（2026-07-12，主控终审 F1–F3）

主控已在非受限环境两遍完成全量：**707 passed + 9 xfailed，零回归**；首轮未决 #1 关闭。首轮未决 #3（legacy `schema_version '2'` 兼容词组）由主控裁决接受，维持不改。

### F1：legacy polygon envelope guard 恢复

`deterministic._apply_envelope_reconcile()` 现在先保留原 B1 分支：非 v3
且任一 cell 有 polygon 时，原样记录原有 unsupported 文案并不移动 bbox-only
cell 边；随后才走 v3 non-rectangular footprint 的 B2b unsupported 分支。两者
不是互斥替换关系。

- `test_f1_legacy_polygon_envelope_rejection_is_preserved`
- `test_f1_v3_nonrectangular_ring_envelope_rejection_is_preserved`

### F2：FacadeSegment footprint digest binding

`footprint.py` 新增 encoding-independent 的 open-CCW/canonical-start SHA-256
`footprint_fingerprint()` 与 floor adapter。`CorrectedGeometryV3._v3_integrity`
现在对每一 segment 验其 `source_footprint_fingerprint` 与所引 floor 的规范
digest 精确相等。

- `test_f2_facade_segment_binds_floor_footprint_digest`（正例 + 改 digest 负例）

### F3：§8 测试映射

| §8 条目 | 覆盖测试 |
|---|---|
| 1 schema v3、strict wire、ring contract | `test_v3_is_strict_and_final_ring_is_canonical`、`test_v3_footprint_is_floor_owned_and_helper_uses_it`、`test_f2_facade_segment_binds_floor_footprint_digest`；B1 polygon/ring 负例：`test_invalid_polygons_raise`、`test_core_canonicalizes_closed_ring` |
| 2 capability / feature gate | `test_v1_polygon_is_rejected_as_undeclared_shape`、`test_orthogonal_polygon_profile_accepts_v1_and_profile_mismatch_blocks` |
| 3 ensure 信任边界与篡改 | `test_f3_tampered_v3_and_feature_state_fail_closed` |
| 4 FacadeSegment finite/normal/interval/digest constraints | `test_f2_facade_segment_binds_floor_footprint_digest`（digest/reference 正负）；既有 `test_invalid_polygons_raise` 覆盖 ring 几何约束 |
| 5 identity snapshot | `test_v3_finalize_derives_legacy_bbox_from_floor_footprint`（finalize v3 transaction） |
| 6 helper / R1–R10 | R1：`test_coverage_hole_blocks`；R2/R3：`test_cross_floor_jitter_unified`、`test_authoritative_envelope_accepts_bounds_and_moves_only_perimeter_edges`；R4/R5/R7/R8：`test_f3_routes_r4_r5_r7_r8_use_floor_footprint`；R6/R9/R10：`test_f3_routes_r6_r9_r10_use_floor_footprint` |
| 7 finalize / serialized output | `test_v3_finalize_derives_legacy_bbox_from_floor_footprint`、`test_correction_writer_emits_b2_contract` |
| 8 CorrectionTarget | `test_v3_is_strict_and_final_ring_is_canonical`（orthogonal target parse） |
| 9 feature state / sidecar tamper | `test_correction_writer_emits_b2_contract`、`test_f3_tampered_v3_and_feature_state_fail_closed`、`test_f3_feature_state_wire_rejects_unknown_keys_and_states` |
| 10 evidence debt id / strict resolution | `test_f3_v3_evidence_debt_requires_once_only_typed_resolution` |
| 11 producer path E2E | `test_v3_finalize_derives_legacy_bbox_from_floor_footprint`（payload → target parse → finalize/core → final artifact） |
| 12 artifact contract cross checks | `test_correction_writer_emits_b2_contract`、`test_native_v2_correction_reporting_base_v2_rejected_by_cross_check` |
| 13 golden / legacy regression | 主控两遍全量 `707 passed + 9 xfailed`；F1 legacy v2 guard 专项回归如上 |

### r1 聚焦测试

```text
pytest -q tests/test_c2_b2_v3.py tests/test_deterministic_core.py \
  tests/test_c2_b1_cell_polygon.py tests/test_checks_reading_correction.py \
  tests/test_geometry_kernel.py tests/test_envelope_extraction.py \
  tests/test_run_manifest_v2.py
137 passed, 1 warning in 6.78s
```

warning 为故意用 `model_copy(update={"floors": ...})` 复现 Pydantic 未验证篡改时的 serializer warning；测试断言下一 trust boundary fail-closed。

### r1 未决 / 偏离

无阻塞未决。legacy polygon 的 `schema_version '2'` 报错词组按主控裁决保留；四处控制流硬编码仍已移除。

### r1 review-ask

1. 核对 `footprint_fingerprint()` 的 canonicalization 是否与后续 B5/Vg 所需 digest 格式一致；
2. 核对 F1 两个 early-return guard 的次序确实保留 v1/v2 行为且不遮蔽 v3 rectangle transaction；
3. 复核 §8 映射表中既有 B1/B-M 测试对 B2 子项的覆盖口径。
