# Role-To-Reading Plan Review

Date: 2026-06-21
Reviewed plan: `AI_agent/logs/review/request/2026-06-21_role_to_reading_plan_request.md`
Scope: plan review only. No source edits.

## Overall Verdict: REWORK

The direction is right: semantic role should stop being invented by the image-blind correction LLM. But the proposed plan is not implementation-ready because its central deterministic assignment mechanism depends on an image-local -> correction-world transform that is not currently a first-class artifact. Without that transform, the fallback "LLM-assisted + guard" only constrains the role vocabulary/source; it does not robustly prove that the selected label belongs to the selected corrected cell.

I would approve after the plan adds:

1. A formal `RoomRoleObservation`/`RoomLabel` identity with stable `id`, `view_id`, anchor coordinate frame, role, confidence, and basis.
2. A formal assignment/provenance contract, preferably `Cell.role_source_label_id` or a sidecar `role_assignments` map, not just `Cell.role`.
3. A deterministic gate① invariant that fails any non-`unknown` role not backed by a matching reading label source.
4. A legacy/grandfathering policy so existing runs without `room_labels` do not instantly fail validation.
5. A clear unknown-role MEP fallback policy.

## §6.1 — Deterministic Code Step vs LLM-Assisted + Guard

Verdict: DISAGREE with deterministic point-in-cell as currently stated; AGREE with it only after adding a canonical transform artifact. LLM-assisted + guard is acceptable only as a bounded interim if the guard proves explicit source linkage, not just role vocabulary membership.

Grounding:

- `src/agent/reading/schema.py:94-114` defines `ReadingView`; there is no room-label anchor field today.
- `src/agent/pipeline.py:326-330` passes reading vector JSONs to correction as text chunks. It does not parse and preserve a transform artifact for later deterministic use.
- `src/agent/pipeline.py:289-306` asks the correction LLM to output world-frame cells and windows; `src/agent/pipeline.py:302` is where the LLM emits `{id, role, x, y}`.
- `src/agent/correction/schema.py:30-37` makes `Cell.role` a plain string and `x/y` world-meter ranges; there is no `role_source_label_id`, `source_view_id`, or plan transform.
- `src/agent/pipeline.py:474-484` validates the parsed LLM JSON directly into `CorrectedGeometry`, then `src/agent/pipeline.py:491-494` writes it. No post-parse transform provenance is available.
- `src/agent/pipeline.py:697-723` applies deterministic core and builds kernel geometry after correction, but by then the only available room geometry is already the LLM's corrected world cells.

The current repo does have deterministic facade-local translation machinery, but it is elevation-specific:

- `src/agent/correction/facade.py:1-7` says facade image-local -> world translation is derived from image-local facade orientation plus reconciled footprint/z-stack.
- `src/agent/correction/facade.py:69-109` implements `derive_facade_frame()` for elevation along-facade coordinates.

That does not solve plan-room anchors. The correction docs describe plan-local -> world as a concept, but not as a persisted code artifact:

- `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:29-33` says to apply the plan's origin offset/rotation to bring `plan_local` into world frame.
- `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:3-16` frames A1 as deterministic over typed evidence, but the current implementation does not expose a reusable plan transform from the LLM correction draw.

Therefore, the plan's line "把 reading anchors 经 correction 的 image→world 同一变换映射后" has nowhere concrete to execute today. The transform is inside the correction LLM's reasoning, not in a `PlanWorldFrame` object.

Required change:

- Add a first-class plan transform artifact before relying on point-in-cell. It needs at least `view_id`, `image_kind=plan`, `floor_hint/floor_ref`, coordinate frame, origin, scale, optional rotation/mirror, and the exact mapping to correction world.
- If correction is allowed to output that transform, gate it deterministically against reading geometry/dimensions. Otherwise the transform itself is another opaque LLM claim.
- If not adding this now, require correction to output `role_source_label_id` for each non-`unknown` cell and enforce only what is provable: the referenced label exists and `Cell.role == label.role`. Do not claim this fully removes DeepSeek from role assignment; it only prevents free invention.

