# 执行日志 · S1 多层轮廓世界坐标吸附（GLM 施工，2026-08-22）

**派工单**：`AI_agent/logs/reviews/request/2026-08-22_gt_multifloor_coordinate_snap_dispatch.md`
**施工**：GLM（glm-5.3）· **代码改动**：`src/agent/judge/gt_extraction.py`（1 个文件，+71/−7 行）
**新测试**：`tests/test_gt_multifloor_world_snap.py`（6 把锁，全绿）
**过程与全部 scratch 产物**：`AI_agent/logs/experiments/2026-08-22_gt_coordinate_snap_glm/`

---

## 0. ⚠️ 先读：三个须主控/复核裁决的事项

### 0.1 锁 2 的「elevation applicable」子项在 sm25 上结构性不可达 —— 与 S1 无关，证据在 §5.2

`rejected → c2_scored` ✅、plan `applicable` ✅ 已达成。但 elevation 频道为
`not_applicable`，原因是**上一批已落地并复核的设计**：sm25 每个立面视图覆盖
F1+F2 两层，`reading_typed_adapter._elevation_result` 对 `len(binding.floor_ids) != 1`
的立面绑定一律 emit `elevation_floor_partition_unresolved`（trusted_input，filter
处置，不进分母）。该 filter 在读产物**之前**就发出，与指纹/坐标零关系——
S1 修不修都不会变。实证：

- 同一驱动、同一入口，sm24（单层立面绑定）→ `{'plan': 'applicable', 'elevation': 'applicable'}`（§5.2 复现）；
- sm25 换上 S1 修复后的 gt → elevation 仍 filter（`cause_class: trusted_input`，理由 `elevation_floor_partition_unresolved`）。

**我的处理**：不碰判卷侧（§六 明确不做；把多层立面分楼层打分是判卷架构改动，
须另行派工）。把该子项作为偏差如实上报，请主控裁决：接受「多层案 elevation =
trusted-input filter」为本批终点，或另立派工单实现多层立面按层分割。

### 0.2 T1 的答案：几何本体不变；content_sha256 字面值必变——差异 100% 归因于溯源段

- 受控实验（`PYTHONHASHSEED=42`，见 §6.1）：改动前后 sm24 重建的**几何段逐位相同**
  （除 `generator` 外全部 section 相等；与签字件几何也逐位相同）。
- `content_sha256` 从 `e87e4dd7…` → `a77a84b2…`，唯一差异 = `generator.extractor_sha256`
  （validator/vg 哈希未动）。该字段按设计记录「哪份实现产出此答案」
  （`compute_gt_implementation_hashes`），改动 `gt_extraction.py` 必然推进它——
  **签字件 sm24（07-26 签）内嵌的 extractor 哈希（`e5ff75…`）本就与现树（改动前 `69a2…`）
  不同**，即「重建 == 签字 sha」在本单之前就因正常代码演进而不再成立。
- 因此**已签字历史答案不需要重签**（其几何仍可逐位复现；文件自一致性校验照过）。
  派工单 T1 停下条款的实质条件（「历史答案全部要重签」）未触发；按「只有多层案几何变」继续，
  **此判断请主控/复核追认**。

### 0.3 途中撞出的既有缺陷（非本单引入，未修，登记待派工）

**F-79（建议编号）：sm24 单层转换跨进程字节不稳定，受 `PYTHONHASHSEED` 影响。**
同一树、同一命令，仅换进程哈希种子，增广 DXF 哈希在
`5141994f…`（=签字件）与 `44ac3bd5…` 之间翻转（stash 本改动后 6 跑 3/3 复现，
固定 seed 0/1/2/5 → 44ac，42/12345/99999/31337/4 → 5141；两分支均无 BLOCK 诊断）。
既有测试 `test_r1_1` 测不出来（同进程双跑共享种子）。**sm25 多层路径不受影响**
（seed 0/5/42 三跑 content_sha256 全等 `f7752dca…`，§6.2）。这也是 T1 必须 seed 受控的原因。
另：**本轮施工期间有并行席位在写 `case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_*`
（16:45 实测 mtime，非本席所为；本席全程未写 case_tests）**——全量对账时若该目录相关测试变红，
先归因并行席位再定责。

---

## 1. 七条前提独立复核结论（全部成立，均带实测）

> 派工单警告主控本轮已有四条前提被抓错；七条逐一当作可能错的前提独立验证。

