# 执行档 · 刻度认领 · 设计稿 **返工 2**（累计式自包含 · 仍是设计稿 · ⛔ 零 `src/` 零 `tests/` 改动）

- **日期**：2026-09-05 · **施工方**：Claude 家族席位 · **审**：GPT 家族（上一轮裁决方）
- **派工单**：[`2026-09-05f_tick_claim_design_rework2`](../request/2026-09-05f_tick_claim_design_rework2.md)
- **上一轮裁决**：[`2026-09-05e`](../verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md)（**REWORK · 阻断 5 · 不阻断 4**）
- **被返工的稿**：[`2026-09-05a`](2026-09-05a_tick_claim_design_rework1.md)（480 行，⛔ 本稿不引用其正文，逐点重新论证）
- **原任务书**：[`2026-09-04u`](../request/2026-09-04u_tick_claim_design.md)
- **工作目录**：`/tmp/tick_rw2_claude` · **分支**：`wt/09.05f_tick_design_rw2` · **基点**：主线 `b4f0b348`
- **复核方独立证据**（已放进本树，本轮全部复跑，§五）：`AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/`

---

## 结论先行

五条阻断是**同一病族**：判据量的是【代理量】不是要守的那件事。本稿按病族给**两族解法**（让那条路在类型层不存在 / 出口全检），⛔ 不逐条打补丁：

1. **F-1**（最近邻自证）：证明**结构闭合本身不能证明建筑语义**——`_nearest()` 是全函数，对任何输入都返回一个结构上「看起来合法」的答案（本稿自设反例：真实 South 链内部、一个 700mm 处的假边，结构签名与真实 O01 一模一样）。**这是类型层不存在的问题**：把 `provenance=auto` 拆成显式的 `confidence: "structural_only"`（今天唯一可能值，因为 reading 还没有给出「像素确实落在刻度墨迹上」这个独立判断）；**出口全检**：契约新增强制——任何 `confidence="structural_only"` 的认领**必须**进入第二步整体把关（`WholeBuildingReviewV1` 消费的输入集**结构性地**必须囊括它，遗漏一条＝构造不出该输入对象），把「局部像样、全局有问题」的残余风险交给架构里本来就该管这类风险的机制（§15.3），不再假装局部能一次性判死。
2. **F-2**（数值当节点身份）：**硬事实**——今天 `calibration.x` 只冻结**主链**一条 `cum_mm`；非主链节点在冻结字节里**没有地址**。本稿用**已冻结的主链数组做值域成员检查**（`primary_indices` 非空）给出 6 条边各自的具名出口：**降二档 + 挂 `EvidenceDebtV1`（`kind="other_known_missing"`）**，⛔ 不是「没有刻度」的二档，是「有刻度但今天的产物冻不住它的地址」的**另一种、显式记账的**二档。跨链「同指」不能从扁平表核实的问题，用同一个锚点（成员检查落在**唯一**被冻结的权威数组上）同构解决。
3. **F-3**：前置门只验总长闭合，不验逐节点前缀和——**这是两件事**。本稿新增一道**独立于** `_require_chain_closed` 的前缀和精确检查（⛔ 不改现有函数），写清楚「验过什么、没验什么、没验的部分谁来兜底」。
4. **F-4**：四个子项全部改成**签名化**（角色/基数/方向/坐标系 + operand 证据档位不可降级传播），每种情况给具名出口，不再让「能复算」冒充「有资格」。
5. **F-5**：撤回上一稿「模块私有令牌 + 逐元素受封」的三件套描述——**B2 返工 3 实际交出的范式是另一种**（闭包持牌，不是模块属性；载体**零携带状态**，不是「逐元素受封」；每次读取从冻结字节重新推导）。本稿改为**如实复用这个已验证有效的范式**，并补上 `rule_id`/`action_id` 拆分、`AutoActionV1.kind` 补项。

4 条不阻断照办：N-1 数字自查重做、N-2 D7 按 `b4f0b348` 全节重写、N-3 给②b/③具名边界出口（不建机制）、N-4 收窄三处论证过头但保留已成立的免疫结论。

---

## 〇、开工自证

```text
$ pwd && git rev-parse HEAD && git branch --show-current && git status --porcelain
/tmp/tick_rw2_claude
b4f0b3483bfdb420fbf3dd2d53b3a732150218f4
wt/09.05f_tick_design_rw2
?? AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/
?? AI_agent/logs/reviews/request/2026-09-05f_tick_claim_design_rework2.md
?? AI_agent/logs/reviews/verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md
```

**基点即 `b4f0b348`**（派工单点名的主线 HEAD），本树含 T4-a 已合并的代码与 §十四/§十五 全文——不存在上一次「建树基点早于口径」的问题。

**五份材料我逐字读完**：派工单（§一）· 上一轮裁决（§二）· 被返工稿 `2026-09-05a`（§三，480 行全文）· 指南 §十四（:970 起）/ §十五（:1117 起）全文 · 原任务书 `2026-09-04u`。核过存在性：

```text
$ grep -n "^## 十四\|^## 十五" AI_agent/guides/reading_correction_split_guide.md
970:## 十四、⭐⭐⭐ 2026-09-04 用户拍板：尺寸证据裁定 → 空间推理（洞口对齐由此定位）
1117:## 十五、⭐⭐⭐ correction 目标态 · 完整表述（2026-09-04 用户点名要的那一份）
```

复核方证据目录也已确认存在且**本轮全部复跑**（§五.1）：

```text
$ ls AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/
README.md  arithmetic.txt  capture_evidence.py  counterexamples.txt  evidence.md  numbers.txt  probe.py  statistics.txt
```

**B 层**：无。**未触发 A 层**——五条建议方向逐条论证下来都能落地为具体契约改动（§三），六条禁令未动。

---

## 一、病族的两族解法怎么落在每一条上（先给全局映射，避免逐条打补丁）

| # | 代理量 vs 要守的性质 | 类型层不存在 | 出口全检 |
|---|---|---|---|
| F-1 | 「结构闭合」≠「像素确实落在这个刻度上」 | `AutoProvenanceV1.confidence` 显式区分 `structural_only` / 未来的 `reading_confirmed`，今天只有前者可构造 | `structural_only` 认领**结构性地必须**进入第二步整体把关的输入集 |
| F-2 | 「数值相等」≠「节点身份」；「扁平表」≠「多链证据」 | `node_ref` 只能指向**唯一被冻结**的 `/calibration/x/cum_mm`，非主链值**在类型层构造不出** `ChainNodeValueV1` | 6 条边 + 跨链 MULTI 的「同指」主张统一走**同一个**值域成员检查，查不到即降档，⛔ 没有第二条判据 |
| F-3 | 「总长闭合」≠「逐节点前缀和」 | 新增独立前缀和检查作为 `node_ref`/`chain_derived` 构造的前置条件（类型构造函数里的守卫，不是事后校验） | —（前置错误直接堵死构造，不存在「构造出来再靠出口拦」的路） |
| F-4 | 「能复算」≠「操作数有资格/方向唯一/属于本图」 | `ChainDerivedValueV1` 的 `direction`/`operand.evidence_tier`/`operand.role` 全部收进类型字段，非法组合构造不出 | operand 证据档位**不可降级传播**在装配处强制核验（任何 operand 是 `pixel_only` 时整条 claim 强制降档，不是留白） |
| F-5 | 「哈希/公开构造器缺失」≠「授权令牌」；「携带值」≠「已冻结值」 | 闭包持牌（构造能力不存在于任何可 introspect 的公开名字空间）+ 载体**零携带状态**（没有值可换） | 每次读取都从冻结字节重新推导（出口全检：不是防「造出坏东西」，是防「读出坏东西」）|

---

## 二、⭐⭐⭐ F-2 先处理（派工单点名优先级）

### 二.1 硬事实复核：6 条边今天确实构造不出 `node_ref`

**独立命令**（我重跑，§五.1 有全部四条探针的逐字复现）：

```text
$ rg -n 'primary_indices=\[\]' AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/statistics.txt
4:  O02:x0 1CHAIN-CONSEC refs=['C_bot_fine_s2', 'C_bot_fine_s3'] px=1013.5 mapped_mm=8640.0 chain_values={'C_bot_fine:boundary2': Decimal('8640')} primary_indices=[]
5:  O02:x1 1CHAIN-CONSEC refs=['C_bot_fine_s3', 'C_bot_fine_s4'] px=1309.0 mapped_mm=12640.0 chain_values={'C_bot_fine:boundary3': Decimal('12640')} primary_indices=[]
8:  O04:x0 1CHAIN-CONSEC refs=['C_bot_fine_s4', 'C_bot_fine_s5'] px=1362.5 mapped_mm=13360.0 chain_values={'C_bot_fine:boundary4': Decimal('13360')} primary_indices=[]
9:  O04:x1 1CHAIN-CONSEC refs=['C_bot_fine_s5', 'C_bot_fine_s6'] px=1657.5 mapped_mm=17360.0 chain_values={'C_bot_fine:boundary5': Decimal('17360')} primary_indices=[]
72:  O05:x0 1CHAIN-CONSEC refs=['C_top_fine_s4', 'C_top_fine_s5'] px=1595.5 mapped_mm=14540.0 chain_values={'C_top_fine:boundary4': Decimal('14540')} primary_indices=[]
73:  O05:x1 1CHAIN-CONSEC refs=['C_top_fine_s5', 'C_top_fine_s6'] px=1683.5 mapped_mm=15740.0 chain_values={'C_top_fine:boundary5': Decimal('15740')} primary_indices=[]
```

前四行 South、后二行 West。**我自己核实了根因**（不是转引复核方的结论）——直接读实际冻结产物：

```text
$ python3 -c "
import json
d = json.loads(open('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_south_as_drawn.json').read())
print(list(d['calibration']['x'].keys()))
print(d['calibration']['x']['cum_mm'])
"
['axis', 'values_mm', 'cum_mm', 'matched_px', 'unmatched_ticks_px', 'origin_px', 'mm_per_px',
 'residual_px', 'rmse_px', 'max_abs_residual_px', 'chain_closure_mm', 'overall_mm', 'm_per_px']
[0.0, 5000.0, 6930.0, 8730.0, 9450.0, 11250.0, 14750.0, 16550.0, 17270.0, 19070.0, 21300.0, 23100.0, 25000.0]
```

