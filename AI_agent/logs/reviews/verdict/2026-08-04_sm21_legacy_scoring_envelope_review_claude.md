# 裁决书 · sm21 legacy 判卷信封缺陷（commit `4a11097`）

- **日期**：2026-08-04 夜
- **审阅席**：Claude 侧子代理（Opus 档），独立对抗审
- **被审对象**：`4a11097` "8.04_sm21_legacy_scoring_envelope_fix"（施工席 GLM-5.2）
- **派工单**：`AI_agent/logs/reviews/request/2026-08-04_sm21_legacy_scoring_envelope_dispatch.md`
- **只看三样**：原始需求 / `git show 4a11097` / **本席自己跑的测试与探针**。施工简报只用来核对「它声称了什么」，
  每个数字均由本席独立复算，**未采信任何自述**。
- **纪律遵守**：破坏性探针全部在 `/tmp/rev4a11097/`（三份 clone：`repo`=4a11097、`repo_base`=a5ba378、
  `repo_na`/`repo_nb`=两个 neuter 副本）；工作树**零改动、零 commit、零 push、零 `git add`/`stash`/`checkout`**，
  只跑了只读 git 命令与只读 pytest。

---

## 0. 结论

# APPROVE-WITH-CHANGES

**0 BLOCKER · 1 MAJOR · 2 MINOR · 3 NIT。**

代码本体是对的：F-1a 与 F-1b 两条修法各自成立、各自有真锁、两次 neuter 全仓零连带零假锁、边界一寸未越。
**但存在一条 MAJOR：这次修复没有让今晚那份产物真的重新被判——判卷 sidecar 的缓存键没有随判分语义一起变，
今晚 sm21 那份 0/9 的产物在装了这次修复之后重判，四条 headline 依然全 `pass`。**
（本席已在 `/tmp` 副本上活体复现。）

⇒ **建议：MAJOR-1 关闭之后再认为「sm21 端到端可以接着复验」**；MINOR/NIT 可并入同批或转跟进债。

---

## 1. 逐命题判定

### A. 缺陷真的被修好了吗

#### A1 — **成立**

用 `case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/attempts/001/output.json`
（已确认顶层键 = `['1f_view','2f_view','East_view','North_view','South_view','West_view']`，**扁平**）
分别以扁平与 `{"views": …}` 两种形状喂进 `_legacy_score_attempt_output("0_reading", …)`，
GT 用 `load_gt("sm21_anchor")`（本席独立核实 `schema_version=2`、`LegacyGroundTruthV2` ⇒ 确属 legacy 路径）：

| 代码版本 | 形状 | 批到几张 | 平面墙 | 平面窗 | 立面窗 | 四条 headline |
|---|---|---|---|---|---|---|
| **4a11097** | 扁平 | 2 | **9/9** | **7/7** | **15/15** | 全 pass |
| **4a11097** | 信封 | 2 | **9/9** | **7/7** | **15/15** | 全 pass |
| a5ba378（修前） | 扁平 | 2 | 9/9 | 7/7 | 15/15 | 全 pass |
| a5ba378（修前） | 信封 | **0** | 0/0 | 0/0 | 0/15 | **全 pass ⛔** |

两种形状在修复后逐项相等 ⇒ 脱壳对评分透明。修前信封列即派工单描述的 0/0-却-pass，**缺陷与修复均独立复现**。

#### A2 — **成立**

今晚那份坏产物 `run_2026-08-04_e1_haiku_e2e/0_reading/attempts/001/output.json`（顶层键 `['views']`，
`identify_reading_contract → reading_views_v2`）原样喂进判卷：

- **4a11097**：批到 2 张、平面墙 **0/9**、平面窗 **0/7**、立面窗 **0/15**；
  `walls_complete=severe · windows_placed=severe · no_oversplit=severe · elevation_windows_placed=severe`。
- a5ba378：批到 **0** 张、四条 headline **全 pass**。

⇒ 非 pass 成立，真实分与派工单预判（0/9 墙 · 0/7 窗）逐项吻合。

**一处与派工单预期不同、经核属正确**：`boundary_complete` 判 **pass**。本席逐楼层读了 `FloorScore.boundary`，
两层的 S/N/W/E 四边全部命中——**这份产物外轮廓确实画对了，错的是内墙与窗**，故 boundary pass 是真结论不是漏判。

