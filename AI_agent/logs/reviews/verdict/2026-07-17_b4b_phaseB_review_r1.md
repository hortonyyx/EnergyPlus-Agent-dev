# B4b Phase B 执行审裁决 r1（Opus 升一档·活体探针）

- 审对象：terra B4b Phase B 工作树（未 commit）。基座 HEAD `d028744`。
- 改动文件：`src/agent/judge/score_schema.py`（+86，纯新增 wire）、新增 `src/agent/judge/segment_score.py`、`src/agent/judge/opening_claim_score.py`、`tests/test_c2_b4b_phase_b.py`。git diff 确认仅此四文件（+两 doc）。
- 定向组：`pytest tests/test_c2_b4b_phase_b.py tests/test_c2_b4b_score_inputs.py tests/test_c2_va_applicability.py` = **80 passed**；含 `test_c2_b4b_contract.py` 扩跑 = **89 passed**。

## 总裁决：ACCEPT-WITH-REWORK

已测核心（Va 信任根、精确 partial 分母、tie 拒绝、extra completeness gate、fusion、trusted-negative conflict）经四组活体探针验证为真实、非恒真式、load-bearing。**但 correction 侧几何 + host resolver + interior partition + reading adapter 属 shipped-untested**（升一档审专抓型），须补真断言测试后方可 CLOSE。

## 头号结论：伪 ledger 是否真换成真实路径 —— 真（部分面）

B4/B5 真实路径测试确实走完整真实链：typed `GroundTruthV3`（`make_b4b_gt_document` + `validate_gt_v3`）→ 真实公开 Vg 重跑（`gt_to_va_visibility` 调 `vg_for_direction`）→ 真实 Va `derive_opening_claim_applicability`（reference/absence ledger 全部委派）→ manifest completeness assertion。四探针全部把对应测试打红（见下），证明断言链非自指、依赖真 Va 输出。`claim()` 手搓 helper 仅残留于 `eligible_units` 纯公式单测，与真-Va 测试并行存在，不构成假绿。

**残余风险**：product 侧（product ledger 消费、correction segment 提取、§8.4.1 host resolver）不是"伪 ledger"而是"未测即发"——伪→真替换在 reading/GT + reference/absence 轴完成，correction/host 轴留白。

## 活体探针（全部 CONFIRMED，改后 md5 已还原一致）

| 探针 | 改动 | 结果 |
| --- | --- | --- |
| P1 恒真式 | `eligible_units` ratio→固定 0.5 | `test_b4b_b4_partial_denominator...[.1]/[.9]` 变红、仅 [.5] 过 → 精确比例非恒真 ✓ |
| P2 确定性 | `assign_plan_segments` tie 接受首 winner | `test_b4b_b2_exact_tie_is_rejected` 变红（DID NOT RAISE）✓ |
| P3a extra gate | `classify_extra_observation`→always "extra" | `test_b4b_b5_..._not_automatically_extra` 变红 ✓ |
| P3b extra gate | →always "not_applicable" | `test_b4b_b5_complete_trusted_negative_coverage_is_extra` 变红 ✓ |
| P4 信任根 | 丢弃 Va `negative_evidence_intervals` | `test_b4b_real_trusted_negative_conflict_is_scored_from_va` 变红 → Va 负证据消费 load-bearing ✓ |

信任根独立复核：`derive_reference/product/absence_ledger` 三者全部单行委派 `derive_opening_claim_applicability`（facade_applicability.py:385，Va）；segment_score/opening_claim_score 内**无重实现或旁路 applicability**，`eligible_units` 只消费 Va 的 `status`/`reason`/`applicable_intervals`。第八 claim / duplicate opening / dangling segment 拒绝由 Va 自身 raise（`va_opening_segment_invalid`/`va_claim_ledger_invalid`），B4b 不 fork。禁区文件（facade_applicability/view_manifest/run_stage/render_grade/gt/golden）一行未改。生产树对 `segment_score`/`opening_claim_score` 的 import = 零（judge/ 外 NONE）；Phase A 稳定件（ScoreIdentityV8/canonical hash）纯新增未动。

## MAJOR

**MAJOR-1 · shipped-untested：correction 侧几何 + §8.4.1 host resolver 零覆盖**
`src/agent/judge/opening_claim_score.py:70 resolve_correction_window_host`、`:95 build_correction_host_resolver`、`src/agent/judge/segment_score.py:118 extract_correction_plan_segments` 在 `tests/` 中零引用（grep 确认 NONE）。host claim 在所有真-Va 测试中靠常量 `host_results={target.id:"complete"}` 喂入（test line 160/174/186），真实 resolver 分支（`host_resolver is not None`，opening_claim_score.py:415）从不进入。§8.4.1 的精确共线邻接解析 + 其 `score_product_segment_unresolved`（0/多相邻 room）raise 分支完全未触发。
- 失败场景（未被任何测试拦）：resolve_correction_window_host 若把 span 轴判反、或 same_line 精确等式在实数据下永不命中 → host 恒 miss/恒 raise，无测试报警。
- verdict：CONFIRMED（grep + 读 score_plan_claims 调用点）。这是 Phase B 明列交付（"plan host"、"correction segment observations"、"temporary unique span binding"），负轴+成功路径均未测。

