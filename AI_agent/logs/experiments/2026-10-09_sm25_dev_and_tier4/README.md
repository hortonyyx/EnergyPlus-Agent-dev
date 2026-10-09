# sm25 模型能力与分工开发诊断

状态：两轮均已交付、冻结并完成共同评价；第二轮含项目经理指出的两项局部返工。生产代码未改，下一轮迭代留待讨论。

## 本轮授权与顺序

用户先要求完整 sm25；随后纠正为：先冷启 GPT-6 Sol 独立完成整案，由项目经理持续观察；再由项目经理担任调度员，派 3/4 档模型完成整案，观察能力与工具缺口后讨论迭代。不由 SOTA 模型先完成第一轮。

1. 第一轮：显式请求 GPT-6 Sol / high，独立原图输入、当前公共 BIM 工具，禁读 GT、旧建模声明与历史答案。执行方由空白上下文子代理启动，通过 MCP bridge 调用 domain；不是自有 runtime 的 LLM 循环。模型实际回执若不可取得，不以自我介绍补造实际型号或用量。项目经理不提供建筑答案；记录原始工具参数、回执、图片、候选与终态。
2. 第二轮：项目经理作为调度员，依据第一轮过程确定局部任务，再调用已授权线路上的 3/4 档模型。记录每次介入，区分调度、工具辅助、指出错误与直接提供答案。第二轮不能当作完全自主运行。

本轮保持 runtime v2 / domain v56，生产代码不改。实验包装与观察记录属于开发辅助，不作为产品新增能力。DeepSeek 禁止；无自动付费回退。Paratera 使用既有获准额度并设本批保护上限，具体选择由准备记录确认。

执行基线 Git HEAD 为 5ea0e893；domain 注册 source_commit 为 7c76446e，二者分别表示当时仓库头与已登记实现版本，不互相冒充。完整版本名是 runtime-v2-20261009 / domain-v56-20261009。

用户询问 runtime 后已明确回复上述第一轮执行边界；第二轮计划由项目经理通过自有 runtime 分派读图任务。第一轮不能用于比较自有 runtime 的缓存与调度效率。

`AI_agent/archive/local_backup/sm25_dev_tier4_20261009/dev` 只完成输入准备及工具 schema 读取，未建模、未调用 work model；用户纠正后停止使用。第一轮使用独立 `sol_cold` 目录。项目经理已读过失败记录和原图，观察与第二轮属于有先验的开发诊断；第一轮执行方不继承这些上下文。

## 必须保留的质量范围

整案包含各层空间、外形、门窗存在/位置/宿主/连接、各立面高度与可查看 BIM。此前错误是两处室外区域被填成室内；约 140 m² 只对应东北一处，不是总面积。该失败信息仅在评测与项目经理侧保留，不发给冷启执行模型。

最终按项目固定表格汇报质量、5/10/30 cm 精度分档、耗时、用量/费用、缓存与行为、干预、对照边界及成果地址。

## 第一轮结果

| 项目 | 冷启 GPT-6 Sol（请求型号） |
|---|---|
| 版本/模式 | domain-v56-20261009；外部 dev model 会话经 MCP，未走 runtime v2 模型循环 |
| 生成 | 17:24:14 → 17:46:47，22 分 33 秒；candidate_12；12 个候选，54 次顶层工具调用，4 次错误 |
| 实质质量 | 29/29 空间；61/61 门窗与宿主；30/30 门连接；两处室外凹入在两层均无假楼板，未见实质拓扑错误 |
| 位置/高度 | 位置 60/61 达评价器标准；唯一未达标内门沿墙 12.97 cm、宿主及连接正确；外部高度 34/34 |
| 分档 | 房间边界 9/13/7/0，门窗沿墙 53/7/1/0，外部高度 34/0/0/0；顺序 ≤5/5–10/10–30/>30 cm |
| 用量/费用/缓存 | 外部会话未提供供应商回执，全部 unknown；订阅不记为零成本 |
| 边界 | 曾由项目经理修复实验 bridge 的 Windows UTF-8 环境；执行方自行写三份辅助脚本；室内门高暂定，图纸未提供竖向交通 |

