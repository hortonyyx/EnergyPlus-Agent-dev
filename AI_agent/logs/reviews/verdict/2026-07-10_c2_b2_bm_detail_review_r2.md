# C2 B2 + B-M 细稿 r2 对抗复审

Date: 2026-07-10  
HEAD: `7422f42`  
Objects: `AI_agent/proposals/c2_b2_detail_spec.md`、`AI_agent/proposals/c2_bm_view_manifest_spec.md`（v2）  
Governing design: `AI_agent/proposals/c2_full_unlock_design.md` v2.2；baseline: `AI_agent/proposals/c2_orthogonal_polygon_design.md` D1–D10  
B2 verdict: **REWORK**  
B-M verdict: **REWORK**

## 一、总裁决

主控确实采纳了 r1 的方向，但“16 条全采纳”不等于 16 条已闭合。本轮结论如下：

- B2：r1 8 条中 **3 CLOSED / 5 PARTIAL / 0 NOT-CLOSED**；新增 **7 findings（2 BLOCKER / 5 HIGH）**。
- B-M：r1 8 条中 **3 CLOSED / 5 PARTIAL / 0 NOT-CLOSED**；新增 **6 findings（2 BLOCKER / 3 HIGH / 1 MEDIUM）**。

严格子类族**可以保留，不要求退回“两棵完全独立且无继承的类树”**。它在 raw payload 解析层确实能形成两份 wire 合同：legacy 类零字段变化、v3 子类全层 `extra="forbid"`、未知版本先分发后拒绝。问题不在“用了继承”，而在细稿把“raw 分发器闭合”误写成“全部对象边界闭合”，并漏掉 Pydantic v2 的基类注解序列化语义。

v3 随 B2 生产发射的批次选择也正确，符合上位 DAG；但发射面尚未闭合：当前 capability 规则会让默认 `rectangular` profile 拒绝任何声明 `{rectangular, orthogonal_polygon}` 的 v3，target version 又没有作为单一值贯穿 prompt、inner validator、post-parse、finalize 与真实重抽。`declared`/`populated` 目前仍是口头二分，不是可机读状态。

B-M 的主体修法方向同样正确，但仍有两个可接受空产物/无清单产物的硬绕口：isolation 的正式 workspace 没有被要求绑定唯一 run，v1 grandfather 也没有禁止在旧 run 上创建新的 0_reading accepted attempt。另有 plan coverage 被错误地无条件与 elevation visibility 相交，正面冲突上位 source-aware 合同。

本审只读核对 HEAD，并在仓库环境的 Pydantic `2.13.3` 上做了无落盘探针；除本 verdict 外未改任何文件。

## 二、B2-01 严格子类族专项裁决

| 问题 | 裁决 |
|---|---|
| 子类 `extra="forbid"` 是否覆盖父类 `extra="allow"` | **是。** 对一个新的 `CorrectedGeometryV3/FloorV3/...` validation，子类 config 生效；未知字段被拒，实例的 `__pydantic_extra__` 为 `None`。不会把某个既存父类实例的 extras“继承进”新建子类。 |
| legacy 同名 extra 是否提前按 v3 类型爆炸 | **不会。** legacy 仍由原 `CorrectedGeometry/Floor/Window` 解析，新字段不在其 field table 中，继续进入 `__pydantic_extra__`；这闭合了 r1 的主要反例。现 legacy 全层 `extra="allow"` 见 `src/agent/correction/schema.py:32-40,43-52,62-83`。 |
| v1/v2 半 v3 字段是否成为 typed field | **不会，但仍可被属性访问。** 它不是 `model_fields` 中的 typed value，却仍可由 `getattr/hasattr` 读到；仓库已有显式读取 extra 的模式（`src/agent/correction/cell_geometry.py:23-27`）。因此 v3-only consumer/readiness 不得用“字段存在”判版本或填充态。 |
| 子类覆写字段是否继承父 validator | **是。** Pydantic v2 会把父类 `field_validator` 应用于子类同名覆写字段；探针确认 `Window.facade` 一类的 before-normalizer 可继续工作。若子类又以同一方法名定义 validator，则存在 Python/Pydantic 覆写风险，须用继承回归锁定。父 validator 现实见 `src/agent/correction/schema.py:54-59`。 |
| `schema_version: Literal["3"]` 不写 default 是否仍必填 | **是。** 子类重新注解会移除父类默认，缺字段即 ValidationError。 |
| `Field(frozen=True)` 是否等于跨事务 immutable identity | **否。** 它挡属性赋值，但 `model_copy(update={"id": ...})` 可产生另一个合法 id，末尾普通 revalidation 也抓不到“值变了”；见 R2-B2-03。 |
| 子类经基类类型外壳序列化是否保留子类字段 | **不保证，而且默认会丢。** `Holder.geom: CorrectedGeometry` 装入 v3 后，`Holder.model_dump()` 按基类字段表序列化，v3-only 字段被裁掉；见 R2-B2-02。 |

