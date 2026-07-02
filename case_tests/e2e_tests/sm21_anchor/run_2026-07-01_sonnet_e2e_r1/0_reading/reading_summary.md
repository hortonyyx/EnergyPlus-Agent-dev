# Reading Summary — sm21_anchor run_2026-07-01_sonnet_e2e_r1

## Run metadata

- Case: sm21_anchor (2-floor office, Shenzhen, 240m², 7 thermal zones/floor per testdata)
- Run: run_2026-07-01_sonnet_e2e_r1
- Model: claude-sonnet-4-6 (isolated cold-start, no GT/prior-run access)
- Date: 2026-07-01

---

## Image manifest

| source PNG | output JSON | image_kind | status |
|---|---|---|---|
| 1f_view.png | 0_reading/1f_view.json | plan | done |
| 2f_view.png | 0_reading/2f_view.json | plan | done |
| North_view.png | 0_reading/North_view.json | elevation | done |
| South_view.png | 0_reading/South_view.json | elevation | done |
| East_view.png | 0_reading/East_view.json | elevation | done |
| West_view.png | 0_reading/West_view.json | elevation | done |

---

## Per-image confidence self-assessment

### 1f_view.json — MEDIUM-HIGH

**Confidence: medium-high**

What was clear:
- Outer perimeter 15.00m × 8.00m: high confidence (top and bottom overall 15000 chain, left 8000 chain all consistent)
- 2 horizontal internal walls at y=3.00 and y=5.00: high confidence (left y-chain 3000+250+1500+250+3000=8000)
- 2 vertical internal walls at x=5.00 and x=10.00: high confidence (bottom chain cumulative confirms x=5000 and x=10000)
- Windows in north wall (3) and south wall (complex): traced with medium-high confidence; positions derived from dimension chains

What was uncertain:
- Top x-chain segment sum = 14760 vs overall 15000 — 240mm discrepancy; one segment likely misread; transcribed verbatim
- Right y-chain sum = 7760 vs 8000 — same 240mm discrepancy; outer wall thickness effect or misread
- Door positions: west perimeter door confirmed by swing arc in plan; corridor door positions estimated from arc positions (not individually dimensioned)
- Lower zone interior partitions (y=0 to 3.0): confirmed at x=5.00 and x=10.00; the WC/bathroom room on the right appears to not have an additional internal wall beyond x=10.00 — only the perimeter
- South wall windows: 5 window positions derived from bottom chain; positions S16 vs S17 boundary needed careful re-calculation (corrected inline)
- Multiple "240" interior annotations may be door-frame offsets or jamb dimensions — logged as dimensions, not structural walls

### 2f_view.json — MEDIUM-HIGH

**Confidence: medium-high**

What was clear:
- Same outer footprint 15.00×8.00m: high confidence
- Horizontal internal walls at y=3.00 and y=5.00: high confidence (left y-chain 3000+400+1200+400=8000 ✓)
- Central vertical wall in upper zone at x≈7.44: high confidence from top chain (1950+3600+1889=7439)
- 4 vertical internal walls in lower zone at x=3.75, x=7.50, x=11.25: high confidence from bottom chain (sums to 15000 ✓)
- Windows in north wall (2 large) and south wall (4 × 1200mm): high confidence from dimension chains

What was uncertain:
- Top chain sum = 14880 vs 15000 (120mm discrepancy); one value may be slightly off; transcribed verbatim
- Upper zone center wall position: x=7.44 (from 1889+1891 center) vs x=7.50 (symmetric center of 15m); slight ambiguity
- F2 has narrower corridor (1200mm net) vs F1's 1500mm net — confirmed from left y-chains

### North_view.json — HIGH

**Confidence: high**

What was clear:
- Facade width 15.00m, height 6.60m: both top and bottom chains sum to 15000 ✓; left/right outer = 6600 ✓
- Floor split: F1=3000mm, F2=3600mm: confirmed from both outer and inner chains
- F2: 2 windows × 3600mm wide, y=[4.00, 5.80]: clean chain derivation (800+1800+1000=3600 for F2 ✓)
- F1: 3 windows × 2400mm wide, y=[1.00, 2.60]: confirmed from bottom chain; inner chain: 1000+1600+400 (F1 sub from bottom = 1000 sill + 1600 height + 400 spandrel, then read remaining F2 chain: 1000+1800+800=3600 ✓)
- Both x-chains sum to 15000 ✓; inner y-chain sums to 6600 ✓ — North is the cleanest elevation

What was uncertain:
- No text labels visible; no level markers with ±0.000 triangles visible

### South_view.json — MEDIUM

**Confidence: medium**

What was clear:
- Facade width 15.00m, height 6.60m: confirmed (top chain sum 15000 ✓, bottom chain sum 15000 ✓)
- Floor split: F1=3000, F2=3600 from outer chains ✓
- F2: 4 windows (2 pairs × 1200mm each), x positions clean from top chain
- F2 window y-range: left inner chain gives 800+1800+1000=3600 ✓ → y=[4.00, 5.80]

What was uncertain:
- South F1 window heights: left inner chain gives 600+900+1500=3000 ✓ → y=[1.50, 2.40] (height=900mm, sill=1500mm); but right inner chain gives different numbers (800+1800+400+1000+1600+1000) which don't match South F1. Right inner annotates East facade windows perhaps. Used left inner chain as authoritative for south F1.
- F1 small window (S7): within 1200mm bottom-chain span x=[3.44, 4.64]; exact sub-position not further dimensioned; placed at the span limits (medium confidence)
- Door in F1: recognized from floor-height leaf visible at approximately x=0.24 to x≈1.14 in west area of south facade; not dimensioned in bottom chain (included in 3440mm first segment); healed in wall_fill
- Right inner y-chain sub-total for F1 (1000+1600+1000=3600) does not match F1 height (3000) — likely cross-referencing East facade windows; flagged

