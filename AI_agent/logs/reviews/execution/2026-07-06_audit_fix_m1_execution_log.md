# M1 parity execution log

Date: 2026-07-06
Executor: Codex
Repo: `/workspaces/EnergyPlus-Agent-dev`

## Backups

Backed up existing files before editing under
`backup/src_history/2026-07-06_m1_parity/`, preserving repo-relative paths:

- `src/agent/pipeline.py`
- `src/agent/execution/evidence_preflight.py`
- `src/validator/checks/assembly.py`
- `src/agent/execution/validation_run.py`
- `tests/test_run_pipeline_self_checks.py`

`tests/test_check_parity.py` and this execution log are new files.

## Changes

- `src/agent/execution/evidence_preflight.py:168`
  - Kept `compute_evidence_debt_from_vector_dir(...)` as the existing public API.
  - Added `compute_reading_report_from_vector_dir(...)` at line 185 to compute the full aggregated S0 `CheckReport` once.
  - `evidence_debt.json` remains the same strict `EvidenceDebt` model; no fields or shape changes.

- `src/agent/pipeline.py:49`
  - Switched `run_pipeline` to import the full S0 report helper and `project_evidence_debt`.

- `src/agent/pipeline.py:814`
  - Implemented the adjudicated S0 order:
    1. compute the full S0 report once,
    2. create/write `0_reading/reading_checks.json`,
    3. project evidence debt from the same report,
    4. write `1_correction/evidence_debt.json`,
    5. preserve the existing A8 evidence-debt raise and message,
    6. run the new profile-tiered `0_reading` gate.

- `src/agent/pipeline.py:939`
  - Made downstream stage directory creation lazy so strict S0 failures do not pre-create later empty stage dirs.

- `src/validator/checks/assembly.py:23`
  - Added `run_profile` to `check_assembly(...)` and stored it on the emitted `CheckReport`.

- `src/agent/execution/validation_run.py:231`
  - Threaded `run_profile` from `validate_case(...)` into `check_assembly(...)`.

- `src/agent/pipeline.py:1026`
  - Threaded `run_profile` from `run_pipeline(...)` into `check_assembly(...)`.
  - Extracted `assembly.contract_backstop` issues from the single report instead of calling `validate_contract(...)` again.
  - Preserved the all-profile contract hard raise, current error message, and `contract_issues.json` write.
  - Routed future non-contract S5 blockers through `_gate_self_check_report(...)` without double-writing `assembly_checks.json`.

- `tests/test_run_pipeline_self_checks.py:331`
  - Added golden S0 invariant raise test for `reading.pen_kind_valid`, asserting `reading_checks.json` and `evidence_debt.json` are written first.
  - Added exploratory S0 invariant warn-and-continue test.
  - Added monkeypatched future S5 blocker test proving `assembly_checks.json` is consumed by the gate.

- `tests/test_check_parity.py:1`
  - Added artifact-based parity lock.
  - Collector reads actual `*_checks.json` artifacts emitted by `run_pipeline`.
  - S0 aggregate IDs are normalized from `1f_view.reading.*` to `reading.*`.
  - Explicit documented exclusions cover `kernel.artifact_consistency`, S3 serializer text equality, `check_ep_baseline`, and the A8 pre-core sidecar.

## Decisions

- Did not introduce a production check registry; the adjudication requested a test-side artifact collector.
- Did not change `src/validator/checks/reading.py`, `src/validator/checks/mep.py`, or `pyproject.toml`.
- Did not run the pipeline or EnergyPlus.
- Kept A8 evidence-debt behavior ahead of the new S0 gate. A test fixture initially triggered A8 evidence debt before the intended S0 invariant; the fixture was adjusted to isolate `reading.pen_kind_valid` while preserving the required A8 ordering.

## Verification

Targeted tests only:

```text
python -m pytest tests/test_check_parity.py tests/test_run_pipeline_self_checks.py tests/test_a8_evidence_routing.py
```

Result:

```text
23 passed in 3.72s
```

Additional non-test check:

```text
git diff --check -- src/agent/pipeline.py src/agent/execution/evidence_preflight.py src/validator/checks/assembly.py src/agent/execution/validation_run.py tests/test_run_pipeline_self_checks.py tests/test_check_parity.py
```

Result: clean.

## Deviations

None from the adjudicated M1 scope.

## Post-merge fix

After M2 landed, full-suite verification exposed one shared test fixture issue in
`tests/test_run_pipeline_self_checks.py`: `_patch_llm_stages` generated MEP
constructions backed only by `Material:NoMass`, which now violates M2's
`mep.construction_thermal_mass` invariant before tests can reach their intended
S1/S4/S5 assertions.

Fix applied: changed the stub MEP fragment to define one exact `Material` object
(`Mat_Mass`) with the standard mass-layer fields and reference it from every
generated construction. No production MEP check was weakened.

Post-merge targeted verification:

```text
/opt/venv/bin/python -m pytest -q tests/test_run_pipeline_self_checks.py tests/test_check_parity.py
```

Result:

```text
11 passed in 3.31s
```
