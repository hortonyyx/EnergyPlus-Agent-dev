REWORK · 阻断 5 · 不阻断 4

# 刻度认领设计稿返工 1 · GPT 跨家族复核裁决

- 日期：2026-09-05；复核席：GPT 家族；作者：Claude 家族。
- 被审对象固定为 `dc886036e058d6382c53167b934ea38e568b62d7` 的 [返工 1 设计稿](../execution/2026-09-05a_tick_claim_design_rework1.md)，不是本席提交后的 HEAD。
- 工作目录：`/tmp/tickrw1_review_gpt`。主线比较对象固定为 `b4f0b348`，仅通过 `git show` / `git diff` 读取。
- 任务：[本轮复核单](../request/2026-09-05e_tick_claim_design_rework1_crossreview.md)；[原任务书](../request/2026-09-04u_tick_claim_design.md)；[上一轮裁决](2026-09-04y_tick_claim_design_crossreview_gpt.md)。指定五份材料已完整读取，其中指南读完 §十四、§十五。
- 三条主控事实直接采用：**一档免疫 10 mm 已获用户同意；T4-a 已合并；B2 返工 3 尚未过审。** 不重新请求拍板，不把待审依赖冒充已通过。

本稿确实补出了派生值联合、区间有序条件、独立响应和颗粒度证书。但独立重算发现：D5 消费的段名本身来自最近邻选择；当前样本已有 **6 条自动一档边无法落到其指定的节点 ref**；D4 的链前置门只验总长；D6 没有把“冻结源字节”与“冻结选中了哪个引用”区分清楚。不能据此发施工单。

证据目录：[独立探针与读法](../../experiments/2026-09-05e_tick_claim_crossreview_gpt/README.md)；[命令与原文输出 E01–E14](../../experiments/2026-09-05e_tick_claim_crossreview_gpt/evidence.md)。下文 `设计稿:L`、`旧裁决:L`、`指南:L` 分别指上述对应文件及 `AI_agent/guides/reading_correction_split_guide.md`；所有行号均由本席 `rg -n` 获取，未采用作者自报定位。证据附件是本裁决组成部分。

## 一、四条复核，各自结论与独立输出

### 1. 上一轮六阻断、两不阻断：原问题确认

**结论：全部确认，保持原问题，不另造一套旧账。** 逐条读取旧裁决 §三、§四及其原反例，原文摘录和本轮闭合状态见 §二。独立命令：

```sh
rg -n '^### [BN]-' AI_agent/logs/reviews/verdict/2026-09-04y_tick_claim_design_crossreview_gpt.md
```

原文输出：

```text
48:### B-1 · 一档契约与 D4 合法域错误收窄为 `cum_mm` 节点
56:### B-2 · D4 失效条件没有列全，且缺少区间级不变量
71:### B-3 · D5-c 确实把未签字判断挤到了“中点分流”
79:### B-4 · D6 还没有在类型/结构层成立
91:### B-5 · §十五的裁决账、阶段隔离与颗粒度消费没有进入契约
104:### B-6 · D7 对两条当前在飞线的描述已过期
115:### N-1 · “每个数字”自查远非全量，且至少两处分类错误
126:### N-2 · D4 把存储格点检查、链成员检查和“整数尺寸”混成了一件事
```

包含各项正文的独立 `rg -n -A 12` 输出保存于证据 E02。这里确认的是旧裁决提出的设计缺陷，不声称重新运行了上一轮全部探针。

### 2. 本稿逐条闭合：一项已闭合，其余有残留或自证不符

**结论：N-2 已闭合；B-1/B-2/B-4/B-5 部分闭合；B-3、B-6、N-1 的全闭合声称与内容不符。** 旧 B-6 的当前残留按本轮非阻断文档更新处理；不是每个旧阻断都自动沿用阻断级别。

独立定位命令（完整输出在 E03）：

```sh
rg -n 'OneTierValueV1|node_ref:|符号由边角色|auto_rule_id:|从每条 claim|B2 已定门' AI_agent/logs/reviews/execution/2026-09-05a_tick_claim_design_rework1.md
```

其中原文输出：

```text
118:OneTierValueV1 = ChainNodeValueV1 | ChainDerivedValueV1     # discriminated on `value_source`
122:    node_ref:     ArtifactPointerV1        # -> /calibration/x/cum_mm/<k>（指认到的节点字节）
210:    auto_rule_id: str      # 指向那次 AutoActionV1 的 rule_id / action_id（wall_compiler.py:333）
275:  - `axis_plus_half_wall`：结果 = `axis_units ± half_wall_units`（符号由边角色 lo/hi 定）。
```

这些引文只证明“稿子承诺了什么”；是否成立的证据来自下面的原料重算、源码门和同形输入，不以承诺充当证明。

### 3. 换同形输入：发现判错、判不出，也确认合法低档出口的边界

**结论：未通过。** D4、D5、D2 三项均做了；没有只重跑 South/East `O01`。

独立可执行命令如下；D5 原稿 `设计稿:325` 的 `python3 -c "... 扫 ..."` 是占位文本，不能作为重跑命令。本席补出了实际扫描器：

```sh
python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py statistics
python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py counterexamples
PYTHONDONTWRITEBYTECODE=1 python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py arithmetic
```

全量统计的原文摘要（[完整 68 边输出](../../experiments/2026-09-05e_tick_claim_crossreview_gpt/statistics.txt)）：