所以，严格子类族满足 r1 的**模型形态意图**，但 v2 当前尚未满足 r1 的**全边界意图**。可保留该变体，必须按下列 findings 补齐。

## 三、r1 B2 findings 关闭矩阵

| r1 finding | 状态 | r2 复核 |
|---|---|---|
| B2-01 strict v3 wire + legacy adapter | **PARTIAL** | 子类族在 raw wire 层成立，legacy bytes/hash 的结构性主张也成立；但 `parse_corrected_geometry(payload: dict)` 没覆盖已实例化的宽松基类，judge 的 `isinstance` 快路仍可绕过，基类类型的 Pydantic 外壳还会裁掉子类字段。见 R2-B2-01/02。 |
| B2-02 footprint 产权与单一事务 writer | **PARTIAL** | v3 缺 footprint 硬错、cells 兜底仅 legacy、七步 writer 与 ring/cells 同事务均已写入；但 wire 先要求 open+CCW，core 又承诺接收并 canonicalize CW/closed，两阶段合同互斥。见 R2-B2-04。 |
| B2-03 constrained types / identity | **PARTIAL** | fixed tuple、finite、interval/digest/条件约束及 post-core revalidation 大体补齐；但 component-wise normal 类型仍接受零向量/对角向量，`frozen=True` 也不证明事务前后 id 未变。见 R2-B2-03。 |
| B2-04 `Window.floor_id` + resolver | **CLOSED** | 不再跨版本改写 `Window.floor`；v3 新主键、并存一致性、重名负例及 scorer/elevation/render/validator/core 消费者均已点名（细稿 `:111-116`）。 |
| B2-05 v3 生产发射 | **PARTIAL** | 发射已从 B5 前移至 B2，prompt schema 分版、B2 空段/空 north-axis、真实 producer 重抽均采纳；但 target/profile 映射和 readiness 状态未成为单一合同，默认 profile 下真实 v3 验收会被 capability gate 拒绝。见 R2-B2-05/06。 |
| B2-06 双路径 typed debt resolution | **PARTIAL** | 两路径 pre-core、禁字符串命中、core audit 不洗债均已采；但被引用的 `debt_id` 不存在，audit 仍是 `list[dict]`，尚无真正 typed reference。见 R2-B2-07。 |
| B2-07 accepted-attempt audit identity | **CLOSED** | `FinalizeResult`、attempt 内 output/checks/audit 同归档、root 仅 accept 后 promote、report/baseline manifest-first 及 001→002 blocked 回归均正面闭合 r1 缺口（细稿 `:132-144`）。R2-B2-02 是子类序列化的新风险，不推翻该身份裁决。 |
| B2-08 legacy bytes/hash | **CLOSED** | legacy 类完全不加字段时，原 v1/v2 `model_dump_json` 字段表与默认键结构不变；不再需要为了新默认字段做 legacy exclude serializer。仍须保留细稿 `:166` 的 bytes/hash 回归，并确保 target 选择不把 legacy run 擅自切成 v3。 |

## 四、B2 r2 新 findings — **REWORK**

### R2-B2-01 — BLOCKER — raw-payload 分发器没有封住 typed-object 入口，宽松基类仍可冒充 v3

`parse_corrected_geometry` 只收 `dict`，且只在 finalize **末尾**往返重验（细稿 `AI_agent/proposals/c2_b2_detail_spec.md:62-70`）。然而 legacy 基类允许任意字符串 `schema_version` 和任意 extras（`src/agent/correction/schema.py:70-83`），所以代码可先构造 `CorrectedGeometry(schema_version="3", ...)`，再把它送入所有注解为基类的入口。

