# Role And Naming Recon

Date: 2026-06-21
Branch observed: `6.15_ValidationArchM0toM4`
Scope: local tree only. Recon only. No source edits.

## Executive Map

Current room role authority is in `1_correction`, not `0_reading`. The LLM emits `Cell.role` per corrected room cell, the geometry kernel copies that role onto `ZoneVolume`, `serialize_geometry()` writes it into `zone_specs`, and `4_mep` is instructed to use the zone role when authoring per-zone people, lighting, and HVAC specs.

Current zone/cell naming authority is also in `1_correction`. The LLM emits `Cell.id`; geometry code sanitizes that id into the zone name. Surface and window names are code-derived later from the zone name plus surface/window type through `NameRegistry`. Final `IntakeOutput` carries all of these names as plain strings, and downstream agents/tools/validators primarily rely on exact string consistency rather than a structured naming contract.

## ROLE

### 1. Does `0_reading` carry any room role/type field today?

No. `0_reading` has no structured room role/type field today, neither per-room nor per-cell.

Relevant schema:

- `src/agent/reading/schema.py:35-43` defines `Stroke` with `id`, `pen`, `geometry`, and optional `note`. There is no room role/type field.
- `src/agent/reading/schema.py:46-66` defines `DimensionRole` and `Dimension.role`; this is a dimension-chain role (`overall`, `segment`, `baseline`), not room role/type.
- `src/agent/reading/schema.py:94-114` defines `ReadingView` with image metadata, strokes, dimensions, OCR text, uncaptured items, self-check, facade metadata, and migration flags. There is no per-room/per-cell role/type.

Relevant reading-stage guidance:

- `skills/intake_pipeline/0_reading/guide.md:32-36` says reading should trace visible components and geometry, while room grouping/topology are outside the reading stage.
- `skills/intake_pipeline/0_reading/guide.md:174-177` says OCR text labels should be transcribed verbatim into `ocr_texts`; this is unstructured text, not a modeled room role.
- `skills/intake_pipeline/0_reading/guide.md:229-239` leaves room enclosure, window parent assignment, and wall interior/exterior decisions to `1_correction`.

Validator evidence:

- `src/validator/checks/reading.py:241-244` consumes `Dimension.role` only for dimension-chain closure checks. This confirms the current `role` in reading validation is dimension role, not room role.

Conclusion: the only reading-stage carrier that might mention room type today is raw OCR text in `ReadingView.ocr_texts`, but that is not per-room/per-cell and is not authoritative.

### 2. In `1_correction`, where is room role/type defined and emitted?

Room role/type is a correction-stage LLM output field on each corrected cell.

Schema:

- `src/agent/correction/schema.py:30-37` defines `class Cell` with:
  - `id: str`
  - `role: str = "office"`
  - `x: List[float]`
  - `y: List[float]`
- `src/agent/correction/schema.py:67-79` defines `CorrectedGeometry`, whose `floors` contain `Floor.cells`; therefore `Cell.role` is part of the correction output payload.

Prompt construction and population:

- `src/agent/pipeline.py:285-287` embeds `CorrectedGeometry.model_json_schema()` into the correction prompt.
- `src/agent/pipeline.py:289-306` describes the required correction JSON, and `src/agent/pipeline.py:302` specifically instructs: “Each room is one rectangular cell {id, role, x:[min,max], y:[min,max]}.”
- `src/agent/pipeline.py:326-330` passes test data and each reading vector JSON to the correction LLM.
- `src/agent/pipeline.py:474-484` parses the LLM response and validates it as `CorrectedGeometry`.
- `src/agent/pipeline.py:491-494` writes the correction output to `1_correction/correction_geometry.json` when `out_dir` is present.

Correction-stage semantic guidance:

- `skills/intake_pipeline/1_correction/A0_contract.md:58-65` gives semantic authority guidance for room type, prioritizing labels/OCR over repeated layout pattern and priors.
- `skills/intake_pipeline/1_correction/A3_arbitration.md:41-53` discusses building/space-type priors and says high-confidence labels should be preserved.

Conclusion: room role is currently an LLM-authored, per-cell correction field.

### 3. Who consumes role downstream?

Role flows into the geometry kernel, serialized geometry specs, final intake output, and the MEP prompt. It is not a structured field in `IntakeOutput`; it is carried as text inside `zone_specs` and then indirectly influences MEP-authored specs.

