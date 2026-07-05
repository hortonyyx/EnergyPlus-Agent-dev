# Grade Visual Model Spec Design Review

Verdict: **APPROVE-WITH-CHANGES**

The design is directionally right: Batch 1 mostly proves that a renderer can be sidecar-driven for plan walls, plan windows, and elevation windows without borrowing gt to draw product geometry. The sidecar now carries product wall segments, product plan-window spans, and product elevation boxes (`scripts/tool_scripts/run_stage.py:426-499`). That satisfies the central red-line goal for those elements.

However, several spec-level semantics are still underspecified or actively unsafe. The highest-risk issue is the elevation-window overlap denominator: `intersection / min(area)` can grade badly wrong-size windows as complete. There are also unresolved contradictions around red dashed miss geometry vs "colors only on product", incomplete floor-line product evidence, and ambiguous topology for split/merged plan wall segments. These should be fixed before Batch 2 makes the renderer authoritative.

## Findings

1. **MAJOR - SPEC: elevation-window `intersection / min(area)` is not a correctness metric.**

   The spec defines overlap ratio as intersection area divided by the smaller box area (`2026-07-04_grade_visual_model_spec.md:58-68`), and Batch 1 implements exactly that (`src/agent/judge/elevation_score.py:480-489`). This means a tiny product box fully inside the gt box has ratio 1.0, and a much larger product box fully covering the gt box also has ratio 1.0. Batch 1 already codifies the latter behavior: a 1.5 m product window over a 1.0 m gt window is asserted `complete` with `width_delta=0.5` only as evidence (`tests/test_elevation_score.py:171-181`).

   This breaks the meaning of green = complete. It also makes the old per-axis size checks non-binding: width/head/sill deltas are reported but cannot prevent a wrong-size nested/covering box from passing (`src/agent/judge/elevation_score.py:512-528`).

   Recommended change: replace the single min-area ratio with a two-sided coverage rule. For example:
   - `gt_coverage = intersection_area / gt_area`
   - `product_coverage = intersection_area / product_area`
   - complete only if both are `>= overlap_complete`
   - within_tol only if both are `>= overlap_accept`

   Alternatively use IoU, but two-sided coverage better preserves the current intuition while closing both tiny-inside and huge-cover cases. Keep along/sill/head/width deltas as evidence, but do not let them be the only guard against wrong size.

2. **MAJOR - SPEC: red dashed misses contradict "colors only on product" unless explicitly modeled as judge annotations.**

   The spec says colors are applied only to product (`2026-07-04_grade_visual_model_spec.md:24-36`) and that gt is always a gray base, never separately recolored (`2026-07-04_grade_visual_model_spec.md:18-20`). But the same spec requires miss geometry at gt locations: plan linear position miss is "miss(gt red dashed) + extra(read red solid)" (`2026-07-04_grade_visual_model_spec.md:46`), and elevation-window miss is "read box red solid + gt red dashed" (`2026-07-04_grade_visual_model_spec.md:68`).

   These are not product elements. They are gt-derived diff annotations. That is probably the desired visualization, but it must be stated as an explicit exception to the red line. Otherwise Batch 2 has two incompatible instructions: either never color gt and let gray show through, or draw red dashed miss ghosts from gt geometry.

   Recommended change: rewrite the red line as:
   - product geometry must never be synthesized or moved from gt;
   - gt may be used for the gray base and for explicit miss annotations only;
   - miss annotations are not product geometry and must be styled dashed so they cannot be mistaken for product.

   Also decide whether small "complete" gaps rely only on gray show-through or whether sub-`complete_eps` miss pieces are suppressed entirely.

