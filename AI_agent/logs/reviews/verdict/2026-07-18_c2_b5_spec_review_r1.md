# B5 施工细稿 v1 对抗审判词（r1）

- 日期：2026-07-18
- 审稿人：Fable 5（Claude 侧最高档，跨厂商对抗审；谁写谁不批——sol 出稿 → Fable 批）
- 审对象：`AI_agent/proposals/c2_b5_detail_spec.md`（sol v1，1334 行）
- 对照源（全部自读原文，未采信任何转述）：委托单 `logs/reviews/request/2026-07-18_b5_spec_dispatch.md`；设计权威 `proposals/c2_full_unlock_design.md` §E1'（L24–35）/§E2'（L37–56）/§122（L122）/§128（L128）；范式 `c2_b4b_detail_spec.md`、`c2_b2_detail_spec.md`；现码 `6d5fd1b`：`src/agent/correction/{schema,claims,parse,deterministic,finalize,facade_applicability,envelope_transform,orientation,feature_state}.py`、`src/agent/geometry/modelling.py`、`src/validator/checks/correction.py`、`src/agent/correction/geometry_validator.py`、`src/agent/execution/{manifest,view_manifest}.py`、`src/agent/judge/{opening_claim_score,score_inputs,score_schema,score_service}.py`、`src/agent/output_coordinates.py`、`src/configs/correction.yaml`
- 审法：spec 审（施工-readiness / 正确性 / 防假绿 / 纪律），两枚冻结哈希向量本审已独立复算验证，未跑测试套件

## 总裁决：**REWORK**

| severity | 计数 |
|---|---|
| BLOCKER | **1** |
| MAJOR | **4** |
| MINOR | 6 |
| NIT | 2 |

一句话：本稿的两支判据、trusted-negative、`_window_verts` 线段化、legacy 隔离、容差纪律、测试反自指纪律都做得扎实（验真清单见文末），但 **Va elevation binding 的生命周期与 ring 变形互相矛盾（B5-R1-01）使 §3/§4/§6 主链按本稿字面不可施工**——执行者必然要在头号信任根路径上自行发明机制，这正是连续 8 批 MAJOR 的温床。加上四处 MAJOR（漏锁的拒绝分支、legacy 分派措辞可实现成行为回归、Va ledger 身份字段时序洞、writer 防篡改探针自相矛盾），必须返工重交。

---

## BLOCKER

### B5-R1-01 · BLOCKER · elevation binding 冻结进 content-hash 输入，与 ring 全生命周期变形不可调和；且生产侧 binding 构造者无主

**判据**：
- 稿 §3.1（L134–141）数据流把 "Va elevation bindings" 画在 **LLM v3 draw 之前**就并入 `WindowResolverInputsV1`；§4.3（L294–311）把 `elevation_views: tuple[VaElevationViewBindingV1, ...]` 冻进带 `content_sha256` 的 strict wire；§4.4 builder 签名（L339–345）在 **structural core 之前**（§3.2 步骤 2，L181）构造并 hash 封口。
- 但 `VaElevationViewBindingV1`（= Va 的 `ElevationViewBindingV1`，`facade_applicability.py:103–117`）含三个 **ring 依赖字段**：`source_footprint_fingerprint`、`along_origin`、`frame_transform_sha256`（后者的 preimage 含前两者，`facade_applicability.py:326–330`）。Va 在消费时硬校验：binding fingerprint 必须等于**当前几何**的 floor fingerprint（`facade_applicability.py:454–455`），`along_origin` 必须等于**当前 segments** 的 family extent 端点（L456–459）——否则 `va_projection_frame_invalid` 硬 raise。
- 而 B5 的 ring 在生命周期内至少变两次：§3.2 步骤 3 snap/jitter/gap-close（现码 `deterministic.py:864–874` 对 v3 ring 逐点 snap）、步骤 6 B2b transform（envelope reconcile 常移边界 ~0.24m）。dry resolver（步骤 5）跑在 pre-transform ring 上，final resolver + Va negative check（步骤 8–9）跑在 final ring 上。**一份在步骤 2（甚至 draw 前）hash 冻结的 binding 元组，其 fingerprint/along_origin 不可能同时匹配这两个 ring，且通常两个都不匹配**（构造时 final ring 根本不存在——draw 前连 ring 都没有）。后果不是温和 fail-closed，而是：dry 阶段 elevation local→world 投影（§6.2 Step1#4，L564 "elevation只用Va binding投影"）用错 origin **静默投错区间**，final 阶段 Va fingerprint 必炸——合法 case 系统性全灭或静默错判。
- 叠加：全稿没有任何一处指定**生产侧由谁、用什么算法构造这些 binding**。§12.1 `window_sources.py` 只写"manifest/Va binding **验证**"；现码唯一构造点 `materialize_va_elevation_bindings` 在 judge 侧（`score_inputs.py:266–280`），而 §1 静态禁止项 + §10.5#7 明确禁止 production import judge。缺主 + 不可调和 = 新执行者只读本稿无法施工（违反 L9 自包含验收自检）。

