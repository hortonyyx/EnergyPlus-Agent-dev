# Fable 对抗审 verdict — C2 体检 4 MAJOR + 配套（sol 施工）

- **日期**: 2026-07-20
- **审者**: Fable 5（顶档对抗审，本批唯一权威）
- **对象**: sol 施工 7 finding（F1-1 / F2-1 / F2-2 / F5-1 / F4-1 / F1-2 / B4b MINOR-1）
- **依据**: 原始需求 `request/2026-07-20_audit_remediation_construction_dispatch.md` + `git diff`（9 文件，397+/21-）+ 本审独立 neuter 活体探针（P1–P7 全跑 + 自设 P1a/P6b/P6c/P7x 四条加测）
- **基线**: 交付尾态 6 目标测试文件 98 passed；本审独立全量见 §5

---

## 总裁决: **REWORK**

**7 条 finding 的 neuter 探针全数通过、无一 false-lock、生产码本体零 bug、零算法改动、零 golden、无越界。** REWORK 的两条出口均为小改动：一条是派单 P1 预判的正例锁缺失（我独立复核后裁定成立），一条是本审活体探针新抓的判卷循环崩溃点（既有休眠缺陷、被本批 SOP 武装成 sm25-L 必踩路径）。生产码改动本身**全部保留、无需回改**。

---

## 1. 逐 finding 裁定

### F1-1 B5 orientation 再入守卫 — ✅ CLEAN（无出口条件）

- 修法正确：早退 tuple 补 `correction_b5_orientation_v1`，与 E4 出口契约本体（output_coordinates.py:165-168）对齐。
- **P5 neuter**（早退 tuple 撤 b5）→ 专属锁 `test_b5_orientation_enrichment_is_idempotent_on_reentry` 红，红因精确 = `AssertionError: already-enriched B5 output re-entered orientation resolution`（monkeypatch 拦截函数级 import，拦截有效性已核）。**另两条 mep e2e 同红** —— 非无关连带：它们经 `_stepwise_e4_run` 产出 accepted `correction_b5_orientation_v1` 后再入 `_draw_assembly`，恰好活体复现 F1-1 原始故障场景（sm25-L 重装配路径），方向正确、属同门真实路径的纵深证据。恢复后全绿。

### F2-1 reading→correction 绑 accepted — ⚠️ **MAJOR M1（出口 #1：缺 happy-path 正例锁）**

**guard 本体裁定 = 正确、非 run 级 BLOCKER（主控 P1 parity 判断复核属实）**，证据：
- 代码级 parity 三条腿独立核毕：① `_draw_reading` 组 `{stem: parsed for sorted(glob("*_view.json"))}`（run_stage.py:178-189）与 guard 重建逐字对位；② `StageRunner` 纯 dict 归档 `_to_json` = `json.dumps(indent=2, ensure_ascii=False)`（stage_runner.py:216/560），`attempts/NNN/output.json` 字节 = `out_text` 原样（445/456 行，无尾换行）；③ `output_hash = hash_text(out_text)` ≡ `hash_bytes(归档文件)`，guard 双锚（归档字节 + stage-root 重建）同against `output_hash` 自洽。
- **P1a 活体正例探针**（真 StageRunner 归档）：单视图 / 多视图排序敏感 stem + 非 ASCII 中文 + 嵌套 + 浮点 → guard 全放行；accept 后篡改 stage-root 负对照 → 正确 raise `accepted_attempt_mismatch`。
- V1/V2 manifest 兼容核毕（StageRecord V1 有 `accepted_attempt`+`output_hash`，RunManifest V1 有 `.accepted`）——legacy run 不炸。
- **P1b neuter**（guard 恒通过）→ 3 条负锁齐红（`_draw_correction` 锁红因 = 未受信字节**真抵达 run_correction**）、standalone 放行锁绿。锁绑对门、无 false-lock。

**缺口（REWORK 依据）**：全仓 grep 证实 `build_verified_window_inputs_from_run` 只有新测试文件触碰、flow 测试全用 fake draw fn ——**「accepted 存在 + 忠实 stage-root → 放行」全仓零测试**。若 guard 因约定漂移（`_draw_reading` 停用 sorted / stem 键变 / guard 改序列化）开始误拒**每一个合法 run**，全套测试依然全绿。该 guard 卡在每次 flow correction draw 的必经入口，误拒 = sm25-L 全线硬阻，且三模块约定耦合无任何绑定锁。

