# 裁决书 · 刻度认领设计稿跨家族复核（GPT）

- 日期：2026-09-04
- 复核对象：[`2026-09-04u_tick_claim_design.md`](../execution/2026-09-04u_tick_claim_design.md)
- 任务书：[`2026-09-04u_tick_claim_design.md`](../request/2026-09-04u_tick_claim_design.md)
- 权威口径：[`reading_correction_split_guide.md` §十四 / §十五](../../../guides/reading_correction_split_guide.md)
- 复核方：GPT 家族（与作者 Claude 家族不同）

## 一、裁决

**REWORK · 阻断 6 · 不阻断 2。**

设计稿抓对了三个大方向：x 必须进入冻结证据契约；模型只返回候选 ID、代码算坐标；B4 当前确实绕过证据 bundle 直接读裸 `x_range_m`。但稿子还不能作为施工契约，原因是：

1. 把权威口径允许的“一档由链算出”错误收窄成“每条边必须是 `cum_mm` 节点”；
2. D5-c 用相邻刻度中点作最近邻分区，会把明确二档的 East `O01` 自动认成一档；
3. D6 的 hash + “无公开构造器”只写出了目标，没有给出真正不可伪造的类型结构；
4. 漏了 §十五要求的裁决账及第一步/第二步响应面的类型隔离；
5. 没有处理一档链真值与 pipeline 10 mm 出口可能冲突的已知问题；
6. D7 没有按当前树识别 B2 返工 3 与 T4-a 返工 2 的实际改动面。

本单无需跑测；我没有运行 pytest。

## 二、§十四 / §十五 delta 核对（逐条）

### 2.1 任务书抄入的五条核心口径

| # | 权威口径 | 对设计稿的判定 | 冲突 / 遗漏 |
|---|---|---|---|
| 1 | correction 两步；第一步逐图独立、第二步跨图；两步各跑一遍三拍 | **方向一致，但结构不完整** | D3–D6 把认领放在第一步、把 B4 放在第二步，顺序正确；但直接复用现有 `CorrectionDecisionResponseV1` 时仍强制携带 `whole_building_review`，设计没有用 phase 判别联合或同等结构禁止第一步产生第二步语义，也没有把自动/模型裁定绑定进裁决账。见 B-4。 |
| 2 | 模型输出决定，代码输出坐标 | **一致** | D2 的结果只带 ref，D3 只让模型回 `candidate_id`/枚举，响应树无数值字段；这是稿子最扎实的一处。 |
| 3 | 尺寸链优先；像素只用于指认；一档值可来自节点或由链算出 | **存在直接冲突** | D2 虽列了 `segment_sum`，却强制 `resolved_local_x_ref` 指向一个 `cum_mm` 节点；D4 又把全部一档合法域限定为节点成员。它表达不了累加、分段相减、轴线 ± 半墙厚等合法的一档派生值。见 B-1。D5-c 还让像素距离的最近邻关系直接决定自动认领，越过了“判断归模型”的边界。见 B-3。 |
| 4 | 两档都出值；二档是正常低权威出口，不是失败/债 | **大体一致，但下游形态没闭合** | `pixel_only`、空 `dimension_refs` 和 `evidence_ref` 正确表达了二档；`reject_all → 二档` 也给了合法出口。但 D2-d/D7 写成 B4 改读“认领结果的一档值”，没有明确第二步同样消费二档并保留低权威；二档按 10 mm 出口后的确定值也没有在结果/裁决账中闭合。 |
| 5 | gt = 1 mm；pipeline 出口 = 10 mm；坐标存储 = 0.1 mm 整数 | **三个数抄对，消费关系遗漏** | D2/D4/数字表正确区分了三个值，未把 0.1 mm 当 pipeline 出口。但没有落实 §15.11 的“两个分辨率分别显式声明、分别被消费”；也没处理一档链值不是 10 mm 整数倍时，pipeline 规整会破坏链真值的问题。见 B-5。 |

### 2.2 因未读到 §十四 / §十五而遗漏的要求

