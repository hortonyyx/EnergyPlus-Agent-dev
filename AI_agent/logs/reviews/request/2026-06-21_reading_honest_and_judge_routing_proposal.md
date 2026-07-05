# Proposal — Reading-honest provenance + judge recoverability routing (sm21 Sonnet fix)

Date: 2026-06-21
Author: Claude (orchestrator)
Status: DESIGN — for Codex review before dispatching an executor
Related: `AI_agent/logs/review/request/2026-06-21_sonnet_plan_recognition_diagnosis.md`
(image-grounded diagnosis, both Codex and Claude passes), `capability/recognition_modeling_capability.md` §2–§5 (founding framework).

---

## 0. Purpose & how to review

The sm21 Sonnet recognition failures (interior dimension ticks traced as walls;
elevation doors emitted with the `window` pen) are NOT a recent regression. They
are the symptom of the **2026-06-07 founding framework having been landed on only
one side of the reading↔correction seam**. This proposal lands the missing reading
side and adds the judge routing the user asked be designed carefully.

The architecture decisions in §1 are already **user-ratified in conversation**;
Codex's job is to (a) sanity-check the articulation, (b) review the concrete
code-grounded plan in §4–§5 for correctness, blast radius, and false-positive
risk, and (c) answer the open questions in §9. Do NOT treat §1 as open for
re-litigation — review whether the implementation faithfully serves it.

Review with `sandbox=danger-full-access` (local files; otherwise the review
silently falls back to GitHub @main and will not see this file or the cited code).

---

## 1. Ratified architecture decisions (context — already agreed)

**D1. Correction stays image-blind and text-only. It is NOT made a VLM.**
- The two-step value is error-budget separation: reading = image-bound perception,
  correction = image-blind reasoning (`guide.md` §0.1; `CLAUDE.md` "image-blind").
- A VLM-correction would (i) double the VLM requirement and contradict the North
  Star (domestic VLM API → local open-source = *progressively lower* the model
  intelligence required), (ii) collapse the two independent training data streams
  (`(image,vectorJSON)` for reading VLM / `(vectorJSON,IntakeOutput)` for the
  correction text-LM) into one harder VLM problem, (iii) destroy
  perception-vs-reasoning attribution, (iv) let reading rot and starve the small-model
  supervision target, (v) re-introduce the very failure (a fresh image look would
  trust its own perception over the dimension channel — exactly the dim-tick-as-wall
  error). trust-the-dim works *because* correction cannot re-perceive.

**D2. Scaffolding IS the intelligence-lowering mechanism.** Every guardrail
(provenance, two-channel discipline, J0/J1 gates, re-read) is something a weaker
model no longer has to be smart enough to do unaided. This is why fixing reading by
*mechanism* (not by "use a stronger model") is the strategically central move:
near-top-tier (Sonnet-class) reading must be made high-quality by mechanism now, so
a distilled small VLM later has clean supervision.

**D3. Image-grounded arbitration lives in the JUDGE + re-read loop, not in
correction's generative work.** J0/J1 already see the original drawings; that is the
correct place for a second image-grounded look (a *gate/verifier*, removable in
prod, attribution-preserving), plus a targeted re-read on halt. Generation stays
image-blind.

**D4. Who fixes what (the image-blind boundary criterion).** Correction can only fix
an error when **independent redundant evidence survives in the reading JSON AND no
guessing is required**. Therefore:
- *Recoverable* → may pass through to correction: value/coordinate conflicts where a
  surviving independent channel (dimension chain / footprint closure / cross-floor
  twin / facade↔plan cross-ref) pins the truth and the defect is honestly flagged.
- *Unrecoverable* → must halt at reading (re-read): evidence-destroying errors
  (channel collapse: a dimension annotation traced as a wall; a missed real element),
  identity/category errors (door read as window), or anything requiring a guess
  (A1 "never guesses", A3 "never merge on doubt").
- "EP/safety-net passed" ≠ correct (founding §2.4 lesson 1: DeepSeek's 1.2 m ghost
  room passed EP cleanly). Do not rely on a downstream green as evidence of geometric
  correctness.

**D5. Revisit VLM-correction only if vector JSON proves a lossy bottleneck for
correctness** (the schema genuinely cannot represent the right answer). sm21 is not
that case — GPT-5.4 produced clean JSON, so the bottleneck is reading quality, not
schema expressiveness.

---

