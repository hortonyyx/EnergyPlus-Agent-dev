# C2 B2b 细稿（2026-07-12）：E3' envelope 权威矩阵安全变形批

> **状态**：待 sol 最高档 Fable 交叉审；本稿只放行 B2b 施工，不放行 B3、Vg、B4、B5 或 E4 的顺带施工。基座固定为 `bac689b`。施工依赖固定为 **B2 已合入且 B3 覆盖门已合入并复核**。
>
> **唯一目标**：把 schema v3 非矩形 `Floor.footprint` 的 envelope reconcile 从“整轴 unsupported”窄化为有证据、可回滚的逐共享轴原子变形；保持 v1/v2 legacy 行为不变。
>
> **施工纪律**：本稿是累计式、自包含施工合同。签名、wire 形状、门 id、审计形状和断言均以本稿为准；不得用“沿用旧稿未变”代替实现说明。本文不要求本轮修改任何代码或测试。

---

## 0. 权威输入、开工门与结论

权威顺序如下：

1. `c2_full_unlock_design.md` v2.2 的 §E3'、B2b 批次行、验收三层和 C-01..C-05 开工门；
2. `c2_b2_detail_spec.md` v6 定稿及其已施工的 schema v3、per-floor footprint、单一 finalize、身份快照与 feature-state 合同；
3. 基座 `bac689b` 的 `src/agent/correction/{deterministic,envelope,footprint,finalize,parse,schema}.py`；
4. B3 已复核后的覆盖门公开合同（§2.3），B2b 只调用，不复制其实现。

开工前必须机械断言：

```python
assert correction_target("orthogonal_polygon").schema_version == "3"
assert hasattr(load_core_tolerances(), "coverage_area_tol_m2")       # B3 已落
assert hasattr(load_core_tolerances(), "envelope_axis_attach_tol_m")
assert hasattr(load_core_tolerances(), "envelope_endpoint_match_tol_m")
assert hasattr(load_core_tolerances(), "envelope_candidate_agreement_tol_m")
assert "correction.coverage" in {f.check_id for f in validate_corrected_geometry(v3_fixture)}
```

若 B3 尚未提供 `coverage_area_tol_m2` 与 `correction.coverage` 的面积守恒语义，B2b **不得以现有 `_AREA_TOL` 或任何临时常数开工**。

本批结论：

- v1 矩形与 v2 legacy（含 v2+polygon）仍走原 legacy 分支；
- v3 矩形和 v3 非矩形统一走同一原子事务，禁止再保留“矩形直接改、非矩形一律 unsupported”的双实现；
- overall facade 证据只能移动对应投影轴的全楼外包边；明确翼分界端点证据只能移动该立面的 world-along 共享轴；任何证据都不得据正投影猜测 cross-axis/notch depth；
- 事务边界是：**全部层的 rings + 所有受影响 cells + 所有 windows + 派生 bbox + 审计**。候选副本通过全部硬门后一次提交；任一门失败整事务回滚并记一条 conflict；
- B2b 阶段不拥有 `FacadeSegment` 的生成与稳定 id 重映射。输入若已填充 `facade_segments` 或任一窗已有 `facade_segment_id`，变形整体拒绝，不能留下 stale ref。

C-01/C-02 属 E4-output-contract，C-03/C-04 属 B-M/Vg/Va，C-05 属知识表 loader；B2b 不消费这些后批合同，也不得借本批修改真北、view manifest、applicability 或知识表。

---

## 1. 范围与非目标

### 1.1 In

1. `envelope.py` 增明确翼分界端点证据的严格解析，以及 overall/endpoint 到变形 intent 的确定性解析；
2. `deterministic.py` 以共享轴/vertex graph 生成变形计划，在深拷贝候选上同步移动 ring、cell 和需要移动的 window span 端点；
3. v3 envelope reconcile 改为候选副本事务，包含前置检查、B3 coverage、共享边、窗宿主、引用、ring/final validator 硬门与回滚；
4. 新增三个 B2b 专用线性容差，进入 `correction.yaml`、`CoreTolerances` 和 A0；
5. 保持 B2 `finalize_correction_draw(...)` 公共签名、身份快照和双路径共用关系；
6. 新增合成 L/U、跨层、故障注入、legacy 与两个原拒绝分支的回归测试族。

### 1.2 Out

- 不改 schema v3 wire，不新增 `CorrectedGeometryV4`；
- 不实现或复制 B3 coverage 算法；
- 不生成 `facade_segments`，不定义 Vg segment id，不实现 B5 窗段 resolver；
- 不改变 topology/凹凸关系，不增删 cell，不合并/拆分房间，不加洞；
- 不从 facade 证据修改 cross-axis/notch depth；
- 不改 window z、north_axis、判卷、gt、render、EnergyPlus 出口或 golden；
- 不用 cells 反推权威 footprint；`Floor.footprint` 仍是唯一 owner。

### 1.3 解锁边界

当前 `_apply_envelope_reconcile` 有两个重要拒绝分支：

1. **legacy v2+polygon**：拒绝 bbox-only 移动，因为 polygon vertices 才是权威；本批原文、分类和返回几何全部维持；
2. **v3 非矩形 ring**：当前一律报“vertex-level deformation belongs to B2b”；本批只删除这个 blanket reject，改由 §5–§7 的证据与事务硬门决定接受或拒绝。

第二条不是“所有非矩形都自动可动”。没有可执行证据、共享轴不唯一、跨轴、segment 已填充、窗口宿主不唯一、任一硬门失败时仍安全拒绝。F1 教训继续成立：每个安全拒绝必须有独立测试锁，不能因 happy path 变绿而删除 fail-closed 分支。

---

## 2. 既有数据合同与依赖接口

### 2.1 B2 已提供、B2b 直接消费的形状

以下是 B2b 所需的最小完整形状；字段名不得另造别名：

```python
class FootprintRing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vertices: list[tuple[FiniteFloat, FiniteFloat]]  # >=4；final 为 open CCW

class CellV3(Cell):
    model_config = ConfigDict(extra="forbid")
    # id, role, x=[min,max], y=[min,max], polygon: list[list[float]] | None

class FloorV3(Floor):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    z_floor: float
    ceiling_height: float
    footprint: FootprintRing
    cells: list[CellV3]

class WindowV3(Window):
    model_config = ConfigDict(extra="forbid")
    # id, floor(display), facade, span=[lo,hi], z=[sill,head], room
    floor_id: str
    facade_segment_id: str | None = None
    provenance: dict[str, FieldProvenance] | None = None

class CorrectedGeometryV3(CorrectedGeometry):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["3"]
    footprint_x: list[float]
    footprint_y: list[float]
    floors: list[FloorV3]
    windows: list[WindowV3]
    facade_segments: list[FacadeSegment]
    north_axis: NorthAxisEvidence | None
    corrections: list[dict]
    conflicts: list[dict]
    unsupported: list[dict]
```

既有函数签名保持：