Guard robustness:

- A guard that checks "role value appears somewhere in reading labels" is weak and can pass a wrong cell-label binding.
- A guard that checks `role_source_label_id` exists and role matches the label is stronger, but still does not prove spatial membership unless the anchor and cell share a deterministic coordinate frame.
- A guard that checks transformed anchor-in-cell is genuinely robust, but only after the transform becomes an auditable artifact.

## §6.2 — Anchor Coordinate System And Multi-Image/Floor Matching

Verdict: DISAGREE with the plan's current specificity. The anchor model needs more fields and a transform policy before implementation.

Grounding:

- `src/agent/reading/schema.py:98-103` has `image_label`, `image_kind`, `scale_origin`, strokes, dimensions, and OCR texts. It does not validate a plan frame or floor binding.
- `src/agent/reading/schema.py:100` leaves `scale_origin` as a free `dict | None`, so code cannot safely depend on its shape.
- `skills/intake_pipeline/0_reading/guide.md:72-79` says each image has a local coordinate system and `scale_origin` records local origin in world system.
- `skills/intake_pipeline/0_reading/guide.md:95-99` gives an example `scale_origin` with world coordinates.
- But `src/agent/reading/schema.py:13-18` and `src/agent/reading/schema.py:80-91` intentionally keep elevation facade orientation image-local and not world-load-bearing.
- `src/agent/reading/legacy.py:9-14` preserves legacy world-direction hints only as low-confidence evidence.
- `tests/test_reading_schema.py:41-50` asserts that legacy facade world hints are not promoted; world axis/sign must be re-derived.

There is also no stable floor binding on reading views:

- `src/agent/reading/schema.py:94-114` has `image_label`, but no `floor_id`, `floor_index`, or structured `floor_ref`.
- `src/agent/pipeline.py:329-330` passes each discovered vector file name and JSON to correction, but does not create a structured map from view -> floor.

Multi-floor failure mode:

- If two floors share similar coordinates, an anchor `[x, y]` without `view_id` and floor binding can match a cell on the wrong floor.
- If correction shifts/snaps cells from face coordinates to centerlines, a label anchor near a boundary may land outside the final cell unless the transform/snap policy is explicit.

Recommended anchor contract:

- `RoomRoleObservation.id`: stable local id, unique per reading view.
- `view_id` or `image_label`: exact source image.
- `image_kind`: normally `plan`; do not let elevation labels bind to plan cells unless explicitly supported.
- `floor_ref`: structured, preferably from project metadata/testdata or file role, not only free-text `image_label`.
- `anchor`: local plan meters or pixels, with explicit `coordinate_frame`.
- `anchor_confidence` and optional `anchor_extent`/bbox. A point is fragile when labels are printed near room edges.
- `role`, `label_text`, `basis`, and `confidence`.

Where anchors would be transformed:

- If implemented deterministically, the natural place is after `run_correction()` parses `CorrectedGeometry` but before `apply_deterministic_core()` at `src/agent/pipeline.py:694-699`, or inside the correction gate path, because corrected cells and reading artifacts are both available there.
- But that requires a reusable transform object. Today only the correction LLM knows the plan-local -> world relationship that produced `Cell.x/y`.

## §6.3 — Does Reading Emitting Role Cross The Topology Boundary?

Verdict: AGREE-WITH-CHANGES. Reading may emit observed semantic role evidence, but not cell membership or room topology.

Grounding:

- `skills/intake_pipeline/0_reading/guide.md:32-36` says reading identifies component type and traces geometry; it does not outline rooms or assign topology.
- `skills/intake_pipeline/0_reading/guide.md:229-239` draws the red line: visual recognition is reading; wall ext/int, window parentage, and which walls enclose which room are correction.
- `skills/intake_pipeline/0_reading/guide.md:259-263` explicitly rejects stuffing a room polygon into strokes or adding parent-child/topology fields.
- `src/validator/checks/reading.py:1-5` says the reading linter is per-image and never topology/cross-image/world placement.
- `src/validator/checks/reading.py:29-30` forbids topology/world keys on strokes.
- `src/validator/checks/reading.py:136-151` enforces that forbidden topology/world fields do not appear on strokes.

Reconciliation with topology-light:

- `label_text + anchor + role_claim` is still topology-light if it is modeled as an observation: "the drawing shows text/furniture cue here, interpreted as this role."
- `cell_id`, room polygon, room boundary, enclosed-cell membership, adjacent zones, or "this label belongs to corrected cell X" crosses into correction territory.
- `role` is a semantic claim, not necessarily topology. `skills/intake_pipeline/1_correction/A0_contract.md:60-65` already treats "what is this space / role?" as a `semantic` claim whose highest authority is label/OCR.

Cleanest boundary:

- Reading should emit `RoomRoleObservation`, not `Room`.
- Reading can normalize direct labels into a controlled role if the label is visible and unambiguous, because correction is image-blind.
- For furniture-based role, be more conservative. `skills/intake_pipeline/0_reading/reading_guide.md:72-74` recognizes furniture/sanitary/equipment as visible categories, and `skills/intake_pipeline/0_reading/pen_library.md:20-24` says several such cues are recognized but logged rather than traced. A round table -> meeting role is image-based but inferential; it should carry `basis="furniture"` and lower confidence, or be emitted as a cue that a deterministic alias/rule maps to role.
- Correction should assign observations to its cells. Once assigned, it cannot change the role value.

I would not move role inference back to correction if the evidence is visible text/furniture. That recreates the image-blind problem. The stable boundary is: reading owns semantic observation; correction owns spatial assignment to cells.

## §6.4 — Controlled Vocabulary, `unknown`, And 4_MEP

Verdict: AGREE-WITH-CHANGES.

Grounding:

- `src/agent/correction/schema.py:35` currently allows any string and defaults missing role to `"office"`.
- `src/agent/geometry/modelling.py:63` also defaults `ZoneVolume.role` to `"office"`.
- `src/agent/geometry/modelling.py:329-334` copies `Cell.role` into `ZoneVolume.role`, defaulting to `"office"` if missing.
- `src/agent/geometry/specs.py:137-140` serializes the role text into `zone_specs`.
- `src/agent/pipeline.py:540-541` gives the exact zone list to MEP.
- `skills/intake_pipeline/4_mep/authoring.md:123-126` instructs MEP to assign people/lights/HVAC per zone by the zone's role.
- `skills/intake_pipeline/4_mep/mep.md:24-27` currently seeds office people and lighting defaults.
- `skills/intake_pipeline/4_mep/mep.md:42-43` says future loads by space type are placeholders.

Risks:

- If `unknown` reaches `zone_specs`, `4_mep` has no explicit unknown-role mapping today.
- If `unknown` silently maps to office defaults, that preserves simulation completeness but weakens the "do not guess" semantics unless the unknown fallback is flagged/audited.
- Existing fixtures use role strings not in the proposed compact list. For example, `tests/test_geometry_kernel.py:156` uses `"entrance lobby"` and `tests/test_geometry_kernel.py:169-170` use `"meeting room"`, while other tests use `"meeting"`, `"office"`, and `"corridor"`.

Recommendation:

- Put the vocabulary in a shared module, not in reading-only or correction-only code. The same source needs to be imported by reading validation, correction role guard, naming later, and MEP authoring/checks.
- Include canonical roles plus aliases. At minimum normalize `"meeting room" -> "meeting"` and `"entrance lobby" -> "lobby"` or intentionally keep multi-word canonical values and update downstream docs.
- Define `unknown` as "no backed semantic observation assigned to this corrected cell." It should not mean "office."
- For `4_mep`, choose one explicit policy:
  - fail before MEP when any role is `unknown`, if role-specific MEP is required; or
  - allow simulation fallback to office defaults while preserving a check flag and text note that the role is unknown.

