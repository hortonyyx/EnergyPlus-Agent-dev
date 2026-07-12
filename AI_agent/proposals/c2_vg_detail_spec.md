# C2 Vg 代码级细稿 v3：E1' 立面可见性纯几何函数批

> **版本史**：v1 2026-07-12（sol 次高档出稿）→ Fable 最高档交叉审 `APPROVE-WITH-CHANGES` → v2 2026-07-12（冻结 core 身份快照在 materialize 前复核、stage version 按 strict helper-version release map 派生、双翻转按 XOR）→ sol 施工交叉审 `REWORK` → **v3 2026-07-12**：中央 release map 纳入 legacy v1 完整状态、删除不可构造的单段双 visible-islands 验收项、禁止两个 visibility epsilon 的 dataclass 默认；全文累计自包含。
>
> **日期 / 档位 / 主控**：2026-07-12；Claude/Fable5 主控，Fable 交叉审。
>
> **上位设计**：[c2_full_unlock_design.md](c2_full_unlock_design.md) v2.2 §E1'、§Schema v3、§DAG 的 Vg 行；**现基座**固定为 commit `bac689b`；**视图方向语义**固定为 [c2_bm_view_manifest_spec.md](c2_bm_view_manifest_spec.md) v6。本文是累计式、自包含、代码级施工细稿；后续修订必须保留全文，不得只交补丁摘要。
>
> **放行边界**：细稿 → 交叉审 → 执行 → 复核；本文只放行 Vg 批。本文自身不修改代码、测试、配置或 A0。

---

## 0. 唯一目标、范围与非目标

### 0.1 唯一目标

为 C2 的无洞、单连通、等高、正交简单 footprint 实现一个 **gt-blind 纯几何 Vg 核**：从每层 exterior ring 派生 North/South/East/West 四方向的全部立面段，按每方向 1D skyline 计算每段可见半开区间，并将结果无损构造成基座已经冻结的严格 `FacadeSegment` wire。

核心调用关系冻结为：

```text
floor_footprint(geom, floor) + floor_footprint_fingerprint(geom, floor)
        │
        ├─ 每方向 Vg(ring, outward_direction, tolerances)
        │      └─ FacadeSegmentFrame + visible [lo, hi)
        │
        └─ floor namespace + canonical segment fingerprint
               └─ strict FacadeSegment instances
```

### 0.2 In

1. 四个 cardinal building-axis 方向的 segment 派生、depth 定义和 skyline visibility；
2. `ViewProjectionFrame` 与 `FacadeSegmentFrame` 的职责拆分及兼容接缝；
3. 每层严格 `FacadeSegment` 构造、确定性 id、稳定排序和 footprint fingerprint 填充；
4. Vg 接入 correction 的同一纯 `finalize_correction_draw`，使 v3 accepted attempt 的 `facade_segments` 与 feature state 变为 populated；
5. 两个新 epsilon 的 `correction.yaml`、`CoreTolerances`、A0 登记方案；
6. L/U/Z/T、全遮挡、部分遮挡、同深冲突、半开端点及集成回归的穷举测试族。

### 0.3 Out

以下均不在本批施工：

- **Va**：opening × claim applicability、manifest/coverage/completeness 消费、plan/elevation 分支、per-claim denominator；本文只冻结 Vg 给 Va 的输出合同（§8）；
- opening 的 `facade_segment_id` 解析、room/parent wall 唯一性、窗 span clamp、`_window_verts` 重构；归 B5；
- B-M manifest、`ResolvedViewDirection` sidecar 的生成或修改；
- gt-v-next、gt_from_dxf、scorer、sidecar、render；归 B4a/B4b；
- 立面匹配、partial view、洞/中庭、非正交或非 cardinal 投影；归 C3/C4；
- footprint/cell 变形、coverage 面积门、north-axis/EP 输出；分别归 B2b、B3、E4/B-O；
- 任何 LLM prompt 推理或图像读取。

## 1. 权威现状对账（基座 `bac689b`）

| # | 冻结事实 | Vg 约束 |
|---|---|---|
| 1 | `src/agent/correction/schema.py` 已有 strict `FacadeSegment`：`id/floor_id/facade_family/p1/p2/outward_normal/world_along_interval/depth/visible_intervals/source_footprint_fingerprint` | 不增删、不改名、不放宽字段；Vg 必须直接产可通过该模型的实例 |
| 2 | `FacadeSegment._valid_segment` 已强制非零轴对齐、法向单位且与 family 一致、world interval 等于线段投影、visible intervals 排序且位于段内 | 本批只补派生与语义验证，不复制第二套 wire |
| 3 | `CorrectedGeometryV3` 已强制 segment id 全楼唯一、floor 引用存在、source fingerprint 与所属 floor 相符 | id 必须含 floor namespace；禁止跨层复用 id |
| 4 | `floor_footprint()` 是模型输入的唯一 footprint 取数通道；`floor_footprint_fingerprint()`/`footprint_fingerprint()` 是唯一几何指纹通道 | 禁止从 cells、`footprint_x/y` 或手写 JSON 重建 v3 权威 ring/指纹 |
| 5 | v3 schema 已强制所有层 footprint 几何相同；final artifact 是 canonical open CCW ring | Vg 仍按层计算并按层填 fingerprint/id；不因 C2 同 footprint 而只产一层后复制对象 |
| 6 | `facade.py` 的 `FacadeWorldFrame` 把 view local→world sign 与单一 bbox 极值 base plane 混在一起，适合旧矩形 cross-check，不足以表达凹形多段 | 新路径必须拆 frame；旧 API 只作 compatibility wrapper，不供 Vg/Va 新代码调用 |
| 7 | `finalize_correction_draw` 是 integrated/stepwise 两路共同纯 finalize；B2 draw 合同拒 producer 预填 `facade_segments`；基座 `_identity_snapshot` 已包含 floors、windows 及 `facade_segments` 的 `(id,floor_id)` | core 后必须在 materialize **之前**完成原快照复核；materialize 后不得拿“入口空段快照”比较“出口满段列表”，段正确性改由独立重算验证承担 |
| 8 | `FeatureStateClaimsV1` 已有 `facade_segments` 与 `helper_versions`，基座 v3 暂报 `declared_unpopulated` | Vg 后 v3 必报 `populated` 并登记 `facade_visibility_v1`；legacy 仍 `not_declared` |
| 9 | B-M v6：`building_axis` 可直接得到 building direction；`true_azimuth/unknown` 必须经绑定 hash 的 `ResolvedViewDirection` sidecar 才可解析 | Vg 不读 manifest/sidecar；调用方只把已解析的 cardinal outward vector 交给 Vg |
| 10 | `StageRunner.record()` 对 `FinalizeResult` 在 accepted 分支硬写 correction `stage_version="2"` | 本批改为从 writer 边界重新派生的 strict feature claims/helper_versions 查 release map；不得继续按“是不是 FinalizeResult”写死版本 |

