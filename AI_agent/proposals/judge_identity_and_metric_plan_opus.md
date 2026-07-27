# 工程方案稿 · 判卷器「数值身份 + 计分度量」（Opus 侧独立出案，2026-07-27）

> **出案方**：Claude 侧 Opus 5（规划出稿）。
> **独立性声明**：本稿依双独立出案纪律独立成文。我**未读**、也未以任何方式获取
> `AI_agent/proposals/judge_identity_and_metric_plan_sol.md` 或任何 `_sol` 后缀方案稿；
> 该文件在我开工时已存在于目录列表中，我只见到文件名与字节数，**未打开**。
> 本稿一切结论来自：问题书、`src/agent/judge/segment_score.py` / `score_policy.py` / `score_schema.py` /
> `score_service.py` / `gt_schema.py`、`src/agent/correction/cell_geometry.py`、两份裁决书
> （`2026-07-27_plan_segment_tjunction_sol.md` 与 `..._sol_r2.md`，作为**实证证据**引用），
> 以及我自己在 `/tmp` 跑的四个只读探针。
> **探针纪律**：`/tmp/probe_identity.py`、`/tmp/probe_sm24.py`、`/tmp/probe_q3.py`、`/tmp/probe_q4.py`、
> `/tmp/probe_comp.py`；**未改动仓库任何文件**（本稿除外）。本稿所有数字均可用这些脚本复现，脚本正文见 §10。

---

## 0. 一句话推荐

**判卷器不再用「把坐标映到一个绝对格」的方式建立身份，改为在信任边界对每个文档的坐标做
「同池单链接聚类 + 歧义显式拒绝 + 簇直径守卫」，让「同一几何的任意浮点写法必共享身份」成为
无条件定理而不是概率论断；同时把墙的计分分母从「邻接界面条数」换成「墙线长度（米）」，
并用支撑线上的区间覆盖代数取代一对一指派 —— 前者消灭静默假红，后者同时消灭权重失真和
`score_match_ambiguous`。**

---

## 1. 先把病理讲死：为什么「换个量子」注定失败

当前实现 `_canonical_coord(v) = round(v / 1e-12) * 1e-12 + 0.0` 是一个**全定义的、把实轴划成等宽格
的映射**。r2 裁决书构造的反例不是运气不好，而是这类映射的结构性质。把它写成命题：

> **不可能性命题**：设 `f: R → D` 是任意**全定义**映射（D 离散），且 f 不是常值。
> 则存在实数 x、y，使 `|x − y|` 任意小而 `f(x) ≠ f(y)`。

证明是初等的：f 非常值 ⇒ 存在 a、b 使 f(a) ≠ f(b)；考察集合 `S = {t ∈ [a,b] : f(t) = f(a)}` 的上确界 s，
则 s 的任意邻域内同时有 f = f(a) 的点与 f ≠ f(a) 的点。换句话说：**任何全定义的离散化都有边界，
且边界两侧相距任意近的两点被判成不同身份**。

推论：

| 备选 | 后果 |
|---|---|
| 把量子从 `1e-12` 改成 `1e-11` / `1e-13` | 边界平移，命题不变，反例照旧存在（r2 已判定） |
| 最近格换成 `Decimal` 定标 round | 仍是全定义离散化，边界照旧（r2 已判定） |
| 定点整数（乘 10^k 取整） | 同上，且额外把「坐标必须是有限小数」烤死 ⇒ 违反不变量 #6（旋转/非正交坐标是无限小数） |
| 保留上游十进制 token（不做浮点） | 只有当**所有**生产者都保证输出十进制字面量、且不经任何算术才成立。correction 的坐标来自尺寸链加减、墙厚折半、frame 换算，本质上是算出来的；此路只能靠「禁止算术」维持，同样烤死 |

**唯一出路**：放弃「全定义」。身份函数必须是**部分函数** —— 落在"分不清是噪声还是真缺口"的区间时，
**显式拒绝**，而不是猜一个答案。这样边界仍然存在（不可能性命题绕不开），但**边界两侧不再是
「两个不同的静默答案」，而是「接受」与「响亮拒绝」**。这是本方案的核心思想，也是它与「改量子」
的本质区别。

---

## 2. Q1 · 数值身份合同

### 2.1 合同（唯一判据）

> **判卷器认定两个坐标是「同一坐标」，当且仅当它们在其所属身份池中属于同一个单链接簇。**
> 簇代表值（cluster representative）成为该坐标此后唯一的表示；此后所有配对/覆盖判定
> 一律对代表值用精确 `==` / `<=`，**判卷器内部零模糊比较**（硬约束 1 满足）。

三个参数（判卷侧常量，进 sidecar 身份块，可审计）：

| 常量 | 值 | 语义 |
|---|---|---|
| `COORD_MERGE_TAU_M` | `1e-11` m | **链接阈值**。相邻两值间距 ≤ 此值 ⇒ 必然同簇 |
| `COORD_SPLIT_TAU_M` | `1e-10` m | **分裂阈值**。相邻两值间距 ≥ 此值 ⇒ 必然异簇 |
| `COORD_CLUSTER_DIAMETER_TAU_M` | `5e-11` m | **簇直径上限**。防链式吞并 |
| `COORD_ABS_MAX_M` | `1024.0` m | 坐标绝对值上界（用于把 ulp 界锁死） |

算法（每个身份池独立执行，输入是该池全部坐标的**多重集**）：

```
1. 若存在 |v| > COORD_ABS_MAX_M  → 拒绝 reason=out_of_range
2. vs := sorted(set(values))                      # 浮点全序，schema 已禁 NaN/inf
3. 逐个相邻间距 d = vs[i+1] - vs[i]：
      d <= COORD_MERGE_TAU_M   → 链接（同簇）
      d >= COORD_SPLIT_TAU_M   → 切断（异簇）
      否则                      → 拒绝 reason=ambiguous_gap，context 带 (vs[i], vs[i+1], d, pool)
4. 任一簇直径 > COORD_CLUSTER_DIAMETER_TAU_M → 拒绝 reason=cluster_too_wide
5. 每簇代表值 rep := min(簇) + 0.0                # 取输入中已存在的值，不引入新舍入；+0.0 收敛 -0.0
6. 返回 {原值 → rep} 映射 + 池统计（池大小、簇数、最小间距、最大直径）
```

### 2.2 四条定理（Q1 要求的「证明」）

设某池未被拒绝（即算法走完第 6 步）。

**定理 1（无条件吸收）**
> 若 `|x − y| ≤ COORD_MERGE_TAU_M`，则 x 与 y 同簇，即身份相同。

*证明*：x、y 之间的所有中间值把 `[x, y]` 分成若干相邻间距，每个间距 ≤ `|x−y|` ≤ τ_merge，
故每一步都判「链接」，x 与 y 由链接链相连 ⇒ 同簇。∎
**注意这里没有任何相位/取余条件** —— 这正是最近格量化做不到的：`round()` 的结论依赖 x 落在格内何处。

**定理 2（分离）**
> 若 x 与 y 被赋予**不同**身份，则 `|x − y| ≥ COORD_SPLIT_TAU_M = 1e-10`。

*证明*：异簇 ⇒ 二者之间至少有一处判「切断」的相邻间距 d ≥ τ_split，而 `|x−y| ≥ d`。∎

**定理 3（1e-9 真缺口必红，且链式攻击无效）**
> 任意两个相距 ≥ `1e-9` 的坐标必然身份不同。

