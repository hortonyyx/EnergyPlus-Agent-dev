# B4b Phase C 执行审 r1（Opus 子代理，升一档交叉，独立上下文 + 活体探针）

**审对象**：terra 施工的 B4b Phase C（elevation/fusion/policy/capability 完整面）。
**基座**：HEAD `04d293d`，改动未 commit（工作树）。
**合同**：派工单 `request/2026-07-17_b4b_phaseC_construction_dispatch.md` + 细稿 `c2_b4b_detail_spec.md` §13 Phase C / §7.3–7.5 / §8.4.1 / §8.5–8.8 / §9.2 / §4.2 / §6.6–6.7 + REC-C verdict。
**改动文件**：`src/agent/judge/{elevation_score,opening_claim_score,score_policy}.py` + `tests/test_c2_b4b_phase_c.py` + `tests/test_c2_b4b_phase_b.py`（fixture 扩 `complete_elevation`）。
**定向套自验**：`tests/test_c2_b4b_phase_c.py tests/test_c2_b4b_phase_b.py tests/test_elevation_score.py` = **61 passed**（非假绿基线）。

---

## 总裁决：**REWORK**

抓到 1 条 MAJOR（活体探针 CONFIRMED）：trusted-negative conflict 逻辑过火，把**正确放置的窗**判成 `conflict`，直接违反细稿 §8.6.1 item 1 与其收尾禁令；且 C3 负轴测试锁死了这一错误期望（false-green，同时使 item 2 真·trusted-negative conflict 路径实际未被测）。另有 3 条 MINOR。禁区/锁定/信任根/Va 唯一引擎/NA override 全部干净。

---

## Findings

### MAJOR-1 ｜ trusted-negative conflict 过火，正确产品被误判 conflict（CONFIRMED）
- **文件:行**：`src/agent/judge/opening_claim_score.py:554–566`（`positive_inputs` / `negative_inputs` / `negative_conflict` / `base_result`）；`score_plan_claims` 里的 Phase-B 同型逻辑 `opening_claim_score.py:421–424` 同病（Phase B 已 CLOSED，本轮不返工但登记）。
- **测试 false-green**：`tests/test_c2_b4b_phase_c.py:187–196`（`test_b4b_c3_trusted_negative_only_conflicts_when_a_different_source_is_positive`）断言的正是这条错误行为。
- **根因**：`negative_inputs` 只把「有产品观测的 source」排除在负证据 conflict 之外（`source_id not in positive_inputs`，而 `positive_inputs` = 产品观测的 input_id），**没有排除「在 reference ledger 里携带 GT positive 声明的 source」**。Va（冻结）对每个 completeness-capable source 一律输出 `negative_evidence_intervals`——**包括那些同时带 GT positive 的 source**。于是只要一个 target 的 GT `source_refs` 含冗余的 complete elevation 视图，而产品没给这些视图逐一交观测，正确的窗就会被判 conflict。代码同时在「用缺失的产品观测反推'图上没画'」——正是 §8.6.1 收尾句 "这条只消费 Va 已输出的 negative intervals，不自行推断'图上没画'" 明文禁止的。
- **失败场景（探针实证，真 fixture + 真 Va，无 mock）**：
  - PROBE 0：reference ledger 中 O1/along 的三个 source `plan-F1 / elev-N / elev-N-detail` **全部** `positive_declared=True` 且 `negative=(0.3,0.7)` 覆盖同一区间 —— 正是 §8.6.1 item 1 定义的 "同一 source 同一区间同时出现 GT positive declaration 与 trusted negative absence" 自相矛盾配置。
  - PROBE 1：产品 = 一份**正确的** plan 观测（span 精确命中）→ `along.result = conflict`。正确语义应为 `complete`（产品按 plan 正确放置；elev-N/-detail 的负证据源本身就是 GT 声明的 positive 源，item 1 禁止把它转嫁成 miss/conflict）。此 conflict **纯**来自 negative_conflict（`positive_conflict=False`，因单一 source 无 miss）。
  - PROBE 2：产品 = 正确 plan + 正确 elev-N，仅漏掉**冗余的** elev-N-detail → 仍 `conflict`。即一个各观测源都与 GT 一致的正确产品，只因没给某个冗余 complete 源交观测就翻车。
  - PROBE 3：产品把三源全交（plan+elev-N+elev-N-detail）才 → `complete`。评分正确性被绑死在「产品必须为每个冗余 complete 源都交观测」，脆弱且与 §8.6.1 相悖。
