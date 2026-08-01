# 2026-08-01 reading unsupervised enablement — terra execution log

## W1 — standing calibration/measurement requirement

### Changed and why

- Updated only `skills/intake_pipeline/0_reading/session_kickoff.md`.
- The CV-tool bullet now states directly that clean vector CAD PNGs require deterministic probes before drawing.
- Added the first Non-negotiable: calibrate and measure before writing metre coordinates, with a pointer to `cv_toolbox.md` rather than copying its durable rules.
- The degraded-input exception remains a pointer to the toolbox robustness-profile exception.
- Before editing, backed up the touched skill file to
  `backup/Skill_history/2026-08-01_w1_calibrate_kickoff/session_kickoff.md`.

### Source traceability

- `cv_toolbox.md:3`: toolbox is used before semantic reading JSON on clean vector CAD PNGs and documents the degraded-input exception.
- `cv_toolbox.md:50`: calibrate before metre coordinates and use dimension-chain extension-line intersections or ticks.
- `cv_toolbox.md:54`: measure before drawing.

### Evidence commands and outputs

```text
$ python scripts/tool_scripts/affected_tests.py --changed skills/intake_pipeline/0_reading/session_kickoff.md
SCOPE: FULL
python -m pytest -p no:cacheprovider -q
跑测声明：受影响子集 = 全仓（依据 affected_tests.py --changed skills/intake_pipeline/0_reading/session_kickoff.md；原因：path is not a first-class Python file: skills/intake_pipeline/0_reading/session_kickoff.md）

$ git diff --check
(no output; clean)
```

The selected scope is full because a Markdown skill file is fail-closed; the one required full-suite run will be recorded at batch completion.

### Under-specified boundaries

None. Existing unrelated unstaged edits already touched this skill file's Workflow section; they were preserved and excluded from this slice's staged diff and commit.
