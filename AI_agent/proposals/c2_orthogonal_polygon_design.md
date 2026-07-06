# C2 开工设计:正交多边形 footprint + 多平面立面(设计方案,待 Codex 审)

> **定位**:C2 档(正交多边形 L/U/凹凸 + 同朝向多平面立面)的**开工设计文档**——把 [capability/pipeline_0-5_capability_upgrade_suggestions.md](../capability/pipeline_0-5_capability_upgrade_suggestions.md) §C2 骨架 + Fable5 体检([logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md](../logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md) B1/C2/C3 节)的烤死假设清单,落成可分批执行的设计决策。**设计=本文档;执行=后续 Opus 主控按 §8 分批走 Codex**。2026-07-06 Fable5 出稿。
> **不变量 #6 合规声明**:全文所有决策 = schema 加槽位 + kernel 扩展 + 判卷/gt 同步,零架构推翻;每个决策标注它松动体检 C3 清单的哪一条烤死假设(标 `[C3#n]`)。
> **依赖事实**(体检已核,file:line 见报告):内核 `modelling.py`/`split_pairing.py` 本就 shapely polygon-native(L 形合成测试在跑),卡死的是**数据源**(schema 必填 x/y、prompt 只教矩形、correction 核只吸 bbox 角点)与**守卫/判卡层**;`interzone.py` 已非正交就绪可作参照。

---

## D1 · schema_version:从纸面承诺变真机制 [C3#9]

- `CorrectedGeometry` 根加 `schema_version: str = "1"`(缺省 "1" = 现行矩形制;本设计落地后新产物写 **"2"** = polygon-capable)。**版本语义 = 数据形状的能力声明,非代码版本**;bump 规则写进 A0:凡新增几何槽位(polygon/footprints/z_span…)必 bump。
- **分发规则**:确定性核、几何内核入口、gate① check 读它——`"1"` 走现行 bbox 路径(字节级行为不变);`"2"` 启用 D2/D3 路径。未知版本 → gate① `correction.schema_version_supported` INVARIANT fail(**拒绝静默降级**)。
- 与 `capability_profile` 的关系(体检 C3 揭示后者内核零感知):`schema_version` 描述**数据**、`capability_profile` 描述**运行档**;本批把 `capability_profile` 线程化进内核入口(`build_zone_volumes`/`split_pairing` 顶层),规则 = profile 允许的形状 ⊇ 数据声明的形状,否则 gate① fail。新 profile 值 `orthogonal_polygon`(rectangular 仍默认)。

## D2 · Cell.polygon:bbox 兼容的多边形槽位 [C3#4][C3#8][C3#10]

