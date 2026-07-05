# P1 动工执行简报：`flow` 编排 + gt 权威 judge evidence —— 待 Codex 审

> 状态：**执行简报待 Codex 审**（2026-07-02，Claude 出）。
> 权威设计 = [`2026-07-02_standardize_test_flow_proposal.md` §8](2026-07-02_standardize_test_flow_proposal.md)（已终审 GO + 8 条 build 必办）。
> 本简报 = 把 §8 的 **P1** 落到当前代码上的**可执行工序**，含对几处 build 必办里未定死机制的**具体机制方案**（durable 人工校验 checkpoint / scorer→criterion 映射 / EP 布局共享函数 / 退出码）。
> 分工：本简报经 **Codex 审**（裁机制方案）→ Claude 裁决 → **Codex 分批执行** → Claude 大节点全面审。**P2（J23 + `score_geometry_vs_gt` + 内核能力根路由）不在本简报**。

---

## 0. 现状锚点（已读码核实，Codex 可据此核）

| 件 | 位置 | 关键接口 |
|---|---|---|
| 逐段 verb 宿主 | `scripts/tool_scripts/run_stage.py` | verbs: run/resample/judge/approve-geometry/status；`cmd_run` 调 `run_one_stage`，`_judge_packet` 产 packet，`_render_geometry_viewer` 产 3D，`_make_policy` 造 RunPolicy |
| 编排核 | `src/agent/execution/step_orchestrator.py` | `run_one_stage`→`StageOutcome(status: StepStatus, route_target, ...)`；`submit_verdict`；`_post_gate1`（几何门 in stage==3、judge dispatch）；`TERMINAL_STOP`/`ADVANCE_OK`；`update_state`/`mark_geometry_approved`/`load_state` |
| StepStatus | 同上 | AWAITING_JUDGE / DETERMINISTIC_PASS / AWAITING_GEOMETRY_APPROVAL / AWAITING_REREAD / JUDGE_PASS / JUDGE_BLOCK / QUARANTINED / DETERMINISTIC_DEFECT / HUMAN_REDRAW_REQUIRED / JUDGE_BLOCK_HUMAN |
| 几何 approval（durable 范例）| `src/agent/execution/approval.py` | `GeometryApproval(digest,actor,policy,timestamp,note)` + `geometry_checkpoint_digest(...)` + `is_approved`；存 `_run/geometry_approval.json`（经 `run_meta_path`）|
| manifest | `src/agent/execution/manifest.py` | `RunManifest.load/save/accept/accepted`；`StageRecord(accepted_attempt, output_hash, input_hashes,...)`；hash helpers |
| invalidate | `src/agent/execution/invalidation.py` | `invalidate(manifest, stage)`→drop 下游指针（返回被清 stage 列表）；`downstream_of` |
| policy | `src/agent/execution/policy.py` | `RunPolicy(confirmation_policy, judge_enabled, run_profile, require_ep, reading_runner_available, budget)`；`ConfirmationPolicy{REQUIRED,OPTIONAL,DISABLED}` |
| EP 布局 | `scripts/run_full_pipeline.py:262-343` | `--reading-from`+`output_subdir==output` 分支设 `output_dir=<case>/EP, ep_run_subdir="EP_run"`（正确布局）；`--intake-from` 走 flat `output/`（无 EP_run）；graph run 段 `build_graph()`+`SimContext(output_dir, ep_run_subdir, run_simulate)`+`run_session` |
| reading scorer | `src/agent/judge/reading_score.py` | `score_reading_dir(dir, case)`→`{stem: FloorScore}`；FloorScore.wall_hits()/window_hits()/max_wall_offset()；**读 gt via load_gt（judge-only）**；解析 `*_view.json` strokes（pen=wall/window，line/rect 皆认）|
| verdict | `src/agent/judge/verdict.py` | `StageVerdict(criteria, root_stage, root_confidence, ...)`，`model_config extra="forbid"`（**别往里塞 raw 分**）；`.blocking`/`.routable` |
| judge registry | `src/agent/judge/executor.py` | `rubric_for(stage)`：J0(0_reading,on)/J1(1_correction,on)/J4(4_mep,off)；2/3/5 无 judge |
| record | `scripts/tool_scripts/record_baseline.py` | CLI `<case> <run> --base-dir --date --orchestrator --require-ep --run-profile`；build fn 带 `require_ep` 参 |

---

## 1. P1 交付总览（§8.10 前 4+6+7 项 + 8 build 必办）

