# 当前代码链与接口

2026-09-08 按整合代码 `461dfc98` 核对入口。本文描述已有实现；下一阶段建议见 [multimodal_bim.md](multimodal_bim.md)。
治理与验证频率以 [Agent.md](../Agent.md) 为准，原多层审批方案不再是开发前置。

## 管线

| 阶段 | 当前职责 / 主要产物 | 实现位置 |
|---|---|---|
| `0_reading` | 校验预先生成的图纸观测、视图与标定信息；CLI 本阶段不自动读原图 | [reading](../../src/agent/reading/) |
| `1_correction` | 证据整合、多层几何、墙、房间和窗；`CorrectedGeometry` 及其扩展 | [correction/schema.py](../../src/agent/correction/schema.py)、[pipeline.py](../../src/agent/pipeline.py) |
| `2_modelling` | 从校正几何生成建筑面/体；`BuildingGeometry` | [geometry](../../src/agent/geometry/) |
| `3_split_pairing` | 当前 CLI 重建并核对几何/规格；切配算法实际已由 build_geometry 调用 | [split_pairing.py](../../src/agent/geometry/split_pairing.py) |
| `4_mep` | 用途、材料、运行等物理语义；HVAC specs 由代码按 zones 替换并合入保留 schedules | [pipeline.py](../../src/agent/pipeline.py) |
| `5_intakeoutput` | 装配与交接检查，输出 `IntakeOutput` | [intakeoutput.py](../../src/agent/intakeoutput.py) |
| 下游 | IntakeOutput → IDF → EnergyPlus | [graph.py](../../src/agent/graph.py)、[run_full_pipeline.py](../../scripts/run_full_pipeline.py) |

CLI 的阶段名字与函数的计算边界并非严格一一对应；例如建模产物已经可能含切配面。
不能仅凭目录或“某阶段已调用”宣称整条链完成，要看实际输出与检查。

## 入口区别

- 从原始图纸生成 reading 观测不是 `flow` 已自动承担的能力，见 [图纸路线](reading_pipeline_architecture.md)。
- 主要实验入口：[run_stage.py](../../scripts/tool_scripts/run_stage.py) 的 `flow`；保存 attempts、checks、judge 和停止原因。
- as-drawn CLI 路径已接多层校正和补窗。代码按契约分类，不能只用文件名猜路线。
- `pipeline.py:run_pipeline` / `run_pipeline_artifacts` 是既有函数入口，内部仍有 legacy 加载路径；不要假定其支持范围与 CLI 新链相同。
- 原始图片与来源信息由各输入适配处理；几何内核消费结构化结果。

## 交接模型

当前下游边界仍是 [state.py](../../src/agent/state.py) 中的 `IntakeOutput`：

`building`、`site_location`，以及 `zone_specs`、`material_specs`、`schedule_specs`、`construction_specs`、
`surface_specs`、`fenestration_specs`、`hvac_specs`、`people_specs`、`lights_specs`。

轻量 BIM 不能简单等同于这组自然语言 specs：已有 `CorrectedGeometry` / `BuildingGeometry` 更适合作为可查看几何的复用基础。
两路共享模型的正式字段尚未定稿，本轮没有新增 schema。

## 需要持续保持

- 单位、坐标原点、朝向、楼层和外皮/轴线基准明确；详见 [坐标与几何](coordinates_and_geometry.md)。
- 已观测数据、推断、默认值和人工修正可区分；简化不应静默删除已知建筑信息。
- 内核的有效性检查服务于输出用途。展示模型与仿真模型可有不同简化策略，但都需记录改变。
- 独立评测使用 GT，生产输入不包含答案。暂时无法评分不必阻止探索模型产出。
- 接口变化在生产者和消费者一起落实，并以真实相邻产物验证；不为每个输入复制一套内核。

## 已知限制

- 现有图纸入口仍对材料和契约有硬要求，尚不是任意缺失信息的混合入口。
- 当前形状支持可见 CLI 的 `rectangular` / `orthogonal_polygon`；复杂体量按需扩展，不宣称已经通用。
- 当前 case 的实际数量、停止阶段与未验证范围集中在 [计划](../plan.md)。
- 旧技术参考中的历史“已实现/待做”状态可能落后；以当前源码、提交和实跑产物为准。
