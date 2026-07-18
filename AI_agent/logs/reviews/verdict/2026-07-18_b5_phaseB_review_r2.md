# B5 Phase B 返工窄增量复核 r2（Fable，对抗审；sol 施工）

**总裁决：APPROVE**

**闭合：12/12（2 MAJOR + 5 MINOR + 5 NIT 全 closed）· 未闭 0 · 新洞 0**

范围 = 只复核 r1 的 12 条返工点（未重跑完整对抗审）。验证 = targeted **327 passed**（复现 sol 报数）+ 我 r1 的 8 项独立对抗探针**重跑 8/8 PASS 无回归** + 逐条比对返工测试的 reject 语义与源码支撑。

---

## 1. 两个 MAJOR（真锁验证）

### B5PB-01 · CLOSED · B2b 三分支 + 恢复 min-width/wing
- `test_b2b_post_resolver_needs_input_rolls_back_without_state_leakage`（host_resolution.py:637）：真 marker、envelope 4.0→3.85 使满高窗吃满 post-transform 面→**post-ring resolver** 报 `invalid_window_span`→转 `EnvelopeTransformRejected("correction.window_host_resolution")` 原子回滚。断 `not committed` + gate 正确 + span 复原 [0,3.85] + 无 segment_id/facade_segments + **无 window_host_resolution audit 行** + conflict evidence reason=invalid_window_span + **输入 geom 字节不变**（before==after）。非 marker-guard，真 post-transform reject。
- `test_b2b_dry_post_ring_fingerprint_invariant_pierces_transaction`（:663）：篡改第 2 次（dry-post）ring fingerprint→`WindowHostResolutionError` **穿透事务未被回滚吞掉**，断 calls==2 / upstream=ring_invalid / invariant fallback / **`exc.phase=="dry_post_transform"`** / context 非空 / geom 不变。原 B5-R1-01 核心真锁。
- `test_b2b_geometry_room_ownership_change_fails_host_parity_and_rolls_back`（:699）：U-ring elevation 窗近 wing、wing 移 3.2 改 room 归属→`_host_parity` False→`window_host_unique` gate 拒回滚，断 room=None / 无 segment / footprint 复原 / 冲突文案。
- 恢复 min-width/wing（`test_c2_b2b_envelope_transform.py:146` + `_with_plan_marker` 建真 plan marker）：断 `failed_gate_id=="correction.window_host_unique"` **且** 命中 `falls below min_edge_length_m` / `window span crosses wing break` 真文案——是带 marker 通过入口守卫后的真 post-transform 物理拒绝，非守卫短路。

### B5PB-02 · CLOSED · 9 条独立安全分支锁
逐条独立 test、各断自身 reason code（非参数化总失败、非自指）：`resolver_output_tampered`(:298，用 test-local `independent_sha256` 重签自洽后 commit 仍拒，坐实"hash 自洽≠关系可信")、`elevation_segment_not_visible`(:451)、`facade_mismatch`(:484，新 `source_facade` 参数使 elevation binding family≠window facade→resolver KeyError 腿)、`source_channel_missing`(:495)、`invalid_host_line`(:508，退化 p2==p1)、VA-ERR6 existence 漂移 derive 腿(:1107，断 va_identity_invalid+invariant+phase=final)、VA-ID2 stale identity derive 腿(:1137)、NEG-7 product 自报(:1155)、NEG-8 同源 positive+negative(:1177，锁"结构不可表达"= `NegativeEvidenceDecisionV1` validator 拒)。

## 2. 5 MINOR + 5 NIT（真落地验证）

- **B5PB-03** CLOSED：`run_envelope_hard_gates` 的 `window_host_ok` 默认值移除，signature lock(:725) 断 `default is Parameter.empty`。
- **B5PB-04** CLOSED：marker-backed monkeypatch core 篡改 floor_id→`test_finalize_marker_backed_core_floor_reference_tamper_hits_identity_invariant`(:922) 断 `finalize invariant`，snapshot 不变量对带窗 v3 的覆盖恢复。
- **B5PB-05** CLOSED：plane filter 累计式写入 spec §6.3（全文散文，非"vN 不变"引用）+ A0；源码 `_plan_source_matches_plane` 用 source 垂直 interval 认 plane、**共面段全保留**；`test_plan_plane_filter_keeps_coplanar_segments_for_cross_segment_rejection`(:413) 拆同面双段验 `cross_segment_boundary` 不被掩盖。
- **B5PB-06** CLOSED：`WindowHostResolutionError` 带 `phase`/`context`（conflict wire 保持冻结、companion 在异常侧）；三 raise 点全接线（finalize final×2、`_dry_resolve_current_ring` dry-pre/dry-post 传 `phase=phase, context=exc.context`）；:663/:872/:898/:1107 断 `exc.phase`。
- **B5PB-07** CLOSED：finalize 入口 `raise ValueError("legacy v1/v2 finalize forbids verified_window_inputs")`；v1(:946)+v2(:964) 误传 marker 各一锁。
- **B5PB-08** CLOSED：`_room_intervals` 拆 `plane_eps`/`span_eps` 双参、merge/最小宽用 `span_eps`；`test_room_interval_merge_receives_span_epsilon_not_plane_epsilon`(:777) spy 断 caller 传 `(1e-10, 1e-9)`——真语义修正非表面改名。
- **B5PB-09** CLOSED：dry-post 捕获 `all(...)`→`any(row.fallback_action=="invariant..." ): raise`；`test_b2b_mixed_post_conflicts_pierce_when_any_row_is_invariant`(:731) 混合(needs_input+invariant)锁穿透。
- **B5PB-10** CLOSED：`map_va_applicability_error` 空 resolutions→`RuntimeError INVARIANT`（非返回空 tuple）；`WindowHostResolutionError.__init__` 也拒空 conflicts；:1321 锁。
- **B5PB-11** CLOSED：original_span=resolver 入口 post-snap 口径钉进 spec §5.3(line 700 举 -0.006→-0.01 例)+ A0，Phase D writer replay snap 比对的义务写明。
- **B5PB-12** CLOSED：`candidate_identity: PreparedCandidateIdentity` 具体标注（`TYPE_CHECKING` 导入避免 finalize↔window_host 循环，`from __future__ annotations` 下运行期为字符串）；:1334 锁。

## 3. 新洞扫描（0）
- 自指假绿：host_resolution 测试**零**调用 production `canonical_sha256`/`_frame_hash`/`_facade_segments_sha256` 生成 expected（`independent_sha256` 为 test-local，符 §13.6）。
- 弱断言/恒真：无 `x!=x`/`assert True`/裸 pass。
- fail-open：rework 三源文件（window_host/envelope_transform/finalize）**零** `except Exception`/裸 `except`。
- 累计自包含：spec §6.3/§5.3 均为全文散文，无覆写正文的"vN 不变"引用违规。
- 循环导入：window_host 对 `PreparedCandidateIdentity` 仅 `TYPE_CHECKING` 导入，无运行期 cycle（327 绿实证）。

## 4. 裁决
r1 的 12 条全部真闭：两 MAJOR 补锁均断到真 reject 语义（非降级守卫、非参数化总失败），源码层有对应改动支撑（非纯测试）；10 条 MINOR/NIT 逐条落实且含语义锁。无算法改动，无新洞，r1 已验真的算法主链/trusted-negative 纪律/信任根/B4 时序不受影响（8 探针无回归）。**可 CLOSED**——主控做全量轻门收口。
