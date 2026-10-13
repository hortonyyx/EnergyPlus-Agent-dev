# 当前架构

Sim BIM Agent = work model + harness；harness = runtime + domain。单模型与分工共用源 BIM、几何能力和工具。模型与输入策略见 [讨论结论](../project/model_and_input_strategy.md)，版本与实际验证状态见 [roadmap](../project/roadmap.md)。

## Runtime

`src/agent_runtime` 负责模型适配、请求与工具循环、上下文、事件/产物、用量/预算、暂停/恢复、委派与连接；公共类型在 `src/harness_contracts`。它不定义建筑判断，也不要求任务经过固定编号阶段。

每次运行记录模型配置、runtime/domain 版本及提交，持久化事件、产物与恢复点。服务连接、目录访问和真实推理分别验收；缺失 usage 不由估算补成供应商实报。

## Domain

| 组成 | 职责 | 当前主要实现 |
|---|---|---|
| BIM rules | 源 BIM、依据、声明、检查与修改约束 | `src/agent/contracts`、`geometry/source_bim.py` |
| kernel | 编译、空间关系、规整、装配和开口宿主计算 | `src/agent/geometry` |
| tools | 看图、量测、试建、编辑、检查和交付 | `scripts/tool_scripts/run_bim_agent.py`、`bim_agent_*.py` |
| methods | 按输入及任务组合的处理方法 | 图纸方法、mesh 观察工具及输入专用 guidance |
| roles | 职责、可见工具、上下文与产物契约 | `src/agent/runtime_roles` |
| guidance | 系统指引、任务说明、参考资料、工具说明和反馈 | `bim_agent_guidance.py`、`runtime_roles/guidance.py` |

Methods 是可复用方法，不是固定阶段；roles 是任务分工，不与三条研究线一一对应。三条线描述相对于交付目标的信息充分程度，同一项目可以组合不同输入和能力。

现有分工实现为调度员、平面读图员和立面读图员；单模型使用同一套源 BIM 与工具。当前优先以现有 single_model 入口验证充分且必要的 harness，让强模型在一个工作上下文共享全套图纸与建筑状态。信息入口、确定性状态维护、必要判断和完成条件应清楚，快速稳定交付是检验结果；10分钟只是优化目标，没有整案硬截止。分工保留为对照和经验证的并行优化。

完整草稿、几何与审计留在外部状态，模型通过有界对象读取与局部修改操作。压缩后的证据还必须可发现，不能仅因磁盘保留就认为模型可用；旧版本来源与当前候选要明确区分。优先统一现有接口和几何约束，不新增同功能框架。网格/照片方法先独立收敛，再按证据接入 domain。混合输入与通用任务规划仍是发展方向，当前图纸角色未实现全模态调度。

## 输入与交付

平立面图纸是当前 harness 的主验证输入。单模型接收图像或 GLB，图像可声明 drawings/mesh_views/photos/unknown；分工入口仅支持图纸。接收输入不等于已达到稳定建模质量。照片生成 mesh 与细度自动选择均未实施。

核心交付为源 BIM：空间、边界、门窗、相邻/连通与依据；查看页由 `render_geometry_viewer.py` 及随包资源生成。源空间简化与后端热区划分分开，EnergyPlus 是可选下游。

图纸分工采用 10 cm 规整。整图标注自动选步长、照片/混合输入细度政策仍待讨论；正确空间关系优先于逐点吻合。离线通过不证明图纸保真或推断合理。

## 当前与历史入口

用户入口为 `sim_bim.py` / `Start.cmd` → `product_cli` → `runtime_configuration` → 单模型或分工入口。当前模型实际接收的 guidance 由 domain 模块生成，源码导航见 [domain 入口](../../src/agent/README.md)。

旧 EnergyPlus intake 顺序管线与阶段资源集中到 [legacy](../../src/agent/legacy/README.md)，不作为顶层 skills 或当前 BIM Agent 的步骤说明。历史 stage ID、产物目录与字段保留原含义；共享的几何、校验和下游适配按能力保留，不因历史命名批量删除。继承与新增关系见 [domain 沿革](domain_lineage.md)。

## 程序与数据

D 盘开发仓库含代码、必要测试和当前文档；桌面为固定提交生成的独立产品。`input_root` 只授权本案材料，`run_root` 指向独立产物。GT、历史答案和归档不得暴露给 work model。

完整持久交互编辑界面、各输入的稳定质量、真实模型推理和下游仿真仍需独立验收。历史资料位置见 [归档索引](../reports/archive-index.md)。