- **spec 锚点**：§8.6.1 item 1（GT positive + trusted negative 同源同区间 = reference/manifest 自相矛盾，REJECTED，**不把矛盾转嫁成产品 miss**）；item 5（无 completeness/遮挡/裁切/区间外缺失**不产生** conflict）；收尾句（不自行推断「图上没画」）。
- **连带影响**：因当前 fixture 的 completeness 均匀施加且窗的 `source_refs` 含 elevation，C3 负轴测试实际走的是 item-1 违规路径，**item 2 真·trusted-negative conflict（negative 源无 GT positive、无产品 positive，另一源有产品 positive）从未被真正测到**。
- **修法方向**：negative-conflict 的 negative 源集合应额外排除「reference decision 有 `positive_evidence_declared` / 非空 `applicable_intervals`」的 source（item 1：声明了 positive 的源不能同时充当 absence 证人）；且不得以「无匹配产品观测」等价于「产品声明缺失」——真·trusted-negative conflict 应消费**产品/absence ledger 明确声明的缺失**（§7.5 absence 架构），而非 reference ledger 的 capability 减去已匹配观测。返工须连带改 C3 负轴测试为**真**item-2 场景（构造 negative-capable 但无 GT positive 的源），并补一条「正确产品单 plan 观测 → complete，不 conflict」的回归。

### MINOR-1 ｜ `walls_complete` 与 `boundary_complete` 喂同一 `segment_rows`（CONFIRMED）
- **文件:行**：`src/agent/judge/score_policy.py:106–107`（两 criterion 均 `rows=segment_rows`）。
- **实证**：PROBE 7 —— 两 criterion 的 denominator/failing/verdict 恒等。细稿 §9.2 把 walls_complete 与 boundary_complete 列为**不同** criteria。segment scorer 若产出可区分的 wall vs boundary row，policy 应分区喂入；当前二者永远相同。
- **现状轻**：Phase C 测试 `segment_rows` 默认 `()`（两者皆 NA），故潜伏未爆；接线后即错。
- **修法**：按 row 的 wall/boundary 归属分区，或在 §9.2 wire 明确 boundary 的独立 row 来源。

### MINOR-2 ｜ `window_elevation_geometry` 缺「受支持的 along/width」（CONFIRMED）
- **文件:行**：`score_policy.py:110`（`rows=by_claim["sill"] + by_claim["head"]`）。
- 细稿 §9.2 line 1347 定义该 criterion = 「sill/head **及受支持的 along/width**」。当前只含 sill/head。
- **张力**：v3 row 模型每 target 只有一条 channel-fused 的 along/width row，elevation-channel 的 along/width 不可分离——所以该 criterion 按细稿字面**不可完整表达**。属 spec↔模型的接缝缺口，建议主控裁决是「接受当前 sill/head-only + 记债」还是「细稿降义」。

### MINOR-3（观察，不阻断）｜ `no_oversplit` / `negative_evidence_complete` 永久 NA
- **文件:行**：`score_policy.py:112–113`（两者 `rows=()`）。
- 实证 PROBE 7：两 criterion 恒 `eligible=False`。细稿 §9.2 列为核心 criteria 但 Phase C 无 oversplit scorer / negative-evidence-completeness 聚合器，NA 可辩护；登记为 Phase C 范围内的 inert criterion，供后续 phase 接线。

---

