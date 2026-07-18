# B5 施工细稿 v2 对抗审判词（r2）

- 日期：2026-07-18
- 审稿人：Fable 5（Claude 侧最高档，跨厂商对抗审；批准权威）
- 审对象：`AI_agent/proposals/c2_b5_detail_spec.md`（sol v2，1561 行，标题已是 v2）
- 前轮：`2026-07-18_c2_b5_spec_review_r1.md`（REWORK，1 BLOCKER + 4 MAJOR + 6 MINOR + 2 NIT）
- 对照源：r1 判词 13 条 + 设计权威 `c2_full_unlock_design.md` §E1'/§E2'/§122/§128 + 现码 `6d5fd1b`（`facade_applicability.py`、`deterministic.py`、`finalize.py`、`modelling.py`、`parse.py`、`view_manifest.py`、`manifest.py`、`score_inputs.py`、`opening_claim_score.py`、`score_schema.py`）
- 审法：spec 审。两枚冻结哈希向量沿用 r1 已独立复算结论（v2 未改）。

## 总裁决：**APPROVE-WITH-CHANGES**

| | 计数 |
|---|---|
| BLOCKER | **0** |
| MAJOR | **1**（新增 B5-R2-01，接线/测试收尾缺口，机制已在位） |
| r1 遗留（13 条） | **全部 CLOSED** |
| 新增 MINOR | 2 |

一句话：r1 的 BLOCKER 与全部 12 条 MAJOR/MINOR/NIT **实质闭合**（逐条引证见下，非采信自报）；BLOCKER 的重设计（ring-free 方向事实 + production current-ring helper + host/evidence 双 sidecar 分离解 hash 环）**方向正确、机制自洽**。唯一未闭是重设计**自己带出的一个收尾缺口**：§4.5 helper 的两个 ring-tamper 拒绝码（`direction_binding_ring_invalid`/`direction_binding_ring_incompatible`）悬空——无归属异常类、无捕获点、未进 conflict wire、无测试锁（B5-R2-01）。这是"补一段接线 + 两条测试"的有界修复，机制（§5.2 typed conflict + §6.6 窄捕获→reject）已建好，故给 **APPROVE-WITH-CHANGES** 而非再来一轮 REWORK：sol 落实 B5-R2-01 + 两条 MINOR 后，我复核该窄增量 diff 即可定稿，无需第三轮完整对抗审。

---

## 一、r1 十三条逐条复核（全部引 v2 行号验，非采信自报）

### B5-R1-01 · BLOCKER → **CLOSED**（重设计成立；残留收尾见 B5-R2-01）
r1 判据：Va elevation binding 含 ring 依赖字段（`source_footprint_fingerprint`/`along_origin`/`frame_transform_sha256`），冻进 draw-前 content-hash 与 ring 两次变形不可调和；且生产侧 binding 无构造者。

v2 逐项闭合：
- **resolver inputs 彻底去 ring 依赖**：`WindowResolverInputsV1` 的 `elevation_views` 换成 `elevation_direction_facts: tuple[ElevationDirectionFactV1,...]`（L324）；`ElevationDirectionFactV1`（L282–295）恰八项 ring-free 字段，L339 明令**严禁**加入 `source_footprint_fingerprint/world_axis/sign/along_origin/frame_transform_sha256`；不变量 #15（L128）+ L351 双锁"13 字段型不进 content hash、不跨 dry/final 复用"。
- **生产侧 helper 有主、签名冻结、时序确定**：§4.5 `materialize_current_ring_va_elevation_bindings`（L418–424），唯一 owner=`window_sources.py`（L107/L413），production 禁 import judge（L413/L436）；每次调用 fresh 重算 fingerprint/extent/axis/flip/sign/along_origin/frame_hash（L429–433）；dry/pre-transform、B2b post-simulation、final 三处调同一 helper、各按**当轮 ring**（L196–199, L436, L720）。
- **adapter 与 Va 冻结约定逐值对齐**（亲核现码）：L431 base sign `North:-1,South:+1,East:+1,West:-1` = `facade_applicability.py:44 _BASE_SIGN`；L432 `along_origin = extent.lo if sign==+1 else extent.hi` = `facade_applicability.py:456–458`；world_axis 映射 = `facade_applicability.py:43 _AXIS`。这些量是 family/mirror 的确定性函数（不依赖 ring 坐标值），归入"禁进 resolver inputs、每轮重算"是**保守且正确**的分类。
- **测试锁到位**：BIND-2（L1305，同一 direction facts 在 pre/post-0.24m ring 各重派生、fingerprint/origin/frame hash 按 ring 不同、分别过 Va `_validate_bindings`）+ BIND-4（L1307，pre-transform binding 强塞 post ring → `va_projection_frame_invalid`）直接锁住 r1 的核心矛盾。

