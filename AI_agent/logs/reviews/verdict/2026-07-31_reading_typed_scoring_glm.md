# 裁决书 · 识图类型化判卷批（验证性对抗审）

> 审阅方 = 接管 GLM-5.2 席位的对抗审阅者（Claude 侧，Opus 5 子代理）· 2026-07-31
> 被审对象 = sol 的施工 = `f98d248..HEAD` 中全部 `7.31_ReadingTypedScoring*` 提交（共 21 个）
> 审阅单 = [`../request/2026-07-31_reading_typed_scoring_glm_review.md`](../request/2026-07-31_reading_typed_scoring_glm_review.md)
>
> **纪律自证**：全程只审不修。主工作树**零生产码改动**（结尾附 `git status`）。
> 所有破坏测试在 `/tmp` 克隆里做、真跑、报实际变红的测试名。
> `case_tests/test_baseline/gt/**` **一字未写**（结尾附 hash 对账）。

---

## 0. 结论

**APPROVE-WITH-CHANGES**

| 分级 | 数量 | 条目 |
|---|---|---|
| BLOCKER | **0** | — |
| MAJOR | **1** | M-1（P10②：新增识图集成测试注入了一条从已签字答案取来的产品坐标）|
| MINOR | **1** | m-1（P10①/C8：超出细稿 §13.3 授权范围改了两处既有断言、未单列记录，且执行日志的措辞与实况不符）|
| NIT | **3** | n-1 / n-2 / n-3 |

**四条承重命题 P1–P4 全部成立**，且四条都由我自己在真实产物上跑出的证据支撑（不采信施工方任何打印值）。
故不触发「任一不成立即 REWORK」。

| 命题 | 判定 |
|---|---|
| P1 分母是受信输入的纯函数（U-13） | **成立** |
| P2 帧冲突 = NA + 证人 + 分母保留（U-10） | **成立** |
| P3 rect 墙逐笔画剔除 + 计数（U-05） | **成立** |
| P4 correction 对外可见判分逐字节未变（U-03/D-1） | **成立** |
| P5 判卷器对识图永不抛异常（C1/R-4） | **成立** |
| P6 F8 恒真陷阱已避开 | **成立** |
| P7 零观测 ≠ 不适用（C2） | **成立** |
| P8 gt 铁律未破（不变量 #4） | **成立** |
| P9 既有行为未被破坏 | **成立** |
| P10 新识图 E2E 没有拿答案当被测物 | **不成立**（②违规；①见 m-1）|
| P11 全仓数字与基线差额逐条可解释 | **成立** |
| P12 跨批次零碰撞 | **成立** |

---

## 1. 审阅环境与共用探针

三份 `/tmp` 克隆（均 `git clone --no-hardlinks`，与主树物理隔离）：

```bash
SP=/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/1fe41113-.../scratchpad
git clone -q --no-hardlinks /workspaces/EnergyPlus-Agent-dev $SP/clone_head      # 7a067b4
git clone -q --no-hardlinks /workspaces/EnergyPlus-Agent-dev $SP/clone_neuter    # 7a067b4，破坏用
git clone -q --no-hardlinks /workspaces/EnergyPlus-Agent-dev $SP/clone_base
(cd $SP/clone_base && git checkout -q f98d248)                                   # 改造前基线
```

自写探针 `probe.py`：以**真实已接受识图产物**为唯一产品字节来源，走**生产入口**
`run_stage._grade_typed_attempt_artifacts("0_reading", …)`，落 sidecar 后自行解析。
产品侧 mutation 全部从产品自身派生，**不从 gt 反解任何坐标**。

```
产品 = case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json
答案 = case_tests/test_baseline/gt/sm24_anchor/gt.json（只读）
侧车 = <run>/_run/{view_manifest.json,judge_score_bindings.json}
```

**基准运行（未改动的真实产物）**：

```
payload.kind                 = c2_scored
schema_version               = 9
denominator_basis_sha256     = 641676383776c099ef3b081009b2ac4b4049726df0bd45e1955aba91e40417d7
denominator_sha256           = de9d54e3f2e335035df3879b0557d2a0deda713d87f2565f345ce7ac4be2d407
denominator 原子数            = 108      denominator 总单位 = 205.85999999999999
window_elevation_geometry.denominator_units = 44.0
unmeasurable_observations    = 0
visibility_counts            = {..., elevation_local_x_sense_disagreements: 2,
                                project_convention_vertical_datums: 4, scorer_internal_failures: 0}
```

⇒ **07-30 那条「一进 J0 必崩」的路径已经真出分了**（这条本身就是本批的活体验收 §6.4）。

---

## 2. 承重命题

### P1 · U-13「分母是受信输入的纯函数」 — **成立**

#### 1.1 锁的覆盖面（U-13 更正的要求）

`tests/test_reading_typed_scoring_slice0.py::test_product_geometry_bytes_cannot_change_denominator`
（`:142-206`）喂的两份产品字节流：

- 几何侧：`for stroke in view["strokes"]: stroke["geometry"] = {}`（全部笔画畸形）；
- **帧侧（U-13 更正明确要求的那两个字段）**：对每个 `image_kind == "elevation"` 的视图
  把 `facade["local_x_positive"]` 与 `facade["mirrored"]` **双双取反**（`:159-174`）。

并断言 `visibility_counts["elevation_local_x_sense_disagreements"]` 正常 = **2**、畸形 = **4**
⇒ 取反确实把两张原本一致的立面也推进了帧冲突通道，**不是空转**。
覆盖面符合更正后的要求（原稿把这两个字段固定住的问题已修）。

同时该测试用 `inspect.signature` 钉死构造器签名：

```python
assert tuple(inspect.signature(derive_reading_denominator_v1).parameters) == (
    "gt", "base_manifest", "bindings", "trusted_capability_dispositions")
```

我复核了 `src/agent/judge/reading_typed_adapter.py:1376-1540`：函数**没有任何产品参数**，
第四参数经 `ReadingFilteredComponentBasisV1` 校验，其 `cause_class` 是
`Literal["trusted_input"]`（`score_schema.py:882`）⇒ **产品侧成因在类型层就无法表达**。
且 `ReadingComponentApplicabilityV1._status_contract`（`score_schema.py:673-694`）强制
`cause_class == "trusted_input" ⟺ denominator_disposition == "filter"`，其余 NA 一律 `retain_as_miss`。

