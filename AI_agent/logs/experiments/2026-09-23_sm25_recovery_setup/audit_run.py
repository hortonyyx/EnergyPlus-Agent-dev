"""Post-run verification only: compare source objects and replay final candidate."""
import json
import tempfile
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.execution.bim_claim_state import project
from src.agent.execution.source_proposal import export_source_proposal

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / 'AI_agent/logs/experiments/2026-09-23_sm25_door_connections_glm_run29'


def main():
    load = lambda path: json.loads((RUN / path).read_text())
    assert (RUN/'summary.json').is_file(), 'Wait until generator finishes'
    manifest, receipt, delivery = load('inputs.json'), load('agent_receipt.json'), load('delivery.json')
    chosen = delivery['candidate']
    old, new = load('seed/source_model.json'), load(f'{chosen}/source_model.json')
    proposal = load(f'{chosen}/proposal.json')
    comparisons = {}
    for field in ('spaces', 'boundaries', 'openings', 'connections'):
        key = 'opening_id' if field == 'connections' else 'id'
        a, b = ({r[key]: r for r in source[field]} for source in (old, new))
        comparisons[field] = {'added': [b[i] for i in b.keys()-a.keys()],
            'removed': [a[i] for i in a.keys()-b.keys()],
            'changed': [{'id': i, 'before': a[i], 'after': b[i]} for i in a.keys() & b.keys() if a[i] != b[i]],
            'unchanged': sum(a[i] == b[i] for i in a.keys() & b.keys())}
    hashes = {p: digest(ROOT/p) == h for p,h in manifest['implementation_sha256'].items()}
    assert all(hashes.values()), 'Production code changed during run'
    with tempfile.TemporaryDirectory(prefix='sm25-source-replay-') as temp:
        report = export_source_proposal(proposal, Path(temp)/'candidate', provenance=new['generation']['provenance'])
        replay = json.loads((Path(temp)/'candidate/source_model.json').read_text())
        exact_replay = replay == new
        assert exact_replay
        exact_display = json.loads((Path(temp)/'candidate/display_geometry.json').read_text()) == load(f'{chosen}/display_geometry.json')
        assert exact_display
    state = project(Toolkit(RUN).claims(), chosen)
    old_records = [r for r in old['unsupported'] if r.get('kind') == 'as_drawn_opening_unbuilt']
    resolutions = [r for r in proposal['geometry'].get('corrections', []) if r.get('operation') == 'resolve_unbuilt_observation']
    actual_ids = {o['id'] for o in new['openings']}
    resolution_audit = [{'observation': r, 'resolutions': [a for a in resolutions if a['before'] == r],
        'remains_unsupported': r in new['unsupported']} for r in old_records]
    assert all(r['remains_unsupported'] or r['resolutions'] for r in resolution_audit)
    for row in resolutions:
        assert set(row['opening_ids']) <= actual_ids, 'Resolution refers to unbuilt replacement'
    out = {'mode': 'post_generation_developer_audit', 'candidate': chosen,
        'actual_model': receipt.get('actual_model'), 'elapsed_seconds': receipt.get('elapsed_seconds'),
        'counts': {k: len(new[k]) for k in ('spaces','boundaries','openings','connections','unsupported','unbuilt_openings')},
        'source_object_comparisons': comparisons, 'floors_unchanged': old['floors'] == new['floors'],
        'historical_observation_resolution': resolution_audit, 'source_replay_exact': exact_replay,
        'display_replay_exact': exact_display, 'runtime_implementation_hashes_match': all(hashes.values()),
        'current_claim_states': [{'id': r['id'], 'state': r['state'], 'missing_bindings': r['missing_bindings']} for r in state['claims']],
        'state_matches_delivery': json.loads(json.dumps(state)) == delivery['current_claim_state'],
        'height_coverage_summary': delivery['height_coverage']['summary'],
        'viewer_has_no_remote_scripts': '<script src="http' not in (RUN/chosen/'viewer.html').read_text(),
        'drawing_fidelity': 'requires independent visual audit; source replay is not drawing acceptance',
        'not_evaluated': ['whole-building fidelity','door height measurements','cold start','EP','human acceptance']}
    dump(RUN/'postrun_audit.json', out)
    print(json.dumps({k:v for k,v in out.items() if k not in {'source_object_comparisons','historical_observation_resolution'}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    if args.run:
        RUN = args.run.resolve()
    main()
