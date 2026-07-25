# 2026-07-24 天正命名立面施工批 — Opus 升一档对抗审裁决书

审阅人：Opus 4.8（Claude 侧，独立上下文·活体探针·探索性对抗审）
施工方：terra（GPT 侧）— 谁写谁不批，跨家族交叉审
审阅对象：`89205fe`（7.24_TArchElevationConstruction）+ `7888ded`（7.24_TArchElevationOverlayPlanAndBorder），基线 `8b805e5`
合同：`AI_agent/proposals/tarch_elevation_spec.md`（1374 行·定稿）
只审不修：本轮零生产码永久改动（所有 neuter 探针跑完即 `git checkout` 还原，终态工作区干净、4 文件 NEUTER-PROBE 残留全 0）

---

## 0. 总裁决：APPROVE-WITH-CHANGES

- **命脉过关**：§9 必红夹具矩阵**全部真红、零 false-lock**。上一轮转换器返工死过的"九门 neuter 假锁"病**未复发**。我对 10 类关键变异各亲手 neuter 目标门逻辑、跑对应 §9 测试，全部由绿翻红，且是**该门在算**（passed=True 复现、无别处兜底、无 fixture 恰非法）。
- **信任边界正确**：converter 对 datum handle / 有向端点 / raster calibration **只校验不猜**（无最低线/窗台/框底 z 启发式、无 auto-mirror、无图像边缘猜校准）；"sign+endpoint+along-offset 三者同步一致重标"正确地**不**做机器红门，且逐 opening 审计表 + 标注 overlay 真实暴露该人信任残留。
- **提取正确**：我独立跑 sm24 全链，14 openings（11 窗 + 3 门）、窗 z 恰 {[1.0,2.8],[1.0,3.4]}、门 observed z=[0.2,2.6]、全有 host_zone、canonical reload 逐字节一致。
- **契约冻结 / scope / 零回归**：v3 新字段全进 canonical hash；render 核心投影零改；scorer/Va/Vg/v2 legacy 未动；全仓 **1556 passed, 10 xfailed**（与基线一致，零回归）。

**但有需修项（不阻断 merge，属跟进债）**：**1 个 spec [S] 强制门缺失（§6.5 配对一致性 postcheck）+ §11 对账 1 处 overclaim**（MAJOR）；**spec [S] 必红/e2e 矩阵 §9.2/§9.3/§6.6 未落 fixture**（MAJOR）。均**非 false-green / false-lock**——命脉门是真的、真在算，缺的是"另一半防线"与"负例/正例锁"。

- BLOCKER：0
- MAJOR：2
- MINOR：2
- NIT：2

---

## 1. 命脉专项：§9 必红矩阵 false-lock 活体验真（全通过）

方法：逐门亲手 neuter 生产码判定逻辑 → 跑对应 §9 测试 → 确认由绿翻红 → `git checkout` 还原。**must-red 测试不设 `TARCH_NEUTER_GATE`**（生产里那个 `_apply_test_neuter` seam 是纯 opt-in env-var 测试 seam，正常调用者不触发、非生产后门），故本套覆盖是真活体、非循环自证。绿基线：`test_tarch_elevation_must_red.py` 14 passed。

