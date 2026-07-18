# B5 Phase C 施工对抗审 r1（Fable，最高档，跨厂商）

- 日期：2026-07-18
- 审者：Fable 5（未参与施工；施工者 sol/GPT 侧）
- 对象：working tree 13 文件 +1285/−54 + 新增 `tests/test_c2_b5_parent_and_verts.py`（781 行，32 tests）
- 合同：`AI_agent/proposals/c2_b5_detail_spec.md` v3（§14 Phase C，gates B5-C1..C5）
- 派工单：`AI_agent/logs/reviews/request/2026-07-18_b5_phaseC_construction_dispatch.md`

---

## VERDICT: **REWORK**

依据（派工单 §2 末条 + spec §13 首行/§14 末行的硬规则「任何安全拒绝分支缺测试锁 = 未交付」）：**算法层零 BLOCKER、零真 bug、四个活体探针全部阳性**；但本批新增的两簇 spec 点名安全拒绝分支**全仓零测试锁**（经独立 grep 证实，Phase A/B 文件亦无覆盖），按与 Phase B r1 完全相同的标准（算法全对·纯缺测试锁 → REWORK）裁定。返工范围窄：**只补锁，不动算法**。

---

## 分级 findings

### MAJOR

**[MAJOR-1] 四同步 promotion 拒绝门缺测试锁 = 未交付**
spec §10.1「v3 conflicts 非空且含 `window_host_conflict` 时 gate 必 block」与 §10.2 kernel 硬门的**核心拒绝分支**无任何测试：
- `src/validator/checks/kernel.py:_window_parent_binding`：`c2_b5_v1` bg + `proof=None` → fail（**这正是派工单点名的「先接受 output、以后补 sidecar」反软接线门**）——无锁；legacy bg + proof 非 None → fail——无锁；unknown contract / invalid proof artifact bytes / unsupported proof type 三条 fail——无锁。
- `src/agent/correction/geometry_validator.py:check_window_host_resolution`：geom.conflicts 含 `window_host_conflict` → block（spec 点名条款）——无锁；evidence wire 型错 / artifact evidence 与传入 evidence 不一致两条——无锁。
- 证据：`grep -rn "check_window_host_resolution\|window_parent_binding\|requires host proof\|must not receive B5" tests/`（排除新文件）= **空**。
- 修法：每分支一条独立测试（B5 bg+无 proof→kernel fail；legacy bg+proof→kernel fail / build ValueError；构造带 conflict 行的 v3 geom→finding not ok；unknown contract→fail；坏 artifact bytes→fail；evidence 型错→fail）。

**[MAJOR-2] versioned serializer 与身份拒绝分支缺测试锁 = 未交付**
- `src/agent/geometry/specs.py:_selected_contract` 显式 contract 与 `bg.geometry_contract` 不符 → raise——无锁；`c2_b5_v1` 窗缺 source/segment/host 三身份 → raise（`building_geometry_dict` 与 `serialize_geometry` 各一处）——无锁。
- `src/agent/geometry/build.py:build_geometry` legacy + proof → raise「legacy build must not receive B5 window host proof」——无锁（只锁了 v3-无-proof 方向）。
- `src/agent/correction/window_host.py:WindowHostsArtifactV1._hash` 本批新增三条 cross-check（output 身份 / claims·evidence window id 精确相等 / 三 identity hash 一致）——无锁。
- `src/agent/judge/score_service.py:score_typed_attempt` 的 `b5_output_hash_mismatch` 与 `b5_product_payload_differs_from_verified_output` 两分支——无锁（只锁了 proof=None）。
- `src/agent/geometry/modelling.py:attach_windows_v3` 首个 source↔resolution 集合 totality reject——无直接锁（仅 build 层 mutation 测试间接相邻）。
- 修法：逐分支独立拒例；serializer 侧建议顺手加一个**带窗 legacy** frozen-byte fixture（见 NIT-4，可与 Phase D §13.7 合并）。

### MINOR

**[MINOR-1] 两处 production 裸构造 `VerifiedWindowResolverInputs` 伪 marker（空 bytes）**
`src/agent/geometry/build.py:_reverify_window_host_proof` 与 `src/agent/correction/geometry_validator.py:check_window_host_resolution` 均以 `producer_draw_canonical_bytes=b"" / raw_view_manifest_bytes=b"" / raw_reading_artifacts=()` 直接构造「已验证」marker。spec §4.4 明言 marker「不能由 public constructor 直接构造，模块只导出 builder 与 verifier」。已核实：下游 `recompute_window_host_claims`/`derive_window_evidence_ledger` **只消费 `.inputs`**（`grep raw_view_manifest_bytes src/agent/correction/window_host.py` = 空），空字段目前惰性、且两处均先过 `verify_window_resolver_inputs`（content hash+catalog+权限重验），故非当下漏洞；但这在 production 立了「伪造 verified marker」先例，未来任何消费 raw 字段的代码即刻中毒。修法（Phase D 顺路）：window_sources 增设 recompute 专用窄输入型或模块内 `reissue_for_recompute()`，收回两处裸构造。

