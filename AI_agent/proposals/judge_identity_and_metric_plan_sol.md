# 判卷器「数值身份 + 计分度量」方案（GPT 侧 sol 独立稿）

- 日期：2026-07-27
- 性质：规划出稿，不是代码审阅
- 范围：C2 / GT v3 的平面墙身份、拓扑配对、分段归一与计分；sm21 legacy 路径保持原样
- 推荐结论：
  1. 用**文档级、有限直径、歧义即拒绝的坐标身份归并**替换固定量子格；归并只发生在信任边界，之后拓扑只比较离散身份，禁止模糊比较。
  2. 把生产端与 judge 端共同服从的 `coordinate_identity_v1` 设为权威；生产端先规范化再按当前 profile 精确校验，judge 只独立复验，不能另立一把尺。
  3. 墙的分母采用**目标墙几何并集的长度（m）**，不是邻接界面数，也不是“物理墙条数”。
  4. target / observation 先形成精确载体上的**联合切点原子覆盖表**，再按原子一一计量；不做一对多 assignment。
  5. 保留 T 切分思想但取消“切出几段就计几分”；删除标量 `_canonical_coord` 固定落格，合并正交与 general edge 的重复配对内核。
  6. sm24 已签 GT **不改字节、不迁移、不重签**；只使 scorer schema、产品规范化合同和旧分数缓存失效。任何改写 sm24 GT 或其 review 清单的做法都不属于本方案。

---

## 1. 问题、目标与不做什么

### 1.1 已有实证

当前实现把两个本应分开的概念混在了一起：

- “这几个浮点数是否是同一个坐标的不同表示”；
- “两段几何是否共线、相接、覆盖或匹配”。

由此已经出现四类活体：

1. `8.059999999999999` 与 `8.06` 表达同一接缝，上游 GREEN，scorer 报 `invalid_interior_edge_pair`；
2. `0.1 + 0.2` 与字面 `0.3` 同型假红；
3. 固定 `1e-12` 最近格量化后，`8.0600000000005` 与 `8.060000000001 - 5e-13` 只差 1 ulp，却跨量子格边界再次假红；
4. correction validator 用 `_EPS=1e-9` 把 `dx=5e-10, dy=1` 视为正交，scorer 又以精确轴对齐分类，导致生产合同与评测合同不一致；近正交外墙还会在 exact-reverse fallback 中被误作缺失内墙。

计分侧也有两个已证伪行为：

- 同一 4m 墙从一段切为四段后，整墙漏画从 `1/1` 变成 `4/4`，邻接房间越多，墙的权重越高；
- 产品把同一墙正确画成一条 `[0,4]`，面对四条 target 子段时会出现四个等价一对一 assignment，报 `score_match_ambiguous`。

### 1.2 本方案的目标

本方案同时建立两个稳定合同：

- **身份合同**：表示噪声只在信任边界被吸收一次；此后“同一坐标、同一载体、同一覆盖原子”都有离散身份，拓扑判定完全精确。
- **度量合同**：分段只影响计算网格，不影响墙在分母中的权重；得分是目标墙实际长度的覆盖比例。

### 1.3 明确不做

- 不把任何 GT 数据给 gate①、执行器或生产 Agent；GT 仍只有 gate② judge / 人可读。
- 不在 `_pair_*`、覆盖、assignment 或 denominator conservation 中加入 `isclose`、`pytest.approx` 式模糊判据。
- 不把当前正交、无洞、共底面盒子 profile 固化成未来唯一几何模型。
- 不改 sm21 legacy scorer、legacy policy、legacy renderer 或其 frozen assets。
- 不改 sm24 的 `gt.json`、render、review ack、review index 或任何签名绑定资产。

---

## 2. Q1：数值身份合同

### 2.1 唯一判据

定义版本化合同 `coordinate_identity_v1`，参数：

```text
MAX_IDENTITY_DIAMETER_M = 1e-12
link rule              = exact_distance < MAX_IDENTITY_DIAMETER_M
boundary rule          = exact_distance == MAX_IDENTITY_DIAMETER_M => reject
```

这里的 `1e-12 m` 是**输入表示噪声上限**，不是墙匹配容差、绘图容差或物理分辨率。它不用于规范化之后的任何拓扑比较。

一次 score request 内，按 `(coordinate_frame, floor_scope, axis)` 收集 GT 与 product 的所有坐标出现值。对每一轴：

