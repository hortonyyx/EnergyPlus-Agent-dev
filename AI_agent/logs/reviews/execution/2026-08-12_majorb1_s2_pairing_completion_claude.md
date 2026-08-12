# 执行日志 · MAJOR-B1 补齐 —— F-9 路线② S2 的 pairing decision 做完整

## 摘要（供快速核对）

- **`unevaluated_conditions` 补齐后是否为空**：**是**。`CURRENTLY_UNEVALUATED_POSITION_EVIDENCE_
  CONDITIONS == ()`，`CURRENTLY_EVALUATED_POSITION_EVIDENCE_CONDITIONS` 覆盖全六个 `ALL_POSITION_
  EVIDENCE_CONDITIONS`（`test_all_six_conditions_currently_evaluated_none_unevaluated` 锁死）。
  该字段本身**结构上不可能被静默留空**——见 §1.1 的 `_shape` validator 说明与 §2 的 coverage 锁记录。
- **全仓汇总行（最终，含 §5#6 补测）**：`2557 passed, 10 xfailed, 211 warnings in 416.96s`，
  **exit code 0**，日志内 `grep -c "FAILED\|ERROR"` = **0**。基线 2539 / 10 xfail / 0 红；
  本轮净增 **18 条测试**（`test_f9_route2_s2_authoritative_projector.py` 从 45 条增至 63 条），
  **零回归**。完整日志已存入仓库：
  [`2026-08-12_majorb1_fullsuite_final.stdout.log`](2026-08-12_majorb1_fullsuite_final.stdout.log)
  （本轮独立新文件名，非复用旧文件；中间还跑过一次 `claude_majorb1_fullsuite_20260812_141416.{log,rc}`
  = `2556 passed`〔`/tmp`，补 §5#6 那条测试前，未存档〕，补测试后重跑得到此最终版本）。

---

- **席位**：Claude 侧 Sonnet（执行档）
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `a17ed0f`，工作树干净（orchestrator 已用 `git status` 核实）
- **派工单**：[`2026-08-12_majorb1_s2_pairing_completion_dispatch_claude.md`](../request/2026-08-12_majorb1_s2_pairing_completion_dispatch_claude.md)
- **设计稿**：[`f9_route2_evidence_citation_design.md`](../../../proposals/f9_route2_evidence_citation_design.md) §5.3 / §10 S2 / §12.2
- **sol 裁决**：[`2026-08-12_round2_blocker1_and_bcd_crossreview_sol.md`](../verdict/2026-08-12_round2_blocker1_and_bcd_crossreview_sol.md) `MAJOR-B1`
- **文件所有权**：`src/agent/correction/window_position.py`（扩）+ `src/validator/checks/correction.py`（扩，仅 evidence 字典）+
  `tests/test_f9_route2_s2_authoritative_projector.py`（扩，既有 45 条测试全部保留并修正，新增 18 条，
  见 §1.3）。
  **未触碰** `envelope_transform.py` / `finalize.py` / `window_host.py` / `window_sources.py` / `deterministic.py` /
  `facade_convention.py` / `run_stage.py` / `pipeline.py`。备份见
  `AI_agent/backup/src_history/2026-08-12_majorb1/`（`.gitignore` `**/backup/**/20*_*/` 规则下不入库，符合既有约定）。

---

## §0. 防假验证自检（开工前，逐字兑现）

在 `_build_window_position_evidence_shadow_decision` 内、我计划插入条件 2/3 判定的确切位置
（既有 §5.1 同一 view 去重检查之后、逐 source 循环之前）插入
`raise AssertionError("MAJORB1_PROBE_reached_pre_mutual_nearest_point")`，
跑我打算用的验收命令 `pytest tests/test_f9_route2_s2_authoritative_projector.py`。

**结果**：15/32 个既有测试当场因该探针异常而失败（涵盖直接调用、`compute_window_position_evidence_shadow`
整链路、`check_correction` 异常兜底路径、两条真实入口 `_draw_correction`/`run_pipeline_artifacts`）。
**⇒ 我计划的判定点在真实验收命令下确实可达，不是假验证路径。** 探针随后立即撤回（`git diff --stat` 核实
撤回后与 HEAD 逐字节相同），未混入正式实现。

