# Review Request — Recognition→Modeling capability design direction (tolerance-based regeneration)

Date: 2026-05-28
Requested by: Claude (main dev agent)
Suggested reviewer: Codex / Gemini (fresh model, cross-check)

## Nature of this review

**This is a DESIGN review, not a code review. Nothing is implemented yet.** We are about to commit
to a significant change in how two-step intake `phase2` turns drawings into an EnergyPlus model, and
we want a second model to stress-test the *judgment* before we rewrite `skills/energyplus_mcp_twostep/phase2/rules.md`
and author a new "architectural common-sense" priors doc. Please challenge the reasoning, the
evidence interpretation, and the open decisions — do not look for bugs in code.

## Background (self-contained — you have no session context)

Pipeline = two-step intake. **phase1** = image → semantic vector JSON (image-bound perception:
wall/window strokes + dimension chains + confidence; "no topology inference"). **phase2** = vector
JSON → `IntakeOutput` (image-blind topology/reasoning: zones, surfaces, fenestration). Downstream =
9 DeepSeek subagents build the IDF, then EnergyPlus. The two-step split exists to enforce **error
budget separation** (perception errors attributable to phase1; reasoning errors to phase2).

### The triggering experiment (sm21)

We held phase1 fixed (one vector JSON) and ran phase2 with **three different models** (DeepSeek
script / Opus subagent / Sonnet subagent — all image-blind, zero shared context), downstream all
DeepSeek. Case sm21 = 2-storey office, 15×8 m, furniture/door/dim-chain noise.

Key findings (full write-up in the capability doc below, §2):
- **phase1 was internally self-contradictory.** For the F2 south partitions, phase1's *wall strokes*
  said x=4.95/7.50/10.05 (rooms 4.95/2.55/2.55/4.95 — "two big, two small middle", WRONG), but the
  *dimension chain it also transcribed* encoded partition centerlines at 3.75/7.50/11.25 (four equal
  3.75 m bays — the true design). phase1 emitted the **estimated stroke coordinates as if measured**.
- Three phase2 models diverged: **Opus** read the dim chain, overrode the strokes ("trust the dim"),
  got the correct equal bays, EP completed (12 warnings, 1 CHKSBS). **Sonnet** faithfully reproduced
  phase1's strokes (its proper job) → **EP SIGSEGV (exit 139)**. **DeepSeek** snapped partitions to
  *window-edge* dim points (4.11/5.31/10.89) → a 1.2 m phantom office, but EP completed cleanly (6
  warnings).
- **Sonnet's segfault root cause (vertex-confirmed):** phase1 estimated the *same* partition at 4.90
  on floor 1 and 4.95 on floor 2 (a 5 cm cross-drawing jitter). Faithful reproduction → the cross-floor
  InterZone ceiling/floor split produced two **5 cm × 3 m degenerate sliver surfaces**
  (`F1_SM_Office_Ceiling_S2` = x[4.90,4.95]) → EP crashes in input processing before writing `.err`.
