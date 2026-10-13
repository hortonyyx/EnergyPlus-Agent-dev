# Harness 充分性、必要性与强模型自主交付

用户在当前会话明确取消模型国别/规模上限，允许 Astra、6.1 Sol 等 work model，并授权“按这个目标做”。最新明确：**提速不是主要目的，先让 harness 充分且必要，使高智力模型能快速稳定交付。10分钟是优化目标，不是硬截止；不强制限制整案时间。** 该授权覆盖本轮实施、必要验证与目标案例冷启动，不扩展到收费API回退、DeepSeek或其他输入路线。

## 方案与验收

- 复用已有 single_model 入口与同一源 BIM/kernel；一个模型处理六张原图，避免主要路径上的读图员提交、历史任务选择与重派协议。
- 统一草稿/报告有界读取；失败稿的报告与成功稿一样绑定原始证据，分页引用在后续修订后仍定位原稿。
- 补齐跨层隔墙/外轮廓物理边界的检查与规整覆盖，保留尺寸证据、拓扑保护、最终源 BIM 门槛和原始审计。
- 不扩大角色、不新增通用调度框架、不降低空间/开口/连接质量门槛。

验收要求：原六张sm25图纸、独立冷启动、无开发者中途提示或改稿；模型主动完成整楼源 BIM 与查看器，并通过独立空间/门窗宿主/连通质量评价。端到端墙钟及各阶段开销如实记录，以约10分钟为优化目标，超过600秒本身不判失败或强制停止。兜底产物、离线成功、单层候选和人工补步骤不算完整自主交付。初次成功后同一冻结版本再做两次冷启动，用3次结果报告有限样本的可重复性，不宣称统计可靠性。

## 当前结论（2026-10-14）

同一冻结版本在 sm25 原六图上顺序冷启动三次：**两次自主交付并通过当前 Lite 已核物理范围独评；第三次被订阅服务使用限制中止，未正式交付。** 不能写成3/3成功、稳定性已全面验收或10分钟目标已达到。未切账号、回退付费服务、额外重试或追加第四轮。

当前主路径复用单模型、局部修订和现有编译/装配工具，不另建大型 domain 框架。模型承担读图、参考面/方向判断、证据取舍、推断与任务完成判断；代码承担确定性计算、几何约束、当前状态、来源核验与交付验真。几何 kernel、10cm规整、拓扑/宿主/连通检查和可恢复证据应保留。

已实际减负：有界草稿与报告读取、成功装配直接跟读、等价锚点排序、可选空备注、当前候选摘要、notes-only后旧开口观察在新源模型上重新验证。三轮均无需因备注修订重填61个开口标记。**仍有明确负担：空间关系报告尚未复用同类重验，第一/二轮重填27/15个已有样本，第三轮25个旧样本过期。** 本轮记录此边界，未为每次可恢复错误继续改版本；不以一轮成功或大量离线检查证明所有机制都已充分且必要。

### 同版冷启动结果

冻结提交`49f1c2e263c166138518cf6eaf78c8fbf50e81d1`，实现`779622c4`，runtime v16/domain v77。三轮均为ChatGPT订阅Astra/high、single_model、自动文本管理、最近3批图片、48请求/240工具/64候选，整案seconds/tokens=null。原六图，无旧稿/GT/开发者中途提示。并发1，运行中474项程序/登记/配置、HEAD及六图不变。

| 冷启动 | 首次整楼 | 完整进程耗时 | 终态与候选 | 请求/完整响应/工具 | provider tokens |
|---|---:|---:|---|---:|---:|
| v77-1 | 333.188秒 | 1552.873秒（25分53秒） | completed、exit0；主动交付candidate07 | 20/20/94 | 3,425,683，完整 |
| v77-2 | 343.841秒 | 1173.622秒（19分34秒） | completed、exit0；主动交付candidate08 | 19/19/95 | 2,813,577，完整 |
| v77-3 | 366.783秒 | 1202.817秒（20分03秒） | service_error、exit1；candidate07仅系统兜底 | 23/22/91 | 已知3,369,675；末请求未知 |

三轮均0重试、0截断恢复。前两轮finish后0请求、六份交付文件SHA与原finish/receipt一致、completion_valid且复用handoff。第三轮返回`subscription_sharing_usage_limit_exceeded`、retryable=false、usage_received=false；没有finish、task_completed=false、没有selection/finish attestation。兜底5份文件另行验真，不能冒充六文件正式交付。已知用量合计9,608,935 tokens只是小计；订阅费用未知。

前两轮runtime中的模型请求耗时分别1277.873/950.514秒，工具128.859/95.033秒，其余122.176/104.741秒；模型请求耗时包含服务等待与响应，不能全归为推理时间。当前未达到约10分钟的完整交付优化目标，也不能用一次前后时长证明图片配置的因果提速。

### 独立物理质量与行为

三份选定/兜底候选均匹配29/29空间、61/61开口位置及宿主、30/30门连接、47邻接；34外开口高度全部≤5cm，3144个源坐标符合10cm网格。各自六张回叠均实际目视。第三份为**终态后显式选择兜底候选的评价**，不增加自主交付成功次数。

以下每格依次为≤5cm／5–10cm／10–30cm／>30cm的对象数：

| 冷启动 | 房间边界（29） | 开口沿墙端点（61） | 外开口高度（34） |
|---|---|---|---|
| v77-1 | 17 / 4 / 8 / 0 | 39 / 22 / 0 / 0 | 34 / 0 / 0 / 0 |
| v77-2 | 17 / 4 / 8 / 0 | 37 / 24 / 0 / 0 | 34 / 0 / 0 / 0 |
| v77-3，兜底 | 16 / 5 / 8 / 0 | 37 / 24 / 0 / 0 | 34 / 0 / 0 / 0 |

三轮raw strict均保留31 severe（29房界、2层内墙汇总），没有改评分或临时放宽。独立谱系核对区分既有墙参考面约定、首次10cm量化与跨层联动；当前已核Lite物理范围可接受，并不表示全部原始边界≤5cm。空间最大原始偏差均约12.65cm，开口沿墙最大约7.41/8.12/7.84cm。第1轮六个开口修订均改善端点误差；第2轮六项修订中仅WE7改善，其余五项略增，仍在已核范围，不能把返工统称质量提升。notes-only尾部候选的物理数组与其直接父候选全等。

| 范围 | 实际行为与边界 |
|---|---|
| 模型角色 | 一个Astra处理全部图纸，无reader/协调员跨上下文重派；每轮有定位到对象的隔墙端点局修，未整稿重写 |
| v77-1 | 成功报告直接跟读；set_notes多余字段、墙位置缺offset两次错误均局部恢复；34高度/61标记首次通过 |
| v77-2 | 四次立面比较实际包含六组L→0反序锚点，首次通过且配对不变；34高度/61标记首次通过 |
| v77-3 | 12条高度缺direction，事务保留成功项，模型只重交失败12项；最终34个唯一对象确认、adopted_unapplied=0。服务中断时仍在看F2局部，不能推定下一步必然finish |
| 图片 | 实际wire逐SHA核验；引用次数283/254/312，峰值20/27/19图；第3轮312是已准备请求，末请求8图不能声称模型已消费。第2轮4次精确回读确为原图已不在工作集，重取后实际送达；其余两轮0回读，不作单因果结论 |
| 未覆盖 | 房间用途仍是模型推断，未独立评用途语义；室内门高、开关状态、未画出的竖向交通未独评；跨案例稳定性、其他模型及分工收益未验证 |

独评与观察不写原run：三轮原文件4422/4607/4467项与GT均保持；独评92项依赖和474冻结文件复核一致。实际浏览器打开第1轮candidate07整楼并切换F2，渲染可用；PNG导出未取得下载事件，未宣称导出成功。第2/3轮没有重复浏览器交互验收，查看器文件和回叠已核。

### 验证、证据与产品入口

v77领域改动32项定向通过20.26秒，独审无P1/P2；登记后既有真实冻结MCP目录节点通过6.89秒，未重复全量。终态后仅同步`product/README.md`、`product/config.example.json`和既有产品示例断言：示例改为本轮相同的single_model/Astra/no-time-limit/auto-text/image3参数，通用用户路径，不带sm25或GT。4项已有配置/非法输入检查通过1.36秒，独审无P1/P2，registry verify仍为v16/v77；这些入口说明改动不触及已测试runtime/domain，不追加整案。

