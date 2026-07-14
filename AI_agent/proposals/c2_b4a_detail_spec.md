# C2 / B4a GT-v-next、DXF round-trip 与可视核验施工细稿

> 版本：v2
> 日期：2026-07-14
> 批次：B4a（`sol` 次高档）
> 状态：r1 `APPROVE-WITH-CHANGES` 已并入；本文是累计式、自包含施工输入，不是代码变更记录
> 上游：`c2_full_unlock_design.md` v2.2 的 B4a 行，以及 B2 v6、Vg v3、Va v2 已闭合接口

## 版本史

| 版本 | 来源 | 累计变更 |
|---|---|---|
| v1 | 2026-07-14 初稿 | 冻结 B4a 范围、v3 wire、DXF round-trip、render/overlay、测试矩阵及 B4b seam。 |
| r1 | 2026-07-14 交叉审 | 判决 `APPROVE-WITH-CHANGES`：1 MAJOR、1 MINOR、2 NIT，零架构 finding；裁决 R1–R5。 |
| v2 | r1 → v2 | 并入 B4A-F1–F4；写死 loader 分层、存档容差与 build-only profile 断言；登记 Vg 派生量限制及 R1–R5 主控裁决。 |

## 0. 一页定案

B4a 只交付三件事：

1. 新增严格的 **GT schema v3**，把矩形 `W_m/D_m + zones[].rect_m + 四向 opening` 升级为逐层正交多边形、逐层 zone 多边形、逐边界段可见性与 `opening -> boundary_segment_id`；同时对盘上既有 schema 2 做只读 dual-read，绝不伪造迁移。
2. 重写 `gt_from_dxf.py` 的 v3 路径：从显式 manifest 指定的 DXF 视图区和实体规则提取闭合 `LWPOLYLINE`/`LINE` 网络，做 polygonize/topology、逐层/逐 zone 归属、Vg 边界段物化、opening 最近合法段关联；先用运行时生成的 L/U 合成 DXF 完成 round-trip，真实 `sm25/sm26` 到盘后才允许生成候选稿。
3. 升级 `render_gt.py` 与 `render_gt_overlay.py`，按真实多边形和动态 projection surface 渲染，关闭 B-03 的“bbox 看似正确”盲点；保留 v2 语义/像素回归入口。

以下事项明确不在 B4a：段级 score、per-claim denominator、`NOT_APPLICABLE`、completeness 的 user/dataset 生成、score sidecar/缓存键、`render_grade.py` 的 v3 grade 叠图、真实基线 GT/golden 提升。它们归 B4b（以及已定的 Va seam）。在 B4b 接通前，任何 v3 文件只能是临时 round-trip 产物或人工候选，不能放入默认 `case_tests/test_baseline/gt/<case>/gt.json`。

## 1. 权威输入、读盘事实与冲突裁决

### 1.1 本稿采用的权威顺序

有冲突时按下列顺序裁决，后项不得反向覆盖前项：

1. `AI_agent/proposals/c2_full_unlock_design.md` v2.2 的 B4a、E0、E4、T'、DAG 条款；
2. 盘上现有实码：
   - `src/agent/judge/gt.py`
   - `scripts/tool_scripts/{gt_from_dxf,inspect_dxf,render_gt,render_gt_overlay,render_grade,score_reading_vs_gt}.py`
   - `src/agent/correction/{schema,cell_geometry,facade_visibility,facade,footprint}.py`
   - 实际 scorer/run-stage 消费面；
3. `c2_b2_detail_spec.md` v6、`c2_vg_detail_spec.md` v3、`c2_va_detail_spec.md` v2；
4. 现有 GT、DXF、测试和历史提取计划；其中已被上位设计或本轮出稿请求改口的旧结论不再生效。

### 1.2 2026-07-14 读盘基线

| 面 | 已核实事实 | B4a 裁决 |
|---|---|---|
| loader | `src/agent/judge/gt.py` 仅 `json.loads`，无 schema/语义校验，默认只读 `gt/<case>/gt.json` | 保留 `load_gt()` 兼容签名；新增 typed loader/validator，v3 工具必须走 typed API |
| GT 资产 | 盘上只有 `sm21_anchor/gt.json`；其 `schema_version` 为整数 `2`，footprint 是 `W_m/D_m`，zone 是 `rect_m`，且 `wall_thickness_m=0.24` | 原字节不改；以 dual-read 覆盖，不做自动 v2→v3 猜测迁移 |
| 缺失资产 | `sm24_anchor` 无 GT；`sm25/sm26` 尚未到盘 | B4a 不补造；验收只用 `tmp_path` 内合成 L/U DXF |
| DXF 来源 | 当前唯一 `sm21_anchor/source.dxf` 位于 GT 根内；实检为 244 `LINE`、无 `LWPOLYLINE`、六个空间视图，另含 DIMENSION/INSERT/HATCH/TEXT，不是能证明 v3 topology 的样本 | 仅视为 legacy 证据；新 v3 输入强制位于 GT 根和 case data 根之外 |
| 旧 extractor | 固定两个楼层、固定 plan band、固定 role 列表，以 WALL `LINE` bbox/分区线构造矩形，以 bbox 四边分 facade，且 `--write` 可直接覆写 GT | v3 路径全部移除这些推断；不保留“自动写基线”能力 |
| inspector | 能做 entity/bbox/proxy 概览，但不验证闭环、polygonize 残线、zone topology 或 view manifest | 扩为 manifest-aware 只读 preflight；自动 bbox 只能给建议，不能成为真值 |
| render | `render_gt.py`/overlay 均以 W/D、rect、固定四面板渲染；overlay 还依赖像素密度猜测 | v3 改为 polygon/segment/dynamic surface；v2 adapter 保持原行为 |
| scorer | `reading_score.py`、`correction_score.py`、`elevation_score.py` 和 `_grade_transform.py` 仍读取 W/D、rect、四 facade；run-stage cache 未纳入 GT hash | B4a 不接 v3 到默认 scorer；B4b 必须先改 scorer/cache/policy 后才能提升 v3 基线 |
| scorer CLI | `score_reading_vs_gt.py` 只是把 raw GT 交现 reading scorer 的薄 wrapper，没有 v3 schema gate | B4a 不改它；`load_gt()` 对 v3 fail-closed，B4b 再迁 typed consumer |
| Vg | `facade_visibility.py` 已有纯函数 `vg_for_direction(..., tolerances=...)`，能为凹正交环产出全部候选段及可见区间 | v3 extractor/validator 复用公开函数，不复制 skyline，也不依赖私有 hash helper |
| correction v3 | correction schema 已有 `FacadeSegment`、`FloorV3.footprint`、`WindowV3.facade_segment_id`、可选 north-axis evidence | GT v3 与 correction v3 保持几何同构但 schema 独立；不得互相 import model |
| polygon helper | `cell_geometry.py` 已有 Shapely polygon/canonical 辅助，但 API 接 correction cell 且含该域私有 epsilon/bbox checks | 只作语义对账，B4a GT 不 import 这些 cell helper；GT topology 容差走 judge config，不能借私有常数 |
| Va seam | Va v2 明确只给 opening claims；per-claim denominator/NA 与 completeness user/dataset 生成在 B4b | B4a 只保留可供 B4b 消费的几何/证据字段，不生成任何评分结论 |

### 1.3 旧文档冲突

旧 `cad_to_gt_extraction_plan.md` 曾把 `source.dxf` 放在 GT case 目录内；本轮请求与更早 H1 review 均要求源 DXF 脱离 GT 根。本稿采用：

```text
case_tests/test_baseline/gt_sources/<case>/source.dxf   # 人工受控源，仅未来真实 case 使用
case_tests/test_baseline/gt/<case>/gt.json              # 唯一真值输出，B4b 前禁止写 v3
```

盘上 `sm21_anchor/source.dxf` 不在本批搬动，因为搬文件属于资产改动且不影响 v3 合成验收；是否另开 data-only 批次迁移，列入 §15 review-ask。

## 2. 范围、不变量与禁区

### 2.1 B4a in-scope

- GT schema 2/3 的 typed 解析、v3 严格线型和跨字段验证；
- v3 canonical serialization、content hash、原子候选写出；
- DXF inspection、manifest 校验、显式 view clipping、单位/坐标变换；
- 正交无洞 L/U footprint 与 zone polygonization；
- 每层 boundary segment、Vg visible intervals、opening→segment 关联；
- 可选 `north_axis_deg` 的提取/保真；
- v2/v3 `render_gt` 和 overlay 的 typed render adapter；
- 合成 L/U DXF round-trip 与所有负向测试；
- B4b 消费所需的只读 contract fixture/API seam。

### 2.2 永久不变量

1. **Gate 隔离**：GT 只能被 gate② judge/human tooling 读取；gate① executor/correction/reading 生产路径不得 import `src.agent.judge`、读取 `case_tests/test_baseline/gt` 或由 GT 派生决策。
2. **形状开放**：wire 与实现不得假定矩形、四条外边、每方向一段、两个楼层、四张 elevation、固定 zone 数、固定 role 次序。
3. **当前 C2 几何 profile**：每层同一 footprint；简单正交、无洞；L/U 可用。courtyard/洞、多岛、斜边、不同层退台留到 C3。schema 为洞保留结构，但 C2 validator 必须 fail closed。
4. **坐标真值**：GT v3 的所有几何均为 metre、building-axis world 坐标；不得保存画布像素或 view-local 数值作为评分真值。
5. **无隐含容差**：任何拓扑吸附、相等、最近段、elevation 匹配和 Vg 比较都只用显式、已校验的 tolerance profile；函数体不得散落裸常数。
6. **证据不补造**：未观察到的 z 不得从相邻窗、楼层平均或“常见窗高”补齐。尤其 sm26 的 inner-wall plan window 可有平面 x/width 真值而 `z_interval=null`。
7. **不自动提升**：generator 只写显式 `--out` 候选且拒绝覆盖；不得提供 `--write`、`--promote` 或默认 GT-root 输出。
8. **零资产扰动**：B4a 实现和测试不得改现有 `gt.json`、DXF、PNG、golden、grade truth；合成输入与渲染产物只进 pytest 临时目录。

### 2.3 B4a 明确 out-of-scope

- v3 reading/correction/elevation score 公式与权重；
- segment-level matching/scoring、claim denominator、`NA`/`NOT_APPLICABLE`；
- completeness 的 user/dataset 侧生成；
- run-stage score sidecar、GT hash cache key、policy/schema bump；
- `render_grade.py` v3 展示与 score report wire；
- `sm21` 自动迁移、`sm24` 补 GT、`sm25/sm26` 真值签收；
- correction schema v3、Vg、Va 的行为修改。

## 3. 施工落点与依赖方向

### 3.1 预定文件面

下表描述后续实施 B4a 时允许的改动面；本细稿本身不执行这些改动。

| 文件 | 动作 | 单一职责 |
|---|---|---|
| `src/agent/judge/gt_schema.py` | 新增 | schema 2/3 typed models、v3 canonical/hash、structural/semantic validator |
| `src/agent/judge/gt.py` | 修改 | 兼容 loader 与新 typed loader；不引入 extractor/render 依赖 |
| `src/agent/judge/gt_manifest.py` | 新增 | v3 extraction manifest 与 tolerance config model |
| `src/agent/judge/gt_extraction.py` | 新增 | 纯/准纯 DXF→GT 构建逻辑；唯一 DXF I/O 在边缘函数 |
| `src/agent/judge/gt_render_model.py` | 新增 | v2/v3→统一 render primitives adapter |
| `src/configs/judge_gt.yaml` | 新增 | B4a 唯一默认 tolerance profile；值完整、无代码默认 |
| `skills/intake_pipeline/1_correction/A0_contract.md` | 仅登记 | 新增 judge-GT 专属 tolerance registry 行；复用既有两条 Vg epsilon 登记，不改 correction 权威矩阵 |
| `scripts/tool_scripts/inspect_dxf.py` | 重写/扩展 | 只读 inspect + manifest preflight；无自动真值推断 |
| `scripts/tool_scripts/gt_from_dxf.py` | 重写为薄 CLI | 严格 v3 candidate builder；显式输入/输出，拒绝覆盖/提升 |
| `scripts/tool_scripts/render_gt.py` | 修改 | typed v2/v3 动态 plan/elevation render |
| `scripts/tool_scripts/render_gt_overlay.py` | 修改 | v3 manifest affine overlay；保留 legacy v2 wrapper |
| `tests/test_gt_schema.py` | 新增 | strict wire、dual-read、semantic validator、hash |
| `tests/test_gt_from_dxf.py` | 重写 | tmp L/U DXF round-trip 与失败矩阵 |
| `tests/test_inspect_dxf.py` | 扩展 | topology/view/source-isolation preflight |
| `tests/test_gt_render.py` | 扩展 | v2 回归 + v3 动态 render |
| `tests/test_gt_overlay.py` | 扩展 | affine/hash/dynamic overlay |
| `tests/test_gt_discipline.py` | 扩展 | gate 隔离、零 baseline 写入、禁固定四面 |

