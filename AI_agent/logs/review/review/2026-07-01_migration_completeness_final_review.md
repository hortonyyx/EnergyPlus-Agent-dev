# Final Migration Completeness Review — Stage 1-5 Scaffold Constraints

Date: 2026-07-01  
Repo: `/workspaces/EnergyPlus-Agent-dev`  
HEAD reviewed: `98ad6b8b6b6cac50f3c38f9a582160408d2a4497`  
Baseline scaffold: `127ba06` `skills/energyplus_mcp_twostep/phase2/{rules.md,prompt_template.md}`  
Mode: local working tree + local git history only. I did not read GitHub and did not execute tests/pipeline.

## GO / NO-GO

**GO.** Relative to `sm21_pre` / `127ba06` phase2, the scaffold-constraint capability migration is **complete under the `validate_case` 口径**: I found **no constraint that was effectively enforced before and is now enforced nowhere**, requiring a from-scratch re-add.

Caveats:

- `run_pipeline` still does not inline the full `check_correction` / `check_mep` gates. That is the known deferred run-pipeline-self-enforcement initiative, not a migration capability loss, because the capstone path runs them.
- Phase-B items `#2` dimension/evidence arbitration, `#3` facade local-to-world wiring, and `#6` non-rectangular/setback policy are not counted as capability losses here. They require a richer correction artifact / dual-channel schema, not a missing migrated check slot.
- `mep.name_charset` is an EP-safe **CROSS_CHECK flag**, not an exact legacy hard block for only letters/digits/underscore. The strict legacy wording still exists in `4_mep/authoring.md`; the code guard now catches non-EP-safe punctuation and exact-reference drift risk. If exact old strictness is desired, that is a tightening request, not a vacuum.

## Capstone Framing Verified

`validate_case` is a non-invasive capstone that reads produced artifacts and runs the full per-stage deterministic gates: `src/agent/execution/validation_run.py:1-9`.

It calls:

- `check_correction` on `1_correction/correction_geometry_snapped.json`: `src/agent/execution/validation_run.py:151-160`
- deterministic kernel rebuild + `check_kernel`: `src/agent/execution/validation_run.py:176-186`
- 2/3 artifact consistency checks: `src/agent/execution/validation_run.py:191-210`
- `check_mep` with `testdata`: `src/agent/execution/validation_run.py:217-221`
- stage-5 assembly backstop: `src/agent/execution/validation_run.py:226-240`
- EP baseline check when present: `src/agent/execution/validation_run.py:242-245`

It is invoked by the baseline/dev paths:

- `record_baseline()` calls `validate_case`: `scripts/tool_scripts/record_baseline.py:305-308`
- geometry approval and approval checks call `validate_case`: `src/agent/execution/step_orchestrator.py:473-476`, `src/agent/execution/step_orchestrator.py:489-491`
- contracts document this design as the M4 capstone that runs full gate ① without modifying `run_pipeline`: `AI_agent/architecture/pipeline_stage_contracts.md:280`

## Per-⚠️ Independent Confirmation Table

