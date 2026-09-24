"""Fresh original-only invocation after adding deterministic concave support."""
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-24_sm25_cold_support_glm_run42'


def main():
    assert not RUN.exists(), 'Never overwrite an existing experiment'
    previous = json.loads((HERE / 'frozen_method.json').read_text())
    hashes = {name: digest(ROOT / name) for name in previous['implementation_sha256']}
    changed = [name for name, value in hashes.items() if value != previous['implementation_sha256'][name]]
    assert set(changed) == {'scripts/tool_scripts/run_bim_agent.py',
        'scripts/tool_scripts/bim_agent_guidance.py', 'src/agent/geometry/plan_partition.py'}
    image = HERE / 'inputs/1f_view.png'
    assert digest(image) == previous['image_sha256']
    dump(HERE / 'frozen_supported_method.json', dict(previous,
        implementation_sha256=hashes, changed_implementation_files=changed,
        differences_from_run41=['Deterministic concave footprint/recessed window support and matching general reference guidance.',
            'New independent invocation; no prior observations, proposals or coordinates supplied.']))
    run_experiment(SimpleNamespace(command='run', images=image.parent,
        mesh=None, building_input=None, out=RUN, scope=previous['scope'], timeout=2400,
        provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
