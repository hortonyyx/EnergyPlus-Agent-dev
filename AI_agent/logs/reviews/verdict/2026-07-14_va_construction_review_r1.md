# Va 批施工执行审判词 r1（2026-07-14）

- **审向**：Opus 次高档执行审（升一档交叉，GPT 侧 terra 施工 → Claude 侧审，谁写谁不批）→ 主控轻门。
- **需求基准**：`AI_agent/proposals/c2_va_detail_spec.md`（v2 定稿，唯一施工合同）+ 派单 `AI_agent/logs/reviews/request/2026-07-14_va_construction_dispatch.md`。
- **审的产物**：
  - 新 `src/agent/correction/facade_applicability.py`
  - 新 `tests/test_c2_va_applicability.py`（14 test ID）
  - 改 `skills/intake_pipeline/1_correction/A0_contract.md`（+18）
- **信任边界**：仅依据合同原文、代码/测试实体、本审自跑测试输出下判断；施工简报仅用于改动映射定位，其自述结论不作证据。

---

## 总裁决：REWORK

核代码质量高（正向 applicability、plan bypass、elevation intersection、canonical hash、identity、VA-R2/R3 均正确落地，定向 suite 240 全绿），但触发 REWORK 的两条：

1. **VA-C1（MAJOR，真 bug）**：负证据源枚举的 elevation family 过滤是恒真式，违反合同 §6.2，多立面场景下把外立面误当任一 opening 的负证据源——被单立面 fixture 掩盖。
2. **VA-C2（MAJOR，§14 硬验收未达）**：合同 §11「测试族(累计全量)」是 §14 硬验收门（"§11 全测试...通过"），实际 31 条编号需求约 14 条整条缺失、多条仅正例/部分覆盖；整个负证据轴与 true_azimuth/unknown 轴 shipped-untested（VA-C1 就住在其中一条未测路径里）。施工简报把这些说成"留给独立审查"，是把未竟当成审查任务的披露纪律偏差。

核结构完好，返工有界：修 family 过滤 + 补齐缺失测试族（尤其负证据、true_azimuth/unknown、方向矩阵、多 source union、B4b seam、property oracle）。

**severity 计数**：BLOCKER 0 · MAJOR 2 · MINOR 1 · NIT 2。

---

## 逐条 findings

### VA-C1 —— MAJOR：负证据 elevation family 过滤恒真，违反 §6.2/§3.1.5

`src/agent/correction/facade_applicability.py:362-363`
```python
def _relevant_negative(entry, opening, family):
    return (entry.view_type == "plan" and entry.floor_ref == opening.floor_ref) \
        or (entry.view_type == "elevation" and family == opening.facade_family)
```
调用点 `:407`：`_relevant_negative(e, opening, opening.facade_family)` —— `family` 实参恒等于 `opening.facade_family`，故 elevation 分支的 `family == opening.facade_family` **恒为真**。本审直跑坐实：一个 South opening 对 East/North 立面 entry 均返回 True（应为 False）。

合同 §6.2 明文：`elevation + resolved family matches`（该 elevation 的 **resolved family** 须等于 opening family），应比 `bindings[entry.input_id].resolved_building_direction == opening.facade_family`，而非拿 opening 自身 family 与自身比。§3.1.5 同旨。

**影响**：多立面楼（C2 的正题，sm26 等）里任何带 completeness assertion 的立面都会被枚举成**每个** opening 的负证据源，产生：外立面 input_id 的 spurious `SourceEvidenceDecisionV1`、错误的 `completeness_assertion_id`、被污染的 `considered_source_view_ids`、同一 opening 多条重复负 decision。所幸 negative_intervals 数值仍取自 opening 自己的 target segment visibility（数值有界），且负-only decision 不贡献正向 coverage，故 **status/reason 不受影响**——腐蚀限于负证据审计归属与多重性。定级 MAJOR（非 BLOCKER：不崩、不污染主输出 applicability；但直接违反冻结合同条款，且下游 B4b 会据此误判 conflict/miss）。正向 elevation 分支（`:404`）family 过滤是对的，仅负-only 路径漏了。

