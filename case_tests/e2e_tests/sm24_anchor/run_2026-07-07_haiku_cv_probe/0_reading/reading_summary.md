# Reading summary — sm24_anchor / run_2026-07-07_haiku_cv_probe

One output JSON per source image; CV sidecars under `cv_evidence/<image_stem>/` (calibrations, profiler runs, band-restricted CC detections, verification crops, overlay_logger decision logs).

## Manifest

| source PNG | output JSON | image_kind | status |
|---|---|---|---|
| `1f_view.png` | `1f_view.json` | plan | done (pilot, reworked once per review) |
| `South_view.png` | `South_view.json` | elevation | done |
| `North_view.png` | `North_view.json` | elevation | done |
| `East_view.png` | `East_view.json` | elevation | done |
| `West_view.png` | `West_view.json` | elevation | done |

No other source images exist in case_data (testdata lists exactly these five).

## Per-image confidence self-assessment

### 1f_view (plan) — HIGH
- Calibration: 36.3333 px/m, RMSE 0.33 px = 9.2 mm, residuals ±0.33 px, 3 anchors (two 10000 + one 20000 overall chains).
- 14 wall strokes + 11 window strokes; 51 dimensions in 11 chains, every chain closes exactly (10.00 / 20.00 m).
- All but one wall chain-pinned. The one un-dimensioned wall (S14, corridor bottom closure) is a calibrated pixel measurement (py 753 → y=3.44 m) with `provenance: seen`, empty `dimension_refs`, cited sidecars — the honest-provenance path.
- 10 doors healed (3 perimeter chain-pinned, 7 interior pixel-measured); 1 doorless open span (corridor → east arm) deliberately NOT healed (real topology signal).
- 52 profiler candidates dispositioned (14 accepted → walls; 38 rejected: furniture / chain artifacts / window crossings) in `cv_evidence/1f_view/001_overlay_logger.json`.
- Reason for high confidence: triple corroboration everywhere (chain arithmetic ↔ wall-mask line extraction ↔ crop verification), and the L-corridor / L-shaped SE room topology resolves all junctions consistently.

### South_view (elevation) — HIGH
- Calibration: 152.773 px/m, RMSE 0.38 px = 2.5 mm, 4 anchors, zero warnings.
- 1 wall_fill + 2 windows; 20 dimensions, all chains close (10000 / 4500).
- Door assembly (900 wide, single leaf + transom) recognized → logged, not drawn.
- Cyan window rects agree with chain positions ≤1 px.

### North_view (elevation) — HIGH
- Calibration: 167.947 px/m, RMSE 0.43 px = 2.6 mm, zero warnings.
- 1 wall_fill + 1 large window (4800×2400); double-door assembly (1600) logged, not drawn.
- 15 dimensions, all chains close.

### East_view (elevation) — HIGH
- Calibration: 94.402 px/m, RMSE 0.14 px = 1.5 mm (best of the set), zero warnings.
- 1 wall_fill + 3 windows (4800×2400, 1200×1800, 1500×1800); double-door (1600) logged.
- 22 dimensions, all chains close (20000 / 4500).
- Minor honest note: the 1200 window's z band has no dedicated chain; it is drawn pixel-identical to the chain-pinned 1700/1800/1000 band (noted in stroke note).

### West_view (elevation) — HIGH (one quirk)
- Calibration: 94.510 px/m, RMSE 0.57 px = 6.0 mm, zero warnings.
- 1 wall_fill + 5 windows (4×small 1500/1200×1800, 1×4800×2400); no door on this facade.
- 21 dimensions, all chains close.
- Quirk: the top 20000 chain is drawn in dimmer green (g≈135 vs ≈224 elsewhere) — my standard green mask missed it; found by lowered-threshold rescan. Same class of trap as antialiased interior walls on the plan.

## Cross-image consistency observed (recorded, not acted on — correction's job)

- Every elevation opening reconciles with the plan's wall chains: south 1500/900/1500 ↔ plan south wall; north 4800/1600 ↔ plan north wall; east 5700/1600/1540/4800/740/1200/2380/1500/540 ↔ plan east inner chain; west 11-segment chain ↔ plan west inner chain verbatim.
- Elevations supply the z the plan lacks: facade height 4500; window sills 1000; small windows 1800 tall, large (4800) windows 2400 tall; door assemblies 2400 tall with bottoms drawn 200 above the ground line (verbatim 1900/2400/200 chains).

## Repeatedly-null / repeatedly-unknown fields

- `strokes[*].geometry.thickness_m`: always null (per guide §0.2); the drawing's four "240" wall-thickness callouts were transcribed as dimensions (D48-D51 in 1f_view) instead.
- `facade.mirrored`: "unknown" on all four elevations — the images themselves carry no mirroring declaration; bottom-chain segment order was recorded in `orientation_evidence` for correction to resolve.
- `ocr_texts`: empty everywhere — this drawing set has no room labels, level markers, north arrow, scale text, or title blocks; the only text is dimension numbers (routed to `dimensions[]`).
- `dimensions[*].note`: empty for anonymous mid-chain segments (piers/jambs without an owning element).

## Schema feedback

1. **`anchor` format bit me (loader-blocking)**: I first wrote `anchor` as a dict `{"px_a","px_b","line_px"}`; the loader requires `list[float] | null`. The schema comment ("optional pixel bbox/anchor of the number") does not state the shape; an explicit `[x0,y0,x1,y1]` example in guide.md §2 would have prevented a full-file rework. Also note: for rotated (vertical) dimension text the "bbox of the number" vs "span along the chain" distinction matters — I used tick-span bboxes for chain entries and text bboxes for standalone callouts, with notes.
2. **No-fill elevations are an interpretive fork**: pen_library §3 mandates "one wall_fill per floor" while the outline card says outline earns a stroke "when no fill is drawn". For a hollow single-storey facade the two rectangles coincide. I emitted one wall_fill (inferred from the outline, per the wall_fill card's no-fill variant) and logged the outline as coincident per guide §6 checklist. If the intended reading is outline-stroke-only, the docs should say which wins.
3. **Standalone thickness callouts ("240") have no natural chain role**: I used `chain_id: C_thickness_callouts, role: segment` with approximate from/to across the wall body. A dedicated role (e.g. `callout`) or an explicit rule would remove the ambiguity.
4. **Door z chains with a non-zero bottom segment** (1900/2400/200): transcribed verbatim; the 200 means the door assembly bottom is drawn above the ground line. Worth a correction-stage convention note so nobody "fixes" it to 0.
5. **Elevation z axis**: I emitted vertical elevation dimensions with `axis: "z"` (guide §2 allows "z only on elevation") while stroke geometry uses image-local y ranges — consistent with the schema but the y/z dual naming could confuse; a one-liner in the guide would help.
6. **Dim-green chain lines + antialiased thin interior walls**: two masks in one drawing set failed fixed thresholds (West top chain g≈135; plan interior walls tones 95-170 vs perimeter 128-fill vs furniture 224). The cv_toolbox recipes could expose threshold knobs or a "weak-line" recipe variant.

## Pixel-measured (un-dimensioned) elements — the honest-provenance ledger

- Plan S14 corridor-bottom wall: y = (878−753)/36.3333 = 3.44 m; `seen`, empty refs, sidecars cited.
- Plan interior door openings (7): healed positions given in px + metres in wall-stroke notes; no printed door dimensions exist for them.
- East 1200-window z band and West small-window shared z band: drawn pixel-identical to chain-pinned bands; refs kept to those chains with honest notes.
