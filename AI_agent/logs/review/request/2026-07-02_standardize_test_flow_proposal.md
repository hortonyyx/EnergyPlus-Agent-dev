# 规范跑测流程：单一 anchor-aware 端到端编排 `flow` —— 方案

> 状态：**方案待 Codex 审**（2026-07-02，Claude 出）。用户定「先规范跑测流程，再用规范后流程重跑 sm21」。
> 缘起：2026-07-01 sm21 双 Sonnet run 我**抄了近道**（run_pipeline 直连 + run_full_pipeline --intake-from），跳过了 judge②/attempts/3D viewer/report → 用户三问（没 judge / 产物不全 / 无 3D+report）。根因 = **没有单一 anchor-aware 编排命令**，正规流程碎成 ~15 条命令，我图快绕开。
> 关联：new_case_guide（两条路径）、run_stage.py（逐段编排器）、record_baseline.py（report）、run_full_pipeline.py（EP，布局坑）、[[pipeline-0-5-refactor-status]]。

---

## 1. 问题（现状实测）

跑**一个自包含 run 的完整正规流程**（judge-in-the-loop + 全产物 + 3D + report + EP），现在要人肉串 ~15 条命令：

```
run_stage run <c> <r> 1_correction → run_stage judge …1_correction --verdict v.json → [resample?]
run_stage run <c> <r> 2_modelling  → judge → run_stage run <c> <r> 3_split_pairing → judge
run_stage approve-geometry <c> <r> --actor …          # 人工几何门
run_stage run <c> <r> 4_mep → judge → run_stage run <c> <r> 5_intakeoutput → judge
python run_full_pipeline.py <c> --intake-from <r>/5_intakeoutput/intake_output.json …   # EP（布局坑）
python record_baseline.py <c> <r> --date … --orchestrator …                            # report
```

**三个痛点**（2026-07-01 监控实测）：
1. **碎片化**：~15 条命令、每段 run→judge→可能 resample 手动切换，极易漏步或抄近道（我就抄了）。
2. **布局接缝**：`run_full_pipeline` 的 EP 落盘随入口 flow 不一致（`--reading-from` 设 `EP_run`、`--intake-from` 不设），且默认把 0-5 写 case 根而非 run 目录 → 需手工对齐 `<run>/EP/EP_run`（validate_case/record_baseline 硬期望这个布局）。
3. **无单一入口**：judge-in-the-loop（run_stage）、EP（run_full_pipeline）、report（record_baseline）三工具割裂，没有「一个 run 从头到尾」的命令。

**note**：judge② = 主控 Agent 提交 `StageVerdict`（`judge_fn` 可插拔、dev 期主控即 judge）——这是**人/主控在环**，故规范流程**不是全自动 one-shot**，而是「一条命令推进到下一个 actionable 检查点（judge / 几何审）」+ 可续跑；regression 档（judge off）才是真 one-shot。

---

## 2. 设计：在 `run_stage.py` 加 `flow` verb（复用全部现有机制，零重写核心）

**不新建脚本、不改编排核**（`run_one_stage`/`submit_verdict`/`validate_case`/`record_baseline` 全复用）。加一个**可续的编排 verb** `flow`，把逐段循环 + 检查点停靠 + EP + report 串成一条命令。

```
python scripts/tool_scripts/run_stage.py flow <case> <run> \
    [--from 1_correction] [--to 5_intakeoutput] \
    [--judge stop|off] [--geometry auto|required] \
    [--with-ep] [--record --date <ISO> --orchestrator <model>] \
    [--run-profile exploratory|dev|golden|regression]
```

### 2.1 循环逻辑（复用 `run_one_stage` + manifest 驱动）
从 manifest 当前位置起，对 `_STAGES`（1_correction..5_intakeoutput）依次：
- 调现有 `run_one_stage`（= cmd_run 的核心）→ 得 `StepOutcome`。
- **`ADVANCE_OK`**（DETERMINISTIC_PASS / JUDGE_PASS）→ 自动进下一段。
- **`AWAITING_JUDGE`** → 产 `judge_packet.json`（现有 `_judge_packet` + 渲染）→ **停**，打印 packet 路径 + 提示 `flow` 会在 `judge` 后续跑。judge 模式：
  - `--judge stop`（默认，judge-in-the-loop）：停下等主控 `run_stage judge … --verdict`；我提交后**重跑 `flow`** 自动续（manifest 记住位置）。
  - `--judge off`（regression/gate①-only）：不停 judge，gate① 过即 advance（等价当前 DETERMINISTIC_PASS 路径；judge_enabled=False policy）。
