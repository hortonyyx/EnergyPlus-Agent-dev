# C2 收官设计全面对抗审

Date: 2026-07-10
Object: AI_agent/proposals/c2_full_unlock_design.md
Baseline: AI_agent/proposals/c2_orthogonal_polygon_design.md D1–D10
Verdict: **REWORK**

Finding count: **16**（BLOCKER 8 / HIGH 6 / MEDIUM 2）。

本审只读本地工作树完成 A/B 两路。相关现状回归：

    pytest -q tests/test_c2_b0.py tests/test_c2_b1_cell_polygon.py \
      tests/test_c2_b1_winding.py tests/test_gt_from_dxf.py \
      tests/test_reading_score.py tests/test_elevation_score.py \
      tests/test_render_grade.py
    => 89 passed, 18 warnings

方向判断：视图 != 面、由 footprint 确定性派生立面段、未知数据不靠 prior 发明，这三条方向成立；但当前稿不能作为 B2–B6 的执行规格。阻断点集中在：E1.4 尚未建立从 reading local 坐标到确定性段归属的完整契约，E2 把“立面不可见”误等同于“所有证据不可见”，E3 与已定 envelope 权威规则没有按 claim type 解开，以及 B4 所假定的 gt/scorer/render 能力在代码中并不存在。

## A 路：设计对抗审

### A-01 — BLOCKER — E1 的 1D skyline 仅在窄域成立，口字形与“C4 零重写”超出既有契约

E1.2 的“同朝向、同高度、正交、外部正投影、实体不透明、简单 polygon”模型下，按 along 区间取最近 depth 是正确的；L/U 的主直觉也成立。问题是设计把这个结论外推到了当前契约没有表达的形状：

- Cell.polygon/D2 只有单一 exterior ring；D7 又把带洞楼板留在 C3。真正的口字形/中庭需要 interior ring（或 multipolygon/void），不能由一个简单 footprint ring 表达；D5 的“cell union == footprint”还会把中庭洞判成 coverage hole。
- E1.2/E2.4 声称任意方向与 C4 “零重写”，但 C4 的权威背景明确还要把 Facade 演化为 wall_ref/方向角并把窗挂墙参数化；只能说 interval-sweep 核心可复用，不能说 C4 零重写。
- 同深重叠、共线相接端点、多 ring、断开体块、重复边均未规定。有效简单 polygon 中同深重叠通常应是不变量错误，而不是任意选赢家。

建议修法：二选一并写死。

1. C2 明确只支持“无洞、单连通、等高、正交简单 footprint + 四个 cardinal 正投影视图”，删去本轮口字形与 C4 零重写承诺；sm27 移回 C3/带洞设计。
2. 若口字形必须属于本轮，则先扩 footprint/gt/cell-union 契约为带 interior rings 的 Polygon，并补 hole winding、coverage、surface 分解、visibility 与 gt 提取设计；这已不是当前“收官增补”的工作量。

无论选哪条，visibility 纯函数都须定义 depth 符号、半开区间端点、同深 tie=INVARIANT、数值 epsilon 与反向/旋转 ring 回归。

### A-02 — BLOCKER — E1.4 对 D10#2 的修订不成立到当前宣称的范围

这是对定案的显式冲突：D4 原文把窗归段交给 A3；D10#2/原审结论把段几何收归确定性表，但仍允许 LLM/A3 从确定性 id 中选择。E1.4 改成“确定性归属为主 + A3 例外”。这个缩窄方向可以成立，但当前稿跳过了两个仍属判断/校正的问题：

- 现有 derive_facade_frame() 只是 gate① cross-check；pipeline.py 仍明确要求 1_correction LLM 把 elevation image-local span 转成 world span。确定性核拿到的已经是 A1/A3 处理后的 Window.span，并没有一个可信、类型化、可独立重放的 local→world transform 产物。
- 段只解决 depth/墙面；当前内核仍靠 Window.room 找具体宿主墙。一个 footprint segment 可以跨多个房间，along 坐标不能替代 room identity 仲裁。

建议修法：把 D10#2 的修订缩成以下可证明版本：

> facade segment 几何、可见区间及“已是 world-frame 的窗口应引用哪个 segment”由确定性代码产生；窗口的 world span、floor、room identity 仍按 A1/A3 契约产生。仅当窗口完整 span 严格落入唯一 visible interval，且其 room 的 exterior boundary 属于同一 segment 时自动写 facade_segment_id；跨边界、零/多候选、room 不符、落入隐藏区一律 conflict，不按中心点猜。