| 冷启动 | 模型交付或兜底入口 | 独立评价入口 |
|---|---|---|
| 1，自主交付 | [BIM与查看器](D:/Sim-BIM-Agent/runs/sm25-harness-astra-v77-20261014-1/bim/delivery.html) | [平面、回叠与质量报告](D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/sm25-harness-astra-v77-1-evaluation/evaluation/index.html) |
| 2，自主交付 | [BIM与查看器](D:/Sim-BIM-Agent/runs/sm25-harness-astra-v77-20261014-2/bim/delivery.html) | [平面、回叠与质量报告](D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/sm25-harness-astra-v77-2-evaluation/evaluation/index.html) |
| 3，未自主交付 | [兜底候选](D:/Sim-BIM-Agent/runs/sm25-harness-astra-v77-20261014-3/bim/delivery.html) | [兜底候选独评](D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/sm25-harness-astra-v77-3-evaluation/evaluation/index.html) |

审计根为`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/`。前两轮各case目录有`independent-terminal-audit.json`，第三轮为`independent-terminal-failure-audit.json`；三轮均有`independent-feedback-terminal-audit.json`。前两轮独立质量audit SHA分别`90a8f389596d6db5f4955c77143ac7de22f3f2de7907b43baa22c4a2e70d5c9b`、`6dc67527d5e2135a4030c57e2734742efa0be4df0781af94f1b7defd68290a41`；第三轮必须读取带partial边界的评价，不能复用成功断言。产品入口独审`v77-product-example-independent-review.json` SHA`4f3013bb24ebbfdcdcebd8278ed0353a742f8b6f3eada593cb7dd0e1f1df9124`，XML`v77-product-example.xml`。

第三轮部分质量审计为`sm25-harness-astra-v77-3-evaluation/quality_partial-audit.json`，SHA`7e46ab6ac997a84db47e18db51a36aee04d4a2b296daf23df66a73068d37c655`，明确标记NOT_autonomous_delivery。

发布同步状态另补于本节末。后续应先处理已重复出现的空间关系状态负担，再在服务可用时补足同版/新版本的完成性证据并扩展案例；不自动追加模型运行，不把本轮两次成功推广为普遍稳定。

## 早期实施与试验记录（历史）

以下保留各版本当时的配置、判断和待办；当前状态以本报告顶部结论为准。

前五次冷启动使用了600秒硬预算，以下按当时配置保留历史记录；助手把优化目标实施成截止线的理解现已纠正。v70在604.22秒由模型主动交付，但随后多余请求超时且覆写选择来源；v71修复后634.17秒兜底；v72在335.83秒装配整楼，34条高度确认因重复reason契约被拒，627.04秒兜底，未finish。这些分别是收尾、接口与预算事件，不能把耗时超过10分钟单独等同建模失败。v73修复、独审、登记与15项正式节点已通过且尚未实测；下一步先取消整案硬时限，再验证完整交付与真实耗时。桌面尚未更新。

首版 runtime v11 / domain v69、实现 `4cbc3edb` 的Sol与Astra两次冷启动均在约6分钟装配整楼，但分别650.23／680.97秒超时兜底，未达到10分钟自主交付。两轮暴露的重复备注、记账浪费和10cm策略接线缺口现已修复，定向验证与独立审阅通过；后续版本 runtime v12 / domain v70、实现 `79d95dd7` 已登记校验，实际本地MCP节点10项通过（53.94秒），证据`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/preflight-v70/cb1493736f74/results.xml`。模型目录包含 gpt-6.1-sol 与 gpt-6-astra，不作为推理或建模成功证据。

本轮真实配置见 [run_sol61.json](run_sol61.json)：sm25原六图，single_model，ChatGPT subscription，gpt-6.1-sol/high；每次48请求/240工具/600秒，无总token上限，64候选上限（避免沿用分工较小上限）；首轮通过后同一冻结版本再做两次冷启动。配置检查已通过，未提供GT、旧稿或答案。

独立审阅修闭：异常提示全量回显、多个分页字段累计超量、差异报告现有hash未核验、失败回执单条审计超量，以及跨层更近匹配错误合并和多层尺寸传播缺口。两条模型路径复用有界JSON读取，成功/失败回执均有最终24KB总量边界，完整原文及hash保留。

| 定向检查（批次间不直接相加） | 最新结果 | 证据 |
|---|---|---|
| 几何、Lite、最终精度、装配 | 122通过，17.23秒 | `D:/Sim-BIM-Agent/cache/geometry-contract-reviewed-final.xml` |
| 单模型读取、异常及相邻接口 | 36通过，33.38秒 | `D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/single-bounded-final-v2.xml` |
| 角色回执最终边界 | 12通过，42.50秒 | `D:/Sim-BIM-Agent/cache/bounded-receipts-20261013-3.xml` |
| 角色失败继承/相邻试建 | 首批18通过、相邻23通过；旧指纹阻断项已在节点复验通过 | `bounded-drafts-20261013-1.xml`、`bounded-drafts-20261013-2.xml` |
| 几何独立反例复验 | 5通过，2.89秒 | `D:/Sim-BIM-Agent/cache/geometry-independent-review-20261013.xml` |
| 注册后真实本地MCP、目录与试建 | 10通过，49.76秒 | `D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/preflight/6208e4dcbec4/results.xml` |

旧稿确定性重放：读取上轮assembly_003的原submitted_plans，新代码2.96秒规整通过，最终source precision亦通过、counts为空；原文件hash不变。只证明同一已读草稿的装配缺口修闭，不证明自主冷启动或图纸质量，未读GT。摘要：`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/old-assembly-replay.json`。

体积核对：两层旧稿602/617KB分别变为5.35/5.32KB整稿投影；合成失败回执938,962→2,831bytes，failed/passed多字段汇总各22,628/23,559bytes，引用逐个校验原文hash。摘要：`D:/Sim-BIM-Agent/cache/harness-bounded-projections-20261013.json`。

既有对照：2026-10-12分工复跑87分47.64秒、180请求、0整楼交付；历史Sonnet结果的版本、模型服务与质量门槛不同，仅作为效率参照，不当作同条件A/B。

## 首轮真实冷启动：6.1 Sol/high

冻结 `aac66e15`，runtime v11 / domain v69，运行 `D:/Sim-BIM-Agent/runs/sm25-single-sol61-20261013-1`。原六图、配置及HEAD未改变，模型未获开发者中途提示或改稿，GT仅在终态后用于独立评价。没有重试、收费回退或补跑Sol重复案例。

| 项目 | 结果 |
|---|---|
| 第一层／第二层源BIM保存 | 启动后231.904／330.558秒，均一次成功 |
| 整楼装配成功 | 354.898秒，candidate_03 |
| 最后完整模型响应 | 397.968秒，仍请求工具；没有finish_bim或最终回答 |
| 终态 | time_budget_exhausted；系统选择最新完整候选，未由模型选定 |
| 兜底查看器／CLI退出 | 618.076／650.228秒；不计自主10分钟达标 |
| 调用 | 9请求／8完整响应，33工具全部成功，0返工、0重试 |
| 用量 | 已知393,192 tokens，最后一次未知；订阅无按量费用记录 |
| 耗时组成 | runtime636.879秒；模型560.813、工具9.017、其他67.049秒 |
| 回执体积 | 最大MCP文本22,312bytes，无大回执或上下文停止 |

最后请求等待198.797秒后超时。`actual_usage_exceeds_reservation`由seconds预留与实测约0.004秒之差触发，不代表token超额；不能仅凭本次超时断言模型生成、代理或服务队列中的哪一环慢。

终态后独立评价显式选择candidate_03，不能把评价者选择算成模型交付。29/29空间、61/61开口位置及宿主、30/30门连接匹配，无实质空间拓扑错误。外部开口高度34/34均≤5cm，29空间层底/层高/层顶最大偏差0。房间边界≤5／5–10／10–30／>30cm为21／2／6／0；开口沿墙为58／3／0／0，离墙>30cm为0。整体几何状态minor，既有单线/跨层规整惯例差异按原评价政策单列，未临时放宽。

仍未完成：高度证据定位绑定0/34，29空间用途unknown；室内开口高度、门窗运行状态、垂直交通未评。浏览器已实际打开交付页和三维查看器，并验证二层筛选；小侧栏下控制面板会遮挡模型，桌面视口可查看。

证据：`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/sm25-single-sol61-1/terminal.json`、同目录`independent-observer-audit.json`；评价摘要与可读报告在`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/sm25-single-sol61-1-evaluation/`。离线XML按测试身份去重212通过，原始结果与去重索引在`offline-checks.json`，不替代真实能力验收。

## 第二轮真实冷启动：Astra/high（v11/v69）

