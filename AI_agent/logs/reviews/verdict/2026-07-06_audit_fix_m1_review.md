# M1 parity proposal review

Verdict: **APPROVE-WITH-CHANGES**.

I verified against the local working tree only. The brief's main diagnosis is correct: S0 reading checks are only projected into A8 evidence debt in `run_pipeline`, and S5 `assembly_checks.json` is written but not gated. The execution plan should proceed, but only with the fixes below.

## Findings

1. **HIGH — Preserve A8 sidecar write-before-raise semantics when adding S0 gating.**  
   Local evidence: `run_pipeline` currently computes evidence debt at `src/agent/pipeline.py:821` (`evidence_debt = compute_evidence_debt_from_vector_dir(`), writes it at `src/agent/pipeline.py:828` (`write_evidence_debt(s1 / "evidence_debt.json", evidence_debt)`), then raises at `src/agent/pipeline.py:829` (`if evidence_debt.blocking:`). Public tests depend on that ordering: `tests/test_a8_evidence_routing.py:299` expects a regression raise, and `tests/test_a8_evidence_routing.py:302` reads the sidecar afterward.  
   Fix: compute full S0 reports once, write `0_reading/reading_checks.json`, project/write `1_correction/evidence_debt.json`, then apply strict S0 failure behavior. If the new S0 gate intentionally replaces the old `"preflight blocked"` raise, update the A8 test explicitly; do not accidentally stop before the sidecar exists.

2. **HIGH — Do not replace S5's all-profile contract hard stop with `_gate_self_check_report` alone.**  
   Local evidence: `_gate_self_check_report` raises only for strict profiles at `src/agent/pipeline.py:751` (`if run_profile in {"golden", "regression"}:`) and otherwise warns/continues at `src/agent/pipeline.py:758` (`logger.warning(`). Current S5 raises for every profile after `validate_contract` at `src/agent/pipeline.py:1018` (`contract_issues = validate_contract(intake, used_constructions)`) and `src/agent/pipeline.py:1025` (`raise RuntimeError(`). `RunProfile` also includes `"dev"` (`src/validator/checks/schema.py:39`), so this is an exploratory/dev regression if mishandled.  
   Fix: call `check_assembly`/`validate_contract` only once, but preserve the current all-profile raise for `assembly.contract_backstop`. The least disruptive shape is: write `assembly_checks.json` from the single `assembly_report`; extract contract issues from that report's evidence; if present, write `contract_issues.json` and raise with the current message; otherwise call `_gate_self_check_report(..., stage_dir=None, filename=...)` so future non-contract S5 blockers are gated without double-writing.

3. **MEDIUM — `evidence_debt.json` shape must remain strict-compatible.**  
   Local evidence: both `EvidenceDebtItem` and `EvidenceDebt` forbid extras (`src/agent/execution/evidence_preflight.py:30`, `model_config = ConfigDict(extra="forbid")`; `src/agent/execution/evidence_preflight.py:45`, `class EvidenceDebt(BaseModel):` then `src/agent/execution/evidence_preflight.py:46`, `model_config = ConfigDict(extra="forbid")`). Loads are strict at `src/agent/execution/evidence_preflight.py:206` (`return EvidenceDebt.model_validate_json(...)`) and in correction at `src/validator/checks/correction.py:213` (`return EvidenceDebt.model_validate(evidence_debt)`).  
   Fix: do not add full reading reports or new metadata fields to `evidence_debt.json`. Add a helper that returns full S0 reports plus the same projected `EvidenceDebt`, but keep `write_evidence_debt()` output byte-shape compatible.

4. **MEDIUM — The S5 gate must use the report's run profile, not only the helper argument.**  
   Local evidence: `CheckReport.blocking()` computes dispositions from `self.run_profile` via `src/validator/checks/schema.py:192` (`def dispositions`) and `src/validator/checks/schema.py:199` (`run_profile=self.run_profile`). `check_assembly` currently creates a report without a run profile at `src/validator/checks/assembly.py:32` (`rep = CheckReport(stage="5_intakeoutput", capability_profile=capability_profile)`).  
   Fix: either add `run_profile` to `check_assembly(..., run_profile=...)` and thread it from both `run_pipeline` and `validate_case`, or have the gate helper evaluate dispositions with the external `run_profile`. Current invariant behavior is okay, but the proposed "future check_id" protection is incomplete otherwise.

