# Review Fixes Re-verify Review

Date: 2026-05-29
Reviewer: Codex
Request: `AI_agent/logs/review/request/2026-05-29_review_fixes_reverify_request.md`

## Overall verdict

Both prior reviews are closeable. All implementation fixes for G1-G4 and T1-T5 are PASS.

One non-blocking test-adequacy note remains: `tests/test_interzone.py::test_audit_counts_only_mutual_pairs` does not actually fail under the old `obc_surface // 2` audit-count implementation because the fixture has 3 Surface-OBC objects and one mutual pair, so both old and new logic return 1. The implementation is correct by inspection, but the regression test should use a graph where the old count diverges.

No new blocking regressions found.

## Per-item verdicts

### G1 - PASS

The vertical-wall offset bug is fixed. `src/validator/interzone.py:79-95` adds `_max_point_to_plane`, and `src/validator/interzone.py:179-188` applies it to every validated reciprocal pair, independent of surface type. This catches the original class where walls are reciprocal, equal-area, and opposite-normal but live on parallel offset planes.

Evidence:
- `tests/test_interzone.py:136-140` covers the vertical wall offset.
- `tests/test_interzone.py:143-147` keeps the horizontal z mismatch covered under the generalized coplanarity path.
- Additional spot check: a non-axis-aligned clean wall pair returned `[]`; the same pair offset 0.05 m along its normal returned `not coplanar`.
- IDF calibration: sm21 opus = 0 issues, sm21 deepseek = 0, sm16 glazingfix = 0, sm21 sonnet = 4 existing slivers only.

### G2 - PASS, with test-strength note

The missing focused tests have been added. `tests/test_interzone.py:77-171` covers clean wall/floor pairs, missing targets, target not Surface, non-reciprocity, duplicate incoming targets, area mismatch, normal direction, vertical/horizontal coplanarity, slivers, and audit counting.

The issue-string assertions are acceptable because each test isolates a single failure class. The one weak spot is G3's audit fixture, discussed below.

### G3 - PASS

The implementation now counts actual mutual reciprocal pairs rather than deriving the value from raw Surface-OBC count. `src/validator/interzone.py:208-221` builds a set of mutual `frozenset((source, target))` pairs only when both surfaces point back to each other, and `src/validator/interzone.py:223-230` reports `len(mutual)`.

Test adequacy note: `tests/test_interzone.py:163-171` intends to pin this, but with one clean pair plus one broken Surface-OBC object, the old `3 // 2` count also equals 1. This should be strengthened with an odd/even broken graph where the old raw count differs from the actual mutual-pair count. This is not an implementation blocker.

### G4 - PASS

The workflow gate validates once and passes the computed issues into the audit. `src/mcp/tools/workflow.py:28-30` calls `validate_interzone_surface_pairs(idf)` once, then `audit_interzone_surface_pairs(idf, issues=issues)`.

### T1 - PASS

The two-step main path now passes raw `testdata_prompt.json` content to phase 2. `scripts/run_full_pipeline.py:171-173` reads `testdata_raw` before building the human-readable `user_input`, `scripts/run_full_pipeline.py:213-219` stores it in `AgentState.testdata_text`, and `src/agent/nodes/intake.py:182-192` passes `state.testdata_text or state.user_input` to `run_phase2`.

The raw-vs-summary behavior is pinned by `tests/test_intake_twostep.py:48-58`.

### T2 - PASS

`run_phase2` is now self-contained with respect to IDD/schema initialization. `src/agent/phase2.py:200-205` calls `ensure_schema_initialized()` before `IntakeOutput.model_json_schema()` and `IntakeOutput.model_validate()` are used later in the same function.

### T3 - PASS

The two-step branch no longer falls through to legacy single-step when validation errors exist. `src/agent/nodes/intake.py:160-172` short-circuits only prefilled intake without errors, and `src/agent/nodes/intake.py:172-193` selects phase 2 whenever `phase1_vector_dir` is present. Errors are forwarded as feedback via `src/agent/nodes/intake.py:184` and appended into the phase2 prompt at `src/agent/phase2.py:160-165`.

This is covered by `tests/test_intake_twostep.py:48-64` and the clean no-feedback case at `tests/test_intake_twostep.py:68-82`.

