"""Independent repeat of run39, with identical input scope and runtime hashes."""
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-24_sm24_repeat_support_glm_run40'


def main():
    assert not RUN.exists(), 'Never overwrite an existing experiment'
    frozen = json.loads((HERE.parent / '2026-09-24_sm24_cold_support_setup/frozen_method.json').read_text())
    previous = json.loads((HERE.parent / '2026-09-24_sm24_cold_support_glm_run39/inputs.json').read_text())
    checks = {name: digest(ROOT / name) == value
              for name, value in frozen['implementation_sha256'].items()}
    assert all(checks.values()), 'Production method must remain frozen'
    assert previous['scope'] == frozen['scope']
    image = HERE.parent / '2026-09-23_sm24_cold_plan_setup/inputs/1f_view.png'
    assert digest(image) == frozen['image_sha256']
    assert list(image.parent.glob('*.png')) == [image]
    dump(HERE / 'frozen_method.json', dict(frozen,
        repetition_of='2026-09-24_sm24_cold_support_glm_run39',
        production_hashes_match_run39=checks,
        differences_from_run39=['New independent subscription invocation/output directory only; no saved proposal, answers or prior calibration supplied.'],
        acceptance_note='User confirmed unavailable internal-door heights are not a blocking acceptance item; still explicitly assumed and retained in raw diagnostics. Generation scope unchanged.'))
    run_experiment(SimpleNamespace(command='run', images=image.parent,
        mesh=None, building_input=None, out=RUN, scope=frozen['scope'], timeout=1800,
        provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
