# 2026-07-04 Grade Refactor Bandfix Execution Log

## Scope

Implemented the small follow-up refinement from `2026-07-04_grade_visual_model_spec.md`:

- FIX B scorer: plane-wall lateral drift now participates in `complete` / `within_tol` classification.
- Renderer tolerance band shape: within-tol plane walls now draw the orange acceptance region around GT, adapting to lateral drift, extent drift, or both.
- Missing/extra line style: verified and covered with a regression that within-tol `missing` remains dashed; `extra` remains solid in the existing renderer paths.

## Scorer Change

- Updated `src/agent/judge/reading_score.py`.
- `WallMatch` now carries drift hints:
  - `lateral_drift`
  - `extent_drift`
  - `extent_start_drift`
  - `extent_end_drift`
- Plane-wall cluster status now requires both axes:
  - `complete`: lateral `abs(delta) <= complete_eps_m` and interval diff pieces all sub-`complete_eps_m`.
  - `within_tol`: lateral `abs(delta) <= position_tol_m` and extent diff pieces all within `extent_tol_m`, but not complete.
  - otherwise `miss` / extra-side unmatched behavior.
- Lateral-only exact-length drift, e.g. 0.2 m with `position_tol_m=0.30` and `complete_eps_m=0.05`, now scores `within_tol`, not `complete`.
- `src/agent/judge/correction_score.py` reuses the shared wall matcher, so correction wall classification follows the same rule.

## Sidecar Schema

- Bumped `SCORER_SCHEMA` in `scripts/tool_scripts/run_stage.py` from `6` to `7`.
- Serialized the new wall drift flags in wall records so old sidecars recompute and renderer has enough information for band shape.

## Renderer Change

- Updated `scripts/tool_scripts/render_grade.py`.
- Within-tol plane-wall orange band is now GT-based acceptance geometry:
  - lateral drift: strip around GT wall, perpendicular half-width `position_tol_m`, spanning GT extent.
  - extent drift: endpoint acceptance bands extending by `extent_tol_m` at the drifted end(s).
  - both drifts: widened GT rectangle with `position_tol_m` lateral half-width and `extent_tol_m` extension at both ends.
- Product overlays remain drawn at product coordinates.
- Lateral-drift matched product spans render orange rather than green.
- Within-tol missing pieces remain dashed; extra pieces remain solid.

## Tests

Added/updated focused coverage:

- `tests/test_reading_score.py`
  - exact-length wall laterally shifted by 0.2 m scores `within_tol`, with `lateral_drift=True`, not `complete`.
- `tests/test_render_grade.py`
  - lateral wall drift draws an orange acceptance strip and orange product line.
  - within-tol missing piece remains dashed.
- Updated schema fixtures to `7`.

Full suite:

```text
468 passed, 9 xfailed, 90 warnings in 97.70s
```

Targeted suite:

```text
45 passed, 18 warnings
```

## Demo Render

Re-rendered plane-states sheet with:

- exact-length x=5 wall cluster laterally shifted by 0.2 m -> `within_tol`, lateral band;
- short wall endpoint drift;
- long wall extra piece;
- missing wall segment;
- extra wall.

Output:

```text
AI_agent/logs/review/renders/2026-07-03_elevation_grade/08_plane_states_bandfix.png
```

Observed scorer printout for the new demo case:

```text
orientation=v coord=5.0 status=within_tol delta=0.2 lateral_drift=True extent_drift=False
```

## REVIEW-ASK

Please review the two-axis wall classification and the GT-based orange acceptance band rendering, especially the `within_tol` lateral-only case and the dashed missing-piece invariant.