```text
SUMMARY south edges=14 {'1CHAIN-CONSEC': 14}
SUMMARY east edges=26 {'ALL_S1': 2, '1CHAIN-CONSEC': 24}
SUMMARY north edges=16 {'MULTI': 14, '1CHAIN-CONSEC': 2}
SUMMARY west edges=12 {'1CHAIN-CONSEC': 8, 'MULTI': 4}
TOTAL edges=68 signatures={'1CHAIN-CONSEC': 48, 'ALL_S1': 2, 'MULTI': 18} MULTI_agreement={'total': 18, 'numeric_equal_to_map': 18, 'same_symbol': 0}
LITERAL_D5_COUNTS auto_one=66 auto_two=2 model=0 auto_total=68
```

**North 不是全 MULTI。** `O03:x1`、`O04:x1` 只有 `C_bot_fine_s5/s6`；原料 `sm25_north_as_drawn.json:546,550,551,616,620,621` 可直接核。North 的两个像素键 `1524.5/1525.0` 都映到 `14700`（同文件 `:188,193`），已经展示了“同数值”与“同像素键”的区别。

**18 条 MULTI 的各链计算值确实相等；这不等于纯符号同一节点。** 本席读取 `tools/cfg_{north,west}.json` 的各链长度、起点、方向，用 Decimal 精确前缀和复算，才得到 `18/18`。West `O02:x0` 是 `C_top_fine:boundary2` 与 `C_bot_fine:boundary4`，数值都为 `7840`；`O02:x1` 是 boundary3 与 boundary7，数值都为 `12160`。不可能仅靠段索引相等得出同指。**精确数值比较本身没有违反零阈值；缺的是完整源映射及同一坐标系证明。** 详见 F-2。

同形输入的逐项裁定：

| 输入（均非作者原例） | 按稿中判据会发生什么 | 本席裁定 |
|---|---|---|
| 无尺寸标注的洞位于中间一段，两边像素 `620/870`，附近刻度 `500/1000` | producer 分别给相邻段证书，D5 自动一档；两值严格有序，D4 也绿 | **判错**：最近邻仍在替“有没有该洞刻度”作判断，F-1 |
| 有直接证据指向链原点的边，refs 全 `_s1`、像素正落原点 | D5 自动二档 | **错误降档**；`ALL_S1` 不能证明无可认领刻度，F-1 |
| 两条闭合链在同一像素键相遇，内部节点分别 `4700/4900` | 扁平 map 后写覆盖前写，refs 却同时保留两链 | **依稿判不出可靠同指**；若据扁平值当同指则判错，F-2 |
| 同一图上两条链算出同值 `4200`，但 ref 身份不同 | D4 可以复算两个值，不能裁定节点同一性；D5 未定义跨链等价关系 | **数值可定，来源裁定不完备**；不能用“值唯一”替“证据唯一”，F-2 |
| 改 South 中间 cum 为 `7000`，保留各段、总长与末节点 | 现有前置门通过，边差 `1730`，被引用段仍为 `1800` | **判错**：污染链被当干净前提，F-3 |
| 两个不同 cum 索引同为 `5000`，总长仍闭合 | 前置门通过；两边若取同值可由区间门拒，但单边节点来源歧义仍在 | **新增区间门有效，链资格门不充分**，F-3 |
| 分段相减得到 `lo=-400, hi=100` | 引用可解、重算正确、有序、宽 `500`，全绿 | **不能仅凭负值判错，也不能证明合法**；未给出带原点/方向的坐标域与差值用途，F-4 |
| 洞口位于两轴线内侧：轴线 `4000/8000`、墙厚 `200` | 所需边为 `4100/7900`；按例中 lo 减、hi 加会得 `3900/8100` | **单靠 lo/hi 无法定加减号**，F-4 |
| 轴线 `4200` 为一档，半墙厚 `115` 来自二档测量 | refs 可解、角色齐、`40850` units 可精确复算 | **没有具名证据资格拒绝或降档规则**；仅按两道检查会冒升一档，F-4 |
| refs 残缺或 nearest 与可解析链节点冲突 | D5-b 进入模型；模型明确 reject_all 后，存在真实像素 ref 时走 PixelOut | **这条如实二档出口在设计上成立**；没有把缺证据一律叫债 |
| ②b：有该立面文件，但没有这条洞口 observation | D2-a 的对应行不存在；一档、二档都缺 evidence_ref | **装不下；没有具名排除规则；不能声称已静默落二档**，N-3 |
| ③：该方向根本无立面，只有平面或第二步推测 | 连 D2-a 的 artifact 都没有，`auto/model` 又不是“观测/推测”来源域 | **装不下；没有具名排除规则；不能混成 pixel_only**，N-3 |

实际源码探针的原文输出（不是拟议校验器的执行结果）：

```text
IMPORTED /tmp/tickrw1_review_gpt/src/agent/correction/evidence_adapters.py /tmp/tickrw1_review_gpt/src/agent/correction/opening_synthesis.py
INTERIOR_CUM_CHANGED require_chain_closed=PASS lo_mm= 7000.0 hi_mm= 8730.0 width_mm= 1730.0 declared_segment_mm= 1800.0
DUPLICATE_NODE_VALUE require_chain_closed=PASS cum_indices_1_2= [5000.0, 5000.0]
GRID_6925 69250
GRID_NEGATIVE_400 -4000
NESTED_POINTER_ASSIGNMENT /calibration/x/cum_mm/2 -> /calibration/x/cum_mm/3 model_config= {'extra': 'forbid', 'strict': True}
```

`counterexamples.txt` 后半标明是**契约构造分析**，没有把打印的分析结论包装成生产测试通过。只有 `_nearest`、`_require_chain_closed`、格点转换、`ArtifactPointerV1` 调用了当前代码。

### 4. 零 src / tests 改动声明