若目标是连 local→world 也确定性化，须另行定义受信 FacadeViewFrame（标定来源、origin/scale/sign/mirror、source stroke ids、置信/冲突）并先接成生产变换；不能用当前 flag-only cross-check 代替。修订前，D10#2 的 A3 责任不能整体删除。

### A-03 — BLOCKER — E2 把“外部立面不可见”错误地当成“窗口证据不存在”

sm26 的内翼窗验收要求“系统不得产出、判卷 NA”，但当前数据链的窗口并不只来自立面：gt_from_dxf._plan_openings() 从平面 INSERT 提取位置/宽度，再与立面匹配高度；0_reading/correction 也同时读取 plan 与 elevation window strokes。U 形内壁窗通常会在平面图/DXF 中可见。若 plan 已给出它，模型产出该窗不是“发明”，把它判 NA 反而是在抹掉已有证据。

建议修法：把 coverage 从“segment 是否被某张 elevation 看见”改成证据通道 × 属性矩阵，例如：

- plan 可观测：wall/segment identity、along span、width；
- elevation 可观测：sill/head、立面外观；
- 两者均缺：opening existence/geometry 才能记 unknown。

sm26 必须由主控明确：内翼窗是否画在 plan/DXF。若画了，应验收“识别 span/segment，但 z 证据缺失并显式 unresolved”；若要验收整窗 NA，测试图须保证 plan、局部图、标注等所有允许通道都没有该窗证据。

### A-04 — HIGH — segment 级三态不足以支撑诚实 NA，且存在 miss laundering

coverage ∈ observed|partially_observed|unobserved 挂在整段上，无法回答窗口落在 partially_observed 段的可见部分还是隐藏部分；跨 visible/hidden 边界的窗也没有政策。更严重的是，“实际收到的视图集”若从 reading 输出反推，reader 漏产/错标一张已提供的图就会把本应是 miss 的对象降为 NA。

建议修法：

- 输入视图清单必须是 reading 前生成、不可由被测产品修改的 case/run manifest；“源图已提供但 reader 漏读”是 no-data/miss，不是 unobserved。
- applicability 按 opening 的完整 along interval（必要时按属性）计算，输出 applicable | partially_applicable | not_applicable + reason/source-view ids；不得只看 segment 总状态或窗口中心。
- judge 用 gt footprint + 受信输入 manifest 独立重算，绝不信产品的 facade_coverage.json；sidecar 记录 helper version、manifest hash、gt schema/hash 与各 denominator。
- 分开两类政策：coverage 计算失败/账本缺失/账本与几何不一致是 INVARIANT；“账本证明某处确实无证据”才是 WARN/NA。无窗建筑合法不能推出“coverage 机制失败也全档 warn”。
- 产品契约要区分“observed zero windows”和“unknown fenestration”；仅靠 windows=[] + 带外 WARN 会让下游把未知永久当成实心墙真值。

### A-05 — BLOCKER — E3 未解开与既有 envelope 权威定案的冲突

2026-06-23 已 ratify 的规则是墙厚量级内“立面外包 > 平面外包”，现 envelope.py 也以 facade-derived authoritative bounds 为权威。E3.1 又说“平面多边形 = 形状权威；立面 = bbox 佐证”，按字面是反转；E3.2 随后又说沿用现行吸收，二者互相冲突。

这可以通过 claim-type 分权化解，但稿中没有写：立面 overall span 只提供投影 bbox，不能证明 notch depth；分段宽度也只能约束投影端点，不能天然给出某条边的 normal/depth 坐标。因此“完整多边形逐边仲裁”名实不符。

建议修法：补一张权威矩阵并保持 6.23 定案：

- topology/凹凸关系/edge incidence/notch depth：plan 尺寸链权威；
- 全楼 x/y 投影外包 bounds：满足现有双证据与 0.30 m 门时 facade overall 权威；
- segment along 端点：只有明确翼分界 dimension 才可佐证/修正；
- elevation 没有 cross-axis depth 证据时不得移动 notch depth；
- 同 claim 高权威冲突继续进 A3，不把“佐证”静默升级为动作。

并将 E3 改名为“polygon bbox + 有证据端点仲裁”，或补齐真正逐边证据模型后再称“完整仲裁”。

### A-06 — HIGH — E3 没有定义可保持拓扑的 polygon 变形

