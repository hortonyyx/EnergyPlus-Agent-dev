# B5 Phase B 施工对抗审判词 r1（Fable，最高档交叉审；sol 施工）

**总裁决：REWORK（范围收窄：算法主链全部验真通过，返工项 = 补测试锁 + 5 个小修；无算法性返工）**

**计数：BLOCKER 0 / MAJOR 2 / MINOR 5 / NIT 5**

审对象 = 本批未 commit diff（window_host.py 新增 1015 行、window_sources.py（Phase A 盘内）、finalize.py、envelope_transform.py、deterministic.py、schema.py、parse.py、config.py、view_manifest.py、correction.yaml、两个新测试文件 + 6 个同步测试文件）。绑定合同 = `AI_agent/proposals/c2_b5_detail_spec.md` v3 + 派工单 `2026-07-18_b5_phaseB_construction_dispatch.md`。

活体验证：`tests/test_c2_b5_host_resolution.py` + `test_c2_b5_source_routing.py` = **67 passed**；同步相邻套件（b2_v3/b2b/deterministic/kernel_guards/b1/vg）= **239 passed**；本审自写 8 项对抗探针 = **8/8 PASS**（探针脚本在审阅 scratchpad，明细见 §3）。

---

## 1. Findings

### B5PB-01 · MAJOR · B2b（B4 时序）三条安全分支零测试锁 + 原有 B2b 拒绝测试被降级

**判据**：
- `envelope_transform.py` 新增的 dry-post 捕获边界（diff 第 571-586 行）有两条安全分支：① `WindowHostResolutionError` 全 invariant → **穿透 re-raise**（禁止回滚掩盖，原 B5-R1-01 BLOCKER 核心）；② needs_input → 转 `EnvelopeTransformRejected("correction.window_host_resolution")` → 原子回滚（spec §15.3）。仓内**两条都没有测试**。③ `_host_parity` 为 False → `correction.window_host_unique` gate 拒（spec §13.8 "B2b使room归属变化：拒/回滚"）同样零锁。
- 同批把 `tests/test_c2_b2b_envelope_transform.py::test_post_transform_window_min_width_and_wing_crossing_reject` 的两个断言改成 `failed_gate_id == "correction.window_host_resolution"`——但这两个 case **没传 marker**，现在命中的是入口 "v3 windows require verified inputs" 守卫，原 min-width / wing-crossing 的 post-transform 拒绝语义**不再被任何测试执行**（静默覆盖回归）。
- 派工单 §3："所有安全拒绝分支独立锁、负轴齐（缺一条=未交付）"；B4 是本批点名主攻面。

**活体探针结果（功能本身是对的）**：
- 探针 P4：真 marker + envelope x 4.0→3.85 使窗 span 附着后 [3.8,3.85] < min_edge → post dry-resolve `invalid_window_span` → 正确转 `EnvelopeTransformRejected`，`committed=False`、`failed_gate_id=correction.window_host_resolution`、回滚后 span 复原 [3.8,4.0]、无 segments/ref 泄漏。PASS。
- 探针 P5：篡改第二次（dry-post）transient Vg fingerprint → `direction_binding_ring_invalid` → **`WindowHostResolutionError` 穿透事务未被回滚吞掉**，全 rows `direction_binding_invalid + invariant_no_geometry_commit`。PASS。

**修法**：把探针 P4/P5 落成正式测试（带 marker 的 post-transform needs_input 回滚 + invariant 穿透各一），补 `_host_parity` False 的几何 fixture（transform 改 room 归属→gate 拒），并恢复 min-width / wing-crossing 两个 case 的带 marker 版本。纯加测试，不动实现。

### B5PB-02 · MAJOR · resolver/commit/evidence 侧 9 条安全拒绝分支 shipped-untested

