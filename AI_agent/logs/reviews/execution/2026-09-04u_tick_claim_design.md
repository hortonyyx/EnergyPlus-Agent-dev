# 执行档 · 刻度认领 · 设计稿（T0 只读勘察 + 契约形态方案）

- **日期**：2026-09-04 · **施工方**：Claude 家族席位 · **审**：GPT 或 GLM 家族（⛔ 不得 Claude）
- **任务书**：[`2026-09-04u_tick_claim_design`](../request/2026-09-04u_tick_claim_design.md)
- **工作目录**：`/tmp/tick_design_claude` · **分支**：`wt/09.04u_tick_claim_design`（基点 `e9a45226`）
- **结论先行**：**x 应当进证据契约层**（§二问题不停报，正面论证见 D2 后半）。落点 = `ElevationOpeningClaimV1`
  与 z 对称地加 `x_lo_m/x_lo_ref/x_hi_m/x_hi_ref`（**证据档**，纯像素、带冻结字节溯源）；**认领结果**是
  另一层产物（`OpeningEdgeTickClaimV1`，D2）。零阈值判据成立（D4，**必要非充分**，失效条件写全）。
  ⛔ 全程零 `src/`、零 `tests/` 改动，`git status` 自证（末尾）。

## 〇、开工自证 + 两件必须先说的事

**开工自证输出原文**：

```text
/tmp/tick_design_claude
e9a45226 09.04f_wrapup_third_leg
A  AI_agent/logs/reviews/request/2026-09-04u_tick_claim_design.md
```

（仅派工单一份 staged、未提交；`src/` `tests/` 洁净。）

**B 层记一条 ①（继续）**：派工单「第一件事」指名读**指南 §十四 / §十五**，但
`AI_agent/guides/reading_correction_split_guide.md` 全文 966 行、章号止于 **§十三 + §十之二**，
**不存在 §十四 / §十五**（`grep -n '^#\{2,3\} 十'` 原文）：

```text
717:## 十、⭐⭐⭐ 2026-08-28 用户拍板（六条，本节 = 当前唯一口径）
776:## 十之二、⭐⭐⭐ 2026-09-01 用户拍板：**旧格式不兼顾，整条拆干净**
820:## 十一、⭐⭐ 2026-08-28 实测：**碎片问题的真相与它的归属**
866:## 十二、⭐⭐⭐ 2026-08-29 定：**gt 侧确定性配对的【准入条件】**
899:## 十三、⭐⭐⭐ 2026-09-02 用户令：**⛔ 不许特化到现有这几个 case**
```

不停报（B 层）：我读了指南与本单直接相关的 **§〇之二（全流程图）· §一（分工）· §十· §十二（gt 侧配对准入）· §十三**，
口径足够。**若派工方本意指别处的「§十四/§十五」，请在审阅时点名，我补读。**

**B 层记一条 ②（继续，且对 D1 承重）**：派工单 §一表中「立面洞口竖边 68 条…认领后宽度全变图纸整数」
我按要求抽查两条，**复现且数值吻合到亚毫米**（命令原文在 §抽查）：South `O01` 两竖边 `6921.9 / 8751.2 mm`
认领到链刻度 `6930 / 8730`（宽 `1829.3 → 1800`）；East `O01` 两竖边 `536.7 / 2164.6 mm` 落在东立面
第一段 6000 mm 内、**最近刻度都是 0.0（距 536.7 / 2164.6 mm）** ⇒ 无刻度可认 ⇒ 二档。**派工方事实成立。**

### 抽查命令原文

```text
$ python3 -c "import json; d=json.load(open('.../sm25_south_as_drawn.json')); print(d['calibration']['x']['cum_mm'])"
[0.0, 5000.0, 6930.0, 8730.0, 9450.0, 11250.0, 14750.0, 16550.0, 17270.0, 19070.0, 21300.0, 23100.0, 25000.0]
# South O01 x_range_m = [6.9219, 8.7512] m → 边 6921.9→tick 6930 (dist 8.1) · 边 8751.2→tick 8730 (dist 21.2)
$ ... east cum_mm = [0.0, 6000.0, 6740.0, 7640.0, ...]  # East O01 x_mm=[536.7, 2164.6], 两边最近 tick 均 0.0
```

（原料：`AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_{south,east}_as_drawn.json`。）

---

## D1 · 勘察落点：x 从 reading 产物到配对的完整路径（逐跳 file:line + 溯源/档位）

⭐ 每一跳的行号我自己 `grep -n` 过（见各跳末括注），⛔ 未引派工单里的行号。