**结论：通过。** 本席原样运行：

```sh
pwd
git rev-parse HEAD
git diff --numstat ac9a0669..dc886036
git diff --numstat dc886036 -- src tests
```

开工原文输出：

```text
/tmp/tickrw1_review_gpt
dc886036e058d6382c53167b934ea38e568b62d7
373	0	AI_agent/logs/reviews/execution/2026-09-04u_tick_claim_design.md
480	0	AI_agent/logs/reviews/execution/2026-09-05a_tick_claim_design_rework1.md
495	0	AI_agent/logs/reviews/verdict/2026-09-04y_tick_claim_design_crossreview_gpt.md
```

最后一条 diff 无输出，exit 0；被审区间只有三份 Markdown，无 `src/`、`tests/` 改动。末尾再核本席改动范围。

## 二、旧六阻断、两不阻断逐条闭合表

| 旧项与原文（不改写原问题） | 本轮状态 | 本稿独立定位与验证结果 |
|---|---|---|
| B-1，旧裁决:52：“两边是链派生事实，却未必是 `cum_mm` 节点。当前 schema 既没有封闭运算表达式，也没有位置容纳多个操作数及其 ref。” | **部分闭合** | 设计稿:118–133 有联合、角色和证书；但 node_ref 仍只指主链，当前 6 条非主链边无法构造；派生签名不能确定加减与资格。见 F-2/F-4。旧例 2550/3450 的“半洞宽”也不能直接冒充 `half_wall_thickness`。 |
| B-2，旧裁决:61：“它只证明‘选到两个链节点后能得到连续段和’，不证明这两个节点界定该洞，也不覆盖合法的链派生边。” | **部分闭合** | 设计稿:294–301 已补塌缩、反向、有序、非零宽；这些改动有效。新反例证明它委托的链前置门没有保证中间前缀和；派生边仍有不确定输入。见 F-3/F-4。 |
| B-3，旧裁决:73：“它不是固定毫米常量，但仍是一个未签字的相对判断阈值：相邻 tick 间距的 1/2。” | **声称与内容不符** | 设计稿:309、332–348 删除了本地中点式，却把同源最近邻产物当语义证书；实际 producer:66、174、178 仍执行最近邻，换中间段输入照样判错。见 F-1。 |
| B-4，旧裁决:87：“‘没有坐标字段’并未冻结决定。” | **部分闭合** | 设计稿:365–369 增加封印方向，优于上一稿；仍只限制新建载体，未封住嵌套 ref 的内容与本次第一步裁决。实际 ArtifactPointer 可赋值，见 F-5。 |
| B-5，旧裁决:93：“只记录结论和证据，不记录该结论来自哪个 `AutoActionV1` 或哪个 packet/response/item decision”；:95 点名二档颗粒度及一档冲突 | **部分闭合** | 设计稿:149–152 的 PixelOut、:242–252 的独立响应、:391–394 的分档出口已补；用户已批准免疫。:210 的 rule_id/action_id 二选一语义未消歧，也未绑定冻结的自动动作实例；跨图 operands 未限制，见 F-4/F-5。推导文字另见 N-4。 |
| B-6，旧裁决:109：“施工必须排在 T4-a 返工 2 合并并过审之后，重基线后保持其 resolver/binding 与 `affected_refs` 锁。” | **声称与内容不符** | 设计稿:406 已识别碰撞面，:407 正确保留 B2 待审条件；但当前 T4-a 已合并，D7 仍用待审状态及旧位置。按 `b4f0b348` 全节复核见 N-2。 |
| N-1，旧裁决:117：“漏了数据数组、距离、反例数、分支估算、日期/版本/源码行号等大量数字。” | **声称与内容不符** | 设计稿:437–439 已改正旧 cutoff、估算、示例的身份；但:435 把“66 自动”当派工方观察，仍错，且缺少派生/规整数字。独立全扫 170 token，见 §五。 |
| N-2，旧裁决:128：“`grid_units`/`grid_units_from_mm` 只证明值在 0.1 mm 存储格点上；它不会证明该值属于某个 `cum_mm` 集合。” | **已闭合** | 设计稿:272–280 明确拆两道检查并收回整数尺寸普遍化；本席实跑 `grid_units_from_mm(6925)=69250`。其他 D4 新问题不倒算成这条措辞未修。 |

## 三、阻断 findings

### F-1 · D5 的“结构证书”是最近邻选择的产物，旧判断被搬到了输入侧

**现象：** 无标注的中间段洞口也会自动一档；正确指向原点的边却会被 `ALL_S1` 自动降二档。East `O01` 原例修好，不代表这一类修好。

**可复现证据：** 设计稿:332–333 给出两个自动分支；证据 E06 的独立 `rg -n` 原文为：

```text
63:def _nearest(ticks: list[float], px: float) -> tuple[float | None, float]:
66:    t = min(ticks, key=lambda v: abs(v - px))
90:            tick_map[world][str(round(px, 1))] = c["world_start_mm"] + c["direction"] * cum
91:            here = refs[world].setdefault(round(px, 1), [])
93:                here.append(f"{cid}_s{k}")
95:                here.append(f"{cid}_s{k+1}")
174:            t, d = _nearest(tk, px)
178:                             "dimension_refs": refs[pool].get(round(t, 1), []) if t is not None else []}
```

文件是 `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/as_drawn_elev.py`。这说明 refs 是“所选最近刻度两旁有什么段”，不是“尺寸标注定位了这个洞”。执行该文件实际 `_nearest` 的新输入输出：

