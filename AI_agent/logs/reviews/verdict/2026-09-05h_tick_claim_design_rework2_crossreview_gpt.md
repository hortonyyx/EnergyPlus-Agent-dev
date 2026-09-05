REWORK · 阻断 4 · 不阻断 4

# 刻度认领设计稿返工 2 · GPT 跨家族复核裁决

- 日期：2026-09-05；复核席：GPT 家族，上一轮裁决方。本轮重新确认原问题，不因同家族自引而免检。
- 被审对象固定为 `75f7732a` 的 [802 行设计稿](../execution/2026-09-05f_tick_claim_design_rework2.md)。审查提交后的 HEAD 不替换被审对象。
- 工作目录：`/tmp/tickrw2_review_gpt`；任务：[本轮复核单](../request/2026-09-05h_tick_claim_design_rework2_crossreview.md)。指定六组材料已读，包括旧裁决、返工派工单、指南 §十四/§十五及旧证据目录。
- **直接采用主控事实：B2 返工 3 已过审并合并；主线全量 3850 passed / 0 failed。** 本席没有重跑该全量。当前被审树是旧基点的设计分支，树内没有 `multifloor.py` 不推翻当前主线状态，不触发 A 层。

**目前不能进施工单。** 作者修对了前缀和的核心判据、方向枚举、半厚来源以及 B2 范式的文字描述。但 `structural_only` 仍以一档事实进入第二步；成员检查仍会把别的节点同值当作本节点身份；操作数资格和本次裁决绑定仍未形成可施工的完整契约。不是要求在设计审里交生产实现，而是现有签名、守卫和消费关系不足以唯一确定应实现的行为。

证据：[本轮目录与读法](../../experiments/2026-09-05h_tick_claim_crossreview_gpt/README.md)、[独立命令及原文输出 E01–E16](../../experiments/2026-09-05h_tick_claim_crossreview_gpt/evidence.md)、[新输入探针](../../experiments/2026-09-05h_tick_claim_crossreview_gpt/probe.py)。下文 `稿:L`、`旧裁决:L`、`指南:L` 分别指被审稿、`2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md`、`AI_agent/guides/reading_correction_split_guide.md`。这些简写都是 file:line；行号来自本席重新执行的 `rg -n`，完整文件路径及输出在相应 E 组。

## 一、三条必做复核

### 1. 上一轮五阻断的原问题确认：通过，原问题未被替换

本席重新读了旧裁决的现象、反例、病根和建议方向。独立命令：

```sh
rg -n '^### F-|病根一句|建议方向' AI_agent/logs/reviews/verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md
```

原文输出摘录（各项正文全文定位见 E02）：

```text
156:### F-1 · D5 的“结构证书”是最近邻选择的产物，旧判断被搬到了输入侧
183:**病根一句：** 用最近邻选择的结果证明最近邻选择具有建筑语义，证据与待证结论来自同一次选择。
187:### F-2 · 多链的源映射没有进入契约；当前已有 6 条边无法构造指定 node_ref
218:**病根一句：** 把多链的节点来源、坐标系和等价关系压成一个数值查找表，后续却要求它提供完整来源证明。
222:### F-3 · D4 把“链总长闭合”当成“所有 cum 是干净前缀和”
235:**病根一句：** 前置门测的是总长代理量，设计的成立性证明依赖的是逐节点前缀和事实。
239:### F-4 · chain_derived 的运算签名与证据资格未封闭，精确重算不能证明一档
250:**病根一句：** 运算结果可复算只证明算术一致，不能证明操作数有资格、表达式有唯一含义、结果属于本图一档证据。
254:### F-5 · D6 限制了构造，却未把引用选择与第一步裁决一起冻结；B2 不能代证
272:**病根一句：** 构造许可、来源字节完整性和“本次第一步究竟裁了什么”被合并成同一个冻结承诺。
```

**原问题成立不代表本轮继续全数阻断。** F-3 的核心反例现在能被新公式拒绝，改判；F-4 前两个子项已有实质修正；F-5 中“B2 尚待审所以不能引用”的前提撤销。保留的 F-5 问题是本契约未绑定本次决定，不能借 B2 的批准跨过这个问题。