1. 拒绝 NaN、Infinity；把 `-0.0` 与 `+0.0` 先归为同一个精确零；
2. 用 `Decimal.from_float` 或等价的 binary64 精确有理值计算距离，不能先做十进制舍入；
3. 建无向图：两个值的精确距离 `< 1e-12` 才连边；
4. 求连通分量；
5. 若某分量 `max(value)-min(value) >= 1e-12`，拒绝。等于上界是边界歧义；大于上界是链式桥接歧义；
6. 合法分量得到一个 request-local `CoordAtomId`。后续点、边、载体、切点和覆盖只使用 atom id 比较；
7. 物理坐标展示值取该分量精确上下界的中点，仅用于长度和审计输出，**不参与身份比较**。

这不是“把每个值落到最近格”。实数轴上没有预置周期性格边界；原 r2 的两个相邻 binary64，无论位于哪个十进制相位，只要整个集合直径小于上限就进入同一 atom。

### 2.2 “合法浮点写法”的输入合同

仅凭两个无 provenance 的 binary64，不可能从信息论上判断它们是“同一意图的计算噪声”还是“两个真实但极近的坐标”。因此必须先定义什么叫合法；否则“任意写法均合并且任意真缺口均保留”是不可同时证明的要求。

`coordinate_identity_v1` 将一个 score request 称为合法，当且仅当：

1. 同一意图十进制坐标的全部 binary64 出现值，集合直径严格小于 `1e-12 m`；
2. 两个不同意图坐标的所有出现值之间，最小距离严格大于 `1e-12 m`；
3. 不出现恰等于上界的输入；
4. 归并不会造成零长边、相邻重复顶点、环自交、owner 重数冲突或 profile 违反。

“浮点写法”包括不同 JSON 数字拼写、正确舍入的 binary64、以及误差仍落在上述直径合同内的确定性算术结果；合同不承诺吸收无界累计误差或灾难性消减结果。生产者若产生超过上界的漂移，必须先在生产端修正或显式报错，不能要求 judge 猜意图。

### 2.3 共享身份的证明

设同一意图坐标 `c` 的所有合法出现值集合为 `S_c`。

- 因为 `diameter(S_c) < B`，其中任意两值距离都 `< B`，图中两两相连，所以一定在同一连通分量；
- 因为任意另一意图坐标集合 `S_d` 与 `S_c` 的最小距离 `> B`，二者之间没有边；
- 因此连通分量恰好恢复意图等价类，所有合法写法得到同一个 `CoordAtomId`；
- 该结论与数值在全局实数轴上的相位无关，所以不存在固定量子格的边界假红。

三个既有反例的实测距离为：

| 表达 | binary64 距离 | `coordinate_identity_v1` |
|---|---:|---|
| `8.059999999999999` / `8.06` | `1.7763568394002505e-15` | 同 atom |
| `0.1+0.2` / `0.3` | `5.551115123125783e-17` | 同 atom |
| r2 量子边界对 | `1.7763568394002505e-15` | 同 atom |

三者都比 `1e-12` 小约三至四个数量级。

### 2.4 `1e-9` 真缺口不被吞掉的证明

当前 sm24 约 20m 量级，binary64 的一个 ulp 约 `3.55e-15 m`。即使缺口两端各自再承受若干 ulp 的合法表示扰动，`1e-9 m` 与 `1e-12 m` 之间仍有约 1000 倍分离：

```text
1e-9 / 1e-12 = 1000
1e-9 - O(10 ulp at 20m) >> 1e-12
```

因此缺口两端不会连边，会形成两个不同 atom。之后联合切点表中出现只有一侧 owner 的非外墙原子区间，仍精确报 `invalid_interior_edge_pair`。该红结果不依赖浮点 `abs(delta) > tolerance`；它来自“两个 atom 不同 + 原子覆盖不守恒”。

必须新增双侧活锁：

- GT 侧 1e-9 endpoint gap：`score_gt_identity_invalid / invalid_interior_edge_pair`；
- correction 侧 1e-9 endpoint gap：`score_product_identity_invalid / invalid_interior_edge_pair`。

### 2.5 边界与歧义处置

一律 fail closed，不做任意 tie-break：

