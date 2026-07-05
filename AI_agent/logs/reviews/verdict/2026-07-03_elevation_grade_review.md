# Elevation Grade Proposal Review

Verdict: **APPROVE-WITH-CHANGES**

I verified this against the local working tree at `/workspaces/EnergyPlus-Agent-dev`; the proposal itself is a local untracked file, not a GitHub copy. The high-level direction is sound: elevation windows need an authoritative `(along, z)` grade, the plane-window grade should remain as secondary evidence, and the grade must stay judge-side without calling `derive_facade_frame`. The proposal is not implementation-ready as written because several details are load-bearing and currently underspecified or contradicted by the local gt.

1. **MAJOR — The motivating S7 example contradicts the local ratified gt.**

   The proposal says South/Floor 1 S7 reads `z=[1.5,2.1]` while gt is `1.0/2.6`. In the local tree, `case_tests/test_baseline/gt/sm21_anchor/gt.json` stores the first South/Floor 1 opening at `x_m=3.44`, `width_m=1.2`, `sill_m=1.5`, `head_m=2.1`, and `tests/test_gt_from_dxf.py` explicitly asserts that the small South/F1 window has its own raised sill/head. The real `South_view.json` reads the same `z=[1.50,2.10]`, so S7 is a vertical hit, not the gap example.

   Recommended change: correct the proposal and tests to use per-opening gt z as authoritative. Add a regression that South/F1 S7 is scored as a z hit, and use a synthetic or different fixture for vertical-drift examples. The scorer must prefer `opening.sill_m/head_m` and only fall back to facade-level `entry.sill_m/head_m` for legacy data with explicit no-data evidence.

2. **MAJOR — Define match vs accuracy semantics before implementation.**

   The design says "hit / miss / extra" plus sill/head deltas, but not whether a window with correct along-position and bad z is a hit or miss. If z is part of the gate, vertical drift disappears as miss+extra; if z is only reported after an along-only hit, bad z can still look like a placed hit.

   Recommended rule:
   - First associate windows with a candidate match, using facade plus normalized orientation, then a tolerant candidate predicate: `abs(read_along_center - gt_along_center) <= elevation_along_tol_m` and a loose vertical sanity check such as interval overlap or same/adjacent floor band with boundary slack.
   - A candidate pair is a **placed hit** only when `along_center`, `sill`, `head`, and preferably width/edge deltas are all within their tolerances.
   - A candidate pair outside z tolerance is **matched_with_z_drift** (or equivalent): count it as not accurately placed for `elevation_windows_placed`, but do not double-count it as both gt miss and read extra.
   - No candidate for a gt opening is a **miss**. Unmatched read windows are **extras**.
   - The sidecar should expose both `matched_total` and `placed_hit_total`, plus per-window deltas and status.

3. **MAJOR — z-band floor binning is too fragile as a hard pre-match step.**

   The proposal bins reading windows by z-center into `[z_floor, z_floor+ceiling]`. That works for clean sm21 windows, including unequal heights F1=3.0 and F2=3.6, but it fails noisily for boundary cases: a window straddling `z=3.0`, a read sill/head shifted enough to put the center on the wrong floor, or a center exactly on a shared boundary.

   Recommended change: for reading elevation windows, match per facade against all gt openings first with a z-aware cost/predicate, then assign the matched floor from the gt opening. Use z-center bands only for unmatched extras and reporting, with half-open bands `[z_floor, next_z_floor)` and top-floor inclusive handling. For correction windows, use `Window.floor` through the existing floor map as the primary floor identity and compare `Window.z` as absolute z; do not re-bin correction windows by their possibly-wrong z.

4. **MAJOR — The coordinate model is sound for current rectangular cardinal gt, but the #6 extensibility claim overreaches.**

   Current gt and code bake in cardinal rectangular assumptions: `derive_gt_windows()` documents `x_m` as world-x for N/S and world-y for E/W, and `render_grade._facade_span_limit()` takes N/S span from footprint `W_m` and E/W from `D_m`. That is fine for sm21 and can still be treated as local along-distance without constructing world points, but it is not yet skew/faceted/non-square safe.

   Recommended change: state v1 support honestly as "cardinal facades with gt `x_m` already normalized to facade-local along distance." For future #6, add explicit gt facade metadata such as facade id, local length, and local opening coordinate system or segment polyline. Also have the reading scorer verify that elevation `x_range_m` is metric and anchored to `[0, span_limit]` using wall_fill/envelope or dimension evidence; A1 reflection handles direction, not arbitrary origin/scale.