不得在 B4a 修改 `render_grade.py`、各 scorer、`run_stage.py`、correction/Vg/Va 代码。若实施中发现必须修改这些文件才能让默认测试通过，应停止并交 B4b，不得在 B4a 偷接。

### 3.2 依赖图

```text
gt_schema  <- gt(loader)
    ^             ^
    |             |
gt_manifest   gt_render_model <- render_gt / render_gt_overlay
    ^
    |
gt_extraction <- gt_from_dxf / inspect_dxf
    |
    +-- public correction.facade_visibility.vg_for_direction
    +-- public correction.footprint.footprint_fingerprint

existing scorers / run_stage / render_grade  --X--> GT v3   (B4a 禁止接线)
executor / reading / correction production   --X--> judge.* (永久禁止)
```

`gt_extraction` 可复用 Vg 的公开纯几何 API；`correction` 不得反向 import `judge`。GT model 不继承或 import correction Pydantic model，以免两个 schema 的版本生命周期绑死。

## 4. 坐标、环、边界段与 north-axis 语义

### 4.1 building-axis world frame

- 右手系，单位 metre，`+Z` 向上；
- `+X` 为 building East，`+Y` 为 building North；
- facade family 与 outward normal 固定为：North `(0,+1)`、South `(0,-1)`、East `(+1,0)`、West `(-1,0)`；
- family 是 building-axis 标签，不因 `north_axis_deg` 改名；
- 水平边的 `world_along_interval` 是其 world-x 的升序 `[lo, hi]`，竖直边是 world-y 的升序 `[lo, hi]`。
- `z_floor_m` 与 opening `z_interval` 都是 building world-z；后者不是 floor-local sill/head。楼层占据 `[z_floor_m, z_floor_m + ceiling_height_m]`，共享层界只算接触不算重叠。

### 4.2 canonical ring

所有 `GtRingV3.vertices`：

1. wire 为**开放环**：末点不得重复首点；
2. 至少四个互异点；坐标 finite；bool 不算 number；
3. 只允许水平/竖直非零边；
4. 不允许重复点、回折、自交、自触、非相邻边接触；
5. exterior 逆时针（CCW）；interior ring 若未来启用则顺时针（CW）；
6. 删除同向共线中间点并把字典序最小点转到首位；`-0.0` 规范为 `0.0`；
7. canonicalizer 只允许删除严格共线点和方向反转，禁止 tolerance-based 改写坐标。DXF 吸附只能发生在 polygonize 前，且使用 manifest/config 中的显式容差。

### 4.3 boundary segment

每个 exterior 边恰好对应一个 `GtBoundarySegmentV3`，由四次公开调用：

```python
vg_for_direction(vertices, direction, *, tolerances) -> tuple[DerivedVisibleSegment, ...]
```

其中 `direction` 依次为 `(0,1)`、`(0,-1)`、`(1,0)`、`(-1,0)`。必须保留 Vg 返回的所有候选边，包括 `visible_intervals=[]` 的完全遮挡边；不能把同 family 的多深度边合并成一条。`depth` 是该方向最前支撑线到本边 wall plane 的非负距离，语义与 Vg v3 完全相同。

`p1/p2` 沿建筑立面标准方向排列：South 西→东、East 南→北、North 东→西、West 北→南。`world_along_interval` 始终升序，与 `p1/p2` 的方向无关。visible interval 使用半开 `[lo, hi)` 语义；wire 仍写 `{lo, hi}`。

### 4.4 `north_axis_deg`

`north_axis_deg` 严格沿用 E4.2 已闭合语义：俯视时从 true/project North **顺时针旋转到 building `+Y`** 的角度，规范到 `[0,360)`；它就是后续写入 EnergyPlus `Building.North Axis` 的 θ。故 true North 在 building 坐标中的平面向量为 `(-sin θ, cos θ)`。它是可选元数据：

- 缺字段或 `null` 均表示“无真值”；canonical writer 总是显式写 `null`；
- 不得把未知默认为 `0`；
- 不参与 footprint、facade family 或 segment ID 计算；
- 非空时必须有 source ref，且 extractor 只能从 manifest 明确绑定的 north arrow/已审元数据读取；
- B4a renderer 可画 north arrow，但 scorer 是否使用由后批另定。

## 5. GT schema v3：严格 wire contract

### 5.1 共同强类型

实现采用 Pydantic v2，所有 v3 model 均：

```python
model_config = ConfigDict(extra="forbid", strict=True)
```

公共 alias（示意即施工签名，不得放宽）：

```python
StrictFiniteFloat = Annotated[float, Strict(), AllowInfNan(False)]
NonNegativeFiniteFloat = Annotated[StrictFiniteFloat, Field(ge=0)]
PositiveFiniteFloat = Annotated[StrictFiniteFloat, Field(gt=0)]
StrictNonNegativeInt = Annotated[int, Strict(), Field(ge=0)]
Hex64 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
StableId = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
]
HumanLabel = Annotated[str, StringConstraints(min_length=1, max_length=255)]
DxfHandle = Annotated[str, StringConstraints(pattern=r"^[0-9A-F]+$")]
DateYmd = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
Point2 = tuple[StrictFiniteFloat, StrictFiniteFloat]
# interval wire 唯一类型见 §5.2 GtWorldIntervalV3；本节不另定义别名。
```

JSON 的整数坐标可被 strict float 接受，但字符串、bool、NaN/Inf 和数值字符串一律拒绝。闭 vocab 必须使用下文的 `Literal`；zone role、case/floor/view 等数据集开放标识用受限字符串，不伪装成闭 enum。

### 5.2 完整 model 形状

以下字段集合就是 v3 wire；除显式 nullable/default 外没有隐藏字段。

```python
class GtWorldIntervalV3(BaseModel):
    lo: StrictFiniteFloat
    hi: StrictFiniteFloat                 # lo < hi

class GtRingV3(BaseModel):
    vertices: list[Point2] = Field(min_length=4)  # canonical open ring

class GtPolygonV3(BaseModel):
    exterior: GtRingV3
    interior_rings: list[GtRingV3] = Field(default_factory=list)
                                           # v3 wire 预留；C2 profile 必须为空

class GtEntityRefV3(BaseModel):
    source_id: StableId
    view_id: StableId
    entity_handle: DxfHandle
    subentity_index: StrictNonNegativeInt | None = None
                                           # 展开块/polyline edge 时必填
    role: Literal[
        "footprint_boundary", "zone_boundary", "opening_plan",
        "opening_elevation", "north_axis", "configured_binding"
    ]

class GtSourceViewV3(BaseModel):
    id: StableId
    kind: Literal["plan", "elevation"]
    floor_ids: list[StableId] = Field(min_length=1)
    projection_surface_key: StableId | None
    facade_family: Literal["North", "South", "East", "West"] | None
    view_kind: Literal["full", "partial"] | None
    world_along_coverage: GtWorldIntervalV3 | None
    direction_semantics: Literal["building_axis", "true_azimuth"] | None
    azimuth_deg: Annotated[StrictFiniteFloat, Field(ge=0, lt=360)] | None
    # plan: 恰一 floor 且 key/family/view_kind/coverage/semantics/azimuth 为空

class GtSourceDocumentV3(BaseModel):
    id: StableId
    kind: Literal["dxf"]
    label: HumanLabel                     # basename/人工标签；不得含绝对路径或 ..
    content_sha256: Hex64
    native_units: Literal["m", "mm", "cm", "in", "ft", "unitless"]
    metres_per_unit: PositiveFiniteFloat
    views: list[GtSourceViewV3] = Field(min_length=1)

class GtExtractionTolerancesV1(BaseModel):
    profile_version: Literal[1]
    dxf_node_join_tolerance_m: PositiveFiniteFloat
    dxf_axis_alignment_tolerance_m: PositiveFiniteFloat
    dxf_topology_area_tolerance_m2: PositiveFiniteFloat
    opening_boundary_max_distance_m: PositiveFiniteFloat
    opening_assignment_tie_epsilon_m: PositiveFiniteFloat
    elevation_match_max_distance_m: PositiveFiniteFloat
    elevation_match_tie_epsilon_m: PositiveFiniteFloat

class GtResolvedToolingTolerancesV1(GtExtractionTolerancesV1):
    # 从既有 correction.yaml/A0 Vg registry 解析，不在 judge_gt.yaml 复制
    vg_depth_epsilon_m: PositiveFiniteFloat
    vg_endpoint_epsilon_m: PositiveFiniteFloat

class GtResolvedToolingConfigV1(BaseModel):
    tolerances: GtResolvedToolingTolerancesV1
    judge_config_sha256: Hex64
    vg_config_sha256: Hex64

class GtImplementationHashesV1(BaseModel):
    extractor_sha256: Hex64
    validator_sha256: Hex64
    vg_implementation_sha256: Hex64

class GtVerificationV3(BaseModel):
    status: Literal["candidate", "human_verified"]
    reviewer_id: StableId | None
    reviewed_on: DateYmd | None
    methods: list[Literal[
        "dxf_topology_roundtrip", "direct_gt_render",
        "overlay_on_original_drawing", "human_source_comparison"
    ]] = Field(default_factory=list)

class GtGeneratorV3(BaseModel):
    name: Literal["energyplus-agent.gt_from_dxf"]
    contract_version: Literal[1]
    extractor_sha256: Hex64
    validator_sha256: Hex64
    vg_implementation_sha256: Hex64
    manifest_sha256: Hex64
    judge_config_sha256: Hex64
    vg_config_sha256: Hex64
    tolerances: GtResolvedToolingTolerancesV1

class GtZoneV3(BaseModel):
    id: StableId
    name: HumanLabel
    role: StableId
    polygon: GtPolygonV3
    source_refs: list[GtEntityRefV3] = Field(min_length=1)

class GtBoundarySegmentV3(BaseModel):
    id: StableId
    floor_id: StableId
    boundary_loop_id: Literal["exterior"]
    facade_family: Literal["North", "South", "East", "West"]
    p1: Point2
    p2: Point2
    outward_normal: tuple[Literal[-1,0,1], Literal[-1,0,1]]
    world_along_interval: GtWorldIntervalV3
    depth: NonNegativeFiniteFloat
    visible_intervals: list[GtWorldIntervalV3]
    source_footprint_fingerprint: Hex64
    projection_surface_keys: list[StableId] = Field(default_factory=list)
    wall_thickness_m: PositiveFiniteFloat | None
    source_refs: list[GtEntityRefV3] = Field(min_length=1)

class GtFloorV3(BaseModel):
    id: StableId
    name: HumanLabel
    z_floor_m: StrictFiniteFloat
    ceiling_height_m: PositiveFiniteFloat
    footprint: GtPolygonV3
    footprint_fingerprint: Hex64
    zones: list[GtZoneV3] = Field(min_length=1)
    boundary_segments: list[GtBoundarySegmentV3] = Field(min_length=4)
                                           # 不设 max/固定四条

class GtOpeningV3(BaseModel):
    id: StableId
    kind: Literal["window", "door"]
    floor_id: StableId
    host_zone_id: StableId | None
    boundary_segment_id: StableId
    world_along_interval: GtWorldIntervalV3
    z_interval: GtWorldIntervalV3 | None
    source_refs: list[GtEntityRefV3] = Field(min_length=1)  # plan-only 合法

class GroundTruthV3(BaseModel):
    schema_version: Literal[3]             # JSON integer，不是 "3"
    case: StableId
    geometry_profile: Literal["c2_simple_orthogonal_no_holes"]
    coordinate_frame: Literal["building_axis_world_m"]
    verification: GtVerificationV3
    generator: GtGeneratorV3
    sources: list[GtSourceDocumentV3] = Field(min_length=1)
    north_axis_deg: Annotated[StrictFiniteFloat, Field(ge=0, lt=360)] | None = None
    north_axis_source_refs: list[GtEntityRefV3] = Field(default_factory=list)
    floors: list[GtFloorV3] = Field(min_length=1)
    openings: list[GtOpeningV3] = Field(default_factory=list)
    content_sha256: Hex64
```