## 探针记录（活体，真 fixture `tests/b4b_contract_fixture.py` + 真 Va 调用）
| Probe | 攻击面 | 结论 |
|---|---|---|
| PROBE 0 | 信任根/负证据结构 | reference ledger O1/along 三源全 `positive_declared=True` 且 negative 覆盖同区间 = §8.6.1 item1 矛盾配置（CONFIRMED 前提） |
| PROBE 1 | ③totality/负证据过火 | 正确单-plan 产品 → **conflict**（应 complete）= MAJOR-1 实证 |
| PROBE 2 | 过火脆弱性 | 正确 plan+elev-N、漏冗余 elev-N-detail → **conflict** = MAJOR-1 加重实证 |
| PROBE 3 | 对照 | 三源全交才 complete，坐实「绑死于每冗余源必交观测」 |
| PROBE 4 | ①frame 信任根 | `OpeningObservation`/`TypedElevationObservation` **零** frame 字段（mirror/local_x/sign/along_origin 均无）→ 产品无法注入 frame；denominator 仅来自 Va reference ledger。攻击面**类型层不存在**（最强防御） |
| PROBE 5 | ④NA override 先于 coverage | 即便喂充分 elevation 证据，appearance 仍 `not_applicable / reference_value_unavailable / units=0.0`（`eligible_units` line 324 短路先于 applicable 计算） |
| PROBE 6 | ③弱 partial 不自动拼 full | partial A=0.4/T=1.0 → units=0.4 ≤ 1；denominator 由 Va totality 封顶，scorer 不跨源累加分母 |
| PROBE 7 | ⑥policy 守恒/criteria | 守恒成立（passing+failing=denominator）；但 walls==boundary（MINOR-1）、no_oversplit/neg_evidence 恒 NA（MINOR-3） |
| PROBE 8 | §9.2 组成 | window_elevation_geometry 仅 sill/head（MINOR-2） |

**信任根攻击探针（派工单 ①③④ 专项）结论**：
- ① frame 信任根：**干净**。产品对象无任何 frame 同名字段，projection 只用受信 `ElevationViewBindingV1.sign/along_origin`；denominator 全程来自 Va reference ledger，产品 frame 无穿透路径。
- ③ 弱 partial 拼 full：**干净**（PROBE 6，Va totality 封顶）。但**同族 ③ 的负证据 totality 分支被 MAJOR-1 击穿**——不是「拼成 full」型假绿，而是「负证据反向把正确 union 判 conflict」型过火。
- ④ NA override：**干净**（PROBE 5）。

---

## 禁区 / 锁定 / 信任根合规
- **Va 唯一引擎（②）**：`score_opening_claims_v3` 的 units/applicable 全读自 `reference_ledger`（Va 输出），未在 scorer 内重实现「看起来可见」判据；C1 "shorter visible intervals only shrink Va output" 测试证明收窄只由 Va 公共通道发生。`eligible_units` 委托 Va status/reason。**干净**。
- **frame 只从受信 bindings（gate C1）**：见 PROBE 4。**干净**。
- **judge-only**：`grep` 确认生产路径（pipeline/correction/reading/execution）**零 import** 本批 v3 模块（`score_opening_claims_v3`/`c2_v3_score_policy`/`project_typed_elevation_observation`/`score_typed_elevation_floor_lines` 无任何非测试调用点）。step_orchestrator 仅 import 既有 verdict/executor（Phase A/B 前既存）。**干净**。
- **facade_applicability.py（Va 生产侧）**：`git diff --stat` = 空，**一行未动**。**干净**。
- **import footgun（REC-C O2）**：`elevation_score.py` 与 `opening_claim_score.py` 与测试均 `from src.agent.correction.facade_applicability import ElevationViewBindingV1`（Va 13 字段那个），**未**误引 `gt_manifest` 的 15 字段同名类型。**干净**。
- **legacy 锁定**：`score_plan_claims` / `reading_score_criteria` / legacy elevation scorer / renderer 语义**未改**（diff 全为 additive 旁路）。**干净**。
- **Phase D 领地未越界**：diff 无 `SCORER_SCHEMA "7"→"8"`、无 sidecar/PNG 原子 pair、无 typed polygon renderer / gray hatch、无 CLI dispatch、无 legacy v2 regression 封口、无 VA-C7 债务扫描。**干净**。

