"""Reuse the frozen original-image evaluation after the self-selected review."""
import argparse
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path

from PIL import Image
from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent


def audit(run):
    assert (run/'summary.json').exists(), 'Wait for the complete model invocation'
    prior_audit = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_wall_context_setup.audit_recovery')
    prior_audit.audit(run)
    load = lambda name: json.loads((run/name).read_text())
    raw = load('postrun_audit.json')
    raw['limits'] = [s for s in raw['limits'] if not s.startswith('Developer-targeted saved-plan')]
    raw['limits'].append('Discrepancy targets were model-selected within saved-plan recovery; not a cold start or repeated stability test.')
    dump(run/'postrun_audit.json', raw)
    finalize = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run')
    finalize.finalize(run)
    manifest, receipt = load('inputs.json'), load('agent_receipt.json')
    frozen = json.loads((HERE/'frozen_method.json').read_text())
    assert digest(run/'images/1f_view.png') == frozen['image_sha256']
    assert digest(run/'resume_plan.json') == frozen['plan_sha256']
    assert manifest['scope'] == frozen['scope']
    assert receipt['actual_model'] == 'glm-5.3-flash'
    assert list(receipt['result']['modelUsage']) == ['glm-5.3-flash']
    rows = [json.loads(s) for s in (run/'tools.jsonl').read_text().splitlines()]
    trace = []
    for row in rows:
        data = row['data']
        if row['action'] in {'view_image', 'view_pixel_profile', 'pixel_profile', 'build_plan_bim', 'revise_bim', 'finish_bim'}:
            trace.append(dict(action=row['action'],
                seconds_from_first_tool=round(row['time']-rows[0]['time'], 2),
                box=data.get('box_original_pixels', data.get('box')),
                candidate=data.get('candidate'), counts=data.get('counts'), error=data.get('error')))
    dump(run/'evaluation/observation_and_edit_trace.json', dict(
        note='Actual model-chosen tool sequence, not an independent semantic correctness verdict.', trace=trace))
    image_calls = [r for r in load('transport_audit.json')['images'] if r['tool'].endswith('__overlay_candidate')]
    overlay_logs = [r['data'] for r in rows if r['action']=='overlay_candidate']
    assert len(image_calls)==len(overlay_logs)
    crops = []
    for actual, meta in zip(image_calls, overlay_logs):
        with Image.open(run/meta['overlay_image']) as im:
            im = im.convert('RGB')
            if meta.get('box_original_pixels'):
                im = im.crop(meta['box_original_pixels'])
            im.thumbnail((1600, 1600))
            assert hashlib.sha256(im.tobytes()).hexdigest()==actual['pixels_sha256']
        crops.append(dict(overlay=meta['overlay_image'], box=meta.get('box_original_pixels'),
                          returned_rgb_exact=True))
    diagnostic = load('evaluation/declared_frame_diagnostic.json')
    previous = json.loads((HERE.parent/'2026-09-23_sm24_wall_context_recovery_glm_run35/evaluation/declared_frame_diagnostic.json').read_text())
    def compact(d):
        return dict(candidate=d['candidate'], partition_status=d['comparison']['status'],
            spaces=d['comparison']['candidate_count'], matched_spaces=d['comparison']['matched_count'],
            positions_matched=d['positions_matched'], hosts_matched=d['hosts_matched'],
            door_connections_matched=d['door_connections_matched'],
            changed_opening_geometry=d['changed_opening_geometry'], removed_openings=d['removed_openings'])
    dump(run/'evaluation/review_comparison.json', dict(
        input_mode='self_selected_review_of_imported_failure_not_cold_start',
        generation_scope=manifest['scope'], frozen_input_hashes_verified=True,
        previous_targeted_run=compact(previous), current_self_selected_run=compact(diagnostic),
        actual_model=receipt['actual_model'], elapsed_seconds=receipt['elapsed_seconds'],
        cli_estimated_usd_not_bill=receipt['result']['total_cost_usd'],
        tool_counts=dict(Counter(r['action'] for r in rows)), actual_overlay_crops=crops,
        limitations=['Same failed draft may itself contain uncertainty clues; only external location hints were removed.',
                     'Budget differs, observations are stochastic; not a one-variable causal test.',
                     'All heights and inherited coordinate convention remain outside this bounded review.']))
    print(json.dumps(compact(diagnostic), indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    audit(parser.parse_args().run.resolve())
