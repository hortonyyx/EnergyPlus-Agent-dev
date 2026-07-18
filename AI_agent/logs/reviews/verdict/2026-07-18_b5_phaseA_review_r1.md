# B5 Phase A 施工审 r1（Opus 升一档 · 独立上下文 · 活体探针）

- 审对象：terra 施工 B5 Phase A（gates B5-A1..A7）本批未 commit diff
- 绑定合同：`AI_agent/proposals/c2_b5_detail_spec.md` v3（§4/§5.2/§5.3/§9.2/§11/§13.1/§14 Phase A）
- 派工单：`AI_agent/logs/reviews/request/2026-07-18_b5_phaseA_construction_dispatch.md`
- 跨厂商：terra(GPT) 写 → Opus 审，谁写谁不批

## 总裁决：APPROVE-WITH-CHANGES

- **BLOCKER: 0 ｜ MAJOR: 0 ｜ MINOR: 4 ｜ NIT: 1**
- **A6 BLOCKER-重设计核心（current-ring binding + ring-free facts + judge parity）经四路活体探针实证为真——本批未抓到 MAJOR 是如实结论、非硬凑**（探针清单见下）。
- CHANGES = 一条 wire 与冻结 spec 背离须**现在改**（B5PA-01，非延后测试问题）+ 三条 shipped-live-but-uncovered 须在交付回报**显式登记为延后（带 spec 指针）**而非用总绿数掩盖（B5PA-02/03/04）。

---

## 正面验真清单（已实证，省 terra 重证）

1. **21/21 targeted 全绿**：`python -m pytest tests/test_c2_b5_source_routing.py -q` → 21 passed。
2. **信任根·content_sha256 强制**（活体）：`verify_window_resolver_inputs` 对 `model_copy` 篡改字段+留旧 content_sha256 的 inputs → 抛 `source_identity_invalid`；重 rehash 的对照件放行。resolver-input 自报 hash 无 fail-open。
3. **信任根·ring fingerprint 防篡改**（活体）：把 segment `source_footprint_fingerprint` 改 `"0"*64` 喂 production helper → `direction_binding_ring_invalid`，fail-closed，非吞错。
4. **A6 非自指**（活体，三重锚）：(a) 独立手算 9 字段 preimage 的 SHA-256 == 冻结字面量 `b0051aa2…6082a86`；(b) production helper 当前输出 == 该字面量；(c) monkeypatch 扰动 production `_frame_hash`（翻 sign）→ 输出偏离冻结字面量 → 证 test line 158 的断言非取 helper 输出、production 漂移即变红。A5 locator 向量同理手写 + 改末字节敏感性。
5. **ring-free 方向事实**（类型实证）：`ElevationDirectionFactV1` 恰 8 字段，`source_footprint_fingerprint/world_axis/sign/along_origin/frame_transform_sha256` 五字段**零泄漏**。
6. **judge parity 逐字节**：production 13 字段 binding model_dump == judge `materialize_va_elevation_bindings` 输出 model_dump（test A6 + judge 侧 frame hash 独立重算）；`_BASE_SIGN`/`_AXIS`/`flip=mirrored^r2l`/`sign=-base if flip`/`origin=lo if sign==1 else hi` 与 `facade_applicability` 逐条同式。
7. **production 零 judge import**：grep + `test_b5_a6_production_source_is_judge_blind` 源扫双证。
8. **无 fail-open**：两新模块 grep 无 `except:`/`except Exception`/`except BaseException`；全部 except 均窄类型（`UnicodeDecodeError/JSONDecodeError/ValueError/FacadeVisibilityInvariantError`）。
9. **SRC-C1..C10 = 10 个独立 test 函数**（非参数化合并一次调用只断总失败），逐条稳定 code。
10. **ViewManifest floor_ref 契约变更零回归**：manifest/Va 相关 133 测试全绿；`RequiredViewEntry` 强制 plan⇒floor_ref 非空（line 362-363）→ 新 `max(plan_refs)` 不会遇 None 崩。
11. **A2 conflict guard 非空转**（活体）：合法 `WindowHostConflictV1` 正常构造；`upstream=ring_invalid` 配非 Va-mapped `reason_code` → 拒。
12. **越界检查通过**：diff 未碰纯 resolver 主链（§6）、build（§8）、四同步（§10 validator/kernel/specs/judge）、E4 rebind（§9.4）、legacy 封口（§3.3/§13.7）；无 protected gt/golden diff（git status 干净于这些路径）。
13. **config/A0 齐**：三容差各自命名进 `correction.yaml`+`CoreTolerances`（无 dataclass 默认，缺 key `TypeError`）+A0 §4 三行 + §5 schema/helper 登记；`window_clamp_to_parent` 注释改 "Legacy v1/v2 only"；validate 关系式 `0<plane<=span<clamp<=min_edge` 落地。

---

## Findings

### B5PA-01 [MINOR·最高优先·现在改] `tolerance_names` wire 比冻结 spec 松

