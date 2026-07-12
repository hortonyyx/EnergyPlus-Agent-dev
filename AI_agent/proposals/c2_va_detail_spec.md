# C2 Va 代码级施工细稿 v2（2026-07-12）：opening × claim applicability 薄适配

> **版本史**：v1（2026-07-12，基于仓库 `db651e3`）首次出稿。
> **r1→v2**：Fable 最高档 r1 `APPROVE-WITH-CHANGES`（0 MAJOR + 2 MINOR + 1 NIT 束，[判词](../logs/reviews/verdict/2026-07-12_c2_va_spec_review_r1.md)）→ v2 全部采纳 VA-R1/VA-R2/VA-R3：移交 completeness user/dataset 生成接缝、关闭 package import 环、收紧字段措辞/golden 口径/七 claim span 一致性。
>
> **角色与审向**：sol 次高档出稿；Fable 最高档交叉审，谁写谁不批。
>
> **状态**：v2 **定稿**（2026-07-12 主控 closure 复核通过：三 findings 落点逐字核实——§1.2 接缝显式移交 B4b、§10/§11 __init__ 不导出+import-order 回归、§3.2#5/§3.3#2/§6.3#3/§11.31 措辞与断言全落）。Va 施工待排（本轮排工表只含出稿）。
>
> **放行边界**：本文是累计式、自包含施工合同，只放行 Va 批的纯适配核、strict wire、A0 合同登记与 Va 专属测试。**不放行** B4a、B4b、B5、B5b、E4、reader、gt、scorer、render、REPORT、golden 或运行编排的顺带施工。
>
> **唯一目标**：实现同一个 gt-blind 纯函数 `Va(Vg 输出, B-M manifest, opening claims) -> opening × claim applicability`。Va 不重算 footprint、segment 或 visibility；judge 与执行器分别用自己的 opening-claim 输入调用同一函数，B4b 后续直接消费 Va 的稳定机读结果。

---

## 0. 权威口径、现状与施工门

### 0.1 本稿内已机械并入的上位定案

以下口径在本稿内完整展开，施工者不需要另读旧稿才能实现；冲突时仍按派单列出的权威顺序裁决：

1. Va 是 **gt-blind、无 I/O、无副作用的薄适配**；Vg 才拥有几何分段与 1D skyline 可见性。
2. claim 词汇封闭为 `existence / host / along / width / sill / head / appearance`；输出必须对每个 opening 固定给出七行，不得因输入缺值、产品漏报或图种不支持而删行。
3. plan 通道可立证 `existence/host/along/width`；elevation 通道可立证 `existence/along/width/sill/head/appearance`。`host` 不从 elevation 猜，`sill/head/appearance` 不从 plan 猜。
4. **plan 来源绕过 Vg visibility**：可信 full-floor plan 覆盖 hidden facade 上的合法 plan claim；hidden 不阻止 plan 证据。
5. **elevation 来源才与 Vg 相交**：先把 view-local 半开区间经 `ViewProjectionFrame` 映到 world，再和同 floor、同 resolved building-axis family、同 target segment 的 `visible_intervals` 相交；禁窗口中心点、段总状态、bbox 单面或“立面名看起来像南”捷径。
6. applicability 与 provenance 是两条轴。Va 不读 claim 值、置信度、`observed/derived/assumed` 或知识表；assumed sill/head 有值仍可是 `NOT_APPLICABLE(unobserved)`。
7. manifest 的 `potentially_observable_claims` 只校验“该图种允许承载什么”，不能单独证明某窗某属性在图上确有证据；正向 applicability 必须有 caller 自己的 opening×claim 正证据声明。`negative_evidence_capable_claims + coverage + CompletenessAssertion` **只额外决定缺席能否构成可信负证据**。judge 的声明来自 gt/reference，执行器的声明来自自己的输入，两边独立，产品漏报不能改 judge denominator。
8. `partially_applicable` 不等于 0.5 分、不等于整窗折半。Va 只给精确区间分区；B4b 后续按 claim 制定 scorer policy。
9. coverage 账本缺失、hash 漂移、方向未唯一解析、claim ledger 不闭合或 segment/fingerprint 不一致都是 INVARIANT/BLOCK；账本完整且算出确无证据才是诚实 `not_applicable(unobserved)`。
10. N/S/E/W 是建筑系标签，不按真北改写。`building_axis` 可由 manifest 直接认定；`true_azimuth/unknown` 必须消费绑定 manifest/orientation hash 的 resolved-direction 接缝，缺失即硬错。

### 0.2 已收录依赖的实码基座

Va 施工以当前实码为准：

- `src/agent/correction/claims.py`：七 claim 常量、`WINDOW_CLAIMS`、`CLAIMS_VOCAB_VERSION="1"`；
- `src/agent/execution/view_manifest.py`：`ViewManifest`、`RequiredViewEntry`、`OpeningEvidence`、`Coverage`、`CompletenessAssertion`，schema/generator/completeness ruleset 均为版本 `"1"`；
- `src/agent/correction/schema.py`：strict v3 `FacadeSegment`、`WorldInterval`、`CorrectedGeometryV3`；
- `src/agent/correction/facade.py`：`ViewProjectionFrame` 与 `derive_view_projection_frame` 的 S/E 正号、N/W 负号、mirror XOR 约定；
- `src/agent/correction/facade_visibility.py`：Vg `facade_visibility_v1`、半开且排序不交的 `visible_intervals`、稳定 segment id/fingerprint；
- `src/agent/correction/finalize.py`、`feature_state.py`、`stage_runner.py`：v3 accepted correction 的 segments 已由 Vg 唯一 materialize，feature state=`populated`，helper tuple=`("floor_footprint_v1", "facade_visibility_v1")`，release map 导出 correction stage version `"3"`；
- `src/agent/execution/manifest.py`：accepted correction 仍是 `artifact_contract="correction_b2_v1"`，output/checks/audit/feature_states 四 hash 构成身份链。

Va 不修改以上 wire 或 owner。

### 0.3 施工前置门：只断言已收录依赖

修改 Va 文件前执行以下机械断言；不得预读或断言本批将新建的 `facade_applicability.py`、schema version、helper version或测试：

