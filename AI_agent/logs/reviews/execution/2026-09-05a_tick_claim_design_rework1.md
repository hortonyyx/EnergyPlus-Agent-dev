# 执行档 · 刻度认领 · 设计稿 **返工 1**（T0 只读勘察 + 契约形态方案）

- **日期**：2026-09-05 · **施工方**：Claude 家族席位 · **审**：GPT 或 GLM 家族（⛔ 不得 Claude）
- **任务书**：[`2026-09-04u_tick_claim_design`](../request/2026-09-04u_tick_claim_design.md)
- **上一稿**：[`2026-09-04u_tick_claim_design.md`](2026-09-04u_tick_claim_design.md)（373 行，D1–D7）
- **裁决书**：[`2026-09-04y_tick_claim_design_crossreview_gpt.md`](../verdict/2026-09-04y_tick_claim_design_crossreview_gpt.md)
  （**REWORK · 阻断 6 · 不阻断 2**）
- **工作目录**：`/tmp/tick_design_rw_claude` · **分支**：`wt/09.05a_tick_design_rw`
- **累计式自包含**：本稿**不引用**上一稿正文（⛔ 无「D2 见上一稿」），逐条闭合 6 阻断 + 2 不阻断，
  末尾附**逐条对账表**与**最薄弱一处**。⛔ 全程零 `src/`、零 `tests/` 改动，`git status` 自证（末节）。

**结论先行**（本稿的承重形状，六条阻断都收在这里）：
1. **x 应当进证据契约层**（§二问题不停报，正面论证见 D2-d），落点 = `ElevationOpeningClaimV1` 镜像加 x 证据档。
2. **裁定结果**另立一层 `OpeningEdgeTickClaimV1`；**一档是判别联合** `chain_node | chain_derived`
   —— 兑现权威口径「节点，**或由链算出来的值**」（累加 / 分段相减 / 轴线 ± 半墙厚），⛔ 不再收窄成「必是 cum 节点」（闭合 **B-1/B-2**）。
3. **自动分流用【结构谓词】** —— reading 产物**每条边已自带** `edge_witnesses[edge].dimension_refs` 与
   `nearest_tick_px`；分流靠「witness 是否角色闭合到唯一链节点」这个符号判断，⛔ **不用相邻刻度中点、不用任何毫米/像素阈值**（闭合 **B-3**）。
4. **第一步有独立响应类型**（结构上不携带第二步的 `whole_building_review`）+ **每条 claim 结构性绑定裁决账**（闭合 **B-5** 阶段隔离与裁决账）。
5. **冻结靠真封印类型**（模块私有令牌 + 逐元素受封 + 第二步从冻结字节重建），复用 B2 返工 3 的最终范式（闭合 **B-4**）。
6. **一档链真值 vs pipeline 10 mm 出口**：在设计层显式收口 —— **一档坐标免疫 10 mm 出口格点**，此结论**由已定死的 §14.2 推出**（坐标只能取自尺寸链），非新决策（闭合 **B-5** 颗粒度冲突，详见 §颗粒度收口）。
7. **D7 更新到当前在飞形态**：B2 返工 3（改 `multifloor.py`）、T4-a 返工 2（改 `opening_synthesis.py`），二者均已交件待审（闭合 **B-6**）。

---

## 〇、开工自证 + 权威口径已读 + 一条 B 层

**开工自证输出原文**：

```text
/tmp/tick_design_rw_claude
ac9a0669 09.04x_dispatch_T4a_rework2 (lock the preimage set, not the lexical near-miss family)
A  AI_agent/logs/reviews/execution/2026-09-04u_tick_claim_design.md
A  AI_agent/logs/reviews/verdict/2026-09-04y_tick_claim_design_crossreview_gpt.md
```

**⭐ 权威口径 §十四 / §十五 已从头读完**（本树有；上一稿作者的树因派工方建树基点错而**没有**这两节，
作者按 B 层如实上报，做得对 —— 那是派工方失误，⛔ 不追溯）。核过存在性：

```text
$ grep -n "^## 十四\|^## 十五" AI_agent/guides/reading_correction_split_guide.md
970:## 十四、⭐⭐⭐ 2026-09-04 用户拍板：尺寸证据裁定 → 空间推理（洞口对齐由此定位）
1117:## 十五、⭐⭐⭐ correction 目标态 · 完整表述（2026-09-04 用户点名要的那一份）
```

承重两句我逐字核过：
- **§14.2b（行 1038）/ §15.4（行 1166）**：一档 = 尺寸链的**节点，或由链【算出来】的值**（用户补：「不一定能直接对上」，例：**累加 · 分段相减 · 轴线 ± 半墙厚**）。⇒ 这是 **B-1** 的权威依据。
- **§14.2（行 1015-1016）**：洞口边坐标**只能取自尺寸链节点**（或链算出的值）；**像素测量的唯一用途 = 指认，⛔ 永远不作坐标值落地**。⇒ 这是**颗粒度收口**（B-5）的权威依据。

**B 层记一条**：派工单 §一表「立面洞口竖边 68 条…认领后宽度全变图纸整数」我全量重量了一遍（68 条 x 边，见 D5-实测），
派工方事实成立；且我**发现了一件上一稿没利用的事实**：reading 产物**每条边已自带 `edge_witnesses`**
（含 `dimension_refs` / `nearest_tick_px` / `measured_px` / `distance_mm`），它把 B-3 从「发明一个阈值」变成「消费一个已有的结构证据」。**不停报，继续。**

---

## D1 · 勘察落点：x 从 reading 产物到配对的完整路径（逐跳 file:line + 溯源/档位）

⭐ 每一跳行号我自己 `grep -n` 过（命令见跳表末），⛔ 未引派工单/裁决书里的行号。裁决书 §5.4 已独立核过本表并判 **PASS**，本稿保留并复核。

| 跳 | 位置（file:line） | x 在这里是什么 | 冻结字节溯源 | 证据档位 |
|---|---|---|---|---|
| **0 · 产物** | reading 立面 JSON `openings[i].x_range_m`（schema `as_drawn_elevation_v0`）| 一对 `[x_lo_m, x_hi_m]` 浮点，像素换算（`mm_per_px≈13.6`）| ❌ 磁盘裸 JSON，无 `ArtifactPointerV1` | ❌ 无（既非一档也非二档，只是像素读数）|
| **0b · 产物（新发现）** | 同 JSON `openings[i].edge_witnesses.{x0,x1}`：`dimension_refs`（链段名列表）· `nearest_tick_px` · `measured_px` · `distance_mm/px` | reading 已对每条边做了**刻度指认**的多通道证据 | ❌ 裸 JSON | ❌ 未成档位（是**待裁定**的原始证据）|
| **1 · 适配器** | `adapt_as_drawn_elevation`（`evidence_adapters.py:609`）建 `ElevationOpeningClaimV1`，**只搬 z**：`z_low_ref=_pointer(...,"/z_range_m/0")`（`:704`）、`elevation_opening_claims=elev_openings`（`:821`）| **x 根本没被搬进 bundle** | ❌ x 不在场 | ❌ x 不在场 |
| **2 · 契约类型** | `ElevationOpeningClaimV1`（`evidence_contract.py:531`），docstring `:544`「`x_range_m` deliberately NOT here」| 类型上**只有** `z_low_m/z_low_ref/z_high_m/z_high_ref`（`:553-556`）| ❌ x 无字段 | ❌ x 无字段 |
| **3 · 校验器** | `validate_evidence_bundle`（`:1215`）逐条重算 z 相等（`ELEVATION_Z_VALUE_DRIFTED_FROM_SOURCE`，`:1650`）| **只校 z**，无 x 分支 | z 有（对冻结字节 `==`）；**x 无** | x 无 |
| **4 · 配对消费者 B4** | `synthesize_openings(elevation_doc: dict, ...)`（`opening_synthesis.py:746`）| **直接从裸 dict 读**：`_elevation_openings(doc)`（`:693`）在 `:713` 取 `("x_range_m","z_range_m")`；`:887` `for oid, x_lo, x_hi, z_lo, z_hi in ...` | ❌ **绕过整个 bundle** | ❌ 无 |
| **5 · 用作坐标** | `opening_synthesis.py:887-899`：`grid_units(x_lo)` → `world_lo = along_origin_u + sign * lo_u` → 世界区间做**零容差**等值配对 | 像素外推 x 被当**权威坐标**参与等值 | ❌ | ❌ |

