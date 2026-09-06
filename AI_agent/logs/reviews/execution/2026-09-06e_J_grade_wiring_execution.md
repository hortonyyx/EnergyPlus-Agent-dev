# 交件 · J：判分接线 + 补立面（施工：GLM · 2026-09-06）

> 派工单：`AI_agent/logs/reviews/request/2026-09-06e_J_grade_wiring_dispatch.md`
> 工作目录 `/tmp/j_grade_glm`（`wt/09.06e_j_grade`），基点 `363844b3`。
> 开工三自检全过（HEAD=`363844b3`；`reading_grade.__file__` 落在本 worktree；派工单 155 行可读）。

---

## 一 ⭐⭐⭐ §三 那次测量：立面判分需要什么 × 今天的 gt 给不给得出

**结论：答案侧撑得起立面判分，未触发 A 层停报。** 全部实测（非转引），夹具 =
`case_tests/test_baseline/gt/sm25-L_anchor/`（答案根，只读）+ 真实 prototype 立面产物。

### 1.1 逐项对照表

| # | 立面判分需要 | gt 有没有 | 在哪个字段（gt.json v3） | 实测 |
|---|---|---|---|---|
| 1 | 视图身份（哪张立面） | ✅ | `sources[].views[]`：`kind:"elevation"` + `id` + `facade_family` | 4 张（E/N/S/W） |
| 2 | **跨层声明** | ✅ | 同上 `floor_ids` | 四张全部 `["F1","F2"]` |
| 3 | 该立面洞口全集（沿墙位置） | ✅ | `openings[].world_along_interval{lo,hi}` + `source_refs[role="opening_elevation"].view_id` 分组 | E 13 / N 8 / S 7 / W 6 = 34，每条恰好挂一张立面 |
| 4 | 洞口垂直区间 | ✅ | `openings[].z_interval{lo,hi}` | F1 z 0.2–2.3 / F2 z 4.6–6.2，与楼层自洽 |
| 5 | 洞口身份（门/窗） | ✅（答案侧） | `openings[].kind` | door 3 / window 31 |
| 6 | 洞口属哪层（拼回跨层立面） | ✅ | `openings[].floor_id` | North = F1 4 + F2 4 |
| 7 | 楼层结构线（层间线） | ✅ 派生 | `floors[].z_floor_m` + `ceiling_height_m` | z ∈ {0, 3.6, 7.2} |
| 8 | 立面端线（外轮廓左右端） | ✅ 派生 | `floors[].boundary_segments[]` 按 `facade_family` 过滤取 `world_along_interval` 并集 | E/S [0,20]，N/W [0,25] |
| 9 | along 轴基准与方向 | ✅（见 1.3 轴向发现） | `review/opening_elevation_audit.json` 每行 `datum_*` 方向声明（34 行齐，本单未消费） | 产品与答案同数轴 |
| 10 | gt 侧分辨率（1 mm） | ✅ | `generator.tolerances.dxf_axis_alignment_tolerance_m = 0.001`（A-11 已按 1 mm 规整入库） | boundary/floor 36/36 坐标严格落 1 mm 网格；⚠️ opening 的 z 带 +0.0214 mm 整体亚毫米偏移（§15.11 已登记的已知项，远小于容差带） |
| 11 | 产品侧分辨率（10 mm）声明 | ⚠️ 产品侧字段 | v0 产物**没有**该字段 ⇒ J-2 本单定形：判分读产物 `resolution_m`，缺席则具名常量兜底且 `declared:false` 如实标注 | 见 §四 |

### 1.2 产品侧（判分的另一半）供给

| 立面产物要给什么 | v0 产物有没有 | 字段 |
|---|---|---|
| 洞口沿墙区间 | ✅ | `openings[].x_range_m` |
| 洞口垂直区间 | ✅ | `openings[].z_range_m` |
| 结构线（楼层线/端线） | ✅ | `structure_lines[]`：`axis:"row"`=z 常数线（楼层线）、`axis:"col"`=along 常数线（端线+分段线），带 `pos_m`/`runs_m` |
| 世界系标定 | ✅ | `calibration`（x/z 链拟合 + `world_zero_px`） |
| **洞口身份 door/window** | ❌ **未声明** | 产物自带 `ledger.door_window_classified: false` ⇒ E5 判分记 `null`+理由（诚实空档），升格归 J-5（本单不做） |

