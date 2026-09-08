# 图纸路线：reading 与 correction

这是图纸输入的简要分工说明，不再是“本批所有工作必须先完成”的施工总令。
原 1304 行指南保存在 [接手前版本](../archive/2026-09-08_pre_takeover/guides/reading_correction_split_guide.md)。

## 保留的分工

- reading 记录图上可见证据、标注及模型识别；原始引用与解释分开保留。
- correction 整合证据、处理冲突与缺失，得到供几何内核消费的结构。
- 确定性代码计算坐标、墙线、闭合区域、拉伸、配对和序列化。
- GT 是评测输入，不进入被评测的 reading/correction 生产链。
- 用已有观测重放调试可以推进工程，但与冷启动识图、正式评分分开报告。

## 当前已有路径

`run_stage.py` 按输入契约分派 legacy / as-drawn。as-drawn 已接入多层证据校正、楼层协调、补窗和最终校正产物归档。
实现见 [pipeline.py](../../src/agent/pipeline.py)、[correction](../../src/agent/correction/)、[CLI](../../scripts/tool_scripts/run_stage.py)。
注意 `flow` 的 reading 阶段只检查已生成观测，尚不负责从原图自动生成；case 状态见 [当前计划](../plan.md)，完整实现边界见 [图纸架构](../architecture/reading_pipeline_architecture.md)。

## 向混合入口演进

现有 as-drawn 类型是图纸适配的实现资产，不要求外部体量或 CAD 伪装成同一种图纸观测。
各适配器保留原始信息，共享下游模型、坐标和质量说明。未知内部格局可用推断分区，明确它不是实测房间。
信息不足应触发可解释的简化或局部输出；当前代码尚未普遍支持这一点，需要后续开发。

GT 精修、审阅债、模型降档或扩充测试矩阵都不是这条路线重新开工的先决条件。
