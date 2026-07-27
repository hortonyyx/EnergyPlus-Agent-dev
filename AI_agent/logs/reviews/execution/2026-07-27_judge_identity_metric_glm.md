# 执行日志 · 判卷器「数值身份 + 计分度量」施工批（2026-07-27）

> 施工 = GLM-5.2 / 对抗审 = sol / 轻门 = 主控 Opus 5。
> 基线 = `proposals/judge_identity_and_metric_plan.md`。派工单 = `reviews/request/2026-07-27_judge_identity_metric_construction_dispatch.md`。

---

## 0. 开工 / 收工 git status

**开工**（HEAD `8d79215`）：
```
?? AI_agent/logs/reviews/request/2026-07-27_judge_identity_metric_construction_dispatch.md
```

**收工**（本批施工后）：
```
 M src/agent/correction/cell_geometry.py
 M src/agent/judge/score_policy.py
 M src/agent/judge/score_schema.py
 M src/agent/judge/score_service.py
 M src/agent/judge/segment_score.py
 M tests/test_c2_b4b_contract.py
 M tests/test_c2_b4b_phase_b.py
 M tests/test_c2_b4b_phase_d.py
?? AI_agent/logs/reviews/request/2026-07-27_judge_identity_metric_construction_dispatch.md   (主控上一轮落, 非本批)
?? src/agent/correction/orthogonality.py                                                       (W5 新增共享模块)
?? tests/test_judge_identity_metric.py                                                          (W1-W5+B 验收锁)
?? AI_agent/logs/reviews/execution/2026-07-27_judge_identity_metric_glm.md                      (本日志)
```

> 纪律 §1.2「逐字相等」的精神 = 除本单列明文件外不新增。本批新增 `orthogonality.py`（W5 共享模块，R-4 必需）+ `test_judge_identity_metric.py`（验收锁，§5 必需）+ 本日志，均为派工单 W4/W5/§5 直接要求的产物。`case_tests/test_baseline/gt/` 逐字节未动（A5：`git diff case_tests/test_baseline/gt/` 为空）。`AI_agent/CLAUDE.md` 未碰。

---

## 1. W1 阈值实测数据（R-2 核心，禁先定数字后补论证）

**方法**：`/tmp/probe_drift.py` + `/tmp/probe_multistep.py`（只读探针，不落仓库）。

### 1.1 已签字 sm24 gt 内部漂移
- 50 个顶点（footprint + zones + boundary_segments + openings），去重后 x 轴 4 个值、y 轴 8 个值。
- **接近但不等的相邻对（diff < 1e-6）计数 = 0**。结论：已签字 gt 内部**零漂移**——同一意图坐标在 gt 内部用的是同一个 binary64 值。漂移只来自跨代码路径（gt 提取 vs correction 算术）或人为构造（L-a 把一侧改写）。

### 1.2 三个活体反例的精确漂移（float.hex）
| 反例 | 值 A | 值 B | diff | hex |
|---|---|---|---|---|
| sm24 seam (G-c.1) | 8.059999999999999 | 8.06 | 1.776357e-15 | 0x1.01eb851eb851ep+3 vs 0x1.01eb851eb851fp+3 |
| typed correction (G-c.2) | 0.1+0.2 | 0.3 | 5.551115e-17 | 0x1.3333333333334p-2 vs 0x1.3333333333333p-2 |
| 1e-9 缺口（须红） | 5.0 | 5.0+1e-9 | 1.000000e-09 | 0x1.4000000000000p+2 vs 0x1.4000000112e0cp+2 |

### 1.3 binary64 ulp 量级（代表性）
ulp(1.0)=2.22e-16 / ulp(5.0)=8.88e-16 / ulp(8.0)=ulp(13.0)=1.78e-15 / ulp(16.0)=ulp(20.0)=3.55e-15。
**20 m 量级单 ulp 上界 = 3.552714e-15**。

