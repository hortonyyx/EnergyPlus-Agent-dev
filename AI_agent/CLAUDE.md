# 多模态输入 Agent 项目管理文档

> **本文件 = 项目最基础的根文件**，每次会话/换主控模型时首加载，作用是**简要说明项目结构 + 当前开发状态**。
> 只放长期稳定的"是什么"和此刻的"在哪"；**待办看 [plan.md](plan.md)，历史决策看 [decision_log.md](decision_log.md)，
> 当前架构细节看 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)，标准工作流看 [guides/new_case_guide.md](guides/new_case_guide.md)。**
> 三者职责互斥：本文不叠历史、不堆待办。

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
| [../scripts/](../scripts) | 总启动 `run_full_pipeline.py`（`--reading-from`/`--intake-from`）；`tool_scripts/`=render×N + `run_stage.py` + `record_baseline.py` + `render_geometry_viewer.py` + `render_gt.py` + `gt_from_dxf.py` + `inspect_dxf.py`；`glm_code.sh`=GLM 席位启动器（凭据只注入子进程，**勿全局导出 `ANTHROPIC_*`**）|
| [../tests/](../tests) | pytest **1786 绿 + 10 strict xfail**（**全仓默认并行** `-n auto`，16 核 4.5–8 分钟；串行 `-n0` 15–26 分钟。跑测三档节奏 + 「受影响子集」工具见 [codex_execution_protocol §7.5](guides/codex_execution_protocol.md)）（kernel/checks/judge/orchestrator/gt/interzone/schedule/viewer/flow/runner/grade/run_config/isolation/view_manifest/c2_b2_v3/c2_b2b_envelope_transform/c2_va_applicability/gt_schema/output_coordinate_×5/e4_relative_north_axis_e2e/c2_b5_source_routing/c2_b5_host_resolution/c2_b5_parent_and_verts/c2_b5_artifact_trust/c2_b5_legacy/reading_line_style_visibility/audit_remediation_accepted_inputs/tarch_converter_p{0,1,2}/tarch_elevation_must_red/**tarch_converter_reproducibility**/**gt_promotion_path**〔含 25 格 `mutation` 源码变异矩阵，默认收集内〕/gt_overlay…）|
| [../case_tests/](../case_tests) | `0_reading_tests/` + `e2e_tests/`(含 sm20_anchor/sm21_anchor) + `test_baseline/`(方案+注册表+gt) |
| `$ENERGYPLUS_EXE` | EnergyPlus 引擎；解析序 env→PATH→硬编码默认。容器内 25.1.0、宿主 Windows 25.2.0（patch 差异，数值对齐以容器为准）|
| [../data/weather/Shenzhen.epw](../data/weather/Shenzhen.epw) | 默认 EPW 气象 |

### 1.4 技术栈
LangGraph + LangChain（`init_chat_model` 路由）；多模态走 base64 图块；结构化输出 `with_structured_output(IntakeOutput)`；
EnergyPlus 经 `WorkflowTool.run_simulation`（eppy + ConverterManager，idfpy 切换搁置）。