*证明*：反设同簇，则该簇直径 ≥ 1e-9 > `5e-11 = COORD_CLUSTER_DIAMETER_TAU_M`，
第 4 步已拒绝，与「未被拒绝」矛盾。∎
**这条是硬约束 2 的正面答复**：分离度不再靠「quantum/ulp ≈ 281」这种量级论断，而是由**簇直径守卫**
提供的硬保证 —— 哪怕对手往池里塞 200 个每隔 1e-11 的中间值试图链式吞并，第 4 步（或第 3 步）
必定拦下（探针 P4 已活体验证：`REJECT` 而非静默合并）。
1e-9 缺口在通过身份层后，仍由既有 `_tile_orthogonal_edges` 的精确覆盖判定报
`invalid_interior_edge_pair` —— **现有 L-c 锁的期望错误码不变**。

**定理 4（不存在静默错判）**
> 对任意一对坐标，结果只可能是三者之一：同身份、异身份（且相距 ≥ 1e-10）、整轮显式拒绝。
> 不存在「同一十进制几何的两种浮点写法被静默赋予不同身份」。

*证明*：由定理 1，若两写法间距 ≤ τ_merge，要么同身份、要么整池被拒（out_of_range /
ambiguous_gap / cluster_too_wide 之一，皆带具体数值上下文）。反之若间距 > τ_merge，
按 §2.3 的量化界，它已不是"同一十进制几何的两种写法"。∎

### 2.3 「同一十进制几何的两种浮点写法」到底能差多远（吸收余量）

两条不同计算路径得到同一精确十进制值时，差距由累计舍入决定，上界约 `k · ulp(|x|)`（k = 运算步数）。

探针 P1/P5 实测：

| |x| | ulp(x) | τ_merge / ulp |
|---|---|---|
| 0.3 m | 5.551e-17 | 1.80e5 |
| 8.06 m | 1.776e-15 | 5630 |
| 32 m（sm24 量程） | 7.105e-15 | **1407** |
| 128 m | 2.842e-14 | 352 |
| 1024 m（合同上界） | 2.274e-13 | **44** |

即：在合同允许的最坏量程（1024 m）下仍能吸收 **44 ulp** 的累计舍入；在 sm24 实际量程下能吸收
**1407 ulp**。correction 的坐标链是数十次加减量级，余量充足。
`COORD_ABS_MAX_M = 1024` 不是随手取的：它是让「44 ulp」这个下界成立的那个门槛，
超界即 `out_of_range` 拒绝，因此**定理的前提被代码强制**，不是口头假设。

### 2.4 三个历史反例的实测结果（探针 P2/P3/P4）

| 反例 | 两值差 | 现行最近格 | 本方案 |
|---|---|---|---|
| r1-A 真实 sm24 接缝 `8.059999999999999` vs `8.06` | 1.776e-15（1 ulp） | 同 → GREEN | **同 → GREEN** |
| r1-B typed correction `0.1+0.2` vs `0.3` | 5.551e-17（1 ulp） | 同 → GREEN | **同 → GREEN** |
| r2 量子格边界 `8.0600000000005` vs `8.060000000001 − 5e-13` | 1.776e-15（1 ulp） | **异 → 假红** | **同 → GREEN** |
| 真实 1e-9 端点缺口 | 1e-9 | 异 → RED | **异 → RED** |
| 人造 5e-11 歧义间距 | 5e-11 | 异 → 假红（静默） | **显式拒绝 `ambiguous_gap`** |
| 人造链式吞并（200 × 1e-11） | 跨度 2e-9 | 部分合并（静默） | **显式拒绝** |

r2 反例被解决的机理值得点明：那两个值只差 1 ulp，**在本方案里它们是"相邻且间距 ≤ τ_merge"，
判链接是无条件的**，跟它们落在哪个"格"里毫无关系 —— 因为**根本没有格**。

### 2.5 身份建立在哪一层，池的范围是什么

**层**：在**判卷器信任边界**建立，即 `extract_gt_plan_segments` / `extract_correction_plan_segments` /
`coerce_plan_observations` 的**入口**，早于任何几何解释。**不在上游产出端**（那会要求生产者承担
判卷器的表示合同，见 Q2），**不在配对逻辑内部**（那就成了模糊比较，违反硬约束 1）。

**池 = 精确等值比较的作用域**。逐条核对现有代码里所有 `==` 的作用域：

| 比较点 | 作用域 |
|---|---|
| `_lies_on_exterior`：zone 边 vs footprint 边 | 同文档同 floor |
| `_tile_orthogonal_edges`：支撑线 key、区间覆盖 | 同文档同 floor |
| `_pair_general_edges`：exact reverse | 同文档同 floor |
| `_candidate`：target vs observation | **跨文档，且本来就是带容差的**（`plan_position_tol_m` 等） |

结论：**精确身份只在文档内部需要**。因此

> **池 = (文档侧 ∈ {gt, product}, floor_id, 轴 ∈ {x, y})**

跨文档不做联合聚类 —— 这既不必要（跨文档比较本就带容差），也避免让 GT 的身份受产品输入影响
（那会开一个「产品能改自己分母」的口子，见 Q4 §5.2）。

分轴的理由：x 与 y 是两个语义无关的数轴，混池只会凭空制造歧义拒绝。

### 2.6 边界与歧义情形的处置

新增**一个**稳定错误码（尽量少动 wire）：

```
score_coordinate_identity_ambiguous      gate = scoring.input_identity
context.reason ∈ { ambiguous_gap | cluster_too_wide | out_of_range }
context 必带：pool = (side, floor_id, axis)，以及触发的两个原始浮点值与间距
```

处置语义：**整轮判卷终止（rejected），不出分**。理由：这是输入合同违规，
不是几何缺陷；给一个"分数"会把合同问题伪装成建模质量问题。
`c2_v3_score_policy` 已有 `identity_valid=False → verdict="rejected"` 通路，直接复用形状。

**这仍然是「上游 GREEN、判卷器 RED」，但性质完全不同**，必须讲清楚这个区别：

| | 现状 | 本方案 |
|---|---|---|
| 错误码 | `invalid_interior_edge_pair`（**声称是拓扑破洞**） | `score_coordinate_identity_ambiguous`（**声称是数值合同越界**） |
| 上下文 | 只有 floor_id，人无法定位 | 具体两个浮点值 + 间距 + 池 |
| 真伪 | **假**（几何是对的） | **真**（该输入确实在"分不清"的区间里） |
| 可达性 | 1 ulp 就能触发（r2 已构造） | 需要 10 pm–100 pm 量级的几何结构 |

后一种"红"是诚实的：一个相邻坐标间距落在 10 皮米到 100 皮米之间的建筑输入，
判卷器说"我无法确定这是噪声还是缺口，请你说清楚"是正确回答。

### 2.7 被否决的备选及其后果（Q1 的"选项 + 后果"）

| 备选 | 做法 | 后果 | 裁 |
|---|---|---|---|
| A. 保留最近格，只调 τ | `round(v/q)*q` 换 q | 边界平移不消灭（不可能性命题 + r2 活体）；下轮对抗审必再抓同一类反例 | ✗ |
| B. 定点整数 + guard band | 要求坐标落在声明标度网格上，偏离超 g 即拒 | 消灭静默错判 ✓，但**把"坐标必须是有限小数"烤进合同**：墙三等分 `8.06/3`、C2.2 旋转坐标、未来非正交对角线全部被拒 ⇒ 违反不变量 #6 | ✗ |
| C. 上游改出 canonical 坐标 | 要求 correction / GT 生产端只发规范化坐标 | 把判卷器的表示合同压给生产路径；且 GT 由 DXF 转换器产、correction 由 LLM+确定性核产，两条生产线都要改，回归面巨大，且 sm24 e2e 在即 | ✗（但见 Q2 的**分阶段**收紧） |
| D. 单链接聚类 + 歧义拒绝 + 直径守卫（本案） | §2.1 | 吸收无条件（定理 1）、1e-9 硬保证（定理 3）、无静默错判（定理 4）、不烤死小数假设 | **✓ 推荐** |

