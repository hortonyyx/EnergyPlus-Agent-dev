# Correction A1/A2 Review And A0 Re-verify

Date: 2026-06-07
Reviewer: Codex
Scope: Review of `A1_coordinate_normalization.md`, `A2_regularization.md`, and re-verification of the revised `A0_contract.md`.

## Verdict

**A0 re-verify:** closeable. The six requested A0 patches are substantially implemented. One tolerance-registry ambiguity remains because `AXIS_JITTER_TOL`, `GAP_CLOSE_THRESHOLD`, and `SNAP_GRID` now overlap in a way that A2 can interpret inconsistently.

**A1 + A2:** conditionally accept, but do not mark final until two blocking edits land:

1. A1 must not let a wall-thickness prior act inside A1 as a self-acting correction path.
2. A2 must make the threshold precedence and snap / quantization order unambiguous.

After those edits, the A1/A2 split is sound and the batch can proceed to A4 stub + A3.

## Findings

### 1. High - A1 allows prior wall thickness to bypass the A3/A4 arbitration path

Evidence:
- `README.md` says runtime is `A1 -> A2-detect -> A3-resolve (+A4) -> A2-apply -> validate`, and A4 is advisory, never self-acting.
- `A1_coordinate_normalization.md` says a prior wall thickness from A4 may be used when measurement is absent, logged with `prior_id`.

Risk:
A1 is supposed to be deterministic over typed evidence: frame conversion, known centerline shifts, and z-stack reconciliation. If A1 can pull an A4 prior directly when measured thickness is absent, it becomes a completion/arbitration step. That reopens the exact "prior silently fixes geometry" risk A0/A3 were meant to isolate.

Recommended action:
Change A1's rule to:

```text
A1 may consume a wall-thickness value only if it is measured or already resolved by A3.
If thickness is absent and only an A4 prior could fill it, A1 emits
reference_or_identity_ambiguity and stops that conversion until A3 resolves it.
```

If the team wants A1 to run after an A3 pre-pass in some future runtime, state that explicitly as a different staged path. In the current runtime, A1 should not invoke A4.

### 2. High - A2's tolerance precedence leaves an offset band ambiguous and risks premature grid snapping

Evidence:
- A0 sets `AXIS_JITTER_TOL = 50 mm`, `GAP_CLOSE_THRESHOLD <=100 mm`, `GAP_CONFLICT_BAND = 100-300 mm`, and `SNAP_GRID = 50 mm`.
- A2 says same-axis merge requires topology identity plus offset <= `AXIS_JITTER_TOL`.
- A2 also says escalation is for offsets within `GAP_CONFLICT_BAND`, while its header says conflicts occur when an offset exceeds `AXIS_JITTER_TOL`.
- A2 says snap joined coordinates to the canonical axis value "on the `SNAP_GRID`", then later says quantization happens only after canonicalization + closure.

Risk:
There are two failure modes:

1. Offsets in the 50-100 mm range are above same-axis jitter but below the named conflict band. One sentence implies A3; another does not.
2. If a canonical axis is rounded onto the 50 mm `SNAP_GRID` before dimension-chain closure, A2 can degrade authoritative dimensions and then "close" the damage. That contradicts the intended order: evidence selection -> canonicalization -> closure -> final output precision.

Recommended action:
Separate axis identity from gap closure:

```text
axis offset <= AXIS_JITTER_TOL + topology_identity evidence -> same canonical axis
axis offset > AXIS_JITTER_TOL -> conflict/A3 unless A3 has already resolved it
gap width <= GAP_CLOSE_THRESHOLD -> only for gap-closing rules, not same-axis identity
GAP_CONFLICT_BAND -> gap-specific escalation band
```

Also clarify snap order:

```text
Canonical axis value is chosen from authoritative evidence / A3 decision.
Do not round canonical values to SNAP_GRID before dimension-chain closure.
Use OUTPUT_PRECISION for final formatting after canonicalization + closure.
If SNAP_GRID is kept, define it as a candidate regularization grid for low-confidence stroke-only geometry, not as pre-closure rounding for dimensioned axes.
```

### 3. Medium - A2 header says topology change is "no" while sliver absorption may remove an entity

Evidence:
- A2 header says "May change topology: no for snap / close / quantize".
- The same header and §5 say absorbing a sub-`MIN_EDGE_LENGTH` sliver may remove a degenerate entity with `changes_topology = true`.

Risk:
This is easy for future A2 implementers to misread. Sliver absorption is exactly the risky path that must be hard-logged and gated by profile.

Recommended action:
Set the header to:

```text
May change topology: yes, only for sub-MIN_EDGE_LENGTH degenerate sliver absorption;
all other A2 operations must preserve topology.
```

Then require `unsupported` when the sliver is semantically meaningful, belongs to a declared exception space, or cannot be absorbed without changing source attribution.

### 4. Medium - A1 facade transform assumes elevation y is already absolute z

Evidence:
- A1 says facade `y_local` maps to world z directly and a per-floor offset must not be added.

Risk:
This is correct only if the perception frame has already established that the elevation coordinate is building-absolute. Some elevation or cropped facade inputs may use a local vertical origin. In that case, direct y->z mapping will shift window anchors and facade heights.

Recommended action:
Rephrase as:

```text
Facade y_local maps to world z through the facade_local -> world transform.
If the transform proves y_local is building-absolute, no per-floor offset is added.
If vertical origin is ambiguous, emit facade_plan_mismatch or reference_or_identity_ambiguity.
```

This keeps A1 deterministic without hard-coding one drawing convention.

### 5. Low - A0's authority ladders are patched, but still mix grade names and source kinds

Evidence:
- A0 §1.2 defines grades such as `direct_measurement`, `inferred_topology`, and `prior`.
- A0 §1.4 topology / semantic ladders use phrases like "direct annotation / dimensioned boundary", "label / OCR", and "repeated layout pattern".

Assessment:
The patch is conceptually correct, and this should not block A1/A2. But if this becomes an executable schema later, the ladder should reference either `grade` values or `source_kind + grade` pairs consistently.

Recommended action:
Keep the current prose for skill readability, but add a note that authority resolution compares structured evidence items by `(claim_type, grade, source_kind, confidence)`.

## A1/A2 Focus Responses

1. **A1/A2 boundary:** mostly clean. A1 owns frame, centerline, and z-stack; A2 owns canonical axes, snapping, closure, quantization, and sliver prevention. Move any prior-driven wall-thickness completion out of A1 into A3.

2. **Deterministic over typed evidence:** directionally implemented. A2's "topology_identity + offset <= AXIS_JITTER_TOL" rule is the right guard against absorbing real shafts/staggers. It needs explicit handling for the >50 mm / <100 mm band.

3. **Escalation paths:** mostly complete. A1 has good escalation for wall side / thickness / origin / facade conflict. A2 escalates checksum, distinct topology/semantic evidence, and unresolved slivers. Fix the threshold ambiguity so no path falls through silently.

4. **Constant usage:** mostly right by name and unit, but `SNAP_GRID`, `AXIS_JITTER_TOL`, and `GAP_CLOSE_THRESHOLD` need sharper semantics. `PERIMETER_DEPTH` correctly remains downstream-only in A0 and is not consumed by A1/A2.

5. **Runtime feedback:** A2's `detect -> A3-resolve (+A4) -> apply` loop matches README and A0. A1 should align with the same rule by escalating missing wall thickness rather than applying A4 priors itself.

6. **Crash killer:** the main guard is present: same intended cross-floor walls snap to one canonical axis, and sub-`MIN_EDGE_LENGTH` pieces are rejected/absorbed/unsupported. The remaining leak is ambiguous 50-100 mm offsets and semantically meaningful slivers; both need explicit A3/unsupported behavior.