判定：BLOCKER 实质解除。重设计引入的 helper 内部 ring 校验码悬空另记 B5-R2-01（MAJOR，非 BLOCKER：它 fail-closed、不假绿，只是接线未封口）。

### B5-R1-02 · MAJOR → **CLOSED**
§13.1 新增独立拒例组 SRC-C1…C10（L1287–1298），逐条对应 r1 六类漏锁：C1/C2=plan 立 sill / elevation 立 host → `claim_permission_invalid`（r1#1）；C3/C4=producer 预填 segment ref / resolver audit（r1#2）；C5/C6=重复 locator / 重复 observation（r1#3）；C7=floor_ref 非连续（r1#4）；C8=elevation z 归层不符（r1#5）；C9/C10=dangling claim 双门（r1#6）。L1285 明令"每行一个独立 test，不得参数化成一次调用只断总失败"——满足 r1 的"独立测试"要求。

### B5-R1-03 · MAJOR → **CLOSED**
§3.3 改写（L207–219）：L209"入口只做分派决策与模式标记，绝不能在入口提前执行 window pass；`_apply_legacy_window_pass` 执行位置保持现码顺序（结构 axis snap + canonicalization + z-stack 之后原位）"——解掉 r1 的"入口先跑 clamp 用未 snap 边界"回归。搬家清单（L211–215）已剔除 geometry 侧件，只留 correction 核内项；geometry 侧（`_legacy_cardinal_window_verts`、naming、specs serializer）L217 明列"原模块原位置保留、不得搬入 deterministic.py"。回归锁：§13.7 L1406"v1 与 v2 各有一个 cell 边界被 structural snap 移动、window 恰需按移动后边界 clamp 的 fixture，断言与改造前 snapshot 一致"。

### B5-R1-04 · MAJOR → **CLOSED**（时序洞真解，无新环）
分离方案成立：
- host record `WindowHostResolutionV1`（L475–495）**移除** Va negative/corroboration，L515 明述"避免 Va ledger 要 output hash、output audit 又要 Va digest 的自引用环"；negative/corroboration 独立到 sidecar `WindowEvidenceLedgerV1`（L534–547）。
- 真实 hash 时序：§3.2 步骤 9（L200）用**与 writer 同一 serializer** 预序列化 → 真实 output/feature SHA 封入 `PreparedCandidateIdentity`，L200"禁止占位 64-hex"；步骤 10（L201）Va ledger `source_output_sha256`/`feature_states_sha256` **必须等于**步骤 9 真实 hash。
- 环验证（我亲验）：output.json 依赖 `resolution_sha256`（audit row 进 geom.corrections，§5.3 L631/L649），`resolution_sha256` 只依赖几何（不含 Va）→ 单向；sidecar `window_hosts.json` 引用 output hash → 单向；output 不引用 sidecar hash。**无环**。不变量 #16（L129）钉死"Va evidence 不得改已序列化 geom/audit；若需改 output 则时序 INVARIANT"。
- 测试锁：VA-ID1（L1371，ledger output/feature hash 与最终两 artifact 逐字节一致）+ VA-ID2（L1372，占位/旧 attempt hash → finalize/writer/loader 三处分别拒 `va_identity_invalid`）。

### B5-R1-05 · MAJOR → **CLOSED**
§13.6#16（L1393）改为"手工构造 FinalizeResult、只改 window_host_claims 一条 span/digest 直接喂 writer；writer 从 fresh output 调真 `window_host_module.recompute_window_host_claims` 并拒；不 patch 算法符号"；#17（L1394）对偶探针"只 patch `finalize.resolve_window_hosts` 绑定，writer 内部 module-qualified import 不受影响并拒"；L1398 明令"禁止全局 patch `window_host.resolve_window_hosts`（会同时改真复算核）"。§9.1 步骤 5（L972）把"writer 方法内 `from src.agent.correction import window_host as window_host_module` 独立调用"升为被测契约（正是 r1 要求）。

