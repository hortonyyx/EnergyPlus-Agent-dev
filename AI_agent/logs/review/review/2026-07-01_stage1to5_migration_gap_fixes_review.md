# Review: Stage 1-5 Migration Gap Fix Proposal

Verdict: **APPROVE-WITH-CHANGES**

The proposal's high-level triage is correct against the current working tree. The Stage 0 conflicts are stale, S1-10/S1-12 belong in Phase B, and the four selected fixes are the right near-term scope. I would not send the execution brief unchanged: S4-07 needs a more robust People field locator, S23-16 needs to reuse the existing `CheckReport`/`kernel.pairing_gate` plumbing instead of vaguely "run_state/report", and S1-18 should sweep the adjacent residual placeholders in the same A0 line.

## Per-finding assessment

| Finding | Assessment | Evidence |
|---|---|---|
| S0-04 | Agree stale/resolved. Reading is now image-local and explicitly forbids world axis/sign/base in elevation. | `skills/intake_pipeline/0_reading/guide.md:88-95`, `skills/intake_pipeline/0_reading/guide.md:323-336` |
| S0-05 | Agree stale/resolved. The old `scale_origin` carrier is gone from the guide; the schema example now uses `facade` and says no world axis/sign/base. | `skills/intake_pipeline/0_reading/guide.md:112-118` |
| S0-15 | Agree stale/resolved. `uncaptured` is canonical top-level, and clean drawings may use `[]`; non-empty is required only when something was healed/excluded. | `skills/intake_pipeline/0_reading/guide.md:254-261`, `skills/intake_pipeline/0_reading/guide.md:358`, `skills/intake_pipeline/0_reading/guide.md:385` |
| S0-26 | Agree stale/resolved. Correction still injects `reading_summary.md`, but only as a reference block; the old instruction to use summary section 3 formulas verbatim is gone. | `src/agent/pipeline.py:330-338` |
| S1-10 | Agree defer to Phase B. Correction/runtime still require rectangular `x/y` cells, while modelling is already polygon-native. This is a schema/prompt/kernel capability alignment issue, not a small patch. | `src/agent/pipeline.py:315-320`, `src/agent/correction/schema.py:8-10`, `src/agent/correction/schema.py:36-37`, `skills/intake_pipeline/2_modelling/spec.md:13-15`, `skills/intake_pipeline/2_modelling/spec.md:40-41`, `src/agent/geometry/modelling.py:163-174` |
| S1-12 | Agree defer to Phase B. `derive_facade_frame()` exists, but the current production correction path still asks the LLM for world-frame window spans and has no production call to the deterministic translator. Phase B already tracks this with E/W sign validation. | `src/agent/correction/facade.py:69-108`, `src/agent/pipeline.py:315-320`, `AI_agent/plan.md:101` |
| S4-07 | Agree in scope, but change the implementation spec. For valid parsed People objects, `fields[9]` is the activity-level schedule because `idf_fragments` drops the object-type token and People field order puts activity after sensible heat fraction. Still, `IdfObject.raw` is retained, so use eppy field-name access (`Activity_Level_Schedule_Name`) with a positional fallback rather than hard-coding index 9. Also fail blank/missing activity schedule, not only undefined refs. Existing `mep.schedule_type_refs` does not cover this; it only checks each `Schedule:Compact` type-limit reference. | `src/validator/idf_fragments.py:43-46`, `src/validator/idf_fragments.py:76-79`, `src/validator/data_model.py:1522-1548`, `src/converters/people_converter.py:30-42`, `src/validator/checks/mep.py:115-127`, `src/validator/checks/mep.py:140-167`, `skills/intake_pipeline/4_mep/authoring.md:115-121` |
| S23-16 | Agree in scope and agree with the user-decided profile behavior, but the proposal is under-specified on plumbing. `run_pipeline` currently writes advisory `kernel_gate_report.json` and continues, while downstream MCP export/simulation hard-blocks the same class. The canonical check already exists as `kernel.pairing_gate` in `check_kernel`; the fix should reuse it. | `src/agent/pipeline.py:677-687`, `src/agent/pipeline.py:699-708`, `src/agent/pipeline.py:724-732`, `src/agent/pipeline.py:861-877`, `src/mcp/tools/workflow.py:168-185`, `src/mcp/tools/workflow.py:244-260`, `src/validator/checks/kernel.py:58-68`, `src/validator/checks/kernel.py:172-191` |
| S1-09 | Agree in scope as prose-only. Adding a corridor rule is useful, but it must be worded as evidence-supported identity arbitration so it does not override A3's "never merge on doubt" rule. No kernel change belongs in this round. | `skills/intake_pipeline/1_correction/A3_arbitration.md:15-17`, `skills/intake_pipeline/1_correction/A3_arbitration.md:31-33`, `skills/intake_pipeline/1_correction/A4_priors.md:35-37`, `src/agent/roles.py:7-24` |
| S1-18 | Agree in scope, but widen the honesty sweep. A0 documents `facade_area_residuals`, `wwr_residuals`, `area residuals`, and `unsupported_count_by_severity`; correction checks do not implement any residual check by those names. Option A is appropriate, preferably as explicit `NOT_APPLICABLE` slots rather than prose-only downgrade. | `skills/intake_pipeline/1_correction/A0_contract.md:184-185`, `skills/intake_pipeline/1_correction/A0_contract.md:291-293`, `src/validator/checks/correction.py:77-82`, `src/agent/correction/geometry_validator.py:164-173`, `src/validator/checks/mep.py:228-233` |

