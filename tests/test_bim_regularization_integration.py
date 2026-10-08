"""Q1 entry points preserve inputs, reject unsafe saves and expose their audit."""
import copy
import hashlib
import json
import pytest

from scripts.tool_scripts.run_bim_agent import Toolkit
from scripts.tool_scripts.bim_agent_regularization import (
    apply_cross_storey_skip_policy,
    selected_cross_storey_failure_policy,
    summary,
)
from scripts.tool_scripts.bim_agent_delivery_display import render_regularization_html
from src.agent.geometry.plan_partition import compile_plan_partition
from tests.test_bim_agent_tools import _run_with_one_image, _two_room_proposal
from tests.test_bim_agent_plan_partition import example


def test_new_plan_retains_raw_input_and_full_audit_with_compact_reply(tmp_path):
    run = _run_with_one_image(tmp_path)
    raw = json.dumps(example())
    result = Toolkit(run).build_plan('plan.png', raw)
    assert result['source_geometry_ready'], result
    record = result['plan_input']
    assert (run / record['submitted_plan_file']).read_text() == raw
    effective = json.loads((run / record['plan_file']).read_text())
    full = json.loads((run / result['regularization']['file']).read_text())
    assert effective['regularization'] == full
    assert record['regularization'] == summary(full)
    assert hashlib.sha256((run / record['plan_file']).read_bytes()).hexdigest() == record['plan_sha256']
    source = json.loads((run / result['candidate'] / 'source_model.json').read_text())
    assert source['generation']['provenance']['plan_input']['regularization'] == full
    assert '几何规整清单' in (run / result['candidate'] / 'viewer.html').read_text()
    assert (run / result['candidate'] / 'regularization_report.json').is_file()


def test_thin_named_space_rejects_with_audit_and_without_a_candidate(tmp_path):
    run = _run_with_one_image(tmp_path)
    plan = example()
    plan['partitions'][0]['points'] = [[1.5, 1], [1.5, 7]]
    plan['space_seeds'] = []
    plan['openings'] = []
    result = Toolkit(run).build_plan('plan.png', json.dumps(plan))
    assert result['source_geometry_ready'] is False
    assert result['saved_candidate'] is None
    assert result['regularization']['rejected_count']
    assert (run / result['regularization']['file']).is_file()
    assert (run / result['plan_input']['draft_view']['image_file']).is_file()
    assert not list(run.glob('candidate_*'))


def test_legacy_policy_is_owned_by_the_run_manifest(tmp_path):
    run = _run_with_one_image(tmp_path)
    plan = example()
    plan['partitions'][0]['points'] = [[1.5, 1], [1.5, 7]]
    plan['openings'] = []
    plan['space_seeds'] = []
    raw = json.dumps(plan)
    toolkit = Toolkit(run)
    toolkit.manifest['plan_regularization_rule'] = 'legacy'
    result = toolkit.build_plan('plan.png', raw)
    assert result['source_geometry_ready'], result
    assert 'regularization' not in result
    assert (run / result['plan_input']['plan_file']).read_text() == raw
    toolkit.manifest.pop('plan_regularization_rule')
    plan['regularization'] = {'rule_version': 'legacy', 'status': 'pass'}
    assert toolkit.build_plan('plan.png', json.dumps(plan))['source_geometry_ready'] is False


