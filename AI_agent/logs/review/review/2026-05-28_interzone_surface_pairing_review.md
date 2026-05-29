# InterZone Surface Pairing Review

Date: 2026-05-28
Reviewer: Codex
Scope: Review how the current pipeline creates EnergyPlus InterZone `BuildingSurface:Detailed` floor/ceiling and wall pairs, with emphasis on cross-floor split-pairing when adjacent floors have different partitions.

## Verdict

The passing IDFs inspected are valid with respect to EnergyPlus InterZone surface pairing, but the pipeline still relies too much on prompt compliance and the surface agent's geometry reasoning.

The good news: `smalloffice_16_newarch` and `smalloffice_21` outputs are not "fake pass" cases. Their `Surface` boundary objects are split into one-to-one reciprocal pairs, with matching areas and opposite normals.

The risk: this correctness is not enforced by a deterministic post-surface validator. Current rules ask phase 2 / intake to enumerate split-pairing, and `surface_agent` creates the split surfaces, but the converter mostly writes whatever it receives into IDF. If a future model omits a split piece or points one surface at the wrong partner, EnergyPlus may catch some cases late, but the pipeline has no early, explicit gate for this contract.

## Findings

### 1. High — InterZone split-pairing has no deterministic validation gate

Evidence:
- `src/agent/nodes/surface.py` asks the surface agent to use `zone_specs` and `surface_specs` to create `BuildingSurface:Detailed` objects.
- `src/converters/surface_converter.py` only validates each surface object shape and writes it into the IDF. It does not verify the whole graph of `Outside Boundary Condition = Surface` references.
- `src/validator/data_model.py` explicitly loosened zone geometry closure because EnergyPlus accepts split surfaces with T-vertices, but it does not replace that with a full InterZone pair validator.

Risk:
Future cases can silently depend on the LLM getting every reciprocal pair right. Missing or inconsistent pairs can produce late EnergyPlus fatals such as missing outside boundary surfaces, area mismatch warnings, or physically wrong interzone heat transfer.

Recommended fix:
Add a deterministic `validate_interzone_surface_pairs` check after the surface phase and before IDF export / simulation. It should fail fast when:
- a `Surface` boundary target is missing
- the target is not also `Surface`
- the target does not point back to the source
- any surface is referenced by more than one incoming pair
- paired areas differ beyond tolerance
- paired normals are not opposite
- paired floor/ceiling surfaces do not lie on the same z plane

### 2. High — Cross-floor coverage is specified in prompt rules but not mechanically checked

Evidence:
- `skills/energyplus_mcp_twostep/phase2/rules.md` now requires misaligned stacked floors to split at the union of x/y breakpoints and enumerate one pair per split piece.
- `skills/energyplus_mcp/intake_output_contract.md` contains the same load-bearing rule.
- The generated IDFs can be audited as pairwise-correct, but there is no geometry-level check that split pieces cover the full overlapping footprint between adjacent floors without holes or overlaps.

Risk:
A model could create reciprocal pairs that are individually valid but collectively incomplete. EnergyPlus may run, yet part of a floor/ceiling boundary could be missing, duplicated, or treated as roof/ground/adiabatic by mistake.

Recommended fix:
In addition to pair checks, add a stacked-footprint coverage check:
- derive each zone footprint polygon from floor/ceiling vertices
- for every adjacent floor pair, intersect upper and lower zone footprints
- verify every nonzero intersection has exactly one floor/ceiling pair
- verify the paired surface area equals the intersection area
- flag any unpaired overlap or duplicated overlap

### 3. Medium — The historical `smalloffice_16_newarch` pass depended on surface-agent inference

Evidence:
- `test_data/SmallOffice/smalloffice_16_newarch/output/intake_output.json` says the Floor 1 north band sits below a differently partitioned Floor 2 north band and instructs the system to use splitting while keeping one-to-one references.
- That `surface_specs` text still includes soft wording: "use the splitting that the geometry agent prefers".
- The final IDF is correct, but the split pieces were produced by the surface agent, not by a deterministic geometry algorithm.

Risk:
This is acceptable as a proof of capability, but not enough as a robust production contract. Another model or a more complex floor plan may choose a different split naming scheme or omit sub-ranges unless the current hard rules and validation gate both hold.

Recommended fix:
Keep the prompt rule, but make the downstream contract executable. The surface phase can still synthesize surfaces, but its output should be rejected unless the deterministic validator confirms the pair graph and coverage.

### 4. Medium — EnergyPlus pass/fail alone is too late and too coarse for this issue

Evidence:
- `smalloffice_16/output/smalloffice_16.idf` does not test InterZone pairing at all: its internal floors/walls are mostly `Adiabatic`, so EnergyPlus has no surface-pair graph to validate.
- `smalloffice_16_newarch/output/temp_20260507_154141_glazingfix.idf` does test InterZone pairing and passes cleanly.
- `smalloffice_21/output/temp_20260528_082631.idf` also passes the local InterZone pair audit.

Risk:
If "EnergyPlus completed" is the only acceptance signal, the pipeline can miss the difference between:
- a real InterZone model with correct reciprocal surface pairs
- an adiabatic simplification that avoids the problem entirely
- a pairwise-valid but coverage-incomplete geometry

Recommended fix:
Record surface-pair audit counts in baseline notes alongside EnergyPlus status:
- total `BuildingSurface:Detailed`
- counts by outside boundary condition
- number of reciprocal InterZone pairs
- number of pair validation issues
- number of coverage validation issues

## Checks Performed

### `smalloffice_16_newarch` PASS IDF

File:
`test_data/SmallOffice/smalloffice_16_newarch/output/temp_20260507_154141_glazingfix.idf`

Audit result:
```text
BuildingSurface:Detailed total: 135
Boundary condition counts: Outdoors 38 / Surface 90 / Ground 7
Surface boundary objects: 90
Reciprocal pairs: 45
Issues: 0
```

Interpretation:
This IDF is a normal EnergyPlus InterZone model, not an adiabatic bypass. It has one-to-one reciprocal surface pairs.

### `smalloffice_21` PASS IDFs

Files:
- `test_data/SmallOffice_TwoStep/smalloffice_21/output/temp_20260528_082631.idf`
- `test_data/SmallOffice_TwoStep/smalloffice_21/output_deepseek/temp_20260528_082631.idf`
- `test_data/SmallOffice_TwoStep/smalloffice_21/output_opus/temp_20260528_095528.idf`

Audit result:
```text
BuildingSurface:Detailed total: 100
Boundary condition counts: Outdoors 31 / Surface 62 / Ground 7
Surface boundary objects: 62
Reciprocal pairs: 31
Issues: 0
```

Interpretation:
The current two-step artifacts inspected also satisfy reciprocal InterZone pairing.

### Original `smalloffice_16`

File:
`test_data/SmallOffice/smalloffice_16/output/smalloffice_16.idf`

Audit result:
```text
Boundary condition counts: Outdoors 38 / Adiabatic 69 / Ground 7
Surface boundary objects: 0
```

Interpretation:
This file does not exercise InterZone surface pairing. It avoids the issue by using adiabatic internal boundaries, and in the current workspace it also fails EnergyPlus because window constructions are opaque.

## Recommended Priority

1. Add deterministic reciprocal InterZone pair validation after `surface_agent`.
2. Add stacked-floor coverage validation for misaligned floor partitions.
3. Include pair/coverage audit summaries in baseline run notes.
4. Keep current phase2 and intake hard rules, but treat them as generation guidance rather than the only enforcement.