| 跳 | 位置（file:line） | x 在这里是什么 | 有无冻结字节溯源 | 有无证据档位 |
|---|---|---|---|---|
| **0 · 产物** | reading 立面产物 JSON `openings[i].x_range_m`（如 `.../sm25_south_as_drawn.json`，schema `as_drawn_elevation_v0`）| 一对 `[x_lo_m, x_hi_m]` 浮点，**像素换算而来**（`mm_per_px ≈ 13.6`）| ❌ 是磁盘上的裸 JSON 值，无 `ArtifactPointerV1` | ❌ 无（既非一档也非二档，只是「像素读数」）|
| **1 · 适配器** | `adapt_as_drawn_elevation`（`evidence_adapters.py:609`）建 `ElevationOpeningClaimV1`，**只搬 z**：`z_low_ref=_pointer(...,"/z_range_m/0")`（`:704`）、`elevation_opening_claims=elev_openings`（`:821`）| **x 根本没被搬进 bundle** —— 适配器只对 `z_range_m` 建 `z_low_ref/z_high_ref`（`:700-707`）| ❌ x 不在场 | ❌ x 不在场 |
| **2 · 契约类型** | `ElevationOpeningClaimV1`（`evidence_contract.py:531`），docstring `:544`「`x_range_m` deliberately NOT here」| 类型上**只有** `z_low_m/z_low_ref/z_high_m/z_high_ref`（`:553-556`）| ❌ x 无字段 | ❌ x 无字段 |
| **3 · 校验器** | `validate_evidence_bundle` 逐条重算 z 相等（`evidence_contract.py:1631-1658`，`ELEVATION_Z_VALUE_DRIFTED_FROM_SOURCE`）| **只校 z**，无 x 分支 | z 有（`_deref_pointer` 对冻结字节 `==`）；**x 无** | x 无 |
| **4 · 配对消费者 B4** | `synthesize_openings(elevation_doc: dict, ...)`（`opening_synthesis.py:746`）| **直接从原始 dict 读**：`_elevation_openings(doc)`（`:693`）在 `:713` 取 `("x_range_m","z_range_m")`；`:887` `for oid, x_lo, x_hi, z_lo, z_hi in ...` | ❌ **绕过整个 bundle**，`elevation_doc` 是裸 dict | ❌ 无 |
| **5 · 用作坐标** | `opening_synthesis.py:894-901`：`grid_units(x_lo)` → `world_lo = along_origin_u + sign * lo_u` → 世界区间做**零容差**等值配对（`:914-935`）| 像素外推 x 被当**权威坐标**参与等值 | ❌ | ❌ |

（跳 1/2/3 行号：`grep -n "def adapt_as_drawn_elevation\|z_low_ref=_pointer\|elevation_opening_claims=elev\|class ElevationOpeningClaimV1\|The horizontal extent\|z_low_ref\|z_high_ref" src/agent/correction/{evidence_adapters,evidence_contract}.py`；
跳 4/5 行号：`grep -n "x_range_m\|def _elevation_openings\|world_lo = along_origin\|for oid, x_lo" src/agent/correction/opening_synthesis.py`。）

### D1 的三条硬结论

1. **派工方核到的落点属实**：x 从产物到 B4 配对，**全程五跳没有一跳有冻结字节溯源、没有一跳有证据档位**。
   z 有契约（跳 2/3），x 完全裸奔。
2. ⭐ **比派工单更进一步的一条**：即便是**有契约的 z**，B4 也**没消费契约** —— `synthesize_openings` 收的是
   `elevation_doc: dict`（`:748`），z 也走 `_elevation_openings` 从裸 dict 读（`:905-906`）。
   全仓对 `elevation_opening_claims` 的**唯一消费者是校验器**（`grep -rn "elevation_opening_claims" src` ⇒
   只有 `evidence_adapters`〔产〕、`evidence_contract`〔校/排序/哈希〕，**无任何配对/装配消费**）。
   ⇒ **本单不仅要给 x 建契约，还要把 B4 从「读 dict」改成「读认领结果」**，否则建了契约也没人读（同 §D7 风险）。
3. **B4 未接线**：`synthesize_openings` 在 `src/`、`scripts/` 里**零调用**（`grep -rn "synthesize_openings" src scripts` ⇒
   仅定义处与自身 docstring）。⇒ 这条 x 路**今天连 pipeline 都还没接上**（与 CLAUDE.md §2 banner ⑥b「洞口对齐等用户拍次序」一致）。
   **好处**：改造 x 路**不动任何在跑的生产消费者**（唯一潜在消费者 B4 尚未接线）。

---

## D2 · 契约形态方案：一条洞口边的裁定结果长什么样

先分清**两层不同的东西**（今天全项目把它们混成「x_range_m 一个裸值」，这就是病）：

- **证据档（输入侧，纯搬运）**：洞口边的**像素读数**，带冻结字节溯源。它是「指认」证据，权威**天然是二档**，
  ⛔ 认领之前不作坐标。落点 = **`ElevationOpeningClaimV1` 与 z 完全对称地补 x**。
- **裁定结果（输出侧，D2 的主体）**：第一步「尺寸证据裁定」对**这一条边**下的结论 —— 几档、值从哪来、依据哪几条链节点。
  落点 = **新产物 `OpeningEdgeTickClaimV1`**（每条竖边一行）。