Regression check:
- `MAX_RETRIES` remains 0 (`src/agent/_share.py:7`), so automatic validate retry is still disabled; human rejection can still route back to intake with feedback.
- For `--phase1-from`, that feedback stays in two-step phase2 as intended.
- For `--intake-from`, if a human later rejects with errors, there is no `phase1_vector_dir`, so the graph uses the legacy intake repair path. That behavior predates this fix and is not a regression in the two-step path.

### T4 - PASS

Phase2 artifact persistence is restored for the graph path. `AgentState.phase2_debug_dir` is defined at `src/agent/state.py:203-205`, `scripts/run_full_pipeline.py:213-220` sets it to `<output>/phase2_intake` for `--phase1-from`, `src/agent/nodes/intake.py:185-192` passes it as `out_dir`, and `src/agent/phase2.py:217-218` creates the directory before writing artifacts.

The e2e output contains `phase2_intake/raw_response.txt`, `phase2_intake/thinking.txt`, and `phase2_intake/intake_output.json`. The rejected IDF path exists, and no top-level `eplusout.*` files were present in `output_twostep_e2e`, consistent with the gate stopping before EnergyPlus.

### T5 - PASS

The private loader has been promoted cleanly. `src/agent/llm.py:14-24` exposes public `load_llm_section`, and `src/agent/phase2.py:31-32` imports it instead of duplicating config parsing.

### Extra robustness fix - PASS

The OpenAI client bound in `src/agent/phase2.py:233` uses `timeout=600.0, max_retries=2`. Given the request context that DeepSeek thinking over a large phase2 prompt can legitimately take minutes, this is a reasonable bound: long enough for the workload, no longer an unbounded hang.

## Regression hunt

No blocking regressions found.

Coplanarity false positives: the real-IDF calibration did not add false kills on the known-good artifacts:
- `test_data/SmallOffice_TwoStep/smalloffice_21/output_opus/temp_20260528_095528.idf`: 0 issues
- `test_data/SmallOffice_TwoStep/smalloffice_21/output_deepseek/temp_20260528_082631.idf`: 0 issues
- `test_data/SmallOffice/smalloffice_16_newarch/output/temp_20260507_154141_glazingfix.idf`: 0 issues
- `test_data/SmallOffice_TwoStep/smalloffice_21/output_sonnet/temp_20260528_095508.idf`: 4 issues, all known 0.05 m slivers

Fresh e2e artifact:
- `test_data/SmallOffice_TwoStep/smalloffice_21/output_twostep_e2e/temp_20260529_073010.idf`: 6 issues, matching the request's expected gate rejection class: 2 slivers, 2 area mismatches, 1 duplicate target, 1 non-reciprocal reference.

`out_dir` existence: `run_phase2` creates `out_dir` before writing, so a missing `<output>/phase2_intake` path is safe.

## Test adequacy

`tests/test_interzone.py` is broad enough for the validator's owned behavior, with the one G3 fixture weakness noted above. I would adjust that fixture, but I would not keep the prior review open on it because the implementation itself is correct and was also verified by IDF calibration.

`tests/test_intake_twostep.py` pins the three riskiest plumbing contracts: raw testdata, feedback-preserving two-step repair, and phase2 debug-dir propagation. T2 is verified by code inspection rather than a dedicated unit test; acceptable for this reverify because the fix is a single top-of-function idempotent call.

## Verification run

Commands/checks run:
- `git log --oneline -3`: `ad50cb8`, `c9bdfd5`, `692d454`
- `pytest -q`: 20 passed
- InterZone validator calibration over the four named historical IDFs plus the fresh `output_twostep_e2e` IDF
- Confirmed no `eplusout.*` exists directly under `output_twostep_e2e`

---

## Disposition (main dev agent, 2026-05-29)

Both prior reviews (`2026-05-29_interzone_pair_gate_review.md`,
`2026-05-29_twostep_intake_node_switch_review.md`) **CLOSED** — all G1–G4 / T1–T5 PASS per this re-verify.

- **G3 test-strength note — ADDRESSED.** `tests/test_interzone.py::test_audit_counts_only_mutual_pairs`
  now uses 1 clean mutual pair + **two** broken Surface-OBC references, so the old `Surface//2` count
  (4//2 = 2) diverges from the actual mutual-pair count (1); the test would now fail the old
  implementation. Full suite 23/23 (added per-case LLM config tests too).

No other actions required from this re-verify.
