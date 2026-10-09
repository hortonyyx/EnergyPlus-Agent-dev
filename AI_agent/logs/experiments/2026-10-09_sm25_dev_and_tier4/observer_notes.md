# 第一轮全流程观察

执行方为通过空白上下文派出的 GPT-6 Sol / high（请求型号；实际供应商型号回执若不可取则不补造）。从独立 `sol_cold` 目录原图开始。项目经理已看过旧失败记录，留在观察与评价侧，不提供几何答案。

## 开始与读图

- 执行方起始记录：2026-10-09 17:24:14 +08:00。
- 第一批调用读取 inputs 和五份通用参考；第二批看两张平面与四张立面整图；第三批按层分区查看六张局部平面图。
- 前三批共 18 个工具回执、12 张返回图片、0 工具错误；截至该检查点尚未建模，没有像素剖面调用。
- 17:25:30 前后纠正了执行方的型号元数据：原记录按自我身份写成 6.1 Sol，改为 requested_model=gpt-6-sol、actual_model=unknown。该纠正不含图纸信息、没有重启执行，也不证明实际发生型号漂移。
- 第一轮模型循环由外部会话承担，调用当前 domain MCP 工具；不作为 runtime v2 的模型循环、缓存或调度验证。

后续将依据原始工具参数与候选补记首次建模、返工、装配和交付，独立评价留到执行方结束。

## 首次建模与执行环境干预

- 首次一层 build_plan_bim 已写出 draft_001/candidate_01，随后工具回执报 GBK 解码错误。执行方独立重试一次，产生 draft_002/candidate_02，仍同错。不能把失败回执等同于未写入。
- 项目经理只读查看 draft_001/draft_view.png：两处室外凹入在首份声明中已保留；这只是首层外形观察，不是整案质量验收。
- 已定位外部 MCP bridge 启动 server 时不传 UTF-8 环境，而 MCP 默认环境白名单不继承外层 PYTHONUTF8。子进程内部无 encoding 的 read_text 在 Windows 按 GBK 解码 UTF-8 产物。
- 项目经理提醒暂停相同声明的盲重提，提供仅实验 helper 的 UTF-8 子进程环境修复；未改 domain/kernel 或图纸内容。执行方先只读核已有候选，再自行续建。该基础设施帮助是显式开发干预，原失败与耗时保留。

## 两层、装配与立面返工

- 执行方自行生成 F1/F2，两层草稿分别编译为 14/15 个空间；内墙差异检查均降到零。该检查的范围限制仍成立，不等同原图完整保真。
- 第一次 assemble_plan_bim 因 stale plan hash 拒绝；执行方 inspect 当前草稿后装配成功。顶层 bridge 回执将这次格式/引用错误与 GBK 两次错误分别保留。
- 候选 07 为首次整栋装配。执行方逐立面看原图和候选回叠，再按东立面不等间距尺寸链改窗位，并修北/西大窗和东外门高度；生成候选 10，随后调整走廊用途为候选 11。
- 执行方报告已为 34 个外部门窗绑定并确认高度依据；将由生成结束后的独立评价核实。项目经理未向执行方提供上述几何修正答案。

## 冻结与独立评价

- 17:46:47 成功 finish_bim，最终 candidate_12；从 17:24:14 起约 22 分 33 秒。执行方补记真实外部会话 summary/dev_end，不再改候选。
- 共同 evaluator：29/29 空间；61/61 门窗存在与宿主、30/30 门连接；位置 60/61；外部门窗高度 34/34；无实质拓扑错误。房间边界分档 9/13/7/0，门窗沿墙分档 53/7/1/0，外部高度 34/0/0/0（依次 ≤5、5–10、10–30、>30 cm）。
- 项目经理复看最终 F1/F2 回叠，东北与西侧两处室外凹入均未被填充；正式独立复核另存 cold_quality_review.md。
- 对照条件差异：Sol 可自行写 Python/JSON，再调用公共 domain；分工读图员只有受限 reader tools。第一轮三份脚本分别承接声明构造、逐开口证据绑定、用途元数据。因此不能把第二轮差异全部归于模型智力。

