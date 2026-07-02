# Review: single anchor-aware `flow` command for standard test runs

Date: 2026-07-02
Reviewer: Codex
Proposal: `AI_agent/logs/review/request/2026-07-02_standardize_test_flow_proposal.md`

## Verdict

**APPROVE-WITH-CHANGES.**

The direction is right: the current formal run path is fragmented enough that a single resumable orchestration entry point is warranted, and the existing `run_one_stage` / `submit_verdict` / geometry approval / `record_baseline` machinery is close to sufficient. But the proposal as written misses one load-bearing state (`JUDGE_BLOCK`), overstates current judge density, and would be unsafe if implemented as a simple "manifest position" loop without explicit downstream invalidation after resampling.

Required changes before implementation:

1. `flow` must handle `StepStatus.JUDGE_BLOCK` explicitly. A rerun after a blocking verdict will return `JUDGE_BLOCK` from `run_one_stage`; this is not terminal, not advance-ok, and not covered by the proposed loop.
2. Any judge/reread/force resample of a stage must invalidate downstream manifest pointers before continuing. Current `run_stage resample` does not do this.
3. Formal self-contained flows must not silently skip `0_reading` / J0. Either default `flow` to start at `0_reading` when the run lacks an accepted+judged J0, or make `--from 1_correction` an explicit "reuse already-adjudicated reading" mode.
4. Use option A for EP layout, but extract the graph invocation carefully enough to preserve `run_full_pipeline` behavior, including LLM config resolution and `--no-simulate`.
5. `--geometry auto` must be explicit and visibly recorded as auto/CI, not indistinguishable from human approval. Golden/baseline-recording should default to `required`; regression can opt into auto/disabled.
6. Define documented `flow` exit codes: success, checkpoint/pending, terminal orchestration stop, and downstream/report failure must be distinguishable.

## 1. Current-State Claim Verification

### 1a. Fragmentation / "~15 commands"

Directionally true, but the example sequence in the proposal is inaccurate.

Current `run_stage.py` exposes only one-stage/action verbs (`run`, `judge`, `resample`, `approve-geometry`, `status`), so the operator does manually stitch stage runs, verdict submissions, geometry approval, EP, and report recording (`scripts/tool_scripts/run_stage.py:9`, `scripts/tool_scripts/run_stage.py:11`, `scripts/tool_scripts/run_stage.py:12`, `scripts/tool_scripts/run_stage.py:13`, `scripts/tool_scripts/run_stage.py:14`, `scripts/tool_scripts/run_stage.py:18`, `scripts/tool_scripts/run_stage.py:21`).

However, the proposal's sample sequence shows judge steps after 2/3/4/5. The actual judge density is not "judge every stage":

- The guide says J0/J1 are enabled, deterministic stages 2/3 have no per-run judge, stage 5 has no judge, and J4 is a disabled stub (`AI_agent/guides/new_case_guide.md:33`).
- The code agrees: `rubric_for()` registers only `0_reading`, `1_correction`, and disabled `4_mep` (`src/agent/judge/executor.py:28`, `src/agent/judge/executor.py:29`, `src/agent/judge/executor.py:30`, `src/agent/judge/executor.py:31`, `src/agent/judge/executor.py:32`).
- `_post_gate1()` only stops for judge when `rubric_for(stage)` exists, the rubric is enabled, and `policy.judge_enabled` is true (`src/agent/execution/step_orchestrator.py:312`, `src/agent/execution/step_orchestrator.py:313`, `src/agent/execution/step_orchestrator.py:322`, `src/agent/execution/step_orchestrator.py:323`, `src/agent/execution/step_orchestrator.py:324`).
- `cmd_run()` records an explicit disabled verdict for `4_mep` rather than stopping for a live J4 judgment (`scripts/tool_scripts/run_stage.py:492`, `scripts/tool_scripts/run_stage.py:493`, `scripts/tool_scripts/run_stage.py:494`).

So the real non-resample happy path from an existing reading is closer to:

`run 0_reading -> judge 0_reading -> run 1_correction -> judge 1_correction -> run 2_modelling -> run 3_split_pairing -> approve-geometry -> run 4_mep -> run 5_intakeoutput -> EP -> record_baseline`

That is still too fragmented, especially once any verdict blocks and a blind resample is needed. But the design should not encode the inaccurate "judge every stage" mental model.

### 1b. EP layout inconsistency

True, with one caveat.

`run_full_pipeline.py --reading-from` only switches into the standard organized layout when `--output-subdir` remains the default `"output"`:

