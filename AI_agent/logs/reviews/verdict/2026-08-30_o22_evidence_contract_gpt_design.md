# ②-2 前置设计 · correction 消费多形态墙证据的契约

- **日期**：2026-08-30
- **席位**：GPT 家族设计出稿
- **性质**：可施工设计稿，**不是代码、不是裁决**
- **复核工作点**：当前主树 `08.23_AsDrawnReading`，复核时 HEAD = `c7c17b4`；请求书所列基线虽为 `bc8e354`，下述四条承重事实在当前主树仍逐条成立
- **返工工作点**：同一主树、同一分支；返工派单点为 `fd4e666`。开工时 HEAD = `0b837b8`，其相对派单点只改 `AI_agent/plan.md`，本稿、返工单、裁决书、f9 fixture 与本稿引用的承重代码均无差异
- **返工依据**：[`2026-08-30_o22_design_crossreview_glm.md`](2026-08-30_o22_design_crossreview_glm.md) 的 B-1 与 NF-1～NF-9；本稿保留已过审主体，累计补强而非另起方案
- **范围**：reading → correction 的墙证据接缝、correction 内的基准转换与三拍协议；⛔ 不设计或改动 gt 侧

## 一、结论先行

本单不应把请求书转写的“六形态”原样做成一个 discriminated union。它混了三种不同性质的东西：

1. `paired_faces` / `solid_band` / `single_face` 是**正向墙语义声明的观测表示**；
2. `axis_trace` 其实只是旧输入在**明确声明中线基准时**的一种特例；当前旧 `ReadingView` 并不保证这一点；
3. `ambiguous` / `non_wall` 是对面线的**消费处置**，而且二者也不等价：`ambiguous` 是弃权，`non_wall` 是明确的否定性语义断言。

因此本设计改成三块正交契约：

```
原始观测（不可改、按 hash 引用）
        │
        ├─ 正向墙声明：4 种
        │    paired_faces | solid_band | single_face | legacy_wall_trace
        │
        ├─ 面线消费台账：3 种
        │    claimed_wall | non_wall | ambiguous
        │
        └─ 候选图：pair_candidates 等代码枚举的可复核现象
             ⛔ 不是墙、⛔ 不是 correction 可以越权重做的感知结论
```

最终接口不是让 correction prompt 直接阅读任一种 reading JSON，而是：

```
已声明 reading 源契约
  → 按 view manifest 逐槽适配
  → CorrectionEvidenceBundleV1（统一、严格、带原始引用）
  → 代码编译 provisional WallAssemblyIR + 待裁决包
  → 模型只返回候选决定与总体 finding
  → 代码算坐标，产出 CorrectionResolvedV1（墙厚与基准仍在）
  → 几何内核
```

旧 `ReadingView` 与新 as-drawn 源契约在**源注册表中并存**；进入 correction 后不保留两条执行腿，二者都必须适配成同一份 `CorrectionEvidenceBundleV1`。未知、同槽重复、单文件多重匹配、声明了却验不过自身模型的输入，全部响亮失败。

## 二、四条承重前提复核

