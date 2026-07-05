# Run 报告 / 产出组织方案（提案）

Date: 2026-06-22
Branch: `6.15_ValidationArchM0toM4`
Status: 提案，待 Codex 双审 → 用户裁决 → 派执行
对应计划: plan.md N1b [P2]「主控汇报优化」
用户三条需求（原话）:
1. 我只看最后的报告（可直接建 report 文件夹，输出所有需要我看的内容，肉检件也 copy 进来）。
2. 报告应由**主控 Agent + judge 动态组织**（每 case/run 侧重点不同）；可有相对框架，但具体由主控作主，重点是讲明白。
3. 报告里要有**建议**：流程机制问题 + 错哪儿了 + 能力怎么升级 + 脚手架怎么搭怎么补 + 什么修法 —— 由主控+judge 探明输出，这样每次跑完才知道怎么改怎么升级。

---

## 0. 核心立场（spine）

把报告劈成两层，与项目已有的 **gate①(确定性) / gate②(judge)** 哲学同构，也兑现「judge = 开发期数据工厂」的定位——**报告就是这座数据工厂的最终产物**：

- **事实层 = 代码**（确定性、可复算、byte-stable、叙事改不动它）。= 今天 record_baseline 产的那套评分卡。
- **判断/叙事/建议层 = 主控 + judge**（动态、每 run 不同、**必须引用事实层证据**）。= 现在完全缺失的部分。

铁律：建议/叙事在 REPORT.md（主控撰写、git 跟踪），数字/计数/flags 在 baseline.json + FACTS（代码生成）。两者 diff 可审，叙事**不能凭空捏数**——任何建议须挂证据（verdict id / flag / 肉检发现），无证据的建议自我标注。这是把 judge 的 evidence 纪律延伸到报告层。

---

## 1. 现状 vs 三条需求的缺口

| 需求 | 现状 | 缺口 |
|---|---|---|
| ① 只看一个报告 | run 目录 40+ 文件平铺；肉检 png 散在 `1_correction/`、viewer 在 `manual_review/` | 无 `report/` 单一入口；肉检件要跨目录翻 |
| ② 主控+judge 动态组织 | RUN_REPORT.md 是 100% 确定性模板 | 无法按本 run 侧重点取舍/强调；无叙事 |
| ③ 含建议（机制/错哪/升级/脚手架/修法）| 完全没有 | judge verdict 只逐段盲判，无人综合成「怎么改怎么升级」|

---

## 2. 目标布局（additive，不动既有产物）

> **关键约束**：`validation_run.py` 对 `2_modelling/building_geometry.json`、`3_split_pairing/geometry_specs.md` 做 **byte 级重算比对**；`*_checks.json`/`intake_output.json`/`correction_geometry*.json`/`verdicts/` 是 gate①/契约/judge 的承重件。**这些一律原位不动**，否则破坏 validate_case + 下游。所以 `report/` 是**叠加的策展视图**——copy 肉检件、链接承重件、点向附录，而**不是把 run 目录物理重新分片**。

「分门别类收好」因此重解为：**一个策展过的 `report/` 把信号提上来、把其余指针化**，而非搬动承重文件。（此重解请用户 ratify —— 见 §6 决策点 A。）

```
<run>/
  report/                         ← 用户只看这里
    REPORT.md                     ← ★主控+judge 动态撰写（顶层人读报告，唯一要打开的文件）
    FACTS.md                      ← 代码生成事实卡（= 今天 RUN_REPORT 内容，byte-stable，叙事引用之）
    eyeball/                      ← 代码 copy 进来的 2D 肉检件（用户不必跨目录翻）
      1f_zones.png  2f_zones.png  …    （现散在 1_correction/，汇拢到此）
      South_elev.png  North_elev.png  …
      *_source.png                ← 原图，便于对照
  manual_review/                  ← 独立人工检视区（viewer 原位不动；REPORT 给指针）
    geometry_viewer.html
  baseline.json                   ← 机器评分卡（record_baseline 产，不变）
  0_reading/ … 5_intakeoutput/    ← 中间产物原位（REPORT 里链接指针，附录 drill-down）
  verdicts/  *_manifest.json  …   ← 承重件原位
```

---

## 3. REPORT.md 的相对框架（需求②：框架 + 主控作主）

骨架七节，主控**按本 run 侧重点增删强调**，不是死模板：

