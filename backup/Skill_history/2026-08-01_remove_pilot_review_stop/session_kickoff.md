# Reading-stage session kickoff (0_reading)

You are running the **reading stage** of the staged intake pipeline: redraw each architectural drawing
with semantic pens. Trace every visible structural stroke by type (wall / window / wall_fill / outline
pen) and the dimension chains. Do **no spatial-topology placement** — assigning rooms, surfaces, zone
adjacency or facade world axes is downstream's job. The single exception is the plan-frame datum:
every plan view **must** declare `scale_origin` (`guide.md` §1/§2), which states where that plan's own
local (0,0) sits in the world frame and nothing else.

This file is the single kickoff command. The durable rules are NOT duplicated here — they live in the
three rule docs below; the recap section is only a pointer so nothing here can silently drift from them.

## First: read the rule docs (required)

Read all three before tracing anything, then follow the worked-example plan JSON's style.
Canonical worked-example file: `case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json`.
Read it as a style/format anchor only; **do not rewrite it**.

- `skills/intake_pipeline/0_reading/guide.md` — error budget, global constraints, JSON schema,
  door-healing, self-check, downstream contract; this is the master rule container
- `skills/intake_pipeline/0_reading/reading_guide.md` — how to *recognize* each element across drawing styles;
  it outputs only semantic-category labels
- `skills/intake_pipeline/0_reading/pen_library.md` — what to *do* with each recognized category:
  which pen to use, what to keep/log, and when door-healing applies
- CV evidence tools: `skills/intake_pipeline/0_reading/cv_toolbox.md` — deterministic pixel probes; see that file for when the toolbox is required or deferred

## Non-negotiables — a checklist of WHAT to read, not a second copy of the rules

Do not memorize anything below; the durable text lives in the rule docs and must not be duplicated here
(a duplicated summary is exactly what drifted and degraded before). Each line just tells you which rule
to go read:

- **Error budget — read coordinates as final** → `guide.md` §0.1 (precise reading vs the *earned*
  redundant-dimension-channel escape hatch; prefer `null` over guessing; anchor against the testdata totals).
- **One stroke per continuous wall; no over-segmentation** → `guide.md` §5 (window jambs / dimension
  ticks / furniture are NOT partitions — the #1 failure mode on cluttered plans).
- **No topology placement; plans declare `scale_origin`** → `guide.md` §1/§2/§3/§4 (forbidden fields;
  every plan states its `scale_origin.world_x_m` + `world_y_m` — the one world datum you do give; for
  elevations fill the facade-orientation fields exactly as the schema + `guide.md` define them — do not
  invent your own world-axis convention here).
- **Pens & healing** → `pen_library.md` (legal pen set per image kind; heal door openings into one
  continuous wall; one `wall_fill` per floor; recognize-then-log clutter in `uncaptured`).
- **Verbatim & null** → `guide.md` §1 (OCR verbatim; plan walls `thickness_m` = null; `null` when not found).

## Images for this case

Produce one JSON per source drawing at `<case>/0_reading/<name>_view.json`. Fill this manifest for
the current case before tracing; every source image must have exactly one output row or an explicit
skip reason in `reading_summary.md`.

| source PNG | output JSON | image_kind | status / note |
|---|---|---|---|
| `1f_view.png` | `0_reading/1f_view.json` | plan | worked example if already supplied; otherwise pilot candidate |
| `2f_view.png` | `0_reading/2f_view.json` | plan | fill/delete row for this case |
| `3f_view.png` | `0_reading/3f_view.json` | plan | fill/delete row for this case |
| `South_view.png` | `0_reading/South_view.json` | elevation | fill/delete row for this case |
| `North_view.png` | `0_reading/North_view.json` | elevation | fill/delete row for this case |
| `East_view.png` | `0_reading/East_view.json` | elevation | fill/delete row for this case |
| `West_view.png` | `0_reading/West_view.json` | elevation | fill/delete row for this case |
| `supp_plan.png` | `0_reading/supp_plan_view.json` | supplementary / plan | choose by content; explain in note |
| `<section/detail/other>.png` | `0_reading/<name>_view.json` | section / supplementary / other | include only if present; explain axes/scope in notes |

## Workflow

1. Read the three rule docs + the worked-example JSON (understand the style).
2. Do **one** pilot image first.
3. Stop and wait for review of that pilot; do not batch remaining images yet.
4. After the pilot is approved, batch the rest (other plans + elevations + supplemental/section images).
5. When all are done, write `0_reading/reading_summary.md`: per-image confidence self-assessment
   (high / medium / low, with reasons), which fields were repeatedly null / unknown, and your schema feedback.

## Boundaries

- Do not modify anything under `src/`, `skills/`, `AI_agent/`.
- Do not modify the worked-example JSON (it is the reference).
- Do not run `run_full_pipeline.py` or any EnergyPlus tool.
- Do not produce IntakeOutput fields (zone_specs / surface_specs / fenestration_specs / …) — that is
  the downstream stages' job.

Do the pilot first, then stop and wait for feedback.