**结论**：`calibration.x` 是**单数**（不是按链名分组的字典），只装得下**一条**链的 `cum_mm`——南立面的 `C_bot_fine`（O02/O04 引用的链）**根本没有自己的 `/calibration/...` 路径**，它的节点值**只活在** `tools/cfg_south.json`（一份不属于冻结产物契约的、reading 工具的**输入配置文件**）里。⇒ **不是 D2 的 schema 设计选错了指针形状——是今天的冻结产物本身缺这块地址空间**，任何 `ArtifactPointerV1.json_pointer` 写法都指不到不存在的路径。

**另一个附带事实我也验证了**：`calibration.x` 不仅是单数，连**自己是哪条链**都不自报——键里没有 `chain_id`/`primary_chain_name` 字段。这意味着即便有人想「按链名核对」，也没有冻结字节可核；`calibration.x` 的权威性来自它是**这个字段位置唯一的一份**，不是来自「它自称是 C_top_fine」。

### 二.2 具名出口（6 条边 + 跨链 MULTI 的「同指」问题，统一解）

**唯一可信的锚点**：`calibration.x.cum_mm`——这是**今天冻结产物里唯一**的、经 `_require_chain_closed`（`evidence_adapters.py:569`）验过闭合的权威 x 值数组。⇒ **检查①（D4-a 的一部分，本轮改写见 D4）改为对这一个数组做精确值域成员检查**：

```
CHAIN_NODE_VALUE_AUTHORITY_CHECK(claimed_mm) :=
    ∃ k : Decimal(calibration.x.cum_mm[k]) == Decimal(claimed_mm)
```

- **通过** ⇒ `node_ref = ArtifactPointerV1(..., json_pointer=f"/calibration/x/cum_mm/{k}")`，可以构造 `ChainNodeValueV1`——**不管 `dimension_refs` 字面上引用的是哪条链的段名**。这不是走后门：`calibration.x` 是这张立面**唯一**的权威 x 记录，任何数值只要精确出现在这个数组里，就是这张立面在这个位置**已经声明过**的一档事实；`dimension_refs` 只是**辅助的、不承重的**指认线索（帮模型/人理解「像素落在哪些段名附近」），⛔ 不再是认领合法性的唯一依据。
- **不通过**（6 条边正是这个分支）⇒ **不构造 `ChainNodeValueV1`，也不构造 `ChainDerivedValueV1`**（因为它们的值不来自主链的任何封闭运算——我核过：`8640` 不是 South 主链 `[0,5000,6930,8730,...]` 中任何两点的和/差的整数倍关系能自然给出的值，`chain_derived` 硬套上去是编造）⇒ **降二档**（`tier="pixel_only"`），**但这是一种与「无刻度可指认」结构不同的二档**——这条边**明明有** `dimension_refs`（非空、结构闭合），只是它引用的链在今天的冻结产物里没有地址。⇒ **挂一条 `EvidenceDebtV1`**（复用既有闭域 `kind="other_known_missing"`，`evidence_contract.py:518-524`，⛔ 不新增枚举值）：

```
EvidenceDebtV1(
    debt_id=<edge_id 派生>,
    kind="other_known_missing",
    affected_refs=(edge 的 evidence_ref,),
    description="edge 的 dimension_refs 指向的链在当前 calibration.x 之外没有冻结地址；"
                "该链的节点值只存在于 reading 工具的输入配置（非产物契约的一部分）；"
                "读法产物需要为非主链新增可寻址的冻结记录后才能升档",
    obligation=None,
)
```

这份债**不是「未来施工方随便找理由消掉」的空话**——它点名了**具体缺什么**（非主链的冻结地址空间）、**为什么现在做不到**（今天的 schema 只留了一份主链槽位）、**升档条件是什么**（reading 产物扩展 `calibration.x` 为可按链寻址的结构，例如 `calibration.x.chains.<chain_id>.cum_mm`）。这份债本身**就是**具名出口——它比「静默降二档」多出的东西是：**可审计、可统计、指向明确升级路径**。

### 二.3 跨链 MULTI「同指」不能只从扁平表核实——同一个锚点解决

复核方 `RASTER_COLLISION` 反例证明：`as_drawn_elev.py:90-91`（`tick_map[world][str(round(px,1))] = ...`）是**逐键覆写**，两条链共享一个像素键时后写的赢，先写的**信息丢失、且丢失本身不可见**。⇒ **任何声称「MULTI 的两条链指同一个 N」的判断，只要依据是这张扁平表本身，就是在拿一个可能已经丢过信息的表去证明自己没丢信息**——同 F-2 病根。

**我自己的反例**（§五.2 Counterexample B，不是复核方那条）证明：**同一个锚点检查天然筛掉了这个风险**——不需要另外发明「跨链一致性」判据：

```text
MULTI_SIGNATURE_DESPITE_DISAGREEMENT MULTI
P_WINS: flat_map_value=4000 primary_indices_nonempty=True
Q_WINS: flat_map_value=4050 primary_indices_nonempty=False
```

两条链（主链 P：`[0,4000,9000]`；非主链 Q：独立拟合得到 `4050`，真实相差 50mm）在扁平表里共享一个像素键，谁写谁读全靠字典写入顺序——**但**无论最终扁平表报的是 `4000` 还是 `4050`，二.2 的成员检查只对**主链数组**做精确匹配：`4000` 通过（它就是主链自己的节点，MULTI 的另一条链只是**恰好**也在同一物理位置画了刻度，这在建筑图纸上完全合理——两条尺寸线标注同一个真实边），`4050` 不通过（它不是主链任何节点，即便扁平表因为覆写而报告了它，也只会正确地掉进 §二.2 的「降二档 + 挂债」分支，不会被误当成一档事实）。**⇒ 「多链同指」问题不需要单独判据——它被「只信一个冻结锚点」这个决定自动吸收：能通过锚点检查的，就是这张立面已经声明的事实，不管有几条链凑巧指向它；不能通过的，不管扁平表报的是哪个数，都进不了一档。**

---

## 三、逐条阻断（F-1 ~ F-5）

### F-1 · 结构闭合不能自证建筑语义

**现象复述**：上一稿 D5 用「`dimension_refs` 角色闭合到唯一链节点」作为自动一档的判据，而这个「角色闭合」本身是从**同一次** `_nearest()` 调用的输出里读出来的——`_nearest()` 是全函数（`as_drawn_elev.py:63-67`：`min(ticks, key=lambda v: abs(v-px))`），对**任何**输入 px 都会返回**某个**看起来结构合法的最近刻度，无论这个刻度离 px 有多远。

**我自己的证明**（不是复核方给的反例，用**真实**南立面链、一个此前没人碰过的位置）：

```text
$ python3 .../my_counterexamples.py
SOUTH_CUM [0.0, 5000.0, 6930.0, 8730.0, 9450.0, 11250.0, 14750.0, 16550.0, 17270.0, 19070.0, 21300.0, 23100.0, 25000.0]
REAL_SEGMENT_INTERIOR_PROBE lo=17270.0 hi=19070.0 fake_raw_mm=17970.0 nearest_tick=17270.0 distance_mm=700.0
PICKED_NODE_INDEX=8 IS_INTERIOR_NODE(1CHAIN-CONSEC-ELIGIBLE)=True
OLD_RULE(rework1 D5-a)=AUTO_ONE value_mm=17270.0  <-- silently finalized, 700mm away from true (fabricated) edge
CHECK_F2_STYLE(value in cum_mm)= True  <-- membership check alone does NOT catch this
```

South 主链真实存在一段**1800mm、今天没有任何开口的干净段**（索引 8→9，`17270→19070`）。我在这段内部虚构一条「假边」，其原始像素换算值是 `17970`（离低端 700mm，离高端 1100mm，二者都远超真实数据里 66 条边的最大距离 `34mm`）。`_nearest()` 依旧诚实地返回 `17270`（这是真实的链节点，两侧段名俱全，**结构签名与真实 South O01 完全一样**：`1CHAIN-CONSEC`）。⇒ **上一稿 D5-a 会把这条假边自动认成一档、值 `17270`，无声无息、没有任何字段能事后区分它和一条真边。**

**且我验证了：这不能被 F-2 的修法顺带治好**——`17270` 本来就是主链自己的真实节点（`in cum_mm == True`），F-2 的锚点检查在这里**帮不上忙**。**F-1 与 F-2 是正交的两种缺陷**，这是本轮新确认的一条事实（上一稿曾暗示两者可以合并处理，是错的）。

**病根一句**：`_nearest()` 只回答「哪个刻度离我最近」，从不回答「我离最近的刻度够不够近到可以说『就是它』」——而回答后一个问题需要一个与「哪个最近」**正交**的独立事实源，光靠再摆弄距离/结构这两样从同一次调用里拿到的东西，摆不出这个事实源。

**为什么不能再加一个「更聪明的结构判据」**：我系统地试过（穷尽过程）——
1. 「宽度自洽」（认领区间的声明长度必须等于测量宽度）：对**声明侧**数字（cum 差值恰好等于某段声明长度）永远成立，因为链的前缀和定义本身保证任意两节点之差就是中间段的和，不区分「真边」与「假边」；只有拿**测量侧**宽度去比对才有信息量，但那立刻退化成「差多少毫米算够近」——正是被禁止的毫米阈值。
2. 「同一开口两条边独立判断，互相校验」：假边的 x0/x1 两侧独立算出的宽度确实会与真实宽度不同（本例中 `250` vs 声明 `500`——见复核方 `UNLABELLED_MIDDLE_INTERVAL` 反例），但判断「差多少算不一致」同样是毫米阈值。
3. 「要求 `distance_mm` 恰好为 0」：真实数据里没有一条边的 `distance_mm` 精确为 0（南立面 O01 是 6.8/20.3mm，全部来自图像检测噪声），这条规则会让 66/68 全部改判模型，与已验证的「省钱」现象矛盾，且仍然是一个阈值（只是阈值取到了 0）。