行为统计见 [cold_behavior_review.md](cold_behavior_review.md)，独立质量复核见 [cold_quality_review.md](cold_quality_review.md)，干预与阶段观察见 [observer_notes.md](observer_notes.md)。原始结果在 `AI_agent/archive/local_backup/sm25_dev_tier4_20261009/sol_cold/`，独立评价及事后回叠在其 `dev_evaluation/`。

## 第二轮执行方式与启动记录

根 dev model 人工担任调度员；Qwen3.8-27B / thinking 负责 F1/F2，Qwen3.8-Flash / thinking 负责四个立面，均 Paratera 原线路，无自动回退。已批准开发额度内设置本次 runtime 估算费用保护上限 20 元。runtime-v2-20261009 / domain-v56-20261009，生产代码不改。

第一次 `manual_dispatch_sm25` 因实验 wrapper 把当前 pending adapter_request 误认成历史费用缺失，在 HTTP 前停止（HTTP=0）。失败目录完整保留。删除重复判断后，由 runtime 原生共享账本继续负责费用保护；离线 mock 已验证。17:52:19 初始化新目录 `manual_dispatch_sm25_retry1`，按相同六任务实际调用。

现有 `scripts/dev/observe_run.py` 的 token 字段仅覆盖另一供应商格式，不能直接读 Paratera 的 prompt/completion/cached 原始字段，可能显示假零；本次使用原始 usage 与 runtime accounting 归一化核对，修正限于实验报告工具。

## 第二轮最终结果与介入边界

第二轮由项目经理通过当前 runtime 的 RoleSession 人工调度；首次六任务不含第一轮计数、坐标或两处凹入提示。项目经理已知旧失败及第一轮评价，因此不是盲测。生成模型未接触 GT，第二轮自己的 GT 评价在终态之后进行。初稿 candidate_05 与最终 candidate_10 都保留，没有用评价结果继续改模。

| 项目 | 初始六读图员 + 确定性装配，candidate_05 | 人工指出问题并返工后，candidate_10 |
|---|---|---|
| 外形、空间、隔墙 | 29/29 空间，两处室外凹入均保留，无错拆错并 | 同左，源/显示楼板和天花板均未填凹入 |
| 门窗存在、宿主、连接 | 60/61 门窗及宿主，29/30 门连接；漏西侧凹墙外门 | 61/61 门窗及宿主，30/30 门连接；无额外门窗 |
| 外部高度 | 33/34 匹配，32/34 达标；东外门整体下移约 20 cm，另缺一外门 | 34/34 匹配且全部 ≤5 cm |
| 评价器位置阈值 | 57/61 | 58/61；3 项因横向 13.67/13.67/14.58 cm 超内墙 8 cm 阈值，宿主/连接正确 |
| 生成状态 | 需处理 West elevation-only，尚未正式选择交付 | 整栋交付成功，candidate_10，source geometry pass |
| 质量判断 | 漏门属于实质错误；东门高是观测被假设覆盖 | 当前分档下无实质拓扑错误；仍非严格零误差 |

项目经理先看 F1 自身回叠发现漏门，装配回执也报告 West F1_D2 为 elevation-only；返工只指出位置语境，不给坐标。东立面原 artifact 已记录墨迹底离地约 0.19 m，却按门落地假设写 0–2.1 m；项目经理指出这个内部矛盾并要求复看原图。返工后 F1 仅新增 D15；东门为 0.19–2.30 m，其他 12 个东立面开口和楼层标高完全保持。这是人工辅助后的成功，不能称小模型自主整案成功。

| 精度范围 | Sol 最终 | 分工初始 | 分工最终 |
|---|---:|---:|---:|
| 房间边界，29 个；≤5 / 5–10 / 10–30 / >30 cm | 9 / 13 / 7 / 0 | 20 / 2 / 7 / 0 | 20 / 2 / 7 / 0 |
| 门窗沿墙端点，参照 61 个；同上四档 | 53 / 7 / 1 / 0 | 56 / 4 / 0 / 0，另漏 1 | 57 / 4 / 0 / 0 |
| 外部上下沿，参照 34 个；同上四档 | 34 / 0 / 0 / 0 | 32 / 0 / 1 / 0，另漏 1 | 34 / 0 / 0 / 0 |
| 离参考墙线 >30 cm | 0 | 0（已匹配部分） | 0 |

