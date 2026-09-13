"""Apply a model-selected local trace with explicit, audited source-frame snapping.

Developer selects the two source IDs and procedure, never supplies vertices or GT.
This is a deterministic local observation replay, not an autonomous cold start.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.proposal_edits import apply_proposal_edits
from src.agent.execution.source_proposal import export_source_proposal


def shape(cell):
    return Polygon(cell['polygon']) if cell.get('polygon') else box(cell['x'][0],cell['y'][0],cell['x'][1],cell['y'][1])


_AXIS_EPS = 1e-9


def _axis_edges(ring, *, label):
    """Return complete orthogonal edges, retaining the input ring's edge IDs."""
    result=[]
    for index,(first,second) in enumerate(zip(ring,ring[1:]+ring[:1])):
        x0,y0=map(float,first);x1,y1=map(float,second)
        if math.isclose(x0,x1,abs_tol=_AXIS_EPS):
            result.append({'index':index,'axis':'x','coordinate':x0,'start':min(y0,y1),'end':max(y0,y1)})
        elif math.isclose(y0,y1,abs_tol=_AXIS_EPS):
            result.append({'index':index,'axis':'y','coordinate':y0,'start':min(x0,x1),'end':max(x0,x1)})
        else:
            raise ValueError(f'{label} edge {index} is not horizontal or vertical')
        if result[-1]['end']-result[-1]['start'] <= _AXIS_EPS:
            raise ValueError(f'{label} edge {index} is degenerate')
    return result


def _outer_boundary_runs(region):
    """Merge collinear exterior-only segments; the former internal wall is absent."""
    if region.geom_type!='Polygon' or region.is_empty or region.interiors:
        raise ValueError('selected source-space union must be one hole-free polygon')
    groups={'x':{},'y':{}}
    for edge in _axis_edges([list(p) for p in list(region.exterior.coords)[:-1]],label='source union exterior'):
        key=round(edge['coordinate'],9)
        groups[edge['axis']].setdefault(key,[]).append(edge)
    runs=[]
    for axis,by_coordinate in groups.items():
        for rows in by_coordinate.values():
            rows=sorted(rows,key=lambda row:(row['start'],row['end']))
            current=None
            for row in rows:
                if current is None or row['start']>current['end']+_AXIS_EPS:
                    if current is not None:runs.append(current)
                    current={'axis':axis,'coordinate':row['coordinate'],'start':row['start'],
                             'end':row['end'],'source_edge_indexes':[row['index']]}
                else:
                    current['end']=max(current['end'],row['end'])
                    current['source_edge_indexes'].append(row['index'])
            if current is not None:runs.append(current)
    return runs


def _map_coordinate(value,mappings):
    matches=[row for row in mappings if math.isclose(value,row['from_coordinate_m'],abs_tol=_AXIS_EPS)]
    targets={round(row['to_coordinate_m'],9) for row in matches}
    if len(targets)>1:
        raise ValueError(f'ambiguous shared source coordinate {value}')
    return (matches[0]['to_coordinate_m'],matches[0]) if matches else (float(value),None)


