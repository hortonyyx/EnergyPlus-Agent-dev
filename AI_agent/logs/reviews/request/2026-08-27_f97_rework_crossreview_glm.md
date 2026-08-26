# 跨家族复核请求（第二轮 · 返工审 · **改派**）· F-97 契约判别器

- **日期**：2026-08-27　**复核席位**：**GLM 家族**（`bash scripts/glm_code.sh`，`glm-5.3`）
- **施工席位**：**Claude 家族**（返工轮）⇒ ⛔ 谁写谁不批 —— 你不是施工方，合法
- **被审 commit**：`f2a8ccf`（分支 `wt/08.27_f97_contract`，worktree `/tmp/ep_f97`）
- ⚠️ **为什么改派给你**：上一轮的 REWORK 裁决是 **GPT 家族 sol** 写的，本轮本该由它复审；
  但它**连开三次**：前两次因 orchestrator 题面错停下上报（都对，见 §七），
  第三次**做完了实体复核（113k token、造了新夹具、跑了 neuter）却在写裁决时被它自家 provider 的安全过滤连拦两次** ⇒
  **裁决文件没写成**。按本项目 08-16 已定的口径「措辞最多改一次、然后换家族」⇒ **改派 GLM**。
  ⛔ **它的探针文件我保住了，但那是【线索】不是证据，见 §五。**
- **上一轮裁决（GPT 写的）**：`AI_agent/logs/reviews/verdict/2026-08-27_f97_contract_discriminator_gpt_verdict.md`
  （**REWORK / 3 阻断 B-01 B-02 B-03 / 3 不阻断 N-01 N-02 N-03**）
- **原派工单**：`AI_agent/logs/reviews/request/2026-08-27_f97_contract_discriminator_dispatch.md`
- **施工方自述**：`AI_agent/logs/reviews/execution/2026-08-27_f97_contract_discriminator_construction_report.md`
  （⚠️ **只作线索，不作证据** —— §5#8：施工席自述一律以 `git diff` 为准）

---

## 〇、你的工作目录与跑测纪律（⛔ 写死 · 以下读数为 orchestrator 在**发单前最后一刻**重跑所得）

```
/tmp/ep_f97       ← 被审 worktree 本体
```

```text
$ git -C /tmp/ep_f97 log --oneline -1
f2a8ccf 08.27_F97Rework_DeclaredSchemaNeverFallsBackToLegacy_AndTheLedgerGoesFirst

$ git -C /tmp/ep_f97 status --porcelain
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_glm.md
```

- **开工自检**：HEAD 必须 = `f2a8ccf`。对不上 ⇒ **停下上报**。
- ⚠️ 那 **2 份 untracked md 都是 orchestrator 留的**（`..._gpt.md` = 派给 GPT 的同一份单子，
  留作对照；`..._glm.md` = **本单**）。**⛔ 别删、别提交。**
  ⇒ 交件时 `status --porcelain` 应为**这 2 项 + 你自己写的裁决文件**，共 3 项。
  ⚠️ 若你实测到的与此不符 ⇒ 我的题错，照 §六 #1 分层办。
- ⛔ **不许在 `/workspaces/EnergyPlus-Agent-dev`（主树）改任何文件、不许在主树跑全量。** 主树可只读参阅。
- ⛔ **你是复核方，不许替它改代码。** 探针 / 变异可做，**做完必须还原**（指被审的源码与测试）。
- ⚠️ **跑全量一律 `python -m pytest -q -n 6`，⛔ 不要 `-n auto`** —— orchestrator 同机在主树也跑着一轮全量。
- ⛔ **裸跑脚本会因共享 venv 的 editable `.pth` 静默串到主树**；一律 `python -m …` 或 pytest 入口。
- ✅ `.env` 已软链进该 worktree。
- ⭐ **先跑全量、把 summary 行抄下来，再做别的**（上一轮你在 G1 单上就是这么办的，很对）。

### 提交链与返工面（`--numstat` 逐字读数，⛔ 不是我数出来的）

