# C2 B2 细稿 v6（定稿）：schema v3 冻结 + per-floor footprint 槽位 + floor_footprint 单一 helper + 双路径同一 finalize

> **版本史**：v1 2026-07-10 → sol+max r1 **REWORK 8**（[r1](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review.md)）→ v2（8 全采纳；子类族变体）→ r2 **REWORK：3 CLOSED/5 PARTIAL + 新 7**（[r2](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r2.md)；子类族与 v3-随-B2-发射获准）→ v3（7 全采纳）→ r3 **REWORK：r2 2 CLOSED/5 PARTIAL + 新 5（4 BLOCKER/1 HIGH）**（[r3](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r3.md)）→ v4 = r3 5 条全采纳 + 恢复累计式自包含全文（自包含判过）→ r4 **REWORK：r3 4 CLOSED/1 PARTIAL + 新 3（R4-X-01 共同 BLOCKER / R4-B2-01 HIGH / R4-B2-02 LOW）**（[r4](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r4.md)）→ v5 = r4 3 条全采纳（共同 wire 归 B-M 唯一规范 owner、B-M 先落 B2 消费；feature-state 两型 strict wire；路由 route id 化）→ r5 **APPROVE-WITH-CHANGES：r4 2 CLOSED/2 PARTIAL + 2 HIGH changes、零 BLOCKER**（[r5](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r5.md)）→ v6 = R5-X-01 补丁机械并入（correction writer 必设 artifact_contract=correction_b2_v1 + stage_version 冻结值 "2"、交叉负例入测试）→ r6 短文字复核 **APPROVE（两补丁 CLOSED、交叉一致、"可进入既定施工顺序、无需 r7"**，[r6](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r6.md)）——**本稿定稿**。施工前置=B-M 共同 wire 先合入并复核。
> **上位设计** = [c2_full_unlock_design.md](c2_full_unlock_design.md) v2.2（定稿）§Schema v3 + §批次重排 B2 行（工作量 L，代码级细稿）；基底 = [c2_orthogonal_polygon_design.md](c2_orthogonal_polygon_design.md) D3。
> **纪律**：细稿→审（sol 最顶档）→执行（执行档）→复核；本稿只放行 B2 施工。现状 file:line 以 `7422f42` 为准。

---

## 0. 范围与非目标

**In（B2 施工面）**：
1. correction **schema v3 类型一次冻结**：strict wire 子类族（全部槽位，含本批不填充的 FacadeSegment/north_axis/knowledge_ref）；
2. **typed/raw 双入口收口**：`ensure_corrected_geometry` 信任边界（无 no-op 快路）+ draw parser / final validator 分立；
3. **capability 检查从 `version=="2"` 硬编码改 feature 声明**（4 处点名修，未知版本 fail closed）；
4. **`CorrectionTarget` 单一目标选择点**贯穿 prompt/validator/parse/finalize/gate/writer（矩阵：rectangular→v1、orthogonal_polygon→v3、v2 只读 legacy）；
5. **`floor_footprint` 单一 helper** 贯穿 core/validator/naming/audit/render/judge（十路路由）；
6. **双路径同一 correction-finalize**（修上位闭 B-02）+ **attempt bundle 身份**（FinalizeResult 序列化合同、FeatureStateClaims/FeatureStatesArtifact 两型 strict wire、StageRecordV2.artifact_hashes、promote-on-accept）——**批次依赖（r4 裁决）：RunManifestV2/StageRecordV2 共同 wire 由 B-M 细稿 §5.1 唯一规范拥有并先落，B2 消费；"先合者建"废除；DAG 加 B-M→B2 边（登记 plan.md，细稿阶段依赖细化非批范围变更）**；
7. **pre-core evidence-debt 对等 + debt_id 主键化 + strict resolution 类型**；
8. **v3 生产发射**（prompt 版本专属 schema；LLM 义务=Floor.id/floor_id/footprint；段/north_axis 强制留空；feature-state 机读）；
9. v1/v2 **legacy 零改动**（legacy 类不加任何字段，bytes/hash 结构性不变）；
10. claims 词汇表常量模块。

**Out（留后批，本批只留槽位/接缝）**：FacadeSegment 填充与可见性（Vg）、窗段 ref 解析与宿主重构（B5）、north_axis 填充/EP 出口（E4-output-contract/B-O）、polygon 级 envelope 变形（B2b；非矩形 ring 的 envelope 轴=整轴 unsupported）、coverage 门 v2 面积守恒容差（B3）、gt/scorer per-claim（B4a/B4b）、知识表 loader（独立细稿门）、B-M manifest 消费。

## 1. 现状对账（累计，全部经 r1–r3 核证）