**判据**（`grep` 全 tests/ 逐 reason code 清点）：以下已实现分支 0 个测试引用：
1. `elevation_segment_not_visible`（SRC-E3，window_host.py:564）；
2. `facade_mismatch`（SRC-E4 resolver 腿，window_host.py:499-501 KeyError 分支；注：verifier 侧没实现 §4.4.8 的"elevation family 与 window facade 一致"检查，resolver 这条是唯一防线——**必须有锁**）；
3. `source_channel_missing`（SRC-I1，window_host.py:472）；
4. `invalid_host_line`（resolver 腿：denom==0 / t 越界，window_host.py:607-616；LINE 系其余归 Phase C）；
5. `resolver_output_tampered`（`apply_window_host_resolutions` 的原子提交防篡改门，window_host.py:669-677）；
6. VA-ERR6（`map_va_applicability_error` existence 漂移→`va_identity_invalid`，window_host.py:729-731）；
7. VA-ID2 derive 腿（`derive_window_evidence_ledger` 对过期 identity 的 `_identity_conflicts` 拒绝，window_host.py:866-873）；
8. NEG-7（product 自报不改 Va decision）；
9. NEG-8（同 source positive+negative 矛盾——分析结论：现 wire 下负证据全由 manifest coverage + positive 缺席派生，矛盾**结构上不可表达**（positive 恒 outcome="positive"），测试应锁这个不可表达性而非期望一个 reject 分支）。

**活体探针结果**：P2b（duck-typed 过期 identity → 全 rows `va_identity_invalid + invariant`）PASS；P3（VA-ERR6 → `va_identity_invalid + invariant`，upstream code 保留）PASS；P6（篡改 claims 一条 span 后重签自洽 hash → commit 仍拒 `resolver_output_tampered`，证明"hash 自洽≠关系可信"）PASS。即被探针覆盖的分支功能全对，缺的是仓内锁。

**修法**：逐条补独立测试（每 code 一个 test，不参数化成一次总失败）；NEG-7/NEG-8 按上述口径落锁。

### B5PB-03 · MINOR · `run_envelope_hard_gates` 的 `window_host_ok: bool = True` 是 fail-open 默认值

事务内调用恒传计算值，但该函数是模块级公开签名；漏传参数的未来调用方会得到恒过的 window-host gate。修法：去默认值（required kw）。

### B5PB-04 · MINOR · `test_c2_b2_v3.py` 的 core 篡改 window floor_id 不变量覆盖丢失

原 `test_finalize_raises_if_core_mutates_window_floor_reference` 断 `"finalize invariant"`，现改断 marker 缺失的 `source_identity_invalid`——`_identity_snapshot` 不变量对**带窗 v3** 的覆盖没了（注释声称"由 Phase-B resolver 测试覆盖"，两个新文件里**并无** marker+tamper-core 的等价测试）。修法：补一个带 marker + monkeypatch core 篡改 floor_id 的版本，断 `finalize invariant`。

### B5PB-05 · MINOR · plan 分支 plane filter 是 spec §6.3 未记载的候选过滤器

`_plan_source_matches_plane`（window_host.py:435-438、510-513）用 plan source 的横轴 interval 过滤同 family 不同 plane 的段。它是 evidence-driven（非 center 猜）、是 U 形凹多边形 hidden fixture（B5-B1 gate）可行的关键、且 `test_geo_multiple_overlapping_segment_candidates` 锁了"plane interval 盖两段→multiple 拒"。但：① spec §6.3 候选规则没有这条，属于合同外行为；② 它在 cross-segment 检查**之前**收窄候选——异 plane 双段被过滤后，理论上可把 `cross_segment_boundary` 事实降级成 `segment_endpoint_overrun`（同为 BLOCK，无 fail-open，但诊断优先级 §7.1#3 被绕）。修法：回写 spec/A0 记载该过滤器语义 + 加"共面双段 plane filter 不掩盖 cross_segment"锁。

### B5PB-06 · MINOR · `phase` 被 mapper 接收后丢弃，§5.2 checks.json companion 证据无从取材

`map_direction_binding_error` 签名带 `phase` 但产出的 conflict/异常均不携带；`WindowHostResolutionError` 也不带。spec §5.2："checks.json companion evidence 保留 phase 与完整 strict context"。Phase D writer 写 rejected attempt 时将拿不到 phase。修法：在 `WindowHostResolutionError` 上带 `(phase, context)` 伴随证据（不进 conflict wire，进 checks evidence）。

### B5PB-07 · MINOR · `FinalizeResult` 未强制 v1/v2 B5 四字段为 None

`finalize_correction_draw` 对 v1/v2 输入若被误传 `verified_window_inputs`，会原样透传进 `FinalizeResult.verified_window_resolver_inputs`（其余三个为 None），违反 spec §9.1 "v1/v2 全部 B5 字段必须 None"。现无此 caller，但没锁。修法：v1/v2 + marker 非 None → 直接 raise，加锁。

### NIT 清单

