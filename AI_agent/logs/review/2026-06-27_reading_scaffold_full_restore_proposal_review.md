# Review - Reading Scaffold Full Restore Proposal

Reviewed proposal: `AI_agent/logs/review/2026-06-27_reading_scaffold_full_restore_proposal.md`

Sources consulted:
- Old scaffold at `127ba06`: `skills/energyplus_mcp_twostep/phase1/guide.md`, `reading_guide.md`, `pen_library.md`, `prompt_template.md`
- Current reading docs: `skills/intake_pipeline/0_reading/guide.md`, `reading_guide.md`, `pen_library.md`, `session_kickoff.md`
- Current code: `src/agent/reading/schema.py`, `src/validator/checks/reading.py`
- Prior audits: `AI_agent/logs/review/2026-06-25_scaffold_degradation_audit/RECONCILED_candidates.md`, `AI_agent/logs/review/2026-06-25_reading_migration_completeness_audit/RECONCILED.md`

## Verdict

APPROVE-WITH-CHANGES.

The proposal is directionally correct: it follows the ratified rule to restore every old-scaffold constraint that is both valid and compatible, and it correctly refuses to reintroduce world-axis reading, old two-stroke door handling, expanded pens, or prompt-strength tuning. It should not be approved as-is because a few concrete code/prose carriers need correction:

1. Candidate 20 is already partly enforced by `_pen_kind`; the remaining gap is that `geometry.kind=None` still passes, and `polyline` is not well-formed-checked.
2. The forbidden-field code gate should include the old prompt's concrete `parent_wall_id` field, not only `is_exterior`, `parent_window_ids`, and `rooms`.
3. Candidate 10 is functionally covered except that `beam` is not explicitly named in current `pen_library.md`; for "no gaps" restoration, add it to the non-traced examples or add a `beam/overhead` row/action.
4. Candidate 7 should be prose now only because the current validator has no expected-image manifest; if that manifest exists at orchestration time, a reading-stage completeness gate is warranted.

## Candidate 9 - Door-Healing Guardrails

Old source: `127ba06:skills/energyplus_mcp_twostep/phase1/guide.md` lines 203-225.
Current source: `skills/intake_pipeline/0_reading/guide.md` lines 269-292.

Line diff:

```diff
--- old-guide-2.1
+++ current-guide-2.1
@@
-continuous wall**. Phase 1 can see the door arc / leaf at a glance; phase 2 only has coordinates and
+continuous wall**. The reading stage can see the door arc / leaf at a glance; the correction stage only has coordinates and
@@
-principle, healing the door belongs to phase 1. Effect: phase 2 always receives a clean, closed wall
+principle, healing the door belongs to the reading stage. Effect: the correction stage always receives a clean, closed wall
@@
-**Healing != assigning rooms**: phase 1 only guarantees the wall network is geometrically continuous
-and closed; which walls enclose which room / inside vs outside / naming is still phase 2's job
+**Healing != assigning rooms**: the reading stage only guarantees the wall network is geometrically continuous
+and closed; which walls enclose which room / inside vs outside / naming is still the correction stage's job
@@
 1. **Only heal openings carrying a door symbol (door leaf / swing arc)** -- the door symbol is the trigger
 2. **Do not heal a doorless large opening / open span** -- that is a real topology signal
@@
 3. **Do not heal windows** -- keep them as a window pen (a window is a sub-face, not a boundary break)
 4. **Always leave a trace when healing**: write `healed door opening at <position>` in that wall
-   stroke's note, and record it in `self_check.uncaptured_visual_elements`, so SVG review can verify
-   "the heal is correct, no real opening was covered up"
+   stroke's note, and record it in the top-level `uncaptured` list, so SVG review can verify
+   "the heal is correct, no real opening was covered up" (the linter flags a healed-door note with
+   no matching `uncaptured` entry)
```

Coverage ruling: full coverage. The old scaffold had these four substantive guardrails:

- only heal openings with a door symbol;
- do not heal doorless large openings/open spans;
- do not heal windows;
- leave a trace on the wall stroke and in the skip/uncaptured carrier.

Current `guide.md` contains all four. The only intentional carrier change is from old nested `self_check.uncaptured_visual_elements` to top-level `uncaptured`, and current `_door_heal_traced` flags a healed-door note with no heal trace in pooled uncaptured carriers (`src/validator/checks/reading.py` lines 382-418). Candidate 9 should be marked already covered, not restored again.