### 1.4 多步算术漂移（尺寸链 a+b+c vs 字面量）
10 个构造用例（含 `13.0-4.94`、`8.06-3.0`、`sum([0.1]*10)` 等）max diff = **1.776357e-15**（= 1 ulp at 8/13）。即若干次算术后漂移仍在单 ulp 量级，未发散。

### 1.5 阈值定案（实测推导）+ 两侧余量

| 阈值 | 值 | 合并侧余量 | 分裂侧余量 |
|---|---|---|---|
| `_COORDINATE_MERGE_THRESHOLD` | **1e-12** | 281× 于 20 m 单 ulp（3.55e-15）；563× 于实测最大漂移（1.78e-15） | — |
| `_COORDINATE_SPLIT_THRESHOLD` | **1e-11** | — | 100× 于 1e-9 必红缺口 |
| `_COORDINATE_DIAMETER_THRESHOLD` | **1e-11** | 链式桥接守卫；合法簇（ulp 级）1000×+ 余量 | — |

- 护带 = 开区间 (1e-12, 1e-11)，宽 9e-12：落此区间的距离 = **响亮拒绝**（identity_guard_band_ambiguity），既非合并也非分裂。
- **为何不抄参考值**：Claude 侧 split=1e-10 对 1e-9 仅 10×（偏薄）；GPT 侧 1e-12 无护带（单点边界零测度，漂移略超即静默分裂=假红换位复发）。本批 split=1e-11 厚 10× 且有护带。
- **为何落模块常量不进 judge_score.yaml**：身份层阈值是表示噪声吸收（皮米级），与判卷容差（分米级，用户可调）是两个层次（基线 C-1′ 表格）。混进判卷配置会模糊分层 + 改 config hash（G-b）。落 `segment_score.py` 模块常量 ⇒ config 不变 ⇒ **G-b hash 不撞**（见 §3）。

### 1.6 双向证明（两条锁）
- 「合法漂移必合并」：`test_a1_identity_merges_one_ulp_binary_spelling`（8.059999999999999↔8.06，1.78e-15 < merge → 同原子）+ `test_a1_identity_merges_fp_sum_spelling`（0.1+0.2↔0.3）+ `test_a1_quantum_boundary_pair_not_false_red`（r2 量子格边界对，nextafter 跨格 → 聚类合并）。
- 「1e-9 缺口必红」：`test_a2_identity_splits_1e9_gap`（1e-9 > split → 两原子）+ `test_a2_product_side_1e9_gap_still_red_code_unchanged`（产品侧缺口 error code 逐字 `score_product_identity_invalid / invalid_interior_edge_pair`）。

---

## 2. 施工改动清单（W1–W6 + B + G-a/G-b）

### 2.1 生产码
- `src/agent/judge/segment_score.py`（+411/-144 行，核心）：
  - **W1 身份层**：删 `_COORDINATE_QUANTUM`/`_canonical_coord`/`_canonical_point`（定格量化），新增 `_AxisIdentity` + `_cluster_axis`（单链接聚类 + 护带 + 直径守卫）+ `_build_floor_identity` + `_identify_point`。池作用域 = (side, floor, axis)（C-1′：GT/产品池分离）。错误分类学：`identity_non_finite_value` / `identity_guard_band_ambiguity` / `identity_chain_bridge_over_diameter` / `identity_merge_edge_collapse`，context 含 hex binary64。
  - **W2**：`_points`/`_edges` 改接收 (x_id, y_id) + identity_code；比较仍 `==`/`<=` 精确，但跑在聚类代表值上；加 C-1″④ 边坍缩检查。顺手修既有缺陷：原 `_points` 硬编码 `score_gt_identity_invalid`，correction 侧误用 gt code —— 现按侧传入正确 code。
  - **W3**：新增 `match_plan_segments`（联合切点原子化），`assign_plan_segments`/`score_plan_segments` 改为它的兼容包装。`score_match_ambiguous` 在平面墙通路结构性不可达（覆盖是集合运算无并列）。
  - `SegmentScore` 加 `eligible_units: float`（W4 长度分母）。
