# Reading CV efficiency batch review

Verdict: **APPROVE-WITH-CHANGES**.

The E batch is directionally sound: the 2026-07-07 Haiku retest shows the CV toolbox fixes the weak-VLM failure mode when the model is forced to measure instead of eyeballing. E1-E3 are the right next efficiency moves. The required changes are contract hardening before implementation, especially around non-rectangular extensibility and the semantic boundary between deterministic prescan and the VLM.

## Findings

1. **MAJOR - E2 / invariant #6 - Segment-form output is necessary but not sufficient.**

   The brief says `p1_px`/`p2_px` candidate rows avoid baking in an axis+constant table shape. That is true at the JSON surface, but the current C0/C1 tools still expose row/column peaks as axis lines (`geometry: {kind:"line", axis:"row|col", x_px|y_px}`) and `overlay_logger` draws those across the full image. If `prescan-plan` only wraps those peaks into full-width/full-height segments, an L-shaped or partial-wall orthogonal polygon is already misrepresented as rectangular spans, even before sloped walls.

   Concrete fix: make prescan candidates real bounded segments, not whole-image axis lines. For orthogonal detectors, derive `p1_px`/`p2_px` from support runs/CC intersections within the FWHM band, and add a synthetic L-shaped orthogonal fixture proving partial segment endpoints survive. The schema test must reject axis-only candidates and reject full-image spans when the support is partial. Keep sloped-wall profiles `NOT_IMPLEMENTED`, but reserve the same segment rows for future Hough/LSD output.

2. **MAJOR - E3 / division of labor - Candidate names must not become semantic truth.**

   The brief says prescan has no semantic assertions, but the proposed rows include names such as `wall_line_candidate`, `facade region CC`, and window candidates. Existing C0/C1 names (`wall_line_profiler`, `window_cc_detector`, `candidate_kind="window_rect"`) are acceptable as tool names only because the skill explicitly says the VLM still classifies them. E3 raises the risk because candidates are preloaded before the cold-start reader and can silently frame the answer.

   Concrete fix: the prescan table should use mechanically neutral kinds such as `line_segment_candidate`, `storey_axis_candidate`, `cc_bbox_candidate`, `tick_candidate`, with `detector` / `recipe_id` / `capability_profile` fields carrying provenance. Do not emit `wall`, `window`, `facade`, `room`, `storey wall`, or similar semantic labels as candidate truth. The sub-agent prompt must explicitly say candidates are mechanical attention aids and may be rejected. Add a test or fixture asserting no prescan JSON key/value in the execution output uses semantic keep-pen labels except in user/VLM-authored accept/reject decisions.

3. **MAJOR - E1 / skills no-duplication - Move generic reading rules back to their owners.**

   Several proposed cv_toolbox disciplines restate or partially override existing rules in `guide.md` §0.1 and `pen_library.md`: completeness, no guessing, dimension ticks not becoming walls, verbatim text, provenance honesty, and null/unknown behavior. The kickoff already states durable rules must not be duplicated, and `session_kickoff.md` is only a pointer.

   Concrete fix: let `cv_toolbox.md` own only CV-specific operating rules: when clean-vector CV tools are required, how to choose tick/extension-line calibration anchors, residual thresholds, the pixel-to-meter formula, sidecar citation requirements, pixel-measured provenance wording, and the flat pixel bbox shape for `dimensions[].anchor` if that field remains a CV sidecar convention. For generic recognition/action rules, link to `guide.md` §0.1 and `pen_library.md` rather than restating them. If `dimensions[].anchor` shape is canonical schema, put it in `guide.md` and have cv_toolbox reference it.

4. **MINOR - E2/E3 / gt isolation - Extend the mechanical scan to the actual prescan entry point.**

   Existing `tests/test_gt_discipline.py` already scans `src/agent/reading/**` and `scripts/tool_scripts/cv_probe.py`, so C0/C1 are covered. E3 may add prescan orchestration in `scripts/tool_scripts/run_stage.py`, `src/agent/execution/**`, or a new helper script.

   Concrete fix: wherever `prescan-plan` / `prescan-elevation` and the pre-spawn handoff are implemented, include those files in `test_gt_discipline.py` or place them under already-scanned execution paths. Add one smoke test that runs prescan against a temp image/out-dir without any `case_tests/test_baseline/gt` path argument or import.

5. **MINOR - E2 / tests - Add behavior tests, not just schema tests.**

   The proposed tests cover schema, idempotence, and superset against the single profiler. They do not yet prove the macro reduces the failure mode seen in the experiment.

   Concrete fix: add tests for: one combined overlay exists and draws bounded segment candidates; repeated prescan writes deterministic JSON when directed to a fresh output path; rejected unsupported capability profiles fail loudly; tick candidates are present separately from wall/line candidates; and a synthetic furniture/dimension-line clutter case remains undecided rather than auto-accepted.

6. **MINOR - E3 / audit surface - Keep prescan sidecars advisory and append-only.**

   E3 should not create a second truth source that later gates or correction code consumes as accepted geometry.

   Concrete fix: store prescan under `0_reading/cv_evidence/<stem>/prescan/` as audit evidence, and require the final `*_view.json` to cite sidecar candidate IDs only through VLM-authored provenance/notes. Gate①, correction, judge packets, and score rendering must not consume prescan candidates as geometry in this batch.

## Codex review points

1. **E2 candidate table / #6:** acceptable only after bounded-segment enforcement and L-shaped partial-span tests. A segment schema is the right future-proof surface, but current row/column profiler geometry cannot be lifted unchanged.
2. **E3 pollution surface:** no gt issue if prescan stays in scanned execution code and receives only source images/out-dir/recipe args. The bigger risk is semantic pollution from candidate labels and any later consumer treating candidates as accepted geometry.
3. **E1 skill prose:** tighten to CV-specific disciplines and pointers. Do not let kickoff duplicate cv_toolbox, and do not let cv_toolbox duplicate guide/pen rules.
4. **E4 OCR recommendation:** proceed with option **(a)** for this batch: VLM selects calibration anchors and reads dimension text; deterministic code measures pixels and checks residuals/closure. This preserves the Phase C OCR decision and keeps E1-E3 small enough to validate. For the upcoming gpt-5.4-mini cross-test, (a) is a useful stress test of model portability; if it fails specifically on digit transcription or anchor selection while residual/closure gates catch it, promote OCR to a Phase C experiment. Lightweight digit OCR may become more model-stable than (a), but it should first run as an advisory sidecar against the same harness rather than becoming an unreviewed calibration truth source.
5. **Missing tests:** add the tests listed in findings 4-5, plus a prompt/SOP test or snapshot ensuring the sub-agent handoff includes prescan artifacts as candidate evidence and still requires VLM semantic acceptance/rejection.

## Approval conditions

- Prescan JSON is segment-native, mechanically named, deterministic, and capability-profiled.
- Orthogonal polygon support is tested with partial spans; sloped-wall support explicitly fails closed.
- No prescan/toolbox/orchestrator path reads or imports gt.
- Skill edits preserve English current-version spec and no-duplication boundaries.
- Semantic classification remains VLM-authored; prescan never silently accepts wall/window/facade truth.

APPROVE-WITH-CHANGES
