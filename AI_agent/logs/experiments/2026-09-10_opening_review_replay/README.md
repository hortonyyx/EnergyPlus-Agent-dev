# 开口清单回查的旧观察重放

本目录复用 run03 评测侧开发助手原图观察，检查 run04/05 已保存的实际源模型；不是新读图，也不是自动保真验收。观察不交给 run06 冷启动模型。尺寸框只用于标记区别，不是门端点量测；西侧双扇外门按同一连接合成一处开口。

预期：run04 留下的一层两个额外门应未被任何观察对应；run05 应与这份观察一致。`drawing_fidelity` 必须仍为 `not_evaluated`。实际执行结果见结果文件与本轮交接。

实际离线结果：`before.json` 准确指出 `D_F1_N2_Cb`、`D_F1_S2_Cb` 未被观察对应；`after.json` 无对应差异，结论为 consistent_with_supplied_observations。两者 drawing_fidelity 均为 not_evaluated。观察质量来自此前开发助手原图复核，不能把这次重放记成自动识图能力。

运行：`python AI_agent/logs/experiments/2026-09-10_opening_review_replay/diagnose.py`。代码提交 `25e9e6a5`；相关模块 11 项、真实 stdio/恢复边界 4 项离线测试通过。
