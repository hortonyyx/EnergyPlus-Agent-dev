# 09-09 图纸路线详细计划与源分区纠正

## 用户要求与交付

用户要求总体把控 C2 非方形、C2.1 立面匹配、挑空/退台、非正交的递进方式，澄清后细化后续执行计划；并纠正 sm24 是 reading 正确、C2 前 correction 将其切割。源分区错误比尺寸微差严重，热区可合并不能成为其他模拟丢失真实分区的理由。随后用户确认 BIM 应是多模拟共用底座，当前基本形式为带门窗的有边界空间体。

已修订 [执行计划](../../project/drawing_reconstruction_plan.md)，明确空间/隔断/开口源对象与计算派生物，细列 M0/M1 工作包和 M2–M6 的样例、依赖、改动与完成条件。主顺序为基础 → 三案例 → 立面匹配 → 退台 → 内院/挑空 → 非正交 → 组合，独立能力可按需求前移。已询问歧义处理与后续实际样本，未答复部分为暂定，不阻塞已知三案例的 M0/M1。

## sm24 直接证据：纠正上一轮解读

基于 `d6801ff5`，读取 [sm24 06-24 run](../../../case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading)：

- `1_correction/attempts/002/output.json` 和 `correction_geometry_snapped.json` 已各有 11 个 cell，polygon 均未提供；不是仅在最终显示阶段三角化。
- 走廊为 `cell_corridor_upper/lower` 两个 cell；右下办公室为 `cell_office_right_bottom_upper/mid/lower` 三个 cell。
- `2_modelling/building_geometry.json` 将其分别映射到 Z06/Z10、Z07/Z08/Z11，存在以下 `type=Wall, obc=Surface` 的互配：

| 配对 | 几何范围（m） | 含义 |
|---|---|---|
| Z06_W1 ↔ Z10_W5 | x=4.1…5.9，y=4.95，z=0…4.5 | 走廊计算切线成为两个空间之间的 Wall |
| Z07_W2 ↔ Z08_W3 | x=9.6…9.9，y=4.95，z=0…4.5 | 办公室上/中片之间的 Wall |
| Z08_W1 ↔ Z11_W3 | x=9.6…9.9，y=4.05，z=0…4.5 | 办公室中/下片之间的 Wall |

用户确认 reading 正确，实际切割发生在 correction，这与产物一致。上一轮把历史 minor/EP 成功用作当前可接受表示差异的例子不妥，已在当前文档及前一记录顶部更正。应回归验证正确房间/隔断关系，不单纯要求某个热区总数。

## 复杂度源码边界

- `tests/test_c2_b1_cell_polygon.py` 已有单 L 形源 cell、不增加跨凹口虚墙的用例及 sm24 形状用例；本轮只读测试定义，未重跑，说明有资产可复用，不作为本次新能力成绩。
- `execution/run_config.py` 当前 profile 为 rectangular/orthogonal_polygon；`correction/cell_geometry.py` 和 facade visibility 拒绝非正交边。底层使用 polygon 不能证明完整非正交路径已支持。
- V3 有 per-floor footprint，但 `correction/multifloor.py` 明确用 `PER_FLOOR_FOOTPRINT_MISMATCH` 拒绝不同楼层外形；`split_pairing.py` 有交集/差集处理未覆盖屋面与外露底板，适合复用为退台基础。
- `Cell` 只有外环，`projection_bridge.py` 拒绝 `FOOTPRINT_HAS_INTERIORS`；`build_zone_volumes` 从所属层统一取 zf/zt，墙面按同层配对、水平面按相邻层处理。孔洞、跨层空间及不同高度的侧面部分相接需要实际扩展。
- 历史 C2.1 设计已有未命名/缺立面、投影宽/层结构/窗列匹配的思路；07-18 记录已把整体旋转和匹配分成独立轴。只复用这些技术思路，不恢复旧审批、schema 冻结和全锁要求。

## 本轮验证与下一次入口

本轮仅修改项目文档，没有业务代码改动、模型调用、新几何生成或 EP 运行。`git diff --check` 通过，13 份变更文档的 117 个本地链接可解析，未跑 pytest。下一次从计划 M0-1/2/4 开始，先把源分区和自动判定做对，再接门/连通、容差规整与当前冷启动链；短边微差不再压过源拓扑成为主线。

## 后续澄清：Stage 2 人工交互停点

用户确认 Stage 2 是主要人工交互停点，完整交互需要后续设计，当前先参考已有 HTML 至少输出模型供人工查看确认。已同步目标、决策、架构、执行计划和 roadmap；持久编辑仍在 M1，不能阻塞首份 HTML。

基于 `cffed459` 只读核对：

- `render_geometry_viewer.py` 已有内嵌 three.js/OrbitControls、离线 HTML、旋转/缩放/半透明/剖切/展开/选择/测量；`build_viewer_html` 目前消费 zones/surfaces/windows/roles，门/通用开口未接。
- `run_stage.py::_render_geometry_viewer` 从 Stage 2 几何写出 `manual_review/geometry_viewer.html`；`cmd_run` 要求阶段检查通过，flow 在抵达几何确认停点时生成。失败产物始终有查看入口尚未保证。
- `step_orchestrator.py` 的正式确认仍在 Stage 3 后，摘要绑定 2+3 和 kernel report，Stage 4 受确认策略控制；新设计的 Stage 2 停点未实现。迁移需核对源版本、确认失效与恢复，不能只改常量。

本次仅澄清并同步文档，未生成新的查看产物、修改业务代码或执行模型/EP。`git diff --check` 通过，6 份变更文档的 46 个本地链接路径存在；未跑 pytest，不改写前轮测试范围。