1. **一档不只等于节点。** 权威 §14.2b/§15.4 明写“节点或由链算出来的值”；设计的 `segment_sum` 只是枚举名，没有可复算的运算证书，且被“必须有单个节点 ref”的互锁条件抵消。
2. **输出必须有裁决账。** §15.2 要求记录“谁在哪一步被判成什么、依据哪档证据”，§15.3 又要求自动动作也记账。设计提到 `AutoActionV1` 与 response，却没有让每个 `OpeningEdgeTickClaimV1` 结构性绑定 auto rule 或 packet/response/decision hash。
3. **第一步必须在结构上保持逐图独立。** 现有 response 强制 `whole_building_review`；“第一步里让它填 accept”仍是纪律，不是阶段隔离。
4. **颗粒度有两个显式消费者，不要求相等。** §15.11 要求 gt 1 mm 与 pipeline 10 mm 各自声明、各自消费；设计只引用了数值，没有给二档输出的配置引用/消费证书，也没登记判分侧最大半格 5 mm 的已签字推论。
5. **一档链真值与 10 mm 出口的冲突必须显式收口或停报。** 指南已举 `1935 mm → 1940 mm` 的风险；当前口径同时要求链优先与 pipeline 10 mm，设计不能因当前 fixture 恰为 10 mm 整数倍就略过。

不记为遗漏的内容：§14.4 四分类、第二步常识/模数推理、F 组三条参考值的模型执行机制均被本任务书明确排除在本单施工范围外；D7 只需把它们当边界，不要求本稿设计实现。

## 三、阻断 findings

### B-1 · 一档契约与 D4 合法域错误收窄为 `cum_mm` 节点

**证据：** 设计 D2-b 第 123–134 行允许 `value_source="segment_sum"`，但又要求所有一档都有 `resolved_local_x_ref`，其含义被限定为“指向被认领的那个 `cum_mm` 节点”；`dimension_refs` 也被限定为 `calibration.x.cum_mm` 节点。D4 第 217–225 行进一步规定每条边必须是 `cum_mm` 成员。权威指南第 1038 行和第 1166 行允许“节点或由链算出来的值”。

**影响：** 合法的一档输入会被误拒。例如链给出轴线 3000 mm 与洞口宽 900 mm，代码按已引用证据算出边界 2550/3450 mm；两边是链派生事实，却未必是 `cum_mm` 节点。当前 schema 既没有封闭运算表达式，也没有位置容纳多个操作数及其 ref。

**必须修：** 把一档做成判别联合，至少区分 `chain_node` 与 `chain_derived`。`chain_derived` 必须携带封闭运算枚举、按角色标注的 operand refs/声明 ref 和可复算结果 ref/证书；代码在 0.1 mm 整数算术域重算，模型仍只选择候选/运算 ID。D4 的零阈值判据应是“引用存在且运算精确可复算”，不能是“结果一定在 cum 集合”。

### B-2 · D4 失效条件没有列全，且缺少区间级不变量

**正面结论：** 若前提明确限定为 `i < j`、`cum` 是同一条干净链的精确前缀和、两端确实引用 `cum[i]`/`cum[j]`，则
`cum[j] - cum[i] = sum(values[i:j])` 成立；用整数算术和精确成员检查可做到零 epsilon。这部分论证成立。

**不成立之处：** 它只证明“选到两个链节点后能得到连续段和”，不证明这两个节点界定该洞，也不覆盖合法的链派生边。作者列出的三类失效不全。

**我补出的会判错输入：**

- `lo` 与 `hi` 都认领同一个节点 0：两条边分别都是合法成员，D4 逐边检查全绿，但洞口宽度为 0；D2 只校验原始像素证据 `x_lo < x_hi`，没有校验认领后的两个 ref 仍严格有序。
- `lo` 认到 6000、`hi` 认到 0：两边分别通过成员检查，但结果反向；D4 的公式暗含 `i < j`，契约未强制。
- B-1 的 2550/3450 合法链派生边会被判红，是 false negative。

**必须修：** 加洞口区间级载体/验证，强制同源、角色、严格有序、非零宽，并对 `chain_derived` 重算；把这些新失效条件写回 D4-c。

### B-3 · D5-c 确实把未签字判断挤到了“中点分流”

**判定：是。** 它不是固定毫米常量，但仍是一个未签字的相对判断阈值：相邻 tick 间距的 1/2。Voronoi/中点分区会给除精确中点外的每个实数唯一最近 tick，因此没有“离所有 tick 都远”的结构出口。所谓“等距分界带”若只指中点，宽度为零、几乎永不触发；若真是一个带，就还缺一个带宽阈值。

当前数据已直接反证它：East `O01` 两边 536.7/2164.6 mm 都处于 `[0, 3000)`，按 D5-c 都唯一归到 tick 0；这会自动产出 `[0, 0]`，而稿子自己又把该洞定为二档。D5-b 说“明确在段中可自动二档”，但没有任何结构判据把“段中”与“最近 tick 的唯一 Voronoi 区”区分开。

