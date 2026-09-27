"""Independent preservation and semantic evidence audit after model termination."""
from collections import Counter
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / '2026-09-27_sm24_room_types_recovery_claude_run60'
load = lambda path: json.loads(path.read_text())


def main():
    run = RUN
    assert (run / 'summary.json').is_file()
    frozen, manifest = load(HERE / 'recovery_frozen_method.json'), load(run / 'inputs.json')
    assert frozen['scope'] == manifest['scope']
    assert digest(run / 'seed/proposal.json') == frozen['seed_proposal_sha256']
    assert not manifest['input_contents']['ground_truth_or_evaluation']['included']
    assert not manifest['input_contents']['building_declaration']['included']
    for name, sha in frozen['image_sha256'].items():
        assert digest(run / 'images' / name) == sha == manifest['images'][name]['sha256']
    assert all(digest(ROOT / name) == sha for name, sha in manifest['implementation_sha256'].items())
    shared = importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run')
    chosen = load(run / 'delivery.json')['candidate']
    source, proposal, display = shared.replay_final(run, chosen)
    seed = load(run / 'seed/source_model.json')
    baseline = load(HERE.parent / '2026-09-27_sm24_room_types_claude_run59/candidate_01/source_model.json')
    preserved = ['floors', 'boundaries', 'openings', 'connections', 'opening_hosts', 'boundary_relations',
                 'unbuilt_openings', 'unsupported']
    assert all(seed[key] == source[key] for key in preserved)
    assert all(baseline[key] == source[key] for key in preserved)
    for old, current in zip(baseline['spaces'], source['spaces']):
        assert all(old[k] == current[k] for k in ['id', 'floor_id', 'polygon', 'z_floor', 'height'])
    def physical_spaces(value):
        return [{k: v for k, v in row.items() if k not in {'role', 'role_evidence'}} for row in value['spaces']]
    assert physical_spaces(seed) == physical_spaces(source)
    original = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.audit_run')
    original.audit(run)
    from src.agent.judge.gt import load_gt_document
    opening = shared._opening_diagnostic(source, load_gt_document('sm24_anchor'), load(run / 'evaluation/partition.json'))
    dump(run / 'evaluation/exterior_opening_diagnostic.json', opening)
    finalizer = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run')
    finalizer.finalize(run)
    actions = [json.loads(line) for line in (run / 'tools.jsonl').read_text().splitlines()]
    assert not any(row['action'] == 'review_detail' for row in actions)
    receipt = load(run / 'agent_receipt.json')
    assert receipt['actual_model'].startswith('claude-sonnet-')
    assert len(list(run.glob('*_receipt.json'))) == 1
    report = dict(candidate=chosen, source_sha256=source['source_model_sha256'],
        status='physical_preservation_pass_semantics_require_original_review',
        counts={key: len(source[key]) for key in ['spaces', 'boundaries', 'openings', 'connections']},
        geometry_and_relations_preserved=preserved + ['space geometry and geometry evidence'],
        source_and_display_replay_exact=True,
        original_run59_geometry_and_relations_preserved=True,
        reference_topics=[r['data']['topic'] for r in actions if r['action'] == 'get_bim_reference'],
        roles=dict(Counter(s['role'] for s in source['spaces'])), spaces=source['spaces'],
        source_assumptions=source['assumptions'], unresolved=source['generation']['unresolved'],
        actual_model=receipt['actual_model'], elapsed_seconds=receipt['elapsed_seconds'],
        cli_estimated_usd_not_bill=receipt['result'].get('total_cost_usd'),
        limits=['Bounded recovery explicitly requested function review; not autonomous cold-start success.',
                'Catalog and evidence presence do not establish real room use.',
                'Height claim confirmations from the previous run are not imported with the proposal.'])
    dump(run / 'evaluation/room_type_audit.json', report)
    print(json.dumps({k: report[k] for k in ['candidate', 'counts', 'reference_topics', 'roles', 'elapsed_seconds']}, indent=2))


if __name__ == '__main__':
    main()