- `output_dir = case_dir / args.output_subdir` initially (`scripts/run_full_pipeline.py:222`).
- If `reading_vector_dir is not None and args.output_subdir == "output"`, it changes to `output_dir = case_dir / "EP"`, `ep_run_subdir = "EP_run"`, and `pipeline_out_dir = str(case_dir)` (`scripts/run_full_pipeline.py:268`, `scripts/run_full_pipeline.py:269`, `scripts/run_full_pipeline.py:270`, `scripts/run_full_pipeline.py:271`, `scripts/run_full_pipeline.py:272`).
- Otherwise, `ep_run_subdir` remains `None`, and with `--intake-from` the EP artifacts land flat in `<case>/<output-subdir>` (`scripts/run_full_pipeline.py:273`, `scripts/run_full_pipeline.py:274`, `scripts/run_full_pipeline.py:275`, `scripts/run_full_pipeline.py:276`).
- `SimContext` carries `ep_run_subdir` through to simulation (`scripts/run_full_pipeline.py:315`, `scripts/run_full_pipeline.py:316`, `scripts/run_full_pipeline.py:318`, `scripts/run_full_pipeline.py:320`), and `WorkflowTool.run_simulation()` only nests EnergyPlus artifacts when that field is set (`src/mcp/tools/workflow.py:265`, `src/mcp/tools/workflow.py:267`, `src/mcp/tools/workflow.py:268`, `src/mcp/tools/workflow.py:269`, `src/mcp/tools/workflow.py:273`, `src/mcp/tools/workflow.py:274`).

This conflicts with validation/report expectations for self-contained run dirs:

- `validate_case(require_ep=True)` requires `<run>/EP/EP_run/eplusout.end` (`src/agent/execution/validation_run.py:107`, `src/agent/execution/validation_run.py:120`, `src/agent/execution/validation_run.py:121`).
- `record_baseline._ep_end()` reads `<run>/EP/EP_run/eplusout.end` (`scripts/tool_scripts/record_baseline.py:65`, `scripts/tool_scripts/record_baseline.py:66`, `scripts/tool_scripts/record_baseline.py:67`).

The proposal's "0-5 writing to case root" claim is true only for the default `--reading-from` organized branch (`scripts/run_full_pipeline.py:263`, `scripts/run_full_pipeline.py:264`, `scripts/run_full_pipeline.py:265`, `scripts/run_full_pipeline.py:266`, `scripts/run_full_pipeline.py:272`). It is not universally true for all `--reading-from` calls when a non-default `--output-subdir` is supplied.

### 1c. Judge is main-agent / submitted verdict, not wired LLM judge

True for the current `run_stage.py` flow.

`_judge_packet()` writes a packet whose note tells the main agent to inspect artifacts and submit a `StageVerdict` JSON (`scripts/tool_scripts/run_stage.py:387`, `scripts/tool_scripts/run_stage.py:407`, `scripts/tool_scripts/run_stage.py:408`, `scripts/tool_scripts/run_stage.py:410`). `cmd_judge()` loads that JSON and calls `submit_verdict()` (`scripts/tool_scripts/run_stage.py:515`, `scripts/tool_scripts/run_stage.py:523`, `scripts/tool_scripts/run_stage.py:527`, `scripts/tool_scripts/run_stage.py:532`, `scripts/tool_scripts/run_stage.py:533`, `scripts/tool_scripts/run_stage.py:534`, `scripts/tool_scripts/run_stage.py:535`).

`run_judge()` is model-agnostic and accepts a pluggable `judge_fn`, but when `judge_fn is None` it records a disabled verdict rather than faking a pass (`src/agent/judge/executor.py:52`, `src/agent/judge/executor.py:56`, `src/agent/judge/executor.py:63`, `src/agent/judge/executor.py:81`, `src/agent/judge/executor.py:82`, `src/agent/judge/executor.py:83`, `src/agent/judge/executor.py:84`, `src/agent/judge/executor.py:85`, `src/agent/judge/executor.py:86`). `run_stage.py` only calls it for disabled J4 (`scripts/tool_scripts/run_stage.py:492`, `scripts/tool_scripts/run_stage.py:494`).

### 1d. `run_one_stage` statuses

Mostly true, but the proposal misses a critical status.

The actual enum is `StepStatus`, and the returned object is `StageOutcome`, not `StepOutcome` (`src/agent/execution/step_orchestrator.py:72`, `src/agent/execution/step_orchestrator.py:99`). `run_one_stage()` can return the statuses listed in the proposal: `AWAITING_JUDGE`, `DETERMINISTIC_PASS`, `AWAITING_GEOMETRY_APPROVAL`, `AWAITING_REREAD`, and the terminal statuses (`src/agent/execution/step_orchestrator.py:72`, `src/agent/execution/step_orchestrator.py:73`, `src/agent/execution/step_orchestrator.py:74`, `src/agent/execution/step_orchestrator.py:75`, `src/agent/execution/step_orchestrator.py:76`, `src/agent/execution/step_orchestrator.py:77`, `src/agent/execution/step_orchestrator.py:81`, `src/agent/execution/step_orchestrator.py:82`, `src/agent/execution/step_orchestrator.py:83`, `src/agent/execution/step_orchestrator.py:84`, `src/agent/execution/step_orchestrator.py:85`).