| item | second-route concern | independent confirmation | verdict |
|---|---|---|---|
| S1-05 / S1-D | Shared footprint and floor coverage could be silently collapsed. | Final corrected cells are gated by `check_correction()` and `check_coverage()` for no holes/overlap/outside-footprint: `src/validator/checks/correction.py:66-90`, `src/agent/correction/geometry_validator.py:53-90`. `validate_case` calls that gate: `src/agent/execution/validation_run.py:154-160`. Raw per-floor dimension-chain arbitration is Phase-B #2, not a missing migrated gate. | NOT LOST |
| S1-06 / S1-E | Floor heights/z ranges source reconciliation not on `run_pipeline` full gate. | Final z-stack is checked by `check_zstack()`: `src/agent/correction/geometry_validator.py:106-119`; deterministic core snaps/flags z gaps: `src/agent/correction/deterministic.py:764-791`; geometry build raises on broken z-stack: `src/agent/geometry/modelling.py:364-376`. | NOT LOST |
| S1-07 / S1-F | Closed-region topology / coverage gate not inline on production path. | `validate_case` runs `check_correction`; `check_coverage()` enforces tiling: `src/agent/correction/geometry_validator.py:53-90`. Kernel also checks zone closure and internal-interface coverage: `src/validator/checks/kernel.py:93-142`, `src/validator/checks/kernel.py:221-277`. | NOT LOST |
| S1-08 / S1-G | One room/cell per zone can only be as good as correction cells. | Modelling deterministically realizes one `ZoneVolume` per corrected cell: `src/agent/geometry/modelling.py:337-419`. Zone-count tripwire exists: `src/agent/correction/geometry_validator.py:122-136`. J1 covers merged/split/missing rooms: `skills/intake_pipeline/1_correction/judge_rubric.md:18-28`. | NOT LOST; semantic/perceptual limit |
| S1-11 / S1-J | Role assignment from room labels not post-checked against every cell. | Reading validates room-label role vocabulary/basis/anchors: `src/validator/checks/reading.py:196-264`. Correction prompt receives room labels and instructs role preference: `src/agent/pipeline.py:315-317`, `src/agent/pipeline.py:344-352`. Roles are carried into zone names/spec text: `src/agent/geometry/modelling.py:416-418`, `src/agent/geometry/specs.py:174-180`. No deterministic label-to-cell proof exists; this was not an old hard gate. | NOT LOST; semantic/perceptual limit |
| S1-13 / S1-K | Null-as-unknown could become zero after flattening. | Current A0 contract defines `unknown` as absent, completed or flagged: `skills/intake_pipeline/1_correction/A0_contract.md:47-49`; prompt requires conflicts/unsupported/audit for unsafe completion: `src/agent/pipeline.py:309-314`. `CorrectedGeometry` numeric schema rejects nulls in emitted geometry: `src/agent/correction/schema.py:59-74`. Raw-null-to-zero detection belongs to Phase-B #2. | NOT LOST |
| S1-14 / S1-L | Dimension-chain checksum and trust-dimension rule no longer mechanically compare raw dimensions to corrected coords. | Reading gate checks dimension P1a fields and closure: `src/validator/checks/reading.py:462-540`, `src/validator/checks/reading.py:597-694`; A8 projects evidence debt into correction: `src/agent/execution/evidence_preflight.py:90-127`; correction coverage gate checks the final artifact. Full raw-evidence arithmetic into correction output is Phase-B #2. | NOT LOST |
| S1-15 / S1-M | Unsupported geometry could be normalized into a clean box. | Schema carries `unsupported`: `src/agent/correction/schema.py:75-79`; A3 says unresolved conflicts become `unsupported`, never silently fixed: `skills/intake_pipeline/1_correction/A3_arbitration.md:71-74`; deterministic core appends unsupported on envelope/z/window failures: `src/agent/correction/deterministic.py:599-604`, `src/agent/correction/deterministic.py:781-791`, `src/agent/correction/deterministic.py:860-866`. | NOT LOST |
| S1-16 / S1-N | Audit completeness not full A0 strength. | `check_correction()` runs `_audit_completeness()`, requiring sourced corrections/conflicts when geometry changed or testdata was relied on: `src/validator/checks/correction.py:161-204`. Deterministic core logs rule/source/tolerance entries, e.g. envelope reconcile: `src/agent/correction/deterministic.py:666-688`. Full per-transform evidence envelope remains Phase-B refinement, not a vacuum. | NOT LOST |
| S1-17 | Plan/elevation envelope reconcile optional. | Runtime extracts an authoritative envelope from vectors and applies deterministic reconcile: `src/agent/pipeline.py:826-837`, `src/agent/correction/envelope.py:396-407`, `src/agent/correction/deterministic.py:581-698`. `check_correction()` has a cross-image reconcile slot when elevation widths are supplied: `src/validator/checks/correction.py:109-149`. | NOT LOST |
| S23-14 / S23-K | Coverage/no-hole/no-overlap not always inline on `run_pipeline`. | Correction coverage and kernel coverage both exist and are run by `validate_case`: `src/agent/correction/geometry_validator.py:53-90`, `src/validator/checks/kernel.py:221-277`, `src/agent/execution/validation_run.py:154-186`. | NOT LOST |
| S23-L / S1-10 | Non-rectangular/polygon support split between correction and kernel. | Correction schema is rectangular-first but allows future extras: `src/agent/correction/schema.py:8-10`. Kernel is polygon-native: `src/agent/geometry/modelling.py:163-180`; non-rect coverage is explicitly profile-gated/NA pending B5: `src/validator/checks/kernel.py:226-229`. This is Phase-B #6, not a lost sm21 rectangular capability. | NOT LOST |
| S1-C / S1-12 | Facade local-to-world deterministic translator exists but is not wired as sole runtime source. | The translator exists and encodes the facade sign/base convention: `src/agent/correction/facade.py:69-108`. Current correction prompt instructs the same A1 convention: `src/agent/pipeline.py:375-379`, `skills/intake_pipeline/1_correction/A1_coordinate_normalization.md:35-64`. Wiring it into the correction artifact is Phase-B #3. | NOT LOST |
| S4-03 / S4-C | Constructions/material definitions only enforced by `check_mep`, not `run_pipeline`. | `check_mep()` parses the MEP bundle and runs construction coverage/layer checks: `src/validator/checks/mep.py:78-107`, `src/validator/checks/mep.py:337-376`. `validate_case` calls it with `used_constructions`: `src/agent/execution/validation_run.py:217-221`. | NOT LOST |
| S4-04 / S4-D | `WindowMaterial:SimpleGlazingSystem` standalone rule only enforced by `check_mep`. | `_simpleglazing_standalone()` fails multi-layer constructions containing SimpleGlazing: `src/validator/checks/mep.py:481-494`; called by `check_mep()`: `src/validator/checks/mep.py:104`. | NOT LOST |
| S4-06 / S4-F | Schedule completeness not inline on `run_pipeline`; checklist only partly code-gated. | Schedule type refs and day-type completeness are checked: `src/validator/checks/mep.py:379-401`; people activity-level schedule refs are checked in `_load_refs()`: `src/validator/checks/mep.py:417-426`. Full six-schedule presence beyond references remains prompt/default discipline, same capability level as old scaffold. | NOT LOST |
| S4-09 / S4-H | Per-zone people/lights/hvac refs may drift. | `check_mep()` validates load-to-zone and load-to-schedule refs: `src/validator/checks/mep.py:404-441`, with per-zone load coverage flag: `src/validator/checks/mep.py:457-478`. Downstream config reference validation also checks final objects: `src/mcp/state.py:250-329`. | NOT LOST |
| S4-10 | MEP reference graph parser/checks only in validation path. | Unified parser owns MEP IDF fragment parsing: `src/validator/idf_fragments.py:1-13`, `src/validator/idf_fragments.py:120-129`; `check_mep()` uses it before all checks: `src/validator/checks/mep.py:88-93`. | NOT LOST |
| S4-E | Interfloor construction / `Cons_InterFloor` could be bypassed if unused extra constructions exist. | Geometry serializer assigns `Cons_InterFloor` to all interzone horizontal faces: `src/agent/geometry/specs.py:115-131`; MEP authoring requires it and forbids `Default_Floor`/`Default_Ceiling`: `skills/intake_pipeline/4_mep/authoring.md:45-48`; stage-5 contract backstop checks used constructions exist: `src/agent/intakeoutput.py:67-83`. | NOT LOST |
| S4-G / #4 | Office defaults and reasonability bands not value-gated. | Defaults are still centralized: `skills/intake_pipeline/4_mep/mep.md:20-33`; the check slot is explicit `NOT_APPLICABLE`: `src/validator/checks/mep.py:515-520`. Reconciliation marks this intentionally deferred, not a migration vacuum. | NOT LOST; deferred |
| S4-I / #9 | Global MEP name character set was a vacuum. | Fixed at HEAD: `_name_charset()` scans material/construction/schedule/type-limit names and emits `mep.name_charset`: `src/validator/checks/mep.py:183-208`; called by `check_mep()`: `src/validator/checks/mep.py:95-97`. It is a CROSS_CHECK flag by policy: `src/validator/checks/schema.py:143-145`. Strict prompt remains: `skills/intake_pipeline/4_mep/authoring.md:128-132`. | FIXED / NOT LOST |
| S4-J / S4-12 | Placeholder/template prose ban was a true vacuum. | Fixed at HEAD: `_placeholder_ban()` scans parsed MEP IDF fields plus structured building/site names and fails invariant `mep.placeholder_ban`: `src/validator/checks/mep.py:56-75`, `src/validator/checks/mep.py:114-154`; called by `check_mep()`: `src/validator/checks/mep.py:95`. | FIXED / NOT LOST |
| S4-B / #5 | Site/testdata mismatch was prompt-only. | Fixed at HEAD for comparable structured fields: `_site_matches_testdata()` extracts numeric testdata site fields, compares MEP `site_location`, and flags mismatches: `src/validator/checks/mep.py:215-267`. `validate_case` loads testdata and threads it into `check_mep`: `src/agent/execution/validation_run.py:62-70`, `src/agent/execution/validation_run.py:108`, `src/agent/execution/validation_run.py:217-221`. Current anchors only carry `"Building location"` free text, so this correctly reports NA there. | FIXED / NOT LOST |
| S5-05 / S5-D | Cross-field refs distributed and incomplete at stage 5 alone. | Distributed enforcement exists: kernel spec self-consistency checks zone/surface refs: `src/validator/checks/kernel.py:199-218`; MEP checks construction/material/load/schedule refs: `src/validator/checks/mep.py:337-441`; stage-5 assembly backstop re-runs construction coverage: `src/validator/checks/assembly.py:23-40`; downstream validates final config refs: `src/mcp/state.py:250-329`. | NOT LOST |