| # | 结论 | 实测要点 |
|---|---|---|
| Q1 | ✅ 成立 | `request_v3.json`：`plan-F1 m02=30.469`、`plan-F2 m02=-24.511800000000004`，两者 `m12` 相同（`-28.213600000000003`）。逐字吻合 |
| Q2 | ✅ 成立 | §四 命令原样跑：`max |Δx| = 3.552713678800501e-15`，`max |Δy| = 0.0`。东/西（y 轴）区间两层相同、南/北（x 轴）不同——与「m02 异、m12 同」的因果方向精确吻合 |
| Q3 | ✅ 成立（零号复现） | 增广 DXF 里两原生环都在 0.1 native 网格上（量化在前）；手工按各自仿射求值**逐位复现** gt 里的世界值（噪声恰诞生于 `_transform` 的求值点）；`_transform` 之后无任何网格吸附（`_snap_segments` 是**每视图内部**的近邻合并，跨视图不可能合；`_norm_zero` 只规 `-0.0`） |
| Q4 | ✅ 成立 | `36fb25250aad` vs `fbfc5e046f79`（§四 命令输出） |
| Q5 | ✅ 成立 | North/South：F1 `(0.0, 25.0)` vs F2 `(-3.55e-15, 24.999999999999996)`（§四 输出） |
| Q6 | ✅ 成立 | GPT verdict MAJOR-2 原文：只修指纹则默认生成器越过指纹门、继续产出 North/South 无效 origin；Va 逐层严格 `==` |
| Q7 | ✅ 成立 | `tarch_normalize.py:2923-2930` 注释原文与派工单引文一致，值 `1e-9`，论证形态=「重结合噪声 O(1e-15)；1nm 比毫米量化步长低 6 个量级、比噪声底高 6 个量级」 |

### Q3 零号复现（关键中间证据）

改动前用官方入口完整重建 sm25（`run_tarch_conversion` → `extract_gt_v3`）：

```text
rebuilt content_sha256: 6c36d9e83f0cfdf49b5b769cac2facf66a63dcb0b0ef5d62513b47c3e82dcfbb
geometry sections identical to signed: True      # 与签字件几何逐位一致（sha 差仅 generator/verification）
F1 fingerprint 36fb25250aad  verts[0..2]: [0.0, 13.999999999999996], [5.0, 13.999999999999996], [5.0, -3.55e-15]
F2 fingerprint fbfc5e046f79  verts[0..2]: [-3.55e-15, 13.999999999999996], [4.9999999999999964, ...], ...
```

增广 DXF 原生环检查（两层都在声明网格上、同一几何不同图纸位置）：

```text
F1 ring on 0.1 native grid: True    F2 ring on 0.1 native grid: True
plan-F1 world first3: [(5.0, 13.999999999999996), (0.0, 13.999999999999996), (0.0, 19.999999999999996)]
plan-F2 world first3: [(4.9999999999999964, -3.552713678800501e-15), ...]
```

手工求值 = gt 值逐位相同 ⇒ 噪声确实诞生于 `m00*x + m01*y + m02` 的浮点求值，
不是下游任何一步产生的。

---

## 2. 吸附取值论证（不拍新数，沿用 Q7 已签论证形态）

**取值：`_WORLD_SNAP_GRID_M = 1e-9` m，即 `tarch_normalize._PAIRING_Z_TOLERANCE_M` 已签值本身。**

按 Q7 论证形态逐项填本场景的实测数：

| 论证要素 | `_PAIRING_Z_TOLERANCE_M`（已签） | 本吸附 |
|---|---|---|
| 噪声量级（实测） | O(1e-15)，|z|≤4 m | **3.552713678800501e-15 m**（sm25 实测最大，\|world\|≤~55 m 的浮点重结合噪声） |
| 与声明量化步长的距离 | 1e-9 比 1 mm 低 6 个量级 | 声明量化步长 `q = node_join/10 = 0.1 mm = 1e-4 m`（`quant_native = 0.001/0.001/10`，judge_gt.yaml + `_Tols.quant_native`）⇒ **1e-9 比它低 5 个量级**（比 1 mm node_join 容差低 6 个量级） |
| 为什么不可能吸收真实漂移 | 同左 | 管线**可表示**的最小真实几何差 = 声明网格 0.1 mm = 吸附格距的 **1e5 倍**；吸附移动坐标 ≤0.5 nm，任何真实差异原样存活（锁 4 实测：1 mm 差异精确保留） |
| 为什么必定吃掉噪声 | — | 噪声底 3.55e-15 比格距低 **~6 个量级**；`round(v/g)*g` 对两侧同一数学值的求值结果必然落到同一格点 ⇒ 逐位一致（锁 1 实测） |

