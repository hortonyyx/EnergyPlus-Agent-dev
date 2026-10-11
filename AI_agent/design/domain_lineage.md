# Domain 的继承关系

当前 domain 是复用、转化和新增共同形成的，不是将旧 skills 改名，也不是从头重写。旧库按执行阶段混放 prompt、方法、接口规则、算法规格和物性参考；现在按职责组织。

| 旧积累 | 当前去向 | 关系与边界 |
|---|---|---|
| 读图、量测、分辨构件、处理歧义的经验 | `bim_agent_guidance.py` 的图纸方法与参考，角色指引和工具反馈 | 经历持续转化与迭代；当前运行不原样加载旧 reading prompt |
| 校正、规整、开口宿主、空间关系、构面与切配 | `src/agent/geometry` 及相关 correction/validator 实现 | 既有确定性能力复用并继续发展；并非每个当前算法都来自旧 skill |
| 建模、依据、检查与修改规则 | 源 BIM、contracts、工具参数和反馈 | 规则被重新分配到结构化契约、代码检查和必要 guidance，避免全部挤进 prompt |
| 旧 EnergyPlus 物性和 IntakeOutput 规则 | `legacy/intake/mep`、`intakeoutput` 及可选下游工具 | 保留为显式旧工具资源，不是当前源 BIM 的必经步骤 |
| 原固定顺序管线和 LangGraph | `src/agent/legacy/pipeline.py`、`graph.py` | 隔离保留，旧运行可追溯，不驱动当前 harness |
| 当前图纸角色、产物交接与确定性总装 | `runtime_roles` | 后来围绕新架构新增和迭代，复用共同 kernel、工具与经验 |
| 自有请求循环、上下文、预算、事件与恢复 | `src/agent_runtime` | 后来开发的 runtime 基础设施，属于 harness，与 domain 分开 |

方法不等于 prompt。方法可以同时体现在角色职责、工具操作、产物结构和反馈；guidance 只承载模型需要知道的文字，确定性规则尽量由代码执行。这里的归类解释职责与总体沿革，不声称旧文件每一段都有一对一迁移。

本轮整理当前入口、命名、历史资源与引用，不重新设计几何算法、工作模型提示或照片细度。当前有效能力导航见 [domain 入口](../../src/agent/README.md)。

清理前的文档和阶段资源已逐项哈希保全；历史提示、用量与方案见 [归档索引](../reports/archive-index.md)。旧文件不会继续以“当前要求”的形式出现在操作入口。