---

## §1. 改了什么

### 1.1 `src/agent/correction/window_position.py`（本次 +414 行 / 全部为新增或对既有函数的插入，无删除既有逻辑）

**新增的判定条件（设计稿 §5.3 条件 2/3/4）**：

- **条件 2·唯一 mutual-nearest**：`_build_window_position_evidence_shadow_decision` 的逐 source 循环内，
  在既有条件 1（距离容差）与条件 6（z-scope）判定之后，新增两段：
  - **elevation 侧**：为当前 `E_i` 构造候选域 = 全 catalog 中 `source_input_id` 相同（同一 elevation view）
    且 `resolve_elevation_source_floor_scope` 解析到与 `E_i` **相同** `floor_id` 的全部 elevation source；
    对候选域按到 `plan_world_interval` 的距离排序，要求 `E_i` 是唯一最近（`_is_unique_nearest`）。
  - **plan 侧**：为 `P` 构造候选域 = 全 catalog 中 `floor_ref` 与 `P` 相同、且经
    `_plan_source_consistent_with_family` 判定与 `window.facade` 家族一致的全部 plan source；
    对候选域按到 `E_i` 投影区间的距离排序，要求 `P` 是唯一最近。
  两侧任一失败 ⇒ `position_evidence_pair_mismatch`（model draw error，与既有距离超容差同码，
  设计稿 §9 错误词表本就把"cited pair 非唯一最佳、明显错配"与之合并）。
- **条件 3·ambiguity margin**：`_is_unique_nearest` 把"唯一最近"与"次优距离差 > 冻结的纯数值
  `PAIRING_AMBIGUITY_EPSILON_M = 1e-9`"合并成一个布尔判定（不允许调用方只查其中一半）——
  与 §12.2 的表述一致："两条件必须在同一决定里"。
- **条件 4·source 不复用**：这是**画布级**（draw-level）性质，单个窗口的决策函数看不到全局，因此实现在
  `compute_window_position_evidence_shadow` 的**第二遍**：`_detect_position_source_reuse` 收集
  所有 `decision=="accepted"` 决策各自的 `plan_locator` 与 `elevation_locators`，任何被 ≥2 个 accepted
  决策共同声称的 locator ⇒ 涉事窗口**全部**经 `_downgrade_decision_to_rejected` 降级为
  `rejected`/`position_evidence_authority_invalid`（设计稿 §9 明确把"source 复用"归入此码）。
  已 rejected 的决策不参与（未赢得过任何权威，无所谓"抢"）。

**MAJOR-B1 语义修法（coverage 声明，任务书 §3）**：

- 新增 6 个具名条件常量（`POSITION_EVIDENCE_CONDITION_*`）+ `ALL_POSITION_EVIDENCE_CONDITIONS`（冻结元组）+
  `POSITION_EVIDENCE_RULESET_VERSION = "f9_route2_s2_position_evidence_ruleset_v2"` +
  `CURRENTLY_EVALUATED_POSITION_EVIDENCE_CONDITIONS`（= 全六条）/
  `CURRENTLY_UNEVALUATED_POSITION_EVIDENCE_CONDITIONS`（= 空）。
- `WindowPositionEvidenceShadowReportV1` 新增三字段：`ruleset_version` / `evaluated_conditions` /
  `unevaluated_conditions`，并在 `_shape` validator 里加了**类型级**约束：
  ① 两个条件列表必须互斥、并集恰为 `ALL_POSITION_EVIDENCE_CONDITIONS`（条件不能悄悄消失）；
  ② **`unevaluated_conditions` 非空时 `all_accepted` 不能为 `True`**——这是 sol finding 的直接回应：
  "shadow 用无修饰的 accepted/PASS 表达只覆盖部分判据的结果" 现在**结构上不可能构造出来**，
  不依赖任何消费方记得检查。