- **`AWAITING_GEOMETRY_APPROVAL`** → 产 3D viewer（现有 `_render_geometry_viewer`）：
  - `--geometry required`（默认，人工门）：停下等 `approve-geometry`。
  - `--geometry auto`：自动 `approve-geometry`（actor=`flow:auto`，绑 digest 不变式）→ 续跑（**用户 2026-07-01「跳过我审、直接过」即此档**）。
- **`AWAITING_REREAD`**（reading 被判不可恢复）→ 打印现有 reread 协议 + 停（reading 由子代理跑、不在 flow 自动化范围）。
- **terminal_stop**（QUARANTINED / DETERMINISTIC_DEFECT / HUMAN_REDRAW / JUDGE_BLOCK_HUMAN）→ 停 + 非零退出。

### 2.2 收尾（5_intakeoutput 过后）
- `--with-ep`：跑 EP **进 `<run>/EP/EP_run/`**（见 §3 布局修）。
- `--record --date --orchestrator`：调现有 `record_baseline` → `_run/baseline.json` + `report/REPORT.md`（GEN 区代码刷、AGENT 区留主控叙事）。

### 2.3 reading 来源
- 默认**复用现有 `<run>/0_reading/`**（本次场景：Sonnet 子代理已产好）。`flow` 从 `--from 1_correction` 起。
- `--from 0_reading`（可选）：若 reading 缺，reading 是主控子代理协议（非 flow 自动化）——flow 遇 0_reading 缺/未过则停 + 打印子代理 reading 协议（复用现有 reread 协议文案），不在 flow 内起子代理。**审阅需求 F1**：Codex 定 0_reading 在 flow 中的处置（停靠打印协议 vs 直接要求先手工产 0_reading）。

---

## 3. EP 布局修（接缝 2）

**目标**：EP 无论入口都落 `<run>/EP/EP_run/`，对齐 validate_case/record_baseline。

`flow --with-ep` 内部跑 EP 时，用**明确的 run 目录布局**：`output_dir=<run>/EP`、`ep_run_subdir="EP_run"`（= 现 run_full_pipeline `--reading-from` 分支已有的正确布局），喂 `<run>/5_intakeoutput/intake_output.json`。
- **实现选项 A（倾向）**：flow 直接调下游 graph（`build_graph` + `SimContext(output_dir=<run>/EP, ep_run_subdir="EP_run", ...)` + `run_session`），即 run_full_pipeline 内部那段（`run_full_pipeline.py:315-334`）抽成一个可复用函数 `run_downstream_ep(intake, run_dir, epw)`，flow 与 run_full_pipeline 共用 → 消除「EP 落盘随入口 flow 不一致」。
- **实现选项 B**：flow shell out `run_full_pipeline --intake-from <r>/5…/intake_output.json --output-subdir <r>/EP/EP_run`（我 2026-07-01 用过、能跑），但依赖 output-subdir 传嵌套路径的巧劲、且 ep_run_subdir 语义仍不统一。
- **审阅需求 F2**：Codex 定 A vs B。倾向 A（抽 `run_downstream_ep` 共享函数，根治不一致）；A 要动 run_full_pipeline（把那段重构成函数并让 CLI 调它，行为不变）。

---

## 4. 判/审/记 模式矩阵（一条命令覆盖两种典型跑法）

| 跑法 | 命令 | judge | 几何 | EP | report |
|---|---|---|---|---|---|
| **dev judge-in-the-loop**（本次 sm21 正规重跑）| `flow <c> <r> --judge stop --geometry auto --with-ep --record …` | 停靠、我提交 verdict、重跑续 | 自动过（用户定跳审）| ✅ | ✅ |
| **regression 一把过**（回归/CI）| `flow <c> <r> --judge off --geometry auto --with-ep --record … --run-profile regression` | gate①-only | 自动过 | ✅ | ✅ |