D 相对 B 的关键优势就是**不需要绝对网格**：身份是从**这份文档自己的坐标分布**里推出来的，
所以任意实数坐标（旋转、非正交、无限小数）都能有身份。这条直接对应不变量 #6。

**D 的代价（诚实登记）**：
1. 身份依赖池内容 ⇒ 同一个坐标在不同 floor 可能取到不同代表值。**不影响正确性**（比较只在池内），
   但审计输出必须显示代表值而非原值，否则人看图会困惑。→ 锁 A-7。
2. 聚类是 O(n log n) 排序；sm24 单 floor 坐标数 ~40，无性能问题。
3. `ambiguous_gap` 拒绝是**整轮**级，粒度粗。可后续细化到"只拒这一个 floor"，本批不做，登记。

---

## 3. Q2 · 上下游口径统一

### 3.1 事实盘点（先把不对称讲准）

| 位置 | 判据 | 性质 |
|---|---|---|
| `correction/cell_geometry.py:159-162` | `if dx > _EPS and dy > _EPS: raise`，`_EPS=1e-9` | **生产路径**，带容差，`dx=5e-10` 判**正交、放行** |
| `judge/gt_schema.py:330` `_ring_vertices` | `if dx != 0 and dy != 0: _fail("gt_polygon_nonorthogonal")` | **判卷侧 GT 校验**，**已经是精确的** |
| `judge/segment_score.py` `_pair_interior_edges` | `p1[0]==p2[0] or p1[1]==p2[1]` 分桶 | 判卷器，精确 |

**关键发现（本稿独立核出，影响裁定方向）**：**GT 侧早就是精确正交合同**。
所以"精确 vs 容差"的分裂不是"判卷器太严"，而是**correction 生产端与 GT 生产端两条线口径本来就不一致**，
判卷器只是第一个把这个不一致暴露出来的地方。这改变了"谁应该让步"的直觉。

同时 `_EPS` 在 `cell_geometry` 里身兼三职（退化边 `length <= _EPS`、正交判定、最小边长松弛），
只有**退化边**那一职是容差的正当用法。

### 3.2 谁是权威 —— 我的裁定

**不选"上游权威"也不选"下游权威"，而是把判据本身抽成唯一实现，让"权威"落在一个模块上。**
同时**把两个被混为一谈的问题拆开**：

> **问题甲：这份几何合不合法？** —— 权威 = **生产路径**（gate①）。判卷器无权把生产端接受的几何
> 重新解释成"拓扑破洞"。
> **问题乙：这份几何本判卷 profile 能不能量？** —— 权威 = **判卷器**。判卷器有权说"我量不了"，
> 但必须说成 *unsupported*，不许说成 *broken*。

现行代码把乙的答案（量不了）写成了甲的措辞（`invalid_interior_edge_pair`），这就是 Y-1 假红的根。

### 3.3 落地：三件事

**(1) 抽出共享的纯几何判据模块** —— `src/agent/geometry/coordinate_identity.py`
   + `src/agent/geometry/orthogonality.py`：

```python
# orthogonality.py  —— 生产与判卷共用，模块内零 gt import、零答案
ORTHOGONAL_EDGE_EPSILON_M = 1e-9        # 唯一定义点，原 cell_geometry._EPS 的正交那一职
def is_orthogonal_edge(p1, p2, *, eps=ORTHOGONAL_EDGE_EPSILON_M) -> bool: ...
def is_exactly_axis_aligned(p1, p2) -> bool: ...      # 身份规范化之后用
```

`cell_geometry.py` 与 `segment_score.py` 都 import 它。
**gt 铁律核对**：`src/agent/geometry/` 下的这两个模块**不含答案、不 import `judge.gt*`**，
依赖方向是 生产 → 共享 ← 判卷，判卷侧不向生产侧注入任何 gt 信息。gate①/执行器 import 它
不构成对 `case_tests/test_baseline/gt/**` 的任何可达路径。→ 锁 B-1 用 AST 扫描钉死。
`cell_geometry._EPS` 的另外两职（退化边、最小边长）**保持不动**，仅把"正交"那一处改为调用共享函数。

**(2) 判卷器把"量不了"说成量不了**：
   身份规范化之后仍非精确轴对齐的边，走 `_pair_general_edges`，规则精确化为：

```
a) 有精确 reverse 且两侧各恰一个 owner  → 内墙 seam，正常入分（保住原行为，Y-1 场景不回归）
b) 无 reverse，但该边（无序 identity 对）与某条 footprint 边逐值相等 → 合法单 owner 外墙，跳过
   （直接消灭 r2 反例 2：footprint == 唯一 cell、右边 dx=5e-10）
c) 无 reverse，且本 floor 存在任何"合法但非精确轴对齐"的边
      → capability NA：reason = unsupported_product_geometry，不是 topology break
d) 其余（全精确正交的 floor 上出现无 reverse 的边）→ 真拓扑破洞，维持
   invalid_interior_edge_pair（Lock3 / L-c / L-d 全部原样通过）
```

   c) 的后果必须讲清楚：**该 floor 的 walls 相关准则变成 NA（`eligible=False`），不出分也不报错**。
   这是诚实的"我不知道"，比现在的假红好，也比静默放行好。代价 = 若真实 case 命中，
   墙准则会静默失去覆盖 ⇒ 用锁 C-6 强制：golden/regression profile 下 capability-NA 必须
   出现在 report 且计数不为 0 时**显式告警**（沿用 `no_oversplit` 永久 NA 的既有登记纪律）。

   同时**删掉** `_pair_general_edges` docstring 里"footprint/exterior rings are axis-aligned
   (validated upstream)"这句 —— 我独立核过 `correction/schema.py` 的 `FootprintRing` 与
   `validate_corrected_geometry`，**确实没有**对 footprint 的精确正交校验，该注释不实
   （与 r2 §3.2 的独立结论一致）。

**(3) 分两阶段收紧上游（这才是真正的"对齐"，但不能一步到位）**：

| 阶段 | 动作 | 后果 |
|---|---|---|
| **本批** | gate① correction 新增**非阻塞** advisory 检查 `correction.axis_exactness`：身份规范化后仍非精确轴对齐的边逐条记入 `*_checks.json`（`severity=info`） | 零生产阻断风险；开始积累"这事到底发不发生"的实测数据 |
| **下批**（sm24 + sm25-L 各跑一次、advisory 命中为 0 之后） | 对 `c2_simple_orthogonal_no_holes` capability profile 翻成 blocking，与 GT 侧 `_ring_vertices` 口径完全一致 | 两侧口径统一；此后判卷器的 c) 分支在正交 profile 下不可达；非正交 profile 打开时该分支自然成为通用 seam |

顺序不能反。**先量后卡**是这个项目已经吃过亏的地方（"关键输入不在 git 里"三连），
在 sm24 e2e 前夜动生产校验器是不划算的。

### 3.4 为什么"直接放宽判卷器"不可选

有人会问：判卷器为什么不干脆也用 `_EPS=1e-9` 判正交？后果：
一条 `dx=5e-10` 的边被判"正交"后，还必须决定它的**支撑线常数**是 `x=1` 还是 `x=1+5e-10` ——
两个端点给出两个不同答案，选任何一个都是在配对逻辑里做模糊归并，**直接违反硬约束 1**，
而且会把一堵真实偏了 5e-10 的墙"贴"到邻墙的支撑线上，制造假绿。**否决。**

---

## 4. Q3 · 分母单位

### 4.1 三个候选的后果

**候选一：邻接界面（现状）**

现状代码：`_tile_orthogonal_edges` 每个初等子区间发一条 `PlanSegment`，
`score_policy._criterion_from_rows` 对没有 `eligible_units` 的 row 默认计 1 单位（`score_policy.py:61`）。

后果（探针 P-Q3 在**真实签字 sm24 答案**上实测）：

