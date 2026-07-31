# 2026-07-31 识图链路断点施工记录

> 执行席：sol（CONSTRUCTION）
> 派工单：`AI_agent/logs/reviews/request/2026-07-31_reading_chain_gaps_dispatch.md`
> 基线：`1997 passed / 10 xfailed / 0 failed`

## 边界与禁区

- 不改 `src/agent/judge/**`、`case_tests/test_baseline/gt/**`、`AI_agent/CLAUDE.md`。
- G-1 gate① 与 G-2 residual fail-closed 均只量影响面，不代主控裁决。
- G-3 只加「合并长线视图」，原候选不删、不筛、仍可达。

## G-1 · `scale_origin` 生产者合约

### 影响面实测（gate①，待主控裁决）

口径：数工作树中 `case_tests/**/{0_reading,phase1}/*.json`，且 JSON 同时满足
`image_kind == "plan"` 与 `strokes` 为 list；这与 gate① 的单视图产品输入口径一致，
排除 `*_checks.json` / judge packet / prescan sidecar；另列 Git 已跟踪子集，避免把
当前未跟踪/ignored 的有效历史产品静默漏掉。

- 工作树既有主产品：**40** 份；`scale_origin` 可用 **31/40**，不可用
  **9/40 = 22.5%**。
- Git 已跟踪子集：**38** 份；可用 **29/38**，不可用
  **9/38 = 23.7%**。多出的两份均可用：
  `sm21_anchor/run_2026-07-01_sonnet_e2e_r1/phase1/{1f_view,2f_view}.json`。
- 九份不可用产品均是整个 key 缺失，无「有 key 但半缺」情形。
- 若现在把 gate① 改为 acceptance block：无论采用哪一库存口径，绝对新增阻断均为
  **9** 份；工作树其余 **31** 份不受影响。本席未改 validator。

九份受影响产品分布：

- `sm21_anchor/run_2026-07-01_sonnet_e2e_r1`：2
- `sm21_anchor/run_2026-07-01_sonnet_e2e_r2`：2
- `sm21_anchor/run_2026-07-02_sonnet_flow_e2e`：2
- `sm21_anchor/run_2026-07-05_haiku_downgrade`：2
- `sm24_anchor/run_2026-07-07_haiku_cv_probe`：1

### 施工

- `guide.md` §1/§2/§6：plan 视图必须声明 `scale_origin`；明确
  `world_x_m/world_y_m` = plan-local `(0,0)` 的世界米坐标，全局唯一原点 =
  整栋投影最大边界 SW 内角，禁每层本地原点；加 JSON 样例与 self-check。
- `pen_library.md`：把标定结果落入顶层 `scale_origin` 定为 plan 必做 container action。
- per-run directive 待主控同步：`session_kickoff.md:4-6` 的
  `Do no spatial-topology reasoning and no world placement`
  需改成「不做 topology placement；plan 仅例外声明 `scale_origin`」，否则与新主合约相冲。

### 锁与 neuter

| 锁 | 定点破坏 | 实跑变红测试 | 还原后 |
|---|---|---|---|
| `test_plan_scale_origin_is_a_locked_reader_instruction_contract` | `guide.md` §1 把 `Every plan view` 定点改为 `Every plan sketch`，使必填指令契约断开 | `tests/test_reading_schema.py::test_plan_scale_origin_is_a_locked_reader_instruction_contract` | 实跑 `1 failed`；还原后 `tests/test_reading_schema.py` = `10 passed` |

## G-2 · 标定可靠性

### 两轴阈值：先量后定，双向论证

可复算定义：先对 x/y 各自做过原点最小二乘
`s_axis = Σ(value_m × span_px) / Σ(value_m²)`，再算
`d = |s_x-s_y| / ((s_x+s_y)/2)`。实测在选阈值之前完成：

- 仓内 **11** 份无 residual warning、x/y 齐全的已接受 clean-vector 标定：
  `d = 0.0012%–0.1376%`；最大值为 sm24 07-07 plan 的 `36.30 vs 36.35 px/m`。
