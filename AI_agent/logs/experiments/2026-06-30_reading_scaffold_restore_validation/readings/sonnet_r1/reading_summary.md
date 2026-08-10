# Reading summary — out_sonnet_r1

Run: 2026-06-30, Sonnet 4.6, batch (all 6 images)

---

## Per-image summary

### 1f_view.json — Floor 1 plan
- **Confidence**: medium-high overall
- **Walls traced**: 11 strokes (S1–S11)
  - 5 perimeter walls (south, east, north, west upper, west lower; west corridor segment S5a also traced = 6 perimeter segments)
  - 2 horizontal internal walls (corridor at y=3.00 and y=5.00)
  - 2 vertical internal walls in south zone (x=5.00, x=10.00) — dimension_derived, high confidence
  - 2 vertical internal walls in north zone (x≈4.94, x≈9.82) — dimension_derived, medium confidence
- **Windows traced**: 7 (4 north wall, 3 south wall); no east or west windows visible in plan (perimeter walls solid there)
- **Doors**: 6+ door openings healed into continuous walls; all logged in uncaptured
- **Low-confidence calls**:
  - North zone vertical wall x-positions (S10, S11): derived from top dimension chain gap boundaries (1300mm spans), exact centerline uncertain; top chain sums to 14760 not 15000 (240mm discrepancy)
  - South wall windows (S16–S18): medium confidence — derived from bottom chain, but bottom chain has a SW recess (540+900 before first window)
  - West corridor entrance: unclear if it is a door or open span; door arc visible → healed as door (S5a)
- **Repeatedly null fields**: `thickness_m` (all walls), `anchor` (all dimensions)

### 2f_view.json — Floor 2 plan
- **Confidence**: medium overall
- **Walls traced**: 10 strokes (S1–S10)
  - 4 perimeter walls (south, east, north, west — full spans, no exterior notches)
  - 2 horizontal internal walls (y=3.00 and y=5.00, corridor same as 1F)
  - 1 vertical internal wall in north zone (x≈7.50, center — two conference rooms)
  - 3 vertical internal walls in south zone (x≈3.75, x≈7.50, x≈11.25 — four office bays)
- **Windows traced**: 6 (2 north wall F2, 4 south wall F2)
- **Doors**: 4+ door openings healed; logged in uncaptured
- **Low-confidence calls**:
  - Bottom dimension chain: crowded text in center positions (reads as "36660" or "360 60" in two locations); south wall window x-positions have only medium confidence; total Σ of bottom chain ≈ 14400–15000 inconsistently
  - South zone vertical wall positions: visual estimates only (x≈3.75, 7.50, 11.25) — no reliable dimension derivation due to crowded chain
  - Top chain sums to 14880 not 15000 (~120mm discrepancy)
- **Repeatedly null fields**: `thickness_m`, `anchor`

### South_view.json — South elevation
- **Confidence**: high overall
- **Strokes**: 2 wall_fill + 6 windows + 1 outline = 9 strokes
  - F2: 4 windows (two pairs of 1200mm windows with 720mm gap between each pair)
  - F1: 1 small clerestory window + 2 large windows (plus 1 door — not traced, in uncaptured)
- **Dimension closure**: top chain 15000 ✓ (Σ=15000), bottom chain 15000 ✓ (Σ=15000), vertical chains 6600 ✓, F2 inner 3600 ✓, F1 inner chains 3000 ✓
- **Low-confidence calls**:
  - F1 small window (S7): x position and width estimated visually within the 1660mm gap zone; not dimensioned in bottom chain; width ~400mm is a guess
  - Left vs right F1 inner vertical chains give different window heights (left: sill=1500,h=900 for small window; right: sill=1000,h=1600 for large windows) — interpreted as applying to different windows
- **Repeatedly null fields**: `anchor`, `ocr_texts` (empty)

### North_view.json — North elevation
- **Confidence**: high overall
- **Strokes**: 2 wall_fill + 5 windows + 1 outline = 8 strokes
  - F2: 2 large windows (3600mm wide each)
  - F1: 3 windows (2400mm wide each, evenly spaced)
- **Dimension closure**: top chain 15000 ✓, bottom chain 15000 ✓, vertical chains 6600 ✓
- **Low-confidence calls**:
  - Right inner vertical chain: reads 340+1200+340+... which doesn't cleanly sum like the left chain (800+1800+1000); left chain used as primary for window y coordinates
- **Repeatedly null fields**: `anchor`, `ocr_texts` (empty)

### East_view.json — East elevation
- **Confidence**: high
- **Strokes**: 2 wall_fill + 2 windows + 1 outline = 5 strokes
  - F2: 1 centered window (1200mm wide)
  - F1: 1 centered window (1200mm wide, height 1800mm — taller than South/North F1 windows)
- **Dimension closure**: top chain 8000 ✓, all vertical chains ✓
- **Low-confidence calls**: none significant
- **Notes**: F1 window height 1800mm (vs 1600mm on South/North); head dimension = only 200mm (very narrow); recorded as-read

### West_view.json — West elevation
- **Confidence**: high for F2 window; medium for F1 (door interpretation)
- **Strokes**: 2 wall_fill + 1 window + 1 outline = 4 strokes
  - F2: 1 centered window (1200mm wide, same position as East F2)
  - F1: door at x=[3.40,4.60] — recognized as double-leaf glazed door; NOT traced as window per pen_library rule; logged in uncaptured
- **Dimension closure**: top chain 8000 ✓, vertical chains 6600 ✓
- **Low-confidence calls**:
  - F1 element identification: the element has window-like glazing but is floor-height with double-panel door frame — classified as door; if correction stage disagrees it can re-read

---

## Cross-check against testdata_prompt.json

- Building: Office, Shenzhen, 240m², 2 floors, 7 thermal zones per floor (14 total)
- Footprint from plans: 15.00m × 8.00m = 120m² per floor × 2 = 240m² ✓
- Floor heights from elevations: F1=3.00m, F2=3.60m, total=6.60m ✓
- Zone count per floor: 7 (from 3 north offices + corridor + 3 south rooms = 7 per floor) — consistent with plan reading

---

## Repeatedly null / unknown fields

- `thickness_m`: all plan walls — always null per schema (EP simulation does not use wall thickness)
- `anchor`: all dimension entries — image-level pixel positions not recorded
- `ocr_texts`: empty for all elevation images (no visible room labels or text annotations)
- Scale: not visible in any image (no "1:N" ratio or graphic scale bar found)
- North arrow: not visible in plan images

## Schema feedback

- The top dimension chain in 1F (north wall) sums to 14760 not 15000 — this is a consistent 240mm discrepancy likely from measuring between inner faces of walls (not centerlines); the correction stage should be aware that chain endpoints may be offset by 120mm from the perimeter centerline on each side.
- The 2F bottom dimension chain has crowded overlapping text in the center that was difficult to read; OCR accuracy there is low and correction stage should cross-reference with South elevation window positions for the south-facing windows.
- The South elevation F1 has a small high window (sill=1500mm) that does not appear in a clean dimension chain segment — only inferrable from the left inner vertical chain. This window may be a toilet/utility room window and its x position is uncertain.
- West F1 has a glazed door (not window) — the pen_library rule is clear, but the correction stage should note that this opening contributes to infiltration/envelope modeling even if not a window sub-face in EP.
