# C2 B2 + B-M 细稿 r4 对抗复审

Date: 2026-07-10  
HEAD: `7422f42`  
Objects: `AI_agent/proposals/c2_b2_detail_spec.md`、`AI_agent/proposals/c2_bm_view_manifest_spec.md`（v4，累计式全文）  
Governing design: `AI_agent/proposals/c2_full_unlock_design.md` v2.2；baseline: `AI_agent/proposals/c2_orthogonal_polygon_design.md` D1–D10  
B2 verdict: **REWORK**  
B-M verdict: **REWORK**

## 一、总裁决

r3 的 7 条修法均已实质落地，两个最大架构缺口已经关闭：当前两稿不再依赖已覆盖的旧正文；V3 重验、v1/v3 target、attempt-bound feature hash、finite 数值、immutable run id 也都按裁决改正。

但两稿共同冻结的 RunManifestV2/StageRecord wire **尚未真正一致且不可直接实现**：两处都写“扩现 `StageRecord`”，却没有 `StageRecordV1/StageRecordV2` 分立。直接给现类加 `artifact_hashes` 会使号称原封的 RunManifestV1 嵌套 wire 改键或加载失败；若另建 V2 record，现稿又没有 stages 类型、迁移 backfill、分 stage 必填键和批次 owner。更隐蔽的是，B-M 的 RunManifestV2 强制 `run_inputs.view_manifest_sha256`，所以 B2 不能按“先合者建”独立先落，否则它没有 B-M manifest 可填。此为两稿共同 BLOCKER。

关闭统计：

- B2：r3 5 条为 **4 CLOSED / 1 PARTIAL / 0 NOT-CLOSED**。新增 **3 findings（1 BLOCKER / 1 HIGH / 1 LOW）**。
- B-M：r3 2 条为 **2 CLOSED / 0 PARTIAL / 0 NOT-CLOSED**。新增 **2 findings（1 BLOCKER / 1 HIGH）**；共同 BLOCKER 与 B2 为同一 wire 缺口，只计一次根因。

自包含测试结论：两稿均已通过“无消失版本引用”的章节级测试；新执行者能从当前文件列出主体 geometry/manifest wire、writer、consumer 与验收表。精确 wire 测试仍暴露两个局部缺型：B2 的 `feature_states_payload` 仍是裸 dict，B-M 的 `CompletenessAssertion` 仍只有 JSONC 省略号。它们分别列为 HIGH。

本审只读核对 HEAD，并以 Pydantic `2.13.3` 复核 FiniteFloat 组合（`AllowInfNan(False)` + `Field(ge=0)` 对 `inf/-inf/nan` 均拒绝）。除本 verdict 外未改任何文件。

## 二、r3 B2 findings 关闭矩阵

| r3 finding | 状态 | r4 复核 |
|---|---|---|
| R3-B2-01 累计式自包含全文 | **CLOSED** | 当前 325 行稿完整恢复 v3 子类/子模型、七步事务、helper 路由、writer、测试与验收；除版本史外无“vN 不变/基础上修”规范引用（`AI_agent/proposals/c2_b2_detail_spec.md:46-325`）。 |
| R3-B2-02 V3 no-op / draw-final 两把尺 | **CLOSED** | schema 3 模型实例一律 strict round-trip 返回新对象，无 no-op；`parse_correction_draw` 与 `validate_final_corrected_geometry` 分立，finalize 顺序与 model_copy/final-CW 负例均冻结（细稿 `:144-178`）。 |
| R3-B2-03 rectangular→v1 target | **CLOSED** | target 已改为 rectangular→v1、orthogonal→v3、v2 只读 legacy；prompt/validator/parse/manifest 同 target及默认 v1 bytes 回归均写明（细稿 `:212-228`）。 |
| R3-B2-04 feature-state attempt identity | **PARTIAL** | FinalizeResult 已携 payload、finalize 零 I/O、writer 整体原子落位、manifest hash sidecar、下游逐 hash 均已采；但共享 StageRecord 没有 V1/V2 分型，artifact key 合同与 migration 不成立，feature payload 本身仍为可变裸 dict。见 R4-X-01、R4-B2-01。 |
| R3-B2-05 finite depth/uncertainty | **CLOSED** | 两字段均为 `Annotated[FiniteFloat, Field(ge=0)]`，并有 `inf/-inf/nan` 负例（细稿 `:68-70,94-116,307`）；本轮运行时探针确认三种非有限值全拒。 |