**⇒ 结论**：在**今天的证据字段**（`measured_px`/`nearest_tick_px`/`dimension_refs`/`distance_mm`，全部来自同一次 `_nearest()` 调用）范围内，**不存在**一个零阈值、纯结构的判据能把「真边」和「假边」分开——这是这批证据字段的**信息论极限**，不是没想到聪明写法。

**类型层修法（让「自动一档=已证实」这条路不存在）**：

```
AutoProvenanceV1:
    decided_by: Literal["auto"]
    auto_action_id: str            # AutoActionV1 的 action_id（本次具体动作实例，闭合 F-5 的字段拆分）
    auto_rule_id:   str            # AutoActionV1 的 rule_id（规则本身）
    confidence: Literal["structural_only"]
    #  ⭐ 今天唯一合法值。"reading_confirmed"（reading 独立断言像素确实落在刻度墨迹/引出线上，
    #  一个与 nearest() 正交的事实源）不存在于当前 reading 契约里——不在本稿臆造，
    #  作为显式的上游依赖登记在 D7。这条字段存在的意义是让「今天的自动认领只有结构证据、
    #  没有独立坐标证据」这个事实，从『读代码才知道』变成『类型上写明』。
```

**出口全检修法**：`confidence == "structural_only"` 的认领**结构性地**必须进入第二步整体把关（§15.3 步骤②b「总体把控」）的输入集——这不是纪律，是构造约束：

```
WholeBuildingOpeningReviewInputV1:
    # 第二步整体把关拿到的输入之一，⛔ 不是可选项
    structural_only_tick_claims: tuple[OpeningEdgeTickClaimV1, ...]
    #  不变量：bundle 里每一条 provenance.confidence == "structural_only" 的
    #  OpeningEdgeTickClaimV1，必须原样出现在这个元组里——构造函数机械遍历
    #  bundle 生成这个元组（同 evidence_contract.py:1127 _payload_row_source_ids
    #  「加成员不教函数在哪儿找它就响亮拒绝」的同一种写法），遗漏一条 = 装配函数
    #  本身构造不出合法的 WholeBuildingOpeningReviewInputV1（字段与来源之间没有
    #  「手写映射表」可以漏项，只有「遍历」可以完整）。
```

**这closes 的是什么、不 close 的是什么，必须说清楚**：这**不能**保证模型一定会抓出每一条错误认领（模型判断本来就没有 100% 保证，同 §15.3 本身接受的风险模型——「任何确定性检查都抓不到；只有做总体把控的模型会看出」这句话本来就承认这类风险交给模型、不交给确定性判据）。它 close 的是：**「一条局部像样、全局有问题的认领永远不会被任何后续步骤看见」这条路不再存在**——从「模型判断可能不完美」退化到「模型判断的输入集本身就不完整」，是两种不同严重程度的风险，本修法只处理第二种（也是唯一能在类型层处理的那种）。

**我的两条自设反例在新规则下的行为**：
- `REAL_SEGMENT_INTERIOR_PROBE`（假边）：`confidence="structural_only"` ⇒ 强制进入 `structural_only_tick_claims`，第二步模型审查这条边时能看到「这条边认成了 17270mm，且没有独立坐标证据佐证」，可以质疑（旧规则下：这条边永远不会被任何后续步骤看到，因为它被当作「自动、已完成」直接落地）。
- 真实 South O01：同样 `confidence="structural_only"`（因为今天没有任何边有 `reading_confirmed` 证据），同样进整体把关——**代价是所有 66 条边现在都显式进入第二步的审查范围**，不再是「悄悄自动完成」。这是**诚实的代价**：上一稿「66/68 自动、省钱」的叙事本身建立在「结构闭合=已证实」这个不成立的假设上；本稿把「自动」的含义改写为「代码先给出一个高置信度候选，仍需第二步过目」，⛔ 不再是「代码独立终局裁决」。

### F-2 · 已在 §二 处理

见 §二 全节：6 条边具名降二档 + 挂 `EvidenceDebtV1`；跨链 MULTI「同指」用同一锚点解决，不需要单独判据。

**补一处 F-2 原文点名但 §二 未覆盖的旁支**：East `O01` 的 `ALL_S1` 签名（真实二档，无刻度可指认）与本节的「有刻度但地址缺失」是**两种不同原因的二档**——两者在 `tier` 枚举上目前都落在 `pixel_only`，这是**有意的**：`tier` 只回答「这个值能不能被链权威支撑」，不回答「为什么不能」；「为什么不能」的区分靠 `PixelOutV1`（无 debt）vs `PixelOutV1` + 附挂的 `EvidenceDebtV1`（有 debt）来体现，⛔ 不在 `tier` 上加第三个值——加第三个值意味着以后每处消费 `tier` 的代码都要多处理一支，而下游（B4 配对/输出）真正关心的只是「这个坐标能不能信到一档权威」，不关心「不能信的原因是没画还是画了地址不够」，这个区分只有**债务台账**的读者（人工排期）需要看见。

### F-3 · 「总长闭合」≠「逐节点前缀和」

**我自己核实的现有函数行为**（`evidence_adapters.py:569-611`，读全文，不是转引）：

```python
total = sum(values)
if total != cum[-1] or cum[-1] != overall:
    raise EvidenceContractError("CALIBRATION_CHAIN_NOT_CLOSED", ...)
```

这段代码**只**检查：`values` 非空且全数值 · `sum(values) == cum[-1] == overall`。它**从未**读取 `values[i]` 与 `cum[i]-cum[i-1]` 的关系——`cum` 数组的中间元素**完全不参与**这道门的任何比较。⇒ 复核方 `INTERIOR_CUM_CHANGED`（把 South `cum[2]` 从 `6930` 改成 `7000`，`PASS`）与 `DUPLICATE_NODE_VALUE`（把 `cum[2]` 改成等于 `cum[1]`，`PASS`）两条反例精确命中这个空白，我本轮重跑确认（§五.1，逐字相同）。

**谁验证了什么、验不过交给谁（本节的正面回答）**：

| 事实 | 谁验证 | 验不过时 |
|---|---|---|
| 链总长闭合（`sum(values)==cum[-1]==overall`）| 既有 `_require_chain_closed`（`evidence_adapters.py:569`，⛔ 本稿不改） | `EvidenceContractError("CALIBRATION_CHAIN_NOT_CLOSED")`，整条链的任何认领全部拒绝构造 |
| **逐节点前缀和**（`cum[i] == cum[i-1] + values[i-1]` 对所有 `i`，精确整数域比较）| **新增、独立的**前置检查 `_require_chain_prefix_consistent`（本稿只给规格，不写实现，⛔ 改动 `evidence_adapters.py` 属另一张施工单）| 同一错误族：`EvidenceContractError("CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM")`，整条链的任何 `node_ref`/`chain_derived` 认领全部拒绝构造——**在构造函数的守卫里堵死，不是先构造出来再指望某个下游校验器发现** |
| 「这条边该认哪个节点」（是否为**真边**而非假边，F-1 的问题）| **不在本层验证** | 交给 D5 的结构候选 + 强制进入第二步整体把关（F-1 修法）|
| 原始像素测量本身的精度 | **不在本层验证** | reading 自己的置信度域（`confidence: high/medium/low`，`reading/schema.py:51`），本稿不重新发明 |

**两条新前置检查的关系**（不是「即」，是并列且独立）：`_require_chain_closed` 验总量，`_require_chain_prefix_consistent` 验逐点——一条链必须**同时**通过两道门才能承载任何认领；两道门任何一道失败都是**同一族**的整链拒绝（不是把「链坏了多严重」分级处理，那属于领域判断，超出本设计范围）。

**穷尽过的无效解**（写清楚为什么不选它们）：
- 「只加一道 `sum(diffs)==total` 检查」：等价于当前 `_require_chain_closed` 已经在做的事，不会命中 `INTERIOR_CUM_CHANGED`（那条反例改的是**中间点**，不改总量），无效。
- 「把两道检查合并成一次遍历」：语义上仍是两件独立的事（一个关心整体、一个关心逐点），合并只省一次循环，不改变判据本身——本稿不为了省一次循环把两个独立不变量焊在一起（那正是 N-2 点名过的「用『即』混成一件事」的病，在这里没有重犯的必要）。

### F-4 · 「能复算」不能替代「有资格 / 方向唯一 / 属于本图」

四个子项逐一签名化：

**① 方向不由 lo/hi 唯一决定**：`axis_plus_half_wall` 不再靠「符号由边角色 lo/hi 定」隐式决定——直接把方向做成**显式枚举字段**，且要求代码在**歧义时**（两墙内侧洞口的例子：轴线 `4000/8000`、墙厚 `200`，正确边应为 `4100/7900`，而「lo 减 hi 加」的固定解释会得到 `3900/8100`）**枚举两个候选**交给模型，⛔ 不由代码替模型决定方向：

```
ChainDerivedValueV1:
    value_source: Literal["axis_plus_half_wall", "segment_span_diff", "segment_span_sum"]
    direction: Literal["toward_positive", "toward_negative"] | None
    #  仅 axis_plus_half_wall 需要；segment_span_diff/sum 无方向歧义（差/和的符号
    #  由 operands 的角色 cum_lo/cum_hi 天然决定，⛔ 不需要额外字段）。
    #  方向不能由 lo/hi 边角色自动推断——D3 的候选生成阶段，遇到轴线两侧都可能是
    #  合法解释时（洞口在两片墙体之间），代码必须把两个方向**都**列成独立候选
    #  （TickCandidateV1 各开一条），由模型依据它能看到的空间上下文（这条边到底
    #  在墙的内侧还是外侧）选择，⛔ 不能让代码替它选一个默认方向。
    operands: tuple[DerivedOperandV1, ...]
    recompute_cert_units: int
```

**② 墙厚 ref 全厚/半厚不一致**：`DerivedOperandV1.role="half_wall_thickness"` 必须显式声明来源，不允许静默做除二：