冻结 `a8c024da`，运行 `D:/Sim-BIM-Agent/runs/sm25-single-astra-20261013-1`。与首轮仅模型、批次与输出身份不同，原六图、质量条件、预算及程序相同。11请求均有完整响应，33工具中32成功、1次备注修订失败，无传输失败或重试；768,797 tokens完整、缓存0。所有输入、配置及HEAD保持冻结。

| 项目 | 从进程启动计时／结果 |
|---|---|
| 第一层／第二层保存 | 222.227／329.700秒，一次成功 |
| 整楼装配 | 358.073秒，一次成功，candidate_03 |
| 最后模型响应 | 598.704秒，仍请求修订；入工具前时间已耗尽 |
| 兜底查看器／CLI退出 | 623.443／680.972秒，未finish_bim，无最终回答 |
| runtime耗时 | 662.008秒；模型473.906、工具16.967、其他171.135秒 |
| 最大回执文本 | 22,182bytes，无大回执或上下文停止 |

独立评价空间29/29、开口位置与宿主61/61、门连通30/30，无实质错误；整体minor。房间边界分档21／2／6／0，开口沿墙61／0／0／0，34外部高度全部≤5cm；楼层标高与层高无偏差。用途更新因事务失败而仍为unknown；高度证据绑定、室内开口高度/状态与竖向交通未完成或未评。此轮查看器只核实产物存在，没有重复浏览器交互验收。

证据位于`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/sm25-single-astra-1/`和`sm25-single-astra-1-evaluation/`。评价器显式选择候选；不能把其通用“run did not deliver”标签解释为没有兜底页面，具体选择来源以terminal.json为准。

## 两轮暴露的确定性缺口与后续修复

1. **重复备注的不可修订状态。** 装配保留了两个完全相同的全局待办；模型逐字正确引用，`replace_note`却要求恰好出现一次，导致29用途更新与1备注替换整批失败。新逻辑只处理同field内完全相同的副本，全部替换、只插入一份新文本，记录旧文/匹配数/原位置；不同文本继续精确匹配，原子回滚与理由、来源保留。57项定向通过；独立重放真实30项事务及跨field/相似文本/回滚反例通过，几何除用途和审计外完全不变。
2. **记账重复还原请求。** 每张图片都还原并校验整份请求，最终收尾又重新累计。改为每次记账函数调用内只还原一次，跨请求/跨调用仍重新校验，逐图片仍验证bytes并使用自己的detail。30项定向通过。旧Sol九请求等价重放21.963→1.565秒，106→7次还原，所有记账字段及原receipt一致。该收益不解释最后198秒等待。
3. **10cm策略未接入单模型。** v69的单模型manifest只有自然语言scope，没有确定性Lite策略；实际走旧Q1规整。Astra正确保留了0.1m要求与工具0.3m反馈不一致的待办。因此前两轮也不能宣称满足10cm建模策略。现已把已有Lite10cm能力接入新drawings manifest、构建/修订/装配及最终源检查，模型audit不能覆盖可信策略；直接源BIM编辑与种子导入均拒绝离网格数据。保留原始观测和拓扑拒绝，不新增规整算法，也不更改既有0.30/0.60m关系门槛。45项定向、3项seed边界和4项黑盒有效通过；独立审阅发现的seed旁路已修闭并复验，无遗留P1/P2。旧两轮原稿的确定性重放均670个坐标全在网格内、最终源精度检查通过，原文件不变；此重放不算自主交付。

审阅与小证据：`note-independent-review.json`、`note-fix.xml`、`note-feedback.xml`在本报告cache根；`D:/Sim-BIM-Agent/cache/accounting-local-body-20261013.xml`和`accounting-local-body-equivalence-20261013.json`记录记账检查。Sol第9请求携带28张图；输入增长是观察到的负担，尚不能单凭一次超时证明因果，未据此新增上下文硬限或删除图像。

## 第三轮配置（已执行）

上述修复、定向验证与独立审阅已完成。Lite最终独审与源码hash见`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/lite-independent-review.json`，旧稿重放见同目录`lite-real-draft-replay.json`。

统一登记并冻结新版本后，使用 [run_fast_v70.json](run_fast_v70.json) 的Astra/high单模型路径，原六图、预算和质量标准不变。先独立冷启动一轮；只有主动完整交付、外部墙钟≤600秒且独立质量达标，才进行同配置两次重复。旧Sol/Astra结果和配置保留，不重写失败记录；桌面尚未更新。

## 第三轮真实冷启动：Astra/high（v12/v70）

冻结 `533e09f5`，运行 `D:/Sim-BIM-Agent/runs/sm25-fast-astra-v70-20261013-1`，外部启动2026-10-13 12:11:05.235951 UTC。六图、配置、HEAD及14项冻结程序文件不变；中途无人工提示、改稿或预算调整。原配置后两次重复尚未启动。

| 项目 | 外部启动后时间／结果 |
|---|---|
| 两层首次试建 | 225秒起；均被原始隔墙悬空端点检查拒绝，尚未进入网格变换 |
| 两层局部修订成功 | 273.655／282.785秒，candidate_01／02 |
| 整楼装配成功 | 325.640秒，candidate_03 |
| 用途及备注更新 | candidate_04／05均成功；重复备注缺口未复现 |
| 正式交付请求／成功回执 | 597.016／604.223秒，candidate_05，原回执agent_selected |
| 交付JSON／HTML首次创建 | 600.699／602.022秒（Windows创建时间）；均超600秒 |
| CLI退出 | 625.644秒，exit1，time_budget_exhausted |
| 调用与用量 | 13请求／12完整响应，35工具，无重试；已知1,127,989 tokens，缓存0，最后一次用量未知 |
| runtime组成 | 611.671秒；模型479.000、工具75.489、其他57.182秒 |

本轮确有模型主动选择并完成finish_bim，不能抹去该事实；但真实正式交付已超过600秒，仍未通过目标。finish之后runtime继续第13次请求，超时后finalizer又把同一candidate_05的磁盘交付标记覆盖成`latest_complete_fallback_not_agent_selected`。原始成功回执在event-000222；覆盖后的JSON/HTML与终态也保留，不能混为同一交付来源。

独立评价：29/29空间、61/61开口位置及宿主、30/30门连接均匹配，无漏、多、错连；34/34外部高度≤5cm；实际源3144个坐标全部满足0.1m网格。房间边界≤5／5–10／10–30／>30cm为14／6／9／0，开口沿墙31／30／0／0。29/29空间用途为inferred且有依据。**原评价器overall=severe，31项墙线变化，没有命中旧规整惯例例外；不能只引用摘要substantive_findings为空就宣称质量通过。** 最近网格量化与原有跨层对齐的可追溯性质正在单列核对，不改旧评分、不临时放宽阈值。

高度证据绑定仍0/34：10条dimension_chain观测全部漏direction，其中6条另漏origin_m，schema拒绝正确。模型读取首条错误后保留未完成说明，没有完成绑定；不能以高度数值符合GT代替证据闭环。室内开口高度、开口状态及竖向交通仍未评。实际交付页和候选查看器已在浏览器打开，F2筛选及渲染已验证，临时页与服务已关闭。

独立观察与时间证据：`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/sm25-fast-astra-v70-1/`下`terminal.json`、`independent-observer-audit.json`、`claim-interface-diagnosis.json`、`browser-check.json`。独立质量报告、平面与回叠在同级`sm25-fast-astra-v70-1-evaluation/`；评价8.38秒，模型调用0，1995项run文件及GT哈希未变。

后续只修已确认的负担：成功交付后的多余模型调用与来源覆盖；按claim既有type分派校验，移除无关union分支报错且继续严格拒绝缺字段。装配26.53秒与交付7.21秒的本地成本先用原稿确定性重放定位，不据事件间隔臆测函数耗时。实现与独立审阅完成后才冻结下一轮，仍不以本轮近达标代替稳定达标。

## v71：移除已定位的额外工作

- 单模型在完整工具批次结束后，由domain核验成功finish的候选、源模型及六份交付文件的哈希；完整交付直接结束runtime，不再多请求模型或重新生成并覆盖选择来源。保留通用runtime与BIM判断的边界；部分交付、后续写入、文件变化与失败均不能触发完成。工具完成和模型最终文本回答分别记录。恢复及最后收尾仍复核绑定证据。
- Claim按既有`type`辨别值类型。必需字段与严格拒绝不变；真实10条错误请求仍全部拒绝，聚合回复由无关union错误分页变为7,769bytes，模型可直接看到缺失字段。claims及事务39项通过，35.20秒，独立反例复核通过。
- 装配内部预检不再反复复制随后丢弃的规整审计；公开编译仍默认返回完整、独立的metadata。对同一原稿唯一非profile重放，`regularize_plan_stack`从14.808降到5.845秒（60.53%）；完整result、report、两份plan及两份proposal的canonical SHA逐项一致。原1995项运行文件与输入未变，119项定向通过，5.07秒，独立审阅无P1/P2。这只证明内核等价与性能改善，不代表整案600秒或质量通过。

