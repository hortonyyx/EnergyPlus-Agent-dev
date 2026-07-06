# C2 Orthogonal Polygon Design Review

Verdict: **APPROVE-WITH-CHANGES**. The direction is right, but B0-B6 should not start until the changes below are folded into the design. Review used the local working tree only.

Verification: `pytest --collect-only -q` collected 505 tests. I also ran a read-only parent-wall pre-scan over 28 local `correction_geometry*.json` files: buildable files had 0 non-unique parent-wall candidates; one existing sm24 raw correction already fails current attachment (`win_east_2: no exterior wall on East for cell_office_right_small`).

## Findings

1. **HIGH - D2 overclaims bbox compatibility; several current consumers treat `Cell.x/y` as authoritative geometry.**  
   Evidence: schema requires bbox fields (`src/agent/correction/schema.py:36` `x: list[float]  # [min, max]`, `:37` `y: list[float]  # [min, max]`) and the prompt still commands rectangles (`src/agent/pipeline.py:316` `Each room is one rectangular cell...`). Safe-ish consumers exist: `_cell_polygon()` already prefers explicit polygon and only falls back to `x/y` (`src/agent/geometry/modelling.py:163-173`), and naming mostly uses `zv.polygon` (`src/agent/geometry/modelling.py:405-417`). Breaking consumers are broader than the design lists: deterministic snap/gap-close reads and writes only bbox endpoints (`src/agent/correction/deterministic.py:726-727`, `:803-815`), envelope boundary attachment mutates bbox edges (`:522`, `:551`, `:645`), window clamp uses bbox span (`:838`), validator coverage/nondegenerate/window-on-wall use bbox (`src/agent/correction/geometry_validator.py:49-50`, `:97`, `:150`), audit signatures ignore polygon (`src/validator/checks/correction.py:156`), and correction-grade scoring derives wall segments/boundaries from bbox (`src/agent/judge/correction_score.py:124-138`, `:156-166`, `:201-209`).  
   Concrete fix: B1 must add shared polygon-first helpers for `cell_axis_values`, `cell_polygon`, `cell_boundary_segments`, and `cell_facade_span`; then use them in deterministic, `geometry_validator`, `check_correction` signatures, and `correction_score`. `x/y` may remain required as bbox projection, but no v2 geometric operation should infer walls, coverage, or window spans from it.

2. **HIGH - D4 should not put the segment model only on `Window`; use a facade segment table plus window refs.**  
   Current code has only an orientation-family enum (`src/agent/reading/schema.py:31` `Facade = Literal["North", "South", "East", "West"]`; `src/agent/correction/schema.py:46` same enum on `Window.facade`) and one frame per facade (`src/agent/correction/facade.py:69-108`). `_find_parent_wall()` currently resolves by facade/span and silently keeps the last match (`src/agent/geometry/modelling.py:301-331`). A window-local optional `{along_range}|segment_id` cannot represent blank facade segments, per-segment envelope evidence, or score/render panels with no windows.  
   Concrete fix: keep the `Facade` enum as the coarse orientation family, but add deterministic `facade_segments` to `CorrectedGeometry`/gt: `{id, facade, floor_or_story, p1, p2, along_range, base_world, normal}`. Windows should carry `facade_segment_id` only. The LLM may choose among deterministic segment ids, but must not invent segment geometry.

3. **MEDIUM - D3 can degrade exactly to current behavior, but only with an explicit compatibility path.**  
   Current reconcile has footprint hard anchors (`src/agent/correction/deterministic.py:264-305`), then mutual-nearest cross-floor matching (`:312-355`), then applies bbox snap and gap-close (`:751-815`). The proposed “intersection-region-only” rule is equivalent for identical footprints only if it preserves the same per-axis candidate graph, fixed anchor semantics, sort order, and audit output.  
   Concrete fix: B2 should either call the existing `_reconcile_cross_floor()` unchanged when all v2 footprints are identical rectangles, or add byte-for-byte regression assertions for sm20/sm21 snapped geometry and audit entries.

