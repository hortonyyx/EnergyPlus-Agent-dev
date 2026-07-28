# 设计稿 · 判卷器「诊断仲裁 + 守恒判据 + 来源身份」

- 日期：2026-07-28
- 出案：sol
- 版次：主控终审补稿（累计式、自包含全文）
- 状态：GLM 跨家族对抗审 `APPROVE-WITH-CHANGES`、主控终审方向批准；待主控只核补正项后转施工基线
- 权威 brief：`AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_and_provenance_brief.md`
- 唯一权威终审：`AI_agent/logs/reviews/verdict/2026-07-28_judge_arbitration_design_controller_final.md`
- 本轮角色纪律：本文作者不参与本稿审阅

> 本文是施工基线候选，不是代码补丁。本轮不修改任何生产码、测试或 GT。
> 本版已把 CapabilityEnvelope 传播、alias 证书和未知 predicate 可见性三项补正写入设计本体；
> 后文不依赖任何被覆盖旧版正文，一个新执行者只读本文即可施工。

---

## 0. 拍板摘要

三条缺口用一条共同原则收口：

> **判卷结论必须由可复算的证书支撑，不能由执行顺序、错误文案、浮点偶合或未保留的语义前提支撑。**

具体决定如下。

1. **缺口 A：证书式仲裁。**
   配对器不再直接把诊断标成“真破裂”或“能力不足”。每个诊断必须携带原始来源边、owner、发生区间和依赖的 capability 不确定域。中央证明器只把“在该不确定域的所有可接受解释下仍成立”的冲突认证为 `CERTIFIED_CONFLICT`。其余分成 `CONTINGENT`（可能是 capability 派生症状）和 `CAPABILITY`。请求级裁决恒为：

   ```text
   任一 CERTIFIED_CONFLICT  -> 评分合同拒绝（红）
   否则任一 CONTINGENT/CAPABILITY -> unsupported（NA）
   否则 -> 进入计分
   ```

   `reason` 只负责展示，永不参与严重性判定。仲裁覆盖整次请求的所有楼层，而不只覆盖某个 helper 的三只 bucket。

2. **缺口 B：区间原子账本。**
   不再比较“顺序累加的 covered”和“另一路算出的 length”。每条 target 和 observation 都建立自己的闭区间参数域；所有覆盖先切成互不相交的原子，再按原子上的 owner 集合记账。一个 observation 原子若同时被两个不同 target 收费，结构上就是重复记功，立即拒绝；相邻 target 只共享切点，不构成重叠。binary64 输入先无损进入 exact-rational 账本，`extra` 是 observation 域中未覆盖原子的并集长度，不再由 `length - covered` 得出，因此没有负 extra 可被吞。

3. **缺口 C：来源保真、候选归并、拓扑举证。**
   GT、correction、reading 的适配器在浮点被送入聚类前，为每次坐标出现建立稳定的来源 key。聚类器改收 `CoordinateOccurrence`，代表映射按来源 key 查询，不能再用裸 `float` 当唯一键。距离只生成“可能归并”的候选；不同来源的两个不等值若要焊成同一原子，必须有来源/拓扑关系给出的 alias 证书，随后还要通过完整的归并后拓扑合同。版本、来源 key、原始 binary64、归并直径和 owner 关系全部进入审计上下文。

4. **未知证明谓词有意 fail-safe，但不得静默。**
   首批 evaluator 不是“获准判红的名字白名单”。任何诊断都可借已有通用谓词举证；真正出现新谓词而没有 evaluator 时，仍有意降级为
   `diagnostic_evidence_incomplete` capability NA，因为 R-4 禁止判卷器在不会证明时定罪。这个取舍会漏放未知真破裂，故每个此类降级必须进入请求级
   `missing_predicate_evaluator_count`，并通过与既有 advisory 同一类的结构化运行时产物发出逐项事件和汇总事件；即使同一请求最终因别的认证冲突判红，计数也不能丢。

三条机制共享一个中间表示：

```text
现有 wire（不加字段、不改 GT）
        |
        v
来源保真的 SourceGeometryDocument                 [C]
        |
        v
文档内身份求解 + alias/拓扑合同
        |
        v
边事实图 + capability 不确定域 + 冲突主张          [A]
        |
        v
请求级证明与仲裁
        |
        +---- 红 / NA
        |
        v
支撑线注册 + target/observation 区间原子账本       [B]
        |
        v
计分行
```

这条顺序是规范的一部分：**C 为 A 提供来源事实；A 成功后 B 才可计量。**

---

## 1. 范围、术语与不变量

### 1.1 本轮只解决什么

- A：诊断并存、派生症状与独立冲突的仲裁。
- B：target/observation 长度守恒和负 extra。
- C：坐标出现值的来源身份、合同版本以及归并后的完整拓扑合同。

不重做已经成立的聚类阈值、文档内身份池、产品向答案单向注册、长度分母、联合切点和 criterion 三分。

### 1.2 “红”不等于“上游几何非法”

本文中的红只有两种含义：

- **评分输入身份合同无法成立**；或
- **若继续计分会发生可证明的分母污染/重复记功。**

判卷器不得输出“生产几何非法”的结论。既有稳定码如
`score_product_identity_invalid` 可为兼容保留，但人可读消息和新增
`context["authority"]` 必须明确写成 `scoring_identity`，不得把它解释为生产校验裁决。

`unsupported` 的含义保持为“生产端可以接受，但当前判卷能力无法形成唯一、可靠的计量解释”。

### 1.3 三种边界状态

| 状态 | 机械定义 | 出口 |
|---|---|---|
| 真破裂（本文称“认证冲突”） | 有完整 witness，且冲突谓词对所有 capability 可接受解释均为真 | 红 |
| 量不了 | 有明确 capability，不能形成唯一计量解释 | NA |
| 分不清 | 某个看似 identity 的症状会随 capability 的可接受解释出现或消失，或诊断缺证书 | NA |

“分不清”不是第四种错误码优先级；它是 capability 的一种。

### 1.4 必须保持的已有事实

- `merge=1e-12`、`split=1e-11`、`diameter=1e-12`，直径上限仍为
  `<= merge`。
- GT 与产品身份池分开；跨文档只走判卷容差层；产品只向答案单向注册。
- 答案原子和分母仍是答案字节的纯函数。
- W5 共享正交判据和 paired/unpaired advisory 运行时日志保留。
- sm21 继续在旧分派缝直接离开，不实例化本文任何新对象。

---

## 2. 共同中间表示与错误协议

### 2.1 `SourceGeometryDocument`

施工时新增 judge-only 内存结构；它不是 wire schema，不能写回 GT 或产品：

```python
@dataclass(frozen=True)
class CoordinateSourceKey:
    side: Literal["gt", "product"]
    floor_id: str
    owner_kind: str
    owner_id: str
    ring_id: str | None
    element_index: int | None
    endpoint_side: str | None
    axis: Literal["x", "y"]

@dataclass(frozen=True)
class CoordinateOccurrence:
    source_key: CoordinateSourceKey
    value: float
    value_hex: str
    use_site: str

@dataclass(frozen=True)
class SourceVertex:
    vertex_id: tuple
    x_source: CoordinateSourceKey
    y_source: CoordinateSourceKey
    raw_point: tuple[float, float]

@dataclass(frozen=True)
class SourceEdge:
    edge_id: tuple
    owner_kind: str
    owner_id: str
    start_vertex_id: tuple
    end_vertex_id: tuple
    predecessor_edge_id: tuple | None
    successor_edge_id: tuple | None
```

要求：

- `source_key` 标识 wire 中的坐标槽位，不由坐标数值生成。
- 一个槽位被多个消费者读取时，产生相同 `source_key`、不同 `use_site` 的样本。
- `_AxisIdentity.rep` 改为按 `CoordinateSourceKey` 查询；禁止再以裸 float 为唯一审计身份。
- 所有排序均使用上述结构 key；输入迭代顺序不得影响代表点或裁决。

### 2.2 非抛出式分析报告

内部分析函数不得在遇到第一个问题时终止楼层遍历：

```python
@dataclass(frozen=True)
class AnalysisReport:
    partial_segments: tuple[PlanSegment, ...]
    diagnostics: tuple[JudgeDiagnostic, ...]
    capabilities: tuple[CapabilityEnvelope, ...]
    audit: IdentityAudit
```

- GT、correction、reading 各自先返回报告。
- v3 的请求级入口收齐所有相关楼层/文档报告后只调用一次仲裁器。
- 现有 `extract_*` 公共函数可保留为兼容 wrapper，但 wrapper 也必须先分析完该文档全部楼层再裁决。
- capability 楼层可以不产出可评分 segment，但不得因此阻止其他楼层产出认证冲突证据。

这样，输入列表顺序、bucket 顺序和楼层顺序都不再有定案权。

### 2.3 诊断协议

```python
@dataclass(frozen=True)
class ConflictWitness:
    predicate: str
    predicate_schema_version: str
    source_edge_ids: tuple[tuple, ...]
    source_vertex_ids: tuple[tuple, ...]
    owner_ids: tuple[str, ...]
    locus: GeometricLocus

@dataclass(frozen=True)
class ContractWitness:
    predicate: str
    predicate_schema_version: str
    source_keys: tuple[CoordinateSourceKey, ...]
    observed_hex: tuple[str, ...]
    expected_contract_version: str | None
    observed_contract_version: str | None

@dataclass(frozen=True)
class JudgeDiagnostic:
    diagnostic_id: str
    requested_code: str
    gate_id: str
    reason: str
    floor_id: str
    witness: ConflictWitness | ContractWitness | None
    caused_by: tuple[str, ...]
```

诊断生产者只能提出主张，不能自行填写 `category="identity"` 取得红色资格。
中央证明器根据 witness 和 capability envelope 计算最终状态：

```text
CERTIFIED_CONFLICT
CONTINGENT
CAPABILITY
DISPROVED（丢弃）
```

没有 witness 的冲突主张不得默认判红；证明器为其生成
`diagnostic_evidence_incomplete` capability，并以 NA 收口。witness 完整但
`(predicate, predicate_schema_version)` 没有 evaluator 时也走同一 NA 出口，
但必须按 §4.3.2 计入运行时产物。新增一个 reason 不会自动获得定罪权；
新增一种判卷器还不会证明的真破裂也不会静默消失。

### 2.4 审计上下文最低字段

所有 A/C 新路径至少记录：

- `authority="scoring_identity"`；
- `contract_version`；
- `side`、`floor_id`；
- `diagnostic_id`、`proof_status`；
- `predicate`、`predicate_schema_version`、命中的 evaluator key；无 evaluator 时记录
  `missing_predicate_evaluator=true`；