- **判据**：spec §5.3（行 690-694）冻结为**定长有序 3 元组** `tuple[Literal["WINDOW_SEGMENT_ENDPOINT_CLAMP_TOL"], Literal["WINDOW_HOST_SPAN_EPSILON"], Literal["WINDOW_HOST_PLANE_EPSILON"]]`。实现 `window_host.py:253` 为**变长联合** `tuple[Literal["…CLAMP_TOL","…SPAN_EPSILON","…PLANE_EPSILON"], ...]`（活体 `get_type_hints` 确认）——允许空元组、乱序、重复。
- **为何非延后测试问题**：这是**已经与冻结 spec 背离的 wire 本身**，不是"测试排到后 Phase"。schema.py 新钩子（行 267-270）现在就对任何 v3 accepted-output 里 `kind=="window_host_resolution"` 的行跑 `WindowHostResolutionAuditV1.model_validate`——Phase D writer 一旦产出 `tolerance_names=()` 也会被放行，违背本批"冻死 strict wire 使后续代码无法发明松 sidecar"的立身宗旨。当前 Phase A 无 live 消费者（producer 预填被 parse 拒、无 writer），故无 fail-open，压 MINOR。
- **修法**：改回 spec 的定长有序 3-Literal 元组；补一条 `WindowHostResolutionAuditV1` 正例构造 + 错 arity/乱序拒例（该 audit 行**当前零正例测试**）。

### B5PA-02 [MINOR] 前置的 output/claims/evidence-ledger/artifact strict wire 在本批 shipped-live 但零拒绝分支锁

- **判据**：`window_host.py` 落地 `WindowHostResolutionV1`（`_shape_and_hash`：cardinal-normal / plan-overlap-空 / elevation-overlap-非空 / canonical-union / resolution_sha256 重算 共 5 处 raise）、`WindowHostClaimsV1._aggregate`（2 raise）、`WindowEvidenceDecisionV1`/`WindowEvidenceLedgerV1`/`WindowHostsArtifactV1`（各 hash 重算 raise）——本批 test 文件**无一条**触及这些 validator。仅 `WindowHostConflictV1`（§5.2）有 A2 拒例。
- **定性**：spec §13 把这些行为拒例排在 **LINE-8（§13.3, Phase C）**；模块 docstring 也诚实披露"resolver 本体落 Phase B / 先冻 record"。故属 spec 排序内的前置，非藏假绿。**但**派工单硬规矩禁"用现有总绿数代替 / 静默延后"。
- **修法**：交付回报里**逐条列出**这些 wire 的拒绝分支锁指向 LINE-8（Phase C）/ BIND-5..6（Phase B），显式标"本批未测·延后"；或本批就补最小 wire 拒例（成本低）。二选一，但不得沉默。

### B5PA-03 [MINOR] §5.2 mapper `map_direction_binding_error` 是 Phase-A 域内 groundwork 却零直测

- **判据**：派工单 Phase A 明列"conflict wire（§5.2）"；`map_direction_binding_error` 即 §5.2 唯一 mapper，本批已实现但**无任何直接测试**（BIND-5/6 是 Phase B 的 resolver dry 路径）。活体探针实证其功能正确（`ring_incompatible` → 1 row，`reason=direction_binding_invalid`、保 `upstream_error_code`、`fallback=invariant_no_geometry_commit`），无 fail-open。
- **修法**：补一条纯函数直测（喂 `WindowDirectionBindingError` 两 code + 有/无 `floor_id` context，断 canonical rows 与三固定字段），成本极低。

### B5PA-04 [MINOR] A6 parity 只覆盖 South / 非镜像 / sign=+1 / axis=x 单向量

- **判据**：`test_b5_a6` 冻结向量仅 South、`mirrored=False`、`sign=1`、`world_axis="x"`。**flip 分支**（`mirrored=True` 或 `local_x_positive="image_right_to_left"` → sign 取反）与 **axis=y 族**（East/West）的 ring 派生分支本批 shipped-live 但零锚点向量。派工单点名"负轴/sign 齐否"。
- **风险**：sign 派生错 = 窗贴错建筑侧；production 与 Va 同式故 parity 不会背离，但缺独立手写锚使该分支"名义已冻、实际未验"。
- **修法**：补一条 mirrored/flip 冻结 parity 向量 + 一条 axis=y（East 或 West）向量。

### B5PA-05 [NIT] `_claim_links` 用 `assert isinstance(entry, RequiredViewEntry)` 收窄信任相关分支

- **判据**：`window_sources.py:356` 用 `assert` 做 entry 类型收窄；`python -O` 下 assert 被剥离。并行的 `verify_window_resolver_inputs`（行 273-275）用正式 `if not …: raise`。此处 entry 恒来自 catalog 的 `required_entries()`（结构保证 Required），不可利用，故 NIT。
- **修法**：与 verifier 一致改显式 `raise WindowResolverInputError(...)`，去掉 `-O` 剥离面。

---

## 活体探针记录（可复现）

- 探针脚本：`scratchpad/probe.py`（非自指+ring 篡改+content-hash）、`probe5b.py`（content-hash verify seam）、`probe6.py`（mapper+A2 guard+arity）。
- 关键输出：
  - `production frame hash == frozen: True` / `independent hand hash == frozen: True` / `perturbed production drifts from frozen (test would go RED): True`
  - `tampered fingerprint -> ring_invalid: True`
  - `verify rejects stale content hash: source_identity_invalid`（初次 probe 5 的 False 系 JSON dump 把 tuple 降 list 触发 strict 前置报错的**探针误报**，已用 model_copy 复验纠正）
  - `mapper rows: 1 | reason: direction_binding_invalid | upstream: direction_binding_ring_incompatible | fallback: invariant_no_geometry_commit`
  - `tolerance_names type: tuple[Literal['…'], ...]`（变长，确认 B5PA-01）
- 全量 pytest 归主控轻门（本审只跑 targeted + 相邻 manifest/Va 回归子集 133 绿），未跑全量。
