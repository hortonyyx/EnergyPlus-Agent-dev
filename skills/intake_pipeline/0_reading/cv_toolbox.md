# CV Toolbox For Reading Evidence

Use the CV toolbox before drawing semantic reading JSON for clean vector CAD PNGs. On noisy scans, hand drawings, or other degraded inputs, defer the required/optional judgment until a robustness profile exists. The tools measure image-local candidates only. They do not classify building elements, write reading JSON, or produce final geometry.

## Tools

- `crop_zoom`: crop a half-open source bbox `[x0,y0,x1,y1)` and record the inverse transform chain so crop-local pixels can be restored to the source image.
- `wall_line_profiler`: apply the clean-vector gray mask, project rows or columns, and return wall-line candidates with prominence strength and FWHM width.
- `px_m_calibrator`: convert dimension spans into `px_per_m` with forced-origin least squares and per-anchor residuals when multiple anchors are supplied. When both x and y anchors are present, their independently fitted scales must agree within the measured clean-vector ceiling (0.30% relative deviation); the tool raises before blending if they do not.
- `window_cc_detector`: label 8-connected clean-vector components, filter by area/shape, merge nearby boxes, and return window-rectangle candidates.
- `storey_line_profiler`: row-projection wrapper for horizontal storey-line candidates.
- `overlay_logger`: draw accepted, rejected, and undecided candidates and preserve each decision reason.

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

- Calibrate first. Before any meter coordinate is written, establish px-to-m scale for that drawing. Calibration anchors must be dimension-chain extension lines or ticks located with high-zoom `crop_zoom`, not wall endpoints or text baselines. Target residual is at most 1 px; if residuals exceed that, refine the anchors before writing meter geometry. A cross-axis disagreement error means at least one endpoint pair or transcribed dimension is wrong; do not average or reuse that result.
- Measure before drawing. Wall lines, window boxes, storey lines, and similar coordinates must come from tool measurement such as projection, connected components, tick candidates, or verified crop measurements. Do not write pure eyeballed coordinates when the clean-vector toolbox applies.
- Use one px-to-m formula and leave enough provenance to reproduce it: `v_m=(px-origin_px)/px_per_m`. Notes for measured strokes should include the source pixel coordinate, origin, converted result, and sidecar/candidate reference. Non-reproducible numbers are invalid data.
- Treat profiler outputs as candidates. Classify semantics with `reading_guide.md`, then log accept/reject decisions with reasons using `overlay_logger` or the reading sidecar. Rejected candidates are evidence, not clutter to delete.
- Verify candidate crops before accepting them. For each material candidate set, inspect crops or overlays, accept only the semantically correct elements, and record rejected candidates with a reason. The recognition and pen rules remain in `guide.md` §0.1 and `pen_library.md`; this file only adds the CV measurement discipline.
- For un-dimensioned elements, calibrated pixel measurement is measurement, not guessing. The `provenance` vocabulary is closed — `seen | dimension_derived | estimated | unknown`, and nothing else validates; there is no separate "pixel-measured" value. Record such strokes as `seen`, leave `dimension_refs` empty, and cite the relevant CV sidecar/candidate in the notes so the number stays reproducible. Reserve `estimated` for coordinates you did not measure.
- `dimensions[].anchor` is a flat pixel bbox list: `[x0,y0,x1,y1]`. Do not replace it with a custom object shape.

This batch does not test weak-VLM dimension transcription or OCR robustness. Dimension text remains a reading responsibility unless a later OCR tool is added.