`ed0ba09..f2a8ccf` **共 3 个提交**：`e08c79b`（第一轮停下上报）· `8fda4c1`（首次施工 = GPT 上一轮审的对象）· `f2a8ccf`（返工）。
`ed0ba09` 是主线 `534b5a2` 的祖先（`git merge-base --is-ancestor` 实测为真）。

```text
$ git diff --numstat 8fda4c1 f2a8ccf          # ← 本轮返工面
126  190  AI_agent/logs/reviews/execution/2026-08-27_f97_contract_discriminator_construction_report.md
106    0  AI_agent/logs/reviews/request/2026-08-27_f97_contract_discriminator_crossreview_gpt.md
 93    0  AI_agent/logs/reviews/request/2026-08-27_f97_contract_discriminator_dispatch.md
139    0  AI_agent/logs/reviews/verdict/2026-08-27_f97_contract_discriminator_gpt_verdict.md
 26    6  src/agent/pipeline.py
 71   10  src/agent/reading/vector_contract.py
194    0  tests/test_f97_vector_contract.py

$ git diff --numstat ed0ba09 f2a8ccf           # ← 本单全貌（代码面）
  0   18  scripts/tool_scripts/affected_tests_rules.yaml
 63    1  src/agent/pipeline.py
371    0  src/agent/reading/vector_contract.py   (新增)
541    0  tests/test_f97_vector_contract.py      (新增)
```

---

## 一、这件事要解决的原始问题（⛔ 不是「diff 干了什么」）

**F-97 = `1_correction` 会静默吃下它没声明过的输入契约。**

历史行为：correction 把 `0_reading/` 目录下**凡是 JSON 就往提示词里塞**，
不问「这份东西是什么契约、我认不认识它」。⇒ 新格式（as-drawn 三层产物）进来时，
门**不但看不见它，还给绿灯**。

**要的三件事**：
- **F-a**：correction **只消费已登记的契约**；
- **F-b**：**未登记的契约 ⇒ 响亮失败并点名**（⛔ 不许静默排除、⛔ 不许静默消费）；
- **F-c**：**消费对账**（ledger）—— 每份文件被消费 / 被排除 / 判成未知都要在盘上留一条带理由的账，
  **包括那次 run 最终失败的情形**。

---

## 二、GPT 上一轮判的三条阻断（本轮的正靶）

> ⛔ 以下逐字取自 **GPT 家族 sol** 的裁决，orchestrator 未改写。**⚠️ 它们本身也可能判错，见 §六 #5。**

| # | 阻断 | 它写的返工要求 |
|---|---|---|
| **B-01** | 未知显式 schema 可被误当 legacy 消费（`schema="future_reading_contract_v99"` + 合法 legacy `strokes` ⇒ `reading_view_legacy/consume`）| 显式声明不能无条件回落 legacy；「已登记显式契约 + legacy 同时命中 ⇒ AMBIGUOUS」保留，「**未登记/畸形**显式 schema + legacy 结构」必须判 unknown；**补真实 `_build_correction_messages` 入口锁** |
| **B-02** | stage report 以**键名 proxy** 冒充生产契约，畸形 JSON 被静默排除 | 复用已有 `CheckReport` 类型 + 保留三键显式存在约束；补「键齐但类型非法 ⇒ unknown loud-fail」的**入口锁** |
| **B-03** | 消费对账在真实入口写得太晚，分类失败可能无 ledger（`pipeline.py:720-725` 的 evidence preflight 先崩，`:738-739` 的 ledger 没执行）| 在任何会解析 `*_view.json` 的 preflight 前完成分类/ledger，或让 preflight 复用同一次分类结果；**新增真实 `run_correction` 入口负例** |

⭐ **B-03 的病根 = 「helper proxy 冒充生产入口锁」**（GPT 原话：那条测试只直调 `_write_vector_contract_ledger`，
其「run that fails」说明是 helper proxy，不是生产入口锁）。
⇒ **请把「锁走的是真实入口还是 helper」当成一等检查项**，不只查 B-03 那一条。
同族已登记：[[lock-must-exercise-real-entry-point]]。