- 07-25 已独立验真的 sm24 同图另一合法 1 px 控制点取法为 **0.28%**；
  亚像素质心修正后为 **0.121%**。
- 已确认错控制点的最小前科为 **1.92%**；sm21 废弃迭代为
  `13.96%–88.86%`；本轮 pilot `37.5 vs 40.9 px/m` 为 **8.673%**。

因此把「合法 0.28% 实测上界向上取到两位小数百分点」作为
**0.30%** 阈值（recipe = `0.003`），而不是先拍数字。

- **不误拒方向**：全部 11 份已接受产品 + 0.28% 合法人工取点均在门内。
- **不误放方向**：1.92% 最小已知错例为阈值 6.4×，pilot 为 28.9×，
  均在混合前失败。对 20 m 跨度，门内两轴任一标尺相对另一标尺
  的最坏差异 `< 0.003/(1-0.0015)×20 = 0.0601 m`，只占 judge `0.30 m`
  墙容差的 20.1%；阈值本身不会允许标定误差先吃完判卷容差。

### 施工

- `px_m_calibrator`：先独立拟合 x/y；`d > 0.003` 立即 `ValueError`，
  错误文本带 x/y px/m、实测 d、阈值与「重查 extension-line intersections」；
  不再产出混合尺。合格结果附 `axis_px_per_m` / `axis_relative_deviation`
  / `axis_relative_deviation_limit`。单轴多锚点仍可做 residual 评估，不伪造跨轴检查。
- prescan 新增派生、advisory-only 的 `calibration_span_candidates.json` +
  `calibration_span_overlay.png`：用边界背景差分提取墨迹，正交开运算找长尺寸线，
  以垂直 extension-line 交点确定 `px_a/px_b`。它不做尺寸/墙语义，
  读图者仍须核 overlay + 图上尺寸文本。原 `candidates.json` 与三个 kind view
  对象/ID/可达性不变，新视图不塞入 master 改号。
- sm24 实图检出 x 交点 **247.5→611.5 = 364.0 px**，y 交点
  **150.5→878.0 = 727.5 px**；配 10/20 m 后两轴为 `36.40 vs 36.375 px/m`，
  `d = 0.0687%`，在门内且与 07-25 独立测量一致；不再用 pilot 的
  `245→620` / `54→872` 目测锚点。

### residual warn 改 fail-closed 的影响面（待主控裁决）

口径：扫描 `case_tests/**` 内 `tool == "px_m_calibrator"` 的已存 sidecar，
按各 sidecar 已记录的 `warnings` 重放当前
`calibration_warn_residual_px=2.0` / `_m=0.05`。

- 已存 sidecar **17**；无 warning **12/17**；若 warn 升为 raise，新失败
  **5/17 = 29.4%**。
- 其中 4 份是 sm21 1f_view `001`–`004` 废弃的迭代试探（RMSE
  `0.725–5.895 m`）；升级后会中止且无 sidecar，改变「先产诊断再细化锚点」工作流。
- 第 5 份是 `run_2026-07-08_gpt54mini_cv_retest/South_view/001`：只有 y 锚点
  `-2.346 px / -0.0405 m`（米残差未超 0.05，像素残差超 2），但该轮最终
  **elevation windows 15/15 complete**。因此 fail-closed 会新阻断至少一条历史上
  产出正确产品的路径，不只是阻断废弃试探。
- 本轮 pilot `RMSE 0.474 m` 也会被阻断（正向收益）；但新增的
  0.30% 跨轴门已会更早阻断它，所以 residual 升级的边际收益主要在
  「同轴多锚点不一致」，而兼容代价是上述 5/17。

本席未改 residual warning 语义；请主控裁决保持 warn、全面 fail-closed，
或仅对「最终接受/落笔」模式 fail-closed。

### 锁与 neuter

