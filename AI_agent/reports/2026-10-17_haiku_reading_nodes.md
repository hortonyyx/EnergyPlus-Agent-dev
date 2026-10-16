# Haiku：当前版本的独立平面与立面实测

日期：2026-10-17。用户要求“让haiku试一下在现在版本上做平面和立面，只做平面立面”。本批六个读图节点中，五个自主提交，只有西立面同时通过交付质量和时间验收；南立面没有有效产物。两层平面均提交，但未通过与6 Sol相同的独立标准。未做整楼装配、整案运行、跨层同墙识别或墙带规整，默认主线仍是6 Sol/high。

## 范围与冻结

- Work model：`claude-haiku-5-5`，medium，输出上限64,000；OpenCode Go，使用现有仓库外显式凭据文件。未切换账号、provider或模型。
- 每节点16请求、60工具、600秒、0模型重试；最多两个独立节点并发。输入为sm25原六图，每位读图员只获配其一张原图和公共坐标约定。没有GT、历史答案、开发者代读或运行中的人工补步骤。
- 先遇到两项接线问题，停止对应失败尝试、离线修复和独审后用新ID冷启；没有续写失败记录。所有生成器运行期间，代码、配置、原图均未改变。其余结果不因质量失败重跑。
- domain始终为`domain-v100-20261017`，两次修复均只变runtime、`changed_modes=[]`。North-02/South-01/East-01为runtime v22、提交`5839669b`；F1-03/F2-01/West-01为runtime v23、提交`4b720aaf69dbcc5d23a380387c798da6d676c634`。
- 生成与评价隔离：先等每个节点的terminal receipt及launch-result落盘，再读取GT和原独评标定。没有把评价结果喂回模型，所有原run、GT、标定哈希在独评前后保持。

## 实测结果

时间为各独立节点端到端墙钟；模型列是发送至完整响应的实际耗时，包含正常网络/服务等待，不能当成纯推理时间。harness包含入口准备、工具、状态维护和收尾。没有确认的服务异常可扣除；异常扣除为0。并发节点时间不能相加当作整案墙钟。

| 节点 / run | 总秒 | 模型 / harness秒 | 请求 / 工具 | 实报tokens | 提交与独立质量 |
|---|---:|---:|---:|---:|---|
| 首层 / f1-03 | 197.887 | 173.795 / 24.092 | 10 / 10 | 646620 | 已提交；14空间、31宿主、16门连接正确，7个内门法向位置不合格；harness尺寸关联使隔墙西移 |
| 二层 / f2-01 | 204.377 | 176.032 / 28.345 | 16 / 17 | 943598 | 已提交；应15空间却产16，原稿封闭了本来连通的走廊，23/30宿主、9/14门连接匹配 |
| 北 / north-02 | 74.302 | 44.438 / 29.864 | 5 / 4 | 118028 | 已提交；8窗世界数值接近正确，实际回叠整体缩移，最大水平窗位偏1.22m |
| 南 / south-01 | 96.256 | 70.767 / 25.489 | 16 / 9 | 352732 | 请求预算耗尽；3次试读均拒绝，无成功候选、净图、回叠或提交 |
| 东 / east-01 | 58.859 | 42.000 / 16.859 | 5 / 5 | 120467 | 已提交；13开口水平回叠基本正确，二层楼面误归F1，门底低约20cm |
| 西 / west-01 | 62.552 | 46.655 / 15.897 | 6 / 6 | 146103 | 已提交且质量通过；6开口、层别、门底、层线和轮廓正确，水平回叠最大1.52cm |

六个实际读图节点共58请求、58响应、51工具，供应方实报2,327,548 tokens，usage完整；另有一个首请求400，实际usage缺失，所以整批已知tokens只是小计，不能把那次计成0。另两次启动失败没有发送模型请求。整批共9次启动尝试、59次请求，0模型重试、0调度员模型请求、0整案调用，费用未知。

