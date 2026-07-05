# Recognition -> Modeling Capability Design Review

Date: 2026-05-28
Reviewer: Codex
Scope: Design review for `AI_agent/capability/recognition_modeling_capability.md`, especially the proposed tolerance-based phase2 regeneration direction, the sm21 evidence interpretation, and the open decisions in Section 6.

## Verdict

Accepted directionally, but not as a single undifferentiated "rewrite phase2 prompt" change.

The core diagnosis is sound: sm21 shows that EnergyPlus completion is not a correctness oracle, and that faithful transcription of phase1 can be wrong when phase1 emits mutually inconsistent channels. The proposed move from rigid transcription to tolerance-aware qualitative-first reconstruction is the right architectural direction.

My recommended architecture is: keep phase1 faithful and image-bound, but make phase2 explicitly two subpasses:

1. `phase2a_reconciliation`: vector JSON -> machine-readable resolved geometry + `corrections[]` / conflicts / residuals.
2. `phase2b_intake_generation`: resolved geometry -> existing `IntakeOutput` 11-field contract.

This can still live "inside phase2" and remain image-blind. The important boundary is not a new model call or graph node; it is a typed intermediate artifact. Without that artifact, `corrections[]` becomes a prose convention buried inside natural-language specs, and the error-budget separation becomes much harder to test.

## Findings

### 1. High - A prose-only `corrections[]` log is not enough to preserve the error budget

Evidence:
- The design correctly makes `corrections[]` a hard requirement when relaxing exact transcription (`recognition_modeling_capability.md` lines 75-81).
- The current phase2 contract outputs exactly one `IntakeOutput` with 11 fields (`phase2/rules.md` lines 24-32), and the runtime model has only those fields (`src/agent/state.py` lines 23-66).
- Those 9 `*_specs` fields are natural-language downstream instructions, not structured geometry (`phase2/rules.md` lines 31-32).

Risk:
If corrections are only written as prose inside `zone_specs` / `surface_specs` / `fenestration_specs`, they are not reliably machine-checkable, diffable, or tied to exact source evidence. That makes the new relaxed regime hard to evaluate: a model can "fix" geometry, omit the correction, or report a correction whose numbers are not actually used downstream.

Recommended action:
Introduce a phase2 reconciliation artifact before `IntakeOutput`, either as a sidecar file or as an internal typed object:

- `resolved_axes`: canonical x/y/z axis sets per floor / facade / band.
- `resolved_zones`: polygons/ranges with source evidence and residuals.
- `resolved_windows`: parent wall, span, z, containment result.
- `corrections[]`: source ids, original values, resolved values, rule invoked, confidence, residual magnitude.
- `conflicts[]`: unresolved contradictions and unsupported-geometry flags.

Then generate the existing 11-field `IntakeOutput` from that resolved artifact. Keep the downstream contract unchanged.

### 2. High - "Consistent measured data > dim-chain > prior" needs a conflict model, not just a priority order

Evidence:
- The design proposes measured > dim-chain-derived > prior and forbids priors from overriding consistent measured data (`recognition_modeling_capability.md` lines 97-100).
- sm21 has locally plausible stroke coordinates and dimension-chain coordinates that disagree: wall strokes S8/S9/S10 are at 4.95 / 7.50 / 10.05, while D19-D30 encode 3.75 / 7.50 / 11.25 (`2f_view.json` lines 55-70 and 140-151).
- Phase1 also records that those partition positions were "estimated from dim chains" in a free-text note (`2f_view.json` lines 161-165), so the stroke coordinates are not actually equal-grade measurements.

Risk:
A simple priority stack will fail when evidence is internally mixed: a stroke may be "drawn" but estimated, a dim chain may be transcribed correctly but refer to window edges rather than partition centerlines, and a real but unusual design may look like an outlier. This is exactly how DeepSeek snapped to window-edge points and produced a 1.2 m office while still completing EP.

Recommended action:
Define evidence grades and conflict classes explicitly:

- Direct measurement, transcribed dimension, estimated stroke, inferred topology, prior.
- Local conflict: stroke vs dimension for the same element.
- Global conflict: floor-to-floor axis jitter, coverage gaps, windows crossing zone boundaries.
- Semantic conflict: room role/label vs room size prior.

