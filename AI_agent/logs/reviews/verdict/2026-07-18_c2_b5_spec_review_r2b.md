# B5 施工细稿 v3 窄增量复核判词（r2b）

- 日期：2026-07-18
- 审稿人：Fable 5（Claude 侧最高档对抗审；批准权威）
- 审对象：`AI_agent/proposals/c2_b5_detail_spec.md`（sol v3，窄增量：仅闭合 r2b 三条收尾）
- 前轮：`2026-07-18_c2_b5_spec_review_r2.md`（APPROVE-WITH-CHANGES，0 BLOCKER + 1 MAJOR〔B5-R2-01〕 + 2 MINOR〔B5-R2-02/03〕；r1 十三条全 CLOSED，BLOCKER 重设计主链已判 CLOSED）
- 审法：窄增量复核，只看 §3.2 / §4.5 / §5.2 / §6.6 / §13.1 / §13.5 改动节，主链不复审

## 总裁决：**APPROVE（定稿）**

| | 计数 |
|---|---|
| 本轮待闭（3 条） | **全部 CLOSED** |
| 未闭 | **0** |
| 新洞 | **0** |

一句话：r2 的一 MAJOR 两 MINOR 收尾**真落地、非措辞糊弄**，且落地质量高于我给的修法下限（B5-R2-02 直接删掉 pre-Va 重复门、把理论漂移归为身份 INVARIANT，比"加一致性断言"更彻底）；三处补丁全部在既有 typed-conflict 机制内接线，未引入 broad-except / 自指 / 未定义行为。**B5 细稿定稿。**

---

## 逐条复核（引 v3 行号）

### B5-R2-01 · MAJOR → **CLOSED**（helper ring-tamper 收尾四要件全落地）

1. **专用窄异常类**：§4.5 L418–430 定义 `DirectionBindingErrorCode = Literal["direction_binding_ring_invalid","direction_binding_ring_incompatible"]` + `WindowDirectionBindingError(ValueError)` 带 typed code/context；L441 明令"helper 唯一业务异常，不能复用 `FacadeApplicabilityInvariantError`、不能转普通 `ValueError` 或被 broad-except 吞"。✓
2. **纳入 conflict wire + fallback=invariant 强制**：§5.2 `upstream_error_code` Literal 加两 code（L623–624）；`_upstream_code_shape` validator 新增段（L642–649）硬性要求这两 upstream code → `reason_code=direction_binding_invalid` **且** `fallback_action=invariant_no_geometry_commit`，否则 raise。唯一 mapper `map_direction_binding_error(exc,*,geom,verified_inputs,phase)`（L655–667）每 row 固定 `reason_code=direction_binding_invalid / upstream_error_code=exc.code / fallback=invariant_no_geometry_commit / blocking=True`；L667 明令"mapper 不得调用 Va error mapper，也不得改写成 `direction_fact_invalid`（事实没错，错的是 current ring/segments 身份）"——诊断归属正确、与 Va mapper 隔离。✓
3. **dry/post/final 三处捕获→typed reject**：dry_pre_transform（§3.2 步骤5 L196"窄捕获 → `map_direction_binding_error(phase="dry_pre_transform")` → typed reject；不得裸传播、吞掉、回滚后继续"）；dry_post_transform（步骤6 L197"不能被 B2b 普通几何回滚掩盖后继续"——正堵住 r2 该担点）；final（步骤8 L199 + §6.6 L843"try/except `WindowDirectionBindingError` 窄边界，绝不进入下面的 `FacadeApplicabilityInvariantError` 捕获器"——与 Va 捕获器显式分流）；§4.5 L452 三处汇总。✓
4. **§13.1 两条独立测试**：BIND-5（L1355，dry helper transient fingerprint 不符 → 独立抛 `direction_binding_ring_invalid` → mapper 转 direction_binding_invalid+invariant，锁"不被 B2b 回滚掩盖"）；BIND-6（L1356，各层 fingerprint 自匹配过 Step1、但跨层 fingerprint/extent 不一致 → Step2 独立抛 `direction_binding_ring_incompatible`，不任选一层）。两条精确隔离两 code、互不混淆，post/final 捕获边界均断言。✓

### B5-R2-02 · MINOR → **CLOSED**（existence/属性零交唯一权威触发点，方案比建议更彻底）

§6.6 L845–850 改写为"intersection 只有两个互斥业务权威触发点，**不设通用 pre-Va 重复门**"：existence 唯一权威 = Step1#4（零交只报 `source_geometry_mismatch`；Va adapter 仅在 resolver/recompute 成功返回后调用，成功返回建立 `existence_overlap_verified` runtime invariant，L847 明述"不新增 wire/hash 字段"）；属性 claim 唯一走 Va `_intersect` → mapper 转 `claim_evidence_invalid`（L848）。L850 把"Step1 已过但 Va 仍报 existence 零交"归为**映射漂移** → 固定转 `va_identity_invalid + invariant_no_geometry_commit`，禁止转 source_geometry_mismatch/claim_evidence_invalid——"同一输入不会因执行顺序得到多个业务 code"。§6.6 L854 捕获器同步（va_claim_ledger_invalid 且 context claim 非 existence → claim_evidence_invalid；为 existence → va_identity_invalid）。测试 VA-ERR1（L1417，锁"无前置属性门"）+ VA-ERR6（L1422，锁漂移路径）。✓ 直接删重复门根除双实现漂移，优于我要求的一致性断言。

### B5-R2-03 · MINOR → **CLOSED**（mapper 两分支补独立锁）

§13.5 VA-ERR4（L1420，`va_direction_unresolved` → mapper 独立转 `direction_binding_invalid` 且保留 upstream code）+ VA-ERR5（L1421，`va_identity_mismatch` → 独立转 `va_identity_invalid` 且**严格断言** `fallback_action=invariant_no_geometry_commit`）。正是 r2 要求的两条含 invariant fallback 的独立锁。✓

---

## 新洞扫描（三处补丁未带出）

- **fail-open**：三处补丁全走窄捕获 `WindowDirectionBindingError` → 必转 typed reject；未知 code / existence 漂移均落 INVARIANT（L850/L857）；helper 异常绝不被 B2b 回滚掩盖（L197/BIND-5）。无 broad-except。
- **自指假绿**：BIND-5/BIND-6 是独立 fixture 断言真实抛出的 typed code，非自产自比；BIND-3 judge parity 仍用独立手写冻结值。无自指。
- **未定义行为**：异常类、两 code、reason 映射、fallback、三处捕获点、mapper、零窗兜底（L667"零窗跳过 binding materialization"、"无法缩小范围时覆盖本批全部 window"）全定义齐。两 mapper（direction vs Va）L667 明令不交叉；`direction_binding_invalid` reason 虽可由两源产生，但 upstream_error_code 可区分、validator 各段不冲突。
- **runtime invariant 取舍**：`existence_overlap_verified` 刻意不落 wire/hash（避免新增自报信任根），由 VA-ERR6 漂移检测兜底——正确取舍，且 recompute 路径同样重跑 resolver 核（含 Step1#4）后才调 Va（L847 "resolver/recompute 成功返回后"涵盖），无绕过。

**定稿。** B5 细稿 v3 = 施工-ready，可交执行档实现。
