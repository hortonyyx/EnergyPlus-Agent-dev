# M3 provenance execution log

Date: 2026-07-06

## Inputs read

- `AI_agent/logs/reviews/request/2026-07-06_audit_fix_m3_provenance_proposal.md`
- `AI_agent/logs/reviews/verdict/2026-07-06_audit_fix_m3_review.md`

Final adjudication followed: no timestamp field; include reading/correction/config hashes; git anchored at project root; keep provenance best-effort.

## Backups

- `backup/scripts_history/2026-07-06_m3_provenance/record_baseline.py`
- `backup/scripts_history/2026-07-06_m3_provenance/report_assembly.py`
- `backup/src_history/2026-07-06_m3_provenance/policy.py`

## Changes

- `scripts/tool_scripts/record_baseline.py`
  - Added deterministic `_hash_directory_contents(root)` helper using sorted relative paths and `relpath + NUL + bytes`, excluding `__pycache__` and `.pyc`.
  - Added provenance collection with `git -C PROJECT_ROOT`, capped dirty paths (`cap=50`) plus total count.
  - Added hashes for:
    - `skills/intake_pipeline/`
    - `src/agent/reading/`
    - `src/agent/correction/`
    - `src/configs/correction.yaml`
  - Added best-effort `collection_error` when git or hash collection fails.
  - Added comment that future exact golden re-record comparisons must normalize/exclude environment-dependent provenance fields.
  - Persisted top-level `baseline["provenance"]`.
- `scripts/tool_scripts/report_assembly.py`
  - Added one-line provenance summary in the existing `GEN:model_config` section with short git/hash values and dirty marker.
- `src/agent/execution/policy.py`
  - Removed zero-consumer `RunPolicy.reading_runner_ladder` and its now-unused `Field` import.
- `tests/test_provenance_baseline.py`
  - Added tests for directory hash determinism, single-byte sensitivity, baseline/report provenance output, and git-failure soft degradation.

## Compatibility note

The review found no local old `_run` artifacts serializing `RunPolicy`; deletion of `reading_runner_ladder` is locally compatible. External serialized policy payloads containing that field would fail because `RunPolicy` remains `extra="forbid"`.

## Tests

Command:

```bash
/opt/venv/bin/python -m pytest tests/test_provenance_baseline.py tests/test_orchestrate_baseline.py
```

Result:

- `35 passed`
- `1 xfailed`
- `91 warnings` (existing run-config/report placeholder warning pattern in these tests)

No pipeline or EnergyPlus runs were executed.
