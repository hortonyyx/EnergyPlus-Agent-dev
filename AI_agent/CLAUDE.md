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
| [../tests/](../tests) | pytest **1427 绿 + 9 strict xfail**（kernel/checks/judge/orchestrator/gt/interzone/schedule/viewer/flow/runner/grade/run_config/isolation/view_manifest/c2_b2_v3/c2_b2b_envelope_transform/c2_va_applicability/gt_schema/output_coordinate_×5/e4_relative_north_axis_e2e/c2_b5_source_routing/c2_b5_host_resolution/c2_b5_parent_and_verts/c2_b5_artifact_trust/c2_b5_legacy…）|
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

---

## 2. 当前开发状态

- **分支** `6.15_ValidationArchM0toM4`（已推 origin）；测试 **1427 绿 + 9 strict xfail**（9 个均为 legacy golden 精确重建待 sm21 批次重录、xfail 带 reason〔含 2 个 legacy golden sm20/run_2026-06-15、sm21/run_2026-06-16_opus 无编排账本→run_state=incomplete〕；**B5 Phase C 延后的 6 个 `test_output_coordinate_identity.py` E4 build-proof xfail 已在 Phase D 复原为真绿**——Phase D 接通 E4 stepwise→build→loader→assembly 的 proof 生产链〔gate B5-D3 + MINOR-2〕，六条现走生产 source→writer→accepted loader→proof→build/assembly 真链，`test_output_coordinate_identity.py` 零 xfail）。
- **最新里程碑** = **C2 B5 Phase D CLOSED ⇒ B5 全系列（A–D）整个收官**（信任根/E4/legacy 封口；2026-07-19 Opus 主控，1360→1427 绿 + 9 xfail〔6 个 Phase C 延后 xfail 复原为真绿、15→9〕）：**全升一档** = sol 施工 → **诚实 PARTIAL**〔精确标 5 未竟、不藏假绿，对标 B4b Phase D 正面样板〕→ 主控退回续作〔5 项 + 裁唯一 review-ask=删 v3→B2 兼容后门，v3 必带 proof 即使零窗〕→ sol 续作 COMPLETE〔writer 十步独立重算/六件套 artifact contract（`correction_b5_v1`·`correction_b5_orientation_v1`）/accepted+integrated loader 全验/E4 rebind/audit-report rejected 扫描/legacy 三层锁/6 xfail 生产链复原/MINOR-1 伪 marker 收回/MINOR-2 pipeline C↔D proof 接线/NIT-3 共享 serializer/NIT-4 冻结字节 fixture〕→ **Fable 对抗审 r1 REWORK**〔0 BLOCKER/2 MAJOR/3 MINOR/2 NIT；**生产码信任根本体零 bug、全部活体验真**〔writer 双根独立 bomb 探针 + 三边界后门删除破坏即红 + legacy 字节层对改造前 HEAD 逐项相等 + 6 xfail 真生产链〕；2 MAJOR 均「门是真的、锁是缺的」——writer replay/totality 门 + E4 relation 守卫 neuter 后全绿=缺负锁、且简报声称的 replay 锁实际停在上一道 `writer_audit_output_drift`、从未触达 replay 门〕→ sol 返工 r1〔纯补 4 负锁 + MINOR-1/2 顺手、零生产码永久改动〕→ **Fable r2 APPROVE**〔三门 neuter 各只红对应新锁 2/1/1、无连带、无新洞、生产码逐字节对 r1 尾态〕→ **主控轻门=独立全量 1427 绿 + 9 xfailed 零回归**〔亲核 6 xfail 复原/伪 marker 清除/3 负锁 match 串绑门/GT·golden 零 diff/三门 raise 在位〕。**治理数据点（Opus 主控试点）**：升一档审**连续第十批首轮抓 MAJOR**（抓的是 false-lock=false-green 近亲）；主控轻门独立全量作唯一权威门。剩 **NIT-3**〔AST 扫描裸 `except:` 一行缺口·现实七文件零命中〕+ **MINOR-3**〔writer replay 对 manifest 覆盖 envelope readings 前提待首个真实 v3 run 验证〕= 非阻断跟进债。审轨 `logs/reviews/{request,execution,verdict}/2026-07-19_b5_phaseD_*`。**上一里程碑** = C2 B5 Phase C CLOSED（窗落墙线几何 + 四子系统同步，2026-07-18，1314→1360 绿；全升一档 sol+Fable r1 REWORK〔缺 17 锁〕→r2 APPROVE→主控轻门抓 6 out-of-scope 回归转 xfail 指向 Phase D）。**上上里程碑** = C2 B4b 全系列（A–D + REC-A–D）全收官 ⇒ C2 判卷子系统 elevation/fusion/policy/capability/run-stage/cache/renderer/CLI 全落地。**完整里程碑史（倒序、含每轮 commits / 审轨 / 产物指针）看 [decision_log.md §A](decision_log.md)；本节不再叠加历史。**
- **主控 / 协作现状**：主控 = **Opus 4.8**（整场不切模型）；Fable5 降三类点射（规划出稿 / 工程细稿最高档交叉审 / 大节点复核会诊）；执行审升一档交叉、排工拍板制、谁写谁不批（详 §5 + [decision_log.md](decision_log.md) 07-16「主控降档拍板」条）。
- **已落地能力盘面**（详见 [decision_log.md §A](decision_log.md)）：0–5 校验架构 M0–M4 + 逐段 judge-in-the-loop 编排 + 离线 3D 几何查看器 + 自包含 baseline（anchor+gt）+ 单一 `flow` 编排 SOP + 判卷可视化统一模型（gt 逐元素对账）+ CV 工具箱（弱 VLM「量而非看」迁移性坐实）+ 污染硬隔离机制化 + 命名/外包确定性化 + report/ 策展汇报 + 双模型家族协作规约。C2 收官批陆续 CLOSED：B0 / B1（Cell.polygon）/ B2 / B2b / B3 / B-M（view_manifest）/ B-O（真北 Relative 出口契约）/ Vg（立面可见性）/ Va（opening 适用性）/ **B4a Phase A–D 收官**（GT schema v3 strict wire + DXF round-trip 提取 + 统一 render model/overlay v3）/ **B4b Phase A–B**（score identity/config/sidecar v8 + 段级 plan scorer〔segment/opening/Va 计分/精确 denominator〕）；strict v3 子类族 + floor footprint 单一权威 + 统一 finalize 已就位；GT-to-Va 计分侧 judge-only、Va 唯一 applicability 引擎。
- **下一步**（滚动计划见 [plan.md](plan.md)）：① **B5 全系列（A–D）已收官** → 下一站 = **B5b（归 C2.1，服务 sm26「不给全」子 case，非 sm25-L 阻塞）** + **B6 端到端 anchor**（外轮廓 polyline/翼分界 skill 词汇〔机械〕+ 跑 **sm25-L**〔图已出、B5 已完，C2 收官不再等图〕）。**⚠️C2 路线 2026-07-18 用户重切为「单轴爬坡」**：sm25-L=C2 收官（L 形非方形、四标准命名立面、无旋转/无匹配/无缺件）/ C2.1=立面匹配+缺件补（sm26-U 不转）/ C2.2=旋转+总图输入（sm26-rotate）/ sm27-回字型=整个 C2 总验收（详 plan.md 07-18 块）。② **B5 Phase D 跟进债**（非阻断，登记待后续批次）：NIT-3 = `test_source_scan...` AST 扫描的 `handler.type is not None` 条件使裸 `except:` 逃逸（一行修法 `handler.type is None or ...`；现实七信任链文件裸 except 零命中，下批顺手落）；MINOR-3 = writer replay 依赖「manifest 覆盖全部 envelope 相关 readings」的可用性前提，待首个真实 v3 case run 验证（若命中按细稿口径并入受信 marker、不得放松 replay）。③ **B4b Phase D 跟进债**（非阻断）：MINOR-1 = `score_typed_attempt(stage="correction")` correction v3 无独立 e2e fixture（休眠不触生产，correction v3 真接下游时补测）；MINOR-2 = typed grade renderer claim-box 简化，未做 §11.3 partial-interval hatch / §11.4 clip-conservation 细化（仅 grade 可视化，sidecar 权威分不受影响）。④ **standing gate**：sm21 批次重跑（reading-honest + judge 两轴 recoverability + auto re-read + 新命名攒齐一次性跑）→ 同时重录 sm20/sm21 golden（撤 9 个 xfail、strict→XPASS 会提醒）→ 结果不错则可合并 main。

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
8. **双模型家族分工（硬默认：主控别自己开干；2026-07-10 GPT-5.6 轮修订；⚠️2026-07-12 用户重梳四档对位阶梯为唯一口径+同日补充；**⚠️2026-07-16 用户拍板主控降档=主控切 Opus 4.8、Fable 在场期降点射，四档对位与审阶梯不变**，详 [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md) §2：最高档 Fable↔sol/次高档 Opus↔sol/中档 Sonnet↔terra/低档 Haiku↔luna；**审一律高产出一档**=规划〔Fable 在场期恒 Fable 出·sol 对抗审〕/细稿次高档出·最高档 Fable/sol 交叉审/执行中档·执行审 Opus/sol 交叉+主控大节点；细稿不占 Fable、主控不亲手出稿；Fable 退场后规划=双独立出案→**新启**会话综合〔综合稿=综合方家族产物〕→另一家族**新启**对抗审,两边均不继承初稿上下文；**排工拍板制：每次排工先出派工表交用户拍板再派,中途返工续循环免重拍**）**（操作手册 [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md)）：**主控 = Claude 家族开对话模型**（**2026-07-16 用户拍板起 = Opus 4.8**，开会话即 Opus、整场不切模型〔同会话中途切模型=已写缓存全作废〕；**Fable 5 在场期降为三类点射**：①规划/方案出稿〔子代理或独立短会话+精简 brief〕②工程细稿最高档交叉审〔不变〕③大节点复核/疑难会诊。动因=Fable 主控烧 5h 窗太快+撞 Fable 单独限额；缓存按「模型+前缀」隔离且 TTL≤1h、跨窗本就冷启→切主控无缓存税，Opus 单价≈Fable 一半→单窗可开发量↑），亲手只做：① 方案/规划 ② 审 diff/裁决 ③ judge ④ memory + 管理文档（`AI_agent/`）纯文字编辑 ⑤ `git add`/`commit`（唯一小例外：trivial 单点改且方案言明、或纯文档/计划编辑）。**凡实质改动（`src/`/`skills/`/`tests/`/MCP/下游）一律走角色矩阵**：方案（规划/方向档 = **Fable 在场期仍 Fable 出稿**〔07-16 起点射方式、不任主控〕+sol 对抗审；Fable 退场后 Opus 与 sol **双独立出案→新 Opus 会话复核统一**〔07-16 用户确认：预埋条款，当前不启用〕）→ **交叉最顶对抗审**（Claude 侧产物→sol；GPT 侧产物→Fable/Opus；effort = 最高两档 max/ultra 主控择一）→ 主控裁决（不盲从）→ **派执行档实现**（Sonnet 5 子代理 / terra；批量机械活 Haiku/luna；简报含「审阅需求」）→ routine 采信、**大节点交叉中档复核**（Claude 侧执行→terra；GPT 侧执行→Opus）+ 主控全面审。**谁写谁不批**（跨厂商交叉是必须）；推理强度不写死、主控按任务定；**额度侧动态定**：派批次活前看两边窗口、问用户拍（规划/方向与方案评审保质量不受额度约束）；复核简报纪律 = 批准者只看原始需求+diff+测试输出，不看执行者长篇自述。独立审计/交叉核实同样交叉派发，主控只设 brief、不与之并行自查以保独立性。**⚠️ 2026-06-27 教训**：已「出方案 + 用户 ratify」后，Claude 仍自己把 reading 修法 7 个文件全改了、只把 Codex 当事后审稿 → 违反分工、已全部回滚重做。**「出了方案 ≠ 可以自己执行」**。**⚠️ 2026-07-11 第三犯，用户令强化**：B-M 首轮施工规矩派了 Sonnet，但交叉复核后的**两轮返工主控又亲手改码**（Fable 额度烧穿、中途被迫切号）→ 硬化条款：**返工轮 / 复核 findings 修复 / 探针·实验执行同属实质改动，一律派执行档**；主控「大节点全面审」= 审 diff + 自跑测试，**不含亲手修**；察觉自己在编辑 `src`/`tests`/`skills` 即违规信号——停手改派。额度侧属哪家按轮动态拍（例：2026-07-11 用户拍 GPT 侧频繁重置期间**施工优先派 terra、终审翻 Claude 侧**，谁写谁不批方向随之反转）。
9. **开发环境统一 VS Code Dev Container**（[../.devcontainer/README.md](../.devcontainer/README.md)）：容器内 EnergyPlus 25.1.0；git 是唯一同步通道，禁文件同步工具同步本目录；`.devcontainer/`(bind mount, VS Code) vs `docker/`(COPY 代码, MCP server 发布) 别混。
10. **DeepSeek**：v4-pro thinking 默认关（langchain_openai 不回传 reasoning_content 多轮 tool-call 必 400）；管线内 correction 模型角色不变；原 `deepseek-bridge` MCP 承接的省额度小活（简单文本任务）现优先派 luna/Haiku 轻档（§5#8 矩阵），bridge 保留备选；架构/编辑/集成仍主模型负责。
11. **idfpy 替换 + token 优化搁置**（[deferred/](deferred)）：等协作者侧 MCP 重写交付。
12. **收工 ritual（每轮结束硬规范，2026-06-27 用户定）**：「收工」必须做完两件事——① **更新管理文档**（当前状态→本文§2 / 待办与进展→[plan.md](plan.md) / 里程碑历史→[decision_log.md](decision_log.md) / 架构变更→[contracts](architecture/pipeline_stage_contracts.md)；并遵 memory↔文档同步铁律 §5#1）；② **git 处理 = `commit` 本轮全部改动 + `push` 当前分支**。**收工本身即对 push 的标准授权**（覆盖 §5#7 的"平时不 push"）；force push 仍禁。没做完这两件不算收工。
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
