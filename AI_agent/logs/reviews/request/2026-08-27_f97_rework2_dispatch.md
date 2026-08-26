# 派工单 · F-97 第二轮返工（三条阻断 BLK-A / BLK-B / BLK-C）

- **日期**：2026-08-27　**施工席位**：**Claude 家族**（= 本单代码的原施工方）
- **复核席位（已定）**：**GLM 家族** —— 三条阻断是它提的 ⇒ ⛔ 谁写谁不批，你别自己审
- **worktree**：`/tmp/ep_f97`　**分支**：`wt/08.27_f97_contract`　**起点**：`f2a8ccf`
- **返工依据**：`AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md`
  （**REWORK / 3 阻断 / 6 不阻断**，⭐ **整份读完再动手**）

---

## 〇、工作目录与纪律（⛔ 写死 · 读数为 orchestrator 发单前最后一刻重跑）

```text
$ git -C /tmp/ep_f97 log --oneline -1
f2a8ccf 08.27_F97Rework_DeclaredSchemaNeverFallsBackToLegacy_AndTheLedgerGoesFirst
```

- **开工自检三问**（对不上任一条 ⇒ **停下上报**）：
  ① HEAD = `f2a8ccf` · ② `AI_agent/CLAUDE.md` 存在且 `grep -c ''` 得 **447**
  （⚠️ 主树那份是 448，多出的一行是今天 orchestrator 加的，与你无关）·
  ③ `AI_agent/guides/reading_correction_split_guide.md` 存在。
- ⚠️ **worktree 里有 4 份 untracked md，全是 orchestrator 留的，⛔ 别删别提交**
  （`request/…_f97_rework2_dispatch.md` = **本单** · `request/…_f97_rework_crossreview_glm.md` ·
  `request/…_f97_rework_crossreview_gpt.md` · `verdict/…_f97_rework_glm_verdict.md` = **返工依据**）。
  ⇒ 交件时 `status --porcelain` 应为**这 4 项 + 你的施工报告**（提交后前 4 项仍在）。
- ⛔ **不许碰 `/workspaces/EnergyPlus-Agent-dev`（主树）**。主树可只读参阅。
- ⛔ **裸跑脚本会因共享 venv 的 editable `.pth` 静默串到主树**；一律 `python -m …` 或 pytest 入口。
- ⚠️ **跑全量 `python -m pytest -q -n 6`**（⛔ 不要 `-n auto`，同机可能有别的席位）。
- **本 commit 的干净树全量基线（GLM 实测）**：`3070 passed, 13 xfailed, 211 warnings`，exit 0。

---

## 一、这件事要解决的原始问题（⛔ 不是「把三个夹具改绿」）

**F-97 = `1_correction` 会静默吃下它没声明过的输入契约。** 三条承诺：
- **F-a**：只消费**已登记**的契约；
- **F-b**：**未登记的契约 ⇒ 响亮失败并点名**（⛔ 不许静默排除、⛔ 不许静默消费）；
- **F-c**：**消费对账**（ledger）—— 每份文件被消费/排除/判未知都要在盘上留一条带理由的账，
  **包括那次 run 最终失败的情形**。

⭐⭐⭐ **复核方给的病根句（比上一轮我写的准，请以这句为准）**：
> **F-c 的「失败必留账」要在【所有】会碰 `0_reading` 的入口、与【所有】输入形态下成立。**

⇒ **BLK-B 是「入口」那半，BLK-C 是「形态」那半。** 上一轮我把病根概括成「helper proxy 冒充生产入口锁」
**过窄** —— 这两条**都与 helper proxy 无关**（锁全走真实入口也拦不住）。

---

## 二、⛔⛔ 三条阻断（**返工要求逐字取自 GLM 裁决，⛔ 我未压缩**）

> ⭐ **为什么强调逐字**：BLK-A 之所以存在，正是因为上一轮 GPT 的返工要求原文写着
> 「**未登记 / 畸形** 显式 schema」，而施工**只修了「未登记」那半**。
> ⇒ **请把下面每条要求当成逐字合同来读，别读成摘要。**

