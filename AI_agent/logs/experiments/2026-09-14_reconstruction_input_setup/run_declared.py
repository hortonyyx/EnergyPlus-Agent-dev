"""sm24 fresh run with five original drawings and the explicit original declaration."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

# Same task wording and runtime budget as run15; no contour-probe answer supplied.
SCOPE = (
    'Reconstruct the target building shown in all supplied drawings into a viewable lightweight BIM. '
    'Preserve actual physical spaces, walls, openings, floor geometry and connectivity. '
    'Choose the observations, measurements and tools that the evidence requires. '
    'Inspect saved source geometry against the original drawings and revise substantive errors. '
    'Record assumptions and unexamined scope, and deliver a useful saved candidate within the budget.'
)


if __name__ == '__main__':
    out = ROOT / 'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run16'
    setup = Path(__file__).resolve().parent
    inputs = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    sources = [ROOT / 'scripts/tool_scripts/run_bim_agent.py',
               ROOT / 'scripts/tool_scripts/bim_agent_guidance.py',
               ROOT / 'scripts/tool_scripts/bim_agent_inputs.py',
               *sorted((ROOT / 'src/agent/geometry').glob('*.py')),
               ROOT / 'src/agent/execution/source_proposal.py',
               ROOT / 'src/agent/execution/subscription_json.py', Path(__file__).resolve()]
    frozen = {str(path.relative_to(ROOT)): path.read_bytes() for path in sources}
    dump(setup / 'declared_frozen_inputs.json', {
        'scope': SCOPE, 'timeout_seconds': 600, 'effort': 'medium', 'seed': None,
        'input_images': {path.name: digest(path) for path in sorted(inputs.glob('*.png'))},
        'building_input_path': str((inputs / 'testdata_prompt.json').relative_to(ROOT)),
        'building_input_sha256': digest(inputs / 'testdata_prompt.json'),
        'frozen_code_sha256': {name: digest(ROOT / name) for name in frozen},
        'input_boundary': 'Five original PNGs and original building declaration, generic scope and tool guide. Declaration includes thermal_zones=8 with its stated downstream meaning. No old observation, seed, GT, correct coordinates or generation-time developer feedback.',
        'development_mode': 'One fresh declared-input experiment; no contour-probe response supplied. Runtime unchanged after launch; offline evaluation follows completion.',
    })
    run_experiment(SimpleNamespace(images=inputs, building_input=inputs / 'testdata_prompt.json',
        out=out, scope=SCOPE, timeout=600, effort='medium', resume_candidate=None))
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