### D1 的三条硬结论

1. **派工方核到的落点属实**：x 从产物到 B4 配对，**全程没有一跳有冻结字节溯源、没有一跳有证据档位**。z 有契约（跳 2/3），x 完全裸奔。
2. ⭐ **比派工单更进一步**：即便**有契约的 z**，B4 也**没消费契约** —— `synthesize_openings` 收 `elevation_doc: dict`，z 也从裸 dict 读。全仓对 `elevation_opening_claims` 的**唯一消费者是校验器**（`grep -rn "elevation_opening_claims" src` ⇒ 只有 `evidence_adapters`〔产〕、`evidence_contract`〔校/排序/哈希〕，**无任何配对/装配消费**）。⇒ **本单不仅要给 x 建契约，还要把 B4 从「读 dict」改成「读认领结果」**（否则建了契约没人读）。
3. **B4 未接线**：`synthesize_openings` 在 `src/`、`scripts/` 里**零调用**。⇒ 改造 x 路**不动任何在跑的生产消费者**（与 CLAUDE.md §2 banner ⑥b 一致）。

```text
# D1 行号复核命令（我自己跑过）
grep -n "def adapt_as_drawn_elevation\|z_low_ref=_pointer\|elevation_opening_claims=" src/agent/correction/evidence_adapters.py
grep -n "class ElevationOpeningClaimV1\|deliberately NOT\|z_low_m:\|_z_direction_agrees\|def validate_evidence_bundle\|ELEVATION_Z_VALUE_DRIFTED" src/agent/correction/evidence_contract.py
grep -n "def _elevation_openings\|def synthesize_openings\|for oid, x_lo\|world_lo = along_origin\|def grid_units" src/agent/correction/opening_synthesis.py
```

---

## D2 · 契约形态方案：一条洞口边的裁定结果长什么样

先分清**两层不同的东西**（今天全项目把它们混成「`x_range_m` 一个裸值」，这就是病）：

- **证据档（输入侧，纯搬运）**：洞口边的**像素读数 + reading 的指认证据**，带冻结字节溯源。它是「指认」证据，权威天然二档，⛔ 认领前不作坐标。落点 = `ElevationOpeningClaimV1` 与 z 对称地补 x。
- **裁定结果（输出侧，D2 主体）**：第一步「尺寸证据裁定」对**这一条边**下的结论 —— 几档、值从哪来、依据哪几条链、由谁裁的。落点 = 新产物 `OpeningEdgeTickClaimV1`。

### D2-a 证据档：`ElevationOpeningClaimV1` 补 x（只写形状与不变量）

```
ElevationOpeningClaimV1（在既有 z 四字段旁，镜像加）:
    x_lo_m:   float             # 像素读数，逐字来自 /openings/<i>/x_range_m/0
    x_lo_ref: ArtifactPointerV1 # json_pointer = "/openings/<i>/x_range_m/0"
    x_hi_m:   float             # 逐字来自 /openings/<i>/x_range_m/1
    x_hi_ref: ArtifactPointerV1 # json_pointer = "/openings/<i>/x_range_m/1"
    # —— reading 的指认证据（搬运，⛔ 不裁定）——
    x_lo_witness_ref: ArtifactPointerV1  # -> /openings/<i>/edge_witnesses/x0
    x_hi_witness_ref: ArtifactPointerV1  # -> /openings/<i>/edge_witnesses/x1
```

**不变量**（全部与 z 现有校验同构，`evidence_contract.py:1632-1650` 是模板）：
- `x_lo_m == 冻结字节(/openings/<i>/x_range_m/0)`、`x_hi_m == 冻结字节(...1)`，**精确 `==`，⛔ 无容差**。
- `x_lo_m < x_hi_m`（同 `_z_direction_agrees`，`:559`）。
- F-2 单源：`{source_ref, x_lo_ref, x_hi_ref, x_lo_witness_ref, x_hi_witness_ref}.input_id` 必须同一（同 z 的单源不变量）；`_payload_row_source_ids`（`:1103`）的 `elevation_opening_claims` 分支**加上这些 ref 的 input_id**（否则 F-2 源闭合会漏 x）。
- `ArtifactPointerV1`（`:190`）四字段 `input_id / source_contract_id / source_output_sha256 / json_pointer` 与 z ref 逐字对称。

⭐ **为什么把 witness 也搬进证据档**：D5 的自动分流要读 `dimension_refs`/`nearest_tick_px`，这些是**裁定的输入证据**，必须挂在带冻结字节溯源的载体上（否则分流又在读裸 dict，重蹈 D1 的病）。⛔ witness 只搬运、不裁定 —— 裁定结论只在 D2-b。

### D2-b 裁定结果：`OpeningEdgeTickClaimV1`（每条竖边一行 —— D2 三问的正式答案）

⭐ 相比上一稿，**一档拆成判别联合**（`chain_node | chain_derived`），并**加裁决账绑定**。

```
# 一档的值来源 —— 判别联合（闭合 B-1：一档 = 节点 或 由链算出的值）
OneTierValueV1 = ChainNodeValueV1 | ChainDerivedValueV1     # discriminated on `value_source`

ChainNodeValueV1:
    value_source: Literal["chain_node"]
    node_ref:     ArtifactPointerV1        # -> /calibration/x/cum_mm/<k>（指认到的节点字节）
    # 代码落坐标：直接取 node_ref 指的 cum_mm 字节值（精确）

ChainDerivedValueV1:                        # ⭐ 由链【算出来】的值（累加 / 分段相减 / 轴线±半墙厚）
    value_source: Literal["axis_plus_half_wall", "segment_span_diff", "segment_span_sum"]
    operands:     tuple[DerivedOperandV1, ...]   # 每个操作数一个角色 + 一个冻结字节 ref
    recompute_cert_units: int               # 代码在 0.1 mm 整数域重算的结果（grid units），供校验器复算比对
    # 代码落坐标：按 value_source 指定的【封闭运算】对 operands 精确重算，结果必 == recompute_cert_units

DerivedOperandV1:
    role: Literal["axis", "half_wall_thickness", "cum_lo", "cum_hi", "segment_len"]
    ref:  ArtifactPointerV1                  # 指向链节点 / 声明墙厚 / 段长 的冻结字节

# 裁定结果本体
OpeningEdgeTickClaimV1:
    edge_id:       str                       # <opening_id>:<lo|hi>，来自证据档，⛔ 非数组下标
    evidence_ref:  ObservationRefV1          # 指回 D2-a 那条边的证据档（指认，⛔ 不作坐标）
    # —— ① 它是几档 ——
    tier:          Literal["chain_backed", "pixel_only"]
    # —— ② 值从哪来 ——
    tier_one_value: OneTierValueV1 | None    # 一档：判别联合；二档：None
    pixel_out_ref:  PixelOutV1     | None    # 二档：像素→出口颗粒度的可复算派生记录；一档：None
    # —— ③ 依据哪几条 dimension_refs ——
    dimension_refs: tuple[ArtifactPointerV1, ...]   # 指向 calibration.x.cum_mm 的具体节点/段
    # —— ④ 谁在第一步把它裁成这样（裁决账，闭合 B-5）——
    provenance:    ClaimProvenanceV1         # 自动 or 模型，见 D2-e

PixelOutV1:                                  # 二档的颗粒度消费证书（闭合 B-5 颗粒度）
    raw_pixel_ref:        ArtifactPointerV1  # 指回证据档的像素读数字节
    output_precision_ref: ArtifactPointerV1  # 指向 pipeline 出口颗粒度【声明点】（10 mm，见颗粒度收口）
    rounded_result_units: int                # 代码按声明颗粒度规整后的结果（0.1 mm 整数单位）
```