**架构发现（写入代码注释，非事先设计好的）**：实现条件 2 时，若不对 plan 侧候选域按 facade family 过滤，
真实"clean" e2e 产物（`case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e`，此前记录的
"15/15 全 accept" 基线）会有 **6/15 扇窗**因建筑本身的南北/东西对称性（同一 along 坐标上北墙和南墙
各有一扇窗）产生几何真实的同分——这不是我编造的边缘情形，是真实产物里已经存在的数据形状。
详细分析与两种被排除的方案（bbox 极值——`facade_convention.FACADE_BASE_PLANE_SIDE` 的文档字面禁止
"window-position 用单一 bbox 极值当墙面"；以及"仅用引用关系推断家族"——会让算法瞎眼于未引用候选，
违反条件 2 本身要求扫全 catalog 的目的）见 §5。采用的解法：`_plan_source_consistent_with_family`
用**已经物化好的** `geom.facade_segments`（Vg，源自建筑自身多边形边，非 bbox 极值，也不依赖任何窗口引用）
判定候选是否与目标家族的某段墙一致。**实测两个真实 fixture（F-9 crash / clean）零假阳性**（见 §4）。

### 1.2 `src/validator/checks/correction.py`（+21 行，仅 evidence 字典扩充，未改判定逻辑）

`_window_position_evidence_shadow` 的 evidence 字典新增三个字段（`ruleset_version` /
`evaluated_conditions` / `unevaluated_conditions`），在 PASS/FAIL 两个分支、以及 `binding_unavailable`
分支都填充——这是 sol finding 指名的"机器可读 coverage"落地到消费方实际会读到的位置
（check evidence，不是内部 report 对象）。**判定逻辑本身未改一行**：`if shadow.all_accepted: add_pass
else: add_fail` 保持原样——因为 `WindowPositionEvidenceShadowReportV1` 自身的类型级不变式已经保证
"unevaluated 非空时 all_accepted 不可能是 True"，这里不需要（也不应该）再加一层运行时防御性检查。

### 1.3 `tests/test_f9_route2_s2_authoritative_projector.py`（+675 行 / -16 行）

- **既有 45 条测试全部保留**，其中因新签名（`_build_window_position_evidence_shadow_decision` 新增
  `catalog=`/`facade_segments=` 两个必填 kwarg）需要改调用点的 11 处全部更新；因新字段
  （`WindowPositionEvidenceShadowReportV1` 新增三字段）需要改直接构造的 1 处更新。
- **新增 18 条测试**，覆盖条件 2（3 条 + 1 条 §5#6 记录的行为变化）/ 条件 3（2 条）/ §12.2 顺序锁（1 条）/
  条件 4（3 条）/ coverage 锁（5 条）/ 两个新增 must-red neuter（2 条）；另加两个共享 fixture helper
  （`_hand_segment` / `_rejected_hand_decision`）+ 一个哈希 helper（`_report_content_sha256`）。
- **一处发现并修正的假锁**（见 §4"遮蔽自查"）：`test_zscope_neuter_disabling_scope_check_causes_false_accept`
  被我的新代码意外遮蔽，已重写为诚实记录该发现的 `test_zscope_global_neuter_now_masked_by_mutual_nearest_
  domain_gap` + 新增外科手术式隔离测试 `test_zscope_window_floor_mismatch_check_alone_is_load_bearing`。
- **另一处发现并修正的假锁**（同样见 §4）：`test_coverage_lock_report_cannot_claim_all_accepted_with_
  unevaluated_conditions` 与 `test_report_evaluated_and_unevaluated_conditions_must_partition_full_set`
  最初用占位符 `content_sha256="0"*64`，导致无论目标不变式是否生效，构造都会因哈希不符而报
  `ValidationError`——两者都已改用正确计算的哈希（`_report_content_sha256` helper），并各自补了
  "同一形状、去掉目标违规后应合法构造成功"的自证。

---

## §2. 每把锁绑什么 + 自证前提实测

