# Final Review: definitive standard test flow design (§8)

Date: 2026-07-02
Reviewer: Codex
Proposal: `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md`
Prior review: `AI_agent/logs/review/review/2026-07-02_standardize_test_flow_review.md`

## Verdict

**GO, with must-fix-during-build constraints.**

The §8 expansion is directionally sound and feasible against the current code. It correctly turns the proposed `flow` verb from a command wrapper into the authoritative formal-run harness: gate1, judge, optional outer human review, resampling, downstream invalidation, EP, baseline/report.

The main new risks are implementation shape, not design blockers:

1. The gt coordinate scorer must become authoritative judge evidence, not a replacement for the `StageVerdict` structured checklist.
2. J23 requires a small orchestration refactor because the current geometry approval gate fires before any possible judge on `3_split_pairing`.
3. Reading/correction human review gates need durable approval state or a resumable acknowledgement mechanism; otherwise `flow` will stop repeatedly after every existing `JUDGE_PASS`.
4. Product-vs-gt overlays must share a metric transform, not composite existing renderer PNGs with different scales/margins.

I recommend **P1 first, then P2**. P1 is already a large harness change touching orchestration, scoring evidence, overlays, EP layout, exit codes, and guide docs. P2 adds a new judge stage plus a nontrivial geometry scorer and should land as a second build pass unless the next round is explicitly split into two commits/review gates.

## §8 New Items

### 1. Coordinate-vs-gt scorer wired into judge

Feasible, moderately invasive.

Current state:

- `score_reading_vs_gt` exists only as judge-side scorer code, not judge harness wiring: `src/agent/judge/reading_score.py:1`, `src/agent/judge/reading_score.py:10`, `src/agent/judge/reading_score.py:283`.
- The CLI wrapper is standalone and can emit JSON: `scripts/tool_scripts/score_reading_vs_gt.py:61`, `scripts/tool_scripts/score_reading_vs_gt.py:69`, `scripts/tool_scripts/score_reading_vs_gt.py:97`.
- `run_stage.py` judge packets currently include only source images, best-effort renders, `gt_path`, and gate1 flags: `scripts/tool_scripts/run_stage.py:387`, `scripts/tool_scripts/run_stage.py:394`, `scripts/tool_scripts/run_stage.py:395`, `scripts/tool_scripts/run_stage.py:402`, `scripts/tool_scripts/run_stage.py:407`.
- The main-agent judge model is packet/submitted-verdict based: `cmd_judge()` loads a user/model-authored verdict JSON and calls `submit_verdict()`: `scripts/tool_scripts/run_stage.py:515`, `scripts/tool_scripts/run_stage.py:527`, `scripts/tool_scripts/run_stage.py:532`.
- `submit_verdict()` persists `attempts/NNN/judge.json` and classifies by `StageVerdict`: `src/agent/execution/step_orchestrator.py:336`, `src/agent/execution/step_orchestrator.py:347`, `src/agent/execution/step_orchestrator.py:355`, `src/agent/execution/step_orchestrator.py:359`.
- `StageVerdict` is explicitly a structured checklist, not a numeric score, and forbids extra fields: `src/agent/judge/verdict.py:3`, `src/agent/judge/verdict.py:40`, `src/agent/judge/verdict.py:48`, `src/agent/judge/verdict.py:51`, `src/agent/judge/verdict.py:55`.

Assessment:

- Wiring the scorer into `judge_packet` is clean: `_judge_packet()` already imports gt only inside the judge path (`scripts/tool_scripts/run_stage.py:389`) and writes packet sidecars (`scripts/tool_scripts/run_stage.py:410`). Add scorer output and/or a sibling `score_vs_gt.json` there.
- This does not need to change the judge model if the main agent still submits a `StageVerdict`. The score becomes primary evidence inside the packet.
- Do not add raw score fields to `StageVerdict` without a schema migration, because `extra="forbid"` will reject them (`src/agent/judge/verdict.py:51`).
- Must define the relaxed pass/fail mapping. The current scorer returns matches/counts/deltas, not a formal blocking threshold: `src/agent/judge/reading_score.py:65`, `src/agent/judge/reading_score.py:69`, `src/agent/judge/reading_score.py:76`, `scripts/tool_scripts/score_reading_vs_gt.py:90`, `scripts/tool_scripts/score_reading_vs_gt.py:95`. Without explicit threshold policy, "primary" falls back to subjective interpretation.
- For J1 correction scoring, `score_reading_dir()` cannot be reused directly. It globs `*_view.json` and extracts reading strokes (`src/agent/judge/reading_score.py:127`, `src/agent/judge/reading_score.py:175`, `src/agent/judge/reading_score.py:192`, `src/agent/judge/reading_score.py:296`), while correction output is `CorrectedGeometry` cells/windows (`src/agent/correction/schema.py:67`, `src/agent/correction/schema.py:71`, `src/agent/correction/schema.py:73`, `src/agent/correction/schema.py:74`). Build a correction adapter or a sibling scorer.

