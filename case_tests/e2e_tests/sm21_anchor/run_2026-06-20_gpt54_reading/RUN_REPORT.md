# sm21_anchor / run_2026-06-20_gpt54_reading 跑批反馈 (2026-06-21, orchestrator=opus-4.8)

**结论**: ✅ clean / EP Completed, 0 severe, 6 warn / 14区·112面·15窗

**模型**: {'intake_correction': 'deepseek-v4-pro', 'default': 'deepseek-v4-pro'}

## 逐段 gate①

| 段 | pass | flag | block | n/a |
|---|---|---|---|---|
| 0_reading | 52 | 0 | 0 | 8 |
| 1_correction | 7 | 0 | 0 | 1 |
| 2_modelling | 5 | 0 | 0 | 0 |
| 4_mep | 10 | 0 | 0 | 1 |
| 5_intakeoutput | 1 | 0 | 0 | 0 |
| downstream | 3 | 0 | 0 | 1 |

## 逐段编排状态（judge-in-the-loop）

| 段 | status | 抽样 |
|---|---|---|
| 0_reading | judge_pass | 2 |
| 1_correction | judge_pass | 1 |
| 2_modelling | deterministic_pass | 1 |
| 3_split_pairing | awaiting_geometry_approval | 1 |
| 4_mep | deterministic_pass | 1 |
| 5_intakeoutput | deterministic_pass | 1 |

**抽样次数（attempts/ 落盘）**: {'0_reading': 2, '1_correction': 1, '2_modelling': 1, '3_split_pairing': 1, '4_mep': 1, '5_intakeoutput': 1}

**judge② verdicts**: 2 条（0 条 blocking；见各 attempts/NNN/judge.json）

## 🔍 请你肉视检验（确定性 + judge 都盖不死的感知项）
1. 每层填色区图 `1_correction/*_zones.png` vs 原平面图 —— 房间无错并/错分/缺失/多出（尤其走廊是否被切断，sm20 那类坑）
2. 立面窗位图 `1_correction/*_elev.png` vs 原立面 —— 窗落在对的立面/楼层/位置
3. 3D 几何 `2_modelling/geometry_viewer.html`（浏览器打开：orbit / 半透明 / 截面 / 爆炸 / 量距） —— 整体体量 + 内部分区 + 窗在对的立面，确认无误后 `approve-geometry`

_附: baseline.json / 各 <stage>_checks.json / geometry_digest=6d7a44f4caae4e92ddc750a70361a7c8c37a8c150c4e17951d65aed9be5aaa2c_
