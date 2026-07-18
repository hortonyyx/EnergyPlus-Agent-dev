# B5 Phase C 施工对抗审 r2（返工复验，Fable）

- 日期：2026-07-18
- 审者：Fable 5（r1 REWORK 同一审者；施工者 sol/GPT 侧，跨厂商，谁写谁不批）
- 对象：sol 返工 = 纯补测试锁（`tests/test_c2_b5_parent_and_verts.py` 781→1126 行，32→52 tests）+ NIT-2 单行生产码改动
- 前序：r1 REWORK（0 BLOCKER / 2 MAJOR〔两簇安全拒绝分支缺锁〕/ 2 MINOR / 4 NIT），判词 `2026-07-18_b5_phaseC_review_r1.md`
- 返工派工单：`AI_agent/logs/reviews/request/2026-07-18_b5_phaseC_rework_r1_dispatch.md`

---

## VERDICT: **APPROVE**

17 条编号拒绝分支**全部 CLOSED**（逐条独立测试 + 断言精确到 message/code/context 字面量），NIT-1 两变体、NIT-2 属性直取均落；**新做 4 轮活体探针 7 个测试全部变红**（锁全是活的）；**除派工单允许的 NIT-2 单行外零生产码改动**（实证见下）；MINOR-1/2、NIT-3/4 确认未被顺手动（按纪律归 Phase D）。targeted 140 passed + 邻接 b4b 76 + kernel/correction/b1/naming 139 全绿零回归。**新洞：0。**

---

## 17 条逐条闭合核查（编号对应返工派工单）

| # | 应锁分支 | 落点（tests/test_c2_b5_parent_and_verts.py） | 判定 |
|---|---|---|---|
| ① | kernel `c2_b5_v1` + proof=None → fail（反软接线门） | `test_kernel_b5_contract_without_proof_fails_closed`:636，断精确 message | **CLOSED**（探针 P5 红）|
| ② | kernel legacy + proof → fail | `test_kernel_legacy_contract_with_b5_proof_fails_closed`:645 | **CLOSED** |
| ③ | kernel unknown contract → fail | `test_kernel_unknown_geometry_contract_fails_closed`:652 | **CLOSED** |
| ④ | kernel invalid proof artifact bytes → fail | `test_kernel_invalid_b5_artifact_bytes_fail_closed`:660（`object.__setattr__` 注坏 bytes，正当攻击构造） | **CLOSED** |
| ⑤ | kernel unsupported proof type → fail | `test_kernel_unsupported_b5_proof_type_fails_closed`:670 | **CLOSED** |
| ⑥ | validator conflicts 含 `window_host_conflict` → block（spec §10.1 点名） | `test_correction_validator_blocks_window_host_conflict_row`:679，断 message+conflicts 回显 | **CLOSED**（探针 P8 红）|
| ⑦ | validator evidence wire 型错 → fail | `test_correction_validator_rejects_wrong_evidence_wire_type`:698 | **CLOSED** |
| ⑧ | validator artifact evidence ≠ 传入 evidence → fail | `test_correction_validator_rejects_evidence_different_from_proof_artifact`:709（重签 content hash 证明「hash 自洽仍拒」）| **CLOSED** |
| ⑨ | specs 显式 contract ≠ bg contract → raise | `test_serializer_rejects_contract_different_from_built_geometry`:758 | **CLOSED** |
| ⑩ | `c2_b5_v1` 窗缺三身份 → raise（两处各一） | `test_building_geometry_dict_rejects...`:767 + `test_serialize_geometry_rejects...`:788 | **CLOSED ×2** |
| ⑪ | build legacy + proof → raise | `test_build_geometry_rejects_legacy_input_with_b5_proof`:809（schema v1 geom + 真 proof）| **CLOSED** |
| ⑫ | artifact output 身份 cross-check | `test_window_hosts_artifact_rejects_output_identity_mismatch`:824（重签 content 后仍拒）| **CLOSED**（探针 P6 红）|
| ⑬ | artifact claims·evidence window id 精确相等 | `test_..._claim_evidence_window_id_mismatch`:838（decision→aggregate→content→artifact 全链重签仍拒）| **CLOSED**（P6 红）|
| ⑭ | artifact 三 identity hash 一致 | `test_..._claim_evidence_identity_hash_mismatch`:863（同上全链重签）| **CLOSED**（P6 红）|
| ⑮ | judge `b5_output_hash_mismatch` | `test_judge_rejects_verified_output_hash_different_from_product_identity`:1032，断 code+context 字面量 | **CLOSED**（探针 P7 红）|
| ⑯ | judge `b5_product_payload_differs_from_verified_output` | `test_judge_rejects_payload_different_from_verified_output`:1054 | **CLOSED**（P7 红）|
| ⑰ | attach source↔resolution totality → `resolver_output_tampered` | `test_attach_windows_v3_rejects_source_resolution_totality_mismatch`:881，断 code+完整 context dict | **CLOSED** |