**必须修：** 自动认领只能依赖已有的显式结构证据（例如 reading 已提供且可解析、角色闭合的 `dimension_refs`/witness 绑定）；凡需要用像素距离判断“是不是这个刻度”的情况都进入模型裁决，或在确有显式“该处无尺寸标注”证书时自动二档。不得再用最近邻/中点替代建筑语义判断。

### B-4 · D6 还没有在类型/结构层成立

**正面结论：** “raw claim 与 validated carrier 是不同类型”方向正确，且 hash 重算适合检查内容在传递中是否漂移。

**为什么仍不成立：**

1. 当前 `finalize_bundle` 是公开纯函数且在 `__all__` 中；改 `tick_ref`/tier 后重新 finalize 就会得到自洽新 hash。hash 是完整性校验，不是授权封印。
2. “`SealedTickClaimsV1` 由 validator 产出、无公开构造器”只是目标句，没有说明构造能力如何不可获得。B2 返工 3 正在修的恰是：`frozen=True`、类型注解、最外层 `isinstance` 都挡不住公开构造器和鸭子元素。
3. “没有坐标字段”并未冻结决定。第二步只要把 `tick_ref` 从 A 换成 B、或把 `tier` 换成 `pixel_only`，就已经改了第一步事实，无需写浮点坐标。

**必须修：** D6 要给出可审的实际形态，例如构造时必须持有模块私有、从不导出/返回/存实例的 seal；或者第二步完全不信任 carrier 值，每次从其冻结引用及第一步裁决账重建。第二步入口只能接受该真封印类型，并且正反例要覆盖重 finalize、替换元素、替换 `tick_ref`/tier。

### B-5 · §十五的裁决账、阶段隔离与颗粒度消费没有进入契约

设计的 `OpeningEdgeTickClaimV1` 只记录结论和证据，不记录该结论来自哪个 `AutoActionV1` 或哪个 packet/response/item decision；因此 §15.2 要求的“谁在哪一步被判成什么”无法从结果结构闭合复算。现有 `CorrectionDecisionResponseV1` 又强制 `whole_building_review`，而 D3 声称响应侧“一字不改”；这无法在类型层保证第一步逐图独立。

同时，二档只指回 536.7/2164.6 mm 原始像素字节，没有记录 pipeline 10 mm 声明点及规整后的确定结果/派生证书；一档若为 1935 mm，设计也没说明 10 mm 出口是保真、豁免还是变成 1940 mm。该冲突已由指南显式提出，不能留给施工方猜。

**必须修：**

- 让每条 claim 结构性绑定 auto rule/action hash 或 packet hash + response/decision hash；bundle 输出完整裁决账。
- 给第一步独立的 phase 类型/判别联合，类型上不能携带第二步 `whole_building_review` finding；或给出同等强度的封闭约束。
- 给二档增加“原始像素 ref → 使用的 pipeline 分辨率声明 ref → 代码规整结果”的可复算派生记录。
- 对“一档链真值 vs 10 mm pipeline 出口”停报请用户/主控收口；未签字前不得自行选舍入或豁免。

### B-6 · D7 对两条当前在飞线的描述已过期

| 在飞线 | 设计稿是否覆盖 | 当前树里的真实改动面 | 对本方案的影响 |
|---|---|---|---|
| **B2 返工 3** | **只笼统写了“排在 B2 第三轮之后”，没有读到本轮门；不合格** | `2026-09-04w_B2_rework3.md` 明确改 `multifloor.py`，唯一阻断是 `ValidatedFloorLadder` 构造能力公开；要求真 seal/逐元素受封/从冻结字节重读 | D6 不能把 B2 称为“现成范式”；它仍在解决与本稿完全同形的公开构造问题。应待返工 3 过审后按其最终模式复用，并避免碰 `multifloor.py`。 |
| **T4-a 返工 2** | **完全漏掉；稿子只写旧的 obligation/hash churn** | `2026-09-04x_T4a_rework2.md` 改 `opening_synthesis.py` 的 obligation resolver/binding，锁“成功解析输入集合 == live key 集合”，并禁止碰 B4 `affected_refs` 源绑定 | 本方案也要改 `opening_synthesis.py` 的 B4 输入，存在直接文件/语义碰撞。施工必须排在 T4-a 返工 2 合并并过审之后，重基线后保持其 resolver/binding 与 `affected_refs` 锁。 |

设计稿 R1–R5 对旧一轮 hash churn、B4 裸 dict、既有重现性锁的识别仍然有价值；问题是风险清单没有更新到当前在飞形态。

## 四、不阻断 findings

### N-1 · “每个数字”自查远非全量，且至少两处分类错误

