# 主 Agent 操作手册 —— 编排器 + judge② 跑 case / 建 baseline（2026-06-16 重写）

> **这份文档是给「主控 Agent」看的初始上下文 + 操作手册。** 你（Opus / GPT5.5 / 任何主控模型）
> 在 dev 期负责：**编排** 0–5 管线逐段跑、**当 judge②** 裁每段 LLM 产物、**记录**反馈，最后给用户
> 一份人读的总反馈 + 🔍 肉视检验清单。**换主控模型时，读这一篇就能接手**（不依赖任何单独 memory）。
>
> **范围**：本项目侧 = 识图 → 校正 → 几何（造面+切配）→ 物理 → 装配 → 产 `IntakeOutput` → 下游 9
> subagent → EP。权威接线见 [architecture/pipeline_stage_contracts.md](../architecture/pipeline_stage_contracts.md)；
> 校验架构施工 [architecture/pipeline_validation_build_plan.md](../archive/pipeline_validation_build_plan.md)。
>
> **两种模式**：① **dev baseline（本手册）**——主 Agent 编排 + judge + 记录，跑出自包含 baseline；
> ② **未来一键化**——0_reading 接 VLM、judge 迁小模型/固化成确定性 check 后，整链无主 Agent 自动跑
> （`run_full_pipeline` 一条命令）。当前长期处于 ①。

---

## 0. 你的角色与三道关

```
                   ┌─ gate① 确定性 (代码 validate_case)  —— 便宜、先跑
每段产物 ─────────►─┤
                   └─ gate② judge (你, 看原图+渲染件+参考) —— ① 过后才跑
                                          │
                              人 ─ L-肉眼 (你列清单, 用户核渲染件)
```

| 关 | 谁 | 判什么 | 处置 |
|---|---|---|---|
| **gate① 确定性** | 代码 [`validate_case`](../../src/agent/execution/validation_run.py) | 结构/几何不变量(block) + 交叉核对(flag) | block→盲重抽/fail-closed；flag→留痕放行 |
| **gate② judge** | **你**（多模态看图）| 该段 rubric 逐条 `pass/minor/severe/fatal/...`（结构化清单，**非数字分**）| severe/fatal→盲重抽；minor→flag |
| **L-肉眼** | **人** | 确定性+judge 都盖不死的感知项 | 你在 `report/REPORT.md` 列 🔍 清单告诉用户看哪张图的哪点 |

judge 密度（自洽口径）：**只在 LLM 段 0/1/4 有 judge**；确定性段 2/3 无 per-run judge（靶子=代码单测）；5 无 judge。J0=0_reading、J1=1_correction（rubric 见 `skills/intake_pipeline/{0_reading,1_correction}/judge_rubric.md`）；**J4(4_mep) 暂 disabled stub**。

## 0.1 case = 纯素材；每次 run 自包含进 `run_<注释>/`（2026-06-16 用户定）

**case = 一组确定的测试素材**——`<case>/` 提交入库时**只含 `case_data/`**（`*_view.png` +
`testdata_prompt.json`）。**改素材才新建 case**。

**每次跑 = 一个自包含的 `run_<注释>/`**（单 case 可多轮 run：换模型组合 / 重抽 / 复跑）。一个 run
内含它自己的**配置 + 识图 + 全部产物 + 记录**，run 之间互不干扰、各自可复现：
```
<case>/
  case_data/                       ← THE case（素材；改素材才新 case）
  run_<注释>/                       ← 一次 run（自包含）
    llm.yaml                       本 run 模型配置
    0_reading/                     本 run 识图（复用好识图=拷进新 run）
    1_correction/ … 5_intakeoutput/  各段产物 + <stage>_checks.json + attempts/NNN/
    2_modelling/building_geometry.json + kernel_gate_report.json
    EP/EP_run/
    _run/                         机器记账：run_manifest / validation_manifest / baseline / state / approval
    report/REPORT.md              唯一人读报告（GEN 事实区 + AGENT 叙事/建议）
  run_<另一注释>/ …                  ← 另一轮（如换模型）
```
`1_correction…5_intakeoutput/ EP/` 由代码**跑中建**（`mkdir(parents=True)`），绝不预搭空骨架。
`validate_case(<run_dir>)` / `record_baseline(<case> <run>)` 都对**一个 run 目录**操作（case 素材由
`run_dir.parent` 解析）。gt 不在 case 内（见 §0.2）。

## 0.2 参考答案（gt）= judge② 专用，gate① / 执行器绝不看