| 锁 | 断言的 check-id / 函数 | 自证前提 | 结果 |
|---|---|---|---|
| 条件 2·uncited 更近候选 | `_build_window_position_evidence_shadow_decision` 直接返回值 | `test_condition2_without_the_closer_candidate_same_fixture_still_accepts`：去掉更近候选后同一夹具改判 accepted，证明拒绝确由该候选的存在造成 | `test_condition2_uncited_closer_candidate_causes_pair_mismatch` PASS，`reject_code=="position_evidence_pair_mismatch"`，且被引源自身距离（0.10）原样保留、未被静默替换 |
| 条件 2·不同 view 不竞争 | 同上 | 反例本身即证明域过滤按 `source_input_id` 生效 | `test_condition2_different_view_candidate_never_competes` PASS |
| 条件 3·ambiguity margin | 同上 | `test_condition3_margin_comfortably_outside_epsilon_accepts`：margin 拉大 20 倍后同一夹具改判 accepted | `test_condition3_near_tie_within_epsilon_is_ambiguous_and_rejected` PASS（margin=eps/2 时拒绝，尽管 cited 严格意义上仍是"最近"——证明条件 3 独立于条件 2 起作用） |
| §12.2 顺序锁（scope 先于排名） | `_build_window_position_evidence_shadow_decision` | `baseline.decision=="accepted"` 断言先行（真实 East_view S3/S4 同 along 不同层） | `test_scope_filter_before_ranking_order_lock` PASS；坍缩 scope 解析后同一引用**改判 rejected**（`pair_mismatch`），证明排名前确实先过了 scope 过滤 |
| 条件 4·source 复用 | `_detect_position_source_reuse` | 两窗口**独立**验证各自 accepted（`assert decision_a.decision=="accepted" and decision_b.decision=="accepted"`）后才应用复用检测——证明不是靠其他条件顺带拦下 | `test_condition4_both_windows_rejected_when_sharing_plan_authority` PASS，两窗口均降级为 `position_evidence_authority_invalid` |
| 条件 4·非阻塞性（targeted 不是 blanket） | 同上 | 单一非碰撞决策 passthrough 校验 + 已拒绝窗口不拖累 accepted 窗口 | `test_condition4_reuse_pass_is_targeted_not_a_blanket_reject` PASS |
| 条件 4·真实入口接线 | `compute_window_position_evidence_shadow` | `baseline.all_accepted is True`（真实 clean run） | `test_condition4_wiring_report_level_pass_is_consumed` PASS——neuter 后（见 §3）`all_accepted` 翻转，证明返回值被真正消费而非弃置 |
| coverage 锁·partition 完整性 | `WindowPositionEvidenceShadowReportV1._shape` | 正确哈希下、去掉违规形状后同一构造合法 | `test_report_evaluated_and_unevaluated_conditions_must_partition_full_set` PASS（两次均用 `_report_content_sha256` 正确计算，非占位符——见 §4 假锁记录） |
| coverage 锁·PASS 不得强于覆盖 | 同上 | 同一部分覆盖形状、`all_accepted=False`（诚实）时合法构造 | `test_coverage_lock_report_cannot_claim_all_accepted_with_unevaluated_conditions` PASS |
| coverage 锁·真实产物携带声明 | `compute_window_position_evidence_shadow` / `check_correction` | 直接读真实 clean run 产物 | `test_real_report_carries_ruleset_version_and_full_coverage` / `test_check_correction_evidence_dict_exposes_coverage_fields` PASS |

---

## §3. neuter 两方向（均在 `/tmp` 完成，做完已还原，主工作树零改动）

**方法**：不是在测试文件内 monkeypatch（那只证明"我自己设计的反例夹具能被拦下"），而是把
**整份工作树**（含我本轮全部改动）`tar` 复制到 `/tmp/.../majorb1_neuter/repo`，在**源码层面**直接删除/
短路目标函数体，跑同一份 `pytest tests/test_f9_route2_s2_authoritative_projector.py`，观察哪些测试翻红、
是否精确命中预期、有无意外连带。每次neuter前先 `cp` 一份主工作树的当前版本覆盖 `/tmp` 副本（保证每次
neuter都是从"干净"状态开始，不叠加上一次的改动）。全部 4 轮 neuter 完成后 `/tmp` 目录整个丢弃，
**未对主工作树做任何 `git checkout/stash/clean/reset`**（因为主工作树从未被这些 neuter 触碰）。