| # | 事实 | 位置 |
|---|---|---|
| 1 | `CorrectedGeometry`：顶层 `footprint_x/footprint_y` bbox（全楼共用）、`Floor{name,z_floor,ceiling_height,cells}` 无 id 无 footprint、全模型 `extra="allow"` | [schema.py:32-83](../../src/agent/correction/schema.py) |
| 2 | 4 处 `schema_version_of(geom) != "2"` 硬编码 | deterministic.py:751-754 · geometry_validator.py:65-68 · pipeline.py:481-485 · modelling.py:392-395 |
| 3 | capability 已有 version→shapes / profile→shapes 表 + subset 门 + `require_supported_geometry_contract`（未知版本 fail closed）：**v1 只声明 rectangular；v2 声明 {rectangular, orthogonal_polygon}；rectangular profile 只允许 rectangular** → **v2/v3 artifact 在默认 rectangular profile 下必被 subset 门拒** | [capability.py:21-75](../../src/agent/geometry/capability.py)；默认 profile [policy.py:37-44](../../src/agent/execution/policy.py) |
| 4 | footprint 消费点 50 处/10 文件（词法计数；语义 writer 见 §4 路由表）：deterministic 跨层锚 :778-800/envelope :591-721/snap；geometry_validator coverage `box(footprint)` :85-88；facade.py frame bounds :72-83；envelope.py :270；modelling `_zone_quadrant` :150-154,458；judge correction_score dict 兜底 :237-273；checks/correction 宽深 :188-193 + frame cross-check :339；render_corrected_geometry / render_elevation_windows dict 消费 | 全清单=审请求单附录 |
| 5 | **B-02**：pipeline 路径 `load_core_tolerances()`→`extract_authoritative_envelope`→`apply_deterministic_core(geom, tol, envelope, profile)`（pipeline.py:921-933）；flow `_draw_correction` 只 `apply_deterministic_core(geom, capability_profile=…)`——tol 走 core 自载默认（等价，deterministic.py:724-738），**envelope 是真缺口**（run_stage.py:181-183） | — |
| 6 | draw 门差异是设计内：flow schema-only 内校验 + 外置 gate①（attempts 记账），pipeline `_make_correction_validator` 内置语义校验（run_stage.py:157-159 注释）——不在 finalize 统一范围 | — |
| 7 | polygon 工具族可复用：`cell_has_polygon/validate_cell_polygon/normalized_ccw_polygon/cell_polygon/cell_axis_values`；**cell 路径 core 内 canonicalize CW/closed 并记 audit** | cell_geometry.py · deterministic.py:755-772 |
| 8 | 跨层 reconcile per-floor 桶按 `fl.name` 作键（v1/v2 既有约定，重名风险既存不动） | deterministic.py:775-776 |
| 9 | evidence-debt：flow **有** coverage 检查（`check_correction` 内调 `_evidence_debt_coverage`，checks/correction.py:85-111）；真差异 = pipeline **core 前** fail-fast（pipeline.py:897-919）vs flow **core 后**；coverage 判定按 corrections/conflicts **文本包含 offender id** 计 covered（checks/correction.py:534-579）→ core 自产 audit（deterministic.py:760-770,783-796,925-930）可"替 LLM 洗债"；`EvidenceDebtItem` **无 debt_id**（evidence_preflight.py:30-53）；audit 是 `list[dict]`（schema.py:79-82） | — |
| 10 | stage-root `corrections.json` 无 accepted-attempt 保护：`_load_snapped` 只保护 snapped（run_stage.py:199-228）；record_baseline.py:372-395 与 report_assembly.py:373-394 直接读 root | — |
| 11 | `Window.floor` 按 Floor.name 消费：correction_score.py:62-122,285-307,405-415；elevation_score.py:964-1000；render_corrected_geometry.py:114-120,181-182 | — |
| 12 | typed-object 入口不设防：judge 对 `isinstance(geom, CorrectedGeometry)` 直接信任、只对 dict 解析（correction_score.py:316-337）；core/checks 均收宽松基类对象（deterministic.py:725-730、geometry_validator.py:216-225、checks/correction.py:85-111） | — |
| 13 | **pydantic 2.13.3 实测（sol 双探针）**：①v3 子类实例直接 `model_dump()` 保留子类字段，但装入基类注解的 Pydantic holder 再 dump **v3-only 字段被静默裁掉**（attempt writer 现直接 `model_dump_json()`，stage_runner.py:140-145,184-189）；②`model_copy(update=…)` **不跑 validator**，坏值注入后实例类型仍是子类——类身份不是 validation 证明；③`Field(ge=0)` 放行 `float("inf")` | — |
| 14 | prompt 链无 target 概念：`_build_correction_messages` 不接 capability/target（pipeline.py:289-302）、run_correction 建 prompt 不传 capability（:541-582）、两个 inner validator 与最终 parse 直调 legacy 类（:510-535,583-604）；legacy `model_json_schema()` 的 schema_version 默认 `"1"`（schema.py:70-78） | — |
| 15 | `StageRecord` 身份只有 `output_hash`（manifest.py:99-111）；`StageRunner.record` 只归档 output/checks 并按 output 文本算 hash（stage_runner.py:124-180） | — |
| 16 | 测试基线：579 collected = **570 passed + 9 strict xfail**（golden 精确重建，reason=pending sm21 batch） | tests/test_validation_run_baseline.py:26-29 · test_orchestrate_baseline.py:32-35 |

## 2. Schema v3 类型定案