But it can also return `JUDGE_BLOCK` on resume after a blocking verdict has been submitted. The path is:

- accepted attempt exists, so `run_one_stage()` re-emits the post-gate decision without redrawing (`src/agent/execution/step_orchestrator.py:232`, `src/agent/execution/step_orchestrator.py:233`, `src/agent/execution/step_orchestrator.py:234`, `src/agent/execution/step_orchestrator.py:236`, `src/agent/execution/step_orchestrator.py:237`, `src/agent/execution/step_orchestrator.py:238`);
- `_post_gate1()` loads an existing verdict and classifies it (`src/agent/execution/step_orchestrator.py:314`, `src/agent/execution/step_orchestrator.py:315`, `src/agent/execution/step_orchestrator.py:316`, `src/agent/execution/step_orchestrator.py:317`, `src/agent/execution/step_orchestrator.py:318`);
- `_verdict_outcome()` returns `StepStatus.JUDGE_BLOCK` for routable stochastic roots (`src/agent/execution/step_orchestrator.py:399`, `src/agent/execution/step_orchestrator.py:400`, `src/agent/execution/step_orchestrator.py:407`, `src/agent/execution/step_orchestrator.py:440`, `src/agent/execution/step_orchestrator.py:441`, `src/agent/execution/step_orchestrator.py:442`, `src/agent/execution/step_orchestrator.py:443`).

`JUDGE_BLOCK` is explicitly not terminal and not advance-ok (`src/agent/execution/step_orchestrator.py:88`, `src/agent/execution/step_orchestrator.py:89`, `src/agent/execution/step_orchestrator.py:90`, `src/agent/execution/step_orchestrator.py:91`, `src/agent/execution/step_orchestrator.py:92`, `src/agent/execution/step_orchestrator.py:93`, `src/agent/execution/step_orchestrator.py:95`, `src/agent/execution/step_orchestrator.py:96`). The flow loop must handle it.

### 1e. Geometry approval helpers exist and are callable

True.

`run_stage.py` imports `approve_geometry`, `geometry_is_approved`, and `mark_geometry_approved` (`scripts/tool_scripts/run_stage.py:43`, `scripts/tool_scripts/run_stage.py:44`, `scripts/tool_scripts/run_stage.py:46`). `cmd_approve_geometry()` calls `approve_geometry()`, then `mark_geometry_approved()` (`scripts/tool_scripts/run_stage.py:549`, `scripts/tool_scripts/run_stage.py:551`, `scripts/tool_scripts/run_stage.py:552`, `scripts/tool_scripts/run_stage.py:557`, `scripts/tool_scripts/run_stage.py:558`).

The helper validates the current run and writes a digest-bound `GeometryApproval` only when a consistent geometry digest exists (`src/agent/execution/step_orchestrator.py:461`, `src/agent/execution/step_orchestrator.py:469`, `src/agent/execution/step_orchestrator.py:476`, `src/agent/execution/step_orchestrator.py:477`, `src/agent/execution/step_orchestrator.py:478`, `src/agent/execution/step_orchestrator.py:479`, `src/agent/execution/step_orchestrator.py:480`, `src/agent/execution/step_orchestrator.py:481`, `src/agent/execution/step_orchestrator.py:483`).

Caveat: the saved approval currently hard-codes `policy="required"` (`src/agent/execution/step_orchestrator.py:480`). If `flow:auto` is introduced, the approval record should either support `policy="auto"` / `"ci"` or carry a mandatory note/actor that makes non-human approval unambiguous in reports.

## 2. Feasibility of a resumable manifest-driven `flow`

Feasible, but the phrase "manifest-driven" needs precision. The manifest does not store "next stage"; it stores accepted attempt pointers. A robust `flow` should scan `_STAGES` from `--from` to `--to`, call `run_one_stage()` for each, and let `run_one_stage()` reclassify accepted attempts.

State that is sufficient today:

- `_run/run_manifest.json` stores `RunManifest.stages[stage].accepted_attempt` and the accepted output hash (`src/agent/execution/manifest.py:99`, `src/agent/execution/manifest.py:104`, `src/agent/execution/manifest.py:105`, `src/agent/execution/manifest.py:106`, `src/agent/execution/manifest.py:114`, `src/agent/execution/manifest.py:123`, `src/agent/execution/manifest.py:144`, `src/agent/execution/manifest.py:145`; `_run` path from `src/agent/execution/run_meta.py:7`, `src/agent/execution/run_meta.py:10`, `src/agent/execution/run_meta.py:11`, `src/agent/execution/run_meta.py:18`).
- `StageRunner.record()` advances that pointer only for accepted gate①-passing attempts (`src/agent/execution/stage_runner.py:156`, `src/agent/execution/stage_runner.py:157`, `src/agent/execution/stage_runner.py:166`, `src/agent/execution/stage_runner.py:167`, `src/agent/execution/stage_runner.py:168`, `src/agent/execution/stage_runner.py:169`, `src/agent/execution/stage_runner.py:170`, `src/agent/execution/stage_runner.py:171`, `src/agent/execution/stage_runner.py:172`, `src/agent/execution/stage_runner.py:173`, `src/agent/execution/stage_runner.py:177`, `src/agent/execution/stage_runner.py:178`, `src/agent/execution/stage_runner.py:180`).
- `submit_verdict()` writes the out-of-band verdict beside the accepted attempt as `attempts/NNN/judge.json` (`src/agent/execution/step_orchestrator.py:336`, `src/agent/execution/step_orchestrator.py:347`, `src/agent/execution/step_orchestrator.py:352`, `src/agent/execution/step_orchestrator.py:353`, `src/agent/execution/step_orchestrator.py:354`, `src/agent/execution/step_orchestrator.py:355`, `src/agent/execution/step_orchestrator.py:356`).
- On rerun, `run_one_stage()` sees the accepted attempt and `_post_gate1()` reads that `judge.json`, allowing a submitted nonblocking verdict to become `JUDGE_PASS` and a submitted blocking verdict to become `JUDGE_BLOCK` / human stop / reread (`src/agent/execution/step_orchestrator.py:232`, `src/agent/execution/step_orchestrator.py:236`, `src/agent/execution/step_orchestrator.py:314`, `src/agent/execution/step_orchestrator.py:315`, `src/agent/execution/step_orchestrator.py:316`, `src/agent/execution/step_orchestrator.py:379`, `src/agent/execution/step_orchestrator.py:390`, `src/agent/execution/step_orchestrator.py:394`, `src/agent/execution/step_orchestrator.py:440`).
- `StageOutcome.status`, `.terminal_stop`, and `.can_advance` distinguish terminal failures from pending checkpoints (`src/agent/execution/step_orchestrator.py:113`, `src/agent/execution/step_orchestrator.py:114`, `src/agent/execution/step_orchestrator.py:115`, `src/agent/execution/step_orchestrator.py:117`, `src/agent/execution/step_orchestrator.py:118`, `src/agent/execution/step_orchestrator.py:119`).
- `_run/orchestration_state.json` records each stage's latest `status`, `accepted_attempt`, `message`, and optional `route_target` via `StageOutcome.summary()` and `update_state()` (`src/agent/execution/step_orchestrator.py:121`, `src/agent/execution/step_orchestrator.py:122`, `src/agent/execution/step_orchestrator.py:123`, `src/agent/execution/step_orchestrator.py:124`, `src/agent/execution/step_orchestrator.py:125`, `src/agent/execution/step_orchestrator.py:126`, `src/agent/execution/step_orchestrator.py:129`, `src/agent/execution/step_orchestrator.py:517`, `src/agent/execution/step_orchestrator.py:518`).

Important distinction: `update_state()` does not set `stop_reason` for `AWAITING_JUDGE`; it clears it for any non-terminal/non-geometry/non-reread outcome (`src/agent/execution/step_orchestrator.py:519`, `src/agent/execution/step_orchestrator.py:520`, `src/agent/execution/step_orchestrator.py:521`, `src/agent/execution/step_orchestrator.py:522`, `src/agent/execution/step_orchestrator.py:523`, `src/agent/execution/step_orchestrator.py:524`). The report layer compensates by scanning per-stage statuses and treating `AWAITING_JUDGE`, `JUDGE_BLOCK`, `AWAITING_REREAD`, and `AWAITING_GEOMETRY_APPROVAL` as pending (`scripts/tool_scripts/report_assembly.py:28`, `scripts/tool_scripts/report_assembly.py:29`, `scripts/tool_scripts/report_assembly.py:30`, `scripts/tool_scripts/report_assembly.py:31`, `scripts/tool_scripts/report_assembly.py:32`, `scripts/tool_scripts/report_assembly.py:33`, `scripts/tool_scripts/report_assembly.py:250`, `scripts/tool_scripts/report_assembly.py:254`, `scripts/tool_scripts/report_assembly.py:269`, `scripts/tool_scripts/report_assembly.py:270`). `flow` should use the current `StageOutcome.status`, not only `state["stop_reason"]`.