分两批派 Codex 执行 + 一批 Claude 文档：
- **Batch A（编排 harness）**：`flow` verb + EP 布局修(option A) + 退出码 + durable 人工校验 checkpoint & resume + geometry-auto 审计可见 + JUDGE_BLOCK 自动重抽 + 下游 invalidate。
- **Batch B（gt 权威 judge evidence）**：`score_*_vs_gt` 接进 judge_packet 当机读 evidence + 阈值→criterion 映射 + J1 correction scorer 适配器 + 产物↔gt overlay(0/1)。
- **Batch C（Claude 亲手，A+B 落地后）**：`new_case_guide.md` 重写为新 SOP（6 步 + 三层叠加门 + gt 权威判卷 + overlay + `flow` 命令）。

Batch A 是结构性大改（动编排核 + 新 StepStatus + 新 durable 记录），是本简报审查重点。Batch B 相对自包含（judge-side 工具 + packet 富化），A 落地并复核后再派 B。

---

## 2. Batch A —— 编排 harness

### A1. `flow` verb（`run_stage.py` 新增，复用现有全部机制，不重写编排核）

命令：
```
python scripts/tool_scripts/run_stage.py [--base-dir ..][--date ISO][--run-profile P] \
    flow <case> <run> \
    [--from auto|0_reading|1_correction|..] [--to 5_intakeoutput] \
    [--judge stop|off] \
    [--review reading,correction]      # 逗号分隔的人工校验点开关（geometry 走 --geometry）
    [--geometry required|auto] \
    [--with-ep] [--record --orchestrator <model>] [--record-partial] \
    [--reading-runner-available]
```

**循环逻辑**（从 `--from` 解析的起点，沿 `_STAGES` 到 `--to`，每段调现有 `run_one_stage`；`flow` 只加"停靠/续跑/自动动作"外壳）：

对每段 `stage`：
1. 造 `draw_fn`/`packet_fn`（复用现有 `_make_draw_fn`/`_judge_packet`），调 `run_one_stage(...)` → `StageOutcome`。`update_state` 落账。
2. 按 `outcome.status` 分派：
   - **`DETERMINISTIC_PASS` / `JUDGE_PASS`（ADVANCE_OK）** → 若该段是**开了人工校验开关的 checkpoint** 且**尚无匹配 durable 复核记录** → **停 `AWAITING_HUMAN_REVIEW`（退 10）**（见 A3）；否则 advance 下一段。
   - **`AWAITING_JUDGE`** → 产 judge_packet（已在 `run_one_stage`→`_post_gate1`→`packet_fn` 内产）。
     - `--judge stop`（默认）：**停（退 10）**，打印 packet 路径 + 提示「提交 verdict 后重跑 flow 自动续」。
     - `--judge off`：判开关关（`judge_enabled=False` 的 policy）→ 该段无 enabled judge → `run_one_stage` 直接给 `DETERMINISTIC_PASS`（走 gate①-only）。**实现 = 造 policy 时 `judge_enabled = (args.judge != "off")`**，不需在 flow 里特判。
   - **`AWAITING_GEOMETRY_APPROVAL`** →
     - `--geometry required`（默认）：**停（退 10）**，先产/刷新 3D viewer（`_render_geometry_viewer`），打印路径 + 提示 `approve-geometry`。
     - `--geometry auto`：**先重渲 viewer**（防陈旧）→ 调 `approve_geometry(..., actor="flow:auto", policy="auto")`（见 A5）+ `mark_geometry_approved` → **续跑**（重进本段/下一段）。
   - **`AWAITING_REREAD`** → 打印现有 reread 协议（`_print_reread_protocol`）+ **停（退 10）**（reading 子代理不在 flow 自动化范围）。
   - **`JUDGE_BLOCK`**（routable stochastic root）→ **自动盲重抽**（见 A4）：`invalidate` 下游 → 对 `route_target` force resample → 继续循环。
   - **terminal_stop**（QUARANTINED / DETERMINISTIC_DEFECT / HUMAN_REDRAW_REQUIRED / JUDGE_BLOCK_HUMAN）→ **停（退 20）**。
3. 到达 `--to` 且该段 advance 后：收尾（A2 EP + record）。

**可续性（manifest-first，MAJOR-2 采纳）**：`--from auto` 的"已 advance"判定**以 manifest 为权威，`orchestration_state.json` 只作 pending 提示、绝不用于证明完成**（`invalidate` 只删 manifest 下游指针、**不改 state** → state 里可能残留旧 `deterministic_pass/judge_pass`，若据 state 跳段会错误跳过被 invalidate 的 2/3/4/5）。某段算 **advance** 须**同时**满足：① 有 `manifest.accepted(stage)`；② 若该段有 enabled judge（J0/J1）→ accepted attempt 旁有**非 blocking** verdict（`judge.json`）；③ 若该段开人工 review 开关 → durable review hash 当前（`review_is_current`）；④ 若是几何门段 → approval digest 当前；⑤ 上游未因 invalidate 使本段缺 accepted 指针。`--from auto` = 从最早"不满足 advance"段起，**不静默跳 0_reading/J0**（build 必办#3）。`--from 1_correction` 须显式（= 声明复用已判 reading）。**补测（F/A7）**：已判 1_correction 后 `invalidate(manifest,1_correction)` → `--from auto` 从 2 起而非跳到 5。