现实中 judge 明确对任何 `isinstance(geom_data, CorrectedGeometry)` 直接信任，只对 dict 解析（`src/agent/judge/correction_score.py:316-337`）；core、geometry checks 与 correction checks 也都接收宽松基类对象（`src/agent/correction/deterministic.py:725-730`、`src/agent/correction/geometry_validator.py:216-225`、`src/validator/checks/correction.py:85-111`）。这会让缺 `FloorV3.id/footprint/floor_id` 或带嵌套 extra 的“typed v3”在 score/check/core 前半段运行，末尾 revalidation 既覆盖不了 judge 直调，也只能在对象已被原地 mutate 后报错。

同名 legacy extra 虽不成为 typed field，却仍可被 `getattr` 取到；已有 helper 正在这样读 extras（`src/agent/correction/cell_geometry.py:23-27`）。若 readiness 或 v3 consumer 用 `hasattr(geom, "facade_segments")`，legacy payload 可用同名 extra 伪装 populated。

**建议修法**：增加唯一的 `ensure_corrected_geometry(value: dict | CorrectedGeometry) -> CorrectedGeometry`：raw 走版本分发；`schema_version==3` 的基类实例必须已经是 `CorrectedGeometryV3`，否则 strict round-trip 后返回新对象；未知版本一律拒绝。finalize 在任何 mutation **之前**先调用并操作返回的新对象，末尾再调用一次。build/check/score/render/load 等公开顶层入口同样调用；v3-only consumer 只能按版本+严格实例/feature-state 判定，禁 `hasattr/getattr` 判 readiness。补“宽松基类 schema=3 直送 judge/core/check”负例。

### R2-B2-02 — BLOCKER — 基类注解序列化会静默裁掉 v3 子类字段，`FinalizeResult` 形状未冻结

细稿只写 `FinalizeResult{geom, audit_payload}`，没有说明它是 dataclass、Pydantic model，或 `geom` 的序列化注解（`AI_agent/proposals/c2_b2_detail_spec.md:134-141`）。当前 attempt writer 对传入 Pydantic 对象直接调用其 `model_dump_json()`（`src/agent/execution/stage_runner.py:140-145,184-189`）。

本仓库 Pydantic `2.13.3` 探针结果：v3 实例直接 `model_dump()` 会保留子类字段；但把它放进 `geom: CorrectedGeometry` 的 Pydantic holder 后 dump，只剩基类字段，`FloorV3.id/footprint`、`WindowV3.floor_id`、`facade_segments/north_axis` 会被静默裁掉。这不是 validation error，而是一个 hash 合法、随后无法按 v3 重载的 accepted artifact。

**建议修法**：冻结 `FinalizeResult` 为非 Pydantic dataclass，并规定 attempt writer 永远直接序列化 `result.geom` 的运行时模型；或显式使用 `SerializeAsAny[CorrectedGeometry]`/`serialize_as_any=True`；更稳的是对 wire output 使用明确的 version-discriminated serializer。禁止把整个 `FinalizeResult` 交给通用 `_to_json` 猜。新增回归必须从真实 `FinalizeResult → StageRunner → attempts/NNN/output.json → parse_corrected_geometry` 往返，并逐键断言所有 v3-only 字段存在。

### R2-B2-03 — HIGH — “cardinal tuple”和“frozen identity”都只约束了表面语法

`tuple[Literal[-1,0,1], Literal[-1,0,1]]` 只限制每个分量，仍合法接受 `(0,0)`、`(1,1)`、`(-1,1)` 等五个非 cardinal 值；细稿却声称它“钉死 cardinal 单位法向”（`AI_agent/proposals/c2_b2_detail_spec.md:87-96`）。它也未把 `p1/p2` 的轴对齐、normal 与 segment 垂直、normal 与 `facade_family` 一致写成同一个 validator。`depth: FiniteFloat  # >=0` 若没有 `Field(ge=0)`/validator，也只是注释。

另一个独立漏洞是 `Floor.id = Field(frozen=True)`（细稿 `:45-48`）：探针确认属性赋值会被拦，但 `floor.model_copy(update={"id":"other"})` 成功，随后 strict revalidation 仍成功。细稿 `:70` 所称“末尾 revalidation 补偿 model_copy”抓不到一个类型合法但身份已变化的 id。

**建议修法**：保留 JSON 友好的二分量 tuple，再加 `abs(nx)+abs(ny)==1`；顶层 validator 同时验证轴对齐、法向/朝向族/along interval 的几何一致性，`depth` 用真实非负约束。finalize 开始时快照有序 floor ids 与所有引用，结束时要求 identity 集合及对应关系逐值不变；不要把 `frozen=True` 当成事务不变性证明。补上述 3 个坏 normal、斜 segment、反向 family 和 `model_copy` 改 id 负例。