设计自查只列了少量领域数，漏了数据数组、距离、反例数、分支估算、日期/版本/源码行号等大量数字。更重要的是：

- `≤34 mm` 是派工方/指南选来分组的经验 cutoff，属于**既有判断值**，不是图纸声明值；虽未进入本方案生产判据，也不能标成“声明值”。
- `0–1 条/立面` 是由 66/68 外推的成本估算，属于作者判断。
- `6925` 是作者构造的反例输入，属于判断性示例。
- “中点”虽然没写阿拉伯数字，隐含的 **1/2** 正是新增判断边界；不能以“数据自定义”把它归成无判断。

本裁决 §六给出独立机械扫描及逐类判定。

### N-2 · D4 把存储格点检查、链成员检查和“整数尺寸”混成了一件事

`grid_units`/`grid_units_from_mm` 只证明值在 0.1 mm 存储格点上；它不会证明该值属于某个 `cum_mm` 集合。实测 `grid_units_from_mm(6925)` 正常返回 `69250`，而 `6925` 不在 East `cum_mm`。施工设计必须明确为“两道精确检查”，不能用“即”连接。

此外，“合法区间宽度必是图纸整数”只是当前样本现象，不是定理；项目的 0.1 mm 表示本就允许小数毫米。真正能证明的是“宽度精确等于被引用尺寸段的整数域求和结果”，不保证十进制表面为整数。

## 五、五处专项的正面结论

### 5.1 D4 零阈值判据

- **成立部分：** 对“两个有序、同源、直接节点型边界”这个窄子域，前缀和恒等式成立，精确整数域检查不需要 epsilon。
- **总体判定：不成立。** 它不是全部一档的必要条件，也不是正确认领的充分条件；且失效条件没列全。至少新增“同节点塌缩”“反向节点”“合法链派生值非节点”三类。

### 5.2 D5-c 分流

- **判定：把判断从 D4 挤到了 D5。** 中点 = 相邻间距 1/2 的未签字相对阈值；“分界带”还欠带宽。
- **实证：** East `O01` 两边按该规则都唯一归 0，恰好打穿稿子自己声称的二档正例。

### 5.3 D6 冻结

- **方向正确：** separate validated carrier + 入口验 seal 是正确路线。
- **当前方案未成立：** 公共 re-finalize 能重签，构造能力没有结构性封闭，且 `tick_ref`/tier 仍可被替换。

### 5.4 D1 逐跳 file:line

**通过。** 我独立核了产物、适配器、契约类型、校验器、B4 裸 dict 消费及整数域配对，共超过四跳：

- 产物 `x_range_m` 存在；
- `adapt_as_drawn_elevation` 只构造 z refs；
- `ElevationOpeningClaimV1` docstring/字段明确无 x；
- validator 只重解引用 z；
- `synthesize_openings(elevation_doc: dict)` 经 `_elevation_openings` 读裸 x/z；
- 世界坐标由裸 x 进入 exact interval 配对；全仓生产面无调用者。

设计稿 D1 的行号和“x 无冻结溯源/档位、B4 连 z 也绕过 bundle、B4 尚未接线”三个结论均与当前树一致。

### 5.5 D7 风险清单

**旧风险识别有价值，当前清单不完整。** B2 返工 3 仅被一句排期带过，未读到它正在修的真 seal；T4-a 返工 2 完全缺失，且后者直接改本方案也要动的 `opening_synthesis.py`。

## 六、设计稿全部数字的独立机械清单与判定

### 6.1 分类口径

我用正则 `\d+(?:\.\d+)?(?:e[+-]?\d+)?` 扫描设计稿，得到 **135 个不同的阿拉伯数字 token**。同一 token 在不同上下文可有不同身份，以下按“出现语义”分类；源码行号/日期/版本号属于**声明性定位符**而非领域判据。另补扫了没有阿拉伯数字字面的“中点”，其隐含 1/2。