## 2. 适用域与全局不变量

### 2.1 适用域

Vg 仅声明支持：

- 一个 exterior ring；无 inner ring、无洞；
- 单连通、非自交、非自触、正面积简单多边形；
- 所有边严格水平或垂直；
- 四个 building-axis cardinal 正投影；实体墙不透明；
- 每层独立计算；C2 caller 继续执行“各层 footprint 相同、等高”的上位 scope gate。

口字形/中庭、多 exterior components、斜边、曲线、透空幕墙、退台造成的跨层互遮、透视投影均 fail closed，不借近似算法伪支持。

### 2.2 冻结不变量

1. **视图不等于一个面**：一个方向可对应多个不同 depth 的同向 facade segments；不得退化为 bbox 极值单面。
2. **区间一律半开**：本文及后续 Va 对 `WorldInterval{lo,hi}` 的唯一解释是 `[lo, hi)`；`lo < hi`。最右端单点不形成可见宽度。
3. **遮挡只由 depth 决定**：同一方向、同一正宽 along 原子区间内，较小 depth 的段遮挡较大 depth 的段。
4. **同深不选赢家**：两个不同 segment 在正宽重叠区间上的 depth 差 `<= FACADE_VISIBILITY_DEPTH_EPSILON` 时为 `INVARIANT`；不得以 id、ring 次序或 sort 次序破 tie。
5. **端点接触不是重叠**：`[a,b)` 与 `[b,c)` 没有正宽交集，不产生遮挡或同深冲突。
6. **全段保留**：fully hidden segment 仍写入 wire，`visible_intervals=[]`；禁止删除它或把它并入浅段。
7. **Vg 不改输入几何**：epsilon 只作比较/拒绝门，不 snap、不 clamp、不合并不同坐标；输出坐标均来自 ring。
8. **确定性**：ring 起点、显式 closure、CW/CCW 编码差异不得改变语义输出、id 或最终排序；同输入同配置逐字节相同。
9. **单一 writer**：accepted `facade_segments` 只由 correction deterministic finalize 写；producer、Va、judge、render 不得回写。
10. **gt-blind**：产品侧和 judge 侧各用自己的 ring 调同一 Vg 函数；任何一侧不得把 gt 或产品 coverage 注入 Vg。

## 3. 方向、frame 与 depth 的精确定义

### 3.1 cardinal direction 表

`direction` 精确表示 facade 的 **outward normal / 观察者所在侧**，只接受下列四个整数向量；近似向量不 normalize：

| family | direction / outward normal `n` | along world axis | 标准 image-left→right sign | segment `p1→p2` |
|---|---:|---|---:|---|
| South | `(0,-1)` | x | `+1` | west→east，x 递增 |
| North | `(0,+1)` | x | `-1` | east→west，x 递减 |
| East | `(+1,0)` | y | `+1` | south→north，y 递增 |
| West | `(-1,0)` | y | `-1` | north→south，y 递减 |

B-M 的 `building_view_direction` 按本表直映；`true_azimuth/unknown` 若未由 E4 sidecar 唯一解析成上述一值，调用 Vg 前即 BLOCK。真北不得改写 family。

### 3.2 frame 拆层

在 `src/agent/correction/facade.py` 冻结两个新 immutable dataclass：

```python
@dataclass(frozen=True)
class ViewProjectionFrame:
    facade_family: FacadeFamily
    world_axis: Literal["x", "y"]
    sign: Literal[-1, 1]
    along_origin: float
    mirrored: bool
    local_x_positive: Literal["image_left_to_right", "image_right_to_left"]

    def to_world_along(self, local_x: float) -> float: ...

@dataclass(frozen=True)
class FacadeSegmentFrame:
    facade_family: FacadeFamily
    p1: Point2
    p2: Point2
    base_world: float
    outward_normal: CardinalDirection
    world_along_interval: tuple[float, float]
    depth: float
```

