"""Bounded coordinator interpretation of actual worker measurements."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = """Resolve reference planes for TWO measured east-side rooms, then
preview their corrected complete contours and corridor doors. Do not re-read
the whole building. The small cabinet room is immediately north of the larger
two-table room; previous Haiku localized them and measured contours and wall
support. Its complete unmodified data is quoted below. No BIM or GT is supplied.

Development review found a REPRESENTATION conflict: Haiku traced room-interior
wall faces and called them representative/exterior walls. Its two polygons
leave a gap at their shared horizontal wall, and its east trace is not the
exterior face used by the overall dimension anchors. Use the original and
worker measurements to resolve this. Keep one declared representative line
per INTERNAL physical wall, shared by both rooms; use the actual EXTERIOR face
for the east perimeter. Do not discard valid measured door jambs while fixing
which wall line they lie on. Door endpoints are projected across wall thickness
to the chosen representative line, not guessed at the swinging leaf tip.

Use view_pixel_profile for a SHORT local scan if a needed opposite face or
exterior limit was not measured. Inspect magnified clean original crops as
needed. Original-pixel measurements, not thumbnail positions, determine points.
Check the right-side main vertical dimension chain against the horizontal
room walls as a scale cross-check; distinguish that chain from window spans.
The worker inherited an unverified exterior calibration hypothesis. Verify
its original endpoints and reuse or correct with evidence; use a single frame
for both rooms, origin southwest exterior, +x east, +y north.

Call preview_space_trace for BOTH final rooms, each with its corridor door.
The two final traces must share exactly the same physical-wall representative
coordinate and same x/y calibration. Look at the preview images and select the
second, then report both final trace IDs and remaining uncertainty. Do not
rewrite or fit any source building. Finish within 150 seconds.

UNMODIFIED WORKER MEASUREMENTS (region polygons can follow arcs/furniture;
profile supports are pixels, not automatic walls):
"""

if __name__ == '__main__':
    run = ROOT / 'AI_agent/logs/experiments/2026-09-14_sm24_east_reference_review'
    worker = ROOT / 'AI_agent/logs/experiments/2026-09-14_sm24_east_measured_observation/detail_01'
    assert (worker.parent / 'summary.json').exists()
    files = [*sorted((worker / 'pixel_regions').glob('*.json')),
             *sorted((worker / 'pixel_profiles').glob('*.json')),
             *sorted((worker / 'space_traces').glob('*.json'))]
    evidence = {str(p.relative_to(worker)): json.loads(p.read_text()) for p in files}
    question = QUESTION + json.dumps(evidence, ensure_ascii=False)
    run.mkdir(exist_ok=False)
    shutil.copytree(worker / 'images', run / 'images')
    implementations = ['scripts/tool_scripts/run_bim_agent.py', 'src/agent/geometry/space_trace.py',
        'AI_agent/logs/experiments/2026-09-14_east_wall_setup/review_measured.py']
    (run / 'implementation').mkdir()
    for p in implementations:
        shutil.copy2(ROOT / p, run / 'implementation' / Path(p).name)
    dump(run / 'inputs.json', {
        'images': json.loads((worker / 'inputs.json').read_text())['images'],
        'input_mode': 'developer_scoped_coordinator_review_of_worker_measurements',
        'only_input': 'Original plan, unmodified Haiku region/profile/trace measurements, and explicit developer reference-plane conflict feedback. No BIM or GT.',
        'worker_evidence_sha256': {str(p.relative_to(ROOT)): digest(p) for p in files},
        'implementation_sha256': {p: digest(ROOT / p) for p in implementations},
    })
    child, sha = prepare_detail_observation(Toolkit(run), question, ['1f_view.png'], 'detail_01', timeout_seconds=150)
    manifest = json.loads((child / 'inputs.json').read_text())
    receipt = subscription(child, 'Images: [1f_view.png]\nQuestion: ' + question,
        model='sonnet', effort='low', name='detail_01', readonly=True,
        timeout=max(1, manifest['deadline_epoch'] - time.time()), log_run=run,
        receipt_context={'observation_source': {'run': 'detail_01', 'input_sha256': sha,
            'worker_evidence_sha256': json.loads((run / 'inputs.json').read_text())['worker_evidence_sha256']}})
    dump(run / 'summary.json', {
        'actual_model': receipt.get('actual_model'), 'elapsed_seconds': receipt['elapsed_seconds'],
        'completed': bool(receipt.get('result')) and not receipt['result'].get('is_error'),
        'estimated_cost_usd': receipt.get('result', {}).get('total_cost_usd'),
        'limits': 'Developer-orchestrated Sonnet conflict review of Haiku measurement; not autonomous delegation or cold start. CLI estimate is not a bill.',
    })
    print((run / 'summary.json').read_text())
