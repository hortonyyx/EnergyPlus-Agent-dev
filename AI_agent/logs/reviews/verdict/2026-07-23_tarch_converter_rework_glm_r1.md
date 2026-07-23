# 天正 DXF → GT v3 转换器返工 GLM 对抗审判裁决（r1）

**日期**：2026-07-23  
**审判方**：GLM-5.2（验证性审阅）  
**被审施工方**：terra  
**核验对象**：`src/agent/judge/tarch_normalize.py`、`src/agent/judge/tarch_converter_schema.py`、`tests/test_tarch_converter_p{0,1,2}_*.py`、`tests/test_tarch_converter_gate_mutations.py`  
**BASE**：`0023a88` ／ **HEAD**：`a94d82a`（送审提交一致，工作树干净）  
**执行文档**：`AI_agent/logs/reviews/request/2026-07-23_tarch_converter_rework_review_checklist.md`（逐条照做）

---

## 0. 最终裁决：**APPROVE-WITH-CHANGES**

sol 原裁决的 **3 个 BLOCKER（假绿主保险失效）全部修复并经 GLM 独立活体验真**：

- **B-01 G8 假绿** → 改为只消费持久化 `p1/p2+basis+thickness` 重算（G8-01 trap 探针：挖空 `offset_native/nx/ny` 后 WKB 字节相同、面积差 0、sd 差 0；basis 翻转 sd=0.4224、厚度变异 sd=0.2112 均变红）。
- **B-02 三承重件摆设** → 近阈值进 G6 承重（`human_confirmation_required`，未签字 G10=candidate 红、报告 BLOCKED）；G10 三 hash 绑定（source/request/overlay 各篡改 → hash_mismatch）；PASS 强制十门全绿（schema + 生产双验证）。
- **B-03 hash 零校验** → `ezdxf.readfile` 前核 source SHA / request 自哈希 / view-floor 归属；全零/篡改均前置 BLOCK、不写几何。

转换器现已 **fail-closed**：经全面对抗验证，**不存在任何假绿 PASS 路径**。sm24 端到端独立重算 8 区 / symdiff 1.46e-13 / overlap 0 / G8 8.27e-13 / 合成 ack → 十门全绿 PASS / v3 1floor8zones / 确定性 384 句柄 100% 保留。全仓 **1537 passed, 10 xfailed, 0 failed**。

**残留（非假绿、不阻断 sm24 收官，须跟进批次清账）**：

| 级别 | 项 | 性质 |
|---|---|---|
| MAJOR | **HC-03** LINE 端点反转令 G4 gap 计数翻转（1→2/1→4，G4 布尔翻转） | **假红风险**（拒合法建筑），非假绿；sm24 方向一致不受影响；M-07-B 未修到根因 |
| MAJOR(轻) | **HC-02** `build_p1_report` 仍 4×`/ 1000.0` 硬编码 mm→m | 仅影响 P1 wall band 报告（native≠mm 时偏 1000×）；zone 几何（v3 输出）走 `mpu` 正确 |
| MINOR | **TE-01** 六类厚度证据仅 1/6（`wall_cap_or_opening_jamb`）有生产发射点，余 5 类仅 schema 枚举 | 当前 profile 走 cap/jamb（kind#2）有效；契约完整性缺口 |
| MINOR | **FC-03** opening 多解诊断仅 `candidate_count`，无 `solutions`/cap handles | 诊断精度（M-04-C 残留） |
| MINOR | **FC-04** far-side 多解未检测（`tarch_edge_far_side_ambiguous` 已移除，`_ray_thickness` 取 `ds[0]`） | 简单 profile 不触发 |
| MINOR | **H-03 case2** 重复 `plan_view` id 绑两 floor 不阻断（ownership 用 `any()` 不查唯一性） | 需畸形请求触发 |
| MINOR | **HC-01 G4** `_outer_skin_gap_count` 仍用字面 `>1.0`（native-unit 阈值） | native=m 时 gap 阈值偏 1000× |
| MINOR | **HC-04** 多层静默 `floors[0]`（无 2-floor 输出/无前置 BLOCK） | 当前单层 profile 范围；converter 按 plan_view 单调用设计 |
| MINOR | S7 junction 规则对"真实未证变厚被相同邻居夹住"会静默归并 | **G7/G8 兜底**（sd=0.4 BLOCK），无假绿，仅诊断精度降 |