| 情形 | 外层 code | `context.reason` |
|---|---|---|
| 非有限坐标 | `score_gt_identity_invalid` 或 `score_product_identity_invalid` | `coordinate_identity_nonfinite` |
| 某对距离恰为 `1e-12` | 同上 | `coordinate_identity_boundary` |
| 连续近值形成直径 `>=1e-12` 的链 | 同上 | `coordinate_identity_ambiguous_chain` |
| 归并后边坍缩 / 环变坏 | 同上 | `coordinate_identity_collapse` |
| atom 合法但共享边少一侧、重叠或 owner 重数非法 | 同上 | 沿用 `invalid_interior_edge_pair`、`exterior_duplicate_owner` 等拓扑 reason |
| 产品产物声明的 identity contract/version 不匹配 | `score_product_identity_invalid` | `coordinate_identity_contract_mismatch` |

错误上下文至少记录 contract version、上界、轴、floor、涉及值的十六进制 binary64、精确直径和 occurrence 路径；不得只打印舍入后的十进制值。

### 2.6 后果与限制

- 好处：消除固定格相位；同一组输入与遍历顺序、zone id 重命名、JSON 数字短写/长写无关。
- 代价：真实差异小于 `1e-12 m` 在本合同中不可表达。若归并造成拓扑变化会拒绝；若不造成可观察拓扑变化，它被视为表示噪声。这是明确输入分辨率，不是暗藏 scorer 容差。
- 若未来要支持大地坐标或低精度来源，应先换到局部建筑世界坐标或发布 `coordinate_identity_v2`，不能静默放大 v1 上界。

---

## 3. Q2：上下游口径统一

### 3.1 权威是谁

权威不是 `cell_geometry._EPS`，也不是 judge 某个私有 helper，而是中立、版本化的：

```text
src/agent/geometry/coordinate_identity.py
coordinate_identity_v1
```

该模块不得 import `src.agent.judge`、GT loader 或 case assets。生产确定性层与 gate② judge 都可以单向依赖它：

```text
生产 raw correction
  -> coordinate_identity_v1（只看产品）
  -> 当前 geometry profile 精确校验
  -> canonical correction + identity receipt

gate②
  -> 独立加载 GT + 已接受产品
  -> 校验产品 receipt / 独立重算
  -> 对 GT + 产品联合建立 request-local atom
  -> 精确拓扑与精确覆盖
```

生产端永远不读取 GT；judge 端可以在 gate② 信任边界联合看 GT 和 observation，这符合 gt 铁律。

### 3.2 `_EPS=1e-9` 的处置

`cell_geometry._EPS` 当前同时承担“退化长度”“是否正交”“最小边长余量”等多个语义，必须拆开：

1. **删除它对坐标身份与正交分类的权威性**；
2. 生产端先应用 `coordinate_identity_v1`；
3. 当前 `c2_simple_orthogonal_no_holes` profile 在 atom 化后用精确判据：
   `x1_atom == x2_atom XOR y1_atom == y2_atom`；
4. 仍为近正交但未归为同 atom 的边，生产端明确拒绝：
   `correction_profile_unsupported_nonorthogonal`，不得让它进入 judge 后再伪装成 topology break；
5. 原来的最小边长、bbox 一致性分别改名为语义阈值，例如
   `MIN_EDGE_LENGTH_M`、`BBOX_CONSISTENCY_TOL_M`。这些是业务验证尺，不得复用于身份或拓扑配对。

这属于**收紧上游公开合同**，但收紧发生在规范化之后：真正的浮点表示噪声先被 atom 化，真实的 `dx=5e-10` 斜边则不再被当前正交 profile 冒充“合法正交边”。

### 3.3 生产路径与 dev 评测路径的不对称

约束不对称决定了不能用“judge 放宽一点”作为主方案：

- 生产端负责产出可供几何核消费的确定性几何，必须最早失败，并留下可定位错误；
- judge 是 dev 评测消费者，只能复验生产合同，不能通过 GT 反向修复产品，也不能创造生产端未承诺的拓扑；
- gate① 校验 receipt 和当前 profile，但不 import GT；
- gate② 对 GT 使用同一 identity 算法，是为了避免答案侧自身的浮点异写假红，不是让 GT 成为生产规范化字典。

若生产 receipt 缺失，旧的 v3 correction 只在一次兼容窗口内由 judge 重算；sidecar 必须记
`identity_source="judge_recomputed_legacy_v3"`。新产物缺 receipt 则 fail closed，不能永久保留双合同。

### 3.4 不变量 #6 的升级接缝

`coordinate_identity_v1` 只定义点坐标身份，不定义建筑必须正交、矩形或无洞。几何能力另由 profile adapter 决定：

