"""Continue verified region localization with a bounded physical-wall observation."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = """Continue ONE local original-plan observation: identify the physical
boundaries and corridor doors of the two east-side rooms immediately below the
full-width northern room. Prior Haiku localization selected overview R21 with
seed [511,347] for the small cabinet room, and R06 seed [495,482] for the larger
room with two tables below. Those are image-region locations ONLY, not physical
wall coordinates. Verify their surroundings on the original; do not select the
full-width northern room or a furniture box.

Observe these two rooms using a single drawing coordinate frame: world origin
at the building's southwest exterior corner, +x east and +y north. Determine the
overall dimensions and their exterior endpoint pixels directly from the plan.
Use clean magnified crops and pixel tools as useful. Distinguish the outer face
for exterior boundaries from a declared representative line for internal walls;
do not map the exterior overall dimension onto an interior wall face. Compare
the right-hand dimension chain to the actual corresponding horizontal walls;
do not confuse window endpoints with room divisions.

Preview TWO complete room traces, one for the small room and one for the two-table
room, using the same x/y calibration and explicit reference-plane explanation.
Include each room's actual corridor doorway jamb endpoints on its west wall,
not the far tip of the swinging door leaf. Keep a straight representative wall
through the doorway; do not turn an arc into a room corner. Include the visible
east window in each trace if its extent is clear. View both actual saved trace
images. Report the final trace ID for EACH room and the evidence for their
shared wall, larger room's south wall, and two corridor doors. You may select
the last trace, but state both final IDs in your answer. Do not edit any BIM.

The only supplied old information is the prior region localization quoted
above. No source BIM, metre coordinates, GT or previous wall/door reading is
available. Mark uncertainty honestly; geometric execution is not image truth.
Finish within 180 seconds and leave time to give final trace IDs.
"""

if __name__ == '__main__':
    run = ROOT / 'AI_agent/logs/experiments/2026-09-14_sm24_east_wall_observation'
    run.mkdir(exist_ok=False)
    (run / 'images').mkdir()
    source = ROOT / 'AI_agent/logs/experiments/2026-09-13_sm24_northeast_overview/images/1f_view.png'
    shutil.copy2(source, run / 'images/1f_view.png')
    implementations = ['scripts/tool_scripts/run_bim_agent.py',
                       'src/agent/geometry/space_trace.py',
                       'AI_agent/logs/experiments/2026-09-14_east_wall_setup/observe.py']
    (run / 'implementation').mkdir()
    for path in implementations:
        shutil.copy2(ROOT / path, run / 'implementation' / Path(path).name)
    dump(run / 'inputs.json', {
        'images': {'1f_view.png': {'size': [790,1111], 'sha256': digest(source)}},
        'input_mode': 'developer_scoped_continuation_of_model_region_localization',
        'only_input': 'One original plan plus prior Haiku region IDs/seeds and developer task; no BIM, prior wall geometry or GT.',
        'implementation_sha256': {p: digest(ROOT / p) for p in implementations},
    })
    child, sha = prepare_detail_observation(Toolkit(run), QUESTION, ['1f_view.png'], 'detail_01', timeout_seconds=180)
    manifest = json.loads((child / 'inputs.json').read_text())
    receipt = subscription(child, 'Images: [1f_view.png]\nQuestion: ' + QUESTION,
        model='sonnet', effort='low', name='detail_01', readonly=True,
        timeout=max(1, manifest['deadline_epoch'] - time.time()), log_run=run,
        receipt_context={'observation_source': {'run': 'detail_01', 'input_sha256': sha,
            'images': {'1f_view.png': digest(source)}}})
    dump(run / 'summary.json', {
        'actual_model': receipt.get('actual_model'), 'elapsed_seconds': receipt['elapsed_seconds'],
        'completed': bool(receipt.get('result')) and not receipt['result'].get('is_error'),
        'estimated_cost_usd': receipt.get('result', {}).get('total_cost_usd'),
        'limits': 'Developer-scoped Sonnet observation with previous Haiku localization; not autonomous generation. CLI estimate is not a bill.',
    })
    print((run / 'summary.json').read_text())