- `ViewProjectionFrame` 一张 elevation view 一个，只负责 local along → world along。标准 `base_sign` 来自 §3.1；`mirrored` 与 right-to-left local convention 是两个独立翻转位，**组合语义固定为 XOR**：`effective_flip = mirrored ^ (local_x_positive == "image_right_to_left")`，`sign = -base_sign if effective_flip else base_sign`。两者同时非默认会双翻转、恢复 `base_sign`。最终 `along_origin = along_lo`（sign `+1`）或 `along_hi`（sign `-1`）。它不含 wall plane、segment id 或 visibility。
- `FacadeSegmentFrame` 一段一个，只负责 world geometry；South/North 的 `base_world=y`，East/West 的 `base_world=x`。它不含 local image、mirror、manifest 或 claim。
- 旧 `FacadeWorldFrame/derive_facade_frame` 保留为 legacy compatibility wrapper，以保证现 cross-check 和矩形回归不被本批无关改写；Vg/Va 新代码禁止 import 该 aggregate 类型。新增测试锁新 builder 的 resolved bool × local convention 四格；旧 wrapper 的 `true/false/unknown` 三态另按既有行为回归，不把 legacy unknown 语义带进新 frame。

builder 签名冻结为 `derive_view_projection_frame(*, vertices, facade_family, mirrored=False, local_x_positive="image_left_to_right")`；`along_lo/hi` 只从该 ring 在 world along axis 的投影极值取得。direction semantics 与 mirror/right-to-left 的证据是否合法由调用方先验，frame builder 不读取 manifest 或 reading artifact。

双翻转真值表（`B=base_sign`）：

| `mirrored` | `local_x_positive` | `effective_flip` | final sign |
|---|---|---:|---:|
| `False` | `image_left_to_right` | 0 | `B` |
| `True` | `image_left_to_right` | 1 | `-B` |
| `False` | `image_right_to_left` | 1 | `-B` |
| `True` | `image_right_to_left` | 0 | `B` |

新 builder 只接收 resolved bool；`mirrored=unknown` 在调用前 fail closed，不把 unknown 当 False。旧 compatibility wrapper 的既有 legacy 解析行为不由本批追溯改变。

### 3.3 depth 符号与公式

对方向单位向量 `n`、ring 顶点 `v`、候选段任一点 `p`：

```python
front_support = max(dot(n, v) for v in ring)
raw_depth = front_support - dot(n, p)
```

- 观察者位于 `+n` 无穷远；support plane 上最浅段 depth 为 `0.0`；越向建筑内部，depth 越大。
- 轴对齐候选段上 `dot(n,p)` 恒定，可用其 canonical `p1` 计算。
- 若 `abs(raw_depth) <= depth_epsilon_m`，序列化为精确 `0.0`（同时消除 `-0.0`）；若 `raw_depth < -depth_epsilon_m`，报 INVARIANT；否则保留原有限 float。
- 比较规则唯一为：`abs(d1-d2) <= depth_epsilon_m` 是同深冲突；`d1 < d2-depth_epsilon_m` 才称 d1 更浅。不得 round depth 后比较。

例：South 的 `front_support=-y_min`，故 `depth=y-y_min`；North 为 `y_max-y`；East 为 `x_max-x`；West 为 `x-x_min`。

## 4. 纯函数 API 与依赖边界

### 4.1 新模块与公开 API

新建 `src/agent/correction/facade_visibility.py`：

```python
CardinalDirection = tuple[Literal[-1, 0, 1], Literal[-1, 0, 1]]

@dataclass(frozen=True)
class VisibilityTolerances:
    depth_epsilon_m: float
    endpoint_epsilon_m: float

@dataclass(frozen=True)
class DerivedVisibleSegment:
    frame: FacadeSegmentFrame
    visible_intervals: tuple[tuple[float, float], ...]
    canonical_edge_key: tuple

def vg_for_direction(
    vertices: Sequence[Sequence[float]],
    direction: tuple[int, int],
    *,
    tolerances: VisibilityTolerances,
) -> tuple[DerivedVisibleSegment, ...]: ...

def materialize_floor_facade_segments(
    geom: CorrectedGeometryV3,
    floor: FloorV3,
    *,
    tolerances: VisibilityTolerances,
) -> tuple[FacadeSegment, ...]: ...

def materialize_all_facade_segments(
    geom: CorrectedGeometryV3,
    *,
    tolerances: VisibilityTolerances,
) -> tuple[FacadeSegment, ...]: ...

def validate_materialized_facade_segments(
    geom: CorrectedGeometryV3,
    *,
    tolerances: VisibilityTolerances,
) -> None: ...
```

`vg_for_direction` 是上位设计所称 `Vg(polygon,direction)`；后两层只是 floor namespace/fingerprint/wire 的薄纯适配，不改变几何判定。

### 4.2 纯函数边界

上述四函数及 frame builder 必须满足：

- 无文件、环境变量、网络、时钟、随机数、日志落盘；
- 无 gt import、无 judge import、无 manifest import、无 LLM/reading import；
- 不在函数内调用 `load_core_tolerances()`，因为配置加载是 I/O；编排/finalize 边界先解析 `CoreTolerances`，再构造显式 `VisibilityTolerances` 传入；
- 不 mutate `vertices`、`geom`、`floor` 或已存在的 segment list；返回 tuple/fresh Pydantic instances；
- 几何模块只允许 import schema 类型、`floor_footprint`/`floor_footprint_fingerprint`、标准库数学/哈希/JSON，以及 frame 类型。

## 5. ring 规范化、校验与四方向段派生

### 5.1 输入编码规范化

`vg_for_direction` 自身对几何相同的 ring 编码保持稳定：