```python
from pathlib import Path

from src.agent.correction.claims import CLAIMS_VOCAB_VERSION, WINDOW_CLAIMS
from src.agent.correction.feature_state import correction_stage_version
from src.agent.execution.view_manifest import (
    CLAIMS_VOCAB_VERSION as MANIFEST_CLAIMS_VERSION,
    COMPLETENESS_RULESET_VERSION,
    VIEW_MANIFEST_SCHEMA_VERSION,
)

assert WINDOW_CLAIMS == {
    "existence", "host", "along", "width", "sill", "head", "appearance"
}
assert CLAIMS_VOCAB_VERSION == MANIFEST_CLAIMS_VERSION == "1"
assert VIEW_MANIFEST_SCHEMA_VERSION == "1"
assert COMPLETENESS_RULESET_VERSION == "1"
assert Path("src/agent/correction/facade_visibility.py").is_file()

# 必须由真实 finalize_correction_draw(v3 fixture) 产生，禁止手填 claims。
assert finalized.feature_state_claims.facade_segments == "populated"
assert finalized.feature_state_claims.helper_versions == (
    "floor_footprint_v1", "facade_visibility_v1"
)
assert correction_stage_version(finalized.feature_state_claims) == "3"
assert finalized.geom.facade_segments
```

另以现有 fixture 断言：每层 segment 全部共享该层唯一 `source_footprint_fingerprint`；`visible_intervals` 均在 `world_along_interval` 内、按半开语义排序不交；`derive_view_projection_frame(..., mirrored="unknown")` 会拒绝。

任一前置不成立则停工并回报依赖漂移；不得以临时 segment builder、默认 mirror、硬编码 manifest、伪造 feature claims 或放宽 strict schema 绕过。

### 0.4 本批步骤 1 后自检（不是开工前置）

新模块与 A0 登记完成后才执行：

```python
from src.agent.correction.facade_applicability import (
    FACADE_APPLICABILITY_HELPER_VERSION,
    FACADE_APPLICABILITY_SCHEMA_VERSION,
)

assert FACADE_APPLICABILITY_SCHEMA_VERSION == "1"
assert FACADE_APPLICABILITY_HELPER_VERSION == "facade_applicability_v1"
```

这两个名字由 Va 自己创建，禁止倒置到 §0.3 造成“施工前要求自建物已存在”的假门。

---

## 1. 范围与非目标

### 1.1 In

1. 新建 Va 纯模块及 strict typed 输入/输出模型；
2. 输入身份、manifest/方向/segment/claim-ledger 的纯内存 fail-closed 校验；
3. plan bypass 与 elevation local→world→visible interval intersection；
4. 七 claim 的稳定 total output、区间 union/complement、status/reason、可信负证据区间与 source/segment 审计；
5. accepted-correction 与 judge-gt 两种 visibility ledger 身份形状，但不实现任何 gt reader；
6. Va 专属单元、性质、纯度和 seam 测试；
7. A0 增 Va schema/helper/半开/无新容差的合同登记。

### 1.2 Out

- 不运行 Vg，不从 footprint 重建 segment，不重算 depth/visibility/fingerprint；
- 不解析 PNG/DXF/reading JSON，不做 OCR、mirror 判断、立面 matcher 或真北 adapter；
- 不匹配 product opening 与 gt opening，不判断 claim 值对错，不计算分数、权重、IoU 或 denominator 数值；
- 不做跨通道 positive/absence conflict 裁决；只输出下游裁决所需的 `negative_evidence_intervals`；
- 不填或回写 `WindowV3.facade_segment_id`，不做 room/host resolver，不 clamp window；
- 不写 attempt artifact、sidecar、run manifest、accepted pointer、REPORT 或 HTML；
- completeness 的 `user`/`dataset_ref` 两 source **生成通路不在 Va 批**：Va 只消费 B-M 已生成且 strict 验真的 `CompletenessAssertion`，不生成/持久化其 source。该遗留明确归 **B4b 细稿承接**，不得在 Va 纯核加 I/O 绕过。B-M 收口接缝登记原文留痕：**“completeness 的 user/dataset 两 source 生成通路归 Va/B4b（case_metadata source 已通）”**；v2 在 Va 侧完成显式移交，B4b 必须在其累计细稿中决定生成 owner、输入信任根、hash/attempt 绑定与测试；
- 不改 `CorrectedGeometryV3`、`ViewManifest`、`StageRecordV2`、`ArtifactKey/ArtifactContract`；
- 不新增/修改 correction.yaml 容差，不改任何 golden。

Va 输出是可规范序列化的**内存 ledger**。若 B4b 后续把它归档，B4b 必须在自己的细稿中扩 artifact contract、绑定 accepted identity 并负责 writer；Va 本批不得抢先写盘。

---

## 2. 术语、claim 顺序与区间代数

### 2.1 固定词汇与顺序

```python
ClaimName = Literal[
    "existence", "host", "along", "width", "sill", "head", "appearance"
]
CLAIM_ORDER: tuple[ClaimName, ...] = (
    "existence", "host", "along", "width", "sill", "head", "appearance"
)
ApplicabilityStatus = Literal[
    "applicable", "partially_applicable", "not_applicable"
]
ApplicabilityReason = Literal[
    "full_observable_coverage",
    "existence_observable_fragment",
    "partial_observable_coverage",
    "unobserved",
]
EvidenceChannel = Literal["plan", "elevation"]
VisibilityRule = Literal["plan_visibility_bypass", "elevation_visible_intersection"]
FacadeFamily = Literal["North", "South", "East", "West"]
```

`CLAIM_ORDER` 是 wire 顺序，不用 `sorted(WINDOW_CLAIMS)` 代替；所有 opening 输出精确七行且按该顺序。

### 2.2 半开区间

所有 Va interval 均为 world metre 或 view-local metre 的半开 `[lo, hi)`：

```python
FiniteFloat = Annotated[float, AllowInfNan(False)]
Hex64 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

class ApplicabilityIntervalV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    lo: FiniteFloat
    hi: FiniteFloat

    @model_validator(mode="after")
    def ordered(self):
        if self.lo >= self.hi:
            raise ValueError("applicability interval requires lo < hi")
        return self
```

算法只用精确序关系：

```text
intersect([a,b), [c,d)) = [max(a,c), min(b,d)) iff max(a,c) < min(b,d)
touch iff b == c or d == a; touch 不产生证据宽度
union = 按 lo/hi 排序后合并 overlap 或 exact adjacency
complement = target - union(covered)
```

Va **不接收 tolerance 参数**，也不读取 config。Vg 已用命名 epsilon 把数值拓扑异常挡在上游；Va 不得重新使用 endpoint epsilon 扩张、snap、桥 gap，代码内不得出现 `+1e-9`、`isclose` 或裸物理容差。