**结论**：返工达成其核心目标（消除假绿主保险、fail-closed），可进入 sm24 真人签字收官流程。HC-03（LINE 反转）为最显著 MAJOR，建议近期批次优先闭合（一行修法：gap 过滤改 `min/max` 对称）；其余 MINOR 登记跟进。

---

## 1. 执行纪律与环境（C-00 / C-01）

### C-00 独立证据纪律 — **成立**
- 全部命令从仓库根 `/workspaces/EnergyPlus-Agent-dev` 执行。
- 环境：Python 3.12.13／shapely 2.1.2（GEOS 3.13.1）／ezdxf 1.4.4／pydantic 2.13.3／pytest 9.0.3。
- GLM 自建探针置于 `/tmp/glm_tarch_rework_probe/`（12 个脚本 + `glm_helpers.py`），**只导入生产 `tarch_normalize`/`tarch_converter_schema` + shapely/ezdxf/hashlib**，**未导入任何 terra 测试模块/fixture/expected/golden**。
- 场景 A/B、九门 neuter、hash 篡改、厚度无证据、S7 变厚、丁字/十字配对**全部由 GLM 按清单坐标独立重建几何**。

### C-01 变更范围 — **成立**
`git diff --name-only 0023a88..HEAD` 仅 6 文件：`tarch_converter_schema.py`、`tarch_normalize.py`、`tests/test_tarch_converter_p{0,2}_*.py`、`tests/test_tarch_converter_gate_mutations.py`、terra 简报。
**禁区零触碰**：gate①（`src/validator/checks/*`）、执行器（`src/agent/execution`、`pipeline.py`）、reading/correction、golden、`gt.json`、v3 提取器本体（`gt_extraction.py`/`gt_schema.py`/`gt_manifest.py`）均不在 diff。

---

## 2. G8 真独立与同墙一致性门（B-01 修复）— **全成立**

| 命题 | 实测 | 裁决 |
|---|---|---|
| **G8-01** 只消费 `p1/p2+basis+thickness` | 独立双房（6000×4000，240 外墙+240 内墙）。基线 recon 面积 5414400、sd=0。挖空 `offset_native=NaN`+`nx/ny=None` 后：**WKB 字节相同、面积差 0.0、sd 差 0.0、G8 仍 passed=True**。证明不读 `offset_native/nx/ny`。 | **成立** |
| **G8-02** basis 变异必红 | 内墙 `wall_axis→outer_skin`（`offset_native` 字节不变）：绿副本 G8=True，变异 G8=False sd=**0.4224** m² > topo(1e-6)。 | **成立** |
| **G8-03** thickness 变异必红 | 内墙厚度 240→360（`offset_native` 不变）：G8=False sd=**0.2112** m²。 | **成立** |
| **SW-01** 场景A同墙冲突 | 两 zone 接 x=4060，左 360/右 120。G7 symdiff=0/overlap=0（数值过），但同墙门 `passed=False`、conflict_count=1、发 `tarch_edge_thickness_inconsistent` BLOCK、G8 红。 | **成立** |
| **SW-02** 合法同墙不误红 | x=4000 两侧均 240/120：同墙门 True、配对恰 1、全一致。 | **成立** |
| **SW-03** basis 不一致必红 | 一侧改 `outer_skin`（同厚）：同墙门 False。 | **成立** |
| **SW-04** 丁字部分重叠 | 基线配对恰 `[0,4000]`/`[4000,10000]` 全绿；E2 厚度→120 仅 `[4000,10000]` 冲突红。 | **成立** |
| **SW-05** 十字部分重叠 | 基线配对恰 `[0,4000]`/`[6000,10000]` 全绿（中节点 y[4000,6000] 不串配）；E2→360 第二段冲突红。 | **成立** |

---

## 3. 近阈值 / G10 / PASS 全门（B-02 修复）— **全成立**

