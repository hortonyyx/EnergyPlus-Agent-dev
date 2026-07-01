# run_pipeline 生产路径自校补齐（inline check_correction + check_mep）—— 方案

> 状态：**方案待 Codex 审**（2026-07-01，Claude 出）。
> 缘起：迁移完整性第二路独立审计 Gap#1（High，`2026-07-01_stage1to5_second_route_audit/codex_independent_findings.md:126`）+ 三路对账裁决桶③（`RECONCILED_and_vacuum_fixes.md:36`）。
> 关联：A8（evidence_debt inline）、S23-16（kernel inline）、contracts §280（validate_case 非侵入 capstone）、plan.md N1f 桶③。
> **注**：本项在裁决时定为「前瞻裂缝，非 sm21_pre 迁移缺口」——不是补丢失的旧能力，而是**续 A8/S23-16 把生产路径自校补齐、口径对齐 validate_case**。用户 2026-07-01 选定推进。

---

## 1. 目标（一句话）

让主线 `intake_node → run_pipeline` 的**内联自校覆盖对齐 `validate_case` 的 gate①**：把完整 `check_correction`（S1）+ `check_mep`（S4）inline 进 `run_pipeline`，产出与 validate_case 同口径的 `1_correction/correction_checks.json` + `4_mep/mep_checks.json`，并沿用 A8/S23-16 既定的 **run_profile 分档**（exploratory=写产物+日志可见但续行；golden/regression=fail-closed raise）。

**病灶（第二路 Gap#1 原文，High）**：主线只跑 evidence-debt coverage（A8）+ kernel（S23-16）+ stage5 `validate_contract`（construction-name backstop）。坏的 cell tiling / MEP 对象语义 / schedule 不全 / 引用错，能一路穿到 IntakeOutput，直到下游工具或 EP 才暴。stepwise（`run_stage.py`）与 validate_case 都跑完整门，唯独生产 run_pipeline 不跑。

---

## 2. 现状盘点（run_pipeline 内联门 vs validate_case gate①）

| 阶段门 | validate_case | run_pipeline 现状 | 本轮 |
|---|---|---|---|
| S0 reading `check_reading_view` | ✅ | — reading 是上游手工/图像段，run_pipeline 从 correction 起，N/A | 不动 |
| **S1 `check_correction`（全量）** | ✅ (`validation_run.py:154`) | ❌ 只跑 `check_evidence_debt_coverage`（A8，`pipeline.py:803-824`，且在 **pre-core**） | **本轮补** |
| S2 `check_kernel` | ✅ | ✅ 已 inline（S23-16，`pipeline.py:880-895`，InterZone fail-closed by profile） | 不动 |
| S3 serializer 一致性 | ✅ (rebuild 比对) | 生产路径即产出源、无「磁盘漂移」问题 | 不动 |
| **S4 `check_mep`（全量）** | ✅ (`validation_run.py:219`) | ❌ 只有 stage5 `validate_contract`（construction-name 子集，`pipeline.py:928`） | **本轮补** |
| S5 `check_assembly` | ✅ | 部分：`validate_contract`（construction 覆盖，raise 全 profile） | **不在本轮**（见 §7） |
| EP baseline | ✅ | — 下游 graph 段，N/A | 不动 |

**关键事实**：
- `check_correction` 内部**已包含** `_evidence_debt_coverage`（`correction.py:88`）→ 全量 check_correction **superset** 现有 A8 standalone coverage。故本轮以完整 check_correction **取代** `pipeline.py:803-824` 那段 standalone coverage，避免重复。
- 生产 `intake_node` 传默认 `run_profile="exploratory"`（`nodes/intake.py:64` 不传该参）→ **新门在生产路径「可见不阻断」，零新硬失败，向后兼容**。
- check_correction INVARIANT 失败（coverage/nondegenerate/zstack）经 `disposition()` 在**所有 profile** 都 map 到 BLOCK；但沿用 S23-16 的做法——**raise 只在 golden/regression 触发**（exploratory 只写产物+warn），与既有 kernel inline 分档一致（见 §4 决策 D1）。

---

## 3. 改动落点（`src/agent/pipeline.py`，全在 `run_pipeline` 内）

### 3.1 S1：以完整 `check_correction` 取代 pre-core standalone coverage

**位置**：现 `pipeline.py:803-824`（A8 standalone coverage，pre-core）→ 删除；在 `apply_deterministic_core` **之后**（约 `pipeline.py:843` 写完 `correction_geometry_snapped.json` / `corrections.json` 附近）新增完整 check_correction。

