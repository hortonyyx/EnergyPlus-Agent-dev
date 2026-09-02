# 派工单 **v2** · **接线（模块 7 上半）**：把新链接进 `run_correction` 的真实入口 + 模型那一拍

> ⛔ **v1 作废**（[原单](2026-09-01i_wiring_module7_dispatch.md)）—— 它写「A 项只是**一行注册**」，
> 而 `Disposition` 枚举里**根本没有一个值能表达「交给 adapter」**。
> GLM 席位 **A 层停报，停得对** ⇒ **题错 #70（累计 70/70）**。
> **裁定书**：[`2026-09-02a_wiring_module7_stop_report_ruling.md`](../verdict/2026-09-02a_wiring_module7_stop_report_ruling.md)
> —— 席位五条断言我**逐条独立复核，全部成立、零夸大**；⭐ **本单是按它量出来的东西重写的**。
> ⭐ **v2 累计式自包含**：⛔ 不要回头读 v1，本单就是全文。

- **日期**：2026-09-01 · **派工方**：orchestrator · **施工方**：**GLM 家族施工席** · **审**：**GPT 家族**（⛔ 不得 GLM）
- **基线**：**`1303e8a`**（`08.23_AsDrawnReading`）
- **权威全量读数**：**`3632 passed / 13 xfailed / 0 failed`**
  ⚠️ **该读数测于 `0fda81f`，不是基线本身**。`git diff --numstat 0fda81f..HEAD` = **只有两份 md**
  （`AI_agent/CLAUDE.md` 9/8 · `AI_agent/plan.md` 19/0）⇒ 基线上这个读数仍成立。
  ⛔ **本单不写死任何会漂的哈希**（`.pth` 哈希、`content_sha256` 一律不作判据 —— 题错 #69 就是这么来的）。
