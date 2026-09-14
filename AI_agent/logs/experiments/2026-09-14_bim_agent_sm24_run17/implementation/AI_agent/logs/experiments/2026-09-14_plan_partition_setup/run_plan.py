"""One bounded original-plan experiment for the optional deterministic wall compiler."""
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

SCOPE = (
    'Create a viewable initial single-floor BIM from the supplied original plan and original '
    'building declaration. This experiment supplies the plan only; elevations are deliberately '
    'not supplied. Focus on actual physical partition paths, complete spatial extents and '
    'plan-visible apertures. Test build_plan_bim with your own observed pixel wall paths and '
    'calibration so code can derive rooms and opening hosts. Save an initial draft early, '
    'inspect its returned source plan and original overlay, then revise the most consequential '
    'discrepancies within this short budget. Do not spend the whole budget describing a layout '
    'without saving it. Mark unexamined elevations, uncertain heights and any incomplete '
    'opening coverage explicitly; do not claim a complete building restoration. Choose '
    'representative wall planes from drawing evidence and explain any regularization. '
    'Retain observed opening sizes when checking their hosts. Deliver the saved partial result.'
)


if __name__ == '__main__':
    setup = Path(__file__).resolve().parent
    originals = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    images = setup / 'plan_only_input'
    images.mkdir(exist_ok=False)
    shutil.copyfile(originals / '1f_view.png', images / '1f_view.png')
    out = ROOT / 'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run17'
    sources = [ROOT / 'scripts/tool_scripts/run_bim_agent.py',
               ROOT / 'scripts/tool_scripts/bim_agent_guidance.py',
               ROOT / 'scripts/tool_scripts/bim_agent_inputs.py',
               *sorted((ROOT / 'src/agent/geometry').glob('*.py')),
               ROOT / 'src/agent/execution/source_proposal.py',
               ROOT / 'src/agent/execution/subscription_json.py', Path(__file__).resolve()]
    frozen = {str(path.relative_to(ROOT)): path.read_bytes() for path in sources}
    dump(setup / 'frozen_inputs.json', {
        'scope': SCOPE, 'timeout_seconds': 300, 'effort': 'medium', 'seed': None,
        'input_images': {path.name: digest(path) for path in images.glob('*.png')},
        'building_input_sha256': digest(originals / 'testdata_prompt.json'),
        'frozen_code_sha256': {name: digest(ROOT / name) for name in frozen},
        'input_boundary': 'Only original plan PNG, original building declaration, generic compiler-focused scope and tool guide. No old observation/candidate, GT, correct wall coordinates or room counts. Original thermal_zones retains backend meaning.',
        'development_mode': 'Developer selects a bounded plan task and new compiler capability. Fresh generation, not an autonomous full-building or cost/quality ablation. No generation-time developer feedback.',
    })
    run_experiment(SimpleNamespace(images=images, building_input=originals / 'testdata_prompt.json',
        out=out, scope=SCOPE, timeout=300, effort='medium', resume_candidate=None))
    changed = []
    for name, data in frozen.items():
        if (ROOT / name).read_bytes() != data:
            changed.append(name)
        target = out / 'implementation' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    dump(out / 'frozen_code_verification.json', {
        'all_frozen_sources_unchanged': not changed, 'changed_files': changed,
        'files': {name: digest(out / 'implementation' / name) for name in frozen},
    })
