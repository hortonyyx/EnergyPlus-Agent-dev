"""Bounded original-only southeast boundary observation; no geometry answers."""
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

QUESTION = """Inspect only the interior boundary of the southeasternmost enclosed
space on this floor plan, where it meets the circulation area. Identify the
actual boundary path and its visible door/opening gap, including any changes
of direction. Do not read the whole building or infer rectangular partitions.
First find a suitable local crop yourself. Use view_pixel_profile on selected
ink and narrow strips to measure supporting pixels rather than guessing their
coordinates. Its candidate numbers are ink runs, not walls: inspect the original
and the actual support intervals to distinguish furniture, door arcs and walls.
You choose the crop, RGB and threshold; empty/fragmented support is inconclusive.
Report a compact original-pixel polyline or segments, separate opening endpoints,
the tool measurements used, and any uncertain connection/reference face. Keep
wall faces distinct from a proposed representative centreline. You may use
magnified clean crops. No scale conversion, BIM construction or other room
inventory is needed. No previous model, proposed coordinates, counts, prior
observation or GT is supplied. Finish within 150 seconds, at most 400 words.
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['haiku', 'sonnet'], default='haiku')
    parser.add_argument('--out', type=Path, default=ROOT/'AI_agent/logs/experiments/2026-09-13_sm24_pixel_support_observation')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
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
    implementation = ['scripts/tool_scripts/run_bim_agent.py']
    (out/'implementation').mkdir()
    shutil.copy2(ROOT/implementation[0], out/'implementation/run_bim_agent.py')
    dump(out/'inputs.json', {'images': {name: {'size': size, 'sha256': digest(target)}},
        'input_mode': 'developer_scoped_original_boundary_observation',
        'only_input': 'one original plan and local question; no BIM, prior answer or GT',
        'implementation_sha256': {p: digest(ROOT/p) for p in implementation}})
    child, input_sha = prepare_detail_observation(Toolkit(out), QUESTION, [name], 'detail_01', timeout_seconds=150)
    source = {'run': 'detail_01', 'input_sha256': input_sha, 'images': {name: digest(target)}}
    deadline = json.loads((child/'inputs.json').read_text())['deadline_epoch']
    receipt = subscription(child, f'Images: {[name]}\nQuestion: {QUESTION}', model=args.model,
        name='detail_01', readonly=True, timeout=deadline-time.time(), log_run=out,
        receipt_context={'observation_source': source})
    result = receipt.get('result', {})
    response = {'actual_model': receipt.get('actual_model'), 'timed_out': receipt.get('timed_out', False),
        'completed': bool(result) and not result.get('is_error', False) and not receipt.get('timed_out', False) and receipt.get('returncode') == 0,
        'result': result.get('result', 'No completed answer'), 'observation_source': source}
    dump(out/'response.json', response)
    print(json.dumps(response, ensure_ascii=False, indent=2))
