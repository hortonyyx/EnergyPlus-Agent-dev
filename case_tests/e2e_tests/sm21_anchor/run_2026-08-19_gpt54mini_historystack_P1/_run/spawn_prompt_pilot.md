You are the 0_reading stage for case `sm21_anchor`. Your workspace is this directory; treat it as the whole world.

Read `skills/intake_pipeline/0_reading/session_kickoff.md` first and follow it.

Inputs:
- Drawings: `case_data/*.png` (2 plans, 4 elevations) plus `case_data/testdata_prompt.json`.
- Pre-computed prescan candidates and combined overlays for every view are already staged at
  `out/prescan/<view>/cv_evidence/<view>/prescan/` (candidates.json + combined_overlay.png).
- CV toolbox: `tools/run_cv_probe.py`, driven through request JSON files written inside this workspace.
  Its contract is documented in `skills/intake_pipeline/0_reading/cv_toolbox.md`.

Outputs: write everything under `out/`.

Isolation rules (hard):
- Work only inside this workspace. Do not read, list, or search anything outside it.
- There is no answer key here and you must not go looking for one.

Process:
- Do the PILOT first: `1f_view` only, finished completely, written to `out/1f_view.json`.
- Then STOP and wait for review. Do not start the remaining five images.
  Ending your turn after the pilot is the correct move, not a failure to finish.
- Say in one line where you wrote the pilot and that it is ready for review.