## Candidate 10 - Non-Keep Clutter List

Old concrete list source: `127ba06:skills/energyplus_mcp_twostep/phase1/prompt_template.md` lines 81-84:

```text
Columns / beams / decorative lines / index arrows / grid lines / stair treads
```

Current action map source: `skills/intake_pipeline/0_reading/pen_library.md` lines 15-63.

Line diff against current `pen_library.md`:

```diff
--- old-nonkeep-list
+++ current-pen-library
@@
-4. **Do not expand the pen set, and do not trace non-keep marks.** Columns / beams / decorative lines /
-   index arrows / grid lines / stair treads are **recognized then logged in `uncaptured_visual_elements`**,
-   not traced as strokes; do not invent enum values like `cornice` / `column` / `level_line` and do
-   not fall back to an `other` pen (there is none)
+| `column` | recognize -> log (not a zone boundary; not traced) | same; if embedded in a wall it is part of that `wall_fill` |
+| `stair` | recognize -> **do not trace treads**; log treads in `uncaptured`; the stairwell is defined by its bounding `wall`s; any `...`/stair label -> `ocr_texts[]` | same |
+| `grid-axis` | not geometry; ignore -> log | same |
+| `view-marker` | not geometry (it points at another drawing); ignore -> log | ignore -> log |
+| `decoration` | **ignore -> log** | same |
+...
+Anything that is not one of these (column, stair, grid line, north arrow, decoration, furniture, ...)
+is **not traced as a stroke** ... There is no `other` pen and no `door` pen.
```

Specific old items:

| Old item | Current coverage | Ruling |
|---|---|---|
| columns | `column` row: recognize -> log, not traced | Covered |
| beams | `reading_guide.md` line 114 names dashed hidden/above-cut line as "e.g. an overhead beam"; `pen_library.md` does not name a beam action | Functionally recoverable via unknown/log, but exact old constraint is not explicit in `pen_library.md`; add "beam/overhead hidden lines" to non-traced examples for no-gap restoration |
| decorative lines | `decoration` row: ignore -> log | Covered |
| index arrows | `view-marker` row covers elevation/detail/section index markers; `north-arrow` also ignored/logged | Covered conceptually; exact phrase absent but not a functional gap |
| grid lines | `grid-axis` row: ignore -> log | Covered |
| stair treads | `stair` row and counterexample: do not trace treads | Covered |
| no invented enum / no `other` pen | legal pen section and `_pen_kind` gate | Covered for plan/elevation |

Candidate 10 should be "covered except explicit beam wording." If the implementation goal is literal old-scaffold completeness for weak VLMs, add `beam` to the current pen-library examples rather than relying on the recognition guide plus unknown/log fallback.

## Exclusions Check

All proposed exclusions are basically correct.

- Candidate 3, facade world-axis table: correctly excluded. Current reading is image-local by design (`guide.md` lines 310-326; `schema.py` lines 83-94), and the old table would reintroduce world placement into stage 0.
- Candidate 22, restoring `other`/`stair` pens: correctly excluded. `127ba06` already used the minimal pen set, and current `_pen_kind`/pen docs intentionally keep plan=`wall/window`, elevation=`wall_fill/window/outline`.
- Candidate 23, old two-stroke door handling: correctly excluded. `127ba06` already had door healing; reverting to two strokes would conflict with the current and old sm21_pre door-healing discipline.
- Candidate 25, `room_labels`: correctly excluded from "remove/revert." It is not an old missing constraint; it is a current topology-light visible-observation channel. Keep it, with existing validation of role vocabulary/basis/anchor.
- Prompt strength: correctly excluded. It is not a proven old scaffold constraint and should not be restored as a magic lever.

No exclusion is wrongly cutting a valid and compatible old-scaffold constraint.

## Candidate 24 - Wall Cue Ruling

Current wall cue: `reading_guide.md` lines 143-154 says a wall is a long boundary line that, with others, encloses rooms and meets at corners to close a region; the positive test says an interior wall bounds rooms and joins the perimeter/corridor network.

Ruling: legitimate recognition cue, not a red-line violation in its current form.