## 未连接接缝（观察，非 finding）
- `project_typed_elevation_observation`（§7.3/§8.8 elevation actual-segment projection）是**独立函数，未接入** `score_opening_claims_v3`（后者收已投影好的 `world_along_interval`）。故 gate C1 frame-trust 仅在单元层证明，projection→scorer 端到端接缝在本 diff 内**未演示**。是否属 Phase C 应交的接线，请主控对派工单 §13 Phase C item 1 核定；若判为应接线未接 = 披露偏差（简报「未决·偏离：none」未提及此接缝未连）。

## review-ask 裁决
简报 "Review ask: none"。**核实属实**——无需主控裁决的 review-ask 项。

## 覆盖净变化 / 安全锁
- 净增 19 条 Phase C 测试 + phase_b fixture 扩 `complete_elevation` 参数；无删除既有测试、无移除守恒 guard（`summarize_claim_rows` totality 检查仍在、`c2_v3_score_policy` 的 `score_denominator_nonconserving` raise 仍在）。
- **无安全锁丢失**。MAJOR-1 是逻辑过火 bug（错误方向：把正确判成 conflict），非「放松了某道门」；但它使一条负轴测试成为 false-green，掩盖了 item-2 真路径的缺测。

---

## 负轴测试逐条审（shipped-untested 专查）
| 测试 | 真断言? | 结论 |
|---|---|---|
| c1 forward/inverse restores world target | 是（参数化 sign/mirror/local + 精确恢复 T） | ✓ 真 |
| c1 true/unknown reject | 是（`pytest.raises score_direction_unresolved`） | ✓ 真 |
| c1 shorter visible only shrink Va | 是（Va 输出收窄 + positive evidence 不变） | ✓ 真 |
| c2 elevation/appearance NA | 是（existence complete + appearance NA/reason/units） | ✓ 真 |
| c2 partial binary + floor lines actual z | 是（eligible_units 二值 + floor-line 状态序列） | ✓ 真 |
| c2 multi-source fuse | 是（complete + 两 id 入 matched） | ✓ 真（但依赖「全冗余源都观测」——MAJOR-1 的镜像面） |
| c2 host correct/wrong/ambiguous | 是（complete/miss + ambiguous raise） | ✓ 真 |
| c3 fusion positive-conflict（elev-bad） | 是（两产品 positive 互斥 → conflict） | ✓ 真（genuine positive conflict） |
| **c3 trusted-negative conflict** | 断言了行为，但**断言的是错误行为** | ✗ **false-green（MAJOR-1）** |
| c4 unsupported schema + door NA | 是（decide_score_capability NA + door unsupported_target_kind） | ✓ 真 |
| c5 policy conservation / all-NA / rejected | 是（fail + 守恒 + NA + totality_valid=False→rejected） | ✓ 真 |

签字：Opus 4.8 执行审子代理，2026-07-17。

---

## r2 闭环复审（Opus 子代理，重跑 r1 探针确认闭合，2026-07-17）

**方法**：不从头再审；读返工 diff（`opening_claim_score`/`score_policy`/`elevation_score` + 两测试文件）→ 重跑 r1 关键探针 → 跑定向套。定向套 `test_c2_b4b_phase_c + phase_b + elevation_score` = **64 passed**（r1 时 61，+3 返工新增）。主控已独立核 diff + 全量 1216 绿 + 9 xfail。

### 闭环裁决：**APPROVE**

MAJOR-1 与 3 条 MINOR 全部闭合，无新洞，禁区/信任根/judge-only 复核仍干净。

