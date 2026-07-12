# C2 E4-output-contract 代码级施工细稿 v1：Relative 出口 + Zone 零原点 + 真北 θ 唯一 owner

> **状态**：2026-07-12 次高档细稿；Fable 独立交叉审 **APPROVE**（零残余 BLOCKER/HIGH）。唯一上位定案为 [c2_full_unlock_design.md](c2_full_unlock_design.md) v2.2 §E4，实证基线为 [E4 probe RESULTS](../logs/experiments/2026-07-10_e4_relative_north_axis_probe/RESULTS.md)。
> **基座**：commit `bac689b`。本文是累计式、自包含施工合同；新执行者只读本文即可施工，无需回读评审对话。现状行号只用于定位，若施工时漂移，以本文点名的符号和不变量为准。
> **批次边界**：本稿只冻结 `E4-output-contract` 的施工方案与 B-O 消费合同；实际接线仍由后续 **B-O** 批执行。本轮不改代码、不改测试、不改 golden。

---

## 0. 结论、范围与非目标

### 0.1 唯一方案

E4 是 **EP 出口坐标声明迁移**，不是几何旋转：

1. correction/kernel/specs/gt/judge 中的所有坐标继续保持建筑系；建筑 +Y 是建筑北，顶点不乘旋转矩阵；
2. E4 合同路径把 EnergyPlus `GlobalGeometryRules` 三个坐标字段显式设为 `Relative`；
3. 所有 `Zone` 的 `X Origin / Y Origin / Z Origin / Direction of Relative North` 由代码统一覆写为 `0.0`；
4. 保留现有“建筑系绝对顶点”，因 Zone 原点和方向全零，这些数值在 EP Relative 语义下仍表示同一刚体；
5. `Building.North Axis = θ`，θ 是“真北到建筑 +Y 的顺时针角”，规范域 `[0, 360)`；
6. θ 的唯一权威 owner 是 **manifest-accepted correction orientation 产物**；4_mep 的 `building.north_axis` 只是兼容占位且只允许 `0.0`；
7. v1/v2 或无法证明属于 E4 的旧 IntakeOutput 继续走 `World` legacy；v3/E4 即使 θ 恰为 `0.0` 也必须走 `Relative`；**禁止**任何 `if theta != 0`、truthiness 或数值猜分支。

### 0.2 In（B-O 按本稿施工的完整改面）

- 内部 `OutputCoordinateContract` strict 类型、派生器、持久 sidecar、加载/校验入口；不扩 `IntakeOutput` 11 字段；
- accepted correction schema/digest 绑定，integrated 与 stepwise 两路径同一派生/校验；
- S4 MEP 占位 0 硬门与 S5 无条件 θ override；
- intake seed 的 `GlobalGeometryRules` 确定性设置；
- Zone Origin/Direction 的代码级归零、迁移门和最终 IDF 门；
- building-bound 坐标对象闭世界 registry、源码/IDD/运行时三层审计；
- `GlobalGeometryRules` A3/A4/A5 完整建模和显式写出；
- integrated、stepwise、`--intake-from`、`--reading-from`、export-only、simulate 六入口对等；
- EP 25.1 端到端五条断言与全部测试族。

### 0.3 Out（明确不借机施工）

- 不旋转 correction、kernel、`BuildingGeometry` 或 specs 顶点；
- 不把 N/S/E/W facade 标签改成真北方位；
- 不改变 `NorthAxisEvidence` 的证据采集、优先级、sanity 或 provenance 政策；这些由 correction orientation 批产出，本批只消费 accepted typed value；
- 不给 v1/v2 伪造 `NorthAxisEvidence`，不迁写历史 IntakeOutput/IDF/golden；
- 不新增 shading/daylighting 功能；只做 registry、显式分类和“若将来出现则必须受合同管理”的门；
- 不改变 11 字段 IntakeOutput wire，不移除 `MepOutput.building.north_axis`；breaking MEP schema 留未来版本；
- 不顺修 stepwise 的其他历史 root-copy/accepted-pointer 问题，除非它直接导致 E4 合同绕过。

---

## 1. 权威语义与不可变式

### 1.1 θ 语义

`NorthAxisEvidence.value_deg` 的定义冻结为：**从真北方向顺时针转到建筑 +Y 方向的角度**。进入 accepted correction 前已正规化到 `[0,360)`；E4 消费端仍须 strict round-trip 验证有限性和范围，不信任对象类身份或 `model_copy(update=...)`。

例：

| θ | 建筑 +Y 的真方位 | 预期 EP 表面 azimuth 变化 |
|---:|---|---|
| 0 | 真北 | 相对 θ=0 基线不变 |
| 90 | 真东 | 每面 `+90 mod 360` |
| 270 | 真西 | 每面 `+270 mod 360` |

最终 θ=0 仍要保留 `provenance/source_ids/uncertainty/method/frame_transform_hash`；“观测到真零”与“未知后 assumed 0”不可混，但二者都属于 E4 Relative 合同。

### 1.2 四条核心不变量

1. **geometry invariant**：E4 前后同一 surface/fenestration 的建筑系顶点逐值不变；只改 EP frame metadata。
2. **single-owner invariant**：最终 `Building.north_axis` 只能由 accepted correction `north_axis.value_deg` 决定；MEP、用户 prompt、Zone、facade 名、旧 IntakeOutput 中的数值都无权竞争。
3. **zero-zone-frame invariant**：Relative 合同下每个 Zone 的四个 frame 字段精确为浮点 `0.0`；不存在“高层 z_origin=层底标高”的例外。
4. **explicit-dispatch invariant**：分支只看经过验证的 `OutputCoordinateContract.mode` 及其 source binding；禁止看 θ 数值、provenance、是否有指北针、building 字段当前值或 warning 文本来猜模式。

### 1.3 EP 25.1 已验证事实

权威探针采用 `World θ=0` 与 `Relative θ=0/90/270` 四变体，Relative 变体均使用全零 Zone Origin/Direction 和现有建筑系绝对顶点：

- θ=0：114/114 个同名 HeatTransfer Surface azimuth 与 World 基线逐面相等；
- θ=90：114/114 逐面 `+90 mod 360`；
- θ=270：114/114 逐面 `+270 mod 360`；
- 14 区在三组比较中的 Floor Area / Volume 共 42 对完全相等；
- World 独有 `Any non-zero Building/Zone North Axes or non-zero Zone Origins are ignored` 及配套 coordinate mismatch warning；三个 Relative 变体均无。

因此本稿不再开放 World+North Axis 或顶点预旋转等备选路线。

---

## 2. 现状对账（`bac689b`）