One more caveat: input-hash based resume is not actually wired into `run_stage.py`. `StageRunner.record()` can store `input_hashes` (`src/agent/execution/stage_runner.py:130`, `src/agent/execution/stage_runner.py:131`, `src/agent/execution/stage_runner.py:172`), and `stages_to_run()` can compare them (`src/agent/execution/invalidation.py:65`, `src/agent/execution/invalidation.py:70`, `src/agent/execution/invalidation.py:71`, `src/agent/execution/invalidation.py:86`, `src/agent/execution/invalidation.py:87`, `src/agent/execution/invalidation.py:88`), but `run_one_stage()` calls `file_stage_attempt()` without supplying input hashes (`src/agent/execution/step_orchestrator.py:252`, `src/agent/execution/step_orchestrator.py:253`, `src/agent/execution/step_orchestrator.py:254`). Therefore `flow` cannot safely assume automatic drift detection. It must explicitly invalidate downstream when it causes a new upstream draw.

## 3. Rulings on F1-F6

### F1. `0_reading` handling

Recommendation: **include `0_reading` in formal flow unless explicitly skipped.**

`0_reading` is manual, but `run_stage.py` can validate an existing flat reading directory and produce an accepted attempt (`scripts/tool_scripts/run_stage.py:89`, `scripts/tool_scripts/run_stage.py:90`, `scripts/tool_scripts/run_stage.py:94`, `scripts/tool_scripts/run_stage.py:95`, `scripts/tool_scripts/run_stage.py:101`, `scripts/tool_scripts/run_stage.py:102`, `scripts/tool_scripts/run_stage.py:103`, `scripts/tool_scripts/run_stage.py:104`). If the run claims to be "proper judge-in-the-loop", it should not default to starting at `1_correction` and thereby omit J0. The proposal's default "reuse existing `<run>/0_reading/` and start from `1_correction`" is acceptable only if the existing reading already has a manifest accepted attempt and a submitted J0 verdict.

Concrete behavior:

- Default `--from auto`: start at the earliest incomplete formal stage. If `0_reading` lacks an accepted attempt or lacks required J0 verdict under `--judge stop`, start there.
- `--from 1_correction`: allowed, but print that J0 is being skipped/reused.
- If `0_reading/*_view.json` is missing, do not run LLM/subagents inside `flow`. Stop with a clear protocol. If `--reading-runner-available` is set, the existing `AWAITING_REREAD` protocol is appropriate (`scripts/tool_scripts/run_stage.py:453`, `scripts/tool_scripts/run_stage.py:456`, `scripts/tool_scripts/run_stage.py:457`, `scripts/tool_scripts/run_stage.py:458`, `scripts/tool_scripts/run_stage.py:459`, `scripts/tool_scripts/run_stage.py:460`, `scripts/tool_scripts/run_stage.py:461`, `scripts/tool_scripts/run_stage.py:463`, `scripts/tool_scripts/run_stage.py:464`, `scripts/tool_scripts/run_stage.py:465`).

### F2. EP layout fix: option A vs B

Recommendation: **option A, with a sharper extraction boundary.**

Option B (`run_full_pipeline --intake-from ... --output-subdir <run>/EP/EP_run`) is a workaround, not a good interface. It relies on `--output-subdir` accepting a nested path under `<case>` (`scripts/run_full_pipeline.py:179`, `scripts/run_full_pipeline.py:181`, `scripts/run_full_pipeline.py:185`, `scripts/run_full_pipeline.py:186`), leaves `ep_run_subdir=None`, and therefore puts IDF/YAML and eplusout files flat in `EP/EP_run` instead of preserving the standard "IDF in EP, EnergyPlus artifacts in EP/EP_run" layout. It also skips saving a copy of `intake_output.json` because `pre_intake is not None` (`scripts/run_full_pipeline.py:336`, `scripts/run_full_pipeline.py:337`, `scripts/run_full_pipeline.py:338`, `scripts/run_full_pipeline.py:339`, `scripts/run_full_pipeline.py:340`, `scripts/run_full_pipeline.py:341`).

Option A is cleaner because the graph already supports the right layout directly through `SimContext(output_dir=<run>/EP, ep_run_subdir="EP_run")` (`src/agent/state.py:69`, `src/agent/state.py:73`, `src/agent/state.py:74`, `src/agent/state.py:76`, `src/agent/state.py:77`, `src/agent/state.py:78`, `src/agent/state.py:79`; `src/agent/nodes/simulate.py:53`, `src/agent/nodes/simulate.py:54`, `src/agent/nodes/simulate.py:55`, `src/agent/nodes/simulate.py:56`, `src/agent/nodes/simulate.py:57`). There is already a test proving nested EP runs go where expected (`tests/test_ep_end_gate.py:137`, `tests/test_ep_end_gate.py:138`, `tests/test_ep_end_gate.py:139`, `tests/test_ep_end_gate.py:153`, `tests/test_ep_end_gate.py:155`, `tests/test_ep_end_gate.py:157`, `tests/test_ep_end_gate.py:158`, `tests/test_ep_end_gate.py:169`, `tests/test_ep_end_gate.py:170`, `tests/test_ep_end_gate.py:171`, `tests/test_ep_end_gate.py:174`, `tests/test_ep_end_gate.py:175`).

