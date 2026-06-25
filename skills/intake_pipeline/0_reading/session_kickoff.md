# Reading-stage session kickoff (0_reading)

You are running the **reading stage** of the staged intake pipeline: redraw each architectural drawing
with semantic pens. Trace every visible structural stroke by type (wall / window / wall_fill / outline
pen) and the dimension chains. Do **no spatial-topology reasoning** and **no world placement** — that
is downstream's job.

This file is the single kickoff command. The durable rules are NOT duplicated here — they live in the
three rule docs below; the recap section is only a pointer so nothing here can silently drift from them.

## First: read the rule docs (required)

Read all three before tracing anything, then follow the worked-example plan JSON's style (do not rewrite it):

- `skills/intake_pipeline/0_reading/guide.md` — error budget, global constraints, JSON schema,
  door-healing, self-check, downstream contract
- `skills/intake_pipeline/0_reading/reading_guide.md` — how to *recognize* each element across drawing styles
- `skills/intake_pipeline/0_reading/pen_library.md` — what to *do* with each recognized category
  (which pen / keep-or-ignore / wall_fill convention)

## Non-negotiables — a checklist of WHAT to read, not a second copy of the rules

Do not memorize anything below; the durable text lives in the rule docs and must not be duplicated here
(a duplicated summary is exactly what drifted and degraded before). Each line just tells you which rule
to go read:

- **Error budget — read coordinates as final** → `guide.md` §0.1 (precise reading vs the *earned*
  redundant-dimension-channel escape hatch; prefer `null` over guessing; anchor against the testdata totals).
- **One stroke per continuous wall; no over-segmentation** → `guide.md` §5 (window jambs / dimension
  ticks / furniture are NOT partitions — the #1 failure mode on cluttered plans).
- **No topology, no world placement** → `guide.md` §1/§3/§4 (forbidden fields; for elevations fill the
  facade-orientation fields exactly as the schema + `guide.md` define them — do not invent your own
  world-axis convention here).
- **Pens & healing** → `pen_library.md` (legal pen set per image kind; heal door openings into one
  continuous wall; one `wall_fill` per floor; recognize-then-log clutter in `uncaptured`).
- **Verbatim & null** → `guide.md` §1 (OCR verbatim; plan walls `thickness_m` = null; `null` when not found).

## Images for this case

Produce one JSON per image at `<case>/0_reading/<name>_view.json` (plans `image_kind=plan`, elevations
`image_kind=elevation`). Fill this table for the current case:

| source PNG | output JSON | image_kind |
|---|---|---|
| `<fill>` | `0_reading/<fill>_view.json` | plan / elevation |

## Workflow

1. Read the three rule docs + the worked-example JSON (understand the style).
2. Do **one** pilot image first, then stop and wait for review — do not batch all images at once.
3. After the pilot is approved, batch the rest (other plans + elevations + supplemental plan).
4. When all are done, write `0_reading/reading_summary.md`: per-image confidence self-assessment
   (high / medium / low, with reasons), which fields were repeatedly null / unknown, and your schema feedback.

## Boundaries

- Do not modify anything under `src/`, `skills/`, `AI_agent/`.
- Do not modify the worked-example JSON (it is the reference).
- Do not run `run_full_pipeline.py` or any EnergyPlus tool.
- Do not produce IntakeOutput fields (zone_specs / surface_specs / fenestration_specs / …) — that is
  the downstream stages' job.

Do the pilot first, then stop and wait for feedback.