---

## 3. strict 输入 wire

全部 Va 新模型使用 Pydantic v2 `ConfigDict(extra="forbid", frozen=True, strict=True)`；浮点为 `AllowInfNan(False)`，hash 为小写 `Hex64`，bool 不得冒充 int/float，unknown field/隐式字符串转数字一律拒绝。

### 3.1 Vg visibility ledger

Va 不直接接整个 mutable `CorrectedGeometryV3`，只接 Vg 已 materialize 的必要事实与身份：

```python
GeometrySourceKind = Literal["accepted_correction", "judge_gt"]

class FloorVisibilityLedgerV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    floor_id: str
    source_footprint_fingerprint: Hex64
    segments: tuple[FacadeSegment, ...]

class FacadeVisibilityLedgerV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    ledger_schema_version: Literal["1"] = "1"
    helper_version: Literal["facade_visibility_v1"] = "facade_visibility_v1"
    source_kind: GeometrySourceKind
    source_schema_version: str
    source_output_sha256: Hex64
    facade_segments_sha256: Hex64
    feature_states_sha256: Hex64 | None
    helper_versions: tuple[str, ...]
    floors: tuple[FloorVisibilityLedgerV1, ...]
```

联动约束：

1. `floors` 非空，`floor_id` 唯一；每层 `segments` 非空且只含该 floor；segment id 全 ledger 全局唯一。
2. 每层所有 segment fingerprint 精确等于 ledger 的 floor fingerprint；family/normal/interval 的 strict 约束仍由现 `FacadeSegment` 执行。
3. segment canonical bytes 按 `(floor_id, family rank N/S/E/W, along.lo, along.hi, depth, id)` 排序后算 `facade_segments_sha256`；调用者给的 hash 不等即 `va_identity_mismatch`。
4. `accepted_correction`：`source_schema_version` 必须为 `"3"`，`feature_states_sha256` 必填，`helper_versions` 精确为 `("floor_footprint_v1", "facade_visibility_v1")`。文件、StageRecord 与 sidecar 的真实 hash 验证由外层 preflight 完成后才构造 ledger；Va 纯核不打开文件。
5. `judge_gt`：`feature_states_sha256` 必须为 null；judge adapter 必须用 gt 自己的 footprint 和显式 Vg tolerances独立运行 Vg，再以 gt artifact hash 构造 ledger。禁止拷 product ledger、product coverage 或 product segment hash。
6. Va 不接受空 segments 表示“全遮挡”；全遮挡应是 segment 在场而 `visible_intervals=()`。空层是机制失败。

### 3.2 elevation view resolution + projection binding

B-M manifest 没有 mirror/local-frame 真值，且 true-azimuth resolution 不回写 manifest。调用者因此给每个 required elevation 一条纯输入 binding：

```python
DirectionResolutionSource = Literal[
    "manifest_building_axis", "resolved_direction_sidecar"
]

class ElevationViewBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    input_id: str
    resolved_building_direction: FacadeFamily
    resolution_source: DirectionResolutionSource
    view_manifest_sha256: Hex64
    orientation_output_hash: Hex64 | None
    adapter_version: str | None

    source_footprint_fingerprint: Hex64
    world_axis: Literal["x", "y"]
    sign: Literal[-1, 1]
    along_origin: FiniteFloat
    mirrored: bool
    local_x_positive: Literal[
        "image_left_to_right", "image_right_to_left"
    ]
    frame_transform_sha256: Hex64
```

条件与 hash preimage 冻结如下：

1. `manifest_building_axis` 只允许 manifest entry 的 `direction_semantics="building_axis"`；resolved family 精确等于 `building_view_direction`；`orientation_output_hash/adapter_version` 都必须 null。
2. `resolved_direction_sidecar` 只允许 `true_azimuth|unknown`；两字段都必填且非空，binding 必须与 B-M 冻结接缝 `{input_id,resolved_building_direction,view_manifest_sha256,orientation_output_hash,adapter_version}` 逐字段一致。Va 不生成 sidecar。
3. `view_manifest_sha256 == ViewManifest.content_sha256`；每个 required elevation 恰一 binding，plan/detail/site 不得有 binding，缺/多/悬空均硬错。
4. family→axis 固定：N/S=`x`，E/W=`y`；base sign 固定：S/E=`+1`，N/W=`-1`；最终 sign 按 `mirrored XOR (local_x_positive==right_to_left)` 翻转。
5. 对每个使用该 binding 的 floor，family 的 Vg segments 所有 **`world_along_interval`** 的 `min(lo), max(hi)` 给 projection extent；sign 正则 `along_origin=min_lo`，sign 负则 `along_origin=max_hi`。fingerprint 必须匹配该 floor。禁止误用 `visible_intervals`（端部全遮挡段仍参与 projection extent）；这里仅核对 Vg 已给出的投影 extent，不派生新 segment/visibility。
6. `frame_transform_sha256` 的 canonical preimage 精确为：

```jsonc
{
  "schema": "view_projection_binding_v1",
  "input_id": "South_view",
  "resolved_building_direction": "South",
  "source_footprint_fingerprint": "<hex64>",
  "world_axis": "x",
  "sign": 1,
  "along_origin": 0.0,
  "mirrored": false,
  "local_x_positive": "image_left_to_right"
}
```

键排序、compact UTF-8 JSON 后 SHA-256。它与 orientation sidecar hash 分工：前者绑定 local→world frame，后者绑定真北/方向 resolution。

### 3.3 opening × claim target/evidence ledger

Va 输入的是“要判断能否判卷的 claim target + caller 自己的逐 source 正证据声明”。同一模型服务两边，但 judge 与执行器不得共享声明：judge 声明由 gt/reference adapter 产生，执行器声明由自己的 opening evidence 产生。

```python
class PlanClaimEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    channel: Literal["plan"] = "plan"
    source_input_id: str
    world_interval: ApplicabilityIntervalV1

class ElevationClaimEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    channel: Literal["elevation"] = "elevation"
    source_input_id: str
    local_interval: ApplicabilityIntervalV1

ClaimEvidenceV1 = Annotated[
    Union[PlanClaimEvidenceV1, ElevationClaimEvidenceV1],
    Field(discriminator="channel"),
]

class OpeningClaimTargetV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    claim: ClaimName
    target_world_interval: ApplicabilityIntervalV1
    positive_evidence: tuple[ClaimEvidenceV1, ...] = ()

class OpeningClaimsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    opening_id: str
    floor_id: str
    floor_ref: int
    facade_segment_id: str
    facade_family: FacadeFamily
    claims: tuple[OpeningClaimTargetV1, ...]
```

