---
name: geometry-pipeline-terminology
description: 约定术语(2026-06-07):再拓扑=在phase1平面上新划zone热区;切配=面切成EP一一对应(确定算法/与线无关);两条线只在zonification分叉
metadata: 
  node_type: memory
  type: project
  originSessionId: ff93d25b-d556-4e3e-8383-6b94e15457ab
---

用户 2026-06-07 约定的几何管线表达术语，后续所有几何讨论按此口径，别再混用：

- **再拓扑** = 在 phase1 画出的平面基础上**进行新的 zone 区划分**（重划热区）。是 zonification 的一种方式，**不**含切配。
- **两条线** = 都只是 **zonification（怎么定 zone）的选择**：
  - 忠实建模 = 房间=zone，保留真实房间（近乎 identity）。
  - 热区再拓扑 = 重划成少而大的新热区（需按真仿真热区规范）。
- **切配** = 把几何建模（面**不**一一对应）切成 EP 要求的**一一对应**关系。**已定为确定性几何算法**，**独立、与两条线无关**（两条线都喂同一个切配）。其 algorithm-vs-LLM 问题不存在，只剩"用哪个库实现"工程问题。

管线顺序：phase1 识图 → 校正(容差) → zonification(两条线在此且仅在此分叉) → 几何建模(升起) → 切配(确定算法) → EP。

直接推论：① 校正(partA)/几何建模/切配 两条线共用，只 zonification 分叉。② 研究简报 [geometry_first_research_brief.md] 真正开放问题 = zonification/热区再拓扑怎么做(算法vs LLM vs 范式)，切配是另一条独立窄轨。

注意 [[twostep-poc-v2-status]] 与现有文档 geometry_first_zonification.md 早期用"再拓扑"指代含切配的整个内核，与本约定有漂移，引用旧文档时按本约定重新对齐。相关:[[recognition-modeling-capability]]。