def test_cross_storey_failure_policy_is_owned_by_the_run_manifest():
    assert selected_cross_storey_failure_policy({}) == 'reject_assembly'
    assert selected_cross_storey_failure_policy({
        'cross_storey_alignment_failure_policy': 'skip_failed_pair',
    }) == 'skip_failed_pair'
    with pytest.raises(ValueError, match='unknown cross_storey_alignment_failure_policy'):
        selected_cross_storey_failure_policy({
            'cross_storey_alignment_failure_policy': 'silently_ignore',
        })
    lines = [
        {'floor_id': 'L1', 'axis': 'x', 'coordinate_m': 1.0,
         'span_m': [0.0, 4.0]},
        {'floor_id': 'L2', 'axis': 'x', 'coordinate_m': 1.2,
         'span_m': [0.0, 4.0]},
    ]
    filtered = apply_cross_storey_skip_policy(
        {'status': 'rejected', 'total': 2,
         'counts': {'storey_wall_offset': 1, 'source_only_violation': 1},
         'items': [
             {'type': 'storey_wall_offset', 'lines': lines},
             {'type': 'source_only_violation', 'objects': ['unrelated']},
         ]},
        {'cross_storey_failure_policy': 'skip_failed_pair',
         'skipped_alignments': [{
             'type': 'cross_storey_alignment_skipped',
             'source': lines[0], 'target': lines[1],
         }]},
    )
    assert filtered['status'] == 'rejected'
    assert [row['type'] for row in filtered['items']] == ['source_only_violation']
    assert [row['type'] for row in filtered['skipped_items']] == [
        'storey_wall_offset']
    changed_lines = copy.deepcopy(lines)
    changed_lines[0]['coordinate_m'] += 1e-6
    no_longer_matching = apply_cross_storey_skip_policy(
        {'status': 'rejected', 'total': 1,
         'counts': {'storey_wall_offset': 1},
         'items': [{'type': 'storey_wall_offset', 'lines': changed_lines}]},
        {'cross_storey_failure_policy': 'skip_failed_pair',
         'skipped_alignments': [{
             'type': 'cross_storey_alignment_skipped',
             'source': lines[0], 'target': lines[1],
         }]},
    )
    assert no_longer_matching['status'] == 'rejected'
    assert no_longer_matching['items'][0]['type'] == 'storey_wall_offset'
    assert 'skipped_items' not in no_longer_matching


def test_toolkit_assembly_and_delivery_honor_cross_storey_failure_policy(tmp_path):
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    rows = []
    for index, coordinates in enumerate(((6.4,), (6.0, 7.2))):
        plan = example()
        plan['partitions'] = [{
            'id': f'wall-{wall_index}',
            'points': [[coordinate, 1], [coordinate, 7]],
            'source_refs': [f'plan.png: wall {wall_index}'],
        } for wall_index, coordinate in enumerate(coordinates, start=1)]
        plan['openings'][0]['p1'][0] = coordinates[0]
        plan['openings'][0]['p2'][0] = coordinates[0]
        built = toolkit.build_plan('plan.png', json.dumps(plan))
        assert built['source_geometry_ready'], built
        record = built['plan_input']
        rows.append({
            'draft_id': record['plan_file'].split('/')[1],
            'expected_plan_sha256': record['plan_sha256'],
            'floor_id': f'L{index + 1}',
            'z_floor': index * 3.0,
            'evidence': 'synthetic cross-storey policy fixture',
        })

    rejected = toolkit.assemble_plans(json.dumps(rows))
    assert rejected['source_geometry_ready'] is False
    assert rejected['saved_candidate'] is None
    assert rejected['regularization']['status'] == 'rejected'
    assert len(list(run.glob('candidate_*'))) == 2

    toolkit.manifest['cross_storey_alignment_failure_policy'] = 'skip_failed_pair'
    assembled = toolkit.assemble_plans(json.dumps(rows))
    assert assembled['source_geometry_ready'], assembled
    assert assembled['candidate'] == 'candidate_03'
    assert assembled['regularization']['status'] == 'pass'
    assert assembled['regularization']['skipped_alignment_count'] == 1
    assert len(list(run.glob('candidate_*'))) == 3

    parent_proposal = run / assembled['candidate'] / 'proposal.json'
    parent_source = run / assembled['candidate'] / 'source_model.json'
    protected = {
        parent_proposal: hashlib.sha256(parent_proposal.read_bytes()).hexdigest(),
        parent_source: hashlib.sha256(parent_source.read_bytes()).hexdigest(),
    }
    source = json.loads(parent_source.read_text(encoding='utf-8'))
    space_id = source['spaces'][0]['id']
    revised = toolkit.revise(assembled['candidate'], json.dumps([{
        'op': 'set_space_role',
        'space_id': space_id,
        'role': 'conference/meeting/multipurpose',
        'basis': 'inferred',
        'assumptions': ['Synthetic use-only inheritance check'],
        'source_refs': ['synthetic test'],
        'reason': 'Verify that a non-geometric revision inherits the audited skip',
    }]))
    assert revised['source_geometry_ready'], revised
    assert revised['candidate'] == 'candidate_04'
    revised_source = json.loads(
        (run / revised['candidate'] / 'source_model.json').read_text(encoding='utf-8'))
    provenance = revised_source['generation']['provenance']
    assert provenance['parent_candidate'] == assembled['candidate']
    assert provenance['parent_proposal_sha256'] == protected[parent_proposal]
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest
               for path, digest in protected.items())

    delivered = toolkit.delivery(
        revised['candidate'], selection_origin='offline_test')
    assert delivered['building_precision']['status'] == 'pass'
    assert {row['type'] for row in delivered['building_precision']['skipped_items']} == {
        'storey_wall_offset', 'thin_horizontal_contact'}
    reports = delivered['building_precision']['regularization']['reports']
    skipped = reports[0]['skipped_alignments']
    assert len(skipped) == 1
    assert skipped[0]['type'] == 'cross_storey_alignment_skipped'
    assert skipped[0]['disposition'] == 'original_pair_preserved_and_reported'
    delivery_html = (run / 'delivery.html').read_text(encoding='utf-8')
    assert '未对齐并保留原值' in delivery_html
    assert '自动对齐未安全完成，保留原值并随交付说明' in delivery_html
    assert 'cross_storey_alignment_skipped' in delivery_html
    assert 'wall-1' in delivery_html