But the proposed signature `run_downstream_ep(intake, run_dir, epw)` is too narrow if the goal is a behavior-preserving refactor of `run_full_pipeline`. Preserve these pieces:

- LLM config resolution and `EP_AGENT_LLM_CONFIG` setup (`scripts/run_full_pipeline.py:195`, `scripts/run_full_pipeline.py:196`, `scripts/run_full_pipeline.py:198`, `scripts/run_full_pipeline.py:211`, `scripts/run_full_pipeline.py:215`, `scripts/run_full_pipeline.py:216`, `scripts/run_full_pipeline.py:218`, `scripts/run_full_pipeline.py:219`).
- `--no-simulate` via `SimContext.run_simulate` (`scripts/run_full_pipeline.py:173`, `scripts/run_full_pipeline.py:174`, `scripts/run_full_pipeline.py:175`, `scripts/run_full_pipeline.py:319`).
- the existing graph invocation (`scripts/run_full_pipeline.py:315`, `scripts/run_full_pipeline.py:327`, `scripts/run_full_pipeline.py:328`, `scripts/run_full_pipeline.py:329`, `scripts/run_full_pipeline.py:330`, `scripts/run_full_pipeline.py:331`, `scripts/run_full_pipeline.py:332`, `scripts/run_full_pipeline.py:333`, `scripts/run_full_pipeline.py:334`).
- short-circuit behavior for prebuilt `IntakeOutput` (`src/agent/nodes/intake.py:20`, `src/agent/nodes/intake.py:23`, `src/agent/nodes/intake.py:24`, `src/agent/nodes/intake.py:34`, `src/agent/nodes/intake.py:35`, `src/agent/nodes/intake.py:36`, `src/agent/nodes/intake.py:37`, `src/agent/nodes/intake.py:44`).

Preferred extraction:

- Extract a reusable lower-level helper like `run_agent_graph(initial, *, output_dir, epw, ep_run_subdir, run_simulate, thread_id, on_event)` from the current graph/`SimContext` block.
- Build `run_downstream_ep(intake, run_dir, epw, *, run_simulate=True, thread_id=None)` on top of it for `flow` and the CLI `--intake-from` branch.
- Leave the `--reading-from` branch behavior-preserving except for using the shared graph helper. Do not force all historical `run_full_pipeline --intake-from` uses into run-dir semantics unless a new explicit `--run-dir` / `--standard-run-layout` option is added.

### F3. `flow` verb location

Recommendation: **add it to `run_stage.py`, not a new script.**

The flow needs private wiring already local to `run_stage.py`: `_make_draw_fn`, `_judge_packet`, `_render_geometry_viewer`, `_make_policy`, `_print_reread_protocol`, and the exact status handling. Keeping it beside `run`, `judge`, `resample`, and `approve-geometry` reduces duplication and makes "flow as composition layer" accurate.

Do not add a separate flow progress marker unless implementation proves it is needed. The manifest + attempt `judge.json` + orchestration state are enough for normal resume. Extra state increases reconciliation risk.

### F4. `--geometry auto`

Recommendation: **allowed only when explicit; not the default for golden/baseline recording.**

The current architecture treats confirmation as a policy knob, not an un-bypassable interaction (`src/agent/execution/policy.py:23`, `src/agent/execution/policy.py:24`, `src/agent/execution/policy.py:25`, `src/agent/execution/policy.py:26`, `src/agent/execution/policy.py:59`, `src/agent/execution/policy.py:60`, `src/agent/execution/policy.py:61`, `src/agent/execution/policy.py:62`, `src/agent/execution/policy.py:63`). So auto/CI operation is legitimate.

But auto-approval should not masquerade as human confirmation:

- Require an explicit `--geometry auto` flag. Default should be `required` for `dev`, `golden`, and `--record` unless the operator opts out.
- For `regression`, allow explicit auto or consider a separate `disabled` mode. Auto writes an approval artifact; disabled merely does not block. Those are different audit claims.
- Record actor as `flow:auto` / `ci:auto` and support `policy="auto"` or equivalent. Current hard-coded `policy="required"` is misleading for auto (`src/agent/execution/step_orchestrator.py:480`).
- Render/regenerate the 3D viewer immediately before auto-approval so reports do not point at a stale viewer. `_render_geometry_viewer()` overwrites `manual_review/geometry_viewer.html` when called (`scripts/tool_scripts/run_stage.py:348`, `scripts/tool_scripts/run_stage.py:354`, `scripts/tool_scripts/run_stage.py:360`, `scripts/tool_scripts/run_stage.py:364`, `scripts/tool_scripts/run_stage.py:366`), while `report_assembly.ensure_geometry_viewer()` currently trusts an existing file (`scripts/tool_scripts/report_assembly.py:158`, `scripts/tool_scripts/report_assembly.py:165`, `scripts/tool_scripts/report_assembly.py:167`, `scripts/tool_scripts/report_assembly.py:168`, `scripts/tool_scripts/report_assembly.py:172`).

