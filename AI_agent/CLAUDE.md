# 多模态输入 Agent 项目管理文档

> **本文件 = 项目最基础的根文件**，每次会话/换主控模型时首加载，作用是**简要说明项目结构 + 当前开发状态**。
> 只放长期稳定的"是什么"和此刻的"在哪"；**待办看 [plan.md](plan.md)，历史决策看 [decision_log.md](decision_log.md)，
> 当前架构细节看 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)，标准工作流看 [guides/new_case_guide.md](guides/new_case_guide.md)。**
> 三者职责互斥：**本文不叠历史、不堆待办**——翻篇的日更与状态摘要一律进 [logs/worklog/](logs/worklog/)，操作手册进 `guides/`。

> **⭐ agent 术语 banner（2026-08-02 用户定，全项目唯一口径）**：端到端主控 = **orchestrator**（只能启动与接收）·
> 子环节内部的**调度** = **`<子环节>-agent`**（如 **`reading-agent`**，即旧称「内部 controller」）·
> 子环节内部**实际执行某功能**的 = **`<子环节>-<功能>-agent`**（如 **`reading-worker-agent`** = 读图并产出观测的 VLM，
> 不叫 vision 是因为它不止看图、还产出）。**新写文档一律用此表**；历史叙述保留原文。
> 起因 = 「主控 / controller / worker」三词指代不一，多次造成排查分类错误。

> **术语 banner（当前唯一口径）**：管线 = **0_reading**（识图）→ **1_correction**（校正,LLM）→
> **2_modelling**+**3_split_pairing**（几何内核,代码）→ **4_mep**（物理,LLM）→ **5_intakeoutput**（装配,代码）。
> 代码入口 `src/agent/pipeline.py:run_pipeline`。**历史叙述（decision_log / logs / archive）沿用旧称**——
> phase1=0_reading / phase2a=1_correction / phase2b=2_modelling+…+5_intakeoutput / `run_phase2`→`run_pipeline`。

---

## 0. ⭐⭐⭐ 项目定位与开发治理（2026-08-18 用户拍板 · **冲突时压过本文 §5 全部流程条款**）

> **本项目 = 科研项目。P0 = 快速迭代 / 快速开发 / 快速跑通。**
> 产品化、工程化（完备的防御面、无懈可击的边界、全覆盖的锁）**是最后一步的事，不是每一步的事**。
> 用户原话：「不需要每一步都考虑得特别完善周全」。

**立此条的事实依据**（2026-08-18 清点，非印象）：07-08 → 08-18 共 **41 天、35 次跑**，
其中 08-13 起的 **25 次全部标注「诊断 / 非成绩 / 作废」**；同期 `guard.py` 长到 **1490 行**、
全仓 **2255 把测试锁**、测试 **60845 行**对源码 **70601 行**。**围栏在长，科研问题一步没动。**
（前情：用户 08-18 收工时提出「照这样下去不是每次改别的东西都要回过头来一点点修？」，
orchestrator 当时判读为「病灶更窄 = 一个护栏类型选错」——**该判读被本条上位口径覆盖**，
但其中一句保留有效：测试锁在 08-18 一天里三次抓住 orchestrator 自己的手滑，
**这类锁便宜、不该一刀切减** ⇒ 故本条给的是**分档**，不是一律减。）

### 0.0 ⭐ 当前第一目标（2026-08-21 战略换挡 → 2026-08-23 细化）

> **跑测的目的 = 升级 harness，不是拿分。分数只是 harness 硬不硬的读数。**

⛔ **~~「恢复到 07-07 的水平」（2026-08-18）已作废~~** —— 被 08-21 用户当面换挡覆盖：
**不再纠结复原 07-07**，改为把历史好 reading 沉淀进现行 harness；
**三种 reading 模式作废**（模型强度是连续刻度，不是并列赛道）。
⛔ **硬约束**：harness 只做**增量升级、不为新 case 特化**。

**⭐⭐⭐ 本批目标（2026-08-26 用户重申，当前唯一口径）**：
> 「我们这批的目标是要把**新分工的 harness**、以及**新分工的判分**、以及 **gt 修正 / gt 出判分答案** 全部落地。」

⇒ **三件事必须都落地才算这批完成**，⛔ 不是三选一：
**① 新分工的 harness**（reading + correction 一体改）· **② 新分工的判分**（grade 要跟新分工对得上 ——
⭐ **reading 产物变了、correction 产物没变**，这是判分改造的分界线）· **③ gt 修正 + gt 出判分答案**。

**本批（分支 `08.23_AsDrawnReading`）的三条目标**（2026-08-23 用户定）：
1. **实现 reading、correction —— 代码与模型两轴的新分工**
2. **对应的 gate、judge 跟上**
3. 继续推进 harness。验收 = **sm21 / sm24 / sm25**；**先探索性做好并完整跑过一遍**，⛔ **不着急降模型智力**

⭐ **执行次序（2026-08-25 用户定，覆盖此前的「先做 sm25」）**：
**① 支线回并 → ② 统一按新 reading 做 → ③ 新 reading 落地后先拿 sm25 全流程撞通。**
理由 = 拿旧格式 reading 测出来的结论，新 reading 落地后还得重测一遍。
⭐⭐ 且用户定死：**「新 reading 本身就和 correction 是一体的，要一起改」** ⇒ ⛔ 不许只改一边。

⇒ **⭐ 展开与硬纪律全在 [guides/reading_correction_split_guide.md](guides/reading_correction_split_guide.md)**
（用户令「这条线上的开发都先读这份指南」）。
凡不服务这三条的工作**一律登记进 [plan.md](plan.md) 不做**（同 §0.1）。

> ⭐ **此刻在哪（2026-09-06 · 第六程 · 已收工）**：**B1 / B3 / F-158 / B4 / T4-a / B2 / A-11 / A-6 八条线在主线**，
> 权威全量 **`3907 passed / 0 failed`**（`3907+2+13=3922` 逐位闭合 = 独立 collect，`.pth` 前后哨兵同值且指主树）。
> ✅ **本程合并两条**：**A-11 gt 按 1 mm 规整入库** · **A-6 刻度认领整条线**（A-6a+A-6b，含返工 1）——
> 两条都是跨家族审 `APPROVE-WITH-FINDINGS / 阻断 0`。
> ⭐⭐⭐ **本程最大的方法论收获**：**返工题从【修这个例子】提到【枚举这一类】** ——
> 复核方按症状只找到 1 个洞，逐项枚举找出**另外 6 个**（详见 §2 第六程 banner ④）。
> ⇒ **挡路新单 2 个**：**J-判分改造**（⭐ **无阻塞，下轮直接开**）·
> **E-a 端到端接线**（⛔ **阻断中** —— 09-06 实测「这是接线」的前提不成立，见 banner ⑨，**需先拍源契约口径**）。
> + **两处卡用户**（G-a gt 人签台账〔⭐ 按你 08-28 定的，排在这批改造完之后，⛔ 不是现在等你签〕 · E-b 跑前配置拍板）。
> ⛔⛔ **三条最要紧的 debt**：**F-1 生产帧【平面几何】零 gt 对账** · **F-7 绑定校验量声明不量载荷** ·
> **A-11-d2 `SM25_DEFERRED_CAVITY_COUNT` 是代理量**（下次任一成因变化前必须先拆 per-code）。
> ⭐ **下程第一件事见 §2 第六程 banner ⑧。**

### 0.1 唯一判断法则

凡要加一道防御 / 补一个边界 / 写一批锁 / 补一轮审，先问：

> **「不做这件事，下一次跑测能不能跑起来、结果能不能读？」**

**能 ⇒ 登记进 [plan.md](plan.md)，不做。** 不能 ⇒ 才做，**且只做到「能跑能读」为止**。

### 0.2 三档口径（当前的病 = 所有 run 都按最高档要求）

| 档 | 用途 | 门 | 审 | 锁 |
|---|---|---|---|---|
| **探索档**（默认）| 撞墙、找现象、n=1 诊断 | **只记录不阻断** | 免 | 免 |
| **工程档** | 改管线内核 / 交接契约 / 校验器 | gate① + 全量绿 | 同族自审 | **只锁契约与几何不变量** |
| **成绩档** | 正式 case 成绩、对外结论 | 全门 + 强隔离 | 跨家族 | 全 |

**默认档 = 探索档**；升档必须**显式声明并写进该 run 的 README**。
⛔ **反向铁律（分档能成立的唯一前提）**：**探索档的产物永远不得记成成绩。**
放松防线之所以无害，正是因为它产出的东西本来就不进成绩账——一旦破这条，整个分档立刻失效。

### 0.3 四条不降档（便宜、且是根）

1. **gt 铁律**（§1.5#4）——成绩可信度的根，动它等于全部历史成绩作废。
2. **收工 ritual**（§5#12，含 **§0.5 的体量自检**）——换会话即失忆，管理文档是唯一跨会话通道；读不动等于没有通道。
3. **用户拍板必须白话**（§5#13）。
4. **几何 / 交接契约不变量**（§1.5#1 / #2 / #3 / #6）。

### 0.4 本次拍板的四项即时后果（2026-08-18，均已落地）