#### 1.2 生产级独立证据（不经施工方测试）

```bash
cd $SP/clone_neuter && python $SP/probe.py all_geometry_malformed   # 全部笔画 geometry={}
cd $SP/clone_neuter && python $SP/probe.py flip_all_facades         # 四张立面帧声明全取反
cd $SP/clone_neuter && python $SP/probe.py views_empty              # {"views": {}}
cd $SP/clone_neuter && python $SP/probe.py views_garbage_view       # 视图内容乱码
```

| 产品字节 | denominator_sha256 | 原子数 | unmeasurable | 帧冲突计数 |
|---|---|---|---|---|
| 真实原样 | `de9d54e3…` | 108 | 0 | 2 |
| 全笔画畸形 | `de9d54e3…` | 108 | **21** | 2 |
| 四立面帧全取反 | `de9d54e3…` | 108 | 0 | **4** |
| `{"views": {}}`（一张图都不给） | `de9d54e3…` | 108 | 0 | 0 |
| 视图内容乱码 | `de9d54e3…` | 108 | 0 | 0 |

**产品把自己删到一张视图都没有，分母仍是 108 个原子、20 条 segment 行全 `miss`。**
这是「产品缩不动自己分母」最强的一条正面证据。

#### 1.3 破坏测试（两个变体都真跑）

**N1a — 把产品触发的帧 NA 洗成受信过滤**（在 `_elevation_result` 帧冲突分支补发
`cause_class="trusted_input"` 的 exclusion）：

```
FAILED tests/test_reading_typed_scoring_slice0.py::test_product_geometry_bytes_cannot_change_denominator
FAILED tests/test_reading_typed_scoring_slice0.py::test_sm24_local_x_disagreement_is_input_scoped_na_with_raw_witness
FAILED tests/test_reading_typed_adapter.py::test_multiple_plan_inputs_for_one_floor_are_trusted_filtered
3 failed, 117 passed
```

**N1b — 字面恢复「`trusted_frame` 也有过滤权」**（把 `ReadingFilteredComponentBasisV1.cause_class`
的 Literal 放宽到含 `"trusted_frame"`，并在帧冲突分支发 `trusted_frame` exclusion）：

```
FAILED tests/test_reading_typed_scoring_slice1.py::test_denominator_constructor_accepts_only_canonical_trusted_exclusions
FAILED tests/test_reading_typed_scoring_slice0.py::test_product_geometry_bytes_cannot_change_denominator
FAILED tests/test_reading_typed_scoring_slice0.py::test_sm24_local_x_disagreement_is_input_scoped_na_with_raw_witness
FAILED tests/test_reading_typed_adapter.py::test_multiple_plan_inputs_for_one_floor_are_trusted_filtered
4 failed, 91 passed
```

⇒ **不是假锁。** 两个变体都精确命中，且线材层（Literal）本身也有独立锁把着。

#### 1.4 二分的另一半也真在工作（反向证明分母不是常量）

`p7_trusted_filter.py`（自写，独立组装 typed request，不借施工方夹具）把 `East_view`
改成**多层 binding**（受信输入侧成因）：

```
--- BASE ---              n_atoms = 108 | window_elevation_geometry.denominator_units = 44.0
                          filtered_components = []
--- TRUSTED_FILTERED ---  n_atoms =  93 | window_elevation_geometry.denominator_units = 32.0
  filtered_components = [{"source_input_id":"East_view","component":"elevation_opening_xy",
    "floor_ids":["F1","F2"],"cause_class":"trusted_input",
    "reasons":["elevation_floor_partition_unresolved"]}, {…"elevation_opening_z"…}]
  East_view elevation_opening_xy not_applicable trusted_input filter ['elevation_floor_partition_unresolved']
```

⇒ 受信侧确实**能**过滤（108→93、44.0→32.0），产品侧**一位都动不了**。二分真落地。

---

### P2 · U-10 帧冲突 = NA + 证人 + 分母保留 — **成立**

真跑判卷（生产入口，真实产物）：

```bash
cd $SP/clone_neuter && python $SP/probe.py identity      $SP/s_identity.json   # 冲突现场
cd $SP/clone_neuter && python $SP/probe.py align_frames  $SP/s_aligned.json    # 决定性探针
```

**① 冲突被认出、East/South 是干净对照**（`certificates.reading_normalization.component_applicability`）：

```
East_view  elevation_opening_xy applicable      none          score          []
East_view  elevation_opening_z  applicable      none          score          []
North_view elevation_opening_xy not_applicable  trusted_frame retain_as_miss ['elevation_local_x_sense_disagreement']
North_view elevation_opening_z  not_applicable  trusted_frame retain_as_miss ['elevation_local_x_sense_disagreement']
South_view elevation_opening_xy applicable      none          score          []
South_view elevation_opening_z  applicable      none          score          []
West_view  elevation_opening_xy not_applicable  trusted_frame retain_as_miss ['elevation_local_x_sense_disagreement']
West_view  elevation_opening_z  not_applicable  trusted_frame retain_as_miss ['elevation_local_x_sense_disagreement']
```

**② 证人含两边原始声明值**（`elevation_frame_disagreements`，North 条，West 同形）：

```json
{"source_input_id": "North_view",
 "binding_local_x_positive": "image_left_to_right",
 "product_local_x_positive_raw": "image_right_to_left",
 "product_local_x_positive_effective": "image_right_to_left",
 "binding_mirrored": false,
 "product_mirrored_raw": "false", "product_mirrored_effective": false,
 "binding_frame_transform_sha256": "aa904bc48b50dcc766860d8f21eb0c6602a94f6e0665ad7540422b1ae2def7db",
 "product_facade_sha256": "b1741a87aff200f2c0a95894305f1b07dcb797299109ee53dabc513ad353e4ad",
 "reason": "elevation_local_x_sense_disagreement"}
```

⇒ 不是只存结论，binding 侧与产品侧的**原值 + 两个 hash** 都在。

**③ 决定性探针（分母必须逐字相同）** —— 把 North/West 的 `facade.local_x_positive`
改回 `image_left_to_right`、`mirrored` 改 `"false"` 后重跑：

| | 冲突现场 | 对齐后 |
|---|---|---|
| `window_elevation_geometry.denominator_units` | **44.0** | **44.0** |
| `denominator_sha256` | `de9d54e3…` | `de9d54e3…` |
| `denominator_basis_sha256` | `64167638…` | `64167638…` |
| `denominator_atoms` 逐字节 | 相同 | 相同 |
| `elevation_local_x_sense_disagreements` | 2 | 0 |
| `elevation_frame_disagreements` | 2 条 | `[]` |