---

## 三、⭐⭐⭐ 请你重点打的六处（按价值排序 —— 预算紧就从上往下打）

### 3.1 ⭐⭐⭐ 三条阻断的**双向**验证（⛔ 不是「看代码像修了」）

对 **B-01 / B-02 / B-03 每一条**分别做两次：
1. **在 `8fda4c1`（返工前）复现出那条缺陷** —— 复现不出来 ⇒ **说明 GPT 上一轮那条判错了**，请如实写；
2. **在 `f2a8ccf`（返工后）确认它不再复现**。

**什么情况下会不通过**：① 某条在 `8fda4c1` 上就复现不出来；② 某条在 `f2a8ccf` 上仍能复现；
③ **修法只堵住了 GPT 举的那一种输入，换一种同形输入照样走通**（⭐ 这一条最要紧，见 §五的线索 3）。

### 3.2 ⭐⭐⭐ 施工方自己点名的「最可能塌」：**第二处手写清单**

施工方自述：`DECLARED_SCHEMA_VALUES` 是**手写的第二处清单**，
往 `CONTRACTS` 加契约却忘同步 ⇒ **「已登记被判成未登记」静默错配**。
它自己写着：**「这是『第二个定义』这个病的第三次现形」**。

请判：**有没有机械对账把这两处钉死**（从 `CONTRACTS` 派生？元测试断言等价？）
没有 ⇒ 是不是阻断由你判，但请明确说出**今天会不会真的错配**、**加一条契约时会不会静默**。

### 3.3 ⭐⭐ **两处各分类一遍**

施工方自述：`_preflight_vector_contracts` 与 `_build_correction_messages` **各分类一遍**。
请构造一份能让两处**给出不同结论**的输入。若不能，请说明**凭什么不能**（共用同一函数？还是今天恰好一致？）。

### 3.4 ⭐⭐ **兼容面的数请你独立重数，⛔ 不许照抄**

施工方自述读数（**orchestrator 一个都没独立核过，全部待验**）：
边车 **43/43 仍 EXCLUDE**、legacy **328/328 仍 CONSUME**（已写成硬断言）；
字节变化面 **56 / 49 / 7 / 0，移除 170,455 B**，自述**与返工前逐字相同**。

⚠️ 施工方同时自陈：`==43` / `==328` 这两个**硬断言没写「为什么是这个数」的出口**，
后来者可能当误报放宽。请判这个形态（把语料计数烤成常量）是不是该阻断。

### 3.5 ⭐⭐⭐ **再找一种能骗过它的真实输入形态**（本项目硬纪律 §五#2）

> 「**自己挑的破坏方式挑不出自己的盲区。**」

⚠️ **本条你有一个特殊约束**：§五 给了另一席位跑出来的 5 条线索。
**⛔ 复核它们不算完成本条** —— 请**另外独立找一遍**，且**换方向**。
（你在 G1 那轮自造 11 种形态级变异，正是这条要的东西。）

**判据**：找到**任何一条**能被静默消费或静默排除的真实形态 ⇒ **阻断**。

### 3.6 ⭐⭐ **信任根只验了产物侧**

施工方自述：B-02 的 `CheckReport` 信任根**只验了产物侧**、
**没回溯 `validation_run.py:292` 的构造类型**。
⇒ 判别器认的 `CheckReport`，与**生产它的那条路真正会写出来的东西**，是不是同一个形状？
（同族 [[recompute-gate-must-mirror-producer-definition]]。）

---

## 四、验收判据（逐条给读数；⛔ 每条都必须有「会不通过」的情形）

