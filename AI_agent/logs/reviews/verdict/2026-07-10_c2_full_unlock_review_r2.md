# C2 收官设计全面对抗审（二审）

Date: 2026-07-10  
Object: `AI_agent/proposals/c2_full_unlock_design.md`（本地未提交 v2）  
Baseline: `AI_agent/proposals/c2_orthogonal_polygon_design.md` D1–D10  
Prior verdict: `2026-07-10_c2_full_unlock_review.md`（16 findings）  
Verdict: **REWORK**

首审 16 项闭合统计：**CLOSED 11 / PARTIAL 5 / NOT-CLOSED 0**。  
本轮新增：**5 findings（BLOCKER 1 / HIGH 3 / MEDIUM 1）**。

v2 已消除首审的大部分结构性问题：C2 窄域、E1.4 对 D10#2 的窄修订、6.23 envelope 权威矩阵、B2b 原子变形前置、gt/scorer 大批重估、sm26 与口字形范围均已改正。当前仍判 REWORK 的直接原因不是这些旧方向，而是新增 E4 的落地前提与代码现实相反：项目当前输出 `GlobalGeometryRules = World`，EnergyPlus 会忽略非零 `Building.North Axis`，所以按 v2 的 B-O 接法，θ 会被写入但不会旋转普通建筑几何。另有 E2′ 单通道宿主解析、field-level applicability、manifest 时序、v3 精确类型和知识候选确定性需要在相关批开工前补齐。

本轮只写本 verdict，未修改设计或代码，未运行测试；代码现实以本地工作树静态核对，EnergyPlus 语义以项目所用 25.1 官方文档交叉确认。

## 一、首审 16 findings 闭合矩阵

| ID | 首审 severity | 二审状态 | v2 核验结论 |
|---|---:|---|---|
| A-01 | BLOCKER | **CLOSED** | E0/E1′ 已锁无洞、单连通、等高、正交简单 footprint；口字形回 C3；半开区间、同深 INVARIANT、命名 epsilon 与 C4 复用边界均补齐。 |
| A-02 | BLOCKER | **CLOSED** | E1′.2 明确只给已是 world-frame、完整落入唯一候选且 room 边界一致的窗确定性写段；local→world 与 room 判断仍归 A1/A3，未整体删除 D10#2 的 A3 责任。E2′新增的 plan-only/hidden 交互另见 R2-A-01。 |
| A-03 | BLOCKER | **CLOSED** | E2′ 改成证据通道×属性矩阵；sm26 已明确内壁窗平面必画，验收为 x/width observed、z assumed，不再把整窗洗成 NA。 |
| A-04 | HIGH | **PARTIAL** | trusted manifest、judge 独立重算、INVARIANT/WARN 分家、observed-zero/unknown 已补；但 applicability 仍只给 opening interval 一个状态，无法表达 sm26 的“同一窗 x/width 可计分而 z 为 NA”，且 manifest 被排到 B5b，晚于其消费者。 |
| A-05 | BLOCKER | **CLOSED** | E3′ 的 claim-type 矩阵保持 6.23 定案：facade overall 管投影外包、plan 管拓扑/notch depth、显式翼分界才管 segment endpoint。 |
| A-06 | HIGH | **CLOSED** | v2 不再把变形当局部改锚，已要求 B2b 独立细稿、shared-axis/vertex graph 原子事务、B3 后置硬门与整事务回滚。这里关闭的是设计越权；B2b 仍不得无细稿施工。 |
| A-07 | HIGH | **CLOSED** | ViewProjectionFrame/FacadeSegmentFrame 已拆；段 id、floor namespace、canonical fingerprint、排序键、mirror/正负号回归均有归属。 |
| A-08 | MEDIUM | **CLOSED** | `line_style/visibility` 或 typed `uncaptured[]` 审计路径及四类负例已明确；v3 细稿须二选一冻结，不能在实现时继续保留“或”。 |
| B-01 | BLOCKER | **PARTIAL** | v3 与四处 `version == "2"` 已点名，未知版本 fail-closed 也保留；但 `footprints` 仍写成“唯一 Floor 键或内嵌”二选一，provenance/coverage/knowledge ref 的类型也未列全，尚未达到“一次冻结”的可执行程度。 |
| B-02 | HIGH | **CLOSED** | B2 已扩大到单一 `floor_footprint` helper、所有消费者、两条路径共用 correction-finalize，并要求 parity 比 snapped artifact/audit。 |
| B-03 | BLOCKER | **CLOSED** | B4a 已承认 gt-v-next、DXF polygonize、floor/view/role 配置化、segment ref、validator 与合成 L/U round-trip 是重写，不再声称现提取器天然支持。 |
| B-04 | BLOCKER | **PARTIAL** | gt、scorer、policy/sidecar/render 已拆 B4a/B4b，范围和 XL 档正确；但 per-attribute denominator/NA 机读形状仍缺，当前“一窗一个 applicability”不能兑现 sm26。 |
| B-05 | HIGH | **CLOSED** | B5 已列 resolver、room+segment 联合约束、真实段 clamp、宿主墙参数化、validator/audit/specs/judge 联动与 v1/v2 legacy path。E2′单通道输入的 resolver 分支另见 R2-A-01。 |
| B-06 | HIGH | **PARTIAL** | accepted-attempt 绑定、output/hash/schema/helper/manifest 身份、single finalize 已补；但受信 manifest 既声明 reading 前生成，又到 B5b 才施工，生产时序尚未闭合。 |
| B-07 | BLOCKER | **PARTIAL** | 画出的图在图论上无环，B2b、V、B4a/B4b 的主依赖已改对；但 manifest 的生产者仍在 B5b、消费者在 V/B4b/reading 前，存在先用后造的语义依赖；E4 也因 R2-B-01 不能再按 B-O(S)并行看待。 |
| B-08 | MEDIUM | **CLOSED** | 语义兼容、serializer 后才承诺 bytes、独立面积/可见性/depth/真北容差均已分层，机械批判断也维持首审口径。 |

