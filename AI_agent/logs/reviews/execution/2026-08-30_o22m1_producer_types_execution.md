# 执行档 · ②-2 模块 1：as-drawn v2 的生产者自己的类型

- **日期**：2026-08-30 · **施工方**：Claude 家族（**重新实现**，⛔ 未复用孤儿件任何一段）
- **派工单**：[`request/2026-08-30_o22m1_as_drawn_producer_types_dispatch.md`](../request/2026-08-30_o22m1_as_drawn_producer_types_dispatch.md)
- **开工时 HEAD**：`0cd2858` · **状态**：✅ 完工待审（⛔ 未 `git add`、未 `git commit`，提交归主控）

---

## 〇、先说三句话

1. **本单的病是「探测器只看键名，桶里装什么没人看」**。改完后，对真实产物做的 **15 种元素级破坏
   全部**从「被认成合法产物」翻成**响亮 unknown**；另有**第 16 种（空骨架）是故意保留绿的边界**，
   单独一条测试钉住（见 §三.1）。
2. **产物逐字节没变**：三份真实产物用**真实 `build()` 重跑**，sha256 与改动前、与仓库里跟踪的那份**三方全等**。
3. ⛔ **我没有改 `tests/test_f97_vector_contract.py` 一个字节**（孤儿件改了它 45 行）。
   那 79 条 F-97 锁**原样全绿**。

---

## 一、承重前提自检（派工单 §一，逐条实测）