```python
def floor_footprint(geom, floor) -> list[list[float]]: ...
def footprint_bbox(geom, floor=None) -> tuple[tuple[float, float], tuple[float, float]]: ...
def floor_key(geom, floor) -> str: ...
def floor_footprint_fingerprint(geom, floor) -> str: ...
def ensure_corrected_geometry(value: dict | CorrectedGeometry) -> CorrectedGeometry: ...
def validate_final_corrected_geometry(geom: CorrectedGeometry) -> CorrectedGeometry: ...

def finalize_correction_draw(
    geom_or_payload,
    *,
    vector_dir: Path,
    tol: CoreTolerances | None = None,
    target: CorrectionTarget,
) -> FinalizeResult: ...
```

B2b 不在 `finalize.py` 增第二条入口；pipeline 与 stepwise 仍只调这一函数。

### 2.2 E3' 权威矩阵的可执行解释

| claim | 可动作 | 禁止动作 |
|---|---|---|
| topology、凹凸、边接续 | 无；只能作为前后不变量 | 增删 turn、改邻接、加洞、拆/并 cell |
| cross-axis / notch depth | 仅平面尺寸链可定；B2b facade 路径不产生 intent | 由立面 overall/segment 尺寸推断或移动 |
| overall x bounds | 仅 North/South facade 的 accepted overall evidence 可产生 `axis="x", side=lo/hi` | 移 y 内轴或任意 notch 轴 |
| overall y bounds | 仅 East/West facade 的 accepted overall evidence 可产生 `axis="y", side=lo/hi` | 移 x 内轴或任意 notch 轴 |
| segment along endpoint | 仅 §4.2 的机器可判 `wing_break` 标注，可移动该 facade 的 world-along 共享轴 | 通过 note/OCR 模糊词、窗边、普通分段尺寸猜翼分界 |
| 同 claim 高权威冲突 | 写 conflict，不生成 intent | 任选赢家或平均 |

“逐边”在实现中指逐个 `EnvelopeMoveIntent` 生成共享轴 component；“原子”指所有 actionable intents 共用一个提交点，不是每条边各自提交。

### 2.3 B3 coverage 门接口（只引用，不复制）

B2b 只依赖以下公开契约：

```python
CoverageGateId = Literal["correction.coverage"]

def check_coverage(
    geom: CorrectedGeometry,
) -> list[GeometryFinding]: ...
```

- **门 id**：`correction.coverage`；
- **语义**：对每层，以该层权威 `Floor.footprint` 为域，按 B3 的 `coverage_area_tol_m2` 判 cells 是否面积守恒且无超容差 hole/overlap/outside；
- **B2b 用法**：候选变形后调用一次，任一该 id finding 的 `ok is False` 即回滚；
- **ownership**：`coverage_area_tol_m2`、面积计算、证据字段和数值舍入口径全部由 B3 拥有。B2b 不复制公式、不定义替代 helper、不以 `min_edge_length_m` 代面积容差。

---

## 3. 新内部类型与精确签名

以下类型均为内部 Python dataclass/type alias，不进入 correction schema v3 wire。

```python
from dataclasses import dataclass
from typing import Callable, Literal
from src.agent.reading.constants import DIMCHAIN_CLOSE_TOL_M

EnvelopeClaimKind = Literal["overall_bound", "wing_break_endpoint"]
EnvelopeAxis = Literal["x", "y"]
EnvelopeSide = Literal["lo", "hi", "internal"]
ResolutionStatus = Literal["accepted", "skipped", "conflict"]

@dataclass(frozen=True)
class WingBoundaryEvidence:
    facade: Literal["North", "South", "East", "West"]
    world_axis: EnvelopeAxis
    world_value: float
    view: str
    source_id: str
    chain_id: str
    order: int
    boundary_ref: str
    boundary_endpoint: Literal["from", "to"]
    frame_transform_hash: str

@dataclass(frozen=True)
class EnvelopeEndpointResolution:
    status: ResolutionStatus
    evidence: WingBoundaryEvidence | None
    corroborating_sources: tuple[str, ...] = ()
    candidates: tuple[WingBoundaryEvidence, ...] = ()
    reason: str | None = None

@dataclass(frozen=True)
class EnvelopeMoveIntent:
    intent_id: str                    # canonical SHA-256；来源+claim+axis+old/new
    claim_kind: EnvelopeClaimKind
    axis: EnvelopeAxis                # 被替换坐标；x 表示移动 constant-x shared axis
    side: EnvelopeSide
    old_value: float
    new_value: float
    source_facade: Literal["North", "South", "East", "West"]
    source_ids: tuple[str, ...]
    boundary_ref: str | None = None

@dataclass(frozen=True)
class AxisInterval:
    lo: float
    hi: float

@dataclass(frozen=True)
class VertexRef:
    owner_kind: Literal["footprint", "cell"]
    floor_id: str
    owner_id: str                    # footprint 时等于 floor_id；cell 时为 cell.id
    vertex_index: int                # 仅在候选副本本次 plan 生命周期内有效

@dataclass(frozen=True)
class SharedAxisComponent:
    axis: EnvelopeAxis
    old_value: float
    new_value: float
    intervals: tuple[AxisInterval, ...]
    vertices: tuple[VertexRef, ...]

@dataclass(frozen=True)
class WindowHost:
    floor_id: str
    room_id: str
    facade: Literal["North", "South", "East", "West"]
    edge_key: str                    # floor_id+room_id+canonical p1/p2/normal
    along_interval: tuple[float, float]

@dataclass(frozen=True)
class EnvelopeGateFinding:
    check_id: str
    ok: bool
    message: str = ""
    evidence: dict | None = None

@dataclass(frozen=True)
class EnvelopeTransactionResult:
    geom: CorrectedGeometryV3        # committed candidate；失败时为原几何 fresh copy+conflict
    committed: bool
    transaction_id: str | None
    intent_ids: tuple[str, ...]
    failed_gate_id: str | None = None

class EnvelopeTransformRejected(ValueError):
    gate_id: str
    evidence: dict

    def __init__(self, gate_id: str, message: str, evidence: dict | None = None):
        super().__init__(message)
        self.gate_id = gate_id
        self.evidence = {} if evidence is None else dict(evidence)
```

`AuthoritativeEnvelope` 只增一个有默认值的内部字段；现 `axes` 和 `axis()` 保持：

```python
@dataclass(frozen=True)
class AuthoritativeEnvelope:
    axes: dict[EnvelopeAxis, EnvelopeAxisResolution] = field(default_factory=dict)
    endpoint_resolutions: tuple[EnvelopeEndpointResolution, ...] = ()

    def axis(self, axis: EnvelopeAxis) -> EnvelopeAxisResolution | None: ...
    def to_dict(self) -> dict: ...
```

`to_dict()` 在 `endpoint_resolutions == ()` 时必须与基座结果精确相等；非空时才增键 `endpoint_resolutions`，避免 legacy audit 无故变化。

新增函数精确签名：