**出口条件 M1**：补一条正例锁 —— output_obj 必须来自**真实 `_draw_reading` 返回值**（真 case seed，如 `_seed_case_data`/sm21 case_data；**禁止**测试内手搓 `{stem: view}` 自指复刻），经真 `StageRunner.record` 归档、stage-root 不篡改，断言 guard 放行（`build_verified_window_inputs_from_run` 越过 guard 继续，或 `_draw_correction` 抵达 run_correction）。一条即可。

### F2-2 S5 绑 accepted mep — ✅ PASS（1 NIT 非出口）

- **P4a neuter**（input_hashes 删 4_mep 条目）→ 只有绑定锁红（红在 `dict(write.input_hashes)["4_mep"]` KeyError = 正是绑定断言）；**P4b neuter**（hash 门恒通过）→ 只有 tamper 锁红。互不连带。
- 正例锁同时证明：合法 accepted mep run 放行、stage-root 覆写件（"BLOCKED LATER DRAW"）**不被消费**、hash 真入 input_hashes。不误伤既有合法 S5。
- **NIT n1**：`assembly.mep_accepted_required` / `assembly.mep_present` 两个辅助拒绝分支无专属锁。neuter 推演：撤 accepted_required → `_accepted_output_path` 无记录返 None → mep_present 兜住；双撤 → `None.read_bytes()` 崩溃 —— 纵深 fail-closed 在位、**无 false-green 开口**，故 NIT 登记跟进债，非出口。

### F5-1 footprint 双层负锁 — ✅ CLEAN（P2 重点全证）

- **P2a neuter envelope 事务层门**（envelope_transform.py:519-520 恒通过）→ **只有**纵深锁 `test_transaction_rejects_divergent_footprints_after_schema_is_bypassed` 红，红因 = `failed_gate_id` 落到下一道 `correction.envelope_axis_attachment` ≠ 期望 `correction.envelope_schema_scope`。此红因同时证明两件事：① 负例经 monkeypatch `CorrectedGeometryV3.model_validate`（`calls==1` 有断言）**真绕过 schema 层、抵达事务层**；② 锁断言**精确目标 gate id** 而非「任意拒绝」。**无 false-lock。**
- **P2b neuter schema 层门**（schema.py:262-263 恒通过）→ **只有** schema 锁 `test_v3_schema_rejects_divergent_per_floor_footprints` 红；envelope 纵深锁不连带。双向独立成立。

### F4-1 bindings 断链兜底 + SOP — ✅ PASS（衍生本审新抓 F-R1，见 §2）

- 重排正确：gt identity 前置（run_stage.py:1357），静默 None 仅限 `typed_gt is None`；有 v3 GT 缺 sidecar → exploratory/dev warn、golden/regression raise。
- **run_profile 线程完整性（P3①）**：四个生产调用点（cmd_run 的 `_judge_packet`:1755 + `_render_stage_grade_artifacts`:1775；cmd_flow 的 1960/1986）全部传 `policy.run_profile`；grep 证实 grade 组件在生产码无其他调用方，函数默认 "exploratory" 从生产入口不可达。golden/regression 不会静默降档。
- **P3a neuter raise** → 只有 golden+regression 两条 fail-closed 锁红；**P3b neuter warn** → 只有 exploratory+dev 两条 warn 锁红；非 v3 静默测试两轮均绿（三态覆盖全证，互不连带）。
- SOP §0.3 如实：诚实写明无 provision bridge、人工落位步骤、hash 匹配核对、分档行为与代码一致；引用锚点 `c2_b4b_detail_spec.md` §6.3（line 343）真实存在。
- **NIT n2**：非 v3 静默测试用 monkeypatch 伪 `load_score_gt_identity` 返 `(None,None)` 而非真 legacy gt 文件 —— 可接受（函数级 import 使 patch 合法生效），仅记录。

### F1-2 capability_profile 进 run_config — ✅ PASS（1 MINOR）

