Read skills/intake_pipeline/0_reading/session_kickoff.md and follow it for case sm21_anchor.

The drawings are at case_tests/e2e_tests/sm21_anchor/case_data/. Write reading outputs under
case_tests/e2e_tests/sm21_anchor/0_reading/ — one JSON per source drawing, named
<name>_view.json — plus reading_summary.md.

You are isolated for this run: work ONLY from the drawings in case_data/, testdata_prompt.json,
and the 0_reading skill docs. Do NOT read ground truth, judge notes, or any other run's reading
of this case.

## Per-run directive (binding for this run)

cv_toolbox.md is REQUIRED reading for this run, and wall-line / window-box / storey-line
positions must be measured with `python scripts/tool_scripts/cv_probe.py` before drawing
(measure-before-draw).
