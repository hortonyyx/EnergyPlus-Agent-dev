# BIM 节点质量记录

逐次列出保存结果；不自动判定验收、稳定性或回退根因。缺失证据保留未知。

| 案例 / 条件 | 运行 | 模式 / 完成状态 | 空间 / 门窗 / 连接 | 原图位置 / 宿主 / 连接 | 严格分区 | 新功能使用 |
| --- | --- | --- | --- | --- | --- | --- |
| sm25 / 旧整案基线 | 2026-09-26_sm25_height_cold_claude_run53 | cold / completed | 29/61/30 | 61/61；宿主61；连接30 | severe | 未单列 |
| sm25 / 旧整案基线 | 2026-09-26_sm25_height_repeat_claude_run54 | cold / completed | 29/61/30 | 53/61；宿主61；连接30 | severe | 未单列 |
| sm24 / 旧整案基线 | 2026-09-26_sm24_whole_building_claude_run55 | cold / completed | 8/21/10 | 20/21；宿主21；连接10 | severe | 未单列 |
| sm24 / 旧整案基线 | 2026-09-26_sm24_whole_building_repeat_claude_run56 | cold / completed | 8/21/10 | 21/21；宿主21；连接10 | severe | 未单列 |
| sm21 / 旧整案基线 | 2026-09-26_sm21_whole_building_claude_run57 | cold / completed | 14/29/14 | 29/29；宿主29；连接14 | minor | 未单列 |
| sm21 / 旧整案基线 | 2026-09-27_sm21_whole_building_repeat_claude_run58 | cold / completed | 14/29/14 | 29/29；宿主29；连接14 | minor | 未单列 |
| sm24 / 用途保存 | 2026-09-27_sm24_room_types_claude_run59 | cold / completed | 8/21/10 | 21/21；宿主21；连接10 | severe | 未单列 |
| sm24 / 用途首轮指引 | 2026-09-27_sm24_room_types_cold_claude_run61 | cold / completed | 8/21/10 | 17/21；宿主21；连接10 | severe | 未单列 |
| sm24 / 用途缺项反馈 | 2026-09-27_sm24_room_types_feedback_claude_run62 | cold / completed | 8/21/10 | 15/21；宿主21；连接10 | severe | 未单列 |
| sm21 / 视图引用及续查 | 2026-09-27_sm21_current_tools_claude_run69 | cold / completed | 14/29/14 | 11/29；宿主29；连接14 | severe | 未单列 |
| sm21 / 候选额度旧稿恢复 | 2026-09-27_sm21_candidate_budget_claude_run70 | recovery / completed | 14/29/14 | 11/29；宿主29；连接14 | severe | 未单列 |
| sm21 / 当前指引对照 | 2026-09-27_sm21_guidance_control_run71 | cold / completed | 14/29/14 | 25/29；宿主29；连接14 | severe | 未单列 |
| sm21 / 精简指引对照 | 2026-09-27_sm21_guidance_ablation_run72 | cold / completed | 14/28/13 | 0/29；宿主2；连接0 | severe | 未单列 |
| sm21 / 旧profile反馈对照 | 2026-09-27_sm21_profile_legacy_run73 | cold / completed | 14/29/14 | 20/29；宿主29；连接14 | severe | 未单列 |
| sm21 / 新profile反馈对照 | 2026-09-27_sm21_profile_current_run74 | cold / completed | 14/29/14 | 4/29；宿主29；连接14 | severe | unexercised (0) |
| sm21 / 用途提醒组织修订前 | 2026-09-27_sm21_use_guidance_before_run75 | cold / completed | 10/28/14 | 26/29；宿主28；连接14 | severe | exercised (7) |
| sm21 / 用途提醒组织修订后 | 2026-09-27_sm21_use_guidance_after_run76 | cold / interrupted | 未知 | 未知 | 未知 | 未单列 |
| sm24 / 用途提醒组织修订前 | 2026-09-27_sm24_use_guidance_before_run77 | cold / interrupted | 未知 | 未知 | 未知 | 未单列 |
| sm24 / 用途提醒组织修订后 | 2026-09-27_sm24_use_guidance_after_run78 | cold / interrupted | 未知 | 未知 | 未知 | 未单列 |
| sm21 / 阈值遗漏反馈修订前 | 2026-09-28_sm21_threshold_legacy_run79 | cold / completed | 14/29/14 | 22/29；宿主29；连接14 | severe | unexercised (0) |
| sm21 / 阈值遗漏反馈修订后 | 2026-09-28_sm21_threshold_current_run80 | cold / completed | 14/29/14 | 24/29；宿主29；连接14 | severe | exercised (3) |
| sm21 / 完整旧树复跑 | 2026-09-28_sm21_historical_tree_run81 | cold / completed | 14/29/14 | 28/29；宿主29；连接14 | severe | 未单列 |

严格分区、位置、宿主和连通分别解读；宽容差高度匹配不代替逐窗语义复核。

- sm25 / 旧整案基线：2 次；不合并统计；条件差异 ['implementation_sha256']，另见证据缺项/参照范围。不据此宣称稳定。
- sm24 / 旧整案基线：2 次；已列同条件位置通过数范围 [20, 21]。不据此宣称稳定。
- sm21 / 旧整案基线：2 次；已列同条件位置通过数范围 [29, 29]。不据此宣称稳定。