### 2.1 版本常量与 feature 表
- `constants.py` 增 `SCHEMA_VERSION_V3 = "3"`；`capability.py`：`SUPPORTED_SCHEMA_VERSIONS += {V3}`、`SCHEMA_VERSION_SHAPES[V3] = {RECTANGULAR, ORTHOGONAL_POLYGON}`。
- feature 轴（与 shape 轴并列）：
  ```python
  FEATURE_CELL_POLYGON        = "cell_polygon"          # v2, v3
  FEATURE_PER_FLOOR_FOOTPRINT = "per_floor_footprint"   # v3
  FEATURE_FACADE_SEGMENTS     = "facade_segments"       # v3
  FEATURE_TYPED_NORTH_AXIS    = "typed_north_axis"      # v3
  SCHEMA_VERSION_FEATURES: dict[str, frozenset[str]]
  def schema_supports(version_or_geom, feature: str) -> bool   # 未知版本 → False（fail closed）
  ```
- artifact 级 populated 状态另有载体（§6bis），与静态表分立。

### 2.2 strict v3 wire 子类族（r2 专项裁决获准保留）

**legacy wire = 现 `CorrectedGeometry`/`Floor`/`Cell`/`Window` 类原封不动，不加任何字段**——v1/v2 解析、extras、`model_dump_json` 键集、bytes/hash 结构性不变（闭 r1 B2-08，无需 legacy serializer）。

**strict v3 wire = 严格子类族**（r2 已核：子类 forbid 覆盖父 allow；legacy 同名 extra 留在父类路径不炸；半 v3 字段不成 typed 值但可被 getattr 读到→§2.3 禁用模式；父 field_validator 在子类覆写字段上继承生效；`Literal["3"]` 重注解移除父默认=必填）：

```python
FiniteFloat = Annotated[float, AllowInfNan(False)]           # 全部几何/角度/区间统一用
Hex64 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Point2 = tuple[FiniteFloat, FiniteFloat]

class FootprintRing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vertices: list[Point2] = Field(min_length=4)
    # draw-wire 校验（编码宽容、几何严格，§2.4）：有限、正交、简单、min-edge（复用 min_edge_length_m）
    # ——这些性质对绕向/闭环不变；不在 wire 层校验 CCW/开环

class WorldInterval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lo: FiniteFloat; hi: FiniteFloat                          # validator: lo < hi

class FieldProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provenance: Literal["observed", "derived", "assumed"]
    source_ids: list[str] = []
    method: str | None = None
    knowledge_ref: KnowledgeRef | None = None

class KnowledgeRef(BaseModel):                                 # 上位 E2'.2 五元组
    model_config = ConfigDict(extra="forbid")
    dataset_id: str; dataset_version: str; entry_id: str; candidate_id: str
    content_sha256: Hex64

class FacadeSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str                                                    # 全楼唯一（顶层 validator）
    floor_id: str                                              # 指向存在层且 fingerprint 匹配
    facade_family: Literal["North", "South", "East", "West"]
    p1: Point2; p2: Point2                                     # p1 != p2
    outward_normal: tuple[Literal[-1, 0, 1], Literal[-1, 0, 1]]
    world_along_interval: WorldInterval
    depth: Annotated[FiniteFloat, Field(ge=0)]                 # 有限 + 非负（r3 修：ge=0 单独放行 inf）
    visible_intervals: list[WorldInterval] = []                # 排序、两两不交、均 ⊆ world_along_interval
    source_footprint_fingerprint: Hex64
    # 顶层 model validator 一次验齐：abs(nx)+abs(ny)==1（排除 (0,0) 与对角）；
    # p1/p2 轴对齐；outward_normal ⊥ (p2-p1)；normal 与 facade_family 罗盘一致；
    # world_along_interval 与 p1/p2 投影一致

class NorthAxisEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value_deg: FiniteFloat                                     # validator 正规化后必须落 [0,360)
    provenance: Literal["observed", "derived", "assumed"]
    source_ids: list[str] = []                                 # observed → 非空（条件约束）
    uncertainty_deg: Annotated[FiniteFloat, Field(ge=0)] | None = None
    method: str | None = None
    frame_transform_hash: Hex64 | None = None

class FloorV3(Floor):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(frozen=True)                               # 必填；frozen 挡属性赋值（事务身份另有快照，§2.5）
    footprint: FootprintRing                                   # 必填
    cells: list[CellV3] = Field(min_length=1)

class CellV3(Cell):
    model_config = ConfigDict(extra="forbid")

class WindowV3(Window):
    model_config = ConfigDict(extra="forbid")
    floor_id: str                                              # v3 主键引用（§2.6）
    facade_segment_id: str | None = None                       # 段 ref 不取代 room
    provenance: dict[str, FieldProvenance] | None = None       # 键 ∈ claims 词汇（§2.8）

class CorrectedGeometryV3(CorrectedGeometry):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["3"]
    floors: list[FloorV3] = Field(min_length=1)
    windows: list[WindowV3] = []
    facade_segments: list[FacadeSegment] = []
    north_axis: NorthAxisEvidence | None = None
```
- v3 顶层 validator：Floor.id 全楼唯一非空；窗 floor_id/facade_segment_id 引用完整；各层 footprint 几何指纹相同（C2 域 INVARIANT，per-floor 异形=C3 接缝，capability 挡）；provenance 键在词汇内；audit 三表中 `kind=="debt_resolution"` 条目按 §7 strict 模型校验（其余 audit kind 维持 dict 宽容，本批不做 audit 全量 typed 化）。
- 子类不得以与父类相同方法名重定义 validator（继承回归锁定父 normalizer，如 `Window.facade` before-normalizer 在 WindowV3 上生效）。