“58/61 位置”与“全部沿墙 ≤10 cm”不矛盾：F1:D10、F1:D11、F2:D-M 的未达标来自参考墙线横向差；门均贴合自己候选的 x=9.09 m 宿主。保留该偏差，不把它写成漏门或挂错墙。2 cm 原始 severe 只作诊断。

## 逐角色行为

下表分钟以首个 reader 事件为零，晚于初始化约 0.5 分钟；并发时长不可相加。两位平面初始角色的 runtime elapsed 分别约 32:02、26:10。最终总墙钟按初始化到 root stop 为 45:31.985，含人工调度、查看、返工与装配，不是纯模型时间；receipt 在最后落盘前采样为 45:28.486。

| 任务 / 型号 / thinking | 开始 → 首 trial → 首成功 → 接受提交 → 结束（分钟） | 请求 / 工具 / 工具错误 | 行为与修正 |
|---|---|---:|---|
| F1 / 27B / 开 | 0.1 → 28.6 → 30.5 → 31.6 → 31.8 | 15 / 58 / 4 | 首 trial 前 48 次 pixel_profile；7 个隔墙端点未接齐、冗余 seed 自修；2 次备注引用错误；漏 1 外门 |
| F2 / 27B / 开 | 0.1 → 23.5 → 24.7 → 25.8 → 25.9 | 15 / 19 / 5 | 首稿整体形状正确；开口相对 Z 与楼层绝对 Z 混用，随后自修；4 次备注引用错误 |
| 南 / Flash / 开 | 0.0 → — → — → 4.0 → 4.2 | 9 / 14 / 0 | 首次提交接受；最终几何高度正确，像素标定仍有小偏差 |
| 北 / Flash / 开 | 0.0 → — → — → 7.4 → 7.6 | 12 / 22 / 0 | 首次提交接受；大小窗高度均正确 |
| 东 / Flash / 开 | 0.0 → — → — → 7.5 → 7.8 | 14 / 23 / 0 | 观测到门底间隙，却被落地假设覆盖 |
| 西 / Flash / 开 | 0.0 → — → — → 9.0 → 9.2 | 14 / 21 / 0 | 提交了平面遗漏的外门；保留图示离地门高 |
| F1 局部返工 / 27B / 开 | 33.4 → 37.3 → 40.0 → 41.1 → 41.3 | 11 / 12 / 3 | 1 次 add 操作字段错误、2 次备注错误；补门成功 |
| 东局部返工 / Flash / 开 | 33.3 → — → — → 39.5 → 39.8 | 8 / 12 / 0 | 重查门高，实际修正且保留其他开口 |

读图员总计 181 工具调用，169 成功 / 12 失败，全部失败在平面角色。其中 8 次为 submit_plan_reading 可选 notes.item 引用错误。调度员另有 8 次成功确定性工具调用（两次装配、一次开口检查、四面回叠、一次 finish）；不混入读图员计数。调度员首次返工把 target 写成裸 D1 被 admission 拒绝，改为 openings:D1 后继续，发生在 HTTP 前，单独记录。

## 用量、缓存与时间边界

| 项目 | 第二轮最终 |
|---|---:|
| 请求 / 响应 / 失败 / pending | 98 / 98 / 0 / 0，无供应商或型号回退 |
| 输入总量（含缓存、图片） | 4,933,811 token |
| 未缓存输入 / 缓存读取 | 1,193,267 / 3,740,544 token |
| 输出 / 供应商合计 | 325,190 / 5,259,001 token |
| 实报图片（已在输入内） | 667,777 token，不重复加入供应商合计 |
| 加权缓存率 | 75.81% = 3,740,544 / 4,933,811 |
| 缓存写入量 | 未报告，不作 0 |
| 压缩 / 预算排队事件 | 5 / 0 |
| 估算 CNY | 8.7029404；27B 7.6161090，Flash 1.0868314 |
| 其中局部返工 | 19 请求，估算 1.3671418 CNY |
| 实际发票 / 实时余额 | 未取得；按旧项目账面约 58 元扣本次估算后约 49.3 元，不是余额查询 |
| 模型请求累计耗时 | 5,666.417 秒，约 94.44 分钟；并发，不能当墙钟或纯生成时间 |
| reader 工具累计执行 | 181 次共 42.484 秒；并发，调度员操作另计，未分类本地时间不伪装为精确墙钟开销 |