- `src/agent/judge/score_policy.py`：
  - **W4**：新增 `_segment_criterion`（长度分母 criterion，显式 passing/failing status bucket）。`c2_v3_score_policy` 的 `walls_complete` 拆三分：`walls_complete`（漏画，分母=答案长度，duplicate 算 target-covered passing）/ `no_extra_walls`（多画）/ `no_duplicate_wall_strokes`（重笔）。守恒 `passing+failing==denominator` 保持。
- `src/agent/judge/score_service.py`：
  - **§5-B**：`product_to_gt` 改用 `match_plan_segments` 的 `observation_to_targets`（多对多结果）重填，取代一对一 `segment_assignment.matched` 推导。抽 `_resolve_facade_product_to_gt` helper（facade 映射 candidates==1 保守，多段跨立面不映射 → 窗 fail-closed，绝不"取第一个"）。
- `src/agent/judge/score_schema.py`：**G-a** `SEGMENT_SCORER_HELPER_VERSION` + `HelperIdentityV8.segment_scorer` Literal 升 `b4b_segment_score_v1` → `v2`（判卷逻辑变了换身份；旧 v1 sidecar 缓存失效是要的效果）。
- `src/agent/correction/orthogonality.py`（新增，W5）：共享正交判据模块（`ORTHOGONALITY_EPSILON=1e-9` + `classify_edge_orthogonality` + `edge_is_axis_aligned`），零 judge import（不变量 #4）。文档化「生产判合法 / 判卷判能不能量（NA 不 broken）」分工。
- `src/agent/correction/cell_geometry.py`：**W5** `_EPS` 改 import 自共享模块（值不变 1e-9，仅口径统一）。

### 2.2 测试
- `tests/test_judge_identity_metric.py`（新增，21 锁）：A1-A4 / A8 / A9 / W3 不可达 / W5 / B 出口1+2。
- `tests/test_c2_b4b_phase_b.py`：2 锁改以匹配 W3 新语义（`exact_tie` → `duplicate_coverage_routes_to_duplicate_not_ambiguous`；`segment_states` fixture 改 offset 触发 within，长度断言改 eligible_units）。
- `tests/test_c2_b4b_contract.py` / `tests/test_c2_b4b_phase_d.py`：G-a v2 字面量同步。

---

## 3. 开工门 G-a / G-b 处置

- **G-a（升 v2）**：5 处同步（`score_schema.py` 常量 + Literal、`score_service.py`、2 测试）。旧值不保留兼容分支。`test_c2_b4b_contract.py` / `test_c2_b4b_phase_d.py` 构造的 HelperIdentityV8 同步 v2。**既有 v1 sidecar 缓存失效**（load_cached_score 因 segment_scorer 不匹配返回 None）—— 这是基线 C-4「需要失效的只是派生件」的效果，非回归。
- **G-b（config hash）**：**不撞**。三个身份阈值落 `segment_score.py` 模块常量（不进 `judge_score.yaml`），`JudgeScoreConfigV1` 字段不变 ⇒ `judge_score_config_sha256` 仍 `ac2c1470…`，`test_config_hash_relationships_and_a0_registration` 绿、`A0_contract.md` 内嵌 hash 不需改。判断依据：身份层阈值（皮米级表示噪声）与判卷容差（分米级用户可调尺）是两个层次（C-1′），混进配置会模糊分层。⚠️ 不混淆：`judge_score.yaml` 的 `opening_assignment_tie_epsilon: 1e-9` 是匹配打分并列判据，与本批身份层 1e-9（拓扑缺口必红）是两个不同层，未合并未互引。

---

## 4. W6 派生件失效登记（本批只登记/失效，不删源；R-6 view_bindings.json 不碰）