**④ 目标真留在分母里并照常算 miss**：冲突现场 North/West 的 `opening_source_rows` 共 **30 行，
全部 `result == "miss"`、`eligible_units ≥ 1.0`**（East/South 25 行同为 miss，因该 attempt 质量本就不合格）。
`denominator_atoms` 里 North_view / West_view 的 `elevation_opening_xy` / `elevation_opening_z` 原子俱在。

**⑤ 破坏测试 N7（忽略帧不一致）**：

```
FAILED tests/test_reading_typed_scoring_slice0.py::test_sm24_local_x_disagreement_is_input_scoped_na_with_raw_witness
FAILED tests/test_reading_typed_scoring_slice0.py::test_product_geometry_bytes_cannot_change_denominator
FAILED tests/test_reading_typed_adapter.py::test_sm24_frame_disagreement_witness_preserves_raw_declarations
FAILED tests/test_reading_typed_adapter.py::test_real_elevations_use_canonical_ranges_and_ruled_vertical_fallback
FAILED tests/test_reading_typed_score_integration.py::test_real_reading_sidecar_publishes_both_certificates_and_channel_scores
5 failed, 115 passed
```

---

### P3 · U-05 rect 墙逐笔画剔除 + 计数 — **成立**

注入方式：取 `1f_view` 里第一条 `pen=="wall"` 且 `geometry.kind=="line"` 的笔画（实测 = `S1`，
世界端点 `(0,20)→(10,20)`，正常轮里它是 `complete`），原地换成等价 `rect`。

```bash
cd $SP/clone_neuter && python $SP/probe.py one_rect_wall $SP/s_rect.json
```

| 断言 | 正常 | 注入 rect | 判定 |
|---|---|---|---|
| ① `1f_view / plan_segments` 状态 | `applicable / none / score` | **`applicable / none / score`** | ✅ 不是整通道 NA |
| ② 其余笔画照常计分 | 15 条 plan_segment 观测 | **14 条**（只少 `S1`）；`segment_rows` 仍 32 行 | ✅ |
| ③ `unmeasurable_observations` | 0 | **1** | ✅ 加 1 |
| ④a 覆盖侧 | `S1` 在观测里、行为 `complete` | **观测里没有 `S1`**（stroke id 逐条对账） | ✅ |
| ④b extras 侧 | `status=="extra"` 行 = 11 | **仍是 11**，且无任何行引用该笔画 | ✅ 没混进多画 |
| 分母 | `de9d54e3…` | **`de9d54e3…`**（逐字相同） | ✅ |

证人（一等字段，`unmeasurable_observation_witnesses`）：

```json
{"source_input_id": "1f_view", "source_stroke_id": "S1", "component": "plan_segments",
 "reason": "plan_wall_rect_has_no_centerline_contract", "cause_class": "product_content",
 "source_geometry_sha256": "3b0ea02607f30d179b1e820f4b646f26346b1eda83d4bf59c34555f3f2d70270"}
```

状态迁移可交叉验证：`complete 5→4 / miss 16→17 / extra 11→11` —— 被剔除的那笔从**覆盖侧**减掉、
**没有**跑到 extras 侧去，正是 U-05 要的语义。板上计数亦已渲染
（`"Unmeasurable observations: 1" in render_grade.reading_grade_status_lines(...)`）。

**破坏测试 N2（rect 改回杀整个 component）**：

```
FAILED tests/test_reading_typed_scoring_slice0.py::test_rect_wall_is_per_stroke_unmeasurable_and_counted
FAILED tests/test_reading_typed_adapter.py::test_plan_polyline_closure_and_rect_wall_are_per_stroke
2 failed, 118 passed
```

---

### P4 · U-03 / D-1 correction 对外可见判分逐字节未变 — **成立**

**没有采信施工方打印的任何 SHA。** 自写 `p4_correction_hash.py` + `p4_full_sidecar.py`，
在两份克隆里各跑一次同一脚本、自己算 SHA-256：

```bash
cd $SP/clone_base   && python $SP/p4_correction_hash.py $SP/p4_base.json   # f98d248
cd $SP/clone_neuter && python $SP/p4_correction_hash.py $SP/p4_head.json   # 7a067b4
cmp $SP/p4_base.json $SP/p4_head.json
```

```
f98d248 : sidecar.schema_version=8  payload.kind=c2_scored
          public_rows.sha256   = ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b
          wall_criteria.sha256 = 65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025
7a067b4 : sidecar.schema_version=9  payload.kind=c2_scored
          public_rows.sha256   = ee2a4d0d3de034417acd76420a9222899d2585d23bbff6f390ebe0ce09b6635b
          wall_criteria.sha256 = 65cf6dfb5136df7195b8cfb7811f7a7f666c90084e8743dc3bcbbf68f9a17025
cmp     : IDENTICAL（11287 bytes 逐字节相同）
```

（口径 = 裁定书 §U-03 指名的 `public_rows` = `segment_rows / segment_extras / claim_rows /
claim_summaries / extras`，`wall_criteria` = `walls_complete / boundary_complete /
no_extra_walls / no_duplicate_wall_strokes` 四条；规范序列化 = sorted + compact + UTF-8 + 一个 LF。
`n_segment_rows=20 / n_claim_rows=7 / n_wall_criteria=4`，两侧一致。）

**并把口径放宽到「整份 sidecar」再对一次**（比裁定要求更严），`diff -u` 全文只有 110 行，
**删除侧仅 7 行且无一条是判分内容**：

```
-  "contract_version": "1",              →  "2" + embedded_certificates（纯附加）
-  "sidecar_schema_version": "8"         →  "9"
-  "grade_renderer": "b4b_grade_png_v1"  →  "b4b_grade_png_v2"
-  "scorer_schema": "8"                  →  "9"
-  "content_sha256": "ba4c914e…"         →  "bab6ff82…"（整份 sidecar 的壳 hash）
-  "schema_version": "8"                 →  "9"
```

`score_criteria` / `segment_rows` / `claim_rows` / `claim_summaries` / `extras` /
`segment_extras` **区间内零 `-` 行**；新增的全是 `certificates`（两条 `present:false`）、
`channel_applicability: []`、`opening_source_rows: []`、`unmeasurable_observations: 0`、
`visibility_counts`（全零）、三个 `*_sha256: null` —— **纯附加**。