```text
Coordinate atoms
  -> GeometryProfileAdapter
       c2_orthogonal_v1       （当前）
       straight_segment_v1    （非正交直线）
       polyline_or_curve_v1   （未来）
       floor_with_voids_v1    （中庭 / 回字）
```

联合切点和长度度量面向“载体 + 参数区间”，不是固定 `("V", x)` / `("H", y)`；当前正交 adapter 只是第一个实现。未来非方形、退台、中庭或回字建筑只增加 profile adapter 与载体类型，不推翻身份、覆盖和分母合同。

---

## 4. Q3：分母单位

### 4.1 三个候选

| 候选 | 后果 | 裁定 |
|---|---|---|
| 邻接界面数 | 同长墙因邻接房间多而权重上升；T 切点直接改变分母 | 否决 |
| 物理墙条数 | 必须先人为定义“一道墙”；共线但跨走廊、转角、开口、不同构造何时算同一条会持续引入新歧义 | 不作主分母 |
| 长度 | 对切分满足可加性，天然可证明 partition invariant；未来斜边可扩展为弧长 | **推荐** |

### 4.2 精确定义

每层 target 内墙先去方向、去共享边重复，得到目标墙的一维几何并集 `W_gt`。分母为其一维测度：

```text
denominator_m = measure(W_gt)
passing_m     = measure(W_gt ∩ W_obs_exact)
failing_m     = measure(W_gt \ W_obs_exact)
score         = passing_m / denominator_m
```

其中交、差不是浮点库带 tolerance 的几何布尔运算，而是联合切点之后对 `MeasureAtomId` 集合做精确集合运算。每个 atom 的长度只计算一次；passing / failing 按 atom id 分区，所以守恒由集合恒等式保证：

```text
passing_atom_ids ∩ failing_atom_ids = ∅
passing_atom_ids ∪ failing_atom_ids = denominator_atom_ids
```

不再用当前 `_criterion_from_rows` 的
`abs((passing + failing) - denominator) > 1e-9` 模糊守恒检查。

外墙边界继续是独立 criterion；不能与内墙长度混成一个分母。楼层之间也分别建 ledger，最终才求和。

### 4.3 三种必答情形

设同一道目标墙长 4m：

| 情形 | 原子覆盖 | 得分 |
|---|---|---|
| 整墙画漏 | matched `0m`，missing `4m` | `0 / 4 = 0%` |
| 几何画对，但 target 为 4×1m、observation 为 1×4m（或反之） | 联合切点后四个原子均被双方覆盖 | `4 / 4 = 100%` |
| 只画对一半 | matched `2m`，missing `2m` | `2 / 4 = 50%` |

无权重失真的证明：对任意墙分区 `P={p_i}`，一维测度可加，
`Σ length(p_i) = length(∪p_i)`；把任意 `p_i` 再细分，和不变。因此邻接房间数、target 切段数、observation 落笔数都不能改变这道墙的总权重。

无重复计罚的证明：每个 target measure atom 只属于 matched 或 missing 一次。多个 observation 重复覆盖同一 atom 不会增加 passing，也不会令同一 target 长度失败两次。

### 4.4 extra / 重笔如何处罚

完整度分母只来自 GT，不能让产品多画一条墙反而把 denominator 变大。额外线另建零预算约束：

```text
extra_length_m = measure(W_obs_exact \ W_gt)
duplicate_coverage_m = observation 重复覆盖同一原子的长度
```

- `walls_complete`：只看 `passing_m / target_length_m`；
- `no_extra_walls`：`extra_length_m == 0`；
- `no_duplicate_wall_strokes`：`duplicate_coverage_m == 0`，若产品语义允许重笔则显式 NA，不能悄悄忽略。

这三项分别回答漏画、多画、重复画，不把同一个 target 缺口在多个 criterion 中重复扣分。policy 总判定可要求三项都通过，但 sidecar 必须分别展示原因。

---

## 5. Q4：分段不一致时的匹配规则

### 5.1 选择联合切点规范化

推荐**联合切点原子化**，否决一对多覆盖 assignment。

对每个精确载体：

1. 收集 GT 与 observation 的全部端点 atom，以及合法交点 atom；
2. 按载体参数的精确顺序取 union cuts；
3. 相邻 cut 形成最小 `MeasureAtom`；
4. 为每个 atom 记录精确布尔位：
   `covered_by_gt`、`covered_by_observation`，并记录 owner / source multiplicity；