收尾通用runtime10项通过（2.23秒），报告消费者15项通过（0.59秒）。独立审阅发现最终复验失效后仍可能报completed的问题，已改为`completion_state_changed`，不再标记任务完成；同批次finish后的只读调用超时会保留有效选择，但不冒充整批完成。独立复审完成后统一登记，并原样运行带版本指纹检查的本地MCP节点17项。实现阶段曾用cache测试入口以release lookup代替release verify验证当前源码，30项通过（R3 15项、报告15项）；该结果明确不算正式冻结节点，正式节点必须在登记后重新验证。

下一轮配置为[run_fast_v71.json](run_fast_v71.json)，仍是Astra/high、原六图、48请求/240工具/600秒，无总token上限、无人工介入。先一轮，严格通过后才同配置再两轮。质量保留原始严格评分，同时独立核对有依据的10cm变换；不将所有墙线差异一概归为允许规整。桌面尚未更新。

小证据：cache根的`claims-discriminator.xml`、`geometry-audit-copy-targeted.xml`；v70运行cache下`claims-discriminator-independent-review.json`及`assembly-profile/optimized.json`、`assembly-profile/independent-review.json`。

收尾最终独审：`sm25-fast-astra-v70-1/completion-final-independent-review.json`，明确最后P2已修、无剩余P1/P2，源码SHA已记录，允许进入统一提交、登记与原样正式R3节点；真实模型调用0。

实现提交`ea3b866a`已登记为runtime v13 / domain v71，verify通过。正式本地MCP节点原样执行`tests/test_runtime_r3.py`与`tests/test_runtime_frozen_tools.py`：26项通过，96.88秒（含新增收尾R3 17项），未使用lookup替代或调用真实work model。证据`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/preflight-v71/aec7dad3324c/results.xml`。

v70补充质量归因：把hash绑定的规整前原稿（模型已修正悬空端点）交给同一个原评价器、reference和conventions，仍为severe；29房间中3项命中原约定、14项minor、12项边界severe，另两层internal boundary仍severe。原稿、评价政策与reference未改。该证据排除了“31项都由10cm造成”的说法；边界位置与真实结构含义另行核对，不把标签直接解释为31处漏墙。证据`sm25-fast-astra-v70-1/boundary-attribution/pre-grid-conventions-summary.json`。

后续逐条独审已完成：12项中8项原稿最大偏差为2.3–4.3cm，属既有≤5cm“好”分档；4项源于西侧两条物理隔墙的约半墙厚参考面偏移，各影响两侧房间。240mm墙厚与旧模型政策允许的参考面转换有原图和先前冻结观察支持；现convention ledger只列东侧相同类型，缺西侧条目，原strict仍保留severe。原稿与参考47对同层共享墙邻接全等，源模型规整前后拓扑/宿主不变，两层外轮廓误差<1.4cm，标高/层顶/层高无偏差。独审结论是v70已核源BIM几何符合当前Lite产品要求，不能把旧strict标签单独当物理错误，也不能用对象数量单独宣称质量。高度绑定0/34、用途推断、内门高度假设及未画竖向交通仍为交付披露边界。完整31项映射、原原则与证据hash：`sm25-fast-astra-v70-1/boundary-attribution/strict-findings-with-original-conventions.json`。

## 第四轮真实冷启动：Astra/high（v13/v71）

冻结`747f283b`，外部启动2026-10-13 13:01:35.661759 UTC，运行`D:/Sim-BIM-Agent/runs/sm25-fast-astra-v71-20261013-1`。全部472项登记源码及registry/config共474项、六图、HEAD保持不变，无人工介入。外部634.170秒，runtime607.397秒，`time_budget_exhausted`；CLI exit0只表示保存兜底产物，不是目标通过。

| 项目 | 外部启动后时间／结果 |
|---|---|
| 首次模型请求 | 29.538秒，外部计时包含准备阶段 |
| 首次两层build | 267.388／267.942秒；61个开口均缺source_refs，未生成source |
| 补来源后再次修订 | 372.776／373.370秒；两层均因5.5–6px隔墙端点脱接拒绝 |
| 两层源BIM | 411.678／420.980秒 |
| 整楼装配 | 456.716秒；调用到回执11.761秒，不能与上轮当严格A/B |
| 最后完整候选 | candidate_04于580.505秒保存，之后仍审计和检查 |
| 正式交付／终态 | 无finish；12请求/11响应、42工具、0重试，系统fallback选candidate_04 |

已知用量918,179 tokens，末次usage未知；runtime模型510.655、工具47.578、其他49.164秒，外部另含26.773秒。装配实际工具计时11.234秒，与调用/回执事件窗口11.761秒分别报告。末次预算超额仅seconds：预留8.055686、实际8.078秒，超0.022314秒，不是token超额。

新成功收尾路径本轮未触发，不能宣称真实覆盖。原配置不重复。只读诊断确认61项开口update仅增加source_refs、几何0变化，共11,566bytes操作；对应请求到响应102.422秒（包括服务等待，不等于纯生成）。更早的build同次已有几何compile错误，但回复用`regularization_error or error`覆盖成来源字段错误，迫使顺序返工。下一版只处理可靠的工具绑定来源继承和两个已知错误同时反馈，不降低几何检查或伪造高度证据。

独立质量评价完成；原run2060项文件前后hash全等。原稿依原评价器/conventions为minor，6房间及两层汇总命中8项既有约定；最终旧严格评分仍31项severe，未改分。原稿/参考/最终三者47对共享墙邻接全同，29房间、61开口位置/宿主、30门连接匹配；最终外轮廓与参考近乎精确一致，标高/层高/层顶无偏差。全部3144源坐标在0.1m网格内，526原读数→采用值逐项吻合且为最近网格，最大变换4.9564cm；另两次跨层对齐各10cm、影响4个空间，关系不变。candidate03→04无物理几何变更。独审认为当前Lite已核几何可接受；运行和主动交付仍明确失败。

≤5／5–10／10–30／>30cm分档：房间16／5／8／0（最大12.649cm）；开口沿墙37／24／0／0（最大8.106cm）；法向20／7／34／0（34项为外墙代表面差、宿主匹配）；外部高度34／0／0／0。29用途均明确inferred：office19、corridor2、meeting7、lounge1；语义正确性不因此被证明。正式height bindings仍0/34，内门高度假设、运行状态、未画出的垂直交通/空洞/假楼板及浏览器交互未独评。

证据：`sm25-fast-astra-v71-1-evaluation/independent-quality-audit.json`及`sm25-fast-astra-v71-1/boundary-attribution/strict-findings-with-original-conventions.json`；原有严格评分与测量值全部保留，没有以修改阈值制造通过。

## v72：来源关联由工具承担，同次检查错误并列返回

仅当开口`source_refs`缺失时，工具依据已经校验的原图名称与SHA建立caller declaration输入关联；明确标记观察和高度证据未验证。显式refs保持原值，无效refs继续拒绝；不扩展其他对象，不修改compiler、Lite规整或高度绑定逻辑。原始请求存入submitted_plan，采用plan与独立source_ref_bindings审计分别保存，模型只收到数量、file/hash/scope。已有regularization与compile两个独立错误同时返回各自repair hint，避免后者被`or`隐藏。

用v71首次两个原始build参数原样离线重放，31+30开口只增加可信输入关联；除新增refs外，整个plan（含所有几何/显式字段）的canonical SHA与原稿相同。首轮就返回原draft003/004相同端点脱接错误，没有生成候选，几何门槛未降低；可见回执13,389／13,525bytes。2060项原run文件及原请求字节均不变，模型与GT读取0。小证据：`D:/Sim-BIM-Agent/cache/v71-opening-provenance-replay-20261013.json`。

定向验证去重10项通过：首次6项4.27秒，最终6项3.24秒（交集2项添加compact回执断言后复验，不能直接相加12）。包含遗漏refs继承、四种显式无效refs继续拒绝、双错误反馈、失败稿/内部错误保护及24KB边界；没有release校验绕过、MCP或模型调用。XML为`D:/Sim-BIM-Agent/cache/opening-provenance-feedback-20261013.xml`与`opening-provenance-feedback-final-20261013.xml`。独立审阅通过，无剩余P1/P2；确认可信来源在原图manifest SHA验证之后绑定、height coverage没有虚增。独审源码SHA与证据位于`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/v72-provenance-independent-review.json`。