- `Cell` 加可选 `polygon: list[[x,y]]`(外环、CCW、首尾不重复、**v2 限正交边**)。
- **兼容关键设计:`x`/`y` 保留必填,语义降为"polygon 的 bbox 投影"**——polygon 在场时 x/y 必须等于其 bbox(gate① 校验一致性,不一致 INVARIANT fail),由 correction 生成端负责派生。这样全部 legacy 消费者(命名质心/envelope/区数 tripwire/`geometry_validator._cell_box`)零改动继续工作,内核优先吃 polygon。
- **确定性核升级**:轴聚类从"每 cell 4 个 bbox 值"改"收集全部 polygon 顶点坐标"(正交下仍是 x/y 两组一维问题,聚类/吸附算法本体不变);吸附后重派生 x/y;`MIN_EDGE_LENGTH` 守卫逐边应用;新增 polygon 合法性守卫(自交/退化/非 CCW/非正交边 → raise)。
- **prompt/skill**:1_correction 规则改为"房间优先拆多个矩形 cell,**房间本身不可拆时**才出 polygon"(骨架原则保留:多边形是兜底不是常态);pipeline.py:315 矩形指令同步改。
- `geometry_validator._cell_box` 改用与 `modelling._cell_polygon` 同一 helper(体检 C3#8:现 bbox 兜底在 polygon 在场时判错洞/叠)。

## D3 · per-floor footprint(C3 的预埋)[C3#3]

- `CorrectedGeometry` 加可选 `footprints: dict[floor_id, polygon]`;全局 `footprint_x/y` 保留、语义降为"全楼投影 bbox"(与 D2 同一兼容手法)。
- 确定性核三处改锚:跨层 reconcile(`_reconcile_cross_floor`)的 footprint 硬锚 → 改"各层 footprint 交集区内 mutual-nearest"(仅在重叠区做跨层身份合并,非重叠区各归各层);gap_close 的"吸到边界"→ 点到 per-floor polygon 边吸附;envelope 权威 bounds(`envelope.py`,现轴对齐 bbox)→ v2 先支持"per-facade 分段 bounds"归属到多边形对应边,超出即 conflict(完整多边形 envelope 仲裁留 C2 后期,先不阻塞)。
- **C2 阶段各层 footprint 仍相同**(退台是 C3);本槽位本批只落 schema+核的读取路径,让 C3 到来时零契约改动。

## D4 · 多平面立面与窗归翼 [C3#1][C3#2][C3#5]

- **reading schema 零改动**(重要简化,体检 B1 未言明、此处定死):立面仍按 N/S/E/W 出图,strokes 本就支持 polyline;分翼线索走既有 `dimensions[]`/描边/notes,不加新字段。reading 侧只动 guide/pen 词汇(外轮廓 polyline 描法、翼分界标注认读)。
- `Facade` Literal(reading/correction 共用的类型根)**保留为"朝向族"**,不扩枚举;`Window` 加可选 `facade_segment: {along_range:[a,b]} | segment_id`——由 **1_correction 的 A3 仲裁**据平面房间布局对位产出(窗归翼是判断活,归 LLM;几何落位仍确定性)。缺省(单平面立面)不填,完全向后兼容。
- `derive_facade_frame`(已 gt 锚定、未接线)升级为 **per-segment frame**:输入朝向+该朝向的外边界线段集(从 per-floor footprint 派生)→ 输出每段的 `base_world`。**接线顺序建议**:先按体检 A1-1 的中间态把单平面版本接成 gate① 交叉校验(C1 情形即可用),C2 批内再升 per-segment——两步都在本设计范围。
- `_find_parent_wall` 重写(修体检 C3#5 的"静默选最后 match"隐藏 bug,**此修对 C1 也是正确性修复,单独可提前**):同朝向候选墙集合 → 按"窗世界坐标落入墙段 span"唯一归属,歧义(跨两段/落缝上)→ kernel gate fail 而非静默;`_window_verts` 的 span 从"x 或 y 区间"改"沿宿主墙段参数化区间"(C4 的线段投影在正交情形先落半步)。

## D5 · 守卫与门(shapely 覆盖门提前落地)[C3#6→C3 期][C3#7]

- **覆盖完整性门 v2**:per-floor cell polygon 并集 ≡ per-floor footprint(差集>容差 → block);层间界面配对面并集 ≡ 相邻层 footprint 交集。`orthogonal_polygon` profile 下 block,`rectangular` 下维持现行;实现收敛到**单一 helper**,`kernel checks` 与内核主路径共用(体检 C3#7 双写病根一并治,by_floor 邻接的双写在本批收敛、z 区间驱动本身留 C3)。
- polygon 合法性(D2)/ footprint-cell 一致性(D3)/ 窗归属唯一性(D4)各配 INVARIANT;全部走既有 run_profile 分档 + parity 锁自动覆盖(M1 已建的机制,新 check 自动进 parity 测试范围)。

## D6 · 判卷 + gt 同步(硬前置,不是尾巴)[体检 C2 节]

- **gt schema v-next**:墙 = 线段集 `[(x1,y1),(x2,y2)]`(C2 仍轴对齐,但结构上任意线段就绪);footprint = polygon;立面 = per-朝向分段(段 along-range + 各段窗)。`gt_from_dxf` 天然支持折线,是升级主路径;sm24(已跑过的非方形 case,无 gt)= **首个真实锚,gt 补录排进 §8 批次**。
- **scorer**:平面墙关联从"(朝向,横坐标簇)"泛化为"(方向族,叉轴位置簇)"——对轴对齐线段集是纯重构非新算法;interval-set 分段机制原样保留;footprint 边界判定从 bbox 四边改 polygon 逐边。**立面判卷已是沿面局部坐标**(设计种子早定"沿面坐标对斜立面也成立"),多平面立面 = 每段一张判卷,复用现有单面逻辑。
- **判卷层 capability 感知**(体检 C2 节:"零准备,未定义行为"):scorer 读 gt/产物的形状声明,不支持的组合 → 显式 `NOT_APPLICABLE` sidecar(对齐内核的诚实姿态);`SCORER_SCHEMA` 随判定语义变更递增(既有纪律)。
- **明确不做**:§8b 的打分粒度问题(墙计数/比例制/Hungarian/ambiguous config)维持用户既定"Sonnet 4.6 之后单独设计",本设计只留槽不拍板。

## D7 · 明确不动的东西

IntakeOutput 11 字段(surface_specs 顶点数 4→N,誊写协议无感);下游 9 subagent;reading schema(见 D4);correction 永 image-blind;A1/A2 与 A3/A4 的确定性/判断分界;命名(墙 CCW 圈序 `Z01_W1` 本就为非矩形设计,零改);C3 的 z_span/切墙/带洞楼板(仅 D3 预埋槽位);C4 斜交(D4 的参数化 span 是半步预埋)。

## D8 · 交付序(Opus 主控按批走 Codex,每批独立可验收)

| 批 | 内容 | 依赖 | 验收 |
|---|---|---|---|
| B0 | `schema_version` 机制 + `capability_profile` 线程化进内核 + `_find_parent_wall` 唯一归属修复(C1 正确性)+ 覆盖门 helper 收敛双写 | 无 | 全量绿;v1 数据字节级行为不变(回归断言) |
| B1 | D2:Cell.polygon + bbox 一致性守卫 + 核顶点吸附 + polygon 合法性 raise + `_cell_box` 统一 | B0 | 手搓 L/凹形合成用例过内核 + InterZone 门 0 issue |
| B2 | D3:footprints 槽位 + 核三处改锚(同层不变形回归) | B1 | 同 footprint 多层回归字节不变 |
| B3 | D5:shapely 覆盖门 v2(orthogonal_polygon block) | B1 | 合成"漏一块/叠一块"负例被抓 |
| B4 | D6:gt schema v-next + scorer 线段化 + 判卷 capability 感知 + sm24 gt 补录(DXF) | 可与 B1-B3 并行 | 合成 gt 判卷全态 + sm24 gt 入库 |
| B5 | D4:facade_segment + per-segment derive_facade_frame 接线 + 窗归翼 A3 prose | B1,B4 | 立面窗世界落位 gt 校验(先 sm21 单平面回归,再合成双翼) |
| B6 | 0/1 skill 词汇(外轮廓 polyline/翼分界)+ 端到端:新增 1 个 L 形真实图纸 case(sm2x)anchor | B1-B5 | 新 case 三层门走通 + 判卷有分 |
| (并行) | 再拓扑 P0 探针:矩形 case 上非阻塞 shapely 覆盖报告(与 B3 同一 helper,advisory 形态) | B3 helper | 报告落 run 目录(体检 B3 建议的双线收益) |

每批纪律照旧:Claude(Opus)出批简报 → Codex 审 → 执行 → 复核;确定性件先合成用例后真图;零 golden 改动逐批断言。

## D9 · 风险与开放问题(审阅重点)

1. D2 的"x/y=派生 bbox"是否有消费者把 x/y 当**权威几何**参与运算而非提示(若有,polygon 在场时会算错——审阅时全量清点 `c.x`/`c.y` 消费点)。
2. D3 跨层 reconcile 改锚后,现行 sm20/21(全层同 footprint)行为是否严格不变(交集=全集时应退化为现行为——需回归断言)。
3. D4 `facade_segment` 放 Window(consumer 侧)vs 放 correction 产物的独立 facade 表(生产侧)哪个更稳。
4. 覆盖门容差怎么定(建议复用 `MIN_EDGE_LENGTH` 量级起步,进 correction.yaml,A0 登记——吸取 D2-1 漂移教训,禁裸字面量)。
5. B0 的 `_find_parent_wall` 修复改变 C1 潜在行为(现"最后 match"若恰好错着用,修复=行为变化)——执行前对现有 anchors 预扫归属唯一性。

---

## D10 · 裁决(2026-07-06,Codex 审 APPROVE-WITH-CHANGES,findings 全采纳,定案;细节以 `logs/reviews/verdict/2026-07-06_c2_design_review.md` 为准,与上文冲突处 verdict 胜)

1. **D2 扩为 polygon-first 消费者清单**:不止 bbox 兼容——确定性核/validators/audit 签名/correction scorer 逐点改吃 polygon(verdict 列了全量消费点),x/y=派生 bbox 仅供"提示级"消费者。
2. **D4 定案 = 生产侧 `facade_segments` 确定性表 + `Window.facade_segment_id` 引用**(替代窗上挂几何段;D9#3 关闭)。
3. **D3 加显式字节兼容路径**:各层 footprint 相同 → 严格退化为现行为(回归断言)。
4. **批次依赖修正**:B3 依赖 B2;B5 依赖 B2+B4;B0 的 profile 线程化须含 `run_stage.py` 与几何 builder 全部入口。
5. **D6 范围补齐**:correction_score + sidecar/render 消费者一并线段化;不支持组合显式 NOT_APPLICABLE。
6. **覆盖门容差 = 独立面积容差配置**(进 correction.yaml+A0 登记),不复用线性 min-edge 常数。
7. **预扫结论在案**:28 份 correction 产物 parent-wall 归属 0 歧义(B0 修复行为安全);sm24 一份 raw correction 现行 attachment 已失败=既有事实非本设计引入。