`north_axis_deg` 正是上位 E4 所定的可选顶层槽位。跨字段约束为：数值为 `null` 时 source refs 必须为空；数值非空时 refs 至少一项且全为 `role="north_axis"`。canonical writer 总是显式写这两个字段，未知北向不得省略成隐含 `0`。

### 5.3 示例 wire（非资产、只说明形状）

```json
{
  "schema_version": 3,
  "case": "synthetic_l",
  "geometry_profile": "c2_simple_orthogonal_no_holes",
  "coordinate_frame": "building_axis_world_m",
  "verification": {"status":"candidate","reviewer_id":null,"reviewed_on":null,"methods":[]},
  "generator": {"...": "完整字段见 5.2"},
  "sources": [{"...": "完整字段见 5.2"}],
  "north_axis_deg": null,
  "north_axis_source_refs": [],
  "floors": [
    {
      "id": "F1",
      "name": "Floor 1",
      "z_floor_m": 0.0,
      "ceiling_height_m": 3.0,
      "footprint": {"exterior": {"vertices": [[0,0],[8,0],[8,4],[4,4],[4,8],[0,8]]}, "interior_rings": []},
      "footprint_fingerprint": "<64 lowercase hex>",
      "zones": [{"...": "polygon + source refs"}],
      "boundary_segments": [{"...": "one exterior edge, including hidden edges"}]
    }
  ],
  "openings": [{"...": "segment ref + plan interval + nullable z"}],
  "content_sha256": "<64 lowercase hex>"
}
```

此示例中的省略号不能出现在真实 JSON，也不是 golden。

### 5.4 稳定 ID 与排序

稳定性不得依赖 DXF entity 遍历顺序、dict 顺序、ring 起点或临时文件路径。

- floor/zone/opening 的业务前缀来自 manifest 的显式 ID；
- segment 几何 hash 输入为 canonical JSON：

```json
{"schema":"gt_boundary_segment_geometry_v1","floor_id":"F1","facade_family":"North","p1":[...],"p2":[...]}
```

- segment ID：`<floor_id>:boundary:<sha256前24位>`；实现必须在整文档校验截断碰撞，碰撞即 fail，不可自动加序号；
- `projection_surface_keys` 由 manifest 的 elevation view scope 明确产生，按 lexical 排序且去重；可为空或多项，不能由 family 单独推成固定四个；
- floor 按 `(z_floor_m,id)`；zone 按 `id`；segment 按 `(family_rank, along.lo, along.hi, depth, id)`，family rank 为 North/South/East/West；opening 按 `(floor_id, boundary_segment_id, along.lo, kind, id)`；source/view 按 `id`；ref 按 `(source_id,view_id,entity_handle,subentity_index或-1,role)`；projection keys/visible intervals 各自升序；
- canonical hash 不含输入路径、mtime、生成时间或主机信息。

persisted wire 的每个 list 必须已经是上述 canonical 顺序；validator 对乱序报 `gt_wire_noncanonical_order`，不在 load 时静默重排。canonical serializer 仍排序作 defense-in-depth。所谓“输入顺序不敏感”只指 DXF entity、manifest selector 和原始 ring 起点经 extractor 后得到同一 canonical wire，不指任意乱序 GT JSON 都合法。

### 5.5 canonical bytes 与 content hash

必须提供：

```python
def canonical_gt_v3_payload(doc: GroundTruthV3) -> dict[str, JsonValue]: ...
def canonical_gt_v3_bytes(doc: GroundTruthV3) -> bytes: ...
def compute_gt_v3_content_sha256(doc: GroundTruthV3) -> str: ...
def write_gt_v3_candidate(doc: GroundTruthV3, out: Path, *, overwrite: Literal[False] = False) -> None: ...
```

规则：先 model dump；把 `content_sha256` 临时置为 64 个 `0`，canonical 排序并将所有 `-0.0` 变 `0.0`；用 `json.dumps(..., sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False)` 加单个末尾换行编码 UTF-8；hash 该 bytes；回填 hash 后再 canonical dump。禁止量化/round 浮点，因量化会隐藏 topology 错误。

writer 只接受 `verification.status="candidate"`，先在同目录创建 mode `0o600` 临时文件、flush/fsync、再次 typed load/hash 校验，再 `os.replace`；但 `out.exists()`，或 `out` 位于 `DEFAULT_GT_DIR`、`case_tests/test_baseline/gt_sources`、任何 `case_tests/e2e_tests/*/case_data` 内时，必须先以稳定错误码拒绝。B4a API 不提供 `overwrite=True` 的可调用实现，签名中的 Literal 是静态/运行时双保险。把 candidate 改为 `human_verified` 并重算 hash 的 promotion/sign-off 工具属于后续资产批，不在 B4a 偷加。

implementation hash 也不得取易漂移的 git dirty flag/mtime。提供：

```python
def compute_gt_implementation_hashes(repo_root: Path) -> GtImplementationHashesV1: ...
```

每组按相对 POSIX path 排序，hash preimage 为逐文件 `relative_path + b"\0" + raw_bytes + b"\0"`：extractor 组含 `src/agent/judge/{gt_extraction,gt_manifest}.py` 与 `scripts/tool_scripts/gt_from_dxf.py`；validator 组含 `src/agent/judge/{gt_schema,gt}.py`；Vg 组含 `src/agent/correction/{facade_visibility,facade,footprint,schema}.py`。缺文件或路径逃出 repo root 均 fail。这样 candidate 精确绑定实际 helper bytes，而不要求开发工作树预先 clean/commit。

## 6. legacy schema 2 / v3 dual-read 与 loader 合同

### 6.1 兼容策略

采用 **dual-read、零迁移改写**：

- 整数 `2`：`LegacyGroundTruthV2`，按当前 `sm21_anchor` 线型校验 `W_m/D_m`、floors、`zones[].rect_m`、opening group、source/verified/wall thickness；
- 整数 `3`：只接受 §5 的 `GroundTruthV3`；
- 当前工作树没有 schema 1 或缺版本 GT；二者以 `gt_wire_unsupported_legacy_version` fail closed，不能凭 git 历史草稿形状扩出运行时合同；若将来真有受支持资产，先把原字节 fixture 收录并另审 schema；
- 字符串 `"2"`/`"3"`、未知整数、bool、浮点版本一律拒绝；
- v2 adapter 可供旧 render/scorer 使用，绝不生成 polygon、segment ID 或 source handle，因为这些信息不能从 bbox 无损恢复。

v2 model 同样 `extra="forbid", strict=True`，完整 wire 如下；前导下划线字段用普通 Python field + `Field(alias="_...")` 实现，不能用 `extra="allow"`：

```python
class LegacyFootprintV2(BaseModel):
    W_m: PositiveFiniteFloat
    D_m: PositiveFiniteFloat

class LegacyZoneV2(BaseModel):
    id: str
    role: str
    rect_m: tuple[StrictFiniteFloat, StrictFiniteFloat,
                  StrictFiniteFloat, StrictFiniteFloat]  # x0< x1, y0<y1

class LegacyFloorV2(BaseModel):
    name: str
    z_floor: StrictFiniteFloat
    ceiling_height: PositiveFiniteFloat
    zone_count: Annotated[int, Strict(), Field(ge=1)]
    zones: list[LegacyZoneV2]

class LegacyOpeningV2(BaseModel):
    x_m: StrictFiniteFloat
    width_m: PositiveFiniteFloat
    sill_m: StrictFiniteFloat
    head_m: StrictFiniteFloat              # sill < head

class LegacyWindowGroupV2(BaseModel):
    facade: Literal["North", "South", "East", "West"]
    floor: str
    count: StrictNonNegativeInt
    sill_m: StrictFiniteFloat | None
    head_m: StrictFiniteFloat | None
    openings: list[LegacyOpeningV2]

class LegacyDoorV2(LegacyOpeningV2):
    facade: Literal["North", "South", "East", "West"]
    floor: str

class LegacyGroundTruthV2(BaseModel):
    case: str
    schema_version: Literal[2]
    source: str | None = Field(default=None, alias="_source")
    cad_file: str | None = Field(default=None, alias="_cad_file")
    cad_sha256: Hex64 | None = Field(default=None, alias="_cad_sha256")
    extractor: str | None = Field(default=None, alias="_extractor")
    note: str | None = Field(default=None, alias="_note")
    verified: bool | None = Field(default=None, alias="_verified")
    verified_by: str | None = Field(default=None, alias="_verified_by")
    verified_on: str | None = Field(default=None, alias="_verified_on")
    verified_method: str | None = Field(default=None, alias="_verified_method")
    wall_thickness_m: PositiveFiniteFloat
    wall_thickness_note: str | None = Field(default=None, alias="_wall_thickness_note")
    footprint: LegacyFootprintV2
    floors: list[LegacyFloorV2]
    windows: list[LegacyWindowGroupV2]
    doors: list[LegacyDoorV2]
```

v2 语义校验还锁：case 与目录名一致；floor/zone ID 与 floor name 唯一；`zone_count == len(zones)`；每 window group `count == len(openings)`，count=0 时 group sill/head 均 null，否则非空且每 opening 在 group/floor z 范围；floor ref 存在；door/window x+width 落在对应 W/D facade span；rect 均落 footprint 且现有 zones 无重叠/缺口。typed adapter dump 必须 `by_alias=True`；兼容 `load_gt()` 则在 typed 校验成功后直接返回最初 `json.loads` 得到的 mapping，不从 model 重建，因而字段名、list 顺序和 Python number 类别均保持当前 raw 解析结果。

### 6.2 API

`src/agent/judge/gt.py` 保持已有调用不破：

```python
GtDocument = LegacyGroundTruthV2 | GroundTruthV3

def gt_path(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> Path: ...

def case_gt_dir(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> Path: ...

def has_gt(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> bool: ...

def load_gt(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> dict | None:
    """legacy scorer API：missing -> None；v2 validate 后返回原 mapping；v3 fail closed。"""

def load_gt_document(case: str, *, gt_dir: Path | str = DEFAULT_GT_DIR) -> GtDocument | None: ...

def load_gt_file(path: Path | str, *, allow_legacy: bool = True) -> GtDocument: ...
```

校验层次固定如下，不允许实现者按现场 config 状态另选路径：

| 层 | 固定职责 |
|---|---|
| L0 read | case-based API 先校验 `case: StableId`，且 `gt_path(...).resolve()` 仍在 `gt_dir.resolve()` 下，不接受 `../`；随后读取 bytes、UTF-8/JSON decode。file API 读取 caller 显式给定的路径，不冒充默认根策略。 |
| L1 wire | 只按 JSON integer `schema_version` dispatch；v2/v3 分别做 `extra="forbid"` 的 strict Pydantic 结构校验；缺版本、v1、未知版本 fail。 |
| L2 intrinsic | 校验 canonical order/content hash 及全部文档内生语义。v2 使用 §6.1 的精确 legacy 规则；v3 必须调用 `validate_gt_v3(doc, tolerances=doc.generator.tolerances, expected_case=...)`，其中 Vg 重算和所有 tolerance-sensitive 语义一律只取该文档存档的 `doc.generator.tolerances`。 |
| L3 baseline policy | case-based typed API 校验目录 case 一致性；默认 GT 根中的 v3 还要求 `verification.status="human_verified"`。自定义根不因此成为 candidate 入口。 |

`load_gt_file()` 固定跑 L0 → L1 → L2，不跑 L3，并以 `expected_case=None` 调 v3 validator，故可读 candidate/verified；`allow_legacy=False` 时在 L1 拒 v2。`load_gt_document()` 固定跑 L0 → L1 → L2 → L3，以 caller 的 `case` 作为 `expected_case`，missing 返回 `None`。所有已进入的层对 decode、schema、semantic、canonical/hash 错误均 fail closed，错误包含稳定 `code` 和 JSON pointer，但不泄漏绝对路径。