```python
def extract_wing_boundary_evidence_from_view(
    view: ReadingView,
    *,
    view_name: str | None,
    footprint: CorrectedGeometryV3,
) -> list[WingBoundaryEvidence]: ...

def dimension_chain_is_closed_for_endpoint(
    view: ReadingView,
    *,
    chain_id: str,
    axis: Literal["x", "y"],
    close_tol_m: float = DIMCHAIN_CLOSE_TOL_M,
) -> bool: ...

def resolve_envelope_move_intents(
    geom: CorrectedGeometryV3,
    envelope: AuthoritativeEnvelope,
    tol: CoreTolerances,
) -> tuple[EnvelopeMoveIntent, ...]: ...

def build_shared_axis_component(
    geom: CorrectedGeometryV3,
    intent: EnvelopeMoveIntent,
    tol: CoreTolerances,
) -> SharedAxisComponent: ...

def resolve_unique_window_host(
    geom: CorrectedGeometryV3,
    window: WindowV3,
    tol: CoreTolerances,
) -> WindowHost: ...

def run_envelope_hard_gates(
    before: CorrectedGeometryV3,
    candidate: CorrectedGeometryV3,
    *,
    intents: tuple[EnvelopeMoveIntent, ...],
    tol: CoreTolerances,
) -> tuple[EnvelopeGateFinding, ...]: ...

def cell_adjacency_signature(
    geom: CorrectedGeometryV3,
    tol: CoreTolerances,
) -> tuple[tuple[str, str, str], ...]:
    """Sorted (floor_id, lower_cell_id, upper_cell_id) shared-boundary pairs."""
    ...

def topology_signature(
    geom: CorrectedGeometryV3,
    tol: CoreTolerances,
) -> tuple:
    """Sorted floor holes/components, canonical turn sequence, cells, adjacency."""
    ...

def apply_v3_envelope_transaction(
    geom: CorrectedGeometryV3,
    tol: CoreTolerances,
    authoritative_envelope: AuthoritativeEnvelope,
) -> EnvelopeTransactionResult: ...
```

上述函数必须 gt-blind、零 I/O、排序确定；不得读取 attempt 目录、manifest、gt 或环境中的另一份几何。

---

## 4. 触发与证据条件

### 4.1 Overall bounds

只有 `EnvelopeAxisResolution(status="accepted", bounds=(lo,hi))` 才能产 intent。overall resolution 必须完整执行以下规则：

1. 只看 elevation view；North/South 产生 x candidate，East/West 产生 y candidate；
2. candidate 必须来自带 bounds 的 dimension、`outline`/`wall_fill` stroke，或仅作 fallback 的 dimension text；rank 固定为 explicit overall dimension > outline/wall_fill > 其他有 bounds dimension > text-only；同 rank 再按 confidence、span 排序；
3. 每个 view 只取 rank 最高 candidate 参与高权威冲突检查；来自不同 facade view 的 overall/outline/wall_fill 高权威候选若 span 或双方 bounds 的任一端相差超过 `envelope_candidate_agreement_tol_m`，resolution=`conflict`；
4. 最高 candidate 的 span 与当前 footprint span 之差必须 `<= envelope_reconcile_tol_m`；超限 resolution=`skipped`；
5. selected candidate 必须有明确 bounds；只有 span 没 origin/bounds 时 resolution=`skipped`；
6. 单 view 必须是 explicit overall，或有同 view outline/wall_fill 在 `envelope_candidate_agreement_tol_m` 内佐证；
7. 多 view 必须满足 explicit overall、opposite-view agreement、same-view outline/wall_fill agreement 三者至少一项；
8. 通过以上条件才写 `status="accepted"`，并完整保存 selected、corroborating candidates、source ids 和 reason。

candidate 的 dimension `value_m` 与由 endpoints 得到的 span 的一致性也只用 `envelope_candidate_agreement_tol_m`；不得继续使用 `_SMALL_TOL_M` 裸常数。数值从 0.05m 提升为命名配置但不改变基座阈值。

对每轴：

```python
old_lo, old_hi = footprint_bbox(geom)[0 if axis == "x" else 1]
new_lo, new_hi = resolution.bounds
```

- `axis="x"` 的 source facade 必须属于 `{North, South}`；`axis="y"` 必须属于 `{East, West}`；不匹配为 `correction.envelope_evidence_scope` conflict；
- 每个变化的 lo/hi 单独产一个 intent；未超过 `output_precision_m` 的相等值不产 intent、不记 correction；
- 每个 `abs(new-old)` 及 span delta 都必须 `<= envelope_reconcile_tol_m`；超限维持 unsupported，事务不启动；
- lo intent 只能以旧全楼 bbox lo 为 source axis，hi 同理；overall 不得匹配内部同坐标近邻或 notch 轴；
- accepted span 没有 bounds 继续按现文案记 origin ambiguity unsupported。

### 4.2 明确翼分界端点

Reading `Dimension` 维持 legacy `extra="allow"`，本批不加会污染 serializer 的默认字段。只有以下 exact extra 形状被识别：

```json
{
  "boundary_kind": "wing_break",
  "boundary_endpoint": "from",
  "boundary_ref": "south-wing-a"
}
```

可把 `boundary_endpoint` 写成 `"to"`；其余值一律不识别。严禁用 note/OCR 正则猜 `wing`、`break`、`凹口` 等词。

一个 endpoint evidence 必须同时满足：

1. view 是 elevation 且 facade 可确定为 N/S/E/W；
2. dimension `role == "segment"`，`chain_id` 非空，`order` 为整数，`from_pt/to/value_m` 均有限；
3. exact extras 三字段齐全且 `boundary_ref` 非空；
4. 该 chain 有 overall/baseline 且 reading 的 dimension-chain closure 已通过；B2b 不绕过上游失败；
5. 用 `derive_facade_frame(...)` 把标记端点 local-x 转成 world-along；frame 使用**已接受 overall bounds 覆写后的候选 bbox**，并把输入 facade/mirror/local convention/候选 bbox 的 canonical hash 写入 `frame_transform_hash`；
6. world value 在 `envelope_endpoint_match_tol_m` 内只匹配一个该轴 footprint shared-axis component；零/多匹配均 skipped/conflict，不任选；
7. source facade 的 world-along 轴必须等于 intent axis：N/S→x，E/W→y；因此端点证据永远不能生成 cross-axis intent；
8. 同 `boundary_ref` 的高权威候选若相差超过 `envelope_endpoint_match_tol_m`，整 claim conflict；
9. delta 仍须 `<= envelope_reconcile_tol_m`。

普通 `role="segment"` 尺寸、stroke endpoint、窗边、文本 fallback 均不足以触发内部轴移动。它们可以作为 corroborating source 记录，但不能单独升级为 action。

真实 producer 不能只靠手写 fixture：同步在 `skills/intake_pipeline/0_reading/guide.md` 的 dimension 示例/义务中加入上述三字段，明确“仅图上有清晰翼分界标注时输出；普通 dimension 不输出”。不改 `Dimension` typed 字段表，故未带 marker 的 reading serializer 键集不变。新增 producer-path 测试必须把含 marker 的原始 JSON 走 `parse_reading_view/load_reading_view`，再走 envelope extraction；禁止直接构造 `WingBoundaryEvidence` 充当唯一正例。

