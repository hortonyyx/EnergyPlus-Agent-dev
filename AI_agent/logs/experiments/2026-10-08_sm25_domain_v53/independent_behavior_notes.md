# sm25 domain v53 独立行为终审

**结论：本次约 104.68 分钟自动结束，未生成整案 candidate，未交付。四份立面提交 accepted；所有平面试建均未通过。** 本报告只读观察完整运行与定向原始证据，没有给 work model 提示、改冻结代码或运行产物。

## 条件与证据口径

- work model：GLMFlash（glm-5.3-flash），所有角色 medium；runtime-v1-20261007；domain-v53-20261008；分工模式 sm25。
- 真实 adapter_request 已核 max_tokens=32000、thinking=adaptive、output_config.effort=medium、stream=false；供应商没有确认服务端实际应用参数。
- 运行目录：D:\EnergyPlus-Agent-worktrees\run-sm25-v53-20261008\AI_agent\archive\local_backup\sm25_v53\sm25_role_v53
- 全部 1,381 个事件，终点 event-001380；events.jsonl SHA-256：8bcdfed0df8536d1b399fd01b3244e4fb8d9c8a9b2d377c073826247917ca089
- 总耗时以 root receipt 的 6,280.745 秒计（含首个事件前的启动时间）；下表事件分钟以第一个事件 2026-10-08T15:37:53.245974Z 为零点，因此终止事件为104.51分。
- observe_run.py 的 requests 实际为响应数，tool_errors 没覆盖 outcome=failed；本报告直接按事件重算。根 receipt 的 model_calls=4、tool_calls=5、reported_tokens=48,701只对应调度员，不代表全案。

## 全流程关键行为

| 时间（分） | 实际行为和返回 |
|---:|---|
| 0.65 | 调度员一次派齐2名平面和4名立面读图员。 |
| 1.13–3.54 | 三次429与一次HTTP500；均在原任务后续请求中恢复，未永久丢弃角色。另有 view_image 空文件名错误。 |
| 3.66 / 5.48 / 5.70 / 6.75 | 南、北、西、东立面提交均真实 accepted；北立面5.16分第一次提交因像素起止反序拒绝，20秒后修正。accepted不证明准确性完成验收。 |
| 24.47–26.51 | F1 首次试建15格式错，查 room_types 后第二试余1项 tick数量错误；第三试进入本地尺寸对齐器，StopIteration 被 runtime 记为 unknown_write_outcome，角色停止。 |
| 25.12 / 34.81 / 47.45 | F2连续三次32,000-token截断；前两次runtime丢弃截断结果并续写，第三次停止 incomplete_response。末次虽有1个tool_call，仍未执行；整个首轮F2没有试建。 |
| 47.50–48.14 | 调度员收到两平面失败后重派 F1b/F2b；引用 previous_task_id，但只有泛化“完成完整稿”要求，没有具体恢复方案。再次从看图开始，两者再次漏填 view_image 文件名。 |
| 73.35–76.04 | F2b 首次试建13格式错→3项tick数量错→无有效draft却局部修改被拒→几何编译发现隔墙在外轮廓外。 |
| 81.97–91.27 | F1b 首试14格式错（7条 printed_segments_mm）→大量悬线；途中给partition加z被拒；最终缩到一段真实长断墙 p_strip_w，仍不通过。 |
| 83.97–100.40 | F2b退化轮廓边→大量悬线→少量悬线→重复空间种子→高度超楼层→找不到完整宿主→D-exec仅单侧宿主且非外边界。期间还发生缺collection、漏source_refs、修改不存在ID等返工。不同错误逐步消失，仍无成功candidate。 |
| 93.67 | F1b root_time_budget_exhausted，因共享根账本的已结算时长加兄弟未完成预留占满；不是45分钟子任务限额，也不是180分钟墙钟到时。 |
| 104.25–104.51 | F2b末次请求仅剩7.653秒预留，发生TimeoutError（没有HTTP429）、随后budget settlement超预留；F2b停止，调度员收到失败并time_budget_exhausted结束。主助手未手动停止。 |

## 逐角色结果