```
DerivedOperandV1:
    role: Literal["axis", "half_wall_thickness", "cum_lo", "cum_hi", "segment_len"]
    ref:  ArtifactPointerV1
    derivation: Literal["declared_as_half", "half_of_declared_full"] | None
    #  仅 role == "half_wall_thickness" 需要。"half_of_declared_full" 时，
    #  recompute_cert_units 的重算必须显式做 full_units // 2 且要求
    #  full_units % 2 == 0（0.1mm 整数格点上必须能整除，否则
    #  WALL_THICKNESS_HALF_UNGRID 具名拒绝，⛔ 不悄悄四舍五入）。
```

复核方反例 `OPERAND_TIER`（轴线一档、半墙厚 `115` 来自二档测量，`evidence_tier_gate=UNSPECIFIED`）指出的其实是**第③点**（见下），这里先说明方向/半厚字段本身必须显式，不是本条反例的核心。

**③ 证据档位不可降级传播（`OPERAND_TIER` 反例的真正修法）**：一个 `pixel_only`（二档）的量，不能作为 `operand.ref` 参与构造 `ChainDerivedValueV1`（一档）——否则一档的权威性就是编出来的：

```
硬不变量（ChainDerivedValueV1 的构造前置条件）：
    ∀ operand ∈ operands :
        operand.role == "axis" 或 "cum_lo" 或 "cum_hi" ⇒ operand.ref 必须解析到
            calibration.x.cum_mm 的某个索引（同 §二.2 的锚点检查）
        operand.role == "half_wall_thickness" ⇒ operand.ref 必须解析到一份
            **声明值**（图纸自己标注的墙厚 callout，非测量推断），
            ⛔ 不能是某处测得的、tier=pixel_only 的间距
        operand.role == "segment_len" ⇒ 同 cum_lo/cum_hi 的锚点检查
    任一 operand 不满足 ⇒ 整条 ChainDerivedValueV1 构造失败，
    该边退回 tier="pixel_only"（不是「部分相信」，是整体降档）
```

反例 `axis_mm=4200 half_wall_mm=115 wall_tier=pixel_only` 在新规则下：`half_wall_thickness` 的 `ref` 解析到的是一个二档测量值（不是声明墙厚）⇒ **构造 `ChainDerivedValueV1` 直接失败**，边整体退到 `pixel_only`，⛔ 不会出现「一档结果、二档 operand」这种自相矛盾的产物。

**④ 输入域不封闭（`segment_span_sum`/`diff` 的连续性 + 坐标系）**：

```
segment_span_diff 的合法性：cum_lo.ref 与 cum_hi.ref 必须解析到**同一条链**
    （同一个 calibration.x 数组，今天只有主链一份，天然满足），
    结果可正可负——⛔ 不强制非负；符号的**含义**（"在轴线之前/之后"）
    由消费方（D3 候选生成时的 direction 字段，见①）显式声明，本层不做裁剪。
    坐标系：结果始终是主链自己的坐标系（相对于该链 world_start_mm 的 x），
    与 operand 的 ref 天然共享同一个 source_ref.input_id（沿用既有的
    F-2 单源不变量，evidence_contract.py 现有的「同 input_id」检查同构复用）。

segment_span_sum 的合法性：segment_len 操作数必须是**连续**的段（索引相邻，
    ⛔ 不能跳段求和——跳段求和没有对应的物理意义，图纸不会画「第2段+第5段」
    这种量），连续性通过 operand 各自的 ref 索引在构造时机械核验
    （索引序列必须是 [i, i+1, i+2, ..., j]，缺一即拒绝构造）。
```

复核方 `NEGATIVE_DIFF`（`lo=-400, hi=100`）在这套规则下：负值本身合法（未强制非负），前提是这条边的 `direction`/消费语义已声明「允许跨轴线两侧」——这是**领域判断**（这张图上这个负值有没有意义），本层只保证**算术**正确，不代为裁定「负的对不对」，这条边和其余「结构闭合但语义存疑」的边一样，落进 F-1 的 `structural_only` 分支，交给第二步整体把关。

### F-5 · 真封印：撤回三件套，改用 B2 返工 3 实际验证过的范式

**我核实的事实**（上一稿的病根）：`multifloor.py` 今天**在主线树里不存在**——

```text
$ find src -iname "*multifloor*"
（无输出）
```

它只存在于 B2 返工 3 那条**尚未合并**的分支（`wt/09.04w_b2_rework3`）。**上一稿声称 B2 交出的是「模块私有令牌 + 逐元素受封」三件套，我读了 B2 返工 3 的实际交件文档，这个描述是错的：**

> [`2026-09-04w_B2_rework3_execution.md:41-56`](2026-09-04w_B2_rework3_execution.md)：
> 「(a) 真封印（入口）：`ValidatedFloorLadder` 的构造器要求出示一个**只存在于工厂函数闭包里**的令牌…⛔ 不是模块属性…(c) 不信任载体携带的值（出口全检）：载体**只存一个字段** `_artifact`——**不存在任何 z 携带状态**，「换元素」这个攻击类别没有了对象…`__len__`/`__iter__`/`__getitem__` 全部…**每次读取重新推导**」

这与「模块私有令牌」（仍是模块级名字空间里的东西，能被 `vars(module)` 找到）和「逐元素受封」（暗示载体里存着一组各自被封印的元素）**都不是同一件事**：真实范式是 **① 令牌活在闭包里，连模块属性都不是**（比「模块私有」更强一档——`hasattr(m, '_SEAL') == False`）；**② 载体压根不持有元素**，只持有对冻结产物的一个引用，「换元素」这个攻击类别**没有对象可换**；**③ 每次读取都重新从冻结字节推导**，不是「读一次验一次，验过了就信」。

**⇒ 本稿的 `SealedTickClaimsV1` 照这个已验证范式设计（不是抄一个目标句，是复刻一个已经跑过 7 条自设攻击路径全部拒绝的实证范式）**：

```
def _mint_sealed_tick_claims(bundle_artifact: CorrectionEvidenceBundleArtifactV1) -> "SealedTickClaimsV1":
    _SEAL = object()   # ⭐ 闭包局部变量，不是模块属性；模块外的任何名字空间都拿不到它

    class SealedTickClaimsV1:
        """第二步唯一合法消费入口。⛔ 无公开构造器：__init__ 要求出示 _SEAL，
        该名字只活在这个工厂函数的闭包里。⛔ 零携带状态：唯一字段是 _artifact
        （对冻结 bundle 的引用），没有任何 z/tick 值被 setattr 到实例上——
        『换元素』这个攻击类别没有对象。每次读取（__len__/__iter__/__getitem__）
        都重新跑 validate_evidence_bundle + 从冻结字节解析 tick 值，
        不存在『读一次、之后都信』的窗口。"""

        __slots__ = ("_artifact",)

        def __init__(self, artifact, seal):
            if seal is not _SEAL:
                raise EvidenceContractError("SEALED_TICK_CLAIMS_MINT_REQUIRED", {})
            object.__setattr__(self, "_artifact", artifact)

        def __init_subclass__(cls, **kwargs):
            raise EvidenceContractError("SEALED_TICK_CLAIMS_NO_SUBCLASS", {"subclass": cls.__name__})

        def _claims(self):
            validate_evidence_bundle(self._artifact.bundle, self._artifact.frozen_sources)  # 门在前
            return _derive_tick_claims_from_frozen_bytes(self._artifact)  # 纯函数，永远从冻结字节算

        def __len__(self):    return len(self._claims())
        def __iter__(self):   return iter(self._claims())
        def __getitem__(self, i): return self._claims()[i]

    return SealedTickClaimsV1(bundle_artifact, _SEAL)
```

**正反例覆盖**（照抄 B2 返工 3 §二#2 已实证的 7 条攻击形状，逐条对应到本类型上）：① 公开构造器直接调用 ⇒ `SEALED_TICK_CLAIMS_MINT_REQUIRED`（无 `_SEAL` 可出示）；② 拿到合法实例后 `object.__setattr__` 换 `_artifact` ⇒ 换了也没用，下次读取 `_claims()` 重新过门，漂移的冻结字节在 `validate_evidence_bundle` 处响亮拒绝；③ `object.__new__` 壳 ⇒ 没有 `_artifact` 属性，`_claims()` 访问 `self._artifact` 直接 `AttributeError`（具名度弱于 B2，这是**本稿要求施工时补一道**「载体缺 `_artifact` 时给具名错误而非裸异常」的验收项，非本设计的结构性缺口）；④ 子类化 ⇒ `__init_subclass__` 类创建时红；⑤ `dataclasses.replace` ⇒ 走 `__init__`，同①；⑥ 鸭子类型 `_artifact`（手填字节）⇒ `validate_evidence_bundle` 类型/内容全检，塞不进去。

**第二步消费**：`tuple(sealed_claims)` 在装配处**当次取值**，⛔ 不缓存成实例状态跨调用复用——与 B2 `levels = tuple(ladder)` 同款。

**`rule_id`/`action_id` 拆分**（闭合上一稿把两个字段压成一个 `auto_rule_id` 的问题，已在 F-1 的 `AutoProvenanceV1` 定义里给出：`auto_action_id` + `auto_rule_id` 两个独立字段，对应 `AutoActionV1` 自己的 `action_id`/`rule_id` 两个字段，`wall_compiler.py:324/333`）。

**`AutoActionV1.kind` 补项**：今天的 4 个枚举值（`wall_compiler.py:325-330`）全是墙语义，没有刻度认领的位置——本稿要求新增第 5 个字面量 `"claim_dimension_tick"`（⛔ 本稿只写规格，实际加这一行字面量属于施工单改 `src/agent/correction/wall_compiler.py` 的范围，不在本设计稿的零改动范围内执行，但**契约上必须点名**，否则 D5-a 产出的 `AutoActionV1` 无法自洽地声明自己的 `kind`）。

