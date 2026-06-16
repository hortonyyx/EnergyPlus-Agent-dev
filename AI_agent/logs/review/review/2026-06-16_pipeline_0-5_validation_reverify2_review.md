# Re-verify #2 Review: 0-5 Validation Implementation Fixes

**Verdict: CLOSEABLE**

Reviewed fix commit: `06d01a0` (`6.15_ValidationFixReverify`) on top of
`963d952`.

This round closes the remaining High-1 partial and the secondary Medium from the prior re-verify.
I did not find a new blocking issue in the touched surface.

## Findings

No blocking findings.

## Re-verify Results

### High 1 Residual: Bad/Stale 2/3 Artifacts

**PASS.** `validate_case()` now reconciles the on-disk 2/3 artifacts against the deterministic
rebuild from `1_correction/correction_geometry_snapped.json`:

- `2_modelling/building_geometry.json` is compared to `building_geometry_dict(build_geometry(...))`.
- `3_split_pairing/geometry_specs.md` is compared to `geometry_specs_markdown(...)`.
- `geometry_digest` is only computed when those consistency checks passed and the kernel report
  itself passed.

Manual reproductions now fail closed:

```text
garbage specs blocked True digest False
bad building_geom blocked True digest False
bad json blocked True digest False
```

Clean anchor still passes and produces a digest:

```text
anchor blocked False digest True summary []
bg byte identical True
specs byte identical True
```

The exact-text check is acceptable here because `pipeline.py` and `validation_run.py` now share
the same canonical helpers in `src/agent/geometry/specs.py`.

### Secondary Medium: Declared Zone With No Surfaces

**PASS.** `_zone_closure()` now iterates the union of declared zones and surface-owned zones, so a
zone present in `bg.zones` / `zone_volumes` but with no surfaces is no longer skipped.

```text
surfaceless zone passed False blocking [('kernel.zone_closure', '3 zone-closure defect(s)')]
```

### Previously Passed Items

Still looks intact:

- missing required artifacts block in full scope
- `validation_manifest.json` remains separate from `run_manifest.json`
- empty `Construction` blocks
- surface zone not declared blocks
- collapsed-axis reading rect blocks

## Verification

```text
python -m pytest tests/test_validation_run_baseline.py tests/test_checks_kernel.py -q
24 passed in 13.33s

python -m pytest -q
204 passed in 36.57s
```

Additional probes:

```text
garbage specs blocked True digest False summary ['3_split_pairing: 3_split_pairing.build — committed geometry_specs.md does not match the deterministic serializer output (stale/garbage artifact)']
bad building_geom blocked True digest False summary ['2_modelling: kernel.artifact_consistency — committed building_geometry.json does not match the deterministic rebuild from snapped correction geometry (stale/garbage artifact)']
bad json blocked True digest False summary ['2_modelling: kernel.artifact_consistency — committed building_geometry.json does not match the deterministic rebuild from snapped correction geometry (stale/garbage artifact)']
anchor blocked False digest True summary []
bg byte identical True
specs byte identical True
```