| 角色 | 请求尝试 / 响应 | 结束事件分钟 | 实际终态 |
|---|---:|---:|---|
| coordinator | 4 / 4 | 104.51 | time_budget_exhausted |
| elev_east | 10 / 10 | 6.98 | completed |
| elev_south | 7 / 6 | 3.91 | completed |
| elev_north | 8 / 8 | 5.66 | completed |
| elev_west | 7 / 5 | 5.94 | completed |
| plan_f2 | 10 / 9 | 47.47 | incomplete_response |
| plan_f1 | 12 / 12 | 26.51 | unknown_write_outcome |
| plan_f2b | 29 / 28 | 104.35 | root_time_budget_exhausted |
| plan_f1b | 18 / 18 | 93.67 | root_time_budget_exhausted |

成功平面试建、平面提交、装配、>30cm 双原图裁决、G1 复核继承、高度应用到全楼候选、finish_bim均**未发生**。因而不能判断G1装配修复在work model整案中的效果，也不能把尚未进入的严格裁决规则当作本次失败原因。

## 请求、工具与用量

- 实际105次 adapter_request，100次 model_response，5次有明确失败事件；没有去向不明的请求。
- 5次失败：temporary_rate_limit / HTTP429三次，service_unavailable / HTTP500一次，timeout / TimeoutError一次。前4次有后续同任务真实请求；仅HTTP500恢复显式记了1个 lifecycle retry，不能据此说只发生1次恢复。末次超时没有usage也没有重试。
- 截断3次，均在首轮F2；前2次续写、第3次停止。截断已返回usage，属于100次响应的一部分，不能重复加到105次请求之外。
- 工具调用与返回均137次：110 succeeded、26 failed、1 unknown。delegate_readers自身 succeeded不代表子任务成功。

| 供应商原始usage字段 | 已知数量 |
|---|---:|
| input_tokens（未并入缓存列） | 2,637,143 |
| output_tokens | 501,027 |
| cache_read_input_tokens | 1,753,920 |
| cache_creation_input_tokens | 0 |
| 已知报告量之和 | 4,892,090 |

这些数字仅来自100次响应的raw usage，input与cache分列；未混入runtime另估的图片token。5次失败请求没有usage，不能将上表宣称为完整供应商账单或全部真实消耗。逐角色原始数在JSON。

## 可用于迭代的结论与边界

1. **确定的domain/kernel缺陷。** Q1尺寸对齐器逐边变异造成邻边暂时斜化，触发StopIteration；不是G1新引入，也不是work model格式错误。见[独立异常调查](unknown_write_investigation.md)。
2. **确定的runtime预算与可观察性问题。** unknown-write没有保存异常类型；10,800秒同时约束墙钟与共享请求时长账本，并发请求时长累加，加上未完成预留，可让角色在容量暂被兄弟占用时永久停止。见[预算调查](budget_stop_investigation.md)。不能把本轮称为“跑满3小时”。
3. **长输出没有保证可靠声明。** 首轮F1在第三次试建前仍有明确隔墙/连通、外门朝向和门位置误读；仅检查未编译声明，不能作最终源BIM评分。见[独立质量复核](independent_quality_notes.md)。
4. **反馈能推进，但首稿与返工负担仍重。** 第二轮错误从格式逐步进入几何/宿主，说明不是原样死循环；最终仍没有平面可用稿，不能假设增加时间必然成功。
5. **待检验：格式提供方式与首稿负担。** 首轮F1首次失败后仅查room_types，其他平面角色未主动查询参考（不等于没有自动附带guide/schema）。三份首稿都用printed_segments_mm，工具描述恰写“printed segments_mm”；可能存在措辞诱因，需局部对照验证。不能把这点或未先查参考定为长思考/截断的已证根因。

## 连续观察记录