### 2. 五阻断、四不阻断逐条闭合：两项已闭合，其余存在残留

| 旧项 | 本轮闭合判定 | 本席独立定位、验证与计数归属 |
|---|---|---|
| F-1 | **声称与内容不符** | 稿:185/609 的标签确已增加；:195–203 只有 tuple 字段及遍历承诺，未闭合消费方与本次全集；:618/642/709 仍先成为一档决定。D5 还有原点分支冲突。阻断 R-1；E03/E13。 |
| F-2 | **部分** | 稿:116–130、595/624 给出非主链六边的二档有债出口，认可该进展；:115/144/666–670 仍以成员资格替代身份；:126 的债无兑现执行绑定。阻断 R-2；E04/E09/E13/E14。 |
| F-3 | **部分（核心已闭合，余项不阻断）** | 稿:235/690–693 逐点递推确实检查中间节点；不是第二份总长检查。新污染输入被拒，旧根因不再阻断。数组基数、起点与退化段域仍需补明，见 N-3；E05/E13。 |
| F-4 | **声称与内容不符** | 稿:249–275 的方向与半厚规则有效；但:67 声称 `operand.evidence_tier` 已进字段，:583–586 实际没有；:290/308–311/679 的段 ref 与求和域冲突。阻断 R-3；E06/E13。 |
| F-5 | **部分** | 稿:335–364 确实采用闭包、单 artifact 载体、每次重读；:607–615 也拆了动作/规则 ID。但没定义本次决定冻结在哪条记录、消费端锁哪个批次；换有效 bundle 仍通过。阻断 R-4；E07/E08/E13。 |
| N-1 | **声称与内容不符** | 稿:391 自认旧探针读旧稿，:774 仍以旧 170 token 支撑“全量”；本稿实扫为 168/1058。分流数字亦未按新规则更新。见本轮 N-1；E11/E13、numbers.md。 |
| N-2 | **部分** | 稿:731/733/735 的 T4-a 状态及函数行号已修；:732 的 B2 状态今天已过期，:733–734 的全称哈希判断仍过宽。见本轮 N-2；E11。 |
| N-3 | **已闭合** | 稿:419–424/590 明示仅在 D2-a 存在时构造，缺行保留纯平面实体交第二步。已给范围出口，不要求它再造二档、不要求本稿实现四分类。E11。 |
| N-4 | **已闭合（旧论证问题）** | 稿:433/435/437–446 明确撤回三处过度推论，改成保持本边已裁定值与显式分档调用规则。免疫决定继续成立，不重请批准。累计稿另有颗粒度配套遗漏，单列本轮 N-4，不倒称原三处未修。E10/E11。 |

支持表中改判的独立原文输出例：

```text
235:| **逐节点前缀和**（`cum[i] == cum[i-1] + values[i-1]` 对所有 `i`，精确整数域比较）| **新增、独立的**前置检查 `_require_chain_prefix_consistent`（本稿只给规格，不写实现，⛔ 改动 `evidence_adapters.py` 属另一张施工单）| 同一错误族：`EvidenceContractError("CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM")`，整条链的任何 `node_ref`/`chain_derived` 认领全部拒绝构造——**在构造函数的守卫里堵死，不是先构造出来再指望某个下游校验器发现** |
421:    ⛔ ②b/③ 场景下，D2-a 不存在对应行 ⇒ 本类型**根本不为这条边构造实例**——
423:    这条洞口边在这一步之后仍然是**纯平面实体**，等待第二步 §14.4 的
```

### 3. 换同形输入：未通过；本轮有独立新输入