- source vertex/edge/owner keys；
- 发生区间两端的十进制值和 binary64 hex；
- 涉及归并时的全部原值 hex、`diameter`、`diameter_hex`；
- `depends_on_capability_ids`；
- capability envelope 的种类和端点 hex。
- 请求级 `missing_predicate_evaluator_count`、按 predicate 排序的 histogram 和最终请求出口。

只记 `reason/floor_id` 不再满足合同。

---

## 3. 缺口 C · 来源身份与输入身份合同

### 3.1 判据凭什么立足

这里严格分开三个概念：

1. **来源槽位**：由 wire 结构和稳定 id 决定；不看距离。
2. **数值候选簇**：沿用已成立的单链接、护带和直径守卫；距离只在这里提出候选。
3. **意图原子**：同来源一致性，或不同来源之间有可机械复算的 alias 证书，并通过归并后拓扑合同后才成立。

因此，`abs(a-b) < merge` 的含义只是“值得尝试证明这两个出现值可共用一个原子”，不是“已经证明同一意图”。

### 3.2 各输入的来源 key

| 输入位置 | 来源 key（另加 side、axis） |
|---|---|
| GT footprint 顶点 | `(floor_id, "footprint", ring_id, vertex_index)` |
| GT zone 顶点 | `(floor_id, "zone", zone_id, ring_id, vertex_index)` |
| GT boundary 端点 | `(floor_id, "boundary", segment_id, "p1"/"p2")` |
| correction footprint 顶点 | `(floor_id, "footprint", "exterior", vertex_index)` |
| correction cell 显式 polygon 顶点 | `(floor_id, "cell", cell_id, "exterior", vertex_index)` |
| correction cell 的 x/y 矩形回退 | x 槽为 `(floor_id, "cell_rect_v1", cell_id, "x", 0/1)`；y 槽同理。两个派生 corner 若读取同一个 x/y wire 槽，必须复用同一 source key |
| reading observation 端点 | `(floor_id, "reading", observation_id, "p1"/"p2")` |

补充规则：

- 当前 `c2_simple_orthogonal_no_holes` GT profile 强制 footprint/zone
  `interior_rings` 为空，v1 的 `ring_id` 只会是 `"exterior"`；`hole_id`
  是未来带洞 geometry profile 的扩展槽，不表示现有 GT 已支持洞。
- 存在稳定 id 时不以列表 ordinal 代替 owner id；顶点索引仍是该 owner 内部来源的一部分。
- 显式闭环尾点保留自己的来源记录，并以 `explicit_ring_closure` 关系连接首点；不能在记录来源前直接丢掉。
- duplicate owner id、duplicate reading id 或同一 source key 指向两个不同 wire 槽位，均为
  `score_identity_contract_mismatch`。
- GT 的 `source_refs` 不足以逐顶点定位，不能拿它替代上述结构 key；也不增加 GT 字段。

### 3.3 合同版本：内存协议，不改输入格式

新增 `IDENTITY_CONTRACT_VERSION = "1"`，由适配器写进内存 envelope：

```python
IdentityInputEnvelope(
    contract_version="1",
    source_schema=("gt_v3" | "correction_v3" | "reading_plan_v1"),
    ...
)
```

- 版本由现有 typed 分派得出，不要求上游传新字段。
- `_build_floor_identity` 只接受单一、受支持的 contract version；缺失、混用或未知版本均发出
  `score_identity_contract_mismatch / identity_contract_version_mismatch`。
- contract version 进入 scorer identity 的方式在本文定死为**编码进 helper identity 串**，
  不给 `ScoreIdentityV8` 新增字段：

  ```python
  IDENTITY_CONTRACT_VERSION = "1"
  SEGMENT_SCORER_HELPER_VERSION = "b4b_segment_score_v3_ic1"
  IDENTITY_CONTRACT_TO_SCORER = {
      "1": "b4b_segment_score_v3_ic1",
  }
  ```

  `HelperIdentityV8.segment_scorer` 的 Literal **只**改为
  `Literal["b4b_segment_score_v3_ic1"]`（不保留 v2 union），
  `score_typed_attempt` 的构造值同时改为该精确字符串。
  builder 必须断言 envelope version 经上表映射后等于 helper identity；未来 identity
  contract v2 必须换新 helper 串，不能继续冒充 `...ic1`。
- 选择 helper 串而非 `ScoreIdentityV8` 新字段的后果是：`ScoreIdentityV8` 结构和 sidecar
  schema version 保持不变，但 canonical identity/hash 因
  `helpers.segment_scorer` 改变；所有旧 typed c2 v3 派生 sidecar/cache 都成为 cache miss。
  旧 `"b4b_segment_score_v2"` typed c2 v3 sidecar 会在新 strict model validation 失败，
  `load_cached_score` 按既有协议返回 cache miss；不得给当前 builder 加“仍接受 v2 helper”
  分支。GT content hash、签字答案和产品 artifact hash 均不变化。
- sm21 不创建 envelope，因此其 scorer identity、分数和渲染均不变。

这使码表中已有的 `score_identity_contract_mismatch` 具有真实、可达的发射路径。

### 3.4 身份求解算法

每个 `(side, floor, axis)` 独立执行以下步骤。

#### C-0 · 来源完整性

1. 校验 contract version。
2. 校验 source key 唯一性和 owner id 唯一性。
3. 校验每个 occurrence 为有限 binary64。
4. 保留所有原值和 use site，不去重来源。

失败即评分身份合同拒绝；context 必须能从 hex 和 source key 复算。

#### C-1 · 同来源一致性

按 `source_key` 聚合全部样本：

- 直径 `<= merge`：作为一个来源槽位继续。
- 直径 `> merge`：`score_identity_contract_mismatch /
  same_source_coordinate_spread`。

直径用样本的 min/max 计算并记录 exact binary64；这里验证的是同一来源槽位在管线内有没有被不同算法改写，不以距离反推来源。

#### C-2 · 数值候选簇

对每个来源槽位的值执行已成立的：

- 单链接；
- merge/split 护带；
- 簇直径 `<= merge`；
- 代表点为簇最小值；
- 排序与输入顺序无关。

护带内仍是现有的响亮歧义码；阈值一字不改。

#### C-3 · 不等值跨来源 alias 证书

候选簇中，两个不同 source key 的值若逐位相等，不发生近似归并；它们共享同一个数值原子，并由 C-4 检查其拓扑用途。

若值不等但因 `< merge` 落入同一候选簇，必须建立 alias 证书。证书判定与距离候选判定在 API 上隔离：

```python
def certify_alias(
    left: CoordinateSourceKey,
    right: CoordinateSourceKey,
    axis: Literal["x", "y"],
    topology: SourceTopologyIndex,
) -> AliasCertificate | None:
    ...
```

该函数收不到 `left.value/right.value`、gap、merge/split/diameter 阈值；实现模块也不得
import 这些阈值。数值层只负责在证书判定前产生待证明的 key pair。证书层只回答：
**不看这两个候选值相差多远，wire 是否把这两个坐标槽放进同一个拓扑接点。**

适配器在聚类前从 wire 建立下列结构索引，索引 id 均由字段位置和稳定 id 生成：

```python
RingHalfEdgeRef(
    side, floor_id, owner_kind, owner_id, ring_id,
    edge_index, start_vertex_index, end_vertex_index,
    direction_axis, direction_sign,
)

BoundaryEndpointRef(
    side, floor_id, boundary_loop_id, source_footprint_fingerprint,
    facade_family, outward_normal, segment_id,
    endpoint_side, interval_role, chain_rank,
)
```

- `start_vertex_index=i`、`end_vertex_index=(i+1) % n` 只取自 ring 顶点序号；显式闭环尾点另以
  `explicit_ring_closure` 连到序号 0。
- `direction_axis/sign` 只比较**同一条 edge 自己的**两端：哪个分量逐位相等、另一个分量的正负号是什么。它不比较两个 owner 的距离。
- boundary 的 `interval_role` 是 `"lo"` 或 `"hi"`。适配器用 segment 自己的
  `p1/p2` 沿轴值与其 `world_along_interval.lo/hi` 的逐位相等关系确定角色；不允许近似匹配。
  GT 的 `boundary_loop_id` 直接取 wire。correction facade segment 只有在
  `source_footprint_fingerprint` 与该 floor 的显式 footprint fingerprint 相同且 profile
  声明它属于 exterior loop 时，adapter 才可派生 `boundary_loop_id="exterior"`；否则没有
  boundary-chain 证书。

允许的 v1 证书及机械规则如下。

##### C-3a · `same_source_reuse` / `explicit_ring_closure`

- `same_source_reuse` 只适用于两个 use site 指向**同一个** source key；它先走 C-1，不是跨来源兜底。
- `explicit_ring_closure` 只连接同一 owner/ring 中 wire 明确给出的闭环尾点与
  `vertex_index=0`。普通的两个近邻顶点不能冒充 closure。

##### C-3b · `paired_edge_endpoint`

对正在证明的轴 `a`，令另一轴为 `b`。只有以下步骤全部成立才发证：

1. 两个 key 必须分别是 half-edge `e/f` 的端点在轴 `a` 上的坐标槽；`e/f`
   位于同一 `side/floor/profile`，owner id 不同，且 endpoint 与 edge 的归属由上述 ring
   序号直接可查，不能拿任意近邻 vertex 拼边。
2. `e/f` 各自在轴 `a` 上为常量边，在轴 `b` 上非零；两条边的
   `direction_axis` 相同、`direction_sign` 相反。这里的“常量/方向”只读每条边内部的两个
   source 槽，不读 `e` 与 `f` 在轴 `a` 上的间距。
3. 用**已经独立解决**的轴 `b` 原子建立两条有向 span，取联合 cut 后原子化。某个正长度
   atom 上必须恰有 `e` 所属的一个 forward owner 与 `f` 所属的一个 reverse owner；
   owner 不同。完整反向边是一个 atom，长边对多短边的 T-junction 是多个 atom，规则相同。
4. 在该 atom 的两端，endpoint 配对严格取 ring 序号给出的
   `e.start ↔ f.end`、`e.end ↔ f.start`；T-junction 端可是一侧 edge endpoint 对另一侧
   long-edge 的 cut，但 cut 必须由轴 `b` 上已有的 source endpoint token 产生。
5. 该证明不得依赖正在证明的轴 `a` 的 representative，也不得经另一张 alias 证书绕回本
   key pair。alias 证明依赖图必须可拓扑排序；环依赖一律视为无证。

通过后，证书只授权 `e/f` 在轴 `a` 上参与该 paired atom 的常量端点槽互为 alias；
不授权同 owner 的其他顶点，也不授权同 floor 上恰好接近的平行边。尤其禁止把
`abs(const_e-const_f) < merge`、欧氏端点距离或“最近反向边”写进任一步。