附带说明：注释里如实写「5 个数量级（相对 0.1mm 声明网格）」而非照抄 sm24 注释的
「6 个数量级（相对 1mm）」——论证形态复用，数字按本场景实测重算，没有抄旧数。
banker's rounding 不构成风险：格点量化输入的商距 .5 边界 ~1e6 格距，且两侧走完全相同的舍入路径。

**为何吸附只作用于「manifest 平面视图 ≥2」**：跨仿射噪声只在「同一几何经两套以上
仿射进同一世界区域」时才存在且才被逐位比较（单层案没有第二个仿射可与之分歧，
指纹/区间逐位比较的多层消费者也不存在）。单层路径保持字节冻结是 T1/锁 3 的硬要求
（sm24 签字值里本就带着同款噪声，如 `19.999999999999996`，无条件吸附必改它 ⇒ T1 停）。
这不是 sm25 特化：任何多层 case（视图≥2）自动获得吸附。

---

## 3. 实施（`src/agent/judge/gt_extraction.py`，单文件）

1. **`_WORLD_SNAP_GRID_M = 1e-9`**：常量 + §2 完整论证注释（噪声量级/与声明步长距离/为何不吸收真实漂移）。
2. **`_plan_world_snap_grid(manifest) -> float|None`**：manifest 平面视图 ≥2 ⇒ 返回格距；否则 `None`（单层路径字节冻结）。`GT_NEUTER_WORLD_SNAP` 环境变量 ⇒ `None`（fresh-process 摘接线 seam，照 `TARCH_NEUTER_GATE` 模式——摘的是**接线**：三个调用点仍在调 `_transform`，只是 dispatch 回无吸附路径）。
3. **`_transform(..., snap_grid_m=None)`**：世界仿射求值出口处 `round(w/g)*g` 双坐标吸附；`None` 时行为与改动前逐字节相同。
4. 三个调用点全部接线：`inspect_extraction_inputs`（巡检与提取看同一形态坐标）、`extract_plan_geometry`（footprint/zone 环）、`_plan_opening_geometry`（opening 平面证据 bbox 角点）。elevation 侧 `_elevation_geometry` 不动（每个立面视图单一仿射覆盖两层的同一堵墙，无跨仿射求值分歧；与 gt 平面侧的比较全部带 0.4 m 容差）。

**未做**（§六）：判卷侧严格相等未动；立面绑定生成器未动；gt 未代签；无 sm25 特化分支。

---

## 4. 锁 1（正向）实测 ✅

改动后完整重建 sm25（同官方入口）：

```text
fingerprints: {'F1': '52f382ee6abb40bcb2284a822a01fe27f80d2e026df53a4bc8b8c462e3d98621',
               'F2': '52f382ee6abb40bcb2284a822a01fe27f80d2e026df53a4bc8b8c462e3d98621'}   # 逐位相同
LOCK1 rings bit-identical: True
North/South: F1==F2 (0.0, 25.0)    East/West: F1==F2 (0.0, 20.0)    # 四族区间逐位相同
```

对改动前重建的几何差异面：`floors`、`openings`（坐标清洗的确定性下游：环顶点、
区间、由坐标哈希派生的 segment/opening id 与排序；zone 多边形 14/15 全部为清洗值）。
`sources`/`coordinate_frame` 等不变。跨 seed 稳定（0/5/42 三跑 content_sha256 全等）。

复现命令：§8 B 组。

## 5. 锁 2（端到端）实测：头条达成，elevation 子项见 §0.1

用 scratch 驱动 `drive_c2_score.py`（**复刻 `run_stage._grade_typed_attempt_artifacts`
同一 service 入口与全部 sidecar 输入**；只读 run 目录、判分产物写实验目录，
全程不写 case_tests）对 H2 六图 run 判分：

```text
$ python AI_agent/logs/experiments/2026-08-22_gt_coordinate_snap_glm/drive_c2_score.py \
    .../repro_post/gt_candidate_post.json .../lock2_scored
payload.kind: c2_scored                        # rejected → c2_scored ✅
channel_applicability: {"plan": "applicable", "elevation": "not_applicable"}
```