| # | 目标门 / 变异 | 我 neuter 了什么 | 结果 | 结论 |
|---|---|---|---|---|
| 1 | G1 datum 四类有向端点（sign / endpoint / offset / sign+offset） | `tarch_normalize.py:1653` 把 `endpoint_bad` 恒置 `False` | 4 个 G1 变异测试全 FAIL（G1 复现 passed=True，无兜底） | 真门 ✓ |
| 2 | G3 门 union 四坏形态（gap / overlap / T-shape / different-z） | `:1714` union 面积恒等检查改 `if False and …` | 4 个 union 测试全 FAIL（G3 passed=True） | 真门 ✓ |
| 3 | G3 block fingerprint drift | `:1667` 禁用 sha256 比较 | fingerprint drift 测试 FAIL | 真门 ✓ |
| 4 | G3 CIRCLE 11C 误作结构轮廓 | `:1672` 结构轮廓选取改为忽略 request 角色、按 LWPOLYLINE 选 → 变异变 benign | role-shape 测试 FAIL | request 穷尽角色图**真驱动**结构选取，11C 误标真被抓 ✓ |
| 5 | G9 kind mismatch | `gt_extraction.py:585` 把 `item.kind == opening.kind` 改恒真（等价撤销 kind 修） | kind 断言 FAIL（door-kind 证据仍匹配 window 候选，no_candidate 不触发） | kind 修真门 ✓ |
| 6 | G9 删 elevation evidence（`gt_opening_elevation_evidence_mismatch`） | `gt_schema.py:614` 该 completeness `_fail` 改 `pass` | missing-evidence 测试 FAIL | evidence 接线真达 completeness 门 ✓ |
| 7 | G10 raster lo/hi 对调 | `_validate_raster_intents` 整体 no-op | lo/hi swap 测试 FAIL | 真门（directed）✓ |
| 8 | G10 raster 水平镜像（图内） | 同上 no-op；再做定向子探针（只摘 elevation `residual_ok`） | no-op → FAIL；子探针 → **镜像测试靠 `residual_ok` 变红、非 directed lo/hi**（lo/hi swap 靠 directed） | 真门 ✓（机制描述见 NIT-1） |
| 9 | G10 plan footprint SW/SE 对调 | 整体 no-op | 测试 FAIL | 真门 ✓ |
| 10 | overlay raster SHA256 改 1 byte | `render_gt_overlay.py:277` 禁用 hash 比较 | hash-mismatch 测试 FAIL | 真门 ✓ |
| 11 | overlay 投影四角越界 | `_within` 越界 raise 改 `if False` | out-of-bounds 测试 FAIL | 真门 ✓ |

**结论：无任何假绿 / false-lock。** terra 最后限时补的两格（门 union 四坏形态、raster 水平镜像）经重点核验均真红、真依赖目标门。门 union 四坏形态是 G3 union 面积恒等门（无容差 `!=`）owns；raster 镜像是 G10 `residual_ok` owns（不是 docstring 声称的 directed handedness，但仍是真 G10 计算，见 NIT-1）。

---

## 2. Findings

### MAJOR-1 —（spec §6.5 [S]）converter↔GT 配对一致性 postcheck 缺失 + §11 对账 overclaim

**事实**：spec §6.4/§6.5 是 [S] 强制项——完整 GT 产出后，必须按每个 `opening_elevation` source ref 的 generated handle 反查 evidence，再与 converter pairing ledger 比较（view/opening/kind 相同 + **z interval == converter 计算值** + 每 relevant pair 恰一组 refs），不一致 BLOCK（`tarch_elevation_pairing_drift`）。spec 明写此门的目的是"防止 converter 预链接变成无人消费的伪检查"。

**核验**：
- `_run_g9_v3_preflight`（`tarch_normalize.py:2039`）只跑 `inspect_extraction_inputs` + `extract_gt_v3`，且**丢弃 `extract_gt_v3` 返回值**（仅取副作用），**之后没有任何** `result.elevation_records` ledger ↔ GT `opening_elevation` refs 的比较。
- 全仓 grep：`tarch_elevation_pairing_drift` 的 emit 引用数 = **0**（死码）。
- 我 live 跑 sm24 后逐条比对：当前审计行 z 与 GT z **一致（0 不匹配）**——所以**不是活体 false-green**（两者同源于同一 manifest evidence handle + 等价 affine）。

**风险**：converter 审计行 z（用 request affine，`build_p2_report:2400`）与 GT z（用 manifest affine=request/mpu×mpu，`_elevation_geometry`）是**两条独立代码路径**，其相等**当前无任何门强制**。未来 units/wiring 漂移会让"人核审计表 z"与"权威 GT z"静默分叉，而 z 正是本批唯一交付物（窗高）。spec 的这道 [S] postcheck 就是为此设的防线。

**overclaim**：terra 简报 §11 row 10 写"GT refs 与 converter ledger 一致 | G9 / audit 实测通过"——但**无任何门比较二者**（审计行由 ledger 构建、无法自证与 GT 一致；G9 丢弃 GT）。此对账项无门支撑。

