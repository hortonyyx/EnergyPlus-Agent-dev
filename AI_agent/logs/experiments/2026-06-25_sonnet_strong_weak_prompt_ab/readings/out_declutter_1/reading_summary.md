# Reading summary — out_declutter_1

## Per-image confidence and tally

| image | walls traced | windows traced | confidence | notes |
|---|---|---|---|---|
| 1f_view | 10 wall strokes | 10 window strokes | medium-high | dimension chain numbers partially legible; y-positions estimated from visual proportion |
| 2f_view | 6 wall strokes | 10 window strokes | medium-high | dimension chain numbers partially legible; furniture-heavy image but furniture excluded cleanly |

## Repeatedly-null fields

- `thickness_m`: null for all plan wall strokes (correct per schema — EP walls have no thickness concept)
- `facade_axis_note`: null for both images (plan images, not elevations)
- `scale_origin.world_z_m`: null for both images (plan images; z comes from elevation chains)
- `dimension_refs`: empty for all `seen` provenance strokes (no dimension-derived strokes)

## Key observations per image

### 1f_view (Floor 1 plan)
- Building footprint: 15.00m (x) × ~9.00m (y) estimated; total x confirmed by "15000" annotation
- Layout: 3 horizontal bands — north rooms (offices), central corridor, south offices + WC
- Interior structure: 2 main horizontal walls (corridor boundaries) + 3 vertical interior walls
- Door healing: west perimeter door (1), north corridor wall (3 openings), south corridor wall (3 openings)
- Windows: 4 on north, 4 on south, 1 on west, 1 on east = 10 total
- Sanitary fixtures visible in SE zone — excluded
- Dimension chain legibility: top chain segments readable (1760/2400/1300 pattern); bottom chain segments partially obscured; left side y-chain partially readable

### 2f_view (Floor 2 plan)
- Same building footprint as F1 (15.00m × ~9.00m)
- Layout: 2 horizontal bands — north conference zone + south office zone; divided left/right by central vertical wall
- Interior structure: 1 horizontal interior wall + 1 central vertical wall (simpler than F1)
- Door healing: 4 openings on horizontal interior wall, 1 on central vertical wall
- Windows: 4 on north, 4 on south, 1 on west, 1 on east = 10 total (same pattern as F1)
- Heavy furniture in both zones (conference tables + office workstations) — all excluded per pen library
- Top dimension chain: 1900/3800/1590/190/3800/950 pattern (partially legible); more legible than F1

## Schema feedback

- The `dimensions[]` array is underspecified when chain segment numbers are partially legible — provenance "seen" but numeric confidence is low; downstream correction should treat these as supporting evidence, not authoritative measurements
- Window positions in plan are recorded as 1D line strokes along the wall (p1/p2 sharing the wall's fixed coordinate); this is the correct representation for plan windows per the pen library
- The decluttered images (furniture removed, dimension chains retained) worked well — wall/window recognition was clean with no furniture-as-wall confusion risk
- Central vertical wall in 2F aligns with the gap between north windows 2 and 3 — this is an expected structural alignment; correction stage should verify