1. **一句话结论（TL;DR）** —— pass/blocked + 本 run 最重要的一件事。
2. **本轮侧重点** —— 这轮在测什么、为何重要（如「验证 auto re-read 三件套」/「双模型对比」）。主控判定。
3. **事实卡** —— 嵌入/链接 FACTS.md，**绝不手改**（数字唯一权威）。
4. **错在哪儿 + 归因** —— 主控+judge 把 gate flags + judge verdicts + corrections 审计 + 肉检发现串成因果链；分清 识图错 / correction错 / kernel / mep / **机制问题**（用 [[reading-honest-judge-routing-architecture]] 的两轴 severity×recoverability + who-fixes 口径）。
5. **肉视检验** —— 指向 `report/eyeball/`，主控标出本 run 最高风险项让用户优先看。
6. **建议（需求③核心）** —— 结构化成用户点名的四桶：
   - **机制问题**：schema 缺口 / 缺的门 / 管线结构性没接住的地方（如「reading 半边没落进 0-5 schema」那类）。
   - **能力升级**：管线还做不到的（接 capability C2/C3/C4 阶梯）。
   - **脚手架建议**：prompt/guide/笔库/check 该加什么补什么（服务「国产 VLM→开源北极星」的降智机制定位）。
   - **修法**：逐 finding 给具体修法 —— who-fixes（reading vs correction）/ 确定性门 vs prompt / 动不动 baseline。
7. **附录指针** —— 链接原位 raw/thinking dump、manifests、逐段 checks，供 drill-down（不 copy）。

---

## 4. 建议从哪来（需求③：主控+judge 探明）

不新造重型机制。复用现有分工：

- **judge（数据工厂，已存在）**：逐段盲判已产 criteria/evidence/root_stage/recoverability —— 这是「错哪儿」的原始证据。
- **主控综合 pass（新增一步，非新 agent）**：全段 + EP 跑完后，主控读 **baseline.json + 全部 judge verdicts + corrections 审计 + 肉检 png（多模态，主控能看图）+ 本 run 自身观察**，撰写 REPORT.md 含四桶建议。
- 口径：「judge 探明 = 逐段 verdict 暴露缺陷；主控综合 = 跨段升一层成机制/能力/脚手架/修法」。忠实于「judge=数据工厂、主控=把数据变行动的消费者」。
- （可选远期）judge③「报告/机制 critic」对 REPORT 的建议再盲审一遍 —— v1 先不做，注为后续选项，避免过度工程。

---

## 5. 代码 vs 主控分工（落地）

**代码**（扩 record_baseline.py 或新 `assemble_report.py`，确定性、可测）：
- 建 `report/` + `report/eyeball/`：按 glob copy `*_zones.png`/`*_elev.png`/`*_source.png`，copy-or-pointer viewer。
- 写 `report/FACTS.md`（= 今天 RUN_REPORT 的确定性内容，byte-stable）+ 保持 baseline.json 不变。
- 写 `report/REPORT.md` **骨架**：事实预填 + 主控待填槽位（本轮侧重点 / 错在哪 / 四桶建议）显式标注 + 主控须引用的证据清单（verdict ids / flags / eyeball 文件名）。

**主控**（new_case_guide 新增收尾步 + judge 输入）：
- record_baseline 后，主控填 REPORT.md 叙事+建议槽，**逐条挂事实层证据**；guide.md 记为最终步。

**测试**：报告组装的确定性部分照旧可单测（report/ 结构、FACTS byte-stable、eyeball copy 齐全、骨架槽位齐全）；叙事层不进 byte 测（动态），但骨架「证据清单」可测其引用的 ids 在 baseline.json 里真实存在。

---

## 6. 待用户裁决的设计点（review-asks）

- **A. 「分门别类」= 策展视图 还是 物理搬移？** 提案选**策展视图**（承重件原位、report/ 叠加），因物理搬移会破 validate_case byte 比对 + 下游精确引用。请 ratify。
- **B. RUN_REPORT.md 何去何从？** 提案：今天的确定性 md → `report/FACTS.md`；新增主控撰写的 `report/REPORT.md` 作顶层。旧 RUN_REPORT.md 名保留为兼容别名还是直接弃用？（倾向弃用，golden 测试同步改。）
- **C. ✅ 已定（用户 2026-06-22）：viewer.html 留在 `manual_review/`，report 里只给指针，不 copy。** 理由 = `6.21_ViewerToManualReview` 已特意把 viewer 挪进 `<run>/manual_review/` 作**独立人工检视区**，设计上它就是单独一块。故 `report/eyeball/` 只 copy 2D 的 zones/elev/source png（这些现散在 `1_correction/`、需汇拢），3D viewer 在 REPORT 的肉视检验节给相对链接 + 一句打开说明。
- **D. 主控撰写的 REPORT.md 进不进 baseline 的「不变量」？** 它是动态产物，不该要求 byte 相等；但建议 golden 测试只校**骨架结构存在 + 证据 ids 真实**，不校叙事文字。请确认。
- **E. 四桶建议的最低纪律**：是否强制「每桶至少一条，若无则显式写『本 run 无』」以防主控偷懒漏桶？倾向强制。