**对齐实测**：每张立面在「恒等或镜像」二选一后，产品洞口与 gt **逐条吻合、偏差 2–23 mm**
——这正是 J-1 要求容差带的定量依据（写成 `==` 会四张全红）。

### 1.3 ⭐ 附带发现（施工中量出，非派工单预设）：立面 along 轴向

- East/South 产品与 gt **同向**（identity）；**North/West 镜像**（产品 along 轴方向相反；
  North 镜像后 8/8 逐条吻合，West 镜像后 6/6）。
- 与 typed 链的既有事实同构：`ElevationScoreViewBindingV1` 本就带
  `mirrored / along_origin / sign`（B4 线撞过同一堵墙）——**轴绑定是真实存在的缺口，不是本判分器造成的**。
- 本单处置（`elevation_grade.py:240-261`）：**两固定假设探测**——镜像 = 答案自己 along
  范围的反射（⛔ 无平移/缩放自由度，不是拟合）；切换需 margin ≥ 2 个 placed 洞口
  （边缘巧合不翻轴、真错位产品不会被洗白——有锁）；假设**显式写进**
  `grade["along_axis"]`（identity/mirror 各自 placed 数 + ambiguous 标志），⛔ 不静默翻转。
  将来 orientation binding 落地，`along_axis` 参数显式传入即可覆盖探测。

---

## 二 接线点清单（§2.1）

**flow 的识图判分现在怎么选判分器**（全部行号已回文件 grep 核对）：

| 环节 | 位置 | 作用 |
|---|---|---|
| 分流插入点 | `scripts/tool_scripts/run_stage.py:2130`（`_grade_typed_attempt_artifacts` 的 `0_reading` 分支，在 `_as_reading_views_envelope` **之前**） | as-drawn 产物走新判分、其余原样走 typed/legacy 路径（⛔ 旧路径未删） |
| 分支函数 | `run_stage.py:2050` `_grade_as_drawn_reading_branch` | 喂 gt（typed 层已加载的 `document.model_dump_json()`，⛔ 无第二次 gt 读取）+ `gt_sources/<case>` |
| **分类器复用** | `src/agent/judge/as_drawn/flow_wiring.py:95` `split_output_by_contract` → `vector_contract.classify_vector_json`（只读 import，`flow_wiring.py:54`） | ⛔ 不按文件名、⛔ 无第二分类器；`AS_DRAWN_CONTRACTS`（`flow_wiring.py:44`）只认 `as_drawn_plan` / `as_drawn_elevation_v0` |
| 视图身份解析 | `flow_wiring.py:120,134` | 显式 `view_id` 声明优先；立面 image stem 即 gt view id（`East_view`）；平面 `<n>f_view` 按层位解析（`1f_view`→`plan-F1`）；查不到 ⇒ `UnknownAsDrawnView` 响亮（⛔ 不猜） |
| 平面径 | `flow_wiring.py:172` `grade_as_drawn_plan` | 签名源 DXF 按 `request.source_dxf_sha256` **哈希绑定**（`flow_wiring.py:162`，⛔ 不按文件名 glob）→ `denominator()` → `reading_grade.grade()`（**判分器本体零改动**；J-2 量化带作 `pos_tol` 下界传入）→ `render_reading_grade` |
| 立面径 | `flow_wiring.py:194` `grade_as_drawn_elevation` | `elevation_targets(gt)`（只从 gt 派生）→ `elevation_grade.grade()` → `render_elevation_grade`（新，`scripts/tool_scripts/render_elevation_grade.py`，view-only） |
| 产物落盘 | `flow_wiring.py:201` `grade_as_drawn_attempt` | 每视图 `<stem>.grade.json` + `<stem>.grade.png` + 汇总 `score_vs_gt.json`（`as_drawn_grade_bundle_v1`）落 attempt 目录；混合 run 的非 as-drawn 视图点名 `leftover_views`（⛔ 不静默丢） |
| 返回形状 | `run_stage.py:2096-2100` | 与 typed 路径同构（`score_vs_gt`/`grade`/`score_criteria`），下游报告不学第二方言 |

接线锁（`tests/test_j_grade_wiring.py`，11 条，夹具=真 gt+真产物）：平面/立面各按**声明的契约**路由、
legacy 不被劫持、malformed 不抛异常（分类器纪律 #6 是分流入口）、e2e 落盘三件套、
平面径 110 targets（签名源绑定生效）、leftover 点名、分支不劫持（**变异验红**：分支条件改恒真 → 锁红，已当场演示并还原）。