`has_gt()` 只做安全 case/path 推导与 regular-file existence probe，不 parse、不声称资产有效。`load_gt()` 对 missing 返回 `None`；v2 固定跑 L0 → L1 → v2 L2 后返回原 mapping；一旦 L1 识别为 v3 就报 `gt_v3_requires_typed_consumer`，不把该兼容 API 伪装成 v3 validator。

两个 typed loader 的 load 路径均禁止调用 `load_gt_tooling_config()`，禁止读取当前仓库的 `judge_gt.yaml`/`correction.yaml`，也禁止把 `doc.generator.tolerances` 与当前 resolved profile 比较。因而旧 verified v3 在 profile 演进后仍按自身生成时的存档容差自验证；“与当轮 profile 逐字段相等”只属于 §10.8 的 build 自检。

`load_gt()` 是当前旧 scorer 的无类型入口，故遇 v3 必须报 `gt_v3_requires_typed_consumer`，不能返回一个会被 W/D/rect scorer 误读的 dict。B4a renderer/extractor 走 `load_gt_document()`/`load_gt_file()`；B4b scorer 接通后也必须迁到 typed API，而不是放宽 `load_gt()`。此裁决既保持当前 v2 caller 行为，又为“禁止 B4b 前提升 v3”加第二道机械门。

`load_gt_file()` 接受 candidate/verified，供临时工具使用；`load_gt_document(case, gt_dir=DEFAULT_GT_DIR)` 若遇 v3 还必须要求 `verification.status="human_verified"`，否则报 `gt_default_root_candidate_forbidden`。自定义临时 `gt_dir` 也不自动获得“基线”身份；调用者若要读 candidate 应明确用 file API。

### 6.3 v2 回归门

- 当前 `sm21_anchor/gt.json` 的 SHA256 在 B4a 前后相同；
- `load_gt("sm21_anchor")` 深等于当前 raw JSON；
- v2 render adapter 输出的 primitive tree 深等于固定测试快照（可在测试内构造，不能新增 golden 文件）；
- legacy render 的既有关键像素/尺寸/面板标题断言继续通过；
- 不允许测试调用 extractor 重写 sm21。

## 7. v3 validator：结构层与语义层

### 7.1 调用面与错误

```python
@dataclass(frozen=True)
class GtValidationIssue:
    code: str
    pointer: str
    context: Mapping[str, JsonValue]

class GtValidationError(ValueError):
    issues: tuple[GtValidationIssue, ...]  # 依 (pointer,code) 稳定排序

def validate_gt_v3(
    doc: GroundTruthV3,
    *,
    tolerances: GtResolvedToolingTolerancesV1,
    expected_case: str | None = None,
) -> None: ...
```

禁止 warnings-only 降级。一个输入可聚合互不依赖的问题，但若结构失败导致后续计算不安全，可只报结构问题。错误 message 不参与 machine contract，`code/pointer/context` 才参与。

### 7.2 必做语义校验

1. **文档/来源**
   - case 与 caller 期望值一致；source/view ID 与非空 projection surface key 均全局唯一；plan source view 恰一 floor 且 key/family/view-kind/coverage/semantics/azimuth 全 null；elevation view 的 key/family/view-kind/semantics 必填并满足 §8.2 direction/coverage 关系。ref 的 source/view 在文档内存在、handle/subentity 线型合法，plan/elevation ref role 与 view kind 相容。standalone GT 不含 DXF path，故 handle 是否真实存在由 hash-verified extractor 重验，不在 loader 假装可查；
   - source label 无 `/`、`\\`、绝对路径、`..`；source hash 非全零；
   - generator 内 `tolerances` 自身必须通过严格模型及字段关系校验；loader/standalone validator 不把它与当前仓库 config/profile 比较。只有 §10.8 build 末段把它与当轮 resolved profile 逐字段完全相等断言；extractor/validator/Vg/manifest/judge-config/Vg-config hash 均非全零；
   - `content_sha256` 与 canonical recompute 一致。
   - verification methods 按声明顺序 canonical、唯一；candidate 必须 reviewer/date null 且 methods 空；`human_verified` 必须 reviewer/date 非空、日期是真实 UTC calendar date，并恰含 `dxf_topology_roundtrip`、`direct_gt_render`、`overlay_on_original_drawing`、`human_source_comparison` 四项。
2. **楼层**
   - floor ID 唯一，`z_floor_m` 严格递增且楼层竖向区间不重叠；
   - 当前 profile 下所有 floor footprint canonical 后逐点完全相同；不同层退台 fail `gt_profile_floor_footprint_mismatch`；
   - footprint fingerprint 以公开 `footprint_fingerprint` 等价算法计算并一致。
3. **polygon**
   - 按 §4.2；`interior_rings` 非空即 `gt_profile_holes_unsupported`；
   - Shapely 只做独立 topology 检查，不用 `buffer(0)` 修复；面积须大于 topology-area tolerance；
   - 不接受 `MultiPolygon`、GeometryCollection、自触或细碎 sliver。
4. **zone tiling**
   - zone ID 全局唯一；每 zone 在本层 footprint 内；
   - 两 zone interior 交面积不得超过 area tolerance；
   - `unary_union(zones).symmetric_difference(footprint).area <= dxf_topology_area_tolerance_m2`；
   - 仅点/边接触合法，重叠和空洞均 fail；zone_count 从 list 得出，不在 wire 重复保存。
5. **boundary segment**
   - segment ID 全局唯一、floor_id 与容器 floor 一致；p1/p2 非零轴对齐、normal 垂直并与 family 一致；along interval 精确等于边投影；
   - source fingerprint 等于 floor fingerprint；visible intervals 排序、互不重叠、落在 full interval；
   - 用 `doc.generator.tolerances` 对每层 footprint 四方向重新运行 `vg_for_direction`，按结构字段 item-for-item 比较；缺边、多边、可见区间或 depth 漂移均报 `gt_boundary_segments_wire_mismatch`；
   - segment 集合恰好覆盖 exterior ring 的每条 canonical 边一次；不得固定 count=4；
   - `projection_surface_keys` 必须 lexical 排序、唯一；每个 key 指向 family 相同且 `floor_ids` 包含本段楼层的 elevation source view。同一 key 可跨层并含多 depth segment，同一 segment 可属于多个 partial view，空 list 表示无 elevation projection evidence。
6. **opening**
   - opening ID 唯一；floor/segment ref 存在且同层；wire 为未来开放保留 nullable host，但当前 C2 profile 要求非空，且 host-zone ref 存在同层；
   - along interval 严格包含于 segment full interval；宽度大于 endpoint epsilon；
   - `z_interval` 非空时 `floor.z_floor_m <= lo < hi <= z_floor_m+ceiling_height_m`；为空时只表示 vertical truth 不适用/未知，B4a 不把它翻译成 score NA；
   - opening 的 plan source 必须存在；重算“key 命中且 coverage∩visible∩opening 正宽”的 relevant elevation view 集：非空时 z 必填且 `opening_elevation` ref 的 view-id 集必须与它精确相等（每 view 一组，可多 handle）；空集时 z 必须 null 且不得有 elevation ref；
   - host-zone 的 polygon boundary 与 opening 所在 segment 有正宽共线交；唯一性由 extractor 保证，validator 重算；
   - 完全隐藏 segment 仍可宿主 plan opening；“不可见”只阻止 elevation 匹配，不阻止 plan truth。
7. **north axis**
   - `[0,360)`、finite；非空时 `north_axis_source_refs` 至少一项且 role 正确，null 时 refs 必为空，也不得在 generator/source refs 中暗藏派生默认；
   - 不参与 family/segment recompute。

建议稳定错误码前缀：`gt_wire_*`、`gt_source_*`、`gt_polygon_*`、`gt_zone_*`、`gt_boundary_*`、`gt_opening_*`、`gt_hash_*`、`gt_profile_*`。测试断 code/pointer，不断整句英文。

## 8. extraction manifest 与 tolerance config

### 8.1 为什么必须有 manifest

TArch 图纸的六视图是空间排版，不是语义 layer API；当前基于全图 bbox、`PLAN_BAND_Y`、固定位置和固定 role 数组的推断对 L/U 必然不稳。inspector 可报告候选聚类，但人工签收的 manifest 才是 view/floor/role/坐标的权威绑定。

manifest 本身不是 GT，不能放进 GT 根；推荐：

```text
case_tests/test_baseline/gt_sources/<case>/extraction_manifest.json
```

真实 case 的 manifest/源文件进入仓库需单独资产 review；B4a 测试只在 `tmp_path` 生成。

### 8.2 manifest v1 wire

本节所有 model 同样 `ConfigDict(extra="forbid", strict=True)`；无另述的 list 必须按 wire 提供，只有显式 `default_factory` 可省。

```python
class ClipBoxDxf(BaseModel):
    xmin: StrictFiniteFloat
    ymin: StrictFiniteFloat
    xmax: StrictFiniteFloat
    ymax: StrictFiniteFloat               # xmin<xmax, ymin<ymax

class Affine2D(BaseModel):
    # target = A @ [source_m_x,source_m_y,1]；最后一行为隐含 [0,0,1]
    m00: StrictFiniteFloat
    m01: StrictFiniteFloat
    m02: StrictFiniteFloat
    m10: StrictFiniteFloat
    m11: StrictFiniteFloat
    m12: StrictFiniteFloat                # 2x2 determinant != 0

class Affine1D(BaseModel):
    source_axis: Literal["x", "y"]
    scale: StrictFiniteFloat              # != 0
    offset: StrictFiniteFloat

class EntitySelectorV1(BaseModel):
    entity_types: list[Literal["LINE", "LWPOLYLINE", "POLYLINE", "INSERT"]] = Field(min_length=1)
    layers: list[str] = Field(min_length=1)  # exact names
    handles: list[DxfHandle] = Field(default_factory=list)
    handle_mode: Literal["all_matching", "only_listed"]
    min_count: StrictNonNegativeInt
    max_count: StrictNonNegativeInt | None # ge=min_count

class EntityLocatorV1(BaseModel):
    handle: DxfHandle
    subentity_index: StrictNonNegativeInt | None = None
                                           # polyline edge/virtual entity 索引

class PlanOpeningBindingV1(BaseModel):
    opening_id: StableId
    kind: Literal["window", "door"]
    geometry_mode: Literal[
        "closed_outline_bbox", "grouped_line_bbox", "virtual_entity_bbox"
    ]
    span_world_axis: Literal["x", "y"]
    entities: list[EntityLocatorV1] = Field(min_length=1)  # 一组恰为一个 opening

class ElevationOpeningEvidenceV1(BaseModel):
    evidence_id: StableId
    kind: Literal["window", "door"]
    geometry_mode: Literal[
        "closed_outline_bbox", "grouped_line_bbox", "virtual_entity_bbox"
    ]
    entities: list[EntityLocatorV1] = Field(min_length=1)
                                           # 尚不与 plan opening 预配对

class ZoneSeedV1(BaseModel):
    zone_id: StableId
    name: HumanLabel
    role: StableId
    point_world_m: Point2

class PlanViewBindingV1(BaseModel):
    kind: Literal["plan"]
    id: StableId
    floor_id: StableId
    clip_box_dxf: ClipBoxDxf
    world_from_source_m: Affine2D
    footprint_boundary: EntitySelectorV1
    zone_boundaries: EntitySelectorV1
    plan_openings: list[PlanOpeningBindingV1]
    zone_seeds: list[ZoneSeedV1] = Field(min_length=1)
    boundary_reference: Literal["outer_skin", "centerline"]
    default_wall_thickness_m: PositiveFiniteFloat | None

class ElevationViewBindingV1(BaseModel):
    kind: Literal["elevation"]
    id: StableId
    floor_ids: list[StableId] = Field(min_length=1)
    projection_surface_key: StableId
    facade_family: Literal["North", "South", "East", "West"]
    view_kind: Literal["full", "partial"]
    world_along_coverage: GtWorldIntervalV3 | None
    direction_semantics: Literal["building_axis", "true_azimuth"]
    azimuth_deg: Annotated[StrictFiniteFloat, Field(ge=0, lt=360)] | None
    clip_box_dxf: ClipBoxDxf
    world_along_from_source_m: Affine1D
    world_z_from_source_m: Affine1D
    segment_scope_mode: Literal["all_family_segments", "listed_boundary_entities"]
    boundary_entities: list[EntityLocatorV1] = Field(default_factory=list)
    opening_entities: list[ElevationOpeningEvidenceV1] = Field(default_factory=list)

class NorthAxisBindingV1(BaseModel):
    value_deg: Annotated[StrictFiniteFloat, Field(ge=0, lt=360)]
    source_view_id: StableId
    source_entity_handle: DxfHandle

class RasterOverlayBindingV1(BaseModel):
    id: StableId
    source_label: HumanLabel
    source_sha256: Hex64
    view_id: StableId
    pixel_to_source_m: Affine2D

class FloorBindingV1(BaseModel):
    id: StableId
    name: HumanLabel
    z_floor_m: StrictFiniteFloat
    ceiling_height_m: PositiveFiniteFloat

class GtExtractionManifestV1(BaseModel):
    manifest_version: Literal[1]
    case: StableId
    source_id: StableId
    source_dxf_label: HumanLabel
    source_dxf_sha256: Hex64
    native_units: Literal["m", "mm", "cm", "in", "ft", "unitless"]
    metres_per_unit: PositiveFiniteFloat
    geometry_profile: Literal["c2_simple_orthogonal_no_holes"]
    floors: list[FloorBindingV1] = Field(min_length=1)
    views: list[Annotated[PlanViewBindingV1 | ElevationViewBindingV1, Field(discriminator="kind")]] = Field(min_length=1)
    north_axis: NorthAxisBindingV1 | None
    raster_overlays: list[RasterOverlayBindingV1] = Field(default_factory=list)
    manifest_sha256: Hex64
```