约束：

1. `opening_id/floor_id/facade_segment_id` 非空；opening id 在本次调用全局唯一；`floor_ref` 是 B-M plan metadata 的受信楼层键，不由 `Floor.name` 猜。
2. target segment 必须存在，且 `floor_id/facade_family` 匹配；七个 `target_world_interval` 语义上都是**同一 opening 的沿面跨度**，必须逐值相等，且该共同 interval contained in segment `world_along_interval`。任两 claim span 不等是 caller 构造 bug，抛 `va_claim_ledger_invalid`，不得分别算出七套 applicability。Va 只校验已有 binding，不替 B5 解析或写回 segment ref。
3. `claims` 必须恰好七条、无重复、按 `CLAIM_ORDER`；少一条是 ledger 机制失败，不产 NA。
4. 每条 positive evidence 必须引用 manifest `required_view`，且 claim 在该 entry 的 `potentially_observable_claims`；该列表只是 allowlist，**没有 evidence row 就没有正向 coverage**。
5. plan evidence：entry 必须 `view_type=plan` 且 `floor_ref` 与 opening 相等；`world_interval` 是该 source 对此 claim 的正证据区间。hidden 不影响它。
6. elevation evidence：entry 必须 `view_type=elevation`，resolved family 等于 opening family；`local_interval` 经该 view binding 映 world。direction/family 不符不能靠 projection 数值碰巧重合通过。
7. detail/site_plan 在 C2 不得出现在 positive evidence；同一 claim 同一 source 最多一行，悬空、重复、图种/claim 越权均硬错。evidence source ids 按字典序 canonical；输入可乱序，输出必须稳定排序。
8. plan world interval或 elevation mapped interval必须与 target 有正宽交集，否则是 claim/frame ledger 不一致的 INVARIANT；超出 target 的部分只在审计保留 positive mapped interval，不计 applicability，绝不 clamp 后伪称原始数据一致。
9. manifest 中**没有** positive evidence row 的 potentially-observable view 不会自动变成正证据；只有该 claim 同时具备 trusted negative capability 时，Va 才为它计算 negative-evidence interval，供下游 conflict/miss 纪律使用。
10. claim 值、provenance、confidence、knowledge_ref 不在此 wire。reader/product 漏报不能改变 judge 结果，因为 B4b 必须分别构造两次 Va 输入：judge 从 gt/reference evidence 声明构造，执行器从产品声明构造；禁止用产品声明或产品 coverage 构造 judge ledger。

`facade_segment_id` 要求的是本次判卷 target 的段身份，不等于本批给 `WindowV3` 填 ref。无法唯一绑定段属于 B4b/B5 入口的显式拒绝/NA 组合，不得让 Va 用中心点猜段。

---

## 4. 输出 wire：B4b 可直接消费的稳定形状

### 4.1 source decision 与 segment slice

```python
class SegmentEvidenceSliceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    facade_segment_id: str
    intervals: tuple[ApplicabilityIntervalV1, ...]

class SourceEvidenceDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    source_input_id: str
    channel: EvidenceChannel
    visibility_rule: VisibilityRule
    positive_evidence_declared: bool
    positive_mapped_world_interval: ApplicabilityIntervalV1 | None
    applicable_intervals: tuple[ApplicabilityIntervalV1, ...]
    negative_evidence_intervals: tuple[ApplicabilityIntervalV1, ...]
    segment_slices: tuple[SegmentEvidenceSliceV1, ...]
    negative_evidence_capable: bool
    completeness_assertion_id: str | None
```

规则：

- decision source 集是“positive evidence 引用的 source”与“对该 claim negative-capable 的 relevant source”的并集；仅 potentially-observable、两者都不是的 source 不产 decision。
- plan positive：`visibility_rule="plan_visibility_bypass"`，`positive_mapped_world_interval=声明的 world interval`，`applicable_intervals=positive mapped ∩ target`，segment slice 指 target segment；不读取 `visible_intervals`。
- elevation positive：`visibility_rule="elevation_visible_intersection"`；先 local 两端分别 `along_origin + sign*local_x`，排序为 positive mapped half-open interval；再依次与 target、target segment 的每段 visible interval 相交并 canonical merge。
- 没有 positive row 但因 negative capability 入选的 decision：`positive_evidence_declared=false`、`positive_mapped_world_interval=null`、`applicable_intervals=()`；它不能抬高 applicability status。
- `negative_evidence_capable` 仅当该 claim 在 manifest entry 的 negative list；为 true 时 assertion id 必填。plan 的 negative interval=target；elevation 的 negative interval=`target ∩ target-segment visible`，与是否有 positive row 无关。为 false 时 negative intervals 必空、assertion id 必 null。
- `segment_slices` 只分解 positive `applicable_intervals`；negative-only decision 的 slices 为空，negative 区间由同 decision + opening 顶层 target segment 审计。当前 positive slices 只会有 target segment 一项或空项，但 wire 是 tuple，不把“一张 elevation 永远只对一个外墙段”的矩形假设写进容器；C2.1 可在 schema v2 允许一个 opening target 分片到开放 segment 集。

### 4.2 per-claim result

```python
class ClaimApplicabilityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    claim: ClaimName
    status: ApplicabilityStatus
    reason: ApplicabilityReason
    target_world_interval: ApplicabilityIntervalV1
    applicable_intervals: tuple[ApplicabilityIntervalV1, ...]
    unobserved_intervals: tuple[ApplicabilityIntervalV1, ...]
    considered_source_view_ids: tuple[str, ...]
    supporting_source_view_ids: tuple[str, ...]
    facade_segment_ids: tuple[str, ...]
    source_evidence: tuple[SourceEvidenceDecisionV1, ...]
```

status/reason 唯一映射：

| union 后 covered 情况 | claim | status | reason |
|---|---|---|---|
| 精确覆盖 target | 任意 | `applicable` | `full_observable_coverage` |
| 有正宽但未全覆盖 | `existence` | `applicable` | `existence_observable_fragment` |
| 有正宽但未全覆盖 | 其余六项 | `partially_applicable` | `partial_observable_coverage` |
| 空 | 任意 | `not_applicable` | `unobserved` |