| 命题 | 实测 | 裁决 |
|---|---|---|
| **HR-01** 场景B面积补偿不静默PASS | sm24 无 ack：near_threshold 6 面（含面积+质心）；G6 `passed=False`+`human_confirmation_required=True`；独立 strip（1.5/2.5/6.0 m²）near=[1.5,2.5]、cavity 数=2（表面对）；G10 candidate；报告 BLOCKED。 | **成立** |
| **HR-02** candidate≠G10通过 | sm24 无 ack：G10 `passed=False`、`verification_status=candidate`、报告非 PASS。 | **成立** |
| **HR-03** 真人ack hash-bound | `HumanReviewAckV1` 含 reviewer/signed_at/decision + 3 hash。合法 ack→G10 True+PASS；source/request/overlay 各篡 1 hash→G10 `hash_mismatch`+BLOCKED；无 ack→candidate。**4 种篡改/缺 ack 全红**。 | **成立** |
| **HR-04** 任一门红则PASS失败 | schema：绿 PASS 报告逐次翻 G1..G10 一门→**10/10 ValidationError**；生产 sm24 无 ack BLOCKED。 | **成立** |
| **HR-05** overlay bundle-relative+hash | `overlay_asset=overlay_plan.svg`（相对、无 `/`、非 staging 绝对）；overlay 篡 1 byte→`hash_mismatch`。 | **成立** |

---

## 4. source/request/归属 hash gate（B-03 修复）— **H-01/02 成立，H-03 case2 MINOR**

| 命题 | 实测 | 裁决 |
|---|---|---|
| **H-01** source SHA 全零 | `source_dxf_sha256=64×'0'`（request 自哈希合法）：发 `tarch_input_source_hash_mismatch` BLOCK；`zones=[]`、`augmented/manifest/source_map=None`、work_dir 无 normalized.dxf/manifest/source_map；只写 `overlay_diagnostics.svg`；BLOCKED。hash 检查在 `ezdxf.readfile` 前。 | **成立** |
| **H-02** request 自哈希篡改 | 真 source SHA，request_sha 改 1 hex（66d4→f6d4）：同 H-01 BLOCK、不写几何。 | **成立** |
| **H-03** view/floor 归属 | case1 view→不存在 floor(F9)：BLOCK、`ownership_ok=False`。case3 入参 view 同 id 异 floor：BLOCK。**case2 重复 plan_view id 绑 F1/F2：不阻断**（ownership 用 `any()` 不查唯一性，`ownership_ok=None`）。 | **部分成立**(2/3；case2 重复 id 不查唯一性=MINOR) |

---

## 5. S7 事件坐标与厚度证据（M-01 修复）— **S7-01..04 全成立 + junction 安全**

| 命题 | 实测 | 裁决 |
|---|---|---|
| **S7-01** 单次变厚精确定位 | `[0,220]=300,[220,10000]=100`：恰 2 段，断点 **220.0**（≤tau_node 1mm），厚度 300/100，**无 477.5 漂移**。 | **成立** |
| **S7-02** 同边两次变化 | `[0,4000]=100,[4000,6000]=300,[6000,10000]=100`：恰 3 段，断点 4000/6000，序列 `[100,300,100]`。 | **成立** |
| **S7-03** 合法上限只作 sanity | `_thickness_profile`/`_ray_thickness` **签名无 range 参数**，函数体不引用 `wall_thickness_range`；两次调用字节相同。range 仅入 `_collect_walls` cap 过滤（S2）。 | **成立** |
| **S7-04** native m/mm 同变 | mm 原生（mpu=0.001）与 m 原生（mpu=1.0）：世界事件/厚度 profile **逐项相同** `[(0,4,0.1),(4,6,0.3),(6,10,0.1)]`。 | **成立** |

**S7 junction 规则特别复验（terra 自点名弱点）**：独立变厚几何四例——
- (a) 接头伪读 `[100,500,100]`+100 proof → 归并 500→100，**无 BLOCK**，单 100 边。
- (b) 同接头无 proof → `tarch_wall_thickness_unevidenced` BLOCK。
- (c) 真实 `100/300/100`+双 proof → 3 段保留（300 存活），G7/G8 绿。
- (d) 真实 `100/300/100`+仅 100 proof → **S7 静默归并 300→100（规则弱点：左右邻居都 100 相同 → donor 非 None → 不 BLOCK）**，但 **G7/G8 兜底**（sd=0.4 m²，发 `tarch_reconstruction_residual`+`tiling_residual` BLOCK）→ **无假绿**，仅诊断精度降为泛 residual。**安全**。

