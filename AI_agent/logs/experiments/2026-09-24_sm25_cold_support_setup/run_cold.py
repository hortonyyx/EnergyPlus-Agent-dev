"""Transfer the frozen original-plan method to sm25, with no saved proposal."""
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-24_sm25_cold_support_glm_run41'


def main():
    assert not RUN.exists(), 'Never overwrite an existing experiment'
    frozen = json.loads((HERE.parent / '2026-09-24_sm24_repeat_support_setup/frozen_method.json').read_text())
    checks = {name: digest(ROOT / name) == value
              for name, value in frozen['implementation_sha256'].items()}
    assert all(checks.values()), 'Production method must remain frozen'
    image = HERE / 'inputs/1f_view.png'
    assert list(image.parent.glob('*.png')) == [image]
    dump(HERE / 'frozen_method.json', dict(
        scope=frozen['scope'], implementation_sha256=frozen['implementation_sha256'],
        image_sha256=digest(image), provider='glm', model='glm-5.3-flash',
        effort='medium', timeout_seconds=2400,
        method_source='2026-09-24_sm24_repeat_support_glm_run40',
        production_hashes_match_run40=checks,
        differences_from_run40=['sm25 first-floor original image replaces sm24.',
            'Budget increased from 1800 to 2400 seconds for the more complex plan; quality is the priority.'],
        withheld=['saved proposal', 'prior wall network', 'prior calibration',
                  'building declaration', 'ground truth', 'evaluation evidence'],
        acceptance_note='Unavailable heights remain explicit assumptions; internal-door heights alone do not block acceptance.'))
    run_experiment(SimpleNamespace(command='run', images=image.parent,
        mesh=None, building_input=None, out=RUN, scope=frozen['scope'], timeout=2400,
        provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