- **B5PB-08**：`_room_intervals` 的碎边 merge 间隙与最小宽度用 `window_host_plane_epsilon_m`，spec §6.4.3 说 merge 用 span epsilon。当前两值同为 1e-9 无数值差，改配置会漂移。对齐为 span epsilon。
- **B5PB-09**：dry-post 捕获用 `all(invariant)` 判穿透；现各 raise 点 rows 同质（核对过：prefilled-ref/identity 全 invariant，几何冲突全 needs_input），但混合时 invariant 会被回滚掩盖。防御性改 `any(...)` 穿透。
- **B5PB-10**：`map_va_applicability_error` 的 fallback 分支在 `host_claims.resolutions` 为空时返回空 tuple，违反"`WindowHostResolutionError` 必须携带 typed rows"（当前仅零窗可达，基本不可达）。
- **B5PB-11**：audit `original_span` 是 post-snap 值而非 producer 原值（test 断 -0.006→-0.01）。Phase D writer 按 §6.1 用 producer bytes 验 original_span 时需 snap replay——建议现在就把口径钉进 spec/注释，免 Phase D 争议。
- **B5PB-12**：`derive_window_evidence_ledger` 的 `candidate_identity` 参数无类型标注；duck-typed 对象可绕过 `PreparedCandidateIdentity.__post_init__` 的 feature-artifact↔output-hash 交叉绑定（derive 内只查 bytes 相等 + hash-of-bytes；探针 P2b 证明 output 侧被字节比对兜住，feature 侧交叉绑定只在构造器）。标注类型即可。

---

## 2. 正面验真清单（已核实，sol 无须重证）

