# sm25 Lite regularization runtime observer notes

## Boundary

- Frozen run tree: `D:\EnergyPlus-Agent-worktrees\lite-sm25-run-20261010`, commit `3484cae5`, domain `domain-v57-20261010`, runtime `runtime-v2-20261009`.
- Run: `AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1`.
- Observation was read-only. It used `observe_runtime_accounting.py`, `scripts/dev/observe_run.py` through their read-only capture resolver, and direct JSON metadata reads. It did not open an `EventStore`, invoke a model or HTTP API, read GT, or read/restate hidden reasoning.
- Times below are minutes from the first saved event unless an absolute UTC timestamp is shown. A role is called complete only after an accepted submission and lifecycle stop; accounting completeness alone is not role completion.

## Initial autonomous six-task delegation

| Task | First request | First trial | Submission / stop | Requests | Tool behavior | Outcome |
|---|---:|---:|---:|---:|---|---|
| elevation_west | 0.0 | n/a | accepted 4.2 | 10 | 2 image views, 7 profiles, 1 submit | autonomous accepted |
| elevation_east | 0.0 | n/a | accepted 5.9 | 10 | 2 image views, 9 profiles, 1 region overview, 1 BIM reference, 1 submit | autonomous accepted |
| elevation_north | 0.0 | n/a | rejected 5.5, accepted 6.0 | 8 | 3 image views, 7 profiles, 2 submits | autonomous accepted after one schema repair |
| elevation_south | 0.0 | n/a | accepted 6.2 | 10 | 5 image views, 8 profiles, 1 region overview, 1 submit | autonomous accepted |
| plan_f1 | 0.1 | 33.6 | stopped about 60.0 | 21 | 10 image views, 7 profiles, 1 block view, 5 trials | no accepted draft; timed out during request 21 |
| plan_f2 | 0.1 | never | stopped 46.9 | 40 | 22 image views, 28 profiles, 0 trials | child model-call budget exhausted; no draft |

The four elevation tasks ran in parallel and all submitted by 6.2 minutes. North's first submission added unsupported `floor_id`; the server rejected it with an exact schema error, and the next submission was accepted about 0.5 minutes later. There were no model failures in the elevation tasks.

### Plan F1 request timing and cache facts

The third request ran from `2026-10-10T09:25:28.121576Z` to `09:36:11.103034Z`: 642.981 s wall time, 45,576 prompt tokens, 0 cached tokens, 24,594 image tokens, 10,577 completion tokens, and 10,403 reported reasoning tokens. The fourth ran from `09:36:13.877029Z` to `09:46:10.061755Z`: 596.185 s, 59,179 prompt, 0 cached, 26,299 image, 7,653 completion, and 7,476 reasoning tokens. Both returned `finish_reason=tool_calls`. The 642.981 s and 596.185 s values are complete request wall times; reported reasoning token counts do not isolate reasoning wall time.

The configured per-request ceiling was `10800 / (6 + 1) = 1542.857 s` (25.71 min), so neither long request hit its own timeout. Across the F1 responses carrying usage, the final observed cache ratio was 692,480 / 1,087,051 prompt tokens (63.70%); requests 3-5 each reported zero cached tokens. F2 reported 2,468,352 / 2,815,361 (87.67%). These are provider/runtime facts only; this note does not attribute the difference to a prefix policy, provider TTL, or another cause.

### Plan F1 trial sequence

F1 did not early-trial: eight observation calls occurred before its first trial, past the recorded reminder threshold of six. Every trial resent one complete plan with 10 dimension chains (5 x, 5 y), 68 total dimension segments, and source references on every chain. The chain count and segment count remained unchanged across all five trials.

1. At 33.6 min, trial 1 failed format validation because the five y chains included unsupported `direction` and `origin_m` fields. The next trial removed those fields.
2. At 35.7 min, trial 2 failed on a dangling `wall-col-left` endpoint, 79.5 px from `wall-col-6`; the tool did not snap or change coordinates.
3. At 39.7 min, trial 3 reached dimension regularization. Chain `YL2` would have moved `wall-col-bottom` by 0.045946 m and detached it from `wall-col-left`, so the regularizer rejected the move. This is direct evidence that the submitted chains entered code regularization and that topology protection blocked an independent move. The returned `next_action.objects` was only `plan.basis`, which is less localized than the reason text.
4. At 43.5 min, trial 4 localized an opening host error to `plan.openings[1]` (D2): one full space host but not wholly on the footprint boundary.
5. At 47.9 min, trial 5 showed the same host class at `plan.openings[6]` (D6), after D2 had been passed.

After trial 5, the model-visible text JSON and structured result agreed on status, target object and D6 coordinates. The six subsequent observation boxes all covered or surrounded that reported D6 location. F1 had two context compactions. The post-trial-5 compaction replaced older history through trial 4 but not trial 5; later boxes stayed on D6, so there is no observed current-task loss.

At the 60-minute role limit, request 21 was still in flight. Lifecycle recorded `failure: timeout` at `model_request`, then stopped with `money_cny_usage_unavailable`. The receipt has `answer=null`, `usage_complete=false`, 21 model calls and 24 tools. All five trial results had `candidate=null` and `draft=null`, and no reader artifact was saved. The captured event stream still contains each complete trial input, but that is not a runtime failed draft and any reuse requires explicit human assistance.

### Plan F2 initial autonomous failure

F2 never called `trial_plan_bim` or `submit_plan_reading`. It stopped with `child_model_budget_exhausted` after 40 model calls and 51 tools. Its receipt records `first_trial=null`, 50 observation calls before first trial, and a reminder threshold of six. `answer=null`; no reader artifact or candidate/draft exists. The trial workspace contains only its initialized input/image.

All 22 `view_image` argument payloads were distinct; 21 boxed calls used 21 distinct boxes. All 28 profile argument payloads were distinct; the 28 calls used 23 distinct boxes, so five calls revisited an existing box across four repeated-box groups (one box was used three times). One context compaction occurred. These counts establish repeated-region observation, not whether any revisit was useful.

Because F2 produced no full plan attempt, an assisted continuation cannot be described as a local geometry edit or autonomous recovery. It is an assisted whole-floor reconstruction in the same run, using the original image and explicit human transcription, while preserving the failed autonomous record.

## Initial-phase accounting

At the end of the first six tasks, the run had 99 requests, 98 responses, one failed request, zero pending requests, and 130 tools. Request 21 has a settlement event, but its usage is missing and `estimated_cost=null`. The known estimated cost across the 98 responses carrying usage was CNY 9.1655892 against the CNY 20 ceiling, and their accounting audit found zero mismatches. Total actual cost remains unknown because the timed-out F1 request has no usage record.

The initial `delegate` process exited with code 0 after persisting the per-task outcomes. That process exit means dispatch finished; it does not turn the two plan-reader failures into successful tasks. F1's unknown usage left the runtime budget state at `money_cny_usage_unavailable`, so no further model request is authorized unless the existing runtime exposes a formal recovery entry that preserves its ledger. No ledger edit, runtime mutation, or replacement blank run is part of this observation.

## Recovery outcome

No assisted recovery was dispatched. The runtime has no formal ledger-preserving recovery entry, so the run closes with the two plan-reader failures above; there is no human-assisted result to include in the outcome.