命令（均 exit 0，完整原文 E13–E16）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/probe.py all
PYTHONDONTWRITEBYTECODE=1 python3 AI_agent/logs/experiments/2026-09-05h_tick_claim_crossreview_gpt/capture.py
```

`capture.py` 还复跑旧 `statistics/counterexamples/arithmetic/numbers` 与旧 `capture_evidence.py` 的全部命令。旧 capture 只重定向输出到本轮目录，**没有覆盖旧证据**。本席复现能力不等于能证明作者在其历史会话里确实执行过全部命令。

| 新输入 | 独立结果 | 判定 |
|---|---|---|
| 未标注中间段里的两条边，像素 `176/254`，刻度 `120/300`，对应链值 `3100/7800` | 实际 `_nearest` 选两端，值域与区间有序均通过 | 原误认形状仍能生成一档；标签没有裁定它，R-1 |
| 同一审查批要求 `FacadeR:W07:lo/hi`，传入 tuple 只有 lo | tuple 字段形状没有全集等式；来源/消费绑定未给出 | 这是契约反模型，**不是执行未来构造器**，R-1 |
| 主链 `[0,2600,5200,10400]`，两条链在同一像素键分别声明 `2600/5200` | 无论哪条最后写，成员检查都通过；却选不同主链索引 | 正面击穿作者“Q_WINS 自然被筛掉”的修法，R-2 |
| 新中间污染 `[0,900,2450,3600]`，段 `[900,1500,1200]` | 现有总长门通过，新递推为 False | **确认 F-3 核心修复有效** |
| 零段、负段及短 cum 数组，细节见 N-3 | 现有总长门通过；按逐节点递推可通过 | 尚需完整域规格；不把这些统称为中间前缀污染 |
| cum `[0,1600,4300,7500]`，`segment_len` 引用 cum 索引 1/2 | 依稿累加得 `5900`，实际两段长和为 `4300` | 运算域混淆，R-3 |
| 同源字节、同 input_id、不同 manifest 的两份有效 bundle | 现有 validator 均接受；载体普通赋值换 artifact 后，下一次派生收到另一份 bundle | 有效性检查不能绑定本次裁决，R-4 |
| 全墙厚格点单位 `201/202`；内侧轴线 `3600/7600`、全厚 `220` | `201` 不可除二，`202→101`；显式方向可得 `3710/7490` | **确认 F-4 两项修复有效** |

关键原文输出：

```text
SPEC_NEW_COLLISION P_LAST true_boundaries=[2600,5200] flat= 2600 membership= True selected_primary_index= 1
SPEC_NEW_COLLISION Q_LAST true_boundaries=[2600,5200] flat= 5200 membership= True selected_primary_index= 2
ACTUAL_CLOSED=PASS INTERIOR_NEW SPEC_prefix= False len_cum= 4 len_values_plus_1= 4 cum= [0, 900, 2450, 3600]
SPEC_SEGMENT_SUM refs=/cum_mm/1,/cum_mm/2 contiguous=True draft_sum_mm= 5900 declared_segment_sum_mm= 4300
ACTUAL_TWO_VALID_ARTIFACTS same_source_bytes= True bundle_ids_differ= True
D6_WITH_ARITY_BRIDGE ordinary_artifact_assignment=PASS derive_received_other_bundle= True new_bundle_valid=True not_a_production_tick_claim_test=True
```

## 二、四条阻断 findings

### R-1 · F-1：标签揭露了不确定性，但候选变事实与整体审查的闭环没有落地

**重点 A 的裁定：有表达上的改进，尚非结构性解法。** 不因字段名含 confidence 就判无效；问题是稿:618、642、709 已将它置于 `chain_backed` 的已决定结果，第二步按指南:1038/1182 消费一档权威，稿:760 又保护其坐标免疫规整。该标签目前没有改变这些承重行为。

本席 E03 重新检索到的输入定义是：

```text
195:WholeBuildingOpeningReviewInputV1:
196:    # 第二步整体把关拿到的输入之一，⛔ 不是可选项
197:    structural_only_tick_claims: tuple[OpeningEdgeTickClaimV1, ...]
198:    #  不变量：bundle 里每一条 provenance.confidence == "structural_only" 的
199:    #  OpeningEdgeTickClaimV1，必须原样出现在这个元组里——构造函数机械遍历
```

“由构造函数遍历 bundle”可以成为正确设计，**本席认可其意图**；但这里尚未给定从哪个冻结批次的哪个完整 claim 集合遍历、输入类型如何绑定该集合，以及第二步哪个唯一入口只能消费这个输入。tuple 允许空集/子集；单次遍历一个被截断或换批次的来源也会完整遍历那个错误来源。所缺的是来源全集与消费入口的关系，不能用“只有遍历所以不会漏”代证。现有 `WholeBuildingReviewV1` 是响应侧 `verdict/findings`（`decision_schema.py:335–366`，E09），本身没有替新增输入提供这个约束。

更承重的是**阶段关系**：稿:206 只承诺看得到，:642 明说这些边不进第一步 `OpenItemV1`，到第二步才质疑；稿:696 亦把“认错哪个刻度”交给第二步。指南:1006、1141–1146 则要求第一步完成认领裁定、本图重检及回②，第二步消费各图已确定的值。如果整体审查发现 `3100/7800` 认错，谁使本图回第一步、生成新裁决批次并使旧结果失效？稿中没有合法状态转换。D6 同时要求第二步不能改既定事实；“请留意”既没有补这条转换，也不能作为第一步已完成的依据。本席不要求模型百分之百判断正确，要求的是模型裁决实际处在该承担认领的位置。

**D5 本身还不自洽。** 稿:705–710 先判断主链成员，再在“不满足值域锚点”下以 `ALL_S1` 降档（:712–716）。本席对当前 68 边按该顺序重算（E13）：

```text
SPEC_D5 east O01:x0 auto_chain value= 0.0 indices= [0]
SPEC_D5 east O01:x1 auto_chain value= 0.0 indices= [0]
SPEC_D5_TOTAL {'auto_chain': 62, 'pixel_debt': 6}
```

East `O01` 两端的 0 都属于主链，进不了稿:625 宣称的无债二档分支；区间门随后会拒绝 `[0,0]`，但稿没给这个拒绝通向该二档的步骤。若施工者把 `ALL_S1` 提前，又回到旧裁决:185 禁止的“用序号证明没有标注”，会错降确实指原点的边。不能让施工者自行选择两种互相冲突的规范。

**所需改动方向：** 把待认领候选与第一步已裁定事实分开，列清何时用同图模型判定、何时可自动终结；为全集输入给唯一冻结来源与消费约束，为整体审查推翻时给回第一步的具名出口。无需发明新毫米阈值，也不能宣称只有 reading 增字段这一条路：指南已经授权第一步的模型裁决。

### R-2 · F-2：成员检查仍不能证明身份；降档债只是有用的记账，未闭合兑现

**六边事实重新确认。** E14 原扫描仍为 South `O02:x0/x1`、`O04:x0/x1` 与 West `O05:x0/x1` 的 `primary_indices=[]`；本轮 D5 重算分别得到 `8640/12640/13360/17360/14540/15740` 的 `pixel_debt`（E13）。这六条具名出口有真实进展，不再指控作者完全没给出口；也不要求它凭空造出不存在的主链节点地址。

**但核心身份问题未解。** 本席 E04/E06 检索的原文是：

```text
112:    ∃ k : Decimal(calibration.x.cum_mm[k]) == Decimal(claimed_mm)
667:    ⇒ node_ref 合法（不要求 dimension_refs 指向的链与 calibration.x 是同一条命名链——
668:       calibration.x 是这张立面唯一被冻结的权威 x 记录，dimension_refs 只作辅助）
```

这证明“主链存在这个数”，没有证明“原来被指认的节点就是它”。新碰撞例把非主链在像素键 `275.0` 的 `5200` 恰好放成主链**另一个**节点值，两个写入顺序都通过。选定值与 ref 随后写链变化，来源冲突未被检查。作者稿:144 对另一链“恰好也在同一物理位置画了刻度”的解释是额外的建筑语义假设，不是成员检查的输出。主链只有一个字段位置，也不等于它已获授权消解全部别链矛盾。

**重点 B 的裁定：降二档有债是有效临时承载方式，但本稿只完成记账。** 其描述给出了必要上游工作“新增可寻址冻结记录”（稿:125/130），却没给具名负责阶段/处理器、触发重裁的事件、旧新 source/edge 的对应检查以及何时退债。稿:216 只说由“债务台账的读者（人工排期）”关注，并未指定谁承担这件事。

它实际指定 `obligation=None`（稿:126）。既有契约与消费者的独立输出（E09）：

```text
529:    #: downstream obligation, or ``None`` = no downstream obligation at all
700:        if debt.obligation is None:
701:            continue
742:        if debt.obligation is None:
743:            continue
```

本席用新的缺地址债调用实际 API（E13）：

```text
ACTUAL_DEBT obligation= None assert_backed=PASS redeemed= () description_upgrade_request_does_not_dispatch=True
```

这不是 T4-a 漏兑，恰是当前契约要求它保留这笔**不归自己兑**的债。不能借“已挂 EvidenceDebtV1”推出有人将其升级。新增地址空间也仅是必要条件；若新记录与该边/坐标系对不上，或跨链仍冲突，不能因路径出现就直接升档。

**所需改动方向：** 保留原链身份与坐标系、指认记录的绑定；冲突进入具名裁决，不由同值查表静默替换。对临时降档给明确的读取产物补证→同图重新认领→新裁决替换旧裁决→退债条件及负责人/阶段。可以是明确人工流程，不强制扩现有 obligation 枚举；但不能把 `None` 当成已绑定的兑现承诺。

### R-3 · F-4：方向与半厚已修，运算域及证据资格仍非封闭签名

**重点 D 逐子项裁定：**

| 子项 | 裁定与独立证据 |
|---|---|
| 加减方向 | **已修核心问题**。稿:249–260/576/677 明示枚举，歧义时双候选由模型选。新内侧例可得 `3710/7490`，不再由 lo/hi 强推符号。仍需每种 operation 的条件必填约束，不能仅靠可空联合。 |
| 全厚/半厚 | **已修核心问题**。稿:269–275/586 明示 `declared_as_half/half_of_declared_full` 与整除、`WALL_THICKNESS_HALF_UNGRID`。`201` units 拒、`202→101` 可复算；不再因旧实例有二档厚度而说这项没修。 |
| 输入域 | **未闭合**。各 operation 的角色基数没列全，段 ref 与节点 ref 混用，长度差被当局部位置；见下。 |
| 档位递归与同图资格 | **声明与字段不符**。禁止低档参与的原则写了，但没定义该属性从哪个可信记录解析、与当前图/决定怎样绑定；见下。 |

独立原文（E06）：

```text
290:        operand.role == "segment_len" ⇒ 同 cum_lo/cum_hi 的锚点检查
583:DerivedOperandV1:
584:    role: Literal["axis", "half_wall_thickness", "cum_lo", "cum_hi", "segment_len"]
585:    ref:  ArtifactPointerV1
586:    derivation: Literal["declared_as_half", "half_of_declared_full"] | None  # 仅 half_wall_thickness（F-4②）
678:segment_span_diff:     结果 = cum_hi_units − cum_lo_units（同链，允许负值，F-4④）
679:segment_span_sum:      结果 = Σ segment_len_units（operands 索引连续，F-4④）
680:前置：每个 operand 的证据档位 == chain_backed 或 role == 声明常量（F-4③，
```

**输入域的两个确定冲突：**

1. 按稿:285–290，`segment_len` 同样指 `/calibration/x/cum_mm`；:308–311 又只核这些 ref 索引连续。对 `[0,1600,4300,7500]` 取索引 1/2，其“段长和”成了 `1600+4300=5900`，而两段声明长度和为 `1600+2700=4300`。若作者本意是指 `/values_mm`，必须改契约，不能让实现猜测。
2. `4300−1600=2700` 是跨度，不因同源就自动变成主链坐标 `4300`。稿:303 要 diff 的消费方用 direction 声明含义，:255/576 却限定 direction 只给 axis 运算；`TickCandidateV1` 的字段（:636–639）也没有该引用的 direction/原点角色。没有 position 与 displacement 的签名及转换，负值允许与否交给模型仍不能补全坐标表达式。

**档位约束的承重空白：** 稿:67 声称 `operand.evidence_tier` 已收进字段，实际只有上列三字段；:680 的“声明常量”也不在 role 枚举中。单纯补一个可自报 tier 字段同样不是解决办法：需要从冻结的、已认定为本图声明/一档的记录解析资格，或者由受约束的 resolver 返回具备资格的操作数类型。本稿对墙厚 callout 没给该记录/ref 域与解析规则；“不能是测量推断”仍只是判断语句。`source_ref.input_id` 的“天然相同”（稿:305）也没约束 axis 与 half-wall 的全部 refs 必须同属于当前 claim；现有 D2-a 单源检查（:561）只覆盖观测字段。

新字段形状探针接受跨图 `/measured_wall_gap_mm`，只证明**展示的字段**不承载资格；不冒称作者未来守卫已经失效。真正的设计不足是该守卫必须读取什么可信资格、怎么处理角色/基数/来源冲突仍没定义。正文还把所有不满足统一退二档（:291–292），没有区分合法纯像素、可补证的无资格、引用损坏及算术不可表示各自交谁。

**所需改动方向：** 给每种 operation 一个完整签名：精确角色/基数、节点或段的 ref 域、单位、原点/方向、同图资格的解析依据，以及拒绝/回裁/像素出口。档位从可信操作数记录推导，不能从裸数值或角色名字推导。

### R-4 · F-5：B2 范式可以引用，但不能代替“本次认领决定”的绑定

**B2 的实际范式引用已改对三件事：** 闭包持牌、载体只持 artifact 而不带坐标状态、读取时重新过门并从冻结字节推导（稿:335–364；B2 交件:41–56，E08）。B2 已过审合并，这一依据合法，本席不重新否定它。

**本稿要求的是一个更具体的关系。** B2 交件:329–331 明确承认“提供一份能过门的不同冻结字节”会改变推导值，且这是它的信任边界；它保证消费的是有效冻结事实，未承诺这个不同 artifact 必须被判为“并非本次认领决定”。本稿旧 F-5 恰恰要求锁定本次选择，不能直接复用 B2 结论填上这个缺口。

本席独立截取并执行稿中工厂。原文使用：

```text
346:        __slots__ = ("_artifact",)
357:            validate_evidence_bundle(self._artifact.bundle, self._artifact.frozen_sources)  # 门在前
358:            return _derive_tick_claims_from_frozen_bytes(self._artifact)  # 纯函数，永远从冻结字节算
```

现有 API `evidence_contract.py:1239–1241` 只接受一个 artifact 参数，所以原样执行先得到：

```text
EXACT_D6_EXCERPT TypeError validate_evidence_bundle() takes 1 positional argument but 2 were given
```

本席没有靠这个表层错误判“封住了”。仅作参数桥接后，用实际适配器/`finalize_bundle` 构造同源字节、同 input_id、不同 manifest 的两个 bundle，实际 validator 均通过；原文载体允许普通 `carrier._artifact = b`，下一次重读收到 b（E13）。探针只诊断派生函数收到哪个 bundle，**未实现 `_derive_tick_claims_from_frozen_bytes`、未声称改了生产 tick 坐标**。这已足够反证“重过有效性门就封住了跨批次替换”。不涉及反射、提取闭包令牌或修改生产函数。

更根本地，本稿没指明 `_derive_tick_claims_from_frozen_bytes` 从哪里读取**不可改的本次选择**。源 reading 字节只记录候选证据；同一份源、同一边，模型在两个 packet 中选不同候选，源字节不会因此改变。D2 的 `packet_hash/item_id/decision_hash` 和拆出的动作 ID 是需要的字段，但稿:629 只是回指它们，没有给冻结 decision/action 记录的地址、该记录与候选/边/档位/批次的全等绑定。当前 bundle/冻结源形状（`evidence_contract.py:643–687`，E07）本来没有本次 tick 裁决成员，稿中也没定义新增的持久化成员与冻结协议。

**所需改动方向：** 指定第一步完成时冻结的决定清单及身份，涵盖边、候选选择、指针内容、档位、操作数、自动动作实例/模型响应；第二步入口持有独立的预期清单身份，并从它重推导。拒绝另一份虽有效但不属于本次批次的清单。继续复用 B2 的无坐标状态与读取时重推导即可，不必倒退回模块私有令牌。

## 三、四条不阻断 findings

### N-1 · 本稿的数字与自证义务还未按新规则收口

稿:391 正确承认旧探针固定读取旧稿；但没有提供本稿定稿后的机械全扫输出，:774 仍用旧 `170 token` 作为全量依据。本席独立运行新目标扫描（完整输出 `numbers.md`）：

```text
TARGET AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md
UNIQUE_COUNT 168
OCCURRENCE_COUNT 1058
```

不是凭 token 数不同认定领域错误；实质错误包括稿:210 的“所有66条进整体审查”未扣六条有债降档、:393 将四立面 68 边写成 South/East、:504 把旧碰撞反例说成“数值恰好相同”。旧探针本次原文（E15）仍为 `true_boundaries=[4700, 4900]`。另外稿:453–478 只展示四个 probe 子命令，未展示派工单要求的 `capture_evidence.py` 执行记录；`my_counterexamples.py` 未随交件入库，稿:157/456 等路径含省略号。可复跑本席脚本不证明作者当时所有自述；只记证据不足，不推断其未执行或动机。

建议定稿后实扫目标稿、按新分流重算数量，并入库自身反例脚本与缺少的原始命令输出。E11/E13–E16 及本轮两个 numbers 附件支持本项。

### N-2 · D7 与示例 API 的文档同步仍需清理

本席 E11 核出的 `_sorted_bundle:737`、`finalize_bundle:784`、`_payload_row_source_ids:1127`、B4 resolver/入口各行与稿中新定位一致；T4-a 已合并描述正确。这部分旧 N-2 有效闭合。

稿:325/375/410/732 的 B2 待审状态按本轮任务事实已过期，应改为已合并依赖。这里是被审稿文档过期，不是任务前提错。稿:733 的“每个立面 bundle 哈希变”、:734 的“同一批第二次翻搅”也仍扩大到无相关 payload/debt 的 bundle；应限定实际受影响记录，旧裁决:324–348 已点过这个范围问题。D6 validator 参数个数错误（R-4 实跑输出）一并按文档签名同步修正，不另计阻断。

### N-3 · F-3 新门是有效逐点检查，仍需补完整链域

**重点 C 的独立回答：不是第二个“只验总长”。** 新公式逐点访问中间 cum，能拒绝新污染 `[0,900,2450,3600]`；对旧 `7000` 污染也同理。稿:234–239 已具名区分总长门与前缀门，并给 `CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM` 的整链构造拒绝。未验的边到节点语义交 D5/整体把关，像素精度交 reading（:236–237），责任确实具名；前一委托能否满足阶段契约归 R-1，不再算 F-3 重复阻断。

余项是公式 `∀ i` 的完整定义：`len(cum)=len(values)+1`、迭代范围、`cum[0]` 的坐标意义、数值合法域，以及零/负段是否拒绝或另有有向链表示。实际现有门（`evidence_adapters.py:586–601`）没有兜这些条件，reading 的 high/medium/low 也不是该结构守卫。

新输入原文（E13）：

```text
ACTUAL_CLOSED=PASS ZERO_SEGMENT_NEW SPEC_prefix= True len_cum= 4 len_values_plus_1= 4 cum= [0, 900, 900, 2400]
ACTUAL_CLOSED=PASS NEGATIVE_SEGMENT_NEW SPEC_prefix= True len_cum= 4 len_values_plus_1= 4 cum= [0, 1250, 1000, 1900]
ACTUAL_CLOSED=PASS SHORT_CUM_NONZERO_ORIGIN SPEC_prefix= True len_cum= 3 len_values_plus_1= 4 cum= [1800, 2500, 3600]
```

短数组例明确采用自然的 `range(1,len(cum))` 直译；它证明稿子仍容许这种未检查基数的实现选择，**不声称未来实现必然如此**。零/负段是与“正长度尺寸链”不同的域，不能仅凭递推真就保证节点严格有序或唯一。补成闭合的前置规格即可；本轮将它作为不阻断细化项，不继续沿用旧 F-3 阻断。

### N-4 · 颗粒度三处论证已修，但累计稿丢了配套约束

旧 N-4 的三项撤回均认可，用户批准的一档免疫不重开。新稿明确“一档解引用函数不 import snap”（稿:444–446/760），是可检查的局部实现规则；最终装配仍需遵守同段“禁止再 snap”的后置约束，不能又把局部无 import 当整条下游必然不会规整的证明。

本席对照指南的独立输出（E10）还包括：

```text
1273:   ⭐ 改成：判分侧核对的是「**两个分辨率各自被显式声明、且各自被消费**」，⛔ **不是「两个数相等」**。
1275:2. ⭐⭐ **pipeline 出口永远不可能逐位等于 gt**（最大差半格 = 5 mm）
1278:3. ⚠️ **gt 侧的 1 mm 今天【没有落地】**（主控 2026-09-04 实测）：
```

这些配套在上一稿已有，802 行累计稿的颗粒度节:752–761 没有保留对应责任/状态说明；D2 的 `output_precision_ref`（:600）也仍须明确是拟议指向，而现有配置:41/72/80 仍三处声明（E10），不是已完成统一。本轮不要求改 gt 或实现判分，只需补回完整口径与施工责任，且区分原 exact 跨图配对和 gt 判分容差这两件事。

## 四、范围核验、未复现项与交件

**零 src/tests 改动声明：通过。** 本席执行的指定命令及完整原文在 E01：

```sh
git diff --numstat b4f0b348..75f7732a
git diff --numstat 75f7732a -- src tests
git diff --exit-code 75f7732a -- AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md
```

第一条输出仅 11 个 `AI_agent/logs/` 下的证据/评审文件；被审稿行为：

```text
802	0	AI_agent/logs/reviews/execution/2026-09-05f_tick_claim_design_rework2.md
```

后二条均无输出、exit 0。没有将本树的旧源码快照冒充最新主线，也没有为追最新状态进入主工作树写文件。

**未复现/验证边界：**

1. 没有执行未来完整 `WholeBuildingOpeningReviewInputV1`、operand 资格守卫或 tick 决定重建器。tuple/operand 例是字段与关系约束分析；新分流和前缀门为规格直译，均标 `SPEC`。
2. D6 工厂原文确实执行；API 适配单独披露，派生函数只是报告收到哪个 bundle 的诊断桩。结果证明未绑定预期批次，不宣称生产几何已被改写。
3. 没有运行 reading 图像流程、模型裁决、pytest 或端到端；原料扫描及实际 `_nearest`、链门、债处理器、适配器、bundle validator 已执行。没有重新判断真实建筑边的视觉真值。
4. 没有重审 B2/T4-a，也没有重跑主控提供的 3850 全量；B2 的合法性直接采用已核事实，只核本稿有没有正确借用范式及其保证范围。
5. 没有证据独立确认作者历史会话里的“全部复跑”行为；本席完整复跑旧探针及 capture，证明其可执行性。作者反例脚本未交、定稿后数字输出缺失按 N-1 记账。
6. **未触发 A 层。** 初始 HEAD 为指定 `75f7732a`，六边前提重现，所有禁令均未动。旧状态、次要统计与签名笔误按 B 层继续。

**是否改过被审对象：否。** 被审稿、旧裁决、指南、任务书、旧证据目录及 `src/`、`tests/` 均原样保留。预置 untracked 复核单不纳入提交。没有 `pip install -e .`、`git add -A` 或主工作树写入。

分段提交：第一段 `52c1ae17` 已提交本轮探针及原始证据；本裁决与最终核验作为第二段提交。每段提交前检查 `git diff --cached --numstat` 与 `git diff --cached --check`，最终范围核验只允许本轮证据目录和本裁决；补充命令输出见 [final_checks.md](../../experiments/2026-09-05h_tick_claim_crossreview_gpt/final_checks.md)。

**这份稿子现在可以进施工单了吗：不可以。若否，还差的那一件事是什么：把“候选如何成为本次第一步已裁定事实”补成一份闭合的契约——它必须绑定实际链身份、合格运算及冻结决定，并给审查推翻与缺地址补证各自可执行的回裁出口；第二步只能消费该契约确认的本次事实。**