### 2.3 信任边界：`ensure_corrected_geometry`（无 no-op 快路，r3 修）+ 禁用模式

新 `src/agent/correction/parse.py`：
```python
def ensure_corrected_geometry(value: dict | CorrectedGeometry) -> CorrectedGeometry:
    # dict：按 raw schema_version 分发——"3"→CorrectedGeometryV3.model_validate（strict）；
    #       "1"/"2"/缺省→CorrectedGeometry.model_validate（legacy 宽容=今日行为）；其他→raise
    # 模型实例：schema_version=="3" → 一律 strict round-trip（model_dump→V3.model_validate）
    #       返回【新对象】——不为"已是 V3"设 no-op（类身份不是 validation 证明：
    #       model_copy(update=…) 不跑 validator，r3 实测坏值注入后类型不变）；
    #       legacy 版本实例→原样返回；未知→raise
    # 调用方必须以返回对象为唯一后续输入
```
- **收口点**（全部改经 ensure）：finalize **入口（任何 mutation 之前）** + 末尾（§2.4 final validator）；judge（correction_score.py:316-337 isinstance 快路改先 ensure）；flow loader `_load_snapped`（run_stage.py:219-232）；offline validator（validation_run.py:151-165）；`apply_deterministic_core`/`validate_corrected_geometry`/`check_correction` 入口；render 脚本 dict 路径。执行档 grep `CorrectedGeometry(`/`model_validate` 直调点全量清点入简报。
- **readiness/版本判定禁 `hasattr`/`getattr`**：v3-only 消费与 feature 状态只按 `schema_version + 严格实例/feature-state 记录`（§6bis）判定——legacy 同名 extra 可被 getattr 读到（cell_geometry.py:23-27 即此模式），不得驱动 v3 行为；测试锁定 `hasattr(geom, "facade_segments")` 类判定为禁用模式。
- 负例：宽松基类 `schema_version="3"` 实例直送 judge/core/check → ensure 拦（三入口各一测）；`V3.model_copy(update=坏嵌套/加 extra)` → 下一个信任边界拦。

### 2.4 draw parser / final validator 分立 + ring 三阶段合同（r3 修）

两个命名 API（同在 parse.py），**不用同一把尺兼职宽进与严出**：
```python
def parse_correction_draw(payload: dict, target: CorrectionTarget) -> CorrectedGeometry:
    # ensure + 版本必须 == target.schema_version + phase_contract 校验（§6bis）
    # ring 用【编码宽容】validator：有限/正交/简单/min-edge；CW/closed 放行（LLM 编码噪声）
def validate_final_corrected_geometry(geom: CorrectedGeometry) -> CorrectedGeometry:
    # strict round-trip 返回 fresh 对象 + ring 用【canonical】validator：开环 CCW 强制
    # accepted artifact/judge/check/build 对最终产物只认这把尺
```
**ring 三阶段合同**（采 cell 先例，deterministic.py:755-772 同族）：
- **draw wire**（parse_correction_draw）：编码宽容、几何严格；
- **core 事务②** = 绕向/闭环唯一 canonicalization owner：CW/closed → 改写 + `POLYGON_WINDING_CCW` 同族 audit（保留 producer 原值）；
- **final artifact**（validate_final_corrected_geometry）：开环 CCW 强制，accepted 产物不存在非 canonical ring。
- 三阶段各自测试锁定（raw draw 收 CW+closed 不拒 / pre-core 对象可非 canonical / final 必 canonical / final 收 CW ring → raise）。

**finalize 固定序**：`parse/ensure 输入 → 身份快照 → mutate（核事务）→ validate_final`（§2.5、§5）。

### 2.5 Floor：footprint 产权 + 核内七步事务 + 事务身份快照

- **产权**：`Floor.footprint` 由 correction 阶段声明（证据=平面尺寸链/描边，与 cells 同源）；**任何版本、任何路径（模型/dict/judge/render）禁止从 cells 派生权威 footprint**——v3 缺 `floors[].footprint` = INVARIANT raise（dict helper 同判；correction_score.py:220-249 的 cells 兜底**只保留给 v1/v2**）。防 B3"cells 铺满 footprint"自证循环。
- **核内单一事务顺序（七步，冻结）**：
  ① 保存 producer 原 bbox/ring（audit 前值）→ ② 逐层 canonicalize + validate ring（绕向/闭环唯一 owner + 正交/简单/min-edge 复验）→ ③ ring 顶点纳入 per-floor 轴收集（与 `cell_axis_values` 同路进 `_reconcile_cross_floor` 桶，键=`floor_key`）→ ④ snap 后回写每层 ring 并重验 → ⑤ envelope reconcile：**矩形 ring** 走现 bbox 事务且**同步移动 ring 顶点 + attached cells**（单事务，禁 ring/cells 分离移动）；**非矩形 ring** 该轴整轴不动、按 deterministic.py:603-615 措辞记 unsupported（顶点级变形=B2b）→ ⑥ 顶层 `footprint_x/y` 从最终 rings 派生覆写（v3 语义=派生投影；producer 不一致值在①已存 audit，覆写记 correction 条目；**精确相等，零新容差**）→ ⑦ post-core：跨层 fingerprint 一致 INVARIANT、窗/段引用重验、`validate_final_corrected_geometry`。