1. **trusted-negative §7.3 无过火**（本批最高危，B4b Phase C 教训）：八条件逐条落地——①`bool(positive_channels)`（且要求 Va applicable 非空=已核验）②`entry.view_type not in positive_channels`（通道级排除，双向对称）③manifest `negative_evidence_capable_claims` 含 existence ④coverage/assertion 成对+id 闭合（B5 查闭合；frame/region 值域由 manifest schema `_FRAME_REGION_PAIRS` + Va 侧 `expected_coverage` 双重强制，错配→`va_claim_ledger_invalid` 升 invariant，fail-closed 不 fail-open）⑤per-source `not positive` ⑥`_canonical_union`+`_covers` 全覆盖判定，残差 span epsilon ⑦**Va 的 elevation negative intervals 生成时已与 Vg visible 相交**（facade_applicability.py:483，hidden 部分天然不满足覆盖）⑧completeness 只出自 manifest。NEG-1/2/4/5/6/9 全有仓内锁；uncorroborated 分支窗**不删、正常挂载**逐一断言。NEG-3 由 manifest 层既有测试（test_view_manifest_schema `test_negative_dangling_assertion_id`）覆盖。探针 P1（同通道第二立面视图携完整性承诺→不 conflict）PASS。**未发现任何过火路径**；Va↔B5 relevance 口径不一致时统一降级 uncorroborated（fail-safe 方向正确）。
2. **信任根**：`PreparedCandidateIdentity.__post_init__` 三重自检（output bytes↔hash、feature bytes↔hash、feature artifact 内嵌 output_sha256 交叉绑定）；finalize 步骤 9 用 `model_dump_json(indent=2)` 预序列化——与 writer（stage_runner.py:186 同一约定）逐字节同源，B5-B7 测试锁 bytes 相等；`derive_window_evidence_ledger` 重序列化比对 bytes；占位 64-hex 三处构造均不可能（constructor 两条 placeholder 拒例 + 探针 P2a/P2b）。evidence ledger 的 output/feature/resolver/manifest/segments/bindings/va 七 hash 全真值,decision/aggregate/content 三层 hash 自校验 + 三个独立篡改拒例。
3. **B4 时序**：spy 测试实证 dry-pre ≠ dry-post/final 的 fingerprint+frame hash（`test_b5_b4_b2b_rederives...` 恰 2 次、`test_finalize_calls_binding_on_dry_pre_dry_post_and_final...` ≥5 次且 transform 后全一致）；`_dry_resolve_current_ring` 每轮 fresh `materialize_all_facade_segments` + deep-copy 一次性 dry_geom；事务后 `facade_segments == []` 且 ref 全 None（无 stale id/binding 泄漏）；`_host_parity` 比较 (floor,room,branch,family) **刻意不含 segment id**（transient id 不跨 ring，正确）；无 intent 早退在 dry-resolve 之前（§13.8 "无 intent 不多做"）；helper 无缓存、resolver 无 `segments_override`。
4. **两支边界（B1/B2）**：B1 = 真凹 U-ring East 双段（x=10 可见 / x=3 Vg 实证 hidden，`visible_intervals==[]` 先断言）plan 挂 hidden 段、`visible_overlap_intervals=()`；B2 = elevation 只 visible 段、完整 span 落唯一 room interval 才补 room、`facade_segment_id != room_id` 断言；elevation 预填错 room→`room_mismatch` 拒不覆写。
5. **B3 不按中心猜**：cross_segment（L-ring 中心对称双段）/cross_room（plan+elevation 双参数）/multiple_segment/multiple_room/cell-bbox-不可替代-真边界 全锁；实现无任何 min-distance/contains(center)/id 破局路径（人工扫全模块证实）。
6. **时序总排布**符合 §3.2 步骤 1-11 的 Phase B 份额：strict parse（raw payload 预检 producer 预填两 code）→ marker↔draw 字节绑定（`producer_draw_canonical_bytes` 相等否则拒）→ v3 窗 pre-host 只 snap+floor-z-clamp（禁 cell bbox clamp、禁提前删窗、audit 仅真 delta）→ B2b（内含 dry-pre/dry-post）→ final Vg 首次持久化 → final resolve（helper 现场重派生 binding）→ `apply_window_host_resolutions` 纯重算比对后一次 commit（room/ref/span/strict audit）→ validate → 步骤 9 identity → evidence sidecar（Va 不再改 output/audit——ledger 在 output bytes 冻结之后派生，hash 环确实解开）。三处 `WindowDirectionBindingError` 捕获全窄型+`map_direction_binding_error`（finalize 两处 phase="final"、transform 两处 dry_pre/dry_post）。
7. **v1/v2 legacy 不变**：deterministic.py 仅 v3 早退分支，legacy window pass 逐行未动；239 个相邻/回归测试全绿；`window_clamp_to_parent` 注释改为 legacy-only（语义未变）。
8. **零越界**：geometry/modelling.py、specs、validator、judge、manifest.py、stage_runner、loader、E4 全未触碰；`window_verts_on_line`/`SegmentLine2D` 未提前实现（record 顶点由 resolver 内联 lerp 产出，属 §5.1 record 义务）；view_manifest 的 floor_ref 连续性检查属 §4.4.7 B-M 合同登记，在界内。
9. **无 fail-open**：全模块 except 清单逐条核过，全窄型+typed 转换；`run_envelope_hard_gates` 的 `except Exception` 还收窄成了 `ValueError`；`map_va_applicability_error` 未知 code → RuntimeError INVARIANT（有锁）。
10. **容差**：三项 required 无默认、次序关系 validate（plane ≤ span < clamp ≤ min_edge）、A0 表+登记段落齐；测试锁 TypeError 缺参与关系违反。
11. **负轴（P7 探针）**：East 段 p1→p2 参数化端点与 t 序一致、不被世界升序 sort 破坏。PASS。
12. **hash 纪律**：空集 `[]` 冻结向量 `4f53cda1...` 与 spec 一致且测试用手写字面量；locator 冻结向量逐字节手写、变一字节即变锁。

## 3. 探针记录

脚本：审阅 scratchpad `b5pb_probes.py`（复用被审 fixture builder，可直接移植为正式测试）。P1 同通道完整性承诺不过火 / P2a 构造器交叉绑定 / P2b derive 拒过期 identity / P3 VA-ERR6 漂移 / P4 B2b post 冲突原子回滚 / P5 dry-post invariant 穿透回滚 / P6 commit 防篡改 / P7 负轴端点序 = **8/8 PASS**。

## 4. 裁决理由

主链算法、trusted-negative 纪律、信任根、B4 时序、越界纪律全部验真为正确——本批**没有功能性缺陷**被找到（12 项对抗面 + 8 探针全过）。判 REWORK 的唯一依据是派工单硬合同"所有安全拒绝分支独立锁、缺一条=未交付"：两个 MAJOR 合计 12+ 条安全分支/回归锁缺席，其中 B2b 三分支恰是本批点名主攻的原 B5-R1-01 核心。返工范围明确：补测试（可直接移植探针）+ 5 个 MINOR 小修，无算法改动，预期一轮可闭。