1. 将每点严格解析为两个 finite real；bool、NaN、±inf、错维度拒绝；`-0.0` 仅在 canonical hash 序列化时正规化为 `0.0`，不移动其他值；
2. 允许 open ring 或**恰好一个**与首点精确相同的 closing point；移除该 closure；中间重复 closure/连续重复点拒绝；
3. 至少四个 distinct vertices；signed area 非零；CW 时反转为 CCW；
4. 旋转到所有循环旋转中字典序最小的完整顶点 tuple，不能只按“第一个最小点”打破对称 tie；
5. 相邻同向共线小段合成一个 maximal run；相邻反向共线属于 backtrack/self-overlap，拒绝；
6. 合并后重新 canonical rotate，并执行 §5.2 全量拓扑门。

生产 adapter 仍必须从 `floor_footprint(geom,floor)` 取数；上述编码兼容不授权从别处取 ring，也不放宽 final CorrectedGeometry 的 open-CCW 合同。

### 5.2 拒绝门

以下统一抛 `FacadeVisibilityInvariantError(code, context)`（`ValueError` 子类），caller 将其作为 deterministic INVARIANT/BLOCK，不转成 `unsupported` 后继续：

| code | 条件 |
|---|---|
| `visibility_bad_direction` | direction 不精确等于四 cardinal 值之一 |
| `visibility_non_finite_coordinate` | 非有限、bool 或坏点结构 |
| `visibility_too_few_vertices` | 少于四 distinct vertices 或合并后少于四边 |
| `visibility_zero_or_short_edge` | 零长，或边长 `<= endpoint_epsilon_m` |
| `visibility_non_orthogonal_edge` | dx、dy 同时非零；不按 epsilon 猜轴 |
| `visibility_zero_area` | signed area 为零 |
| `visibility_self_intersection` | 非相邻边相交或接触；相邻边除共享唯一端点外重叠 |
| `visibility_repeated_vertex` | 非 closure 的顶点重复/self-touch |
| `visibility_backtrack` | 连续边 180° 回折或共线重叠 |
| `visibility_endpoint_collision` | 同方向 sweep 中两个不同 endpoint 的正差 `<= endpoint_epsilon_m`；拒绝而非 bucket/snap |
| `visibility_negative_depth` | depth 小于 `-depth_epsilon_m` |
| `visibility_same_depth_overlap` | 两不同段在正宽 atom 上 depth 差 `<= depth_epsilon_m` |
| `visibility_wire_mismatch` | materialized list 与从权威 floor ring 重算结果不逐项相同 |

洞/多环输入因 API 只接受一层 point sequence；传入 nested ring 或 multi-polygon 结构按坏点结构拒绝。错误 context 至少含 floor_id（adapter 层）、family、canonical edge keys/atom，禁止只报“bad geometry”。

### 5.3 boundary edge → candidate segment

规范 ring 为 CCW。对每条边 `a→b`，令 tangent `t=b-a`，outward normal 为右法向：

```python
n = (t.y / length, -t.x / length)
```

正交条件下 n 必精确落在四 cardinal 值。仅 `n == requested_direction` 的 maximal edges 进入该方向候选集；侧边与背向边不投影成 facade segment。

对候选段：

- `facade_family` 由 requested direction 唯一映射；
- `world_along_interval=(min(along(a),along(b)), max(...))`；
- `p1/p2` 强制按 §3.1 的标准 view sign 排列，不依赖 producer ring 起点/绕向；
- `base_world` 为常量 plane 坐标；
- `depth` 按 §3.3；
- `canonical_edge_key=(facade_family, along_lo, along_hi, base_world)`，其中所有 `-0.0→0.0`；key 不含 ring edge index、input order 或 visibility；
- 候选先按 `(along_lo, along_hi, depth, canonical_edge_key)` 排序。

每个合法 bounded orthogonal polygon 对四个方向都应至少有一个候选；缺任一方向说明拓扑/法向派生错误，报 INVARIANT。

## 6. 每方向 1D skyline 算法

### 6.1 原子化

对该方向所有 candidate 的 `along_lo/along_hi`：

1. 收集并 exact 去重后升序排序为 `events`；
2. 若相邻不同 event 的差在 `(0, endpoint_epsilon_m]`，报 `visibility_endpoint_collision`；Vg 不决定该细缝应合并还是保留；
3. 每对相邻 event 形成正宽半开 atom `[events[i], events[i+1])`；
4. contender 定义为其 segment interval **完整包含**该 atom 的候选。因为 atom 边界来自全部 endpoint，禁止用 midpoint-only 的模糊命中代替完整包含断言。

空 contender atom 只是候选 union 的间隙，不产生记录。

### 6.2 winner 与冲突

```python
for atom in atoms:
    contenders = segments_covering(atom)
    if not contenders:
        continue
    d_min = min(s.depth for s in contenders)
    winners = [s for s in contenders
               if abs(s.depth - d_min) <= depth_epsilon_m]
    if len(winners) != 1:
        raise FacadeVisibilityInvariantError("visibility_same_depth_overlap", ...)
    visible_atoms[winners[0]].append(atom)
```

只比较最浅层 tie 已足够：更深段之间即使同深也不影响当前 skyline，但它们仍代表非法上游几何。故实现还必须对 atom 的**全部 contender 两两**检查：任意不同段 depth 差 `<= epsilon` 都报 INVARIANT，然后才选唯一最浅者。不得只检查 winners。

### 6.3 合并与输出

- 同一 winner 的连续 atoms 仅在 `previous.hi == next.lo` **精确相等**时合并；epsilon 不用于桥接真实 gap；
- 输出 intervals 按 lo 升序、两两不交，均为正宽且在 segment world interval 内；
- 没赢过任何 atom 的 segment 输出空 tuple；
- 对每个 direction，返回全部 candidates，排序仍为 `(along_lo, along_hi, depth, canonical_edge_key)`；
- visibility 不改变 segment id/key/depth/frame。

