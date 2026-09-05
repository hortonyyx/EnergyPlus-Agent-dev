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

---