##### C-3c · `boundary_chain_endpoint`

只有一个**已声明 boundary loop 的相邻槽位**可发证：

1. key pair 必须是（a）同一声明 loop 上两个不同 segment 的 boundary endpoint，或
   （b）一个 boundary endpoint 与该 chain junction 唯一映射到的 footprint ring vertex；
   二者须同 `side/floor/boundary_loop_id/source_footprint_fingerprint`。相同 facade family
   时 outward normal 必须相同；跨 corner 时 family/normal 必须与相邻 ring half-edge 的方向表一致。
2. 对同一 ring half-edge/facade family，按
   `(world_along_interval.lo, world_along_interval.hi, segment_id)` 的 exact 值排序。
   仅排序后相邻的 `left.hi` 与 `right.lo` 是一个连续槽位；必须满足各 interval 自身有序、
   不嵌套、不 exact-overlap，且中间没有第三个 segment。这里不检查
   `abs(left.hi-right.lo)`，也不以阈值决定“相邻”。
3. 对 corner，连续槽位只由 ring 序号
   `edge[i].end_vertex_index == edge[(i+1)%n].start_vertex_index` 给出；闭环 junction 只由
   `(n-1) -> 0` 给出。坐标接近不能创建、跳过或改写这个序号关系。
4. 待证明 key 必须正是上述两个槽位在所求 axis 上的 source key。boundary↔ring 只可映到
   同一 declared junction 的唯一 `vertex_index`；任一 endpoint 无法唯一映射到
   `interval_role` 或 ring junction 时，不发证。

`world_along_interval` 在这里用于确定 wire 已声明链上的**次序和端点角色**，不是用于测两端
有多近。即使把两个候选值改成相差 1 m，只要 owner、ring 序号和 interval 槽位不变，证书层的
结构关系仍应得到同一答案；只是 C-2 不会再把它们放入同一候选簇，C-4 随后会把真实大缝判成
拓扑问题。这条变形性质是 C-L4 的必测断言。

##### C-3d · `profile_axis_constraint`

当前 profile 可以证明一条源 edge 的两个端点共享同一常量轴槽时，adapter 可发
`profile_axis_constraint`；证书必须引用 profile version、edge id、ring 序号和被约束 axis。
通用求解器不写死“所有建筑都正交”。未来非正交 profile 可以不注册它，改注册自己的结构关系证明。

##### C-3e · 证书图求解与终止

1. C-2 为每个不等值 candidate pair 建 proposal；proposal 只含结构条件和所依赖的其他-axis
   atom/certificate id。
2. `same_source_reuse`、wire 明示 closure 和不依赖其他 alias 的 boundary/ring relation
   先进入 accepted set。
3. 按 canonical proposal id 反复接纳“全部依赖已 accepted 且 C-3a–d 规则成立”的 proposal。
   每轮至少接纳一项，否则停止；proposal 有限，故必终止。
4. 停止后仍未解决的 proposal（包括 alias dependency SCC）没有证书，不能靠同一 SCC
   互相背书。对每个 candidate cluster 检查：每个不等值 source node 都能沿 accepted
   certificate edge 连到 canonical anchor；否则发 `unproven_cross_source_alias`。
5. 仅在整簇通过后才提交 `source_key -> cluster minimum representative`；失败簇不得先局部
   改写几何再报错。

每张证书必须列出两端 source key、证书种类、支撑 edge/owner/ring/interval 槽、
原始 hex 和证明依赖。候选簇内每个不等值来源必须通过**无环证书图**连到该簇的一个已证成员；
只靠逐位相等形成的数值原子不替别的不等值 pair 背书。

证书实现不可避免会读取三类数值：单条 edge 内的 exact 方向、单个 boundary segment 内
`p1/p2` 与 `world_along_interval` 的 exact 自洽、以及非待证明轴上的 exact span 顺序。
这些读取均不计算两个待 alias 坐标的距离，也不拿 merge 阈值推断意图；它们验证的是 wire
自身角色和独立拓扑 join key，因此不构成“距离反推意图”的循环。

若只有数值接近而没有上述任一结构关系，发出
`score_identity_contract_mismatch / unproven_cross_source_alias`，不得静默归并。

#### C-4 · 归并后完整拓扑合同

用 `source_key -> representative` 重建几何，再执行以下检查。检查器使用精确 dyadic orientation/intersection predicate；宽相位用 AABB/sweep index，不能以全层两两暴力比较作为长期架构。

C-4 的检查器统一**产出带 witness 的合同主张，不在本地立即 raise**。没有 capability 依赖的主张会在 §4 被认证为评分身份合同拒绝；若某个交叉、坍缩或 owner 症状的必要端点来自 capability envelope，则同样接受 §4 的 contingent 判定。这样不能在 `self_touch` 等新 reason 上重建一条绕过仲裁的假红路径。C-0 至 C-3 的版本、来源一致性、护带和无证 alias 属纯输入合同事实，不依赖几何 capability，可直接形成认证 contract witness。

**ring：**

- 去掉被明确标为 closure 的尾点后至少三个不同顶点；
- 包括闭合边在内，任一相邻顶点不得坍缩；
- 非相邻顶点不得重复；
- 非相邻边不得 proper-cross、touch 或 collinear-overlap；
- 相邻边只能共享声明的公共端点，不得回折覆盖；
- interior ring 与 exterior/其他 interior ring 因归并新增的触碰或交叉同样拒绝。

这里不规定建筑必须无洞、必须矩形或必须正交；profile 只决定哪些 ring 关系本来允许，身份合同只禁止归并后无法形成唯一边界身份的关系。

**boundary / reading segment：**

- 两端归并后不得相同；
- 两个不同 segment 归并成同一无向几何时，必须拒绝 duplicate-after-merge；
- context 同时保存两条 segment 的两个原始端点对、source keys、各轴直径和 hex。

**owner：**

- 同一 owner 不得在同一有向原子上出现两次；
- 反向配对的 interior 原子必须是两个不同 owner，`("Z","Z")` 永不成立；
- 同方向 owner 重数、exterior 原子多 owner、interior 原子缺一侧或多一侧都形成带 witness 的冲突主张；
- owner 检查以一般共线支撑和一维原子为接口，当前 H/V tiler 只是一个 profile 实现。

上述全部拓扑/owner 主张进入 §4 的 capability 证明器。这样 advisory 扰动产生的拓扑症状可以判为 contingent，而独立 duplicate、自交或同 owner 回折仍能认证为红。

### 3.5 C 的边界行为

| 输入形态 | 结果 |
|---|---|
| 同 source key 多次读取，直径 `<= merge` | 合并 |
| 同 source key 多次读取，直径 `> merge` | `score_identity_contract_mismatch` |
| 不同来源、值逐位相等 | 共享数值原子但保留各自 source identity；继续走 C-4 |
| 不同来源、差值在护带 | `score_identity_guard_band_ambiguity` |
| 不同来源、不等值、sub-merge 且有 alias 证书、拓扑合同成立 | 合并 |
| 不同来源、不等值、sub-merge 但无 alias 证书 | `score_identity_contract_mismatch` |
| 归并造成零长/重复/自触/owner 冲突且冲突不依赖 capability | 评分身份合同拒绝 |
| 任一归并后拓扑/owner 症状落在 capability 不确定域 | 交给 A；没有独立固定核心证书时为 NA |
| 来源缺失、碰撞、版本未知 | `score_identity_contract_mismatch` |

这些出口是在评分信任边界 fail-closed，不宣判生产几何非法。

### 3.6 C 的机械验收锁与指定 neuter

以下锁是最低集，不得用一个共用 helper 锁冒充多条独立承重锁。

| ID | 会红的锁 / 预期 | 现码状态 | 指定 neuter（实施后必须使该锁红） |
|---|---|---|---|
| C-L1 | GT、correction、reading 各取一个正式对象，断言 audit 中逐点 source key 与上表一致，且 `_AxisIdentity` 按 source key 查询 | 红：当前进聚类前只剩 float | 把适配器恢复成 `float(p[axis])` 生成器，或把 rep 改回 `Mapping[float,float]` |
| C-L2 | 向身份求解器送同一 source key 的两个样本，间距 `> merge`，精确断言 contract mismatch、两值 hex、diameter | 红：当前无法表达来源组 | 聚合键改成 raw float，绕开 same-source diameter 门 |
| C-L3 | 两个不同来源落护带，精确断言错误 context 同时含两 source key | 红：当前 context 无来源 | 在 `_cluster_axis` 入参处剥离 occurrence，只传 float |
| C-L4 | 三个历史表示漂移升级为正式夹具：sm24 `8.059999999999999↔8.06` 和 correction `0.1+0.2↔0.3` 必须各产 `paired_edge_endpoint`，1-ulp 量子边界对必须挂在真实 reverse/T-junction 或 boundary-chain 槽上产对应证书；三者生产校验、提取、计分仍绿。再把待 alias 轴差值改到 `>split` 而保持 owner/方向/ring/interval 槽不变，断言证书层关系不变、但数值层不归并 | 现有裸 helper 绿，但来源合同锁不存在 | 让证书层读取 `abs(left-right)<merge`，或对所有不等值来源无条件拒绝；至少一项变形/历史锁必须红 |
| C-L5 | 两个不同 owner/source 的 sub-merge 不等值近邻，刻意不给 reverse span、连续 boundary slot、ring closure 或 profile relation，必须 `unproven_cross_source_alias`；context 列出候选 pair 和“无结构关系” | 红：当前仅凭距离焊接 | 让 alias certifier 恒返回 true，或把 candidate gap 直接当 `paired_edge_endpoint` |
| C-L6 | 既有 polygon 相邻坍缩、boundary collapse、reading collapse 均断言原端点 source/hex/diameter 完整 | 部分红：context 不完整 | 跳过 post-merge segment/ring validator |
| C-L7 | 非相邻重复顶点 + 自触活体必须拒绝，且不能产出 `zone_ids=("Z","Z")` | 红：当前静默接受 | 把 ring validator 退回只查相邻顶点 |
| C-L8 | 单独构造 bow-tie（无重复顶点）走正式 source adapter，必须报 self-intersection | 红：当前无检查 | 令 exact non-adjacent edge-intersection predicate 恒 false |
| C-L9 | 直接给 owner atom helper 两条同 owner 反向边，必须 contract mismatch | 红：当前会配成同 owner 内墙 | 删除 `left_owner != right_owner` 守卫 |
| C-L10 | 两条 boundary 在归并后重合；断言 context 含两条 segment 的四个原端点、source keys 和 hex | 红：当前 duplicate context 不完整 | duplicate key 改用归并前几何 |
| C-L11 | 让 typed adapter 发 contract version `"2"` 给只支持 `"1"` 的 builder，正式入口必须发 `score_identity_contract_mismatch` | 红：当前无版本 | 忽略 envelope version |
| C-L12 | duplicate reading id/source key collision 必须拒绝 | 红：当前没有来源唯一性门 | 给重复 id 偷加 ordinal 使其静默唯一 |
| C-L13 | 非正交简单凹多边形通过通用 topology identity checker；非正交自交多边形拒绝 | 红：当前没有通用检查器 | 把相交检查限定为 H/V 分支 |
| C-L14 | 既有答案纯函数锁继续比较答案原子规范字节和 denominator binary64 字节 | 已有锁绿 | 非法联合 GT/产品来源池 |
| C-L15 | sm21：令新 identity adapter 一调用就 raise，既有分数字节、像素 hash、分派路径仍全绿 | 应绿 | 把 legacy 分派接入新 adapter |
| C-L16 | 保存一份改造前真实 typed c2 v3 sidecar（helper v2）及 hash；改造后新 strict model 只接受 `...v3_ic1`，旧 sidecar 经 `load_cached_score` 必须 cache miss，新 identity/hash 与 baseline 不同，GT hash 不变。envelope version `"1"` 配非 `...ic1` helper 必须 contract mismatch | 红：当前 helper 仍是 v2 且无 version 映射 | 把 Literal/构造串恢复为 v2、给当前 builder 加 v2 兼容分支，或删掉 envelope-version/helper 交叉断言 |