费用采用 runtime 既有历史账单反推单价，含额外图片计费；预算 charge 5,926,778 token 不是供应商 total。settlement 逐项核对无不一致、无坏行/残尾/缺失 usage。根调度员在此 runtime 的 HTTP 模型请求为零，只代表人工调度方式；Codex/GPT 开发会话用量仍未知，不记为零成本。完整明细见 [final_runtime_accounting.json](final_runtime_accounting.json)、[逐任务账本与时间口径](dispatch_accounting_notes.md)。

## 能说明什么、下一步讨论什么

1. 当前 domain v56 可以承载正确 sm25：Sol 无实质拓扑错误，27B 两份首稿也都读对两处凹入。因此不能将上次两块假楼板简单归为 kernel 必然错误，也不能因这一次成功声称稳定恢复。
2. work model 能力显著影响完整观察、假设取舍、工具操作和自修；这些能力应分别衡量。局部测量做了很多，不等于完整性更好；已经量出的证据也可能被错误默认值覆盖。
3. 机械接口仍大量消耗能力。现有先试建提醒、trial_id=latest、自动证据、坐标转换、几何规整和有界返工都已存在；下一步应检验如何让这些能力成为更短的默认操作路径，不能把已存在的功能重新当方案。
4. 第一轮外部会话允许 Python/脚本和通用工具，第二轮 reader 只有局部工具和不同 guidance；型号、上下文、工具面及人工帮助均不同。这不是纯模型能力 A/B，也不证明 runtime 优于 Claude Code。再验证应先固定这些条件，不自动加角色或收紧时限。

此轮只做诊断和开发辅助；runtime、domain/BIM rules/kernel/tools/methods/roles/guidance 生产实现均未迭代。后续方向见 [能力拆分讨论](capability_diagnosis.md)，本轮不自动追加付费试跑。

## 查看结果与验证边界

| 运行 | 两层平面 | 事后原图回叠 | BIM 查看页 |
|---|---|---|---|
| Sol | [F1](../../../archive/local_backup/sm25_dev_tier4_20261009/sol_cold/dev_evaluation/display/plan_F1.png) / [F2](../../../archive/local_backup/sm25_dev_tier4_20261009/sol_cold/dev_evaluation/display/plan_F2.png) | [F1](../../../archive/local_backup/sm25_dev_tier4_20261009/sol_cold/dev_evaluation/overlays/plan_F1.png) / [F2](../../../archive/local_backup/sm25_dev_tier4_20261009/sol_cold/dev_evaluation/overlays/plan_F2.png) | [viewer](../../../archive/local_backup/sm25_dev_tier4_20261009/sol_cold/dev_evaluation/display/viewer.html) |
| 人工调度分工最终 | [F1](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/display/plan_F1.png) / [F2](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/display/plan_F2.png) | [F1](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/overlays/plan_F1.png) / [F2](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/overlays/plan_F2.png) | [viewer](../../../archive/local_backup/2026-10-09_sm25_dev_and_tier4/manual_dispatch_sm25_retry1/dev_evaluation/display/viewer.html) |

每个 dev_evaluation/overlays 另有四立面回叠，evaluation/index.html 有逐对象记录。第二轮终态和原交付页在运行目录的 receipt.json、bim/delivery.html；初稿另存 dev_evaluation_initial，不冒充正式交付。独立质量复核见 [dispatch_quality_review.md](dispatch_quality_review.md)，过程与基础设施边界见 [observer_notes.md](observer_notes.md)、[dispatch_efficiency_notes.md](dispatch_efficiency_notes.md)。

两轮均实际打开过 Chromium 查看页。第二轮已切换 F1/F2，控制正常，最终页无 console error；最初入口仅 favicon 404。截图在仓库 output/playwright/sm25_manual_*.png。查看页仍显示旧暂定 3.0 m 层高等历史假设，以及过长标高证据 JSON；最终源标高已正确解析为每层 3.6 m，旧说明属于呈现/溯源问题，本轮未改产品界面。室内门高仍为假设、竖向交通未凭空补造；未做 EnergyPlus 下游验收。