**注意 flow 与 judge 提交的接力**：judge verdict 由主控**在 flow 之外**用 `run_stage judge ... --verdict v.json` 提交（flow 不产 verdict——主控在环判卷不变）。提交后主控**重跑 flow**，`run_one_stage` 读到 attempt 旁的 `judge.json` → 经 `_post_gate1`/`_verdict_outcome` 给出 JUDGE_PASS/JUDGE_BLOCK → flow 据此续/重抽。**人工校验**同理：主控看完 overlay 后用新 verb `approve-review`（A3）落 durable 记录，再重跑 flow 续。

### A2. 收尾：EP + record（在 5_intakeoutput advance 后）

- `--with-ep`：调 **A6 抽出的共享函数** 跑下游 graph + EP → `<run>/EP/EP_run/`。喂 `<run>/5_intakeoutput/intake_output.json`。EP 失败 → **退 30**。
  - **run-scoped LLM 配置（MAJOR-3 采纳）**：调共享函数**前**解析并设 `EP_AGENT_LLM_CONFIG`，优先序 = `--llm-config`（显式）> `<run>/llm.yaml` > `<case>/llm.yaml` > 全局 `src/configs/llm.yaml`；**日志记实际配置路径**（对齐 §8.1 第 2 步"新 run 落模型配置"）。`--epw` 暴露为 flow 参、默认复用 `data/weather/Shenzhen.epw`。
- `--record`：调 `record_baseline`（build fn 或 shell）→ `_run/baseline.json` + `report/REPORT.md`。
  - **build 必办#6**：`--with-ep` ⇒ 传 `require_ep=True`；**有 pending 段时 `--record` 默认拒绝**（除非 `--record-partial`）——flow 收尾前查 state：若 `stop_reason` 非空或未到 `--to`，拒绝 record（退 30 或明确报错），除非 `--record-partial`。
  - `--date` 复用顶层 `--date`；`--orchestrator` 必填（record 要）。

### A3. durable 人工校验 checkpoint + resume（build 必办#6 核心——**新机制**）

**问题**：judge 过（JUDGE_PASS）后若该 checkpoint 的人工校验开关开着，flow 应停等用户看 overlay+分表再续；但 `run_one_stage` 对已判段每次重进都回 JUDGE_PASS → 无 durable「已人工复核」记录则 flow 每次都在同点反复停。

**方案（照 `GeometryApproval` 平行造，最小侵入）**：新 `src/agent/execution/review.py`：
```python
REVIEW_NAME = "human_review.json"          # 存 _run/human_review.json（run_meta_path）
class HumanReviewApproval(BaseModel):       # extra="forbid"
    stage: str
    output_hash: str                        # 绑该段 accepted attempt 的 output_hash（manifest.StageRecord）
    actor: str
    timestamp: str = ""
    note: str = ""
# 文件 = {stage: HumanReviewApproval}（多 checkpoint 各一条）
def load_reviews(run_dir) -> dict[str, HumanReviewApproval]: ...
def record_review(run_dir, *, stage, output_hash, actor, timestamp, note): ...
def review_is_current(run_dir, *, stage, output_hash) -> bool:   # 存在且 hash 匹配（漂移即失效 fail-closed）
```
- **绑 output_hash**（取 `manifest.accepted(stage).output_hash`）：resample/重画换了 accepted attempt → hash 变 → 复核自动失效（须重审），与几何 approval 的 digest-drift 语义一致。
- **flow 判定**：某段 ADVANCE_OK 后，若 `stage in review_switches` 且 `not review_is_current(run_dir, stage, cur_hash)` → 返回/停在**新 StepStatus `AWAITING_HUMAN_REVIEW`**（见 A3.1），打印 overlay + score sidecar 路径（Batch B 产），退 10。用户看完 → `run_stage approve-review <case> <run> <stage> --actor X` 落记录 → 重跑 flow → 匹配 → advance。
- **geometry 人工校验点**沿用现有 `AWAITING_GEOMETRY_APPROVAL` + `approve-geometry`（已 durable，不用新机制）；故三开关映射：reading→AWAITING_HUMAN_REVIEW、correction→AWAITING_HUMAN_REVIEW、geometry→现有几何 approval 门。