**破坏测试 N8（翻掉一个公开 correction 判分值）**：在 `extract_gt_plan_segments` 返回前
`replace(s, exterior=not s.exterior)`（`exterior` 是 correction `segment_rows` 的公开字段）：

```
wall_criteria.after_sha256=c2a26415b95d9783e91c21440aaabdbf2303ad460c16186a685d13b7033f9737
blocking_change=true
FAILED tests/test_reading_typed_scoring_slice0.py::test_correction_public_judgment_sha_matches_pre_v9_baseline
```

⇒ 对照真成立、锁真绑。**「`f98d248` 侧跑不起来」的情况没有发生**，无需报「无法判定」。

---

## 3. 结构命题

### P5 · 判卷器对识图永不抛异常（C1 / R-4） — **成立**

**① 畸形 payload 矩阵（全部走生产入口 `_grade_typed_attempt_artifacts`）**

| 输入 | 结果 | 抛异常？ |
|---|---|---|
| `{}`（空 dict） | 顶层 `not_applicable / unsupported_reading_contract` | 否 |
| `{"strokes": []}`（缺 `views`） | 顶层 `not_applicable / unsupported_reading_contract` | 否 |
| `{"views": [1,2,3]}`（`views` 非对象） | 顶层 `not_applicable / unsupported_reading_contract` | 否 |
| `{"views": {}}` | `c2_scored`，10 个 component 全 `product_content / retain_as_miss`，20 行全 miss | 否 |
| 视图内容乱码（`"not-an-object"` / `17`） | `c2_scored`，受影响 component 逐个 NA，其余照常 | 否 |
| 全笔画 `geometry={}` | `c2_scored`，`unmeasurable_observations=21` | 否 |

⚠️ 审阅单预期的是「顶层 NA」，实况是**信封层畸形 ⇒ 顶层 NA；视图层畸形 ⇒ 逐 component NA、顶层仍出分**。
经复核这**符合 U-04**（「歧义只降级它影响的那个 component」）与 U-13(ii)（产品侧成因保留分母算 miss），
不是缺陷。审阅单该处的「顶层 NA」是简写。**判定依据取审阅单写死的不成立条件**（「任一畸形输入让
`_grade_typed_attempt_artifacts` 抛出」）—— **无一抛出** ⇒ 成立。

**② `scorer_internal_failure` 通道存在、计数可见、按 profile 分档**

自写 `p5_internal_failure.py`，**进程内 monkeypatch**（不改任何生产文件）把
`score_service.score_typed_attempt` 换成 `raise RuntimeError("reviewer-injected scorer bug")`：

```
--- profile=exploratory injected_bug=True ---
  raised           : None
  sidecar/png 已写  : True / True
  payload.kind     : not_applicable | reason: scorer_internal_failure
  visibility_counts: {..., 'scorer_internal_failures': 1}
  warnings         : ['typed scorer internal failure; emitted not_applicable']
--- profile=regression injected_bug=True ---
  raised           : TopLevelNotApplicableError: top_level_not_applicable:scorer_internal_failure
  sidecar/png 已写  : True / True          ← 先落盘、后 raise
  payload.kind     : not_applicable | reason: scorer_internal_failure
  visibility_counts: {..., 'scorer_internal_failures': 1}
--- profile=golden injected_bug=True ---
  raised           : TopLevelNotApplicableError: top_level_not_applicable:scorer_internal_failure
--- profile=regression injected_bug=False ---（真实产物对照）
  raised           : None      payload.kind : c2_scored      scorer_internal_failures: 0
```

⇒ 通道存在、**计数一等可见**、`exploratory` warn 续行、`golden`/`regression` **fail-closed 且先持久化再抛**。

**破坏测试**：

- **N4**（`except Exception` 分支改成 `raise`）→
  `FAILED …slice1.py::test_totalizer_emits_internal_na_and_trusted_rejected`、
  `FAILED …slice1.py::test_reading_score_error_does_not_abort_later_attempts_in_exploratory`（2 failed）
- **N5**（拿掉 `golden/regression` 的 `raise TopLevelNotApplicableError`）→
  `FAILED …slice1.py::test_strict_profile_commits_top_level_na_before_raising[regression]` /`[golden]`（2 failed）

### P6 · F8 恒真陷阱已避开 — **成立**

识图契约识别是**结构性**的，`reading_typed_adapter.py:61-72`：

```python
def identify_reading_contract(raw: object) -> ReadingContractDecision:
    if not isinstance(raw, dict):        return ...("unrecognized", "reading_output_not_object")
    if "views" not in raw:               return ...("unrecognized", "reading_views_missing")
    if not isinstance(raw["views"], dict): return ...("unrecognized", "reading_views_not_object")
    if any(not isinstance(key, str) or not key for key in views):
                                         return ...("unrecognized", "reading_view_id_invalid")
    return ReadingContractDecision(READING_PRODUCT_CONTRACT, None)
```

**全函数没有 `schema_version` 三个字**。F8 那个 `output.get("schema_version", "3")` 默认值
已从 `run_stage.py:1360` 与 `score_reading_vs_gt.py` 两处**物理消失**：

```python
# run_stage.py（改造后）
if stage == "0_reading":
    output_schema = identify_reading_contract(output).contract_id
else:
    declared_schema = output.get("schema_version")
    output_schema = str(declared_schema) if declared_schema is not None else "unrecognized"
```

守卫侧 `decide_score_capability` 对 reading 要求 `product_schema == "reading_views_v1"`
**且** detector / adapter 版本双匹配，否则 `unsupported_reading_contract`；同时把
`gt.content_sha256 / view_manifest.content_sha256 / score_view_bindings_sha256` 并入
capability_key ⇒ 不是恒真断言。

**破坏测试 N3（让 detector 恒返回「是识图契约」）**：