- **事务身份快照**（`frozen=True` 只挡属性赋值，不证跨事务不变——r3 实测 `model_copy(update={"id":…})` 可产新 id 且重验不报）：finalize 入口快照有序 `floor ids + 全部 floor_id/facade_segment_id 引用`，末尾断言集合与对应关系逐值不变。
- 负例：删 v3 footprint / 只改 cells / 只改顶层 bbox / 矩形 envelope 成功（ring+cells 同步）/ L 形 envelope unsupported——judge/render/validator 三方同 fail/同几何，无 dict 特赦；`model_copy` 改 id → 快照拦。

### 2.6 Window：新增 `floor_id`，不改 `floor` 语义（r1 裁决）

- v3 `WindowV3.floor_id` 必填、唯一引用存在层；legacy `floor` 保留 deprecated/display——两者并给时 validator 强制 `floor == 该层.name`。
- 消费者统一先 resolve：新 `resolve_window_floor(geom, win) -> Floor`（v3 经 floor_id，v1/v2 经 name）。改面全列：correction_score（:62-122 floor map、:285-307 查表、:405-415 完整性）、elevation_score:964-1000、render_corrected_geometry:114-120,181-182、geometry_validator 窗归属、deterministic 窗处理、specs/audit target。v1/v2 adapter 不伪造持久 v3 id。
- 负例：重名 Floor.name（v3 下 floor_id 仍唯一解析；v1/v2 既有歧义行为不动）。

### 2.7 footprint_x/y 在 v3 = 派生投影
v3 下两字段保留且必填（十文件消费者兼容面），语义=per-floor footprint 的 bbox 投影、由核事务⑥派生写入；producer 不一致值=audit+覆写。v1/v2 语义不动（权威 bbox 本体）。

### 2.8 claims 词汇表（共享常量，单一来源）
新 `src/agent/correction/claims.py`：`CLAIM_EXISTENCE/HOST/ALONG/WIDTH/SILL/HEAD/APPEARANCE`（上位 E2'.5 七词汇）、`WINDOW_CLAIMS = frozenset`、`CLAIMS_VOCAB_VERSION = "1"`。消费方：本批 WindowV3.provenance 键校验；B-M `negative_evidence_capable_claims`；Va applicability；B4b per-claim denominator。**B-M 先落（r4 批次裁决）故由 B-M 批创建该模块，内容以本节为准。**

## 3. capability：4 处硬编码 → feature 声明

统一改写：
```python
if cell_has_polygon(c) and not schema_supports(geom, FEATURE_CELL_POLYGON):
    raise ValueError(f"cell {c.id}: polygon requires a schema version with "
                     f"feature '{FEATURE_CELL_POLYGON}' (declared: {schema_version_of(geom)})")
```
- 4 处点名：deterministic.py:751 / geometry_validator.py:65 / pipeline.py:481 / modelling.py:392；消息文案改 feature 名（不再出现字面 `'2'`）。
- 未知版本：`schema_supports()` False + `require_supported_geometry_contract` 拒绝双保险。
- 三态回归：v1+polygon raise（消息措辞更新登记测试）/ v2+polygon 过 / v3+polygon 过。

## 3bis. CorrectionTarget：目标版本单一选择点（矩阵按 r3 修正）

```python
@dataclass(frozen=True)
class CorrectionTarget:
    schema_version: str                  # "1" | "3"（生产 target 矩阵；见下）
    schema_model: type[CorrectedGeometry]
    capability_profile: str
    phase_contract: str                  # "b2"：facade_segments/north_axis 必空（§6bis）
```
- **生产 target 矩阵（按基底 D1"v1=rectangular、v2=polygon-capable"与现 capability subset 门冻结）**：
  - `capability_profile == "rectangular"` → **schema v1 + legacy model**（=现实生产行为：v2 声明 {rect,ortho} 在 rectangular profile 下必被 subset 门拒，capability.py:21-75；默认 run 全链继续发 v1、bytes/行为不变）；
  - `capability_profile == "orthogonal_polygon"` → **schema v3 + CorrectedGeometryV3**；
  - **schema v2 = 只读 legacy artifact**，B2 后不再作为生产 target（历史产物照常可读可判；确需再产 v2 须另建 `Literal["2"]` wire model + polygon profile，本批不做）。