- **P6 neuter cmd_flow 接线**（退纯 CLI）→ 只有 present 支参数化锁红（config=orthogonal 期望 orthogonal 实得 rectangular）、absent 支（CLI 保留）绿。**P6c neuter 值域校验** → invalid 回退锁单独红。
- **MINOR m1**：**cmd_run 的同款接线（run_stage.py:1742）无锁** —— 本审 P6b 探针把 cmd_run 接线单独退回纯 CLI，flow/config/audit 三文件 28 测**全绿**。stepwise `run` 入口漂移即静默回 rectangular（正是 F1-2 要杀的故障模式）。出口成本极低：把现有参数化锁孪生一条到 cmd_run（或同 capture 手法）。**并入本轮返工顺手做**（单独不阻断，但既有返工轮就一并收）。

### B4b MINOR-1 correction v3 判卷 e2e — ✅ PASS（接线合规）

- e2e 尾态绿：真 accepted `correction_b5_orientation_v1` + 真 bindings + typed GT 端到端，断真 v8 sidecar（`kind=c2_scored`、`stage=correction`、真 PNG grade）。
- **接线越界审（P7①）**：`score_attempt_service`/`score_typed_attempt` 的 `window_host_proof` 参数为**本批之前既有**（score_service.py:107，不在 diff）；sol 只在 assembler 侧对 **accepted attempt**（`accepted_record` 仅当本 attempt 即 accepted 时非 None，run_stage.py:1345）经 `load_verified_accepted_correction` 补传，另加 `accepted_attempt == attempt` 一致性守卫。**零 scorer 算法/policy/verdict 改动，纯传参。**
- **P7a neuter**（proof 恒传 None）→ 只有 correction e2e 红（红在 scorer **既有**六件套门 score_service.py:161），reading typed e2e（test_d1_d2_d3）绿。

---

## 2. 本审新抓 F-R1 — ⚠️ **MAJOR M2（出口 #2：判卷循环对非 accepted v3 correction attempt 必崩）**

**P7x 活体探针**（真实 v3 run 形状 `_stepwise_e4_run`：attempt 001 = base correction〔enrichment 后变非 accepted〕+ 002 = orientation enrichment accepted；sidecars 按新 SOP 就位）：

```
correction attempts on disk: ['001', '002'] | accepted: 2
LOOP RAISED: ScoreContractError: score_unsupported_combination at scoring.capability
```

- `_render_all_typed_attempt_grades` 遍历**所有** attempt 目录；非 accepted 的 correction attempt 在 scorer 既有 capability/六件套门被拒（B5 设计：official typed correction 计分只定义在 accepted 六件套输入上）→ `ScoreContractError` 在 run_stage **全链无捕获**。
- **sm25-L 触发路径**（cmd_flow 在每段 run_one_stage 后**无条件**调 `_render_stage_grade_artifacts`，1986 行）：① correction 首抽被 gate① block、重抽 accepted → 段后判卷循环遍历到 blocked 001 号 → **flow 崩**（stochastic LLM 下高概率）；② enrichment 之后任何再触 1_correction 判卷的 stepwise/re-entry → base attempt 已非 accepted → 崩。
- **定性**：scorer 门与判卷循环均先于本批存在 = **既有休眠缺陷，非 sol 回归**；但 F4-1 的 SOP 使 sidecars 对 v3 case **强制**（golden/regression 缺件还 fail-closed），本批正是把这条崩溃路武装成 sm25-L 照 SOP 跑**必踩**。判卷是 sm25-L 的测量仪器，本审据此升格为本批出口而非跟进债。
- **出口条件 M2**（改动面最小、零 scorer 改动）：`_grade_typed_attempt_artifacts` 在 `stage == "1_correction" and accepted_record is None` 时返回静默 None 三元组（与 scorer 政策对齐：非 accepted 无 official 分）+ **一条回归锁**：真实 v3 run 形状（base+enrichment 两 attempt）+ sidecars 就位 → 循环完整跑完不 raise、accepted attempt 出真分、非 accepted attempt 为 None。时序安全性已核：judge packet 只在 gate① 通过后构建、record 即 accept（stage_runner.py:479），skip 不会饿死 packet 路径；reading 段非 accepted 判卷不受影响（scorer 该门仅 correction 分支）。

---

## 3. 边界纪律核查