| 锁 | 定点破坏 | 实跑变红测试 | 还原后 |
|---|---|---|---|
| 两轴不一致在 blend 前失败 | `tools.py` 把 raise 分支定点改为 `if False and axis_relative_deviation > ...` | `tests/test_cv_toolbox.py::test_px_m_calibrator_rejects_cross_axis_anisotropy_before_blending`，实跑 `1 failed`，`Failed: DID NOT RAISE <class 'ValueError'>` | 还原后受影响子集 `246 passed` |
| extension-line 交点端点助手 | `recipes.py::_foreground_mask` 定点返回全 False mask | `tests/test_cv_toolbox.py::test_prescan_sm24_calibration_spans_find_extension_line_intersections`，实跑 `1 failed` / `StopIteration` | 还原后受影响子集 `246 passed` |

受影响子集由下列命令算定：

```bash
python scripts/tool_scripts/affected_tests.py --changed \
  src/agent/reading/cv_toolbox/recipes.py \
  src/agent/reading/cv_toolbox/tools.py \
  tests/test_cv_toolbox.py --explain
```

输出 `SCOPE: SUBSET` = `tests/test_affected_tests_map.py tests/test_cv_toolbox.py
tests/test_gt_discipline.py tests/test_isolation.py`；实跑 **246 passed**。

## G-3 · 预扫共线长线视图

### 根因实测（先于施工）

源：本轮 pilot 未筛的
`0_reading/cv_evidence/1f_view/prescan/{candidates,structural_candidates}.json`
+ `case_data/1f_view.png`；以 structural peak band 的原 `p1_px/p2_px` 计数，并在
FWHM 带内对每个 gap 做 RGB 分类，未用 GT。

| 外墙 peak | 交点夹定跨度 | 原碎片数 | 最长碎片 | gap 数/长度 px | gap 像素证据 |
|---|---:|---:|---:|---|---|
| North row `y=155.283` | `x=252.105→606.883` (354.8) | 3 | 92 | 2: 56,176 | 56 px 深色门洞；176 px `72.1%` cyan 窗带 |
| South row `y=873.428` | 同上 | 4 | 91 | 3: 57,31,57 | 两个 gap 各 `54.9%` cyan 窗；31 px `78.7%` 深色门洞 |
| West col `x=252.105` | `y=155.283→873.428` (718.1) | 6 | 111 | 5: 55,44,56,59,175 | 5 个 gap 的 cyan 占比 `69.4%–73.0%`，全是窗带 |
| East col `x=606.883` | 同上 | 5 | 203.4 | 4: 55,44,175,56 | 前三个 cyan `72.1%–72.6%`；末个 `94.1%` 深色门洞 |

合计：四条外墙被分成 **18** 碎片，中间正好 **14** 个洞口 =
**11 window + 3 door**，与图上开口类型/数量逐一吻合。

对派工单根因推测的校正：

- **确认**：灰度 mask 主动排除 cyan 窗线，门洞是背景色，所以 `_runs`
  必然在每个窗/门处分段；之后确实**没有任何结构线重组层**。
- **否证两个细节**：`merge_gap_px=2` 只在 `window_cc_detector` 的 bbox merge 路径使用，
  prescan line-band 从未读该参数；`min_run_px=4` 只删小于 4 px 的噪声，上述
  18 段均存活，不是造成断点的原因。四墙夹定跨度内的 gap 也没有一个
  由 dimension-line crossing 造成；尺寸注记造成的碎片在建筑跨度外。

因此核心根因「开口使 mask 断段 + 无重组」得到实测确认，但不把
`merge_gap_px` / dimension crossing 的原推测写成事实。

### 施工

- 新增派生视图 `long_structural_lines.json` + `long_structural_overlay.png`；
  原 `candidates.json` / `structural_candidates.json` 对象、ID、顺序原样保留。
- 合并法是确定性 `reciprocal_orthogonal_intersections_v1`：只看 strength 至少
  `3 × recipe prominence`、长度至少 100 px 的带；row/col 必须各自有原碎片到达
  同一交点，再用最远两个双向交点夹定长线端点。这使图外尺寸文字碎片
  不能把墙无限外伸，同时能跨过任意宽的窗/门洞。
- 每条长线带 `source_candidate_ids`、`source_fragment_count`、
  `support_coverage_px/support_ratio`、`bridged_gaps_px`、正交交点列表与 method；
  所有证据可反查回原碎片。

