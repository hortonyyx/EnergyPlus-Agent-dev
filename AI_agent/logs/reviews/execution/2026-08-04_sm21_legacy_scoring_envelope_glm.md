# 交付简报 · sm21 legacy 判卷信封缺陷（F-1a / F-1b）

- **日期**：2026-08-04 夜
- **施工席**：GLM-5.2
- **派工单**：`AI_agent/logs/reviews/request/2026-08-04_sm21_legacy_scoring_envelope_dispatch.md`
- **审阅席**：Claude 侧子代理（本席不自批）
- **开工前 HEAD**：`a5ba378`；开工前基线 **2158 passed / 10 xfailed / 0 failed**（派工单已载）

---

## 0. 一句话

判卷的 legacy（v2-GT）分支不认识今天读图产物的 `{"views": {...}}` 外层信封，整张卷子塌缩成一个假
`"views"` stem、**0 张楼层被判**，却仍报 `walls_complete/windows_placed/boundary_complete/no_oversplit`
全 pass。F-1a 在唯一一处脱壳、F-1b 兜底「空 scores 永不判 pass」，两条都修，锁四格实测 + 两次 neuter。

---

## 1. 逐条改了什么、为什么这样修

### F-1a · legacy 判卷路径消费当前读图信封（`scripts/tool_scripts/run_stage.py`）

**改法**：新增 `_unwrap_reading_views_envelope(output)`，在 `_legacy_score_attempt_output` 的
`if stage == "0_reading":` 分支首行调用一次：

```python
if identify_reading_contract(output).contract_id == "reading_views_v2":
    return output["views"]
return output
```

**为什么在这一处、只在这一处**：
- `_legacy_score_attempt_output` 是 legacy plan 评分（`_score_reading_attempt_output`）和立面评分
  （`score_reading_elevation_views`）的**唯一共同祖先**——两者都从它手里拿到同一个 `output`。在它
  首行脱壳一次，两个消费者同时拿到扁平 `{stem: view}`，满足派工单「⛔ 不许在多个消费点各写一份脱壳逻辑」。
- 复用 typed 路径自己的探测器 `identify_reading_contract`（派工单指定），不新发明判据。
- **扁平输入与非读图产物原样返回**：`identify_reading_contract` 对扁平/校正产物判 `unrecognized` ⇒ 原样透传。
- **校正分支完全不触碰**：脱壳守在 `stage == "0_reading"` 内，`1_correction` 走 `score_correction_geometry`，一字节不动。
- **渲染链无需另改**：`_grade_attempt_artifacts` 渲染消费的是已评分的 sidecar（`render_grade.render_grade(stage, sidecar, gt)`），
  不直接读原始 `output`；脱壳修好评分后，sidecar 自然带真分数、渲染自然对。已逐个查实同源消费者
  （`_score_reading_attempt_output` / `score_reading_elevation_views` / `_grade_attempt_artifacts` /
  `_render_all_attempt_grades`），仅 `_legacy_score_attempt_output` 一处需改。

### F-1b · 空 scores 永不判 pass（`src/agent/judge/score_policy.py::reading_score_criteria`）

**改法**：在算完 `missed_*` 之后，加机械判据 `no_scored_floors = not scores`；为真则四条 headline
（`walls_complete` / `windows_placed` / `boundary_complete` / `no_oversplit`）一律 `severe`，evidence 写
`no_data: no reading views were scored against gt floors; ...`；否则走原有逻辑（**逐字节不变**）。

**为什么这样切**（派工单 §2 的「⚠️ 必须区分两件事」）：
- 判据**只认 `scores` 是否为空这一个机械事实**，不发明启发式。
- 「GT 本来就没窗」= scores 非空、某楼层 `total_windows==0` ⇒ 落在 `else` 分支里原有的
  `if total_windows == 0 ... window_status = "pass"`，**保持不变**——这是合法 pass，不是本单目标。
