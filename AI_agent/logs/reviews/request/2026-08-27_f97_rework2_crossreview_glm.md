# 跨家族复核请求 · F-97 **第二轮返工**（BLK-A / BLK-B / BLK-C）

- **日期**：2026-08-27　**复核席位**：**GLM 家族**（`bash scripts/glm_code.sh`，`glm-5.3`）
- **施工席位**：**Claude 家族** ⇒ ⛔ 谁写谁不批，你不是施工方，合法
- **被审 commit**：`c3fc3fd`（分支 `wt/08.27_f97_contract`，worktree `/tmp/ep_f97`）
- ⭐ **三条阻断是你上一轮提的** —— 本轮验它们有没有被真正堵上
- **上一轮你的裁决**：`AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md`（**REWORK / 3 阻断 / 6 不阻断**）
- **本轮派工单**：`AI_agent/logs/reviews/request/2026-08-27_f97_rework2_dispatch.md`
- **施工方自述**：`AI_agent/logs/reviews/execution/2026-08-27_f97_rework2_construction_report.md`（495 行）
  ⚠️ **只作线索，不作证据** —— §5#8：施工席自述一律以 `git diff` 为准

---

## 〇、⛔⛔ 先读这条：本机今天出过一次【共享 venv 被改到别的树】的事故

**实测事实**（orchestrator 留证于 `AI_agent/logs/experiments/2026-08-27_pth_hijack/`）：
`/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth` 的内容在 **11:52:41** 被改成了
**`/tmp/ep_f97`**（原本是主树 `/workspaces/EnergyPlus-Agent-dev`）。
⇒ **orchestrator 当时正在主树跑的那轮权威全量因此作废、已重跑。**

⛔⛔ **由此给你（以及所有席位）的硬禁令**：
- **⛔ 绝对不许跑 `pip install -e .` / `pip install .` / 任何会写 `site-packages` 的安装命令。**
  这个 venv 是**全机器共享**的，改它 = 把别的席位和主树一起拖下水。
- 若你遇到 import 问题，**一律用 `python -m …` 或 pytest 入口解决**，⛔ 不许靠重装解决。
- `.pth` 现已还原指向主树。**若你发现它又变了，⇒ 立刻停下上报**（这属承重前提错）。

## 〇之二、工作目录与跑测纪律

```
/tmp/ep_f97       ← 被审 worktree 本体
```

**orchestrator 发单前最后一刻实测（⛔ 不是写单时量的）**：

```text
$ git -C /tmp/ep_f97 log --oneline -1
c3fc3fd 08.27_F97Rework2_ConstructionReport_ThreeBlockersThreeGridsAndNineNeuters

$ git -C /tmp/ep_f97 status --porcelain          # 5 份 untracked md，全是 orchestrator 留的，⛔ 别删别提交
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework2_crossreview_glm.md      ← 本单
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework2_dispatch.md             ← 施工派工单
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_glm.md
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
?? AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md           ← 你上一轮的裁决

$ cat /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
/workspaces/EnergyPlus-Agent-dev
```

⇒ 交件时 `status --porcelain` 应为**这 5 项 + 你的裁决文件**，共 6 项。
⚠️ 若实测与上面任一行不符 ⇒ 我的题错，按 §六 #1 分层办。

- **开工自检**：HEAD 必须 = `c3fc3fd`。对不上 ⇒ **停下上报**（承重）。
- ⛔ **不许在主树 `/workspaces/EnergyPlus-Agent-dev` 改任何文件、不许在主树跑全量**（主树可只读参阅）。
- ⛔ **你是复核方，不许替它改代码。** 探针/变异做完必须还原。
- ⚠️ **跑全量一律 `python -m pytest -q -n 6`，⛔ 不要 `-n auto`** —— orchestrator 同机可能在主树也跑着一轮。
- ⭐ **先跑全量、summary 行抄下来，再做别的**（你前两轮都是这么办的，很对）。

---

## 一、原始问题与病根句（⛔ 不是「diff 干了什么」）

**F-97 = `1_correction` 会静默吃下它没声明过的输入契约。** 三条承诺：
**F-a** 只消费已登记契约 · **F-b** 未登记契约 ⇒ 响亮失败并点名 · **F-c** 消费对账（**包括那次 run 最终失败的情形**）。

