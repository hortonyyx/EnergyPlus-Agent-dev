"""Original-only bounded west-corridor door inventory after east recovery."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = """Inventory actual INTERNAL door apertures along the WEST wall of
the CENTRAL CORRIDOR in 1f_view.png. This wall separates the corridor from the
rooms to its left. Scope runs from immediately below the northern full-width
room down to the southern exterior wall. Do not inventory external windows,
the corridor's east wall, or the north full-width room's double door.

Use the original, a clean magnified crop, and view_pixel_profile on the actual
straight corridor wall. Identify its gray wall support and every gap along its
full extent; bind each gap to visible door jambs/arcs and the adjoining room.
If a region contour helps interpret a gap, call view_pixel_region using a seed
inside that room. Profiles do not assign semantics: confirm openings on the
original image. A door swing extends off the wall; the aperture endpoints lie
ON the straight wall, not at the far door-leaf tip. Long continuous supported
wall runs are not doors. Measure original pixel coordinates from tools rather
than rounding guesses from a thumbnail.

Return the FULL ordered list of visible corridor-west door apertures north to
south, each with two pixel jamb endpoints, adjacent-room description, and the
actual support/gap evidence. Also list the principal continuous wall intervals
so an omitted or invented gap can be checked. If any part is obscured, mark it
unexamined rather than claiming completeness. No fixed number of doors is
provided or expected. Do not infer a door solely from room adjacency.
Only pixels and visible room identity; no metre calibration, traces or BIM edits.
Only one original plan and this task are supplied; no old BIM/door counts/GT.
Finish within 120 seconds.
"""

if __name__ == '__main__':
    run = ROOT / 'AI_agent/logs/experiments/2026-09-14_sm24_west_door_observation'
    run.mkdir(exist_ok=False)
    (run / 'images').mkdir()
    source = ROOT / 'AI_agent/logs/experiments/2026-09-13_sm24_northeast_overview/images/1f_view.png'
    shutil.copy2(source, run / 'images/1f_view.png')
    implementations = ['scripts/tool_scripts/run_bim_agent.py',
        'AI_agent/logs/experiments/2026-09-14_east_wall_setup/observe_west_doors.py']
    (run / 'implementation').mkdir()
    for p in implementations:
        shutil.copy2(ROOT / p, run / 'implementation' / Path(p).name)
    dump(run / 'inputs.json', {
        'images': {'1f_view.png': {'size': [790,1111], 'sha256': digest(source)}},
        'input_mode': 'developer_scoped_original_only_west_wall_aperture_inventory',
        'only_input': 'Original plan and west-corridor wall inventory task, no old BIM, expected door count, candidate door pixels, or GT.',
        'implementation_sha256': {p: digest(ROOT / p) for p in implementations},
    })
    child, sha = prepare_detail_observation(Toolkit(run), QUESTION, ['1f_view.png'], 'detail_01', timeout_seconds=120)
    manifest = json.loads((child / 'inputs.json').read_text())
    receipt = subscription(child, 'Images: [1f_view.png]\nQuestion: ' + QUESTION,
        model='haiku', name='detail_01', readonly=True,
        timeout=max(1, manifest['deadline_epoch'] - time.time()), log_run=run,
        receipt_context={'observation_source': {'run': 'detail_01', 'input_sha256': sha}})
    dump(run / 'summary.json', {
        'actual_model': receipt.get('actual_model'), 'elapsed_seconds': receipt['elapsed_seconds'],
        'completed': bool(receipt.get('result')) and not receipt['result'].get('is_error'),
        'estimated_cost_usd': receipt.get('result', {}).get('total_cost_usd'),
        'limits': 'Developer-scoped original-only Haiku inventory, not autonomous whole-building generation. CLI estimate is not a bill.',
    })
    print((run / 'summary.json').read_text())
