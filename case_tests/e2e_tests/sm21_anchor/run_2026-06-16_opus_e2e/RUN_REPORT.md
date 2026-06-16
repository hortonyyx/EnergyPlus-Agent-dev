# sm21_anchor / run_2026-06-16_opus_e2e 跑批反馈 (2026-06-16, orchestrator=opus-4.8)

**结论**: ✅ clean / EP Completed, 0 severe, 6 warn / 14区·100面·15窗

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

## judge② 裁决（主 Agent opus-4.8）

**J0 · 0_reading = PASS（忠实，对 gt）**：6 视图全过 gate①；逐图肉视对照原图——两平面忠实捕获
F1(3北办公+走廊+3南) ≠ F2(2北会议+走廊+4南) 的**异图**、**走廊两层都全宽未被切断**（避开 sm20 坑）、
门 heal 未臆造；立面窗数+z带+门处理正确。识图无识别错。

**J1 · 1_correction = PASS（对 gt 定量精确，1 minor）**：校正几何与 gt 逐项比——

| 维度 | gt | 产物 | |
|---|---|---|---|
| 区数 F1/F2 | 7 / 7 | 7 / 7 | ✅ |
| 层高 F1/F2 (m) | 3.0 / 3.6 | 3.0 / 3.6 | ✅ |
| 窗 North F1/F2 | 3 / 2 | 3 / 2 | ✅ |
| 窗 South F1/F2 | 3 / 4 | 3 / 4 | ✅ |
| 窗 East F1/F2 | 1 / 1 | 1 / 1 | ✅ |
| 窗 West F1/F2 | 0 / 1 | 0 / 1 | ✅ |
| 总窗 | 15 | 15 | ✅ |
| 异图布局 | F1=3北+3南 / F2=2北+4南 | 一致 | ✅ |

- **minor**：F1 东南房 `R_1F_BR` 用途标为 `office`，gt 该处是 `meeting`（圆会议桌）。仅**用途标签**
  差异（影响内部负荷档位），不动区数/几何/窗位。geometry 完美，不重抽。

**J4 · 4_mep = disabled**（stub，不产 verdict）。

> 本轮关键修复：首抽 4_mep 系统性缺陷（全 NoMass→warmup 4 severe；schedule 缺 ScheduleTypeLimits）
> 经用户决策**改 4_mep skill**（authoring.md 加两条硬规则：ScheduleTypeLimits 自建 + 不透明围护须有热质量
> 材料层；备份 `backup/Skill_history/2026-06-16_4mep_scheduletypelimits_and_mass/`）后，盲重抽 attempt 1
> 即 gate① 干净、EP 0 severe。

## 🔍 请你肉视检验（确定性 + judge 都盖不死的感知项）
1. 填色区图 `1_correction/zones.png` vs 原平面图 `case_data/{1f,2f}_view.png` —— 房间无错并/错分/缺失/多出（尤其走廊是否被切断，sm20 那类坑）；**特别核 F1 东南房**该是会议室还是办公室（J1 标了 minor）
2. 立面窗位图 `1_correction/elev.png` vs 原立面 `case_data/{South,North,East,West}_view.png` —— 窗落在对的立面/楼层/位置；West-F1 应**无窗（是门）**
3. 3D 体量 `2_modelling/building_geometry.glb` —— 整体像不像这栋楼（trimesh 出 GLB，230 面）

_附: baseline.json / 各 <stage>_checks.json / geometry_digest=8ba319cb6b560f5625a5f7d72c7abb205f8491e19d89621bb9ac70e77cd21feb_