- **由 run policy 一次选定，无默认歧义**；贯穿链点名：`_build_correction_messages`（prompt 文案 + `target.schema_model.model_json_schema()` 嵌入——v3 时 `Literal["3"]` 使 LLM 无法省略/降版；pipeline.py:289-302,317-328 改版本感知）→ 两个 inner validator（:510-535，改按 target.schema_model）→ 最终 `parse_correction_draw(payload, target)`（:583-604）→ finalize → gate①（同一 target.capability_profile）→ attempt writer（run_config/manifest 记录 target）。混搭结构性不可能=同一 target 对象一路传。
- **sm21 真实 v3 重抽验收条款**：`capability_profile=orthogonal_polygon + schema_version=3`（run_config 显式），断言 accepted manifest 记录同一 target；模型/额度配置跑前请用户拍板（既有铁律）。
- 回归：默认 rectangular run 全链发 v1、prompt/validator/parse 均 legacy、bytes/行为不变。

## 4. floor_footprint 单一 helper

新 `src/agent/correction/footprint.py`（gt-blind 纯函数；全部消费者已 import correction）：
```python
def floor_footprint(geom, floor) -> list[list[float]]
    # v3 → floor.footprint canonical ring；v1/v2 → footprint_x/y 派生矩形 ring（显式 legacy 分支）
def footprint_bbox(geom, floor=None) -> ((xmin,xmax),(ymin,ymax))
    # floor=None 取全楼（C2 各层相同任取一层；v1/v2 即 footprint_x/y）
def floor_footprint_from_payload(data: dict, floor_payload: dict | None = None)
    # dict 变体，同模块单源实现（judge/render 消费 dict）；v3 缺 floors[].footprint → raise（§2.5）
def floor_key(geom, floor) -> str            # v3→id，v1/v2→name（deterministic per-floor 桶键）
```

**贯穿点路由表（route id 化，r4 修——验收按 route id 集合相等，不按词法命中数）**（"吃 ring"=消费多边形本体，"吃 bbox"=只要 bounds）：

| route | 消费点 | 路由 | v3 语义 |
|---|---|---|---|
| R1 | geometry_validator `check_coverage`（:85-88）| ring → `Polygon(floor_footprint(...))` | cells 铺满**多边形** footprint（面积守恒收紧=B3，本批只换底座不改容差/判定式） |
| R2 | deterministic 跨层 reconcile（:778-800）| §2.5 事务③ ring 顶点进桶 | — |
| R3 | deterministic envelope reconcile（:591-721）| §2.5 事务⑤ | 矩形 ring=bbox 事务同步 ring+cells；非矩形=整轴 unsupported |
| R4 | facade.py `derive_facade_frame(fx, fy)` | 调用点换 `footprint_bbox` 喂参（签名不动；per-segment frame=B5/Vg） | — |
| R5 | envelope.py `extract_authoritative_envelope`（:270）| bbox | — |
| R6 | modelling `_zone_quadrant`（:150-154,458 命名罗盘）| bbox | 罗盘中心=bbox 中心不变（命名稳定性优先，不引入 polygon 质心） |
| R7 | checks/correction 宽深（:188-193）+ frame cross-check（:339）| bbox | — |
| R8 | judge/correction_score（:237-273 dict 兜底）| dict 变体 | v3：floors[].footprint bbox，缺失 raise；cells 兜底链仅 legacy |
| R9 | render_corrected_geometry | dict 变体 | v3 画 footprint 多边形轮廓；v1/v2 输出逐像素不变 |
| R10 | render_elevation_windows | dict 变体 | 同 R9 |

**回归铁则**：v1/v2 fixture 上 R1–R10 全部路由数值输出与改造前逐项相等（legacy 分支=原表达式搬家）。

## 5. 双路径同一 finalize + FinalizeResult 序列化合同 + attempt bundle 身份