**为何 post-core**：validate_case 读的是磁盘上的 **snapped（post-core）** geom（`validation_run.py:151`）。要让「run_pipeline 内联报告 == 该 run 后续 validate_case 报告」（口径一致的定义），run_pipeline 必须在 **post-core snapped geom** 上跑 check_correction。位置仍在 kernel（862）+ mep（917）之前，早停有效。

**调用签名（对齐 validate_case `:154-160`）**：
```python
from src.validator.checks.correction import check_correction
crep = check_correction(
    geom,                                    # post-core snapped
    expected_zone_total=_expected_zone_total_from_text(testdata_text),
    relied_on_testdata=bool(testdata_text.strip()),
    capability_profile=...,                  # 见 R9
    run_profile=run_profile,
    evidence_debt=evidence_debt,             # run_pipeline 已算好（pipeline.py:781）
)
```
- **`raw_geom` 取舍（审阅需求 R1）**：validate_case 传 `raw_geom=None`（磁盘无 pre-core）。为报告严格一致，本轮**也传 None**（不传 pre-core）。副作用：`_audit_completeness` 走 `relied_on_testdata` 分支——post-core geom 因确定性核追加了 corrections，audit 非空 → pass。（备选：传 pre-core geom 得更强 audit，但会使 run_pipeline 报告严于 validate_case、破坏「同口径」。倾向 None，请 Codex 定夺。）
- **`elevation_widths`**：validate_case 也不传（默认 None → cross_image_reconcile 记 NOT_APPLICABLE）。本轮同样不传，保持一致。

**产物**：`out_dir/1_correction/correction_checks.json`（与 validate_case `write_reports` 同文件名 `correction_checks.json`，`validation_run.py:163`）。

**分档 raise**（见 §4）：`_gate("1_correction", crep, s1, run_profile)`。

**A8 coverage 迁移说明（审阅需求 R2）**：删掉的 `pipeline.py:803-824` 会连带删掉 standalone `evidence_debt_coverage_checks.json` 的写出。完整 check_correction 把 evidence coverage 折进 `correction_checks.json`（`correction.evidence_debt_coverage` 子结果仍在）。**语义变化**：A8 原在 **pre-core** 跑 coverage，现随 check_correction 挪到 **post-core**（audit rows 多了确定性核追加项）。validate_case 本就是 post-core coverage，故此变化=向 validate_case 口径对齐。请 Codex 核：(a) 是否保留 `evidence_debt_coverage_checks.json` 单独文件以兼容既有读取方/测试，还是直接并入 correction_checks.json；(b) pre-core→post-core 是否影响任何既有 A8 测试断言（预计需改 A8 相关测试）。

### 3.2 S4：inline `check_mep`

**位置**：run_mep（`pipeline.py:917`）之后、assemble（922）之前（此时 `used_constructions`、`bg.zones` 均在手）。

**调用签名（对齐 validate_case `:219-221`）**：
```python
from src.validator.checks.mep import check_mep
mrep = check_mep(
    mep_for_check,                           # 见 R3
    used_constructions=used_constructions or None,
    zone_names=set(dict.fromkeys(bg.zones)) or None,
    testdata=_parse_testdata(testdata_text), # 见 R4
    capability_profile=...,                  # 见 R9
)
```
- **`mep` 形态（审阅需求 R3）**：`run_mep` 返回 `MepOutput` 对象；validate_case 传 `json.loads(mep_output.json)`（dict）。`check_mep`/`parse_mep_fragments` 声明 `dict | object` 均可。为与 validate_case 完全同口径，倾向传 `json.loads(mep.model_dump_json())`（或 `mep.model_dump(mode="json")`）。请 Codex 核 `parse_mep_fragments` 对 MepOutput 对象 vs dict 的行为是否等价（若等价，直接传对象更省）。
- **`check_mep` 无 `run_profile` 入参**：其内部 `CheckReport(stage="4_mep", capability_profile=...)` 默认 `run_profile="exploratory"`。MEP 门无 evidence-check，disposition 不吃 profile（INVARIANT→BLOCK / CROSS_CHECK→FLAG 恒定）。**分档 raise 由 run_pipeline 侧的 `_gate` 决定**（§4），报告本身 run_profile 字段与 validate_case 一致（validate_case 也没给 check_mep 传 run_profile）→ 天然同口径。

**产物**：`out_dir/4_mep/mep_checks.json`（同 validate_case `validation_run.py:224`）。