## 2. Root cause (code-grounded gap analysis)

The correction side of the founding framework is **fully landed**; the reading side
is **not**.

| Piece | State | Anchor |
|---|---|---|
| trust-the-dim arbitration (`stroke_vs_dimension` → trust the chain) | ✅ landed | `1_correction/A3_arbitration.md:28` |
| evidence model, ladders, conflict types, §6 upstream provenance input contract | ✅ landed (doc) | `1_correction/A0_contract.md` §1, §3, §6 |
| Stroke carries `provenance` / `confidence` | ❌ MISSING — only `id/pen/geometry/note` | `src/agent/reading/schema.py:35-43` |
| deterministic "low-confidence internal stroke↔dimension consistency" check | ❌ MISSING — docstring promises it; only `_chain_closure` exists | `src/validator/checks/reading.py:13`, `:377-413` |
| reading guide two-channel discipline + dim-tick-not-a-wall negative example | ❌ MISSING — only a one-line "confusable with" | `0_reading/reading_guide.md:143-152`; `guide.md` §5 |
| elevation door≠window explicit counter-example | ❌ MISSING — `door = not drawn (note only)` stated, no counter-example | `0_reading/pen_library.md:22`, `:82-91` |
| J0 recoverability routing axis | ❌ MISSING — `blocking = any(severe/fatal)`, severity-only | `src/agent/judge/verdict.py:55-59` |

Consequence: correction's arbitration machinery is **starved of the conflict
signal**. When Sonnet traces a dimension tick as a wall, the dimension channel is
*consumed into geometry* and there is nothing for `stroke_vs_dimension` to fire on;
with no provenance, correction cannot tell an estimated coordinate from a measured
one, so it faithfully transcribes the error. J0 then passes it (severity under-judged)
and J1 catches it only at correction — the exact failure in the diagnosis.

---

## 3. Design overview

Two **co-equal** fronts; correction (A1–A4 prompts + deterministic core) is
**untouched**.

- **Front 1 — make reading honest (D2/D4).** Land the two-channel + provenance/
  confidence discipline so an honest reading either (a) does not destroy the
  dimension channel, or (b) flags its uncertainty — moving recoverable errors into
  the class correction can actually fix, and making unrecoverable ones visible.
- **Front 2 — judge recoverability routing (D3/D4).** Give J0 a second axis
  (recoverability) so it halts the unrecoverable class for re-read and passes through
  only the provably-recoverable class; J1 is the confirm gate that re-judges
  correction's output against the reference and attributes failure back to reading or
  correction.

**Key property — no golden-baseline re-record.** All new schema fields are optional,
the new reading check is a non-blocking CROSS_CHECK flag, and the verdict change is
backward-compatible (missing recoverability ⇒ treated as unrecoverable ⇒ current
blocking behavior). Existing sm20/sm21 reading JSONs load as `provenance_mode=legacy`.

---

## 4. Front 1 — reading honest (file-by-file)

### 4.1 `src/agent/reading/schema.py` — `Stroke` gains provenance/confidence

Add three optional fields (legacy artifacts still load via `extra="allow"` +
defaults):

```python
class Stroke(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    pen: str
    geometry: dict = Field(default_factory=dict)
    provenance: Literal["seen", "dimension_derived", "estimated", "unknown"] | None = None
    confidence: Literal["high", "medium", "low"] | None = None
    dimension_refs: list[str] = Field(default_factory=list)
    note: str | None = None
```

Semantics (the reading-local signal; correction maps it to A0 §1.2 grades):
- `seen` — traced from an actual drawn wall/window line I can see (→ `estimated_stroke`; trustworthy for *existence*, coordinate may be offset).
- `dimension_derived` — coordinate computed from a dimension/chain, not from a drawn line here; `dimension_refs` lists the backing dimension ids (→ `transcribed_dimension`; trustworthy for *value*).
- `estimated` — best-guess placement, low evidence (→ `estimated_stroke`, low confidence).
- `unknown` / `None` — unstated; legacy.

