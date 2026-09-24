# sm24 原平面冷启动：冻结完整墙段反馈方法

本轮取消run36的旧失败声明，只给未修改的`1f_view.png`。生产实现逐文件哈希与run36一致；任务范围、1800秒预算与run32原冷启动一致。工作模型仍为现有GLM订阅`glm-5.3-flash`、medium，不提供建筑声明、立面、旧候选、旧观察、正确数量/坐标或GT，不在运行中追加定位提示。

目标是完整实体分隔、平面开口和真实门连接。标定也由模型自己建立；未给出的竖向高度必须保留为假设。这是单次有界原图冷启动，不是多层/高度完整验收或重复稳定性证明。相对run32的工具/指导改动是一个组合，不作单工具因果归因。

运行入口（目标目录已存在时拒绝覆盖）：

```bash
python -m AI_agent.logs.experiments.2026-09-24_sm24_cold_context_setup.run_cold
```

生成结束后才运行独立评价：

```bash
python -m AI_agent.logs.experiments.2026-09-24_sm24_cold_context_setup.audit_cold --run AI_agent/logs/experiments/2026-09-24_sm24_cold_context_glm_run37
```

评价复用run32生成前独立冻结的原图空间/开口观察和容差，以及未经修改的GT。保存原始坐标评分；另按实际生成声明的标定严格反解，再映到独立原图框架作诊断，不拟合、不改模型、不替代原始评分。重放源/显示、核对原图/运行实现哈希、真实图像运输及局部回叠；浏览器WebGL交互不在本次审计范围。生产代码未改，同范围51项既有离线检查沿用。

实跑结果与限制见[本轮工作记录](../../worklog/2026-09-24_reconstruction_cold_context.md)。

run37正常完成但分区未通过：多造走廊隔墙，9空间，19/21开口宿主及8/10门连接匹配。开发侧生成后用`diagnose_wall.py`另建[全段/空白回放](postrun_tool_replay/diagnosis.json)，未向模型回注，也未修改原候选。该脚本需在新回放目录运行，已有目录时拒绝覆盖。
