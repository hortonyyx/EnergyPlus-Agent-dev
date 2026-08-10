I am doing **the reading stage of the staged intake pipeline: redraw the source image with semantic pens** — trace
every visible structural stroke by type (wall / window / wall_fill / outline pen) and do **no spatial-topology
reasoning** at all.

## Mental model
The reading stage = "re-trace the source image with semantically labeled pens". It does NOT enclose strokes into
rooms / judge exterior-vs-interior / say a window belongs to a wall / place anything in world coordinates. **All
topology + world placement is the downstream stages' job.**

## Error budget (CRITICAL — coordinate fidelity is on you)
The reading stage sees the image; downstream stages do NOT. **Perception errors can ONLY be caught here.** Once you
misread a dimension, **offset a coordinate**, flip an axis, or miss a stroke, no downstream stage can backtrack — it
takes what you wrote as truth. **Do NOT rely on a "surviving dimension chain" to let correction recover an offset
coordinate** — your job is to read every coordinate *correctly the first time*, to the precision the drawing's
dimension chain supports. **Prefer null over guessing** (null = honestly "not dimensioned / couldn't see it"; a
guessed number is contamination). Plan walls have no thickness (`thickness_m`=null). Do not copy testdata content
into the JSON (reflect only what the image shows).

### Anchor your coordinates against the dimension chain and testdata
- Read the explicit **dimension chain** on each drawing and use it to fix coordinates. When a coordinate is the sum
  of chained segments, write the **arithmetic into the stroke's `note`** (e.g. `note: "x = 0 + 3.6 + 1.8 = 5.4 per
  bottom dim chain"`), so the coordinate is auditable and you are forced to actually add the chain rather than
  eyeball the pixel position.
- Use `testdata_prompt.json` only as a **sanity anchor** (NOT to copy in): it gives floor area 240 m² over 2 floors
  → ≈120 m² per floor. After tracing the plan footprint, check your read total footprint area is consistent with
  this. If your footprint is off by more than a tick, you misread the dimension chain — re-read before writing.

## Task
1. Read the three skill docs (required): `skill/{guide.md, reading_guide.md, pen_library.md}`.
2. One JSON per image, written to `<OUT_DIR>/<name>_view.json`; plans `image_kind=plan`, elevations `=elevation`.
   The six images live in `images/`: `1f_view.png`, `2f_view.png` (plans); `South_view.png`, `North_view.png`,
   `East_view.png`, `West_view.png` (elevations).

## Core discipline
1. plan legal pens = `wall`/`window`; elevation = `wall_fill`/`window`/`outline`. No `other`/`door` pen.
2. Heal door openings into one continuous wall (note it in `uncaptured_visual_elements`).
3. Elevation wall body = one `wall_fill` per floor; split by the dimension chain's per-floor z ranges.
4. Forbidden fields: `is_exterior`/`parent_wall_id`/`rooms[]`/any "belongs to / faces out / encloses".
5. Stairs/columns/grids/furniture/dimension-tick marks/window-opening edges → recognize then log in
   `uncaptured_visual_elements`, **NOT traced as walls**. A dimension tick is not a wall; a window opening edge is
   not a wall.
6. One stroke per continuous wall (the south perimeter from (0,0) to (15,0) is ONE wall stroke, not 3). Door
   openings and plan windows do not break a wall.
7. Fill null when not found. OCR verbatim.
8. For elevations, emit the image-local facade fields (`view_facade` from the trusted image name; do NOT write
   east/west into the in-image axis). World axis/sign is derived later by 1_correction — not your job.

## Workflow
Do one pilot image first, then batch the rest (no human in the loop here — proceed after the pilot). Finally write
`<OUT_DIR>/reading_summary.md` (per-image confidence + repeatedly-null fields + schema feedback).

## Boundaries
Work ONLY inside your assigned `<OUT_DIR>` and read ONLY from `images/`, `skill/`, `testdata_prompt.json`. Do not
read any other directory, any ground-truth file, any other reading output, or anywhere in the repository. Do not
run any pipeline or EnergyPlus. Do not produce IntakeOutput fields.
