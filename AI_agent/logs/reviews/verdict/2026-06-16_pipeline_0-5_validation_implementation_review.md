# Review: 0-5 Validation Architecture M0-M4 Implementation

**Verdict: CHANGES REQUESTED**

Reviewed target: commit `0d267bf` (`6.15_ValidationArchM0toM4`) against `971b852`, per
`AI_agent/logs/review/request/2026-06-16_pipeline_0-5_validation_implementation_request.md`.

Existing tests are green, but the implementation is not closeable yet because the full-case
capstone has fail-open paths for missing required artifacts, and `write_reports=True` can
write an invalid `run_manifest.json`. I also found three narrower deterministic-check gaps.

## Findings

### High 1. `validate_case()` silently passes missing required stage artifacts and missing EP output

`src/agent/execution/validation_run.py:77-144` only runs a stage check if the corresponding
directory/file already exists. There is no `else` branch that records a blocking `ERROR` for a
missing required artifact in full validation scope:

- no `0_reading/` or no `*_view.json` => no S0 report
- no `1_correction/correction_geometry_snapped.json` => no S1/S2/S3 report
- no `4_mep/mep_output.json` => no S4 report
- no `5_intakeoutput/intake_output.json` => no S5 report
- no `EP/EP_run/eplusout.end` => `check_ep_baseline()` is not called, even though
  `check_ep_baseline()` itself is fail-closed when called
- missing `2_modelling/building_geometry.json` / `3_split_pairing/geometry_specs.md` is also
  allowed; S2 is rebuilt from snapped correction data and the digest falls back to `{}` / `""`
  at `src/agent/execution/validation_run.py:147-155`

Minimal reproductions:

```text
empty blocked False reports [] summary []
missing 4_mep blocked False reports [..., '5_intakeoutput', 'downstream'] summary []
missing 2/3 artifacts blocked False reports [..., '2_modelling', '4_mep', '5_intakeoutput', 'downstream'] summary [] digest True
missing EP_run blocked False reports [..., '5_intakeoutput'] summary []
missing intake blocked False reports [..., '4_mep', 'downstream'] summary []
```

This violates the requested fail-closed boundary and makes the M4 acceptance entry weaker than
the individual checks. Full-scope validation needs an explicit required-artifact table and should
emit blocking `ERROR` reports for every absent or unreadable required artifact. If a pre-EP mode is
desired, make that a separate validation scope or policy; do not infer it from a missing `.end`.

### High 2. `validate_case(write_reports=True)` fabricates/overwrites `run_manifest.json`

When `write_reports=True`, `validate_case()` calls `_build_manifest(...).save(case_dir)` at
`src/agent/execution/validation_run.py:159-160`. `_build_manifest()` then creates `StageRecord`s
with `accepted_attempt=1`, `output_hash=hash_text(rep.model_dump_json())`, and no `input_hashes`
at `src/agent/execution/validation_run.py:208-219`.

That manifest is not backed by append-only attempt directories and its hashes point to check
reports, not accepted stage artifacts. It can also overwrite a real `run_manifest.json`. This
breaks the M0 audit/resume contract: a resume consumer can see accepted pointers that do not
correspond to `<stage>/attempts/NNN/` and have no input provenance.

Recommendation: either do not write `run_manifest.json` from `validate_case`, or use
`StageRunner`/real attempt dirs and preserve/merge existing manifest state. If this is just a
validation summary, write a separate filename such as `validation_manifest.json`.

### Medium 1. Empty `Construction` objects pass the 4_mep object-semantics gate

`src/validator/checks/mep.py:91-103` only checks that every authored construction layer names a
defined material. A construction with no layers has an empty `c.fields[1:]`, so it passes
vacuously, even when that construction is listed in `used_constructions`.

Reproduction:

```text
mep = {'construction_specs': 'Construction, Default_Ext_Wall;', ...}
rep = check_mep(mep, used_constructions={'Default_Ext_Wall'})
=> rep.passed == True
```

This can let an LLM-authored but EnergyPlus-invalid construction through the 4_mep gate. Add a
blocking case for `Construction` objects with zero non-empty layers, and preferably for blank
layer fields too.

### Medium 2. `kernel.spec_self_consistency` cannot detect surfaces whose zone is not declared

`src/validator/checks/kernel.py:183-194` builds the declared zone set as:

```python
zones = set(dict.fromkeys(bg.zones)) | {s.zone for s in bg.surfaces}
```

Because every surface's own `zone` is unioned into the declared set, `if s.zone not in zones` is
false for the exact undefined-zone case the check claims to catch. Reproduction: mutate all
surfaces of one anchor zone to `NoSuchZone` while leaving `bg.zones` unchanged; `check_kernel(...)`
still passes.

Use only `bg.zones` / `zone_volumes` as the declaration source, and make `_zone_closure()` also
block when a surface zone has no matching `ZoneVolume` instead of skipping area/perimeter checks.

### Medium 3. Zero-width/zero-height reading rectangles are accepted

`src/validator/checks/reading.py:165-170` marks a rect degenerate only when both axes are below the
minimum extent:

```python
elif abs(xr[1] - xr[0]) < _MIN_EXTENT and abs(yr[1] - yr[0]) < _MIN_EXTENT:
```

A `wall_fill` / `window` rect with width `0` and height `3` therefore passes S0:

```text
zero-width rect passed True blocking []
```

For rectangle primitives, either collapsed axis makes the area degenerate. This should be `or`
or an explicit area/extent check.

## Checks That Looked Sound

- `CheckReport` policy/fact separation is clean: checks emit statuses, and `disposition()` maps
  status/layer to block/flag/info without embedding per-check policy.
- `downstream_of()` and `stages_to_run()` cover the requested transitive DAG and upstream
  contamination logic in the tested cases.
- `StageRunner.record()` preserves rejected attempts and only moves the accepted pointer when
  instructed.
- `retry_stage_draw()` keeps `judge_retry_context` out of prompt injection and only logs it
  out-of-band.
- Facade convention + mirror handling is internally consistent; the choice to distrust the legacy
  free-text axis note and rely on downstream window-on-wall reconciliation is defensible.

## Test Results

```text
python -m pytest tests/test_execution_foundation.py tests/test_checks_kernel.py -q
26 passed in 3.75s

python -m pytest -q
191 passed in 31.24s
```

The green suite does not cover the failure modes above. Suggested added regressions:

- full-scope `validate_case()` blocks on missing `0_reading`, `1_correction`, `2_modelling`,
  `3_split_pairing`, `4_mep`, `5_intakeoutput`, and missing `EP/EP_run/eplusout.end`
- `write_reports=True` does not overwrite/fabricate `run_manifest.json` unless it creates real
  append-only attempts
- empty-layer `Construction` blocks
- surface zones outside `bg.zones` block
- collapsed-axis rect blocks in S0
