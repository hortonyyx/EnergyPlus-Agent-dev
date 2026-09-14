"""Verify explicit three-door correction/one false-door removal without GT."""
import json
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from PIL import Image, ImageChops
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.proposal_edits import apply_proposal_edits
from src.agent.geometry.source_image_overlay import render_source_overlay

read = lambda p: json.loads(p.read_text())
run = ROOT/'AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run12'
assert read(run/'summary.json')['deterministic_application_completed']
before, after = [read(run/p/'source_model.json') for p in ['seed','candidate_01']]
seed, proposal = [read(run/p/'proposal.json') for p in ['seed','candidate_01']]
ops = read(run/'operations.json')
removed = 'D_Corridor_Office3'
changed = {'D_Corridor_Office1','D_Corridor_Office2','D_Corridor_MeetingDining'}
old, new = [{o['id']:o for o in s['openings']} for s in [before,after]]
def physical(o):
    return {k:o.get(k) for k in ['kind','vertices','space_ids','exterior','connectivity']}
connections = [{c['opening_id']:c for c in s['connections']} for s in [before,after]]
checks = {
    'operation_replay_matches_full_proposal':apply_proposal_edits(seed,ops)==proposal,
    'source_spaces_unchanged': before['spaces']==after['spaces'],
    'exactly_named_false_opening_removed':set(old)-set(new)=={removed} and not set(new)-set(old),
    'only_three_expected_doors_changed':{k for k in new if physical(new[k])!=physical(old[k])}==changed,
    'other_openings_including_all_windows_and_exterior_doors_unchanged':all(physical(o)==physical(old[k]) for k,o in new.items() if k not in changed),
    'only_false_connection_removed':set(connections[0])-set(connections[1])=={removed} and not set(connections[1])-set(connections[0]),
    'kept_connection_space_pairs_preserved':all(new[k]['space_ids']==old[k]['space_ids'] for k in new),
    'door_heights_preserved':all(sorted({v[2] for v in new[k]['vertices']})==sorted({v[2] for v in old[k]['vertices']}) for k in changed),
    'no_unbuilt_openings':not after['unbuilt_openings'],
    'source_geometry_ready':read(run/'candidate_01/report.json')['source_geometry_ready'],
}
with tempfile.TemporaryDirectory() as d:
    out = Path(d)/'reexport'
    export_source_proposal(proposal,out,provenance=read(run/'candidate_01/report.json')['provenance'])
    checks['source_reexport_sha256_matches'] = read(out/'source_model.json')['source_model_sha256']==after['source_model_sha256']
overlay = read(run/'image_overlays/overlay_001.json')
with Image.open(run/'images'/overlay['image']) as original:
    picture, metadata = render_source_overlay(after,original,floor_id=overlay['floor_id'],
        x_anchors=overlay['anchors']['x'],y_anchors=overlay['anchors']['y'],basis=overlay['basis'],image_name=overlay['image'])
with Image.open(run/overlay['overlay_image']) as actual:
    checks['actual_source_overlay_replay_matches'] = actual.size==picture.size and ImageChops.difference(actual.convert('RGB'),picture.convert('RGB')).getbbox() is None
checks['overlay_bound_to_current_source'] = overlay['source_model_sha256']==after['source_model_sha256']
result = {'checks':checks,'removed_false_door_id':removed,'updated_door_ids':sorted(changed),
          'limitation':'Source preservation and reproducibility only. Removal semantics and image correspondence require original-plan review; no GT was used.'}
(run/'application_verification.json').write_text(json.dumps(result,indent=2)+'\n')
assert all(checks.values()), checks
print(json.dumps(result,indent=2))