**B2 依赖声明**（⛔ 不代批，如实记录状态）：B2 返工 3**仍待审**（`multifloor.py` 不在主线）。本稿 D6 的封印范式是**独立于 B2 是否过审都成立的通用模式**（闭包令牌 + 零状态载体 + 出口重推导，不依赖 `multifloor.py` 的任何具体代码，只是**复用同一种设计范式**）——即使 B2 返工 3 被要求再改一轮，本稿引用的是**这个范式本身**，不是引用某一版具体实现的哈希或行号，风险因此有限；真正的施工顺序约束仍是 D7 的 R2（不与 B2 撞同一份文件）。

---

## 四、不阻断（N-1 ~ N-4）

### N-1 · 全量数字自查重做

**独立命令**（本轮重跑，输出与复核方逐字相同，§五.1）：

```text
$ python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py numbers
UNIQUE_COUNT 170
OCCURRENCE_COUNT 948
```

本稿是全新文本（行号、数字分布与上一稿不同），因此这份机械扫描必须在**本稿定稿后**对本稿自己重跑一遍（见 §五.1 的复跑记录——探针脚本读取的是**上一稿**路径 `2026-09-05a_tick_claim_design_rework1.md`，用于验证复核方证据可复现；本稿自己的数字自查见下表，逻辑与探针一致但目标文件是本稿）。

**分类判定**（沿用上一稿已验证正确的分类框架，`≤34mm` 与中点 `1/2` 两处旧错不复现——本稿的 D5 已经不含「相邻刻度中点」这个隐含阈值，`≤34mm` 全文只作为**已发生过的事实描述**——South/East 68 条边里 66 条落在这个距离内——⛔ **不作为任何分支的判据**，判据已改写为 §二.2 的值域成员检查 + F-1 的 `confidence` 分档）：

| 类别 | 代表数字 | 判定 |
|---|---|---|
| 已签字颗粒度 | `0.1mm`/`1mm`/`10mm` | 声明值（§十五终裁） |
| 结构/类型常量 | `Hex64`/四字段/五 effect | 声明性结构 |
| 原料/观测值 | South cum 数组、East `values_mm`、`mm_per_px≈13.6` | 图纸/产物声明或观测 |
| **本轮新增反例数字** | `700`（假边距离）、`17270/17970/19070`（真实链位置）、`4000/4050/9000`（自造两链）| **反例构造用数值**，⛔ 非判据 |
| **既有经验统计**（引用，非判据）| `66/68`、`≤34mm`、`535.8/2163.7` | 观测统计，⛔ D5-a 分支不再引用 `≤34mm` |
| 反例常量（F-3/F-4）| `7000`（改后的 cum[2]）、`4000/8000/200`（DERIVED_SIGN）、`-400/100`（NEGATIVE_DIFF）| 构造性论证用值 |
| 文档标识 | `D1-D7`/`F-1..F-5`/`N-1..N-4`/`R1-R5` | 结构性标识 |
| 源码行号 | 见 §一/§三各节 grep 输出 | 声明性定位符（本轮全部 `grep -n` 亲自核过，见各节命令原文） |

**结论**：本稿没有新增任何「差多少毫米算够近」式的生产判据；F-1 修法之后，`≤34mm` 从「上一稿误标声明值」彻底降级为「纯统计描述，代码路径里不出现」。

### N-2 · D7 全节按 `b4f0b348` 重写

见 §六（D7）。核心变化：T4-a 已合并（不再是「待审」），`multifloor.py` 今天在主线里**不存在**（B2 返工 3 未合并），R1-R5 全部重新核实。

### N-3 · ②b / ③ 具名边界出口（不建机制）

**问题**：一条洞口边若属于②b（平面画了、立面没画）或③（这个方向根本没有立面），今天的 `OpeningEdgeTickClaimV1` 结构要求 `evidence_ref` 指回 D2-a 的立面洞口证据档——而这两种情形下**根本不存在**这样一条立面记录。

**具名边界出口**（⛔ 不建四分类机制，只声明这个类型的适用边界）：

```
OpeningEdgeTickClaimV1 的构造前置条件（新增，显式声明，不是隐含约定）：
    该类型只能为**存在对应 D2-a 立面证据行**的洞口边构造。
    ⛔ ②b/③ 场景下，D2-a 不存在对应行 ⇒ 本类型**根本不为这条边构造实例**——
    不是"构造出来、tier 打成 pixel_only"，是"这个类型在这条边上不适用"。
    这条洞口边在这一步之后仍然是**纯平面实体**，等待第二步 §14.4 的
    四分类处置（本单不做，属另一张单）。
```

这与「无刻度可指认」的 `pixel_only` 是**不同性质**的空白：`pixel_only` 是「有一份立面证据，但没有链权威支撑其坐标」；②b/③ 是「压根没有立面证据可谈」。⛔ 不能把两者都译成二档——`tier` 字段的语义只在**存在立面证据**的前提下才有意义。

### N-4 · 收窄三处论证过头，保留免疫结论

**免疫结论本身不重开**（用户已拍板，§14.2 已定死洞口坐标只能取自尺寸链）。收窄三处：

1. **撤回**：「`1940` 既不是链节点、也不是任何链运算的结果」不是普遍成立的论断（若某条链恰好有节点 `1940`，它就是别的边的合法节点）。**改写为**：真正被免疫格点破坏的是**这一条边已裁定取 `1935` 的事实**——一旦这条边的一档认领已经落地为 `1935`（来自 `node_ref` 或 `chain_derived` 的精确重算），10mm 输出格点绝不能把**这个已裁定的值**改写成 `1940`，⛔ 不论 `1940` 本身在别处是不是某个节点的合法值。

2. **收窄引用范围**：§15.11 终裁表**本身没有**「这节只谈二档/像素」这个限定，本稿不再替它加这个限定；本稿的论证只引用它明确写出的部分——**pipeline 出口的身份是「去浮点尾差的规整」，服务对象是需要出干净数的值**，这与「一档链值本身已经是精确整数格点上的数（0.1mm 域），不需要也不应该被二次规整」并不冲突，⛔ 不需要主张「整节都是关于二档」这个更宽的、指南原文没写的结论。

3. **撤回**：「无坐标字段 ⇒ 天然不过 snap」——这不是自动成立的推论（代码解引用出坐标之后，完全可以选择再调用一次 snap 函数，类型层挡不住这个选择）。**改写为显式契约条款**（不是自动推论，是一条必须遵守的规则）：

```
硬约束（写进契约，不依赖"没有字段"这个偶然性）：
    从 OneTierValueV1 解引用出的坐标 ⇒ 该坐标**禁止**经过
    output_precision/structural_snap_grid/window_snap_grid 中的任何一个；
    只有从 PixelOutV1 解引用出的坐标才允许（事实上是必须）经过其中之一。
    这条约束由**装配代码的调用路径**保证（一档值的解引用函数与二档值的
    解引用函数是两个不同的函数，前者的实现里不 import 任何 snap 相关符号——
    这是可静态检查的「不该出现的调用不存在」，不是「没有字段所以自然不会」）。
```

---

## 五、⭐⭐ 本轮自证义务

### 五.1 复跑复核方的探针（命令原文 + 输出原文，本轮亲自执行）

```text
$ python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py statistics > /tmp/.../my_statistics.txt
$ diff /tmp/.../my_statistics.txt AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/statistics.txt
（无输出，exit 0，逐字相同）

$ python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py counterexamples > /tmp/.../my_counterexamples.txt
$ diff /tmp/.../my_counterexamples.txt AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/counterexamples.txt
（无输出，exit 0，逐字相同）

$ PYTHONDONTWRITEBYTECODE=1 python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py arithmetic
IMPORTED /tmp/tick_rw2_claude/src/agent/correction/evidence_adapters.py /tmp/tick_rw2_claude/src/agent/correction/opening_synthesis.py
INTERIOR_CUM_CHANGED require_chain_closed=PASS lo_mm= 7000.0 hi_mm= 8730.0 width_mm= 1730.0 declared_segment_mm= 1800.0
DUPLICATE_NODE_VALUE require_chain_closed=PASS cum_indices_1_2= [5000.0, 5000.0]
GRID_6925 69250
GRID_NEGATIVE_400 -4000
NESTED_POINTER_ASSIGNMENT /calibration/x/cum_mm/2 -> /calibration/x/cum_mm/3 model_config= {'extra': 'forbid', 'strict': True}
（除 IMPORTED 行的路径前缀因工作树不同而不同外，其余逐字相同）

$ python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py numbers > /tmp/.../my_numbers.txt
$ diff /tmp/.../my_numbers.txt AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/numbers.txt
（无输出，exit 0，逐字相同）
```

**四条探针全部本轮亲自复跑，三条逐字相同，一条（`arithmetic`）除路径前缀外逐字相同**——复核方的证据**可复现**，本轮的设计修法建立在**我自己验证过**的事实上，不是转引。

### 五.2 自设两条同形但不同的输入（证明「这一类」走不通，且用于验证本稿修法生效）

**Counterexample A（F-1 类，用真实南立面链、复核方未触碰的位置）**：见 F-1 节全文；命令与输出：

```text
$ python3 my_counterexamples.py
SOUTH_CUM [0.0, 5000.0, 6930.0, 8730.0, 9450.0, 11250.0, 14750.0, 16550.0, 17270.0, 19070.0, 21300.0, 23100.0, 25000.0]
REAL_SEGMENT_INTERIOR_PROBE lo=17270.0 hi=19070.0 fake_raw_mm=17970.0 nearest_tick=17270.0 distance_mm=700.0
PICKED_NODE_INDEX=8 IS_INTERIOR_NODE(1CHAIN-CONSEC-ELIGIBLE)=True
OLD_RULE(rework1 D5-a)=AUTO_ONE value_mm=17270.0
CHECK_F2_STYLE(value in cum_mm)= True
```

**用真实链数据、真实 `_nearest()` 函数、一个此前两轮审阅都没碰过的位置**（南立面索引 8→9 段），证明「1CHAIN-CONSEC ⇒ 自动一档」这**一类**规则在**任何**位置都可能被击穿，不是 East `O01` 或复核方那几个例子的特例。**本稿修法后的行为**：`confidence="structural_only"`（今天没有独立坐标证据），强制进入第二步整体把关输入集——不再是「悄悄落地、永远无人复查」。

