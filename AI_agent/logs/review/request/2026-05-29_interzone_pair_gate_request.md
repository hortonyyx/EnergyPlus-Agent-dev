# Review Request — Deterministic InterZone surface-pair validation gate

Date: 2026-05-29
Requested by: Claude (main dev agent)
Suggested reviewer: Codex / Gemini (fresh model, cross-check)

## Nature of this review

**Code review.** This implements finding #1 of the 2026-05-28 InterZone surface pairing review
(`AI_agent/logs/review/review/2026-05-28_interzone_surface_pairing_review.md`). Please check the
validator's correctness, its placement in the workflow, the calibration, and whether the hard-gate
behavior is safe (no false kills on legitimate geometry).

## What changed

- **New** `src/validator/interzone.py` (pure numpy, no new deps):
  - `validate_interzone_surface_pairs(idf)` — runs on the assembled eppy `IDF`. Checks, per
    `Outside Boundary Condition = Surface` surface: target exists; target is itself `Surface`; target
    points back (reciprocity); no target claimed by >1 source; paired areas match (abs 0.02 m² or rel
    1%); unit normals antiparallel (Newell, dot ≤ -0.99); floor/ceiling pairs coplanar in z (≤ 0.02 m).
    Plus a global degenerate guard: any surface whose shortest edge < 0.10 m is rejected.
  - `audit_interzone_surface_pairs(idf)` — non-failing summary counts (total / by-OBC / reciprocal
    pairs / issue count) for baseline notes (finding #4).
- **Modified** `src/mcp/tools/workflow.py` — `run_simulation` + `export_idf_only` call
  `_check_interzone_pairs()` after `manager.convert_all()`, before EP / final-IDF save. Issues →
  `ToolResponse(success=False, data={interzone_pair_issues: [...]})`, EP not started. Reads the live
  `manager._idf` (the `manager.idf` property deep-copies an IDF backed by a possibly-closed StringIO).

## Why this placement

The gate runs on the *assembled IDF* (what EP actually sees), not on the natural-language `*_specs`,
so it enforces the InterZone contract regardless of which prompt wording the surface agent followed —
directly closing the "correctness depends on prompt compliance" gap. It is fail-fast: a missing /
non-reciprocal / degenerate pair stops before the expensive EP run (or before a late EP fatal / silent
wrong-physics pass).

## Calibration (already run)

| IDF | EP history | gate result |
|---|---|---|
| sm21 OPUS | completed (12 warn) | **0 issues — pass** |
| sm21 DEEPSEEK | completed (geometry worst, "phantom room") | **0 issues — pass** |
| sm21 SONNET | **segfault (exit 139)** | **4 issues — blocked** (the 0.05 m slivers `F1_SM_Office_Ceiling_S2/S5`, `F2_S1/S4_Office_Floor_S2/S5` = the documented segfault root cause) |
| sm_16_newarch glazingfix (135 surfaces) | completed | **0 issues — pass** |

`pytest` 5/5 green.

## Scope to review (challenge these)

1. **Correctness of each check** — especially the Newell normal + the antiparallel test (does it
   correctly treat InterZone walls *and* floor/ceiling pairs?), the area tolerance, and the floor/ceiling
   coplanar-z test (is `{Floor, Ceiling, Roof}` membership the right trigger?).
2. **The `_MIN_EDGE = 0.10 m` degenerate guard** — is 0.10 m the right threshold? Could any legitimate
   SmallOffice-class geometry produce a sub-0.10 m surface edge and be wrongly rejected? Is "shortest
   polygon edge" the right degeneracy metric vs. min-area or aspect ratio?
3. **Hard-gate vs warn** — we made issues a hard `success=False`. Is failing the run correct here, or
   should some sub-checks (e.g. area mismatch within a looser band) be warnings? Any risk of blocking a
   case EP would actually accept?
4. **Placement & the `manager._idf` access** — reading the private `_idf` to avoid the deepcopy bug.
   Acceptable, or should `ConverterManager` expose a read-only accessor instead?
5. **DEFERRED finding #2 (coverage completeness)** — we deferred the stacked-floor footprint-coverage
   check because it needs polygon intersection (`shapely` absent in-container). Agree with deferring, or
   is there a numpy-only coverage check worth doing now for the axis-aligned rectangular cases?

## Files to review

- `src/validator/interzone.py` (primary)
- `src/mcp/tools/workflow.py` (the two call sites + `_check_interzone_pairs`)
- Context: `AI_agent/logs/review/review/2026-05-28_interzone_surface_pairing_review.md` (the review this
  answers) and `AI_agent/logs/downstream_agent_changes.md` (2026-05-29 entry).
- Evidence IDFs under `test_data/SmallOffice_TwoStep/smalloffice_21/output_{opus,sonnet,deepseek}/temp_*.idf`
  and `test_data/SmallOffice/smalloffice_16_newarch/output/temp_*glazingfix.idf`.

## Acceptance criteria

- [ ] Verdict on validator correctness (each check sound, no logic bugs)
- [ ] Verdict on the 0.10 m threshold + degeneracy metric
- [ ] Verdict on hard-gate behavior (safe? any false-kill risk?)
- [ ] Opinion on the `manager._idf` access pattern
- [ ] Opinion on deferring coverage completeness (finding #2)
- [ ] Graded findings (High/Medium/Low) with evidence + recommended action

Please write the review to
`AI_agent/logs/review/review/2026-05-29_interzone_pair_gate_review.md`.