- **零算法改动**：9 文件 diff 全为守卫/接线/config 解析/测试/文档；kernel、scorer、gate 语义体未触。✅
- **零 golden**：diff 无 golden 文件。✅
- **无越界**：全部文件在派单点名范围内；proof 接线为派单 §7 预告的披露项、已按钩子审毕。✅
- **简报 neuter 自报核对**：sol 简报声称的锁位与本审探针结果一致，无 false-lock 虚报（对照 B5 Phase D r1 的 replay false-lock 翻车点，本批干净）。✅

## 4. 探针台账（全部已恢复，工作树 = sol 交付尾态，NEUTER 残留扫描零命中，diff --stat 逐文件对齐 397+/21-）

| 探针 | neuter 目标 | 红 | 余 |
|---|---|---|---|
| P1a | （正例活体，无 neuter） | — | guard 放行 ×2 场景 + 负对照 raise |
| P1b | reading guard 恒通过 | 3 条 F2-1 负锁（红因=字节抵达 run_correction） | standalone + 其余 4 绿 |
| P2a | envelope 层 identical 门 | 仅 envelope 纵深锁（落 axis_attachment） | 53 绿含 schema 锁 |
| P2b | schema 层 identical 门 | 仅 schema 锁 | 53 绿含 envelope 锁 |
| P3a | golden/regression raise | 仅 strict 2 锁 | 14 绿含 warn/非v3 |
| P3b | warn 分支静默 | 仅 warn 2 锁 | 14 绿含 strict/非v3 |
| P4a | input_hashes 删 4_mep | 仅绑定锁（KeyError） | 6 绿含 tamper 锁 |
| P4b | mep hash 门恒通过 | 仅 tamper 锁 | 6 绿含绑定锁 |
| P5 | 早退 tuple 撤 b5 | 专属再入锁（红因精确）+ 2 条 mep e2e（同门真实路径连带，方向正确） | 20 绿 |
| P6 | cmd_flow run_config 接线退 CLI | 仅 present 支锁 | 20 绿含 absent 支 |
| P6b | cmd_run 同款接线退 CLI | **零红（28 全绿）→ MINOR m1** | — |
| P6c | capability 值域校验 | 仅 invalid 回退锁 | 3 绿 |
| P7a | proof 恒传 None | 仅 correction e2e（红在 scorer 既有六件套门） | 15 绿含 reading e2e |
| P7x | （活体，无 neuter） | 循环在非 accepted 001 号 raise → **MAJOR M2** | — |

## 5. 独立全量

- r1 轮 Fable 侧全量因返工中途落树作废；权威全量 = 主控独立复跑返工 r1 尾态：**1456 passed + 9 xfailed, PYTEST_EXIT=0**（较派工单基线 1434+9 净增 22 测，含本批 18 + 返工 4 项；零 scorer/golden/judge/config 触碰，主控亲核）。

## 6. 出口清单（REWORK → sol，闭环回本审）

1. **M1**（F2-1）：真 `_draw_reading` 归档路径的 happy-path 正例锁一条（§1 F2-1 出口条件原文）。
2. **M2**（F-R1）：非 accepted v3 correction attempt 判卷 skip（静默 None）+ 真实 run 形状回归锁一条（§2 出口条件原文）。
3. **m1（顺手，MINOR）**：cmd_run capability_profile 接线孪生锁一条。
4. 纯测试 + 一处 assembler 早退，**零生产语义改动、零 scorer 改动、零 golden**；返工后我按同标准复审（新锁各自 neuter 红 + P7x 复跑通过 + 全量零回归）。

n1（mep 辅助分支锁）/ n2（非 v3 静默测试 realism）登记跟进债，非出口。

---

# r2 复核（sol 返工 r1：M1 / M2 / m1）— 2026-07-20

- **树态**: sol 返工 r1 尾态（未 commit），r1-tail diff 指纹 `2a11c272…`；主控权威全量 = 1456 passed + 9 xfailed, PYTEST_EXIT=0。
- **交付态基线**: 三条新锁（4 test items）全绿（本审复跑）。

## r2 总裁决: **APPROVE**