下一轮为[run_fast_v72.json](run_fast_v72.json)，只更改运行身份，Astra/high、六图、预算与任务范围相同；登记并验证后冷启动一轮，目标通过才同版本再两轮。不会把离线预计省掉102秒直接当真实提速。

实现`c537f29f`已登记并verify为runtime v13 / domain v72。原样正式本地节点13项通过（68.97秒）：frozen tools 9项、成功finish 2参数、plan原图来源/重校正和编译失败保留原稿2项。无release校验绕过或work model调用，复用v71其余完整R3证据。XML：`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/preflight-v72/69b3eb46ac03/results.xml`。当前可冻结进行真实冷启动；桌面未更新。

## 第五轮真实冷启动：Astra/high（v13/v72）

冻结`010be1a3`，外部启动2026-10-13 13:34:04.647329 UTC，运行`D:/Sim-BIM-Agent/runs/sm25-fast-astra-v72-20261013-1`。474项源码/registry/config、六图及HEAD全部未变，原run1942项文件在观察/评价期间未变。无人工介入，后两次原配置重复未启动。

| 项目 | 外部启动后时间／结果 |
|---|---|
| 首次模型请求 | 19.291秒 |
| 首次F1构建 | 159.878秒，13个partition缺source_refs；31opening已由tool关联 |
| 次个响应 | 同时补13个partition.refs并首次生成F2；95.486秒请求不能全算补字段成本 |
| 两层源BIM | 292.048／300.855秒，均先经过端点脱接修复 |
| 整楼候选 | 335.828秒，candidate_03；装配工具计时12.453秒 |
| 高度确认 | 530.737秒返回34条confirm；该请求136.586秒，事务约542.95秒业务失败 |
| 正式交付／终态 | 无finish；627.036秒CLI退出，time_budget_exhausted，candidate_03系统兜底 |

10请求/9响应、32工具、0重试；已知552,101 tokens（缓存6,528），末次usage未知。runtime609.399秒=模型521.219+工具47.079+其他41.101；最长MCP文本21,836bytes。本轮budget_violations为空，最后耗时66.016秒不超过预留66.022814秒，不能套用上一轮seconds超额。CLI exit0不是目标通过，新completion成功路径仍未真实触发。

事务首因：34条claim全部有理由、已记录/采纳/解析，31个window和3个door目标存在，声明z与当前proposal逐值一致；但各自operation未重复写reason，统一被update_window/update_opening校验拒绝。15,165bytes可见回复完整保留34条错误，未分页遗漏。模型已收到8,753bytes claims参考；正文“省略reason使用claim.reason”没区分entry与operation，示例含operation.reason。下一步修缺省理由继承，不要求模型重抄34遍，也不放宽确认值必须等于几何的门槛。诊断与原请求位于cache根`v72-claim-transaction-diagnosis.json`、`v72-claim-transaction-original-entries.json`。

独立评价认为已核物理几何可接受：29房间、47对共享墙邻接、61开口位置/宿主、30门连通匹配；两层外轮廓近乎精确、z/层高/层顶无偏差。526项最近网格采用值逐项吻合（最大4.9654cm），另4次跨层对齐各10cm、影响13空间且关系不变，全部3144源坐标在0.1m网格。旧strict31 severe原样保留；原稿17房间+2层severe中，5个约12cm项位于既有半墙规则段，应用旧规则后的残差2.20–4.04cm，其余12项2.13–3.69cm，没有据标签臆称错分空间。

≤5／5–10／10–30／>30cm分档：房间17／4／8／0（max12.649cm）；开口沿墙36／25／0／0（max8.106cm），法向20／7／34／0，后34项为代表面差；外部高度34／0／0／0。**用途29项均unknown，高度绑定0/34**，不能沿用v71用途完成结论；内门高度、开关状态、未画出的垂直交通和空洞未独评。此次未重复浏览器验收。

证据：`sm25-fast-astra-v72-1/independent-terminal-detail.json`、`root-freeze-check.json`，`sm25-fast-astra-v72-1-evaluation/independent-quality-audit.json`及case下`boundary-attribution/`。

## v73后续范围

原六图、Astra/high、600秒配置保留，准备[run_fast_v73.json](run_fast_v73.json)。仅修claim-bound操作理由的可靠缺省继承，并将已有原图像素来源关联统一应用到必填的partition与opening；不自动补结构化尺寸、标注、height claims或修订判断。原稿/显式值/审计保留，独立revise_bim理由门槛不改；先验证原事务与几何不变，再独审、登记及正式节点，才启动下轮。不会直接换配置碰运气。

原34条entries原样离线重放已全部confirmed，外部门窗高度绑定0→34；声明与当前值一致，proposal、source及物理几何SHA不变，新candidate为0，只有cache副本的height_coverage审计更新。每条原请求保留，理由继承单独记路径；显式空/null仍拒绝、无claim绑定的编辑和独立revise不自动补理由。原F1请求首轮关联13partition+31opening，seeds不变，直接暴露与原稿相同的两个6px端点问题。原run1942文件hash全等，模型/GT读取0，回执分别9502/13601bytes。证据：cache根`v73-redundant-fields-replay.json`。

定向18项有效通过：初批17pass、1项测试错误地期待返回值而实际应抛ValueError，修正仅该断言后单项通过；没有生产失败。XML为`D:/Sim-BIM-Agent/cache/v73-redundant-fields-targeted-20261013.xml`与`v73-reason-scope-final-20261013.xml`。完整确认本地wall30.532秒、CPU30.219秒，功能通过不代表提速充分；先定位重复计算，再决定进入实测。

同原34条请求的一次cache cProfile定位：插桩wall40.177秒（不能当未插桩耗时），35次located_heights累计28.514秒，内含project22.263秒；同一candidate源哈希与proposal哈希在每条历史记录中重复序列化。优化范围限单次project调用的惰性哈希复用，跨调用仍重新读盘验证，不省略每项确认/报告与部分提交记录。另一个只读确认的接口缺口是space_seeds已有role、却不接受role_evidence，导致单模型需要尾部逐间重复set_space_role；将复用已有RoomRoleEvidence规则打通可选seed依据到源BIM，裸role不自动获证据、不推断房间用途或改变空间拓扑。这两项完成定向验证和独审后再冻结。

seed接线已完成：可直接在`space_seeds[].role_evidence`声明role/basis/source_refs/assumptions，外层role可省略；重复声明时须目录归一后一致。复用现有校验，inferred必须有假设、unknown配对，裸role仍unrecorded；首次source和两层assembly都保留依据，拓扑全等。guidance替换强制后置录入语句，没有新tool或状态机。用途范围去重66项通过（45基础、21工具/guide；首次黑盒测试误取不存在draft_id，已修正该断言并复验），独审无P1/P2。证据`D:/Sim-BIM-Agent/cache/seed-role-evidence-review-20261013.json`及其两份XML。v71尾部29条set_space_role共5360bytes，位于一个含其他检查的70.305秒请求；这不是可直接承诺节省的耗时。

局部哈希复用完成。原34事务一次未插桩对照wall30.532→19.210秒、CPU30.219→19.125秒，减少11.322秒（37.1%，非统计稳定性承诺）；34confirmed、height绑定0→34，完整transaction返回相等，103个claim审计文件逐字节相等、103条逐项工具结果相等（日志时间不比较），height报告逐字节相等。原candidate proposal/source与run1942文件不变，模型/GT读取0。3项性质检查通过：同candidate各自expected hash仍逐条比较、跨调用篡改能检出、候选来回切换恢复后输出一致。证据cache根`v73-local-hash-replay-summary.json`及`D:/Sim-BIM-Agent/cache/v73-project-local-hash-20261013.xml`。

实现`ca81fdd8`已登记为runtime v13 / domain v73并verify。原样正式本地节点15项通过，58.61秒：frozen tools、成功finish含恢复、原图来源与重校正、编译失败保留原稿、首build用途到两层装配、claim事务MCP与只读边界。没有lookup替代、release校验绕过或work model调用。XML：`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/preflight-v73/75ac9dd6b531/results.xml`。五份当前定向XML合并去重76项有效通过，与正式节点存在交集，不相加充数。

总独审完成，无剩余P1/P2；完整结果/103份审计/103条工具结果/高度报告由审阅者独立读盘核等价，11文件SHA留档。`v73-final-independent-review.json`的600秒硬验收文字属于用户最新澄清前的审计范围，已由本节新要求覆盖；源码语义结论仍有效。v73真实冷启动未启动，未为了改目标追写旧运行证据。

## 取消整案硬时限，保留十分钟优化目标