4. **MEDIUM - B0-B6 dependencies are mis-ordered.**  
   The table says B3 depends only on B1, but D5 coverage compares cell union to **per-floor footprint** (`AI_agent/proposals/c2_orthogonal_polygon_design.md:38`), so B3 depends on B2 unless it is split into a rectangular advisory helper and a later v2 block gate. B5 depends on B2 as well: per-segment `derive_facade_frame` needs footprint-derived facade segments, not just `Cell.polygon`. B0 also needs all entry points, not only `run_pipeline`: `run_stage.py` still calls `check_kernel(bg, interzone_issues=issues)` without policy profile (`scripts/tool_scripts/run_stage.py:220`), while `build_geometry()`, `build_zone_volumes()`, and `pair_surfaces()` have no profile parameter (`src/agent/geometry/build.py:31`, `src/agent/geometry/modelling.py:337`, `src/agent/geometry/split_pairing.py:44`).  
   Concrete fix: make B3 depend on B2; make B5 depend on B2+B4 and the segment table; include `run_stage.py` plus geometry builder signatures in B0 profile threading.

5. **MEDIUM - D6 scorer generalization is feasible but not a pure refactor of `reading_score.py`.**  
   The current plan scorer is rectangular at every layer: gt walls come from `rect_m` and bbox `W/D` (`src/agent/judge/reading_score.py:166-195`), reading walls are only constant-x/constant-y inside `W/D` (`:271-285`), matching clusters by scalar coord (`:620-636`), and footprint boundary is exactly four sides (`:392-406`). Elevation scoring also uses one `span_limit` from `W_m/D_m` per facade (`src/agent/judge/elevation_score.py:260-264`). `SCORER_SCHEMA` is centralized in `scripts/tool_scripts/run_stage.py:74`.  
   Concrete fix: B4 must update gt schema, `reading_score.py`, `correction_score.py`, score sidecar serialization, and render consumers together. Add `NOT_APPLICABLE` for unsupported shape/schema combos before accepting any C2 case.

6. **MEDIUM - Coverage tolerance needs an area tolerance, not direct reuse of `MIN_EDGE_LENGTH`.**  
   Existing code distinguishes linear sliver thresholds (`src/agent/geometry/modelling.py:26` `_MIN_EDGE = 0.10`) from area tolerances (`src/validator/checks/kernel.py:33` `_AREA_TOL = 0.10`; `src/agent/correction/geometry_validator.py:35` `_AREA_TOL = 0.05`). D9 #4’s “reuse MIN_EDGE_LENGTH” has the wrong unit for polygon union/difference area.  
   Concrete fix: add `coverage_area_tol_m2` to `src/configs/correction.yaml`/A0, optionally paired with a separate linear sliver tolerance. Do not introduce a naked Python constant.

7. **LOW - B0 parent-wall pre-scan should be an acceptance artifact, not a note.**  
   My scan found 0 non-unique candidates among buildable local geometries, but the sm24 raw correction build already fails one East window.  
   Concrete fix: make B0 produce a checked-in or logged pre-scan report over sm20/sm21/sm24 anchors, and decide whether sm24 raw failure is expected pre-C2 data debt or a regression blocker.

## D9 Answers

1. `Cell.x/y` bbox is unsafe as authoritative geometry in deterministic snap/gap-close, envelope reconcile, correction validation, correction scoring, and audit signatures. It is tolerable only for legacy fallback, rough naming quadrant, and count tripwires.
2. D3 degrades exactly only if identical-footprint v2 calls the current reconcile path or proves byte-equivalent output.
3. Prefer `Facade` enum + independent `facade_segments` table + `Window.facade_segment_id`; do not store segment geometry only on windows.
4. Use a named area tolerance (`coverage_area_tol_m2`) plus separate linear sliver guards.
5. Existing buildable anchors do not show parent-wall ambiguity; sm24 raw already has one attachment failure, so pre-scan is cheap and should be formal.

## Invariant Check

Judgment/geometry split is preserved only if facade segments are generated deterministically from footprints and the LLM merely selects a segment id. Single world frame is preserved only if `Window.span` and `facade_segment_id` are explicitly world/segment-frame typed. IntakeOutput can remain unchanged. No-baked-assumptions needs the B1/B4 fixes above; otherwise bbox geometry and rectangular scorer assumptions leak into C2.