### VA-C2 —— MAJOR：§11 测试族对 §14 硬验收未达，且披露纪律偏差

合同 §10 定 `tests/test_c2_va_applicability.py = §11 全量 Va 测试`；§14 验收 = "§11 全测试与全量 suite 通过"；§13 步骤 8 明列 strict/hidden-partial/sm26/direction/pure-property 各族。实际落地 14 test ID 覆盖约 31 编号需求中不到六成（明细见文末对账表）：**整条缺失**含 item 4/7（方向 4×2×2 矩阵仅 1 格）/9（true_azimuth/unknown 全路径）/11/16/18（负证据 capability 全轴）/20/21（sm26）/22/23/24（B4b seam）/27（property oracle）/29。整个负证据机制与 true_azimuth/unknown 分支 shipped-untested——若 item 18 有测试，VA-C1 本会被抓出。

施工简报"未决"节写"其余矩阵型扩展案例留给独立审查按合同逐项核验"，既非逐条列明，亦把**未竟施工**表述为**审查任务**（审者职责是复核不是补测）。派单纪律原文"稿内测试族全数落地,确有未竟逐条列明,不得静默"——本审裁定：构成实质未竟，且披露不合格。这是 §14 硬门未达，故进 REWORK 而非 APPROVE-WITH-CHANGES。

### VA-C3 —— MINOR：`facade_segments_sha256` preimage 合同未冻结（review-ask #1 裁决）

`:281-287,312-314` Va 把 preimage 定为「每 segment 全量 `FacadeSegment.model_dump(mode="json")`，按 `(floor_id, family_rank, along.lo, along.hi, depth, id)` 排序后的 JSON list，compact sort_keys SHA-256」。全仓 grep 确认**无既有外部生产者**（仅合同与 Va 自身），故本批**自洽**（测试用同一 `_segment_payload` 构造 ledger，identity 门自证）。但合同 §3.1.3 只冻结了**排序键**，未冻结**每 segment 字节内容**（对比 §3.2.6 对 frame preimage 是逐字段冻结的）。下游 B4b / judge-gt adapter 必须复现这一精确 preimage 才能构造 Va 接受的 ledger，而当前只由 Va 实现隐式冻结、非合同显式冻结。建议在 A0/B4b seam 里把该 preimage 写死（含"含 visible_intervals 全量 dump"）。行为无缺陷，属 seam 欠规约。

### VA-C4 —— NIT：true_azimuth/unknown seam 形状可比对但零测试（review-ask #2 裁决）

`:341-343` Va 对 `resolved_direction_sidecar` 只校验 binding 内部自洽（`entry.direction_semantics ∈ {true_azimuth,unknown}` + `orientation_output_hash`/`adapter_version` 非空），**不**与外层 B-M 冻结 sidecar 对象逐字段比对——这是**对的**：该 sidecar 不是 Va 输入，§3.2.2"Va 只校验已有 binding"把逐字段一致性留给 adapter/B4b。`ElevationViewBindingV1` 已携带 seam 五字段（`input_id/resolved_building_direction/view_manifest_sha256/orientation_output_hash/adapter_version`），B4b 接线时可直接逐字段比对，**不需本批新增 I/O**。裁决：接缝形状已就绪、分工正确。唯该整条路径零测试（见 VA-C2 item 9），shipped-untested，返工时须补正例 + 缺 hash/adapter/manifest-drift/不可唯一 resolve 的拒例。

### VA-C5 —— NIT：item 15 测试名超出断言

`tests/test_c2_va_applicability.py:114 test_half_open_touch_is_not_evidence_and_adjacent_sources_merge` 名承诺"adjacent_sources_merge"与真 gap 不桥接，但函数体只断言 touch=零覆盖（`status == not_applicable`），未断言相邻 source 合并、未断言 gap 不桥接。`_merge` 本身逻辑正确（本审已核 `<=` 合并、gap 不并），但测试名与断言不符，误导覆盖账。

### 正向确认（非缺陷，登记留痕）