约束：

- 每 floor 恰一 plan view；plan view 的 `floor_ids` 等价信息由 singular `floor_id` 给出。elevation view 的 `floor_ids` lexical 排序且唯一，可覆盖一层或多层；elevation view 数量开放，可为 0、1 或多于 4；view clip boxes 先按 unit scale 转 source-m 后，交叠面积不得超过 topology area tolerance；
- floor/view/opening/evidence ID 与 elevation `projection_surface_key` 各自在文档内唯一；所有 floor ref 必须存在；
- selector 的 type/layer/handle list 各自排序唯一；`all_matching` 要求 handles 空，`only_listed` 要求非空且每个 handle 仍满足 type/layer/view，最终 count 必须落 `[min_count,max_count]`（max null 表示无上限）；
- DXF raw coordinate 先逐分量乘 `metres_per_unit` 得 `source_m`，再进 view transform。plan `world_from_source_m` 的 2×2 线性部必须是 exact signed-permutation matrix（只允许 0/±1 的 90°旋转/镜像，无二次缩放/剪切），translation 为 metre；elevation 两个 1D scale 各须 exact ±1 且 source axes 不同；raster `pixel_to_source_m` 可含 pixel scale，但 2×2 determinant 必须非零；
- elevation `projection_surface_key` 可绑定同 family 的多 depth segment；一个 view 不是一条 wall plane。`all_family_segments` 时 `boundary_entities=[]`；`listed_boundary_entities` 时 list 非空并按 source edge ancestry 精确选段；一个段可进入多个 partial view，故 GT 存 plural keys；
- `view_kind="full"` 必须配 `segment_scope_mode="all_family_segments"` 且 `world_along_coverage=null`；`partial` 必须配 `listed_boundary_entities` 与非空 coverage，且 coverage 与至少一个所列段正宽相交。full 表示该 view 覆盖其声明楼层/family 的整个投影域，不表示每条凹段都可见；是否可见仍只看 Vg intervals；
- elevation direction 若为 `building_axis`，`azimuth_deg` 必须 null，family 直接生效；若为 `true_azimuth`，azimuth 必填、GT north axis 必须非空，并精确满足 `azimuth_deg == (north_axis_deg + family_offset) % 360`，其中 offset `{North:0, East:90, South:180, West:270}`。`unknown` 不能进 extraction manifest；无唯一映射即 fail，不用角容差或图名猜；生成的 `GtSourceViewV3` 原样保留 semantics/azimuth；
- 每个 opening group 的成员必须全落在本 view clip 内且 entity kind 符合 geometry mode：`closed_outline_bbox` 只收单个无 bulge 闭 polyline；`grouped_line_bbox` 收 manifest 显式列出的至少四条 LINE/polyline edge，且 `polygonize_full` 后恰一闭合正交 face、零残线；`virtual_entity_bbox` 只收单个可完整 virtualize 的 INSERT，多 locator 只允许同一 INSERT ancestry 下的 virtual primitives。不按空间邻近把散 LINE 猜成一扇窗。plan 的 `span_world_axis` 必须与 world 变换后的一组 outline 对边平行，不用长短边猜轴；elevation evidence ID 只标证据，不预先指定 plan opening，配对仍按 §10.7 全局求解；
- `boundary_reference="centerline"` 时 thickness 必填，先按每条边外法线偏移半厚得到 outer-skin footprint；`outer_skin` 时 thickness 可为 null，若非空只记录证据、不再偏移；
- 当前 `sm21` 的 `0.24m` 语义按 centerline→outer-skin 的 W5 解释保存；不能把总厚度错当单侧偏移量；
- `source_dxf_label`/raster label 只能 basename，且 source label 必须等于实际 `--dxf` basename；manifest hash 的 canonical 规则与 GT 相同，hash 字段置零后计算；
- exact handles 可用于冻结人工挑选；无 handles 时 selector 仍受 view clip、type、layer 和 count 上下界约束，任何额外匹配都 fail，而非悄悄吸收。

### 8.3 tolerance profile v1

`src/configs/judge_gt.yaml` 必须完整写 **七个 B4a 新值**；model 无默认。Vg 两值不在此复制，而由 CLI 边界直接从已收录 `src/configs/correction.yaml` 的两个已登记 key 解析并写进 `GtResolvedToolingTolerancesV1`；B4a 不修改 correction config/loader，也不 import 私有 `_load_cached`。v1 建议冻结为：

```yaml
profile_version: 1
dxf_node_join_tolerance_m: 0.001
dxf_axis_alignment_tolerance_m: 0.001
dxf_topology_area_tolerance_m2: 0.000001
opening_boundary_max_distance_m: 0.400
opening_assignment_tie_epsilon_m: 0.000000001
elevation_match_max_distance_m: 0.400
elevation_match_tie_epsilon_m: 0.000000001
```

前 0.400m 沿用当前 extractor 的 400mm 搜索上限，但现在只作**候选门限**，不能用于把不合法边变合法；它是本稿唯一待真实 sm25/26 校准的数值，见 §15 R2。若真实图需要不同 profile，必须新增 `profile_version` 或 case manifest 显式引用经 review 的 profile；不能通过 CLI 临时 override。

解析签名固定为：

```python
def load_gt_tooling_config(
    gt_config_path: Path,
    vg_config_path: Path,
) -> GtResolvedToolingConfigV1: ...
```

loader 要求 `vg_config_path.resolve()` 正是仓库已收录 `src/configs/correction.yaml`，用 OmegaConf 读 `correction.facade_visibility_depth_epsilon_m` 与 `correction.facade_visibility_endpoint_epsilon_m`，缺 key/非 numeric/非 finite 即 fail；不调用私有 correction loader。它同时记录两个 config **原始文件 bytes** 的 SHA256（注释变化也算 provenance 变化）；纯 extractor/Vg 调用只收 resolved frozen model，不在函数内读 config。config-load 静态关系固定为：两个 assignment tie epsilon 都小于 `min(node_join,axis_alignment)`，两个 Vg epsilon 也小于 node-join；case-build 再逐 opening 断 `width > max(node_join,axis_alignment,vg_endpoint)`，逐 zone 断 `area > topology_area_tolerance`。不使用“足够小”一类无公式判断。resolved 数值全部写入 GT generator 元数据，使重验可复现。

### 8.4 A0 tolerance registry 登记

施工时在 A0 §4 登记下列七行；两条 Vg epsilon 只交叉引用既有 `FACADE_VISIBILITY_*`，不得重复登记或改值：

| name | value | unit | status | profile | hard/warn | 唯一用途/依据 |
|---|---:|---|---|---|---|---|
| `GT_DXF_NODE_JOIN_TOLERANCE` | 0.001 | m | provisional | gt-v3/C2 | hard snap-or-block | 图形导出后端点数值裂隙；只在 polygonize 前聚类，component 直径超限即阻断 |
| `GT_DXF_AXIS_ALIGNMENT_TOLERANCE` | 0.001 | m | provisional | gt-v3/C2 | hard project-or-block | 图形导出后近水平/近竖直噪声；只允许投到唯一较近轴 |
| `GT_DXF_TOPOLOGY_AREA_TOLERANCE` | 0.000001 | m² | provisional | gt-v3/C2 | hard topology | polygonize sliver 与 zone union 面积残差；不修复几何 |
| `GT_OPENING_BOUNDARY_MAX_DISTANCE` | 0.400 | m | provisional | gt-v3/C2 | hard candidate gate | 沿用 sm21 旧 400mm 搜索窗；只筛合法段，不决定 tie |
| `GT_OPENING_ASSIGNMENT_TIE_EPSILON` | 1e-9 | m | provisional | gt-v3/C2 | INVARIANT | 两个最近合法段数值同解门；同解即拒绝 |
| `GT_ELEVATION_MATCH_MAX_DISTANCE` | 0.400 | m | provisional | gt-v3/C2 | hard candidate gate | plan/elevation along endpoints 最大匹配残差；待真实图校准 |
| `GT_ELEVATION_MATCH_TIE_EPSILON` | 1e-9 | m | provisional | gt-v3/C2 | INVARIANT | bipartite 多个等价最优解门；同解即拒绝 |

A0 同节注明这些值 owner 为 judge② tooling，gate① correction 不得消费；登记是全仓容差可审计面，不改变 A0 的 correction 决策矩阵。实现代码中除 config parser、测试输入和 registry 断言外，不得出现这些数值字面量。

## 9. `inspect_dxf.py` v3 preflight

### 9.1 CLI

```text
python scripts/tool_scripts/inspect_dxf.py \
  --dxf <outside-gt-root/source.dxf> \
  [--manifest <manifest.json>] \
  --config <src/configs/judge_gt.yaml> \
  --vg-config <src/configs/correction.yaml> \
  [--json-out <new-report.json>]
```

- 无 manifest：只输出 entity/layer/unit/proxy、闭 polyline、network component 和候选空间 cluster 报告；必须标 `UNBOUND`，退出码 `2`，不能宣称可生成 GT；
- 有 manifest：执行 source hash、unit、view clip、selector count、proxy/export、polygonize preflight；成功退出 `0`；
- `BLOCKED` 退出 `1`，CLI 用法/内部异常退出 `3`；UNBOUND/BLOCKED 在显式 `--json-out` 时可原子写完整诊断 report，但任何路径均不得留下半文件；
- `--json-out` 只允许不存在且不在 GT/gt-sources/case-data 根内的路径；默认只 stdout；
- 不提供 `--fix`、`--write-manifest` 或隐式单位猜测。

### 9.2 检查项

1. DXF 文件 hash 与 manifest 一致；INSUNITS 与 manifest 相容。非 unitless 的 `metres_per_unit` 必须精确等于表 `{m:1.0, mm:0.001, cm:0.01, in:0.0254, ft:0.3048}`，不设单位容差；unitless 只有 manifest 显式正数 scale 才合法。
2. 任一 bound view 内遇到 TArch/proxy/ACAD_PROXY_ENTITY、自定义 object，或被 selector/opening group 引用的 `INSERT` 无法由 ezdxf 完整 virtualize，报 `dxf_requires_graphics_export`；操作建议固定为先在 CAD 中“图形导出/EXPORTTOAUTOCAD”，不得部分读取。view 外对象只列 INFO，不进入真值。
3. 报每 view 内 selector 的 entity handles、type/layer/count、落在 clip 边界上的歧义实体；clip 边界触碰需 fail，不能按实体中心随意归侧。
4. 对 footprint/zone 网络分别执行同 §10 的 snap/polygonize dry-run，报告 polygons/dangles/cuts/invalid rings；任一残留为阻断。
5. 报 plan opening 的合法 segment candidate 数、最近距离与 tie；报 elevation candidate 的 interval/vertical 匹配歧义。
6. 报 north-axis binding 是否真实存在；无 binding 是合法 `null`，不提示默认 0。