#### A3 — **成立**

空 scores ⇒ 四条 headline 全部非 pass，且三条入口都验过：

| 入口 | 4a11097 | a5ba378 |
|---|---|---|
| `reading_score_criteria({})` 直调 | 四条全 `severe` | 四条全 `pass` |
| `_legacy_score_attempt_output("0_reading", {"views": {}}, gt)`（被识别的空信封） | 四条全 `severe` | 四条全 `pass` |
| `_legacy_score_attempt_output("0_reading", {}, gt)`（扁平空 dict） | 四条全 `severe` | 四条全 `pass` |

另核：evidence 串含 `no_data`；空 scores 下 `_grade_attempt_artifacts` 端到端**能正常渲染 grade.png 不崩**
（拿今晚 attempt 002 那份 `{}` 产物在 `/tmp` 实跑，28 760 字节 PNG 正常落盘）。

---

### B. 锁是不是真锁

#### B1 — **成立（且比施工方声称的更严：本席跑的是全仓，不是单文件）**

**基线口径先说清**：`/tmp` clone 里有 6 条与本提交无关的既有红（`test_reading_score::test_sm21_phase1_...`
等依赖 **未纳入版本控制** 的 `case_tests/e2e_tests/smalloffice_21_pre/` 等路径，clone 里没有；另有需要
网络/EnergyPlus 的两条）。故本席**先跑了一遍未 neuter 的 clone 全仓当对照**，再逐个 neuter 对差。

| 运行 | 结果 | 相对 clone 基线的差 |
|---|---|---|
| **clone 基线**（`repo` = 4a11097 原样） | **6 failed / 2150 passed / 8 skipped / 10 xfailed**（288.96s） | — |
| **neuter F-1a**（把 `run_stage.py:1314` 的 `output = _unwrap_reading_views_envelope(output)` 摘掉） | **7 failed / 2149 passed**（290.86s） | **恰好 +1 条** |
| **neuter F-1b**（`score_policy.py` 整份回退到 a5ba378 = 守卫整个摘掉） | **8 failed / 2148 passed**（289.18s） | **恰好 +2 条** |

**neuter F-1a 新增的红（1 条）**：

```
FAILED tests/test_legacy_reading_envelope_scoring.py::test_four_cell_matrix_envelope_consumed_in_both_directions
```

失败断言（本席复跑取原文）：`assert len(good_env_r["scores"]) == len(good_flat_r["scores"]) == 2`
⇒ `AssertionError: assert 0 == 2`（信封列重新塌回 0 张）。

**neuter F-1b 新增的红（2 条）**：

```
FAILED tests/test_legacy_reading_envelope_scoring.py::test_empty_scores_makes_all_headline_criteria_non_pass
FAILED tests/test_legacy_reading_envelope_scoring.py::test_empty_scores_guard_fires_end_to_end_through_legacy_seam
```

失败断言：前者 `assert criteria[criterion]["suggested_status"] != "pass"`，
后者 `assert criteria[criterion] != "pass"` ⇒ 均得 `'pass' != 'pass'` 的 AssertionError（假 pass 重现）。

**两次 neuter 的其余红逐条与 clone 基线同名同数 ⇒ 零连带。** 两次 neuter 相互不串（F-1a 的 neuter 没碰到任何
F-1b 锁，反之亦然）⇒ 归位正确、零假锁。

**⚠️ 与施工简报的一处口径差（本席认为是简报口径偏宽，不是造假）**：简报称 neuter F-1a「恰好红 2 条」。
那是因为它 neuter 的是**helper 函数体**（改成 `return output`），于是连 helper 的单元测试
`test_envelope_unwrap_helper_is_single_point_and_idempotent` 一起红。**本席按派工单口径 neuter 的是「调用」**，
结果只红 1 条——因为那条 helper 单测**只锁 helper 自己的语义、不锁它有没有被接上生产路径**。
真正锁「接线」的只有四格矩阵那一条。详见 NIT-2。

#### B2 — **成立（四格确有分辨力；无退化夹具；但有一格是被 F-1b 兜住的，靠另一条断言补住了）**