### BLK-A｜已登记值的「畸形声明」仍回落 legacy 并被静默消费

- **证据**：`{"schema": <任一已登记值>, "strokes": [合法 stroke]}`（**缺该契约必需键**）⇒
  `reading_view_legacy / CONSUME`；`as_drawn_plan_v2`（经 `_build` 原文进提示词）与
  `as_drawn_plan_v0` / `as_drawn_elevation_v0`（判别器直测）**三值全测**。
- **返工要求（逐字）**：
  > 声明过 `schema` 而该声明**不匹配任何已登记契约**的文件，永远不得被解析为 legacy CONSUME（判 unknown）；
  > 「已登记声明 + legacy 结构**双命中** ⇒ AMBIGUOUS」的现行为**保留**（R2 守的就是它）。
  > 实现上可在 `classify_vector_json` 加后置规则（唯一命中为 legacy 且 `"schema" in raw` ⇒ 改判 unknown 并说明原因），
  > 不必把双命中也否决掉。补一条 registered-but-malformed 的真实入口锁（R1 组同款三件套）。
- ⚠️ **注意那句「不必把双命中也否决掉」** —— 上一轮施工第一版就是在这里塌过一次
  （写「有 `schema` 键就不是 legacy」，当场把双命中从 AMBIGUOUS 塌成单命中）。**别再塌。**

### BLK-B｜`run_pipeline` 在分类/ledger 之前自己解析 `*_view.json`

- **证据**：`run_pipeline_artifacts` 于 `pipeline.py:1368`（`compute_reading_report_from_vector_dir` →
  `load_reading_view` 逐个解析 `*_view.json`）、`:1376-1379`（再解析一遍）、v3 `:1411`（catalog）
  **全部先于 `:1414` 的 `run_correction`**。夹具 `1f_view.json = [1,2,3]` ⇒
  `AttributeError: 'list' object has no attribute 'get'`（`reading/legacy.py:108`）、**ledger 不存在**；非法 JSON 同形。
  **正对照**：同一毒文件改名 `mystery.json` 走 `run_pipeline` ⇒ 正确 `UnconsumableVectorFile` + ledger 在盘
  ⇒ **缺口纯由入口顺序造成**。`8fda4c1` 同样崩 ⇒ **未覆盖、非回归**。
- **返工要求（逐字）**：
  > 把 `_preflight_vector_contracts(vector_dir, out_dir)` 提到 `run_pipeline_artifacts` 中
  > **任何 `*_view.json` 消费之前**（至少先于 :1368），或让 reading-report / catalog 消费复用同一次分类结果；
  > 补一条走 `run_pipeline(_artifacts)` 的真实入口负例（非对象 + 非法 JSON 两条）。

### BLK-C｜「ledger 永不抛」前提不成立

- **证据**（三形态全实测，**ledger 文件均不存在**、异常均非点名异常）：
  1. `{"schema": [] /* 或 {} */, "strokes": […]}` ⇒ `raw.get("schema") not in DECLARED_SCHEMA_VALUES`
     对 frozenset 判成员 ⇒ `TypeError: unhashable type`；
  2. 非法 UTF-8（`b"\xff\xfe\x00"`）⇒ `read_text` 抛 `UnicodeDecodeError`，`_classify_rows` **只捕 `json.JSONDecodeError`**；
  3. **`0_reading/backup.json` 是个目录** ⇒ glob 收进目录名、`read_text` 抛 `IsADirectoryError`。
  ⇒ `ledger_for` 的 "never raises" 与 `pipeline.py:731-732` 注释 "`_write_vector_contract_ledger` never raises" **为假**。
