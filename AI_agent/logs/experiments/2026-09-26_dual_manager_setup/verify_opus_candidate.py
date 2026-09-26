"""Coordinator checks for a revised Voimatalo candidate, independent of room names."""
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

ROOT = Path(__file__).resolve().parents[4]
BASELINE = ROOT/'AI_agent/logs/experiments/2026-09-25_voimatalo_opus_development/candidate_01/source_model.json'


def verify(candidate):
    old_checks = importlib.import_module('AI_agent.logs.experiments.2026-09-16_voimatalo_completion.verify_candidate')
    source = json.loads((candidate/'source_model.json').read_text())
    proposal = json.loads((candidate/'proposal.json').read_text())
    baseline = json.loads(BASELINE.read_text())
    windows = {row['id']:row for row in baseline['openings'] if row['kind']=='window'}
    current = {row['id']:row for row in source['openings']}
    missing = sorted(windows.keys()-current.keys())
    changed = [name for name,old in windows.items() if name in current
               and (current[name]['kind'] != old['kind'] or current[name]['vertices'] != old['vertices'])]
    rehosted = [name for name,old in windows.items() if name in current
                and current[name].get('space_ids') != old.get('space_ids')]
    external_doors = {row['id']:row for row in baseline['openings'] if row['kind']=='door' and row.get('exterior')}
    exterior_changes = [name for name,old in external_doors.items() if name not in current or
                       (current[name]['kind'],current[name]['vertices']) != (old['kind'],old['vertices'])]
    declared = {row['id'] for key in ['windows','openings'] for row in proposal['geometry'].get(key,[])}
    spaces = {row['id']:row for row in source['spaces']}
    roof = {name for name,row in spaces.items() if 'roof' in str(row.get('role','')).lower()
            or str(row.get('floor_id','')).upper().startswith('ROOF')}
    graph = {name:set() for name in spaces}
    graph['__OUTSIDE__'] = set()
    for connection in source['connections']:
        if connection['kind'] not in {'door','open'}:
            continue
        owners = list(connection['space_ids'])
        if connection.get('exterior') and len(owners)==1:
            owners.append('__OUTSIDE__')
        if len(owners)==2:
            first,second = owners
            graph[first].add(second)
            graph[second].add(first)
    reached, pending = {'__OUTSIDE__'}, ['__OUTSIDE__']
    while pending:
        for name in graph[pending.pop()]:
            if name not in reached:
                reached.add(name)
                pending.append(name)
    unreachable = sorted(set(spaces)-roof-reached)
    floors = [row for row in source['floors'] if row['id'].startswith('F') and row['id'][1:].isdigit()]
    cores = []
    # Validate the candidate's declared continuous spaces at their actual spans.
    # A set-back top landing may legitimately replace the upper end of a core;
    # unchanged old core IDs/extents are not a geometry invariant.
    core_ids = sorted({name for floor in floors for name in floor.get('spanning_space_ids',[])})
    for core in core_ids:
        space = spaces.get(core)
        horizontal = [row for row in source['boundaries'] if row['space_id']==core
                      and row['geometry_type'] in {'floor','ceiling'}]
        levels = sorted({round(v[2],8) for row in horizontal for v in row['vertices']})
        expected_levels = [round(space['z_floor'],8), round(space['z_floor']+space['height'],8)] if space else []
        covered_floors = [floor for floor in floors if space and
            min(space['z_floor']+space['height'],floor['z_floor']+floor['height']) -
            max(space['z_floor'],floor['z_floor']) > 1e-7]
        floor_connections = {}
        for floor in covered_floors:
            # Another continuous core can be the immediate peer. Follow actual
            # aperture heights through this floor, never infer access from IDs.
            local_graph = {name: [] for name in spaces}
            for connection in source['connections']:
                aperture = current.get(connection['opening_id'])
                if connection['kind'] not in {'door','open'} or aperture is None or len(connection['space_ids']) != 2:
                    continue
                z_values = [v[2] for v in aperture['vertices']]
                if min(max(z_values), floor['z_floor'] + floor['height']) - max(min(z_values), floor['z_floor']) <= 1e-7:
                    continue
                first, second = connection['space_ids']
                local_graph[first].append((second, connection['opening_id']))
                local_graph[second].append((first, connection['opening_id']))
            paths, queue = {core: []}, [core]
            while queue:
                owner = queue.pop(0)
                for peer, opening_id in local_graph[owner]:
                    if peer not in paths:
                        paths[peer] = paths[owner] + [opening_id]
                        queue.append(peer)
            floor_connections[floor['id']] = [
                {'space_id': name, 'opening_path': path}
                for name, path in paths.items()
                if name != core and spaces[name]['floor_id'] == floor['id']]

        declared_floors = [row['id'] for row in floors if core in row.get('spanning_space_ids',[])]
        cores.append({'id':core,'present':core in spaces,'horizontal_boundary_count':len(horizontal),
            'horizontal_levels':levels,'expected_end_levels':expected_levels,'floor_connections':floor_connections,
            'covered_floor_ids':[floor['id'] for floor in covered_floors],
            'spanning_floor_references':declared_floors,
            'status':'pass' if space and levels==expected_levels
                and sorted(declared_floors)==sorted(floor['id'] for floor in covered_floors)
                and covered_floors and all(floor_connections.values()) else 'fail'})
    result = {'candidate':str(candidate), 'source_sha256':source['source_model_sha256'],
        'baseline':str(BASELINE), 'floor_access_method':'aperture-height-filtered graph to a local floor space; continuous core peers allowed','source_validation':source.get('validation'),
        'source_export_replay':old_checks.check_source_export_replay(candidate,candidate/'source_model.json',source),
        'positive_volume_overlap':old_checks.check_no_overlap(source),
        'baseline_windows':{'count':len(windows),'missing':missing,'changed_kind_or_geometry':changed,
            'rehosted':rehosted,'interpretation':'Room splits may legitimately rehost preserved windows.'},
        'baseline_external_door_geometry_changes':exterior_changes,
        'declared_not_built':sorted(declared-current.keys()),'built_not_declared':sorted(current.keys()-declared),
        'unbuilt_openings':source.get('unbuilt_openings',[]),
        'unsupported':source.get('unsupported',[]),
        'connectivity':{'unreachable_nonroof_spaces':unreachable,'roof_spaces_excluded':sorted(roof),
            'interpretation':'Declared door/open connectivity only; not proof of actual unseen layout.'},
        'continuous_cores':cores,
        'baseline_continuous_ids_missing':sorted(row['id'] for row in baseline['spaces']
            if row['id'].endswith('_continuous') and row['id'] not in spaces),
        'space_counts_by_floor':dict(Counter(row['floor_id'] for row in source['spaces'])),
        'space_roles':dict(Counter(row.get('role','unknown') for row in source['spaces'])),
        'opening_kinds':dict(Counter(row['kind'] for row in source['openings'])),
        'scope':'Technical checks only. Interior plausibility, missing-content coverage and user acceptance require visual review.'}
    result['technical_checks_pass'] = (
        result['source_export_replay']['status']=='pass' and result['positive_volume_overlap']['status']=='pass'
        and not missing and not changed and not exterior_changes and not result['declared_not_built']
        and not result['built_not_declared'] and not result['unbuilt_openings'] and not result['unsupported']
        and not unreachable and all(row['status']=='pass' for row in cores)
        and (source.get('validation') or {}).get('status') != 'severe')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    assert not args.out.exists(), 'Keep prior audits intact'
    report = verify(args.candidate.resolve())
    dump(args.out,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
