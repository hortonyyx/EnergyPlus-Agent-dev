# 设计稿 · 判卷器「诊断仲裁 + 守恒判据 + 来源身份」

- 日期：2026-07-28
- 出案：sol
- 状态：待 GLM 跨家族对抗审、主控（Opus 5）终审
- 权威 brief：`AI_agent/logs/reviews/request/2026-07-28_judge_arbitration_and_provenance_brief.md`
- 本轮角色纪律：本文作者不参与本稿审阅

> 本文是施工基线候选，不是代码补丁。本轮不修改任何生产码、测试或 GT。

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
    source_edge_ids: tuple[tuple, ...]
    source_vertex_ids: tuple[tuple, ...]
    owner_ids: tuple[str, ...]
    locus: GeometricLocus

@dataclass(frozen=True)
class ContractWitness:
    predicate: str
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
`diagnostic_evidence_incomplete` capability，并以 NA 收口。新增一个 reason
而忘记补证明适配器，最坏结果是可见的能力降级，不会自动获得定罪权。

### 2.4 审计上下文最低字段

所有 A/C 新路径至少记录：

- `authority="scoring_identity"`；
- `contract_version`；
- `side`、`floor_id`；
- `diagnostic_id`、`proof_status`；
- source vertex/edge/owner keys；
- 发生区间两端的十进制值和 binary64 hex；
- 涉及归并时的全部原值 hex、`diameter`、`diameter_hex`；
- `depends_on_capability_ids`；
- capability envelope 的种类和端点 hex。

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
| GT footprint 顶点 | `(floor_id, "footprint", "exterior"/hole_id, vertex_index)` |
| GT zone 顶点 | `(floor_id, "zone", zone_id, ring_id, vertex_index)` |
| GT boundary 端点 | `(floor_id, "boundary", segment_id, "p1"/"p2")` |
| correction footprint 顶点 | `(floor_id, "footprint", "exterior", vertex_index)` |
| correction cell 显式 polygon 顶点 | `(floor_id, "cell", cell_id, "exterior", vertex_index)` |
| correction cell 的 x/y 矩形回退 | x 槽为 `(floor_id, "cell_rect_v1", cell_id, "x", 0/1)`；y 槽同理。两个派生 corner 若读取同一个 x/y wire 槽，必须复用同一 source key |
| reading observation 端点 | `(floor_id, "reading", observation_id, "p1"/"p2")` |

补充规则：

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
- contract version 必须进入 v3 scorer identity/cache preimage，施工时按既有协议 bump
  `SEGMENT_SCORER_HELPER_VERSION`。旧派生 sidecar 失效，GT 文件不失效。
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

若值不等但因 `< merge` 落入同一候选簇，必须建立 alias 证书。允许的 v1 证书仅来自已有结构：

- `same_source_reuse`：同一 source key 的多 use site；
- `explicit_ring_closure`：明确的首尾闭环；
- `paired_edge_endpoint`：两个不同 owner 的反向边或 T-junction 原子要求端点共址；
- `boundary_chain_endpoint`：同一已声明 boundary loop 的连续端点；
- `profile_axis_constraint`：当前 geometry profile 明确要求某源边沿某轴恒定。

每张证书必须列出两端 source key、支撑它的 edge/owner 关系和原始 hex。候选簇内每个不等值来源都必须通过证书图连到该簇的一个已证成员。

若只有数值接近而没有上述任一关系，发出
`score_identity_contract_mismatch / unproven_cross_source_alias`，不得静默归并。

`profile_axis_constraint` 是 profile adapter 的能力，不写死在通用身份求解器里。未来非正交 profile 可以不注册它，改注册自己的几何关系证明；数据模型无需重写。

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
| C-L4 | 三个历史合法表示漂移各改成带真实 topology/source 的正式夹具，保持可提取和可计分 | 现有裸 helper 绿，但来源合同锁不存在 | 对所有“不同来源且数值不等”无条件拒绝，三锁必须红 |
| C-L5 | 不相关的两个 sub-merge 不等值来源、没有 alias 关系，必须 `unproven_cross_source_alias` | 红：当前仅凭距离焊接 | 让 alias certifier 恒返回 true |
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

其中 C-L4 必须把现有三个“裸 float helper”历史锁升级成有 source/topology 的正式形态；不是删除历史反例。

