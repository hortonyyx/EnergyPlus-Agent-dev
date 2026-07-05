# 0–5 管线各环节 capability 升级建议（活文档）

> **定位**：记录 0–5 管线**六个子环节**各自的 capability（能力/质量）升级建议，供后续依次升级。**不是硬伤清单**——硬伤走 [review/request/2026-06-10_pipeline_0-5_full_audit_request.md](../logs/reviews/request/2026-06-10_pipeline_0-5_full_audit_request.md) → review 闭环。
>
> **状态（2026-06-10）**：骨架 + 当前已知建议（Opus 起草）。明天 Fable 5 做完整体检时，顺手发现的 capability 想法往这里加。**这些升级先不实施**，按用户路线（§ 路线图）在 test_baseline + 国产 VLM 接通后，**依次提升建筑复杂度时**再逐项落地。
>
> 权威接线见 [pipeline_stage_contracts.md](../architecture/pipeline_stage_contracts.md)。术语：识图=0_reading / 校正=1_correction / 建模=2_modelling / 切配=3_split_pairing / 物理=4_mep / 装配=5_intakeoutput。

---

## 0_reading（识图）

- **跨画法/风格泛化**：识图库（`reading_guide.md`）扩充——墙的多种画法、家具/铺装/楼梯/轴网符号长相，提升对杂乱真实图的 keep-set 分类与杂物排除（plan.md B1.5.b / B7）。
- **全自动 VLM**：`llm.yaml:intake_reading` 段预留未接；pivot 后接国产 VLM API（见路线图）。
- **尺寸链自洽校验**：识图阶段对 dimension chain 做和校验（子链 vs 总链），不自洽时标 `null` + note，而非硬填（sm23 已暴露内部子链 ~100–200mm 偏差）。

## 1_correction（校正，LLM）

- **稳定性**（2026-06-10 已加重试 + 窗自检兜底，commit `fd3d4bf`）：进一步可加——结构化输出约束 / 更细的自检（区数 vs testdata、楼层 z-stack 连续性、外包闭合）。
- **多层 z-stack 合成**：2 层已验证，**3 层（sm20）2026-06-11 audit 实证通过**（0/3.6/7.2 连续、各层窗 z 落位正确、一发即中）；facade_local→world 的逐层 z 偏移仍是易错点（z 连续性确定性守卫属硬伤修复，见 [audit review H2](../logs/reviews/verdict/2026-06-11_pipeline_0-5_full_audit_review.md)）。
- **仲裁/先验丰富度**：A3 仲裁 + A4 几何先验目前偏薄，复杂图（凹形/退台）下需要更强的常识仲裁。

## 2_modelling（建模·几何，确定性）

- **非矩形 footprint**：当前矩形 cell；L/U 形、凹凸异型需 cell 多边形 + straight-skeleton（plan.md B5，[geometry_first_zonification.md](../proposals/geometry_first_zonification.md)）。**复杂度升级路径详见下方 §0–3 路径骨架（C2 档）**。
- **zonification 粒度**：sm23 暴露——走廊被横墙切成多段、房间粗合并。怎么定 zone 边界（贴房间 vs 贴热区）是 capability 主线（[recognition_modeling_capability.md](../capability/recognition_modeling_capability.md)）。

## 3_split_pairing（切配·仿真，确定性）

- **覆盖完整性**：InterZone 门的覆盖洞盲区（两侧都标 Outdoors 的"内部边界"）——长期解走 shapely（plan.md B1.5.g 残留、B5）；z 向子类已由 2026-06-11 audit 修复确定性兜住，x/y 向建议提前到 C2 档落地（见下方骨架接缝④）。
- **非矩形切配**：跨层不同 footprint 的面切分（退台/挑空，plan.md B6）。**复杂度升级路径详见下方 §0–3 路径骨架（C3 档:墙竖向 z-cut + 带洞楼板分解）**。

## 4_mep（物理撰写，LLM）

