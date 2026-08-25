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

- **CLAUDE.md ≤ ~400 行**（2026-08-18 清理后 = 341 行）；**§2 的索引表 ≤ 15 行**。
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
| [../scripts/](../scripts) | 总启动 `run_full_pipeline.py`（`--reading-from`/`--intake-from`）；`tool_scripts/`=render×N + `run_stage.py` + `record_baseline.py` + `render_geometry_viewer.py` + `render_gt.py` + `gt_from_dxf.py` + `inspect_dxf.py`；`glm_code.sh`=GLM 席位启动器（默认 **glm-5.3**）+ `deepseek_code.sh`=DeepSeek 席位启动器（默认 **deepseek-v4-pro**，**⛔ 按量扣余额、与管线共用**）——两者**凭据只注入子进程，勿全局导出 `ANTHROPIC_*`**；家族版图见 [codex_execution_protocol §1](guides/codex_execution_protocol.md)|
| [../tests/](../tests) | ⛔ **当前红着**：pytest **3010 passed / 1 failed / 3 errors / 13 xfailed**（2026-08-25 主控权威全量实测；四项同源见 plan.md **F-93**，与工具箱转正无关，08-24 提交上复跑同样红）（**全仓默认并行** `-n auto`，16 核 4.5–8 分钟；串行 `-n0` 15–26 分钟。跑测三档节奏 + 「受影响子集」工具见 [codex_execution_protocol §7.5](guides/codex_execution_protocol.md)）（kernel/checks/judge/orchestrator/gt/interzone/schedule/viewer/flow/runner/grade/run_config/isolation/view_manifest/c2_b2_v3/c2_b2b_envelope_transform/c2_va_applicability/gt_schema/output_coordinate_×5/e4_relative_north_axis_e2e/c2_b5_source_routing/c2_b5_host_resolution/c2_b5_parent_and_verts/c2_b5_artifact_trust/c2_b5_legacy/reading_line_style_visibility/audit_remediation_accepted_inputs/tarch_converter_p{0,1,2}/tarch_elevation_must_red/**tarch_converter_reproducibility**/**gt_promotion_path**〔含 25 格 `mutation` 源码变异矩阵，默认收集内〕/gt_overlay…）|
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

> **⭐⭐⭐ 2026-08-25 晚 · 当前唯一口径 banner**
> **分支 `08.23_AsDrawnReading`** · 支线 `toolbox_into_src_08.25` @ `283e868`（跨家族 APPROVE，**待合并**）。
> 逐段全档 → [plan.md 本日](plan.md)。
>
> **① ✅ 合并阻塞已全清 + ✅ 支线已回并**（两步都跨家族审过）：**F-93** `b3e0a32` · **F-94 A 案** `91ae82d`
> （16 脚本自举 + **AST 机械锁**）· 支线 `toolbox_into_src_08.25` 于 `0182bea` **零冲突回并**。
> 全量 **`3017 passed, 13 xfailed`**。⭐⭐ **那道新锁的第一次真实捕获就发生在合并上** ——
> 它点名支线带进来的 `reading_toolbox.py:39`（import `src` 无自举），补上后转绿。
> ⚠️ GLM 裁定：锁 = **在枚举过的暴露面上把「忘关门」从静默变响亮**，⛔ **不是根治** ⇒
> **B 案 = 债 D-2「中高紧迫、本批收尾前后排期」**（覆盖外仍有活例 `tests_scripts/deepseek_review.py`）。
> ⭐ 派工单累计题错 **26/26**。
>
> **② ⭐⭐ 答案直喂内核，撞出两条现行管线撞不到的缺陷**（探索档 ⛔ 永不作成绩）→
> [实验档](logs/experiments/2026-08-25_kernel_probe_from_gt/README.md)：**内核不是卡点**，但 **R0 的 38 个 cell 带 `polygon` 的 = 0**
> ⇒ **C2 多边形路径从未被内核吃过** ⇒ **F-95** 顶点规范化毁凹多边形（97.731→226.457；⛔ 已有 L 形锁没分辨力）· **F-96** 跨层碎片无守卫。
> ⭐ 6 cm 已溯源到原始 DXF：四处墙厚同为 120、**1F 右半段整体南偏 60.3 mm** ⇒ **原图就这么画的**。
>
> **③ ⭐⭐ gt 该录「原图」还是「修复后的建筑」**（用户 08-25 提；全档 plan.md 三之三）：同意「加校验」与「误差归 correction 吸收」；
> **「录入时就修复」改落点** = 用户 08-20 定的**三层**（忠实原始层 + 显式不规整清单 + 按出模规则派生的答案层）。
> ⛔ 实测：纯坐标分不开「真墙」与「画图偏差」⇒ **「gt 加校验」与 R-6 是同一件事**；R-6 工作量**下调**。
>
> **④ ⭐⭐⭐ 一体改备料已到，我方核心倾向被证伪** → [GPT 设计答复](logs/reviews/verdict/2026-08-25_reading_correction_unification_gpt_design.md)：~~吃两条面线~~ ⇒ **吃「带原始引用的【多形态】墙证据」**（sm24 实物 4 堵墙是单条实心带）。
> ⭐ **基准归属更正**：不是「旧 reading 自述中线」，**是 correction 的提示词在要求中线**
> （`pipeline.py:365-369` 逐字 `wall CENTERLINE`）⇒ 一体改必须动那两句。
> ⇒ **F-97**：新识图产物会进提示词收集器的 `others` 桶**进提示词**，而识图门只看 `*_view.json`
> ⇒ **静默地半喂进去**，⛔ 比「喂不进去」严重。
> 给 sol 的讨论稿已累计式改写至最新 → [讨论稿](logs/reviews/request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md)。
>
> **⑤ ⏭ 下一步**：~~清阻塞~~ ✅ → ~~支线回并~~ ✅ → **一体改**（⭐ **卡在「与 sol 讨论」，需用户拉人**）→ 拿 sm25 撞 C2（F-95/F-96/F-91/F-92）· gt 层（R-6+校验）并进其后。⭐ **可并行推进且不依赖 sol 的**：**F-90** 楼层 id 映射（撞 C2 的前置）。

