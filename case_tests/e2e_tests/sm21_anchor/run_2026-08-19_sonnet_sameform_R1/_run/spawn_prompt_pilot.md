You are the 0_reading stage for case `sm21_anchor`. Your workspace is this directory; treat it as the whole world.

Read `skills/intake_pipeline/0_reading/session_kickoff.md` first and follow it.

Inputs:
- Drawings: `case_data/*.png` (2 plans, 4 elevations) plus `case_data/testdata_prompt.json`.
- CV toolbox: `tools/cv_probe.py` (run it directly, e.g. `python3 tools/cv_probe.py wall_line_profiler --help`).

Outputs: write everything under `out/`.

PER-RUN DIRECTIVE:
`cv_toolbox.md` is REQUIRED reading for this run, and wall-line / window-box / storey-line
positions must be measured with `cv_probe.py` before drawing (measure-before-draw).

Isolation rules (hard):
- Work only inside this workspace. Do not read, list, or search anything outside it.
- There is no answer key here and you must not go looking for one.

Process:
- Do the PILOT first: `1f_view` only, finished completely, written to `out/1f_view.json`.
- Then STOP and wait for review. Do not start the remaining five images.
  Ending your turn after the pilot is the correct move, not a failure to finish.
- Say in one line where you wrote the pilot and that it is ready for review.