**载荷真实性（本席独立复算，未采信简报）**：
- GT = 真 `sm21_anchor` v2 答案（`load_gt`，非手搓）；
- good 产物 = 真 07-07 产物**只读加载**（`GOOD_ARTIFACT.read_text`，全文件无任何写操作）；
- 实测规模 = **2 层 · 平面墙 9/9 · 平面窗 7/7 · 立面窗 15/15**，与派工单 §3.3 要求逐项吻合；
- `test_good_product_is_real_scale` 把这四个数字钉死 ⇒ **有防退化守门**（若有人把夹具换小，这条先红）；
- bad 产物 = 深拷贝后把 stroke 内所有 `[x, y]` 数值对整体 +1000 m ⇒ **段数、结构、笔画数全部不变，只是位置全错**，
  属真实形状的真实误读，**不是 2×2 退化 fixture**。

**四格 + 第五格的分辨力实测**（本席分别在「原样 / F-1a neuter / F-1b neuter」三种代码下算同五个 payload）：

| 格 | 原样 | F-1a neuter | F-1b neuter | 能抓 F-1a？ | 能抓 F-1b？ |
|---|---|---|---|---|---|
| good × 扁平 | 2 层 · 全 pass | 2 层 · 全 pass | 2 层 · 全 pass | 否（对照格） | 否（对照格） |
| **good × 信封** | 2 层 · 全 pass | **0 层 · 全 severe** | 2 层 · 全 pass | **是** | 否 |
| bad × 扁平 | 2 层 · 墙/窗/边界 severe | 同 | 同 | 否（对照格） | 否 |
| **bad × 信封** | **2 层** · 墙/窗/边界 severe | **0 层** · 四条 severe | 2 层 · 同原样 | **是（靠层数断言）** | 否 |
| **空 scores** | 四条 severe | 四条 severe | **四条 pass** | 否 | **是** |

**结论**：没有任何一格是「构造出来必然成立」的空格——两条修法各自都有格能抓。
**但必须点明一处结构性交叉**：`bad × 信封 → severe` 这个**判据本身**在 F-1a 被摘掉时**仍然成立**
（因为脱壳失败 ⇒ 空 scores ⇒ F-1b 让它照样 severe）。也就是说，**如果测试只断言了 severity，这一格是零分辨力的**。
测试**补对了**：它同时断言 `len(bad_env_r["scores"]) == len(bad_flat_r["scores"]) == 2`
以及 `bad_env_c[criterion] == bad_flat_c[criterion]`（F-1a neuter 下 `no_oversplit` 一边 pass 一边 severe，也会红）。
⇒ **两道独立断言各自都能抓，该格实际有分辨力。** 这正是 08-04「neuter 变红只证明实现被调用」教训的正确应用。

#### B3 — **成立（达到派工单最低线，但没有再往上一层）**

- 六条锁里有三条走 `_legacy_score_attempt_output` 的真实入口（`test_good_product_is_real_scale` /
  `test_four_cell_matrix_...` / `test_empty_scores_guard_fires_end_to_end_through_legacy_seam`），
  用真 GT + 真产物，**不是直调内部私有函数**。派工单 B3 的要求满足。
- 生产链是 `_grade_attempt_artifacts → _score_attempt_output → score_attempt_service(legacy_evaluator=…)
  → _legacy_score_attempt_output`；`score_attempt_service` 对 legacy 是纯透传（本席读码确认），
  ⇒ 锁的入口点与生产只差一层无逻辑的 dispatch。
- **但没有任何一条锁走到 `_grade_attempt_artifacts` 这一层** ——而 **MAJOR-1 恰恰就藏在这一层**（见 §2）。
  这不是巧合：**锁停在哪一层，缺陷就能躲在再上一层。**

---

### C. 边界有没有越

#### C1 — **成立（typed v3 路径一字节未受影响）**

验证方式（三条独立证据）：

1. **源码级**：`git rev-parse a5ba378:<f>` 与 `4a11097:<f>` 逐个对比 blob hash，以下九个 typed/判卷核心文件
   **全部 IDENTICAL**：`score_service.py` · `reading_typed_adapter.py` · `score_schema.py` ·
   `opening_claim_score.py` · `gt.py` · `gt_schema.py` · `elevation_score.py` · `reading_score.py` ·
   `correction_score.py`。`git diff --name-only a5ba378 4a11097` 全仓只有 4 个文件（见 C3）。
