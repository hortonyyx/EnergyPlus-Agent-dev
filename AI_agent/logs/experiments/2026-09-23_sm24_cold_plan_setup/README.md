# sm24 单层冷启动换例

沿用sm21/run31相同提示、生产实现和1800秒预算，仅替换为sm24原始`1f_view.png`。工作模型仍为现有订阅`glm-5.3-flash`、medium；不提供立面、建筑声明、旧模型、旧观察或GT。不提示具体错处、正确数量或坐标。未提供的高度须明确假设。

运行：`python -m AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.run_glm`。独立run32不覆盖旧产物。实际run32的实现基点为`81ec359c`，当时生产代码与sm21/run31一致；脚本调用当前工作树，若复现实验旧方法须使用该基点，并改为新的输出目录。后续空筛选增量不属于run32生成时实现。

`original_observations.json`和`developer_original_review/`仅用于独立评测，未送给GLM。首次候选生成前，开发直接从原图标注/像素/局部裁图建立尺度、完整房间轮廓和门窗清单；不从旧BIM或GT复制几何。门窗容差沿用sm21；完整原图空间对照使用8cm边界容差，约等于本图三个像素，单独报告误差和错分/错并。GT仍在生成结束后读取，维持原始坐标和原有评分阈值。

生成结束后执行：

```
python -m AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.audit_run --run AI_agent/logs/experiments/2026-09-23_sm24_cold_plan_glm_run32
python -m AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run --run AI_agent/logs/experiments/2026-09-23_sm24_cold_plan_glm_run32
```

首个脚本核源/显示精确重放、图像/代码哈希、原图轮廓及门窗宿主/连接，再做独立GT诊断；第二个核原始流中的实际图像与保存产物，并无损压缩原始流。原图手工判读不是自动语义judge，平面结果不能证明未输入的高度或整栋建模通过。


结果：run32冷启动未通过，见[完整记录](../../worklog/2026-09-23_reconstruction_sm24_cold_plan.md)。`runtime_snapshot/`保存当时实现，后续审核从快照核运行哈希，重放仍用当前几何代码且要求完全一致。`diagnose_declared_frame.py`另输出根据申报锚点换算的诊断，隔离上下翻转对原始评分的影响；不修改原候选或评分。

`run_probe.py`是工具增量后的run33只读GLM探测，600秒上限。开发指定局部区域和需要复现的白色空筛选，原图之外不送旧模型、GT、正确颜色或墙端点；因此只检验新反馈能否被使用，不能算自主选题/整案还原成绩。两次运行均显式走GLM现有订阅，无模型回退。