| # | 当前主树实测 | 结论 |
|---|---|---|
| 1 | [`pipeline.py:367`](../../../../src/agent/pipeline.py#L367) 仍写 `world-frame, wall-centerline`，[`:370`](../../../../src/agent/pipeline.py#L370) 仍写 `wall CENTERLINE` | ✅ 成立。基准要求属于 correction prompt，不属于新 reading |
| 2 | [`vector_contract.py:205-219`](../../../../src/agent/reading/vector_contract.py#L205) 中唯一 `CONSUME` 是 `_detect_legacy_reading_view`；它同时要求显式 `strokes` list 且能被 `ReadingView.model_validate` 解析（[`:153-178`](../../../../src/agent/reading/vector_contract.py#L153)） | ✅ 成立。F-97 的“只吃声明契约、未知响亮失败”已经承重，不能绕开 |
| 3 | 全仓 `class\s+\w*(Hypothes\|Percept)\w*` 对 Python 类零命中；[`as_drawn_v2.assemble`](../../../../src/agent/reading/as_drawn/as_drawn_v2.py#L560) 直接返回裸 `dict` | ✅ 成立。当前只有 schema 字符串与键形，没有生产者自己的 Pydantic 类型 |
| 4 | [`as_drawn_v2.py:622-631`](../../../../src/agent/reading/as_drawn/as_drawn_v2.py#L622) 原样产出 `pair_candidates`、`pairs`、`non_wall_face_lines`、`unpaired_wall_faces`、`solid_band_walls`、`ambiguous_face_lines` | ✅ 成立。但这些键并不构成同一维度的“六形态” |

四条均成立，故不触发停下上报。

另有一个对本设计承重的反例：[`Stroke.geometry`](../../../../src/agent/reading/schema.py#L49) 是自由 dict，类型上没有墙几何 `basis`。现有真实夹具又同时存在“外皮线”墙笔画（[`f9 ... 1f_view.json:35`](../../../../tests/fixtures/f9_window_host_crash/0_reading/1f_view.json#L35)）和明确写 `centerline` 的墙笔画（[`smalloffice_22/1f_view.json:27`](../../../../case_tests/e2e_tests/smalloffice_22/0_reading/1f_view.json#L27)）。所以“旧 reading 给的是中线 ⇒ 适配成 `axis_trace`”不成立；prompt 要中线不能倒推输入已经是中线。

全仓已经存在 [`RoomRoleObservation.basis`](../../../../src/agent/reading/schema.py#L113)，它描述房间角色判断的依据，不是墙线几何基准。施工新增 `geometry.basis` 时，源模型字段注释必须逐字点明这两处同名字段语义不同，禁止复用或互相回填。

返工开工自检又直接读取
[`f9 1f_view.json`](../../../../tests/fixtures/f9_window_host_crash/0_reading/1f_view.json)：`pen=="wall"` 恰有 10 条，
其 `geometry.thickness_m` 全为 `null`；S1–S4 的 note 写“外皮线”，S5–S10 写“中线”。这份历史产物既是无类型化厚度的 B-1 夹具，
又在同一文件内混合基准，不能靠文件级默认解释。

## 三、源类型与统一证据包

### 3.1 reading 生产者必须拥有自己的类型

在 `src/agent/reading/as_drawn/schema.py` 建 `AsDrawnPlanV2` 及嵌套模型，schema 常量仍由生产者唯一拥有。模型应**逐字段覆盖当前实物**，不是另起一份“理想 v3”：

- 顶层：`schema`、`image`、`image_label`、`observations`、`declarations`、`hypotheses`、`ledger`；
- `observations.face_lines[]`：当前的 `id`、轴、`pos_px/m`、`support_cols_px`、`edges_m`、`runs_px/m`、`gaps`、像素覆盖字段；
- `hypotheses.pair_candidates[]` 与 `pairs[]`：把当前自由 dict 变成类型；
- `non_wall_face_lines`、`unpaired_wall_faces`、`solid_band_walls`、`ambiguous_face_lines`：先忠实接住当前 `dict[face_id, reason_text]`，不要趁建模偷偷重写历史产物；
- `opening_candidates` / `opening_types` 也必须进入源模型。墙接口落地不能把同一份 as-drawn 文件的洞口半边静默丢掉。

生产路径的出口应是 `AsDrawnPlanV2.model_validate(...)` 后再序列化；“有个 detector 猜它像”不能替代生产者模型。

当前 v2 的自由理由字符串可以由适配器结构化，但结构化结果必须反指原 JSON pointer；不能覆盖源产物，更不能把 reason 文本解析成坐标、基准或厚度事实。

### 3.2 原始引用：只引用，不复制一份方便几何

统一使用两层引用：

```text
ArtifactPointerV1
  input_id                 # view manifest 的稳定槽位，不用文件名冒充身份
  source_contract_id
  source_output_sha256
  json_pointer             # 指到原产物中的精确节点

ObservationRefV1 : ArtifactPointerV1
  observation_id
  source_locator           # 复用现有 src:<sha256> 词汇与生成原则
  pixel_witness_pointers[] # 指向 support_cols_px / runs_px / gaps 等；不复制其值
  native_handle            # 仅未来源真的有 handle 时出现；当前图像产物不得伪造
  evidence_resolution      # pixel_backed | vector_only | native_handle_backed
```

现有 window source 已经用 `input_id + observation_id + source_output_sha256` 生成稳定 locator（[`window_sources.py:290`](../../../../src/agent/correction/window_sources.py#L290)）；墙证据应复用同一身份原则，不另造“文件名/行号就是 provenance”的第二套。

持久化的 `CorrectionEvidenceBundleArtifactV1` 应像现有 window resolver artifact 一样携带**原始 reading bytes**及各自 sha256。引用只在这些冻结 bytes 内解析，不能在下一轮重新读一个可能已变化的工作目录文件。`WallClaim` 里不复制 `pos_m`、`edges_m`、`runs_m`；所有派生值由 resolver 从被 hash 绑定的源节点重算。

### 3.3 统一证据包的顶层

```text
CorrectionEvidenceBundleV1
  schema_version = "correction_evidence_bundle_v1"
  view_manifest_sha256
  source_artifacts[]       # input_id / contract_id / sha256 / view_type / floor_ref
  channel_status[]         # walls / plan_openings / elevation_openings / dimensions / room_roles
  wall_claims[]            # 四种正向声明的 discriminated union
  face_dispositions[]      # 三种消费处置
  opening_claims[]         # 复用统一 source locator；本稿不重写其完整业务协议
  evidence_debts[]         # 缺失通道或已知不足，结构化且按 profile 决定能否继续
  content_sha256
```

`channel_status` 是必要的：把 as-drawn 的墙接通，不等于它已经完整替代旧 `ReadingView` 的门窗、尺寸和房间角色。注册表只有在一个源契约的 correction 必需通道都有适配器，或缺失被显式记为当前 profile 允许的 evidence debt 时，才可把它从 `KNOWN_NOT_CONSUMED` 改为 `ADAPT`。⛔ 不允许“墙走新腿、窗悄悄仍从目录里随便找 `strokes`”。

## 四、墙声明不是六种，而是“4 种正向表示 + 3 种处置”

### 4.1 四种正向墙声明

所有正向声明共有：

```text
claim_id                    # 对规范化 source refs 做 canonical hash，非数组下标
kind
hypothesis_ref              # 指到 pairs / solid_band_walls / ... 的原节点
observation_refs[]
perception_source_ref
source_contract_id
```

| `kind` | 几何角色已知？ | 它断言什么 | 它明确没有断言什么 | 必带原始引用 |
|---|---|---|---|---|
| `paired_faces` | 是：墙的两侧面 | 两条被观测面线在二者共同覆盖的沿墙区间内，是同一堵墙的两侧面 | 不断言中线、名义厚度、内外墙、输出基准；也不断言两条面的所有 runs 等长 | 两个 `ObservationRefV1`，各自回指 `observations.face_lines[i]` 及 `support_cols_px/runs_px/gaps`；选中 `pairs[j]` 的 `hypothesis_ref`；对应 `pair_candidates[k]` 的 pointer。`spacing_m` 只作缓存审计，代码必须从两面重算 |
| `solid_band` | 是：墙的墨带 | 一条被观测墨带本身表达一堵墙；该观测自己的两条 `edges_m` 是墨带边界 | 不断言这两边已经是规范墙面、不把 `support_width_m` 命名为事实厚度、不判内外 | 一个 face-line ref；指到 `solid_band_walls.<id>` 的 hypothesis ref；必须指到 `support_cols_px`、`edges_m`、`runs_px` 的像素 witness |
| `single_face` | 是：墙的一张面 | 该观测是墙的一张面；另一面没有成为同一 claim 的已认领 counterface | 不断言另一面是否完全未被观测、在哪一侧、离多远或为何未被认领，也不断言可直接产出中线 | 一个 face-line ref；指到 `unpaired_wall_faces.<id>`；保留原 reason。`counterface_state = not_in_observations \| observed_unclaimed`；后者必须再带被观测但未被认作 counterface 的原节点 pointer 与其 disposition，不能从 prose 猜 side 或 thickness |
| `legacy_wall_trace` | 否：仅知是墙相关线迹 | 旧 `ReadingView` 的某条 `pen=="wall"` stroke 是墙相关线迹 | 除非有类型化字段证明，否则不保证它是中线、外皮或墙面；`geometry.thickness_m` 也不能无条件晋升为实测厚度 | 回指原 `strokes[i]`、stroke id 与 geometry pointer；`source_basis = centerline \| wall_face \| outer_skin \| unknown`。非 `unknown` 必须有**结构化** basis evidence ref；禁止解析自由 `note` 猜基准 |

请求书中的 `axis_trace` 由此降为 `legacy_wall_trace(source_basis="centerline")` 的特例，而不是独立、无条件成立的来源形态。上表也显式承认隐藏轴：前三类是“几何角色已知”的正向观测，`legacy_wall_trace` 是“角色未知”的降级声明；四类仍按“证据与墙的关系”组成同一个 union，但不得拿它们做同层几何角色的完备性证明。

一个重要的保真规则：`paired_faces` 只在两张面实际共同覆盖的区间内编译为双面墙。A 面独有或 B 面独有的余段，必须由代码切成仍引用原 claim 的 `single_face_fragment`；⛔ 不得因为“这两条总体配过对”就取交集后把余段扔掉，也不得把并集全当双面。这正对应指南所记的 T 接头与两侧不同步。

### 4.2 三种面线处置

每一条 as-drawn `observations.face_lines[]` 必须**恰好一次**落入：

| `status` | 语义 | 下游动作 |
|---|---|---|
| `claimed_wall` | 被恰好一个正向墙声明消费；成对面对应同一 claim | 进入墙编译器；重复售卖给两个 claim 是输入完整性错误 |
| `non_wall` | reading 感知明确断言这条面线不是墙，并给出理由/类别 | 代码自动排除并记账；它不是待 correction 猜的歧义，也不是“已知缺失” |
| `ambiguous` | reading 明确弃权：仅凭当前感知不能判断是否为墙 | 合法输入、但形成 known-missing evidence debt；不能静默当 `non_wall` |

因此请求书“`ambiguous` 与 `non_wall` 都是弃权声明”的前提要更正。sm25 实物里的 `non_wall_face_lines` 明确说某些线是厚度标注文字；这是有语义内容的否定判断。把它叫弃权会允许 correction 重开已经由 reading 做完的感知决定。

### 4.3 `pair_candidates` 的地位

`pair_candidates` 是代码枚举的**候选关系图**，不是第五或第七种墙：

- reading 模型从中选择 `pairs`，这是指南已定的感知职责；
- correction 只能用它复核 selected pair 是否存在、重算间距/重叠、解释为何请求重新感知；
- correction 模型不得在 `pairs` 缺失时自行从几百个 `pair_candidates` 里重做墙配对，因为它不看原图，这会把“认”从 reading 偷搬到 correction；
- `pairs_status=ABSENT_NO_MODEL_SELECTION` 或 selected pair 不在候选图中，进入 `reperception_required` / 输入错误，不得用互为最近邻等代码规则补一条腿。

### 4.4 统一包的硬不变量

适配完成后、调用任何 correction 模型之前，代码必须验证：

1. 每个 source ref 的 `input_id + sha256 + json_pointer + observation_id` 都能在冻结原始 bytes 中唯一解析；
2. 每条 as-drawn face line 恰好一个处置；无桶、跨桶、重复墙 claim 全部响亮失败；
3. `paired_faces` 的两 ref 不同轴、同一 observation 自配、选中项不在重算候选图中，全部失败；
4. `solid_band` / `single_face` / `non_wall` / `ambiguous` 引用的 id 必须真实存在；
5. 一个 manifest 语义槽位只能有一个源产物；同一 1F plan 同时给 legacy 与 as-drawn 是 `DUPLICATE_SEMANTIC_INPUT`，不能靠文件排序选赢家；
6. 所有 detector 全跑；单文件命中两个源契约是 `AMBIGUOUS_CONTRACT_MATCH`；
7. 显式声明了 schema 但验不过该 schema 的生产者模型，是 `MALFORMED_DECLARED_CONTRACT`，不得回退成 legacy；
8. canonical 排序与 `content_sha256` 一致；同一原始 bytes 必须生成逐字节相同的证据包。
9. **basis 无 centerline 证据的墙，其候选集不得包含 identity 类操作；已进入 `open_items` 的 item 不受“只剩一个候选 / Pareto 支配 ⇒ 自动执行”管辖（该规则只适用于未开项情况）。**

## 五、基准在哪里转换，以及厚度怎样活到内核

### 5.1 转换位置与职责

基准转换只能发生在 correction 内的**确定性 provisional compiler**：

```
CorrectionEvidenceBundleV1
  → resolve source refs
  → segment evidence（保留双面共同段与单面余段）
  → derive provisional wall support-lines
  → topology / dimension / declaration consistency
  → WallAssemblyIR + open_items
```

reading 不新增 `centerline` 方便字段，适配器也不生成一份“中线版 reading JSON”。适配器只做契约翻译和引用绑定；真正坐标派生由 correction compiler 完成并写 derivation record。

### 5.2 四种输入怎样派生

| 输入 | 代码可直接做的事 | 必须留给待裁决/重新感知的事 |
|---|---|---|
| `paired_faces` | 从两条原面重算共同区间、观测间距和几何中分线；共同段的中线坐标是纯代码结果 | 保持观测宽度还是吸到某个 callout/模数；存在多个设计轴/拓扑解释时选哪一个 |
| `solid_band` | 从该墨带两条原始 edge 重算中分线与 observed width | 该观测宽度是否代表设计厚度、是否模数化 |
| `single_face` | 保留这张面作为锚，枚举“向正侧/负侧按候选厚度偏移”等**符号候选**，坐标预览由代码算 | 没有唯一 side/thickness 依据时不得自动造中线；需要总体判断或重新感知 |
| `legacy_wall_trace` | `basis=centerline` 时原线可作 provisional axis；显式 `wall_face/outer_skin` 且有唯一厚度/方向规则时由代码偏移 | `basis=unknown` 必须先开项；无论有无 `thickness_m`，都先按 §4.4 #9 排除 identity，且开项后不得再被唯一候选/Pareto 自动规则消化 |

墙角不传播原观测端点。遵守指南 §十#6c：传播的是 resolved support-line，最终多边形角点由相邻 support-lines 求交；原 `runs/along intervals` 只控制证据覆盖、洞口落位和墙段有效区间。

### 5.2.1 ⭐ 同形但不同输入：`basis=unknown` 且有厚度

这不是只给 f9 的 `thickness_m=null` 打补丁。真实 legacy 产物
[`sm25-L_anchor/.../1f_view.json` 的 W01](../../../../case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H1/0_reading/1f_view.json#L12)
具有与 f9 相同的旧 `Stroke.geometry` 形状：它有
[`thickness_m=0.239`](../../../../case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H1/0_reading/1f_view.json#L29)，
但 geometry 内没有类型化 `basis`。自由 note 即使写了 `centreline` 也不满足结构化证据门。因此它在 adapter 后是
`legacy_wall_trace(source_basis="unknown")`。该实物已在 `/tmp` 的主树归档副本上用
`ReadingView.model_validate` 与 `_detect_legacy_reading_view` 求证，二者都接收；模块来源哨兵指向 `/tmp` 副本。

按本设计逐门推演：

1. 非空厚度只给 compiler 一个可用于构造 `OFFSET_POSITIVE(thickness_ref)` / `OFFSET_NEGATIVE(thickness_ref)`
   等符号候选的尺度；它不能证明原线本来就是中线，也不能证明偏移方向。
2. §4.4 #9 在候选生成门先删去 `IDENTITY_AS_CENTERLINE`；note、prompt、最小扰动均不能把它放回来。
3. `basis=unknown` 随即进入 `open_items`。若正负偏移都存活，它显然不是自动唯一；若拓扑或尺寸硬约束把候选压到唯一，
   或某候选 Pareto 支配其余候选，§4.4 #9 的后半仍禁止 executor 自动吃掉这个**已开项** item。
4. 合法终点只能是绑定 packet 的显式模型决定、墙级定向再感知，或 profile 允许且带 residual debt 的 degraded；
   候选为空则 `unsupported_or_reperceive`。任何终点都不会产出静默 identity 中线。

因此“有厚度”不会把 unknown 偷换成 centerline；它至多丰富待裁决的偏移候选。这个反例锁的是整类输入，
与 f9 的“无厚度、候选可能只剩 identity/空”是不同分支。

### 5.3 厚度的三个名字必须分开

`spacing_m` 不能一路改名成 `thickness_m`。correction 内至少保留：

```text
observed_face_spacing_m     # 两面/墨带边缘的观测间距；不可覆盖
resolved_thickness_m        # correction 选择后的设计厚度；代码执行决定后产生
thickness_resolution
  operation_id              # KEEP_OBSERVED_WIDTH / SNAP_TO_DECLARATION / ...
  source_values[]           # observation refs / callout refs / dimension refs
  decision_id               # 自动动作或模型候选决定
  delta_m
```

`matched_declared_mm` 仍只是“这个观测间距落在某个声明附近”的标签，不能直接成为 `resolved_thickness_m`。只有已签确定规则唯一命中，或模型从代码枚举的候选中选中某个符号操作后，执行器才能产出 resolved thickness。

### 5.4 内核入口必须携带墙 IR，不能再只剩房间多边形

新增代码产物而不是扩张模型输出：

```text
ResolvedWallV1
  wall_id
  source_claim_ids[]
  source_refs[]
  resolved_centerline       # 代码坐标
  resolved_along_intervals  # 代码坐标
  observed_face_spacing_m
  resolved_thickness_m
  observed_basis
  output_basis               # Literal["wall_axis", "outer_skin"]
  boundary_role             # topology 完成后由代码确定
  thickness_resolution
  derivation_hash

CorrectionResolvedV1
  resolved_walls[]
  corrected_geometry_projection
  opening_resolution
  auto_actions[]
  model_decisions[]
  residual_evidence_debts[]
  content_sha256
```

`output_basis` 不另造 correction 方词表，值域机械复用判分侧既有
[`CompiledZoneEdgeV1.basis: Literal["wall_axis", "outer_skin"]`](../../../../src/agent/judge/answer_compiler.py#L110)：
canonical 中线输出写 `wall_axis`，外皮输出写 `outer_skin`；`centerline`、`wall_face`、`unknown` 只可出现在
`observed_basis` / open item，不能作为 `output_basis` 发给下游。这里仅引用既有定义，不修改 gt 侧。

兼容投影必须带可消费的债务落点，不能只落一份裸 `CorrectedGeometry`：

```text
CorrectedGeometryProjectionEnvelopeV1
  source_resolved_sha256
  geometry                         # 由同一 CorrectionResolvedV1 确定性派生
  completion = complete | degraded
  residual_evidence_debt_ids[]
  projection_sha256
```

attempt/report 记录必须消费这个 envelope，并保存 `source_resolved_sha256`、`completion` 与 debt ids；strict profile
在投影交给 judge 前拒绝 `degraded`，exploratory profile 可以照常把 `geometry` 交给现有 judge，但报告必须显示
`degraded` 且不得缩 judge 分母。当前 `correction_score.py` 不读 conflicts/degraded，正因如此，状态权威必须留在
envelope/attempt 记录而不能指望 judge 从几何猜出来。丢 envelope、hash 对不上、debt ids 与
`CorrectionResolvedV1.residual_evidence_debts` 不闭合，都是投影失败，不得把裸 geometry 当完整产物。

几何内核的权威输入改为 `CorrectionResolvedV1`，其中 `resolved_walls` 承载墙线、厚度、basis 与原始引用。现有 `CorrectedGeometry(V3)` 可以暂时保留为**从同一 resolved wall IR 确定性派生的兼容投影**，但不能与 `resolved_walls` 成为两份并列真相，也不能继续由模型直接手填。

由此 R-6 在 pipeline 侧不再复发：厚度不是“量了 → 中线算过 → 只存 polygon 时扔掉”，而是 observation spacing 与 resolved design thickness 两层都跟随 wall 到 kernel，并能解释由厚度/basis 产生的 10 mm 等真实台阶。

## 六、三拍循环落到契约上

当前 [`run_correction`](../../../../src/agent/pipeline.py#L732) 仍是模型直接返回完整 `CorrectedGeometry`，失败时最多重抽三次；这不是本指南定义的“三拍”。新契约不能只包住现有 prompt，必须把 producer contract 改为“决定响应”。

### 6.1 第一拍：代码编译 provisional + 待裁决包

```text
CorrectionDecisionPacketV1
  packet_hash
  input_bundle_hash
  solver_revision
  round_index
  previous_decision_hashes[]
  provisional_geometry
  provisional_wall_summaries[]
  entity_to_source_refs[]
  auto_actions[]
  consistency_results[]
  open_items[]
```

每个 `open_item`：

```text
item_id
kind
scope_entity_ids[]
phenomenon                 # 代码重算事实，不是模型描述
source_refs[]
hard_constraints[]
candidates[]
why_not_auto_resolved
dependencies[]
exclusions[]
```

每个候选：

```text
candidate_id
symbolic_operation         # 枚举；不含坐标
preconditions[]
predicted_effects
cost_vector                # 观测位移/声明残差/拓扑变化/跨层差异/信息损失
preview_geometry_hash
reversibility
```

代码自动处置并记账的边界：

| 情况 | 处置 |
|---|---|
| ref、hash、完备性、互斥性不成立 | **输入完整性错误，停；不是让模型修 schema** |
| `non_wall` | 自动排除，写 `auto_actions(kind=honor_non_wall_declaration)` |
| 双面/实心带的中分线计算 | 自动；这是坐标运算，不是设计决定 |
| 显式 centerline legacy trace | 自动 identity，并写 basis 证据 |
| **未进入过 `open_items`**，且硬约束筛后只剩一个候选，或一候选在全部 cost 维度 Pareto 支配其余候选 | 自动执行并记账；此规则不得用于“回收”已经开项的 item |
| 已签规则唯一决定的数值闭合、同墙连续段接缝 | 自动；规则 id 必须入账 |
| `single_face` 的 side/thickness 多解、legacy basis unknown、互不支配的设计轴/拓扑候选 | **先**进入 `open_items`；即使后续筛成唯一或 Pareto 支配也仍需显式决定/再感知 |
| reading `pairs` 缺失、`ambiguous` 可能影响墙拓扑 | `reperception_required`；不让 correction 代做读图 |
| 没有任何合法候选 | `unsupported_or_reperceive`，⛔ 不选最近值 |

执行优先序是：先过输入完整性门，再应用 §4.4 #9 的 basis/identity 候选门，再判定是否开项，最后才允许对
**从未开项**的候选使用唯一候选/Pareto 自动规则。`open_items` 是状态边界，不是一个能被隔壁自动表重新分类的展示列表。

### 6.2 第二拍：模型只输出决定 + 总体把控

```text
CorrectionDecisionResponseV1
  packet_hash
  item_decisions[]
    item_id
    action = select_candidate | reject_all | request_reperception
    candidate_id            # 仅 select_candidate 时
    reason_code
  whole_building_review
    verdict = accept | findings
    findings[]
      finding_id
      kind
      affected_entity_ids[]
      source_refs[]
      requested_effect       # RequestedEffectV1 discriminated union，不含坐标
      rationale
```

`requested_effect.kind` 的封闭值域为：

| `kind` | 允许模型指定 | 代码怎样消费 |
|---|---|---|
| `review_alignment` | packet 内的 subject/reference entity ids；关系仅限 `collinear/parallel/perpendicular` | compiler 从这组既有实体生成有界 alignment candidates；模型不提供目标线或坐标 |
| `review_segmentation` | packet 内 subject ids；关系仅限 `split_required/merge_review_required` | compiler 根据 source intervals 枚举切分/合并候选 |
| `review_topology_relation` | packet 内 subject/reference ids；关系仅限 `connect/separate` | compiler 枚举合法连接或分离操作并重跑围合 |
| `review_opening_host` | packet 内 opening id 与候选 wall ids | opening resolver 生成 rehost 候选；finding 本身不改 host |
| `request_wall_reperception` | packet 内 wall/item ids、source refs 与 reason code | 生成 §7.3 的墙级定向请求，不生成几何 |

每个 kind 使用自己的 strict schema，禁止未列字段；所有 entity/ref 必须已在 packet 中。模型指定“参照谁/检查何种关系”
只是下一轮候选生成输入，不是吸附坐标。executor 只执行下一轮 packet 明列、重新 hash 后的 symbolic candidate。

模型输出 schema `extra="forbid"`，不存在任何 `x/y/z/p1/p2/span/thickness_m` 字段。出现坐标、直接新造 wall id、选择不在 packet 内的 candidate、回复陈旧 packet hash，全部拒绝。

`whole_building_review.findings` 必须允许模型指出代码未列出的总体问题，例如走廊幻墙、Z 形未分段、内墙画穿；但 finding 不能当场执行。代码把 finding 翻成下一轮新的有界候选，再让模型从候选中决定。这样总体通道存在，同时不打开“模型一句 prose 直接改坐标”的后门。

### 6.3 第三拍：代码执行、复算、有限回环

执行器只接受绑定当前 `packet_hash` 的响应：

1. 校验 response 与候选集合；
2. 运行 `symbolic_operation`，所有坐标/厚度/交点由代码求；
3. 更新 `ResolvedWallV1` 与 source trace；
4. 重跑拓扑、围合、重叠、洞口 host、跨层与信息保存检查；
5. 总体 finding 生成新候选，仍有 open item 则进入下一轮。

成功条件必须同时满足：无 blocking open item、确定性检查通过、模型对**同一个 provisional hash** 给出总体 `accept`、没有 strict profile 不允许的 residual evidence debt。

无进展、decision hash 循环、陈旧 packet、轮次预算耗尽时响亮退出并保留残余清单；最后一次 provisional geometry 不是成功产物。

## 七、`ambiguous` 与 `non_wall` 的进出规则

### 7.1 `non_wall`

- 它是 reading 模型已经做出的**否定语义判断**；correction 代码尊重、排除、记账。
- correction 整体审查若发现“这里缺一堵墙才围得起来”，可以产生 `request_reperception` finding，点名原 `non_wall` source ref；不得直接把它晋升为墙。
- 谁判：初判归看图的 reading 模型；结构完备性与引用互斥归代码门；复查仍归 reading 模型。correction 模型只提出“请复查”的建筑总体理由。
- 一个 `non_wall` 引用不存在、同时又被墙 claim 消费，是**契约错误**，不是已知缺失。

### 7.2 `ambiguous`

- 它是合法、诚实的弃权，解析契约时不是错误；进入统一包后状态是 `known_missing`。
- correction 编译器对它做依赖分析并生成 `reperception_required`：列出它能参与的 pair candidates、可能影响的 provisional entity 与为什么代码不能定。
- strict/production profile：只要它可能改变房间围合、墙拓扑、洞口 host 或出模边界，就阻止成功，回 reading 重感知。
- exploratory/历史 profile：可在明确 `completion=degraded`、保留 residual debt、judge 不缩分母的前提下继续；⛔ 不得把它记录成已处置的 non-wall。
- correction 模型没有原图，不是重新判断 wall/non-wall 的合法主体；它只能选 `request_reperception`，或在 profile 明确允许时接受“带已知缺口的探索产物”。

这一区分同时保住两条：模型可以诚实说“认不出来”；弃权也不能悄悄换来一份自称完整的建筑。

### 7.3 墙级定向再感知，以及 note 的边界

unknown 的第三条路不是整图重跑，也不是配置逐图补默认，而是**墙级带锚点定向再感知**：compiler 从
`scope_entity_ids + source_refs + pixel_witness_pointers` 生成墙区域 crop 请求，reading 模型在能看到原图的层重新返回
类型化 basis 声明、像素 witness 与新的 source artifact；新 artifact 仍走 §3.2 的 sha256 身份绑定和 adapter，
不能由 correction 直接回填。调用成本随 unknown 墙数线性增长，即
`O(unknown 墙数)`，不是按整图全通道重跑；该量级沿用
[`GLM 裁决 §二 NF-2`](2026-08-30_o22_design_crossreview_glm.md#L147) 的复核结论。

自由 note 的禁令要分清主体：**代码**不得正则解析 note 成 basis/thickness/side 事实；但 note 可以作为
`open_item.untrusted_context` 给决定模型看，供它解释为何选择 `request_reperception` 或某个已存在的非 identity 候选。
它永远不生成结构化 basis evidence ref、不满足 §4.4 #9 的 centerline 门、不让 identity 进入候选，也不能触发自动动作。
真实存量 note 同时存在互相冲突的“中线/centerline”与“外皮”信号，具体计数见
[`GLM 裁决:126-129`](2026-08-30_o22_design_crossreview_glm.md#L126)，所以推荐路径始终是有图的墙级再感知，
note 只是一条不受信线索。

## 八、新旧契约并存与判别器

### 8.1 并存什么，取代什么

- **并存**：源注册表中的 `reading_view_legacy`、`as_drawn_plan_v2`，以及尚未升级的 elevation 源契约；允许不同 manifest 槽位使用不同源契约，例如新 plan + 旧 elevation。
- **取代**：correction 直接把某类源 JSON 整份 paste 给模型的执行方式。所有源先适配成统一 bundle；prompt/模型只看 provisional packet。
- **不允许**：同一 manifest 槽位同时给旧 plan 和新 plan；也不允许发现新 plan 不好处理后静默回退旧 plan。
- 迁移期保留旧直通路只能是显式命名的对照/影子 profile，有独立 ledger，不能成为生产 fallback。

### 8.2 判别算法

1. 从 view manifest 取得 `input_id/view_type/floor_ref/expected_output_id`；文件名只用于定位，不用于决定契约。
2. 每个文件运行全部注册 detector；每个 detector 必须调用**生产者自己的 Pydantic 类型**。
3. 无 schema 的文件才允许 legacy structural fallback：显式有 `strokes` 且 `ReadingView` 解析成功。
4. 文件只要声明了 schema，就必须按该 schema 的类型与 required shape 成功；失败不得 legacy fallback。
5. 单文件 0 命中或 >1 命中都失败并写 ledger。
6. 目录级按 manifest 槽位检查唯一性、必需通道与 source sha；同槽双源失败。
7. 分类结果从今天的 `CONSUME / KNOWN_NOT_CONSUMED / EXCLUDE` 收窄为 `ADAPT(adapter_id) / KNOWN_NOT_ADAPTED / EXCLUDE`；不存在“分类成功所以可直接贴 prompt”。

### 8.3 legacy basis 的迁移纪律

旧 `ReadingView` adapter 对 `pen==wall` 一律先产 `legacy_wall_trace`：

- 新增的类型化 `geometry.basis` 或**验证通过**的签名 sidecar 明确写 `centerline/wall_face/outer_skin` 时，才填对应 basis；
- 当前历史产物没有类型化声明时填 `unknown`；
- 禁止代码正则解析 `note` 里的 “centerline / 外皮线”；自由文本可作审计展示或 §7.3 的不受信模型线索，不能承重、不能生成 basis evidence ref；
- `unknown` 进入待裁决或重新感知。为追平历史基线而暗设 `unknown→centerline` 会原样复活本单要消掉的基准错误。

`geometry.basis` 的源模型注释必须明确它是“墙线几何相对墙体的基准”，与
[`RoomRoleObservation.basis`](../../../../src/agent/reading/schema.py#L113) 的“房间角色判断依据”同名不同义。
adapter 不得在两者之间拷贝值。

所谓“签名 sidecar”必须是可验证的 `SignedLegacyBasisAssertionV1`，至少把下列 canonical payload 一起签入：

```text
input_id
source_contract_id
source_output_sha256
json_pointer
observation_id
basis = centerline | wall_face | outer_skin
issuer
key_id
```

verifier 必须先按 §3.2 冻结 bytes 重算 `source_output_sha256`，再验证签名覆盖上述完整 payload，并确认 pointer/id
在该 sha256 身份内唯一解析、issuer/key 受当前 profile 信任。任何 hash、pointer、id、签名或信任链不匹配都把声明判无效，
回到 `basis=unknown`；不得“sidecar 文件存在就相信”。这样签名绑定的是 §3.2 的内容身份，而不是可被替换的文件名或一句 prose。

## 九、迁移次序与验收

### 9.1 施工顺序

可开工最小集固定为 §十所列 correction/reading **模块 1–6 + `vector_contract` 的一行 as-drawn adapter 注册**；
这个切片来自 [`GLM 裁决 §五`](2026-08-30_o22_design_crossreview_glm.md#L219)。`CONSUME→ADAPT` 命名收窄与目录 ledger
重排属于模块 7 的收窄工程，已登记 `AI_agent/plan.md`，本批不做；但 as-drawn disposition 指向新 adapter 的注册不能缓，
否则 adapter 永远不会生效。

1. **先建源模型，不改消费**：`AsDrawnPlanV2` 覆盖当前 sm25 1F/2F、sm24 1F 三份产物；生产者经模型出口，现有字段与语义不变。
2. **建统一 source ref 与 bundle**：复用 manifest、source locator、raw bytes/hash 绑定；先 shadow 生成，不进模型。
3. **建双 adapter**：as-drawn → 四种 wall claim + disposition ledger；legacy → `legacy_wall_trace(basis=...)`。验证同槽唯一、引用闭合、面线完整消费。
4. **建 provisional compiler 与 ResolvedWall IR**：先纯代码/固定决定夹具；验证双面余段不丢、四堵 solid band 不丢、厚度活到 kernel。
5. **建 packet/response/executor**：模型输出 schema 无坐标，先用固定 response 测三拍执行器，再接模型。
6. **shadow 双跑**：旧 correction 不改，旁路跑新 bundle/compiler；按同一冻结输入与固定决定比较。
7. **切 prompt 与入口**：模型不再直接填 `CorrectedGeometry`；新旧源都走 bundle。只有到这一步才把 as-drawn 合同 disposition 改成 `ADAPT`。
8. **删除旧直贴腿**：历史回归仍可从 legacy adapter 进入统一路径；未知输入继续由 F-97 响亮失败。

### 9.2 必须有的契约/反证测试

建议按职责落成明确测试函数，而不是散文纪律：

| 测试 | 必须证明 |
|---|---|
| `test_as_drawn_plan_v2_model_accepts_three_current_products` | 生产者模型真实覆盖 sm25 1F/2F、sm24 1F，不是只验一个手造最小 dict |
| `test_declared_as_drawn_missing_required_field_fails_without_legacy_fallback` | F-97 不因新 adapter 回退 |
| `test_single_file_double_contract_match_is_loud` | 所有 detector 全跑，不 first-match-wins |
| `test_duplicate_manifest_slot_old_and_new_plan_is_loud` | 同槽双腿不会按排序静默选一条 |
| `test_every_face_has_exactly_one_disposition` | 无桶、跨桶、重复售卖都红 |
| `test_selected_pair_must_recompute_from_source_faces` | 不信产物缓存的 `spacing_m`/candidate 值 |
| `test_paired_face_unshared_tail_survives_as_single_face_fragment` | 两面不等长时不取交集丢信息、不取并集造双面 |
| `test_sm24_four_solid_bands_become_four_wall_claims_without_fake_faces` | 请求书最直接的反例不会回归 |
| `test_legacy_outer_skin_stroke_does_not_become_axis_trace` | f9 形状的旧外皮线保持 basis unknown/outer_skin，不吃 prompt 默认 |
| `test_unknown_basis_item_is_never_auto_resolved` | 喂 f9 形状的 legacy fixture：墙 stroke 无类型化 `geometry.basis`、`geometry.thickness_m=null`，note 即使写外皮也只作审计。断言 packet 中有对应 `open_item` 或终点为 `unsupported_or_reperceive`，候选集不含 identity；`auto_actions` 不出现 identity/中线动作，且 executor 不产出该 claim 的静默 axis trace |
| `test_unknown_basis_with_thickness_still_never_silent_identity` | 喂 §5.2.1 的 W01 形状：`basis=unknown` 且厚度非空。断言 identity 仍不入候选；即使硬约束只留一个偏移或形成 Pareto 支配，已开项 item 仍不进 `auto_actions`，只能显式决定/再感知/degraded |
| `test_non_wall_is_auto_accounted_but_ambiguous_is_evidence_debt` | 两种状态不塌成同一弃权 |
| `test_model_decision_schema_rejects_coordinate_fields` | 模型输出决定、代码输出坐标 |
| `test_stale_packet_hash_and_unknown_candidate_are_rejected` | 三拍响应不能串轮或新造操作 |
| `test_same_bundle_and_decisions_produce_byte_identical_resolved_artifact` | 编译器/执行器确定性 |
| `test_observed_spacing_and_resolved_thickness_survive_kernel_entry` | R-6 不在 pipeline 重演 |

### 9.3 `feed-the-answer-in-to-test-the-code-alone`

至少建两层“喂答案”夹具，均不调用 LLM：

1. `test_signed_decisions_compile_to_known_resolved_walls`：手造一份含四种正向来源、已填合法 candidate 决定的 response，执行器必须逐位产出已知 `ResolvedWallV1[]`，包括 source refs、observed spacing、resolved thickness、basis 与中线坐标。
2. `test_resolved_correction_answer_runs_kernel_without_model`：手造一份完整 `CorrectionResolvedV1` 当作 correction 已答对的答案，从 correction 之后直接喂内核；断言预期房间/相邻面/墙厚台阶/洞口 host。这样把“决策模型好不好”和“代码拿到正确答案会不会执行错”彻底拆开。

第二条是本单最便宜、也最承重的验收。若它不通过，禁止用真实 LLM 全流程偶然跑通来替代。

### 9.4 “不比现在差”的判定矩阵

不能只报“新契约能 parse”或“全流程跑完”。至少分别报告：

| 对照 | 通过条件 |
|---|---|
| sm25 新 as-drawn plan + 固定决定 vs 冻结 legacy correction 基线 | correction judge 各项不下降；无新增 hard gate；每条 resolved wall 可反查原 face；observed spacing 未覆盖 |
| sm24 新 as-drawn | 4 个 solid band 全部进入墙 IR；不得伪造第二 observation；最终 correction judge 不低于冻结历史基线 |
| 旧 ReadingView 历史 case | **今天没有可验的“显式 centerline 存量子集”**：存量 `pen==wall` 为 1240/1240 unknown，geometry basis 键为 0；读数与空集结论见 [`GLM 裁决:122-146`](2026-08-30_o22_design_crossreview_glm.md#L122)。strict 终点是阻止成功并发墙级定向再感知；exploratory 终点是 `completion=degraded`、保留 open item/debt、projection envelope 显示 degraded，judge 分母不缩。两档都不得宣称“兼容且不下降”。sm21 又没有 as-drawn 产物，strict 必须走墙级再感知，exploratory 只能诚实 degraded；该实物缺口见 [`GLM 裁决:130-151`](2026-08-30_o22_design_crossreview_glm.md#L130)。将来只有出现类型化/验签 centerline fixture 后，才新增非空兼容验收子集 |
| `ambiguous` 反事实 | 删除 debt 或改写为 `non_wall` 不得无记录通过；strict profile 必须阻止完整成功 |
| 厚度反事实 | 只保留中线、丢 observed/resolved thickness 的变异必须被 gate 抓住；只改厚度不改轴、只改轴且破坏双面间距，分别失败 |
| 未知/混装契约 | 未注册 schema、已声明但缺字段、同槽双源、单文件双匹配全部在调用模型前失败且 ledger 点名 offender |

真实模型端到端只能放在上述确定性测试之后。sm25 先跑，sm24 与历史 case 后跑；模型波动不能拿来解释代码验收失败。

## 十、建议的非 gt 施工边界

本设计对应的模块职责建议如下，便于派工时不再现场发明：

- 模块 1 · `reading/as_drawn/schema.py`：as-drawn v2 生产者类型；
- 模块 2 · `correction/evidence_contract.py`：source refs、四种 wall claim、三种 disposition、bundle；
- 模块 3 · `correction/evidence_adapters.py`：legacy/as-drawn 双 adapter；
- 模块 4 · `correction/wall_compiler.py`：ref resolve、切段、中线/候选/厚度 IR；
- 模块 5 · `correction/decision_schema.py`：packet 与 response；
- 模块 6 · `correction/decision_executor.py`：执行符号决定、复算坐标与 hash；
- 模块 7 · `reading/vector_contract.py`：本批只做 as-drawn 指向新 adapter 的一行注册；`CONSUME→ADAPT` 重命名与 ledger 重排登记 plan、暂不施工；
- pipeline 只编排上述阶段，不再内嵌第二套“看到某几个键就当某契约”的判断。

⛔ 本单不要求改 gt schema、AnswerCompiler、promote 路径或重签答案；验收只消费既有 correction judge 结果，不向 judge 侧新增事实。

## 十一、返工处置与新增量化来源对账

### 11.1 NF-1～NF-9 逐条处置

| finding | 处置 | 落点与理由 |
|---|---|---|
| NF-1 | **已改** | §9.4 删除今天取空的“显式 centerline fixture 保持兼容”承诺，写明 strict/exploratory 两档终点，并点名 sm21 零 as-drawn 的代价；degraded 不再冒充“不比现在差” |
| NF-2 | **已改** | §7.3 加墙级带锚点定向再感知，成本为 `O(unknown 墙数)`；同时把 note 的“代码禁解析”与“模型可见但不受信”边界拆开 |
| NF-3 | **已改** | §4.1 表新增“几何角色已知？”列，明确 `legacy_wall_trace` 是角色未知的降级声明，不能与其余类型做同层几何完备性证明 |
| NF-4 | **已改** | §4.1 将 `single_face.counterface_state` 扩为 `not_in_observations \| observed_unclaimed`，后者强制带原节点与 disposition 引用 |
| NF-5 | **已改** | §5.4 新增 `CorrectedGeometryProjectionEnvelopeV1`，attempt/report 消费 completion 与 debt ids；strict 前置阻断，exploratory judge 不缩分母且报告 degraded |
| NF-6 | **已改** | §6.2 把 `requested_effect.kind` 收成封闭枚举，并规定 entity/ref 必须来自 packet、坐标只由下一轮 compiler 候选产生 |
| NF-7 | **已改** | §9.1 与 §十固定最小集为模块 1–6 加模块 7 的 adapter 注册；模块 7 的重命名/ledger 收窄登记 plan、本批不做 |
| NF-8 | **已改** | §5.4 的 `output_basis` 直接采用判分侧既有 `wall_axis \| outer_skin`，并写机械映射；只引用、不改 gt 侧 |
| NF-9 | **已改** | §二把 `Stroke.geometry` 锚点修到 `schema.py:49`，点明 `RoomRoleObservation.basis:113` 的同名不同义；§8.3 要求源模型注释隔离语义，并把签名 sidecar 绑定 §3.2 sha256 身份与验证门 |

### 11.2 本轮新增数值/数量的 provenance

- f9 自检的墙笔画、null 厚度与 S1–S4“外皮线”/S5–S10“中线”均直接来自
  [`tests/fixtures/f9_window_host_crash/0_reading/1f_view.json`](../../../../tests/fixtures/f9_window_host_crash/0_reading/1f_view.json)；
  本稿不从 note 推导 basis，只用它复核混合历史事实。
- “存量 `pen==wall` 为 1240、geometry basis 键为 0、有厚度墙为 132、sm21 零 as-drawn”均沿用
  [`GLM 裁决:122-151`](2026-08-30_o22_design_crossreview_glm.md#L122) 的仓库递归复核及其可复现脚本；本稿没有外推新计数。
- §5.2.1 的 `0.239` 直接取自
  [`sm25-L_anchor W01 geometry`](../../../../case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H1/0_reading/1f_view.json#L19)，
  同一节点没有 basis 键；`ReadingView` 接收门见
  [`schema.py:49`](../../../../src/agent/reading/schema.py#L49) 与
  [`vector_contract.py:153-178`](../../../../src/agent/reading/vector_contract.py#L153)。
- 模块 1–6 加模块 7 一行注册的切片来自
  [`GLM 裁决 §五`](2026-08-30_o22_design_crossreview_glm.md#L219)；`output_basis` 的两个既有词值来自
  [`answer_compiler.py:110`](../../../../src/agent/judge/answer_compiler.py#L110)。

## 十二、我认为这次返工后最薄弱的一处

最薄弱的是 **residual debt 从 `CorrectionResolvedV1` 经 projection envelope 落到 attempt/report 的真实消费者**。
本稿已经定义了唯一落点和 strict/exploratory 行为，但当前 `correction_score.py` 不读 degraded/conflicts，尚无代码实证证明
runner 不会只拿出 envelope 内的裸 geometry、把状态留在旁边。这个缝若施工漏接，unknown 虽未变成 identity，degraded 仍可能在报告面伪装成完整成功。

## 十三、希望复核方重点打哪里

请优先打两处相连的门：其一，用 §5.2.1 那种 `basis=unknown + thickness_m 非空` 输入，故意让硬约束只剩一个偏移候选，
看 executor 能否绕过“已开项不自动”而记成 `auto_actions`；其二，从同一 degraded resolved artifact 只抽裸
`CorrectedGeometry` 去跑 judge，看 attempt/report 是否会因 envelope 缺失或 hash/debt 不闭合而响亮失败。前者若穿透，静默中线腿仍在；
后者若穿透，degraded 会在投影面伪装成 complete。两处都是本次返工最值得用反证测试而不是文字复核去打的地方。
