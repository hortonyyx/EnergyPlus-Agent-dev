"""Original-only complete room tracing with a visual preview and explicit selection."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = """Trace the COMPLETE plan footprint of the southeasternmost room,
including its exterior sides, every real change of direction, and ALL of this
room's door apertures (both internal and exterior if visible). Do not trace
furniture, door swing arcs or leaves as room walls. Do not assume a rectangle.
This is an independent original-image observation, not correction of an old BIM.

Use preview_space_trace to submit an ordered closed room polygon in ORIGINAL
pixels plus door aperture endpoints on the room boundary. The logical contour
closes across a door; the opening uses the two jambs across the wall, not a
hinge-to-swung-leaf-tip diagonal. Select a consistent light-weight representative
wall line; use the outside footprint reference for exterior sides and a stated
representative line for thin internal walls. Explain that choice in basis.
Provide two [pixel,world_metres] calibration anchors on each image axis from
visible dimension/extension endpoints; world origin is the building footprint's
southwest corner, x east, y north. Keep dimension-chain labels tied to the actual
extension endpoints; exterior aperture chains do not imply interior partitions.

Preview early (aim within 80 seconds). Actually inspect the returned clean and
marked images to check every turn and door segment against the drawing. Correct
an erroneous trace with another preview, then select_space_trace for the most
faithful executable observation. A valid polygon alone is not a visual pass.
Exact pixel precision is secondary to the correct room shape and aperture hosts.
Do not invent a segment to turn a door leaf into a wall. Use measurement/crops as
needed, avoid long prose and unnecessary full reading. Finish within 180 seconds.
No seed, prior observation, room count, supplied pixel coordinates or GT is given.
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['haiku', 'sonnet'], default='sonnet')
    parser.add_argument('--out', type=Path, default=ROOT/'AI_agent/logs/experiments/2026-09-13_sm24_space_trace_sonnet')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--seed-trace', type=Path)
    parser.add_argument('--pixel-region', action='store_true')
    parser.add_argument('--reference-review', action='store_true')
    parser.add_argument('--effort', choices=['low','medium'])
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.pixel_region:
        QUESTION = 'First inspect the original to select a clear interior point of the target room, then call view_pixel_region with its background color. Use the actual returned contour/bbox to locate the target before tracing: do not guess a different wall path in empty circulation. The connected region may follow door arcs/leaves and furniture; restore straight logical walls across real apertures using jamb-to-jamb segments, not the arc or leaf. Then preview the complete room including all exterior door apertures. Do not infer exterior doors from a room label.\n\n' + QUESTION
    if args.seed_trace:
        QUESTION = 'A saved model-generated trace_001 is available. FIRST call view_space_trace to inspect its actual clean/marked overlay. Recheck its ordered contour and all apertures against the original image, revise promptly with preview_space_trace, inspect that returned image, and select your final trace. No correct coordinates are supplied. Aim for a corrected preview in 50 seconds.\n\n' + QUESTION
    if args.reference_review:
        QUESTION = 'Developer review found a reference-plane inconsistency in your previous trace: the room-background contour follows INNER exterior wall faces, although the basis claims OUTSIDE faces. Its calibration also needs rechecking against the actual building footprint extremities: a dimension line offset is not a building endpoint. Keep the observed room topology, independently correct the exterior representative lines and both axis calibrations from the original. Use the actual outside wall faces at the footprint southwest/northeast as zero/full-span anchors, backed by overall dimensions; internal partitions use a stated representative line. Project jambs onto the revised logical host line. No developer pixel or metre coordinates are provided. Save and inspect a NEW preview before selecting.\n\n' + QUESTION
    QUESTION = QUESTION.replace('180 seconds', f'{args.timeout} seconds')
    if args.dry_run:
        print(QUESTION)
        raise SystemExit
    out = args.out.resolve()
    out.mkdir(exist_ok=False)
    (out/'images').mkdir()
    name = '1f_view.png'
    target = out/'images'/name
    shutil.copy2(ROOT/'case_tests/e2e_tests/sm24_anchor/case_data'/name, target)
    with Image.open(target) as im:
        size = list(im.size)
    implementation = ['scripts/tool_scripts/run_bim_agent.py', 'src/agent/geometry/space_trace.py', 'src/agent/geometry/pixel_region.py']
    (out/'implementation').mkdir()
    for path in implementation:
        shutil.copy2(ROOT/path, out/'implementation'/Path(path).name)
    dump(out/'inputs.json', {'images': {name: {'size': size, 'sha256': digest(target)}},
        'input_mode': 'developer_scoped_original_boundary_observation',
        'only_input': ('one original plan, local question and previous model-generated trace; no BIM or GT'
                       if args.seed_trace else 'one original plan and local question; no BIM, prior answer or GT'),
        'developer_reference_plane_feedback': args.reference_review,
        'implementation_sha256': {p: digest(ROOT/p) for p in implementation}})
    child, input_sha = prepare_detail_observation(Toolkit(out), QUESTION, [name], 'detail_01', timeout_seconds=args.timeout)
    if args.seed_trace:
        (child/'space_traces').mkdir()
        shutil.copy2(args.seed_trace, child/'space_traces/trace_001.json')
        shutil.copy2(args.seed_trace.with_suffix('.png'), child/'space_traces/trace_001.png')
        manifest = json.loads((child/'inputs.json').read_text())
        manifest['seed_trace'] = {'trace_id':'trace_001','trace_sha256':digest(args.seed_trace), 'origin':'previous model-generated observation; not ground truth'}
        dump(child/'inputs.json',manifest)
        input_sha = digest(child/'inputs.json')
    source = {'run': 'detail_01', 'input_sha256': input_sha, 'images': {name: digest(target)}}
    deadline = json.loads((child/'inputs.json').read_text())['deadline_epoch']
    receipt = subscription(child, f'Images: {[name]}\nQuestion: {QUESTION}', model=args.model,
        name='detail_01', readonly=True, timeout=deadline-time.time(), log_run=out,
        receipt_context={'observation_source': source}, effort=args.effort)
    result = receipt.get('result', {})
    response = {'actual_model': receipt.get('actual_model'), 'timed_out': receipt.get('timed_out', False),
        'completed': bool(result) and not result.get('is_error', False) and not receipt.get('timed_out', False) and receipt.get('returncode') == 0,
        'result': result.get('result', 'No completed answer'), 'observation_source': source}
    dump(out/'response.json', response)
    print(json.dumps(response, ensure_ascii=False, indent=2))