---

## 7. 影响面 / 风险

- **不碰 baseline 数值、不需重录**（纯叠加的产出组织 + 报告呈现）。
- 改动集中在 record_baseline.py（+ 可能新 assemble_report.py）+ new_case_guide.md（新增收尾步）+ golden 测试（RUN_REPORT→report/ 路径）+ .gitignore（report/eyeball/ 大图是否纳管）。
- **正好排在 sm21 重跑之前做** —— 重跑是报告大量产出处，先把汇报整干净，那一轮直接受益。
- blast radius 小、自包含，与命名确定性化（宽 blast）解耦。**（v2 修正：弃用 RUN_REPORT.md 的 blast 比此处原估宽——但实测仅 5 测试断言 + 3 活文档 + 生成器自身，全在本仓，决策定为 §8 D4「优雅原子全改、不留 shim」。）**

---

## 8. v2 修订（2026-06-22，采纳 Codex 一审 8 findings 全部）

Codex 一审 verdict=REWORK（2 BLOCKER / 4 DISAGREE / 2 NIT，落 `logs/review/review/2026-06-22_run_report_organization_review.md`）。Claude 裁决：**8 条全采纳**。修订如下，覆盖前文相应处。

### B1（BLOCKER 1）证据-id 纪律需先有可引用的 id —— 加 `evidence_index`
- 现状：baseline.json 只存 `{stage,attempt,blocking,root_stage}`（record_baseline.py:92-94），judge criteria/evidence 是自由文本（verdict.py:40-45），gate 只给 `stage/check/message`。**没有稳定 id 可被引用** → §0/§5 的「测引用 id 存在」不可实现。
- 修：record_baseline 新产**确定性 `evidence_index`**（写进 baseline.json + FACTS.md），给以下各项派稳定 id：gate flags/blockers、judge 每条 criterion、corrections 审计的 conflicts/unsupported/capped corrections、orchestration stop_reason、EP 结果、geometry digest、copy 进来的 eyeball 件。id 形如 `E:gate:1_correction:correction.zone_count_tripwire`。
- 配 **citation linter**：解析 REPORT.md 里结构化引用 `[E:...]`，任一**可执行建议**未引用 ≥1 个存在的 id → 测试失败。无此前置，golden 只能测「有没有标题」，证明不了建议有据。

### B2（BLOCKER 2）stopped/partial run 一等语义 —— 报告状态感知
- 现状：stopped 的 sonnet run（root=`human_redraw_required@1_correction`）把下游缺件当 blocking facts 列、还叫用户开不存在的 viewer（digest=None）（run_2026-06-20_sonnet_reading/RUN_REPORT.md:29-44）。
- 修：组装**状态感知**。FACTS.md 仍可含 full-scope 原始 gate 事实；但 REPORT.md 把「根因停 root_stop」与「连带缺失下游件」**分两节**、**抑制不可用检视链接**、肉检节只列**真实存在的件**（available-only）。
- golden 覆盖 ≥4 态：`human_redraw_required`、`awaiting_reread`、`awaiting_geometry_approval`、clean completed。

### D3（DISAGREE 3）eyeball 采集按真实 producer，非臆想 glob
- 现状真实件：`1_correction/zones.png` + `1_correction/elev.png`（**单文件，非 per-floor `*_zones.png`**，run_stage.py:302-309）；`0_reading/*_render.png`；源图在**父 `case_data/`**（run_stage.py:346-354）。连现有 checklist 文本(record_baseline.py:223-228)都用错 glob。
- 修：写**显式 collector**，从真实产出处 copy（collision-safe 命名）：`1_correction/zones.png`、`1_correction/elev.png`、`0_reading/*_render.png`、父 `case_data/*_view.png`（或更佳：读 `attempts/NNN/judge_packet.json` 的 `source_images`/`renders` 路径）。缺件在 FACTS.md 显式记 missing。