The digest binding itself is sound: validation only computes a digest after consistent 2/3 artifacts pass (`src/agent/execution/validation_run.py:250`, `src/agent/execution/validation_run.py:251`, `src/agent/execution/validation_run.py:252`, `src/agent/execution/validation_run.py:253`, `src/agent/execution/validation_run.py:254`, `src/agent/execution/validation_run.py:255`, `src/agent/execution/validation_run.py:256`, `src/agent/execution/validation_run.py:257`, `src/agent/execution/validation_run.py:258`, `src/agent/execution/validation_run.py:259`, `src/agent/execution/validation_run.py:264`, `src/agent/execution/validation_run.py:267`), and `is_approved()` requires digest equality (`src/agent/execution/approval.py:80`, `src/agent/execution/approval.py:81`, `src/agent/execution/approval.py:82`, `src/agent/execution/approval.py:83`, `src/agent/execution/approval.py:84`).

### F5. Resume marker vs pure manifest

Recommendation: **no new marker for v1, but do not over-trust current manifest hashes.**

The existing accepted attempt pointer plus `judge.json` is enough to resume judge pass/block decisions. The orchestration ledger is enough to report pending/terminal state. A separate flow marker would create one more state source to reconcile.

However, because `run_stage.py` is not currently recording input hashes, `flow` must explicitly handle invalidation when it causes a redraw. Use `invalidate(manifest, target_stage)` for downstream pointers (`src/agent/execution/invalidation.py:50`, `src/agent/execution/invalidation.py:51`, `src/agent/execution/invalidation.py:57`, `src/agent/execution/invalidation.py:58`, `src/agent/execution/invalidation.py:59`, `src/agent/execution/invalidation.py:60`, `src/agent/execution/invalidation.py:61`) before/after the forced target redraw, then save the manifest. `invalidate()` drops only downstream stages, not the target itself; the target must be redrawn with `force_draw=True`.

### F6. Exit-code semantics

Recommendation: **make `flow` exit codes explicit and different from per-stage legacy behavior.**

Current `cmd_run()` returns `0` for any non-terminal outcome, including checkpoints, and `2` for terminal stops (`scripts/tool_scripts/run_stage.py:507`). That is tolerable for one-stage manual driving, but a single "complete the flow" command needs stronger shell semantics.

Use stable named constants and document them in `--help`:

- `0`: requested flow completed successfully through `--to`, and any requested EP/report step completed.
- `10`: stopped at an expected human/action checkpoint: `AWAITING_JUDGE`, `AWAITING_GEOMETRY_APPROVAL` under required mode, `AWAITING_REREAD`, or an unhandled `JUDGE_BLOCK` if v1 chooses to stop rather than auto-resample.
- `20`: terminal orchestration stop: `QUARANTINED`, `DETERMINISTIC_DEFECT`, `HUMAN_REDRAW_REQUIRED`, `JUDGE_BLOCK_HUMAN`.
- `30`: downstream EP/report failure after stages completed.

Do not use `0` for checkpoint-stop in `flow`; CI and shell wrappers should be able to distinguish "all done" from "healthy but waiting for judge."

## 4. Missed Design Risks

### `JUDGE_BLOCK` resume edge

This is the most serious gap. After `run_stage judge ...` submits a blocking routable verdict, rerunning `flow` on that stage will not return `AWAITING_JUDGE`; it will return `JUDGE_BLOCK`. The proposal's loop has no branch for that. A correct branch should either:

- auto-resample the stochastic `route_target` with `force_draw=True`, invalidate downstream, save manifest, update state, then continue from the target; or
- stop with checkpoint code `10` and print the exact resample command.

If the goal is to reduce fragmentation, auto-resampling routable stochastic roots is the better default. Manual roots still stop at reread/human protocol; deterministic roots already become human triage.

### Downstream stale outputs after resample

Existing `cmd_resample()` only sets `args.force = True` and calls `cmd_run()` (`scripts/tool_scripts/run_stage.py:510`, `scripts/tool_scripts/run_stage.py:511`, `scripts/tool_scripts/run_stage.py:512`). It does not call `invalidate()`. If `flow` force-redraws `1_correction` after stages 2/3/4/5 have accepted pointers, a naive loop can reuse stale downstream accepted attempts because `run_one_stage()` returns the accepted branch without rebuilding (`src/agent/execution/step_orchestrator.py:232`, `src/agent/execution/step_orchestrator.py:233`, `src/agent/execution/step_orchestrator.py:236`, `src/agent/execution/step_orchestrator.py:238`).

