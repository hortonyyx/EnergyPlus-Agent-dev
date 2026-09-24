"""Report both completed runs without selecting a winner or changing raw scores."""
from collections import Counter
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

HERE = Path(__file__).resolve().parent
RUNS = [HERE.parent/name for name in (
    '2026-09-24_sm24_cold_support_glm_run39',
    '2026-09-24_sm24_repeat_support_glm_run40')]


def main():
    load = lambda p: json.loads(p.read_text())
    assert all((run/'summary.json').exists() for run in RUNS), 'Post-generation only'
    manifests = [load(run/'inputs.json') for run in RUNS]
    frozen = load(HERE/'frozen_method.json')
    for manifest in manifests:
        assert manifest['scope'] == frozen['scope']
        assert manifest['implementation_sha256'] == frozen['implementation_sha256']
        assert manifest['images']['1f_view.png']['sha256'] == frozen['image_sha256']
        assert manifest['source_input_mode'] == 'original_images_only'
    receipts = [load(run/'agent_receipt.json') for run in RUNS]
    sessions = [receipt['result']['session_id'] for receipt in receipts]
    assert len(set(sessions)) == len(sessions), 'Independent runtime sessions required'
    rows = []
    for run, receipt in zip(RUNS, receipts):
        audit = load(run/'postrun_audit.json')
        cold = load(run/'evaluation/cold_start_audit.json')
        raw = load(run/'evaluation/original_partition.json')['comparison']
        declared = load(run/'evaluation/declared_frame_diagnostic.json')
        source = load(run/audit['candidate']/'source_model.json')
        internal_doors = [o['id'] for o in source['openings']
                          if o['kind'] == 'door' and not o['exterior']]
        rows.append(dict(
            run=run.name, candidate=audit['candidate'],
            source_sha256=load(run/'delivery.json')['source_model_sha256'],
            actual_model=receipt['actual_model'], effort=receipt['effort'],
            elapsed_seconds=receipt['elapsed_seconds'],
            cli_estimate_usd_not_bill=receipt['result'].get('total_cost_usd'),
            counts=audit['counts'],
            original_partition_status=raw['status'],
            original_partition_matches=raw['matched_count'],
            original_partition_match_statuses=dict(Counter(r['status'] for r in raw['matches'])),
            original_partition_finding_codes=dict(Counter(r['code'] for r in raw['findings'])),
            original_max_boundary_distance_m=max(r['boundary_hausdorff_m'] for r in raw['matches']),
            original_position_matches=audit['position_matches'],
            original_host_matches=audit['host_matches'],
            original_door_connection_matches=audit['door_connections_matched'],
            declared_frame_partition_status=declared['comparison']['status'],
            declared_frame_position_matches=declared['positions_matched'],
            declared_frame_host_matches=declared['hosts_matched'],
            declared_frame_door_connection_matches=declared['door_connections_matched'],
            internal_door_ids_with_nonblocking_unknown_height=internal_doors,
            tools=cold['tools'],
            actual_image_count=load(run/'transport_audit.json')['image_count'],
            source_replay_exact=audit['source_replay_exact'],
            display_replay_exact=audit['display_replay_exact']))
    report = dict(
        mode='post_generation_repeat_comparison_no_mutation_no_best_run_selection',
        scope_and_production_hashes_identical=True,
        independent_runtime_sessions_verified=True,
        acceptance_scope=dict(
            internal_door_height='Unavailable in supplied evidence; explicit assumption is nonblocking per user 2026-09-24.',
            internal_door_geometry='Existence, position, host, connectivity and within-space height checks remain applicable.',
            other_heights='Plan-only experiment: assumed, not verified; no new exemption for heights supplied in future evidence.'),
        runs=rows,
        limits=['Two runs on one image are not a general success rate or broad stability proof.',
                'Raw original and declared-frame scores remain distinct and unchanged.',
                'Space count alone cannot establish correct partitions; compare matched geometry, findings and original overlay.'])
    dump(HERE/'repeat_comparison.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
