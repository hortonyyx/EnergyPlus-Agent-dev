项目资料冻结摘录。源码片段不覆盖整个仓库；历史结果来自工作记录，未经你重新跑测。


## AI_agent/Agent.md L1-36

1: # 每次会话的项目初始上下文
2:
3: Codex、Claude 及其他开发助手共用本文件。用户当前指令优先，所有项目管理与交互记录放在 `AI_agent/`，不在仓库根另建管理文件。
4:
5: ## 开始会话
6:
7: 完整阅读本文、[产品目标](project/goal.md)、[当前任务](project/roadmap.md) 和 [工作方式](workflow/development.md)，再打开“当前任务”的“当前交接”指定的最新一份收工/交接记录（若有），然后按任务读取源码与相关设计。其余资料从 [总目录](README.md) 查找，不以通读历史日志作为开工条件。
8: 检查 `git status --short --branch`、`git worktree list` 和近期提交。会话加载方法见 [设置](workflow/session_setup.md)。
9:
10: ## 目标与开发取向
11:
12: - 核心是可查看、可修改、可用于后续分析的轻量 BIM。按信息充分程度统一称还原建模、部分推理建模、完全推理建模，不按输入模态划分；还原建模（sm21/sm24/sm25）与部分推理建模共用底座；每轮只推进一个方面，按用户最新安排切换，当前方向与具体入口见 [当前任务](project/roadmap.md)；部分推理保留 [研究计划](project/partial_inference_research_plan.md) 与验收待修交接。
13: - 当前关键目标是在有限模型智力下稳定生成相对精准的丐版 BIM。时间不是当前关键约束，耗时优化后置，prescan 等可随后按需考虑；不以抢早首稿主导排期。见[当前优先级](project/goal.md#当前优先级09-14-收工确认)。
14: - 当前只做目标单体，不考虑环境。用户生成前决定通用 BIM 对实际建筑空间的简化/合并程度，再选后端模拟。分块以实体隔墙为依据，最细保留实际空间，大开敞办公区不能因朝向或复杂度增加而被细分；低档可直接推断合并后的表达，无需先推全楼。物理/抽象边界仍区分，但抽象边界不授权凭空拆空间。输入信息量、源简化与后端热区合并独立；档数、控件和对应关系后续详细设计，办公楼仅为理解示例。
15: - 产品形态是模型驱动的总 Agent：根据目标、输入和工具反馈组织任务，按需调用代码工具、模型工具及专门能力。确定性几何操作可封装固定步骤，整案不写死为唯一流程；架构取舍与复杂度由开发助手总体把控，见 [系统设计](design/architecture.md)。
16: - 定性大于定量：先保房间、外形、楼层、门窗和空间关系正确、几何自洽可用。图纸/CAD/GT 的细小偏差允许有记录的容差规整；judge + GT 用于自动判断效果、减少人工逐项核对，不以逐点吻合或 GT 精修为主线。具体边界见 [验证与评价](design/evaluation.md)。
17: - 源分区保真优先于尺寸微差：漏墙、多墙、错误拆房/并房、假楼板和连通改变属于严重问题。计算切片/热区拆并只能是显式派生，不能变成源 BIM 的物理隔断；EP 跑通或历史 judge 放行不证明源模型正确。
18: - 我方主线是几何，物性由协作者负责；EnergyPlus 是首个下游。保留源房间、隔断、门窗和空间关系，仿真热区从源模型派生。
19: - 信息不足可用明确标注的推断、默认值和简化。不能静默丢房间/窗或掩盖失败，不能把推断当实测。
20: - 先取得真实 case 的可查看输出，再改善下游连通和质量。现有代码与工具按用途复用或替换；毫米级复刻、全实体墙、完整治理和旧债清零均非普遍前置。
21: - 生产模型目标档从首批实验参与，Sonnet 级为运行上限；开发派工前读取 [模型与费用](workflow/models.md)，按最新子代理分配偏好选择，不直接沿用主助手型号。
22:
23: ## 权限与执行
24:
25: - 可直接设计、修改、验证和提交，包括核心代码。保持一条 main；需要并行时划分任务/文件，使用短期树并及时集成公共接口。
26: - **Claude、GLM 现有订阅调用与派工已获授权，无需逐次确认。DeepSeek 的任何调用必须先获用户对本次任务/批次的明确同意**，主助手、子代理、管线、探测、重试与自动回退均适用。普通任务授权、旧记录或已有凭据不代替该许可；订阅授权不自动扩展到付费 API。
27: - 本项目 Git 备份、tag、分支/worktree 整理、commit 和正常 push 已全权授权。保留可回退的小提交，不强推共享历史，不丢弃未知改动。
28: - 验证按影响选择，复用同代码同范围的有效结果；不强制跨模型复审、每步全量或逐锁清债。代码里仍生效的检查需查明后再改，不能靠改文档宣称已取消。
29: - 几何计算、变换、切配和装配优先用确定性代码。失败先复用已有产物定位阶段，再做最短验证；新实验独立 run，不覆盖原始输入和旧结果。
30: - GT 留在评测侧。人工辅助、旧观测重放与冷启动生成分别报告，单测通过不等于整案完成。普通测试离线，凭据和私有配置不入 Git。
31: - 正常技术选择自行推进；遇到无法安全保留的冲突、无法判定的产品矛盾或新的外部权限障碍，说明具体问题后确认。
32:
33: ## 项目记忆与收工
34:
35: 所有助手的项目记忆同次同步到仓库对应文档：目标归 `project/`，设计/实现结论归 `design/`，操作约定归 `workflow/`，执行证据归 `logs/`。本地 memory 只留索引，不能独存项目事实或用户要求。收工和切模型前检查遗漏，敏感内容除外。
36: 用中文先说明结果、影响和建议，尽量用白话讲明白，不堆砌技术术语、变量名或内部任务代号；必要术语要解释它对用户意味着什么。每完成一个大节点，主动汇报这一程做成了什么、带来什么变化、还有什么未完成。用户说“收工”即按 [工作方式](workflow/development.md) 更新文档与交接、核对验证/diff、commit/push、收回完成的临时树，并总结本轮会话的全部工作；不重复全量，也不再问是否做 Git。

## AI_agent/workflow/models.md L1-48

1: # 开发与产品运行的模型使用约定
2:
3: 2026-09-09 更新：子代理常规优先 5.6 系列，Astra 按难度使用；保留 DeepSeek 事先明确同意，以及 Claude、GLM 订阅调用和派工授权。不引入必派工或强制跨家族复审链。
4: 原记录及当时的官方资料链接见 [模型路由历史资料](../archive/2026-09-08_codex_memory/energyplus-agent-dev-model-routing-2026-09-07.md)。
5:
6: ## 产品运行
7:
8: **09-14 本次Voimatalo探索例外：** 用户明确同意先把开发助手已有方法迁移给工作模型，允许本轮探索放宽，Opus也可尝试。主助手选择先用现有Claude订阅Opus验证方法迁移；须显式记录为探索性运行，后续Sonnet级目标档能力另验。此许可不扩展为付费API或DeepSeek许可，也不自动修改常规产品上限。
9:
10: 目标档从首批实验参与：可本地部署级 / Flash 级，经 API 调用，Sonnet 级为上限。
11: 各运行 agent 可配置模型，按实际质量、成本和时间比较；开发时借助更强模型不提高产品运行上限。
12: 09-14 收工确认：当前以**有限模型智力下的相对精度与稳定生成**为关键目标，时间优化后置，详见[当前优先级](../project/goal.md#当前优先级09-14-收工确认)。既有模型上限、订阅/付费权限与实际用量记录保留；下一轮的调用预算应支持质量验证，不把此前300/600秒实验时限视为产品要求。prescan 等只作为后续可能的提速方法，本次收工不启动新调用或修改运行时限代码。
13: 09-13 最后收工澄清：**Sonnet调度＋低档局部执行是可接受组合，不是开发每轮必须一步到位的硬流程，也不是锁定的最终架构。** 开发可先验证单项能力，再调整分工；有依据时可让Sonnet直接承担一段有界工作以定位问题，如实记录该干预、时间和用量。若工具/工作方式能进一步降低对模型智力的依赖，应继续优化；不要求每次必须调用Haiku或维持固定角色数。工作模型Sonnet级上限仍有效，开发助手型号与产品调用继续区分。
14: 09-13 用户再次明确：**Sonnet级是工作模型上限，即使用作工作模型，也应主要承担调度、思考和冲突裁定，控制消耗与时间。** 局部读图优先由适合的低档模型执行，量测/算术/几何改动交确定性代码；允许Sonnet为关键歧义直接核图，但不能长期代做全部细节。以实际质量、总用量、父子耗时和返工记录判断分工是否有效，不把调用了Haiku就等同降本。用户仍质疑历史Haiku/5.4-mini好reading与当前退步之间的差距；需继续检验工作方式，不能以旧任务边界不同为由结束解释，也不据此宣称旧端到端已成功。
15: 09-10 用户看过新 reading 后再次指出：直接让 Haiku 做整案效果差，历史已验证；下轮必须先核对历史好跑测及 reading/correction 架构，不再以同型整案重抽作为起点。Haiku 在工具测量和受约束工作方式下也有历史好结果，不据此一刀切禁止目标档模型；角色拆分及降本须按实际证据设计。见 [架构复盘](../design/reading_correction.md)。
16: 完整目标见 [产品范围](../project/goal.md)。
17:
18: ## 开发分配
19:
20: - 09-23 用户反馈已试用 Opus 5.5，认为可以承担相当的方案审阅、推理与完整长程任务；开发分工应纳入这一选择，不把 Claude 限于轻量局部工作。用户同时告知 GPT-6 家族发布。这里记录用户反馈，本轮未核验官方发布、订阅可用型号或实际调用标识；具体派工时核对通道与回执，产品运行上限及费用权限不因此改变。
21: - 用户指出子代理全部用 Astra 消耗过快，常规子任务优先使用 5.6 系列，具体选择由主助手按任务判断；这替代此前“减少 Sol/Terra/Luna 常规调用”的旧偏好。主助手型号不因此变更。
22: - 09-09 后续用户再次要求成块工作及时派工，避免全部由主助手完成造成过快消耗。对可独立实施的部分按文件/接口拆分，主助手集中于取舍、集成与实跑；不为简单小改额外造派工流程。
23: - 成块实现、分析和复核可选 5.6 Sol/Terra，轻量整理可按需选 5.6 Luna；Astra 留给确有难度的推理、复杂跨模块问题或较轻模型未能解决的任务，不要求先试遍一套模型阶梯。使用 Astra 子代理时在派工说明或工作记录中简短写明原因。
24: - 派工时明确选择子代理型号和适当的推理档位，避免因省略设置而全部继承主助手 Astra；只传任务所需上下文。若当前工具的完整会话继承方式不能同时指定型号，改用必要上下文加明确模型的派工方式。
25: - Claude、GLM 的现有订阅通道已获用户持续授权，可按任务需要自行调用和派工，无需逐次确认。Opus 可承担难推理/分析，Sonnet、GLM 可承担成块实现或复核，Haiku 可承担适合的提取和重复任务。
26: - DeepSeek 不列为默认开发或派工选项；先取得下述明确许可才可使用。Flash 等其他模型仍按各自通道与既有授权处理。
27: - 上述为分配偏好，不是每次都要开多个助手。当前任务和系统允许的执行方式优先，不为小改造出审阅流程。
28: - 一次任务提供必要上下文、产物和完成标准；按实际交付、返工、耗时和总成本调整，不凭公开榜单认定建筑图纸能力。
29:
30: ## 费用与通道
31:
32: - **DeepSeek 调用必须事先取得用户明确同意。** 用户指出此前 Claude 开发中大量使用了直接付费的 DeepSeek，因此本约束覆盖所有助手及子代理的开发调用、派工、管线实验、连通探测、重试与自动回退，小任务也不例外。
33: - 请求许可时说明拟执行的任务/批次、用途和预计调用量或费用（无法可靠估算则直说）。已同意的范围内可继续执行，扩大范围或另起任务需重新取得许可；一般开发、跑 case 或派工授权不代替 DeepSeek 专项许可。
34: - 主助手给子代理的任务须传递此限制，不得通过委派间接使用未获同意的 DeepSeek。配置里有 DeepSeek、凭据可用或历史方案推荐它，都不构成许可；运行前核对实际模型配置与回退路径。
35: - Claude、GLM 使用用户现有订阅通道，可自行分配任务和并发，不逐次申请调用/派工许可；订阅授权不自动扩展到按量计费 API。按实际额度合理安排，不为小任务制造审批流程。
36: - DeepSeek 开发调用与管线共用计费余额；凭据只注入需要的子进程，不全局覆盖模型端点，不输出密钥。
37: - 大任务按需检查资源与其他任务占用；存在尚未获授权的费用或确需用户决定的资源取舍时，再说明具体范围和替代方案。DeepSeek 始终按上述专项许可执行。
38: - 考虑峰谷与订阅额度，但不为等折扣拖住关键进度。价格、活动、窗口和可用模型在真正分配大任务时再核对。
39: - 历史 CLI 成本估算不等于真实账单；一次文本请求成功不等于视觉/工具能力、长期稳定性或剩余额度够用。
40: - 09-07 的模型通道探测和计费资料已归档，仅作历史信息；这些记录不代表当前额度、价格或授权。
41:
42: 既有脚本：[GLM](../../scripts/glm_code.sh)、[DeepSeek](../../scripts/deepseek_code.sh)。具体运行参数看实际脚本及有效接口。
43:
44: 当前 flow 已修复配置作用域：`--llm-config` 从主干启动时生效，退出恢复原环境；也可显式用 `EP_AGENT_LLM_CONFIG`。`--reading-model` 单独选择隔离读图 Haiku/Sonnet，校正可设 `provider: claude_subscription` 复用本机已登录订阅（无工具/MCP文本JSON调用）。该新路径拒绝 API key/base URL，无 DeepSeek 或其他模型回退。源码和使用方法见 [case 指南](run_case.md)；实际模型与用量以保存的 CLI 记录为准，估算费用不等于账单。
45:
46: 09-10 用户指定的 **Claude** 三项梳理已完成：通过已授权订阅并行分析历史实跑、架构演变和独立方案比较，主助手核对原件/源码并修正误判。请求 Sonnet，实际主模型和 CLI 辅助模型用量见 [本轮会话记录](../logs/experiments/2026-09-10_reading_architecture_review/review_sessions.json)，估算不是账单。未开展产品模型实验。用户随后确认按证据提高精度、模型负责泛化和合理推断；下一项围绕可查看 BIM 补实际缺口，Sonnet 级承担工序/歧义判断、目标档参与可检查子任务，不预设单/双线或要求先补齐证据接口。当前范围见 [任务](../project/roadmap.md)。
47:
48: 09-12 的 sm24 实验已实际完成一次 Haiku 局部立面读图委派，110.66秒，图像/隔离核验通过，但窗数、尺寸段和接地判断有误，父问题还预填了错误高度。Sonnet未直接采用额外窗，却未核清冲突；随后订阅429中断。该例不证明降本或可独立采信，按原图证据核验子任务回答仍是下一次工作重点；详细实际模型/用量/限制见[本轮记录](../logs/worklog/2026-09-12_reconstruction_sm24_delegation.md)。

## AI_agent/logs/worklog/2026-09-22_reconstruction_agent_reframing.md L1-31

1: # 09-22 还原/部分推理统一 Agent 重定位
2:
3: 用户进一步明确了项目主线：旧 pipeline 在 07-07 一类案例上用 Haiku、GPT-5.4-mini 配合 CV 工具完成了高质量 reading，虽然没有完成旧 pipeline 端到端或当前要求的丐版 BIM；这应作为低级模型借助工具完成图像到结构化数据转译的强参考。另一条路线是开发模型先完整探路，再将工具、步骤、中间产物和检查方式交给工作模型。两条路线都服务于 Agent 开发，不要求恢复旧 pipeline 原样运行。
4:
5: ## 当前设计判断
6:
7: 本项目主线从“测试 Sonnet/GLM 能否直接从图纸生成 BIM”切换为“尽快搭建模型驱动的总 Agent”。整案直出保留为诊断基线，不能继续作为主要施工方式；它已经证明直接图像到完整 BIM 的空间拓扑稳定性不足，但不能否定历史 reading 方法或开发探路路线。
8:
9: 旧 `reading / correction` 的职责拆分继续保留为可调用能力和中间产物类型，而不是固定的唯一流水线：Agent 可以按资料和歧义选择量测、像素区域、尺寸链、候选墙段、跨视图对应、校正、建模或回叠检查；但在提交源 BIM 前必须形成可审查的墙/开口/空间关系证据。这样保留拆分带来的可控性，同时不恢复后来过度僵化的阶段顺序和细节锁定。
10:
11: ## Agent 第一版应具备的核心状态
12:
13: - 任务目标、建筑输入、用户选择的简化/合并意图和当前预算；
14: - 原图/网格/CAD 等输入清单及可调用能力；
15: - 带来源、坐标、证据类型、置信度和未决项的观察账本；
16: - 墙段、开口、空间、连通和跨视图对应的假设图；
17: - 候选 BIM 版本、几何操作和受影响对象；
18: - 源几何检查、原图回叠和查看反馈；
19: - 模型路由记录：Sonnet 级规划/冲突裁定，低级模型执行可拆分观察，确定性代码负责量测、坐标计算、装配和检查。
20:
21: 工具调用不再直接把自然语言判断写成最终 BIM，而是返回可追溯的观察或修订 patch；Agent 再决定是否合并、补看、询问或生成候选。旧 reading 工具、CV 工具和现有 `build_bim`/`revise_bim` 都作为能力接入，不预先规定所有任务都必须经过同一顺序。
22:
23: ## 下一阶段顺序
24:
25: 1. 先为现有 `run_bim_agent` 加入最小 Agent 状态、观察账本和动作/结果契约，保留现有工具和候选产物。
26: 2. 把历史 reading 的 CV/量测能力和开发模型探路结果整理为可调用能力，先在 sm21/sm24 做结构化观察基线，不把旧 GT 或答案送入模型。
27: 3. 增加“拓扑证据达到最低要求后才能 build/revise”的软闸门；顺序仍由 Agent 自主选择，不能只凭一份直接几何猜测出 BIM。
28: 4. 用 Sonnet 级模型作规划和冲突裁定，用可配置的低级模型处理像素/尺寸/重复检查；记录每次路由的质量、总耗时和费用。
29: 5. 在还原建模上先验证跨 sm21/sm24/sm25 的闭环，再把部分推理接入同一 Agent，只额外增加假设、未知状态和缺失信息管理，不另建第二套总架构。
30:
31: 这是一项架构推进记录，不宣称当前 Agent 已实现；下一轮不再以新的整案直出实验作为主入口。

## AI_agent/logs/worklog/2026-09-23_bim_output_scope_and_next.md L1-23

1: # 09-23 BIM 输出边界澄清与下一步
2:
3: ## 用户明确的需求
4:
5: - 几何沿用逻辑闭合空间体；空间可非矩形，真实敞开与未知围护继续显式表达。
6: - 停点编辑沿用这一形态，可选对应墙、板、门窗等构件调整。
7: - 厚度是构件属性，对后续仿真重要；其对几何的细小影响不重要，不为此新增实体墙、净空重建或精修工程。
8: - 用户反馈 Opus 5.5 可承担方案审阅、推理和完整长程开发任务，已记入模型约定；本轮没有核验新型号或调用模型。
9:
10: 后端信息观察的助手建议为：建模必需信息主动查明，已看到的明确附加信息保留原文/数值、对象或类型关联和原始位置，后端按专业缺项定向补查；后端模拟假设与共享建筑事实分别保存。此为工作方案建议，不冒称用户逐项确认了字段或专业数据契约。
11:
12: ## 接下来的实施计划
13:
14: 1. **最小状态与记录贯通。** 在现有 run_bim_agent 上保存观察、依据、待核项和采纳/搁置/撤回决定，关联实际候选版本及工具结果。墙/板厚度作为可选构件属性随源输出保存，明确对象/共享构件对应、数值单位、来源和未知状态；属性更新不隐式调整空间几何。完成依据是记录可重读、不同候选依据不串用、属性进入实际源产物且几何保持不变，不仅生成一份账本 JSON。
15: 2. **把有效识读能力接入自主选择。** 复用已有 CV、尺寸链、墙网编译、局部修订和原图回叠；由总 Agent 选择观察问题、处理冲突和决定采用，模型提交可引用的观察，代码负责量测与几何计算。先接真实任务所需路径，保留 reading/correction 的职责区分，不重建固定阶段流程。Sonnet 级负责工作编排，合适的低档模型承担有界观察；开发强模型用于方案与实现工作，和产品效果分开评价。
16: 3. **sm24 验证最小真实闭环。** 优先房间分隔、走廊连续性与门窗宿主，给原图和建筑声明，由 Agent 自选局部检查、使用观察形成/修订可查看 BIM，再查看原图回叠。开发不预填具体正确墙位或空间答案，GT 只在事后评测。先验证真实观察能驱动正确几何动作、可靠对象被保留，失败则修对应接口/方法；不以记录数量、几何自洽或房间计数代替保真。
17: 4. **方法成立后换例。** sm21 检查换例迁移，再用 sm25 检查多层与门连接；不先无限精修 sm24。局部成功、完整冷启动、开发辅助和自主执行分别报告，已有采用候选保持原位。
18:
19: 第一交付节点是“有依据的观察 → 显式采纳 → 确定性建模/修订 → 原图反馈”的真实产物闭环，同时证明厚度属性可保存而不会改变盒子几何。完整三案例稳定性、通用停点编辑界面、EP 物性适配与其他后端仍未完成，不在本节点同时施工。
20:
21: ## 本轮实际状态
22:
23: 本轮完成需求讨论和文档同步，无新生产代码、模型实验或采用候选。讨论回复前写的观察账本已保存为[未验证草稿](drafts/2026-09-23_observation_ledger/README.md)，运行源码恢复；该草稿尚缺指引、验证和源属性接线，不直接认定为下一阶段实现。后续先按上述需求重新审视，再开始实施。

## AI_agent/logs/worklog/2026-09-21_reconstruction_measured_binding.md L1-44

1: # 09-21 还原建模：量测引用实测、局部复查与历史输入更正
2:
3: 继续用户授权的两路线研发。本程将保存的像素量测直接接入开口声明，完成Sonnet局部观察和自动选题的Haiku复查；历史代理进一步核清示例与目标墙网的重合。**坐标采用、标定和三处水平对应改善，但墙窗判读仍错，没有新的可采用BIM。**
4:
5: [Sonnet实测与可查看对照](../experiments/2026-09-21_sm24_measured_binding_run08/README.md) · [Haiku复查](../experiments/2026-09-21_sm24_residual_review_run09/README.md) · [历史更正](../experiments/2026-09-21_reading_reproduction_audit/historical_success.md)
6:
7: ## 实现与实际收益
8:
9: 生产提交`36cc1044`新增量测引用解析模块，并接通只读/完整工具和通用指引。模型可以在坐标槽中选保存的profile/candidate及peak/start/end，工具读取原文件、核原图/轴/散列并保存引用和解析值；纯数字仍允许标作其他依据或视觉估计。模型自行选颜色、阈值、候选、开口分组与标定。工具没有自动认窗或修BIM，没有内置案例坐标。
10:
11: 开发从run07真实扫描选20个引用重放通过，反向最大残差0.03601m；这是开发分组的接口验证，未送给新工作模型。独立run08只收原平面/East图及通用方法，Sonnet medium在421.26秒正常结束。20个像素槽中17个引用量测、3个明确视觉估计；两图尺度基准正确，两短窗及外门水平对应正确，端点残差约1—5cm。
12:
13: 但它把平面y355—382实墙当740mm窗，漏掉y382—556大窗；与立面大窗相配时最大误差4.79978m。模型把冲突解释为原图有矛盾，没有在成功比较后回看或重交。门高又错用大窗尺寸链。完整观察不采纳；相较run07同时有引用、比较v2及提示变化，不是单因素或稳定性结论。
14:
15: ## 复查没有解决语义错误
16:
17: 实验脚本从run08比较自动选出较低误差方向下残差最大的一对，投回平面仅用于裁图。Haiku拿原两图和明确未验证的旧声明，360.17秒正常完成，22次查看无工具错误，却继续将740mm实墙认作开口，还将外门内分格说成四开口并建议错误配对。没有量测/新比较，未修正大窗识读；其建议未回灌或修改任何BIM。
18:
19: 开发事后重看原图及实际返回裁图；两run共38次原图返回逐像素重放通过。没有发现运输损坏，也不能因一次Haiku失败推断它普遍不能复查。本次缺口是完整物理构件识别及尺寸链归属，仅增加自由文字复查没有解决。
20:
21: ## 历史核查的新证据与纠正
22:
23: 1595981/723b0f9旧kickoff要求读smalloffice_20的一层格式例。该例有10条完整墙及16条粗尺寸；10条墙与sm21两次成功输出完全相同，无窗或立面。主助手逐段和字节散列复核，见[example_overlap.json](../experiments/2026-09-21_reading_reproduction_audit/example_overlap.json)。此前将其当作无关格式例不准确，历史报告和设计已明确更正。
24:
25: 这不否定旧reading质量，也不能证明模型照抄；它说明一层墙的无答案独立性尚未证明，不能直接把旧条件当原图独立基线。窗和详细尺寸有不同的原始量测资料。sm24布局不同，此例不是其答案，不能解释其复现失败。09-16实际没有完成成功时的完整工序仍是可证差异，原因未受控隔离。
26:
27: 旧方法下一次独立sm21一层pilot方案已保存：保留旧规则/CV，排除完整同布局答案例和旧输出，先原图复核、冻结后评价；历史辅助条件单列，不为相同常见数值改写全部指引。见[短方案](../experiments/2026-09-21_reading_reproduction_audit/next_pilot_plan.md)。本程没有启动历史模型重跑或创建旧树。
28:
29: ## 下一项如何选择
30:
31: 1. 先在现有失败区域用已有同色连通范围工具核完整框：overview列块，seed定位，region取原图范围；保留断框/粘连，不由颜色或bbox自动判窗。开发走通后只交通用方法给工作模型，正确坐标和候选名单不进入独立实验。该方法与旧CV的连通块思路相通，暂不新增API，见[源码核对](../experiments/2026-09-21_sm24_measured_binding_setup/component_method_note.md)。
32: 2. 若完整范围证据不能促成正确分组，转入已准备的旧工具/工序一层独立pilot，比较实际产物；不再无新证据重跑相同自由复查，不固定押注单一路线。可以按准备成本和证据提前安排该对照，用户授权无需重问。
33: 3. 局部清单及高度链能正确修订后，再回到sm24整案；随后sm21换例和sm25多层/漏门。局部数值通过不能提前算三个case完成。
34:
35: ## 验证、用量和保留状态
36:
37: - 相关测试最终61 passed，32.10秒：profile_observation_binding、facade_span_comparison及bim_agent_tools；包含真实只读/完整stdio引用、混合数字和跨图/非法引用拒绝。生产代码自提交后未改，无需重复全量。
38: - run08：16原图返回、13成功扫描的图像/候选、17引用及比较返回/存盘/重算一致；36请求中4次接口错误有记录。两原图和七实现散列、离线页面通过。run09：22原图返回、六实现散列、父比较散列/自动选题重放和离线页面通过。两份原始流均无损gzip归档；机制通过与语义失败分别报告。
39: - run08主模型输出33328 token，CLI辅助Haiku16；估算$1.3730828。run09回执usage输出24752，modelUsage为24773，估算$0.293692；原始口径保留。费用是CLI估算而非订阅账单，全部现有Claude订阅，无付费API回退、DeepSeek或GT输入。
40: - 开发代理按最新偏好使用5.6 Sol，分工为纯引用模块/测试、历史审计与连通范围源码核对；主助手集成、实跑、复核和决策。
41:
42: sm24仍采用09-20 opening_heights run04/candidate_02（8空间/11窗/10门，开发限定恢复）；sm21仍为09-12/run22局部恢复；sm25保留旧29房/31窗/29门及两组漏门问题。本程没有新整案或另外两例改善。原6—10有效工作日仅为目标预算，不能作为可靠交付承诺；独立识图未通过，2—3周或更久的风险仍在。
43:
44: 本节点所有模型调用已结束，无后台生成、无临时工作树。生产代码单独提交，证据/设计/roadmap/本交接随后一并提交并正常push；旧原图/BIM/实验不覆盖。

## AI_agent/logs/worklog/2026-09-22_reconstruction_glm_progress.md L1-21

1: # 09-22 还原建模 GLM 推进记录
2:
3: 用户要求继续还原建模，并在 Claude 额度中断后明确改用 GLM。本程不改生产代码、不切部分推理或 EP；所有图像模型调用通过临时 CLI shim 路由到项目已验证可读图的 `glm-5.3-flash`，原始回执与工具流保存在对应实验目录。
4:
5: ## 结果
6:
7: 1. **East 竖向链观察完成。** Claude 首次请求返回 429 月度额度错误，未产生观察。GLM 只读 East 原图，36 轮、384.56 秒，实际模型由回执核实为 `glm-5.3-flash`。三条链均按原图放大、pixel profile 和 `map_dimension_chain` 核对并闭合：门组 1900/2400/200，对应 z=0.2–2.6m；大窗 1100/2400/1000，对应 z=1.0–3.4m；中/右短窗 1700/1800/1000，对应 z=1.0–2.8m。没有将结果回写 BIM。
8: 2. **独立整案生成完成。** GLM 输入五张 sm24 原图和 `testdata_prompt.json`，未给旧候选或 GT；1129.3 秒后保存并选择 `run14/candidate_01`，9 空间/11窗/10门/10连接，源自洽检查通过、查看器可看。生成后才运行独立 GT 诊断，结果为 severe：候选把参照一个空间拆为 `corridor`+`room_R3`，其余边界也有差异。窗数仅作数量信号，属性尚未由此诊断评价。
9: 3. **右侧不确定项恢复完成。** 从 run14 候选恢复，仍只给五张原图和 seed proposal。GLM 通过 4×裁图和灰度 profile 确认 D_R1/D_R2 是两个独立门；确认 R3/R4 之间有完整实体隔墙；发现 R3 所在段与走廊之间 y≈588–696px 无墙，于是提交完整修订把该段并入 corridor。新 `run15/candidate_01` 为 8 空间/11窗/10门/10连接，源自洽通过且可查看。生成后独立 GT 诊断仍 severe，主要剩会议区、走廊及右侧空间边界差异；不替换 run04/candidate_02 采用基点。
10: 4. **西南边界恢复完成。** 从 run15/candidate_01 恢复，只给原始 `1f_view.png` 和 seed proposal，限定检查会议区、走廊南端折角及右下接头。GLM 使用 `glm-5.3-flash`，476.09 秒完成；根据原图局部和 pixel profile 认定 x≈455–462 在 y≈756 以下没有实体墙，西南入口凹槽属于 `room_R4`。候选把 `conference_W` 改为矩形、把凹槽并入 L 形 `room_R4`，并把 `D_south` 重新托管到 `room_R4`，保留 8空间/11窗/10门/21开口。生成后 GT 诊断仍为 severe，说明该局部原图判读有记录但整案边界仍未通过自动参照；候选不替换 run04/candidate_02。
11: 5. **sm21 独立换例与两轮复核完成。** GLM 只看 sm21 两层平面、四向立面和建筑声明，1412.21 秒生成两层合并候选 `run23/candidate_03`：14 空间、15 窗、14 门；生成后独立诊断为 14/15 窗匹配、窗高无 z 漂移，但隔墙仍 severe。随后从该候选复核走廊和隔墙，1045.04 秒将 F1 走廊边界按原图改到 y≈3.0/5.0，独立诊断剩 F2 两条南侧隔断约 5cm 差异；最后 387.1 秒窄复核 F2 尺寸链，模型认为证据不足而保持 seed。三轮均未把 GT 或评测输出传给模型；run24 的候选可查看，run25 仅保留 seed。
12:
13: ## 运行与验证
14:
15: - run13/14/15 的 `agent_receipt.json` 分别记录实际模型、耗时和 CLI 估算；估算合计不等同账单。
16: - 原图、输入清单、工具 JSONL、候选 proposal/source/viewer、GT 后评估均保留。run14、run15、run18、run23、run24 与 run25 的 GT 只在生成后读取，未进入模型输入。
17: - 源几何检查均为 pass，但 `drawing_fidelity` 和人工确认仍为 `not_evaluated`；独立分区诊断是 severe，不能以空间计数对齐、源自洽或可查看代替保真通过。
18:
19: ## 下一步
20:
21: sm24 的有限复核和 sm21 的独立换例均已完成。GLM 在 sm21 达到 14/15 窗匹配，且 F1 走廊边界复核改善了独立差异；F2 两条约 5cm 隔断在窄复核中没有足够图证改动。当前保留 sm24 `run04/candidate_02` 及 sm21 历史采用基点，不把新候选的窗匹配或源自洽当作整案通过。下一步先整理并提交本轮证据，再决定是否转 sm25 或停止还原实验。

## AI_agent/design/architecture.md L14-85

14:
15: 09-14 讨论调整研发顺序：先完整复现已取得好结果的方法组合，再拆解、精简、重组吸收到总Agent，避免结构先行、逐个补要素忽略协同作用。好reading源于Sonnet自主开发/使用CV工具，随后才固化供Haiku使用；明确工序可作为总Agent按需调用的专门能力，模型驱动不要求单会话同时承担所有任务。具体复现边界见[读图方法](reading_correction.md#成功方法的复现与吸收09-14-讨论确认)，本次未实现新结构或启动实验。
16:
17: 同次讨论补充开发助手探路路径：先用可复用工具、明确中间数据和确定性计算走通任务，整理成工作模型可执行的kit，再根据其具体失败补harness。开发助手的强视觉/空间直觉不充作已实现工具能力，开发成功与目标模型独立成功分别评价。该路径与历史方法复现互补，由实际效果决定如何组织工具与专门能力，详见[迁移方法](reading_correction.md#开发助手先探路再交工作模型09-14-讨论补充)；本次仅记录。
18:
19: 总 Agent 持续读取用户目标、原始输入、当前 BIM/观测、未解决问题及工具结果，决定下一项动作；动作可以是观察、量测、请求专门模型、补充假设、生成/局部修改、检查或交付。工具执行后把真实结果交回，模型重新判断，允许回看或改方法。产物和任务状态落盘，长任务可恢复；不能只靠聊天上下文保存建筑事实。
20:
21: | 层次 | 负责什么 |
22: |---|---|
23: | 总 Agent | 判断还缺什么、下一步做什么、是否值得继续细化，以及何时形成可交付结果；处理整体语义和冲突 |
24: | 可组合工具/专门模型 | 查看/裁图、量测、图意识别、几何生成与修改、检查与渲染；后续 CAD 和后端能力通过同类接口接入 |
25: | 确定性内核与运行支撑 | 可靠计算与装配、统一源模型、工具执行及错误返回、产物保存/恢复、调用预算和最终状态核对 |
26:
27: ### 旧 0–5 职责如何放进总 Agent
28:
29: 用户追问是否将 0–5 各做成 Agent、是否需要 Agent 嵌套。助手曾建议总 Agent 直接调用代码/模型工具、必要时一层子 Agent；用户随后要求不要预先定死，边试边推进。下表仅为旧职责的参考映射，当前不施工 EP 的 3–5。若实验需要子 Agent，其返回结果、候选及依据，共同建筑改动统一应用，避免多个角色各自维护一栋楼。
30:
31: | 旧职责 | 首版建议形态 | 对总 Agent 的作用 |
32: |---|---|---|
33: | 0 reading | 可交互的读图工具；需要自主多次看图/量测时用读图子 Agent | 返回观测、对象候选和不确定项；可针对局部重新调用，无需整图重读 |
34: | 1 correction | 总 Agent 的整体判断 + 量测/约束求解与几何操作工具 | 处理跨图一致性、冲突及假设；复杂局部可再交专门能力，不强制设置独立 correction Agent |
35: | 2 modelling | 确定性源几何生成、检查、渲染工具 | 将已选方案变成可查看的共同 BIM，模型可据反馈局部修订 |
36: | 3 split/pairing | 后端确定性派生工具 | 按具体模拟用途切配，共同源 BIM 不被改成计算片 |
37: | 4 MEP/物性 | 后端模块，按需要用模型工具或其专门 Agent | 材料分层、热工信息等沿用协作者分工，不前移为几何生成前置 |
38: | 5 intake/output | 后端校验、装配与导出工具 | 执行对应出口合同；源 BIM 查看与交付无需等待旧 EP 导出阶段 |
39:
40: 调用一次模型做识别/判断可以是普通模型工具；只有子任务需要持有局部上下文、自主选择多个工具并根据结果继续时，才值得做成子 Agent。总 Agent 的规划不是每次生成整条流程图，而是在当前目标和状态下决定下一项有效动作。确定性的数据依赖依然存在；需要仿真时可调用一个内部含稳定步骤的后端工具。
41:
42: 稳定的几何依赖和计算顺序留在工具内部，例如按给定房间边界生成墙面、挂窗并核对宿主。模型不必重新算每个顶点，也不必每次指挥同一组底层步骤；它需要能选择这项能力、理解适用范围和失败原因。工具应围绕有意义的任务提供清楚的输入、结果及受影响对象，避免照搬几百个底层函数。少量临时代码可用于输入分析和方法探索，几何写入仍经过共同内核与检查。
43:
44: 专门视觉模型或子 Agent 可作为工具被调用，返回所见、候选、假设和产物引用；总 Agent 判断是否采信及下一步。既有“标注 + 像素 ＞ 像素 ＞ 纯推理”原则继续适用。子任务可分摊给目标档模型，整体判断维持 Sonnet 级运行上限；任务权限、实际通道与费用沿用 [模型约定](../workflow/models.md)，产品设计不扩大调用授权。
45:
46: 例如纹理遮住墙线：总 Agent 可先看局部、尝试量测，量测不足时调用视觉判读或结合房间关系提出假设，再生成粗 BIM 并查看检查结果；之后只修影响空间关系的部分。工具未检出线不直接结束整案。该例说明可选择的行为，不是给每张图强制安排的新流程。
47:
48: ## 反馈、停止与交付
49:
50: Agent 化增加可选择的方法，但不能自动消除死循环和误判。设计重点是让模型看到具体问题并能采取有效动作：
51:
52: - 工具返回结果、局部失败及有关对象/图像位置。几何操作失败时保留上一份可用状态，总 Agent 可重看、补假设或调用其他方法；真正的内核缺陷不能通过反复生成掩盖。
53: - 生产侧原图、量测、几何检查和渲染反馈可以用于有针对性的修订。**评测侧 GT 及其派生裁判信息不回流给生成 Agent**；旧盲重抽策略保留其历史实验含义，不扩展为禁止产品利用自身执行反馈。
54: - 09-10 用户明确原图回叠应进入生产侧校正循环。模型选择图面、楼层、像素/米锚点及墙面基准，确定性工具负责把实际源 BIM 画回该图；登记后，新候选复用同一标定返回新图，模型据此决定是否修改或补查。只有显式重新标定才改变基准，不能随新墙位自动拟合以掩盖差异。各图独立，保留每版源和标定的绑定；投影失败保留候选并明确反馈。工具生成、返回图像与模型正确读懂图像分开记录，原图语义、标定正确性和停止决定仍需模型判断，不新增 GT 或固定外部 judge 作为生成依赖。
55: - 正常完成以真实保存的 BIM、当前检查和可查看产物为依据，不能只相信模型说“完成”。几何可用、信息完整程度和后端可接受性分别说明；输入不足允许带假设交付，已知严重问题不得包装为通过。
56: - 有界调用预算、连续无进展判断和恢复状态由运行代码支撑。预算耗尽保存已有成果及缺口，不能空转，也不能把预算停止当成成功。普通不确定性由模型处理；涉及用户目标冲突或所需信息无法合理假设时再询问。
57:
58: 这些运行约束规定动作与成果是否有效，不预先穷举整案的任务路线。源 BIM 仍是共同交付与查看停点，材料分层等热工信息和专用派生留给后端。
59:
60: ## 现有能力与首个增量
61:
62: ### 09-13 收工：架构骨架明确，执行方法仍在收敛
63:
64: 当前实验入口已经可执行“原图/保存方案 → 模型选择观察、量测与局部模型 → 方案及确定性源生成 → 实际源查看/原图回叠/开口检查 → 修订或带缺口交付”。这是能力与数据依赖的概括，不要求每次依次经过固定阶段。下层几何生成、保存/恢复、检查、查看已有实际证据；上层选取有效局部任务、解释墙段与尺寸、判断反馈、保护既有正确对象及预算内收尾仍不稳定。当前应称为**能运行并取得局部修复的Agent原型**，还不是三案例可重复通过的产品管线，也不是仅有概念设计。
65:
66: 开发助手近期仍在选择局部问题和安排恢复运行；不能把这部分人工组织算作产品Agent自身能力。Sonnet局部尺寸观察辅助sm24撤假墙是有效结果，但随分区修订又无新量测地缩窄一扇门，说明闭环还缺可靠的修改取舍。Haiku历史好reading及当前局部正确观察支持继续试低成本能力，不证明其能独立承担整案发现、裁定和自我纠错。成功子任务应按实测能力下放，模型分工不固定为必须双Agent接力。
67:
68: 下一步收敛可观察的工作状态：已确认信息、待核冲突、候选改动、当前源检查/未核范围，以及是否还有值得继续的修复；动作仍由模型选择。先在原图新运行中验证错误能被自行发现和修复、可靠对象能保留，再整合正式flow，避免把同图定点补救无限延长或先重写框架。三案例状态、主观可行性估计及开发轮次假设见[本次收工](../logs/worklog/2026-09-13_reconstruction_session_close.md)。
69:
70: 09-10 新增独立实验入口 [run_bim_agent.py](../../scripts/tool_scripts/run_bim_agent.py)：Sonnet 订阅模型直接选择查看/裁图、像素投影量测、坐标换算、Haiku 局部复核、生成与检查、候选平面查看。工具仅暴露本次显式原图与自产候选，未提供仓库/任意文件/命令访问；不向模型暴露 GT。几何方案通过 [直接方案导出](../../src/agent/execution/source_proposal.py) 接共同源内核，无需旧 correction run 或接受记录。每次候选单独保存，假设、未解决项及输入来源跟随源模型和查看器；几何通过仍不代表原图保真。
71:
72: 09-10 续推增加保存方案恢复及局部修订：`--resume-candidate` 只导入上一候选的 proposal，重新执行生产几何检查，不导入旧评价；`inspect_candidate` 读取方案，`revise_bim` 由确定性代码执行整体反射、门窗更新/开口改判及假设备注替换。新旧候选分开保存，修订理由、来源、前后值及父方案摘要留档，几何对象 ID 保留。更新后的来源同步到门窗对象，旧来源及删门前对象留在审计；完整修订历史也进入独立源 BIM 的 generation 字段，不能仅靠外部对话保留。这是方案恢复实验，不是完整编辑产品，也不承诺派生边界 ID 跨修订稳定。
73:
74: 新增开口回查工具 `check_openings`：生成后先给出按楼层/空间分组的实际开口清单，模型可提交原图各独立标记与对象的对应关系，代码报告未对应、重复及连接不一致。观察与结果独立保存并绑定源/图像摘要，候选修订后不自动沿用旧回查。它不读取 GT、不自动识别像素，也不把自然语言备注解释成门数；模型需把判断落成可核对的标记清单。局部或推断观察仍可保存，不以完整回查作为已有 BIM 可查看的前置。
75:
76: 后续增量增加 `overlay_candidate` 与 `finish_bim`。前者复用既有像素标定器，按模型给出的原图像素/米锚点，将已建源房间和门窗投影回原图，便于发现分开查看时漏掉的错位；分轴比例、警告、来源摘要和原分辨率叠图独立保存，不自动识别图像真值。后者让模型选择保存候选，由代码汇总实际几何检查和当前源回查，交付 `delivery.json/html`；未回查、局部观察、仍需跟进和旧源回查分别显示，不把模型最后文字当验收依据。模型未显式选定时运行结束仍保留最新保存候选，并标明回退选择。带问题候选可以交付查看，没有强制全层回查或新的审批链。
77:
78: 这是原型入口，尚未替换正式 `flow`，不代表跨案例能力已验证或已支持完整恢复/持久编辑。当前实验设置最多 6 个候选、2 次局部复核，订阅调用有时限；记录真实工具轨迹、模型和用量。这些是本次试验范围，不固定产品角色数量或所有输入必须经过的工序。实际结果见 [当前任务](../project/roadmap.md)。
79:
80: 仓库已有 [局部工具调用循环](../../src/agent/react.py)，旧 [下游图](../../src/agent/graph.py) 把这些循环装入固定阶段；[flow](../../scripts/tool_scripts/run_stage.py) 仍按阶段顺序运行，[旧失败路由](../../src/agent/execution/routing.py) 主要按阶段类型选择重抽、人工重读或停止。开发期的 [orchestrate.py](../../src/agent/execution/orchestrate.py) 明确依赖会话主助手驱动，不等于已交付产品总 Agent。新源分叉绕开 EP 阶段，但尚未成为跨观察、修订、生成和检查的总 Agent 循环。
81:
82: 首个独立入口原型已按上述范围接通，sm21 实跑说明模型能消费检查反馈，却仍会为消除几何错误改变立面语义。下一增量以保存的候选和原图处理坐标变换、门洞身份与候选生成节奏；不先更换框架、重写内核或包装全库。旧 flow 留作重放/对照，后续按验证结果整合到同一产品入口。
83:
84: 当前先用一个真实输入试到可查看 BIM，工具和任务拆分随发现调整；不以框架选型、嵌套层级、完整恢复系统或所有复杂输入覆盖为首份输出的前置。EP 相关工具不纳入这轮原型。
85:

## AI_agent/design/model.md L114-145

114: ### 09-23 厚度属性与观察分界讨论
115:
116: **本次最终需求澄清：用户明确墙厚对几何的影响不重要，作为构件信息对仿真重要。** 当前实现应优先保存厚度与来源，不推进厚度驱动的实体墙、净空间或全楼几何精修。下文及历史章节的墙面派生/基准换算属于可复用能力与后续选项，不构成新的开发前置；助手此前提出的完整厚度几何处理方案未被确认为近期必做功能。
117:
118: **用户进一步确认：既定 BIM 几何形态不变，仍由一组逻辑闭合的空间体组成。** “盒子”指空间体，可为非矩形；逻辑闭合不代表每个边界都有实体墙/板，实际敞开、挑空及未知围护继续显式表达。墙厚、板厚等作为对应构件的属性补充，不把源模型改成一套完整实体构件模型，也不因本次讨论重开几何形态选择。
119:
120: 此前确定的停点编辑同样基于此形态：用户选择空间及其对应墙、板、门窗等进行调整。构件选择和属性编辑不要求源几何变成实体墙；几何调整需保持相关空间边界、共享关系和宿主开口一致。此处确认的是产品设计，现有局部修订工具与尚未交付的通用持久编辑界面继续分别记录。
121:
122: 用户明确：厚度应作为墙、板等构件的属性保存；它会影响几何生成，但这类几何精度差异在当前丐版 BIM 目标下可以接受。不因此前置完整实体构件、墙角精修或净空间重建。
123:
124: 助手建议（待讨论收敛）：继续以明确的参考面表达空间关系，厚度保存数值、口径、来源和已知/推断/未知状态；按需要派生实体、净空或洞深。补充厚度信息不自动触发全楼精修；几何采用近似时说明参考面与面积/体积口径，避免两侧各算一遍厚度或楼层标高混用。明确修改实际构件尺寸时，仍需说明固定的参考面及更新范围。
125:
126: 用户追问源 BIM 阶段应为 EP 等后端观察记录到何种程度，原始输入将持续可查。助手建议用“建模必需信息主动查清、已经看到的明确附加信息随手保留、专业缺项在使用后端时定向补查”划界：
127:
128: - 源建模主动处理空间/构件身份、几何、相邻与敞开关系，以及定位建模所需的朝向、标高、厚度基准等；信息不足保留明确假设，不用缺物性阻塞几何交付。
129: - 已在当前观察范围看到的材料说明、构造编号、层次表、门窗型号、明确性能数值、用途或运行声明，保留原文、位置、单位、适用对象/类型和确认程度；不要求首次建模读遍全部专业表格。
130: - 输入清单标明专业表格/说明的位置及未读/部分读范围，后端可按缺项和对象定向调用同一观察能力。没有查过与查过但未找到分别记录。
131: - 后端负责专业信息的进一步提取、材料库匹配、参数推断、计算简化和本次运行设置。新发现的建筑事实可形成共享记录；后端默认值和本次模拟假设保留在后端配置，不直接覆盖源属性或几何。冲突保留并交总 Agent 裁定。
132:
133: 以上为输出边界讨论，尚未实现通用构件属性或跨后端补充接口。当前 EP 固定构造模板的范围见 [最小物性契约](ep_physics_contract.md)，不把建议当成现有能力。
134:
135: 用户补充：墙厚精细几何优先级较低，但墙厚参数影响后续仿真；随后明确材料分层等热工信息归后端模块。几何侧按可用信息保留总厚/墙面间距，缺少可靠厚度时可采用明确的表示假设，不阻塞丐版 BIM。以下具体接口仍是设计建议，不是新 schema 或实现验收。
136:
137: - **几何总厚/墙面间距**：保留测量位置、所指层次（结构/含饰面/未知）、来源和不确定性。可信总厚与参考线定位共同用于派生内外面、净尺寸和洞深；单有厚度不能判断尺寸是按轴还是按边，也不能默认所有轴线都居中。
138: - **表示用的参考线/面**：表示空间关系和装配范围，记录其与真实墙面的偏移约定。保留厚度参数和观测引用即可支持后续派生，不要求初始模型画成完整实体墙。
139: - **热工材料层**：层厚、材料导热率、密度、比热等归后端构造参数，不作为源几何生成前置。图上总厚不足以确定整墙传热/蓄热表现。EnergyPlus 将表面坐标与引用的材料构造分开；见 [官方手册内容](https://bigladdersoftware.com/epx/docs/24-2/input-output-reference/group-surface-construction-elements.html#specifying-the-building-envelope)。
140:
141: 二者分开管理但不能无视真实构造相容性：若均描述同一实际墙体，应核对几何总厚与构造层合计，允许明确记录结构层/饰面或等效热工简化造成的口径差。用户明确修改实际总厚时，需按固定参考线/面重新派生受影响几何；仅改变热工假设或等效参数时，不静默回写源墙位置。当前物性接口不提供几何修改，此处不宣称该编辑能力已实现。
142:
143: 成熟表示同样分别记录材料层及其相对参考线的偏移，并要求相应实体几何与材料层一致；参考 [IfcMaterialLayerSetUsage](https://standards.buildingsmart.org/IFC/DEV/IFC4_3/HTML/lexical/IfcMaterialLayerSetUsage.html)。本项目只借鉴这种信息区分，不以完整 IFC 或实体墙为前置。
144:
145: ### 墙厚与标注基准的实施方案（09-10 收工讨论，尚未实现）

## scripts/tool_scripts/run_bim_agent.py L211-315

211: def prepare_detail_observation(
212:         toolkit: "Toolkit", question: str, images: list[str], name: str, *,
213:         timeout_seconds: float | None = None, deadline_epoch: float | None = None):
214:     """Make one immutable, image-only MCP workspace for a local observation."""
215:     if not isinstance(question, str) or not question.strip():
216:         raise ValueError("local review question must be non-empty")
217:     if not images:
218:         raise ValueError("choose at least one original image for local review")
219:     if len(set(images)) != len(images):
220:         raise ValueError("choose each local review image only once")
221:     if timeout_seconds is not None and deadline_epoch is not None:
222:         raise ValueError("choose either timeout_seconds or deadline_epoch for local review")
223:     if timeout_seconds is not None:
224:         if timeout_seconds <= 0:
225:             raise ValueError("local review timeout_seconds must be positive")
226:         deadline_epoch = time.time() + timeout_seconds
227:     if deadline_epoch is not None and deadline_epoch <= time.time():
228:         raise ValueError("local review deadline_epoch must be in the future")
229:     sources = {image: toolkit.image_path(image) for image in images}
230:     child = toolkit.run / name
231:     child.mkdir(exist_ok=False)
232:     child_images = child / "images"
233:     child_images.mkdir()
234:     selected = {}
235:     for image, source in sources.items():
236:         target = child_images / image
237:         shutil.copy2(source, target)
238:         with PILImage.open(target) as picture:
239:             size = list(picture.size)
240:         selected[image] = {"size": size, "sha256": digest(target)}
241:         if selected[image]["sha256"] != toolkit.manifest["images"][image]["sha256"]:
242:             raise ValueError("selected original image changed while preparing local review")
243:     # Keep the caller's wording verbatim. File isolation cannot make a leading
244:     # question independent if the caller itself includes a candidate claim.
245:     (child / "question.txt").write_text(question, encoding="utf-8")
246:     manifest = {
247:         "images": selected,
248:         "input_mode": "isolated_detail_observation",
249:         "only_input": (
250:             "selected original image copies and local question; no parent scope, "
251:             "seed, candidates, history or evaluation"
252:         ),
253:         "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
254:     }
255:     if deadline_epoch is not None:
256:         # This is part of the immutable child input before its digest is recorded.
257:         # The readonly server reads it to expose remaining_seconds to its tools.
258:         manifest["deadline_epoch"] = deadline_epoch
259:     dump(child / "inputs.json", manifest)
260:     return child, digest(child / "inputs.json")
261:
262:
263: def review_detail_observation(
264:         toolkit: "Toolkit", question: str, images: list[str], *,
265:         timeout_seconds: float = DETAIL_MAX_TIMEOUT_SECONDS, invoke=subscription) -> dict:
266:     """Run one bounded, readonly local observation and retain parent receipts."""
267:     if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
268:             or not DETAIL_MIN_TIMEOUT_SECONDS <= timeout_seconds <= DETAIL_MAX_TIMEOUT_SECONDS):
269:         raise ValueError(f"timeout_seconds must be between {DETAIL_MIN_TIMEOUT_SECONDS} and {DETAIL_MAX_TIMEOUT_SECONDS}")
270:     # FastMCP may serve sync tools concurrently. Keep allocation, receipt creation
271:     # and the bounded invocation together so two calls cannot both claim detail_01.
272:     with DETAIL_OBSERVATION_LOCK:
273:         used = len(list(toolkit.run.glob("detail_*_request.json")))
274:         if used >= 2:
275:             return {"error": "local review budget exhausted", "completed": False}
276:         parent_deadline = toolkit.manifest.get("deadline_epoch")
277:         remaining = toolkit.remaining_seconds()
278:         if remaining is not None:
279:             child_deadline = min(time.time() + timeout_seconds,
280:                                  float(parent_deadline) - DETAIL_COMPLETION_RESERVE_SECONDS)
281:             timeout = child_deadline - time.time()
282:             if timeout < DETAIL_MIN_TIMEOUT_SECONDS:
283:                 return {"error": "insufficient remaining budget for local review",
284:                         "completed": False, "remaining_seconds": remaining}
285:             # Keep the parent completion reserve outside the child workspace too.
286:             # This exact absolute deadline avoids extending the child's budget while
287:             # it is being prepared or while the parent waits for it to return.
288:             # ``timeout`` is also capped by that deadline, not a rounded display value.
289:         else:
290:             timeout = timeout_seconds
291:             child_deadline = time.time() + timeout
292:         name = f"detail_{used + 1:02d}"
293:         child, input_sha256 = prepare_detail_observation(
294:             toolkit, question, images, name, deadline_epoch=child_deadline)
295:         source = {"run": name, "input_sha256": input_sha256,
296:                   "images": {image: toolkit.manifest["images"][image]["sha256"] for image in images}}
297:         # Image copying/manifest writing consume time too. Do not let the process
298:         # outlive the deadline the readonly tools were shown.
299:         timeout = min(timeout_seconds, child_deadline - time.time())
300:         result = invoke(child, f"Images: {images}\nQuestion: {question}", model="haiku", name=name,
301:                         readonly=True, timeout=timeout, log_run=toolkit.run,
302:                         receipt_context={"observation_source": source})
303:         result_event = result.get("result")
304:         completed = (bool(result_event) and not result_event.get("is_error", False)
305:                      and not result.get("timed_out", False) and result.get("returncode") == 0)
306:         return {"actual_model": result.get("actual_model"),
307:                 "timed_out": result.get("timed_out", False),
308:                 "returncode": result.get("returncode"),
309:                 "result": result_event.get("result", "No completed answer") if result_event else "No completed answer",
310:                 "is_error": result_event.get("is_error", False) if result_event else True,
311:                 "completed": completed,
312:                 "observation_source": source,
313:                 "remaining_seconds": toolkit.remaining_seconds()}
314:
315:

## scripts/tool_scripts/run_bim_agent.py L347-383

347:     def __init__(self, run: Path, readonly=False):
348:         self.run = run.resolve()
349:         self.manifest = json.loads((self.run / "inputs.json").read_text())
350:         self.readonly = readonly
351:
352:     def log(self, action, data):
353:         with (self.run / "tools.jsonl").open("a") as stream:
354:             stream.write(json.dumps({"time": time.time(), "readonly": self.readonly,
355:                                      "action": action, "data": data}, ensure_ascii=False) + "\n")
356:
357:     def candidate_path(self, candidate):
358:         allowed = {p.name for p in self.run.glob("candidate_*") if p.is_dir()}
359:         if (self.run / "seed").is_dir():
360:             allowed.add("seed")
361:         if candidate not in allowed:
362:             raise ValueError("unknown candidate")
363:         return self.run / candidate
364:
365:     def remaining_seconds(self):
366:         deadline = self.manifest.get("deadline_epoch")
367:         return max(0, round(deadline - time.time())) if deadline else None
368:
369:     def delivery(self, candidate, *, selection_origin, generation_status=None):
370:         """Build the handoff from saved source/check records, never model prose."""
371:         from src.agent.geometry.bim_delivery import summarize_delivery
372:         path = self.candidate_path(candidate)
373:         source = json.loads((path / "source_model.json").read_text())
374:         reviews = [json.loads(p.read_text()) for p in
375:                    sorted((self.run / "opening_reviews").glob("review_*.json"))]
376:         result = {"candidate": candidate, "selection_origin": selection_origin,
377:                   "viewer": f"{candidate}/viewer.html", "source_model": f"{candidate}/source_model.json",
378:                   "viewer_exists": (path / "viewer.html").is_file(),
379:                   "generation_status": generation_status or {"state":"in_progress"},
380:                   **summarize_delivery(source, reviews)}
381:         result["source_image_feedback"] = self._delivery_projection_status(candidate, source)
382:         dump(self.run / "delivery.json", result)
383:         # A separate handoff preserves the immutable candidate's original report.

## scripts/tool_scripts/run_bim_agent.py L617-667

617:     def build(self, proposal, *, action="build_bim", parent=None, operations=None,
618:               plan_input=None, calibration=None):
619:         from src.agent.execution.source_proposal import export_source_proposal
620:         if isinstance(proposal, dict) and 'mesh_frame' in proposal:
621:             from src.agent.geometry.mesh_bim_frame import validate_mesh_frame
622:             frame = validate_mesh_frame(proposal['mesh_frame'])
623:             if frame['mesh_sha256'] != self.manifest.get('mesh_input', {}).get('sha256'):
624:                 raise ValueError('candidate mesh_frame must refer to the admitted original mesh')
625:         index = len(list(self.run.glob("candidate_*"))) + 1
626:         if index > 6:
627:             return {"error": "candidate budget exhausted; report saved partial results"}
628:         candidate = f"candidate_{index:02d}"
629:         provenance = {"input_manifest_sha256": digest(self.run/"inputs.json"),
630:                       "mode": self.manifest.get("input_mode", "original_images_agent_experiment"),
631:                       "generator": "Claude subscription tool loop"}
632:         if parent is not None:
633:             provenance.update(parent_candidate=parent,
634:                               parent_proposal_sha256=digest(self.candidate_path(parent)/"proposal.json"))
635:         if plan_input is not None:
636:             provenance["plan_input"] = plan_input
637:         report = export_source_proposal(proposal, self.run/candidate, provenance=provenance)
638:         if operations is not None:
639:             dump(self.run/candidate/"operations.json", operations)
640:         result = {"candidate": candidate, "remaining_seconds": self.remaining_seconds(), **report}
641:         if plan_input is not None:
642:             result["plan_input"] = plan_input
643:             result["plan_compilation"] = json.loads(
644:                 (self.run / plan_input["compilation_file"]).read_text())
645:         source_path = self.run / candidate / "source_model.json"
646:         if source_path.exists():
647:             from src.agent.geometry.opening_review import opening_inventory
648:             result["opening_inventory"] = opening_inventory(json.loads(source_path.read_text()))
649:             result["opening_review"] = "not_reviewed; compare this inventory with distinct drawing marks"
650:             if calibration is not None:
651:                 self._save_calibration(candidate=candidate, image=plan_input["image"],
652:                                        metadata=report, **calibration)
653:             projections, errors = self.project_registered_calibrations(candidate, action)
654:             result["source_image_projections"] = projections
655:             result["projection_errors"] = errors
656:             result["source_plan_views"], result["source_plan_errors"] = [], []
657:             source = json.loads(source_path.read_text())
658:             for floor in source["floors"]:
659:                 try:
660:                     _, metadata = self.plan_view(candidate, floor["id"])
661:                     result["source_plan_views"].append(metadata)
662:                 except Exception as error:
663:                     result["source_plan_errors"].append({"candidate": candidate,
664:                         "floor_id": floor["id"], "error": str(error)})
665:         self.log(action, result)
666:         return result
667:

## scripts/tool_scripts/run_bim_agent.py L1657-1714

1657:         @server.tool()
1658:         def build_plan_bim(image: str, plan_json: str) -> CallToolResult:
1659:             """Build one floor from observed pixel wall paths, apertures and calibration.
1660:             Read get_bim_reference('plan_partition') for the JSON contract. Code
1661:             closes faces and finds opening hosts; it never fills wall-path gaps,
1662:             invents partitions or trims openings. Returns actual source plan and
1663:             original overlay images. Rectangular outer footprint, orthogonal
1664:             interior partitions only. A draft with known omissions needs explicit
1665:             unresolved notes. Each source export uses the shared candidate budget.
1666:             """
1667:             return candidate_result(toolkit.build_plan(image, plan_json))
1668:
1669:         @server.tool()
1670:         def build_parametric_bim(plan_json: str) -> CallToolResult:
1671:             """Expand model-declared floor templates and window rows, then build source BIM.
1672:             Read get_bim_reference('parametric') first. Never infers or trims geometry.
1673:             Relative aperture heights are offset by each explicit instance base.
1674:             """
1675:             from src.agent.geometry.parametric_proposal import expand_parametric_proposal
1676:             folder = toolkit.run / 'parametric_drafts'
1677:             folder.mkdir(exist_ok=True)
1678:             draft = folder / f'draft_{len(list(folder.glob("*.json")))+1:03d}.json'
1679:             draft.write_text(plan_json)
1680:             try:
1681:                 plan = json.loads(plan_json)
1682:                 proposal = expand_parametric_proposal(plan)
1683:             except (ValueError, TypeError, KeyError) as error:
1684:                 result = {'error': str(error), 'draft': str(draft.relative_to(toolkit.run)),
1685:                           'remaining_seconds': toolkit.remaining_seconds()}
1686:                 toolkit.log('build_parametric_bim', result)
1687:                 return candidate_result(result)
1688:             result = toolkit.build(proposal, action='build_parametric_bim')
1689:             if result.get('candidate'):
1690:                 dump(toolkit.run / result['candidate'] / 'parametric_plan.json', plan)
1691:             # Full inventories and every plan remain on disk/available on demand.
1692:             # Return representative template plans without repeating identical floors.
1693:             result.pop('opening_inventory', None)
1694:             representatives = {}
1695:             for instance in plan['instances']:
1696:                 representatives.setdefault(instance['template'], instance['id'])
1697:             result['source_plan_views'] = [v for v in result.get('source_plan_views', [])
1698:                                          if v['floor_id'] in representatives.values()]
1699:             return candidate_result(result)
1700:
1701:         @server.tool()
1702:         def inspect_parametric_plan(candidate: str) -> dict:
1703:             """Read the exact saved compact plan for revision; original evidence is separate."""
1704:             value = json.loads((toolkit.candidate_path(candidate) / 'parametric_plan.json').read_text())
1705:             toolkit.log('inspect_parametric_plan', {'candidate': candidate})
1706:             return value
1707:
1708:         @server.tool()
1709:         def build_bim(proposal_json: str) -> CallToolResult:
1710:             """Build/check/save a candidate; get_bim_reference("geometry") describes proposal JSON.
1711:             Returns errors or actual geometry checks. Six immutable candidates maximum.
1712:             """
1713:             return candidate_result(toolkit.build(json.loads(proposal_json)))
1714:

## scripts/tool_scripts/bim_agent_guidance.py L1-153

1: """Task-focused BIM guidance and on-demand parameter references.
2:
3: Examples are independent of case inputs. Reference reads never inspect run files.
4: """
5: from __future__ import annotations
6:
7: GUIDE = """Build a viewable lightweight BIM of the target building from the supplied
8: visual inputs and building declarations. You choose observations, tools, delegation and revisions.
9: Preserve actual physical spaces, partitions, openings and connectivity. Geometry
10: checks prove internal consistency, not drawing fidelity. No EP or materials.
11:
12: When inputs contains mesh_input, the ORIGINAL textured GLB is available through
13: inspect_mesh, view_mesh and measure_mesh_pixels. You choose cameras, detail targets,
14: view spans and whether to query geometry or inspect texture. No fixed screenshots
15: are required. Query bounds before choosing metric views; zoom by changing target
16: and spans, and measure visible surface pixels rather than guessing scale. Mesh
17: local coordinates are Z-up [GLB.x,-GLB.z,GLB.y] optionally rotated in xy by your
18: explicit yaw_degrees. Keep one declared frame for construction and evidence.
19: inspect_mesh_directions reports area-weighted near-vertical triangle directions,
20: with selectable local bounds; these are surface evidence, not a supplied axis.
21: measure_mesh_pixels includes hit-triangle normals/tilts: do not use roof/slope
22: points as if they established one physical wall edge. Check independent local
23: surfaces and their texture before deciding a construction frame. A direction
24: is not the rotation to apply; state the transform and inspect an aligned view.
25: Axis-parallel directions leave quarter-turn and half-turn ambiguities. Resolve
26: these using the asymmetric whole-building footprint and its long/short wings,
27: not a translation chosen to compensate for the wrong orientation. Establish the
28: old candidate's explicitly stated frame and inspect its baseline when recovering.
29: set_candidate_mesh_frame saves that transform on a NEW candidate: source XYZ =
30: rotate_xy(yaw)*original_Zup + translation_m. It keeps numerical BIM geometry,
31: changing placement relative to the original. overlay_mesh_candidate projects
32: actual source edges onto any saved mesh view without fitting; use side/top views
33: and individual floors to identify orientation, displacement and shape errors.
34: Hidden source edges are drawn as X-ray lines. Frame-only correction does not
35: establish footprint, heights or aperture fidelity. A later revise_bim preserves
36: the frame; remove obsolete frame claims in notes explicitly. For direct build_bim,
37: the optional mesh_frame uses mesh_sha256, yaw_degrees, translation_m, reason and
38: source_refs. No candidate receives an implicit frame from a viewing camera.
39: Choosing yaw is your alignment decision, not a supplied building answer. Missing
40: surfaces or regions excluded by bounds are missing evidence, never proof of a
41: blank wall or opening. Preserve visible window groups AND intervening wall strips;
42: repeated geometry must retain the observed gaps, not become one long window.
43: The parametric reference supports explicit floor/space templates and aperture spans.
44:
45: When inputs are prepared views of a textured 3D mesh, use their supplied metric
46: projection metadata. Local x/y need not be geographic east/north: retain the
47: explicit transform. Treat missing mesh surfaces as missing evidence, not proof
48: of an opening or blank wall. Infer plausible missing parts using available
49: context and record the basis. Without interior evidence, propose a useful
50: layout at the requested simplification, explicitly marking partitions/doors as
51: hypotheses. Do not claim recovered true interiors. build_parametric_bim can
52: expand explicit templates and window spans without mental coordinate repetition;
53: get_bim_reference('parametric') documents it. Full original images remain the
54: visual evidence; no prior generated model is an observation.
55:
56: Work from the physical partition layout before assigning detailed room uses.
57: For drawing reconstruction, read get_bim_reference('reconstruction') for a
58: measurement-to-source method, including calibration, wall junctions and opening
59: identity across views. It contains no case answers. Choose its applicable parts.
60: Trace each space's full extent, including corridor turns and nonrectangular
61: parts. Furniture groups, labels, dimension lines and door swings do not create
62: partitions. If a proposed split is uncertain, compare its entire extent with
63: visible wall evidence and adjoining spaces before using it as a physical wall.
64: Keep a continuous open space intact even if its use varies within it.
65:
66: Use a short, checkable observation instead of repeatedly estimating the same
67: coordinates in prose. After viewing a plan, choose the tool that resolves your
68: main uncertainty: view_pixel_region_overview can locate numbered background
69: regions; view_pixel_region shows the selected region's actual contour;
70: view_pixel_profile measures exact ink support; preview_space_trace overlays a
71: proposed complete boundary. Region IDs are pixel components, never automatic
72: rooms: furniture, text, door symbols and leaks can shape them. Pick color and
73: thresholds from the actual image; unsuitable color evidence permits another
74: method or an explicitly uncertain observation. Tools are optional, not a fixed
75: sequence. map_pixels and map_dimension_chain perform coordinate and dimension
76: arithmetic; they do not validate your interpretation or calibration.
77: For plan/elevation correspondence, compare_facade_spans tests BOTH directions
78: from independently observed complete opening lists. Read facade_correspondence
79: for its schema. Check absolute residuals as well as the direction difference;
80: relative_error_separated is only a relative comparison and absolute_fit_status
81: remains not_evaluated. The tool cannot establish that observations or types are correct.
82: When using measured endpoints, reference the saved profile_id/candidate in pixel
83: slots instead of retyping estimated coordinates. You still decide which peaks
84: belong to the same aperture and which dimension endpoints define the scale.
85:
86: Your primary role is coordination and resolving evidence conflicts.
87: review_detail asks Haiku a small local visual question using only selected
88: originals and your exact question. Use it when useful, with a bounded timeout.
89: Describe a location and observable question, not an expected wall or room answer;
90: check the returned measurements before applying them. Do not duplicate a whole
91: worker reading or spend the budget mentally calculating vertices. Annotation
92: plus pixels is stronger evidence than pixels alone, then explicit inference.
93: Uncertainty permits stated assumptions, not silent omission or invented evidence.
94:
95: Prioritize faithful physical partitions and openings over an early first draft.
96: Use the available budget to resolve consequential uncertainty and compare the
97: actual saved source with the originals. For a single floor with a rectangular footprint,
98: build_plan_bim can derive complete rooms and opening hosts from your observed
99: pixel partition paths; read plan_partition for its compact input format. This
100: avoids repeating shared room vertices and doing coordinate arithmetic yourself.
101: It returns the actual source overlaid on the same original using your anchors.
102: If compilation fails, its draft overlay shows the submitted pixel paths and
103: apertures, not a constructed or verified BIM. Compare the numbered paths with
104: the original before revising them. Closing a polygon is not evidence for a wall:
105: check both adjoining spatial extents and any continuation through a door aperture.
106: If a seed exists, inspect_candidate('seed') reads its proposal and checks;
107: include_geometry=False retrieves notes/frame/floor summary without a large
108: expanded geometry. Use floor_id to inspect one floor or read_candidate_items
109: to page exact cells/windows/openings; oversized inspections return a summary.
110: check_wall_dimensions also pages its host inventory and accepts floor_id.
111: Partial pages are observations of a saved proposal, never full replacement input.
112: Preserve reliable objects with local revisions.
113: A successful build/revision returns source plan images. Inspect them; for
114: positional comparisons use overlay_candidate with original pixel/metre anchors
115: supported by the same observed reference plane. Registered anchors are reused
116: after revisions, never fitted automatically to new walls. A rendered view is
117: not an independent observation and an image returned is not a completed review.
118: Use view_elevation_candidate for real source window/door heights; plan views
119: cannot reveal height errors. Examine the supplied views relevant to unresolved
120: geometry, and record any views or regions left unexamined.
121:
122: If an opening fails to attach, check the original wall path, adjoining spaces,
123: aperture marks and source host's plan/absolute-height bounds. An incorrect room
124: can be the cause. Do not move, shorten, delete or relabel an observed aperture
125: merely to fit the proposed room or clear a host error. Change a measurement only
126: with image evidence; explicitly retract a mistaken object with its reason and
127: source reference. Keep unresolved observations when a reliable fix is unavailable.
128:
129: Keep object IDs stable. Source room simplification and downstream thermal zoning
130: are separate. Do not split a real room into boxes or add fake walls/floors.
131: Unknown door state stays unknown. Use metres, x east/right, y north/up, z absolute
132: world height, including upper-floor openings. Original pixel coordinates are
133: shown in image metadata/grid; use those, not thumbnail dimensions. Clean crops
134: and display_scale magnify thin lines and labels without changing coordinates.
135:
136: Parameter details are available through get_bim_reference(topic):
137: - reconstruction: drawing observation, bounded wall evidence and source comparison.
138: - geometry: build_bim JSON schema, nonrectangular rooms and coordinate conventions.
139: - plan_partition: optional build_plan_bim from pixel walls/openings, single floor.
140: - edits: revise_bim operations, supported scopes and examples.
141: - wall_dimensions: optional wall-face offsets and dimension endpoint conversions.
142: - opening_review: observed-mark schema for check_openings; partial review is allowed.
143: Read the needed reference when preparing that call; avoid unrelated details.
144: Opening/partition reviews cover different things. check_openings lists actual
145: objects and can compare your observed marks; it checks observation consistency,
146: not visual truth. Unknown offsets stay unknown; never assume half a wall thickness
147: just to close a chain. A wall-dimension side/order error is not a room-location error.
148:
149: Finish with finish_bim(candidate), which records actual checks, then state the
150: selected candidate, assumptions and unresolved/unexamined scope honestly. Saving,
151: self-consistent geometry and successful image transport do not certify faithful
152: reconstruction. Do not ask the user for routine geometry choices.
153: """

## src/agent/execution/source_proposal.py L27-78

27:
28:
29: def _validate_proposal(proposal: dict) -> tuple[dict, list[str], list[str], dict | None]:
30:     if not isinstance(proposal, dict):
31:         raise TypeError("proposal must be an object")
32:     unknown = set(proposal) - _PROPOSAL_FIELDS
33:     missing = {"geometry", "assumptions", "unresolved"} - set(proposal)
34:     if unknown or missing:
35:         details = []
36:         if missing:
37:             details.append("missing " + ", ".join(sorted(missing)))
38:         if unknown:
39:             details.append("unknown " + ", ".join(sorted(unknown)))
40:         raise ValueError("proposal fields: " + "; ".join(details))
41:     if not isinstance(proposal["geometry"], dict):
42:         raise TypeError("proposal.geometry must be an object")
43:     # Legacy Window permits extra fields, but source generation always emits
44:     # entries from this collection as windows. Reject a conflicting declaration
45:     # before that can silently turn an explicitly identified door into glazing.
46:     windows = proposal["geometry"].get("windows", [])
47:     if isinstance(windows, list):
48:         conflicts = [
49:             f"windows[{index}] id={window.get('id')!r} kind={window['kind']!r}"
50:             for index, window in enumerate(windows)
51:             if isinstance(window, dict) and "kind" in window and window["kind"] != "window"
52:         ]
53:         if conflicts:
54:             raise ValueError(
55:                 "geometry.windows only accepts windows; conflicting kinds: " + "; ".join(conflicts)
56:                 + ". Put doors/passages in geometry.openings with kind, space_id, p1, p2 and z; "
57:                 "use other_space_id=null for an exterior opening. Preserve the declared type "
58:                 "and observed size when correcting the proposal."
59:             )
60:     for field in ("assumptions", "unresolved"):
61:         if not isinstance(proposal[field], list) or any(not isinstance(item, str) for item in proposal[field]):
62:             raise TypeError(f"proposal.{field} must be a list of strings")
63:     if "mesh_frame" in proposal:
64:         from src.agent.geometry.mesh_bim_frame import validate_mesh_frame
65:         validate_mesh_frame(proposal["mesh_frame"])
66:     enclosure = proposal.get("enclosure_declaration")
67:     if enclosure is not None and not isinstance(enclosure, dict):
68:         raise TypeError("proposal.enclosure_declaration must be an object")
69:     return proposal["geometry"], list(proposal["assumptions"]), list(proposal["unresolved"]), enclosure
70:
71:
72: def _html_list(rows: list[str]) -> str:
73:     if not rows:
74:         return "<li>无</li>"
75:     return "".join(f"<li>{html.escape(row, quote=True)}</li>" for row in rows)
76:
77:
78: def export_source_proposal(proposal: dict, out_dir: Path, *, provenance: dict | None = None) -> dict:

## src/agent/geometry/plan_partition.py L1-130

1: """Compile declared plan linework into a deterministic source proposal.
2:
3: The compiler is deliberately literal: it polygonizes a rectangular footprint
4: and the supplied physical partition representatives without snapping,
5: extending, clipping, or inventing linework.  Schema-v2 cannot encode a
6: non-rectangular floor footprint, so such footprints are rejected rather than
7: silently replaced by their bounding box.  Cells inside the footprint may be
8: arbitrary orthogonal polygons.
9: """
10: from __future__ import annotations
11:
12: import math
13: from collections.abc import Iterable
14: from typing import Any
15:
16: from shapely.geometry import LineString, Point, Polygon, box
17: from shapely.geometry.polygon import orient
18: from shapely.ops import polygonize_full, unary_union
19:
20: from src.agent.geometry.source_image_overlay import _axis_anchors
21:
22:
23: _PLAN_FIELDS = frozenset({
24:     "floor_id", "z_floor", "ceiling_height", "x_anchors", "y_anchors",
25:     "basis", "footprint_pixels", "partitions", "openings", "space_seeds",
26:     "assumptions", "unresolved",
27: })
28: _REQUIRED_PLAN_FIELDS = _PLAN_FIELDS - {"space_seeds"}
29: _PARTITION_FIELDS = frozenset({"id", "points", "source_refs"})
30: _OPENING_FIELDS = frozenset({
31:     "id", "kind", "p1", "p2", "z", "source_refs", "state", "assumptions",
32: })
33: _SEED_FIELDS = frozenset({"id", "point", "role", "source_refs"})
34: _AUTO_METHOD = (
35:     "Plan spaces were compiled deterministically from the declared footprint "
36:     "and physical partition segments; no snapping, extension, clipping, or "
37:     "inferred partition was applied."
38: )
39: _AUTO_CALIBRATION = (
40:     "Pixel-to-world calibration was supplied by the caller and was not "
41:     "independently verified."
42: )
43:
44:
45: class OpeningHostError(ValueError):
46:     """A full declared opening has no valid host; keep exact pixel evidence."""
47:
48:     def __init__(self, message: str, *, opening_id: str,
49:                  p1_pixel: tuple[float, float], p2_pixel: tuple[float, float]):
50:         super().__init__(message)
51:         self.opening_id = opening_id
52:         self.p1_pixel = list(p1_pixel)
53:         self.p2_pixel = list(p2_pixel)
54:
55:
56: def _number(value: object, *, path: str) -> float:
57:     if isinstance(value, bool) or not isinstance(value, (int, float)):
58:         raise TypeError(f"{path} must be a finite number")
59:     parsed = float(value)
60:     if not math.isfinite(parsed):
61:         raise ValueError(f"{path} must be a finite number")
62:     return parsed
63:
64:
65: def _text(value: object, *, path: str) -> str:
66:     if not isinstance(value, str) or not value.strip():
67:         raise ValueError(f"{path} must be a nonempty string")
68:     return value
69:
70:
71: def _fields(value: object, *, path: str, allowed: frozenset[str], required: frozenset[str]) -> dict:
72:     if not isinstance(value, dict):
73:         raise TypeError(f"{path} must be an object")
74:     unknown = set(value) - allowed
75:     missing = required - set(value)
76:     if unknown or missing:
77:         details = []
78:         if missing:
79:             details.append("missing " + ", ".join(sorted(missing)))
80:         if unknown:
81:             details.append("unknown " + ", ".join(sorted(unknown)))
82:         raise ValueError(f"{path} fields: " + "; ".join(details))
83:     return value
84:
85:
86: def _strings(value: object, *, path: str, require_one: bool = False) -> list[str]:
87:     if not isinstance(value, list) or (require_one and not value):
88:         suffix = " with at least one item" if require_one else ""
89:         raise TypeError(f"{path} must be a list of strings{suffix}")
90:     if any(not isinstance(item, str) or not item.strip() for item in value):
91:         raise ValueError(f"{path} entries must be nonempty strings")
92:     return list(value)
93:
94:
95: def _point(value: object, *, path: str, width: int, height: int) -> tuple[float, float]:
96:     if not isinstance(value, list) or len(value) != 2:
97:         raise ValueError(f"{path} must be [pixel_x, pixel_y]")
98:     point = (_number(value[0], path=f"{path}[0]"), _number(value[1], path=f"{path}[1]"))
99:     if not (0 <= point[0] < width and 0 <= point[1] < height):
100:         raise ValueError(f"{path} {list(point)} is outside image bounds {width}x{height}")
101:     return point
102:
103:
104: def _orthogonal(points: list[tuple[float, float]], *, path: str, closed: bool) -> None:
105:     pairs = list(zip(points, points[1:]))
106:     if closed:
107:         pairs.append((points[-1], points[0]))
108:     for index, (first, second) in enumerate(pairs):
109:         if first == second:
110:             raise ValueError(f"{path} segment {index} is degenerate at pixel {list(first)}")
111:         if first[0] != second[0] and first[1] != second[1]:
112:             raise ValueError(
113:                 f"{path} segment {index} is not orthogonal: {list(first)} -> {list(second)}"
114:             )
115:
116:
117: def _parts(geometry: Any) -> Iterable[Any]:
118:     if geometry.is_empty:
119:         return
120:     if geometry.geom_type in {"Point", "LineString"}:
121:         yield geometry
122:         return
123:     for part in geometry.geoms:
124:         yield from _parts(part)
125:
126:
127: def _rounded(value: float) -> float:
128:     result = round(float(value), 6)
129:     return 0.0 if result == 0 else result
130:

## AI_agent/logs/worklog/drafts/2026-09-23_observation_ledger/bim_agent_state.py.draft L1-118

1: """Persistent drawing observations, separate from decisions and built geometry.
2:
3: The coordinator owns this ledger. Workers retain their isolated workspaces;
4: their prose is never automatically promoted to an accepted observation.
5: """
6: from __future__ import annotations
7:
8: import hashlib
9: import json
10: from pathlib import Path
11: from typing import Literal
12:
13: from pydantic import BaseModel, ConfigDict, Field, JsonValue
14:
15:
16: def encoded(value: object) -> bytes:
17:     return (json.dumps(value, ensure_ascii=False, sort_keys=True,
18:                        indent=2, allow_nan=False) + "\n").encode()
19:
20:
21: class ImageEvidence(BaseModel):
22:     model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
23:     image: str = Field(min_length=1)
24:     box: list[float] = Field(min_length=4, max_length=4)
25:
26:
27: class Observation(BaseModel):
28:     model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
29:     topic: Literal["partition", "opening", "space", "connection", "dimension", "attribute"]
30:     statement: str = Field(min_length=1)
31:     evidence_kind: Literal["annotation_and_pixels", "pixels", "inference", "unknown"]
32:     confidence: Literal["low", "medium", "high", "unknown"]
33:     basis: str = Field(min_length=1)
34:     sources: list[ImageEvidence]
35:     object_refs: list[str] = Field(default_factory=list)
36:     value: JsonValue = None
37:     unresolved: list[str] = Field(default_factory=list)
38:
39:
40: class ObservationLedger:
41:     """Append immutable events; derive current decisions without rewriting evidence."""
42:
43:     def __init__(self, run: Path, manifest: dict, image_path):
44:         self.run = run
45:         self.manifest = manifest
46:         self.image_path = image_path
47:         self.folder = run / "observations"
48:
49:     def events(self) -> list[dict]:
50:         return [json.loads(path.read_text()) for path in sorted(self.folder.glob("event_*.json"))]
51:
52:     def _append(self, event: dict) -> dict:
53:         # The coordinator is the sole writer. Exclusive creation also rejects
54:         # accidental concurrent writes rather than silently overwriting history.
55:         self.folder.mkdir(exist_ok=True)
56:         index = len(self.events()) + 1
57:         event = {"event_id": f"event_{index:06d}", **event}
58:         with (self.folder / f"event_{index:06d}.json").open("xb") as stream:
59:             stream.write(encoded(event))
60:         return event
61:
62:     def record(self, data: dict) -> dict:
63:         observation = Observation.model_validate(data).model_dump()
64:         # JsonValue can contain overflowing floats nested inside a value.
65:         encoded(observation)
66:         for field in ("statement", "basis"):
67:             if not observation[field].strip():
68:                 raise ValueError(f"{field} must be non-empty")
69:         if observation["evidence_kind"] in {"annotation_and_pixels", "pixels"} and not observation["sources"]:
70:             raise ValueError("pixel observations require an original image location")
71:         for source in observation["sources"]:
72:             path = self.image_path(source["image"])
73:             from PIL import Image
74:             with Image.open(path) as picture:
75:                 width, height = picture.size
76:             left, top, right, bottom = source["box"]
77:             if not (0 <= left < right <= width and 0 <= top < bottom <= height):
78:                 raise ValueError("box must be inside the original image bounds")
79:             source.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
80:                           coordinate_frame="original_image_pixels")
81:         event = self._append({"kind": "observation", "observation": observation})
82:         return {"observation_id": event["event_id"], "status": "proposed",
83:                 "verification": "not_independently_verified", **observation}
84:
85:     def decide(self, observation_id: str, disposition: str, reason: str) -> dict:
86:         if disposition not in {"adopted", "deferred", "rejected"}:
87:             raise ValueError("disposition must be adopted, deferred or rejected")
88:         if not reason.strip():
89:             raise ValueError("a decision requires a non-empty reason")
90:         if observation_id not in {row["event_id"] for row in self.events() if row["kind"] == "observation"}:
91:             raise ValueError("unknown observation_id")
92:         return self._append({"kind": "decision", "observation_id": observation_id,
93:                              "disposition": disposition, "reason": reason})
94:
95:     def snapshot(self) -> dict:
96:         events = self.events()
97:         rows = {}
98:         for event in events:
99:             if event["kind"] == "observation":
100:                 rows[event["event_id"]] = {"observation_id": event["event_id"],
101:                     **event["observation"], "status": "proposed", "decision": None}
102:             else:
103:                 rows[event["observation_id"]].update(status=event["disposition"], decision=event)
104:         for row in rows.values():
105:             for source in row["sources"]:
106:                 # Fail visibly if admitted source bytes change; neither a saved
107:                 # observation nor an adopted decision makes stale evidence valid.
108:                 path = self.image_path(source["image"])
109:                 if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
110:                     raise ValueError("observation source image changed")
111:         return {"schema_version": "bim_observation_ledger_v1",
112:                 "input_manifest_sha256": hashlib.sha256((self.run / "inputs.json").read_bytes()).hexdigest(),
113:                 "event_count": len(events),
114:                 "events_sha256": hashlib.sha256(encoded(events)).hexdigest(),
115:                 "observations": list(rows.values()),
116:                 "verification": "not_independently_verified",
117:                 "geometry_application": "not_checked",
118:                 "note": "Adoption is a coordinator decision, not proof of fidelity or application to geometry."}