Geometry kernel:

- `src/agent/geometry/modelling.py:50-64` defines `ZoneVolume` with `role: str = "office"`.
- `src/agent/geometry/modelling.py:329-334` creates each `ZoneVolume` from a corrected cell and copies `getattr(c, "role", "office") or "office"` into `ZoneVolume.role`.

Serialized geometry:

- `src/agent/geometry/specs.py:121-142` writes `zone_specs`; `src/agent/geometry/specs.py:137-140` emits each zone line with `role: {zv.role}.`

MEP authoring:

- `src/agent/pipeline.py:517-545` builds the `4_MEP` prompt, and `src/agent/pipeline.py:540-541` passes the exact serialized `zone_specs` as the “ZONE LIST”.
- `skills/intake_pipeline/4_mep/authoring.md:18-26` says the MEP stage receives a serialized zone list containing “names + role per zone”.
- `skills/intake_pipeline/4_mep/authoring.md:123-126` instructs `4_MEP` to assign people, lights, and HVAC per zone using defaults from `mep.md` according to the zone’s role.
- `skills/intake_pipeline/4_mep/mep.md:24-27` currently seeds office defaults for people density and lighting power density.
- `skills/intake_pipeline/4_mep/mep.md:42-43` says future loads by space type are placeholders, not expanded yet.

Final intake output:

- `src/agent/intakeoutput.py:36-57` assembles final `IntakeOutput` by copying `zone_specs` into the final object.
- `src/agent/state.py:40-66` defines `IntakeOutput`; it has `zone_specs`, `people_specs`, `lights_specs`, `hvac_specs`, and related text fields, but no structured room-role field.

Downstream agent consumers:

- `src/agent/nodes/zone.py:36-37` gives `zone_specs` to the zone agent. Role text is present in the prompt input, but this node’s prompt focuses on zone names, z origin, and height.
- `src/agent/nodes/surface.py:108-114` gives `zone_specs` and `surface_specs` to the surface agent. It uses exact zone names and geometry references; role is only incidental text.
- `src/agent/nodes/schedule.py:115-124` reads schedule, HVAC, people, and lights specs. Role reaches it only if `4_MEP` encoded role-driven choices into those specs.
- `src/agent/nodes/people.py:46-49` reads `people_specs`, not `zone_specs`; role is only indirect through MEP-authored people specs.
- `src/agent/nodes/lights.py:47-50` reads `lights_specs`, not `zone_specs`; role is only indirect through MEP-authored lights specs.
- `src/agent/nodes/hvac.py:49-50` reads `hvac_specs`, not `zone_specs`; role is only indirect through MEP-authored HVAC specs.

Validation and tooling:

- `src/validator/checks/mep.py:21-23` frames MEP checks as name binding, construction existence, and basic reasonability, not role-specific load validation.
- `src/validator/checks/mep.py:228-233` contains a placeholder reasonability check and does not enforce role-specific density values.
- `scripts/tool_scripts/render_corrected_geometry.py:30-39` and `scripts/tool_scripts/render_corrected_geometry.py:104-112` color corrected cells by `c["role"]`.
- `scripts/tool_scripts/render_geometry_viewer.py:535-557` discovers roles by reading sibling `1_correction/correction_geometry.json` and matching `cell.id` to zone name.
- `scripts/tool_scripts/render_geometry_viewer.py:561-569` embeds discovered roles in the viewer data.

Conclusion: role does drive the MEP authoring prompt today, but mostly as prompt text. It is not preserved as a structured downstream contract field after `zone_specs`, and validators do not currently prove role-specific loads were applied.

### 4. How does identity flow reading -> correction today?

Correction receives reading output as raw per-image vector JSON text, then re-derives rooms/cells. There is no structured per-cell identity flowing from reading to correction.

Evidence:

- `src/agent/pipeline.py:326-330` reads all vector JSON files discovered for correction and embeds each file’s contents in the correction prompt.
- `src/agent/pipeline.py:302` instructs the correction LLM to produce room cells with `{id, role, x, y}`. Since reading has no room/cell objects, these cells are inferred at correction time.
- `skills/intake_pipeline/0_reading/guide.md:229-239` explicitly assigns room enclosure/topology decisions to correction rather than reading.