**判-在-环仍是主控职责**：`--judge stop` 下 flow 停在 judge 检查点、产 packet，我（主控）看图+gt 写 verdict 提交，再 `flow` 续 —— 这正是用户要的「judge 监控」，只是从「记住跑哪条命令」降为「flow 停哪我判哪」。

---

## 5. 明确不做（scope 边界）
- **不接 LLM/VLM judge_fn**：judge 保持主控在环（dev 期数据工厂设计不变）。`--judge off` 只是不判、非自动判。
- **不改 gate①/judge/verdict 语义**、不改 `run_pipeline`、不改 CorrectedGeometry/契约。
- **不改** reading 子代理协议（flow 复用现有 reread/reading 协议文案，不在 flow 内起子代理）。
- 保留所有现有 per-stage verbs（run/judge/resample/approve-geometry/status）不动 —— `flow` 是**便捷组合层**，底层仍是它们。

## 6. 测试
1. `flow --judge off --geometry auto` 在一个已存在 0_reading 的 run 上跑通 1→5，产全 attempts/manifest/renders/viewer，无 case 根污染。
2. `flow --judge stop` 停在第一个 AWAITING_JUDGE、产 judge_packet、退出码语义正确；提交 verdict 后重跑 flow 续到下一检查点。
3. `--geometry auto` 自动 approve-geometry（digest 绑定、4_mep 解锁）；`--geometry required` 停靠。
4. `--with-ep` EP 落 `<run>/EP/EP_run/eplusout.end`；`--record` 产 `report/REPORT.md` + `_run/baseline.json`。
5. EP 布局：选项 A 抽的 `run_downstream_ep` 单测 + run_full_pipeline 行为不变回归。
6. 全量 pytest（当前 395 绿）作回归基线。

## 7. 审阅需求汇总（Codex 逐条裁 + 补漏）
- **F1**：0_reading 在 flow 中的处置（停靠打印子代理协议 vs 前置要求）。
- **F2**：EP 布局修选项 A（抽 `run_downstream_ep` 共享函数、动 run_full_pipeline）vs B（shell out）。倾向 A。
- **F3**：`flow` 是 run_stage.py 新 verb（倾向、复用 _draw_fn/_judge_packet/viewer/policy）vs 独立 `run_case.py`。
- **F4**：`--geometry auto` 的 auto-approve 是否可接受（用户 2026-07-01 明确要跳审；但 auto-approve 绕过人工几何确认门——dev 档 OK、golden/regression 呢？倾向 dev/exploratory 允许 auto，golden/regression 也允许（CI 无人）；仅「正式基线录制」建议 required）。
- **F5**：`flow` 可续性实现——纯 manifest 驱动（每次从 manifest 位置续）是否够稳，还是需 flow 自己的 progress marker。倾向纯 manifest（现 status/state 已足）。
- **F6**：判/审停靠时的**退出码语义**（区分「停在 judge 检查点=需人介入、非失败」vs「terminal_stop=失败」），供脚本/CI 判读。

---

## 8. 定案设计（2026-07-02 用户 spec 整合 —— 取代 §2 初稿，含 Codex 审 findings + 本轮讨论全部决策）

> 本节 = 权威设计。整合：用户 6 步流程规格 + 3 开关模型 + judge/人工校验叠加 + gt-权威判卷 + 产物↔gt overlay + **J23 几何 judge** + Codex APPROVE-WITH-CHANGES 的 6 条必办。**待用户拍板后**送 Codex 再审→执行。

### 8.1 完整跑测流程（6 步操作协议，主控↔用户）
1. **查 gt 状态** → 报用户（有 gt = 正式跑；无 gt = 简单测试、不上主线、判卷降级）。
2. **定模型配置 + 建新 run 目录** → **跟用户确认一次**（含 reading 模型/effort、下游模型、orchestrator——落 `<run>/llm.yaml` + run 溯源）。
3. **定起止范围 + judge 开关 + 3 个人工校验开关** → **用户拍**。
4. **judge-in-the-loop 跑**（`flow` verb 驱动）。
5. **开了的人工校验点**：judge 过后**停下等用户拍板**再续。
6. 跑完 **record_baseline → report/REPORT.md** → 向用户汇报。

