# 2026-08-01 · 主控参与项目生产 —— 全面接缝排查

> 承 [2026-07-31 SUPERVISION_CONTAMINATION.md](../2026-07-31_sm24_e2e_retry/SUPERVISION_CONTAMINATION.md)
> 与 CLAUDE.md §1.5 不变量 #7。执行人：主控 Opus 5。**本文只做排查与取证，不含修法施工**（修法归设计轮/派工）。

## 0. 判据与方法

### ⚠️ 0.0 判据更正（用户 2026-08-01 当场补充，**本文 v1 定性有误已改**）

主控排查 v1 用的判据是「把主控整个拿掉，产品仍须跑完并保质」。**用户当场校准，该判据过宽**：

> **现在是 dev 阶段，全流程需要主控来编排各个环节，这个是没问题的**（稳定之后考虑把主控代码化
> 或者模型降档化，那是开发后期的工程问题、不是现在的重心）。**绝对不可以的是主控参与各个环节内部的生产。**
> 即**拿掉主控整个流程跑不出来可以接受，但需要各个环节本身能完成输入到输出的过程**。
>
> **judge 同样是 dev 阶段辅助看开发质量的 agent**（主要为减少人工核对、判断各环节质量，
> 免得每次都要完全跑完端到端、节省成本），**目前不归属到项目本身的环节**；产品最终要不要引入
> judge 环节，最后工程化时再说。**所以目前主控兼任 judge 是可以的。**
> 但 **judge、主控都不能参与项目本身的生产**：**judge 可以全部打回盲重抽，但不能给任何信息 ——
> 相当于另外做一次，而不是原任务给反馈续作。**

**⇒ 修正后的判据（本文据此重新定性）**：

| 层 | 合法性 |
|---|---|
| 主控**编排**环节（建工作区 / spawn / merge / 跑确定性工具 / 决定跑什么） | ✅ 合法（dev 期） |
| 主控**兼任 judge**、判定某环节产物合格与否 | ✅ 合法（judge 是 dev 辅助，不属产品环节） |
| judge 不过 ⇒ **整轮盲重抽、零信息** | ✅ 合法（等于另外做一次） |
| **环节内部走不完输入→输出**（需要中途有人回答才能继续） | ⛔ **违规** |
| 主控/judge **把"哪里错了、该怎么改"送进环节内部**（含按子部分打回、原任务续作） | ⛔ **违规** |
| 主控的**判断**（而非固定档参数）成为某环节的输入 | ⛔ **违规** |

**v1 的两条头号"硬断"据此作废**（详 §2 附的更正说明）：识图段没有代码执行器、
判卷层没接模型 —— **两条都是"拿掉主控流程跑不出来"，属可接受，不是违规**。

### 0.1 方法

**方法**：不看文档声称，只读代码与真实 run 产物。三条追问逐段过：
1. 这一段的**执行器**是谁？是代码/LLM 调用，还是主控手动动作？
2. 这一段的**门**是谁在判？门的**阻断层**里到底有什么？
3. 这一段吃的**输入**里，有没有主控当轮生成的内容？

**取证基准**：`case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/`（07-30 那份**质量 1/8**、
但被系统 accepted 的真实识图 attempt 003）。它是现成的天然对照：一份公认不合格的产物，
在无主控判卷的情况下系统会怎么处置。

---

## 1. 一句话结论（按 §0.0 修正判据重写）

**违规只有一处，但它是结构性的：识图这个环节自己走不完输入 → 输出。**

- **⛔ 唯一真违规 = 识图被设计成「中途停下等主控回答，然后拿着主控给的具体错处续作」。**
  不是偶发操作习惯，是**三处机制同时钉住的**：产品 skill 库里写着 *"Stop and wait for review"*（§D-2）、
  隔离层有专门的 `feedback.md` 注入点并提示 *"read it FIRST"*（§D-2）、
  主控每轮现写 198 行 directive 投喂上一轮的失败教训（§D-1）。
  **07-07 那个 8/8 正是这么来的**（pilot r1 被主控告知「锚标错了 / 候选没逐条核 / 字段全空」，r2 才达标）。
  按用户口径这属于「原任务给反馈续作」，不是「另外做一次」。
- **✅ 不构成违规（v1 定性有误，已更正）**：识图段没有代码执行器、判卷层没接模型、主控兼任 judge、
  主控跑预扫这个动作本身 —— 按 §0.0，**dev 期编排合法**，属后期工程化事项。