def normalize_trace_ring(ring,region,tolerance_m):
    """Snap only whole trace edges to compatible exterior union runs.

    A coordinate is mapped once for every point which shares it.  This avoids
    per-vertex nearest-point choices that can turn a nominally orthogonal edge
    into a diagonal, and it makes the applied reference-plane adjustment fully
    reconstructible from the audit.
    """
    if not 0<=tolerance_m<=.2:raise ValueError('boundary snap must be explicit, between 0 and 0.2m')
    trace_edges=_axis_edges(ring,label='trace polygon')
    outer_runs=_outer_boundary_runs(region)
    mappings={'x':[],'y':[]};edge_audit=[]
    for edge in trace_edges:
        candidates=[run for run in outer_runs if run['axis']==edge['axis']
                    and abs(run['coordinate']-edge['coordinate'])<=tolerance_m+_AXIS_EPS
                    and run['start']-tolerance_m<=edge['start']
                    and edge['end']<=run['end']+tolerance_m]
        candidate_coordinates={round(run['coordinate'],9) for run in candidates}
        if len(candidate_coordinates)>1:
            raise ValueError(f"ambiguous exterior-boundary match for trace edge {edge['index']}")
        if not candidates:
            edge_audit.append({'trace_edge_index':edge['index'],'axis':edge['axis'],'before_coordinate_m':edge['coordinate'],
                               'status':'unchanged_no_compatible_outer_boundary_run'})
            continue
        chosen=candidates[0]
        existing=[row for row in mappings[edge['axis']]
                  if math.isclose(edge['coordinate'],row['from_coordinate_m'],abs_tol=_AXIS_EPS)]
        if existing and not math.isclose(existing[0]['to_coordinate_m'],chosen['coordinate'],abs_tol=_AXIS_EPS):
            raise ValueError(f"ambiguous shared coordinate on trace edge {edge['index']}")
        if not existing:
            mappings[edge['axis']].append({'from_coordinate_m':edge['coordinate'],'to_coordinate_m':chosen['coordinate'],
                                            'trace_edge_indexes':[],'outer_boundary_runs':[]})
            existing=[mappings[edge['axis']][-1]]
        mapping=existing[0];mapping['trace_edge_indexes'].append(edge['index'])
        mapping['outer_boundary_runs'].append({'coordinate_m':chosen['coordinate'],'span_m':[chosen['start'],chosen['end']],
                                                'source_edge_indexes':chosen['source_edge_indexes']})
        edge_audit.append({'trace_edge_index':edge['index'],'axis':edge['axis'],'before_coordinate_m':edge['coordinate'],
                           'after_coordinate_m':chosen['coordinate'],'status':'mapped_to_outer_union_boundary',
                           'outer_boundary_span_m':[chosen['start'],chosen['end']],
                           'source_edge_indexes':chosen['source_edge_indexes']})
    points=[];point_audit=[]
    for index,point in enumerate(ring):
        x,x_mapping=_map_coordinate(float(point[0]),mappings['x']);y,y_mapping=_map_coordinate(float(point[1]),mappings['y'])
        distance=math.hypot(x-float(point[0]),y-float(point[1]))
        if distance>tolerance_m+_AXIS_EPS:raise ValueError(f'trace vertex {index} final displacement {distance}m exceeds boundary snap tolerance')
        after=[x,y];points.append(after)
        point_audit.append({'kind':'trace_polygon_vertex','index':index,'before':list(map(float,point)),'after':after,
                            'displacement_m':distance,'x_mapping':None if x_mapping is None else x_mapping['to_coordinate_m'],
                            'y_mapping':None if y_mapping is None else y_mapping['to_coordinate_m']})
    return points,mappings,edge_audit,point_audit


def normalize_trace_point(point,mappings,tolerance_m,*,kind,index):
    """Apply only the ring's shared-coordinate maps to an aperture endpoint."""
    x,x_mapping=_map_coordinate(float(point[0]),mappings['x']);y,y_mapping=_map_coordinate(float(point[1]),mappings['y'])
    distance=math.hypot(x-float(point[0]),y-float(point[1]))
    if distance>tolerance_m+_AXIS_EPS:raise ValueError(f'{kind} {index} final displacement {distance}m exceeds boundary snap tolerance')
    return [x,y],{'kind':kind,'index':index,'before':list(map(float,point)),'after':[x,y],'displacement_m':distance,
                       'x_mapping':None if x_mapping is None else x_mapping['to_coordinate_m'],
                       'y_mapping':None if y_mapping is None else y_mapping['to_coordinate_m']}