其中 C-L4 必须把现有三个“裸 float helper”历史锁升级成有 source/topology 的正式形态；不是删除历史反例。

### 3.7 C 的实施代价与风险

- 预计：新建一个 judge-only identity/provenance/structural-alias 模块约 450–700 行；三类
  adapter 和 `segment_score.py` 接线约 200–350 行；新增/改写约 22–30 条窄锁。
- 工作量：约 6–9 个专注工程日，属本轮最高成本项。
- 主要风险：
  - alias 证书过窄导致过多评分合同拒绝；
  - alias 证书过宽退化成数值接近即同一；
  - 通用 ring 相交检查的性能；
  - scorer identity/cache 未 bump 导致旧 sidecar 被错误复用。
- 控制：
  - 历史三绿 + 无关系 sub-merge 红构成双向门；
  - AABB/sweep 宽相位 + exact predicate；
  - contract version 进入 scorer identity；
  - 每个 merge cluster 输出 alias certificate audit。

---

## 4. 缺口 A · 诊断证明与请求级仲裁

### 4.1 判据凭什么立足

当前问题不是诊断名字不够全，而是诊断缺少“它由哪些输入事实推出”的证明对象。

新机制把判断拆成两步：

1. detector 只说：“在这些来源边、owner 和区间上，我观察到某个冲突谓词。”
2. certifier 问：“把所有当前判卷器量不了的输入按其可接受解释展开后，这个谓词是否仍然恒真？”

只有第二问得到“恒真”才有红色资格。新 reason 不需要进入任何严重性名单；它需要的是一个已注册的 witness predicate evaluator。

### 4.2 capability 不确定域

每个量不了的形态必须给出 `CapabilityEnvelope`。它不是替上游“修正”坐标，也不虚构一个最可能的轴线；它只声明：**哪些来源事实不能用于当前判卷器的红色证明。**

v1 首先覆盖 W5 的 unpaired near-orthogonal advisory。实现必须保留下列可审计对象：

```python
@dataclass(frozen=True)
class CapabilityEnvelope:
    capability_id: str
    kind: Literal["near_orthogonal_advisory_unpaired"]
    source_edge_id: tuple
    source_vertex_ids: tuple[tuple, tuple]
    seed_coordinate_keys: tuple[CoordinateSourceKey, ...]
    dependent_fact_ids: tuple[tuple, ...]
    dependency_arcs: tuple[tuple[tuple, tuple], ...]
    fixed_invariants: tuple[tuple, ...]
    complete: bool
```

`complete=False` 的 envelope 没有红色证明资格，只能 NA。`dependency_arcs`
必须允许从任何 dependent witness fact 反查到 seed，不能只存一个最终 bool。

#### 4.2.1 有限事实图

C 完成后、detector 运行前，为每个 `(side, floor)` 建一个有限、带 phase rank 的事实图。
每个派生函数必须为输出 fact 声明直接 operand；禁止在图外偷读坐标。v1 至少有：

1. `SOURCE_COORD(key)`、owner/ring/edge index 等 wire 结构事实；
2. `EDGE_ENDPOINT(edge, side, axis)`；
3. `EDGE_CLASS/EDGE_DIRECTION/EDGE_SUPPORT/EDGE_SPAN/EDGE_ON_EXTERIOR`；
4. source-labelled `CUT_TOKEN`、`CUT_ORDER` 和 `CUT_GROUP`；
5. `ATOM_SPAN`、`EDGE_COVERS_ATOM`、`OWNER_ON_ATOM`、reverse/pair slot；
6. detector 的 predicate fact 与 witness fact。

图的 rank 固定为
`source -> edge -> support/cut -> atom/owner -> diagnostic`。alias 关系在 C
已经求解，只能作为 `source -> semantic coordinate` 的前向边；cut/diagnostic
不得反向改写 source 或 alias。因此事实图是 DAG。

#### 4.2.2 seed 的机械选择

对每条**未配对** advisory source edge `e=(v0,v1)`：

1. 只采用生产与判卷已共享的 W5 classifier 结果，不增加阈值。
2. near-vertical 的 small axis 为 `x`，near-horizontal 为 `y`。若两个非零分量都落入
   advisory 范围、classifier 无法唯一给出 dominant axis，则该 edge 的 envelope
   `complete=False`，其来源结构连接分量整体 NA；不得猜 axis。
3. 令两个原始 small-axis 值为 `s0/s1`，建立 exact-rational 闭域
   `H_e=[min(s0,s1), max(s0,s1)]`。两个 endpoint 的语义 small coordinate 各自是
   `H_e` 上的符号变量；C 已证明 co-motion 的 key 共享同一个变量，其他 key 不共享。
   这个 over-approximation 同时包含原始斜边写法和在两端之间的所有 straightening，
   但不选择任何一个“修正值”，也不在端点外另造半径。若 future capability 不能给出完整、
   有界且可做 exact enclosure 的 admissible domain，则 `complete=False`。
4. seed 是 `v0/v1` 在 small axis 上的两个 `CoordinateSourceKey`，再沿 C 已认证的
   **结构 co-motion alias**（同 source reuse、explicit closure、已证 paired/boundary
   junction）取有限传递闭包。裸数值相等、sub-merge、同 floor 或“看起来同一直线”都不是 seed
   传播边。
5. edge 存在、owner id、ring/edge index、两个 large-axis source coordinate 均列入
   `fixed_invariants`。把一个 advisory edge 放进 envelope 不等于把它的 owner 或整个 ring
   都标成未知。

paired advisory 已有 exact reverse，可计量，不建立 envelope；paired/unpaired 的既有
可计数日志都保留。

#### 4.2.3 闭包 worklist

从 seed fact 开始执行下列单调算法：

```text
dependent := set(seed facts)
queue := canonical_order(seed facts)

while queue not empty:
    fact := pop_smallest(queue)
    for child in canonical_order(direct_dependents[fact]):
        if child not in dependent and child_is_variable(child, dependent):
            dependent.add(child)
            dependency_arcs.add(fact -> child)
            queue.add(child)

stop when queue is empty
```

`child_is_variable` 不留给施工方自由解释，按以下规则：

- copy、仿射值表达式、支撑坐标和 span 端点只要读取任一 dependent operand，输出值即
  dependent，并携带由 exact interval arithmetic 得到的 enclosure。
- 方向/共线/相交、cut order、bucket eligibility 等布尔比较，若所有 admissible 值都给出同一
  结果，可用 exact enclosure 证明为固定；否则 dependent。禁止用抽样、浮点 epsilon 或“当前
  这一次结果”代替全域证明。
- 一个 half-edge endpoint 的某 axis 分量 dependent，当且仅当它绑定的 source key 在 seed
  co-motion 闭包。对 advisory 顶点，前驱 edge 的 end endpoint、advisory edge 的 start/end、
  后继 edge 的 start endpoint若读取同一 key，均入闭包；**只入该 axis 分量**。相邻 edge
  的另一个顶点、该顶点的另一 axis、再下一条 ring edge不会因“相邻”自行传播。
- edge 的 source 身份和 owner 始终固定；只有 support、direction、span、axis class、
  exterior-membership 等确实读取 dependent endpoint 的派生事实入闭包。这样传播依赖数据读取，
  不是沿 ring 无条件 flood fill。
- 每个 cut 保留 source-labelled token，不能先按 float 去重后丢来源。endpoint cut 的 along
  coordinate 或 producer edge 的 support-bucket membership dependent，则该
  `CUT_TOKEN` dependent；edge/edge intersection cut 的任一支撑或交点参数 dependent，也同样
  dependent。
- pairing/cut 的潜在 interaction 不能只从当前 float bucket 枚举。对每个符号 support/cut
  enclosure，与本 floor 的有限 fixed support/span 做 exact 相交测试：全域不相交则关系固定为
  false；存在任一 admissible 相交则建立 candidate fact 并继续传播。由此 A-L1 的局部 cut 会
  入图，远处 A-L2 真缝不会因“support 未知”被整层污染。
- T-junction 的 long carrier 即使所有 source endpoint 固定，只要切它的 token dependent，
  由该 token 产生的 `CUT_ORDER`、分割 atom 和 atom owner/pairing 关系都入闭包；carrier 的
  source edge、固定 endpoints 和固定 full span **不**反向入闭包。
- exact 值相同的 cut tokens 仍分别保留。`DOMAIN_START/DOMAIN_END` 或至少一个固定 token
  可给当前位置一个固定 cut；dependent token 不会抹掉这个固定 cut，但它在其他可接受解释下可能
  移动或新增 cut，因此凡依赖它的相对次序、分区或 owner membership 仍标 dependent。
- `EDGE_COVERS_ATOM`、`OWNER_ON_ATOM`、reverse slot 或 absence 结论，只要所需 edge 的
  support/span、atom boundary、cut order 或 pairing eligibility 任一 dependent，就入闭包。
  仅 owner 字符串相同不传播 capability。
- predicate/witness 的**必要事实**有任一 dependent 时，该份完整 witness 是
  contingent；certifier 仍必须继续搜索不使用这些事实的最小固定核心。