- **schedule 完整性**（2026-06-10 已加确定性门 + authoring 硬化，commit `04e7dbe`）：先验库 `mep.md` 目前是 office 单一种子；扩成多建筑类型（学校/商业/住宅）的 MEP 先验库。
- **构造/材料真实性**：当前占位构造（Default_*）；接真实构造库 + 按气候区选型。
- **材料质量跨 draw 波动**（2026-06-11 audit 顺手发现）：同一 prompt 下 sm21 某次 draw 全配 no-mass 材料 → EP "building has no thermal mass" warning，sm20 同期正常。可在 authoring.md 加"外墙/楼板至少一层有质量材料"硬规则，或入契约校验。
- **数值合理性**（2026-06-11 audit 顺手发现）：sm20 的 OFFICE_ACTIVITY 活动量 schedule 数值超出 70–1000 W/person 典型区间（19 条 EP warning）；可在 mep.md 先验里给典型值表。
- **仿真控制默认值**（2026-06-11 audit 顺手发现）：4_mep 不产 design days 但 SimulationControl 默认要求 design-day 仿真（EP warning）；地温缺省走 EP 默认 18 °C。可补 authoring 默认块。
- **HVAC 升级**：当前 IdealLoads；后续可扩真实系统（plan.md 远期）。

## 5_intakeoutput（装配，确定性）

- **契约校验扩展**：`validate_contract` 现查 construction 引用；可扩到 schedule/material 引用闭包的全量校验。
- 目前较稳，升级优先级低。

---

## 0–3 建筑复杂度升级路径骨架（主战场，2026-06-11 起草，Fable 5）

> **定位**：0_reading→3_split_pairing 是这套系统后续升级的主战场。本节是**路径骨架**——按复杂度阶梯 C1→C5 排出每一档要解锁的几何能力、四个环节各自要动什么、契约接缝在哪。每档落地时再展开成独立设计文档。
>
> **三条总原则（升级中不变的东西）**：
> 1. **分工线不动**：LLM 只做 感知(0)+校正判断(1)；代码做 所有几何(2+3)。复杂度升级 = 同时升"LLM 能看懂/校正什么"和"内核能确定性构造什么"，但绝不把几何判断退回给 LLM。
> 2. **内核先行**：每一档先用**手搓 CorrectedGeometry 合成用例**把内核(2+3)升级好、对标 InterZone 门 0 issue（确定性、可独立测，不依赖 LLM/识图），再升 0/1 让真实图纸流进来。0–5 重构(Step 2)已验证此法有效。
> 3. **守卫与档位同步**：每档解锁新几何的同时,加上该档的确定性守卫与门检查(2026-06-11 audit 的教训:契约只写 prose=没有契约)。

### 阶梯总览

| 档 | 解锁几何 | 0_reading | 1_correction(schema/校正) | 2_modelling | 3_split_pairing | 状态 |
|---|---|---|---|---|---|---|
| **C1** | 正交矩形 cell、单一外包矩形、立面每向单平面 | ✅ | ✅ | ✅ | ✅ | **当前已稳**(sm20/21/22/23) |
| **C2** | **正交多边形**(L/U/凹凸 footprint)+ **立面多平面**(同向外墙不共面) | 外轮廓折线/分翼标注 | cell 多边形 + per-floor footprint + 窗归翼仲裁 | 多边形 cell 守卫 | 覆盖完整性门(shapely) | 内核已半就绪 |
| **C3** | **竖向复杂**:退台/露台、**挑空/中庭/跨层 zone**、夹层 | 剖面图输入 + 平面开洞标注 | per-cell z 区间(打破"层=统一z") | 跨层棱柱 ZoneVolume | **墙的竖向切配**(z-cut)+ 带洞楼板分解 | 退台已就绪;挑空=最大内核改造 |
| **C4** | **斜交墙**(非轴对齐,仍直墙棱柱) | 斜向尺寸链/角度 | 核:旋转系吸附 | 窗挂墙投影化 | (shapely 本就支持) | 核+窗挂载是主工作 |
| **C5** | 异形远期:曲墙、坡屋顶、非棱柱体量 | — | — | — | — | 远期,不展开 |