Given current MEP defaults are office-only, the pragmatic near-term policy is probably `unknown` -> office physical defaults with a cross-check flag, but this must be explicit.

## §6.5 — Guard Placement And Fail vs Flag

Verdict: DISAGREE with putting the core enforcement in judge② or making unbacked non-unknown roles only a flag. The invariant belongs in gate①.

Grounding:

- `src/validator/checks/schema.py:6-13` defines invariants as hard/fatal and cross-checks as attribution surfaces.
- `src/validator/checks/schema.py:103-106` maps invariant failures to `BLOCK` and cross-check failures to `FLAG`.
- `src/validator/checks/schema.py:169-172` says `CheckReport.passed` is true if nothing blocks; flags pass through gate①.
- `src/agent/execution/step_orchestrator.py:197-200` says deterministic gate① failure blocks/resamples before stage acceptance.
- `src/agent/execution/step_orchestrator.py:238-253` only advances after the report passes.
- `src/agent/execution/step_orchestrator.py:270-289` runs judge② only after gate① passes, and may advance without judge if no enabled judge or judge is disabled by policy.
- `src/agent/judge/executor.py:28-33` has J0/J1 enabled in the registry, but `src/agent/execution/policy.py` defaults judge execution off in normal policy. The guarantee cannot depend on judge availability.
- `src/validator/checks/correction.py:55-71` is the current correction deterministic gate adapter; this is the right place to add role provenance checks, with extra reading-label inputs.
- `src/agent/pipeline.py:425-442` builds the current correction inner validator; `src/agent/pipeline.py:469-482` uses it during LLM calls. Legacy `run_pipeline` would need the role guard in this path too, not only in validation replay.
- `src/agent/execution/validation_run.py:128-137` validates persisted snapped correction geometry via `check_correction()`, so replay validation also needs access to reading labels if the guard is part of S1.

Recommended dispositions:

- Fail gate① as `INVARIANT` if `Cell.role != "unknown"` and no `role_source_label_id` exists.
- Fail gate① as `INVARIANT` if `role_source_label_id` points to a missing reading observation.
- Fail gate① as `INVARIANT` if `Cell.role` differs from the referenced observation's canonical role.
- Fail gate① as `INVARIANT` if spatial membership is claimed but the deterministic transformed anchor is outside the cell beyond tolerance.
- Flag as `CROSS_CHECK` if a cell has `role="unknown"` because no label/observation is available.
- Flag or fail, depending on policy, if multiple labels fall in one cell with conflicting roles.

This enforces "correction cannot change role" even though the role still rides on `Cell`. If unbacked roles are merely gate② findings or gate① flags, correction can still emit a wrong role and the pipeline can advance.

## §6.6 — Omitted Blockers / Simpler Correct Approach

Verdict: REWORK.

The plan omits several implementation blockers.

### BLOCKER: No First-Class Transform For Deterministic Anchor-In-Cell

As covered in §6.1/§6.2, there is no durable plan-local -> world transform to apply to reading anchors. The plan must either create one or downgrade its claim from deterministic spatial assignment to explicit-source LLM binding plus deterministic provenance guard.

### BLOCKER: Migration Will Break Existing Baseline Validation Unless Grandfathered

The plan says old readings without `room_labels` become `unknown + flag`. That is safe only for new correction draws. It is not safe for validating existing runs whose correction geometry already contains non-unknown roles.

Grounding:

- `src/agent/execution/validation_run.py:128-137` loads existing `1_correction/correction_geometry_snapped.json` and runs `check_correction()`.
- `tests/test_validation_run_baseline.py:199-205` requires every per-stage gate① report to pass on the clean `sm21_anchor` golden run.
- The sm21 baseline comments at `tests/test_validation_run_baseline.py:191-194` describe the golden run as existing fresh reading and gate①-green baseline.
- If the new S1 guard sees old `0_reading` artifacts with no `room_labels` and existing correction cells with roles like `office`, `corridor`, or `meeting`, then a strict "non-unknown role must have room_label backing" invariant will block this test.

