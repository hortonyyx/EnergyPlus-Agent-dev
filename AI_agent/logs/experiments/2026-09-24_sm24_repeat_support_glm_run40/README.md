# sm24 同方法独立冷启动 run40

逐字复用run39 scope、相同原平面与生产实现，新GLM订阅session独立生成；实际glm-5.3-flash、medium、1135.59秒，无旧稿/标定/答案/GT/中途干预。输入方法见[设置](../2026-09-24_sm24_repeat_support_setup/README.md)，完整结果与用户验收口径见[工作记录](../../worklog/2026-09-24_reconstruction_repeat_support.md)。

首份墙网直接生成8空间/11窗/10门/10连接，完整路径复核后无改形。独立原图8/8空间对应、21/21宿主、10/10门连接；连续走廊、东北分隔和东南折墙保持。原始数值仍有1 minor/7 severe边界项、最大14.30cm，门窗位置17/21；声明框架诊断18/21，分区仍severe。两次主要空间关系重复成立，尚非跨案例稳定或毫米准确度证明。

无立面，层高3m/门高2.1m/窗0.9–2.4m是假设；无资料的内部门高度按用户明确要求不作为验收阻塞。原始GT三维severe保留为诊断，不要求单张平面提供不存在的信息。

- [查看模型](candidate_01/viewer.html) / [源平面](candidate_01/plan_F1.png) / [独立叠合](evaluation/independent_original_overlay.png)
- [冷启动核验](evaluation/cold_start_audit.json) / [原始评价](postrun_audit.json) / [两次完整比较](../2026-09-24_sm24_repeat_support_setup/repeat_comparison.json)
- [实际观察/交付轨迹](evaluation/observation_and_edit_trace.json) / [路径支持](plan_wall_support/support_001.json)
- [19图运输](transport_audit.json) / [3张反馈RGB对应](evaluation/actual_feedback_images.json) / [无损归档](stream_archive.json)

源/显示精确重放及输入/运行哈希通过，viewer无远程脚本；未做浏览器WebGL验收。CLI估算$1.7165288非订阅账单。模型自评在agent_receipt.json，独立评价与其分开。