**A3.1 新 StepStatus `AWAITING_HUMAN_REVIEW`**：
- 加进 `StepStatus` 枚举（非 TERMINAL_STOP、非 ADVANCE_OK；类 AWAITING_* 停靠态）。
- `update_state`：把它并入「设 stop_reason 但非 terminal」那支（同 AWAITING_GEOMETRY_APPROVAL/AWAITING_REREAD）。
- **谁产它**：倾向**不进 `run_one_stage` 核**（保核纯净），而在 **flow 外壳**里在 ADVANCE_OK 后据开关+durable 记录判定后自造一个 `StageOutcome(status=AWAITING_HUMAN_REVIEW,...)` 落 state。→ `run_one_stage` 语义不变，只是枚举多一个值供 flow/ state 用。**审阅需求 A-R1**：Codex 裁「flow 外壳自造」vs「传 review 开关进 `run_one_stage` 让核产」——倾向前者（核不认识"人工校验开关"这种 calling policy 细节，符合 fact≠policy）。

**A3.2 新 verb `approve-review`**：`run_stage.py` 加 `approve-review <case> <run> <stage> --actor [--note]`：读 `manifest.accepted(stage).output_hash` → `record_review(...)` → 打印。无 accepted attempt 报错。
- **state 清理（MINOR-3 采纳，对齐 geometry approval）**：新增 `mark_review_approved(run_dir, stage, ...)`——若当前 `stop_reason` 正是该 stage 的 `awaiting_human_review@<stage>` → 记 `human_review_approved` 元数据并**清该 pending stop_reason**（照 `mark_geometry_approved` 范例，避免批准后、重跑前 `status` 仍显示 pending）。重跑 flow 仍以 `review_is_current`（output_hash 复核）为**权威**放行判据（state 清理只是 UX 一致性、不替代 hash 复核）。

**A3.3 软降级（MINOR-2 采纳）**：`AWAITING_HUMAN_REVIEW` 停靠时打印的 overlay + score sidecar 路径是 **Batch B 产物**；Batch A 落地时 Batch B 可能未到 → **缺失即软降级**打印「overlay/score_vs_gt not generated yet（Batch B 未落地）」，**不阻断** durable review 停靠/`approve-review`/续跑，durable review 测试不依赖 Batch B artifact。

### A4. JUDGE_BLOCK 自动盲重抽（build 必办#1）

flow 遇 `outcome.status == JUDGE_BLOCK`（= `_verdict_outcome` 判 routable + root 是 stochastic）：
- `target = outcome.route_target`。
- **先 `invalidate(manifest, target)` + `manifest.save`**（build 必办#2/#7，见 A7）。
- 对 `target` force resample = 复用 `run_one_stage(..., force_draw=True)`（该段 draw_fn）；预算 disk-derived（同 `per_stage_draws`）——预算耗尽 `run_one_stage` 自回 QUARANTINED → flow 停退 20。
- resample 出新 attempt（无 verdict）→ 若该段是 enabled judge 段 → 新的 AWAITING_JUDGE → flow 停等主控判（退 10）。即"自动重抽减碎片，但判卷仍主控在环"。
- **非 stochastic 根**（manual→AWAITING_REREAD、deterministic→JUDGE_BLOCK_HUMAN）不进这支（`_verdict_outcome` 已分流），flow 按 A1 停靠处置。
- **defensive 兜底（MINOR-1 采纳）**：正常路径 `_verdict_outcome` 必给 stochastic root 填 `route_target`；但实现须防御 `route_target` 缺失 / target 超出 `--to` 范围 / 自动动作被显式关闭 → 这些**无法自动处理**的 JUDGE_BLOCK **退 10** + 打印人工动作（见 A8）。

### A5. geometry-auto 审计可见（build 必办#4）

- `approve_geometry`（step_orchestrator.py）加 `policy: str = "required"` 参 → 写进 `GeometryApproval.policy`（现硬编码 "required" 会误导 auto 场景）。
- flow `--geometry auto` 调 `approve_geometry(..., actor="flow:auto", policy="auto")`；auto 前先 `_render_geometry_viewer` 重渲（防陈旧）。
- `run_stage.py cmd_approve_geometry` 也线程化 `policy`（人工调默认 "required"）。
- **§8.9 口径**：`--record`（正式基线录制）+ `--geometry auto` 组合：flow 收尾时若 `run_profile in {golden}` 且 geometry 是 flow:auto 批准 → 打印告警（正式基线建议人工看 HTML）。**不硬阻**（regression/CI 无人可显式 auto）。**审阅需求 A-R2**：Codex 裁是否要对 golden+auto 硬阻或仅告警——倾向告警。

### A6. EP 布局修（build 必办#3，option A —— 抽共享函数）

**目标**：EP 无论入口都落 `<run>/EP/EP_run/`，对齐 validate_case/record_baseline。