@pytest.mark.parametrize('perimeter_offset', [0., .2])
def test_stack_saves_effective_drafts_and_full_floor_reports(tmp_path, perimeter_offset):
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    rows = []
    original_drafts = {}
    for index in range(2):
        plan = example()
        if index:
            for point in plan['partitions'][0]['points']:
                point[0] += .2
            for key in ('p1', 'p2'):
                plan['openings'][0][key][0] += .2
            for point in plan['footprint_pixels']:
                if point[0] == 1:
                    point[0] += perimeter_offset
            for key in ('p1', 'p2'):
                plan['openings'][1][key][0] += perimeter_offset
        result = toolkit.build_plan('plan.png', json.dumps(plan))
        assert result['source_geometry_ready'], result
        record = result['plan_input']
        original_drafts[record['plan_file']] = (run / record['plan_file']).read_bytes()
        rows.append(dict(draft_id=record['plan_file'].split('/')[1],
                         expected_plan_sha256=record['plan_sha256'],
                         floor_id=f'L{index+1}', z_floor=index*3., evidence='test level'))
    assembled = toolkit.assemble_plans(json.dumps(rows))
    assert assembled['source_geometry_ready'], assembled
    audit = json.loads((run / assembled['regularization']['file']).read_text())
    assert audit['changes'] and set(audit['floor_reports']) == {'L1', 'L2'}
    source = json.loads((run / assembled['candidate'] / 'source_model.json').read_text())
    html = render_regularization_html(source)
    assert '几何规整清单' in html and '移动' in html
    binding = json.loads((run / assembled['plan_assembly']['file']).read_text())
    assert all((run / row['effective_plan_file']).is_file() for row in binding['floors'])
    assert all((run / name).read_bytes() == payload
               for name, payload in original_drafts.items())
    if perimeter_offset:
        edge_moves = [row for row in audit['changes'] if row['type'] == 'move_footprint_edge']
        assert len(edge_moves) == 1 and edge_moves[0]['floor_id'] == 'L2'
        assert edge_moves[0]['moved_opening_ids'] == ['W1']
        upper = next(row for row in binding['floors'] if row['floor_id'] == 'L2')
        effective = json.loads((run / upper['effective_plan_file']).read_bytes())
        assert min(point[0] for point in effective['footprint_pixels']) == pytest.approx(1)
        window = next(row for row in source['openings'] if row['id'] == 'L2:W1')
        assert all(point[0] == pytest.approx(0) for point in window['vertices'])
        assert len(source['spaces']) == len(source['openings']) == 4
        assert '跨层外轮廓边对齐' in html