```python
@dataclass(frozen=True)
class FinalizeResult:               # 非 Pydantic dataclass（基类注解 holder dump 裁字段坑，r2 实测）
    geom: CorrectedGeometry          # validate_final 后的 fresh 对象
    audit_payload: dict              # {corrections, conflicts, unsupported}
    feature_state_claims: FeatureStateClaimsV1   # §6bis：immutable strict 模型（非可变裸 dict，r4 修），
                                                  # 由 target + final geom 确定性派生

def finalize_correction_draw(geom_or_payload, *, vector_dir, tol=None, target) -> FinalizeResult:
    # ① ensure/parse 输入（mutation 前）② 身份快照 ③ tol 自载
    # ④ extract_authoritative_envelope(vector_dir, footprint, tol.envelope_reconcile_tol_m)
    # ⑤ apply_deterministic_core（§2.5 七步事务）⑥ 身份快照比对
    # ⑦ validate_final_corrected_geometry → fresh geom
    # ⑧ 派生 audit_payload + feature_states_payload —— finalize 本身零 I/O（不落盘、不知 attempt dir）
```
- **序列化合同**：attempt writer 对 `result.geom` 直接调用**运行时实例**的 `model_dump_json()`（子类按子类字段表 dump）；禁止装进基类注解 Pydantic holder 再 dump；`stage_runner._to_json` 对 FinalizeResult 显式 raise（逼调用方走显式路径）。
- **attempt bundle 身份（r3/r4 修）**：唯一 attempt writer 在序列化 output、算出 `output_sha256` **后**：①从 `target + result.geom` **重新派生 feature claims 并与 `result.feature_state_claims` 逐项比对**（不盲信调用方数据——frozen dataclass 不冻结内容，篡改由重派生比对拦，不一致=INVARIANT）；②构造 `FeatureStatesArtifactV1{schema_version, output_sha256, claims}` 写 `feature_states.json`；③同一 `attempts/NNN/` 下原子归档 output.json + checks.json + audit.json + feature_states.json，以临时 attempt dir 整体 rename 落位；④登记 **`StageRecordV2.artifact_hashes`** 并设 **`artifact_contract="correction_b2_v1"` + `stage_version` bump 到冻结值 `"2"`**（r5 修；wire/合同矩阵由 B-M 细稿 §5.1 唯一规范拥有：required keys 只由 artifact_contract 决定，correction_b2_v1 = output/checks/audit/feature_states 四键；**冻结不变量 `StageRecordV2.output_hash == artifact_hashes["output"]`**；现 StageRunner stage_version 默认 `"1"`（stage_runner.py:124-134）——调用方漏 bump/漏设合同 = loader 交叉校验拒，禁默认值降级）。下游从 manifest-accepted attempt 读取并逐 hash 验证；claims/sidecar/output 任一篡改断链。
- **stage-root 降级**：`correction_geometry_snapped.json`/`corrections.json` 为 convenience copy，仅 gate① accept 后 promote；record_baseline.py:372-395 与 report_assembly.py:373-394 改从 manifest-accepted attempt 派生（root 只作无 manifest 兜底，与 `_load_snapped` 同序）。
- 两侧改接：pipeline.py:921-954 / run_stage.py:181-190 调同一 finalize；各自前置门保留（§1#6 设计内差异；evidence-debt 见 §7）。
- **flow envelope 生效 = B-02 修复申报**：sm21 型输入 footprint 将收到 `[0,15]×[0,8]`（与 pipeline 一致）；受影响 fixture 走独立非-golden fixture 明示，逐条登记执行简报；历史 run 产物 append-only 不动。
- **parity 口径**：同 fixture 两路径 → FinalizeResult 语义相等 + promote 后 artifact 字节相等（同 writer 同输入）；**"001 accepted → 002 blocked → 下游/report 仍全绑 001"回归**。

## 6.（并入 §5，编号保留避免歧义——本节无独立内容）

## 6bis. v3 生产发射 + feature-state 机读载体

- 发射机制并入 §3bis CorrectionTarget（prompt/validator/parse 一条链）；`phase_contract="b2"`：draw 校验强制 `facade_segments == [] and north_axis is None`（LLM 给非空→拒）。
- **feature-state 两型 strict wire（r4 修）**：
  - **`FeatureStateClaimsV1`**（finalize 返回，immutable：frozen records/tuple 非可变 dict，`extra="forbid"`）：**受控完整 feature 键集**（§2.1 四 feature 全员必填，缺键=坏 wire）× 状态 enum `not_declared | declared_unpopulated | populated`，加 `target_schema_version / phase_contract / helper_versions`。B2 期 v3 = cell_polygon+per_floor_footprint: populated、facade_segments+typed_north_axis: declared_unpopulated；legacy = 全 not_declared。
  - **`FeatureStatesArtifactV1{schema_version, output_sha256, claims}`**（writer 序列化 output 后构造落盘）——sidecar 内 output_sha256 只证"sidecar 指向 output"，**StageRecordV2.artifact_hashes 记 sidecar hash 才证"accepted 指向这份 sidecar"**。
  - 两 API 分立：`schema_supports(version, feature)`（静态表）与 `artifact_feature_state(attempt, feature)`（**先验 artifact schema + StageRecordV2 hash + output_sha256，再读 state**；缺失/hash 不符=fail closed）；判定永不依赖字段存在性/空列表歧义（§2.3 禁用模式）。
- **ownership 冻结（Vg 上线后合同）**：facade_segments 唯一 writer = correction 确定性核（上位 E2'.7）——Vg helper 接入 finalize 后**形成新 attempt**（feature_states 翻 populated + 记 Vg helper version）；**绝不回写旧 accepted output**。B3/Vg/Va/B4/B5 消费者各自声明需要 `support` 还是 `populated`；缺所需状态恒 BLOCK。
- 负例：legacy 同名 extra 伪装 populated（§2.3 拦）/ v3 空段无 sidecar（fail closed）/ 声称 populated 但列表空且无 Vg version（不一致 INVARIANT）/ 改 sidecar 不改 manifest（hash 断链）/ 篡改旧 accepted output（hash 断）/ **FinalizeResult 返回后篡改 claims（writer 重派生比对拦）** / **未知 feature 键、未知 state、缺完整 feature 集（strict wire 拒）**。

## 7. evidence-debt：双路径 pre-core 对等 + debt_id 主键化 + strict resolution

