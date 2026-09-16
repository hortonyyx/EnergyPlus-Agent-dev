"""Fixed raw sections versus actual source unions; descriptive, not full fidelity score."""
from pathlib import Path
import argparse, json
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--candidate',type=Path,default=HERE/'candidate_03')
parser.add_argument('--out',type=Path,default=HERE/'roof_comparison')
args=parser.parse_args();args.out.mkdir(exist_ok=False)
old=json.loads((HERE.parent/'2026-09-15_voimatalo_developer_walkthrough/candidate_02/source_model.json').read_text())
new=json.loads((args.candidate/'source_model.json').read_text())
raw=json.loads((HERE/'roof/sections.json').read_text())
canvas=Image.new('RGB',(1440,1120),'white');d=ImageDraw.Draw(canvas)
d.text((20,10),'Raw mesh: blue | previous: red | revised source union: green. Equal XY scale; interiors NOT evaluated.',fill='black')
reports=[]
for i,row in enumerate(raw['sections']):
    z=row['z_m']; x0,y0=30+(i%3)*480,70+(i//3)*535
    def pt(p):return(x0+(p[0]+18)*7,y0+(30-p[1])*7)
    d.text((x0,y0-25),f'z={z:g}m (observation cut, NOT new floor)',fill='black')
    for x in range(-15,25,5):d.line([pt([x,-35]),pt([x,30])],fill='#ddd')
    for y in range(-35,31,5):d.line([pt([-18,y]),pt([24,y])],fill='#ddd')
    for s in row['segments']:d.line([pt(p) for p in s['endpoints_xyz_m']],fill='#1678af',width=2)
    mids=np.array([np.mean(s['endpoints_xyz_m'],axis=0) for s in row['segments']])
    weights=np.array([np.linalg.norm(np.diff(s['endpoints_xyz_m'],axis=0)) for s in row['segments']])
    rr={'z_m':z,'raw_segment_count':len(mids),'raw_trace_length_m':float(weights.sum())}
    for label,source,color in [('previous',old,'#c44b4b'),('revised',new,'#15924c')]:
        poly=unary_union([Polygon(s['polygon']) for s in source['spaces'] if s['z_floor']<=z<s['z_floor']+s['height']])
        parts=[poly] if poly.geom_type=='Polygon' else list(poly.geoms)
        for p in parts:
            d.line([pt(q) for q in p.exterior.coords],fill=color,width=2)
            for ring in p.interiors:d.line([pt(q) for q in ring.coords],fill=color,width=2)
        distances=[Point(m[:2]).distance(poly.boundary) for m in mids]
        rr[label]={'length_weighted_mean_raw_midpoint_to_source_outline_m':float(np.average(distances,weights=weights)),
                   'source_cross_section_area_m2':poly.area,'source_model_sha256':source['source_model_sha256']}
    reports.append(rr)
canvas.save(args.out/'sections.png')
(args.out/'report.json').write_text(json.dumps({'rows':reports,'scope':'Same fixed raw section segments and source unions; no fitting or source mutation.',
 'limitations':['One-way trace distance does not penalise added envelope where scan is missing.','Cuts do not evaluate roof caps between sample heights, openings, interior layout or complete building fidelity.',
 'Roof envelope remains a prism simplification of curved/stepped geometry.']},indent=2)+'\n')
(args.out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>屋顶剖切核对</title><h1>原网格与实际新旧源模型的同高剖切</h1><p>蓝：原网格；红：旧草稿；绿：新候选。相同比例，不做二次拟合。高度仅为诊断取样，不是楼板。</p><p>单向截线距离不处罚扫描缺口处多建的体量，不评价开口和内部，也不是整栋保真分数。屋盖仍为弧面简化。</p><a href="report.json">逐高度指标与限制</a><p><img style="max-width:100%" src="sections.png"></p>')
print(json.dumps(reports,indent=2))