2. **可达性**：`reading_score_criteria` 全仓**只有一个生产调用者** = `run_stage.py:1361`（legacy 分支），
   typed 路径用的是 `score_policy.py` 里另一套 `c2_v3_score_policy`/`V3PolicyVerdict`（本次 diff 未触）。
   `run_stage.py` 的两个 hunk（`@@ -1270` / `@@ -1285`）都落在 legacy 区。
   `_render_stage_grade_artifacts:1617` 对 `GroundTruthV3` 直接 `return _render_all_typed_attempt_grades(...)`
   ⇒ sm24 根本进不到 legacy 函数。本席独立核实 `load_gt_document("sm24_anchor")` 返回 `GroundTruthV3`、
   `load_gt_document("sm21_anchor")` 返回 `LegacyGroundTruthV2`。
3. **实测**：工作树全仓 **2164 passed / 10 xfailed / 0 failed**，含全部 sm24/typed/c2_b4b 系列，零红零回归。

#### C2 — **成立**

`git show --name-only 4a11097` 的完整清单里**没有任何 `case_tests/` 路径、没有 gt 文件、没有 `src/agent/reading/`
或 `src/validator/checks/reading.py`**。新测试对 07-07 产物只 `read_text`，无写路径。
本席另扫了 `case_tests/` 下全部 **28 份** reading attempt 产物，形状分布见附录 A——
**所有 sm21（legacy GT）历史产物都是扁平的**，⇒ 本修复对既有 sm21 run 是 no-op，**无追溯性回归风险**。

#### C3 — **成立（没有混入他席半成品）**

`4a11097` 的文件清单恰好 4 个：

```
AI_agent/logs/reviews/execution/2026-08-04_sm21_legacy_scoring_envelope_glm.md
scripts/tool_scripts/run_stage.py
src/agent/judge/score_policy.py
tests/test_legacy_reading_envelope_scoring.py
```

提交后 `git status --porcelain` 显示 orchestrator 的未跟踪产物**仍然全部在外**：
`case_tests/e2e_tests/sm25-L_anchor/` · `case_tests/test_baseline/gt_sources/sm25-L_anchor/` ·
`case_tests/e2e_tests/sm21_anchor/run_2026-08-04_e1_haiku_e2e/` · `.../run_2026-08-04_smoke_downstream/` ·
派工单本身。⇒ **08-04「收工 `git add -A` 扫走并行席位半成品」那个坑本轮没有重犯。**

---

## 2. Findings

### 🟠 MAJOR-1 · 判分语义变了，但判卷 sidecar 的缓存键没变 ⇒ 今晚那份产物重判仍报四条 pass

**在哪**
- `scripts/tool_scripts/run_stage.py:79` — `SCORER_SCHEMA = "8"`，本提交**未动**（`git show 4a11097 | grep -c SCORER_SCHEMA` = 0）。
- `scripts/tool_scripts/run_stage.py:1441-1450` — `_load_valid_score_sidecar` 的缓存键 =
  `(stage, attempt, output_hash, source, scorer_schema, tolerances)`。
- `scripts/tool_scripts/run_stage.py:1514-1526` — `_grade_attempt_artifacts` 里
  `sidecar = _load_valid_score_sidecar(...)`；**命中即 `render_needed=False`，`_score_attempt_output` 整个不调用**。

**为什么是问题**

本次提交同时改了两处判分语义（F-1a 改「批到几张」、F-1b 改「空 scores 判什么」），
**但缓存键里没有任何一个分量会因此变化**：产物没改 ⇒ `output_hash` 不变；容差没改 ⇒ `tolerances` 不变；
`SCORER_SCHEMA` 没 bump ⇒ 仍是 `"8"`。⇒ **任何在旧判卷器下已经落过 sidecar 的 attempt，装了这次修复之后
再判还是拿旧结论，判分器一次都不会被调用。** 全仓也没有任何一处 invalidate 逻辑
（`run_stage.py` 里的三处 `unlink` 全是原子写失败回滚，不是失效）。

**会怎么崩（本席活体复现，非推理）**

盘上现成的证据：`case_tests/e2e_tests/sm21_anchor/run_2026-08-04_e1_haiku_e2e/0_reading/attempts/001/score_vs_gt.json`
此刻的内容是 `"scores": {}` + `walls_complete/windows_placed/boundary_complete/no_oversplit` **四条全 pass**
+ `"scorer_schema": "8"` —— 正是旧判卷器写下的那份假 pass。

