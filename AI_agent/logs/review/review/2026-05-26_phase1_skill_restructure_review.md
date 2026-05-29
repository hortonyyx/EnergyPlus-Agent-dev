# Phase 1 Skill Restructure Review

Date: 2026-05-26
Reviewer: Codex
Scope: Review the phase-1 three-way split under `skills/energyplus_mcp_twostep/phase1/`, the moved phase-2 docs, and the two pre-run script fixes requested in `AI_agent/review/request/2026-05-26_phase1_skill_restructure_request.md`.

## Verdict

Partially accepted, with fixes required before using this as the POC v2 baseline.

The old bundled phase-1 hard constraints are mostly preserved across `guide.md` + `reading_guide.md` + `pen_library.md`: error budget, null-over-guessing, local coordinate container, door healing, no topology inference, legal pen sets, one wall_fill per floor, OCR verbatim, non-empty `uncaptured_visual_elements`, and downstream contract all survived.

The main risk is not the split itself. The split is sound. The remaining issues are integration edges: supplementary drawings can be silently dropped in phase 2, the manual phase-2 prompt still describes a fixed sm_20-style file set, the category enum is not mechanically one-row-per-category in the pen map, and a few stale references survived the move.

## Findings

### 1. High — Phase 2 automated path silently drops supplementary / section JSONs

Evidence:
- `skills/energyplus_mcp_twostep/phase2/rules.md` says phase 2 must read every vector JSON and explicitly consume supplementary / section JSONs if present.
- `skills/energyplus_mcp_twostep/phase1/prompt_template.md` still asks phase 1 to produce `phase1_vector/supp_plan.json` when a supplementary plan exists.
- `Tool_scripts/run_phase2_deepseek.py` now discovers only `phase1_vector/*_view.json`, so `supp_plan.json`, section JSONs, or other non-`*_view.json` vector outputs are omitted from the DeepSeek phase-2 message without an error.

Risk:
This is a real capability regression for cases where a supplement carries stair indexing, local geometry clarification, sections, or nonstandard drawing context. The rules say to use that evidence, but the automated path never sends it to the model.

Recommended fix:
Change `_discover_phase1_files()` to include all phase-1 vector JSONs that represent source images, not just `*_view.json`. Keep deterministic ordering:

1. numeric floor plans like `<N>f_view.json`
2. facade elevations like `South_view.json`, `North_view.json`, etc.
3. supplementary / section / other JSONs

Exclude only non-image artifacts if any are later added under `phase1_vector/`.

### 2. Medium — Manual phase-2 prompt still contradicts the new "read every JSON" rule

Evidence:
- `skills/energyplus_mcp_twostep/phase2/prompt_template.md` tells the model to read vector JSONs "as needed, not all" and lists the fixed 3-plan + 4-elevation sm_20 set.
- `skills/energyplus_mcp_twostep/phase2/rules.md` now says to read every vector JSON and not assume a fixed file set.

Risk:
The session path can skip a floor, facade, or supplement in exactly the cases this restructure is preparing for. This also preserves sm_20-shaped assumptions in the launcher even though the rules were generalized.

Recommended fix:
Update the prompt template to say:
- enumerate all JSONs under `phase1_vector/`
- read all plan/elevation JSONs
- read supplementary/section JSONs when present
- do not assume 3 floors or 4 facades

### 3. Medium — Separation of concerns leaks actions back into `reading_guide.md`

Evidence:
- `reading_guide.md` §0.3 includes "role for phase 1" entries such as "triggers wall-healing", "`dimensions[]`", and "clutter".
- `reading_guide.md` says axonometric / perspective / 3D render should be skipped.
- `reading_guide.md` clutter section says the pen library says to ignore these marks.

Risk:
This weakens the clean mental model requested in the review: reading guide = identity only, pen library = action only. The leakage is not fatal, but it creates two sources of truth for action semantics and makes future RAG-able recognition cards less clean.

Recommended fix:
In `reading_guide.md`, rename the enum table's second column to identity-only language, for example "recognition scope / typical identity". Remove action arrows like `→ dimensions[]`, "trigger healing", "skip", and "ignore". Keep action words only in `pen_library.md` and `guide.md`.