**硬不变量**（承重处，⛔ 不写实现）：
- `tier=="chain_backed"` ⟺ `tier_one_value is not None` 且 `pixel_out_ref is None` 且 `dimension_refs` **非空**；
  `tier=="pixel_only"` ⟺ `tier_one_value is None` 且 `pixel_out_ref is not None` 且 `dimension_refs` **恰好为空**。
  （枚举与字段互锁，同 `FaceDispositionV1._status_fields_agree` 的写法。）
- **⛔ 本类型不带任何裸坐标浮点字段**：一档只说「哪个节点 / 哪个封闭运算 + 哪些操作数 ref」，二档只说「哪个像素 ref + 哪个颗粒度声明 ref + 规整结果整数」。**坐标全由代码从 ref 现算** —— 与铁律「模型/裁定层出决定、代码出坐标」一致。
- **二档不是缺陷**（§14.2b）：`pixel_only` 是干净出口，`dimension_refs=()` 是「没有可指认刻度」的**显式**记录。
- **区间级不变量**（闭合 B-2，见 D4-c）：一条洞口的 `lo`/`hi` 两条边 claim 必须**同源、角色互异、严格有序、非零宽**；这条**跨两条边**，不能只逐边查。

### D2-c 三问的具体例子（验收 #2：一档 + 二档各一）

**一档 —— South `O01`**（`x_range_m=[6.9219, 8.7512]`；witness：x0 refs=`[C_top_fine_s2, C_top_fine_s3]` d=6.8mm、x1 refs=`[C_top_fine_s3, C_top_fine_s4]` d=20.3mm；`nearest_tick_px` 经 `dimension_witnesses.x` 表分别映到 `6930 / 8730`）：

| 边 | ① tier | ② value_source | 值从哪来 | ③ dimension_refs |
|---|---|---|---|---|
| `O01:lo` | `chain_backed` | `chain_node` | 节点 `6930 mm`（像素 6921.9 指认到它，d=6.8）| `/calibration/x/cum_mm/2` |
| `O01:hi` | `chain_backed` | `chain_node` | 节点 `8730 mm`（d=20.3）| `/calibration/x/cum_mm/3` |

⇒ 宽度 = `8730-6930 = 1800`（= South `values_mm[2]`，一段画出的尺寸）。**零容差成立**（两端都是精确 tick，像素距离 6.8/20.3 mm **不进任何判据、不进坐标**）。

**`chain_derived` 一档示例（B-1 的核心 —— 权威口径明写的合法一档，⛔ 上一稿判不了）**：设某洞口边落在**轴线 3000 mm 处减半墙厚 120 mm** = `2880 mm`（`2880` **不是** cum 节点）：

| 边 | ① tier | ② value_source | operands（角色 + ref）| recompute_cert |
|---|---|---|---|---|
| `Oxx:lo` | `chain_backed` | `axis_plus_half_wall` | `{axis: cum_mm 节点 3000}` + `{half_wall_thickness: 声明墙厚 240 的一半}` | 代码在 0.1 mm 整数域算 `30000 − 1200 = 28800` units（= 2880 mm）|

⇒ 值是**链派生事实**（轴线是链节点、半墙厚是声明值），**外部可证伪、零建筑先验**，但**结果不在 cum 集合**。D4 的判据必须放行它（见 D4-a），⛔ 不能要求「结果 ∈ cum」。

**二档 —— East `O01`**（`x_range_m=[0.5367, 2.1646]`，落在东立面第一段 6000 mm **正中**；witness：x0/x1 的 `dimension_refs` **全是 `_s1`**（`C_top_overall_s1, C_top_mid_s1, C_bot_fine_s1, C_bot_mid_s1, C_bot_overall_s1`）、`nearest_tick_px` 都映到 `0.0`、d=535.8/2163.7mm）：

| 边 | ① tier | ② value_source | 值从哪来 | ③ dimension_refs |
|---|---|---|---|---|
| `O01:lo` | `pixel_only` | （PixelOut）| 像素 `536.7 mm` → 按 10 mm 出口规整 → `540 mm` | `()` |
| `O01:hi` | `pixel_only` | （PixelOut）| 像素 `2164.6 mm` → 规整 → `2160 mm` | `()` |

⇒ **不强行认领**：witness 的 refs 全是开口段（`_s1`）、无任何相邻段边界被引用 ⇒ **结构上就没有可认的内部刻度** ⇒ 二档，权威低，⛔ 非失败。

### D2-d ⭐ §二的正面论证：x 该进这层，且不破坏 docstring 原意（⛔ 不停报）

docstring（`evidence_contract.py:544`）原意两句：**(a)**「x 故意不在，B4 拥有需要它的跨视图配对」·**(b)**「这层只带**被具名消费者要过**的东西」。逐句核：

1. **(b) 是这层的真原则，本方案恰好履行它。** B3 加 z 时走的就是同一逻辑：有了具名消费者（`WindowV3.z`）才带进来、且必带冻结字节溯源。x 现在**同样有了具名消费者**：第一步的刻度认领要对 x 裁定，裁定证据必须挂在带溯源的载体上（D1 证明今天它挂在裸 dict 上 = 病）。⇒ 按 (b) 自己的判据，x **现在有资格进**，进法与 z 逐字对称。
2. **(a) 的事实前提变了，不是原则变了。** 「B4 拥有需要 x 的配对」当时等价于「x 还没有证据层消费者」。但 D1 跳 4/5 证明：B4 靠**读裸 dict** 拿 x、零容差配对**永远对不上**（banner ⑥b：真实四立面配 0 对）—— 这正是「x 没有证据档位」的直接恶果。让 x 带溯源进层、B4 改读认领结果，**恰恰是在兑现 (a)**（B4 仍拥有配对，只是喂的是认领后的一档值而非像素外推值）。
3. **反面验证**（认真想过「x 不该进这层」）：若把 x 认领结果放进**平行新层**、`ElevationOpeningClaimV1` 只留 z，会造出「一个洞口的 x 与 z 分属两个溯源载体」—— 正是 §〇之二警告的 **F-130「两条并列生产线各自漂移」**形状。x 与 z 读自**同一个** `/openings/<i>` 节点、共享 `source_ref`，拆开无收益、有漂移风险。⇒ **证据档 x 与 z 同类**（D2-a）；**裁定结果**才另立一层（D2-b，它是第一步的**产出**，不是 reading 的搬运）。

⇒ **结论：x 应当进证据契约层，落点如 D2-a/D2-b。不触发 §六 A 层①。**

### D2-e 裁决账绑定 `ClaimProvenanceV1`（闭合 B-5 之「裁决账」）

§15.2 要求输出带**裁决账**（谁在哪一步被判成什么、依据哪档证据），§15.3 要求**自动动作也记账**。⇒ 每条 `OpeningEdgeTickClaimV1` **结构性绑定**它的来源，二选一（判别联合）：

