# J0 — 0_reading VLM judge rubric (gate ②)

Runs **after** the deterministic linter (`reading_checks.json`) passes. The judge
sees **[original drawing + wireframe render + reading JSON]** and rules each
criterion below `pass | minor | severe | fatal | not_applicable |
insufficient_evidence` **with structured evidence — never a numeric score**.

This is a **per-image perception** check: "what did this drawing show, and was it
traced faithfully?" Do NOT reason about topology, cross-image consistency, or
world placement — those are 1_correction's (J1).

## Criteria (seven classes of obvious recognition error)
1. **missed real element** — a real wall or window in the drawing has no stroke.
2. **clutter traced as structure** — furniture / paving / text / grid axes /
   stairs traced as a wall/window stroke (should be `uncaptured`, not a stroke).
3. **pen misclassified** — a wall traced as window (or vice-versa); on elevations,
   `wall_fill` vs `outline` vs `window` confusion.
4. **number copied wrong** — a dimension's `text_verbatim` does not match the
   number printed in the drawing. **This is the transcription-truth check** (the
   deterministic linter only checks internal consistency; the real-number truth
   lives here / independent OCR).
5. **image-local orientation self-consistent** — `view_facade` / `mirrored`
   declarations are consistent with what the elevation shows. **Declaration-level
   only**; the world translation is judged in J1.
6. **door healing wrong** — a door opening was not healed into a continuous wall
   (or a real opening was wrongly healed shut).
7. **whole-region missing / misplaced** — an entire room / wing / floor band is
   absent or grossly displaced.

## Disposition
- **fatal / severe** → `human_redraw_required` (0_reading is `manual` today; once a
  VLM runner is wired, auto blind-reread, 3 attempts → terminate).
- **minor** → flag and pass.
- Set `root_stage="0_reading"` when the defect is a recognition error; leave
  `root_stage=null` + low `root_confidence` when you cannot attribute confidently
  (do **not** force a routing decision).

## Output
A `StageVerdict` (verdict schema v2): `criteria[]` + `root_stage` +
`root_confidence` + `retriable`. Commentary is **out-of-band only** — it is never
injected back into the reading prompt.