- rejected 的直接死因（`score_view_binding_invalid`）来自生成器对层间分歧拒产；
  换 S1 修复 gt 后生成器 6 条绑定全出、Va 逐层严格 `==` 通过、判分走到 c2_scored。
- elevation `not_applicable` 的处置=`filter`、`cause_class=trusted_input`、
  理由 `elevation_floor_partition_unresolved`（多层立面绑定按设计不打分，§0.1）。
- **sm24 对照**（同驱动、真实签字 gt）：

```text
$ python .../drive_c2_score.py case_tests/test_baseline/gt/sm24_anchor/gt.json \
    .../lock2_sm24_both_applicable --run-dir case_tests/e2e_tests/sm24_anchor/run_2026-08-02_sonnet_full_unsup
payload.kind: c2_scored
channel_applicability: {"plan": "applicable", "elevation": "applicable"}   # 单层立面的两频道达标实证
```

## 6. 锁 3 / T1 实测 ✅（§0.2 结论的证据）

受控对比（`PYTHONHASHSEED=42`，取与签字件同分支；分支抖动本身见 §0.3 F-79）：

```text
PRE  content_sha256: e87e4dd7e182d071ef0dea8cad410f6395cc4ee33a629cbcfb689a31db9aa01f2
POST content_sha256: a77a84b235a93af191b480e9923f2905daf171125a83f17a125ee46d08fd4c40
T1 (seed=42): geometry sections (all except generator) identical pre vs post: True
pre  generator: extractor=69a219493001  validator=894dc4158bcb  vg=8e45fd15b4df
post generator: extractor=4999cddda907  validator=894dc4158bcb  vg=8e45fd15b4df   # 唯一差异
post geometry == signed sm24 geometry: True
sm24 F1 verts 仍为 [0,0],[10,0],[10,19.999999999999996],[0,19.999999999999996]   # 单层噪声原样保留
```

受影响的 case 清单（几何实际变化的）：**仅 sm25-L_anchor**（多层）。
sm21_anchor 为 legacy v2、sm24_anchor 单层，重建几何均不变。

## 7. 锁 4（反向锁）与锁 5（neuter）实测 ✅

**锁 4**（`lock4_reverse.py`，A/B/C 三层证据）：

```text
A. unit:   noise pair  (5.0,14.0) == (5.0,14.0)            # 噪声坍缩，逐位相同
           1mm pair    delta = (0.001000000000000334, 0)   # 真实 1mm 精确保留，未被吸收
B. +2mm:   fail closed with ExtractionError: dxf_profile_floor_footprint_mismatch
C. +1mm:   fail closed with ExtractionError: dxf_profile_floor_footprint_mismatch
```

C 的机制值得记录：浮点求值使 +1mm 的实际差为 `0.001000000000000334`，比容差大
3.3e-16，环一致性检查（`<=` 1mm）保守地拦下——**吸附没有抹平它**（若被抹平，
两层指纹会变为相同、提取会成功），fail closed 正是锁 4 要求的方向。

**锁 5**（摘接线，非摘机制——env 只翻转 `_plan_world_snap_grid` 的 dispatch，
吸附代码与三处接线原样在位）：

```text
$ GT_NEUTER_WORLD_SNAP=1 <重建 sm25>
NEUTER fingerprints: {'F1': '36fb25250aad', 'F2': 'fbfc5e046f79'}   # 锁 1 变红，精确回退病态值
NEUTER North: F1 (0.0, 25.0)  F2 (-3.552713678800501e-15, 24.999999999999996)

$ <build_score_view_bindings 对 neuter 产物>            # 锁 2 变红（rejected 的链头）
SystemExit: East_view: 'East' facade floors disagree across ['F1','F2'] —
  F1: fingerprint=36fb25250aad…  F2: fingerprint=fbfc5e046f79 …
```

测试套件内的对应锁：`tests/test_gt_multifloor_world_snap.py`（6 条，含前提自证
`test_neuter_unwires_the_snap_and_restores_the_disease`——neuter 下夹具必须复现病症，
否则整套测试没有分辨力）。

## 8. 测试与全量对账