inspection report 是诊断，不进入 GT hash；真正 generator 必须重新执行全部检查，不能信任旧报告。

### 9.3 inspection JSON wire

`--json-out` 若给出，严格写下列 schema；stdout 人读摘要由它渲染，不另算结果：

```python
class DxfInspectionIssueV1(BaseModel):
    code: str
    severity: Literal["BLOCK", "UNBOUND", "INFO"]
    view_id: StableId | None
    entity_handles: list[DxfHandle] = Field(default_factory=list)
    context: dict[str, JsonValue] = Field(default_factory=dict)

class DxfViewInspectionV1(BaseModel):
    view_id: StableId
    kind: Literal["plan", "elevation", "unbound_cluster"]
    entity_count_by_type: dict[str, StrictNonNegativeInt]
    entity_count_by_layer: dict[str, StrictNonNegativeInt]
    matched_handles: list[DxfHandle]
    polygon_count: StrictNonNegativeInt
    dangle_count: StrictNonNegativeInt
    cut_count: StrictNonNegativeInt
    invalid_ring_count: StrictNonNegativeInt

class DxfInspectionReportV1(BaseModel):
    report_version: Literal[1]
    status: Literal["PASS", "UNBOUND", "BLOCKED"]
    source_dxf_sha256: Hex64
    native_units_observed: str
    manifest_sha256: Hex64 | None
    judge_config_sha256: Hex64
    vg_config_sha256: Hex64
    proxy_entity_count: StrictNonNegativeInt
    views: list[DxfViewInspectionV1]
    issues: list[DxfInspectionIssueV1]
```

issues 按 `(severity_rank,view_id,code,entity_handles)` 排序；report 不写绝对 path/mtime。`PASS` 要求有 manifest 且无 BLOCK/UNBOUND；无 manifest 恒 `UNBOUND`；有任一 BLOCK 恒 `BLOCKED`。

## 10. `gt_from_dxf` v3 构建算法

### 10.1 CLI 与边界

唯一公开模式：

```text
python scripts/tool_scripts/gt_from_dxf.py \
  --dxf <source.dxf> \
  --manifest <extraction_manifest.json> \
  --config <src/configs/judge_gt.yaml> \
  --vg-config <src/configs/correction.yaml> \
  --out <new-candidate.json>
```

五参数均必填，无默认 case/source/output/config；`--dxf` resolve 后必须脱离 `DEFAULT_GT_DIR` 以及 `case_tests/e2e_tests/*/case_data`（允许位于 `gt_sources`），`--out` 已存在即退出且还必须脱离 GT、gt-sources 与 case-data 三类 protected roots。检查 nearest existing parent 及 symlink 后的 resolved path，不能靠 `..`/symlink 绕过。CLI 成功 stdout 只给 case/schema/hash/count 摘要，stderr 给诊断；失败不留半文件。旧 positional `case`/`--write` 删除，不保留隐藏 alias。

production signatures：

```python
@dataclass(frozen=True)
class InspectionInputs:
    dxf_path: Path
    manifest: GtExtractionManifestV1 | None
    tooling: GtResolvedToolingConfigV1
    implementation_hashes: GtImplementationHashesV1

@dataclass(frozen=True)
class ExtractionInputs:
    dxf_path: Path
    manifest: GtExtractionManifestV1
    tooling: GtResolvedToolingConfigV1
    implementation_hashes: GtImplementationHashesV1

@dataclass(frozen=True)
class PlanZoneExtraction:
    id: str
    name: str
    role: str
    polygon: GtPolygonV3
    source_refs: tuple[GtEntityRefV3, ...]

@dataclass(frozen=True)
class PlanFloorExtraction:
    id: str
    name: str
    z_floor_m: float
    ceiling_height_m: float
    footprint: GtPolygonV3
    footprint_fingerprint: str
    zones: tuple[PlanZoneExtraction, ...]
    boundary_edge_sources: Mapping[
        tuple[Point2, Point2], tuple[GtEntityRefV3, ...]
    ]

@dataclass(frozen=True)
class PlanExtractionResult:
    case: str
    source: GtSourceDocumentV3
    floors: tuple[PlanFloorExtraction, ...]

def inspect_extraction_inputs(inputs: InspectionInputs) -> DxfInspectionReportV1: ...
def extract_plan_geometry(inputs: ExtractionInputs) -> PlanExtractionResult: ...
def extract_gt_v3(inputs: ExtractionInputs) -> GroundTruthV3: ...
def build_gt_v3_candidate(inputs: ExtractionInputs, out: Path) -> GroundTruthV3: ...
```

`extract_gt_v3` 除读取已显式路径外不读 cwd/env/clock/network/random；排序后输出确定。`build_*` 才负责 path policy 与原子写。

### 10.2 单位、view 和实体归一化

1. 先 hash 原始 bytes，再由 ezdxf 读取；manifest hash/units 不符立即停止。
2. 先以轻量 extents 做全图 inventory；bound view 内任何 proxy/custom object 按 §9 阻断。除此以外，只对 selector 实际匹配或 opening locator 明确引用的实体 explode/virtualize 到 primitive，并保留原 handle ancestry；这些 truth entity 的 primitive 不支持即 fail，未匹配的普通标注/家具只入 inspect INFO。
3. 以 manifest clip box 分 view；被真值规则引用的实体必须完全落入唯一 view，跨界/多归属 fail；未被引用且在所有 view 外的实体不参与构建。
4. 在 raw DXF 坐标完成 clip/selector；坐标先乘 manifest `metres_per_unit` 得 `source_m`，再用 view 的 `*_from_source_m` 变换一次到 building world metre；后续 topology 全在 world-m frame，严禁把 unit scale 再塞进 affine 重复缩放。
5. 对一条非零边：若 `abs(dx)<=axis_tol < abs(dy)` 则投竖直，若 `abs(dy)<=axis_tol < abs(dx)` 则投水平；两差均小于等于容差是短边 block，两差均大于容差是斜边 block，不作“较近轴”猜测。投影前后坐标和 source handle 只放诊断，不在 GT wire 双存。
6. node snap 采用 metre 平面的 Euclidean 距离建确定性 connected-component clustering；只有距离 `<= node_join_tolerance` 才连边，且 component 最大 pairwise Euclidean 直径也必须 `<=` 该值，否则 fail，禁止链式漂移；代表点取字典序最小原点而非均值，避免运行顺序差异。

### 10.3 footprint polygonization

对每个 plan view：

1. `LWPOLYLINE` 必须无 bulge/arc，闭合标记或端点在 join tolerance 内闭合；LINE/POLYLINE 拆成线段；
2. footprint selector 网络通过 `shapely.ops.polygonize_full`；`dangles/cuts/invalid` 任一非空即 fail；
3. polygon 面必须唯一。多面时不得取 largest bbox，必须通过 manifest 所有 zone seed 的包含关系唯一选 exterior；仍不唯一即 fail；
4. `boundary_reference=centerline` 时按每边 outward normal 偏移 `thickness/2`，以相邻偏移线交点构造正交 outer-skin；凹角/凸角都做 miter，随后重新跑全部 topology；不用通用 `buffer()` 的圆角/修复语义；
5. canonicalize 成 §4 ring，当前 profile 拒绝 holes/multipolygon；
6. 所有楼层 footprint 必须 pairwise canonical 等同；不相同是 profile block，而非取交/并集；实现不得固定楼层数为二。

### 10.4 zone polygonization

1. footprint exterior 与 zone-boundary selector 一起 noding/polygonize；残线、悬线、重叠线、微小 face 均 fail；
2. 每个 manifest zone seed 必须严格落在唯一 face interior，距任何边大于 node-join tolerance；
3. 每 face 必须恰有一个 seed；无 seed/多 seed 均 fail；role 只来自对应 `ZoneSeedV1`，不按西→东位置分配；
4. 选中 faces 规范化为 zone polygons，并用 §7 tiling 规则重验；
5. 每个 polygon/边界保存贡献 entity refs；不能只记 view 名而丢 handle。

### 10.5 boundary segments 与 surface binding

1. 对 canonical footprint 调用四方向 Vg，tolerance 从 config 显式构造 `VisibilityTolerances`；
2. 物化 §5 字段，使用 GT 自有 public stable-ID 函数；禁止 import Vg 私有 `_segment_geometry_sha256`；
3. 对每个 manifest elevation binding 应用 segment scope：`all_family_segments` 取其 `floor_ids` 内同 family 全部段；`listed_boundary_entities` 以 canonical edge 的 source locator 精确匹配。scope 选到零段、落在声明楼层/family 外的 locator、或同 locator 映到多条段均 fail；
4. 每段把所有命中的 `projection_surface_key` lexical 排序后写入 plural list。零个 view/零 key 合法；多 depth segment 可共用一个 key，一个 segment 也可进入多张 partial view；不能把 view 当 wall plane，也不能造 plan-only 假 key；
5. 所有边都保留，包含完全 hidden；source refs 来自对应 canonical exterior edge 的 line ancestry。

### 10.6 plan opening → 最近合法 boundary segment

先按 `PlanOpeningBindingV1` 取证据组：closed outline 用单 polyline bbox；grouped-line mode 先严格 polygonize 再取唯一 face bbox；virtual mode 对唯一 INSERT 完整 virtualize 后取所有 primitive union bbox；空 bbox、arc/bulge、非平面、跨 view、group 残线或 locator ancestry 不一致均 fail。经 plan affine 转 world 后，显式 `span_world_axis` 上的 min/max 是 opening span，正交轴 bbox 中点是墙法向中心线；span 宽度必须大于 endpoint epsilon。opening wire ID/kind 直接取 manifest binding，source refs 保留所有 locators。再找同层候选，合法候选必须同时满足：

1. opening 主轴与 segment 平行，偏轴误差不超过 axis tolerance；
2. opening 的完整 along span 精确落入 segment full interval；Vg endpoint epsilon 只做零宽/近碰撞退化门，不允许裁切或放宽包含；
3. 法向距离 `<= opening_boundary_max_distance_m`；
4. opening 与 segment 共属 footprint/zone 的合法边界；不能跨 notch 空隙“投影”到远边；
5. kind 与 manifest binding 相符，locator 未被另一 opening 重用且全属本 view。

在合法集内按 `(normal_distance, endpoint_residual, segment_id)` 排序；第一、第二在 distance 和 residual 上均落入 tie epsilon 时 fail `opening_segment_assignment_ambiguous`，不能用 ID 消歧。无候选也 fail。选中后将 along 端点投影到 segment axis，保留原实体 ref。

`host_zone_id` 由该 segment 与 zone boundary 的正宽共线交唯一决定：当前 profile 必须恰有一个 zone，写其 ID；多 zone/零 zone 均 fail。nullable 槽只为未来非分区 exterior object 留 wire seam，本批 extractor 不产 null。不得用 opening 中心点最近 zone 猜测。

### 10.7 elevation 匹配与 plan-only z

elevation evidence group 按与 plan 相同的 closed-outline/grouped-line/virtual bbox 规则独立取框；view 的两个 `Affine1D.source_axis` 必须不同，再分别把 bbox 两端转为升序 `(world_along_interval,z_interval)`。空/零宽/零高均 fail；z 必须恰好落入该 view 声明楼层集中**一个**楼层的竖向区间，跨层或命中零层/多层均 fail，该楼层即 evidence floor。随后：

- 只允许匹配同 floor，且该 view key 出现在 segment 的 plural key list 中、opening plan interval 与 `segment.visible_intervals ∩ view.world_along_coverage` 有正宽交的 opening；full view 的 null coverage 在该交式中按 segment full interval 处理；
- cost 为 along endpoints 的 L∞ 残差；超过 `elevation_match_max_distance_m` 不合法；
- 对整个 view 做确定性最小代价 bipartite assignment，不逐窗贪心；存在多个总成本在 tie epsilon 内的最优解则 fail；
- 一个 plan opening 在**每个 view** 最多匹配一个 elevation evidence；每个 manifest evidence group 恰好匹配一个 plan opening，任何额外 evidence 都 fail。同一 opening 可由多个 full/partial view 重复观察，所有匹配所得 z interval 必须精确一致（无已登记 vertical-agreement tolerance，故不近似平均），source refs 全部保留而 wire 只存一份一致 z；
- plan opening 无任何 projection key、没有覆盖它的 elevation view，或在所有相关 view 中均不与 segment visible interval 正宽相交时，不强求 elevation；其 `z_interval=null`，且只留 plan ref。反之，每个覆盖且可见的相关 view 都必须恰好匹配一项 evidence，任一缺失即 fail；
- 禁止平均窗高、复制相邻 z、楼层默认 sill/head。未来 assumed knowledge 由 Va/B4b provenance 流处理，不能写进 GT observed truth。