存在性是 existential claim：可见 fragment 足以立证“这个 opening 存在”；但 residual 必须保留在 `unobserved_intervals`，不得顺带把 width/head/appearance 升 full。其余 claim 无隐式推断。

`considered_source_view_ids` 包括有 positive declaration 或 trusted negative capability、但可能因 hidden 而给出空区间的视图；`supporting_source_view_ids` 只含 positive declaration 产生正宽 applicable interval 的视图。两者分开，才能审计“无正证据声明”“有声明但 target hidden”与“可信完整性覆盖该位置”。

### 4.3 opening 与顶层 ledger

```python
class OpeningApplicabilityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    opening_id: str
    floor_id: str
    floor_ref: int
    facade_segment_id: str
    facade_family: FacadeFamily
    claims: tuple[ClaimApplicabilityV1, ...]  # 恰七条 CLAIM_ORDER

class ApplicabilityBindingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    geometry_source_kind: GeometrySourceKind
    geometry_source_schema_version: str
    geometry_source_output_sha256: Hex64
    facade_segments_sha256: Hex64
    feature_states_sha256: Hex64 | None
    view_manifest_sha256: Hex64
    direction_bindings_sha256: Hex64

class OpeningApplicabilityLedgerV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    applicability_schema_version: Literal["1"] = "1"
    helper_version: Literal["facade_applicability_v1"] = "facade_applicability_v1"
    claims_vocab_version: Literal["1"] = "1"
    view_manifest_schema_version: Literal["1"] = "1"
    visibility_helper_version: Literal["facade_visibility_v1"] = "facade_visibility_v1"
    bindings: ApplicabilityBindingsV1
    openings: tuple[OpeningApplicabilityV1, ...]
    content_sha256: Hex64
```

canonical order/hash：

1. openings 按 `(floor_id, facade_segment_id, opening_id)`；claims 按 `CLAIM_ORDER`；source evidence 按 `(channel rank plan=0/elevation=1, source_input_id)`；interval 按 `(lo,hi)`；segment slice 按 id。
2. `direction_bindings_sha256` 是所有 binding canonical model dump 排序后的 SHA-256；空 tuple 也有确定 hash。
3. `content_sha256` 是顶层 canonical payload 排除自身后的 SHA-256；同语义乱序输入必须产逐字节相同 canonical JSON。
4. 输出不含时间戳、路径、run id、product/gt 标签、claim value 或浮动 tolerance。

### 4.4 B4b 消费纪律（接缝冻结，本批不施工）

B4b 可机械映射：

```text
applicable              -> claim 进入可判域；按该 claim scorer 计 denominator
partially_applicable    -> 进入 PARTIAL 分支，消费 precise intervals；禁止自动 0.5
not_applicable/unobserved -> NOT_APPLICABLE(unobserved)，denominator 排除
```

B4b 必须把七 claim 行逐行落 sidecar，不得把 opening status 汇总成一个 bool；必须保留 Va `content_sha256`、bindings、source ids、applicable/unobserved intervals。B4b 的 score policy、partial claim 如何切片、sidecar artifact contract 与 render 灰纹均由 B4b 细稿定案，Va 不越界。

---

## 5. 公共函数签名与纯度边界

新建 `src/agent/correction/facade_applicability.py`，公开面精确为：

```python
FACADE_APPLICABILITY_SCHEMA_VERSION = "1"
FACADE_APPLICABILITY_HELPER_VERSION = "facade_applicability_v1"

class FacadeApplicabilityInvariantError(ValueError):
    code: str
    context: dict

    def __init__(self, code: str, context: dict):
        self.code = code
        self.context = dict(context)
        super().__init__(f"{code}: {self.context}")

def derive_opening_claim_applicability(
    *,
    visibility: FacadeVisibilityLedgerV1,
    manifest: ViewManifest,
    elevation_views: tuple[ElevationViewBindingV1, ...],
    openings: tuple[OpeningClaimsV1, ...],
) -> OpeningApplicabilityLedgerV1:
    ...
```

函数要求：

- keyword-only，无默认 manifest/binding/openings，无 tolerance 参数；
- 不 mutation caller-owned list/model；输出全部 fresh immutable tuple/model；
- 允许 import `claims.py`、`schema.py`、`facade.py` 的 frame dataclass、`facade_visibility.py` 的公开 version/类型事实、`view_manifest.py` 的 schema 类型，以及 stdlib hash/json/math；
- 禁止 import gt、judge、scorer、LLM、reading loader、run manifest writer、checks policy、render、network；
- 禁止文件/环境/clock/random/log I/O，禁止 `load_core_tolerances()`，禁止调用任何 Vg materialize/validate/skyline 函数；
- `ViewProjectionFrame` 只作为已验证 frame 值的 affine mapping，不调用 legacy `FacadeWorldFrame/derive_facade_frame`；
- 相同语义输入重复调用结果相等且 canonical JSON 字节相同。

外层 accepted-correction adapter 在调用前负责文件和 record 验证；judge adapter 在调用前负责 gt hash/Vg 构造。二者都只把纯内存 ledger 送进本函数，不为方便把 I/O 塞回 Va。

---

## 6. 确定性算法（逐步可施工）

### 6.1 入口身份与 totality 校验

1. Pydantic strict parse 所有 Va 新输入；现 `ViewManifest` 自身 validator 重算 content hash。
2. 校验 manifest 四版本均为 `"1"` 且 `claims_vocab_version` 与 claims 常量一致。
3. 重算 visibility segment hash、逐层 fingerprint/segment id/排序完整性；执行 §3.1 source-kind 联动。
4. 对 manifest 每个 required elevation 校验且只校验一条 binding；执行 §3.2 semantics/hash/frame 约束。
5. 对 opening id、floor/floor_ref、segment binding、七 claim totality 执行 §3.3 约束。
6. 任一步机制失败立即抛 structured invariant；不得返回部分 openings，也不得把失败 claim 填 `unobserved`。

### 6.2 positive declaration 校验与 negative source 枚举

对每个 opening、每个 claim 分两步构造 source 集：

```python
positive_sources = every explicitly declared ClaimEvidenceV1
    after manifest view_type/floor/family/claim allowlist validation

negative_sources = required entries where
    claim in negative_evidence_capable_claims
    and (
        plan + floor_ref matches
        or elevation + resolved family matches
    )

decision_sources = positive_sources union negative_sources
```