### 4.3 无动作与混合状态

- `authoritative_envelope is None`：完全 no-op；
- 只有 skipped/unsupported：按现有 audit 分类记录，不启动事务；
- evidence conflict：记 conflict，不生成该 claim intent；其他独立 accepted claim 可组成事务；
- 多个 accepted intents：按 `(axis, old_value, new_value, intent_id)` 排序，一次 plan、一次 gate、一次 commit；
- 同一 `(axis, old_value)` 指向不同 `new_value`、两旧轴变成同轴、lo/hi 反转、intent 形成循环映射：`correction.envelope_intent_consistency` conflict，零 mutation。

---

## 5. 共享轴/vertex graph 与逐边变形算法

### 5.1 输入正规化

事务在 B2 核七步中的 ring canonicalize + cross-floor snap 完成后运行。入口先对 `geom` 做 `ensure_corrected_geometry` fresh round-trip，并断言：

```python
assert isinstance(geom, CorrectedGeometryV3)
assert geom.schema_version == "3"
assert all(floor.footprint.vertices[0] != floor.footprint.vertices[-1] for floor in geom.floors)
```

所有层须有相同 `floor_footprint_fingerprint`。endpoint intent 必须在每层解析到拓扑同构的 shared-axis component；任一层缺失/多解即拒绝全楼事务。

### 5.2 平面化图

对每层构建只存在于本次 plan 内的正交平面图：

1. 输入 edges = footprint open ring 的闭合边 + 每个 cell 的 polygon/bbox ring 边；
2. 在所有同线 edge endpoint、T-junction 和重叠区间端点处分割，形成 canonical vertices；
3. vertex key 使用 `(round-by-configured-attach-match(x), round-by-configured-attach-match(y))` 的确定性键；不得写 `1e-6`/`1e-9` 字面 epsilon；
4. graph edge 记录 owner（footprint/cell）、floor_id、owner_id、原 edge 与分割 interval；
5. 不把相交的垂直轴和水平轴并为同一“可移动 component”。component 只沿与被移动 shared axis 平行的共线 interval 扩张。

`axis="x"` intent 的 shared axis 是 constant-x 竖线；从目标 footprint 竖边/端点出发，只沿 x≈old 的重叠/相接竖向 intervals 做传递闭包。`axis="y"` 同理为 constant-y 横线。不得沿垂直于该轴的边传播，否则会把整栋平移。

overall lo/hi 的种子是所有位于对应全楼 bbox side 的 footprint 共线 edge；wing endpoint 的种子是 `boundary_ref` 唯一匹配的 footprint turn 及其平行 shared axis。component 必须包含 footprint vertex 和至少一个 cell boundary vertex，否则 `correction.envelope_axis_attachment` 拒绝。

### 5.3 生成候选坐标映射

每个 component 产生精确替换 `old_value -> new_value`；同一个 vertex 可同时吃一个 x intent 和一个 y intent，二者按坐标分量交换且结果与排序无关。

对 ring/cell：

1. 只替换 component interval 内、与 `old_value` 相距不超过 `envelope_axis_attach_tol_m` 的对应坐标分量；
2. 若 intent 需要在 owner edge 中点制造 kink，先用平面化图的分割点 materialize vertex；
3. 变形后去掉重复点与无意义共线 degree-2 点，再 canonicalize open CCW；
4. cell 若原 `polygon is None` 且结果仍矩形，只更新 `x/y`；若结果合法但不再是矩形，写入 canonical polygon 并重派生 `x/y`；不得用多个 cell 代替一个 room；
5. 每个 polygon cell 的 `x/y` 必须精确等于其最终 polygon bbox；
6. 每层 ring 完成后写回 `FootprintRing(vertices=...)`；顶层 `footprint_x/y` 最后从最终 rings 精确派生。

### 5.4 Window 一致移动

事务前先对每个 v3 window 调 `resolve_unique_window_host(before, win, tol)`。宿主解析只用本产品几何，不用 gt：

- `floor_id` 指向存在层且 display `floor` 与层名一致；
- `room` 指向同层唯一 cell；
- 候选 host 是该 room 与 footprint 外边界重合、outward normal 对应 `window.facade`、且完整包含 `window.span` 的 exterior edge；
- 完整 span 候选必须恰好一个；零/多候选拒绝，不按中心点猜。

对 window span 的变换：

```python
for endpoint in (span_lo, span_hi):
    if host_along_axis == intent.axis and endpoint belongs_to intent.component:
        endpoint = intent.new_value
```

“belongs_to”必须同时满足：端点距 `old_value <= envelope_axis_attach_tol_m`，且端点落在该 host/component interval；仅数值相近但属于另一断开的 edge 不移动。host plane 沿法向移动时，Window wire 没有法向坐标，span/z 均不改；它通过重建后的宿主墙隐式随墙移动。

变形后重新解析所有 window host；span 顺序反转、宽/高低于既有物理 `min_edge_length_m`、跨过 wing break、宿主改变为零/多解或 facade 变化，均拒绝事务。`z` 永不在 B2b 修改。

### 5.5 FacadeSegment/引用边界

B2b 在 Vg/B5 之前，唯一可接受的 feature state 是 facade segments declared-unpopulated。前置硬门：

```python
assert geom.facade_segments == []
assert all(window.facade_segment_id is None for window in geom.windows)
```

若不满足，不能仅改 `p1/p2` 或 fingerprint，因为 segment id 的 canonical 几何输入已改变，窗 ref 也需稳定重映射；这些 owner 属 Vg/B5。B2b 必须以 gate id `correction.facade_segment_binding` 整事务拒绝，并在 conflict evidence 中列出 segment/window ids。这样“段 ref 重验”的结果是明确拒绝，而不是留下 stale ref。

后续若需要对 Vg-populated artifact 再做 envelope transform，必须另出细稿定义“重跑 Vg→旧新 segment id 映射→window ref 重绑”；不得在本批预埋半实现。

---

## 6. 前置守卫、硬门与门 id

### 6.1 变形前守卫

在候选副本写值前依次执行：

1. `correction.envelope_schema_scope`：strict v3、orthogonal_polygon profile、相同 per-floor footprint；
2. `correction.envelope_evidence_scope`：§4 claim/source facade/along-axis 合法，无 cross-axis；
3. `correction.envelope_intent_consistency`：无一轴多值、反转、交叉、collapse；
4. `correction.facade_segment_binding`：segments 为空、segment refs 全 None；
5. `correction.window_host_unique`：所有 pre window 恰一宿主；
6. `correction.envelope_axis_attachment`：每 intent 在每层唯一 shared component，ring+cell attachment 闭合；
7. `correction.envelope_topology_preserved`：候选模拟后无洞、connected component 数不变、按 cell id 的邻接 pair 集不变、turn/reflex 顺序不变；
8. `correction.envelope_ring_valid`：所有候选 ring/cell 正交、简单、绕向非零且保持 CCW；
9. `correction.envelope_min_edge`：所有 materialized/最终 edge 均 `>= min_edge_length_m`，没有 edge/segment 消失；
10. `correction.envelope_notch_depth_authority`：每 intent 只动 source facade 的 world-along 分量；候选中所有未列入 component 的 cross-axis 坐标逐值等于 before。