| # | 现状事实 | 代码落点 / 风险 |
|---|---|---|
| 1 | `NorthAxisEvidence` 已落 strict v3 schema，含 `value_deg/provenance/source_ids/uncertainty_deg/method/frame_transform_hash`，validator 做 `%360` | `src/agent/correction/schema.py`；E4 只消费，不另造角度类型 |
| 2 | B2 phase contract 目前要求 correction draw 的 `north_axis is None` | `src/agent/correction/parse.py`；B-O 接线前必须由 orientation 产物形成新的 accepted correction attempt，不能拿 B2 空槽继续下游 |
| 3 | `MepOutput` 拥有完整 `BuildingSchema`；`assemble_intake_output` 目前原样复制 `mep.building` | `src/agent/intakeoutput.py`；θ 尚无 deterministic owner override |
| 4 | `check_mep` 尚未把 `building.north_axis == 0.0` 做成 S4 INVARIANT | `src/validator/checks/mep.py`；非零 LLM 输出可能进入 S5 |
| 5 | `IntakeOutput` 是稳定 11 字段，当前无 schema/version/coordinate-mode 字段 | `src/agent/state.py`；分派元数据必须 sidecar/AgentState 内置，不能塞第 12 字段 |
| 6 | `_seed_config()` 只写 Building 和 Site | `src/agent/nodes/intake.py`；`ConfigState.global_geometry_rules` 留默认 World |
| 7 | `GlobalGeometryRulesSchema` 只建模 A1/A2/A3，A3 默认 `World`；EP IDD 的 A4/A5 未建模 | `src/validator/data_model.py`、`src/converters/setting_converter.py`；日照参考点/矩形表面坐标系靠 EP 默认，不够显式 |
| 8 | Zone prompt 要求高层 `z_origin=楼层下标高`，且允许 description 指定 zone rotation | `src/agent/nodes/zone.py`；与“顶点已含绝对 z + Relative”组合会重复平移 |
| 9 | Zone tool/schema/converter 允许四个 frame 字段为非零 | `src/agent/tools/zone_tools.py`、`src/validator/data_model.py`、`src/converters/zone_converter.py`；prompt 不能替代代码门 |
| 10 | geometry specs 明写 world/absolute coordinates，surface/fenestration agents照抄顶点 | `src/agent/geometry/specs.py`、`src/agent/nodes/surface.py`；文案须改称 building-frame absolute values，数值不改 |
| 11 | `ConfigState` 当前可输出的直接坐标对象只有 Zone、`BuildingSurface:Detailed`、`FenestrationSurface:Detailed`，无 shading/daylighting schema/converter | `src/mcp/state.py` + `src/converter_manager.py`；仍需闭世界门防未来 producer 加入后漏审 |
| 12 | integrated `run_pipeline` 与 stepwise `run_stage.py` 各自装配；downstream 另有 `--intake-from` short-circuit | `src/agent/pipeline.py`、`scripts/tool_scripts/run_stage.py`、`src/agent/nodes/intake.py`、`src/agent/runner.py`；三入口都必须携带同一内部合同 |
| 13 | stepwise correction accepted identity 已有 `RunManifestV2`、`StageRecordV2.output_hash/artifact_hashes`、`correction_b2_v1` | `src/agent/execution/manifest.py`；E4 直接绑定，不另造“最新 root 文件”权威 |
| 14 | 最终 IDF 由 ConfigState→YAML→ConverterManager 生成；pre-EP gate 目前只查 interzone/schedule | `src/mcp/tools/workflow.py`；坐标合同必须在 YAML 前与 IDF 后各验一次 |

---

## 3. `OutputCoordinateContract` 类型、owner 与落点

### 3.1 新模块与 strict 类型

新建 `src/agent/output_coordinates.py`，它是内部坐标出口合同的唯一类型/派生/校验 owner。禁止把类型散落在 `state.py`、`intakeoutput.py` 或 CLI。

```python
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Hex32 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]
Hex64 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

class AcceptedCorrectionRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    binding_kind: Literal["accepted_correction"] = "accepted_correction"
    schema_version: Literal["1", "2", "3"]
    output_sha256: Hex64
    acceptance: Literal["manifest", "integrated_gate1"]
    run_id: Hex32 | None = None
    accepted_attempt: Annotated[int, Field(ge=1)] | None = None
    artifact_contract: Literal[
        "correction_b2_v1", "correction_e4_orientation_v1",
        "base_v2", "migrated_v1"
    ] | None = None

    # manifest: run_id/accepted_attempt/artifact_contract 三字段都必填；
    # integrated_gate1: run_id/accepted_attempt 必须 None，但 artifact_contract
    # 仍必填并来自实际 finalize phase（否则 v3 无法证明 orientation-ready）。
    # manifest ref 还须现场对账 StageRecordV2.output_hash、artifact_hashes["output"]、
    # accepted attempt/output.json 真 hash；不接受 stage-root convenience copy。
    # relative v3 只允许 correction_e4_orientation_v1；B2 的
    # correction_b2_v1 仍是 north_axis 未填的前置 artifact，不能冒充 E4 ready。
    # v1/v2 可读历史 base_v2/migrated_v1，也可读 B2 后 writer 的 correction_b2_v1。

class LegacyStandaloneIntakeRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    binding_kind: Literal["legacy_standalone_intake"] = "legacy_standalone_intake"
    intake_output_sha256: Hex64
    inferred_schema_family: Literal["unversioned_v1_v2"] = "unversioned_v1_v2"

SourceBinding = Annotated[
    AcceptedCorrectionRef | LegacyStandaloneIntakeRef,
    Field(discriminator="binding_kind"),
]

@dataclass(frozen=True)
class VerifiedAcceptedCorrection:
    """只在 hash-chain verifier 通过后构造；不是持久 wire。"""
    ref: AcceptedCorrectionRef
    raw_output_bytes: bytes
    raw_feature_states_bytes: bytes | None
    # 只保存 immutable bytes，不保存可原位 mutation 的 Pydantic geom/claims。
    # derive 每次重算 hash并从 bytes fresh strict parse，旧 digest 不可能绑新 θ。
    # correction_b2/e4 contract 必须有 feature bytes；历史 v1/v2
    # base_v2/migrated_v1 允许 None，且 legacy derive 不读取 feature state。

class OutputCoordinateContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    contract_schema_version: Literal["1"] = "1"
    mode: Literal["world_legacy", "relative_north_axis"]
    source: SourceBinding

    geometry_frame: Literal["building_axis_absolute_values"]
    global_geometry_coordinate_system: Literal["World", "Relative"]
    daylighting_reference_point_coordinate_system: Literal["World", "Relative"]
    rectangular_surface_coordinate_system: Literal["World", "Relative"]
    zone_origin_policy: Literal["preserve_legacy", "all_zero"]
    zone_direction_policy: Literal["preserve_legacy", "all_zero"]

    north_axis_owner: Literal[
        "legacy_mep_placeholder", "accepted_correction_orientation"
    ]
    north_axis_deg: Annotated[float, Field(ge=0, lt=360, allow_inf_nan=False)]
    orientation_provenance: Literal["observed", "derived", "assumed"] | None
    orientation_source_ids: tuple[str, ...]
    orientation_uncertainty_deg: Annotated[
        float, Field(ge=0, allow_inf_nan=False)
    ] | None
    orientation_method: str | None
    frame_transform_hash: Hex64 | None
    geometry_snapshot_sha256: Hex64 | None
    coordinate_registry_version: Literal["ep25.1-v1"] = "ep25.1-v1"

    # model_validator 冻结 mode→常量组合，任何混搭直接 raise：
    # world_legacy => accepted schema in {1,2}，或明确 legacy_standalone_intake；
    #   World/Relative/Relative（精确保留现状：
    #   A3 显式 World，A4/A5 是 EP 25.1/现 schema 的 Relative 默认），
    #   preserve_legacy/preserve_legacy, legacy_mep_placeholder,
    #   north_axis_deg=0.0，全部 orientation metadata 空；新 accepted assembly
    #   geometry_snapshot_sha256 必填，legacy standalone 唯一允许为 None。
    # relative_north_axis => accepted schema==3 且 artifact contract 是
    #   correction_e4_orientation_v1, Relative/Relative/Relative,
    #   all_zero/all_zero, accepted_correction_orientation，
    #   metadata 与 accepted correction NorthAxisEvidence 逐字段相等，
    #   geometry_snapshot_sha256 必填。
```

说明：

- `geometry_frame` 描述**数值的项目侧 frame**，不声称这些顶点是 EP World；E4 路径中它们以全零 Zone frame 写进 EP Relative。
- A3/A4/A5 在新 writer 中全显式，不依赖 IDD 默认；E4 为 Relative/Relative/Relative，legacy 为 World/Relative/Relative，后者精确保留现状而不是把 A4/A5 擅改成 World。
- tuple 化 `source_ids` + contract/ref 全层 frozen 避免派生后被原位改写；从 correction 复制时保持原序，不排序、不丢 provenance。测试必须尝试修改 nested ref.digest/run_id 并确认 Pydantic 拒绝。
- `AcceptedCorrectionRef` 绑定的是 accepted `1_correction/output.json` 的 raw-bytes SHA-256，与 `StageRecordV2.output_hash` 同口径；禁止绑定 `correction_geometry_snapped.json` 的“当前最新”root copy。
- `LegacyStandaloneIntakeRef` 只服务“历史 11 字段文件被单独拷出、没有 correction/run metadata”的兼容入口，绑定该 IntakeOutput 自身 hash；它只能派生 World legacy，永远不能升级成 Relative。新 integrated/stepwise run 不得使用此逃生口。