### 4. Medium — Category enum parity is semantically complete but not mechanically identical

Evidence:
- `reading_guide.md` §0.3 defines one category per row.
- `pen_library.md` §1 combines seven categories into one table row: `furniture` `sanitary` `equipment` `landscape-paving` `vehicle-figure` `shadow` `decoration`.

Risk:
Humans can read the mapping, but the request explicitly asks that `reading_guide` §0.3 match the left column of `pen_library` §1. The current combined row will fail a simple parity script and makes orphan detection brittle as the category library grows.

Recommended fix:
Expand the combined clutter row into seven one-category rows, all with the same ignore-and-log action. This preserves the deliberately thin pen library while making the enum contract exact.

### 5. Low — Plan-file discovery sorts floors lexicographically, not numerically

Evidence:
- `_discover_phase1_files()` sorts names lexicographically before splitting plans from elevations.
- `_PLAN_RE` matches numeric floor names, but the code does not use the numeric capture for ordering.

Risk:
For cases with 10 or more floors, `10f_view.json` sorts before `2f_view.json`. That may not break correctness if the model reads labels carefully, but it violates the intended "plans before elevations in floor order" discipline.

Recommended fix:
Make `_PLAN_RE` capture the floor number and sort plans by `int(match.group(1))`, then name as a tiebreaker.

### 6. Low — Some project docs still point to deleted flat phase-1 paths or obsolete script status

Evidence:
- `AI_agent/plan.md` still links to `../skills/energyplus_mcp_twostep/phase1_vector_schema.md`, which is deleted by this restructure.
- `AI_agent/plan.md` still says `run_phase2_deepseek.py` has a hardcoded `PHASE1_FILES` list and must be changed before new cases, even though this diff replaced it with discovery.
- `AI_agent/CLAUDE.md` still describes the skill source as `phase1_vector_schema.md v1.2 + phase2_rules.md v1.3` in the historical artifact section, which is not a broken link but is stale wording after the move.

Risk:
This does not affect runtime, but it undermines the "new docs are the source of truth" transition and can send the next agent to removed files.

Recommended fix:
Update the remaining project-doc references to the new paths:
- `skills/energyplus_mcp_twostep/phase1/guide.md`
- `skills/energyplus_mcp_twostep/phase1/reading_guide.md`
- `skills/energyplus_mcp_twostep/phase1/pen_library.md`
- `skills/energyplus_mcp_twostep/phase2/rules.md`

Also remove the obsolete `PHASE1_FILES` warning from `AI_agent/plan.md`.

## Checks Passed

- No major hard-constraint regression found in the phase-1 split itself.
- Door handling is coherent across the three docs:
  - `reading_guide.md` recognizes `door`
  - `pen_library.md` routes `door` to "not drawn → trigger wall-healing"
  - `guide.md` preserves the four guardrails and trace requirement
- The legal pen sets survived:
  - plan: `wall`, `window`, `stair`, `other`
  - elevation: `wall_fill`, `window`, `outline`, `other`
- `phase1/guide.md` preserves the old output container and self-check fields.
- `phase1/reading_guide.md` is broadly useful and mostly follows the "invariant cue first, variants non-exhaustive" framing.
- `scripts/run_full_pipeline.py --base-dir` is narrowly scoped and preserves the default `test_data/SmallOffice` behavior.
- The edited scripts passed a lightweight syntax check:
  - `python -m py_compile Tool_scripts/run_phase2_deepseek.py scripts/run_full_pipeline.py`

## Acceptance Criteria Status

- Zero capability regression: blocked by supplementary JSON omission in the automated phase-2 path.
- No concern leakage: needs cleanup in `reading_guide.md`.
- Category enum parity: semantically present, mechanically not exact due combined clutter row.
- Reading guide quality: acceptable, with the action-language cleanup above.
- Door handling: pass.
- Clean-spec compliance: mostly pass for skill files; avoid "pending v2" style notes in current spec over time, though example-image placeholders were declared out of scope in this request.
- Links: not fully pass; stale `phase1_vector_schema.md` path remains in project docs.
- Script fixes: `--base-dir` pass; phase1 discovery needs supplementary inclusion and numeric floor sorting.