### R2-B2-04 — HIGH — `FootprintRing` 的 strict wire 与 core canonicalization 是隐性二选一

细稿先把 `FootprintRing` 定义为必须“开环 CCW”（`AI_agent/proposals/c2_b2_detail_spec.md:73-76`），这意味着 strict parse 在进入 finalize 前就应拒绝 closed/CW；随后七步事务又要求 core canonicalize 绕向/闭环并保存 producer 前值（`:77-79`）。两者不能同时发生：若 Pydantic validator 真 enforce，core 永远看不到非 canonical raw；若不 enforce，“v3 strict ring”又不是所写的 wire 合同。

当前 cell 路径刻意允许 core 看见 CW/closed 后改写并记 audit（`src/agent/correction/cell_geometry.py:116-138`、`src/agent/correction/deterministic.py:755-772`），不能不说明阶段就机械复用。

**建议修法**：明确二选一。最小方案是 v3 draw wire 只接受 open+CCW，删除 footprint 的 core 编码 canonicalization，只保留 validate/snap；若必须兼容 LLM 的 CW/closed，则定义 parse 前 normalization adapter，返回 `{strict_geom, normalization_audit}` 并保留 raw 值，再由 final contract 只接受 open+CCW。测试分别锁 raw draw、pre-core object、final artifact 三个阶段，不能用同一 `FootprintRing.model_validate` 同时扮演宽进和严出。

### R2-B2-05 — HIGH — v3 target 与 capability profile 没有单一选择点，默认 sm21 发射会自拒

细稿把 v3 声明形状定为 `{RECTANGULAR, ORTHOGONAL_POLYGON}`（`AI_agent/proposals/c2_b2_detail_spec.md:35-36`），这沿用当前“schema 声明形状集合必须是 profile 允许集合的子集”规则（`src/agent/geometry/capability.py:21-31,51-75`）。默认 `RunPolicy.capability_profile` 却是 `rectangular`（`src/agent/execution/policy.py:37-44`）。因此即使 sm21 实际全是矩形，只要产物版本为 v3，默认 profile 也会因 v3 声明含 polygon 而拒绝；细稿 `:154-156` 的“真实 accepted v3”没有指定如何跨过此门。

目标版本也没有成为一条参数链：当前 `_build_correction_messages` 不接 capability/target（`src/agent/pipeline.py:289-302`），`run_correction` 虽接 capability，却在建 prompt 时没有传入（`:541-582`），两个 inner validator 和最终 parse 又各自直接调用 legacy 类（`:510-535,583-604`）。只改 schema 嵌入点会留下“prompt 选 v3、validator 仍 legacy”或反向混搭。

**建议修法**：冻结一个无默认歧义的 `CorrectionTarget`，至少包含 `schema_version/schema_model/capability_profile/phase_contract`，由 run policy 一次选定并贯穿 prompt、inner validator、最终 parse、finalize、gate、writer。按上位/base 现语义，`orthogonal_polygon → v3`；`rectangular` legacy run 保持原目标版本。若主控要让 `rectangular → v3`，必须先修改“版本声明全集”这条上位 capability 语义，不能在 B2 暗改。sm21 真实重抽必须在验收条款中写明 target/profile，并先验证运行配置与 accepted manifest 都记录同一选择。

### R2-B2-06 — HIGH — `declared` 与 `populated` 没有载体，空列表同时表示“未施工”和“施工后零结果”

细稿静态 feature 轴只定义 `supports(geom, feature)`（`AI_agent/proposals/c2_b2_detail_spec.md:35-36`），却又要求 B2 accepted v3 的 `facade_segments=[]/north_axis=None`，并称以后由 Vg “翻转 populated”（`:152-156`）。没有字段、sidecar、attempt metadata 或 helper version 承载这个翻转。仅从 schema version 可知 declared；仅从空列表无法区分“Vg 尚未运行”“Vg 运行后合法零结果”“Vg 漏产”。更不能靠字段存在，因为 legacy extra 也可伪装同名字段。

这还隐藏一个 owner 问题：上位要求 `facade_segments` 随 accepted correction output、单一 writer 为 correction deterministic core（`AI_agent/proposals/c2_full_unlock_design.md:51-54,84-91`）；Vg 后续不得原地修改已经 accepted 的 B2 artifact。

