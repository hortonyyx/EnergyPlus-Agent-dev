# Review Request — Phase 1 skill restructure (three-way split + subfolders)

Date: 2026-05-26
Requested by: Claude (main dev agent)
Suggested reviewer: Codex / Gemini (fresh model, cross-check)

## Background

The two-step intake phase-1 spec used to be **one bundled file** `phase1_vector_schema.md` (the
version Codex reviewed and we fixed on 2026-05-25). This session it was restructured, in two moves,
into a **three-way knowledge split** plus a subfolder layout, to prepare for the异图 POC v2 (broad
drawing-style generalization) and a future RAG-able recognition library.

The conceptual decomposition (user-driven):
- **总指导 / guide** — flow, error budget, global constraints, the JSON output container, processing
  discipline (door-healing rule + guardrails, self-check, downstream contract). *Rules + container.*
- **识图指南 / reading_guide** — *how to recognize what an element is* across drawing styles
  (convention "cards" + a semantic-category vocabulary). Pure perception; outputs a **category
  label**; decides no action. NEW content.
- **画图指南 / pen_library** — *what to do* with a recognized category (which pen / keep-or-ignore /
  heal). Currently a **deliberately simple version** (pending a separate user discussion).

The three are wired by a shared **semantic-category enum** (reading_guide §0.3 ↔ pen_library §1 map).

## Scope to review

1. **No capability regression** vs the pre-split bundled spec. The single most important check:
   every hard constraint that existed in the 2026-05-25 `phase1_vector_schema.md` must still be
   present in **exactly one** of the three new docs — not dropped, not weakened, not silently
   duplicated/contradicted.
2. **Clean separation of concerns** — does each doc stay in its lane?
   - reading_guide = identity only (no pen/keep/ignore/heal actions, no topology like inside/outside,
     parent-child, room grouping)
   - pen_library = action only (no "what it looks like" visual descriptions)
   - guide = flow/container/discipline
   Flag any leakage in either direction.
3. **Semantic-category enum parity** — is the category set in `reading_guide §0.3` identical to the
   left column of the `pen_library §1` map? Is **every** category routed to an action? Any orphan
   (in one doc, missing in the other)?
4. **reading_guide quality** — the user's explicit constraint was "宁泛勿死" (cover broadly, do not
   hard-code one drawing style). Check:
   - factual correctness of the architectural-drawing conventions (walls / doors / windows / stairs /
     dimensions / grids / hatches / clutter, GB vs US vs ISO notes)
   - whether the "invariant cue first, variants non-exhaustive" framing is applied consistently
   - whether any card went too vague to be actionable, OR too rigid (pins a single style)
   - that the high-confusion pairs (door vs window vs plain-opening; wall vs grid-axis vs
     dimension-extension; stair vs paving; wall_fill vs shadow; wall-material vs floor-paving) are
     correct and useful
5. **Door handling coherence across the three docs** — recognition (reading_guide `door` card) →
   action = "not drawn, trigger healing" (pen_library) → rule + 4 guardrails + trace (guide §2.1).
   Verify these three references are mutually consistent and the guardrails survived intact.
6. **clean-spec compliance** (per project policy): skill files must carry **no** version numbers /
   timestamps / changelogs / decision-history / cross-references to `AI_agent/` decision docs;
   **English-only** except deliberately-retained drawing/OCR labels (e.g. `上`/`下`/`北`/`办公室`).
7. **Link integrity** — all intra-lib and external (`AI_agent/`) markdown links resolve after the
   rename + subfolder move. (I verified with a script; please spot-check.)
8. **The two pre-run script fixes** (smaller, separate concern):
   - `scripts/run_full_pipeline.py`: new `--base-dir` (default `test_data/SmallOffice`) so two-step
     cases under `SmallOffice_TwoStep/` run without copying files. Check it didn't break the
     single-step default path.
   - `Tool_scripts/run_phase2_deepseek.py`: `PHASE1_FILES` hardcoded list → `_discover_phase1_files()`
     scanning `phase1_vector/*_view.json` (plans `<N>f_view` before elevations). Check ordering and
     the empty/missing-dir error path.

## Files to review

New / restructured skill lib (`skills/energyplus_mcp_twostep/`):
- `phase1/guide.md` (总指导; renamed from the bundled spec, content trimmed)
- `phase1/reading_guide.md` (识图指南; NEW)
- `phase1/pen_library.md` (笔库; simplified to a category→action map)
- `phase1/prompt_template.md` (operational launcher; now reads all three)
- `phase2/rules.md`, `phase2/prompt_template.md` (only moved + relink; content unchanged)
- `README.md` (file table + flow updated)

Scripts:
- `scripts/run_full_pipeline.py`
- `Tool_scripts/run_phase2_deepseek.py`

External docs touched (links repointed; review only for correctness of the pointers):
- `AI_agent/CLAUDE.md` §7 index, `AI_agent/plan.md` B1.5.c, `AI_agent/new_case_guide_twostep.md`
  (also de-staled the two now-fixed pitfalls in §二B/§三), `AI_agent/twostep_architecture_diagram.md`

## Diff anchors (compare "before" vs "after")

- **Authoritative "before" (the 2026-05-25 Codex-fixed bundled spec)**:
  `Skill_history/2026-05-26_twostep_phase1_split_recognition_penlib/phase1_vector_schema.md`
  — diff this against the union of the three new `phase1/` docs for the regression check (item 1).
- Intermediate two-way state: `Skill_history/2026-05-26_twostep_phase1_threeway_split_v2/`
- Pre-subfolder state: `Skill_history/2026-05-26_twostep_phase1_subfolder_reorg/`

## Explicitly out of scope / known-pending (do not flag)

- `pen_library` being "thin" — it is intentionally a simple version pending a separate user
  discussion about the pen vocabulary.
- Empty `示例图 / example image` fields in reading_guide cards — pending the v2 image corpus.
- The case-level runtime copy convention: `run_phase2_deepseek.py:91` still reads a single
  `vector_schema_v1.md` per case; updating that to copy the three `phase1/` docs is deferred to
  B1.5.c (no new case is built yet).
- The 5-25 review doc keeping the old flat path — it is a frozen audit artifact.

## Acceptance criteria

- [ ] Zero capability regression: every pre-split hard constraint maps to exactly one new doc
- [ ] No concern leakage between guide / reading_guide / pen_library
- [ ] Category enum parity; every category has an action; no orphans
- [ ] reading_guide is broad + style-robust without being unusably vague; conventions are correct
- [ ] door handling consistent across the three docs; healing guardrails intact
- [ ] clean-spec compliant (no version/date/decision; English-only except drawing labels)
- [ ] all links resolve
- [ ] the two script fixes are correct and the single-step path is unaffected

Please write the review to `AI_agent/review/review/2026-05-26_phase1_skill_restructure_review.md`
with a verdict + graded findings (High/Medium/Low, with evidence + recommended fix), matching the
2026-05-25 review's format.
