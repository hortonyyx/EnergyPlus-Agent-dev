"""Original-image-only Sonnet cold start after the bounded recovery comparison."""
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / '2026-09-25_sm25_relation_cold_claude_run48'


def main():
    assert not RUN.exists(), 'Never overwrite an existing experiment'
    prior = HERE.parent / '2026-09-24_sm25_cold_support_setup'
    scope = json.loads((prior/'frozen_supported_method.json').read_text())['scope']
    scope += (' Choose key same-space and separate-space observations from the original, '
        'then use check_source_space_relation to compare them with actual source ownership. '
        'Investigate conflicts against the original, revise geometry or observations as justified, '
        'and check the revised candidate again. Sample consistency is not whole-plan verification.')
    manifest = json.loads((HERE.parent/'2026-09-25_sm25_space_relation_claude_run47/inputs.json').read_text())
    hashes = dict(manifest['implementation_sha256'])
    hashes['src/agent/geometry/source_space_relations.py'] = digest(ROOT/'src/agent/geometry/source_space_relations.py')
    assert all(digest(ROOT/p) == h for p,h in hashes.items())
    dump(HERE/'frozen_method.json', dict(scope=scope, implementation_sha256=hashes,
        image_sha256=digest(prior/'inputs/1f_view.png'), provider='claude', role='sonnet',
        effort='medium', timeout_seconds=2400, mode='original_image_only_cold_start',
        withheld=['saved pixel declaration','saved source BIM','earlier observations',
                  'building declaration','correct counts','GT','evaluation evidence'],
        developer_participation='Selected case and generic method only; no local defect hint or intervention.',
        evaluation='Existing frozen original reference and GT F1 are accessed only after generation.'))
    run_experiment(SimpleNamespace(command='run', images=prior/'inputs', mesh=None,
        building_input=None, out=RUN, scope=scope, timeout=2400, provider='claude',
        exploratory_opus=False, effort='medium', resume_candidate=None,
        resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