**建议修法**：拆成两个明确 API：`schema_supports(feature)` 只看 wire 版本；`artifact_feature_state(attempt, feature)` 返回 `not_declared | declared_unpopulated | populated`，状态绑定 correction stage/helper version/output hash。冻结 Vg 上线后的 ownership：要么 Vg helper 被接入一次新的 correction finalize 并形成新 attempt，要么先产 attempt-bound sidecar，绝不能回写旧 accepted output。每个 B3/Vg/Va/B4/B5 consumer 写明需要 support 还是 populated；缺所需状态恒 BLOCK。补“legacy 同名 extra”“v3 空但未跑 Vg”“Vg 已声明完成却空/缺 sidecar”“篡改旧 accepted output”负例。

### R2-B2-07 — HIGH — `resolves_debt_id` 引用了不存在的主键，`list[dict]` 也不是 typed audit

细稿要求 audit entry 增 `resolves_debt_id` 并只认 typed 条目（`AI_agent/proposals/c2_b2_detail_spec.md:146-150`），但现实 `EvidenceDebtItem` 只有 check/view/scope/offender 等字段，没有 `debt_id`（`src/agent/execution/evidence_preflight.py:30-53`）。同一 check 可在多 view、多 offender、多次报告中出现，不能把 `check_id` 偷当唯一 debt id。

同时 `CorrectedGeometry.corrections/conflicts/unsupported` 仍是 `list[dict]`（`src/agent/correction/schema.py:79-82`）；只往任意 dict 加一个同名 key，不会得到类型化来源，也挡不住产品伪造引用。现字符串扫描实现位于 `src/validator/checks/correction.py:534-579`，修掉扫描不等于引用身份已成立。

**建议修法**：evidence-debt schema bump，给每项确定性 `debt_id`（至少绑定 source report/artifact hash、canonical check id、view、scope、排序后的 offender ids）；correction attempt 的 input hashes 绑定该 debt artifact。定义 strict `DebtResolutionAuditEntry`（带 kind、`resolves_debt_id`、rationale/source），或对 audit union 做等价 strict validation；checker 只接受指向本 attempt 输入 debt 集的引用，重复/不存在/跨 run id 均 BLOCK。core audit 使用不同 kind，类型上不拥有该字段。

## 五、r1 B-M findings 关闭矩阵

| r1 finding | 状态 | r2 复核 |
|---|---|---|
| BM-01 trusted completeness / negative evidence | **PARTIAL** | 静态 potentially-observable 与 case completeness 已拆，负证据默认空，coverage/assertion 已类型化；但消费公式无条件 `coverage ∩ Vg visible`，错误套到 plan。见 R2-BM-01。 |
| BM-02 isolation bypass | **PARTIAL** | ensure 前置、merge 共用 checker、blocking 不得强 accept、partial 不接受、五负例均已写；但当前 optional `run_dir` 与独立 merge target 未被裁掉，仍可构建无 run 身份的 workspace 再并入任意 run。见 R2-BM-02。 |
| BM-03 direction axes | **PARTIAL** | raw token / semantics / resolved building direction 已拆；但正文新增的 `direction_source` 不在 strict entry schema，true-azimuth 的 resolved 产物身份也没冻结。见 R2-BM-03。 |
| BM-04 staged image full classification | **CLOSED** | `required_view|excluded_input`、supp/site/detail typed entry、`expected_output_id` 和只读 inventory projection 已正面采纳 r1 裁决（细稿 `:23-26,45-75,92-97`）。R2-BM-05 是“已分类但仍可无输出消费”的新旁路。 |
| BM-05 emitter / validate / RunManifest evolution | **PARTIAL** | provisioning 唯一 emitter、validate 只读、manifest v2 槽与 v1 grandfather 均已写；但 v1/v2 wire/serializer 和“旧 run 是否可新增 attempt”未冻结，judge 的 `ensure` 也仍有 emit/verify 双义。见 R2-BM-04。 |
| BM-06 profile disposition | **CLOSED** | check 明确定为 INVARIANT，所有 profile 恒 BLOCK，pilot 只能未 accepted（细稿 `:109-115`）。 |
| BM-07 strict metadata loader | **CLOSED** | 缺失/坏 JSON、根逃逸/symlink、repo-relative 归一化、冲突与原子写均已 fail closed（细稿 `:92-97`）。 |
| BM-08 strict schema/version chain | **PARTIAL** | 顶层版本链、metadata/content hash、全 submodel forbid 与条件约束方向已补；但 schema 自称按 `view_id` 排序却没有该字段，正文 `direction_source` 也不在模型，尚不能称 wire 已冻结。见 R2-BM-03/06。 |