### B5-R1-06 · MINOR → **CLOSED**（另见 B5-R2-02/03 的收尾）
§6.6 建立"窄捕获 `FacadeApplicabilityInvariantError` → 必转 typed reject"：va_claim_ledger_invalid→`claim_evidence_invalid`、va_projection_frame_invalid/va_direction_unresolved→`direction_binding_invalid`、va_identity_mismatch/va_visibility_ledger_invalid→`va_identity_invalid`；未知 code 不降级作 INVARIANT（L805–810）。§5.2 conflict wire 补 3 个 Va-mapped reason + `upstream_error_code` + `_upstream_code_shape` validator（L601–624）+ `map_va_applicability_error` helper（L701–706）。L805/L811 明述"窄类型捕获后必转 reject 不违反 broad-except 禁令"。测试 VA-ERR1/2/3（L1368–1370）。属性 claim 零交语义已明确（L803 给 existence→`source_geometry_mismatch`、属性→`claim_evidence_invalid`）。

### B5-R1-07 · MINOR → **CLOSED**
§3.2 步骤 5（L196）`dry_geom = geom.model_copy(deep=True, update={"facade_segments": list(transient_segments)})` 一次性视图、用后丢弃、不回写；§6.1 L709"dry 传一次性 dry_geom、final 传持久化 segments 后的 final geom；**不设 segments_override**，从签名上杜绝原 geom 无 segments 却私传第二真值"——正是 r1 建议方案。

### B5-R1-08 · MINOR → **CLOSED**
旧函数重命名 `_legacy_cardinal_window_verts`（L69/L217/L791），新公开接口 `window_verts_on_line`（无下划线，L28/L771）；§6.5/§8.2/§10.2/§13 引用一致。命名冲突解除。

### B5-R1-09 · MINOR → **CLOSED**
§6.5 实现块（L782–789）改用 tuple 解包 `q0x, q0y = host_line.point_at(t0)`（与 L762 返回型 `tuple[float,float]` 一致），`_orient(v, np.array([nx,ny,0.0], dtype=float))` 明确 3D 适配，L791"`_orient` 明确是现 modelling.py 3D normal 适配、normal 先升 (nx,ny,0)"。冻结块自洽。

### B5-R1-10 · MINOR → **CLOSED**
§4.4#7（L363）+ §11（L1120）+ §12.2（L1165–1166）把"z 升序 rank ↔ manifest 整数"登记为 B-M 合同 `manifest_floor_order_v1 = 1-based ascending floor.z`，B-M/`ViewManifest` 侧校验 plan required floor_ref 去重后无 gap `1..max_ref`，B5 再验 `max_ref == len(geom.floors)`；两 code 分离：`manifest_floor_ref_non_contiguous`（结构）vs `floor_ref_window_mismatch`（与窗层不符）——正是 r1 要求的区分 + 登记到 B-M。测试 SRC-C7。

### B5-R1-11 · MINOR → **CLOSED**
§6.4#5（L746）plan 分支现在也先在全部相邻 room intervals 检验 C、"C 对两 room 各正宽交且无一完整包含 → `cross_room_boundary`"，再落 zero/multiple。测试拆 GEO-9P（plan）+ GEO-9E（elevation）（L1321–1322）。诊断对称化。

### B5-R1-12 · NIT → **CLOSED**
§9.2（L993–995）`correction_b5_orientation_v1` 六键全列展开，不再用"同上"。

### B5-R1-13 · NIT → **CLOSED**
§5.1 加 `_normal_and_visibility_shape` model_validator（L497–512）：normal 必须四 cardinal 单位向量之一；plan 分支 visible_overlap_intervals 必须空、elevation 必须非空且 canonical union；L515 补述 plan 固定空 tuple、elevation 固定 target∩visible union。测试 LINE-8（L1338）。

---

## 二、新 finding（v2 重设计带出，B5-R2 编号）