5. **MAJOR — Flip-robust matching needs a precise global algorithm.**

   The reflection must map an interval `[a0,a1]` to `[span_limit-a1, span_limit-a0]`; reflecting endpoints independently without reordering will invert spans. Orientation should be selected once per facade/view, across all floors on that facade, not per window. Use a deterministic score such as: maximize placed hits, then matched pairs, then minimize total normalized cost; break ties toward `aligned` and report `orientation=ambiguous` when scores are equal or near-equal.

   Recommended change: codify the above. This prevents a half-wrong reading from being rescued window-by-window. Also scope A1 carefully for correction: `CorrectedGeometry.Window.span` is already a world-frame along span, so a flipped correction should not silently pass as "not a per-window miss" without separate orientation evidence, because the modeled geometry would be mirrored.

6. **MAJOR — Keep elevation scoring out of `FloorScore.windows`.**

   `FloorScore` is the current plan/secondary shape: `windows` contains only along spans, and `score_policy.reading_score_criteria()` treats `FloorScore.window_hits()` as the existing `windows_placed` evidence. Adding z-rich elevation matches directly there risks corrupting the plane path and existing renderer/policy assumptions.

   Recommended change: create a separate elevation score structure, likely in a new `src/agent/judge/elevation_score.py`, with explicit `ElevationWindowMatch` / facade result dataclasses. Keep current `scores` as plan-derived secondary evidence, and add a top-level sidecar section such as `elevation_scores` or `elevation`. Then derive the new advisory criterion from that section only. Bump `SCORER_SCHEMA`.

7. **MAJOR — Renderer sidecar-driven-only requires complete elevation boxes in the sidecar.**

   Current `_draw_elevation_panel()` borrows gt heights via `_window_meta()` and draws read spans at gt sill/head, which is exactly the fake panel the proposal wants to remove. A sidecar-driven renderer cannot recompute or look up window z for status.

   Recommended change: each elevation match in `score_vs_gt.json` should carry full boxes: `truth.span`, `truth.z`, `read.span`, `read.z`, deltas, status, source stroke/window id, floor, facade, and chosen orientation. The renderer may use gt for the building envelope and floor reference lines only, not for window height decisions. If the elevation sidecar section is absent, draw "no elevation score" instead of falling back to the old fake panel. Also label the existing plan row as "plan-derived / secondary."

8. **MINOR — Advisory-only and gt discipline are compatible, but need guard tests.**

   `StageVerdict` and `CriterionVerdict` already use `extra="forbid"`, and `run_stage.py` already passes `score_criteria` as judge-packet evidence while saying StageVerdict remains authoritative. The design should keep `elevation_windows_placed` in `score_criteria` only.

   Recommended change: add tests that the new criterion appears in `score_vs_gt.json` / judge packet, never as a `StageVerdict` field, and that `tests/test_gt_discipline.py` remains green. New gt readers should stay under `src/agent/judge/` or tool-side judge rendering only; do not import them from validator, pipeline, execution, or correction modules.

9. **MINOR — Zero-window and no-data semantics must be explicit.**

   sm21 has West/Floor 1 with `count=0`. That should not look like missing scorer data. Conversely, a missing facade key or missing elevation view should be no-data evidence, not a pass.

   Recommended change: emit explicit empty `matches=[]` and `extras=[]` for every facade/floor combination, including zero-window truth. Empty gt plus no read windows is pass; empty gt plus read windows is extra; missing sidecar/facade/view is no-data. Preserve the current renderer distinction tested by `test_render_grade_empty_facade_is_not_no_data`.

10. **MINOR — Grade config and cache identity need the new tolerances threaded end-to-end.**

   `GradeConfig` currently carries only `wall_tol_m` and `window_centre_tol_m`, and sidecar reuse keys on `tolerances`. The proposal calls for `elevation_along_tol_m`, `sill_tol_m`, and `head_tol_m`; these must be parsed, serialized into sidecar `tolerances`, used by the scorer and policy evidence, and included in strict sidecar reuse checks.

   Recommended change: extend `GradeConfig.as_tolerances()`, update `run_config.yaml` parsing tests, and bump `SCORER_SCHEMA` so old sidecars cannot render as if they contain authoritative elevation scores. Consider adding a width/edge tolerance now, or explicitly mark width as reported-only.

11. **MINOR — Extraction should use elevation rectangles, not the plan segment normalizer.**

   `reading_score._as_segment()` collapses rects to midlines for the current plan scorer. Elevation windows need the full `x_range_m/y_range_m` rectangle to preserve sill/head. Reusing `_as_segment()` would erase the new z signal.

   Recommended change: implement elevation-specific extraction that accepts `pen="window"` rects with valid numeric `x_range_m` and `y_range_m`, preserves source stroke ids, and reports unusable shapes as scorer evidence. Legacy line windows without z should be no-data or extras, not silently converted to fake z boxes.

Summary: approve the architecture, but fix the gt example, specify matching/floor/orientation semantics, keep the new score shape separate from `FloorScore`, and make the renderer consume only complete elevation match records from the sidecar.
