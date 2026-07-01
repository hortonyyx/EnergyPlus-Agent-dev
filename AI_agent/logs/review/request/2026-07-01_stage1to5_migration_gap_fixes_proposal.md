# 方案：Stage 1–5 迁移缺口修法（item ④，综合 Codex 0-5 迁移审计）

> 状态：**待 Codex 审**（2026-07-01）。Claude 出方案，按 [[codex-execution-protocol]] 派 Codex 审 → Codex 执行 → Claude 全面审。
> 输入 = Codex 独立全 0-5 迁移审计 `logs/review/2026-06-27_full_0to5_migration_audit_codex/codex_findings.md`（80 条：✅64/❌4/⚠️7/🗑5）。
> 关联：plan.md N1f（reading 先做透→推 1-5）、A8/Phase A"让弱可见"哲学、[[sm21-ep-anchor-two-real-defects]]（schedule 段错族）、[[sm24-nonsquare-first-run-2026-06-24]]（走廊过度分区 C2）。

---

## 0. 一句话

Codex 的 0-5 审计是 **2026-06-27 快照**，之后落地了 `6.27_ReadingImageLocalUncaptured` / `ScaffoldFullRestore` / `6.30_PhaseA` / `7.01_A8` 一串。
Claude 已对**当前树**逐条核实 11 条开放 finding（❌4+⚠️7）：**stage-0 那 4 条冲突全已 stale**（前几轮修掉），两条最重的 ⚠️（S1-10/S1-12）**归 Phase B**（本轮已 defer）。
本轮实修 = 用户选定的 **S4-07 + S23-16 + S1-09 + S1-18**。

---

## 1. 全量триаж（对当前树核实，非 06-27 快照）

| Finding | 裁定 | 核实证据 |
|---|---|---|
| **S0-04** facade_axis_note 世界轴 | ✅ stale | `guide.md` grep 无 `facade_axis_note`（`6.27_ReadingImageLocalUncaptured` 删）|
| **S0-05** scale_origin 世界坐标 | ✅ stale | `guide.md` grep 无 `scale_origin` 世界坐标 |
| **S0-15** uncaptured 必须非空 | ✅ stale | `guide.md:358/385` 已改"a clean drawing may be []"，与 schema 对齐 |
| **S0-26** correction §3 verbatim | ✅ 实质 stale | `pipeline.py` grep 无"§3/verbatim/facade_axis"；仅残留无害的 `reading_summary.md` REFERENCE 注入（不 load-bearing）|
| **S1-10** 非矩形房间 vs 矩形 cell | ⏸ Phase B | correction 矩形 vs kernel polygon-native 张力 = 双通道/polygon 支持 |
| **S1-12** derive_facade_frame 未接线 | ⏸ Phase B | Phase B §3 明确项；接核前对 gt 验 E/W sign（[[derive-facade-frame-unwired-ew-sign-trap]]）|
| **S23-16** InterZone advisory vs blocking | 🔴 本轮 | 见 §2.2 |
| **S4-07** people activity schedule 未设门 | 🔴 本轮 | 见 §2.1 |
| **S4-12** TBD/etc 占位禁令无门 | ⚪ 用户本轮不选 | 记 backlog |
| **S1-09** 走廊几何规则未承载 | 🟡 本轮 | 见 §2.3 |
| **S1-18** WWR residual 自检未实现 | 🟡 本轮 | 见 §2.4 |

---

## 2. 本轮修法（逐 finding）

### 2.1 S4-07 — people activity-level schedule 引用门（❌ 真·EP-fatal 缺口）

**病**：`src/validator/checks/mep.py::_load_refs` 对 `_LOAD_TYPES=(PEOPLE,LIGHTS,ELECTRICEQUIPMENT)` 只查 `obj.fields[2]`（People 的 *Number of People Schedule Name*）。
People 的 *Activity Level Schedule Name* 是更深字段（标准 IDF 约 `fields[9]`），**完全没被验**。若它引用未定义 schedule → EP fatal（同 [[sm21-ep-anchor-two-real-defects]] 不完整 schedule 段错族）。
authoring.md:120 明确要求它"easy to forget — do not omit"，但 prompt 要求 ≠ 代码门。

**修（要求，非实现细节）**：让 mep gate 覆盖 People 的 activity-level schedule 引用 → 未定义即 `add_fail`（INVARIANT，进 `mep.load_to_schedule` 或新 `mep.people_activity_schedule`）。

