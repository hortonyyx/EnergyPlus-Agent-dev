# skills/energyplus_mcp_twostep — two-step intake skill library

This folder is the skill source for the **two-step intake** (phase 1 vectorized redraw → phase 2
topology modeling). It sits alongside [`../energyplus_mcp/`](../energyplus_mcp/), the skill source for
the single-step intake.

The two stages split the work along the error budget: phase 1 only perceives the drawing (and may
only introduce perception errors), phase 2 only reasons over the vectorized JSON without the image
(and may only introduce reasoning errors).

## Files

| File | Role |
|---|---|
| [`phase1/guide.md`](phase1/guide.md) | Phase 1 master guide: error budget + global constraints + output container (strokes / dimensions / OCR / self-check) + door-healing + elevation facade_axis_note spec + recognition-vs-topology red line + downstream contract. The flow and discipline both other phase-1 docs feed into. |
| [`phase1/reading_guide.md`](phase1/reading_guide.md) | Phase 1 recognition reference: *how to recognize what an element is* across drawing styles (convention cards: walls / doors / windows / dimensions / clutter / …) + the semantic-category vocabulary. Outputs a category label; decides no action. |
| [`phase1/pen_library.md`](phase1/pen_library.md) | Phase 1 action map: *what to do* with a recognized category — which pen (plan vs elevation) / keep-or-ignore / heal — plus the per-floor wall_fill convention and pen counter-examples. |
| [`phase2/rules.md`](phase2/rules.md) | Phase 2 reasoning rules (vector JSON → IntakeOutput: field derivation order / naming / vertex synthesis / InterZone single-construction, etc.). Hard constraint for the phase 2 prompt: describes how the model turns vector JSON into IntakeOutput. |

This folder holds only the knowledge specs above. The **operational startup prompts** (the phase 1 /
phase 2 blocks to paste into a new session) live in
[`../../AI_agent/new_case_guide_twostep.md`](../../AI_agent/guides/new_case_guide_twostep.md) Step 4a / 4b —
kept in one place so they don't drift from the run procedure.

## Flow

1. **Phase 1** (sees the image): for each drawing, recognize elements via `phase1/reading_guide.md`,
   map each to an action via `phase1/pen_library.md`, and produce one vector JSON in the container
   defined by `phase1/guide.md` (semantic-pen strokes + dimension chains + OCR text), plus a
   `phase1_summary.md` carrying the per-facade local↔world translation formulas.
2. **Phase 2** (no image): consume the vector JSONs + `testdata_prompt.json` and follow
   `phase2/rules.md` to produce the 11-field `IntakeOutput` Pydantic JSON for the downstream subagents.

When running a case, the rule docs are read from this folder directly (the manual sessions load them;
the automated phase 2 script `Tool_scripts/run_phase2_deepseek.py` reads `phase2/rules.md` +
`phase1/guide.md` + `phase1/pen_library.md` from here). No per-case copy of the skill files is needed.

## Relationship to `../energyplus_mcp/`

| Aspect | `energyplus_mcp/` (single-step) | `energyplus_mcp_twostep/` (two-step) |
|---|---|---|
| Intake model | single step: image + text → IntakeOutput | two steps: image → vector JSON → IntakeOutput |
| Skill content | visual reading + output contract + vertex synthesis, mixed | split apart: phase1 guide + reading guide + pen library handle visual tracing only / phase2_rules handles topology reasoning only |

The two-step skill consolidates the output contract that phase 2 needs, so phase 2 does not read the
single-step docs.