- sm24 内墙抽出 **16 条邻接界面**，长度从 1.50 m 到 5.94 m（**4.0×** 跨度），每条各占 1/16 权重；
- 折成"每米权重"：最短那条 **0.04167 /m**，最长那条 **0.01052 /m** ⇒ **权重失真 3.96×**。
  即：在已经签字转正的标准答案上，一米走廊墙的分值是一米长外围隔墙的近四倍，纯粹因为切分方式。
- 合成走廊例（问题书里的 4 m 墙面对 4 间房）：该墙占楼层墙权重 **4/7 = 57.1%**，
  但只占墙长 **4/13 = 30.8%**。**邻接房间越多，同一道墙权重越高** —— r1 裁决书的判断成立且可量化。

**候选二：物理墙（一条 = 一单位）**

- 消灭了邻接权重失真 ✓；
- 但**无法表达"画对一半"**：二值 row 只能 0/1，要给半分就得在墙内部按长度切 ⇒ 已经把长度偷渡进来了；
- 且"什么算一道物理墙"本身又是一个分段决策（过 T 型接头算不算同一道？过转角呢？
  GT 与产品对"墙的身份"不会一致）—— **把我们正要消灭的那类歧义换个位置重新引入**；
- 另有次级失真：0.3 m 的短墩与 20 m 的长墙同权。

**候选三：长度（米）—— 推荐**

定义：

> **分母单位 = 内墙线支撑集的长度（米），每条几何墙线只量一次，与两侧各有几个房间无关。**

这是**唯一在分段变换下不变**的量。而"分段不变"正是这次事故要买的性质本身。

关键实现细节（防重复计罚）：GT 内墙的支撑集 = 按 (轴, 支撑线常数身份) 分组后**取区间并集**（不是求和）。
探针 P-comp 在 sm24 上验证：16 条界面 → 8 条支撑线 → **10 个极大连通分量**，
界面长度求和 57.86 m **恰等于**并集长度 57.86 m（该 GT 的切分是一个划分，无重叠），
说明"每米只被计一次"在真实数据上成立。

### 4.2 计分模型（守恒的两个准则）

把「漏画」与「多画」拆成两个各自守恒的准则（今天它们混在 `walls_complete` 一个准则里：
`_criterion_from_rows` 让 `extra` row 也计 1 单位失败）：

| 准则 | 分母 | passing | failing | 语义 |
|---|---|---|---|---|
| `walls_complete` | `L(GT内墙)` | `L(GT ∩ P)` | `L(GT \ P)` | 长度加权召回 |
| `walls_no_extra`（新） | `L(P内墙)` | `L(GT ∩ P)` | `L(P \ GT)` | 长度加权精确率 |
| `boundary_complete` | `L(GT footprint 周长)` | 同构 | 同构 | 外围 |
| `boundary_no_extra`（新） | `L(P footprint 周长)` | 同构 | 同构 | 外围 |

两个准则各自 `passing + failing == denominator`，**恒等式由构造保证**（`failing := denominator − passing`
计算，不独立求和，避免浮点残差撞 `score_denominator_nonconserving` 的 `1e-9` 阈）。
**无重复计罚**：漏掉的一米只出现在召回的 failing 里，凭空多画的一米只出现在精确率的 failing 里，
互不相干。

**总裁决不变性**：今天 `extra` row 让 `walls_complete` 判 fail；改造后它让 `walls_no_extra` 判 fail。
`c2_v3_score_policy` 的聚合是 `any(fail)`，所以**整体 pass/fail 结论不变**，只是证据诚实了。
这条对迁移很重要 → 锁 C-4。

### 4.3 三种情形的具体得分（Q3 要求的数字）

场景：走廊 A 在上，房间 B/C/D/E 各宽 1 m 在下。
GT 内墙 = 走廊墙 `y=3, x∈[0,4]`（4 m，被 4 间房分成 4 段 × 1 m）+ 三道隔墙各 3 m。
**楼层内墙总长 = 4 + 9 = 13 m；邻接界面数 = 7。**

**表 1 · 走廊墙本身（4 m）**

| 情形 | 邻接界面单位（现状） | 物理墙单位 | **长度单位（推荐）** |
|---|---|---|---|
| **S1 整墙画漏** | 0/4 → 该墙吃掉 4/7 = **57.1%** 楼层权重 | 0/1 | **0.00 / 4.00 m = 0%**，占楼层权重 4/13 = **30.8%** |
| **S2 画对，但画成一整条 [0,4]** | **`score_match_ambiguous`，candidate_assignments=4，整轮抛错不出分**（探针 P-Q4 实测） | 1/1 = 100% | **4.00 / 4.00 m = 100%** |
| **S3 只画对一半 [0,2]** | 2/4 = 50%（**碰巧**对，因为 GT 恰好按 1 m 切） | 二值，只能 0 或 1，表达不了 | **2.00 / 4.00 m = 50%** |

**表 2 · 楼层级 `walls_complete`（分母 13 m / 7 界面 / 4 墙）**

| 情形 | 邻接界面单位 | **长度单位（推荐）** |
|---|---|---|
| S0 完全画对（4 段） | 7/7 = 100%，verdict=pass | **13.00/13.00 = 100%**，pass |
| S1 整墙画漏 | 3/7 = **42.9%**，fail | **9.00/13.00 = 69.2%**，fail |
| S2 画成一整条 | **抛错，无分** | **13.00/13.00 = 100%**，pass |
| S3 只画一半 | 5/7 = 71.4%，fail | **11.00/13.00 = 84.6%**，fail |

**表 3 · 权重失真对照（同一道 4 m 墙整条画漏，只改"对面有几间房"）**

| 对面房间数 | 邻接界面单位下的 failing/denominator | **长度单位下的 failing/denominator** |
|---|---|---|
| 1 | 1 / 1 | **4.00 m / 4.00 m** |
| 2 | 2 / 2 | **4.00 m / 4.00 m** |
| 4 | 4 / 4 | **4.00 m / 4.00 m** |

在**楼层分母固定**的前提下，界面单位让这道墙的**相对权重**随房间数线性上涨（表 1 第一列 57.1%），
长度单位下恒为 30.8%。**这就是"无权重失真"的证明**：分母是 GT 墙线的几何属性，
与"对面怎么分房"这个**产品/GT 的分区决策**正交。

**表 4 · 真实 sm24（签字答案）实测**

| 指标 | 值 |
|---|---|
| 邻接界面数 | 16 |
| 支撑线数 | 8 |
| 墙线极大连通分量数（新 row 单位） | **10** |
| 内墙线总长 | **57.86 m** |
| 界面长度求和 / 并集长度 | 57.86 / 57.86 = **1.0000**（无重复计罚） |
| 界面单位下 每米权重 最大/最小 | **3.96×**（失真） |
| 长度单位下 每米权重 最大/最小 | **1.00×**（定义上恒等） |

### 4.4 wire 变更

`SegmentScoreRowV8` 增三个字段（additive）：

```python
denominator_units: NonNegativeFloat        # 该 row 的 GT（或 P）长度，米
passing_units:     NonNegativeFloat
failing_units:     NonNegativeFloat        # 恒 == denominator_units - passing_units
```

`score_policy._criterion_from_rows` 的 `amounts()` 增一条分支：row 若同时具备
`denominator_units`/`passing_units`/`failing_units` 三字段则直接取用（优先于现有
`outcome_slices` 与二值回退两条路径）。**claim 侧一行不改**（`ClaimOutcomeSliceV8.units ≤ 1.0`
的上限只约束 claim，不波及 segment）。