以上规则也回答“哪些边端由小分量坐标决定”：只有 source incidence 实际复用 seed small-axis
key 的 endpoint 分量，以及读它而产生的派生 support/span/cut；不是整条相邻边，更不是整个
owner/floor。

#### 4.2.4 终止与未知依赖

source key、half-edge incidence、potential edge pair 和 symbolic cut token 都由有限 wire
笛卡尔上界枚举；连续 admissible domain 只保留 exact enclosure，不采样、不生成无限 token。
每个 fact 最多入集合一次，且边只从低 rank 指向高 rank。因此 worklist 最多处理
`|facts| + |dependency_arcs|`，queue 为空即终止。算法不按坐标半径发现新邻居，也不枚举连续的
straightening 坐标。实现可用 exact AABB/sweep index 剪枝 potential pair，但结果集合必须与
有限笛卡尔定义一致，不能靠当前 float bucket 漏项。

若 future profile 的派生函数无法声明完整 operands，必须把该函数所有输出及其下游标成
dependent；若连下游边界也无法枚举，则 envelope `complete=False`，整个来源结构连接分量
NA。禁止以“目前没看见依赖”为由把它当固定。

#### 4.2.5 固定核心与两只方向门

certifier 不得把“当前 atom id 固定”当成唯一证明方式。对正向 owner 冲突，它从固定 source
edge 的 exact support、方向和 span 直接求交：若两个非法 owner 在一个**固定正长度**
interval 上恒并存，dependent cut 即使把它再细分也不能消灭冲突，故可
`CERTIFIED_CONFLICT`。对 `missing_reverse_owner` 这类 absence 证明，只要任一
capability edge 仍可能按 dependent support/span 覆盖所缺 interval，就只能
`CONTINGENT`。

由此机械得到两只关键出口：

- A-L1 的 `5e-10` vs `4e-10` 两条 unpaired advisory 各自把 small-axis key 纳入 seed；
  与它们共顶点的相邻 exterior edge endpoint 复用该 key，两个 T-junction cut 及其间的
  derivative duplicate atom 都在闭包内。不存在固定正长度 duplicate 核心，故 NA。
- A-L3 的 A/B 两个满幅 owner 的 source edges、端点、support 和正长度交集都不经 C cell
  advisory 的 source-incidence/结构 alias 路径；数值相等或同 floor 不传播 capability。
  A/B 本身构成固定核心，故必须 `CERTIFIED_CONFLICT` 判红。

同理，A-L2 的 1e-9 真缝若来源边与 advisory 无依赖路径，或其 fixed support/span 与
advisory exact enclosure 全域不相交，仍由固定事实认证为红。传播做宽到
“同 floor 全未知”会使 A-L2/A-L3 红；传播做窄漏掉相邻 endpoint/T-junction cut 会使
A-L1 红，这三锁共同钉死闭包边界。

### 4.3 冲突谓词

首批 evaluator 覆盖下列五个通用拓扑/身份谓词；它们是启动集，不是穷尽清单：

| 主张 | witness 必含 | 认证条件 |
|---|---|---|
| `owner_multiplicity`（含 exterior duplicate） | 原子 span、全部 owner edge ids、方向 | 在 capability 域的所有解释下，该正长度原子仍有非法 owner 重数 |
| `missing_reverse_owner` | 单侧 edge/span、应有的反向槽位 | 在所有解释下仍不存在可覆盖该 span 的反向 owner |
| `exterior_interior_conflict` | exterior atom、两侧 owner facts | 在所有解释下该原子仍同时承担互斥的 exterior/interior 身份 |
| `ring_identity_conflict` | 重复 source vertices 或相交 edge ids、交点关系 | 能用固定端点证明非相邻重复、touch/cross/overlap 或回折 |
| `segment_merge_conflict` | segment ids、归并前后两对端点 | 能用固定来源和代表映射证明零长或 duplicate-after-merge |

谓词用 exact dyadic 区间算术和来源依赖闭包判断：

- 能从 capability 之外的固定事实构造完整证书：`CERTIFIED_CONFLICT`；
- 观察到症状，但任一必要 witness 事实依赖 capability：`CONTINGENT`；
- 固定事实反证该症状：丢弃；
- evaluator 已注册但 witness 不足以完成证明：合成 capability，NA；
- evaluator 缺失：合成 `missing_predicate_evaluator` capability，NA，并强制走 §4.3.2 计数。

证明器必须搜索**最小固定核心 witness**，不能因为同一大诊断还列有一个 contingent owner 就污染全部固定 owner。例如 owner multiplicity 只需找到两个固定、非法并存的 owner 和一个固定正长度子原子；第三个 capability-dependent owner 可以留在 audit，但不进入核心证书。反过来，absence 类证明必须证明所有 capability edge 都因固定的支撑、方向或区间事实不可能补上缺侧；做不到就只能 contingent。

这正好区分两个关键活体：

- R4 合法 advisory 派生 duplicate：duplicate 小区间的两个 cut 都来自 advisory 相邻边的非固定端点，无法从固定事实证明一个正长度 duplicate 原子，故为 `CONTINGENT`。
- 两个完整 footprint owner 的真实 duplicate + 独立 cell C advisory：duplicate witness 只引用 A/B 的固定来源边，与 C 的 envelope 无交，故在所有解释下恒真，为 `CERTIFIED_CONFLICT`。

同理，B/C 的 1e-9 真缝 witness 与 A 的 advisory 来源无关，仍可认证为冲突。

#### 4.3.1 predicate registry 的有意取舍

registry 的 key 是 `(predicate, predicate_schema_version)`，value 是一个读取 typed witness、
fact graph 与 capability closure 的 evaluator。detector 的 `reason` 可以新增而不改 registry；
只要它能把证据归约到已有通用谓词，就复用对应 evaluator。只有证据的逻辑形态真的新增时才增加
predicate/evaluator。

必须正面承认：**一个真正全新的 predicate 若没有 evaluator，在该版本中不能判红。**
这在逻辑效果上是 certifier 的已知不完备性。本文有意保留“无 evaluator ⇒ NA”，理由是：

1. 自动把未知主张判红，会重新让 detector 名字/category 取得定罪权，违反 R-4；
2. 一个所谓 catch-all evaluator 若不能给出机械 witness，只是把 reason 白名单改名；
3. 在“可能漏放未知真破裂”和“可能冤判生产端合法形态”之间，本评分信任边界选择前者，
   但必须用下节计数让漏口成为可运营发现的债务，而不是静默常态。

因此“有 evaluator”本身不等于红：evaluator 还必须从 witness 得出固定核心并返回
`CERTIFIED_CONFLICT`。反过来，predicate 集合长期不全也不允许凭“fail-safe”被掩盖。

#### 4.3.2 无 evaluator 的运行时可见性

每次 typed c2 v3 请求在进入分析前创建请求级 accumulator。计数单位是 canonical 去重后的
`(diagnostic_id, predicate, predicate_schema_version)`；同一 detector 重复发同一 id
不得重复计数，两个不同 diagnostic id 即使 predicate 相同仍各计一次。diagnostic id 冲突但
witness 不同则是内部合同错误，不能靠去重吞掉。

dispatch 找不到 evaluator 时必须原子地完成三件事：

1. 把原诊断标成 `UNPROVEN`，合成
   `diagnostic_evidence_incomplete / missing_predicate_evaluator` capability，最终按 NA 候选处理；
2. accumulator 的 `missing_predicate_evaluator_count += 1`，并更新按
   `(predicate, predicate_schema_version)` 排序的 histogram；
3. 通过与 `near_orthogonal_advisory_*` 相同的结构化 runtime artifact/logger 通道发逐项事件：

   ```text
   event = "judge_certifier_missing_evaluator"
   request_key
   side, floor_id, diagnostic_id
   predicate, predicate_schema_version
   requested_code, resolution = "diagnostic_evidence_incomplete"
   ```

`request_key` 由本次 GT content hash、product output hash 和
`"b4b_segment_score_v3_ic1"` 组成 canonical hash；不要求上游新增字段。
per-floor detector 只把 missing-evaluator record 放入 `AnalysisReport`，不自行发 summary；
typed 请求入口合并后统一计数。兼容 wrapper 若在 typed service 外被直接调用，则以
`("compat", side, canonical SourceGeometryDocument audit hash, helper version)` 生成本地
request key，并走同一 emitter，不能成为无计数旁路。

请求级仲裁放在 `try/finally` 内；无论最终是 scored、NA、还是被另一条认证冲突判红，`finally`
都恰好发一条：

```text
event = "judge_certifier_missing_evaluator_summary"
request_key
missing_predicate_evaluator_count
predicate_histogram              # tuple[(predicate, version, count), ...]，canonical sorted
diagnostic_ids                   # tuple[str, ...]，canonical sorted
final_outcome = "scored" | "na" | "red"
```

count 为 0 也发 summary，方便真实 run 区分“零命中”与“根本没接 telemetry”。该计数是运行时
可见性，不改变红/NA 优先级，也不写回 GT、产品或签字答案。没有 witness 是另一种
`missing_witness` 证据缺失；它同样 NA，但不得冒充本计数。无法持久化 summary 的 run
在运行审计中标为 telemetry incomplete，不能被用于声称 predicate 覆盖完整。

### 4.4 请求级裁决

证明完成后，在整次 v3 score request 上执行：

```python
certified = all_reports.certified_conflicts
uncertain = all_reports.contingent_or_capability

if certified:
    raise scoring_contract_error(select_root(certified))
if uncertain:
    raise unsupported(select_capability(uncertain))
return all_segments
```

规范要求：

- 任一楼层认证冲突高于任一楼层 capability；调换楼层顺序不得改变出口。
- GT/product 分析若都在本次请求内，先收报告后裁决；不能由“先提取 GT 还是先提取产品”定案。
- `select_root` 只影响展示哪条红，不影响红/NA。它先沿 `caused_by` 图去掉派生节点，再按
  `(side, floor_id, locus canonical bytes, diagnostic_id)` 稳定排序。
- 单一既有冲突的 code/gate/reason 保持逐字兼容；多冲突时不再靠 reason 排位推断根因。
- capability 日志在最终判红时仍要保留，不能因红色出口丢掉运行时计数。
- `finally` 中的 missing-evaluator summary 在选定最终出口后发出；红色 raise、NA raise 和正常
  return 三条控制流都必须经过同一 emitter。

### 4.5 A 的边界行为