## Vacuum Fixes at HEAD

The three true-vacuum fixes landed in `98ad6b8` are present and threaded through `validate_case`.

| fix | check | implementation review |
|---|---|---|
| S4-12 placeholder ban | `mep.placeholder_ban` | The banned patterns include `TBD`, `same as above`, `see above`, `etc.`, ellipsis, and angle placeholders: `src/validator/checks/mep.py:56-75`. `_placeholder_ban()` scans parsed IDF object fields and structured `building.name` / `site_location.name`; offenders are INVARIANT failures: `src/validator/checks/mep.py:114-154`. |
| #9 MEP name charset | `mep.name_charset` | `_name_charset()` scans material, construction, schedule, and ScheduleTypeLimits object names: `src/validator/checks/mep.py:41-42`, `src/validator/checks/mep.py:183-208`. It flags outside `[A-Za-z0-9_ -]` as CROSS_CHECK, so it is intentionally EP-safe rather than exact legacy strict. |
| #5 site vs testdata | `mep.site_matches_testdata` | `_site_matches_testdata()` compares structured numeric `latitude`, `longitude`, `time_zone`, `elevation` fields with tolerances and reports NA if no structured fields are present: `src/validator/checks/mep.py:215-267`, `src/validator/checks/mep.py:270-334`. `validate_case` passes `testdata`: `src/agent/execution/validation_run.py:217-221`. |