1. **读图器沙箱围栏（`guard.py`）→ 探索档默认「只记录不拦截」**（`guard_profile="observe"`：
   按 strict 原样判、只把「本来会拦」记成 `shadow_decision` 不阻断 ⇒ 摩擦归零而摩擦测量照收）。
   ⛔ **「专用低权用户 + 权限位」已被用户当场否掉，不做** —— 隔离要防的只有 **reading 抄答案**，
   而每个 run 本来就新建独立空间（`tempfile.mkdtemp` + `_require_outside_repo` 硬校验必须在仓库外）、
   **答案本来就不在里面** ⇒ **物理隔绝已成立**。用户原话：「每一次新 run 都单独新建一个空间就行了，
   物理隔绝就好了，**不要一道道规则去防**」。**主控泄答案**风险用户判定不大（档位高 + 介入留记录）。
   完整论证（同族缺陷 F-49→F-62 六次现形等）逐字搬入
   [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)。
2. **复审债按新分档重新分类**：只保留**碰管线内核 / 交接契约 / 成绩产出路径**的那几笔；
   围栏、脚手架、测试工程、诊断工具类的复审债**直接销账**（不是补审，是重分类）。
3. **主控（orchestrator）可直接改**：探索档脚手架、诊断工具、日志、`AI_agent/` 管理文档。
   **仍须派工 + 换人审**：`src/agent/pipeline` 内核、交接契约、`src/validator/`。
   ⇒ **§5#8「凡实质改动一律走角色矩阵」按本条收窄**，「谁写谁不批」只在后一类上仍然成立。
4. **测试锁跟着契约走，不跟着脚手架走**：只给**交接契约、几何不变量、已经真咬过人的坑**加锁；
   **围栏 / 隔离壳 / 诊断工具这类脚手架不配锁**——它们天天改，配锁等于每改一次重做一遍锁。

### 0.5 ⭐ 管理文档体量纪律（2026-08-18 用户令「东西放到该放的地方，不要全挤在这两个管理文档」）

**立此条的事实依据**（清理当天的清点）：`CLAUDE.md` **1658 行**、`plan.md` **4765 行**；
其中 CLAUDE.md §2 有 **1327 行**是历史节点叙述，plan.md 的「当前焦点」章节整节其实是**7 月的历史**，
「近期（细）」整节是**6 月已完成**的 backlog。⇒ **根文件读不动，当前口径被历史叙述淹没。**
**已经造成过实害**：orchestrator 因在长文里读到 §1.5#7 的旧条文，**连续三次**得出
「07-07 模式违规、须先实现 `reading-agent`」的错误结论，其中一次把 08-02 的旧口径当现行说给用户。

#### 每份文档只放一件事（⛔ 越界即搬，不是「顺手也写这儿」）

| 文档 | 只放 | ⛔ 不放 |
|---|---|---|
| **CLAUDE.md** | 长期稳定的「是什么」+ 此刻的「在哪」；§2 = **当前 banner + 节点索引表** | 日更叙述 · 操作手册正文 · 待办 · 已翻篇的口径原文 |
| **plan.md** | **还没做完的事** + **当前一轮**的日更 | 上一轮及更早的日更 · 已完成条目的长篇经过 |
| `decision_log.md` | 里程碑与决策详档 | 过程流水 |
| `architecture/` · `guides/` · `capability/` · `proposals/` · `reference/` | 架构 / 操作手册 / 能力主线 / 未落地设想 / 稳定参考 | —— |
| **`logs/worklog/`** | **翻篇的日更与状态摘要归档**（逐字搬、不改） | 任何权威口径（⛔ 与前两份冲突时一律以前两份为准）|

#### 硬指标（超了就搬，别讨论）

- **CLAUDE.md ≤ ~500 行**（⭐ **2026-08-26 用户把上限从 400 上调到 500**；2026-08-18 清理后曾 = 341 行）；**§2 的索引表 ≤ 15 行**。
- **plan.md ≤ ~900 行**（清理后 = 700 行，其中当前一轮日更就占 588 行）；日更**只留当前一轮**。
- ⚠️ **超标时的正确处置有先后**：**先搬上一轮日更**；搬完仍超 ⇒ 说明**本轮日更本身写太长**
  ⇒ **逐条经过归 run 目录 / `logs/experiments/`，plan.md 只留结论 + 指针**。
  ⛔ 不许靠「把限额调大」解决——那正是它长到 6423 行的机制。
- **验收判据（唯一）**：**一个新接手的模型，只读 CLAUDE.md + plan.md，能不能在五分钟内说出
  「现在卡在哪、下一步做什么、什么明确不做」？** 说不出来 ⇒ 就是该搬了。

#### 搬家动作（三步，做完才算搬完）

1. **逐字搬**进 `logs/worklog/YYYY-MM_plan_log.md`（或 `status_digest_*.md`）——⛔ 不改写、不删减、不总结。
2. **原处留一行指针**（日期 + 一句话 + 链接），⛔ 不留摘要段落。
3. **修相对链接层级**（搬深两级要补 `../../`）+ 机械对账「搬走的每一行都在新文件里」。

⚠️ **本条不与 §0.1 判断法则冲突**：管理文档是**换会话后唯一的跨会话通道**（同 §0.3#2 收工 ritual），
读不动 = 下一轮直接读错口径 ⇒ 它属于「不做就跑不起来 / 读不懂结果」那一类，**不是可登记不做的完备性工作**。

---

## 1. 项目总览

### 1.1 目标 / 仓库
- 根目录 [..](..)；项目说明 [../README.md](../README.md)
- 目标：建筑设计意图（YAML / 自然语言 / 建筑图纸）→ 合法 EnergyPlus IDF + 仿真完成

### 1.2 当前架构

```
[建筑图 + 文本]
   ↓
0_reading 识图（半人工 Opus 子代理 / 未来 VLM）→ <case>/.../0_reading/*.json + reading_summary.md
   ↓
run_pipeline（image-blind，src/agent/pipeline.py）几何彻底确定性化：
   1_correction 校正(LLM,出 CorrectedGeometry) → 确定性核(代码)
     → 2_modelling 造面 + 3_split_pairing 互逆配对/跨层切分（几何内核,代码）→ 序列化 surface_specs
     → 4_mep 物理(LLM,只产非几何字段) → 5_intakeoutput 装配+契约校验(代码)
   ↓ 落盘 IntakeOutput Pydantic JSON ── 本项目侧交接契约（11 字段不变）──
   ↓
自动下游（9 subagent，本地 LangGraph）→ InterZone 门 + schedule 门(EP前) → IDF / EnergyPlus
```

- ⭐ **2026-08-23 起 0_reading / 1_correction 的分工按新口径**（分支 `08.23_AsDrawnReading`，未合并）：
  **量=代码 · 认=模型（在 reading）· 对账=代码门 · 装配=correction（模型出决定、代码出坐标）**
  ⇒ 全档 [guides/reading_correction_split_guide.md](guides/reading_correction_split_guide.md)。
- **每段两道门校验**：① 确定性自校验（代码，`*_checks.json`）+ ② LLM/VLM judge（结构化清单，dev 期）。
  逐段阻塞编排见 [`src/agent/execution/step_orchestrator.py`](../src/agent/execution/step_orchestrator.py) +
  CLI [`scripts/tool_scripts/run_stage.py`](../scripts/tool_scripts/run_stage.py)；几何确认门 = 离线 3D 查看器
  [`render_geometry_viewer.py`](../scripts/tool_scripts/render_geometry_viewer.py)。
- **权威接线**：[architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)（子流程↔skill↔中间产物 + 逐段校验登记）。
- **完整工作流**：[guides/new_case_guide.md](guides/new_case_guide.md)（主 Agent 编排器 + judge② 操作手册）。

### 1.3 关键路径