平面约180秒、立面约120秒是节点规划值。两层平面均超过180秒且质量不通过；西立面同时满足两者。北/东虽在120秒内提交，质量不通过；南没有交付，不能因为96秒结束就称时间验收通过。整案5分钟未验证。

与[现有6 Sol结果](2026-10-16_reading_contract_nodes.md)对照：首层从229.396秒到197.887秒，少31.509秒；二层从188.960秒到204.377秒，多15.417秒。Haiku的两层tokens约为对应6 Sol结果的3.69倍、6.27倍，trial工具调用8/9次（含入口格式拒绝），而对应6 Sol为3/2次；本次两案实际各落盘7份试读，6失败、1通过。两模型effort/output cap不同，二层旧结果为v99（v100改平面回叠底色），因此这是现有节点结果对照，不是严格同配置性能实验，更不是同质量提速。没有重跑6 Sol或历史Haiku整案。

## 平面：读数、harness采用值与最终图分别核对

首层的问题不能全部归为模型读错。正式最后稿的东侧办公室西隔墙POW原始x=793px，原图墙墨线约[790,795.5]px，中点约792.75px；`wall_reference.partitions`声明centerline。采用值却变成x=786.58px、世界x=10.9m。保存的`regularization_inputs.line_references`把这道墙关联到`top_row2`尺寸链附近的窗端tick787，造成约6.42px/13.9cm西移。最终7个内门DO1–DO7宿主/连通正确，但法向偏差17.266cm，超原内部开口8cm标准。实际线已处于墨线墙带西侧，不能用未知侧别解释。

回执已提示POW `reference_outside_ink_m≈0.074`；模型看到实际回叠后将其留在unresolved，没有修正。本轮记录为**harness尺寸关联造成位移，读图员局部复核未纠正**；没有在本批追加几何修复或质量复跑。后续应先围绕这一个反例修尺寸关联，不扩大容差或补写交付。

二层的问题在模型原稿已存在。PT11首稿[481,993]→[929,993]横穿原图约x655–744的无墨通道；最后原稿[470,985]→[929,985]仍封闭，采用值为[470.2,982.9]→[928.6,982.9]。harness调整坐标，封口并非代码新增。连续大厅/南走廊被拆成hall_N和corr_S，空间15→16，连带7个开口宿主、5条门连接不匹配。模型最终也承认`wall_gap_without_opening`，却作为未解决项交付。

两层各仅录入2条observed的240mm墙厚，与原标注相符；其余首层25/27、二层23/25为unknown，两个已知厚度的reference_side也均unknown。已录厚度正确和覆盖不足分开记录，不因unknown多单独判几何失败，也不称测厚充分。

| 平面 | 房界5/10/30cm分档 | 开口沿墙分档 | 开口跨墙分档 | 其他边界 |
|---|---|---|---|---|
| F1 | 1 / 3 / 10 / 0 | 11 / 20 / 0 / 0 | 2 / 4 / 25 / 0 | 房界最大18.889cm；沿墙最大7.838cm；31开口仅24位置满足原实体标准 |
| F2 | 9 / 1 / 4 / 1 | 15 / 15 / 0 / 0 | 8 / 6 / 16 / 0 | 多拆空间导致匹配房界最大11.234m，不代表某条墙整体平移11m；位置计数不能掩盖宿主/拓扑错误 |

分档按≤5、5–10、10–30、>30cm；原strict 2cm分区报告均为severe并保留。实体位置仍采用原沿墙10cm、外开口法向16cm、内开口法向8cm，不改成新容差；此前6 Sol外开口法向13.625cm与本次内门17.266cm不能混为同一标准。门连接是二维宿主投影关系，非整楼BIM连通验收。

## 立面与角色行为