- 观察UTC 2026-10-08T15:41:11.564527+00:00，最新事件 event-000285（事件时间2.98分）：0.65 分钟调度员一次派齐六名读图员。1.13 分钟二层平面读图员遭遇 HTTP 429（服务码 1302）；南立面和一层平面读图员随后各一次 view_image 漏填文件名，工具拒绝。首错均发生在读图初期，尚未到 G1 装配修复的验证阶段。
- 观察UTC 2026-10-08T15:45:01.063077+00:00，最新事件 event-000515（事件时间6.98分）：南立面在 3.66 分钟 submit_elevation_reading 返回 accepted，3.91 分钟正常结束，是首个成功读图交付。前两次空文件名错误已由 work model 后续补齐；二层平面与西立面遇到的可重试服务错误后仍继续运行。
- 观察UTC 2026-10-08T15:48:41.795189+00:00，最新事件 event-000567（事件时间9.86分）：四名立面读图员均已实际提交 accepted：南 3.66、北 5.48、西 5.70、东 6.75 分钟。北立面首次提交在 5.16 分钟被 z_calibration 像素起止顺序拒绝，20 秒后自行修正。四个角色都正常 completed；此状态仅证明格式与提交成功，准确性仍需独立评价。
- 观察UTC 2026-10-08T15:55:32.477033+00:00，最新事件 event-000609（事件时间13.75分）：13.8 分钟尚无首次试建。一层平面累计约 31,165 output tokens、12.1 model 分钟；二层约 26,829 tokens、7 次像素剖面。分块查看已使用，但尚不能判定其减少首稿前探索或后续返工；需将首稿前长请求投入与试建错误和最终质量对应。observe_run.py 的 tool_errors 未识别本轮 outcome=failed/isError，不能使用其零错误统计。
- 观察UTC 2026-10-08T15:56:50.985972+00:00，最新事件 event-000609（事件时间13.75分）：定向核对实际发出的请求体：plan_f1 event-000609、plan_f2 event-000583 均为 glm-5.3-flash、max_tokens=32000、thinking.type=adaptive、output_config.effort=medium、stream=false。provider_report 未报告实际应用参数，故 medium 仅证实请求已发送，不宣称服务端执行效果已验证。当前无事件阶段是等待非流式 model_response，而非工具卡住。
- 观察UTC 2026-10-08T15:57:52.466158+00:00，最新事件 event-000621（事件时间19.44分）：旧 v52 原始 events 仍在本地，已直接对照首轮平面读图员、未解压归档。旧一层首次试建 14.85 分钟，首稿前 5 请求/43,207 output tokens，最长请求 395.7 秒/23,758 tokens；旧二层 15.15 分钟，11 请求/41,433 tokens，最长 190.2 秒/12,761 tokens。本轮一层截至 19.41 分钟已 8 请求/47,955 tokens，仍未首次试建；最长两次分别 373.1 秒/16,624 tokens、339.4 秒/16,790 tokens。不能归因版本改动，先看首稿和后续返工是否获得收益。
- 观察UTC 2026-10-08T16:05:32.199370+00:00，最新事件 event-000679（事件时间26.52分）：24.47 分钟一层首次试建返回 15 个 plan_format 问题：自造 source_refs_extra/printed_segments_mm 字段、漏 assumptions/unresolved、conference/meeting 非正式类型码。work model 查类型表后在 25.52 分钟第二次试建，仅余 tick_pixels 数量须比 segments_mm 多一项。26.48 分钟第三次试建 outcome=unknown、结果未捕获；676 原文 interrupted after durable intent，677 状态核查 inconclusive，678 以 unknown_write_outcome 停止该角色。首稿前长输出尚未换来格式一次通过。二层 25.09 分钟返回恰为 32,000 tokens，649 明确 response_truncation/length，0 tool calls；单请求 779.6 秒，runtime 丢弃截断输出并发 652 请求精简续写，未把截断算作已完成任务。
- 观察UTC 2026-10-08T16:14:34.995277+00:00，最新事件 event-000686（事件时间34.84分）：主助手转交另一独立 dev model 的纯函数重放结论：一层第三次试建的 unknown 源于 domain/kernel 的 _snap_footprint。依次移动轮廓边时，前边更新使邻边临时斜化，_segments 不再返回该边，next 查原 index 抛 StopIteration。该诊断在运行外进行，未改本次冻结版本或给 work model 提示；证据将保存 unknown_write_investigation.md。runtime 当前只留 unknown 未保存异常类型；应区分这个 domain 异常与前两次 work model 格式错误。
- 观察UTC 2026-10-08T16:28:44.391565+00:00，最新事件 event-000785（事件时间48.99分）：47.45 分钟二层连续第三次 length 截断，runtime 以 incomplete_response 停止；虽然响应出现一个 tool_call，但未执行截断调用。47.50 分钟原 delegate_readers 结束，调度员至此才一起收到一层 unknown 与二层 incomplete。703 重派 plan_f1b/plan_f2b，引用 previous_task_id，issues 仅复述状态并要求完整交付，未形成具体纠错方案。两个角色约 48.1 分钟启动，重新看原图与分块，均又一次 view_image 漏文件名。无成功平面稿、尚无装配，故 G1 装配修复效果仍未测到。
- 观察UTC 2026-10-08T16:34:32.118894+00:00，最新事件 event-000871（事件时间55.90分）：待检验假设：截至约 56 分钟，所有平面角色中仅首轮一层在 24.61 分钟、首次试建15个格式错误之后主动 get_bim_reference(topic=room_types)；二层及两名重派角色未主动查询 reference/guide 工具。room_types 是用途编码表，并非完整 plan 格式；角色 guide/tool schema 自动随 runtime 提供，因此不能表述为完全没读格式。与 Sonnet 标杆先查参考后写完整稿的顺序不同，后续可检验首稿负担/格式提供方式；尚不能断言此差异导致长输出或截断。第二次仅余1个格式问题，但同时修了逐项工具反馈，改善不可单归因查询参考。
- 观察UTC 2026-10-08T16:48:37.253716+00:00，最新事件 event-001009（事件时间69.69分）：约 67 分钟、第二轮派工后约 19 分钟，F1b/F2b 仍无 trial 或平面提交，分别累计 9/8 次 pixel_profile。重新探索未形成可编译稿；截至该时点未重复 kernel 异常或截断终止，不能把等待模型响应直接判作重复故障。
- 观察UTC 2026-10-08T16:50:47.818796+00:00，最新事件 event-001024（事件时间71.04分）：独立质量复核已保存 independent_quality_notes.md，并回读其边界：首轮一层 trial_003 是未编译声明，已发现会议室东墙延长穿走廊并将东入口声明为独立房间、西南外门错为水平内部门，以及原始门位置明显偏差。它不是源 BIM/交付评分，也不能预测对齐器之后最终几何；说明首稿前长输出尚未保证语义正确。domain/kernel 异常与 work model 读图误解是两个独立问题，修复前者不等于恢复后者。
- 观察UTC 2026-10-08T16:55:13.935642+00:00，最新事件 event-001113（事件时间76.12分）：第二轮 F2b 73.35 分钟首次试建返回13个格式错误（再次使用 printed_segments_mm、漏 unresolved）；74.62 分钟第二试余3个 tick数量问题；74.94 分钟未有有效草稿却尝试局部修改，被 No editable plan yet 拒绝；76.04 分钟完整稿进入几何编译，P-corr-north 被判在 footprint 外。此轮已有新几何反馈，未重复截断终止。另存待检验假设：guidance.py:50 / readers.py:470 描述为 printed segments_mm，严格 schema 只接受 segments_mm；两角色都生成 printed_segments_mm，措辞可能诱发混写，尚非已证因果。
- 观察UTC 2026-10-08T17:05:55.207122+00:00，最新事件 event-001205（事件时间86.00分）：F1b 81.97 分钟首次试建14个格式问题均来自7条 printed_segments_mm；83.43 分钟第二试格式问题消失，转为悬线，工具逐项给 junction_repairs 原图坐标。F2b 82.25 分钟格式错为两开口漏 source_refs，83.97 分钟纠正后又暴露 footprint 第2边在 [928.6,521.7] 退化。反馈确实改变了错误层级，但仍无可用平面候选。
- 观察UTC 2026-10-08T17:14:39.949668+00:00，最新事件 event-001323（事件时间95.93分）：第二轮继续沿工具反馈推进：F1b 91.27 分钟悬线已缩到 p_strip_w 一段（距最近墙约44.2px），93.67 分钟以 root_time_budget_exhausted 停止，整案尚未到180分钟且主助手未手动停止；预算归因由独立 dev 另查，不能假设再给时间必成功。F2b 94.23 分钟转为 corridor/hall 种子占同空间，95.82 分钟再转为窗 W-top-1.z=[1,2.4] 超出楼层 [4,7.6]；这些表明反馈改变了状态，但无成功候选，不代表源 BIM 已通过。

最终审计UTC：2026-10-08T17:27:31.207512+00:00。完整逐事件参数、定向业务返回、异常分类和时间记录见 [independent_behavior_summary.json](independent_behavior_summary.json)。