5. 用 `(carrier_id, lo_atom, hi_atom)` 作为唯一身份；
6. 覆盖、缺失、额外、重复均由布尔位和重数精确派生。

一条长 observation 对四条短 target 时，不存在“把 observation 分配给哪一个 target”的问题；它在四个联合原子上都是 `covered_by_observation=True`。

### 5.2 为什么不选一对多覆盖匹配

一对多会引入额外规则：

- observation 的一次证据是否可以复制给多个 target；
- 多个 observation 同时覆盖一个 target 时如何分配；
- overlap、重复落笔与合法合笔如何区分；
- objective 相同时是否仍报 ambiguous。

这些规则最终仍需建立联合覆盖表才能守恒。直接把覆盖原子作为基本事实，比分配组合更短、更可审计，也不会把切分结构误作产品语义。

### 5.3 对 `score_match_ambiguous` 的影响

- “长 observation 对四个短 target”不再产生 `candidate_assignments=4`，应稳定得到 4m/4m；
- 平面墙路径不再用当前穷举一对一 `assign_plan_segments`，因此
  `score_match_ambiguous(kind="segment")` 从墙分段差异路径退出；
- 完全重复的 observation、一个原子存在多 owner、同一 occurrence 可落入两个 carrier 等，不应以 assignment tie 报错，而应在更早阶段分别报
  `score_product_identity_invalid / duplicate_observation_coverage`、
  `invalid_interior_edge_pair` 或 `carrier_identity_ambiguous`；
- opening 等非本方案墙路径的 `score_match_ambiguous` 保留，sm21 legacy 也不动。

### 5.4 关于“近但不等”的墙

身份、拓扑和墙完整度不能使用位置容差。规范化后载体不同的 observation 不与 target 配对：target 部分记 missing，observation 部分记 extra。

如产品仍需要“偏了 0.2m、但看起来对应哪道墙”的橙色诊断，可另算
`nearest_wall_distance_m`，只用于 renderer / 人审提示，不能：

- 改变 atom 身份；
- 改变 matched / missing / extra；
- 参与 policy pass；
- 作为一对一 assignment tie-break。

这是对“判卷器内部禁模糊配对”的直接落实。

---

## 6. Q5：迁移、兼容与现有 helper

### 6.1 `_canonical_coord`

**删除现有实现和 `_COORDINATE_QUANTUM`。**

原因：标量最近格映射必有全局边界，已经被 1 ulp 活体证伪。不能只换 quantum，也不能改成 Decimal round。

替代物：

- 中立模块的 request-level `build_coordinate_atoms(...)`；
- `CanonicalCoordinate` / `CoordAtomId`；
- `CoordinateIdentityReceiptV1`，记录 contract version、input hash、atom count、最大实际分量直径和 canonical geometry hash。

为减少调用点迁移，可以临时保留同名 shim，但它必须直接抛
`scalar_coordinate_canonicalization_forbidden`，不能继续被生产路径调用。

### 6.2 `_tile_orthogonal_edges`

**保留职责，重构实现。**

保留的部分：

- union cuts；
- elementary interval；
- 每个原子检查 forward/reverse owner；
- 外墙与内墙冲突、单侧悬空、重复 owner fail closed。

必须改变的部分：

- 输入从 `float Point` 改为 atom point / exact carrier interval；
- 不再让“切出的 interval 数”决定 denominator；
- 输出 topology atom 与 measure atom，而不是每个 atom 直接冒充一个独立计分墙；
- docstring 只声称实际覆盖到的 gap / overlap 类别，面积级 zone overlap 仍由上游 coverage validator 负责；
- 抽出载体接口，避免 API 永久绑定 `("V", x)` / `("H", y)`。

可改名为 `_tile_edge_coverage_atoms`；旧名只在一个版本内作为私有转调存在。

### 6.3 `_pair_general_edges`

**删除当前独立 exact-reverse 分支，合并进统一载体覆盖内核。**

当前分支有两个问题：

- 一律要求 reverse，导致合法 single-owner general exterior 被误判；
- 只支持一对一 exact reverse，未来 general T 接头仍需重写。

统一内核至少支持：

- exact reverse；
- single-owner exterior containment；
- 同载体一对多切点；
- owner multiplicity；
- profile adapter 提供的 exact carrier identity 与参数顺序。