这正是 sm26 U-notch 内墙 plan window 的预定表达：x/width 可评分，z 暂无 GT claim；B4a 只提供 nullable wire，B4b 决定该 claim denominator/NA。

### 10.8 north-axis、来源与最终自检

- manifest `north_axis=null` → GT `north_axis_deg=null` 且 `north_axis_source_refs=[]`；
- 非空时确认 handle 位于绑定 view 且 source ref 可回溯；inspector 把该实体 geometry/text 与 manifest 数值并列给 human review。`dxf_axis_alignment_tolerance_m` 是长度，禁止拿来比较角度；B4a 不新增未经实图校准的角容差，也不从标题文字、页面旋转或 block 朝向静默猜 θ；
- source document 只写 label/hash/unit/scale，不写本机 path；所有 ref 必须可回到 source/view/handle；
- build 入口先解析当轮 resolved tooling profile，并把其 tolerance 值逐字段写入 `doc.generator.tolerances`；构建完整文档、计算 fingerprint/IDs/sort/hash 后，必须先断言 `doc.generator.tolerances` 与该 build 调用实际使用的 resolved profile 逐字段完全相等，不等即 fail。此断言只存在于 `extract_gt_v3` 的 build 末段，不得进入任一 loader。
- 随后调用独立 `validate_gt_v3(doc, tolerances=doc.generator.tolerances, ...)`；再 canonical dump/reload，并仍用 reload 后的 `doc.generator.tolerances` validate。两个 typed object 和 canonical bytes 必须相同，才允许 candidate writer 落盘。

## 11. render 与 overlay

### 11.1 统一 render model

新增内部 primitives，避免 renderer 再直接读 schema dict：

```python
@dataclass(frozen=True)
class RenderPolygon:
    id: str
    label: str
    role: str
    exterior: tuple[Point2, ...]

@dataclass(frozen=True)
class RenderSegment:
    id: str
    floor_id: str
    facade_family: Literal["North", "South", "East", "West"]
    p1: Point2
    p2: Point2
    depth_m: float
    visible_intervals: tuple[tuple[float, float], ...]
    projection_surface_keys: tuple[str, ...]

@dataclass(frozen=True)
class RenderOpening:
    id: str
    floor_id: str
    kind: Literal["window", "door"]
    segment_id: str
    world_along_interval: tuple[float, float]
    z_interval: tuple[float, float] | None

@dataclass(frozen=True)
class PlanRenderFloor:
    floor_id: str
    z_floor_m: float
    ceiling_height_m: float
    footprint_exterior: tuple[Point2, ...]
    zone_polygons: tuple[RenderPolygon, ...]
    boundary_segments: tuple[RenderSegment, ...]
    openings: tuple[RenderOpening, ...]

@dataclass(frozen=True)
class ElevationRenderSurface:
    key: str
    source_view_id: str
    floor_ids: tuple[str, ...]
    facade_family: Literal["North", "South", "East", "West"]
    view_kind: Literal["full", "partial"]
    direction_semantics: Literal["building_axis", "true_azimuth"]
    azimuth_deg: float | None
    world_along_coverage: tuple[float, float] | None
    segments: tuple[RenderSegment, ...]
    openings: tuple[RenderOpening, ...]

@dataclass(frozen=True)
class GtRenderModel:
    case: str
    source_schema_version: Literal[2, 3]
    north_axis_deg: float | None
    floors: tuple[PlanRenderFloor, ...]
    elevation_surfaces: tuple[ElevationRenderSurface, ...]

def gt_to_render_model(doc: GtDocument) -> GtRenderModel: ...
def render_plan_model(model: GtRenderModel) -> Image.Image: ...
def render_elevation_model(model: GtRenderModel) -> Image.Image: ...

# 保留当前脚本内可测入口；先 load/validate/adapt，再调用 model renderer
def render_plan(gt: dict) -> Image.Image: ...
def render_elev(gt: dict) -> Image.Image: ...
```

- v3 adapter 直接转 polygon/segment；
- v2 adapter 保留当前 W/D、rect、四 facade 解释，仅服务 legacy；不得称其为 v3 migration；
- renderer 只收 `GtRenderModel`，禁止 `gt.get("footprint",{}).get("W_m")` 一类 schema probing。

### 11.2 `render_gt.py`

CLI 保持盘上真实接口：

```text
python scripts/tool_scripts/render_gt.py <case-name-or-gt-json-path> [--out-dir <dir>]
```

positional 不带 suffix 时按 case name 解析 `DEFAULT_GT_DIR/<case>/gt.json`，带 suffix 时走 `load_gt_file()`；临时候选 path 模式必须显式给 `--out-dir`，防止默认写回 GT 根。v3 行为：

1. header 显示 schema、content-hash 短码和 verification；candidate 在两图上高对比水印 `CANDIDATE — NOT BASELINE`，不可由 CLI 关闭；
2. 每 floor 单独 plan panel，PIL world→pixel transform 从 polygon min/max 加比例 margin 计算，x/y 使用同一 pixels-per-metre，绝不拉伸成 bbox；
3. 画 footprint exterior、zone polygon 填色/label、每条 segment 的 ID 短码/family/depth；visible 实线、hidden 虚线；
4. opening 沿其实际 segment 放置；不得按 bbox family 重新定位；plan-only z 不影响平面图；
5. elevation panel 动态按所有 source elevation view 的 `projection_surface_key` 排序创建，不断言四张；同 key 展示命中的多个 depth plane，partial panel 按 `world_along_coverage` 裁窗并画截断标记，标注 visible/hidden；无 key 的段只在 plan 出现；
6. `z_interval=null` 且段属于 surface 时在对应 legend 标 `PLAN-ONLY / Z UNSET`；段无 surface key 时只在 plan legend 标，均不写 `NA` 分数；
7. north axis 非空时在 plan 画 building +Y 与 true/project North 两箭头；null 时只画坐标轴，不画推测北；
8. 保持 `gt_plan.png`、`gt_elev.png` 两个输出名，内部 panel 数由 model 决定；无 elevation surface 时仍产带明确 `NO ELEVATION SOURCE BINDING` 的 `gt_elev.png`，不伪造四面板。

### 11.3 `render_gt_overlay.py`

v3 overlay 不得使用当前 density auto-calibration/mirror 常量。必须有 manifest 的 `RasterOverlayBindingV1`：

```text
# legacy，保持现 positional 行为
python scripts/tool_scripts/render_gt_overlay.py <case>

# v3 candidate；不得同时给 positional case
python scripts/tool_scripts/render_gt_overlay.py \
  --gt-file <candidate.json> --manifest <manifest.json> \
  --raster-root <original-view-dir> --out-dir <new-dir>
```

v3 核签名：

```python
def build_gt_overlay_images_v3(
    doc: GroundTruthV3,
    manifest: GtExtractionManifestV1,
    *,
    raster_root: Path,
) -> Mapping[str, Image.Image]: ...       # key = manifest view_id

def write_gt_overlay_images_v3(
    images: Mapping[str, Image.Image],
    out_dir: Path,
) -> tuple[Path, ...]: ...                # out_dir 必须不存在；原子建目录/清理失败残留
```

1. 重算 raster SHA；不符 fail；
2. `source_label` 只能作为 basename 在显式 raster root 下 resolve；symlink/`..` 不得逃逸。通过 invert `pixel_to_source_m` 与对应 plan `world_from_source_m`/elevation 两个 `*_from_source_m`，把 GT polygon/segment/opening 反投影到像素；
3. 逐 view 动态输出 `overlay_<sanitized-view-id>.png`；plan 可叠 footprint/zone/opening，elevation 可叠 segment visible intervals/opening z；sanitize 后重名 fail；
4. 变换矩阵 singular、超图界、两个绑定竞争同 view 均 fail；
5. candidate overlay 同样带不可关闭的 `CANDIDATE — NOT BASELINE` 水印与 content-hash 短码；
6. legacy v2 overlay 继续走原 density wrapper，以 sm21 测试锁住；v3 代码不得 fallback 到该 heuristic。

### 11.4 `render_grade.py` 边界

B4a 只读盘核实了 `render_grade.py` 仍以 W/D/四 facade 画 quiet GT base；本批不修改也不让它读取 v3。B4b 接段级 scorer 时必须同时升级 grade transform/sidecar/cache，不能把 B4a 的 human-only `render_gt` 当 grade render 已完成。

## 12. 合成 L/U DXF round-trip 验收夹具

### 12.1 夹具原则

- pytest 运行时用已存在依赖 `ezdxf` 在 `tmp_path` 生成；不提交 `.dxf/.png/.json` fixture；
- 同时生成 manifest/config，source/out 均在临时 GT 根之外；
- 两层 footprint 完全一致，至少两个 zone，全部以闭 LWPOLYLINE/LINE 网络表达；
- 所有尺寸使用不整齐但可精确表示的 metre 值，防止只对整数 bbox 过测；
- entity insertion 顺序、ring 起点、CW/CCW、LINE/LWPOLYLINE 混合做参数化扰动，canonical bytes 不变。

### 12.2 L case

建议 exterior：

```text
[(0,0),(8,0),(8,3),(4.5,3),(4.5,7),(0,7)]
```

必须覆盖：

- segment 数大于 4；同 family 有多个 depth；该 L 的同 family 投影仅端点相接，因此所有段 full-visible，测试不得硬造遮挡；
- 三个以上 zone polygon 精确 tile footprint；role 顺序故意不按空间排序；
- notch face 有 plan/elevation window，最近合法 segment 不是 bbox 外边；
- 两个同 family segment 共用一个 projection view，另一个 family 用两张 partial view，使动态 elevation panel 总数不等于 4，证明 view≠wall plane 且 segment↔view 非一对一；
- `north_axis_deg=27.5`，round-trip 不归零、不四舍五入、不重标 facade。

### 12.3 U case

建议南侧 notch exterior（保持 CCW canonical 后形状等价）：

```text
[(0,0),(3,0),(3,3),(7,3),(7,0),(10,0),(10,8),(0,8)]
```

必须覆盖：

- South 有前沿与 notch 内墙多 depth segment；
- East/West 视向中 notch 侧边与外边投影重叠，至少一条 inner segment 完全/部分 hidden，锁住 Vg wire 不得丢 hidden 段；
- 一个 inner-notch plan window 只能关联内段，z 无 elevation，因此 `z_interval=null`；
- 另一个 observed 外窗有完整 elevation z，用于混合 nullable 测试；
- north axis 为 null；
- 交换 notch 两侧实体顺序仍稳定；制造等距双候选时必须 fail ambiguous。

### 12.4 round-trip 定义

每个 case 完整链：

```text
generate DXF+manifest
  -> inspect(manifest-aware) PASS
  -> extract typed GT
  -> validate
  -> canonical candidate write
  -> load_gt_file
  -> validate/recompute Vg/hash
  -> render_gt + overlay to tmp
  -> canonical bytes exactly equal after reload
```

“round-trip PASS”不是仅比较 W/D 或 opening count；必须逐点 polygon、zone tiling、逐 segment depth/visible intervals、opening ref/interval/z-null、north/source/hash 全等。

## 13. 分阶段施工与独立验收

### Phase A — schema、loader、config、dual-read

**施工**：新增 `gt_schema.py`/`gt_manifest.py`/config；改 `gt.py`；不碰 extractor/render。

**验收**：v3 正负 wire、semantic validator、canonical hash、path traversal；sm21 v2 raw equality/SHA 不变；unknown schema fail。

**独立合并条件**：旧测试全绿，新 API 无默认 scorer caller，工作树无资产变更。

### Phase B — inspector、manifest、plan polygonize

**施工**：扩 inspector；新增 extraction core 的单位/view/snap/polygonize/zone；先产内部 strict `PlanExtractionResult`（floors/footprints/zones/source ancestry），不伪装成尚缺 segment/opening/generator hash 的合法 `GroundTruthV3`。