- **VA-R2 红线成立且被守**：`correction/__init__.py` 未改、`__all__` 无 Va 符号（`:16-21`）；import-order 回归 `test_import_order_and_package_no_va_export` 真跑双序 subprocess + 断言 package 不暴露 `derive_opening_claim_applicability`，本审核实包级环真实（`execution.view_manifest → correction.claims → correction/__init__`；若 __init__ 导 Va 即成环 `correction/__init__ → facade_applicability → execution.view_manifest`），未成环因 __init__ 未导 Va。
- **gt 铁律（focus #3）成立**：`facade_applicability.py` import 面 = hashlib/json/typing/pydantic + claims/facade(ViewProjectionFrame)/schema(FacadeSegment)/view_manifest(RequiredViewEntry,ViewManifest)，零 `judge/gt`、零 scorer、零 `load_core_tolerances`、零 Vg materialize；测试用合成 fixture，零读 `case_tests/test_baseline/gt/`。
- **A0 §12 登记完整**：新增 §4.1 覆盖两版本常量+owner、引用 `CLAIMS_VOCAB_VERSION`、半开区间、plan bypass、elevation local→world→target→Vg-visible、existence fragment、completeness 不 gate 正向只 gate 负证据、无 tolerance/不读 correction.yaml、版本 bump 规则；未触 A1–A4 权威矩阵。
- **canonical 一致**：`_canonical_hash` 与仓库 `manifest.hash_obj` 同口径（sort_keys/compact/ensure_ascii=False）；`frame_transform_sha256` preimage 逐字段等于 §3.2.6（9 键、排除 view_manifest_sha256/orientation/adapter/resolution_source）。
- **语义核对（focus #4）**：七 claim 固定 ledger 恒七行不删行（`:386-387` CLAIM_ORDER 门 + `:392` 逐 claim 构造）；plan 正证据绕过 Vg（`:414-420` 不碰 visible_intervals）；elevation 必经 local→world→target→target-segment.visible_intervals 相交（`:429-435`）；半开区间 lo<hi 严格、touch 不产宽（`_intersect` 要 `lo<hi`）；applicability 与 provenance 两轴分离（Va 不读 claim 值/置信度/observed-derived-assumed）；completeness 只作负证据审计不抬正向 status（负-only decision applicable_intervals=() 不进 covered，`:457-466` status 仅由正向 covered 决定）；身份/hash 漂移/方向未解析走结构化 error code（§7.1 七 code 齐）。
- **§10 vg 测试行**：`tests/test_c2_vg_visibility.py` 无 Va seam stub（grep 命中均为 Vg 自有符号），无需去重，施工未改属实。
- **定向 suite**：240 passed（见下）。

---

## 测试族对账表（合同 §11 族 → 测试落点 / 缺失）

