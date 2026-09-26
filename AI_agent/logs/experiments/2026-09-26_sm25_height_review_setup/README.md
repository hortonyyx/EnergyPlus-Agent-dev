# sm25 原图查看提醒与逐层高度核验

本轮按用户要求由Astra单独继续还原，无开发子代理、无Opus/部分推理工作包。

生产增量在`Toolkit.input_view_status()`：从本次`view_image`成功记录统计与输入hash绑定的整图/局部返回，在inputs、建模、开口检查、交付中提示。仅统计该工具；其他图像工具、局部模型、前次运行及无hash旧记录不在范围内。没有记录不等于没有通过其他手段观察，返回整图也不等于已审视全图。不建硬阻断或自动推断立面/楼层映射。现有高度绑定检查保持原语义，不把看图当高度已核验。

新增2个回归检查并与高度状态/输入相关检查合跑22项通过；源立面、交付、中断保存等另4项通过，共26项不同检查。普通测试离线，无新增依赖。

1. `python -m AI_agent.logs.experiments.2026-09-26_sm25_height_review_setup.run_review`：run52，仅六原图+run51草稿，限定外开口高度复核，没有具体错误提示。[实际结果](../2026-09-26_sm25_height_review_claude_run52/README.md)。
2. `python -m AI_agent.logs.experiments.2026-09-26_sm25_height_review_setup.run_cold`：run53，取消旧稿，仅六原图；继承run51通用任务，加直接看图/逐层高度绑定提醒，禁止局部模型委派。独立运行，不继承run52答案。工具变化和任务指引同时存在，不作单因果归因。
3. 对应`audit_review`/`audit_cold`在模型退出后读取GT，并复用上轮确定性组合/源/GT开口诊断；禁止回送给生成。`browser_check.py`复用已有`/tmp/ep-bim-browser-qa`环境，离线核源hash、逐层切换、旋转与交付检查。

生产源码在两次实跑之间不变，均为`cfc33ab1`。原失败run51及成功续修run52分别保留，[run53结果](../2026-09-26_sm25_height_cold_claude_run53/README.md)不覆盖既有失败/辅助范围。

run53的最终回执暴露工具摘要过长问题，之后修复按缩进JSON计预算，保留覆盖/未决/失败状态，完整报告照常保存。16项当前检查通过，与先前7项重叠，共35项不同检查。`replay_delivery_transport.py`对两个run临时副本的真实MCP返回重放均通过，原产物不变；不代表原模型已收到修复后输出。原运行hash核对必须用`cfc33ab1`，修复后摘要为单独诊断文件。完整结果与下一入口见[本轮交接](../../worklog/2026-09-26_reconstruction_height_review.md)。