### B5-R2-01 · MAJOR · §4.5 helper 的两个 ring-tamper 拒绝码悬空——无异常类 / 无捕获点 / 未进 conflict wire / 无测试锁

**判据**：§4.5 helper 步骤 1–2（L429–430）定义两个安全拒绝码：`direction_binding_ring_invalid`（"segment 所带 fingerprint 与 current ring 任一不符即拒"）、`direction_binding_ring_incompatible`（"同一 elevation view 覆盖各层 footprint fingerprint 与 family extent 逐值相同，否则拒，不任选一层"）。但全稿：
- 这两个 code **不在** §4.4 `WindowResolverInputError` code vocabulary（L399），**不在** §5.2 `HostConflictReason` 枚举（L562–586，那里只有语义不同的 `direction_binding_invalid`，专给 Va 的 `va_projection_frame_invalid/va_direction_unresolved`），**不在** `map_va_applicability_error` 覆盖（L807–809 只映射 `FacadeApplicabilityInvariantError`）；
- helper 抛什么异常类型未定义。§6.6 的窄捕获只接 `FacadeApplicabilityInvariantError`（Va 的）；helper 住在 `window_sources.py`，不该也不宜抛 Va 异常类，故其抛出物**无捕获点** → 要么裸传播成非 typed crash，要么诱导执行者加 broad-except（被 §1 L82 明令禁止）；
- **无测试**。BIND-1（L1304）测的是 build_verified 层的 `direction_fact_invalid`；BIND-2/BIND-4 测的是 Va `_validate_bindings` 层。helper 自身的 ring 校验分支（尤其 **dry 路径**——B2b 之前，Step1#6 的 final-ring fingerprint 门尚未介入，helper 的 fingerprint 校验是该处唯一防线）零覆盖。

这是委托单 §5"所有安全拒绝分支必须有测试锁、负轴不得缺"+"信任根 fail-closed 必须 typed（禁 broad-except 吞、裸 raise 丢 evidence）"的正面命中，且恰是本次 BLOCKER 重设计的**核心 ring-tamper 保护**——悬空 = 该保护未真正落地。定 MAJOR（非 BLOCKER：它 fail-closed、不导致错误 accepted，只是接线/诊断/测试未封口）。

**修法方向**：①§4.5 给 helper 定义专用窄异常类（如 `WindowDirectionBindingError(code, context)`，或明确复用 `WindowResolverInputError`），把两个 code 纳入其 vocabulary；②§5.2 或 §4.4 明确这两个 code 落哪条 typed conflict/入口拒绝路径（建议归 `direction_binding_invalid` reason 或新增 ring 专属 reason，并写 `fallback_action`——ring 篡改应是 `invariant_no_geometry_commit`）；③§3.2 步骤 5/6（dry/post）与 §6.6（final）分别指定 helper 异常的捕获→typed reject 路径；④§13.1 BIND 组加两条独立测试：dry helper 收到 fingerprint 不符的 transient segments → `direction_binding_ring_invalid`；构造各层 fingerprint/extent 不一致 → `direction_binding_ring_incompatible`。

### B5-R2-02 · MINOR · §6.6 pre-Va "可运行门"与 Va 内部 positive intersection 双实现，existence 零交诊断码多源、确定性依赖执行顺序

**判据**：§6.6 L803 要求"每个 positive claim 先执行同一可运行门：source interval 映 world 与 final clamped target 取交、交宽 > span epsilon；existence 零交报 `source_geometry_mismatch`、属性零交报 `claim_evidence_invalid`"。但同一 intersection 判定 Va 内部也做（`facade_applicability.py:447–449,463–465` → `va_claim_ledger_invalid`），且 Step1#4（L720）对 existence 零交也报 `source_geometry_mismatch`。于是 existence 零交有**三处**可触发（Step1#4 / §6.6 L803 / Va-mapped），属性零交有两处（L803 / Va-mapped→`claim_evidence_invalid`）。诊断码正确性靠"L803 先跑拦住、Va 不被调到"这一执行顺序保证——正确性无损（都 fail-closed），但**唯一权威触发点/code 依赖实现顺序**，易在返修/多人施工时漂移。且 R1-06 的 `map_va_applicability_error` 已能把 Va 的零交映射成 `claim_evidence_invalid`，L803 的前置属性门与之冗余。