新 `src/agent/runner.py`（或 `scripts` 侧 helper——见审阅需求）抽出 run_full_pipeline.py:315-343 的 graph-run 段为可复用函数，签名建议：
```python
def run_downstream_ep(
    *, initial_state: AgentState, epw: Path, output_dir: Path,
    ep_run_subdir: str | None, run_simulate: bool, on_event=None,
) -> dict:   # 返回 final state；内部 build_graph + SimContext + run_session(auto_approval)
```
- **run_full_pipeline** 重构成调它（`--reading-from`/`--intake-from`/`--no-simulate`/prebuilt-intake short-circuit/flat-vs-EP 布局**行为全不变**——run_full_pipeline 仍算好自己的 `output_dir`/`ep_run_subdir` 再传入）。
- **flow** 调它：`initial_state = AgentState(intake_output=<load run/5_intakeoutput/intake_output.json>, testdata_text=..., image_paths=[], reading_vector_dir=None, pipeline_out_dir=None)`；`output_dir=<run>/EP`、`ep_run_subdir="EP_run"`、`run_simulate=True`。
- **共享函数只承载 graph/session/SimContext**（MAJOR-3 采纳）：`build_graph` **lazy import**、接收已构造的 `AgentState`/`SimContext` 参数，**不吞 CLI config 解析/布局决策**（run_full_pipeline 仍自己算 `output_dir`/`ep_run_subdir` 再传入；flow 固定传 `<run>/EP`+`EP_run`）。`EP_AGENT_LLM_CONFIG` 的设定放**调用方**（run_full_pipeline 现逻辑 / flow 的 A2 run-scoped 解析）。
- **intake loader 抽共享**（MAJOR-3 采纳）：`_load_intake_from`（含 `ensure_schema_initialized()`）从 run_full_pipeline 抽到共享处（`src/agent/runner.py` 或 `state`），flow 与 CLI 共用——**flow 不裸 `IntakeOutput.model_validate_json`**（否则漏 IDD 初始化，MepOutput/BuildingSchema 反序列化会炸）。
- **审阅需求 A-R3（已裁）**：共享函数落 `src/agent/runner.py`；thread_id 建议 `f"{case}/{run}"`。**回归保真硬线**：run_full_pipeline `--reading-from`/`--intake-from`/`--no-simulate`/prebuilt-intake short-circuit/flat-vs-EP 布局（`run_full_pipeline.py:241-343`）全过回归测试。

### A7. 下游 invalidate（build 必办#2/#7）

- **flow 内**任何 force 重画/重抽 `target` 前：`invalidate(manifest, target)` + `manifest.save(run_dir)`（清下游陈旧 accepted 指针，避免复用旧 2/3/4/5）。
- **`cmd_resample` 也补**（现 `cmd_resample` 只 `force=True` 转 `cmd_run`、不 invalidate → 手动 resample 也会留陈旧下游）：resample 前 `invalidate(manifest, stage)`。**审阅需求 A-R4**：Codex 核这不会破坏现有 resample 语义（应只是补掉一个已知缺口；现有测试若假设 resample 不清下游需同步）。

### A8. 退出码（build 必办#5）

flow 返回：
- `0` = 跑到 `--to` 完成（含可选 EP+record 成功）。
- `10` = 停在人/动作检查点：AWAITING_JUDGE / AWAITING_GEOMETRY_APPROVAL / AWAITING_HUMAN_REVIEW / AWAITING_REREAD / **未能自动处理的 JUDGE_BLOCK**（MINOR-1：defensive 兜底——能自动重抽就不返回、不能则退 10 + 打印人工动作）。
- `20` = 终止编排停：QUARANTINED / DETERMINISTIC_DEFECT / HUMAN_REDRAW_REQUIRED / JUDGE_BLOCK_HUMAN。
- `30` = EP / record 失败（含 `--record` 遇 pending 未加 `--record-partial`）。

（现有 per-stage verbs 保留 `0/2` 语义不动——`flow` 是新 verb，退出码独立。**审阅需求 A-R5**：是否把老 verb 也升级到新码表？倾向**不动**老 verb 保兼容，只 flow 用新码表。）

---

## 3. Batch B —— gt 权威 judge evidence

> 全部 judge-side / tooling-side（读 gt via load_gt）——**gate①/执行器绝不 import**（`tests/test_gt_discipline.py` 机械守，build 必办 gt 铁律）。落点：judge 包 + `scripts/tool_scripts/`。

### B1. `score_*_vs_gt` 接进 judge_packet 当机读 evidence（build 必办#1/#2）

**⚠️ MAJOR-1 采纳（硬约束）**：sidecar/overlay 一律**从 accepted attempt 的 `attempts/NNN/output.json` 生成，绝不读 mutable flat stage 目录**（`0_reading/*_view.json`、`1_correction/correction_geometry_snapped.json` 可能被 judge 前手改 → 落旧 attempt 目录却对应新 flat 文件，破坏"gt evidence = accepted attempt 证据"语义 + 让 A3 人工复核绑错对象）。sidecar 里写 `stage`/`attempt`/`output_hash`（= `manifest.accepted(stage).output_hash`）/`source="attempt_output"`；复用已存 sidecar 前**必校验 hash 一致**。