Only let priors operate when the evidence is missing, low confidence, or mutually contradictory, and log the residuals. For "unusual but possible" designs such as a real service closet, prefer `conflicts[]` / unsupported-note over silently normalizing it into an office bay.

### 3. High - Canonical-axis snapping is right, but must be topology-preserving and scoped

Evidence:
- The design identifies global-consistent axis snapping as the real fix for the Sonnet crash (`recognition_modeling_capability.md` lines 87-90).
- The current phase2 rules already support intentionally misaligned partitions between floors by splitting InterZone surfaces at the union of breakpoints (`phase2/rules.md` lines 213-235).
- The Sonnet output produced sub-0.1 m strips from 4.90/4.95 and 10.05/10.10 misalignment, and the logs show non-manifold warnings around those points (`step5_downstream.log` lines 280-307). The IDF contains the 5 cm paired surface `F1_SM_Office_Ceiling_S2` (`temp_20260528_095508.idf` lines 721-744 and 1848-1869).

Risk:
"Snap all references to one canonical partition axis set" fixes jitter, but if applied globally it can erase legitimate staggered walls, shafts, setbacks, structural transfers, or non-orthogonal geometry. The existing rules intentionally allow real cross-floor misalignment; the new snapping rule must not collapse that entire capability.

Recommended action:
Make snapping scoped and topology-preserving:

- Cluster axes only within a tolerance and only when their semantic evidence suggests "same intended wall".
- Preserve genuine misalignment when the offset exceeds the jitter tolerance or has independent evidence.
- Add a minimum split width / area invariant: no InterZone split piece below the geometry tolerance; either merge it into the nearest adjacent canonical cell or mark the case unsupported.
- Run snapping before InterZone split generation, not after surfaces have already been enumerated.

### 4. Medium - The sm21 diagnosis is sound, but "phase1 internal contradiction" should be phrased as "dual-channel conflict plus provenance failure"

Evidence:
- The 2f wall strokes and dimension chain genuinely disagree (`2f_view.json` lines 55-70 and 140-151).
- The free-text self-check says the problematic x positions were estimated (`2f_view.json` lines 161-165).
- Opus explicitly used the dimension-chain interpretation and completed EP, though still with geometry warnings and one CHKSBS warning (`eplusout.err` lines 23-68 and 85-93).
- Sonnet's run reached EnergyPlus and then exited with code -11 while `.err` remained empty (`step5_downstream.log` lines 477-490; `output_sonnet/eplusout.err` is 0 bytes).

Risk:
Calling this only "phase1 internal contradiction" may hide the actionable failure: phase1 did not preserve structured provenance for estimated coordinates. The right fix is not just "phase2 should be smarter"; it is "phase1 must not make estimated geometry indistinguishable from traced geometry".

Recommended action:
Keep the diagnosis, but sharpen it:

- Phase1 perception succeeded on the dimension text.
- Phase1 coordinate/provenance discipline failed by emitting estimated partition coordinates in the same shape as measured strokes.
- Phase2 needs arbitration because the channels disagree.

This supports the proposed dual-channel phase1 change, but it should be treated as a schema-level change, not just a note-writing habit.

### 5. Medium - The 50 mm grid is reasonable only after canonicalization, not as an independent snap of every coordinate

Evidence:
- The design proposes 50 mm coordinate quantization and separate relative checks for area/WWR (`recognition_modeling_capability.md` lines 92-95).
- The Sonnet failure class is exactly a 50 mm cross-floor jitter (`recognition_modeling_capability.md` lines 55-59).

Risk:
If every coordinate is rounded independently, the grid can create new boundary crossings: a narrow window can cross a parent wall split, a small shaft can disappear, or two nearby but distinct axes can collapse. It can also mask arithmetic mistakes because "now it is on grid" looks clean while topology changed.

Recommended action:
Use the grid as an output normalization step for a resolved axis set, not as the primary solver:

- First solve topology and canonical axes.
- Then quantize canonical axes as a group.
- Re-run containment, coverage, minimum-width, and WWR residual checks after quantization.
- For windows, snap to the parent surface coordinate frame and then verify the window remains fully inside exactly one exterior parent wall.

### 6. Medium - The qualitative hierarchy is missing several hard invariants

Evidence:
- The proposed generation hierarchy mentions closure, adjacency, windows not crossing zones, and elevation window position outranking plan window position (`recognition_modeling_capability.md` lines 102-105).
- Current rules already contain additional invariants: no unsupported rectangular normalization (`phase2/rules.md` lines 132-139), exact cross-field references (`phase2/rules.md` lines 428-438), and explicit no-template writing / no placeholders (`phase2/rules.md` lines 441-449).
- The Opus "successful" EP run still reports multiple zones not fully enclosed (`eplusout.err` lines 23-68), which means EP completion alone does not enforce the intended qualitative level.

Risk:
The proposed hierarchy may allow models to optimize for "EP runs" while leaving non-manifold zones, duplicate edges, unsupported normalizations, or cross-field reference drift. That would recreate the same false-positive problem with a different vocabulary.

Recommended action:
Promote these to non-negotiable phase2 verification invariants:

- Zone coverage = footprint minus explicit voids; no overlap.
- Each zone is manifold or explicitly unsupported.
- No surface edge/area below tolerance.
- Every InterZone pair has reciprocal surfaces with matching sub-ranges and construction.
- Every window is fully inside exactly one exterior parent surface and does not cross a zone boundary.
- Cross-field names resolve exactly.
- No unsupported geometry is silently normalized.
- Area, volume, facade WWR, and window counts are reported with residuals against source evidence.

### 7. Medium - Phase1 "dual-channel + confidence" is larger than a small prompt tweak

Evidence:
- The current phase1 schema has one `strokes[]` geometry and one `dimensions[]` list; provenance/confidence is mostly free text (`phase1/guide.md` lines 102-172 and 179-190).
- The design proposes phase1 should stop presenting estimated strokes as measured, and instead provide two independent channels plus confidence (`recognition_modeling_capability.md` lines 77-80).

Risk:
If this is implemented only by telling the VLM to write better notes, phase2 will still receive ambiguous evidence. The exact sm21 failure can recur because a downstream text model must parse prose notes to discover that a coordinate was estimated.

Recommended action:
Add structured provenance fields to phase1 outputs before relying on phase2 reconciliation:

- Per coordinate or stroke: `coordinate_source = measured_from_stroke | estimated_from_dimension | inferred | unknown`.
- `confidence = high | medium | low` or a numeric score.
- `linked_dimension_ids`.
- Optional `alternatives[]` for known competing interpretations.

This is still faithful perception; it does not require phase1 to choose topology.

### 8. Low - The first implementation increment is too broad unless split into reviewable slices

Evidence:
- The proposed next step combines phase2 solver rewrite, a new priors document, and phase1 dual-channel changes (`recognition_modeling_capability.md` lines 120-121).

Risk:
Bundling all three makes it hard to attribute a regression: did quality improve because of axis reconciliation, priors, or a changed phase1 schema? It also increases the chance of disrupting B1.5.c intake-node serialization before the new contract is stable.

Recommended action:
Sequence as:

1. Add the phase2 reconciliation artifact and corrections schema, using current phase1 inputs.
2. Add verifier checks and replay sm20/sm21 against it.
3. Add phase1 structured provenance/confidence fields.
4. Add priors last, initially only as warnings / tie-break suggestions.
5. Only then wire the serial `intake_node` implementation to the new artifacts.

## Review of the Four Improvement Directions

### Section 5.1 Gap closure + global-consistent axis snapping

Sound, with the caveat that "same axis" must be inferred from evidence, not just coordinate proximity. The under-weighted failure mode is erasing real staggered walls or legitimate cross-floor misalignment. Fix by scoping canonical-axis clusters and adding a min-surface rule.

### Section 5.2 50 mm grid + dimension-chain closure

Sound as a framework, but the grid should normalize resolved axes, not raw coordinates. The under-weighted failure mode is that independent snapping can create a new window-parent crossing or delete a real small space. Fix by re-running topology and containment checks after quantization.