```text
NEAREST_COUNTEREXAMPLE chain_origin_edge px=0.0 nearest=0.0 distance_px=0.0 signature=ALL_S1 D5=auto_two value_mm=0
UNLABELLED_MIDDLE_INTERVAL raw_px=[620,870] picked_px=[500.0, 1000.0] signatures=['1CHAIN-CONSEC', '1CHAIN-CONSEC'] D4_order_pass=True
UPSTREAM_HIDDEN_MIDPOINT_PX 750.0
```

后一个洞的两边仍在同一个未给洞口刻度的中间段内，producer 却分别附上两个内部节点的相邻段名；D5/D4 合起来会接受整段作为洞宽。隐含的半间距边界仍在 `_nearest` 内。另有上游 `round(px,1)` 的像素键合并，不能冒称没有任何数值处理。

**病根一句：** 用最近邻选择的结果证明最近邻选择具有建筑语义，证据与待证结论来自同一次选择。

**建议方向：** 区分测量候选、节点拓扑、边到节点的认领依据；自动分支只消费足够支持认领或明确无标注的证据，其余进入模型判断。不能把 `_s1` 的序号身份当“没有尺寸标注”证书，也不能给最近邻再套一个容差。

### F-2 · 多链的源映射没有进入契约；当前已有 6 条边无法构造指定 node_ref

**现象：** D5 明令自动一档为 `chain_node`，D2:122、145 却只允许 `/calibration/x/cum_mm` 节点/段。该数组只保存 primary chain；其他链的值不能借同数值查表自动取得该节点身份。

**可复现命令：** 全量扫描后执行：

```sh
rg -n 'primary_indices=\[\]' AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/statistics.txt
```

原文输出：

```text
4:  O02:x0 1CHAIN-CONSEC refs=['C_bot_fine_s2', 'C_bot_fine_s3'] px=1013.5 mapped_mm=8640.0 chain_values={'C_bot_fine:boundary2': Decimal('8640')} primary_indices=[]
5:  O02:x1 1CHAIN-CONSEC refs=['C_bot_fine_s3', 'C_bot_fine_s4'] px=1309.0 mapped_mm=12640.0 chain_values={'C_bot_fine:boundary3': Decimal('12640')} primary_indices=[]
8:  O04:x0 1CHAIN-CONSEC refs=['C_bot_fine_s4', 'C_bot_fine_s5'] px=1362.5 mapped_mm=13360.0 chain_values={'C_bot_fine:boundary4': Decimal('13360')} primary_indices=[]
9:  O04:x1 1CHAIN-CONSEC refs=['C_bot_fine_s5', 'C_bot_fine_s6'] px=1657.5 mapped_mm=17360.0 chain_values={'C_bot_fine:boundary5': Decimal('17360')} primary_indices=[]
72:  O05:x0 1CHAIN-CONSEC refs=['C_top_fine_s4', 'C_top_fine_s5'] px=1595.5 mapped_mm=14540.0 chain_values={'C_top_fine:boundary4': Decimal('14540')} primary_indices=[]
73:  O05:x1 1CHAIN-CONSEC refs=['C_top_fine_s5', 'C_top_fine_s6'] px=1683.5 mapped_mm=15740.0 chain_values={'C_top_fine:boundary5': Decimal('15740')} primary_indices=[]
```

前四行为 South，后二行为 West。原料定位：`out/sm25_south_as_drawn.json:205–208`；`out/sm25_west_as_drawn.json:187–188,727–738`；完整路径前缀同 F-1。不是假想“换张图才会发生”。若强制 D2，认领无法构造；若静默换主链邻点则错值；若改成 `chain_derived` 或指向 witness map，已改了 D5 分支/节点引用定义，稿中没有规定这条路。

多链“同指”也不能从扁平表独立核：`as_drawn_elev.py:90` 每个像素键只留一个值，`:91–95` refs 却累积所有链。构造两条总长均 `10000` 的链 `[4700,5300]`、`[4900,5100]`，让内部节点同落像素键 `400.0`，得到：

```text
RASTER_COLLISION refs=['C_A_s1', 'C_A_s2', 'C_B_s1', 'C_B_s2'] signature=MULTI flattened={'400.0': 4900} true_boundaries=[4700, 4900]
```

从输入表复制两次 `4900` 再比较，不是在核两条链。若按独立 cfg 前缀和比较可发现分歧，但 cfg 没有被 D2 收进冻结证据契约。North/West 当前同值只是本席用额外源复算出来的观察，不是 `dimension_refs` 字符串本身的性质。

**病根一句：** 把多链的节点来源、坐标系和等价关系压成一个数值查找表，后续却要求它提供完整来源证明。

**建议方向：** 先明确各链与段/节点的冻结源定位、坐标系和跨链精确等价条件，再定义自动分流及结果引用。数值相等可作精确检查，不能替代节点身份；合法非主链节点必须有确定出口。

### F-3 · D4 把“链总长闭合”当成“所有 cum 是干净前缀和”

**现象：** 设计稿:298、301 将污染链交给 `_require_chain_closed`，:287 的恒等式却需要每个中间 cum 都是段长前缀和。两者不是同一个性质。

**可复现证据：** E08 对 `src/agent/correction/evidence_adapters.py` 的独立行号输出：

```text
595-        total = sum(values)
596-        if total != cum[-1] or cum[-1] != overall:
```

函数 `:564–606` 只做基本形状、段数值类型及总长/末节点相等检查，未逐节点核前缀和、节点个数或中间有序。`probe.py arithmetic` 实际调用该门：把 South `cum[2]` 改为 `7000`，总长不变，门仍 PASS；认领 `[7000,8730]` 后区间严格有序、宽 `1730`，但原声明段仍为 `1800`。再令两个 cum 索引都为 `5000`，该门仍 PASS。原文见 §一.3 / `arithmetic.txt:2–3`。