### D2-a 证据档：`ElevationOpeningClaimV1` 补 x（只写形状与不变量）

```
ElevationOpeningClaimV1（在既有 z 四字段旁，镜像地加）:
    x_lo_m:  float          # 像素读数，逐字来自 /openings/<i>/x_range_m/0
    x_lo_ref: ArtifactPointerV1   # json_pointer = "/openings/<i>/x_range_m/0"
    x_hi_m:  float          # 逐字来自 /openings/<i>/x_range_m/1
    x_hi_ref: ArtifactPointerV1   # json_pointer = "/openings/<i>/x_range_m/1"
```

**不变量**（全部与 z 现有校验同构，`evidence_contract.py:1631-1658` 已是模板）：
- `x_lo_m == 冻结字节(/openings/<i>/x_range_m/0)`、`x_hi_m == 冻结字节(...1)`，**精确 `==`，⛔ 无容差**
  （两侧是同一 JSON 字面量解析两次，差即撒谎）。
- `x_lo_m < x_hi_m`（同 `_z_direction_agrees`，`:558`）。
- F-2 单源：`{source_ref, x_lo_ref, x_hi_ref}.input_id` 必须同一（同 z 的 `:1660-1665`）。
- 适配器侧：`adapt_as_drawn_elevation` 在建 z ref 处**同点建 x ref**（`evidence_adapters.py:700-707` 旁），
  `_payload_row_source_ids` 的 `elevation_opening_claims` 分支（`evidence_contract.py:1118-1123`）**加上 x_lo_ref/x_hi_ref**。

### D2-b 裁定结果：`OpeningEdgeTickClaimV1`（每条竖边一行 —— D2 三问的正式答案）

```
OpeningEdgeTickClaimV1:
    edge_id:        str            # <opening_id>:<lo|hi>，来自证据档，非数组下标
    evidence_ref:   ObservationRefV1   # 指回证据档那条边的像素读数（指认，不作坐标）
    # —— ① 它是几档 ——
    tier:           Literal["chain_backed", "pixel_only"]   # 一档 / 二档
    # —— ② 值从哪来 ——
    value_source:   Literal["chain_node", "segment_sum", "pixel"]
    # —— ③ 依据哪几条 dimension_refs ——
    dimension_refs: tuple[ArtifactPointerV1, ...]   # 指向 calibration.x.cum_mm 的具体节点
    resolved_local_x_ref: ArtifactPointerV1 | None  # 一档：指向被认领的那个 cum_mm 节点字节；二档：None
```

**硬不变量**（这些是 D2 的承重处，⛔ 不写实现）：
- `tier=="chain_backed"` ⟺ `value_source ∈ {chain_node, segment_sum}` 且 `dimension_refs` **非空** 且
  `resolved_local_x_ref` 非空；`tier=="pixel_only"` ⟺ `value_source=="pixel"` 且 `dimension_refs` **恰好为空** 且
  `resolved_local_x_ref is None`。（枚举与字段互锁，同 `FaceDispositionV1._status_fields_agree` 的写法，`:418`。）
- **⛔ 本类型不带任何坐标值字段**：认领结果**只说「是哪个链节点」（ref），坐标由代码从该节点算**
  —— 与不变量「模型/裁定层出决定，代码出坐标」一致（下游从 `resolved_local_x_ref` 指的 `cum_mm` 字节取值）。
  一档的世界坐标 = `along_origin + sign * cum_mm[node]`，全部代码算，本层不落浮点。
- **二档不是缺陷**（指南 §〇 第 4 条）：`pixel_only` 是干净出口，`dimension_refs=()` 是「没有可指认刻度」的**显式**记录。

### D2-c 三问的具体例子（验收 #2：一档 + 二档各一）

**一档 —— South `O01`**（`x_range_m=[6.9219, 8.7512]`，cum_mm 含 `6930/8730`）：
| 边 | ① tier | ② value_source | 值从哪来 | ③ dimension_refs |
|---|---|---|---|---|
| `O01:lo` | `chain_backed` | `chain_node` | 链节点 `6930 mm`（像素 6921.9 指认到它）| `/calibration/x/cum_mm/2` |
| `O01:hi` | `chain_backed` | `chain_node` | 链节点 `8730 mm` | `/calibration/x/cum_mm/3` |
⇒ 宽度 = `8730-6930 = 1800 = values_mm[2]`（一段画出的尺寸，`segment_sum` 退化为单段）。**零容差成立**（两端都是精确 tick）。