### 方向 A（机制）：`_is_unique_nearest` 源码短路为恒 `return True`

覆盖条件 2+3 的核心合并判定。结果：**5 个精确命中、57 个不受影响**：

```
FAILED test_condition3_near_tie_within_epsilon_is_ambiguous_and_rejected
FAILED test_condition2_uncited_closer_candidate_causes_pair_mismatch
FAILED test_zscope_global_neuter_now_masked_by_mutual_nearest_domain_gap
FAILED test_scope_filter_before_ranking_order_lock
FAILED test_neuter_disable_plan_family_filter_reintroduces_symmetric_false_reject
5 failed, 57 passed
```

后两者的翻红是**预期的级联**（不是误伤）：`test_zscope_global_neuter_...` 本来就是靠 mutual-nearest
兜底才正确拒绝（它自己的 docstring 记录了这个事实）；`test_neuter_disable_plan_family_filter_...`
自身内部也调用了 `_is_unique_nearest`（家族过滤只是缩小候选域，最终判定仍要过 mutual-nearest），
两把锁叠加时外层锁失效会连带内层锁的断言前提失效——这不是"锁的分辨力不够"，是两把锁本来就
不是相互独立的电路（家族过滤是 mutual-nearest 的输入，不是并联的另一条通路）。

### 方向 B（接线）：`_detect_position_source_reuse` 源码短路为恒等 `return decisions`

覆盖条件 4（画布级第二遍）。结果：**1 个精确命中、61 个不受影响**：

```
FAILED test_condition4_both_windows_rejected_when_sharing_plan_authority
1 failed, 61 passed
```

`test_condition4_wiring_report_level_pass_is_consumed`（接线锁）**没有**翻红——这是对的，
它测的是"`compute_window_position_evidence_shadow` 是否消费该函数的返回值"，与该函数**自身实现**
是否正确是两件事；它靠**自己的 monkeypatch**（把函数换成"全部降级"而不是"改用真实算法"）驱动，
不依赖被 neuter 掉的那份真实算法，因此这份 neuter 下仍然通过——恰好证明这把锁测的是**接线**、
不是碰巧靠算法本身的正确性通过。

### 方向 C（补充）：`_plan_source_consistent_with_family` 源码短路为恒 `return True`

针对 §1.1 提到的"架构发现"——facade-segment 家族过滤本身是否真的承重。结果：**12 个翻红**，
波及范围明显更大（F-9 oracle 的 11/4 拆分、clean run 的 15/15、多个真实入口测试）：

```
12 failed, 50 passed
```

这个更宽的爆炸半径是**预期且正确的**：该过滤器是防止"建筑对称导致假同分"这一**全局性**问题的
唯一防线，一旦失效，影响面自然覆盖所有依赖"clean=15/15"这一基线事实的下游测试——这不是锁范围
划分不清，是这个函数本来就是多个测试共享的前提。

### 方向 D（coverage 锁本身）：`WindowPositionEvidenceShadowReportV1._shape` 里
`if unevaluated_conditions and all_accepted: raise` 整段注释掉

**首次跑时发现真实假锁**：`test_coverage_lock_report_cannot_claim_all_accepted_with_unevaluated_
conditions` 用占位符哈希 `"0"*64`，在这一段被禁用后**依然通过**（因为它本来就是靠哈希不匹配的
`ValidationError` 通过的，与目标不变式无关）——已在 §4 记录并修正。**修正后重新 neuter 验证**：

```
FAILED test_coverage_lock_report_cannot_claim_all_accepted_with_unevaluated_conditions
  Failed: DID NOT RAISE <class 'pydantic_core._pydantic_core.ValidationError'>
1 failed, 1 passed
```

修正后精确命中，`test_report_evaluated_and_unevaluated_conditions_must_partition_full_set`
（测的是不同的不变式——partition 完整性，未被这次 neuter 触碰）不受影响。

