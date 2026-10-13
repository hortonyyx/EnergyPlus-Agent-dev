# 强模型与10分钟交付路径

用户在当前会话明确取消模型国别/规模上限，允许 Astra、6.1 Sol 等 work model，并授权“按这个目标做”。最新澄清：**10分钟是优化目标，不是硬截止；先不强制限制整案时间。** 该授权覆盖本轮实施、必要验证与目标案例冷启动，不扩展到收费API回退、DeepSeek或其他输入路线。

## 方案与验收

- 复用已有 single_model 入口与同一源 BIM/kernel；一个模型处理六张原图，避免主要路径上的读图员提交、历史任务选择与重派协议。
- 统一草稿/报告有界读取；失败稿的报告与成功稿一样绑定原始证据，分页引用在后续修订后仍定位原稿。
- 补齐跨层隔墙/外轮廓物理边界的检查与规整覆盖，保留尺寸证据、拓扑保护、最终源 BIM 门槛和原始审计。
- 不扩大角色、不新增通用调度框架、不降低空间/开口/连接质量门槛。

验收要求：原六张sm25图纸、独立冷启动、无开发者中途提示或改稿；模型主动完成整楼源 BIM 与查看器，并通过独立空间/门窗宿主/连通质量评价。端到端墙钟及各阶段开销如实记录，以约10分钟为优化目标，超过600秒本身不判失败或强制停止。兜底产物、离线成功、单层候选和人工补步骤不算完整自主交付。初次成功后同一冻结版本再做两次冷启动，用3次结果报告有限样本的可重复性，不宣称统计可靠性。

## 当前实施状态

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
