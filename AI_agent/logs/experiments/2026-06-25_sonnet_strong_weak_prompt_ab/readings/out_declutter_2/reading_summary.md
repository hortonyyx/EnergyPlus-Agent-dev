# Reading summary — out_declutter_2

Run date: 2026-06-25
Images: decluttered plan images (furniture and dimension chains omitted from fills; wall fills gray, windows/door-swings cyan)

---

## Per-image confidence

### 1f_view.png → 1f_view.json
- **Overall confidence**: medium-high
- **Wall strokes**: 10 traced. Perimeter (S1–S4) high confidence. Interior corridor wall (S5) high confidence. Interior vertical partitions (S6–S7 upper zone, S8 lower zone) high confidence. Lower-left sub-room walls (S9–S10) medium confidence (partial walls, short lengths, some ambiguity about extent near stair).
- **Window strokes**: 8 traced. North wall 3 windows, south wall 4 windows, east wall 1 window. Positions estimated from visual x-spacing along walls; exact x_range_m values are seen-estimated and will need dimension-chain refinement by correction stage.
- **Door healings**: 4 healed (west entry, 3 on corridor wall S5). All door swing arcs were cyan in the decluttered image.
- **Repeatedly null fields**: `thickness_m` (plan — by rule); `facade_axis_note` (plan — N/A); `world_z_m` (plan — by rule); some dimension `from`/`to` coordinates set to null where chain spans were partially legible.

### 2f_view.png → 2f_view.json
- **Overall confidence**: high
- **Wall strokes**: 9 traced. Perimeter (S1–S4) high confidence — clean rectangle, no entry recess on 2F. Interior horizontal wall (S5) high confidence. Interior vertical walls (S6 upper, S7 lower) high confidence. Lower-zone sub-partitions (S8, S9) medium confidence (estimated position from window/door spacing).
- **Window strokes**: 12 traced. North wall 4 windows, south wall 4 windows, east wall 2 windows, west wall 2 windows. Symmetric layout; positions estimated visually.
- **Door healings**: 5 healed (1 on horizontal corridor wall S5; 4 on lower-zone vertical partitions S8/S9 — two doors per sub-zone visible as cyan arcs).
- **Repeatedly null fields**: same as 1F — `thickness_m`, `facade_axis_note`, `world_z_m`; several dimension span `from`/`to` positions null where chain text partially illegible.

---

## Repeatedly null fields (both images)

| Field | Reason |
|---|---|
| `thickness_m` | Plan walls by schema rule: simulation does not need wall thickness |
| `facade_axis_note` | Plans only; elevation-specific field |
| `scale_origin.world_z_m` | Plan — z comes from elevation dimension chains; always null |
| Some `dimensions[].from / .to` | Dimension chain numbers are partially legible at this image resolution; exact terminator positions not always readable |

---

## Schema feedback

1. **Plan window geometry**: The schema uses `x_range_m / y_range_m` for `rect` geometry, which suits elevation windows well. For plan windows on a horizontal perimeter wall (north/south), the window spans x but sits exactly at the wall's y — so `y_range_m` collapses to [y_wall, y_wall]. This is technically correct (it is a line in plan) but feels degenerate. Correction stage may want to record `wall_side` as a separate field or use `p1/p2` geometry for plan windows. No schema change needed from reading stage — just noting.

2. **Dimension chain legibility at this resolution**: The rendered plan at ~1400×900px makes sub-dimension numbers along the chains (especially the denser bottom chain on 1F) difficult to read individually. Several `from`/`to` values are left null. The correction stage has the same JSON and cannot re-read the image — this is flagged as a known gap.

3. **Door swing directionality**: Door swings (cyan arcs) in the decluttered image clearly show the hinge side and swing direction. The reading stage records these as healed wall positions with notes but does not encode which side the door swings toward — that is topology and is left to correction.

4. **1F stair / west entry**: The lower-left corner of 1F has a compound element — a staircase with a stepped outline (stair treads visible as parallel lines), a door arc at the west perimeter, and an adjacent small room. The perimeter wall (S4) was traced as a polyline with a notch to capture the entry recess. The stair treads are excluded and logged.
