# 架构与实现边界

这里区分已核对的代码事实和下一阶段建议，不承担任务排期。

| 现行文档 | 范围 |
|---|---|
| [阶段与入口](pipeline_stage_contracts.md) | 当前实际调用链、产物与函数入口差异 |
| [图纸观测与校正](reading_pipeline_architecture.md) | reading 前置、as-drawn 接线与证据处理 |
| [坐标与几何](coordinates_and_geometry.md) | 源几何、派生面、容差与两路共用边界 |
| [评测与证据](evidence_and_evaluation.md) | GT 隔离、运行/评分区别、成绩条件 |
| [版本与验证记录](harness_versioning.md) | 用提交、配置和实际产物标识可复查结果 |
| [两路输入融合](multimodal_bim.md) | 下一阶段设计建议，尚未形成统一实现 |

旧 flow_map、as_drawn_layer_contract、GT ledger、judge_grade_model 仅保留历史跳转；详细旧稿已逐份归档，不能按文件名推断是当前契约。
代码事实核对见 [管线审计](../logs/experiments/2026-09-08_management_audit/pipeline.md)。
