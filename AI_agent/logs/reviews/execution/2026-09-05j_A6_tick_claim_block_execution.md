# A-6 整条线执行档（GPT，2026-09-05）

工程档 / 科研 P0，施工方 `gpt-6-astra`；提交 Claude 家族复核，本档不是自批通过。
工作树 `/tmp/a6_tickclaim_astra`，分支 `wt/09.05j_a6_tick_claim`，基点 `2a51d7fd`；本次续跑起点 `a2cd995c`。
已有 A-6a/A-6b 实现、测试和探针沿用已提交版本。本轮只写本档，并按派工单 §三#4 删除契约中五处没有代码强制的措辞；没有重跑测试或修改 `src/`、`tests/`。

完整全量实际在 `c1dab3b8` 运行，原文由 `a2cd995c` 落库：**3877 passed / 2 skipped / 13 xfailed / 0 failed，EXIT_CODE=0**。
双导入哨兵见 [full_suite.txt:1](../../experiments/2026-09-05j_A6_tick_claim/full_suite.txt#L1)，汇总及退出码见该文件第 442、444 行；独立算账见本档第六节。
`git diff --name-status c1dab3b8 a2cd995c -- src tests` 输出为空，因此这次完整读数覆盖当前实现与测试。先前 `7b6f5885` 的中断日志不计通过。

以下位置都回到文件用 `rg -n -F` 检索锚点核过，没有从 diff 推算行号。为压缩表格：

- **T** = [src/agent/correction/tick_claim.py](../../../../src/agent/correction/tick_claim.py)，`T:498` 表示该文件第 498 行。
- **O** = [src/agent/correction/opening_adjudication.py](../../../../src/agent/correction/opening_adjudication.py)。
- **E** = [enforcement_lines.txt](../../experiments/2026-09-05j_A6_tick_claim/enforcement_lines.txt)，`E54 → T:493` 是索引第 54 行所列消费函数入口；表内另列实际判断/赋值行，入口不冒充拒绝条件。
- **P** = [probe_after.txt](../../experiments/2026-09-05j_A6_tick_claim/probe_after.txt)，行号指原始输出；数值后缀 `_u` 是 0.1 mm 整数。
- **C** = [收口契约](2026-09-05j_A6_tick_claim_contract.md)，行号指本轮删除措辞后的正文；删除只改同行文字，未移动行号。

## 一、§三#1：十五条重新表态

引用 `b7e77431` 已提交的 [reassessment.md:10](2026-09-05j_A6_tick_claim_reassessment.md#L10) 表（第 12—26 行，共 6+5+4 条）：B-4、B-6 降为不阻断，其余问题保留但明确收窄解释；B-5 中“还要另行停报批准一档免疫”的旧要求撤回。并非默认十五条全部成立，理由逐条在原表，本档不重写。

## 二、§三#2：旧反例、原命令与改后出口

完整索引沿用 [证据 README:27](../../experiments/2026-09-05j_A6_tick_claim/README.md#L27)。已执行的命令原文如下，本次续跑仅阅读已有输出：

```sh
python AI_agent/logs/experiments/2026-09-05j_A6_tick_claim/capture_legacy.py
python AI_agent/logs/experiments/2026-09-05j_A6_tick_claim/probe_after.py
```

`capture_legacy.py:19` 载入旧命令定义，`:22` 执行，`:24` 同时写原命令、原输出和退出码。完整旧记录为：

- [legacy_2026-09-05e.md](../../experiments/2026-09-05j_A6_tick_claim/legacy_2026-09-05e.md)：E01—E14；第 287 行起是原型 producer，第 346 行起是旧链门，第 406 行起是旧响应/工厂约束。
- [legacy_2026-09-05h.md:1066](../../experiments/2026-09-05j_A6_tick_claim/legacy_2026-09-05h.md#L1066)：E13 的旧 `probe.py all` 命令和输出；E14（1102）、E15（1190）、E16（1215）分别保留之前的统计、反例、算术重跑。`SPEC` 仍表示按旧稿签名构造，`ACTUAL` 才是所标 API 的实际调用，未把旧稿模拟冒称新实现运行。

| 旧反例 / 诉求 | 改后输出原文位置与具名出口 | 强制点 |
|---|---|---|
| B-1：中心 3000、声明宽 900，合法非节点 2550/3450 被节点域排除 | P:85、86 为 `25500 / 34500`；不是把数值凑入节点表 | T:291、297、302 |
| 同节点塌缩、反向区间 | P:78、79：两者均 `RETURN_TO_STEP_ONE_INTERVAL` | T:478 |
| 原型最近邻将 800/950 都选成 1000；原点 0/700 被 `_s1` 错分；620/870；176/254 | P:1—13 实际执行原 `_nearest`，新入口全部 `SAME_IMAGE_MODEL_REQUIRED`，提前取事实均 `TICK_BATCH_INVALIDATED` | T:397、495 |
| East O01 两端不能由 `ALL_S1` 自动定为原点 | P:19、20：52 个 x/z 端点进同图包；诊断模型明确选 pixel，O01 输出 5400/21600u | T:397、449、458 |
| South 主链内虚构 17970 仍可能误认 | README:34 登记的是同一候选/事实边界，不是另一次真实图像裁定；P:14 的全 South 包不自动定案 | T:397、410、495；不声称已证明视觉选择正确 |
| South O02/O04 四端及 West O05 两端无非主链地址 | P:15—18、23、24：保留 `C_bot_fine / C_top_fine` 节点身份，出口 `ADDRESSABLE_MODEL_CANDIDATE` | T:189、370、383 |
| 4700/4900 覆盖；4200 同值异链；4000/4050；2600/5200 碰另一主链节点 | P:31—38 两种扁平表覆盖结果都保留 P/Q 候选，交 `SAME_IMAGE_MODEL_REQUIRED`；完整“另一节点也同值”结构另见测试第 164—187 行 | T:370、383、397 |
| 总长正确但中间 7000 污染、重复 5000、新 2450 污染 | P:25—27：`CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM` | T:61 |
| 零段、负段、短 cum 且非零起点 | P:28—30：`CHAIN_SEGMENT_NOT_POSITIVE / CHAIN_DOMAIN_INVALID` | T:55、57 |
| node1+node2=5900 冒充真段和 4300 | P:43：`OPERAND_REF_DOMAIN segment`；P:44 合法段和 `43000` | T:237、289 |
| 差值 2700 冒充位置 4300；有向 -400/100 没有坐标系 | P:45 显式锚后 `43000`；P:68、69 在显式原点下输出 -4000/1000u | T:259、262、295、302 |
| 轴线半厚左右符号；4000/8000 全厚 200；3600/7600 全厚 220 | P:48—61 正负号均执行；内侧分别为 41000/79000u、37100/74900u | T:264、270、280 |
| 4200 一档轴线搭二档 115 半厚；角色齐全仍无同图声明资格 | P:63—65：有合格声明才可算，改为测量资格即 `OPERAND_NOT_DECLARED` | T:246、273 |
| 跨图 ref、错轴 ref | P:46、47：`OPERAND_CROSS_IMAGE / OPERAND_FRAME_MISMATCH` | T:235、252 |
| full 201u 除半格；full 202u | P:66、67：前者 `WALL_THICKNESS_HALF_UNGRID`，后者精确取 101u 半厚 | T:277 |
| tuple 类型正确仍可漏边、漏平面洞、漏方向 | P:70、94、95：`TICK_DECISION_COVERAGE_MISMATCH / PLAN_TOPOLOGY_COVERAGE_MISMATCH / FACADE_AVAILABILITY_MANIFEST_INCOMPLETE` | T:436；O:157、159 |
| D6 工厂/重新 finalize、换数值/档位/ref、两个有效 artifact 换本次选择 | 旧 D6 原输出在 legacy_h:1096—1098；新 P:71—73、96、97 均以 `TICK_BATCH_NOT_CURRENT_DECISION` 拒绝替换 | T:498、513 |
| `obligation=None`，assert_backed 通过却无人兑现 | legacy_h:1095 仍是 `redeemed=()`；新 P:76、77 为 TickSession 自有两笔债及补证重裁后两笔 retired；不是修改旧 resolver | T:454、464、489、539 |
| 整体审查推翻后旧事实、旧响应、旧空间结果复活 | P:74、75、82：`TICK_BATCH_INVALIDATED / STALE_TICK_RESPONSE`；第二步发起回裁见测试 `test_opening_adjudication_a6.py:93` | T:429、495、542；O:256、311 |
| 一档 1935 被 10mm 出口碾成 1940 | P:92、93：1935/2473 分别保留 19350/24730u | T:449、515 |
| ②b 无立面洞口行；③ 无立面图，旧签名均无出口 | P:80：①、②a、②b、③；②b 无几何、③ `inferred / score_eligible=False`；P:81 可计分出口仅两笔 | O:272、281、295、298、319 |
| 单有 6925 的单位整数化就当成认领证明 | P:83 只得 69250u；选择仍须选该边 candidate ID | T:38、447、498 |
| 本轮发现：补证失败、可变操作数/调用方清空 facade 列表 | P:87—91：失败补证后旧响应 `REGISTER_PENDING_READING_INPUT`；别名修改后 preview/final 均 16000u，旧空间结果仍失效。修前原文在 `mutable_inputs_before.txt:1` | T:85、334、542、543；O:143、233 |

“可寻址候选”不等于已认领；上述模型选择都是显式诊断 fixture（`probe_after.py:1`、P:84），没有声称完成真实图像模型裁定。旧 `numbers` 输出扫描的是旧稿，不拿它给本契约背书（README:19）。

## 三、§三#3：两条单独设置的同形输入

**这一类错误**是：两个具名链共用一个像素键，扁平 `pixel → value` 覆盖掉链身份；非主链 Q 的值又恰等于主链 P 的另一个节点，导致“主链有这个数”的成员检查通过，却把 Q:node1 偷换成 P:node2。
旧输入是 `2600/5200 @275.0`。本轮两条测试在 [test_tick_claim_a6.py:164](../../../../tests/test_tick_claim_a6.py#L164)：

| 新输入 | P 累计节点（mm） | Q 累计节点（mm） | 像素键与两种最后写入值 |
|---|---|---|---|
| A | `[0,1800,3600,7200]` | `[0,3600,7200]` | 318.5；分别最后写 1800、3600 |
| B | `[0,2150,6450,8600]` | `[0,6450,8600]` | 407.2；分别最后写 2150、6450 |

两例都保留“Q:node1 与 P:node2 同值，但不是同一节点”的结构；数值、总长、像素键都不同于旧例。测试第 170、179 行建立上述两条链，第 175 行枚举覆盖顺序，第 183、185、187 行核两种顺序均保留 `(chain_id,index,value_u)` 集合，第 186 行核未裁定前不能消费事实。

输出原文在 P:39—42：

```text
COLLISION 1800 3600 pixel_key 318.5 flat 1800 => SAME_IMAGE_MODEL_REQUIRED [('P', 1, 18000), ('Q', 1, 36000)]
COLLISION 1800 3600 pixel_key 318.5 flat 3600 => SAME_IMAGE_MODEL_REQUIRED [('P', 1, 18000), ('Q', 1, 36000)]
COLLISION 2150 6450 pixel_key 407.2 flat 2150 => SAME_IMAGE_MODEL_REQUIRED [('Q', 1, 64500), ('P', 1, 21500)]
COLLISION 2150 6450 pixel_key 407.2 flat 6450 => SAME_IMAGE_MODEL_REQUIRED [('Q', 1, 64500), ('P', 1, 21500)]
```

探针这四行展示两链地址与覆盖顺序；**包含 P:node2 同值碰撞的完整构造以测试第 170—179 行为准**，不把探针的简化 P 链冒称完整构造。两项测试的收集原文在 `resume_test_collection.txt:17`、`:18`，已被完整全量覆盖。

证明范围来自通用机制，加上这两组检验：T:370 按链节点枚举，T:383 以包含 `chain_id/domain/index/source_sha` 的完整表达式生成候选身份，T:397 统一要求同图模型选择；代码不读取扁平表来决定节点，也没有针对 318.5、407.2 或这几组毫米数的修补分支。T:447 限定选择属于当前边，T:498 再核本次决定。因此这类**由同值成员检查或覆盖顺序自动偷换身份**的路径在正常 API 中被移除。两条样例本身不构成对所有视觉输入的穷举证明，也不保证模型一定选择正确；模型仍可判错并走回裁。

## 四、§三#4：契约逐句强制对账及删句

索引 E 是既有 `enforcement_lines.txt`；以下用其记录的 `文件:函数入口行` 定位，再给出本次从源文件检索的实际执行行。示例核行命令原文：

```sh
rg -n -F -e 'def consume' -e 'type(supplied)' -e 'retired_debt_id=' -e 'self._current = None' src/agent/correction/tick_claim.py
rg -n -F -e 'if len({b.opening_id' -e 'if len(facades)' -e 'classification = "①"' -e 'return tuple(r for' src/agent/correction/opening_adjudication.py
```

| 契约句（C 行号；复合句分列其保证） | E 中的文件入口 → 实际强制行 |
|---|---|
| C:7 第一步候选→响应→落值/区间→当前批次 | E44→T:331；E51→T:426；执行 T:397、433、449、478、486 |
| C:7 第二步独立预期批次、B4、四分类 | E13→O:140；E17→O:239；执行 O:150、155、196、281、295、298 |
| C:9 x/z 都从第一步重推导后交 B4 | E11→O:122；执行 O:123、129、130、196 |
| C:17 只接受两种源契约，全集由原始源枚举 | E43→T:305；执行 T:307、314、317、324、328；T:342 直接取此源集合 |
| C:18 字节摘要、源 ID、平面索引退债身份 | E23→T:34；E43→T:305；E52→T:464；执行 T:316、326、337、467 |
| C:19 witness 原样冻结，packet/edge 保留源和证据字段 | E30→T:96；E34→T:129；E44→T:331；执行 T:386、387、396 |
| C:20 packet 包含源、补证、代次及全候选集合 | E44→T:331；执行 T:393、394、395 |
| C:20 第一响应、平面拓扑、四向清单分别精确覆盖 | E51→T:426；E13→O:140；执行 T:435、436；O:157、159 |
| C:21 最近邻/ALL_S1/同值均不自动终结；空图可记空账 | E44→T:331；E51→T:426；执行 T:397、410、435、481、486；未提交的 current 不能过 T:495 |
| C:22 witness 链全部节点；无 witness 枚举同轴链；派生先验证 | E46→T:370；E44→T:331；执行 T:374、376、379、382；非法域由 T:234 解析器拒绝 |
| C:28—39 补证 schema/源图、链、坐标系、声明字段资格 | E37→T:158；E40→T:234；执行 T:168、169、174、177、179、184、246、273 |
| C:42 bytes/tuple 快照，公开 packet 只读 | E28→T:83；E45→T:334；E14→O:143；E49→T:419；E15→O:230；执行 T:85、334、335；O:143、229 |
| C:44 原型补证核图、方向、主链，保留配置且不自动把墙厚候选升为声明 | E38→T:189；执行 T:197、198、201、213、216、217、219；主链复核 T:184 |
| C:46 ref 地址域、mm→0.1mm、声明资格、原点方向 | E26→T:67；E24→T:38；E40→T:234；执行 T:41、42、235、237、240、246、252、259 |
| C:50 正段、零相对原点、基数、总长、中间前缀 | E25→T:47；执行 T:55、57、59、61 |
| C:54 anchor 必为一个本图同轴 node；显式正负号 | E39→T:223；E40→T:234；执行 T:231、235、237、252、262、264 |
| C:58 node 不接受多余 operands/thickness/负方向 | E39→T:223；执行 T:266 |
| C:59 sum 是一个以上同链连续 segment，不接受 node 伪装 | E39→T:223；E40→T:234；执行 T:284、286、287、289、237 |
| C:60 diff 恰两同链 node；位移须加锚 | E39→T:223；执行 T:291、293、294、295、302 |
| C:61 half_span 恰两同链 node，除半精确，否则拒绝 | E39→T:223；E42→T:298；执行 T:291、297、299、302 |
| C:62 half_wall 恰一个声明、full/half 对应、正厚、full 除半无余数 | E39→T:223；E41→T:275；执行 T:270、272、273、274、277、279、280 |
| C:64 同图同轴、算段/差链自身一致，不假设共同累计原点 | E40→T:234；E39→T:223；执行 T:235、252、259、286、291 |
| C:66 输入拒绝不自动降档；pixel 须由响应明确选择 | E39→T:223；E51→T:426；执行 T:236、238、248、253、257、301；T:109、446、452、458 |
| C:68 5900 伪段和走不通，合法 4300 与 2550/3450 放行 | E40→T:234；E39→T:223；执行 T:237、289、297、302；原文 P:43—45、85、86 |
| C:72 strict/extra forbid，重验响应，第一步无跨图审查或模型坐标字段 | E31→T:106；E33→T:122；E51→T:426；执行 T:107、108—111、123—125、433 |
| C:76 select 必须是本边候选，代码一档落值 | E51→T:426；执行 T:443、447、449、451 |
| C:77 正常 pixel 无补证债 | E51→T:426；执行 T:445、453、458、459 |
| C:78 pending evidence 必须缺链，且记自有债 | E51→T:426；执行 T:454、456、463 |
| C:79 reperceive 不冻结当前事实 | E51→T:426；执行 T:438、439，在 T:486 之前退出 |
| C:81 二档消费 output_precision_m、HALF_UP；一档免疫 | E48→T:402；E51→T:426；E54→T:493；执行 T:414、449、458、484、515、518 |
| C:83 record 含完整选择/证据/两档/债/代次与出口声明，ID 为其摘要 | E22→T:29；E23→T:34；E51→T:426；执行 T:460—467、481—486；这里的“持久化”指冻结序列化内容，不承诺磁盘写入 |
| C:85 不接受另一有效批次、重 finalize、换字段；重新算值且核全集 | E54→T:493；执行 T:495、498、501、504、513、515、521；独立预期 ID 在 O:150、217、233 |
| C:92—95 正常提交、区间回裁、推翻失效、轮数耗尽 | E51→T:426；E55→T:528；E17→O:239；执行 T:478、481、542、545、546；O:256 |
| C:98 先失效再验证，旧事实不恢复；成功新包拒旧响应，失败则 pending；同源候选保留 | E55→T:528；E56→T:543；E51→T:426；执行 T:540、542、543、544、553、555、557；T:427、429 |
| C:98 默认轮数是预算，不是毫米比较 | E48→T:402；执行 T:403、407、545 |
| C:100 补证→重裁→重新选择→成功新批次才可能退债 | E55→T:528；E52→T:464；E53→T:489；执行 T:539、555、449、464—467、486、489、490 |
| C:100 同 edge/source、无缺链且一档；同值或换源不自动退；原债留历史 | E52→T:464；E55→T:528；执行 T:465、466、467、539、540；T:487 保留旧批次记录 |
| C:102 刻度债由本模块处理，不借 obligation=None 的文本承诺 | E51→T:426；E52→T:464；E55→T:528；执行 T:456、464、539；旧 resolver 不改见第六节路径对账 |
| C:109 平面端点覆盖旧 line；显式楼层原点；墙/立面轴绑定 | E1→O:31；E13→O:140；执行 O:38、170—179 |
| C:109 四向 session/batch 同在或同空；镜像正向不默认为 False | E2→O:42；E13→O:140；执行 O:46、47、159、184、199；既有 `opening_synthesis.py:1071` 调用 `src/agent/correction/facade_convention.py:104`、`:109` 的声明校验 |
| C:111 审查包含全集、四向有无图、B4 和未配洞口 | E13→O:140；执行 O:155、157、159、205、217、218—227 |
| C:111 响应覆盖每个平面洞，配对 ID 属该方向且不可复用 | E5→O:67；E17→O:239；执行 O:77、263、275、277 |
| C:115 ① 区间精确相等，z 取立面 | E17→O:239；执行 O:280、281、284 |
| C:116 ②a 区间不同取立面，保留平面墙/房 | E17→O:239；执行 O:281、284、301 |
| C:117 ②b 登记不造 span/z | E17→O:239；执行 O:272、297、298 |
| C:118 ③ 仅缺立面时推测，保留平面位置，加楼层原点，标记不可计分；允许登记 | E17→O:239；执行 O:270、272、286、291、292、295、297 |
| C:120 尺寸是假设，不是世界坐标；无默认尺寸/表；正高格点塌缩拒绝 | E3→O:50；E4→O:61；E17→O:239；执行 O:57、58 为必填，O:62、291—295 算 z 并重检；不声称模型自带知识被代码证明 |
| C:122 整栋推翻按图回第一步，旧结果失效 | E17→O:239；E16→O:233；E18→O:310；执行 O:251、256、259、311；T:542 |
| C:122 整栋 register 不可计分；出口只取当前且 eligible 的结果 | E17→O:239；E19→O:316；执行 O:300、311、312、318、319；eligible 只在配对 O:284 置 True，推测 O:295 不置 True |
| C:128 保证汇总：来源/算术/账/全集/本次绑定/显式档位/失效 | 对应上述 C:46、50、81、83、85、100、122 行；保证仅及这些入口，不包括模型语义正确 |

C:3、11、48、130 的 P0 范围、语义责任与未实现项是边界说明，不是代码能够证明“图认对了”的保证。C:9、81、102、130 关于没有改 B4/T4-a/gt/签字产物的事实，用第六节 Git 路径差异核，不把“没改文件”冒充运行门。C:24、50、66、87、104、124 是强制位置导航，实质保证已逐条在上表展开。主控补记 C:134 以后保留为当时的中断记录，本轮完整读数由本档和 a2cd995c 的日志接续。

### 找不到强制点而删除的五处措辞

下列原文均取自 `a2cd995c` 的契约。本轮只删除文字，没有用新增实现补洞，也没有把未实现动作写成已完成：

| 原位置与删去的原文 | 原因与保留的实际边界 |
|---|---|
| C:7「每张 reading 图各一实例」 | 没有图级全局单实例注册器；P:96 反而实际创建同源两次合法会话。强制的是给定 owner 与独立 expected ID 下的本次决定（T:498），不是禁止两个会话存在。 |
| C:11「`CorrectedGeometryV3` 装配消费新结果时，应通过当前 `OpeningReview.consume`/`scoreable_openings` 获取，不把历史 JSON 当成当前有效批次。」 | 尚无该装配接线，无法指到装配端的强制调用行；保留新 API 自身的当前结果检查 O:311、319。 |
| C:66「代码调用方修候选或 reading 补证后回第一步。」 | 非法候选会具名拒绝，但没有自动修候选/驱动 reading 的调度器。保留可显式调用的 reconsider 及其状态约束，不承诺输入拒绝后自动修复。 |
| C:83「调用方持久化时需一起保存这两份源及批次 record，不能只保存预览坐标。」 | 当前只产出冻结 bytes，没有磁盘存储器或跨进程恢复消费门，约束不了调用方究竟保存哪些文件。保留 TickPacket 源 bytes 与 TickBatch record 的实际字段。 |
| C:130「正式接线需消费这里的来源和当前出口语义」 | 这是未来接线要求，未在本次实现中强制；删除后仍明示绕过新 API 的历史记录消费不在保证内。 |

这些是 B 层保证措辞收窄：不撤销两阶段、身份不等于同值、运算域或本次决定绑定的承重前提，也不触碰禁区。没有以删句声称未来装配、reading 自动调度或磁盘恢复已经实现。

## 五、§二：R-1…R-4 逐条闭合

### R-1：候选、事实、全集和回第一步

**原文诉求**：“待认领候选与已裁定事实分开”“全集输入的唯一冻结来源与消费入口约束”“推翻时回第一步的具名出口”。
**落地机制**：T:305 从冻结 reading 定义源集合；T:393 冻结候选包身份，T:397 让当前非空输入全部交同图模型，空图可空响应记账。T:436 把完整响应集合与源集合对照，T:449/458 落两档，T:478 重检区间，T:486 才登记事实批次。O:155、157、159 在第二步消费事实并核平面与四向全集。
**回裁责任**：第二步 O:256 调用该图 TickSession.reconsider；T:542 先作废 current、T:555 新包、T:429 拒旧响应，O:311 使依赖旧图的空间结果失效。具名出口是 `RETURN_TO_STEP_ONE_FROM_SPATIAL / RETURN_TO_STEP_ONE_INTERVAL / STALE_TICK_RESPONSE / TICK_BATCH_INVALIDATED`；证据 P:70、74、75、78、79、82、94、95，第二步主动回裁的测试 O 对应测试文件第 93—95 行。不能用“遍历过”代替这三处集合相等判断。

### R-2：身份不同于同值，补证债有兑现责任

**原文诉求**：绑定“原链身份 + 坐标系 + 指认记录”，并落实“补证 → 同图重新认领 → 新裁决替换旧裁决 → 退债条件 + 负责阶段”；特别不能拿 `obligation=None` 当兑现承诺。
**落地机制**：T:235/237/252/259 解析图、链、域、原点方向；T:383 候选保留完整表达式身份；T:461—463 保存原 witness、候选和模型选择。同值/覆盖顺序仍进 `SAME_IMAGE_MODEL_REQUIRED`（P:31—42），不做主链同值替换。
**谁挡住旧 API 的空兑现**：旧 API **仍然**在 legacy_h:1095 输出 `obligation=None / redeemed=()`，本单没有修它，也没有把该结果改称已兑现。新消费入口 O:144 要求 TickSession，O:155/193 从该会话的当前事实取数；新刻度债由 T:456 生成，T:539 由会话持有，T:464—467 只有在同一源、同一边、补齐缺链、重新选择一档后才写 `retired_debt_id`，成功冻结后 T:489—490 移除旧债。责任阶段是 **correction 第一步的 TickSession.submit**，不是 B4 的 obligation resolver。
**证据与界限**：P:76、77 展示两笔自有债从 pending 到 retired；测试 `test_tick_claim_a6.py:134` 还核旧批次失效。单有补证路径或旧 assert_backed 通过不会触发新退债条件；未取得补证仍可保留二档值与债，不能称已兑现。reading 尚须实际供证、模型尚须实际再选，本单没有自动调用它们的调度承诺。补证失败的出口 `SUPPLEMENT_SOURCE_MISMATCH / REGISTER_PENDING_READING_INPUT / TICK_BATCH_INVALIDATED` 见 P:87—89，强制 T:542、543、427。

### R-3：完整运算签名与资格解析

**原文诉求**：每种运算的角色/基数、node 或 segment 域、单位、原点/方向、同图声明资格及具名拒绝；特别是 5900 伪段和。
**落地机制**：封闭的五种 Expression 运算见 C:58—62 及第四节逐项强制表；入口 T:234 从冻结补证解析，不从 role 名或裸数值猜资格。T:237/289 让 node1+node2 在求段长时立即 `OPERAND_REF_DOMAIN`，P:43 记录原文；P:44 合法段和 43000u，P:45 显式锚的差位置 43000u。跨图、错轴、二档厚度、半格分别走 `OPERAND_CROSS_IMAGE / OPERAND_FRAME_MISMATCH / OPERAND_NOT_DECLARED / WALL_THICKNESS_HALF_UNGRID`（P:46—67）。这些是候选输入拒绝；真正无合适刻度的值由显式 pixel 决定经 T:458 出口，一档 T:449 不经该格点。没有阈值把非法运算变成合法一档。

### R-4：绑定本次认领决定

**原文诉求**：B2 的“有效冻结事实”不足以证明 artifact 属于本次决定。
**落地机制**：T:486 由会话登记当前批次，T:481—485 的 record 纳入整份 response、源、代次、出口声明和全部行；第二步 O:150/217 留独立预期 ID。T:495 比当前身份，T:498 比预期 ID、当前字节和摘要，T:504 核全集，T:513/515/521 重推选中表达式与值。新包 T:542 作废旧 current；普通 list 别名另由 T:85、334、335 和 O:143 快照。
**反例出口**：P:96 两份同源合法批次确实分别给 15900/16000u，P:97 以 `TICK_BATCH_NOT_CURRENT_DECISION` 拒绝用另一份替换；P:71—73 的换值/换档/换候选同样拒绝；P:90、91 核 list 修改不改已冻决定或移除失效检查。保证只对给定 owner、独立 expected ID 和正常 API 成立，不要求禁止另开会话或抵抗 Python 反射。

## 六、完整全量与逐位闭合

**基点读数是从版本树取的，不是照抄续跑消息。** 本次执行：

```sh
git show 2a51d7fd:AI_agent/logs/reviews/request/2026-09-05i_A11_gt_1mm_crossreview.md
git diff --name-status c7c6831a 2a51d7fd -- src tests
git diff --name-status 2a51d7fd a2cd995c -- src tests case_tests
```

第一条原文第 21 行记载：主控在 `c7c6831a` 跑得 `3850 passed / 2 skipped / 13 xfailed / 0 failed`；第二条输出为空，故该已签基线沿用到 `2a51d7fd` 的源码和测试。本席本轮没有重新执行基点全量。第三条只输出四条新增路径：

```text
A src/agent/correction/opening_adjudication.py
A src/agent/correction/tick_claim.py
A tests/test_opening_adjudication_a6.py
A tests/test_tick_claim_a6.py
```

新增数直接解析 `resume_test_collection.txt` 中以 `tests/` 开头且含 `::` 的 nodeid，按文件计数并去重：第 1—22 行为 tick_claim 的 22 条，第 23—27 行为 opening_adjudication 的 5 条；27 条均唯一，与第 30 行 `27 tests collected in 0.91s` 相符。这是参数展开后的用例数，不是源码中 `def test_` 个数。两测试文件在基点都不存在，既有测试无删除、修改或替换。

| 结果位 | 基点已签读数 | 本单增量 | 相加 | 完整全量实际 | 差额 |
|---|---:|---:|---:|---:|---:|
| passed | 3850 | 22+5=27 | 3877 | 3877 | 0 |
| skipped | 2 | 0 | 2 | 2 | 0 |
| xfailed | 13 | 0 | 13 | 13 | 0 |
| failed | 0 | 0 | 0 | 0 | 0 |
| 所有结果合计 | 3865 | 27 | 3892 | 3892 | 0 |

完整全量的运行命令（已执行并落库，本轮没有再跑）：

```sh
cd /tmp/a6_tickclaim_astra && python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```

原始日志首两行及末尾，不以进度点号代替汇总：

```text
/tmp/a6_tickclaim_astra/src/agent/correction/tick_claim.py
/tmp/a6_tickclaim_astra/src/agent/correction/opening_adjudication.py
3877 passed, 2 skipped, 13 xfailed, 211 warnings in 508.38s (0:08:28)
EXIT_CODE=0
```

上述汇总没有 failed 类目且 shell 退出 0，故 failed=0；211 warnings 如实保留，不计入测试条数。中间三次完整全量只作历史线索，最终读数单独取 `full_suite.txt:442`。本轮没有依赖安装、没有新增 txt、没有运行 pytest。

路径纪律：本次核 `git diff --name-status 2a51d7fd a2cd995c`，除本单文档/证据外只有上述四条新增源码/测试。故 `score_service.py`、`as_measured.py`、整个 `answer_compiler.py`、旧 `gt/*/gt.json`、`case_tests/test_baseline/gt_staging/`、旧 facts/签字 fixture、B4/T4-a/B2 实现均无差异。本轮只改本档和契约删句；未进入主工作树写入，未使用 `git add -A`。提交前按确切两个路径暂存并查看 `git diff --cached --numstat`。

## 七、最薄弱的一处与交审边界

**最可能被跨家族审推翻的是“新子环节 API 的消费约束是否已足以代表整条生产线收口”。** 现有强制确实发生在 T:498、O:155、O:233、O:311、O:319，但 `run_pipeline → CorrectedGeometryV3 → judge` 尚未接这些出口；旧 B4 低层 dict API 也还存在。因此它们不能证明生产调用方没有绕开新入口、从历史 JSON 拼出结果，更不能证明一栋真实建筑已经过模型整体审查。

本单实际完成的是同图认领/重裁/补证退债、第二步四分类及当前结果消费的可执行 API；模型响应在证据里是诊断 fixture（P:84）。没有做真实模型调用、sm25 端到端、跨进程 owner 恢复或通用整栋拓扑重检。C:11、130 明示这个边界；本轮又删去装配/持久化端无法强制的句子。换人审应按新 API 的具体闭合判据核，不能把本档当 E-a/J 的接线验收或模型视觉质量证明。

本轮未发现需改源码、禁区或已签基线的 A 层前提问题。B 层记录两处派工文字差异：派工单分支写作 `wt/09.05h_a6_tick_claim`，实际为 `wt/09.05j_a6_tick_claim`；较早续跑消息提 §六，但当前派工正文止于 §五，本档按最新用户逐条指定的 §三四义务、§二四阻断及读数/弱点结构交件。施工自证交齐后仍待 Claude 家族独立复核，不自签 APPROVE，不合并。