**二档 —— East `O01`**（`x_range_m=[0.5367, 2.1646]`，落在东立面第一段 6000 mm **正中**，无中间刻度）：
| 边 | ① tier | ② value_source | 值从哪来 | ③ dimension_refs |
|---|---|---|---|---|
| `O01:lo` | `pixel_only` | `pixel` | 像素读数 `536.7 mm`（按出口 10 mm 颗粒度出干净数）| `()` |
| `O01:hi` | `pixel_only` | `pixel` | 像素读数 `2164.6 mm` | `()` |
⇒ **不强行认领**：最近 tick 是 0.0、距 536.7 mm，认了就是大错。二档如实标出，权威低，⛔ 非失败。

### D2-d ⭐ §二的正面论证：x 该进这层，且不破坏 docstring 原意（⛔ 不停报）

docstring（`evidence_contract.py:544`）原意两句：**(a)**「x 故意不在，B4 拥有需要它的跨视图配对」·
**(b)**「这层只带**被具名消费者要过**的东西」。逐句核：

1. **(b) 是这层的真原则，我的方案恰好履行它、不违反它。** B3 加 z 时（`:531` 起 docstring、`:95-98` 变更记）
   走的就是同一逻辑：`WindowV3.z needs the number, so the number travels here` —— z 从前也「不在这层」，
   **有了具名消费者（`WindowV3.z`）才带进来，且必带冻结字节溯源**。x 现在**同样有了具名消费者**：
   第一步的刻度认领要对 x 裁定，而裁定的证据必须挂在带溯源的载体上（D1 证明今天它挂在裸 dict 上 = 病）。
   ⇒ 按 (b) 自己的判据，x **现在有资格进**，进法与 z 逐字对称。
2. **(a) 的事实前提已经变了，不是原则变了。** 「B4 拥有需要 x 的配对」当时等价于「x 还没有证据层消费者」。
   但 D1 跳 4/5 证明：B4 靠**读裸 dict** 拿 x，零容差配对**永远对不上**（banner ⑥b：真实四立面配 0 对）——
   **这正是「x 没有证据档位」的直接恶果**。让 x 带溯源进层、B4 改读认领结果，**恰恰是在兑现 (a)**
   （B4 仍拥有配对，只是配对喂的是认领后的一档值而非像素外推值）。原意「B4 owns pairing」保留，**改的只是它读什么**。
3. **反面验证（我认真想过「x 不该进这层」的可能）**：若把 x 认领结果放进一个**平行的新层**、
   `ElevationOpeningClaimV1` 只留 z，会造出「一个洞口的 x 与 z 分属两个溯源载体」——正是指南 §〇之二警告的
   **F-130「两条并列生产线各自漂移」**形状。x 与 z 读自**同一个** `/openings/<i>` 节点、共享 `source_ref`，
   拆开无收益、有漂移风险。⇒ **证据档 x 与 z 同类**（D2-a）；**裁定结果**才另立一层（D2-b，因为它是第一步的**产出**，不是 reading 的搬运）。

⇒ **结论：x 应当进证据契约层，落点如 D2-a/D2-b。不触发 §六 A 层①。**

---

## D3 · 模型那一拍怎么接（`CorrectionDecisionPacketV1` / `CorrectionDecisionResponseV1`）

⭐ 现有机制**已经够用，几乎不用扩响应侧** —— 这正是铁律「模型只回决定、⛔ 不回坐标」在类型层的落地方式，复用它最省、最安全。

**现状回顾**（我核过）：
- 包（code→model）`CorrectionDecisionPacketV1`（`decision_schema.py:174`）带 `open_items: tuple[OpenItemV1,...]`（`:192`）；
  每个 `OpenItemV1`（`wall_compiler.py:296`）带 `candidates: tuple[SymbolicCandidateV1,...]`（`:313`），
  候选是**代码枚举**的、带 code-computed preview（`SymbolicCandidateV1`，`wall_compiler.py:217`）。
- 响应（model→code）`ItemDecisionV1`（`decision_schema.py:208`）：`action ∈ {select_candidate, reject_all, request_reperception}`，
  `candidate_id: str`（**回显包里的 id**，执行器校成员资格 `UNKNOWN_RESPONSE_CANDIDATE`）。
  **响应树无任何数值字段**（`decision_schema.py:30-41` 的结构性证明 + `CoordinateSmuggledInResponse` 走查）。

**刻度认领怎么套进去**（⛔ 只写形状）：
1. **`OpenItemV1.kind` 扩一个枚举值**：`"opening_edge_tick_claim"`（`wall_compiler.py:304-309` 的 Literal 里加一项 —— 这是**可见 diff**，不是自由文本）。
   `scope_entity_ids` = 那条洞口边的 `edge_id`；`source_refs` = 证据档 x ref（D2-a）+ 候选链节点 refs。