**病根一句：** 前置门测的是总长代理量，设计的成立性证明依赖的是逐节点前缀和事实。

**建议方向：** 在设计中补齐“哪些链事实先被精确验证、失败交给谁”的前提；区分总体闭合与节点/段一致性。这里不是要求本席改现有函数，也不是宣称零阈值不可能做到。

### F-4 · chain_derived 的运算签名与证据资格未封闭，精确重算不能证明一档

**现象与引文：** 设计稿:126–133 只有操作枚举、角色和裸 ArtifactPointer；:272 接受 `cum_lo/cum_hi` 或“一组 segment_len”，:275 把符号交给 lo/hi。仍缺下列决定契约含义的约束：

1. **加减方向不由 lo/hi 唯一决定。** 外侧边与两墙内侧洞边的合法方向相反。`4000/8000` 轴线、`200` 墙厚的内侧边须 `4100/7900`，不能复用稿中 lo 减半厚的固定解释。需要反映几何关系的运算选择依据。
2. **墙厚 ref 指全厚还是半厚不一致。** :133 说指“声明墙厚”，:178 的例子引用 `240` 后取一半，:275 却直接使用 half_wall_units；未声明除二资格、半格不可表示时的出口。
3. **分段和/差的输入域不封闭。** :272 允许 diff 配一组 segment_len，但 :276 公式只取 cum_hi/cum_lo；sum 配两个 cum 时 :277 又只对 segment_len 求和。没有规定次数、段序、连续性、原点或差值何时能成为局部 x。负差 `[-400,100]` 本身不是普遍非法，但稿中没有足够信息判定它在这张图上的合法性。
4. **证据档位与同图约束没有递归到操作数。** :107 只约束原始 x 的五个 ref 同源；:301 只要求两条边的 evidence input_id 相同。另一个图的节点、或者 `pixel_only` 墙厚值也能满足“ref 可解、角色齐、证书算得对”。两道检查没有声明墙厚必须是图上声明/已裁定可用证据，也没有定义低档操作数的档位传播。

**可复现依据：** E03 保存上述逐行原文；`counterexamples.txt:9–12` 记录新输入和按纸面公式的推演；`arithmetic.txt:5` 实证负数也属于现有 0.1 mm 算术域。指南 `:1038,1096,1141,1166` 分别要求链派生、只用本图声明数、逐图独立及档位权威，不能仅凭有冻结字节就满足。

**病根一句：** 运算结果可复算只证明算术一致，不能证明操作数有资格、表达式有唯一含义、结果属于本图一档证据。

**建议方向：** 补齐每种封闭运算的角色/基数/方向/坐标系签名及操作数证据资格；明确无资格、表达不出与纯像素三种情况各自的具名出口。模型仍只选择代码枚举的决定，不新增坐标输出。

### F-5 · D6 限制了构造，却未把引用选择与第一步裁决一起冻结；B2 不能代证

**现象：** 设计稿:365–366 限制新建 wrapper/元素；:367 从“每条 claim 的冻结 ref + 裁决账”重建。但它复用的 ref 本体是可赋值的 Pydantic 对象。**源字节不可变，不意味着指向源内哪个节点的指针不可变。** 换指针内容无需新建 claim、无需改任何坐标浮点。

**独立可复现证据：** `src/agent/correction/evidence_contract.py:170,190,199` 定义 `_CFG={extra=forbid,strict=True}` 及 `ArtifactPointerV1.json_pointer`，没有 frozen。本席用实际类型正常构造 ref，然后正常赋值：

```text
NESTED_POINTER_ASSIGNMENT /calibration/x/cum_mm/2 -> /calibration/x/cum_mm/3 model_config= {'extra': 'forbid', 'strict': True}
```

这是**现有被引用类型的运行事实**，不是声称已执行了尚不存在的 `SealedTickClaimsV1`。在拟议契约中，若没有额外的递归不可变表示或对原裁决的独立绑定，同一个受封元素的 `node_ref.json_pointer` 就仍可换节点；#3 跟着新 ref 重读冻结字节会得到另一个同样精确的值。即使加 hash，若第二步可接受重新生成的索引/hash，也没有证明它仍是本次第一步交来的决定。

**裁决账没有补足这个锚点。** 设计稿:210 的 `auto_rule_id` 允许解释为 rule_id 或 action_id；实际 `wall_compiler.py:324,333` 是两个不同字段，同规则可产生多次动作。:325–330 的 AutoAction.kind 还是四种墙语义，未包含自动刻度认领；稿中只扩了 OpenItem.kind。`rule_id` 不能唯一定位本次 action、更不能独立锁住本次选定的节点/档位。模型分支有 packet/item/decision hash 的方向正确，但还须说明重建时如何核它与候选、边、裁决结果的绑定。

**三条叠加后仍需明确的第二步外延：** 可以选取/舍弃已经冻结的事实；不得改同一事实的嵌套 ref、tier、来源、所隶属的图/裁决批次。当前 #1/#2 只回答“谁能新建”，#3 若从可变索引出发，只回答“这个新索引还能否算出一个数”。这两问尚未推出后一条不变量。

**B2 依赖核查：** D2/D3 没有直接调用 B2 API，也没有证据表明它们已把 B2 实现接入；:371、407 等过审的条件正确。问题在 :19、470、480 又把 D6 写成已闭合/“B2 已定门”。本席读取 `b4f0b348:AI_agent/logs/reviews/execution/2026-09-04w_B2_rework3_execution.md:30–59`：实际交件采用 **闭包持牌 + 仅存 artifact、每次消费重新过门派生**，不是本稿描述的“模块私有令牌 + 逐元素受封”三件现成套件。它仍待审，本席不代批，也不以它的自述证明封印有效。