---

## §4. 遮蔽自查（本轮实际抓到的两处，如实记录）

1. **z-scope 全局 neuter 被我的新代码意外遮蔽**：设计稿/既有测试原本用
   `resolve_elevation_source_floor_scope` 恒返回 `not_declared` 来证明"z-scope 与窗口楼层不一致"这条
   原有检查是承重的。我的新 mutual-nearest 域构造**同样调用**这个函数（构造 elevation 候选域时要知道
   每个候选属于哪层），因此同一个全局 neuter 现在**同时**打瞎两条防线，不再能单独证明"原检查"本身
   承重——旧检查被新检查**遮蔽**了。处置：诚实重写该测试记录这一发现（不是删除或悄悄改断言），
   另加一把**外科手术式隔离**的新锁（只欺骗 `window.floor_id` 本身，不碰 `resolve_elevation_source_
   floor_scope`，从而只废掉原检查、不影响新检查赖以构造候选域的同一次调用）——证明原检查在**新代码
   存在的前提下**依然独立承重。
2. **coverage 锁的两个直接构造测试最初是假锁**：用占位符 `content_sha256` 导致
   `pytest.raises(ValidationError)` 永远能通过（哈希本身就是错的），与目标不变式（partition 完整性 /
   PASS-vs-coverage 互斥）是否生效**无关**。这条是在**方向 D 的 neuter 里**才现形的（neuter 前独立
   review 没有发现，因为"测试通过"看起来完全正常）——`/tmp` neuter 是发现它的唯一渠道。
   已用正确计算哈希的 `_report_content_sha256` helper 重写并补充自证（见 §1.3、§3 方向 D）。

**方法论落地**：本轮两次假锁发现都印证了同一条纪律——**验证锁必须真的移除目标机制、观察是否翻红，
不能只看"测试通过"就认定断言真的在测目标**。这与 CLAUDE.md 里"⛔ 恒等锁不算正确性锁"是同一件事的
另一种表现形式（这里是"总会失败的锁不算正确性锁"）。

---

## §5. 未决判断（如实列出，供 sol 复审时重点核对）

1. **facade-segment 家族过滤是本轮唯一发明的、设计稿没有逐字给出算法的部分**——设计稿 §5.3 条件 2
   写"该 scope 同 floor_ref plan 域"（字面上未提"family"），但只按字面实现（不加家族过滤）会在真实
   clean run 上产生 6/15 假拒绝（用只读 `python3 -c` 脚本直接读取真实 fixture 的 `verified_inputs`/
   `geom` 实测确认、非猜测——只读探索，未写文件、未改动任何代码，过程未单独存档，本记录 §1.1/§3
   方向 C 是唯一书面留痕）。我认为设计稿 §14.1 第 2 条自己承认的低置信区间
   （"请重点构造重复等宽窗...的反例"）正是指向这个缺口，
   并采用了设计稿明确许可、`facade.py::derive_facade_frame` 文档明确指出"新代码应该用"的替代方案
   （Vg 分段而非 bbox 极值）。**但这是我在实现期间做的架构判断，不是逐字照抄设计稿**，请 sol 复审
   时重点核实这个判断本身站不站得住，而不是只核实"条件 2/3/4 是否存在"。
2. **`_plan_source_consistent_with_family` 依赖 `geom.facade_segments` 已被物化**——本轮通过读
   `finalize.py` 与两条真实入口的调用顺序（`finalize_correction_draw` 先于 `check_correction`）确认了
   这在**当前**（S2、非阻塞 shadow）的实际接线下总是成立；但如果未来 S3/S4 把这套判定挪到 hydration
   之前（设计稿 §8.3 的顺序），facade_segments 届时可能还不存在。本轮**没有**为"facade_segments 为空"
   写显式的 typed 拒绝路径（只是自然地让候选域为空 ⇒ `position_evidence_insufficient`，fail-closed，
   但没有专门的错误码区分"真的没有候选"与"facade_segments 本身还没算出来"）——留给 S3/S4 施工时
   处理，因为那时候审计路径本来就要整体重排。