`potentially_observable_claims` 只校验 positive declaration 合法性，不自行加入 `decision_sources`。单通道实体因此不会因另一张“理论上可观察但实际上没有该窗/属性证据”的图被误记 miss。产品删自己的 declaration 会改变执行器侧 ledger，但**不能改变 judge ledger**；judge declaration 由 gt/reference 独立构造。manifest 中 required view 整张漏产物仍由 `reading.view_manifest_coverage` 上游 BLOCK，Va 不负责把整图漏读解释为 unobserved。

### 6.3 plan 分支

每个进入 decision set 的 plan source 产一条 decision：

1. 若有 positive declaration，`applicable_intervals=declared world interval ∩ target`；若无则空；
2. 不读/不碰/不 import Vg visibility entry point；
3. 若 claim 在 negative list，则验证 `coverage.frame == "plan_floor_region" and coverage.region == "full_floor"` 且 assertion link 已成立，negative interval=target；否则 negative interval 空；
4. hidden segment、empty visible intervals 或 facade depth 都不得改变结果。

### 6.4 elevation 分支

每个进入 decision set 的 elevation source：

1. 若有 positive declaration，取且只取该 claim/source 的 local interval；用已验证 binding 映两端并排序；`candidate = mapped ∩ target`，空则 ledger/frame mismatch；`covered = union(candidate ∩ target_segment.visible_intervals)`；
2. 若没有 positive declaration，positive mapped=null、covered=空，不伪造正证据；
3. negative capable 时另算 `negative_covered = union(target ∩ target_segment.visible_intervals)`，不借 positive interval 缩小 trusted completeness coverage；
4. decision 分别记录 positive mapped/covered 与 negative covered；只正宽相交，touch 不算；
5. 即使 manifest 声明 `full_facade`，Vg hidden residual 也不能成为 elevation 负证据；
6. 禁止拿同 family 的浅段 visible interval替深 target 段背书；target segment id 是物理段身份，投影重叠不等于同 opening。

### 6.5 aggregate 与 reason

1. 合并所有 source decisions 的 applicable intervals，并 clip 在 target 内；求 complement。
2. 依据 §4.2 唯一表产 status/reason；不得由 source 数、confidence 或 completeness 改写。
3. source ids、segment ids canonicalize；零 positive source 是合法 honest unobserved。若有 negative-only source，其 negative intervals 仍保留，但不得把 status 抬为 applicable。
4. opening 七行完成后做 output totality revalidation；最终算 bindings hash 与 content hash。

---

## 7. gate id、失败分类与审计

### 7.1 纯核错误 code

`FacadeApplicabilityInvariantError(code, context)` 的 code 值域固定：

| code | 触发 |
|---|---|
| `va_identity_mismatch` | manifest/geometry/segment/direction/content hash 不符，source-kind identity 联动错误 |
| `va_visibility_ledger_invalid` | floor/segment/fingerprint/visible interval ledger 不完整或错绑 |
| `va_direction_unresolved` | elevation binding 缺失、多份、semantics 不符、true/unknown 无 sidecar 绑定 |
| `va_projection_frame_invalid` | axis/sign/origin/mirror XOR/fingerprint/frame hash 不符 |
| `va_opening_segment_invalid` | opening segment 不存在、floor/family/interval 不符或无法唯一绑定 |
| `va_claim_ledger_invalid` | 七 claim 不全/重复、evidence 重复/悬空/越权、mapped 与 target 无正宽交集 |
| `va_output_totality_invalid` | 输出非七行、区间 partition 不守恒、排序/hash 不自洽 |

`context` 只放 canonical 可 JSON 化事实：`opening_id/claim/input_id/floor_id/facade_segment_id/declared/recomputed` 等；不得放绝对路径、整个 PNG、模型 repr 或非确定时间。

### 7.2 外层 check id

后续 caller 把 error 机械映射为以下 check；全部 `CheckLayer.INVARIANT`、所有 run profile 恒 BLOCK：

| check_id | errors |
|---|---|
| `applicability.input_identity` | `va_identity_mismatch` |
| `applicability.visibility_ledger` | `va_visibility_ledger_invalid` |
| `applicability.direction_binding` | `va_direction_unresolved`, `va_projection_frame_invalid` |
| `applicability.opening_claim_ledger` | `va_opening_segment_invalid`, `va_claim_ledger_invalid` |
| `applicability.output_totality` | `va_output_totality_invalid` |

Va 本批只冻结 mapping，不接 `CheckReport` writer；B4b 入口接线归 B4b 施工。任何 invariant 均不能被 exploratory profile 降 WARN。

### 7.3 成功审计形状

成功时 `OpeningApplicabilityLedgerV1` 本身就是完整审计：

- bindings 证明使用哪份 geometry/Vg/manifest/direction；
- source decision 证明 plan bypass 或 elevation intersection 的每一步；
- applicable/unobserved partition 证明 status；
- negative interval + assertion id 证明缺席何处可作可信负证据；
- content hash 供 B4b 后续 sidecar 绑定。

不得另写自由文本 `audit.json`、不得把 success trace 塞进 correction `corrections/conflicts/unsupported`。

---

## 8. 关键语义矩阵与反例

### 8.1 hidden/partial 矩阵

| 场景 | existence | host | along | width | sill/head | appearance |
|---|---|---|---|---|---|---|
| hidden segment + plan 对四 claim 有正声明 | applicable | applicable | applicable | applicable | 无 elevation 正证据则 NA | 无 elevation 正证据则 NA |
| elevation target 全可见且六 claim 有正声明、无 plan | applicable | NA | applicable | applicable | applicable | applicable |
| elevation target 部分可见且六 claim 有正声明、无 plan | applicable（fragment） | NA | partial | partial | partial | partial |
| plan 四 claim 正声明 + elevation 两属性 partial 正声明 | applicable | applicable | applicable | applicable | partial | partial |
| 两类 relevant source 都无 | NA | NA | NA | NA | NA | NA |

“applicable”只说 reference 正证据落在可判域，不说 product 的值正确；reference 已声明而 product 漏画是 miss，judge 侧不得用 product 缺声明把它改成 NA。

### 8.2 sm26 语义锚

内凹 hidden/内壁 opening：

- plan 对 `existence/host/along/width` 的正证据声明仍使四项 full applicable；
- elevation hidden 对 sill/head 不给 coverage，故 `not_applicable/unobserved`；
- correction 中若 sill/head 由 prior 填值且 provenance=assumed，Va 结果仍不变；
- elevation completeness 即使承诺 openings 完整，negative interval 也只能落在 Vg visible subset，hidden absence 不构成负证据。