把整个 run 目录拷进 `/tmp`（不动工作树），用**修好之后**的代码调 `_grade_attempt_artifacts`：

```
[A] 保留旧 sidecar 重判：walls_complete=pass  windows_placed=pass  boundary_complete=pass  no_oversplit=pass
[B] 删掉旧 sidecar 重判：walls_complete=severe windows_placed=severe boundary_complete=pass no_oversplit=severe
```

**⇒ 派工单第 0 节那句「一张没批 ≡ 全对」，在这次修复之后、在触发它的那份产物上，原样复现。**
而且 `grade.png` 同理不会重渲（`render_needed=False` 且文件已存在）⇒ **用户看图这条独立通道也一起停在旧图上**。

这条正好落在派工单 F-1a 点名要求「逐个查实」的 `_grade_attempt_artifacts` 里。施工简报 §1 查到了它
（结论「渲染消费的是已评分 sidecar，无需另改」），**但只看了「渲染读谁」，没看「sidecar 本身会不会被复用」**。

**这是本项目的老形状**：`SCORER_SCHEMA` 这个常量正是 `43b79e3`（7.03_BoundaryGrading）为了同一件事引入的——
当时的 commit 原文写着「加 `SCORER_SCHEMA="2"` 进 sidecar 身份匹配（**老 sidecar 无 boundary → 自动重算补齐**）」。
**机制是现成的、就为这种场合设的，这次没用。**

**修法（供 orchestrator 裁定，本席不施工）**
- 把 `run_stage.SCORER_SCHEMA` 从 `"8"` 提到 `"9"`。**这个改动是外科手术式的**：该常量在 `run_stage.py` 里
  只有两处用途（`:1446` 缓存比对、`:1532` 写 sidecar 标签），**与 typed 侧的 `score_schema.SCORER_SCHEMA`
  是两个独立常量**，不牵动 typed 身份；既有测试用 `rs.SCORER_SCHEMA` 而非字面量断言（`test_judge_batch_b.py`），
  拒旧 schema 的锁（`test_c2_b4b_contract.py:82` / `test_judge_batch_b.py:484` / `test_render_grade.py:77`）本就在。
- **并补一条锁**：「旧 sidecar 在判分语义变更后必须被拒绝重算」目前**零锁**——所以同族缺陷下次还会来。
  建议的锁形状：造一份 `scorer_schema` 为旧值、其余字段全对的 sidecar，断言 `_grade_attempt_artifacts` 重算而非复用。

---

### 🟡 MINOR-1 · 模块级 `skipif` 让六条锁在夹具消失时**静默失效**（fail-open）

**在哪**：`tests/test_legacy_reading_envelope_scoring.py:51-54`

```python
pytestmark = pytest.mark.skipif(
    not GOOD_ARTIFACT.exists(),
    reason="real-scale 07-07 sm21 reading artifact is required for this lock",
)
```

**为什么是问题**：该产物**已纳入版本控制**（本席 `git ls-files --error-unmatch` 核实 = TRACKED），
所以在仓库里它必然存在——这个 `skipif` **换不来任何鲁棒性，只换来 fail-open**。
它是模块级的，覆盖**全部六条锁**，包括唯一那条锁 F-1a 接线的四格矩阵。

**会怎么崩**：将来任何一次 run 目录整理/搬迁把 `run_2026-07-07_haiku_cv_retest` 挪走，
**六条锁全部静默 skip，全仓照样绿，F-1a 与 F-1b 双双回到无锁状态、且没有任何人会注意到。**
本项目已经为同一形状登记过债（07-26：「`test_gt_overlay` 的 sm21 `skipif` 应改 assert，
主控与 sol 独立认定同一『最脆』」），也已明确过纪律「fail-closed 要硬红、不要静默 skip」。

**修法**：改成 `assert GOOD_ARTIFACT.exists()`（或 session fixture 里 `pytest.fail`），删掉 `skipif`。

---

### 🟡 MINOR-2 · 交付声称「校正路径一字节不动」与实际不符；且被改到的那个方向**没有锁**

**在哪**
- `src/agent/judge/score_policy.py:286-289`（F-1b 守卫）
- `scripts/tool_scripts/run_stage.py:1361` —— `reading_score_criteria(...)` 是 `_legacy_score_attempt_output`
  **`0_reading` 与 `1_correction` 两个分支共用**的返回构造，不在 `if stage == "0_reading"` 里面。
