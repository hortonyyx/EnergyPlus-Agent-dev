# F-20 cross-review follow-up · terra execution log

- Date: 2026-08-10
- Scope read: request `2026-08-10_f20_crossreview_followup_terra.md` and sol
  verdict `2026-08-10_f20_crossreview_sol.md`.
- Boundary: production change is confined to `_resolve_correction_source` in
  `src/agent/execution/validation_run.py`, for MINOR-1 exception-to-trust-row
  mapping only.  No `stage_runner.py`, loader contract, golden baseline, or
  F13 anchor changes.  No git add/commit/branch operation.

## Changes

1. MAJOR-1 lock: added a V2 ledger-rejection test with a buildable
   legacy-schema stage-root fixture.  It self-proves clean `PASS` plus a
   nonempty digest and a successful approval, corrupts accepted `output.json`
   to provoke a hash rejection, then requires `FAIL`, no digest, and no new
   geometry approval.  The legacy fixture avoids the v3-under-legacy FAIL wall
   that masked the former L2/L3 coverage.
2. MINOR-1: resolver now maps manifest-dispatch and legacy-stage-root payload
   exceptions into a trust row: `ValueError` to `FAIL`, unexpected `Exception`
   to `ERROR`.  Added self-proving locks for a manifest dispatcher sentinel and
   malformed legacy payload.
3. NIT-1: replaced L5's in-memory manifest record self-comparison with a
   frozen on-disk manifest-byte comparison; replaced the two cited
   `FAIL => != NOT_APPLICABLE` implications with checks of the trust reason.

## Neuter evidence

All mutations were in distinct `/tmp` snapshot roots; each snapshot copied
`src/`, `tests/`, `data/` (including `data/dependencies/Energy+.idd`), project
metadata, and used a read-only `case_tests` symlink.  No golden `gt` directory
was read.

| Lock | Mutation | Result | Collateral |
| --- | --- | --- | --- |
| MAJOR-1 | V2 accepted-loader `except ValueError` returns `_resolve_legacy_stage_root(snapped, reason=...)` | exactly `test_f20_major1_v2_rejection_never_falls_back_to_buildable_legacy_stage_root` red (`FAIL` expected, got `NOT_APPLICABLE`) | none |
| MINOR-1 manifest | manifest-dispatch unexpected-exception mapping changed to re-raise | exactly `test_f20_minor1_manifest_dispatch_exception_is_reported_as_error` red (sentinel escaped) | none |
| MINOR-1 legacy payload | legacy-stage-root `ValueError` mapping changed to re-raise | exactly `test_f20_minor1_malformed_legacy_payload_is_reported_as_fail` red (`JSONDecodeError` escaped) | none |

The MAJOR-1 fail-open mutant is therefore caught by the new lock.

## Verification

- Focused file: `60 passed in 13.76s`.
- Three-file directed set: `72 passed, 8 xfailed in 19.29s` (69 prior tests
  plus the three new locks).
- Required independent full run:

  ```bash
  python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20fu_full.log 2>&1; echo $? > /tmp/f20fu_full.rc
  ```

  Both completion artifacts exist.  `/tmp/f20fu_full.rc` is `0`; summary is
  `2361 passed, 10 xfailed, 209 warnings in 410.41s (0:06:50)`.

## Uncertainty

None identified within the assigned scope.  The full count rose from the stated
2358-pass baseline by exactly the three newly added locks.