### East_view.json — HIGH

**Confidence: high**

What was clear:
- Facade width 8.00m, height 6.60m: top and bottom chains both = 8000 ✓
- Floor split: F1=3000, F2=3600 ✓
- x-chain: 3400+1200+3400=8000 ✓; both windows centered at x=[3.40, 4.60]
- Inner y-chain: 800+1800+1000+200+1800+1000=6600 ✓ — clean, complete
- F2 window y=[4.00, 5.80]; F1 window y=[1.00, 2.80]; both derived without ambiguity
- Only 1 window per floor, no doors on east facade

What was uncertain:
- Nothing significant; East is the cleanest elevation

### West_view.json — MEDIUM

**Confidence: medium**

What was clear:
- Facade width 8.00m, height 6.60m: top and bottom chains both = 8000 ✓
- x-chain: 3400+1200+3400=8000 ✓
- F2: 1 window at x=[3.40, 4.60], y=[4.00, 5.80] (estimated from cross-elevation consistency)
- F1: 1 double door (floor-height) at x=[3.40, 4.60]; healed in wall_fill; NOT traced as window

What was uncertain:
- No inner sub-dimension chain for window heights on west facade — F2 window y-range estimated from cross-elevation consistency with East/North (1800mm height, 1000mm sill); marked as estimated
- Left inner chain shows "3000" for both F2 and F1 zones — the F2 "3000" is inconsistent with the structural F2 height of 3600mm from right chain; likely showing interior clear height; transcribed verbatim
- West F1 door exact y-extent not dimensioned; floor-height door assumed; healed, not traced

---

## Fields repeatedly left null

| field | images affected | reason |
|---|---|---|
| `thickness_m` | all plan walls | EP simulation does not use wall thickness; schema rule |
| `facade` | 1f_view, 2f_view | plan images; facade block is null for plans per schema |
| level markers (▽ ±0.000) | all elevations | no explicit ±0.000 triangle/datum text visible in any elevation image; height info came only from dimension chains |
| `anchor` | all dimensions | pixel anchor coords not recorded; not required for this trace |

---

## Dimension chain cross-checks

| chain | image | sum | expected | status |
|---|---|---|---|---|
| top x | 1f_view | 14760 | 15000 | FAIL -240 (transcribed verbatim) |
| bottom x | 1f_view | 15000 | 15000 | ✓ |
| left y | 1f_view | 8000 | 8000 | ✓ |
| right y | 1f_view | 7760 | 8000 | FAIL -240 |
| top x | 2f_view | 14880 | 15000 | FAIL -120 |
| bottom x | 2f_view | 15000 | 15000 | ✓ |
| left y | 2f_view | 8000 | 8000 | ✓ |
| top x | North_view | 15000 | 15000 | ✓ |
| bottom x | North_view | 15000 | 15000 | ✓ |
| inner y (N) | North_view | 6600 | 6600 | ✓ |
| top x | South_view | 15000 | 15000 | ✓ |
| bottom x | South_view | 15000 | 15000 | ✓ |
| left inner y | South_view | 6600 | 6600 | ✓ |
| right inner y | South_view | 6600 | 6600 | ✓ (but F1 sub contradicts facade) |
| top/bottom x | East_view | 8000 | 8000 | ✓ |
| inner y (E) | East_view | 6600 | 6600 | ✓ |
| top/bottom x | West_view | 8000 | 8000 | ✓ |

---

## Thermal zone count cross-check

testdata_prompt.json states: 7 thermal zones per floor.

From plan traces:
- 1F: outer perimeter + 2 horizontal corridor walls + 2 vertical walls in upper zone + 2 vertical walls in lower zone → visually: 3 upper offices + corridor zone + 3 lower rooms (incl. WC/bathroom) = 7 zones. Count consistent with testdata.
- 2F: outer perimeter + 2 horizontal corridor walls + 1 central upper wall + 3 lower zone walls → visually: 2 conference rooms (upper) + corridor zone + 4 lower offices = 7 zones. Count consistent with testdata.

---

## Schema feedback

1. The `dimension_refs` field is a free-text array in schema; it would benefit from a formal ID reference constraint (currently I used chain/segment IDs as ad-hoc strings matching the `dimensions[].id` field).

2. For elevations, `wall_fill` as a single full-width rect per floor is clean but the schema could explicitly note that "windows overlay wall_fill" (not break it unless they fully span the fill height) — the current pen library §3 says "when windows merely overlay the fill (no break), keep one fill per floor" which I followed, but it required careful reading.

3. The `facade.local_x_positive` field with value `"image_left_to_right"` for all four facades is correct per the schema (purely in-image) but may be confusing downstream since e.g. the West elevation's local-left-to-right doesn't correspond to the same world direction as the East elevation's left-to-right. The correction stage will need to handle this — no issue with the reading-stage output.

4. Some "240" interior annotations on the plan appear near internal wall positions and may be door-frame or finish offsets. These were logged as dimension entries rather than structural walls, which is the correct call but makes the dimension array larger than necessary. A dedicated `interior_annotations` sub-field might reduce noise.
