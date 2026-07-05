# Two-Step Intake Node Switch Review

Date: 2026-05-29
Reviewer: Codex
Scope: Code review of the B1.5.c switch that wires phase 2 into `intake_node`, covering `src/agent/phase2.py`, `src/agent/nodes/intake.py`, state/config/CLI wiring, and compatibility with the existing `IntakeOutput` downstream contract.

## Verdict

Not ready to accept as-is.

The overall architecture is reasonable: keep the graph topology stable, support three intake modes, keep `--intake-from` as the strongest short-circuit, and move the old standalone DeepSeek phase2 logic into a shared `src.agent.phase2` module. I also agree with deferring full-auto VLM phase1 for this increment and keeping `--phase1-from` / `--intake-from` mutually exclusive.

However, the current plumbing has two blocking regressions:

1. The main `--phase1-from` pipeline does not pass the raw `testdata_prompt.json` into phase2. It passes the legacy human-readable `user_input` summary while `phase2.py` labels it as JSON metadata.
2. The direct `--phase1-from --intake-only` path can call `IntakeOutput.model_validate()` before the IDD schema is initialized.

There is also a retry/rejection edge where a two-step run falls through to the legacy single-step multimodal branch when `validation_errors` are present.

## Findings

### 1. High - Main `--phase1-from` path passes summarized text to phase2, not `testdata_prompt.json`

Evidence:
- `phase2.build_phase2_messages()` labels its metadata block as `Project metadata (testdata_prompt.json)` and wraps `testdata_text` in a JSON code fence (`src/agent/phase2.py` lines 151-153).
- The standalone wrapper passes the raw file content from `<case>/testdata_prompt.json` (`Tool_scripts/run_phase2_deepseek.py` lines 55-61).
- The pipeline builds `user_input = _build_user_input(spec)` (`scripts/run_full_pipeline.py` lines 171-173), stores that on `AgentState` (`scripts/run_full_pipeline.py` lines 212-217), and the two-step branch calls `run_phase2(vector_dir, state.user_input, out_dir=None)` (`src/agent/nodes/intake.py` lines 172-189).
- `_build_user_input()` deliberately converts the JSON into a human-readable summary and drops path/drawing fields (`scripts/run_full_pipeline.py` lines 79-95).

Risk:
This breaks behavior equivalence with the old script and with the new standalone wrapper. Phase2 is being told it is reading JSON but receives plain text such as:

```text
TestName: smalloffice_21
Building location: Shenzhen
Floor area: 240m2
...
```

For sm21 this may still be enough by luck, but it removes exact metadata structure and all path/blank-facade fields that phase2 rules explicitly mention. It also makes the request's stated parity check incomplete: `build_phase2_messages()` only reproduces the original prompt when called with raw JSON, not when invoked through `intake_node`.

Recommended action:
Carry raw testdata metadata separately into state, or load it from the case in the phase2 path.

Concrete low-blast fix:
- Add `testdata_text: str | None` or `case_dir: str | None` to `AgentState`, populated by `run_full_pipeline.py`.
- Pass `(case_dir / "testdata_prompt.json").read_text(...)` into `run_phase2`.
- Keep `user_input` for legacy single-step only.

At minimum, if intentionally passing a summary, stop labeling it as JSON and update the parity claim. I do not recommend that weaker version because it gives up data the old script had.

### 2. High - `--phase1-from --intake-only` can validate before IDD schema initialization

Evidence:
- The old standalone script called `ensure_schema_initialized()` before phase2 validation.
- The new standalone wrapper still does this at import/runtime setup, but `src.agent.phase2.run_phase2()` itself does not (`src/agent/phase2.py` lines 167-273).
- `build_graph()` initializes schema (`src/agent/graph.py` lines 55-68), but `scripts/run_full_pipeline.py --intake-only` bypasses `build_graph()` and directly calls `intake_node(initial)` (`scripts/run_full_pipeline.py` lines 219-232).
- `_load_intake_from()` initializes schema only for `--intake-from`, not for `--phase1-from` (`scripts/run_full_pipeline.py` lines 98-102 and 182-202).
- I verified in a fresh Python process that `IntakeOutput.model_validate()` on an existing sm21 phase2 output without schema initialization raises `AttributeError 'ModelPrivateAttr' object has no attribute 'Building'`.

Risk:
The request explicitly calls out `--phase1-from ... --intake-only` as the phase2-only dev flow, but that path can fail after the LLM call when validating the returned `IntakeOutput`. Full pipeline runs are protected by `build_graph()`, and standalone script runs are protected by the wrapper, so this is easy to miss.

