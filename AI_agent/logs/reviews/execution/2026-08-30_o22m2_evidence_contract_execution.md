# 执行档 · ②-2 模块 2：`correction/evidence_contract.py`（证据契约类型层）

- **日期**：2026-08-30 深夜 · **施工方**：GLM 家族（headless 席位）· **审**：GPT 家族（待派）
- **派工单**：
  [`../request/2026-08-30_o22m2_evidence_contract_dispatch.md`](../request/2026-08-30_o22m2_evidence_contract_dispatch.md)
  （含 §六–§八补充：四个任务项 + 九条验收，本文以补充后全文为准）
- **基线**：`8abd6e0`（开工时 HEAD）· **口径**：设计稿
  [`../verdict/2026-08-30_o22_evidence_contract_gpt_design.md`](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
  §3.2/§3.3/§4.1/§4.2/§4.3/§4.4 + N-1 覆盖（`counterface_state` 第三值）
- **交付物**：`src/agent/correction/evidence_contract.py`（新，1234 行）、
  `tests/test_o22m2_evidence_contract.py`（新，1309 行 / 28 条测试）。
  ⛔ 未提交（提交归主控）；⛔ 未动 `vector_contract.py` / `pipeline.py` / `judge/` / 任何既有测试。

---

## 〇、一句话交付

**类型层 + 硬不变量 1–8 校验器 + 逐条锁，零接线。** 三份真实产物各自构造出 bundle 并通过校验；
NF-4 前三种破坏从「今天 PASS」变为响亮失败；`gap_index` 越界（第四种）经判定**收进本单**
（纯引用完整性，无散文解析）；第五种（未被选中的悬空候选）按任务 4 留 pin 归模块 3/4。

一个架构决定先说清楚：**bundle 的构造工厂在测试文件里，⛔ 不在生产代码里**——
派工单禁令「不产 adapter」，而「从产物到 bundle 的翻译」正是模块 3 的活。因此：

- 构造期的拒绝（`SELECTED_PAIR_REFERENCES_UNKNOWN_FACE` 等）**不是承重锁**，只是早失败；
- **承重锁 = `validate_evidence_bundle`（生产代码）**。NF-4 每一族破坏都有
  「绕开构造器、直接打在校验器上」的独立证据（见验收 8 表），其中重复 id 一族
  由生产函数 `as_drawn_face_index` 承重（工厂与校验器共用它，构造期拒绝与校验期拒绝
  是**同一把牙**，不是两种意见）。

---

## 一、验收表逐条（命令 + 读数）

### 验收 1 · 类型词汇：4 种墙声明 + 3 种处置 + `counterface_state` 恰三值

```bash
python3 -m pytest tests/test_o22m2_evidence_contract.py::test_acceptance_1_type_vocabulary -q
```
**读数：1 passed。** 断言了四个 kind 的默认值、三种 status 的 Literal 值域、
`counterface_state` 恰为 `not_in_observations | observed_unclaimed | ink_present_unpromoted`
（N-1 第三值在），且**两值拼写的旧枚举值被类型拒绝**（喂
`"not_in_observations_ink_absent_checked"` ⇒ ValidationError）。

### 验收 2 · 三份真实产物各自构造出 bundle

```bash
python3 -m pytest tests/test_o22m2_evidence_contract.py -k "acceptance_2 or n1_the_sixth" -q
```
**读数：4 passed。** 三份产物（sm25_1f / sm25_2f / sm24_1f）各自：
`classify == as_drawn_plan` 前提成立 → 构造 → `validate_evidence_bundle` 绿。
构造完整性有数（**防工厂悄悄丢东西**）：

| 产物 | wall_claims | dispositions | opening_claims | debts |
|---|---|---|---|---|
| sm25_1f | 22（=22 pairs） | 49（=49 faces） | 85 | 3 |
| sm25_2f | 22（21 pairs + 1 single_face） | 46 | 87 | 3 |
| sm24_1f | 12（8 pairs + 4 solid_band） | 98 | 87 | 81（78 ambiguous + 3 channel） |

**L012**：按派工单要求**只证明第三态在类型上存在且可被构造**——
`test_n1_the_sixth_state_is_constructible_with_a_witness` 在 tiny 夹具上构造
`ink_present_unpromoted` + witness pointer → 校验**绿**；去 witness → 类型层红；
witness 指向不存在的节点 → 校验器 `COUNTERFACE_WITNESS_UNRESOLVED` 红。
真实产物 sm25_2f 里的 L012 今天落在**机械默认** `not_in_observations`
（工厂⛔ 不解析散文，验收 2 的断言钉住了这一点——从散文派生是模块 3 的活）。

### 验收 3 · 不变量 1–8 每条一把锁，先绿后红

```bash
python3 -m pytest tests/test_o22m2_evidence_contract.py -k "inv1 or inv2 or inv3 or inv4 or inv5 or inv6 or inv7 or inv8" -q
```
**读数：8 passed。** 每个测试**第一句就是绿前提**（未破坏夹具 `validate_evidence_bundle` 通过），
随后每个突变断言**精确 code**：

| 锁 | 破坏面 → 红 code |
|---|---|
| inv1 解引用唯一 | 改 ref 的 id ⇒ `OBSERVATION_ID_MISMATCH`；改 input_id ⇒ `UNKNOWN_INPUT_ID`；witness 悬空 ⇒ `WITNESS_POINTER_UNRESOLVED`；ref sha ≠ 冻结 sha ⇒ `REF_HASH_MISMATCH`；bytes 追加一字节 ⇒ `SOURCE_HASH_MISMATCH` |
| inv2 处置恰一次 | 悬空处置 ⇒ `DISPOSITION_REFERENCES_UNKNOWN_FACE`；漏处置 ⇒ `FACE_WITHOUT_DISPOSITION`；重复处置 ⇒ `DUPLICATE_DISPOSITION`；处置卖给未消费它的 claim ⇒ `FACE_SOLD_TO_TWO_CLAIMS`；claim 吃了 non_wall 面 ⇒ `FACE_CLAIMED_AND_DISPOSITIONED`；ambiguous 无 debt ⇒ `AMBIGUOUS_WITHOUT_EVIDENCE_DEBT` |
| inv3 配对一致性 | 自配 ⇒ `PAIR_SELF_REFERENTIAL`；不同轴 ⇒ `PAIR_AXES_DISAGREE`；hypothesis 节点与 claim refs 不符 ⇒ `PAIR_HYPOTHESIS_MISMATCH`；候选不符 ⇒ `SELECTED_PAIR_NOT_IN_CANDIDATE_GRAPH` |
| inv4 引用存在+witness | solid band 缺 runs_px witness ⇒ `SOLID_BAND_WITNESS_INCOMPLETE`；桶键悬空 ⇒ `POINTER_UNRESOLVED`；桶键 ≠ 被 claim 的面 ⇒ `BUCKET_KEY_IS_NOT_THE_CLAIMED_FACE` |
| inv5 语义槽唯一 | 两份源同 (plan, 9f) ⇒ `DUPLICATE_SEMANTIC_INPUT`；不同楼层共存 = 绿前提 |
| inv6 双契约 | hybrid（as-drawn + strokes）⇒ `AMBIGUOUS_CONTRACT_MATCH`（前提：classifier 报 AMBIGUOUS 被先断言） |
| inv7 声明即受检 | 破坏产物（`runs_px="0-100"`）⇒ `MALFORMED_DECLARED_CONTRACT`，⛔ 不回退 legacy |
| inv8 canonical+hash | 改内容不重算 hash ⇒ `CONTENT_HASH_MISMATCH`；乱序但 hash 对 ⇒ `WALL_CLAIMS_UNORDERED`（hash 锚在排序后形态，只有顺序门能点名）；未 finalize ⇒ `BUNDLE_NOT_FINALIZED`；claim 戴别人的 id ⇒ `CLAIM_ID_NOT_CANONICAL` |

**neuter 自证（摘门必红）**——四组「摘掉校验器一段 → 对应测试变红 → 还原 → 全绿」：

| 摘掉的门 | 对应测试 | 读数 |
|---|---|---|
| `OBSERVATION_ID_MISMATCH` 检查 | test_inv1 | **1 failed** |
| 处置域·悬空方向 | test_inv2 | **1 failed** |
| `gap_index` 范围检查 | test_nf4_4 | **1 failed** |
| 重复 id 检查 | test_nf4_3 | **1 failed** |
| （还原后整文件） | 全文件 | **28 passed** |

### 验收 4 · WallClaim 无复制几何值（机械断言）

```bash
python3 -m pytest tests/test_o22m2_evidence_contract.py::test_acceptance_4_no_geometry_value_fields_on_wall_claims -q
```
**读数：1 passed。** **禁名集从模块 1 的生产者类型反射**（`FaceLineV2/GapV2/PairCandidateV2/InkProfileV2`
中一切「数字或任意深度数字容器」字段——含 `list[PixelInterval]` 这种嵌套形态），
再递归遍历四种 claim 的**全部字段**（含嵌套 ref model）求交，交集必须为空。
测试先抽查禁名集本身含 `pos_m/edges_m/runs_m/runs_px/spacing_m/...`（防空集假绿）。
**`spacing_m` 连缓存审计都不带**——没有读者就没有「证明不读」的对象（派工单给了两条路，我选了不保留）。

### 验收 5 · 逐字节可复现（= 不变量 8 的字节面）

```bash
python3 -m pytest tests/test_o22m2_evidence_contract.py -k "acceptance_5" -q
```
**读数：4 passed。** 三份产物各跑两次构造：`content_sha256` 相同 **且**
`canonical_json_bytes(model_dump)` 逐字节相同；同 JSON 换缩进（bytes 变、结构不变）
重构造 ⇒ `content_sha256` **变**——哈希锚在 bytes 不在解析后的结构（重序列化的源
不能静默继承旧身份）。⚠️ 该 hash 是**包身份**，测试里没有任何地方拿它当子事实相等判据。

### 验收 6 · 本单零接线

```bash
git diff --stat -- src/agent/reading/vector_contract.py src/agent/pipeline.py   # → 空输出
git status --porcelain -- src/agent/reading/vector_contract.py src/agent/pipeline.py  # → 空输出
```
**读数：两命令均零输出（零 diff、未动）。** 行为面另有两条锁：
`test_the_type_layer_imports_no_pipeline`（干净子进程只 import 本模块 ⇒ `src.agent.pipeline`
不在 sys.modules，**读数 False**）；`test_as_drawn_is_still_not_consumed`
（as-drawn disposition 仍 `KNOWN_NOT_CONSUMED`——与模块 1 同型的翻牌 pin，接线日须有意翻）。

### 验收 7 · 跑测与文件清单

```bash
python3 -m pytest tests/test_o22m2_evidence_contract.py -n 4 -q
```
**读数：28 passed**，连跑四轮全绿（6.0s / 6.3s / 5.9s / 6.3s，无 flaky）。
**改/新建的全部文件**：
1. `src/agent/correction/evidence_contract.py`（新）
2. `tests/test_o22m2_evidence_contract.py`（新）
3. `AI_agent/logs/reviews/execution/2026-08-30_o22m2_evidence_contract_execution.md`（本档）

零修改既有文件 ⇒ 除 `affected_tests` 诚实门外不可能有既有锁受扰；诚实门方面
（⛔ 派工单禁跑全仓 AST 遍历，**未实测**、交主控在权威全量时验证）：
新生产模块被本测试文件 `import`，依赖边真实存在，不需要 allowlist 条目。

### 验收 8 · NF-4 五种破坏的交付前/交付后读数

每个「交付前」读数都在测试里**先跑再断言**（`_today_says_yes`：模块 1 类型 PASS +
classifier 判 `as_drawn_plan`）——不是转引复核方的表：

| # | 破坏 | 交付前（今天） | 交付后（本单） |
|---|---|---|---|
| 1 | `pairs[0].face_b → "L999"` | **PASS**（断言在案） | 构造期 `SELECTED_PAIR_REFERENCES_UNKNOWN_FACE`；**校验器层同族独立牙**：`PAIR_HYPOTHESIS_MISMATCH`（test_inv3c 构造出的 bundle 上直接触发） |
| 2 | `non_wall_face_lines["L999"]` | **PASS** | 构造期 `BUCKET_KEY_REFERENCES_UNKNOWN_FACE`；**校验器层**：`DISPOSITION_REFERENCES_UNKNOWN_FACE`（test_inv2a——用「ref 指向 opening 节点」的悬空处置绕开构造器直接触发） |
| 3 | 两条面线同 id | **PASS** | 生产函数 `as_drawn_face_index` ⇒ `DUPLICATE_OBSERVATION_ID`（工厂与校验器共用它） |
| 4 | `opening_candidates[0].gap_index = 99` | **PASS** | **收进本单**：构造成功（工厂机械信任 openings）→ 校验器 `OPENING_GAP_INDEX_OUT_OF_RANGE` 红。判定理由：下标越过一个 face 的 `gaps` 列表 = 纯悬空引用，机械可查、零散文解析——这正是 NF-4 的病族，且绿前提成立（三份产物今天 gap_index 全合法，已实测） |
| 5 | `pair_candidates[k].face_b → "L999"`（**未被选中**的候选） | **PASS** | **仍 PASS（pin，见验收 9）** |

### 验收 9 · 不在本单的破坏留 pin

**第五种（未被选中的悬空候选）**：
`test_nf4_5_unselected_dangling_candidate_passes_today_module3_4_pinned`
断言「今天能通过」（构造 + 校验全绿），测试名与 docstring 写明归属：
**模块 3**（`correction/evidence_adapters.py`——adapter 遍历候选图时必须解引用 `face_b`）
与**模块 4**（`correction/wall_compiler.py`——从 observations 重算候选图时必须拒不存在的面）。
理由（设计稿 §4.3）：bundle 只引用**被选中**的 pairs，候选图是复核辅助不是墙声明，
未被选中的悬空候选对这一层**不可见**。边界如实记录：同一腐败落在**被选中的**候选上时
是响亮的（验收 8 #1 / inv3d），pin 恰好只覆盖候选图的未选中部分。

---

## 二、我认为最薄弱的一处

**`channel_status` 的 `present` 与 wall_claims / opening_claims 之间没有任何闭合锁。**
「`walls: present` 但 `wall_claims` 为空」今天能全绿通过（inv6 / inv7 的夹具恰好就是
这么构造的——空 claims + present 通道，它们测的是别的门，顺带暴露了这个洞）。
设计稿 §3.3 立 `channel_status` 的动机是防「墙走新腿、窗悄悄仍从目录里随便找 strokes」，
但我只锁了「absent 必须带 debt」这一半；「present 必须真有对应载荷（或显式记
零载荷 debt）」这一半没有立门。可辩之处：载荷闭合的语义（什么算「walls 通道已供数」）
依赖 adapter 的构造职责，属模块 3；但**「present 却零 claims 零 debt」这个极端形态**
本层就能判，没判是我的留白。接线日（模块 3/7）若不补，它就是下一个
「`band_collapse` 无一假数却八门全绿」的形状。

次弱（记录在案）：不变量 6/7 的判定**委托** `classify_vector_json`，其中
`AMBIGUOUS_CONTRACT_MATCH` 靠 `"AMBIGUOUS" in decision.reason` 的**文案子串**区分——
vector_contract 改一句措辞，该 code 会退化成 `CONTRACT_MISMATCH`（仍响亮、不是静默，
但 code 错位，且那两个测试的精确断言会红）。

## 三、希望复核方重点打哪里

1. **打通道闭合**（上面第二节）：构造「`walls: present` + 空 claims + 无 debt」的 bundle，
   验证它真的能过——若复核方认为这该红，那就是一条本单应立未立的门，我接受。
2. **打构造器/校验器的缝隙**：我声称「NF-4 前三种都有绕开构造器、直接打在校验器上的独立牙」
   （#1=inv3c、#2=inv2a、#3=共用生产函数）。请复核方亲手把三者的「校验器层证据」
   与「构造层早失败」分开复跑——若哪一族只有构造期牙而校验器放行，我的承重叙述就是假的。
3. **打「夹具工厂不是 adapter」的边界**：工厂在测试文件里、生产代码零构造路径——
   这意味着**今天没有任何生产代码能产 bundle**（模块 3 之前的真空期）。请确认这与
   派工单「先 shadow 生成」的次序不冲突：我的理解是「shadow 生成」也归模块 3 的 adapter，
   本单只交类型与门。若复核方读出「模块 2 就该有 shadow 生成器」，那是范围误读，
   请以派工单 §一「唯一交付 = 类型层 + 校验 + 锁」为准——但值得被明说出来过一遍。

## 四、外围记录（只记不停，§四分层口径）

- `source_locator` 直接复用 `correction.window_sources` 的函数——其哈希 payload 里的
  schema 标签是 `window_source_locator_v1`（window 专用词）。一个定义优先于第二套
  provenance，故未改；跨体系同名 observation 共享 locator 语义上无害（同一冻结 bytes
  内的同一观测，身份本该同一）。
- `perception_source_ref` 设计稿列在共有字段但未定义语义；本单填「指向 `/hypotheses`（as-drawn）
  或整份文档（legacy）」的弱引用，只验证可解析。模块 3 应收紧。
- legacy 源的 face_disposition 语义设计稿未定义（§4.2 只说 as-drawn face lines）；
  本单实现为「允许携带、不做域约束」。模块 3 需要明确 legacy 处置策略。
- `view_manifest_sha256` 恒 `None`（今天无 manifest）；非 None 的绑定语义无锁，接线日补。
- 处置域检查对 legacy 源跳过（`key[0] in face_index` 守卫）——这是「域 = as-drawn」的
  实现面，不是疏漏，但值得模块 3 复核。
- 构造前提三件（selected pairs 全在候选图 / 五槽互斥 / 处置键皆真实面）在开工前
  对三份产物实测成立（执行档开头的第一条命令），故「三份构造不出 bundle」的停报
  条款未触发。

## 五、可复现命令

```bash
# 本单唯一跑测入口（连跑四轮）
python3 -m pytest tests/test_o22m2_evidence_contract.py -n 4 -q      # → 28 passed

# 零接线证明
git diff --stat -- src/agent/reading/vector_contract.py src/agent/pipeline.py   # 空
git status --porcelain -- src/agent/reading/vector_contract.py src/agent/pipeline.py  # 空

# F-152：两个新 .py 的字符串常量里不得有带仓库根前缀的生产路径
grep -n '"src/\|'"'"'src/\|`src/' src/agent/correction/evidence_contract.py \
  tests/test_o22m2_evidence_contract.py                                # → 零命中

# neuter 四组（备份→临时改→跑→还原；文件是本单新建的，未过 git）
cp src/agent/correction/evidence_contract.py /tmp/m2_backup.py
# （把目标 if 改成 if False: → 对应测试 1 failed → cp 还原 → 28 passed）
```

—— GLM 施工席位 · 2026-08-30 深夜