### D4（DISAGREE 4）RUN_REPORT.md 原子全改（用户 re-ratify 2026-06-22：弃用 shim，走优雅原子）
- Codex finding #4 给两选项：(a) 指针 shim **或** (b) 一次性更新所有 grep 可见引用；它只反对"不更新却号称小 blast"。
- 实测引用面（排除 logs/review 历史 + decision_log 历史，不动）：**承重仅** record_baseline.py(3 处，本就在改) + `test_orchestrate_baseline.py`(5 处断言，本就要为新结构改) + orchestrate.py(2 处注释) + 活文档 3 个(`new_case_guide.md`/`test_baseline/README.md`/`index.md`) + CLAUDE/contracts 路径表顺带。**全在本仓、无外部下游、一个 PR 原子改完。**
- 决策点 B 定为 **(b) 优雅原子全改**：record_baseline **不再产 RUN_REPORT.md**，直接产 `report/`（FACTS.md + REPORT.md 骨架）；**同一 PR** 把那 5 个断言 + 3 个活文档一并迁到 `report/`。不留 shim、不留"再删"尾巴。满足 Codex #4 的 (b) 分支。

### D5（DISAGREE 5）生成件 vs 撰写件分离 —— REPORT.md 防覆写
- 现状：record_baseline 每次**无条件覆写** baseline.json + md（:278-283）。若 REPORT.md 同写法，重跑**抹掉主控叙事+建议**。
- 修：**确定性生成件**（FACTS.md、可选 REPORT.template.md）与**主控撰写件**（REPORT.md）分离。REPORT.md：**缺则建、有则护**（marker 围栏区保留 / `--force-template` 显式非默认）。加回归测试：写自定义叙事 → 重跑组装 → 证明叙事未被毁。

### D6（DISAGREE 6）pointer viewer 需校验/重生
- 现状：viewer gitignored 可重生（.gitignore:299-302）、runner best-effort 返错串不 fail run（run_stage.py:318-343）。committed/拷贝的 run 可能有 building_geometry 但**无 viewer 文件** → 指针成死链。
- 修：组装时**校验** `manual_review/geometry_viewer.html`；缺且几何在 → 从 `2_modelling/building_geometry.json` **重生**；重生失败 → 记 unavailable 事实、**不发"打开 viewer"死指令**。仍守"不 copy 进 report/"。

### N7（NIT 7）四桶强制标题、不准凑数（细化决策点 E）
- 桶必在，但允许**显式** `本 run 无可证据支持的建议`；linter 把桶里**无证据的凑数 prose** 判**失败**，不判成功。

### N8（NIT 8）顺手修 guide 陈旧处
- `new_case_guide.md:183-187` 的 record_baseline 例子**漏 `run` 位置参数**（对照 record_baseline.py:387-397）；guide:148-151 写 viewer 在 `2_modelling/`，实为 `manual_review/`（run_stage.py:331-340）。改 guide 加收尾步时一并修。

### v2 影响面修正
- 仍**不需重录 baseline 数值**；但**新增 `evidence_index` 进 baseline.json** = baseline schema 扩字段（向后兼容、加字段不改既有值）。
- 改动集合扩为：record_baseline.py（evidence_index + 状态感知 + 显式 collector + 防覆写）、可能新 `assemble_report.py`、新 **citation linter**、new_case_guide.md（收尾步 + 修 N8）、golden 测试（4 态覆盖 + RUN_REPORT 指针迁移 + 防覆写回归）、test_baseline 文档、.gitignore。
- blast 比 v1 估的略宽（主要在测试/文档迁移 + linter 新件），但仍与命名确定性化解耦、不碰几何/契约。

---

## 9. v3 修订（2026-06-22，采纳 Codex 二审 4 findings 全部）

二审 verdict=REWORK（2 BLOCKER / 1 DISAGREE / 1 NIT，落同一 review 文件 §「二审」）。Claude 裁决：**4 条全采纳**——均为"v2 enforcement 面按字面不可实现"，把三个最难点精确化。

