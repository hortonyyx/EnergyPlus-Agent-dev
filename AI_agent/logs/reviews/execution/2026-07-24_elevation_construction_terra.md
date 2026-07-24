# 2026-07-24 天正命名立面施工简报（terra）

## 施工范围与备份

- 施工前已备份 `tarch_converter_schema.py`、`tarch_normalize.py`、`gt_extraction.py` 至 `backup/src_history/2026-07-24_elevation/`。
- 主控明示授权的一处窄例外：先备份 `scripts/tool_scripts/render_gt_overlay.py` 至 `backup/scripts_history/2026-07-24_elevation_overlay_corner_sort/`，仅修 line 323 的 PIL rectangle 两角点排序。根因是 v3 立面 z 向上投影到 y-down PNG 后，两个 y 反序，PIL 要求 `y1 >= y0`；修法仅在绘制前 `min/max`，`_pixel_for_world_elevation`、affine 与全部投影数学均未改。sm21 走 legacy 路径，故此前未触发。新增真实 sm24 四视图回归覆盖该路径。
- 本轮主控明示授权第二处窄添加：在同一 `ElevationViewBindingV1` 绘制分支，只新增 facade envelope 矩形（plan projection `[lo,hi] × [z_floor, z_floor+ceiling_height]`）的白色描边。理由是让人核直观看到镜像/错位；未改 `_pixel_for_world_elevation`、affine 或任何投影数学，plan 分支的 footprint envelope 未改。修改前已再次备份该脚本到同一受控 backup 目录。
- 未改 GT v3 wire、`GroundTruthV3` opening wire、v2 legacy adapter、scorer/Va/Vg、execution/reading/correction；未写 `case_tests/test_baseline/gt/`、`gt_sources/` 或 e2e `case_data/`。

## 实现与单位结论

- 新增 request v3 的独立 `named_datum_bound` 立面契约、四个 datum 的有向端点、title map、门 block fingerprint/exhaustive role map、typed raster controls、E0--E8 diagnostics、完整 G9 `extract_gt_v3` preflight 及 G10 review-index acknowledgement。
- sm24 事实底座按合同输入：North `125/start`、South `102/start`、West `144/end`、East `12F/end`；门 `112` 为唯一 structural outline，`11C` exact excluded。没有以最低线、窗台或“天正常规”推导 z。
- 主控交付的控制点是 DXF-native mm；`world_from_source_m` 的 source 输入为 m。因此 request/manifest 的 `pixel_to_source_m` 把 main-control affine 的线性项及 offset 同乘 `0.001`，但 calibration controls 原样保存为 mm；converter 用 `metres_per_unit` 转换后复核三点残差、角色、非共线、lo/hi endpoint 与四角反投影。四立面及 1F 平面均通过。
- 1F 平面 binding 是 `plan-F1 / 1f_view.png`，控制点为 `footprint_sw/se/nw` 外墙角；它们由 `GTV3_FOOTPRINT` 的 SW/SE/NW source 点、非共线与 native-mm→source-m residual 校验，不以图像启发式猜测。

## sm24 review 产物

- `logs/experiments/2026-07-24_sm24_gt_review/gt/gt.json`：14 个 relevant openings，均有 source-observed z（11 window、3 exterior door）。
- `gt/renders/gt_plan.png`、`gt/renders/gt_elev.png`，后者含 4 个真实 elevation surface。
- 同一原子 `gt/renders/` bundle 内共 7 张图：`gt_plan.png`、`gt_elev.png`、`overlay_1f_view.png`、四张 `overlay_{East,North,South,West}_view.png`。平面 overlay 是调暗 `1f_view.png` 加 footprint、8 个 zone 描边/id 与窗门线；立面 overlay 保留 opening id/z、datum legend，并新增白色 facade envelope。已与 `maincontrol_calibration_verify/plan_verify.png` 逐项对照落位一致。
- `opening_elevation_audit.json` 有 14 行；每行含 `opening_id/evidence_id/view_id/facade_family/floor_id/kind/host_zone_id/plan_world_along_interval/elevation_source_along_interval/world_along_interval/z_interval/datum_entity_handle/datum_source_start_point/datum_source_end_point/declared_world_along_lo_source_endpoint/mapped_endpoint_pair/raw_source_handles/structural_source_handles`，并绑 candidate GT 与 manifest hash。South 的对称两窗、East 各 host zone 的 handness 由此供 G10 人核。
- canonical `review_index.json` 以 inventory 绑定 `gt.json`、两张 GT render、五张 overlay、audit（9 files）；新 inventory hash：`fa0ad58d95b1718c64b808fa34cf20e213f797db0c19f4a11057e28890539ccf`。v3 ack 只接受这一 index hash，不使用逐文件散绑。

