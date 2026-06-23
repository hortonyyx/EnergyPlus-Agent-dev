# 多模态输入 Agent 项目管理文档

> **本文件 = 项目最基础的根文件**，每次会话/换主控模型时首加载，作用是**简要说明项目结构 + 当前开发状态**。
> 只放长期稳定的"是什么"和此刻的"在哪"；**待办看 [plan.md](plan.md)，历史决策看 [decision_log.md](decision_log.md)，
> 当前架构细节看 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)，标准工作流看 [guides/new_case_guide.md](guides/new_case_guide.md)。**
> 三者职责互斥：本文不叠历史、不堆待办。

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
| [../scripts/](../scripts) | 总启动 `run_full_pipeline.py`（`--reading-from`/`--intake-from`）；`tool_scripts/`=render×N + `run_stage.py` + `record_baseline.py` + `render_geometry_viewer.py` + `render_gt.py` + `gt_from_dxf.py` + `inspect_dxf.py` |
| [../tests/](../tests) | pytest **277 绿**（kernel/checks/judge/orchestrator/gt/interzone/schedule/viewer…）|
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

---

## 2. 当前开发状态

- **分支** `6.15_ValidationArchM0toM4`；测试 **328 绿**；最新里程碑 `6.23_RunDirTidySingleReport`（2026-06-23）。
- **已落地**（详见 [decision_log.md §A](decision_log.md)）：0–5 校验架构 M0–M4 + 逐段 judge-in-the-loop 编排 + 离线 3D 几何查看器 + 新 baseline 方案（自包含 anchor + gt）+ sm20/sm21 两份 golden baseline + sm21 双模型轮（GPT-5.4 识图 clean / judge-in-the-loop 验证）+ CAD→gt 工具链 + 管理文档重构 + **Claude 编排/Codex 执行协作规约**（[guides/codex_execution_protocol.md](guides/codex_execution_protocol.md)，审阅方向反转 + 本机沙箱校准）+ **P0#1 跨层概念墙对齐**（`deterministic.py` 加 `_reconcile_cross_floor`：per-floor identity → footprint 硬锚 → mutual-nearest 跨层匹配 + 歧义 flag → provenance-aware sliver；sm21 112→100 面、走廊跨层对齐、双审+四重验证）+ **reading 诚实机制 + judge recoverability 路由**（修 sm21 Sonnet 识图：`Stroke` 加可选 provenance/confidence/dimension_refs + 落地承诺已久的 stroke↔dimchain 一致性 CROSS_CHECK（非阻塞）+ judge 加第二轴 `recoverability`（`blocking` 改 J0-scoped、四条放行判据+默认中止）+ guide/pen/judge prose（双通道纪律/门≠窗/provenance→A0 映射）；**correction A1-A4+核 不动、不需重录 baseline**；架构总纲 D1-D5 = correction 永 image-blind 纯文本**不做 VLM** / 脚手架=降智机制（服务国产 VLM→本地开源北极星）/ 看图仲裁归 judge+重读 / who-fixes=证据冗余在+不靠猜才放行，用户全程 ratify）+ **同源欠债三件套收齐（2026-06-22）**：PR-A audit→评测归因（`0c625fe`，record_baseline 读 corrections.json → `baseline.json.corrections_summary` + report/FACTS.md 校正审计节）+ PR-B 0_reading auto re-read（`600d30e`，**子代理即 runner**：主控冷启隔离子代理盲重读、`AWAITING_REREAD` 非终止、`reading_runner_available` 默认 False 向后兼容、root 段算预算、`resample --force` 交接）——让错「可见→可归因→可重读恢复」，correction 不动、不需重录 baseline、测试→307。+ **主控汇报优化（report/ 策展文件夹，2026-06-23，五审闭环）**：每 run 产**单一 `report/`**（你只看这里）= `FACTS.md`(确定性事实卡) + `REPORT.md`(主控+judge 动态撰写、含**四桶建议**机制/能力/脚手架/修法) + `eyeball/`(显式 collector 汇 2D 肉检图，3D viewer 留 manual_review 指针)；事实层(代码)/叙事层(主控)分离、`REPORT.md` create-if-absent 防覆写；新增 **evidence_index**(坐标式稳定 id 派给 gate/judge/correction/stop/ep/geom/eyeball + dup-id 断言) + **citation linter**(建议必挂 `[E:..]` 证据、纯词法) + **run_state**(复用 TERMINAL_STOP/ADVANCE_OK + PENDING + 几何 supersede，状态感知报告不发死链)；RUN_REPORT.md→report/ 原子迁移；新 `report_assembly.py`、测试→320。审计轨迹 logs/review/2026-06-22_run_report_organization_{proposal,review} + 2026-06-23_report_org_execution_log。**续：run 目录收拾 + 单一 REPORT.md（2026-06-23 `6.23_RunDirTidySingleReport`）**：5 个机器记账件（orchestration_state/baseline/run_manifest/validation_manifest/geometry_approval）迁 **`<run>/_run/`**（经新 `run_meta_path` helper 统一路由，llm.yaml 留根）；**FACTS.md 并入单一 `report/REPORT.md`**（模型配置置顶 + GEN 生成区[事实卡/run_state/eyeball 索引/evidence_index] + AGENT 撰写区[conclusion/focus/diagnosis/recommendations]，**marker 围栏合并**：GEN 每跑刷新、AGENT 跨跑保留、畸形 marker fail-before-write）；citation linter 改吃抽出的 AGENT 建议区；所有测试触及 run 迁 `_run/` 单契约；根目录=纯文件夹+llm.yaml、用户只开 REPORT.md，测试→328。审计轨迹 logs/review/2026-06-23_rundir_tidy_{proposal,review,execution_log}。**已知 wart**：2 个 legacy golden（sm20/run_2026-06-15、sm21/run_2026-06-16_opus）无编排账本→run_state=incomplete（未编造，待批次重录自愈）。
- **下一步**（plan.md N1b）：① **命名确定性化**（楼层-类型-方位-序号，blast radius 宽、需 baseline 重录）；② role **phase-2**（确定性绑定 sidecar + gate① provenance + plan→world 变换产物，远期）；③ **sm21 重跑验证（明天）** reading-honest + judge 两轴 recoverability + auto re-read 三件套（与①等待改项**攒齐一次性跑**，用户定）→ **结果不错则可合并 main**（当前在 `6.15_ValidationArchM0toM4` 分支、未 push）。（N2 South 2F 窗 x **已关闭**；role **phase-1**、viewer 挪 manual_review、**Sonnet 识图变差诊断 + 机制修**〔reading 诚实 provenance + judge 两轴 recoverability〕、**主控汇报优化〔report/ 策展文件夹〕已落地**。）完整滚动计划见 [plan.md](plan.md)。

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

