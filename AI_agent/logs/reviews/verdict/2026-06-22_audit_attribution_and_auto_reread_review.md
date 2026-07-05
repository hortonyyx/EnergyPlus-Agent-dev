# Design Review - Audit Attribution + Auto Re-read

Top-line verdict: **APPROVE-WITH-CHANGES**

The proposal is directionally sound against the ratified D1-D5 architecture. It keeps correction image-blind, keeps image-grounded arbitration in J0/J1 plus re-read, and surfaces existing attribution data instead of changing geometry. The changes needed are mostly executor-boundary details: policy must be threaded through judge verdict classification, re-read budget must be computed for the target stage, and the main-Agent re-read protocol must say exactly how new `0_reading/*_view.json` files become the flat working artifacts that downstream code reads.

No golden geometry baseline re-record is needed for either debt. Debt 1 changes metadata/reporting only. Debt 2 is backward-compatible if `reading_runner_available` defaults to `False`; existing runs and tests should continue to stop at `human_redraw_required` until the flag/protocol is enabled.

## Findings

1. [major] `src/agent/execution/step_orchestrator.py:299` / `src/agent/execution/step_orchestrator.py:324` - The proposed `reading_runner_available` gate cannot be applied to judge-routed manual failures unless `submit_verdict()` and `_verdict_outcome()` receive policy and target-stage attempt context. Today `submit_verdict()` calls `_verdict_outcome()` with `_existing_attempts(stage_dir)` for the judged stage, not the judge-attributed root stage. For a J1 verdict on `1_correction` with `root_stage="0_reading"`, that would compare the correction attempt count against the reading budget. Recommendation: thread `RunPolicy` through `submit_verdict()` and the existing-verdict path in `_post_gate1()`, and provide a target-stage attempt lookup, stage-dir map, or `run_dir` so manual target budget is computed against `0_reading`.

2. [major] `scripts/tool_scripts/run_stage.py:86` / `scripts/tool_scripts/run_stage.py:264` / `src/agent/execution/stage_runner.py:140` - The re-read artifact handoff is underspecified. Current `_draw_reading()` validates flat `0_reading/*_view.json`, while `StageRunner.record()` stores only a generic `attempts/NNN/output.json`. Downstream correction also reads the flat `0_reading` directory. If the sub-agent only files an attempt output, the pipeline will keep seeing stale or missing flat reading files. Recommendation: define the main-Agent protocol explicitly: the re-read runner writes/replaces the flat `0_reading/*_view.json` working copy, then `run_stage.py resample ... 0_reading --force` records that copy as the next attempt; or add a dedicated ingest verb that installs a supplied re-read bundle into both places before gate1/J0.

3. [major] `src/agent/execution/step_orchestrator.py:361` / `scripts/tool_scripts/run_stage.py:467` - The current judge route to a manual root is terminal `HUMAN_REDRAW_REQUIRED`, and the CLI only prints a next action for `JUDGE_BLOCK`. Adding `AWAITING_REREAD` requires consumer updates, not just an enum member. Recommendation: add explicit `AWAITING_REREAD` handling in `cmd_run()`/`cmd_judge()` output, state ledger summaries, and tests. Keep it out of `TERMINAL_STOP` and `ADVANCE_OK`, but make the CLI print the sub-agent re-read protocol the same way it prints the stochastic resample command today.

4. [minor] `src/agent/execution/routing.py:10` / `AI_agent/guides/new_case_guide.md:81` / `AI_agent/guides/new_case_guide.md:118` - Several docs still describe `0_reading` auto retry as future VLM-runner wiring or manual-only human redraw. The proposal intentionally changes the dev model to a main-Agent spawned cold-start sub-agent. Recommendation: update the protocol docs and `routing.py` docstring in the same PR so "manual by default, sub-agent reread when policy-enabled" is the canonical language.

5. [minor] `scripts/tool_scripts/record_baseline.py:117` - Debt 1 is confirmed: `record_baseline()` never reads `1_correction/corrections.json`. The proposed surfacing is code-only and safe, but the summary shape must tolerate heterogeneous audit entries. LLM A0 entries can have `id`, `stage`, `method_profile`, `source_ids`, `changes_topology`, `candidates`, and rich values; deterministic-core entries can be narrower, with `rule_id`, `stage`, `target`, `axis`, `original_value`, `resolved_value`, `delta`, and `tolerance_name`. Recommendation: preserve full `conflicts[]` and `unsupported[]`, cap/summarize `corrections[]`, include counts by kind and by `rule_id`, and include the sidecar path/presence status.