**与 stage5 `validate_contract` 关系**：`validate_contract`（928）继续保留、对全 profile raise（construction-name 覆盖是硬契约）。check_mep 是其**超集**（加 schedule 完整性 / 对象语义 / placeholder_ban / name_charset / site）。两者共存，无冲突（construction-name 由两处各判、结论一致）。

### 3.3 辅助
- **`_expected_zone_total_from_text(testdata_text)`** + **`_parse_testdata(testdata_text)`**：run_pipeline 只有 `testdata_text`（str），没有 `case_dir`。新增两个模块级小 helper（`json.loads` + 复用 validation_run 的 `Floor plans[].thermal_zones` 求和逻辑），解析失败返回 None/{}（防脆）。**审阅需求 R5**：是否把 `validation_run._expected_zone_total` 重构成「接受 dict」的共享 helper 复用，避免逻辑双写（倾向：抽 `case_metadata` 或 correction 侧一个 `expected_zone_total_from_testdata(data: dict)` 纯函数，两处调用）。
- **`_gate(stage_name, report, stage_dir, run_profile)`**：统一「写 `<stage_dir>/<stage>_checks.json` + golden/regression 下 `report.blocking()` 非空则 raise RuntimeError」。kernel 段（S23-16，`pipeline.py:887-895`）可选一并收编进该 helper（**审阅需求 R6**：是否顺手统一 kernel 段以除重，或本轮只加 correction/mep、kernel 不动以缩小 diff。倾向：本轮加 helper 并让 correction/mep 用，kernel 段保持原样不动以控制回归面，除非 Codex 认为收编更干净）。

---

## 4. run_profile 分档决策（D1，核心）

**沿用 S23-16 kernel 既定分档**，不新造语义：
- **exploratory（含生产 intake_node 默认）**：`check_correction` / `check_mep` 照跑、**总是写 `*_checks.json` 产物**、blocking 结果只 `logger.warning` 摘要，**不 raise、续行产出 IntakeOutput**（「可见但不阻断」）。→ 生产路径**零新硬失败**，向后兼容。
- **golden / regression**：`report.blocking()` 非空 → **raise RuntimeError**（fail-closed），与 kernel（`pipeline.py:891`）、evidence preflight（`pipeline.py:788`）、evidence coverage（A8，`pipeline.py:814-824`）同档。

**为何不用「disposition==BLOCK 即 raise」（A8 那种）**：A8 那段针对的是 evidence-check（只在 golden/regression BLOCK），故等价于 profile-gated。但完整 check_correction/check_mep 含 INVARIANT 门（所有 profile 都 BLOCK）。若「有 BLOCK 就 raise」，exploratory 生产路径会在 INVARIANT 失败上**新增硬失败**，破坏向后兼容、也与 S23-16 kernel 分档不一致。故**统一按 run_profile 门控 raise**。

**副作用坦白**：exploratory 下即便 correction/mep 有 INVARIANT 级坏（如 tiling 破洞、schedule 不全），run_pipeline 仍产出 IntakeOutput（但产物 + 日志已可见）。这与全项目「exploratory 可见但续行、golden/regression 才拦」的既定哲学一致；真正的硬拦仍靠下游 InterZone 门 / EP schedule 门 / validate_case（baseline 录制走 golden、必 fail-closed）。**审阅需求 R7**：Codex 判断该副作用可接受，还是 correction/mep 的某些 INVARIANT（如 tiling coverage、schedule day-type 完整）应升级为「所有 profile 都 raise」。倾向：本轮**严守 S23-16 分档**（profile-gated），不在此引入新的「恒 raise」策略；如需，另立 tightening initiative。

---

## 5. 向后兼容 / 影响面

- **生产路径（exploratory）**：无新硬失败，仅多两个 `*_checks.json` 产物 + 潜在 warning。✅
- **golden/regression**：run_pipeline 现在会 fail-closed 于 correction/mep blocking。**若有既有 golden 走 run_pipeline 且 MEP/correction 带 blocking → 会新 fail**。但据 §1 事实，baseline 录制走 **validate_case**（非 run_pipeline），run_pipeline 的 golden/regression 主要在**测试**里显式传 profile。→ 需 Codex 全量 pytest 核实哪些测试以 golden/regression 调 run_pipeline，是否触发新 raise。
- **A8 测试**：pre-core standalone coverage 段被取代 → 相关断言（`evidence_debt_coverage_checks.json` 存在性 / pre-core 行为）需更新（见 R2）。
- **stepwise（run_stage.py）**：不动。
- **validate_case**：不动（本就是 capstone）。