Current seam options:

- Cleanest schema seam: add a structured reading artifact under `src/agent/reading/` for room labels/roles, then include it in `ReadingView`; the correction prompt already receives the full reading JSON via `src/agent/pipeline.py:326-330`, so it can be instructed to consume and preserve reading-sourced role.
- Cleanest pipeline seam if role mapping already exists: after `run_correction()` and before `apply_deterministic_core()` in the pipeline path at `src/agent/pipeline.py:697-723`, overwrite or lock `Cell.role` from a reading-sourced role map.

Blocker for a pure postprocessor today: `0_reading` has no stable per-cell identity. If reading remains topology-blind, the new role artifact likely needs to be a label/anchor/region observation that correction maps to generated cells, or reading must start producing room regions/cells.

## NAMING

### 5. Where do zone/cell ids originate?

Zone/cell ids originate as LLM output in `1_correction`, then zone names are sanitized from those ids by code.

Correction schema and prompt:

- `src/agent/correction/schema.py:30-37` defines `Cell.id` as part of the LLM-output corrected cell.
- `src/agent/correction/schema.py:40-50` defines `Window.id` and `Window.room`; `Window.room` references the room/cell id.
- `src/agent/correction/schema.py:59-64` defines `Floor.name`; floor names are also correction output, though downstream deterministic naming can use floor order/index instead.
- `src/agent/pipeline.py:302-305` instructs the correction LLM to emit each room’s `{id, role, x, y}` and each window’s `room id`.

Evidence that ids are treated as correction-authored identifiers:

- `src/agent/pipeline.py:390-400` has duplicate-cell-id drawing checks, which only make sense because correction output can supply duplicate ids.
- `src/agent/correction/deterministic.py:611-622` builds `cell_by_id` keyed by `c.id` and raises on duplicate cell ids.
- `src/agent/geometry/modelling.py:289-308` guards global cell id uniqueness and sanitized EnergyPlus-safe zone-name collisions.

Zone name generation:

- `src/agent/geometry/modelling.py:330-334` creates `ZoneVolume` with `zone = _safe(c.id)` and `cell_id = c.id`.
- `src/agent/geometry/build.py:35-37` sets `out.zones = [zv.zone for zv in zvs]`.

Conclusion: current zone names are deterministic only after accepting the LLM-provided `Cell.id`. They are not deterministically generated from floor, role, direction, or sequence.

### 6. Where are surface and window names derived?

Surface and window names are code-derived in the geometry kernel from current zone names.

Name registry and sanitization:

- `src/agent/geometry/modelling.py:75-89` defines `NameRegistry.uname(base)`, which sanitizes a base name and appends `_2`, `_3`, etc. on collisions.
- `src/agent/geometry/modelling.py:95-97` defines `_safe`, which replaces every non-`[A-Za-z0-9_]` character with `_`.

Surface derivation:

- `src/agent/geometry/split_pairing.py:38-44` defines local `add(zone, stype, verts, ...)` and creates each surface with `registry.uname(f"{zone}_{stype}")`.
- `src/agent/geometry/split_pairing.py:69-71` creates paired same-floor interzone wall surfaces and sets each `obc_obj` to the reciprocal generated surface name.
- `src/agent/geometry/split_pairing.py:93-115` creates floor/interfloor ceiling surfaces via `add(zone, "Floor", ...)` and `add(zone, "Ceiling", ...)`, then sets reciprocal `obc_obj` names.
- `src/agent/geometry/split_pairing.py:132-137` creates roof surfaces via `add(zone, "Roof", ...)`.

Window derivation:

- `src/agent/geometry/modelling.py:355-377` attaches windows after finding a parent wall; `src/agent/geometry/modelling.py:376` names each window with `registry.uname(f"{zone}_Win")`.

Serialization:

- `src/agent/geometry/specs.py:23-45` serializes the kernel-produced surface and window names into `building_geometry_dict`.
- `src/agent/geometry/specs.py:115-211` writes zone, surface, and window names verbatim into markdown specs.

Conclusion: surface/window names are already generated by code, but their base strings inherit nondeterminism from the LLM-originated zone names.

### 7. What naming flows into `IntakeOutput`, and what downstream risk exists?