| 类别 | 全量数字 | 判定 |
|---|---|---|
| 已签字数值 | `0.1 mm`、`1 mm`、`10 mm`；`CodeToken 1..96` | **声明值**。前三个分别为存储表示、gt 分辨率、pipeline 出口；`1..96` 是既有代码类型约束，非本稿新阈值。 |
| 原料/实测/示例原值 | South：`0.0, 5000.0, 6930.0, 8730.0, 9450.0, 11250.0, 14750.0, 16550.0, 17270.0, 19070.0, 21300.0, 23100.0, 25000.0`；`6.9219, 8.7512, 6921.9, 8751.2, 6930, 8730, 1829.3, 1800, 8.1, 21.2, 936, 900`。East：`0.0, 6000.0, 6740.0, 7640.0, 0.5367, 2.1646, 536.7, 2164.6, 6000`。另有 `mm_per_px≈13.6`、`66/68`、离群 `2`、真实配对 `0`、闭合 `0.0`、设计 diff `281/91`、旧指南 `966` 行。 | **声明值/观察值**，不是本稿新判据。`0.0` 同时被既有精确闭合门消费；这是既有声明判据，不是容差。 |
| 已存在但未签成本稿判据的数 | `≤34 mm` | **判断值**。它是派工方/指南用于统计“靠近”的 cutoff；本稿没有把它作为生产阈值，所以不是“新引入”，但作者把它归成声明值不准确。 |
| 作者构造或外推 | `6925`；“两个节点均在 `1` 像素内”；`66/68 → 每立面 0–1 条`；“宽度全为整数”的普遍化 | **判断/示例**。`6925` 是反例，`1` 像素是假设条件，`0–1` 是成本估算；均非外部签字声明。 |
| 隐含新边界 | 相邻 tick 的“中点” = 间距 `1/2`；“等距分界带”宽度未给 | **作者判断**，且实际进入自动/惊动分支，因此违反“没有新判断阈值”的验收精神。 |
| 文档/任务/类型标识 | `T0`；`D1–D7` 及 `D2-a/b/c/d, D4-a/b/c, D5-a/b/c`；`R1–R5`；`T1–T5`；`B1/B2/B3/B4`、`B-1/B-2`；`F-2/F-130`；`V1/V3`；`O01`；`sm25`；`sha256`；模块 `2/3/4/5/6/7`；跳 `0–5`；证据档 `1/2`；数组下标 `0/1/2/3`；验收 `#2/#3/#4/#6/#7`；三问、三类、三条、五种 effect、四字段、两文件等计数 | **声明性标识/结构计数**，不是数值判据。注意同一个 token `1/2/...` 也可能在上一行“作者判断”中出现，须按上下文分。 |
| 日期/修订/commit 标识 | `2026-09-04`、`2026-09-03`、`2026-09-02`、`2026-09-01`、`2026-08-29`、`2026-08-28`、`2026-08-23`、`2026-08-22`、`09.04`、`e9a45226`（扫描 token `9/45226`）、`5804ae4b`（扫描 token `5804/4`） | **声明性身份**，不是判据。 |
| 旧指南章节 grep 的行号/日期片段 | `717, 776, 820, 866, 899`；日期片段 `2026, 08, 28, 01, 29, 02, 09, 04` | **声明性定位/日期**。 |
| 源码行号：`evidence_adapters.py` | `609, 662, 700–707, 704, 706, 821` | **声明性定位符**。 |
| 源码行号：`evidence_contract.py` | `418, 531, 544, 553–556, 558, 743, 760, 1118–1123, 1224, 1631–1658, 1660–1665` | **声明性定位符**。 |
| 源码行号：`opening_synthesis.py` | `56–68, 153–171, 166, 693, 713, 746, 748, 887, 894–901, 905–906, 914–935` | **声明性定位符**。 |
| 源码行号：`decision_schema.py` | `30–41, 36–40, 129, 131, 174, 192, 208, 356` | **声明性定位符**。 |
| 源码行号：`wall_compiler.py` | `119, 217, 296, 304–309, 313, 318` | **声明性定位符**。 |
| 其他源码/文档定位 | `multifloor.py:72–200`；`pipeline.py:1363–1364/1366–1367`；`evidence_contract.py:95–98`；指南/规范 `§8.5` | **声明性定位符**。 |

结论：设计稿出现的外部签字数值本身没有抄错；但“没有任何新阈值”的自证不成立，因为 D5-c 的中点是实际控制分支的未签字相对边界。作者自己的数字表也并非“每个数字”全量表。

### 6.2 机械扫描命令与原文输出