这里 `min_edge_length_m` 只做它本来的物理最短边硬门；不得拿它作 axis attachment、endpoint matching、coverage area 或浮点 epsilon。

### 6.2 变形后硬门

候选写完后，按固定顺序运行：

| 顺序 | gate id | 可执行通过条件 |
|---|---|---|
| 1 | `correction.envelope_ring_valid` | `validate_final_corrected_geometry(candidate)` 成功，所有 ring open CCW/正交/简单 |
| 2 | `correction.coverage` | B3 返回的所有该 id findings 均 `ok is True` |
| 3 | `correction.shared_boundary_consistency` | before/candidate 的 cell-id adjacency pair 集相等；每条 post 共享边双方坐标重合，无 orphan T-junction/重叠面 |
| 4 | `correction.window_host_unique` | 每窗 post resolver 恰一宿主，floor/room/facade 一致，完整 span 在宿主内 |
| 5 | `correction.facade_segment_binding` | segments 仍空且所有 segment ref 仍 None |
| 6 | `correction.envelope_identity_snapshot` | Floor.id、Window.id/floor_id/facade_segment_id、Cell.id 集合与对应关系逐值等于 before |
| 7 | `correction.envelope_bbox_projection` | `footprint_x/y == footprint_bbox(candidate)` 精确相等；所有层 fingerprint 相等 |
| 8 | `correction.envelope_topology_preserved` | holes/components/cell count/adjacency/turn sequence 与 before 相等 |

所有 gate 返回 `EnvelopeGateFinding`，不以异常消息字符串决定 pass/fail。`run_envelope_hard_gates` 必须返回完整有序 findings 供 audit；发现失败后可停止昂贵后续门，但已执行门的顺序不可变。

### 6.3 Shared-boundary 口径

新增纯函数：

```python
def check_shared_boundary_consistency(
    before: CorrectedGeometryV3,
    candidate: CorrectedGeometryV3,
    tol: CoreTolerances,
) -> EnvelopeGateFinding: ...
```

它比较按 `(floor_id, min(cell_a,cell_b), max(...))` 键控的 adjacency，不以 cell list 顺序为身份。几何相等只用 `envelope_axis_attach_tol_m` 识别本次 shared-axis attachment；不得复用 B3 面积容差或 `min_edge_length_m`。若 before 本身不一致，事务不得“顺手修”，而应 pre-gate conflict。

---

## 7. 原子提交与回滚协议

### 7.1 候选副本

`apply_v3_envelope_transaction` 必须遵循：

```python
before = CorrectedGeometryV3.model_validate(geom.model_dump())
candidate = before.model_copy(deep=True)
# plan/apply/gates 只操作 candidate
# success -> 返回 fresh validated candidate
# reject  -> 丢弃 candidate，返回 before fresh copy + one conflict
```

禁止先改入参再用反向操作“撤销”；禁止只备份 ring 而让 cells/windows/audit 泄漏；禁止在每个 axis 后局部 commit。

事务 id：

```python
transaction_id = sha256(canonical_json({
    "schema_version": "3",
    "before_fingerprints": sorted(...),
    "intents": [intent_asdict_sorted...],
})).hexdigest()
```

不得包含运行时间、路径或随机数。

### 7.2 成功审计

成功只追加一条 transaction-level correction；精确形状：

```python
{
  "rule_id": "deterministic_core.envelope_atomic_transform",
  "stage": "core",
  "target": "building.per_floor_footprints",
  "claim_type": "numeric",
  "transaction_id": "<hex64>",
  "source_ids": ["<sorted unique>"],
  "original_value": {
    "footprint_fingerprints": {"floor_id": "hex64"},
    "bbox": {"x": [lo, hi], "y": [lo, hi]}
  },
  "resolved_value": {
    "footprint_fingerprints": {"floor_id": "hex64"},
    "bbox": {"x": [lo, hi], "y": [lo, hi]}
  },
  "value_type": "polygon",
  "intents": [
    {"intent_id": "...", "claim_kind": "overall_bound|wing_break_endpoint",
     "axis": "x|y", "side": "lo|hi|internal", "old_value": 0.0,
     "new_value": 0.0, "source_facade": "South", "boundary_ref": null}
  ],
  "moved": {
    "floor_vertex_refs": ["..."],
    "cell_vertex_refs": ["..."],
    "window_span_refs": ["window_id:span[0]"],
    "promoted_rect_cells_to_polygon": ["cell_id"]
  },
  "hard_gates": [{"check_id": "...", "ok": true}],
  "tolerance_name": "ENVELOPE_RECONCILE_TOL",
  "tolerance_value": 0.3,
  "attachment_tolerance_name": "ENVELOPE_AXIS_ATTACH_TOL",
  "attachment_tolerance_value": 0.01,
  "endpoint_match_tolerance_name": "ENVELOPE_ENDPOINT_MATCH_TOL",
  "endpoint_match_tolerance_value": 0.05,
  "changes_topology": false
}
```

数值来自 config，不把示例数值写成执行常量。moved refs 和 source ids 全排序。

### 7.3 回滚 conflict

预置守卫或 post gate 失败时：

- candidate 全丢弃；
- `before.corrections`、`before.unsupported` 不变；
- 只在 fresh `before.conflicts` 末尾追加一条；
- `committed=False`，`failed_gate_id` 为首个失败门；
- 返回几何除该 conflict 外与事务前语义相等。

精确 conflict 形状：

```python
{
  "rule_id": "deterministic_core.envelope_atomic_transform",
  "stage": "core",
  "target": "building.per_floor_footprints",
  "conflict_type": "facade_plan_mismatch|reference_or_identity_ambiguity|unsupported_geometry",
  "claim_type": "numeric|topology_identity",
  "transaction_id": "<hex64-or-null-if-plan-never-formed>",
  "intent_ids": ["<sorted>"],
  "source_ids": ["<sorted unique>"],
  "failed_gate_id": "correction.<id>",
  "reason_unresolved": "<deterministic message>",
  "evidence": {"offenders": []},
  "fallback_action": "rollback_keep_original_geometry"
}
```

证据 status conflict 仍用 conflict；证据不足/无 bounds/超 `ENVELOPE_RECONCILE_TOL` 继续用既有 unsupported 分类，因它们尚未进入变形事务。

### 7.4 异常与故障注入

- 预期安全拒绝只抛/捕获 `EnvelopeTransformRejected`，转成 §7.3 conflict；
- 编程错误、MemoryError、非预期 RuntimeError 不得伪装成业务 conflict，应继续向上抛；由于入参从未被 mutate，调用方可断言原对象未改变；
- 测试可 monkeypatch plan/apply/每个 gate 抛受控或非受控异常，但生产签名不得增加 `fault_injection=True` 开关。

---

## 8. 接入点与逐文件施工表

### 8.1 `src/agent/correction/config.py`