The `IntakeOutput` contract is structural and text-based. Renaming zone/surface/window strings should not by itself break the 11-field `IntakeOutput` schema, but it can break exact cross-reference consistency, generated agent outputs, viewer tooling, fixtures, and prompts that currently require underscore-only names.

Fields and assembly:

- `src/agent/state.py:23-66` defines the final intake output shape. It has exactly 11 text fields:
  `zone_specs`, `material_specs`, `construction_specs`, `surface_specs`, `fenestration_specs`, `schedule_specs`, `hvac_specs`, `people_specs`, `lights_specs`, `infiltration_specs`, and `equipment_specs`.
- `src/agent/intakeoutput.py:36-57` assembles final `IntakeOutput` by stitching together geometry specs and MEP specs.
- `src/agent/geometry/specs.py:121-142` writes `zone_specs` and states that zone names are referenced literally by `surface_specs`, `fenestration_specs`, `people_specs`, `lights_specs`, and `hvac_specs`.
- `src/agent/geometry/specs.py:146-181` writes `surface_specs` with exact zone names, surface names, adjacent zone names, and adjacent surface names.
- `src/agent/geometry/specs.py:195-208` writes `fenestration_specs` with exact window names and exact parent surface names.

Downstream graph:

- `src/agent/graph.py:58-64` adds the intake, zone, material, schedule, construction, surface, fenestration, HVAC, people, and lights nodes.
- `src/agent/graph.py:92-110` wires the graph so generated geometry and MEP names flow through downstream subagents.

Downstream exact-name consumers:

- `src/agent/nodes/zone.py:9-20` tells the zone agent to create zones from zone specs. `src/agent/nodes/zone.py:13-14` currently documents an underscore naming convention like `{floor}_{usage}_{direction}`.
- `src/agent/nodes/zone.py:36-37` sends `intake_output.zone_specs` to the zone agent.
- `src/agent/nodes/surface.py:57-71` tells the surface agent to use exact zone and construction names and exact verbatim references.
- `src/agent/nodes/surface.py:86-87` documents an underscore-oriented naming convention.
- `src/agent/nodes/surface.py:108-114` sends exact `zone_specs`, `construction_specs`, and `surface_specs` to the surface agent.
- `src/agent/nodes/fenestration.py:26-45` tells the fenestration agent to use exact parent surface names; `src/agent/nodes/fenestration.py:44` still documents an old window naming pattern.
- `src/agent/nodes/people.py:13-24` tells the people agent to use exact zone names and to name objects `{zone}_People`.
- `src/agent/nodes/lights.py:13-24` tells the lights agent to use exact zone names and to name objects `{zone}_Lights`.
- `src/agent/nodes/hvac.py:14-33` tells the HVAC agent to use exact zone and schedule names.

Tool exact-name consumers:

- `src/agent/tools/zone_tools.py:12-39` creates EnergyPlus zones using exact provided names.
- `src/agent/tools/zone_tools.py:41-49` lists created zone names.
- `src/agent/tools/surface_tools.py:12-57` creates surfaces using exact zone, construction, outside-boundary, and adjacent-surface names.
- `src/agent/tools/surface_tools.py:75-82` lists created surfaces by exact name.
- `src/agent/tools/fenestration_tools.py:13-50` creates windows using exact parent surface names.
- `src/agent/tools/fenestration_tools.py:68-75` lists created fenestration objects by exact name.
- `src/agent/tools/people_tools.py:13-49` creates people objects with exact zone and schedule names.
- `src/agent/tools/people_tools.py:61-69` lists people objects by exact name.
- `src/agent/tools/lights_tools.py:13-49` creates lights objects with exact zone and schedule names.
- `src/agent/tools/lights_tools.py:61-69` lists lights objects by exact name.
- `src/agent/tools/hvac_tools.py:35-53` creates thermostats with exact zone and schedule names.
- `src/agent/tools/hvac_tools.py:75-83` lists thermostats by exact name.

Validator exact-name consumers:

- `src/validator/checks/mep.py:140-167` checks load-zone references by exact string membership in zone names.
- `src/validator/checks/mep.py:170-191` checks per-zone MEP coverage by exact zone name.
- `src/validator/checks/kernel.py:194-213` checks surface `zone`, adjacent `obc_obj`, and related references by exact names.
- `src/validator/interzone.py:124-189` checks reciprocal interzone surface references by exact surface names.
- `src/agent/intakeoutput.py:60-83` checks construction coverage by exact construction names; this is not directly zone naming, but it shows the final assembly layer uses exact text matching.