## 三、B2 历史遗留 PARTIAL 复核

| 历史 finding | r3 状态 | r4 状态 | 说明 |
|---|---|---|---|
| R2-B2-01 typed/raw coercion | PARTIAL | **CLOSED** | schema 3 无实例快路，所有信任边界吃 fresh strict 对象。 |
| R2-B2-03 cardinal/identity | PARTIAL | **CLOSED** | cardinal/段几何/身份快照与 finite 数值全部闭合。 |
| R2-B2-04 ring 宽进严出 | PARTIAL | **CLOSED** | 两个命名 API、唯一 canonicalization owner、final canonical validator已具备。 |
| R2-B2-05 CorrectionTarget | PARTIAL | **CLOSED** | 生产矩阵已与 base D1/capability subset 门一致。 |
| R2-B2-06 feature-state | PARTIAL | **PARTIAL** | 状态三态、owner、attempt hash已落；strict payload wire 与共享 StageRecord 仍漏。 |
| r1 B2-01/B2-03/B2-05 | PARTIAL | **CLOSED** | strict 边界、精确类型、生产发射矩阵均已闭；r1 其余遗留项此前已 CLOSED。 |

## 四、共同新 finding

### R4-X-01 — BLOCKER — RunManifestV2/StageRecord “两处一致”只是一致写了同一个未闭合类型

B2 定义 `StageRecord.artifact_hashes: dict[str, Hex64]`，并称 correction 至少需要 output/checks/audit/feature_states 四键（`AI_agent/proposals/c2_b2_detail_spec.md:259-280`）；B-M 定义 RunManifestV1 为现类原封，同时让 RunManifestV2 增 `run_id/run_inputs` 和同一个 `StageRecord.artifact_hashes`（`AI_agent/proposals/c2_bm_view_manifest_spec.md:139-147`）。现实只有一棵共享 `StageRecord`，且现 RunManifestV1 的 `stages` 就嵌它（`src/agent/execution/manifest.py:99-135`）。

这里至少有四个未裁的二选一：

1. **V1 污染**：修改现 `StageRecord`，required 字段会让旧 manifest load 失败；optional/default 字段会让 v1 save 多键，违反两稿的 V1 bytes 不变。必须分 `StageRecordV1`/`StageRecordV2`，不能只分顶层 RunManifest。
2. **键合同不成立**：`dict[str, Hex64]` 只约束 value，既不要求 output/checks，也不拒未知/拼错 key；“typed artifact_hashes”名不副实。B2 的四键只适用于新 correction attempt，0_reading、modelling、Mep 与迁移来的 legacy correction 没有 audit/feature_states，不能全局要求四键。
3. **migration 缺 backfill**：B-M 的 v1→v2 migration 只写“生成 run_id + provision manifest”（`AI_agent/proposals/c2_bm_view_manifest_spec.md:143-147`），没有把现有 `dict[str, StageRecordV1]` 转为 V2 record、扫描 accepted attempt、计算已有 artifact hash，也没有规定缺失 legacy sidecar 是合法缺省还是迁移失败。
4. **“先合者建”有隐藏依赖**：RunManifestV2 的 `run_inputs.view_manifest_sha256` 必填（B-M `:144`），B2 若先合并既没有 `view_manifest.json` 也无权施工 B-M provisioning；若继续写 V1 又无法合法记录 V2 artifact hashes。上位批表仍把 B2 与 B-M 设为独立批（`AI_agent/proposals/c2_full_unlock_design.md:112-119`），所以“先合者建”并未给出可执行顺序。

此外必须冻结冗余不变量：`StageRecordV2.output_hash == artifact_hashes["output"]`；否则两条 accepted identity 可互相矛盾。

**建议修法**：