- ⭐ **为何是阻断**：这三个**不是对抗性输入，是普通文件系统/编码现实**（截断的 UTF-16 产物、错位的 `mkdir`）。
- **返工要求（逐字）**：
  > `_classify_rows` 的异常面收宽为「读不出/解不开 ⇒ 账上一行 error + offender」：
  > 捕 `OSError`（含 `IsADirectoryError`）与 `UnicodeDecodeError`；
  > `_declares_unregistered_schema` 先 `isinstance(raw.get("schema"), str)` 再判成员
  > （非字符串声明值一律按畸形声明处理 ⇒ 不回落 legacy）。补三条对应真实入口锁。

---

## 三、⭐⭐⭐ 验收判据 —— **每条阻断都要你自己跑满三格**

> **立此条的事实依据（08-27 实测）**：上一轮的返工审判据只有前两格，**三条阻断在前两格上全绿**；
> 唯一新加的第三格**一次抓出全部三条**。
> ⇒ ⛔ **前两格只证明「被举的那个例子修好了」，第三格才证明「那类缺陷修好了」。**
> **这一轮把第三格下放给你**，别再等复核方来抓。

| 阻断 | ① 在 `f2a8ccf` 上复现得出 | ② 在你的新 commit 上复现不出 | ③ ⭐ **换同形输入仍走不通** |
|---|---|---|---|
| BLK-A | 三个已登记值各一份夹具 | 同上 | **自己造：换别的已登记值 / 换缺不同必需键 / schema 值大小写与空白变体 / 嵌在别的合法结构里** |
| BLK-B | `[1,2,3]` + 非法 JSON 两条，走 `run_pipeline_artifacts` | 同上 | **自己造：`:1376` / `:1411` 那两条路各来一次；再找 `0_reading` 还有没有【第四个】解析入口** |
| BLK-C | 三形态（非字符串 schema / 非法 UTF-8 / 目录） | 同上 | **自己造：权限不可读 / 符号链接断链 / 超大文件 / 其它 `OSError` 子类** |

**③ 的写法要求**：⛔ 不许只列「我试了这些都红」。**要写出你试过的每一种形态与各自读数**，
并明确说**你是按什么方向找的**（⛔ 「同形」不是我给的清单的复制）。

**另外必做**：
- **A-全量**：`python -m pytest -q -n 6`，summary 行逐字进报告。基线 3070 + 你新增的锁数。
- **A-neuter**：每条新机制**逐条摘掉**，对应锁必须变红且**只红对应的**。⚠️ 复核方已点名
  **N-F**：现有 R1/R4 锁对 BLK-A / BLK-B / BLK-C 的形态**零分辨力**（这些形态下现有锁全绿）
  ⇒ **新锁必须连同新形态一起补**，⛔ 别以为老锁能接住。
- **A-兼容面**：`43 / 328` 两个硬断言**别动**（本轮不改，见 §四），但要复跑确认没被你的改动打破。

---

## 四、⛔ 明确不做（本轮）

- ⛔ **N-A**（`DECLARED_SCHEMA_VALUES` 第二处手写清单无机械对账）—— **登记，本轮不做**。
  今天不会错配（复核方探针证三值↔三契约一一对应）；正解是给 `ContractSpec` 加 `declared_schema_value`
  **从源头派生**，那要动契约数据面，**另开单**。
- ⛔ **N-B**（`==43` / `==328` 语料快照常量）—— **登记，本轮不做**，
  但 orchestrator 已把它挂上硬闸：**本批第 ③ 步「产出新方案产物」开工前必须先改掉**
  （届时任何新 `0_reading/*.json` 入库都会让它们红 ⇒ 合法增长被当失败）。
- ⛔ **N-C / N-D / N-E**（`out_dir=None` 无账 · `{"strokes":[]}` 判 legacy · ledger 清单看不见大写/子目录）
  —— 登记不做。
- ⛔ **不要顺手重构**、不要动 `src/agent/pipeline` 以外的模块、不要改测试以外的既有断言。
- ⛔ **不要自己审自己**（复核归 GLM）。

---

