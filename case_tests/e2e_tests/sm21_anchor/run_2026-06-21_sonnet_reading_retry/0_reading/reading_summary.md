# Reading Summary — sm21_anchor run_2026-06-21_sonnet_reading_retry

Run date: 2026-06-21
Model: claude-sonnet-4-6
Images read: 6 (2 plans + 4 elevations)

---

## Per-image confidence

| Image | Confidence | Notes |
|---|---|---|
| 1f_view.json | Medium | Perimeter walls high confidence. Interior partition x-positions derived from dim chains and cross-checked (bottom chain sums to 15000 ✓). Top chain has 760 mm discrepancy — one segment value uncertain. East wall window y-range estimated from right-side sub-dims only. Furniture/door swings excluded and logged. |
| 2f_view.json | Medium | Perimeter walls high confidence. North conference room divider x position uncertain (1889+1891 mid-span; total ≠ 15000 by ~120 mm). South office partitions placed at x=3.75, 7.50, 11.25 from bottom chain; bottom chain has ~200 mm running discrepancy. West/east wall window positions estimated from side sub-dims. |
| South_view.json | Medium-High | Top chain sums to 15000 ✓. Bottom chain sums to 15000 ✓. F2 window height discrepancy: left side says 1800, right side says 1600 — both transcribed. F1 door opening at x=0 captured as window pen opening (no door pen in elevation). F1 large window x-ranges on right half estimated. |
| North_view.json | High | Top chain sums to 15000 ✓. Bottom chain sums to 15000 ✓. Height chains internally consistent. 3 F1 windows + 2 F2 windows well-defined. No door visible. Cleanest elevation to read. |
| East_view.json | High | Top chain sums to 8000 ✓. Both height chains consistent. One window per floor, both centered at x=[3.40, 4.60]. No door visible. |
| West_view.json | Medium | Top chain sums to 8000 ✓. F2 window same as east. F1 has a door (double-leaf visible) — no elevation door pen; captured as window pen opening per pen_library rule; correction stage must classify. Door exact top height not dimensioned — estimated ~2.55 m from pixel proportion. |

---

## Repeatedly null fields

- `thickness_m` — null on all plan wall strokes (by spec: EP simulation does not use wall thickness)
- `world_z_m` — null on all plan scale_origin entries (z comes from elevation dim chains, not plans)
- `world_x_m` / `world_y_m` — set to null or 0.00 as applicable; elevation scale_origin world positions not directly readable from the elevation image alone
- `ocr_texts` — empty on all 6 images; no room-name labels, no text annotations visible in any image (rooms identified by furniture layout in plans; elevations have no text labels)
- level markers (▽ symbols) — not visible in any image; z-heights read from dimension chains only

---

## Dimension chain sum checks

| Image | Chain | Segments | Sum | Expected | Pass? |
|---|---|---|---|---|---|
| 1f top | x | 1240+2400+1300+1240+2400+1240+1300+2400+1240 | 15760 | 15000 | FAIL (760 mm discrepancy — one seg likely misread) |
| 1f bottom | x | 540+900+2000+1200+360+1300+2400+1300+1360+2400+1240 | 15000 | 15000 | PASS |
| 1f left | y | 3000+1500+250+250+3000 | 8000 | 8000 | PASS |
| 2f top | x | 1950+3600+1889+1891+3600+1950 | 14880 | 15000 | FAIL (120 mm — D4/D5 uncertain) |
| 2f bottom | x | 2190+1200+360+560+1200+2190+... (×2 symmetry) | ~15400 | 15000 | FAIL (~400 mm — segments D23/D24 uncertain) |
| 2f left | y | 3000+1200+400+400+3000 | 8000 | 8000 | PASS |
| South top | x | 2190+1200+720+1200+4380+1200+720+1200+2190 | 15000 | 15000 | PASS |
| South bottom | x | 3440+1200+1660+2400+2660+2400+1240 | 15000 | 15000 | PASS |
| South F2 left | z | 800+1800+1000 | 3600 | 3600 | PASS |
| South F1 left | z | 600+900+1500 | 3000 | 3000 | PASS |
| North top | x | 1950+3600+3900+3600+1950 | 15000 | 15000 | PASS |
| North bottom | x | 1240+2400+2660+2400+2660+2400+1240 | 15000 | 15000 | PASS |
| North F2 left | z | 800+1800+1000 | 3600 | 3600 | PASS |
| North F1 left | z | 400+1600+1000 | 3000 | 3000 | PASS |
| East top | x | 3400+1200+3400 | 8000 | 8000 | PASS |
| East F2 | z | 800+1800+1000 | 3600 | 3600 | PASS |
| East F1 | z | 200+1800+1000 | 3000 | 3000 | PASS |
| West top | x | 3400+1200+3400 | 8000 | 8000 | PASS |
| West F2 | z | 800+1800+1000 | 3600 | 3600 | PASS |

---

## Schema feedback

1. **Top chain discrepancy (1f)**: The 9-segment top chain sums to 15760 instead of 15000. Segment D7 (read as "1240") may actually be "880" based on the 760 mm gap. The bottom chain (11 segments) sums correctly to 15000 and is more reliable. Correction stage should use bottom chain for partition x-positions on F1.

2. **2f top chain discrepancy**: Segments labeled 1889 and 1891 likely result from a slight misread (could both be 1890, or the center gap could be 3780 total). The bottom chain values are also slightly over; recommend correction stage cross-checks with F2 plan window positions.

3. **West F1 door in elevation**: The pen_library says elevation doors = "not drawn (note only)". However, the opening visually breaks wall_fill. This reading captured it as a `window` pen stroke with a clear note flagging it as a door for the correction stage. Schema could benefit from an explicit "door_opening" marker for elevations that doesn't require the window pen workaround.

4. **South F2 window height inconsistency**: Left sub-chain gives window height = 1800 mm; right sub-chain gives 1600 mm. Both are transcribed. The left-side chain (3600 F2 total, 800+1800+1000=3600) checks out; the right-side chain may include a decorative band or thicker lintel. Correction stage should use 1800 mm (left chain consistent with North facade's same 1800 F2 window height).

5. **No OCR text in any image**: All 6 images have no visible room-name labels or other text annotations. `ocr_texts` arrays are empty throughout. This may indicate a drawing style that uses furniture symbols rather than text to identify room types.

6. **Scale note**: No scale bar or ratio text was visible in any of the 6 images. Scale was inferred from dimension chains alone (all values in mm).