```
FAILED tests/test_reading_typed_scoring_slice1.py::test_detector_is_total_and_leaves_per_view_shape_to_adapter[raw0-unrecognized-reading_output_not_object]
FAILED tests/test_reading_typed_scoring_slice1.py::test_detector_is_total_and_leaves_per_view_shape_to_adapter[raw1-unrecognized-reading_views_missing]
FAILED tests/test_reading_typed_scoring_slice1.py::test_detector_is_total_and_leaves_per_view_shape_to_adapter[raw2-unrecognized-reading_views_not_object]
FAILED tests/test_reading_typed_scoring_slice1.py::test_detector_is_total_and_leaves_per_view_shape_to_adapter[raw3-unrecognized-reading_view_id_invalid]
FAILED tests/test_reading_typed_scoring_slice1.py::test_detector_is_total_and_leaves_per_view_shape_to_adapter[raw4-unrecognized-reading_views_missing]
FAILED tests/test_reading_typed_scoring_slice1.py::test_non_object_reading_product_still_gets_total_na_artifacts
FAILED tests/test_reading_typed_scoring_slice1.py::test_exploratory_na_returns_artifacts_and_empty_criteria
FAILED tests/test_reading_typed_scoring_slice0.py::test_reading_contract_is_not_inferred_from_missing_schema
FAILED tests/test_c2_b4b_phase_d.py::test_gt_echo_fixture_preserves_runstage_cli_byte_parity
9 failed, 111 passed
```

⇒ 守卫有锁，且锁不止一把。

### P7 · 零观测 ≠ 不适用（C2） — **成立**

两种情形我在**生产层**各跑一遍，行为清晰可区分：

| 情形 | component 状态 | 分母 | 目标 |
|---|---|---|---|
| **applicable + 零观测**（`1f_view.strokes = []`） | `applicable / none / score` | `de9d54e3…`、108 原子（**未变**） | 全部算**真 miss** |
| **inapplicable（受信输入侧）**（East_view 改多层 binding） | `not_applicable / trusted_input / filter` | `ea3e0d4c…`、**93** 原子（44.0→32.0 单位） | 从分母移除，**并带 reason** `elevation_floor_partition_unresolved`（落在 `denominator_basis.filtered_components`） |

代码层对应 `reading_typed_score.py:556-579`（`scored_targets` 只按分母原子过滤、observations 只按
component 是否 `applicable` 过滤）与 `:659-685`（被受信过滤的目标另发零单位 NA 审计行、`na_reason` 取自 component）。

**破坏测试 N6（零观测就跳过该层、把目标丢掉）**：

```
FAILED tests/test_reading_typed_score_integration.py::test_supported_empty_and_invalid_plan_both_retain_targets_as_misses
1 failed, 94 passed
```

### P8 · gt 铁律未破（不变量 #4） — **成立**

自写 AST 扫描 `p8_gt_import_scan.py`（遍历全仓 `*.py`，展开 `Import` / `ImportFrom` 到
`module` 与 `module.alias` 两级），在 `f98d248` 与 `HEAD` 各跑一次、取差集：

```
=== 本批新引入的 gt import 边 ===
scripts/tool_scripts/render_grade.py:1137/1245: src.agent.judge.gt_schema.GroundTruthV3
scripts/tool_scripts/run_stage.py:1459/1460  : src.agent.judge.gt{,_schema}   ← 同文件 :1295 早已有同样的边
tests/test_c2_b4b_score_inputs.py:220        : src.agent.judge.gt_schema.GroundTruthV3
（无其它）
```

全部落在 **judge 侧渲染器 / 判卷 CLI / 测试**，**零条**落进
`src/agent/execution/**`、`src/validator/**`、`src/agent/reading/**`、`src/agent/correction/**`、
`src/agent/geometry/**`、`src/agent/pipeline.py`。

两个新模块 `reading_typed_adapter.py` / `reading_typed_score.py` 均在 `src/agent/judge/` 下；
其被导入方仅 = judge 模块 + `run_stage.py` / `score_reading_vs_gt.py`（两处都只导入
无 GT 依赖的 `identify_reading_contract`）+ 测试。既有 `tests/test_gt_discipline.py` 的
`test_gate1_checks_do_not_reference_gt` / `test_executors_do_not_reference_gt` /
`test_judge_side_gt_readers_remain_confined_to_judge_package` 三门在 HEAD 全绿。

### P9 · 既有行为未被破坏 — **成立**

| 条 | 证据 |
|---|---|
| ① v2 GT 仍走 legacy | `decide_score_capability`: `if gt_identity.schema_version == 2: return path="legacy_v2"`（未改）；`run_stage._judge_packet` 的 `else: gt = load_gt(case) … _judge_gt_artifacts(...)` 分支逐字未动 |
| ② correction v3 仍要求 accepted B5 六件套 + verified proof | `run_stage.py:1354-1356` 的 `if stage == "1_correction" and accepted_record is None: return {...None}` 未改；`window_host_proof` 仍经 `load_verified_accepted_correction(...)` 取得并校验 `accepted_attempt`；`decide_score_capability` 的 `product_artifact_contract ∈ {correction_b5_v1, correction_b5_orientation_v1}` 与 `product_schema ∈ {"3","v3"}` 两道守卫原样保留 |
| ③ 识图 attempt（accepted 与否）继续进判卷 | `run_stage.py:1351-1354` 的 F7 原注释与其早退条件逐字保留（早退只对 `1_correction`）；`_render_all_typed_attempt_grades` 仍无条件遍历全部 attempt |
| ④ 没有引入自动 `StageVerdict` | `git diff f98d248..HEAD -- src/ scripts/ \| grep StageVerdict` **零命中** |

唯一的行为差异是刻意的、且已在细稿登记：`if stage != "0_reading" and not isinstance(output, dict)` ——
识图的非对象产物不再静默跳过，改为出顶层 NA（这正是 C1/R-4 要的），correction 侧行为不变。

### P10 · 新的识图 E2E 没有拿答案当被测物 — **不成立**

#### ① parity 测试的断言体：**被改动了，且超出细稿 §13.3 的授权** ⇒ 见 m-1

`tests/test_c2_b4b_phase_d.py` 的改动（`git diff f98d248..HEAD`）：

```diff
-def test_d1_d2_d3_runstage_and_cli_share_real_v3_service_byte_for_byte(tmp_path):
+def test_gt_echo_fixture_preserves_runstage_cli_byte_parity(tmp_path):
-    assert sidecar["schema_version"] == "8" and sidecar["payload"]["kind"] == "c2_scored"
+    assert sidecar["schema_version"] == "9"
+    assert sidecar["payload"]["kind"] == "not_applicable"
+    assert sidecar["payload"]["reason"] == "unsupported_reading_contract"
```

