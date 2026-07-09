# CV Toolbox For Reading Evidence

Use the CV toolbox before drawing semantic reading JSON for clean vector CAD PNGs. On noisy scans, hand drawings, or other degraded inputs, defer the required/optional judgment until a robustness profile exists. The tools measure image-local candidates only. They do not classify building elements, write reading JSON, or produce final geometry.

## Tools

- `crop_zoom`: crop a half-open source bbox `[x0,y0,x1,y1)` and record the inverse transform chain so crop-local pixels can be restored to the source image.
- `wall_line_profiler`: apply the clean-vector gray mask, project rows or columns, and return wall-line candidates with prominence strength and FWHM width.
- `px_m_calibrator`: convert dimension spans into `px_per_m` with forced-origin least squares and per-anchor residuals when multiple anchors are supplied.
- `window_cc_detector`: label 8-connected clean-vector components, filter by area/shape, merge nearby boxes, and return window-rectangle candidates.
- `storey_line_profiler`: row-projection wrapper for horizontal storey-line candidates.
- `overlay_logger`: draw accepted, rejected, and undecided candidates and preserve each decision reason.
- `prescan-plan` / `prescan-elevation`: macro probes that emit mechanically neutral pixel candidates and one combined numbered overlay for cold-start triage. Optional triage filters `--min-strength` / `--min-line-len-px` narrow line-band candidates only (ticks are always derived unfiltered — they are calibration anchors); `--label` names the sidecar folder so differently parameterized prescans coexist. `diagnostics.axis_summary` groups the emitted line bands per projection peak (axis, position, strength, run count, coverage, member candidate ids).

## Invocation Examples

```bash
python scripts/tool_scripts/cv_probe.py wall_line_profiler \
  --image case_data/1f_view.png \
  --out-dir 0_reading \
  --axis col
```

```bash
python scripts/tool_scripts/cv_probe.py crop_zoom \
  --image case_data/1f_view.png \
  --out-dir 0_reading \
  --bbox 120,80,620,460 \
  --scale 2
```

```bash
python scripts/tool_scripts/cv_probe.py px_m_calibrator \
  --image case_data/1f_view.png \
  --out-dir 0_reading \
  --anchors-json '[{"axis":"x","px_a":100,"px_b":700,"value_m":15.0,"dimension_ref":"overall_width"}]'
```

```bash
python scripts/tool_scripts/cv_probe.py window_cc_detector \
  --image case_data/South_view.png \
  --out-dir 0_reading \
  --min-area 30
```

Sidecars are written under `0_reading/cv_evidence/<image_stem>/NNN_<tool>.json` with a matching overlay PNG. In this batch that directory is a flat-stage audit sidecar only; attempts/report collection may archive it in future work.

## Disciplines

- Calibrate first. Before any meter coordinate is written, establish px-to-m scale for that drawing. Calibration anchors must be dimension-chain extension lines or ticks located with high-zoom `crop_zoom`, not wall endpoints or text baselines. Target residual is at most 1 px; if residuals exceed that, refine the anchors before writing meter geometry.
- Reuse calibration within a same-scale group, never across groups. Drawings exported together usually share scale within a kind (all plans one scale, all elevations another — the two groups routinely differ, so blind reuse across kinds is a gross scale error). To reuse: calibrate one drawing of the group fully, then on each sibling verify with a single spot-check anchor (predicted px span from the reused `px_per_m` vs measured, within ~1 px). If the spot check passes, reuse and cite the source calibration sidecar in your notes; if it fails, calibrate that drawing fully.
- Budget prescan candidates. On clean vector CAD, run prescan with `--min-strength 0.08 --min-line-len-px 30` and verify at the axis level using `diagnostics.axis_summary` (one crop per peak band, not one per segment). On elevations add `--no-cc` (elevation prescan components are text glyphs plus one merged outline; window rectangles come from `window_cc_detector`, not prescan). If an element you expect has no surviving candidate, re-run prescan unfiltered under a different `--label` (e.g. `prescan_full`) or probe the region with `crop_zoom` + a profiler — the filter is a triage budget, not a detection verdict.
- Measure before drawing. Wall lines, window boxes, storey lines, and similar coordinates must come from tool measurement such as projection, connected components, tick candidates, or verified crop measurements. Do not write pure eyeballed coordinates when the clean-vector toolbox applies.
- Use one px-to-m formula and leave enough provenance to reproduce it: `v_m=(px-origin_px)/px_per_m`. Notes for measured strokes should include the source pixel coordinate, origin, converted result, and sidecar/candidate reference. Non-reproducible numbers are invalid data.
- Treat prescan and profiler outputs as candidates. Classify semantics with `reading_guide.md`, then log accept/reject decisions with reasons using `overlay_logger` or the reading sidecar. Rejected candidates are evidence, not clutter to delete.
- Verify candidate crops before accepting them. For each material candidate set, inspect crops or overlays, accept only the semantically correct elements, and record rejected candidates with a reason. The recognition and pen rules remain in `guide.md` §0.1 and `pen_library.md`; this file only adds the CV measurement discipline.
- For un-dimensioned elements, calibrated pixel measurement is measurement, not guessing. Record honest provenance such as `pixel-measured`, leave `dimension_refs` empty, and cite the relevant CV sidecar/candidate.
- `dimensions[].anchor` is a flat pixel bbox list: `[x0,y0,x1,y1]`. Do not replace it with a custom object shape.

This batch does not test weak-VLM dimension transcription or OCR robustness. Dimension text remains a reading responsibility unless a later OCR tool is added.