**Counterexample B（F-2 类，两条独立拟合链在扁平表共享像素键但真实数值不同）**：见 §二.3；命令与输出：

```text
$ python3 my_counterexamples.py（下半段）
MULTI_SIGNATURE_DESPITE_DISAGREEMENT MULTI
P_WINS: flat_map_value=4000 primary_indices_nonempty=True
Q_WINS: flat_map_value=4050 primary_indices_nonempty=False
```

与复核方的 `RASTER_COLLISION`（两条链**总长相同**、碰撞点数值**恰好相同**，用来证明「碰撞发生」这件事本身）不同，本反例的两条链**独立拟合、真实数值相差 50mm**，用来证明：**即使扁平表已经因为覆写而报告了错误的那个值（`Q_WINS`），§二.2 的成员检查依然正确拒绝它**——不是「运气好没撞上」，是**这个检查的锚点从来不依赖扁平表本身是否曾经历过覆写**，只依赖它是否精确等于主链冻结数组里的某个值。

### 五.3 逐条对账表 + 最薄弱一处

见 §七（因需要引用 D1-D7 的具体行号/段落，置于全文之后）。

---

## 六、D1–D7 全文（累计式，不引用返工 1 正文）

### D1 · 勘察落点：x 从 reading 产物到配对的完整路径

| 跳 | 位置（本轮 `grep -n` 亲自核过）| x 在这里是什么 | 冻结字节溯源 | 证据档位 |
|---|---|---|---|---|
| 0 · 产物 | `openings[i].x_range_m`（`as_drawn_elev.py:191`）| 像素外推的 `[x_lo_m, x_hi_m]` | ❌ 裸 JSON | ❌ 无 |
| 0b · 产物 | 同 JSON `openings[i].edge_witnesses.{x0,x1}`（`:178`）：`dimension_refs`/`nearest_tick_px`/`measured_px`/`distance_mm` | reading 已做的刻度指认，多通道证据 | ❌ 裸 JSON | ❌ 未成档位 |
| 1 · 适配器 | `adapt_as_drawn_elevation`（`evidence_adapters.py:614`）：`z_low_ref=_pointer(...)`（`:709`）、`elevation_opening_claims=elev_openings`（`:834`）| **只搬 z** | z 有，x 无 | z 有，x 无 |
| 2 · 契约类型 | `ElevationOpeningClaimV1`（`evidence_contract.py:555`），docstring（`:568`）「x deliberately NOT here」| 只有 `z_low_m/z_low_ref/z_high_m/z_high_ref`（`:577-580`）| x 无字段 | x 无字段 |
| 3 · 校验器 | `validate_evidence_bundle`（`:1239`）逐条重算 z（`ELEVATION_Z_VALUE_DRIFTED_FROM_SOURCE`，`:1674`）| 只校 z | x 无 | x 无 |
| 4 · 配对消费者 B4 | `synthesize_openings`（`opening_synthesis.py:1009`）| `_elevation_openings(doc)`（`:956`）直接读裸 dict `x_range_m` | ❌ 绕过 bundle | ❌ 无 |
| 5 · 用作坐标 | `:1155,1167`：`grid_units(x_lo)` → `world_lo = along_origin_u + sign * lo_u` → 零容差配对 | 像素外推被当权威坐标 | ❌ | ❌ |

**三条硬结论**（与上一稿一致，本轮重新核实行号，未变）：① x 全程没有冻结字节溯源；② z 虽有契约但 B4 也不消费它（`synthesize_openings` 收 `elevation_doc: dict`，z 也从裸 dict 读）——`grep -rn "elevation_opening_claims" src` 只命中产/校验/排序三处，无配对消费者；③ B4 今天在 `src/`、`scripts/` 里零调用（`grep -rn "synthesize_openings(" src scripts` 只命中定义与测试），改造 x 路不动任何在跑的生产路径。

```text
# D1 命令原文（本轮亲自核）
$ grep -n "def adapt_as_drawn_elevation\|z_low_ref=_pointer\|elevation_opening_claims=" src/agent/correction/evidence_adapters.py
614:def adapt_as_drawn_elevation(
709:            z_low_ref=_pointer(input_id, contract, sha, f"{base}/z_range_m/0"),
834:        elevation_opening_claims=elev_openings,

$ grep -n "class ElevationOpeningClaimV1\|deliberately NOT\|z_low_m:\|def validate_evidence_bundle\|ELEVATION_Z_VALUE_DRIFTED" src/agent/correction/evidence_contract.py
555:class ElevationOpeningClaimV1(BaseModel):
568:    The horizontal extent (``x_range_m``) is deliberately NOT here: B4 owns
577:    z_low_m: float
1239:def validate_evidence_bundle(
1674:                    "ELEVATION_Z_VALUE_DRIFTED_FROM_SOURCE",

$ grep -n "def _elevation_openings\|def synthesize_openings" src/agent/correction/opening_synthesis.py
956:def _elevation_openings(doc: dict) -> tuple[tuple[str, float, float, float, float], ...]:
1009:def synthesize_openings(
```

### D2 · 契约形态：一条洞口边的裁定结果

**D2-a 证据档**（`ElevationOpeningClaimV1` 镜像加 x，与 z 完全对称）：

```
ElevationOpeningClaimV1（在既有 z 四字段旁）:
    x_lo_m:   float             # 逐字来自 /openings/<i>/x_range_m/0
    x_lo_ref: ArtifactPointerV1
    x_hi_m:   float             # 逐字来自 /openings/<i>/x_range_m/1
    x_hi_ref: ArtifactPointerV1
    x_lo_witness_ref: ArtifactPointerV1  # -> /openings/<i>/edge_witnesses/x0（reading 的指认证据，⛔ 不裁定）
    x_hi_witness_ref: ArtifactPointerV1  # -> /openings/<i>/edge_witnesses/x1
```

不变量：`x_lo_m == 冻结字节(.../x_range_m/0)` 精确 `==`；`x_lo_m < x_hi_m`；F-2 单源（`_payload_row_source_ids` 的 `elevation_opening_claims` 分支加上这些 ref 的 `input_id`，`evidence_contract.py:1127-1147`，本轮已重新核过该函数当前实现，只覆盖 `source_ref`/`z_low_ref`/`z_high_ref`，本设计要求它也覆盖新增的 x 四个 ref）。

**D2-b 裁定结果**（本轮修订版，纳入 F-1/F-2/F-4/F-5 的全部修法）：

```
OneTierValueV1 = ChainNodeValueV1 | ChainDerivedValueV1     # discriminated on value_source

ChainNodeValueV1:
    value_source: Literal["chain_node"]
    node_ref: ArtifactPointerV1        # 必须解析到 /calibration/x/cum_mm/<k>（§二.2 唯一锚点）
    #  构造前置条件：Decimal(node_ref 指向的字节值) 必须恰好等于某个候选值（由 D5 提出）；
    #  这条检查在【构造时】做，不是构造后再校验（F-2 修法）。

ChainDerivedValueV1:
    value_source: Literal["axis_plus_half_wall", "segment_span_diff", "segment_span_sum"]
    direction: Literal["toward_positive", "toward_negative"] | None   # 仅 axis_plus_half_wall（F-4①）
    operands: tuple[DerivedOperandV1, ...]
    recompute_cert_units: int
    #  构造前置条件：每个 operand 的证据档位不可低于 chain_backed（F-4③，
    #  operand 是 pixel_only 时整条 ChainDerivedValueV1 构造失败）；
    #  segment_span_sum 的 operands 索引必须连续（F-4④）。

DerivedOperandV1:
    role: Literal["axis", "half_wall_thickness", "cum_lo", "cum_hi", "segment_len"]
    ref:  ArtifactPointerV1
    derivation: Literal["declared_as_half", "half_of_declared_full"] | None  # 仅 half_wall_thickness（F-4②）

OpeningEdgeTickClaimV1:
    edge_id:       str                       # <opening_id>:<lo|hi>
    evidence_ref:  ObservationRefV1          # 指回 D2-a；⛔ 该类型只在存在对应 D2-a 行时才被构造（N-3）
    tier:          Literal["chain_backed", "pixel_only"]
    tier_one_value: OneTierValueV1 | None
    pixel_out_ref:  PixelOutV1     | None
    dimension_refs: tuple[ArtifactPointerV1, ...]   # 辅助指认线索，⛔ 不再是认领合法性的唯一依据（§二.2）
    debt_ref:      ArtifactPointerV1 | None  # 新增（F-2）：指向挂在这条边上的 EvidenceDebtV1（若有）
    provenance:    ClaimProvenanceV1

PixelOutV1:
    raw_pixel_ref:        ArtifactPointerV1
    output_precision_ref: ArtifactPointerV1  # 指向 pipeline 出口颗粒度声明点（10mm）
    rounded_result_units: int

ClaimProvenanceV1 = AutoProvenanceV1 | ModelProvenanceV1

AutoProvenanceV1:
    decided_by: Literal["auto"]
    auto_action_id: str      # AutoActionV1.action_id（F-5 拆分，本次具体动作实例）
    auto_rule_id:   str      # AutoActionV1.rule_id（规则本身）
    confidence: Literal["structural_only"]   # F-1 修法：今天唯一合法值

ModelProvenanceV1:
    decided_by: Literal["model"]
    packet_hash:   Hex64
    item_id:       str
    decision_hash: Hex64
```

**硬不变量**：`tier=="chain_backed"` ⟺ `tier_one_value is not None` 且 `pixel_out_ref is None` 且 `dimension_refs` 非空；`tier=="pixel_only"` ⟺ 反之。二档不是缺陷（§14.2b）。`debt_ref` 非空的 `pixel_only` 边表示「有刻度指认但今天冻结不了地址」（F-2 的 6 条边），与「结构上无刻度可指认」（East `O01` 的 `ALL_S1`）是**不同原因**，但**都落在 `pixel_only`**（N-1 之后的旁支说明，见 F-2 节末）。