NOT-CLOSED 为 0 的含义是：v2 没有完全忽略任何首审 finding；PARTIAL 项仍是重新送审前必须写进设计的残余，不等于可以留给施工现场自行猜。

## 二、A 路：v2 新增政策的增量对抗审

### R2-A-01 — HIGH — E1.4 的“visible interval”门与 E2′的单通道实体政策相撞

E2′允许 plan-only 与 elevation-only 各自立实体，但现有两端无法同时落成：

- sm26 的 plan-only 内凹侧壁窗可能位于该朝向正投影的 hidden segment；E1′.2 却把“落入遮挡区”统一送 conflict，导致有平面证据的窗拿不到 B5 必需的 `facade_segment_id`。
- elevation-only 能证明存在/span/z，却不天然给 `room`；而 B5 已正确要求 room+segment 同时唯一。一个 footprint segment 还可能沿线跨多个 room，不能仅凭 segment id 补 room。
- “一通道有窗、另一通道无窗 = 必有一边读错”把缺省当成强负证据。只有该位置确实在 full/legible/visible coverage 内且该图种承诺完整表达 openings 时，“无”才是 negative evidence；版本不同、遮挡、裁切或制图省略也可能造成通道差异。

建议修法：把宿主解析拆成 source-aware 两支，再合并证据。

1. plan-derived world opening：在**全部**外边界段上按 room boundary + 完整 span 唯一解析，hidden 不阻止挂段；visibility 只决定 elevation 属性能否计分。
2. elevation-derived opening：只在该 view 的 visible segment candidates 中解析；再由完整 span 落入唯一 room-boundary interval 才补 room，跨 room seam/零或多候选进 A3/interactive。
3. negative evidence 增 `coverage_complete`/legibility 条件；不满足时是“无独立佐证”，不是 conflict。
4. sm26 增硬验收：plan-only hidden 窗最终有 segment+room、可生成宿主墙；其 z 为 assumed，不能因 elevation hidden 被整窗拒绝。