| # | 合同 §11 需求 | 落点 | 裁定 |
|---|---|---|---|
| 1 | 七 claim exact order 正例 + 缺一/重复/第八词/错序拒 | 正例 test_full_...；错序 test_wrong_claim_order... | 部分（缺一/重复/第八词无测） |
| 2 | 全模型 unknown field/数字串/bool-as-num/NaN/±inf/空id/lo>=hi 拒 | test_strict_interval_wire...[bad0-4]（仅 interval） | 部分（其余模型 unknown field/空 id 无测） |
| 3 | visibility ledger 重复 floor/seg、跨 floor、fingerprint/segment hash 漂移、缺/伪 feature hash、错 helper tuple 拒 | test_identity_..._fail_closed（仅 segment hash 漂移） | 大量缺失 |
| 4 | manifest 篡改由 ViewManifest 拒 + binding manifest hash 漂移由 Va 拒 | —— | **缺失** |
| 5 | target 不存在/floor·family 错/越 segment/七 target 任两不等/opening id 重复拒 | —— | **缺失** |
| 6 | output hash 自复算 + 篡改 interval/source/status 不一致 + 乱序 canonical 相同 | 自复算 test_full_...；乱序 test_input_permutation... | 部分（篡改不一致无测） |
| 7 | 四 family × mirror{F,T} × local 两值逐格 XOR/origin/两端 | fixture 仅 South/F/l2r 一格 | **缺失（16 格测 1）** |
| 8 | building_axis 正例 + family≠building_view_direction 拒 | 正例（fixture 隐含） | 部分（不等拒无测） |
| 9 | true_azimuth/unknown sidecar 全字段正 + 缺 hash/adapter/manifest 漂移/不可唯一 resolve 拒 | —— | **缺失（全路径）** |
| 10 | unknown mirror/错 axis·sign·origin/frame hash 漂移拒 | test_identity_...（仅 sign=-1） | 部分 |
| 11 | 每 elevation 恰一 binding：缺/多/plan 多余/悬空拒 | —— | **缺失** |
| 12 | rect 全 visible plan4/elev6 full + 越权(host@elev,sill/head/appear@plan)拒 | 正例 test_full_... | 部分（越权拒无测） |
| 13 | Z partial：existence fragment + 余 partial + complement 逐值 | test_partial_elevation_... | **覆盖** |
| 14 | FULL_OCCLUDE：elev6 unobserved + 加 plan4 full | test_plan_bypasses_hidden...（elev 仅 sill/head） | 部分（实质覆盖 plan 不读 visibility） |
| 15 | 端点半开零覆盖 + exact adjacent merge + 真 gap 不桥 | test_half_open_touch...（仅零覆盖，名超断言→VA-C5） | 部分 |
| 16 | 多 source union：两 elev 片段合 full/去重/plan 压 elev partial 保 audit | —— | **缺失** |
| 17 | mapped∩target 部分交按交集计 + 完全 disjoint 是 invariant | test_wrong_claim_order...（disjoint） | 部分（部分交集无测） |
| 18 | negative capability：空 list 不影响 + 三类 assertion + plan negative full/elev visible subset | —— | **缺失（全轴；VA-C1 藏此）** |
| 19 | positive 重复/悬空/越权 BLOCK + 缺 positive 合法 NA + 双调用 judge/executor ledger 分离 | test_wrong_claim_order...（disjoint 一facet） | 部分（重复/悬空/越权/双调用无测） |
| 20 | 凹形 hidden 四例 | —— | **缺失** |
| 21 | sm26 三反例（合成 fixture） | —— | **缺失** |
| 22 | provenance 正交（observed/derived/assumed 丢弃后 bytes 同） | —— | **缺失** |
| 23 | judge/executor parity（gt Vg ledger 构造、不引 product hash） | —— | **缺失** |
| 24 | B4b seam contract（七行→INCLUDED/PARTIAL/NA 形状足够、无 0.5/weight） | —— | **缺失** |
| 25 | import graph 无禁忌 + monkeypatch open/env/clock/random/config/Vg 后仍运行 + import-order 独立回归 + package 不导出 Va | test_import_order...、test_module_is_gt_blind...（token 扫描） | 部分（monkeypatch 纯度回归无测；import-order+no-export **已覆盖**） |
| 26 | deep copy 前后相等 + 重复调用相等 + 并发无共享 | test_input_permutation...（无 mutation + a==b） | 部分（并发未测，可接受） |
| 27 | 小整数半开 property：独立 oracle 验 partition | —— | **缺失** |
| 28 | 任意打乱 canonical 稳定 + claim 错序拒 | test_input_permutation... + test_wrong_claim_order... | **覆盖** |
| 29 | 一/零/多 relevant view 均运行 + 不断言 elev==4 | —— | **缺失（仅单 elev fixture）** |
| 30 | legacy v1/v2 不接 Va + Vg/B-M/B2/B3/B2b 既有 tests 全绿 | 定向回归 240 绿 | **覆盖（suite 级）** |
| 31 | 全量 suite 绿 + strict xfail 不变 + sm20/sm21 golden 零改 + sm26 合成 fixture | 未改 golden；全量归主控轻门；sm26 fixture 缺（见 item 21） | 部分（全量待主控） |

小结：**完整覆盖** 5/6/13/28/30 及 VA-R2/R3 基础位；**部分** 1/2/3/6/8/10/12/14/15/17/19/25/26/31；**整条缺失** 4/5/7/9/11/16/18/20/21/22/23/24/27/29。

---

## 定向测试组结果（本审自跑）

`pytest tests/test_c2_va_applicability.py tests/test_c2_vg_visibility.py tests/test_view_manifest_schema.py tests/test_view_manifest_generator.py tests/test_claims_vocab.py tests/test_c2_b2_v3.py -q`