### 3.7 C 的实施代价与风险

- 预计：新建一个 judge-only identity/provenance 模块约 350–550 行；三类 adapter 和
  `segment_score.py` 接线约 180–300 行；新增/改写约 18–26 条窄锁。
- 工作量：约 5–8 个专注工程日，属本轮最高成本项。
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

v1 首先覆盖 W5 的 unpaired near-orthogonal advisory。envelope 包含：

- advisory 源边；
- 它的两个源顶点；
- 该边的小分量坐标（near-vertical 时为端点 x，near-horizontal 时为端点 y）；
- ring 中与这两个顶点相邻、且 cut 端点由上述坐标决定的边端；
- 由这些非固定端点产生的 pairing cut/owner 关系。

传播按 source data-dependency 做，不按整层打标签，也不围绕端点另造一个数值半径。证明器只可使用 envelope 之外的固定事实，或使用 capability 自身明确保证的不变量；W5 当前只保证“生产端接受这一 near-axis 类别”，并不保证某个具体 straightening 坐标。

若一个冲突在去掉所有 capability-dependent 事实后，仍能由固定来源边和一个固定正长度子区间独立证明，它仍可认证为红。若做不到，就只能是 `CONTINGENT`。若未来 capability 类型不能给出完整依赖闭包，安全退化是把其来源连接分量标成未知，而不是猜一个较小影响域。

paired advisory 因 exact reverse 已可计量，不产生 capability envelope；paired/unpaired 的既有可计数日志均保留。

### 4.3 冲突谓词

首批 evaluator 至少覆盖现有三种 pairing 主张：

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
- evaluator 缺失或无法完成证明：合成 capability，NA。

证明器必须搜索**最小固定核心 witness**，不能因为同一大诊断还列有一个 contingent owner 就污染全部固定 owner。例如 owner multiplicity 只需找到两个固定、非法并存的 owner 和一个固定正长度子原子；第三个 capability-dependent owner 可以留在 audit，但不进入核心证书。反过来，absence 类证明必须证明所有 capability edge 都因固定的支撑、方向或区间事实不可能补上缺侧；做不到就只能 contingent。

这正好区分两个关键活体：

- R4 合法 advisory 派生 duplicate：duplicate 小区间的两个 cut 都来自 advisory 相邻边的非固定端点，无法从固定事实证明一个正长度 duplicate 原子，故为 `CONTINGENT`。
- 两个完整 footprint owner 的真实 duplicate + 独立 cell C advisory：duplicate witness 只引用 A/B 的固定来源边，与 C 的 envelope 无交，故在所有解释下恒真，为 `CERTIFIED_CONFLICT`。

同理，B/C 的 1e-9 真缝 witness 与 A 的 advisory 来源无关，仍可认证为冲突。

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

### 4.5 A 的边界行为

| 并存形态 | 裁决 |
|---|---|
| 只有独立认证冲突 | 红 |
| 只有 capability | NA |
| 只有 contingent identity 症状 | NA |
| 认证冲突 + unrelated capability | 红，同时保留 capability audit/log |
| 认证冲突 + 与它相交但不影响其恒真性的 capability | 红 |
| 某 identity 症状的真伪依赖 capability 解释 | NA |
| 新诊断有 reason、无 witness/evaluator | NA，并显式记 `diagnostic_evidence_incomplete` |
| 不同楼层分别有红和 NA | 整次请求红 |

这条边界允许保守 NA，但不允许在证据不足时制造假红，也不允许无关 NA 洗掉已经证明的评分冲突。

### 4.6 A 的机械验收锁与指定 neuter