### R2-A-02 — HIGH — “多候选交给 LLM 挑”没有新增证据，会把 prior_fill 变成随机 prior

`window_modules.yaml` 以 zone 类型确定性查到多个候选后，LLM 若没有额外 case evidence，并没有比稳定优先级更有资格选择；它只会把同一输入变成模型/轮次相关的 z。`knowledge_ref = id+版本` 也不足以在表内容被原地编辑后重放选择。另需明确 sill/window height 是 floor-local 模数，最终 `Window.z` 必须加 `z_floor` 并过 ceiling/min-clearance 守卫，不能静默 clamp。

建议修法：

- `prior_fill` 只允许表内唯一 `default_candidate_id` 或无并列的 deterministic priority；无唯一默认即 INVARIANT/配置错误。
- `interactive` 才向用户列候选；LLM 只有在引用了可审计的观察属性并命中显式 applicability rule 时可筛选，不得凭“常见”自由选。
- `knowledge_ref` 固定为 `dataset_id + dataset_version + entry_id + candidate_id + content_sha256`；加载器校验单位、唯一默认、有效范围、source locator 与 ceiling fit，失败不落值。

### R2-A-03 — MEDIUM — `interactive` 已成为公开模式，但停止/恢复合同仍写“形式后议”

一个会停流水线的模式不能只冻结枚举值。当前 `RunConfig` 仅有 scope/judge/review/models/grade；没有等待输入状态、请求产物或 resume 身份。若实现者临场决定，容易出现 CI 挂起、重跑丢请求、或 interactive 静默退化成 prior_fill。

建议修法：在设计中冻结非交互 UI 的最小协议：阶段返回结构化 `NEEDS_INPUT`，attempt 产 `input_request.json`（缺失 claim、候选、证据、checkpoint digest），进程正常停止且不计坏 attempt；用户回复绑定 digest 后 resume。同一模式在 non-interactive/CI 环境必须 fail-fast 并指出如何改用 `prior_fill`，不得自动降级。

## 三、B 路：E4 与代码现实的增量对抗审

### R2-B-01 — BLOCKER — 当前 World 坐标输出会让 E4 的 `Building.North Axis` 对普通几何无效

v2 的关键落地断言“EP 侧 surface 方位由 Building.North Axis 自动旋转”在当前仓库不成立：