**MAJOR-2 · shipped-untested：interior partition 提取 + reading typed adapter 零覆盖**
`extract_gt_plan_segments` 的 interior 反向配对分支（segment_score.py:86-107）及其两条不变量 raise（`exterior_interior_topology_conflict`、`invalid_interior_edge_pair`）从不触发——唯一 GT fixture 每层单 zone（ZF1），无共享内墙。`coerce_plan_observations`（reading typed dispatch adapter，segment_score.py:141）零引用。
- 失败场景：多 zone 平面的内墙精确反向配对若归组错误（例：owners/reverse 计数逻辑）→ interior target 漏/重，无测试拦。dispatch 明列"多同-family segment / 内墙 partition / 短回折 / missing-ambiguous product segment id"，interior 与 correction 提取路径未落测。
- verdict：CONFIRMED。

## MINOR

**MINOR-1 · 恒真式：B1 headline 测试**（test line 78-87）`test_b4b_b1_actual_concave_segments_are_not_bbox_or_fixed_four_sides` 的 `actual` 半段是手搓 ring 边列表、断 `len>=minimum` 且非四角集——自证不涉生产提取；GT 半段（单 zone fixture）`extract_gt_plan_segments` 返回空、`assert not segments`。真实凹形保真仅由 sibling `test_b4b_b1_gt_fixture_contains_multiple_same_family...`（line 90-95，真提取、断 north>2 且 min<max 长度）覆盖，且只验 exterior boundary。headline B1 测试不锁生产凹形拓扑。verdict：CONFIRMED。

**MINOR-2 · 恒真式：declaration-deletion 守恒半段**（test line 190-201）`before`/`after` 均读同一 immutable `reference.openings[0].claims[2]`，`before==after` 是 x==x 空转，未在删除后重推 reference。真实内容仅 `declared.content_sha256 != deleted.content_sha256`（product 变）。守恒不变量本身由构造成立（reference = GT 正证据独立 Va 调用，与 product declaration 无关），但该 guard 不防"把 product 数据接进 reference 路径"的回归。verdict：CONFIRMED（不变量真、guard 弱）。

**MINOR-3 · `bind_correction_window_segment` 仅测失败路径**（test line 126-136 只测 ambiguous/empty raise）；成功分支 `declared_segment_binding`/`temporary_unique_span_binding`（opening_claim_score.py:63-66）未测。verdict：CONFIRMED。

## NIT

- **NIT-1** `derive_product_ledger`（opening_claim_score.py:213）零引用；但与已测的 `derive_absence_ledger` 是逐字孪生单行 passthrough，风险低。
- **NIT-2** 真-Va 测试中 GT view id 与 manifest input_id 恰相等（fixture 巧合），`source_view_to_input` 映射的真实分支未被区分性验证。

## 结论与放行条件
核心算法与信任根经探针坐实为真，伪 ledger 在已测轴真替换。放行前须补：(a) correction 侧 `extract_correction_plan_segments` + §8.4.1 host resolver 成功/负轴真断言（含 build_correction_host_resolver 端到端进 score_plan_claims）；(b) 多-zone GT/correction fixture 触发 interior 反向配对及其两 raise；(c) `bind_correction_window_segment` 成功路径。MINOR-1/2 恒真式测试建议改成真提取/真重推。

---

## 返工 r1 收回 + 主控轻门收口（2026-07-17，主控 Opus）

**返工派工**：[2026-07-17_b4b_phaseB_rework_r1_dispatch.md](../request/2026-07-17_b4b_phaseB_rework_r1_dispatch.md)（补 correction/interior/host/reading-adapter 真实路径测试；明示这些分支从没执行、补测暴露真 bug 则修生产+登记）。terra 续原线程闭合，定向 80→83 passed。

