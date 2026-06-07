# Correction A0 Contract Review

Date: 2026-06-07
Reviewer: Codex
Scope: Review of `skills/energyplus_mcp_twostep/phase2/PartA-correction/A0_contract.md` and the local `README.md` staging contract.

## Verdict

**Conditionally accept the A0 shape, but do not freeze it as the spine until the schema fixes below land.**

The document correctly implements the previous review's core request: A0 is no longer only a constants table; it now defines evidence, audit event classes, conflict types, tolerance names, method profiles, upstream input expectations, and validation. That is the right spine for A1-min + A2.

However, two issues are structural rather than editorial:

1. A0's validation schema currently talks about `zones` before zoning exists in the pipeline.
2. The evidence model mixes numeric evidence, topological identity evidence, and prior/semantic evidence under one authority ladder, then omits `inferred_topology` from the ladder.

My recommendation: patch A0 in place, then proceed to A1-min + A2. No need to add an A5 if A0 absorbs the fixes.

## Findings

### 1. High - Validation schema uses downstream `zones` before PartA produces them

Evidence:
- `README.md` places PartA before zoning: `PartA correction -> zoning -> geometry build`.
- `A0_contract.md` says validation follows `A2-apply`, but the schema checks `union(zones) vs floor footprint`, pairwise zone overlap, and `wwr_residuals`.

Risk:
At the A2 validation point, the system has corrected floor footprint, room cells / source cells, facade segments, surfaces, and window anchors. It does not yet have final `thermal_zones`, especially under `perimeter_core`, where zones are created by the later zonification sidecar. If A0 calls these objects `zones`, A1/A2 may either invent a pre-zoning zone concept or silently couple correction validation to the downstream thermal-zone artifact.

Recommended action:
Rename and split the validation targets:

- `floor_footprint_coverage`: corrected floor boundary validity.
- `room_cell_coverage`: only when source room cells are required by the selected profile.
- `facade_segment_coverage`: exterior boundary attribution and orientation coverage.
- `window_anchor_validation`: parent facade/surface containment and WWR attribution.
- `thermal_zone_coverage`: reserved for the later zonification artifact, not PartA A2 validation.

Keep the same hard/soft logic, but make it profile-aware: `room_identity` and `use_grouped_rooms` require room-cell closure; `perimeter_core` requires envelope/facade/window correctness and can tolerate incomplete internal partitions except declared exceptions.

### 2. High - Evidence authority needs claim-type scoping, not one global ladder

Evidence:
- §1.1 ranks `estimated_stroke` above `inferred_topology`.
- §1.3's priority ladder omits `inferred_topology` entirely.
- A2 depends on evidence that two strokes are the same intended wall/axis, not merely on nearby coordinates.

Assessment:
Putting `inferred_topology` below `estimated_stroke` is reasonable only when the claim is "what is this coordinate?" It is not reasonable when the claim is "are these two edges the same intended boundary?", "does this room close?", or "is this a shared wall?" In those cases, topology is the evidence being evaluated, not a worse coordinate estimate.

Recommended action:
Add `claim_type` or `quantity_kind` to evidence items, with separate resolution ladders:

- numeric dimension / coordinate claims: direct measurement > dimension chain > stroke estimate > prior.
- topology / identity claims: direct annotation or dimensioned boundary > consistent enclosure / adjacency inference > stroke proximity > prior.
- semantic claims: OCR / label evidence > repeated layout pattern > prior.

This preserves grade/confidence independence while preventing A2 from merging axes solely because coordinates are close.

### 3. Medium - Audit entries are close, but not yet reproducible enough

Evidence:
- `corrections[]` has `target`, `rule_id`, `source_ids`, values, threshold, delta, evidence grade, confidence, topology flag, and prior id.
- `conflicts[]` has candidates and fallback action.

Missing for reproduction:

- `stage` / producing document: `A1`, `A2-detect`, `A3-resolve`, `A2-apply`.
- `method_profile`: `room_identity`, `use_grouped_rooms`, or `perimeter_core`.
- stable locator: `floor_id`, `entity_type`, `entity_id`, optional `parent_id`.
- coordinate frame / units for geometry values.
- `tolerance_name` plus applied numeric value and unit; `threshold` alone is too loose.
- `value_type`: scalar, point, line, polygon, ratio, area, facade extent.
- for conflicts, candidate `source_ids[]`, not only singular `source_id`, because a dimension-chain candidate is compound.

Recommended action:
Keep the compact schema, but add these fields as required unless explicitly `null`. This lets A1/A2/A3 reuse the same event envelope without inventing per-doc audit metadata.

### 4. Medium - Add a seventh conflict type for reference / identity ambiguity

The six conflict types are a good start, but they do not cleanly cover the most important A1/A2 escalation path from the previous review: "same intended wall/axis or legitimate offset?"

Recommended addition:

```text
reference_or_identity_ambiguity
```

Use it for:

- plan origin / local-to-world transform conflicts;
- unknown wall side or missing wall-thickness basis for centerline conversion;
- same-floor or cross-floor axis identity ambiguity that is not just numeric jitter;
- cases where coordinate proximity and semantic/topological evidence disagree.

`cross_floor_axis_jitter` can remain as the numeric subtype; this new type is the higher-level "what object is this?" conflict.

### 5. Medium - Pending tolerance values are acceptable only as registry slots, not executable constants

The tolerance class split is right: absolute coordinate/grid tolerances should not be mixed with relative area/WWR tolerances.

The risk is that `*(pending)*` values in a "current version spec" can leak into A1/A2 as usable constants. For A0 to be the spine, each tolerance should carry:

- `name`;
- `value`;
- `unit`;
- `status`: `calibrated | provisional | disabled`;
- `source_or_basis`;
- `profiles`;
- `hard_fail_or_warn`.

If a value is still pending, mark it `disabled` and require the consuming rule to emit `unsupported` or skip that path. Once the retrieval package is accepted, backfill `SNAP_GRID`, `MIN_EDGE_LENGTH`, `GAP_CLOSE_THRESHOLD`, `AXIS_JITTER_TOL`, and `PERIMETER_DEPTH` with explicit basis notes.

### 6. Medium - `use_grouped_rooms` needs stronger A3/A4 than the current profile note implies

The profile table is good, but the sentence "A3/A4 full force only under `room_identity`" under-specifies `use_grouped_rooms`.

For `use_grouped_rooms`, A3/A4 are not as strict about exact wall thickness as `room_identity`, but they are still central for:

- room-cell closure;
- adjacency graph correctness;
- use/schedule/load/HVAC semantic grouping;
- preserving exception spaces like shafts, stairs, toilets, equipment rooms, and high-load rooms.

Recommended action:
Use three levels:

- `perimeter_core`: conservative A3/A4, envelope/facade/window first.
- `use_grouped_rooms`: full semantic grouping and room-cell closure; relaxed wall-thickness precision.
- `room_identity`: full geometry fidelity for every internal boundary.

### 7. Medium - Legacy provenance degradation needs an explicit mode and stop conditions

The degradation direction is right: legacy JSON can run with downgraded confidence and more conflicts. But as written, it may be too permissive.

Recommended action:
Add:

- `provenance_mode`: `full | partial | legacy`;
- `provenance_coverage`: per evidence class, e.g. dimensions, strokes, labels, facades, windows;
- profile-specific stop conditions.

Suggested stop conditions:

- `room_identity`: fail or mark unsupported when internal wall provenance is too sparse.
- `use_grouped_rooms`: fail or mark unsupported when room-cell closure / labels are too sparse.
- `perimeter_core`: may continue if exterior footprint, floor height, facade orientation, and window/WWR evidence pass minimum coverage.

This keeps legacy support without letting low-provenance input quietly become high-confidence correction output.

### 8. Low - Hard/soft validation split is directionally right; add invalid geometry and attribution checks

The hard failures are mostly right: overlaps, undeclared holes, degenerate edges, failed containment. Add a few explicit checks so downstream docs do not reinvent them:

- invalid / self-intersecting polygons;
- geometry outside the declared footprint;
- duplicate or missing entity ids;
- source-to-output attribution completeness;
- facade orientation / parent-surface mapping;
- floor-height / z-stack consistency;
- unsupported count by severity.

Also add a top-level validation outcome:

```text
status: pass | pass_with_warnings | fail
```

Without this, downstream callers have to infer gate status from a loose list of residuals and flags.

## Direct Responses To The 8 Focus Questions

1. **A0 as spine**: Almost. The scope is right, but freeze only after fixing validation target scope, claim-type evidence, reproducible audit envelope, and legacy/profile stop conditions.

2. **Evidence model**: Six grades are usable, and confidence should stay decoupled from grade. `inferred_topology` should not be globally below `estimated_stroke`; its authority depends on claim type. The ladder must include it or split ladders by claim type.

3. **Audit event classes**: The four classes are clean. `corrections[]` / `conflicts[]` / `unsupported[]` are the right containers, but entries need stage/profile/entity locator/unit/tolerance metadata to be reproducible.

4. **Conflict types**: The six cover many numeric conflicts. Add `reference_or_identity_ambiguity` for frame, wall-side, wall/axis identity, and same-vs-different object ambiguity.

5. **Tolerance classes**: Absolute-grid vs relative-error split is correct. Pending constants are acceptable only as named slots; executable rules must consume calibrated/provisional-with-basis values or treat the path as disabled.

6. **Method profiles**: The three profiles are right. A1/A2 all-profile applicability is right. A3/A4 should be conservative under `perimeter_core`, semantic/closure-heavy under `use_grouped_rooms`, and fully strict under `room_identity`.

7. **Upstream input + degradation**: Directionally right but too loose. Add `provenance_mode`, evidence coverage metrics, and profile-specific fail/unsupported conditions.

8. **Validation schema + fail/continue**: Hard vs relative-tolerance split is right, but the schema must validate PartA artifacts, not downstream `thermal_zones`. Add invalid geometry, outside-footprint, id uniqueness, attribution, facade mapping, and z-stack checks.

## Missing Field / Concept Checklist

- `claim_type` / `quantity_kind` on evidence items.
- Evidence item schema: `id`, `grade`, `confidence`, `source_kind`, `source_ids`, `floor_id`, `entity_id`, `coordinate_frame`, `unit`, optional source bbox/span.
- Audit envelope: `stage`, `method_profile`, `entity_type`, `entity_id`, `floor_id`, `parent_id`.
- Applied tolerance metadata: `tolerance_name`, `tolerance_value`, `unit`, `status`, `source_or_basis`.
- `reference_or_identity_ambiguity` conflict type.
- `provenance_mode` and `provenance_coverage`.
- Profile-specific required evidence / stop conditions.
- PartA validation target names separated from downstream thermal-zone validation.
- Top-level validation `status`.

## Recommended Minimal Patch Before A1-min + A2

1. Replace `zones` in §7 with profile-aware PartA validation targets.
2. Add `claim_type` and separate authority ladders for numeric, topology/identity, and semantic claims.
3. Add the audit envelope fields listed above.
4. Add `reference_or_identity_ambiguity`.
5. Convert pending tolerance text into a tolerance registry table with `status` and `source_or_basis`.
6. Change method-profile wording so `use_grouped_rooms` gets strong semantic grouping and closure logic.

After those edits, A0 is suitable to serve as the A1-A4 spine.

## Sources Checked

Internal:

- `AI_agent/logs/review/request/2026-06-07_correction_A0_contract_request.md`
- `skills/energyplus_mcp_twostep/phase2/PartA-correction/A0_contract.md`
- `skills/energyplus_mcp_twostep/phase2/PartA-correction/README.md`
- `AI_agent/logs/review/review/2026-06-07_partA_correction_constraint_set_review.md`
- `AI_agent/capability/recognition_modeling_capability.md`
- `AI_agent/logs/review/review/2026-06-07_zonification_approach_review.md`

No external research was needed for this document review.
