# prescan 候选收窄 — 阈值裁决分析（2026-07-09，Fable5 主控）

缘起：07-08 GPT-5.4-mini 交叉测试收工报告指出 prescan 候选太多（1f 825 个），
弱模型逐候选 crop 核验烧 token（pilot 86 次 cv 调用）。本分析用该 run 的真实侧车
（`run_2026-07-08_gpt54mini_cv_retest/0_reading/prescan/cv_evidence/`）+ sm21 gt
做**差分幸存验证**，裁决安全收窄参数。gt 只用于本分析（judge/人侧），不进工具代码。

## 候选构成（收窄前）

| 图 | 总数 | line_band | cc_box | tick | 投影峰 |
|---|---|---|---|---|---|
| 1f | 825 | 370 | 221 | 234 | 48 |
| 2f | 1103 | 544 | 228 | 331 | 68 |
| South | 498 | 199 | 167 | 132 | 18 |
| North | 347 | 124 | 127 | 96 | 14 |
| East | 225 | 91 | 77 | 57 | 13 |
| West | 185 | 64 | 81 | 40 | 11 |

放大机理：line_band = 每投影峰的 FWHM 带内按连通 run 切段（48 峰 → 370 段，~8x）。

## 差分幸存验证（关键结论）

方法：gt 墙轴/窗边投影到像素坐标（用 col 双外墙峰拟合 px/m：平面 91.2/90.9，
立面 57.6 ≈ run 内 South 标定 57.93），检查过滤前后哪些 gt 构件失去附近候选。

- **`min_strength≥0.08` + `min_line_len_px≥30`：全部 6 图、平面墙轴（col 9/9、row 8/8）
  与立面窗边（30 条）零新增丢失**（幸存集与不过滤完全一致）。
- 立面窗边本来就不在 line_band 通道里（窗竖边短、投影峰弱于 prominence 地板）——
  窗走 `window_cc_detector` 专用通道，不受 line 过滤影响。
- **立面 prescan cc ≈ 纯噪声**：South 167 个 cc 中 p50 面积 ~95px²（文本字形），
  min-dim≥40px 的只有 1 个 = 整楼轮廓连通域（窗框线与轮廓 8 连通粘连，不成独立组件）。
  → 立面直接 `--no-cc`。平面 cc 保持默认（未验证平面窗/门弧的 cc 依赖，不动）。
- **tick 永不过滤**：tick 是标定锚（尺寸链），实现上从未过滤的 line 候选派生。

## 推荐档在真实 run 上的削减

`--min-strength 0.08 --min-line-len-px 30`（+ 立面 `--no-cc`）：

| 图 | 总候选 | line_band（crop 核验大头） |
|---|---|---|
| 1f | 825→519 | 370→64（-83%）|
| 2f | 1103→651 | 544→92（-83%）|
| South | 498→138 | 199→6（-97%）|
| North | 347→105 | 124→9（-93%）|
| East | 225→62 | 91→5 |
| West | 185→46 | 64→6 |
| **合计** | **3183→1521（-52%）** | |

另加 `diagnostics.axis_summary`（按峰聚合，无损附加）：平面核验单位 370/544 段 → 48/68 轴。

## 标定复用实测

该 run 全程只做了一次正式标定（South）——跨图复用已是模型自发行为，缺的是验证纪律。
实测刻度分组：平面组 91.2/90.9 px/m 一致、立面组 57.6 px/m 一致，**两组间差 58%**
→ 盲复用跨组是灾难，组内复用 + 单锚点抽验（≤1px）安全。已落 cv_toolbox.md 纪律。

## 落地

- `recipes.py::_prescan`：`min_strength`/`min_line_len_px`/`label` 参数（默认 None/None/"prescan" = 行为不变），
  params+diagnostics 全记录（`line_band_candidate_count_prefilter`、`axis_summary`）。
- `cv_probe.py` prescan 子命令加对应 CLI 旗。
- `cv_toolbox.md`：候选预算纪律 + 立面 `--no-cc` + 组内标定复用纪律。
- 默认值刻意不动（保护 07-07/07-08 满分带配方）；推荐档由 skill 文档驱动。
- codex reasoning effort 下调 = 下次跑测的实验变量（CLI per-run 参数），非本批代码。
