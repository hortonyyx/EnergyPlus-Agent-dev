# 当前代码链与接口

2026-09-08 按整合代码 `461dfc98` 核对入口。本文描述已有实现；下一阶段建议见 [multimodal_bim.md](multimodal_bim.md)。
治理与验证频率以 [AGENTS.md](../../AGENTS.md) 为准，原多层审批方案不再是开发前置。

## 管线

| 阶段 | 当前职责 / 主要产物 | 实现位置 |
|---|---|---|
| `0_reading` | 图纸观测、识别结果、视图与标定信息 | [reading](../../src/agent/reading/) |
| `1_correction` | 证据整合、多层几何、墙、房间和窗；`CorrectedGeometry` 及其扩展 | [correction/schema.py](../../src/agent/correction/schema.py)、[pipeline.py](../../src/agent/pipeline.py) |
| `2_modelling` | 从校正几何生成建筑面/体；`BuildingGeometry` | [geometry](../../src/agent/geometry/) |
| `3_split_pairing` | 面切分、跨区域配对及几何规格 | [split_pairing.py](../../src/agent/geometry/split_pairing.py) |
| `4_mep` | 用途、材料、运行和设备等物理语义 | [pipeline.py](../../src/agent/pipeline.py) |
| `5_intakeoutput` | 装配与交接检查，输出 `IntakeOutput` | [intakeoutput.py](../../src/agent/intakeoutput.py) |
| 下游 | IntakeOutput → IDF → EnergyPlus | [graph.py](../../src/agent/graph.py)、[run_full_pipeline.py](../../scripts/run_full_pipeline.py) |

CLI 的阶段名字与函数的计算边界并非严格一一对应；例如建模产物已经可能含切配面。
不能仅凭目录或“某阶段已调用”宣称整条链完成，要看实际输出与检查。

## 入口区别

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

- 单位、坐标原点、朝向、楼层和外皮/轴线基准明确；跨输入变换可追溯。
- 已观测数据、推断、默认值和人工修正可区分；简化不应静默删除已知建筑信息。
- 内核的有效性检查服务于输出用途。展示模型与仿真模型可有不同简化策略，但都需记录改变。
- 独立评测使用 GT，生产输入不包含答案。暂时无法评分不必阻止探索模型产出。
- 接口变化在生产者和消费者一起落实，并以真实相邻产物验证；不为每个输入复制一套内核。

## 已知限制

- 现有图纸入口仍对材料和契约有硬要求，尚不是任意缺失信息的混合入口。
- 当前形状支持可见 CLI 的 `rectangular` / `orthogonal_polygon`；复杂体量按需扩展，不宣称已经通用。
- sm25 最近建模产物有两张约 65 mm 短边配对面，被现行 100 mm 检查拦截；没有完成后续仿真。
- 旧技术参考中的历史“已实现/待做”状态可能落后；以当前源码、提交和实跑产物为准。