```text
$ python3 - <<'PY'
import re
from pathlib import Path
p=Path('AI_agent/logs/reviews/execution/2026-09-04u_tick_claim_design.md')
seen={}
for n,line in enumerate(p.read_text().splitlines(),1):
    for m in re.finditer(r'\d+(?:\.\d+)?(?:e[+-]?\d+)?', line, re.I):
        seen.setdefault(m.group(0), []).append(n)
for token, lines in seen.items():
    print(f'{token}\t{",".join(map(str,lines))}')
print('UNIQUE_COUNT',len(seen))
PY
0	1,62,62,63,100,101,107,165,243,247,280,337
2026	3,4,4,18,28,29,30,31,32,52,291,301,315,316,322,323,368,369
09	3,4,4,18,29,32,291,301,315,316,322,323,368,369
04	3,4,4,18,291,301,315,316,322,323,368,369
09.04	5,17
9	5,17,364,367
45226	5,17,364,367
2	6,8,25,64,69,75,76,82,87,93,96,110,114,114,129,138,138,143,145,154,164,171,171,173,173,191,192,221,242,244,270,290,291,291,298,298,300,301,303,306,307,307,316,316,316,316,316,316,316,316,317,321,323,323,323,333,333,334,336,338,340,350,370
1	6,8,38,56,62,63,63,64,69,69,72,74,92,94,96,99,101,102,103,103,107,114,117,119,125,126,132,159,162,165,169,177,177,182,182,183,183,184,185,190,190,193,195,196,196,198,205,220,237,259,261,263,266,268,268,280,287,291,294,294,299,299,306,315,315,315,316,317,318,322,323,335,336,339,340,355,373
4	8,66,66,70,74,76,80,81,83,136,156,164,165,165,166,167,167,212,214,227,234,246,274,287,315,315,315,315,317,317,317,317,317,317,317,318,321,322,322,322,327,335,336,337,350,355
966	24
3	25,46,65,69,75,81,144,159,160,161,168,177,198,234,247,266,303,306,316,316,317,337,339
717	28
08	28,30,31,52
28	28,30
776	29
01	29,39,40,48,49,140,143,144,147,150,151,242,271,333,334
820	30
866	31
29	31
899	32
02	32
68	38,232,259,264,280,338,356
6921.9	39,48,143,224,333,333
8751.2	39,48,333,333
6930	40,48,140,143,145,221,225,333
8730	40,48,140,144,145,221,333
1829.3	40,230
1800	40,145,221,230,333,333
536.7	40,41,49,150,152,243,334
2164.6	40,41,49,151,243,334
6000	41,147,243,334
0.0	41,47,49,49,152,249,334,337,337
25	46,52,62
5000.0	47
6930.0	47
8730.0	47
9450.0	47
11250.0	47
14750.0	47
16550.0	47
17270.0	47
19070.0	47
21300.0	47
23100.0	47
25000.0	47
6.9219	48,140
8.7512	48,140
8.1	48
21.2	48
6000.0	49
6740.0	49
7640.0	49
23	52
13.6	62,238,335
609	63
704	63
821	63
700	63,111
707	63,111
531	64,159
544	64,156,319
553	64
556	64
1631	65,106
1658	65,106
746	66
693	66
713	66,317
887	66,317
5	67,70,165,240,245,246,253,257,261,266,274,319,322,335,336,338,343,350
894	67
901	67
914	67,317
935	67
748	77
905	77
906	77
7	80,307,311,361,373
558	109
1660	110
1665	110
1118	112,318
1123	112
418	132
0.5367	147
2.1646	147
10	150,336
95	159
98	159
130	170
174	182
192	182
296	183
313	183
217	184
208	185
30	187
41	187
304	190
309	190
119	193
129	203
356	205
36	206
40	206
0.1	218,336
153	218
171	218
6925	228
936	230
900	230
56	232
166	232
662	249
66	259,264,280,338
318	261
6	285,316,316,316,321,350
256	294,295,296,315,315,315,322
760	295
1224	296
743	315
72	316,323
200	316,323
5804	317
8.5	319,319
1363	323,323
1364	323,323
1366	323
1367	323
96	339
131	339
34	354,356
281	368
91	369
UNIQUE_COUNT 135
```

## 七、核事实命令与原文输出

### 7.1 权威章节存在性

```text
$ rg -n '^#{1,6} .*十四|^#{1,6} .*十五|§十四|§十五' AI_agent/guides/reading_correction_split_guide.md
970:## 十四、⭐⭐⭐ 2026-09-04 用户拍板：**尺寸证据裁定 → 空间推理**（洞口对齐由此定位）
1117:## 十五、⭐⭐⭐ correction 目标态 · 完整表述（2026-09-04 用户点名要的那一份）
```

### 7.2 D1 独立逐跳 grep