**出口**：实现 §6.5 postcheck 并接线 `tarch_elevation_pairing_drift`（补真门级必红 fixture）；或若确认延后，须把 §11 row 10 诚实改为"未实现、handle+kind 由构造保证、z 一致性未强制"。（注：handle + kind 链接由 manifest evidence 构造 + kind 修保证；缺的是 z 值/唯一性显式 postcheck。）

### MAJOR-2 —（spec [S]）必红/e2e 验收矩阵 §9.2 / §9.3 / §6.6 未落 fixture

**事实**：must-red 文件 8 个测试函数只覆盖 §9.4（along 四变异）+ 门 role/fingerprint/union + kind/missing-evidence + raster 三格。以下 [S] 矩阵**零 fixture**：
- **§9.3 z-datum 变异**（datum 换屋顶线 / z-axis 不符 / z-scale 0.001→1.0 / z-offset 0.2 / 两 datum 不同 offset / 窗跨楼层 / 窗 z>ceiling）——**这是本批核心安全门**（窗高全靠 datum）。
- **§9.2 frame/title 变异**（bbox 相同但 handle 指第二框 / 框内 0 或 2 标题 / alias map / 两 full North 覆盖同层 / entity 跨框边）。
- **§6.6 sm24 正向 e2e 断言**（14 openings / 11 窗 z ∈ {[1,2.8],[1,3.4]} / 3 门 observed z / 11C 排除 / 7 interior 排除 / canonical reload 逐字节）。

**核验**：
- must-red 中 title/z/datum 变异关键词命中 = 0。
- 唯一跑真 sm24 路径的 `test_sm24_v3_...overlays...` 只断言 overlay 渲染（4 白 envelope + view 列表），不校验开口数 / z 值 / 排除项。`test_tarch_converter_p1_geometry.py:197` 的 `exterior==14 and interior==7` 是 **plan 侧**计数，非立面 z。`test_gt_from_dxf.py:170` 的 14 是合成 fixture、非 sm24。
- **但相关门是真的、非死码**：`title_mismatch`/`datum_missing`/`datum_invalid`/`z_transform_mismatch` emit 引用数均 ≥1，且我审读 z_transform 门逻辑是**真跨源交叉检查**（DXF datum 线 z0 vs request floor z_floor + offset，非恒真自比），我 live 跑 sm24 时 happy-path 真经过这些门并给出正确 z、North/West/East 负 sign 立面 G1 全绿（§9.4 绿线满足）。

**结论**：非 false-green（门真在算、正向已 live 验证正确），缺的是**负例/正例回归锁**。z-datum（§9.3）尤应补——它是全批安全命门却唯独无 negative fixture。**出口**：补 §9.2/§9.3 必红 fixture + §6.6 sm24 正向 e2e 断言（晋升 sm24 anchor 时一并落，防未来算法漂移无人察觉）。

### MINOR-1 — 死登记诊断码（shipped-untested 登记面）

除 `tarch_elevation_pairing_drift`（见 MAJOR-1）外，另有 4 个 registry 码 emit 引用数 = 0：`tarch_elevation_opening_no_candidate` / `tarch_elevation_opening_assignment_ambiguous` / `tarch_elevation_opening_kind_mismatch`（G9）+ `tarch_interior_opening_elevation_not_applicable`（G4 INFO）。前三者与 §6.4 的"G9 extraction 错误经 `tarch_v3_precondition.context.v3_code` 原码上浮"设计**冗余**（失败仍 fail-closed，实测走 raw code `elevation_opening_no_candidate`——见命脉 #5/#6），属可辩护的登记冗余；后者 INFO（G4 exterior14/interior7 适用性对账）从未 emit。**出口**：接线为真 emit 或删冗余码 + 文档说明 G9 立面失败统一走 `tarch_v3_precondition`。

### MINOR-2 — G9 宽 except + 前置 `extract_gt_v3` 未包裹（fail-closed 安全但欠优雅）