- attempt `output.json` 的形状：**0_reading** = `{stem: view_dict}`（`_draw_reading` 返回 dict）；**1_correction** = `CorrectedGeometry` dump（`_draw_correction` 返回 geom）。故 scorer 需能吃**内存对象/attempt output**，不只 glob 目录：
  - 0_reading：从 attempt output 的 `{stem: view_dict}` 逐 floor 调 `score_floor(view_dict, gt, floor_name)`（`score_reading_dir` 的 per-view 逻辑复用，喂内存 dict 而非重 glob flat 目录）。
  - 1_correction：调 B3 correction scorer 吃 attempt output 的 `CorrectedGeometry` dump。
- `_judge_packet`（run_stage.py，已在 judge 路径内 import gt）对 0/1 段：落 sidecar `attempts/NNN/score_vs_gt.json` + packet 加 `"score_vs_gt": "<path>"` + `"score_criteria": [...]`（见 B2）。
- 无 gt（`has_gt(case)` False）→ sidecar 省略、packet 标 `"score_vs_gt": null`（judge 降级为纯看图，诚实占位）。
- **补测（build 必办#8）**：resume 后篡改 flat stage 文件，packet sidecar 仍等于 accepted attempt（hash 绑定验证）。

### B2. 阈值→criterion 映射（build 必办#1/#2 —— **别用数字分替 checklist**）

新 `src/agent/judge/score_policy.py`：把 FloorScore（或 correction score）→ **suggested criterion evidence** 列表（机读，进 packet），**不**改 verdict schema、**不**自动提交 verdict。
```python
# 放宽容差为主判据（复用 scorer 的 DEFAULT_WALL_TOL_M=0.30 / DEFAULT_WIN_CENTRE_TOL_M=0.40）
def reading_score_criteria(scores: dict[str, FloorScore]) -> list[dict]:
    # 每条 {criterion, suggested_status(pass/minor/severe), evidence(机读串: hit/total + max_offset + extras)}
    # 例：walls_complete: 所有 floor wall_hits==total 且 无 extra → pass；有 miss → severe；仅 extra(过度分割) → minor/severe 按数量
    #     windows_placed: window_hits/total ≥ 阈值 → pass；否则 minor/severe
    #     no_oversplit: extra_vwalls+extra_hwalls==0 → pass；否则 minor/severe（数量分级）
```
- 阈值集中此模块常量（放宽口径：wall 命中看 0.30m 容差内、窗看中心 0.40m；过度分割看 extra 计数）。
- **packet 里叫 `score_criteria`（suggested evidence）**，note 明确「这是机读 gt 对账建议，**StageVerdict 仍由你（主控）裁决权威**，以对账为主、看图为辅、容差已放宽」。
- **build 必办#2 硬线**：不得把 suggested_status 直接写进 `StageVerdict`（`extra="forbid"`）当自动判卷；主控仍手写 verdict.criteria。sidecar/score_criteria 只是 evidence。

### B3. J1 correction scorer 适配器（build 必办#3）

新 `src/agent/judge/correction_score.py`（judge-side，读 gt）：
- 吃 **accepted attempt output 的 `CorrectedGeometry`**（MAJOR-1：非读 flat `correction_geometry_snapped.json`）。cells 带 rect、windows 带 facade+along-facade span。
- 抽 **interior partition lines**（cell rect 内边非 footprint 边界）+ **窗 facade span**（world 坐标），复用 `reading_score._match_lines`/`_match_windows` + gt 派生（`derive_gt_walls`/`derive_gt_windows`）。
- 返回同构 FloorScore（或等价），供 B2 映射。
- **floor-name 映射（⚠️ MAJOR-4 采纳，硬约束）**：`CorrectedGeometry.Floor.name` 是任意字符串，现有真实样本**并存** `"Floor 1"/"Floor 2"` 与 `"F1"/"F2"`；gt 用 `"Floor 1"/"Floor 2"`。**不得只按字符串相等匹配**——映射顺序 = ① 精确名称 ② 数字序号（`F1`/`1F`/`Floor 1` 抽数字对齐 gt floor 序）③ 兜底按 `z_floor`/列表顺序。**未匹配的 floor 写进 sidecar evidence（不静默空分）**，否则 J1 scorer 在 sm21 `F1/F2` run 上假阴性/无 evidence。
- **容差 caveat（build 必办#4）**：gt=clear-space bbox、correction 常 centerline 偏移；但 envelope-facade-priority 已把 footprint 收成 gt 外包（[0,15]×[0,8]），内隔墙应落容差内。0.30m wall_tol 吸收残余。**不把该系统偏移显示成硬错**。