## Findings

### BLOCKER

None.

### MAJOR

1. **S4-07 should not be specified as a bare `fields[9]` patch.**

   `fields[9]` is stable for a valid People object with the normal IDF field layout, but the parser keeps the eppy raw object, and other code already writes People by field names. The concrete execution brief should say:

   - read `Activity_Level_Schedule_Name` from `obj.raw` for `PEOPLE`
   - fallback to `obj.fields[9]` only if raw access is unavailable
   - add a failure for blank/missing activity schedule as well as an undefined schedule name
   - report under `mep.load_to_schedule` unless a new check id is deliberately needed
   - add fixtures for missing activity schedule, undefined activity schedule, and clean primary+activity schedules

   This stays narrower than a schema-wide "scan all schedule-looking fields" approach and avoids false positives.

2. **S23-16 should use the existing kernel check/report channel, not a vague new run_state signal.**

   Current blocking/report plumbing is:

   - `CheckReport.blocking()` maps invariant failures to `BLOCK`: `src/validator/checks/schema.py:70-80`, `src/validator/checks/schema.py:143-145`, `src/validator/checks/schema.py:205-219`
   - validation adds blocking rows to `CaseValidationResult.blocking_summary`: `src/agent/execution/validation_run.py:299-303`
   - report assembly indexes all block/flag gate rows as `E:gate:...`: `scripts/tool_scripts/report_assembly.py:301-327`
   - baseline/report rendering consumes `blocked`, `blocking`, and `flags`: `scripts/tool_scripts/record_baseline.py:305-338`, `scripts/tool_scripts/record_baseline.py:543-556`, `scripts/tool_scripts/record_baseline.py:604-609`

   `run_state` itself is derived from the stepwise orchestration ledger, not gate reports: `scripts/tool_scripts/report_assembly.py:228-287`. Do not silently overload it unless the execution brief explicitly adds a derived validation-blocked field. Minimal correct plumbing is:

   - have `materialize_kernel_geometry()` or immediately after it write a `2_modelling/kernel_checks.json` produced by `check_kernel(bg, interzone_issues=kernel_issues)`; if adding `run_profile` to `check_kernel`, set the report field but keep `kernel.pairing_gate` an invariant
   - in `run_pipeline`, after the kernel report is written, raise for `run_profile in {"golden", "regression"}` when `kernel_issues` is non-empty; leave exploratory/dev artifacts written and continue only if that is still desired
   - rely on `summarize_gates()` / `build_evidence_index()` for report visibility instead of creating a parallel InterZone sidecar vocabulary
   - add a test that injects an InterZone issue, runs exploratory profile, and proves the artifact/report has `kernel.pairing_gate` as blocking-severity while artifacts still exist
   - add the golden/regression fail-closed test

   Existing legacy anchors should not be affected: sm20 and the two sm21 clean anchor runs already have `kernel.pairing_gate` entries and empty gate issues. See `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/2_modelling/kernel_checks.json:29`, `case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/2_modelling/kernel_gate_report.json:2`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/2_modelling/kernel_checks.json:29`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/2_modelling/kernel_gate_report.json:2`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/2_modelling/kernel_checks.json:29`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/2_modelling/kernel_gate_report.json:2`.

   I found no test that combines a broken InterZone case with run_state/report status. Existing tests cover `kernel.pairing_gate` blocking only at the kernel-check level (`tests/test_checks_kernel.py:101-104`) and cover `run_state` derivation separately (`tests/test_orchestrate_baseline.py:395-430`). Add the combined regression.