## 第二轮启动与包装器问题

- 第二轮模型组合：Paratera Qwen3.8-27B / thinking 平面读图员 ×2，Qwen3.8-Flash / thinking 立面读图员 ×4；项目经理人工担任调度员。runtime-v2-20261009 / domain-v56-20261009 保持不变。
- 初始任务只含原图/层/方位与共同包围盒坐标原点，无 GT、旧计数、旧尺寸、旧几何或第一轮答案。
- 第一次 manual_dispatch_sm25 在模型 HTTP 前被实验 GuardedAdapter 的重复费用检查错误拦住：runtime 已记录当前 adapter_request，而包装器将其尚无 usage 误判为历史缺失账单。实际 HTTP=0；runtime 中 adapter_request=1，两者不可混计。
- 保留零 HTTP 失败目录。实验包装修复由 prepare_fourth_tier 离线核验；新的 retry1 配置只换输出目录与批次标识，费用/模型/输入/版本不变。

## 第二轮读图阶段（运行中）

- retry1 于 17:52:19 初始化，随后六个任务实际并发。未向读图员注入第一轮答案或两处凹入的提示；本阶段没有建筑纠错帮助。
- 四个 Flash 立面读图员均在约 9 分钟内提交：南 9 请求/14 工具，北 12/22，东 14/23，西 14/21；大量工具是 pixel_profile/view_pixel_profile。所有提交首轮被接受，尚不代表质量正确。
- 18:02 时两位 27B 仍无试建；F1 已完成 1 次响应、2 个工具（view_image/view_plan_blocks），第二次请求仍等待；F2 已完成 4 次响应、7 个工具（含 4 次 pixel_profile），第五次请求仍等待。HTTP 请求等待包含供应商侧处理，不能称纯生成时间。
- 东立面 artifact 明确记录：门墨迹底距基线约 0.19 m，模型却选择 sill=0、head=2.1，理由是按门落地/整尺寸处理。这是观测已得到但被默认解释覆盖的可观察行为；需原图复核后由调度员处理，不能把接受提交等同保真。
- 报告 helper 已用 runtime accounting 归一化 Paratera usage：18:02 快照 56 请求/54 响应/2 pending，provider token 1,938,958，已结算估算 1.6363818 元，缓存 1,490,048/1,820,102；这些不是最终用量或发票。
- 两位 plan reader 均使用了 view_plan_blocks；F1 第二请求携带 10 张图，实报 image tokens 24,594。离线前缀对照未发现只有 F1 被 runtime 异常改动前缀，不能把其前两次 cache=0 直接归因 runtime。细节见 dispatch_efficiency_notes.md。
- 当前 domain 已在连续观察达到 6 次时反馈先试建的提醒；F1 到约 24 分钟已有 36 次 pixel_profile，却未试建。追加同类文字提醒不是尚未尝试的办法。
- F2 约 24 分钟首次 trial：完整 footprint 含正确的两处室外凹入，17 处 divider 的 scoped drawing_differences=0。项目经理看了 draft_001 回叠，主要分隔/开口与原图相符，尚不能作为最终独立质量验收。
- 首次 F2 trial 被 `opening D-A.z [0,2.1] outside floor vertical bounds [3,6]` 拒绝；原始 tool_invocation 确认 model 同时提交了 z_floor=3、ceiling_height=3（标明暂定）和相对式 opening.z=[0,2.1]。不是 kernel 自动改坏，也不是室外区域被填。工具已给具体字段修复提示，项目经理未介入更正。
- 预备了尚未发送的 elevation_east_rework：只指出当前 reader 自己记录的门底墨迹和提交值矛盾，不给 GT 或第一轮数值答案。须等初批 delegate 返回后再执行。

## 第二轮初始 delegate 收口与定向重工（运行中）

