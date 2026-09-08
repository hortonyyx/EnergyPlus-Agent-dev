# 几何切配与有效性参考

已建成的确定性内核优先复用：[modelling.py](../../src/agent/geometry/modelling.py)、[split_pairing.py](../../src/agent/geometry/split_pairing.py)、[build.py](../../src/agent/geometry/build.py)。本文是方法说明，当前支持范围见 [能力图](../capability/README.md)。

## 切配在解决什么

两个区域共用的边界可能被两侧不同的房间分割。确定性算法识别相交部分、分片、建立对应关系，再输出具有正确朝向与引用的计算面。当前实现用多边形运算处理墙和水平楼板，不让模型凭文字猜计算几何。

## 分开检查不同问题

| 问题 | 检查重点 |
|---|---|
| 单个面是否有效 | 有限坐标、平面/面积/环、自交和退化 |
| 已有配对是否合法 | 对象存在、互相引用、对应几何与法向 |
| 该有的覆盖是否齐全 | 预期相交范围与实际配对覆盖的差集 |
| 源建筑信息是否保留 | 房间、隔断、门窗及其来源和宿主 |
| 能否交给下游 | 相应出口的几何、构造和用途约束 |

某一项通过不能代替其他项。检查阈值应注明单位和作用，不能把经验阈值说成求解器的普遍物理限制。

## 旧参考中不再沿用的结论

- 0.1 m 是当前项目相关检查采用的值，旧崩溃个例不足以证明所有 EnergyPlus 模型短边低于它都不可运行。
- 统一量化到 50 mm、自动剔除小片或强制层间墙对齐不是通用修复；先判断真实差异与转换/数值误差，简化时检查覆盖与信息损失。
- 两面共用同一个 Construction 名称并不自动保证非对称材料层序互为反向；具体下游装配应按实际构造与求解器要求核验。
- 支持退台的局部算法不等于已经支持中庭、通高和任意斜屋面。源码和实跑是实现依据。

来源原稿保存在 [InterZone 备忘](../archive/2026-09-08_management_rebuild/original/AI_agent/reference/InterZone_Surface_Matching_TechNote.md) 与 [内核参考](../archive/2026-09-08_management_rebuild/original/AI_agent/reference/split_pairing_kernel_reference.md)。