用户澄清后，下一轮改为[run_fast_v74.json](run_fast_v74.json)：原六图、single_model、Astra/high、48请求/240工具、无总token上限；`limits.seconds`与`maximum_seconds_per_case`均明确null，`target_seconds_per_case=600`仅为指标。任务文字明确完整检查与交付优先，不因十分钟到点切断。前三轮case身份仍各自独立，无旧稿/GT/开发者辅助。

当前入口/预算实现原来强制正seconds，直接删字段不能取消限制。最小接线范围为单模型可选整案时限、独立实际耗时记账/恢复及反馈；分工等未接通路径明确拒绝null。没有用大常数冒充无限制。无整案时限时，不为模型生成套一个绝对300秒期限；300秒仅用于HTTP I/O连续无数据等待保护，既有认证/目录20秒保护及请求失败重试保留。有限预算路径与实际seconds结算仍需定向验证和独审。外部观察器已去掉600秒通过判定，只保留优化参考；v73/v74均尚未启动真实运行。

可选时间接线已完成并停编：RunLimits与请求时间预留支持明确null，账本仍保存实际seconds，checkpoint/receipt/finalizer独立记录真实elapsed；JSON中没有Infinity或伪造大时限。`--no-time-limit`只开放给单模型，CLI默认及有限配置保持。无期限工具自身TimeoutError改为operation_timeout，避免误判整案耗尽。新配置check与command通过，确实生成`--no-time-limit`。

有效离线去重37项通过：新增15项覆盖超过600秒继续完成、跨恢复累计elapsed、JSON null、网络idle失败重试、其他预算仍生效；有限旧预算及无期限child等待有限root22项通过。初批3项失败是测试夹具预期错误（恢复更早被身份/limits校验拒绝、FastMCP返回list的适配），只修断言后3项通过，无放宽产品检查。XML为cache根`v74-no-time-limit-new-20261013.xml`、`v74-no-time-limit-fixtures-final-20261013.xml`、`v74-time-limit-existing-regression-20261013.xml`。新增真实MCP R3以模拟时钟901秒完成finish，待登记后原样执行；不需要真实等待901秒，也未调用模型。

实现`74515a62`登记为runtime v14 / domain v74并verify。总独审无剩余P1/P2，11生产/6测试SHA及37项证据在cache根`v74-no-time-limit-independent-review.json`。登记后的原样完整R3与frozen-tools节点共27项通过，90.74秒，包含模拟901秒后成功finish、保留agent_selected且无多余请求。没有release绕过或真实work model调用。XML：`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/preflight-v74/ccb1214701ed/results.xml`。可冻结按新目标实测，尚未更新桌面。

## 第六轮真实冷启动：无整案时限，完整交付通过，速度仍待优化

冻结`3d9c6bdd`，runtime v14/domain v74，原六图、Astra/high单模型。2026-10-13 14:56:43.557747 UTC外部启动，运行`D:/Sim-BIM-Agent/runs/sm25-fast-astra-v74-20261013-1`；474源码/registry/config、HEAD及六图全程不变。开发者没有补稿、派工、提示或中途改预算。

| 项目 | 外部启动后时间／结果 |
|---|---|
| 首次模型请求 | 27.211秒 |
| 两层源BIM | 299.291／441.760秒，首次构建均通过 |
| 首次整楼 | 493.504秒，candidate03，装配工具15.218秒 |
| 七处开口修订后整楼 | 1060.969秒，candidate06，第二次装配工具5.860秒 |
| 高度与用途 | 34外开口全部located_confirmed；29用途均inferred并有依据/假设 |
| 正式交付 | 2396.363秒，finish_bim成功，agent_selected candidate07 |
| 完整退出 | 2433.734秒（40分34秒），completed，复用handoff；finish后0请求、0工具 |

单轮自主完整交付通过；10分钟优化目标未达，尚不能声称重复稳定。runtime2385.073秒＝模型2083.140＋工具142.201＋其他159.732；外部另含48.661秒。24请求/22完整响应/98工具；一次流中断、一次connect失败均按既定策略恢复，共2次重试。已知4,772,714 tokens只是小计（input4,731,594/output41,120/cache46,080），另2失败请求usage未知。无预算违例，没有时间耗尽。

独立质量在现行Lite已核范围内通过：29空间、47物理共享墙邻接、61开口位置/宿主、30门连接匹配；两层外轮廓、标高/层高/顶高无实质偏差，3144坐标全在10cm格。七处开口修订仅各改变端点10cm，全部沿墙误差下降；03→06其余物理数组全等，06→07全部物理数组全等。原strict的29房界＋2内墙汇总severe原样保留；原准备稿经预先登记的半墙参考面规则诊断，29房界残差均≤4.253cm。最近网格最大变换4.989cm，另两次跨层10cm对齐影响5空间，拓扑/宿主/连通未变。

≤5／5–10／10–30／>30cm分档：房间17／4／8／0（max12.649cm）；开口沿墙37／24／0／0（max7.838cm），法向20／7／34／0（后34项为代表面差）；外部高度34／0／0／0。用途GT语义、未画出的竖向交通/空洞、内门高度及开关状态未独评，保留模型假设。六张回叠人工检查未发现新增实体错误。浏览器实测交付页、整楼渲染及F2切换成功；观察到一条未归因MutationObserver错误，页面自身无此符号，不能宣称console全净。临时浏览器与本地服务均已关闭。

原run4280文件和GT在独立评价前后全等。证据：case目录`independent-observer-audit.json`、`independent-lifecycle-and-context-audit.json`，评价目录`sm25-fast-astra-v74-1-evaluation/independent-quality-audit.json`（SHA83cd69d3c231e1ca21d638e5c5eb55374e70dc4b3df33a167107cab40be9131f）。完整handoff六文件hash、最后tool批次及零多余请求均经独立复验。

### 本轮发现的两处可避免负担

1. 图片历史每轮完整重发：24请求累计986张引用，实际55种不同SHA，931次为首次后的重复；最终请求66图、448,736实际input tokens。累计base64图片payload约162MB不是vision计费token。默认token投影未接通已有图片归档机制，不能只调低max_images淘汰整个tool interaction。
2. 仅说明文字变化使已完成开口回查变stale：06→07几何/宿主/图纸均不变，完整source hash变化后4份报告失效，回执要求not_reviewed。模型又录入同样61marks；box、opening_ids、space_ids、basis等观察字段全等。对应请求123.480秒、426,478input/4,027output。应由现有kernel在当前source/同图/标定上重新验证原观察并保存新报告，不能盲继承旧pass。证据`independent-notes-only-review-attribution.json`。

据此调整下一步：先做这两项定向减负，离线性质验证、独审、登记冻结后再冷启动。v74后两轮未启动，避免重复两次已有明确负担的40分钟路径；这不构成稳定性通过。图片策略只归档模型可见图片，完整历史不删，初始实际附图/最近工具批次/未送达图/精确重读图保留，旧图有按SHA回读入口。原六图通过工具提供，并非初始附图，不宣称始终常驻。当前批次内SHA去重暂不做，防止伪造多来源送达状态。另发现claim_status等小型回执超过24KB，最大46,475bytes；本次只记录，不扩大同轮修改面。

## v75：图片历史与开口观察的定向减负

下一轮配置为[run_fast_v75.json](run_fast_v75.json)：Astra/high、single_model、原六图、48请求/240工具/64候选、无总token和整案时间上限；10分钟仍仅为优化指标。新增`image_history_batches=1`，默认未启用的其他路径保持原行为。旧图替换为view ID、SHA及本任务内只读回读参数；运行初始实际附图、最近图片工具批次、未成功送达图片及精确回读受到保护。完整历史和证据未删除，保留图片超过目标时不静默截断；重试与恢复沿用同一送达记录。

仅note/use事务且完整物理内容、父候选、原图bytes和标定一致时，旧开口观察可以由kernel在新source上重验，产生新报告与旧报告哈希引用。不是继承旧pass；几何变化、改回原位或异常旧报告不会被当成已验证。v74的4份观察在独立cache重放中1.733秒完成，61个标记无需模型重录，新报告的kernel结果与真实后续重录全等。此耗时是确定性重放，不能等同下一轮模型节省时间。

定向离线当前有效去重：图片20项、开口重验48项、配置/CLI 8项。图片最初夹具存在索引/排序/批次边界错误，校正后复验通过；开口测试首次标定夹具越界已校正。独审另找到旧报告observations/location_check非对象时的异常路径，已补显式拒绝。新测试模块纳入node清单；登记后还需原样验证Runtime入口的真实MCP工具目录、版本哈希及完成后恢复。此处尚未报告任何v75真实模型结果。