**240 passed, 1 warning**（warning = test_c2_b2_v3 既有 Pydantic serializer warning，非本批引入）。其中 Va 专属 14 passed（collect 确认 14 test ID）。全量 pytest 归主控轻门。

---

## 返工清单（给施工者，主控裁决后下发）

1. **[VA-C1]** 修 `_relevant_negative` elevation 分支：按 §6.2 用 `bindings[entry.input_id].resolved_building_direction == opening.facade_family`（需把 bindings 传入或在调用点过滤），删恒真 `family` 形参。
2. **[VA-C2]** 补齐 §11 缺失族，至少：item 7 方向矩阵、item 9 true_azimuth/unknown 正+拒、item 11 binding 计数、item 16 多 source union、item 18 negative capability（含会抓出 VA-C1 的多立面反例）、item 24 B4b seam、item 27 property oracle、item 20/21/22/23/29；并补 item 1/3/5/12/19 的拒例、item 25 monkeypatch 纯度回归。逐族落地或逐条列明真未竟。
3. **[VA-C3]** 在 A0（或 B4b seam note）显式冻结 `facade_segments_sha256` 的精确 preimage（含全量 segment dump + 排序键）。
4. **[VA-C5]** 修 item 15 测试断言使其名实相符（或改名），补相邻合并 + gap 不桥接断言。
5. 返工后重跑定向组 + 交主控全量轻门；施工者不作最终批准。

---

# r2 复审(2026-07-14)

同审向、同基准(合同 v2 + 派单),对象=返工后工作树(facade_applicability.py 513 行、test_c2_va_applicability.py 455 行/46 test ID、A0 +29)。工作树核对:仍仅 A0 改动 + 两新文件,`correction/__init__.py` 未动,零 golden。

## r1 findings 逐条闭合

| r1 finding | 状态 | 闭合证据 |
|---|---|---|
| VA-C1(MAJOR 恒真式) | **CLOSED** | `facade_applicability.py:366-382` `_relevant_negative` 改接 `bindings` dict,比 `bindings[entry.input_id].resolved_building_direction == opening.facade_family`,与 §6.2「elevation + resolved family matches」逐字一致;恒真形参已删;`_validate_bindings` 保证每 required elevation 恰一 binding,无 KeyError 路径;detail/site 两分支均 False 不入选。回归测试 `test_negative_capability_sources_and_multi_elevation_family_filter` 构造 South opening + East negative-capable elevation,断言 `"east" not in by_source`。本审另跑独立 4 立面 probe(South opening + N/E/W 全 negative-capable):decision 集恰 `{plan, south}`,N/E/W 全被排除——**新 review-ask #1 裁决:修法正确,无新恒真/漏配对**。probe 顺带实证 hidden target 的 elevation 负区间=(),即 sm26 第三反例语义行为正确。 |
| VA-C2(MAJOR 测试族未达) | **CLOSED(实质)** | 14→46 test ID;31 行对账表重录于下:已落 25 / 部分 5 / 仍缺 0;r1 点名的整条缺失族(4/5/7/9/11/16/18/20/21/22/23/24/27/29)全部落地或实质落地。残留降级为 VA-C6(MINOR)+ VA-C7(NIT 束),不再构成 §14 硬门未达。 |
| VA-C3(MINOR preimage 未冻结) | **CLOSED** | A0 §4.1 新增整段冻结 `facade_segments_sha256` preimage:完整 `FacadeSegment.model_dump(mode="json")` 十字段逐一点名(id/floor_id/facade_family/p1/p2/outward_normal/world_along_interval/depth/visible_intervals 全量有序表/source_footprint_fingerprint,无省略无投影)、排序键 `(floor_id, family_rank N0/S1/E2/W3, along.lo, along.hi, depth, id)`、compact UTF-8 `sort_keys=true` `(',',':')` `ensure_ascii=false` JSON 数组、标注为 accepted-correction 与 judge adapter 共用的 frozen v1 preimage。**新 review-ask #2 裁决:可复现**——本审仅按 A0 prose 从零实现重算(不 import Va helper),对 4 段多 family fixture 与实现 hash 逐字节相同(`9e3253…384f`)。与实现唯一差异=实现排序 tuple 尾挂 dump dict,合法 ledger 内 id 全局唯一故永不参与比较,不影响可复现性。 |
| VA-C4(NIT true_azimuth 零测试) | CLOSED | `test_direction_resolution_sidecar_true_azimuth_and_unknown_paths`:true_azimuth 与 unknown 双正例 + 缺 orientation hash/缺 adapter version/manifest hash 漂移/building_axis entry 配 sidecar binding 四拒例。 |
| VA-C5(NIT item15 名实不符) | **CLOSED** | 原测试改名 `test_half_open_touch_is_not_evidence`(只断言 touch);新增 `test_half_open_adjacent_merge_and_real_gap_do_not_bridge`:exact adjacency `[0,1)+[1,2)→[0,2)` 合并、真 gap `[0,0.5)+[1,2)` 不桥接且 unobserved=`[0.5,1)`,均经 Va 行为断言。 |