现核对 polygon cell 明确 unsupported，因为旧 bbox 挪边会造成 x/y 与 polygon 不一致。E3 只写“贴边 cell 边吸到对应边”，没有回答：移动一个 polygon 边端点时如何同步相邻边、共享 cell 边、footprint 顶点、窗 span 与 bbox 投影。只挪某条边的两个端点可能把相邻正交边拉成斜边；逐 cell 独立挪又可能造洞/叠。

建议修法：B2b 先出独立细稿，定义基于共享轴/vertex graph 的原子 transform：证据坐标→受影响 footprint axis-line→所有 incident footprint/cell vertices→重派生 bbox→窗/segment ref 重验。变形前检查跨轴、最小边、winding、自交、segment 消失；变形后以 B3 的 polygon coverage、共享边一致、窗口宿主唯一性做硬门；任一失败整轴/整 transaction 回滚并记 conflict。B2b 因此必须依赖 B3，而非只依赖 B2。

### A-07 — HIGH — segment id、frame 与边界归属尚不具确定性契约

{D}{k} 在多楼层会冲突；仅按 along 排序没有 depth/geometry tie-break；edge_ref=polygon 边索引会受 ring 起点影响。当前 B1 只规范 winding，保留起点，并不提供 canonical footprint edge index。另一个混淆是现有 FacadeWorldFrame 同时含全视图的 along origin 与唯一 base plane，而多段后应拆为“视图投影 frame”和“墙段 frame”；否则 North/West 反号、mirrored 与 segment-local 原点容易二次翻转。

建议修法：冻结类型化表，至少含：

    segment_id, floor_id, facade_family, p1, p2, normal,
    world_along_interval, depth, visible_intervals,
    source_footprint_version/fingerprint

id 用 floor namespace + canonical geometry fingerprint/rank；排序至少 (along_lo, along_hi, depth, canonical_edge_key)，端点采用明确半开约定。另设 ViewProjectionFrame（整张图 local→world along）与 FacadeSegmentFrame（p1/p2/base/normal）；矩形单段回归分别验证 South/East 正号、North/West 反号及 mirror。

### A-08 — MEDIUM — “虚线不读为窗”缺少可审计表示，直接写 pen 负例会静默丢证据

现 Stroke 没有 line_style/visibility 字段。仅在 guide 写“虚线 hidden，不出 window stroke”，既不能区分隐藏构件、中心线、上方构件等不同虚线语义，也无法让后续知道 VLM 看见但有意排除了什么。

建议修法：不必扩 Facade Literal，但应给 observation 增可选 line_style/visibility，或至少要求在 uncaptured[] 写 {source_id, kind: hidden_window_candidate, reason}。hidden observation 不进入实体 Window，但保留给 conflict/audit；补实线可见、虚线隐藏、虚线误读、同位置实虚重叠四类负例。

## B 路：落地可行性审

### 代码现实总对账

| 设计假设 | 当前代码现实 | 结论 |
|---|---|---|
| Facade 可保留为视图/朝向族 | reading Facade 与 correction Window.facade 均为 N/S/E/W Literal | 可保留，但它不能标识具体墙段或补交庭院视图 |
| B2 已有 per-floor footprint 接缝 | CorrectedGeometry 只有全局 footprint_x/y；Floor 无 id/footprint | 未落，不能“原样机械执行” |
| B5 可直接填 facade_segment_id | schema 无 facade_segments/facade_segment_id；window 仍靠 room+facade+span | 需 schema + 核 + validator + serializer 联动 |
| 内核已 polygon-native | cell surface/split-pairing 主体确为 shapely polygon-native | 仅体块/切配成立；窗挂载、footprint、coverage、frame 仍轴向/bbox |
| E3 可沿现 envelope 逐边泛化 | envelope.py 只解 x/y bounds；core 遇任一 polygon cell 即 unsupported | 不是局部循环改造，需要新变形算法 |
| gt/DXF 天然支持折线 | gt schema 仍 W_m/D_m + zones[].rect_m；提取器用 LINE bbox + band×partition | 假设不成立 |
| scorer/render 可小改支持 C2 | plan scorer、elevation scorer、policy、render_grade 全按 W/D、四边、单 facade span | B4 是独立大设计/多批施工 |
| 两条运行路径可共享产物 | run_pipeline 传 authoritative envelope/reading views；run_stage core/check 均未传 | 已存在行为漂移，新增 coverage 不能再双接线 |

### B-01 — BLOCKER — 新槽位没有 schema/version 方案，直接违反 D1