**NIT-1**：LINE-6 t>1 → `test_line_6_parameter_interval_above_one_rejected`:368 ✅；LINE-8 (0,0) normal → `test_line_8_zero_wire_normal_rejected`:430 ✅。
**NIT-2**：`score_schema.py:build_product_identity` 已改 `accepted_stage_record.artifact_contract` 直取（diff 核实，getattr 已除）✅。

## 无假绿核查

- 每分支**独立测试函数**，`parametrize` 计数 = 0，无「一次调用断总失败」合并；
- 断言全为**精确字面量**（error message / conflict code / context dict / status），非仅「raises」；
- 无 `x != x` 恒真伪检查（grep 核实）；
- 攻击 fixture 用 `canonical_sha256` **重签下游 hash 构造「自洽但语义错」的输入**（⑧⑫⑬⑭），这是正当攻击构造、非「生成 expected 自比」——恰好证明 cross-check 是语义门不是 hash 门；
- r1 既有冻结字面量（SOUTH_SEGMENT_ID / SOUTH_RESOLUTION_SHA256 / LINE 系列 / 空几何 frozen bytes）原样保留。

## 零算法改动核查

- `git diff HEAD --stat` 与 r1 逐文件完全一致（13 文件 +1285/−54）；
- **强证据**：本轮 4 个探针的 `Edit old_string` 全部取自 r1 审读时的生产码原文，跨 4 个文件（kernel.py / window_host.py / score_service.py / geometry_validator.py）**全部一次精确匹配**——这些关键段与 r1 一字未变；
- 另抽查 `resolve_window_hosts` 负轴 t 段、`_v3_parent_candidates` normal 分量残差段、kernel verts 等值段 grep 逐行一致；
- 唯一生产码语义变化 = score_schema.py NIT-2 单行（派工单明示允许）。

## Phase D 延后项未被顺手动（确认）

- MINOR-1：`build.py:97` / `geometry_validator.py:326` 两处 `producer_draw_canonical_bytes=b""` 裸构造仍在（Phase D 收口）✓；
- MINOR-2：`pipeline.py:743` build 无 proof、`pipeline.py:1144` check_kernel 无 proof 仍在（Phase D 接线）✓；
- NIT-3（序列化口径共享 helper）、NIT-4（带窗 legacy frozen-byte fixture）未动 ✓。

## 活体探针清单（本轮 4 轮，全部已回滚）

| # | 改坏点 | 预期红 | 结果 |
|---|---|---|---|
| P5 | kernel proof=None fail 改 NOT_APPLICABLE | ① | **1 failed** ✅ |
| P6 | `WindowHostsArtifactV1._hash` 三条 cross-check 全删 | ⑫⑬⑭ | **3 failed** ✅ |
| P7 | judge output-hash + payload 两分支全删 | ⑮⑯ | **2 failed** ✅ |
| P8 | validator conflicts block 改恒 False | ⑥ | **1 failed** ✅ |

回滚后干净态：`git diff --stat` 恢复 +1285/−54；**targeted 140 passed**（sol 自报 140 ✓）；b4b 5 文件 **76 passed**；kernel/correction/pipeline/b1/naming 9 文件 **139 passed**。累计两轮探针 8 轮 15 个测试全按预期变红，零假绿证据。

---

**总评**：返工精准——17+2+1 全部落点、锁真实有效、零算法漂移、零新洞；r1 的 MAJOR-1/2 全部闭合，MINOR-1/2、NIT-3/4 按纪律留 Phase D（已登记，Phase D 派工单须显式列 pipeline/check_kernel proof 接线与 marker 收口）。**B5 Phase C 达 APPROVE，可进主控轻门（独立全量 pytest + 亲核）。**