| 命题 | 实测 | 裁决 |
|---|---|---|
| **TE-01** 六类证据 | 生产 `source_kind=` 仅 `wall_cap_or_opening_jamb`（2 处：`build_p1_report`、`_thickness_evidence_for`）；其余 5 类（window_block_short_side/pub_dim_explicit/pub_hatch_outer_wall/reproduced_from_segment/source_hash_override）**仅 schema 枚举、无生产发射点**。当前 profile 走 kind#2（cap/jamb）有效。 | **部分成立**(1/6 落地；5 类契约缺口=MINOR) |
| **TE-02** 全证据空 fail-closed | 单 240 房 `wall_lines=[]`+无 bands：发 `tarch_wall_thickness_unevidenced` BLOCK；run_p2_conversion 走 blocked 分支不写 bundle；**但 G8 本身仍绿**（G8 是几何门、证据 fail-close 由 unevidenced BLOCK 承担）。安全属性（无 PASS/无持久化）成立。 | **成立**(fail-closed)；注：G8 几何门不查证据 |
| **TE-03** proof 闭环 | sm24：38 厚度边全有 proof、0 空；source_map 0 悬空 proof_id；report 边 0 空 proof。 | **成立** |

---

## 6. 九门 neuter（M-03 修复）— **全成立**

GLM 自建 10 个 canonical 红夹具（自有 DXF builder + 几何 + gate 提取，用生产 `_apply_test_neuter` seam）：

**基线**：G1..G10 每个目标门均 `passed=False`（全红）。
**逐门 neuter**（`TARCH_NEUTER_GATE=Gk`）：10/10 均**恰只翻转 Gk 自身夹具**，其余 9 个保持红——**零假锁**。

| neuter | 结果 | neuter | 结果 |
|---|---|---|---|
| G1(circle→G1) | match | G6(expected7→G6) | match |
| G2(quant conflict→G2) | match | G7(bloat→G7) | match |
| G3(unknown block→G3) | match | G8(flip basis→G8) | match |
| G4(clear openings→G4) | match | G9(DEADBE manifest→G9) | match |
| G5(free-end→G5) | match | G10(no ack→G10) | match |

逐门 G1..G10 命题（MUT-G1..G10）随基线+neuter 一并**全成立**。

---

## 7. 强制几何矩阵与 fail-closed（M-04/M-08）— **MX 成立，FC 部分**

**MX-01**：P2 测试枚举 5 类各正负（≥10）：L(`test_s7_single_room_outer_skin_expand`+/`test_l_corner_self_intersection_blocks_g8`−)、丁字(`test_s7_two_room_shared_wall_no_overlap`+/`test_same_wall_gate_splits_t_junction...`−)、十字(`test_s7_cross_junction_four_rooms_tile`+/`test_cross_junction_conflicting_segment...`−)、自由端(`test_free_end_non_zoning_with_proof_deferred` xfail+/`test_s4_free_end_blocks_before_s7`−)、厚度(`test_s7_event_profile_detects_two_changes`+/`test_s7_thickness_without_independent_proof...`−)。GLM 独立复现 SW-04/SW-05/S7-01/S7-02。文件头如实标注自由端 defer。— **成立**

| 命题 | 实测 | 裁决 |
|---|---|---|
| **FC-01** dialect 重叠不猜 | `_classify_block("X_DOOR", win=["X_DOOR"], door=["X_"])` → `None`（ambiguous），生产发 `tarch_opening_kind_ambiguous`。 | **成立** |
| **FC-02** 非法 polygon 不 buffer(0) | 源码 **0 处 `buffer(0)`**；bow-tie 腔体 → `tarch_edge_thickness_inconsistent` BLOCK、不修形。 | **成立** |
| **FC-03** opening 多解带 cap 冲突集 | 多解诊断 context 仅 `candidate_count`，**无 `solutions`/cap handles**（M-04-C 残留）。 | **不成立**(MINOR 诊断精度) |
| **FC-04** 空 provenance/far-side/厚度冲突 | 空→`tarch_wall_thickness_unevidenced`✓；厚度冲突→`tarch_edge_thickness_inconsistent`✓；**far-side 多解未检测**（码已移除，`_ray_thickness` 取 `ds[0]` 静默）。 | **部分成立**(far-side MINOR) |