`CoreTolerances` 在 B3 已有面积字段之上新增三个 B2b-owned 字段：

```python
@dataclass(frozen=True)
class CoreTolerances:
    # existing fields...
    envelope_axis_attach_tol_m: float
    envelope_endpoint_match_tol_m: float
    envelope_candidate_agreement_tol_m: float
    coverage_area_tol_m2: float              # B3 contract；B2b 只读
```

loader 必填读取。validate 新增：

```python
if not (0 < envelope_axis_attach_tol_m <= envelope_endpoint_match_tol_m
        <= envelope_reconcile_tol_m):
    raise ValueError(...)
if not (0 < envelope_candidate_agreement_tol_m <= envelope_reconcile_tol_m):
    raise ValueError(...)
if coverage_area_tol_m2 <= 0:
    raise ValueError(...)
```

不得给 dataclass 默认值掩盖漏配；所有手工构造 `CoreTolerances(...)` 的测试 fixture 必须显式补齐。

### 8.2 `src/configs/correction.yaml` 与 A0

新增配置见 §9。B3 的面积项若已在并行施工中加入，本批只消费并解决合并冲突，不重复定义 owner。

### 8.2bis `src/agent/reading/constants.py` 与 reading guide

新增共享常量模块：

```python
DIMCHAIN_CLOSE_TOL_M: float = 0.010  # A0 DIMCHAIN_CLOSE_TOL；迁移既有值
```

`src/validator/checks/reading.py` 删除本地同名定义并 import；`envelope.py` 也只 import 此常量。`skills/intake_pipeline/0_reading/guide.md` 增 §4.2 exact marker producer 义务。不得修改 view manifest、negative evidence 或 facade semantics。

### 8.3 `src/agent/correction/envelope.py`

1. 保持 existing overall candidate extraction/resolution；
2. 增 §3 的 endpoint 类型、严格 extras parser 和 frame hash；
3. `extract_authoritative_envelope(...)` 在 v3 footprint 时附 endpoint resolutions；legacy footprint 不解析 endpoint，保证行为不变；
4. `AuthoritativeEnvelope.to_dict()` 空 endpoint 时保持原 shape；
5. 删除 `_SMALL_TOL_M`，所有 overall candidate/value/bounds agreement 改用 `envelope_candidate_agreement_tol_m`；阈值保持 0.05m，legacy resolution 逐 fixture 等价；本批新增代码不得引入 `1e-9` 一类裸容差。

overall 相关函数统一收同一 tol，精确签名：

```python
def extract_envelope_candidates_from_view(
    view: ReadingView,
    *,
    view_name: str | None = None,
    tol: CoreTolerances | None = None,
) -> list[EnvelopeCandidate]: ...

def extract_envelope_candidates_from_dir(
    vector_dir: Path | str,
    *,
    tol: CoreTolerances | None = None,
) -> list[EnvelopeCandidate]: ...

def resolve_authoritative_envelope(
    candidates: list[EnvelopeCandidate],
    *,
    footprint: CorrectedGeometry | dict[EnvelopeAxis, tuple[float, float]] | None = None,
    footprint_tolerance_m: float = 0.30,
    tol: CoreTolerances | None = None,
) -> AuthoritativeEnvelope: ...
```

三个函数若 `tol is None` 只允许在入口调用一次 `load_core_tolerances()`，随后逐层显式传递同一对象；private `_within/_bounds_agree/_near_matches` 的 tol 参数必须必填、无数值默认。

endpoint chain closure 使用 A0 已有 `DIMCHAIN_CLOSE_TOL`，不创造新阈值。把基座 `src/validator/checks/reading.py` 的 `DIMCHAIN_CLOSE_TOL_M=0.010` 移到 `src/agent/reading/constants.py`，reading validator 与 B2b parser 共同 import；数值和 reading gate 行为逐 fixture 相等。不得从 validator private `_chain_closure` 反向 import，也不得复制另一份 0.010。

为传入 endpoint 所需 config，公共签名扩为：

```python
def extract_authoritative_envelope(
    vector_dir: Path | str,
    *,
    footprint: CorrectedGeometry | dict[EnvelopeAxis, tuple[float, float]] | None = None,
    footprint_tolerance_m: float = 0.30,
    tol: CoreTolerances | None = None,
) -> AuthoritativeEnvelope: ...
```

`finalize_correction_draw` 必须传同一 `tol`，禁止 envelope 自己重载另一份配置。

### 8.4 `src/agent/correction/deterministic.py`

1. 原 legacy v2+polygon reject 放在任何 v3 dispatch 之前，正文精确保留；
2. v1/v2 rectangular 原路径保留；
3. v3 rectangular/nonrectangular 都调用 `apply_v3_envelope_transaction`；删除 `_v3_rectangular_ring` 作为行为分支（可留纯测试 helper，但不得决定 capability）；
4. `_set_v3_ring_bounds` 被共享轴事务取代；不得在 v3 path 单独先改 bbox/cells；
5. transaction 返回新 geom 后，后续 connectivity/window snap 只处理该返回对象；若 transaction rejected，处理的是 original-geometry fresh copy+conflict；
6. v3 `footprint_x/y` 仍在最终从 rings 精确派生；
7. `apply_deterministic_core` 公共签名不变。

建议把现 private API 改为：

```python
def _apply_envelope_reconcile(
    geom: CorrectedGeometry,
    tol: CoreTolerances,
    authoritative_envelope: AuthoritativeEnvelope | None,
) -> CorrectedGeometry: ...
```

不再传三个可变 audit list，也不再只返回 `fx/fy`；审计跟随返回 geom，避免候选回滚后 audit 泄漏。所有现 private-call tests 同步适配。

### 8.5 `geometry_validator.py` / `parse.py` / `finalize.py`

- `geometry_validator.py`：按 B3 已发布签名调用 `check_coverage(geom)`；该函数从同一 active correction config 读取 `coverage_area_tol_m2`。B2b 不改其签名或复制实现。新增 shared-boundary helper 可放本文件或新 `envelope_transform.py`，但只能有一个 owner；
- `parse.py`：schema/draw/final ring 合同不变；B2b 不放宽 strict v3；
- `finalize.py`：仍按 parse/ensure→身份快照→同一 tol→extract envelope→core→身份比对→validate final；只补 `tol=tol` 传给 extraction；
- `schema.py`：零 wire 字段变化。

复杂度建议：把 §3、§5–§7 的新事务实现放 `src/agent/correction/envelope_transform.py`，`deterministic.py` 只负责 dispatch；避免继续扩大千行核文件。此为文件组织定案，不改变公共 import surface。

---

## 9. 新容差与 A0 登记

`src/configs/correction.yaml` 新增：

```yaml
correction:
  envelope_axis_attach_tol_m: 0.010
  # 只用于把 canonical ring/cell/window endpoint 认作同一待移动 shared axis。
  # 不是最短边、不是 coverage、不是 evidence delta 门。

  envelope_endpoint_match_tol_m: 0.050
  # 只用于 wing_break world endpoint 与唯一 footprint shared axis 的匹配，
  # 以及同 claim endpoint candidates 的一致性判断。

  envelope_candidate_agreement_tol_m: 0.050
  # 只用于 overall candidate 之间、dimension value 与 endpoint span 之间的一致性。

  # coverage_area_tol_m2: 0.050 已由 B3 拥有并落地；B2b 不重复添加或改值。
```

