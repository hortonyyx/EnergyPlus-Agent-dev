# Reading Summary — sm21_anchor run_2026-07-01_sonnet_e2e_r2

**Run:** r2 independent re-sample (automated, no pilot review gate)
**Model:** claude-sonnet-4-6
**Date:** 2026-07-01
**Images processed:** 6 / 6

---

## Image manifest

| source PNG | output JSON | image_kind | status |
|---|---|---|---|
| `1f_view.png` | `0_reading/1f_view.json` | plan | done |
| `2f_view.png` | `0_reading/2f_view.json` | plan | done |
| `North_view.png` | `0_reading/North_view.json` | elevation | done |
| `South_view.png` | `0_reading/South_view.json` | elevation | done |
| `East_view.png` | `0_reading/East_view.json` | elevation | done |
| `West_view.png` | `0_reading/West_view.json` | elevation | done |

---

## Per-image confidence self-assessment

### 1f_view.json — Floor 1 plan
**Confidence: medium**

- Building perimeter 15000×8000mm: **high** — outer dim chains verified.
- Horizontal interior walls at y=3.0 and y=5.0: **high** — left dim chain 3000+250+1500+250+3000=8000 ✓.
- Vertical interior walls at x=5.0 and x=10.0: **high** — bottom dim chain arithmetic confirms.
- South windows W1–W3: **high** — cyan strips visible; positions from bottom dim chain (verified sum=15000).
- North windows W4–W6: **medium** — top sub-chain segments do NOT sum cleanly to 15000 (apparent sum ≈15800). Window positions estimated by matching 2400mm window widths from the chain. Correction should re-verify.
- Door positions on interior walls S5 and S6: **low** — visual arc positions only (estimated x≈2.5, 7.5, 12.5); no explicit dimension.
- Room count: 6 rooms + 1 corridor = 7 zones matches testdata `thermal_zones: 7` for floor 1. ✓

**Key uncertainty:** Top sub-chain does not close (apparent over-count). Likely one of the "1240" or "1300" labels in the top chain is misread. The north window positions (S14–S16) are **medium confidence** — correction should reconcile with plan geometry.

---

### 2f_view.json — Floor 2 plan
**Confidence: medium**

- Building perimeter 15000×8000mm: **high**.
- Y-zone boundaries y=3.0, y=5.0: **high** — left dim 3000+400+1200+400+3000=8000 ✓.
- South office walls at x=3.75, x=7.5, x=11.25: **high** — bottom dim 2×(2190+1200+720+1200+2190)=2×7500=15000 ✓.
- Conference room divider at x=7.5: **high** — single wall in upper zone.
- South office windows W1–W4 (each 1200mm wide): **high** — from bottom dim chain.
- North conference windows W5–W6 (each 3600mm wide): **medium** — top chain sums to 14880mm not 15000mm; 1889/1891 values may be misread (possibly 1950 each). Window positions flagged.
- Windows S17/S18 on west/east face of north zone: **low** — cyan strips visible but no explicit x-dimension chain for these lateral openings.
- Room count: 4 offices + 1 corridor + 2 conference rooms = 7 zones matches testdata ✓.

**Key uncertainty:** Top x-chain mismatch (~14880 vs 15000). Correction should verify 2F north window x-positions.

---

### North_view.json — North elevation
**Confidence: high**

- All dimension chains close: top chain 1950+3600+3900+3600+1950=15000 ✓; bottom chain 1240+2400+2660+2400+2660+2400+1240=15000 ✓; both floor heights 3000+3600=6600 ✓; F1 inner 1000+1600+400=3000 ✓; F2 inner 1000+1800+800=3600 ✓.
- Window counts: F1=3 windows (2400mm wide, sill=1.0m, height=1.6m), F2=2 windows (3600mm wide, sill=1.0m, height=1.8m).
- All window rects well-constrained by two independent dim chains (x from horizontal, y from vertical inner).
- No doors, no ambiguous elements.

**Lowest uncertainty of all 6 images.**

---

### South_view.json — South elevation
**Confidence: medium**

