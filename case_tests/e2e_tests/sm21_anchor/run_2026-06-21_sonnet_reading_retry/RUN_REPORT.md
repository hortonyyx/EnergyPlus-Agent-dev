# sm21_anchor / run_2026-06-21_sonnet_reading_retry 跑批反馈 (2026-06-21, orchestrator=opus-4.8)

**结论**: ❌ STOPPED (human_redraw_required@0_reading) / EP 未跑

**模型**: {'intake_correction': 'deepseek-v4-pro', 'default': 'deepseek-v4-pro'}

## 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 1_correction | 0 | 0 | 1 | 0 |
| 2_modelling | 0 | 0 | 1 | 0 |
| 3_split_pairing | 0 | 0 | 1 | 0 |
| 4_mep | 0 | 0 | 1 | 0 |
| 5_intakeoutput | 0 | 0 | 1 | 0 |
| 0_reading | 52 | 0 | 0 | 8 |

## 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | human_redraw_required | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 1}

**judge② verdicts**: 1 条（1 条 blocking；见各 attempts/NNN/judge.json）

## ⛔ blocking
- [1_correction::1_correction.build] required artifact missing: 1_correction/correction_geometry_snapped.json
- [2_modelling::2_modelling.build] required artifact missing: 2_modelling/building_geometry.json
- [3_split_pairing::3_split_pairing.build] required artifact missing: 3_split_pairing/geometry_specs.md
- [4_mep::4_mep.build] required artifact missing: 4_mep/mep_output.json
- [5_intakeoutput::5_intakeoutput.build] required artifact missing: 5_intakeoutput/intake_output.json

## 🔍 请你肉视检验（确定性 + judge 都盖不死的感知项）
1. 每层填色区图 `1_correction/*_zones.png` vs 原平面图 —— 房间无错并/错分/缺失/多出（尤其走廊是否被切断，sm20 那类坑）
2. 立面窗位图 `1_correction/*_elev.png` vs 原立面 —— 窗落在对的立面/楼层/位置
3. 3D 几何 `2_modelling/geometry_viewer.html`（浏览器打开：orbit / 半透明 / 截面 / 爆炸 / 量距） —— 整体体量 + 内部分区 + 窗在对的立面，确认无误后 `approve-geometry`

_附: baseline.json / 各 <stage>_checks.json / geometry_digest=None_