- **口径来源**：用户 2026-09-01 开工拍板 —— **两条并行 · 接线先只求「跑得通」，一条 case 端到端**。
- **设计权威**：已过审设计稿
  [`2026-08-30_o22_evidence_contract_gpt_design.md`](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
  §5.4 / §6.1 / §6.2 / §6.3 / §9.1 第 7 步。⛔ 与本单冲突处**停下上报**，不要自行取舍。

---

## 〇、⭐⭐⭐ 派工方今天自己量过的东西（⛔ 这些是本单的承重前提，不是转引）

探针全档 → [`logs/experiments/2026-09-01i_wiring_seam_probe/`](../../experiments/2026-09-01i_wiring_seam_probe/README.md)

| 我量的 | 读数 | 怎么量的 |
|---|---|---|
| 新链在生产侧有没有消费者 | **零** | `grep -rn 'evidence_contract\|evidence_adapters\|wall_compiler\|decision_schema\|decision_executor' --include=*.py src/ scripts/` ⇒ 空 |
| `pipeline.py` 今天怎么喂 correction | **把识图 JSON 原文贴进提示词** | `src/agent/pipeline.py:452` 一带 |
| ①→②→③ 在**真实 sm25 新格式产物**上通不通 | ✅ **通** | `adapt_as_drawn_plan` → 22 条 `PairedFacesWallClaimV1` + 49 条 face disposition；`compile_wall_ir` → 22 堵墙 / 22 条 `thickness_resolution` 待裁决 / `completion=degraded` / 3 条残余债；`build_decision_packet` → 出包成功、134 条 entity→source |
| ①→②→③ 在**真实 sm25 旧格式产物**上通不通 | ✅ 也通，但**更差** | `adapt_legacy_reading_view` → 22 条 `legacy_wall_trace`；待裁决全是 `legacy_basis_unknown`（连基准都不知道），refs 只有 44 |
| 新格式产物到底有没有 | ⭐ **有，且含 sm25 两层** | `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/` 下 **22 份**通过 `AsDrawnPlanV2` 校验，含 `sm25_1f_v2.json` / `sm25_2f_v2.json` / `sm24_1f_v2.json` |
| `case_tests/` 下的识图产物是什么格式 | **368 份全是旧格式**（带 `strokes`） | `find case_tests -name '*_view.json' \| wc -l` + 逐份 top-keys |
| as-drawn 合同现在的 disposition | `KNOWN_NOT_CONSUMED` | `src/agent/reading/vector_contract.py` 的 `CONTRACTS` 元组，`CONTRACT_AS_DRAWN_PLAN` 那一行；该函数 docstring 自己写着 *"Pointing this contract at a correction adapter is a later module's work"* —— **就是本单** |

⚠️ **派工方自己的一处更正**（写在这里是为了让你不要继承它）：我最初据指南 §十之二 写下
「新格式产物全仓只有 sm24 一层」，**是错的** —— 那是拿 `as_drawn_plan_v0` 的文件当成了 v2。
逐份 `AsDrawnPlanV2.model_validate` 之后才是上表那一行。⇒ **本单一切以上表为准。**

---

## 一、要做什么（四项，⛔ 只有这四项）

### A. 注册：as-drawn 合同指向新 adapter（⭐ **v2 改写：这【不是】一行**）

**你上一轮量出来的、我复核成立的事实**（⛔ 不必重量，但开工前请自己再确认一眼）：
`Disposition` 只有 `CONSUME` / `KNOWN_NOT_CONSUMED` / `EXCLUDE`；`CONSUME` 的 docstring 自己写着
*"Pasted into the correction prompt"* ⇒ 落 `CONSUME` 会把新格式文件**整份贴进旧 prompt**，语义正好反。
`_classify_rows`（`vector_contract.py:486-516`）是**四分支穷举**。
设计稿目标态（`…_gpt_design.md:476`，我回原件核过逐字属实）：
`CONSUME / KNOWN_NOT_CONSUMED / EXCLUDE` **收窄为** `ADAPT(adapter_id) / KNOWN_NOT_ADAPTED / EXCLUDE`。

⇒ **范围裁定（派工方定，⛔ 不必再上报）**：

| **本单必做** | **本单仍然不做** |
|---|---|
| **新增** `ADAPT` 枚举值 + `_classify_rows` **第五分支** | 把 `CONSUME` **重命名**成 `ADAPT` |
| `ADAPT` 的台账行为：⛔ 不进 `consumed` · ⛔ 不当 offender · ✅ **在 ledger 里被点名** | 把 `KNOWN_NOT_CONSUMED` 重命名成 `KNOWN_NOT_ADAPTED` |
| `CONTRACT_AS_DRAWN_PLAN` 那一行改指 `ADAPT` | 目录 ledger **重排** |

**⭐ 为什么「四值过渡态」不是烂摊子**（⛔ 别自己去收窄）：目标三值是靠**收窄**到达的 ——
**`CONSUME` 的存活期恰好等于「旧的贴 JSON 路」的存活期，两者在【拆旧腿单】里一起死**。
我已把「拆旧腿时同时删 `CONSUME`」登记进 plan.md，⛔ 不归你。

**⛔ 翻 pin 锁的硬要求**：你上一轮点名的 6 把锁（`test_as_drawn_is_still_known_but_not_consumed` /
`test_no_new_contract_became_consumable` / 两处同名 `test_as_drawn_is_still_not_consumed` /
`test_f97_vector_contract.py` 的 `test_b3_as_drawn_plan_is_known_but_not_consumed` 与 `test_b3_as_drawn_raises_and_says_known_not_unknown`）
⚠️ **B 层更正**：你上一轮把这两条写成行号 `170/210`，我回文件 `grep -n` 实测是 **159 / 214**。⭐ 纪律：**引用位置一律回文件按【锚点名】grep，⛔ 别用行号** —— 行号会漂，名字不会。
⭐ 另外**这张清单本身可能不全**：⛔ 别把它当穷举，请你自己再扫一遍「哪些锁断言了 as-drawn 不被消费」）**是要翻的**（它们 docstring 自己写着"module 7 落地时这个 pin 会翻"）。
⛔ **但不许删掉了事** —— `test_no_new_contract_became_consumable` 保护的**规则**是
「**没有任何合同能悄悄长出一条线**」；必须改写成**同时覆盖 `consuming` 与 `adapting` 两个集合**的规则。
⇒ 拿删锁换绿 = 本单作废。

### B. 新链接进 `run_correction` 的真实入口
[`src/agent/pipeline.py:732 run_correction`](../../../src/agent/pipeline.py#L732) 增加一条**新链路径**：

```
识图产物(冻结字节) → adapt_* → CorrectionEvidenceBundleArtifactV1
   → compile_wall_ir → WallCompilationV1
   → build_decision_packet → CorrectionDecisionPacketV1
   → 【模型】→ CorrectionDecisionResponseV1
   → run_decision_loop → DecisionLoopOutcomeV1   ← 本单的终点
```

**平面走新格式 adapter（`adapt_as_drawn_plan`），立面走 legacy adapter** ——
这不是「兼顾旧格式」，是设计稿 §9.1 第 7 步的原话「新旧源都走 bundle」：
立面**至今没有任何新格式产物**（我查过：只有 `as_drawn_elevation_v0`），
拆旧腿是**后面另一单**（plan.md ④），⛔ 不在本单。

⭐⭐ **切换必须显式，且开了就不许回落**：
- 新链默认**关**（默认关是为了让现有全量读数一位不变，见验收 2）；
- 用一个**显式**入参/开关打开，且**run 目录里必须落一份记录说明这次走的是哪条路**；
- ⛔⛔ **新链打开后中途失败 ⇒ 响亮失败**。**绝对不许 fall back 到旧的贴 JSON 路径** ——
  「新格式不好处理就静默回退旧路」这条缝正是指南 §十之二 第 4 条要消灭的东西。

### C. 模型那一拍
今天全仓**没有任何提示词产出 `CorrectionDecisionResponseV1`**（我 grep 过），`run_decision_loop` 只被夹具喂。
本项 = 写这一拍：提示词 + 结构化输出 + 接进 `run_decision_loop`。
- 模型入口**唯一**走 [`src/agent/llm.py`](../../../src/agent/llm.py) + [`src/configs/llm.yaml`](../../../src/configs/llm.yaml)（CLAUDE.md §5#2），⛔ 不在节点里硬编码。
- ⭐ **响应里结构上不许有坐标** —— `decision_schema.py` 的类型已经这么设计了；
  本单要的是**一把锁证明这件事没被绕过**（比如 `extra` 通道、字符串里塞数）。

### D. 落盘与溯源
`DecisionLoopOutcomeV1` 落进 run 目录；`success` / `exit_reason` **如实落盘**。
⛔ `exit_reason != "success"` 时那份 provisional **不得**被当成成功产物往下游递。

---

## 二、⛔ 本单明确不做（做了就是超范围）

| 不做 | 为什么 | 挂到哪 |
|---|---|---|
| **投影桥**（`CorrectedGeometryProjectionEnvelopeV1`，设计稿 §5.4）| 它要把「墙」派生成「房间(cells)」，**这是一个几何派生的架构决定，不是接线** ⇒ 归主控出方案、另开单 | 下一单（甲-2）|
| 拆旧格式那条腿 | 前提是新格式夹具顶上；且指南 §十之二 第 1 条：拆单排在模块 5/6 之后 | plan.md ④ |
| `CONSUME` **重命名** / `KNOWN_NOT_CONSUMED` 重命名 / ledger **重排** | plan.md 已登记「本批不做」。⚠️ **注意与 §一A 的分界**：**新增** `ADAPT` 值与第五分支是**必做**，⛔ 别把两者混为一谈 | 收窄工程单 |
| 补任何围栏 / 加任何阈值 | 用户本程口径 = **先只求跑得通**；跑不通的地方**响亮报错 + 登记**，⛔ 不当场补 | plan.md |

⭐ **这条禁令【不】禁止加测试锁** —— §三的验收 3/4/5 明确要求加锁，锁是判据不是围栏。禁的是**在生产代码里新造门、新设阈值**。两者若在某处你分不清，按 A 层停报（§四）。

---

## 三、验收（⭐ 每条都写成**规则**，⛔ 不是现状名单）

> ⭐ **绿锚纪律**：每条验收只许锚在**它自己负责的那一段**上。
> ⛔ 不许写成「整份全绿」——那会让本单的锁变成别人家已知缺陷的人质。

| # | 规则 | 怎么证 |
|---|---|---|
| **1** | 拿**一份真实的 sm25 新格式平面产物**走完 A→C，落盘一份 `DecisionLoopOutcomeV1` | 贴命令原文 + 输出；⛔ 别贴转述 |
| **2** | **新链关闭时，现有那 3632 条不许有【计划外】的红或消失**。⚠️⚠️ **两处计划内的变动，⛔ 别把它们当违规**：① 本单要求你**加锁** ⇒ 总数会变大；② §一A 要求你**翻 6 把 pin 锁** ⇒ 那几条会被改写、可能改名。⇒ ⛔ **「读数一位不变」不是判据**（那正是「验收要求不变、而任务项要求改东西」的老病，我 v1 犯过一次、v2 差点又犯）| `failed` 恒 **0**、`xfailed` 恒 **13**、`passed` **不小于 3632**；⭐ **另附一张【变动清单】**：每一条被改写/改名/新增的锁都**点名**，并各写一句「**它原本保护的规则，现在由谁保护**」。⛔ 只报总数不算数 |
| **3** | 新链打开、链上**任一环**失败 ⇒ ① 异常**穿出到调用方**（⛔ 不被吞）② run 目录留下一条指名哪一环的失败记录 ③ ⛔ **不产生任何被当成功的产物**（`exit_reason != "success"` 时那份 provisional 不得往下递）| 每一环各造一次失败，⛔ 不是只造一次；每次都要证明「**没有悄悄走旧的贴 JSON 路**」。⚠️ ⛔ **别把这条读成「加围栏」** —— 四个模块**本来就各自响亮失败**（`EvidenceContractError` / `WallCompilerError` / `DecisionLoopError`）；本单要你做的是**不要去接住它、不要加回退**，⛔ 不是新造一道门 |
| **4** | 注册改动的**三个方向各有一条锁**：合法新格式 → 走 adapter；旧格式 → 仍走 legacy；**结构损坏的新格式 → UNKNOWN，⛔ 不许静默落回 legacy** | 第三条是重点：`classify_vector_json` 的 BLK-A 规则声称保证这件事，**要实测，不要引用它的注释** |
| **4b** | 翻掉的 pin 锁**改成了规则、没有变弱**：改后的锁在「**任何合同悄悄长出一条线**」这个方向上仍然**能红** | ⭐ 造一个「第三个合同偷偷变成 adapting」的变异，锁必须红。⛔ 只报「改写完了」不算数 |
| **5** | 模型响应里**结构上没有坐标**这件事有锁，且**该锁摘掉相应实现会变红** | ⭐ 只说「测试通过」不算数 —— 必须证明它**能红**（[[gate-with-only-negative-assertions-is-unobservable]]）|
| **6** | 全量绿（**`-n 6`**，⛔ 不用 `-n auto`：本程有另一个席位在飞，同机三路会跑崩）| 汇总行原文 |

**⭐ 环境自证（⛔ 每次跑测都要，且与 pytest 放【同一条命令】）**：
```
python -c "import src.agent.correction.evidence_adapters as m; print(m.__file__)" && python -m pytest ...
```
`__file__` 必须落在**你自己的工作目录**里。⛔ **不要用 `.pth` 哈希当判据**——它是代理量，
而且 claude 家族席位**光是启动就会改掉它，不是谁违纪**（CLAUDE.md §5#8.6）。

---

## 四、停下上报（⭐ 分层，⛔ 不是一律停）

**A 层 —— 立刻停，不要绕**（承重前提错了）：
1. 上面 §〇 表里任何一行**你实测不成立**（尤其「①→②→③ 已通」）。
2. 设计稿 §5.4 / §9.1 第 7 步与本单的说法**打架**。
3. 要完成任务项，**必须动 §二 的禁令**。
4. ~~现有枚举表达不了「交给 correction adapter」~~ ⇒ ✅ **v2 已答**（§一A 的范围裁定），⛔ 不必再停。
5. **新的**：`ADAPT` 分支要正确，**必须**动 §二 禁令里的重命名或 ledger 重排。

**B 层 —— 记一条，继续干**（外围）：我引的行号、读数、文件名对不上。
⇒ 交件里列一张「派工方说的 vs 我实测的」，⛔ 别停。

**⭐ 合法出口**：模型那一拍要是**真跑不出合法响应**（额度 / provider / 结构化输出打架），
允许先用**固定响应**证明 loop 通，但**交件里必须显式写明「模型未真跑」**，
⛔ 绝对不许把 fixture 的结果写成模型的结果。

---

## 五、交件

⛔ **指南 §五#1：文字不许跑在实现前面。** 交件里每一个数，都要能指出**是哪条命令、哪份产物跑出来的**；
⛔ 不许拿设计稿的描述或本单的措辞当读数。

1. 一份执行日志进 `AI_agent/logs/reviews/execution/`：**命令原文 + 输出原文**，⛔ 不要长篇自述（复核方只看原始需求 + diff + 测试输出）。
2. 逐条对着 §三 的六条报，红/绿都报。
3. ⛔ **不要跑 `pip install -e .` 或任何写 `site-packages` 的命令**（venv 全机器共享）。
4. ⛔ 有席位在飞，**提交只 add 你自己动过的明确路径**，⛔ 不许 `git add -A`。