- `src/agent/judge/correction_score.py:350-359` —— `score_correction_geometry` 在 `floor_map` 全部落空时
  逐个 `continue`，**确实可以返回空 `scores`**。

**为什么是问题**：commit message ③ 写「typed v3 线、gt、case_tests 既有产物、识图侧、容差均未触碰」，
简报 §1 写「**校正分支完全不触碰** …… 一字节不动」、§5.6 重申。**F-1a 确实没碰校正**（守在 `stage=="0_reading"` 内），
**但 F-1b 碰了**：本席跨版本实测 `reading_score_criteria({})` 在 a5ba378 返回四条 `pass`、在 4a11097 返回四条 `severe`
—— legacy 校正判卷走的是同一个函数。

**本席对新行为的判断：语义是对的，不该回退。**「一份 correction 产物零楼层匹配上 gt，却报 pass」同样是假绿；
且派工单 F-1b 点名的入口就是 `reading_score_criteria` 这个函数本身，属于射程内。
**问题在声称，不在代码**——本项目对「诚实交接」有明确标准，交付说明应如实写成
「F-1b 同时收紧了 legacy 校正分支（同一函数），此为有意且正确的副作用」。

**会怎么崩**：六条新锁**全部是 reading 侧**，校正方向零锁 ⇒ 将来若有人把守卫改成
`no_scored_floors = not scores and stage == "0_reading"` 之类（看起来更"窄"更"安全"），
校正侧的假 pass 会静默回来且全仓零红。

---

### ⚪ NIT-1 · `no_oversplit` 的 evidence f-string 引用了只在 `else` 分支绑定的 `oversplit_count`

`src/agent/judge/score_policy.py:307`（`oversplit_count = extra_walls` 在 `else` 里）对 `:357-359`
（`f"extra_vwalls+extra_hwalls={oversplit_count}; ..."`）。今天安全**只因为条件表达式短路**
（`no_data_evidence if no_scored_floors else (f"...")`）。将来任何人把 evidence 改成无条件拼装，
空 scores 就会在判卷器内部抛 `NameError`。一行加固：把 `oversplit_count = extra_walls` 提到分支之前。

### ⚪ NIT-2 · helper 单测**不是接线锁**，简报把它算成了 F-1a 的锁

`test_envelope_unwrap_helper_is_single_point_and_idempotent` 只调 `_unwrap_reading_views_envelope` 本身，
**不经过 `_legacy_score_attempt_output`**。本席按派工单口径 neuter「调用」而非「函数体」，实测**它是绿的**，
唯一变红的是四格矩阵。⇒ F-1a 的真实接线锁**只有 1 条**（简报称 2 条，那是 neuter 函数体的结果）。
不是假锁（它确实锁住了 helper 语义），但覆盖面被口径放大了。**接线只有单点保护，删调用最容易，最好再补一条。**

### ⚪ NIT-3 · `identify_reading_contract` 对「扁平产物里恰好有一个叫 `views` 的图名」会误判（继承风险，今天不可达）

`src/agent/judge/reading_typed_adapter.py:60-71`：只要顶层有 `views` 且其值是「键全为非空字符串」的 dict，
就判 `reading_views_v2`。若某个 case 的图名恰好是 `views`（产物形如 `{"views": {...}, "1f_view": {...}}`），
脱壳会**丢掉真正的图、把那一张图的字段名当成 stem**。本席扫了 `case_tests/` 下全部 28 份 reading 产物，
**混合形状 0 处** ⇒ 今天不可达；且该探测器是既有的、typed 路径共用，**不是本提交引入的**。仅登记。

---

## 3. 本席跑的测试（三个数字）

### 权威门（工作树 @ `4a11097`）

```
python -m pytest -q -n auto
2164 passed, 10 xfailed, 209 warnings in 399.03s (0:06:39)
```

⇒ **2164 passed / 10 xfailed / 0 failed**，**0 skipped**。
基线 `a5ba378` = 2158 / 10 / 0 ⇒ **净增 6（= 6 条新锁）、零回归、xfail 不变**。
**与施工简报声称的数字逐字相同，本席独立复算成立。**

### 对照与 neuter（`/tmp` clone，破坏性）

