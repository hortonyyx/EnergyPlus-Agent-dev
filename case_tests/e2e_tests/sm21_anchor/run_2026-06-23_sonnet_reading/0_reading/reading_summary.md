# Reading Summary — sm21_anchor
Run: 2026-06-23 | Model: claude-sonnet-4-6

---

## Per-image confidence and stroke counts

| Image | Kind | Wall strokes | Window strokes | Wall_fill strokes | Overall confidence | Notes |
|---|---|---|---|---|---|---|
| 1f_view | plan | 10 | 7 | 0 | high | West bump-out traced; 5 door heals; east slit window medium confidence |
| 2f_view | plan | 9 | 8 | 0 | high | Bottom chain segment values ambiguous (360/560 pair); partition x positions approximate |
| South_view | elevation | 0 | 9 | 2 | high | F1 door excluded; small F1 window estimated; 4 F2 + 2 F1 large + 1 F1 small windows |
| North_view | elevation | 0 | 7 | 2 | high | Different F2 pattern (2 wide windows) vs South (4 narrow); 3 F1 windows |
| East_view | elevation | 0 | 2 | 2 | high | Single window each floor, centred; F1 sill only 200mm |
| West_view | elevation | 0 | 1 | 2 | high | F2 window only; F1 has floor-height door (excluded); inner F1 chain undivided |

---

## 1F plan — interior partitions traced and rationale

**10 wall strokes total (4 perimeter + 1 corridor + 5 interior):**

1. **S1** — south perimeter (full width y=0.00)
2. **S2** — north perimeter (full width y=8.00)
3. **S3** — west perimeter wall with bump-out vestibule polyline (L-shaped, seen as drawn double-wall outline)
4. **S4** — east perimeter (full height)
5. **S5** — main horizontal corridor partition at y=5.00 (full width 0–15m); left dimension chain 3.00+1.50+0.25+0.25=5.00 confirms position; drawn as heavy line visible across full plan width
6. **S6** — vertical partition x=5.00, upper zone only (y=5.00–8.00); seen as drawn line separating left and centre north offices
7. **S7** — vertical partition x=10.00, upper zone only (y=5.00–8.00); seen as drawn line separating centre and right north offices
8. **S8** — vertical partition x=3.44, lower zone (y=0–5.00); bottom chain 0.54+0.90+2.00=3.44; seen as drawn line separating small SW room from corridor
9. **S9** — vertical partition x=5.00, lower zone (y=0–5.00); seen at same x as S6; healed door at y≈2.50
10. **S10** — vertical partition x=10.00, lower zone (y=0–5.00); seen at same x as S7; healed door at y≈2.50

**Why 5 interior partitions (S5–S10 excluding S5):** I can see by drawn partition lines 5 interior walls — one horizontal corridor, two upper-zone verticals, and three lower-zone verticals (counting S8 at x=3.44, S9 at x=5.00, S10 at x=10.00). The partition at x=3.44 creates a small SW room only in the lower zone; no corresponding wall exists in the upper zone. Total rooms implied: 3 upper + 4-ish lower (depending on how the SW entry vestibule and corridor connect), consistent with testdata_prompt indicating 7 thermal zones on F1.

---

## 2F plan — interior partitions traced and rationale

**9 wall strokes total (4 perimeter + 1 corridor + 4 interior):**

1. **S1** — south perimeter
2. **S2** — north perimeter
3. **S3** — west perimeter (straight, no bump-out on 2F)
4. **S4** — east perimeter
5. **S5** — main horizontal partition at y=3.00 (full width); left chain bottom segment 3000mm; consistent with single heavy line seen dividing upper (conference) from lower (office cells)
6. **S6** — vertical partition x=7.44, upper zone (y=3.00–8.00); top chain 1950+3600+1889=7439≈7.44; single line dividing west conference room from east conference room
7. **S7** — vertical partition x=3.39, lower zone (y=0–3.00); bottom chain 2190+1200=3390; divides cell 1 from cells 2–4
8. **S8** — vertical partition x=7.50, lower zone (y=0–3.00); centre line (15000/2=7500); divides cells 2 from cells 3
9. **S9** — vertical partition x=11.61, lower zone (y=0–3.00); symmetric to S7 (15000-3390=11610); divides cells 3–4 from cell 4

**Why 4 interior partitions:** upper zone has 1 vertical (two conference rooms); lower zone has 3 verticals (four office cells). Total rooms: 2 upper + 4 lower + 1 corridor zone? = depends on whether the corridor between y=3.00–5.00 (using 1F partition logic) is a separate zone. On 2F the left chain shows 3000+400+1200+400+3000=8000 where the 400+1200+400 band may represent window-height reference on the west/east perimeter walls, not a second horizontal partition. Only ONE horizontal line is seen at y=3.00. This gives 2+4=6 spatial areas, consistent with testdata_prompt 7 zones if the corridor/entry counts as one zone.

---

## Repeatedly null or absent fields

- `thickness_m`: always null (by schema rule)
- `scale_origin.world_z_m`: always null for plan images
- `scale`: no scale bar or ratio text visible in any image
- `north_arrow`: not visible in any image
- Elevation `outline` pen: not used in any elevation — wall_fill boundaries coincide with outline in all four elevations (no separate outline stroke needed)
- `facade_axis_note`: null for plan images, filled for all 4 elevation images

---

## Schema feedback and anomalies

1. **North top chain sum discrepancy**: 1950+3600+1889+1891+3600+1950=14880mm ≠ 15000mm (gap 120mm). Likely absorbed at chain endpoints (wall half-thickness). Window positions derived from chain values with this acknowledged delta.

2. **2F south bottom chain sum discrepancy**: individual segments 2190+1200+360+560+1200+2190+2190+1200+360+560+1200+2190 sum to 15200mm > 15000mm by 200mm. The "360 560" pair appears jammed together in the image; individual values transcribed verbatim but cumulative positions are approximate.

3. **1F right y-chain (2940+340+1200+340+2940=7760mm)**: does not sum to 8000mm. Interpreted as interior room clear heights plus window sill/head dimensions, not a complete floor height chain. The overall 8000mm confirmed by left chain.

4. **South facade F1 small window**: narrow window visible at approx x=4.64–5.18 alongside door. No explicit bottom chain segment for its width — the "1200" in the bottom chain covers the adjacent door; the small window width is estimated visually at ~0.54m.

5. **East facade F1 sill=200mm**: unusually low sill (200mm from floor). Transcribed verbatim; correction stage may flag for cross-check.

6. **West facade F1 door vs East facade F1 window**: West shows floor-height double-door (inner chain undivided "3000"); East shows window with 200+1800+1000 subdivisions. These are distinct openings on opposite walls, not a cross-reading error.

7. **1F west bump-out dimensions**: bump-out width estimated at 240mm (matching the "240" labels visible at the entry zone) and height 1500mm from left chain (3.00 to 4.50). Exact outer coordinates of bump-out may require correction stage refinement.

---

## Scales (noted here, not in strokes)

- 1F plan: scale not visible in image (likely 1:100 for an office drawing at this detail level, but not transcribed — no scale bar seen)
- 2F plan: same
- All elevations: scale not visible in images