2. **候选 = 代码枚举的链节点**。两条路，**推荐后者**：
   - (甲) 复用 `SymbolicCandidateV1`：`symbolic_operation` 枚举加 `"CLAIM_CHAIN_TICK"`（`wall_compiler.py:119` 的 Literal），
     每个候选一个 cum_mm 节点，`preview_constant_pos_m` 放 code-computed 预览值（**preview 是代码算的，不是模型回的**）。
   - (乙) 若不想动 `SymbolicOperation` 语义（它现在全是墙厚操作），新增一个**平行候选类型** `TickCandidateV1`
     `{candidate_id: str, tick_ref: ArtifactPointerV1, preview_local_x_m: float}`，`OpenItemV1` 用判别联合承载。
   两路的共同点：**候选 id 由代码 mint、preview 由代码算、模型只在 id 之间选**。
3. **响应侧：一字不改就够**。模型对该 open item 回 `ItemDecisionV1`：
   - `select_candidate` + `candidate_id`（某个 tick 节点的 id）⇒ **一档**（认领这个节点）；
   - `reject_all` ⇒ **二档**（没有 tick 配得上这条边，像素值站住）；
   - `request_reperception` ⇒ 退回 reading 重读（边本身没量准）。
   ⛔ **模型全程只吐 id 与枚举，零坐标**：`candidate_id` 是包的索引成员（执行器校验），
   `reason_code` 是 `CodeToken`（`decision_schema.py:129`，无数字），坐标由代码从 `tick_ref` 指的字节算。

**为什么这样接不破铁律（承重论证）**：`CorrectionDecisionResponseV1`（`:356`）**类型上构造不出数字**
（`decision_schema.py:36-40`：`extra="forbid"` + 无数值字段 + 五种 effect 是封闭域）。刻度认领**没有新增任何**
需要模型吐数的通道 —— 它把「认哪个刻度」表达成「在代码枚举的候选 id 里选一个」，与现有 `select_candidate`
选墙厚候选**同构**。⇒ 「模型回坐标」在类型层依旧不可表达，认领只是多了一种 `OpenItem.kind`。

---

## D4 · 零阈值判据（⛔ 不许「差多少毫米算够近」）

### D4-a 判据表述
把认领结果的**合法取值集合**限制成「尺寸链能给出的值」：

> **一档认领合法 ⟺ 被认领的每条边的 local x 值，精确等于 `calibration.x.cum_mm` 里的某一个节点值**（在项目声明的
> 0.1 mm 整数栅格上做**精确成员判定**，即 `opening_synthesis.grid_units` 那套 round-trip 相等，`opening_synthesis.py:153-171`，
> ⛔ 无 epsilon）。于是一条洞口的一档区间 `[cum_mm[i], cum_mm[j]]` 的长度 = `cum_mm[j]-cum_mm[i]`
> = `values_mm[i..j-1]` 之和 = **恰好等于图纸画出的一段或连续几段之和**（cum 是 values 的精确前缀和，抽查已证：
> South `8730-6930=1800=values_mm[2]`）。

**判分怎么写（零阈值）**：判据**不问「边离刻度多近」**，只问「认领结果里填的值，是不是链上真有的一个节点」——
是 `cum_mm` 的成员就合法，不是就红。**没有任何毫米阈值**：像素读数（6921.9）根本不进判据，
进判据的是**认领后的值**（6930），它要么 `== cum_mm[k]` 要么不等。

### D4-b 成立性正面论证
- **拒伪造**：任何「模型/代码编出来、链上没有的 x」都当场红（`6925` 不是 cum_mm 成员 ⇒ 不合法）。这是零阈值能给的**真保证**。
- **区间=画出的尺寸**：因 cum 是精确前缀和，合法区间必然 = 某几段连续 `values_mm` 之和，
  ⇒ 认领后的洞口宽度**必是图纸整数**（派工单 §一实测：1829.3→1800、936→900… 全部落在 `values_mm` 上）。
- **与已有零阈值范式一致**：`opening_synthesis` 全模块已经在用「声明栅格上的精确 `==`」而非容差
  （`opening_synthesis.py:56-68`、`grid_units` `:166`）。本判据是同一范式搬到「候选集 = cum_mm 节点」。

### D4-c ⭐ 失效条件（验收 #3 硬要求：它在什么输入下判错）
零阈值判据是**必要非充分**。三种失效，逐一写清：

1. **认对了「是个刻度」，认错了「是哪个刻度」——判据看不见。** 若两个相邻 cum_mm 节点相距很近（
   而像素分辨率 `mm_per_px≈13.6`），一条边的像素读数离两个节点都在一像素内，认领成 A 或认领成 B **都通过判据**
   （两者都是合法 cum_mm 成员）。判据只保证「值是画出来的尺寸」，**不保证是界定这条边的那个尺寸**。
   ⇒ 区分「哪个刻度」的唯一证据是**像素指认**（`evidence_ref`/`witness`），**这正是这类必须惊动模型的原因（见 D5）**，
   ⛔ 判据自己解决不了，也不该假装能。