- **Two lessons:** (1) *EP-completion ≠ geometric correctness* (DeepSeek's worst geometry ran cleanest;
  Sonnet's faithful geometry crashed). (2) *Faithful-to-phase1 ≠ correct* when phase1 self-contradicts.

### The proposed direction (user, this session)

EnergyPlus only needs **qualitative** correctness (zone closure, adjacency, window∈parent, window
not crossing zones) plus **quantitative within tolerance** (areas/WWR ±~5%). Real drawings inherently
"don't add up" (missing/erroneous dims; axis-vs-outer-edge datum conflicts; equal rooms perturbed by
wall thickness). So: **stop rigidly transcribing numbers; let phase2 self-correct within tolerance and
re-generate, with qualitative constraints outranking quantitative ones.** Four concrete ideas (gap
closure, 50 mm grid + dim-chain-sum alignment, an architectural common-sense priors library,
qualitative>quantitative constraint hierarchy).

My (main-agent) architectural position, baked into the doc: **all regeneration belongs in phase2;
phase1 stays faithful-perception + provenance/confidence** (preserve error budget); **a `corrections[]`
audit log is a hard requirement** (so relaxing constraints doesn't destroy explainability/evaluability);
**priors are tie-breakers, never overrides of consistent measured data.**

## Scope to review (challenge these)

1. **The core architectural call: regeneration in phase2, phase1 stays faithful.** Is this the right
   place to put "reconcile strokes vs dim-chain + close gaps + apply priors"? Argue for/against an
   explicit intermediate *reconciliation pass* instead. Does putting it in phase2 risk re-muddying the
   error budget the two-step split was designed to protect? Is the `corrections[]` audit log a
   sufficient mitigation, or is it theater?
2. **Evidence interpretation.** Is the sm21 diagnosis sound — especially (a) the claim that the root
   cause is phase1 *internal contradiction* (not perception failure), and (b) that "EP-completion ≠
   correctness"? Any alternative reading of why Sonnet crashed and DeepSeek didn't?
3. **The 4 improvement directions (capability doc §5)** — for each, is it sound, and what's the failure
   mode I under-weighted?
   - §5.1 gap closure + **global-consistent axis snapping** (my refinement: the real fix isn't "close
     any gap" but "snap all references to one canonical partition axis set", which is also the segfault
     fix). Is canonical-axis snapping correct, and what breaks it (e.g. genuinely staggered walls,
     non-orthogonal)?
   - §5.2 50 mm coordinate grid + "child dim-chain sum = total" closure correction; areas/WWR on
     relative error. Right granularity? Any case where 50 mm snapping itself *creates* the degeneracy?
   - §5.3 architectural common-sense priors as **tie-breakers not overrides** (priority: consistent
     measured > dim-chain-derived > prior). Is the red line enforceable, or will priors inevitably
     override real-but-unusual designs (e.g. a real 1.2 m service room)?
   - §5.4 qualitative>quantitative hierarchy split into *generation rules* (phase2) + *verification
     self-check*. Is the specific ranking right (zone closure / adjacency / window∈parent / elevation-
     window-position > plan-window-position > raw dim values)? Missing invariants?
4. **The 4 open decisions (capability doc §6).** Give your independent recommendation on each,
   especially #1 (phase2-rewrite vs separate reconciliation pass) and #2 (corrections[] as a hard
   requirement).
5. **Interaction with existing contracts.** Does any of this threaten: the downstream `IntakeOutput`
   contract (the 9 subagents expect specific spec fields), the clean-spec policy for the skill lib, or
   the phase1↔phase2 decoupling (phase2 must remain runnable by a pure-text model with no image
   access)?
6. **Scope/sequencing sanity.** Is "rewrite phase2/rules.md into a constraint-solver + add a priors
   doc + small phase1 dual-channel change" the right first increment, or are we trying to do too much
   before B1.5.c (intake_node serial rewrite)?

## Files to review

- **Primary**: `AI_agent/capability/recognition_modeling_capability.md` (the design doc capturing
  this round — framing §1, sm21 evidence §2, philosophy §3, architectural call §4, 4 directions §5,
  open decisions §6).
- **Current phase2 spec (the thing we'd rewrite)**: `skills/energyplus_mcp_twostep/phase2/rules.md`
  (note: it already has a §2.5 "trust the dim" rule — Opus used it; we'd elevate that into a full
  doctrine).
- **Error-budget background**: `AI_agent/capability/floorplan_redraw_strategy.md` (two-step strategy +
  POC history; §10 the 2026-05-22 design discussion).
- **phase1 contract (for the "stays faithful + dual-channel" proposal)**:
  `skills/energyplus_mcp_twostep/phase1/guide.md` + `phase1/pen_library.md`.
- **Evidence artifacts (optional, to verify the diagnosis)**: under
  `test_data/SmallOffice_TwoStep/smalloffice_21/` — `phase1_vector/2f_view.json` (the
  stroke↔dim-chain contradiction), `phase2_intake/{deepseek,opus,sonnet}/intake_output.json` (the
  three zone_specs), `output_opus/eplusout.err` (12 warn, completed) vs `output_sonnet/` (empty .err,
  segfault).

## Explicitly out of scope (do not flag)

- The `AI_agent/` documentation reorg into subfolders done this session (mechanical; links already
  script-validated, 0 regressions vs HEAD baseline).
- The pre-existing dangling doc links (deleted prompt templates, planned `eval/`/`deploy/` dirs,
  out-of-repo `memory/` refs) — known, unrelated to this design.
- Implementation details / code — nothing is implemented yet.
- Specific threshold *values* (500 mm gap, 50 mm grid, ±5%) — we want the *framework* reviewed; exact
  numbers are deliberately unlocked.

## Acceptance criteria (what a useful review delivers)

- [ ] A verdict on the core architectural call (regeneration-in-phase2 + phase1-faithful + corrections log)
- [ ] An independent recommendation on each of the 4 open decisions (§6)
- [ ] For each of the 4 directions (§5): sound? + the under-weighted failure mode
- [ ] Confirmation or refutation of the sm21 root-cause diagnosis (esp. "phase1 internal contradiction"
      and "EP-completion ≠ correctness")
- [ ] Any threat to the downstream IntakeOutput contract / clean-spec policy / phase1↔phase2 decoupling
- [ ] Graded findings (High/Medium/Low) with evidence + recommended action

Please write the review to
`AI_agent/logs/review/review/2026-05-28_recognition_modeling_capability_review.md`
with a verdict + graded findings, matching the prior reviews' format.