- 「一张卷子都没批到」= `scores` 空 ⇒ 四条非 pass。
- status 用既有的 `severe`（同函数 `score_evidence_completeness` 已用），不新造 token；
  `suggested_status` 经核实仅本函数内部产生、无下游代码消费它（grep 全仓仅 `score_policy.py` 出现），
  故 `no_data` 进 evidence 字符串、status 沿用 `severe` 最稳。

---

## 2. 四格矩阵实测（真实量级 + 真实形状）

夹具 = **真 sm21 gt（`load_gt("sm21_anchor")`，schema_version=2）** + **真 07-07 已知满分读图产物**
（`case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/attempts/001/output.json`，
扁平形）。坏产物 = 深拷贝后把所有 stroke 几何坐标 `+1000m`（同样的段数/结构，仅整体偏到容差外）。

**good 产物规模（实测）**：2 楼层 · 平面墙 **9/9** · 平面窗 **7/7** · 立面窗 **15/15** —— 与派工单 §3.3
要求的真实量级逐项吻合（`test_good_product_is_real_scale` 钉死）。

| 形状＼产物 | good | bad（stroke +1000m） |
|---|---|---|
| **带信封** `{"views":…}` | scores=2 · 四条 pass · 立面 pass | scores=2 · 墙/窗/边界 severe · 立面 severe |
| **扁平** | scores=2 · 四条 pass · 立面 pass | scores=2 · 墙/窗/边界 severe · 立面 severe |

- 信封列 == 扁平列（两方向都相等）⇒ **脱壳对评分透明**，F-1a 在两个方向都成立。
- good→pass / bad→severe ⇒ scorer 仍有分辨力（不是「脱壳后两头都空判 severe」的假绿）。
- bad 的 `no_oversplit` 仍 pass 是**正确**行为：偏移坐标不会多画墙，oversplit 管的是「多画的墙」，
  不是「画错位的墙」；矩阵对 bad 只断言墙/窗/边界 severe。

第五格（空 scores）：
- `reading_score_criteria({})` ⇒ 四条全 `severe` + evidence 含 `no_data`（`test_empty_scores_makes_all_headline_criteria_non_pass`）。
- 端到端：`_legacy_score_attempt_output("0_reading", {"views": {}}, gt, ...)` ⇒ scores 空 + 四条非 pass
  （`test_empty_scores_guard_fires_end_to_end_through_legacy_seam`）。

F-1b 判别格（不许误杀合法 pass）：
- 非空 scores、该楼层零窗（「GT 无窗」替身）⇒ `windows_placed` 仍 `pass`（`test_empty_scores_guard_does_not_overfire_on_windowless_floor`）。

---

## 3. 两次 neuter 的原始输出（摘掉即红）

新测试文件：`tests/test_legacy_reading_envelope_scoring.py`（6 条锁）。

### Neuter F-1a（把 `_unwrap_reading_views_envelope` 改成 `return output`）

```
FAILED tests/test_legacy_reading_envelope_scoring.py::test_envelope_unwrap_helper_is_single_point_and_idempotent
FAILED tests/test_legacy_reading_envelope_scoring.py::test_four_cell_matrix_envelope_consumed_in_both_directions
2 failed, 4 passed
```
四格锁的失败点：`assert len(good_env_r["scores"]) == len(good_flat_r["scores"]) == 2` ⇒ `AssertionError: assert 0 == 2`
（信封塌缩 bug 复现：good+envelope 又判到 0 张）。
**恰好红 2 条 F-1a 锁，其余 4 条（含全部 F-1b 锁）全绿 ⇒ 零连带。**

### Neuter F-1b（把 `no_scored_floors = not scores` 改成 `= False`）

```
FAILED tests/test_legacy_reading_envelope_scoring.py::test_empty_scores_makes_all_headline_criteria_non_pass
FAILED tests/test_legacy_reading_envelope_scoring.py::test_empty_scores_guard_fires_end_to_end_through_legacy_seam
2 failed, 4 passed
```
端到端锁的失败点：`assert criteria[criterion] != "pass"` ⇒ `AssertionError: assert 'pass' != 'pass'`
（原「空 scores → 假 pass」bug 复现）。
**恰好红 2 条 F-1b 锁，其余 4 条（含四格 + helper + real_scale + overfire）全绿 ⇒ 零连带。**