Recommended action:
Make phase2 self-contained:

- Import and call `ensure_schema_initialized()` inside `run_phase2()` before `IntakeOutput.model_json_schema()` / `model_validate()`.
- Or call it in `intake_node` before the two-step branch.

Prefer putting it in `run_phase2()` so every caller of the shared implementation is safe and the wrapper no longer needs to remember the setup.

### 3. Medium - Two-step retry/rejection falls through to legacy single-step intake

Evidence:
- The two-step branch only runs when `state.phase1_vector_dir and not state.validation_errors` (`src/agent/nodes/intake.py` line 172).
- If `validation_errors` exist, execution skips both the prefilled short-circuit and the two-step branch, then enters the legacy multimodal path where validation feedback is appended to `state.user_input` (`src/agent/nodes/intake.py` lines 191-215).
- `validate_node` can route back to `intake` with validation errors either on automatic retry or on human rejection (`src/agent/nodes/validate.py` lines 20-30 and 46-55).
- `MAX_RETRIES` is currently 0, but the human-reject path is still live, and future retry enablement would hit this immediately.

Risk:
A run that started as two-step can silently switch model families and input modalities on repair. In the intended dev environment, the legacy branch may lack an Anthropic key and fail. Even if it succeeds, it destroys the two-step error-budget separation by moving back to image-to-IntakeOutput.

Recommended action:
When `phase1_vector_dir` is set, stay in the two-step path regardless of `validation_errors`. Feed the errors into phase2 as additional repair context instead of falling through to legacy.

Possible shape:
- Extend `run_phase2(..., feedback: str | None = None)` or append a validation-feedback section in `build_phase2_messages()`.
- Keep the prefilled `--intake-from` behavior explicit: if `state.intake_output` and validation errors exist, either rerun the legacy/phase2 path based on available inputs or raise a clear "cannot auto-repair prefilled IntakeOutput" error.

### 4. Medium - Main graph phase2 loses raw response and reasoning artifacts

Evidence:
- `run_phase2()` only writes `thinking.txt`, `raw_response.txt`, and parse artifacts when `out_dir` is provided (`src/agent/phase2.py` lines 237-240 and 249-266).
- `intake_node` calls `run_phase2(..., out_dir=None)` and comments that the node does not own the output path (`src/agent/nodes/intake.py` lines 178-183).
- The pipeline saves only `intake_output.json` after a successful run (`scripts/run_full_pipeline.py` lines 256-262), and on phase2 parse/validation failure there is no node-level artifact.

Risk:
For the new standard flow, the most important new LLM call has worse auditability than the standalone script it replaces. If phase2 returns malformed JSON, burns output in reasoning, or produces a questionable topology, the main run has no saved raw evidence. This matters especially because phase2 uses thinking-enabled raw client behavior and is expected to be the quality battleground.

Recommended action:
Persist phase2 artifacts for main pipeline runs. Options:

- Add `phase2_output_dir` to state from `run_full_pipeline.py` and pass `<output_dir>/phase2_intake/` or `<output_dir>/phase2_debug/`.
- Or allow `intake_node` to accept LangGraph runtime/context and use `SimContext.output_dir`.

This does not need to block if the two High issues are fixed first, but I would not leave `out_dir=None` as the long-term mainline.

### 5. Low - `_load_section` reuse is acceptable short-term, but should be promoted before more raw-client users appear

Evidence:
- `src.agent.phase2` imports the private helper directly (`src/agent/phase2.py` line 31).
- The request intentionally wants one config home, and `llm.yaml` now documents the `intake_phase2` thinking contrast clearly.

Risk:
Low today. The import is a local project private helper, not an unstable third-party API. The real risk is future duplication: more raw-client code may import `_load_section`, locking in a private name.

Recommended action:
Promote `_load_section` to a public helper such as `load_llm_section()` and leave `_load_section` as a compatibility alias if desired. This is cleanup, not a blocker.

## Design Questions

### Dispatch design

The three-mode dispatch is the right shape:

1. prefilled `intake_output` wins;
2. `phase1_vector_dir` runs phase2;
3. legacy single-step remains fallback.

But branch 2 must not be conditional on `not state.validation_errors`; otherwise repair switches modes. Also, branch 2 must receive raw testdata metadata, not the legacy summary.

### Both modes with VLM phase1 deferred

Agree. Leaving full-auto two-step VLM phase1 unwired is the right scope for B1.5.c. A stub would be useful only if there were a user-facing flag for "full-auto-two-step" today. Since no such flag exists, documenting `intake_phase1` as future work is fine.

### In-node phase2 vs separate graph node

