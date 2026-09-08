---
name: editable-geometry-confirmation-vision
description: "用户的中长期愿景(2026-06-19 记,先不做):把几何确认环节(#3 的 geometry_viewer)从只读检视升级为可轻量编辑——三轴滑杆移窗 / Rhino 式推拉墙(先设网格颗粒度滑杆再按格推拉面)/ 更后期点 surface 自然语言调材料;目的=让用户在这一步微调,之后管线近乎确定、结果不黑箱"
metadata: 
  node_type: memory
  type: project
  originSessionId: 162b5c9c-3c0c-4e9a-9033-d6e8acb8e566
---

用户在 #3 离线 3D 查看器(`scripts/tool_scripts/render_geometry_viewer.py`,几何确认门的检视件)之上,规划一个**中长期方向**:把这一步从**只读检视**升级为**可轻量编辑**,让用户在进入下游(近乎确定的流水线)前略作调整,使整体结果**不那么黑箱**。**2026-06-19 仅记录,先不动手,要先聊方案。**

**想要的编辑能力(由近及远)**:
1. **移窗**:三轴滑杆移动窗户位置。
2. **推拉墙**:类似 Rhino 的 push/pull——**先让用户调一个"网格颗粒度"滑杆**,然后**按这个颗粒度对面进行推拉**(吸附到网格步长)。
3. **(更更后期)调材料**:点击 surface 显示其材料,用**自然语言交互**调整材料。

**意义(用户原话)**:这一步做完后,后面几乎是确定的流水线;让用户能在此微调 + 看清,结果不会太黑箱。

**关联/约束(我补的方案要点,待聊)**:
- 编辑必须**回写到几何的权威表示**——不是只改 three.js mesh,而是改 `building_geometry.json`(或更上游的 `1_correction` snapped 几何),再经确定性内核重建,否则下游对不上。**几何确认门有 digest 绑定**([[pipeline-0-5-refactor-status]] 的 geometry_checkpoint_digest):编辑→几何变→digest 变→需重新 approve,这条链天然支持"编辑后重新确认"。
- 编辑的**确定性**:移窗/推拉本质是改 correction 层的尺寸/坐标,然后**重跑 2_modelling+3_split_pairing 内核**(确定性),保持 EP 配对规范;不能让用户直接乱改导致非封闭/非法配对。
- 网格颗粒度推拉 = 把面沿法向按步长平移 + 内核重切配;窗移动 = 改窗在墙上的 along-facade/z 位置(呼应 [[sm21-review-backlog]] #2 South 窗 x 问题——编辑能力也是一种人工兜底)。
- 落地形态待定:viewer 内嵌编辑(three.js TransformControls + 回写 JSON 经一个本地 server/文件)vs 单独编辑工具。headless 容器无浏览器,编辑回写需要一条 viewer→磁盘的通道(目前 viewer 是纯静态 HTML、只读)。

**下一步**:用户要先聊方案再决定是否/如何落地。见 [[sm21-review-backlog]](#3 几何检视已实现)与 [AI_agent/guides/new_case_guide.md](AI_agent/guides/new_case_guide.md) §2 几何门。