```text
$ rg -n '"x_range_m"|"z_range_m"|"cum_mm"|"mm_per_px"' AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_south_as_drawn.json | head -n 20
59:      "cum_mm": [
91:      "mm_per_px": 13.550243440549048,
123:      "cum_mm": [
143:      "mm_per_px": 13.53634078133386,
159:    "mm_per_px": 13.543292,
390:      "x_range_m": [
394:      "z_range_m": [
456:      "x_range_m": [
460:      "z_range_m": [
522:      "x_range_m": [
526:      "z_range_m": [
588:      "x_range_m": [
592:      "z_range_m": [
654:      "x_range_m": [
658:      "z_range_m": [
720:      "x_range_m": [
724:      "z_range_m": [
786:      "x_range_m": [
790:      "z_range_m": [

$ rg -n 'def adapt_as_drawn_elevation|z_low_ref=_pointer|z_high_ref=_pointer|elevation_opening_claims=elev_openings' src/agent/correction/evidence_adapters.py
609:def adapt_as_drawn_elevation(
704:            z_low_ref=_pointer(input_id, contract, sha, f"{base}/z_range_m/0"),
706:            z_high_ref=_pointer(input_id, contract, sha, f"{base}/z_range_m/1"),
821:        elevation_opening_claims=elev_openings,

$ rg -n 'class ElevationOpeningClaimV1|horizontal extent|z_low_m:|z_low_ref:|z_high_m:|z_high_ref:' src/agent/correction/evidence_contract.py
531:class ElevationOpeningClaimV1(BaseModel):
544:    The horizontal extent (``x_range_m``) is deliberately NOT here: B4 owns
553:    z_low_m: float
554:    z_low_ref: ArtifactPointerV1
555:    z_high_m: float
556:    z_high_ref: ArtifactPointerV1

$ rg -n 'ELEVATION_Z_VALUE_DRIFTED_FROM_SOURCE|claim\.z_low_ref|claim\.z_high_ref|claim\.z_low_m|claim\.z_high_m' src/agent/correction/evidence_contract.py
1632:            (claim.z_low_m, claim.z_low_ref, "z_low"),
1633:            (claim.z_high_m, claim.z_high_ref, "z_high"),
1650:                    "ELEVATION_Z_VALUE_DRIFTED_FROM_SOURCE",

$ rg -n 'def _elevation_openings|for field in \("x_range_m", "z_range_m"\)|def synthesize_openings|for oid, x_lo, x_hi|world_lo = along_origin_u' src/agent/correction/opening_synthesis.py
693:def _elevation_openings(doc: dict) -> tuple[tuple[str, float, float, float, float], ...]:
713:        for field in ("x_range_m", "z_range_m"):
746:def synthesize_openings(
887:    for oid, x_lo, x_hi, z_lo, z_hi in _elevation_openings(elevation_doc):
899:        world_lo = along_origin_u + sign * lo_u

$ rg -n 'synthesize_openings\(' src scripts --glob '*.py'
src/agent/correction/opening_synthesis.py:746:def synthesize_openings(
```

### 7.3 D4/D5 活体计算

```text
$ python3 - <<'PY'
import json
from pathlib import Path
from src.agent.correction.opening_synthesis import grid_units_from_mm
base=Path('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out')
east=json.loads((base/'sm25_east_as_drawn.json').read_text())
o1=next(o for o in east['openings'] if o['id']=='O01')
ticks=east['calibration']['x']['cum_mm']
print('EAST_O01_X_MM', [x*1000 for x in o1['x_range_m']])
print('EAST_FIRST_TICKS_MM', ticks[:3])
for x in [v*1000 for v in o1['x_range_m']]:
    ranked=sorted((abs(x-t), t) for t in ticks)
    print('NEAREST', x, ranked[:2], 'UNIQUE_VORONOI_WINNER', ranked[0][1])
print('MIDPOINT_FIRST_INTERVAL_MM', (ticks[0]+ticks[1])/2)
print('GRID_6925', grid_units_from_mm(6925, what='probe'))
print('6925_IN_EAST_CUM', 6925 in ticks)
print('COLLAPSED_CLAIM_MEMBERS_PASS', 0 in ticks and 0 in ticks, 'WIDTH_MM', 0-0)
PY
EAST_O01_X_MM [536.6999999999999, 2164.6]
EAST_FIRST_TICKS_MM [0.0, 6000.0, 6740.0]
NEAREST 536.6999999999999 [(536.6999999999999, 0.0), (5463.3, 6000.0)] UNIQUE_VORONOI_WINNER 0.0
NEAREST 2164.6 [(2164.6, 0.0), (3835.4, 6000.0)] UNIQUE_VORONOI_WINNER 0.0
MIDPOINT_FIRST_INTERVAL_MM 3000.0
GRID_6925 69250
6925_IN_EAST_CUM False
COLLAPSED_CLAIM_MEMBERS_PASS True WIDTH_MM 0
```

### 7.4 D6 公共 re-finalize 面