### V1（二审 BLOCKER 1）evidence_index：坐标式 id 配方（从 RAW 产物建，非折叠 summary）
v2 的 `E:gate:1_correction:correction.zone_count_tripwire` 形不安全：`summarize_gates` 把 per-view key（`0_reading::1f_view`）折叠成 `0_reading`、同 check_id 在多 view 出现会撞；judge criteria 是有序自由文本无 id（record_baseline 今天根本没把 criteria 收进来）；corrections 行异构（有的无 `id`）+ 显示 cap=20。精确配方：
- **gate id**：从 **RAW `res.reports`**（保留 per-view key）建，`E:gate:<report_key>:<check_id>`；同一 report_key 内同 check_id 重复则追 `#<n>` 序号。跨 view 撞由 report_key 含 view 解决。
- **judge criterion id**：**先把 criteria 收进 index**（扩 record_baseline：读 RAW `attempts/NNN/judge.json` 的 criteria，今天只存 `{stage,attempt,blocking,root_stage}`）；id `E:judge:<stage>:<attempt>:c<ordinal>`，**run-local 稳定**（重抽换 attempt# 可接受，非跨 run 稳定）；人读 slug 可附但**不参与身份**。
- **correction audit id**：优先用行自带 `id`；无则 `E:corr:<kind>:r<ordinal>`（kind ∈ corrections/conflicts/unsupported）。**evidence_index 索引全集**（cap=20 只是 FACTS.md 显示截断、不影响 index）。
- **单例**：`E:stop:<status>@<stage>` / `E:ep:result` / `E:geom:digest` / `E:eyeball:<filename>`。
- 一律从 RAW（res.reports + 原始 judge.json + 原始 corrections.json）建；**加 duplicate-id 断言测试**（index 内 id 必唯一）。

### V2（二审 BLOCKER 2）run_state：从 per-stage status 推导，复用现有集合（不靠 stop_reason 判 clean）
v2 误把 `stop_reason==null` 当 clean——但 `AWAITING_JUDGE`/`JUDGE_BLOCK` 是非 clean 却 stop_reason=null 的中间态（step_orchestrator.py:507-523 只给 terminal + geometry/reread 写 stop_reason，其余清空）。**复用代码已有枚举/集合**（step_orchestrator.py:71-95）：
- `TERMINAL_STOP = {QUARANTINED, DETERMINISTIC_DEFECT, HUMAN_REDRAW_REQUIRED, JUDGE_BLOCK_HUMAN}`
- `ADVANCE_OK = {DETERMINISTIC_PASS, JUDGE_PASS}`
- 新 `PENDING = {AWAITING_JUDGE, JUDGE_BLOCK, AWAITING_REREAD, AWAITING_GEOMETRY_APPROVAL}`

派生 `run_state`（确定性，读 orchestration_state.json 各段 status）：
- `root_stopped`：任一段 status ∈ TERMINAL_STOP。REPORT 分"根因停 stage"与"连带下游缺件"两节、抑制死链。
- `pending`：最新段 status ∈ PENDING（如 judge 待判/待重抽/待几何批/待重读）。
- `completed_clean`：所有预期段在册且末段 ∈ ADVANCE_OK、无 PENDING/TERMINAL。
- **golden 覆盖 6 态**：completed_clean + 4 个 PENDING + ≥1 个非 human_redraw 的 terminal（quarantined / judge_block_human）。

### V3（二审 DISAGREE 3）citation linter：建议区改可解析 mini-format（纯词法、确定性）
"可执行建议"无句法边界 → 启发式 NLP 不确定 / 宽松 regex 漏网。改**结构化**：每桶或为**精确哨兵** `本 run 无可证据支持的建议`，或为 bullet 记录：
```
- action: <一句修法>
  evidence: [E:...] [E:...]
  owner: reading|correction|kernel|mep|scaffold|...
```
linter **纯词法/结构**：每条 action 必含 ≥1 个 evidence id 且该 id 存在于 evidence_index，否则失败；桶内**自由散文不允许**（除非显式标 `> note:` context 行、linter 忽略）。不从散文推断"是否 actionable"。

### V4（二审 NIT 4）修 §7 陈旧矛盾
§7 仍写"已改为指针过渡"，与 §8 D4「原子全改、不留 shim」矛盾 → 已就地改正（见 §7）。

---

## 10. v4 修订（2026-06-22，采纳 Codex 三审 2 findings 全部）