### Section 5.3 Architectural common-sense priors

Useful, but dangerous unless priors are separately logged and tested. The under-weighted failure mode is that priors will look like "obvious fixes" and suppress real small service rooms, shafts, lobbies, or atypical facade patterns. Fix by requiring a conflict class before priors can change geometry, and by using priors first as warnings.

### Section 5.4 Qualitative > quantitative hierarchy

Correct principle, incomplete invariant list. Add explicit manifold, min-edge/min-area, reciprocal InterZone pairing, name resolution, unsupported-geometry, and residual-reporting checks. Also treat "EP completed" as a weak signal, not an acceptance criterion.

## Open Decision Recommendations

### Decision 1 - Phase2 rewrite vs separate reconciliation pass

Recommendation: explicit reconciliation pass, but inside phase2.

Do not add a new image-aware stage. Do not push reasoning back into phase1. But do create a formal `resolved_geometry + corrections[]` artifact before generating `IntakeOutput`. This preserves the two-step split while making the new regeneration behavior auditable.

### Decision 2 - `corrections[]` hard requirement

Recommendation: yes, hard requirement, but structured.

A prose correction note is not enough. Make the run fail or mark unsupported if geometry changed and there is no correction entry with source ids, original value, new value, rule, residual, and confidence.

### Decision 3 - Priors red line

Recommendation: keep the red line, but refine it.

Priors may break ties, fill missing values, or flag suspicious geometry. They should not override consistent high-confidence evidence. When evidence is consistent but violates a prior, emit `conflicts[]` or a low-confidence warning rather than silently normalizing.

### Decision 4 - Threshold framework

Recommendation: approve the framework, not values.

Keep separate thresholds for closure gaps, axis clustering, minimum surface width/area, coordinate output precision, and area/WWR relative residuals. Values should be empirically tuned on sm20/sm21 plus a deliberately weird case containing a real small service room and a real staggered wall.

## Evidence Interpretation

The sm21 diagnosis is mostly confirmed.

- Phase1 internal conflict: confirmed. The 2f stroke channel gives 4.95 / 7.50 / 10.05 while the dimension chain supports 3.75 / 7.50 / 11.25, and the output admits those stroke coordinates are estimated.
- Sonnet crash reading: plausible and well supported. The Sonnet IDF contains a 4.90-4.95 m InterZone sliver, the geometry validator warns around the same coordinates, EnergyPlus exits with code -11, and `.err` is empty.
- EP-completion != correctness: confirmed. Opus completes but still has non-enclosed-zone warnings; DeepSeek's geometry is known to be worse yet completes cleanly per the request. EnergyPlus is a necessary runtime check, not a geometry oracle.

Alternative reading:
The exact EnergyPlus segfault trigger is still technically "EnergyPlus crashed on this IDF", not a formally isolated minimal reproducer. But the sliver/non-manifold evidence is strong enough to drive the design conclusion: phase2 must avoid sub-tolerance split surfaces before IDF generation.

## Contract / Policy Impact

- Downstream `IntakeOutput`: safe if the resolved geometry and corrections log stay outside the 11-field `IntakeOutput` or are stored in a sidecar. Risky if a top-level `corrections` field is added without updating `src/agent/state.py` and downstream tooling.
- Clean-spec policy: a priors doc can remain clean if it is normative and current, not a pile of case notes. Put case-specific lessons in tests/fixtures or capability docs, not inside generic rules except as clearly labeled examples.
- Phase1 <-> phase2 decoupling: preserved if phase2 remains image-blind and operates only on phase1 JSON + metadata. Strengthened if phase1 emits structured provenance instead of prose notes.

## Acceptance Criteria Status

- Verdict on core architectural call: accept phase2 regeneration, but require explicit phase2 reconciliation artifact.
- Open decisions: recommendations given above.
- Four directions: all directionally sound, with failure modes listed.
- sm21 diagnosis: confirmed with the provenance caveat.
- Contract threats: main threat is adding `corrections[]` to `IntakeOutput` instead of a sidecar/intermediate object.
- Scope/sequencing: split into smaller slices before B1.5.c wiring.