Required migration policy:

- Either mark legacy reading artifacts as `role_provenance_unavailable` and downgrade role provenance to `NOT_APPLICABLE`/flag for existing runs, or provide a one-time migration that creates `room_labels` for fixtures/baselines before enabling the invariant.
- Do not make "old readings -> all unknown" the only story. That describes regenerated correction outputs, not persisted historical artifacts.

### MAJOR: Unknown Roles Can Degrade MEP

Grounding:

- `src/agent/geometry/specs.py:137-140` serializes role into `zone_specs`.
- `skills/intake_pipeline/4_mep/authoring.md:123-126` tells MEP to author per-zone specs by role.
- `skills/intake_pipeline/4_mep/mep.md:24-27` only defines office defaults today.

If many legacy or unlabeled cells become `unknown`, the MEP prompt loses the role signal that currently drives load selection. The current validators check name binding and basic reasonability, not role-specific density correctness. This could pass tests while semantically degrading load assumptions.

### MAJOR: `Cell.role` Alone Is The Wrong Enforcement Surface

`Cell.role` remains a mutable string:

- `src/agent/correction/schema.py:30-37` defines `Cell.role` as a plain string.
- `src/agent/geometry/modelling.py:329-334` blindly copies it to `ZoneVolume`.

If the plan only changes prompts and adds a role vocabulary check, correction can still choose the wrong backed role. Add provenance:

- `RoomRoleObservation.id` in reading.
- `Cell.role_source_label_id` in correction, or a sidecar assignment table.
- Guard that checks source existence and exact role equality.

### MAJOR: Role Vocabulary Needs Alias Migration

Existing tests and fixtures contain mixed role strings:

- `tests/test_intakeoutput_assembly.py:21-26` uses `office` and `corridor`.
- `tests/test_geometry_kernel.py:156` uses `entrance lobby`.
- `tests/test_geometry_kernel.py:169-170` use `meeting room`.
- `tests/test_gt_from_dxf.py:42-46` uses `meeting`, `office`, and `corridor`.

A strict new vocabulary without alias handling will create churn or failures unrelated to the refactor.

### MINOR: Reading Validator Needs To Avoid Strokes-Only Topology Logic

The plan mentions `validator/checks/reading.py` anchor bounds and vocabulary checks. That is fine, but keep it local:

- Validate `RoomRoleObservation.id` uniqueness, non-empty label/cue text, role in vocabulary, basis in enum, and anchor numeric/in-bounds for that view.
- Do not validate whether the anchor is inside a corrected cell at reading gate①. `src/validator/checks/reading.py:1-5` explicitly keeps reading checks per-image and away from topology/world placement.

### Simpler Correct Approach

Recommended revised architecture:

1. Reading emits `RoomRoleObservation` with stable id, view id, anchor, basis, verbatim cue text, canonical role, and confidence. No cell id, no polygon.
2. Correction still draws cells and must assign a source label id to each non-unknown role. It may not invent roles.
3. Gate① S1 enforces source existence and role equality. If a deterministic transform exists, it also enforces anchor-in-cell. If not, it records "spatial binding not mechanically provable" as a flag and leaves that part to J1.
4. `unknown` is allowed only when no source label is assigned. It is flagged, not silently defaulted semantically.
5. Legacy runs get a transition mode: role provenance `NOT_APPLICABLE`/flag when no `room_labels` exist, until fixtures and baselines are migrated.

This keeps the philosophy clean: reading owns visible semantic evidence; correction owns topology and spatial assignment; deterministic checks enforce the handoff contract.

## v2 re-review

Overall verdict: APPROVE-WITH-CHANGES.