5. **MEDIUM — Parity test should compare actual emitted reports, not a copied check-id table.**  
   Local evidence: existing parity coverage only snapshots S1/S4/S5 statuses in `tests/test_run_pipeline_self_checks.py:331` (`def test_run_pipeline_inline_reports_match_validate_case`) through `tests/test_run_pipeline_self_checks.py:363`, and S0 is absent. `validate_case` uses per-view S0 keys at `src/agent/execution/validation_run.py:140` (`res.reports[f"0_reading::{vj.stem}"] = rep`). Report evidence IDs preserve those keys at `scripts/tool_scripts/report_assembly.py:318` (`eid = f"E:gate:{report_key}:{result.check_id}{suffix}"`).  
   Fix: implement a small test-side collector that reads actual `*_checks.json` artifacts emitted by `run_pipeline`, excludes explicitly documented non-gated sidecars such as `evidence_debt_coverage_checks.json`, normalizes S0 view prefixes, and compares to `validate_case(...).reports`. This is less rot-prone than a static copied check-id list and avoids a full registry.

6. **LOW — The brief undercounts S0 check IDs, but the factual direction is right.**  
   Local evidence: `check_reading_view` starts at `src/validator/checks/reading.py:87` and calls many helpers through `src/validator/checks/reading.py:150`. Dynamic IDs are generated at `src/validator/checks/reading.py:188` (`f"reading.{kind}_ids_unique"`), and literal examples include `src/validator/checks/reading.py:350` (`"reading.pen_kind_valid"`), `src/validator/checks/reading.py:589` (`"reading.facade_fields"`), and `src/validator/checks/reading.py:682` (`"reading.dimension_chain_closure"`). The code has more than the six evidence IDs in `src/validator/checks/schema.py:41`-`50`.  
   Fix: phrase the implementation around "full S0 report" rather than a fixed approximate count.

## Review Questions

1. **S0 gate position/timing:** put S0 computation before correction. To preserve A8 behavior, compute once, write `0_reading/reading_checks.json`, project/write `1_correction/evidence_debt.json`, then perform the strict S0/A8 raise path. `run_pipeline` currently has no S0 stage directory (`src/agent/pipeline.py:807`-`811` only creates S1-S5), so add `_stage("0_reading")` when `out_dir` is present.

2. **All `evidence_debt.json` consumers:** source consumers are `run_pipeline`/`run_correction` write and prompt injection (`src/agent/pipeline.py:353`, `src/agent/pipeline.py:541`, `src/agent/pipeline.py:828`), `validate_case` load (`src/agent/execution/validation_run.py:154`), correction coverage (`src/validator/checks/correction.py:257`), stepwise `run_stage` load (`scripts/tool_scripts/run_stage.py:165`), report assembly indexing (`scripts/tool_scripts/report_assembly.py:392`, `:399`), record-baseline/report rendering (`scripts/tool_scripts/record_baseline.py:514`, `:735`), and tests (`tests/test_a8_evidence_routing.py:274`, `:302`, `:333`). Checked-in baselines/reports also reference it, but they are artifacts, not parsers.

3. **`reading_checks.json` write conflict:** `validate_case` does **not** write `reading_checks.json`. It writes per-view files at `src/agent/execution/validation_run.py:142` (`_write(rdir / f"{vj.stem}_checks.json", rep)`). A new aggregate `0_reading/reading_checks.json` will not collide, but the parity normalizer must account for aggregate-vs-per-view shape.

4. **Parity route:** prefer actual-report collection plus normalization over a production registry. Keep an explicit allow/exclude list only for known structural exceptions: `kernel.artifact_consistency` (`src/agent/execution/validation_run.py:195`), S3 serializer text mismatch (`src/agent/execution/validation_run.py:208`), EP baseline (`src/agent/execution/validation_run.py:245`), and A8's pre-core sidecar (`src/agent/pipeline.py:853`).

5. **S5 all-profile tests:** yes, they break if the implementation removes the raw all-profile raise and relies only on `_gate_self_check_report`. They do not break if contract issues are raised specially from the single `assembly_report` before the profile-split gate handles future non-contract blockers.

6. **Missed behavior surfaces:** `intake_node` calls `run_pipeline` without a profile at `src/agent/nodes/intake.py:64`-`66`, so default exploratory must remain warn-and-continue for new S0 non-contract blockers. `dev` is a real run profile and currently behaves like exploratory under the gate. Avoid double-writing `assembly_checks.json`; avoid changing `evidence_debt.json`; and verify anchors rather than editing them, because `validate_case` anchor tests are already xfailed for re-recording (`tests/test_validation_run_baseline.py:26`-`29`).

I did not run pytest or EnergyPlus; this review used local file reads and greps only.
