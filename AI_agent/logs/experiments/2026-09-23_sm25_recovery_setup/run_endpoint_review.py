"""Developer-scoped review of the new door's source-derived calibration; no target values/GT."""
from pathlib import Path
from types import SimpleNamespace
from scripts.tool_scripts.run_bim_agent import run_experiment

ROOT = Path(__file__).resolve().parents[4]
run_experiment(SimpleNamespace(
    command='run', images=ROOT/'case_tests/e2e_tests/sm25-L_anchor/case_data', mesh=None, building_input=None,
    out=ROOT/'AI_agent/logs/experiments/2026-09-23_sm25_door_extent_glm_run30',
    scope=(
        'Narrow original-drawing review of the newly added door 2f-door-c000-c006-junction only. '
        'The previous run built the corridor-to-northeastern-room connection but calibrated pixels '
        'against saved candidate wall coordinates. Those candidate coordinates are unverified geometry, '
        'not original dimension labels, so that calibration cannot independently establish accurate '
        'door endpoints. Recheck the original 2f plan using its labeled dimensions and actual extension '
        'line endpoints to establish an independent pixel-to-metre scale. Distinguish the clear door '
        'opening (door leaf/arc and jambs) from the longer gap between wall-face ink runs at the junction; '
        'wall-return extents and half thickness may differ from jamb endpoints. Use original-image '
        'measurements and record their uncertainty, naming which physical reference the endpoints use. '
        'Use claims to confirm or update only this door p1/p2; preserve its identity, kind, two hosts '
        'and assumed z unless a direct dimensional source proves otherwise. Keep every other room, wall '
        'and opening unchanged. Do not clip a measured door to fit its host or move a wall for convenience. '
        'If evidence conflicts with the current host, report the actual conflict. Replace obsolete '
        'endpoint/calibration notes explicitly, retain door-height and unexamined-building limitations. '
        'Verify the final door on an original-image overlay using the independent labeled calibration '
        'and submit a partial opening review. This is a developer-directed local recovery, not a '
        'whole-building review; no specific target dimension or reference answer is supplied.'),
    timeout=1200, provider='glm', exploratory_opus=False, effort='medium',
    resume_candidate=ROOT/'AI_agent/logs/experiments/2026-09-23_sm25_door_connections_glm_run29/candidate_02',
    resume_plan=None, plan_image=None))