```
ClaimProvenanceV1 = AutoProvenanceV1 | ModelProvenanceV1     # discriminated on `decided_by`

AutoProvenanceV1:          # 拍①代码自动认（D5-a）
    decided_by: Literal["auto"]
    auto_rule_id: str      # 指向那次 AutoActionV1 的 rule_id / action_id（wall_compiler.py:333）

ModelProvenanceV1:         # 拍②模型裁（D5-b / D3）
    decided_by: Literal["model"]
    packet_hash:   Hex64   # 哪个 CorrectionDecisionPacketV1（decision_schema.py:182）
    item_id:       str     # 包里哪条 open item
    decision_hash: Hex64   # 模型那次响应的 canonical hash
```

⇒ 从任一条 claim 结论**都能闭合复算**到「哪个自动规则 / 哪个 packet+item+decision 把它裁成这样」。bundle 输出**完整裁决账**（所有 claim 的 provenance 汇总）。⛔ 无 provenance 的 claim = 非法（互锁不变量）。

---

## D3 · 模型那一拍怎么接（第一步**独立响应类型**，闭合 B-5 阶段隔离）

### D3-a 包（code→model）：`OpenItemV1` 扩一个 kind

`CorrectionDecisionPacketV1`（`decision_schema.py:174`）带 `open_items`（`:192`）、`auto_actions`（`:190`）。刻度认领的**歧义边**进 `open_items`：
- `OpenItemV1.kind`（`wall_compiler.py:304-309` 的 Literal）**加一项** `"opening_edge_tick_claim"`（**可见 diff**，非自由文本）。
- `scope_entity_ids` = 那条边的 `edge_id`；`source_refs` = 证据档 x ref + witness ref + 候选链节点 refs。
- **候选 = 代码枚举的链节点/派生运算**。两路，**推荐乙**：
  - (甲) 复用 `SymbolicCandidateV1`（`wall_compiler.py:217`，`symbolic_operation: SymbolicOperation` `:225`、`preview_constant_pos_m` `:227`）：`SymbolicOperation` Literal（`:119`）加 `"CLAIM_CHAIN_TICK"`；每候选一个 cum 节点，preview 由代码算。**缺点**：`SymbolicOperation` 现全是墙厚语义，混入刻度会污染它。
  - (乙) **新增平行候选类型** `TickCandidateV1 {candidate_id: str, value: OneTierValueV1, preview_local_x_units: int}`，`OpenItemV1` 用**判别联合**承载候选。每候选可以是 `chain_node` 或 `chain_derived`（**含派生运算候选**，天然容纳 B-1 的 `axis_plus_half_wall`）。preview 由代码算。
  两路共同点：**候选 id 由代码 mint、preview 由代码算、模型只在 id 之间选**。

### D3-b 响应（model→code）：⛔ **不能复用 `CorrectionDecisionResponseV1`**（闭合 B-5#3 / B-4 阶段隔离）

**病根（我核过）**：`CorrectionDecisionResponseV1`（`decision_schema.py:356`）**强制携带** `whole_building_review: WholeBuildingReviewV1`（`:366`，**必填、无默认**）。而 `WholeBuildingReviewV1`（`:335`）是**第二步（跨图空间推理）**的「整栋楼讲不讲得通」语义。第一步**逐图独立**（§15.3），结构上**不该能**产出第二步语义。上一稿说「响应侧一字不改、第一步让它填 accept」—— 那是**纪律不是阶段隔离**（GPT B-5#3 点名）。

⇒ **第一步用独立响应类型**（结构上装不下 `whole_building_review`）：

```
TickClaimResponseV1:                         # 第一步 · 逐图独立 · 只回刻度裁定
    model_config = _CFG                      # extra="forbid", strict（decision_schema.py:170）
    packet_hash:     Hex64
    item_decisions:  tuple[TickItemDecisionV1, ...]
    # ⛔ 结构上【没有】whole_building_review 字段 —— 第一步永远产不出第二步语义

TickItemDecisionV1:                          # 与既有 ItemDecisionV1（:208）同构，仅动作域收窄
    item_id:      str
    action:       Literal["select_candidate", "reject_all", "request_reperception"]
    candidate_id: str | None                 # 仅 select_candidate 携带（同 :224 的互锁）
    reason_code:  CodeToken                   # 模型 MINT，v3 CodeToken（无数字，:222）
```

- `select_candidate` + `candidate_id`（某 tick 候选的 id）⇒ **一档**（认这个候选，值来自候选的 `OneTierValueV1`）。
- `reject_all` ⇒ **二档**（没有候选配得上，像素值站住）。
- `request_reperception` ⇒ 退回 reading 重读（边本身没量准）。
- ⛔ 模型全程只吐 **id 与枚举**，零坐标：`candidate_id` 是包成员（执行器 `UNKNOWN_RESPONSE_CANDIDATE` 校验），`reason_code` 是 `CodeToken`（无数字），坐标由代码从候选的 ref 算。

**为什么这样接不破铁律 + 强于上一稿**：
1. **铁律**：`TickClaimResponseV1` 的字段树**构造不出数字**（`_CFG` = `extra="forbid"` + 无数值字段 + 动作是封闭域），与既有响应侧的「无坐标」结构证明同款（可加一条 walk-the-tree 测试，⛔ 本稿不写实现）。
2. **阶段隔离（B-5#3）**：第一步在**类型层**就没有 `whole_building_review` 这条路 —— ⛔ 不是「填 accept」的纪律，是**结构上填不了**。第二步的响应仍用 `CorrectionDecisionResponseV1`（它带 review）。两步响应类型**判别分开**。

## D4 · 零阈值判据（⛔ 不许「差多少毫米算够近」；闭合 B-2）

⭐ 相比上一稿，本节把判据从「结果 ∈ cum 集合」改成**两道分离的精确检查 + 区间级不变量 + chain_derived 精确重算**，并**列全失效条件**。

### D4-a 判据表述（两道**分离**的精确检查，⛔ 不许用「即」混成一件事，闭合 N-2）

一档认领合法 ⟺ **同时**满足下面两道**各自独立**的精确检查（⛔ 无 epsilon、⛔ 无毫米阈值）：

- **检查① · 引用存在且角色闭合**：claim 的 `tier_one_value` 引用的每个 ref（`node_ref` 或 `operands[*].ref`）**都能在冻结字节里解析到**，且角色齐备（`chain_node` 要 1 个节点 ref；`axis_plus_half_wall` 要 `axis` + `half_wall_thickness` 各 1；`segment_span_diff/sum` 要 `cum_lo` + `cum_hi` 或一组 `segment_len`）。
- **检查② · 运算精确可复算**：代码在**声明的 0.1 mm 整数域**（`grid_units_from_mm`，`opening_synthesis.py:174`，round-trip 相等强制，`:180`）按 `value_source` 指定的**封闭运算**对 operands 重算：
  - `chain_node`：结果 = `grid_units_from_mm(node_ref 指的 cum 值)`。
  - `axis_plus_half_wall`：结果 = `axis_units ± half_wall_units`（符号由边角色 lo/hi 定）。
  - `segment_span_diff`：结果 = `cum_hi_units − cum_lo_units`。
  - `segment_span_sum`：结果 = `Σ segment_len_units`。
  重算结果**必精确 == `recompute_cert_units`**（整数比较，零 epsilon）。

⭐ **关键分辨（N-2）**：`grid_units_from_mm` 只证明「值落在 0.1 mm 存储格点上」（实测 `grid_units_from_mm(6925)=69250` 正常返回，而 `6925` **不在** East `cum_mm`）—— 它**不**证明值属于某链集合。所以检查①（引用+角色）与检查②（运算重算）**是两件事**，⛔ 不能用「即」连接、⛔ 不能只用存储格点成员冒充链成员。此外「合法区间宽度必是图纸整数」只是**当前样本现象、不是定理**（0.1 mm 表示本就允许小数毫米）；真正能证的是「宽度精确等于被引用尺寸段的整数域求和」。