复杂度基线为 `O(E log E + A·S)`（E endpoints、A atoms、S same-direction segments）；C2 footprint 规模足够。若施工者优化为 event active-set sweep，必须与本定义逐 atom 等价，不能改变 tie/半开语义。

## 7. 严格 `FacadeSegment` 构造与确定性身份

### 7.1 fingerprint 与 id

每层先且只调用：

```python
ring = floor_footprint(geom, floor)
source_fp = floor_footprint_fingerprint(geom, floor)
```

segment geometry fingerprint 的 canonical JSON preimage 冻结为：

```json
{
  "schema": "facade_segment_geometry_v1",
  "facade_family": "North|South|East|West",
  "p1": [0.0, 0.0],
  "p2": [0.0, 0.0]
}
```

序列化用 `sort_keys=True, separators=(",",":"), ensure_ascii=False`，finite float 采用 Python JSON 最短往返表示，且先把 `-0.0` 改为 `0.0`；digest 为 lowercase full SHA-256 hex。id 冻结为：

```python
segment_id = f"{floor.id}:facade:{segment_geometry_sha256}"
```

不得截断 digest，不得用 ring edge index、list position、Python `hash()`、depth 或 visibility 构造 id。相同几何的不同层因 floor namespace 得到不同 id；同层不同 family/plane/span 得到不同 digest。

### 7.2 wire 构造

每个结果直接实例化基座类型，不先造宽松 dict：

```python
FacadeSegment(
    id=segment_id,
    floor_id=floor.id,
    facade_family=frame.facade_family,
    p1=frame.p1,
    p2=frame.p2,
    outward_normal=frame.outward_normal,
    world_along_interval=WorldInterval(lo=along_lo, hi=along_hi),
    depth=frame.depth,
    visible_intervals=[WorldInterval(lo=lo, hi=hi) for lo, hi in visible],
    source_footprint_fingerprint=source_fp,
)
```

`WorldInterval` 在 wire 中不携带开闭标志；其 schema/A0 语义由本文冻结为半开 `[lo,hi)`。不得把 fully visible 表示成缺字段，也不得把 fully hidden 段省略。

### 7.3 全楼排序

`materialize_all_facade_segments` 的唯一顺序：

```text
(floor_id lexical,
 family_rank where North=0, South=1, East=2, West=3,
 along_lo, along_hi, depth, canonical_edge_key)
```

该顺序独立于 `geom.floors` 输入顺序、ring 起点和 hash-map 遍历。构造后立即用 strict `FacadeSegment` 验证，再执行 id uniqueness、floor/fingerprint 交叉断言。

## 8. Vg → Va 输出合同（Va 下一批实现）

Vg 交给 Va 的唯一几何事实是 accepted output 内每层全量 strict `FacadeSegment`：

1. `facade_family/outward_normal` 是 building-axis，不是真北标签；
2. `p1/p2/world_along_interval/depth` 是 world-frame；
3. `visible_intervals` 是该 family 正投影下的半开、排序、不交可见区间；空列表明确表示该段全遮挡；
4. `source_footprint_fingerprint` 把结果绑定到该 floor 权威 ring；
5. id 对 ring 编码/visibility 稳定，可供 opening 与 sidecar 引用；
6. Vg 不输出 claim applicability、coverage、room、window 或 view identity。

Va 必须遵守：

- elevation 来源 claim：先用该 view 的 `ViewProjectionFrame` 将 local interval 两端映到 world、排序成半开 interval，再与**同 floor + 同 resolved family** 的各 segment `visible_intervals` 做区间交；禁止按窗口中心点、段总状态或 bbox 单面判断；
- plan 来源 claim：按 B-M v6 §3.5 走 trusted `plan_floor_region` 与 footprint/host boundary，**不与 Vg visibility 相交**；hidden 不阻止 plan evidence；
- claim 跨 visible/hidden 边界时，Va 按 claim 产 partial/NA；Vg 不替 Va 做政策决定；
- Va 消费前验证 accepted attempt hash/feature state、floor fingerprint、B-M manifest hash及必要的 ResolvedViewDirection hash；缺失/漂移 fail closed；
- Va 不修改 `FacadeSegment` 或 `CorrectedGeometry`。

## 9. correction finalize、feature state 与 artifact 接线

### 9.1 唯一写入时点

两条执行路径继续只调同一个 `finalize_correction_draw`。v3 顺序冻结为：

```text
ensure/parse producer input（仍要求 facade_segments=[]）
→ 身份快照
→ authoritative envelope + deterministic core（footprint 已最终稳定）
→ **立即做身份快照复核**（仍是入口空段 vs core 后空段）
→ materialize_all_facade_segments(fresh geom, explicit visibility tolerances)
→ model_copy(update={"facade_segments": list(result)}) 产 fresh v3 object
→ validate_materialized_facade_segments（从 floor_footprint 独立重算逐项比对）
→ validate_final_corrected_geometry
→ derive feature claims
```

实现方式固定选择“**core 后、materialize 前复核原 `_identity_snapshot`**”：保留 `_identity_snapshot` 的现有三元 tuple 形状与内容，不拆两级、不加条件比较；只把 `finalize.py` 现 `before != _identity_snapshot(geom)` 的复核保持在 `apply_deterministic_core` 返回后，并确保新增 materialize 代码插在该复核之后。materialize 后不再调用 `_identity_snapshot`，因为 facade list 从空变满是本批预期写入，不是身份漂移；其完整性由 `validate_materialized_facade_segments` 从权威 ring 独立重算并逐项比较，floor/window 身份则已经在 materialize 前被原快照锁定。