**病根一句：** 构造许可、来源字节完整性和“本次第一步究竟裁了什么”被合并成同一个冻结承诺。

**建议方向：** 指定第二步从哪个不可改的本次裁决记录重建，封住索引本身的改变和跨批次替换，给自动动作唯一实例绑定；明确 B2 最终模式只是待审依赖及复用条件，不能替本契约提供完成证明。不涉及运行时反射等范围外问题。

## 四、§十四 / §十五逐条 delta 核对

依据 E05 的独立行号及完整章节阅读；同一根因不重复计阻断。

| 权威条目 | 本稿对齐程度与 delta |
|---|---|
| §14.1 / §15.1，决定归模型、坐标归代码（指南:1006,1125） | ref/候选 ID 路线保留；D3 新响应无坐标字段的方向正确。不能把 hash/id 内可含数字理解成“字段树构造不出任何数字”；应保持“不能回坐标”的准确范围。 |
| §14.2 / §14.2b / §15.4，链优先、节点或链派生、两档都出值（:1015–1039,1166–1173） | 联合与 PixelOut 已补；非主链定位仍收窄，证据档位未随 operands 校验，F-2/F-4。两档结果在类型上都保留，不判为“没有二档”。 |
| §14.3，两侧职责不对称（:1061–1067） | 立面负责尺寸、平面负责身份的方向未改变；本席不把平面所有端点强钉到链上。没有要求用同一输入类型完成两侧不同职责。 |
| §14.4 / §15.5，四分类、立面优先、②b 登记、③ 推测且不计成绩（:1073–1076,1177–1184） | 本稿不做第二步符合原任务边界。D2 两档不能装②b/③，需要明确输入域和具名不适用，N-3；不要求扩参考表或本轮实现四分类。 |
| §14.5 / §15.8，目标态与现状分别标记（:1081–1087,1217–1223） | D1 对被审 commit 的裸 dict 路径、零生产调用者独立复现，E07；D7 必须使用指定当前主线，N-2。指南旧状态标签不是本轮施工完成证明。 |
| §14.6，第一步只用本图画出的数、零建筑先验（:1096–1099） | 本稿没有新增模数参考表；但 refs 能解不能代替“本图声明/已裁定可用”，F-4。 |
| §14.7 / §15.6 / §15.11，表示、gt、pipeline 三个数各归其位（:1105–1112,1265–1267） | `0.1/1/10 mm` 身份抄对；PixelOut 明确 pipeline 声明引用；一档免疫由本轮主控事实直接成立。现有配置仍三处声明，不能把拟议 ref 写成已完成单一声明点，N-4。 |
| §15.2，每笔输入 provenance + refs，输出裁决账（:1131–1132） | 模型分支有 packet/item/decision hash；自动分支 rule/action 未消歧；输入墙厚等档位尚未消费，F-4/F-5。 |
| §15.3，两步各三拍、第一步逐图独立（:1141–1146） | 独立 response 的 whole_building_review 隔离已补。仍需同图 operands/packet 范围约束；本图重检失败回②的有限轮出口未具体交代，不能把 D4 红一概降二档。由 F-1/F-3/F-4 的失败处置一起收口。 |
| §15.5，第二步原 exact 配对不改（:1177） | 本稿拟改变喂给 B4 的值，不主张放宽配对门，符合。B4 接口迁移是未来施工，本席没有执行。 |
| §15.7 / §15.9 / §15.10，判断不转成确定性毫米门；F 组只作模型数据参考（:1194–1211,1231,1299–1304） | 未新增 F 组三阈值或参考表机制；但 D5 仍继承最近邻半间距判断，F-1。模型不能判时应保留合法出口，不可把未决、无立面都译成二档，N-3。 |
| §15.11 三条必须同执行的推论（:1271–1286） | :394 已补“分别声明/分别消费”和半格比对，旧遗漏已修。gt 1 mm 尚未落地属于另一条施工线，本稿不能当完成；不要求本席动 gt。论证的外延过宽见 N-4。 |

## 五、不阻断 findings 与数字机械扫描

### N-1 · 全量数字自查仍有遗漏，“66 自动”分类错误

**独立扫描命令：** `python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py numbers`。正则与上轮相同：`\d+(?:\.\d+)?(?:e[+-]?\d+)?`，逐次记录行号。[170 个 token 的全部原文输出](../../experiments/2026-09-05e_tick_claim_crossreview_gpt/numbers.txt)已入库。

```text
UNIQUE_COUNT 170
OCCURRENCE_COUNT 948
```

相对于稿中分类表，**41 个 token 没在表中出现**。不是把每个定位符漏列都当领域错误：日期、章节、行号可由类别概括。需要补清的有实际单位换算、示例运算和规整结果：`6.9219/8.7512/0.5367/2.1646`、`30000/1200/28800`、`540/2160`、`1700/9700`、`1935/1940`，以及分布计数 `14/24/26`。这些不能全说成“图纸原声明值”。

本席按上下文重分以下全部身份；同 token 可跨行具有不同身份，完整出现定位见附件：