| 运行 | passed | failed | skipped | xfailed |
|---|---|---|---|---|
| clone 基线（4a11097 原样） | 2150 | 6 | 8 | 10 |
| neuter F-1a（摘调用） | 2149 | **7** | 8 | 10 |
| neuter F-1b（整份守卫回退） | 2148 | **8** | 8 | 10 |

⚠️ **clone 那 6 条既有红与本提交无关**，是 clone 缺少未纳入版本控制的输入所致
（例：`test_sm21_phase1_reading_score_regression_floor` 读 `case_tests/e2e_tests/smalloffice_21_pre/phase1`，
该目录不在 git 里 ⇒ clone 上 `scores == {}`；另有需网络的 `test_zone_agent` 与需 EP 基线的 `test_sm21_anchor_ep_clean`）。
**这本身是既有的「绿只绿在这台机器上」问题**（07-26 已就同族问题立过项），与本次评审无关，仅登记为背景信息——
但它也说明：**neuter 对差必须有同环境对照，否则会把环境噪音报成连带。**

---

## 附录 A · `case_tests/` 下 28 份 reading 产物的形状分布（本席独立扫描）

| 形状 | 数量 | 说明 |
|---|---|---|
| 扁平非空（`unrecognized`） | 17 | 全部 sm21 历史 run（06-20 → 07-08）+ sm24 两份早期 run + 今晚 `smoke_downstream` |
| 空 dict `{}`（也判 `unrecognized`） | 3 | sm21 `e1_haiku_e2e/002` + sm24 `run_2026-07-27_haiku_e2e/001` 与 `/002` |
| 信封（`reading_views_v2`） | 8 | 今晚 sm21 `e1_haiku_e2e/001` + sm24 七份（07-27/003、08-01 ×5、08-02 ×1） |
| **混合（同时有 `views` 与其他 stem）** | **0** | ⇒ NIT-3 今天不可达 |
| 合计 | 28 | |

**关键含义**：所有走 legacy 判卷的 sm21 **历史**产物都是扁平的 ⇒ 本修复**不会改写任何既有 sm21 历史成绩**；
8 份信封产物里除今晚 sm21 那一份外全是 sm24（v3 GT ⇒ typed 路径）⇒ **不经过本次改动的代码**。

---

## 附录 B · 本席核过但**未发现问题**的项（免得下一轮重查）

1. **归一化确实只有一处**：`_unwrap_reading_views_envelope` 全仓生产调用点 = 1（`run_stage.py:1314`），
   无第二把尺子。
2. **考试范围（exam scope）不影响 legacy**：`reading_exam_scope` 的解析与消费全在
   `_grade_typed_attempt_artifacts`（`run_stage.py:1645-1759`）与 typed scorer 内，legacy 路径零引用
   ⇒ 不存在「减卷把平面图全排除 ⇒ 空 scores ⇒ F-1b 误红」这条路。
3. **`score_criteria` / `suggested_status` 是 advisory-by-design**：全仓无自动 gating 消费者，
   `run_stage.py:1843` 明写「machine-readable gt reconciliation evidence only」，`StageVerdict(extra="forbid")`
   拒收 `suggested_status`。⇒ F-1b 修的是判卷者读到的证据，不是自动闸门——**这是既有架构，不是本提交的缺陷**，
   但与 MAJOR-1 叠加后果要一起看：假 pass 既不会被自动拦，重判又拿不到新结论。
4. **空 scores 的渲染链不崩**：`_grade_attempt_artifacts` 在 `scores == {}` 时正常出 28 760 字节 grade.png。
5. **`{"views": {}}` 被正确识别**：`identify_reading_contract({"views": {}})` = `reading_views_v2`
   （`any()` 对空集为 False），脱壳得 `{}` ⇒ 落 F-1b。
6. **夹具无写副作用**：新测试对 07-07 产物只读；`_bad_product` 全程 `copy.deepcopy` 后再改。

---

## 4. 给 orchestrator 的一句话

**代码修对了，锁也是真的（本席全仓 neuter 逐条验过、零连带零假锁）；但这次修复没有让今晚那份卷子真的被重判。**
在 `SCORER_SCHEMA` 提上去（或旧 sidecar 被清掉）之前，**拿今晚的 sm21 run 去复验判卷，会原样看到那四条假 pass。**