```text
$ rg -n '^_CFG|def finalize_bundle|__all__|finalize_bundle' src/agent/correction/evidence_contract.py | head -n 40
170:_CFG = ConfigDict(extra="forbid", strict=True)
622:    ``content_sha256`` is computed by :func:`finalize_bundle` over the
760:def finalize_bundle(
1977:__all__ = [
2007:    "finalize_bundle",
```

### 7.5 当前两条在飞线

```text
$ rg -n 'B2 返工 3|multifloor.py|T4-a 返工 2|opening_synthesis.py|成功解析输入集合' AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md AI_agent/logs/reviews/request/2026-09-04x_T4a_rework2.md
AI_agent/logs/reviews/request/2026-09-04x_T4a_rework2.md:1:# 派工单 · **T4-a 返工 2**：锁**成功解析输入的集合**，⛔ 不是锁「像不像活键」
AI_agent/logs/reviews/request/2026-09-04x_T4a_rework2.md:39:> （`opening_synthesis.py:338-365, 513-524`）——
AI_agent/logs/reviews/request/2026-09-04x_T4a_rework2.md:57:| **R1** ⭐⭐⭐ | **锁住「成功解析输入集合 == live key 集合」这个性质本身**。⭐ 形式你定（结构 / 行为 / 类型皆可），但必须能在**复核方那个反例**（seam 外挂与活键无字面相似的兼容映射）下**变红**，且**不依赖枚举输入**|
AI_agent/logs/reviews/request/2026-09-04x_T4a_rework2.md:78:| **1** ⭐⭐⭐ | **「成功解析输入集合 == live key 集合」这个性质有锁** | §二#1 复现 + §二#2 两条自设扩法，全部变红；⛔ 且锁的断言里不出现任何具体扩法名字 |
AI_agent/logs/reviews/request/2026-09-04x_T4a_rework2.md:95:⛔ 碰 `src/agent/correction/multifloor.py`（**B2 返工 3 正在 GLM 席上跑，会撞**）·
AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md:1:# 派工单 · **B2 返工 3**：`ValidatedFloorLadder` 的**构造能力**必须不可公开获得
AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md:26:src/agent/correction/multifloor.py:184  @dataclass(frozen=True, eq=False)
AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md:27:src/agent/correction/multifloor.py:185  class ValidatedFloorLadder:      ← 公开导出（:462 在 __all__ 里）
AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md:28:src/agent/correction/multifloor.py:197      _levels: tuple[_DerivedFloorLevel, ...]   ← 公开构造器直接收
AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md:29:src/agent/correction/multifloor.py:356      if not isinstance(ladder, ValidatedFloorLadder):  ← 只查最外层
AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md:30:src/agent/correction/multifloor.py:384-417  直接读 level.z_floor_m / level.ceiling_height_m
AI_agent/logs/reviews/request/2026-09-04w_B2_rework3.md:111:⛔ 碰 `src/agent/correction/evidence_contract.py` / `opening_synthesis.py` / `evidence_adapters.py`
```

## 八、未复现项清单

1. **未跑任何测试**：本单是纯 Markdown 设计复核，任务明确无需跑测。
2. **未重量全部 68 条立面边**：只读取 South/East 原料并对 East `O01` 做 D5 中点/最近邻反证；未独立重算“66/68、≤34 mm”整批统计。
3. **未复现作者工作树的 commit/diff 统计**：当前工作目录是派工方提供的 detached 树；作者文末 `e9a45226..HEAD` 的 `281/91` 行统计只作为其自报，不作为本裁决依据。
4. **未运行 B2 返工 3 或 T4-a 返工 2 的在飞实现**：当前树只有它们的派工单，没有把别的工作树/未合并代码拉进来；本裁决只核风险与改动面。
5. **未实现或执行 D2–D6 的拟议 schema**：它们是设计形态，不存在可运行实现；D4 的 2550/3450、同节点、反向节点属于构造性反例。
6. **未核第二步 §14.4 四分类的实现**：明确不在本单设计/复核范围。

## 九、是否改过项目文件

**没有改动任何既有项目文件，也没有改 `src/`、`tests/`、任务书或被审设计稿。仅新增本裁决 Markdown。**

写入前工作树已有：

```text
A  AI_agent/logs/reviews/execution/2026-09-04u_tick_claim_design.md
```

该文件是派工方预置/用户范围内的既有状态，我未触碰。

### 9.1 写入后状态原文

```text
$ git status --short
A  AI_agent/logs/reviews/execution/2026-09-04u_tick_claim_design.md
?? AI_agent/logs/reviews/verdict/2026-09-04y_tick_claim_design_crossreview_gpt.md
```