| 数字身份 | 独立判定及例子 | 抽查证据 |
|---|---|---|
| 已签字量 | `0.1 mm` 表示、`1 mm` gt、`10 mm` pipeline = 声明值 | 指南:1265–1267；`opening_synthesis.py:130,133`；配置:41,72,80，E08/E14 |
| 原料数组/测量 | South/East cum 全数组、16 段、原始 x 数、distance、`≈13.6`、原宽 = 观察/声明；不是自动认领判据 | `probe.py statistics` 全扫各原料；South `O01` 的两 refs/值在输出:2–3，East 输出:18–19 |
| 规则运行结果 | `66 自动` 不等于派工方的“66 距离≤34”；是**作者分流规则的计算结论** | 原任务书:32 的 66 测的是距离；设计稿:435 换成自动数量。照 D5 文字应为 66 一档 + 2 二档 = **68 自动**，且另有 6 条 node_ref 不成立 |
| 统计判断 | `≤34 mm` = 既有经验判断；`0–1/立面` = 作者估算 | 设计稿:437 已改前者、:435 已改后者；这两处旧错已修；不能由当前零模型边推保证其他图的模型调用数 |
| 作者构造 | `6925`、`3000 ±120`、`240`、`2880/3120` = 示例；`30000/1200/28800` 是该示例的单位换算/算术派生 | 设计稿:174–178,280；实际格点转换 `arithmetic.txt:4`，不是图纸提供的这些例值 |
| 规整与运算产物 | `540/2160` 是声明格点消费结果；`1800/8000` 在差式中是算术结果，在 values 原料中才是声明；`1935/1940` 是权威反例输入/示意规整输出 | 设计稿:172,186–187,321,379；指南:1233–1235。不把例子用的舍入绑成新的未声明 tie 规则 |
| 隐含数值边界 | `1/2` 不在 D5 本地比较式，但仍控制 producer 最近邻的前像；像素键还有 `round(px,1)` | `as_drawn_elev.py:66,90–91,174–178`；F-1/F-2 |
| 结构计数/类型 | `V1/V3`、档位、x0/x1、下标、四字段、三动作、五 effect、Hex64 = 类型/结构标识 | `evidence_contract.py:190–200`；`decision_schema.py:220,247–295`。CodeToken 禁止数字字符；另有既有长度 `1..96`（:131），不能把“无数字”读成“无长度约束” |
| 定位/历史身份 | 日期、commit 的数字片段、D/B/N/R/T/F/O/sm 编号、章节/源码行号、旧稿373行、提交3次 = 定位/自述计数 | 全部由 `numbers.txt` 定位。仅扫 token 不证明这些位置真实，D1 与 D7 分别以 E07/E12 复核 |

已抽查超过要求的五个数字/类别。`0.1/1/10`、South 差式 `1800`、North `8000`、`≤34`、`0–1`、`6925`、`66 自动` 均有独立源码/原料/算术依据。**本轮不是因为机械漏列41个 token 而阻断；承重错误是 F-1/F-2，“全量且无判断”自证需撤回重写。**

### N-2 · D7 按 b4f0b348 全节复核：4/5 风险行有过期内容

按**风险行**计：R1/R4 的状态与排期逻辑过期；R3/R5 的源码定位过期，共 **4/5 行**。R2 待审状态正确。B2 实际交件形态与本稿借用描述的差异归 F-5，不冒称 B2 已过审。

| D7 行 | 当前主线核验结果 | 应更新内容 |
|---|---|---|
| R1，设计稿:406 | `b4f0b348` 已包含 T4-a；resolver `:481`、出口核验 `:609`、binding `:705`，源绑定 `:749` | “已交件待审/未合并”撤下；改为基于已合并代码保护现有出口检查及锁，不能仍按旧 :338–365/:513–524 定位 |
| R2，:407 | plan:406 仍待审；实际交件为闭包 mint + artifact 重派生 | 保留待审复用条件；附实际交件而非只读返工单。D2/D3 无 B2 API 依赖，但验收:470/:480 不能以它证明闭合 |
| R3，:408 | `_sorted_bundle:737`、`finalize_bundle:784`、`_payload_row_source_ids:1127` | 更新旧 :713/:760/:1103；x/witness 入 dump 会影响相应非空 payload，保留基线重生成/源闭合核验要求，不把“每个”扩大到无洞口记录的 bundle |
| R4，:409 | `EvidenceDebtV1.obligation` 已存在于主线 :539；hash 迁移已是基线组成部分 | 后续只按当前基线计算 x 增量影响；不再写与 T4-a 在飞并发翻两次。无 debt 行的 bundle 也不能仅因类型新增字段就断言 hash 必变 |
| R5，:410 | B4 仍裸 dict，`_elevation_openings:956`、`synthesize_openings:1009`；docstring 当前 `evidence_contract.py:568` | 改输入风险与 docstring 依赖纪律仍对；更新旧 :544 的当前定位 |

独立命令与输出在 E12。核心原文：

```text
b4f0b348 09.05b_wrapup_fourth_leg (opening-alignment doctrine ratified; T4-a merged; suite 3819)
bfd6419a 09.05a_merge_T4a_obligation_field (GLM cross-review APPROVE / 阻断 0 / 不阻断 3)
539:    obligation: DebtObligationV1 | None
737:def _sorted_bundle(bundle: CorrectionEvidenceBundleV1) -> dict:
784:def finalize_bundle(
1127:def _payload_row_source_ids(member: str, row: object) -> set[str]:
481:def redemption_row_for_obligation(obligation: str) -> tuple[str, DebtRedemption]:
609:def _resolve_backed_obligation(obligation: str) -> tuple[str, DebtRedemption]:
705:def redeemable_debt_ids(
749:            executed.source.binds(ref) for ref in debt.affected_refs
```

当前新增锁也已读取定位：`b4f0b348:tests/test_t4a_rework1_resolution_lock.py:606,670,689` 分别覆盖 seam 扩大、域外 obligation、查询侧 str 子类。这里只确认应保护的改动面，没有重跑这些锁、没有复审 T4-a。