**[MINOR-2] v3 pipeline 中间态硬断未在自报中明示（fail-closed，登记 Phase D 必接线）**
`build_geometry` v3 现要求 proof，而 `pipeline.py:materialize_kernel_geometry`（line 743）与 `check_kernel`（line 1144）均未传 proof——v3 走 run_pipeline 将在 kernel 段 RuntimeError 硬失败（fail-closed，非假绿；v3 correction 尚无生产 e2e，无现网回归——与 B4b MINOR-1 登记一致）。sol 自报只说 writer/loader 延后，未明示「Phase C↔D 之间 v3 pipeline 不可运行」。要求：Phase D 派工单显式列 pipeline/check_kernel proof 接线两项，防漏。

### NIT

- **[NIT-1]** LINE-6 越界 t 只测下界（-0.01），上界 t>1 未测；LINE-8 wire normal 只测 (1,1)，(0,0) 变体未测（同一校验条款，spec 原文「(0,0)或(1,1)」，勉强达标）。
- **[NIT-2]** `score_schema.build_product_identity` 用 `getattr(accepted_stage_record, "artifact_contract", None)`——StageRecord 该字段为 required（manifest.py:228），default None 只会掩盖未来漂移；改直取属性。
- **[NIT-3]** 候选 output 序列化口径 `model_dump_json(indent=2)` 在 `finalize.py:157` 与 `geometry_validator.py` 两处独立书写；漂移会 fail-closed（identity mismatch）而非假绿，但应共享同一 helper。
- **[NIT-4]** legacy frozen-byte fixture（`test_legacy_version_gate_preserves_frozen_building_json_bytes`）只覆盖**空几何**，恰好没走本批唯一改动的窗行代码路径；带窗 legacy byte parity 按 §13.7 归 Phase D，本批测试名未过度声称，可接受但登记。

---

## 高危面逐条裁定（派工单 §2）

1. **`window_verts_on_line` 零 facade/x/y 分支** ✅ 真。函数体 = 校验 + `point_at(t)`×2 + z + `_orient((nx,ny,0))`（modelling.py），与 spec §6.5 伪码逐行同构；`_validate_window_line_inputs` 亦无 axis 分支；源码扫描测试在。build/kernel/validator 三边界均从 line+t+z+normal fresh 重算四点与 record 比对（`attach_windows_v3`、`_window_parent_binding`、`window_host_claim_issues`），**record 四点从不作为 helper 输入**（helper 签名根本不收点）。C2 `FacadeSegment` 斜线仍拒（LINE-5 绿）；diagonal 只作 helper 正例（LINE-4），未动 schema validator（§12.4 遵守）。
2. **负向轴** ✅ 真。resolver 用 `parameter_of(world_lo/hi_point)` 求 t、sort **t** 而非点、endpoints=`point_at(t_lo),point_at(t_hi)` 保 p1→p2；**探针 P1**（在 resolver 强行 `sorted((q0,q1))`）→ LINE-2/3/7 三测全红，方向锁活。**LINE-7 延后裁定：正当**——Phase C 边界（`window_host_claim_issues` 的「p1->p2 endpoints」检查 + `_reverify_window_host_proof` 全量重算）已锁死该篡改（测试双断言：validator 拒 + proof 签发拒）；且代数上封闭：要让世界升序 endpoints 与 t 自洽需 t 逆序，wire `ParamIntervalV1` 拒。当前**不存在**任何消费持久化 sidecar bytes 的生产路径（写者/读者均未落地），故 writer/loader 双边锁归 Phase D 不构成本批覆盖缺口。
3. **parent 恰一** ✅ 真。零/多 = `WindowParentBindingError`（typed raise，非 note+skip）；normal 用 `_newell`（已归一，modelling.py:239-240）分量残差 `<= plane epsilon`，无 dot>0.9；fragmented 半 span 因 contains-both-endpoints 过滤直接零候选拒绝、不切双窗（PARENT-4 绿）。**探针 P2**（删 normal 检查）→ PARENT-5 红。
4. **不按中心点猜** ✅ 真。`_v3_parent_candidates`/`window_host_claim_issues`/judge 侧均无 `min(distance)`/`contains(center)`/bbox 截断/id 破平局；judge `map_product_cells_to_gt_zones` 只认 polygon 全等，`resolve_correction_window_host` 补 outward-normal 匹配（修掉共线两侧 cell 误配）。对称包围 fixture 在 Phase B（GEO-2/3/9P/9E 等，`test_c2_b5_host_resolution.py` 绿）。
5. **serializer legacy byte-parity** ✅/⚠️ 半真。version-gated `_selected_contract` + legacy 投影排除三 None 字段 + `geometry_contract` key 仅 c2_b5_v1 注入；frozen-byte 测试存在但只覆盖空几何（NIT-4）；测试名与自报未越界声称 v1/v2 全量 byte parity（那是 §13.7/Phase D）。语义层由 76+114+25 邻接套件零回归背书。
6. **四同步无软接线** ✅ 接线真（gate①：pipeline.py:991 与 run_stage.py:260 均传 claims+evidence；kernel 门存在且 fresh 重算 parent+verts——**探针 P3**（关 verts 等值门）→ 红；specs 从 built fresh 生成、`check_geometry_specs_consistency` 篡改双向拒（SYNC-2×2 绿）；judge 先 `_reverify_window_host_proof` 全量重算 + output hash 绑定 + payload 全等，再独立评分，`allow_temporary_binding=False` 钉死 official——**探针 P4**（删 contract 门）→ JUDGE-3 红）。但**拒绝分支缺锁**见 MAJOR-1/2；judge「六件套 verifier」在本批实现为三 raw artifact 全量重算 + accepted/contract/output-hash 门，六件套完整校验依赖 Phase D loader，属正当延后。
7. **production 禁 import judge** ✅ 真。`test_c5` 扫 correction+geometry 两根目录（含 `import src.agent.judge` 与 `from src.agent import judge` 两式）；独立 grep 复核零 judge import；judge→production 单向 import（score_service import build/window_host）方向正确。
8. **broad-except** ✅ 无 fail-open。触及模块 grep 零 `except Exception`；新增捕获全为窄型（ValueError/RuntimeError）且一律转 fail finding / typed raise / re-raise。pipeline.py:745 的 advisory 广捕获系**既有代码**（非本批），且 v3 build 失败经它仍落 `bg is None → RuntimeError` 硬失败，fail-closed（MINOR-2 已登记中间态）。
9. **shipped-untested / 假绿** ⚠️ 见 MAJOR-1/2。fixture 纪律合格：SOUTH_SEGMENT_ID / SOUTH_RESOLUTION_SHA256 / LINE-1..4 t·点 / 空几何 bytes / specs 全文 均为冻结字面量；`canonical_sha256` 仅用于**构造合法输入**（artifact content hash），未用于生成 expected 自比；无 `x!=x` 恒真检查；`_resigned_claims` 重签是攻击 fixture 的正当用法（证明「hash 自洽≠关系可信」）。

