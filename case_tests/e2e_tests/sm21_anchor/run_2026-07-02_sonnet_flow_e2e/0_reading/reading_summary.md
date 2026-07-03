# Reading-stage summary — sm21_anchor (run 2026-07-02_sonnet_flow_e2e)

Reader: Claude (Sonnet-class), reading stage only. Strict isolation kept: only the 6 case_data PNGs +
`testdata_prompt.json` + the three 0_reading skill docs + the smalloffice_20 worked-example JSON (style
anchor) were opened. No gt, no other run dir, no attempts/checks/judge files, no pipeline/EP tools.

All coordinates were read by direct pixel tracing (gray = wall body, cyan = window/door, white =
elevation outline/storey line, green = dimension chains) and cross-checked against the transcribed
dimension chains. Building envelope from testdata: 15.0 m × 8.0 m footprint, 2 floors, 7 thermal zones
per floor.

## Image manifest (this case has exactly 6 images; the kickoff's 3f / supp / section rows deleted)

| source PNG | output JSON | image_kind | status |
|---|---|---|---|
| `1f_view.png` | `0_reading/1f_view.json` | plan | done (pilot, approved) |
| `2f_view.png` | `0_reading/2f_view.json` | plan | done |
| `South_view.png` | `0_reading/South_view.json` | elevation | done |
| `North_view.png` | `0_reading/North_view.json` | elevation | done |
| `East_view.png` | `0_reading/East_view.json` | elevation | done |
| `West_view.png` | `0_reading/West_view.json` | elevation | done |

## Per-image result + confidence self-assessment

### 1f_view (plan) — confidence HIGH (one MEDIUM window)
- 10 walls, 7 windows, 8 healed door openings; 32 dimensions; 4 chains.
- Layout: central corridor (y=[3,5]) between two full-width partitions; upper band split into 3 rooms
  (x=5,10), lower band split into 3 rooms (x=5,10) → 6 rooms + corridor = **7 regions = testdata**.
- Windows: 3 top-wall, 3 bottom-wall, 1 right-wall (corridor). Doors: bottom entrance + left side
  entrance + 3+3 interior corridor doors.
- MEDIUM item: right-wall corridor window **S17** — the right-side height chain (2940/340/1200/340/2940)
  sums to 7.76 m with no printed overall (0.24 m unlabeled residual); I placed the stroke from the
  pixel measurement (y=[3.40,4.60], anchored between the confirmed y=3 / y=5 partition walls) and
  flagged the chain discrepancy rather than trusting the non-closing chain.

### 2f_view (plan) — confidence HIGH (one MEDIUM window)
- 10 walls, 8 windows, 6 healed door openings; 30 dimensions; 4 chains.
- Layout **read independently — differs from 1f**: central corridor (y=[3,5]); upper band = **2**
  conference rooms (single partition x=7.5); lower band = **4** offices (partitions x=3.75, 7.5, 11.25)
  → 6 rooms + corridor = **7 regions = testdata**.
- Windows: 2 top-wall (3.6 m), 4 bottom-wall (1.2 m), 1 left + 1 right (corridor). **No exterior door
  on floor 2.**
- MEDIUM item: right-wall window **S18** — same right-chain 0.24 m residual as 1f; placed from pixel +
  the exactly-closing left chain, flagged.
- Sub-medium: lower partitions S9/S10 pixel-traced ~0.06 m higher than the chain (3.81/11.31 vs the
  chain-derived 3.75/11.25); used the chain values because C_bottom closes exactly. Flagged as a small
  systematic scale/origin bias.

### South_view (elevation) — confidence HIGH
- 2 wall_fill (one per floor), 7 windows, 1 logged door; 33 dimensions; all 5 chains close exactly.
- F2: 4 windows 1.2×1.8 at z=[4.0,5.8]. F1: 1 short window (1.2×0.6 at z=[1.5,2.1]), 2 large windows
  (2.4×1.6 at z=[1.0,2.6]), + floor-height door (z=[0,2.1]) at far left.
- Storey line z=3.0, roof z=6.6. F1 height 3.0 m, F2 height 3.6 m.

### North_view (elevation) — confidence HIGH
- 2 wall_fill, 5 windows, no door; 23 dimensions; all chains close exactly.
- F2: 2 windows 3.6×1.8 at z=[4.0,5.8]. F1: 3 windows 2.4×1.6 at z=[1.0,2.6].

### East_view (elevation) — confidence HIGH
- 2 wall_fill, 2 windows, no door; 13 dimensions; all chains close exactly.
- Facade width 8.0 m (building depth). One centred 1.2 m window per floor at local-x=[3.40,4.60];
  F2 z=[4.0,5.8], F1 z=[1.0,2.8] (F1 here is **1.8 m tall**, read from the "200" gap to the storey line
  — deliberately not copied from the S/N 1.6 m sill).