- `src/validator/data_model.py:692` 的 `GlobalGeometryRulesSchema.coordinate_system` 默认是 `World`；`src/mcp/state.py:104-106` 用该默认创建下游状态。
- 现有真实 IDF `case_tests/e2e_tests/sm21_anchor/run_2026-07-01_sonnet_e2e_r2/EP/EP_run/temp_20260701_170158.idf:222-233` 也写 `GLOBALGEOMETRYRULES ... World`，且首个 Zone 的 Y Origin 为 4.85；`src/agent/geometry/specs.py:160-190` 明示 zone/surface 是 absolute world coordinates。
- EnergyPlus 25.1 官方契约明确：World coordinates 不使用 Building/Zone North Axis 与 Zone Origin；North Axis 只在 Relative coordinate system 生效，非 Relative 时被忽略。[EnergyPlus 25.1 GlobalGeometryRules](https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-thermal-zone-description-geometry.html#field-coordinate-system)、[Building North Axis](https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-simulation-parameters.html#field-north-axis)
- 现有生成 Zone Origin 并非全 0，因此也不能只把一个 setting 从 World 改为 Relative；那会把当前绝对 surface vertices 再按各 zone origin 平移，破坏几何。

所以当前 B-O 会形成“JSON/IDF 看见 θ、EnergyPlus 实际忽略 θ”的假完成。

建议修法：B-O 前先拍一个**出口坐标策略**，两条只能选一条并端到端证明。

1. **推荐候选 R（Relative）**：GlobalGeometryRules 改 Relative；所有 Zone Origin/Direction 明确归零或把每个 detailed surface/fenestration 转成严格 zone-local 坐标；Building North Axis 写 θ。同步审计 daylighting reference、building/site shading 等坐标对象。
2. **候选 W（World）**：保留 World，在 EP serializer 边界把所有 building-bound coordinate objects 旋到 true-world；IDF 的 Building North Axis 写 0（θ 只留审计元数据），并同步旋转 zone origins/相关参考点。不能既旋 vertices 又写有效 θ 造成双转。

无论选哪条，新增 θ=0/90/270 合成端到端：比较 EnergyPlus 报告的 exterior surface azimuth/solar orientation，且非零用例不得出现 “North Axes ... ignored” warning。E4 整体工作量应从 **S 改为至少 L、先出独立细稿**，依赖不只是 B2，还包括 zone/surface/fenestration/setting 出口与 EP 门。

### R2-B-02 — HIGH — E4 尚无唯一写入者，0 也未区分“真值零”与“未知默认”

`src/agent/intakeoutput.py:22-47` 现实是 4_MEP 的 `MepOutput` 拥有整个 `BuildingSchema`，5_intakeoutput 原样复制 `mep.building`；而 `BuildingSchema.north_axis` 又默认 0。v2 写“correction→5 装配填值”，但没有规定 MEP 值被删除、覆盖还是对账。结果可能是 LLM 重写确定性 θ，或缺值被 Pydantic 提前变成 0，使下游无法判断 0 是 observed 还是 assumed。“MCP create_building 参数必填”只证明最终调用要有数，不证明上游已经有唯一权威。

同时，角度合同缺少可编码定义。EnergyPlus 的正方向是“从真北到建筑 +Y 的顺时针角”，范围 `[0,360)`；CV 读到的是 image pixel vector，必须经过 page rotation/mirror 与 image→building frame 变换才能得到该角。普通“南立面”标题可能按地理方位命名，也可能按建筑轴命名，不能在没有 `direction_semantics` 时当硬 sanity。

建议修法：

- north axis 的唯一 owner 定为 accepted correction/orientation artifact；5 的 `assemble_intake_output` 显式接收它并对 `mep.building` 做 deterministic override，或从 MepOutput 的 authorable fields 中移除该字段。两条运行路径调用同一 merge/check，冲突硬错。
- v3 用 typed evidence value：`value_deg`、`provenance(observed|derived|assumed)`、`source_ids`、`uncertainty_deg`、`method`、`frame_transform_hash`；最终 0 可照常写 EP，但 unknown/assumed 状态不能丢。
- gt 只有在 gt 有值且产品 provenance 非 assumed 时计角度误差；assumed 0 展示/报告但该 claim 为 NA，不能因“两边都有 float”误计。
- 把“CV ±2–3°”记录为测量 uncertainty，不直接等同 scorer tolerance，也删除“太阳辐射对度级误差不敏感”的无条件断言；遮阳敏感模型不保证该结论。

## 四、v2 六个开放问题：明确建议

### 1. E1′.4 是否完全闭合 A-02？

**对首审 A-02 的原问题：是，CLOSED。** 它已准确保留 local→world 与 room 的 A1/A3 责任，D10#2 只窄修为 world-frame 后的确定性引用。但 E2′新增 plan-only hidden 窗后，要按 R2-A-01 把“宿主唯一性”和“立面可见性”解耦；这是 v2 新特性间的交叉缺口，不应倒退到“所有窗都由 A3 猜段”。

### 2. E2′是否完全闭合 A-03/A-04，partially_applicable 怎么判/画？

**A-03 CLOSED；A-04 PARTIAL。** 必须把状态从 `opening` 级提升为 `opening × claim`：至少 `existence/host/along/width/sill/head/appearance` 各有 `applicable | partially_applicable | not_applicable`、reason、evidence interval 与 source ids。产品 provenance 与 judge applicability 是两条轴：sm26 可有 assumed sill/head 值，但 scorer 对 sill/head 仍 NA；along/width 由 plan 计分。

`partially_applicable` 不能把整窗按半分或整窗灰掉：score sidecar 分 claim denominator；render 的几何本体按 observed/derived/assumed 三色，另用灰纹/标签显示哪些 claim/interval 不计分。若 only-elevation 窗跨 visible/hidden boundary，存在性可成立，完整 width/head 等无法证明的 claim 单独 partial/NA。

### 3. 新 DAG 是否无环，V 是否应并入 B2？

**文本图无环，但生产依赖仍不真实；V 不应并入 B2。** V 的 segment/visibility 几何核保持 gt-blind 纯函数是正确的，也值得独立穷举测试。应把 manifest 从 B5b 拆成 reading 前的独立前置 `B-M`，并把 V 分成纯几何 `Vg` 与薄 applicability adapter `Va`：

```text
B-M (trusted manifest schema/generator; before 0_reading)
B2 -> B3 -> B2b
B2 -> Vg (segment + visibility pure geometry)
B-M + Vg -> Va (claim applicability)
Vg -> B4a
B4a + Va -> B4b -> B5 -> B5b(report/coverage/archive/HTML only)
B2 -> E4-output-contract -> B-O
all above + sm25/26 -> B6
```

B5b 不再“造 manifest”，只消费并归档其 hash。E4-output-contract 先闭 R2-B-01，B-O 才可开工。

### 4. schema v3 槽位是否覆盖充分？

**否，当前仍不是可冻结 schema。** 明确建议如下：

- 选定 `Floor.id`（immutable）+ `Floor.footprint`（typed exterior ring）内嵌方案；不要再保留“dict 键或内嵌”的二选一，也不要用可改名的 `Floor.name` 作主键。
- 类型化 `FacadeSegment`：`id/floor_id/facade_family/p1/p2/normal/world_along_interval/depth/visible_intervals/source_footprint_fingerprint`。
- `Window.facade_segment_id` 加 field-level evidence/provenance map；segment ref 不取代 room。
- `north_axis` 用 R2-B-02 的 typed evidence value；`knowledge_ref` 用不可变五元组。
- “observed zero / unknown fenestration”、per-claim applicability 与 accepted-attempt identity 放各自 versioned coverage/scorer sidecar，不硬塞进 CorrectedGeometry；view manifest 也有独立 schema/version。
- `completion_mode` 留在 RunConfig，不进几何 schema；给 v3 几何子模型 `extra="forbid"` 或等价 unknown-field gate，v1/v2 通过 adapter 保持 legacy 宽容。

完成上述精确类型后，C2 内一次 bump 到 v3是可行目标；但“一次性冻结”不能解释为以后发现契约缺口也禁止 bump。

### 5. E4 的 ±2–3° 是否需要 sanity 门？“南立面”能否交叉验证？

**需要 sanity，但普通图名只能是 hint，不能作硬门。** 硬门应包括：箭头 shaft/head 方向唯一、page rotation/mirror 已解析、image→building transform 有 hash、多枚 north marks 在 uncertainty 内一致、显式 metadata 与 glyph 差超过阈值时记 conflict、角度正规化到 `[0,360)`。manifest 增 `direction_semantics: building_axis | true_azimuth | unknown`；只有图纸明确声明立面标题是地理方位时，才可与 glyph 做独立交叉验证。

测量 uncertainty 与验收 tolerance 分开配置；θ=0/90/270 的正负号/World-vs-Relative EP probe 比“看起来像南立面”更重要。

### 6. 知识库路径与 `window_modules` schema 怎么定？

**C2 保持 `src/configs/knowledge/`。** 它是当前 runtime 的结构化、可版本化配置，且现有 `correction.yaml`/loader 已提供相邻范式；等知识需要跨 runtime 独立发布、人工策展或外部服务消费时再迁顶层包。目录当前不存在是“尚未实施”，不是设计冲突；施工须加 typed loader、wheel/package-data smoke test 与可选测试 override，不能让业务代码散读 YAML。

第一张表至少冻结：

| 层级 | 必需字段 |
|---|---|
| dataset | `schema_version`, `dataset_id`, `dataset_version`, `units: m`, `space_type_taxonomy_version`, `content_sha256` |
| entry | `entry_id`, `applies_to`（space/building/jurisdiction/条件）, `default_candidate_id`, `source_refs` |
| candidate | `candidate_id`, `sill_m`, `height_m`, `priority`, `valid_when`（含 ceiling/clearance）, `source_refs` |
| source | `source_id`, title/edition, locator（页/条款）, URL/作者或机构, license/notes |

加载硬门：id 唯一、每 entry 恰一默认、priority 无并列、值有限且正、`sill+height` 在当前 floor ceiling 内；最终 z 由 `z_floor + sill/head` 派生。消费规则按 R2-A-02：prior_fill 走唯一默认，interactive 列候选，LLM 不做无证据抽签。

## 五、D1–D10 与批次真实性结论

- D7/口字形：v2 维持“带洞留 C3”，**无冲突**。
- D10#2：E1′.4 的原窄修订**可接受**；R2-A-01 只要求按证据源拆 resolver，不把段几何交回 LLM。
- D10#3/#6：语义兼容与独立容差已恢复，**继续有效**。
- D10#4/#5：B3→B2b 与 V→B4a/B4b→B5 主链成立；manifest 须按 Q3 前移。
- E4 是 D1–D10 之外的新能力；当前“只接既有字段即可”的代码现实断言不成立，必须把 GlobalGeometryRules/坐标出口纳入设计，不能借“不变量 #6”把实际跨阶段 seam 隐去。

| 批 | 二审依赖结论 | 工作量档 | 当前可开工性 |
|---|---|---:|---|
| B-M（应新增） | reading 前独立生成 trusted manifest；V-a/B4b/B5b 消费 | M | 需细稿 |
| B2 | 依赖 B1；v3 精确 schema + helper + finalize | L | 补 Q4 后可开 |
| B3 | 依赖 B2 | M | B2 定稿后机械性较高 |
| B2b | 依赖 B2+B3 | XL | 独立细稿后开 |
| Vg/Va | Vg 依赖 B2；Va 依赖 B-M+Vg | L | 独立细稿/穷举测试 |
| B4a | 依赖 Vg | XL | 独立细稿 |
| B4b | 依赖 B4a+Va；先冻结 per-claim schema | XL | 不可直接开 |
| B5 | 依赖 B2+B4b；落实 source-aware resolver | XL | 不可直接开 |
| B5b | 依赖 B5；只做 coverage/report/archive/HTML，manifest 已前移 | L | 需细稿 |
| E4-output-contract + B-O | 依赖 B2，并跨 setting/zone/geometry/assembly/EP；不是单纯字段接线 | **L（原 S 作废）** | R2-B-01 裁决后开 |
| B6 | 依赖全部前件+用户图 | S（词汇）+L（E2E） | 词汇可机械；E2E 后置 |

机械批结论不扩大：仍只有 **B3（B2 定稿后）**与 **B6 纯词汇**接近机械执行；其余都需细稿。不得按 v2 表直接连续施工 B2→B6。

## 六、重新送审门

要从 REWORK 升到 APPROVE-WITH-CHANGES，设计稿至少须：

1. 选择并写死 E4 的 Relative 或 World 出口策略，补 EP 方位端到端验收，重估 B-O。
2. 写死 north-axis 唯一 owner、角度语义、unknown/assumed 与 gt 计分规则。
3. 按 evidence source 拆 window host resolver，并补 negative-evidence 条件。
4. 冻结 per-claim applicability、v3 精确类型、B-M 前置 DAG。
5. 把知识多候选策略改成 deterministic default/interactive，并冻结第一张表 schema；定义 interactive 停机/恢复合同。

## 审阅需求（review-ask）

需主控裁决一项会改变下游几何出口合同的选择：E4 采用 **Relative + 有效 `Building.North Axis`**，还是保留 **World + 在出口旋转所有坐标对象且 IDF North Axis 写 0**。本审倾向先对“Relative + Zone Origin/Direction 全 0 + 现 building-frame detailed vertices”做最小 EnergyPlus probe；若 probe/下游对象审计成立，再选 Relative。未裁前，B-O 不应开工。