当前 C2 正交 profile 只产生水平/竖直 carrier；未来 straight-segment profile 再提供一般直线的精确有理 carrier。未启用的 profile 应报 `unsupported_geometry_profile`，不能伪装成 `invalid_interior_edge_pair`。

### 6.4 `assign_plan_segments` / `score_plan_segments` / `score_policy`

- v3 墙路径用 `build_wall_measure_ledger` 替代一对一
  `assign_plan_segments`；
- `score_plan_segments` 变为从 measure ledger 物化可视化 rows；
- `SegmentScoreRowV8` 增加 `length_m`、`measure_atom_ids` 或等价摘要，不能再默认“一 row = 1 unit”；
- `_criterion_from_rows` 不得对 segment row 默认 `eligible_units=1.0`；
- conservation 用 atom id 集合精确验证；
- scorer schema 从 `"8"` 升到 `"9"`，旧 sidecar / grade PNG 缓存全部失效重算；
- legacy dispatch 在 `gt_identity.schema_version == 2` 时原封不动进入 `legacy_v2`。

### 6.5 sm24 已签答案

当前受控签字证据绑定了：

- source DXF hash；
- conversion request hash；
- review index / inventory hash；
- 候选 GT 与清单中文件 hash。

本方案**不修改任何上述输入或文件字节**，所以：

- `case_tests/test_baseline/gt/sm24_anchor/gt.json` 继续有效；
- `verification.status=human_verified`、reviewer `hortonyyx` 继续有效；
- 不需要迁移 GT，不需要重新 promotion，不需要重签；
- 只能新增运行时 identity receipt / score sidecar；它们不写入受保护答案目录的签名 inventory。

施工前后必须对整个 `sm24_anchor` 受保护清单做 byte hash 对照。若任何 GT / render / review 文件变化，施工直接失败，不能用“规范化”作为改写答案的理由。

需要失效的是：

- scorer schema 8 的既有 `score_vs_gt` sidecar；
- 旧 grade PNG；
- 使用旧 correction identity 合同的阶段缓存；
- 当前挂起 sm24 run 从 correction 接受点之后的派生评分件。

如果实现者选择把 canonicalized coordinate 写回 sm24 GT，则已越出本方案；写回会改变 GT content hash、review inventory，原签名失效，必须走完整重审重签。推荐方案明确不这样做。

### 6.6 sm21 legacy

在 `decide_score_capability` 的 `schema_version == 2 -> legacy_v2` 分支之前不得调用新 normalizer、measure ledger 或 schema 9 serializer。验收以既有 legacy score bytes、render pixel hash 和 dispatch 路径零变化为准。

---

## 7. 一次施工工作包

### WP-0：基线与保护面

1. 记录受影响文件与 sm24 签名 inventory 的 sha256；
2. 记录现有三活体 GREEN/RED 行为、1e-9 RED、4m 三种计分和长对短 ambiguous；
3. 用 affected-tests 工具算受影响子集；
4. 禁止修改 `case_tests/test_baseline/gt/**`。

### WP-1：中立数值身份层

新增 `src/agent/geometry/coordinate_identity.py`：

- `CoordinateIdentityContractV1`；
- `build_coordinate_atoms`；
- chain / boundary / collapse 检查；
- `CoordinateIdentityReceiptV1`；
- exact audit serialization。

必须用稳定排序，结果对输入次序、ID 重命名、dict 顺序不敏感。

### WP-2：生产端统一

1. correction deterministic 层在 polygon 校验前调用 identity normalizer；
2. `cell_geometry._EPS` 拆义；
3. 当前 profile 在 atom 化后精确判正交；
4. 不支持的真斜边在生产端报独立 capability code；
5. accepted correction record 绑定 identity receipt hash；
6. 加 import discipline：生产模块不得 import judge / GT。

### WP-3：GT / 产品 v3 信任边界与拓扑

1. GT 与产品使用同一 contract 共同构建 request-local atoms；
2. 保留现有 outer code，补细粒度 reason；
3. 统一 orthogonal / general carrier 接口；
4. exact union cuts、owner coverage 和 exterior containment；
5. 删除固定格与 general exact-reverse 特判；
6. GT discipline 测试证明只有 gate② 新路径读取 GT。

### WP-4：长度 ledger 与 policy

1. 构建 `WallMeasureLedgerV1`；
2. target / observation 联合切点；
3. matched / missing / extra / duplicate atom 集；
4. policy 以长度计量，删除 segment row 默认 1 unit；
5. 分开 `walls_complete`、`no_extra_walls`、`no_duplicate_wall_strokes`；
6. scorer schema 9，renderer / sidecar 展示 m 与百分比；
7. `score_match_ambiguous(kind=segment)` 不再用于墙分段。

