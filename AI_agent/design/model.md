# 共同源 BIM

所有输入方法和执行模式共用源 BIM，承载空间、边界、开口、相邻/连通及依据。信息充分程度描述任务条件，不定义三套数据模型。当前目标与未定细度策略见 [产品目标](../project/goal.md)。

## 对象与实现

| 内容 | 当前实现与边界 |
|---|---|
| 空间 | 逻辑闭合空间体，保留楼层、轮廓、高度与身份；按交付目标表达实际空间或已授权的简化 |
| 边界 | 带归属和几何的空间边界；同一隔断两侧可以是相关联的两个边界，不冒充唯一全局墙实体 |
| 开口 | 门、窗、无门洞口，保留宿主、尺寸和空间关系；开口连通不等于空间合并 |
| 依据 | 观测、推断、假设、简化及用户要求区分，保存来源与所采用值 |
| 派生物 | 查看页/回叠及可选后端输入从源 BIM 生成，不能反向冒充源对象完整性 |

主要代码入口：

- [source_bim.py](../../src/agent/geometry/source_bim.py)：独立源 BIM 构造和显示投影，`source_bim_v2`。
- [source_enclosure.py](../../src/agent/geometry/source_enclosure.py)：显式实际围护扩展，`source_bim_v3`。
- [schema.py](../../src/agent/correction/schema.py)：复用的几何、源空间、边界和开口数据类型；路径名不表示当前必须跑旧 correction。
- [plan_assembly.py](../../src/agent/geometry/plan_assembly.py)：平面和多层装配。
- [source_space_relations.py](../../src/agent/geometry/source_space_relations.py)：空间关系查询。
- [bim_delivery.py](../../src/agent/geometry/bim_delivery.py)：交付范围与检查摘要。

旧 `geometry/source_model.py` 还服务历史 EnergyPlus 的 `source_bim_v1` 附带投影。它不作为当前源输出的唯一入口，亦不能以其旧阶段目录描述当前架构。

## 坐标、规整与修改

长度以米表达，x 东、y 北、z 为绝对高度；图像定位按工具约定保存原始像素及变换。楼层装配、开口宿主和显示使用一致坐标，不能只改查看器小数位代替修改源几何。

现有图纸分工采用 0.1 m 联动规整，保留原始读数、采用值和对象关系；原图标注首先服务尺度与尺寸链。不能靠删开口、错误拆并空间或改变连通消除冲突。自动选步长和新的细度政策尚未实现。

局部工具可修改已有声明/候选，修改后的检查必须对应实际保存版本。完整持久交互编辑界面仍未交付，不把工具可修改等同完整产品编辑体验。

## 输入方法与后端

图纸识读、mesh 分析及未来照片方法共用上述对象和检查。信息不足允许明确假设，不要求凭空补全所有室内细节；具体照片按层成块及细度调整留待讨论。

源空间简化与 EnergyPlus 热区合并是独立决策。下游派生、物性配置及仿真分别验收，源 BIM 几何有效不证明能耗准确。

本页清理前的逐次实现、墙厚/规整方案和历史对照完整保留于 [归档索引](../reports/archive-index.md)。当前状态以 [roadmap](../project/roadmap.md) 为准。
