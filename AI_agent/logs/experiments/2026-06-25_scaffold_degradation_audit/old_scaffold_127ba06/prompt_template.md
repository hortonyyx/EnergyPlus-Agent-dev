# Phase 1 startup prompt (paste directly into a new Claude Code session)

> Usage: in the `EnergyPlus-Agent-dev` project root, start a new Claude Code session (a capable
> multimodal model, e.g. Opus), and paste the block between the "---" markers below as the first
> message. Copy this template per new case and adjust the paths.

---

I am doing **phase 1 of the two-step intake: redraw the source image with semantic pens** — trace
every visible structural stroke on the architectural drawing by type (wall pen / window pen / wall_fill pen / ...),
and do **no spatial-topology reasoning** at all.

## Mental model

Phase 1 = "re-trace the source image with a set of semantically labeled pens". For example "the wall
pen drew a wall stroke from (0,0)→(15,0)", "the window pen drew a filled rectangle at elevation
(1.4, 1.0)→(3.8, 2.8)".

Phase 1 does **not**: enclose multiple wall strokes into "a room" / judge whether a wall is
"exterior or interior" / say "this window belongs to that wall" / write "the z_min/z_max of the
middle window on the south elevation F2". **All topology reasoning is left to phase 2.**

## Error budget (key, see guide.md §0.1)

Phase 1 sees the image, phase 2 does not. So:

- **perception errors can only be caught in phase 1**. Once phase 1 misreads a dimension, offsets a
  coordinate, flips the elevation x-axis, or misses a stroke, phase 2 cannot backtrack — it takes
  what it gets as truth
- **prefer null over guessing**. null = "I couldn't see it / it isn't dimensioned", which phase 2
  knows is missing. A guessed value is contamination
- EP zones are enclosed by surfaces (2D faces), **walls have no thickness** — plan walls'
  `thickness_m` is always `null`, do not estimate visual stroke width

## Your task

1. Read all three phase-1 skill docs (**required**):
   - `guide.md` — flow / error budget / global constraints / output container / door-healing /
     facade_axis_note spec / self-check / downstream contract
   - `reading_guide.md` — how to *recognize* each element across drawing styles (the
     convention cards + the semantic-category vocabulary)
   - `pen_library.md` — what to *do* with each recognized category (which pen / keep-or-ignore /
     wall_fill convention)
2. Look at the worked example JSON (already hand-authored, e.g. the first plan view — **do not
   rewrite it**), and follow its style for the remaining images
3. Produce one JSON per remaining image, e.g.:

| source PNG | output JSON | image_kind |
|---|---|---|
| `2f_view.png` | `phase1_vector/2f_view.json` | plan |
| `3f_view.png` | `phase1_vector/3f_view.json` | plan |
| `South_view.png` | `phase1_vector/South_view.json` | elevation |
| `North_view.png` | `phase1_vector/North_view.json` | elevation |
| `East_view.png` | `phase1_vector/East_view.json` | elevation |
| `West_view.png` | `phase1_vector/West_view.json` | elevation |
| `supp_plan.png` | `phase1_vector/supp_plan.json` | decide yourself |

Read metadata from `testdata_prompt.json` — but only to learn the floor count / floor height / total
dimensions; **do not copy testdata_prompt content directly into the phase 1 JSON** (phase 1 should
reflect only what is seen in the image).

## Core discipline

1. **plan and elevation use different, minimal pen sets** (pen_library.md):
   - plan legal pens = `wall` / `window`
   - elevation legal pens = `wall_fill` / `window` / `outline`
   - there is **no `other` pen and no `door` pen**; stairs / columns / grids / furniture / decoration
     are recognized then logged in `uncaptured_visual_elements`, **not traced** (do not trace stair treads)
   - cross-use is an error. E.g. an elevation wall body must use `wall_fill`, not `wall`
2'. **Heal door openings into continuous walls (door-healing, guide.md §2.1)**: when you see a door
   leaf / arc on a plan, do not draw a door pen — heal the walls on its two sides into **one
   continuous wall stroke** + a note `healed door opening at <position>` (a door is ignored in EP, a
   wall is a continuous boundary face). Guardrails: only heal openings carrying a door symbol;
   doorless large open spans are kept, not welded (those are real topology signals); windows are not
   healed. Record each heal in `uncaptured_visual_elements`
2. **Split elevation wall bodies as "one wall_fill stroke per floor"** (pen_library.md §3). For a 3-story
   building, each elevation produces 3 wall_fills. Even if the gray looks visually continuous, split
   by the dimension chain's per-floor z ranges
3. **Topology is not phase 1's job.** Forbidden fields: `is_exterior` / `parent_wall_id` / `rooms[]`
   / any "X belongs to Y / X faces outside / X encloses" semantics
4. **Do not expand the pen set, and do not trace non-keep marks.** Columns / beams / decorative lines /
   index arrows / grid lines / stair treads are **recognized then logged in `uncaptured_visual_elements`**,
   not traced as strokes; do not invent enum values like `cornice` / `column` / `level_line` and do
   not fall back to an `other` pen (there is none)
4'. **`uncaptured_visual_elements` is required**: anything "seen but not drawn into strokes" must be
   acknowledged — out-of-dictionary strokes + clutter actively excluded by selective extraction
   (furniture / paving / texture / room text boxes) + healed doors. Even when the dictionary is truly
   enough, write a note rather than leaving it empty ("acknowledged skip" ≠ "silent loss")
5. **One stroke per continuous stroke.** E.g. the south perimeter wall from (0,0) to (15,0) is **one**
   wall stroke, do not split into 3. Door openings do not break a wall (heal into a continuous wall,
   see 2'); a window on a plan is a sub-face and also does not break a wall
6. **Fill null when not found**, no defaults. Plan walls' `thickness_m` is always null (simulation
   doesn't use it, guide.md §0.2); other fields not found in the image are also null
7. **Elevation facade_axis_note must include the sign** (guide.md §4 four-facade table)
8. **OCR verbatim**; if there are no text labels, leave ocr_texts as an empty array

## Workflow

1. Read guide.md + reading_guide.md + pen_library.md + the worked-example plan JSON (understand the style)
2. Do one pilot first (e.g. `2f_view.png`), then stop and let me review — **do not batch all images at once**
3. After I approve the pilot, batch the rest (other plans + elevations + supplemental plan)
4. When all are done, write a `phase1_vector/phase1_summary.md`:
   - per-image confidence self-assessment (high/medium/low, with reasons)
   - which fields were repeatedly null / unknown
   - the four-facade x_local ↔ world-axis table (actual filled values)
   - your feedback on the schema: where it falls short / where it is redundant / which pen enum values are insufficient

## Boundaries

- Do not modify any file under [src/](src/), [skills/](skills/), [AI_agent/](AI_agent/)
- Do not modify the worked-example JSON (it is the reference)
- Do not run `run_full_pipeline.py` or any EnergyPlus tool
- Do not produce IntakeOutput fields (zone_specs / surface_specs / fenestration_specs / ...), that is all phase 2's job

When ready, do the pilot first, then stop and wait for my feedback.