7. **Quantization order:** the intended rule is correct and important: quantize after canonicalization + closure. A2 should make `SNAP_GRID` not look like pre-closure rounding.

8. **Profile applicability:** accurate. A1/A2 are useful across all profiles. The perimeter_core caveat is well stated: envelope/facade axes are always strict; internal axes only matter for declared exceptions and attribution.

## A0 Re-verify Responses

1. **Validation scoped to PartA:** closed. A0 now validates `floor_footprint_coverage`, `room_cell_coverage`, `facade_segment_coverage`, and `window_anchor_validation`, while reserving `thermal_zone_coverage` for zonification. Top-level `status` is present.

2. **Claim types + ladders:** closed with minor cleanup. Numeric / topology_identity / semantic ladders are present and directly address the previous `inferred_topology` issue.

3. **Audit envelope + schema fields:** closed. `stage`, `method_profile`, entity locator, frame/unit, `value_type`, `tolerance_name`, and candidate `source_ids[]` were added.

4. **Seventh conflict type:** closed. `reference_or_identity_ambiguity` is present and correctly covers wall side, origin, local-to-world, and same-vs-different wall/axis ambiguity.

5. **Tolerance registry:** mostly closed, but not fully closeable until the axis-vs-gap threshold semantics are clarified. The registry format and constants are there; the overlap among `AXIS_JITTER_TOL`, `GAP_CLOSE_THRESHOLD`, and `GAP_CONFLICT_BAND` needs one sentence of precedence.

6. **Method profile A3/A4 strength:** closed. `use_grouped_rooms` now has semantic grouping and closure-heavy A3/A4 posture; `perimeter_core` is conservative; `room_identity` is full strength.

## Missing / New Issue Checklist

- A1: prior wall thickness must be A3-resolved before A1 consumes it.
- A1: facade vertical transform should require a known vertical origin, not assume all elevation y coordinates are absolute.
- A2: define precedence for `AXIS_JITTER_TOL` vs `GAP_CLOSE_THRESHOLD` vs `GAP_CONFLICT_BAND`.
- A2: clarify that `SNAP_GRID` is not pre-closure rounding for authoritative dimensions.
- A2: mark topology change as conditionally allowed only for logged degenerate sliver absorption.
- A0: optionally normalize authority ladder prose into structured `(claim_type, grade, source_kind, confidence)` comparisons.

## Recommended Minimal Patch Before Finalizing

1. In A1 §4, replace direct prior use with "A3-resolved prior may be consumed; otherwise escalate."
2. In A1 §2.2, route facade y through the declared facade transform and escalate ambiguous vertical origins.
3. In A2 §1, add explicit handling for any same-axis offset > `AXIS_JITTER_TOL`.
4. In A2 §2/§4, state canonical values are chosen from evidence, not rounded to `SNAP_GRID` before closure.
5. In A2 header and §5, make topology-changing sliver absorption conditional and logged.
6. In A0 §4, add one precedence note separating axis identity tolerances from gap-closing tolerances.

With those edits, A1/A2 are ready to freeze and the next batch can move to A4 stub + A3.

## Sources Checked

Internal:

- `AI_agent/logs/review/request/2026-06-07_correction_A1A2_and_A0_reverify_request.md`
- `skills/energyplus_mcp_twostep/phase2/PartA-correction/A0_contract.md`
- `skills/energyplus_mcp_twostep/phase2/PartA-correction/A1_coordinate_normalization.md`
- `skills/energyplus_mcp_twostep/phase2/PartA-correction/A2_regularization.md`
- `skills/energyplus_mcp_twostep/phase2/PartA-correction/README.md`
- `AI_agent/logs/review/review/2026-06-07_correction_A0_contract_review.md`
- `AI_agent/logs/review/review/2026-06-07_partA_priors_tolerance_retrieval.md`

No external research was needed for this document review.