## 六、B-M r2 新 findings — **REWORK**

### R2-BM-01 — HIGH — `trusted coverage ∩ Vg visible` 不能无条件套到 plan 通道

细稿把 plan coverage 与 elevation coverage 放入同一 union（`AI_agent/proposals/c2_bm_view_manifest_spec.md:81-87`），随后无条件规定负证据取 `trusted coverage ∩ Vg visible intervals`（`:89-90`）。plan 没有某一立面视向的 Vg visibility；凹形建筑中，平面可看到并证明 hidden facade 上的 opening，不能因某张 elevation 的遮挡区间把 plan 证据抹掉。

上位已明确分支：plan 来源在**全部外边界段**解析，hidden 不阻止挂段；只有 elevation 来源限于该视图 visible 段（`AI_agent/proposals/c2_full_unlock_design.md:28-34`）。证据矩阵也明确 plan 可立 existence/host/along/width，elevation 才带“该段 visible”条件（`:41-48`）。细稿当前公式会把可信完整 plan 的 absence/positive evidence 错降为 NA，和上位冲突，按上位裁。

**建议修法**：冻结 source-specific Va 公式：plan claim 用 trusted `plan_floor_region` 与 footprint/host boundary 的空间覆盖，不与 elevation Vg 相交；elevation claim 才用 trusted `elevation_local_along` 与该 view 的 Vg visible intervals 相交。跨通道 conflict 在双方各自 coverage 后再比较。补凹形 hidden segment 的四例：plan positive 保留、plan trusted absence 可作负证据、elevation absence 为 NA、elevation positive 仅 visible claim 生效。

### R2-BM-02 — BLOCKER — isolation workspace 可无 run 构建，merge target 又独立传入，ensure 身份仍可绕

细稿只说 `build_isolation_workspace` 前置 ensure（`AI_agent/proposals/c2_bm_view_manifest_spec.md:99-106`），没有裁掉现实 API 的 `run_dir: Path | None = None`（`src/agent/execution/isolation.py:91-120`）。现测试和 helper 正常走无 run 构建（`tests/test_isolation.py:23-24,286-302`）。之后 `merge_isolated_output(staging_root, run_dir)` 再独立接受任意目标 run（`src/agent/execution/isolation.py:150-166`）；现 provenance 只记 staging/settings/guard/access-log hashes，甚至不记 builder 的 run identity（`:451-475`）。

因此“build 前 ensure”若只在 `run_dir is not None` 时执行，调用者仍可构建无 view-manifest 身份的 workspace，再把产物 merge 到一个正式 run。即使 merge 重算目标 manifest，staging 内图片/inventory 与目标 run 是否同一生成快照也无不可替换绑定。

**建议修法**：正式、可 merge 的 builder 强制 `run_dir`，并在 staging immutable provenance 中绑定 canonical run id/case id、view-manifest hash、metadata hash及每张 image hash；merge 必须验证目标 run 与 builder 身份完全相同。若保留 `run_dir=None`，命名为 preview/unbound 模式，产物带不可移除的 `merge_eligible=false`，merge 恒拒。负例增加“无 run build 后 merge”“为 run A build 后 merge 到 run B”“build 后 target manifest 被替换”。

### R2-BM-03 — HIGH — 方向 provenance 字段漏出 strict schema，true-azimuth resolved 产物也无不可变 owner

ManifestEntry 样例有 `declared_direction_token`、`direction_semantics`、`semantics_source`、`azimuth_deg`、`building_view_direction`（`AI_agent/proposals/c2_bm_view_manifest_spec.md:45-64`），却没有 §3.1 所称 `direction_source`（`:78-79`）。`semantics_source` 表示“为何认定 building_axis/true_azimuth”，不能替代“raw token 来自 metadata、title hint、matcher 还是 user”。全 submodel 又是 `extra="forbid"`（`:43`），执行时无法临时补字段。