### sm24 验收

实跑 `prescan_plan(case_tests/e2e_tests/sm24_anchor/case_data/1f_view.png,
include_cc=False)`：长线视图共 10 条（含内部结构线），其中四条外墙为：

| candidate | 像素长线 | 原碎片 | coverage / ratio | 跨过 gap |
|---|---|---:|---:|---|
| `long_line:001` | col `(252.105,155.283)→(252.105,873.428)` | 6 | 329.1 / 0.4583 | 5 |
| `long_line:003` | col `(606.883,155.283)→(606.883,873.428)` | 5 | 388.1 / 0.5405 | 4 |
| `long_line:005` | row `(252.105,155.283)→(606.883,155.283)` | 3 | 122.8 / 0.3461 | 2 |
| `long_line:010` | row `(252.105,873.428)→(606.883,873.428)` | 4 | 209.8 / 0.5913 | 3 |

**验收结论：sm24 plan 已产出 4/4 连续外墙线**，四线端点在互证角点
精确闭合；它们的 18 个原碎片全部仍可由 `source_candidate_ids` 达到。

### 锁与 neuter

| 锁 | 定点破坏 | 实跑变红测试 | 还原后 |
|---|---|---|---|
| sm24 4/4 外墙长线 + 原 348 碎片不改号且可达 | `_prescan` 在呼叫 `_merged_long_line_candidates` 的定点把 `long_structural_lines` 改为 `[]` | `tests/test_cv_toolbox.py::test_prescan_sm24_long_structural_view_yields_four_exterior_wall_lines`，实跑 `1 failed`，首条预期外墙 `len(matches) == 0` | 还原后受影响子集 `247 passed` |

## 最终验证

- G-1 定向：`python -m pytest -p no:cacheprovider -q tests/test_reading_schema.py`
  → **10 passed**。
- G-2 受影响子集：**246 passed**。
- G-3 受影响子集：**247 passed**。
- 三项提交完成后、HEAD `35f13e6`，按要求只跑一次全量：
  `python -m pytest -p no:cacheprovider -q`
  → **2001 passed, 10 xfailed, 0 failed, 150 warnings in 399.00s (0:06:39)**；
  相对基线净增 4 passed，`tests/test_gt_discipline.py` 已由全量实际覆盖。
- 全量结束后共享工作树出现不属于本席提交的
  `session_kickoff.md`、`src/validator/checks/{reading,schema}.py` 改动；本席未暂存、
  未修改、未把它们计入上述全量结论，合流者须单独验证这些并发改动。

## 提交与改动文件

- `68fd6d0 7.31_PlanScaleOriginInstructionContract`
- `421c9d3 7.31_CalibrationAxisConsistencyAndAnchors`
- `35f13e6 7.31_AdditiveLongStructuralLineView`
- `AI_agent/logs/reviews/execution/2026-07-31_reading_chain_gaps.md`
- `skills/intake_pipeline/0_reading/{guide,pen_library,cv_toolbox}.md`
- `src/agent/reading/cv_toolbox/{recipes,tools}.py`
- `tests/{test_reading_schema,test_cv_toolbox}.py`

## 请主控裁决 / review ask

1. gate①：按工作树库存会新增阻断 **9/40（22.5%）**，按 tracked 子集是
   **9/38（23.7%）**；请裁决 profile、迁移/豁免口径，再决定 validator hardening。
2. residual warn→fail：会阻断 **5/17（29.4%）** 历史 sidecar，其中一条来自最终
   `15/15` elevation windows 成功路径；请裁决保持 warn、全面 fail-closed，或仅最终
   接受模式 fail-closed。
3. 请复核并合流 per-run kickoff 与新 `scale_origin` 合约；共享工作树已有一份并发修改，
   不属于本席提交。
4. 请重点 adversarial review：0.30% 两轴阈值的合法端点边界、交点端点助手对非白底图的
   稳健性、长线互证是否可能把强内部网格误标为外墙；新增视图保持 advisory/additive，
   下游须显式选择，不应替换原 fragment 视图。