### WP-5：兼容、文档和收口

1. capability dispatch 明确 v3 schema 9 与 legacy v2 分流；
2. 更新 `AI_agent/architecture/judge_grade_model.md`：
   identity contract、长度分母、联合切点、extra 约束；
3. 登记 residual risks；
4. 重跑 sm24 评分派生件，不动 GT；
5. 受影响子集后跑一次全仓 `pytest -q`；
6. neuter / mutation 只在 `/tmp` 副本执行。

---

## 8. 验收锁清单草案

### A. 数值身份

- [ ] A1 `8.059999999999999` / `8.06`：GT validator GREEN，scorer GREEN；
- [ ] A2 `0.1+0.2` / `0.3`：typed correction 生产规范化 GREEN，scorer GREEN；
- [ ] A3 r2 量子边界的 1 ulp 对：同 atom，scorer GREEN；
- [ ] A4 上述三格打乱 occurrence / zone / floor 顺序，receipt hash 与结果不变；
- [ ] A5 GT 1e-9 endpoint gap：RED，reason 为 topology gap；
- [ ] A6 correction 1e-9 endpoint gap：生产或 scorer RED，不能被归并；
- [ ] A7 恰等于 `MAX_IDENTITY_DIAMETER_M`：`coordinate_identity_boundary`；
- [ ] A8 近值链总直径越界：`coordinate_identity_ambiguous_chain`；
- [ ] A9 归并造成零长边：`coordinate_identity_collapse`；
- [ ] A10 NaN / Infinity / contract version mismatch：各自稳定 code；
- [ ] A11 property test：随机 decimal c 的合法多种 binary64 写法共享 atom；
- [ ] A12 property test：在 20m 量级随机加入 1e-9 真缺口，始终为不同 atom；
- [ ] A13 源码守卫：配对、覆盖、ledger conservation 中无 `isclose`、epsilon tie 或 `abs(delta)<=tol`。

### B. 上下游一致

- [ ] B1 typed correction `dx=5e-10,dy=1` 在 atom 化后若仍非正交，由生产端报 `correction_profile_unsupported_nonorthogonal`，judge 不再报 topology break；
- [ ] B2 真正表示噪声造成的 near-axis 在 atom 化后变为 exact axis，并由生产 / judge 同时接受；
- [ ] B3 GT 当前 profile 与 correction 当前 profile 使用同一 exact-axis adapter；
- [ ] B4 production import graph 不含 `src.agent.judge`、`gt.py` 或 case assets；
- [ ] B5 gate① 跑通时证明零 GT 读取；
- [ ] B6 gate② 独立重算 receipt，篡改 receipt 或产物坐标必红；
- [ ] B7 future general profile 的 unsupported code 与 topology code 分离。

### C. T 接头与联合切点

- [ ] C1 一长对四短：联合切出四个 measure atoms，owner 正确；
- [ ] C2 四短对一长：同样结果；
- [ ] C3 双方分点都不同但并集相同：100%；
- [ ] C4 endpoint gap、overlap、single-sided interior、exterior conflict 继续红；
- [ ] C5 exterior single owner 合法；exterior duplicate owner 红；
- [ ] C6 occurrence / segment ID 重命名和顺序不改变 ledger；
- [ ] C7 删除 `_pair_general_edges` 后，现有合法 exact-reverse 与 exterior 行为由统一内核覆盖。

### D. 长度分母

- [ ] D1 4m 整墙漏：`0/4m`；
- [ ] D2 4m 画对但 1↔4 分段：`4/4m`，无 ambiguous；
- [ ] D3 4m 只画一半：`2/4m`；
- [ ] D4 同墙分别切 1、2、4、随机 N 段，denominator / passing / failing 完全相同；
- [ ] D5 把一邻接界面改成四邻接界面但几何并集不变，墙权重不变；
- [ ] D6 observation 重笔不增加 passing；duplicate constraint 红；
- [ ] D7 observation extra 只进 extra constraint，不改变 GT denominator；
- [ ] D8 target measure atom 集严格等于 passing 与 failing 的不交并；删掉模糊 conservation；
- [ ] D9 多楼层分别守恒后总和守恒；
- [ ] D10 renderer 数字与 ledger 完全一致，不从 segment row 数量反推分母。