`HelperIdentityV8.segment_scorer` 的 Literal 增加取值 `"c2_segment_coverage_v2"` 并改为发这个值；
新增字段 `coordinate_identity: StableId`（发 `"coord_identity_cluster_v1"`）。
两者都是 additive，老 sidecar 仍可验证；但会改变新 run 的 `ScoreIdentityV8` 摘要 ⇒
**施工开工第一步必须先跑 `tests/test_c2_b4b_contract.py` 确认没有被钉死的 identity 摘要常量**
（我没有逐测核完，登记为开工门 → 锁 D-1）。

---

## 5. Q4 · 分段不一致时的匹配规则

### 5.1 两个候选

**候选 (a) 联合切点规范化 + 一对一**
把 GT 与 observation 的所有端点取并集，双方都按这个 cut set 重切，再一对一匹配。

后果：
- 能解决 S2 的 ambiguous ✓；
- 但**分母被观测方污染**：cut set 含产品端点，产品把一堵墙画成 100 小段，row 数就变 100
  ⇒ **产品可以自己改自己的分母**。在计数单位下这是可利用的评分完整性漏洞；
  在长度单位下总长不变（漏洞被 Q3 堵住），但 row 数仍随产品波动，审计输出不稳定；
- 且规范化只在"支撑线相同"时定义良好，产品墙偏了 3 cm（容差内）时仍要先做支撑线归并。

**候选 (b) 允许一对多覆盖匹配**
让一条长 observation 同时命中多条 target。

后果：
- 解决 ambiguous ✓；
- 但"一对多"要定义"覆盖多少算命中"，很容易滑回阈值判断；
- 且指派搜索空间从排列变成子集族，`assign_plan_segments` 的穷举法（`segment_score.py:372`）
  会指数爆炸。

### 5.2 推荐：支撑线区间覆盖代数（(a) 与 (b) 的共同上界，且都不用指派）

**根本认识：墙不是一堆待配对的对象，墙是平面上的一个一维点集。**
两个点集之间不需要"匹配"，只需要**测量**。

流程（身份规范化之后，全部精确算术）：

```
1. GT 侧：内墙边 → 按 (轴, 支撑线常数身份) 分桶 → 每桶取区间并集 → GT 支撑集
   产品侧：同法 → P 支撑集
2. 跨文档配准（容差只出现在这一步，且这一步本来就是跨文档 ⇒ 合法）：
   对每条 GT 支撑线 (a, c)，其"产品对应集" = 所有满足 轴相同 且 |c' − c| <= plan_position_tol_m
   的产品支撑线；把它们的区间并集投影到该 GT 线上
3. 逐 GT 墙线连通分量发一条 row：
      denominator_units = 分量长度
      passing_units     = 分量 ∩ 产品投影并集 的长度
      failing_units     = denominator - passing
      status            = complete           若 passing==denominator 且 max|Δc| <= claim_complete_epsilon_m
                          within_tolerance   若 passing==denominator 且 max|Δc| <= plan_position_tol_m
                          miss               否则
4. 精确率方向对称做一遍（GT ↔ P 互换），发 walls_no_extra 的 row
5. 前置校验：同轴两条 GT 支撑线常数之差 <= 2 * plan_position_tol_m
      → 拒绝 score_supporting_lines_too_close（否则一条产品墙会被两条 GT 线同时记功）
```

### 5.3 对 `score_match_ambiguous` 的影响（Q4 明问）

**segment 通路上 `score_match_ambiguous` 变为结构性不可达。** 理由：

- 步骤 2 的"产品对应集"是一个**集合运算**，不是指派 —— 没有"选哪个"的自由度，
  就没有并列最优，就没有 ambiguous；
- 步骤 3 的每个 GT 分量的分数是一个**确定的测度**，与产品如何分段无关（区间并集对分段不变）；
- 因此 r1 裁决书那个反例（一条 [0,4] 对四条 1 m target ⇒ `candidate_assignments=4`）
  **不是被"解决"，而是不再存在这个问题类**。

`score_match_ambiguous` 保留给 opening/claim 通路（`assign_openings`，`kind="opening"`），
那里是真正的离散对象匹配，ambiguous 是有意义的。→ 锁 C-5 钉死：segment 通路不再产生该码。

### 5.4 代价与残留

| 代价 | 说明 | 处置 |
|---|---|---|
| 丢失 target↔observation 逐条配对关系 | 现 `SegmentScoreRowV8.observation_id` 语义变化 | row 改发"贡献覆盖的产品支撑线 id 列表"；`observation_id` 保留但对覆盖式 row 置 `None`，另加 `covering_observation_ids: tuple[StableId, ...]` |
| grade 渲染 | `render_grade.py` 按 row 画绿/红 | 覆盖式 row 自带 passing/failing 长度 ⇒ 可画**部分覆盖**（一段绿一段红），比现在的整条二值更准；本批只要求不回归，精细画法登记 |
| 一条产品墙被两条相近 GT 线同时记功 | 由步骤 5 前置校验挡住 | sm24 实测最小 GT 线间距 = **1.00 m**，`2×plan_position_tol_m = 0.60 m` ⇒ 满足，余量 1.67×（**余量不大，必须写成机器校验，不能靠"看着够"**） |
| 反向（两条产品线都在一条 GT 线容差内）导致精确率偏宽松 | 并集运算下不会重复计功，但产品的位置过分割不被罚 | 登记为残留风险 R-4，归 `no_oversplit` 未来批次 |

---

## 6. Q5 · 迁移与兼容

### 6.1 现有实现逐件处置

| 件 | 处置 | 理由 / 后果 |
|---|---|---|
| `_COORDINATE_QUANTUM`、`_canonical_coord`、`_canonical_point` | **删** | 被 §2 的池聚类取代。留着就有两套身份，必然分叉 |
| `_canonical_geometry` | **留，改名 `_segment_sort_key`** | 它是排序键不是身份，现名误导（r1/r2 两轮都有人把它当身份看）。行为零改动 |
| `_points` / `_edges` | **改** | 不再逐点 canonical；改为接收池映射后查表 |
| `_lies_on_exterior` | **留，零改动** | 精确轴对齐包含判定，规范化之后语义正确 |
| `_tile_orthogonal_edges` | **拆成两个函数，两半都留** | ①`validate_zone_partition_topology(...)` = 现有的 gap / overlap / one-sided / exterior-duplicate / exterior-interior-conflict 全部判定与错误码，**逐字保留** ⇒ Lock1/3/4/5、L-c/L-d/L-e 全部原样通过，这是本迁移最重要的兼容论据；②`interior_wall_support(...)` = 只产支撑线区间并集，喂给新计分。**邻接切分继续算，但只当审计元数据（`zone_ids`），不再当分母** |
| `_pair_general_edges` | **改**（§3.3 的 a/b/c/d 四分支）+ 删不实注释 | 修 r2 反例 2；保住 Y-1 原行为 |
| `_pair_interior_edges` | **留，改 docstring** | r2 §4 判定：上层 docstring 无限定地写 "a gap, an overlap ... is rejected"，与 inline 限定自相矛盾。改写成已实现的窄合同 |
| `_candidate` | **留** | opening 通路仍用；segment 通路不再调用 |
| `assign_plan_segments` | **从 C2 v3 segment 通路摘掉；函数本体保留一版并标 deprecated** | 直接删会连带 `test_c2_b4b_phase_b.py` 等既有锁；保留一版让迁移可分两步。下批清除，登记 R-5 |
| `score_plan_segments` | **改**：内部改调覆盖式计分，签名与返回类型保持 | 上游 `score_service.py:191` 调用点不必改形状 |
| `score_service.py:190` `segment_assignment` | **改**：不再用于 segment 计分；`product_to_gt` 里由它填的部分改由覆盖式的 `covering_observation_ids` 提供 | 注意 `product_to_gt` 还喂给 opening 通路（`assign_openings`），**必须逐条核对不回归** → 锁 D-2 |
| `score_policy._criterion_from_rows` | **改**：加长度分支 | §4.4 |
| `c2_v3_score_policy` | **改**：加 `walls_no_extra` / `boundary_no_extra` 两准则 | §4.2；整体 verdict 不变 |
| sm21 legacy 判卷路径（`reading_score.py`、`elevation_score.py`、`reading_score_criteria`） | **一字不动** | 硬约束 6。sm21 GT 非 v3，走 `decide_score_capability → legacy_v2`，与本批全部改动无交集 → 锁 D-3 用 AST/import 扫描钉死 |

