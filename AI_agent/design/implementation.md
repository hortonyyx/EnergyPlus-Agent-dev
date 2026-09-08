# 现有实现与能力边界

依据业务代码 `461dfc98` 和 [2026-09-08 代码审计](../logs/experiments/2026-09-08_management_audit/README.md)。本轮管理整理未扩展业务能力；当前 case 的具体状态只在 [路线与任务](../project/roadmap.md) 维护。

## 实际调用链

| 阶段 | 当前行为与产物 | 实现 |
|---|---|---|
| 0_reading | 读取并检查预生成的 `*_view.json`，不自动调用视觉模型读原图 | [run_stage.py](../../scripts/tool_scripts/run_stage.py)、[reading](../../src/agent/reading/) |
| 1_correction | legacy/as-drawn 分派、多层证据整合、坐标校正、补窗与 finalize，输出 CorrectedGeometry/V3 | [pipeline.py](../../src/agent/pipeline.py)、[correction](../../src/agent/correction/) |
| 2_modelling | 构建 BuildingGeometry，build 内已造面、切配和挂窗 | [build.py](../../src/agent/geometry/build.py) |
| 3_split_pairing | 当前 CLI 再从校正产物重建，序列化 specs 并与前段几何核对 | [split_pairing.py](../../src/agent/geometry/split_pairing.py)、run_stage.py |
| 4_mep | 生成非几何语义；HVAC specs 由代码按 zones 替换并合入保留 schedules | pipeline.py、[intakeoutput.py](../../src/agent/intakeoutput.py) |
| 5_intakeoutput | 朝向/坐标合同、已接受产物核对、装配 IntakeOutput 和 sidecar | [output_coordinates.py](../../src/agent/output_coordinates.py) |
| 下游 | IntakeOutput → IDF → EnergyPlus | [graph.py](../../src/agent/graph.py)、[run_full_pipeline.py](../../scripts/run_full_pipeline.py) |

CLI `flow` 保存 attempts、checks、停止原因和可选 judge/确认。`run_pipeline` / `run_pipeline_artifacts` 函数仍有 legacy 加载路径，不能假定和 CLI 支持范围相同。命令与配置优先级见 [运行 case](../workflow/run_case.md)。

## 图纸观测与证据

reading 工具箱、CV、隔离和模型工具可复用，但需要调用者准备配置、观测和执行顺序。`flow` 本身没有完整冷启动识图入口。
[vector_contract.py](../../src/agent/reading/vector_contract.py) 将 legacy ReadingView 作为消费格式，as-drawn plan v2 / elevation v0 可适配，plan v0 尚不消费；现有 as-drawn 路由要求相应平立面材料，混用或缺失会拒绝。

as-drawn 的 reading 检查覆盖契约、标定和尺寸链，旧字段检查为 NA；来源引用还依赖校正等消费者验证，独立像素自检不等于自动接进 flow。尺寸链和纯像素是不同证据条件，像素量测不能凭统一量化变成尺寸标注精度。
校正证据链已接多层求解、楼层协调和窗口构建；projection bridge 的 `outer_skin` 尚未实现，`complete` 只说明对应算法的完成条件，不证明所有房间都已读出。窗位置路线②的 citation 仍有 shadow 阶段，完整替代模型 span 尚未交付。

## 模型和几何内核

[correction/schema.py](../../src/agent/correction/schema.py) 中 Cell 以米表达平面、Floor 给出高度；legacy 注释使用 world-frame/centerline，V3 配合当前建筑坐标合同，带 footprint、立面段、来源等字段。
[geometry/modelling.py](../../src/agent/geometry/modelling.py) 提供 ZoneVolume、Surface 和 BuildingGeometry；后者主要承载 zone/surface/window，并非完整通用 BIM。当前切配按楼层分组处理墙和相邻层水平面，不能据几何原语支持 polygon 就宣称任意通高、中庭、斜屋面均可运行。

E4 的建筑坐标、Relative、Zone 归零和来源朝向已经接入装配及导出检查；并非全部 legacy 入口都等价消费。[state.py](../../src/agent/state.py) 中 IntakeOutput 仍以 building、site_location 及九类 specs 交接下游，多数 specs 是文本，不能替代可编辑的建筑模型。
V3 外皮事务和 B5 的部分窗宿主/可见性链要求楼层 footprint/family 范围匹配，还会拒绝部分 assumed existence；不能直接用于任意外壳或全推断开口。

## 面向目标的缺口

| 能力 | 已有基础 | 缺口 |
|---|---|---|
| 窗与开口 | 补窗已接线并有实际产物 | 门等仍有未分类台账；通用开口、连通和源隔断不完整 |
| 朝向与视图匹配 | 候选/假设朝向与 manifest | 枚举槽不是自动多源匹配和仲裁 |
| 查看与编辑 | 离线交互式 3D 查看器、确认/恢复 | 窗移动、墙推拉、自然语言修改的完整回写尚需实现 |
| 外皮体量 | 可复用几何与查看出口 | 专用适配、内部推断及其简化策略尚待建立 |
| CAD 与混合输入 | 已有 CAD/GT 工具及图纸资产 | 生产输入与评测答案需分开；现有图像评测测试仍禁 case_data 带 DXF/DWG，接 CAD 时需相应调整 |
| 下游与物性 | IntakeOutput/IDF/EP 基础 | 最近 case 尚未贯通；协作者交付需核对接口，不重开同类工程 |
| 质量与成本 | checks、judge、配置和记录工具 | 目标档模型仍需形成可比较的实跑基线 |

GT 修订、AnswerCompiler 和评分已有部分接线，尚未统一消费 frozen facts，详见 [验证与评价](evaluation.md)。相关模块按用途复用，设计建议只有落实并实测后才成为能力声明。