**验收**：L/U 两层 footprint+zones；dangle/cut/bulge/proxy/unit/hash/view-overlap/seed ambiguity 负测；禁止 largest-bbox fallback。

**独立合并条件**：inspection 无 manifest 只能 UNBOUND；不写默认 GT；Phase A 回归全绿。

### Phase C — Vg segments、opening、elevation、north、candidate writer

**施工**：接公开 Vg、稳定 segment、最近合法段、bipartite elevation、source refs、hash/atomic writer。

**验收**：L/U 完整 round-trip；多 depth/hidden/plan-only z/nonzero north；tie/no-candidate/source isolation/overwrite 全负测。

**独立合并条件**：两次不同 entity 顺序产出 canonical bytes 相同；无 v3 baseline 文件。

### Phase D — render/overlay 与 B4b seam

**施工**：统一 render model；升级两 renderer；保留 v2 adapter；新增只读 B4b contract fixture factory（测试代码内）。

**验收**：v3 动态 panels、实际 polygon、segment/opening placement、affine raster hash；v2 primitive/pixel 关键断言；render_grade 未改。

**独立合并条件**：B-03 关闭证据齐备；discipline scan 证明 gate 隔离和固定四面假设未进入 v3 路径。

每 phase 一个独立 PR/commit 亦可；不得为等待真实 `sm25/sm26` 把合成验收挪到后面。

## 14. 测试矩阵、preflight 与交付门

### 14.1 schema/loader 单测

- 接受完整 v3 candidate/verified、north null/非空、z null/非空、>4 segment、动态 surface；拒 candidate 混入 reviewer/method、verified 缺四项签收法；
- 拒 extra field、string number/bool、NaN/Inf、闭环重复首点、CW/nonorthogonal/self-touch/hole/multipolygon；
- 拒 zone gap/overlap、fingerprint/hash mismatch；seed drift 属 manifest/extractor 测试；
- 拒 segment family/normal/p1顺序/along/depth/visibility/source fingerprint 任一漂移；
- 拒 opening cross-floor/ref missing/out-of-span/ambiguous host/z越层；
- schema `2`/`3` integer only；当前 v2 fixture read；缺版本、v1 与未知版本 fail；
- 打乱 DXF entity/selector 输入顺序或 ring 起点，extractor 的 canonical hash 不变；手工打乱已落盘 GT list 则以 `gt_wire_noncanonical_order` 拒绝；任一真值坐标变化会改 hash；
- `load_gt` missing→None、v2 raw 不变、v3 报 `gt_v3_requires_typed_consumer`；file typed loader 接 candidate，default-root typed loader 拒 candidate/接 verified；bad JSON/path traversal fail。
- 构造“存档 `doc.generator.tolerances` 与当前仓库 resolved profile 不同”的旧 verified v3：两个 typed loader 仍须仅用存档值通过 L2/Vg 重算，且测试以 monkeypatch 证明 load 路径未读 tooling config；篡改存档 tolerance 但不重算对应语义/hash则 fail。
- build 测试将当轮 resolved profile 与待写 `doc.generator.tolerances` 制造单字段差异，必须在 writer 前 fail；相等时通过最终 dump/reload 自检。该断言不得复用于 load 测试。

### 14.2 extractor/inspector 单测

- §12 L/U 完整链；closed LWPOLYLINE 与 LINE network 等价；
- TArch proxy/未展开 INSERT/bulge/斜边/短边/链式 snap/残线/重复线/clip 边界实体 fail；
- unitless without scale、source hash mismatch、manifest hash mismatch、selector count/zone-seed drift fail；
- floor/role 不按位置推断；更换 floor/view ID 后 wire 只发生预期 ID/hash变化；
- building-axis view 接受 null azimuth；true-azimuth view 用 `(θ+offset)%360` 唯一回映，缺 θ/符号反向/unknown semantics 均 fail；
- centerline 0.24m 只外偏 0.12m，凹/凸角 outer-skin 坐标精确；outer_skin 模式不二次偏移；
- nearest legal segment、notch crossing、tie、hidden plan opening、elevation global assignment；
- writer 拒 existing、GT root、gt-sources root、case data root，失败零残留；
- inspector 与 generator 对同一错误给同 code，但 generator 必须自行重验。

### 14.3 render 单测

- plan path vertices 不是 bbox；zone 面积/label 数正确；L/U concavity 在 primitive tree 中可见；
- candidate 两图水印不可关闭，verified 显示 reviewer/date/hash 且无 candidate 水印；
- segment count/visible-hidden style/depth labels 与 model 一致；
- panel count 等于 surface key 数，不等于常数 4；partial coverage 之外几何被裁且有截断标记；
- inner-notch opening 落内段；plan-only z 文案存在且无 `NA score`；
- north 27.5°箭头按 `(-sin θ, cos θ)` 数值正确，null 不画真北；
- overlay affine 的连续坐标正反算误差小于显式 endpoint epsilon；最终 PIL 像素落点误差不超过 1px；raster hash mismatch fail；
- v2 sm21 当前关键尺寸、zone/opening count、四 panel legacy 行为不变。

### 14.4 discipline/仓库门

- production 扫描：除 `src/agent/judge` 和 tool scripts 外无新增 `gt` path/import；executor/correction/reading 无 judge import；
- v3 路径 AST/源码禁用 `_FLOOR_OF`、`_ROLES`、`PLAN_BAND_Y`、`largest bbox`、`range(4)` 和固定四 panel 构造；schema/manifest 的闭 `FacadeFamily` Literal 与四方向 Vg 循环是允许的几何 vocab，不得被误报；
- diff 中无 `case_tests/test_baseline/gt/**`、`gt_sources/**`、golden、PNG、DXF 变动；
- `render_grade.py`、score modules、run-stage、Va/completeness 未改；
- 全部输出固定排序，重复运行 hash 相同。

### 14.5 施工前 preflight（只查已有依赖）

preflight 不安装、不升级、不联网：

```bash
python -c 'import pydantic, shapely, ezdxf; from PIL import Image; from omegaconf import OmegaConf'
python -c 'from src.agent.correction.facade_visibility import vg_for_direction, VisibilityTolerances'
python -c 'from src.agent.correction.footprint import footprint_fingerprint'
python -c 'from src.agent.correction.config import load_core_tolerances; load_core_tolerances()'
test -f src/configs/correction.yaml
git status --short
```

若依赖缺失，停止并报环境 blocker；不得在 B4a 顺手改 lockfile。`git status` 用于记录并避开用户已有脏改，不要求清空工作树。

### 14.6 build 后检查（与 preflight 分开）

每 phase 先跑定向测试，再跑相关回归；最终门建议：

```bash
pytest -q tests/test_gt_schema.py tests/test_gt_from_dxf.py tests/test_inspect_dxf.py
pytest -q tests/test_gt_render.py tests/test_gt_overlay.py tests/test_gt_discipline.py
pytest -q tests/test_reading_score.py tests/test_elevation_score.py tests/test_judge_batch_b.py tests/test_judge_harness.py
pytest -q
git diff --check
git status --short
```

最终人工核验：打开 tmp L/U plan/elevation/overlay，逐项对 notch、multi-depth、hidden、inner window、plan-only z、north arrow；记录 canonical hashes 与命令，但不把图片提交为 golden。

## 15. B4a→B4b 交接合同与 review-ask

### 15.1 B4a 给 B4b 的稳定输入

B4b 只能依赖：

- `GroundTruthV3` typed loader；
- verification status 与 generator/source/content hashes；
- per-floor canonical footprint/zones；
- 完整 boundary segment list（含 hidden、depth、visible intervals、0..N surface keys）；
- `visible_intervals = Vg(footprint, direction, doc.generator.tolerances)`：它是 Vg 派生量，不是独立观察真值；B4b 设计可见性类 claim 的判分政策时不得把它当作独立证据源，证据独立性只由 verified 门的人工 overlay 签收提供；
- opening 的 floor/host/segment/along/nullable-z/source refs；
- optional north axis；

B4b 仍必须自行定义并实现：segment matching/scoring、每 claim denominator、z-null 的 `NOT_APPLICABLE` 表达、completeness user/dataset 生成、score sidecar + GT hash、policy/schema bump、render_grade v3。B4a 不输出看似半成品的 `scoreable`、`claim_status`、`denominator` 或 `completeness` 字段。

### 15.2 提升真实 v3 GT 的联合门

真实 `sm25-L/sm26-U` 只有同时满足以下条件才能写默认 GT 根：

1. source/manifest 资产 review 已签收；
2. B4a 全链从真实图通过且 human overlay 签收；
3. B4b scorer/sidecar/cache/render_grade 已接 v3，旧 scorer 不会误读；
4. expected policy 与 denominator/NA 已 review；
5. 独立 reviewer 在资产批写入 `human_verified` 四项方法/reviewer/date 并重算 content hash；
6. baseline/golden 变更在独立资产批次中明确列出，不夹带在代码批。

`sm24` 是否补 GT 不属于该联合门的默认工作；需另开请求。

### 15.3 review-ask 与主控裁决登记

| ID | 不确定处 | 本稿建议 | 主控裁决 |
|---|---|---|---|
| R1 | 盘上 legacy `sm21_anchor/source.dxf` 仍在 GT 根，和新源隔离原则不一致 | B4a 不搬；另开 data-only 批迁到 `gt_sources/sm21_anchor/`，不留兼容 symlink | **采纳**：B4a 不搬；迁移另开用户可见、上排工表的 data-only 资产批；迁到 `gt_sources/` 后**不留兼容 symlink**。 |
| R2 | 0.400m opening/elevation 搜索上限来自 sm21 旧 extractor，尚无 sm25/26 实图校准 | 合成验收先冻结 profile v1；真实图若证明不合适，以 review 后 profile v2 调整，不允许 case CLI override | **采纳**：0.400m 冻结为 profile v1 候选门限；sm25/26 实图到盘后经 review 才可出 profile v2；禁止 CLI 临时 override。 |
| R3 | sm25/26 的指北针究竟是 vector、block 还是文字元数据尚无实图，无法安全冻结角度自动测量容差 | 角度语义直接沿用 E4（真北→building +Y 顺时针）；B4a 只校验 manifest 数值范围、handle 存在并供 human overlay，不自动量角。实图若要求自动量测，另提带角容差/A0 登记的小批 | **采纳**：不自动量测；使用 manifest 数值 + human overlay。实图若需自动量测，另开带角容差及 A0 登记的小批。 |
| R4 | 真实 TArch DXF 是已图形导出的 plain entities，还是仍含 proxy/custom object，尚无 sm25/26 文件可查 | 维持 fail-closed：只接收图形导出稿；不在 B4a 实现 TArch 专有解析 | **采纳**：维持 graphics-export-only、fail-closed；不解析 TArch 专有对象。 |
| R5 | git 历史曾有缺 `schema_version` 的 sm21 草稿，但当前工作树没有可支持的 v1/无版本资产 | loader 只 dual-read 盘上 v2/v3，缺版本/v1 fail；历史支持须先收原字节 fixture 另审，不能 `extra=allow` 猜 | **采纳**：loader 只 dual-read 当前 v2/v3；无版本/v1 fail-closed；历史支持须先收录原字节 fixture 并另审。 |

R1–R5 已全部按 r1 主控裁决关闭；本稿的范围、wire、算法和分阶段验收均为可直接施工定案。review 不应借 B4a 扩入 B4b score/NA/completeness。

## 16. Done 定义

B4a 完成必须同时满足：

- schema v3 能表达并严格验证 L/U 多边形、zone、逐段、opening ref、nullable z、optional north；
- schema 2/3 dual-read，当前 sm21 v2 资产字节零变化；
- 合成 L/U DXF 从 inspect 到 extract/load/render/overlay round-trip 完整通过；
- extractor 无矩形/固定楼层/固定 role/bbox facade/自动提升假设；
- renderer 真实显示 concavity、多 depth/hidden/inner opening，B-03 关闭；
- GT 仍只在 gate②，B4b seam 清楚且未越界；
- 全测试通过、重复 hash 确定、无 golden/gt/DXF/PNG 或其他资产变更。

达到以上条件后，B4a 可标 done；真实 `sm25/sm26` GT 的生成与签收仍是后续联合门，不是 B4a 代码完成的阻塞项。