Validation artifact risk:

- `src/agent/execution/validation_run.py:139-152` rebuilds `building_geometry.json` and serialized geometry specs during validation.
- `src/agent/execution/validation_run.py:154-168` requires stored `building_geometry.json` to equal the deterministic rebuild.
- `src/agent/execution/validation_run.py:172-180` requires `geometry_specs.md` to byte-equal serializer output.

Naming-rule conflict:

- `skills/intake_pipeline/4_mep/authoring.md:128-131` says names must use only letters, digits, and `_`; no hyphens.
- `src/agent/geometry/modelling.py:95-97` currently converts hyphens to `_`.

Viewer risk:

- `scripts/tool_scripts/render_geometry_viewer.py:535-557` assumes roles can be recovered by matching correction `cell.id` to final zone names.
- If deterministic zone names diverge from correction `Cell.id`, this role lookup will become stale unless `building_geometry.json` carries role directly or a mapping is added.

Conclusion: changing zone/surface/window name strings should not break the 11-field `IntakeOutput` shape, but all exact references must change atomically across `zone_specs`, `surface_specs`, `fenestration_specs`, MEP specs, generated EnergyPlus objects, validators, viewers, and fixtures. The literal hyphenated convention `floor-type-direction-sequence` conflicts with current sanitization and MEP authoring rules unless those rules are intentionally changed.

### 8. Natural insertion point for deterministic `floor-type-direction-sequence`

Zone name generation naturally belongs after correction has been normalized by deterministic core and before serialized specs are built.

Best zone insertion point:

- `src/agent/pipeline.py:697-723` runs correction, applies deterministic core, then materializes kernel geometry.
- `src/agent/geometry/modelling.py:274-334` builds `ZoneVolume` objects from snapped `CorrectedGeometry`. At this point, the code has:
  - floor order/index (`fi` in the floor loop),
  - room role/type (`c.role`),
  - cell coordinates and polygon (`_cell_polygon(c)`),
  - stable geometry order after deterministic core,
  - internal source `cell_id`.

This is the natural point to mint deterministic zone names while preserving original `cell_id` for internal lookup.

Surface insertion point:

- `src/agent/geometry/split_pairing.py:38-44` is the natural place to derive deterministic surface names because surface type, owning zone, vertices, and registry collision state are available when each surface is created.
- `src/agent/geometry/split_pairing.py:69-71` and `src/agent/geometry/split_pairing.py:93-115` are where reciprocal adjacent-surface references are set, so deterministic surface names must be generated before those reciprocal references are assigned.

Window insertion point:

- `src/agent/geometry/modelling.py:355-377` is the natural place to generate deterministic window names because parent wall/facade and owning zone are known only after `_find_parent_wall()`.

Compass-direction note:

- For zone naming, the compass direction can be computed from world-coordinate centroids once corrected geometry is snapped and scaled in `build_zone_volumes()`.
- For exterior surface and window naming, direction should be computed from wall/window geometry after surfaces exist. The existing geometry module already has normal-related helpers such as `src/agent/geometry/modelling.py:21-26` (`_FACADE_NORMAL`) and `src/agent/geometry/modelling.py:156-170` (`_newell`).
- Floors, ceilings, roofs, and interzone surfaces need an explicit naming policy because compass direction is less directly meaningful than for exterior walls/windows.

Internal identity caution:

- `src/agent/geometry/build.py:45-46` builds `zv_by_cell = {zv.cell_id: zv}` and resolves windows by `Window.room`.
- If deterministic naming rewrites `Cell.id` itself, then all `Window.room` references must be rewritten consistently.
- Safer implementation shape: retain correction `Cell.id` as internal source identity and generate deterministic public `zone` names separately.

## Test And Fixture Assertions To Update

The following are local `tests/` files and fixtures that assert, encode, or rely on specific name strings or role values. They are likely update candidates for deterministic naming and/or role relocation.

### Direct unit tests