三条新锁（M1 parity 正例锁、M2 早退+真实形状回归锁、m1 cmd_run 孪生锁）neuter 探针**逐条精确命中**（各只红对应锁，余绿，无连带、无 false-lock），M2 的 P7x 活体场景在 neuter 前后分别复现"正常完整跑通"与"删早退即重现原崩溃"两态、生产码红线（reading 不受限、scorer/golden/judge/config 零触碰）经主控独立全量 1456 passed + 9 xfailed 复核为真。**本批 7 finding + 本审新抓 F-R1 全部闭合，无新洞。批准合入。**

## 逐项闭合验证

### M1 正例 parity 锁 `test_real_draw_reading_archive_is_accepted_by_correction_guard`
- 内容核毕：真 sm21 case_data + 仓内真实 reading 产物（run_2026-06-20_gpt54_reading）+ **完整真 `_draw_reading`**（非手搓复刻）→ 真 `StageRunner.record`（断言 `recorded.accepted`）→ 真 `_draw_correction` 越过 guard 抵达 run_correction。非自指，符合出口条件原文。
- neuter 探针（任一侧约定改坏 → 锁应红）：**PASS** —— 两侧独立改坏均命中：① `_draw_reading` 侧改归档键（`vj.stem`→`vj.name`）→ 该锁单独红（AssertionError，`report.passed` 前置断言即挂，红因=archived output_obj 键约定漂移使 `recorded.accepted` 判定/后续 hash 不再自洽），余 7 绿；② guard 侧改序列化（`indent=2`→`indent=4`）→ 该锁单独红（`WindowResolverInputError` 于 window_sources.py:549 `accepted_attempt_mismatch`），余 7 绿。锁真绑两侧 parity 约定，双向独立、无连带。恢复后全绿。

### M2 判卷早退 + 真实形状回归锁 `test_correction_v3_grade_loop_skips_nonaccepted_attempt_and_scores_accepted`
- 内容核毕：早退精确落位 run_stage.py:1350-1351（`stage=="1_correction" and accepted_record is None` → 静默 None 三元组），scope 只 correction；注释明写 reading 不受限。共享 `_correction_v3_runstage_fixture`（真 `_stepwise_e4_run` 形状：001 base + 002 enrichment accepted）。
- 边角核毕：早退位于 F4-1 sidecar 检查之前，但同循环 accepted attempt 仍触发 warn/fail-closed → F4-1 语义无损。
- reading 段不受影响的锁 = F4-1 四条 warn/strict 测试本身（reading attempt 001 无 accepted record 仍抵达 sidecar 分支出 warn/raise；若早退误伤 reading 会静默 None 令 pytest.warns 失败）——r1 尾态四条全绿即证。
- 正常态 P7x 复跑：**PASS** —— 同一探针脚本原样复跑，输出 `correction attempts on disk: ['001','002'] | accepted: 2` + `LOOP COMPLETED: {"1": false, "2": true}`（循环完整不 raise、001=None、002 真分）。r0 轮的 `ScoreContractError: score_unsupported_combination` 崩溃已被早退挡住。
- neuter 探针（删早退 → 回归锁红 + P7x 崩重现）：**PASS** —— neuter 后 test_c2_b4b_phase_d.py **只有**新回归锁红（1 failed, 16 passed），红因 = `ScoreContractError`（score_service.py:131 capability 门）= 原崩溃原样重现；P7x 探针同步复现 `LOOP RAISED: score_unsupported_combination`。correction e2e（accepted attempt）与 reading 各锁均绿不连带。恢复后全绿。

### m1 cmd_run 孪生锁 `test_cmd_run_config_capability_profile_overrides_only_when_present`
- 内容核毕：present/absent 参数化，capture `_make_draw_fn` 断言 policy.capability_profile，经真 cmd_run。
- neuter 探针（run_stage.py:1748 cmd_run 接线退纯 CLI → present 支红）：**PASS** —— test_run_stage_flow.py 只有该锁 present-support 参数化用例红（1 failed, 18 passed），absent-support 用例及 cmd_flow 孪生锁均绿。恢复后全绿。

## 恢复核验
- 每条探针完成后立即单点回改；`grep -rn "NEUTER" src scripts tests` 零命中；`git diff | sha256sum` = `2a11c2723a66…`，与探针开跑前记录的 r1-tail 指纹逐字节一致。工作树 = sol 返工 r1 尾态，未 commit，无 Fable 探针残留。
