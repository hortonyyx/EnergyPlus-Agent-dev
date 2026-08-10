I am doing **the reading stage of the staged intake pipeline: redraw the source image with semantic pens** — trace
every visible structural stroke by type (wall / window / wall_fill / outline pen) and do **no spatial-topology
reasoning** at all.

## Mental model
The reading stage = "re-trace the source image with semantically labeled pens". It does NOT enclose strokes into
rooms / judge exterior-vs-interior / say a window belongs to a wall / place anything in world coordinates. **All
topology + world placement is the downstream stages' job.**

## Error budget (key)
The reading stage sees the image; downstream stages do not. Perception errors can only be caught here. **Prefer
null over guessing.** Plan walls have no thickness (`thickness_m`=null). Do not copy testdata content into the JSON
(reflect only what the image shows).

## Task
1. Read the three skill docs (required): `skill/{guide.md, reading_guide.md, pen_library.md}`.
2. One JSON per image, written to `<OUT_DIR>/<name>_view.json`; plans `image_kind=plan`, elevations `=elevation`.
   The six images live in `images/`: `1f_view.png`, `2f_view.png` (plans); `South_view.png`, `North_view.png`,
   `East_view.png`, `West_view.png` (elevations).

## Core discipline
- plan legal pens = `wall`/`window`; elevation = `wall_fill`/`window`/`outline`. No `other`/`door` pen.
- Heal door openings into one continuous wall (note it in `uncaptured_visual_elements`).
- Elevation wall body = one `wall_fill` per floor.
- Forbidden fields: `is_exterior`/`parent_wall_id`/`rooms[]`/any "belongs to / faces out / encloses".
- Stairs/columns/grids/furniture → recognize then log in `uncaptured_visual_elements`, NOT traced.
- One stroke per continuous wall. Fill null when not found. OCR verbatim.
- For elevations, emit the image-local facade fields (`view_facade` from the trusted image name; do NOT write
  east/west into the in-image axis). World axis/sign is derived later by 1_correction — not your job.

## Workflow
Do one pilot image first, then batch the rest (no human in the loop here — proceed after the pilot). Finally write
`<OUT_DIR>/reading_summary.md` (per-image confidence + repeatedly-null fields + schema feedback).

## Boundaries
Work ONLY inside your assigned `<OUT_DIR>` and read ONLY from `images/`, `skill/`, `testdata_prompt.json`. Do not
read any other directory, any ground-truth file, any other reading output, or anywhere in the repository. Do not
run any pipeline or EnergyPlus. Do not produce IntakeOutput fields.