独审最终无剩余P1/P2，记录为cache根`v75-image-projection-independent-review.json`（SHA55247476f5c3a7509614d318000c4d8b6977f37c7020d061f17f5b9befc66d9e）及`v75-opening-revalidation-independent-review.json`（SHAd3bbc99b0531388b51bcdb7f797485036824b40f229872e9b3a1a35eb788c8b7）。真实v74末次请求event545的只读投影66图/55SHA→4图/4SHA；62个旧图块变精确引用，文本/tool协议和完整history哈希不变，904个实际读取文件不变。未读取GT或调用模型，不能据此推算整案耗时。

实现`73362479`已登记runtime v15/domain v75（20261014）并verify，所有旧registry版本记录语义保持不变。登记后原样执行11个正式本地节点全部通过，37.47秒：frozen catalogs/role边界、notes→use→move→restore→notes、Runtime opt-in工具版本哈希、完整交付与完成后恢复。XML：`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/preflight-v75/945b04447368/results.xml`。正式节点与既有定向结果有交集，不相加充数；无真实模型调用。接下来冻结源码/配置/HEAD后启动v75首轮。

## 第七轮真实冷启动：v75有效交付，CLI后置报告异常

冻结`38cf36cd974b7a7ed537f9636491a449bb6025b4`，runtime v15/domain v75、Astra/high、图片最近1批、无整案硬时限。2026-10-13 16:13:47.723095 UTC启动；run为`D:/Sim-BIM-Agent/runs/sm25-fast-astra-v75-20261014-1`。474源码/registry/config、HEAD及六图全程不变；没有开发者建模干预。

| 项目 | 结果 |
|---|---|
| 首次两层源BIM | 464.568／473.722秒；首build各遇端点dangle后自主修订 |
| 首次整楼 | 535.289秒（8分55秒），candidate03 |
| 高度证据 | 1074.528秒时34/34 located_confirmed |
| 正式交付 | 1823.003秒，finish_bim主动选择candidate04；完成后0请求、0工具 |
| 完整进程耗时 | 1852.046秒（30分52秒），比v74少23.9%；10分钟目标未达 |
| 运行与进程边界 | receipt completed、delivery有效、六handoff hash匹配；CLI exit1，后置行为报告崩溃 |
| 请求与工具 | 28请求／27完整响应／125工具，1次响应流错误按原策略恢复 |
| 已知用量小计 | input4,024,554、output43,272、合计4,067,826，cache27,136；1失败请求usage未知，订阅费用未知 |

runtime1812.914秒＝model1487.813＋tool182.123＋other142.978。CLI的异常发生在`write_behaviour_report→summarise`：合法有界`claim_transaction.entries`回执是引用字典，统计器仍当list迭代字符串并调用`.get`。交付文件没有因此失效，但不能称端到端干净退出，也不能以此轮宣称稳定。

图片策略真实wire累计134图（55种SHA），累计1291个`archived_image`是文本引用，不能混算图片。22次本地回读返回注册原字节，70个带图执行均有精确送达记录。只保留1批也促成重复回读：固定行为对照前19次回读，保留2批可同时看12张，3批可看19张；累计引用/单请求峰值从1批60/7变2批116/13、3批168/17。此为可见性反事实，不是速度保证。图片减少后，末wire仍有约863,773B工具回执、157,409B调用声明、116,316字符加密推理；没有`previous_response_id`隐式历史。文本历史仍是明确负担。

物理质量在现行Lite已核范围通过：29空间、61开口与宿主、30门连接匹配，47邻接在原稿→grid→装配→交付全等；3144源坐标在10cm格。房界≤5／5–10／10–30／>30cm为17／4／8／0；开口沿墙38／23／0／0；外部高度34／0／0／0。raw strict原31severe完整保留；原稿按既有参考面规则最大残差0.4002mm，网格最大坐标变换F1 4.377cm/F2 5cm，另1处F1 Ediv2从y16.0→16.1作跨层10cm规整。03→04全部物理数组全等，仅4条notes。29用途均inferred且有依据/假设，内门高度/开关状态等未独评。六张叠图已目视核验；浏览器实际渲染与F2切换成功，本次捕获warn/error为空，临时页面及本地服务已关闭。

独评前后原run5138文件与GT未变。质量审计`sm25-fast-astra-v75-1-evaluation/independent-quality-audit.json`（SHA6f2c5f23c259298c2445c975705af9c1bbec7319521b23843a5c599e2e32114f）；生命周期、图片和CLI边界在case目录独立审计中。

本轮新增明确减负项：首次4份开口回查的61marks中53项只缺可空`note`键，原位置信息、ID、空间关联、basis齐全；补note后的所有其他观察字段全等，却增加2个模型请求、124.943秒生成。v74也有同样问题（49/61缺note）。将note设为可省补充文本、改善精确字段错误与reference路由，不改物理检查。尺寸链direction则必须明确，因为+1/-1改变真实高度；不以默认值伪造依据。另修行为统计的有界报告解析。v75其余两例未运行。曾准备下一轮6.1 Sol/high、图片3批与文本软压缩组合；用户进一步明确目标后，该候选已搁置，未启动。

## 2026-10-14：以充分且必要重新核对路径

用户明确“提速不是主要目的”，先让 harness 充分且必要，使高智力模型能够快速稳定交付。按信息是否可用、模型要求是否服务实际判断、修复及完成条件是否清楚检查现有路径，不把缩小上下文、切模型或减少检查本身当作进展。10分钟保留为软优化指标；没有整案硬截止。

已准备但未执行的速度候选配置保存在`D:/Sim-BIM-Agent/cache/harness-fast-path-20261013/v76-speed-candidate-not-launched.json`，从repo移除时已核副本SHA一致。下一次实测配置待下列完整路径检查后确定；本节不构成该候选已启用或已验证的声明。

已完成并独审的修复：

| 项目 | 可观察结果 | 验证边界 |
|---|---|---|
| 开口回查可省note、精确字段错误、正确reference | v75原四份请求61 marks不补写即可通过，完整报告与后来的真实成功报告相等 | 12项定向通过；cache重放0.743秒，原5138文件不变；无模型调用 |
| 行为报告读取有界entries引用 | 同run/hash绑定的完整报告供统计，模型实际回执不被改写；缺失或篡改仍拒绝 | 30项有效检查；v75日志重放50.656秒，4事务56项与34条已记录claim恢复，原文件不变；原CLI exit1保留 |
| 图片与文本投影组合 | 保留工具配对、当前状态、未送达保护和精确回读/恢复 | 1项组合检查通过；只证明程序性质，未证明模型能自主找到被压缩的证据 |

相关cache证据：`v76-opening-review-replay-summary.json`、`v76-opening-review-independent-review.json`、`v76-behaviour-replay-summary.json`、`v76-behaviour-independent-review.json`、`v76-combined-context-test-evidence.json`。

只读审计发现旧图片“仍在磁盘”不足以保证可用：真实v75检查点有60个图片身份/55种字节，组合压缩后46个身份的所有出现都退出模型请求。现已通过`read_context_image(action="list")`增加有界目录，复用原登记表和精确读取；明确旧候选来源，目录列出不算图片已送达。15项定向通过7.13秒，真实检查点8页列全60身份（最大页9046B），此前丢失的46身份全部可发现，4张旧检查图从目录精确读回，原读取596文件和完整历史hash不变。独审通过；`v76-image-directory-replay-summary.json`与`v76-image-directory-independent-review.json`留证。

Domain后段检查不能整体删除：v75的27个空间关系样本与墙线检查有具体图纸判断，后者还报告了跨层规整偏差。应补足当前候选的只读状态摘要，按已知问题和未决判断选择检查，澄清finish的终止语义；不要求遍历全部工具，不把状态摘要当独立保真证明。与此同时补齐regularization回执的现有读取参数、墙面检查精确缺字段与reference反馈，保留会改变几何含义的direction/offset显式要求。

工具反馈补全已独审：成功/失败草稿回执提供既有`inspect_plan_draft(report:/regularization)`及hash绑定；失败装配完整报告通过既有immutable `tool_reports`按需读，不只给侧车文件名；墙位置错误精确报告对象与缺字段，并指向`wall_dimensions`，offset仍必填。21项定向通过（首20项11.80秒、新增失败装配1项6.50秒，未重跑旧项），含真实stdio读取、原对象不变与篡改拒绝。证据`v76-feedback-discovery-implementation-audit.json`、`v76-feedback-independent-review.json`、`v76-failed-assembly-independent-review.json`。