**修法**：明确 existence/属性零交的唯一权威触发点与 code（建议 existence 只在 Step1#4、属性只走 Va→mapper），或加一条断言"L803 前置门与 Va 内部 intersection 对同一输入判定一致"以钉死双实现不漂移。

### B5-R2-03 · MINOR · `map_va_applicability_error` 三类映射分支只锁了一类

**判据**：mapper 三类映射（L807–809）：`va_claim_ledger_invalid→claim_evidence_invalid`、`va_projection_frame_invalid/va_direction_unresolved→direction_binding_invalid`、`va_identity_mismatch/va_visibility_ledger_invalid→va_identity_invalid`（后者还带 `_upstream_code_shape` 强制 `fallback_action=invariant_no_geometry_commit`，L622–623）。但测试只有 VA-ERR2（L1369，`va_claim_ledger_invalid` 一类）+ VA-ERR3（未知 code→INVARIANT）。**`direction_binding_invalid` 与 `va_identity_invalid`（含 invariant fallback 断言）两条映射分支无独立锁**。BIND-4（L1307）测的是 Va `_validate_bindings` 直接拒 `va_projection_frame_invalid`，走的不是 finalize 的 mapper 路径。§16 开放问题 #7 自陈"Va typed-error 拒例是否逐项独立"——正命中此缺。

**修法**：§13.5 VA-ERR 组补两行：窄型 callable 抛 `va_direction_unresolved` → mapper 转 `direction_binding_invalid`；抛 `va_identity_mismatch` → 转 `va_identity_invalid` 且 `fallback_action=invariant_no_geometry_commit`。

---

## 三、回归扫（新机制未引入新 shipped-untested / fail-open / 自指 / 自包含违规 / v1-v2 回归）

- **fail-open**：§6.6 窄捕获 + 必转 reject + 未知 code 作 INVARIANT（L805–810）、§9.1 L979"禁 try/except 后只丢 sidecar 仍接受 output"、§13.6 L1398 source scan 锁 no broad-except——纪律完整。**唯一漏点** = B5-R2-01（helper 抛出物无捕获路径，存在被 broad-except 吞或裸 crash 的接线真空），已记 MAJOR。
- **自指假绿**：冻结向量仍手写字面量、禁调 production hash helper（L311/L1265/L1400）；BIND-3（L1306）judge parity 用**独立手写冻结**的 ring 字段与 frame hash、不取 production helper 输出（防自指）；VA-ID1/VA-ID2 用真实 artifact 逐字节比对。无自指。
- **hash 环**：已亲验解除（见 B5-R1-04 复核），无新环。
- **累计自包含**：全文重写，grep 无"沿用上一版/vN 不变"式引用（唯一命中是 L9 禁令本身）；§9.2 六键展开。无违规。
- **v1/v2 行为回归**：§3.3 入口只决策 + §13.7 L1406 snap-moved-boundary 回归 fixture + L1407 lax-extra 伪 ref 行为不变 + L1408 `window_clamp_to_parent=False` 语义不变。锁齐。
- **judge 独立性/cache**：§10.5 与现码相符（`score_schema.py:276 accepted_stage_record_sha256` 已在，capability key 纳入 artifact contract L1087 合理）；production 禁 import judge（L413/L436/L1089）、测试可 import judge 作 parity oracle（L436/L1306）——边界清晰。

## 四、定稿路径

- **可定稿：接近**。BLOCKER 0、r1 十三条全闭、无新 BLOCKER、无新 fail-open 假绿设计缺陷。
- 施工前 sol 须落实 **B5-R2-01（MAJOR，必办）** + B5-R2-02 / B5-R2-03（MINOR，随文修）。这些均为现有机制内的有界补丁（helper 异常接入既有 typed-conflict wire + 补测试），不触动主链设计。
- **建议流程**：sol 交增量 diff（仅 §4.5/§5.2/§6.6/§3.2/§13 的对应段落）→ 我复核该窄增量即 APPROVE，**无需第三轮完整对抗审**。若主控愿凭 diff 直接确认 B5-R2-01 已按修法落实，亦可视作 A-W-C 条件满足。
