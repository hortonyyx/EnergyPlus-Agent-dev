"""Evaluation-only two-floor aperture correspondence; never imported by generation."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, Polygon

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.geometry.source_image_overlay import render_source_overlay

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent/'2026-09-26_sm21_whole_building_claude_run57'
load = lambda p: json.loads(p.read_text())


def save_reference():
    first = HERE.parent/'2026-09-23_sm21_cold_plan_setup/original_observations.json'
    f1 = load(first)
    image = ROOT/'case_tests/e2e_tests/sm21_anchor/case_data/2f_view.png'
    apertures = []
    def add(name, kind, axis, cross, span, hosts):
        apertures.append(dict(id=name,kind=kind,axis=axis,cross_pixel=cross,span_pixels=span,hosts=hosts))
    for name,span,host in [('NW',[607,940],'NW'),('NE',[1300,1633],'NE')]:
        add('window-'+name,'window','x',342.5,span,[host])
    for name,span in [('S1',[629,740]),('S2',[807,918]),('S3',[1322,1433]),('S4',[1500,1611])]:
        add('window-'+name,'window','x',1059.5,span,[name])
    for name,x in [('W',438),('E',1802)]:
        add('window-'+name,'window','y',x,[645,757],['C'])
    for name,span in [('NW',[1003,1086]),('NE',[1152,1236])]:
        add('door-'+name,'door','x',608.5,span,[name,'C'])
    for name,span in [('S1',[657,741]),('S2',[807,891]),('S3',[1350,1434]),('S4',[1500,1584])]:
        add('door-'+name,'door','x',793.5,span,[name,'C'])
    f2=dict(source_image=str(image.relative_to(ROOT)),source_sha256=digest(image),
        calibration=dict(x_anchors=[[427,0],[1813,15]],y_anchors=[[331,8],[1071,0]],
            basis='Original 15000/8000 mm overall extension endpoints; no candidate fitting.'),
        spaces=dict(NW=[700,450],NE=[1450,450],C=[1100,700],S1=[550,950],S2=[950,950],S3=[1250,950],S4=[1650,950]),
        apertures=apertures,tolerance=f1['tolerance'])
    reference=dict(floors=[f1,f2],prior_f1_reference_sha256=digest(first),
        isolation='Developer original-image review only, not model input. F2 recorded during generation before inspecting candidates.',
        basis='F2 full original viewed, cyan components and original grayscale wall edges inspected; representative midlines and visible jambs.',
        limits=['Approximate manual pixel observations, not surveyed geometry or an automated semantic judge.',
                'Interior seeds establish room identity, not complete room shape. Independent GT partition evaluated separately.',
                'No door height, operating state, material or vertical circulation claim.'])
    dump(HERE/'original_reference.json',reference)
    return reference


def audit(run=RUN):
    assert (run/'summary.json').is_file(), 'Wait for generation completion'
    ref=load(HERE/'original_reference.json'); delivery=load(run/'delivery.json')
    source=load(run/delivery['candidate']/'source_model.json')
    floors=sorted(source['floors'],key=lambda f:f['z_floor'])
    assert len(floors)==len(ref['floors'])==2
    output=run/'evaluation';output.mkdir(exist_ok=True)
    comparisons=[];floor_reports=[]
    for floor,obs in zip(floors,ref['floors']):
        name=Path(obs['source_image']).name
        assert digest(run/'images'/name)==obs['source_sha256']
        def coordinate(value,axis):
            (p0,v0),(p1,v1)=obs['calibration'][axis+'_anchors']
            return v0+(value-p0)*(v1-v0)/(p1-p0)
        spaces={s['id']:Polygon(s['polygon']) for s in source['spaces'] if s['floor_id']==floor['id']}
        identities={key:[sid for sid,poly in spaces.items() if poly.contains(Point(coordinate(p[0],'x'),coordinate(p[1],'y')))] for key,p in obs['spaces'].items()}
        actual=[]
        for opening in source['openings']:
            if not any(s in spaces for s in opening['space_ids']):continue
            xy=np.array(opening['vertices'])[:,:2];dim=int(np.argmax(np.ptp(xy,axis=0)))
            actual.append(dict(id=opening['id'],kind=opening['kind'],axis='xy'[dim],span=[float(xy[:,dim].min()),float(xy[:,dim].max())],cross=float(xy[:,1-dim].mean()),space_ids=opening['space_ids'],exterior=opening['exterior']))
        costs=np.full((len(obs['apertures']),len(actual)),1e6);metrics={}
        for i,r in enumerate(obs['apertures']):
            span=sorted(coordinate(v,r['axis']) for v in r['span_pixels']);cross=coordinate(r['cross_pixel'],'y' if r['axis']=='x' else 'x')
            for j,a in enumerate(actual):
                if (r['kind'],r['axis'])!=(a['kind'],a['axis']):continue
                along=max(abs(x-y) for x,y in zip(span,a['span']));across=abs(cross-a['cross'])
                costs[i,j]=along+across;metrics[i,j]=(along,across)
        matched_r=set();matched_a=set()
        for i,j in zip(*linear_sum_assignment(costs)):
            if costs[i,j]>=1e6:continue
            matched_r.add(int(i));matched_a.add(int(j));r=obs['apertures'][i];a=actual[j]
            along,across=metrics[i,j];hosts=sorted(s for h in r['hosts'] for s in identities[h]);resolved=all(len(identities[h])==1 for h in r['hosts']);exterior=len(r['hosts'])==1
            host_ok=resolved and len(set(hosts))==len(r['hosts']) and sorted(a['space_ids'])==hosts and a['exterior']==exterior
            connections=[c for c in source['connections'] if c['opening_id']==a['id']]
            connected=None if r['kind']!='door' else bool(host_ok and len(connections)==1 and sorted(connections[0]['space_ids'])==hosts and connections[0]['exterior']==exterior)
            tol=obs['tolerance'];position=along<=tol['along_m'] and across<=tol['external_cross_m' if exterior else 'internal_cross_m']
            comparisons.append(dict(floor_id=floor['id'],reference_id=r['id'],opening_id=a['id'],max_endpoint_error_m=along,perpendicular_error_m=across,position_match=bool(position),expected_hosts=hosts,actual_hosts=a['space_ids'],host_match=bool(host_ok),connection_match=connected))
        floor_reports.append(dict(floor_id=floor['id'],image=name,space_identity_by_interior_point=identities,unmatched_reference=[r['id'] for i,r in enumerate(obs['apertures']) if i not in matched_r],unmatched_actual=[a['id'] for i,a in enumerate(actual) if i not in matched_a]))
        with Image.open(run/'images'/name) as original:
            overlay,metadata=render_source_overlay(source,original.convert('RGB'),floor_id=floor['id'],image_name=name,**obs['calibration'])
        overlay.save(output/f'original_{name}');dump(output/f'original_{name}.json',metadata)
    report=dict(candidate=delivery['candidate'],reference_sha256=digest(HERE/'original_reference.json'),reference_count=sum(len(f['apertures']) for f in ref['floors']),matched=len(comparisons),positions=sum(r['position_match'] for r in comparisons),hosts=sum(r['host_match'] for r in comparisons),door_connections=sum(r['connection_match'] is True for r in comparisons),floors=floor_reports,comparisons=comparisons,limits=ref['limits'])
    dump(output/'original_openings.json',report)
    print(json.dumps({k:report[k] for k in ['candidate','reference_count','matched','positions','hosts','door_connections']},indent=2))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--reference-only',action='store_true');args=parser.parse_args()
    if args.reference_only:save_reference()
    else:audit()
