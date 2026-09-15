"""Move an inferred service partition into the observed gap; preserve windows."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
path=HERE/'case_plan.json'
old=HERE/'case_plan_before_host_revision.json'
assert not old.exists()
old.write_bytes(path.read_bytes())
plan=json.loads(path.read_text())
data=json.loads((HERE/'assembly_observations.json').read_text())['openings']
first=next(o for o in data if o['id']=='court_short_R01_G01')
second=next(o for o in data if o['id']=='court_short_R01_G02')
gap=[first['span_m'][1],second['span_m'][0]]
new=round(sum(gap)/2,1)
assert gap[0]<new<gap[1]
previous=plan['inferred_service_rectangles']['services_n'][2]
plan['inferred_service_rectangles']['services_n'][2]=new
plan['host_revision']={'trigger':'candidate_01_host_failure.json','moved_inferred_partition_x_m':[previous,new],
    'observed_gap_x_m':gap,'observed_opening_ids':[first['id'],second['id']],
    'window_coordinates_modified':False,'reason':'Original inferred service boundary crossed a visible complete window group; choose a position inside the observed inter-window gap.'}
plan['unresolved'].append('九条窗观察的未决或排除情况保存在源generation.provenance.aperture_input_metadata中：包含未建的大窗/暗槽/残窗，以及不属于该面的后墙透出；不能以已建244组窗宣称立面完整。')
path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(plan['host_revision']))