- 新测试：`python -m pytest tests/test_gt_multifloor_world_snap.py -q` → **6 passed**。
- 受影响子集：
  - `tests/test_gt_extraction.py tests/test_gt_from_dxf.py tests/test_gt_schema.py tests/test_gt_multifloor_world_snap.py tests/test_tarch_converter_reproducibility.py tests/test_elevation_score_bindings.py` → **98 passed**；
  - `tests/test_tarch_converter_p2_geometry.py tests/test_gt_promotion_path.py tests/test_gt_overlay.py tests/test_tarch_elevation_must_red.py tests/test_tarch_opening_carriers.py` → **178 passed, 1 xfailed**（该 xfailed 为既有）；
  - `tests/test_reading_typed_score_integration.py` → **9 passed**。
- 全量（主树 `python -m pytest -q -n auto`，期间未运行任何写 case_tests 的命令）：

> ⚠️ 过程纪律自曝：全量运行期间我曾改过 `gt_extraction.py` 一行**注释**（banker's
> rounding 论断的量化修正）——违反「全量在跑时不许动树」。风险窗口 =
> `test_tarch_converter_reproducibility.py::test_r1_4`（两次运行内嵌实现哈希比对）
> 若恰好横跨编辑时刻会假红。全量结束后已单独重跑该文件复核（见下）。

```text
<!-- FULL_SUITE_RESULT -->
```

基线对账：3008 passed / 13 xfailed ⇒ 本批预期 **3014 passed / 13 xfailed**（+6 新锁）。

## 9. T2 候选包（⛔ 未代签，等用户签字）

用官方 `gt_review_build.py` 从原始输入（`sm25-L_t3.dxf` + `request_v3.json` + 六图 rasters +
`zone_roles_review_only.json`）重建完整评审包：

```text
$ python scripts/tool_scripts/gt_review_build.py \
    --source-dxf case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf \
    --request AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json \
    --raster-dir case_tests/e2e_tests/sm25-L_anchor/case_data \
    --zone-roles AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/zone_roles_review_only.json \
    --out AI_agent/logs/experiments/2026-08-22_gt_coordinate_snap_glm/t2_review_bundle
bundle: AI_agent/logs/experiments/2026-08-22_gt_coordinate_snap_glm/t2_review_bundle
```

- **候选包路径**：`AI_agent/logs/experiments/2026-08-22_gt_coordinate_snap_glm/t2_review_bundle`
- **新 content_sha256（candidate）**：`f7752dcaa7c21d45318fffaeb3a0363b863cbf145ad4625eae76dd661b04a05b`
  （`review_index.json` 的 `candidate_gt_sha256` 同值；`verification.status == "candidate"`；
  与手工重建链字节一致；跨 seed 稳定）
- 两层指纹均为 `52f382ee6abb40bc…`（逐位相同）。
- 旧签字件（现网 `case_tests/.../sm25-L_anchor/gt.json`）content_sha256 =
  `f97cea65b445148d5e3ee79f51eebdc30114d1c357163ae2bc557cc02a912f9b`，**未动**。
- 后续（须用户执行，本席未做）：`gt_review_sign.py <bundle> --reviewer <用户> --signed-at <ISO>
  --confirm-near-threshold` → `gt_review_rerun.py` → `gt_promote.py`；晋升后六图 run 的
  sidecar（`judge_score_bindings.json` 等）须对新 gt sha 重建再判分。

## 10. 附：主要实测命令索引（产物均在实验目录）

| 组 | 命令 | 产物 |
|---|---|---|
| A 前提复核 | 派工单 §四 命令原样 + `request_v3.json` 读取 + 增广 DXF 环检查 | 本日志 §1 |
| B 重建 sm25（改前/改后/neuter/seed） | `run_tarch_conversion` + `extract_gt_v3`（脚本内联，见 `repro_pre/`、`repro_post/`、`neuter/`、`seedtest/`） | 各 `gt_candidate_*.json` |
| C 锁 2 | `drive_c2_score.py`（sm25 新 gt / sm24 对照） | `lock2_scored/`、`lock2_sm24_both_applicable/` |
| D 锁 4 | `lock4_reverse.py` | 控制台输出（本日志 §7） |
| E T1 | stash 前后 `PYTHONHASHSEED=42` 全量重建 sm24 | `sm24_rebuild_pre_seed42.json`、`sm24_rebuild_post_seed42.json` |
| F F-79 归因 | 同命令 ×（stash 后 6 跑 / 固定 seed 6+6 跑） | §0.3 |
| G T2 | `gt_review_build.py`（上行 §9 原文） | `t2_review_bundle/` |