### 3.2 hash-chain verifier + 纯派生函数 + historical factory

```python
def load_verified_accepted_correction(
    *, run_dir: Path, manifest: RunManifestV2
) -> VerifiedAcceptedCorrection:
    """I/O 边界：只读 accepted attempt，核验 manifest/artifact/raw bytes/feature-state。"""
    ...

def verify_integrated_gate1_correction(
    *, raw_output_bytes: bytes, correction_report: CheckReport,
    feature_states: FeatureStatesArtifactV1,
) -> VerifiedAcceptedCorrection:
    """integrated 边界：仅 gate① 无 blocking 后构造 verified bundle。"""
    ...

def derive_output_coordinate_contract(
    verified: VerifiedAcceptedCorrection,
    *, geometry_snapshot_sha256: Hex64,
) -> OutputCoordinateContract:
    ...
```

固定算法：

1. 两个 verifier 先拿**真实 raw output bytes**算 SHA-256；manifest 路径逐项对账 `StageRecordV2.output_hash/artifact_hashes["output"]/attempt output.json/feature_states.output_sha256`，integrated 路径逐项对账刚序列化 bytes、无 blocking gate① report、feature-state；
2. verifier 只从已验 raw bytes strict parse `geom`，并验证 `ref.schema_version == geom.schema_version`；禁止对现成 model 再 dump 来“重造原始 hash”；
3. verifier 按 artifact-contract/schema 矩阵处理 feature-state：`correction_b2_v1/correction_e4_orientation_v1` 必须有且 hash-bound；历史 v1/v2 `base_v2/migrated_v1` 允许无；v3 在任何 contract 下缺失都 BLOCK；返回只含 ref + immutable raw bytes 的 `VerifiedAcceptedCorrection`；
4. `derive_output_coordinate_contract(verified, geometry_snapshot_sha256=...)` 是真正纯函数：每次重算存在的 bytes hash、fresh parse geom/FeatureStatesArtifact，再做 `ensure_corrected_geometry`；绝不复用 mutable model；v1/v2 legacy 不读取缺失 feature-state；
5. schema v1/v2：只能派生 `world_legacy`，最终 North Axis 为 0；不得读取 legacy extra `north_axis`；
6. schema v3：只接受 `artifact_contract="correction_e4_orientation_v1"`，要求 `typed_north_axis` feature state 为 `populated`，且 `geom.north_axis` 恰一份、非空、strict 合法；派生 `relative_north_axis`；
7. v3 的 north_axis 缺失、B2 artifact 冒充 E4、feature-state 不符、artifact/schema/digest 不符全部硬失败，不回落 World；
8. 未知 schema 版本硬失败；integrated/stepwise 最终都只能把 verified bundle交给同一 derive。

历史 standalone 唯一工厂：

```python
def legacy_contract_for_unversioned_intake(
    *, intake_output_sha256: Hex64
) -> OutputCoordinateContract:
    # source=LegacyStandaloneIntakeRef；只返回 world_legacy；
    # geometry_snapshot_sha256=None；无其他参数。
```

上述两个 API 共同构成 explicit dispatch 的唯一 owner：有 correction 身份必须走 derive；只有 §3.4 第 4 条的无版本历史文件可走 factory。全仓禁止重复写 `schema_version == "3"` 来决定坐标模式；其他模块只消费派生后的 `contract.mode`。

### 3.2bis orientation-enriched correction 的唯一生产路径

`bac689b` 的 B2 合同故意要求 `north_axis is None`，并把 `typed_north_axis` 固定为 `declared_unpopulated`。B-O 不得直接翻这个布尔或手改旧 output；新增一个**确定性 augment phase**，只丰富 metadata，不重抽/重写几何：

```python
class OrientationEnrichmentV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1"] = "1"
    base_correction_sha256: Hex64
    orientation_evidence_sha256: Hex64
    north_axis: NorthAxisEvidence

def finalize_orientation_enrichment(
    base: VerifiedAcceptedCorrection,
    enrichment: OrientationEnrichmentV1,
) -> FinalizeResult:
    # base 必须是 v3 + correction_b2_v1（或已 enriched 后显式 replacement）；
    # 从 base.raw_output_bytes fresh parse，只替换顶层 north_axis；
    # 用 CorrectedGeometryV3.model_validate fresh rebuild，不用 model_copy(update=...)；
    # 除 north_axis 外逐字段 canonical dump 与 geometry-coordinate digest 必须不变；
    # feature claims 仅 typed_north_axis: declared_unpopulated→populated，
    # 其余 claims/helper_versions 原样 carry forward并复验。
```

输入 `OrientationEnrichmentV1` 必须来自**恰一份 accepted orientation evidence**；零份、两份、hash 不一致或 evidence sanity/conflict 未闭合均 BLOCK。历史 attempt 可有多份，但同一时刻 manifest 只能有一个 current accepted correction 与一个被它绑定的 orientation evidence；“多份冲突”不把 append-only history 误判成冲突。

writer 合同冻结：

- `CorrectionTarget.phase_contract` 扩为 `"b2" | "e4_orientation"`；`b2` 继续强制 north_axis 空，`e4_orientation` 强制 v3、north_axis 非空且只允许上述 augment API；不得走全几何 LLM redraw；
- 新 attempt 仍落 `1_correction/attempts/NNN/`，`StageRecordV2.stage_version="3"`、`artifact_contract="correction_e4_orientation_v1"`；
- required/allowed artifact keys = `output/checks/audit/feature_states`；若 accepted orientation evidence 是独立 sidecar，则再以 `input_hashes["orientation_evidence"]` 绑定其 raw hash，不复制成第二权威；
- `input_hashes` 至少含 `base_correction` 与 `orientation_evidence`；accept 新 attempt 后按既有 DAG invalidate 2–5，使 geometry/specs/MEP/S5 都重新绑定新 correction digest；
- `derive_feature_state_claims`/`artifact_feature_state` 的允许矩阵加入 `correction_e4_orientation_v1`；typed north 必为 populated，其他 feature state 与 base 相等；
- 重复执行且 base/orientation hash 相同可复用现 accepted attempt；证据 hash 变化必须新建 append-only attempt，不原位改写。

验收：augment 前后 `footprints/cells/windows/facade_segments/corrections/conflicts/unsupported` 逐字段相等，kernel canonical coordinate snapshot hash 相等；唯一允许差异是 `north_axis`、对应 orientation audit、feature-state transition 与 artifact identity。

### 3.3 内存落点：AgentState，不进 IntakeOutput

`src/agent/state.py`：

```python
class AgentState(BaseModel):
    ...
    output_coordinate_contract: OutputCoordinateContract | None = None
    output_coordinate_context: OutputCoordinateValidationContext | None = None

class AgentStateUpdate(TypedDict, total=False):
    ...
    output_coordinate_contract: OutputCoordinateContract | None
    output_coordinate_context: OutputCoordinateValidationContext | None
```

- 不加入 `IntakeOutput`，所以 11 字段 wire 与历史 JSON byte shape 不变；
- `merge_config_state` 不合并合同/context；二者随 AgentState 单值传递，任何节点不得改写；context 持有已验 source bytes、IntakeOutput hash 与 snapshot，不把“verified=True”裸布尔当证明；
- graph intake seed 前必须已有合同：新 E4 run 缺合同硬失败；明确 legacy standalone IntakeOutput 由加载器生成 `world_legacy` 合同。

### 3.4 持久落点与加载优先级

为让 final gate 真能证明“顶点未被 E4 旋转/平移”，冻结 companion baseline：

```python
class CoordinateRecordV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    object_type: Literal["BuildingSurface:Detailed", "FenestrationSurface:Detailed"]
    name: str
    zone_or_parent: str
    vertices: tuple[tuple[FiniteFloat, FiniteFloat, FiniteFloat], ...]

class OutputCoordinateSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_schema_version: Literal["1"] = "1"
    quantization: Literal["geometry_specs_2dp"] = "geometry_specs_2dp"
    zone_names: tuple[str, ...]
    records: tuple[CoordinateRecordV1, ...]
```