## 测试族对账表(r2 重录)

| # | r2 状态 | 落点/残留 |
|---|---|---|
| 1 | 已落 | 正例/错序/缺一/重复(test_claim_ledger_totality);残留:第八词无显式测例(Literal wire 拒,NIT→VA-C7) |
| 2 | 已落 | test_strict_interval + test_strict_new_models(unknown field×3 模型、数字串、空 id、mirrored="unknown");输出模型未逐一(NIT) |
| 3 | 已落 | test_visibility_identity_closure:重复 floor/跨 floor/fingerprint 漂移/缺·伪 feature hash/错 helper tuple;残留:同层重复 segment id 无独立测例(NIT) |
| 4 | 已落 | test_manifest_and_output_hash_tampering:manifest 篡改由 ViewManifest 拒 + binding manifest hash 漂移由 Va 拒 |
| 5 | 已落 | test_claim_ledger_totality(不存在/floor 错/family 错/七 target 不等)+ test_mapped_partial(越 segment);残留:opening_id 重复无测例(代码有门,NIT) |
| 6 | 已落 | 自复算 + 篡改 content_sha256 拒 + 乱序 canonical |
| 7 | **部分** | 16 格参数化在,但循环自证且不驱动 Va → VA-C6 |
| 8 | 已落 | 正例(fixture)+ family≠building_view_direction 拒(test_binding_cardinality) |
| 9 | 已落 | test_direction_resolution_sidecar 全路径 |
| 10 | **部分** | unknown mirror/错 sign √;错 axis、错 origin(hash 一致)、binding fingerprint 漂移无拒例 → 并入 VA-C6 |
| 11 | 已落 | test_binding_cardinality:缺/多(重复)/plan 多余 |
| 12 | 已落 | 正例 + host@elevation 拒 + sill@plan 拒(channel 级 PLAN/ELEVATION_POTENTIALLY_OBSERVABLE 检查为合同加固,方向正确) |
| 13 | 已落 | 不变 |
| 14 | 已落 | test_full_occlusion(合并式:plan4 full + elev3 NA on visible=()) |
| 15 | 已落 | VA-C5 闭;残留:line 348 no-op assert(NIT) |
| 16 | 已落 | test_multiple_elevation_sources:两 elevation 片段 union full + plan 共存 + 三 source audit 全保留 |
| 17 | 已落 | test_mapped_partial:部分交按交集计 + disjoint 是 invariant |
| 18 | 已落 | test_negative_capability:三类 CompletenessAssertion source(case_metadata/user/dataset)、assertion id 输出、plan negative=target、elevation negative=visible subset、多立面 family 过滤(VA-C1 抓手) |
| 19 | **部分** | 重复/越权/诚实 NA √;残留:悬空 source(不在 manifest)、"产品删声明不改 judge ledger"双调用对照无直接测(parity 测近似,NIT) |
| 20 | **部分** | 核心语义(plan positive 保留/plan negative full/elevation negative 仅 visible subset)在单段 fixture 覆盖;凹形多段同 family 深 target fixture 缺(§6.4.6 浅段背书禁令无测,NIT);本审 4 段 probe 实证行为正确 |
| 21 | 已落 | test_sm26(plan4 full、sill/head NA、provenance 不入 wire);第三反例 hidden completeness→零负区间无直接断言,本审 probe 实证正确(NIT) |
| 22 | 已落 | 结构性闭合:wire 无 provenance 槽位 + extra=forbid |
| 23 | 已落 | test_judge_executor_parity:judge_gt ledger 独立 hash、不引 product feature hash、canonical 相等 |
| 24 | 已落 | 同测试:七行→INCLUDED/PARTIAL/NOT_APPLICABLE 形状 + 无 0.5/weight |
| 25 | 已落 | monkeypatch open/env/random/clock/Vg materialize 后仍运行 + import-order 双序 + no-export + token 扫描 |
| 26 | 已落 | 无 mutation + 重复调用相等 + ThreadPoolExecutor 8 路并发相等 |
| 27 | 已落 | test_purity 尾部 2-cell 独立 oracle(covered∪unobserved=全集且不交);最小化实现(NIT) |
| 28 | 已落 | 不变 |
| 29 | 已落 | test_zero_one_and_many(0/1 source)+ 多 source 测试(2 elevation + 1 plan);无 elev==4 断言 |
| 30 | 已落 | 定向回归 226 非 Va 测试全绿 |
| 31 | 部分 | 零 golden √(git status 复核);全量 suite 归主控轻门(非施工残留) |