---

## 三 跨两层立面必须判出分：锁在哪 + 变红证明（§2.2）

- **锁**：`tests/test_elevation_grade.py:47` `test_a_two_storey_facade_grades_whole`
  ——四张立面参数化：`targets["floor_ids"] == ["F1","F2"]`、
  `len(targets["openings"]) == {E:13,N:8,S:7,W:6}`、每层计数 > 0、
  `grade` 后 `denominator["floors"] == ["F1","F2"]` 且行数 = 全量。
  配套 `tests/test_elevation_grade.py:72` `test_north_storeys_both_carry_openings`
  钉死 North 的 4+4 层分布（哪一半消失都能点名）。
- **实现侧保证**：`elevation_grade.py:136` `elevation_targets` 按**视图**派生目标，
  代码里不存在任何按 `floor_id` 过滤洞口的路径；空分母 ⇒ `ElevationTargetsUnavailable`
  响亮（F-126 的形状，镜像到立面侧，`:88`）。
- **变红证明（当场做过）**：在 `elevation_targets` 里注入「只取第一层」过滤
  （F-89 的原形状）→ `[North_view-8]` 一条**立刻红**（`len(targets["openings"])` 从 8 掉到 4）；
  还原后全绿。变异原文与还原已记录在本轮会话命令历史。

---

## 四 J-2 两个分辨率：具名常量 × 声明点 × 消费 × 锁（§2.3）

`src/agent/judge/as_drawn/resolutions.py`：

| 侧 | 具名常量（默认+文档锚） | 声明点（判分读它，⛔ 不写死数字） | 消费 |
|---|---|---|---|
| gt | `GT_RESOLUTION_M = 0.001`（`:62`） | gt 自己的 `generator.tolerances.dxf_axis_alignment_tolerance_m`（`read_gt_resolution`，`:105`）；**缺席/非正 ⇒ `ResolutionDeclarationMissing` 响亮**，⛔ 不静默兜底 | 答案坐标 snap 到 gt 网格；进量化带 |
| pipeline 出口 | `PIPELINE_OUTPUT_RESOLUTION_M = 0.010`（`:66`） | 产物自身 `resolution_m` 字段（`read_product_resolution`，`:130`）；v0 产物无此字段 ⇒ 常量兜底且 `declared:false` 如实标注 | 产品坐标 snap 到产品网格；进量化带 |
| 两端 | ——（⛔ 故意不相等，有锁防「统一」） | —— | `snap_to_resolution`（`:152`）+ `quantization_band_m = 0.5·gt + 0.5·prod`（`:165`）；**语义容差 < 量化带 ⇒ `ToleranceBelowQuantizationBand` 响亮拒绝**（`elevation_grade.py:102`）——声明粗到判不了的产物，判分拒绝而非放水 |

**「换一个声明分辨率，判分跟着变」的实测**（`tests/test_elevation_grade.py:190` 等）：

1. 产物声明 `resolution_m: 0.6` ⇒ 量化带 0.3005 m **超过** along 语义带 0.30 m ⇒ 同一份
   East 产物从「判出分」变成 `ToleranceBelowQuantizationBand` **响亮拒绝**（band 值随声明变）。
2. 产物声明 `resolution_m: 0.35`（带 0.1755 < 0.20，可判）⇒ 产品坐标被真实 snap 到 0.35 网格，
   报告里的洞口中心误差**实测发生变化**（`fine_errs != coarse_errs`，⛔ 不是报告行装饰）。
3. gt 声明 2 mm ⇒ `params.gt_resolution_m == 0.002`、量化带 0.006（跟着 gt 声明变）。
4. 两条路径都变异验红过：把 `read_product_resolution` 改成忽略声明字段 → (1)(2) 的锁当场红，还原后绿。

平面侧消费（不重写判分器）：`flow_wiring.py:189-191` 把量化带作 `reading_grade.grade` 的
`pos_tol` 下界（`max(POS_TOL_M, band)`；默认 0.0055 ≪ 0.08，行为不变、params 可见）。

