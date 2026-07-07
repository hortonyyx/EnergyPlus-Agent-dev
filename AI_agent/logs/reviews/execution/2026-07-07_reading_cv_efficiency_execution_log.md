# Reading CV Efficiency E Batch Execution Log

## Built

- Backed up touched skill files to `backup/Skill_history/2026-07-07_cv_discipline_hardening/`:
  - `cv_toolbox.md`
  - `session_kickoff.md`
- Updated `skills/intake_pipeline/0_reading/cv_toolbox.md` with current-version CV disciplines:
  - clean vector CAD PNGs require the toolbox; noisy and hand-drawn inputs are deferred until a robustness profile exists
  - calibrate first with dimension-chain tick or extension-line anchors and <=1 px residual iteration
  - measure before drawing
  - single px-to-m formula provenance
  - crop-verified candidate accept/reject logging
  - pixel-measured provenance for un-dimensioned elements with empty `dimension_refs`
  - flat `dimensions[].anchor` bbox shape
  - pointers to `guide.md` and `pen_library.md` instead of duplicated reading rules
- Updated `skills/intake_pipeline/0_reading/session_kickoff.md` so required/optional CV judgment points to `cv_toolbox.md`.
- Added `prescan-plan` and `prescan-elevation` CLI verbs in `scripts/tool_scripts/cv_probe.py`.
- Implemented prescan macros in `src/agent/reading/cv_toolbox/recipes.py`:
  - clean-vector gray mask
  - row and column projection candidates
  - bounded real mask-run segments for each peak line
  - neutral `line_band_candidate`, `cc_box_candidate`, and `tick_candidate` names
  - fixed `cv_evidence/<stem>/prescan/candidates.json`
  - numbered `combined_overlay.png`
  - `capability_profile` support for `rectangular` and `orthogonal_polygon`
  - explicit `NotImplementedError` for unsupported profiles
  - advisory-only params and no validator/correction/judge consumption
- Exported prescan functions from `src/agent/reading/cv_toolbox/__init__.py`.
- Updated `AI_agent/guides/new_case_guide.md` §2.1 and Appendix A so the orchestrator runs deterministic prescan before cold-start reading sub-agent spawn and passes candidates plus overlay as advisory inputs.
- Extended `tests/test_cv_toolbox.py` for prescan schema, bounded L-mask segments, idempotence, unsupported profiles, tick detection, and CLI overlay output.
- Extended `tests/test_gt_discipline.py` with an explicit GT-blind scan for prescan entry points.

## Test Counts

- New tests added: 7 total.
  - `tests/test_cv_toolbox.py`: +6
  - `tests/test_gt_discipline.py`: +1
- Before this batch, inferred full-suite count was 510 pass-capable tests plus 9 xfailed.
- After this batch: 517 passed, 9 xfailed.

## Test Results

Focused command:

```bash
python -m pytest tests/test_cv_toolbox.py tests/test_gt_discipline.py -q
```

Result:

```text
23 passed in 9.15s
```

Full command:

```bash
python -m pytest tests/ -q
```

Result:

```text
517 passed, 9 xfailed, 115 warnings in 150.14s (0:02:30)
```

## Deviations

- None from the adopted brief. Existing numbered sidecar tools remain append-only and behavior-compatible. Prescan uses the brief's fixed `prescan/candidates.json` path; repeat writes are idempotent when content is identical and fail if different content would replace existing evidence.