| 并存形态 | 裁决 |
|---|---|
| 只有独立认证冲突 | 红 |
| 只有 capability | NA |
| 只有 contingent identity 症状 | NA |
| 认证冲突 + unrelated capability | 红，同时保留 capability audit/log |
| 认证冲突 + 与它相交但不影响其恒真性的 capability | 红 |
| 某 identity 症状的真伪依赖 capability 解释 | NA |
| 新诊断有 reason、无 witness | NA，并显式记 `diagnostic_evidence_incomplete / missing_witness` |
| witness 完整但无 `(predicate, version)` evaluator | 有意 NA；逐项事件 + 请求汇总计数必须进运行时产物 |
| 不同楼层分别有红和 NA | 整次请求红 |

这条边界允许保守 NA，但不允许在证据不足时制造假红，也不允许无关 NA 洗掉已经证明的评分冲突。

### 4.6 A 的机械验收锁与指定 neuter

| ID | 会红的锁 / 预期 | 现码状态 | 指定 neuter（实施后必须使该锁红） |
|---|---|---|---|
| A-L1 | R4 双 cell `5e-10` vs `4e-10` 活体：生产五项绿，最终必须 capability NA；audit 中 derivative duplicate 为 CONTINGENT，逐弧列出 small-axis seed → 相邻 edge endpoint → T-junction cut → owner atom 及 capability id | 结果已 NA，但无证书/audit，新增断言红 | 让 advisory envelope 不传播到相邻边端/T-junction cut，或令 certifier 忽略依赖 |
| A-L2 | 1e-9 真缝 + unpaired advisory：生产五项绿，仍精确为 product identity 红；audit 证明真缝 fixed support/span 与 advisory admissible enclosure 全域不相交，witness 不依赖 advisory | 结果已红，但来源证书断言红 | 把同 floor 任一 capability 污染到所有 witness，或忽略 exact enclosure 的全域不相交证明 |
| A-L3 | brief 的两个满幅 cell duplicate + unrelated advisory：生产五项绿，必须 `exterior_duplicate_owner` 红；fixed-core audit 只列 A/B 固定 edge/span，不含 C advisory facts | 红：现码会 NA | 同 A-L2；这是该“局部而非整层污染”门的第二个正式活体，共用 neuter 必须如实披露 |
| A-L4 | A-L1 和 A-L3 分别交换 cell 输入顺序，结果及选中 diagnostic canonical bytes 不变 | 红：现结构无 canonical evidence | 恢复“第一个 diagnostics 元素获胜” |
| A-L5 | floor F1 只有 advisory，F2 有独立 duplicate；两个 floor 顺序各跑一次，都必须红 | 红：当前 F1 可先抛 NA | 在 floor loop 内恢复立即 raise |
| A-L6 | 构造一个新 reason 的 identity-like claim，但不给 witness；必须 NA `diagnostic_evidence_incomplete / missing_witness`，不得凭 category 红，且不得误增 missing-evaluator count | 红：当前数据模型无法表达 | 对 `requested_code=score_*_identity_invalid` 的无证 claim 默认认证 |
| A-L7 | 同时存在 located conflict 和其派生 dangling conflict；调换 detector 输出顺序，红/码不变，root 由 `caused_by` 图选 | 红：当前按 reason/list 顺序 | 删除 caused-by root 消解，改回列表首项 |
| A-L8 | 最终红时 unpaired advisory 结构化日志仍包含 floor、端点 hex、capability id | 部分红：当前无 capability id | 仲裁红出口前清空/短路 capability audit |
| A-L9 | 给一个完整 typed witness 和新 `(predicate, "1")` 但不注册 evaluator：单独运行必须 NA，逐项事件一次、summary 的 `missing_predicate_evaluator_count=1` 且 histogram 精确；再加 unrelated certified duplicate 后最终必须红而 count 仍为 1；临时注册 evaluator 后 count 必须为 0 | 红：当前无 registry/计数产物 | 在 missing-evaluator 分支只返回 NA 而跳过 accumulator/emitter，或在红色出口前清空 accumulator |

A-L2/A-L3 是同一局部污染守卫的两个方向：一个防过宽导致假 NA，一个钉 brief 的第三张脸。施工日志不得把它们虚报成两个独立 guard。

### 4.7 A 的实施代价与风险

- 预计：finite fact graph/envelope/certifier 约 450–700 行；现有 pairing detector 改造约
  180–280 行；请求级 report/telemetry 接线约 100–180 行；新增约 12–18 条锁。
- 工作量：约 5–8 个专注工程日。
- 主要风险：
  - envelope 过窄会让派生症状假红；
  - envelope 过宽会让独立冲突假 NA；
  - evaluator registry 长期不全会把新型真破裂系统性降级为 NA；
  - 只改 `_pair_interior_edges` 而遗漏跨楼层/跨文档的第一次抛错；
  - 多诊断 root 展示变化误伤既有精确 reason 锁。
- 控制：
  - A-L1 与 A-L2/A-L3 构成窄/宽双向门；
  - A-L9 把 registry 不完备变成每个真实请求可累计、可分 predicate 查询的运行时债务；
  - A-L5 钉请求级而非 helper 级收集；
  - 单诊断保持旧 reason，多诊断才走证据图 root。

---

## 5. 缺口 B · 结构性守恒与精确长度账本

### 5.1 判据凭什么立足

守恒判断改为两个事实：

1. **集合事实**：区间原子上有几个不同 target/observation owner；
2. **算术事实**：所有有限 binary64 都是精确 dyadic rational，可以作为 exact-rational 参数运算的无损输入。

生产判据中不新增任何 conservation tolerance。现有的匹配位置/方向容差仍用于“是否候选”，但一旦候选注册完成，守恒只看明确的区间集合和 exact-rational 账本。

### 5.2 两个一维参数域

每个 segment 都有自己的弧长参数域：

```text
target domain       T = [0, target.length]
observation domain  O = [0, observation.length]
```

匹配器不再只返回 `overlap: float`，而返回一对带来源的区间：

```python
CoverageClaim(
    target_key,
    observation_key,
    target_interval=(t_lo, t_hi),
    observation_interval=(o_lo, o_hi),
    endpoint_sources=(...),
)
```

- 两个区间必须由**同一对几何 cut token**产生，claim 内保存从支撑线参数到 observation 弧长参数的单调仿射映射证书。
- claim builder 校验两域端点都在各自 domain 内、顺序一致、clip 来源一致；消费者不再接受一个脱离区间来源的裸 `covered: float`。
- target interval 用 target 自身弧长参数。
- observation interval 是同一几何覆盖沿 observation 自身直线的仿射反投影，因此容量单位始终是产品墙自身米数。
- 参数值不先用 binary64 dot/divide 算完再转精确数。对 segment 方向
  `d=(dx,dy)`，先把输入 binary64 分量无损转成 rational，再计算
  `lambda(p)=((p-p1)·d)/(d·d)`，最后以 `lambda * L` 映到 `[0,L]`。这样两个不同 cut 不会仅因一次中间投影舍入被焊成同一参数。
- 与 segment 端点相交产生的 cut 使用 `DOMAIN_START/DOMAIN_END` sentinel，值精确取
  `0` 或该 domain 的 length，避免端点经过投影再反投影产生假缝。
- 共享的 canonical target 顶点总是经同一 observation 参数函数求值一次并复用 cut id；相邻 target 因而共享同一个 bit pattern。
- 通用接口只要求“直线 segment 可给出单调的一维参数”；当前 H/V 支撑线不是账本的硬编码前提。

因此，一个孤立 claim 不能凭空声明“4 m observation 收了 4.0000000005 m”：若多出的量来自第二个 target，原子 owner multiplicity 会抓住；若来自同一 claim 的端点/clip 不一致，mapping certificate 会抓住。守恒入口不再接受无法追到几何 cut 的幻想总量。

### 5.3 exact rational measure

内部使用：

```python
Dyadic.from_float(value)  # 基于 value.as_integer_ratio()
```

作为输入叶子；仿射参数中的除法由 exact rational 承接。规范要求：

- 坐标和 rounded `hypot` 长度先无损转 dyadic；
- dot、乘、除、cut 排序、原子相减和聚合全在 exact rational 中完成；
- 只在生成公开 `eligible_units: float` 时做一次 correctly-rounded binary64 转换；
- audit 保存 exact numerator/denominator 或等价 canonical bytes。

标准库 `Fraction.from_float` 可作为首版正确性实现；若性能实测需要，可换专用 exact-rational 表示，但输出 canonical bytes 必须相同。任何性能替换都不得在 ledger 内重新引入中间 binary64 投影。

这里有一项有意保留的精度边界：exact ledger 在公开
`eligible_units` 处 correctly-round 成 binary64；下游用来判
`complete/within_tolerance/miss` 的 axis/position/extent 残差也仍是 binary64，并按既有
float `claim_complete_epsilon_m` 比较。恰落政策边界的输入可能因 1 ulp 改变 criterion 分类。
本轮不把评分政策改成 rational，也不声称 exact ledger 消除了这项历史精度债；它只保证该
float 决策不能回流到 conservation、owner multiplicity 或 extra 非负性。audit 同时保留
`eligible_units_exact` 与公开 float hex，供 §8.3 的逐行 diff 识别这种边界。

### 5.4 target 原子账本

对一条 target：

1. cuts = domain 两端 + 所有 target claim 端点；
2. 按 exact rational 值排序、相同值合一；
3. 相邻 cuts 形成正长度原子；
4. 对每个原子计算覆盖它的 observation id 集：
   - 0 个：`miss`；
   - 1 个：该 observation 的 matched 状态；
   - >1 个：`duplicate`。

每个原子只进入一个状态，因此 `matched + miss + duplicate = target domain`
由分区结构证明，不再靠一个浮点差值和窗口事后猜。

防御性 checker 验证：

- 首尾等于 domain sentinel；
- 原子首尾连续、无洞、无重叠；
- 每个正长度原子恰有一个状态；
- exact-rational 状态总和等于 exact domain 长度。

任一内部不变量失败仍用 `score_denominator_nonconserving`，context 输出 exact ledger。

### 5.5 observation 原子账本

对一条 observation：

1. cuts = observation domain 两端 + 所有 observation claim 端点；
2. 原子化；
3. 对每个原子计算向它收费的不同 target id 集：
   - 0 个：`extra`；
   - 1 个：合法 covered；
   - >1 个：**重复记功，立即 `score_denominator_nonconserving`**。

因此：

- `[0,4]` target 与 `[1,3]` target 同时向一条 4 m observation 收费时，
  observation 原子 `[1,3]` 的 target owner 数为 2，结构性拒绝。
- 三条严格相邻 target 只在 cut 上相接，所有正长度原子的 owner 数均为 1，合法。
- 只要输入 binary64 能表达一个正长度重叠，即使宽度只有 1 ulp，也会形成正 exact-rational 原子并拒绝。
- `extra` 是 owner 数为 0 的原子之和；从数据模型上非负。
- 不再计算 `extra = obs.length - covered`，也不再用 `if extra > epsilon` 决定是否掩盖负数。