### 8.3 completeness 与 applicability 分轴

同一 visible target、同一 manifest view、同一 positive evidence declaration：

- negative list 空：claim 仍可 applicable；`negative_evidence_capable=false`；
- negative list 含 claim 且 assertion 完整：applicability status **不变**，只新增 negative evidence intervals；
- reader 自报“低清/没看见”不能作为删除 judge declaration 的依据；judge ledger/hash 不变，执行器自己的 evidence ledger可诚实反映缺失；
- manifest completeness link 损坏：ViewManifest strict parse/identity gate BLOCK，不产 NA。

---

## 9. 建筑复杂度扩展缝

C2 当前 schema/Vg family 词汇仍封闭 N/S/E/W，但 Va 实现不得烤死“恰四张立面、每 family 恰一图、矩形每面一段”：

1. 所有 view、floor、segment、opening 都是 tuple/list 枚举，不写 `len==4`、`North/South/East/West` 四变量或按固定文件名取图；
2. output 以 opaque `facade_segment_id`、`source_input_id` 为主键；family 只负责当前 Vg 投影选择；
3. segment slices 是集合形状而非单 scalar；
4. C2.1 若引入局部/内院立面，新增 discriminated schema v2 的开放 `projection_surface_key/resolved_direction_vector`，复用 interval intersection 核；不得原地把 v1 Literal 放宽并改变旧字节；
5. C2 仍拒 `view_kind=partial`；partial view 的 coverage intervals 归 C3 schema bump，不在 Va v1 用自由 dict 偷渡。

---

## 10. 文件级施工清单

| 文件 | 本批动作 | 禁止事项 |
|---|---|---|
| `src/agent/correction/facade_applicability.py`（新） | §2–§7 strict models、error、pure derive、canonical hash | 无 I/O/config/gt/judge/scorer/LLM/Vg materialize |
| `src/agent/correction/__init__.py` | **不改、不导出 Va 符号**。消费者一律直接 `from src.agent.correction.facade_applicability import ...` | 防包级环：`execution.view_manifest → correction.claims` 会先执行 `correction/__init__`；若其再导 Va，便形成 `correction/__init__ → facade_applicability → execution.view_manifest`，此时 `ViewManifest` 尚未定义 |
| `tests/test_c2_va_applicability.py`（新） | §11 全量 Va 测试 | 不改 golden |
| `tests/test_c2_vg_visibility.py` | 仅把现“Va seam stub”保留为 Vg seam 或去重到真实 Va test；不得改 Vg expected | 不改 Vg 算法/容差 |
| `skills/intake_pipeline/1_correction/A0_contract.md` | 登记 Va schema/helper/半开/无新容差 | 不改 A1–A4 权威矩阵 |

原则上不需要改 `schema.py`、`view_manifest.py`、`facade_visibility.py`、`facade.py`、`feature_state.py`、`manifest.py`。若实作发现必须改其中 wire/算法，停止扩批并回细稿复审，不现场兼容。

---

## 11. 测试族（累计全量）

### 11.1 strict wire 与 identity

1. 七 claim exact order 正例；缺一、重复、乱造第八词、错顺序分别拒。
2. 全部新模型 unknown field、数字字符串、bool-as-number、NaN/±inf、空 id、`lo>=hi` 拒。
3. visibility ledger：重复 floor/segment、跨 floor segment、fingerprint 漂移、segment hash 漂移、accepted 缺 feature hash、judge_gt 伪带 feature hash、wrong helper tuple 全拒。
4. manifest 任一字段篡改但 content hash 未改，先由 ViewManifest 拒；bindings manifest hash 漂移由 Va 拒。
5. target segment 不存在、floor/family 错、target interval 越 segment、七 claim 的 `target_world_interval` 任两不等、opening id 重复全拒。
6. output hash 自复算、篡改任一 interval/source/status 后不一致；语义等价乱序输入输出 canonical bytes 相同。

### 11.2 direction/frame 矩阵

7. 四 family × `mirrored={False,True}` × local convention 两值，逐格断言 XOR sign、origin 与 local→world 两端。
8. building_axis manifest resolution 正例；family 与 `building_view_direction` 不等拒。
9. true_azimuth/unknown：sidecar binding 全字段正例；缺 orientation hash、adapter version、manifest hash 漂移、不可唯一 resolved family 拒。
10. unknown mirror、错误 axis/sign/origin、frame fingerprint/hash 漂移拒；不得默认为 false。
11. manifest 每个 elevation 恰一 binding：缺、多、plan 多余 binding、悬空 input id 各拒。

### 11.3 核心 applicability

12. rectangle 全 visible：显式 plan 四 claim 正声明均 full，显式 elevation 六 claim 正声明均 full；host 的 elevation evidence、sill/head/appearance 的 plan evidence 作为越权输入拒。
13. `Z` partial：target deep segment 的 elevation positive evidence 跨 visible/hidden，existence=applicable(fragment)，其余 elevation claims=partial，区间与 complement 逐值相等。
14. `FULL_OCCLUDE`：target deep segment 即使有 elevation positive declarations，六个 elevation-observable claim 均 unobserved；同 target 加 plan 四项 positive evidence 后四 claim full，证明 plan path 没读 visibility。
15. 端点半开：target `[0,2)` 与 visible `[2,4)` 为零覆盖；exact adjacent source intervals merge；真 gap 不桥接。
16. 多 source union：两个 elevation 可见片段合成 full；overlap 去重不重复 denominator；一个 plan full 压过 elevation partial 但 source audit 全保留。
17. local projection mapped 与 target 部分交集按交集计；完全 disjoint 是 ledger invariant，不是 NA。
18. negative capability：空 negative list 不影响 applicable；三类 CompletenessAssertion 已由 manifest parse，Va 正确输出 assertion id；plan negative full、elevation negative 仅 visible subset。
19. positive evidence 重复、悬空 source、图种/claim/floor/family 越权均 BLOCK；缺 positive declaration 本身合法产 NA。另以双调用 fixture 证明删产品 declaration 只改变执行器 ledger，不改变独立 gt/reference judge ledger。

### 11.4 上位语料与消费者 seam