**修法方向**：resolver inputs 只冻结 **ring 无关的方向事实**（`input_id / resolved_building_direction / resolution_source / mirrored / local_x_positive / orientation_output_hash / adapter_version / view_manifest_sha256`——即"不创造第二套 direction/mirror 解算"真正要保的东西）；新增一个 **production 侧确定性 helper**（落 `window_sources.py` 或 `window_host.py`，给出唯一准签名），在每次 Va/投影调用点按**当前 ring** 重算 `source_footprint_fingerprint / along_origin / frame_transform_sha256`，dry 与 final 各用各的 ring、同一 helper；并加测试：①方向事实被篡改 → 拒；②同一方向事实在 pre/post-transform 两个 ring 上重算出的 binding 均过 Va `_validate_bindings`；③与 judge 侧 `materialize_va_elevation_bindings` 的 frame hash 在同 ring 上逐字节 parity（防两套解算漂移）。§3.1/§3.2/§4.3/§4.4/§6.6 全部相应改写。

---

## MAJOR

### B5-R1-02 · MAJOR · §13 测试矩阵漏锁一批安全拒绝分支（shipped-untested 惯犯面）

**判据**（委托单 §5"所有安全拒绝分支必须有测试锁"；对照 §13 全部表格逐条比对）：
1. **claim 权限矩阵拒例缺失**：§4.4#5 + 权限表（L352–360）规定 plan 不能立 `sill/head/appearance`、elevation 不能立 `host`——13.1–13.8 无任何一条测 "plan source 链接 sill claim → 拒" / "elevation source 链接 host claim → 拒"。这是 E2' 证据政策的核心闸，无锁。
2. **draw 时 producer 预填拒例缺失**：§4.4 末段（L350）"producer 预填任一项直接拒绝"（`facade_segment_id` 非 null / 自报 reserved resolver audit kind）+ §5.3（L520）+ §6.2#7（L567）。现码 `parse.py:83–86` 只拒 `facade_segments`/`north_axis`，**不拒 window 级 segment ref**（稿 §1 行5 自己也点了这个洞）——但 13.x 没有一条 draw-contract 拒例。13.6 的 18 项全是 accepted 产物**事后**篡改，不覆盖 draw 入口。
3. §4.4#2 catalog 内**重复 locator / 重复 `(input,observation)`** 拒例缺失（SRC-E5 测的是两窗争一 locator，不是 catalog 去重）。
4. §4.4#7 **floor_ref 非连续 1..N** 拒例缺失（SRC-P3 只测错层）。
5. §4.4#8 elevation z 可唯一归层但与 `window.floor_id` 不符 → conflict，无锁（SRC-E4 只测 family 不符）。
6. claim 不在 source `positive_claims` / manifest `potentially_observable_claims` 内的 dangling-claim 拒例缺失。

