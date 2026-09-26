"""Independent six-door original-pixel spot check; never admitted to generation."""
import argparse
import json
from pathlib import Path

from PIL import Image
from scipy.optimize import linear_sum_assignment
from shapely.geometry import LineString, Point, Polygon

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUT = HERE / 'internal_door_reference'
# Endpoints use a representative wall midline reviewed on the original crop.
# Seeds describe visible space on each side without assuming generated room IDs.
SAMPLES = [
    dict(id='f1_north', floor='F1', image='1f_view.png', crop=[450,410,600,540],
         p1=[529,492.5], p2=[565,492.5], seeds=[[600,420],[600,530]],
         subject='Northern middle room to corridor, single leaf'),
    dict(id='f1_east', floor='F1', image='1f_view.png', crop=[750,305,855,420],
         p1=[793,349], p2=[793,386], seeds=[[875,357],[760,357]],
         subject='Top small eastern room to corridor, single leaf'),
    dict(id='f1_south', floor='F1', image='1f_view.png', crop=[755,1015,905,1120],
         p1=[793,1053], p2=[866,1053], seeds=[[825,1150],[825,1020]],
         subject='Southwestern meeting room to corridor, double leaf'),
    dict(id='f2_west', floor='F2', image='2f_view.png', crop=[575,590,695,740],
         p1=[651,630], p2=[651,703], seeds=[[560,670],[695,670]],
         subject='Western elongated meeting room to corridor, double leaf'),
    dict(id='f2_north', floor='F2', image='2f_view.png', crop=[675,450,790,565],
         p1=[704,522], p2=[742,522], seeds=[[820,450],[720,550]],
         subject='Northeastern large room to corridor, single leaf'),
    dict(id='f2_south', floor='F2', image='2f_view.png', crop=[1180,1035,1290,1145],
         p1=[1217,1077.5], p2=[1255,1077.5], seeds=[[1290,1150],[1230,1040]],
         subject='Southeastern office to corridor, single leaf'),
]


def save_reference():
    original = ROOT / 'case_tests/e2e_tests/sm25-L_anchor/case_data'
    reference = dict(samples=SAMPLES, endpoint_tolerance_pixels=6, width_tolerance_pixels=6,
        image_sha256={n:digest(original/n) for n in {'1f_view.png','2f_view.png'}},
        basis='Developer original-image review; approximate representative wall midlines and visible jambs. Crop images are clean originals enlarged 3x.',
        scope='Six development-selected internal doors only, not all internal doors or completeness, heights, stairs or global corridor continuity.',
        isolation='Reference and evaluation are not supplied to the product model.',
        calibration_limit='Uses each generated floor plan calibration for reprojection; not an independent metric calibration test.')
    dump(OUTPUT/'reference.json',reference)
    for row in SAMPLES:
        box=row['crop']
        with Image.open(original/row['image']) as im:
            im.crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3), Image.Resampling.NEAREST).save(OUTPUT/f"{row['id']}.png")
    return reference


def audit(run, reference):
    load=lambda p:json.loads(p.read_text())
    assert (run/'summary.json').is_file(), 'Generation must be finished'
    delivery=load(run/'delivery.json'); source=load(run/delivery['candidate']/'source_model.json')
    assert source['source_model_sha256']==delivery['source_model_sha256']
    binding=source['generation']['provenance']['plan_assembly']
    assert digest(run/binding['file'])==binding['sha256']
    assembly=load(run/binding['file']); plans={}
    for floor in assembly['floors']:
        path=run/'plan_drafts'/floor['draft_id']/'plan.json'
        assert digest(path)==floor['expected_plan_sha256']
        assert digest(run/'images'/floor['image'])==reference['image_sha256'][floor['image']]
        plans[floor['floor_id']]=load(path)
    spaces={s['id']:s for s in source['spaces']}; rows=[]
    for floor,plan in plans.items():
        def transform(p,inverse=False):
            result=[]
            for coord,key in zip(p,['x_anchors','y_anchors']):
                (pixel0,world0),(pixel1,world1)=plan[key]
                slope=(world1-world0)/(pixel1-pixel0)
                result.append((coord-world0)/slope+pixel0 if inverse else (coord-pixel0)*slope+world0)
            return result
        observations=[r for r in SAMPLES if r['floor']==floor]
        doors=[d for d in source['openings'] if d['kind']=='door' and not d['exterior'] and
               all(spaces[s]['floor_id']==floor for s in d['space_ids'])]
        lines=[LineString(list(dict.fromkeys(tuple(transform(v[:2],True)) for v in d['vertices']))) for d in doors]
        targets=[LineString([r['p1'],r['p2']]) for r in observations]
        costs=[[a.hausdorff_distance(b) for b in lines] for a in targets]
        assert len(doors)>=len(observations), 'Too few doors for selected sample'
        for i,j in zip(*linear_sum_assignment(costs)):
            sample,door=observations[i],doors[j]
            memberships=[[s['id'] for s in spaces.values() if s['floor_id']==floor and
                Polygon(s['polygon']).contains(Point(transform(seed)))] for seed in sample['seeds']]
            expected_ids={ids[0] for ids in memberships if len(ids)==1}
            connections=[c for c in source['connections'] if c['opening_id']==door['id']]
            geometry_ok=costs[i][j]<=reference['endpoint_tolerance_pixels'] and abs(targets[i].length-lines[j].length)<=reference['width_tolerance_pixels']
            connection_ok=(all(len(ids)==1 for ids in memberships) and len(expected_ids)==2 and
                set(door['space_ids'])==expected_ids and len(connections)==1 and
                set(connections[0]['space_ids'])==expected_ids and not connections[0]['exterior'])
            rows.append(dict(sample_id=sample['id'],opening_id=door['id'],original_pixel_segment=list(lines[j].coords),
                endpoint_hausdorff_pixels=costs[i][j],width_error_pixels=abs(targets[i].length-lines[j].length),
                geometry_match=bool(geometry_ok), seed_space_memberships=memberships,
                opening_space_ids=door['space_ids'],connection_match=bool(connection_ok),
                connection_state=connections[0]['state'] if len(connections)==1 else None,
                pass_sample=bool(geometry_ok and connection_ok)))
    report=dict(run=run.name,candidate=delivery['candidate'],source_sha256=source['source_model_sha256'],
        reference_sha256=digest(OUTPUT/'reference.json'),samples=rows,passed=sum(r['pass_sample'] for r in rows),
        sample_count=len(rows),all_selected_samples_pass=len(rows)==len(SAMPLES) and all(r['pass_sample'] for r in rows),
        limits=[reference['scope'],reference['calibration_limit'], 'Connection endpoint identities checked; open/closed operational state remains as recorded, not inferred.'])
    dump(OUTPUT/f'{run.name}.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path,nargs='?')
    args=parser.parse_args();reference=save_reference()
    if args.run: audit(args.run.resolve(),reference)