**判分怎么写（零阈值）**：判据**不问「边离刻度多近」** —— 像素读数（6921.9）根本不进判据；进判据的是**认领结果**（节点 ref / 派生运算），它要么精确可复算要么红。**没有任何毫米阈值**。

### D4-b 成立性正面论证（含 B-2 承认成立的窄子域）

- **拒伪造**：任何「编出来、链上算不出」的 x 当场红（`chain_node` 填 `6925` ⇒ `6925` 不是 cum 成员 ⇒ 检查①失败；`chain_derived` 填错运算 ⇒ 检查②重算对不上 `recompute_cert`）。这是零阈值给的**真保证**。
- **窄子域的恒等式成立**（GPT B-2 承认的部分）：若 `lo`/`hi` 都认到**同一条干净链**的两个精确前缀和节点 `cum[i]`/`cum[j]` 且 `i<j`，则 `cum[j]−cum[i] = Σ values[i:j]`，整数域精确、零 epsilon。抽查已证：South `8730−6930 = 1800 = values_mm[2]`。
- **`chain_derived` 兑现权威口径**：`axis_plus_half_wall` 让 `2880/3120` 这类**非节点但链派生**的值合法（B-1），判据放行它靠的是「运算精确可复算」而非「结果 ∈ cum」。

### D4-c ⭐ 失效条件（验收 #3 硬要求：它在什么输入下判错；闭合 B-2）

零阈值判据是**必要非充分**。GPT 补出三类我上一稿漏掉的失效，逐一收进不变量：

1. **同节点塌缩**：`lo` 与 `hi` 都认领同一个节点（如都认 0）⇒ 逐边检查全绿，但**洞口宽度为 0**。⇒ **区间级不变量**（D2-b）强制 `lo` 与 `hi` **非零宽**（`hi_units > lo_units`），跨两条边查，逐边判据看不见。
2. **反向节点**：`lo` 认 6000、`hi` 认 0 ⇒ 两边分别通过成员检查，但**结果反向**。⇒ 区间级不变量强制 `lo_units < hi_units`（严格有序）。
3. **合法链派生边被误判红（false negative）**：上一稿「结果必 ∈ cum 集合」会把 `2880`（`axis±半墙厚`）判红。⇒ D4-a 检查②的判据是「**运算精确可复算**」而非「结果在 cum」，放行 chain_derived。
4. **认对「是个刻度」、认错「是哪个刻度」——判据看不见**：两个相邻节点很近，一条边指认到 A 或 B **都通过判据**。⇒ 区分「哪个刻度」是**指认**问题，归 D5 的**结构分流 + 模型**，⛔ D4 不兼职。
5. **链本身不闭合/被污染——判据地基塌了**：判据把 `cum_mm` 当权威合法集。前置门必须复用 `_require_chain_closed`（`evidence_adapters.py:564`，在 `:662` 调用；抽查 South/East `chain_closure_mm=0.0`）。这是判据的**前提**，不是判据能兜的。

**区间级不变量（D2-b 承诺、这里给全，闭合 B-2）**：一条洞口的 `lo`/`hi` 两条 claim 必须
① **同源**（两条边的证据档 `input_id` 同一条立面链）· ② **角色互异**（一个 lo、一个 hi）· ③ **严格有序**（`lo_units < hi_units`）· ④ **非零宽** · ⑤ 若为 `chain_derived` 则各自**重算精确**。⇒ 失效 1/2 被 ③④ 挡、失效 3 被 D4-a② 放行、失效 4 交 D5、失效 5 交前置门。

⇒ **零阈值做得到**（拒伪造 + 运算精确，均无毫米数），**但只覆盖「值是否为真链派生」这一问**；「是否该认、认哪个」由 D5 + 模型承担。**不触发 §六 A 层②**（判据成立，失效边界写全）。

---

## D5 · 按需触发：什么时候才惊动模型（⛔ 结构谓词，不用中点/阈值；闭合 B-3）

⭐ **上一稿用「相邻刻度中点划界」做自动分流 —— 那是把一个没人签字的判断（间距 1/2）挤到了别处**（GPT B-3 点名，且实测会把明确二档的 East `O01` 自动认成一档 `[0,0]`）。**本稿彻底换掉它**：分流只依赖 reading **已经提供**的**显式结构证据**，⛔ 无任何毫米/像素阈值。

### D5-实测：reading 每条边已自带指认证据（全量重量 68 条 x 边）

reading 立面产物 `openings[i].edge_witnesses.{x0,x1}` 每条边带：`dimension_refs`（链段名列表）· `nearest_tick_px` · `distance_mm`。`dimension_witnesses.x` 另给一张 `像素 → cum 值` 的**已解析刻度表**。我把四张立面 68 条 x 边全扫了一遍，**结构签名恰好三类**：

| 签名 | 含义 | 出现 | 分流 |
|---|---|---|---|
| **1CHAIN-CONSEC** | `dimension_refs` = **同一条链的两个相邻段**（如 `C_top_fine_s2 + s3`）⇒ 共享边界 = **唯一一个 cum 内部节点** | South 全 14 边 · East 24/26 · West/North 多数 | **自动一档**（D5-a）|
| **ALL_S1** | `dimension_refs` **全是 `_s1`**（多条链的开口段）⇒ 像素落在若干 6000/overall 段**内部**、无内部边界被引用 | **仅 East `O01` 两边**（d=535.8/2163.7mm）| **自动二档**（D5-a，`_s1` 证书）|
| **MULTI** | `dimension_refs` 来自 ≥2 条链、共 4 段 ⇒ 需查它们是否**共同指认同一个内部节点** | North 全部 · West 部分 | **同一节点 ⇒ 自动一档；否则 ⇒ 惊动模型**（D5-b）|

⭐ 实测：MULTI 的 North `O01` 两边 `nearest_tick_px` 经表映到 `1700 / 9700` ⇒ 宽 `8000`（正是派工方那条 `8039.0→8000`）。当前 fixture 里 MULTI 全部**共同指认同一节点** ⇒ 全自动一档；⚠️ **但「MULTI 一定同指」是数据巧合、⛔ 不是规则**（[[gate-teeth-direction-follows-fixture-inventory]]）—— 设计必须为「MULTI 指认分歧」留惊动模型的路，即使今天撞不上。

```text
# 全量重量命令（我自己跑过；三类签名的判定纯符号，⛔ 无毫米比较）
python3 -c "... 扫 sm25_{south,east,north,west}_as_drawn.json 的 edge_witnesses 的 dimension_refs 链-段结构 ..."
# 输出摘要：South 14/14=1CHAIN-CONSEC；East O01=ALL_S1 其余=1CHAIN-CONSEC；North 全 MULTI（均同指）；West 混合
```

### D5-a 自动认领（不惊动模型，走 `AutoActionV1`，`wall_compiler.py:318`）

**结构谓词**（⛔ 无阈值 —— 每个分支都是**符号判断**：段相邻、节点相等、集合基数）：
- **自动一档** ⟺ `nearest_tick_px` 经 `dimension_witnesses.x` 表解析到节点 N（**纯查表，无距离**），**且** N 被 `dimension_refs` **角色闭合**：存在某条链，其被引用的两个**相邻段**的共享边界 == N（1CHAIN-CONSEC 天然满足；MULTI 需两条链都指到**同一个** N）。⇒ 代码认成一档 `chain_node`（值 = N），记 `AutoActionV1`（带 `rule_id`，`:333` + 证据 ref），`provenance=auto`。
- **自动二档** ⟺ `dimension_refs` **全是开口段**（`_s1`）、**无任何内部边界被引用**、`nearest_tick_px` 解析到链原点（ALL_S1 证书）⇒ 边**结构上落在某段内部、无刻度可认** ⇒ 代码认成二档 `pixel_only`，记 `AutoActionV1`，`provenance=auto`。