- 初始六角色约 33 分钟内全部完成：79 个 HTTP 请求，runtime settlement 累计估算 7.3357986 CNY。角色实际 runtime elapsed 分别为南立面 4:23.459、北立面 7:47.860、东立面 7:58.105、西立面 9:23.897、F2 26:10.035、F1 32:02.413；六者并发，不能相加作墙钟，也不是纯生成时间。
- F1 到启动后约 28:48 才首次 trial。首稿为 8 点正交 footprint、18 partitions、15 doors、15 windows、15 seeds；原图和 draft_001 overlay 的可见对照表明两处外轮廓凹入和主要房间分隔均已表达。首份 trial 的 18 条内分隔 scoped drawing differences 为 0，但该工具明示不检查外墙/门窗/整图完整性。
- F1 `trial_001` 因东侧七条横向分隔离 footprint 端线约 5 px 而失败；按回执把七个端点延到外墙。`trial_002` 又因 `S-ENTRY`、`S-CORR` 同处一个连通空间失败；检查原图未见二者间实体隔墙后，仅删除冗余 `S-CORR`。`trial_003` 在 18:23:16 成功，candidate_01 为 14 spaces、30 openings。
- F1 成功 trial 后的提交又有两次 schema 摩擦：第一次把说明句放进 `notes.item`，第二次把裸 `S-ENTRY` 当 item，均被“不是已声明 plan object”拒绝；第三次仅传 `trial_id=latest` 才 accepted。两次是提交格式/对象引用错误，不是几何失败；成功 trial 到 accepted 约 64 秒。
- 全图复看发现 F1 有一处明确缺门：原图西侧内凹竖墙、两间西南会议室上方有单扇门，draft_003 没有 opening；原图可见门符号 16 个，reader 只提交 15 个。candidate_05 的 reader assembly 也独立报 West artifact `F1_D2` 为 elevation-only，与缺少 plan opening 相容。此检查未用 GT；当前尺度没有再发现同等明确的 F1 主墙/开口遗漏，不代表完整验收。
- 项目经理因此派出 `plan_f1_rework`，只给“自身 overlay 与原图可见缺门”的语义位置，不提供坐标；同时派出 `elevation_east_rework`，只要求解决该 reader 自身记录 D1 墨迹底部约 0.19 m、提交 sill=0 的矛盾。东立面 rework 首次 target 写为裸 `D1`，在 task admission、HTTP 之前失败；改为合法 `openings:D1` 后才进入运行。该 admission 失败不计模型请求或费用。当前两个 rework 各只有 1 个 adapter request，尚无完成回执，不推断结果。

## 第二轮终态

- 两项定向 rework 均正常完成。`plan_f1_rework` 用 11 个 HTTP 请求、12 个工具调用，实际几何变化只有新增缺失门 `D15`；第一次 add operation 多带 `changes`、`id`，被 admission 以 `unknown changes, id` 拒绝，修正后试建通过。提交又两次因 notes.item 分别写成说明句和裸 `D15` 被拒，改成 canonical `plan.openings:D15` 后接受。
- `elevation_east_rework` 用 8 个 HTTP 请求、12 个工具调用，将 D1 改为 sill=0.19 m、head=2.30 m；其余 12 个 opening 与各 level 保持原提交值。这里修正的是 reader 自己已观察到、却曾被落地假设覆盖的值。
- 调度员重建两层、重新装配并应用高度，最终 `candidate_10` 成功 `finish_bim` 并冻结。第二轮合计 98 个 HTTP 请求，runtime settlement 累计估算 8.7029404 CNY；这是运行时估算，不是供应商最终账单。
- 共同 evaluator 对 candidate_10 报告：29/29 spaces、61/61 openings 与 hosts、30/30 connections、34/34 exterior heights，无实质 finding；房间边界分档 20/2/7/0，opening 沿墙分档 57/4/0/0。严格位置阈值下另有 3 个 false，已由独立 reviewer 调查，本记录不重复判定。