### B4. 产物↔gt overlay（0/1，build 必办#4 —— **共享 metric transform，不 raster 合成**）

新 `scripts/tool_scripts/render_overlay.py`（judge-side tooling，读 gt）：
- **一个共享 metric→pixel 变换**（统一 scale/origin/margin），把 **gt**（zone rects + 窗 spans，底色/灰）与**产物**（reading strokes / correction cells，红）画进**同一张** PNG。**不**分别渲两张再叠 raster（现 `render_gt`/`render_vector_to_png`/`render_corrected_geometry` 各自 transform 不一致，会错位）。
- reading overlay：reading strokes 叠 gt；correction overlay：correction cells 叠 gt。**产物一律取 accepted attempt output**（MAJOR-1，与 B1 sidecar 同源，别读 flat）。
- **容差标注**：gt clear-space vs correction centerline 的系统偏移用**淡色/注记/图例**表达为**容差说明**，不画成硬红错。
- `_judge_packet` 产 packet 时调它 → PNG 落 attempt 目录 → packet `"overlay": "<path>"`；同一 overlay 既喂 judge（数据层佐证）又喂人工校验（A3 停靠时打印给用户看视觉 delta）。
- **审阅需求 B-R1**：Codex 裁 overlay 变换复用点——倾向新建一个纯坐标变换 util（`scripts/tool_scripts/_overlay_transform.py` 或复用某现有渲染器的 transform 抽出），gt+产物共用同一函数。

---

## 4. Batch C —— `new_case_guide.md` 重写（Claude 亲手，A+B 落地后）

6 步 SOP + 三层叠加门（gate①→judge②→人工校验）+ gt 权威判卷（放宽容差为主/看图辅）+ overlay + `flow` 命令矩阵。**工具落地后写、描述真工具不写 vaporware**（§8.9）。不派 Codex。

---

## 5. 测试（Codex 执行时随批产，§6 + build 必办#8）

**Batch A**：
1. `flow --judge off --geometry auto` 在已有 0_reading 的 run 上跑通 1→5，产全 attempts/manifest/renders/viewer，无 case 根污染；退 0。
2. `flow --judge stop` 停在首个 AWAITING_JUDGE、产 judge_packet、**退 10**；提交 verdict 后重跑 flow 续到下一检查点。
3. `--geometry auto` 自动 approve-geometry（**policy="auto"/actor="flow:auto"** 审计字段）；`--geometry required` 停靠退 10。
4. **durable 人工校验**：`--review correction` 下 JUDGE_PASS 后停 AWAITING_HUMAN_REVIEW 退 10；`approve-review` 后重跑续；resample 改 output_hash → 复核失效重停。
5. **JUDGE_BLOCK 自动重抽**：注入一个 routable-stochastic-root verdict → flow 自动 invalidate 下游 + resample target；deterministic-root → JUDGE_BLOCK_HUMAN 退 20。
6. **下游 invalidate**：force resample stage-N 后下游 accepted 指针被清（manifest 断言）；`cmd_resample` 同。
7. **EP 布局**：A6 抽的 `run_downstream_ep` 单测 + run_full_pipeline `--reading-from`/`--intake-from` 行为不变回归；flow `--with-ep` EP 落 `<run>/EP/EP_run/eplusout.end`。
8. 退出码全码表（0/10/20/30）+ `--record` pending 拒绝（无 `--record-partial`）退 30。

**Batch B**：
9. scorer sidecar 进 packet（0_reading + 1_correction）；`score_criteria` 是 evidence 非 verdict（断言不落 StageVerdict）。
10. J1 correction scorer 对 sm21 correction_geometry_snapped 打分（interior walls + 窗）合理。
11. overlay 用共享 transform（gt+产物同图、坐标一致性断言）。
12. **gt 隔离**：`tests/test_gt_discipline.py` 仍绿（新 scorer/overlay/policy 全 judge-side，gate①/执行器无 import）。

**回归**：全量 pytest（当前 **395 绿 + 9 strict xfail**）零 golden 改动（flow/EP/scorer 都是**新增**，不动 gate①/judge/verdict 语义/run_pipeline/契约——§5 scope 边界）。

---

## 6. 明确不做（scope 边界，§5 + §8.7）

- 不接 LLM/VLM judge_fn（judge 保持主控在环）。`--judge off` 只是不判、非自动判。
- 不改 gate①/judge/verdict 语义、不改 `run_pipeline`、不改 CorrectedGeometry/契约、不改 reading 子代理协议。
- **J23 + `score_geometry_vs_gt` + stage-3 门 reorder + 内核能力根路由 = P2**（不在本简报）。
- MEP judge(J4) 保持禁用。污染硬隔离仍 prompt 级（backlog）。
- 保留所有现有 per-stage verbs 不动，`flow` 是组合层。