snapshot 由 `serialize_geometry` 同源结构数据生成：名称排序、坐标按 specs 的 `:.2f` 数值规范化；不能反向解析自然语言 specs。surface/fenestration agents 的最终 ConfigState/IDF 必须与 snapshot 按对象名逐顶点相等。snapshot canonical JSON raw hash写入 contract 的 `geometry_snapshot_sha256`。

新文件名固定为 `output_coordinate_contract.json` 与 `output_coordinate_snapshot.json`：

- integrated：两文件落 `<run>/5_intakeoutput/`；
- stepwise accepted attempt：两文件落 `<run>/5_intakeoutput/attempts/NNN/`，accept 后可 promote 同内容到 stage root 仅作 convenience；
- organized run metadata：`<run>/_run/output_coordinate_contract.json` 是 accepted 合同的 convenience mirror；其内容必须与 accepted S5 attempt sidecar逐字节相同；
- flat `--intake-only`：与 `intake_output.json` 同目录并列。

stepwise 要把 sidecar 纳入 accepted identity。由 E4 在 B-M 既有 wire 上做向后兼容扩展：

```python
# 在 manifest.py 现有 Literal 定义中追加下列 member（不是运行时 `+=`）：
ArtifactKey = Literal[
    "output", "checks", "audit", "feature_states", "isolation_provenance",
    "output_coordinate_contract", "output_coordinate_snapshot",
]
ArtifactContract = Literal[
    "migrated_v1", "base_v2", "reading_isolated_v2", "correction_b2_v1",
    "correction_e4_orientation_v1", "assembly_e4_v1",
]
_CONTRACT_REQUIRED_KEYS["correction_e4_orientation_v1"] = {
    "output", "checks", "audit", "feature_states"
}
_CONTRACT_ALLOWED_KEYS["correction_e4_orientation_v1"] = 同上
_CONTRACT_REQUIRED_KEYS["assembly_e4_v1"] = {
    "output", "checks", "audit", "output_coordinate_contract",
    "output_coordinate_snapshot",
}
_CONTRACT_ALLOWED_KEYS["assembly_e4_v1"] = 同上
```

新 orientation correction 与 S5/E4 attempt 分别必须使用上述两个新 contract；历史 `base_v2/migrated_v1` 仍可按 legacy 读取，绝不回写。每个 artifact hash 必须等于同 attempt sidecar raw bytes。B-M 仍是 manifest wire 机制 owner；本稿只登记两个新版本化 artifact contract，不改变旧 contract 的 required/allowed key 集。

加载 API：

```python
@dataclass(frozen=True)
class IntakeArtifactBundle:
    intake: IntakeOutput
    output_coordinates: OutputCoordinateContract
    coordinate_snapshot: OutputCoordinateSnapshotV1 | None
    validation_context: OutputCoordinateValidationContext

def load_intake_bundle(intake_path: Path, *, run_dir: Path | None = None) \
        -> IntakeArtifactBundle:
    ...
```

优先级与拒绝规则：

1. 有 V2 manifest 且 S5 accepted 为 `assembly_e4_v1`：只读 accepted attempt 两 sidecar，验全部 artifact hash、snapshot hash、correction ref、S5 input hash；root mirror 只比对，不作权威；
2. integrated/flat 有同目录两 sidecar：strict 读取，并对账 snapshot hash 与可用的 correction artifact/digest；
3. 无 sidecar但能看到 v3 correction/run metadata：**硬失败**，禁止静默当 legacy；
4. 无 sidecar且无任何 correction/v3/E4 身份的历史 11 字段 IntakeOutput：以 IntakeOutput raw-bytes hash 构造 `LegacyStandaloneIntakeRef` + `world_legacy` 合同，bundle 的 snapshot=None；这是唯一 absence→legacy 兼容口，绝不伪造 correction schema/digest；
5. sidecar 未知版本、extra 字段、hash 漂移、mode/schema 混搭均硬失败；
6. bundle 的 `intake` 必须从 context 保存的 exact raw IntakeOutput bytes fresh strict parse 得到；`_seed_config` 再从 raw bytes fresh parse，不信任可 mutation 的现成 model；
7. 旧 `load_intake_from()` 保留为只取 `.intake` 的 compatibility wrapper；所有会进入 downstream graph 的 CLI 改用 `load_intake_bundle()` 并把合同/context 放进 AgentState。

### 3.5 integrated/stepwise 同一 assembly API

新增：

```python
def assemble_intake_artifacts(
    *, zone_specs: str, surface_specs: str, fenestration_specs: str,
    mep: MepOutput, correction: VerifiedAcceptedCorrection,
    coordinate_snapshot: OutputCoordinateSnapshotV1,
) -> IntakeArtifactBundle:
    snapshot_bytes = canonical_json_bytes(coordinate_snapshot)
    contract = derive_output_coordinate_contract(
        correction, geometry_snapshot_sha256=sha256(snapshot_bytes)
    )
    intake = assemble_intake_output(..., mep=mep, output_coordinates=contract)
    return IntakeArtifactBundle(
        intake=intake, output_coordinates=contract,
        coordinate_snapshot=coordinate_snapshot,
        validation_context=context_from_exact_written_bytes(...),
    )
```

- `run_pipeline_artifacts()` 与 stepwise `_draw_assembly()` 共调它；
- 现 `run_pipeline()` 可保留返回 `bundle.intake` 的 compatibility wrapper，但 `intake_node` 主线必须调用 bundle 版本，避免丢合同；
- parity helper 固定为 `coordinate_semantic_projection(contract) = contract.model_dump(exclude={"source"})`；source identity 另走各路径 verifier，禁止用“为追求 byte 相等而抹掉 provenance”的方式合并二者；
- 两路径对同一 correction/MEP/snapshot 必须产出 byte-identical IntakeOutput 与 snapshot sidecar；contract sidecar 的 acceptance proof 天生不同（`integrated_gate1` vs `manifest`、run_id/attempt），故不要求整文件 bytes 相等，只要求去掉 `source` 后的 coordinate-semantic projection 逐字段相等；两侧 identity envelope 各自 hash-valid；
- S5 input hashes 必须登记 accepted correction output hash、accepted MEP output hash、geometry specs hash；禁止从 stage-root `4_mep/mep_output.json` 猜“最新”。

---

## 4. θ 唯一 owner、S4 占位与 S5 override

### 4.1 S4：MEP `north_axis` 只允许占位 0

`src/validator/checks/mep.py` 增永远 BLOCK 的 INVARIANT，例如 `mep.building_north_axis_placeholder`：

```python
value = validated_mep.building.north_axis
pass iff type(value) in numeric path and value == 0.0
```

- Pydantic 已先拒 NaN/越界；checker 再精确要求 `0.0`；
- `-0.0 == 0.0` 可接受，S5 重序列化为 correction θ 的规范浮点；
- LLM 给 90、270 或任意非零，S4 当前 draw 直接失败；不等 S5“纠正”；
- prompt 同步写“North Axis 必须为 0.0 compatibility placeholder”，但 prompt 只是辅助，checker 才是机制；
- v1/v2 MEP 同样只允许 0，避免 World 下写无效非零值制造 warning/假权威。

### 4.2 S5：无条件 override，不做 0-vs-θ 冲突比较

`assemble_intake_output(..., output_coordinates=contract)` 固定序：

1. 先断言 `mep.building.north_axis == 0.0`，S4 被绕过也挡；
2. `world_legacy`：最终仍写 0.0；
3. `relative_north_axis`：无条件把 `contract.north_axis_deg` 写入最终 Building；θ=0 也执行同一 override；
4. 用 `BuildingSchema.model_validate({...dump, "north_axis": theta})` 重建 fresh 对象，禁止 `model_copy(update=...)` 绕 validator；
5. 不修改传入 `mep`，保证纯装配与 attempt 可复算；
6. final IntakeOutput 再 strict round-trip，并断言 `intake.building.north_axis == contract.north_axis_deg`。

**冲突豁免**：MEP placeholder 0 与 correction θ（包括 90/270）不参与值冲突比较；0 没有证据权威，故 `0 != θ` 不是 conflict。

**真正硬冲突只有**：

