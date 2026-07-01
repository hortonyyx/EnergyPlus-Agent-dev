# Review: bucket ③ close proposal

Verdict: **APPROVE-WITH-CHANGES**.

The two intended changes are sound: S5 can inline `check_assembly` as an artifact-only backstop, and the D1 reversal on kernel is acceptable now that the explicit scope is to tighten strict-profile `run_pipeline` from "InterZone-only" to all kernel invariant blocks. The proposal does need a few required adjustments: update the one old-message test, add direct non-pairing kernel gate tests, keep assembly out of `_gate_self_check_report`, and stop relying on the absolute "golden baselines cannot contain this" claim.

## Factual Verification

- **(a) `check_assembly` is only a `validate_contract` backstop: TRUE.** It constructs a `CheckReport`, re-runs `validate_contract`, and records only `assembly.contract_backstop`; there is no extra validation logic: `src/validator/checks/assembly.py:23-41`. `validate_contract` itself only checks that each `used_constructions` name appears as a whole token in `construction_specs`: `src/agent/intakeoutput.py:60-83`.

- **(b) `validate_contract` already raises for all run profiles in `run_pipeline`: TRUE.** Current `run_pipeline` calls `validate_contract` and raises unconditionally on issues, with no `run_profile` branch: `src/agent/pipeline.py:1011-1021`. This is why S5 must not be converted to `_gate_self_check_report`; the existing all-profile hard stop is stronger than the helper's golden/regression-only raise.

- **(c) `kernel_report.blocking()` includes InterZone issues through `kernel.pairing_gate`: TRUE.** `run_pipeline` passes `interzone_issues=kernel_issues` into `check_kernel`: `src/agent/pipeline.py:947-952`. `_pairing_gate` emits `kernel.pairing_gate` as an invariant `FAIL` when that list is non-empty: `src/validator/checks/kernel.py:177-196`. `CheckReport.blocking()` returns any result whose disposition is `BLOCK`: `src/validator/checks/schema.py:192-211`; invariant failures block at `src/validator/checks/schema.py:143-145`. Switching to `kernel_report.blocking()` does not drop the existing InterZone strict raise.

- **(d) The five kernel sub-checks are invariant-layer checks: TRUE.** `check_kernel` invokes the five checks at `src/validator/checks/kernel.py:70-74`. The emitted rows use `CheckLayer.INVARIANT` for zone closure (`src/validator/checks/kernel.py:137-142`), normals (`src/validator/checks/kernel.py:168-174`), pairing gate (`src/validator/checks/kernel.py:188-196`), spec self-consistency (`src/validator/checks/kernel.py:214-218`), and coverage completeness (`src/validator/checks/kernel.py:227-228`, `src/validator/checks/kernel.py:265-277`).

- **(e) "Golden baselines can't already contain kernel-non-interzone blocks": OVERSTATED.** `validate_case` does mark all `rep.blocking()` results into `res.blocked`: `src/agent/execution/validation_run.py:317-321`. But `record_baseline` defaults `run_profile="exploratory"` and records `blocked` into baseline metadata instead of aborting the record operation: `scripts/tool_scripts/record_baseline.py:292-309`, `scripts/tool_scripts/record_baseline.py:326-347`, `scripts/tool_scripts/record_baseline.py:670-674`. So the impossibility claim is too strong. Practical impact is still low: the checked-in anchor `kernel_checks.json` files have all five kernel rows passing (`case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/2_modelling/kernel_checks.json:9`, `:19`, `:29`, `:37`, `:45`; same row layout in both sm21 checked-in kernel reports), and a read-only rebuild of all six checked-in run directories under `case_tests/e2e_tests/*/run_*` found no current `check_kernel(..., run_profile="golden")` blockers.

## A1-A5 Rulings

**A1: S5 double-run and write-before-raise.** Accept the double `validate_contract` run. It is cheap, clearer, and preserves `check_assembly` as the canonical validate_case wrapper. Write `5_intakeoutput/assembly_checks.json` immediately after `check_assembly(...)` and before the existing `validate_contract` raise, so contract-failure runs still leave the diagnostic artifact. Keep the existing `contract_issues.json` and unconditional `RuntimeError` behavior unchanged.

**A2: Kernel advisory double warning.** Accept for this round. With InterZone issues under exploratory/dev, `run_pipeline` will log the existing advisory warning at `src/agent/pipeline.py:928-935` and `_gate_self_check_report` will also warn because `kernel_report.blocking()` is non-empty: `src/agent/pipeline.py:747-765`. The messages point at different artifacts/semantics. No visible test asserts warning count or absence.

**A3: Existing test break from the message change.** I found exactly one visible assertion that will break:

- `tests/test_a8_evidence_routing.py:374-382`, `test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles`, parametrized over `golden` and `regression`, currently has:
  `with pytest.raises(RuntimeError, match="InterZone pairing gate blocked"):`