D1 定案写明“新增 polygon/footprints/z_span 等几何槽位必须 bump”。B1 已发布 correction schema "2"；B2 再加 footprints、B5 再加 facade_segments/Window.facade_segment_id，当前稿却没有新版本。现代码只注册 v1/v2，而且 pipeline.py、deterministic.py、geometry_validator.py、modelling.py 多处硬编码“polygon 必须恰好 version == 2”。若按 D1 bump 到 v3，现有 polygon 会被这些检查反杀；若继续写 v2，则是在静默改变已发布契约。extra="allow" 只会让未知字段无类型地穿过，并不等于支持。

建议修法：在 B2 前冻结一个新的 correction schema（建议一次性定义 C2 剩余可选槽位的 v3），并：

- 定义 Floor.id 或明确 footprint map 只能键入唯一 Floor.name；更稳的是把 footprint 直接放到 Floor。
- 类型化 footprint ring、facade segment、window ref 与 compatibility defaults。
- capability 从“版本恰等于 2”改为 feature/shape 声明检查，使 v3 仍可含 polygon。
- 未知未来版本继续 fail closed；v1/v2 读取行为不变。
- gt 的整数 schema_version: 2 是另一条答案契约，必须独立命名/演化，不能与 correction "2" 混用。

### B-02 — HIGH — B2 涉及的实际消费者远超“三处改锚”，且两条生产路径已不等价

当前 deterministic core 的 cross-floor anchors、footprint snap、gap-close 全读全局 footprint_x/y；geometry_validator.check_coverage() 仍构造 bbox box()；命名 quadrant 也用全局 bbox。更关键的是 run_pipeline 会提取/传入 authoritative envelope 与 reading views，而 scripts/tool_scripts/run_stage.py::_draw_correction() 直接调用 core，不传 envelope，随后 check 也不传 reading views。§5.8 parity 目前只锁检查集合，锁不住 core 输入。

建议修法：B2 先建单一 floor_footprint(geom, floor)/polygon helper，覆盖 core、validator、modelling naming、audit/signature、render 与 judge adapter；相同 footprint 必须走显式 legacy branch。run_pipeline 与 run_stage 都调用同一个 correction-finalize 函数，由它一次性完成 envelope extraction 输入解析、core、coverage 产物和 check，新增 parity 测试比较 snapped artifact/audit，而不只比较 check ids。B2 工作量属“需细稿的大批”，不是“原样执行”。

### B-03 — BLOCKER — gt_from_dxf “天然支持折线”与代码事实相反

当前工具：

- _plan_footprints() 对 LINE[layer=='WALL'] 取 bbox；
- _zones() 用 horizontal bands × vertical partitions 生成 rect_m；
- _facade_of() 只认 bbox 四边；
- _FLOOR_OF、_ROLES 固定两层 sm21；
- _self_check() 用 sum(rect areas) == W*D；
- gt README/唯一真实 gt 也只有 footprint.W_m/D_m 与 zones[].rect_m，且没有 Pydantic/JSON Schema validator。

它既不能重建 L/U footprint，也不能识别内凹 perimeter window，更不能生成 segment id/visibility。source.dxf 中存在折线能力不等于当前 extractor 消费了折线。

建议修法：B4 前半必须先成为独立的 gt-v-next 设计/批次：polygon/holes、zone polygon、per-floor footprint、facade segments、opening segment ref、source entity handles 与 schema validator；DXF 侧用闭合 LWPOLYLINE/LINE network polygonize + 拓扑验证，floor/view/role 配置数据化，窗口按最近合法 polygon boundary segment 归属，不再按 bbox 四边。先用合成 L/U DXF 证明 round-trip/self-check，再接 sm25/26；render_gt/overlay 也一并升级。

### B-04 — BLOCKER — B4 把 scorer、renderer、policy 与 NA 低估为一个可并行批

当前判卷链的矩形假设是端到端的：

- reading_score 从 rect_m 派墙、用 W/D 排除四边并把窗分 N/S/E/W bbox lane；
- correction_score 虽已从 cell polygon 抽边，仍用 gt W/D、四边 boundary 与单 facade window span；
- elevation_score 每朝向只有一个 span_limit，无 segment/applicability status；
- score_policy 只统计 complete/within/miss/extra/no_data，NA 没有独立 denominator；
- render_grade 画矩形 gt zones、矩形 footprint、四个整宽立面，未知 not_applicable 画法；
- run_stage._score_attempt_output() 没有 capability 参数；sidecar 缓存身份也不含 gt hash/schema、capability 或 view-manifest hash。