## 五、⛔⛔ 停下上报触发器（**分层**，⛔ 别一律停）

> **事实依据**：本项目累计 **38 次「停下上报」，38 次都是派工方（orchestrator）的题错了**。
> **⇒ 触发器命中记功不记过。**
> ⚠️ 但 08-27 也吃过不分层的亏（一处「有几份 md」的计数错让整轮复核空转两轮），所以本条分层：

1. **题面与实测不符 —— 分两层**：
   - **(a) 承重前提错 ⇒ 停下上报**：错了则**整件事的方向作废 / 判据不再有意义**
     （例：行号指的根本不是那段代码、某条阻断在 `f2a8ccf` 上**复现不出来**、要求的行为与既有契约冲突）。
     ⭐ **「某条阻断复现不出来」务必停** —— 那说明复核方判错了，比闷头改重要得多。
   - **(b) 外围事实错 ⇒ 记进报告的「orchestrator 题面写错的地方」，然后【继续做其余】。**
2. **判据结构上不可能红**。
3. ⭐ **我给的两条路都次优，但存在第三条严格更优的** —— ⛔ 别在我给的里硬选。
   （复核方的「把签字件喂进复现跑」正是这条的产物，价值最高的一次。）
4. **要做它必须改 §四 明令不做的东西**。
5. ⭐ **BLK-A 的「保留双命中 AMBIGUOUS」与你的修法冲突** —— 停下说清楚，⛔ 别偷偷塌掉它。

---

## 六、⚠️ orchestrator 自认本单可能写错的地方（请优先证伪）

1. **§二三条阻断的证据与返工要求我是逐字抄 GLM 裁决的**，但**行号（`:1368` / `:1376` / `:1411` / `:1414` /
   `legacy.py:108` / `pipeline.py:731-732`）我一个都没自己核过** —— 请开工先核，对不上按 §五(b) 记下继续。
2. **我把病根句换成了 GLM 那句**（「所有入口 × 所有形态」）—— 那是它的归纳，**也可能仍不完整**。
3. **§三那张表里 ③ 列的「自己造」方向是我随手写的提示** —— ⛔ **不是穷举、也不保证是最有产出的方向**。
   你按自己的判断换方向，比照抄我的更有价值。
4. **我判定 N-A/N-B/N-C/N-D/N-E 都不做** —— 这是我按 §0.1 判断法则（「不做它，下次跑测能不能跑起来、
   结果能不能读」）做的取舍。**若你在施工中发现其中某条其实是三条阻断的同一个根**，⇒ §五 #3，停下说。
5. **§〇 的读数是我在发单前最后一刻对 `/tmp/ep_f97` 重跑的**（⭐ 这是 08-27 花两轮空转换来的新规矩：
   描述「环境现状」的句子必须在**最后一个准备动作之后**重核）。第一版我写的是「3 份 untracked / CLAUDE.md 448 行」，
   重跑抓到实际是 **4 份 / 447 行**，已改。⇒ **若你实测仍与 §〇 不符，那还是我的题错，按 (b) 记下继续。**

---

## 七、交件形式

1. **提交在 `wt/08.27_f97_contract` 上**（message 仿 `08.27_<英文标签>`，body 含 ①改动 ②为何此刻 ③影响）。
2. **施工报告**写成文件：`AI_agent/logs/reviews/execution/2026-08-27_f97_rework2_construction_report.md`
   —— **累计式自包含**，含：三条阻断 × 三格判据逐条读数 · 全量 summary 行逐字 ·
   neuter 逐条 · **⭐「我认为最可能塌的地方」** · **⭐「orchestrator 题面写错的地方」**。
3. ⭐ **「我认为最可能塌的地方」这一节是硬要求** —— 08-27 实测：上一轮施工自陈「B-02 是我最弱的地方」
   却没修，复核方就把它变成了阻断。**⇒ 「自陈不确定」≠「已处理」：识别出弱点就当场修掉，
   修不掉就写清楚为什么。**