⭐ **病根句用的是你上一轮给的那句**（比 orchestrator 原来写的准）：
> **F-c 的「失败必留账」要在【所有】会碰 `0_reading` 的入口、与【所有】输入形态下成立。**

---

## 二、你上一轮三条阻断的返工要求（**逐字**，⛔ orchestrator 未压缩）

> ⭐ 为什么强调逐字：**BLK-A 的存在本身**就是因为上上轮 GPT 的要求原文写着「未登记 **/ 畸形**」而施工只修了前半句。

- **BLK-A**：「声明过 `schema` 而该声明**不匹配任何已登记契约**的文件，永远不得被解析为 legacy CONSUME（判 unknown）；
  『已登记声明 + legacy 结构**双命中** ⇒ AMBIGUOUS』的现行为**保留**（R2 守的就是它）。…补一条 registered-but-malformed 的真实入口锁。」
- **BLK-B**：「把 `_preflight_vector_contracts(vector_dir, out_dir)` 提到 `run_pipeline_artifacts` 中
  **任何 `*_view.json` 消费之前**（至少先于 :1368），或让 reading-report / catalog 消费复用同一次分类结果；
  补一条走 `run_pipeline(_artifacts)` 的真实入口负例。」
- **BLK-C**：「`_classify_rows` 的异常面收宽为『读不出/解不开 ⇒ 账上一行 error + offender』：
  捕 `OSError`（含 `IsADirectoryError`）与 `UnicodeDecodeError`；
  `_declares_unregistered_schema` 先 `isinstance(raw.get("schema"), str)` 再判成员。补三条对应真实入口锁。」

---

## 三、⭐⭐⭐ 请你重点打的六处（按价值排序）

### 3.1 ⭐⭐⭐ 三条阻断 × 三格（⛔ 不是「看代码像修了」）

判据三格：① 在 `f2a8ccf` 上**复现得出** · ② 在 `c3fc3fd` 上**复现不出** · ③ ⭐ **换同形输入仍走不通**。
⚠️ **本轮 ③ 已经下放给施工方自己跑过**（这是 08-27 定的新做法）⇒
**你的任务不是复读它的 ③，而是【另外再找一遍】** —— 见 3.5。

**什么情况下会不通过**：①在旧 commit 复现不出（⇒ 你上一轮那条判错了，如实写）· ②仍能复现 ·
③ 你能找到它 ③ 没覆盖的同形输入。

### 3.2 ⭐⭐⭐ 施工方自己点名的「最可能塌」—— **请优先打这里**

它自陈（⛔ 未经 orchestrator 复跑）：
1. **嵌套声明** `{"meta": {"schema": ...}}` **仍被当 legacy 消费** —— 它**故意没修**，
   理由是「需要先在契约数据面上定义『什么算一次声明』」；它自己说
   **「producer 哪天把声明包进信封里，它就是 BLK-A 的孪生兄弟」**。
2. **`pipeline.py:528` 是同一个错误的第二份拷贝**，**目前不可达只是因为 preflight 挡在它前面**。
⇒ 请判：这两条是**该阻断**、还是**登记即可**？⭐ 特别是第 2 条 ——
「靠另一道门挡着所以不可达」是本项目登记过的脆弱形态。

### 3.3 ⭐⭐⭐ **它的 ③ 撞出了四条【你上一轮的处方本身没覆盖】的东西 —— 请独立验证**

它自述（⛔ 全部待你复跑）：
| # | 它主张的 |
|---|---|
| 1 | **一个名叫 `*.json` 的 fifo 会让 `read_text` 永久挂死** —— **没有任何 except 能捕获**⇒ 修法必须是 `is_file()` 边界，⛔ 不是更长的 except 元组 |
| 2 | **深嵌套 JSON 触发 `RecursionError`**，既不是 `OSError` 也不是 `UnicodeDecodeError` ⇒ **你上一轮那条【逐字处方】照做仍会崩** |
| 3 | **v3 catalog（`:1411`）在【完全没有毒文件】的情况下也会丢账** |
| 4 | **`_run` 不可写时，F-c 的存储失败会把 F-b 的点名拒绝一起毁掉** |
| 5 | `:1376` **结构上被 `:1368` 遮蔽、不可能先崩** ⇒ 它用**顺序锁**覆盖，⛔ 没有伪造 payload |

