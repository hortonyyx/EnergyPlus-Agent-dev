"""Fresh full-input quality experiment; no generation-time developer correction."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

SCOPE = (
    'Reconstruct a viewable lightweight BIM of the supplied target building from all '
    'original drawings and the original building declaration. Prioritize faithful physical '
    'partitions, full spatial extents, openings and connectivity. This experiment evaluates '
    'quality with time for observation and revision; first-draft speed is not a target. '
    'Use build_plan_bim for the plan when its supported geometry fits the observed building, '
    'letting code derive spaces and opening hosts from your observed pixel paths. Compare '
    'any returned declaration preview and actual source feedback with original evidence; '
    'a compile error does not justify inventing a wall or altering an aperture to fit. '
    'Choose local observations or delegation where useful and check conflicting evidence. '
    'Use the supplied elevations to resolve exterior openings and vertical dimensions. '
    'Keep explicit assumptions and unexamined scope. Deliver the saved candidate with an '
    'honest account of what has and has not been verified.'
)


if __name__ == '__main__':
    setup = Path(__file__).resolve().parent
    originals = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    out = ROOT / 'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run18'
    sources = [ROOT / 'scripts/tool_scripts/run_bim_agent.py',
               ROOT / 'scripts/tool_scripts/bim_agent_guidance.py',
               ROOT / 'scripts/tool_scripts/bim_agent_inputs.py',
               *sorted((ROOT / 'src/agent/geometry').glob('*.py')),
               ROOT / 'src/agent/execution/source_proposal.py',
               ROOT / 'src/agent/execution/subscription_json.py', Path(__file__).resolve()]
    frozen = {str(path.relative_to(ROOT)): path.read_bytes() for path in sources}
    dump(setup / 'frozen_inputs.json', {
        'scope': SCOPE, 'timeout_seconds': 1800, 'effort': 'medium', 'seed': None,
        'input_images': {path.name: digest(path) for path in sorted(originals.glob('*.png'))},
        'building_input_sha256': digest(originals / 'testdata_prompt.json'),
        'frozen_code_sha256': {name: digest(ROOT / name) for name in frozen},
        'input_boundary': 'Five original PNGs, original declaration and generic quality/tool guidance. No old candidate, observation, GT, correct room count or case-specific geometry hints.',
        'development_mode': 'Developer selects the experiment and optional compiler capability. No generation-time developer feedback. Fresh generation, not proof of stable full-building autonomy or a single-variable ablation against run17 (input scope, feedback and budget differ).',
    })
    try:
        run_experiment(SimpleNamespace(images=originals,
            building_input=originals / 'testdata_prompt.json', out=out,
            scope=SCOPE, timeout=1800, effort='medium', resume_candidate=None))
    finally:
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