3. **S1-18 should not single out only WWR.**

   A0 lists a group of residual soft checks in one promise: facade-area residuals, WWR residuals, area residuals, and unsupported severity count. The code has no residual check implementation. If the chosen fix is "honest placeholder", make the placeholder group explicit:

   - either update A0 to label all residual checks as deferred placeholders
   - or add `correction.facade_area_residuals`, `correction.wwr_residuals`, `correction.area_residuals`, and possibly `correction.unsupported_count_by_severity` as `NOT_APPLICABLE` cross-check entries with a clear "deferred until evidence is richer" message

   The second option is more machine-visible and matches the existing `mep.reasonability_bands` pattern.

### MINOR

1. **S1-09 wording needs a guardrail.**

   Recommended wording for A3:

   > Corridor/circulation identity: if adjacent corridor fragments are supported by continuous circulation evidence (same label/use, open passage, continuous centerline/width, and no physical wall/door partition between them), prefer one continuous corridor zone. Do not merge across a drawn wall, door-controlled partition, fire/stair/core boundary, floor break, or unresolved identity ambiguity; when evidence is insufficient, keep distinct cells or mark `unsupported` rather than merging on doubt.

   This preserves A3's current identity-ambiguity policy.

2. **S1-12 deferral should explicitly include production wiring and tests.**

   The Phase B task should name the production call sites and E/W sign tests, not only "derive facade frame". The current function is good raw material, but it is not load-bearing.

3. **Ordering and test impact.**

   Suggested execution order:

   1. S4-07, with focused MEP fixtures.
   2. S1-09 and S1-18 documentation/placeholder edits.
   3. S23-16 last, because it touches run/report semantics and needs the broader regression pass.

   Expected suite impact is realistic: S4-07 adds targeted tests; S23-16 adds at least two tests; S1-09/S1-18 should not require golden artifact changes. Run the full suite after S23-16 because it interacts with validation/report generation.

## Recommended proposal edits before execution

1. Replace the S4-07 "fields[9]" recommendation with "use eppy raw field-name access for `Activity_Level_Schedule_Name`, fallback to index 9, fail blank/missing and undefined refs".
2. Rewrite S23-16 plumbing around `check_kernel(..., interzone_issues=...)`, `kernel.pairing_gate`, `kernel_checks.json`, `summarize_gates()`, and `build_evidence_index()`. State clearly that `run_state` currently does not carry gate blocking by itself.
3. Expand S1-18 from WWR-only to the whole residual placeholder group in A0 line 291.
4. Add the corridor wording guardrail above to avoid conflict with "never merge on doubt".