---

## 8. 诊断 registry 与契约版本（M-05/M-06）— **D/V 全成立**

**D-01**：AST 枚举生产 `_diag(...)` 字面码 = **25**；`TARCH_DIAGNOSTIC_REGISTRY`=25；`DiagCode` Literal=25；**三集合差均为空**（registry−literal=∅、literal−registry=∅、registry−emitted=∅）。原 17 码：3 WIRED（`tarch_input_source_hash_mismatch`/`tarch_wall_thickness_unevidenced`/`tarch_edge_thickness_inconsistent`，均已活体触发）+ **14 REMOVED**（registry/literal/生产全消失）。— **成立**

**D-02**：保留的 3 码 100% 有活体负例（H-01/H-02、S7-junction(b)、SW-01/04/05 分别触发）；移除的 14 码无悬挂引用（REG-01 全绿佐证）。— **成立**

**V-01**：`CONTRACT_VERSION=Literal[2]`、`request_version=Literal[1,2]`；P0 `edf1477` v1 字段集（grep 确认无 `wall_thickness_range_m`/`min_room_area_m2`）；新字段只在 v2。— **成立**

**V-02**：`compute_request_sha256` 显式 v1/v2 分发（v1 pop 两字段）；当前 v1 hash == 手算旧式（omit 两字段）；v2 确定性；改 `min_room_area_m2` → v2 hash 变、v1 hash 不变。— **成立**

---

## 9. 去写死 / 方向 / 多层 / 安全写入 / overlay（M-07/N-01/N-02）— **SAFE/OV 成立，HC 部分**

| 命题 | 实测 | 裁决 |
|---|---|---|
| **HC-01** 去 native 常量 | `_ray_thickness`/`_thickness_profile` 无 `50000`/march step；0.4m 内墙（native m）→ `wall_axis`（ext=False，用 `tols.node_join_native` 非硬编码 1.0）。**但 `_outer_skin_gap_count` 仍用字面 `>1.0`**（native=m 时 gap 阈值偏 1000×）。 | basis **成立**；G4 `>1.0` MINOR |
| **HC-02** /1000 由 mpu 取代 | `build_p1_report` 仍 **4×`/ 1000.0`**（wall band coord_m/span_m/value_m，假定 native=mm）；`build_p2_report` zone 边厚度用 `*mpu` 正确、walls 沿用 p1_report。 | **部分成立**(P1 wall 报告残留；zone 路径正确) |
| **HC-03** LINE 反转不变 | 直接打 `_outer_skin_gap_count`：forward gap=1，**reversed gap=2**（全建筑 1→4）；G4 布尔翻转。根因：过滤子句 `not (x1<=lo or x0>=hi)` **非 min/max 对称**（假设 x0<x1）。M-07-B 未修。 | **不成立**(MAJOR，假红风险) |
| **HC-04** 多层不静默 floors[0] | `_build_manifest` 用 `request.floors[0]`；2-floor 请求 manifest 只写首层、**无 2-floor 输出/无前置 BLOCK**。 | **不成立**(单层 profile 范围) |
| **SAFE-01** work_dir 受 guard | `assert_staging_work_dir(gt_sources/...)` → `tarch_staging_work_dir_invalid`（mkdir 前）；`run_p2_conversion` guard 在 mkdir 前。 | **成立**(N-01 修复) |
| **OV-01** BLOCK 生成诊断 overlay | free-end BLOCK：写 `overlay_diagnostics.svg`，含 `<circle>` marker + `tarch_` code 文本；报告 BLOCKED。 | **成立** |
| **OV-02** 凹区标签 representative_point | overlay 用 `z.polygon.representative_point()`（非 centroid）；C 形（质心在外、rep_point 在内）验证。 | **成立**(N-02 修复) |