- `_run_g9_v3_preflight` 末尾 `except Exception as exc: return False, str(exc)`——把任意异常（含潜在 coding bug 如 KeyError）转成 G9 BLOCK + 不透明 message。方向 fail-closed 安全（不产假绿），但会把真 bug 伪装成"合法 block"。
- `run_p2_conversion:2254` 的**前置** `extract_gt_v3`（为 elevation_records 取 plan_gt）**未包 try**：若某个过了 P2 plan 门却过不了 gt_extraction 的输入，会**崩溃**而非返回 blocked report（同一 extract_gt_v3 在 G9 又跑一次=双跑）。崩溃仍是 fail-closed（不产假绿），但欠优雅、无诊断产物。**出口**：窄化 except 到 `(ExtractionError, ValidationError)`；前置调用包 try 转 BLOCK 或复用 G9 结果避免双跑。

### NIT-1 — 水平镜像 must-red 测试机制描述与实际不符

`test_raster_horizontal_mirror_in_bounds_makes_g10_calibration_red` docstring 称"only the directed lo/hi controls expose the wrong handedness"。定向子探针证明：摘掉 elevation `residual_ok` 后**镜像测试转绿、lo/hi swap 测试仍红**——即镜像实际靠 `residual_ok`（镜像 affine 不再把 control 反投影到声明 source 点）owns，directed lo/hi 在镜像下仍 pass。二者都是真 G10 计算、覆盖不同失败面（residual vs 手性），只是镜像格的**声称机制**写错。**出口**：修正 docstring，或另补一个"镜像 + 同步镜像 source 点使 residual 仍成立、只 directed 手性能抓"的 fixture 以真覆盖 directed 手性面（lo/hi swap 已覆盖手性，故非硬缺）。

### NIT-2 — `_assign_elevation` kind 判定的 `item is None` 死分支

`gt_extraction.py:585` `(item is None or item.kind == opening.kind)`——real call path 里 evidence tuple 的 `item` 恒非 None（`evidence.append((item, …))`），故 `item is None` 是永假防御分支。无害（等价 `item.kind == opening.kind`），可留作未来防御或删。

---

## 3. 逐条审点结论

1. **信任边界正确性（§0.3/§2.5/§2.6/§2.8）**：PASS。z datum 经 request 声明的 datum handle + `floor.z_floor − z0×scale` 交叉核 request offset，**无最低线/窗台/框底启发式**；along 有向端点从 request 取、核 plan 投影；raster 只校 residual + directed control + 三点非共线，**无 auto-mirror、无图像边缘猜校准**。"三字段同步一致重标"正确**不**设机器红门，且逐 opening 审计表（`datum_entity_handle`/`datum_source_start/end_point`/`declared_world_along_lo_source_endpoint`/`mapped_endpoint_pair`）+ 标注 overlay 真实暴露该残留、未被冒充成机器真值门。
2. **render_gt_overlay.py 改动最小正确**：PASS（附一处披露）。`_pixel_for_world_elevation`/`_pixel_for_world_plan` 定义**逐字未改**（diff 中仅有对它们的**调用**、无 `def`、无 affine 系数改动）。授权的角点 min/max 排序（PIL 要 y1≥y0）+ envelope 外轮廓矩形均 draw-only、经 `_within` 越界保护。**披露**：`7888ded` 平面分支另有 zone 默认色 (150,150,150)→(0,200,255) + zone-id 文字标签两处 draw-only 添加，超出 dispatch 字面枚举的"line 323 + envelope"，但属 `7888ded` 授权的平面 overlay 交付、投影中性、plan 分支语义未改——在 scope 内，仅登记透明。
3. **scope 边界（§10）**：PASS。gt_extraction.py 仅改 kind 一行（属"kind 修"授权交付）；GT v3 wire / GroundTruthV3 opening wire / v2 legacy adapter / scorer·Va·Vg / render 核心投影**未动**。全仓零回归佐证 kind 修未破既有 v3 提取。
4. **契约冻结（§2.1/§2.4）**：PASS。`compute_request_sha256` 用整体 `model_dump(mode="json")`，typed v3 elevation/raster 子模型自动进 hash（must-red 的 `_rehash` 依赖此）；`compute_manifest_sha256` 的 canonical payload 含 views + raster_overlays（既有 wire 字段被填充）；`HumanReviewAckV1.review_index_sha256` 新增且 v3 G10 真比对（None→fail-closed）。无"加了字段不进 hash"。
5. **零回归**：PASS。独立干净全仓 `python -m pytest -q -p no:cacheprovider` = **1556 passed, 10 xfailed, 146 warnings（583s）**，与基线完全一致。（注：neuter 探针期间曾有一次后台全量跑与我的编辑相互污染，已 kill 并在所有探针还原、工作区确认干净后**重新干净全跑**，此 1556 即干净结果。）
6. **提取正确性 + fail-closed**：PASS。独立 live 跑 sm24：14 openings / 11 窗全有 z 且恰 {[1.0,2.8],[1.0,3.4]} / 3 门 observed z=[0.2,2.6] / 全有 host_zone / canonical reload 逐字节一致 / G1–G5,G7–G9 全绿、G6+G10 False（待人签=candidate 正确态）。fail-closed 门（no_candidate / evidence_mismatch）经命脉 #5/#6 neuter 验真。
7. **诚实披露**：PARTIAL。terra §9 自查表**无伪造**（我逐格 neuter 复核，含限时补的两格，全真红）；neuter 自查表诚实。**但** §11 对账 row 10 overclaim（见 MAJOR-1）——声称"GT refs 与 converter ledger 一致 G9/audit 实测通过"而无门支撑。
8. **恒真式自检 / 死分支 / shipped-untested**：见 MINOR-1（5 死码）、MINOR-2（宽 except + 未包裹前置调用）、MAJOR-2（§9.2/§9.3/§6.6 未落 fixture）、NIT-2（死防御分支）。**关键澄清**：z_transform / datum / union / raster 诸门经审读均为**真跨源交叉检查、非恒真自比**；缺的是负例锁与一道 postcheck，不是门本身假。