`covered_exact + extra_exact == observation_domain_exact` 同样由分区结构成立。账本先无条件保留完整、非负的 `extra_exact`；公开计分行是否忽略一个很小但为正的 extra，继续由既有
`claim_complete_epsilon_m` 评分政策决定。该 epsilon 不参与守恒、不参与重复收费判定，也不能接触负数——因为账本结构根本不产生负 extra。

#### B 的双向证明

设一条 observation 域被全部 claim 端点切成原子 `A_k`，`m_k` 为原子上的不同 target owner 数。因所有 claim 已 clip 在 observation 域内：

```text
所有 target 的收费长度之和 = Σ_k m_k * |A_k|
合法并集 covered             = Σ_k [m_k >= 1] * |A_k|
observation domain           = covered + Σ_k [m_k = 0] * |A_k|
```

所以：

- 存在正长度原子 `m_k > 1`，收费和必严格大于合法并集，是真过计；
- 所有 `m_k <= 1`，收费和等于合法并集且不超过 domain，不可能有负 extra；
- 两段只共享端点时没有正长度原子 `m_k > 1`，不会假红。

这是有限区间集合上的等价关系，不依赖建筑尺寸、原子数量或误差窗。exact-rational 运算保证实现检查的正长度和上述代数是同一个对象，而不是两个不同舍入路径的近似量。

### 5.6 与计分语义的关系

- target 账本的原子长度继续供 `walls_complete` 和
  `no_duplicate_wall_strokes`。
- observation 账本的未覆盖弧长供 `no_extra_walls`。
- 一条 slightly tilted、但在既有匹配容差内的 observation，其容量按自身弧长参数计算；不能用 target 投影米数把产品墙收费超过自身。
- B-1 唯一支撑线注册不变；observation 账本只处理已经唯一注册的 claims。
- 两个平行答案支撑线的歧义仍在注册阶段 NA，不进入守恒账本。

### 5.7 B 的边界行为

| 情形 | 结果 |
|---|---|
| target spans 精确相邻 | 合法；共享 cut、无正长度重叠 |
| target spans 有任一可表示的正长度重叠，向同一 observation 收费 | 响亮拒绝 |
| target spans 有 gap | observation 对 gap 为 extra；相应 target 账本按各自覆盖计 |
| 同一 target 被多 observation 覆盖 | target 原子记 duplicate criterion，不与 observation 重复记功混淆 |
| observation 完整覆盖若干相邻 target | extra exact 为 0 |
| observation 部分覆盖 | extra 为未覆盖原子并集 |
| 区间端点/状态无法形成完整分区 | `score_denominator_nonconserving` |

### 5.8 B 的机械验收锁与指定 neuter

| ID | 会红的锁 / 预期 | 现码状态 | 指定 neuter（实施后必须使该锁红） |
|---|---|---|---|
| B-L1 | 正式 match path：t1 `[0,4]`、t2 `[1,3]`、obs `[0,4]`，精确拒绝，audit 指出 `[1,3]` target owners `{t1,t2}` | 已绿 | 禁用 observation atom 的 `len(target_ids)>1` 守卫 |
| B-L2 | 同一路径把重叠缩到 `5e-10`，仍拒绝；不得依赖某个固定窗 | 现码会因 strict compare 拒，但无结构证书 | 同 B-L1；这是小额方向，共用 guard 如实披露 |
| B-L3 | 把重叠缩到 `nextafter(4,-inf)..4` 的最小相邻 binary64 正长度原子，仍拒绝 | 红：现码中 `4.0 + 0x1p-51` 会按 round-to-even 舍回 `4.0`，strict compare 也看不见 | 同 B-L1 |
| B-L4 | r3 三段正式 GT/correction 活体：生产五项绿，match 不拒绝；无 extra；observation ledger exact covered 等于 exact domain | 红：当前 1 ulp 假红 | 把 atom ledger 替换为旧式顺序 `covered += b-a` 后做 strict `covered > length` |
| B-L5 | B-L4 的三个 target 顺序全排列或至少正序/逆序，rows canonical bytes 与 ledger exact bytes 不变 | 红：当前顺序和可变 | 将 exact accumulator 换成普通顺序 `sum` 并按输入顺序发 rows |
| B-L6 | 半覆盖 target：target ledger 的 matched/miss/duplicate exact 和等于 domain；observation extra 为 complement | 新 exact audit 断言红 | 删除 domain 末端 sentinel 或跳过一个 atom 状态 |
| B-L7 | 一条 observation 覆盖两个相邻 target，断言 `extra_exact == 0` 且所有 extra 行为空 | 当前可能受顺序漂移 | 恢复 `extra = obs.length - covered; if extra > epsilon` |
| B-L8 | slightly tilted observation 的全域/部分域夹具：所有 observation atom 均位于 `[0,L]`，covered+extra exact 等于自身弧长 | 红：当前没有 observation-native 区间 | 用 target 投影长度直接充当 observation domain |
| B-L9 | checker 收到人为破坏的非连续 atom ledger，必须 denominator error 并输出 exact endpoints | 红：当前无 ledger checker | 让 checker 恒 return |
| B-L10 | 构造一个两域 clip 不一致的 CoverageClaim（target 端多 `5e-10`、observation 端仍止于 4 m），claim builder 必须在进入账本前拒绝 | 红：当前 scalar helper 可直接接这种总量 | 跳过 cut-token/mapping certificate 校验 |

B-L1/2/3 是同一个 multiplicity guard 的大额、小额和最小可表示正重叠三张脸，只算一个结构守卫；B-L4 是独立的合法舍入方向。

### 5.9 B 的实施代价与风险

- 预计：通用 interval/measure ledger 约 220–360 行；匹配器返回区间 claims 的改造约
  140–240 行；新增/改写约 11–15 条锁。
- 工作量：约 3–5 个专注工程日。
- 主要风险：
  - observation 弧长反投影改变少量 v3 extra 的最后 1 ulp；
  - `eligible_units` 公开 float 在 `claim_complete_epsilon_m` 恰好边界仍有 1-ulp criterion
    抖动；这是记录在案的既有评分精度债，不是 conservation 漏口；
  - exact accumulator 的大整数性能；
  - 下游再次用普通顺序 sum 破坏 canonical 总量；
  - 把 observation 重复收费与 target duplicate criterion 混为一类。
- 控制：
  - exact measure 在行聚合前只 round 一次；
  - 对真实 sm24 v3 按 §8.3 记录改造前后逐行差异；任何 float 变化须列 hex/exact 来源，
    status/verdict 变化不得仅以“已知 1 ulp”带过；
  - 基准测试以实际最大 floor edge/cut 数测量，不预设“只会有几个盒子”；
  - 两本账分别以 target ids 和 observation ids 做 owner 集。

---

## 6. 三条机制的组合裁决

### 6.1 总状态机

```text
来源/版本/护带/alias/静态拓扑合同诊断
                         \
边配对冲突主张 ----------> capability-aware certifier
                         /
W5 capability envelopes
        |
        v
请求级仲裁
  | CERTIFIED_CONFLICT 存在 -> 红
  | 否则不确定/量不了存在  -> NA
  | 否则
        v
唯一支撑线注册
  | 0 candidate -> extra
  | 1 candidate -> interval claims
  | >1 candidate -> 既有 unsupported
        v
exact target/observation ledgers
  | observation atom 多 target owner -> denominator 红
  | ledger 结构破坏 -> denominator 红
  | 否则 -> rows
```

### 6.2 失败优先级的边界

- A/C 的认证评分身份冲突可以与 capability 比较，因为二者都在计量前分析阶段。
- B 只在 A/C 成功后运行；NA 请求没有“先算一部分分数再决定”的路径。
- B 的 denominator error 是判卷器自身账本完整性失败，不是上游几何非法。
- 任何内部异常不得偷换成 pass；未知证明/未知版本在其所属边界 fail-closed。

### 6.3 为什么不会在下一个位置再破一次

- 新 pairing reason 没有证书时没有红色资格；严重性不随字符串集合增长。
- 无 evaluator 的新谓词有意 NA，但逐诊断和请求汇总计数强制进入运行时产物；证明能力缺口不会静默积累。
- capability 的影响由有限 source fact DAG 和明确 T-junction cut 传播求闭包，且请求级统一仲裁；
  换 bucket、floor 或输入顺序不改变结论。
- 守恒由区间 owner 重数和精确分区成立，不依赖累加顺序或另选一个数值窗口。
- 数值聚类只提出 alias 候选；证书 API 收不到待 alias 值或阈值，只有 owner/方向、
  `world_along_interval` 槽和 ring 序号能建立意图原子。
- 新 geometry profile 只需提供来源 adapter、alias relation 和 capability envelope；仲裁器、账本和 exact measure 不需要改成“只认正交盒子”的第二套。

---

## 7. 施工拆分与不可半交付项

### Slice 0 · 先落会红的锁

先提交本稿三张核心活体锁，确认现码：

- A-L3 红（duplicate + unrelated advisory 被洗成 NA）；
- A-L9 红（当前没有 missing-evaluator 请求级计数产物）；
- B-L4 红（三相邻 span 的 1-ulp 假红）；
- C-L1/C-L7/C-L11 红（来源丢失、完整拓扑、版本门）。

同时把每个指定 neuter 写成施工日志中的可执行 patch，不接受“代码看起来会覆盖”。

### Slice 1 · 来源图与身份合同（C）

1. 建 `SourceGeometryDocument` 和三类 adapter。
2. 改 `_cluster_axis` / `_build_floor_identity` 为 occurrence API。
3. 按 C-3a 至 C-3d 落 contract version、same-source 和结构 alias certificates；先跑
   C-L4/C-L5 的距离独立双向门。
4. 落通用 post-merge topology/owner claims。
5. 保住三历史绿、答案纯函数和 sm21。

**不可半交付：**只传 source key 但聚类后又回到 `raw float -> rep`；或
`paired_edge_endpoint/boundary_chain_endpoint` 读取待 alias 差值、最近邻或 merge 阈值，
均视为未实施。

### Slice 2 · 证明式仲裁（A）

1. 把 pairing 诊断改成 source witness。
2. 按 §4.2 的 finite fact DAG/worklist 建 W5 unpaired advisory envelope，含相邻 edge
   endpoint 与 T-junction cut 传播。
3. 建首批五个通用冲突 predicate evaluator。
4. 所有 floor 先报告后请求级仲裁。
5. 保留结构化 advisory 日志，并落
   `missing_predicate_evaluator_count` 的逐项/summary 运行时产物。