**修法方向**：§13.1 增 SRC-C1…C6 六行（或并入 13.6 前置一节"draw/link 入口拒例"），逐条给 fixture + 稳定 reason code 断言；每条都是独立测试，不许合并成一个大测试（13.6 开头的纪律同样适用于此）。

### B5-R1-03 · MAJOR · §3.3 legacy 分派措辞可被实现成 v1/v2 行为回归；且"机械搬家"清单混装了不属于该函数的模块

**判据**：§3.3（L195）"`schema_version in {"1","2"}` 在 `apply_deterministic_core` **入口立刻分发**到 `_apply_legacy_window_pass`，该函数是当前 window block 的机械搬家"。现码窗口 block（`deterministic.py:966–1023`）跑在结构 snap / z-stack **之后**，cell-bbox clamp 用的是**已 snap 的** cell 边界。若执行者按字面在函数入口先跑窗口 pass，clamp 将用未 snap 的 cell 边 → v1/v2 行为改变，直接违反验收三层①（§128 / 稿 §15.1 第1层）。13.7 frozen snapshot 只在 fixture 恰好含"snap 会移动其 clamp 边界的窗"时才抓得到，不能靠它兜。另外该节清单（L197–203）把 `_find_parent_wall`、cardinal `_window_verts`、built naming、spec serializer 也列进 `_apply_legacy_window_pass` 的"搬家"内容——这些住在 `geometry/modelling.py`/`specs.py`，根本不在 deterministic 核的 window block 里，照写会诱导执行者跨模块乱搬。

**修法方向**：改写为"分派**决策**在入口做；`_apply_legacy_window_pass` 的**执行位置保持现序**（结构 snap 与 z-stack 之后原位），函数体 = `deterministic.py` 窗口 block 逐行等价搬移"；geometry 侧 legacy 件（`_find_parent_wall`/cardinal verts/naming/serializer）单列一段，明确"原模原样留在原模块，仅由 build 按 schema 分派"，与 correction 核的搬家清单分开。

### B5-R1-04 · MAJOR · §6.6 生产内调 Va 时 visibility ledger 的身份字段在该时点不存在，构造方式未定义 → 信任根上的自报身份洞

**判据**：§6.6（L641–644）要求"visibility ledger 从 final accepted-candidate `facade_segments` 独立构造"。但 `FacadeVisibilityLedgerV1`（`facade_applicability.py:87–97`）要求 `source_output_sha256: Hex64` 必填，且 `source_kind="accepted_correction"` 时 Va 硬校验 `feature_states_sha256` 非 None + `helper_versions` 精确（L294–298）。按 §3.2 时序，Va negative check 在步骤 9，而 output 序列化/hash 在步骤 12（writer），feature state 派生在步骤 11——**步骤 9 时这两个 hash 都不存在**。Va 对这两个字段只查"在场"，不与任何东西对账（身份回声字段）——执行者最省事的解法就是填占位 64-hex，即在 C2 头号信任根路径里塞自报身份，恰是委托单 §3#2 点名要打的形态。稿对此零着墨。

**修法方向**：明确二选一并写死：(a) 步骤 9 前对 candidate geom 做一次与 writer 完全同一 serializer 的预序列化取 hash（writer 步骤 1 复算后必须 byte 相等，不等即 INVARIANT），feature-state 派生同理提前且 writer 复算比对；或 (b) 重排时序把 Va negative check 挪到 writer 内、output/feature hash 已定之后、accepted 判定之前（rejected 语义不变）。无论哪条，都要加一条测试：ledger 身份字段与最终 artifact hash 逐字节一致，占位/错位 → 拒。

### B5-R1-05 · MAJOR · §13.6#16 防篡改探针按字面自相矛盾——monkeypatch `resolve_window_hosts` 会同时骗过 writer 复算，探针要么测不出要么被弱化成假绿

