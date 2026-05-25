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
| [`phase1_vector_schema.md`](phase1_vector_schema.md) | Phase 1 vector JSON output format (strokes / pen types / elevation facade_axis_note spec / self-check). Hard constraint for the phase 1 prompt: describes what the model should produce. |
| [`phase2_rules.md`](phase2_rules.md) | Phase 2 reasoning rules (vector JSON → IntakeOutput: field derivation order / naming / vertex synthesis / InterZone single-construction, etc.). Hard constraint for the phase 2 prompt: describes how the model turns vector JSON into IntakeOutput. |
| [`phase1_prompt_template.md`](phase1_prompt_template.md) | Phase 1 startup prompt template (paste into a new session). Copy per case and adjust paths. |
| [`phase2_prompt_template.md`](phase2_prompt_template.md) | Phase 2 startup prompt template. Copy per case and adjust paths. |

## Flow

1. **Phase 1** (sees the image): for each drawing, produce one vector JSON per
   `phase1_vector_schema.md` (semantic-pen strokes + dimension chains + OCR text), plus a
   `phase1_summary.md` carrying the per-facade local↔world translation formulas.
2. **Phase 2** (no image): consume the vector JSONs + `testdata_prompt.json` and follow
   `phase2_rules.md` to produce the 11-field `IntakeOutput` Pydantic JSON for the downstream subagents.

When running a case, copy the latest files from this folder into the case directory as the runtime
copy / audit anchor, and adjust the prompt-template paths.

## Relationship to `../energyplus_mcp/`

| Aspect | `energyplus_mcp/` (single-step) | `energyplus_mcp_twostep/` (two-step) |
|---|---|---|
| Intake model | single step: image + text → IntakeOutput | two steps: image → vector JSON → IntakeOutput |
| Skill content | visual reading + output contract + vertex synthesis, mixed | split apart: phase1 schema handles visual tracing only / phase2_rules handles topology reasoning only |

The two-step skill consolidates the output contract that phase 2 needs, so phase 2 does not read the
single-step docs.