⭐ **#1 与 #2 是对你上一轮处方的实质性证伪**（若成立）。**请务必自己验**，并说明你是否接受这个修法方向。
⚠️ #5 那种「结构上不可达所以用顺序锁代替夹具」的做法，请判它是**诚实的替代**还是**回避**。

### 3.4 ⭐⭐ **43/43 与「5 把自己的假锁」**

它自述：红集对账做了 **9 次变异**，最终 **43/43 把锁至少在一次变异下变红**；
过程中**发现并收紧了 5 把自己写的假锁**（「我写的断言，光靠最后那道兜底网就能满足」）。
最后一把（`directory_named_non_view`）它判定为**真的没有分辨力**（不是变异没生效），
依据两条自证：`apply.py` 每个锚点断言 `s.count(old)==1`（打不中就中止而非静默通过）+
同一变异下**同一测试函数的另两个参数变红**（⇒ 函数跑了、变异落地了）。修法 = 改成断言
`out_dir/0_reading/reading_checks.json` **不存在**（= 下游确实什么都没跑），复跑该变异 **8→9 红**。

⇒ 请判：**这个「变异确实生效了」的自证够不够硬**？以及 **43/43 这个口径本身**（锁的总数是怎么数的、
有没有把不该算的算进去）。⭐ 同族已登记：[[neuter-proves-wiring-not-discriminating-power]]。

### 3.5 ⭐⭐⭐ **另外独立找一遍缝**（⛔ 不许只复读它的 ③）

**判据**：找到**任何一条**能被静默消费或静默排除、或让账丢失的真实形态 ⇒ **阻断**。
⚠️ 它 ③ 打过的方向：文件系统形态（目录 / fifo / 不可写 `_run`）· 编码 · 声明值变体 · 入口顺序 · 递归深度。
⇒ **请换你自己的方向**（你上一轮在 G1 上自造 11 种形态级变异，正是这条要的东西）。

### 3.6 ⭐⭐ **N-A / N-B 本轮明令不做，请确认它确实没动**

- **N-A**（`DECLARED_SCHEMA_VALUES` 第二处手写清单）· **N-B**（`==43`/`==328` 语料快照常量）
  · **N-C / N-D / N-E** —— 派工单 §四 全部划为「登记不做」。
⇒ 请核：**它有没有顺手改了这些**（顺手改 = 超范围，即使改对了也应点名）；
以及 **`43`/`328` 两个硬断言在它的改动后是否仍然成立**。

---

## 四、验收判据（逐条给读数；⛔ 每条都必须有「会不通过」的情形）

| # | 判据 | 什么情况下会不通过 |
|---|---|---|
| **A1** | ⭐ **第一个动作**：独立跑全量 `python -m pytest -q -n 6`，summary 行**逐字**抄进裁决 | 有 failed/error；或无 summary 行（同机竞争假红 ⇒ 重跑一次再判）|
| **A2** | 三条阻断 × 三格（§3.1），**其中 ③ 由你另外找**（§3.5）| 任一格不成立 |
| **A3** | **每条新锁走生产入口还是 helper** —— 逐条点名 | 存在只调 helper 的锁却被当入口锁 |
| **A4** | **红集对账独立复核**（§3.4）：43/43 的口径、5 把假锁的收紧是否到位、最后一把的自证够不够硬 | 口径含糊；或收紧后仍无分辨力；或「变异生效」的自证不成立 |
| **A5** | ⭐ **§3.3 那 5 条独立验证**，并给出你对「`is_file()` 边界」这个修法方向的判定 | #1/#2 若不成立 ⇒ 说明施工方的论证有假；若成立 ⇒ 你上一轮处方需在裁决里更正 |
| **A6** | ⭐ **§3.2 两条自陈弱点定性**（嵌套声明 · `pipeline.py:528` 第二份拷贝）| 判定为阻断却被施工方留着 |
| **A7** | **超范围核查**（§3.6）+ `43`/`328` 兼容面仍成立 | 动了明令不做的东西 |
| **A8** | ⛔ **`.pth` 哨兵**：开工前与交件前各 `cat` 一次 `/opt/venv/.../_editable_impl_energyplus_agent.pth`，两次都必须是 `/workspaces/EnergyPlus-Agent-dev` | 变了 ⇒ 你这轮读数作废，**停下上报** |

⚠️ **A4 的注意**：[[neuter-proves-wiring-not-discriminating-power]] —— **变红只证接线**。