- 精确定义 `StageRecordV1`（当前字段逐字不动）与 `StageRecordV2`（显式 record schema version + artifact hashes），并令 `RunManifestV1.stages: dict[str, StageRecordV1]`、`RunManifestV2.stages: dict[str, StageRecordV2]`。
- artifact key 使用受控 enum/strict submodel；所有新 attempt 至少 output/checks，新 B2 correction stage_version 再要求 audit/feature_states，isolated 0_reading 按其 bundle 要求 provenance 等键，legacy migrated record只登记真实存在且迁移合同允许的集合。未知键、缺本 stage/version 必填键、output 双 hash 不同均拒。
- 写出显式 migration：逐 accepted pointer 验文件、重算可用 hashes、转换 record；绝不伪造不存在 sidecar。若某 legacy stage 不能安全转换，migration 原子失败并保持 V1。
- 批次必须二选一并写回依赖表：**B-M 先落共同 RunManifestV2，再由 B2 消费**；或先拆一个两稿共同依赖的 manifest-evolution 小批。删除“先合者建”。B2 不得被迫越界生成 view manifest。
- 两稿引用同一个规范 owner（建议 `src/agent/execution/manifest.py` 对应的独立 wire 小节/共享设计），不要复制两段可能漂移的 prose。

在此修复前，B2 的 attempt bundle 与 B-M 的 isolation/run migration 都不能施工，故两稿均 REWORK。

## 五、B2 其他新 findings

### R4-B2-01 — HIGH — `feature_states_payload: dict` 不是冻结的 readiness wire，且 frozen dataclass 不冻结其内容

FinalizeResult 把 feature state 声明为普通 `dict`（`AI_agent/proposals/c2_b2_detail_spec.md:261-273`）；§6bis 只给一个状态示例和三个字符串值（`:284-292`），没有 exact schema version 字段、受控 feature key 集、target/phase/helper 结构或 extra-forbid validator。`@dataclass(frozen=True)` 只禁止重新赋值，不禁止调用方在 finalize 与 writer 之间执行 `result.feature_states_payload["facade_segments"]="populated"`；writer随后会诚实 hash 这份被改过的 sidecar，hash 身份成立但 readiness 事实已被伪造。

sidecar 又需要 output hash，而 finalize 在 output serialization 前无法知道它；当前“payload 由 finalize 派生、writer 再写含 output hash sidecar”实际上是两个形状，尚未命名。

**建议修法**：分为严格、不可混淆的两型：finalize 返回 immutable `FeatureStateClaimsV1`（受控完整 feature 集、state enum、target schema/phase、helper versions，extra forbid；用 tuple/frozen records而非可变 dict），writer在序列化 output 后构造 `FeatureStatesArtifactV1{schema_version, output_sha256, claims}`。writer应从 target+final geom重新派生或至少重算并比较 claims，不盲信可变调用方数据。consumer 先验 artifact schema + StageRecordV2 hash + output_sha256，再读 state。补“FinalizeResult 返回后篡改 claims”“未知 feature/key/state”“缺完整 feature 集”负例。

### R4-B2-02 — LOW — “十路路由”与累计测试的“九路贯穿点”计数仍不一致

范围承诺十路（`AI_agent/proposals/c2_b2_detail_spec.md:11-21`），路由表以一行合并两个 render consumer（`:243-257`），测试又写“九路贯穿点”（`:302-315`）。当前表实际点名了两份 render 脚本，未发现确定遗漏；问题是数字口径会让执行简报无法判断应断言 9 个语义路由、10 个文件还是 11 个调用点。

**建议修法**：删除模糊计数，给每个 consumer 一个稳定 route id；两个 render 脚本分行或在测试中分别断言。验收按 route id 集合相等，不按词法命中数。

## 六、r3 B-M findings 关闭矩阵与历史遗留

| finding | r3 状态 | r4 状态 | 说明 |
|---|---|---|---|
| R3-BM-01 累计式自包含全文 | REWORK/BLOCKER | **CLOSED** | 当前 188 行稿恢复顶层、entry union、coverage、generator、RunManifest/isolation、gate、消费者接缝、测试与验收；不再依赖消失 v2（`AI_agent/proposals/c2_bm_view_manifest_spec.md:30-188`）。 |
| R3-BM-02 immutable run id | HIGH | **CLOSED** | RunManifestV2 已有必填 Hex32 random run_id，provision/migration owner、builder/merge/StageRecord 绑定、不比较整份 manifest及同输入 A→B 负例均明确（细稿 `:139-154`）。 |
| R2-BM-02 isolation binding | PARTIAL | **CLOSED** | stable run identity、formal/preview、merge target 与负例全闭。 |
| r1 BM-02 isolation bypass | PARTIAL | **CLOSED** | 同上。 |
| r1 BM-08 strict schema/version chain | PARTIAL | **PARTIAL** | 主 top-level/entry/version/identity 已恢复；CompletenessAssertion 仍非完整 strict submodel，见 R4-BM-01。 |