> **已翻篇的 banner（均逐字搬入 [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)）**：
> **08-25 收工**（reading 架构定稿 · 管子拆 9 工序 · C2 首次被真正量过 · 工具箱转正 APPROVE · F-93/F-94）·
> **08-24 收工**（六审 APPROVE·gt 放行书写 · 五审 `band_collapse` · 可评分分母+判分器落成 · 模型真进环）· **08-23 收工**（as-drawn v2 三层 · 语义去写死化 · 两轮 REJECT · R-6 更正）· **08-23 早间**（sm25 gt 入库 ·
> 判分首次跑通 · 真错只有三条且同源 · 推翻 F-78）· **08-22**（F-69 真因 · **开发循环六步** ⭐ 仍有效 ·
> harness 版本管理）· **08-21 战略**（核心已进 §0.0；历史 reading 解剖 · 离线夹具 + 四道硬门）·
> **08-20**（707 复现 · 立面载体方言层 F-65 · C2 首考 94.4%）· **08-16 reading 口径**（已被后续覆盖）。

### 2.1 最近节点索引

> **⛔ 本节只放索引，不叠叙述。** 当前轮次的逐日全档 → [plan.md](plan.md)；
> 已翻篇的日更 → [logs/worklog/](logs/worklog/)；
> **2026-08-17 及更早的节点摘要原文（逐字未改）→ [logs/worklog/status_digest_to_2026-08-17.md](logs/worklog/status_digest_to_2026-08-17.md)。**