### C2 — 正交多边形 + 多平面立面（第一战役,建议下一档就打这个）

**为什么先打**:L/U 形是真实办公楼最常见的非矩形;且**内核已经半就绪**——`modelling.py` 是 shapely 多边形原生(`_cell_polygon` 已优先读 cell 的 `polygon` 字段,矩形只是特例),`split_pairing` 的墙配对(boundary.intersection)和楼板配对(polygon.intersection)对任意多边形本来就成立。缺口集中在 0/1 和守卫:

- **1_correction schema**(接缝①,最小演化):`Cell` 增可选 `polygon: [[x,y],…]`(有则优先,无则退回 x/y 矩形——`extra="allow"` 已前向兼容);`footprint_x/y` 单矩形 → **per-floor footprint 多边形**(退台在 C3 也要用它)。1_correction 文档教 LLM 何时必须出多边形(房间本身 L 形)vs 何时拆成多个矩形 cell(优先拆,多边形兜底)。
- **确定性核**:现在只吸 `c.x/c.y` 四个值——升级为**收集全部多边形顶点坐标进轴聚类**(正交前提下仍是 x/y 两组一维问题,算法不变);gap_close 的"footprint 边界"从全局矩形改成 per-floor footprint 多边形(点到边吸附)。
- **多平面立面**(同一朝向不共面,L 形天然出现):内核侧**已经能干**——`_find_parent_wall` 按"窗所属 room + 朝向 + 外法向"找墙,room 定了平面就定了(2026-06-11 H4 修复后法向匹配可靠)。真正的难点在 **0/1**:南立面图上前翼和退进翼的窗混在一张图里,**窗归翼**(哪扇窗属于哪个进深的房间)是 A3 仲裁新课题——0_reading 需要给立面分段/进深线索(翼分界标注),1_correction 用平面房间布局做对位仲裁。
- **守卫同步**:cell 多边形合法性(自交/退化/非 CCW → raise);**shapely 覆盖完整性门落地**(B5 计划提前到这档——非矩形后"漏一块墙/楼板"靠肉眼查不住了):per-floor cell 并集 vs footprint、层间界面 interzone 配对面并集 vs footprint 交集,差集非空即 issue。
- **测试锚**:手搓 L 形/凹形合成用例打内核 → 新增 1 个 L 形真实图纸 case(sm2x)端到端。

### C3 — 竖向复杂:退台 / 挑空 / 跨层 zone（第二战役,内核最大改造在这档）

- **退台/露台**(易,先收):切配对"上层未覆盖 → Roof、悬挑楼板 → ext_floor"**已就绪**(sm20-shaped 测试在跑);缺的是真实 case 验证 + per-floor footprint(C2 带来)+ 露台的 4_mep 语义(上人屋面构造,不在 0–3)。
- **挑空/中庭/跨层 zone**(难,本档主菜):
  - **schema**(接缝②,最大一次契约演化):打破"楼层 = 统一 z"——`Cell` 增可选 `z_span: [zf, zt]`(缺省继承所在层),挑空 = 一个 cell 的 z_span 跨两层;平面上"开洞/上空"标注归这个 cell。
  - **2_modelling**:`ZoneVolume` 本来就带独立 zf/zt,改动小;`build_zone_volumes` 的 z-stack 守卫要从"层连续"升级为"体块 z 区间合法性"。
  - **3_split_pairing(主改造)**:墙配对目前**按 by_floor 分组只配同层**——跨层 zone 的墙必须改为 **z 区间重叠驱动**:两体块边界线段相交 × z 区间求交,墙在 z 断点处竖向切开(双层高墙 vs 单层邻居 → 下半配对/上半另配或外墙)。**切配第一次从"只切楼板"扩到"也切墙"**——这是本档的核心工程,先用合成用例对标门写透。
  - **带洞楼板**:中庭楼板 = 带内环多边形;EP 面不支持洞 → 加**简单多边形分解**步骤(`_ring_verts` 现在只取 exterior,直接吃带洞多边形会出错几何——升级时同步加"polygon 有 interiors → 必须先分解"的守卫)。
  - **0_reading**:新增 `image_kind: section`(剖面图)——挑空的 z 证据主要在剖面;平面上开洞填充/“上空”文字进 pen/词汇库。
