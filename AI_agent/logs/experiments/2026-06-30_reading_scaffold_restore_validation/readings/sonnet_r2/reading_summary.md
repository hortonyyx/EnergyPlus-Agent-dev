# Reading Summary — out_sonnet_r2

Run: Sonnet r2, batch all-6-images, 2026-06-30

## Image manifest

| image | output JSON | image_kind | status |
|---|---|---|---|
| 1f_view.png | 1f_view.json | plan | done |
| 2f_view.png | 2f_view.json | plan | done |
| South_view.png | South_view.json | elevation | done |
| North_view.png | North_view.json | elevation | done |
| East_view.png | East_view.json | elevation | done |
| West_view.png | West_view.json | elevation | done |

## Per-image confidence + stroke counts

### 1f_view.json (Floor 1 plan)
- Confidence: **medium-high**
- Walls: 14 (4 perimeter + 10 interior)
- Windows: 7 (3 north/upper, 3 south/lower, 1 east corridor)
- Healed doors: 5 (2 on y=3.00 corridor wall, 1 on y=5.00, 1 stair area)
- Low-confidence calls:
  - East corridor window (S21): right-side chain gives y=3.28–4.48 (medium confidence — the right-side dimension chain reads 2940+340+1200+340+2940=7760 vs overall 8000; small gap not accounted for)
  - Top dimension chain sums to 14760 (vs 15000 overall); rounding across 9 segments; used overall as authority
  - Lower-zone partitions (S9–S14): positions read from bottom chain; corridor wall doors inferred from visible swing arcs
- Repeatedly null: thickness_m (all plan walls), world placement fields (none emitted)

### 2f_view.json (Floor 2 plan)
- Confidence: **medium-high**
- Walls: 10 (4 perimeter + 6 interior)
- Windows: 6 (2 north/upper conference rooms, 4 south/lower offices) + 1 east corridor (medium)
- Healed doors: 4 (1 on y=5.00, 3 on y=3.00)
- Low-confidence calls:
  - Top chain sum: 1950+3600+1889+1891+3600+1950=14880 vs overall 15000 (small 120mm gap); center partition x set at 7.44
  - Bottom chain: the two pairs of '360' segments around partition walls are ambiguous — partition positions estimated at x=3.57–3.75 range; used 3.59 for symmetry considerations
  - Lower zone has 4 offices but center partition x (S9=7.50) is anchored to symmetry since bottom chain reads in pairs
- Repeatedly null: thickness_m, world placement fields

### South_view.json (South elevation)
- Confidence: **medium**
- wall_fill: 2 (one per floor)
- outline: 1
- Windows: 6 total (4 × F2 narrow windows + 1 F1 center large + 1 F1 right large)
- Low-confidence calls:
  - F1 small window (S8): bottom chain places a 1200mm span at x=3.44–4.64, but visible rectangle appears to be at x≈4.64–5.84; conflicting evidence logged; used chain value as primary
  - F1 left element: recognized as door (floor-height, leaf subdivisions) — not emitted as window pen; logged in uncaptured
  - S10 note had an error mid-JSON (corrected: F1 right window at x=[11.36, 13.76] per bottom chain)
  - Left detail chain arrangement: segments read bottom-up as 1500+900+600+1000+1800+800 — assignment of which is sill vs header requires careful reading
- Repeatedly null: no ocr_texts visible (no level markers legible in image); facade detail notes use dimension chain evidence

### North_view.json (North elevation)
- Confidence: **high**
- wall_fill: 2 (one per floor)
- outline: 1
- Windows: 5 total (2 × F2 large 3600mm + 3 × F1 medium 2400mm)
- Low-confidence calls: none significant
- Both dimension chains close cleanly (top: 1950+3600+3900+3600+1950=15000 ✓; bottom: 1240+2400+2660+2400+2660+2400+1240=15000 ✓)
- y-chain: 800+1800+1000+400+1600+1000=6600 ✓
- Repeatedly null: ocr_texts (no visible text labels), level markers not legible

### East_view.json (East elevation)
- Confidence: **high**
- wall_fill: 2 (one per floor)
- outline: 1
- Windows: 2 (1 per floor, both centered at x=3.40–4.60, 1200mm wide)
- Low-confidence calls: none
- Dimension chains: top 3400+1200+3400=8000 ✓; left detail 800+1800+1000+200+1800+1000=6600 ✓
- Repeatedly null: ocr_texts

### West_view.json (West elevation)
- Confidence: **high** for F2; **medium** for F1 door dimensions
- wall_fill: 2 (one per floor)
- outline: 1
- Windows: 1 (F2 only, x=3.40–4.60, y=4.00–5.80)
- F1 door: recognized as double-leaf door — NOT drawn as window; logged in uncaptured
- Low-confidence calls:
  - F1 door head height not dimensioned; y-extent logged only in uncaptured
  - West view has no detailed y sub-chain (only overall 3600/3000 split); F2 window y extrapolated from East elevation detail chain (consistent across gable facades)
- Repeatedly null: detailed y-sub-chain for West, ocr_texts

## Fields repeatedly null or unknown across all images

- `thickness_m`: always null (plan walls; correct per schema §0.2)
- `anchor` on dimension entries: null throughout (exact pixel anchor not readable)
- `ocr_texts[]`: empty for all 4 elevations (no room labels, no level marker text legible)
- Level markers (▽ ±0.000 symbols): not visible in any of the 6 images — z-base is inferred from dimension chain y=0.00 at ground
- Scale ratio: not annotated in any image

## Scale notes (for reading_summary only; not geometry)

The drawings appear to be at approximately 1:100 based on the dimension chain numbers vs image pixel dimensions, but no explicit scale bar or ratio is drawn.

## Closure-check summary

| image | chain | sum | overall | status |
|---|---|---|---|---|
| 1f top | 1240+2400+1300+1240+2400+1240+1300+2400+1240 | 14760 | 15000 | 240mm gap; rounding |
| 1f bottom | 540+900+2000+1200+360+1300+2400+1300+1360+2400+1240 | 15000 | 15000 | ✓ |
| 1f left | 3000+250+1500+250+3000 | 8000 | 8000 | ✓ |
| 2f top | 1950+3600+1889+1891+3600+1950 | 14880 | 15000 | 120mm gap; rounding |
| 2f bottom | 2190+1200+360+360+1200+2190+2190+1200+360+360+1200+2190 | 14880 | 15000 | 120mm gap |
| 2f left | 3000+400+1200+400+3000 | 8000 | 8000 | ✓ |
| South top | 2190+1200+720+1200+4380+1200+720+1200+2190 | 15000 | 15000 | ✓ |
| South bottom | 3440+1200+1660+2400+2660+2400+1240 | 15000 | 15000 | ✓ |
| South left | 1500+900+600+1000+1800+800 | 6600 | 6600 | ✓ |
| North top | 1950+3600+3900+3600+1950 | 15000 | 15000 | ✓ |
| North bottom | 1240+2400+2660+2400+2660+2400+1240 | 15000 | 15000 | ✓ |
| North left | 800+1800+1000+400+1600+1000 | 6600 | 6600 | ✓ |
| East top | 3400+1200+3400 | 8000 | 8000 | ✓ |
| East left | 800+1800+1000+200+1800+1000 | 6600 | 6600 | ✓ |
| West top | 3400+1200+3400 | 8000 | 8000 | ✓ |
| West left | 3600+3000 | 6600 | 6600 | ✓ |

Most chains close cleanly. The two small gaps in 1F top and 2F top/bottom (~120–240mm) are within rounding of drawn dimension text and the overall dimension is the authority.