- `tests/test_zone_agent.py:16` and `tests/test_zone_agent.py:30` use exact zone names `F1_Office` and `F1_Corridor`.
- `tests/test_intakeoutput_assembly.py:21-30` builds fixtures with exact cell ids `F1_L`, `F1_R`, `F2_L`, `F2_R`, roles `office`/`corridor`, and window id `W1`.
- `tests/test_intakeoutput_assembly.py:39-42` asserts exact zone strings and `"role: corridor"` in `zone_specs`.
- `tests/test_intakeoutput_assembly.py:46-48`, `tests/test_intakeoutput_assembly.py:52`, `tests/test_intakeoutput_assembly.py:55-56`, `tests/test_intakeoutput_assembly.py:102-110`, and `tests/test_intakeoutput_assembly.py:113-120` assert exact construction names. These are not zone names but may be affected by any broad naming cleanup.
- `tests/test_intakeoutput_assembly.py:64-74` asserts exact toy zone strings `A` and `B` in specs.
- `tests/test_geometry_kernel.py:22-29`, `tests/test_geometry_kernel.py:36-44`, `tests/test_geometry_kernel.py:52-61`, `tests/test_geometry_kernel.py:69-79`, `tests/test_geometry_kernel.py:86-93`, `tests/test_geometry_kernel.py:100-106`, `tests/test_geometry_kernel.py:125-144`, `tests/test_geometry_kernel.py:155-173`, and `tests/test_geometry_kernel.py:183-195` build fixtures with exact cell ids, roles, and window room refs.
- `tests/test_geometry_kernel.py:79` asserts there is a `Roof` surface in zone `F1_A`.
- `tests/test_geometry_kernel.py:156`, `tests/test_geometry_kernel.py:159`, and `tests/test_geometry_kernel.py:168-170` assert or inspect role literals.
- `tests/test_geometry_kernel.py:183-185` relies on exact window room refs.
- `tests/test_kernel_guards.py:47-73` tests duplicate/collision behavior with exact ids `Corridor`, `Room`, `Room 1`, and `Room_1`.
- `tests/test_kernel_guards.py:81-117`, `tests/test_kernel_guards.py:123-166`, and `tests/test_kernel_guards.py:172-231` use exact cell/window ids such as `F1_A`, `F2_A`, and `W1`.
- `tests/test_kernel_guards.py:160-166` asserts an exact parent-name map.
- `tests/test_kernel_guards.py:181` and `tests/test_kernel_guards.py:194` assert exact target `W1` behavior.
- `tests/test_geometry_viewer.py:18-28` and `tests/test_geometry_viewer.py:45` use exact names `Z1`, `Z2`, `w1`, `w2`, and `win1`.
- `tests/test_geometry_viewer.py:80-83` asserts exact role map `{"Z1": "office", "Z2": "corridor"}`.
- `tests/test_geometry_viewer.py:103-107` asserts exact role discovery `{"A": "office", "B": "meeting"}`, depending on `cell.id == zone name`.
- `tests/test_gt_from_dxf.py:40-47` asserts exact GT zone ids `F1_S3`, `F1_N1`, `F1_COR`, `F2_N1`, `F2_N2`, `F2_S1` and roles `meeting`, `office`, and `corridor`.
- `tests/test_gt_render.py:72-73` uses exact fixture id `Z1` and role `office`.
- `tests/test_checks_kernel.py:81-82` uses exact zone `Z1`/`ZoneVolume`; `tests/test_checks_kernel.py:69` uses exact `Does_Not_Exist`.
- `tests/test_checks_mep_assembly.py:42-43`, `tests/test_checks_mep_assembly.py:54`, `tests/test_checks_mep_assembly.py:70`, `tests/test_checks_mep_assembly.py:76`, `tests/test_checks_mep_assembly.py:113-114`, and `tests/test_checks_mep_assembly.py:123` use exact `Default_*`, `Cons_*`, `Z1`, and `Cons_Missing` references.
- `tests/test_idf_fragments.py:29`, `tests/test_idf_fragments.py:48`, `tests/test_idf_fragments.py:51`, and `tests/test_idf_fragments.py:59` use exact `Default_Ext_Wall` and `Z1`.
- `tests/test_merge.py:8-14`, `tests/test_merge.py:19-25`, `tests/test_merge.py:48`, `tests/test_merge.py:63`, and `tests/test_merge.py:73` use exact toy identities `A`, `B`, `S1`, and `S2`.
- `tests/test_deterministic_core.py:39-49`, `tests/test_deterministic_core.py:62-68`, `tests/test_deterministic_core.py:81-88`, `tests/test_deterministic_core.py:103`, `tests/test_deterministic_core.py:132`, `tests/test_deterministic_core.py:150-172`, `tests/test_deterministic_core.py:179-199`, and `tests/test_deterministic_core.py:206-210` use exact cell ids such as `F1_A`, `F2_0`, `A`, and `B` and exact window room references.
- `tests/test_pipeline_kernel_wiring.py:17-22` and `tests/test_pipeline_kernel_wiring.py:47-49` use exact fixture ids `F1_L`, `F1_R`, `F2_L`, `F2_R`, `Room`, and `Corridor`.
- `tests/test_correction_stability.py:79`, `tests/test_correction_stability.py:87-88`, `tests/test_correction_stability.py:237-247`, `tests/test_correction_stability.py:263-283`, and `tests/test_correction_stability.py:324-344` use exact correction cell ids and role literals such as `office`.
- `tests/test_correction_stability.py:252`, `tests/test_correction_stability.py:270`, `tests/test_correction_stability.py:329`, and `tests/test_correction_stability.py:339` assert generic error messages around duplicate ids, overlaps, or bounds; they may need only minor updates if error text changes.
- `tests/test_checks_reading_correction.py:98-106` asserts dimension roles `overall` and `segment`; this is not room role but is a role-named field to avoid conflating during refactor.
- `tests/test_checks_reading_correction.py:137` checks correction window-on-wall validation.
- `tests/test_checks_reading_correction.py:143-148` and `tests/test_checks_reading_correction.py:155-169` use exact toy cell ids `A`, `B`, `F1`, and `F2`.
- `tests/test_schedule_completeness.py:72-81` uses exact schedule names such as `Office_People_Number`; this is not geometry naming but is an exact role-ish MEP naming string.
- `tests/test_interzone.py:67-71`, `tests/test_interzone.py:92-129`, and `tests/test_interzone.py:152` use exact fake surface/zone names such as `F2_Floor`, `F1_Ceiling`, `A`, `B`, `C`, `Sliver`, and `Partner`.
- `tests/test_validation_run_baseline.py:138` uses exact bogus zone `BogusZone`; `tests/test_validation_run_baseline.py:214-216` assert counts but may need artifact fixture updates.
- `tests/test_orchestrate_baseline.py:94` asserts counts only, but baseline artifacts may still need updates if stored names change.