升 `segment_scorer v1→v2`（G-a）使评分身份摘要变更，下列派生件**按设计失效**（基线 C-4）：
1. 旧 `score_vs_gt` sidecar（segment_scorer=v1）：`load_cached_score` 因 helper identity 不匹配返回 None，下次 run 重算。**这是要的效果，非回归**。
2. 旧 grade PNG（随 sidecar 失效，grade_png_sha256 不匹配）。
3. 旧 identity 合同下的阶段缓存（v1 helper identity）。
4. 挂起 `run_2026-07-27_haiku_e2e/`：**校正接受点之后的评分派生件**需失效重算；接受点之前的不动（基线 C-4）。

**R-6 `case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json`**：未入版本控制、在受保护 gt 目录内、不在 07-26 签名清单。**本批施工方不碰**（纪律 §1.1）。主控收工时 `git add`；清单口径归下一批「gt 标准产物清单」。

---

## 5. neuter 自查表（§1.6 / A11：每条锁自带 neuter，共用守卫归并披露）

neuter 在 /tmp 副本驱动（`cp` 备份 → 改 src → 跑 `test_judge_identity_metric.py` → 恢复），每次恢复后 `grep NEUTER` 校验 **0 残留**（工作树不留 neuter 状态，纪律 §7）。

| neuter | 摘掉（文件:行） | 变红测试 | 绑定守卫 |
|---|---|---|---|
| **A** | `_cluster_axis` 合并分支 `rep[value]=cur_min` → `=value`（segment_score.py:90） | `test_a1_identity_merges_one_ulp_binary_spelling` / `test_a1_identity_merges_fp_sum_spelling` / `test_a1_quantum_boundary_pair_not_false_red` / `test_a9_identity_merge_edge_collapse_rejects` | _cluster_axis 合并逻辑 |
| **B** | `_cluster_axis` 护带 `raise` → 静默分裂（segment_score.py:96-101） | `test_a3_guard_band_is_loud_reject_with_hex_context` | _cluster_axis 护带 |
| **C** | `_cluster_axis` 直径 `raise` → `pass`（segment_score.py:105-110） | `test_a9_chain_bridge_over_diameter_rejects` | _cluster_axis 直径 |
| **D** | `_segment_criterion` `units()` → `1.0`（界面条数非长度）（score_policy.py） | `test_a4_q3_full_wall_miss...` / `..._split_differently...` / `..._half_wall...` / `test_a4_failing_equals_wall_length...` / `test_w4_extra_and_duplicate_walls...` | 长度分母 |
| **E** | `match_plan_segments` → `return (), {}`（segment_score.py 匹配层） | `test_a4_q3_*`（×4）/ `test_w3_score_match_ambiguous_unreachable...` / `test_b_observation_map_records_multi_cover_per_key` / `test_w4_extra_and_duplicate_walls...` | 联合切点 |

**共用守卫归并披露**（r2 教训：不许把共用一个守卫的多条锁记成多条独立承重锁）：
- **`_cluster_axis`** 是身份层**唯一**守卫，A1/A2/A3/A9 全依赖它。`test_a2_identity_splits_1e9_gap` / `test_a2_product_side_1e9_gap...` / `test_a9_non_finite_value_rejects` 未单列 neuter 行——它们共用同一 `_cluster_axis` 函数（split 在 `elif` 分支、非有限在入口 `raise`），与 A/B/C 同一守卫，**归并披露**（摘掉 _cluster_axis 整体即全部红）。
- **`match_plan_segments`** 是匹配层**唯一**守卫，A4/W3/B(observation_map) 共用（E 一并变红）。
- **`_segment_criterion` 长度** 与 match 的 `eligible_units` 共同支撑 W4 —— D 和 E 都让 A4/W4 红，因 A4 同时绑 match 产出与长度聚合两者。
- `test_a4_q3_*` 的 4 锁共用 `_wall_criterion` → `c2_v3_score_policy` → `_segment_criterion` 同一通路（D/E 归并）。