- **测试锚**:合成用例(双层高大堂 + 单层邻居;中庭带洞楼板)→ 真实图纸 case。

### C4 — 斜交墙（仍直墙棱柱,非轴对齐）

- **确定性核**(主工作):轴吸附从 x/y 两组一维 → **按方向分簇**(墙段方向角聚类,容差内归同向)后在各向的法向/切向做一维吸附;栅格语义改"沿墙向/法向栅格"。
- **2_modelling 窗挂载**:`_find_parent_wall`/`_window_verts` 还残留轴对齐假设(常数 x/y 平面判定、span 是 x 或 y 区间)→ 改为**线段投影**:窗 span 定义为沿宿主墙段的弧长区间,平面放置用墙段参数化。`Window.facade` 枚举(N/S/E/W)在斜墙下退化 → schema 演化为 `wall_ref` 或方向角。
- **3_split_pairing**:shapely 的 boundary/polygon 运算本就方向无关,预期改动最小;门的法向/共面检查已是任意朝向。
- **0/1**:斜向尺寸链、角度标注的识别与校正先验。

### 接缝清单（跨档共用,动哪里要同步什么）

| 接缝 | 内容 | 影响档 |
|---|---|---|
| ① `CorrectedGeometry` schema 演化 | cell.polygon / per-floor footprint / cell.z_span / window.wall_ref;每次演化 = schema + 1_correction 文档 + 核 + draw 级校验**四处同步**(audit 教训);`extra="allow"` 保证旧 case 兼容,建议加 `schema_version` 字段 | C2/C3/C4 |
| ② 确定性核算法 | 顶点级吸附(C2)→ z 区间(C3)→ 旋转系(C4);容差全部进 correction.yaml,不硬编码 | 全部 |
| ③ 切配内核 | 墙竖向 z-cut(C3)+ 带洞分解(C3);楼板/墙配对算法本体 shapely 已通用 | C3 |
| ④ 门与守卫 | shapely 覆盖完整性门(C2 落地,全档受益);多边形合法性守卫(C2);z 区间守卫升级(C3);fenestration 门(audit M2 遗留,复杂立面后必要性升高) | 全部 |
| ⑤ 0_reading 输入类型 | 剖面图 image_kind(C3);立面分翼/进深标注(C2);角度/斜向尺寸(C4) | C2/C3/C4 |

### 节奏建议

**C2 → C3(退台先收、挑空后攻) → C4**,每档节奏固定:**合成用例升内核(确定性,先行)→ schema+correction 文档演化 → 真实图纸 anchor case → 守卫/门补齐 → 入 test_baseline**。C2 内核现成度最高、真实需求最广,test_baseline + VLM 接通后建议直接开 C2。

## 路线图锚点（用户定，2026-06-10）

1. Fable 5 完整体检 0–5（找硬伤）→ 修硬伤。
2. 拿 **sm20 + sm21** 两个干净 anchor → 建 **test_baseline**。
3. 接**国产 VLM API** 做一套全流程（0_reading 自动化）。
4. **依次提升建筑复杂度**（矩形→非矩形→退台/挑空→规范化绘图），每升一档**强化对应的 0–5 环节能力**——本文档的建议在此阶段逐项落地。

详见 [../plan.md](../plan.md) 阶段 3 (B5–B7) + 远期。