每个 case 的评测标准答案放 [`case_tests/test_baseline/gt/<case>.json`](../../case_tests/test_baseline/gt)
（真实区划 / 每立面窗数 / 尺寸真值，人读原图独立得出）。**只有你（gate② judge）经
[`src/agent/judge/gt.py:load_gt`](../../src/agent/judge/gt.py) 读它**；**gate① 与执行器绝不 import**
（gate① 随上线、prod 无答案，必须 dev/prod 一致；执行器看了=照抄、误差预算崩）。详见
[gt/README.md](../../case_tests/test_baseline/gt/README.md)。判 1_correction 时载 gt 直接比对区划/窗数。

## 1. 不污染原则（最重要，机械保证，别破）

> 你既编排又当 judge，最大风险是把 judge 信息 / 下游信息泄漏进某段的输入，污染误差预算与训练数据。

1. **各阶段执行器隔离**：每段用**独立 API 调用** 或 **冷启子 Agent**，只喂该段**合同输入**（规则 +
   上游产物 + testdata），看不到你的 judge 评语、看不到下游信息。子 Agent 冷启 = 天然隔离。
2. **重做 = 盲重抽**：judge 说"不行"只触发"**同样输入换采样重跑**"，你的评语**只进带外记录**
   （`attempts/NNN/judge.json`），**绝不回灌 prompt**。代码已强制：`judge/retry.py` 的
   `judge_retry_context` 永不注入；只有显式 `repair_feedback`（下游 repair 通道）才注入。
3. **失败先分类再处置**（[contracts §0.3](../architecture/pipeline_stage_contracts.md)）：
   - `deterministic_code_failure`（确定性段后置失败）→ **fail-closed、记 code defect、不弹上游/不换样本**。
   - `stochastic_draw_failure`（0自动后/1/4 的 draw）→ **盲重抽**（≤3，超则 quarantine 交人）。
   - `upstream_input_failure`（输入违反前置）→ 弹**上游产出段**。
   - `judge_mismatch` → 盲重抽；归因不确定（root_confidence 低）→ **不自动路由、交人**。
   - **0_reading 默认 = manual** → `human_redraw_required`；当 `reading_runner_available=True` 时，
     可返回 `awaiting_reread`，由主 Agent 冷启隔离子 Agent 做盲重读（≤每段预算）。

## 2. 逐段编排流程（你每跑一个 case 这样走）

记号：`<case>` 在 `case_tests/e2e_tests/<case>/`；标准布局见 [contracts §3.1](../architecture/pipeline_stage_contracts.md)。

> **逐段 judge-in-the-loop 驱动器（2026-06-19 落地，理想态已实现）**：用
> [`scripts/tool_scripts/run_stage.py`](../../scripts/tool_scripts/run_stage.py) 一段一动作地推进——每段
> **跑执行器 → gate① →（坏 draw 段内盲重抽 ≤ 预算）→ 渲染 → 落 append-only attempt → 停下交你
> judge②**。核心状态机 [`src/agent/execution/step_orchestrator.py`](../../src/agent/execution/step_orchestrator.py)（`run_one_stage`/`submit_verdict`/`approve_geometry`/`update_state`）。verbs：
> ```bash
> BD=case_tests/e2e_tests
> # 逐段：跑一段 → 看它停在哪个状态（awaiting_judge / deterministic_pass / awaiting_geometry_approval / quarantined / …）
> python scripts/tool_scripts/run_stage.py --base-dir $BD --date <ISO> run      <case> <run> <stage>
> # judge②：你看完 packet 的原图+渲染(+gt)，写一份 StageVerdict JSON，提交
> python scripts/tool_scripts/run_stage.py --base-dir $BD --date <ISO> judge    <case> <run> <stage> --verdict v.json
> #   verdict 非阻塞→JUDGE_PASS(进下一段)；severe/fatal 可路由→JUDGE_BLOCK(↻ resample)；
> #   不可归因→交人；manual 段默认→human_redraw，有 runner→awaiting_reread
> python scripts/tool_scripts/run_stage.py --base-dir $BD --date <ISO> resample <case> <run> <stage>   # judge 打回后盲重抽（同 ≤3 预算）
> # 几何阻塞门：3_split_pairing 过 gate① 后停在 awaiting_geometry_approval；用户在对话里看 3D/区图/立面确认后你才批
> python scripts/tool_scripts/run_stage.py --base-dir $BD --date <ISO> approve-geometry <case> <run> --actor <user>
> python scripts/tool_scripts/run_stage.py --base-dir $BD status <case> <run>   # 看编排账本 + stop_reason
> ```
> **停下判据**（按 §1.3）：gate①-block 盲重抽耗尽=`quarantined`；deterministic gate①-block=`deterministic_defect`（fail-closed）；
> judge severe/fatal 不可归因=`judge_block_human`；0_reading 阻塞默认=`human_redraw_required`，
> runner 可用时=`awaiting_reread`（非 terminal，等主 Agent 完成盲重读 handoff 后继续）。任一 terminal 停点 → 直接出总报告。
> **几何门**：`ConfirmationPolicy.REQUIRED` 已接成阻塞门，**未 approve 时 `run 4_mep` 直接拒跑、不画**。
> 跑完或中途停 → `record_baseline.py`（已纳入逐段 status + stop_reason + judge verdict 计数）出 `_run/baseline.json` + `report/REPORT.md`。

