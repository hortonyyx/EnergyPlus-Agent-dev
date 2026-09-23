"""Bounded recovery from run32's own unverified plan; no reference geometry."""
from pathlib import Path
from types import SimpleNamespace
from scripts.tool_scripts.run_bim_agent import run_experiment

HERE = Path(__file__).resolve().parent
SCOPE = '''Recover the supplied unverified pixel plan against its original drawing.
This is a developer-targeted partition review, not an independent cold start.
Concentrate on the eastern physical dividers and their full adjoining spaces,
the corridor's lower turns, and the top internal door's actual jambs.
The old plan's claims about these areas are unverified. Trace full wall paths,
both ends and junction continuations in the original, and follow both adjoining
spaces around their entire boundaries. Use cross-axis profile evidence and
wider original crops where helpful; a junction peak or a cropped line end is
not an entire wall or a free physical end. Distinguish furniture and door leaves
from enclosure. Do not force a room count or retain a wrong divider for a door.
Update observed pixel paths/apertures and appropriate space seeds, letting
build_plan_bim construct rooms and hosts. Keep the existing declared coordinate
frame, floor heights, outer footprint, and unaffected paths/openings for this
bounded test; they are outside this review and not thereby certified. Preserve
unobserved heights as assumptions. You may correct a targeted aperture from
its actual symbol, never just trim it to silence a host error. Rebuild and inspect
the actual source plan and original overlay; explicitly report which observed
dividers, full spaces and door connections were checked and what remains
uncertain. No old successful candidate, prior local answer, correct geometry,
expected counts or evaluation/GT is supplied.'''


def main():
    run_experiment(SimpleNamespace(
        command='run', images=HERE.parent/'2026-09-23_sm24_cold_plan_setup/inputs',
        mesh=None, building_input=None,
        out=HERE.parent/'2026-09-23_sm24_wall_context_recovery_glm_run35',
        scope=SCOPE, timeout=1500, provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None,
        resume_plan=HERE.parent/'2026-09-23_sm24_cold_plan_glm_run32/plan_drafts/draft_004/plan.json',
        plan_image='1f_view.png'))


if __name__ == '__main__':
    main()