This is the concrete landing of A0 §6 ("not emit estimated coordinates
indistinguishable from measured strokes; carry structured provenance + confidence;
link estimated geometry to the dimension ids that produced it").

### 4.2 `src/validator/checks/reading.py` — implement the promised consistency check

Implement `_stroke_dimension_consistency` as a **CROSS_CHECK (flag, non-blocking)**,
fulfilling the docstring at `:13`. Two non-blocking signals:

1. **Provenance coverage → `provenance_mode`** (A0 §6.1): tally how many
   structural strokes carry `provenance` → emit evidence `provenance_mode ∈
   {full, partial, legacy}`. Pure reporting; never fails.
2. **Stroke↔dim-tick coincidence flag**: for each plan `wall` stroke, if its axis
   coordinate coincides (within a small tolerance) with a dimension-chain cumulative
   position **and** the stroke is NOT tagged `dimension_derived` **and** a chain is
   present on that axis → flag: "wall coordinate coincides with a dimension tick;
   verify it is a real room-bounding wall, not a traced annotation." This is the
   sm21 signal (x=3.44/6.30 sit on the south dim chain). Flag only — it surfaces the
   suspicion for J0's recoverability test; it must NOT block (false positives on
   legitimately-dimensioned interior walls are expected and acceptable as flags).

Keep INVARIANT (blocking) layer unchanged.

### 4.3 Reading skill prose (perception discipline)

- `guide.md` §0.1 — refine the error-budget table with the D4 recoverability nuance:
  an offset-coordinate error with a surviving dimension channel + honest provenance is
  *recoverable* by correction (trust-the-dim); a missed stroke / wrong category is
  *unrecoverable*. State the **two-channel discipline**: emit walls and dimension
  chains as two INDEPENDENT channels; a dimension annotation must NEVER become a wall
  stroke.
- `guide.md` §2 (schema) — add `provenance`/`confidence`/`dimension_refs` to the
  stroke example + comments; instruct: tag `dimension_derived` + `dimension_refs`
  when a partition position comes from a chain rather than a seen line.
- `guide.md` §5 (counter-examples) — add: "❌ tracing a dimension-chain cumulative
  tick (drawn OUTSIDE the building outline) as an interior `wall` — dimension
  annotations are not walls; they go to `dimensions[]`."
- `guide.md` §6 (self-check) — add: "[ ] every wall/window stroke carries
  `provenance` + `confidence`; no dimension-chain position emitted as a wall stroke."
- `reading_guide.md` §D wall card "Confusable with" — strengthen with the positive
  test: an interior wall **bounds rooms and joins the perimeter/corridor walls**;
  cumulative dimension positions outside the outline do not.
- `pen_library.md` §4 — add: "❌ tracing an elevation floor-height door as a
  `window` because it breaks `wall_fill` — a door is recognized and logged, NEVER a
  `window` pen, even when it is a real opening (door = note only; §1)."

### 4.4 `0_reading/judge_rubric.md` (J0) — plan band/cell-count checklist

Under criterion 2 (clutter traced as structure) add a plan over-segmentation check:
when `testdata_prompt.json` carries per-floor `thermal_zones`, sanity-check plan
band/cell counts (e.g. sm21 F1 = 3N + corridor + 3S; F2 = 2N + corridor + 4S).
Sharpen criterion 3 to name "elevation door emitted as `window`" explicitly.
(The two-axis routing additions to this rubric are in §5.2.)

---

## 5. Front 2 — judge recoverability routing (file-by-file)

### 5.1 `src/agent/judge/verdict.py` — second axis + blocking semantics

```python
class Recoverability(str, Enum):
    CORRECTION_RECOVERABLE = "correction_recoverable"
    UNRECOVERABLE = "unrecoverable"
    UNKNOWN = "unknown"

class CriterionVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: str
    status: CriterionStatus
    recoverability: Recoverability | None = None   # NEW (optional)
    evidence: str = ""
```

`blocking` becomes severity × recoverability:

```python
@property
def blocking(self) -> bool:
    return any(
        c.status in (CriterionStatus.SEVERE, CriterionStatus.FATAL)
        and c.recoverability != Recoverability.CORRECTION_RECOVERABLE
        for c in self.criteria
    )
```

Backward compatible: a severe/fatal with `recoverability` unset (None) or `unknown`
still blocks (current behavior). Only an explicit `correction_recoverable` lets a
severe pass through. `routable()` unchanged.

### 5.2 `0_reading/judge_rubric.md` (J0) — the routing policy

Add the two-axis model + disposition table + the four-part recoverability test +
default-to-halt:

> **Disposition = severity × recoverability** (not severity alone):
> | | correction_recoverable | unrecoverable / unknown |
> |---|---|---|
> | severe/fatal | pass-through → correction (J1 confirms) | **halt → re-read** |
> | minor | flag + pass | flag + pass |
>
> A finding is `correction_recoverable` only when **all four** hold:
> 1. it is a value/coordinate error, not an existence/identity error;
> 2. an independent surviving channel pins the truth (a faithfully-emitted dimension
>    chain / footprint closure / cross-floor twin / facade↔plan cross-ref), itself trustworthy;
> 3. the conflict is in correction's deterministically-resolvable set (A3 §1:
>    `stroke_vs_dimension` / `cross_floor_axis_jitter` / dominant-channel `checksum_failure`);
> 4. the defect is honestly flagged (stroke `provenance`/`confidence` or the §4.2 check).
>
> Any condition fails → `unrecoverable`. **Default on uncertainty → unrecoverable
> (halt).** The asymmetry is deliberate: a false-green ship costs more than a wasted
> re-read; widen the pass-through set only as correction's capability is proven.

### 5.3 `1_correction/judge_rubric.md` (J1) — confirm gate + attribution

J1 already sees originals + reference and attributes root_stage. Make the
pass-through confirmation explicit: when a defect J0 passed through as recoverable is
not actually fixed in the corrected geometry, attribute —
- surviving channel was insufficient / the defect is a perception error visible in
  the originals → `root_stage=0_reading` → re-read (J0 mis-routed; J1 is the backstop);
- channels were sufficient but correction botched the arbitration →
  `root_stage=1_correction` → blind resample.

### 5.4 `src/agent/execution/step_orchestrator.py` — verify, likely no change

The pass-through path is realized entirely by `verdict.blocking` returning False for
a severe-but-recoverable J0 finding (the orchestrator then proceeds to correction as
today). Executor to confirm the orchestrator consumes `blocking`/`routable()` and
that no code path independently re-derives "severe ⇒ block".

---

## 6. Non-goals (explicitly NOT changing)

- `1_correction/A1–A4` prompts — trust-the-dim is already complete; do not touch.
- `src/agent/correction/deterministic.py` — operates on cells post-correction; out of scope.
- `IntakeOutput` contract (11 fields) — unchanged.
- golden baselines (sm20/sm21) — NOT re-recorded (see §3 property).
- `gt.json` / judge gt access rules — unchanged.

---

## 7. Test plan

- `schema.py`: Stroke loads with and without the new fields; a legacy artifact (no
  provenance) loads; `dimension_refs` defaults to `[]`.
- `checks/reading.py`: the coincidence flag fires on a synthetic sm21-like stroke
  (wall x on a dim-chain cumulative position, not `dimension_derived`); does not fire
  on a clean grid; `provenance_mode` reports full/partial/legacy correctly; the check
  never moves a previously-passing report to fail (CROSS_CHECK flag only).
- `verdict.py`: severe+`correction_recoverable` ⇒ not blocking; severe+unset ⇒
  blocking (backward compat); severe+`unknown` ⇒ blocking; minor ⇒ not blocking
  regardless.
- Full suite (currently 277/288 green per CLAUDE.md §2 — confirm exact count) stays
  green; no baseline byte-diffs.

---

## 8. Blast radius & risks

- **Schema additive** → low risk; the only consumers of `Stroke` are the reading
  linter and the correction LLM (prompt), both tolerant.
- **New reading check** is flag-only → cannot break gate① pass/fail of existing runs.
- **verdict.blocking** semantics change is the highest-attention item: confirm no
  other code treats "severe ⇒ block" outside this property. (Risk: an orchestrator
  path bypassing `blocking`.)
- **False positives** on the §4.2 coincidence flag for legitimately-dimensioned
  interior walls — acceptable because it is a non-blocking flag feeding J0 judgment,
  not a hard gate; tolerance must be tight enough to be useful but is advisory only.

---

## 9. Open questions for Codex

1. **Provenance enum**: is `{seen, dimension_derived, estimated, unknown}` the right
   reading-local vocabulary, or should reading emit A0 §1.2 grades directly
   (`direct_measurement/transcribed_dimension/estimated_stroke/...`)? Trade-off:
   reading-local is simpler for the perception model; A0-direct avoids a mapping layer.
2. **blocking overload**: is tweaking the `blocking` property sufficient, or is an
   explicit orchestrator-level disposition (`halt_reading|pass_through|pass_clean`)
   warranted for auditability? (I argue the property + recoverability field suffices;
   confirm against `step_orchestrator.py`.)