3. **MAJOR - SPEC/BATCH-1: floor/ground/roof lines lack a complete product-diff model.**

   The spec says elevation horizontal lines are product band edges vs gt z lines (`2026-07-04_grade_visual_model_spec.md:72-76`, `:100-102`), but it only defines gt-line misses. It does not define red-solid extra product horizontal lines, no-data behavior, or what counts as product evidence when `wall_fill` is absent.

   Batch 1 exposes the gap:
   - reading floor-line product comes only from `wall_fill` y edges (`src/agent/judge/elevation_score.py:305-318`);
   - if no `wall_fill` exists, `_match_floor_lines` returns `[]`, not gt misses or explicit no-data records (`src/agent/judge/elevation_score.py:271-302`);
   - unmatched product floor-line candidates are dropped after matching, so the sidecar cannot render red-solid extra horizontal lines (`scripts/tool_scripts/run_stage.py:502-550`).

   This violates the "miss dashed / extra solid" universal color rule and makes "gray truth shows through" ambiguous: absent `wall_fill`, a facade can have elevation windows but no floor-line grade geometry.

   Recommended change:
   - sidecar should carry `product_floor_lines` per facade, `gt_floor_lines`, matched records, and unmatched product extras;
   - define no-data separately from miss. Missing elevation view can be no-data; present elevation view with no product floor-line source should either be explicit no-data or explicit miss, but the spec must choose;
   - Batch 1 should serialize extra product lines so Batch 2 can draw red-solid extras without rereading product output.

4. **MAJOR - SPEC: plan wall piece model needs a topology rule for multiple colinear gt segments and split/merged product strokes.**

   The spec describes "gt wall extent" as two ends of a line (`2026-07-04_grade_visual_model_spec.md:44-54`) and Batch 1 derives gt wall segments from merged rectangular zone edges (`src/agent/judge/reading_score.py:158-170`). That works for simple axis-aligned segments, but it is underspecified for common topology cases:
   - one product stroke spans multiple gt segments separated by a gap;
   - several product strokes cover one gt segment;
   - a partition is represented by multiple zone edges that merge or only partially overlap;
   - future non-rectangular/skew cases.

   Batch 1 currently does one-to-one association per gt segment (`src/agent/judge/reading_score.py:465-521`). A continuous product wall crossing a gt gap can be matched to one gt segment, counted extra over the gap and the next gt segment, while the next gt segment is also a miss. That double-counts covered truth as both missing and extra in some split cases.

   Recommended change: define plan linear scoring per `(orientation, lateral-coordinate cluster)` as interval-set comparison rather than per-record one-to-one. After position association, compare the union of product intervals against the union of gt intervals on that coordinate; emit matched/missing/extra pieces from the set difference. If one-to-one is intentionally retained, the spec must state that split/merged strokes are penalized this way and add regression tests for crossing-gap and multi-stroke-cover cases.

5. **MAJOR - SPEC/BATCH-1: complete/within tolerances can produce contradictory status vs pieces.**

   The spec says if both ends are within `complete_eps`, the whole element is green (`2026-07-04_grade_visual_model_spec.md:47-54`). Batch 1 computes pieces independently from status (`src/agent/judge/reading_score.py:423-462`). Therefore a near-exact complete element can still carry small `missing` or `extra` pieces marked within tolerance. A renderer that follows `pieces` will draw orange/red-ish fragments on an element whose status says complete; a renderer that follows status will ignore piece evidence.

   Recommended change:
   - enforce `0 <= complete_eps_m <= extent_tol_m`, `overlap_accept <= overlap_complete`, and all tolerances nonnegative in `GradeConfig`;
   - if status is `complete`, suppress sub-`complete_eps` missing/extra pieces or mark them as diagnostic-only and instruct the renderer to draw the full product as green;
   - add tests for near-exact complete with one short end and one long end.

6. **MAJOR - SPEC: elevation orientation/reflection is not reconciled with "product geometry is never moved."**

   Batch 1 evaluates aligned and flipped reading elevation orientations and chooses the better score (`src/agent/judge/elevation_score.py:689-741`). The serialized `product_box` is the oriented box, while `source_span` preserves the raw input span (`scripts/tool_scripts/run_stage.py:454-470`). This is useful, but the spec does not mention it.

   A gt-selected flip can move a product box in the rendered scoring frame. That may be acceptable as a facade-coordinate normalization step, but it is not the same as drawing the raw product geometry. Without an explicit rule, the red-line principle is too easy to misread.

   Recommended change: define `product_box` as "product geometry normalized into the scorer's facade coordinate frame" and require `source_span`/raw geometry to be retained for audit. Also state whether the renderer should draw normalized `product_box` only, or whether it should show a cue when an orientation flip was selected from gt comparison.

