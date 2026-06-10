# skills/intake_pipeline — staged intake pipeline skill/spec library

Skill + spec source for the **staged intake pipeline** that turns architectural
drawings + testdata into the 11-field `IntakeOutput` handoff contract. The pipeline
is organized into ordered stages **0–5**; geometry is fully deterministic (code),
and the LLM does only perception, correction judgment, and physics semantics.

> Renamed from `energyplus_mcp_twostep/` (2026-06-10). The single-step library
> `energyplus_mcp/` is retired (archived to `Skill_history/`).

## Stages (0–5)

| Stage dir | Actor | Role | Docs here |
|---|---|---|---|
| [`0_reading/`](0_reading) | LLM/VLM (image-bound) | perceive each drawing → semantic vector JSON | `guide.md` (master flow) + `reading_guide.md` (recognize what an element is) + `pen_library.md` (what action to take) |
| [`1_correction/`](1_correction) | LLM (image-blind) | vectors → clean, self-consistent `CorrectedGeometry` (then a deterministic core snaps it) | `A0_contract.md` … `A4_priors.md` + `README.md` |
| [`2_modelling/`](2_modelling) | **code** | cells → zone volumes + oriented faces | `spec.md` (code-of-spec) |
| [`3_split_pairing/`](3_split_pairing) | **code** | which faces exist + 1:1 reciprocal correspondence (切配); serialize to `surface_specs` | `spec.md` (code-of-spec) |
| [`4_mep/`](4_mep) | LLM (image-blind) | the 8 non-geometry fields (building/site + material/construction/schedule/people/lights/hvac) | `authoring.md` (rules) + `mep.md` (default values) |
| [`5_intakeoutput/`](5_intakeoutput) | **code** | assemble geometry + MEP specs → `IntakeOutput` + contract check | `spec.md` (code-of-spec) |

The `code` stages have a `spec.md` documenting the deterministic behavior their code
realizes (not a prompt). The LLM stages have rule docs loaded into their prompt at
runtime by [`src/agent/pipeline.py`](../../src/agent/pipeline.py).

> The old single whole-output `phase2/rules.md` prompt is retired (the geometry it
> drove is now deterministic code; the physics moved to `4_mep/`). Archived to
> `Skill_history/2026-06-10_phase2_terminology_cleanup/`.

## Error-budget split

Each stage owns a separable error budget: 0_reading may only introduce perception
errors; 1_correction only correction-judgment errors; the code stages (2/3/5) are
deterministic; 4_mep only physics-semantics errors. The `CorrectedGeometry` and
`IntakeOutput` checkpoints are materialized so each stage is independently testable.

## Startup prompts

The operational startup prompts (the phase-1 / phase-2 blocks to paste into a new
session) live in [`../../AI_agent/guides/new_case_guide.md`](../../AI_agent/guides/new_case_guide.md)
Appendix A / B, kept in one place so they don't drift from the run procedure.

## Authoritative wiring

See [`../../AI_agent/architecture/pipeline_stage_contracts.md`](../../AI_agent/architecture/pipeline_stage_contracts.md)
for the full stage-by-stage contract (inputs / outputs / which skill feeds which
stage / invariants).