- **byte-parity 断言本体完整保留**（`:208-209` 仍逐字节比 `score_vs_gt.json` 与 `grade.png`），
  且 neuter 证明它真绑（下表 N11）。
- 但改的**不只是名字与注释**：`kind` 从 `c2_scored` 变成 `not_applicable`。
  细稿 §13.3 只授权了 `"8" → "9"` 的版本迁移，并自行立规「其余断言若需改动须**单列记录**并取得主控批准」。
- 该变化本身是 U-11（扁平形状 ⇒ `unsupported_reading_contract`）的必然后果、**不是放水**
  （断言反而更细），但执行日志写的「Its substantive assertion is unchanged」与实况不符。
- 连带后果：这条 parity 现在比对的是一对 **NA 形态**产物，覆盖强度低于改造前。
  施工方另加了 `test_real_views_cli_and_runstage_artifacts_are_byte_identical`
  （真实 `{"views": …}` 走 scored 路径比对 sidecar + PNG 字节），**这条补位有效**（N11 证明两条都真绑）。

#### ② 新增识图 E2E 是否从 GT 反解产品坐标：**有一处，判 MAJOR**

逐行核过全部 5 个新增/改动测试文件的**产品侧**夹具来源：

- `_real_payload()` = 直接读真实 accepted 产物字节；所有 mutation 都从产品自身派生（geometry 置空、
  facade 取反、strokes 清空、line→rect 等），**不碰 GT**；
- `tests/test_reading_typed_adapter.py` 里的 `2.04 / 4.54 / 5.34 / 9.46` 等数字全在**断言侧**
  （= 产品 local_x 经 reviewed binding 投影后的期望世界值），不是注入的产品坐标；
- `_trusted_request` / `_grade_payload` 用 GT 只用在**受信/答案侧**（`load_score_gt_identity`、
  binding 校验），产品侧从不取 GT。

**唯一违例**：`tests/test_reading_typed_score_integration.py:124-134`

```python
payload["views"]["1f_view"]["strokes"].append({
    "id": "independent-plan-window", "pen": "window",
    "geometry": {"kind": "line", "p1": [4.66, 20.0], "p2": [9.46, 20.0]},
})
```

我在已签字答案里核到对应目标：

```
op_ae1  window  F1  F1:boundary:ea6ab5959cad49df5dc8d9b4
        world_along_interval = {'lo': 4.659999999999997, 'hi': 9.46}   source_refs=['North_view','plan-F1']
```

⇒ 注入笔画的两个端点 = **该答案窗的世界跨度**（`y=20.0` 即北侧边界线）。
施工方在执行日志里主动披露了来源（"corrected … to the signed GT North-window span"）。

判定：违反 D-1 裁定第 4 条与审阅单 P10② 写死的不成立条件 ⇒ **MAJOR（M-1）**。
影响面已核清（见 §5 M-1）。

### P11 · 全仓数字与基线差额逐条可解释 — **成立**

**独立全量（主工作树，我自己跑）**：

```bash
python -m pytest -q -p no:cacheprovider
→ 1881 passed, 10 xfailed, 150 warnings in 297.05s (0:04:57)     EXIT=0
```

与主控给的 HEAD 数字**逐字一致**，`xfailed` **仍是 10**（没有偷加 xfail）。

**差额逐条对账（用 `--collect-only` 独立复算，不采信施工方的分解）**：

```bash
(cd $SP/clone_base   && python -m pytest -q -n0 --collect-only) → 1796 tests collected   # = 1786 + 10
(cd $SP/clone_neuter && python -m pytest -q -n0 --collect-only) → 1891 tests collected   # = 1881 + 10
diff <(per-file counts base) <(per-file counts head)
```

```
  tests/test_c2_b4b_score_inputs.py                9  →  10   (+1)
  tests/test_reading_typed_adapter.py              -  →  18   (+18)
  tests/test_reading_typed_score_integration.py    -  →   7   (+7)
  tests/test_reading_typed_scoring_slice0.py       -  →   6   (+6)
  tests/test_reading_typed_scoring_slice1.py       -  →  18   (+18)     本批小计 +50
  tests/test_cv_toolbox.py                        20  →  23   (+3)
  tests/test_isolation.py                         37  →  79   (+42)     并行席位小计 +45
（其余文件计数逐条相等）
```

`1786 + 50 + 45 = 1881` ✅；`test_isolation.py + test_cv_toolbox.py` 由 `57 → 102` ✅
（与施工方声称一致，但这是我自己算的）。改名的 D-1 parity 测试计数中性 ✅。
新增数与 Slice 清单对得上（Slice 0 = 6 / Slice 1 = 18 / 适配器 = 18 / 集成 = 7 / 受信过滤 Va 锁 = 1）。

> ⚠️ 附带实况（不计入本批 finding，见 n-3）：在**全新 `git clone`** 上跑全仓会有
> **6 failed / 8 skipped**（`test_zone_agent`〔需网络/凭据〕、`test_validation_run_baseline::test_sm21_anchor_ep_clean`、
> `test_reading_score`、`test_checks_reading_correction`、`test_gt_from_dxf`、`test_inspect_dxf`）。
> 我在 `f98d248` 的克隆上跑同一组 —— **同样 6 failed** ⇒ 与本批无关，属「关键输入不在 git 里」的既有债。

### P12 · 跨批次零碰撞 — **成立**

对 sol 的 21 个 `7.31_ReadingTypedScoring*` 提交逐个取 `git show --name-only`，
再与四处点名路径做精确匹配：

```
src/agent/execution/isolation.py                 : 0 sol-commit touches
src/agent/execution/isolation_templates/guard.py : 0 sol-commit touches
scripts/tool_scripts/cv_probe.py                 : 0 sol-commit touches
tests/test_isolation.py                          : 0 sol-commit touches
tests/test_cv_toolbox.py                         : 0 sol-commit touches
AI_agent/guides/new_case_guide.md                : 0 sol-commit touches
```

这六处在本区间内的改动**全部**来自并行席位的
`9d6c278 / c9974fd / f2a4efb / c42de85 / 78967eb`（`7.31_Isolation*` / `7.31_S{1,2,3,4}_*`）。零越界。

---

## 4. neuter 表（全部在 `/tmp/clone_neuter` 真跑；基线子集 = `120 passed`）