其余 r1/r2 B-M findings 均维持 CLOSED；未发现 direction、source-aware Va、reader 可见性、恒 BLOCK、strict loader 或 provision/verify 被重开。

## 七、B-M 其他新 finding

### R4-BM-01 — HIGH — `CompletenessAssertion` 仍是省略号对象，C-03 最关键的 trusted negative-evidence wire 未真正冻结

ManifestEntry 将 `completeness_assertion` 写成 `{source: "case_metadata|user|dataset_ref", assertion_id, ref} 或 null`（`AI_agent/proposals/c2_bm_view_manifest_spec.md:85-98`），但全文没有 `CompletenessAssertion`/source-ref 子模型；`ref` 的类型和各 source 必填字段未知。coverage 也只写字符串 `source_ref` 与 `completeness_assertion_id`（`:100-106`），没有强制：

- coverage id 必须等于同 entry assertion id；
- plan frame 只能配 full_floor、elevation frame 只能配 full_facade；
- negative claims 必须是 potentially observable claims 的子集；
- negative claims 为空时 coverage/assertion 是否必须同时为空；非空时二者必须同时存在；
- dataset_ref 必须绑定 dataset/contract version 与 content hash，而不是任意字符串 `ref`。

§4.2 虽再次说三种受信来源开启并要求 coverage/assertion（`:123-132`），仍未消除这些 wire 形态选择。这里是 denominator 的信任根，不应留给施工者临场设计。

**建议修法**：冻结 strict discriminated `CompletenessSourceRef`：case-metadata JSON pointer + metadata hash、user assertion id + signed/hashed content reference、dataset id/version/contract id/content_sha256；再定义 `CompletenessAssertion{assertion_id, source_ref}`。OpeningEvidence 顶层 validator一次执行上述 iff/subset/id/frame-region 约束。给三 source 各一正例，并补 dangling assertion id、错误 frame/region、negative 非 observable、空/非空联动、dataset 原地换内容五类负例。

## 八、两稿共同冻结件最终对账

| 字段/语义 | B2 §5 | B-M §5.1 | 裁决 |
|---|---|---|---|
| RunManifestV2.manifest_version | 仅引用 B-M bump | `Literal["2"]` | 字面不冲突，但 B2 非自载定义。 |
| RunManifestV2.run_id | 未在 §5 重述 | Hex32 immutable random | 字面不冲突；owner 在 B-M。 |
| run_inputs.view_manifest_sha256 | 未在 §5 重述 | required Hex64 | **形成 B-M→B2 的实现依赖，不能“先合者建”。** |
| StageRecord artifact_hashes | `dict[str,Hex64]`，correction 至少四键 | 同类型并括注同四键 | 字面一致，**版本/分 stage 语义不成立**，见 R4-X-01。 |
| output_hash 冗余关系 | 未写 | 未写 | 必须冻结相等 invariant。 |
| V1 nested StageRecord | 未分型 | 声称 RunManifestV1 原封但未分型 | **正面冲突。** |
| v1→v2 stage-record migration | 不涉及 | 只生成 run_id/provision manifest | **缺失。** |

结论：两处并非“真一致”；它们对字段名字大体一致，但没有共同、版本安全、stage-aware 的 wire。

## 九、重新送审门

### 共同门

1. 冻结 `StageRecordV1/V2 + RunManifestV1/V2` 完整类型、stage/version-specific artifact key 规则、output 双 hash invariant和 migration backfill。
2. 明确共同 wire 的唯一 owner与落批顺序；推荐 B-M（或独立 manifest-evolution 小批）先于 B2，删除“先合者建”。

### B2

1. 将 feature claims/sidecar 两阶段改成 strict immutable models，writer重派生/核对后再 hash。
2. 统一 helper route ids，分别覆盖两 renderer。

### B-M

1. 冻结 CompletenessAssertion/source-ref discriminated wire及 OpeningEvidence 全部联动 validator。

## Review ask

none — 本轮无产品选择需用户拍板；阻塞项均为 wire versioning、批次依赖与 strict schema 闭合。修订后再送 r5。
