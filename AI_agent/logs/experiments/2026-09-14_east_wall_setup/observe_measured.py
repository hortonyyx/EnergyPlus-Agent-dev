"""Separate measured contour interpretation from visual coordinate guessing."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = """Measure the same two located east-side rooms in 1f_view.png, using
returned pixel measurements, not estimates from a displayed thumbnail. R21 seed
[511,347] is the small cabinet room below the northern full-width room; R06 seed
[495,482] is its southern neighbor with two tables. These seeds are a previous
Haiku localization result; neither is a supplied physical boundary.

First call view_pixel_region for BOTH exact seeds with background black and
inspect its returned outer_polygon_pixels, original-pixel bbox and clean/marked
panels. Those measured contours follow the inside of walls and door swings.
Use their long straight runs to locate wall bands and their departures/returns
at the west wall to locate the door jambs. Verify the physical wall band with
view_pixel_profile or a magnified clean crop. Door arcs bend into the room;
the aperture is the interval between jambs ON the straight west wall. Do not
replace a measured coordinate with a rounded visual guess. The contours/bbox
are image evidence, not final room polygons: bridge the door swing using the
actual wall line, and use one representative line per internal wall.

Preview two complete room traces in the SAME coordinate frame. Each includes
only its corridor door (window geometry is outside this small task). Exterior
east boundary must use the exterior face. Internal shared wall must use the
same representative line in BOTH traces, justified by the physical wall band.
For calibration, previous independent Sonnet observed 10m x 20m exterior
overall dimensions and anchors x=[[248,0],[612,10]], y=[[880,0],[150,20]].
These are unverified hypotheses: check the actual overall endpoints with clean
crops, reuse or correct them with evidence. No source BIM or GT is supplied.
Use pixel scans for precision if helpful; arithmetic goes to map_pixels/trace.

View both saved trace images and finish with their exact IDs, measured wall-band
positions, door-jamb intervals, and remaining uncertainty. select_space_trace
may select the second trace; report both. No BIM edits. Budget 180 seconds.
"""

if __name__ == '__main__':
    run = ROOT / 'AI_agent/logs/experiments/2026-09-14_sm24_east_measured_observation'
    run.mkdir(exist_ok=False)
    (run / 'images').mkdir()
    source = ROOT / 'AI_agent/logs/experiments/2026-09-13_sm24_northeast_overview/images/1f_view.png'
    shutil.copy2(source, run / 'images/1f_view.png')
    implementations = ['scripts/tool_scripts/run_bim_agent.py', 'src/agent/geometry/space_trace.py',
        'src/agent/geometry/pixel_region.py',
        'AI_agent/logs/experiments/2026-09-14_east_wall_setup/observe_measured.py']
    (run / 'implementation').mkdir()
    for p in implementations:
        shutil.copy2(ROOT / p, run / 'implementation' / Path(p).name)
    dump(run / 'inputs.json', {
        'images': {'1f_view.png': {'size': [790,1111], 'sha256': digest(source)}},
        'input_mode': 'developer_constrained_measured_contour_interpretation',
        'only_input': 'Original plan, previous Haiku seeds, prior Sonnet calibration hypothesis, and developer measurement procedure; no BIM or GT.',
        'implementation_sha256': {p: digest(ROOT / p) for p in implementations},
    })
    child, sha = prepare_detail_observation(Toolkit(run), QUESTION, ['1f_view.png'], 'detail_01', timeout_seconds=180)
    manifest = json.loads((child / 'inputs.json').read_text())
    receipt = subscription(child, 'Images: [1f_view.png]\nQuestion: ' + QUESTION,
        model='haiku', name='detail_01', readonly=True,
        timeout=max(1, manifest['deadline_epoch'] - time.time()), log_run=run,
        receipt_context={'observation_source': {'run': 'detail_01', 'input_sha256': sha,
            'images': {'1f_view.png': digest(source)}}})
    dump(run / 'summary.json', {
        'actual_model': receipt.get('actual_model'), 'elapsed_seconds': receipt['elapsed_seconds'],
        'completed': bool(receipt.get('result')) and not receipt['result'].get('is_error'),
        'estimated_cost_usd': receipt.get('result', {}).get('total_cost_usd'),
        'limits': 'Developer-constrained Haiku measurement continuation, not cold start or a controlled model comparison. CLI estimate is not a bill.',
    })
    print((run / 'summary.json').read_text())