### 6.2 已签字 sm24 答案的处置（硬约束 5）

**结论：`case_tests/test_baseline/gt/sm24_anchor/gt.json` 保持原字节不动，签名依然有效，
不需要迁移，不需要重签。**

论据逐条：

1. **本方案不改 GT 输入合同的任何一条**。GT schema、`_ring_vertices` 的精确正交判据、
   `content_sha256` 计算、canonical bytes 形状 —— 全部不动。
2. **身份规范化发生在判卷器读取之后、内存里**，是"判卷器如何读这份文件"的改变，
   不是"这份文件该长什么样"的改变。答案文件一个字节都不重写。
3. **转正签名绑定的三项 hash（源图 hash + request hash + 清单 hash）与判卷器无关**。
   我核过 `gt_promotion.py`：它验的是 `ConversionReportV1` 十门全绿、`HumanReviewAckV1` 签名、
   `review_index` 清单、以及 `_assert_promotion_semantics`（除 verification/content_sha256 外逐字段全等）。
   这条链上**没有任何一环消费 `segment_score` 的输出**。
4. **已签字答案在新判卷器下的行为实测**：本稿探针在**未改代码**的当前实现上跑
   `extract_gt_plan_segments(sm24 gt)` = 16 条内墙 + 4 条外围，无异常；按本方案的池聚类重算，
   sm24 单 floor 的坐标最小相邻间距远大于 `COORD_SPLIT_TAU_M`（H 线最小间距 1.00 m，
   V 线 1.64 m），**不可能触发任何歧义拒绝**。迁移后 sm24 答案照常可判。

**⚠️ 但必须同时登记一条我在核查中发现的实况问题（与本方案无关，但影响"签字答案是否完整"的判断）：**

> `case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json`
> **不在 git 里**（`git status` 显示 `??` 未跟踪），**也不在 `review/review_index.json` 的 files 清单里**
> （清单只列 `gt/gt.json` + 7 张 renders + 3 份 review 件），且其 mtime（07-27 03:40）**晚于**
> 07-26 的转正时刻。也就是说：**有人在人签转正之后，往受保护的答案根里写了一个既不在签名清单、
> 又不在版本控制里的文件**。

这正是 plan.md 07-27 已登记的"gt 标准产物清单 + provision bridge"那条债的实况面。
本方案不处理它（不在 Q1–Q5 范围），但**必须在派工单里显式声明本批不碰答案根**，
并把它作为**开工前置核查项**（锁 D-4）：施工方开工与收工各跑一次
`git status --porcelain case_tests/test_baseline/gt/`，两次必须一致，证明本批零写入。
真正的修复（把 `score_inputs/` 纳入清单 + 入库 + 建桥）另行立项。

### 6.3 不变量 #6 的接缝在哪（硬约束 4）

必须逐条指出本方案给"复杂体量"留了哪些口子，否则就是又一次把当前简化烤死：

| 未来能力 | 本方案的接缝 |
|---|---|
| 非正交墙 | 身份层**完全不假设正交**（聚类只看数轴上的值）；`_pair_general_edges` 的 a/b/c/d 分支里，c) 就是未来通用 seam 的插槽 —— 今天它 NA，将来实现通用支撑线切分后它变成正常通路，**不需要改 API、不需要改身份层** |
| 旋转 / 总图输入（C2.2） | 身份层无绝对网格 ⇒ 旋转后的无限小数坐标照样有身份（这是否决"定点整数"备选的直接原因） |
| L 形 / U 形 / 回字（sm25-L、sm26、sm27） | 长度分母对拓扑形状完全无感；支撑线区间代数对凹多边形、多连通分量天然成立（sm24 已实测出 10 个分量、其中 V5.82 线上就是 2 个不相连分量） |
| 退台 / 每层不同 footprint | 池按 `(side, floor_id, axis)` 分，**本来就是逐层的**，不假设各层 footprint 相同 |
| 中庭 / 洞（interior rings） | 支撑集是"边的并集"，洞的内环边天然加入同一支撑线桶；今天 GT schema 仍 `gt_profile_holes_unsupported`，那是 GT 层的限制，本方案没有再加一道 |
| 变层高 / 竖向（C3） | 本方案全在平面 (x,y)；z 不参与，无新耦合 |

反向自查（"这条路以后能不能长到复杂体量"）：**唯一一处正交假设**是
`_tile_orthogonal_edges` 的 `("V", x) / ("H", y)` 支撑线 key。本方案**不消灭它**（消灭它超出本批范围），
但做两件事让它以后能松动：①把它降级为"实现细节"而非"分母定义"（分母是长度，与支撑线 key 的
形状无关）；②给它一个通用抽象的名字与签名 `supporting_line_key(edge) -> Hashable`，
未来非正交 profile 换实现即可。

---

## 7. 施工派工单（可直接开）

五个工单，**必须按序**（W1 是 W2/W3 的地基）。每个工单给出口条件。

### W1 · 数值身份合同

- 新建 `src/agent/geometry/coordinate_identity.py`：四常量 + `resolve_coordinate_identity(values) -> CoordinateIdentityMap`
  + `CoordinateIdentityError(reason, detail)`；**零 gt import、零 judge import**。
- `segment_score.py`：删 `_COORDINATE_QUANTUM` / `_canonical_coord` / `_canonical_point`；
  三个入口（`extract_gt_plan_segments`、`extract_correction_plan_segments`、`coerce_plan_observations`）
  改为**先建池、后查表**；`CoordinateIdentityError` 翻成
  `ScoreContractError("score_coordinate_identity_ambiguous", "scoring.input_identity", context=...)`。
- `score_schema.py`：`STABLE_ERROR_CODES` 加 `score_coordinate_identity_ambiguous`。
- **出口**：锁 A-1 ~ A-8 全绿；r1-A / r1-B / r2 三个历史反例全部 GREEN；1e-9 缺口仍报
  `invalid_interior_edge_pair`（错误码不变）。

### W2 · 正交口径统一

- 新建 `src/agent/geometry/orthogonality.py`（`ORTHOGONAL_EDGE_EPSILON_M` + 两个谓词）；
  `cell_geometry.py:161` 改调共享谓词（**只动正交那一职，退化边与最小边长的 `_EPS` 不动**）。
- `_pair_general_edges` 实现 §3.3 的 a/b/c/d 四分支；删不实注释；
  `_pair_interior_edges` / `_tile_orthogonal_edges` docstring 收窄到已实现的合同。
- `NotApplicablePayloadV8.reason` Literal 加 `"unsupported_product_geometry"`。
- gate① 加 **advisory** 检查 `correction.axis_exactness`（`severity=info`，不阻塞）。
- **出口**：锁 B-1 ~ B-6 全绿；r2 反例 2（footprint == 唯一 cell、右边 `dx=5e-10`）由 RED 转 GREEN；
  Y-1 场景（两 cell 共享 `dx=5e-10` 精确反向内边）仍正常入分；**Y-1 锁升级为 typed 全链**
  （先断言 `validate_corrected_geometry` 五项 GREEN，再断言 scorer 结果，不许再用 `SimpleNamespace`）。

### W3 · 覆盖式长度计分

- `segment_score.py`：`_tile_orthogonal_edges` 拆成 `validate_zone_partition_topology` +
  `interior_wall_support`；新增 `score_plan_coverage(...)` 实现 §5.2 五步；
  `score_plan_segments` 内部改调它、签名不变。