Verdict schema tension:

The design is reconcilable if "relaxed coordinate score is primary" means:

- scorer output is machine-readable evidence;
- J0/J1/J23 rubric criteria are still populated as `pass/minor/severe/fatal`;
- severe/fatal coordinate misses become criteria evidence and drive `blocking`;
- visual read remains auxiliary evidence for categories the scorer cannot cover.

It is not reconcilable if implemented as "numeric score directly replaces the checklist." That would contradict the current verdict contract (`src/agent/judge/verdict.py:3`) and the J0/J1 rubric text (`skills/intake_pipeline/0_reading/judge_rubric.md:3`, `skills/intake_pipeline/0_reading/judge_rubric.md:6`, `skills/intake_pipeline/1_correction/judge_rubric.md:3`, `skills/intake_pipeline/1_correction/judge_rubric.md:6`).

### 2. Product-vs-gt overlays for 0/1 only

Feasible, but not as simple PNG compositing.

Current render facts:

- `render_gt.py` has a fixed gt metric transform with gt footprint W/D and y-flip: `scripts/tool_scripts/render_gt.py:165`, `scripts/tool_scripts/render_gt.py:170`, `scripts/tool_scripts/render_gt.py:173`, `scripts/tool_scripts/render_gt.py:319`.
- `render_vector_to_png.py` derives its own bounds from reading strokes plus a margin: `scripts/tool_scripts/render_vector_to_png.py:72`, `scripts/tool_scripts/render_vector_to_png.py:74`, `scripts/tool_scripts/render_vector_to_png.py:79`, `scripts/tool_scripts/render_vector_to_png.py:82`.
- `render_corrected_geometry.py` uses correction footprint extents, scale 30, and its own margins: `scripts/tool_scripts/render_corrected_geometry.py:24`, `scripts/tool_scripts/render_corrected_geometry.py:53`, `scripts/tool_scripts/render_corrected_geometry.py:62`, `scripts/tool_scripts/render_corrected_geometry.py:84`, `scripts/tool_scripts/render_corrected_geometry.py:87`.
- Existing gt-over-original overlay solves a different problem: calibrating gt onto original PNGs from pixel density (`scripts/tool_scripts/render_gt_overlay.py:1`, `scripts/tool_scripts/render_gt_overlay.py:10`, `scripts/tool_scripts/render_gt_overlay.py:65`, `scripts/tool_scripts/render_gt_overlay.py:96`).

Assessment:

- Both reading and correction artifacts use world metres, so a product-on-gt overlay is feasible. The current scorer already assumes reading coordinates are in the gt world frame (`src/agent/judge/reading_score.py:253`, `src/agent/judge/reading_score.py:257`, `src/agent/judge/reading_score.py:259`), and correction schema is explicitly world-frame (`src/agent/correction/schema.py:40`, `src/agent/correction/schema.py:47`, `src/agent/correction/schema.py:67`, `src/agent/correction/schema.py:71`).
- The build should draw reading strokes/correction cells into the gt renderer's coordinate functions, or refactor shared plan/elevation transform helpers out of `render_gt.py`.
- Do not alpha-composite `*_render.png`, `zones.png`, or `elev.png` over `gt_plan.png`; those images use different scales, origins, panel layouts, and margins.
- Calibration caveat: gt `rect_m` are clear-space bboxes per the renderer doc (`scripts/tool_scripts/render_gt.py:17`), while corrected/kernel artifacts often carry centerline-ish offsets. Example correction output has footprint `[0.1, 14.9]` and cells starting at `0.1`, while gt is `[0.0, 15.0]`: `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/1_correction/correction_geometry_snapped.json:2`, `case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/1_correction/correction_geometry_snapped.json:15`, `case_tests/test_baseline/gt/sm21_anchor/gt.json:13`, `case_tests/test_baseline/gt/sm21_anchor/gt.json:27`. The overlay should label/tolerate that offset rather than make it look like a hard failure.

