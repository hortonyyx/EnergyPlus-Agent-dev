# 冻结全路径支持方法后的sm24原图冷启动

run39只给一张未修改的原平面，不提供旧声明、标定、成功候选、局部诊断、建筑JSON、立面或GT。生产实现逐文件哈希与run38相同；工作模型GLM订阅`glm-5.3-flash`、medium。沿用run32/run37冷启动范围和1800秒预算，追加通用方法指示：首稿后用`view_plan_wall_support`查完整路径，再依据未标记原图、合适量测及两侧空间作判断；缺墨不能自动删墙或造门。

这是单次原图冷启动，非重复稳定性/多层/高度验收；新增工具、通用指导和显式工具使用提示共同变化，不作单工具因果对照。未给出的竖向高度须明确假设，生成中不追加开发定位提示。

```bash
python -m AI_agent.logs.experiments.2026-09-24_sm24_cold_support_setup.run_cold
python -m AI_agent.logs.experiments.2026-09-24_sm24_cold_support_setup.audit_cold --run AI_agent/logs/experiments/2026-09-24_sm24_cold_support_glm_run39
python -m AI_agent.logs.experiments.2026-09-24_sm24_cold_support_setup.summarize_trajectory
```

目标run目录存在时拒绝覆盖。独立核验在生成结束后运行，复用run32冻结的原图观察/容差和原始GT；原图平面、GT三维及严格反解声明标定的诊断分别保存，不拟合、不改候选。源/显示重放、图像运输与流无损归档均复用既有脚本。

生产代码未改，沿用同代码35项离线有效结果；本轮不重复pytest全量。新运行/核验脚本做语法检查。结果见[本轮记录](../../worklog/2026-09-24_reconstruction_cold_support.md)。

运行已结束：8空间/21开口/10连接，主要空间关系正确，严格原图分区仍severe；原始位置14/21、声明框架诊断20/21，宿主21/21、门连接10/10。详见[run39](../2026-09-24_sm24_cold_support_glm_run39/README.md)。