3. **J0→J1 obligation hand-off**: does J1 need an explicit `correction_obligations[]`
   carried from J0, or does independent re-judging against the reference answer
   suffice? (I argue independent re-judge suffices — J1 sees originals + gt; the
   obligation is implicit. Adding a hand-off field is a verdict-schema change I'd
   rather avoid.)
4. **§4.2 coincidence tolerance**: what tolerance scopes "coincides with a dim tick"
   without excessive false positives — `OUTPUT_PRECISION` (10 mm)? `SNAP_GRID`
   (50 mm)? something axis-relative?
5. **Component 2 scope**: include "persist the manual 0_reading prompt/model into run
   artifacts" (diagnosis §D #4) in this PR, or defer? It is orthogonal and small but
   widens the PR.
6. Anything in §1 (ratified) that the implementation in §4–§5 fails to faithfully
   serve.

---

## 10. Addendum — accepted review changes (BINDING; supersedes §4–§5 where in conflict)

Codex review (`AI_agent/logs/review/review/2026-06-21_reading_honest_and_judge_routing_review.md`):
verdict **APPROVE-WITH-CHANGES**. Claude adjudication: **all 5 findings accepted**,
independently verified (record_baseline.py:94-95 and step_orchestrator.py:328/331
confirmed by reading; grep confirms record_baseline._verdict_blocking is the ONLY
re-derivation of verdict.blocking that bypasses the property). Binding deltas:

- **Δ1 (was Finding 1, major) — recoverability pass-through is J0-ONLY.** `blocking`
  blocks on any severe/fatal **unless** `rubric_id == "J0"` AND
  `recoverability == CORRECTION_RECOVERABLE`. A J1 severe/fatal **always** blocks
  regardless of recoverability (J1 is the confirm gate; there is no further
  correction stage to recover at J1). Tests: J0 severe+recoverable → non-blocking;
  J1 severe+recoverable → blocking; severe + missing recoverability → blocking
  (backward compat).
- **Δ2 (Finding 2, major) — fix `record_baseline.py:94` `_verdict_blocking`.** It must
  become recoverability-aware (parse via `StageVerdict.model_validate(...)` and use
  `.blocking`, or share one helper) so a J0 severe-recoverable pass-through is NOT
  mislabeled blocking in `baseline.json` / `RUN_REPORT.md`. Regression test. This is
  the lynchpin of the "no golden re-record" claim.
- **Δ3 (Finding 3, minor) — orchestrator audit message.** `step_orchestrator._verdict_outcome`
  (`:328-331`) must distinguish "pass-through (severe recoverable)" from clean/minor
  pass, and surface the recoverable-criteria count in the log/baseline, so reading
  debt is not reported as a clean pass. No new routing STATE — control flow unchanged.
- **Δ4 (Finding 4, minor) — coincidence flag discipline.** §4.2 flag stays CROSS_CHECK
  (non-blocking), tolerance = `OUTPUT_PRECISION` (10 mm) NOT `SNAP_GRID` (50 mm).
  Evidence carries stroke id + axis coordinate + matching dimension ids + (when
  inferable) whether the line bounds rooms / joins walls. Flag text asks J0 to
  **verify**; it must NOT presume "annotation traced as structure" (true partitions
  often sit exactly on dimension-chain endpoints).
- **Δ5 (Finding 5, minor) — document the provenance→A0 mapping per claim type.** In
  `guide.md` (and a one-liner in the correction docs / A0 input-contract section):
  `seen` = visual EXISTENCE evidence → numeric `estimated_stroke` (NOT
  `direct_measurement`); `dimension_derived` → numeric `transcribed_dimension` and
  **requires non-empty `dimension_refs`**; `estimated` → low-confidence
  `estimated_stroke`; `unknown`/missing → legacy/unknown. Prevents `seen` from being
  over-trusted as a measured coordinate (the runtime passes raw reading JSON + A0/A3
  prose to the correction model — `src/agent/pipeline.py:289`,`:340` — with no typed
  conversion, so the mapping must live in prose).

Open-question resolutions (Codex, accepted): Q1 reading-local enum (not A0 grades);
Q2 property-only, J0-scoped, + audit label (no new orchestrator route); Q3 NO
`correction_obligations[]` — independent J1 re-judge against the reference suffices;
Q4 10 mm coincidence tolerance; **Q5 defer Component 2 (persist prompt/model) to a
follow-up PR** — out of scope for this one.