### 3. Geometry human review and J23

Feasible. J23 is the main P2 complexity.

Existing geometry viewer:

- `run_stage.py` already generates `manual_review/geometry_viewer.html` from `2_modelling/building_geometry.json`: `scripts/tool_scripts/run_stage.py:348`, `scripts/tool_scripts/run_stage.py:354`, `scripts/tool_scripts/run_stage.py:364`, `scripts/tool_scripts/run_stage.py:366`.
- Reports already reference or regenerate that viewer: `scripts/tool_scripts/report_assembly.py:158`, `scripts/tool_scripts/report_assembly.py:165`, `scripts/tool_scripts/report_assembly.py:167`, `scripts/tool_scripts/report_assembly.py:171`.
- Existing tests assert the viewer appears in reports when geometry is available and is suppressed when unavailable: `tests/test_orchestrate_baseline.py:223`, `tests/test_orchestrate_baseline.py:231`, `tests/test_orchestrate_baseline.py:246`.

So the §8 decision "geometry human review = existing HTML viewer, no new geometry overlay" is sound.

J23 feasibility:

- Current judge registry has no 2/3 judge: only J0, J1, and disabled J4 exist (`src/agent/judge/executor.py:28`, `src/agent/judge/executor.py:29`, `src/agent/judge/executor.py:30`, `src/agent/judge/executor.py:31`, `src/agent/judge/executor.py:32`).
- `run_one_stage()` dispatches an enabled judge for any registered stage after gate1, so adding `3_split_pairing: ("J23", True)` is mechanically possible (`src/agent/execution/step_orchestrator.py:312`, `src/agent/execution/step_orchestrator.py:313`, `src/agent/execution/step_orchestrator.py:319`, `src/agent/execution/step_orchestrator.py:322`).
- But current `_post_gate1()` checks the geometry approval gate before judge dispatch (`src/agent/execution/step_orchestrator.py:301`, `src/agent/execution/step_orchestrator.py:302`, `src/agent/execution/step_orchestrator.py:303`). To make "J23 first, human review second" true, this order must change or `flow` must run J23 under a nonblocking confirmation policy and apply human review outside.
- `3_split_pairing` is the right checkpoint: it is the defined geometry checkpoint stage (`src/agent/execution/step_orchestrator.py:68`), and validation computes a digest only when `building_geometry.json` plus `geometry_specs.md` are consistent (`src/agent/execution/validation_run.py:250`, `src/agent/execution/validation_run.py:255`, `src/agent/execution/validation_run.py:264`).

`score_geometry_vs_gt` feasibility:

- Current `building_geometry.json` has zones, optional `zone_meta`, surfaces with 3D verts, and windows with verts: `src/agent/geometry/specs.py:57`, `src/agent/geometry/specs.py:63`, `src/agent/geometry/specs.py:65`, `src/agent/geometry/specs.py:69`, `src/agent/geometry/specs.py:80`.
- The underlying build model has zone volumes/polygons, surfaces, and windows: `src/agent/geometry/modelling.py:52`, `src/agent/geometry/modelling.py:60`, `src/agent/geometry/modelling.py:69`, `src/agent/geometry/modelling.py:75`.
- Windows can be inferred from verts and facade-normal rules. The same concepts already exist in `_window_verts()` and `_find_parent_wall()`: `src/agent/geometry/modelling.py:273`, `src/agent/geometry/modelling.py:278`, `src/agent/geometry/modelling.py:286`, `src/agent/geometry/modelling.py:301`, `src/agent/geometry/modelling.py:315`.
- GT has verified zones/windows/floors/heights: `case_tests/test_baseline/gt/sm21_anchor/gt.json:9`, `case_tests/test_baseline/gt/sm21_anchor/gt.json:13`, `case_tests/test_baseline/gt/sm21_anchor/gt.json:17`, `case_tests/test_baseline/gt/sm21_anchor/gt.json:175`.

Caveats:

- `building_geometry.json` does not store zone polygons directly; the scorer must reconstruct per-zone XY footprints from floor/roof surfaces or all zone surface verts. That is feasible but more than a mirror-copy of `reading_score.py`.
- Legacy `building_geometry.json` may lack `zone_meta`; current code includes it, but scorer should degrade gracefully or derive floor/role from surfaces/names.
- Matching built zones to gt zones needs area/IoU and role synonym tolerance, not name matching.
- Built geometry can be intentionally centerline-offset vs gt clear-space, so relaxed tolerance is required.

Routing:

The proposed deterministic-root routing is already supported by the current verdict classifier. If a blocking verdict is routable to a deterministic root, it returns `JUDGE_BLOCK_HUMAN`, not a resample: `src/agent/execution/step_orchestrator.py:407`, `src/agent/execution/step_orchestrator.py:434`, `src/agent/execution/step_orchestrator.py:436`, `src/agent/execution/step_orchestrator.py:438`. Adding backlog recording is new, but the no-resample decision is sound.

### 4. Judge switch + human-review switch stack

Conceptually sound, but current code needs explicit outer-gate support.

Current composition points:

- `run_one_stage()` stops at `AWAITING_JUDGE` when an enabled judge has no verdict yet: `src/agent/execution/step_orchestrator.py:312`, `src/agent/execution/step_orchestrator.py:314`, `src/agent/execution/step_orchestrator.py:322`.
- Once a nonblocking verdict exists, `_verdict_outcome()` returns `JUDGE_PASS`: `src/agent/execution/step_orchestrator.py:379`, `src/agent/execution/step_orchestrator.py:390`.
- `StageOutcome.can_advance` is true only for deterministic pass or judge pass: `src/agent/execution/step_orchestrator.py:95`, `src/agent/execution/step_orchestrator.py:117`.

That gives `flow` a clean interception point: after `JUDGE_PASS` or `DETERMINISTIC_PASS`, before advancing to the next stage.

Must-fix during build:

- Add durable human-review state for reading/correction/geometry, or require an explicit one-shot resume flag that is audit-visible. Existing durable approval is geometry-only (`src/agent/execution/approval.py:57`, `src/agent/execution/approval.py:60`, `src/agent/execution/approval.py:62`) and current status enum has no generic `AWAITING_HUMAN_REVIEW`: `src/agent/execution/step_orchestrator.py:72`.
- For geometry, do not leave current approval gate before judge if J23 is enabled. Current order would block at `AWAITING_GEOMETRY_APPROVAL` before J23 could run (`src/agent/execution/step_orchestrator.py:301`, `src/agent/execution/step_orchestrator.py:302`).
- `update_state()` only records geometry/reread/terminal stop reasons; if `flow` introduces new human review checkpoints, the state/report layer must learn them or flow must maintain a separate durable record: `src/agent/execution/step_orchestrator.py:519`, `src/agent/execution/step_orchestrator.py:521`, `src/agent/execution/step_orchestrator.py:523`.

### 5. `new_case_guide.md` SOP rewrite as build deliverable

Correct sequencing.

The current guide still documents the old one-stage verbs and old judge density/no-J23 model: `AI_agent/guides/new_case_guide.md:33`, `AI_agent/guides/new_case_guide.md:88`, `AI_agent/guides/new_case_guide.md:95`, `AI_agent/guides/new_case_guide.md:101`, `AI_agent/guides/new_case_guide.md:143`.

Updating it now would be vaporware. Listing the guide rewrite in §8.10 as a next build deliverable is the right call, because it can describe the actual `flow` flags, scorer sidecars, overlay paths, review checkpoint artifacts, and exit codes after they exist.

### 6. §8.9 decisions

Sound.

