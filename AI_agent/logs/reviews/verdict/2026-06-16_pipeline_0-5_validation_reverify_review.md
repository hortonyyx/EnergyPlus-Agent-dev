# Re-verify Review: 0-5 Validation Implementation Fixes

**Verdict: CHANGES REQUESTED**

Reviewed fix commit: `963d952` (`6.15_ValidationFixCodexReview`) on top of
`0d267bf`.

The original five findings are mostly addressed, and the new regression tests pass. However,
High 1 is only partially fixed: `validate_case()` now blocks on missing required artifacts, but
still passes when required 2/3 artifacts exist with bad/stale contents. Because it also computes a
geometry approval digest from those bad artifacts paired with a check report generated from a
different in-memory geometry, this is not closeable yet.

## Remaining Finding

### High. Existing but bad 2/3 artifacts still pass full-scope validation

`src/agent/execution/validation_run.py:89-102` now checks that
`2_modelling/building_geometry.json` and `3_split_pairing/geometry_specs.md` exist, but the later
kernel check is still rebuilt from `1_correction/correction_geometry_snapped.json` at
`src/agent/execution/validation_run.py:119-144`. The on-disk 2/3 artifacts are not validated for
semantic consistency. Then `src/agent/execution/validation_run.py:183-190` computes
`geometry_digest` from those on-disk files and the rebuilt-geometry check report, even if the files
are stale or garbage.

Reproductions on a copied `sm20_anchor`:

```text
geometry_specs.md = "garbage geometry specs, not the generated surface graph"
=> garbage specs blocked False summary [] digest True

building_geometry.json zones = ["BogusZone"], surfaces = []
=> bad building_geometry blocked False summary [] digest True
```

This leaves the M4 capstone fail-open for bad 2/3 outputs and can bind an approval digest to
unchecked geometry/spec bytes. The required-artifact table fixed "missing file"; it did not yet
fix "bad stage artifact".

Suggested fix:

- Load and validate `2_modelling/building_geometry.json` as the checked S2 artifact, or compare it
  canonically against the `build_geometry(snapped)` result and block on drift.
- Recompute `geometry_specs.md` from `serialize_geometry(bg)` and block if the committed file does
  not match the deterministic serializer output, or parse/check the file directly if exact text
  matching is intentionally too strict.
- Only compute `geometry_digest` after those real on-disk 2/3 artifacts have passed the consistency
  check. The digest should never combine unchecked artifact bytes with a report from a different
  source of truth.

## Secondary Gap

### Medium. `kernel.zone_closure` still passes declared zones with no surfaces

The Medium 2 fix catches surfaces that point to an undeclared zone, which closes the original
reproduction. But `_zone_closure()` still iterates only `_by_zone(bg)` at
`src/validator/checks/kernel.py:94`, so a declared zone in `bg.zones` / `bg.zone_volumes` with no
surfaces at all is never checked.

Minimal reproduction:

```text
BuildingGeometry(zones=["Z1"], surfaces=[], zone_volumes=[ZoneVolume("Z1", ...)])
=> zone with no surfaces passed True blocking []
```

This is less urgent than the M4 artifact issue because the current kernel normally emits surfaces
from `build_geometry()`, but the check's stated contract is "every zone has a floor, top, and
walls". Iterate `set(polys) | set(_by_zone(bg))` so declared-but-surface-less zones block.

## Original Findings Status

- High 1 missing-artifact fail-open: **PARTIAL**. Missing required artifacts now block; bad/stale
  2/3 artifacts still pass.
- High 2 `run_manifest.json` overwrite/fabrication: **PASS**. `write_reports=True` now writes
  `validation_manifest.json`, and an existing `run_manifest.json` is preserved.
- Medium 1 empty `Construction`: **PASS**. Empty construction now blocks via
  `mep.construction_to_material`.
- Medium 2 surface zone not declared: **PASS for original repro**, with the secondary declared-zone
  gap above.
- Medium 3 collapsed rect axis: **PASS**. A one-axis-collapsed rect now blocks.

## Verification

```text
python -m pytest tests/test_validation_run_baseline.py tests/test_checks_mep_assembly.py tests/test_checks_kernel.py tests/test_checks_reading_correction.py -q
53 passed in 11.49s

python -m pytest -q
201 passed in 38.42s
```

Manual repros:

```text
empty blocked True reports ['0_reading', '1_correction', '2_modelling', '3_split_pairing', '4_mep', '5_intakeoutput'] summary_len 6
anchor blocked False reports ['0_reading::1f_view', ..., 'downstream'] digest True
missing 4_mep blocked True summary ['4_mep: 4_mep.build — required artifact missing: 4_mep/mep_output.json']
missing geometry blocked True digest None summary ['2_modelling: 2_modelling.build — required artifact missing: 2_modelling/building_geometry.json']
missing intake blocked True summary ['5_intakeoutput: 5_intakeoutput.build — required artifact missing: 5_intakeoutput/intake_output.json']
missing EP default blocked False has_downstream False
missing EP required blocked True summary ['downstream: downstream.build — required artifact missing: EP/EP_run/eplusout.end']
run_manifest {"case":"sm20_anchor","stages":{}}
validation_manifest_exists True
empty construction passed False
undefined zone passed False blocking_ids ['kernel.zone_closure', 'kernel.spec_self_consistency']
collapsed rect passed False blocking_ids ['reading.nondegenerate_geometry']
```