J-1（容差带 ⛔ 逐位相等）：平面侧本就 `POS_TOL_M=0.08`；立面侧洞口匹配 = 双轴中心差 ≤ 带宽 +
尺寸差 ≤ 带宽（`ALONG_TOL_M=0.30 / Z_TOL_M=0.20 / SIZE_TOL_M=0.30`，`elevation_grade.py:78-80`），
锁 = 四张立面诚实产物（实测偏差 2–23 mm）判 85%+（`tests/test_elevation_grade.py:91`）。

---

## 五 判分读数（真实产物 × 真实 gt，2026-09-06 实测）

| 视图 | 轴向假设 | 洞口 found / placed+sized | 多画 | 结构线 | 身份 |
|---|---|---|---|---|---|
| East_view（13） | identity | 100% / 100% | 0 | 100%（分段线只入账不扣分） | null（产品未声明，J-5） |
| North_view（8，F1 4 + F2 4） | mirror | 100% / 100% | 0 | 100% | null |
| South_view（7） | identity | 100% / 100% | 0 | 100% | null |
| West_view（6） | mirror | 100% / 100% | 0 | 100% | null |
| 平面 plan-F1（110 targets） | —— | C1_C2 100% / C2 覆盖 99.2% | 0.722 m（0.3%） | —— | C5 100% |

（以上为 prototype 诚实产物；判分器对「缺一个洞口」「捏造一个洞口」「整体平移 0.5 m」
分别在锁里验出 NOT_FOUND / E2 计费 / 不被翻轴洗白。）

---

## 六 全量跑测与逐位闭合

```sh
cd /tmp/j_grade_glm && \
python -c "import src.agent.judge.as_drawn.reading_grade as g; print(g.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
# /tmp/j_grade_glm/src/agent/judge/as_drawn/reading_grade.py   ← 哨兵：落在本 worktree
3954 passed, 2 skipped, 13 xfailed, 211 warnings in 476.17s (0:07:56)   ← 汇总行原文
```

**逐位闭合（自己数）**：

| 项 | 数 | 出处 |
|---|---|---|
| 派工单基线 | 3907 passed / 2 skipped / 13 xfailed | 派工单 §五（主线权威全量 `363844b3` 基点同源） |
| 本单新增 | **47** | 独立 `--collect-only` 四个新测试文件实测（`tests/test_j2_resolutions.py` 11 + `tests/test_elevation_grade.py` 21 + `tests/test_j_grade_wiring.py` 11 + `tests/test_render_elevation_grade.py` 4） |
| 预测 | 3907+47 = **3954** | —— |
| 实测 | **3954** passed | 汇总行原文，与预测**逐位吻合** |
| 总数核对 | 3954+2+13 = **3969** = 独立 `--collect-only` 全仓实测 3969 | **差额 0** |

跑测全程 `git status` 干净（仅未提交的交件本文件）、HEAD 未变；`-n 6`（派工单纪律）；
跑测期间未动树、未启动席位。

---

## 七 最薄弱一处（⛔ 不写「无」）

**平面产物 v2 与判分链的「生产格式」断点还在 E-a 手里**：本单接线吃的是 prototype 产物
（`as_drawn_plan_v2` / `as_drawn_elevation_v0`），而 E-a 线（A-6 吃生产格式）尚未落地——
今天 `flow --to 0_reading` 跑一个**新** run 时，`0_reading/` 里的产物仍是 legacy 视图，
新判分分支**零流量**（接线是保险丝，不是已通车的路，同 A-6 删句三条的现状）。
具体地：`grade_as_drawn_attempt` 的平面径依赖产物契约 `as_drawn_plan`，而该契约今天的
产出方仍是 08-23 prototype（`vector_contract.py` 头部注释自陈的同一事实）。
第二个薄弱点：立面 along 轴向靠**两假设探测**而非声明件（§1.3）——探测 margin≥2 在四张
真实立面上工作，但一份「恰好一半洞口对得上」的产物会落在 ambiguous 分支按 identity 判低分
（诚实但低）；根因（orientation binding）在 B4/E-a 线。

---

## 八 本单不做（登记，另开单）

- J-5 语义升格为正式答案字段并计分（配对/门窗身份/墨族角色/「我认不出来」声明本身）——产物侧
  `door_window_classified:false` 的诚实空档已在判分里记 `null`+理由，升格需先冻结字段语义。
- F-98 判分对浮点末位敏感——观察项（本单量化带 + snap 已把末位敏感吸收在带内）。
- gt 任何改动（gt 铁律）——本单对 `gt/**` **零写入**（`git diff` 可核）。
