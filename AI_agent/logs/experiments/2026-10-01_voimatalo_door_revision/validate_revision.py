"""Saved-source preservation, pairing, clearance and connection checks."""
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from src.agent.geometry.source_model import _digest
from src.agent.geometry.source_naming import build_public_names


def main():
    source = json.loads((HERE / 'candidate_02/source_model.json').read_text())
    parent = json.loads((HERE.parent / '2026-09-30_voimatalo_user_revision/candidate_01/source_model.json').read_text())
    audit = json.loads((HERE / 'door_layout.json').read_text())
    doors = {o['id']: o for o in source['openings'] if o['kind'] == 'door'}
    rows = {d['id']: d for d in audit['changed_doors']}
    spaces = {s['id']: s for s in source['spaces']}
    checks = []
    def check(name, passed, detail):
        checks.append({'name': name, 'pass_check': bool(passed), 'detail': detail})
    digest = _digest({k:v for k,v in source.items() if k != 'source_model_sha256'})
    check('digest_and_source_checks', digest == source['source_model_sha256'] and source['validation']['status'] == 'pass', source['validation'])
    check('spaces_floors_unchanged', source['spaces'] == parent['spaces'] and source['floors'] == parent['floors'],
          'All 267 spaces, storeys, role evidence and continuous/annex circulation unchanged.')
    check('windows_unchanged', [o for o in source['openings'] if o['kind']=='window'] == [o for o in parent['openings'] if o['kind']=='window'], 334)
    check('door_identity_preserved', set(doors) == {o['id'] for o in parent['openings'] if o['kind']=='door'} and len(doors)==284, len(doors))
    check('untargeted_doors_unchanged', all(o == doors[o['id']] for o in parent['openings'] if o['kind']=='door' and o['id'] not in rows), len(audit['unchanged_doors']))
    check('enclosure_and_boundary_geometry_unchanged', source['boundaries'] == parent['boundaries'] and
          source['source_enclosure']['open_connections'] == parent['source_enclosure']['open_connections'],
          'The door repair adds no partitions, storey slabs or exterior openings.')
    failures = []
    for oid, row in rows.items():
        door = doors[oid]
        points = list(dict.fromkeys(tuple(v[:2]) for v in door['vertices']))
        length = LineString(points).length
        poly = Polygon(spaces[row['room']]['polygon'])
        hinge = Point(row['swing']['hinge_xy'])
        partition = Point(row['partition_at'])
        sector = Polygon(row['swing']['sector_xy'])
        corridor = Polygon(spaces[f"{row['floor']}_hall"]['polygon'])
        if not (math.isclose(length, .9, abs_tol=1e-7) and math.isclose(hinge.distance(partition), .25, abs_tol=1e-7)
                and min(hinge.distance(Point(p)) for p in points) < 1e-7 and poly.buffer(1e-6).covers(sector)
                and sector.intersection(corridor).area < 1e-7 and set(door['space_ids']) == {row['room'], row['after']['other_space_id']}):
            failures.append(oid)
    check('door_width_jamb_swing_and_saved_connections', not failures, {'doors': len(rows), 'failed': failures,
          'width_m': .9, 'partition_reference_offset_m': .25, 'swing': 'Inward illustrative sector clear of room walls and corridor.'})
    pair_failures = []
    for pair in audit['paired_groups']:
        a,b = [rows[oid] for oid in pair['door_ids']]
        axis = a['front']['axis']; anchor = pair['partition_at'][axis]
        pa = list(dict.fromkeys(tuple(v[:2]) for v in doors[a['id']]['vertices']))
        pb = list(dict.fromkeys(tuple(v[:2]) for v in doors[b['id']]['vertices']))
        mirrored = {tuple(round(2*anchor-c,5) if i==axis else round(c,5) for i,c in enumerate(p)) for p in pa}
        if mirrored != {tuple(round(c,5) for c in p) for p in pb}:
            pair_failures.append(pair['id'])
        partition = Polygon(spaces[a['room']]['polygon']).boundary.intersection(Polygon(spaces[b['room']]['polygon']).boundary)
        if partition.distance(Point(pair['partition_at'])) > 1e-7 or partition.length < 1:
            pair_failures.append(pair['id'])
    check('paired_doors_mirror_actual_shared_partition', len(audit['paired_groups']) == 114 and not pair_failures,
          {'pairs': len(audit['paired_groups']), 'unpaired_room_doors': len(rows)-2*len(audit['paired_groups']), 'failed': pair_failures})
    graph = defaultdict(set)
    for c in source['connections']+source['source_enclosure']['open_connections']:
        if len(c['space_ids']) == 2:
            a,b = c['space_ids'];graph[a].add(b);graph[b].add(a)
    seen=set();todo=deque(['F1_retail'])
    while todo:
        sid=todo.popleft()
        if sid not in seen:
            seen.add(sid);todo.extend(graph[sid]-seen)
    unreachable = sorted(sid for sid in spaces if not sid.startswith('ROOF') and sid not in seen)
    changed = [r['id'] for r in rows.values() if r['before']['other_space_id'] != r['after']['other_space_id']]
    check('circulation_connections', not unreachable and len(changed)==18,
          {'unreachable': unreachable, 'redirected_from_stair_to_corridor': changed, 'annex': 'unchanged'})
    names = build_public_names(source)
    check('public_names_and_roles', source['public_names']==names and names['spaces']==parent['public_names']['spaces'],
          'Room names/types unchanged; door-side names regenerated after moving to their new host wall.')
    end_walls = json.loads((HERE/'end_wall_inference.json').read_text())
    window_hosts = {o['host_boundary_id'] for o in source['openings'] if o['kind']=='window'}
    check('blank_end_walls_have_explicit_inference', len(end_walls)>0 and all(e['boundary_id'] not in window_hosts and e['assumptions'] and e['source_refs'] for e in end_walls),
          {'count':len(end_walls),'status':'Inferred blank party/gable walls; hidden and exposed actual window inventory remains unverified.'})
    result={'status':'pass' if all(c['pass_check'] for c in checks) else 'fail', 'source_model_sha256':digest,
            'checks':checks,'counts':{'spaces':len(spaces),'windows':len(window_hosts),'doors':len(doors)},
            'not_evaluated':['Human acceptance','As-built door/hidden-window fidelity','Detailed hardware or regulatory compliance','Framework or working-model performance']}
    # Count windows themselves, not their host walls.
    result['counts']['windows']=sum(o['kind']=='window' for o in source['openings'])
    (HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[c for c in checks if not c['pass_check']]},ensure_ascii=False))
    assert result['status']=='pass'


if __name__ == '__main__':
    main()
