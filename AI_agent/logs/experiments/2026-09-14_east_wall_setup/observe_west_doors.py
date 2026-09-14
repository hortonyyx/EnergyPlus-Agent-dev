"""Original-only bounded west-corridor door inventory after east recovery."""
import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-source-wall-hint', action='store_true')
    args = parser.parse_args()
    question = QUESTION
    hint = None
    if args.with_source_wall_hint:
        seed = ROOT / 'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run11/candidate_01/proposal.json'
        trace_path = seed.parent.parent / 'trace_a.json'
        proposal = json.loads(seed.read_text())
        frame = json.loads(trace_path.read_text())
        cell = next(c for f in proposal['geometry']['floors'] for c in f['cells'] if c['id'] == 'Office1')
        def pixel(value, anchors):
            (p0,w0),(p1,w1) = anchors
            return p0 + (value-w0)*(p1-p0)/(w1-w0)
        hint = {'source_proposal': str(seed.relative_to(ROOT)), 'source_sha256': digest(seed),
                'frame_trace': str(trace_path.relative_to(ROOT)), 'frame_sha256': digest(trace_path),
                'suspected_wall_endpoints_original_pixels': [
                    [pixel(cell['x'][1], frame['x_anchors']), pixel(cell['y'][1], frame['y_anchors'])],
                    [pixel(cell['x'][1], frame['x_anchors']), pixel(proposal['geometry']['footprint_y'][0], frame['y_anchors'])]],
                'origin': 'Developer selected existing source Office1 east wall and extended its line south; code inversely projects source coordinates. Not an independently verified wall.'}
        question = ('SOURCE-BASED LOCATION HYPOTHESIS: ' + json.dumps(hint) +
            '\nThe requested internal partition is near this projected segment, not the western exterior wall. '
            'Verify it on the original, then first use an x-axis gray-wall pixel profile in a narrow strip '
            'around this line along its full length. Its support intervals locate gaps. No door coordinates '
            'or expected count are provided. Check all visible gaps in clean crops and report the final '
            'north-to-south door jamb coordinates early. Budget 90 seconds.\n' + QUESTION)
    run = ROOT / ('AI_agent/logs/experiments/2026-09-14_sm24_west_door_projected_observation'
                  if args.with_source_wall_hint else 'AI_agent/logs/experiments/2026-09-14_sm24_west_door_observation')
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
        'input_mode': 'developer_scoped_projected_wall_aperture_inventory' if hint else 'developer_scoped_original_only_west_wall_aperture_inventory',
        'only_input': 'Original plan and west-corridor wall inventory task; optional source-projected wall line explicitly recorded. No expected door count, candidate door pixels, or GT.',
        'source_wall_hint': hint,
        'implementation_sha256': {p: digest(ROOT / p) for p in implementations},
    })
    child, sha = prepare_detail_observation(Toolkit(run), question, ['1f_view.png'], 'detail_01', timeout_seconds=90 if hint else 120)
    manifest = json.loads((child / 'inputs.json').read_text())
    receipt = subscription(child, 'Images: [1f_view.png]\nQuestion: ' + question,
        model='haiku', name='detail_01', readonly=True,
        timeout=max(1, manifest['deadline_epoch'] - time.time()), log_run=run,
        receipt_context={'observation_source': {'run': 'detail_01', 'input_sha256': sha}})
    dump(run / 'summary.json', {
        'actual_model': receipt.get('actual_model'), 'elapsed_seconds': receipt['elapsed_seconds'],
        'completed': bool(receipt.get('result')) and not receipt['result'].get('is_error'),
        'estimated_cost_usd': receipt.get('result', {}).get('total_cost_usd'),
        'limits': 'Developer-scoped Haiku inventory; source wall projection hint used: ' + str(bool(hint)) + '. Not autonomous whole-building generation. CLI estimate is not a bill.',
    })
    print((run / 'summary.json').read_text())