7. **MINOR - SPEC/BATCH-1: elevation vertical boundary mapping is directionally right but should be serialized explicitly.**

   The spec correctly says N/S elevation left/right edges come from W/E plan boundaries, and E/W from S/N (`2026-07-04_grade_visual_model_spec.md:72-76`). The plan boundary sidecar has enough product coordinates per floor to support this (`scripts/tool_scripts/run_stage.py:584-588`). But Batch 2 would still have to infer elevation boundary geometry from plan score records plus mapping rules.

   Recommended change: add an explicit elevation-boundary section to the sidecar, or at minimum specify the exact renderer mapping:
   - North/South: left = W, right = E, product x = boundary read coordinate;
   - East/West: left = S, right = N, product x = boundary read coordinate;
   - no plan boundary data must render as no-data/reference gray, not as green or red.

8. **MINOR - SPEC: plan window association no longer has an explicit lateral-position gate.**

   The spec groups walls and plan windows under "position first, extent second" (`2026-07-04_grade_visual_model_spec.md:40-54`). Batch 1 plan-window matching is overlap-based along the facade span (`src/agent/judge/reading_score.py:528-593`), while facade assignment uses hardcoded near-boundary extraction. That may be fine, but it is not the same as the stated two-stage position/extent model.

   Recommended change: specify that plan windows are first assigned to a facade lane, then compared as 1D interval sets along that lane. If a configurable lateral distance to facade is part of the grade, add it to `GradeConfig`; if not, remove plan windows from the generic "position_tol" wording.

9. **MINOR - SPEC: v1 rectangular/cardinal scope should be stated as an explicit limitation.**

   The current model relies on rectangular zone `rect_m`, cardinal facades, N/S using footprint width, E/W using footprint depth, and axis-aligned wall strokes. That is consistent with `sm21_anchor`, but it is a real v1 constraint. The spec says non-goals include not touching world solving (`2026-07-04_grade_visual_model_spec.md:115-119`), but it does not explicitly say skewed/non-orthogonal footprints and non-rectangular zones are out of scope.

   Recommended change: add a v1 scope paragraph: "Plan walls are axis-aligned maximal intervals from rectangular gt zones; elevations are cardinal facade rectangles. Skew, curved, non-cardinal, and polygonal partition support requires a future segment/polyline model."

10. **MINOR - BATCH-1: `test_gt_discipline` covers the new gt reader but not the renderer contract.**

   The new `elevation_score.py` is included as an allowed judge-side gt reader (`tests/test_gt_discipline.py:68`). That is enough for gate① leakage discipline. It does not test the red-line renderer contract, which is the key risk in this spec.

   Recommended change for Batch 2: add renderer tests that fail if product wall/window/elevation geometry is drawn from gt extents instead of `product`, `product_box`, `pieces`, and explicit product floor-line records. The current renderer still contains old gt-derived drawing paths, but that is already acknowledged as pre-Batch-2 work.

## Approval Conditions

Before Batch 2 renderer rewrite, update the spec and scorer sidecar contract for:

1. two-sided elevation window overlap or IoU;
2. explicit miss-annotation exception to the "colors only on product" language;
3. floor-line extras/no-data/product-line serialization;
4. interval-set semantics or explicit one-to-one semantics for split/merged plan linear elements;
5. tolerance ordering and complete-vs-piece rendering rules.

With those changes, the design is sound enough for the renderer rewrite. Without them, the renderer can be red-line compliant mechanically while still producing misleading green geometry and incomplete diff evidence.