- accepted correction orientation 缺失或 feature-state 非 populated；
- 同一 run 出现多份 current accepted correction identity；
- correction ref 的 schema/digest/attempt/run_id/artifact contract 不匹配；
- θ 或 typed evidence 非法；
- integrated 与 stepwise 对同输入派生出不同合同/IntakeOutput；
- MEP placeholder 非零；
- sidecar 与 final Building 值不一致。

### 4.3 防回写门

下游任何 node/tool 不得更新 Building.North Axis。`BuildingTool.update`/MCP API 若在 graph 内仍可达，E4 合同下对 `north_axis` 更新必须拒绝；最终 pre-export gate 再验证一次。这样唯一 owner 不依赖“目前 prompt 没调用它”。

---

## 5. GlobalGeometryRules 与分派

### 5.1 schema 补齐 A4/A5

`GlobalGeometryRulesSchema` 增：

```python
daylighting_reference_point_coordinate_system: str = Field(
    "Relative", alias="Daylighting Reference Point Coordinate System"
)
rectangular_surface_coordinate_system: str = Field(
    "Relative", alias="Rectangular Surface Coordinate System"
)
```

两字段 validator 复用 `Relative|World` choice；`SettingsConverter._global_geometry_rules_apply()` 显式写 A3/A4/A5。注意：A4/A5 现 IDD 默认就是 Relative，但 E4 不能依赖默认；legacy contract 显式写 World/Relative/Relative，精确保留当前 A3=World、A4/A5=Relative 的行为并让模式可从导出 IDF 自证。

### 5.2 单一应用函数

```python
def apply_output_coordinate_contract(
    config: ConfigState, contract: OutputCoordinateContract
) -> ConfigState:
    # deep-copy；设置 GGR 三字段；设置/复验 Building North Axis；
    # relative 模式将所有 Zone frame 四字段写 0；legacy 不改已有 Zone frame；
    # 返回 fresh validated ConfigState，不原位修改输入。
```

调用点：

1. `_seed_config()`：Building/Site 写入后立即设置 GGR 和 Building θ；此时 Zone 为空；
2. `zone_agent()` 尾部：Zone 创建完成后统一归零；
3. `cross_ref_foundations_node` 前/内：并行 merge 后复验并幂等应用；
4. `validate_node()`：引用检查之外加入坐标合同检查；
5. `simulate_node()` 调 WorkflowTool 前：只复验，不“静默修好”；
6. `WorkflowTool` 在 YAML export 前与 ConverterManager convert 后各一次 gate。

原则：早期 writer 后可 deterministic normalize；批准/导出边界只 validate、发现漂移即失败，不在最后一秒掩盖越权写入。

合同必须显式穿过现有只收 `ConfigState` 的 API，禁止实现者从 GGR/Building 值反推：

```python
make_zone_tools(config, contract)
ZoneTool(config, coordinate_policy=policy_from(contract))
WorkflowTool(config, output_coordinates=contract, validation_context=context)
```

`zone_agent` 从 AgentState 取合同后传给 tool factory；`simulate_node` 同时传 contract/context 给 WorkflowTool。standalone MCP 没有 AgentState 时使用显式 `legacy_unbound` policy：只允许/导出 A3=World、Building North Axis=0 的 legacy 配置；若 ConfigState 已是 Relative 却没合同/context，export/simulate 硬失败，不能靠字段值“认领 E4”。

### 5.3 explicit dispatch 表

| correction/输入身份 | sidecar | 合同 mode | GGR A3/A4/A5 | Zone frame | Building North Axis |
|---|---|---|---|---|---|
| accepted v3 + populated orientation | 必须有 | `relative_north_axis` | Relative/Relative/Relative | 四字段全 0 | correction θ |
| v3 但 orientation 缺失 | 不得生成 | BLOCK | — | — | — |
| v3 但 sidecar 丢失/坏 hash | 缺/坏 | BLOCK | — | — | — |
| v1/v2 accepted legacy | 可显式生成 | `world_legacy` | World/Relative/Relative | 保持旧行为 | 0 placeholder |
| standalone 历史 11 字段、无 v3 身份 | 无 | `world_legacy` | World/Relative/Relative | 保持旧行为 | 0 placeholder |
| 任意 schema、仅因 θ!=0 | 不适用 | **禁止判定** | — | — | — |

仓库守卫测试/静态 grep 要拒绝这些模式：`if north_axis`、`if theta`、`north_axis != 0` 决定 Relative、从 `BuildingSchema.north_axis` 反推 mode、按 provenance observed/assumed 决定 mode。

---

## 6. Zone Origin/Direction 归零迁移

### 6.1 为什么必须迁

现 serializer 把墙/板/窗顶点写成全楼建筑系绝对值，含高层真实 z；现 Zone prompt 又把高层层底写入 `z_origin`。在 World 下这些 origin 被 EP 忽略，所以历史上未暴露；切 Relative 后再保留非零 origin 会把同一顶点二次平移/旋转，造成几何漂移。归零是坐标迁移本体，不是格式清理。

### 6.2 施工步骤

1. `src/agent/geometry/specs.py` 按显式 contract/version 选文案：v3/E4 用 `building-axis coordinates; values are absolute within the project building frame`；v1/v2 保留现有 `world coordinates/absolute world coordinates` 原文与 bytes；两支顶点格式和数值都零变化。
2. Zone prompt 同样显式分支：Relative 版本要求四字段均 `0.0`，明确层底标高已经在 surface vertices 中；legacy 版本保留现 prompt/行为。prompt 选择读取 contract.mode，不读 θ/GGR 猜测。
3. `create_zone` docstring 同步，默认值保持 0；不要删除参数，以免扩大工具 breaking 面。
4. `zone_agent` 返回前调统一 normalizer，把 LLM 写出的任意 x/y/z/direction 全部覆写 0；记录 deterministic audit（zone name、before、after、contract mode），但不把 prompt 输出当 conflict。
5. Relative 模式下，`make_zone_tools(config, contract)` 把显式 policy 传入 ZoneTool/API，对后续 `update_zone(...origin/direction nonzero...)` 直接拒绝；legacy/standalone MCP 走显式 legacy policy 保留原行为，工具自身不得查看 GGR 猜 mode。
6. `validate_output_coordinate_contract(config, contract)` 遍历**全部** zones，按名字排序报告每个 offender；不得只查首区或集合均值。
7. YAML 前断言 `ConfigState` 四字段全 0；IDF 后用 eppy 按字段名断言每个 `ZONE` 对象四字段为 0。
8. EP run 后检查 ignored warning 不出现，并用 EIO 面积/体积/azimuth 证实没有双平移。

### 6.3 迁移兼容

- 不批量改历史 IDF/IntakeOutput/run artifact；
- 新 E4 Relative run 读取旧的非零 Zone tool 输出时在 zone-agent postprocess 归零并审计；
- 已经进入批准/导出阶段的非零值视为越权漂移，硬失败，不自动修；
- World legacy 仍保持旧 Zone frame 语义，避免 v1/v2 行为漂移；但 Building North Axis 固定占位 0。

### 6.4 Zone 验收

- 单层、多层、负坐标 footprint 各一例；高层 surface z 仍为真实 `[zf,zt]`，Zone z_origin=0；
- LLM 故意给 `(x,y,z,direction)=(10,-3,3.6,45)`，postprocess 后精确四零且 audit 有 before；
- postprocess 后再通过 tool/MCP 改非零，立即拒；
- merge/checkpoint pickle round-trip 后合同与四零不丢；
- final YAML、IDF、EIO 三层一致。

---

## 7. building-bound 坐标对象全量清单

### 7.1 分类原则

“building-bound”指应随 `Building.North Axis` 一起刚体旋转的坐标/宿主几何。闭世界审计范围精确为：所有受 Building/Zone/GGR frame 影响的几何字段、显式 true-north/site-world 几何方向字段，以及它们的宿主局部派生。`Site:Location` 等地理参考字段也进 exclusion registry 说明为何不受 θ 控制；不是把 IDD 中所有带 X/Y 或“angle”字样的 HVAC 参数误当建筑坐标。任何实际输出中的候选没有分类仍 fail closed。

