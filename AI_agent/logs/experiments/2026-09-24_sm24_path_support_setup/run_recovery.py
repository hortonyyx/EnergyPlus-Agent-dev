"""Full-path support review of run37's own failed cold-start declaration."""
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import run_experiment, dump, digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = HERE.parent / '2026-09-24_sm24_cold_context_glm_run37'
RUN = HERE.parent / '2026-09-24_sm24_path_support_glm_run38'
SCOPE = '''Review the supplied unverified single-floor pixel declaration against
the original drawing. Choose consequential partition and door-connectivity
discrepancies yourself; no correct room counts, locations or geometry are supplied.
First reproduce the declaration with build_plan_bim, then use view_plan_wall_support
on its saved draft with wall colour/radius chosen from the original. Consider all
reported paths, declared apertures and gaps. Check the CLEAN original alongside
the marked panel; follow complete boundaries and both adjoining spaces. The
report is colour evidence, not a wall classifier: do not delete walls, add openings
or force connectivity just to clear unsupported intervals. Resolve discrepancies
with original crops/profiles and retain explicit uncertainty where needed. Preserve
reliable objects, inherited calibration/footprint and unobserved height assumptions.
Let deterministic code construct rooms and opening hosts from revised pixel paths.
Inspect the actual revised source and original-image overlay. Deliver the best
viewable candidate and distinguish observed, changed, preserved and unresolved
content. This is old-draft recovery, not a cold start. No successful candidate,
developer-selected error locations, previous local diagnosis, GT or evaluation
is supplied. Prior declaration claims are unverified, even if labelled checked.'''


def main():
    plan = OLD / 'plan_drafts/draft_002/plan.json'
    image = OLD / 'images/1f_view.png'
    dump(HERE/'experiment.json', dict(scope=SCOPE, provider='glm', effort='medium',
        timeout_seconds=1500, input_plan_sha256=digest(plan), image_sha256=digest(image),
        input_mode='saved_failure_recovery_no_location_hint',
        production_changes=['Full declared path support tool with clean original, aperture separation and proposed adjacency.',
                            'General guidance explains the new tool; scope explicitly requests its use.'],
        limitations=['Not a cold start, repetition or isolated single-factor causal experiment.']))
    run_experiment(SimpleNamespace(command='run', images=image.parent,
        mesh=None, building_input=None, out=RUN, scope=SCOPE, timeout=1500,
        provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=plan, plan_image='1f_view.png'))


if __name__ == '__main__':
    main()
