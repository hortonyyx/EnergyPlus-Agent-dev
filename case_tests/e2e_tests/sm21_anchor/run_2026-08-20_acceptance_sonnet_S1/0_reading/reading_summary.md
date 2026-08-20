# Reading-stage summary — sm21_anchor

Six source images read: `1f_view`, `2f_view` (plans), `South_view`, `North_view`, `East_view`,
`West_view` (elevations). Per the per-run directive, every wall-line / window-box / storey-line
position was measured with `tools/run_cv_probe.py` (`px_m_calibrator`, `wall_line_profiler`,
`storey_line_profiler`) before being written as a coordinate; sidecars are under
`out/cv/cv_evidence/<image_stem>/`. Windows/doors in this case's drawings are drawn in cyan, which
the shipped `window_cc_detector` recipe does not mask (it targets the same achromatic/gray mask as
`wall_line_profiler`), so window/door rectangles and dimension-chain tick pixels were located with
small, targeted cyan/green connected-component scripts (numpy/scipy, per `cv_toolbox.md`'s "Writing
Your Own Measurement Code" section) instead — each such measurement's source pixels and conversion
are cited in the relevant stroke's `note`.

Cross-checks that came back clean and materially raised confidence in every file below:
- 1F: 15.00 x 8.00 m footprint x 2 floors = 240 m², matches `testdata_prompt.json`'s stated 240 m².
- 1F: 6 rooms + 1 corridor = 7 zones, matches `testdata_prompt.json`'s `thermal_zones: 7` for both floors.
- Both plans' partition/corridor-wall centerlines landed on clean round metre values (5.00/10.00,
  3.00/5.00, 3.75/7.50/11.25) purely from pixel measurement, independently confirmed by each
  dimension chain's segment-boundary sums.
- Every elevation window/door position was cross-validated against the corresponding plan wall's
  window/door x (or y) extent — all matched to within ~0.02 m.

## Per-image confidence

- **1f_view — high.** Fully closed, symmetric geometry; every wall centerline and opening is backed
  by both pixel measurement and a dimension-chain closure. `scale_origin` filled (0.00/0.00 at the SW
  outer corner).
- **2f_view — high.** Same calibration/measurement discipline as 1f_view; door/window placement
  reconciled cleanly (bottom-row door pairs land exactly on partition centerlines). `scale_origin`
  filled.
- **South_view — high.** Outline, storey line, and all 7 openings (1 door + 6 windows across both
  floors) are each backed by a dimension chain and independently cross-checked against 1f_view's/
  2f_view's south-wall openings.
- **North_view — medium-high.** Same discipline as South_view; slightly lower than South only because
  the top x-chain's segment sum closes exactly with no unlabeled gap (unlike the plans' equivalent
  chain), which is a real drawing difference, not a reading gap — flagged for correction's awareness
  in `self_check.unknowns_noted`, not a confidence problem in the reading itself.
- **East_view — high.** Simple facade (1 window per floor, no door); every stroke backed by pixel
  measurement + dimension chain, cross-validated against both plans.
- **West_view — high.** Same as East_view, but the 1F opening is a door; its height comes only from a
  cyan pixel measurement (no drawn z-detail chain subdivides the 1F "3000" on this side), which is
  recorded honestly as `provenance` on the note / uncaptured entry rather than invented as
  `dimension_derived`.

## Fields repeatedly null / not found

- `strokes[*].geometry.thickness_m` — null on every plan wall stroke in both files, per schema (walls
  are centerlines for EnergyPlus purposes; thickness is never estimated even though several small
  "240" dimension callouts on the plans give an approximate wall thickness).
- `ocr_texts` — empty in all six files. No room-name labels, title block, scale bar, or north arrow
  were visible in any of the six cropped source images; only dimension numbers and furniture symbols
  appear, and all dimension numbers are transcribed into `dimensions[]` instead.
- `facade.mirrored` — `"unknown"` on all four elevations. Nothing in-image (no north arrow, no
  explicit mirror note) distinguishes a mirrored export from an unmirrored one from a single facade
  alone; this is flagged for correction to resolve via cross-referencing each facade's window/door
  x-positions against the plan footprints, per `guide.md` §7 — deliberately not guessed here.

## Schema feedback

- The gray-mask-only `window_cc_detector` (and by extension `wall_line_profiler`'s color assumption)
  did not fire on this case's cyan window/door strokes; every window/door rectangle and every
  dimension-chain tick pixel in this run came from ad hoc cyan/green color-threshold scripts instead
  of the shipped detector tools. A cyan-aware recipe (or a `--color` parameter) would let
  `window_cc_detector` actually do this case's window-finding job, and would remove the biggest
  manual/scripted-measurement burden in this run.
- Nested dimension chains (an overall column, e.g. elevation "6600", drawn alongside a coarser
  per-floor breakdown "3600"/"3000", drawn alongside a fine sill/head breakdown "800"/"1800"/"1000")
  are common in these elevations and don't map cleanly onto a single `chain_id`'s flat
  overall+segments shape without either double-counting a closure sum or inventing multiple
  `chain_id`s per physical dimension line group (what this run did: one `chain_id` per drawn line,
  fine detail as its own child chain-id). Worth stating explicitly in `guide.md` as the intended
  pattern, since the worked example only shows a single-tier chain.
  - The reading stage found an average of one occurrence of "single-segment 240mm dimension chain used
  purely to state a wall's thickness at one jamb/corner" per plan image (up to 5 in 1f_view). These
  are legitimate dimension chains (two ticks + a number) so they were transcribed, but they add
  meaningful volume to `dimensions[]` without being consumable by anything downstream (wall
  `thickness_m` is always null). Worth a one-line schema note confirming these should still be
  transcribed (this run assumed yes, per the "every dimension-chain number" self-check line) so
  future readers don't skip them as redundant.