### 7.2 EP 25.1 registry（`ep25.1-v1`）

| 类别 | EnergyPlus 对象/字段族 | E4 规则 | 当前仓库 producer |
|---|---|---|---|
| frame controller | `Building.North Axis` | Relative=θ；legacy=0 | 有：BuildingConverter |
| frame controller | `Zone.Direction of Relative North/X/Y/Z Origin` | Relative 四零 | 有：ZoneConverter |
| frame controller | `GlobalGeometryRules` A3/A4/A5 | E4=Relative/Relative/Relative；legacy=World/Relative/Relative | 有，但 A4/A5 待补 |
| detailed zone-bound | `BuildingSurface:Detailed` | 顶点建筑系值不改；由 A3+零 Zone frame+Building θ 旋转 | 有 |
| detailed zone-bound | `Wall:Detailed`、`RoofCeiling:Detailed`、`Floor:Detailed` | 同上 | 无；出现即 unsupported BLOCK，直至有 serializer/converter 测试 |
| detailed zone-bound | `FenestrationSurface:Detailed` | 同宿主 Zone frame；顶点值不改 | 有 |
| detailed zone-bound | `Shading:Zone:Detailed` | 同宿主 Zone frame | 无；出现即 BLOCK |
| building-origin bound | `Shading:Building:Detailed` | 坐标相对 building origin，随 Building North Axis 旋转 | 无；出现即 BLOCK |
| rectangular opaque | `Wall:Exterior`、`Wall:Adiabatic`、`Wall:Underground`、`Wall:Interzone`、`Roof`、`Ceiling:Adiabatic`、`Ceiling:Interzone`、`Floor:GroundContact`、`Floor:Adiabatic`、`Floor:Interzone` | 受 A5 控制；E4 A5=Relative，起点须与零 Zone frame 同约定 | 无；出现即 BLOCK |
| building rectangular shading | `Shading:Building` | building-bound，随建筑旋转 | 无；出现即 BLOCK |
| daylight coordinate | `Daylighting:ReferencePoint`、`Output:IlluminanceMap` | 受 A4 控制；E4 A4=Relative，坐标按所属 Zone 且 Zone frame 全零 | 无；出现即 BLOCK |
| host-local | `Window`、`Door`、`GlazedDoor`、`Window:Interzone`、`Door:Interzone`、`GlazedDoor:Interzone` | 起点相对 base surface；继承宿主，不单独做 world/relative 转换 | 无；出现须验证宿主链，否则 BLOCK |
| host-local | `Shading:Overhang`、`Shading:Overhang:Projection`、`Shading:Fin`、`Shading:Fin:Projection` | 由窗口/表面宿主与局部尺寸派生；继承宿主 | 无；出现须验证宿主链，否则 BLOCK |
| host-derived daylight | `DaylightingDevice:Tubular`、`DaylightingDevice:Shelf`、`DaylightingDevice:LightWell` | 通过表面/窗引用及局部长度关联；无独立 building-frame 顶点 | 无；出现须验证宿主链，否则 BLOCK |
| site-world exempt | `Shading:Site`、`Shading:Site:Detailed` | 固定在 facility world，不随 Building North Axis 旋转；不得被 E4 批量转成 Relative | 无；出现必须明确标为 site-world 并另测 |
| true-north parameter | `AirflowNetwork:SimulationControl.Azimuth Angle of Long Axis of Building` | 字段定义为从真北顺时针；不是 GGR-relative。未来若产出必须由 θ+建筑长轴关系显式派生 | 无；当前统一 unsupported BLOCK |
| conditional orientation | `Generator:PVWatts.Azimuth Angle` | `Array Geometry Type=TiltAzimuth` 时为 true-north/site-world；`Surface` 时继承宿主，不能按 object type 单一分类 | 无；当前统一 unsupported BLOCK，未来 registry 用 predicate 分支 |
| georeference exempt | `Site:Location.Latitude/Longitude/Time Zone/Elevation` | 定义场地地理位置，不是建筑系顶点，也不随 θ 数值改写 | 有；明确 exclusion，不进入 vertex rotation/zero-origin 门 |

说明：当前生产输出中受建筑 frame 影响的实际闭包只有 frame controllers + `BuildingSurface:Detailed` + `FenestrationSurface:Detailed`；另有已登记但不受 θ 改写的 `Site:Location` georeference。表中“无”的对象仍必须登记，因为它们是切坐标系时最容易漏掉的未来 producer；本批不实现它们，只保证“新增前先扩 registry/测试”。

### 7.3 怎么穷举，保证没漏

不是做一次人工 grep，而是建立可复跑的四层闭世界审计：

1. **IDD 层**：解析当前 `data/dependencies/Energy+.idd` 的 object block，主集合收集备注含 `GlobalGeometryRules coordinates`、`relative to Zone Origin`、`relative to building origin`、`rotate with BUILDING north axis`、`Daylighting Reference Point Coordinate System` 的对象；在 `Thermal Zones and Surfaces`/shading/daylighting 几何组内再收 `Vertex/Starting X/Y/Z`、Origin、Azimuth。禁止对全 IDD 裸扫所有 Azimuth 后假装表已穷举；跨组的 true-north/空间字段由 producer/runtime 集合触发，并必须进 rule 或 exclusion registry。
2. **schema/converter 层**：枚举 `ConfigState.model_fields` alias、`ConverterManager.converters`、各 validator schema 的 field alias 和 converter 的 `newidfobject/setattr` 写字段；坐标候选必须映射到 registry。新增 converter 或坐标 field 会让差集测试失败。
3. **producer 层**：`rg`/AST 检索 `Vertex_.*coordinate|vertices|Starting_[XYZ]|[XYZ]_Origin|North_Axis|Azimuth|Latitude|Longitude|Elevation` 及 raw IDF fragment 注入点；每个 writer 登记 route id、对象类型、字段 predicate、frame class、owner或 exclusion reason。grep 只作发现，registry completeness test 才是门。
4. **最终 IDF 层**：ConverterManager 完成后遍历 live eppy IDF 的实际非空 object/field；凡实际空间候选不在 rule/exclusion registry，或 rule 标 unsupported/host-unverified 而实际出现，pre-EP BLOCK。这样 AFN/PVWatts、动态工具、默认对象或未来 converter 不能绕过 Python schema 清点。

新增 `CoordinateObjectRule` registry 记录：`object_type / field_pattern / variant_predicate / frame_class / controlling_ggr_field / current_support / owner_route / idd_version`；同一 object 可按字段值分 variant。另有 `CoordinateExclusionRule{object_type, field_pattern, reason, idd_version}`，exclusion 必须有具体语义理由，不能用通配 `*` 消音。registry 常量与测试生成器放 `src/validator/output_coordinates.py`，业务应用留 `src/agent/output_coordinates.py`，避免 validator 反向 import agent graph。

验收附带两份机器证据：

- `output_coordinate_audit.json`：实际对象按 registry 分类、对象数、offenders、GGR/Building/Zone snapshot；
- 测试日志中的 IDD candidate set 与 registry set 差集必须双空（候选无漏登、registry 无幽灵对象）。

### 7.4 audit 类型、时序、落点与 hash owner

审计拆两层，禁止把下游才知道的 IDF 事实伪装成 S5 已知：

```python
class AssemblyCoordinateAuditV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1"] = "1"
    correction_output_sha256: Hex64
    contract_sha256: Hex64
    snapshot_sha256: Hex64
    mep_placeholder_north_axis: FiniteFloat  # validator: == 0.0
    final_building_north_axis: FiniteFloat
    zone_origin_policy: Literal["preserve_legacy", "all_zero"]

class ZoneFrameNormalizationEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    zone_name: str
    before: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]
    after: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat]
    # validator: after == (0.0, 0.0, 0.0, 0.0)

class ExportCoordinateAuditV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1"] = "1"
    contract_sha256: Hex64
    snapshot_sha256: Hex64 | None
    yaml_sha256: Hex64
    idf_sha256: Hex64
    registry_version: str
    registry_candidate_sha256: Hex64
    config_counts: tuple[tuple[str, int], ...]  # object type 排序后的 immutable pairs
    idf_counts: tuple[tuple[str, int], ...]
    zone_normalizations: tuple[ZoneFrameNormalizationEntryV1, ...]
    offenders: tuple[OutputCoordinateIssue, ...]
```