legacy v1/v2 分支不调用 materializer、不加字段、不改 serializer bytes/行为。Vg 失败是 deterministic INVARIANT；不得把空 list 当降级成功。专门回归必须证明：core 偷改 floor/window/入口 segment identity 仍由原快照拦截，而合法 Vg 空→满不会产生假阳性。

### 9.2 feature state

`derive_feature_state_claims(target, geom)` 改为 shape + phase 明确派生：

- v3/Vg final 且 materialized validation 通过：`facade_segments="populated"`；
- `helper_versions` canonical tuple 精确为依赖顺序 `("floor_footprint_v1", "facade_visibility_v1")`；不得按 set/hash-map 顺序输出；
- v3 若空段、缺 helper version、或列表与重算不一致：INVARIANT，不能报 `declared_unpopulated`；
- B2 历史 accepted attempt 保持 append-only，不回写；它仍可诚实显示 unpopulated；
- legacy 保持全 `not_declared`。

attempt writer 继续使用 `artifact_contract="correction_b2_v1"` 的四产物合同，不扩大 B-M 所拥有的 wire；新结果只能形成新 attempt，绝不改旧 accepted output。

`stage_version` 的唯一 owner 仍是 accepted attempt writer，但版本选择移到 `feature_state.py` 的集中策略：

```python
ReleaseKey = tuple[
    str,                    # target_schema_version
    tuple[str, ...],        # helper_versions, canonical dependency order
    FeatureState,           # cell_polygon
    FeatureState,           # per_floor_footprint
    FeatureState,           # facade_segments
    FeatureState,           # typed_north_axis
]

_CORRECTION_STAGE_VERSION_BY_RELEASE: dict[ReleaseKey, str] = {
    # legacy v1 lineage: no v3 feature/helper is declared
    ("1", (),
     "not_declared", "not_declared", "not_declared", "not_declared"): "2",

    # B2 v3 lineage: footprint features populated; facade/north only declared
    ("3", ("floor_footprint_v1",),
     "populated", "populated", "declared_unpopulated", "declared_unpopulated"): "2",

    # Vg v3 lineage: facade visibility is now populated; north remains pending
    ("3", ("floor_footprint_v1", "facade_visibility_v1"),
     "populated", "populated", "populated", "declared_unpopulated"): "3",
}

def correction_stage_version(claims: FeatureStateClaimsV1) -> str:
    key: ReleaseKey = (
        claims.target_schema_version,
        claims.helper_versions,
        claims.cell_polygon,
        claims.per_floor_footprint,
        claims.facade_segments,
        claims.typed_north_axis,
    )
    try:
        return _CORRECTION_STAGE_VERSION_BY_RELEASE[key]
    except KeyError as exc:
        raise ValueError("INVARIANT: unknown correction helper/state release") from exc
```

legacy v1 的合法 claims 精确为 `helper_versions=()` 且四项 feature 全 `not_declared`；禁止为迁就版本表伪填 `floor_footprint_v1`。字符串 `"2"/"3"` 必须只存在于这个**单一、显式、fail-closed 的完整状态 release map**，因为 stage wire 需要稳定协议标签，无法从 helper 名数学推导；version `"2"` 同时覆盖 legacy v1 与 B2 v3，但由不同完整 key 区分，不再用“version 2 必须 `facade_segments=declared_unpopulated`”这种会误拒 legacy 的事后条件。禁止在 `stage_runner.py` 散落任何 correction 版本字面量或 schema 分支。`StageRunner.record()` 对**所有** `FinalizeResult` 在 writer 边界重派生并核对 `expected` claims 后，无条件执行 `stage_version = correction_stage_version(expected)`；未知 schema/helper/state 组合必须先显式登记新 release，不能静默沿用 `"2"/"3"`，也不能信任 caller 传入的 `stage_version` 覆盖 correction release。

## 10. 配置与 A0 登记

### 10.1 `correction.yaml` / `CoreTolerances`

新增且只新增：

```yaml
facade_visibility_depth_epsilon_m: 1.0e-9
facade_visibility_endpoint_epsilon_m: 1.0e-9
```

`CoreTolerances` 增同名 finite positive float，**两个 dataclass 字段均禁止默认值**；YAML loader 必填读取，所有生产代码与测试中的直接 `CoreTolerances(...)` 构造点也必须显式传入两值。不得为既有 test helper 设置例外：helper 的 base dict/fixture 必须显式加入 `facade_visibility_depth_epsilon_m=1.0e-9` 与 `facade_visibility_endpoint_epsilon_m=1.0e-9`，需要覆盖时再由测试逐项 override。缺任一参数在 Python 构造边界直接 `TypeError`，缺 YAML key 在 loader 边界 fail closed；两条路径都不得 silent default。`validate()` 增：

```python
0 < facade_visibility_depth_epsilon_m < structural_snap_grid_m
0 < facade_visibility_endpoint_epsilon_m < min_edge_length_m
```

两值是数值等价/退化硬门，不是测量 uncertainty、建模精度或吸附半径；不得复用 `OUTPUT_PRECISION`、`SNAP_GRID`、`MIN_EDGE_LENGTH`、coverage area tolerance 或 facade cross-check tolerance。

### 10.2 A0 §4

追加两行：

| name | value | unit | status | profiles | hard/warn | basis |
|---|---:|---|---|---|---|---|
| `FACADE_VISIBILITY_DEPTH_EPSILON` | `1e-9` | m | provisional | orthogonal_polygon/v3 | INVARIANT tie/negative-depth guard | 只吸收 IEEE-754 运算噪声；比 10mm structural grid 小七个数量级，不代表物理可分辨率 |
| `FACADE_VISIBILITY_ENDPOINT_EPSILON` | `1e-9` | m | provisional | orthogonal_polygon/v3 | INVARIANT short-edge/near-endpoint guard | 半开 sweep 的数值拓扑门；只拒绝，不吸附、不桥接 gap |