这也不满足上位 manifest 必带 direction 来源的要求（`AI_agent/proposals/c2_full_unlock_design.md:51-52`），且其允许来源还包括 `standard_assumption/title_hint/matcher/user`，与细稿正文的 `user|title_hint`、样例的 `standard_assumption|case_metadata|user` 三套枚举互不相同。

此外 true-azimuth 的 `building_view_direction` 在 trusted manifest 中必须保持 null，但细稿只说 E4 adapter 以后“产 resolved 方向”，没冻结产物位置/identity。若 adapter 回写 manifest，会破坏 `content_sha256` 和“唯一 emitter”；若只存在内存，Va/Vg/replay 无法证明它绑定哪一份 accepted θ。

**建议修法**：把 `direction_source` 与 `semantics_source` 都纳入 strict schema，并统一唯一枚举/生成规则。冻结独立 `ResolvedViewDirection` sidecar：绑定 view-manifest hash、accepted orientation output hash/θ schema、input_id、resolved building direction/vector、adapter version；E4 adapter 唯一写，manifest 永不改。Vg/Va 只收该 sidecar 的 resolved vector；缺失、hash 漂移或不可唯一映射 fail closed。

### R2-BM-04 — BLOCKER — RunManifest grandfather 没有限制“只读旧 run”，可成为新增 accepted reading 的永久豁免

细稿规定 `manifest_version=1/无字段` 一律 grandfather、消费端 `NOT_APPLICABLE`（`AI_agent/proposals/c2_bm_view_manifest_spec.md:99-107`），但没有区分只读 replay/validation 与在旧 run 上新增、resample、isolation merge 0_reading。按当前文字，旧 run 可永远绕过 view-manifest coverage，再创建一个新的 accepted attempt；这直接废掉 C-03 硬门。

wire evolution 也未真正冻结。当前只有一棵 `RunManifest`，`manifest_version: str = "1"`，load/save 直接用当前类全量 parse/dump（`src/agent/execution/manifest.py:114-135`）；isolation 的第二 writer 也直接 `model_dump_json`（`src/agent/execution/isolation.py:514-520`）。若在同一类上加 required `run_inputs`，v1 load 失败；若加 optional/default，v1 save 会被新键污染。单写“bump 2 + v1 compatible read”没有消除这个二选一。

**建议修法**：冻结 `RunManifestV1` 与 `RunManifestV2` 两份 wire model及版本分发/serializer；v1 load/save 保持原 bytes/字段，不自动补键。grandfather 仅允许只读 validation/replay/report，且 coverage 明示 N/A；任何会创建或接受新 0_reading attempt 的命令，必须先走显式、原子 migration 到 v2 并生成/绑定 trusted manifest，否则 BLOCK。普通 save 与 isolation atomic save 共用同一 versioned serializer。补“v1 只读不写”“v1 resample 拒绝”“显式 migrate 后可重抽”“v1 load-save bytes 不变”四例。

同时把 API 分成 `provision_view_manifest`（唯一 emitter）与 `verify_view_manifest`（绝不写），或给 mandatory mode enum 且无默认。细稿一边称 preflight 是唯一 emitter，一边让 judge 调同一个 `ensure_view_manifest` 并口头要求“只验不产”（`:92-107`），仍是隐藏双义。

### R2-BM-05 — HIGH — “已分类但无需产物”的图片仍对 reader 可见，重开 audit-only 证据旁路

细稿允许 `required_view.reader_output_required` 由 entry 决定（`AI_agent/proposals/c2_bm_view_manifest_spec.md:63-70`），gate 只要求其中为 true 的产物（`:109-115`）。与此同时现实 isolation 会复制所有 PNG，并告诉 reader 读取整个 `case_data`（`src/agent/execution/isolation.py:252-260,308-322`）。若 supp/site/detail 被标成 required_view 但 `reader_output_required=false`，或 excluded_input 仍留在可读目录，reader 可使用其几何事实，却无需为该 source 产 ReadingView，也不进入 missing denominator。它只是把 r1 的 `undeclared_images audit-only` 改名成了“classified but unaccounted”。

`derived_working_copy` 在证明与 parent 内容等价时可以例外；普通 detail/site plan 或 `non_drawing_asset` 不能仅靠标签阻止模型读取。

**建议修法**：所有对 reader 可见且可能承载 drawing claims 的输入必须是 `required_view + reader_output_required=true`。不要求产物的文件应从 reader 可见 staging 移除；若因工具需要保留，guard/目录能力必须使 reader 不可读。derived copy 仅在绑定 parent 且有版本化等价规则（最好 pixel/content relation）时可见；其 claim provenance 归 parent。加“supp plan 可见但 output_required=false”“excluded detail 被 reader 引用”“derived copy hash/parent 不符”负例。