三审 verdict=REWORK（2 BLOCKER / 0 DISAGREE / 0 NIT，落同一 review 文件 §「三审」）。Codex 明确确认 v3 其余配方已 grounded（gate per-view key 暴露 / `#<n>` 覆盖重复 check_id / judge attempts 可解析 / STAGE_ORDER 给预期段 / mini-format 确定性 / §7-§8 一致）。剩两个边界 bug，精修：

### W1（三审 BLOCKER 1）correction id 永远铸进 E: 命名空间
真实行自带 raw id（`corr_1F_S_spans`、conflict `conflict_cross_floor_corridor`），不匹配 `[E:...]` token → 仅据此行的建议引用不到。修正 §9 V1 的 correction 子条：
- **永远** `E:corr:<kind>:<sanitized-row-id>`（行有 `id` 时，把 raw id 消毒后作 slug 段）/ `E:corr:<kind>:r<ordinal>`（无 id 时）。
- 行自带 id 只当 **payload**（在 FACTS.md 里显示给人看），**不当全局 evidence 身份**。dup-id 断言保留。
- 同理复核其它源：gate/judge/单例本就在 E: 下，无此问题；本条只补 correction。

### W2（三审 BLOCKER 2）completed_clean 用 STAGE_ORDER + geometry_approved supersede
真实 clean 几何门 run：`3_split_pairing` 即便几何已批 + 下游已过 + stop_reason=null，status **仍滞留 awaiting_geometry_approval**（`mark_geometry_approved` 只置 `geometry_approved`+清 stop_reason、不改 3_split status；step_orchestrator.py:516-523,:530-542）。"无 PENDING anywhere" 会误判已知 clean run。修正 §9 V2 的派生规则：
- **expected / latest 用 `STAGE_ORDER`**（stage_runner.py:57-75）定序，**非** JSON 对象顺序。
- **pending 只看「最新有效段」** status ∈ PENDING，不是"任意段曾 PENDING"。
- **`geometry_approved` flag supersede**：当 `res.geometry_approved` 为真，`3_split_pairing` 的 `awaiting_geometry_approval` 视为**已被后续推进取代**，不再计入 pending。
- `completed_clean` = 所有 expected 段在册 + **最新 expected 段** ∈ ADVANCE_OK + 无**当前** terminal stop +（几何门已 supersede）。
- `root_stopped` 与 `pending` 若并存：terminal stop 优先（已被 stop_reason 锚定）。
- golden 须含**这个真实 clean 几何门 run 形态**（3_split 滞留 awaiting_geometry_approval 但整体 clean）作回归，防再犯。

### v4 收敛说明
三轮审 findings 收敛 8→4→2，方向三轮均获批，仅精确度递减。W1/W2 是两处外科式边界修，均锚在真实 on-disk 产物（corrections.json 真实 id / orchestration_state.json 真实滞留态）。无残留 hand-wave。

---

## 11. v5 修订（2026-06-23，采纳 Codex 四审 1 finding）

四审 verdict=REWORK（1 BLOCKER）。Codex 确认 W1 完全关闭（36 corr/2 conflict/0 unsupported、无 dup id）、W2 正确分类真实 clean run 且真未批 run 仍 pending。唯一残留：**W2 过度泛化成"只看最新段"**。

### X1（四审 BLOCKER）completed_clean 必须扫全段、唯一豁免几何 supersede
风险：`update_state` 只改当前段 + 清 stop_reason，不重写早段 summary（step_orchestrator.py:516-523）。故"末段 `5_intakeoutput: deterministic_pass` + 某早段非几何 pending（如 `awaiting_judge`/`judge_block`/`awaiting_reread`，这些**无** geometry 那样的 digest-bound supersede 信号）"会满足 v4 的"只看最新段"谓词、误判 clean。精修 §10 W2：
- `completed_clean` = 所有 expected 段（STAGE_ORDER）在册 + **全段无任何非-supersede 的 `PENDING` 或 `TERMINAL_STOP`**（不是只看末段）。
- **唯一可忽略的 pending** = `3_split_pairing: awaiting_geometry_approval` 且**当前** `res.geometry_approved` 为真（最好再要求已有后续 expected 段 ∈ ADVANCE_OK 佐证）。
- `pending`（用于 REPORT 展示）= 按 STAGE_ORDER 的**最新非-supersede pending 段**；terminal 优先级不变（terminal stop 压过 pending）。
- 其余（root_stopped / golden 6+态含真实几何门 clean 形态）不变。

至此三处 enforcement 配方（evidence_index id / run_state / citation linter）全部精确且 grounded，无残留 hand-wave。