建议修法：B4 至少拆为 gt schema/extractor、plan segment scorer、elevation segment+applicability scorer/policy、sidecar+renderer 四个可验收子批。先定义 WallSegment 的二维端点/方向/interval-set 关联与 polygon boundary records，再定义 NOT_APPLICABLE(unobserved) 的机读结构、计数和灰/纹理画法。sidecar 身份增加 gt hash/schema、capability、view manifest hash、visibility helper version 并 bump SCORER_SCHEMA。不支持组合必须在评分入口显式 NA/拒绝，不能先产矩形分再事后贴 capability 标签。

### B-05 — HIGH — facade_segment_id 尚不能驱动当前 window attachment

当前 schema 无 segment ref；core 窗钳制用 parent cell bbox，check_windows_on_wall() 也只是 bbox span；_find_parent_wall() 依赖 room+facade+span 找具体 Outdoors wall，_window_verts() 仍按 x/y 轴构造。split_pairing 的 polygon 主路径可复用，但不会替窗口建立 footprint segment identity。仅给 Window 加一个 id，内核仍可能钳错、挂错或因 room 不一致失败。

建议修法：B5 明确联动：

- deterministic resolver 先验证 window floor/room/segment 一致；
- clamp 到 segment 的真实参数区间，不再 clamp 到 cell bbox；
- parent wall 候选同时满足 room、segment plane/normal、完整 span，segment id 不替代 room；
- _window_verts() 以宿主墙 p1→p2 参数化（C2 可先轴向实现，但接口按线段）；
- correction validator、audit signature、geometry specs/serializer、judge extraction 同步消费 ref；
- 没有 ref 的 v1/v2 单段窗口严格走 legacy path。

### B-06 — HIGH — facade_coverage.json 的 single-writer/尝试归档/视图清单没有落点

E1 说 B5 写 facade_coverage.json，B5b 又说新增 coverage 产物，writer/batch 自相矛盾。当前 StageRunner 每次 attempt 只归档 output.json 与 checks.json；若 coverage 只写在 1_correction/ 根，坏的后续 draw 会覆盖它，accepted manifest 又无法把它绑定到对应 output。当前也没有受信的 case view manifest，只有 *_view.json/图片 glob 与可缺省的 ReadingView.facade。

建议修法：

- 把确定性 facade_segments 放进版本化 CorrectedGeometry（随 accepted output.json 归档）；
- coverage 若独立 sidecar，必须作为 attempt artifact 存在，含 output hash/schema/helper/view-manifest hash，并由 accepted attempt promote；或把其完整机读内容也纳入 correction output；
- 视图 manifest 在 0_reading 前由 case metadata 产生，记录 source image id、kind、view direction、可选 target segment/local-view frame；reader 只能引用，不能决定“收到过什么图”；
- report collector、resume/invalidation、两条运行路径均从同一 finalize/writer 取，不另写副本。

### B-07 — BLOCKER — B2→B6 依赖图不真实，B4/E1 形成隐含环

具体错误：

1. B2b 会移动 polygon/贴边 cells，却只依赖 B2；安全验收需要 B3 polygon coverage 硬门，故应依赖 B2+B3。
2. B4 把 E2.3 NA 放在 B5/E1 前，却声称复用 E1 helper；若 helper 到 B5 才有，B4 不能并行完成。
3. B5 又依赖完整 B4，形成“B4 NA 需要 E1、E1 在依赖 B4 的 B5”循环。
4. E1 宣称 B5 产 coverage，批表却把 coverage 放 B5b；验收/单 writer 无法分派。
5. B6 依赖全件和用户新 case 这点真实，但 sm26 的预期要先解决 A-03。

建议 DAG：

    B2 (footprint contract/helper)
     ├─> B3 (polygon coverage gate) ─> B2b (safe E3 transform)
     └─> V  (pure facade-segment + visibility contract/helper)
           └─> B4a (gt-v-next + DXF)
                 └─> B4b (segment scorer + applicability + policy/render)
                       └─> B5 (correction segment/window/frame wiring)
                             └─> B5b (trusted view inventory + coverage/WARN/report)
    all above + user artifacts ─> B6

V 可以先只接受 plain polygon/方向向量，保持 gt-blind；judge 与 executor 各以自己的 polygon 调同一纯函数。这样既无循环，也不破 gt 铁律。

### B-08 — MEDIUM — D10 的兼容与容差验收在增补稿中被弱化