### 准备
- 确认 `case_data/testdata_prompt.json` + `case_data/*_view.png` + 根 `llm.yaml` 就位。
- `.env` 有 `DEEPSEEK_API_KEY`（1_correction/4_mep 走 DeepSeek）。EP 在 `/EnergyPlus-*/energyplus`。

### S0 0_reading（识图，现半人工 / 子 Agent；后 VLM）
- 用一个**冷启多模态子 Agent**（或独立会话）逐图重描语义矢量 → `0_reading/*_view.json` +
  `reading_summary.md`。启动 prompt 见 [附录 A](#附录-a--识图0_reading-子-agent-启动-prompt)；规则真身
  `skills/intake_pipeline/0_reading/`。
- **gate①**：`check_reading_view`（结构 linter）→ 逐视图 `*_checks.json`。
- **gate② J0**（你看【原图 + `*_render.png` 线框 + JSON】，rubric=`0_reading/judge_rubric.md`）：七类
  识别错。致命/严重 → 默认 **human_redraw_required**；若本 run 显式启用 `reading_runner_available`，
  orchestrator 返回 **awaiting_reread**。
- **awaiting_reread handoff（主 Agent 协议，orchestrator 不执行）**：冷启一个隔离多模态子 Agent，
  只给 `case_data/*.png`（原分辨率，必要时裁图）、`testdata_prompt.json`、`skills/intake_pipeline/0_reading/`。
  **禁止**给 prior strokes / prior attempts / judge commentary / gt。模型/effort ladder 必须按 attempt
  预声明并带外记录；优先用原图保真、独立 OCR、严格 schema/linter 这些 discipline-safe lever，而不是把
  judge 评语变成 prompt repair。子 Agent 写/替换 flat working copy：`0_reading/*_view.json` +
  `reading_summary.md`（可附渲染）。然后主 Agent 跑
  `python scripts/tool_scripts/run_stage.py ... resample <case> <run> 0_reading --force`，它会读取 flat
  working copy，记录成下一次 `0_reading/attempts/NNN/output.json`，再 gate①→J0；达到 `per_stage_draws`
  仍不过则 quarantine/交人。

### S1 1_correction（校正，DeepSeek 独立调用）
- 执行器：`src/agent/pipeline.py:run_correction(vector_dir, testdata, out_dir=...)`——独立 DeepSeek
  调用，只喂 reading+testdata+`1_correction/` 规则，**看不到你的 judge**。出 `CorrectedGeometry` →
  确定性核吸附（`apply_deterministic_core`）。
- **gate①**：`check_correction`（A0§7 coverage/closure/zstack + 区数 tripwire + 窗位落墙 + delta/audit
  完整性）→ `correction_checks.json`。block→盲重抽。
- **gate② J1**（你看【原图 + 填色区图 `*_zones.png` + 立面窗位图 `*_elev.png` + 参考答案】，
  rubric=`1_correction/judge_rubric.md`）：区划/跨层/窗位/计数/整体 redraw 五条。severe/fatal→盲重抽。
  渲染件：`render_corrected_geometry.py`（区图）+ `render_elevation_windows.py`（窗位图）。

### S2+S3 几何内核（代码，确定性，无 judge）+ 几何阻塞人工确认门
- 执行器：`materialize_kernel_geometry(geom, out_dir)` 造面+切配 → `building_geometry.json` +
  `geometry_specs.md`。
- **gate①**：`check_kernel`（封闭/法向/pairing-gate-as-block/**矩形 coverage completeness**/spec 自洽）
  → `kernel_checks.json`。block = **代码缺陷，fail-closed**（不弹上游）。
- **3D 检视（#3，2026-06-19）**：`run_stage run … 3_split_pairing` 过 gate① 后生成
  **`manual_review/geometry_viewer.html`**（`render_geometry_viewer.py` 出的**自包含离线**交互查看器：
  three.js 内嵌、浏览器双击即用——orbit/缩放 + 墙体半透明 + X·Y·Z 截面 + 爆炸视图 + 量距 + 点选高亮区 +
  按楼层/区/OBC 着色 + 存 PNG）。GLB 旁路 `render_building_3d.py` 已从主流程剥离（工具保留，后续需要再启）。
- **阻塞门**：`ConfirmationPolicy.REQUIRED` 下停在 `awaiting_geometry_approval`，用户浏览器看完确认无误
  → `run_stage approve-geometry <case> <run> --actor <你>`（绑 geometry digest，几何漂移自动失效）→ 才放行 S4。

### S4 4_mep（物理，DeepSeek 独立调用）
- 执行器：`run_mep(zone_specs, used_constructions, testdata, out_dir=...)`——独立 DeepSeek，只喂 zone
  列表 + 必需 construction 集 + `4_mep/` 规则。
- **gate①**：`check_mep`（引用图 geometry→construction→material + load→zone/schedule + schedule 完整性
  + 对象语义 SimpleGlazing standalone/NoMass 正热阻）→ `mep_checks.json`。block→盲重抽。
- **gate② J4 暂 disabled**（不产 verdict，记 disabled，非假 PASS）。

### S5 装配 + EP
- `assemble_intake_output` + `validate_contract`（backstop）→ `5_intakeoutput/intake_output.json`。
  `check_assembly` → `assembly_checks.json`。
- 下游 9 subagent + InterZone 门 + EP 仿真：跑 `run_full_pipeline`（它内部完成校正→…→EP；若你已逐段
  跑出 intake，可 `--intake-from` 只跑下游+EP）。EP end 断言：`check_ep_baseline`。

> **两条路径**：① **逐段 judge-in-the-loop（理想态，2026-06-19 已落地，默认走这条）**——`run_stage.py`
> 一段一停，per-stage judge 盲抽 + attempts 全上 + 几何阻塞门（见本节顶部驱动器框）。② **整链 v1（仍可用，
> 调试/回归用）**——`python scripts/run_full_pipeline.py <case> --base-dir case_tests/e2e_tests
> --reading-from 0_reading` 跑完再 `validate_case` 出 gate①、事后补 judge②。两者都不污染（执行器本就隔离）；
> 差别只在 judge 是**逐段在线打回**（①）还是**事后统一**（②）。

## 3. 记录（attempts 全上 + 成绩单 + 人读反馈）

- **每次抽都落 append-only attempt**：用 [`file_stage_attempt(runner, stage=…, output_obj=…,
  report=…, verdict=…)`](../../src/agent/execution/orchestrate.py) → `<stage>/attempts/NNN/{output,
  checks,judge}.json`（**不覆盖坏草稿**），accepted 指针进 `_run/run_manifest.json`。`runner =
  StageRunner(case_dir, RunManifest.load(case_dir))`。
- **你的 judge verdict** 用 `StageVerdict`（schema v2：criterion status + root_stage/confidence +
  retriable，见 `src/agent/judge/verdict.py`）；可经 `run_judge(stage, artifacts, judge_fn=<你填
  verdict>)` 走预算/quarantine/append-only，或直接 `file_stage_attempt(..., verdict=…)`。
- **成绩单 + 人读反馈**：跑完一条命令出 `_run/baseline.json` + `report/REPORT.md`：
  ```bash
  python scripts/tool_scripts/record_baseline.py <case> <run> --base-dir case_tests/e2e_tests \
      --date <ISO 日期> --orchestrator <你的模型id>
  ```
  它跑 `validate_case(write_reports=False)` + 汇总 + 读 llm.yaml/EP end + 收集 attempts/verdicts，
  不重写 load-bearing `<stage>_checks.json`。

## 4. 给用户的总反馈 + 🔍 肉视清单

`record_baseline.py` 生成单一 `report/REPORT.md`：GEN 区由代码刷新，AGENT 区保留主控撰写内容。
**你必须完成 `REPORT.md` 的 Agent-fill 槽位**，尤其是错因链和四桶建议；建议区只能用结构化 bullet：
`action` / `evidence: [E:...]` / `owner`，每条 evidence id 必须存在于 `_run/baseline.json.evidence_index`。
若某桶无证据支持，保留精确哨兵 `本 run 无可证据支持的建议`。**你在对话里也复述这份反馈**，并明确告诉用户：

- 结论（clean / blocked）+ golden 计数 + EP 结果。
- **🔍 必看**（L-肉眼，确定性+judge 盖不死的）：① `report/eyeball/` 里的填色区图 vs 原平面（走廊有没有被切断那类）
  ② `report/eyeball/` 里的立面窗位图 vs 原立面（窗在不在对的立面）③ `manual_review/geometry_viewer.html`
  体量/分区/窗位像不像 ④ 每条 flag 对应的那张图那一点。
- **不要让用户瞎看**——精确到"看哪张图的哪一点"。

## 5. 「干净」收口 + baseline 入库

- 收口标准：gate① **0 block** + EP **0 severe**；flag 允许但必须在 `_run/baseline.json.flags[]` 留痕。
  出现不该有的 flag（区数 tripwire / 跨图对账不齐）→ 回 S0 修识图到干净，不带病入库。
- 入库：在 [`case_tests/test_baseline/index.md`](../../case_tests/test_baseline/index.md) 登记一行
  （golden 计数 + 状态），并加/更新该 anchor 的 golden 测试（`tests/test_validation_run_baseline.py`
  断言 `blocked=False` + 计数 + EP 干净）。
- anchor 的管线产物**提交入库**（与可重生成的普通 e2e case 不同——anchor 是冻结金标准；EP `eplusout.*`
  与 `EP/temp_*` 仍 gitignored）。

## 6. 模型配置（per-case）

`<run>/llm.yaml`（run 记录的模型配置；从全局 `src/configs/llm.yaml` 拷模板，经 `EP_AGENT_LLM_CONFIG` 覆盖）。段→阶段：

| 段 | 阶段 | thinking |
|---|---|---|
| `intake_correction` | 1_correction（+几何兜底）| **enabled**（单次推理）|
| `intake_mep`（缺则回退 correction）| 4_mep | enabled |
| `default` | 下游 surface/construction/fenestration | disabled（多轮 ReAct，开则 400）|
| `zone`(*flash) | 下游 zone/material/schedule/hvac/people/lights | disabled |

换模型 = 改 run 里的 `llm.yaml`，不动全局/代码。

## 7. 常见坑

| 坑 | 处理 |
|---|---|
| 识图把杂物当结构 / 漏真墙 | gate② J0 抓；manual 段 → human_redraw |
| 走廊被切成多段（区数 ↑）| gate① 区数 tripwire flag + J1 布局裁决；回 S0 修 |
| 跨层同墙抖动 5cm | 确定性核吸附；仍报看识图矢量 |
| 1_correction 0 窗 / 非法 JSON | draw 级校验已拦 → 盲重抽（DeepSeek 偶发） |
| EP 段错（不完整 schedule）| `mep.schedule_completeness` 前移已拦 |
| `validate_case` 报 `artifact_consistency` | 磁盘 2/3 产物与确定性重建不符（陈旧/坏）→ 重跑该段 |
| EP `eplusout.end` 缺 | fatal/段错，**非 PASS**（`check_ep_baseline` fail-closed）|

---

## 附录 A · 识图（0_reading）子 Agent 启动 prompt

> S0 用。冷启一个多模态子 Agent / 独立会话。**启动 prompt 已版本化为单文件**
> [`skills/intake_pipeline/0_reading/session_kickoff.md`](../../skills/intake_pipeline/0_reading/session_kickoff.md)
> ——durable 纪律不再贴在这里（根因=非版本化启动 prompt 会悄悄退化），规则真身在
> `skills/intake_pipeline/0_reading/` 三件套，运行时读取。

把下面**单行**作首条消息（按 case 改占位）：

```
Read skills/intake_pipeline/0_reading/session_kickoff.md and follow it for case <CASE>.
The drawings are at <CASE>/case_data/ (or the path I give you); fill the image table in the kickoff
before tracing. Do the pilot first, then stop and wait for my review.
```

`session_kickoff.md` 自身会指引读三件套 skill 文档 + 填本 case 图名表 + pilot→review→batch 流程 + 边界。
改纪律请改 `guide.md`（版本化），不要改回启动 prompt。

---

完工后人工校验：`render_vector_to_png.py` 渲图肉眼比对（杂物误当结构 / 漏真墙真窗 / 门 healing /
`uncaptured` 是否如实）。

---

_2026-06-16 — 重写为「主 Agent（编排器 + judge②）操作手册」：换主控模型读此即可接手。新增 §0 三道关 /
§1 不污染原则（执行器隔离 + 盲重抽 + 失败分类）/ §2 逐段编排（各段执行器 + gate① + gate② rubric）/
§3 记录（attempts 全上 file_stage_attempt + record_baseline）/ §4 总反馈+🔍肉视清单+REPORT 撰写 / §5 干净收口+入库。
配套校验架构 M0–M4（`src/agent/execution/`、`src/validator/checks/`、`src/agent/judge/`）。旧「正式化一次
性跑」版备份 logs/backup/new_case_guide.md.bak_2026-05-29（更早）。_