**判据**：§13.6#16（L1177）"monkeypatch `resolve_window_hosts` 返回伪 claims，writer 独立 recompute 拒绝"。但 §6.1（L531–555）明文规定 writer/loader 调 `recompute_window_host_claims`，而 dry/final/recompute **调同一 candidate 算法** `resolve_window_hosts`。全局 monkeypatch 该符号 → writer 复算同样返回伪 claims → 比对通过 → 期望的拒绝不发生。执行者撞上后最可能的"修复"是弱化断言——这正是恒真自检/假绿前科（Va `_relevant_negative`、PhaseC `x!=x`）的再生产路径。

**修法方向**：写死注入点：不 patch 算法符号，而是**手工构造一个 `FinalizeResult`，其 `window_host_claims` 为伪造**（改一条 record 的 span/digest），直接喂 writer——writer 用自己 import 的真算法复算即必拒。同时补一条对偶探针：patch **finalize 模块名下**的绑定（`finalize.resolve_window_hosts`）而 writer 从 `window_host` 模块自行 import，证明 writer 复算路径与 finalize 路径无共享可劫持接缝（这也顺带把"writer 必须独立 import"变成被测契约而非注释）。

---

## MINOR

### B5-R1-06 · MINOR · §6.6 调 Va 时的 `FacadeApplicabilityInvariantError` 处置未定义 → fail-closed 但无 typed conflict
Va 对如 "claim 证据区间与 target 零交" 是硬 raise（`facade_applicability.py:447–449,463–465` → `va_claim_ledger_invalid`）。B5 在链验时只对 existence 要正宽交（L564），width/along 等属性 claim 的证据在 final clamped target 上完全可能零交 → finalize 中段裸 raise，既无 `WindowHostConflictV1` 也无 §5.2 reason code（枚举 L448–469 无对应项）。L564 后半句"width/along claim 才要求相应属性 coverage"语焉不详——在哪一步、按什么判据、失败落什么 reason，全没说。**修法**：明确 §6.6 捕 `FacadeApplicabilityInvariantError` 后按 code 映射到 typed conflict（新增 reason 或归 `source_geometry_mismatch`/input invariant），attempt rejected 带 evidence；补一条测试锁；把 L564 的属性-claim 验证语义写成可执行判据。（注意：这不是允许 `except Exception` 吞——是**窄类型捕获 + 必转 typed reject**，与 §1 静态禁止项不冲突，需在稿内明说以免执行者因禁令不敢接。）

### B5-R1-07 · MINOR · §3.2 步骤 5 transient Vg 的段结果如何进 `resolve_window_hosts` 未指明
签名（L531–537）只收 `geom`，而步骤 5（L182）禁写 `geom.facade_segments`。执行者要么违禁写入要么自创第二签名。**修法**：写死"dry 路径构造一次性 `model_copy(update={"facade_segments": transient})`，用后即弃、绝不回写原 geom"，或给 `resolve_window_hosts` 加显式 kw-only `segments_override`（并说明 final 路径禁用该参数）。

### B5-R1-08 · MINOR · 新旧 `_window_verts` 同名共存未定名；"公开低层接口"却带下划线
§3.3 legacy 保留 cardinal `_window_verts`（`modelling.py:303`），§6.5（L615–621）又冻结同名新签名，§12.2 两者都落 `geometry/modelling.py` 域 → 直接命名冲突。§0#7 称其"公开低层接口"，下划线私名与"公开"自相矛盾（C4 要复用它）。**修法**：给出唯一命名定案（如 legacy 改 `_legacy_cardinal_window_verts`，新接口定 `window_verts_on_line` 或保留 `_window_verts` 但明写"模块内私有、C4 经同模块扩展"），并更新 §6.5/§12/§13.3 一致引用。