- Top x-chain (F2 windows): verified sum=2.19+1.2+0.72+1.2+4.38+1.2+0.72+1.2+2.19=15.00 ✓.
- Bottom x-chain (F1 features): verified sum=3.44+1.2+1.66+2.4+2.66+2.4+1.24=15.00 ✓.
- Floor heights 3000+3600=6600 ✓; F1 inner 1.5+0.9+0.6=3.0 ✓; F2 inner 1.0+1.8+0.8=3.6 ✓.
- F2 windows W1–W4 (4 windows at 1200mm each): **high**.
- F1 windows W5–W6 (2 windows at 2400mm): **high** — but sill height 1500mm is unusually high; accepted as-read.
- South F1 door at x=[3.44, 4.64]: **high** — door leaf panels clearly visible; logged in uncaptured.
- S9 (small element at x≈[4.64, 5.64]): **low** — possibly a ventilation window within the 1660mm gap; no explicit dimension; included as estimated stroke with low confidence.
- Right-side inner y-chain: **low** — multiple ambiguous sub-values visible that do not cleanly map; flagged.

**Key uncertainty:** S9 small element; right inner chain ambiguity; South F1 window sill at 1500mm is high (verify vs gt).

---

### East_view.json — East elevation
**Confidence: high**

- X-chain 3400+1200+3400=8000 ✓; floor heights 3000+3600=6600 ✓.
- F1 inner 1000+1800+200=3000 ✓; F2 inner 1000+1800+800=3600 ✓.
- 1 window per floor, both at x=[3.40, 4.60].
- No doors, decoration, or ambiguous elements.
- Only concern: F1 top spandrel = 200mm (very thin); accepted as-read.

---

### West_view.json — West elevation
**Confidence: medium-high**

- X-chain 3400+1200+3400=8000 ✓; floor heights 3000+3600=6600 ✓.
- F2 inner 1000+1800+800=3600 ✓.
- F2 window at x=[3.40, 4.60]: **high**.
- F1 West door (double-door, building entry): **high** recognition, door logged in uncaptured.
- F1 door height: **low** — no explicit sub-dimension visible; estimated ~2400mm.
- No F1 window on West facade (only door).

---

## Fields repeatedly left null or unknown

| field | images affected | reason |
|---|---|---|
| `thickness_m` | 1f, 2f (all wall strokes) | EP simulation does not use wall thickness; schema requires null |
| `facade` | 1f, 2f | plan image kind; facade block not applicable |
| `anchor` | all | no pixel anchor provided |
| `ocr_texts` | North, East, West, South | no readable room-name / text labels in elevation images |
| level markers (▽) | all elevations | no level marker symbols visible in any elevation image |
| door height (explicit) | West F1 | no sub-dimension chain for door height visible |

---

## Schema feedback

1. **Top dim chain closure:** The 1F plan top dim chain segments do not sum to 15000 as read; the disagreement likely comes from misreading one or two small numbers in the dark image (some ticks are very close together). The redundant-channel discipline helps: the bottom chain is clean and confirmed. Correction should use the bottom chain as the definitive source for 1F plan x-positions, and treat north windows as aligned with south windows by plan symmetry.

2. **S9 in South elevation:** A small element at x≈[4.64, 5.64] in F1 South is included with `provenance: estimated` and `confidence: low`. It falls in the undimensioned 1660mm gap and may be a door sidelight. Correction should discard it if not confirmed by plan or gt.

3. **2F top chain 14880 ≠ 15000:** The two middle segments (1889+1891=3780) should probably be 1950+1950=3900. All conference window positions derived from this chain are flagged as medium confidence. The 3600mm window widths themselves appear clean.

4. **South F1 window sill = 1500mm:** This is higher than typical office windows (normally 900–1000mm). Accepted as-read but flagged; correction should verify this value against gt.

5. **Right side inner chain on South elevation:** Multiple small segment values visible on the right inner chain that do not match the left inner chain cleanly. This likely reflects wall-thickness sub-segments being interspersed with window height dimensions. The left chain was used as primary; right chain segments included with low-confidence flag.

---

## Testdata cross-check

| item | testdata | read |
|---|---|---|
| Number of floors | 2 | 2 ✓ |
| Building footprint | 240m² implied | 15.0×8.0=120m² per floor, 2 floors = 240m² ✓ |
| Thermal zones F1 | 7 | 6 rooms + 1 corridor = 7 ✓ |
| Thermal zones F2 | 7 | 4 offices + 1 corridor + 2 conference = 7 ✓ |
| F1 height | — | 3000mm (from all 4 elevations consistent) |
| F2 height | — | 3600mm (from all 4 elevations consistent) |
| Total height | — | 6600mm |
