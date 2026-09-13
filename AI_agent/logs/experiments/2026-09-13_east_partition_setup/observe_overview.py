"""Single-capability Haiku localization probe using numbered image regions."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = """Locate ONE requested room in 1f_view.png: the small northeastern
room directly below the large full-width room at the top of the building. It
contains a narrow cabinet, is east of the corridor, and has a larger room with
two tables directly below it. Do not choose the full-width top room or furniture.
This probe tests ONLY target localization, not a whole room trace or BIM editing.
FIRST call view_pixel_region_overview on the entire plan, choosing the drawing
background color yourself. Inspect the clean/numbered whole-image panels, compare
the spatial relationships, and select the candidate belonging to the requested
room. Use that returned candidate's seed_pixel in view_pixel_region to inspect
the actual selected region and original surroundings. If wrong, select another
overview candidate. Do not invent seeds, crop coordinates or metre coordinates.
Report the final overview candidate ID, exact returned seed and bounding box,
and briefly explain the visible neighboring rooms/walls that support your choice.
If no candidate fits, report that honestly; image regions are not room labels.
There is no saved BIM, prior observation, correct region ID, supplied geometry
or GT. Leave unexamined wall/door/scale questions explicit. Finish within 90 seconds.
"""

if __name__ == '__main__':
    run = ROOT/'AI_agent/logs/experiments/2026-09-13_sm24_northeast_overview'
    run.mkdir(exist_ok=False)
    (run/'images').mkdir()
    source = ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run04/images/1f_view.png'
    shutil.copy2(source, run/'images/1f_view.png')
    implementations = ['scripts/tool_scripts/run_bim_agent.py', 'src/agent/geometry/pixel_region.py',
                       'src/agent/geometry/pixel_region_overview.py']
    (run/'implementation').mkdir()
    for path in implementations:
        shutil.copy2(ROOT/path, run/'implementation'/Path(path).name)
    dump(run/'inputs.json', {'images': {'1f_view.png': {'size':[790,1111], 'sha256':digest(source)}},
         'input_mode':'developer_scoped_original_image_localization',
         'only_input':'One original plan, target-room description, and request to use a numbered overview; no seed, observations or GT.',
         'implementation_sha256':{p:digest(ROOT/p) for p in implementations}})
    child, sha = prepare_detail_observation(Toolkit(run), QUESTION, ['1f_view.png'], 'detail_01', timeout_seconds=90)
    manifest = json.loads((child/'inputs.json').read_text())
    receipt = subscription(child, 'Images: [1f_view.png]\nQuestion: '+QUESTION,
        model='haiku', name='detail_01', readonly=True,
        timeout=max(1, manifest['deadline_epoch']-time.time()), log_run=run,
        receipt_context={'observation_source':{'run':'detail_01','input_sha256':sha,
            'images':{'1f_view.png':digest(source)}}})
    dump(run/'summary.json', {'actual_model':receipt.get('actual_model'),
         'elapsed_seconds':receipt['elapsed_seconds'], 'completed':bool(receipt.get('result')) and not receipt['result'].get('is_error'),
         'estimated_cost_usd':receipt.get('result',{}).get('total_cost_usd'),
         'limits':'Localization-only developer-directed probe; no BIM change or full reading. CLI estimate is not a bill.'})
    print((run/'summary.json').read_text())