### 逐条闭合状态（探针实证）
| Finding | 返工 | 探针实证 | 状态 |
|---|---|---|---|
| **MAJOR-1** trusted-negative 过火 | `negative_inputs` 现要求 `source_id in declared_absences`（来自**产品 ledger** 显式 absence via `_explicit_product_absence_sources`）+ `not positive_evidence_declared and not applicable_intervals`；v3 加 `product_ledger` 参数（缺省 None→无 trusted-negative conflict） | 重跑 PROBE 1：正确单-plan 产品 → **complete**（r1 是 conflict）；PROBE 2：正确 plan+elev-N、漏冗余 elev-N-detail → **complete**（脆弱性消除）；PROBE 3 对照不再需要三源全交 | **CLOSED** |
| **Phase B twin**（r1 登记 421-424） | `score_plan_claims` 的 `negative_sources` 同加 `not positive_evidence_declared and not applicable_intervals`（`opening_claim_score.py:419-426`） | 旧 false-green `..._trusted_negative_conflict_is_scored_from_va`（产品经 elev-N〔GT-positive 源〕观测 → 断言 conflict）拆成两条正确断言：plan-only→complete、经 GT-positive 源观测→**complete**（原 conflict 是 false-green，新 complete 符合 §8.6.1 item 1「GT-positive 源不得充当 absence 证人」）。**核实=纠正 false-green，非放松真安全锁** | **CLOSED** |
| **真 item-2**（r1 指出「item2 从未被真测」） | 新增 `test_b4b_c3_explicit_product_absence_in_non_gt_source_conflicts_with_positive`（phase_c.py:244）+ fixture `negative_only_elevation` 加 `elev-N-absence`（complete、**无 GT source ref** 的真 absence 证人）+ 显式 product ledger | 实证 elev-N-absence 在 reference 里 `positive_declared=False`/`applicable=[]`/`negative=(0.3,0.7)`（真 negative 证人无 GT positive）；**有** product_ledger→conflict、**无**→complete → 断言**承重非恒真**，且正确要求「显式产品 absence 声明」而非「缺失观测」= 真 §8.6.1 item 2 | **CLOSED** |
| **projection 接缝**（r1 观察未连） | 新增 `test_b4b_c1_projection_to_v3_scorer_ignores_product_frame_self_report`（phase_c.py:107）走 `project_typed_elevation_observation`→`OpeningObservation`→`score_opening_claims_v3` 端到端 | 端到端到 along=**complete**；翻转产品 frame 自报（mirrored/local_x_positive）后 rows `model_dump_json` **逐字节相同**（产品 frame 字段不被消费）→ C1 从单元层升到端到端。terra 简报「返工 r1」节如实登记 production normalizer/CLI 接线属 **Phase D 禁区**（披露修正属实） | **CLOSED** |
| **MINOR-1** walls==boundary | `score_policy` 按 `PlanSegment.exterior`（row.target/observation 的 topology 判别）分区 `wall_rows`/`boundary_rows` | 探针喂 wall(complete)+boundary(miss) → walls_complete=**pass**、boundary_complete=**fail**，denominator 分离，恒等消除 | **CLOSED** |
| **MINOR-2/3**（主控已裁决接受） | terra 只在 `score_policy` 加注释登记债务（window_elevation_geometry sill/head-only 因 row channel-fused 不可分；no_oversplit/negative_evidence_complete inert 待后 phase）——**核实=仅注释/登记，无擅自超范围** | 代码事实：两处 `rows=()` 与 sill/head-only 保持，附解释注释 | **CLOSED（登记）** |

### 回归与禁区复核
- **正-conflict 回归干净**：genuine positive-conflict（elev-bad 两产品 positive 互斥）仍 → `conflict`，守恒 `sum(slice.units)=1.0=eligible_units`。
- **禁区仍守**：`facade_applicability.py` 仍**一行未动**（`git diff --stat` 空）；仅 3 个 judge src 改动；新 v3 函数**零生产 import**（judge-only 保持）；无 Phase D 渗漏（无 SCORER_SCHEMA "7"→"8"、无 gray_hatch/not_rendered_reason）。
- **无安全锁丢失**：新增守恒 guard 均在；被修正的两条 false-green 测试是「解锁错误期望」非「移除真门」。

### 新 finding
**无**。返工精准闭合 r1 所有 findings，未引入新问题。

**最终裁决：APPROVE。**

签字：Opus 4.8 执行审子代理（r2 闭环），2026-07-17。