### Fixtures

- `tests/fixtures/validation/bad_2f_corridor_split.json:11-16` contains exact ids `F2_N`, `F2_S`, `F2_CORR_1`, `F2_CORR_2`, `F2_CORR_3`, `F2_CORR_4` and roles `office`/`corridor`.
- `tests/fixtures/validation/wrong_facade_window.json:11-18` contains exact ids `F1_SW`, `F1_REST`, `F1_N`, `W_BAD`, roles `office`, and window room reference `F1_SW`.
- `tests/fixtures/validation/self_consistent_wrong_dimension.json:10-14` contains dimension roles `overall` and `segment`; this is not room role but is a role-named field.
- `tests/fixtures/validation/bad_mep_semantics.json:6` and `tests/fixtures/validation/bad_mep_semantics.json:9-10` use exact `Default_Ext_Wall` and `Z1` references.

## Review-Asks / Uncertain Conclusions

1. Re-verify the local EnergyPlus/tooling stance on hyphens. The requested convention uses hyphens, but `_safe()` currently replaces hyphens with `_`, and `4_mep/authoring.md` explicitly says no hyphens.
2. Re-verify whether any downstream code outside the inspected graph path pattern-matches names. The main path appears to use exact string references, but scripts, fixtures, and any external consumers may depend on old underscore formats.
3. Decide whether reading is allowed to emit room regions/cells. Current reading guidance says it should not group rooms/topology, so moving role to reading needs either a new non-topological label/anchor artifact or a deliberate reading-boundary change.
4. Re-verify viewer/reporting requirements. `render_geometry_viewer.py` currently recovers roles through `cell.id == zone name`; deterministic public names will break that assumption unless role or source-id mapping is serialized.
5. Add or update validation if role-specific MEP loads are important. Today MEP is prompted to use roles, but validators do not enforce role-specific density choices.