| ID | 会红的锁 / 预期 | 现码状态 | 指定 neuter（实施后必须使该锁红） |
|---|---|---|---|
| A-L1 | R4 双 cell `5e-10` vs `4e-10` 活体：生产五项绿，最终必须 capability NA；audit 中 derivative duplicate 为 CONTINGENT 且列出 capability id | 结果已 NA，但无证书/audit，新增断言红 | 让 advisory envelope 不传播到相邻边端，或令 certifier 忽略依赖 |
| A-L2 | 1e-9 真缝 + unpaired advisory：生产五项绿，仍精确为 product identity 红；witness 不依赖 advisory | 结果已红，但来源证书断言红 | 把同 floor 任一 capability 污染到所有 witness |
| A-L3 | brief 的两个满幅 cell duplicate + unrelated advisory：生产五项绿，必须 `exterior_duplicate_owner` 红 | 红：现码会 NA | 同 A-L2；这是该“局部而非整层污染”门的第二个正式活体，共用 neuter 必须如实披露 |
| A-L4 | A-L1 和 A-L3 分别交换 cell 输入顺序，结果及选中 diagnostic canonical bytes 不变 | 红：现结构无 canonical evidence | 恢复“第一个 diagnostics 元素获胜” |
| A-L5 | floor F1 只有 advisory，F2 有独立 duplicate；两个 floor 顺序各跑一次，都必须红 | 红：当前 F1 可先抛 NA | 在 floor loop 内恢复立即 raise |
| A-L6 | 构造一个新 reason 的 identity-like claim，但不给 witness/evaluator；必须 NA `diagnostic_evidence_incomplete`，不得凭 category 红 | 红：当前数据模型无法表达 | 对 `requested_code=score_*_identity_invalid` 的无证 claim 默认认证 |
| A-L7 | 同时存在 located conflict 和其派生 dangling conflict；调换 detector 输出顺序，红/码不变，root 由 `caused_by` 图选 | 红：当前按 reason/list 顺序 | 删除 caused-by root 消解，改回列表首项 |
| A-L8 | 最终红时 unpaired advisory 结构化日志仍包含 floor、端点 hex、capability id | 部分红：当前无 capability id | 仲裁红出口前清空/短路 capability audit |

A-L2/A-L3 是同一局部污染守卫的两个方向：一个防过宽导致假 NA，一个钉 brief 的第三张脸。施工日志不得把它们虚报成两个独立 guard。

### 4.7 A 的实施代价与风险

- 预计：evidence graph/envelope/certifier 约 280–450 行；现有 pairing detector 改造约
  180–280 行；请求级 report 接线约 80–140 行；新增约 10–14 条锁。
- 工作量：约 4–6 个专注工程日。
- 主要风险：
  - envelope 过窄会让派生症状假红；
  - envelope 过宽会让独立冲突假 NA；
  - 只改 `_pair_interior_edges` 而遗漏跨楼层/跨文档的第一次抛错；
  - 多诊断 root 展示变化误伤既有精确 reason 锁。
- 控制：
  - A-L1 与 A-L2/A-L3 构成窄/宽双向门；
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
  - exact accumulator 的大整数性能；
  - 下游再次用普通顺序 sum 破坏 canonical 总量；
  - 把 observation 重复收费与 target duplicate criterion 混为一类。
- 控制：
  - exact measure 在行聚合前只 round 一次；
  - 对真实 sm24 v3 记录改造前后逐行差异，任何语义变化须能由新账本解释；
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
- capability 的影响是来源/区间局部的，且请求级统一仲裁；换 bucket、floor 或输入顺序不改变结论。
- 守恒由区间 owner 重数和精确分区成立，不依赖累加顺序或另选一个数值窗口。
- 数值聚类只提出 alias 候选；来源一致性和拓扑证书才建立意图原子。
- 新 geometry profile 只需提供来源 adapter、alias relation 和 capability envelope；仲裁器、账本和 exact measure 不需要改成“只认正交盒子”的第二套。

---

## 7. 施工拆分与不可半交付项

### Slice 0 · 先落会红的锁

先提交本稿三张核心活体锁，确认现码：

- A-L3 红（duplicate + unrelated advisory 被洗成 NA）；
- B-L4 红（三相邻 span 的 1-ulp 假红）；
- C-L1/C-L7/C-L11 红（来源丢失、完整拓扑、版本门）。

同时把每个指定 neuter 写成施工日志中的可执行 patch，不接受“代码看起来会覆盖”。

### Slice 1 · 来源图与身份合同（C）

1. 建 `SourceGeometryDocument` 和三类 adapter。
2. 改 `_cluster_axis` / `_build_floor_identity` 为 occurrence API。
3. 落 contract version、same-source、alias certificates。
4. 落通用 post-merge topology/owner claims。
5. 保住三历史绿、答案纯函数和 sm21。