| # | 判据 | 什么情况下会不通过 |
|---|---|---|
| **A1** | ⭐ **第一个动作**：独立跑全量 `python -m pytest -q -n 6`，**summary 行逐字抄进裁决** | 有 failed / error；或 summary 行缺失（同机竞争假红 ⇒ 重跑一次再判） |
| **A2** | B-01 / B-02 / B-03 **各做双向验证**（§3.1） | 任一条在旧 commit 复现不出、或在新 commit 仍复现、或换同形输入又走通 |
| **A3** | **每一条新锁走的是生产入口还是 helper** —— 逐条点名 | 存在只调 helper 的锁却被当成入口锁 |
| **A4** | **neuter 逐条**：摘掉每条机制，对应锁必须变红，且**只红对应的那几条** | 摘了不红（= 没接线）；或红一片（= 附带面失控） |
| **A5** | 兼容面三个数（43 / 328 / 371 或你自己数出的口径）**独立重数** | 与自述对不上；或口径是「抽样」却被写成全集 |
| **A6** | ⭐ **独立主动找缝**（§3.5），写出你试过哪些形态、各自读数 | 找到能静默通过的形态 ⇒ 阻断 |
| **A7** | **§五那 5 条线索逐条独立复跑**并给出你自己的判定 | 有任一条经你复跑成立且属阻断级 ⇒ 阻断 |
| **A8** | GPT 上一轮三条不阻断（N-01/N-02/N-03）**现状复查** | 有任何一条实际已恶化成阻断 |

⚠️ **A4 的注意**：[[neuter-proves-wiring-not-discriminating-power]] ——
**变红只证明接线，不证明有分辨力**。摘了机制才红、但换个真实错误照样绿的锁，请点名。

---

## 五、⚠️⚠️ 另一席位（GPT sol）的探针文件 —— **⛔ 线索，不是证据**

GPT 第三次派出实打实审了 113k token，写了一个探针文件后才被 provider 拦掉。文件我保住了：

```
/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/execution/artifacts/2026-08-27_f97_rework_gpt_probe/_review_f97_new_probe.py
```
（118 行，只读参阅。同目录还有它**没来得及还原**的一处 neuter diff = 摘掉 `_declares_unregistered_schema` 那两行；
orchestrator 已在 worktree 里 `git checkout --` 还原。）

⛔⛔ **它的裁决没写成 ⇒ 我们不知道它自己怎么判这些**（哪条它认为是阻断、哪条它认为无害）。
**orchestrator 也一条都没跑过。** ⇒ **以下全是【它写在测试名与断言里的主张】**：

| # | 探针名 | 它主张的 |
|---|---|---|
| 1 | `test_new_b01/b02/b03_..._at_real_run` | 三条阻断的**原夹具**已在真实入口被拦、点名、记账 |
| 2 | ⭐ `test_registered_but_malformed_declaration_still_falls_back_and_is_consumed` | 顶层声明 **as-drawn schema** 但只带 legacy `strokes` ⇒ 仍判 `reading_view_legacy` 并**被消费** |
| 3 | ⭐⭐ `test_unhashable_schema_crashes_before_ledger`（`schema=[]` / `{}`）· `test_invalid_utf8_crashes_before_ledger` | **崩在 ledger 之前 ⇒ 与 B-03 同形**（即 B-03 可能只修了 GPT 举的那一种输入）|
| 4 | `test_empty_and_bom_files_are_named_and_ledgered` | 空文件 / BOM ⇒ 点名且记账（**这条是好消息**）|
| 5 | `test_uppercase_and_nested_json_are_absent_from_ledger_inventory` | `MYSTERY.JSON`（大写）与子目录里的 json **不进 ledger 清单** |

**你的动作（A7）**：逐条**自己复跑**、自己判**是不是阻断**。
⛔ **别把它的断言当结论**，也**别因为有了这 5 条就跳过 §3.5 的独立找缝**。
⚠️ 若你复跑发现其中某条**根本不成立**，请直说 —— 那同样是有价值的读数。

---

## 六、⛔⛔ 停下上报触发器（分层，⛔ 别一律停）