---

## 五、⛔ 明确不做

⛔ 不改代码（你是复核方）· ⛔ 不扩面到 F-97 以外（N-A…N-E 已划出）· ⛔ 不碰主树 ·
⛔⛔ **不许跑任何 `pip install`**（§〇）· ⛔ 不要为了让判据变绿而放宽它（见 §六 #2）。

---

## 六、⛔⛔ 停下上报触发器（**分层**）

> **事实依据**：本项目累计 **38 次「停下上报」，38 次都是派工方（orchestrator）的题错了**。**记功不记过。**
> ⚠️ 但也吃过不分层的亏（一处计数错让整轮复核空转两轮），故本条分层：

1. **题面与实测不符 —— 分两层**：
   - **(a) 承重前提错 ⇒ 停**：错了则整件事方向作废 / 判据不再有意义
     （例：被审 commit 不对、要审的机制不在这棵树里、**`.pth` 又被改走**）。
   - **(b) 外围事实错 ⇒ 记进「orchestrator 题面写错的地方」，然后【继续审其余】。**
   ⇒ **判别问法：这条错如果成立，我还需不需要审这份 diff？需要 ⇒ 走 (b)。**
2. **判据结构上不可能红**。
3. ⭐ **两个选项都次优但有第三条严格更优的路** —— ⛔ 别在我给的两条里硬选。
4. **要验它必须改被审对象之外的文件**。
5. ⭐ **你发现自己上一轮那三条阻断里有一条判错了 / 或处方本身有误**（§3.3 #1#2 正指向这个）
   —— **直说，本轮你没有任何维持一致的义务。**

---

## 七、⚠️ orchestrator 自认本单可能写错的地方（请优先证伪）

1. **§三里所有「它自述」的读数（43/43 · 9 次变异 · 5 把假锁 · 8→9 红 · 3113 passed · 495 行报告）
   我一条都没独立复跑**，只核过：提交链、树干净、报告确在 `HEAD` 里（`git show HEAD:<path>` = 495 行）、
   以及 `diff --numstat f2a8ccf HEAD` = `pipeline.py 53/5` · `vector_contract.py 165/25` · 测试 `582/0` · 报告 `495/0`。
2. ⭐ **施工方点名了我派工单里的两处题面错，我认，并已在此更正**：
   - 派工单 §四 写「不要动 `src/agent/pipeline` 以外的模块」，**与 BLK-A / BLK-C 的返工要求直接冲突**
     （那两条要改的 `_classify_rows` / `_declares_unregistered_schema` 就住在 `reading/vector_contract.py`）
     ⇒ **是我的题错**；`vector_contract.py` 的改动**在范围内，⛔ 不要当超范围记**。
   - 派工单里那句「裸跑会静默串台到**主树**」在它施工时**方向是反的**（`.pth` 当时指向 `/tmp/ep_f97`）⇒ 见 §〇。
3. **它的全量基线 `f2a8ccf = 3070 passed` 是沿用你上一轮的读数，它自己没重跑**（它自陈，且说改为核对算术
   + 9 次 neuter 的 `passed+failed` 恒 = 3113）。⇒ **请你判这个替代够不够**。
4. **§3.3 那 5 条我是从它的自述归纳的**，措辞可能不准，以它报告原文为准。
5. **它的 `3113 passed` 是在 `.pth` 指向 `/tmp/ep_f97` 的环境下跑的** —— 对它自己那棵树是自洽的，
   但**与你即将在 `.pth` 已还原为主树的环境下跑出来的读数，严格说不是同一个启动器**。
   ⇒ 若两者对不上，**先怀疑这个，别先怀疑代码**。同族 [[green-suite-is-a-property-of-tree-and-launcher]]。

---

## 八、交件形式

**把裁决写成文件**（⛔ 必须是文件，且写完再结束会话）：

```
/tmp/ep_f97/AI_agent/logs/reviews/verdict/2026-08-27_f97_rework2_glm_verdict.md
```

**结构**：总判（`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT`）·
§四 判据 **A1–A8** 逐条读数（⛔ 不许留占位符）· §三 六处逐条结论 ·
Findings（阻断 / 不阻断分开）· **「orchestrator 题面写错的地方」**一节 ·
你自己跑的全量 summary 行逐字 · **`.pth` 哨兵两次读数** · 交件时工作树状态。
