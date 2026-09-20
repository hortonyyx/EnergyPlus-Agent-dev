# CV Toolbox For Reading Evidence

Use the CV toolbox when a clean vector PNG needs pixel evidence before you draw semantic reading JSON. The tools measure image-local candidates only. They do not classify building elements, write reading JSON, or produce final geometry.

## Tools

- `crop_zoom`: crop a half-open source bbox `[x0,y0,x1,y1)` and record the inverse transform chain so crop-local pixels can be restored to the source image.
- `wall_line_profiler`: apply the clean-vector gray mask, project rows or columns, and return wall-line candidates with prominence strength and FWHM width.
- `px_m_calibrator`: convert dimension spans into `px_per_m` with forced-origin least squares and per-anchor residuals when multiple anchors are supplied.
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

- Tools measure; you still classify semantics with `reading_guide.md`. A gray peak is a candidate, not automatically a wall.
- Prefer empty hands over wrong anchors. Low-confidence candidates should stay out of reading JSON rather than becoming false wall/window anchors.
- Log accepted and rejected candidates with reasons. Rejections are useful evidence: mark them `rejected` in `overlay_logger` instead of deleting them from the audit trail.

This batch does not test weak-VLM dimension transcription or OCR robustness. Dimension text remains a reading responsibility unless a later OCR tool is added.