**给 Codex 的实现方向（自选更稳的）**：
- **A（点修，推荐起手）**：`_load_refs` 里对 `PEOPLE` 额外取 activity-level schedule 字段核 `sched_names`。**风险=字段索引脆弱**——activity-level 的 `fields[N]` 依赖 LLM 授权字段数/顺序。Codex 须先确认 `idf_fragments` parser 如何切 People 字段、activity-level 的稳定 index，或用"名字含 Activity/最后一个非空 schedule-typed 字段"启发式。**审阅需求**：Codex 自报字段定位是否稳、是否需 fixture 坐实。
- **B（泛化，备选）**：把 gate 从"只查 fields[2]"升级为"扫 load 对象所有 *schedule-typed* 字段核定义"——但 parser 无 schema map、非 schedule 字段可能误撞 schedule 名。除非有稳的 schedule-typed 字段清单，否则**别做 B**（假阳性风险 > 收益）。
- 已有 `mep.schedule_type_refs` 门（authoring.md:88）只管 schedule→type-limits，不管 load→activity-schedule，二者不重叠。

**测试**：加 fixture — People 带一个引用未定义 activity schedule → 门 fail；正常 case → pass。守 sm21 golden 不动（sm21 activity schedule 应已定义）。

### 2.2 S23-16 — InterZone advisory(run_pipeline) vs blocking(check_kernel) 口径一致（⚠️ 可见性/口径，非正确性洞）

**已核实的全貌**（重要，避免误判为正确性洞）：
- `run_pipeline`（`pipeline.py:861-869`）拿 InterZone `kernel_issues` 后**只 `logger.warning` + 落 `2_modelling/kernel_gate_report.json`、照常出 IntakeOutput**；只有硬 build error（`bg is None`）才 raise。
- `check_kernel`（validate_case 路径）把同样 InterZone 问题当 **blocking 不变量**。
- **下游 MCP workflow 门真的硬 block**：`src/mcp/tools/workflow.py:170-185`（export）/ `:244+`（run_simulation）—— `pair_issues` 非空即 `success=False`"IDF not accepted"。**∴ 破损几何到不了 EP**，run_pipeline 的"advisory here + downstream re-checks"注释属实、是真纵深防御。
- 但 `record_baseline`/`report_assembly`/execution 层 grep **都不读** kernel_gate_report/kernel_issues → InterZone kernel 问题对 run 报告/run_state **不可见**，run 仍显"绿"、破损静默越过 intake 交接边界、推迟到下游才炸。这正是 Phase A/A8 要治的"pipeline 绿掩盖弱"反模式。

**裁决（Claude 建议，请用户/ Codex 确认）**：
- **不让 run_pipeline 硬 raise**（保产物可检视——一 raise 就出不了 geometry viewer/report，坏调试）。
- **但把 InterZone kernel 问题升级为 run 的机器可读 blocking-severity 信号**：沿用 A8/Phase A 的 `run_profile` 口径——
  - **exploratory/dev** = **flag/可见**（进 orchestration_state / run_state / report evidence index，标 blocking-severity，令 run_state 不再是 clean/ADVANCE_OK；run 续、产物照出）。
  - **golden/regression** = **fail-closed**（沿用 `pipeline.py:542` evidence_debt 的 `run_profile` fail-closed 范式 raise，令 golden baseline 不可能带破损 InterZone 录进去）。
- 目标 = **让 run_pipeline 的 severity 分类与 check_kernel 对齐**（都视 InterZone 为 blocking-severity），只是**运行时控制流**在 exploratory 下仍 advisory（可见但不阻断产物）。

**给 Codex 的实现方向**：
- run_pipeline 已有 `run_profile` 入参（A8 引入）——复用。
- InterZone `kernel_issues` 非空时：exploratory → 写进 run_state/report 的 blocking 信号（找 evidence_index / run_state 现有的 blocking 通道，别新造）；golden/regression → 与 evidence_debt fail-closed 并列 raise。
- **审阅需求**：Codex 自报 (a) run_state/evidence_index 里挂 InterZone blocking 的最小接线点；(b) 是否触及现有 2 个 legacy golden（sm20/sm21）——若它们本无 InterZone 问题则不受影响，须实测确认。

**明确不做**：不改 InterZone 判定逻辑本身（`validate_interzone_surface_pairs` 不动）；不动下游 MCP workflow 门（已正确 block）。

### 2.3 S1-09 — 走廊几何规则（❌ 部分承载，低优先）