6. [minor] `scripts/tool_scripts/record_baseline.py:197` / `src/agent/execution/orchestrate.py:66` - Do not silently merge full `conflicts[]`/`unsupported[]` into the existing gate `flags` list. That list is currently derived from `CheckReport` disposition and feeds the gate report. Recommendation: surface conflicts/unsupported prominently in the new audit section and optionally add one count-level audit warning to the report/checklist. If existing `baseline["flags"]` is augmented, mark entries as derived from `corrections_summary` and do not mutate gate counts.

7. [minor] `AI_agent/logs/review/request/2026-06-22_audit_attribution_and_auto_reread_proposal.md:54` - Model/effort escalation per re-read attempt is discipline-safe only if it is predeclared and logged, not chosen from judge commentary. Recommendation: use an attempt-indexed runner profile ladder, keep judge notes, prior attempts, and gt out of the re-read prompt, and log model/effort per attempt. Prefer source-fidelity levers first where available: original-resolution images, deterministic reading linter improvements, stricter output schema, and independent OCR channels.

## Open Questions

1. **New `AWAITING_REREAD` status?** Yes. Use a distinct non-terminal status rather than overloading `HUMAN_REDRAW_REQUIRED`; the latter means the automatic path is unavailable. Keep it out of `TERMINAL_STOP` and `ADVANCE_OK`. Update CLI handling, state summaries, docs, and tests for both default-false and enabled behavior.

2. **Where should `reading_runner_available` live?** Put it on `RunPolicy` with default `False`. The orchestrator should stay pure decision logic with injected callables and must not spawn the sub-agent. Do not infer availability from the existing `draw_fn`; current `0_reading` `draw_fn` only validates flat files. The actual sub-agent spawn and artifact installation belong to the main-Agent/runner protocol.

3. **Is model/effort escalation blind-safe?** Yes, if it is an attempt-indexed, preconfigured runner ladder and not adaptive prompt repair from judge feedback. It does not teach-to-test by itself. Better or complementary safe levers are higher-fidelity source images/crops, independent OCR, stricter reading schema/linter checks, and cold-start independent samples with no prior strokes or judge commentary.

4. **`corrections_summary` shape and flags?** Use a hybrid shape: counts by `corrections/conflicts/unsupported`, counts by `rule_id` and/or `stage`, capped correction rows with `id/rule_id/target/source_ids/original_value/resolved_value/delta/changes_topology`, and full conflict/unsupported entries. Keep the raw sidecar path referenced. Do not put full conflict/unsupported entries into gate flags; add a prominent report section and, if needed, one count-level derived audit warning.

5. **Bundle or split?** Split is cleaner. Debt 1 is small, code-only, and immediately valuable. Debt 2 touches orchestration state, policy, CLI protocol, docs, and tests. If they are kept in one PR for narrative reasons, separate the commits and tests clearly so the audit surfacing can land even if the re-read runner needs another pass.

## Architecture Check

No D1-D5 violation in the intended design. Debt 1 strengthens attribution. Debt 2 implements D3/D4 by putting the second image-grounded attempt in the judge plus re-read loop, not in image-blind correction. The design would violate D1-D5 only if the reading sub-agent receives judge commentary, prior attempts/strokes, gt/reference answers, or if correction is given image access.

## Blast Radius

Debt 1: `record_baseline.py` and focused baseline-report tests. No schema, geometry, deterministic core, or EP artifact change.

Debt 2: `step_orchestrator.py`, `policy.py`, `run_stage.py`, `tests/test_step_orchestrator.py`, protocol docs, J0 rubric, and likely the `routing.py` docstring. Default `reading_runner_available=False` must preserve all existing manual-stop tests.

## Review Ask

I could not verify an actual sub-agent runner implementation locally because none exists in the repo. Before execution, define the exact re-read handoff: prompt inputs, model ladder, output file names, where the sub-agent writes, how the flat `0_reading` working copy is updated, and which command records/re-gates the new attempt.