20. 凹形 hidden 四例：plan positive 保留；plan trusted absence 有 full negative interval；elevation absence hidden 为零 negative interval；elevation positive 只在 visible subset 生效。
21. sm26 三反例：plan `existence/host/along/width` full；sill/head assumed 值不进 Va 输入且结果 NA；hidden elevation completeness 不制造负证据。
22. provenance 正交：对同 target 分别构造 observed/derived/assumed 的外层 Window fixture，adapter 丢弃 provenance 后 Va bytes 相同。
23. judge/executor parity：两边用语义相同但对象实例/输入次序不同的 ledger，Va canonical bytes相同；judge fixture 明确从 gt Vg ledger构造且不引用 product hash。
24. B4b seam contract test（不实现 scorer）：机械读取每 opening 七行，验证 status→`INCLUDED/PARTIAL/NOT_APPLICABLE(unobserved)` 的形状足够；partial 不出现 0.5/weight 字段。

### 11.5 纯度、性质与回归

25. import graph 无 gt/judge/scorer/LLM/reading loader/manifest writer；monkeypatch `open`、env、clock、random、config loader 与所有 Vg entry points为 raise 后，Va 对内存输入仍运行。
    - **import-order 独立回归**：新 Python 进程分别执行 `import src.agent.execution.view_manifest` 后再 `import src.agent.correction.facade_applicability`，以及反向先后序；两条均无 ImportError、拿到同一 public types。测试同时断言 `src.agent.correction` 不暴露 Va public symbol，锁住 §10 的环路禁令。
26. 输入 deep copy 前后相等；重复调用相等；并发调用无共享可变状态。
27. 小整数半开区间 property：independent oracle 验 union/intersection/complement partition，`covered ∪ unobserved == target` 且二者不交；oracle 不复用 Va helper。
28. 任意打乱 floors/segments/openings/positive-evidence/source entries，canonical result稳定；claim 输入自身错顺序按 §3.3 拒，不静默重排坏 wire。
29. 一张、零张及多张 relevant view均可运行；测试中不得断言 elevation 数量等于四。
30. legacy v1/v2 correction 不接 Va、不改变现行为或 bytes；Vg/B-M/B2/B3/B2b既有 tests 全绿。
31. 全量 suite 绿、strict xfail 集合不变、**sm20/sm21 golden + 全部既有 anchor 零修改**；§11.21 的 sm26 语义继续用合成 fixture，不新增或假称 sm26 golden。新增失败必须归因，禁止更新 golden 吞回归。

---

## 12. A0 登记与版本纪律

A0 新增非 tolerance 合同登记：

| name | value | owner | 语义 |
|---|---|---|---|
| `FACADE_APPLICABILITY_SCHEMA_VERSION` | `1` | Va | §3/§4 strict input-output wire；未知版本 fail closed |
| `FACADE_APPLICABILITY_HELPER_VERSION` | `facade_applicability_v1` | Va | §6 算法与 canonical hash 语义 |
| `CLAIMS_VOCAB_VERSION` | `1`（引用既有） | claims.py | Va 输出恰七 claim，按 CLAIM_ORDER |

A0 同节写明：Va interval 恒为 `[lo,hi)`；plan visibility bypass；elevation local→world→target→Vg-visible；existence fragment 的特殊 status；completeness 不 gate 正向 applicability，只 gate negative-evidence capability；Va 无 tolerance、不得读 correction.yaml。

schema bump 规则：字段增删、enum 语义变化、claim 顺序变化、status 聚合变化或 hash preimage 变化必须新 schema/helper version；不得原地修改 v1。仅实现重构且 canonical output 对全测试不变可保版本。

---

## 13. 施工顺序

1. 跑 §0.3 依赖门并保存结果；
2. 建新模块常量、strict models、error 与 A0 登记，跑 §0.4；
3. 实现 canonical interval leaf helpers与独立 leaf tests；
4. 实现 visibility ledger/manifest/direction/frame/claim closure validators；
5. 实现 plan bypass；
6. 实现 elevation projection + target/Vg-visible intersection；
7. 实现 aggregate/status/reason/negative intervals/canonical hash；
8. 加 strict、hidden/partial、sm26、direction、pure/property tests；
9. 跑 Va 专属、依赖批回归、全量 suite；确认 git diff 只含本批批准文件且零 golden；
10. 提交执行简报给独立审者；施工者不作最终批准。

---

## 14. 验收清单

施工完成须同时满足：

- 公共签名、全部 strict wire、error codes、check-id mapping 与本文逐字一致；
- plan path 在 Vg entry points 全被封锁时仍可运行；elevation path 只消费 accepted Vg intervals，不重算 geometry；
- 每 opening 固定七行，covered/unobserved 精确 partition；existence fragment 与其余 partial 分开；
- judge 与执行器各自构造 positive-evidence ledger；产品删自己的声明不能改变 judge ledger，悬空/越权/重复声明是 BLOCK，诚实无正证据才是 NA；
- accepted correction hash/feature state 与 judge gt 独立 ledger 两条入口身份均可审计；
- C-03 completeness/negative evidence 与 applicability 分轴；C-04 building-axis/true-azimuth/unknown 守卫均 fail closed；
- B4b 可只读 ledger 稳定字段区分 INCLUDED/PARTIAL/NOT_APPLICABLE，无需猜段总状态；
- 无新容差、无 I/O、无 gt/judge/scorer import、无 code/test/golden 越界；
- §11 全测试与全量 suite 通过，零 golden；
- 独立交叉复核者只看本文、diff、tests 即可复建算法，不依赖聊天上下文。

---

## 15. 交叉审重点（review ask）

1. 复核“positive applicability 必须来自 opening×claim 正证据声明；manifest potentially-observable 只作 allowlist；completeness 只决定 negative evidence”的三分法是否与 B4b denominator 完全一致。本文用 judge/reference 与 product 两次独立 Va 调用防产品漏报洗 judge denominator。
2. 复核 `existence` 在任意正宽 visible fragment 上直接 `applicable`、其余六 claim 保持 partial 的聚合裁决。
3. 复核 Va 要求 opening target 先有唯一 `facade_segment_id` 是否与 B4b 的匹配顺序兼容；本文把它定义为 scorer 输入的临时 target binding，不授权 Va/B5 写回 Window。
4. 复核 true-azimuth/unknown 只消费 B-M 已冻结的 resolved-direction 接缝、Va 不抢 E4 sidecar owner 的批界。
5. 复核 B4b 对 `partially_applicable` 是否只需本文区间 ledger 即可制定 claim-specific policy；本文有意不冻结 0.5 或其他评分权重。