---

## 4. false-lock / 假绿 专项结论

**未发现任何 false-lock 或 false-green。** 10 类命脉变异全部 neuter 验真为真门（该门在算、passed=True 可复现、无别处兜底、fixture 非恰非法）；sm24 正向提取 live 验证正确；审计 z 与 GT z 当前一致。上一轮转换器返工的"九门 neuter 假锁"病**未复发**。本批需修项均为"另一半防线缺失 / 覆盖锁缺失 / 一处对账 overclaim"，性质上是**防御不足**而非**假绿**——故裁 APPROVE-WITH-CHANGES 而非 REWORK。

---

## 5. 全仓测试

```
python -m pytest -q -p no:cacheprovider
→ 1556 passed, 10 xfailed, 146 warnings in 583.13s
```
零 v2 / execution / reading / correction 回归；既有 gt / overlay / gt_schema / gt_from_dxf 测试零回归。
`tests/test_tarch_elevation_must_red.py` 14 passed（未污染基线）。

---

## 6. 出口清单（返工建议，按优先级）

1. **[MAJOR-1]** 实现 spec §6.5 converter↔GT 配对一致性 postcheck，接线 `tarch_elevation_pairing_drift` + 真门级必红 fixture；或诚实降级 §11 row 10 措辞。
2. **[MAJOR-2]** 补 §9.3 z-datum 必红 fixture（本批安全命门）+ §9.2 frame/title 必红 fixture + §6.6 sm24 正向 e2e 断言（宜随 sm24 anchor 晋升一并落）。
3. **[MINOR-1]** 清理/接线 4 个死登记码，或文档说明 G9 立面失败统一走 `tarch_v3_precondition`。
4. **[MINOR-2]** 窄化 `_run_g9_v3_preflight` 的宽 except；前置 `extract_gt_v3` 包 try 或复用 G9 结果避免双跑。
5. **[NIT-1]** 修正水平镜像测试 docstring 机制描述。
6. **[NIT-2]** 处置 `item is None` 死防御分支（留注释或删）。

以上出口均可作为跟进债登记，不阻断本批 merge / sm24 后续人签收官流程。