1. **memory ↔ 管理文档同步（硬纪律）**：助手 memory 是 Claude 本地的，换主控模型即丢。**凡进 memory 的项目级事实/决策/反馈，必须同步落进管理文档**（当前状态→本文§2 / 待办→plan.md / 历史→decision_log.md / 架构→pipeline_stage_contracts.md）。memory 只作 Claude 的个人索引，不作唯一存储。
2. **模型切换入口唯一**：[llm.yaml](../src/configs/llm.yaml) + [llm.py](../src/agent/llm.py)，不在节点内硬编码；per-case 改 `<case>/llm.yaml`。
3. **多模态改动只改 intake/0_reading**，不绕过把图像塞下游。
4. **改 skill/src/MCP/下游 subagent 先备份**：`cp` 到 `backup/{Skill,src,MCP,scripts}_history/<YYYY-MM-DD>_<reason>/`；动下游代码并在 [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 记一条（活文档，管理方式不变）。
5. **本项目交接产物 = IntakeOutput JSON**；下游走 [run_full_pipeline.py](../scripts/run_full_pipeline.py) 自动跑产 IDF + 仿真；规则库 [`../skills/intake_pipeline/`](../skills/intake_pipeline) 按阶段运行时加载。**skill 库 = 英文纯当前版本 spec**：文件内不写时间戳/版本号/changelog/缘起 case（决策史归 decision_log + git）；0–5 阶段布局；旧 `energyplus_mcp` 单步库已退役。
6. **回归门槛**：切默认 provider 前端到端跑通率 ≥ Anthropic 基线 80%（[reference/pivot_criteria.md](reference/pivot_criteria.md)）。
7. **git 权限下放**：助手可在里程碑自行 `git add`+`commit`（message 仿 `<月.日>_<英文标签>`，body 含①改动②为何此刻③影响）。**禁** push（除非明确要求）/ force push / `reset --hard` / 跳 hook / 动 `git config`。
8. **Claude 编排 / Codex 执行**（操作手册 [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md)）：Claude 主控（方案+审 diff+judge+memory/文档+commit），执行尽量派 Codex（省 Claude 上下文、推理算 Codex 额度）。**审阅方向**：Claude 出方案 → Codex 审方案（`mcp__codex__codex`，落 `logs/review/`）→ Claude 裁决（不盲从）→ 派 Codex 执行器（简报含「审阅需求」自报需复核处）→ Claude **按 review-ask 复核、不逐次全审**（把 Codex 当可靠工具），**大节点才全面审**（自跑 pytest + 逐行 diff + 端到端回归）。方案类决策**双审**后再派。**本机硬坑**：Codex MCP 碰本地文件必须 `sandbox=danger-full-access`（read-only/workspace-write 起 bwrap 失败→静默回退读 GitHub @main）；sandbox 建 thread 时定死，换权限须新开会话；看图走 CLI `codex exec -i`（MCP 无图参数）；**effort 按角色分档（2026-06-23）**：方案审阅 `xhigh`，执行 `medium`/`high` 由主控按复杂度定、默认不再 xhigh（per-call `config={"model_reasoning_effort":..}` 覆盖 config.toml 的 xhigh 默认）。
9. **开发环境统一 VS Code Dev Container**（[../.devcontainer/README.md](../.devcontainer/README.md)）：容器内 EnergyPlus 25.1.0；git 是唯一同步通道，禁文件同步工具同步本目录；`.devcontainer/`(bind mount, VS Code) vs `docker/`(COPY 代码, MCP server 发布) 别混。
10. **DeepSeek**：v4-pro thinking 默认关（langchain_openai 不回传 reasoning_content 多轮 tool-call 必 400）；`deepseek-bridge` MCP 可调时派简单文本任务省额度，架构/编辑/集成仍主模型负责。
11. **idfpy 替换 + token 优化搁置**（[deferred/](deferred)）：等协作者侧 MCP 重写交付。

---

## 6. 文档索引

| 文档 | 作用 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 本文 — 项目结构 + 当前状态 + 约定 + 索引（根文件）|
| [plan.md](plan.md) | **活计划**：近细远粗的决策与待办（动态调整）|
| [decision_log.md](decision_log.md) | **历史决策唯一归档**：里程碑时间线 + §5.1–5.13 决策详档 + 变更日志 |
| [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) | **唯一「当前稳定架构」文档**（活）：逐阶段 输入·输出·校验 + 两道门 + 规范不变量 + 接缝缺口 |
| [guides/new_case_guide.md](guides/new_case_guide.md) | **主 Agent（编排器+judge②）操作手册**：换主控模型读此接手 |
| [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md) | **Claude 编排 / Codex 执行**协作规约：分工 + 省上下文机制 + 通道/沙箱校准 + 审阅反转 + 兜底纪律 |
| [capability/](capability) | **识图→建模能力主线**：`recognition_modeling_capability.md`(质量主线) · `floorplan_redraw_strategy.md`(两步法策略/POC 史) · `pipeline_0-5_capability_upgrade_suggestions.md`(C2/C3/C4 复杂度升级) |
| [proposals/](proposals) | **未落地的方案/讨论**：`geometry_first_zonification.md`(再拓扑支线,休眠) · `editable_geometry_confirmation.md`(可编辑几何确认,DEFERRED) · `cad_to_gt_extraction_plan.md`(CAD→gt,设计待审) |
| [reference/](reference) | 稳定参考：`pivot_criteria.md` · `open_model_guide.md` · `drawing_to_model_research_landscape.md` · `split_pairing_kernel_reference.md` · `InterZone_Surface_Matching_TechNote.md` |
| [deferred/](deferred) | 搁置（等外部依赖）：`idfpy_embed.md` · `token_optimization.md` |
| [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) | **活文档**：本项目侧对下游 subagent 代码的 hotfix 记录（备份在 `backup/src_history/`）|
| [logs/review/](logs/review) | 交叉模型审阅轨迹（`request/` + `review/`，见 §5#8）|
| [archive/](archive) | 历史归档（已被取代/已实现/已 close）：`architecture.md` · `pipeline_validation_build_plan.md` · `rules_md_split_map.md` · `twostep_architecture_diagram.md` · `2026-06-09_..._refactor_handoff.md` |
| [../case_tests/test_baseline/](../case_tests/test_baseline) | baseline 方案 [README.md](../case_tests/test_baseline/README.md) + 注册表 [index.md](../case_tests/test_baseline/index.md) + gt [gt/README.md](../case_tests/test_baseline/gt/README.md) |
| [../skills/intake_pipeline/](../skills/intake_pipeline) | 0–5 阶段 skill 演进源（唯一 skill 库）|
| [../.devcontainer/README.md](../.devcontainer/README.md) | 多端开发环境指南 |
