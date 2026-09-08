---
name: self-consistent-gates-anchor-on-product-chosen-apertures
description: 自洽重算门若锚在产物自报的支撑/孔径上，表示法塌缩可全绿；关门判据=镜像生产者的分组定义
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5b506ee-5ace-4a11-a706-a2503219d163
---

2026-08-24 五审实测（as-drawn reading 判据组）：`observations_recomputable_from_own_pixels`
重算 `edges_m` 用的是**产物自报的 support_cols 端点**——产物把支撑条报多宽，重算就认多宽，
门只验证「数与孔径自洽」，从不验证「孔径内真的是一条连续的墨」。于是「两线墙塌成一条自洽的带」
（band_collapse）骗过全部八门 + 新判分器 + 旧 gt 尺，C1/C2/C5/gt 与诚实逐位同、C4 反而被洗得更低
（consts 多了，多画更容易被解释掉）。

**Why:** 自洽 ≠ 与源同一。当重算的锚（支撑列、孔径、采样窗）由被测对象自己挑时，
重算只是在验证「你没有算错自己的谎」，不是在验证「你说的东西存在」。与
[[recompute-gate-must-mirror-producer-definition]]（映射公式要镜像）互补：那条管**怎么换算**，
这条管**在什么上换算**。

**How to apply:**
- 给任何「从自身像素重算」的门问一句：重算的锚是谁挑的？锚可挑 ⇒ 门只防算错、不防选错。
- 关门判据优先**镜像生产者的分组/聚合定义**（例：按 `_ink_groups` 同款数支撑条内墨列组数，
  诚实两方言全 1、塌缩带全 2，零阈值），而不是再发明一个填充率阈值（0.57 vs 0.52 的边太贴）。
- 表示法塌缩类作弊在「多 consts」的尺子上常**优于**诚实（覆盖=并集、多画更易解释）——
  别指望分数降，要指望有门看得见形态（同 [[two-rulers-answer-side-and-source-side]]）。
- 平行墙的门洞在沿轴米数上会数值重叠：命名/归属迁移必须限定到本墙自己的源面，
  全局按跨度匹配会把名字偷给别的墙（本轮调试实撞）。