### B5-R1-09 · MINOR · §6.5 冻结实现块与自己冻结的签名不符
`SegmentLine2D.point_at` 声明返回 `tuple[float,float]`（L606–608），实现块却写 `q0.x/q0.y`（L628–630）——tuple 无属性访问，照抄即 `AttributeError`。`orient(v, outward_normal_xy)` 用 2D normal，而现码 `_orient` 吃 3D np 向量（`modelling.py:281`）——适配未着一字。冻结块是执行者逐字照搬的对象，必须自洽。**修法**：统一为下标访问或把 `SegmentLine2D` 升为带 `.x/.y` 的 Point 型；orient 适配给一行定义（2D normal 升 (nx,ny,0) 后走现 `_orient` 或新写、二选一写死）。

### B5-R1-10 · MINOR · floor_ref"z 升序 rank ↔ manifest 整数"是新契约语义，未登记到 B-M 侧
§4.4#7（L323）把 manifest `floor_ref` 解释为"z 升序 rank、连续 1..N"。现码 B-M 只强制整数 + 唯一（`view_manifest.py:651–655`），从未承诺"1 = 最低层"。语义靠 B5 单方假设：用户若倒序编号，产物会以 `floor_mismatch` 全灭且诊断误导（fail-closed 但不可解释）。**修法**：该语义作为 B-M manifest 合同补充登记（B-M 文档/A0 §5 registry），B5 校验给专属 reason（区分"非连续"与"与窗层不符"），并连同 B5-R1-02#4 的拒例测试一起落。

### B5-R1-11 · MINOR · plan 分支跨 room seam 只能落 `zero_room_interval_candidates`，诊断不对称
§6.4#5/#6（L590–591）：`cross_room_boundary` 只在 elevation 分支精确报；plan 窗跨 declared room 的 seam 时归并进 zero。两者 A3/interactive 的呈现与用户动作完全不同（补 room 划分 vs 改窗位）。正确性无损（都 fail-closed），但 conflict 纪律的价值一半在可解释性。**修法**：plan 分支同样先检"C 对相邻两 room interval 各有正宽交且无一完整包含"→ 报 `cross_room_boundary`，再落 zero；GEO-9 拆成 plan/elevation 两条断言。

---

## NIT

### B5-R1-12 · NIT · §9.2 冻结契约表用"同上"（L816）
`correction_b5_orientation_v1 required/allowed = 同上`——本稿明令禁止"沿用式"引用，冻结表里自己用"同上"虽是同文档近距引用，仍应展开为六键全列（对照 `manifest.py:179–210` 的逐键风格）。

### B5-R1-13 · NIT · record wire 层两处可再拧
①`segment_outward_normal: tuple[Literal[-1,0,1], Literal[-1,0,1]]`（L408）允许 (0,0)/(±1,±1)，单位性只靠下游 `invalid_host_line` 兜（hash 链确实覆盖篡改，故仅 NIT）——wire 层加一个 model_validator 与 `FacadeSegment._valid_segment`（`schema.py:148`）同款约束更省心。②`visible_overlap_intervals`（L418）在 plan 分支的内容（空元组？不适用哨兵？）未定义，writer/loader 复算虽同码自洽，但跨版本重放需要定死。

---

## 验真通过项（本审亲核，sol 返修时不必重证）