### 1.5 仍有约束力的关键不变量（详档见 [decision_log.md §B](decision_log.md)）
1. **分工铁律**：LLM 只做 感知 + 校正判断 + 物理语义；**代码做所有几何（建模+切配）+ 装配**。
2. **全局唯一世界坐标系**：原点 = 整栋投影最大边界 SW 内角，禁每层本地原点。
3. **交接契约 = IntakeOutput Pydantic 11 字段**（[state.py](../src/agent/state.py#L23)）；下游 9 subagent 消费、不归本项目管。
4. **gt 铁律**：评测答案 `case_tests/test_baseline/gt/<case>/gt.json` **只 gate② judge / 人 可读**，gate①/执行器绝不 import（dev/prod 一致 + 防照抄）。
5. **精确坐标容差带由确定性层判**（核坍缩规范值 + gate① 带容差不变量），gt/judge 只判布局/计数/窗位定性。
6. **建筑复杂度可扩展性铁律（2026-07-03 用户定，硬约束所有决策）**：**每个决策必须为未来建筑复杂度升级留路**——现架构（正交·**共底面盒子**）刻意保留了升级到复杂体量（**非方形 / 退台 / 挑空双层高 / 中庭竖井**）的可能：不变量 #1 判断-几何分工、#2 单一世界坐标、版本化 schema、#3 稳定契约都是为此设的**接缝**；复杂体量 = schema 加槽位（per-floor footprint / 变高区 / void）+ kernel 实现扩展（含休眠支线 [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md) 热区积木 = kernel 策略替换、**非架构推翻**），都在接缝内长。**不得**把"共用 footprint / 每层满铺楼板 / 固定层高"这类**当前简化假设烤死到无法松动**——纯只适用当前情况（不能长到复杂体量）的方案**没有意义**。复杂体量本身是远期 defer，但**任何当下决策都要过一遍"这条路以后能不能长到复杂体量"**。风险不在架构、在"烤死的假设"，本条即那道保险。
7. **环节的控制边界 + 成绩归因（2026-07-31 立 → 08-01 校准 → ⭐2026-08-02 用户重订，
   [调研报告 §0.4/§0.5](logs/reviews/verdict/2026-08-02_reading_regression_controller_cv_investigation.md) 为唯一口径，
   下述 07-31/08-01 两版判据凡与本版冲突处**全部作废**）**：
   本条现在管两件事——**谁不许伸手（端到端主控）** 和 **成绩怎么记账（provenance）**；
   它**不再**禁止「环节内部存在更强 agent 或针对性反馈」。
   - **⛔ 端到端主控（本 Agent）对某环节内部：只能启动与接收。**
     ✅ 可以：创建 job / 传入**冻结的** case bundle + profile / 等待 / 接收 `status + output + evidence manifest`；
     dev 期编排（建工作区 / spawn / merge / 跑确定性工具 / 决定跑什么）仍合法；**主控兼任 judge 仍合法**。
     ⛔ 不可以：写自由文本 directive / feedback；**看了图之后指导 worker**；替它挑 CV 参数或返工区域；
     操作环节内部会话；**接触 gt 之后把任何结论送回同一个 run**。
   - **✅ 环节内部允许有自己的 controller（08-02 新增许可）**：reading 可以配置属于
     `ReadingService` 内部的控制 agent 去指挥弱 VLM，条件是——
     ① 与端到端主控**彻底解耦**（外部看仍是 reading 自己走完输入→输出）；
     ② **档位不高**（DeepSeek v4Flash 级或以下、thinking off、结构化输出、短上下文）；
     ③ **有界**：最多「一次任务计划 + 一次局部返工」，不重抽整栋，**不得直接写最终坐标**
     （最终 stroke 必须来自 worker + 工具证据）；④ 它是**权衡方案不是永久架构**，后续要代码化 / 降档 / 撤除。
   - **⛔ 成绩记账 = 两条正式 lane + 一个 dev 期职能（⭐2026-08-02 晚用户当面更正，
     此前记成「三条并列 lane」**是错的**）**（配 `reading_mode` provenance 块：
     `reading-agent` / `reading-worker-agent` 各自模型、`reading-agent` 是否看图、返工轮次、
     工具箱版本、隔离档）：
     - **autonomous**（目标 VLM + 冻结工具箱，**零 `reading-agent`**）= **北极星、长期目标**；
     - **controlled**（+ `reading-agent`）= **当前批次的验收 lane**。
     **controlled 完全算真实工程成功**，但**不得记成「弱模型独立满分」**；
     autonomous lane 必须一直保留，否则不知道离「本地开源 VLM 自主完成」还有多远。
     - **另有一个 dev 期开发者职能（不是 lane、不产生正式成绩）**：允许**最强模型观察 reading
       （乃至其他环节）的内部过程**，提炼方法论 / 搓适配工具 / 改进流程，**作为成果资产纳入项目开发本身**。
       角色归属用户**倾向 orchestrator 兼任**（可再议）。**四条铁律**：
       ⛔ 不能给项目生产本身提供**信息** · ✅ 可以提供思路 / 方法 / 工具 ·
       ⛔ 这种模式下的**跑测不作为正式成绩** · ⛔ **一个 case 的收官验收必须脱离该角色完成**
       （验收时跑的是已固化工序 + 已冻结工具箱，该角色不在场）。
     - **⭐ 本批次目标口径（用户 08-02 晚更正）**：**不是**「autonomous 拿到好 reading」——那是北极星；
       **本批 = 在 `reading-agent` 在场的形态下，sm21 与 sm24 两个 case 都拿到接近满分**，
       本质是**先恢复到「Haiku 做 sm21/sm24 满分」那个状态**（那时本就有高档模型部分介入），
       只是把当时 orchestrator 的**临场介入固化成 `reading-agent` + 与 orchestrator 隔离 + 降档到 Flash**。
       ⇒ **不是提高分数，是用合规形态重新达到一次。** 拿到之后再尝试撤掉 `reading-agent` 验证 autonomous。
   - **⛔ 隔离原则改写（08-02）**：**严格限制可见信息与写出边界，不限制在合法输入上采用何种计算方法。**
     要防的是漏题与污染（gt / baseline / judge / 其他 run / 历史答案 / 网络外传），
     **不是**模型用了哪种算法 —— 按命令形态封杀通用 CV 编程（`python -c`、临时脚本）属于**能力封口**，
     它封掉的正是 07-02 Sonnet 那条成功路径。
   - **judge 出口不变**：判定不过 ⇒ **整轮盲重抽、零信息**（相当于另外做一次）；
     judge **不得**告诉执行环节「哪里错了、该怎么改」。（注意区分：**环节自己的 controller 做局部返工是允许的**，
     受 judge 约束的是**跨环节的评判者**。）
   **⚠️ 已排查完的违规点（2026-08-01 全面排查，[审计报告](logs/experiments/2026-08-01_controller_in_production_audit/README.md)）**：
   ① **pilot 停等 review + `feedback.md` 续作通道**，且「停下等审阅」**写在产品 skill 库
      `session_kickoff.md` 里**（不是 dev 脚手架）⇒ 读图器被自己的启动文件命令停下等人；
      **07-07 的 8/8 正由此而来** ⇒ 该成绩非无监督基线。**08-01 已改**（自检后继续，无 review 点）；
   ② **per-run directive**（198 行，主控看着上轮失败当场写）⇒ 待拆分：通用纪律沉淀进 standing 文档 /
      针对上轮错法的删除。**⚠️ 与补门成对做**——其 §2、§4.7 实为两条缺失 gate① 检查的替代品，只删不补即退化；
   ③ **预扫参数由主控临时挑**（跑预扫本身合法，参数必须是随产品发布的固定档）；
   ④ **污染闸门 `check_feedback_text` 是纯词法**，挡不住裸坐标与具体错处 ⇒ 上述通道无实质约束。
   **⚠️ 07-31 原文列的另两条已作废**（v1 判据过宽所致）：~~识图段无代码执行器~~、~~judge② 由主控担任~~
   —— 按 08-01 校准判据**均属合法 dev 编排**。
   **⭐ 08-02 重要改判**：上面 ①–④ 违的是**「端到端主控伸手」**这一条，**仍然成立**；
   但**同样的动作若由 `ReadingService` 内部的 controller 做（解耦 + 低档 + 有界 + 如实分账），现在是允许的**。
   即：**要禁的从来是「谁在做」和「记成谁的成绩」，不是「reading 内部有没有控制」。**
   详 [08-02 调研报告](logs/reviews/verdict/2026-08-02_reading_regression_controller_cv_investigation.md)
   · [08-01 排查报告](logs/experiments/2026-08-01_controller_in_production_audit/README.md)
   · [07-31 缘起](logs/experiments/2026-07-31_sm24_e2e_retry/SUPERVISION_CONTAMINATION.md)。


---

## 2. 当前开发状态

- **⭐⭐⭐ 最新（2026-08-09 收工）= F-18 修法 + 返工 + ⭐sol 两轮交叉审全过 · F-9 路线②设计稿已出**
  （全档见 [plan.md「六之十三」](plan.md)）。全仓 **2339 绿 / 10 xfail / 0 红**（本日 2323 → 2339，零回归）。
  - **F-18 = 窗宿主自洽门用浮点精确相等**（`!=` 比两条不同算路得到的同一个世界跨度，
    实测偏差 1–4 ULP ≤2e-15 m）⇒ 判真实产物「被篡改」并**裸抛终止整条 flow**。
    **不是几何错。** 修法 = 三处比较改用 B5 自己的 `window_host_span/plane_epsilon_m`（1e-9）。
    ⭐ 该容差**本就存在、同文件用了 11 次、其中一处就在失败那行上面 14 行** ⇒ **不是缺容差，是门没用**。
  - **⛔⛔ 本轮最该记住的一条 —— 「谁写谁不批」防的不是粗心，是作者对自己推理的系统性盲区**：
    Claude 侧施工席撞月度额度中断，orchestrator 接手做完 ⇒ **作者=验证者**。
    orchestrator 自验做满（全仓绿 + neuter 转红 + 真实产物通过，**外观完全合格**），
    **sol 仍抓出 1 MAJOR**：headline 正向锁用的是**变换前**宿主线 `[0.12,14.88]`，
    而真实失败发生在**变换后**的 `[0,15]` 上 ⇒ **那个用例恢复 `!=` 后仍是绿的、根本不是锁**。
    ⇒ 这正是 orchestrator neuter「只红 2/4」的原因 —— **我只观察到症状，没诊断出原因**。
  - **⛔⛔ 同一类错误（从测量过度外推）同一批里连犯两次，两次都是交叉审抓的**：
    ① MAJOR-1 = 从「数值看起来难看」外推到「能复现缺陷」；
    ② 返工时新引入的 MINOR = 从一组实测外推成普适定律
    （「宿主线长为 2 的幂 ⇒ 永不产生 ULP」，sol 反例 `p1=2.6317878,L=8,x=7.877522392`
    ⇒ 偏差 −8.88e-16，orchestrator 已独立复算证实）。
    **第二次是在我刚写完「⛔ 不许靠挑数字、必须实测」那条纪律之后犯的。**
  - **⭐ 由此定的新纪律**：**回归用例必须自证前提** —— 先断言「旧的错误判据在这个夹具上
    确实会失败」，再断言修法放行；前提破了要**大声报错**，⛔ 不许静默退化成空锁。
    （已落 `tests/test_f18_window_host_float_tolerance.py` 的 `_round_trip_differs`。）
  - **sol 两轮裁决**：[第一轮](logs/reviews/verdict/2026-08-09_f17_f18_crossreview_sol.md)
    = APPROVE-WITH-CHANGES（0 BLOCKER / 1 MAJOR / 3 MINOR）·
    [第二轮](logs/reviews/verdict/2026-08-09_f17_f18_crossreview_sol_round2.md)
    = APPROVE-WITH-CHANGES（0 BLOCKER / 0 MAJOR / 1 MINOR，已修）。**审阅债已清。**
    F-17 复核通过（sol 独立逆序探针验证组件顺序无关）。
  - **⭐ F-9 路线②设计稿 v1 已出**（[proposals/f9_route2_evidence_citation_design.md](proposals/f9_route2_evidence_citation_design.md)，**待用户过目**）：
    **关键发现 = 零件基本都在**，确定性换算 `_advisory_elevation_world_frame` 已存在、
    帧参数 `VaElevationViewBindingV1` 已算出、`source_ids` 通道已存在，
    **缺的只是「让确定性结果当权威」**（源码逐字写着 never authoritative）。
    ⛔ **附带必做**：`_BASE_SIGN` 声明 3 份、**其中一份在 judge 侧** ⇒ 判卷方与生产方各持一份约定、
    可各自漂 ⇒ 届时「判卷说错了」与「生产真的错了」**原理上无法区分**。**轴 B 第五次现形（生产 vs 判卷）。**
  - **⛔ 施工席中断的自述不可信（第二次实证）**：它最后一句「Let me apply the fix」听起来未动手，
    实测工作区**已落 20 行**（helper 已加、三个调用点一行未改）
    ⇒ **纪律：施工席中断后一律以 `git diff` 为准。**（08-08 那次是「中断在 neuter 自查前」，同族。）

- **（同日）2026-08-09 中场 = F-17 修法落库 + 轻门 PASS + ⭐真链路证实解开，撞出 F-18**
  （全档见 [plan.md「六之十三」](plan.md) · [轻门裁决](logs/reviews/verdict/2026-08-09_f17_orchestrator_lightgate.md)）。
  全仓 **2326 绿 / 10 xfail / 0 红**（2323 → 2326，零回归）。落库 `2c8aca3`。
  - **修法 = 三阶段替换「边移边判」**：相 1 只插点不移动 ⇒ 相 2 用**冻结的原始坐标**对全部组件定位、
    命中哪个改哪个分量 ⇒ 相 3 规范化。**恰好恢复 legacy 由 bbox/索引表示【免费】得到、
    v3 顶点环/谓词表示静默丢掉的跨轴独立性。** 同批交付分类修法（cell 环失败改走结构化拒绝）。
  - **⭐ orchestrator 轻门换方向 neuter 两格**（施工席测的是函数内部两格，不重复）：
    ① **接线方向** —— **不动 `_apply_components` 本身**，只把调用点改回逐组件调用
    ⇒ **恰好 Group A/B 转红、零连带** ⇒ 兑现 08-06 判别问法「把调用点改回缺陷形态，锁红不红」；
    ② materialize 删除方向 ⇒ 全仓零红（缺口坐实，见下）。
  - **✅ F-17 已由真链路证实解开**（run `run_2026-08-09_f17_e2e_verify`）：
    真实产物 + 官方入口 + 调用追踪 ⇒ **4 个跨轴 intent 全跑过 `_apply_components` 无异常**，
    footprint `[0.12,14.88]×[0.12,7.88]` → **`[0.0,15.0]×[0.0,8.0]`**（修法前此处必抛非正交）。
    **⭐ 输入无变量是机械可验证的**：`policy_hash` 与 08-08 逐字一致 · `view_manifest` 指纹一致 ·
    `0_reading` 逐字节复制 ⇒ **唯一变量就是修法本身**。
    ⛔ **但分类修法那一半未被验证**（本 run 没产生斜边、那条 try/except 没执行到）——
    **「代码在、锁绿」≠「真链路验过」，不记功。**
  - **⛔ 新登记 F-18 候选**：写入侧 `recompute_window_host_claims` 在最终几何上失败
    （`line_geometry` / `world span`，6–8 个窗，`invariant_no_geometry_commit` **按 F-9 的设计裸抛**
    ⇒ 不归档、直接终止 flow）。**A/B 已证非 F-17 引起**（抑制 envelope 变换后照样失败，8 个窗）。
    **⚠️ 与 F-9 的关系未定性**（F-9 是 `source_geometry_mismatch`，本次是 `line_geometry`）⇒ ⛔ 不许直接归并。
  - **⛔⛔ 轻门量到比「缺一把锁」严重的事**：给 `_materialize_axis_splits` 挂计数器跑遍全部
    envelope 测试（152 passed）= **调用 101 次、插点恒为 0** ⇒ **整套 T-junction／图闭包机制
    从来没有被任何测试执行过**。定性：**继承自旧代码、不记施工席账**（它主动登记了该缺口），
    但派工单那条「⛔ 不许删 materialize」**目前零机器验证**，且正好处在 **F-13 那个危险位置**
    （全绿、看起来多余、实际在为 L/U 形 T-junction 服务）。触发配方已推出，待拍板是否补锁。
  - **⭐ 两条新纪律（都是本轮实犯／实测换来）**：
    ① **权威门的观测通道本身必须可信** —— 施工席自陈：`pytest | tee log | head -20` 会因
       `head` 关 stdin ⇒ `tee` 收 SIGPIPE ⇒ **连带打断 pytest**，而通知里的「退出码 0」
       **其实是 `head` 的退出码**。⇒ 输出直接重定向到文件、退出码单独落一个只属于该命令的文件，
       ⛔ 中间不接任何下游管道（与「`-n auto` 静默 OOM」并列）；
    ② **`run_config.yaml` 必须先于 `provision` 落盘** —— 反了会冻结「flow 默认」策略、
       之后配置一改就撞 policy 漂移门（orchestrator 本轮实犯；**门是对的**，且它打印的 `requested`
       哈希顺带把「唯一变量」从声称升级成机械证据）。

- **（同日上半场）2026-08-09 = F-17 根因实测坐实（推翻立项推断）+ F-8 债「第二面」收口**
  （全档见 [plan.md「六之十二」](plan.md) · [调查报告](logs/experiments/2026-08-09_f17_envelope_cross_axis_chamfer/README.md)）。
  orchestrator 亲跑，**零 LLM 成本 · 只读 · 零生产码改动**；三个可复跑脚本随报告入库。
  - **⛔ 立项推断被实测推翻**：~~「materialize 插中间点后只部分移动 ⇒ 共线三点中间被移出斜边」~~。
    **实测单个组件永远不产生斜边**（同轴双组件也不）。**真根因 = 跨轴组件的顺序耦合** ——
    `_apply_components` **顺序就地**改写几何，但四个组件的 `intervals` 全锚在**变换前**的坐标系；
    第二个组件与第一个正交时，公共角点已被前一个挪出后一个的区间判定 ⇒ **漏移**，
    同时 `_materialize_axis_splits` 又在原位插新点补上 ⇒ **一个直角裂成两点、连成 45° 斜边**。
    **佐证：干净原始几何上四个组件插点数都是 0 ⇒ 插点本身就是顺序污染的产物。**
  - **组合矩阵 15 格全跑零例外**：**跨轴 ⇔ 斜边**（数量 = 4 × x组件数 × y组件数）；
    **中招判据 = cell 碰不碰 footprint 的角**（碰角 4 个全中、不碰角 3 个全正常）。
  - **⭐⭐ 本轮最贵的一条 —— legacy 路径本来是对的，v3 重写把它丢了**：
    `_three_bay_inset()` 用的**正是**真实的 `[0.12,14.88]×[0.12,7.88]`、**同时声明 x/y 两轴**，
    断言跨轴角点两个方向都移对 —— 它走 legacy。**legacy 用 bbox 表示（按索引改，两轴天然独立），
    v3 换成顶点环（改成坐标匹配谓词，谓词在第一次移动后失效）。**
    ⇒ **新方法论：换表示时要专门问「旧表示里有哪些正确性是【免费】的」——
    免费的那些不会有测试守着，最容易在重写中静默蒸发。**
  - **为什么 2323 绿漏掉它**：全仓走 v3 变换的夹具 footprint 环**全部以 `[0,0]` 起**
    ⇒ lo 侧不产生 intent ⇒ **结构上凑不出正交组件对**。**F-5 那族又一次现形**（夹具形态分布 ≠ 真实产出）。
    潜伏属 **B 类**（代码 07-12 出生，08-07 那次是 legacy 形态整段跳过；F-16 一修好就第一次真跑到）。
  - **⛔ 两条出口必须一起修**：cell 碰角 ⇒ **裸 ValueError 炸穿 flow**（同 F-15 第二堵墙）；
    只有 footprint 出斜边 ⇒ 结构化拒绝**归档重抽**，**但重抽永远没用** ⇒ 烧钱到 quarantine
    **且把内核 bug 记在模型账上**。
  - **修法方向已用反事实探针验证**（斜边归零、几何正确 14.76×7.76 → 15.0×8.0）：
    **先在变换前的几何上一次性定位、再统一移动**。⛔ **派工单必须写死：不许砍
    `_materialize_axis_splits`**（探针零插点只因本 case 是矩形，L/U 形的 T-junction 靠它）。**修法未施工。**
  - **✅ F-8 债「第二面」收口，且修法比原建议更省（不搬家，改规则）**：
    `.gitignore:7` 的 `20*_*/` 写于 05-05（`e9d7a2b`）只为挡一份 LangSmith 归档，
    却写成**不限路径的「目录名形状」规则**；**实测该形态目录今天一个都不存在**
    ⇒ **挡不到任何本来要挡的东西，只误伤自己**（`AI_agent/logs/**` 8.4 MB / 238 文件）。
    改为**按位置**限定 `**/backup/**/20*_*/` ⇒ **零迁移零引用更新**。
    顺带查实**原三条 `!` 例外全是死的**（git 无法在已排除目录内再包含，已实测；第三条路径根本不存在）并删除
    ⇒ **「声称在守其实没守」这一族的又一例，这次在 `.gitignore` 里。**
    两面陷阱实测消失（均查 index、⛔ 不看 `status`）。
    **顺带全量链接审计**：311 条内部链接中 **5 条文件在盘上却未入库**（含 CLAUDE.md §1.5#7 引用的
    `SUPERVISION_CONTAMINATION.md`，已入库）· **20 条断链**（登记未修）·
    **新登记「第三面」**：`*.txt`/`*.log` 是全局忽略，同一陷阱换了条规则。

- **（前一节点）2026-08-08 收工 = 接线摸排第一轮跑完 + 三摊修法过审 + ⭐F-16 真链路解开、当场撞出 F-17**
  （全档见 [plan.md「六之九／六之十／六之十一」](plan.md)）。全仓 **2323 绿 / 10 xfail / 0 红**（2289 → 2323，零回归）。
  本轮落库 5 个提交：摸排 `4b77513` · 三摊修法 `15ea05d` · 审阅单修正 `23aed2e` ·
  交叉审裁决 `c8d5ac2` · 真链路验收 `8d17211`。
  - **⭐ 用户 08-07 立项的「接线问题统筹摸排」第一轮完成，且一路做到修法过审 + 真链路验收。**
    **轴 A 在下游侧收官 = 9/9**（立项时「剩 7 个从没人看过」现已全部看完）；
    **盘子比预想小**：`construction`/`material`/`schedule` **整体不在射程内**（完全不碰几何、纯物理语义），
    `intake`/`cross_ref`/`validate`/`simulate` **根本不是 LLM 节点**。
  - **⛔ 立项时的盘子估计两处更正**：① **下游暴露面是「工具参数 schema」不是字段**（ReAct + MCP 工具）
    ⇒ **F-15 那套 JSON-Schema 机械剥除在下游用不上**，要在工具定义侧动；
    ② 拒绝点是 **355 个**不是 19 个，其中仅 18 个 `model_draw_error` + 39 个 `input_integrity_error` 模型可触发。
  - **⭐ 权属发现（解开一处以为会卡的阻塞）**：CLAUDE.md §3 out-of-scope① 管的是下游 9 节点的**「prompt 演进」**；
    **工具定义（`src/agent/tools/`）不是 prompt ⇒ 在本项目权属内**（`zone_tools._reject_if_nonzero` 已有先例）
    ⇒ 下游修法可走工具侧，不触发协作者权属谈判。
  - **三摊修法**（GLM-5.2 验证性交叉审 = **APPROVE**，0 BLOCKER/0 MAJOR/0 MINOR/2 NIT，17 命题全成立，
    独立全仓与 orchestrator 逐字一致）：**F-16**（`WindowV3.floor` 改**代码从 `floor_id` 派生**+ 补上嵌套字段标记机制）·
    **A-1**（`create_fenestration` 摘掉 `multiplier` 参数）· **B-1′**（严格档 fail-open 两处）。
  - **⭐⭐⭐ F-16 定性被摸排改写**：根因**不是**「模型把 id/name 写混」，是
    **「这扇窗在哪一层」有 4 处独立声明**（模型写 name · 模型写 id · 代码按 z_floor 排的 rank · reading manifest 的 floor_ref）。
    ⇒ **轴 B 定义据此扩写**为「同一**事实**的多处声明，**含模型输出内部**」——
    已见三形态：代码 vs 代码（F-13）· schema vs 门（F-15②）· **模型输出内部（F-16）**。
    顺带发现 **F-15② 那次只统一了顶层清单、嵌套这一层原样留着同一个病**，Step 1 一并消掉。
  - **✅ F-16 已由真链路证实解开**（run `run_2026-08-08_f16_e2e_verify`，用户拍板「跑到底」）：
    `floor must match referenced floor name` **出现 0 次**（上一轮三次抽签全死在这条）·
    **`correction_geometry.json` 产出**（模型 draw 通过 parse 层全部门）· 崩溃位置从 parse 层**后移到确定性核**。
    ⇒ 兑现 F-5 教训：**夹具自洽不算数，只有真实产物跑通才算修好。**
  - **⛔ 新登记 F-17 候选（内核 bug，非模型错）**：envelope 变换造出**非正交** cell 多边形
    （`cell RM1F_01: polygon edge 3 is not orthogonal`）。**已实测证实**：模型 14 个 cell **全部 `polygon=None`**、
    `RM1F_01` 是标准轴对齐矩形 ⇒ **多边形是内核 `_apply_components` 自己造的、重抽无用**；
    且是**裸 `ValueError` 全链无捕获** ⇒ **不走归档重抽、直接炸穿 flow**（`attempts/` 零归档），**与 F-15 第二堵墙同型**。
    ⚠️ 机理（`_materialize_axis_splits` 插中间点后只部分移动 ⇒ 共线三点中间被移出斜边）**为推断、未证实**，
    orchestrator 离线复现卡在缺上游 `verified_window_inputs` ⇒ **精确机理留调查单**。
  - **⭐⭐ 三条方法论（都是本轮实犯换来的）**：
    ① **「有门」必须落到那一行在约束什么** —— `ge=1` 是**范围校验不是语义门**，
       我的机械判据栽在这、初筛出「0 条候选」是假的（与「非 None ≠ 成功」同型）；
    ② **凡「一律／全部／共 N 处」这类批量措辞，发单前必须逐处列值对账** ——
       ⇒ **派工方错误率 12/12**（详下）；
    ③ **暴露面比 schema 窄本身就是防线**（`SurfaceSchema` 有 `multiplier` 而 `create_surface` 不暴露 ⇒ 模型碰不到），
       是「让它看不见」的最便宜形态。正面样板 = `create_zone` 的三层防护（全项目唯一）。
  - **⛔ 派工方错误率 12/12（第 12 次 = 同一轮内同一个错犯两次）**：设计稿写「同形阻断白名单**共 4 处**，一律翻转」，
    施工席翻 2 处、**拒绝翻另 2 处并标记分歧点** —— **它对我错**：另 2 处的值是 **`frozenset()` 空集
    = 2026-08-04 用户拍板的永久 advisory**（启发式双向误判、结构性修法归 R1.5），
    照原指令翻转会**推翻用户拍板**并用已知会误判的判据去拦正确建筑。
    **错因 = 只看名字形状不看那一行的值**，与本轮报告 §3 刚记下的①同一模式。
  - **⭐ 施工席的设计比派工稿更准（登记）**：把「打 `CORRECTION_DRAW_FORBIDDEN`」拆成**两个标记**
    （新增 `CORRECTION_DRAW_DERIVED`）—— 派生字段在 `model_validate` 成功后**总是**被填充
    ⇒ post-construction 的「是否非空」检查会对**每个合法 draw** 误触发；
    **唯一还能观察「模型有没有填」的点是 raw payload** ⇒ **门必须落在 parse 的原始载荷层**。
  - **⛔ 轻门抓到 1 条缺锁（已补实）**：席 A 撞**月度额度上限**中断在 neuter 自查前
    ⇒ 「代码在、测试绿」与「已验收」外观完全一致。orchestrator **换方向 neuter** 发现
    原 22 把锁的三把双向属性锁**全走 `DERIVED` 路径**、**`FORBIDDEN` 嵌套路径零回归保护**
    ⇒ 补 2 把并独立复验「改回硬编码 ⇒ 恰好这 2 条红、零连带」。
    **⇒ 「轻门的 neuter 必须 orchestrator 自己跑」这条纪律本轮再次兑现价值。**
  - **⛔ 结转**：**F-17 调查单待起**（可零成本离线做，不必再跑真链路）· 两条 NIT（E2 裸 assert 在 `-O` 下失效 · E3 `facade_segment_id` 散布 ~6 处但经核实全属非 draw-合约用途）·
    摸排**步骤 4 全量语义轴未做**（89 个写入参数逐个过，本轮只在候选上做了）· 轴 B 的 B-3 待查证 ·
    **落盘 `correction_geometry.json` 不能直接重放**（带派生 `floor` 会被新门拒）⇒ 需官方重放姿势 ·
    **F-8 防复发债第二面**（被文档引用的过程痕迹被 `.gitignore` `20*_*/` 吞掉，且 `-f` 入库后**每次改仍被静默拦下**
    ⇒ 建议移出该命名空间，别靠人肉记得加 `-f`）。
  - **⛔ 运维两条**：① 全仓 `-n auto`（16 worker）实测会在 ~98% 处**静默 OOM 中断**（无汇总行、无进程，
    外观与「还在跑」难分）⇒ **改 `-n 8`**，且**以汇总行 + 退出码为准、不看进度条**；
    ② orchestrator 又用**「输出文件非空」当哨兵判据**栽了一次（08-02 已记过该禁令）。

- **（前一节点）2026-08-07 下半场收工 = 打前半条链：F-9 治本 + F-15 两堵倒，1_correction 仍未通**
  （全档见 [plan.md「六之七」](plan.md)）。**用户本轮目标 = 拿 sm21 好 reading 产物把链路全跑通到 EnergyPlus，未达成。**
  - **落库**：F-9 治本 `99d9521`+锁 `76a639d` · F-15 两堵 `eaa6b4e`。全仓 **2262 绿**（F-15 批见轻门）。
  - **F-9 治本走【B1】**：立面区间翻成世界朝向**只需立面自身总宽**（`world = local` 或 `W−local`），
    **不需要 `along_origin`** ⇒ 推翻了此前「路线①结构上做不到」的判定。该区间标 **advisory、绝不进强制路径**
    ⇒ 交叉校验未退化成同义反复。**真链路证据仅指示性**（镜像两窗的引用顺序已反转 = 正确方向），
    **但抽签死在更早的 pydantic 校验、未走到 resolver ⇒ F-9 验收未闭合。**
  - **⛔ 留档**：F-9 那条 `lo == 0` 是**假设不是检查**，依赖「每层共用 footprint」——
    正是铁律 #6 不许烤死的那类；实测 `footprint_x=[0.12,14.88]`、**`lo` 已经是 0.12**。
    今日无害（advisory + 容差够），**退台/L 形会静默给错提示** ⇒ 建议补偏离计数，未做。
  - **F-15 = 同族缺陷第 5、6 次现形**：① schema 把内核专属字段暴露给模型（提示词一字没提）
    ⇒ 修法 = 打标记后**从给模型的 schema 里机械剥除**（⛔ 不是手维护名单）；
    ② **二阶**：门里**另外硬编码了一份禁止清单**、与标记集**已经漂了**
    ⇒ 修法 = 门改为遍历标记，**两份清单合成一份**。分阶段性保留（`e4_orientation` 阶段本就该填 `north_axis`）。
    **施工席额外抓到**：该门原抛裸 `ValueError` 拿不到重试引导 ⇒ 上一次真跑**白烧 3 次里的 2 次**。
  - **⛔ F-16 候选（未定性）**：`quarantined@1_correction`，报错已从「接口逼着失败」变为模型内容错
    （`floors.id="F1"/name="Level 1"`，窗引用 `F1` 而门要求匹配 `name`）。**形状像同族第七次，但必须查证。**
  - **⭐⭐⭐ 同族缺陷六次现形，形状固定**（F-5/F-7/F-9/F-12/F-15×2）：
    **「凡是模型看得见但不该它管的东西，最终都会被它填，然后靠事后拒绝纠正。
    有效修法只有一种 —— 让它看不见，而不是告诉它别碰。」**
    ⇒ **建议立项：把整个生产者接口盘一遍**，而不是等它一堵堵撞出来。**待用户拍板。**

- **（前一节点）2026-08-07 = 【几何内核→装配→下游→EnergyPlus】这半条链首次跑通且【数值可信】**
  （排工与全部结论见 [plan.md 顶部「2026-08-06 下半场」节](plan.md)）。全仓 **2255 绿 / 10 xfail / 0 红**。
  - **⛔⛔ 口径必须说准（08-07 用户追问后 orchestrator 核实更正，此前表述"端到端跑通"⚠️ 说过头了）**：
    这次跑通的**不是**「从图纸到 EnergyPlus 全程一次跑通」。实际形态 =
    **0_reading 用 07-07 老产物**（reading 是下轮支线）· **1_correction 完全没跑**
    （逐字节复用 `wall3_a_retest` 那份，且该产物 `schema_version=None`、窗无 `provenance`/`source_ids`
    ⇒ **legacy 形态，v3 窗源那条路〔F-5/F-7/F-9 所在〕本次根本没被走过**）·
    **2→5 + 下游 13 节点 + IDF + EnergyPlus 才是今天真跑的部分**。
    ⇒ **「后半条链在一份 legacy correction 产物上跑通且数值可信」** 才是准确表述。
    ⇒ **reading 重启会补上前半条，届时 1_correction 被真跑、F-9 那条路会立刻现形
    ⇒ F-9 治本（路线②）宜在 reading 重启前拍板。**
  - **本轮落库**：F-12（`77b3da4`）· F-9（`f316cfe`→合并 `657f3e6`）· F-8 收口（`5cccee8`/`709bc8f`）·
    **F-13 r1（`a3458cc`）**。三道 orchestrator 轻门：**F-9 PASS · F-13 否决版 REJECT · F-13 r1 无条件 PASS**。
  - **⭐ 终局实测**（新 run `run_2026-08-07_f13_e2e_verify`）：内核冻结快照 vs 最终 IDF
    **115/115 逐顶点一致** · **宽高对账 79 判对 / 0 判错**（脚本自校验 面积 115/115）·
    `EnergyPlus Completed Successfully -- 0 Severe`。
  - **⭐⭐⭐ 本轮最该记住的一条 —— 「三绿齐」不等于对**：F-13 的**否决版**做到了
    **全仓 2243 绿 0 红 + 漂移门 104→0 + EnergyPlus 0 severe**，
    而 **76/79 个垂直面的宽高被 EnergyPlus 判错**（4.4m×3.0m 的墙被当成 3.0m×4.4m）。
    成因 = 我（orchestrator）在派工单里断言校验器那段「挪起笔点」是**多余的**并让人砍掉，
    **它实为兑现 IDF 自己头部的 `GlobalGeometryRules = UpperLeftCorner` 声明**，
    而 EnergyPlus **信任该声明**去推每面的 `~Width`/`~Height`（再喂外表面对流）。
    **⇒ 唯一穿透「三绿」的动作 = 量产出的物理量本身。**
    **⇒ 新自检：删除一段「看起来多余」的规范化之前，先找出它在为哪一份对外契约服务**
    （问法：这段没了，谁会因为「以为它还在」而算错？消费方常在产物外部）。
  - **F-13 r1 修法（用户实证做满后拍板路线①）**：把校验器的规范化**逐字节提取**为纯函数，
    **内核 `build_geometry` 与校验器共用同一份** ⇒ 排序器变恒等 · 漂移门自然归零 ·
    IDF 声明为真 · EnergyPlus 宽高正确。**一个动作解决三件事。**
  - **⭐⭐ 另两条通用纪律**：① **恒等锁 ≠ 正确性锁** —— 恒等锁证明「两套规范已统一」，
    **不证明这套规范是对的**（两边用同一函数一起挑错角时它照样绿；orchestrator 换方向 neuter 才照出来）；
    ② **验一个「已被代码规范化」的东西，必须用那段代码自己的定义**
    （我用俯视直觉判「左上角」，把 18 个楼板误判 —— 楼板朝外法向朝下，是从下往上看）。
  - **⛔ 派工方错误率 11/11**（每次施工席「停下上报」都是我的题错了）。**第 11 次最危险**：
    验收条件要求重放一份**修复前 21 小时**落盘的冻结产物，而 `--intake-from` 恰好**跳过**被修复的段
    ⇒ 数学上不可能体现修复效果。**施工席顶住没照做、如实上报**（派工单里如实自陈错误率，确有防御价值）。
    ⇒ **新自检：写验收路径前先问「这条路径真的会经过我改的那段代码吗」；
    冻结产物 + 跳段入口 = 天然的假验证温床 ⇒ 派工单第一步就写防假验证自检。**
  - **⛔ 结转**：**交叉审待发**（请求书已备，GLM-5.2 验证性审阅，三摊合审）·
    **F-14 候选**（`tests/test_zone_agent.py` 无 mock、真调付费 API ⇒ 全仓绿依赖 API 可用性且每跑一次都烧钱）·
    F-9 治本路线②待签字 · 架构债 D-2 待与协作者谈权属 · 接地面无地温 ·
    World 坐标系忽略非零 North Axis · 环检测计数缺口。

- **（前一节点）2026-08-06 收工 = 0→5 全线打通 + 下游首次全跑完 + 缺陷推进到 F-12**
  （排工与全部结论见 [plan.md 顶部](plan.md)）。全仓 **2234 绿 / 10 xfail / 0 红**（08-05 收工 2220 → +14 锁零回归）。
  - **本轮落库 9 个提交**：F-10（`b379cd8`）· 墙 3（`e58edb1`+`9b6a7ff`）· F-11（`4b87e9f`→`966d667`→`a658989`）·
    F-12 登记与调查（`756e821`/`75fc9ba`）。**三道 orchestrator 轻门全 PASS**（各含独立全量 + 独立 neuter）。
  - **⭐⭐ 战线整体前移**：0_reading ✅ · 1_correction 🔴F-9 · 2_modelling/3_split_pairing ✅ ·
    **4_mep ✅（F-10 + 墙 3 两堵都倒）** · **5_intakeoutput ✅ 首次通过**（`deterministic_pass`，契约 11 字段齐）·
    **下游 13 个节点全部跑到**（surface/fenestration/hvac/people/lights 五个此前**结构上永不可达**）·
    卡在 **F-12**（几何一致性）。
  - **⭐⭐⭐ F-12 = 本侧 prompt 制度性地把墙的几何建模交给了 LLM** ——
    `src/agent/nodes/surface.py:29-31` 逐字命令 LLM 用 `zone_specs` 重算墙顶点、丢弃 `surface_specs` 已写死的值
    ⇒ **违反不变量 #1「建模」边**。机械证明：**exterior 墙 24/24 全漂 + interior 20 对配对 20/20 各漂一个**（44=24+20）；
    **Floor/Ceiling 与窗零漂移**（窗的 prompt 是 `verbatim` 照抄）⇒ **只有墙被要求"重新推导"，所以只有墙错**。
    ⛔ **修法待拍板且权属有张力**（`surface.py` 在本地 `src/`，但 prompt 归 §3 协作者维护权）。
  - **⭐⭐ 三条方法论产出**：① **neuter 必须同时覆盖「机制」与「接线」** ——
    轻门实测：删调用点参数 = 复原缺陷本尊，而施工席四向 neuter 全绿（**假锁**）⇒ 判别问法
    **「把调用点改回缺陷形态，锁红不红？」**；② **夹具不仅要用对字段名，还要覆盖真实产出的形态分布**
    （墙 3：夹具全是人手写的 IDD-correct 顺序，真实 LLM 从不产出这种形态）；
    ③ **对称载荷证明不了方向**（F-9 定性作废的根由）。
  - **⛔ 派工方错误率更新：8 次「停下/如实上报」，8 次全是 orchestrator 的题错了**
    （新增第 7 次 = 要求的行为差异在策略层根本不存在；第 8 次 = 验收条件互相冲突）。
    **新自检两条**：写行为锁前先读策略代码「这个差异我指得出是哪一行产生的吗」· 验收条件之间须互不冲突。
  - **⛔ 结转**：F-12 修法待拍板（含权属裁定）· F-12 的 Q1 未闭合（需最小烧钱探针）·
    **F-9 定性作废、调查单已备好未发** · F-8 未排期 · `MAX_RETRIES=0` 为何关成 0 未查 ·
    GLM 席位 08-06 撞两次 5h 额度窗。

- **（前一节点）2026-08-05 收工 = 端到端工程缺陷批推进到 F-10 + 两条探针把「未知空间」清了大半**
  （排工与全部结论见 [plan.md 顶部 2026-08-05「二之二」条](plan.md)）。全仓 **2220 绿 / 10 xfail / 0 红**。
  - **本轮落库**：F-2c 收口（`a8c367a`）· F-7 接口修法（`a174fe8`→`86ab24b`）· sol 对抗审 REWORK 后的返工批
    四条 MAJOR（`cac457a`/`49e5f42`/`5797653`）。三道 orchestrator 轻门全 PASS（独立全量 + 独立 neuter）。
  - **⭐⭐ 逐段体检全景（本轮最有价值的产出）**：**0_reading / 1_correction / 2_modelling / 3_split_pairing
    在 v1 路径 gate① 全绿（几何内核本身没坏）· 4_mep 🔴 硬崩 · 5_intakeoutput 仍零证据 ·
    下游 9 subagent→IDF→EnergyPlus ✅ 实测 `0 Severe`**。⇒ **全部缺陷集中在 0→4 段，下游半边健康。**
  - **⭐⭐ F-10 = `check_mep()` 签名漂移**（调用方 07-06 加 `run_profile`、被调方 07-01 签名没有）
    ⇒ **任何走 flow 跑到 4_mep 的 run 必崩，已断整整一个月无人发现** —— 因为这一个月没有东西走到过 4_mep。
    **⇒ 方法论：F-9 一直遮着 F-10；「串行修墙」会让后段缺陷无限期潜伏，「绕开卡点先撞后段」是必要的并行手段**
    （用户 08-05 定的打法：「拿之前端到端跑通的中间产物直接试，反正是探工程问题」，当场兑现）。
  - **F-9（当前 1_correction 卡点）= 又一个接口错位**：图纸平面与四立面**共用一套轴网**，
    而代码 `_BASE_SIGN` 写死「从外部看的镜像约定」（北/西 `sign=-1`），南立面恰好蒙对。
    **⇒ 需与用户 08-02 定的「每张图都从一个方向读」口径重新对齐，修法待拍板。**
    另发现代码里**本就有优雅回滚路径**，同一个 07-18 提交里两个调用点一个接了一个没接。
  - **⭐⭐ 两条方法论已生效**：① **分辨力实测只证明「机制能分辨」，不证明「每个抛出点分得对」**
    ⇒ 自归类设计必须**逐点审计**（实证：54 处只有 2 处归错，稀疏到抽样与机制级 neuter 都照不出来）；
    ② **neuter 必须先确认「改动真的落下去了」**（orchestrator 实犯：正则命中 0 处的空操作拿到「22 绿」）。
  - **⛔ 结转**：F-9 修法待拍板 · F-10 未修 · `run_mep` schedule 引用未定性 · F-8 未排期 ·
    **5_intakeoutput 至今零证据** · sol 的 BLOCKER（真实 sm21 correction accepted attempt）**继续持有**。

- **（前一节点）2026-08-05 早间 = 端到端工程缺陷批：真链路暴露 6 条、已落库 5 条；reading 转下轮支线**
  （用户 08-05 定：「**sm21 先停了，下轮再修，这轮把端到端工程问题解决就可以**」；
  排工与全部结论见 [plan.md 顶部 2026-08-05 条](plan.md)）。
  - **打法**：拿 **07-07 那份已知满分的 sm21 识图产物**做下游机械烟测，把识图变量摘掉，只问「除识图外这条链今天还通不通」。
    **通不了。** 逐条撞出 **F-1**（判卷不认读图信封 + 空 scores 判 pass ⇒「一张卷子没批却报全对」）·
    **F-2**（隔离 merge 丢 `reading_summary.md` ⇒ 隔离产物永远进不了 correction）·
    **F-3**（advisory 检查触发早退 ⇒ 未 finalize 的草稿被 accept、两段后才炸）·
    **MAJOR-1**（`SCORER_SCHEMA` 没 bump ⇒ 旧 sidecar 短路、F-1 的修复在触发它的产物上原样复现，Claude 侧对抗审抓出）·
    **F-4**（correction 内层重试是**盲的** ⇒ 模型三次犯同一个 schema 错、整条链被打死）·
    **F-5**（窗源消费侧读错字段名：契约 `x_range_m`、代码 `x_range` ⇒ **任何带窗的合规产物都过不了 1_correction**；
    立面 `z_range` 契约里根本不存在 ⇒ **窗台/窗顶证据从来没进过链**）。
    落库：`4a11097` / `fb78e74` / `0256060` / `373b3fe`；**F-6（provenance 枚举）· F-7（残留产物/locator）· F-2c · r4 结转下轮**。
  - **⭐⭐ F-5 = 本项目招牌缺陷的最纯形态**：四个测试文件的**夹具全部照抄了实现的错拼写**
    ⇒ 实现与夹具自洽、测试永远绿，而任何真实产物必崩 ⇒ **B5 窗源这条路从来没在合规产物上跑通过**。
    **新治理教训（与「探针 ≠ 锁」「非 None ≠ 成功」并列）：消费某契约的测试，其夹具必须钉到契约的单一来源（机械导出），
    ⛔ 不许手抄字段名。**
  - **⭐ reading 三条硬结论（本轮停、下轮单开支线；逐字介入实录见
    [INTERVENTION_LOG](logs/experiments/2026-08-05_sm21_e1_restored/INTERVENTION_LOG.md)）**：
    ① **「停下等审」是会话形态的属性、不是提示词的属性**（07-07 kickoff 原文放回 headless ⇒ 不停；换会话内子 Agent ⇒ 立刻停）；
    ② **⭐⭐ review 环的效果不迁移** —— 同会话内被审 7 轮的 1f = **墙 4/4 · 多画 0**，零介入的 2f = **0/5**，
       四立面全缺 `facade.view_facade` 整段作废 ⇒ **介入 = 逐图纠错，不是教会方法**；
    ③ **纠偏有两类固有过冲**：只说「不是什么」⇒ 把对的一起删；**硬纪律诱发伪造**（我要求「链必须闭合」⇒ 它编了一段 240 mm 凑够）
       ⇒ **立规则必须同时给合法退出口**（补上后它就诚实标注「不闭合、1.48 m 无法解释」）
       ⇒ **直接影响 gate① `dimension_chain_closure` 严格档的设计**。
  - **⚠️ orchestrator 自己的两处错（如实登记）**：① 08-04 那一抽**不是 E1**（排期写「E1 + 主控介入保留」，我改成了产品默认无介入路径）
    ⇒ 那一抽不能当「E1 复现失败」的证据；② **严格档是我自己套的**（E 臂跑测单原本写给 sm24）——
    实测 **07-02 与 07-07 两份满分产物在今天严格档下都会被拒收**（8 / 6 条 `dimension_chain_closure`）
    ⇒ 严格档比历史 anchor 达到过的水平更高，「做到之前的效果」与「过严格档」是两件事。
  - **判卷口径澄清**：sm21 的 GT 是 **schema v2** ⇒ 走 **legacy** 判卷分支（R1 批 A–D 修的是 typed 那条）；
    **07-07 老产物在今天判卷下仍是满分**（平面 9/9 · 7/7、立面 **15/15 全 `complete`**、extras 0）⇒ 尺子对老产物没坏。
  - **sm25 素材已入仓**（[全档](logs/experiments/2026-08-04_sm25_material_prep/README.md)）：6 图入 `case_data/`、
    命名规范化、机械验收过；testdata 骨架已建留 4 个 `TODO_`。**GT 卡在「转换器只处理一个平面」**（= sm24 收官登记的 `HC-04`），
    需「多层化」批次；**GT 不是跑 sm25 的前提**（无 GT 也能跑、只是判分降级）。
  - **运维**：**三个席位全撞过 5h 额度窗**（Claude ×2 / GLM ×1）；
    **⭐ GLM 三次「停下上报」三次都是派工方（orchestrator）的题错了** —— 与 08-04 同型、第二次坐实。

- **⭐⭐⭐ 最新（2026-08-04 凌晨收工）= R1 批 B 收口**：一夜 r2 → r2b → 交叉审 → r2c，全仓 **2096 绿 + 10 xfail 零红**
  （2089 → 2096，净增 7 锁零回归）。**审全走 Claude 侧子代理**（用户定：GPT 侧额度不足，本批不再启）、
  **施工全走 GLM**（同席位三轮，05:59 撞 5h 额度上限 ⇒ 三条 MINOR 结转）。交叉审 = **APPROVE-WITH-CHANGES**
  （0 BLOCKER / 1 MAJOR / 4 MINOR / 1 NIT），**唯一 MAJOR 已修并经 orchestrator 独立 neuter 证明真绑**。
  **⭐ 两条最重要结论**：① **「停下上报」产生了本批最高价值的两次修正——两次都是派工方的题错了**
  （要求给一块恒空操作的代码补锁 = 硬补必得假锁；给的防篡改方案挡不住篡改）；
  ② **新判据（⭐2026-08-04 用户拍板定案，详 [decision_log §5.14](decision_log.md)）：一个值配不配被冻结并防漂移，
  看两道题 —— ① 除冻结记录外是否存在第二处记载说明它本该是什么；② 那处记载是否先于本次运行就已固定
  （进 git / 有人签字 / 绑真实文件指纹）且被评判方写不了。两题皆是才可冻结；任一为否 ⇒ 不冻结、不据以判定，
  至多留显式标注非权威的审计快照。在册的第二处记载只有两个（`run_config.yaml` 档位声明 · case 身份含签字与图像指纹），
  ⛔ 新增须用户拍板。** ⇒ 命令行旋钮（`--with-ep` / draw budget / judge 开关）第一题即不通过、永不进判定面。
  **⛔ 同族缺陷本夜第三/四次现形**：两处「声称在守其实没守」的假 docstring / 假注释已消除；
  一条「自称摘掉即红、实测全仓零红」的假锁已修。详见
  [轻门 + 结转债](logs/reviews/verdict/2026-08-04_reading_ruler_r1_batchB_r2_orchestrator_lightgate.md) ·
  [交叉审](logs/reviews/verdict/2026-08-04_reading_ruler_r1_batchB_r2_crossreview_claude.md) ·
  [plan.md 顶部 08-04 条](plan.md)。**批 C 未开工。**
- **⭐⭐⭐ 最新（2026-08-04 收工）= 批 C（安全交付面）+ 批 D（判卷图）+ R4-a（成绩分账）全部落地**，
  全仓 **2158 绿 + 10 xfail 零红**（**本日 2089 → 2158，+69 条锁、零回归**）。
  施工三席接力（GLM 三轮撞额度 → Claude 侧接手 ×3），审 = Claude 侧 ×2 + **sol ×2**。
  **⭐ 三条最重要的结论**：
  ① **判卷图与渲染修好了** —— 07-08 起「每轮识图零渲染、用户看不到产物图」已闭合（O-1），
     判卷图恢复六 panel + 图例（批 D）；**用户重新有了独立看懂产物好坏的通道**；
  ② **⭐ 方法论（本日最贵）：neuter 变红只证明「实现被调用」，不证明「判据有分辨力」** ——
     同一族缺陷两个方向各栽一次（2×2 px 退化 fixture 假绿 / 两堵墙探针假红）
     ⇒ **判据类检查必须四格实测（坏×小·好×小·好×大·坏×大），载荷须真实量级 + 真实形状**；
  ③ **⭐ 用户拍板：判据两个方向都不稳时不再打补丁，去看接口** ——
     「像素当米」检测降为 **advisory（只提醒不拦）**，**结构性修法归 R1.5**
     （读图器只写像素锚点 + 引用标注、米制由代码唯一换算 ⇒ 该错在接口上表达不出来）。
  详见 [批 C r3/r4 轻门 + 结转债](logs/reviews/verdict/2026-08-04_batchC_r3_orchestrator_lightgate.md) ·
  [sol 两轮复核](logs/reviews/verdict/2026-08-04_batchC_r3_review_sol.md) · [plan.md 顶部 08-04 条](plan.md)。
  **⛔ 结转债**：D-5（判据结构性修法归 R1.5）· D-6（源图不可解码仍 coverage PASS）· **X-4 至今未裁定**。
- **分支** `6.15_ValidationArchM0toM4`（已推 origin）；测试 **2158 绿 + 10 strict xfail·零红**（下条 2089 为 08-03 收工数）
  （08-03 收工数：批 A 2055 → 批 B r0 2068 → r1 2089，净增 34 条锁零回归；
  08-01 W4 那 1 红已随返工 r1/r2/r3 闭环，见下条；xfail 十条含 2 个 legacy golden sm20/run_2026-06-15、
  sm21/run_2026-06-16_opus 无编排账本→run_state=incomplete；**B5 Phase C 延后的 6 个
  `test_output_coordinate_identity.py` E4 build-proof xfail 已在 Phase D 复原为真绿**，该文件零 xfail）。
- **⭐⭐⭐ 最新（2026-08-03 收工）= R1 批 A + 批 B（r0+r1）全部落库、轻门通过 · 批 C 未开工 · 交叉审两路待下轮 · ⭐ 07-07 启动 prompt 被复原 ⇒ 「杠杆是模式不是纠偏」定案 ⇒ 新立 R1.5「接口层强制测量」**
  （详细排工与结论见 [plan.md 顶部 2026-08-03 条](plan.md)；审轨：
  [批 B/C 派工单](logs/reviews/request/2026-08-03_reading_ruler_r1_batchBC_dispatch.md) ·
  [GLM 边界上报](logs/reviews/execution/2026-08-03_reading_ruler_r1_batchBC_glm_boundary_report.md) ·
  [orchestrator 裁定](logs/reviews/request/2026-08-03_reading_ruler_r1_batchBC_ruling.md) ·
  [批 B 轻门](logs/reviews/verdict/2026-08-03_reading_ruler_r1_batchB_orchestrator_lightgate.md) ·
  [sol 部分稿](logs/reviews/verdict/2026-08-03_reading_ruler_r1_batchB_review_sol.md) ·
  [r1 返工派工单](logs/reviews/request/2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md) ·
  [J-1/J-2 裁定](logs/reviews/request/2026-08-03_reading_ruler_r1_batchB_j1j2_ruling.md) ·
  [r1 轻门终版](logs/reviews/verdict/2026-08-03_reading_ruler_r1_orchestrator_lightgate_final.md)）：
  - **⭐⭐ 批 B 走完 r0 → 两轮独立审 → r1 → 轻门**：r0 落库后
    **orchestrator 轻门 + sol 交叉对抗审两路独立收敛到同一句话 ——
    「修好的是『机制存在』，没修好的是『机制在所有真实路径上都生效』」** ⇒ REWORK（6 MAJOR + 1 MINOR）。
    r1 七条全修完（施工 GLM ×6 + **terra ×1**〔R1-5，GLM 额度耗尽后跨家族接手〕），
    轻门通过：**独立全量 2089 绿零红 · 独立 neuter 恰好红 2 条 R1-5 锁零连带、POST-RESTORE 全绿 ⇒ 锁真绑**。
  - **⛔⛔ 本项目第五次撞见「规范写了、没有机器验证」——这次是「考生自己填的字符串决定这道题考不考」**：
    gate① 本就有 `_dimension_derived_refs`（`src/validator/checks/reading.py:793`）在管
    「声称按尺寸推导的墙必须真的引用得到标注」，但其首行
    `if provenance != "dimension_derived": continue` ⇒ **读图器写 `seen` 即整条检查跳过、落 N/A**。
    今天 Sonnet 那 10 条墙全 `seen` ⇒ 该检查零压力零阻断。
    **与批 B 修的 L-22「产品内容不得决定考卷」同形** ⇒ **R1.5 的必要性从「设计判断」升为已坐实的接口缺陷**。
  - **⭐ R1-5 加固超出要求**：`GeometryApproval` 现钉 `run_profile`/`capability_profile`/`source`/
    `legacy_defaulted` ⇒ **一次人工签字从此绑定「它是在哪个档位下签的」**，事后可审。
  - **⛔ 下轮起点 = 交叉对抗审两路（施工跨家族、「谁写谁不批」）**：
    **R1-5（terra 产出）⇒ 派 GLM 审**（契合其「验证性审阅达最高档 / 探索性不及格」画像，此处清单现成）；
    **GLM 那六条 ⇒ 派 sol 重审 + 补完被平台内容策略中断的 P-3…P-9**。**之后才是批 C。**
  - **⭐ 07-07 的事前 prompt 没丢，在 git 里**（用户提供线索）：启动命令 = 老 `new_case_guide.md` 附录 A 三行
    + 当时**已版本化**的 `session_kickoff.md`（`git show 891356d:skills/intake_pipeline/0_reading/session_kickoff.md`）
    ⇒ **sol 架构审 P-2 BLOCKER 的前提被推翻**（仅剩「那次 review 的原文措辞」未落盘，维持待验假设）。
    **且该 kickoff 逐字写着 "Do one pilot image first / Stop and wait for review"
    ⇒ 07-07 的「打回」是产品 skill 里写死的 review 环，不是临场干预。**
  - **⭐⭐ 打回的作用是切换工作模式、不是修具体的错**（07-07 = 13/14 `dimension_derived` + crop_zoom 11 次；
    今天 Sonnet 无监督 = 全 `seen` + crop_zoom 0 次；**返工两轮造不出这个差别**）
    ⇒ **用户判断「杠杆不在那一两次纠偏上」成立**；**⛔ 回纠应退化成异常路径，不做主机制**。
  - **⭐⭐ 新立 R1.5 = 坐标来源改造（接口层强制测量）**：**读图器不写公制坐标**，只写源图像素锚点
    + 引用的尺寸标注 + 标定变换，**公制坐标由确定性代码唯一换算** ⇒ 目测与左右反向**在接口上表达不出来**，
    且**不需要任何 controller**。排 R1 之后、R3/R4 冻结接口之前；**⛔ 不得先跑新基线再补方向证据**。
  - **⭐ 用户定「reading 怎么解决靠实验说话」** ⇒ `reading-agent` 存废由 R1.5 之后的实测两抽决定，
    **不由设计辩论决定**；架构细稿的 REWORK 返工不必先做。
  - **⛔ 债 D-1**：sm24 五图 `dimensioned=true` 写入会打穿已签字 GT 信任链（`dimensioned` 进 manifest
    `content_sha256`，而 GT 侧车冻结 `base_view_manifest_sha256`、评分入口四元组逐字相等）
    ⇒ **本批只交付机制 + fixture 锁；真值写入 + GT 侧车重签归 R2，需用户单独授权 + 真人签字**。
- **（前一节点）2026-08-02 深夜 = reading 攻坚开工：R1 修尺子施工中 + 架构细稿被对抗审判 REWORK + 用户三处口径更正**
  （审轨：[R1 问题书](logs/reviews/request/2026-08-02_reading_ruler_r1_discussion_brief_sol.md) ·
  [R1 sol 方案](logs/reviews/verdict/2026-08-02_reading_ruler_r1_discussion_sol.md) ·
  [R1 派工单+裁定](logs/reviews/request/2026-08-02_reading_ruler_r1_construction_dispatch.md) ·
  [Slice 0 调查](logs/reviews/execution/2026-08-02_reading_ruler_r1_slice0_rtl_survey.md) ·
  [架构问题书](logs/reviews/request/2026-08-02_reading_architecture_design_brief.md) ·
  [Fable 细稿](logs/reviews/verdict/2026-08-02_reading_architecture_design_fable.md) ·
  [sol 对抗审](logs/reviews/verdict/2026-08-02_reading_architecture_design_review_sol.md)）：
  - **⭐ 用户三处口径更正（已写入术语 banner 与 §1.5 #7）**：① **术语统一**为 orchestrator /
    `reading-agent`（子环节内部调度）/ `reading-worker-agent`（实际读图产出的 VLM）；
    ② **autonomous 是北极星、不是本批目标**，**本批 = `reading-agent` 在场下 sm21+sm24 都接近满分**
    = 把 07-07 那次 orchestrator 临场介入**固化 + 隔离 + 降档**，**不是提高分数、是用合规形态重新达到一次**；
    ③ **tool-invention 不是成绩 lane 而是 dev 期开发者职能**（跑测不算正式成绩 · case 收官须脱离它完成）。
  - **⭐ 立面读图方向：用户拍板「直接规定每张图都从一个方向读，不用它自己选方向再声明」**
    ⇒ 契约钉死 left-to-right、`local_x_positive` 降为「历史可加载、判卷永不读取」的废弃字段。
    **terra Slice 0 全语料调查坐实**：RTL 声明共 4 处、**数值真反射 0 处**（全是 metadata 填错）；
    另 92 处无声明产物在现行代码里本来就默认 L-to-R ⇒ **零动作、零风险**。
    **⇒ 净减少一个 schema 选项、一套迁移机制、一整类错误来源。**
  - **⛔⛔ 但「契约钉死 ≠ 约束住」——本项目第四次撞见「规范写了、没有机器验证」**
    （前三次 = 自评字段 / CV 证据 / access_log 零消费者）。gate① 对立面 x 方向**零校验**
    （`reading.facade_fields` 只查字段存在性）。**orchestrator 自拟的「对齐产物自己转录的尺寸链」判据
    被真实数据当场证伪**（07-27 North：产物宽度量错 ⇒ 原样命中 2/4、**镜像 3/4** ⇒ 该判据会判错）
    ⇒ 本批**不实现**，转 sol 作追加命题 N-6。
  - **⛔ sol 对抗审架构细稿 = REWORK（4 BLOCKER / 8 MAJOR / 1 MINOR）**，
    **两条最硬的 orchestrator 已独立核实属实**：
    ① **反例就在仓库里**——`test_self_consistent_wrong_dimension_passes_linter` 的 docstring 自陈
    「一条闭合的尺寸链**哪怕每个数字都与真实图纸不符**也不许阻断」（`3+3+3+6=15` 即 pass）
    ⇒ **「尺寸链闭合」证明不了「量对了」**，而它是细稿四支柱之一 ⇒ P-3 不成立；
    ② **`spawn_isolated_reader.py` 的 `--directive` 与 `feedback` 子命令仍在**、且被测试固化为期望行为，
    加上 orchestrator 与 worker **同 UID 同可写 staging** ⇒ 「验收脱离 dev 角色」**无结构性保证**（P-8 BLOCKER）。
    另 **P-2 判定「07-07 干预映射属倒推、须降级为待验假设」**（细稿自身前后矛盾：一面承认候选召回 5 vs 真实 16，
    一面称该映射是「代码可判定的事实」）；**P-5 BLOCKER**（解除命令形态限制却无 OS 级隔离信任根
    ⇒ `python -c` 内 `open()` 可直读 GT；且 `ANTHROPIC_API_KEY` 保留 ⇒ 外传通道）；
    **F-3 最尖锐**：`reading-agent` 按现规格「只原样摘录 gate 已有 ID、不添加新判断」
    ⇒ **几行确定性代码即可实现 = LLM 形状的拷贝器**，与「能代码化的就代码化」自相矛盾。
  - **⭐ N-6 得到比 orchestrator 两个候选都好的答案**：**四条信号抓不住反向**
    （把所有 x 写成 `W−x` 可四项全绿）；且**「分数低」不是答案**——**近似对称的立面反向后分数可能不低**，
    GT 几何根本区分不了。**修法 = 读图器不写公制坐标**，只写源图像素锚点 + 标定变换，
    **由确定性代码按「源图左缘=0、向右为正」唯一换算** ⇒ **反向根本表达不出来**
    （明确否掉「只把字段改名叫距左缘」——模型照样能把距右缘的数填进去）。
    **排期建议 = 插 R1.5，在 R1 之后、R3/R4 冻结接口之前**（晚做要返工两次；
    **且不得先跑新基线再补方向证据**，否则「方向错」与「画错」混成同一个低分）。
  - **⇒ 架构线下一步（用户 08-02 拍板）= 另开会话与 orchestrator 详谈**（P-8 触到用户自定规则 /
    N-6-d 要插新阶段 / F-3 质疑 `reading-agent` 存废，三条均须用户当面敲定，不由 orchestrator 代裁）。
  - **⚠️ 运维根因（用户查明）= 容器内存只给了 16 G ⇒ 会话被 OOM 杀掉**，此前归因的「会话切换带走后台任务」
    只是表现。用户将扩到 24 G。**当日两次丢失、同样的活白做两遍**，三条修法已落：
    ① 席位启动一律 `setsid` 脱离进程组；② 派工单明写「做完一件存一件 / 先落骨架再补」（实测有效）；
    ③ **哨兵判据不得用「文件非空」**（骨架会被误判为完成，orchestrator 当日即栽），
    须用**进程退出 + 占位符计数归零**。另：**骨架里的「暂定 REWORK」不得当结论汇报**
    （sol 自己写明「以本文最终版为准」）。**风险点**：16 核 `-n auto` 全仓并行 ≈ 16 worker × 350–700 MB
    ⇒ 叠加两个 codex 席位后逼近上限 ⇒ orchestrator 轻门改**限制 worker 数**
    （不削弱门：提速批已机械证明并行与串行**节点集合逐字节相等**；与禁用的 `-m` 过滤性质不同）。
- **（同日晚些）2026-08-02 = 同一把尺子回放坐实「历史正确路径真的存在」+ 判卷层与 gate 档位两条 P0 断线 + 治理口径被用户重订**
  （**零代码改动**·[主控回放全档](logs/experiments/2026-08-02_one_ruler_replay/README.md)·
  [GPT 侧调研报告](logs/reviews/verdict/2026-08-02_reading_regression_controller_cv_investigation.md)）：
  - **⭐⭐ 一把尺子的纵向回放（此前一直被判「量纲不可比」，本轮做成了）**：把 **07-07 sm24 老产物**
    （Haiku 4.5 + CV 工具箱）直接喂进**今天的 v3 生产判卷层**（同 GT / 同 bindings / 同容差 / 同全卷五张；
    先用新件复现出已落盘的 53.31/57.86 验证调用姿势）⇒ **老件内墙 57.86/57.86 = 100 %（20 行全 `complete` 精确命中）·
    外轮廓 60/60 · 多画 0 m**；今天 Sonnet 全卷 = 92.1 % · 60/60 · 多画 6.77 m。
    **⇒ 用户「正确做法一定存在」从强推断升级为已证实。** 今天丢的分不在那 12 段 0.06 m 上（容差内照算），
    **是漏掉右下小房间三面墙（4.55 m）+ 多画 6.77 m**。
    **做法差别写在 provenance 里：老件 14 条平面墙 13 条 `dimension_derived`（单条最多引 12 个尺寸标注）/ 38 份 CV 证据；
    今天 10 条墙 10 条全 `seen`、引用 ≤2。**
    ⚠️ **回放前提**：老件缺 07-31 才立的 `scale_origin` 契约 ⇒ 原样进尺子必然**全 0**（gate① 在 golden/regression 有硬拒、
    属已知设计），补值取自产物自己的 `calibration_note`、几何未动 —— **这正是此前没人能重量老件的原因**。
    ⚠️ **仍不能断言「无监督全对」**：该 run 的 `llm.yaml` 逐字写着 prompt 级隔离 + **2 轮 rework**（纪律 1 + schema 1）。
  - **⛔ P0 断线一 = 判卷层把诚实的 `mirrored:"unknown"` 判成「帧向冲突」，整张立面观测在读 strokes 前就被丢弃**
    （`reading_typed_adapter.py:273 _facade_sense` 把 `"unknown"`→`None`，`:873` 与 binding 的 `false` 不相等 ⇒
    `_na_components(..., retain_as_miss)`）。**判决性对照：只把这一个词改成 `false`、几何一字节不动 ⇒
    老件与新件双双 existence/along/width/sill/head 各 11/11 全 `complete`、`window_elevation_geometry` 0/44 → 44/44、墙面不变。**
    而 `guide.md:351` 明列 `unknown` 为合法值、`:355` 明令读图器不得做世界落位声明，
    判卷 CLI 边界注释更写着 *"product-provided mirror declarations are not read"* —— **不但读了，还照它判零**。
    **⇒ 收回三条结论**：08-02 早间报告的「窗是墙之外唯一真缺口 / 平面与四立面互相矛盾」、
    「平面窗连续三轮全崩」——**是尺子砸的**，两份质量差很多的产物 `claim_summaries` 哈希**完全相同**（分辨力 = 0）。
  - **⛔ P0 断线二 = 声明的严格档从未真正执行 ⇒「gate① 分辨力 = 0」这个说法本身要改口径**
    （GPT 报告 §3.6.1 指出、主控独立核实且后果更重）：`run_config.yaml` 声明 `orthogonal_polygon` + CLI `regression`(fail-closed)，
    实际落盘 `checks.json` 头部 = **`rectangular` + `exploratory`**；而该 run 的 gate① **本来就抓到 5 条 fail**
    （`dimension_chain_closure` ×4 + `stroke_dimension_consistency` ×1）。按档位重算 `blocking()`：
    **exploratory ⇒ 0 · regression ⇒ 4** ⇒ **严格档若真生效，这份产物会被当场拒收**。
    **且它抓的正是本轮 provenance 分析指向的同一个病灶（尺寸链不闭合 / 看着画）。**
    同时证实 `_run/view_manifest.json` 五张视图**全 `dimensioned:false`**（图纸带完整尺寸链、产物自己抄了 48–51 条）
    ⇒ 尺寸类检查在 31 条 N/A 里占大头。
  - **⭐ 用户重订治理口径（已写入 §1.5 #7，旧版冲突处作废）**：**reading 内部允许有自己的 controller**
    （ReadingService 内部 / Flash 档或以下 / 一次计划 + 一次局部返工 / 不写最终坐标）；
    **端到端主控只能启动与接收**；**成绩按 autonomous / controlled / tool-invention 三条 lane 分账**；
    **隔离原则改为「严格限制可见信息与写出边界，不限制在合法输入上采用何种计算方法」**
    —— 按命令形态封杀通用 CV 编程，封掉的正是 07-02 Sonnet 那条成功路径。
    **降档的真实动因**：reading 后续要转本地开源 VLM 部署，Haiku 是那个档位的代理基准，不是省钱实验。
  - **⇒ 排工表见 [plan.md 顶部 2026-08-02 晚条](plan.md)**（R0 口径统一 → R1 修尺子 → R2 重建基线 →
    R3 把正确路径提成工序 → R4 ReadingService 边界化 → R5 CV Lab → R6/R7 四臂与 CV A/B）。
- **（同日早些）2026-08-02 = 「减卷有害」被实证 + Sonnet 无监督全卷墙侧基本达标 + 六条机制缺陷 ⇒ 用户「是我们把机制改坏了」的判断成立**（**零代码改动**·[全档](logs/experiments/2026-08-02_scope_harms_reading/README.md)）：
  - **⭐ 用户校准的方法论原则（本轮最重要，凌驾于此前所有 reading 规划之上）**：
    **「先保证质量，从高模型往低模型上降，而不是先降模型、拿到很低的分数再想办法提分数。」**
    既然已有 Sonnet 几乎全对、Haiku 加轻量介入也基本全对，**不应容忍分数掉到 40–70 % 再想办法提升**。
    **「之前的成绩是假象」的准确含义 = 「Haiku 纯自己做到全对」是假象，不是「那个 100 % 是作弊」**
    —— 100 % 是真的，只是不是低档模型的单一功劳。**该做的是把已经存在的正确路径让 Haiku 也掌握，
    而不是为 Haiku 或为这两个 case 定制方案再迭代。** ⇒ 08-01 主控那份「预估 40–70 %」的规划**目标定错、作废**。
  - **⭐⭐ 主结论：减卷（考试范围五张→两张）不只是判卷失真，它真的把识图质量压下去了。**
    同模型 / 同文档 / 同零监督 / 同一把尺（内墙分母 57.86 m、外轮廓 60 m、容差 0.30 逐字相同）：
    **Sonnet 全卷 = 内墙 53.31/57.86 = 92.1 % · 外轮廓 60/60 = 100 % · 多画 6.77 m**；
    **Sonnet 减卷 = 70.9 % · 48.8 % · 46.01 m**；Haiku 减卷两抽 = 9.0 % / 24.8 %、多画 59–79 m。
    **机制解释 = 五张图本互为佐证**（平面判不准处由立面校核），减卷砍掉了这层冗余。
    ⇒ **墙这一侧 Sonnet 无监督基本达标**：17 段内墙命中 14（2 完全 + 12 容差内）、漏 3；外轮廓全中。
  - **⚠️ 减卷那轮的失分是「基准」不是「没测量」**：它每条轴线都在 0.30 m 容差内（最大 0.25 m），
    但线段级判不过；产物写明局部原点取外墙**中心线**、按 240 墙厚推内角 +0.12、并用 200 m² 面积交叉验过
    ⇒ **经过论证的基准选择，只是与 GT 不一致** ⇒ 撞上 07-08 就登记、至今未收口的「尺寸基准=轴线还是墙面」。
    **⇒ 现尺子在惩罚「真的去量」、奖励「抄整数」**（Haiku 外轮廓 100 % 正因它直接抄了尺寸链上的 0/10/20）。
  - **窗仍是墙之外唯一真缺口，但失败形状变了**：全卷下 existence/along/width **11/11 全 `conflict`**
    （平面与四个立面对同一窗说法不一致、判卷两边都不敢算），非漏画；减卷那轮反而 7/11 命中（只有一张立面、没机会打架）。
    **可用现成全卷产物离线定位、无需重跑。**
  - **⛔ 六条机制缺陷（全部近期新增，逐条坐实）**：**M-1 渲染整个不跑**（`_render_stage` 按 `0_reading/*_view.json` 找，
    硬隔离 merge 把产物放进 `attempts/NNN/output.json` ⇒ **07-08 起每轮识图零渲染、用户看不到任何产物图**）·
    **M-2 判卷图退化**（v3 typed grade = 标签互压的柱状图；老的是两层平面+四立面几何叠图带图例）·
    **M-3 合并门命名契约自相矛盾**（kickoff 通则 `<name>_view.json` vs 同文件表格 `1f_view.json`，merge 认表格
    ⇒ 图名以 `_view` 结尾的 case 必踩、读图器照通则做即被拒收）·**M-4 gate① 放行离谱坐标**
    （`ocr_texts[].anchor` 写成像素 `[360,450]`、楼只有 10×20 m，0 阻断 ⇒ 渲染出 **3.3 亿像素** PNG、打不开）·
    **M-5 减卷有害**·**M-6 gate① 与 CV 证据零接线**（`src/validator/` 对 `cv_evidence`/`prescan`/`candidate_id` 零引用）。
    **另：gate① 分辨力 = 0 第五次坐实**（92.1 % 与 9.0 % 同为 0 block）。
  - **Fable 点射两版设计稿**（[问题书](logs/reviews/request/2026-08-01_reading_completeness_design_brief_fable.md)·
    [稿](logs/reviews/verdict/2026-08-01_reading_completeness_design_fable.md)）：v1 建在预扫上、经用户「预扫不是杠杆」**整版撤回**；
    v2 = 尺寸链闭合当分母 + 读图器自己的验证痕迹当工作量账本 + 双读 diff 当二级复核。
    **主控核验一对一错**：✅ 双读 diff 独立重算逐条吻合（d1/d2 只有 4 条对得上且中点距离**精确 0.00 m**、全是外轮廓；
    内墙 0 条 ⇒ **抄数字的可复现、目测的不可复现**，不看答案即可分辨）；
    ❌「两抽都零验证工作量」被证伪（**d1 实跑 3 次探针**，侧车没被 merge 搬出考场 ⇒ 那个计数器量的是搬运策略）。
    **⭐ 由此挖到更好的账本 = 考场守卫写的 `access_log.jsonl`**（命令原文+放行/拒绝+理由、按 attempt 归档、进指纹、
    **被测者伪造不了**）**同样零消费者** ⇒ 今天第三次撞见同一个病：**自评字段 / CV 证据 / 访问日志，信号都产出了、没人读**。
  - **⚠️ 主控自身两处错误（如实登记）**：① **声称已把修正发给 Fable、实际消息没发出**
    ⇒ 规约候选：**凡声称已派发的动作，必须在同一轮内有对应工具调用回执**；
    ② **量纲错误**：把 07-07 的「8/8」与今天的「70.9 %」并排比 —— **v3 判卷层 07-31 才建成**，
    两者未对齐前不可直接比较，该比较已收回。
  - **⚠️「文档说服无效」这条结论按用户要求不写死**（三次失败都在 Haiku 上、且每次混着别的变量），改列待验。
  - **运维**：全卷首跑 19 分钟撞 API 断线（`Connection closed mid-response`）静默死掉，
    哨兵因 `pgrep -f "claude -p"` 误匹配到**前几天遗留的监控循环**而判成「还活着」、白等 70 分钟
    ⇒ 新哨兵改为三判据：产物齐 / 日志出现 API 错误 / 访问记录 8 分钟不增长。重跑 46 分钟正常完成。
- **⛔⛔ 上一节点（2026-08-01 收工时口径）= 「上游给了指令不照做、被打回就照做」双独立调查 ⇒ 病灶定位到「完成度判定没有机器所有者」；用户判定：此前的 reading 成绩都是假象，且没有准确回归的办法**
  （**零代码改动**·[GPT 侧报告](logs/reviews/verdict/2026-08-01_compliance_gap_investigation_sol.md)·[问题书](logs/reviews/request/2026-08-01_compliance_gap_investigation_brief.md)）：
  - **打法 = 双独立调查**（GPT 侧 sol + 主控各自查、互不通气；问题书只给事实与线索、**不给假设或解法方向**）。用户明令「先不要改动」。
  - **⭐⭐ 决定性发现（sol 先发现、主控独立验证两遍）**：d1 在正式产物里用**结构化字段**写了
    `self_check.all_visible_strokes_captured = false` + `all_dimensions_transcribed = false`
    （并附「只描了主要分隔」「窗检测到但没画」），而**该字段在整个生产代码里零个消费者**
    （`grep` 全仓：只出现在 `guide.md:290` 的 schema 文档与产物里，`src/` 零命中）⇒ gate① 以 0 阻断放行。
    **⇒ 读图器没有不听话：它读了自检清单、诚实自评、正确判定没做完、写进指定字段、提交。
    没人说过 false 不许提交，也没人去看。主控当初打回提供的，正是这个信号缺失的消费者。**
  - **⭐ 由此解释了「把话说清楚」为何连续失败三次**：E1（07-07 纪律写进 skill）→ W1（08-01 提到顶层非可选）
    → W3（08-01 把正确写法写进报错）。**第三次是把标准答案递到手上**——d1 拿到精确的
    `did you mean --tool prescan-plan?` **仍然放弃该路径** ⇒ **08-01「回执不可操作才放弃」的归因被推翻**。
    根本原因：**文档不可能验证别人有没有遵守自己。**
  - **⭐ 机制侧硬证据（主控查）**：好成绩两轮在平面图上 **sm21 = 33/24 次工具调用（crop_zoom 17/16）·
    sm24 = 19 次（crop_zoom 11）**，即**逐个候选放大核验**；**今天两抽 1–5 次、crop_zoom 零次**。
    两轮打回的指令原话都是「逐条核验 / 全墙完整描」⇒ **做对时在做枚举，崩时在做目测。**
    **⚠️ 且 07-07 两轮均无预扫**（`cv_evidence/` 下无 `prescan/`，全是读图器自己按 001/002… 编号的产物）。
  - **⛔ 但归因不干净，三个缺口（两边独立收敛）**：① **07-07 事前完整 prompt 从未落盘**
    （记录原文「完整 prompt 在主控 transcript」，已丢失）⇒ 无法排除「那次打回是它第一次被要求」；
    ② 07-07 与今天差 ≥4 个变量（监督/预扫/隔离档次/卷量）；③ 今天同配置两抽差 2.8×（噪声主导）。
    **并且打回不是零信息**——两边独立指出反馈含「你漏了哪些」这类**针对产物自身**的差异（不含建筑信息）。
  - **一处两边分歧、主控认输**：主控把「守卫摩擦」（今天两抽吃 6/3 次拒绝，07-07 走 prompt 级隔离零守卫）排第一，
    sol 排第六并给出决定性反驳——**d2 一次新探针都没尝试过，摩擦解释不了 d2** ⇒ 摩擦只能是放大器。
  - **⚠️ 冷水（决定下一步形态）**：**d2 四个自检字段全填 `true`，成绩仍只有 24.8 %**
    ⇒ 把该标志位变成阻断项**只能抓「诚实的没做完」，抓不住「自信的做错」**，且最可能的结果是
    **d1 学会变成 d2**。⇒ **「完成度由谁判定」必须有不依赖自评的答案，否则第一条白做。**
  - **⭐ 用户收工判定（下轮起点）**：**「之前的 reading 都是假象，且不是简单的问题、还没有准确回归的办法」**
    ⇒ **下轮先点射 Fable 出一版解决方案，再讨论怎么解。**
    **⚠️ Fable 2026-07-21 已退订、非可直接调用席位** ⇒ 走 **Comate 人工中继**（§5#14：主控出**脱敏 prompt**
    〔不含项目源码/文件树〕→ 用户在 Comate 侧跑 → 贴回；该通道口径正是「只做不碰代码的活」，与本轮任务吻合）。
  - **可行方向（已在册，非方案）** = plan.md 债 #2「**把测量整个移进代码，识图降为在确定性候选上分类 + 查漏**」。
    **实测卡点**：预扫长结构线**只有 5 条**，其中 3 条精确命中答案内墙（误差 **0.06–0.07 m**，容差 0.30 m），
    但答案有 **16 段**内墙 ⇒ **召回远不够当完成度分母**，这是设计轮第一个要解的。
- **⭐ 同日（2026-08-01）= W5「减卷无监督识图·同配置独立两抽」跑完 + 撞出 W4 判卷 BLOCKER 并修复**
  （`caca860`·**2047 → 2051 绿 + 10 xfail·零红**·施工 terra / 主控轻门·[全档](logs/experiments/2026-08-01_w5_scoped_unsupervised_reading/README.md)）：
  - **用户拍板**：同一套配置**独立考两遍**（d1/d2）· **只跑识图 + 出分**。
    两抽考试范围哈希逐字相同（`ef5f5bad…`）⇒ 机械证明配置一致；答案账本哈希逐字相同（`45365cbf…`）⇒ 尺子未被被测物变形。
  - **⭐⭐ 结论① 两抽相差 2.8 倍 ⇒ 这个量级的单次成绩就是噪声**：内墙命中 **d1 = 5.18/57.86 = 9.0 %** vs
    **d2 = 14.34/57.86 = 24.8 %**（同模型同图同文档同范围同预扫档，唯一差别 = 抽样）。
    08-01 A 臂那个 35.8 % 落在两抽之外 ⇒ **回溯地看，此前所有单抽成绩的可比性都应打折**。
    **⇒ 用户「考两遍」这一拍板是本轮决定性的**：只跑一遍的话，结论完全取决于抽到哪个。
  - **⭐ 结论② 「探针次数」不是「有没有去量」的代理指标（对 08-01 判据的修订）**：
    **d1 调 5 次探针**、拿到 27.47 mm/px，**却自述内墙是 *"traced via visual inspection rather than dimension
    derivation"*、±0.2 m**（并写明「时间花在外轮廓和主分隔上，内部没余力」）⇒ 9.0 %；
    **d2 只调 1 次探针**，但直接消费预扫的 `calibration_span_candidates`，两轴得 **36.4 / 36.375 px/m、
    跨轴一致 0.04 %**（门限 0.30 %）并显式记「标定接受」⇒ 24.8 %。
    **⇒ 量得更好的是探针更少的那一抽；判「有没有测量」必须看标定与坐标的来源，不能数工具调用次数。**
  - **⭐ 结论③ 标定变好了，内墙仍然靠目测 —— 分数就丢在这里**：两抽在同一处失守。
    **「先量再画」被理解成了「先把比例尺量准」，而不是「每一条墙的位置都要量」** ⇒ W1/W3 没覆盖到这一环。
    **另：平面窗 0/11 连续第三轮全崩**（07-30 / 08-01 / 本轮），与减卷无关、是独立能力缺口。
  - **gate① 第三次坐实 S-0**：9.0 % 与 24.8 % 两份产物**阻断层结论完全相同、都是 0 block**；
    旗标层再次有信号（`stroke_dimension_consistency` 1 条 vs 4 条）但无阻断权。范围外三张显式记 `not_applicable` + 声明来源。
  - **⛔ 第一次真用 W4 就撞出 BLOCKER = 减卷判卷跑不通**（首判两抽均 `{"kind":"rejected","error_code":"score_view_binding_invalid"}`）：
    根因 = GT 侧信任根校验**没把考试范围传下去**（`score_inputs.py:141`），拿全部五张当「必需」与收窄后的两张对不上；
    修完立刻会撞第二处（`opening_claim_score.py:234` 对范围外 ref 直接 raise），主控在派工单里一并点名。
  - **⭐⭐ 为什么施工自查 / 主控轻门 / GLM 对抗审三道关全漏**：W4 补的 L8 锁断言的是 `score_vs_gt is not None`，
    而**判卷器「拒绝」时产出的侧车也不是 None** ⇒ **锁绿着、判卷其实是拒的**。三方都验了机制
    （冻结 / 防漂移 / 消费侧收窄 / 六道守卫真锁），**但没有任何一方真的跑一次带范围的完整判卷看它出没出分**。
    **⇒ 治理教训升为两条并列：「探针 ≠ 锁」+「非 None ≠ 成功」**（断言写在返回值存在性上 = 等于没断言）。
  - **修复口径由主控裁定、未下放**：读图器没见过范围外的图 ⇒ 只在那些图上才看得见的门窗**整个移出分母**并显式记来源；
    但**只要有任何一条证据落在范围内就照常考** —— **减少题量不等于放水**。
    主控独立验真：回退修复 ⇒ **恰好那条强化后的 L8 变红**（此前同缺陷在场它是绿的）；
    识图产物哈希重判前后逐字相同（未重跑识图）；独立全量 **2051 绿零红**。
  - **⚠️ 登记跟进债（主控自己的欠规格，如实登记）**：主控派工单的参数表写在**门窗**这一层，
    而现实有**「门窗的某个指标」**这一层（如窗台/窗顶高度只在立面可见）⇒ 这类被记成 `unobserved`
    而非 `outside_reading_exam_scope`。**分数不受影响**（两者同为 not_applicable、同样出分母），仅来源标签偏粗。
- **✅ 上一节点（2026-08-01 同日）= 「无监督识图使能」批（W1+W3+W4）整批 CLOSED**
  （`3b7d930` → `2cb1f82` → `a796c6b`·**2040 绿 + 1 红 → 2047 绿 + 10 xfail·零红**·
  **施工 GPT 侧 terra / 审 GLM-5.2 跨家族对抗审 = APPROVE-WITH-CHANGES / 主控轻门**）：
  - **⭐ GLM 审 = 20 条命题全部成立（A 4/4 · B 6/6 · C 10/10）· 0 BLOCKER / 0 MAJOR / 1 MINOR / 1 NIT**，
    独立全量 2046 与主控逐字一致，工作树零改动零 commit，破坏性探针全在 `/tmp`。
    **审阅单按 GLM 强项写成验证性清单**（每条写死「验什么 / 什么算不成立」），
    **并特意留两条「要它来证伪主控」的承重命题 —— 它主动证伪均失败 ⇒ 反向坐实**：
    **B1** 拿一个既不在工具名表、也不在真授权表里的假工具去试 ⇒ 守卫放行、真授权表拒绝
    ⇒ `PROBE_TOOL_NAMES` **确非第二张授权表**（W3「零扩权」声称成立）；
    **C3** 构造两种「两个哈希不一致但校验通过」的篡改 ⇒ **均被挡** ⇒ r2 删那道冗余检查安全。
  - **⛔ GLM 清单外自主发现 S-1（MINOR·假锁）= 主控 neuter 漏扫的同族**：W4 还引入了**第二道**考试范围守卫
    —— merge 读图产物时校验「范围有没有在 build 之后被换掉」（`isolation.py:340`）—— **同样无锁**。
    **主控独立复现且跑得更宽**：摘掉那三行，`test_isolation` + `test_view_manifest_generator` 共 **244 全绿**；
    既有测试只断言 binding **记录了**范围哈希、**没断言「改了会被拒」**。
    **主控的 neuter 只覆盖了判卷侧那六道、没扫到隔离/合并链 ⇒ 跨家族对抗审的价值再证：
    它按主控写的清单验完，还从清单外找到了同族漏网。**
  - **NIT-1（卫生）**：探针错误提示的语法样例用了真实楼宽 `15.0` / `overall_width`（worked-example 那栋楼的真宽度）。
    **经核非污染**（与目标 sm24 无关；**主控用结构化遍历复核 = 0 命中** ——
    主控最初用裸正则查出的「15.0」实为命中 sha256 十六进制串里的 `15`，**如实更正**）。
    但仍改成一看就假的占位值：**拿任何真实建筑的真实尺寸当样例，等于在赌以后的目标 case 不会撞上这个数。**
  - **r3（`a796c6b`）= 两条 finding 窄修**：补 merge 拒绝锁 + 换占位值。**主控独立验真：摘掉那道 merge 门 ⇒
    恰好 `test_merge_rejects_reading_exam_scope_changed_since_build` 一条红、零连带**；
    独立全量 **2047 passed / 10 xfailed / 0 failed**。**⇒ 本批 CLOSED。**
  - **⭐ 该锁的构造值得记**：它把声明**和**冻结件**一起**改成一个「自洽的新范围」（resolver 因此照常放行），
    **靠 build 时记进 binding 的旧哈希把它拒掉** —— 即**单靠 resolver 挡不住的那种「考中改卷」，正是这道门的存在理由**。
  - **r1 = 修缺陷**。修法比原实现更紧：抽出 `resolve_frozen_reading_exam_scope(run_dir, base_manifest)` 作**唯一**只读消费者，
    `verify_view_manifest` 改为调用它（**不留第二把尺子**）；判卷侧因此**根本不需要 case 目录** —— 冻结件自带
    `base_view_manifest_sha256`，与判卷已加载的那份 base 直接对账 ⇒ `--base-dir` 恢复可用、未声明 scope 的 run 逐字节不变。
    **顺带补上一道原先没有的检查**：冻结件必须绑定到判卷正在用的那份 base manifest。
    **主控独立全量 2042 绿零红**（与 terra 数字逐字一致），三个身份哈希主控独立重算逐位不变。
  - **⛔ 主控轻门抓到第二条（同族「门是真的、锁是缺的」）**：在 `/tmp` 克隆逐道守卫 neuter ⇒ **6 道里 5 道无锁**
    （冻结件在但声明被删 / 冻结件绑到另一份 base / `content_sha256` 漂移 / **判卷侧根本不按 scope 收窄 bindings**，全部摘掉仍 277 全绿）。
    **最重的是最后一条 —— 那是 W4 判卷侧的全部功能点、也正是 W5 减卷要靠的那条**；terra r1 给的是临时 run 里的手工探针
    ⇒ **探针证明「当时跑对了」，但不会在有人改坏时变红**。另查出 `declaration_sha256` 那道是**冗余检查**
    （`content_sha256` 是含它的整个 payload 的哈希且模型层强制自洽 ⇒ 它不可能成为唯一触发原因、**也无法为它构造独立锁**，
    两条一起摘才红 = 互相遮蔽）。**如实登记：3 条在 r1 之前就以等价形式无锁、收窄那条来自 `2d2137e`、只有 base 绑定那条是 r1 新加的。**
  - **r2 = 只补锁不改语义**（唯一生产码改动 = 按主控推荐删掉那道冗余检查，删完 `content_sha256` 自动获得独立锁）。
    **主控独立复跑 neuter 逐条验真：6 道守卫各摘一次，每次恰好红 1 条、且正是 terra 点名的那条、零连带、零假锁**
    （L8 那条走真 `_grade_typed_attempt_artifacts` + 真 GT + 真产物，只 monkeypatch 服务层抓 bindings）。
    **主控独立全量 = 2046 passed / 10 xfailed / 0 failed。**
  - **⚠️ 登记跟进债（主控独立发现，未让施工方顺手补 —— 那是另一个决定）**：判卷路径上的「on-disk manifest vs 由 case 元数据重建」
    漂移门，**在「已有 accepted attempt 且不重画」时不经过**（此时 `run_one_stage` 早退、不调 `_draw_reading` ⇒ 不 provision）。
    **该缺口 W4 之前即存在、本次未改变**；terra 的可达性回答（留在 provision 与 `cmd_judge`）对**重画路径**成立、未覆盖这条。
  - **治理数据点**：① **「探针 ≠ 锁」应与「门是真的、锁是缺的」并列**——本轮施工方两轮的自查表都诚实且准确，
    但 r1 的验收证据形态是探针，**探针不具备回归效力**；派工单今后须**明写「每条新守卫必须有摘掉即红的锁」**，
    否则施工方会照字面只给探针。② **主控轻门的 neuter 必须由主控自己跑**：本轮 terra 的自查表与主控独立复算逐条吻合，
    但那是**验证之后**才知道的。③ 08-01 的 `.git/index.lock` 教训已生效：**本轮主控全程只跑只读命令，零抢锁、零阻塞。**
- **⛔ 上一节点（2026-08-01 Opus 5 主控）= 「主控参与生产」全面排查 + 判据被用户校准 + 第一份无监督识图基线 + W1/W3/W4 施工**。
  - **⚠️ 用户校准了不变量 #7 的判据（07-31 原判据过宽、已作废，详 §1.5 #7）**：**dev 期主控编排合法、主控兼任 judge 合法**
    （judge 是 dev 辅助、不属产品环节；产品要不要 judge 最后工程化再说）；**真判据 = 每个环节自己能走完输入→输出**
    （拿掉主控整个流程跑不出来可以接受）。**judge 只能整轮盲重抽、零信息 = 另外做一次**，
    **禁按子部分打回 / 原任务给反馈续作 —— 即使反馈纯属方法、零信息泄露也违规**（粒度即违规）。
    **⇒ 主控 v1 排查按旧判据把两条合法的东西列成头号违规**（识图段无代码执行器 / judge② 未接模型），
    **用户当场纠正 ⇒ 教训：判据没跟用户对齐，整份排查的分类全错。**
  - **排查产物** [审计报告](logs/experiments/2026-08-01_controller_in_production_audit/README.md)：**真违规四条，全在识图输入通道**
    ① **pilot 停等 review + `feedback.md` 续作** —— ⭐**「停下等审阅」写在产品 skill 库 `session_kickoff.md` 里、不在 dev 脚手架**
    ⇒ 读图器是被自己的启动文件命令停下等人的；**07-07 那个 8/8 正由此而来**（当日已改，见下）；
    ② per-run directive（198 行）—— ⚠️**不能只删不补**（其 §2/§4.7 实为两条缺失 gate① 检查的替代品）；
    ③ 预扫参数主控临时挑；④ 污染闸门 `check_feedback_text` 纯词法、挡不住裸坐标。
    **⚠️ 另一类非违规但真问题（judge 成本）= 判决性实证 S-0**：sm24 的 **8/8** 与 **1/8** 识图各跑一遍最严格档 gate①，
    **阻断层结论逐字相同、都是 0 block** ⇒ **确定性层对识图质量分辨力 = 0**，替 judge 分担不了任何东西。
    病根的书面形态 = `reading.py` 注释明写 *"advisory only… **J0 must verify**"*；普查 `src/validator/` 显式降级共 3 处 ⇒ 逐条清可行。
  - **⭐ 第一份无监督识图基线**（[全档](logs/experiments/2026-08-01_unsupervised_reading_baseline/README.md)·两臂·唯一变量=预扫·零 directive/零 feedback/零中途反馈）：
    **① 两臂都自己读完五图 + summary、全程没停下提问** ⇒ **「环节自己走完输入→输出」在识图段已达成**
    （对照 07-31 pilot r2 停在半路问「Would you like me to continue…」—— 那不是模型不行、是产品文档叫它停）。
    **② 但成绩不合格、不能用**：A 臂（带预扫）内墙 **20.70/57.86 m = 36%**、**多画 64.20 m**（画的墙里约四分之三是虚构的）、
    平面窗 **0/11**；B 臂（无预扫）内墙 **0%**。同尺子下 07-30 那份有监督的是 0.48/57.86（今日在 scratch 副本独立重算、与 07-31 记录逐位吻合）。
    **③ 根因：两臂都没去测量。A 臂跑了 0 个探针**，自述「标定推迟、坐标靠目测」；它唯一一次标定尝试被守卫按语法拒了一次
    （漏 `--tool`）**就整个放弃**。⇒ **「量而非看」没错，错的是「把工具箱摆着指望它自己去用」这个落地方式**。
    **④ 归因边界**：A vs B 只差预扫 ⇒ **预扫结论干净（35.8% vs 0%，反驳 07-30「预扫噪音是元凶」的猜想）**；
    但「无监督不比有监督差」**不是单变量结论**，只能说无监督没造成崩塌。**07-07 那个 8/8 至今没有无监督对照。**
  - **⭐ 历史考据（用户提问后逐条查证）**：**07-02 那份 9/9 · 15/15 · 0.0 m 的 Sonnet 5 产物 = `attempts=1` 一次成、无返工轮、
    且当时根本没有工具箱**（它自己用 PIL 灰度投影 + numpy + scipy 连通域临时搭了一套 CV，112 次工具调用，
    第一张图 30 min 发明配方、最后一张 42 s）⇒ **目前唯一一份干净的、无干预的、达标的 reading**。
    **07-07 主控投喂的内容经查证是「思路/流程」不是「信息」**（记录原文「纯流程合规反馈，无 gt 泄露」）
    ⇒ **能力没问题、缺的是思路，而思路可以 skill 化** —— 但按 08-01 校准判据，**那次按子部分打回仍属违规、8/8 不算数**。
    **⚠️ 更正**：主控此前把「全 `dimension_derived` = 零实测 = 失败特征」当判据（写进 07-31 directive §2）**是错的**——
    07-07 那份 8/8 也是 17/17 全 `dimension_derived`；而 07-02 那份 9/9 **全是 `seen` 且 `dimension_refs` 全空、零像素痕迹**
    ⇒ **`provenance` 字段与成绩完全不相关，现有 schema 判不出「量没量」**。
  - **施工（GPT 侧 terra / effort=high，[派工单](logs/reviews/request/2026-08-01_reading_unsupervised_enablement_dispatch.md)）**：
    **W1** 先量再画提到 kickoff 顶层非可选项、删掉「required or deferred 见那个文件」的间接层（`15cfcb8`）·
    **W3** 探针回执可操作（`--help` 放行为精确三 token 形式、参数错给正确写法；**主动拒绝放 `mkdir`/`find`、零扩权**）（`0763164`）·
    **W4** run 级「本轮考哪几张」声明（`run_config.yaml` 声明 → provision 时冻进 `_run/reading_exam_scope.json` 绑双哈希 ⇒
    **开考前定死、考中不可变更**；判卷 bindings 消费侧取子集、签名件不动；**sm24 三个身份哈希逐字不变**）（`2d2137e`，主控代提交）。
  - **⛔ 主控轻门抓到 1 条真缺陷（✅ 已于同日返工 r1 CLOSED，见上条）**：[`run_stage.py`](../scripts/tool_scripts/run_stage.py) 判卷侧
    新加的 exam-scope 校验对 `0_reading` **无条件触发**且把 case 路径**硬编码**成 `case_tests/e2e_tests/<case>`
    ⇒ ① **无视 `--base-dir`**（该 CLI 明确支持，主控当日就用它在 scratch 目录跑过重判）② **违派工单 §1.6「默认行为不变」**
    （未声明 scope 的 run 也走该校验并可能抛错）。红的是 `tests/test_c2_b4b_phase_d.py::test_gt_echo_fixture_preserves_runstage_cli_byte_parity`。
    **terra 三个 slice 都报「欠规格边界：None」没抓到它，因为它被 git 锁卡在交付前的全仓那一步 —— 而全仓正是唯一能抓到这条的地方。**
  - **运维（两条，都值得记）**：① **codex MCP 第五次撞 30 分钟静默超时** ⇒ 查明**是 Claude Code 客户端侧的空闲计时器**
    （codex 发的是自家 `codex/event` 而非 MCP 规范的 `notifications/progress`，计时器永不重置；Anthropic 侧同族 issue #58687 已 closed as not planned）。
    **中止的只是主控这边的等待、codex 进程不会被杀**（本轮 W1/W3 两个 commit 全是超时之后产出的）
    ⇒ **修法已落**：`.claude/settings.local.json` 加 `Bash(codex *)` 权限（已实测生效 ⇒ **以后施工席走 CLI 后台、不阻塞**）
    + `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT=3600000`（需重开会话生效）。
    ② **⚠️ 主控为绕开 MCP 超时去轮询工作树，跟 terra 的 `git add` 抢出了 `.git/index.lock`、把施工席卡住**
    ⇒ **规约候选：主控监控施工席时只跑只读命令，`git status` 等会刷新索引的命令也算写**。
    terra 撞锁后**拒绝自行删除**（派工单写了「删除需单独授权」）、停下上报 —— 纪律正确。
- **⛔⛔ 最新（2026-07-31 Opus 5 主控）= 「跑测流程修复」大批 + ⚠️用户当日提出 reading 监督污染问题、明日优先重新设计**（全仓 **1786 → 2028 绿** + 10 xfail·零回归·`f98d248`→`13cc33a`）。本日以 sm24 为跑测修复案例，把 07-30 卡死的六条缺陷全修 + 另修主控预扫新发现的一条 + pilot 又暴露三条链路断裂，**全部经跨家族独立对抗审 + 主控轻门**。
  - **⚠️⚠️ 当日最重要的产出不是修复，而是用户识破的一个架构级问题：[reading 的监督污染](logs/experiments/2026-07-31_sm24_e2e_retry/SUPERVISION_CONTAMINATION.md)**。用户拍板两条硬口径：① **reading 时间要算总量**（主控把活提前做了不算 reading 变快）；② **上线版本没有主控 ⇒ judge 整体打回可以，但绝不可以主控告诉 reading agent 哪里错了该怎么改**，要实现的是「Haiku 等级模型独立完整完成 reading 并保证质量，过程中不接收任何更强 agent 的信息」。**⇒ 主控自查发现三条违规通道**：per-run directive（主控看着失败现调、随轮投喂）/ pilot→主控反馈→返工（`isolation.py` 有机制化的 `write_feedback` 注入点）/ 预扫参数由主控临时挑。**⇒ 用户判定「之前在 sm21 和 sm24 上拿到的高分很可能是虚假的」**——**07-07 那个 8/8 北极星成绩的过程记录白纸黑字写着 pilot r1 被主控打回并被告知「标定错锚 / 候选未逐条核验 / 字段全空」，r2 才达标** ⇒ **该成绩不能作为无监督基线**。**本轮实测佐证**：pilot r2 在长线视图齐备下自己停在半路输出「Would you like me to continue…」等主控回答 ⇒ 流程本身是围绕「主控在场」设计的。**用户拍板：明日优先单独全面检查并重新设计 reading，具体方案届时再议。**
  - **仍然有效、与监督无关的确定性成果（明日可直接继承）**：**① F-6 BLOCKER 已消**（v3 判卷层建成识图阶段的生产投影 + 能力守卫；sm24 真实识图产物走生产路径出 sidecar v9 + `c2_scored` + grade.png，不再崩）+ **坐标级尺子回到生产**（此前 `load_gt` 对 v3 硬拒 legacy ⇒ v3 答案的识图完全没有生产级尺子，只能主控手搓、违「禁手搓判卷」）；② 硬隔离守卫改**按参数角色**判定 + 补真写保护洞（散文误伤 **13 → 0**，且 44 形状差分证明**净收紧 13 处**、只放松授权的一处）；③ 探针**单调用 + bounded batch**（20 次探针的测量扫描 **40 轮 → 1 轮**）；④ 预扫**按 kind 拆分（零丢弃）+ 长线合并** —— **实测长线视图直接覆盖 GT 8 条分区线中的 6 条、误差 0.01–0.13 m**，并令 **pilot r2 在无人提示下标定出 36.41 px/m、两轴偏差 0.046%**（上一轮 40.22 / 9%，因为它量的是尺寸链跨度而非建筑本身）；⑤ gate① 平面帧契约按 `run_profile` 分档（保住 07-07 那份历史参考产物不被废）。
  - **治理数据点（本日最值得记的三条）**：① **主控自己的边界写错/写窄，被精确地实现成同样错，一天内发生三次**（U-13 把帧冲突归错类＝开假绿杠杆 / r1 只裁 content 免扫没裁 path 必查＝造成 `case_tests` DENY→ALLOW 真回归 / D-1 措辞过宽＝差点把一把真锁误判成 MAJOR），与 07-28 MAJOR-1 同型 ⇒ **「边界写窄就会被实现得同样窄」应升为规约条款**；② **本批共抓 5 把假锁，其中 3 把是施工方自己抓的**（夹具形状族：token 数恰为偶数被另一规则兜住 / 夹具名恰等于工具自动编号 / lossless 只证 split==master 而漏了上游丢弃）—— 施工方自查纪律已立住；③ **跨家族对抗审再次抓到主控六条探针全漏的缺陷**（白名单 helper 的写副作用可绕过写保护真往 `tools/**` 落盘）。
  - **时间口径更正**：主控此前只报 reader 会话墙钟。本轮补测**主控侧前置 30.7s**（五图预扫 23.6s + 工作区构建 7.1s，全为确定性代码），reader 会话 447s ⇒ **总量 ≈ 478s**。以后一律报总量。
  - **审轨**：[判卷问题书](logs/reviews/request/2026-07-31_reading_typed_scoring_brief.md) · [设计稿](proposals/reading_typed_scoring_plan_sol.md) · [主控裁定 U-01–U-15](logs/reviews/verdict/2026-07-31_reading_typed_scoring_design_controller_rulings.md) · [判卷对抗审](logs/reviews/verdict/2026-07-31_reading_typed_scoring_glm.md) · [主控终审](logs/reviews/verdict/2026-07-31_reading_typed_scoring_controller_final.md) · [脚手架派工](logs/reviews/request/2026-07-31_isolation_scaffold_construction_dispatch.md) + [r1](logs/reviews/request/2026-07-31_isolation_scaffold_rework_r1.md)/[r2](logs/reviews/request/2026-07-31_isolation_scaffold_rework_r2.md)/[r3](logs/reviews/request/2026-07-31_isolation_scaffold_rework_r3.md) · [脚手架对抗审](logs/reviews/verdict/2026-07-31_isolation_scaffold_sol.md) + [r2 复验](logs/reviews/verdict/2026-07-31_isolation_scaffold_r2_verification.md) · [链路断裂派工](logs/reviews/request/2026-07-31_reading_chain_gaps_dispatch.md)。
- **⛔ 最新（2026-07-30 Opus 5 主控）= sm24 端到端跑测**第一次尝试**，卡在识图判卷门、用户拍板「先停，修好再跑复验」**（无生产码改动·测试 1786 绿不变·实况全档 [logs/experiments/2026-07-30_sm24_e2e_attempt/](logs/experiments/2026-07-30_sm24_e2e_attempt/README.md)）：**跑前按铁律停下问用户拍配置 ⇒ 三项全按 07-27 原案**（识图 Haiku 4.5 + 量图工具箱 / 全链含真跑 EP / 判卷拦停 + 只开几何人核）。**三个「第一次」各撞出一个真缺陷**，全属「机制建好但从未在真实 case 上跑过」。
  - **⛔ BLOCKER（F-6）= v3 判卷层对 reading 阶段既无生产投影、也无能力守卫 ⇒ 一进 J0 必崩**（`ScoreContractError: score_product_identity_invalid`，未捕获、带崩整条 flow）。根因两处叠加：① `decide_score_capability` 对 correction 有两道守卫（product_schema 必须 v3 + artifact_contract 必须 B5 两契约之一），**对 reading 一道都没有**、直落 `c2_v3`；② `score_typed_attempt` 里 `stage=="correction"` 走真生产提取器 `extract_correction_plan_segments`，**else 分支要顶层 `segments` + `elevation_observations`**，而识图产物形态是 `{"views": {…}}`，**全仓无任何生产代码产出该形态**（`grep` 仅命中测试与一审计脚本＝测试全靠手搓 payload）⇒ **任何 v3 答案 case 的识图阶段必崩**，sm24 是史上第一个 v3 签字答案 case 故从未触发。**同族于 07-20 M2**（判卷撞 `ScoreContractError` 全链无捕获→flow 崩），但那次在非 accepted attempt、**这次在 accepted attempt 且无条件**；**并违 R-4**「判卷只许说 unsupported 不许崩」。附带小缺陷：`payload.get("elevation_observations", ())` 默认元组、校验要 list ⇒「键不存在」被报成「不是列表」，错误文案指错方向。**修法是设计决策非补丁**（识图到底做不做类型化判卷：退回 legacy 尺子 vs 真写 image-local→building-axis 投影层）⇒ **须走派工，主控不自行拍**。
  - **⭐ 本轮最有价值的产出＝意外收获，且由用户当场提出假设、主控立即用盘上数据证实**：用户见识图结果即判「错这么多应该是机制问题，之前跑过 sm24 效果不错」⇒ 主控以同一把尺子（GT 八道隔墙 · 容差 0.30 m）量三份历史识图：**06-24 Opus 5/8 · 07-07 Haiku+工具箱 8/8 满分 · 07-30 Haiku+工具箱+预扫+硬隔离 1/8（多画 10）**。**同模型同工具从满分掉到几乎全错 ⇒ 机制退化、非模型能力**。产出量同崩：笔画 25→15（平面 window 11→**0**）· 尺寸转录 51→13 · uncaptured 15→3 · 探针 19→8（另 6 次被守卫拒）＝**只做了约四分之一的活**，并错误断言「平面里没有窗」。**失败形状很具体**：15 条墙全部 `dimension_derived`、零实测，把**北立面**链 `540|1600|2520|4800|540` 的累加位置画成四道纵向内墙（那是窗与垛），而真正标隔墙的底部链 `4180|1640|4180`（→ 4.18 / 5.82 ＝ GT 两道纵墙）在 pilot 轮读到过、正式轮却没用 ⇒ **工具跑了、量出来的数没进产物**。**「量而非看」未被推翻，被推翻的是「给了工具就会去量」这个隐含假设**（对 [[reading-cv-toolkit-methodology]] 的适用域修订）。**归因候选四条**（硬隔离令探针成本翻倍＝写请求文件+执行两步 / 守卫摩擦吃 6 轮 / 预扫 803 噪音候选可能锚定到尺寸链 / **主控 directive 把「尺寸链逐字读」列为可接受来源第一位＝主控自身也是变量，如实登记**）⇒ **下一步＝单变量四臂 A/B**（`07-07 原样` / `+预扫` / `+硬隔离` / `+两者`），便宜且判决性。
  - **另两个机制缺陷**：**F-2**（MAJOR 候选）硬隔离 staging **不含 kickoff 强制要求的格式样板件**（另一 case 的已接受识图产物），且 `guard.py` 的 `DENY_TOKENS` 含 `case_tests` ⇒ **子代理被自己的 kickoff 指向一个墙外且必被拦的文件**；07-07 走 prompt 级隔离能读全仓故从未暴露。主控裁定按不触禁词路径补入（另一栋楼、不含本 case 信息＝非污染），**遗留：手工补入件不在 MANIFEST 内**。**F-4**（MAJOR 候选）守卫词法禁词**扫文件内容**（不只路径参数）⇒ 子代理写必交总结时用「约等号」被拒三次、该件一度写不出；**立面 JSON 里的 `grade line`（室外地坪线）＝本领域核心词汇被误伤**；同族被拦的还有 `python -c` 内分号、`> /dev/null`、管道、三点省略号。**定性＝可用性缺陷非安全洞，但会被误读成「模型不会写」**。另 **F-1**（预扫 CLI `--out-dir` 语义与手册口径打架，照抄产生套娃路径且套娃件不会进 staging）+ **F-5**（merge 要单一聚合件而 kickoff 令每图一件，无人负责拼装 ⇒ 主控手工按 `expected_output_id` 机械组装）。
  - **实际完成**：溯源记录更新到真实开跑时刻（07-27 铺好后原地挂起三天，`4e4da34`→`0342f66`，期间对本 run 相关脚手架的全部 git 级改动仅 `src/agent/correction/{cell_geometry,orthogonality}.py`、识图侧四目录零改动）· 五图预扫 · staging 污染面核过 · **判卷侧车四项身份用生产加载器逐一核对全吻合**（J0 不会因缺件 fail-closed）· 识图两轮（pilot 只描外墙但**如实自标未完成**、方法正确故 approach 批准 → 打回一次做完五图）· merge ＝ **attempt 003 accepted**（gate① 阻断层干净 + 6 条 `cross_check` 非阻断旗标）。**下游 1_correction / 几何 / MEP / 装配 / EP 全部未跑。**
  - **⇒ 下一站（用户 07-30 拍板）＝ 先修判卷缺口，修好后跑复验**；**复验轮须重跑识图**（本轮 attempt 003 质量 1/8 不合格、不得复用）。run 目录原地保留。
- **✅ 上一节点（2026-07-28 Opus 5 主控）= 「诊断仲裁 + 守恒判据 + 来源身份」批 CLOSED ⇒ 判卷器三处立足点全部换成可复算证书**（`cce6e83` → `ce23426`·全仓 **1725 → 1786 绿** + 10 xfail·**零回归**）：**GLM-5.2 跨家族验证性对抗审 r1 = APPROVE-WITH-CHANGES（1 MAJOR）→ sol 窄修 → r2 = APPROVE（0 BLOCKER / 0 MAJOR / 0 MINOR / 1 NIT）**。**⭐ 本批与前三轮的决定性差别 = 破坏测试首次被独立方实跑对账**：GLM 在 `/tmp` 克隆里重跑 **14 个指定 neuter**（覆盖 S1–S4 + MAJOR-1 修复，含施工方自查出的两处假锁），**红数与执行日志声称逐条吻合、零夸大**（唯一表面差异被其追到是 baseline-commit 偏差、非声称错误）；全仓独立复算 `1786` 与主控逐字一致。**对比 r1 教训**：上一轮 GLM 沙箱禁执行 ⇒ 只出静态审、**neuter 无人独立验**，主控发现后**带工具白名单重开一场专补执行验证**（`--dangerously-skip-permissions` 在 root 下被禁 ⇒ 改用 `--allowedTools`）。
  - **⚠️ MAJOR-1 = 主控自己的裁定写窄了（如实登记）**：主控轻门曾独立发现豁免位 `exact_error_context` 无锁，但把出口写成「守住 `_raise_score_input_contract` 这座桥」⇒ 施工方精确地只锁了桥；**而该位是 `JudgeDiagnostic` 的公开字段**，直接构造即绕过全部三把锁、**12 个证书字段塌成只剩 `reason`、全仓零测试变红**。GLM 构造出该逃逸、主控活体复现确认。**这正是本批教训自身的再演一遍：边界写窄，就会被精确地实现得同样窄。** **修法比主控给的选项更彻底**——sol 取出口 (a) 并再推一步：**布尔策略位整个删除**，豁免改由只能经受审桥梁构造的内部子类型 `_ExactErrorContextDiagnostic` 承载（探针现直接 `TypeError`）；GLM 用 **11 个攻击向量**复验（字段构造/`replace`/属性赋值/`__class__=`/pickle/copy 全被挡），残留 3 个向量均需显式 import 私有名 + 刻意反惯用写法 ⇒ 评 NIT 不阻断。**派工（用户 07-28 拍板）**= **sol 施工 / GLM-5.2 对抗审 / 主控轻门**，且**整批做完再审一次**（不拆多轮对抗审）；主控另加**不花额度的 Slice 边界轻门**作为唯一中途纠偏点。
  - **打法要点**：sol **既是设计者又是施工者**（本轮设计稿即其所出）⇒ 边界理解误差最小；派工单明令「**『我当时的意思是……』不是可接受的交付说明**」，并挂**规约 §5 的 sol 执行护栏三条**（删除/覆盖/推送单独授权·每阶段给可验证证据·一个 Slice 做完即停）。审轨 [派工单+五道轻门裁定](logs/reviews/request/2026-07-28_judge_arbitration_construction_dispatch.md) · [审阅单](logs/reviews/request/2026-07-28_judge_arbitration_glm_review.md) · [执行日志](logs/reviews/execution/2026-07-28_judge_arbitration_sol.md)。
  - **交付实况**：Slice 0 六条「先落会红的锁」**红的理由逐条对靶**（A-L3 得 `score_unsupported_combination` = **R3-B1 假绿活体复现**；B-L4 得 `score_denominator_nonconserving` = **R3-B2 1-ulp 假红活体复现**）→ S1 来源身份（**前两轮均未落地的那块**）→ S2 证明式仲裁（**唯一严重性出口 + 静态门**）→ S3 精确区间账本（**六锁全部转绿**）→ S4 版本/缓存/全链回归（**遗留浮点通道物理删除**·helper 升 `b4b_segment_score_v3_ic1` 无 v2 残留）。**整批 gt 与本管理文档零触碰**，sm24 受保护树 14 项 hash 逐段 byte-identical。
  - **⭐ D-1 最强证据（主控独立读证书、不采信自述）**：真实 sm24 正门对照的 **`public_rows.jsonl` 与 `wall_criteria.jsonl` baseline/new SHA-256 逐字节相同**（`blocking_change=false`）⇒ **改造未改变任何对外可见判分**；差异仅内部审计列 + 8 个 internal extra 浮点，每个附 exact fraction/domain/cut-id 舍入证书并由活锁钉住。
  - **⚠️ D-1 执行边界（施工方主动披露，主控裁定接受 + 转跟进债）**：仓库唯一真实已接受 sm24 correction artifact **早于 B5 六件套 proof wire**、无法进 correction 分支（除非伪造 proof＝信任根禁止）⇒ D-1 走 **reading 正门**（两侧输入逐字节相同 + 两侧真 `score_typed_attempt` + 无手造 `PlanSegment`，三条实质要件满足）。**缺口 = correction 分支未被 D-1 覆盖 ⇒ 下一站 sm24 端到端跑测须产出原生 correction 正门 D-1 对照**（与 B5 Phase D 的 MINOR-3 同族同口径）。
  - **治理数据点（本批最值得记的三条）**：① **施工方上报 10 处「设计稿定了语义、没定接口形状」的欠规格边界，无一自行降级为假设** ⇒ 主控逐条裁定写入派工单 §8–§12、与设计稿同等约束力（**这正是三轮失败病根的对症解**）；② **施工方自查出 2 处「指定 neuter 其实不会变红」的假锁**（B-L5 入口预排序遮蔽 accumulator neuter / B-L7 整数夹具恰好精确故旧减法也绿），无人指出下自行发现并修到夹具层 = **本批首次由施工方自己分辨「锁绿」与「锁真绑」**；③ **主控轻门独立发现 1 条必修**（§10.1 豁免位 `exact_error_context` **零测试锁** = 「门是真的、锁是缺的」，通用机制配窄用途必扩散），已在 S4 补三把锁。另：新增审计 CLI 触红「受影响子集」静态门时**未走 allowlist 遮盖、而是补真 certificate lock 修到根因**。
  - **⚠️ 运维**：codex MCP **连撞四次 30 分钟静默超时** ⇒ 主控改用「**从工作树 + 执行日志读进度**」作为可靠通道（对标 07-27「headless 进度看工作树、不能只看 stdout」教训）；sol 每个 Slice 边界提交 + 写日志，故零工作丢失。
  - **⇒ 本批 CLOSED。下一站 = 跑 sm24 端到端**（run 目录 `run_2026-07-27_haiku_e2e/` 原地挂起，从识图接着跑；**跑前必须停下问用户拍配置**）。**跟进债**：① **D-1 的 correction 分支未覆盖**——仓库唯一真实已接受 sm24 correction artifact 早于 B5 六件套 proof wire、无法进 correction 正门（伪造 proof＝信任根禁止）⇒ D-1 走 reading 正门（两侧输入逐字节相同 + 两侧真 `score_typed_attempt` + 无手造 `PlanSegment`，三条实质要件满足）；**下一站 sm24 端到端须产出原生 correction 正门 D-1 对照**（与 B5 Phase D 的 MINOR-3 同族同口径）。② GLM NIT：3 个需显式 import 私有名的残留豁免向量。
- **上一节点（2026-07-27 Opus 5 主控）= 「数值身份 + 计分度量」设计轮已过审 ⇒ 施工 r0–r3 连续三轮 ⛔REWORK ⇒ 未闭部分升级为窄设计轮**（即上条的施工基线来源）：
  - **施工 r0（GLM-5.2·`29a1ce0`·11 文件 +1007−144·全仓 1706 绿 + 10 xfail）**：W1 身份层删 1e-12 定格量化换单链接聚类 + 护带 + 直径守卫（阈值实测推导 merge 1e-12/split 1e-11/diam 1e-11）+ W3 联合切点原子化 + W4 分母换长度 + criterion 三分 + W5 共享正交模块 + §5-B `product_to_gt` 多对多重填。**主控开工门预扫先查出两处钉死常量**（`segment_scorer` 字面量 / `judge_score` 配置 hash **且同串内嵌 A0_contract.md**），写进派工单免撞；**并预扫 diff 点名三处形状可疑写进审阅单**（P-1 既有测试被改写 / P-2 A8 锁用 `approx` / P-3 §5-B 出口 2 打折）。
  - **⛔ sol 对抗审 = REWORK（2 BLOCKER / 4 MAJOR / 1 MINOR）**，主控裁决**7 条全部成立、无一驳回**。**B-1 = 把假红修成了假绿**（比原病更险）：`match_plan_segments` 外层逐 target 独立循环、`exactly_one` 每 target 内重建 ⇒ **一条 4 m 产品墙同时覆盖两道平行答案墙拿 `8/8 pass`**；**主控独立读码复核确认并加一层**——`obs_covered` 累加到 8.0 已 > 产品墙自身长度 4.0，extra 算出 **−4.0 被 `> epsilon` 静默吞掉，全程零守恒检查**。B-2 = C-1″ 输入合同只实现聚类未执行（合同①②需「意图」信息，实现只有距离 ⇒ **循环假设**）。**M-1/M-2/M-4 三条 false-lock**（施工方声称「21 锁全经 neuter、零 false-lock」被 sol 四组 neuter 证伪）+ M-3 W5 共享判据**生产/判卷调用数均为 0 = shipped-untested** + N-1 §5-B 出口 2 未交付（**但施工方的架构理由经 sol 独立验证成立**，故不升 BLOCKER）。
  - **主控预扫命中率**：点名三处中 P-1(b)、P-2 均被 sol 证实为 false-lock，P-3 理由成立但出口确未交付 ⇒ **预扫路由准确**（对标 07-20 同型正面数据点）。
  - **返工单 r1 主控给死骨架**（不只甩问题回去）：§1 产品墙**单向注册到唯一答案支撑线**（0 条→算多画 / **≥2 条→响亮拒绝**，不许选最近不许都算——理由 = 此时判卷尺本身分不开两道墙，按 R-4 判卷器只许说 unsupported）+ **三条守恒不变式必须在代码里 raise**；§2 **「意图」身份 = 来源身份**（polygon 顶点索引 / boundary segment 端点侧，输入里本就有 ⇒ 不造新格式不改 GT schema），**若实测无法机械验证须停下上报、禁再自行降级为假设**；§2.1 **直径阈裁定必须 ≤ 合并阈**（原 diam 1e-11 > merge 1e-12 ⇒ 守卫形同虚设，sol 反例 1 实证），merge/split 保留（sol 独立复算余量成立：合并侧 562×/281×、分裂侧 100×）。
  - **✅ 窄设计轮已闭环（2026-07-28）= 施工基线就绪、施工派工待用户拍板**（用户拍板打法 = **sol 出稿 / GLM 跨家族对抗审 / 主控终审**）：[问题书](logs/reviews/request/2026-07-28_judge_arbitration_and_provenance_brief.md)（只给事实与约束、不给解法方向）→ [设计稿](proposals/judge_arbitration_and_provenance_plan_sol.md)（**1380 行累计式自包含**）→ [GLM 裁决 APPROVE-WITH-CHANGES](logs/reviews/verdict/2026-07-28_judge_arbitration_design_glm.md) → [主控终审](logs/reviews/verdict/2026-07-28_judge_arbitration_design_controller_final.md) → sol 补稿。
    - **核心原则**：**「判卷结论必须由可复算的证书支撑，不能由执行顺序、错误文案、浮点偶合或未保留的语义前提支撑」**——四个禁止项经主控独立复核**与三轮失败的四个病因一一对应**（执行顺序 = r2 advisory 抢跑 / 错误文案 = r3 reason 白名单 / 浮点偶合 = r1 固定窗与 r3 零容差 / 未保留的语义前提 = 来源身份丢失）。三条缺口各换成**结构性判据**：**A** 证书式仲裁（只有「在 capability 不确定域的所有可接受解释下仍成立」的冲突才认证为 `CERTIFIED_CONFLICT`，**`reason` 降为纯展示、永不参与严重性判定**）/ **B** 区间原子账本 + exact-rational（重复记功 = **owner 重数**的结构性问题，不再比较两个浮点算路；`extra` 由未覆盖原子并集得出 ⇒ **结构上不可能为负**）/ **C** 来源保真 occurrence + alias 证书（**距离只提候选，焊成同一原子需独立于距离的结构证书**）。
    - **GLM 审 = 30 命题逐条判定 + 独立探针**，**八条承重命题全成立**、七条已否决路径均未复活、地基未被推翻；探针数字与 sol 裁决书、与主控此前独立核实**三方逐位吻合**。**两条 MAJOR = 两个新边界只有概念承诺、缺可机械判定算法**（envelope 传播做宽⇒假绿/做窄⇒假红；alias 证书未说清依据结构字段还是数值接近⇒可能退化回「距离反推意图」）。**清单外自主发现 E2**（certifier 的 predicate 集合可能退化成**新白名单** = reason 白名单换皮）——**主控与 sol 均未预见，本轮最尖锐发现**。
    - **⚠️ 主控终审的关键纠正**：GLM 建议「施工方开工前把两条 MAJOR 写成可机械判定步骤」，**主控不采纳，改由出案方 sol 补进设计稿本体**。**理由 = 本批三次失败的共同结构都是「机制选对、边界留给施工方猜」**（r0 守恒边界没定 / r2 并存优先级没定 / r3 哪些算真破裂没定）；MAJOR-1 后果**双向且互斥**（做宽假绿、做窄假红）⇒ **是设计决策不是实现细节**，再下放即第四次重复同一结构。**并把 GLM 的 E2 升级为必补第三条**（其「无 evaluator ⇒ NA」方向 fail-safe 符合 R-4，**但代价是对未知形态系统性放水，而放水正是三轮的实际后果** ⇒ 必须配可见性计数机制）。
    - **补稿三条全落地**（主控复核）：C-1 有限事实图 + 闭包 worklist + **终止条件证明**（fact 最多入集一次、边只从低 rank 指向高 rank）/ C-2 alias 改纯 wire 结构判据（owner+方向 / boundary interval 槽 / ring 序号），并给出**独立于距离的可验证性质**——「候选值即使相差 1 m，只要结构字段不变则证书判定不变」⇒ 循环假设被机械排除 / C-3 未知 predicate 有意 NA + 请求级逐项与汇总计数 + histogram + **A-L9 锁与指定 neuter** ⇒ predicate 集合不全不再静默积累。MINOR 1–5 并入（helper identity 定死 `b4b_segment_score_v3_ic1`、影响面扩至全部 v3 segment 计分锁、**sm24 v3 逐行 diff 列为必跑项**）。
    - **⇒ 下一步 = 施工派工待用户拍板**（本批施工档已连续三轮 REWORK，派工须重新评估）；按设计稿 §7 拆 Slice 0–4，**Slice 0「先落会红的锁」优先**（A-L3 / B-L4 / C-L1 / C-L7 / C-L11 经 GLM 探针实证在现码上全红）。
  - **⛔⛔ sol 复审 r3 = 第三次 REWORK（2 BLOCKER / 1 MAJOR）⇒ 主控裁定：停止施工式打补丁，本批未闭部分升级为「窄设计轮」**（[裁决书 r3](logs/reviews/verdict/2026-07-27_judge_identity_metric_sol_r3.md)）：
    - **R3-B1 = 同一漏洞第三张脸**（sol 原话）：r3 的仲裁器**没有**实现死骨架的绝对规则，而是退化成 **reason 白名单** ⇒ 实际优先级变成「白名单内 identity > capability > **白名单外 identity**」。`exterior_duplicate_owner` 虽被收集为 `category="identity"` 却不在白名单 ⇒ **生产五项全绿的 duplicate-owner 真红，只要再加一条未配对 advisory 就被洗成 capability NA**（sol 活体：0.1×0.1 footprint + 两个满幅 cell + 一个 5e-10 斜边梯形，上游 overlap 0.015 m² < `coverage_area_tol_m2=0.05`）。
    - **R3-B2 = 主控点名的零容差风险坐实（预扫连续第三轮命中）**：`_assert_obs_conservation` 改零容差后，**三段严格相邻零缝零重叠的合法铺满**因浮点顺序累加比端点直差多 **1 ulp**（`excess=3.55e-15`）被判 `score_denominator_nonconserving` = **假红**。sol 关键论断：施工方只证明了**实数**几何不等式，没证明 binary64 逐位相等；且 `_SUBINTERVAL_SUM_TOL=1e-9`（target 层承认累加漂移）与 observation 层零容差**互不自洽**。**明令不得再在固定 `1e-9` 与零容差之间摆动**，须用结构性判据或有误差证明的判别。
    - **R3-M1 = 同一出口第三次打折**：M2 的替代锁各自为真（两条指定 neuter 确实各有锁红），但**只切断 `score_typed_attempt → host_resolver` 这一条生产接线，五条相关锁全绿** ⇒ 正式多-span 闭环仍未锁住。
    - **确认真进展**：R2-B1 指定四锁全通过 + 优先级反转 neuter 真红 + 未配对 advisory 已进可计数运行时日志（闭环）/ 大额真过计锁已走 `match_plan_segments` 真接线 / 排序反转经 AST 独立复算**零误伤**（退回旧序只有那 1 条红，其余 8 条 gap/overlap/dangling 夹具不受影响）/ **原失败测试函数体逐字节未改**（`sha256` 两提交相同，主控核实一致）/ **R2-B2 确认未半做**（无危险的来源身份半成品）。
    - **⇒ 主控战略裁定（本轮核心）**：**本批已连续三轮 REWORK，且 R2-B1→R3-B1 是同一漏洞第三张脸 ⇒ 停止施工式返工。** 病根 = **判卷器一直在用「症状分类白名单 + 数值阈值」打补丁，缺的是结构性判据**——这与 C-1 的教训**完全同构**（「任何全定义的离散化都有边界」⇒ 现在是「任何『哪些 reason 算真破裂』的白名单都会漏」；「精确硬拒 vs 固定容差」的二元摆动同理）。**并非基线错了，而是基线有两个未覆盖的缺口**：① **诊断仲裁**（R-4 只规定「判卷器只许说 unsupported」，未规定**真破裂与不可测同时存在时**谁定案）；② **计分守恒的数值判据**（R-2 只覆盖身份层三阈值，未覆盖守恒门）。⇒ 这两条**移交窄设计轮**（打法照本批立项：跨家族双独立出案 → 综合 → 对抗审），**派工待用户拍板**。
  - **⛔ sol 复审 r2 = 再判 REWORK（2 BLOCKER / 2 MAJOR），主控裁决 4 条全成立**（[裁决书 r2](logs/reviews/verdict/2026-07-27_judge_identity_metric_sol_r2.md)）：**R2-B1 = 本批第二次把假红改成假绿**——r2 为修 R-4 把 advisory 配对提到正交门之前 ⇒ **产品只要额外画一条 5e-10 斜边，就能让自己的 1e-9 真拓扑破洞整轮降级为 `score_unsupported_combination`（capability NA）不出分**（sol 在生产五项全绿的正式 `CorrectedGeometryV3` 上活体实证）。**该风险由主控预扫点名、sol 独立证实 ⇒ 预扫连续第二轮命中。** R2-B2 = **r1 §2 的来源身份死骨架两轮均未落地**（主控独立核实：`_build_floor_identity` 把点展平成 `(float(p[0]) for p in …)`、来源身份进聚类器前即丢光；`score_identity_contract_mismatch` 全仓**只在码表出现一次**、零 raise 零测试；合同④ 非相邻重复顶点/自触自交/同 owner 反向配对全部静默接受）。R2-M1 = 负 extra 仍留 1e-9 容差窗被静默吞（sol 实测 `covered=4.0000000005 / extra_rows=0`）。R2-M2 = N-1 只钉住 `:230→assign_openings`，**host resolver 恒 miss 时测试仍绿**（host claim 是假锁）且夹具仍单段。**同时确认真进展**：B-1 的 4 m 活体现响亮拒绝（摘拒绝门后第二防线也只给 `4 pass + 4 miss`）/ A8·overlong·GT 精确码三锁经独立 neuter 全真 / W5 两端确已接线（生产 8 红 + 判卷 24 红经 extraction）。
  - **主控范围裁定：R2-B2 移出本批、单独立项、派工待用户拍板**。理由 = ① 这不是补锁而是**跨层重构**（来源身份要穿透 GT/correction/reading 三种结构一路传进聚类器）；② **主控已给过一次死骨架、同档位连续两轮不达，且 r1 自查表未将其标 PARTIAL ⇒ 施工方误以为已完成**，原地重派不会有不同结果；③ 其余三项是当下真实风险（R2-B1 是活的假绿路径），不应被此重构阻塞。**明令施工方不得「顺手做一点」**（半成品的来源身份传递比没有更危险）。
  - **返工 r3（`b005004`·WIP 已标红）**：主控给死骨架 = **「收集诊断 → 按优先级裁决」取代「谁先跑谁定案」**（⚠️ **不许简单换回 tile-before-advisory** —— sol 已验证那样会报 `exterior_duplicate_owner`，即 r2 施工时撞的「第二张脸」；**两种顺序各有一种错 ⇒ 问题不在顺序、在结构**）；硬规则 = **identity/topology 类永远优先于 capability 类，只要存在任一 identity 诊断整轮必须以 identity 码红，绝不许被 NA 掩盖**。**施工方骨架已落地且方向正确**，但**在收尾处撞第二个 5h 窗口**（重置 2026-07-28 07:10 UTC+8）⇒ **全仓遗留 1 red**：`test_b4b_r1_gt_interior_pairing_and_invariant_raises` 期望 `exterior_interior_topology_conflict` 实得 `invalid_interior_edge_pair`。**主控诊断 = 仲裁器「同类内取最精确」排序未调好，两条均属 identity 类 ⇒ R2-B1 硬门未被违反、仍判红、非假绿**；处置 = 修仲裁器排序，**明令不许改测试迁就实现**。R2-M1 / R2-M2 本轮未开工。
  - **⏳ 返工 r1 实况（主控核实）= 主体已落工作树、全仓 1709 绿，但施工方在收尾处撞 429 ⇒ 未 commit / 未自验 / 未写执行日志**：GLM **严格照死骨架施工**（主控亲核：R-5 六个新分码落地并精确区分「identity merge 失败走中性新码」vs「pairing 失败仍走 side 码」以保住 A2 逐字码不变 / `diam` 按 §2.1 裁定改为 `= merge = 1e-12` / B-1 三步骨架全在：单向注册 + `score_identity_support_ambiguous` 拒绝 ≥2 + 守恒硬门 **raise 而非 clamp** + 负 extra 抛错不吞）。**主控轻门 = 独立全量 `1709 passed / 10 xfailed / 0 failed`**（基线 1706 +3）。**但全仓绿 ≠ 锁是真的**（上轮栽的正是此处）⇒ **仍缺 §4 要求的 neuter 自查表重做 + 执行日志**，**本批未完成**。主控代为 commit 保成果（`cc07997`），状态如实标注。
  - **⚠️ 运维教训**：一场深度施工 ≈ 烧穿一个 GLM 5h 窗口，主控在**同一窗口内连派施工 + 返工两场** ⇒ 返工在收尾处撞 429（重置 2026-07-28 02:04 UTC+8）。**用户拍板 = 等重置续作**（不换施工方，保上下文连续 + 零额外成本）。**下次派长批次前先估窗口余量。** **另一教训（主控自犯）**：撞 429 后主控只看 stdout 错误行就断言「返工一行没跑」并如此汇报，**实际工作树里已有 +217/+139 行返工**——headless 会话的进度要看**工作树**，不能只看 stdout。
  - 审轨：[派工单](logs/reviews/request/2026-07-27_judge_identity_metric_construction_dispatch.md) · [审阅单](logs/reviews/request/2026-07-27_judge_identity_metric_sol_review.md) · [sol 裁决书](logs/reviews/verdict/2026-07-27_judge_identity_metric_sol.md) · [返工单 r1](logs/reviews/request/2026-07-27_judge_identity_metric_rework_r1.md) · [执行日志](logs/reviews/execution/2026-07-27_judge_identity_metric_glm.md)。
  - 以下为本批**设计轮**记录（已过审，仍是施工唯一基线）：
  - **跑测配置（用户拍板）**=识图重跑 Haiku 4.5 + 预扫工具 / 全链含 EP / judge 拦停 + 只开几何人核 / regression + 录基线 / `orthogonal_polygon`。**开跑前置卡点（照 [new_case_guide §0.3](guides/new_case_guide.md) 查出）**= v3 case 判卷必须有 judge 侧车 `gt/<case>/score_inputs/view_bindings.json`，sm24 缺件、且 **v3 判卷层此前从未在任何真实 case 上跑过**（sm21 走 legacy）。主控核实五视图 `direction_semantics` 全 `building_axis` ⇒ 侧车**不依赖校正产物、可开跑前一次定稿**且 `provision_view_manifest` 逐字节可复现 ⇒ 侧车随答案包入库、每 run 复用；手性用**图纸自带尺寸链**独立核过四立面（北/西/东逐项吻合、两种 sign 都验到）。
  - **撞出的真缺陷**：平面判卷器假设「内墙两侧顶点完全对齐」，真实走廊布局（一条长墙对多个进深不等房间）**答案侧硬抛错 / 产品侧静默跳过（= 假红，且像识图模型的锅）**。sm21 是矩形网格故从未暴露 ⇒ **sm25-L/sm26/sm27 会同样撞死**。
  - **三轮施工/对抗审**（GLM 施工 · sol 审 · 主控轻门）：T 切分落地（真实 sm24 = **16 段内墙**，主控与 sol 两方独立复算一致）+ 产品侧假红消除（7/7 complete、0 unmatched）；但 **sol 连判两轮 REWORK**，每轮抓出**同一病根的新一张脸**——「上游校验器带容差放行、判卷器精确硬拒」⇒ 同一十进制几何的不同浮点写法被诬告成拓扑破洞（r1 两例 / r2 量子格边界 + 近正交外墙边）。**主控裁定：停止逐面打补丁，升级为设计问题。**
  - **设计轮（跨家族双独立出案 → 主控综合 → 第三家对抗审）**：[Claude 侧](proposals/judge_identity_and_metric_plan_opus.md)（Opus 子代理，772 行）+ [GPT 侧](proposals/judge_identity_and_metric_plan_sol.md)（sol，613 行）**互不可见独立成文** → 主控综合 = **[施工基线](proposals/judge_identity_and_metric_plan.md)** → **GLM 对抗审 APPROVE-WITH-CHANGES**（10 命题 9 成立、全部独立探针）。**两版独立收敛四条**：① 身份机制放弃定格量化（**任何全定义离散化都有边界 ⇒ 注定失败**，GLM 在 6 个量级各构造出跨格反例），改**单链接聚类 + 直径守卫 + 歧义显式拒绝**（部分函数：分不清就响亮拒绝）；② 分母由「邻接界面条数」改**长度（米）**（真实 sm24 实测界面口径下**每米权重最大/最小 3.96×** 失真，GLM 独立复算精确命中）；③ **联合切点原子化**取代一对一指派 ⇒ `score_match_ambiguous` 结构性不可达；④ **sm24 已签答案字节不动、签名有效、不重签不迁移**（GLM 独立核实晋升链不消费判卷器输出）。
  - **主控裁定**：R-1 取**护带**否决单点边界（单点是零测度、现实永不触发 ⇒ 漂移略超即静默分裂 = 假红换位复发）/ R-2 **阈值须实测推导 + 双向证明**，禁先定数字后补论证 / R-3 采 GPT 侧 **criterion 三分**（漏画·多画·重笔分开算账）/ R-4 采 Claude 侧框架：正交判据抽共享模块，**「合不合法」权威在生产、「量不量得了」权威在判卷且只许说 unsupported 不许说 broken**（三轮假红的结构性根源 = 判卷器拿自己的能力上限宣判上游几何非法）/ **C-1′ 身份池 = 文档内不跨文档**（GLM P10-① 点出两源稿此处**互斥**而综合稿原稿未落锤；联合池会让**答案分母成为产品输入的函数** = 尺子被被测物变形 ⇒ 新增硬锁「答案原子与分母是答案字节的纯函数」）/ C-1″ **输入合法性合同四条须运行时执行**，只聚类不执行 = 验收不通过。
  - **点名风险（Claude 侧独有发现，写进派工单）**：`score_service.py` 的 `product_to_gt` 同时服务墙计分与**窗宿主解析**，摘掉一对一指派后若图省事「取第一个」，**多段覆盖时窗会静默绑错墙且无任何测试变红**——GLM 逐条核实**既有窗夹具全是单段**，确为「门是真的、锁是缺的」。
  - ~~**⇒ 下一轮开工即派**：GLM 施工 / sol 对抗审 / 主控轻门~~ **已派并走完 r0 + 对抗审，见本条开头**。**sm24 端到端跑测仍排在该批过审之后**。
- **✅ 上一批（2026-07-26 Opus 5 主控·小批）= 根目录清零 + 测试夹具入库 CLOSED**（1671 绿不变·**0 skipped**·sol 审 APPROVE 零 finding）：**派工（用户拍板）**=GLM-5.2 施工 / GPT 侧 sol 升一档审 / 主控轻门。**起因**=用户发现根目录多出未授权的 `logs/`（15M）与 `output/` 并立**硬规矩「未经授权不许在仓库根目录落文档/新目录，过程痕迹一律 `AI_agent/logs/`」**。**实质问题**=根 `logs/experiments/` 是 **4 个测试文件的活输入却不在版本控制内**（`.gitignore` 的 `20*_*/` 吞掉一切日期目录）⇒ 新克隆上 skip 或红、**绿只绿在这台机器上** = 第三次同型「关键输入不在 git 里」。**交付**=`tests/fixtures/sm24_review/` 6 JSON（约 80KB）真入库〔`git check-ignore` 无输出、非 force-add；`source.dxf` 不搬——与已入库 `gt_sources/sm24_anchor/source.dxf` md5 相同〕+ 4 测试文件改指夹具（断言零改动）+ `_mirror_repo` 删冗余拷贝块（夹具随 `tests/` copytree 进镜像，25 格矩阵实证仍绿）+ 三处受保护根输入改「拷进 tmp 再喂」（§6.1 `assert_staging_input`·字节不变）+ `main.py` import 期不再建日志文件（原先每次 import 建一个多为零字节的文件、跑测试也触发；sink 挪进 `__main__` 指 gitignored `AI_agent/logs/runtime/app.log`）+ 根 `logs/`（15M 派生件，用户拍板直接删——**逐字节可重生成 + 签名证据已随转正入库**）与 `output/` 清零。**fail-closed 活体证明**=/tmp 副本改夹具名 ⇒ **29 failed + 50 errors + 0 skipped**（硬红非静默 skip）。**⚠️ 施工方停下上报、主控改派工单前提**：`.gitignore` 的 `output/` 行是**全局**规则（删后 16 个既有 e2e output 目录冒成未跟踪噪音）⇒ **裁定保留 + 加注释**（派工单前提有误·sol 独立复核属实）=「执行档发现派工单前提错时停下上报」的样板。**残留债**：`convert_idf`/`run_agent` 仍以 `output/` 为默认输出（显式跑会让根 `output/` 重现）/ `test_gt_overlay` 的 sm21 `skipif` 应改 assert（主控与 sol 独立认定同一"最脆"）。详 [plan.md](plan.md) 07-26 块。
- **✅ 同日（2026-07-26 Opus 5 主控·小批）= 测试提速 + 「受影响子集」映射表 CLOSED**（1656 → **1671 绿** + 10 xfail 零回归）：**派工（用户拍板）**=GPT 侧 terra 施工 / GLM-5.2 验证性对抗审 / 主控轻门。**成果**=①**全仓默认并行**（`addopts=["-n","auto","--dist","load"]` + `pytest-xdist`）⇒ **主控实测 18:54 → 4:21（4.4×）**，改造前后**节点集合逐字节相等**（串行 1 次 + 并行 2 次两两 `diff` 空、1679 行）；②三处并行不安全被修到**根因**而非遮盖（嵌套子 pytest 钉 `-n0` 防 25 格 × 16 worker 超订 / 真跑 EnergyPlus 的 E4 fixture 把 idf 拷进各自 tmp 目录〔EP 会在输入 idf 旁建 `in.idf`、两 worker 撞同一路径〕/ `test_mcp_stdio` 10s→120s 启动容差〔契约是 `returncode==0`+`stdout==""`，十秒是隐含机器速度假设〕）；③**受影响子集由工具算、禁自由裁量**（`affected_tests.py` = AST import 边 + 字符串路径边的传递闭包 + `SCOPE: FULL/SUBSET` + 跑测声明 + `--explain`；五条 fail-closed 全部活体验真；`uncovered_allowlist` 双向卡死）。**GLM 审=APPROVE-WITH-CHANGES**（19 命题 18 成立·命脉「并行≡串行」独立复算空 diff·七条承重机制零假锁·唯一 MAJOR=**施工方越界改本管理文档** ⇒ 主控收回主权、亲自复核并修正其中两处过乐观耗时数字）。**主控轻门 r1 抓 3 条**（**`--since` 锁是环境依赖弱锁**〔靠"工作树恰好脏"才承重，一 commit 即退化为永真断言〕/ 子集命令吐非测试 helper 且与全仓触发器口径矛盾 / 两处死码噪音）→ terra 返工 r2 全修 + 字符串边加方向约束（**禁经测试文件中转**，`cv_probe` 子集 87→3、`gt.py` 87→29）→ **主控轻门 r2 = 1671 绿零回归**。**⚠️ 实况登记**：`src/agent/**` 枢纽子集仍≈全仓（`pipeline.py` 85/93），根因 = `src/agent/__init__.py` 首行即 `from src.agent.graph import build_graph`（import 任何 `src.agent.*` 都拉进整张图）⇒ **改惰性 = 唯一杠杆、登记跟进债**（顺带压 import 开销）。详 [plan.md](plan.md) 07-26 提速批块。
- **✅ 上一里程碑（2026-07-26 Opus 5 主控）= GT 受控转正通道 CLOSED ⇒ 「sm24 标准答案签字转正落库」= sm24 收官**（1583 → **1656 绿** + 10 xfail 零回归）：**派工（用户拍板）**=GPT 侧 terra 施工 / GLM-5.2 验证性对抗审 / 主控轻门。**立项**=开工核查坐实昨日卡点（受保护答案根只有候选写入器且拒写、读取端只认 `human_verified`、全仓无转正代码），并新查出两条：用户 07-25 签收的**候选包整个不在版本控制内**（`.gitignore` 的 `20*_*/`）、**组装包与算清单指纹的代码只存在于未入库实验脚本**（＝07-25 治理教训在签名绑定根上的同型复发）。**主控范围裁定**=先做「可复现」再建通道——清 G6 近阈值的唯一路径是 G10 签名且**同一次运行内**生效 ⇒ 必然带签名重跑；而重跑每次写新时间戳/GUID 令答案指纹变、**签名当场失效**，两者互相否定，故可复现是地基不是后续债（同时裁掉三条替代路：另写一套清门判定＝第二把尺子 / 接受 BLOCKED 报告＝假绿 / 手工拼装 `gt.json`＝在最高信任资产上重犯治理教训）。**交付**=转换可复现（钉死值＝源图 hash+request hash 的纯函数）+ 候选包与 `review_index` 入库为生产代码（inventory 公式**冻结**）+ 签署 CLI（hash 一律磁盘现算、拒手工传入）+ 受控 `promote_gt_v3`（十门全绿 + **直调既有验签** + 语义不变式 + 原子写 + 写后重读自校）+ 三 CLI；落盘布局与 sm21 同构并新增 `review/`（签名证据同库入版本控制）。**主控轻门 r1=REWORK**：抓 **2 MAJOR**——**恒真假门**（`if data != canonical_gt_v3_bytes(promoted)` 同一纯函数比自己、分支永不可达、注释却声称防漂移）与 **false-lock**（`test_r4_3` 直调守卫不经生产路径 ⇒ **摘掉守卫调用后它与 R4-2 全绿**）+ 5 MINOR。**返工与交接**：terra 修完 MAJOR/MINOR 但**变异矩阵连推三轮**（与 07-23 同型）→ 主控 firm 卡 + **给死方案骨架**（源码行变异 + 镜像仓库 + 子进程 `-m "not mutation"` + 精确串命中恰 1 次 + **失败集合严格相等**）→ 预算耗尽**诚实交接不伪造** → 新 terra 会话接手落地 **25 格矩阵**并**自查出两处真洞**（R4-9 用例先被身份门拦截**从未到达** content-hash guard；ack 缺失原仅由底层 `read_bytes()` 兜底 ⇒ 补显式 guard）。**GLM 审=APPROVE-WITH-CHANGES**（命脉三条全成立·抽 8 格重跑 + 裸探针独立复算·独立全量与主控逐数字一致·只审不修自证）**唯一 MAJOR Y-06**：所谓「双向完整性」实为 declared ↔ 固定白名单、非 declared ↔ **目录实际文件** ⇒ 三处 rogue 文件双双放行（fail-safe，但「声称大于实况」）→ 主控裁定本轮窄修（目录级真双向 + 白名单**精确列举**且唯一目录豁免注明理由 + 三位置必红 + 矩阵加格；另补「**纯几何篡改**」正向证明）→ **主控轻门 r3 = 1656 绿零回归**。**⇒ 终点**：主控亲自跑通 `build → sign（reviewer hortonyyx）→ 带签名重跑十门全绿 PASS → promote`，**sm24 答案 + 7 图 + 5 份签名证据落 `case_tests/test_baseline/gt/sm24_anchor/`**；请签前出具**机械比对（排除三指纹字段后逐字段全等）+ 7 图逐像素 diff（差异仅限标题指纹横条）**，用户拍板「签，现在就转正」。**带签名重跑这一步同时活体证明了可复现地基**（否则清单校验当场拒绝）。详 [plan.md](plan.md) 07-26 块。
- **✅ 上一批（2026-07-25 Opus 5 主控）= 立面批「六笔债」CLOSED（GLM 审 APPROVE-WITH-CHANGES）**（`70dceb8`·1556→**1579 绿** + 10 xfail 零回归）：07-24 立面批过审时登记的六笔跟进债一次清——§6.5 converter↔GT 配对一致性 postcheck（死码接线 + 审计行与门共用同一 z 计算）/ §9.3 z 组七格必红 + §6.6 正向 e2e（**过程中修出真 bug：原只校验 `floor_datums[0]`、第二个 datum 是死输入**）/ 登记面清理 / GT 补 `wall_thickness_m`（证据绑定 + 无证据即 None）/ 出图达 sm21 级 / 重生成 sm24 review bundle。**§9.2 frame/title 六格诚实标未做**（下批按「先补门、再补锁」立项——其中至少两格是**缺门不是缺锁**）。**派工**（用户拍板）= 施工 Claude 侧执行档（GPT 侧额度用尽）/ 审 = GLM-5.2 照结构化清单验证性对抗审 / 主控轻门。**主控轻门抓回两条施工方与其自查表均未发现的缺陷**（交付图 z4 无标签＝人核门失效；审计表丢 `opening_id`/`plan_world_along_interval`/`host_zone_id` 三字段＝合同 §7.4 [S] 强制 backstop 失效）。**主控独立诊断「没对准」根因 = 07-24 平面校准控制点错（各向异性 1.92%＝等比截图物理不可能），与 GT 无关**；GT 对图纸自带尺寸链逐项精确吻合。修复后四立面 GT 框边命中图纸窗框线 ≤1.5px、平面 footprint 残差 0。**用户裁定**：地面线 = 室内地面 ±0.000（GT 不改）、门下沿 +0.2m = 正常门槛照图实记。详 [plan.md](plan.md) 07-25 块。
- **岔出一轮（2026-07-21→22 Opus 主控）= 天正→GT v3 转换器方案定稿 + 过审（无生产码改动·1456 绿不变·施工待下轮）**：sm24 收官需补 gt → **天正真实墙线喂不进 v3 提取器**（v3 要单线区划边界，天正画双线 + 门窗洞处断开）→ 用户拍板**走转换器、不改画图习惯**（否决手画区划线=违不变量 #6）→ **双独立出案**（Opus 子代理 851 行 + sol 701 行·跨家族互不可见·**Fable 5 退订故「双独立」预埋条款正式启用**）→ 主控综合裁「**腔体 + 逐边外扩**」主干（**不做双线配对**·绕开 sol 自认最脆环节 + 信息论不可识别）+ 并入 sol 7 条证据纪律 → **GLM-5.2 结构化清单对抗审**（把任务从其弱项探索性改造为强项验证性）= APPROVE-WITH-CHANGES·10 成立/0 不成立/1 无法判定·5 修订全落 → **C6 数字复现闭环**（Opus 未落盘脚本→GLM 判无法判定→落 17 探针→主控独立跑通逐项吻合·教训=探针数字须随稿落盘）。定稿 [proposals/tarch_to_gtv3_converter_plan.md](proposals/tarch_to_gtv3_converter_plan.md)。详 [decision_log §A](decision_log.md) 07-21→22 条。
- **施工岔出一轮（2026-07-22 Opus 主控·GLM 全程施工）= 天正→GT v3 转换器 P0–P2 已施工入库、但 sol 对抗审判 ⛔REWORK（3 BLOCKER + 8 MAJOR + 2 MINOR）**：P0 契约冻结（`edf1477`·1473 绿）+ §6.1 保护路径矛盾主控裁**方案 A**（不动双侧重保护·派生件归 `gt_sources/`·重建走 staging）+ P1 S0–S4（`d5e57e3`·洞口 21/21·1494 绿）+ P2 S5–S9（`a0c2a6c`·sm24 8 区/对称差 0/v3 复跑 PASS·1508 绿·S9 晋升 `gt_sources/sm24_anchor/`·**验证暴露并修上轮未验算法体 4 个阻断 bug**）。三批均过主控轻门（独立全量零回归 + 亲核 diff）+ GLM 自验。**⛔ 但 sol（gpt-5.6-sol max·GPT 侧·谁写谁不批）活体探针对抗审判 REWORK**（裁决书 [verdict](logs/reviews/verdict/2026-07-22_tarch_converter_p0p2_sol.md)）：**B-01 G8 主保险失效=假绿**（名义只读 zones、实际回放正向 S7 的 `offset_native`、不读 basis/thickness→逼近 `footprint−cavities` 恒等式·两反例 G7+G8 全过·GLM 必红夹具因同改 offset 而假锁）/**B-02 三承重门两道摆设**（近阈值仅 evidence·G10 candidate 即 passed·report status 不验全门）/**B-03 源图 hash 运行时零校验**（sha256 改 0 仍 PASS）+ 8 MAJOR（九门大面积 false-lock·neuter G1/2/3/4/7/8/9→35 测全绿仅 G6 真绑·S7 采样非精确事件求解·厚度没绑六类证据·17/39 码没接线·P0 契约冻结被 P1/P2 加字段破坏·写死 mm/单层/方向）。**治理数据点：主控轻门 + GLM 自验双双漏判、sol 活体探针独抓——升一档交叉对抗审价值再证、轻门非其替代**（主控轻门时已标"G8 强度待 sol 深究"·路由正确）。sol 亦验真正确项（测试基线/sm24 数字/S3 门排除/S9 hash/原句柄 384/384 保留/gt 隔离/4 bug 里 #1#3#4 修到根因）。**返工 9 条出口见裁决书 §6**（G8 从 basis+thickness 独立重算/三门真承重/接 hash gate/S7 事件坐标精确/真门级变异测试/接头矩阵/恢复 fail-closed/契约版本+去烤死/失败人核件）。**⇒ 转换器落地 + sm24 收官被此 REWORK 阻断；用户拍板=先收工、下轮开新会话专门规划返工（尤其 G8 重设计）再施工。** sm24 gt bundle 由已知有缺陷转换器产出、返工后需重生成、**当前不可信**。**✅ 该 REWORK 已于 2026-07-23 CLOSED（见下方「返工 CLOSED」条）——用户拍板不写单独返工稿、裁决书 §6 当返工单甩回施工方（对标 B2b/Va/B-M 常规返工），terra 施工 + sol 写审核单 + GLM 验证性对抗审 = APPROVE-WITH-CHANGES。**
- **✅ 返工 CLOSED（2026-07-23 Opus 主控）= 天正→GT v3 转换器过审、fail-closed（1508→1539 绿 + 10 xfail）**：**派工（用户拍板）**=terra（gpt-5.6-terra high）施工 / **sol 写结构化核验清单**（把 GLM 弱项〔探索性审阅〕改造为强项〔验证性审阅〕=60+ 命题每条写死「验什么/什么算不成立」）/ **GLM-5.2 照单验证性对抗审**（谁写谁不批：terra=GPT 侧、GLM=GLM 侧跨家族）/ 主控轻门。Claude 侧额度近顶⇒重活全在 GPT/GLM 侧、主控只写派工单 + 轻门。**terra 六轮**（`1a02fc6`→…→`cef0de9`）：核心一次落（G8 真独立 + 同墙一致性门 + hash gate + PASS 全门 + G10 hash-bound ack 机制 + S7 事件坐标 + 厚度绑证据 + fail-closed + 契约版本），但**九门 neuter 变异测试连推三轮**（命脉·上轮 7 门假锁死在这）→主控 firm 卡 + 给 seam 用法才落；场景 B / 五类接头矩阵续作补；**诚实披露不伪造 neuter 自查表**（对标 B4b Phase D 正面样板）。**主控轻门**=独立复跑全仓逐字对齐（1539/10/0）+ 亲核 G8/同墙门核心正确。**GLM 独立验真**（12 探针在 /tmp·零 terra fixture 导入）：**sol 原 3 BLOCKER 全修**——B-01 G8 trap〔挖空 offset_native/nx/ny→WKB 字节不变 sd=0、basis 翻转 sd=0.42 / 厚度变异 sd=0.21 变红〕/ B-02 近阈值进 G6 承重 + G10 三 hash 绑定 + PASS 强制十门 / B-03 hash 前置 BLOCK 全零不写几何；**九门 neuter 10×表零假锁**；转换器 **无任何假绿 PASS 路径**。**顺手关两 MAJOR**（`cef0de9`）：HC-03（`_outer_skin_gap_count` 过滤子句用 LINE 原始端点→反转 gap 计数翻转 = **假红**·M-07-B 未修到根·归一化 min/max 修 + 反转不变性测试）/ HC-02（`build_p1_report` `/1000`→mpu）。**残留 MINOR（全 fail-safe）登记跟进债**（见下一步条）。**治理数据点**：升一档交叉对抗审连续第十二批（本批 GLM 验证性）独立验真 3 BLOCKER + 抓 HC-03/HC-02；GLM 结构化清单打法再奏效（Fable 级验证性审阅）；terra 连推命脉三轮 = 中档执行档遇「验收纪律」类硬活需主控 firm 盯 + 给使能 seam。**⚠️ sm24 gt bundle 仍待真人签 G10 才能重生成 + 晋升**（见下一步条）。审轨 `logs/reviews/{request,execution,verdict}/2026-07-23_tarch_converter_rework_*`。
- **最新里程碑（2026-07-20 Opus 主控）= C2 体检修复批 CLOSED**（07-19 Fable 体检 4 MAJOR + 配套 7 finding 全落地；1434→1456 绿 + 9 xfail 零回归）：用户定「一把全上 + sol 最高档一把」，全升一档 = **sol 施工 + Fable 顶档对抗审 + 主控轻门**。①**施工**（sol，7 finding）：F1-1 orientation 再入守卫补 `correction_b5_orientation_v1`（`run_stage.py:452`·1 行 + 再入回归锁）/ F2-1 reading→correction·B5 消费经 accepted attempt 对账（新 `verify_reading_stage_root_against_accepted_attempt`，两处消费入口；有 accepted 时字节 hash 对账、无则 standalone 放行）/ F2-2 S5 mep 走 accepted + hash 校验 + `input_hashes` 补 `4_mep` / F5-1 footprint 一致门补两条负锁（schema 层 + envelope 纵深层，后者 monkeypatch 绕过 schema 抵事务层）/ F4-1 v3 判卷断链兜底（有 v3 GT 但缺 bindings → exploratory warn·golden/regression fail-closed，`run_profile` 全链程传导）+ new_case_guide §0.3 SOP / F1-2 capability_profile 进 run_config.yaml（present 覆盖 CLI）/ B4b MINOR-1 correction v3 判卷 e2e fixture（诚实披露暴露并补 assembler→scorer `window_host_proof` 接线）。②**Fable r1 REWORK**（生产码信任根本体零 bug、7 finding neuter 全过无 false-lock、零算法/golden/越界；2 出口 + 1 MINOR）：M1 = F2-1 缺 happy-path 正例锁（guard 重建 parity 与 `_draw_reading` 对位、非 BLOCKER，但缺正例回归锁）；**M2 = Fable P7x 活体探针新抓真崩溃点**——判卷循环 `_render_all_typed_attempt_grades` 遍历所有 attempt，非 accepted 的 v3 correction attempt 撞 scorer 六件套门 → `ScoreContractError` 全链无捕获 → flow 崩（sm25-L 照 SOP 跑必踩：首抽 block 重抽 / enrichment 后 base 变非 accepted）；m1 = cmd_run capability_profile 接线无锁。③**sol 返工 r1 三项 CLOSED**：M1 补真 `_draw_reading` + 真 `StageRunner.record` 非自指 parity 正例锁 / M2 `_grade_typed_attempt_artifacts` 对 `stage=="1_correction" and accepted_record is None` 静默早退（只 correction、reading 不受影响）+ 真 `_stepwise_e4_run` 形状回归锁（001 skip、002 出分）/ m1 cmd_run 孪生锁。④**Fable r2 APPROVE**（三锁 neuter 各精确命中无连带无 false-lock、M2 删早退即重现原崩溃、生产码逐字节对 r1 尾态）→ **主控轻门 = 独立全量 1456 绿 + 9 xfailed 零回归**（亲核三处返工 diff + 全批零 scorer/golden/judge/config 触碰）。**治理数据点（Opus 主控试点）**：升一档审**连续第十一批首轮抓 MAJOR**（M2 = sol+主控双漏的真崩溃路径、Fable 活体探针独立揪出）；主控预扫 diff 提前定位 M1 假绿风险（缺正例锁）与 Fable 独立复核吻合。运维注：codex MCP 撞 30min idle-timeout（rollout task_complete 可核）；Fable r2 连撞会话限额 + 连接断线两次、第三次 resume 成功。审轨 `logs/reviews/{request,execution,verdict}/2026-07-20_audit_remediation_*`。**⇒ 体检 4 MAJOR 必接项全清；下一步 = 素材入仓（sm25-L 图 → case_data + reading + gt，用户+主控一起做）→ 跑 sm25-L 端到端 = C2 收官。跟进债（登记 plan.md）**：F5-1 B2/B2b/B-M 老门负锁补扫 + §3.2 五漏记债 + F1-3 同名两型改名 + Fable n1/n2。**上一节点（2026-07-19 收尾轮·无代码改动）** = Fable 下架前三任务点射：C2 横向体检（[C2_AUDIT_REPORT.md](logs/experiments/2026-07-19_c2_landing_quality_audit/C2_AUDIT_REPORT.md)，本批修复来源）+ C2.1/C2.2 规划稿出稿存档（[c2_1](proposals/c2_1_facade_matching_plan.md)/[c2_2](proposals/c2_2_orientation_input_plan.md)·sol 对抗审后置）+ C3 竖向前瞻探索（[c3](proposals/c3_direction_exploration.md)）。
- **上一里程碑** = **C2 B6 词汇批 CLOSED**（0_reading 识图词汇：L/U 外轮廓 polyline + 翼分界 + 虚线四负例；**机械批**，2026-07-19 Opus 主控，1427→1434 绿 + 9 xfail 零回归）：**terra 施工**（`Stroke` 加可选 `line_style`/`visibility` 两字段〔image-local 非拓扑、hidden 观测不提升为实体 Window〕 + `reading_guide.md` 三处词汇〔外轮廓 polyline 复用现有 wall+polyline·凹角 reflex vertex 不抹平／翼分界仅显式标注才记不发明／虚线四负例口径含 uncaptured hidden_window_candidate〕 + 新测试文件 `test_reading_line_style_visibility.py` 7 测〔四负例各独立/schema 往返/legacy 无字段序列化不变/凹角 polyline 过 gate①〕，未碰 gate①·legacy adapter·golden）→ **Opus 子代理升一档审 APPROVE**（0 BLOCKER/MAJOR/MINOR·1 NIT 非出口〔uncaptured 路径未走故无 shipped-untested〕·3 假绿探针全证真绿〔visibility 默认篡改／dashed→solid 强转注入令 3 条红／删 `_GEOMETRY_KINDS` polyline 各令对应测试变红〕）→ **主控轻门=独立全量 1434 绿 + 9 xfailed 零回归**（亲核三处 diff 准确·零 golden·无越界〔未碰 correction/内核/装配消费·未跑 sm25-L〕）。**⇒ 到 07-19 用户定收尾路线的「跑测之前」**；下一步 = 素材入仓（sm25-L 图 → case_data + reading + gt，**用户 + 主控一起做**）→ 跑 sm25-L 端到端 = C2 收官。审轨 `logs/reviews/request/2026-07-19_b6_vocab_construction_dispatch.md`。**上一里程碑** = **C2 B5 Phase D CLOSED ⇒ B5 全系列（A–D）整个收官**（信任根/E4/legacy 封口；2026-07-19 Opus 主控，1360→1427 绿 + 9 xfail〔6 个 Phase C 延后 xfail 复原为真绿、15→9〕）：**全升一档** = sol 施工 → **诚实 PARTIAL**〔精确标 5 未竟、不藏假绿，对标 B4b Phase D 正面样板〕→ 主控退回续作〔5 项 + 裁唯一 review-ask=删 v3→B2 兼容后门，v3 必带 proof 即使零窗〕→ sol 续作 COMPLETE〔writer 十步独立重算/六件套 artifact contract（`correction_b5_v1`·`correction_b5_orientation_v1`）/accepted+integrated loader 全验/E4 rebind/audit-report rejected 扫描/legacy 三层锁/6 xfail 生产链复原/MINOR-1 伪 marker 收回/MINOR-2 pipeline C↔D proof 接线/NIT-3 共享 serializer/NIT-4 冻结字节 fixture〕→ **Fable 对抗审 r1 REWORK**〔0 BLOCKER/2 MAJOR/3 MINOR/2 NIT；**生产码信任根本体零 bug、全部活体验真**〔writer 双根独立 bomb 探针 + 三边界后门删除破坏即红 + legacy 字节层对改造前 HEAD 逐项相等 + 6 xfail 真生产链〕；2 MAJOR 均「门是真的、锁是缺的」——writer replay/totality 门 + E4 relation 守卫 neuter 后全绿=缺负锁、且简报声称的 replay 锁实际停在上一道 `writer_audit_output_drift`、从未触达 replay 门〕→ sol 返工 r1〔纯补 4 负锁 + MINOR-1/2 顺手、零生产码永久改动〕→ **Fable r2 APPROVE**〔三门 neuter 各只红对应新锁 2/1/1、无连带、无新洞、生产码逐字节对 r1 尾态〕→ **主控轻门=独立全量 1427 绿 + 9 xfailed 零回归**〔亲核 6 xfail 复原/伪 marker 清除/3 负锁 match 串绑门/GT·golden 零 diff/三门 raise 在位〕。**治理数据点（Opus 主控试点）**：升一档审**连续第十批首轮抓 MAJOR**（抓的是 false-lock=false-green 近亲）；主控轻门独立全量作唯一权威门。剩 **NIT-3**〔AST 扫描裸 `except:` 一行缺口·现实七文件零命中〕+ **MINOR-3**〔writer replay 对 manifest 覆盖 envelope readings 前提待首个真实 v3 run 验证〕= 非阻断跟进债。审轨 `logs/reviews/{request,execution,verdict}/2026-07-19_b5_phaseD_*`。**上一里程碑** = C2 B5 Phase C CLOSED（窗落墙线几何 + 四子系统同步，2026-07-18，1314→1360 绿；全升一档 sol+Fable r1 REWORK〔缺 17 锁〕→r2 APPROVE→主控轻门抓 6 out-of-scope 回归转 xfail 指向 Phase D）。**上上里程碑** = C2 B4b 全系列（A–D + REC-A–D）全收官 ⇒ C2 判卷子系统 elevation/fusion/policy/capability/run-stage/cache/renderer/CLI 全落地。**完整里程碑史（倒序、含每轮 commits / 审轨 / 产物指针）看 [decision_log.md §A](decision_log.md)；本节不再叠加历史。**
- **主控 / 协作现状**：主控 = **Opus 4.8**（整场不切模型）；**⚠️ 2026-07-21 用户告知：Fable 5 已退出订阅方案 ⇒ 彻底退场**（此前的三类点射安排作废）——**Claude 侧最高档位空缺，Opus 4.8 即 Claude 侧顶档**；**规划出稿即日起走「双独立」**（§5#8 预埋条款**正式启用**）= Opus 与 sol **跨家族**各出一版 → 综合 → **另一家族**新启对抗审。执行审升一档交叉、排工拍板制、谁写谁不批（详 §5 + [decision_log.md](decision_log.md) 07-16「主控降档拍板」条）。**⚠️ 2026-07-21 起四家族**（Claude / GPT / **GLM** / DeepSeek）：GLM-5.2 = 执行档主力、可坐次高档备用位但主要做复核不单独出稿（回溯测实证 = 验证性审阅 Fable 级 / 探索性审阅不及格）；GLM 在册主力仅 `glm-5.2` + `glm-5v-turbo`；DeepSeek 非订阅制⇒不作日常开发选项、只在用户指定时用（管线内角色不变）。详 §5#8/#10 + [实验记录](logs/experiments/2026-07-21_glm_capability_exam/README.md)。
- **已落地能力盘面**（详见 [decision_log.md §A](decision_log.md)）：0–5 校验架构 M0–M4 + 逐段 judge-in-the-loop 编排 + 离线 3D 几何查看器 + 自包含 baseline（anchor+gt）+ 单一 `flow` 编排 SOP + 判卷可视化统一模型（gt 逐元素对账）+ CV 工具箱（弱 VLM「量而非看」迁移性坐实）+ 污染硬隔离机制化 + 命名/外包确定性化 + report/ 策展汇报 + 双模型家族协作规约。C2 收官批陆续 CLOSED：B0 / B1（Cell.polygon）/ B2 / B2b / B3 / B-M（view_manifest）/ B-O（真北 Relative 出口契约）/ Vg（立面可见性）/ Va（opening 适用性）/ **B4a Phase A–D 收官**（GT schema v3 strict wire + DXF round-trip 提取 + 统一 render model/overlay v3）/ **B4b Phase A–B**（score identity/config/sidecar v8 + 段级 plan scorer〔segment/opening/Va 计分/精确 denominator〕）；strict v3 子类族 + floor footprint 单一权威 + 统一 finalize 已就位；GT-to-Va 计分侧 judge-only、Va 唯一 applicability 引擎。
- **下一步（2026-07-27 二轮收工时口径）**：① **「判卷数值身份 + 计分度量」批返工 r1**（基线 = [judge_identity_and_metric_plan.md](proposals/judge_identity_and_metric_plan.md)；**r0 已交付、sol 判 REWORK、返工单 r1 死骨架已写**〔[rework_r1](logs/reviews/request/2026-07-27_judge_identity_metric_rework_r1.md)〕；**GLM 额度 2026-07-28 02:04 UTC+8 重置后续作** → sol 复审 → 主控轻门）；② 过审后**跑 sm24 端到端**（run 目录 `run_2026-07-27_haiku_e2e/` + 配置 + 判卷侧车均已就位，从识图接着跑；顺带实测 07-07「E 效率批」并在 report 单出一节）；③ 之后素材入仓 sm25-L → 跑 sm25-L = **C2 收官**；④ **「gt 标准产物清单」批**（用户 07-27 拍板：以后每份 gt 产物对齐同一清单、缺件即红 + 补 provision bridge；含 R-6 = 判卷侧车与签名清单口径打架的收口）。以下为既有滚动计划：**✅ 天正→GT v3 转换器返工已 CLOSED（2026-07-23，见上方「返工 CLOSED」条）= GLM 对抗审 APPROVE-WITH-CHANGES**（3 BLOCKER 假绿主保险全修独立验真、转换器 fail-closed、1539 绿）。**✅✅ sm24 收官已达成（2026-07-26）= 标准答案签字转正落库 `case_tests/test_baseline/gt/sm24_anchor/`**（`human_verified`·reviewer `hortonyyx`·答案 + 7 人核图 + 5 份签名证据；经受控转正通道，见上方里程碑条）。**✅ 测试提速小批亦已 CLOSED（2026-07-26，见上方最新条）= 全仓 4.4× + 受影响子集工具化**——**⚠️ 下一站（2026-07-26 用户当场纠正排期）= 跑 sm24 端到端**（材料已齐：`case_data` 5 图 + **刚签字转正的 v3 答案** + 两次历史 run〔06-24 opus reading / 07-07 haiku cv probe〕；依据 = plan.md §N3「**转换器唯一真实验收标准即 sm24 端到端跑通，两事合一**」；**顺带实测 07-07「E 效率批」**〔预扫宏工具 + 预扫前置 SOP〕在真 case 上到底被用上没有、有没有用；**跑前必须停下问用户拍配置**〔识图模型/范围/judge 三档开关/EP/record〕并走 [new_case_guide](guides/new_case_guide.md) 单一 `flow` SOP）→ 之后 **素材入仓（sm25-L 图 → case_data + reading + gt，用户 + 主控一起做）→ 跑 sm25-L 端到端 = C2 收官**。**立面批已施工并过审**（07-24 施工 + 07-25「六笔债」CLOSED `28efe05`·GLM 0 BLOCKER/0 MAJOR），**残留 §9.2 frame/title 六格诚实标未做**（下批按「先补门、再补锁」立项，其中至少两格是**缺门不是缺锁**）。以下为该收官前的历史卡点记录（已闭）：转换器返工过审后跑 sm24→v3 提取暴露两缺口——① v3 提取「多房间共用外墙→窗无法归属」已 CLOSED（`2b7affad`·terra option b + Opus 子代理审 APPROVE + 1541 绿）；② **转换器根本没处理立面**（`elevation_views` 声明不用=又一 D8·sm24 DXF 有 4 命名立面 + E_WINDOW）⇒ 无窗高/立面/overlay、做不成 sm21 形态。**立面处理批**（用户拍板「设计细稿先行」）:sol 出设计细稿 [proposals/tarch_elevation_spec.md](proposals/tarch_elevation_spec.md) → Opus 子代理审细稿 **APPROVE-WITH-CHANGES**〔抓门 z 弱校验 + 对称立面镜像隐患 + 方向安全过度声称〕→ sol 累计并入全部修订 = **施工基线就绪·terra 施工待排（剩余最重一块）**。立面批产完整 gt（plan + 4 立面 + 窗高 + overlay）后 → **sm24 真人签字收官**（G10 三 hash 绑定·**逐窗 z + datum 端点映射进 review bundle 供人核**·需真人看 overlay 确认 8 区 + 四立面地面基准线正确；旧 bundle 由缺陷转换器产、不可信、待覆盖）。**z 基准 = 受信人工输入**（sm24 地面线无机读 ±0.000·窗高依赖「地面线=1F z=0」·机器定死 datum handle 绑 request、语义要用户 review 人眼核）。签字收官后 → 素材入仓（sm25-L 图 → case_data + reading + gt，用户 + 主控一起做）→ 跑 sm25-L 端到端 = C2 收官。**转换器返工残留 MINOR（全 fail-safe）登记跟进债**（登记 plan.md）：TE-01 六类证据仅 1/6 落地 / FC-03 多解无 solutions / FC-04 far-side 未检测 / H-03 重复 plan_view id 不查唯一 / HC-01 G4 `>1.0` native 阈值 / HC-04 多层静默 floors[0] / S7 junction 未证变厚静默归并（G7/G8 兜底无假绿）/ 自由端 §2.6 non_zoning 证明式处理 defer（自由端一律 S4 fail-closed BLOCK·MX-01 正例 xfail 待立项）。以下为既有滚动计划：① **✅ 07-20 体检修复批 CLOSED = 4 MAJOR + 配套 7 finding 全落地**（F1-1 再入守卫 / F4-1 判卷断链兜底+SOP / F5-1 两条负锁〔schema+envelope 层〕/ F2-1 reading accepted 绑定 / F2-2 mep accepted 绑定 / F1-2 capability_profile 进 run_config / B4b MINOR-1 correction v3 e2e fixture；Fable r1 REWORK〔新抓 M2 判卷循环崩溃〕→r2 APPROVE，1456 绿·详 §2 最新里程碑）→ **下一步 = 素材入仓**（sm25-L 图 → case_data + reading + gt，**用户 + 主控一起做**；图已出但仓库现 sm25 文件为 0、e2e anchor 仅 sm20/21/24、gt 仅 sm21）→ **跑 sm25-L 端到端 = C2 收官**（识图词汇已就位、B5 宿主解析已落、判卷子系统已就位、几何造面 B1/B2/B2b 已落）。**体检跟进债（登记 plan.md）**：F5-1 B2/B2b/B-M 老门负锁补扫 + §3.2 五漏记债 + F1-3 同名两型改名 + Fable n1/n2；**no_oversplit 永久 NA = 跑测判读纪律**（人工肉检 + 区数对账兜 L 形 oversplit，写进跑测单）。**B5b（归 C2.1，服务 sm26「不给全」子 case）不阻塞 sm25-L**。**⚠️C2 路线 2026-07-18 用户重切为「单轴爬坡」**：sm25-L=C2 收官（L 形非方形、四标准命名立面、无旋转/无匹配/无缺件）/ C2.1=立面匹配+缺件补（sm26-U 不转）/ C2.2=旋转+总图输入（sm26-rotate）/ sm27-回字型=整个 C2 总验收（详 plan.md 07-18 块）。② **B5 Phase D 跟进债**（非阻断，登记待后续批次）：NIT-3 = `test_source_scan...` AST 扫描的 `handler.type is not None` 条件使裸 `except:` 逃逸（一行修法 `handler.type is None or ...`；现实七信任链文件裸 except 零命中，下批顺手落）；MINOR-3 = writer replay 依赖「manifest 覆盖全部 envelope 相关 readings」的可用性前提，待首个真实 v3 case run 验证（若命中按细稿口径并入受信 marker、不得放松 replay）。③ **B4b Phase D 跟进债**（非阻断）：MINOR-1 = `score_typed_attempt(stage="correction")` correction v3 无独立 e2e fixture（休眠不触生产，correction v3 真接下游时补测）；MINOR-2 = typed grade renderer claim-box 简化，未做 §11.3 partial-interval hatch / §11.4 clip-conservation 细化（仅 grade 可视化，sidecar 权威分不受影响）。④ **standing gate**：sm21 批次重跑（reading-honest + judge 两轴 recoverability + auto re-read + 新命名攒齐一次性跑）→ 同时重录 sm20/sm21 golden（撤 9 个 xfail、strict→XPASS 会提醒）→ 结果不错则可合并 main。

---

## 3. 责任范围

**In-scope**：① `intake`/0–5 管线多模态理解（图+文本 → IntakeOutput）= 核心战场；② [llm.py](../src/agent/llm.py) provider 抽象 + 开源模型接入；③ skill 提示词演进（[`../skills/intake_pipeline/`](../skills/intake_pipeline) 0–5 阶段库）；④ 测试数据集 + baseline + 评测 + 逐段校验；⑤ 本地推理后端（vLLM/SGLang，等 Pivot 准入）。

**Out-of-scope**（协作者维护权 ≠ 本地无代码）：① 下游 9 subagent + cross_ref + validate + simulate 的 **prompt 演进**（本地有完整可跑代码，协作者负责 prompt + LangSmith 部署）；② MCP 工具基于 idfpy 的全线重写（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）；③ LangSmith 多步编排；④ RAG 知识库。

---

## 4. 关键洞察

1. **视觉理解非首要瓶颈**；真正瓶颈 = **长链路 tool-calling 稳定性 + 子系统覆盖完整性**（新流程靠 cross_ref + validate + 确定性门兜底）。
2. **强制约束别交给 LLM 记得** → 关键不变量一律确定性门强制（schedule 门 / interzone 门 / 内核 raise），不靠 prompt。
3. **EP 通过 ≠ 几何对**：几何正确性以 InterZone 门 + gate① 不变量为准；EP 段错≠环境（多为不完整 schedule 等可定位真因）。
4. **token 口径**：`/context` 真值才作准（deferred MCP / autocompact / system tools 不计入 Total）。

---

## 5. 协作者 / 助手约定

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
8. **双模型家族分工（硬默认：主控别自己开干；2026-07-10 GPT-5.6 轮修订；⚠️2026-07-12 用户重梳四档对位阶梯为唯一口径+同日补充；**⚠️2026-07-16 用户拍板主控降档=主控切 Opus 4.8、Fable 在场期降点射，四档对位与审阶梯不变**，详 [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md) §2：最高档 Fable↔sol/次高档 Opus↔sol/中档 Sonnet↔terra/低档 Haiku↔luna；**审一律高产出一档**=规划〔Fable 在场期恒 Fable 出·sol 对抗审〕/细稿次高档出·最高档 Fable/sol 交叉审/执行中档·执行审 Opus/sol 交叉+主控大节点；细稿不占 Fable、主控不亲手出稿；Fable 退场后规划=双独立出案→**新启**会话综合〔综合稿=综合方家族产物〕→另一家族**新启**对抗审,两边均不继承初稿上下文（**⚠️2026-07-21 Fable 退订 ⇒ 本条正式启用**，最高档位 Claude 侧空缺、Opus 即顶档）；**排工拍板制：每次排工先出派工表交用户拍板再派,中途返工续循环免重拍**）**（操作手册 [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md)）：**主控 = Claude 家族开对话模型**（**2026-07-16 用户拍板起 = Opus 4.8**，开会话即 Opus、整场不切模型〔同会话中途切模型=已写缓存全作废〕；**Fable 5 在场期降为三类点射**：①规划/方案出稿〔子代理或独立短会话+精简 brief〕②工程细稿最高档交叉审〔不变〕③大节点复核/疑难会诊。动因=Fable 主控烧 5h 窗太快+撞 Fable 单独限额；缓存按「模型+前缀」隔离且 TTL≤1h、跨窗本就冷启→切主控无缓存税，Opus 单价≈Fable 一半→单窗可开发量↑），亲手只做：① 方案/规划 ② 审 diff/裁决 ③ judge ④ memory + 管理文档（`AI_agent/`）纯文字编辑 ⑤ `git add`/`commit`（唯一小例外：trivial 单点改且方案言明、或纯文档/计划编辑）。**凡实质改动（`src/`/`skills/`/`tests/`/MCP/下游）一律走角色矩阵**：方案（规划/方向档 = ~~Fable 在场期仍 Fable 出稿~~**Fable 2026-07-21 退订、条款失效**；**现行 = Opus 与 sol 跨家族双独立出案 → 综合 → 另一家族新启对抗审**〔07-21 正式启用；综合方按轮拍，可由主控综合，此时对抗审派非 Claude 家族〕）→ **交叉最顶对抗审**（Claude 侧产物→sol；GPT 侧产物→Fable/Opus；effort = 最高两档 max/ultra 主控择一）→ 主控裁决（不盲从）→ **派执行档实现**（Sonnet 5 子代理 / terra；批量机械活 Haiku/luna；简报含「审阅需求」）→ routine 采信、**大节点交叉中档复核**（Claude 侧执行→terra；GPT 侧执行→Opus）+ 主控全面审。**谁写谁不批**（跨厂商交叉是必须）；推理强度不写死、主控按任务定；**额度侧动态定**：派批次活前看两边窗口、问用户拍（规划/方向与方案评审保质量不受额度约束）；复核简报纪律 = 批准者只看原始需求+diff+测试输出，不看执行者长篇自述。独立审计/交叉核实同样交叉派发，主控只设 brief、不与之并行自查以保独立性。**⚠️ 2026-06-27 教训**：已「出方案 + 用户 ratify」后，Claude 仍自己把 reading 修法 7 个文件全改了、只把 Codex 当事后审稿 → 违反分工、已全部回滚重做。**「出了方案 ≠ 可以自己执行」**。**⚠️ 2026-07-11 第三犯，用户令强化**：B-M 首轮施工规矩派了 Sonnet，但交叉复核后的**两轮返工主控又亲手改码**（Fable 额度烧穿、中途被迫切号）→ 硬化条款：**返工轮 / 复核 findings 修复 / 探针·实验执行同属实质改动，一律派执行档**；主控「大节点全面审」= 审 diff + 自跑测试，**不含亲手修**；察觉自己在编辑 `src`/`tests`/`skills` 即违规信号——停手改派。额度侧属哪家按轮动态拍（例：2026-07-11 用户拍 GPT 侧频繁重置期间**施工优先派 terra、终审翻 Claude 侧**，谁写谁不批方向随之反转）。
   **⚠️ 2026-07-21 用户拍板：GLM 家族接入 ⇒ 四家族**（Claude / GPT / **GLM** / DeepSeek）。
   - **GLM-5.2 = 执行档（施工）主力**；**可坐次高档备用位，但主要做复核类工作、一般不单独出稿**。
     依据 = 回溯测实测能力画像（[logs/experiments/2026-07-21_glm_capability_exam/](logs/experiments/2026-07-21_glm_capability_exam/README.md)）：**验证性审阅**（给定 finding 清单、验锁真绑/防 false-lock）达 **Fable 级**（7/7 锁全 neuter、零漏判零误报、操作纪律满分）；**探索性审阅**（无线索处找未知缺陷）**不及格**（漏掉 Fable 当初靠活体探针抓的必崩缺陷、误判 APPROVE）。
     ⇒ **适合接「返工轮复核」**（验证施工者补的锁是否真绑目标门，如 Fable r2 那类任务），为最高档腾额度专攻首轮对抗审；**不得**替代首轮对抗审与规划出稿。
   - **派工表必须把 GLM 算进候选**（与 Claude/GPT 侧同列）；**仍是用户拍板再放**（排工拍板制不变）。
   - **运维**：一场深度对抗审 ≈ 烧穿一个 5 小时订阅窗口；高峰 14:00–18:00 (UTC+8) 额度 **3x** 扣、非高峰 2x（促销期至 2026-09 降 1x）⇒ **长批次避开下午**。席位启动器 [`scripts/glm_code.sh`](../scripts/glm_code.sh)（凭据只注入子进程；**全局 `ANTHROPIC_BASE_URL` 会静默劫持主控会话**）。
   - **在册主力仅两个（2026-07-21 用户定）**：**`glm-5.2`（文本）+ `glm-5v-turbo`（多模态，200K）**；其余（`glm-5-turbo` / `glm-4.7` / `glm-4.5-air` / `glm-4.6v` / `glm-4.6v-flash`）**不专门指定即不用**——`glm_code.sh` 的 small/fast 槽位因此也默认 `glm-5.2`（省额度需 `GLM_SMALL_MODEL=glm-4.5-air` 当轮显式覆盖）。
   - **多模态仅 V 系**，主力 `glm-5.2` 是纯文本看不了图；识图实验臂唯一候选 = `glm-5v-turbo`（`glm-4.6v` 因把图纸毫米标注当像素坐标出局，且已不在册）。
9. **开发环境统一 VS Code Dev Container**（[../.devcontainer/README.md](../.devcontainer/README.md)）：容器内 EnergyPlus 25.1.0；git 是唯一同步通道，禁文件同步工具同步本目录；`.devcontainer/`(bind mount, VS Code) vs `docker/`(COPY 代码, MCP server 发布) 别混。
10. **DeepSeek**：v4-pro thinking 默认关（langchain_openai 不回传 reasoning_content 多轮 tool-call 必 400）；管线内 correction 模型角色不变；原 `deepseek-bridge` MCP 承接的省额度小活（简单文本任务）现优先派 luna/Haiku 轻档（§5#8 矩阵），bridge 保留备选；架构/编辑/集成仍主模型负责。
    **⚠️ 2026-07-21 用户定**：DeepSeek **非订阅制（按量计费）** ⇒ **不作日常开发选项**，项目开发里**只在用户专门指定时才用**；**管线内角色不受此限**（1_correction / 4_mep / 下游 9 subagent 照旧，有 baseline 沉淀、不轻动）。
11. **idfpy 替换 + token 优化搁置**（[deferred/](deferred)）：等协作者侧 MCP 重写交付。
12. **收工 ritual（每轮结束硬规范，2026-06-27 用户定）**：「收工」必须做完两件事——① **更新管理文档**（当前状态→本文§2 / 待办与进展→[plan.md](plan.md) / 里程碑历史→[decision_log.md](decision_log.md) / 架构变更→[contracts](architecture/pipeline_stage_contracts.md)；并遵 memory↔文档同步铁律 §5#1）；② **git 处理 = `commit` 本轮全部改动 + `push` 当前分支**。**收工本身即对 push 的标准授权**（覆盖 §5#7 的"平时不 push"）；force push 仍禁。没做完这两件不算收工。
14. **Comate 内网模型网关 = 「路线 3·人工中继」备用通道（2026-07-27 用户拍板登记，需要时才用）**：用户在公司 Comate 有近乎全量头部模型的调用权（**含 Fable 5** ⇒ 2026-07-21 起空缺的 Claude 侧最高档审阅位有回补可能）。
    - **接入实况（主控只读诊断）**：网关 = OneAPI 风格（`X-Oneapi-Request-Id` + APISIX），候选 base URL `https://oneapi-comate.baidu-int.com/v1`，四个路由（`/v1/models`·`/chat/completions`·`/messages`·`/responses`）在无 token 时均返回 OneAPI 统一鉴权错误 ⇒ **路由存在但协议实现未证**（尤其 `/v1/messages` 的多轮 `tool_use`/`tool_result` 往返）。**⛔ 当前 dev container 连不上该内网域名**（TLS 0.04s 即断；同环境 GitHub 200 / 智谱 401 正常 ⇒ 出网无碍，是内网可达性问题）。**⚠️ 诊断纪律**：本沙箱把**任何**域名（含不存在的）解析到递增假地址且都「连得上」⇒ **DNS/TCP 连通性测试在此环境下全是假阳性**，只能用「不带凭证的真实 HTTP 请求」判可达。
    - **数据流向（用户已知悉并接受用于非代码用途）**：多厂商网关**必须解密**才能路由与计费 ⇒ **公司网关是链路的一端、不是管道**，明文提示词对其可见且绑定工号；**agent 用法会把整个代码库增量上传**。公司政策鼓励用模型开发（合规无碍），但**课题组数据不出组**是另一层约束 ⇒ 未确认留存政策前**不走施工**。待确认三项：请求体是否落盘 / 留存期与查看权 / 是否二次用途。
    - **⇒ 当前口径 = 路线 3（人工中继）**：**只做不碰代码的活**（规划出稿、方案/细稿评审、算法思路、通用工程问题），由主控出**脱敏 prompt**（不含项目源码/文件树）→ 用户在 Comate 侧跑 → 结果贴回。**不接为 worker 席位**（施工仍走 Claude/GPT/GLM 现有席位）。技术路径若要升级为真席位，第一道坎是**网络可达**、第二道才是协议（多轮工具调用），详 [plan.md](plan.md) 07-27 条。
13. **用户拍板必须白话（2026-07-10 用户定，硬规矩）**：凡需用户拍板的技术决策，呈现时**禁用代码变量名/内部代号/批次号当主语**（用户没有代码上下文，"E4/B-O/north_axis"这类词无意义）——必须用大白话讲清：① 背景（我们在干什么）② 问题（撞上了什么）③ 每个选项的**后果**（选了会发生什么、代价是什么）④ 推荐+理由。技术细节/代号放链接或括号供查，不作叙述主体。判卷/审阅产物里的技术版照旧，白话义务只在**面向用户的拍板请求**这一层。

---

## 6. 文档索引

| 文档 | 作用 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 本文 — 项目结构 + 当前状态 + 约定 + 索引（根文件）|
| [plan.md](plan.md) | **活计划**：近细远粗的决策与待办（动态调整）|
| [decision_log.md](decision_log.md) | **历史决策唯一归档**：里程碑时间线 + §5.1–5.13 决策详档 + 变更日志 |
| [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) | **唯一「当前稳定架构」文档**（活）：逐阶段 输入·输出·校验 + 两道门 + 规范不变量 + 接缝缺口 |
| [architecture/judge_grade_model.md](architecture/judge_grade_model.md) | **判卷子系统活规格**（gate② grade：reading+correction·平面+立面·三档色·容差带；§8b 开放 backlog=墙粒度/立面窗移位vs变尺寸/Hungarian/ambiguous/非方形）|
| [guides/new_case_guide.md](guides/new_case_guide.md) | **主 Agent（编排器+judge②）操作手册**：换主控模型读此接手 |
| [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md) | **Claude 编排 / Codex 执行**协作规约：分工 + 省上下文机制 + 通道/沙箱校准 + 审阅反转 + 兜底纪律 |
| [capability/](capability) | **识图→建模能力主线**：`recognition_modeling_capability.md`(质量主线) · `reading_improvement_methodology.md`(**reading 提升唯一管理文档**：诊断+Phase A/B/C+CV 工具箱方法论+决策) · `floorplan_redraw_strategy.md`(两步法策略/POC 史) · `pipeline_0-5_capability_upgrade_suggestions.md`(C2/C3/C4 复杂度升级) |
| [proposals/](proposals) | **未落地的设想 / deferred 设计**（一旦动工搬进 capability，不两处并存）：`geometry_first_zonification.md`(再拓扑支线,休眠) · `editable_geometry_confirmation.md`(可编辑几何确认,DEFERRED) · `cad_to_gt_extraction_plan.md`(CAD→gt,设计待审) · `role_binding_phase2.md`(role 确定性绑定 phase-2,DEFERRED·2026-07-05 抽出) · `j23_geometry_judge.md`(J23 几何 judge,P2 DEFERRED·2026-07-05 抽出) |
| [reference/](reference) | 稳定参考：`pivot_criteria.md` · `open_model_guide.md` · `drawing_to_model_research_landscape.md` · `split_pairing_kernel_reference.md` · `InterZone_Surface_Matching_TechNote.md` |
| [deferred/](deferred) | 搁置（等外部依赖）：`idfpy_embed.md` · `token_optimization.md` |
| [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) | **活文档**：本项目侧对下游 subagent 代码的 hotfix 记录（备份在 `backup/src_history/`）|
| [logs/](logs) | **过程痕迹**（非活文档；纪律见 [logs/README.md](logs/README.md)）：`reviews/`=交叉审阅（`request/` ask + `verdict/` Codex 裁决 + `execution/` 执行日志，见 §5#8）· `experiments/`=独立测试/审计/A-B/诊断 · `renders/`=gitignored 图 |
| [archive/](archive) | 历史归档（已被取代/已实现/已 close）：`architecture.md` · `pipeline_validation_build_plan.md` · `rules_md_split_map.md` · `twostep_architecture_diagram.md` · `2026-06-09_..._refactor_handoff.md` |
| [../case_tests/test_baseline/](../case_tests/test_baseline) | baseline 方案 [README.md](../case_tests/test_baseline/README.md) + 注册表 [index.md](../case_tests/test_baseline/index.md) + gt [gt/README.md](../case_tests/test_baseline/gt/README.md) |
| [../skills/intake_pipeline/](../skills/intake_pipeline) | 0–5 阶段 skill 演进源（唯一 skill 库）|
| [../.devcontainer/README.md](../.devcontainer/README.md) | 多端开发环境指南 |
