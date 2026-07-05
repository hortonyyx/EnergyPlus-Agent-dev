# Stage 1-5 迁移完整性：两路对账裁决 + 真空项修法方案

> 状态：**裁决已落 + 修法待 Codex 审**（2026-07-01）。Claude 第三路综合（对账 Codex 第一路全 0-5 审 + Codex 第二路独立 1-5 审 + 逐条代码核验）。
> 输入：`2026-06-27_full_0to5_migration_audit_codex/codex_findings.md`（第一路）、`2026-07-01_stage1to5_second_route_audit/codex_independent_findings.md`（第二路）。
> 关联：contracts §280（validate_case 非侵入 capstone）、plan.md N1f、[[reading-evolution-and-phase-a]]（Phase B）。

---

## 0. 一句话裁决

**相对 sm21_pre，迁移在 `validate_case` 口径下基本完全。** 第二路把第一路 ~15 条 ✅ 降为 ⚠️，但逐条核验后**根因是路径差、非迁移缺失**：这些约束**迁到了 `validate_case`**（M0-M4 **非侵入 capstone**，contracts §280 明文"未动 run_pipeline"的有意设计），dev/baseline 全程走它跑 full gate①（`record_baseline` + `step_orchestrator` 调用坐实）。真·"迁到无处强制"的只剩 **S4-12 + #5 + #9**（本轮补）。

---

## 1. 两路对账（Claude 逐条核验）

**验证的决定性事实**（`grep check_correction/check_mep` 全 call site）：
- `check_correction` 仅 `validation_run.py:142`（validate_case）+ `run_stage.py:171`（stepwise）。
- `check_mep` 仅 `validation_run.py:207` + `run_stage.py:253`。
- `intake_node → run_pipeline`（`nodes/intake.py:55/65`），run_pipeline inline 只跑 `check_evidence_debt_coverage`（A8）+ kernel check（本轮 S23-16）+ stage5 `validate_contract`。
- 下游 `validate_node` 跑 `ConfigState.validate_references()`，非 validate_case。
- `validate_case` 由 `record_baseline.py:305` + `step_orchestrator.py:476/491` 调用 → **dev/baseline 路径跑 full gate①**。

**∴ 两路都对，只是看不同路径**：第一路 ✅（约束迁到 validate_case capstone，成立）；第二路 ⚠️（生产 run_pipeline 路径不跑，成立）。**contracts §280 = 2026-06-15 有意设计**：validate_case 非侵入跑全段 gate①、run_pipeline 不动。

**第二路真正的价值发现（前瞻裂缝，非旧缺口）**：A8 + 本轮 S23-16 已开始把门 inline 进 run_pipeline（evidence_debt / kernel，run_profile fail-closed），**correction/mep 门没跟上** → "run_pipeline 自校"现在**半拉子、口径不齐**。补齐 = **前瞻架构 initiative**（让生产路径自校），非 sm21_pre 迁移缺口 → 记 backlog（且与 Phase B correction 重构重叠，宜合并考量）。

---

## 2. 最终缺口分类（四桶）

| 桶 | 条目 | 处置 |
|---|---|---|
| **① 已迁到 validate_case**（第二路 ⚠️ 根因，非缺失）| S1-05/06/07/08/11/13/14/15/16/17 · S23-14 · S4-03/04/06/09/10 · S5-05（第二路降级项）| **不动**：validate_case 口径下强制在；dev/baseline 全走它 |
| **② 真·迁到无处强制**（连 validate_case 都无）| **S4-12**（占位禁令）· **#5**（building/site vs testdata）· **#9**（MEP 命名字符集）· #4（合理性区间=有意 deferred 占位，不动）| **本轮补 S4-12/#5/#9 进 check_mep** |
| **③ 前瞻裂缝**（run_pipeline 自校半拉子）| check_correction/check_mep 未 inline run_pipeline（第二路 Gap#1）| **backlog**：独立 initiative，续 A8/S23-16、宜并 Phase B |
| **④ Phase B 领**（需双通道 schema）| #2 尺寸/证据仲裁机械化 · #3 facade local→world · #6 非矩形/退台策略一致性 | **Phase B**（CorrectedGeometry 拍平原始证据 → 非双通道不可解）|

---

## 3. 本轮修法（真空三项，全落 `check_mep`，validate_case 口径）