def test_generic_build_and_revision_refuse_thin_spaces_without_allocating_candidates(tmp_path):
    run = _run_with_one_image(tmp_path)
    plan = example()
    plan['partitions'][0]['points'] = [[1.5, 1], [1.5, 7]]
    plan['openings'] = []
    plan['space_seeds'] = []
    proposal, _ = compile_plan_partition(plan, image_size=(12, 8), image_name='plan.png')
    before = copy.deepcopy(proposal)
    toolkit = Toolkit(run)
    rejected = toolkit.build(proposal)
    assert rejected['source_geometry_ready'] is False
    assert rejected['regularization']['rejected_count']
    assert rejected['saved_candidate'] is None
    assert proposal == before and not list(run.glob('candidate_*'))
    assert (run / rejected['regularization']['file']).is_file()
    built = toolkit.build(json.loads(_two_room_proposal()))
    assert built['source_geometry_ready'], built
    assert built['saved_candidate'] == 'candidate_01'
    source = run / built['candidate'] / 'source_model.json'
    saved_source = source.read_bytes()
    revised = toolkit.revise(built['candidate'], json.dumps([{
        'op': 'move_shared_wall', 'space_ids': ['left', 'right'], 'coordinate_m': .5,
        'reason': 'exercise hard-width refusal', 'source_refs': ['synthetic test'],
    }]))
    assert revised['source_geometry_ready'] is False
    assert revised['saved_candidate'] is None
    assert revised['claim_application']['status'] == 'failed'
    assert revised['save_effects']['created_candidates'] == []
    assert source.read_bytes() == saved_source
    assert len(list(run.glob('candidate_*'))) == 1


def test_compact_audit_counts_delivered_merges_but_not_rejected_floor_attempts():
    changes = [
        {'type': 'remove_narrow_strip_space_seeds', 'removed_space_seeds': [{'id': 'false-strip'}]},
        {'type': 'merge_overlapping_openings', 'removed_opening_ids': ['duplicate-door']},
    ]
    floor = {'status': 'pass', 'changes': changes, 'rejections': []}
    delivered = summary({'status': 'pass', 'floor_reports': {'F1': floor}})
    assert delivered['removed_strip_seed_count'] == 1
    assert delivered['merged_opening_count'] == 1
    assert delivered['attempted_change_count'] == 0
    refused = summary({'status': 'rejected', 'floor_reports': {'F1': floor},
                       'rejections': [{'type': 'cross_storey_relationship_changed'}]})
    assert refused['moved_count'] == 0
    assert refused['removed_strip_seed_count'] == refused['merged_opening_count'] == 0
    assert refused['attempted_change_count'] == len(changes)
    skipped = summary({
        'status': 'pass',
        'cross_storey_failure_policy': 'skip_failed_pair',
        'skipped_alignments': [{
            'type': 'cross_storey_alignment_skipped',
            'source': {'floor_id': 'F1', 'partition_id': 'A'},
            'target': {'floor_id': 'F2', 'partition_id': 'B'},
            'distance_m': .2,
            'attempted_changes': [{'type': 'move_wall_line'}],
        }],
    })
    assert skipped['status'] == 'pass'
    assert skipped['skipped_alignment_count'] == 1
    assert skipped['cross_storey_failure_policy'] == 'skip_failed_pair'
    assert 'attempted_changes' not in skipped['skipped_alignments'][0]


def test_source_refusal_stays_primary_when_plan_and_stack_prechecks_pass(tmp_path, monkeypatch):
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    rows = []
    for index in range(2):
        built = toolkit.build_plan('plan.png', json.dumps(example()))
        assert built['source_geometry_ready'], built
        record = built['plan_input']
        rows.append(dict(draft_id=record['plan_file'].split('/')[1],
                         expected_plan_sha256=record['plan_sha256'],
                         floor_id=f'F{index + 1}', z_floor=index * 3., evidence='synthetic'))

    monkeypatch.setattr('src.agent.geometry.building_precision.precision_report',
                        lambda source: {'status': 'rejected', 'items': [{
                            'type': 'source_only_violation', 'objects': ['synthetic'],
                            'distance_m': .1, 'fix': 'synthetic later-stage refusal',
                        }]})
    results = [toolkit.build_plan('plan.png', json.dumps(example())),
               toolkit.assemble_plans(json.dumps(rows))]
    for result in results:
        assert result['source_geometry_ready'] is False
        assert result['saved_candidate'] is None
        assert result['error_stage'] == 'source_hard_constraints'
        reference = result['regularization']
        assert reference['status'] == 'rejected'
        audit = json.loads((run / reference['file']).read_text(encoding='utf-8'))
        assert audit['rejections'][0]['type'] == 'source_only_violation'
    assert len(list(run.glob('candidate_*'))) == 2