### D5-b 惊动模型（进 `OpenItemV1` → D3）

⟺ **既非自动一档、也非自动二档**，即 witness **不角色闭合**：
- MULTI 的两条链**指认到不同节点**（真「哪个刻度」歧义）；
- `nearest_tick_px` 解析的节点与 `dimension_refs` 角色闭合的节点**矛盾**；
- refs 结构无法判定（残缺 / 角色不齐）。

⇒ 代码把候选（相关 cum 节点 + 可能的派生运算）列进 `OpenItemV1`，模型 `select_candidate`（认某候选→一档）/ `reject_all`（→二档）/ `request_reperception`（重读）。`provenance=model`（带 packet+item+decision hash）。

### D5-c ⭐ 为什么这是零阈值（对 B-3 的正面回答）

- 三个分支的判据全是**符号谓词**：①「refs 是不是同链相邻段」= 段名字符串比较；②「两条链是否指同一 N」= 节点相等；③「refs 是否全 `_s1`」= 段索引集合。**没有一处是「距离 ≤ X mm/px」**。
- `distance_mm`（6.8 / 535.8 / …）**只作为证据随 `OpenItem` 流给模型**，**永不进任何分支条件** —— 它是给模型看的上下文，不是门。
- ⇒ 上一稿「中点 = 间距 1/2」这个隐含阈值**被删除**；本稿分流不含任何数值边界。**不触发「引入新阈值」**（验收 #4）。

**省钱 + 少给模型乱动机会**：当前 fixture 66/68 自动（East `O01` 两边二档、其余全一档），模型每立面平均看 0–1 条边；且模型只能在**代码给定的候选**里选，⛔ 不能凭空移边。

---

## D6 · 两步之间的冻结：真封印类型（⛔ 不是纪律；闭合 B-4）

**要守的性质**：第一步产出的 `OpeningEdgeTickClaimV1`（含 tier / tier_one_value / provenance）进第二步（跨图配对 / B4）后，第二步**只能选与取舍，⛔ 不能改认领的值/档位/来源**。

⛔ **上一稿的三条（finalize+hash / validated carrier「无公开构造器」/ 无坐标字段）不足以成立**（GPT B-4 逐条驳）：
1. `finalize_bundle`（`evidence_contract.py:760`）是**公开纯函数**、在 `__all__` 里；改 `tick_ref`/tier 后**重新 finalize** 就得到自洽新 hash。**hash 是完整性校验，不是授权封印。**
2. 「`SealedTickClaimsV1` 无公开构造器」只是目标句 —— B2 返工 1/2 已证：`frozen=True` / 加下划线 / `__all__` 摘除 / 最外层 `isinstance` **都挡不住**公开构造器与鸭子元素（`2026-09-04w_B2_rework3.md` §③：「病根 = 构造能力公开 + Python 不强制注解元素类型」）。
3. 「没有坐标字段」并未冻结决定 —— 第二步把 `tick_ref` 从 A 换到 B、或 `tier` 换成 `pixel_only`，就已改了第一步事实，**无需写浮点**。

**⇒ 本稿的真封印（三条叠加，均为结构，复用 B2 返工 3 的最终范式，⛔ 不另造）**：

1. **构造时出示模块私有令牌**（B2 返工 3 §出路(a) 原话）：`SealedTickClaimsV1` 的构造**必须持有一个从不导出、从不返回、不存在于任何实例上的模块私有 seal 令牌**；`__all__` 里没有它、没有工厂返回它。⇒ 第二步**无法凭空铸造**封印载体。
2. **逐元素受封**（B2 返工 3 §出路(b)）：装配入口**不只查最外层类型**，还**逐个元素**核每条 `OpeningEdgeTickClaimV1` 确实来自封印通道 —— 且**元素类型本身也不可公开构造**（否则等于「加一句检查」，B2 返工 3 明警）。
3. **第二步从冻结字节重建、不信载体携带值**（B2 返工 3 §出路(c)）：第二步入口**不直接消费**载体里的 `tier_one_value` 数值，而是**从每条 claim 的冻结 ref + 第一步裁决账重新解析**一遍 —— 载体只当「一份可复算的索引」，改了载体里的值也没用，因为第二步照 ref 重算。

**正反例必须覆盖**（B2 裁决同款要求）：① 重 finalize 后替换 → 拒 · ② 替换某个元素 → 拒 · ③ 把某条边的 `tick_ref`/`tier` 从 A 换 B → 拒。第二步入口**只接受**该真封印类型，⛔ 不接受裸 `OpeningEdgeTickClaimV1` 列表。

⭐ **三条里 #1+#2 是承重的**（构造能力结构性不可获得），#3 让「即便拿到载体也改不动事实」。**这与 B2 返工 3 正在解的是同一道题** ⇒ 见 D7：应**等 B2 返工 3 过审、按其最终封印范式复用**，⛔ 不各造一套、⛔ 不碰 `multifloor.py`。

---

---

## 颗粒度收口：一档链真值 vs pipeline 10 mm 出口（闭合 B-5#5 —— **显式收口，不停报**）

**问题**（指南 §15.9 已举、GPT B-5#5 要求处置）：若某一档链值不是 10 mm 整数倍（指南例：`1935 mm`），而 pipeline 出口按 10 mm 规整，会把 `1935 → 1940`，**用格点产物覆盖了图纸真值**。⛔ 不许因当前 fixture 恰全为 10 mm 整数倍就略过。

**⭐ 我论证下来这条【能在设计层收口】，收口结论由已定死的 §14.2 直接推出，非新决策**：

1. **§14.2（行 1015-1016，用户已定死）**：洞口边坐标**只能取自尺寸链节点（或链算出的值）**，**像素测量永不作坐标值落地**。⇒ 一档坐标 **就是** 链节点值 / 链派生值本身。
2. 若把 10 mm 出口格点作用到一档值上，落地的 `1940` **既不是链节点、也不是任何链运算的结果** —— 它是像素域格点吸出来的数。**这直接违反 §14.2。** ⇒ 逻辑上，一档值**必须免疫** 10 mm 出口格点，否则 §14.2 不成立。
3. **§15.11 终裁**给了 10 mm 的身份：它是 **pipeline 出口**「**去浮点尾差的规整**」，服务的是**需要出干净数的那类值** —— 即**二档（纯像素）**。§15.11 推论 2 也明写 pipeline 出口与 gt 最大差半格 5 mm，判分必须**容差带**、⛔ 不许逐位相等。这些都是关于**二档/像素**出口的口径。

**⇒ 设计层收口（写进契约、不留给施工方猜）**：

| 档 | 出口处置 | 契约落点 |
|---|---|---|
| **一档** | **免疫 10 mm 出口格点**：坐标 = `tier_one_value` 的 ref/运算在 0.1 mm 整数域**精确落地**，⛔ 不经 10 mm snap | `OpeningEdgeTickClaimV1` **无坐标字段**（D2-b）⇒ 坐标由代码从 ref 现算、天然不过 snap；契约**显式声明**一档落地不消费 `output_precision` |
| **二档** | **消费 10 mm 出口格点**：`PixelOutV1` 记 `raw_pixel_ref → output_precision_ref（10 mm 声明点）→ rounded_result_units`，可复算 | `PixelOutV1`（D2-b）三字段即此派生证书 |