> **事实依据**：本项目累计 **38 次「停下上报」，38 次都是派工方（orchestrator）的题错了**。
> ⇒ **触发器命中不是你的问题，是我的。**
> ⚠️ **但本单已经因不分层的触发器空转两轮**（GPT 为一处「返工面里有 3 份还是 4 份 md」停了整轮），
> 所以本条现在是**分层**的。

1. ⭐⭐ **题面与实测不符 —— 分两层办**：
   - **(a) 承重前提错 ⇒ 停下上报**：错了之后**整个任务方向作废 / 判据不再有意义**
     （例：被审 commit 不对、要审的机制根本不在这棵树里、判据结构上不可能红）。
   - **(b) 外围事实错 ⇒ 记进「orchestrator 题面写错的地方」那一节，然后【继续审其余】。**
     行号偏了、文件计数差一、我引的某个数字不对 —— **都属 (b)**，照记不误、但别为它们停。
   ⇒ **判别问法：这条错如果成立，我还需不需要审这份 diff？需要 ⇒ 走 (b)。**
2. **判据里有一条结构上不可能红** —— 即无论被审对象怎样它都通过。（你在 G1 单上抓到过我一条，请继续。）
3. ⭐ **两个选项都次优，但存在第三条严格更优的路** —— ⛔ 别在我给的两条里硬选。
   （你上一轮的「把签字件喂进复现跑」正是这条触发器的产物，价值最高的一次。）
4. **要验它必须改被审对象之外的文件** —— 停下说清楚要改什么、为什么。
5. ⭐ **你发现 GPT 上一轮那三条阻断里有一条判错了** —— 直说。**本轮我没有任何维持一致的义务。**

---

## 七、⚠️ orchestrator 自认本单可能写错的地方（请优先证伪）

0. ⭐⭐⭐ **本单派给 GPT 的那一版，前两次都被它判「停下上报」，两次都是我的题错（第 37、38 次）**：
   - 第 37 次：§〇 写「工作树干净」——**写下那一刻是真的**，可我随后**自己**把请求单 `cp` 了进去，
     再叠「交件时只剩裁决文件」⇒ **结构上不可同时满足**。
   - 第 38 次：§〇 写返工面「另有**三份** md」，`--numstat` 实测**四份**。
   ⭐⭐ **第 38 次真正的病不是那个数，是我的触发器写得不分层** —— 已改（§六）。
   ⇒ **本单 §〇 的所有读数现在都是发单前最后一刻重跑的原始输出**，但**其余各节仍可能有我拍脑袋的地方**。
1. **§3.4 的全部数字（43 / 328 / 56 / 49 / 7 / 0 / 170,455 / 3070 passed）我一个都没独立核过**，全部转录自施工方自述。
2. **§二那三条阻断我是逐字抄 GPT 的裁决**，但「返工要求」那一列我做过压缩 —— 以它原文为准。
3. **我把 B-03 的病根概括成「helper proxy 冒充生产入口锁」** —— 这是我的归纳，不是 GPT 的原话，可能过窄。
4. **§五那张表是我读探针的【测试名与断言】归纳出来的**，⛔ 我没跑过、GPT 也没说它怎么判。
   若我把某条的含义读歪了，请直接改写。
5. **我没有核实「返工后 `pipeline.py` 的 ledger 是否真的排在 preflight 之前」** —— 刻意不核，因为那正是要你判的。

---

## 八、交件形式

**把裁决写成文件**，路径写死：

```
/tmp/ep_f97/AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md
```

⚠️ **必须是文件、且必须写完再结束会话**（08-27 两次实测教训：转录版与原件逐字节不同；
以及一个复核会话在全量跑完前就结束、留下占位符）。

**结构**：总判（`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT`）·
§四 判据 A1–A8 逐条读数（⛔ 不许留占位符）· §三 六处逐条结论 · **§五 5 条线索逐条你自己的判定** ·
Findings（阻断 / 不阻断分开）· **「orchestrator 题面写错的地方」**一节 ·
你自己跑的全量 summary 行逐字 · 交件时工作树状态。