**D2-c 三问的例子**（一档 chain_node + 一档 chain_derived + 二档-有债 + 二档-无债，四例全覆盖）：

1. **一档 chain_node — South `O01`**：`node_ref -> /calibration/x/cum_mm/2`（`6930`）、`/calibration/x/cum_mm/3`（`8730`）；`Decimal('6930') == Decimal(cum_mm[2])` 精确成立；`dimension_refs=[C_top_fine_s2,s3]` 作为**辅助**证据（⛔ 不是判据）；`confidence="structural_only"`（今天没有独立坐标证据，即便这条边几乎肯定是真的）。
2. **一档 chain_derived — 虚构示例**：轴线节点 `3000`（`role=axis`）+ 声明墙厚 `240` 的一半（`role=half_wall_thickness, derivation=half_of_declared_full`）⇒ `2880`；`recompute_cert_units` 精确重算 `30000-1200=28800` units；`direction="toward_negative"`（代码在轴线两侧都合法时会同时生成 `toward_positive` 候选给模型选，本例假设模型已选定负向）。
3. **二档-有债 — South `O02:x0`**：`refs=[C_bot_fine_s2,s3]`，`mapped_mm=8640`，`8640 ∉ calibration.x.cum_mm` ⇒ 构造 `ChainNodeValueV1` 失败 ⇒ `tier="pixel_only"`，`pixel_out_ref` 记像素规整值，`debt_ref` 指向 `EvidenceDebtV1(kind="other_known_missing", description="C_bot_fine 链在当前 calibration.x 之外无冻结地址")`。
4. **二档-无债 — East `O01`**：`refs` 全 `_s1`（`ALL_S1`），无内部边界被引用 ⇒ 结构上判定「没有可认的内部刻度」，`tier="pixel_only"`，`debt_ref=None`（这不是数据缺陷，是这个位置本来就没画刻度）。

**D2-d 正面论证：x 该进证据契约层**（与上一稿一致，未被裁决书挑战，保留）：docstring 原意「只带被具名消费者要过的东西」——x 现在有了具名消费者（第一步的刻度认领）；「B4 拥有需要 x 的配对」的事实前提已变（B4 靠读裸 dict 拿 x、零容差配对永远对不上——banner ⑥b：真实四立面配 0 对）；x 与 z 不拆分放两层（避免 F-130「两条并列生产线各自漂移」的形状）。

**D2-e 裁决账绑定**：见上方 `ClaimProvenanceV1`（已含 F-5 的 `auto_action_id`/`auto_rule_id` 拆分）。

### D3 · 模型那一拍怎么接

**D3-a 包**：`OpenItemV1.kind`（`wall_compiler.py:304-309`）加一项 `"opening_edge_tick_claim"`；候选类型采用上一稿的乙路（判别联合 `TickCandidateV1`，⛔ 复用 `SymbolicCandidateV1` 会把刻度语义混进现全是墙厚语义的 `SymbolicOperation`）：

```
TickCandidateV1:
    candidate_id: str
    value: OneTierValueV1        # chain_node 或 chain_derived（含 F-4 的 direction/operand 签名）
    preview_local_x_units: int   # 代码算好的预览，模型只看数不算数
```

**⭐ F-1 修法在这里的接口影响**：D5-b 惊动模型的边（结构不闭合/矛盾）走 `OpenItemV1`；D5-a 自动认领的边（结构闭合，`confidence="structural_only"`）**不进 `OpenItemV1`**（它们没有歧义需要模型逐条选择候选），但**必须**同时进入 D5 之后新增的 `WholeBuildingOpeningReviewInputV1.structural_only_tick_claims`（F-1 修法），由第二步整体把关看到——**两条不同的模型接触点，服务不同目的**：`OpenItemV1` 是「这条边有歧义，请选一个」；`structural_only_tick_claims` 是「这条边代码已经决定了，但决定的依据只有结构证据，请在看整栋楼是否讲得通时留意它」。

**D3-b 响应**（与上一稿一致，未被裁决书挑战，保留）：`TickClaimResponseV1` 独立类型，结构上不含 `whole_building_review`：

```
TickClaimResponseV1:
    model_config = _CFG                      # extra="forbid", strict
    packet_hash: Hex64
    item_decisions: tuple[TickItemDecisionV1, ...]

TickItemDecisionV1:
    item_id: str
    action: Literal["select_candidate", "reject_all", "request_reperception"]
    candidate_id: str | None
    reason_code: CodeToken
```

不破铁律（字段树构造不出数字）+ 阶段隔离（第一步结构上没有 `whole_building_review` 这条路，⛔ 不是纪律）——两条论证与上一稿一致，本轮重新核过 `decision_schema.py:174-364` 未变，未被裁决书挑战，保留。

### D4 · 判据（本轮改写，纳入 F-2/F-3/F-4 全部修法）

**检查①（引用存在 + 值域权威，取代上一稿的「角色闭合」单一判据，F-2 修法）**：

```
∃ k : Decimal(calibration.x.cum_mm[k]) == Decimal(claimed_mm)
    ⇒ node_ref 合法（不要求 dimension_refs 指向的链与 calibration.x 是同一条命名链——
       calibration.x 是这张立面唯一被冻结的权威 x 记录，dimension_refs 只作辅助）
不存在这样的 k ⇒ 不构造 ChainNodeValueV1；若也无法构造合法 ChainDerivedValueV1，
    ⇒ 降 tier="pixel_only" + 视情况挂 EvidenceDebtV1（F-2 §二.2）
```

**检查②（运算精确可复算，含 F-4 的签名化 operand 检查）**：

```
chain_node:            结果 = grid_units_from_mm(node_ref 指的 cum 值)
axis_plus_half_wall:   结果 = axis_units ± half_wall_units（符号取自显式 direction 字段，⛔ 不由 lo/hi 边角色推断，F-4①）
segment_span_diff:     结果 = cum_hi_units − cum_lo_units（同链，允许负值，F-4④）
segment_span_sum:      结果 = Σ segment_len_units（operands 索引连续，F-4④）
前置：每个 operand 的证据档位 == chain_backed 或 role == 声明常量（F-4③，
      任一 operand 是 pixel_only ⇒ 整条 ChainDerivedValueV1 构造失败，不是部分接受）
重算结果必精确 == recompute_cert_units（整数比较，零 epsilon）
```

**前置门（构造 node_ref/chain_derived 之前必须先过，F-3 修法，两道独立）**：

```
① _require_chain_closed（既有，evidence_adapters.py:569，⛔ 本稿不改）：
     sum(values_mm) == cum_mm[-1] == overall_mm
② _require_chain_prefix_consistent（新增、独立，本稿只给规格）：
     ∀ i : cum_mm[i] == cum_mm[i-1] + values_mm[i-1]（精确整数域）
两道任一不过 ⇒ 该链上任何 node_ref/chain_derived 构造直接拒绝（EvidenceContractError），
不是「构造出来再靠别处校验」。
```

**失效条件（区间级，与上一稿一致，未被裁决书挑战，保留）**：同节点塌缩、反向节点由区间不变量（`lo_units < hi_units` 严格、非零宽）挡；合法链派生 false-negative 由检查②「运算精确可复算」而非「结果∈cum」放行；「认对是个刻度、认错哪个刻度」——**本轮不再交给 D5 的结构谓词独自解决**（那正是 F-1 揭示的空白），而是交给 F-1 修法的 `confidence` 分档 + 强制整体把关。

### D5 · 按需触发（本轮改写，纳入 F-1 修法）

**D5-实测**（与上一稿一致，本轮重新验证签名统计，§五.1 逐字复现）：三类结构签名（`1CHAIN-CONSEC`/`ALL_S1`/`MULTI`），68 条边分布不变。

**D5-a 自动候选生成**（⛔ 不再直接称为「自动认领=已完成」，改称「代码提出高置信度候选，仍需整体把关」）：

```
候选生成 ⟺ nearest_tick_px 经 dimension_witnesses.x 表解析到某值 V，
    且 Decimal(V) 精确等于 calibration.x.cum_mm 的某个元素（§二.2 唯一锚点，取代
    「N 被 dimension_refs 角色闭合」这一条单独的判据——结构闭合仍然要看，但只是
    「有没有辅助证据」，不再是「能不能自动认领」的唯一门槛）
⇒ 构造 ChainNodeValueV1，provenance = AutoProvenanceV1(confidence="structural_only")
⇒ ⭐ 该 claim 强制进入 WholeBuildingOpeningReviewInputV1.structural_only_tick_claims（F-1 出口全检）

不满足值域锚点 ⇒ 不生成 chain_node 候选；
    若 dimension_refs 全 `_s1`（ALL_S1，结构上表示"落在开口段内部，无刻度可认"）
    ⇒ 直接 tier="pixel_only"（无 debt，语义上的二档，不是数据缺陷）；
    若 dimension_refs 非 `_s1` 但值域锚点不过（F-2 的 6 条边情形）
    ⇒ tier="pixel_only" + 挂 EvidenceDebtV1（有 debt，数据地址缺陷）
```

**D5-b 惊动模型**：与上一稿一致（结构不闭合/refs 矛盾/残缺）——这部分本来就走 `OpenItemV1`，未被任何一条裁决意见挑战。

**D5-c 为什么这仍然是零阈值**：三个分支判据全是符号谓词或精确值域成员检查（`Decimal ==`，不是「差多少算近」）；`distance_mm` 依旧只作证据随 claim 流转，永不进任何分支条件。**本轮新增的 `confidence` 字段不是阈值**——它是一个**永远只有一个合法取值**（`structural_only`）的枚举，不是一个可调的数字。

### D6 · 两步之间的冻结

见 §三 F-5 全节：闭包持牌 + 零携带状态载体 + 出口重推导（`SealedTickClaimsV1`），复用 B2 返工 3 已实证的范式。`rule_id`/`action_id` 拆分、`AutoActionV1.kind` 补项均已在 D2/D5 给出。