**§15.11 推论 1 配套**（GPT B-5#4）：判分侧核对的是「**gt 1 mm 与 pipeline 10 mm 各自被【显式声明】、各自被【消费】**」，⛔ **不是「两个数相等」**。本契约兑现它：`output_precision_ref` 是 pipeline 10 mm 的**单一声明点**（二档消费它、一档显式不消费）；gt 1 mm 是判分侧的分辨率声明。二者**故意不等**，判分用**容差带**（半格 5 mm）比对。

⚠️ **一处对用户的诚实提示**（⛔ 不是停报、不是待拍）：指南 §15.9 当时把「一档免疫格点」记成「主控提的新风险 · ⛔ 待用户拍」，那是 §14.2 与 §15.11 尚未被主控对撞时的状态。本稿的收口**只是把 §14.2 推到底**，⛔ 未引入任何新口径。**唯一需要用户留意的**：若用户本意是「一档也要 snap 到 10 mm」，则与 §14.2「坐标只能取自尺寸链」直接冲突 —— 那才需要用户重新拍 §14.2。**在 §14.2 不变的前提下，本收口是唯一自洽解，故不停报。**

---

## D7 · 风险清单：已落库哈希 / 已签字锁 / 在飞的单（更新到当前树，闭合 B-6）

⚠️ **上一稿 D7 对在飞线的描述已过期**（GPT B-6）。**当前树的真实在飞形态**（我 `ls` + `grep -n` 核过两单原件）：

| # | 风险面 | 当前树的真实改动面 | 与本方案的关系 |
|---|---|---|---|
| **R1 · T4-a 返工 2（已交件待审，⛔ 未合并）** | `2026-09-04x_T4a_rework2.md`：改 `opening_synthesis.py` 的 **obligation resolver/binding**，锁「**成功解析输入集合 == live key 集合**」（`opening_synthesis.py:338-365, 513-524`），且**明令 ⛔ 碰 B4 的 `affected_refs` 源绑定、⛔ 碰 `multifloor.py`** | 本方案也要改 `opening_synthesis.py` 的 **B4 输入**（把 `_elevation_openings` 从读裸 dict 改成读认领结果）⇒ **同文件直接碰撞**。⇒ 施工单**必须排在 T4-a 返工 2 合并过审之后**，重基线后**保持其 resolver/binding 与 `affected_refs` 锁不退化** |
| **R2 · B2 返工 3（已交件待审，⛔ 未合并）** | `2026-09-04w_B2_rework3.md`：改 `multifloor.py`，唯一阻断 = `ValidatedFloorLadder` **构造能力必须不可公开获得**（真 seal / 逐元素受封 / 从冻结字节重读）；⛔ 碰 `evidence_contract.py`/`opening_synthesis.py`/`evidence_adapters.py` | 本方案 **D6 的真封印正是同形问题**（validated carrier 类型层封印）。⇒ **D6 不能把 B2 称为「现成范式」** —— 它**还在解**同一道题。应**等 B2 返工 3 过审、按其最终封印形态复用**，⛔ 不各造一套、⛔ 施工不碰 `multifloor.py` |
| **R3 · 立面 bundle 既有哈希/锁** | `evidence_contract` 的 `finalize_bundle`（`:760`）/ `_sorted_bundle`（`:713`）/ `_payload_row_source_ids`（`:1103`），以及 `tarch_converter_reproducibility` 一类「同字节→同 bundle」锁 | 本方案给 `ElevationOpeningClaimV1` 加 x 四字段 + 两 witness ref，**进 `_sorted_bundle` dump** ⇒ **每个立面 bundle 的 `content_sha256` 变**。⇒ 施工须**重生成受影响立面产物基线 + 重签**，并核 `_payload_row_source_ids` elevation 分支同步加 x（否则 F-2 源闭合漏 x 的 input_id）|
| **R4 · content_sha256 churn 与 T4-a 叠加** | T4-a 给 `EvidenceDebtV1` 加 `obligation` 字段同样翻每个 finalize 过的 bundle 的 `content_sha256` | 本方案的 x 四字段也翻 `content_sha256` ⇒ **两笔叠加**。⇒ 施工单**在 T4-a 合并后排、一次重算基线**，⛔ 别与 T4-a 并发各翻一次（重蹈 banner ⑥b「只翻搅一次哈希」）|
| **R5 · B4 已合并主线 + docstring 依赖边** | `synthesize_openings` 从裸 dict 读 x、零容差配对（已合并、有锁）；改 `evidence_contract.py:544` docstring | 改 B4 输入 = 改已签字模块入口，属工程档、须派工换人审；docstring **⛔ 别写仓库根前缀的生产路径**（`affected_tests` 会建边，CLAUDE.md §8.5）|

**我读了在飞两单原件的证据**（验收 #6）：

```text
$ ls AI_agent/logs/reviews/request/2026-09-04{w_B2_rework3,x_T4a_rework2}.md   # 两单均在
$ grep -n "opening_synthesis|affected_refs|multifloor" .../2026-09-04x_T4a_rework2.md
  38-40: 两道类型钉量全局注册表与 stored keys（opening_synthesis.py:338-365, 513-524）
  94-95: ⛔ 碰 B4 的 affected_refs 源绑定 · ⛔ 碰 src/agent/correction/multifloor.py
$ grep -n "构造能力|SEALED|__all__|逐元素|从冻结" .../2026-09-04w_B2_rework3.md
  1: ValidatedFloorLadder 的构造能力必须不可公开获得
  72-75: (a) 真封印 模块私有令牌 从不导出/返回/存实例 · (b) 逐元素验证 元素类型本身不可公开构造
```

---

## 验收 #4 · 方案里出现的**每个数字**，逐个标【声明值】或【判断】（闭合 N-1）

⚠️ **上一稿这份自查 GPT 判「远非全量、且至少两处分类错误」**。本次做全：机械扫描 + 逐类判定。⛔ 分类以**身份**为准（源码行号/日期/版本号 = **声明性定位符**，非领域判据）。