| 路径 | 作用 |
|---|---|
| [../src/agent/pipeline.py](../src/agent/pipeline.py) | **0–5 单一实现 `run_pipeline`**：1_correction(LLM)→确定性核→几何内核(代码)→4_mep(LLM)→5_intakeoutput 装配+契约校验 |
| [../src/agent/correction/](../src/agent/correction) | 校正：`schema.py`(CorrectedGeometry) + `deterministic.py`(确定性核) + `config.py`(容差) + `geometry_validator.py`/`facade.py`(gate① 件) |
| [../src/agent/geometry/](../src/agent/geometry) | 几何确定性内核：`modelling.py`(造面) + `split_pairing.py`(配对/切分) + `specs.py`(序列化) |
| [../src/agent/intakeoutput.py](../src/agent/intakeoutput.py) | **5_intakeoutput**：`assemble_intake_output` 装配 + `validate_contract` 逐 token 契约校验 |
| [../src/agent/execution/](../src/agent/execution) | 执行/审计地基：`step_orchestrator.py`(逐段编排) + `manifest`(append-only attempts) + `validation_run.py`(`validate_case`) + `orchestrate.py` + 失效 DAG/resume/budget/approval |
| [../src/validator/](../src/validator) | 确定性门：`interzone.py`(配对) + `schedules.py`(day-type 完整) + `idf_fragments.py`(统一 parser) + `checks/{reading,correction,kernel,mep,assembly}.py` |
| [../src/agent/judge/](../src/agent/judge) | gate② judge harness（verdict v2 + rubric）；`gt.py:load_gt` **唯一可读 gt**（gate①/执行器绝不 import）|
| [../src/agent/reading/](../src/agent/reading) | 0_reading schema（P1a dimension chain + P1b facade image-local + legacy 迁移）|
| [../src/agent/llm.py](../src/agent/llm.py) + [../src/configs/llm.yaml](../src/configs/llm.yaml) | LLM 工厂 + 多 section（per-case `<case>/llm.yaml` 经 `EP_AGENT_LLM_CONFIG` 覆盖）；容差 [correction.yaml](../src/configs/correction.yaml) |
| [../src/agent/graph.py](../src/agent/graph.py) | 下游 LangGraph（intake → 9 subagent → cross_ref → validate → simulate）；prompt 演进归协作者（§3）|
| [../scripts/](../scripts) | 总启动 `run_full_pipeline.py`（`--reading-from`/`--intake-from`）；`tool_scripts/`=render×N + `run_stage.py` + `record_baseline.py` + `render_geometry_viewer.py` + `render_gt.py` + `gt_from_dxf.py` + `inspect_dxf.py`；`glm_code.sh`=GLM 席位启动器（默认 **glm-5.3**）+ `deepseek_code.sh`=DeepSeek 席位启动器（默认 **deepseek-v4-pro**，**⛔ 按量扣余额、与管线共用**）——两者**凭据只注入子进程，勿全局导出 `ANTHROPIC_*`**；家族版图见 [codex_execution_protocol §1](guides/codex_execution_protocol.md)（⭐ **2026-09-05 入册**：GPT 侧**最高档 = `gpt-6-astra`**〔⛔ 要 codex CLI ≥0.153，已升 0.153.4〕· **GLM 侧要看图只派 `glm-5.3-flash`**，⛔ `glm-5.3` 对图**静默出错**、`glm-5v-turbo` 已被套餐挡死）|
| [../tests/](../tests) | ✅ **当前全绿**：pytest **3378 passed / 13 xfailed / 0 failed**（2026-08-30 主控权威全量 **`407fa44`**，14m28s、`-n auto`、exit 0；`3355 + 23 = 3378` 逐文件闭合：`answer_compiler_{closure,exit_gate,profiles}` 6+3+8 · `denominator_from_facts` **5**（⚠️ 3 个 `def` 但**含参数化**，⛔ `grep def test_` 会低估）· `as_measured_facts_layer` +1；⛔ **`3130`/`3fe0d29` 那条读数已过期，勿再引用**）。⭐⭐ **该读数带 `.pth` 哨兵**（跑前跑后各记一次 editable 装机文件哈希，`58f547fa…` 两次相同、内容均为主树）。⛔ **哨兵是 2026-08-27 因事故新立的**：`.pth` 曾被改指到 `/tmp/ep_f97`、正好穿过一次权威全量的窗口 ⇒ **「全仓绿」的第四种假象 = 跑测【途中】启动器被第三方改掉**，那轮读数已作废。⇒ ⛔⛔ **两条硬口径**：① **席位绝对不许跑 `pip install -e .` / 任何写 `site-packages` 的命令**（venv 全机器共享）；② **权威全量必须带 `.pth` 前后哨兵，两次相同才算数**。事故档 → [logs/experiments/2026-08-27_pth_hijack/](logs/experiments/2026-08-27_pth_hijack/)。⛔ **~~08-25 的「3010 passed / 1 failed / 3 errors」已作废~~** —— 那批红 = **F-93**，已于 `b3e0a32` 闭合（**全仓默认并行** `-n auto`，16 核 4.5–8 分钟；串行 `-n0` 15–26 分钟；⚠️ **有别的席位在同机跑时一律 `-n 6`**，见 §5#7.5。跑测三档节奏 + 「受影响子集」工具见 [codex_execution_protocol §7.5](guides/codex_execution_protocol.md)）（kernel/checks/judge/orchestrator/gt/interzone/schedule/viewer/flow/runner/grade/run_config/isolation/view_manifest/c2_b2_v3/c2_b2b_envelope_transform/c2_va_applicability/gt_schema/output_coordinate_×5/e4_relative_north_axis_e2e/c2_b5_source_routing/c2_b5_host_resolution/c2_b5_parent_and_verts/c2_b5_artifact_trust/c2_b5_legacy/reading_line_style_visibility/audit_remediation_accepted_inputs/tarch_converter_p{0,1,2}/tarch_elevation_must_red/**tarch_converter_reproducibility**/**gt_promotion_path**〔含 25 格 `mutation` 源码变异矩阵，默认收集内〕/gt_overlay…）|
| [../case_tests/](../case_tests) | `0_reading_tests/` + `e2e_tests/`(含 sm20_anchor/sm21_anchor) + `test_baseline/`(方案+注册表+gt) |
| `$ENERGYPLUS_EXE` | EnergyPlus 引擎；解析序 env→PATH→硬编码默认。容器内 25.1.0、宿主 Windows 25.2.0（patch 差异，数值对齐以容器为准）|
| [../data/weather/Shenzhen.epw](../data/weather/Shenzhen.epw) | 默认 EPW 气象 |

### 1.4 技术栈
LangGraph + LangChain（`init_chat_model` 路由）；多模态走 base64 图块；结构化输出 `with_structured_output(IntakeOutput)`；
EnergyPlus 经 `WorkflowTool.run_simulation`（eppy + ConverterManager，idfpy 切换搁置）。

### 1.5 仍有约束力的关键不变量（详档见 [decision_log.md §B](decision_log.md)）
1. **分工铁律**：LLM 只做 **感知** + 校正判断 + 物理语义；**代码做所有几何（建模+切配）+ 装配**。
   ⚠️ **2026-08-23 用户据此当场纠正 orchestrator**：「语义搬去 1_correction」的提法**违反本条**——
   **感知就是语义**，它本来就归 reading 的模型。展开见
   [guides/reading_correction_split_guide.md §一](guides/reading_correction_split_guide.md)。
