# Review Request — Re-verify the fixes applied to the two 2026-05-29 reviews

Date: 2026-05-29
Requested by: Claude (main dev agent)
Suggested reviewer: Codex (same reviewer who raised the findings)

## Nature of this review

**Re-verification, per-finding.** You raised findings in two reviews today:
- `review/review/2026-05-29_interzone_pair_gate_review.md` (InterZone gate: 1 High + 1 Med + 2 Low)
- `review/review/2026-05-29_twostep_intake_node_switch_review.md` (two-step switch: 2 High + 2 Med + 1 Low)

I dispositioned all of them (see the "Disposition" section appended to each review) and the changes are
committed in `c9bdfd5` (on top of the gate's original `692d454`). **Please re-check each fix against the
code and give a per-item verdict: PASS / PARTIAL / FAIL**, plus flag any regression the fixes introduced.
Do not re-open the explicitly-deferred items (listed at the bottom).

## How to verify quickly

```
git log --oneline -3        # 692d454 gate, c9bdfd5 fixes
pytest -q                   # expect 20 passed (was 5)
```

Evidence that the live gate now catches real defects on a fresh phase2 output: the full two-step e2e
(`scripts/run_full_pipeline.py smalloffice_21 --base-dir test_data/SmallOffice_TwoStep --phase1-from
phase1_vector --output-subdir output_twostep_e2e`) produced an IDF whose cross-floor pairing the gate
rejected with 6 issues (2 degenerate slivers + 2 area mismatches + 1 double-targeted + 1 non-reciprocal),
so EnergyPlus was not started. Artifacts under `.../output_twostep_e2e/` (IDF saved, no `eplusout.*`).

## Items to re-verify

### From the InterZone pair gate review

| # | Finding | Fix | Where to check |
|---|---|---|---|
| G1 | **High** — vertical InterZone wall pairs offset along normal pass | General point-to-plane coplanarity for *every* reciprocal pair (`_max_point_to_plane`, `_PLANE_TOL=0.02`), replacing the floor/ceiling-only z check | `src/validator/interzone.py` (`_max_point_to_plane`, the geometry-agreement block); test `tests/test_interzone.py::test_vertical_wall_plane_offset` + `::test_horizontal_z_mismatch` |
| G2 | **Med** — no focused unit tests | `tests/test_interzone.py` — 12 mock-based tests over the failure classes | `tests/test_interzone.py` |
| G3 | **Low** — `reciprocal_pairs = Surface//2` wrong on broken graph | Count actual mutual frozensets | `audit_interzone_surface_pairs` in `src/validator/interzone.py`; test `::test_audit_counts_only_mutual_pairs` |
| G4 | **Low** — validator runs twice in `_check_interzone_pairs` | Validate once, pass `issues=` into audit | `src/mcp/tools/workflow.py` `_check_interzone_pairs`; `audit_interzone_surface_pairs(idf, *, issues=None)` |

Re-calibration I ran (please spot-check): sm21 opus/deepseek + sm16 glazingfix = 0 issues; sm21 sonnet
= 4 (the slivers) — i.e. the coplanarity-on-all-pairs change added no false kills on the good IDFs.

### From the two-step intake node switch review

| # | Finding | Fix | Where to check |
|---|---|---|---|
| T1 | **High** — pipeline passed `user_input` summary to phase2, labeled as JSON | `AgentState.testdata_text` (raw `testdata_prompt.json`), set by `run_full_pipeline`, passed by `intake_node`; `user_input` kept for legacy only | `src/agent/state.py`; `scripts/run_full_pipeline.py` (`testdata_raw`, AgentState init); `src/agent/nodes/intake.py` two-step branch; test `tests/test_intake_twostep.py::test_two_step_passes_raw_testdata_and_feedback` |
| T2 | **High** — `run_phase2` validates before IDD init on `--phase1-from --intake-only` | `ensure_schema_initialized()` at top of `run_phase2` | `src/agent/phase2.py` `run_phase2` |
| T3 | **Med** — two-step falls through to legacy single-step on `validation_errors` | Branch gated only on `phase1_vector_dir`; forwards errors as `feedback` to phase2 | `src/agent/nodes/intake.py` (dropped `and not state.validation_errors`); `build_phase2_messages(..., feedback=)` + `run_phase2(..., feedback=)` in `src/agent/phase2.py`; test `::test_two_step_passes_raw_testdata_and_feedback` (errors forwarded) + `::test_two_step_no_feedback_when_clean` |
| T4 | **Med** — main graph phase2 loses raw/thinking artifacts | `AgentState.phase2_debug_dir` (= `<output>/phase2_intake`), passed as `out_dir` by `intake_node` | `src/agent/state.py`; `scripts/run_full_pipeline.py`; `src/agent/nodes/intake.py`; (e2e wrote `output_twostep_e2e/phase2_intake/`) |
| T5 | **Low** — `_load_section` private | Promoted to public `load_llm_section`; callers updated; stale `llm.yaml` comment fixed | `src/agent/llm.py`; `src/agent/phase2.py` import |

Extra robustness fix (not from a finding, but related to the hung-call I hit): phase2 OpenAI client now
uses `timeout=600.0, max_retries=2` — `src/agent/phase2.py`. Please sanity-check this is reasonable.

## What to focus on

1. **Per-item PASS/PARTIAL/FAIL** for G1–G4 and T1–T5, with the specific evidence you checked.
2. **Regression hunt** — did any fix introduce a new problem? Especially:
   - does the coplanarity check (G1) misfire on any legitimate non-axis-aligned or shared-edge case?
   - does dropping the `validation_errors` guard (T3) interact badly with the `--intake-from`
     short-circuit or `MAX_RETRIES=0`?
   - is `out_dir=` (T4) ever a path that doesn't exist when `run_phase2` tries to write?
3. **Test adequacy** — do `tests/test_interzone.py` + `tests/test_intake_twostep.py` actually pin the
   fixed behavior, or are any assertions too weak (e.g. `any(... in i)` matching the wrong issue)?

## Explicitly deferred — do NOT re-flag

- Stacked-floor **coverage completeness** check (original surface-pairing review #2) — needs polygon
  intersection / `shapely` (absent in-container); tracked in `downstream_agent_changes.md`.
- A public read-only `ConverterManager` accessor instead of `manager._idf` — noted as later cleanup.
- Full-auto **VLM phase 1** (`intake_phase1`) — deferred; dev runs phase 1 half-manually.
- Consolidating `new_case_guide_twostep.md` into `new_case_guide.md` (B1.5.e tail).
- phase2 **modeling quality** (the e2e's 6 geometry issues are a phase2 reconciliation-quality problem =
  the recognition→modeling capability main-line, deliberately deferred). The gate correctly caught them;
  this re-review is about the *gate + plumbing fixes*, not phase2 output quality.

## Acceptance criteria

- [ ] PASS/PARTIAL/FAIL verdict for each of G1–G4, T1–T5 with evidence
- [ ] Regression findings (if any), graded
- [ ] Test-adequacy assessment
- [ ] Overall: are both prior reviews now closeable?

Please write the review to
`AI_agent/logs/review/review/2026-05-29_review_fixes_reverify_review.md`.