### R2-BM-06 — MEDIUM — strict entry 的主身份仍有 `view_id`/`input_id` 两套名字

顶层 schema 注释称 `entries` 按 `view_id` 排序（`AI_agent/proposals/c2_bm_view_manifest_spec.md:30-40`），ManifestEntry 却没有 `view_id`，只有 `input_id`（`:45-51`）；gate 又按 `expected_output_id` 对账（`:101-106`）。若 `input_id` 就是 manifest entry identity，应删除全部 `view_id` 术语并规定它与 source path/stem 的关系；若二者不同，当前 strict model 漏字段。后续 opening provenance 的 `source-view ids` 到底引用哪个 id 也会出现两种合法解释。

**建议修法**：选一个稳定、非文件名推断的 manifest entry id（可直接把 `input_id` 定为它），写死唯一性、canonical sort、所有 provenance foreign key；`source_image` 与 `expected_output_id` 只是它的属性。补 duplicate id、同 stem 不同路径、expected output collision 与 provenance dangling-ref 负例。

## 七、四个开放问题的 r2 明确裁决

| r1 开放问题 | r2 裁决 |
|---|---|
| B2 evidence-debt BLOCK 是否进 finalize / 是否允许两路径差异 | **维持 r1：不进纯 finalize，但必须在 B2 内由两路径共用的 pre-core check 闭合。** pipeline 可 fail-fast；flow 记 blocked attempt。只有绑定本 attempt 输入 debt artifact 的 strict `resolves_debt_id` 可清偿，core audit 永不清偿。 |
| `Window.floor` 是否在 v3 改成 id | **维持 r1：不改义。** v3 新增必填 `floor_id`；legacy/display `floor` 保持 name，二者并存必须一致，所有 consumer 经 resolver。此问题已 CLOSED。 |
| manifest coverage 在 exploratory 是否降级 | **维持 r1：所有 profile 恒 BLOCK。** missing/extra/identity/hash/manifest mismatch 都是 input identity INVARIANT；pilot 只能是未 accepted partial workflow。此问题已 CLOSED。 |
| `undeclared_images` audit-only 还是 raise | **维持 r1：未知图片生成期 fail closed；每张 staged image 必须 required/excluded 全分类。** 但“excluded/无需 output”不能继续对 reader 可见并承载未记账证据，须同时满足 R2-BM-05。 |

## 八、重新送审门

### B2

1. 保留严格子类族，但落唯一 typed/raw coercion boundary；pre/post finalize、judge/check/build/load 全覆盖，legacy 同名 extra 不得驱动 v3 feature。
2. 冻结 v3 runtime serializer 与 `FinalizeResult → attempt output → strict reload` 回归，证明子类字段不被基类注解裁剪。
3. 修 cardinal/segment 几何约束、transaction identity snapshot 与 FootprintRing 宽进/严出阶段合同。
4. 以单一 `CorrectionTarget` 贯穿 prompt/validator/parse/finalize/gate/writer，明确 sm21 v3 重抽的 profile；按现上位语义不得让 default rectangular 暗接 v3。
5. 给 feature population 可机读、attempt-bound 状态及唯一 owner；Vg 不得改写旧 accepted artifact。
6. debt schema 有稳定主键，audit resolution 为 strict 类型并绑定输入 debt hash。

### B-M

1. Va coverage 按 plan/elevation 分支，禁止把 plan 证据无条件裁进 Vg-visible。
2. 正式 isolation build 必须绑定唯一 run/view-manifest，unbound preview 永不可 merge。
3. direction source 进 strict schema；true-azimuth resolved direction 用绑定 manifest+orientation hash 的独立 sidecar。
4. RunManifest v1/v2 分 wire/serializer；grandfather 只读，任何新 0_reading attempt 先显式 migrate。
5. reader 可见 drawing 必须有 required output；excluded/optional 输入不得成为不记账证据面。
6. 统一 manifest entry identity 名称与所有 foreign key。

## Review ask

none — 两处实现形态均已明确裁决：严格子类族**可保留但当前未闭边界**；v3 随 B2 发射的批次选择**正确但当前发射面未闭合**。完成上述门后再送 r3。
