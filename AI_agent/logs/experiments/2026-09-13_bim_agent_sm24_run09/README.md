# sm24 东北两房局部恢复：未修改，错误自证

[交付页（仍为旧seed）](delivery.html) · [源差异](source_audit.json) · [独立执行审计](execution_audit.json)

继续使用run07/candidate_01，未采用run08错门；输入五张原图，只限定东北小房间、大会议室的共墙与走廊门，不给正确坐标。Sonnet low实际222.43秒结束并选择seed，**无新候选、无物理改动，未取得分区或门的改善。**

模型最终声称已登记原图标定、局部墙和两门均得到像素支持，但实际工具记录没有overlay_candidate、map_pixels、map_dimension_chain或保存标定。交付JSON明确current_source_projections为空，F1无登记视图。“Registered frame”的自述不成立。

它把原图约y295的北部接待区横墙当作东北小房间与会议室共墙；实际目标横墙更南。它自报的y标定约67.5→20m、867.5→0m不是实际整栋外墙端点，不能用这组坐标自证旧墙正确。两扇走廊门只用宽泛像素范围和共墙归属说明，未逐洞口比较位置；一个长共墙能容纳门不证明门位正确。原自述原样保留，开发不采信其verified/corroborated结论。

源差异核验确认房间、门窗、连接和物理几何完全保留。独立分区复用run08/evaluation/seed_partition.json及run07有效结果：同一源空间、同评价代码，仍severe，不重跑相同分区全量。离线交付页JSON/链接及嵌入源显示检查见browser_check；仅检查显示，不证实图意。

CLI估算$0.7494561，非账单。没有显式低档子观察；实际模型/辅助CLI用量见agent_receipt与execution_audit。此轮比run08范围更窄且思考档位不同，不作单变量降本结论。

执行入口：[run_northeast.py](../2026-09-13_east_partition_setup/run_northeast.py)。恢复基点继续run07，后续一次隔离Haiku原图完整轮廓观察不读取本轮seed/自评，以核查旧候选影响与局部量测到实际几何的对应。
