# sm20_anchor / run_2026-06-15_baseline 跑批反馈 (2026-06-16, orchestrator=opus-4.8)

**结论**: ✅ clean / EP Completed, 0 severe, 6 warn / 19区·135面·16窗

**模型**: {'intake_correction': 'deepseek-v4-pro', 'default': 'deepseek-v4-pro'}

## 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 0_reading | 60 | 0 | 0 | 10 |
| 1_correction | 8 | 0 | 0 | 1 |
| 2_modelling | 5 | 0 | 0 | 0 |
| 4_mep | 10 | 0 | 0 | 1 |
| 5_intakeoutput | 1 | 0 | 0 | 0 |
| downstream | 3 | 0 | 0 | 1 |

## 🔍 请你肉视检验（确定性 + judge 都盖不死的感知项）
1. 每层填色区图 `1_correction/*_zones.png` vs 原平面图 —— 房间无错并/错分/缺失/多出（尤其走廊是否被切断，sm20 那类坑）
2. 立面窗位图 `1_correction/*_elev.png` vs 原立面 —— 窗落在对的立面/楼层/位置
3. 3D 体量 `2_modelling/building_geometry.glb` —— 整体像不像这栋楼（trimesh 出 GLB）

_附: baseline.json / 各 <stage>_checks.json / geometry_digest=225fb57256b3b2a0546c0cacde68506240c6cf0283d109d8d0be4fd275f3b411_