A0 同节再写明：`WorldInterval` 在 Vg/Va 中恒为 `[lo,hi)`；同深 tie 是 INVARIANT；两 epsilon 状态由未来跨 case 数值探针决定是否校准，施工者不得临场调值过用例。

## 11. 逐文件施工表

| 文件 | 施工内容 | 禁止扩张 |
|---|---|---|
| `src/agent/correction/facade_visibility.py`（新） | §4–§7 的纯 Vg、异常、wire materializer/validator | 无 I/O、gt、manifest、claims |
| `src/agent/correction/facade.py` | 新增两 frame 与 builders；旧 aggregate API 留 compatibility wrapper | 不重写现 cross-check 政策 |
| `src/agent/correction/finalize.py` | 保持原 identity compare 在 core 后，新增 materialize 必须插在 compare 后；再做 semantic revalidation；legacy bypass | 不把空→满 facade list 纳入入口快照复核；不接 Va/B5 |
| `src/agent/correction/feature_state.py` | populated 派生、helper version、集中 `_CORRECTION_STAGE_VERSION_BY_RELEASE` 与 `correction_stage_version()` | 不改 feature-state wire 字段；未知 helper release fail closed |
| `src/agent/execution/stage_runner.py` | writer 重派生 claims 后调用 `correction_stage_version(expected)`；删除 FinalizeResult accepted 分支硬编码 `stage_version="2"` | 不信 caller version；不在本文件新增 `"3"` 字面量 |
| `src/agent/correction/config.py` | 两 epsilon typed load/validate | 不加默认降级 |
| `src/configs/correction.yaml` | 两命名值及用途注释 | 不复用其他 tol |
| `skills/intake_pipeline/1_correction/A0_contract.md` | 两 registry 行、半开/tie 语义 | 不改 A1/A3 权威矩阵 |
| `tests/test_c2_vg_visibility.py`（新） | 几何穷举、metamorphic、拒绝门、strict wire | 不读 golden/gt |
| `tests/test_c2_b2_v3.py` | finalize identity 时序、feature-state、helper→stage-version release map、attempt version 集成回归 | 不改 B2 历史 fixture 语义 |
| `tests/test_deterministic_core.py` | shipped config 正负例 | 不改既有 tolerance 值 |

`schema.py` 的 FacadeSegment 字段保持冻结；若执行中发现现 validator 无法接受本文合法输出，必须回到细稿升审，禁止现场改 wire。

## 12. 穷举测试族（累计全量）

### 12.1 手写 shape fixtures

基础 open-CCW 坐标冻结为：

```python
L = [(0,0),(4,0),(4,2),(2,2),(2,4),(0,4)]
U = [(0,0),(6,0),(6,6),(4,6),(4,2),(2,2),(2,6),(0,6)]
Z = [(0,0),(4,0),(4,2),(2,2),(2,4),(6,4),(6,6),(0,6)]
T = [(0,0),(6,0),(6,2),(4,2),(4,6),(2,6),(2,2),(0,2)]
FULL_OCCLUDE = [(0,0),(6,0),(6,2),(2,2),(2,4),(6,4),(6,6),(0,6)]
```

`Z` 从 South 看时，浅段 `[0,4)` 只遮深段 `[2,6)` 的 `[2,4)`，故深段 visible 精确为 `[4,6)`；`FULL_OCCLUDE` 从 South 看时，浅段 `[0,6)` 使深段 `[2,6)` visible 为空。每个 fixture 先经独立简单多边形断言，避免测试用坏形状证明算法。

### 12.2 穷举矩阵

1. **矩形基线 + frame 双翻转**：四 family 各一段、depth=0、visible=full；p1→p2 sign、normal、base、world interval 精确；每 family 穷举 `mirrored ∈ {False,True}` × `local_x_positive ∈ {left_to_right,right_to_left}` 四格，逐格断言 §3.2 XOR 真值表及 along origin；unknown mirror 拒。另锁旧 wrapper 既有矩形行为。
2. **L/U/Z/T 全方向**：每 shape × 四个 90° rotation × x reflection × 四 directions，几何同构去重后全跑；基础实例用手写 expected intervals，变换实例用独立坐标变换后的 expected，不调用被测 skyline 造 oracle。
3. **编码不变性**：每实例的 cyclic start 全枚举、open/closed、CW/CCW；最终 `model_dump_json()`、ids、排序逐字节相同。
4. **全遮挡**：`FULL_OCCLUDE` 及四旋转；深段仍在 list、visible 空，浅段 full。
5. **部分遮挡 / 双端与 merge 机制**：`Z` 及其镜像/旋转分别覆盖深段左端被遮、右端被遮（“双端遮挡”指两组 mirrored fixtures 各遮一端，不声称同一物理段同时留下两岛），深段保留精确半开 residual；另对 `_merge_adjacent_atoms` 做 leaf 单测，精确相邻 atoms 必合并、存在正宽真 gap 必保持两个 intervals。单一无洞简单环下，同一物理 edge 不可构造左右两个 visible islands：4×4 cell lattice 的 4,111 个单 Polygon × 四方向独立探针为零反例，故删除该不可实现的 end-to-end 字面验收项，仅保留真-gap merge 机制覆盖。
6. **同深 INVARIANT**：直接对 internal skyline leaf 注入两个同深正宽重叠 candidates；覆盖 exact equal、差 `epsilon/2`、差 `epsilon` 均 raise；差 `2*epsilon` 唯一浅者胜；再测 tie 在更深层也 raise。
7. **端点半开**：`[0,2)` 与 `[2,4)` 只接触不竞争；三段同点 begin/end；最右端不生成零宽 atom；精确相邻 visible atoms 合并；真实 gap 不桥接。
8. **端点 epsilon**：edge length 等于/小于 epsilon 拒；两个 distinct events 差 epsilon/2 与 epsilon 拒，差 `2*epsilon` 保留；不得观察到坐标被 snap。
9. **depth 符号**：四方向各造浅/深段，断言 support 段 0、内缩段正数、旋转后数值相同；微小负值正规化 0、超 epsilon 负值拒。
10. **退化族**：少点、重复点、零面积、斜边、bow-tie、自触、non-adjacent touch、backtrack、非有限、bool、multi-ring、非 cardinal direction 全部逐 code 断言。
11. **segment identity**：同几何不同 ring 编码 id 相同；改 family/plane/任一 endpoint id 改；同 geometry 不同 floor id 不同；source fingerprint 必等唯一 helper 输出。
12. **strict wire**：每 shape 全结果均为 `FacadeSegment` 实例并通过 `CorrectedGeometryV3`；visible 排序/不交/contained；手改 fingerprint、interval、normal 由现 schema 拒。
13. **全楼排序**：打乱 floors、directions、candidate 输入次序，materialized bytes 相同并符合 §7.3。

