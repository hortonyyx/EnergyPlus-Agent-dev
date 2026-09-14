"""Freeze existing original-mesh renders and metric mappings; no BIM/room/window answers."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
OLD=ROOT/'AI_agent/logs/experiments/2026-09-10_showcase_textured_mass'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    images=OUT/'images';images.mkdir(exist_ok=False)
    inputs={}
    for group,prefix in [('input_views','overview'),('facade_views','facade')]:
        for path in sorted((OLD/group).glob('*.png')):
            target=images/(prefix+'_'+path.name)
            shutil.copy2(path,target)
            inputs[target.name]={'source':str(path.relative_to(ROOT)),'sha256':sha(path)}
    measurements=json.loads((OLD/'facade_views/measurements.json').read_text())
    mappings={}
    for name,m in measurements.items():
        lo,hi=m['along_range'];w=m['width_pixels'];h=m['height_pixels']
        x0,x1=(lo-1,hi+1) if m['along_pixel_direction']=='increasing' else (hi+1,lo-1)
        mappings['facade_'+name+'.png']={**m,'horizontal_world_axis':'y' if m['axis']==0 else 'x',
            'horizontal_pixel_to_m':{'offset':x0,'scale':(x1-x0)/w},
            'vertical_pixel_to_z_m':{'offset':m['top_z_m'],'scale':-m['view_height_m']/h},
            'selection_caveat':'Developer-selected near-plane triangles, within 1.25m; plane is an estimated reference, not a verified BIM wall. Selection may exclude projecting/recessed surfaces. Use overview for context.'}
    declaration={
        'building':'Voimatalo', 'location':'Helsinki',
        'use':'office with street-level commercial, from previously sourced input preparation',
        'storey_information':'Prior public record describes eight above-ground storeys including six similar office storeys and a setback upper storey; reconcile with visual evidence. Not actual surveyed slab levels.',
        'source_mesh':{'sha256':sha(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/input.glb'),
            'kind':'real photogrammetric textured mesh, metres, cropped to one building; not watertight'},
        'coordinate_frame':{'units':'metres','x':'cos(15deg)*GLB.x+sin(15deg)*GLB.z',
            'y':'sin(15deg)*GLB.x-cos(15deg)*GLB.z','z':'GLB.y',
            'note':'Developer-prepared 15 degree local alignment from prior exploration. North/East facade names in tools refer to local axes, not geographic north.'},
        'facade_image_mappings':mappings,
        'overview_camera':json.loads((OLD/'input_views/capture.json').read_text()),
        'simplification_intent':'Retain main shape, storeys, setbacks and visible aperture groups. Infer a useful, moderately detailed office/circulation/service-space scheme from available constraints. Do not make room counts a goal or split a continuous open space just by orientation. No internal plan is supplied; all interior partition/door hypotheses must be explicit.',
        'missing_information':['actual internal partitions and doors','precise storey/slab levels','occluded facade surfaces','stair/elevator details','complete ground-level entrance inventory'],
        'experiment_condition':'Exploratory working-model transfer with developer-prepared observations. No old BIM, window coordinates/counts or interior layout supplied. Cropped mesh context is limited; missing pixels do not prove either an opening or blank wall.'}
    (OUT/'building_input.json').write_text(json.dumps(declaration,ensure_ascii=False,indent=2)+'\n')
    (OUT/'preparation.json').write_text(json.dumps({'inputs':inputs,'building_input_sha256':sha(OUT/'building_input.json'),
        'model_calls':0,'old_generated_BIM_included':False,'manual_window_observations_included':False,
        'interior_plan_or_ground_truth_included':False},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