### N-3 · ②b / ③ 装不下是合理范围边界，但还没有具名边界出口

原任务书:69–70 明确本稿不做第二步四分类；**不因没有实现②b/③判阻断**。本轮仍按要求套了 D2：`evidence_ref` 必须回 D2-a 的立面洞口行，PixelOut 也必须有原像素 ref。②b 缺这行，③ 缺该立面 artifact，均无法形成有效 claim；把 `tier` 改成二档并不能补出缺失证据。`provenance=model` 只表示谁裁定，不能替代指南要求的“来源=推测”。

独立负向检索（E11）：

```sh
rg -n '②b|只有平面|平面有立面无|推测|plan_only|unsupported|OUT_OF_SCOPE' AI_agent/logs/reviews/execution/2026-09-05a_tick_claim_design_rework1.md
```

输出为空，exit 1。结合设计稿:138,150,206–216 与指南:1075–1076，裁定为**输入域不适用但未定义具名处置**，不是已证实的静默降档漏洞。建议写明本类型只承载本图实际观测边；不存在的立面边进入第二步登记/推测的独立载体，禁止以缺失 ref 伪装二档。本轮不补参考表、不写四分类实现。

### N-4 · 一档免疫的决定已成立，但“由旧条文唯一推出”的论证写过头

**结论不重开：免疫已获用户同意，正确。** E12 独立读取 `b4f0b348:AI_agent/plan.md:428`，原文：

```text
428:| **A-2** | ⭐ **出口格点【免疫一档】** | 用户同日拍「同意」 | 防「10 mm 格点把 `1935` 碾成 `1940`」= 用格点产物覆盖图纸真值 |
```

需要修的是三个推论，不是重新请用户同意：

1. 设计稿:384 说 `1940` “既不是链节点，也不是任何链运算的结果”不普遍成立；若同一链有节点 `[0,1935,1940]`，1940 本身就是另一节点。真正被破坏的是**这一条边已裁定取1935的事实**，不是抽象链成员资格。这个反例也是 F-5 必须冻结引用选择的原因。
2. :385 将 §15.11 的“pipeline 出口”推成该节“都是关于二档/像素”，指南终裁表 `:1266` 本身没有这个限定。应引用后续 A-2 的明确分档豁免，而非改写旧终裁的语义后声称“非新决策、唯一自洽”。
3. :391 “无坐标字段 ⇒ 天然不过 snap”不成立。代码解引用后依然可以 snap；实际消费位置 `deterministic.py:282,349,390,1247` 已经说明规整发生在代码端。契约明确免疫是正确要求，必须在后续出口消费处兑现；同理 `output_precision_ref` 是拟议引用，不代表配置的三处声明已统一。

证据命令及原文在 E04/E14。建议按“已批准的分档政策 + 保持每条已裁定事实 + 出口明确消费/不消费”的关系重写推导，不把链成员存在性或没有 float 字段当证明。

## 六、未复现项、边界与改动声明

1. **没有运行 pytest、端到端或模型调用**。本单为设计审；实际运行范围已在 §一.3 列清，未把构造性推演报成拟议实现通过。
2. **未实现、未执行拟议 D2–D6 类型/校验器**，它们尚不存在；D6 ref 可赋值只针对稿中复用的现有类型，不宣称运行了未来 wrapper。F-4/F-5 是当前设计不足以推出不变量的证据。
3. **未重跑图像 reading 生产流程**；全扫其已冻结原料，并执行独立 `_nearest` 及本树实际算术/前置门。MULTI 值比较额外读了各 cfg，已明确披露，不冒称来自 D2 的现成证据。
4. **未运行或批准 B2 待审实现；未重跑 T4-a 全量锁**。通过指定主线的源码和交件只读核 D7 状态/碰撞面。
5. **未读写 gt，未实现第二步四分类，不判建筑图纸实际洞口真值**。②b/③仅用于检验该 schema 的适用边界。对派工方“66 近刻度”的距离 cutoff 未另行重算中位数；本轮重算的是所要求的全量结构签名与各链值。
6. **没有触发本复核单 §六 A 层。** 初始 commit 匹配，三条主控事实按已核前提采用，未碰禁区。North“全 MULTI”是被审稿自报统计的误差，按 B 层记账继续，不误判成复核单前提错误。

**是否改过被审对象：否。** 未改设计稿、旧裁决、指南、任务书、`src/`、`tests/`。仅新增本裁决及独立证据目录；预置 untracked 复核单原样保留。未进入 `/workspaces/EnergyPlus-Agent-dev` 写文件，未安装依赖，未用 `git add -A`。

分段提交：`9728ad97` 提交探针/命令证据；`097b1f01` 提交四份原始输出（仓库通用 txt 忽略规则下逐文件显式加入）；本裁决单独提交。复核对象始终固定为 `dc886036`，本席提交不改变被审版本。

裁决写完后的独立范围核验：

```sh
git diff --check
git diff --numstat dc886036 -- src tests
git status --short
```

前两条无输出、exit 0；提交裁决前状态原文：

```text
?? AI_agent/logs/reviews/request/2026-09-05e_tick_claim_design_rework1_crossreview.md
?? AI_agent/logs/reviews/verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md
```

**这份稿子现在可以进施工单了吗：不可以。若否，还差的那一件事是什么：把“本次第一步认定的每条边、链来源、运算与档位”收成可唯一复算且不可在第二步改写的完整证据契约，并用本文的新输入证明它确实成立；仅补原例或改闭合自述还不够。**