---

## 10. gt 隔离 — **成立（ISO-01）**

`tests/test_gt_discipline.py` **11 passed**；`rg` 反向扫描 `pipeline.py`/`execution`/`correction`/`reading_score`/`correction_score`/`gt_extraction`/`validate` → **0 命中** tarch/Tianzheng/天正。converter 仅调既有 v3 preflight，无反向 import、无天正特例渗透。

---

## 11. sm24 真端到端与全仓回归 — **E2E 成立，REG 成立**

**E2E-01**（独立数值重算，合成 ack）：独立 source sha==声明；**zone=8**；独立 Shapely symdiff=**1.46e-13** ≤1e-9；pairwise overlap=**0.0**；独立 G8 residual=**8.27e-13** ≤topo；十门全绿（G10 signed+3 hash 全 True）；报告 **PASS**；v3 preflight ok、extract **1 floor/8 zones**；source_map zone_boundary 0 空 proof。— **成立**

**E2E-02**（确定性，两目录）：gates/evidence/zone 面积全同；原 source modelspace 句柄 **384/384 100% 保留**；34 生成实体全 mapped、**0 phantom**。— **成立**

> sm24 PASS 此处为**合成 ack** 演示（G10 机制验证，brief 授权）；仓库内 sm24 仍 candidate/BLOCKED（无真人签字）= 刻意真实状态。

**REG-01**：
- 定向集（p0/p1/p2/gate_mutations/gt_discipline）：**91 passed, 1 xfailed, 0 fail/error, EXIT 0**。
- 全仓 `pytest -q`：**1537 passed, 10 xfailed, 0 failed, EXIT 0**（459.75s）。
- 对比返工前 1508/9xfail：passed +29（新增 gate_mutations+p2 测试）；xfail 9→10，**+1 = `test_free_end_non_zoning_with_proof_deferred`（自由端 §2.6 主控裁定 defer，明确 `pytest.fail` 标记、S4 仍对一切 dangle fail-closed BLOCK——安全 fail-closed 非静默出错，brief 明确批准）**。— **成立**（xfail +1 为已披露 defer）

---

## 12. END-01 覆盖表

