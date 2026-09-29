"""Post-generation original-drawing interpretation and complete run89 accounting."""
from .audit_run import completed
from .batch import HERE, ROOT, RUN, load, save, sha


def main():
    summary, receipt = completed()
    report, behavior = load(RUN / 'postrun_audit.json'), load(RUN / 'behavior_audit.json')
    source, seed = (load(RUN / path / 'source_model.json') for path in ['candidate_01', 'seed'])
    current, before = ({o['id']: o for o in s['openings']} for s in [source, seed])
    assert all(source[k] == seed[k] for k in ['floors', 'spaces', 'boundaries', 'connections'])
    assert set(current) == set(before)
    changed = [key for key in current if current[key] != before[key]]
    assert len(changed) == 15 and all(current[key]['kind'] == 'window' for key in changed)
    for key in current:
        assert {k:v for k,v in current[key].items() if k != 'vertices'} == {k:v for k,v in before[key].items() if k != 'vertices'}
        assert all(p[:2] == q[:2] for p,q in zip(current[key]['vertices'], before[key]['vertices']))
    heights = []
    for key in changed:
        actual = [min(p[2] for p in current[key]['vertices']), max(p[2] for p in current[key]['vertices'])]
        expected = ([4.0, 5.8] if key.startswith('F2:') else [1.5, 2.1] if key == 'F1:W4'
                    else [1.0, 2.8] if key == 'F1:W7' else [1.0, 2.6])
        heights.append(dict(id=key, actual_z_m=actual, original_nominal_z_m=expected,
                            delta_m=[a-b for a,b in zip(actual,expected)]))
    wrong = [r['id'] for r in heights if any(abs(d) > 1e-6 for d in r['delta_m'])]
    assert wrong == ['F1:W7']
    assert behavior['counts'] == dict(tool_calls=55, errors=7, original_returns=26,
                                     elevation_returns=5, paired_returns=5, calibrated_returns=5)
    assert all(r['candidate'] == 'seed' for r in behavior['elevation_transport'])
    assert report['exterior_parameters_match'] == 17 and not report['height_mismatches']
    identity = load(RUN / 'room_identity_audit.json')
    assert identity['hosts_with_distinct_reference_room_identity'] == 29
    assert identity['connections_with_distinct_reference_room_identity'] == 14
    assert not identity['reference_room_collisions'] and not identity['unresolved_reference_room_seeds']
    assert not report['space_identity_findings']
    behavior['semantic_review'] = 'manual_review.json'
    save(RUN / 'behavior_audit.json', behavior)
    preservation = dict(floors=2, spaces=14, boundaries=84, connections=14,
        unchanged_doors=14, changed_windows=15, changed_physical_fields='window vertices z only',
        all_29_opening_xy_and_hosts_unchanged=True, all_other_opening_fields_unchanged=True)
    manual = dict(reviewer='development assistant after generation, not working-model feedback',
        source_model_sha256=source['source_model_sha256'], generation_complete=True,
        complete_quality_restored=False, stable_generation_established=False,
        physical_preservation=preservation, original_window_height_review=heights,
        findings=[
            dict(object='F1:W7', status='wrong_height_family_applied_again', old_z_m=[1.007368421,2.605263158],
                actual_z_m=[1.0,2.6], original_expected_z_m=[1.0,2.8], head_shortfall_m=0.2,
                evidence='East lower dimension chain: 1000/1800/200mm. Orange source head is visibly below cyan original head in the actual returned seed overlay.',
                observed_behavior='East calibrated overlay call42 exposed the old mismatch. Claim0001/call44 instead cites the full North view and incorrectly states East shares its 400/1600/1000mm chain; adopted call47 and applied call52.',
                old_parameter_tolerance_pass=True),
            dict(scope='post-revision review', status='no_final_elevation_recheck',
                evidence='All five calibrated elevation calls used seed. After revision52, only height-coverage check53, failed note edit54 and finish55 followed; final text says all matched although no final elevation was returned.'),
            dict(scope='height coverage', status='linked_does_not_mean_semantically_correct',
                evidence='Three claims link all15 windows, including the wrong East window. Claim0001/0002 cite North full view; claim0003 cites South. No claim cites East.'),
            dict(scope='calibration', status='caller_selected_and_unverified',
                evidence='West first scale was visibly wrong and warned; caller changed the outer-wall frame. Final East overall height/base anchors match the original and expose an11px residual. North/West positive horizontal frames have symmetric aperture layouts, which cannot independently establish object direction/identity.'),
            dict(scope='partition', status='unchanged_old_wall_position_offsets',
                evidence='14 space identities and all physical partitions/connections remain exact to seed. Strict2cm partition score stayssevere because of inherited F2 wall offsets about2.2-5.2cm; no new split/merge/missing-space finding.'),
            dict(scope='tool errors', status='seven_errors_retained',
                evidence='Two invented image names; two space-relation calls before calibration; missing confirm reason; confirmation differs from stored small pixel-offset heights; exact-note replacement fails because the old text is duplicated. Failed actions are not counted as successful checks.'),
            dict(scope='unlinked heights', status='14_doors_not_currently_image_linked',
                evidence='All14 door geometries remain unchanged. Their current height-evidence gaps, documented simplifications and unrecorded role_evidence remain; this is not a new missing-opening or room-type failure.'),
        ],
        result_interpretation='Calibrated feedback was actually adopted and transported exactly, but did not repair the known semantic error. It cannot establish quality recovery or causality; save-state/task/CLI conditions differ from prior runs.',
        next_offline_scope='Replay the explicit North-image evidence to East-source-window mapping error and the missing final-object recheck. Test scope/object correspondence and visible projection residuals before choosing a production constraint; do not add another generic reminder or repeat the same batch blindly.',
        evaluation_overlay='evaluation/final_east_overlay.png',
        evaluation_overlay_limit='Developer-only projection of the final source using the model\'s saved East anchors; never returned to the working model.',
        evidence_sha256={str(p.relative_to(RUN)):sha(p) for p in [
            RUN/'agent_receipt.json', RUN/'experiment_condition.json', RUN/'candidate_01/source_model.json',
            RUN/'candidate_01/operations.json', RUN/'image_overlays/overlay_007.png',
            RUN/'images/East_view.png', RUN/'claims/claim_0001.json', RUN/'source_changes.json',
            RUN/'behavior_audit.json', RUN/'postrun_audit.json', RUN/'room_identity_audit.json',
            RUN/'browser_qa/report.json', RUN/'evaluation/claim_transport_audit.json',
            RUN/'evaluation/final_east_overlay.json', RUN/'evaluation/final_east_overlay.png']})
    save(RUN/'manual_review.json', manual)
    delivery = load(RUN/'delivery.json')
    save(RUN/'comparison_metrics.json', dict(candidate=report['candidate'], counts=report['counts'],
        original_openings=report['original_openings'], height_coverage=delivery['height_coverage']['summary'],
        old_tolerance_exterior_matches=17, old_tolerance_exterior_total=17,
        unresolved_semantic_height_errors=wrong, complete_quality_restored=False,
        actual_mode='saved_candidate_recovery', strict_partition_status=report['strict_partition_status'],
        physical_geometry_preservation=preservation, calibrated_tool_returns=5,
        audit_model_calls=0, manual_review_sha256=sha(RUN/'manual_review.json')))
    save(HERE/'execution_receipt.json', dict(completed=True, primary_invocations=1, local_model_invocations=0,
        actual_model=receipt['actual_model'], effort='medium', elapsed_seconds=summary['elapsed_seconds'],
        candidates=1, estimated_usd_not_bill=summary['estimated_cost_usd'],
        usage=receipt['result']['usage'], model_usage=receipt['result']['modelUsage'],
        automatic_retry=False, continuation_rounds=0, paid_api_or_fallback=False,
        receipt_sha256=sha(RUN/'agent_receipt.json')))
    config = load(HERE.parent/'2026-09-28_paired_elevation_review/quality_runs.json')
    assert len(config['runs']) == 29
    config['scope'] = '30 saved records, including run89 calibrated-elevation saved-proposal review. All prior failures and interrupted/unknown outcomes preserved; no pooled success rate or baseline adoption.'
    config['runs'].append(dict(case='sm21', condition='原立面显式标定叠图（保存稿复核）', run=str(RUN.relative_to(ROOT)),
        feature_count=dict(file='behavior_audit.json',path=['counts','calibrated_returns'],name='calibrated_elevation_returns'),
        notes=['五次叠图确实送达但东窗仍错高0.2m；15窗改整值，其他源物理几何保持。',
               '原图位置/宿主29/29、连接14/14；旧宽容差17/17与15条高度绑定均不代替语义正确。',
               '单Sonnet5/medium保存稿任务，CLI更新/任务/工具条件有变化；未恢复质量，不宣称冷启动或稳定。']))
    save(HERE/'quality_runs.json', config)
    save(HERE/'postrun_verification.json', dict(status='complete', model_calls=1, audit_model_calls=0,
        reused_targeted_checks=31, producer_and_43_frozen_execution_files_verified=True,
        real_original_and_elevation_transport_verified=True, offline_browser='pass',
        generation_outcome='height_rounding_only_east_window_still_wrong', stable_quality=False,
        pending_new_batch=False, manual_review_sha256=sha(RUN/'manual_review.json')))
    save(HERE/'batch_status.json', dict(state='closed', completed=True, user_approval='发',
        run=RUN.name, actual_model=receipt['actual_model'], primary_invocations=1,
        automatic_retry=False, additional_batch_approved=False, complete_quality_restored=False))
    print(dict(completed=True, source_hash=source['source_model_sha256'], changed_windows=15,
               remaining_error='F1:W7', head_shortfall_m=0.2, historical_records=30))


if __name__ == '__main__':
    main()