## §9 必红夹具逐格自查

| 变异 | 实际目标门 / 证据 | 状态 |
|---|---|---|
| South sign-only | G1 / `tarch_elevation_along_direction_mismatch` | 红 |
| South endpoint-only | G1 / 同码 | 红 |
| South along-offset-only | G1 / 同码 | 红 |
| South sign+offset、endpoint 不变 | G1 / 同码 | 红 |
| CIRCLE `11C` 误作 structural outline | G3 / `tarch_elevation_door_structure_invalid` | 红 |
| block fingerprint drift | G3 / `tarch_elevation_door_block_drift` | 红 |
| window evidence kind→door | G9 / `elevation_opening_no_candidate` | 红 |
| 删除 elevation evidence | G9 / `gt_opening_elevation_evidence_mismatch` | 红 |
| South raster datum lo/hi source anchor 对调 | G10 / `tarch_raster_calibration_invalid` | 红 |
| raster SHA256 改 1 byte | overlay delivery / `gt_overlay_raster_hash_mismatch` | 红 |
| 投影四角越界 | overlay delivery / `gt_overlay_projection_out_of_bounds` | 红 |
| y-down 的 z 像素角反序 | 真 sm24 `build_gt_overlay_images_v3` | 修复后绿；回归已覆盖 |
| door union 正面积 overlap | G3 / `tarch_elevation_door_structure_invalid` | 红 |
| door union gap（不连通） | G3 / 同码 | 红 |
| door union T-shape（非矩形闭包） | G3 / 同码 | 红 |
| door union 两段不同 z | G3 / 同码 | 红 |
| raster 水平镜像且四角仍图内 | G10 / `tarch_raster_calibration_invalid` | 红 |
| plan footprint SW/SE control 对调 | G10 / `tarch_raster_calibration_invalid` | 红 |
| 三字段同步一致重标 | G10 人审 | 机器不应必红；由 audit rows + overlay 暴露，待人工 datum/手性确认 |

## §11 完成定义逐条对账

| # | 对账 | 结果 |
|---|---|---|
| 1 | v1/v2 legacy 与 v3 datum-bound 分离 | 已实现并保留 legacy variant |
| 2 | 44 window LINE → 11 outlines | sm24 实测通过 |
| 3 | 5 door INSERT、`112` → 3 exterior doors | sm24 实测通过 |
| 4 | 11 window 一一链接 | sm24 实测通过，无 orphan/ambiguity |
| 5 | 四 datum/部分沿向 mutation | 四类真红；三字段同步一致重标留 G10 人审 |
| 6 | `11C` 排除、门 z 不依赖 raw bbox | 实现及误角色真红覆盖 |
| 7 | complete manifest 1 plan + 4 elevation | 实测通过 |
| 8 | G9 真跑 `extract_gt_v3` | 实测通过 |
| 9 | 14 opening 全有 observed z | 实测通过 |
| 10 | GT refs 与 converter ledger 一致 | G9 / audit 实测通过 |
| 11 | `gt_elev.png` 四真实 surface | 实测通过 |
| 12 | 四张有向三点 calibration overlay 且不过界 | 实测通过 |
| 13 | 14 行 audit + overlay、同 inventory | 产物已绑 review-index |
| 14 | 用户 datum/手性确认后才 promotion | 未 promotion；G10 保持 candidate，待用户确认 |
| 15 | 无 v2/execution/reading/correction 回归 | 全仓最终回归通过 |

## 测试

- `pytest -q tests/test_tarch_elevation_must_red.py`：`14 passed`；新增 plan footprint control 对调，命中 G10。
- `pytest -q tests/test_tarch_elevation_must_red.py tests/test_gt_overlay.py`：`27 passed`（12 个既有 Pydantic serializer warnings）；含真实 sm24 plan overlay、四立面、envelope 描边 capture。
- 本轮全仓最终回归：`1556 passed, 10 xfailed, 146 warnings`，`576.92s`；零 v2/execution/reading/correction 回归。

## 诚实交接

已完成候选 GT、真实原图 overlay、审计表与 review-index；未做 promotion、未写受保护基线资产、未 push。door union 四种坏形态与“水平镜像但仍图内”均已有单列、真跑目标门的必红夹具；不以其他 gate 兜底。