---

## 6. 测试计划（Codex 执行时补）
1. **run_pipeline inline correction/mep 冒烟**：给一份 good snapped geom + good mep → exploratory 下产出 `correction_checks.json` + `mep_checks.json` 且 passed、不 raise、IntakeOutput 正常。
2. **exploratory 续行**：注入一个 correction blocking（如重复 cell id 或 tiling 破洞的 geom）+ 一个 mep blocking（如漏 construction 或 schedule 不全）→ exploratory 下**写产物 + warn 但不 raise**、仍产出 IntakeOutput。
3. **golden/regression fail-closed**：同 2 的坏输入，`run_profile="golden"` → **raise RuntimeError**，产物已写。
4. **口径一致**：同一 run，run_pipeline 内联产出的 `correction_checks.json`/`mep_checks.json` 与随后 `validate_case` 的报告**逐字段等价**（至少 check_id 集合 + status 一致）。
5. **A8 迁移回归**：evidence coverage 仍生效（现经 check_correction），pre-core→post-core 变化不误伤既有 A8 冒烟（gpt54 空 dimensions→仍在 preflight 段 block；坏 coverage→仍报 `correction.evidence_debt_coverage`）。
6. 全量 pytest（当前 **388 绿 / 9 xfail**）作回归基线。

---

## 7. 明确不做（scope 边界）
- **check_assembly（S5）inline**：Gap#1 只点名 correction/mep；stage5 `validate_contract` 已 backstop construction-name。完整 check_assembly inline 属更进一步 tightening，**不在本轮**（可记 backlog）。
- **kernel 其余 INVARIANT（zone_closure/normals）升级为 run_pipeline raise**：S23-16 只对 InterZone fail-closed，其余仍只写报告——这是 plan.md N1f 已记 backlog，**不在本轮**。
- **Phase B（#2/#3/#6）**、**#4 合理性区间**：另线。
- 不改 `check_correction`/`check_mep`/`CorrectedGeometry`/`MepOutput` 任何签名或语义——**只在 run_pipeline 侧接线调用**（helper 除外，且 helper 纯新增）。

---

## 8. 审阅需求汇总（Codex 请逐条裁 + 补漏）
- **R1**：check_correction 传 `raw_geom=None`（对齐 validate_case、报告一致）vs 传 pre-core geom（更强 audit）。倾向 None。
- **R2**：A8 standalone coverage（`pipeline.py:803-824`）取代方式——是否保留 `evidence_debt_coverage_checks.json` 单独文件；pre-core→post-core 对既有 A8 测试的影响与改法。
- **R3**：check_mep 传 MepOutput 对象 vs `json.loads(model_dump_json())` dict；`parse_mep_fragments` 两者是否等价。
- **R4**：`testdata_text`→dict 解析的防脆处理（空/非法 JSON→{}/None），site 比对与 expected_zone_total 的 None 兼容。
- **R5**：`expected_zone_total` 逻辑抽共享纯函数（吃 dict）复用 validation_run，避免双写。
- **R6**：新增 `_gate` helper 是否顺手收编 kernel 段（除重）还是本轮 kernel 不动（控 diff）。倾向后者。
- **R7**：exploratory 下 correction/mep INVARIANT 失败「可见但续行」（严守 S23-16 分档）是否可接受，还是个别 INVARIANT 应恒 raise。倾向严守分档。
- **R8**：golden/regression 下哪些既有测试以该 profile 调 run_pipeline、是否触发新 raise（全量 pytest 核）。
- **R9**：`capability_profile`（D3）——run_pipeline 无 policy 对象；check_correction/check_mep 的 capability_profile 传什么（默认 "rectangular"？是否需从入参线程化）。请一并裁。

---

## 9. 定案（Claude 裁决，2026-07-01，Codex 审 APPROVE-WITH-CHANGES 全采纳）

Codex 审 = **APPROVE-WITH-CHANGES**（`logs/review/review/2026-07-01_run_pipeline_self_check_review.md`）。Claude 逐条核后**全采纳**；对原方案的实质修正是 R2（不替换 A8，改为并存）。执行按下列定案：