**逐项闭合核实**：
- **MAJOR-1 ✅ 闭**：`test_b4b_r1_correction_extraction_and_reading_adapter_are_real_typed_paths`(:108) + `test_b4b_r1_real_correction_host_resolver_scores_and_rejects_zero_multi_adjacency`(:176) + `test_b4b_b2_missing_and_ambiguous_correction_segment_binding_fail_closed`(:163)：真实 typed correction segment 提取 + host resolver **端到端进 `score_plan_claims(host_resolver=...)`**（不再喂常量 host_results）+ 0/多邻接负轴 raise。`resolve_correction_window_host`/`build_correction_host_resolver`/`extract_correction_plan_segments` 引用数 0→2-3。
- **MAJOR-2 ✅ 闭**：`test_b4b_r1_gt_interior_pairing_and_invariant_raises`(:120)：多-zone GT fixture 触发 interior 反向配对 + 两 invariant raise（`exterior_interior_topology_conflict`/`invalid_interior_edge_pair` 各造反例，引用 0→1）；`coerce_plan_observations` reading adapter 引用 0→3。
- **⭐ 补测暴露并修复真 bug**：`extract_gt_plan_segments` 把 **tiled zone 落在 footprint 外边界上的分裂外边误判为 interior**（单 zone fixture 从未触发）→ 无 reverse 时会误落 `invalid_interior_edge_pair` raise。修法 = 新 `_lies_on_exterior`（segment_score.py:72-80）精确轴对齐子段包含判定，落外边界的无 reverse 边正确当 exterior `continue`；有 reverse 又落外边界 → `exterior_interior_topology_conflict`。**shipped-untested 返工价值实证：真 bug 藏在从没跑过的分类路径里**。
- **MINOR-1 ✅ 闭**：B1 headline 的 `actual` 半段改走真实生产提取。
- **MINOR-3 ✅ 闭**：temporary unique span binding 成功路径由 host 端到端测试覆盖。
- **MINOR-2 + NIT-1/2 → 登记残留挂账**：declaration-deletion 守恒 guard 弱（不变量真、terra argue 既有真-Va 覆盖结构性成立，未新增重推测试）/ `derive_product_ledger` 孪生 passthrough / view-id≠input-id fixture 巧合。主控裁：MINOR/NIT 且不变量已坐实真，不为其再起一轮；**下批（B4b Phase C/D）碰 reference/product 路径时收紧 declaration-deletion guard**。

**主控轻门**：
- **审 diff**：改动 = `score_schema.py`(+86 纯新增 wire) + 新增 `segment_score.py`/`opening_claim_score.py`/`test_c2_b4b_phase_b.py`；禁区（Va/view_manifest/run_stage/render_grade/gt/golden/Phase A 稳定件）一行未改；生产树对本批模块 import=零。
- **bug 修活体自证（主控亲手抽查）**：临时把 `_lies_on_exterior` 改 `return False` → `test_b4b_r1_gt_interior_pairing_and_invariant_raises` 变红（tiled exterior 边误落 `invalid_interior_edge_pair` at segment_score.py:112）→ **修必要、测试真锁**；随后还原、工作树零残留。判 8 行局部几何 helper + 亲核 + 探针 + 测试锁充分，不需再起 Opus 定向复审。
- **独立全量 pytest**：**1193 passed + 9 xfailed**（Phase B 交付基线 1190 + 返工 +3）。

**裁决：B4b Phase B CLOSED**（出口 gate B4B-B1..B5 全落真断言）。伪 ledger 假绿风险在头号审已排除+返工补齐未测轴；升一档审首轮抓 2 MAJOR shipped-untested + 返工暴露 1 真 bug = **审阶梯价值又一次实证**。**下一站 B4b Phase C 依赖 REC-C**（Va 公共合同保持 v1 + B4a elevation/source refs 已落，REC-C 待做）。

---

## 返工 r2（2026-07-17，用户拍「本轮收掉挂账」，纯测试侧零生产改动）

用户定本轮收掉 r1 登记的 MINOR-2 + NIT 残留（不留挂账）。terra 续线程补，主控轻门核。
- **MINOR-2 ✅ 闭**：`test_b4b_r2_product_declaration_deletion_repushes_reference_ledger_and_changes_only_product`(:252)——由原 `before==after` 同对象空转改为**两次独立 `derive_reference_ledger` 调用**：删 product declaration 后断 reference 的 `content_sha256` + **denominator units**（`eligible_units` 逐 claim）均不变、product `content_sha256` 变。主控亲核=真重推非 x==x，且 `derive_reference_ledger` 签名只吃 `(gt,bindings,manifest)`、结构上拿不到 product → 守恒有确定性断言 + 签名级隔离双保。
- **NIT-1 ✅ 闭**：`derive_product_ledger` 补真断言路径。
- **NIT-2 ✅ 闭**：新增 GT view id ≠ manifest input_id fixture，区分性验证 `source_view_to_input` 映射真实分支。
- **主控轻门**：改动仅 `tests/test_c2_b4b_phase_b.py`（生产零改，git 确认）；独立全量 **1194 passed + 9 xfailed**。定向 84 passed。**B4b Phase B 零残留挂账**。