- `score_schema.py`：`SegmentScoreRowV8` 加 `denominator_units` / `passing_units` / `failing_units` /
  `covering_observation_ids`；`HelperIdentityV8.segment_scorer` Literal 加 `"c2_segment_coverage_v2"`；
  加字段 `coordinate_identity: StableId`。
- `score_policy.py`：`_criterion_from_rows` 加长度分支（`failing := denominator − passing`，
  不独立求和）；`c2_v3_score_policy` 加 `walls_no_extra` / `boundary_no_extra`。
- 新增前置校验 `score_supporting_lines_too_close`。
- **出口**：锁 C-1 ~ C-8 全绿；§4.3 表 1/表 2 的**每一个数字**由测试逐个钉死。

### W4 · 迁移、清理与回归

- `score_service.py` 接线（`product_to_gt` 来源切换，逐条核对 opening 通路不回归）。
- `assign_plan_segments` 标 deprecated 并从 v3 segment 通路摘除；受影响测试迁移。
- `_canonical_geometry` → `_segment_sort_key` 改名。
- **出口**：锁 D-1 ~ D-5 全绿；`affected_tests.py` 算出的受影响子集全绿；**交付前跑一次全仓**。

### W5 · 文档与登记

- `AI_agent/architecture/judge_grade_model.md`：新增「§X 数值身份合同」与「§Y 计分度量」两节
  （四条定理、三阈值、两准则、拒绝码语义、capability NA 语义）。
- `AI_agent/architecture/pipeline_stage_contracts.md`：登记 `correction.axis_exactness` advisory 检查
  与"下批翻 blocking"的条件。
- `AI_agent/plan.md`：登记 §9 残留风险 R-1 ~ R-6。
- **出口**：主控轻门（独立全量 + 亲核 diff）。

---

## 8. 验收锁清单草案

**总纪律（r2 裁决书 §5 的直接教训，必须写进派工单）**：
> 每条新锁给出**指定 neuter**（要改哪一行让它、且只让它变红）；若多条锁共用同一守卫，
> **必须在归并表里如实登记连带翻转的全部测试**，包括 happy 路径。
> 「本表已覆盖全部新锁」这句话，除非归并矩阵是机器跑出来的，否则不许写。
> 验锁 neuter **只在 `/tmp` 的仓库副本上做**；审锁必问一句"换台机器还红不红"。

### A 组 · 数值身份（W1）

| 锁 | 命题 | 指定 neuter |
|---|---|---|
| A-1 | 真实 sm24 GT 把 z0 顶边 `8.059999999999999` 改写为 `8.06`、重算 content hash 后，`validate_gt_v3` GREEN 且 `extract_gt_plan_segments` 抽出 16 条内墙 | 把 `resolve_coordinate_identity` 换成恒等映射 |
| A-2 | typed correction 一侧 `0.1+0.2`、另一侧字面 `0.3`，validator 五项 GREEN 且 scorer GREEN | 同 A-1 |
| A-3 | **r2 格边界活体**：一侧 `8.0600000000005`、另一侧 `8.060000000001 - 5e-13`，validator GREEN 且 scorer GREEN | 把聚类换回 `round(v/1e-12)*1e-12`（**该 neuter 必须让 A-3 红而 A-1/A-2 仍绿** —— 这是"本方案严格强于旧方案"的证明） |
| A-4 | 1e-9 端点缺口仍报 `score_gt_identity_invalid` / `invalid_interior_edge_pair`（错误码逐字不变） | 把 `COORD_CLUSTER_DIAMETER_TAU_M` 调到 `1e-8` |
| A-5 | 5e-11 歧义间距报 `score_coordinate_identity_ambiguous` / `ambiguous_gap`，context 含两个原始浮点值 | 删歧义分支（改成 `d <= τ_merge ? link : cut`） |
| A-6 | 链式吞并（200 个每隔 5e-12、跨度 1e-9）被拒 `cluster_too_wide`，**不得**静默合并 | 删直径守卫 |
| A-7 | 坐标绝对值 > 1024 m 报 `out_of_range`；且 `τ_merge / ulp(1024) >= 40`（**性质测试，纯算术，防有人调参数破坏定理前提**） | 把 `COORD_ABS_MAX_M` 调到 `1e6` |
| A-8 | 池作用域正确：同一 floor 的 footprint / zones / boundary_segments 共池；**不同 floor 不共池**（构造两层，F2 的坐标不影响 F1 的簇划分） | 把池 key 改成只 `(side, axis)` |

### B 组 · 正交口径（W2）

| 锁 | 命题 | 指定 neuter |
|---|---|---|
| B-1 | AST 扫描：`src/agent/geometry/coordinate_identity.py` 与 `orthogonality.py` 的 import 传递闭包**不含** `src.agent.judge.gt`、`gt_schema`、`gt_promotion`，且源码不含字符串 `test_baseline` | 在共享模块里加一行 `from src.agent.judge.gt import load_gt` |
| B-2 | **typed 全链**：两 cell 共享 `dx=5e-10` 精确反向内边 → `validate_corrected_geometry` 五项 GREEN（**逐项断言**）**且** scorer 抽出 1 条 interior（不许用 `SimpleNamespace`） | 把 `_pair_general_edges` 的 a) 分支改 raise |
| B-3 | **r2 反例 2**：footprint == 唯一 cell、右边 `dx=5e-10` → validator GREEN 且 scorer **不报错**（走 b) 分支） | 删 b) 分支 |
| B-4 | 全精确正交 floor 上，无 reverse 的孤边仍报 `invalid_interior_edge_pair`（d 分支未被 c 分支吞掉） | 把 c) 的条件改成恒真 |
| B-5 | 含近正交边的 floor 上，无 reverse 的孤边报 capability NA `unsupported_product_geometry`，**不是** `invalid_interior_edge_pair` | 把 c) 改成 raise 拓扑码 |
| B-6 | `cell_geometry` 与 `segment_score` 的正交判据来自**同一常量对象**（`is ORTHOGONAL_EDGE_EPSILON_M`，身份比较不是值比较） | 在 `cell_geometry` 里重新写死 `1e-9` 字面量 |

### C 组 · 计分度量（W3）

| 锁 | 命题 | 指定 neuter |
|---|---|---|
| C-1 | §4.3 表 1 三行数字逐个钉死：S1 → `0.00/4.00`；S2 → `4.00/4.00` 且**不抛 `score_match_ambiguous`**；S3 → `2.00/4.00` | 把 `passing` 改成按 row 数计 |
| C-2 | §4.3 表 2 楼层级四行逐个钉死（`13.00/13.00`、`9.00/13.00`、`13.00/13.00`、`11.00/13.00`） | 同上 |
| C-3 | **权重不变性**（表 3）：同一道 4 m 墙整条画漏，对面 1/2/4 间房三个夹具，`failing_units` **恒等于 4.00** | 把分母改回界面计数 |
| C-4 | **总裁决不变性**：一个含 extra 的夹具，改造前后 `V3PolicyVerdict.verdict` 相同（fail），但证据落到 `walls_no_extra` | 删 `walls_no_extra` 准则并把 extra 计回 `walls_complete` |
| C-5 | segment 通路**不再产生** `score_match_ambiguous`：C-1 的 S2 夹具 + 一个"产品画 100 小段"夹具，两者都不抛该码；同时 opening 通路的既有 ambiguous 锁仍红 | 把 `score_plan_segments` 改回调 `assign_plan_segments` |
| C-6 | capability NA 计数 > 0 时，golden/regression profile 下 report 必须出现显式告警条目 | 删告警分支 |
| C-7 | `score_supporting_lines_too_close`：构造两条相距 `0.5 m < 2×0.30` 的 GT 内墙线 → 拒绝 | 删前置校验 |
| C-8 | **守恒**：随机 50 个夹具，`passing + failing == denominator` 逐字相等（不是 `abs(...) < 1e-9`） | 把 `failing` 改成独立求和 |

