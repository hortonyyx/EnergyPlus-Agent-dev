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

现有分工实现为调度员、平面读图员和立面读图员；单模型使用同一套源 BIM 与工具。当前以 role_division 为主线，各角色统一使用 gpt-6-sol/high，先逐节点检验，再串联整案。信息入口、确定性状态维护、必要判断和完成条件应清楚，快速稳定交付是检验结果；10分钟只是优化目标。读图员并发、共享预算和恢复继续保留。当前只有单模型支持无整案时间截止，分工入口仍要求有限 seconds；这项接口差异不能混写为所有模式均已支持无限时。

完整草稿、几何与审计留在外部状态，模型通过有界对象读取与局部修改操作。压缩后的证据还必须可发现，不能仅因磁盘保留就认为模型可用；旧版本来源与当前候选要明确区分。优先统一现有接口和几何约束，不新增同功能框架。网格/照片方法先独立收敛，再按证据接入 domain。混合输入与通用任务规划仍是发展方向，当前图纸角色未实现全模态调度。

## 输入与交付

平立面图纸是当前 harness 的主验证输入。单模型接收图像或 GLB，图像可声明 drawings/mesh_views/photos/unknown；分工入口仅支持图纸。接收输入不等于已达到稳定建模质量。[照片→mesh→BIM](photo_to_mesh_bim.md) 已有独立、有开发代理介入的原型，并已转换为项目源格式；照片生成服务尚未接入自主 harness，细度自动选择尚未实施。

核心交付为源 BIM：空间、边界、门窗、相邻/连通与依据；查看页由 `render_geometry_viewer.py` 及随包资源生成。源空间简化与后端热区划分分开，EnergyPlus 是可选下游。

当前主线为全6 Sol/high分工：公共坐标与楼层约定 → 平/立面读图、试建、采用值图和局部原图回叠 → 不可变读图交付 → 平立面匹配、层高与门窗高度应用 → 整楼建筑合理性 → 定向返工 → finish交付。读图员负责局部正确性；调度员复用读图检查，判断跨图一致性与建筑合理性。单模型保留 `process_reviews: true` 作为实验入口。

`reader_task`（CLI `--reader-task-json`）通过相同 RoleSession、权限、预算和事件记录只运行一个明确读图任务，跳过调度员模型和整案自动补齐。输出明确为 reader_unit，不能当整楼交付。平面交付复用实际试建图；立面 `trial_elevation_reading` 先保存采用值、净图和原图叠图，`submit_elevation_reading` 引用当前试稿并附 `local_review.summary`。检查与产物哈希绑定，图像改动或旧稿不能静默复用；自报检查不等于独立质量验收。调度员 `finish_bim` 携带 `architectural_review.summary`，绑定实际源几何。读图接受与完整finish均自动结束相应任务，不额外请求结束语。


保留的单模型实验入口中，平面交付复用现有草稿、源BIM、标定与实际源回叠；立面交付保留独立观测、采用值、标高/开口清单、回叠和未确定项。`prepare_elevation_reading` 复用分工读图校验、墨线定位与10cm规整；等价锚点对、开口列表顺序由代码整理，可从完整清单计算数量，语义冲突仍拒绝。`apply_elevation_readings` 复用匹配与有依据的高度批量应用，应用前返回超宿主高度的开口、楼层和修订入口。

局部判断通过下一次正常建模、修订、读数、装配、应用或交付调用的`reviews_json`携带；没有独立登记工具。判断绑定已返回且模型已检查的结果，不能预先批准该次操作的新结果。先看整套图确认公共坐标和有依据的层高，再尽早试建。建筑判断可随`finish_bim`提交；正式交付前应先完成预期修改和备注整理，再选择实际最终稿。层间轮廓投影差异作为事实提示，不判断同墙、不自动移动墙，墙带规整仍待讨论。

单模型局部检查绑定原图、采用结果和实际回叠；未改的物理范围可跨候选复用，修改高度不作废平面XY判断。装配后重点核对跨图冲突、体量/楼层、空间与动线、宿主和高度合理性，发现具体问题才返回相应图纸。`finish_bim` 对启用该政策的单模型运行要求当前局部覆盖、平立面应用一致性和建筑判断；分工模式使用上述读图交付、装配和建筑判断契约。模型自报检查完成、确定性一致、独立质量评价分别记录；原图已返回不等于模型已正确理解。历史manifest保留原政策。

图纸分工采用 10 cm 规整。整图标注自动选步长、照片/混合输入细度政策仍待讨论；正确空间关系优先于逐点吻合。离线通过不证明图纸保真或推断合理。

## 当前与历史入口

用户入口为 `sim_bim.py` / `Start.cmd` → `product_cli` → `runtime_configuration` → 单模型或分工入口。当前模型实际接收的 guidance 由 domain 模块生成，源码导航见 [domain 入口](../../src/agent/README.md)。

旧 EnergyPlus intake 顺序管线与阶段资源集中到 [legacy](../../src/agent/legacy/README.md)，不作为顶层 skills 或当前 BIM Agent 的步骤说明。历史 stage ID、产物目录与字段保留原含义；共享的几何、校验和下游适配按能力保留，不因历史命名批量删除。继承与新增关系见 [domain 沿革](domain_lineage.md)。

## 程序与数据

D 盘开发仓库含代码、必要测试和当前文档；桌面为固定提交生成的独立产品。`input_root` 只授权本案材料，`run_root` 指向独立产物。GT、历史答案和归档不得暴露给 work model。

完整持久交互编辑界面、各输入的稳定质量、真实模型推理和下游仿真仍需独立验收。历史资料位置见 [归档索引](../reports/archive-index.md)。