| # | 前提 | 我的复核 | 结论 |
|---|---|---|---|
| 1 | `assemble()` 返回裸 dict | [`as_drawn_v2.py:566`](../../../../src/agent/reading/as_drawn/as_drawn_v2.py#L566) 签名 `-> dict`，函数体是一个 `return {…}` 字面量 | ✅ 成立 |
| 1' | 全仓 `class \w*(Hypothes|Percept)\w*` 零命中 | ⚠️ **今天已不是零**：`src/agent/judge/answer_compiler.py:128 class BoundaryPairingHypothesisV1`（**GPT 席位 ②-1d 的在途/已交件**，与 reading 侧无关），另一处在孤儿件目录里。**as-drawn 生产者侧仍是零命中** | ✅ 前提的实质成立（只记不停） |
| 2 | detector 只做 `_is_declared + _has_keys` | 改动前 `vector_contract.py:213-219` 逐字就是那两句；**并且我实测了它的后果**：对 `out/sm25_2f_v2.json` 做 15 种元素级破坏，改动前**全部**返回 `as_drawn_plan / KNOWN_NOT_CONSUMED` | ✅ 成立，且**有量** |
| 3 | `validator/checks/as_drawn.py` 11 道门没接进 `run_pipeline`/gate① | 该文件 `grep -c "def check_"` = 11；`scripts/tool_scripts/affected_tests_rules.yaml:44-50` 的 `uncovered_allowlist` 逐字写着「does not wire it into run_pipeline/gate①」 | ✅ 成立 |

⭐ 另外**实测了一条派工单没写、但我需要它才敢动 detector 的事实**：
**全仓 `as_drawn_plan_v2` 的 JSON 只存在于 `AI_agent/logs/experiments/` 下**
（`grep -rl "as_drawn_plan_v2" --include=*.json .` 排除该目录后为空；任何 `0_reading/` 里都没有）
⇒ 收紧 detector **对生产运行的产物没有任何影响面**。

---

## 二、做了什么

### R1 · 新建 [`src/agent/reading/as_drawn/schema.py`](../../../../src/agent/reading/as_drawn/schema.py)（373 行）

生产者自己的 Pydantic 类型，覆盖**墙 + 洞口两族**：
`face_lines`（含 `gaps` / `ink_by_family` 的完整下钻）· `pairs` · `pair_candidates` ·
四个处置桶 · `opening_candidates` · `opening_types`。

**四个设计决定，每个都有理由**：

1. **`SCHEMA` 挪到 `schema.py` 定义、`as_drawn_v2` 再导出**。
   ⛔ 不是重构癖：`AsDrawnPlanV2` 要校验 `schema` 字段的值，而 `vector_contract` 又要
   `from …as_drawn_v2 import SCHEMA`（F-97 有测试逐字断言这行 import）。
   如果两边各写一遍字面量，就是**同一个值的第二处定义**。
   `as_drawn_v2.py` 里现在**没有** `"as_drawn_plan_v2"` 这个字面量（新测试断言了这一点）。
   同理 `axis` 的 `row|col` 直接 `from _plan_ink import Axis`，⛔ 不重抄。

2. **⭐ 顶层 `extra="allow"`，但下面每一层 `extra="forbid"` + `strict=True`。**
   顶层为什么必须开：F-97 的 `test_r5_complete_declaration_plus_legacy_is_still_ambiguous` 要求
   「声明了本契约 + 满足键集 + 又像 legacy view」的混合体判 **AMBIGUOUS**。
   那个混合体带一个多余的 `strokes` 键 —— **如果顶层 forbid，它就只剩 legacy 这一个匹配 ⇒ 变成
   `CONSUME` ⇒ 被逐字贴进 correction 提示词 ⇒ 这就是 F-97 本体重开**。
   ⇒ 收紧顶层不是「更严」，是**制造回归**。这条我写进了 `AsDrawnPlanV2` 的 docstring 并**单测钉住**。

3. **`strict=True` 是量出来的，不是默认加的。**
   先按 pydantic 默认（lax）写完，跑破坏矩阵发现 **`spacing_m` 被换成字符串 `"0.24"` 仍然全绿**
   （lax 会把它强转回 float）。这正是[[gate-measures-right-but-carrier-gets-swapped]]的形状：
   门量得准，但**载体被换掉了**。开 strict 后该条翻红。
   **strict 在真实数据上的代价 = 0**：三份真实产物 + 全部诚实的历史变体在 lax/strict 下判定**完全一致**；
   只有伪造/变异产物改变判定，且**每一条都是往「拒绝」的方向改**。

4. **区间类型 `Interval` / `PixelInterval` 钉死长度 2**（`span_m` / `edges_m` / `support_cols_px` /
   `runs_px[i]` / `runs_m[i]`）。实测三份产物**全部**为 2。
   ⚠️ 只钉**长度**：`hi > lo`、`ink_coverage_per_run` 与 `runs_px` 等长这类**数与数之间的关系**
   ⛔ 不进类型，那是 `validator/checks/as_drawn.py` 那 11 道门的活（写进 docstring 了）。

**接线**：`assemble` 的 `return {…}` 改成 `return validate_as_drawn_plan({…})`。
⭐ `validate_as_drawn_plan` **返回同一个对象**，⛔ 永不 `model_dump()` ——
dump 往返会重排键、强转数值、丢掉顶层故意放行的 extra，**那是一边声称检查一边悄悄改写产物**。
逐字节不变因此是**结构上真**，不是「测了一下没变」。

### R2 · [`vector_contract.py`](../../../../src/agent/reading/vector_contract.py) 换判别方式（+41/-3）

`CONTRACT_AS_DRAWN_PLAN` 的 lambda 换成具名 `_detect_as_drawn_plan`，形状**照抄同文件里
`_detect_stage_check_report` 的既有模式**（显式键 + 生产者的类型）：

```
_is_declared(...)  →  _has_keys(...)  →  AsDrawnPlanV2.model_validate(raw)
```

- `Disposition` **仍是 `KNOWN_NOT_CONSUMED`**（⛔ 本单不接 adapter，那是模块 3）。
- `describe` 补上「AND parses as reading/as_drawn/schema.py:AsDrawnPlanV2」。
- ⛔ **没有碰**重命名 / ledger 重排 / `classify_vector_json` 的任何一行。

---

## 三、验收逐条自查（派工单 §三，7 条）

### 验收 1 ⭐⭐⭐ 有牙 —— ✅，且**premise 是被断言的，不是被记住的**

测试文件里有一个 `_detector_before_this_dispatch(raw)`，**逐字复述了改动前那条规则**。
15 个破坏用例每一个都先断言 **「旧规则说 yes」**，再断言 **「新规则说 unknown」**。
⇒ 这不是「现在红了」，是「**同一份输入，改动前绿、改动后红**」，而且这个对比**跑在 CI 里**，
不是我在执行档里报的一个数（[[regression-case-must-prove-its-own-premise]]）。

15 个用例：桶值变 dict / 桶值变数字 / 桶变 list / **凭空长出一个兄弟桶** /
面线丢 `id` / `runs_px` 变字符串 / **图像轴被换成世界轴** / pair 丢 `face_b` /
spacing 以文本到达 / `pairs` 变 dict / 洞口候选丢 `span_m` / `opening_types` 值变 dict /
墨迹剖面丢 `span_ratio` / **区间装了三个数** / **区间只装了一个数**。

⚠️ **故意留的那一格（我主动交代，不等审阅方翻）**：
`{"schema": …, "observations": {}, "declarations": {}, "hypotheses": {}}` 这个**空骨架仍然被认**。
理由不是漏了，是 **F-97 的 R5 锁依赖它**（三处：`test_b3_as_drawn_plan_is_known_but_not_consumed`、
`test_b3_as_drawn_raises_and_says_known_not_unknown`、`_COMPLETE_DECLARATIONS[0]`）。
⇒ 本版的牙**长在「元素结构」上，⛔ 不长在「空不空」上**。
这条边界我写进了 `AsDrawnPlanV2` docstring **并单独写了一条测试把它钉住**
（`test_the_declared_skeleton_is_still_recognised`），**⛔ 不让它以后变成一个没人记得的默认**。
→ 见 §六「最薄弱的一处」。

### 验收 2 ⭐⭐ 产物逐字节不变 —— ✅（**用真实 `build()` 重跑，不是读文件**）

```
              改动前 build()                                              改动后 build()      跟踪件
sm25_1f  2a5631494479b65d27328f5891e8016df632e0b5783fbae1acc86f4ce9936c57  同  同   438211 B
sm25_2f  bdf9a6fbd0e6ac6694575b748ca3c34f124ac7b4f11551e2ea816340e774d9e2  同  同   428774 B
sm24_1f  dd6115789de2cccaa31616caa4ff39f994ff0494a8da7b8357afbc136e0718c8  同  同   563981 B
```

三方全等（改动前重跑 / 改动后重跑 / 仓库里跟踪的 `out/*_v2.json`）。
⭐ 顺带证明了**跟踪件本身今天仍可从 `build()` 逐字节复现** —— 这是「逐字节不变」这句话能成立的前提，
⛔ 否则我比的就只是两次读同一个文件。

配置：`tools/cfg_1f_full.json` / `cfg_2f_full.json` / `cfg_sm24.json`，
走 `src.agent.reading.as_drawn.as_drawn_v2.build()` + `dump()`。

### 验收 3 ⭐ 真的经过它（**摘得动**）—— ✅

**neuter 实验**（`/tmp` 之外的本地临时摘，跑完立即还原）：
把 `assemble` 里的 `return validate_as_drawn_plan({…})` 改回 `return ({…})`，
`tests/test_o22m1_as_drawn_producer_types.py` 立刻 **1 failed / 52 passed**，
红的正是 `test_assemble_refuses_to_emit_a_malformed_product`，**⛔ 全仓没有第二条测试红**。

还原后 `diff` 与备份**为空**，`git diff --numstat` = `18 4 src/agent/reading/as_drawn/as_drawn_v2.py`
（与摘之前一致）。⛔ **交件 diff 里没有任何 neuter 痕迹。**

⭐ 这条 neuter 测试用的是**真的 `assemble`**，只是喂最小参数
（[[lock-must-exercise-real-entry-point]]）：`percept` 里放一个**值是 dict 而不是 prose** 的桶，
产物就必须**出不去生产者**。

### 验收 4 「五桶」到底几个 —— ✅ **判定：四个。⛔ 没凑数。**

复核方写的「五桶」没有列举。我数了三遍，答案是 **四**：

1. [`as_drawn_v2.select_pairs:515-533`](../../../../src/agent/reading/as_drawn/as_drawn_v2.py#L515)
   —— 完备性不变式的**生产者本人**，只读四个声明桶：
   `non_wall_face_lines` / `unpaired_wall_faces` / `solid_band_walls` / `ambiguous_face_lines`。
2. [`src/validator/checks/as_drawn.py:576-583`](../../../../src/validator/checks/as_drawn.py#L576) 点名同样四个，没有第五个。
3. 三份真实产物的 `hypotheses` 下**恰好**这四个键是 `dict[face_id, str]`。

**第五格是真的，但它不是桶**：一条面线也可以因为「是某个选中 `pairs` 的一半」而被交代掉。
`select_pairs` 把它与四个桶**并起来**算 `accounted`；
[`judge/as_drawn/reading_grade.py:121-124`](../../../../src/agent/judge/as_drawn/reading_grade.py#L121)
拆 claimed/abstained 时也是同一个并集。
⇒ **处置空间 = 5 格，其中 4 个是同形的桶，第 5 个是 `pairs`**；
而复核方自己的裁剪清单里 **`pairs` 已经单列**了 ⇒ 再算一次就是**重复计数**。
⛔ 没有第五个 dict，也没有为了凑到五而发明一个。

判定与依据写在 `schema.py` 模块 docstring 的专章，并有两条测试钉住：
- `test_there_are_exactly_four_buckets_and_pairs_is_not_one_of_them`
  （`len == 4`；`"pairs" not in`；与模型里**类型为 `dict[str,str]` 的字段集合**逐一相等；与三份真实产物相等）
- `test_the_fifth_slot_is_pairs_measured_on_the_real_products`
  —— **在真实数据上**验「四桶并 pairs 覆盖全部面线」，并且**断言四个桶单独覆盖不全**
  （⛔ 否则这份产物根本证明不了「`pairs` 是必需的一格」，那条测试就是恒真的）。

### 验收 5 缓做通道显式声明 + 能列清单 —— ✅

`DEFERRED_CHANNELS` 是一个 13 项的**点分路径常量**，⛔ 不是散文：

```
image · image_label · observations.calibration · observations.ink_palette ·
observations.components_by_family · observations.dimension_witnesses · declarations ·
hypotheses.family_roles · hypotheses.opening_candidates_basis ·
hypotheses.pair_candidates_basis · hypotheses.perception_source · hypotheses.note · ledger
```

每一项都是模型上**具名的字段**（typed `Any`，`description` 以 `"deferred"` 开头），
⛔ 不是被 `extra="allow"` 吞掉的。三条测试锁：
- `test_deferred_roster_matches_the_model_exactly` —— 名单与模型**互为充要**，⛔ 不能单边漂移；
- `test_the_in_scope_families_are_not_on_the_deferred_roster` —— 在编范围的 9 个字段**不许**溜进名单；
- `test_every_in_scope_node_forbids_unknown_keys` —— 下层节点必须 `forbid`+`strict`，顶层必须 `allow`。

⚠️ **一条我不敢写成「已完成」的**：派工单/裁决书说 `ledger`/`roles` 要**登记 plan.md 缓做**。
我查了 `AI_agent/plan.md`，**今天没有这条登记**（有的是 96 行「②-2 模块 7 收窄工程不做」，不是这条）。
⇒ 我**没有替主控去写 plan.md**（那是管理文档），而是把这个事实**逐字写进了 `DEFERRED_CHANNELS` 的
docstring**（「as of this commit that plan.md entry is not written yet」）。
**请主控补登记**，⛔ 别让「登记过了」变成一句没人指得到出处的话。

### 验收 6 `Disposition` 仍是 `KNOWN_NOT_CONSUMED` —— ✅

`test_as_drawn_is_still_known_but_not_consumed`（查 spec + 查真实产物的分类结果）
\+ `test_no_new_contract_became_consumable`（**全表**只有 legacy 一个 `CONSUME`）。

### 验收 7 受影响子集绿 + `git status` 干净 —— ✅（含一条**必须说明**的偏差）

⚠️ **「开工时 `git status` 干净」这条与本单 §〇 自相矛盾**：§〇 二次发单已改写成
「`git status` 现在【不干净】是正常的，⛔ 别读成异常」，而 §三 验收 7 与 §五 触发器 1
是**一次发单的旧文，没跟着改**。派工单原文写了「§四 的预裁别停下上报」，
我按 §〇 的新口径执行，**只记不停**。
（⭐ 这正是记忆里那条「写完派工单把**验收项**逐条与**本单禁令/任务项**对撞」能一次拦下的形状 ——
本单的 §〇 禁令与验收 7 直接对撞。）

**实况**：开工时 `git status` 只有那份派工单自己被改（就是 §〇 的改写，**不是我改的**）。
GPT 席位的在途改动在我开工前已经进了提交（HEAD 已到 `0cd2858`）。
**收工时** `git status` = §六 那 5 条 + 那份派工单，**没有一条属于别人**。

**跑测**（⛔ 全程 `-n 4`，⛔ 没跑 `-n auto`、没跑 `affected_tests.py`、没跑全量）：

| 轮 | 范围 | 结果 |
|---|---|---|
| ×3 | 受影响子集 18 个文件 | **479 passed**（三次一字不差） |
| ×1 | `test_f97_vector_contract.py` 单独 | **79 passed**（⛔ 我一个字节都没改这个文件） |
| ×1 | neuter 后 | 1 failed / 52 passed（只红该红的那条） |

受影响子集怎么定的（⛔ 没用 AST 工具，手工反查 import 面）：
我改的三个 src 文件 → 直接 importer = `pipeline.py`（`classify_vector_dir`）、
`validator/checks/as_drawn.py`、`scripts/tool_scripts/reading_toolbox.py` →
再取全部 `grep -l "run_correction|discover_vector_files|UnconsumableVectorFile|classify_vector|reading_vector_contract_ledger"`
的测试文件 + 全部 `grep -l as_drawn` 的测试文件，共 18 个。

---

## 四、孤儿件的三处可疑 —— 我自己的裁定（⛔ 未复用任何一段）

我把 `logs/experiments/2026-08-30_o22m1_orphan_wip/` 当笔记翻过一遍，然后**合上从派工单重写**。
主控点名的三处，我的独立判定：

| # | 主控点名 | 我的裁定 |
|---|---|---|
| ① | 它改写了 `tests/test_f97_vector_contract.py` 45 行 | ⛔ **不该改，而且不需要改**。我把类型写成「三层必填、每层成员各自有默认」之后，F-97 那三处空骨架夹具**原样全绿**，79 条一条没动。⭐ 我推测（**只是推测**）它撞的是同一堵墙：若把 `face_lines` 写成必填、或顶层 `extra="forbid"`，那三条就会红 —— 而**正确的反应是把类型写对，不是把锁改松**。⚠️ 尤其顶层 forbid 会让混合体从 AMBIGUOUS 掉成 **CONSUME**，那是 F-97 本体重开。 |
| ② | `vector_contract.py` `+85/-6` 超出 R2 | 我的是 **`+41/-3`**，其中 34 行是 docstring。实体改动 = 新增一个具名 detector（照抄同文件既有 `_detect_stage_check_report` 的形状）+ 换掉 lambda + 改 `describe`。`Disposition`、`classify_vector_json`、ledger、命名**一行未动**。 |
| ③ | `schema.py` 430 行，「五桶」裁定无人核过 | 我的 **373 行**（其中约 40% 是 docstring 与理由）。**五桶裁定做了，判「四个」，依据三条，并写了两条测试**（见验收 4）。⛔ 我没读它的 `schema.py` 去比对字段——**重写就是重写**。 |

⚠️ 我确实**读过**那份孤儿件的 README 与 `files/` 里两个文件的开头
（为了理解主控点名的三处到底指什么）。**⛔ 没有复制任何一段代码，也没有拿它当任何断言的依据。**
一处巧合值得主动交代：孤儿件里也有 `class HypothesesV2`，我的也叫 `HypothesesV2` ——
这是「产物里的键叫 `hypotheses`」这一个事实决定的，⛔ 不是抄的。

---

## 五、N-1（`counterface_state` 第六态 `ink_present_unpromoted`）怎么处理的

**先说结论：本版把它当作【已知缺口】显式钉住，⛔ 没有为它发明字段。**

- 实证在真实产物里：`sm25_2f` `hypotheses.unpaired_wall_faces.L012` 的值是一句**散文**，
  原文含「The ink is there — column 655 carries 170 px over rows 1080-1249 — and the reader dropped it」。
  ⇒ 对面墨迹**在**、只是没被提升成面线。这就是第六态。
- **为什么不加结构槽**：
  ① 复核方裁决书 §4.1 逐字要求「先**忠实**接住当前 `dict[face_id, reason_text]`，
     ⛔ 不要趁建模偷偷重写历史产物」，而验收 2 又要求逐字节不变；
  ② 一个**零真实实例**的 union 分支 = **没被行使过的能力** = 缺陷躺着的地方
     （[[feed-the-answer-in-to-test-the-code-alone]]）；
  ③ `counterface_state` 是**模块 2 `EvidenceContract`** 的字段，不是生产者产物的字段。
- **那我做了什么**：`test_n1_the_sixth_counterface_state_exists_only_as_prose_today`
  —— 钉住 L012 这个实例（断言它存在、是 `str`、含那两个关键短语），
  **并断言把它换成结构化 dict 今天会被类型拒绝**。
  ⇒ 哪天生产者真开始在那里出结构，**类型必须被有意地改**，⛔ 不会被静默吸收。

⚠️ **交给模块 2 的一句话**：`unpaired_wall_faces` 的语义载体今天**只有散文**。
模块 2 若要判 `not_in_observations` vs `observed_unclaimed` vs `ink_present_unpromoted`，
**⛔ 不能解析这句散文**（设计稿自己禁了）——**要么让 reading 侧新出一个结构字段（那要改本模块的类型），
要么按 N-1 修法把 `not_in_observations` 定义成「像素通道亦无墨」的显式检查**。
两条路都不在本单。

---

## 六、本单改动的**全部路径**（⛔ 主控只 `git add` 这 5 条）

```
M  src/agent/reading/as_drawn/as_drawn_v2.py          +18 / -4
M  src/agent/reading/vector_contract.py               +41 / -3
A  src/agent/reading/as_drawn/schema.py               373 行（新文件）
A  tests/test_o22m1_as_drawn_producer_types.py        477 行（新文件）
A  AI_agent/logs/reviews/execution/2026-08-30_o22m1_producer_types_execution.md   （本文件）
```

⚠️ `git status` 里还有一条 `M AI_agent/logs/reviews/request/2026-08-30_o22m1_…_dispatch.md`（+26/-1）——
**那是派工方自己的 §〇 二次发单改写，⛔ 不是我改的**，请主控自行决定是否一并提交。

⛔ **我没有 `git add`、没有 `git commit`、没有 `git checkout --` 任何文件、没有 `pip install -e .`。**

---

## 七、我认为**最薄弱的一处** + 希望复核方重点打哪里

### 最薄弱的一处：**空产物仍然被认成合法契约**

`{"schema": "as_drawn_plan_v2", "observations": {}, "declarations": {}, "hypotheses": {}}`
在改动前后**都是绿的**。一份「一条面线都没量到、一个桶都没有」的产物，
今天仍然被 `classify_vector_json` 认成合法的 `as_drawn_plan`。

**我知道它是洞，也知道为什么没堵**：堵它（把 `face_lines` 设为必填）会让 F-97 的三处夹具变红,
而修那三处夹具就是**改一道已经承重的锁**，正是孤儿件被点名的那件事。
⇒ 我选择**不改别人的锁**，把边界写死在 docstring + 一条测试里。

⚠️ **但我要按记忆里那条规矩自我举报**：[[gate-measures-right-but-carrier-gets-swapped]]说
「反查『哪个方向没有锁』并问为什么 —— **答案若是「加了就会红」，那是缺陷本身在挡锁**」。
我这里的答案**恰恰就是「加了就会红」**。
我的辩解是「红的是别人的夹具、不是我的产物」，**但这句辩解需要第二个人来判，⛔ 不该由我自己拍**。

⇒ **请复核方优先打这一处**：
「让 F-97 的三处骨架夹具带上一条最小但真实的 `face_lines`，然后把 `face_lines` 设为必填」——
这条路到底通不通？如果通，本单就该顺手把这个洞堵上；如果不通，请说清是什么挡住的。

### 另外三处希望被打的地方

1. **`extra="allow"` 顶层这个决定**。我给的理由是「forbid 会把 AMBIGUOUS 变成 CONSUME」，
   我也写了测试钉住这个行为。但这等于**承认顶层任何多余的键都进不了任何门**。
   请打：**有没有第三条路**（比如 detector 先做类型校验、再单独判 legacy 冲突），
   能同时拿到「顶层严」和「混合体仍 AMBIGUOUS」？

2. **`strict=True` 的代价我只在【现有】数据上量过**。三份真实产物 + 一堆历史变体全过。
   但「未来某个合法产物会不会被 strict 挡住」我**证明不了**。
   请打：`assemble` 拿到的活对象里若某天混进 numpy 标量，strict 会直接红 ——
   我认为这是**好事**（`_plan_ink.dump` 的 `default=lambda o: o.__dict__` 会把 numpy 标量写成垃圾），
   但这是我一个人的判断。

3. **`test_the_fifth_slot_is_pairs_measured_on_the_real_products` 的分辨力**。
   我加了「断言四桶单独覆盖不全」来防它恒真，但它依赖 `pairs_status == "SELECTED"`。
   三份产物今天都是 SELECTED。请打：**这条测试在什么产物上会红**？如果答案是「没有」，它就没牙。
