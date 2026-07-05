# Grade Refactor Batch 1 Scorer Execution Log

Date: 2026-07-04

Scope: Batch 1 only: scorer, sidecar, config, policy, tests. `scripts/tool_scripts/render_grade.py` was already dirty at turn start and was left read-only by this batch.

## Files Changed By This Batch

- `src/agent/judge/reading_score.py`
- `src/agent/judge/correction_score.py`
- `src/agent/judge/elevation_score.py`
- `src/agent/judge/score_policy.py`
- `src/agent/execution/run_config.py`
- `scripts/tool_scripts/run_stage.py`
- `tests/test_reading_score.py`
- `tests/test_elevation_score.py`
- `tests/test_run_config.py`
- `tests/test_judge_batch_b.py`

Pre-existing dirty files observed before edits and not intentionally modified in this batch:

- `scripts/tool_scripts/render_grade.py`
- `tests/test_gt_discipline.py`
- `tests/test_render_grade.py`

## Schema And Config

- `SCORER_SCHEMA`: `4 -> 5`.
- Sidecar strict reuse still validates `stage`, `attempt`, `output_hash`, `source`, `scorer_schema`, and exact `tolerances`.
- `GradeConfig.as_tolerances()` now emits:

```json
{
  "wall_tol_m": 0.3,
  "window_centre_tol_m": 0.4,
  "elevation_along_tol_m": 0.4,
  "sill_tol_m": 0.3,
  "head_tol_m": 0.3,
  "width_tol_m": 0.4,
  "position_tol_m": 0.3,
  "extent_tol_m": 0.3,
  "complete_eps_m": 0.05,
  "overlap_accept": 0.75,
  "overlap_complete": 0.95,
  "floor_line_tol_m": 0.3
}
```

`position_tol_m` defaults from `wall_tol_m` unless explicitly set. Legacy `elevation_overlap_min` is accepted as a parse fallback for `overlap_accept`, but schema-5 sidecars serialize the new keys.

## Implemented Algorithms

Plane walls:

- GT wall geometry is derived judge-side from gt zone edges using the same merged-segment logic as the renderer's `_interior_coords` / `_merge`, without importing renderer code.
- Product wall geometry is preserved as `[lateral_coord, start, end]`.
  - Reading uses stroke `p1`/`p2` or rect midline.
  - Correction uses cell edges with their real cell spans.
- Stage 1 association requires same orientation and `abs(product.coord - gt.coord) <= position_tol_m`.
- Stage 2 pieces compare associated product span to gt span:
  - `matched`: overlap span.
  - `missing`: gt span not covered by product.
  - `extra`: product span outside gt.
- Status:
  - `complete` when both ends are within `complete_eps_m`.
  - `within_tol` when both end offsets are within `extent_tol_m`.
  - `miss` for gt records with no product association or beyond-tolerance extent.
  - `extra` for unassociated product records.

Plane windows:

- Product and gt windows are 1D facade-lane spans.
- One-to-one matching maximizes segment overlap.
- Status and pieces use the same complete / within tolerance / miss / extra span breakdown as walls.

Elevation windows:

- `overlap_ratio = intersection_area / min(product_area, gt_area)`.
- Reading still evaluates aligned and interval-reflected flipped orientations per facade and chooses the better orientation. Correction remains aligned-only; flipped improvement is recorded as evidence.
- A pair is associated only when `overlap_ratio >= overlap_accept`.
- Pair status:
  - `complete` for `overlap_ratio >= overlap_complete`.
  - `within_tol` for `overlap_accept <= overlap_ratio < overlap_complete`.
  - Below accept is not a match, producing gt `miss` plus product `extra`.
- Sidecar records product box, gt box, `overlap_ratio`, status, orientation, and along/sill/head/width deltas as evidence only.

Elevation floor lines:

- GT lines: `0`, positive `z_floor` values, and roof `max(z_floor + ceiling_height)`.
- Reading product lines: distinct `y_range_m` edges from `wall_fill` strokes per elevation facade. Facades without usable `wall_fill` emit no-data evidence and no fabricated lines.
- Correction product lines: model floor `z_floor` values plus top roof line.
- Each gt line matches nearest product line within `floor_line_tol_m`.
  - exact hit: `complete`
  - nonzero offset within tolerance: `within_tol`
  - no product within tolerance: `miss`

Policy:

- Advisory criteria remain advisory-only and are not in `StageVerdict`.
- Wall/window/elevation evidence now includes counts derived from `complete`, `within_tol`, `miss`, and `extra`.
- `elevation_windows_placed` treats `complete + within_tol` as placed for advisory status.

## Sidecar Shape Example From Real sm21

Generated from local `case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/attempts/001/output.json`.