This must be fixed in `flow` at minimum. It may also be worth fixing `cmd_resample()` itself, but that is an implementation-scope decision.

### `0_reading` / J0 skip

The proposal defaults to reusing `0_reading` and starting from `1_correction`. That contradicts the "proper judge-in-the-loop" claim unless the reading has already gone through `run 0_reading` + J0 verdict. The current guide makes J0 part of the formal flow (`AI_agent/guides/new_case_guide.md:120`, `AI_agent/guides/new_case_guide.md:140`). `flow` should not accidentally make "no J0" the new standard.

### Geometry approval state after redraw

The digest check is robust, but the state ledger is not the authority. `mark_geometry_approved()` writes a run-level `geometry_approved = True` and clears a pending stop reason (`src/agent/execution/step_orchestrator.py:531`, `src/agent/execution/step_orchestrator.py:532`, `src/agent/execution/step_orchestrator.py:535`, `src/agent/execution/step_orchestrator.py:536`, `src/agent/execution/step_orchestrator.py:539`, `src/agent/execution/step_orchestrator.py:540`). If geometry is later redrawn, `flow` must use `geometry_is_approved()` / `validate_case().geometry_approved`, not that ledger flag.

### Auto-approval can bind semantically bad geometry

Digest binding prevents stale-byte approval; it does not prove geometry is worth approving. That is fine for CI/regression, but not fine as the default for golden/baseline recording. Reports must show auto approval clearly so a later reviewer does not read it as human confirmation.

### `_run/` collision

`flow` should write only the artifacts existing verbs already write:

- `_run/run_manifest.json`
- `_run/orchestration_state.json`
- `_run/geometry_approval.json`
- `_run/baseline.json`

Avoid a new flow progress file unless a specific ambiguity appears during implementation. If one is added, it must not replace or reinterpret these ledgers.

### `record_baseline` preconditions

`record_baseline()` requires `date` and `orchestrator` and can optionally require EP (`scripts/tool_scripts/record_baseline.py:292`, `scripts/tool_scripts/record_baseline.py:293`, `scripts/tool_scripts/record_baseline.py:295`, `scripts/tool_scripts/record_baseline.py:296`, `scripts/tool_scripts/record_baseline.py:297`, `scripts/tool_scripts/record_baseline.py:662`, `scripts/tool_scripts/record_baseline.py:664`, `scripts/tool_scripts/record_baseline.py:665`, `scripts/tool_scripts/record_baseline.py:667`, `scripts/tool_scripts/record_baseline.py:668`, `scripts/tool_scripts/record_baseline.py:669`). `flow --record --with-ep` should pass `require_ep=True` or refuse to claim an EP-backed baseline. If stages are pending, `--record` should either refuse by default or require an explicit `--record-partial`.

## 5. Scope Check

Adding a `flow` verb is the right size if the goal is to make the proper run path harder to bypass. Merely fixing EP layout and documenting a fixed command sequence would reduce one wart but would not solve the root problem: the operator still has to remember when to run judge, when to resample, when geometry approval unlocks 4_mep, when to rerun from a blocking verdict, and when report/EP are safe.

A smaller useful interim could be:

1. Fix EP layout via the shared helper.
2. Update the guide with an exact non-fragmented checklist.
3. Then add `flow`.

But I would not stop at documentation. The state machine already exists in code; the missing piece is a composition layer that respects it.

## 6. Required Test Coverage

Add focused tests before running a real sm21 rerun:

1. `flow --judge stop` starts at `0_reading` when no accepted/J0 reading exists, stops at `AWAITING_JUDGE`, writes packet, exits `10`.
2. Submit nonblocking J0; rerun `flow`; it advances to `1_correction` and stops at J1.
3. Submit blocking routable J1; rerun `flow`; it handles `JUDGE_BLOCK`, force-redraws the route target, invalidates downstream accepted pointers, and does not reuse stale 2/3/4/5.
4. Geometry required: stops after 3 with viewer and exits `10`; approval then rerun reaches 4.
5. Geometry auto: regenerates viewer, writes digest-bound approval with auto actor/policy, reaches 4.
6. EP helper writes `EP/EP_run/eplusout.end` while IDF/YAML stay under `EP/`.
7. `--record --with-ep` calls `record_baseline(require_ep=True)` and fails distinctly if EP did not produce `eplusout.end`.
8. Exit codes: complete = `0`, checkpoint = `10`, terminal orchestration = `20`, EP/report failure = `30`.

## Final Ruling

Implement the `flow` verb, but not as the exact loop in the proposal. Treat `JUDGE_BLOCK` and downstream invalidation as blockers. Use option A for EP layout with a careful helper extraction. Default formal/golden/baseline flows to human geometry approval, allow explicit auto/CI approval, and make exit codes scriptable.