编译器不再自动把自身方法与校准未独验的说明追加进作者assumptions/unresolved；事实保留在metadata和geometry.notes，经装配/source generation继续保存。作者文本不自动清理，旧运行不改。收尾指引改为围绕scope/current candidate/具体剩余问题，明确可用信息不足与尚未完成工作的区别，以及finish可能直接结束运行。3项编译/导出/两层路径有效通过（旧测试关于机器说明位于unresolved末尾的断言已按新职责更新），6项guidance接线通过；独审`v76-finishing-compiler-independent-review.json`。这不提高独立保真等级。

当前候选摘要已实现：显式`inspect_candidate(include_geometry=false)`按需返回整候选当前/过期开口回查、楼层覆盖、空间关系、立面计数、claim与高度状态以及作者未决项，复用既有投影；默认几何查看不自动触发。完整详情单一hash绑定、摘要仍在24KB内；不重跑像素/precision生成器、不产生质量通过门槛。有效声明的未决项可见，已撤回内容及已成功修复的失败历史不升为当前待办。未生成source的候选同样有可读详情。7项有效检查通过，含真实stdio交付回归和缺source详情跟读；独审通过，无剩余P1/P2；审阅记录`v76-current-checks-independent-review.json`。v75原candidate04纯投影2.881秒，5138原文件不变，保留34当前高度和6项窗宽提示，并未把提示升级成独立质量失败。证据`v76-current-checks-final-files.json`及`v76-current-checks-v75-readonly-replay.json`。

下一轮配置已准备并通过配置检查：[run_harness_v76.json](run_harness_v76.json)。

| 配置项 | 安排 |
|---|---|
| 模型/模式 | Astra/high，single_model，ChatGPT订阅；保持v75模型 |
| 输入 | sm25原六PNG，两层平面与四立面；不提供旧稿或GT |
| 上下文 | 保持v75图片1批和自动文本压力策略；本轮不启用搁置的128k/3批/Sol组合 |
| 资源 | 48模型请求、240工具、64候选；无总token与整案时间硬限；600秒仅外部指标 |
| 验收 | 完整自主交付、CLI干净退出、独立物理/宿主/连通质量分别检查；合格后同冻结配置再两次冷启动，有限样本如实报告 |

尚未启动v76真实模型，未证明可重复稳定；桌面未更新。

实现`3f224ab1`已登记runtime v16/domain v76，registry verify通过。两个正式冻结入口节点（图片目录工具版本/完成后恢复、全部MCP角色catalog）通过15.87秒，证据`v76-registered-preflight.xml`。实测前完成配置、474源码/registry/config及原输入冻结，运行期间不改程序、配置或候选。

## v76真实交付：状态摘要进入收尾路径，剩余负担有具体反例

冻结`6530f4080843923309301c324e98b428165aa3ed`，runtime v16/domain v76，Astra/high、图片1批、自动文本策略、无整案时限。2026-10-13 17:37:55.590915 UTC启动，运行目录`D:/Sim-BIM-Agent/runs/sm25-harness-astra-v76-20261014-1`。474程序/登记/配置、HEAD与六原图全部不变；无开发者建模干预。

| 项目 | 本轮结果 |
|---|---|
| 首次整楼 | 644.200秒，candidate07；必要局部修订后824.038秒生成candidate09 |
| 当前状态与完成 | 1179.885秒实际读取current_checks；1257.924秒主动finish candidate09 |
| 完整进程 | 1284.988秒（21分25秒），completed、CLI exit0；finish后0模型请求 |
| 交付绑定 | agent_selected、completion_valid、复用handoff，六文件SHA与原finish/receipt全等 |
| 模型/工具 | 28请求/28响应、130工具、0重试；finish回执不再送模型，符合终止设计 |
| 用量 | provider实报input3,503,913/output31,295/total3,535,208，cache14,336；订阅费用未知 |
| 耗时分解 | runtime1257.262秒：model1017.593、tool106.266、other133.403；外部另含27.725秒 |

四次开口回查共61 marks，其中57项未带note，全部首次通过；34外部高度claim全部confirmed。当前摘要实际呈现楼层、当前回查、高度、claim及剩余说明，模型随后只做推断/claim状态核对和两条规整子项读取，下一响应即finish；没有尾部整稿重写或再次泛化看图。这证明功能进入真实路径，单次前后时长不能证明因果提速或重复稳定。原behaviour报告崩溃未复现，summary/timeline/record.gz全部生成。

本轮仍有三类可避免负担，不能因已交付而忽略：

1. 六次立面对照因同一0/L锚点对仅行顺序相反被拒绝，后续交换行即通过；像素、米值、区间和对应对象不变。错误还指向了不相干的plan_partition参考。
2. 成功装配给了regularization文件/SHA，却漏了其直接read参数；模型据路径调用通用report reader被拒绝。v76已修草稿和失败装配，本次揭示成功分支遗漏，需要在共同保存入口统一。
3. 实际请求中局部图、六原图、局部图互相替换，13次精确回读前对应图均不在可见工作集。保持真实行为的3批反事实使13/13可见；比较点图片峰值6→16、PNG字节1,147,278→2,730,732，不是节时承诺。整轮真实wire共135次图像引用、59种SHA，最多9图；目录action=list未用，不能称已实证目录减少回读。

生命周期独审5982原run文件前后全等，证据在case cache的`independent-terminal-audit.json`（SHA e50455474ca99f30c176233117ee3bf2fb6ab9e0cfaf9c28dd8e636c2c8f5938）、`independent-terminal-freeze.json`、`independent-feedback-terminal-audit.json`与`image3-first13-counterfactual.json`。独立物理/谱系评价另存`sm25-harness-astra-v76-1-evaluation`，不可用以上执行成功替代质量结论。

浏览器已实际加载delivery与candidate09整楼并切换F2，HTTP200。捕获一条未归因MutationObserver错误，不能称console全净；临时页面及服务已关闭，原run未写入。记录为case cache的`browser-viewer-audit.json`。

独立物理评价：29空间、61开口及宿主、30门连接匹配，47邻接在原稿→grid→装配→交付保持；34外部高度均≤5cm。≤5／5–10／10–30／>30cm分档为房间15／8／6／0、开口沿墙35／26／0／0。raw strict的29房界及2整层内部线合计31 severe原样保留；按已登记墙面约定，原稿29房界残差均≤5cm（max4.294cm），初次grid每坐标最大F1 4.752/F2 4.842cm，另有三处跨层10cm联动对齐。07→09唯一物理变化为F2 W-S3宽1.7→1.8m，端点误差5.759→5.305cm，其余物理数组全等；这是标注/舍入边界的实质局部修复。六张回叠已实际目视，未发现额外实体错误；用途语义、未画出的竖向交通、内部高度及开关状态未独评。5982原文件及GT在独评前后不变；证据`independent-quality-attribution.json`与同目录独立评价。

## v77：统一现有契约与补足图像工作集

改动限现有接口：锚点保留每个pixel/metre绑定，只接受0/正L的两行等价排序，不自动重设基准或选择立面方向；反馈指向facade_correspondence。所有五处regularization保存调用共用读取规则：草稿仍用绑定的inspect_plan_draft，其余成功/失败装配和源约束拒绝都提供既有immutable tool_reports读取；移除易遗漏的分支布尔开关，不增加工具或reader。

32项定向检查通过20.26秒，包括真实MCP成功/失败装配回执跟读、SHA篡改拒绝及总回执压缩后的跟读；原六次失败观测原样离线重放0.024秒，与其后真实成功的kernel字段相等。原日志未改，无GT或模型调用。证据：cache根`v77-feedback-targeted.xml`、`v77-feedback-implementation-audit.json`、`v77-facade-anchor-replay.json`。独审无剩余P1/P2，7文件及原事件/重放SHA独立吻合，未重复测试；审计`v77-feedback-independent-review.json`（SHA cc384c6fb1713539b5708b4ea0359f8c04bdd7ab4922879c5b2b0f6c0035b7bd）。下一步登记并检查正式冻结入口。

[run_harness_v77.json](run_harness_v77.json)配置检查通过。相对v76只变批次/运行身份与图片1→3，Astra/high、自动文本、预算和原六图均保持；不启用先前搁置的Sol/128k组合。先冻结并完成首轮独立交付/质量验收，再按同版本配置重复冷启动，分别报告可重复性和时间。尚未启动v77，未更新桌面。

实现`779622c454aaffae23a98274e399b6bb08cf9353`已登记runtime v16/domain v77并verify。变更只涉及domain，本次登记后的真实冻结MCP目录/角色/材料节点1项通过6.89秒，XML为cache根`v77-registered-preflight.xml`；复用v76未改runtime/完成恢复的已有通过证据，不重复全量，也没有模型调用。