## Independent Sweep of `127ba06` Phase2

I re-walked `127ba06:skills/energyplus_mcp_twostep/phase2/rules.md` and `prompt_template.md`.

Covered constraint groups:

- Input discipline: image-blind phase2 and every vector JSON/supplement read are preserved by staged correction prompts and `discover_vector_files()`: `src/agent/pipeline.py:77-99`, `src/agent/pipeline.py:287-381`.
- Final 11-field `IntakeOutput`: stage 5 deterministic assembly preserves the same contract: `src/agent/intakeoutput.py:22-57`, `src/agent/state.py:23-66`.
- World coordinates, z-stack, coverage, cell-to-zone, surface orientation, OBC/pairing, window attachment, zero-window, construction, schedule, load refs, cross-field refs, naming, and placeholder constraints are all represented in the table above.
- The old `building` prose mentioned non-schema fields like building type, floor count, and total floor area; the actual `BuildingSchema` at `127ba06` and HEAD is the EnergyPlus `Building` object, not those metadata fields: `127ba06:src/validator/data_model.py:147-181`, HEAD `src/validator/data_model.py:147-181`. I do not count those prose-only/non-schema fields as an effective old enforcement capability.
- `phase2_followup_notes.md` was a manual process instruction, not a model constraint that affects the built EnergyPlus case.

New lost-capability findings: **none**.

## Bottom Line

No remaining genuinely lost scaffold-constraint capability was found relative to `sm21_pre`, under the intended `validate_case` capstone口径. The remaining work is the already-known future work: inline production self-checking for `run_pipeline`, Phase-B evidence/transform/non-rectangular architecture, and optional tightening if exact legacy name strictness is desired.