1. **S1（correction）= 保留 + 新增（不替换）**：`pipeline.py:803-824` 的 A8 **pre-core** standalone coverage + strict gate **原样保留**（保 A8「LLM 是否覆盖 reading 债」的 pre-core 语义，避免确定性核事后 audit 行补掉债）。**另在 post-core**（apply_deterministic_core 之后、kernel 之前，约 `pipeline.py:843` 后）新增完整 `check_correction`，写 **`1_correction/correction_checks.json`**，做 validate_case 口径对齐。两者并存、evidence coverage 轻微重复可接受（各自目的清晰）。
2. **`relied_on_testdata` = `bool(parsed_testdata)`**（解析后 dict 真值），**不用** `bool(testdata_text.strip())`——后者把 `"{}"` 当 reliance，会让 `test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles`（testdata `"{}"` + `_minimal_geom()` 无 audit 行）在 S1 `correction.audit_completeness` 提前 raise、破坏其预期的 kernel raise 路径。空 testdata=无 reliance，语义更准，且对真 case 与 validate_case（文件存在=reliance）结论一致。`raw_geom=None`（R1，对齐 validate_case、报告一致）。
   - **执行注意**：若 `_minimal_geom()` 因结构 INVARIANT（coverage/nondegenerate）仍被完整 check_correction 在 S1 提前拦（先于 kernel gate），执行器按判断二选一并回报理由：(a) 给该 fixture 一个合法 tiling 的 geom 使其到达 kernel gate；或 (b) 更新测试断言「S1 gate 现在先于 kernel gate」这一新管线现实。**不得**为过测把 S1 门弱化。
3. **kernel 段不动**：不并进通用 `_gate`（会把 kernel 收紧到 InterZone 之外——`check_kernel` 还含 zone_closure/normals/coverage 等 INVARIANT block，S23-16 只对 InterZone fail-closed）。新增 `_gate` **仅** correction/mep 用，且 **filename 显式**（`correction_checks.json`/`mep_checks.json`，非按 stage 名派生）+ **profile 显式**（golden/regression 下 `report.blocking()` 非空则 raise，raise 消息带外部 `run_profile`；exploratory 只 `logger.warning`（含 check id）+ 先写产物再续行）。
4. **S4（mep）inline**：run_mep 后、assemble 前，`check_mep(json.loads(mep.model_dump_json()), used_constructions=used_constructions or None, zone_names=set(dict.fromkeys(bg.zones)) or None, testdata=parsed_testdata, capability_profile=…)`（R3 传 persisted-dict 形态求 validate_case 完全一致）。写 **`4_mep/mep_checks.json`**，走 `_gate`。stage5 `validate_contract` 保留不动（全 profile raise）。
5. **`capability_profile="rectangular"` kwarg 加进 run_pipeline 并 thread through**（R9）：`compute_evidence_debt_from_vector_dir` / `run_correction` / `check_correction` / `check_kernel` / `check_mep` 均接线（各已接受/默认该概念）；`intake_node` 继续省略=默认 rectangular，行为不变。
6. **helper 去重**（R5）：抽一个吃 `dict` 的纯函数 `expected_zone_total_from_testdata(data)`（`Floor plans[].thermal_zones` 求和，无则 None），`validation_run._expected_zone_total` + `run_stage._expected_zone_total` + run_pipeline 新解析路径**共用**（消除现有双写、不建第三份）。落点由执行器定（倾向 `execution/case_metadata.py` 或 correction 侧纯函数模块）。
7. **testdata 解析 helper**（R4）：返回 `dict | None`——blank / 非法 JSON / 非对象 JSON → `None`；合法对象（含 `{}`）→ dict。传给 `check_mep(testdata=…)` 与 `expected_zone_total_from_testdata`。**不用 `{}` 兜底**（`_extract_testdata_site(None)` vs `({})` 证据不同）。
8. **imports 保持惰性**：`check_correction`/`check_mep`/helper 的 import 放插入点（函数内），不加 pipeline.py 模块顶部 import（`check_mep` 经 idf_fragments 拉 eppy，勿上热路径）。
9. **文档口径修正**（Codex 事实纠正，非代码）：① stepwise（run_stage.py）S4 不传 testdata → `mep.site_matches_testdata` 在 stepwise 恒 NOT_APPLICABLE（本轮不改 stepwise，仅记录 stepwise≠validate_case 这一既有差）；② record_baseline 默认 exploratory（非 golden），故 run_pipeline 的 golden/regression fail-closed 主要影响**显式传该 profile 的测试**，非日常 baseline 录制。

**明确不做**（同 §7）：check_assembly inline / kernel 其余 INVARIANT 升级 / Phase B / #4。

**验收**：全量 pytest（当前 **388 绿 / 9 xfail**）作回归基线；§6 六项测试补齐；Claude 大节点全面审（自跑 pytest + 逐行 diff）。