v2 addresses the main REWORK issue by explicitly deferring deterministic anchor-in-cell until a first-class plan-local -> world transform exists. The source-linkage guard is a valid M1-style step if the implementation keeps legacy replay truly grandfathered and does not make the main correction JSON more brittle.

### (a) Legacy `NOT_APPLICABLE` And Test Stability

The design should keep `sm21` and most existing tests green, but only under two concrete implementation constraints.

First, `role_source_label_id` must not be schema-required on `Cell`. Current old artifacts and many tests construct cells with only `id`, `role`, `x`, and `y`; see `src/agent/correction/schema.py:30-37`. If the new field is declared as `str | None` without `= None`, Pydantic v2 treats it as required, and old JSON will fail before the guard can emit `NOT_APPLICABLE`. Use `role_source_label_id: str | None = None`, or do not put the field on `Cell` at all and use a sidecar.

Second, legacy mode cannot be inferred from parsed `ReadingView.room_labels == []` alone. `ReadingView` already uses defaults and permissive loading (`src/agent/reading/schema.py:94-114`), so once `room_labels: list[...] = []` is added, an old artifact with no key and a new artifact that intentionally found no labels both look identical after parsing. The grandfather check must inspect raw JSON key presence, a run/feature flag, or a migration marker.

Specific sm21 path:

- `tests/test_validation_run_baseline.py:199-205` requires every gate① report to pass for the sm21 golden run.
- `src/agent/execution/validation_run.py:128-137` loads existing `correction_geometry_snapped.json` and calls `check_correction()` before rebuilding kernel artifacts.
- Therefore, if the replay guard sees no explicit role-observation capability and emits `NOT_APPLICABLE`, sm21 remains green.
- If it treats absent `room_labels` as an empty strict observation set, existing non-`unknown` roles will trigger the invariant and sm21 will fail.

Full-suite stability expectations:

- Unit tests that instantiate `CorrectedGeometry` directly should stay green if the new field is optional/defaulted or sidecar-only.
- Tests that assert exact legacy role strings may churn if implementation globally canonicalizes `Cell.role`; avoid global canonicalization on legacy/no-provenance paths. Apply aliases at reading/guard boundaries.
- `src/agent/geometry/modelling.py:329-334` still copies `Cell.role` directly into `ZoneVolume`, so any accidental `unknown` rewrite in legacy tests will propagate into `zone_specs`.

Additional implementation note: `src/agent/execution/validation_run.py:131-134` currently passes no reading-label data to `check_correction()`. That is good for legacy N/A by default, but new strict replay needs the validation path to load `0_reading` observations and pass them explicitly; otherwise the invariant will silently never run on replay.

### (b) `role_source_label_id` In Main Correction JSON

Concern: adding a required field to the already-large DeepSeek correction JSON does materially increase malformed-output and retry risk. The correction prompt already asks the LLM to solve cells, world coordinates, z-stack, windows, and audit in one object at `src/agent/pipeline.py:289-306`, and `_call_json_llm()` validates/retries that object through `src/agent/pipeline.py:469-482`. Adding per-cell provenance linkage into this same object couples geometry draw success to a second semantic-binding task.

Concrete recommendation: use a sidecar/post-correction role-binding step, not a required main correction field.

Recommended flow:

1. Keep `CorrectedGeometry` backward-compatible. If a field is added, make it optional with default `None`.
2. Let `1_correction` focus on geometry cells and windows.
3. After `run_correction()` and before `apply_deterministic_core()` at `src/agent/pipeline.py:694-699`, run a small role-binding step that takes corrected cells plus `RoomRoleObservation`s and emits `role_assignments.json`.
4. Sidecar rows should be `{cell_id, role, role_source_label_id, status, note/confidence}`.
5. Deterministically apply the sidecar to `Cell.role` before geometry serialization, then gate the sidecar/materialized roles with the v2 source-exists + role-equality invariant.
6. Persist the sidecar and, if useful for viewer/audit, materialize optional `role_source_label_id` back onto the snapped correction artifact.