2. **该二档的边被强行认成一档——若判据被误写成「区间必须等于某段之和」就会犯。** East `O01`（二档）
   两端离最近 tick 536.7/2164.6 mm；若强制「必须认到某个节点」，它会被认成 `[0, 6000]` 之类**大错但"合法"**的区间。
   ⇒ **判据必须允许 `pixel_only` 作为一等出口**（D2-b），把「有没有资格认一档」交给「边是否精确落在某 tick 的
   指认半径内」这个**上游门**（那是 D5 的自动/惊动分流，仍零几何阈值 —— 用「像素读数到最近 tick 的排序」而非「毫米阈值」判，
   见 D5-b），⛔ 不能让 D4 的等值判据兼职做「该不该认」。
3. **链本身不闭合/被污染——判据的地基塌了。** 判据把 `cum_mm` 当权威合法集。若某立面链 `chain_closure_mm ≠ 0`
   或 cum_mm 有脏节点，则「合法集」本身错，认领全体失真。⇒ 前置门必须复用已有链闭合校验
   （`evidence_adapters._require_chain_closed`，`adapt_as_drawn_elevation:662`；抽查 South/East `chain_closure_mm=0.0`）。
   这是判据的**前提**，不是判据本身能兜的。

⇒ **零阈值做得到**（拒伪造 + 区间=画出尺寸，均无毫米数），**但只覆盖「值是否为真刻度」这一问**；
「是否该认、认哪个」由 D5 的分流 + 模型承担。**不触发 §六 A 层②**（判据成立，失效边界写全）。

---

## D5 · 按需触发：什么时候才惊动模型

66/68 条边无歧义 ⇒ 绝大多数应**代码自动认领（`AutoActionV1`）**，只把真歧义送模型。分三类：

### D5-a 自动认领（不惊动模型，走 `AutoActionV1`，`wall_compiler.py:318`）
一条边**恰好有唯一一个 cum_mm 节点**落在它的像素指认半径内（即：把该边像素读数到各 tick 的距离排序，
**最近的一个显著唯一**）⇒ 代码直接认成一档，记 `AutoActionV1`（带 rule id + 证据 ref），⛔ 不进 open_items。
这覆盖派工单说的 66/68。

### D5-b 惊动模型（进 `OpenItemV1`，D3）
仅当**有歧义**，两种形态：
1. **多刻度争一边**：最近的若干 tick 里，**排序前两名的像素距离分不开**（失效条件 #1 的场景）⇒
   代码列出这几个 tick 作候选，模型用像素图/上下文选一个（`select_candidate`）或都不选（`reject_all`→二档）。
2. **无刻度可认但疑似该有**：边离所有 tick 都远（二档候选），但代码不敢独判它是真二档还是漏了刻度 ⇒
   送模型，`reject_all`=确认二档 / `request_reperception`=让 reading 重读。East `O01` 那种**明确落在整段正中**的，
   代码可直接判二档（`AutoAction`）不必惊动 —— 惊动只留给「代码分不清」的。

### D5-c 分流判据本身也零阈值（⭐ 关键，别把阈值从 D4 挤到这里）
「显著唯一/分不开」**不用毫米阈值**：用**排序 + 结构**判 —— 若像素读数落在某 tick 的**指认区间**内（该 tick 与
相邻 tick 的**中点划界**，纯几何、无签字常量）且该区间只含这一个 tick，即唯一 ⇒ 自动；若边落在两个 tick 的
**等距分界带**（中点两侧对称）⇒ 送模型。分界由 cum_mm 自身的中点决定，是**数据自定义的**，⛔ 不是外来阈值。
（这条是我最不确定的一处 —— 见末尾「最薄弱一处」。）

**省钱 + 少给模型乱动机会**：66/68 自动 ⇒ 模型每立面平均只看 0–1 条边；且模型只能在**代码给定的 tick 候选**里选，
⛔ 不能凭空移边（`candidate_id` 必是包成员，执行器 `UNKNOWN_RESPONSE_CANDIDATE` 挡）。

---

## D6 · 两步之间的冻结：第一步定下的事实进第二步后不许再被改（⭐ 类型层强制，不是纪律）

**要守的性质**：第一步「尺寸证据裁定」产出的 `OpeningEdgeTickClaimV1`（认领结果），进第二步（跨图配对 / B4）后，
第二步**只能选与取舍，⛔ 不能改认领的值或档位**。

**⛔ 不能靠「写一句纪律」**（B2 两轮 REWORK 的教训就在这：把类改私有、加 `_` 前缀**不是访问控制**，
公开 helper 会替调用方铸造裸载体 —— `2026-09-04d_B2_rework1_crossreview_gpt.md` §B-2）。

**类型层强制手段（三条叠加，均为结构，不是措辞）**：
1. **finalize + content_sha256 封印（复用现有机制，最省）**：认领结果打包成一个 `TickClaimBundleV1`，走
   `finalize_bundle` 同款（`evidence_contract.py:760`）算 `content_sha256`，第二步入口**先 `validate_*` 重算哈希**
   （同 `validate_evidence_bundle` 对 `content_sha256` 的 `BUNDLE_NOT_FINALIZED` / 重算，`:1224`）。
   第二步若改了任何认领值，哈希对不上、**入口即红**。这把「不许改」变成「改了就哈希失配」，是结构不是纪律。
