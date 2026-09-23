"""One scoped GLM subscription recovery; original drawings and historical proposal only."""
from pathlib import Path
from types import SimpleNamespace
from scripts.tool_scripts.run_bim_agent import run_experiment

ROOT = Path(__file__).resolve().parents[4]
run_experiment(SimpleNamespace(
    command='run', images=ROOT/'case_tests/e2e_tests/sm25-L_anchor/case_data',
    mesh=None, building_input=None,
    out=ROOT/'AI_agent/logs/experiments/2026-09-23_sm25_door_connections_glm_run29',
    scope=(
        'Continue the supplied historical sm25 candidate with original-drawing evidence, focusing on '
        'unbuilt door observations and their actual room connections across the two floors. '
        'First inspect the unresolved records and relevant candidate rooms/openings, then choose '
        'original-image views, crops and measurements to determine which physical openings they describe. '
        'The number of old scan records is not a target door count. Resolve ambiguity from the complete '
        'wall junction, door symbol and both sides, not by clipping to a convenient host. '
        'Use get_bim_reference("edits") and get_bim_reference("claims") for local addition and evidence '
        'application. Observe plan endpoints/host geometry with record_claim and apply values by reference; '
        'state assumed heights separately. Use reshape_spaces only if image evidence requires changing '
        'physical boundaries, with claims for changed coordinates and explicit dependent opening edits. '
        'Preserve other floors, rooms and existing openings unless a specific original-image discrepancy '
        'requires a local change. Check the resulting source plan and original overlay, and submit a '
        'partial opening review for the actual corrected connection. Replace obsolete unresolved notes '
        'explicitly while keeping all unexamined limitations. Deliver an inspectable candidate and an '
        'honest account of measured, assumed and unresolved content; this scoped recovery is not whole-building acceptance.'),
    timeout=1800, provider='glm', exploratory_opus=False, effort='medium',
    resume_candidate=Path(__file__).resolve().parent/'seed', resume_plan=None, plan_image=None))