---

## 7. 审阅需求汇总（Codex 逐条裁 + 补漏）

- **A-R1**：`AWAITING_HUMAN_REVIEW` 由 flow 外壳自造（倾向，保 `run_one_stage` 核纯净/fact≠policy）vs 传 review 开关进核。
- **A-R2**：golden + `--geometry auto` → 硬阻 vs 仅告警（倾向告警）。
- **A-R3**：EP 共享函数落点（`src/agent/runner.py` 倾向）+ flow 侧 intake 加载复用 `_load_intake_from`（挪共享 vs 内联）。
- **A-R4**：`cmd_resample` 补 `invalidate` 是否破坏现有 resample 语义/测试预期。
- **A-R5**：老 verb 是否也升级新退出码表（倾向不动，仅 flow 用）。
- **B-R1**：overlay 共享 metric transform 的复用/抽取点。
- **F-额外**：durable 人工校验绑 `output_hash`（manifest.StageRecord.output_hash）是否够稳（vs 另算 digest）；`--from auto` 起点解析是否有边角（已判但下游被 invalidate 的情形）。
- **总**：批次切分（A 先 B 后）是否合理；有无 build 必办#1-#8 未覆盖处；有无破坏 395 绿/golden 的隐患。

---

## 8. Codex 审要求

1. 逐条裁 §7 审阅需求 + §2/§3 机制方案（尤其 **A3 durable checkpoint 新机制** + **A6 EP 共享函数保真** + **B2 scorer→criterion 不越权**）。
2. 核 build 必办#1-#8（§8.11）全落进本简报、无遗漏、无越界（不动 run_pipeline/契约/gate①语义）。
3. 给 APPROVE / APPROVE-WITH-CHANGES / REWORK + 必办清单。落 `logs/review/review/2026-07-02_flow_p1_execution_brief_review.md`。

---

## 9. 定案（Codex 审 = APPROVE-WITH-CHANGES，6 条全采纳 —— 本简报即 P1 build 权威）

审阅报告：[`review/2026-07-02_flow_p1_execution_brief_review.md`](../review/2026-07-02_flow_p1_execution_brief_review.md)。Claude 裁决 = 6 条全采纳（均真问题、指向正确），已回改进 §2/§3：

1. **MAJOR-1**（→ §3 B1/B3/B4）：scorer sidecar/overlay **从 accepted attempt `output.json` 生成 + 写 `output_hash`/`source`**，绝不读 mutable flat stage 目录；复用前校验 hash。
2. **MAJOR-2**（→ §2 A1 可续性）：`--from auto` **manifest-first**，state 只作 pending 提示；被 invalidate 的下游即使 state 显 pass 也必重跑。
3. **MAJOR-3**（→ §2 A2/A6）：flow `--with-ep` 前解析 **run-scoped LLM 配置**（`--llm-config`>`<run>/llm.yaml`>`<case>/llm.yaml`>全局）+ `--epw` 默认 + **抽共享 intake loader**（含 `ensure_schema_initialized`）；共享函数只承载 graph/session/SimContext、`build_graph` lazy import。
4. **MAJOR-4**（→ §3 B3）：correction scorer **floor-name 映射**（精确名 > 数字序号 > z_floor/序兜底）+ 未匹配写 evidence。
5. **MINOR-1**（→ §2 A4/A8）：未能自动处理的 `JUDGE_BLOCK` **defensive 退 10** 兜底。
6. **MINOR-2 + MINOR-3**（→ §2 A3）：Batch A 对 Batch B artifact **软降级**；`approve-review` 后新增 `mark_review_approved` **清 pending**（output_hash 复核仍为权威放行）。

**§7 审阅需求裁决（Codex 与我的倾向一致，全采纳）**：A-R1=flow 外壳自造 `AWAITING_HUMAN_REVIEW`（核不认 review 开关）；A-R2=golden+auto 仅告警不硬阻；A-R3=共享函数落 `runner.py`、intake loader 抽共享、thread_id=`case/run`；A-R4=`cmd_resample` 补 invalidate（改旧错误行为、同步更新依赖旧行为的测试）；A-R5=老 verb 不升级退出码（仅 flow 用新码表）；B-R1=新建纯坐标 transform util（`scripts/tool_scripts/_overlay_transform.py`）、gt+产物同 canvas；F=`output_hash` 绑定够稳。

**⟹ 本简报（含以上回改）= P1 build 权威指令**。下一步 = **派 Codex 执行 Batch A**（编排 harness）→ Claude 大节点全面审（自跑 pytest + 逐行 diff）→ 再派 Batch B → Claude 亲手 Batch C（new_case_guide 重写）。
