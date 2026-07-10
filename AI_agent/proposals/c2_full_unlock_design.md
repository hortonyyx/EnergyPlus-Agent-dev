# C2 收官设计 v2.2(定稿):完全解锁非方形 + 真北方位

> **版本史**:v1 2026-07-09(`0e28520`)→ sol+max **首审 REWORK 16 findings**([r1](../logs/reviews/verdict/2026-07-10_c2_full_unlock_review.md))→
> v2 2026-07-10(吸收 16 findings + 用户三轮讨论)→ sol **二审 REWORK:11 closed/5 partial/0 not-closed + 新增 5**(1 BLOCKER/3 HIGH/1 MEDIUM,[r2](../logs/reviews/verdict/2026-07-10_c2_full_unlock_review_r2.md))→
> v2.1 2026-07-10 = 按 r2 升审门 5 条修订:E4 出口坐标策略定案(**用户拍选项一 Relative + EP 探针五条全过**,[probe](../logs/experiments/2026-07-10_e4_relative_north_axis_probe/RESULTS.md))、宿主解析按证据源拆支、opening×claim 级 applicability、v3 精确类型、B-M 前置、知识候选确定性化、interactive 停机合同 →
> sol **三审 APPROVE-WITH-CHANGES:复核 10/10 closed、历史 21/21 closed、零新架构 finding、5 条 changes(1 HIGH/4 MEDIUM)**([r3](../logs/reviews/verdict/2026-07-10_c2_full_unlock_review_r3.md),探针经其独立复算)→
> **v2.2 2026-07-10 本稿(定稿)** = C-01..C-05 机械并入;sol 裁定无需第四次整稿复审,后续各批按本稿纪律独立出细稿过审。**放行边界:放行总设计与分批细稿阶段,不放行 B2→B6 连续施工;C-01/02 落 E4-output-contract 开工门,C-03/04 落 B-M/Vg/Va 细稿门,C-05 落知识表/loader 细稿门(均已并入正文)。**
> 基底 [c2_orthogonal_polygon_design.md](c2_orthogonal_polygon_design.md)(D1–D10 定案)地位不变;本稿对 D10#2 仅做**窄版修订**(§E1'.4),对 D7 **维持原判**(带洞→C3)。
> **不变量合规**:零架构推翻;全部 = schema 槽位 + kernel 扩展 + 判卷/gt 同步(不变量 #6);分工铁律不动。

---

## E0 · 范围定案(v2 变更,用户 2026-07-10 拍)

| 进 C2 收官 | 出 C2(留接缝) |
|---|---|
| L/U 外包多边形:**无洞、单连通、各层相同、等高、正交简单多边形** | **口字形/中庭**(内环契约,维持 D7"带洞留 C3";sm27 随迁)|
| 四标准视图(天然对上,不做匹配)+ **受信视图清单契约** | **立面匹配引擎**(确定性打分器:投影总宽→层结构→窗列指纹互相关;图名/OCR 永远只是 hint;歧义→conflict 问用户)→ C3 |
| E1' 可见性 + E2' 证据政策 + E3' 权威矩阵 + **E4 真北方位角** | 补交/局部视图消费(manifest 留 `view_kind: full\|partial` 槽)→ C3 |
| 判卷/gt 全链升级(B4 拆批)+ 知识库骨架(第一张表) | 交互式编辑 viewer(中长期线,已档);知识库大规模搬迁(独立轮) |

**用户 07-10 定案登记**:①匹配=几何题,确定性打分器主导 ②E2' "实体要证据,属性可补默认+标记" ③接受 unobserved 段单通道实体的鲁棒性交易(reading 精度提升后风险自然下降) ④证据矩阵对称+通道矛盾不静默 ⑤REPORT assumed 清单桶 ⑥回字形出 C2 ⑦sm26 内壁窗平面必画(验收器重定义) ⑧知识库骨架现在立 ⑨completion_mode 双模式 ⑩E4 真北一起上。

## E1' · 立面可见性模型(修订:窄域声明 + frame 拆层 + V 批)

1. **适用域显式声明**(闭 A-01):无洞单连通等高正交简单 footprint + 四 cardinal 正投影 + 实体不透明墙。1D skyline 区间竞争在此域内确定性成立;**同深重叠 = INVARIANT 错误**(合法简单多边形不产生同深竞争,出现即上游坏数据),不选赢家。区间为**半开 `[a,b)`**,端点/深度比较用命名 epsilon(进 correction.yaml + A0,禁裸字面量)。对 C4 的承诺收窄为"**interval-sweep 核心可复用**"(方向向量入参),不再宣称零重写。
2. **E1.4 窄版**(闭 A-02;r2 确认对首审 CLOSED):确定性归段**只对已在世界坐标系的窗**成立;图纸局部坐标→世界坐标的换算责任仍在 A1/A3(现 `derive_facade_frame` 是 flag-only 旁路;真替换归 Phase B)。**D10#2 的 A3 责任不整体删除**。
   **宿主解析按证据源拆两支**(v2.1 新,闭 R2-A-01——E2' 单通道政策与可见性门的交叉缺口):
   - **平面来源的窗**:在**全部**外边界段上按 room boundary + 完整 span 唯一解析——**hidden 段不阻止挂段**(有平面证据的窗必须拿到段归属与宿主墙);可见性只决定**立面属性(z 等)能否计分**,不决定实体挂不挂。
   - **立面来源的窗**:只在该视图的 **visible** 段候选中解析;完整 span 落入唯一 room-boundary interval 才补 room(一个段可跨多 room,段 id 不替代 room);跨 room 缝/零或多候选 → A3/interactive。
   - **负证据有前提**:"一通道有窗另一通道无 = conflict"仅当另一通道对该位置 **coverage 完整且图种承诺完整表达 openings** 时成立;遮挡/裁切/制图省略/版本差异下的"无"只是**无独立佐证**,不是 conflict。
   - 其余一律 conflict 纪律不变:跨段边界/零或多候选/room 不符,**不按中心点猜**。
3. **frame 拆两层**(闭 A-07):`ViewProjectionFrame`(一张图一个:local→world along 映射,含 S/E 正号、N/W 负号约定与 mirrored 位——号位来自约定+镜像位非 VLM 申报,现行 6.30 定案继承)+ `FacadeSegmentFrame`(一段一个:`p1/p2/base/normal`)。段 id = **floor namespace + canonical 几何指纹**(不用 ring 边索引,免受起点影响);排序键 `(along_lo, along_hi, depth, canonical_edge_key)`。回归:矩形单段 South/East 正号、North/West 负号、mirrored 三组分别字节级验证。
4. **Vg/Va 批(新增,前置纯函数;v2.2 按 C-04 定名分工)**:`Vg(polygon, direction)` = 分段派生 + 可见性,只吃多边形与方向向量;`Va(Vg 输出, B-M manifest, opening claims)` = opening×claim applicability 薄适配。两者均为 **gt-blind 纯函数**但输入/责任不同,judge 与执行器各拿自己的输入调同一函数——不破 gt 铁律,解 B4↔B5 循环(见 §DAG)。
5. 楼层维度:按层计算(C2 各层同 footprint → 段表相同;结构留 C3 退台)。

## E2' · 证据通道 × 属性矩阵(替代 v1 E2,用户 07-10 定案 + 闭 A-03/A-04)

**核心口径:实体要证据(任一通道),属性可补默认+标记;无任何通道证据的实体禁止发明。**

1. **矩阵**(对称):
   | 通道 | 可立证的属性 |
   |---|---|
   | 平面(plan/DXF) | 窗**存在**、along 位置、宽度、宿主墙/room |
   | 立面(该段 visible) | 窗**存在**、along 位置(经标定)、宽度、**窗台高/窗高(z)**、外观 |
   | 两通道都无 | 实体 unknown——**禁发明** |
   - **单通道立实体合法**(平面 only 或立面 only 均可);单通道实体错误率高于双通道 = 用户已知情接受的交易,靠 provenance 高亮 + interactive 优先问 + dev 期 gt 兜底。
   - **通道矛盾按 E1'.2 的负证据前提判**(v2.2 按 C-03 改,删旧绝对句):仅当另一通道对该位置 coverage 完整且图种承诺完整表达 openings 时,"无"才构成负证据 → conflict 升 A3;否则只是无独立佐证。**前提须机读**:B-M manifest 类型化 `negative_evidence_capable_claims` + 可信 coverage region/interval 及 completeness 来源;**reader 不得通过自报"低清/没看见"改变 judge denominator**(完整性声明只来自受信 manifest,不来自被测产品)。
2. **z 缺失补默认**(v2.1 收紧,闭 R2-A-02):查 `knowledge/window_modules.yaml` **确定性 lookup**——`prior_fill` 模式**只允许表内唯一 `default_candidate_id` 或无并列的确定性 priority**;无唯一默认 = INVARIANT(配置错误),**不许 LLM 无证据抽签**(那是随机 prior 不是 prior)。LLM 仅当引用**可审计的观察属性**并命中显式 applicability 规则时可筛选候选;interactive 模式才向用户列候选。写入值带 `provenance: assumed` + **`knowledge_ref` 五元组**(`dataset_id+dataset_version+entry_id+candidate_id+content_sha256`,防表被原地改后不可重放)。**z 语义**:表值为楼层内模数,最终 `Window.z = z_floor + sill/head` 派生,过 ceiling/最小净高守卫,**不静默 clamp**。**prior 补属性 ≠ 幻觉几何**——v1"prior 只用于物理属性"修订为:实体有证据时,缺失几何属性可走 prior 阶梯,必须带 provenance(与墙厚 prior 阶梯 07-08 定案同族)。
3. **completion_mode**(run_config):`prior_fill`(默认)| `interactive`。**interactive 停机/恢复合同本轮冻结**(闭 R2-A-03,不再"形式后议"):阶段返回结构化 `NEEDS_INPUT`,attempt 产 `input_request.json`(缺失 claim、候选、证据、checkpoint digest),进程正常停止**不计坏 attempt**;用户回复绑定 digest 后 resume;non-interactive/CI 环境下该模式 **fail-fast 并提示改用 prior_fill,禁止自动降级**。UI 形式后议,合同不后议。
4. **受信视图清单**(闭 A-04 洗分漏洞):reading **前**由 case metadata 生成 view manifest(source image id、`view_kind: full|partial`、view_direction + **direction 来源**:standard_assumption|图名 hint|matcher(C3)|user),产品不可改;**源图已提供而 reader 漏读 = miss,不是 unobserved**。
5. **applicability 升级为 opening × claim 级**(v2.1,闭 A-04 残余/B-04 残余):每窗按 claim 分别判——至少 `existence / host / along / width / sill / head / appearance` 各有 `applicable | partially_applicable | not_applicable` + reason + evidence interval + source-view ids;不看段总状态、不看窗中心点。**provenance 与 applicability 是两条轴**:sm26 内壁窗可以有 assumed 的 sill/head **值**,判卷对 sill/head 仍 NA,along/width 由平面照常计分。`partially_applicable` 不整窗折半也不整窗灰掉:score sidecar 按 claim 分 denominator;渲染几何本体按 observed/derived/assumed 三色,**不计分的 claim/区间另用灰纹/标签**。跨 visible/hidden 边界的立面来源窗:存在性可立,证不到的完整宽/头高等 claim 单独 partial/NA。**judge 用 gt footprint + 受信 manifest 独立重算**(调 V 批同一纯函数),绝不消费产品的 coverage 产物;sidecar 记 helper version、manifest hash、gt schema/hash、各 claim denominator。
6. **两类分开**(闭 A-04 尾):coverage 机制失败/账本缺失/账本与几何不一致 = **INVARIANT**(硬错);账本证明确实无证据 = WARN/NA(诚实缺失)。产物区分 "observed zero windows" 与 "unknown fenestration"。
7. **产物归属**(闭 B-06):确定性 `facade_segments` 进**版本化 CorrectedGeometry**(随 accepted output.json 走 attempt 归档);coverage/applicability 若独立 sidecar 必须是 attempt artifact(绑 output hash + schema + helper + manifest hash,由 accepted attempt promote)。单一 writer = correction 确定性核;两条运行路径经同一 finalize(§B2)。
8. **报告与呈现**(用户 07-10):REPORT 增 **assumed 清单桶**(本 run 所有 assumed 属性 + knowledge_ref,机械生成)——补默认要认账认到最终报告;人工校验 HTML 按 provenance 上色(**观测/推导/assumed 三色**,置信度分层留槽),C2 交付 = 静态可见"哪些是猜的"。
9. **虚线可审计**(闭 A-08):reading stroke observation 增可选 `line_style/visibility` 字段(或至少 `uncaptured[]` 记 `{source_id, kind: hidden_window_candidate, reason}`);hidden observation 不进实体 Window、保留供 conflict/audit;B6 词汇配四类负例(实线可见/虚线隐藏/虚线误读/同位实虚重叠)。

## E3' · envelope 权威矩阵(替代 v1 E3,闭 A-05/A-06)

更名:**"polygon bbox + 有证据端点仲裁"**(不再称"完整逐边仲裁")。**保持 6.23 定案**(墙厚量级内立面外包>平面外包),用 claim-type 分权化解表面冲突:

| claim | 权威 |
|---|---|
| 拓扑/凹凸关系/边接续/**缺口深度(notch depth)** | 平面尺寸链(立面正投影无叉轴证据,**不得移动 notch depth**)|
| 全楼 x/y 投影外包 bounds | 满足现行双证据 + 0.30m 门时 facade overall 权威 |
| 段 along 端点 | 仅有明确翼分界标注时立面可佐证/修正 |
| 同 claim 高权威冲突 | 升 A3,"佐证"不静默升级为动作 |

**变形算法 = B2b 独立细稿**(闭 A-06):基于共享轴/vertex graph 的**原子 transform**(证据坐标→受影响 footprint 轴线→所有关联 footprint/cell 顶点→重派生 bbox→窗/段 ref 重验);变形前查跨轴/最小边/绕向/自交/段消失,变形后以 B3 polygon coverage、共享边一致、窗宿主唯一性做**硬门**,任一失败整事务回滚记 conflict。**故 B2b 依赖 B2+B3**。

## E4 · 真北方位角(新,用户 07-10 拍"一起上")

**定性:元数据旋转,非几何旋转。** 建筑内部保持正交,整栋相对真北转角 θ。**不变量 #2 澄清条款:内部世界坐标系 = 建筑系(轴对齐),真北 = 一个声明的元数据角**——所有几何/gt/判卷留在建筑系,只在 EP 出口应用角度。

1. **出口坐标策略定案(v2.1,闭 R2-B-01——r1/r2 唯一新 BLOCKER)**:v2 的"填字段即生效"断言错误——现出口为 `GlobalGeometryRules=World`,EP 在 World 坐标系下**忽略 Building.North Axis**(EP 警告原文亲测:"Any non-zero Building/Zone North Axes or non-zero Zone Origins are ignored"),现有 IDF Zone Origin 还非零 → 直接接线 = 假完成。**用户 2026-07-10 拍选项一(Relative 路线)**,同日 **EP 25.1 探针五条全过**([probe RESULTS](../logs/experiments/2026-07-10_e4_relative_north_axis_probe/RESULTS.md),Sonnet 执行档对账):Relative+全零 Zone Origin+现建筑系绝对顶点,θ=0 时 114 面 Azimuth 与 World 基线逐面相等(几何零变形)、θ=90/270 全面精确偏转、14 区面积体积不变、World 独有的"ignored"警告消失。**出口契约 = GlobalGeometryRules 切 Relative + 全部 Zone Origin/Direction of Relative North 归零 + Building.North Axis 写 θ**;`E4-output-contract` 细稿批负责落地(含 daylighting reference/shading 等 building-bound 坐标对象的全量审计,防漏转对象),**B-O 依赖它,工作量 S→L**。验收:θ=0/90/270 合成端到端比对 EP 报告 azimuth,非零用例不得出现 "ignored" 警告。
2. **唯一 owner + 类型化角度**(v2.1,闭 R2-B-02):现实是 4_mep 的 MepOutput 拥有整个 BuildingSchema、5 段原样复制——θ 的**唯一 owner 定为 accepted correction 的 orientation 产物**,`assemble_intake_output` 对 `mep.building.north_axis` 做**确定性 override**——**占位语义精确化(v2.2 按 C-02/r3-Q2)**:4_mep 的 `building.north_axis` 是**无权威兼容占位,校验只允许 0.0**(LLM 显式给非零 → S4 INVARIANT fail);S5 接收 accepted orientation evidence 后**无条件用其 `value_deg` 替换占位 0,不拿占位 0 与 θ 做值冲突比较**(默认 0 对 θ=90 不是 conflict);硬冲突只指 orientation 产物缺失/多份、schema/digest 不匹配、角度非法、或两条运行路径输入不一致。两条运行路径调同一 merge/check。后续如单独做 MepOutput breaking version 可再移除该字段,C2 不为此扩大改面。v3 用 **typed evidence value**:`{value_deg, provenance(observed|derived|assumed), source_ids, uncertainty_deg, method, frame_transform_hash}`——最终 0 照写 EP,但"真值零"与"未知默认零"**不可混**。**角度语义写死**:真北到建筑 +Y 的顺时针角,`[0,360)` 正规化。
3. **证据通道**(按 E2' 政策):用户 metadata/总平显式标注 > 指北针读数(reading 观测,CV 测角;**±2–3° 记为测量 uncertainty,不等同判卷容差**,两者分开配置;不 snap 整角) > **default 0 + `provenance: assumed`**。**sanity 硬门**(闭 r2-Q5):箭头杆/头方向唯一、page rotation/mirror 已解析、image→building 变换有 hash、多枚北针在 uncertainty 内一致、显式标注与 glyph 差超阈值记 conflict。manifest 增 `direction_semantics: building_axis | true_azimuth | unknown`——**图名只是 hint**,仅图纸明确声明立面标题为地理方位时才可与 glyph 交叉验证。判卷:gt 有值**且**产品 provenance 非 assumed 才计角度误差,assumed 0 该 claim 为 NA。
4. **Facade 语义守卫**(v2.2 按 C-04 加条件):N/S/E/W 保持**建筑系标签**;"图纸『南立面』=建筑系南"**仅当 manifest `direction_semantics=building_axis` 时成立**;`true_azimuth` 必须带数值 `azimuth_deg` 并经 θ 映射回建筑系视向,`unknown`/不可唯一映射 → conflict 或留 C3——与 E4.3"图名只是 hint"一致不冲突。任何环节不得按真北改写立面归属;E1'/判卷全建筑系,**几何管线零改动**。
5. **落批**:schema 槽位随 B2 v3;`E4-output-contract` 细稿 → **B-O**(correction→装配 override→EP 出口切换),依赖 B2;gt v-next 加可选 `north_axis_deg`(随 B4a)。
6. **出口合同确定性化(v2.2 按 C-01,HIGH——E4-output-contract 开工硬门)**:现代码三处 seam 已点名——`intake._seed_config()` 只写 building/site、`ConfigState.global_geometry_rules` 默认 World、`zone.py` prompt 让 LLM 把 x/y/z origin 写成房间位置。细稿必须:① 冻结**内部** `OutputCoordinateContract`/run metadata(不扩 11 字段契约),绑定 accepted correction schema+digest;② v3/E4 路径由 intake seed **代码确定性**设置 `GlobalGeometryRules=Relative`,zone agent 之后由**代码统一覆盖** x/y/z origin 与 direction 为 0 并以 gate 拒绝任何非零(prompt 只作辅助不作机制);③ **v1/v2 默认继续走现 World legacy 分支**,分支判定依据 schema/合同、**禁用 θ≠0 猜分支**(v3 的真值 0/assumed 0 同属 E4 合同);④ integrated 与 stepwise 两条路径都断言最终 ConfigState、IDF setting、全部 zone origins 与 EP warning(θ=0/90/270 端到端)。

## Schema v3 一次性定案(闭 B-01;v2.1 按 r2-Q4 精确化,消灭全部"二选一")

- **correction schema v3 在 B2 前冻结**,精确类型:
  - **`Floor.id`(immutable 主键)+ `Floor.footprint`(typed exterior ring)内嵌**——不用 dict 键、不用可改名的 `Floor.name` 作主键,**不留二选一**。
  - **`FacadeSegment` 类型化**:`id / floor_id / facade_family / p1 / p2 / normal / world_along_interval / depth / visible_intervals / source_footprint_fingerprint`。
  - **`Window.facade_segment_id`** + field-level evidence/provenance map;**段 ref 不取代 room**。
  - **`north_axis`** = E4.2 的 typed evidence value;**`knowledge_ref`** = 五元组。
  - "observed zero / unknown fenestration"、per-claim applicability、accepted-attempt 身份 → 各自**独立版本化的 coverage/scorer sidecar schema**,不塞进 CorrectedGeometry;view manifest 独立 schema/version;`completion_mode` 留 RunConfig 不进几何 schema。
  - v3 几何子模型 `extra="forbid"`(unknown-field 硬门);v1/v2 经 adapter 保持 legacy 宽容。
- **capability 检查从"version == 2"改 feature/shape 声明**——4 处硬编码点名修:`deterministic.py:751`、`geometry_validator.py:65`、`pipeline.py:481`、`modelling.py:392`(已亲核);未知未来版本 fail closed;v1/v2 行为不变。
- gt 的 `schema_version: 2` 是**另一条答案契约**,独立命名/演化。"一次冻结"= C2 内目标一次 bump 到位,**不解释为未来发现契约缺口也禁止 bump**。

## 批次重排(闭 B-07,收官 DAG)

```
B-M (受信视图清单 schema/generator;0_reading 前,新增——解"先用后造")
B2 (footprint 契约/helper/schema v3)
 ├─> B3 (polygon coverage 硬门)  ─> B2b (E3' 安全变形,独立细稿)
 ├─> E4-output-contract (出口坐标细稿) ─> B-O (真北接线,S→L)
 └─> Vg (纯几何:分段+可见性,gt-blind)
       ├─(+B-M)─> Va (opening×claim applicability 薄适配)
       └─> B4a (gt-v-next + gt_from_dxf 重写 + DXF round-trip)
             └─(+Va)─> B4b (段级 scorer + per-claim 判卷 + policy/sidecar/render)
                   └─> B5 (correction 段/窗/frame 接线 + source-aware 宿主解析)
                         └─> B5b (coverage/WARN/REPORT 桶 + HTML 三色;只消费 B-M 的 manifest 并归档 hash,不再造)
全部 + 用户 sm25/26 图 ─> B6 (0/1 skill 词汇 + 端到端 anchor)
```

| 批 | 内容 | 依赖 | 工作量档(sol 对账采纳) |
|---|---|---|---|
| B2 | v3 冻结 + `floor_footprint` 单一 helper 贯穿 core/validator/naming/audit/render/judge + **双路径同一 correction-finalize**(闭 B-02:run_stage 现不传 envelope 已亲核,parity 测 snapped artifact 非 check ids)+ 矩形显式 legacy 分支 | B1 | **L,代码级细稿先行** |
| B3 | 覆盖门 v2(面积守恒,独立 `coverage_area_tol_m2` 进 correction.yaml+A0,闭 B-08) | B2 | M,细稿定稿后机械 |
| B2b | E3' 原子变形 + 硬门 + 回滚 | B2+B3 | **XL,独立细稿** |
| B-M | 受信视图清单(0_reading 前生成,产品不可改;含 view_kind/direction+来源/direction_semantics) | — | M,细稿 |
| E4-output-contract | 出口切 Relative 细稿(Zone Origin 归零迁移 + building-bound 坐标对象全量审计 + θ 唯一 owner override) | B2 | **L(原 S 作废)** |
| B-O | 真北接线施工 | E4-output-contract | S |
| Vg | E1' 纯几何函数(穷举单测:L/U/Z/T、全遮挡、部分遮挡、同深 INVARIANT、端点半开) | B2 | L,细稿 |
| Va | opening×claim applicability 薄适配 | B-M+Vg | S |
| B4a | gt-v-next(polygon/zone polygon/per-floor/段/opening 段 ref/north_axis/validator)+ gt_from_dxf 重写(LWPOLYLINE polygonize+拓扑验证,floor/view/role 配置化,窗归最近合法边界段;先合成 L/U DXF round-trip 再接 sm25/26)+ render_gt/overlay 升级(闭 B-03) | Vg | **XL** |
| B4b | 段级 plan/elevation scorer + `NOT_APPLICABLE(unobserved)` 机读结构/独立 denominator/灰纹画法 + sidecar 身份扩(gt hash/schema、capability、manifest hash、helper version,bump SCORER_SCHEMA)+ **per-claim denominator/NA 机读形状**(闭 B-04 残余)+ 不支持组合在评分入口显式 NA/拒绝 | B4a+Va | **XL,4 子件顺做** |
| B5 | 窗挂载联动(闭 B-05):resolver 验 floor/room/segment 一致→clamp 到段真实区间(弃 cell bbox)→parent wall 同时满足 room+段平面/法向+完整 span→`_window_verts` 按宿主墙 p1→p2 参数化(接口按线段,C2 轴向实现)→validator/audit/specs/judge 同步;无 ref 的 v1/v2 严格 legacy path;**source-aware 宿主解析两支(E1'.2)** | B2,B4b | **XL,细稿** |
| B5b | coverage 产物归档 + assumed 清单桶 + HTML provenance 三色(**只消费 B-M manifest,不再造**) | B5 | L,细稿 |
| B6 | 词汇(外轮廓 polyline/翼分界/虚线四负例)+ sm25/26 端到端 | 全部+用户图 | S(词汇)+L(E2E) |

**机械批只有 B3 和 B6 词汇**;B2/B2b/B4a/B4b/B5/B5b 均需细稿过审后施工(每批照旧:细稿→审→执行→复核,合成用例先行,零 golden 改动逐批断言)。

**验收三层**(闭 B-08):① v1/v2 输入的 built geometry/specs/audit 行为不变(语义等价为准);② artifact **byte 等价只在 version-gated serializer(exclude defaults)落地后承诺**,否则文案一律"semantic/geometry equality";③ 所有新容差(面积/可见性端点/深度 epsilon/真北比对)各自命名进配置+A0,禁复用线性 min-edge、禁裸常数。

## 知识库骨架(用户 07-10 拍,C2 只立骨架+第一张表)

```
src/configs/knowledge/
  ├─ window_modules.yaml   # C2 第一张表:zone类型 → 窗台高/窗高模数候选(id+版本+出处)
  └─ (路径预留:墙厚 prior 阶梯迁入、层高惯例、荷载/作息默认…)
```
- **消费分级(v2.2 按 C-05 与 E2'.2 对齐)**:查表(确定性代码,唯一 default)> **有证据筛选**(LLM 仅在引用可审计观察属性并命中显式 applicability 规则时筛候选;interactive 才向用户列候选;**无证据抽签禁止**)> prose 咨询(留在 skill 体系),能上一级绝不下一级。
- **第一张表 schema 冻结(r3-Q3 采纳 + 四条补强)**:四层 `dataset(schema_version/dataset_id/dataset_version/units:m/space_type_taxonomy_version/content_sha256) / entry(entry_id/applies_to/default_candidate_id/source_refs) / candidate(candidate_id/sill_m/height_m/priority/valid_when/source_refs) / source(source_id/title/locator/license)`;加载硬门 = id 唯一、**每 entry 恰一 `default_candidate_id`**(不并存两套默认算法)、priority 无并列、值有限且正、sill+height 过楼层 ceiling。四条补强:① `entry.applies_to` 用版本化规范 `space_type_id`,自由文本 `Cell.role` 先经显式 alias/taxonomy 映射,未知 role 不模糊匹配;② 多 entry 同时命中按 specificity/`match_priority` **全序**裁定,并列 = INVARIANT;③ no-match/守卫全失败的终态:有显式 generic entry 才可 fallback,否则 interactive→`NEEDS_INPUT`、prior_fill→unresolved/INVARIANT,**不回 prose/LLM 猜值**;④ `content_sha256` = 规范化 payload(排除该字段自身)之 hash,dataset version 一经发布不可原地改;静态 schema/load 校验与结合楼层 ceiling 的 runtime guard 分开记账。
- 被消费时产物记 `knowledge_ref` 五元组 → REPORT assumed 清单机械生成;A0 禁裸字面量纪律延伸覆盖。
- **知识库=领域事实,skill=操作规程**;现有 skill 内散落知识的清点搬迁 = 后续独立轮,C2 不动。

## §T' · 用户测试案例规格(修订)

共同要求照旧(天正 DXF 图形导出、平面尺寸链含每个缺口两轴偏移、四标准立面、各层同 footprint、2 层)+ **新增:总平/指北针若有则一并提供**(E4 证据;没有则走 default 0 + assumed)。

1. **sm25-L**(不变):L 形,北/东各 2 段不同深,南/西单段,全段可见;缺口两面都放窗(考深段窗归属 + E3' 逐边)。
2. **sm26-U**(验收器重定义,用户 07-10 拍):凹口朝南;缺口底墙放窗(考同视图不同深度);**侧翼内壁窗:平面图上必画**——验收 = 系统从平面读出实体(x/宽 observed)→ z 查表补默认(assumed + knowledge_ref)→ 判卷 x/宽计分、z 记 NA → HTML 标"猜测色" → REPORT assumed 清单收录。**不再验收"整窗 NA"**。
3. ~~sm27-口~~ → 随口字形移出,归 C3。

## 开放问题:无(三审全部裁定)

> r3 裁定:①五条升审门全部闭合,唯一 BLOCKER(World 下朝向角无效)由 Relative 定案+前置细稿批+实跑探针共同关闭;②MEP 字段采**装配段确定性 override + 占位 0 语义**(已并入 E4.2),暂不移除字段;③知识表四层骨架直接采用+四条补强(已并入知识库节)。C-01..C-05 已全部并入正文,各批细稿开工门见版本史注。