- North：8窗数量/层别/宽高和世界位置正确，采用世界位置8/0/0/0、最大0.852cm；实际像素回叠水平0/0/0/8、最大1.220m，轮廓偏1.403m、层线最大0.489m。初次把立面误判成平面，内置完成提示后继续；两次trial修标定端点格式，两次submit修`local_review`字符串格式，没有改几何。原输入和返回图片都保持2690×1276，现有证据不能断言provider内部缩图原因。
- South：多次坚持把立面当平面，把3600/7200理解为进深；3次trial均给空开口/层线且Z起止均0，被正确拒绝。普通文字停止后由runtime内置完成提示继续，仍未完成；不是服务中断，也没有可以评价的候选。
- East：13开口水平回叠13/0/0/0、最大0.386cm；高度12/0/1/0，门底偏20.002cm。Z=3.6中层线画在正确位置，却标成F1而非F2；评价器按标签匹配出现3.6m错误，不能写成画线实际移了3.6m。3次trial、2次submit主要修标定和对象格式，没有修正门底/层别。
- West：6开口实际水平/高度均6/0/0/0，层线3/0/0/0、轮廓1/0/0/0；实际水平最大1.52cm、轮廓1.35cm。门底0.2m保留；4.32→4.3m为已有网格采用，宽度误差2cm。4次trial经历端点顺序、开口排序、端点顺序复发，最后生成唯一候选；2次submit将字符串改成summary对象。

平面第一份原稿也发生了plan/operations包装拒绝，之后是断头墙、重复空间种子和宿主失败；首层共2次submit，一次字符串格式拒绝后接受，二层共3次submit，两次对象格式/备注引用拒绝后接受。没有外部代为调用工具。当前这套接口在Haiku上存在明显机械往返和局部自检失效；本例不能支持“单节点已稳定合格”，也不能据此否定历史单模型基线已达到的范围。

## 接线修复与离线检查

| 尝试 | 版本 | 结果与耗时 | 模型请求 |
|---|---|---|---:|
| f1-01 | runtime21 / domain100 / e195e542 | 版本记录函数未传model，启动失败9.950秒 | 0 |
| north-01 | 同上 | 同一启动失败9.967秒 | 0 |
| f1-02 | runtime22 / domain100 / 5839669b | 首请求HTTP400，28.707秒（请求1.172、harness27.535）；未产图，usage未知 | 1 |