### 12.3 集成与边界测试

14. **finalize producer 权限 + identity 时序**（`tests/test_c2_b2_v3.py`）：v3 producer 预填 segment 仍拒；空输入经 core 后由 Vg 填满；Vg 用的是 core 后 final ring，不是 producer 前值；spy/fixture 断言 `_identity_snapshot` compare 发生于 materialize 前且只发生该次，合法空→满不 raise；core 偷改 floor id、window floor/ref 仍由 end-to-end finalize raise，segment identity 分量用绕过 producer parser 的 `_identity_snapshot`/mock-core 单元 guard fixture 锁定仍参与原三元比较。
15. **双路径 parity**：同 v3 fixture 走 integrated/stepwise，共同 finalize 产语义与 promoted artifact 字节相同；feature state populated、helper versions 完整。
16. **append-only + stage-version owner**（`tests/test_c2_b2_v3.py`）：`test_correction_stage_version_from_helper_versions` 断言 B2 exact helper tuple/state→`"2"`、Vg exact tuple/populated→`"3"`、未知 helper/错 state 均 INVARIANT；`test_vg_attempt_uses_derived_stage_version` 断言即使 caller 传 `"1"`/`"9"`，新 Vg accepted attempt 仍由 writer 记 `"3"`，且 `stage_runner.py` 无 correction `"3"` 字面量。B2 旧 accepted attempt 不变；artifact contract 仍四键且 hash 全通过；001 accepted→002 Vg blocked 时下游仍绑 001。
17. **legacy 零回归**：v1/v2 finalize 不调用 Vg、无新字段、现 rectangle output bytes/行为不变。
18. **纯度哨兵**：模块 import graph 无 gt/judge/manifest/LLM；显式 tol 下同输入重复调用相等；测试中封锁 `open`/env/config loader 后 Vg 仍可运行；输入对象深拷贝前后相等。
19. **配置**：默认 YAML 两值精确加载；缺键、0、负、NaN/inf、违反上界均拒；env override 仅由外层 loader 读取，Vg leaf 不读取。
20. **Va seam（只测合同）**：local interval 经四标准 ViewProjectionFrame 与 mirror 映射后，和 Vg visible interval 做纯区间交得到预期；plan-source fixture 明示不调用 visibility。不得在本批实现 applicability schema。
21. **property oracle**：对小整数格上所有不重复的合法 orthogonal simple rings（限制顶点数以控制时长）穷举；用独立 ray-first-hit oracle 对每个 atom 验证 Vg winner，且旋转/反射保持等变。oracle 不复用 Vg candidate/sweep helper。
22. **零 golden**：不改现有 sm20/sm21 golden；全量测试绿，strict xfail 集合不变。新增失败必须归因，不许更新 golden 吞回归。

## 13. 验收与复核清单

施工完成须同时满足：

- §11 文件范围内完成，`schema.py` wire 零变更；
- §12 全测试族通过，全量 suite 绿、零 golden；
- `rg` 证明 Vg 模块无 gt/judge/manifest/LLM/I/O import；
- 四方向 rectangle、Z partial、FULL_OCCLUDE、same-depth、half-open 五组结果在执行简报逐值列出；
- integrated/stepwise 产物及 feature sidecar hash parity；
- 新 config 与 A0 名称/值/语义逐字一致；
- 独立交叉复核者只看本文、diff、测试即可重建算法，不依赖聊天上下文；
- 谁施工谁不作最终批准；发现 wire 或 scope 缺口回到细稿，不现场扩批。

## 14. 施工顺序建议（不扩大放行）

1. config + A0 + `VisibilityTolerances`；
2. frame split 与 legacy equivalence tests；
3. ring canonicalization/validation；
4. candidate/depth/identity；
5. skyline + half-open/tie tests；
6. strict wire materializer + per-floor fingerprint；
7. finalize identity 时序 + feature-state release map + StageRunner 派生版本接线；
8. metamorphic/property/integration/full suite；
9. 执行简报与独立复核。

## 15. 开放问题

无。本文已冻结 depth 符号、epsilon 值与用途、半开端点、同深纪律、frame 分工、id preimage、排序、纯函数边界、Va 接缝、finalize 写入点及 stage version；施工者无需临场拍板。