A0 tolerance registry 新增三行：

| name | value | unit | status | profiles | hard/warn | basis |
|---|---:|---|---|---|---|---|
| `ENVELOPE_AXIS_ATTACH_TOL` | 0.010 | m | provisional | orthogonal_polygon | hard match | canonical output coordinate identity；只认 shared-axis attachment |
| `ENVELOPE_ENDPOINT_MATCH_TOL` | 0.050 | m | provisional | orthogonal_polygon | evidence match/conflict | elevation endpoint reading resolution；只做 endpoint→axis 唯一匹配 |
| `ENVELOPE_CANDIDATE_AGREEMENT_TOL` | 0.050 | m | calibrated | all | evidence agreement/conflict | 把基座 `_SMALL_TOL_M=0.05` 提升为命名配置；overall candidate/value/bounds agreement 语义不变 |

并在 A0 交叉引用 B3-owned `COVERAGE_AREA_TOL`（config 字段 `coverage_area_tol_m2`）。禁止：

- 复用 `MIN_EDGE_LENGTH` 识别同轴、匹配 endpoint 或判断面积；
- 复用 `ENVELOPE_RECONCILE_TOL` 作 vertex attachment；
- 在新代码写 `0.01/0.05/0.3/1e-6/1e-9` 作为容差字面量；
- 用 Shapely 默认 buffer epsilon 偷渡第三套容差。

`output_precision_m` 只决定 no-op/audit 噪声；`min_edge_length_m` 只做物理最短边；`envelope_reconcile_tol_m` 只做 facade-vs-plan 最大允许修正；三个语义不得混用。

---

## 10. 可执行验收断言

本节 fixture helper 形状固定，避免断言依赖不存在的动态属性：

```python
def geometry_without_audit(value: CorrectedGeometry | dict) -> dict:
    data = value if isinstance(value, dict) else value.model_dump()
    return {k: v for k, v in data.items()
            if k not in {"corrections", "conflicts", "unsupported"}}

def axis_coordinates(geom: CorrectedGeometryV3, axis: Literal["x", "y"]) -> tuple[float, ...]:
    idx = 0 if axis == "x" else 1
    values = [p[idx] for floor in geom.floors for p in floor.footprint.vertices]
    values += [p[idx] for floor in geom.floors for cell in floor.cells
               for p in cell_polygon_vertices(cell)]
    return tuple(sorted(values))
```

### 10.1 Happy path：L 形 overall 外包

fixture：两层相同 L ring，x-hi facade overall 从 10.00→10.20；x=10 shared component 覆盖两层 ring 与贴边 cells；segments 空；windows 有唯一 room host。

```python
before = ensure_corrected_geometry(l_shape_payload)
out = apply_deterministic_core(before, tol, authoritative_envelope=accepted_x_hi)

assert all(max(x for x, _ in f.footprint.vertices) == 10.20 for f in out.floors)
assert out.footprint_x == [0.0, 10.20]
assert out.footprint_y == [0.0, 8.0]
assert len({floor_footprint_fingerprint(out, f) for f in out.floors}) == 1
assert not any("non-rectangular v3 footprints is unsupported" in r.get("reason", "")
               for r in out.unsupported)
row = [r for r in out.corrections
       if r.get("rule_id") == "deterministic_core.envelope_atomic_transform"]
assert len(row) == 1
assert all(f.ok for f in validate_corrected_geometry(out)
           if f.check_id == "correction.coverage")
```

并断言所有未属于 x=10 component 的 ring/cell x/y 坐标逐值等于 before。

### 10.2 U 形 wing endpoint

fixture：U 形凹口朝南，明确 `wing_break` endpoint 把 world x=3.00→3.10；y 坐标是 notch depth 轴，必须完全不动。

```python
result = apply_v3_envelope_transaction(u_geom, tol, env_with_wing_break)
assert result.committed is True
assert axis_coordinates(result.geom, "y") == axis_coordinates(u_geom, "y")
assert 3.10 in axis_coordinates(result.geom, "x")
assert 3.00 not in axis_coordinates(result.geom, "x")  # fixture 中旧轴只属于目标 component
assert topology_signature(result.geom, tol) == topology_signature(u_geom, tol)
assert cell_adjacency_signature(result.geom, tol) == cell_adjacency_signature(u_geom, tol)
```

相同 dimension 去掉 exact `boundary_kind/boundary_endpoint/boundary_ref` 后：

```python
assert resolve_envelope_move_intents(u_geom, env_without_marker, tol) == ()
out = _apply_envelope_reconcile(u_geom, tol, env_without_marker)
assert geometry_without_audit(out) == geometry_without_audit(u_geom)
```

### 10.3 Window 同步与拒绝

```python
result = apply_v3_envelope_transaction(before, tol, env_with_window_axis_move)
assert result.committed is True
moved = result.geom
before_windows = {w.id: w for w in before.windows}
moved_windows = {w.id: w for w in moved.windows}
# span endpoint attached to moved world-along axis -> endpoint follows
assert moved_windows["w_edge"].span == [1.0, 3.10]
# window not on component -> exact no-op
assert moved_windows["w_other"].span == before_windows["w_other"].span
# host normal-plane move -> span/z no-op, post host still unique
assert moved_windows["w_normal"].span == before_windows["w_normal"].span
assert moved_windows["w_normal"].z == before_windows["w_normal"].z
```

跨 wing break、post 零/多 host、room/floor/facade 不一致三例均：

```python
assert result.committed is False
assert result.failed_gate_id == "correction.window_host_unique"
assert geometry_without_audit(result.geom) == geometry_without_audit(before)
assert result.geom.conflicts[-1]["fallback_action"] == "rollback_keep_original_geometry"
```

### 10.4 Segment/ref fail-closed

```python
geom.facade_segments = [valid_segment]
geom.windows[0].facade_segment_id = valid_segment.id
result = apply_v3_envelope_transaction(geom, tol, envelope)
assert result.committed is False
assert result.failed_gate_id == "correction.facade_segment_binding"
assert geometry_without_audit(result.geom) == geometry_without_audit(geom)
```

### 10.5 硬门回滚

对 §6.2 每个 gate 构造一个失败 fixture 或 monkeypatch controlled rejection：

```python
before_dump = geometry_without_audit(geom)
before_corrections = list(geom.corrections)
before_unsupported = list(geom.unsupported)
result = apply_v3_envelope_transaction(geom, tol, envelope)

assert result.committed is False
assert geometry_without_audit(result.geom) == before_dump
assert result.geom.corrections == before_corrections
assert result.geom.unsupported == before_unsupported
assert len(result.geom.conflicts) == len(geom.conflicts) + 1
assert result.geom.conflicts[-1]["failed_gate_id"] == expected_gate_id
```