D10#3 要求显式兼容路径，D10#6 要求独立 coverage_area_tol_m2 进入 correction.yaml+A0。当前 config 仍无该面积项，geometry_validator/kernel 各有裸面积常数。另一方面，新增 Pydantic 字段后，现有 model_dump_json() 默认会把 defaults 序列化；“sm21 单段字节不变”若指 correction JSON 原始 bytes，按当前 serializer 并不自动成立。现 B0 测试名虽写 byte-identical，实际比较的是 building_geometry_dict 等价。

建议修法：明确三层验收：

1. v1/v2 输入的 built geometry/specs/audit 行为不变；
2. 若真要求 artifact bytes 不变，采用 version-gated serializer/exclude_none 并对真实 fixture 做 byte fixture；否则把文案改成 semantic/geometry equality；
3. B3 落独立面积容差，visibility boundary/depth epsilon 也各自命名配置/A0 登记，禁止复用线性 min-edge 或裸常数。

## D1–D10 定案冲突/继承表

| 基线项 | 本审结论 |
|---|---|
| D1 | **冲突**：新增 footprints/facade_segments 未 bump；须先解 B-01。 |
| D2 / D10#1 | B1 的 polygon-first cell 路径已落，不重开；但它只支持无洞 exterior ring，不能承载口字形。 |
| D3 / D10#3 | B2 是合法延伸，但 helper、版本与显式兼容路径未设计完整；E3 不是现规则的机械逐边化。 |
| D4 / D10#2 | **显式修订未获通过（as written）**：允许缩窄为“world-frame 后确定性归段”，不得删除 span/room 的 A1/A3 责任。 |
| D5 / D10#4 | B3 依赖 B2 的修正被保留；新增 B2b 还必须依赖 B3。 |
| D6 / D10#5 | 硬前置继续有效；B4 必须覆盖 correction_score、reading/elevation scorer、score policy、sidecar、render_grade、render_gt/overlay 与 capability dispatch。 |
| D7 | **冲突**：口字形/中庭洞与“带洞留 C3”冲突；需砍范围或正式改基线。 |
| D8 | 原批序被 E1–E3 改出循环；按 B-07 重排后才能执行。 |
| D9 | visibility 边界容差有登记意图，但面积容差、depth/tie epsilon 与 transform guard 未闭合。 |
| D10 | #1 继续有效；#2 仅接受 A-02 的窄修订；#3/#6 不能因增补而丢；#4/#5 继续作为依赖与判卷硬约束。 |

## B2→B6 依赖真实性与工作量分档

| 批次 | 依赖结论 | 工作量档 | 可否按当前稿执行 |
|---|---|---|---|
| B2 | 依赖 B1 真实；但缺 schema v3、floor key/helper、双路径 finalize | **L，需代码级细稿** | 否；不是“原样执行” |
| B3 | 依赖 B2 真实；shared adjacency 主体已有 polygon-native 基础 | **M，前置闭合后可机械执行** | B2 定稿后可 |
| B2b | 应依赖 B2+B3，不是仅 B2 | **XL，需独立 E3 变形设计** | 否 |
| V（建议新增） | 依赖 B2；给 B4/B5 共用纯 segment/visibility helper | **L，需细稿+穷举单测** | 当前批表缺失 |
| B4 | “可并行 B2–B3”只对早期 gt schema 讨论勉强成立；E2.3 必须等 V/视图契约 | **XL，必须拆 4 子批** | 否 |
| B5 | B2+B4 是原 D10 硬前置，但当前又被 B4 反向依赖；按 B-07 解环 | **XL，需细稿** | 否 |
| B5b | 依赖 B5 不够，还依赖 B4b applicability 与 trusted view manifest | **L，需细稿** | 否 |
| B6 | 依赖前件与用户 sm25/26 真实；词汇编辑本身机械，端到端不是 | **S（词汇）+ L（真实 E2E）** | 等前件与图纸；sm26 规格先修 |

机械执行结论：当前只有 **B3（在 B2 helper/schema 定稿后）**与 **B6 的纯词汇编辑（在政策定稿后）**可归机械批；B2、B2b、B4、B5、B5b 都需要新的代码级细稿与复审。当前设计不得直接进入 B2→B6 连续施工。

## 审阅需求（review-ask）

需主控确认两项会改变范围/验收口径的事实：

1. sm26 内翼窗是否在 plan/DXF 中可见；若可见，E2 不能把整窗判 unobserved/NA。
2. “口”是否确指带中庭洞的 footprint；若是，必须决定纳入 C2 的带洞契约，或明确移回 C3。

除此之外，无需主控替审阅器补判断；其余均为设计稿可自行修正的阻断项。
