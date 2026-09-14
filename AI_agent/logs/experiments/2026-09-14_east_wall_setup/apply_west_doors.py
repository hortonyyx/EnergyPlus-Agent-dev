"""Replay the reviewed worker inventory on the existing source wall.

Developer maps the three observed doors to existing IDs and explicitly rejects
one old invented opening using continuous original-wall support. No GT/models.
"""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from shapely.geometry import LineString, Polygon
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.proposal_edits import apply_proposal_edits

if __name__ == '__main__':
    observation = ROOT / 'AI_agent/logs/experiments/2026-09-14_sm24_west_door_projected_observation'
    seed = ROOT / 'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run11/candidate_01'
    out = ROOT / 'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run12'
    if out.exists():
        raise FileExistsError(out)
    assert json.loads((observation / 'summary.json').read_text())['completed']
    receipt_path = observation / 'detail_01_receipt.json'
    answer = json.loads(receipt_path.read_text())['result']['result']
    # Parse the saved worker's literal endpoint report, without supplying new
    # pixel coordinates or relying on its vague furniture-based room labels.
    north = re.findall(r'\*\*Northern jamb\*\*:\s*\[([\d.]+),\s*([\d.]+)\]', answer)
    south = re.findall(r'\*\*Southern jamb\*\*:\s*\[([\d.]+),\s*([\d.]+)\]', answer)
    assert len(north) == len(south) == 3
    traces = [[list(map(float,a)), list(map(float,b))] for a,b in zip(north,south)]
    frame = json.loads((seed.parent / 'trace_a.json').read_text())
    proposal = json.loads((seed / 'proposal.json').read_text())
    cells = {c['id']: c for f in proposal['geometry']['floors'] for c in f['cells']}
    doors = {o['id']: o for o in proposal['geometry']['openings']}
    identities = ['D_Corridor_Office1', 'D_Corridor_Office2', 'D_Corridor_MeetingDining']
    def world(v, anchors):
        (p0,w0),(p1,w1) = anchors
        return w0 + (v-p0)*(w1-w0)/(p1-p0)
    def pixel(v, anchors):
        (p0,w0),(p1,w1) = anchors
        return p0 + (v-w0)*(p1-p0)/(w1-w0)
    operations = []
    mappings = []
    refs = [f"1f_view.png: model west-wall profile and reviewed inventory; receipt sha256 {digest(receipt_path)}"]
    for identity, endpoints in zip(identities, traces):
        old = doors[identity]
        assert old['p1'][0] == old['p2'][0]
        wall_x = old['p1'][0]
        converted = [[round(world(x,frame['x_anchors']),6), round(world(y,frame['y_anchors']),6)] for x,y in endpoints]
        new = [[wall_x, p[1]] for p in converted]
        line = LineString(new)
        for sid in (old['space_id'],old['other_space_id']):
            assert Polygon(cells[sid]['polygon']).boundary.buffer(1e-6).covers(line), (identity,sid)
        for p,q in zip(converted,new):
            assert abs(p[0]-q[0]) <= .065, 'reference-plane projection requires new review'
        mappings.append({'source_opening_id':identity,'observed_pixels':endpoints,'converted_metres':converted,
                         'applied_metres':new,'reference_plane':'Existing corridor-west source wall; jamb endpoints project across wall thickness only, without changing measured pixel y.'})
        operations.append({'op':'update_opening','id':identity,'changes':{'p1':new[0],'p2':new[1],
            'assumptions':['Door jambs measured from the original gray-wall break and cyan swing; projected onto existing representative wall. Height and state inherited, not re-observed.']},
            'reason':'Apply independently measured west-wall jamb interval to the matching existing corridor door.', 'source_refs':refs})
    removed = 'D_Corridor_Office3'
    profile_path = observation / 'detail_01/pixel_profiles/profile_001.json'
    profile = json.loads(profile_path.read_text())
    old = doors[removed]
    old_pixels = sorted(pixel(p[1],frame['y_anchors']) for p in (old['p1'],old['p2']))
    supporting = [(c['id'],c['peak'],span) for c in profile['candidates'] for span in c['support_intervals_at_peak']
                  if span[0] <= old_pixels[0] and old_pixels[1] <= span[1]]
    assert len(supporting) == 1, 'removal requires one continuous measured wall span over the whole old door'
    operations.append({'op':'remove_opening','id':removed,
        'reason':'Developer original-image review and the complete worker inventory show this old extra opening lies wholly within a continuous supported wall, with no door arc/gap. Retract the previous unverified distinct-arc claim.',
        'source_refs':refs + [f"1f_view.png: profile {supporting[0][0]} x={supporting[0][1]}, continuous y={supporting[0][2]}; old aperture projects to y={old_pixels}"]})
    operations.append({'op':'set_notes',
        'assumptions': proposal['assumptions'] + ['Three corridor-west apertures restored from original measured wall gaps. The previous extra Office2 aperture was explicitly removed after continuous-wall evidence and original-image review; this changes 11 old doors to 10 actual candidate doors.'],
        'unresolved':proposal['unresolved'] + ['This remains developer-assisted local recovery. Global calibration, reference-plane offsets, original door heights/states and complete independent building fidelity remain unverified.']})
    result = apply_proposal_edits(proposal,operations)
    out.mkdir()
    shutil.copytree(observation / 'images', out / 'images')
    (out / 'implementation').mkdir()
    snapshots = [Path(__file__), ROOT/'scripts/tool_scripts/run_bim_agent.py', ROOT/'src/agent/geometry/proposal_edits.py']
    for p in snapshots:
        shutil.copy2(p,out/'implementation'/p.name)
    manifest = {'images':json.loads((observation/'inputs.json').read_text())['images'],
        'input_mode':'developer_selected_west_door_measurement_replay',
        'only_input':'Existing source, model-observed original-pixel jambs, original wall profile and explicit developer identity/removal decision; no GT or new model call.',
        'seed':{'source':str(seed),'proposal_sha256':digest(seed/'proposal.json')},
        'observation':{'run':str(observation),'receipt_sha256':digest(receipt_path),'profile_sha256':digest(profile_path)},
        'application_implementation_sha256':{str(p.relative_to(ROOT)):digest(p) for p in snapshots}}
    dump(out/'inputs.json',manifest)
    export_source_proposal(proposal,out/'seed',provenance=manifest['seed'])
    dump(out/'operations.json',operations)
    dump(out/'measurement_application.json',{'doors':mappings,'removed_id':removed,'old_aperture_pixel_interval':old_pixels,
        'continuous_wall_support':supporting,'removal_decision':'Developer checked original; continuous pixel support alone is not a universal semantic classifier.'})
    toolkit = Toolkit(out)
    report = toolkit.build(result,action='apply_reviewed_west_door_inventory',parent='seed',operations=operations)
    assert report.get('source_geometry_ready'), report
    toolkit.project_overlay(report['candidate'],frame['name'],'F1',frame['x_anchors'],frame['y_anchors'],frame['basis'],trigger_action='west_door_inventory_application')
    delivery = toolkit.delivery(report['candidate'],selection_origin='developer_selected_deterministic_trace_replay',generation_status={'state':'completed','agent_response_completed':False})
    dump(out/'summary.json',{'input_mode':manifest['input_mode'],'agent_response_completed':False,'deterministic_application_completed':True,
        'has_viewable_candidate':True,'delivery':{'candidate':report['candidate'],'selection_origin':delivery['selection_origin']},
        'counts':report['counts'],'model_invocations_in_application':0,'drawing_fidelity':'not_evaluated'})
    print(json.dumps({'counts':report['counts'],'removed_id':removed,'doors':mappings},indent=2))