This is safer because a malformed binding response only affects role assignment, not the whole geometry draw. It also avoids breaking old correction JSON and keeps the future plan-transform upgrade localized to the binder.

If the team still wants the field in the main correction JSON, make it optional and non-blocking at schema-parse time; enforce it only in the guard when role provenance mode is strict.

### (c) Remaining Blockers

No remaining conceptual blocker after v2, but there are two implementation blockers to resolve before dispatch:

1. Do not make `role_source_label_id` required in the `Cell` schema. Required schema would break legacy artifacts before `NOT_APPLICABLE` can protect them.
2. Define a real provenance-mode switch for legacy vs strict. Raw `room_labels` key presence, explicit run metadata, or migration flags are acceptable; parsed empty defaults are not.

I would dispatch with those changes and the sidecar placement recommendation.

## v3 re-review

Overall verdict: APPROVE-WITH-CHANGES.

The narrowed phase-1 scope is safe enough to dispatch if it stays exactly input-only and optional. It no longer tries to enforce provenance, so it should not disturb legacy replay or the sm21 golden baseline.

### (a) Baseline / Legacy / Full-Suite Safety

Optional `room_labels` is baseline-safe if the new schema field uses a default empty list and the new validator treats empty as pass/no-op.

Grounding:

- v3 specifies `ReadingView` gets `room_labels: list[RoomRoleObservation] = []` at `AI_agent/logs/review/request/2026-06-21_role_to_reading_plan_request.md:78`.
- Current `ReadingView` already uses permissive defaults and `extra="allow"` at `src/agent/reading/schema.py:94-114`, with defaulted list fields at `src/agent/reading/schema.py:101-106`. Adding `room_labels` the same way should let old JSON parse.
- Replay validation loads each `0_reading/*_view.json` and calls `check_reading_view()` at `src/agent/execution/validation_run.py:112-121`.
- Current `check_reading_view()` only runs existing stroke/dimension/facade/uncaptured/dimension-chain checks at `src/validator/checks/reading.py:58-96`. A new room-label check will not affect old runs if it returns pass/not-applicable for `[]`.
- sm21 requires every gate① report to pass at `tests/test_validation_run_baseline.py:199-205`, so any empty-list failure would break the baseline.

Implementation caution: after adding a Pydantic default, `view.room_labels` will exist for legacy artifacts. The validator should check `if not view.room_labels: pass/not_applicable`, not `hasattr(view, "room_labels")`.

### (b) Prompt-Input-Only Stability And Phase-1 Value

This is materially lower risk than v2 because the correction output schema stays unchanged.

Grounding:

- Current `Cell` output remains only `id`, `role`, `x`, and `y` at `src/agent/correction/schema.py:30-37`.
- The correction prompt embeds the `CorrectedGeometry` output schema at `src/agent/pipeline.py:285-287` and asks for room cells `{id, role, x, y}` at `src/agent/pipeline.py:302-305`.
- Reading vectors are already included as prompt input at `src/agent/pipeline.py:326-330`, so adding `room_labels` to those JSONs changes evidence content, not output shape.

This is sufficient phase-1 value if expectations are modest: it gives the image-blind correction LLM explicit image-observed role evidence and should improve cases like visible meeting-room cues. It does not guarantee role correctness because binding remains implicit and unguarded. Phrase the prompt as "prefer high-confidence image-observed roles; fall back when no relevant observation exists" to avoid over-trusting low-confidence furniture cues.

### (c) Remaining Blocker

No remaining blocker for the narrowed phase-1 scope.

Required dispatch notes:

- Keep `room_labels` optional/default-empty.
- Validator must be no-op on empty.
- Do not add `Cell` fields, provenance gates, sidecars, or baseline migration in this phase.
- Add tests for schema parse with and without `room_labels`, empty-list validation, alias normalization, and prompt inclusion when labels exist.