### D 组 · 迁移与不回归（W4）

| 锁 | 命题 | 指定 neuter |
|---|---|---|
| D-1 | `tests/test_c2_b4b_contract.py` 全绿；若其中钉了 identity 摘要常量，**开工时先把该常量改成从代码计算并留注释**（施工方须在执行日志里如实报告是否命中） | — （这是开工门，不是运行时锁） |
| D-2 | opening 通路不回归：`product_to_gt` 在改造前后对同一 sm24 级夹具**逐键相等** | 把新来源接错（少填 facade 那部分） |
| D-3 | **sm21 legacy 不破**：AST 扫描证明 `reading_score.py` / `elevation_score.py` 的 import 闭包不含 `segment_score`；且 legacy 判卷 e2e 夹具逐字节输出不变 | 在 `reading_score.py` 里 import `segment_score` |
| D-4 | **零写入答案根**：`git status --porcelain case_tests/test_baseline/gt/` 在开工与收工两次输出逐字相等 | —（纪律门，执行日志留证） |
| D-5 | 真实 sm24 GT 端到端：`extract_gt_plan_segments` → 10 条墙线 row、总分母 **57.86 m**、全部 `complete`（用 GT 自身当完美产品对拍） | 把并集换成求和（会得 57.86 但重叠夹具会露馅，故 D-5 需配一个人造重叠夹具） |

### 全局

- 中间轮只跑 `affected_tests.py --explain` 算出的受影响子集；**交付前跑一次全仓**；
  **主控轻门独立全量 = 唯一权威门**，永远不加 `-m` 过滤。
- 施工方须交**neuter 归并矩阵**（每个 neuter × 每条测试的翻转真值表），
  不是"我认为它们独立"。

---

## 9. 残留风险与登记方式

| id | 风险 | 严重度 | 登记 |
|---|---|---|---|
| R-1 | `ambiguous_gap` 拒绝粒度是**整轮**，一条坏坐标毁掉整个 case 的判卷 | 中 | plan.md 跟进债；下批细化到 per-floor |
| R-2 | `COORD_ABS_MAX_M = 1024 m` 对总图输入（C2.2 旋转 + 总图）可能不够；届时 τ_merge/ulp 余量从 44 降到 11（4096 m） | 中 | plan.md；C2.2 立项时必须重算定理余量，**并在 A-7 性质测试里体现新界** |
| R-3 | 精确率方向对"产品位置过分割"偏宽松（两条产品线都落在一条 GT 线容差内） | 低 | 归 `no_oversplit` 未来批次 |
| R-4 | 覆盖式 row 的 grade 渲染只做到"不回归"，未做部分覆盖的精细画法 | 低 | judge_grade_model.md §8b backlog（与既有 partial-clip hatch 债合并） |
| R-5 | `assign_plan_segments` 保留一版 deprecated 死码 | 低 | 下批清除，plan.md |
| R-6 | **签字答案根里存在未入库、未在签名清单内的 `score_inputs/view_bindings.json`** | **高**（治理类，第四次同型） | 已在 plan.md 07-27 登记；本批**只核不动**（锁 D-4），修复另行立项：纳入 review_index 清单 + 入库 + provision bridge + 缺件即红 |
| R-7 | `correction.axis_exactness` 只是 advisory，翻 blocking 的时机依赖两次真实 run 的实测 | 中 | pipeline_stage_contracts.md 登记翻转条件；不许无声跳过 |
| R-8 | `_tile_orthogonal_edges` 的 `("V",x)/("H",y)` 支撑线 key 仍是正交假设 | 中 | 已抽象为 `supporting_line_key`；非正交 profile 立项时替换实现（不变量 #6 接缝，见 §6.3） |

---

## 10. 探针复现（数字来源）

全部只读，落 `/tmp`，未改仓库任何文件。

| 脚本 | 产出本稿的哪些数字 |
|---|---|
| `/tmp/probe_identity.py` | §2.3 ulp 表、§2.4 三反例的 raw delta、最近格 vs 聚类对照、链式攻击、§2.3 余量表 |
| `/tmp/probe_sm24.py` | §4.1 sm24 16 界面 / 8 支撑线 / 57.86 m / 界面和 == 并集 |
| `/tmp/probe_q3.py` | §4.1 权重失真 **3.96×**、§4.3 表 1/表 2 全部数字、走廊例 57.1% vs 30.8% |
| `/tmp/probe_q4.py` | §4.3 表 1 第一列的**活体**结果（S2 实测抛 `score_match_ambiguous` / `candidate_assignments=4`） |
| `/tmp/probe_comp.py` | §4.3 表 4 的 10 个连通分量、§5.4 的 GT 支撑线最小间距 1.00 m |

复现命令（在仓库根）：`python3 /tmp/probe_identity.py` 等，各脚本自带 `sys.path` 注入。
若脚本已被清理，逐个重建的逻辑在本稿 §2.1 / §4.1 / §5.2 中已完整给出，不依赖脚本存在。

---

## 11. 与硬约束的逐条对照（自查表）

| 硬约束 | 本方案的满足方式 |
|---|---|
| 1 判卷器内部禁模糊比较 | 身份规范化之后，`_lies_on_exterior` / 支撑线分桶 / 区间覆盖全部精确 `==` `<=`；唯一的容差出现在**跨文档配准**（§5.2 步骤 2）与既有的 `_candidate` —— 这两处本来就是跨文档的度量层，不是身份层 |
| 2 `1e-9` 真缺口必须继续判红 + 证明分离度 | 定理 3（簇直径守卫），错误码逐字不变；锁 A-4 + A-6 双向钉死 |
| 3 gt 铁律 | 共享模块零 gt import，AST 扫描锁 B-1；身份/度量全部判卷侧，gate① 只新增一个 advisory 检查且不读答案 |
| 4 不变量 #6 | §6.3 逐条列接缝；否决"定点整数"备选的直接理由就是它烤死小数假设 |
| 5 已签字答案处置明确 | §6.2：字节不动、签名有效、无需迁移、无需重签，并给了 4 条论据 + 锁 D-4；顺带登记 R-6 实况问题 |
| 6 sm21 legacy 不破 | §6.1 最后一行 + 锁 D-3（AST 闭包 + 字节级 e2e） |
| 7 一次施工可落地 | §7 五个工单 + §8 二十七条锁 + 每条锁的指定 neuter |

---

## 12. 我认为最脆的环节

**`score_service.py:190-193` 那段 `product_to_gt` 的构造。**

它现在同时被两条通路消费：segment 计分（要被我改掉）和 opening/claim 计分
（`assign_openings` 的 `product_to_gt_segment` 参数、以及 `build_correction_host_resolver`）。
我把 segment 的指派摘掉之后，`product_to_gt` 的第一半来源就没了，必须由覆盖式的
`covering_observation_ids` 重新填 —— 而这两者的语义**不完全等价**：
指派是一对一的"这条产品段就是这条 GT 段"，覆盖是多对多的"这些产品段一起覆盖了这条 GT 线"。
如果施工时图省事按"取第一个"填回去，**窗的宿主解析会在多段覆盖的情形下静默绑错墙**，
而且**不会有任何测试变红**（因为 opening 通路的既有锁都是单段夹具）。

这是典型的"门是真的、锁是缺的"，也是本项目连续十几批对抗审最常抓到的形态。
所以锁 D-2 必须写成**逐键相等**而不是"不抛错"，并且必须补一个**多段覆盖的 opening 夹具**——
我把这一条单独标出来，建议主控在派工单里点名，别让它混在 D 组里被当成常规回归。