1. `run_model_configuration`调用`provider_parameters`补传各角色自身model。实现`ae458864`，登记`5839669b`为runtime22。独立19项离线通过；非Go、混合角色和未知型号拒绝保持。没有改默认6 Sol配置。
2. Go Messages不能直接接收本次平面目录的根级presence组合器；F1失败目录含根级`oneOf`/`anyOf`，成功立面及旧Haiku整案没有，存在同类[上游首手错误记录](https://github.com/anthropics/claude-code/issues/64113)。旧400正文被既有日志安全策略省略，不能声称服务明确返回了组合器原因。修复后F1/F2同目录均实际收到完整响应并自主提交，验证了当前请求可被服务接受。

第二项实现`3a01c72c`、登记`4b720aaf`为runtime23：仅Go Messages在传输/估算时深拷贝投影根级、两个互异已声明字段的singleton-required组合；无BIM工具/字段硬编码，不递归、不删除其他结构或本地schema。实际执行仍拒绝plan/operations同时或均未给、提交缺trial_id/hash等非法调用；nested操作约束保持。其他Go Chat/Responses及非Go Messages不变。没有修改domain角色指引、原图、几何或验收标准；传给模型的工具schema有上述明确的协议投影变化。

最终定向模块有效去重27项离线通过，独立复核4.40秒、无P1/P2；另核15种未支持形态原样保留和真实call_tool拒绝边界。初始旧码反例失败及修复记录均保留；19与27存在重叠，不相加成46。离线及发布验收均0真实模型请求。

## 产物与审计入口

运行根：`D:/Sim-BIM-Agent/runs/haiku-reading-v100-20261017`。证据根：`D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017`。其中`*-preflight.json`、`*-launch-result.json`、`*-audit.json`、`*-timing.json`记录原始版本、配置、文件哈希、真实请求/响应、图像注入和时间；三个configuration文件保留各次启动身份。最终配置SHA为`71c81abc5a9815706f6d961a72dea7768baedbee08f189428c428898709b521f`。

| 节点 | 实际净图 | 实际回叠 |
|---|---|---|
| F1-03 | [平面](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation-f1-03/reader_view_2.png) | [回叠](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation-f1-03/reader_view_1.png) |
| F2-01 | [平面](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation-f2-01/reader_view_2.png) | [回叠](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation-f2-01/reader_view_1.png) |
| North-02 | [立面](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation/north-02/reader_elevation.png) | [回叠](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation/north-02/reader_overlay.png) |
| South-01 | 未生成 | 未生成 |
| East-01 | [立面](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation/east-01/reader_elevation.png) | [回叠](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation/east-01/reader_overlay.png) |
| West-01 | [立面](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation/west-01/reader_elevation.png) | [回叠](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation/west-01/reader_overlay.png) |

各立面`review.html`包含原图、实际净图/回叠及两种独立回叠；独评投影不改写模型交付。`independent_review.json` SHA：North `d47232729f9f599774a0b5ab8e515444334a14f23a086546889f66df34e6d8e9`；East `1ffff3028c0c3b1e9e2adb23887cfc9f522936c5fbabe2ed52399d71aee408df`；South `ece166e973267b1f5d72400fcd18ff937cce15acf47541f2abe2f091cbd1568b`；West `91ebda61557a6a8f6920cc8f709fe10a5733b3bffb00ae9d594889dd3fe4afc6`。四立面总表SHA `600869d1c561dcfc603c2bc507332df169c160387d60c6c3e2b7fe25eb9659a7`。

平面独评`f1-03-independent-review.json` SHA `48d12ce1871c697324328fd24f3f01116f614568e5c4b2bc8a8dbdbe7590d083`；`f2-01-independent-review.json` SHA `0a9907fd56214f7cfe06d93bfc02170d184d93c96e8fdae472fd9d6d088a9851`。[首层可读验收页](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation-f1-03/review.html)与[二层可读验收页](D:/Sim-BIM-Agent/cache/haiku-reading-v100-20261017/evaluation-f2-01/review.html)包含三联缺陷裁图及墙厚标注核对。两案原run640/879文件的整树成员与SHA、GT/reference及18份旧Sol评价文件均未变。

接线独审`review-role-version-route.json` SHA `21116f866383042b9418b0e06f6ac070963290ce51c3724562b6d8fbd1f3099c`；`review-go-messages-schema.json` SHA `7875fd493688fa447213f0d98a067b5c497f623c46e80919385045c068e1a288`。新平面评价器只调整路径；立面评价器只调整路径、Messages参数审计和终态门槛，9个评分/匹配/参考/渲染函数与原脚本AST相同，标准未放宽。

## 固定桌面与后续边界

桌面`C:/Users/Horton/Desktop/Sim BIM Agent`原位更新为`4b720aaf`、runtime23/domain100，只含上述接线修复。517个程序文件SHA一致，安装离线验收26.656秒通过、0真实请求；上一版`previous.zip`校验通过，保留`5d56b7ec`，更新工作副本已清空。发布与本次失败的几何质量是两项不同结果。

安装验证后的临时发布目录`D:/Sim-BIM-Agent/releases/haiku-reader-adapter-20261017`（约21.5MB程序）删除被自动审批策略拒绝，返回`blocked by policy`，没有提供更具体原因。目录保留，未重试、改路径或绕过；历史已拒绝的临时目录也未触碰。没有创建新工作树，既有其他任务工作树未改。

收尾时C盘可用约42.79GiB、D盘约127.29GiB。模型原始输出、失败证据与独评留在D盘，未复制进桌面产品。

下一步优先处理首层尺寸链误关联，以及已有局部差异为何可以被当作未解决项带入提交；二层原图连通判断、南立面图种识别也需针对节点讨论。本轮到测试与归因收口，没有自动追加模型实跑、提高预算、调整容差或开启整案。