## 机械事实核查

**gate↔测试映射（独立复核）**：
| gate | 落点 | 判定 |
|---|---|---|
| B5-C1 parent-unique | PARENT-1..5 各一测（test_parent_1..5）| ✅ 全锁，P2 探针活 |
| B5-C2 line-parameterized | LINE-1/4 手写字面量；LINE-6 三拒（上界缺）；LINE-8 三拒（(0,0) 缺）| ✅（NIT-1）|
| B5-C3 negative-axis | LINE-2/3（North/West 负轴字面量）/5/7（validator+proof 双边）| ✅，P1 探针活；writer/loader 边归 D 正当 |
| B5-C4 sync | SYNC-1（含冻结 segment id+resolution sha）/SYNC-2×2/JUDGE-1/2/3/validator pass·missing/kernel verts；GEO-1..12 在 Phase B 文件已锁 | ⚠️ 接线全真但拒绝分支缺锁（MAJOR-1/2）|
| B5-C5 import-zero | test_c5 扫描 + 独立 grep | ✅ |

**活体探针（4/4 阳性，全部已回滚，diff 恢复 +1285/−54）**：
| # | 改坏点 | 预期红 | 结果 |
|---|---|---|---|
| P1 | resolver 内 `sorted((q0,q1))` 世界升序写 endpoints | LINE-2/3/7 | **3 failed** ✅ |
| P2 | `_v3_parent_candidates` 删 normal 分量残差检查 | PARENT-5 | **1 failed** ✅ |
| P3 | kernel `built.verts != fresh_vertices` 改恒 False | test_kernel_fresh_recompute | **1 failed** ✅ |
| P4 | `decide_score_capability` 删 B5 contract 门 | JUDGE-3 | **1 failed** ✅ |

**targeted 复跑（干净态）**：`test_c2_b5_*` 3 文件 = **120 passed**（sol 自报 120 ✓）；b4b 5 文件 = **76 passed** ✓；checks/kernel/geometry/pipeline/correction-stability 6 文件 = **114 passed**；b1/naming 3 文件 = **25 passed**。零回归。sol 自报改动面（13 文件 +1285/−54、测试 781 行）与 git 逐项相符；自报「诚实未完」清单相符，另有 MINOR-2 一项未明示的中间态。

---

**总评**：算法与信任根工程质量高——line 几何、负轴方向、parent 恰一、fresh 重算、judge 独立性全部实证为真，四探针全活、零 fail-open、零真 bug；唯一缺口是本批新增安全拒绝分支两簇未按合同逐条上锁，按「缺锁=未交付」硬规与 Phase B 同标准裁 REWORK。**返工=纯补测试锁（MAJOR-1/2 清单逐分支），预计小批量；补齐复验后可进主控轻门**。MINOR-1/2 可随 Phase D 处理，不阻本批返工闭合。