| 日期 | 一句话 | 详档 |
|---|---|---|
| **2026-08-25 晚** | ⏳ **清合并阻塞已派发**（F-93/F-94，施工 Claude / 审 GLM）· ⭐⭐ **答案直喂内核**撞出 **F-95**（顶点规范化毁凹多边形 97.731→226.457，且已有 L 形锁**没有分辨力**）与 **F-96**（跨层碎片无守卫）· 6 cm 偏差**溯源到原始 DXF**（四处同为 120 墙，1F 右半段南偏 60.3 mm，原图如此）· ⭐⭐ **gt 三层立场**（加校验与 R-6 是同一件事）· ⭐⭐⭐ **GPT 跨家族证伪我方核心倾向**（→ 多形态墙证据）+ **基准归属更正**（是 correction 提示词在要中线）+ **F-97 静默半喂路径** | [实验档](logs/experiments/2026-08-25_kernel_probe_from_gt/README.md) · [GPT 答复](logs/reviews/verdict/2026-08-25_reading_correction_unification_gpt_design.md) · [派工单](logs/reviews/request/2026-08-25_merge_blockers_f93_f94.md) |
| **2026-08-25** | ⭐⭐⭐ **reading 架构定稿并单独成文**（量具/工序/出口三层归属 · SOP≠判例 · 九条盲区）· **管子拆成 9 工序 + 工具箱 CLI**（产物逐字节相同）· **T 形接头已解**（`merge_m` 彻底不承重）· **grade 图落成** · ⭐⭐ **C2 首次被真正量过**（L 形 8 顶点逐点对上、只差半个墙厚；但 **F-91 立面多平面为空** / **F-92 cell 多边形未用** / **F-89·F-90 两侧都判不了分**）· **工具箱转正跨家族 APPROVE** · ⛔ **F-93 全仓已红两天**（gt 晚于锁一天入库）· **F-94 `.pth` 合并阻塞** · 派工「停下上报」累计 **23/23 全是派工方题错** | [架构](architecture/reading_pipeline_architecture.md) · [裁决](logs/reviews/verdict/2026-08-25b_toolbox_transplant_crossreview_glm_verdict.md) · [plan.md 本日](plan.md) |
| **2026-08-24** | ⭐⭐⭐ **模型真进环**（perception 独立成文件：族角色 + 配对选择 + 「认不出来」；代码穷举候选**无阈值**）· ⭐⭐ **两把尺子互补是实测**（作弊在 gt 侧 93.3→97.3、在原图对账上 49 条违规）· 立面结构线判据 v2（清空 runs 从 24/24 → 0/24）· 新增两条判据（自洽重算 / 门窗族落位）· 登记 **F-86** · 实验 README 重写为纯 v2 口径。晚间：⭐⭐⭐ **可评分分母 + reading 判分器落成**（sm25 1F 108 目标 / 100% / 98.2%；作弊 0%）· 登记 **F-88** · ⛔⛔ **跨家族三审 REJECT**（新作弊=把真的漏读说成洞口 · 我的单像素变异从没跑到消费者）⇒ 补四道门 · 登记 **F-87/F-88**（F-88 已查清=只污染溯源、不动几何）。**夜间连打四→六审（GLM）**：四审证伪我两个数 · 五审 `band_collapse`（没有一个假数却优于诚实、八门全绿）· ⭐⭐⭐ **六审 APPROVE，gt 放行书写**，落 [层契约](architecture/as_drawn_layer_contract.md)，记成绩四道闸 2/4 已做（剩 `span_min` 签字 + 冷启首考，待用户）| [实验档](logs/experiments/2026-08-23_as_drawn_reading_prototype/README.md) · [RESULTS_v2.json](logs/experiments/2026-08-23_as_drawn_reading_prototype/out/RESULTS_v2.json) · [plan.md 本日](plan.md) |
| **2026-08-23** | 上午：sm25 gt 签字入库 · **判分首次真正跑通** · ⭐⭐ 全案对答案「**真错只有三条且同源**」· 推翻 F-78 · 登记 F-83/84/85。下午起分叉 `08.23_AsDrawnReading`：**as-drawn v2 三层实现** · **语义去写死化**（颜色族发现 + 指派外部化）· ⛔ **两轮跨家族审均 REJECT** · ⭐⭐⭐ **用户定新分工与判分口径 → 本批开发指南成文** · R-6 更正 | [指南](guides/reading_correction_split_guide.md) · [实验档](logs/experiments/2026-08-23_as_drawn_reading_prototype/README.md) · [裁决](logs/reviews/verdict/) |
| **2026-08-22** | **⭐⭐⭐ orchestrator 亲自下场跑通 sm25 1f+2f**：F-69 真因 = **门窗在独立颜色图层上而现行掩膜看不见它**（青色像素数实测 0）· A×B 对账落成代码规则（像素定哪段是洞口、刻度定边界）⇒ **31/31 扇窗坐标取自尺寸链、零笔无证据、12 条链闭合 0.0 mm** · **跨 case 迁到 sm24：11 扇历史窗逐个复现宽度全同** · 修 F-73 · 登记 F-74/75/76/77/78 | [全档](logs/experiments/2026-08-22_orchestrator_hands_on/README.md) · [SOP](logs/experiments/2026-08-22_orchestrator_hands_on/sop_plan_reading.md) · [缺口清单](logs/experiments/2026-08-22_orchestrator_hands_on/tool_gaps.md) |
| **2026-08-21 夜** | **⭐⭐⭐ 战略换挡：跑测=升级 harness 不是拿分** · 历史 reading 解剖（27 份独立、19 个满分是同一份复用）· **离线夹具 + 过程指标 + 四道硬门**（此前「改脚手架伤没伤 reading」只能花钱跑抽）· A/B 互为盲区实证 → CHAIN-PLACEMENT 门 · F-35 侧车带回 · 登记 F-69/70/71/72 | [解剖档](logs/experiments/2026-08-21_historical_reading_dissection/README.md) · [作业设计](logs/experiments/2026-08-21_historical_reading_dissection/orchestrator_hands_on_plan.md) |
| **2026-08-21** | **⭐⭐ sm25 gt 签字晋升入库（首份多层+非凸答案）· C2 首考已判分**（外轮廓 94.4% / 窗 8/15，病灶=F-69 极性反了·把墙垛当窗）· 转换器三修 + 判卷两修 · 四处「肉眼看不见的一点点错」· 停下上报 **8/8** 全是派工方题错（累计 22/22）| [plan.md 本日](plan.md) · [gt](../case_tests/test_baseline/gt/sm25-L_anchor/) |
| **2026-08-20** | **✅ 07-07 水平在当前基座复现（Sonnet 9/9·7/7·15/15·0.0m）** · 转换器多层化 + **立面载体方言层（F-65）**落地 · 满分掩盖外轮廓偏移 · 停下上报 **4/4** 全是派工方题错 | [plan.md 本日](plan.md) · [专项 §10](capability/reading/improvement_methodology.md) |
| **2026-08-19** | **三臂判别**：Sonnet 首抽零返工 4/4·3/3 · GPT 历史栈一轮返工 4/4 · Haiku 两臂皆崩 ⇒ 病灶 = 眼估入口敞开；根治归专项 | [plan.md 本日条目](plan.md) · [专项 §9](capability/reading/improvement_methodology.md) |
| 2026-08-18 | 治理换挡（§0）· 707 完整环境还原仍不回来（22 抽）· 新建 reading 回归门 · **全案报告已出** | [plan.md](plan.md) · [全案报告](logs/reviews/request/2026-08-18_reading_regression_external_investigation.md) |
| 2026-08-17 | 707 复现前置三件落地（F-51 单帧化 / `scale_origin` 退回 SHOULD / 跨轴合法出口）+ 全仓首次真零红 **2835 绿** | [plan.md](plan.md) |
| 2026-08-16 晚 | 移植基座一次性普查：40 分钟撞出 7 条（此前串行一天撞 3 条）· 修 5 条 · +135 锁 | [worklog](logs/worklog/2026-08_plan_log.md) · [sweep README](logs/experiments/2026-08-16_substrate_sweep/README.md) |
| 2026-08-16 | 方法论转向「读 diff 不猜变量」· 撤能力封口（A3）证伪 | [worklog](logs/worklog/2026-08_plan_log.md) · [行为清单](logs/experiments/2026-08-16_707_repro/behavioral_change_inventory.md) |
| 2026-08-15 | reading 重启七抽全否 · ⭐ 基准本身被查出「不可审计」 | [worklog](logs/worklog/2026-08_plan_log.md) · [实验档](logs/experiments/2026-08-15_reading_restart/README.md) |
| ≤2026-08-14 | 验收首次达成（一口气推完不出错·连跑 3/3）· 下游断链真因坐实（截断⇒幽灵 tool_call⇒400）· **全链首次跑到 EnergyPlus（0 Severe）** · F-8…F-21 缺陷批 · 判卷身份与度量批 | [worklog](logs/worklog/2026-08_plan_log.md) · [status digest](logs/worklog/status_digest_to_2026-08-17.md) · [2026-07](logs/worklog/2026-07_plan_log.md) |

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
    `wc -l AI_agent/CLAUDE.md AI_agent/plan.md` —— **CLAUDE.md >400 行 或 plan.md >900 行 或 plan.md 里出现了上一轮的日更**
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