- **两路径共用 pre-core check**（放 evidence_preflight 或 checks/correction，执行档定位）：pipeline 保持 fail-fast（core 前）；flow 将同一结果并入该 draw 的 gate① report（blocked draw 按 attempts 记账不静默）。**不进纯 finalize**（r1 裁决：编排语义不塞纯函数）。
- **evidence-debt schema bump**：`EvidenceDebtItem` 增确定性 `debt_id` = canonical hash（source report/artifact hash + canonical check id + view + scope + 排序后 offender ids；同 check 多 view/多 offender 各自成键）；correction attempt input_hashes 绑定 debt artifact hash。
- **strict `DebtResolutionAuditEntry`**（audit union 独立 kind，typed 模型）：`{kind: "debt_resolution", resolves_debt_id, rationale, source: "llm_correction" | "a3"}`；v3 校验时该 kind 条目按此模型验证；**core 自产 audit kind 在类型上不拥有 `resolves_debt_id` 字段**（洗债结构性不可能）。
- checker（替换 checks/correction.py:534-579 字符串扫描）：只接受指向**本 attempt 输入 debt 集**的 `resolves_debt_id`；重复清偿/不存在 id/跨 run id 均 BLOCK。
- 负例：core audit 洗债（类型锁）/ 伪造 id / 重复清偿 / pipeline 与 flow 同判。

## 8. 测试计划（累计全量）

1. **schema v3**：Floor.id 缺失/重复/引用断裂 raise；footprint 缺失 raise、CW/closed 三阶段合同（§2.4）；非正交/自交/min-edge raise；跨层指纹不一致 INVARIANT；v3 未知字段五点位（顶层/Floor/Cell/Window/FacadeSegment）raise；v1/v2 lax 回归（extras 保留、缺 id 合法）；同名 legacy extra 双向负例（v1 异形 extra 不炸；v1 带合法形 v3 字段仍是 extra）。
2. **capability/feature**：版本→feature 矩阵；版本 "4" fail closed；4 call sites 三态。
3. **ensure 边界**：三入口拦截（judge/core/check 收宽松基类 schema=3）；`model_copy` 注入坏嵌套/extra/CW-final-ring → 下一边界拦；hasattr 禁用模式锁。
4. **约束类型**：坏 normal 三例 (0,0)/(1,1)/(-1,1)；斜 segment；normal 与 family 反向；`depth/uncertainty` 的 `+inf/-inf/nan` 三负例（不只测负数）；逆区间/重叠 visible_intervals/区间越界；坏 digest。
5. **身份快照**：`model_copy` 改 Floor.id → finalize 拦。
6. **helper**：v1/v2 矩形等价（bbox ≡ footprint_x/y、ring ≡ 四角）；v3 passthrough；dict 变体同输入同输出；**R1–R10 按 route id 集合相等验收**，v1/v2 fixture 数值逐项回归（R9/R10 两渲染分别断言）。
7. **finalize/身份**：parity（语义相等+promote 后字节相等）；FinalizeResult→StageRunner→attempts/NNN/output.json→ensure 重载**逐键**断言 v3-only 字段在场；基类 holder dump 裁字段哨兵测试；001 accepted→002 blocked 回归；flow envelope 修复回归（sm21 型 fixture → [0,15]×[0,8]）。
8. **CorrectionTarget**：贯穿一致性（prompt schema/validator/parse/manifest 同 target，**含 stage_version bump 与 artifact_contract 设置进贯穿断言**）；默认 rectangular run 全链发 v1 且 bytes/行为不变。
9. **feature-state**：§6bis 负例族全量（含篡改 claims、未知键/state、缺完整 feature 集）。
10. **evidence-debt**：debt_id 确定性（同输入同 id/改 offender 变 id）；strict resolution 负例族；两路径同判。
11. **producer 路径合成 E2E**：v3 从 prompt-schema→parse_correction_draw→finalize→kernel→specs 全链（构造 LLM 返回 payload 走 parse 入口，非直接构造 post-schema 对象）。
12. **artifact contract 交叉负例（r5 增）**：B2 新 correction 缺 audit/feature_states 或报 `base_v2` → 拒；migrated legacy 两键可读；伪造 contract 与 attempt provenance 不符 → 拒。
13. **零 golden**：570 绿 + 9 strict xfail 全程不动；sm20/sm21 golden 零改动；新增测试另行通过。

## 9. 施工顺序建议（执行档参考，不构成放行扩张）

①constants/capability+feature 表 → ②claims.py → ③ring 通用族 + 三阶段合同 → ④strict 子类族 + parse.py（ensure/draw parser/final validator）+ 入口收口 → ⑤核七步事务 + 身份快照 → ⑥footprint helper 贯穿 → ⑦CorrectionTarget 贯穿链 → ⑧FinalizeResult + attempt bundle（audit/feature_states/StageRecord.artifact_hashes）→ ⑨evidence-debt bump + typed resolution → ⑩prompt 版本感知 + 4 处硬编码 → ⑪测试补齐。④⑤⑦⑧⑨ 各出中间 diff 供复核；每步全量测试。

## 10. 配置 / A0

零新增几何容差（v3 footprint_x/y 一致性=核写入端精确相等；面积容差归 B3；可见性 epsilon 归 Vg）。A0 登记：`resolves_debt_id` 槽位、FeatureStateClaimsV1/FeatureStatesArtifactV1 schema、evidence-debt schema version bump、claims 词汇版本；StageRecordV2.artifact_hashes 的 A0 登记随其 wire owner（B-M §5.1）。

## 11. 开放问题：无（r1–r4 全部裁决已吸收；r3/r4 均确认无需用户新拍板项）
