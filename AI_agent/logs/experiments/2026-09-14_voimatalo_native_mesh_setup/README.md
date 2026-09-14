# Voimatalo 原始网格输入实验准备

本次继续已获授权的Voimatalo探索，用户告知Claude已恢复并要求推进后收工。一次Claude订阅Opus medium，1800秒上限；实际用量/退出状态以运行回执为准，不切换付费通道。

输入为此前已裁出的目标单体原始GLB和用途/层数/简化意图声明。保留既有单体选择辅助，但不提供旧14张截图、15度对齐、立面三角面筛选/范围、旧BIM或GT。工作模型通过harness内部查询网格、选择视角和量测。声明中的缺失项是输入范围，不是正确布局答案。

command.json保存完整参数；本目录的开发预检视图只用于确认工具是否忠实渲染，不进入模型输入。普通PNG输入仍可同时提供，此次不提供。模型能调用工具不等于能正确判读或生成；通过实际轨迹和源产物评价。

本程已完成[原资产整案](../2026-09-14_voimatalo_native_mesh_run01/README.md)与[修复后局部观察](../2026-09-14_voimatalo_native_alignment_run01/README.md)。后者由run_alignment_probe.py启动Sonnet只读观察，不是再次整栋生成；模型/任务/工具均有变化，不作受控消融。

初整案发现局部画幅拉伸后，view_mesh已改成等米制像素并返回点对朝向。audit_run.py在各自运行完成、后续代码修复前执行，核冻结代码、真实运输、逐图/逐点与源重放；报告原样保留。diagnose_observations.py和diagnose_alignment_points.py是事后检查，不回注运行。package_result.py/package_overlay.py/check_overlay.py与既有浏览器检查生成实际查看证据；后者叠合严格使用模型声明角度。replay_delivery_reply.py仅离线重放大交付截断问题，不调用模型。