def _self_check():
    region=unary_union([box(0,0,2,2),box(2,0,4,2)])
    ring=[[.03,.02],[3.97,.02],[3.97,1.98],[2.02,1.98],[2.02,1.2],[.03,1.2]]
    normalized,mappings,_edges,_points=normalize_trace_ring(ring,region,.05)
    assert normalized[1][0]==normalized[2][0]==4.0
    assert normalized[0][1]==normalized[1][1]==0.0
    assert normalized[3][0]==normalized[4][0]==2.02  # old internal partition is never a snap target
    door,audit=normalize_trace_point([3.97,.7],mappings,.05,kind='synthetic_door',index=0)
    assert door==[4.0,.7] and audit['x_mapping']==4.0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--seed',type=Path,default=ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run04/candidate_01')
    parser.add_argument('--space-id',default='BottomRightOffice');parser.add_argument('--neighbor-id',default='Corridor')
    parser.add_argument('--boundary-snap-m',type=float,default=0.05)
    parser.add_argument('--self-check',action='store_true')
    args=parser.parse_args()
    if args.self_check:
        _self_check();print('synthetic outer-boundary normalization check passed');raise SystemExit
    if args.observation is None or args.out is None:parser.error('--observation and --out are required unless --self-check')
    out=args.out.resolve();out.mkdir(exist_ok=False)
    if not 0 <= args.boundary_snap_m <= .2:raise ValueError('boundary snap must be explicit, between 0 and 0.2m')
    child=args.observation.resolve()/'detail_01'
    selection=json.loads((child/'trace_selection.json').read_text())
    path=child/'space_traces'/f"{selection['trace_id']}.json"
    assert digest(path)==selection['trace_sha256']
    trace=json.loads(path.read_text());assert trace['geometrically_executable']
    proposal=json.loads((args.seed/'proposal.json').read_text())
    ids={args.space_id,args.neighbor_id}
    floors=[f for f in proposal['geometry']['floors'] if ids <= {c['id'] for c in f['cells']}]
    assert len(floors)==1
    cells={c['id']:c for c in floors[0]['cells']};region=unary_union([shape(cells[i]) for i in ids])
    # Only whole axis-aligned edges may map to the exterior of this two-space
    # union. The old shared partition is not present in `outer_boundary_runs`.
    # No footprint clipping or hidden coordinate edits occur here.
    ring,coordinate_mappings,edge_mappings,point_mappings=normalize_trace_ring(
        trace['world_polygon'],region,args.boundary_snap_m)
    refs=[f"{trace['name']}:{selection['trace_id']} model-selected complete room contour; trace sha256 {selection['trace_sha256']}"]
    operations=[{'op':'replace_space_region','space_id':args.space_id,'neighbor_space_id':args.neighbor_id,
                 'polygon':ring,'reason':'Apply independently model-traced complete room contour; compute neighbor as old-union remainder.',
                 'source_refs':refs}]
    reshaped=apply_proposal_edits(proposal,operations)
    newcells={c['id']:c for f in reshaped['geometry']['floors'] for c in f['cells']}
    target=shape(newcells[args.space_id]);neighbor=shape(newcells[args.neighbor_id])
    trace_internal=[];opening_mappings=[]
    for o in trace['world_openings']:
        p,p_audit=normalize_trace_point(o['p1'],coordinate_mappings,args.boundary_snap_m,
                                        kind='trace_opening_endpoint',index=f"{o['id']}:p1")
        q,q_audit=normalize_trace_point(o['p2'],coordinate_mappings,args.boundary_snap_m,
                                        kind='trace_opening_endpoint',index=f"{o['id']}:p2")
        opening_mappings.extend([p_audit,q_audit])
        line=LineString([p,q])
        if not target.boundary.buffer(1e-6).covers(line):
            raise ValueError(f"traced opening {o['id']} no longer lies on the normalized target boundary")
        if target.boundary.buffer(1e-6).covers(line) and neighbor.boundary.buffer(1e-6).covers(line):
            trace_internal.append({'id':o['id'],'p1':p,'p2':q})
    source_internal=[o for o in proposal['geometry']['openings'] if {o['space_id'],o.get('other_space_id')}==ids]
    assert len(trace_internal)==len(source_internal)==1, 'Local replay requires one unambiguous existing/observed shared door; otherwise explicit identity mapping needed.'
    old=source_internal[0];new=trace_internal[0]
    operations.append({'op':'update_opening','id':old['id'],'changes':{'p1':new['p1'],'p2':new['p2']},
                       'reason':'Place the existing shared door on the traced aperture jamb segment, preserving height/state and identity.', 'source_refs':refs})
    # Unchanged aperture geometry may transfer from the compensating corridor
    # to the enlarged room. Only remap when exactly one new boundary covers it.
    for opening in proposal['geometry']['openings']:
        if opening['id']==old['id']:continue
        line=LineString([opening['p1'],opening['p2']]);changes={}
        for field in ['space_id','other_space_id']:
            if opening.get(field) not in ids:continue
            matches=[i for i in ids if shape(newcells[i]).boundary.buffer(1e-6).covers(line)]
            if opening[field] in matches:continue
            assert len(matches)==1,f"Cannot preserve/rehost {opening['id']} without more observed evidence"
            changes[field]=matches[0]
        if changes:
            operations.append({'op':'update_opening','id':opening['id'],'changes':changes,
                'reason':'The unchanged aperture segment belongs to the newly traced room after local spatial redistribution; physical geometry preserved.',
                'source_refs':list(dict.fromkeys(opening.get('source_refs',[])+refs))})
    result=apply_proposal_edits(proposal,operations)
    result['assumptions'].append(f"Local trace {selection['trace_id']} uses model-observed image calibration; existing two-space outer boundary reconciled within {args.boundary_snap_m}m. Old notes retained; trace does not certify remaining partitions.")
    result['unresolved'].append('Model calibration remains unverified and representative wall faces retain observed pixel-scale reference-plane differences; bounded exterior normalization does not certify either calibration or drawing fidelity.')
    result['unresolved'].append('East-side partitions and other opening geometry remain unverified; new local contour/apertures need independent original-image evaluation.')
    shutil.copytree(child/'images',out/'images')
    shutil.copy2(path,out/'selected_trace.json');shutil.copy2(path.with_suffix('.png'),out/'selected_trace.png')
    manifest=json.loads((child/'inputs.json').read_text())
    application_sources=[
        Path('AI_agent/logs/experiments/2026-09-13_space_trace_setup/apply_trace.py'),
        Path('src/agent/geometry/proposal_edits.py'),
        Path('scripts/tool_scripts/run_bim_agent.py'),
    ]
    implementation_dir=out/'implementation';implementation_dir.mkdir()
    for source in application_sources:shutil.copy2(ROOT/source,implementation_dir/source.name)
    manifest.update(
        input_mode='developer_orchestrated_local_trace_replay',
        only_input='selected original image, selected model trace, and the named source proposal for deterministic replay; no developer coordinates or GT',
        scope='Two selected source IDs, model-observed pixel contour and bounded existing-union-boundary normalization; no developer coordinates or GT',
        observation_run={'absolute_path':str(args.observation.resolve()),'trace_id':selection['trace_id'],
                         'trace_sha256':selection['trace_sha256']},
        seed={'source':str(args.seed),'proposal_sha256':digest(args.seed/'proposal.json')},
        application_implementation_sha256={str(source):digest(ROOT/source) for source in application_sources},
    )
    manifest.pop('deadline_epoch',None);dump(out/'inputs.json',manifest)
    export_source_proposal(proposal,out/'seed',provenance=manifest['seed'])
    all_point_mappings=[*point_mappings,*opening_mappings]
    dump(out/'normalization_audit.json',{
        'mode':'whole_axis_edge_to_outer_union_boundary',
        'boundary_snap_tolerance_m':args.boundary_snap_m,
        'coordinate_mappings':coordinate_mappings,
        'edge_mappings':edge_mappings,
        'point_mappings':all_point_mappings,
        'max_final_displacement_m':max([row['displacement_m'] for row in all_point_mappings],default=0),
        'outer_boundary_only':True,
        'not_snapped_to_old_internal_partition':True,
        'no_footprint_clipping_or_cropping':True,
        'opening_endpoints_use_trace_coordinate_mappings':True,
    })
    dump(out/'operations.json',operations)
    toolkit=Toolkit(out);report=toolkit.build(result,action='apply_selected_trace',parent='seed',operations=operations)
    if not (out/report['candidate']/'source_model.json').exists():raise RuntimeError(report)
    toolkit.project_overlay(report['candidate'],trace['name'],floors[0]['name'],trace['x_anchors'],trace['y_anchors'],trace['basis'],trigger_action='post_application_local_trace_projection')
    delivery=toolkit.delivery(report['candidate'],selection_origin='developer_selected_deterministic_trace_replay',generation_status={'state':'completed','agent_response_completed':False})
    dump(out/'summary.json',{'input_mode':manifest['input_mode'],'agent_response_completed':False,'deterministic_application_completed':True,'has_viewable_candidate':True,'delivery':{'candidate':report['candidate'],'selection_origin':delivery['selection_origin']},'counts':report['counts'],'model_invocations_in_application':0,'drawing_fidelity':'not_evaluated'})
    print(json.dumps({'candidate':report['candidate'],'counts':report['counts'],
                      'normalization_count':sum(row['before']!=row['after'] for row in all_point_mappings),
                      'operations':[o['op'] for o in operations]},indent=2))
