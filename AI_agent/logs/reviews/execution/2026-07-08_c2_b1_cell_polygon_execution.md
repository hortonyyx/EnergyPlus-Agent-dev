# C2 B1 Cell.polygon Execution

Date: 2026-07-08

## Scope

Implemented D2 / D8 B1 on top of B0:

- Added `Cell.polygon` and schema v2 (`"2"`) as the polygon-capable correction contract.
- Registered schema v2 with `orthogonal_polygon` capability profile handling.
- Added shared polygon-first cell geometry helpers for bbox projection, validated polygons, axis values, facade spans, and bbox re-derivation.
- Made gate ① validate polygon contract:
  - polygon requires schema v2;
  - exterior ring must be CCW and not explicitly closed;
  - v2 B1 polygons must be orthogonal;
  - self-intersection, degeneracy, bbox mismatch, and sub-min-edge edges fail.
- Upgraded deterministic core to collect all polygon vertices for x/y axis clustering, snap polygon vertices, and rederive `x`/`y` from the snapped bbox.
- Kept v1 bbox path unchanged and added regression coverage for byte-identical v1 geometry.
- Unified `geometry_validator._cell_box` and `modelling._cell_polygon` through the same polygon-first helper.
- Kept split-pairing polygon-native path; added B1 tests that prove L-shaped cell walls are generated from polygon edges, not bbox four sides.
- Updated correction prompt and `1_correction` A0 contract wording:
  - prefer multiple rectangular cells;
  - only emit polygon when a room itself cannot be faithfully represented by rectangles;
  - polygon is a fallback, not the default.
- Updated correction scoring wall extraction to read cell polygon edges instead of bbox edges.
- Updated audit geometry signatures to include polygon vertices.

## Deviations / Engineering Calls

- Authoritative envelope reconcile is explicitly skipped with an `unsupported` entry when polygon cells are present. B1 does not define how to move polygon vertices from facade envelope evidence, and the old bbox-only edge move would create `x`/`y` vs `polygon` inconsistency. This follows verdict priority over silent bbox fallback.
- `correction.window_on_wall` remains a coarse bbox-span flag check for polygon cells. Kernel attachment still uses actual polygon wall segments and fails if no unique parent wall exists.

## Tests

- Focused affected suite:
  - `pytest -q tests/test_c2_b1_cell_polygon.py tests/test_c2_b0.py tests/test_geometry_kernel.py tests/test_kernel_guards.py tests/test_checks_reading_correction.py tests/test_deterministic_core.py tests/test_judge_batch_b.py tests/test_elevation_score.py`
  - Result: `137 passed`
- Full suite excluding network-dependent zone-agent test:
  - `pytest -q --ignore=tests/test_zone_agent.py`
  - Result: `546 passed, 9 xfailed, 115 warnings`

Baseline noted in the request was `538 passed + 9 xfailed`; this batch adds 8 passing B1 tests.

## Residual

- No git commit was made.
- Existing unrelated dirty/untracked workspace files were left untouched.

## Follow-up: sm24 C-shape Wall Normal Defect

Trigger: first real sm24 DeepSeek correction run failed closed at 2_modelling:

- `kernel.normals`: 3 inward corridor wall surfaces.
- InterZone pairing: 1 reciprocal pair with same-direction normals.

Root cause:

- Wall generation used one global zone `representative_point()` to decide the
  interior side of every wall segment. That is insufficient for concave polygon
  cells: a C-shaped corridor has local boundary segments whose interior side is
  opposite from the side implied by the representative point in another wing.
- `kernel.normals` had an independent diagnostic weakness: it used the mean of
  all surface vertices as a zone centroid and tested wall normals against
  `mid - centroid`. For concave cells this can both false-positive and miss a
  genuinely flipped local edge, explaining why `kernel.normals` and InterZone
  reported different surface sets.

Fix:

- `modelling._wall_verts` now computes the wall outward normal from the owning
  polygon locally: probe both sides of the wall segment midpoint and choose the
  side outside the zone polygon.
- `split_pairing` passes the owning `ZoneVolume.polygon` into wall vertex
  generation for both interior and exterior wall segments.
- `kernel.normals` now checks wall normals against the owning zone polygon with
  the same local inside/outside probe instead of a global centroid heuristic.
- Added a regression test using the sm24 simplified 8-cell layout, including the
  8-vertex C-shaped corridor and 6-vertex L-shaped `se_office`.

Verification:

- Reproduced the disk case from
  `case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/1_correction/correction_geometry_snapped.json`;
  after the fix, `check_kernel(..., capability_profile="orthogonal_polygon")`
  passes `kernel.normals` and `kernel.pairing_gate`, and InterZone returns `[]`.
- Focused suite:
  - `pytest -q tests/test_c2_b1_cell_polygon.py tests/test_c2_b1_winding.py tests/test_geometry_kernel.py tests/test_checks_kernel.py tests/test_kernel_guards.py tests/test_c2_b0.py`
  - Result: `57 passed`
- Full suite excluding network-dependent zone-agent test:
  - `pytest -q --ignore=tests/test_zone_agent.py`
  - Result: `556 passed, 9 xfailed, 115 warnings`

Test count after this follow-up is one above the user's stated current baseline
(`555 passed + 9 xfailed`) due to the added sm24 C-shape regression.

## Orchestrator amendment (Fable 5, 2026-07-08, post-batch)

- Reworded the polygon-fallback rule in `src/agent/pipeline.py` (_build_correction_messages) and
  `skills/intake_pipeline/1_correction/A0_contract.md`. The batch wording — "only when a room cannot be
  faithfully represented as one or more rectangles" — made `Cell.polygon` dead-letter (every orthogonal
  polygon decomposes into rectangles) and reproduced the exact defect C2 set out to fix (sm24 L-corridor
  split into 2 zones, 2026-06-24 finding). New rule: **each room is exactly one cell; never split a single
  room into multiple cells just to keep them rectangular; a room whose own shape is not a single rectangle
  gets a polygon cell**. Skeleton principle preserved: polygon stays the exception, not the default.

## Orchestrator amendment 2 (Fable 5, 2026-07-08, first real-case exercise)

sm24 push (DeepSeek correction, orthogonal_polygon profile) triggered the polygon route on the
first real draw — and crashed the flow: the LLM emitted the L-corridor ring **CW**, and the D2
guard ("非 CCW → raise") raised out of `apply_deterministic_core` inside `_draw_correction`,
killing the run instead of burning a draw. Two-part fix (deviation from D2 wording, rationale
recorded):

1. **Winding is encoding, not geometry** — `normalized_ccw_polygon()` in `cell_geometry.py`;
   the deterministic core canonicalizes CW→CCW (start vertex preserved, zero information loss)
   and logs a `POLYGON_WINDING_CCW` correction. LLM producers routinely emit CW; raising on it
   made the polygon path a coin-flip. The strict-CCW raise stays for every consumer that does
   NOT run behind the core (gate① validator sees post-core geometry, unchanged).
2. **Polygon crimes = LLM draw defects, not code defects** — `correction_draw_issues()` now
   mirrors all core polygon raises winding-tolerantly (v1-schema polygon, self-intersection,
   non-orthogonal, sub-min-edge, bbox mismatch), so a bad polygon blocks the draw and
   blind-resamples per the established stochastic-stage contract instead of crashing the flow.

New tests: `tests/test_c2_b1_winding.py` (8). Focused suites green; full suite rerun pending.
