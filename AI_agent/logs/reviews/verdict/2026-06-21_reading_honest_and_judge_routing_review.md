# Design Review - Reading-honest provenance + judge recoverability routing

Top-line verdict: APPROVE-WITH-CHANGES

The proposal is architecturally sound against D1-D5: it keeps 1_correction image-blind, puts the second image-grounded look in J0/J1, and addresses the missing reading-side provenance guardrails. Front 1 is additive and compatible with legacy readings. Front 2 is the right routing idea, but the executor plan needs two blast-radius fixes before implementation: scope the recoverability pass-through to J0, and update the baseline reporter that currently re-derives "severe/fatal => blocking".

## Findings

1. [major] `src/agent/judge/verdict.py:54` - The proposed `blocking` change is stage-generic, but recoverability pass-through is only safe for J0. If a future J1 verdict ever emits `recoverability="correction_recoverable"` on a severe criterion, `StageVerdict.blocking` would become false and `step_orchestrator` would advance a bad corrected geometry, contradicting the J1 confirm-gate role in `skills/intake_pipeline/1_correction/judge_rubric.md:32`.
   Recommendation: make the recoverability exception J0-only, e.g. severe/fatal blocks unless `(rubric_id == "J0" or stage == "0_reading") and recoverability == CORRECTION_RECOVERABLE`. Add tests for J0 severe recoverable pass-through and J1 severe recoverable still blocking.

2. [major] `scripts/tool_scripts/record_baseline.py:94` - `_verdict_blocking()` independently implements `any(status in ("severe", "fatal"))`, so future severe-but-recoverable J0 pass-through verdicts will be reported as blocking in `baseline.json` / `RUN_REPORT.md` even though orchestration advanced. This is the main grep-discovered counterexample to the proposal's "no other severe => block path" claim.
   Recommendation: parse with `StageVerdict.model_validate(...)` and use `.blocking`, or share a recoverability-aware helper. Add a regression test where `judge_verdicts[*].blocking` is false for J0 severe + correction_recoverable and unchanged for missing recoverability.

3. [minor] `src/agent/execution/step_orchestrator.py:328` - After the proposed change, "not blocking" can mean either clean/minor or severe pass-through to correction, but the current status/message says `JUDGE_PASS` and "pass/minor". That is control-flow correct but audit-misleading and can make reading debt look like a clean pass.
   Recommendation: no separate routing state is required, but update the message/summary to distinguish `judge verdict pass-through (severe recoverable)` from clean/minor pass, and surface the recoverable criteria count in logs/baseline.

4. [minor] `AI_agent/logs/review/request/2026-06-21_reading_honest_and_judge_routing_proposal.md:162` - The stroke/dimension cumulative-position flag will false-positive on legitimately dimensioned interior walls: true partitions often sit exactly on dimension-chain endpoints. Flag-only is the right disposition, but the rule must not become a proxy for "bad wall".
   Recommendation: keep it CROSS_CHECK only; use a tight 10 mm tolerance; include evidence with stroke id, axis coordinate, matching dimension ids, and whether the line bounds rooms/joins walls when inferable. Prefer flag text that asks J0 to verify, not language that presumes an annotation was traced as structure.

5. [minor] `AI_agent/logs/review/request/2026-06-21_reading_honest_and_judge_routing_proposal.md:144` - The reading-local provenance enum is good, but the current runtime passes raw reading JSON plus A0/A3 docs to the correction model (`src/agent/pipeline.py:289` and `:340`) rather than doing a typed code conversion into A0 evidence grades. Ambiguous prose here can break attribution by letting `seen` be read as numeric `direct_measurement`.
   Recommendation: keep the reading-local enum, but document the mapping per claim type: `seen` is visual existence evidence and numeric `estimated_stroke`; `dimension_derived` is numeric `transcribed_dimension` and requires non-empty `dimension_refs`; `estimated` is low-confidence `estimated_stroke`; `unknown`/missing is legacy/unknown. Add tests for schema defaults and prompt/docs text coverage.

## Open Questions

1. Provenance enum: use the reading-local vocabulary, not A0 grades directly. The VLM should not have to reason about A0's full evidence lattice. The bridge to A0 must be explicit in the reading guide and correction docs, especially that `seen` is not a numeric direct measurement.

2. `blocking` overload: the property change is sufficient for control flow only if the recoverability exception is J0-scoped. Do not add a new orchestrator route state for execution. Do add an audit-visible pass-through label/message so severe recoverable findings are not reported as clean passes.

3. J0 -> J1 obligation hand-off: independent J1 re-judging against originals + reference is sufficient for correctness. Do not add `correction_obligations[]` now. The J0 criterion evidence remains available in `judge.json` for audit; if later evaluation needs obligations, derive them from criteria rather than changing the verdict schema in this PR.

4. Coincidence tolerance: use `OUTPUT_PRECISION` / `DIMCHAIN_CLOSE_TOL` scale, i.e. 10 mm. Do not use `SNAP_GRID` 50 mm for coincidence; it is too broad and will inflate false positives on ordinary grid/dimensioned walls. Axis-relative tolerance is unnecessary for these meter-scale architectural coordinates.

5. Persist manual 0_reading prompt/model: defer. It is useful and small, but orthogonal to the provenance/routing fix and would widen an already cross-cutting PR. Do it as a follow-up auditability PR.

6. Faithfulness to D1-D5: yes, with the changes above. The proposal does not reintroduce image access into correction, preserves perception-vs-reasoning attribution through J0/J1, and reduces reading rot by making reading uncertainty visible. The main risks are audit drift (`record_baseline.py`) and accidental J1 false-green if recoverability is not J0-scoped.

## Blast-Radius Notes

Confirmed judge `StageVerdict.blocking` consumers in code:

- `src/agent/judge/executor.py:94` quarantines `verdict.blocking and not verdict.routable(...)`.
- `src/agent/execution/step_orchestrator.py:328` advances when `not verdict.blocking`, then uses `routable()` for blocking routing.
- `scripts/tool_scripts/run_stage.py:462` validates submitted verdicts through `StageVerdict`; it should inherit the property semantics.
- `scripts/tool_scripts/record_baseline.py:94` is the exception: it re-derives blocking from raw severe/fatal status and must be fixed.

Golden baseline claim: current sm20/sm21 verdict artifacts do not contain `recoverability`, so missing recoverability preserving "unrecoverable/current blocking" is backward-compatible. The schema additions are optional, and the new reading check is CROSS_CHECK, so gate1 pass/fail should not change. With the `record_baseline.py` fix, no golden re-record should be required solely for this design.

## Review-Ask

- I did not perform a fresh image-grounded inspection in this review; I relied on the supplied diagnosis and its image-grounded Claude pass. Before execution, confirm the sm21 visual facts still stand: x=3.44/6.30 are dimension ticks, and the South/West F1 openings are doors, not windows.
- Confirm the executor updates all severity/blocking consumers, including `record_baseline.py`, not only `verdict.py` and `step_orchestrator.py`.
- Confirm J1 either cannot emit `recoverability=correction_recoverable` or the `blocking` property ignores recoverability outside J0.
- After implementation, run the focused verdict/orchestrator/baseline tests plus the reading-check tests to confirm severe+missing recoverability keeps current behavior and CROSS_CHECK flags do not block.