Required fix: change the match to the helper message and still assert the report row:

```python
with pytest.raises(
    RuntimeError,
    match=rf"2_modelling self-check blocked under run_profile={run_profile}: .*kernel\\.pairing_gate",
):
    pipeline.run_pipeline(...)
```

or drop the message match and assert `kernel.pairing_gate` in `str(exc.value)`. I found no other `InterZone pairing gate blocked` assertion. The exploratory kernel test at `tests/test_a8_evidence_routing.py:336-370` should continue to pass; it does not capture warnings and the report content stays the same.

**A4: D1 reversal.** Sound, given this round's explicit scope. The previous "do not fold kernel into generic gate" review was preventing an accidental behavior change during S1/S4 work. This proposal intentionally makes that behavior change, and it aligns `run_pipeline` strict profiles with `validate_case`'s handling of kernel invariant blocks. I found no existing exploratory-profile test that depends on kernel non-pairing invariant failures being both non-raising and silent. Existing warning capture is limited to S1/S4 self-checks in `tests/test_run_pipeline_self_checks.py:204-228`, and loguru warnings are not Python warnings. The helper also treats `dev` like exploratory (warn and continue), which should be stated if this behavior matters.

**A5: `_gate_self_check_report` for kernel.** Semantically appropriate as-is if the implementation passes the external `run_profile` into `check_kernel` and uses the helper as the only `kernel_checks.json` writer. The helper writes before raising (`src/agent/pipeline.py:743-747`), raises only for golden/regression with the external profile in the error message (`src/agent/pipeline.py:750-757`), and warns otherwise with blocking check ids (`src/agent/pipeline.py:758-765`). Note that `blocking = report.blocking()` uses `report.run_profile`, not the helper's external parameter, so do not accidentally call `check_kernel` without `run_profile=run_profile`.

## Missed Risks / Required Guardrails

1. **Test the new kernel behavior with a non-pairing block.** Add one strict-profile test where `kernel_report.blocking()` contains `kernel.coverage_completeness`, `kernel.normals`, or `kernel.spec_self_consistency` without relying on `kernel_issues`. A monkeypatch of `src.validator.checks.kernel.check_kernel` is acceptable because `run_pipeline` imports it lazily at call time (`src/agent/pipeline.py:945-952`). Also add the exploratory counterpart proving it writes `kernel_checks.json`, warns, and continues to S5.

2. **Ordering is a behavior change for strict profiles.** The new kernel gate will raise before S3/S4/S5 for any kernel invariant block. That matches the proposal, but tests should assert the expected artifact boundary: `building_geometry.json`, `kernel_gate_report.json`, and `kernel_checks.json` exist; `3_split_pairing/geometry_specs.md` does not.

3. **`coverage_completeness` NOT_APPLICABLE is correctly excluded from blocking.** Non-rectangular coverage emits `NOT_APPLICABLE` at invariant layer (`src/validator/checks/kernel.py:226-229`), and schema maps `NOT_APPLICABLE` to `INFO` before invariant handling (`src/validator/checks/schema.py:119-124`). This is safe; do not add a special kernel-side exclusion.

4. **Checked-in anchors are clean, but don't rely on the stronger recording guarantee.** Current on-disk anchor runs should not newly fail under the upgraded gate; the current checker reports no kernel blockers for all six checked-in run directories. The proposal should phrase this as an observed repository fact, not as a property guaranteed by baseline recording.

5. **Assembly report profile is an existing limitation.** `check_assembly` has no `run_profile` parameter, so `assembly_checks.json` will carry the default exploratory profile even during golden/regression runs. That matches current `validate_case` behavior (`src/agent/execution/validation_run.py:227-241`) and is fine because S5 remains governed by the separate all-profile `validate_contract` raise. Do not later gate S5 through `report.blocking()` without first adding `run_profile` to `check_assembly`.

## Required Changes Before Execution

1. Add `check_assembly` inline in S5, write `assembly_checks.json` before the existing `validate_contract` block, and leave the existing all-profile contract raise untouched.
2. Replace the manual kernel `kernel_checks.json` write plus `kernel_issues`-only strict raise with `_gate_self_check_report(... filename="kernel_checks.json" ...)`, with no duplicate write.
3. Update `tests/test_a8_evidence_routing.py::test_run_pipeline_fail_closed_for_kernel_pairing_gate_profiles` to match the new helper error text or assert on `kernel.pairing_gate` in the exception string.
4. Add direct tests for strict-profile non-pairing kernel invariant blocking and exploratory visible-but-continue behavior.
5. Adjust the proposal/implementation notes to avoid claiming baseline recording makes blocked kernel reports impossible; current anchors are clean, but the tooling does not enforce that as an absolute.