**非行级守卫锁（诚实标注性质，非 false-lock）**：
- `test_a8_answer_denominator_independent_of_product`：架构锁——GT 池与产品池分离（C-1'）由 `extract_gt_plan_segments` **函数签名不接产品**保证。neuter 方式是破坏签名（让 extract 接产品），不属于行级摘除；摘 match（E）不触发它是**符合预期**的（match 摘掉不破坏池分离，A8 仍绿正确）。它防御的是"未来有人让 GT 池受产品影响"。
- `test_b_facade_multi_span_straddle_fails_closed_not_first`：绑 `_resolve_facade_product_to_gt` 的 `candidates==1` 逻辑（score_service.py），与 interior match 不同通路，未单列 neuter（同 score_service 守卫）。
- W5 三锁（`test_w5_*`）：绑 `orthogonality.py`（AST 零 judge import + `classify_edge_orthogonality` 三类 + `cell_geometry._EPS` 来源）。

**结论**：21 条锁全部经 neuter 验证真绑守卫，零 false-lock；共用守卫已归并披露。

---

## 6. 全仓测试输出

基线 **1685 绿 + 10 xfail**。本批交付全仓（默认并行 `-n auto`，253.25s）：

```
1706 passed, 10 xfailed, 150 warnings in 253.25s (0:04:13)
```

- **1706 passed** = 基线 1685 + 本批新增 21 锁（`test_judge_identity_metric.py` 21 测）。phase_b 2 锁为适配 W3 新语义改写（非新增非删除，计数不变）。
- **10 xfailed** = 基线不变。
- **0 failed / 0 regression**。

首轮全仓曾出 1 回归（`test_c5_production_correction_and_geometry_sources_import_no_judge`：W5 新建 `orthogonality.py` docstring 含 ``src.agent.judge`` 说明文字，被 correction 包的字面扫描命中）—— 已修（docstring 改 ``src/agent/judge`` 路径形式，不匹配点号字面），重跑全仓 1706 绿零回归。`case_tests/test_baseline/gt/` 全程零 diff（A5）。

---

## 7. §5-B 简报单列（出口3）

`score_service.py` 的 `product_to_gt` 原由 `segment_assignment.matched`（一对一）推导，**同时喂墙计分与窗宿主解析两个语义不等价的下游**。W3 摘掉一对一指派后，一个产品段可覆盖多个答案段：

- **墙计分**（walls_complete/no_extra/no_duplicate）走 `segment_rows`（长度分母，W4），**不走 product_to_gt**。
- **窗宿主解析 + 开窗匹配**走 `product_to_gt`，按 `facade_segment_id` 查（产品外墙段）。

故「产品长墙覆盖多个 GT 内墙」**不影响窗**（窗在外墙 facade 段，不在 interior）。改法：
1. `product_to_gt` 用 `match_plan_segments` 返回的 `observation_to_targets`（多对多结果）重填 —— 一个产品段覆盖多个 GT 段时，映射记录为 `obs→targets[0]`（sorted first，确定性，不依赖输入顺序）。该条目是 interior 段，**不携带窗**，故选择仅审计用途。
2. facade 段映射抽 `_resolve_facade_product_to_gt`：**candidates==1 才映射**（唯一包含），跨多 GT facade（candidates>1）**不映射** → 窗 fail-closed（unmatched），绝不"取第一个"静默绑错墙。
3. 三条出口：① `test_b_observation_map_records_multi_cover_per_key`（逐键契约锁：obs→("t1","t2") 多覆盖逐键）；② `test_b_facade_multi_span_straddle_fails_closed_not_first`（多段覆盖窗夹具：跨立面不映射、单包含正常映射）；③ 本简报。

语义正确性根因：判卷器对 interior 多段覆盖用集合运算（W3，NA 式），对 facade 跨立面用 fail-closed（不 broken）—— 兑现 R-4「判卷只许说 unsupported，不许说 broken」。