Reason: the text is used to distinguish wall marks from dimension ticks, grid axes, and furniture outlines. It does not ask reading to emit room polygons, assign rooms, or decide which walls enclose which specific room. The red-line section still explicitly assigns "which walls enclose which room" and parent/inside-outside decisions to correction (`guide.md` lines 296-306). Keep the cue. If edited, phrase it as "visual recognition cue only; do not output closure/room topology."

## Candidate 20 - Current Enforcement and Warranted Gate

Schema state:

- `Stroke.pen` is plain `str`; `Stroke.geometry` is plain `dict` (`schema.py` lines 35-42).
- `ReadingView.image_kind` permits `plan`, `elevation`, `section`, `supplementary`, and `other` (`schema.py` lines 31-32, 113-115).
- This permissiveness is intentional for legacy loading; the validator owns the invariant checks.

Validator state:

- `_legal_pens` enforces legal pens only for `plan` and `elevation`; `section/supplementary/other` return `None` and skip pen-set enforcement (`reading.py` lines 42-48).
- `_pen_kind` blocks illegal plan/elevation pens and blocks unknown `geometry.kind` values (`reading.py` lines 282-300).
- However, `_pen_kind` allows `geometry.kind is None` (`kind not in (None, "line", "rect", "polyline")`), so a stroke with missing `geometry.kind` passes the legal-kind gate.
- `_geometry_wellformed` validates line endpoints and rect ranges, but does not validate `polyline` point lists (`reading.py` lines 321-346).

Ruling: a geometry-kind code gate is warranted, but the proposal should state it as tightening an existing partial gate, not adding a wholly missing one. Recommended scope:

- require `geometry.kind in {"line", "rect", "polyline"}` for canonical/current outputs, while preserving legacy migration if needed before validation;
- add a regression test for missing `geometry.kind`;
- consider validating polyline `points` as a non-empty finite list with nonzero path length.

## Missed-Constraint Self-Scan

I did not find a new category-level old scaffold constraint, valid and compatible, that both prior audits completely missed.

Two concrete coverage nits did surface:

1. The old startup prompt names `parent_wall_id` as a forbidden topology field (`prompt_template.md` line 79). The migration forbidden-field backlog names `is_exterior`, `parent_window_ids`, and `rooms`, but not `parent_wall_id`. This is covered conceptually by candidate 26/parent-relation discipline, but the proposed code gate should include the concrete old field name too. Recommended forbidden set addition: `is_exterior`, `parent_window_ids`, `parent_wall_id`, `parent_wall_ids`, `rooms`.
2. The old non-keep list explicitly names `beams`; current `pen_library.md` does not. This belongs under candidate 10 rather than a new candidate.

## Carrier Check for Proposal's Prose Items

- 5 doc roles: prose is correct; current guide/kickoff already largely cover it.
- 6 re-trace coordinate examples: prose is correct.
- 7 image/output checklist: prose is acceptable today, but if a source-image manifest exists, add an orchestration/reading completeness gate. Current validation only checks that some `0_reading/*_view.json` exists and then globs existing files (`validation_run.py` lines 96-119), so it cannot detect missing expected images.
- 8 worked-example anchor: prose is correct.
- 9 door-healing guardrails: already covered by prose plus `_door_heal_traced` cross-check. No image-free code can verify the door-symbol/doorless-span/window distinction; that remains J0/image review.
- 10 clutter list: prose is mostly correct; illegal pen values are already code-gated for plan/elevation. Add explicit `beam` wording.
- 11 workflow wording: prose is correct, and current workflow is already unambiguous.
- 15 self-check provenance/tick items: prose is acceptable; current validator reports provenance coverage and has an advisory dimension/stroke consistency check. Making provenance/confidence blocking is possible, but would be a reading-honest policy change rather than direct old-scaffold restoration.
- 19 schema examples: prose/doc fix is correct, but if the project wants canonical non-legacy readings to require `provenance`/`confidence`, that should become a validator invariant with a legacy escape.
- 21 section/supplementary/other: prose is correct. The validator intentionally does not constrain pens for these kinds yet.
- 26 window "which wall" wording: prose fix is required; also add parent-relation field names to `_FORBIDDEN_STROKE_KEYS` as above.
- #50 per-facade/floor window chain: reading-side prose is correct. The deterministic count/blank gate belongs in the correction/cross-image companion as the proposal says; reading alone lacks the cross-facade/floor reconciliation context.