子集固定为：`slice0 + slice1 + adapter + integration + c2_b4b_score_inputs + c2_b4b_phase_d +
c2_b4b_contract + render_grade + elevation_score`。每次 neuter 前后均 `git checkout -- .` 复位。

| # | 命题 | 破坏点 | 实际变红的测试 | 符合预期 |
|---|---|---|---|---|
| N1a | P1 | `_elevation_result` 帧冲突分支补发 `cause_class="trusted_input"` 的 exclusion（把产品成因洗成受信过滤） | `slice0::test_product_geometry_bytes_cannot_change_denominator`；`slice0::test_sm24_local_x_disagreement_is_input_scoped_na_with_raw_witness`；`adapter::test_multiple_plan_inputs_for_one_floor_are_trusted_filtered` （3 failed / 117 passed） | ✅ |
| N1b | P1 | 把 `ReadingFilteredComponentBasisV1.cause_class` 放宽到含 `"trusted_frame"` **并**在帧冲突分支发之（字面恢复原稿的过滤权） | 上述三条 + `slice1::test_denominator_constructor_accepts_only_canonical_trusted_exclusions` （4 failed / 91 passed） | ✅ |
| N2 | P3 | rect 墙笔画改回 `malformed_segments = True`（杀整个 component） | `slice0::test_rect_wall_is_per_stroke_unmeasurable_and_counted`；`adapter::test_plan_polyline_closure_and_rect_wall_are_per_stroke` （2 failed / 118 passed） | ✅ |
| N3 | P6 | `identify_reading_contract` 首行直接 `return ReadingContractDecision(READING_PRODUCT_CONTRACT, None)`（恒真 detector） | `slice1::test_detector_is_total_and_leaves_per_view_shape_to_adapter`（5 参数化全红）；`slice1::test_non_object_reading_product_still_gets_total_na_artifacts`；`slice1::test_exploratory_na_returns_artifacts_and_empty_criteria`；`slice0::test_reading_contract_is_not_inferred_from_missing_schema`；`phase_d::test_gt_echo_fixture_preserves_runstage_cli_byte_parity` （9 failed / 111 passed） | ✅ |
| N4 | P5 | `score_typed_attempt_total` 的 `except Exception` 改成 `raise`（拆掉全量边界） | `slice1::test_totalizer_emits_internal_na_and_trusted_rejected`；`slice1::test_reading_score_error_does_not_abort_later_attempts_in_exploratory` （2 failed / 118 passed） | ✅ |
| N5 | P5 | 拿掉 `run_stage` 里 `golden/regression` 的 `raise TopLevelNotApplicableError` | `slice1::test_strict_profile_commits_top_level_na_before_raising[regression]` / `[golden]` （2 failed / 118 passed） | ✅ |
| N6 | P7 | `_segment_rows` 加 `if not floor_observations: continue`（零观测就丢目标） | `integration::test_supported_empty_and_invalid_plan_both_retain_targets_as_misses` （1 failed / 94 passed） | ✅ |
| N7 | P2 | 帧一致性判断改 `if False:`（完全忽略产品/binding 冲突） | `slice0::test_sm24_local_x_disagreement_is_input_scoped_na_with_raw_witness`；`slice0::test_product_geometry_bytes_cannot_change_denominator`；`adapter::test_sm24_frame_disagreement_witness_preserves_raw_declarations`；`adapter::test_real_elevations_use_canonical_ranges_and_ruled_vertical_fallback`；`integration::test_real_reading_sidecar_publishes_both_certificates_and_channel_scores` （5 failed / 115 passed） | ✅ |
| N8 | P4 | `extract_gt_plan_segments` 返回前翻转 `exterior`（改一个公开 correction 判分值） | `slice0::test_correction_public_judgment_sha_matches_pre_v9_baseline`（探针同时打印 `blocking_change=true`） | ✅ |
| N10 | P10② | `mapping` 改成 `item.input_id: (item.input_id,)`（input ID 直接当 GT view ID 比） | `integration::test_plan_input_id_maps_through_binding_gt_view_set_and_host_stays_na` （1 failed / 94 passed） | ✅ |
| N11 | P10① | `score_reading_vs_gt.py` 的 CLI attempt identity `+1` | `phase_d::test_gt_echo_fixture_preserves_runstage_cli_byte_parity`；`integration::test_real_views_cli_and_runstage_artifacts_are_byte_identical` （2 failed / 22 passed） | ✅ |

**11 次定点破坏，11 次真红，零假锁。** 与施工方自述的 neuter 表在重叠项上逐条吻合，未发现夸大。

---

## 5. Finding 清单

### ⚠️ MAJOR-1 · 新增识图集成测试注入了一条从已签字答案取来的产品坐标

**位置**：`tests/test_reading_typed_score_integration.py:124-134`
（`test_plan_input_id_maps_through_binding_gt_view_set_and_host_stays_na`）

**事实**：注入笔画端点 `[4.66, 20.0]` / `[9.46, 20.0]` = 受保护答案 `gt.json` 中
`op_ae1`（北立面窗）的 `world_along_interval = {lo: 4.659999999999997, hi: 9.46}` 落在北边界线上。
该测试随后断言 `result in {"complete","within_tolerance"}` —— 也就是说，**这条命中是被答案喂出来的**。

**为什么算问题**：违反 D-1 裁定第 4 条（「该新 E2E **禁止**从 GT 反解任何产品坐标」）。
这正是主控在 `_typed_attempt_payload` 上抓到的那个病的缩小版：被测物的一部分来自答案，
该断言在计分逻辑上不可能红（其红只能来自 ID 映射链路，见 N10）。

**影响面（已核清，请主控据此定分寸）**：

- 仅**一条笔画、一个测试**；同文件其余 6 条与 `slice0`（6 条）、`slice1`（18 条）、
  `adapter`（18 条）的产品侧夹具**全部**来自真实产物，零 GT；
- 承重命题 P1–P4 的证据链**不依赖**这条测试；
- 该测试真正要锁的性质（input ID 必须经 `binding.gt_source_view_ids` 集合交集、
  而不是直接与 GT view ID 比字符串）**确有真锁**（N10 命中）；
- 施工方在执行日志里**主动披露**了该坐标的来源，未掩盖。