| id | 命令/探针 | 实测值 | 裁决 |
|---|---|---|---|
| G8-01 | trap(NaN offset/None nx,ny)→生产 G8 | WKB 相同/面积差 0/sd 差 0/仍 passed | 成立 |
| G8-02 | basis 翻转(保 offset)→生产 G8 | sd=0.4224>topo,passed=False | 成立 |
| G8-03 | 厚度 240→360(保 offset)→生产 G8 | sd=0.2112>topo,passed=False | 成立 |
| SW-01 | 场景A x=4060 360/120→生产门 | conflict=1,BLOCK inconsistent,G8红 | 成立 |
| SW-02 | 合法 x=4000 240/120 | 配对1,全一致 | 成立 |
| SW-03 | 一侧 basis→outer_skin | 同墙门 False | 成立 |
| SW-04 | 丁字 E0/E1/E2 | [0,4000]/[4000,10000];E2变异仅后段红 | 成立 |
| SW-05 | 十字 E0/E1/E2 | [0,4000]/[6000,10000];E2变异第二段红 | 成立 |
| HR-01 | sm24无ack+strip | near含面积质心,G6红human_conf,BLOCKED | 成立 |
| HR-02 | sm24无ack | G10 candidate,非PASS | 成立 |
| HR-03 | 5例ack | legal→PASS;3 hash篡+无ack全红hash_mismatch | 成立 |
| HR-04 | 翻G1..G10+生产 | 10/10 ValidationError;生产BLOCKED | 成立 |
| HR-05 | overlay字段+篡byte | 相对路径;篡→hash_mismatch | 成立 |
| H-01 | source_sha=0 | BLOCK,无几何产物 | 成立 |
| H-02 | request_sha改1hex | BLOCK,无几何 | 成立 |
| H-03 | 3归属case | case1/3 BLOCK;case2重复id不阻断 | 部分成立(MINOR) |
| S7-01 | [0,220]=300 | 2段,断点220,无477.5 | 成立 |
| S7-02 | 100/300/100 | 3段,断点4000/6000 | 成立 |
| S7-03 | range非参数 | profile无range,grep确认 | 成立 |
| S7-04 | mm vs m | 世界profile逐项相同 | 成立 |
| TE-01 | 6类grep | 仅kind#2生产;5类schema-only | 部分成立(MINOR) |
| TE-02 | wall_lines=[]+无bands | unevidenced BLOCK,无bundle;G8仍绿 | 成立(fail-closed) |
| TE-03 | sm24 proof闭环 | 38边全proof/0悬空/0空 | 成立 |
| MUT-G1..G10 | 10夹具+neuter | 基线全红;逐门一对一翻转 | 全成立 |
| MX-01 | 5类正负枚举+独立复现 | 10+测,SW-04/05/S7-01独立复现 | 成立 |
| FC-01 | X_DOOR双匹配 | None→ambiguous | 成立 |
| FC-02 | bow-tie+grep buffer | 0 buffer(0);BLOCK不修 | 成立 |
| FC-03 | 多解诊断 | 仅candidate_count无solutions | 不成立(MINOR) |
| FC-04 | 空/far-side/冲突 | 空+冲突BLOCK;far-side未检测 | 部分成立(MINOR) |
| D-01 | AST+registry | 25=25=25,差空;17码3WIRED+14REMOVED | 成立 |
| D-02 | 3保留码活体 | hash/unevidenced/inconsistent均触发 | 成立 |
| V-01 | 版本字段 | v1/v2分发,新字段仅v2 | 成立 |
| V-02 | 跨版本hash | v1==旧式;v2确定;改字段v2变v1不变 | 成立 |
| HC-01 | native常量+0.4m墙 | 无50000;0.4m→wall_axis;G4>1.0残留 | basis成立/G4 MINOR |
| HC-02 | /1000 grep | build_p1_report 4×/1000;zone用mpu | 部分成立 |
| HC-03 | LINE反转 | gap 1→2,G4翻转,filter非对称 | 不成立(MAJOR) |
| HC-04 | floors[0] | 静默首层,无BLOCK | 不成立(单层范围) |
| SAFE-01 | work_dir guard | 拒保护路径在mkdir前 | 成立 |
| OV-01 | BLOCK overlay | overlay_diagnostics.svg+marker+code | 成立 |
| OV-02 | rep_point | overlay用rep_point;C形验证 | 成立 |
| ISO-01 | gt_discipline+反向rg | 11 passed;0反向import | 成立 |
| E2E-01 | sm24独立重算 | 8区/symdiff1.46e-13/overlap0/G8 8.27e-13/PASS/v3 1f8z | 成立 |
| E2E-02 | 两目录确定性 | 全同;384/384句柄;0 phantom | 成立 |
| REG-01 | 定向+全仓 | 91p/1xf;1537p/10xf/0fail/EXIT0 | 成立 |

**覆盖率 100%**（清单全部 id 逐项有命令/探针/原始值/布尔判定）。

---

## 13. 给主控的建议

1. **可批准返工合入**（APPROVE-WITH-CHANGES）：3 个 BLOCKER 全修且独立验真，假绿主保险已消除，sm24 可进入真人签字收官。
2. **近期批次优先闭合 HC-03**（LINE 反转 → G4 翻转）：一行修法，gap 过滤改 `min(x0,x1)`/`max(x0,x1)` 对称（`not (max<=lo or min>=hi)`）。虽是假红非假绿、sm24 不受影响，但属真实正确性缺口。
3. **登记跟进 MINOR**：HC-02（`/1000` → `mpu`）、TE-01（补 5 类证据生产路径或缩窄契约）、FC-03（多解诊断带 `solutions`+cap handles）、FC-04/H-03（far-side 多解、重复 plan_view id 唯一性）、HC-01 G4 `>1.0`、HC-04（多层前置 BLOCK 或显式单层 profile 声明）。
4. **sm24 真人签字后**重生成并晋升 gt_sources bundle（当前仓库内 bundle 由旧缺陷转换器产出、返工前不可信——本次返工后机制已就绪）。
