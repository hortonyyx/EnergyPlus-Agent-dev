# ②-2 前置设计 · correction 消费多形态墙证据的契约

- **日期**：2026-08-30
- **席位**：GPT 家族设计出稿
- **性质**：可施工设计稿，**不是代码、不是裁决**
- **复核工作点**：当前主树 `08.23_AsDrawnReading`，复核时 HEAD = `c7c17b4`；请求书所列基线虽为 `bc8e354`，下述四条承重事实在当前主树仍逐条成立
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

另有一个对本设计承重的反例：[`ReadingView`](../../../../src/agent/reading/schema.py#L117) 的 `Stroke.geometry` 是自由 dict，类型上没有 `basis`。现有真实夹具又同时存在“外皮线”墙笔画（[`f9 ... 1f_view.json:35`](../../../../tests/fixtures/f9_window_host_crash/0_reading/1f_view.json#L35)）和明确写 `centerline` 的墙笔画（[`smalloffice_22/1f_view.json:27`](../../../../case_tests/e2e_tests/smalloffice_22/0_reading/1f_view.json#L27)）。所以“旧 reading 给的是中线 ⇒ 适配成 `axis_trace`”不成立；prompt 要中线不能倒推输入已经是中线。

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

| `kind` | 它断言什么 | 它明确没有断言什么 | 必带原始引用 |
|---|---|---|---|
| `paired_faces` | 两条被观测面线在二者共同覆盖的沿墙区间内，是同一堵墙的两侧面 | 不断言中线、名义厚度、内外墙、输出基准；也不断言两条面的所有 runs 等长 | 两个 `ObservationRefV1`，各自回指 `observations.face_lines[i]` 及 `support_cols_px/runs_px/gaps`；选中 `pairs[j]` 的 `hypothesis_ref`；对应 `pair_candidates[k]` 的 pointer。`spacing_m` 只作缓存审计，代码必须从两面重算 |
| `solid_band` | 一条被观测墨带本身表达一堵墙；该观测自己的两条 `edges_m` 是墨带边界 | 不断言这两边已经是规范墙面、不把 `support_width_m` 命名为事实厚度、不判内外 | 一个 face-line ref；指到 `solid_band_walls.<id>` 的 hypothesis ref；必须指到 `support_cols_px`、`edges_m`、`runs_px` 的像素 witness |
| `single_face` | 该观测是墙的一张面；另一面**没有进入当前 observations** | 不断言另一面在哪一侧、离多远、为何缺失，也不断言可直接产出中线 | 一个 face-line ref；指到 `unpaired_wall_faces.<id>`；保留原 reason。canonical 字段只写 `counterface_state=not_in_observations`，不能从 prose 猜 side 或 thickness |
| `legacy_wall_trace` | 旧 `ReadingView` 的某条 `pen=="wall"` stroke 是墙相关线迹 | 除非有类型化字段证明，否则不保证它是中线、外皮或墙面；`geometry.thickness_m` 也不能无条件晋升为实测厚度 | 回指原 `strokes[i]`、stroke id 与 geometry pointer；`source_basis = centerline | wall_face | outer_skin | unknown`。非 `unknown` 必须有**结构化** basis evidence ref；禁止解析自由 `note` 猜基准 |

请求书中的 `axis_trace` 由此降为 `legacy_wall_trace(source_basis="centerline")` 的特例，而不是独立、无条件成立的来源形态。

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
| `legacy_wall_trace` | `basis=centerline` 时原线可作 provisional axis；显式 `wall_face/outer_skin` 且有唯一厚度/方向规则时由代码偏移 | `basis=unknown` 必须开项；不能因 correction prompt 曾要求中线就自动 identity |

墙角不传播原观测端点。遵守指南 §十#6c：传播的是 resolved support-line，最终多边形角点由相邻 support-lines 求交；原 `runs/along intervals` 只控制证据覆盖、洞口落位和墙段有效区间。

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
  output_basis
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
| 硬约束筛后只剩一个候选，或一候选在全部 cost 维度 Pareto 支配其余候选 | 自动执行并记账 |
| 已签规则唯一决定的数值闭合、同墙连续段接缝 | 自动；规则 id 必须入账 |
| `single_face` 的 side/thickness 多解、legacy basis unknown、互不支配的设计轴/拓扑候选 | 进入 `open_items` |
| reading `pairs` 缺失、`ambiguous` 可能影响墙拓扑 | `reperception_required`；不让 correction 代做读图 |
| 没有任何合法候选 | `unsupported_or_reperceive`，⛔ 不选最近值 |

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
      requested_effect       # 结构化意图，不含坐标
      rationale
```

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

- 新增的类型化 `geometry.basis` 或签名 sidecar 明确写 `centerline/wall_face/outer_skin` 时，才填对应 basis；
- 当前历史产物没有类型化声明时填 `unknown`；
- 禁止正则解析 `note` 里的 “centerline / 外皮线”；自由文本只能做审计展示，不能承重；
- `unknown` 进入待裁决或重新感知。为追平历史基线而暗设 `unknown→centerline` 会原样复活本单要消掉的基准错误。

## 九、迁移次序与验收

### 9.1 施工顺序

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
| 旧 ReadingView 历史 case | 显式 centerline 的 fixture 保持兼容；basis 不明者必须显示 open item/degraded，不能以静默 centerline 换表面分数 |
| `ambiguous` 反事实 | 删除 debt 或改写为 `non_wall` 不得无记录通过；strict profile 必须阻止完整成功 |
| 厚度反事实 | 只保留中线、丢 observed/resolved thickness 的变异必须被 gate 抓住；只改厚度不改轴、只改轴且破坏双面间距，分别失败 |
| 未知/混装契约 | 未注册 schema、已声明但缺字段、同槽双源、单文件双匹配全部在调用模型前失败且 ledger 点名 offender |

真实模型端到端只能放在上述确定性测试之后。sm25 先跑，sm24 与历史 case 后跑；模型波动不能拿来解释代码验收失败。

## 十、建议的非 gt 施工边界

本设计对应的模块职责建议如下，便于派工时不再现场发明：

- `reading/as_drawn/schema.py`：as-drawn v2 生产者类型；
- `reading/vector_contract.py`：只做源识别/目录 ledger，不做几何、不直接决定 prompt paste；
- `correction/evidence_contract.py`：source refs、四种 wall claim、三种 disposition、bundle；
- `correction/evidence_adapters.py`：legacy/as-drawn 双 adapter；
- `correction/wall_compiler.py`：ref resolve、切段、中线/候选/厚度 IR；
- `correction/decision_schema.py`：packet 与 response；
- `correction/decision_executor.py`：执行符号决定、复算坐标与 hash；
- pipeline 只编排上述阶段，不再内嵌第二套“看到某几个键就当某契约”的判断。

⛔ 本单不要求改 gt schema、AnswerCompiler、promote 路径或重签答案；验收只消费既有 correction judge 结果，不向 judge 侧新增事实。

## 十一、我认为最薄弱的一处

最薄弱的是 **`single_face` 与 `legacy_wall_trace(basis=unknown)` 如何在不重做 reading 感知的前提下收束**。本稿给出了安全边界——无唯一 side/thickness/basis 就开项或重新感知——但当前实物还不足以证明这条路不会让大量历史输入都退化为 unresolved。这个风险不能用 `unknown→centerline` 默认值掩盖；施工前需要拿 f9 的“外皮线”与明确 centerline 的历史产物做成对夹具，实测候选生成和总体判断的可用性。

## 十二、希望 GLM 复核时重点打哪里

请重点攻击**旧输入并存是否仍藏着一条静默中线腿**：从 detector、legacy adapter、packet、兼容 `CorrectedGeometry` 投影一直追到 kernel，尝试构造一份 `ReadingView`，其中外墙是 outer-skin、内墙是 centerline、自由 note 又互相矛盾；看它能否在没有类型化 basis 证据、没有 open item、没有 degraded ledger 的情况下被当成全中线成功消费。若能，本设计最核心的基准隔离仍未成立。