**病**：旧 `phase2/rules.md:184-187` 有专门走廊几何规则；当前只有 A4 priors 的走廊宽/高（`office_corridor_w`/`corridor_net_h`）+ roles 词表 corridor + A3 通用 merge/split。缺"走廊作连续循环空间、别当多房过度分割"的专门 correction 规则。接 [[sm24-nonsquare-first-run-2026-06-24]] 的 L 走廊被拆 2 区（C2）。

**修（要求）**：在 correction **A3_arbitration.md**（拓扑仲裁）补一条走廊处置规则：走廊/circulation 空间默认作**连续单一区**，除非有门/隔墙实体分隔才拆；相邻矩形碎片属同一开敞循环空间时倾向合并而非过度分区。**纯 prompt/prose 规则**（correction 做拓扑仲裁的语义活，符合 0-5 分工——geometry 仍代码算）。

**边界**：
- **不碰几何内核**（区合并/air-boundary 的**确定性**实现 = C2 能力升级，归中期 capability，不在本轮）。本轮只补 correction 侧的语义仲裁 prose，降低"走廊被识/校成多房"的概率。
- 与 A3 现有 `reference_or_identity_ambiguity`"never merge on doubt"**不冲突**：走廊规则是"识别为同一循环空间时倾向单区"，仍要证据支撑、不无脑合并。**审阅需求**：Codex 核这条与 A3 现有反-无脑-合并条款的措辞是否打架，给消歧。

### 2.4 S1-18 — WWR residual 自检（❌ 文档有码无，低优先）

**病**：`A0_contract.md:291` 把 `wwr_residuals`（within `WWR_REL_TOL`）列为 soft check，但 `src/validator/checks/correction.py` 未实现 → 文档承诺 vs 代码落差（doc-honesty 问题）。

**修（要求，二选一，请 Codex 权衡后建议）**：
- **A（诚实降级，推荐·最省）**：把 A0 的 `wwr_residuals` soft check 标注为**未实现占位**（类比 `mep.reasonability_bands` 的 NOT_APPLICABLE 显式占位），或在 correction gate 里加一个 `correction.wwr_residuals` = `NOT_APPLICABLE`（"deferred until WWR evidence richer"）占位，让"文档说有的门"在代码里可见其未实现状态。**不假装实现**。
- **B（最小实现）**：仅当 reading/correction 证据里有立面窗面积 + 立面面积时算 WWR residual、超 `WWR_REL_TOL` 则 warn（soft、不 block）；证据缺就 NOT_APPLICABLE。工作量大于 A、且多数 case 无干净 WWR 证据 → 实益有限。
- **Claude 倾向 A**（消 doc↔code 落差最干净），把真 WWR 校验推到有 WWR 证据链的后续（可挂 Phase B 双通道）。**审阅需求**：Codex 确认 A 是否漏了 A0 里其他"列了没实现"的 soft check（`facade_area_residuals`/`area_residuals` 同段，一并核诚实性）。

---

## 3. 测试 / golden 影响预案

- **S4-07**：新增 mep fixture 测试；sm21/sm20 golden 若 activity schedule 本已定义则不动（须实测）。
- **S23-16**：exploratory 下只加 flag 信号，现有测试若断言 run_state=clean 的破损-InterZone case（应无）需查；golden/regression fail-closed 走 `run_profile`、legacy golden 祖父化（同 Phase A 口径）。**须实测两个 legacy golden 不被误 block。**
- **S1-09 / S1-18-A**：纯 markdown / 占位改，无 Python 逻辑动，不动 golden。
- 全量 `pytest`（当前 374 绿 + 9 strict xfail）作回归基线；Codex 执行后 Claude 大节点全面审（自跑 pytest + 逐行 diff）。

## 4. 本轮明确不做（记 backlog / 归他处）

- **S4-12**（TBD/etc 占位禁令门）：用户本轮不选，记 backlog（纵深防御，非急）。
- **S1-10 / S1-12**（非矩形房间、derive_facade_frame 接线）：归 **Phase B**（双通道 + 算术下沉 + facade 变换接线），已 defer。
- **走廊/开敞空间确定性区合并 + air-boundary**（C2）：归中期 capability，非本轮（S1-09 只补 correction prose，不碰内核）。
- **stage-0 四条 stale 冲突**：已被前几轮修掉，无动作。

## 5. 推进

