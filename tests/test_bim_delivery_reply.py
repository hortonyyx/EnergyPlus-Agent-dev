"""Large height/review evidence must leave a readable completion summary."""
import copy
import json

from scripts.tool_scripts.run_bim_agent import delivery_tool_reply
from tests.test_bim_claims import setup_run


def test_large_nested_evidence_keeps_actionable_status_under_transport_budget(tmp_path):
    _, toolkit = setup_run(tmp_path)
    report = toolkit.delivery("seed", selection_origin="agent_selected")
    report['current_claim_state']['claims'] = [{
        'id': 'claim_0001', 'state': 'partially_satisfied', 'missing_bindings': ['door.z'],
        'retained_bindings': [{'object': 'window', 'evidence': 'measured'}] * 800,
    }]
    report['source_image_feedback']['current_source_projections'] = [
        {'image': 'plan.png', 'geometry': list(range(4000))}]
    before = copy.deepcopy(report)
    reply = delivery_tool_reply(report)
    assert len(json.dumps(reply, ensure_ascii=False, indent=2)) <= 18000
    assert reply['response_compacted'] is True
    assert reply['current_claim_summary']['state_counts'] == {'partially_satisfied': 1}
    assert reply['current_claim_summary']['claims_with_missing_bindings'] == ['claim_0001']
    assert reply['height_coverage']['summary']['unchecked_height_opening_ids'] == ['door', 'window']
    assert reply['source_image_feedback_summary']['current_source_projections_count'] == 1
    assert reply['full_delivery_report'] == 'delivery.json'
    assert reply['drawing_fidelity'] == 'not_evaluated'
    assert report == before


def test_extreme_notes_fall_back_to_counts_without_hiding_unresolved_failures(tmp_path):
    _, toolkit = setup_run(tmp_path)
    report = toolkit.delivery("seed", selection_origin="agent_selected",
                              generation_status={'state': 'interrupted', 'error': 'x' * 30000})
    report['assumptions'] = ['large note ' * 6000]
    report['generation']['unresolved'] = ['still needs review']
    report['claim_applications'] = [{'id': 'app_1', 'status': 'failed', 'error': 'x' * 30000}]
    report['adopted_unapplied_claims'] = ['claim_1']
    before = copy.deepcopy(report)
    reply = delivery_tool_reply(report)
    assert len(json.dumps(reply, ensure_ascii=False, indent=2)) <= 18000
    assert reply['detail_level'] == 'counts_only'
    assert reply['generation_state'] == 'interrupted'
    assert reply['failed_claim_application_count'] == 1
    assert reply['adopted_unapplied_claim_count'] == 1
    assert reply['assumption_count'] == reply['unresolved_count'] == 1
    assert reply['height_coverage']['unchecked_count'] == 2
    assert reply['drawing_fidelity'] == 'not_evaluated'
    assert report == before