- S5 accepted attempt 的 `audit.json` 是 `AssemblyCoordinateAuditV1`，由 `assembly_e4_v1.artifact_hashes["audit"]` 绑定；stage-root mirror 只作 convenience。
- Zone postprocess 把 normalization entry 作为 immutable tuple 随 AgentState 传到 export；legacy 不造虚假“归零”entry。
- WorkflowTool convert/gate 完成后原子写 `<output_dir>/output_coordinate_audit.json`，内容绑定实际 YAML/IDF raw hash；这是 downstream export audit，不回填 S5 attempt。
- simulate 后另写 `<ep_run_dir>/output_coordinate_ep_audit.json`，绑定 IDF/EIO/ERR raw hash与 §9 五断言结果；export-only 不伪造 EIO/ERR。
- `validate_case`/replay 现场重算上述 raw hashes与 registry candidate hash；audit 被篡改、IDF 被替换或 candidate set 漂移均 finding/BLOCK。audit 是可验证证据，不反过来成为合同 mode/θ owner。
- `OutputCoordinateIssue` 本身也须 strict+frozen，所有 nested collection 用 tuple/frozen record；不得在 frozen 外壳里藏可 mutation dict/list。

---

## 8. 合同 gate 与下游接线

### 8.1 `validate_output_coordinate_contract`

放在 `src/validator/output_coordinates.py`，返回结构化 issues，不写盘：

```python
@dataclass(frozen=True)
class OutputCoordinateValidationContext:
    raw_intake_output_bytes: bytes
    verified_correction: VerifiedAcceptedCorrection | None
    raw_snapshot_bytes: bytes | None
    # accepted/integrated 新 run：verified_correction + snapshot 都必有；
    # historical standalone：二者都 None；每次从 raw intake bytes fresh strict parse，
    # 其 hash 必须匹配 LegacyStandaloneIntakeRef。不得只存可伪造的 hash 字符串。

def validate_output_coordinate_contract(
    config: ConfigState,
    contract: OutputCoordinateContract,
    context: OutputCoordinateValidationContext,
    *, idf: IDF | None = None,
) -> list[OutputCoordinateIssue]:
    ...
```

context 由 `load_intake_bundle`/`run_pipeline_artifacts` 在同一 hash-chain 边界用**最终实际写盘 bytes**构造；validator 每次重算 IntakeOutput/source/snapshot raw hash，并从 raw IntakeOutput bytes fresh strict parse。stepwise 还对账 S5 `output_hash/artifact_hashes["output"]`；调用者不能同时伪造“hash + parsed model”。它不从 GGR 反推 mode，也不接受调用者声称“already_verified”的布尔。

Relative 至少检查：

- contract strict；source 是 accepted correction 时用 context raw bytes 重验 identity，historical standalone 时 IntakeOutput hash 必须匹配；
- ConfigState Building 存在且 north_axis 与合同精确相等；
- GGR A3/A4/A5 三个 `Relative`；
- 全部 Zone frame 四零；
- surface/fenestration vertices 有限；snapshot bytes hash 等于 contract，ConfigState 或 IDF 的对象名/宿主/逐顶点值与 canonical snapshot 相等，证明未被 E4 旋转/平移；
- registry 对实际 object types 完整，unsupported building-bound 对象为零；
- IDF 阶段重复上述字段名检查，不依赖 YAML serializer。

新 accepted legacy 也携带 snapshot并做顶点对账；historical standalone 因无可信 pre-E4 baseline，只检查 IntakeOutput hash、GGR A3=World/A4/A5=Relative、Building North Axis=0，不声称能证明 vertex drift；不对历史 Zone origin 做新限制。

两阶段能力边界：YAML 前检查 source/intake/snapshot hash + ConfigState；ConverterManager 后检查 live IDF object/字段 + 同一 snapshot。EP run 后只检查 EIO/ERR 行为，不拿 warning 反推合同身份。

issue code 固定词汇：`CONTRACT_IDENTITY`、`MODE_SCHEMA_MISMATCH`、`BUILDING_NORTH_AXIS`、`GGR_COORDINATE_SYSTEM`、`ZONE_FRAME_NONZERO`、`VERTEX_FRAME_DRIFT`、`UNCLASSIFIED_COORDINATE_OBJECT`、`UNSUPPORTED_COORDINATE_OBJECT`。

### 8.2 graph/CLI 消费合同

- `intake_node`：接收/生成 `IntakeArtifactBundle`，调用 `_seed_config(state, bundle)`；没有合同不得进入 zone/material/schedule fan-out；
- `_seed_config`：不再只写 building/site，必须一次写 building/site/GGR/contract；
- graph node 全部只读 `state.output_coordinate_contract`；
- `run_full_pipeline.py --intake-from` 与 `run_stage.py _flow_ep` 使用 `load_intake_bundle`；
- `--reading-from` integrated path由 `run_pipeline_artifacts` 返回 bundle；
- `--no-simulate` 与真实 simulate 共用相同 pre-export/post-convert gate；
- repair loop 回到 intake 时保留同一 correction identity；若重新跑 correction，旧合同必须失效并重派生，不能沿用旧 θ。

### 8.3 B-O 施工消费清单（本稿不替它动代码）

B-O 按顺序消费本文：

1. orientation 产物进入新的 v3 correction attempt，`typed_north_axis` feature-state=populated；
2. 建 `output_coordinates.py` 类型/derive/sidecar/registry；
3. S4 placeholder gate；
4. S5 bundle assembly + θ override + accepted sidecar；
5. AgentState/loader/CLI 携带合同；
6. GGR A4/A5 schema/converter；
7. seed/Zone postprocess/final gate；
8. IDF runtime audit；
9. 单测→路径 parity→EP 五条 E2E。

B-O 不得简化为“给 `Building.north_axis` 赋值”或“只改 prompt”；缺 sidecar、Zone 迁移、对象审计、legacy 分派、两路径 parity 任一项都算未完成。

---

## 9. EP 端到端验收（逐条对齐探针五条）

### 9.1 四变体与前置断言

同一 synthetic fixture 生成：

- `world_000`：v1/v2 legacy 合同、World/Relative/Relative、Building=0，并**保留 canonical probe 的旧 Zone origins**；跑 EP 前断言至少一个 Zone 的 origin/direction 非零（例如探针既有 `Y Origin=4.85`），使 ignored warning 与迁移前状态确定可触发；
- `rel_000`：v3 E4 合同、Relative/Relative/Relative、Building=0；
- `rel_090`：同上、Building=90；
- `rel_270`：同上、Building=270。

四者保持同名 zone/surface/fenestration 与逐值相同建筑系顶点；区别仅为 world anchor 保留迁移前非零 Zone frame，三个 Relative 变体四字段全零。运行 EnergyPlus 25.1.0，动态解析 EIO 表头，不硬编码列号。若另加全零 legacy synthetic fixture，它不得承担“World warning 必命中 1”的断言；该断言只由上述 canonical anchor 承担。

### 9.2 五条必过断言

1. **零角几何等价**：`rel_000` 与 `world_000` 的 HeatTransfer Surface 名称集合相等，每个同名面的 Azimuth 在 `1e-6°` 内相等。
2. **90° 精确偏转**：每面 `az(rel_090) == (az(rel_000)+90) mod 360`，环形角差 `<=1e-3°`。
3. **270° 精确偏转**：每面 `az(rel_270) == (az(rel_000)+270) mod 360`，环形角差 `<=1e-3°`。
4. **面积/体积不变**：四变体 Zone 名集合相等；world 分别对三个 relative 的每区 Floor Area、Volume 在 `1e-6 m²/m³` 内相等。canonical probe fixture 同时锁定 14 区×3=42 对；窗仍通过 HeatTransfer Surface 的 `Surface Class=Window` 覆盖。
5. **warning 行为**：三个 Relative err 中精确 warning 子串 `Any non-zero Building/Zone North Axes or non-zero Zone Origins are ignored` 命中 0；World 基线命中 1，并保留配套 potential mismatch。尤其 `rel_000` 也必须无 warning，证明分支不是 θ!=0 猜测。