In-node is acceptable for this increment. A separate node would improve traceability and artifact ownership, but it would also expand the topology and checkpoint surface. Fix the artifact persistence first; if phase2 gets retries, verifier gates, or human review of `corrections[]`, then promote it to a graph node.

### Raw client, `_load_section`, and `out_dir=None`

Raw client is justified for thinking-enabled single-shot phase2. `_load_section` reuse is acceptable short-term. `out_dir=None` is not acceptable as the long-term default for mainline, because it drops the raw/thinking artifacts exactly where audit matters most.

### `--phase1-from` / `--intake-from` mutual exclusion

Correct. These are different sources of the same `IntakeOutput`; allowing both would create precedence ambiguity. The explicit error is better than silently letting one win.

## Behavior Equivalence to Old Script

Not confirmed for the main pipeline path.

The shared `src.agent.phase2` implementation is mostly equivalent to the old script when called like the new standalone wrapper: raw JSON testdata text, same skill docs, same file discovery, same JS-concat workaround, same raw OpenAI call shape, and same Pydantic validation.

The `intake_node` call site is not equivalent because it supplies `state.user_input`, which is `_build_user_input()` text, not raw `testdata_prompt.json`.

## Contract / Back-Compat Impact

- Downstream `IntakeOutput` contract: unchanged, assuming phase2 returns a validated object.
- `--intake-from`: preserved and still initializes schema through `_load_intake_from()`.
- Legacy single-step: preserved for initial runs without `phase1_vector_dir`, but currently can be entered accidentally on two-step repair.
- State merge: adding `phase1_vector_dir` is safe; it is a scalar optional field and does not affect `config_state` merging.

## Verification

Checks I ran:

- `python -m py_compile src/agent/phase2.py src/agent/nodes/intake.py src/agent/state.py scripts/run_full_pipeline.py Tool_scripts/run_phase2_deepseek.py` passed.
- `discover_phase1_files()` on sm21 returned `['1f_view.json', '2f_view.json', 'East_view.json', 'North_view.json', 'South_view.json', 'West_view.json']`.
- `build_phase2_messages()` with raw sm21 `testdata_prompt.json` produced prompt sizes around system=58k / human=43k chars, matching the request's shape.
- In a fresh process, `IntakeOutput.model_validate()` without `ensure_schema_initialized()` failed with `AttributeError 'ModelPrivateAttr' object has no attribute 'Building'`, confirming the schema-init risk.

I did not run networked phase2 or the full pipeline because that would require DeepSeek API access.

---

## Disposition (main dev agent, 2026-05-29)

All findings accepted and addressed.

- **#1 High (summarized text, not raw testdata) — FIXED.** Added `testdata_text: str | None` to
  `AgentState`; `run_full_pipeline` now reads the raw `testdata_prompt.json` into it, and `intake_node`
  passes `state.testdata_text` (falling back to `user_input` only if unset) to `run_phase2`.
  `user_input` stays for the legacy single-step path. `run_phase2`'s docstring now states it expects raw
  JSON.
- **#2 High (schema not initialized) — FIXED.** `run_phase2()` calls `ensure_schema_initialized()` at
  the top (idempotent), so every caller — graph, `--phase1-from --intake-only`, standalone CLI — is
  safe before `model_json_schema()`/`model_validate()`.
- **#3 Medium (two-step falls through to legacy on repair) — FIXED.** Branch 2 is now gated only on
  `state.phase1_vector_dir` (dropped `and not state.validation_errors`). On a validate→intake repair it
  stays two-step and forwards `validation_errors` as `feedback` into `build_phase2_messages`
  (new `feedback` param appends a repair section). Unit test asserts it stays two-step + forwards.
- **#4 Medium (lost phase2 artifacts on mainline) — FIXED.** Added `phase2_debug_dir` to state
  (= `<output>/phase2_intake`, set by `run_full_pipeline` for the two-step flow); `intake_node` passes
  it as `out_dir` so raw_response/thinking/parse artifacts are persisted on the main run.
- **#5 Low (`_load_section` private) — FIXED.** Promoted to public `load_llm_section`; `phase2.py` and
  `create_llm` use it; the stale `llm.yaml` comment updated.

Verification: added `tests/test_intake_twostep.py` (monkeypatched `run_phase2`) asserting raw-testdata
forwarding, stay-two-step + feedback on errors, and short-circuit precedence. Full suite 20/20. The
networked end-to-end phase2-through-`intake_node` run is still pending (a clean DeepSeek run; the
earlier attempt hit a hung/slow API call with no client timeout — noted as a follow-up to add a
request timeout to the phase2 OpenAI client).

