# F-20 MAJOR-1 frozen digest lock — terra execution log

Date: 2026-08-10

## Result: legal stop — no test lock added

The dispatch requires the two frozen values to be measured using the code before
the F-20 repair, commit `2c7e0a4`.  Both required calls returned
`geometry_digest=None`.  This is explicitly a legal exit in the dispatch
(§6), so no literal digest exists to freeze and adding a replacement assertion
would violate §2.2.  No files under `tests/` or `src/` were changed.

## Temporary pre-repair checkout

Created a detached temporary worktree, then removed it after the measurement:

```sh
git worktree add --detach /tmp/f20m1_pre_terra 2c7e0a4
git worktree remove /tmp/f20m1_pre_terra
```

The final `git worktree list` showed only the primary worktree.

## Measurement command and raw output

The calls intentionally reproduce the policies already used in
`tests/test_validation_run_baseline.py`: sm20 uses the default policy and sm21
uses `RunPolicy(require_ep=True)`.

```sh
PYTHONPATH=/tmp/f20m1_pre_terra python -c 'from pathlib import Path; from src.agent.execution import RunPolicy, validate_case; sm20 = validate_case(Path("case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline")); sm21 = validate_case(Path("case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e"), policy=RunPolicy(require_ep=True)); print(f"sm20 geometry_digest={sm20.geometry_digest}"); print(f"sm20 blocked={sm20.blocked}"); print(f"sm21 geometry_digest={sm21.geometry_digest}"); print(f"sm21 blocked={sm21.blocked}")'
```

```text
sm20 geometry_digest=None
sm20 blocked=True
sm21 geometry_digest=None
sm21 blocked=True
```

A diagnostic rerun with the same calls and policies produced:

```text
sm20 digest= None blocked= True summary= ['2_modelling: kernel.artifact_consistency — committed building_geometry.json does not match the deterministic rebuild from snapped correction geometry (stale/garbage artifact)', '3_split_pairing: 3_split_pairing.build — committed geometry_specs.md does not match the deterministic serializer output (stale/garbage artifact)', '4_mep: mep.load_to_zone — 38 load(s) reference an unknown zone'] reports= {'0_reading::1f_view': True, '0_reading::2f_view': True, '0_reading::3f_view': True, '0_reading::East_view': True, '0_reading::North_view': True, '0_reading::South_view': True, '0_reading::West_view': True, '0_reading::view_manifest': True, '1_correction': True, '2_modelling': False, '3_split_pairing': False, '4_mep': False, '5_intakeoutput': True, 'downstream': True}
sm21 digest= None blocked= True summary= ['2_modelling: kernel.artifact_consistency — committed building_geometry.json does not match the deterministic rebuild from snapped correction geometry (stale/garbage artifact)', '3_split_pairing: 3_split_pairing.build — committed geometry_specs.md does not match the deterministic serializer output (stale/garbage artifact)', '4_mep: mep.load_to_zone — 28 load(s) reference an unknown zone', '4_mep: mep.load_to_schedule — 14 People/Lights schedule field(s) are blank or reference a name not defined in schedule_specs — a blank People activity-level schedule is usually a field-misalignment symptom, not a missing schedule (see mep.people_field_alignment)'] reports= {'0_reading::1f_view': True, '0_reading::2f_view': True, '0_reading::East_view': True, '0_reading::North_view': True, '0_reading::South_view': True, '0_reading::West_view': True, '0_reading::view_manifest': True, '1_correction': True, '2_modelling': False, '3_split_pairing': False, '4_mep': False, '5_intakeoutput': True, 'downstream': True}
```

## r2 corrected dispatch: one non-empty F-13 verification anchor

The corrected §2.0 superseded the unusable v1 anchor and supplied the sole
non-empty anchor.  The lock was added to
`tests/test_validation_run_baseline.py`, which is the test module that holds
real on-disk run regression anchors and their `validate_case` policy calls.
It invokes the supplied F-13 run using the default policy (by omitting the
optional policy argument, equivalent to `RunPolicy()`) and compares its result
to this frozen literal:

```text
bed87c03e4c9947858f540a638ee495658fca56545f120352ef9e4003de8a5c8
```

The source comment records that it was measured at pre-F-20 commit `2c7e0a4`
and why it is frozen.  The adjacent L6 repeat-call assertion remains, but its
comment now explicitly identifies it as repeatability only, not a historical
digest lock.

The unchanged-source targeted verification was:

```sh
python -m pytest -p no:cacheprovider -q \
  tests/test_validation_run_baseline.py::test_sm21_f13_verify_geometry_digest_is_frozen_from_pre_f20 \
  tests/test_c2_b5_artifact_trust.py::test_f20_l6_legacy_no_manifest_and_v1_manifest_continue_to_be_auditable
```

```text
2 passed in 11.05s
```

## r2 neuter proof

Created a separate temporary detached worktree at `3303eee`, then made the
specified production-code mutation only there (the primary worktree's `src/`
was never edited):

```sh
git worktree add --detach /tmp/f20m1_neuter_terra 3303eee
git worktree remove --force /tmp/f20m1_neuter_terra
```

Immediately before `res.reports["2_modelling"] = krep`, the temporary copy
received this requested mutation:

```python
krep.add(
    _TRUST_CHECK_ID, source.trust_status, CheckLayer.INVARIANT,
    message=source.trust_message,
)
```

The temporary worktree also received the same new test so that pytest imported
the mutated temporary `src/` rather than the primary worktree's source.  (An
initial invocation which named the primary-worktree test by absolute path
resolved imports from the primary source and was therefore rejected as an
invalid proof; it reported 59 passed and is not used as evidence.)

The valid bound run was:

```sh
python -m pytest -p no:cacheprovider -q -n 8 \
  tests/test_validation_run_baseline.py::test_sm21_f13_verify_geometry_digest_is_frozen_from_pre_f20 \
  tests/test_c2_b5_artifact_trust.py tests/test_check_parity.py \
  > /tmp/f20m1_neuter_bound.log 2>&1; echo $? > /tmp/f20m1_neuter_bound.rc
```

Raw result:

```text
2 failed, 57 passed in 7.76s
```

The intended new lock failed exactly because the digest changed:

```text
- bed87c03e4c9947858f540a638ee495658fca56545f120352ef9e4003de8a5c8
+ 1f9cc8bbff8e03821b31d9e5b5c95c75e5607d83af1bc169f9a41d21912446d5
```

The only collateral was the known indirect `test_check_parity` failure: it
reported the extra `('2_modelling', 'correction.accepted_artifact_trust')`
check ID.  The other 57 selected tests passed.  The temporary worktree was
then forcibly removed because it intentionally contained the neuter edit;
the final worktree list contains only the primary worktree.

## Independent full acceptance

The final run used one preserved pytest session and exactly the required
direct-redirection form (no output pipeline):

```sh
python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20m1_full.log 2>&1; echo $? > /tmp/f20m1_full.rc
```

```text
rc=0
2358 passed, 10 xfailed, 209 warnings in 405.94s (0:06:45)
```

The passed count is one above the dispatch's 2357 baseline because this change
adds one unconditionally passing frozen-digest test.  The two golden baseline
directories were not modified, and `case_tests/test_baseline/gt/` was not
read.