### E. 歧义与错误语义

- [ ] E1 长 observation 对四 target 不再触发 `score_match_ambiguous`；
- [ ] E2 duplicate observation 报 duplicate coverage，不伪装 assignment tie；
- [ ] E3 carrier identity 真歧义 fail closed，错误上下文包含原始 bits / occurrence；
- [ ] E4 opening 的现有 ambiguity 锁不变；
- [ ] E5 每个新锁有指定 neuter；共享守卫的连带必须合并登记，不能虚报独立承重。

### F. 迁移与回归

- [ ] F1 sm24 受保护 inventory 施工前后逐字节相同；
- [ ] F2 sm24 `human_verified / hortonyyx` 原样可加载；
- [ ] F3 sm24 GT 可完成 identity、topology、length ledger，全流程不改 GT；
- [ ] F4 schema 8 sidecar 被拒绝复用，schema 9 重算；
- [ ] F5 sm21 capability 仍走 `legacy_v2`；
- [ ] F6 sm21 score frozen bytes / renderer pixel hash 不变；
- [ ] F7 全仓 0 failed、0 skipped；既有 xfail 不增；
- [ ] F8 `/tmp` mutation 证明：删除 cluster-cap、1e-9 separation、union cuts、unique-length ledger、legacy dispatch 任一承重机制，对应锁必红。

---

## 9. 残留风险与登记

| 风险 | 当前处置 | 登记 |
|---|---|---|
| 小于 `1e-12m` 的真实几何差异不可表达 | v1 明文限制；造成拓扑变化则拒绝 | `judge.numeric_identity.sub_picometer_resolution` |
| 大地坐标 / 极大绝对坐标下 binary64 精度不足 | 要求建筑局部世界坐标；否则 capability reject，未来 v2 | `judge.numeric_identity.large_coordinate_range` |
| 一般斜线长度含平方根，十进制数值非有限 | ledger 守恒基于 atom id，不基于舍入后长度；未来 adapter 定统一高精度输出 | `judge.metric.general_segment_length_serialization` |
| 曲线、弧墙、多洞 footprint 尚未实现 | carrier/profile adapter 已留接口，不在 C2 冒充支持 | `judge.capability.curve_and_void_overlay` |
| reading 原始笔画偏移过去可显示 orange，精确墙覆盖会记 miss+extra | 允许另报 nearest diagnostic，但不影响 pass | `judge.visual.near_wall_advisory_only` |
| duplicate stroke 的产品语义可能随 reading schema 改变 | 当前独立 constraint；需要时显式 NA，不并入 completeness | `judge.metric.duplicate_stroke_applicability` |

上述债务应写入架构文档的 capability / backlog 表，带 owner、触发条件和目标 schema；不能只留在执行日志。

---

## 10. 最终裁定摘要

### Q1

同一坐标的唯一判据是：在 gate② score request 的信任边界，按
`coordinate_identity_v1` 的文档级有限直径规则得到同一 `CoordAtomId`。固定量子格删除。合法写法集合直径 `<1e-12m`，不同意图集合间距 `>1e-12m`；边界、桥接和坍缩全部拒绝。1e-9 缺口与该上界有约 1000 倍分离，归并后仍成为精确拓扑缺口。

### Q2

权威是生产与 judge 共用、但不依赖 GT 的中立 identity contract。生产先规范化再按 profile 精确校验；judge 独立复验。`cell_geometry._EPS=1e-9` 不再决定坐标身份或正交性，真实近正交边在生产端报 capability error。

### Q3

分母采用目标墙几何并集长度。4m 整墙漏为 `0/4`，分段不同但画对为 `4/4`，画对一半为 `2/4`。长度测度对任意切分可加，故无邻接权重失真；measure atom 唯一计量，故无重复计罚。

### Q4

使用联合切点原子化，不做一对多 assignment。长对短只形成多个确定覆盖原子，不再触发 segment `score_match_ambiguous`；真重复或 carrier 歧义在更早的身份 / 覆盖层用专用错误码拒绝。

### Q5

删除固定格 `_canonical_coord`；保留并重构 `_tile_orthogonal_edges` 的 union-cut / owner-check 职责；删除独立 `_pair_general_edges`，并入 profile 化统一载体内核。sm24 签字答案不改、不迁移、不重签，只重算 schema 9 评分派生件；sm21 legacy 分流和冻结输出保持不变。
