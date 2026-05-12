# Phase 2 Self-check — opus run

Run against `intake_output.json` per phase2_rules.md §7.

| # | Check | Status | Note |
|---|---|---|---|
| 1 | 11 fields present | PASS | `['building','construction_specs','fenestration_specs','hvac_specs','lights_specs','material_specs','people_specs','schedule_specs','site_location','surface_specs','zone_specs']` |
| 2 | All zones explicitly enumerated, per-floor count = testdata `thermal_zones` (7+8+4 = 19) | PASS | F1: F1_S1/S2/S3/Corridor/N1/N2/N3 (7). F2: F2_S1/S2/S3/Corridor/N1/N2/N3/N4 (8). F3: F3_S1/S2/Corridor/North (4). |
| 3 | All surfaces enumerated per zone (4 walls + floor + ceiling/roof), no template | PASS | Each of 19 zones has its 6 surfaces listed explicitly with vertices. Composite walls/ceilings/floors split into named sub-surfaces where footprints diverge. |
| 4 | Cross-floor floor/ceiling split-pairing explicitly enumerated | PASS | 10 explicit F2↔F1 pairings + 9 explicit F3↔F2 pairings written in surface_specs "Inter-floor pairing summary". No "foreach" / "same as F1". |
| 5 | All fenestrations give `parent_surface_name` mapping to a valid external wall | PASS | 16 windows total. South: 6 parents = south_wall_F1_S1/S2/S3 + south_wall_F2_S1/S2/S3 (all Outdoors). North: 8 parents = north_wall_F1_N1/N2/N3 + north_wall_F2_N1/N2/N3/N4 + north_wall_F3_North (all Outdoors). East: 1 parent = east_wall_F3_Corridor (Outdoors). West: 1 parent = west_wall_F3_Corridor (Outdoors). All parent names exist verbatim in surface_specs. |
| 6 | Cross-field name references literally consistent | PASS | Constructions used in surface_specs/fenestration_specs (Default_Ext_Wall / Default_Int_Wall / Default_Window / Default_Floor / Default_Ceiling / Default_Roof / Default_GroundFloor) all defined in construction_specs. Schedules referenced (Office_Occupancy_Frac / Office_Lighting_Frac / Office_Activity_Level / Office_HVAC_OnOff / Office_Cooling_Setpoint / Office_Heating_Setpoint) all defined in schedule_specs. All zone refs match zone_specs verbatim. |
| 7 | Naming charset legal (alnum + `_` only) | PASS | All zone/surface/window/construction/material/schedule names use only `[A-Za-z0-9_]`. site_location.Name = `Shenzhen_CN`. building.Name = `Smalloffice_20`. |
| 8 | WWR / window count sanity | PASS | South: 3 windows × 2 floors × 2.40×1.80 = 25.92 m² on a south outer wall area 15×7.20 = 108 m² (F1+F2 portion 108 m²) → ~24% WWR on F1+F2 south, F3 south 0. North F1: 3 × 2.40×1.80 = 12.96 on 5×3 + 5×3 + 5×3 = same 54 m² F1 north → matches. North F2: 4 × 1.75×1.80 = 12.60 m². North F3 ribbon: 12.20 × 2.60 = 31.72 m² on 15×4.80 = 72 m² (44%, dominant top). East/West F3: 1 × 1.00×2.40 = 2.40 m² each on 8×4.80 = 38.40 m² (~6%). |
| 9 | z continuity F1→F2→F3 | PASS | F1 z_top = 3.60 = F2 z_floor. F2 z_top = 7.20 = F3 z_floor. F3 z_top = 12.00. No gaps. |

## Additional checks beyond §7

- vertex CCW table from §4 applied uniformly. South walls: v1=(x_min,0,z_top), v2=(x_max,0,z_top), v3=(x_max,0,z_floor), v4=(x_min,0,z_floor). North walls: v1=(x_max,8,z_top), v2=(x_min,8,z_top), v3=(x_min,8,z_floor), v4=(x_max,8,z_floor). East walls: v1=(15,y_min,z_top), v2=(15,y_max,z_top), v3=(15,y_max,z_floor), v4=(15,y_min,z_floor). West walls: v1=(0,y_max,z_top), v2=(0,y_min,z_top), v3=(0,y_min,z_floor), v4=(0,y_max,z_floor). Floors and Ceilings/Roofs follow §4 row 5/6 directly.
- Default_Window construction layers only `Mat_SimpleGlazing` (single SimpleGlazingSystem layer), no air gap or second glazing — avoids the known EP NaN fatal flagged in `project_fenestration_glazing_layer_bug`.
- Fenestration `Window_F3_North_Ribbon_1` z range = 10.80 − 8.20 = 2.60 m, matches North_view D34. F3 east/west single window z range 10.60 − 8.20 = 2.40 m, matches D14.
- North-window world x derivation verified: F1 windows local x ∈ {1.40, 6.30, 11.20} → world x of left edge ∈ {1.40, 6.30, 11.20} (since `X_world_left = 15 − x_local_right` and the rect symmetry preserves the same value set for symmetric windows). For F2 asymmetric layout, world x ranges checked: {[1.40,3.15],[4.80,6.55],[8.45,10.20],[11.85,13.60]}.
- East and West F3 windows both land on `y_world ∈ [3.50, 4.50]` (corridor band y[3,5]); parent = corridor east/west wall.

## Caveats / non-blocking

- The F2 north window 1.75/1.65/1.90/1.65/1.40 dim chain matches phase1 transcription; "asymmetric" non-issue per phase2 rules (figure-as-drawn).
- Corridor floor area per person = 30 m² (sparse corridor occupancy) is an editorial default not specified by phase2_rules; chosen to keep ASHRAE-like behavior. Documented in followup notes.
