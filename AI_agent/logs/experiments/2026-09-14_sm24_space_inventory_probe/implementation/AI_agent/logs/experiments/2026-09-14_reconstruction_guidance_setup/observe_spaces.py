"""Bounded plan-space interpretation probe, without metric geometry or a BIM seed."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import Toolkit,digest,dump,prepare_detail_observation,subscription

QUESTION='''Inspect ONLY the physical space partition of the supplied floor plan.
Do not compute metric dimensions, wall thickness, heights, window sizes, or a BIM.
The task is to distinguish full physical rooms and circulation from furniture,
door symbols and annotation regions before any geometry generation.

For this bounded method probe, obtain view_pixel_region_overview after seeing the
original, choosing the background color yourself. Compare its numbered regions
with the original walls, and use view_pixel_region on relevant returned seeds to
resolve ambiguous extents. Pixel regions are not rooms; furniture and door symbols
may divide them, or actual openings may join rooms. If it is unsuitable, explain
that and use original crops. Do not trace precise metric polygons or spend the
budget measuring dimension chains. Do not assume room counts or rectangular shapes.

Return a concise inventory of physical spaces: your space label, location, any
supporting candidate IDs/seeds actually returned by the tool, and the full extent
in words including bends/extensions. Explain the visible physical separators
between neighboring spaces, and where circulation stays continuous. Distinguish
observed walls from uncertain hypotheses. Do not create walls from differing
furniture/use, or require a separate room for each colored component. Mark unclear
boundaries rather than inventing connections. Cover the floor, including small
spaces; do not infer omitted content from a fixed expected count.

Only this original plan and the generic task are supplied: no previous BIM,
correct room/door counts, prior observations, coordinates or GT. Finish within
180 seconds. State what remained unexamined. No BIM write or final fidelity claim.
'''

if __name__=='__main__':
    run=ROOT/'AI_agent/logs/experiments/2026-09-14_sm24_space_inventory_probe'
    run.mkdir(exist_ok=False);(run/'images').mkdir()
    original=ROOT/'case_tests/e2e_tests/sm24_anchor/case_data/1f_view.png'
    shutil.copy2(original,run/'images'/original.name)
    with Image.open(original) as im:size=list(im.size)
    files=[ROOT/'scripts/tool_scripts/run_bim_agent.py',ROOT/'scripts/tool_scripts/bim_agent_guidance.py',
           *sorted((ROOT/'src/agent/geometry').glob('*.py')),ROOT/'src/agent/execution/subscription_json.py',Path(__file__).resolve()]
    frozen={str(p.relative_to(ROOT)):p.read_bytes() for p in files}
    dump(run/'inputs.json',{'images':{original.name:{'size':size,'sha256':digest(original)}},
       'input_mode':'developer_scoped_floor_partition_observation',
       'only_input':'One original plan and generic partition-only/overview method question; no candidate, count, coordinates or GT.',
       'implementation_sha256':{name:digest(ROOT/name) for name in frozen}})
    child,sha=prepare_detail_observation(Toolkit(run),QUESTION,[original.name],'detail_01',timeout_seconds=180)
    deadline=json.loads((child/'inputs.json').read_text())['deadline_epoch']
    receipt=subscription(child,'Images: [1f_view.png]\nQuestion: '+QUESTION,model='sonnet',effort='low',
       name='detail_01',readonly=True,timeout=max(1,deadline-time.time()),log_run=run,
       receipt_context={'observation_source':{'run':'detail_01','input_sha256':sha,'images':{original.name:digest(original)}}})
    for name,data in frozen.items():
        assert (ROOT/name).read_bytes()==data,name
        out=run/'implementation'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    dump(run/'summary.json',{'actual_model':receipt.get('actual_model'),'effort':'low',
       'elapsed_seconds':receipt['elapsed_seconds'],'completed':bool(receipt.get('result')) and not receipt['result'].get('is_error'),
       'estimated_cost_usd':receipt.get('result',{}).get('total_cost_usd'),'frozen_code_unchanged':True,
       'limits':'Developer-selected plan-only method and Sonnet low budget; not an autonomous whole-building run, source revision, cost ablation or fidelity verdict. CLI estimate is not a bill.'})
    (run/'observation.txt').write_text(receipt.get('result',{}).get('result','No completed answer'))
    print((run/'summary.json').read_text())