### D7 · 风险清单（按 `b4f0b348` 全节重写，闭合 N-2）

| # | 风险面 | 当前树的真实状态（本轮 `ls`/`grep` 亲自核过）| 与本方案的关系 |
|---|---|---|---|
| **R1 · T4-a（已合并，⛔ 不再是「待审」）** | `git log --oneline -1` = `b4f0b348`，`09.05b_wrapup_fourth_leg (...T4-a merged; suite 3819)`；`opening_synthesis.py` 现有 `redemption_row_for_obligation`（`:481`）、`_resolve_backed_obligation`（`:609`）、`assert_obligations_backed`（`:683`）、`redeemable_debt_ids`（`:705`）——出口全检锁已在主线 | 本方案要改的 B4 输入面（`_elevation_openings`，`:956`）与 T4-a 改动的 obligation resolver（`:481-722`）**同文件不同函数**，重叠风险低于上一稿描述的「同函数碰撞」；仍需施工前重跑一次全量确认锁不退化 |
| **R2 · B2 返工 3（仍待审，`multifloor.py` 今天不在主线）** | `find src -iname "*multifloor*"` 无输出——B2 的封印代码**只存在于它自己的分支**；`AI_agent/logs/reviews/execution/2026-09-04w_B2_rework3_execution.md` 是**已交付、待跨家族审**的施工报告，非主线代码 | 本方案 D6 引用的是 B2 **已验证的封印范式**（闭包令牌+零状态+出口重推导），不引用 `multifloor.py` 的具体代码或哈希；即便 B2 返工 3 再改一轮，只要范式不变本方案不受影响；施工排期仍应**晚于** B2 合并（⛔ 不碰同一份 `multifloor.py`，本方案不新建这个文件） |
| **R3 · 立面 bundle 既有哈希/锁** | `_sorted_bundle`（`evidence_contract.py:737`）、`finalize_bundle`（`:784`）、`_payload_row_source_ids`（`:1127`）| x 四字段 + 两 witness ref 进 `_sorted_bundle` dump ⇒ 每个立面 bundle 的 `content_sha256` 变；`debt_ref` 字段（本轮新增）若挂在 `OpeningEdgeTickClaimV1` 上也会进哈希——施工需重生成受影响立面产物基线 |
| **R4 · content_sha256 churn** | T4-a 的 `obligation` 字段已经翻过一次哈希（`EvidenceDebtV1.obligation`，`evidence_contract.py:539`，已在主线）| 本方案的 x 四字段是**第二次**翻搅同一批 bundle 的哈希——施工单应在 T4-a 稳定后一次性重算基线，⛔ 不与任何在飞的哈希改动并发 |
| **R5 · B4 已合并主线 + docstring 依赖边** | `synthesize_openings`（`opening_synthesis.py:1009`）从裸 dict 读 x、零容差配对；改 `evidence_contract.py:568` docstring | 改 B4 输入 = 改已签字模块入口，属工程档、须派工换人审；docstring 修改**⛔ 不写仓库根前缀的生产路径**（CLAUDE.md §8.5，`affected_tests` 会建边）|

```text
# D7 命令原文（本轮亲自核）
$ git log --oneline -1
b4f0b3483bfdb420fbf3dd2d53b3a732150218f4 09.05b_wrapup_fourth_leg (opening-alignment doctrine ratified; T4-a merged; suite 3819)
$ find src -iname "*multifloor*"
（无输出）
$ grep -n "def redemption_row_for_obligation\|def _resolve_backed_obligation\|def assert_obligations_backed\|def redeemable_debt_ids" src/agent/correction/opening_synthesis.py
481:def redemption_row_for_obligation(obligation: str) -> tuple[str, DebtRedemption]:
609:def _resolve_backed_obligation(obligation: str) -> tuple[str, DebtRedemption]:
683:def assert_obligations_backed(debts: Sequence[EvidenceDebtV1]) -> None:
705:def redeemable_debt_ids(
```

---

## 颗粒度收口（一档链真值 vs pipeline 10mm 出口，N-4 收窄版）

**结论不变（用户已拍板，§14.2 定死）**：一档坐标免疫 10mm 出口格点；二档消费 10mm 出口格点。

**三处收窄**（详见 N-4 节）：① 不再声称「`1940` 普遍不是链节点」，改为「这一条边**已裁定**的值不许被格点改写」；② 不扩大引用 §15.11 的范围到「整节都是二档」；③ 「无坐标字段⇒天然不过 snap」改为**显式契约条款**（一档解引用函数与二档解引用函数是两个不同函数，前者不 import snap 符号），不依赖字段缺失的偶然性。

| 档 | 出口处置 | 契约落点 |
|---|---|---|
| 一档 | 坐标 = `tier_one_value` 精确落地，⛔ 不经 10mm snap（由**解引用函数分离**这条显式规则保证，非字段缺失自动推出）| `OpeningEdgeTickClaimV1` 无坐标字段；两个独立解引用函数 |
| 二档 | `PixelOutV1` 记 `raw_pixel_ref → output_precision_ref → rounded_result_units` | `PixelOutV1` 三字段 |

---

## 七、逐条对账表（5 阻断 + 4 不阻断）+ 最薄弱一处

| 项 | 上一稿的病 | 本稿怎么闭合 | 证据在哪 |
|---|---|---|---|
| **F-1** | 用最近邻选择的结果证明最近邻选择有建筑语义 | `AutoProvenanceV1.confidence="structural_only"`（类型层承认今天没有独立坐标证据）+ 强制进入第二步整体把关（出口全检，遗漏一条即装配函数构造不出输入对象）| §三 F-1 全节；D2-b `AutoProvenanceV1`/D3-a 接口影响/D5-a；自设反例 Counterexample A（§五.2）|
| **F-2** | 数值相等当节点身份；扁平表当多链证据 | 唯一锚点=`calibration.x.cum_mm` 值域成员检查；6 条边具名降二档+挂 `EvidenceDebtV1(kind="other_known_missing")`；跨链同指用同一锚点吸收 | §二全节；D2-b `debt_ref` 字段；自设反例 Counterexample B（§五.2）|
| **F-3** | 链总长闭合当逐节点前缀和 | 新增独立 `_require_chain_prefix_consistent` 前置门（不改现有函数），写清「验过什么/没验什么/交给谁」表 | §三 F-3 全节；D4 前置门表 |
| **F-4** | 可复算当有资格/表达唯一/属于本图 | 四子项签名化：`direction` 显式枚举 + 歧义时双候选、`derivation` 显式声明半厚来源、operand 证据档位不可降级传播、`segment_span_sum` 索引连续性检查 | §三 F-4 全节；D2-b `ChainDerivedValueV1`/`DerivedOperandV1` |
| **F-5** | 冻结源字节当冻结指针；三件套描述与 B2 实际交件不符 | 撤回三件套，改用 B2 返工 3 实证范式：闭包持牌+零携带状态载体+出口重推导；`rule_id`/`action_id` 拆分；`AutoActionV1.kind` 补项 | §三 F-5 全节；D6 `SealedTickClaimsV1` |
| **N-1** | 数字自查非全量+分类错 | 全量重跑（170 token 逐字复现）；`≤34mm` 降级为纯统计描述，D5-a 不再引用 | §四 N-1；§五.1 |
| **N-2** | D7 对在飞线描述过期 | D7 按 `b4f0b348` 全节重写：T4-a 已合并、`multifloor.py` 今天不在主线 | D7 全表 + 命令原文 |
| **N-3** | ②b/③ 缺具名边界出口 | `OpeningEdgeTickClaimV1` 显式声明「只在存在 D2-a 行时构造」，不建四分类机制 | §四 N-3 |
| **N-4** | 免疫结论论证过头三处 | 撤回「`1940` 普遍非节点」/收窄 §15.11 引用范围/撤回「无字段⇒不过snap」改显式契约条款 | §四 N-4 + 颗粒度收口节 |

### 最薄弱一处

**F-1 修法的「出口全检」只保证「模型看得到」，不保证「模型看得对」。** 本稿把 F-1 从「局部判据能不能证明建筑语义」这个我已经证明**信息论上不可能**用今天的证据字段解决的问题，转移成「局部判据的产物是否结构性地暴露给第二步整体把关」这个**能**在类型层解决的问题——这是一次**范围收缩**，不是一次**风险消除**：如果第二步的模型审查本身质量不够（漏看、判断错），一条被 `structural_only` 标记的错误认领依然会走到最终几何里，只是**这次它至少留了一个可以被复查/事后审计的痕迹**（`confidence` 字段本身就是将来做「这批一档值里有多少从未被独立坐标证据验证过」这种统计审计的抓手）。这个薄弱处**不能靠本稿再往前推一步解决**——已经穷尽了当前证据字段能给出的所有零阈值组合（§三 F-1「穷尽过的无效解」），真正的解法是**reading 侧**新增一个与 `_nearest()` 正交的独立坐标证据源（如「像素是否落在识别出的引出线/刻度墨迹上」的视觉判断），这不在本单范围内，已作为 D7 之外的**显式上游依赖**登记在 F-1 节。

---

## 八、验收 #7 · 零 `src/` `tests/` 改动自证

```text
$ git status --porcelain
?? AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/
?? AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md
?? AI_agent/logs/reviews/request/2026-09-05f_tick_claim_design_rework2.md
?? AI_agent/logs/reviews/verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md

$ git diff --stat b4f0b348..HEAD -- src tests
（空，exit 0 — src/ 与 tests/ 零改动；本轮全程只新增一份 AI_agent/logs/reviews/execution/ 下的 md
 + 三份预置材料原样落库，未改动任何既有文件内容）

$ python3 -c "import src.agent.correction.evidence_contract as c; print(c.__file__)"
/tmp/tick_rw2_claude/src/agent/correction/evidence_contract.py
```

未执行 `pip install -e .`；未用 `git add -A`（分段提交，每次 `git diff --cached --numstat` 核过）；未进入 `/workspaces/EnergyPlus-Agent-dev` 写任何东西；同机有别的席位在飞时本轮**没有跑 pytest**（本单不需要）。