2. **全局唯一世界坐标系**：原点 = 整栋投影最大边界 SW 内角，禁每层本地原点。
3. **交接契约 = IntakeOutput Pydantic 11 字段**（[state.py](../src/agent/state.py#L23)）；下游 9 subagent 消费、不归本项目管。
4. **gt 铁律**：评测答案 `case_tests/test_baseline/gt/<case>/gt.json` **只 gate② judge / 人 可读**，gate①/执行器绝不 import（dev/prod 一致 + 防照抄）。
5. **精确坐标容差带由确定性层判**（核坍缩规范值 + gate① 带容差不变量），gt/judge 只判布局/计数/窗位定性。
6. **建筑复杂度可扩展性铁律（2026-07-03 用户定，硬约束所有决策）**：**每个决策必须为未来建筑复杂度升级留路**——现架构（正交·**共底面盒子**）刻意保留了升级到复杂体量（**非方形 / 退台 / 挑空双层高 / 中庭竖井**）的可能：不变量 #1 判断-几何分工、#2 单一世界坐标、版本化 schema、#3 稳定契约都是为此设的**接缝**；复杂体量 = schema 加槽位（per-floor footprint / 变高区 / void）+ kernel 实现扩展（含休眠支线 [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md) 热区积木 = kernel 策略替换、**非架构推翻**），都在接缝内长。**不得**把"共用 footprint / 每层满铺楼板 / 固定层高"这类**当前简化假设烤死到无法松动**——纯只适用当前情况（不能长到复杂体量）的方案**没有意义**。复杂体量本身是远期 defer，但**任何当下决策都要过一遍"这条路以后能不能长到复杂体量"**。风险不在架构、在"烤死的假设"，本条即那道保险。
7. **环节的控制边界 + 成绩归因** —— **⛔ 正文已迁出**，见
   [capability/reading/improvement_methodology.md §8](capability/reading/improvement_methodology.md)。
   本文只保留仍然无条件生效的那条硬边界：
   **端到端 orchestrator 对某环节内部只能「启动与接收」** —— ✅ 建工作区 / spawn / merge / 跑确定性工具 / 决定跑什么 / 兼任 judge；
   ⛔ 写自由文本 directive、看了图之后指导 worker、替它挑 CV 参数或返工区域、接触 gt 之后把结论送回同一个 run。
   **judge 出口不变**：判定不过 ⇒ 整轮盲重抽、零信息，⛔ 不得告诉执行环节哪里错了。
   **隔离原则（08-02）**：严格限制**可见信息与写出边界**，⛔ 不限制在合法输入上采用何种计算方法。
   ⚠️ **其余整包**（`reading-agent` / autonomous↔controlled lane / 成绩归因 / 隔离档位）**已打包延后归 reading 专项，
   ⛔ 不是本批准入门** —— orchestrator 曾因误读本条连续三次得出错误结论，故迁出。**现行口径以 §2 的 reading banner 为准。**
---

## 2. 当前开发状态

> # ⭐⭐⭐ 先读本批开发指南 → [guides/reading_correction_split_guide.md](guides/reading_correction_split_guide.md)
> 用户 2026-08-23 令：「**最近这条线上的开发你都先读这份指南**，有违背的或者需要我裁定的再来找我。」
> ⇒ 它就是为了**减少用户进来纠偏**而立的；⛔ **别再拿它已经定死的事去问用户**。
> **内含**：分工四刀（量=代码 · **认=模型（在 reading）** · 对账=代码门 · 装配=correction）·
> reading 三层产物 · correction 三拍循环（**模型出决定、代码出坐标**）·
> ⭐ **只判答案不判过程，两个判分器都对着 gt** · 墙厚归属 · 回叠比对 ·
> **八条硬纪律**（每条都有 08-23 实犯）· 验收尺度 · 两个专项的并入与留尾。
> ⛔ 与本文其余各节冲突处，**reading/correction 分工与判分口径以该指南为准**。

> ⛔ **2026-08-28 ~ 2026-09-05【第四程】的历次收工 banner，以及 §2.1 的历史索引行，已按 §0.5 三步逐字搬入** [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md) 与 [`logs/worklog/2026-09_plan_log.md`](logs/worklog/2026-09_plan_log.md)（每批对账均 0 缺失）。

> **⭐⭐⭐ 2026-09-01 用户拍板（当前唯一口径，⛔ 覆盖已过审设计稿 §8.1 / §9.1 第 8 步）**
> **① 旧格式不兼顾，整条拆干净** —— 用户原话「旧格式不用兼顾，全部按新的来」。
> **② 「产出新格式产物」提到前面，下一批就做**；**sm21 / sm24 / sm25 的 gt 与 pipeline 都按新格式重新完整做**
> ⇒ 主控提的「拆了没东西喂新路径」顾虑**已被用户当场解掉**（三个 case 全重做，无历史包袱）。
> ⛔ **拆单必须排在模块 5/6 落地之后**（它们正 import 编译器，中途拆会造在飞席位假红）。
> ⭐ 展开 + 主控核过的三项事实 + 作废清单 → [guides/reading_correction_split_guide.md §十之二](guides/reading_correction_split_guide.md)。

> ⛔ **2026-09-05【第五程】banner 已按 §0.5 三步逐字搬入** [`logs/worklog/2026-09_plan_log.md`](logs/worklog/2026-09_plan_log.md)（逐行对账 0 缺失）。

> **⭐⭐⭐ 2026-09-06【第六程】banner（当前唯一口径）**
>
> ### ① ⭐⭐⭐ 收口读数：**权威全量 `3907 passed / 2 skipped / 13 xfailed / 0 failed`**（主树，15m08s）
> 逐位闭合 **`3907 + 2 + 13 = 3922`** = 独立 `--collect-only` 实测 3922，**差额 0**；
> ⭐ **合并前的预测与实测逐位吻合**：`3863`（A-11 后）`+ 27`（A-6 整块）`+ 17`（A-6 返工）`= 3907`。
> 本日跑了两次（A-11 后 `3863` / A-6 后 `3907`），**两次的 `.pth` 与 `m.__file__` 哨兵均前后同值且指主树**，
> 跑测全程 `git status` 空、HEAD 未变；`3863` 那次三方读数一致（施工席 / 复核方独立复算 / 主树权威）。
> 两次对账原文与耗时说明 → [`logs/experiments/2026-09-06_authoritative_suite/`](logs/experiments/2026-09-06_authoritative_suite/README.md)。
>
> ### ② ✅ **A-11「gt 按 1 mm 规整入库」已合并**（`3ca8abda`）
> Claude 跨家族审 **APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 2**；上一轮两个根因**真实修复**，
> ⭐ 三条复核全过（改动前红 · 改动后绿 · **换同形输入仍走不通**）。
> **两条不阻断已结转 `plan.md` A-11 行**：**A-11-d1** handle 锚在「旧 handle 被转移给另一堵**真实存在**的墙」
> 子场景下**仍静默指错墙**（1 hit 指错对象，⛔ 不是 0-hit no-op）—— 是旧病族被**收窄**后剩的一角，净改善 ·
> ⛔⛔ **A-11-d2 `SM25_DEFERRED_CAVITY_COUNT = 4` 被独立反例坐实是代理量**（`3×F-157 + 1×form B` 总数仍 4、锁不红）
> ⇒ **硬排期：下一次任一成因单独变化【之前】必须先拆 per-code 两个钉，且拆分须同时 touch 两个消费者文件。**
>
> ### ③ ⛔ **A-6 整条线被判 REWORK / 阻断 2 / 不阻断 3**（Claude 跨家族审）
> **阻断① 已由主控自行销账**：施工方按「指不到强制行就删句」这条**合法出口**删掉的三句**只能由接线方兑现**的承诺，
> 已写进 `plan.md` 的 E-a 行成为 **E-a-1 / E-a-2 / E-a-3** 三条可查验收项 ——
> ⭐ 判定依据是 `grep … src/agent/pipeline.py` **零命中** ⇒ **缺口是真的，删句没消除它、只是让它从文档里消失**。
> ⚠️ 三条**今天零流量**，是**未来的保险丝**，⛔ 引用时别读成「已经在保护」。
> **阻断② 已返工并过审合并**（`gpt-6-astra` 返工 → Claude 跨家族审 `APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 2`，合并 `d5675286`）。见 ④。
>
> ### ④ ⭐⭐⭐ 阻断② 的形状 = **入口检查了、出口没有对称地重做**（本批那条口径的第二形态）
> `submit()` 的跨行顺序检查（`tick_claim.py:469-478`）是这批数据**唯一一次**被验证顺序的机会；
> `consume()`（`:493`）逐行重算**数值**、却**从不重核跨行 `lo < hi`** ⇒ 复核方实测**倒置的假区间被接受**，
> 而 `OpeningReview.__init__`（`opening_adjudication.py:178-179`）把 `value_u` 直接写进 `along_lo_m/along_hi_m`、
> **全程无 `lo<hi` 校验** ⇒ 假事实**一路静默流进洞口几何**。⚠️ **不需要有人恶意攻击**，重构里一个普通 bug 就够。
> ⭐ 复核方按「**反查哪个方向没有锁**」给出判据：把该检查搬进 `consume()` 对合法批次是**无操作**、
> **不会打红任何现有测试** ⇒ **不存在「加了就会红」的理由挡着这把锁**。
> ⇒ **返工单把题从【例子】提到【类】**：要逐项回答「`submit()` 每项检查，`consume()` 各自重做了没有」，那张对照表就是交付物。
> **⭐⭐⭐ 结果证明这个提法值回票价**：施工方交回 **17 项表**，除复核方按症状找到的那 1 项外，**另外 6 项 `consume()` 从未重做** —— 响应类型/`packet_id` 对应 · `reperceive` 不能冻结为事实 · 补证债必须有 `missing_chains` · `debt_id` 生成 · `retired_debt_id` 条件 · 逐行来源字段。新增 17 条测试、**零既有测试被改动**（`3877 + 17 = 3894`，差额 0）。
> **复核方用两套互不依赖口径独立枚举**（A：逐行标号 `submit()` 全文得 A1–A18；B：⭐ 不依赖阅读顺序，取 `submit()`/`consume()` 各自能抛的**具名 code 集合求差集**）——**两套完全收敛且与 17 项表逐项映射，零遗漏零多余。**
> ⭐ 施工方标为「结构上不必重做」的 #3/#16/#17 也全部实测证实，其中 **#17 的理由是可证伪的**（「拿提交后活字典重放会误拒合法批次」）⇒ 复核方用**直接替换法**验了，确实会误拒；**#16 自称「未新增封印或私有名字屏障」也实测证实**：伪造赋值仍赋得进去、在**出口**被拒 ⇒ **是出口全检**。
> ⛔ **结转 A-6-d1**：`opening_adjudication.py` 只对 **PLAN 侧**装配点加了第二层拦截，**ELEVATION 侧 `_elevation_document()` 没有对称的第二层**。今天两侧同被主锁挡住 ⇒ 不是缺口；⚠️ **但主锁若被未来重构悄悄削弱（正是本单的病根形状），PLAN 侧立刻红、ELEVATION 侧不会。**
>
> ### ⑤ ⭐⭐ A-6 审的**正面发现**（⛔ 别只记 REWORK）
> 把 B2 已证的五类攻击原样打过来：`__class__` 重赋值**被逐字节内容比对挡住** ——
> ⭐ 挡它的**不是 `isinstance`**，**比 B2 当时的对应设计更强**；`freeze()` 的 canonical JSON 在
> int/float、`-0.0`/`0.0`、NaN 边界上**未发现坍缩**。R-1..R-4 四条全核实通过，抽 3 条最承重的锁变异**三条全真红**。
>
> ### ⑥ ⭐⭐⭐ **分段提交的正面证明**：`gpt-6-astra` 在 A-6 一个大块里**三次**撞 `Selected model is at capacity` 退出，
> **三次都发生在活干完之后**（实现+契约+证据 / 全量+README / 执行档 248 行且已 `git add`），每次只丢 `git commit`
> 这一个动作 ⇒ **一行代码没丢**。⭐ **容量 ≠ 额度**：探针当场 `PROBE_OK` 即可续，⛔ 别当额度耗尽改派。
>
> ### ⑦ ⚠️ 两条运维坑（本程实撞）
> **`codex exec resume` 静默把 reasoning effort 重置为 `low`**（原会话是 `xhigh`），只在启动横幅印一行、不报错
> ⇒ 续会话必须显式 `-c model_reasoning_effort=`，且**选项要放在 `resume` 之前** ·
> **五个席位启动器在 git 里都是 `100644`**，而 `seat_claude.sh` 头部写明宿主按 `Bash(scripts/seat_claude.sh:*)` 放行
> ⇒ 那条被文档写死的调用路径**从来走不通**；已 `git update-index --chmod=+x` 落库（本仓 `core.fileMode=false`，
> 光 `chmod` 换棵树就没了）。
>
> ### ⑧ ⭐ **下程第一件事**：**J 判分改造**（前置 A-11 已合并，⭐ **无阻塞**）。
> ⚠️ **E-a 先别派** —— 见 ⑨，它需要先拍一个口径。
> ⚠️ **两处卡用户**：**E-b**（跑 reading 用哪个模型、抽几次）· **G-a**（sm25 gt 人签台账 ——
> ⭐ **按用户 08-28 定的排在「这批改造完之后」，⛔ 不是现在等签**；理由是「现在属于改造阶段很多都还是测试」）。
>
> ### ⑨ ⛔⛔ **E-a 被 A 层停报打回：「这是接线」这个前提不成立**（第 70 次停报，⭐ 又是派工方的题错）
> 实测**没有任何一份平面产物同时被两边接受**：`sm25_*f_v2.json`（`as_drawn_plan`）pipeline **✅** / A-6 **❌ `TICK_SOURCE_CONTRACT_UNSUPPORTED`**；
> `sm25_*f_as_drawn.json`（`as_drawn_plan_v0`）pipeline **❌ `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED`** / A-6 **✅**。
> ⭐ **已排除「只是标签不同」**：两套洞口全集来源不同路径，**1F 51 对 85、2F 45 对 87，ID 交集均为空**
> ⇒ **是两个不同的洞口全集**，⛔ 不能改名/按序替换接通。⇒ **这是源契约对齐，⛔ 不是接线**，
> **下轮开 J 之前先拍**：甲 让 A-6 支持 v2 原 bytes · 乙 把 v0 接进证据链 · 丙 先查清 51 vs 85 的差从哪来。
> ⛔⛔ **主控一条断言被实测推翻**：我写「A-6 之后立面 `x_range_m` 由链档 mm 值出、不再是像素外推」——**错**，
> `tick_claim.py:458` **只在显式 `select` 时**产 `chain_backed`，显式 `pixel` 仍产 `pixel_only`。⭐ **候选出现 ≠ 认领完成。**
> ⭐ 施工方保持 `pair_count=null` + `BLOCKED_BEFORE_OPENING_REVIEW`，⛔ **没把未测得填成 0**。
> B 层（我的错，已修 5 份单）：`git show` 不接 `--cached`，正确是 `git diff --cached --numstat`。

### 2.1 最近节点索引

> **⛔ 本节只放索引，不叠叙述。** 当前轮次的逐日全档 → [plan.md](plan.md)；
> 已翻篇的日更 → [logs/worklog/](logs/worklog/)；
> **2026-08-17 及更早的节点摘要原文（逐字未改）→ [logs/worklog/status_digest_to_2026-08-17.md](logs/worklog/status_digest_to_2026-08-17.md)。**

| 日期 | 一句话 | 详档 |
|---|---|---|
| **2026-09-06 第六程** | ✅ **A-11「gt 按 1 mm 规整入库」合并**（Claude 审 `APPROVE-WITH-FINDINGS/阻断0/不阻断2`；⭐ 三条复核全过，含**换同形输入仍走不通**）⇒ **权威全量 `3863`**（逐位闭合 `3863+2+13=3878` = 独立 collect，差额 0）· ✅ **A-6 刻度认领整条线合并**（先判 `REWORK/阻断2`：**阻断①** 删句留下的接线缺口只活在散文里〔`grep src/agent/pipeline.py` 零命中〕**已由主控销账进 `plan.md` E-a-1/2/3**；**阻断②** = ⭐⭐⭐ **`submit()` 检查了、`consume()` 没对称重做** ⇒ 倒置的假区间静默流进洞口几何）⇒ **权威全量 `3907`**（`3863+27+17`，逐位闭合 `3907+2+13=3922` 差额 0）· ⭐⭐⭐ **本程方法论收获：返工题从【修这个例子】提到【枚举这一类】** —— 复核方按症状只找到 1 个洞，逐项枚举找出**另外 6 个** `consume()` 从未重做的检查；复核方再用**两套互不依赖口径**（逐行标号 / 具名 code 集合求差集）独立枚举，**零遗漏零多余** · ⛔ **A-6-d1** 防御深度不对称（PLAN 侧有第二层拦截、ELEVATION 侧没有；主锁若被未来重构削弱，只有 PLAN 侧会红）· ⭐⭐ **正面发现**：`__class__` 重赋值被**逐字节内容比对**（⛔ 不是 `isinstance`）挡住、比 B2 更强；`freeze()` canonical 无坍缩 · ⭐⭐⭐ **分段提交正面证明**：astra 三次撞 provider 容量**都在活干完之后**，只丢 commit、**一行代码没丢**（⭐ 容量≠额度，探针可续）· ⛔ **A-11-d2** `SM25_DEFERRED_CAVITY_COUNT=4` 被反例坐实是**代理量** · ⚠️ 两坑：`codex exec resume` **静默把 effort 降到 `low`** · 五个启动器缺 `+x` 致文档写死的调用路径从未成立 · ⭐ **挡路新单 5 → 2**（只剩 E-a / J-判分改造，且都无前置阻塞）|  [A-11 裁决](logs/reviews/verdict/2026-09-05l_A11_rework1_crossreview_claude.md) · [A-6 裁决](logs/reviews/verdict/2026-09-05m_A6_tick_claim_block_crossreview_claude.md) · [A-6 返工单](logs/reviews/request/2026-09-06a_A6_rework1_dispatch.md) · [A-6 返工裁决](logs/reviews/verdict/2026-09-06b_A6_rework1_crossreview_claude.md) · [独立枚举](logs/experiments/2026-09-06b_A6_rework1_crossreview_claude/independent_submit_consume_enumeration.md) · [权威全量](logs/experiments/2026-09-06_authoritative_suite/README.md) |
| **2026-09-05 第五程** | ⭐⭐ **模型家族扩编**（GPT 最高档=`gpt-6-astra`，⛔ 要 CLI ≥0.153 已升 0.153.4 · GLM 新增 `glm-5.3-flash`，⭐ **识图 6/6 全对而 `glm-5.3` 静默降级**、`glm-5v-turbo` 被套餐挡死）· ✅ **B2 返工 3 合并**（Claude 审 `APPROVE/阻断0`，⭐ **五条自造攻击里三条绕过入口封印、全被出口全检接住**）⇒ **权威全量 `3850`**（逐位闭合 `3819+31`）· ⛔ **设计稿返工 1 被 astra 判 REWORK/阻断5**（⭐ 实测 6 条自动一档边落在非主链、构造不出 `node_ref`；链前置门只验总长；`ArtifactPointerV1` 非 frozen）· ⭐⭐ **主控自查**：J-6 四条里**三条是过期账**、F-89 转为 J-3 验收项（新判分器**零立面维度**）⇒ 挡路单 6→5；A-11 量出 **74 个非 1 mm 值**、**用户拍板走乙**（转换器加规整，⛔ 不做 74 条人签）· ⛔ 自错两条：`.gitignore` 静默吞证据 · 跑测途中启席位翻 `.pth` | [B2 裁决](logs/reviews/verdict/2026-09-05d_B2_rework3_crossreview_claude.md) · [设计稿裁决](logs/reviews/verdict/2026-09-05e_tick_claim_design_rework1_crossreview_gpt.md) · [自查读数](logs/experiments/2026-09-05g_orchestrator_readouts/README.md) · [名册探针](logs/experiments/2026-09-05_model_roster_probe/README.md) |
| **2026-09-05 收工（第四程）** | ⭐⭐⭐ **用户把洞口对齐 / correction 目标态整条口径拍定**（尺寸链优先·像素只作指认 · 证据两档都出值 · 四分类 · 两步各跑一遍三拍 · **gt 1 mm / pipeline 出口 10 mm / 存 0.1 mm 整数** · `GAP_*` 与基准差降级为**给模型的参考** · **判分入闸：第一次跑=跑通＋判出分**）⇒ 全档进 [指南 §十四/§十五](guides/reading_correction_split_guide.md) · ⭐⭐ **主控实测**：立面 68 条洞口边 66 条 ≤34 mm、认领后宽度**全变图纸整数**，平面侧弱（102 个端点仅 44 个）⇒ **两侧不对称是结构性的**；B4 配对**零生产调用者**；gt 侧 1 mm **尚未落地** · ✅ **T4-a 合并**（GLM 审 `APPROVE/阻断0`），**权威全量 `3819 passed / 0 failed`**（`3778+3+28+10`，`.pth` 前后同值）· ⏳ B2 返工3 与设计稿返工1 待审 · ⭐⭐⭐ **四条线的阻断是同一形状：判据量的是【代理量】**（`isinstance`≠过了字节门 · 像不像活键≠能否解析成功 · 链节点≠链能给出的值）⇒ 有效解只有**类型层不存在** / **出口全检** · ⛔ 派工方错：**建树基点早于自己当天写的口径**，靠跨家族审的 delta 核对救回 · ⚠️ **GPT 席位被 provider 安全过滤拦死两次**、零产出 | [T4-a 裁决](logs/reviews/verdict/2026-09-05c_T4a_rework2_crossreview_glm.md) · [设计稿裁决](logs/reviews/verdict/2026-09-04y_tick_claim_design_crossreview_gpt.md) · [B2 裁决](logs/reviews/verdict/2026-09-04p_B2_rework2_crossreview_gpt.md) · [排期盘面](plan.md) |
| **2026-09-04 收工** | ⭐⭐⭐ **B4 一轮返工后 `APPROVE/阻断0` 并合并** ⇒ **B1/B3/F-158/B4 四条线全在主线，权威全量 `3778`**（逐位闭合 `3717+31+5+3+20+2`）· ✅ **T4-a 债义务字段做完待审**（⭐ 施工方 A 层停报**推翻了派工方的时机理由**：基点上没有 B4 ⇒ 现在做半个会让哈希**翻搅两次**；已先合并 B4 再重派，只翻搅一次）· ⛔ **B2 两轮均 REWORK 且同形 = 改表面不改类型层可达性**（把类改私有 ⇒ 复核方**根本不用碰那个私有类**；换结构判据 ⇒ 自报「唯一可达」**当场被同结构反例证否**）· ⭐ **主控以 judge 身份做完 B2 的 z 梯子 gt 对账**（层数逐位相等、标高准到 **0.155 像素**，残差归 reading）⛔ 但只对了 z 一个维度，F-1 原样挂着 · ⛔⛔ **派工方本程自己错七条**，⭐ 其中**三条同形=判据测不到要守的性质** | [B4 裁决](logs/reviews/verdict/2026-09-03am_B4_rework1_crossreview_claude.md) · [B2 裁决](logs/reviews/verdict/2026-09-04d_B2_rework1_crossreview_gpt.md) · [T4-a 停报](logs/reviews/execution/2026-09-04b_T4a_execution.md) · [z 梯子对账](logs/reviews/verdict/2026-09-03an_B2_gt_reconciliation_judge.md) |
| **2026-09-01 ~ 09-03（5 行）** | ⛔ 已于 2026-09-05 第五程按 §0.5 三步逐字搬入 worklog（对账 0 缺失） | [logs/worklog/2026-09_plan_log.md](logs/worklog/2026-09_plan_log.md) |
| **≤2026-09-01（20 行）** | ⛔ 已于 2026-09-05 第五程收工按 §0.5 三步逐字搬入 worklog（对账 0 缺失） | [logs/worklog/2026-09_plan_log.md](logs/worklog/2026-09_plan_log.md) |
| **≤2026-08-20** | 六行已按 §0.5 折叠（07-07 水平复现 · 三臂判别 · 治理换挡 · 707 前置三件 + 全仓首次真零红 2835 · reading 重启七抽全否与基座普查 · 验收首次达成与全链首跑 EnergyPlus）| [worklog](logs/worklog/2026-08_plan_log.md) · [status digest](logs/worklog/status_digest_to_2026-08-17.md) · [2026-07](logs/worklog/2026-07_plan_log.md) |

---

## 3. 责任范围

**In-scope**：① `intake`/0–5 管线多模态理解（图+文本 → IntakeOutput）= 核心战场；② [llm.py](../src/agent/llm.py) provider 抽象 + 开源模型接入；③ skill 提示词演进（[`../skills/intake_pipeline/`](../skills/intake_pipeline) 0–5 阶段库）；④ 测试数据集 + baseline + 评测 + 逐段校验；⑤ 本地推理后端（vLLM/SGLang，等 Pivot 准入）。

**Out-of-scope**（协作者维护权 ≠ 本地无代码）：① 下游 9 subagent + cross_ref + validate + simulate 的 **prompt 演进**（本地有完整可跑代码，协作者负责 prompt + LangSmith 部署）；② MCP 工具基于 idfpy 的全线重写（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）；③ LangSmith 多步编排；④ RAG 知识库。

---

## 4. 关键洞察

1. **视觉理解非首要瓶颈**；真正瓶颈 = **长链路 tool-calling 稳定性 + 子系统覆盖完整性**（新流程靠 cross_ref + validate + 确定性门兜底）。
2. **强制约束别交给 LLM 记得** → 关键不变量一律确定性门强制（schedule 门 / interzone 门 / 内核 raise），不靠 prompt。
3. **EP 通过 ≠ 几何对**：几何正确性以 InterZone 门 + gate① 不变量为准；EP 段错≠环境（多为不完整 schedule 等可定位真因）。
   **⭐ 2026-08-14 扩写：`EP 0 Severe` ≠ 物理输入对** —— 同一份逐位相同的几何，三次跑的 MEP 数值逐次在变，
   其中一次把**活动水平**（每人代谢率）写成了会归零的作息曲线；**全链无任何门校验 MEP 数值物理合理性**
   （`mep.reasonability_bands` 现为 `not_applicable`），只有 EnergyPlus 以 **Warning** 提了一句，
   而验收条件只看 `0 Severe` ⇒ **看不见**。登记为 **F-32**。
4. **token 口径**：`/context` 真值才作准（deferred MCP / autocompact / system tools 不计入 Total）。

---

## 5. 协作者 / 助手约定

> **⛔ 2026-08-18 起本节整体受 [§0 治理条款](#0-⭐⭐⭐-项目定位与开发治理2026-08-18-用户拍板--冲突时压过本文-5-全部流程条款) 约束，冲突处以 §0 为准。**
> 影响最大的两条：**#8 的「凡实质改动一律走角色矩阵」按 §0.4#3 收窄**——
> 探索档脚手架 / 诊断工具 / `AI_agent/` 文档主控可直接改，
> 只有 `src/agent/pipeline` 内核 / 交接契约 / `src/validator/` 仍须派工 + 换人审；
> **审阅与补锁的必要性一律先过 §0.1 的判断法则**（不做它，下一次跑测能不能跑起来、结果能不能读？）。


> **⚠️ 跑 case / reading / judge / baseline 铁律（2026-07-08 用户定——已犯几次：参照旧 run 临时脚本、手搓判卷、现查接口，既浪费 token 又产物不规范）**：动手前**先读 [guides/new_case_guide.md](guides/new_case_guide.md) 走单一 `flow` SOP**，别照旧 run 现凑。
> - **禁手搓判卷**：`score_vs_gt`（平面+立面一次出）/ `grade.png` / `*_render.png` / `attempts/NNN/` 全由 `flow`（[run_stage.py](../scripts/tool_scripts/run_stage.py)）**自动生成**——别手动调 `score_reading_vs_gt`/`elevation_score` 现查 API 手工汇总（= 造轮子）。**标准链**：reading 走冷启子 Agent / codex 产 `0_reading/*_view.json` → `flow <case> <run> --judge stop --to <stage>` 自动 gate①+判卷（render/grade/score_vs_gt/attempts）→ 你写 `StageVerdict` 经 `judge --verdict` 提交 → `flow --record[-partial]` 出 `report/REPORT.md`，补 AGENT 四桶建议（**record 格式**：`- action: …` / `  evidence: [E:..]` / `  owner: …`，citation linter 卡）。
> - **禁抄近道**：`run_pipeline` 直连 / `run_full_pipeline --intake-from` 跳过 judge/attempts/3D/report。
> - **非 Claude 模型 reading（如 gpt-5.4-mini）**：经 codex CLI，用 `spawn_isolated_reader build` 的 clean-room staging 隔离（gt 物理排除）；坑 = codex `-i` 是可变参数会吞掉尾随位置 prompt → **prompt 走 stdin**（`codex exec -m <model> -i <png> < prompt.txt`）。E3 前置=spawn 前先 `cv_probe prescan-plan/-elevation` 把候选拷进 staging。

1. **memory ↔ 管理文档同步（硬纪律）**：助手 memory 是 Claude 本地的，换主控模型即丢。**凡进 memory 的项目级事实/决策/反馈，必须同步落进管理文档**（当前状态→本文§2 / 待办→plan.md / 历史→decision_log.md / 架构→pipeline_stage_contracts.md）。memory 只作 Claude 的个人索引，不作唯一存储。
2. **模型切换入口唯一**：[llm.yaml](../src/configs/llm.yaml) + [llm.py](../src/agent/llm.py)，不在节点内硬编码；per-case 改 `<case>/llm.yaml`。
3. **多模态改动只改 intake/0_reading**，不绕过把图像塞下游。
4. **改 skill/src/MCP/下游 subagent 先备份**：`cp` 到 `backup/{Skill,src,MCP,scripts}_history/<YYYY-MM-DD>_<reason>/`；动下游代码并在 [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 记一条（活文档，管理方式不变）。
5. **本项目交接产物 = IntakeOutput JSON**；下游走 [run_full_pipeline.py](../scripts/run_full_pipeline.py) 自动跑产 IDF + 仿真；规则库 [`../skills/intake_pipeline/`](../skills/intake_pipeline) 按阶段运行时加载。**skill 库 = 英文纯当前版本 spec**：文件内不写时间戳/版本号/changelog/缘起 case（决策史归 decision_log + git）；0–5 阶段布局；旧 `energyplus_mcp` 单步库已退役。
6. **回归门槛**：切默认 provider 前端到端跑通率 ≥ Anthropic 基线 80%（[reference/pivot_criteria.md](reference/pivot_criteria.md)）。
7. **git 权限下放**：助手可在里程碑自行 `git add`+`commit`（message 仿 `<月.日>_<英文标签>`，body 含①改动②为何此刻③影响）。**push** 仅在**收工（§5#12）**或明确要求时（平时不主动 push）。**禁** force push / `reset --hard` / 跳 hook / 动 `git config`。
7.5. ⭐⭐⭐ **并发治理：一个模型家族同时只能在飞一个任务**（2026-08-27 用户拍板，硬口径）
    —— **跨家族可以同时开**（Claude 施工 ‖ GLM 复核 ‖ GPT 设计审 = 合法），
    **同一家族⛔ 不许并行两个**（⛔ 两个 Claude 施工席位同时跑 = 违规）。
    **立此条的事实依据**：2026-08-27 夜班同时开两个 Claude 施工席位 + GLM 复核 + 两轮 GPT 复核，
    两个 Claude 席位实测烧掉 **约 16 万 + 33 万 token**，中途撞上月度上限中断；
    并且**同机三路各跑 `-n auto` 会把全量测试跑崩**（`load average 17.44 / 16 核`，
    worker `OSError: cannot send`、**无 summary 行** = 同机竞争假红，重跑即可、⛔ 不记回归）。
    ⇒ **配套两条**：① 并行时跑测一律 **`-n 6`**，⛔ 不用 `-n auto`；
    ② 派工前先点一遍「这个家族现在有没有别的活在飞」。

8. **实质改动一律走角色矩阵**（操作手册 = [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md)
   —— 四家族版图 / 四档对位阶梯 / 审阶梯 / 排工拍板制 / 席位运维**全在那里，⛔ 本文不重复**）：
   **主控 = Claude 家族开对话模型**（整场不切模型），亲手只做 ① 方案/规划 ② 审 diff/裁决 ③ judge
   ④ memory + `AI_agent/` 文档编辑 ⑤ `git add`/`commit`。
   **⛔ 2026-08-18 起按 §0.4#3 收窄**：探索档脚手架 / 诊断工具 / `AI_agent/` 文档**主控可直接改**；
   只有 `src/agent/pipeline` 内核 / 交接契约 / `src/validator/` 仍须**派工 + 换人审**。
   **谁写谁不批**（跨厂商交叉是必须）· **审恒升一档、⛔ 不许跳两档** · 排工前出派工表交用户拍板 ·
   复核简报只看原始需求 + diff + 测试输出，不看执行者长篇自述。
   **⚠️ 同一形状已三次实犯**（2026-06-27 / 07-11 / 07-14，详见规约 §2.1）：**「出了方案 ≠ 可以自己执行」**；
   返工轮 / findings 修复 / 探针·实验执行**同属实质改动**；察觉自己在编辑 `src`/`tests`/`skills` 即违规信号——停手改派。
8.5. ⭐⭐ **在 `.py` 的 docstring 里引用【生产文件的仓库相对路径】会造出一条真实依赖边**（2026-08-30 实证，F-152）
    —— `affected_tests.py` 对**任何字符串常量（docstring 也算）**做仓库相对路径子串匹配就建边。
    实害：一句正当的引证把一个**真·无人测试**的生产模块静默变成「已覆盖」，诚实门红。
    ⇒ **在 `.py` 里引用生产模块时，⛔ 不要带仓库根前缀**（用不带前缀的相对写法或点号模块名）。
    ⚠️⚠️ **这条规则本身不能在 `.py` 里举例说明** —— 写出那个形式就又造一条边（施工方实测：举例版边还在，去掉例子才 1→0）。
    ⭐ **本文件（markdown）不受影响**：依赖图只遍历一等 Python 文件。
    ⛔ 与「引用位置一律回文件 `grep -n` 核」不冲突：**该核照核，只是别把仓库根前缀写进 `.py` 的字符串常量**。

8.6. ⭐⭐⭐ **席位【启动】就会改掉共享 venv 的 editable 安装 —— 不是谁违纪**（2026-09-01 判别实验立）
    —— [`.mcp.json`](../.mcp.json) 用 **`uv run`** 起 MCP server，而环境里全局
    `UV_PROJECT_ENVIRONMENT=/opt/venv` ⇒ **任何以 worktree 为工作目录启动的【claude 家族】席位
    （含走 `glm_code.sh` 的 GLM），光是【启动】就把 `/opt/venv` 的 `.pth` 改指到它自己那棵树。**
    `codex` 席位不吃 `.mcp.json` ⇒ **不触发**（实测三次）。恢复 = 回主树 `uv run python -c "pass"`。
    **⛔ 两条推论**：
    ① 「禁止席位跑 `pip install -e .`」这条纪律**必要但不充分** —— 这次没有任何人打过那条命令。
      **归因时不许从「`.pth` 变了」直接推「有人违纪」**：先读席位会话记录里的实际命令
      （`~/.claude/projects/-<工作目录转义>/<uuid>.jsonl` 逐条 `tool_use`），
      再查有没有**启动即触发**的机制。⚠️ **2026-08-27 那次的归因很可能也是这个机制，⛔ 别再当已证事实引用。**
    ② ⭐⭐⭐ **`.pth` 哨兵哈希是【代理量】**。承重不变量 = **「我这次导入的，是不是我该测的那份代码」**：
      `python -c "import <被测模块> as m; print(m.__file__)"` 必须落在自己的工作目录里。
      **cwd 胜过 `.pth`**（实测：`.pth` 指别处时，从 worktree 跑 pytest 仍解析到本 worktree）
      ⇒ 哈希不符**不一定**脏，`__file__` 不对**一定**脏。
      ⭐ **变异实测必须把 `__file__` 与 pytest 放同一条命令里跑** ——
      否则「**变异没生效**」与「**锁没牙**」在读数上长得一模一样。
      ⇒ **派工单/复核单的环境判据一律改用 `__file__`，哈希降级为「只记一条、不停报」**；
      ⛔ 但**权威全量前仍要把 `.pth` 恢复到主树并核一次**。

8.7. ⭐⭐ **席位撞额度会留下【未提交的半成品】，而它的日志只字不提**（2026-09-02 一天两次实证）
    —— GLM 撞 5 小时上限留下 **1035 行**、Claude 施工席撞月度上限留下 **1273 行**，
    **两次的会话日志都只有 2–3 行**，全是启动 warning 加那条额度错误。
    ⇒ ⛔⛔ **收到任何席位失败通知，第一件事永远是 `git status`（含它的 worktree）**，
    ⛔ 不许只看日志就下「它什么都没做」的结论。
    **处置三步**：移出工作树存进 `logs/experiments/` · README 写死「**线索非证据**」·
    主控点名可疑处但**不代判**；重派时写明「**重新实现**，复用任何一段须自己重新论证 + 补锁」。
    ⭐ **配套（当天立、当天三次兑现）**：**派工单一律要求分段提交** ——
    每完成一个能独立成立的小步就 commit 一次，⛔ 不许攒到最后。
    立此条后的三次中断（会话结束 ×2 + 额度 ×1）**零丢失**。

9. **开发环境统一 VS Code Dev Container**（[../.devcontainer/README.md](../.devcontainer/README.md)）：容器内 EnergyPlus 25.1.0；git 是唯一同步通道，禁文件同步工具同步本目录；`.devcontainer/`(bind mount, VS Code) vs `docker/`(COPY 代码, MCP server 发布) 别混。
10. **DeepSeek**：v4-pro thinking 默认关（langchain_openai 不回传 reasoning_content 多轮 tool-call 必 400）；管线内 correction 模型角色不变；原 `deepseek-bridge` MCP 承接的省额度小活（简单文本任务）现优先派 luna/Haiku 轻档（§5#8 矩阵），bridge 保留备选；架构/编辑/集成仍主模型负责。
    **⚠️ 2026-07-21 用户定**：DeepSeek **非订阅制（按量计费）** ⇒ **不作日常开发选项**，项目开发里**只在用户专门指定时才用**；**管线内角色不受此限**（1_correction / 4_mep / 下游 9 subagent 照旧，有 baseline 沉淀、不轻动）。
11. **idfpy 替换 + token 优化搁置**（[deferred/](deferred)）：等协作者侧 MCP 重写交付。
12. **收工 ritual（每轮结束硬规范，2026-06-27 用户定；2026-08-18 加第 ② 步；2026-08-24 把 ① 拆成可查四问）**：「收工」必须做完三件事——
    ① **更新管理文档**（待办与进展→[plan.md](plan.md) / 里程碑历史→[decision_log.md](decision_log.md) / 架构变更→[contracts](architecture/pipeline_stage_contracts.md)；并遵 memory↔文档同步铁律 §5#1）。
    **⭐ 其中 CLAUDE.md 必须逐条过下面四问**（2026-08-24 用户令「**CLAUDE.md 更新要纳入收工步骤，否则每次初始上下文都有滞后**」）——
    **⛔ 每问都要能指出具体行号，不许「看过了」**：
    - **①-a §0.0 的第一目标，还是今天在做的事吗？** 变了就**当场改并划掉旧的**。
      ⚠️ **实犯**：「恢复到 07-07」08-21 就被用户当面换挡作废，却**挂到 08-24** —— 三天里每次会话第一眼都在读废口径。
      **根因 = 本条原先只写「当前状态→§2」，于是只往 §2 加 banner、从不回头看 §0。**
    - **①-b §2 的状态 banner 是今天的吗？** 上一条被覆盖了 ⇒ **当场按 §0.5 搬走留一行指针**，⛔ 不许堆叠（曾堆到六块）。
    - **①-c 本轮用户拍板的口径，进 CLAUDE.md / `guides/` 了吗？**（⛔ 只进 plan.md 不算 —— **口径归前者，进展归后者**。）
    - **①-d §2.1 索引表加了今天这一行吗？**
    - **机械收尾**：`wc -l` 过 §0.5 硬指标 + **全文链接解析一遍**（零坏链）。
    - **验收判据**：**只读 CLAUDE.md，能不能说出「今天做了什么、明天从哪接、什么明确不做」**；
    ② **⭐ 管理文档体量自检（§0.5）**：
    `wc -l AI_agent/CLAUDE.md AI_agent/plan.md` —— **CLAUDE.md >500 行（2026-08-26 上调）或 plan.md >900 行 或 plan.md 里出现了上一轮的日更**
    ⇒ **当场按 §0.5 的三步搬进 [`logs/worklog/`](logs/worklog/)**，⛔ 不许留到「以后再整理」（这就是它长到 6423 行的原因）；
    ③ **git 处理 = `commit` 本轮全部改动 + `push` 当前分支**。**收工本身即对 push 的标准授权**（覆盖 §5#7 的"平时不 push"）；force push 仍禁。
    **没做完这三件不算收工。**
13. **用户拍板必须白话（2026-07-10 用户定，硬规矩）**：凡需用户拍板的技术决策，呈现时**禁用代码变量名/内部代号/批次号当主语**（用户没有代码上下文，"E4/B-O/north_axis"这类词无意义）——必须用大白话讲清：① 背景（我们在干什么）② 问题（撞上了什么）③ 每个选项的**后果**（选了会发生什么、代价是什么）④ 推荐+理由。技术细节/代号放链接或括号供查，不作叙述主体。判卷/审阅产物里的技术版照旧，白话义务只在**面向用户的拍板请求**这一层。

14. **Comate 内网模型网关 = 备用「人工中继」通道**（2026-07-27 用户拍板登记，需要时才用）：
    只做**不碰代码**的活（规划出稿 / 方案评审 / 算法思路），主控出**脱敏 prompt** → 用户在 Comate 侧跑 → 贴回；
    ⛔ 不接为 worker 席位。**⚠️ 当前 dev container 连不上该内网域名**；且本沙箱把**任何**域名都「解析得通」
    ⇒ **DNS/TCP 连通性测试在此环境全是假阳性**，只能用不带凭证的真实 HTTP 请求判可达。
    数据流向风险 / 待确认三项 / 升级为真席位的技术路径 → [规约 §9](guides/codex_execution_protocol.md)。
---

## 6. 文档索引

| 文档 | 作用 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 本文 — 项目结构 + 当前状态 + 约定 + 索引（根文件）|
| [plan.md](plan.md) | **活计划**：当前焦点 + 未闭合缺陷 + 本轮日志 + 近细远粗待办。⛔ 翻篇的日更不留在这里 |
| [decision_log.md](decision_log.md) | **历史决策唯一归档**：里程碑时间线 + §5.1–5.13 决策详档 + 变更日志 |
| [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) | **唯一「当前稳定架构」文档**（活）：逐阶段 输入·输出·校验 + 两道门 + 规范不变量 + 接缝缺口 |
| [architecture/harness_versioning.md](architecture/harness_versioning.md) + [harness_versions.yaml](architecture/harness_versions.yaml) | **harness 版本管理**（2026-08-22 用户定）：能力点=建筑复杂度 × 图纸方言两根轴；**探索性不进版本、走完循环①–④对过 gt 的才进**；`known_gaps` 必填 |
| [architecture/as_drawn_layer_contract.md](architecture/as_drawn_layer_contract.md) | ⭐ **as-drawn 层契约**（2026-08-24 六审 APPROVE 时随层落库）：谁能写观测层 · 画框/标定是已声明盲区 · 记成绩的四道闸 |
| [architecture/reading_pipeline_architecture.md](architecture/reading_pipeline_architecture.md) | ⭐⭐⭐ **0_reading 唯一架构文档**（2026-08-25 用户令单独成文）：当前七步形态（量=代码·**认=模型**·11 道不读 gt 的门）· **目标形态 = `reading-agent` 拿 SOP+判例库+工具箱自选工序** · 三层归属（量具/工序/出口）· SOP≠判例 · 两条不让给 agent 的边界 · 演进路线 · **六条已知盲区**（单色图 / 「洞口=空档」是方言 / 尺寸只定尺子）|
| [architecture/judge_grade_model.md](architecture/judge_grade_model.md) | **判卷子系统活规格**（gate② grade：reading+correction·平面+立面·三档色·容差带；§8b 开放 backlog=墙粒度/立面窗移位vs变尺寸/Hungarian/ambiguous/非方形）|
| [guides/new_case_guide.md](guides/new_case_guide.md) | **主 Agent（编排器+judge②）操作手册**：换主控模型读此接手 |
| [guides/reading_correction_split_guide.md](guides/reading_correction_split_guide.md) | **本批开发指南**（2026-08-23）：reading/correction 新分工 + 只判答案不判过程 + 八条硬纪律 + 验收尺度 |
| [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md) | **Claude 编排 / Codex 执行**协作规约：分工 + 省上下文机制 + 通道/沙箱校准 + 审阅反转 + 兜底纪律 |
| [capability/](capability) | **识图→建模能力主线**：`recognition_modeling_capability.md`(质量主线) · `reading/improvement_methodology.md`(**reading 提升唯一管理文档**：诊断+Phase A/B/C+CV 工具箱方法论+决策) · `floorplan_redraw_strategy.md`(两步法策略/POC 史) · `pipeline_0-5_capability_upgrade_suggestions.md`(C2/C3/C4 复杂度升级) |
| [proposals/](proposals) | **未落地的设想 / deferred 设计**（一旦动工搬进 capability，不两处并存）：`geometry_first_zonification.md`(再拓扑支线,休眠) · `editable_geometry_confirmation.md`(可编辑几何确认,DEFERRED) · `cad_to_gt_extraction_plan.md`(CAD→gt,设计待审) · `role_binding_phase2.md`(role 确定性绑定 phase-2,DEFERRED·2026-07-05 抽出) · `j23_geometry_judge.md`(J23 几何 judge,P2 DEFERRED·2026-07-05 抽出) |
| [reference/](reference) | 稳定参考：`pivot_criteria.md` · `open_model_guide.md` · `drawing_to_model_research_landscape.md` · `split_pairing_kernel_reference.md` · `InterZone_Surface_Matching_TechNote.md` |
| [deferred/](deferred) | 搁置（等外部依赖）：`idfpy_embed.md` · `token_optimization.md` |
| [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) | **活文档**：本项目侧对下游 subagent 代码的 hotfix 记录（备份在 `backup/src_history/`）|
| [logs/](logs) | **过程痕迹**（非活文档；纪律见 [logs/README.md](logs/README.md)）：`reviews/`=交叉审阅（`request/` ask + `verdict/` 裁决 + `execution/` 执行日志，见 §5#8）· `experiments/`=独立测试/审计/A-B/诊断 · **`worklog/`=翻篇的日更与状态摘要归档** · `renders/`=gitignored 图 |
| [logs/worklog/](logs/worklog) | **日更归档**（2026-08-18 从 CLAUDE.md §2 / plan.md 搬出，逐字未改）：`status_digest_to_2026-08-17.md`(§2 历史节点摘要) · `2026-08_plan_log.md` · `2026-07_plan_log.md` · `2026-06_backlog_closed.md` |
| [archive/](archive) | 历史归档（已被取代/已实现/已 close）：`architecture.md` · `pipeline_validation_build_plan.md` · `rules_md_split_map.md` · `twostep_architecture_diagram.md` · `2026-06-09_..._refactor_handoff.md` |
| [../case_tests/test_baseline/](../case_tests/test_baseline) | baseline 方案 [README.md](../case_tests/test_baseline/README.md) + 注册表 [index.md](../case_tests/test_baseline/index.md) + gt [gt/README.md](../case_tests/test_baseline/gt/README.md) |
| [../skills/intake_pipeline/](../skills/intake_pipeline) | 0–5 阶段 skill 演进源（唯一 skill 库）|
| [../.devcontainer/README.md](../.devcontainer/README.md) | 多端开发环境指南 |
