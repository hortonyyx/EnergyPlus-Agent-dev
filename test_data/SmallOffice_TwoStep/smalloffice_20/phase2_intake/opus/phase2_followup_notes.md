# phase2_followup_notes — opus run

Items where phase2_rules.md did not fully cover the situation and the answer required a judgment call. Suggest folding these into a future rev of phase2_rules.

## 1. Inter-floor split-pairing when upper/lower footprints differ — sub-surface naming convention

phase2_rules §3 Step 4 says "F2 各 zone floor 对应 F1 同名 zone ceiling — 这是模板", and gives a 2-line good example for the matching-footprint case. But for sm_20, F1 (3-room north row) / F2 (4-room north row) / F3 (integral north zone) split differently across floors, so a single F2 zone's floor must be split into multiple sub-surfaces, and a single F3 ceiling/floor must be split into 4. I introduced an ad-hoc sub-surface naming convention (`ceiling_F1_N1_seg_a`, `floor_F2_N2_west`, `floor_F3_North_seg1`...). Rules should specify:

- Required sub-surface naming pattern (e.g. `<parent_surface>_seg<n>` or `<parent_surface>_<direction>`).
- Whether the downstream `surface_specs` consumer is expected to split the parent into N sub-surfaces, or whether it should create them as fully independent surfaces (the latter is what I assumed).
- Whether the pairing summary list should be in surface_specs body or a separate field.

## 2. Composite interior wall segmentation

Same problem on interior walls: F1_Corridor's south wall touches three rooms (F1_S1/S2/S3) at the corridor side. I segmented it (`south_wall_F1_Corridor_seg1/seg2/seg3`) to make per-pair interzone walls explicit. Rules don't say whether this segmentation is required or if a single composite wall paired only with its dominant neighbor is acceptable. EnergyPlus requires per-pair surfaces, so the segmentation is right — but it should be stated.

## 3. Window placement falling on internal-wall column line

North F1 window 2 has world x = [6.30, 8.70]. The interior wall x=5 / x=10 means the window is entirely within room F1_N2 (5–10) — fine. But window 1 (x_world = [1.40, 3.80]) is within F1_N1 (0–5), and window 3 (x_world = [11.20, 13.60]) within F1_N3 (10–15) — all fine. **No window crosses an interior wall in F1/F2 south or F1 north.** However, F2 north window 2 (world x [8.45, 10.20]) crosses the F1 internal wall at x=10 IF compared to F1; but for F2 the partition is at 7.50/11.25, so it sits cleanly in F2_N3 (7.50–11.25). The F3 north ribbon (1.40–13.60) is on F3_North which is integral so no issue. **Rules should add a check: "no fenestration may straddle an interior wall on its own floor".** Pass for sm_20.

## 4. Corridor people / lights density default

phase2_rules §3 Step 7 quotes 10 m²/person and 10 W/m² as ASHRAE 90.1 Office defaults, but corridors are typically a separate space type with lower occupancy (~30 m²/person, lights ~5 W/m²). I applied that distinction (offices vs corridors) but it is a judgment call not anchored in the rules.

## 5. F3 ceiling_height = 4.80 vs F1/F2 = 3.60

phase1 South_view notes the F3 layer is 4.80 m where F1/F2 are 3.60. phase2_rules §2.2 confirms F3 height 4.80. There is no rule about whether this is "valid input as drawn" or a likely transcription oddity. I treated as authoritative (phase1 frozen). If real cases should normalize cap heights, a rule is needed.

## 6. East / West F3 single-window placement on corridor

The F3 east and west window each land in world y ∈ [3.50, 4.50], which sits within the corridor band (y[3,5]). So the parent is `east_wall_F3_Corridor` / `west_wall_F3_Corridor`, not an office zone. Rules don't call out the case of fenestration on a corridor exterior wall (whether that is plausible for an office building) — a sanity-check item worth flagging.

## 7. Building.Name char restriction

phase2_rules §5 says charset = alnum + `_` only. testdata `TestName = "smalloffice_20"` is fine; I used `Smalloffice_20` (capital S) for readability. Rules could clarify case-preservation policy (or canonical lowercase).

## 8. site_location.Name vs city string

I used `Shenzhen_CN`. SiteLocationSchema validator collapses non-word chars to `_`, so `Shenzhen, China` → `Shenzhen_China` would also be legal at the schema level. Rules and downstream weather-file lookup expect a specific canonical form — recommend pinning `<City>_<ISO2>` (e.g. `Shenzhen_CN`) in phase2_rules §5.

## 9. Schedule:Compact day-type names

I used `Weekdays`, `Weekends`, `Holidays`, `AllDays`. EnergyPlus expects `Weekdays`, `Weekends`, `Holiday`, `AllOtherDays`, etc. Rules do not constrain this; the downstream schedule subagent must translate. Worth a one-line note in phase2_rules §3 Step 7.

## 10. Vertex CCW for composite (split) ceiling/floor sub-surfaces

I synthesized each sub-surface using §4's Ceiling row vertex pattern with its own (x_min,x_max,y_min,y_max) sub-rectangle. Rules' §4 table is per-zone but does not explicitly address sub-rect cases. I extended the rule by analogy. A 1-line confirmation in the rules would remove ambiguity.