3. **条件 5（"plan 的 plane interval...与 model 的...facade...claim 一致"）没有独立的判定代码或
   独立的错误码**——本轮把它作为 facade-segment 过滤器的**副作用**实现（P 自身若与其宣称的 facade
   家族在几何上不一致，会被排除出自己的候选域，进而在"P 是否为唯一最近"判定里失败）。这个副作用
   已被条件 2 的测试间接覆盖，但**没有一把锁专门只测条件 5、和条件 2/3 解耦**。如果这个副作用关系
   将来因为其他改动断开，不会有专门的锁独立报警——这是我认为可接受的取舍（任务书明确只要求补齐
   条件 2/3/4），但如实列出供复审判断是否需要补一把独立锁。
4. **`_hand_segment` 测试 helper 里 East/West 家族的 `p1`/`p2` 构造方式未被真实数据验证**——所有
   hand-typed 测试只用了 North 家族（`_identity_frame` 默认 North），East/West 分支的
   `_plan_source_consistent_with_family` 逻辑只被**真实**（非 hand-typed）F-9/clean fixture 覆盖
   （那两个 fixture 确实有 East/West 窗口，已在真实数据上验证——见 `test_condition2_*` 之外、
   既有 `test_east_view_*` 系列全部保留且通过）。
5. **没有为条件 4 写通过真实 `geom`/`VerifiedWindowResolverInputs`（而非 hand-typed 或
   `_detect_position_source_reuse` 直接单元测试）构造出真实几何冲突场景的测试**——真实 F-9/clean
   fixture 里没有天然的"两窗口抢同一证据"场景，人工在 `claim_links` 层面伪造这种场景又会先撞上条件 1
   （距离超容差，见任务执行期间的分析），所以条件 4 的算法测试改用了 hand-typed 场景（两窗口位置
   完全重合），真实入口部分则只验证了"接线"（`test_condition4_wiring_report_level_pass_is_consumed`
   用 monkeypatch 而非真实冲突数据）。**这不是假验证**（monkeypatch 测的是接线这一独立性质，
   已在 §3 方向 B 说明其与算法测试的分工），但如实标注这条组合尚未有"真实入口 + 真实冲突几何"
   的端到端一体化证据。
6. **发现一处真实行为变化（非任务书字面要求，实现条件 2 的必然副作用）**——补齐前，一个 z 数据
   完全缺失（`resolve_elevation_source_floor_scope` 返回 `"not_declared"`）的被引 elevation source，
   只要 along 距离在容差内，会被**既有两道守卫都放过**（`status=="unresolved"` 与
   `status=="resolved" 且楼层不符` 两个检查都要求一个确定的 status，`not_declared` 两边都碰不到）
   ⇒ **静默 accepted**。用回退到本轮改动前的模块（`AI_agent/backup/src_history/2026-08-12_majorb1/
   window_position.py.orig`）在同一夹具上实测复现，确认这是补齐前的真实行为，不是我编造的假设。
   本轮加入条件 2 后，elevation 侧候选域只接纳 `status=="resolved"` 的候选（无法排名的 scope 无法参与
   排名），被引源自己若是 `not_declared` 就永远进不了自己的候选域 ⇒ 空域 ⇒ 判 `pair_mismatch`。
   **判断**：认定这是正确的收紧（v2.1 §2.1 规则 10"无隐式 fallback...scope 不唯一时均 fail closed"
   本就要求这一类行为），而非应该保留的旧行为——刻意保留旧行为需要专门为"z 缺失"开一个绕过 mutual-
   nearest 校验的口子，那本身就是一个可被利用的漏洞（模型只要不填 z 就能跳过条件 2/3）。**真实
   F-9/clean fixture 均未触发**（两份 catalog 里每条 elevation source 的 `local_z_interval` 都非空，
   已核实），已补测试 `test_condition2_side_effect_undeclared_z_scope_now_rejects_not_silently_accepts`
   锁定新行为并写明新旧对照。**请 sol 复审时重点核实这条"判断"本身，而不只是核实测试存在。**
