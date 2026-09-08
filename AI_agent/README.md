# 多模态输入 → 轻量 BIM

项目要把现有图纸、文字参数、带表皮体量以及后续 CAD 等输入，转成可查看、可解释、可继续用于能耗建模的轻量 BIM。
“丐版”指按现有信息生成有用的简化模型，不要求施工图级精度，也不允许把未知信息伪装成准确事实。

## 当前口径

- 图纸路线：尽可能恢复外形、楼层、主要房间/分区、墙与门窗。
- 体量路线：先保住体量、楼层和外表皮；内部划分、用途、构造等可用明确的推断或默认值补足。
- 混合入口：多种输入组合提升同一模型；不要求每个输入都具备完整平面和立面。
- 近期验收围绕一个真实 case 的模型产物和可读问题清单，随后验证 IntakeOutput / IDF / EnergyPlus。
- 两条路线尚未统一实现。现有代码主要服务图纸链，不能把设计方向写成已具备的能力。

## 已有基础

| 位置 | 用途 |
|---|---|
| [reading](../src/agent/reading/) | 图纸观测、感知与工具箱 |
| [correction](../src/agent/correction/) | 证据整合、楼层协调、墙与门窗、校正几何 |
| [geometry](../src/agent/geometry/) | 确定性建模、切分和面配对 |
| [pipeline.py](../src/agent/pipeline.py) | 管线函数及物理属性阶段 |
| [run_stage.py](../scripts/tool_scripts/run_stage.py) | 分阶段 `flow` CLI、attempt、检查与产物归档 |
| [state.py](../src/agent/state.py) / [intakeoutput.py](../src/agent/intakeoutput.py) | IntakeOutput 交接模型与装配 |
| [graph.py](../src/agent/graph.py) | 下游 IDF / 仿真代理链 |
| [validator](../src/validator/) / [judge](../src/agent/judge/) | 几何/交接检查与独立评测 |
| [case_tests](../case_tests/) | 原始素材、运行产物与基准 |

## 文档职责

| 文档 | 只负责什么 |
|---|---|
| [AGENTS.md](../AGENTS.md) | 开发行为、权限和收工 |
| [plan.md](plan.md) | 当前状态、近期下一步和少量明确搁置事项 |
| [development.md](guides/development.md) | 常用开发、测试、Git 操作 |
| [new_case_guide.md](guides/new_case_guide.md) | 如何使用现有 CLI 跑 case |
| [pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) | 当前代码链与实际接口 |
| [multimodal_bim.md](architecture/multimodal_bim.md) | 两路融合的建议设计，明确标出尚未实现 |
| [decision_log.md](decision_log.md) | 当前方向上的关键决策，长历史只留链接 |
| [logs](logs/README.md) / [archive](archive/README.md) | 历史过程和旧口径，不自动生成待办 |

其余技术参考按需查阅，不再是开工必读串。旧技术规格可以复用；其中的旧日期状态、审批顺序和“硬纪律”不恢复为开发要求。
项目级决定必须落在仓库，Claude 本地记忆只作索引。当前阶段见 [plan.md](plan.md)。