**不可半交付：**只传 source key 但聚类后又回到 `raw float -> rep`，视为未实施。

### Slice 2 · 证明式仲裁（A）

1. 把 pairing 诊断改成 source witness。
2. 建 W5 unpaired advisory envelope。
3. 建三个现有冲突 predicate evaluator。
4. 所有 floor 先报告后请求级仲裁。
5. 保留结构化 advisory 日志。

**不可半交付：**仅扩大现有诊断 context、但仍由 detector category/reason 直接定红，视为未实施。

### Slice 3 · exact interval ledgers（B）

1. `_candidate`/matching 产出双域 CoverageClaim。
2. target ledger 接管 matched/miss/duplicate。
3. observation ledger 接管 covered/extra 和重复收费。
4. 删除旧 scalar conservation 分支与 `_SUBINTERVAL_SUM_TOL` 在本通路的职责。
5. exact audit 接入错误 context 和 canonical row aggregation。

**不可半交付：**只把普通 `sum` 换成 `math.fsum`、但仍以两个独立浮点总量比较定案，视为未实施。

### Slice 4 · 版本、缓存与全链回归

- bump v3 segment scorer helper identity；
- 失效旧 v3 派生 sidecar/cache，不动 GT；
- 跑受影响子集、全仓、sm21 三件套、sm24 受保护树 hash；
- 每个 neuter 仅在临时副本执行并还原。

### 7.1 总成本估计

| 项 | 专注工程日 | 主要影响文件 |
|---|---:|---|
| C 来源身份与拓扑合同 | 5–8 | 新 judge-only 模块、`segment_score.py`、score identity |
| A 证书与请求级仲裁 | 4–6 | 新 evidence/certifier 模块、`segment_score.py`、`score_service.py` |
| B exact interval ledgers | 3–5 | 新 measure/ledger 模块、`segment_score.py` |
| 集成、neuter、全仓与性能 | 2–3 | tests、执行日志 |
| **合计** | **14–22** | 不含审阅返工 |

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

预计直接受影响：

- `tests/test_judge_identity_metric.py`；
- `tests/test_c2_segment_tjunction.py`；
- 少量 v3 score service / score identity contract 锁；
- 新增独立 provenance、arbitration、measure ledger 测试文件。

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

GLM 审后若本文获主控批准，施工只有同时满足以下条件才可报完成：

1. A-L1 至 A-L8、B-L1 至 B-L10、C-L1 至 C-L15 全部按表执行；共用 guard 如实归并计数。
2. 三张核心活体分别得到：
   - advisory 派生 duplicate：NA；
   - genuine duplicate + unrelated advisory：红；
   - 三相邻 span：合法计分。
3. 最小可表示正重叠与 `5e-10` 重叠均被 observation multiplicity 结构门拒绝。
4. `extra` 只来自 observation complement atoms；生产路径中不存在负 extra 的生成和过滤分支。
5. `_cluster_axis` 的生产调用点全部传 occurrence，不存在先展平 float 再“补来源”的旁路。
6. 非相邻重复、自触/自交、同 owner 反向配对、boundary/reading collapse 与 duplicate-after-merge 均有完整 source/hex/diameter context。
7. `score_identity_contract_mismatch` 至少有版本、same-source spread、unproven alias/source collision 三类真实 raise 路径。
8. 任意调换 bucket、diagnostic、cell、floor 输入顺序，出口与 canonical audit 不变。
9. sm24 受保护答案树一个字节不变；答案原子与分母纯函数锁仍绿。
10. sm21 三件套零变化；全仓零新增非预期 red。
11. 新增 exact/topology 结构在真实最大 fixture 上给出时间和内存实测；不得以正交盒子数量估算代替。
12. 每个指定 neuter 在临时副本中至少使点名锁变红，副本还原后工作树干净。

---

## 11. 结论

这轮不再给三个症状各补一个例外：

- A 把“谁有资格判红”改成可验证的全称证明；
- B 把“有没有多收钱”改成区间 owner 重数；
- C 把“这两个数为什么能焊”改成来源身份与拓扑 alias 证书。

三者共同把判卷器的立足点从隐含假设变成可重放证据。本文若通过 GLM 对抗审和主控终审，可直接按 §7 拆施工，不需要施工方再自行补边界裁定。