```json
{
  "plane_wall": {
    "status": "complete",
    "orientation": "v",
    "truth": 5.0,
    "read": 5.0,
    "delta": 0.0,
    "product": [5.0, 0.0, 3.0],
    "gt": [5.0, 0.0, 3.0],
    "pieces": [
      {"kind": "matched", "span": [0.0, 3.0], "within_tol": true}
    ]
  },
  "elevation_window": {
    "status": "complete",
    "facade": "North",
    "floor": "Floor 1",
    "orientation": "ambiguous",
    "source_id": "S5",
    "product_box": {
      "span": [1.24, 3.64],
      "z": [1.0, 2.6],
      "center": 2.44,
      "width": 2.4,
      "source_id": "S5",
      "source_span": [1.24, 3.64]
    },
    "gt_box": {
      "id": "North/Floor 1/0",
      "span": [1.24, 3.64],
      "z": [1.0, 2.6],
      "center": 2.44,
      "width": 2.4
    },
    "deltas": {
      "along_center_m": 0.0,
      "sill_m": 0.0,
      "head_m": 0.0,
      "width_m": 0.0
    },
    "overlap_ratio": 1.0
  },
  "floor_lines_South": [
    {"facade": "South", "gt_z": 0.0, "product_z": 0.0, "status": "complete", "delta": 0.0},
    {"facade": "South", "gt_z": 3.0, "product_z": 3.0, "status": "complete", "delta": 0.0},
    {"facade": "South", "gt_z": 6.6, "product_z": 6.6, "status": "complete", "delta": 0.0}
  ]
}
```

## Tests

- Targeted scorer/config/sidecar subset before final correction regression: `37 passed`.
- Targeted scorer/config/sidecar subset after final correction regression: `38 passed`.
- Full final run: `python -m pytest -q` -> `460 passed, 9 xfailed, 90 warnings in 83.32s`.

Added/updated coverage includes:

- Reading half-length wall scores as missing piece, not clean hit.
- Correction half-length wall scores as missing piece.
- Plan window double-width scores an extra piece.
- Elevation window overlap `0.80 -> within_tol`, `0.60 -> miss + extra`, `0.97 -> complete`.
- Floor/ground/roof line hit and miss.
- Full tolerance round-trip through `GradeConfig` and sidecar strict reuse.

## Review Ask

- Batch 2 renderer must consume `complete` / `within_tol` / `miss` / `extra` elevation statuses. The current read-only renderer still recognizes old `placed_hit` / `matched_with_z_drift` for coloring, so schema-5 elevation boxes may not be colored until Batch 2.
- Batch 2 renderer should draw plan products from `product` / `product_box` and diff pieces from `pieces`, not from gt extents.
- Batch 2 renderer should use `vwall_records`, `hwall_records`, and `extra_window_records` for detailed product geometry. Legacy `extra_vwalls`, `extra_hwalls`, and `extra_windows` are retained only to keep the current read-only renderer from crashing.
- Confirm whether continuous product walls crossing a gt gap should remain one-to-one against one gt segment plus miss/extra, as implemented, or whether Batch 2 should visually group adjacent same-coordinate records. The scorer currently follows one-to-one association.
- Confirm whether elevation `within_tol` should count as "placed" in advisory policy. Implemented as placed for advisory status, with separate complete/within counts preserved.

## REWORK Per Review

Date: 2026-07-04

Independent review verdict: APPROVE-WITH-CHANGES. All adopted findings in the updated spec were applied to Batch 1 scorer/sidecar/config/tests.

### Schema

- `SCORER_SCHEMA`: `5 -> 6`.
- Sidecar strict reuse remains fail-closed on `stage`, `attempt`, `output_hash`, `source`, exact `tolerances`, and `scorer_schema`.

### Two-Sided Elevation Coverage

Elevation windows no longer use `intersection_area / min(product_area, gt_area)`.

Implemented formula:

```text
gt_coverage      = intersection_area / gt_area
product_coverage = intersection_area / product_area
overlap_ratio    = min(gt_coverage, product_coverage)
```

Status:

- `complete` iff `overlap_ratio >= overlap_complete`.
- `within_tol` iff `overlap_accept <= overlap_ratio < overlap_complete`.
- Otherwise no association: gt `miss` plus product `extra`.

The sidecar now carries `overlap_ratio`, `gt_coverage`, and `product_coverage`. A 1.5 m product window over a 1.0 m gt window is no longer complete; the regression test asserts the miss+extra case, and a 1.25 m product over a 1.0 m gt is `within_tol` at 0.8 product coverage.

### Plane Interval-Set Algorithm

Plane walls:

- Group by orientation and lateral-coordinate cluster within `position_tol_m`.
- Within each cluster, compare the union of product intervals against the union of gt intervals.
- Pieces are set operations:
  - `matched = product_union ∩ gt_union`
  - `missing = gt_union - product_union`
  - `extra = product_union - gt_union`
- No one-to-one gt/product segment assignment remains inside a cluster.

Plane windows:

- First assign product windows to a facade lane using the existing facade extraction.
- Compare all product spans vs gt spans as 1D interval sets per facade lane.
- No lateral `position_tol_m` gate is applied to plan windows.

Added regressions:

- One product wall crossing a gt gap emits matched + extra-gap + matched, with no missing of the next gt segment.
- Two product strokes covering one gt segment union to a complete hit.

### Complete Suppression And Tolerance Validation

`GradeConfig` now raises on invalid judge rulers:

- all serialized tolerances must be nonnegative;
- `complete_eps_m <= extent_tol_m`;
- `overlap_accept <= overlap_complete <= 1`.

When interval-set diff pieces are all at or below `complete_eps_m`, the element status is `complete` and missing/extra pieces are suppressed. The sidecar keeps the product/gt interval geometry, and `pieces: []` tells Batch 2 to draw the product as a clean green element. Added a near-exact wall regression with one slightly short and one slightly long end inside `complete_eps_m`.

### Floor-Line Sidecar Schema

`elevation.floor_lines` is now a full per-facade diff object:

```json
{
  "South": {
    "facade": "South",
    "gt_floor_lines": [0.0, 3.0, 6.6],
    "product_floor_lines": [0.0, 3.0, 6.6],
    "matches": [
      {"gt_z": 0.0, "product_z": 0.0, "status": "complete", "delta": 0.0}
    ],
    "extras": [],
    "no_data": false,
    "no_data_reason": null
  }
}
```

No-data is separate from miss:

- missing elevation view -> `no_data: true`, `no_data_reason: "missing_elevation_view"`;
- view present but no horizontal-line source such as `wall_fill` -> `no_data: true`, `no_data_reason: "no_product_floor_line_source"`;
- product line with no gt match -> `extras[]` as red-solid product candidates for Batch 2.

### Elevation Boundary Sidecar Schema

`elevation.boundary` is now explicit per facade and floor:

- North/South: `side_left` from W boundary, `side_right` from E boundary.
- East/West: `side_left` from S boundary, `side_right` from N boundary.
- If plan boundary data is absent, side status is `no_data`.

This prevents Batch 2 from re-deriving mapping rules from plan records.

### Real sm21 Schema-6 Snippet

Generated from local `case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/0_reading/attempts/001/output.json`.

```json
{
  "schema": "6",
  "plane_wall": {
    "status": "complete",
    "orientation": "v",
    "truth": 5.0,
    "read": 5.0,
    "delta": 0.0,
    "product": [5.0, 0.0, 3.0],
    "gt": [5.0, 0.0, 3.0],
    "product_intervals": [[5.0, 0.0, 3.0], [5.0, 5.0, 8.0]],
    "gt_intervals": [[5.0, 0.0, 3.0], [5.0, 5.0, 8.0]],
    "pieces": []
  },
  "elevation_window": {
    "status": "complete",
    "facade": "North",
    "floor": "Floor 1",
    "orientation": "ambiguous",
    "source_id": "S5",
    "product_box": {
      "span": [1.24, 3.64],
      "z": [1.0, 2.6],
      "center": 2.44,
      "width": 2.4,
      "source_id": "S5",
      "source_span": [1.24, 3.64]
    },
    "gt_box": {
      "id": "North/Floor 1/0",
      "span": [1.24, 3.64],
      "z": [1.0, 2.6],
      "center": 2.44,
      "width": 2.4
    },
    "overlap_ratio": 1.0,
    "gt_coverage": 1.0,
    "product_coverage": 1.0
  },
  "floor_lines_South": {
    "facade": "South",
    "gt_floor_lines": [0.0, 3.0, 6.6],
    "product_floor_lines": [0.0, 3.0, 6.6],
    "matches": [
      {"facade": "South", "gt_z": 0.0, "product_z": 0.0, "status": "complete", "delta": 0.0},
      {"facade": "South", "gt_z": 3.0, "product_z": 3.0, "status": "complete", "delta": 0.0},
      {"facade": "South", "gt_z": 6.6, "product_z": 6.6, "status": "complete", "delta": 0.0}
    ],
    "extras": [],
    "no_data": false,
    "no_data_reason": null
  },
  "elevation_boundary_North_Floor1": {
    "side_left": {
      "source_boundary": "W",
      "status": "complete",
      "truth": 0.0,
      "product": 0.0,
      "delta": 0.0
    },
    "side_right": {
      "source_boundary": "E",
      "status": "complete",
      "truth": 15.0,
      "product": 15.0,
      "delta": 0.0
    }
  }
}
```

### Tests

- Focused scorer/config/sidecar subset: `44 passed`.
- Full final run: `python -m pytest -q` -> `466 passed, 9 xfailed, 90 warnings in 76.40s`.

### Remaining Review Ask

- Batch 2 renderer must consume schema-6 `product_intervals`, `gt_intervals`, `pieces`, two-sided coverage fields, `floor_lines` diff objects, and `elevation.boundary`.
- Batch 2 should render `orientation=flipped` with an explicit cue and keep `source_span` available for audit.
- The current read-only renderer still recognizes old elevation status names for coloring; schema-6 scorer evidence is correct, but the renderer rewrite must update visual semantics.