### 8.2 每段的门叠加模型（gate① → judge② → 人工校验，三层）
每阶段依次：
- **gate①**（确定性 code，always）——违反不变式即按现有失败分类处置。
- **judge②**（该段有 judge 且 judge 开关 on 时）：
  - **判卷 = gt 坐标对账（权威）+ 看图感知（辅助）**。数据权威层 = `score_*_vs_gt`（**放宽容差**、非毫米精确；判布局/计数/窗位定性命中）为**主判据**；judge 主观视觉只作**辅助/补充**（抓坐标对账覆盖不到的感知类，如"这是门不是窗"）——**降低对 judge 主观依赖（治 S9）**。
  - judge 不过 → **3 次盲重抽**（按归因根因路由；`JUDGE_BLOCK` 可路由 stochastic 根 → 自动盲重抽 + 失效下游；manual 根 → reread；deterministic/内核根 → 交人/backlog）。
- **人工校验**（该点开关 on 时）：**在 judge 过之后**停下，给用户看 **产物↔gt overlay + 坐标分表** → 用户拍板（OK→advance / 打回→按机制重抽/重读）。**人工校验 = judge 之上的外层终审兜底**，与 judge **叠加非互斥**（judge 开+人工开 = judge 先过、人再审）。

**开关解析（叠加）**：judge 开+人工开 → judge 过后人再审；judge 开+人工关 → 只 judge；judge 关+人工开 → 只人工；都关（或该段无 judge）→ 继续。

### 8.3 三个人工校验点 ↔ 阶段 ↔ judge
| 校验点(开关) | 阶段 | judge | 数据权威层 | 产物↔gt overlay |
|---|---|---|---|---|
| **reading** | 0_reading | **J0** | `score_reading_vs_gt`(接进 judge) | reading 描边叠 gt |
| **correction** | 1_correction | **J1** | `score_reading_vs_gt`/几何对账(接进 judge) | correction cell 叠 gt |
| **geometry(3D)** | 2/3 | **J23(新)** | `score_geometry_vs_gt`(新) | **既有 `manual_review/geometry_viewer.html`**(用户直接看 HTML，**不新渲 overlay**) |

### 8.4 要新建/改的件（本初稿新增，超出 §2）
1. **坐标对账接进 judge 当权威层**（现状：`score_reading_vs_gt` 是独立脚本、**未接 judge harness**——治「judge 拍脑袋」）。judge_packet 带 `score_*_vs_gt` 结果 + overlay；judge 判卷以对账为主、看图为辅、**容差放宽**。
2. **产物↔gt overlay 渲染**（新，**仅 0/1**）：reading 描边 / correction cell **叠在 gt 渲染上**（2D）。复用 `render_gt`(gt) + `render_corrected_geometry`/`render_elevation_windows`(产物)；一份 overlay 同喂 judge（数据层）+ 人工校验（视觉 delta）。**几何人工校验直接看既有 HTML viewer、不新渲 overlay**（用户 2026-07-02 定）。
3. **J23 几何 judge**（新，见 §8.5）。
4. **`score_geometry_vs_gt`**（新，照 `score_reading_vs_gt` 路子：built zone/window ↔ gt 逐元素 + 热区数）。
5. **`flow` verb**（§2 + Codex 必办）。