额外门：四变体 surface/zone 行数与名称集合一致；EP `eplusout.end` completed，0 severe；不要求总 warning=0，只排除坐标系 warning，避免把 Timestep/SizingPeriod/GroundTemperature 共性 warning 误当失败。

### 9.3 探针 fixture 与泛化 fixture

- 保留 2026-07-10 探针的 114 面/14 区作为回归 anchor；
- 再加最小两层 fixture，专门验证高层 surface z 不变且 Zone z_origin=0；
- 再加带负 x/y 坐标的 L 形 v3 fixture，证明“building-axis absolute values”不要求所有顶点从 0 开始；
- 当前无 shading/daylighting producer，另用手工 eppy object fixture 验 registry：`Shading:Building:Detailed`/`Daylighting:ReferencePoint` 在 unsupported 状态 BLOCK，`Shading:Site:Detailed` 被明确归类为 world-exempt而非误旋转。

---

## 10. 测试族清单

### 10.1 类型与分派（建议 `tests/test_output_coordinate_contract.py`）

- strict wire：缺字段/extra/坏 digest/NaN/inf/θ=360/负角拒；
- mode 组合矩阵：Relative+v1、World+v3、Relative+preserve origins、legacy+orientation metadata 全拒；
- v3 θ=0 observed 与 assumed 都派生 Relative，provenance 保持可区分；
- v1/v2 即使 legacy extra 或 Building 非零也只能派生 World/0，不读 extra；
- 未知 schema、v3 north_axis None、feature-state 未 populated、digest/run_id/attempt 漂移拒；
- 禁用模式哨兵：θ=0/90 都由同一 mode 字段分派，不走 truthiness。

### 10.2 S4/S5 owner（扩 `tests/test_checks_mep_assembly.py`、`tests/test_intakeoutput_assembly.py`）

- MEP 0 pass，90/270/极小非零 fail；
- S5 θ=0/90/270 无条件 override，输入 MepOutput 不被 mutation；
- MEP 0 vs θ=90 明确无 conflict；MEP 非零即使等于 θ 也 fail（无权威不能“碰巧相等”）；
- `model_copy` 注入坏 angle 后 strict rebuild 拒；
- final IntakeOutput building 与 contract 精确相等；construction backstop 行为不变。

### 10.3 GGR/Zone/config（建议 `tests/test_output_coordinate_application.py`）

- A3/A4/A5 schema round-trip、YAML aliases、SettingsConverter IDF 三字段；锁定 legacy=World/Relative/Relative、E4=Relative/Relative/Relative；
- `_seed_config` Relative 与 legacy 两表；parallel merge 后不退回默认 World；
- Zone postprocess 多区全量归零、幂等、audit before/after；
- late tool update nonzero 拒；final validator 能列出所有 offender；
- high-floor surface z 保持，Zone z_origin 不承载层高；
- checkpoint pickle、repair loop、ConfigState deep copy 不丢合同。

### 10.4 accepted identity/sidecar（扩 manifest/stage runner 测试）

- S5 `assembly_e4_v1` 五个 required artifact hash 逐名齐全：`output/checks/audit/output_coordinate_contract/output_coordinate_snapshot`，output hash 不变式继续成立；
- accepted 001→blocked 002：loader 仍只读 001 contract；root mirror 被 002 污染也不影响权威且验证报漂移；
- 篡改 contract sidecar/output/correction output/manifest 任一处均断链；
- 有 v3 correction 无 sidecar拒；纯历史 11 字段无 metadata才生成 legacy；
- integrated_gate1 ref 与 manifest ref 对同 correction bytes 派生合同的 coordinate-semantic projection 相等；identity/source 字段按各自路径不同且各自验证。

### 10.5 building-bound registry（建议 `tests/test_output_coordinate_registry.py`）

- IDD candidate set − registry set = ∅，registry set − IDD/显式 host-local set = ∅；
- ConfigState/converter/producer route 差集双空；
- 当前 production fixture 实际只出现受支持对象；
- 注入未知 coordinate object、Wall:Detailed、Shading:Zone:Detailed、Daylighting:ReferencePoint 各自 BLOCK；
- `Shading:Site:Detailed` 明确 world-exempt，不被 Zone zero 检查误判；
- host-local window/door 无宿主、跨宿主 frame 时 BLOCK。

### 10.6 路径 parity（扩 pipeline/runner/flow 测试）

- integrated 与 stepwise 同 correction/Mep/specs → IntakeOutput bytes、snapshot bytes、contract coordinate-semantic projection、GGR、Zone snapshots 相等；不误要求 acceptance proof bytes 相等；
- `--reading-from`、`--intake-from`、`run_stage flow`、export-only、simulate 均进入同 gate；
- standalone historical intake 只走 World；standalone E4 bundle 丢 sidecar fail closed；
- retry 后 correction digest 变化使旧 S5/contract invalidated。

### 10.7 EP E2E（建议 `tests/test_e4_relative_north_axis_e2e.py`，按环境 marker）

- §9 五条逐条独立 test id，失败能直接定位；
- EIO 表头动态定位，按 Surface/Zone Name join；
- 角度用 circular difference，面积/体积用独立命名容差；
- 精确 warning substring；Relative θ=0 单独锁定；
- 114/14 anchor + 两层迁移 fixture；
- 无 EnergyPlus 环境时按既有 EP integration marker skip，不得 xfail 掩盖。

### 10.8 回归纪律

- v1/v2 legacy geometry/specs/audit 语义不变；旧 IntakeOutput 11 字段 byte shape 不变；
- 现有 tests 全绿，9 个 strict xfail 数量与 reason 不变；
- 零 golden 修改，零探针基线重录；
- 新容差仅用 `e4_azimuth_zero_tol_deg=1e-6`、`e4_azimuth_rotation_tol_deg=1e-3`、`e4_area_volume_tol=1e-6`，不得复用几何 min-edge/snap 容差；配置/A0 同步登记。

---

## 11. 施工顺序与逐步放行门

1. strict contract/ref/bundle 类型 + derive 单测；
2. accepted identity 与 `assembly_e4_v1` sidecar writer/loader；
3. S4 placeholder gate + S5 fresh Building override；
4. AgentState、intake node、CLI bundle 贯穿；
5. GGR A4/A5 schema/converter + seed application；
6. Zone prompt/tool 文案 + postprocess + late-write gate；
7. registry/IDD completeness + ConfigState/IDF validator；
8. integrated/stepwise parity；
9. EP 四变体五断言；
10. 全量回归与 zero-golden 对账。

每步先跑本节对应小测试，再跑全量；第 2、4、7、9 步各保留独立 diff/测试记录供复核。任何一步不得用 prompt 替代代码 invariant，也不得为让 EP 通过而直接旋转顶点。

---

## 12. 完成定义（DoD）

B-O 只有同时满足以下条件才可声明 E4 完成：

- `OutputCoordinateContract` 已作为 strict、hash-bound 内部 artifact 落盘且不扩 11 字段；
- v3 θ=0/90/270 都显式派生 Relative，v1/v2 明确 World；仓库无按 θ 猜分支；
- MEP 只产 0 placeholder，S5 从 accepted correction 无条件 override；
- ConfigState/YAML/IDF 的 GGR A3/A4/A5、Building θ、全部 Zone frame 三层一致；
- building-bound registry 的 IDD/schema/converter/runtime 差集双空；
- integrated/stepwise/CLI 路径 parity 全过；
- EP 五条全过，ignored warning 在全部 Relative 变体为 0；
- v1/v2 与 11-field wire 回归通过，零 golden 改动；
- 执行简报逐项列出本稿 §10 test family 的结果和 §7 audit artifact。

---

## 13. 开放问题：无

上位设计已裁定 Relative 路线、Zone 全零、θ 唯一 owner、MEP 0 占位豁免、v1/v2 World legacy 与显式合同分派；本文没有需要用户再次拍板的实现二选一。