1. **派 Codex 审本方案**（`mcp__codex__codex` xhigh，落 `logs/review/review/2026-07-01_stage1to5_migration_gap_fixes_review.md`）。
2. Claude 裁决（不盲从）→ 派 Codex 执行器（简报含各 finding「审阅需求」自报点）。
3. Claude 大节点全面审（pytest + 逐行 diff + 必要时 sm21 冒烟）。
4. 更新 plan.md N1f / decision_log / contracts（memory↔文档同步）。

---

## 6. 定案（Codex 审 APPROVE-WITH-CHANGES 全采纳，2026-07-01）

审轨 `logs/review/review/2026-07-01_stage1to5_migration_gap_fixes_review.md`（0 BLOCKER/3 MAJOR/3 MINOR）。Claude 全采纳，以下 delta 超越 §2 对应措辞：

**S4-07（MAJOR1 采纳）**：不用裸 `fields[9]`。执行口径 =
- 对 `PEOPLE` 从 `obj.raw` 读 `Activity_Level_Schedule_Name`（eppy 字段名访问，`idf_fragments` 保留了 raw 对象）；
- raw 不可用时才回退 `obj.fields[9]`（正常 People 布局稳定在 index 9：drop 对象类型 token 后 activity 落在 sensible-heat-fraction 之后）；
- **blank/missing activity schedule 也 fail**（非仅未定义引用）；
- 报在 `mep.load_to_schedule`（除非确需新 check id）；
- fixtures：missing activity schedule / undefined activity schedule / clean(primary+activity) 三例。
- 确认 `mep.schedule_type_refs` 不覆盖此项（它只查每个 Schedule:Compact 的 type-limit 引用）。

**S23-16（MAJOR2 采纳，纠正原 §2.2 plumbing）**：不造新 run_state 信号。**`run_state` 由编排账本派生、本身不载 gate blocking**（`report_assembly.py:228-287`），故可见性走既有 gate report 通道，不 overload run_state。执行口径 =
- `materialize_kernel_geometry()` 后（或其内）用 `check_kernel(bg, interzone_issues=kernel_issues)` 产 `2_modelling/kernel_checks.json`；若给 `check_kernel` 加 `run_profile`，只设报告字段、**`kernel.pairing_gate` 仍是 invariant**；
- `run_pipeline` 在写完 kernel 报告后：`run_profile in {golden,regression}` 且 `kernel_issues` 非空 → raise（对齐 evidence_debt fail-closed）；exploratory/dev 照写产物续行；
- 报告可见性复用 `summarize_gates()` / `build_evidence_index()`（`kernel.pairing_gate` 会作 blocking-severity 进 `E:gate:...` 索引 + `blocking_summary`），**不新造 InterZone sidecar 词表**；
- 测试：① 注入 InterZone 问题 + exploratory → 证 gate 报告/evidence index 有 `kernel.pairing_gate` blocking-severity 且产物仍在；② golden/regression fail-closed 测试。
- legacy 锚点不受影响（sm20/sm21 clean anchor 的 `kernel_checks.json` gate issues 为空，Codex 已核 file:line）。

**S1-18（MAJOR3 采纳，扩范围）**：不止 WWR。A0:291 一行承诺 `facade_area_residuals`/`wwr_residuals`/`area_residuals`/`unsupported_count_by_severity` 四项、代码全无。执行 = 加 `correction.facade_area_residuals` / `correction.wwr_residuals` / `correction.area_residuals`（+ 视情 `correction.unsupported_count_by_severity`）为显式 `NOT_APPLICABLE` cross-check 槽，message="deferred until evidence is richer"（对齐 `mep.reasonability_bands`，机器可见优于纯 prose 降级）。

**S1-09（MINOR1 采纳）**：A3 走廊措辞用 Codex 给的保护版（须保住"never merge on doubt"）：
> Corridor/circulation identity: if adjacent corridor fragments are supported by continuous circulation evidence (same label/use, open passage, continuous centerline/width, and no physical wall/door partition between them), prefer one continuous corridor zone. Do not merge across a drawn wall, door-controlled partition, fire/stair/core boundary, floor break, or unresolved identity ambiguity; when evidence is insufficient, keep distinct cells or mark `unsupported` rather than merging on doubt.

**执行序（MINOR3 采纳）**：① S4-07（+MEP fixtures）→ ② S1-09 / S1-18（doc/占位）→ ③ **S23-16 最后**（触 run/report 语义、要全量回归）。S23-16 后跑全量 `pytest`。

**S1-12 deferral 补注（MINOR2 采纳）→ 记 Phase B backlog**：Phase B 任务须点名生产调用点 + E/W sign 测试，非仅"接 derive_facade_frame"。