> 全部进 `src/validator/checks/mep.py`（走 validate_case，**不 inline run_pipeline**——与用户定"填 validate_case 口径真空、run_pipeline 自校另算"一致）。

### 3.1 S4-12 — 占位/模板 prose 禁令门（❌ 真空，第二路 confirmed）
**要求**：新 `check_mep` 子门（建议 id `mep.placeholder_ban`，INVARIANT）扫 MEP 授权的字符串值，命中 banned 占位 → `add_fail`。
- **banned 集**：`TBD` / `same as above` / `see above` / `etc.` / `...` / `<placeholder>` 类模板 prose（大小写不敏感、词界匹配防误伤如合法词内含 "etc"）。
- **扫描面**：解析后 MEP 对象的字段值（schedule/construction/material 名 + 授权文本字段）。**审阅需求**：Codex 定确切扫描面（parsed IDF fragment field values vs raw mep dict string 字段）+ 假阳性护栏（词界/引号内整值匹配）。

### 3.2 #9 — MEP 命名字符集门（❌ 真空，S4-I）
**要求**：新 `check_mep` 子门（建议 id `mep.name_charset`）验 MEP 授权对象名（material/construction/schedule/type-limit）字符集。
- **裁定倾向 = FLAG（CROSS_CHECK）非 FAIL**：EP 实际容忍空格/更多字符，几何名本已 `_safe`，真风险是 exact-ref 漂移 → flag 可见即可，别硬 block 误伤合法名。**审阅需求**：Codex 定 flag vs fail + 字符集（旧规则 letters/digits/underscore 严格 vs EP-safe 超集）；建议 letters/digits/underscore/`-`/space 之外才 flag。

### 3.3 #5 — building/site 对 testdata 核（⚠️ 真空，S4-B）
**要求**：`check_mep` 加 `testdata: dict | None = None`（或 `expected_site`）入参；validate_case 从 `case_dir/case_data/testdata_prompt.json` 读并传入（validate_case 本已读该文件，`validation_run.py:140`）。
- **轻量版（防脆）**：testdata 若带结构化 site 字段（latitude/longitude/time_zone/elevation）→ 比对 MepOutput.site_location、超容差 **FLAG**；testdata 无可比字段 → `NOT_APPLICABLE`（对齐 `reasonability_placeholder` 诚实占位，不假装能核）。building.name/site presence 存在性可顺带查。
- **审阅需求**：Codex 核 testdata_prompt.json 实际 schema（sm20/sm21/sm24 各带哪些 site 字段可靠比对）+ 签名 threading（是否触及 validate_case→check_mep 其他调用点如 run_stage.py:253，须给默认 None 向后兼容）+ flag vs fail。**明确**：EPW/weather 路径运行时单独传（`run_full_pipeline.py:311`），本门不管 EPW 存在性。

---

## 4. 明确不做（记 backlog / 归他处）

- **run_pipeline 自校半拉子**（第二路 Gap#1，桶③）：把 check_correction/check_mep inline 进 run_pipeline = 独立前瞻 initiative，续 A8/S23-16，宜与 Phase B correction 重构合并，本轮不做。
- **#2 / #3 / #6**（桶④）：Phase B（双通道 schema）。#3 facade local→world 接线守 [[derive-facade-frame-unwired-ew-sign-trap]]（E/W sign 接核前对 gt 验）。
- **#4 MEP 合理性区间**：`mep.reasonability_bands` 有意 deferred 占位，不动。

## 5. 测试 / golden 影响预案
- 三门全落 check_mep = validate_case 路径。**sm21/sm20 golden 走 validate_case**——若既有 baseline MEP 带占位/非法字符/site 不符则会新 fail（预期不带、须实测）。用 legacy 祖父化思路：若触及 legacy golden，disposition 按 run_profile / 保守 flag。
- 全量 `pytest`（当前 381 绿）作回归基线；Codex 执行后 Claude 大节点全面审。

## 6. 推进
1. **派 Codex 审本方案**（xhigh，落 `logs/review/review/2026-07-01_vacuum_fixes_review.md`）。
2. Claude 裁决 → 派 Codex 执行（简报含各门「审阅需求」自报点）。
3. Claude 大节点全面审（pytest + 逐行 diff）。
4. 更新管理文档：**宣告"相对 sm21_pre 迁移在 validate_case 口径下完全"** + 桶③/④ backlog（CLAUDE.md §2 / plan.md N1f / decision_log）。