非预期异常注入：

```python
snapshot = geom.model_dump()
with pytest.raises(RuntimeError, match="injected"):
    apply_v3_envelope_transaction(geom, tol, envelope)
assert geom.model_dump() == snapshot
```

### 10.6 两个原拒绝分支回归（F1 安全锁）

**分支 A：legacy v2+polygon 原文保留。**

```python
before = geom.model_dump()
out = _apply_envelope_reconcile(geom, tol, accepted_env)
assert geometry_without_audit(out) == geometry_without_audit(before)
assert out.unsupported[-1] == {
    "target": "footprint",
    "reason": (
        "authoritative envelope reconcile for polygon cells is not "
        "implemented in schema v2 B1; refusing to move bbox-only "
        "cell edges without moving polygon vertices"
    ),
    "regime_assumption_violated": "rectangular envelope reconcile",
}
```

**分支 B：v3 非矩形 blanket reject 被窄化而非消失安全性。**

```python
# eligible L ring: old blanket reason must disappear and transaction commits
ok = _apply_envelope_reconcile(v3_l, tol, accepted_env)
assert not any("vertex-level deformation belongs to B2b" in r.get("reason", "")
               for r in ok.unsupported)
assert any(r.get("rule_id") == "deterministic_core.envelope_atomic_transform"
           for r in ok.corrections)

# same L ring with ambiguous attachment/populated segment: geometry stays and conflict locks rejection
bad = _apply_envelope_reconcile(v3_l_unsafe, tol, accepted_env)
assert geometry_without_audit(bad) == geometry_without_audit(v3_l_unsafe)
assert bad.conflicts[-1]["fallback_action"] == "rollback_keep_original_geometry"
```

### 10.7 v1/v2 legacy 零影响

对 v1 rectangular、v2 rectangular、v2 polygon 三类 fixture，分别在 `authoritative_envelope=None`、accepted、skipped、conflict、over-tolerance 下与 `bac689b` 保存的 expected semantic payload 比较：

```python
assert out.model_dump() == expected_model_dump
assert built_geometry_dict(out) == expected_built_geometry_dict
assert specs_payload(out) == expected_specs_payload
assert out.corrections == expected_corrections
assert out.conflicts == expected_conflicts
assert out.unsupported == expected_unsupported
```

这里承诺 semantic/geometry/audit equality，不在无 version-gated serializer 的位置宣称 artifact byte equality。legacy Pydantic 类字段表不得改变。

### 10.8 双路径与身份

```python
p = finalize_via_pipeline(payload, vector_dir, target, tol)
s = finalize_via_stepwise(payload, vector_dir, target, tol)
assert p.geom.model_dump() == s.geom.model_dump()
assert p.audit_payload == s.audit_payload
assert p.feature_state_claims == s.feature_state_claims
assert _identity_snapshot(p.geom) == _identity_snapshot(parse_correction_draw(payload, target))
```

promote 后仍按 B2 attempt writer 断言 output/audit/feature_states hash 身份；B2b 不改 artifact contract 或 stage_version。

---

## 11. 测试族清单

建议新增 `tests/test_c2_b2b_envelope_transform.py`，并扩 `test_envelope_extraction.py`、`test_c2_b2_v3.py`、`test_deterministic_core.py`：

1. **evidence parser**：exact marker 正例；缺三字段各一；错误 enum；note-only 不触发；非 elevation；未知 facade；坏 chain；nan/inf；frame mirror/N/W sign；frame hash 稳定；
2. **intent resolver**：overall lo/hi；N/S→x、E/W→y；cross-axis 拒绝；endpoint 零/唯一/多 axis match；同 claim 冲突；delta over tol；多 intent 排序与冲突；
3. **graph**：L/U；断开的同坐标 edge 不串联；T-junction planarization；overlap interval；跨层同构/某层缺 component；x+y 交点交换；
4. **ring/cell**：矩形 v3 与非矩形 v3 同事务；polygon/bbox cell；必要时 rectangle→polygon；CW/closed 不泄漏；self-intersection、cross、min-edge、edge disappear 全拒；
5. **authority**：overall 只移 bbox side；wing 只移 world-along；全部未受影响 cross-axis/notch depth 坐标逐值不变；topology signature 不变；
6. **windows**：沿轴 endpoint 跟随、normal-plane no wire move、非 component no-op、跨 break、room/floor/facade 错、零/多 host、span collapse；
7. **segments/refs**：空表通过；非空表、非空 ref 各自 fail-closed；
8. **hard gates**：ring、B3 coverage、shared boundary、window host、segment binding、identity、bbox/fingerprint、topology 每门至少一负例；
9. **fault injection**：plan、ring write、cell write、window write、bbox derive、每个 post gate；受控拒绝回 conflict，非预期异常传播且入参零 mutation；
10. **原两拒绝分支**：legacy exact entry；v3 eligible 解锁 + unsafe narrowed reject；
11. **legacy 矩阵**：v1/v2 × none/accepted/skipped/conflict/over-tol，built geometry/specs/audit 语义等价；
12. **B3 接口**：monkeypatch `correction.coverage` fail，断言整事务回滚；断言使用 `coverage_area_tol_m2`，静态 grep 不出现 B2b 自建面积阈值；
13. **config/A0**：缺字段、零/负、attach>endpoint、endpoint>reconcile、candidate-agreement>reconcile；环境 override；所有手工 `CoreTolerances` 构造完整；
14. **双路径 E2E**：真实 v3 producer payload→parse→finalize→attempt writer，pipeline/stepwise 语义和 artifact 一致；
15. **零 golden**：现有 golden 与 strict xfail 不改；新增 fixture 独立存放。

静态纪律断言建议：

```bash
rg -n "1e-9|1e-6|buffer\([^)]*[0-9]|_SMALL_TOL_M|_AREA_TOL|MIN_EDGE.*attach|MIN_EDGE.*coverage" \
  src/agent/correction/envelope_transform.py src/agent/correction/envelope.py
```

命中必须逐条说明是既有 overall legacy 代码还是违规；B2b 新代码命中数应为零。

---

## 12. 施工顺序与复核切片

1. B3 dependency probe + config/A0 三个 B2b 容差；
2. endpoint evidence types/parser/resolution（只测，不接 core）；
3. intent consistency + shared-axis planar graph；
4. candidate ring/cell/window transform；
5. pre/post gates 与 audit/rollback；
6. deterministic v3 dispatch，删除 blanket reject，保留 legacy branch；
7. finalize 同 tol 接线与双路径 E2E；
8. legacy、故障注入、两拒绝分支、全量测试；
9. 执行简报逐项列变更文件、测试命令、baseline 数、未改 golden，并交最高档 Fable 复核。

建议在步骤 2、4、6、8 各出独立 diff 供审；不得把 B3/Vg/B5 实现混入 B2b diff。

---

## 13. 开放问题

无。B2b 对已填充 facade segments 采用 fail-closed；其后再变形所需的 segment 重生成/id 重映射明确留给 Vg/B5 后续独立细稿，不构成本批待裁决项。