> 两次 neuter 均「恰好红对应 2 条、零连带、零假锁」，neuter 后已逐字还原（grep `NEUTER` 无残留，6 锁复跑全绿）。
> 注：端到端空 scores 锁在 F-1a 被 neuter 时**仍绿**——因为无论信封脱不脱壳，空 scores 都触发 F-1b；
> 故它是 F-1b 锁、不是 F-1a 锁，归位正确（见 §4 诚实披露）。

---

## 4. 全仓三个数字

```
2164 passed, 10 xfailed, 0 failed   (python -m pytest -q -n auto, 366s)
```

基线 2158 / 10 / 0 ⇒ **+6 锁（6 条新测试）、零回归、xfail 不变**。只增不减满足。

---

## 5. 诚实披露（没做到的 / 绕过的 / 不确定的）

1. **夹具是读真产物、非自造**：四格用真 sm21 gt + 真 07-07 产物（**只读、未改**，符合派工单
   「不得改动 case_tests/ 下任何既有产物」）。代价：锁耦合该产物路径；已加 `pytestmark = skipif(not GOOD_ARTIFACT.exists())`
   兜底。该产物是已签字证据、稳定。
2. **今晚仓里两种形状并存**：触发本单的 `run_2026-08-04_e1_haiku_e2e/.../output.json` 顶层键 = `['views']`
   （信封，`identify_reading_contract → reading_views_v2`）；同夜的 `run_2026-08-04_smoke_downstream`
   仍是扁平（`1f_view…`，`unrecognized`）。**F-1a 对两者都对**（信封脱壳 / 扁平透传）——这是本修法相对
   「只认信封」的鲁棒性所在，也是 F-1b 兜底的意义（任何未来形状只要造成空 scores，F-1b 都拦）。
3. **bad 产物不触发 `no_oversplit` severe**：偏移坐标不增墙，oversplit 理应 pass（见 §2）。四格对 bad
   只断言墙/窗/边界 severe，**不是漏断，是该格正确行为**。
4. **F-1b status 用 `severe` 而非新造 `no_data` token**：`suggested_status` 无下游消费（已 grep 核实），
   `no_data` 进 evidence。若未来下游要按 status 细分「真空判」与「真画错」，需另立 token——本单不做。
5. **未自跑端到端 live e2e**：本单只修判卷层、只验判卷层。「谁写谁不批」——live 复跑归 orchestrator
   验收侧；本席以 A/B 复现 + 四格 + neuter 证明判卷层修对。
6. **未触碰**：typed v3 路径（sm24 线）、gt 文件、case_tests 既有产物、识图侧（读图质量另案）、任何容差。
   校正路径对脱壳 helper 是 no-op（`identify_reading_contract → unrecognized` + `stage=="0_reading"` 守卫，双保险）。
7. **提交范围**：仅 `run_stage.py` / `score_policy.py` / 新测试 / 本简报 4 个文件。`git status` 里其他未跟踪项
   （`run_2026-08-04_smoke_downstream/`、`sm25-L_anchor/`、派工单本身等）**属他席/他源，本席一律未动**
   （规避「收工 `git add -A` 扫走并行席位半成品」旧坑）。

## 6. 改动清单

- `scripts/tool_scripts/run_stage.py`：新增 `_unwrap_reading_views_envelope` + 在 `_legacy_score_attempt_output`
  reading 分支首行调用一次（F-1a）。
- `src/agent/judge/score_policy.py`：`reading_score_criteria` 加 `no_scored_floors` 守卫，空 scores ⇒ 四条
  severe + no_data evidence；非空分支逐字节不变（F-1b）。
- `tests/test_legacy_reading_envelope_scoring.py`：6 条锁（real-scale 守门 / helper 单点幂等 / 四格矩阵 /
  空 scores 直测 / 空 scores 端到端 / 不误杀合法 pass）。