- 2026-09-26_sm25_height_cold_claude_run53: 27内门高度仍是假设，旧全局备注保留。
- 2026-09-26_sm25_height_repeat_claude_run54: 8处位置超既有容差；其中7内门随隔墙约8.30cm偏移，仅比8cm阈值多约3mm。宿主/连接正确，不能一律作重大拓扑退步。
- 2026-09-26_sm24_whole_building_claude_run55: 严格GT分区severe，独立原图分区minor；一处位置误差约11cm。7内门高假设。
- 2026-09-26_sm24_whole_building_repeat_claude_run56: 严格GT分区severe，独立原图分区minor；7内门高假设。
- 2026-09-26_sm21_whole_building_claude_run57: 12内门高假设；旧基线的已知限制仍保留。
- 2026-09-27_sm21_whole_building_repeat_claude_run58: 15窗图像高度确认，2外门暂缓，12内门高假设；不能称全部自主核完。
- 2026-09-27_sm24_room_types_claude_run59: 用途保存改动后原图位置仍21/21；单次结果不证明该改动长期无影响。
- 2026-09-27_sm24_room_types_cold_claude_run61: 尚未完成用途自主复核，原图位置17/21。
- 2026-09-27_sm24_room_types_feedback_claude_run62: 新增反馈实际送达，模型仍结束；原图位置15/21。
- 2026-09-27_sm21_current_tools_claude_run69: 先核初稿标定与尺寸段对应，不以末尾续查解释首稿错误。
- 2026-09-27_sm21_candidate_budget_claude_run70: 使用run69旧稿恢复，不能作为新的冷启动样本。
- 2026-09-27_sm21_guidance_control_run71: 小窗和东窗高度家族仍有差异，宽容差统计不等于逐窗语义正确。
- 2026-09-27_sm21_guidance_ablation_run72: 原始米字段误填毫米；保留原始0/29结果，不用事后缩放诊断代替生成成绩，且实际漏一门。
- 2026-09-27_sm21_profile_legacy_run73: 南小窗1.5..2.4m，应1.5..2.1m；原高度容差0.3m恰接受该误读。二层墙约2.2–2.7cm偏移触发严格severe，另有内门做宽。
- 2026-09-27_sm21_profile_current_run74: 新增profile反馈未实际送达；不能据此判补丁有益/有害。一层小窗及东窗被套用普通窗高，仍有明显隔墙偏移。
- 2026-09-27_sm21_use_guidance_before_run75: 每条件一次，仅作跨例筛查；用途反馈计数是可解析回执下界，不代表正确理解或因果收益。
- 2026-09-27_sm21_use_guidance_before_run75: 正常结束但F1南北各三房错并，漏小窗；原位置26/29不代表整案通过。
- 2026-09-27_sm21_use_guidance_before_run75: 原宿主28/连接14因种子映射允许错并而偏乐观；要求房间身份独立后的补充统计16/7，见semantic_review.json。
- 2026-09-27_sm21_use_guidance_after_run76: 每条件一次，仅作跨例筛查；用途反馈计数是可解析回执下界，不代表正确理解或因果收益。
- 2026-09-27_sm21_use_guidance_after_run76: 429中断；最新候选为系统保留稿，未获模型最终选定，不计作修改后完整成绩。
- 2026-09-27_sm21_use_guidance_after_run76: 保存稿另行诊断14空间/27门窗，位置22/29，漏两东窗，详见saved_candidate_audit.json；汇总质量保持未知。
- 2026-09-27_sm21_use_guidance_after_run76: Audit candidate does not match the final selected delivery
- 2026-09-27_sm24_use_guidance_before_run77: 每条件一次，仅作跨例筛查；用途反馈计数是可解析回执下界，不代表正确理解或因果收益。
- 2026-09-27_sm24_use_guidance_before_run77: 启动即429，0输入/输出token、无工具调用或候选；实际模型未发生推理，receipt型号是通道路由记录。
- 2026-09-27_sm24_use_guidance_before_run77: Audit candidate does not match the final selected delivery
- 2026-09-27_sm24_use_guidance_after_run78: 每条件一次，仅作跨例筛查；用途反馈计数是可解析回执下界，不代表正确理解或因果收益。
- 2026-09-27_sm24_use_guidance_after_run78: 启动即429，0输入/输出token、无工具调用或候选；实际模型未发生推理，receipt型号是通道路由记录。
- 2026-09-27_sm24_use_guidance_after_run78: Audit candidate does not match the final selected delivery
- 2026-09-28_sm21_threshold_legacy_run79: 14空间一一对应，29宿主/14连接，无错拆错并；严格墙位差异仍保留。
- 2026-09-28_sm21_threshold_legacy_run79: 原图位置22/29；首层南小窗和东窗高度族错误，后者在旧GT容差内。14用途已填写；旧反馈27份实际回执。
- 2026-09-28_sm21_threshold_current_run80: 14空间一一对应，29宿主/14连接，无错拆错并；严格墙位差异仍保留。
- 2026-09-28_sm21_threshold_current_run80: 原图位置24/29；F1七窗高度错，14用途未知。新增反馈送达3次，均为绿色尺寸线扫描，不认证细墙误读修复；另1次错误图片名调用单列。
- 2026-09-28_sm21_historical_tree_run81: 468d83f7原生成代码、36工具/6保存上限/完整任务与run58一致；1次独立旧树生成，外部服务及历史依赖环境不冻结。
- 2026-09-28_sm21_historical_tree_run81: 14空间无错拆错并，位置28/29、宿主29/连接14；F2东窗只画约半宽，F1南小窗套错窗高；没有复现旧完整成功。
- 2026-09-28_sm21_historical_tree_run81: 121次工具调用/17次错误，4过程版本、余约2010秒结束。7/29高度图像绑定，22项未核对；不以旧树位置较好判定全部新开发有害。
