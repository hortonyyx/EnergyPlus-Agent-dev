# 冻结工具的原图整案验证

本目录只保存实验编排与事后核验，不向生成模型提供旧候选、历史观察、正确空间/门数、局部坐标或 GT。

- `run_cold.py`：sm24 五张原图、通用还原目标，Sonnet 订阅、medium、600 秒、新会话、无 seed；是否调用局部 Haiku 由父模型选择。输出独立 `2026-09-14_bim_agent_sm24_run13`。
- `run_with_plan_feedback.py`：相同原图/目标/预算与模型配置，使用新增自动源平面反馈的实现，输出独立 run14；没有继承run13候选或失败定位。冻结清单为 `frozen_with_plan_inputs.json`。
- `frozen_inputs.json`：开跑前的原图、通用目标与代码散列；结束时检查冻结文件未变，并在 run 中保存逐文件实现快照。
- `verify_execution.py RUN`：等 `summary.json` 后，核原图裁剪/缩放/网格、实际返回源图和衍生图的像素；若有局部调用，核选图隔离与原文回传。保存实际工具错误，不以成功返回或自述证明读图正确。
- `summarize_run.py RUN`：汇总实际调用、耗时、CLI估算与工具时间线；父耗时含等待子调用，不把两者叠加成端到端耗时。
- `audit_source.py RUN`：逐候选重放操作和完整源导出，并在 `post_run_inspection/` 另存开发侧源图/原图回叠；仅生成完成后执行，这些图不计生成时反馈。

生成完成后才能运行评测侧 `2026-09-12_sm24_delegation_setup/evaluate.py --run RUN`。没有保存候选时不伪造可查看交付或 GT 成绩。图像运输核验可以在无候选的完成运行上执行。

辅助恢复基点 `2026-09-14_bim_agent_sm24_run12` 保留。新整案结果必须独立核对后才决定是否采用。