**建议出口（三选一，主控裁）**：
(a) 把注入笔画改成**产品侧自证**的坐标（例如从产品既有 `1f_view` 笔画端点派生一条落在同一支撑线上的窗），
使命中不再由答案喂出；(b) 若该断言确需一次命中，则把它降为**只断言 ID 映射链路**（例如断言
`matched_observation_ids` 的解析路径经过 binding 的 GT view 集合），删掉 `result == complete` 的分数断言；
(c) 保留但在测试内**显式注释坐标来源 = 已签字答案**并改名（对标 D-1 对 parity 夹具的处置），
同时在细稿 §13.3 登记为第三条授权例外。

### MINOR-1 · 超出细稿 §13.3 授权范围改了两处既有断言，且未按其自订规则单列记录

细稿 §13.3 白纸黑字：「Exactly two existing test edits are authorized」+「No other current
assertion may be weakened. If a new failure requires changing one, **record it separately with the
exact false premise and obtain controller approval**.」实际改了**三处**：

1. `tests/test_c2_b4b_phase_d.py::test_gt_echo_fixture_preserves_runstage_cli_byte_parity`
   —— 改名 + 注释（**已授权**）、`"8" → "9"`（**已授权**）、
   `payload["kind"] c2_scored → not_applicable` + 新增 `reason` 断言（**未授权、未单列**）。
2. `tests/test_c2_b4b_contract.py::test_typed_capability_dispatch_never_downgrades_v3_to_legacy`
   —— reading 分支从 `assert …path == "c2_v3"` 改成
   `assert reading.path == "not_applicable" and reading.reason == "unsupported_reading_contract"`（**未授权、未单列**）。

**定性**：两处都是已采纳裁定（U-11 / F8 契约守卫）的**必然后果**，方向都是**变严不是放水**，
我逐条核过没有覆盖任何真实缺陷 ⇒ **不升 MAJOR**。
但执行日志「Its substantive assertion is unchanged」的表述与实况不符（`kind` 断言确实换了），
属本项目多次登记过的「声称大于实况」小型复发。

**建议**：把这两处补记进执行日志/细稿 §13.3（写清原断言为何在新契约下是错的），一行即可。

### NIT-1 · 同一 reason 字面量跨两个相反的分母处置

`reading_view_schema_unsupported` 同时出现在：

- `reading_typed_adapter.py:773 / :915` —— `cause_class="product_content"` / `retain_as_miss`（产品视图不是对象）；
- `reading_typed_adapter.py:1217` —— `cause_class="trusted_input"` / `filter`
  （manifest entry 的 view_type 与 binding 类型对不上，纯受信侧成因）。

权威字段是 `cause_class` + `denominator_disposition`，判定不受影响；但只看 `reasons`
的人核者会把两种相反处置读成同一件事。建议受信侧换一个专用码（如 `reading_view_binding_type_mismatch`）。

### NIT-2 · `test_adapter_has_no_typed_gt_import` 是单串词法扫描，与日志措辞的强度不匹配

该锁只断言 `"src.agent.judge.gt_schema" not in source`。而 `derive_reading_denominator_v1`
在函数体内 `from src.agent.judge.segment_score import extract_gt_plan_segments`
（`segment_score` 自身 import `gt_schema`），且第一个形参就是 typed GT 对象。
日志「The product-only adapter remains free of a typed-GT schema import」字面为真、
但容易被读成「适配器不接触 typed GT」。**不违反不变量 #4**（该模块在 `src/agent/judge/` 下，
本就有读 GT 的资格），故只记 NIT。代码注释 `:1438-1442` 其实已把理由写清楚了，建议把该注释的口径同步到日志。

### NIT-3 · 全新克隆跑不出全绿（既有债，非本批）

`git clone` 后在 `f98d248` 与 `HEAD` 上均有同样 6 条 failed（依赖 gitignored 工作树输入或网络）。
与 2026-07-26 已登记的「关键输入不在 git 里」同族。本批未加重亦未减轻，**只作登记**。

> 另：主工作树里出现的未跟踪文件 `src/agent/execution/isolation_templates/access_log.jsonl`
> **不是**测试产生的（我在克隆里单跑 `tests/test_isolation.py` → `79 passed` 且该文件未被创建），
> 应是并行席位的交互式操作留下的。不计入本批。

---

## 6. 附：审阅方纪律自证

**① 主工作树零生产码改动**

```bash
$ git status --short          # 收尾时刻
?? AI_agent/logs/reviews/request/2026-07-31_isolation_scaffold_construction_dispatch.md
?? AI_agent/logs/reviews/request/2026-07-31_isolation_scaffold_rework_r1.md
?? AI_agent/logs/reviews/request/2026-07-31_isolation_scaffold_sol_review.md
?? AI_agent/logs/reviews/request/2026-07-31_reading_typed_scoring_brief.md
?? AI_agent/logs/reviews/request/2026-07-31_reading_typed_scoring_glm_review.md
?? AI_agent/logs/reviews/verdict/2026-07-31_isolation_scaffold_sol.md
?? AI_agent/logs/reviews/verdict/2026-07-31_reading_typed_scoring_design_controller_rulings.md
?? AI_agent/logs/reviews/verdict/2026-07-31_reading_typed_scoring_glm.md          ← 本文
```

**已跟踪文件零改动**（无 ` M ` / ` D ` 行），未跟踪项全部是审轨文档。
**本裁决书是本审阅方在主树上写下的唯一文件。**
其余未跟踪项属并行席位（该席位在本审阅期间仍在活动，故 `git status` 的未跟踪列表会随时刻变化；
上一次快照里还有一个 `src/agent/execution/isolation_templates/access_log.jsonl`，见 NIT-3 附注）。

**② 受保护答案树逐字节未动**

```bash
$ find case_tests/test_baseline/gt/sm24_anchor -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
e78c6e7e015746c14d8f70521551a71ee77b6e726259000ecf6133f91d61771f  -
$ find case_tests/test_baseline/gt/sm24_anchor -type f | wc -l
14
$ git diff --name-only f98d248..HEAD -- case_tests/
（空 —— 本批亦从未触碰）
```

与主控给的基准值 `e78c6e7e015746c14d8f70521551a71ee77b6e726259000ecf6133f91d61771f` 逐字相同。

**③ 破坏测试全部在 `/tmp` 克隆里做**，每次前后 `git checkout -q -- .` 复位并核 `git status` 为空。

**④ 无法判定项 = 0。** 本轮所有命题都有可复跑的第一手证据；P4 的对照在 `f98d248` 侧跑通，
不需要按「跑不起来 ⇒ 无法判定」的出口走。
