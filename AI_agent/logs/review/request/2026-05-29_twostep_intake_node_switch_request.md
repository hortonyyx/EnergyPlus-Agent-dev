# Review Request — Two-step intake architecture switch (intake_node serial rewrite)

Date: 2026-05-29
Requested by: Claude (main dev agent)
Suggested reviewer: Codex / Gemini (fresh model, cross-check)

## Nature of this review

**Code review** of the B1.5.c architecture switch: wiring the two-step intake (phase 1 perception →
phase 2 topology) into the main pipeline so it is the standard flow, while keeping the legacy
single-step path. Nothing about phase1/phase2 *rule content* changes here — this is the plumbing that
makes `intake_node` run phase 2 in-process. Please check the dispatch logic, the config/entry-point
wiring, the contract preservation, and back-compat.

## Background (self-contained)

Two-step intake: **phase 1** = image → semantic vector JSON (image-bound; produced half-manually in a
Claude Code Opus session during dev — no Anthropic API key in this environment). **phase 2** = vector
JSON → `IntakeOutput` (image-blind topology reasoning; DeepSeek with thinking on). Downstream = the 9
DeepSeek subagents + EnergyPlus, **unchanged**. The split exists to keep the error budget separable.

Until now phase 2 lived only in a standalone script (`run_phase2_deepseek.py`) and the pipeline took a
finished `IntakeOutput` via `--intake-from`. This change makes `intake_node` itself run phase 2.

## What changed

- **New `src/agent/phase2.py`** — the single implementation of phase 2 (moved out of the script):
  `discover_phase1_files`, `build_phase2_messages`, `run_phase2(vector_dir, testdata_text, out_dir=None)
  -> IntakeOutput`. Uses a **raw OpenAI client** (not langchain) with DeepSeek thinking ON — phase 2 is
  single-shot and langchain_openai's structured-output would burn the budget on reasoning_content.
  Model/endpoint/thinking come from the **`intake_phase2` section of `llm.yaml`** (single config home).
- **`src/agent/nodes/intake.py`** — `intake_node` now has 3 dispatch modes:
  1. pre-filled `state.intake_output` → short-circuit (existing `--intake-from`),
  2. `state.phase1_vector_dir` set → run phase 2 (the new two-step dev default),
  3. else → legacy single-step multimodal `intake` call (unchanged).
  The graph still always receives exactly one validated `IntakeOutput`.
- **`src/agent/state.py`** — added `phase1_vector_dir: str | None` to `AgentState` + `AgentStateUpdate`.
- **`src/configs/llm.yaml`** — added `intake_phase2` (deepseek-v4-pro, thinking=enabled) and a commented
  `intake_phase1` future slot (full-auto VLM phase 1, not wired).
- **`scripts/run_full_pipeline.py`** — added `--phase1-from <dir>` (mutually exclusive with
  `--intake-from`); sets `phase1_vector_dir`; docstring rewritten (TWO-STEP / INTAKE-FROM / AUTO flows).
- **`Tool_scripts/run_phase2_deepseek.py`** — slimmed to a thin CLI wrapper over `src.agent.phase2`
  (so script and pipeline can't drift).
- **`AI_agent/guides/new_case_guide_twostep.md`** — §二路径B / §三 / §四 updated for `--phase1-from`.

## Design decisions made (challenge these)

1. **Both modes supported, default half-manual.** Per user direction: architect for both
   (vectors→phase2 *and* full-auto VLM), but dev currently runs phase 1 half-manually. So the full-auto
   VLM phase 1 is left as a documented, commented `intake_phase1` slot + the `else` branch is still the
   *legacy single-step* call (which is itself an auto image→IntakeOutput path when an Anthropic key
   exists). **Is leaving full-auto-two-step-VLM unimplemented (vs a stub that raises) the right call, or
   should `intake_node`'s `else` branch be restructured now to make the VLM-phase-1 slot explicit?**
2. **Phase 2 in `intake_node` vs a separate graph node.** I kept the graph topology identical
   (intake_node internally calls `run_phase2`), matching plan B1.5.c wording. Alternative: a dedicated
   `phase2` graph node between `intake` and the phase-1 fan-out. Is the in-node call the right altitude,
   or does a separate node buy enough (observability / checkpointing) to justify the topology change?
3. **Raw OpenAI client inside the node.** `run_phase2` bypasses `create_llm()`/langchain on purpose
   (thinking + single-shot JSON). It still reads config from `llm.yaml` via `_load_section`. Is reusing
   the private `_load_section` acceptable, or should it be promoted to a public helper?
4. **`out_dir=None` in the node.** The node doesn't write phase-2 debug artifacts (raw_response/thinking)
   — the pipeline saves `intake_output.json` to the run's output dir, and the node doesn't own that path.
   Acceptable, or should phase-2 thinking be persisted for audit (and if so, where)?
5. **Mutually-exclusive `--phase1-from` / `--intake-from`.** Right guard, or should `--phase1-from`
   silently win / be allowed to co-exist?

## Scope to review

- Dispatch correctness in `intake_node` (the three branches + the `validation_errors` retry interaction
  — note `MAX_RETRIES=0`, so the retry-from-validate loop currently never re-enters intake; does the
  two-step branch behave correctly if it ever did?).
- `run_phase2` correctness vs the original script (prompt assembly parity, JSON extraction, the
  `_fix_js_concat` workaround, error/artifact handling).
- Contract preservation: downstream `IntakeOutput` (11 fields) unchanged; `state.py` merge logic
  unaffected by the new field; back-compat of `--intake-from` and the legacy single-step path.
- Config: `intake_phase2` thinking=enabled is deliberate and differs from `default` (disabled for the
  ReAct downstream) — is that contrast documented clearly enough to not get "fixed" later?

## Verification done

- Syntax/import checks green; `discover_phase1_files` + `build_phase2_messages` reproduce the original
  file set and prompt structure on sm21 (system≈58k / human≈43k chars).
- End-to-end two-step node run on sm21 via `--phase1-from phase1_vector --intake-only`:
  **[to be filled with result — running at request-authoring time]**.
- The InterZone gate (separate change, see `2026-05-29_interzone_pair_gate_request.md`) validates the
  downstream IDF; the two paths compose (new node produces IntakeOutput → unchanged downstream → gate).
- `pytest` 5/5 (run after Task 2; rerun after this change).

## Files to review

- `src/agent/phase2.py` (primary, new)
- `src/agent/nodes/intake.py` (dispatch rewrite; backup in `src_history/2026-05-29_intake_node_twostep/`)
- `src/agent/state.py`, `src/configs/llm.yaml`, `scripts/run_full_pipeline.py`,
  `Tool_scripts/run_phase2_deepseek.py`, `AI_agent/guides/new_case_guide_twostep.md`

## Acceptance criteria

- [ ] Verdict on the dispatch design (3 modes; in-node phase 2 vs separate node)
- [ ] Verdict on the both-modes-but-VLM-phase1-deferred scoping
- [ ] Confirmation `run_phase2` is behavior-equivalent to the old script
- [ ] Any threat to the downstream IntakeOutput contract / back-compat
- [ ] Opinion on the raw-client + `_load_section` + `out_dir=None` choices
- [ ] Graded findings (High/Medium/Low) with evidence + recommended action

Please write the review to
`AI_agent/logs/review/review/2026-05-29_twostep_intake_node_switch_review.md`.
