# Two-Step Skill Migration Review

Date: 2026-05-25
Reviewer: Codex
Scope: Compare `skills/energyplus_mcp/` single-step skill library against `skills/energyplus_mcp_twostep/` and verify whether the two-step skills migrated the old skill capabilities completely.

## Verdict

Not fully migrated yet.

The two-step skill has the right architecture and covers most core constraints from the old skill: global world coordinates, shared footprint, explicit zone enumeration, strict naming, no template writing, schedule completeness, absolute window z, window vertex synthesis, SimpleGlazing standalone construction, and InterZone single-construction handling.

However, several old hard constraints that previously prevented fatal downstream errors or silent geometry drift are missing, weakened, or made too case-specific in the new two-step docs.

## Findings

### 1. High — `phase2_rules.md` still contains sm_20 case-specific hardcoding

Evidence:
- `skills/energyplus_mcp_twostep/phase2_rules.md` Step 1 hardcodes `Smalloffice_20`, 3 floors, and 360 m2.
- Step 2 hardcodes Shenzhen / `Shenzhen.epw`.
- The WWR self-check uses sm_20-specific window counts and facade patterns.

Risk:
For a new case, phase 2 may copy sm_20 metadata or validation expectations instead of deriving them from `testdata_prompt.json` and vector JSONs. This weakens generalization, especially for the planned异图 POC.

Expected migration:
Old skill behavior was generic: read building/site/floor/window facts from the input package, only using office defaults where information is genuinely missing.

Recommended fix:
Replace sm_20 values with generic derivation rules and move the sm_20 counts to an example block explicitly labelled "example only, not reusable".

### 2. High — Cross-floor split-pairing rule lost required sub-range enumeration

Evidence:
- Old `intake_output_contract.md` required that when adjacent floors have misaligned internal partitions, InterZone floor/ceiling surfaces must be split at the union of breakpoints, with each piece listing exact x/y sub-range and paired zone.
- New `phase2_rules.md` requires pair enumeration, but the example only lists zone-to-zone pairs and does not require sub-ranges.

Risk:
This can reintroduce the previous EnergyPlus fatal class where `RoofCeiling:Detailed` or InterZone surfaces reference an outside boundary surface that cannot be found. It is especially risky when upper and lower floor layouts differ.

Expected migration:
Phase 2 should preserve the old rule verbatim in spirit: pair every split piece, not just every zone.

Recommended fix:
Add a hard subsection to `phase2_rules.md` Step 4:
- detect partition misalignment between stacked floors
- compute union of x/y breakpoints
- split InterZone floor/ceiling surfaces by sub-range
- enumerate each source zone, surface type, sub-range, paired zone, paired surface, and construction

### 3. Medium — Fenestration output contract is less auditable than the old version

Evidence:
- Old `intake_output_contract.md` required each window record to include parent zone, facade direction, parent wall side, facade plane, horizontal span axis/range, absolute `z_min/z_max`, and construction.
- New `phase2_rules.md` requires name, parent surface, construction, and CCW vertices.

Risk:
Vertices may be enough for downstream geometry, but the omitted fields make review and diffing harder. They also make it harder to catch facade-axis flips, parent-wall mismatches, and incorrect z-height calculations before IDF export.

Expected migration:
The two-step version should keep both: explicit vertices for downstream execution and semantic/audit fields for human and automated checks.

Recommended fix:
Restore the old one-record-per-window checklist inside `phase2_rules.md` Step 6, while keeping the new `parent_surface_name` and vertex requirement.

### 4. Medium — Supplementary drawings and blank-facade semantics are not fully connected to phase 2

Evidence:
- Old skill explicitly handled optional supplementary drawings and blank facade rules.
- New phase 1 prompt mentions `supp_plan.png`, but the phase 2 prompt/rules required inputs only list normal plans plus four elevations.
- Blank facades are mostly covered implicitly by "no window strokes", but the old rule also covered empty/missing paths and image-present-but-no-blue-window cases.

Risk:
If a new case relies on a supplement for stair indexing, sections, or local geometry clarification, phase 2 may not consume it. If a facade path is missing or present but blank, the model may not explicitly record zero windows with the same discipline as the old skill.

Recommended fix:
Add optional `section` / `supplementary` JSON handling to phase 2 inputs and require phase 2 to explicitly state zero windows for blank or missing facades.

### 5. Low — Phase 1 schema has a wall-thickness contradiction

Evidence:
- `phase1_vector_schema.md` repeatedly says plan wall `thickness_m` is always `null`.
- The polyline example uses `thickness_m: 0.30`.

Risk:
The model may start estimating wall thickness during phase 1, violating the "perception only, no simulation thickness" discipline.

Recommended fix:
Change the polyline example thickness to `null`.

## Migration Coverage Snapshot

Covered:
- Two-step error-budget split: image perception vs text-only topology reasoning
- Global coordinate system and facade local-to-world translation
- Shared-footprint invariant and unsupported-geometry warning
- Explicit per-floor zone enumeration
- Special-space preservation: corridor, stair, lift, WC, lobby, storage/service
- Corridor collapse into one zone where appropriate
- Naming character restrictions and exact cross-field reuse
- No placeholders, no templates, no "typical floor" shorthand
- Schedule completeness, including people activity-level schedule
- Window absolute world z and CHKSBS prevention
- Window CCW vertex synthesis
- SimpleGlazing standalone construction
- InterZone single construction via `Cons_InterFloor`

Incomplete or weakened:
- Generic new-case derivation, due to sm_20 hardcoding
- Cross-floor split-pairing sub-range enumeration
- Full fenestration audit record
- Supplementary drawing consumption in phase 2
- Explicit blank/missing facade handling
- Phase 1 wall-thickness example consistency

## Recommended Priority

1. Remove sm_20 hardcoding from `phase2_rules.md`.
2. Restore cross-floor split-pairing with explicit sub-ranges.
3. Restore full fenestration per-window audit fields.
4. Add phase 2 handling for supplementary drawings and blank/missing facades.
5. Fix the phase 1 schema `thickness_m` example.

After these are patched, the two-step skill should be functionally equivalent to the old skill and better positioned for the upcoming generalized two-step baseline.