2. **validated carrier 类型区分（吸取 B2 的返工门原话）**：第二步的装配入口**只接受**一个「已过冻结字节门」的
   **封印类型**（如 `SealedTickClaimsV1`，由 validator 产出、⛔ 无公开构造器），⛔ 不接受裸 `OpeningEdgeTickClaimV1` 列表。
   「未验证 claim」与「已验证 claim」**在类型上就是两个类**（B2 裁决要求的正是这条：
   `2026-09-04d` §B-2「消费类型上不可与未验证 claims 混淆的封印/validated carrier」）。
   ⇒ 第二步拿到的东西**在类型上就没有"改值再装配"这条路**：要改值得回到第一步重出、重封印、重算哈希。
3. **认领结果无坐标字段（D2-b 已保证）**：认领结果只带 `tick_ref`（指节点字节），坐标是代码从字节现算的。
   第二步**没有一个浮点坐标字段可改** —— 它能碰的只有「选哪条配对/弃哪条」，改不动「这条边认的是哪个刻度」。

⇒ 三条里 **#2 是承重的**（类型区分 validated/unvalidated），#1 是它的落地机制，#3 让"可改的面"本就不存在。
**这与 B2 现在还没做完的那件事是同一道题** ⇒ 见 D7 风险：应等 B2 的 validated-carrier 范式定下来后复用，⛔ 不各造一套。

---

## D7 · 风险清单：碰到的已落库哈希 / 已签字锁 / 在飞的单

| # | 风险面 | 具体是什么 | 与本方案的关系 |
|---|---|---|---|
| **R1 · T4-a（待审，⛔ 未合并）** | `EvidenceDebtV1` 加 `obligation` 字段（`2026-09-04b_T4a_execution.md`：`str\|None`，**riding inside `_sorted_bundle` dump** ⇒ 每个 finalize 过的 bundle `content_sha256` 变） | 本方案给 `ElevationOpeningClaimV1` 加 x 四字段，**同样进 `_sorted_bundle`**（`evidence_contract.py:743`）⇒ **每个立面 bundle 的 `content_sha256` 也变** | **两笔改动都翻 content_sha256，会叠加。** ⇒ 施工单必须**在 T4-a 合并后排**，一次重算基线，⛔ 别与 T4-a 并发各翻一次（重蹈 banner ⑥b「只翻搅一次哈希」的教训）|
| **R2 · B2（两轮 REWORK，⛔ 未合并）** | B2 是 z 的下游消费者（`FloorLevelClaimV1.z_m` → `WindowV3.z`），它的返工门 = **validated/unvalidated carrier 类型区分**（`multifloor.py:72-200`，`2026-09-04d` §B-2）| 本方案 D6 的强制手段 **正是同一个类型层范式**；且 x 认领后最终喂 `WindowV3.x`，与 B2 的 z 装配同源 | **强依赖**：D6 的封印/validated carrier **应复用 B2 定下的范式**，⛔ 不另造。B2 未收口前，本单的 D6 落地形态**悬着** ⇒ 施工单排在 B2 第三轮之后 |
| **R3 · B4（已合并主线 `5804ae4b`）** | `opening_synthesis.synthesize_openings` 从**裸 dict** 读 x（`:713/:887`），零容差配对（`:914`）| 本方案要把 B4 从「读 dict」改成「读认领结果的一档值」——**直接改 B4 的输入契约** | B4 已合并、有锁（`opening_synthesis` 测试、`grid_units` 精确成员）。改 B4 输入= **改已签字模块的入口**，属工程档、须派工换人审。⛔ 别原地加"x 也建 ref"就完事，要真让 B4 消费认领结果（D1 结论 #2）|
| **R4 · 立面 bundle 既有哈希/锁** | `evidence_contract` 的 `finalize_bundle`/`_sorted_bundle`/`_payload_row_source_ids`(`:1118`)、以及 `tarch_converter_reproducibility` 一类「同字节→同 bundle」锁 | x 四字段改 bundle 结构 ⇒ 触发这些逐字节可复现锁 | 施工单须**重生成受影响立面产物基线 + 重签**（改的是事实层结构，指南 §〇之二「改事实⇒重签」），并核 `_payload_row_source_ids` 的 elevation 分支同步加 x（否则 B-1 源闭合会漏 x 的 input_id）|
| **R5 · docstring 依赖边（§8.5）** | 改 `evidence_contract.py:544` docstring | docstring 目前不含仓库根路径前缀，改它**不新造依赖边** | 低风险，但施工时**别在 docstring 里写仓库根前缀的生产路径**（`affected_tests` 会建边，CLAUDE.md §8.5）|