### 8.5 J23 几何 judge（新，补 S1/S2）
- **判内核 build 出来的几何**（非 correction 输入），坐在 **3_split_pairing gate① 过后**（几何+specs 定型、digest 绑 2+3）。
- **看**：原图 + built 几何静态多视角 PNG + 2D 区/面图 + gt + kernel_checks 摘要。
- **判**（rubric）：① 热区分解保真（**过度分区/欠合并** vs gt——sm24 类）② 空气耦合/邻接语义 ③ 3D 体量 vs 图 ④ 窗落 built 面 ⑤ 计数 vs gt（内核合法碎裂要有解释）。判卷同 8.2：`score_geometry_vs_gt` 权威 + 看图辅助。
- **新路由**：归因根 = **内核能力缺陷（2/3 确定性）→ `JUDGE_BLOCK_HUMAN` + 打 backlog**（不重抽——确定性重抽还是同结果），让过度分区这类系统性显形（喂 C2）。
- **3 开关几何格**：review on→**人工看既有 HTML viewer**（不新渲 overlay）；review off + judge on→**J23**（数据层 `score_geometry_vs_gt` 权威 + 感知辅助可用 viewer 静态 PNG 导出/`render_building_3d`）；都关→continue。
- **红利**：J23 判多了可沉出不吃 gt 的启发式 gate① 几何检查（如"相邻同 role 矩形区共享整边+仅导热→疑过度分区/该 air-boundary"）——把判据机械化。

### 8.6 Codex APPROVE-WITH-CHANGES 必办（全采纳）
1. **`flow` 处理 `JUDGE_BLOCK`**：可路由 stochastic 根 → 自动盲重抽（减碎片）；否则停靠退码 10。
2. **任何 force 重画必 `invalidate` 下游 manifest 指针**（现 `resample` 不做 → flow 内做，避免复用陈旧 2/3/4/5）。
3. **不静默跳 0_reading/J0**：`--from auto` 从最早未完成段起；`--from 1_correction` 须显式声明"复用已判 reading"。
4. **EP 布局修 = 选项 A**：抽 `run_agent_graph(...)` / `run_downstream_ep(intake, run_dir, epw, ...)` 共享函数（保 LLM 配置解析 + `--no-simulate` + prebuilt-intake short-circuit），flow 与 run_full_pipeline CLI 共用 → EP 干净落 `<run>/EP/EP_run`。
4. **`--geometry auto` 审计可见**：actor=`flow:auto`、approval 记 `policy="auto"`（现硬编码 `required` 会误导）；auto 前先重渲 viewer 防陈旧；**golden/正式基线录制默认 required**、regression 可显式 auto。
5. **scriptable 退出码**：`0` 完成 / `10` 停在人/动作检查点（judge/几何审/reread/未处理 JUDGE_BLOCK）/ `20` 终止编排停（quarantine/defect/human_redraw/judge_block_human）/ `30` EP·report 失败。
6. **record_baseline 前置**：`--with-ep` → `require_ep=True`；有 pending 段 `--record` 默认拒绝（除非 `--record-partial`）。

### 8.7 scope 边界
- **MEP judge（J4）保持禁用**（用户定后续做 MEP）。
- **per-stage 具体 judge 方式 / 人工校验方式 / 0-5 产物细节** = 用户之后逐项对；本轮 `flow` 只做承载 harness + 上述框架件。
- **污染硬隔离**仍 prompt 级（backlog，不在本轮）。
- 保留所有现有 per-stage verbs 不动，`flow` 是组合层。

### 8.8 建议分期（供拍板时定 scope）
- **P1 harness**：`flow` verb + EP 布局修(A) + 退出码 + 产物↔gt overlay(0/1) + 坐标对账接进 J0/J1 judge（数据权威层，容差放宽）。→ 让「正规流程一条命令、judge 按 gt 判、人工看 overlay」立即可用。
- **P2 几何 judge**：J23 + `score_geometry_vs_gt` + 内核能力缺陷路由。→ 补几何 judge 空洞（S1）。
- （P1/P2 可一轮做完，也可分两轮；用户拍。）

### 8.9 敲定决策（2026-07-02 用户）
- **几何人工校验 = 直接看既有 HTML viewer**，不新渲几何 overlay；overlay-on-gt 仅 0/1（2D）。
- **本套 SOP 写进 [`new_case_guide.md`](../../guides/new_case_guide.md)** —— 作为**下一轮动工的交付项**（工具落地时同步改，guide 才描述真工具、不写 vaporware）。列入 build scope。
- **JUDGE_BLOCK**：可路由 stochastic 根 → **自动盲重抽**（用户"其他没啥问题"采纳推荐）。
- **`--geometry-approval`**：正式基线录制默认 **required**（人工看 HTML）、regression 可显式 auto。
- **判卷**：gt 坐标对账（**容差放宽**）为主判据、judge 看图主观仅辅助（降 S9）。
- **节奏**：本轮 = 方案终审（Codex）；**下一轮 = 动工**（含 new_case_guide SOP 更新）。