- `JUDGE_BLOCK` auto-resample for stochastic roots fits the existing classifier. A routable blocking verdict returns `route_target`, and stochastic roots become `JUDGE_BLOCK`: `src/agent/execution/step_orchestrator.py:399`, `src/agent/execution/step_orchestrator.py:407`, `src/agent/execution/step_orchestrator.py:440`, `src/agent/execution/step_orchestrator.py:442`.
- Manual roots already route to reread/human, not stochastic resample: `src/agent/execution/step_orchestrator.py:408`, `src/agent/execution/step_orchestrator.py:409`, `src/agent/execution/step_orchestrator.py:429`.
- Deterministic roots already route to human/code-defect handling: `src/agent/execution/step_orchestrator.py:434`, `src/agent/execution/step_orchestrator.py:436`.
- Downstream invalidation is required because `cmd_resample()` currently just forces `cmd_run()` and does not call `invalidate()`: `scripts/tool_scripts/run_stage.py:510`, `scripts/tool_scripts/run_stage.py:512`. The invalidation primitive exists: `src/agent/execution/invalidation.py:50`, `src/agent/execution/invalidation.py:58`, `src/agent/execution/invalidation.py:60`.
- `--geometry-approval required` for baseline and explicit auto for regression is correct. Current `RunPolicy` has required/optional/disabled but no auto actor/policy distinction (`src/agent/execution/policy.py:23`, `src/agent/execution/policy.py:40`, `src/agent/execution/policy.py:59`). Current approval persistence hard-codes `policy="required"` (`src/agent/execution/step_orchestrator.py:479`, `src/agent/execution/step_orchestrator.py:480`), so §8.6/§8.9 correctly call this out.

## Prior Required Changes

All six prior required changes are captured in §8.6:

1. `JUDGE_BLOCK` handling and stochastic auto-resample: captured at `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md:157`.
2. Downstream invalidation after force redraw: captured at `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md:158`.
3. No silent J0 skip: captured at `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md:159`.
4. EP option A with shared graph helper preserving config/no-simulate/prebuilt intake behavior: captured at `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md:160`.
5. Geometry auto approval audit-visible and baseline default required: captured at `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md:161`.
6. Scriptable exit codes: captured at `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md:162`.

The prior review's extra record-baseline precondition is also captured: `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md:163`.

No prior required change was dropped. The duplicate numbering in §8.6 is cosmetic only.

## New Risks Introduced by §8

1. **Scorer authority without threshold policy.** `reading_score.py` reports hits/misses/extras, but not verdict severity. Build must define relaxed threshold-to-criterion mapping. Otherwise "primary pass/fail driver" is underspecified.
2. **Numeric-score drift from verdict schema.** Keep scorer output as evidence feeding `criteria[]`; do not replace `StageVerdict` with a pass percentage.
3. **J1 correction scoring adapter missing.** Current scorer is reading-stroke specific and cannot directly parse `CorrectedGeometry`.
4. **Geometry judge order conflict.** Current geometry approval runs before judge dispatch on stage 3. J23 needs judge-before-human ordering.
5. **Outer human review durability.** Reading/correction review gates have no durable approval artifact today.
6. **Overlay transform mismatch.** Existing renderer images use incompatible transforms. New overlay should share a metric transform, not raster-composite outputs.
7. **GT isolation discipline.** All `score_*_vs_gt` code must remain under judge/tooling. Gate1 validators and executors are mechanically expected not to import gt: `tests/test_gt_discipline.py:1`, `tests/test_gt_discipline.py:50`, `tests/test_gt_discipline.py:57`.

## Must-Fix During Build

1. Add machine-readable scorer sidecars to judge packets and define relaxed threshold-to-criterion mapping for J0/J1.
2. Keep `StageVerdict` as the routing/disposition authority; use scorer output as primary evidence inside checklist criteria.
3. Implement a correction scorer adapter for `correction_geometry_snapped.json`.
4. Implement product-on-gt overlays using a shared metric transform, not PNG compositing.
5. For J23, add the rubric registration and reorder/wrap the stage-3 geometry gate so J23 can run before human geometry review.
6. Add durable human-review checkpoint records for reading/correction/geometry or an equivalent audit-visible resume mechanism.
7. On any force redraw or judge-driven resample, call `invalidate()` for downstream manifest pointers before continuing.
8. Add tests for exit codes, scorer-in-packet evidence, downstream invalidation, J23 deterministic-root routing, geometry auto audit fields, and post-judge human-review resume.

## P1/P2 Recommendation

Build **P1 first**, then P2.

P1 already produces a useful formal flow: `flow`, EP layout fix, exit codes, J0/J1 scorer evidence, 0/1 overlays, geometry auto audit visibility, and guide rewrite.

P2 should follow once the harness is stable: J23, `score_geometry_vs_gt`, deterministic-root backlog routing, and any static geometry PNG exports needed for the J23 packet. P2 changes judge density and stage-3 ordering, so it deserves its own focused review/test pass.

