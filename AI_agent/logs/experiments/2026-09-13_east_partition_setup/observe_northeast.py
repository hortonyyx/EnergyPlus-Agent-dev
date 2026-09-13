"""Image-only Haiku room trace; developer selects scope, no candidate or GT."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = """From 1f_view.png, trace ONE complete room: the small northeastern
room directly below the large full-width room at the top of the building. It
contains a narrow cabinet, is east of the corridor, and has a larger room with
two tables directly below it. Do not trace the full-width room or furniture.
You have only the original image, no saved BIM or target coordinates.
Use view_pixel_region from your own chosen background seed to locate this room
if useful. It is a pixel candidate, not automatically a physical boundary;
door symbols and furniture must be interpreted. Identify the complete room's
four boundary segments and its actual doorway jambs on the corridor wall.
Call preview_space_trace EARLY with the ordered ORIGINAL-pixel room polygon,
and the aperture's two jamb endpoints (not swung-leaf tips). State a consistent
representative wall-line basis, distinguishing internal lines and outer faces.
For world coordinates use the building southwest footprint origin, x east/y
north; choose your own two [original_pixel,metres] anchors for each axis from
the actual outside walls and overall marked dimensions. Dimension lines are
offset from the wall; their location is not itself a footprint endpoint.
Inspect the clean/marked preview, correct only what the image supports, then
select_space_trace. Focus on the correct room/host and complete contour; do not
read the whole drawing, inventory other rooms or write long prose. Submit a
preview within 60 seconds and finish within 120 seconds. Unknowns stay explicit.
"""

if __name__ == '__main__':
    run = ROOT/'AI_agent/logs/experiments/2026-09-13_sm24_northeast_trace'
    run.mkdir(exist_ok=False)
    (run/'images').mkdir()
    source = ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run04/images/1f_view.png'
    shutil.copy2(source, run/'images/1f_view.png')
    dump(run/'inputs.json', {'images': {'1f_view.png': {'size':[790,1111], 'sha256':digest(source)}},
         'input_mode':'developer_scoped_original_image_observation',
         'only_input':'One original plan and the developer-selected room description; no seed, old observations or GT.'})
    child, sha = prepare_detail_observation(Toolkit(run), QUESTION, ['1f_view.png'], 'detail_01', timeout_seconds=120)
    manifest = json.loads((child/'inputs.json').read_text())
    receipt = subscription(child, 'Images: [1f_view.png]\nQuestion: '+QUESTION,
        model='haiku', name='detail_01', readonly=True,
        timeout=max(1, manifest['deadline_epoch']-time.time()), log_run=run,
        receipt_context={'observation_source':{'run':'detail_01','input_sha256':sha,
            'images':{'1f_view.png':digest(source)}}})
    dump(run/'summary.json', {'actual_model':receipt.get('actual_model'),
         'elapsed_seconds':receipt['elapsed_seconds'], 'completed':bool(receipt.get('result')) and not receipt['result'].get('is_error'),
         'selected_trace': json.loads((child/'trace_selection.json').read_text()) if (child/'trace_selection.json').exists() else None,
         'estimated_cost_usd':receipt.get('result',{}).get('total_cost_usd'),
         'limits':'CLI estimate is not a bill; trace selection does not certify image fidelity or change the source BIM.'})
    print((run/'summary.json').read_text())