### 8.10 build 交付清单（下一轮）
1. `flow` verb（run_stage.py）：循环 + JUDGE_BLOCK 自动重抽 + 下游 invalidate + 3 开关叠加 + 退出码 + 可续。
2. EP 布局修（option A：抽共享 graph/EP 函数，EP→`<run>/EP/EP_run`）。
3. 坐标对账接进 judge harness（J0/J1 数据权威层 + judge_packet 带 `score_*_vs_gt` + 容差放宽口径）。
4. 产物↔gt overlay 渲染（0/1）。
5. J23 几何 judge + `score_geometry_vs_gt` + 内核能力缺陷路由（P2，可同轮或次轮）。
6. `--geometry-approval auto` 审计可见（actor/policy）。
7. **`new_case_guide.md` 重写为新 SOP**（6 步 + 三层叠加门 + gt 权威判卷 + overlay + J23 + `flow` 命令）。
8. 测试（§6）+ 全量 pytest 回归（当前 395 绿）。

### 8.11 Codex 终审 = GO + 8 条 build 期必办（`review/2026-07-02_standardize_test_flow_review_final.md`）
终审确认 §8 方向正确、可行，6 条旧必办全在，无遗漏；风险全在**实现形态**非设计阻塞。build 时必守：
1. **坐标分表进 judge_packet 当机读 evidence（sidecar `score_vs_gt.json`）+ 定义"放宽阈值→criterion"映射**（现 scorer 只出命中/偏移、无 pass/fail 政策，不定映射则"权威"沦为主观）。
2. **StageVerdict 仍是路由/裁决权威**——scorer 输出**当 criteria 的主 evidence**、**不**用数字分替代 checklist（`verdict.py` `extra="forbid"`，别往 schema 塞 raw 分）。
3. **J1 要 correction scorer 适配器**（现 `score_reading_dir` 只解析 `*_view.json` 描边；correction 是 `CorrectedGeometry` cell/window → 建 sibling scorer 吃 `correction_geometry_snapped.json`）。
4. **overlay 用共享 metric transform、不 raster 合成 PNG**（`render_gt`/`render_vector_to_png`/`render_corrected_geometry` 各自 scale/origin/margin 不同；把产物画进 gt 渲染的坐标函数）。**容差 caveat**：gt 是 clear-space bbox、correction 常 centerline 偏移（gt `[0,15]` vs correction `[0.1,14.9]`）→ overlay 要标注/容忍该偏移、别显示成硬错。
5. **J23：注册 rubric + reorder/wrap stage-3 几何门**（现 `_post_gate1` 几何 approval 门在 judge dispatch **之前** → J23 跑不到；要改成"J23 先判、人工 3D 后审"）。
6. **加 durable 人工校验检查点记录**（reading/correction/geometry）或等价 audit-visible resume（现 durable approval 只几何有、StepStatus 无通用 `AWAITING_HUMAN_REVIEW` → 否则 flow 每次 JUDGE_PASS 后反复停）。
7. **任何 force 重画/judge 重抽前 `invalidate()` 下游 manifest 指针**（现 `cmd_resample` 不做）。
8. **测试**：退出码 / scorer-in-packet evidence / 下游 invalidate / J23 deterministic-root 路由 / geometry auto 审计字段 / post-judge 人工校验 resume。
- **gt 隔离铁律**：所有 `score_*_vs_gt` 必须留在 judge/tooling 侧，gate①/执行器绝不 import（`tests/test_gt_discipline.py` 机械守）。
- **分期**：Codex 荐 **P1 先、P2 后**（P1 已是大改：flow+EP+scorer evidence+overlay+退出码+guide；P2 改 judge 密度 + stage-3 顺序，值得独立 review/test pass）。