| 类别 | 数字 | 判定 |
|---|---|---|
| **已签字颗粒度** | `0.1 mm`（存储表示）· `1 mm`（gt 分辨率）· `10 mm`（pipeline 出口）| **声明值**（§15.11 终裁 + `DECLARED_GRID_UNITS_PER_M=10_000` / `_GRID_UNITS_PER_MM=10`）·⛔ 非本单新设 |
| **既有代码类型约束** | `CodeToken` 无数字约束 · `ArtifactPointerV1` 四字段 · `Hex64` · 五种 effect · 三动作枚举 | **声明性/结构** ·引用既有类型（`decision_schema.py`），非本稿阈值 |
| **原料/实测**（图纸画的 or 产物读的）| South cum `0,5000,6930,8730,9450,11250,14750,16550,17270,19070,21300,23100,25000`；East cum `0,6000,6740,7640,8740,9640,10360,11260,12740,13640,14360,15260,16740,17640,18360,19260,20000`；East `values_mm` 16 段；像素读数 `6921.9/8751.2/536.7/2164.6`；`mm_per_px≈13.6`；宽度 `1800/900/2400/8000/600/800`；`8039.0`；`chain_closure_mm=0.0` | **声明值/观察值**（图纸链 or 产物像素）·非本稿判据；`0.0` 进的是**精确相等** `==` 判据（零阈值，非容差）|
| **实测统计（引用派工方，用于说明比例）** | `68` 条边 · `66` 自动 · `2` 离群 · 每立面 `0–1` 惊动 | ⚠️ `68/66/2` = **派工方实测的声明值**（我全量重量复现）；`0–1` = **由 66/68 外推的成本估算 = 判断**（作者估） |
| **reading witness 里的距离**（进证据、不进门）| `distance_mm = 6.8/20.3/27.1/535.8/2163.7/…` | **观察值**（reading 产的证据）· ⭐ **随 OpenItem 流给模型、⛔ 永不进任何分支** ⇒ 非判据阈值 |
| **既有经验 cutoff（⚠️ 上一稿分类错）** | `≤34 mm` | **判断值** —— 它是**派工方/指南**用于统计「靠近」的经验 cutoff。**本稿生产判据 ⛔ 不使用它**（分流已换成结构谓词）；但它**是判断、不是声明值**（上一稿标成声明值，错，已改）|
| **反例/构造示例** | `6925`（`grid_units_from_mm` 返回 69250 但不在 East cum，用于 N-2 反证）· `2880/3120`（`axis 3000 ± 半墙厚 120` 的 chain_derived 示例）· `240` 墙厚 | **判断/示例**（作者构造，用于论证），⛔ 非外部签字声明 |
| **⭐ 隐含判断阈值（上一稿有、本稿删除）** | 相邻 tick「中点」= 间距 `1/2` | **判断** —— **上一稿的隐含新边界，本稿 D5 已彻底删除**（换成结构谓词），故本稿**不再出现**此判断 |
| **文档/类型/结构标识** | `D1–D7`·`B-1..B-6`·`N-1/N-2`·`R1–R5`·`V1/V3`·`O01`·`sm25`·`_s1..s6`·模块/跳/档位/下标计数 | **声明性标识/结构计数**，非数值判据 |
| **日期/commit/版本** | `2026-09-05/04/03/01`·`09.04/05`·`ac9a0669`·`5804ae4b`·`e9a45226` | **声明性身份**，非判据 |
| **源码行号（我 grep 核过）** | `evidence_contract.py`: 170/190/531/544/553-556/559/564/609/662/704/713/760/821/1103/1215/1225/1650；`opening_synthesis.py`: 130/133/153/174/180/693/713/746/887/899；`decision_schema.py`: 170/174/182/190/192/208/220/335/356/366；`wall_compiler.py`: 119/217/225/227/296/304-309/318/333；T4-a: 338-365/513-524 | **声明性定位符** |

**结论**：本稿**没有任何「差多少毫米算够近」式的判断阈值** —— 分流是结构谓词（段名/节点相等/集合）、判据是精确 `==`/整数重算。所有毫米数要么是图纸/产物的**声明/观察值**（举例说明），要么进的是**精确相等**判据。⚠️ 本稿仍存在的**判断类数字**（诚实列出，非阈值）：`≤34 mm`（既有 cutoff，本稿**不用**）· `0–1` 条（成本估算）· `2880/6925`（论证用反例）—— 它们**都不进生产判据分支**。

---

## 验收 #7 自证 · 零 `src/` 与 `tests/` 改动

```text
$ git status --porcelain
 M AI_agent/logs/reviews/execution/2026-09-05a_tick_claim_design_rework1.md   # 仅本交件
   （另有两份预置材料 2026-09-04u 执行档 / 2026-09-04y 裁决书已在基点提交里，非本轮改）

$ git diff --stat ac9a0669..HEAD -- src tests
（空 —— src/ 与 tests/ 零改动，exit 0）
```

全程只写 `AI_agent/logs/reviews/execution/` 下一份 md，**分段提交 3 次**（seg1 header+D1+D2+D3 · seg2 D4+D5+D6 · seg3 D7+颗粒度+对账）。

---

## 逐条对账表（6 阻断 + 2 不阻断，每条：怎么闭合 + 证据）

| 裁决项 | 上一稿的病 | 本稿怎么闭合 | 证据 |
|---|---|---|---|
| **B-1** 一档错收窄成 `cum_mm` 节点 | D2/D4 强制一档必是 cum 节点成员 | 一档改**判别联合** `chain_node \| chain_derived`；`chain_derived` 带**封闭运算枚举 + 角色化 operands + 可复算证书**（axis±半墙厚/分段相减/累加）| D2-b `OneTierValueV1`/`ChainDerivedValueV1`；D2-c `2880` 示例；§14.2b 行 1038/1166 |
| **B-2** 失效条件不全 + 缺区间不变量 | D4 只列三类失效，逐边查 | 补**区间级不变量**（同源/角色/严格有序/非零宽/派生重算），失效补**同节点塌缩/反向节点/合法派生 false-negative** | D4-c 五条 + D2-b 区间不变量 |
| **B-3** D5-c 中点分流 = 挤走的未签字判断 | 「相邻 tick 中点划界」隐含间距 1/2、把 East O01 认成一档 | **删除中点**；分流改**结构谓词**（reading `edge_witnesses` 的链-段角色闭合），⛔ 无毫米/像素阈值；East O01 结构上判**二档** | D5 全节 + 68 边实测三签名 |
| **B-4** 冻结未在类型层成立 | finalize+hash 可重签、「无公开构造器」是目标句、可换 tick_ref | **真封印**：模块私有令牌 + 逐元素受封（元素类型本身不可公开构造）+ 第二步从冻结字节重建；正反例覆盖重finalize/换元素/换 tick | D6 三条 + 复用 B2 返工 3 §出路(a)(b)(c) |
| **B-5** 裁决账/阶段隔离/颗粒度未进契约 | claim 不记来源、复用带 review 的响应、颗粒度冲突略过 | **裁决账** `ClaimProvenanceV1` 绑定；**第一步独立响应类型** `TickClaimResponseV1`（结构无 whole_building_review）；**颗粒度收口**（一档免疫格点，由 §14.2 推出）| D2-e + D3-b + 颗粒度收口节 |
| **B-6** D7 在飞线描述过期 | 只笼统写「排在 B2 之后」、漏 T4-a 返工 2 | D7 更新到**当前树**：T4-a 返工 2 改 `opening_synthesis.py`（碰撞面）+ B2 返工 3 改 `multifloor.py`（同形封印）| D7 R1/R2 + `grep` 两单原件 |
| **N-1** 数字自查非全量+两处分类错 | `≤34mm` 标成声明值、中点 1/2 漏计 | 全量机械扫描分类；`≤34mm` 改标**判断值**、中点**已删除**、`0–1` 标**估算判断** | 验收 #4 全表 |
| **N-2** 存储格点 vs 链成员混成一件事 | D4 用「即」把两道检查连起来 | D4-a 拆成**两道独立精确检查**（引用+角色 / 运算重算），并证 `grid_units_from_mm(6925)` 反例 | D4-a + 关键分辨段 |

---

## 最薄弱一处

**D3 的候选枚举（甲/乙两路）与 `SymbolicCandidateV1` 的边界。** B-1..B-6 六条阻断我都有实测或类型层论证垫背（D5 三签名全量重量、D4 反例 `6925`、D6 复用 B2 已定门、颗粒度由 §14.2 推出）。但 **D3 把「认哪个刻度/哪个派生运算」表达成 `OpenItemV1` 的候选**这一步，我给了两路（甲复用 `SymbolicCandidateV1` / 乙新增 `TickCandidateV1` 判别联合）却**未实测**哪一路在真实 packet 里更省、更不易让 `SymbolicOperation`（现全是墙厚语义，`wall_compiler.py:119`）被刻度语义污染。乙路的判别联合更干净但要动 `OpenItemV1` 的候选载体类型；甲路少改类型但把两种语义混进一个枚举。**风险**：若施工时发现 `OpenItemV1.candidates` 的现有消费者（执行器成员校验、`UNKNOWN_RESPONSE_CANDIDATE`）对判别联合候选有隐含假设，乙路可能要连带改执行器。⇒ **施工前应先读一遍 `OpenItemV1.candidates` 的全部现有消费者**，确认判别联合候选不破坏执行器的成员校验，再定甲/乙。这是本稿唯一没有类型层或实测垫背、留给施工单先勘的选择点。
