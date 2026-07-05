# sm21 South 2F Window-X Diagnosis

Scope: local tree only, no source edits. Target run inspected:
`case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/`.

## Finding

The requested GPT-5.4 run does **not** reproduce the stated South-2F window-x bug in
the accepted artifacts. The South elevation reading, raw correction geometry, snapped
correction geometry, and final deterministic model all carry the same South-2F spans as
the CAD-derived GT.

I can reproduce a nearby historical failure in
`case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/`: its 1_correction output
places South-2F windows at wrong x. That failure is a 1_correction logic/model decision,
not a 0_reading or 2_modelling transform failure.

## GT Expected Vs Produced

GT source: `case_tests/test_baseline/gt/sm21_anchor/gt.json:248` declares South Floor 2
with count 4. Per-opening x and width are:

| window | GT span [x, x+width] | width | z |
|---|---:|---:|---:|
| South 2F 1 | [2.19, 3.39] | 1.20 | [4.00, 5.80] |
| South 2F 2 | [4.11, 5.31] | 1.20 | [4.00, 5.80] |
| South 2F 3 | [9.69, 10.89] | 1.20 | [4.00, 5.80] |
| South 2F 4 | [11.61, 12.81] | 1.20 | [4.00, 5.80] |

Relevant GT lines: `gt.json:255`, `gt.json:261`, `gt.json:267`, `gt.json:273`
for `x_m`, with `width_m=1.2` on the following lines.

Requested GPT-5.4 run:

| stage | produced South 2F spans | delta vs GT |
|---|---:|---:|
| `0_reading/South_view.json` | [2.19,3.39], [4.11,5.31], [9.69,10.89], [11.61,12.81] | all 0.00 |
| `1_correction/correction_geometry.json` | [2.19,3.39], [4.11,5.31], [9.69,10.89], [11.61,12.81] | all 0.00 |
| `1_correction/correction_geometry_snapped.json` | [2.19,3.39], [4.11,5.31], [9.69,10.89], [11.61,12.81] | all 0.00 |
| `2_modelling/building_geometry.json` | vertices use x ranges [2.19,3.39], [4.11,5.31], [9.69,10.89], [11.61,12.81] on y=0.1 | all 0.00 |

Evidence:
- `0_reading/South_view.json:61` through `:123` has S4-S7 exactly at those x/z ranges.
- `1_correction/correction_geometry.json:294` through `:347` has `w_2F_S_01` through
  `w_2F_S_04` exactly at those spans.
- `1_correction/correction_geometry_snapped.json:294` through `:347` is unchanged by the
  deterministic core.
- `2_modelling/building_geometry.json:3452` through `:3551` materializes those same x ranges.
- The J1 judge for this run says window position fidelity passed at
  `1_correction/attempts/001/judge.json:16`.

Historical failing run for contrast:

| run | produced South 2F spans | delta vs GT centers |
|---|---:|---:|
| `run_2026-06-16_opus_e2e` | [1.95,3.15], [5.07,6.27], [8.25,9.45], [11.37,12.57] | -0.24, +0.96, -1.44, -0.24 |

Evidence:
- `run_2026-06-16_opus_e2e/1_correction/correction_geometry.json:322` through `:375`
  has the wrong South-2F spans.
- The same run's `0_reading/South_view.json` had the correct South-2F elevation x ranges,
  so the divergence begins in 1_correction.

## Per-Step X Trace

### GT semantics

- `scripts/tool_scripts/gt_from_dxf.py:143` defines plan openings as facade-local.
- `scripts/tool_scripts/gt_from_dxf.py:169` chooses x-bbox for North/South windows.
- `scripts/tool_scripts/gt_from_dxf.py:174` through `:181` computes opening center and width
  from the window bbox along the facade axis.
- `scripts/tool_scripts/gt_from_dxf.py:328` through `:351` emits `x_m = centre - width/2`
  and `width_m`.
- `scripts/tool_scripts/render_gt_overlay.py:35` through `:36` says only North and West
  are mirrored in elevation overlay; South is not mirrored.
- `scripts/tool_scripts/render_gt_overlay.py:157` through `:159` therefore maps South
  `x_m` directly left-to-right in the elevation overlay.

Conclusion: comparing South GT `x_m` spans directly to South world x spans is valid for
this case.

### 0_reading

- `src/agent/reading/schema.py:13` through `:18` says elevation facade data is image-local;
  world axis/sign/base are not supposed to be load-bearing in 0_reading.
- `src/agent/reading/schema.py:80` through `:90` defines `FacadeOrientation` with
  `view_facade`, `local_x_positive`, and `mirrored`.
- `src/agent/reading/schema.py:94` through `:111` defines `ReadingView` and keeps legacy
  `facade_axis_note` only as migration text.
- Requested run data: `0_reading/South_view.json:61` through `:123` reads South-2F
  S4-S7 as exact GT spans.

Conclusion: no 0_reading error in the requested run. Also, in the historical bad run,
the South elevation read was correct; the incorrect values came later.

### 1_correction contract and prompt path

- `src/agent/pipeline.py:289` through `:305` asks the correction LLM to emit a
  `CorrectedGeometry` in one world frame, with each window carrying `facade`, `span`,
  absolute `z`, and owning room.
- `src/agent/pipeline.py:336` through `:339` tells the correction LLM to use facade
  translation formulas in `reading_summary.md §3`. The requested GPT-5.4
  `reading_summary.md` has no §3 formula block; it only summarizes counts and notes.
- `src/agent/correction/schema.py:40` through `:49` defines `Window.span` as an
  along-facade **world** range: x for N/S, y for E/W.