### West_view (elevation) — confidence HIGH
- 2 wall_fill, 1 window, 1 logged door; 11 dimensions; all chains close exactly.
- Facade width 8.0 m. F2: 1 centred window 1.2×1.8 at z=[4.0,5.8]. F1: a floor-height double-leaf
  **door** (1.5 m wide, x-local=[3.25,4.75], z=[0,2.1]) — the side entrance; logged, not traced.
  Contrast East (F1 = real window) — read each facade independently.

## Internal cross-consistency (a happy side-effect, NOT topology I asserted — correction owns this)
Every facade's opening x/z line up with the corresponding plan wall: South F1↔1f bottom wall, South
F2↔2f bottom wall, North F1↔1f top wall, North F2↔2f top wall, East↔right-wall corridor windows (both
floors), West F1 door↔1f left-wall door, West F2↔2f left-wall window. This gives me confidence the
readings are coherent, but I did not encode any plan↔elevation mapping in the JSONs.

## Fields that were repeatedly null / empty / unknown
- **`strokes[*].geometry.thickness_m` = null everywhere** (both plans) — per schema §0.2. Wall thickness
  IS visible (~0.24 m exterior, ~0.12 m interior, from double-line spacing and the "240" ticks) but is
  intentionally not recorded.
- **`ocr_texts` = [] in all 6 images** — there are no room-name labels, no north arrow, no scale bar,
  no grid axes anywhere in this case. The only text on the drawings is dimension numbers (→ dimensions[])
  and the "240" thickness ticks (→ uncaptured).
- **`dimensions[*].anchor` = null everywhere** — I did not record per-number pixel bounding boxes.
- **`facade` = null on both plans** (elevation-only field), fully populated on all 4 elevations.
- **`provenance` = "seen" on every stroke**; I emitted no `dimension_derived` strokes. Coordinates were
  read from pixels and corroborated by the dimension chains that live in `dimensions[]` (the redundant
  channel), rather than tagging individual strokes dimension_derived.
- **elevation `outline`** — never traced as its own stroke in any of the 4 elevations: the silhouette is
  a plain rectangle that coincides exactly with the wall_fill edges + storey line (flat roof, no
  parapet/setback), so per pen-library it is redundant → logged in `uncaptured`.

## Schema / process feedback
1. **The worked-example JSON (smalloffice_20/0_reading/1f_view.json) is on an OLDER schema** than
   `guide.md` §2 describes: it has no `provenance` / `confidence` / `dimension_refs` / `facade`, its
   dimensions use `"text"` (not `text_verbatim` + `value_m` + `chain_id` + `role` + `order`), and it
   carries `self_check.uncaptured_visual_elements` instead of a top-level `uncaptured`. I followed the
   current `guide.md` schema as authoritative and used the worked example only for id-naming / note
   tone. Recommend refreshing the worked example to the current schema so style anchor and rule
   container cannot drift apart (this drift is exactly the failure the kickoff warns about).
2. **The closure check (Σsegments == overall) mis-fires on two legitimate drawing features** on the
   plans, and callers should not treat these as reading errors:
   - `C_top` on both plans has an **unlabeled gap** between segments (a double-tick with no number) that
     represents an interior partition's drawn thickness (~0.12 m). Σsegments (14.76 / 14.88) < overall
     (15.00) by the gap. There is no schema slot to declare "unlabeled gap = X here", so the residual
     can only be explained in a note. Consider a `role:"gap"` / `unlabeled:true` dimension entry so the
     closure check can account for real un-numbered gaps.
   - `C_right` on both plans has **no printed overall total at all** and its 5 numbered segments sum to
     7.76 m vs the true 8.00 m (a 0.24 m residual that the drawing simply never dimensions). The closure
     check can't even run (no overall). Flagged in each file's `self_check.unknowns_noted`.
3. **Height (z) chains on elevations were split into separate `chain_id`s** (`C_height_coarse` for the
   storey split 3000/3600 + overall 6600, and `C_left_fine` / `C_right_fine` for the window-band
   breakdown) so that each chain closes to 6.60 and the closure check stays meaningful. A single mixed
   chain of coarse+fine numbers would not close. Documenting this convention would help the next reader.
4. **`facade.mirrored`** is a low-confidence field: I set `"false"` for all four elevations (they are
   drawn as normal, non-flipped orthographic views) but I have no positive in-image evidence of
   non-mirroring — `"unknown"` would be defensible. A note on how to earn `"false"` vs `"unknown"` would
   remove the ambiguity.
5. **No stair / vertical-circulation symbol is drawn on either floor plan**, yet the building is 2
   storeys. This is a testdata simplification; I did not invent a stair. Downstream should be aware the
   inter-floor connection is simply absent from the source.