1. **两枚冻结哈希向量独立复算全对**：locator preimage 字面量 UTF-8 SHA-256 = `d4e4d28c48522a4852047b9c7f257b9370692c9c186a85c884c2774f2fa9d2e2`（本审用独立脚本算得，与 L281 一致）；`[]` = `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`（与 L443 一致）。冻结向量纪律真实成立、非自指。
2. **§1 现码对账表 10 行逐行核真**：cell-bbox clamp（`deterministic.py:984–990`，v3 也在走——B5 拆分确有必要）；B2b `resolve_unique_window_host` 要求 room 非空（`envelope_transform.py:279`，时序环真实存在）；v3 draw 不拒 window 级 segment ref（`parse.py:83–86`）；`_find_parent_wall` 0.05 硬码 + `dot>0.9` 宽门（`modelling.py:334–352`）；`check_windows_on_wall` 仅 room bbox + `_SPAN_TOL=0.10`（`geometry_validator.py:47,231–257`）；judge temporary binding 不写回（`opening_claim_score.py:52–68`）；contracts 现仅四件套（`manifest.py:173–210`）；双同名 `ElevationViewBindingV1` 认准 Va 13 字段型且明令禁 gt_manifest 型（§4.3 L301–309）——REC-C 坑已正确规避。
3. **source-aware 两支与 §E1'.2 严丝合缝**：plan hidden bypass（不变量 #5/#6、SRC-P1/P2）；elevation 只在 visible 正宽交候选、partial visible 允许挂实体（SRC-E2 ↔ E2'.5 existence fragment）；plan+elevation 并存走 plan 且立面不反向赶窗（§0#2、SRC-P2）；段跨多 room、段 id ≠ room 分别解析分别断言（不变量 #7、GEO-8）；跨段优先于端点 clamp（§6.3#1→#2 + §7.1 优先级）正面回答了 §16 开放问题 3——clamp 不可能掩盖跨段。
4. **trusted-negative 与 B4b Phase C 教训对齐**：八条件缺一即 `uncorroborated`（§7.3），完整性只认受信 manifest 机读位 `negative_evidence_capable_claims` + coverage/assertion 闭环（对照 `view_manifest.py:190–214` 的 iff 校验，机制真实存在）；elevation negative 区间经 Vg visible 相交、hidden 残差天然挡完整覆盖（`facade_applicability.py:479–482` 亲核，§7.3#7 描述准确）；产品自报不改判（NEG-7）；双向判据（NEG-9）；不删窗不降级（NEG-4/5）。
5. **`_window_verts` 真线段化、非换皮**：函数体禁 facade/x/y 分支（L634）、LINE-2/3 负轴手写期望、LINE-7 锁"世界升序写回"假绿、LINE-4 diagonal 正例 + LINE-5 C2 拒斜——接口为 C4 预埋且不偷扩 C2 capability，符合不变量 #6。
6. **容差纪律**：三项独立命名 + A0 登记 + 关系链（§11），明令不复用 `min_edge`/`_SPAN_TOL=0.10`/visibility epsilon；`window_clamp_to_parent` 降 legacy-only。
7. **feature-state 四轴不污染**：§9.2 拒把 resolver digest 塞四轴——对照 Va 对 `helper_versions` 的精确冻结检查（`facade_applicability.py:296`），此保护是必要且正确的（塞第五 helper 会炸掉 Va 现有 accepted-correction 身份校验）。
8. **E4 rebind 必要性核真**：`orientation.py:396` 现只收 `correction_b2_v1`，不做 §9.4 同步则 B5 落地后 E4 全断——§0.10 非越界而是必要闭环。
9. **judge 独立性声明与现码相符**：score cache 已绑 `accepted_stage_record_sha256`（`score_schema.py:276`），§10.5#5 增 capability key 的理由成立；proof 只作 identity gate、分数独立重算（§10.5#4 ↔ B4b §8.4.1 现实现 `opening_claim_score.py:71–111`）。
10. **累计式自包含**：全稿无"沿用上一版/vN 不变"式引用（唯一命中是 L9 的禁令自身）；结构与 b4b/b2 细稿范式一致（执行结论/对账/所有权/不变量/wire/主链/测试矩阵/Phase/验收）。

## 复审要求

r2 须交付：①B5-R1-01 的 binding 重设计全文（新 helper 唯一准签名 + 双 ring parity 测试 + §3/§4/§6 改写）；②§13 补齐 R1-02 六类拒例；③R1-03 的分派措辞与模块归属改写；④R1-04 时序定案二选一写死；⑤R1-05 探针注入点写死。MINOR/NIT 随文修。r2 仍由本审稿人终审，迭代至 APPROVE 为止。