- `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:35` through `:44`
  states the facade horizontal axis maps to the facade world axis but does not provide
  per-facade sign/origin formulas.

Conclusion: production 1_correction relies on the LLM to choose/derive window spans.
The deterministic translator exists but is not integrated into the production path.

### Deterministic facade translator

- `src/agent/correction/facade.py:31` through `:36` defines the standard convention:
  South maps along local x to world +x; North maps to world -x; East maps to -y; West
  maps to +y.
- `src/agent/correction/facade.py:58` through `:60` translates local x as
  `along_origin + sign * local_x`.
- `src/agent/correction/facade.py:69` through `:100` derives sign, base plane, and
  origin from facade, footprint, `local_x_positive`, and `mirrored`.
- `tests/test_checks_reading_correction.py:175` through `:184` asserts South local
  0..15 maps to world x 0..15, while North local 0..15 maps to world x 15..0.
- Repository search shows `derive_facade_frame` is only used in tests, not by
  `run_correction`, deterministic core, or the modelling kernel.

Conclusion: `facade.py` encodes the intended fixable logic, but it is not currently what
materializes correction windows.

### Deterministic core

- `src/agent/correction/deterministic.py:609` through `:610` says windows are processed
  on a finer grid and clamped to parent cell/floor.
- `src/agent/correction/deterministic.py:624` through `:626` snaps the supplied window
  span/z to the window grid.
- `src/agent/correction/deterministic.py:627` through `:633` clamps the supplied span/z
  into the owning room/floor when enabled.
- `src/agent/correction/deterministic.py:660` through `:664` logs and writes the snapped
  values back.

Conclusion: deterministic core does not derive facade-local x and cannot correct a wrong
but still in-room span. In the requested GPT-5.4 run, it leaves the correct South-2F
spans unchanged.

### Validation and modelling

- `src/agent/correction/geometry_validator.py:139` through `:161` validates only that a
  window's span lies inside its owning room's facade extent. This catches floating or
  axis-flipped windows, not wrong in-room x placement.
- `src/agent/geometry/modelling.py:223` through `:233` converts `CorrectedGeometry`
  window spans into actual vertices: for N/S facades, span values become vertex x
  coordinates on the parent wall's constant-y plane.
- `src/agent/geometry/modelling.py:238` through `:268` finds the parent exterior wall by
  facade normal and span containment.
- `src/agent/geometry/modelling.py:355` through `:376` attaches the window to that wall.

Conclusion: 2_modelling is a faithful consumer of 1_correction window spans. If
1_correction emits wrong-but-contained South spans, the final model preserves the error.

## Root Cause

For the requested `run_2026-06-20_gpt54_reading`, I found no South-2F x divergence:
GT, reading, correction, snapped correction, and final model all match.

For the reproducible historical bad artifact (`run_2026-06-16_opus_e2e`), the root
cause is in **1_correction**, not 0_reading or modelling:

1. The South elevation read had the correct window spans.
2. 1_correction applied a global `-0.24 m` origin shift to along-facade x, treating the
   reading origin as SW outer corner and output origin as SW inner corner.
3. For South-2F, it also used 2F plan south-window strokes for the middle pair. Those
   plan strokes were approximate (`S14`/`S15` in the historical 2F plan), while the
   South elevation spans were exact and matched GT.
4. The deterministic core and modelling kernel then preserved those wrong but
   still-contained spans.

Why this looks floor-specific: in the historical bad run, South-1F windows were also
uniformly shifted by `-0.24 m`, but South-2F had additional nonuniform errors because
the middle 2F plan-window strokes differed from the South elevation truth. That makes
the 2F failure larger and easier to notice.

The architectural cause is that production correction lets the LLM perform facade
window-x reconciliation directly. The deterministic `derive_facade_frame()` convention
exists, but it is not used in the production path, and the current gate only checks
window containment, not facade-read-to-correction positional fidelity.

## Fix Direction

Do not implement in the report-only pass. Recommended direction:

1. Add a deterministic facade-window reconciliation step or gate around 1_correction:
   parse elevation window rectangles, derive the facade frame with
   `src/agent/correction/facade.py:69`, convert local x ranges to world spans, and match
   them to `CorrectedGeometry.windows` by facade/floor/z/width/order or nearest center.
2. For South specifically, the standard conversion should preserve local x as world x
   under `src/agent/correction/facade.py:31` through `:36`; do not subtract wall
   thickness along the facade direction. Wall-centerline offsets belong to the wall
   normal direction, not the along-facade coordinate.
3. If plan and elevation window x disagree, prefer elevation x for facade windows, or
   flag an explicit `facade_plan_mismatch`; do not silently choose approximate plan
   strokes when elevation dimension chains are available.
4. Extend `correction.window_on_wall` or add a new `correction.facade_window_position`
   cross-check. The historical bad spans all passed containment; the check needs a
   position residual against elevation-derived spans.

Risk:

- North/West mirror handling must use the structured `mirrored` and convention logic;
  legacy artifacts with only `facade_axis_note` need migration or a conservative flag.
- Some old reading artifacts do not carry canonical `facade` blocks, and some plan
  window strokes lack geometry. The fix should be robust to missing elevation data and
  emit a flag instead of inventing positions.
- If a drawing has real plan-vs-elevation disagreement, the deterministic step should
  preserve the conflict rather than overwriting it silently.

## Review Ask

Please re-verify which produced artifact is intended by the bug report. The requested
`run_2026-06-20_gpt54_reading` is numerically correct for South-2F x, while the older
`run_2026-06-16_opus_e2e` is wrong and matches the described failure mode. If the bug
is visible in another downstream artifact not inspected here, point me to that exact
path before designing the fix.
