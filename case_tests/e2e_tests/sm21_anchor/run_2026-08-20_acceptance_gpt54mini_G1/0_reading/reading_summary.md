# Reading Summary

## Confidence

- `2f_view`: medium-high. The wall network and windows were measurable from the clean vector linework, and the repeated lower dimension labels plus wall-thickness callouts were still readable with care.
- `South_view`: high. The facade, floor bands, and window groups were clear after axis-specific calibration.
- `North_view`: medium-high. The window grouping was clear, but the lower-left opening was interpreted as an entrance and logged instead of traced as a window.
- `East_view`: medium. The facade is simple, but the lower centered opening is better treated as a door/entrance than a window.
- `West_view`: medium. The facade is simple, but the lower opening reads more like a door than a glazed window.

## Repeated null / unknown fields

- `scale_origin` stayed `null` for all elevations, as required by the schema.
- `facade` stayed `null` for the plan view.
- `ocr_texts` is populated on `2f_view` with wall-thickness callouts; the elevations stayed text-free.
- `thickness_m` stayed `null` for all plan wall strokes.

## Schema feedback

- The plan/elevation split works well, but repeated mirrored dimension chains on the same drawing are easy to overcount; a clearer chain grouping rule would help.
- Elevation door openings are still awkward to represent cleanly when the wall fill remains continuous. A dedicated opening/door note field would reduce ambiguity.
- For clean CAD drawings, separate axis calibration is reliable and avoids false cross-axis disagreement warnings.
