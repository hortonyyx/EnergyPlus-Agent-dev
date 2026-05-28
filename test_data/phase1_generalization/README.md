# Phase 1 redraw — generalization pretest

A **phase1-only** stress test of the two-step intake redraw on 7 unrelated, real-world
residential floor plans downloaded from the web (different styles / languages / conventions).
This is **not** a full two-step run: no phase2, no downstream, no EnergyPlus. The goal is to see
how well phase1 (`skills/energyplus_mcp_twostep/phase1/`) recognizes structure and excludes clutter
across drawing styles it was *not* designed against (the skill was built on the SmallOffice corpus:
per-floor plans + 4 elevations).

Run date: 2026-05-26. Tracer: Claude Opus 4.7 (the same model class a real phase1 session uses),
applying `guide.md` + `reading_guide.md` + `pen_library.md` as loaded.

## Scope caveat (read before judging fidelity)

These are **single-image, single-floor, plan-only** drawings — there are **no elevations**. The
skill's whole z machinery (`wall_fill` / `outline` / `facade_axis_note` / per-floor z) is therefore
unused, and **window sill/head z is genuinely unknowable** from these inputs. Windows are traced at
their plan position only; z is left absent on purpose (honesty rule). So this exercises the
*plan-reading half* of phase1: walls, windows (x/y), dimension chains, door-healing, clutter
exclusion. It does **not** test elevation translation or full IntakeOutput.

## Layout

```
phase1_generalization/
  testN/
    testN.jpg          original (copied in for side-by-side)
    testN.json         phase1 vector output
    testN.svg          official render (Tool_scripts/render_vector_to_svg.py) — browser, zoomable
    testN_render.png   PIL render — more legible side-by-side
```

## Per-case verdict

| case | style | geometry | units | result |
|---|---|---|---|---|
| test1 | Turkish villa render, beige fill + heavy furniture | rectangular | cm | ✅ clean; 7 windows, 4 doors healed, ~20 clutter items excluded |
| test2 | Spanish 3D render, photoreal furniture + tile | rectangular | m | ✅ clean; green size-badges logged as callouts |
| test3 | **photorealistic 3D**, extruded walls, no labels | rectangular | m | ⚠️ LOW confidence — wall/window/door discrimination at the edge of plan-reading; flagged for rejection in a real pipeline |
| test4 | Turkish villa render | **non-rect: canted SW bay** | cm | ✅ structure clean; bay traced as chamfer polyline + 3 angled bay windows (vertices LOW conf) |
| test5 | Russian CAD line drawing, **grid background**, no furniture | rectangular + L-notch room | m | ✅ clean; grid rejected (key trap); Cyrillic OCR verbatim; 1 door healed |
| test6 | Room Planner app, **watermark**, no furniture | **non-rect: stepped composite** | m | ⚠️ structure attempted; stepped offsets LOW conf (areas ≠ W×H); watermark rejected |
| test7 | Turkish villa render | rectangular | cm | ✅ clean; same quality as test1 |

**Headline result**: across 7 unfamiliar styles, phase1's core disciplines held — zero furniture /
sanitary / paving leaked into `strokes`; windows landed on the right walls; door arcs healed
uniformly; grid + watermark rejected; non-rectangular features were traced as polylines rather than
forced into rectangles. The two genuine weak spots are **photorealistic 3D** (test3) and
**stepped/composite non-rectangular footprints** (test6) — both flagged, not silently mis-traced.

## Cross-cutting findings → skill actions (for plan.md B1.5.b)

1. **Units are not always meters.** test1/4/7 dimension in **cm**, test3 even dimensions wall
   thickness (15 cm). The skill assumes meters. → `reading_guide.md`: add a "detect drawing units
   (mm / cm / m) from the dimension magnitudes + any unit marks, record in `scale_origin.note`,
   convert coords to m, keep dimension `text` verbatim" step. This was handled ad-hoc here; it
   should be an explicit rule.

2. **Plan-only inputs have no z source.** For single-image residential plans, the elevation-based z
   pipeline does not apply. → decide how phase2/intake handles "no elevation supplied": either a
   documented sill/head default heuristic (e.g. sill 0.9 m / head 2.1 m) or an explicit
   "requires elevation for z" gate. Today the skill is silent on plan-only cases.

3. **Non-rectangular is the norm in the wild, not the exception.** test4 bay/oriel, test5 L-notch
   room, test6 stepped composite. Polyline tracing works for perception, but: (a) bay/oriel has no
   vocabulary; (b) composite footprints can't be back-solved from one plan (areas ≠ W×H). → confirms
   plan.md **B5/B6** (non-rectangular + global coords) is real and needed; phase1 polyline is a sound
   stopgap that keeps the data honest.

4. **Photorealistic 3D top-views are high-risk.** Walls-as-extruded-blocks + openings-as-reveals
   push wall/window/door calls to low confidence (test3). → `reading_guide.md`: name this drawing
   class explicitly and recommend rejecting / requesting a 2D line drawing rather than guessing.

5. **Grid backgrounds and app watermarks are concrete false-positive traps.** Both rejected here, but
   the reading guide should list them by name in the ignore-set ("drafting grid" → already under
   grid-axis; "app watermark / logo / URL" → add).

6. **Window-size-label convention `NNN/NNN` = width/height (cm).** Consistent across the Turkish
   plans (test1/4/7): 120/120, 200/190, 60/40, 240/180. A reliable recognition cue worth adding to
   `reading_guide.md` so phase1 reads these as window annotations, not generic dimensions.

7. **Room labels carry an area value** ("10,0 m²", "КОМНАТА 33,1 м²", "HABITACIÓ 31.8 m²"). Cheap and
   consistent to capture; gives phase2 a free sanity check (labeled area vs traced-polygon area).

8. **Semi-outdoor spaces (veranda / terrace)** recur (test1/4/7) with railing-vs-wall boundary
   ambiguity. phase1 traced the drawn edges + flagged thermal role for phase2 — a recurring pattern
   worth one line in the guide so the call is consistent.

## Reproduce

```bash
# re-render any case
python Tool_scripts/render_vector_to_svg.py test_data/phase1_generalization/testN/testN.json
```