**T4-a 与 B2 的改动面我读了原件**（验收 #6）：
- T4-a：`2026-09-04b_T4a_execution.md`（`obligation` 字段 + content_sha256 churn，T1–T5 停报因基点无 B4 注册表）。
- B2：`2026-09-04d_B2_rework1_crossreview_gpt.md`（`multifloor.py:72-200` 私有类未成 validated 类型；旧 `run_correction` 裸 z 面 `pipeline.py:1363-1364`〔B2 裁决记为 :1366-1367，我核到实为 :1363-1364〕未迁）。

---

## 验收 #4 · 方案里出现的每个数字，逐个说明是【声明值】还是【判断】

⭐ 通读全文，把所有数字列出（⛔ 方案**未引入任何新阈值**）：

| 数字 | 出处 | 声明值 / 判断 |
|---|---|---|
| `6930 / 8730 / 1800 / 6921.9 / 8751.2`（South O01）| D2-c、抽查 | **声明值**（cum_mm 是图纸画的链、`values_mm[2]=1800` 是画出的段；6921.9/8751.2 是产物里的像素读数）·非阈值 |
| `536.7 / 2164.6 / 6000 / 0.0`（East O01）| D2-c、抽查 | **声明值**（东立面 cum_mm 节点与产物像素读数）·非阈值 |
| `mm_per_px ≈ 13.6` | D1/D4/D5 | **声明值**（产物 `calibration.mm_per_px`，用于**说明**分辨率量级，⛔ 不进任何判据）|
| `0.1 mm` 栅格 / `10 mm` 出口颗粒度 / `1 mm` gt | D2/D4 | **声明值**（项目已签字的坐标颗粒度，指南 §〇 第 5 条 + `DECLARED_GRID_UNITS_PER_M`，⛔ 不是本单新设）|
| `chain_closure_mm = 0.0` | 抽查、D4-c#3 | **判断的输入**（是**精确相等**判据 `==0`，零阈值；不是"允许差 0.0"的容差）|
| `66 / 68 / 2` | D5、派工单 | **声明值**（派工方实测的条数，用于说明自动/惊动比例，⛔ 非判据阈值）|
| `1..96`（CodeToken 长度）| D3 | **声明值**（引用**既有** `decision_schema.py:131` 的 CodeToken 约束，⛔ 非本单新设）|
| `MIN_FLOOR_LEVELS=2` | （未在本方案用，仅 D1 邻近代码）| 不适用（本方案未引用）|

**结论**：方案里**没有任何"差多少毫米算够近"式的判断阈值**。所有毫米数要么是图纸/产物的**声明值**（拿来举例或说明），
要么进的是**精确相等 `==`** 判据（零阈值）。唯一带"判断"色彩的是 D5-c 的「用相邻 tick 中点划界」——
但它由 **cum_mm 自身**定义、无外来常量（见"最薄弱一处"）。

---

## 最薄弱一处

**D5-c 的自动/惊动分流判据。** D4 的等值判据我有把握是零阈值且必要成立；D6 的类型层封印有 B2 现成范式可依。
但**「一条边到底该自动认、还是该惊动模型」这个分流**，我给的是「像素读数落在相邻 tick 中点划出的区间里 ⇒ 唯一 ⇒ 自动」。
它**看起来**零阈值（中点由 cum_mm 自己算），但**它仍是一个几何判断**：当一条边恰好落在中点分界带附近时，
「自动 vs 惊动」的切换点是由中点这条线决定的 —— 而**中点是不是"指认唯一性"的正确判据**，我没有实测支撑
（派工方实测的是「距最近刻度 ≤34 mm」这类**带毫米**的统计，而我刻意不用它）。**风险**：若某条边的真实归属刻度
并非最近的那个（比如洞口边本就该对齐较远的轴线），中点判据会把它**自动**认错而不惊动模型，且 D4 判据看不见（失效条件 #1）。
⇒ **施工前应先做一个小实验**：拿 68 条边跑「中点分流」，看它把哪些边判成自动/惊动，与派工方那份「≤34 mm」名单对照，
确认中点判据不会把该送模型的边偷偷自动认掉。这是我唯一没有实测垫背、且直接影响"省钱 vs 认错"权衡的判断。

---

## 验收 #7 自证 · 零 `src/` 与 `tests/` 改动

```text
$ git diff --stat e9a45226..HEAD -- src tests
（空 —— src/ 与 tests/ 零改动）

$ git diff --stat e9a45226..HEAD
 .../execution/2026-09-04u_tick_claim_design.md | 281 +++++
 .../request/2026-09-04u_tick_claim_design.md   |  91 +++
 2 files changed  # 仅 AI_agent/ 下派工单（预置）+ 本交件
```

⭐ 全程只写 `AI_agent/` 下一份 md，分段提交。为核事实跑的命令原文均已贴入（§〇抽查、D1 各跳 grep、D7 读原件）。