## 残留 findings

### VA-C6 —— MINOR:方向矩阵测试循环自证,未驱动 Va(§11.7/§11.10 深度不足)

`tests/test_c2_va_applicability.py:280-289` 16 格参数化的三条断言(sign XOR、along_origin、frame hash)全部与 `binding()` helper(`:104-113`)用**同一内联公式**构造,且**不调用** `derive_opening_claim_applicability`——矩阵格没有一格经 Va `_validate_bindings` 行为验证,"local→world 两端"逐格断言(§11.7 原文)缺失。Va 行为面实际只覆盖 South(多处)/East(negative 测试)两格 + 错 sign 拒例;错 axis、错 origin(frame hash 一致重算时)、binding fingerprint 漂移三类拒例(§11.10)无测。**非正确性缺陷**:本审独立 probe 已驱动 N/S/E/W 四 family(含 N/W 负 sign origin=extent_hi)全部经 Va 接受,行为正确。修法小:矩阵每格补一次 invoke(接受)+ 每 family 一个 mapped 端点断言,另补三类拒例。

### VA-C7 —— NIT(束):零散测试深度残留

①第八 claim 词显式拒例缺(Literal 已拒);②opening_id 重复、同层重复 segment id、悬空 positive source 无显式测例(代码门均在);③"产品删自己声明不改 judge ledger"的双调用对照(§11.19 后半)无直接测;④凹形多段同 family fixture 缺(§6.4.6 浅段背书禁令未测);⑤sm26 第三反例(hidden completeness→零负区间)无直接断言(本审 probe 实证正确);⑥`:348` no-op assert(`assert _canonical_hash(...)` 恒真)。均不阻批,建议随 B4b 批顺带补。

## 定向测试组结果(r2 自跑)

- Va 专属:**46 passed**(collect 确认 46 test ID = 27 函数,含 5 参数化 interval + 16 格矩阵)。
- 六组(同 r1):**272 passed, 1 warning**(warning 仍为 test_c2_b2_v3 既有 Pydantic serializer warning,非本批)。
- 本审两 probe:family 过滤 PASS、A0 preimage 独立重算 PASS(脚本落 scratchpad,未入仓)。

## r2 总裁决:APPROVE-WITH-CHANGES

r1 四条(+1 NIT)全闭;两项新 review-ask 均裁决通过(family 过滤修法正确、A0 preimage 独立可复现)。残留 1 MINOR(VA-C6 矩阵测试去循环化+补三拒例)+ 1 NIT 束(VA-C7),均为测试深度问题、无正确性缺陷,不需再开返工轮:VA-C6 可作小补丁随本批收尾或明示挂账 B4b,由主控裁决;核代码与合同 §2-§7/§10/§12 逐字一致,全量 suite 权威门照常归主控轻门。