- **⚠️ 另一类真问题，性质不是「违规」而是「judge 成本」**：把 sm24 的 **8/8 满分**识图与 **1/8** 识图
  各跑一遍最严格档 gate①，**阻断层结论逐字相同、都是 0 block**（详 §S-0）。
  确定性层对识图质量的**分辨力是 0** ⇒ **它替 judge 分担不了任何东西，主控每轮必须亲自看图**。
  这正打在 judge 的设立目的（减少人工核对、免得每次跑完端到端）上 ⇒ **是改进动机，不是违规**。

---

## 2. ~~硬接缝~~ → **合法的 dev 编排**（v1 误判，§0.0 更正后作废）

> **⚠️ 本节两条在 v1 被列为「⛔ 硬接缝·拿掉主控直接断」。按用户 08-01 校准的判据，
> 「拿掉主控整个流程跑不出来可以接受」⇒ 两条均 <u>不构成违规</u>。**
> 证据保留在此，因为它们精确刻画了「主控现在到底在替哪些还没写出来的组件干活」，
> 是**后期工程化（主控代码化 / 降档化）的输入清单**；但**不是今天要修的东西**。

### H-1 · 识图段没有代码执行器，主控在编排位上顶着 ✅合法（后期工程化事项）

| 证据 | 内容 |
|---|---|
| [`run_stage.py:162`](../../../../scripts/tool_scripts/run_stage.py#L162) `_draw_reading` | docstring 原文 *"0_reading is MANUAL: validate the already-produced view JSONs (no LLM)"* —— 这一段的"draw"函数**只做校验，不生产** |
| [`run_stage.py:1747`](../../../../scripts/tool_scripts/run_stage.py#L1747) `_print_reread_protocol` | 需要重读时，flow 做的事是**打印一段给人看的协议**：「1. Spawn a fresh isolated cold-start sub-agent…」 |
| [`run_stage.py:2195`](../../../../scripts/tool_scripts/run_stage.py#L2195) | `--reading-runner-available` 的 help 原文：*"the main Agent still runs the sub-agent protocol"* —— **旗标自己承认 runner 是主控** |
| [`spawn_isolated_reader.py`](../../../../scripts/tool_scripts/spawn_isolated_reader.py) | `spawn` 子命令**默认只打印命令行**（`--execute` 才真跑）；build / spawn / feedback / merge 四步全是人敲的 CLI |
| [`isolation.py:401`](../../../../src/agent/execution/isolation.py#L401) `spawn_command` | 全仓唯一调用方就是上面那个 CLI；**没有任何编排代码调用它** |
| `scripts/run_full_pipeline.py` | 入口参数是 `--reading-from <已有目录>` —— 连"全流程"入口也假设识图已经存在 |

**判定（更正后）**：主控在**编排位**上顶着一个还没写出来的组件 ⇒ **合法**。
留作后期工程化的输入清单：要把主控代码化，这六处就是待补的接线。

### H-2 · gate② 判卷没有接模型，只会"停下等人" ✅合法（judge 属 dev 辅助）

| 证据 | 内容 |
|---|---|
| [`step_orchestrator.py:13`](../../../../src/agent/execution/step_orchestrator.py#L13) | 编排器 docstring：*"judge stage (J0/J1 enabled) → **STOP: AWAITING_JUDGE**"*；开篇写明这是 *"a per-stage BLOCKING loop **the main Agent drives turn by turn**"* |
| [`executor.py:56`](../../../../src/agent/judge/executor.py#L56) `judge_fn` | 可插拔的模型调用位。全仓 `grep judge_fn` 的**生产调用只有两处**（`run_stage.py:1813` / `:2023`），**都是 `judge_fn=None` 且都是已 disabled 的 J4** ⇒ **J0/J1 从未接过任何模型** |
| [`verdict.py`](../../../../src/agent/judge/verdict.py) + [`score_policy.py:1`](../../../../src/agent/judge/score_policy.py#L1) | 代码侧**已经有**能出 pass/fail 的机器判据（`V3PolicyVerdict`），但 score_policy 开头就写死：*"These suggestions are evidence for gate②, **not an automatic verdict**… kept out of StageVerdict **on purpose**"* ⇒ **不是没能力，是设计上明令禁止自动化** |
| `new_case_guide.md` §0 表格 | judge② 那一行的"谁"字段直接写 **「你」** |

**判定（更正后）**：judge 是 dev 期辅助、不属产品环节 ⇒ **主控兼任合法**，本条不是违规。

**⚠️ 但有一条约束因此变硬，且正是今天要修的东西**：既然 judge 合法地由主控担任，
那么**唯一的红线就落在 judge 的出口形态上** —— 用户口径：
**「judge 可以全部打回盲重抽，但不能给任何信息，相当于另外做一次，而不是原任务给反馈续作。」**
⇒ judge 判不过时，系统允许的动作**只有一个**：整轮丢弃、零信息重来。
现有的 `feedback.md` 通道（§D-2）恰恰实现的是被禁的那一种。

**⚠️ 顺带记一条不必今天处理的**：判卷现在背着两个身份 ——
**(A) dev 期评测尺**（有 gt，可代码化，能省主控人工核对）；
**(B) 未来产品若引入的质量门**（无 gt）。用户已明确 **(B) 属最后工程化时再议**，
本轮**不展开**；但 §S-0 的实证说明 (A) 现在也几乎没有被确定性层分担。

---

## 3. ~~软接缝~~ → **judge 的成本与可靠性问题**（不是违规，是改进动机）

> **⚠️ 定性更正**：v1 把本节列为「跑得完但质量门是空的」，隐含"产品需要这些门"。
> 按 §0.0，产品要不要质量门是后期工程化议题。**本节的真实意义变为**：
> 确定性层几乎不替 judge 分担任何判断 ⇒ **主控每轮必须亲自看图**，
> 与 judge 的设立目的（减少人工核对、免得每次跑完端到端省成本）直接冲突。
> 证据与数字全部有效，只是**归类从「违规」改为「dev 效率/可靠性」**。

### S-0 · ⭐⭐ 判决性实证：gate① 对「8/8 满分」和「1/8 几乎全错」给出**逐字相同**的阻断层结论

同一个 case、同一份检查代码、**最严格档**（`run_profile=regression`，fail-closed），
把 sm24 两份历史识图各跑一遍 `check_reading_view`：

| 产物 | 坐标级质量（GT 八道隔墙 · 容差 0.30 m） | invariant（阻断层） | cross_check（非阻断） | **blocking fails** |
|---|---|---|---|---|
| `run_2026-07-07_haiku_cv_probe` | **8/8 满分** | 44 pass · 1 NA | 18 pass · 26 NA · **6 fail** | **NONE** |
| `run_2026-07-27_haiku_e2e/attempts/003` | **1/8**（还多画 10 道、平面窗 11→0） | 44 pass · 1 NA | 12 pass · 32 NA · **6 fail** | **NONE** |

**阻断层结论完全一致，连非阻断的 fail 条数都同为 6。**
两者唯一的差别落在非阻断层的 pass/NA 配比（18/26 vs 12/32）——
**而且方向是反的：质量更差的那份，NA 更多**（漏做的活越多，被自动豁免的检查越多，见 S-2）。

⇒ **确定性门对识图质量的分辨力 = 0。** 这就是判据的直接答案：
拿掉主控之后，不是"质量下降"，是**根本没有任何东西在看**。

> 复算方式：直接调生产函数 `check_reading_view`，两份产物同参数。
> 与产物里存档的 `checks.json`（46 条 invariant）差 2 条，是因为 `isolation_provenance_bound` +
> `view_manifest_coverage` 由外层 `check_reading_stage` 追加、不属本函数——**两侧同口径，比较成立**。

### S-1 · 识图 gate① 的阻断层里没有一条准确度检查 ⭐实证

从真实产物 `run_2026-07-27_haiku_e2e/0_reading/attempts/003/checks.json` 逐条拆层：

| 层 | 条数 | 内容 |
|---|---|---|
| **INVARIANT（阻断）** | 11 类 / 46 条全 pass | `stroke_ids_unique` · `dimension_ids_unique` · `dimension_parseable` · `pen_kind_valid` · `nondegenerate_geometry` · `axis_endpoint_consistent` · `no_topology_fields` · `facade_fields` · `uncaptured_present` · `view_manifest_coverage` · `isolation_provenance_bound` |
| **CROSS_CHECK（只留痕、不阻断）** | 9 类 / 45 条（28 NA · 11 pass · 6 fail） | `dimension_chain_closure` · `dimension_derived_refs` · `stroke_dimension_consistency` · `partition_on_window_jamb` · `stroke_provenance_coverage` · `dimensions_present` · `dimension_p1a_fields` · `door_heal_traced` · `raw_field_presence` |

**阻断层 11 类全部是"这份 JSON 长得对不对"，没有一条是"画的跟图纸对不对得上"。**
⇒ 那份 **8 道隔墙只对 1 道、还多画 10 道、平面窗数从 11 掉到 0** 的识图，
gate① 结论是 **0 block**，正常 accepted 进下一段。

### S-2 · 恰恰是针对头号失败模式的那条检查，被同一个失败自我解除了 ⭐

[`reading.py:997`](../../../../src/validator/checks/reading.py#L997) `_partition_on_window_jamb`
就是专门抓「把窗垛当隔墙」的——07-30 的失败形状一模一样。它在那份产物上的实际结论是：

```
not_applicable   cross_check   1f_view.reading.partition_on_window_jamb  ::  no window jamb geometry
```

**因为这份识图一个平面窗都没画**（`pens: {'wall': 15}`，window 0 条），
所以"窗垛坐标"集合是空的，检查直接 NA。
**一份产物漏掉某类要素，就自动豁免了那条专门抓"把该要素错认成别的东西"的检查。**
这类自我解除是结构性的，不是这一条的个案。

### S-3 · 尺寸链证据层被 case 声明缺件整层关掉

[`reading.py:478`](../../../../src/validator/checks/reading.py#L478)：`dimensioned` 为假 ⇒
`dimensions_present` + `dimension_p1a_fields` 两条直接 NA。
该旗标来自 **case 元数据**（[`case_metadata.py:51`](../../../../src/agent/execution/case_metadata.py#L51)
读 `testdata_prompt.json` 的 `dimensioned_views` / `Floor plans[].dimensioned` / `views{}`）。

**实测 sm24 的 `case_data/testdata_prompt.json` 里没有任何 `dimensioned` 声明**
（只有 `Floor plans` 的 path + thermal_zones + 四个立面 path）。
⇒ 五个视图 × 2 条 = **10 条尺寸证据检查在 sm24 上永久 NA**。
而 sm24 的图**是带完整尺寸链的**（07-07 那轮转录了 51 条；GT 就是从 DXF 尺寸链建的）。

⇒ **项目当前的旗舰 case，最强的那层 gate① 证据从头到尾没开过**，没人发现，因为主控在用眼睛判。

### S-4 · provenance 只查"有没有填"，不查"填的是什么分布" —— 且代码**明写**把这活交给主控 ⭐

[`reading.py:849`](../../../../src/validator/checks/reading.py#L849) `stroke_provenance_coverage`
只判断结构笔画是否**都带了** provenance 字段，**不看取值分布**。
⇒ 07-30 那份「15 条墙 100% `dimension_derived`、零条实测」的产物，这条检查是 **pass**。
07-31 只好把「全 dimension_derived 即违规」写进**主控当轮的 directive**（下面 D-1）——
即用主控的临时投喂顶替了一条本该在代码里的检查。

**⭐ 而这不是疏忽，是写在注释里的分工**——同一函数
[`reading.py:829`](../../../../src/validator/checks/reading.py#L829) 的 docstring 原文：

> *"…flag plan-wall coordinates that sit exactly on dimension-chain cumulative positions.
> **This is advisory only**: a real wall can be dimensioned, so **J0 must verify the rendered/source
> image evidence.**"*

即：确定性层遇到"需要看图才能定"的事，**显式地把判定权交给 J0**；而 J0 的唯一实现是主控（§H-2）。
**这是整个软接缝群的病根的书面形态**：gate① 每遇到一处判不了的，就写一句"交给 judge"，
而 judge 从来就是主控。逐条清接缝时，**这类"advisory only + 交给 J0"的注释就是接缝的普查线索**。

**按该线索普查 `src/validator/`（全仓确定性门），显式"降级为 advisory / 交给 gate②"共 3 处**：

| 位置 | 降级的是什么 | 理由（原注释） | 定性 |
|---|---|---|---|
| [`reading.py:831`](../../../../src/validator/checks/reading.py#L831) | 墙坐标恰落在尺寸链累加位置 | 真墙也可能被标注 ⇒ 要看图 | **接缝**（J0=主控） |
| [`reading.py:562`](../../../../src/validator/checks/reading.py#L562) | 门洞 heal 未留 `uncaptured` 痕 | 缺审计注释不破坏几何 | 轻，可留 |
| [`correction.py:594`](../../../../src/validator/checks/correction.py#L594) | view/global 级证据债 | 映射不到具体 cell/window ⇒ 即使严格档也只 advisory | **接缝**（无人接手） |

数量不大 ⇒ **逐条清是可行的，不是无底洞**。另一个方向的线索是 `CheckLayer.CROSS_CHECK` 本身
（识图 9 类、见 S-1 表），那是"层级默认非阻断"，与显式降级不同源，需分开处理。

### S-5 · 几何人工确认门可一键旁路

[`run_stage.py:2060`](../../../../scripts/tool_scripts/run_stage.py#L2060)：`--geometry auto`
直接 `approve_geometry(actor="flow:auto", policy="auto")` 盖章通过。
`--record` 只在 **golden** 档打印一句 `⚠ …human HTML review is recommended`，不阻断。
公平起见记全：`--geometry` **默认是 `required`**（`auto` 是显式选进的旁路，且留审计字段）；
但人工校验开关 `--review` **默认空 = 全关**（[`run_stage.py:2236`](../../../../scripts/tool_scripts/run_stage.py#L2236)）。
⇒ 这三个门都是"有人在才存在"的门。**这一条定性是"人的门"不是"主控的门"**，
但它同样落在判据里：拿掉人和主控之后，几何一层只剩 gate①。

---

## 4. 输入污染接缝 —— 主控当轮生成的内容进了产品输入

（07-31 已自查出三条，本轮复核全部成立，并补一条。）

### D-1 · per-run directive（**违规**，且已被当成缺陷的止痛药在用）

[`isolation.py:410-415`](../../../../src/agent/execution/isolation.py#L410)：
`--directive <FILE>` 的内容被**直接拼进 spawn prompt**（标题 *"Per-run directive (binding for this run)"*）。

本轮实况 [`reader_directive.md`](../2026-07-31_sm24_e2e_retry/reader_directive.md) = **198 行**，
七节，其中 §2「测量产生笔画、尺寸链只能佐证」+ §4.7「缺席必须先用探针证明」
**是主控看着上一轮的失败形状当场写的**。

⚠️ **两处后果，必须一起看**：
1. 它是主控对**上一轮具体错法**的针对性投喂 ⇒ 违反用户口径。
2. 它同时是 **S-4 那条缺失检查的替代品** ⇒ 就算把 directive 整个删掉，那条约束也不该消失，
   **该沉淀成代码里的门或 standing 文档**。删 directive 与补门必须成对做，否则是纯退化。

### D-2 · pilot → 主控反馈 → 返工（**违规**，且被写进了随产品发布的 skill）

- 机制位：[`isolation.py:254`](../../../../src/agent/execution/isolation.py#L254) `write_feedback` +
  [`:416`](../../../../src/agent/execution/isolation.py#L416) spawn 时自动附
  *"A review of your previous output exists at feedback.md — **read it FIRST**"*。
- **更严重的是**：这个假设**不在 dev 脚手架里，而在产品的 skill 库里**——
  [`skills/intake_pipeline/0_reading/session_kickoff.md:66-68`](../../../../skills/intake_pipeline/0_reading/session_kickoff.md#L66)：
  ```
  2. Do one pilot image first.
  3. Stop and wait for review of that pilot; do not batch remaining images yet.
  ...
  80: Do the pilot first, then stop and wait for feedback.
  ```
  `skills/` 是**随产品运行时加载的规则库**（CLAUDE.md §5#5）。
  ⇒ **上线之后，读图器仍然会被自己的启动文件命令"停下来等审阅"**——
  这正是 07-31 pilot r2 输出 *"Would you like me to continue…"* 的直接原因。
  **不是模型不会做，是产品文档叫它停。** 全仓 grep，`skills/` 里这类假设**仅此一处两句**，其余干净。

### D-3 · 预扫：跑它＝编排（合法）；**看着结果临时挑参数＝生产（违规）**

- 预扫本身是确定性代码（`cv_probe.py prescan-plan/-elevation`），不含更强 agent 的判断；
  **主控跑它属编排** ⇒ 按 §0.0 **合法**（v1 曾把"不在自动编排里"记为问题，按新判据作废）。
- **⛔ 违规的是参数**：档位若由主控**看着这张图的预扫结果临时挑**，
  主控的视觉判断就通过候选集进了识图环节的输入。07-30 的 `--no-cc` 即主控当场加的（已如实登记）。
  ⇒ 必须是**固定档**：写死在代码/配置里，按图类（clean vector CAD / 扫描件）分档，不随轮调。
- **同族债（plan.md 已登记第 3 条，本轮复核成立）**：收窄档 `--min-strength 0.08 --min-line-len-px 30`
  写在 [`cv_toolbox.md:52`](../../../../skills/intake_pipeline/0_reading/cv_toolbox.md#L52)——**那是给读图器看的文档**，
  而预扫是主控/管线跑的，`new_case_guide.md` 从未提及 ⇒ **这个纪律写给了错的角色，从未被执行过**。

### D-4 · 污染闸门本身是纯词法（新补，plan.md 第 5 条同族）

[`isolation.py:244`](../../../../src/agent/execution/isolation.py#L244) `check_feedback_text`
是 directive / feedback 两条通道**共用**的唯一闸门，而它只做词法禁词扫描。
⇒ 它能挡住「gt」「answer」这类词，**挡不住一句"北边那道墙你画到 4.18 上去"**——
裸坐标、具体错处、无禁词的自然语言全部放行。
**主控的自律是这条通道当前唯一的真实约束。**

---

## 5. dev-only 合法接缝 —— 不在判据内，重设计时别误伤

这些是**评测侧**资产，上线本就不存在，主控/人参与它们**不违反不变量 #7**：

| 接缝 | 为什么合法 |
|---|---|
| gt 编写 / 转正 / 签字（`gt_promote.py` / `gt_review_sign.py` / `gt_from_dxf.py`） | gt 是判卷专用、prod 无答案（不变量 #4） |
| judge 侧车 `view_bindings.json` 人工定稿（guide §0.3） | judge-only 资产，明令不可由产品输出反推 |
| `report/REPORT.md` 的 AGENT 区 + 四桶建议 | 给用户看的开发报告，不是产品产出 |
| 派工 / 审阅 / 裁决 / 管理文档 | 主控作为**开发助手**的本职（不变量 #7 原文允许） |
| run_config.yaml / llm.yaml 的**存在** | 属产品配置；但**默认档必须随产品发布**，不能每轮现挑（与 D-3 同理） |

**注意边界**：`view_manifest` 是从 case 元数据确定性派生的
（[`view_manifest.py:54`](../../../../src/agent/execution/view_manifest.py#L54) 明确的声明族表 + 未分类图硬门），
**不是主控手填** ⇒ 合法，不必动。

---

## 6. 汇总表（按 §0.0 修正判据重新定性）

### 6.1 ⛔ 真违规 —— 今天要修的全部内容

| # | 接缝 | 违的是哪一条 | 修法方向（不定死） |
|---|---|---|---|
| **D-2** | pilot 停等 review + `feedback.md` 续作通道；**且停等假设写在产品 skill 库里** | 「环节自己走不完输入→输出」+「原任务给反馈续作」 | 取消两段式 → 一次读完全部视图；`feedback` 通道下线或改造为**只能承载"整轮作废、重来"这一个比特** |
| **D-1** | per-run directive（198 行，主控看着上轮失败当场写） | 「主控参与环节内部生产」 | 内容一分为二：**属通用纪律的沉淀进 standing 文档随产品发布**；**属针对上轮错法的删除**。⚠️与补门成对做（见下） |
| **D-3b** | 预扫参数由主控看着结果临时挑（`--no-cc` 等） | 同上（主控判断经候选集进输入） | 定死为按图类分档的固定参数，随产品发布 |
| **D-4** | 污染闸门 `check_feedback_text` 纯词法，挡不住裸坐标/具体错处 | 上述三条的唯一约束形同虚设 | 与 D-1/D-2 同批处理；若通道整个下线则本条自然消解 |

**⚠️ D-1 的连带约束（不能只删不补）**：directive 的 §2「测量产生笔画、尺寸链只能佐证」与
§4.7「缺席必须先用探针证明」，实质是在**替代 S-4 / S-2 两条代码里缺失的门**。
**删 directive 与补门必须成对做**，否则是纯退化。

### 6.2 ✅ 合法（v1 误判，已更正）—— 今天不动

| # | 接缝 | 为什么合法 |
|---|---|---|
| H-1 | 识图无代码执行器，主控在编排位顶着 | dev 期编排合法；「拿掉主控跑不出来」可接受 |
| H-2 | gate② 未接模型、主控兼任 judge | judge 是 dev 辅助、不属产品环节 |
| D-3a | 主控手跑预扫这个**动作** | 确定性代码 + 编排位 |
| S-5 | 几何 3D 确认门 / 人工校验开关 | 人的门，dev 期辅助，同 judge |

### 6.3 ⚠️ 不是违规，是 judge 的成本与可靠性（改进动机，排期另议）

| # | 接缝 | 后果 |
|---|---|---|
| S-0 | gate① 对 8/8 与 1/8 阻断层结论**逐字相同** | 确定性层分辨力 = 0 ⇒ 主控每轮必须亲自看图，与"减少人工核对"的初衷冲突 |
| S-1 | 识图阻断层 11 条全是结构类 | 同上的成因 |
| S-2 | 抓「窗垛当墙」的检查被"漏画窗"自我解除 | 头号失败模式没有确定性抓手 |
| S-3 | sm24 case 未声明 `dimensioned` ⇒ 10 条检查永久 NA | 最强证据层从没开过。**修法极小，可顺手做** |
| S-4 | provenance 只查有没有、不查分布 | 「15 条墙零实测」畅通无阻 |

---

## 7. 排查过程中确认为「不成问题」的（避免重复排查）

- **1_correction / 4_mep**：走 `llm.yaml` 的独立 LLM 调用，`_make_draw_fn`
  （[`run_stage.py:597`](../../../../scripts/tool_scripts/run_stage.py#L597)）里是真执行器，**无主控参与**。
- **2_modelling / 3_split_pairing / 5_intakeoutput / EP**：确定性代码，无主控参与。
- **盲重抽纪律**：`draw_fn(None)` 有注释 *"blind: never inject judge/feedback in the loop"*
  （[`step_orchestrator.py:251`](../../../../src/agent/execution/step_orchestrator.py#L251)），
  judge 评语确实不回灌 prompt ⇒ **这条纪律是真的**。污染走的是 directive / feedback 两条**旁路**，不是重抽通道。
- **skills/ 其余五段**：grep `wait for|ask me|orchestrator|reviewer|stop and`，
  除 D-2 那两句外**零命中**，规则库其余部分不含监督假设。

---

## 8. 留给设计轮的问题（本文不预设答案）

**已由用户 08-01 答掉的**（不再是问题）：
- ~~判卷两个身份怎么拆~~ ⇒ judge 属 dev 辅助，产品要不要 judge **最后工程化时再议**，本轮不展开。
- ~~pilot 两段式存废~~ ⇒ 由「judge 只能整轮盲重抽、不能反馈续作」直接推出：**中途 review 点必须取消**。
- ~~几何门定性~~ ⇒ 人的门，同 judge，dev 期辅助，合法。

**仍然开放**：

1. **取消 pilot 之后，质量自检靠什么承接**？standing 自检清单（写进 skill，随产品发布）/
   整轮盲重抽 / 两者叠加？各自成本与可达质量？
2. **S-1/S-2/S-4 的共同病根**：现有 cross_check 层是"有证据才判"，于是**漏做的活自动免检**。
   要不要反过来 —— **"该有的证据没有"本身就是阻断项**（缺席必须证明）？
   这正是 D-1 §4.7 那条 directive 想干的事，**把它从投喂改成门** ⇒ 这是 D-1 "只删不补"风险的解。
3. **重抽机制的预算**：judge 不过 ⇒ 整轮盲重抽零提示。每轮成本 ≈ 一次冷启，
   上限设几轮？超限之后怎么处置（quarantine 交人？）
4. **无监督真实基线是多少** ⇒ **用户 08-01 拍板：先跑这个**。
   在拿到该基线之前，任何"质量恢复了"的判断都没有依据。
5. **D-1 的拆分判据**：directive 里哪些属"通用纪律应沉淀"、哪些属"针对上轮错法应删除"？
   需要一条可机械判定的界线，否则下一轮又会以"这条是通用纪律"为名把投喂放回去。
