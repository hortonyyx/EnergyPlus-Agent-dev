# 当前架构

Sim BIM Agent = work model + harness；harness = runtime + domain。单模型与分工共用源BIM、几何能力与工具。当前版本/验证状态只在 [roadmap](../project/roadmap.md) 维护。

## runtime

`src/agent_runtime`负责模型适配、请求/工具循环、上下文、事件/产物、用量与预算、暂停/恢复、委派和连接。公共类型在`src/harness_contracts`。支持GLM订阅、Paratera等已登记线路及ChatGPT原生Responses订阅接入；真实服务状态独立验收。

按运行记录模型配置、runtime/domain版本与提交。保存声明/候选、事件账本和恢复点，按工具可重复性恢复；缺真实usage不凭估算补成供应商事实。源码版本检查保留，发布目录通过不可变文件清单识别来源。

## domain

- `src/agent/geometry`：源模型、平面编译、规整、装配、开口与空间关系。
- `src/agent/runtime_roles`：调度员、平面读图员、立面读图员；工具范围、指引和产物契约。
- `scripts/tool_scripts/run_bim_agent.py`及`bim_agent_*.py`：看图/量测/试建/编辑/检查/交付工具。
- 输入方式对应独立methods和指引，共用源BIM；图纸分工路径已接入，网格/照片按现有单模型能力使用。
- `render_geometry_viewer.py`及随包JS：离线HTML查看页。
- 旧固定阶段管线、判断/诊断、EnergyPlus适配仍有源码与可选检查，不作为新产品必经工作流。旧graph按显式API需要加载。

当前产品重点为正确空间划分与关系，而非逐点复刻。10cm规整已在分工路径接入，自动读全图标注选步长尚未实现。声明持久/局改、近轴与尺寸链门槛仍是后续讨论项。

## 程序、输入与数据

D盘开发仓库含代码、必要测试和当前文档；桌面是无Git发布目录。发布清单含程序、资源、版本登记及锁文件；环境和用户数据独立。发布入口为`sim_bim.py`/`Start.cmd`，配置入口仍复用`runtime_configuration`。

配置的`input_root`只授权本案输入所在范围，`run_root`只授权独立运行产物。两模式共用外部目录。GT、历史答案、归档和其他检出不能因为根目录迁移而暴露给work model。产品不依赖D盘开发源码或Git元数据。

## 交付与限制

源BIM保存空间、边界、门窗、相邻/连通及依据；后端热区为显式派生，不改源空间语义。EnergyPlus为独立可选下游；通过离线几何或工具验收不等于仿真或图纸保真验收。

产品具有局部工具修改与查看能力，完整持久交互编辑界面尚未交付。ChatGPT真实订阅连接等待用户独立授权；当前sm25规整失败结果保持冻结。本次发布组织调整不改变这些质量结论。

旧架构沿革和原文在`D:\Sim-BIM-Agent\archive\documentation-before-slim`及Git基准`9f5332ae`，按问题查证。