**不可半交付：**仅扩大现有诊断 context、但仍由 detector category/reason 直接定红；
或未知 evaluator 虽 NA 却不计数/红色出口丢计数，均视为未实施。

### Slice 3 · exact interval ledgers（B）

1. `_candidate`/matching 产出双域 CoverageClaim。
2. target ledger 接管 matched/miss/duplicate。
3. observation ledger 接管 covered/extra 和重复收费。
4. 删除旧 scalar conservation 分支与 `_SUBINTERVAL_SUM_TOL` 在本通路的职责。
5. exact audit 接入错误 context 和 canonical row aggregation。

**不可半交付：**以下任一项成立都视为未实施：

- 只把普通 `sum` 换成 `math.fsum`，仍以两个独立浮点总量比较定案；
- 对每条 target 独立重算同一个 observation 上的共享顶点，不复用 canonical cut id；
- target/observation 两域不是由同一对 cut token 和 mapping certificate 生成。

### Slice 4 · 版本、缓存与全链回归

- 把 v3 segment scorer helper 精确 bump 为
  `"b4b_segment_score_v3_ic1"`，并验证 envelope version/helper release map；
- 失效旧 v3 派生 sidecar/cache，不动 GT；
- 跑全部 v3 segment 计分锁、全仓、sm21 三件套、sm24 受保护树 hash；
- 对真实 sm24 typed c2 v3 按 §8.3 产出改造前/后 canonical JSONL 并逐行 diff；
- 每个 neuter 仅在临时副本执行并还原。

### 7.1 总成本估计

| 项 | 专注工程日 | 主要影响文件 |
|---|---:|---|
| C 来源身份与拓扑合同 | 6–9 | 新 judge-only 模块、`segment_score.py`、score identity |
| A 证书与请求级仲裁 | 5–8 | 新 evidence/certifier 模块、`segment_score.py`、`score_service.py` |
| B exact interval ledgers | 3–5 | 新 measure/ledger 模块、`segment_score.py` |
| 集成、neuter、全仓与性能 | 3–4 | tests、执行日志 |
| **合计** | **17–26** | 不含审阅返工 |

建议按上述 slice 独立提交、最终一次性启用新 v3 scorer identity；不得把未完成的 source 传递或 capability envelope 单独作为可发布状态。

---

## 8. 对既有测试与地基的影响

### 8.1 必须保留原意的锁

- 三个历史坐标表示反例仍绿，但应升级为带来源和真实 topology 的夹具。
- 1e-9 真 gap 双侧仍红，单一形态的既有 code/gate/reason 不变。
- R4 advisory-only 仍 NA；exact reverse advisory 仍能提取计分。
- 答案原子/分母纯函数字节锁不变。
- B-1 多支撑线歧义不变。
- 大额 observation 重复收费仍红。
- sm21 分数、像素 hash、分派路径全部不变。

### 8.2 必须替换的旧判据锁

- 直接断言 `covered=length+微量` 必红的 helper 锁不再代表合同；应由
  observation 原子 owner multiplicity 锁替代。
- `_assert_target_conservation(..., tol)` 的 helper 锁改为 ledger 分区破坏锁。
- 只给 `_PairDiagnostic(category, reason)` 就期待仲裁结果的 helper 锁，改为带 witness/envelope 的证明锁。
- 裸 float `_cluster_axis` 锁改为 occurrence API；历史语义不删。

### 8.3 影响面估计

这是**全部 typed c2 v3 segment 计分路径**的改造，不得按“少量 score service 锁”估算。必跑影响面至少包括：

- `tests/test_judge_identity_metric.py` 的 identity、matching、denominator、criterion 全部锁；
- `tests/test_c2_segment_tjunction.py` 的 GT/product 提取、T-junction、advisory 和正式计分锁；
- `tests/test_c2_b4b_phase_b.py` 中所有消费 `SegmentScore/eligible_units` 的锁；
- `tests/test_c2_b4b_phase_d.py`、`tests/test_c2_b4b_contract.py` 的 typed scorer
  identity、sidecar hash/cache 和正式服务接线锁；
- 新增独立 provenance、alias、capability closure、predicate telemetry、exact measure ledger 锁。

施工前后对**真实 sm24 typed c2 v3** 的逐行 diff 是必跑项，步骤定为：

1. 改造前通过真实 `score_typed_attempt`/accepted product 正门生成 baseline，不用手造
   `PlanSegment` 代替。按稳定 key
   `(floor_id, target_id, observation_id, exterior, status)` 排序，写 canonical JSONL；
   每行保存公开字段、`eligible_units` 十进制与 binary64 hex、observation-to-target map。
2. 改造后用同一 GT/product/config 重跑；另存每行的 exact numerator/denominator、
   public float hex、cut ids 和 mapping certificate id。输入 GT/product/config hash 必须逐位相同，
   唯一预期 identity 输入变化是 helper
   `"b4b_segment_score_v3_ic1"`。
3. 对 internal segment rows、公开 `SegmentScoreRowV8`、三项 wall criteria 和 sidecar
   identity 分别逐行 diff；把 baseline/new 文件 hash 与完整 diff 附进施工日志。
4. helper identity 与由它派生的 sidecar/content hash 变化是预期。`eligible_units` 或 extra
   最后 1 ulp 的变化只有在 diff 同行给出 exact ledger/mapping 解释时可接受。
   target/observation 配对、row status、extra/duplicate/miss 类别、criterion verdict
   或 denominator 语义变化一律阻断，不得以 MINOR-4 的“已知 1 ulp”概括放行；若确需这种变化，
   先回到设计审新增裁定。

预计不应变化：

- correction 生产五项 validator 的判定；
- GT schema/wire；
- sm21 legacy 测试；
- renderer；
- opening/host claim 逻辑（除非其测试共用 scorer identity fixture，届时只更新新 v3 派生身份预期）。

---

## 9. 硬约束逐项证明

| 硬约束 | 本稿如何满足 | 机械门 |
|---|---|---|
| gt 铁律 | 来源 key 全在 judge 内存派生；不增 GT 字段、不规范化、不回写 | sm24 受保护树施工前后 SHA-256 manifest 相同；共享模块零 GT import |
| 建筑复杂度可扩展 | ring/edge/source 模型支持多环；相交谓词一般化；B 用任意直线一维参数；A 的 capability 为插件式 envelope | C-L13 + 非方形/凹多边形性质锁；性能基准按实际 edge/cut 数 |
| sm21 零变化 | legacy 分派不实例化新 adapter/ledger，v3 helper identity 单独 bump | C-L15 + 既有分数/像素/路径锁 |
| 不宣判上游非法 | 红只写 `authority=scoring_identity` 或 denominator integrity；不调用/替代生产合法性裁决；证据不足为 NA | 人可读消息精确锁 + A-L1 |
| 每条出口机械验证 | §3.6、§4.6、§5.8 均给当前会红形态和指定 neuter | 施工日志逐 neuter 实测 |
| 不先定数字后论证 | B 不增加守恒数字；用正长度原子和 exact rational。C 沿用已签字三阈值 | 搜索/AST 锁：新 ledger/certifier 不出现 conservation epsilon/tol 参数 |

额外保护：

- GT/产品池分离写在 `SourceGeometryDocument.side` 和 builder API 中，不能传混合 side。
- capability audit 即使最终红也保留，延续 W5 的真实运行计数。
- 新 scorer identity 只影响新 v3 派生件；不触碰签字答案和 legacy identity。

---

## 10. Definition of Done

本文经主控补稿复核并转为施工基线后，施工只有同时满足以下条件才可报完成：

1. A-L1 至 A-L9、B-L1 至 B-L10、C-L1 至 C-L16 全部按表执行；共用 guard 如实归并计数。
2. 三张核心活体分别得到：
   - advisory 派生 duplicate：NA；
   - genuine duplicate + unrelated advisory：红；
   - 三相邻 span：合法计分。
3. A-L1 audit 能从 derivative duplicate/T-junction cut 逐弧回放到 small-axis seed；A-L3
   的 fixed core 不含 unrelated advisory fact，且得到 `CERTIFIED_CONFLICT`。
4. missing evaluator 单独出现时 NA、与 unrelated 红并存时整请求红；两条路径都发
   `missing_predicate_evaluator_count=1` summary，注册 evaluator 后为 0。
5. 三历史 alias 正式夹具仍绿；证书对待 alias 差值的远近变形不变；无结构关系 sub-merge 必红。
6. `_cluster_axis` 的生产调用点全部传 occurrence，不存在先展平 float 再“补来源”的旁路；
   alias certifier API/实现不能读取待 alias 值、gap 或三个 identity 阈值。
7. 最小可表示正重叠与 `5e-10` 重叠均被 observation multiplicity 结构门拒绝。
8. `extra` 只来自 observation complement atoms；生产路径中不存在负 extra 的生成和过滤分支。
9. 相邻 target 对同一 observation 的共享顶点只求值一次并复用 canonical cut id；不存在
   per-target 独立反投影旁路。
10. 非相邻重复、自触/自交、同 owner 反向配对、boundary/reading collapse 与
    duplicate-after-merge 均有完整 source/hex/diameter context。
11. `score_identity_contract_mismatch` 至少有版本、same-source spread、unproven
    alias/source collision 三类真实 raise 路径。
12. helper identity 精确为 `"b4b_segment_score_v3_ic1"`，identity contract `"1"`
    与其交叉验证；旧 typed c2 v3 sidecar/cache miss，GT hash 不变。
13. 任意调换 bucket、diagnostic、cell、floor 输入顺序，出口与 canonical audit 不变。
14. §8.3 点名的全部 v3 segment 锁和真实 sm24 逐行 diff 完成；无未解释 row/status/verdict
    变化。sm24 受保护答案树一个字节不变，答案原子与分母纯函数锁仍绿。
15. sm21 三件套零变化；全仓零新增非预期 red。新增 exact/topology 结构在真实最大 fixture
    上给出时间和内存实测，不得以正交盒子数量估算代替。
16. 每个指定 neuter 在临时副本中至少使点名锁变红，副本还原后工作树干净。

---

## 11. 结论

这轮不再给三个症状各补一个例外：

- A 把“谁有资格判红”改成可验证的全称证明；
- B 把“有没有多收钱”改成区间 owner 重数；
- C 把“这两个数为什么能焊”改成来源身份与拓扑 alias 证书。

三者共同把判卷器的立足点从隐含假设变成可重放证据；未知证明能力则以有意 NA +
强制运行时计数公开其代价。本文已经过 GLM 对抗审和主控方向终审，待主控完成本补稿的窄复核后，
可直接按 §7 拆施工，不需要施工方再自行补 CapabilityEnvelope、alias 或 predicate 完整性边界。
