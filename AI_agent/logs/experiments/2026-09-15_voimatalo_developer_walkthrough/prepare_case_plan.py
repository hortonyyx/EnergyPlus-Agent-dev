"""Record this developer's case decisions separately from deterministic assembly."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation

out = HERE / 'case_plan.json'
assert not out.exists()
direction = json.loads((HERE / 'evidence_01/direction.json').read_text())
mesh = MeshObservation(ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb')
shell = {'west': -13.7, 'north': 26.2, 'court_long': .8, 'court_short': 8.8,
         'court_step_x': 4.6, 'court_corner_y': 9.5, 'east_end': 19.5, 'south_end': -33.4,
         'annex_east': 13.1, 'annex_south': -21.7, 'annex_roof': 6.7,
         'attic_west': -12.7, 'attic_north': 25.2, 'attic_east_end': 18.5, 'attic_south_end': -32.4}
additional, query_records = [], []
specs = [
    ('roof_court', 'court_long', [(393,431),(449,490),(503,541),(557,597),(613,653),(710,748),(766,803)], [(90,124)]),
    ('annex_east', 'annex_east', [(96,174),(201,277),(299,382),(409,485),(516,597),(624,701),(730,807),(837,912),(945,1014)], [(133,177),(234,282)]),
]
for name, view, groups, rows in specs:
    prefix = HERE / 'additional_views' / name
    meta = json.loads(prefix.with_suffix('.json').read_text())
    mapping = meta['pixel_center_mapping']
    origin, dx, dy = [np.array(mapping[k]) for k in ('top_left_pixel_center_plane_xyz', 'column_step_world_xyz', 'row_step_world_xyz')]
    picture = Image.open(prefix.with_suffix('.png')).convert('RGB')
    draw = ImageDraw.Draw(picture)
    for row_index, (top, bottom) in enumerate(rows):
        for index, (left, right) in enumerate(groups):
            oid = f'{name}_row{row_index+1}_{index+1:02}'
            if name == 'annex_east' and row_index == 1 and index == 4:
                draw.rectangle((left,top,right,bottom), outline='orange', width=3)
                draw.text((left,top-13), 'ENTRY?', fill='orange')
                query_records.append({'id':oid, 'decision':'Proposed glazed entrance instead of a window; class and threshold are unverified.', 'pixel_box':[left,top,right,bottom]})
                continue
            a, b = origin + left*dx + top*dy, origin + right*dx + bottom*dy
            point = [round((left+right)/2), round((top+bottom)/2)]
            query = mesh.pixel_query(prefix, [point])
            query_records.append({'id': oid, 'query': query})
            additional.append({'id':oid, 'view':view, 'pixel_box':[left,top,right,bottom],
                'span_m': sorted([float(a[1]),float(b[1])]), 'z_m':sorted([float(a[2]),float(b[2])]),
                'basis':'development_assistant_visible_glazing_group_estimate',
                'notes':'New raw-asset observation; box estimates glazing groups, not individual sashes. Ground-level class/hidden extent and roof curvature remain uncertain.',
                'source_refs':[f'additional_views/{name}.png', f'additional_views/{name}.json'], 'hit_check':query['queries']})
            draw.rectangle((left,top,right,bottom), outline='#10dd8a', width=2)
            draw.text((left,top-13), str(index+1), fill='#10dd8a')
    picture.save(HERE / 'additional_views' / (name+'_marked.png'))
(HERE / 'additional_views/aperture_queries.json').write_text(json.dumps(query_records, ensure_ascii=False, indent=2)+'\n')
plan = {
 'schema':'voimatalo_developer_case_decisions_v1',
 'mode':'developer exploration, new source assembly; not working-model success or blind cold start',
 'mesh_frame':{'mesh_sha256':mesh.mesh_sha256,'yaw_degrees':direction['used_yaw_degrees'], 'translation_m':[0,0,0],
     'reason':'Area-weighted orthogonal direction family from original mesh, disambiguated by developer inspection of asymmetric whole L shape. Approximate frame, not survey truth.',
     'source_refs':['evidence_01/direction.json','evidence_01/top.png']},
 'shell':shell,
 'shell_basis':{'measured_regularised':['west','north','court_long','court_short','annex_east','annex_south','annex_roof','attic_west','attic_north'],
     'measurement_reference':'wall_measurements/: selected near-vertical surface distributions; measured values retained separately',
     'inferred_end_closures':['east_end','south_end','attic_east_end','attic_south_end'],
     'end_note':'Short ends are incomplete in original sections; approximate logical closures inferred from remaining ends/roof, rendered as unknown enclosure. No party-wall or blank-facade truth claim.',
     'corner_note':'Inner short facade includes a shallower segment near x0.8..4.6, regularised to y9.5; main segment y8.8. Breakpoint is an estimate, needs opening-host review.'},
 'storey_levels_m':[0,5.6,8.8,12.0,15.2,18.4,21.6,24.8,27.8],
 'storey_basis':'Declared eight storeys plus six similar visible office window rows; 3.2m repeated pitch, ground and attic levels are explicit estimates, not surveyed slabs.',
 'inferred_core_rectangles':{'CORE_S':[-2.4,-27.4,.8,-23.7], 'CORE_N':[.8,9.5,4.6,14.4]},
 'inferred_service_rectangles':{'services_s':[-5.7,-27.4,-2.4,-23.7], 'services_n':[4.6,8.8,8.2,13.4]},
 'interior_basis':'One possible moderately simplified office/circulation/service scheme. One connected L-shaped open tenant space per main storey; no orientation-derived splits. Core positions and service partitions are inferred, actual room layout unavailable.',
 'roof_primary_rectangles':[[-11,-31,-1,-22],[-12.5,-22,-4.5,11],[-9,11,16,23]],
 'roof_primary_top':30.0,
 'roof_upper_volumes':{
     'ROOF_N':{'rectangle':[-4,12,7,17], 'z':[30,32.1], 'evidence':'Northern raised roof box from whole views and actual courtyard pixel hit near(-2.95,14.42,31.98). Extents regularised developer estimates.'},
     'ROOF_STACK':{'rectangle':[-6,-26,-4,-24], 'z':[30,34.2], 'evidence':'Visible southern rooftop stack; actual courtyard pixel hits near(-5.01,-25.19,34.02). Square prism approximates round/irregular stack; not an occupied room.'}},
 'additional_openings':additional,
 'inferred_entrances':[
     {'id':'D_entry_west','space_id':'F1_open','axis':0,'plane_key':'west','span_m':[-16,-14.4],'z_m':[0,2.8],
      'source_refs':['additional_views/ground_west.png'], 'note':'Ground entrance hypothesis near a visible glazing break; exact door class, threshold and extent not verified.'},
     {'id':'D_entry_annex','space_id':'ANNEX_open','axis':0,'plane_key':'annex_east','span_m':[-8.2,-6.1],'z_m':[0,2.8],
      'source_refs':['additional_views/annex_east.png: lower central glazed bay'], 'note':'Central lower glazed bay treated as an entrance hypothesis instead of a window; actual door class and threshold unknown.'}],
 'assumptions':[
     '开发助手从原单体GLB和声明重新装配的部分推理草稿；已有历史上下文，不是Sonnet达标案例。',
     '主要外墙、低体屋顶和退台面按选定原三角面量测规整，米制坐标与窗框转换交代码执行；窗口是可见窗组的估测与显式重复，不是逐窗扇实测。退台墙面支持稀疏，完整延展轮廓仍结合屋顶外形推断，不能把采样跨度当连续实测墙段。',
     '主体按八层；六个标准办公层采用约3.2m层高，首层5.6m、退台层3.0m及绝对楼板标高仍为假设。',
     '内部采用一种连续L形开放办公/商业空间，加两处服务空间及两处连续竖向交通核心的方案。实际房间布局、核心位置、用途和全部内门均未被外网格证实。',
     '两交通核心跨0–27.8m连续表达，仅有底/顶边界；每层连接门为方案假设，不建立逐层堵死核心的假楼板，也不绘制未证实的楼梯/电梯。',
     '低层附属体保留一个合并空间；两排窗不推导为两层。它与主楼的接触分隔是假设，内部连通未知。',
     '缺失短端和南核心临内院缺面用未知围护显示；未借用旧父瓦片的贴邻建筑或交通盒结论。',
     '弧形/坡形屋顶简化为有明确用途限制的屋盖体量；屋顶轮廓、高度变化和窗仍未全部精修，不能称完整屋顶保真。'],
 'unresolved':[
     '沿街首层的窗/玻璃门尚未逐组完成；当前仅两处明确标为假设的入口，不能称首层开口完整。',
     '退台西、北侧及其它屋顶开口未完整建入；屋顶曲率、局部体量和端部尺寸需要继续原网格核对。',
     '原单体裁剪缺失的两短端及局部凸出体只能保留未知/推断；实际窗洞和围护未确认。',
     '内部房间、服务分隔、交通核心位置和门都为方案假设；没有真实内部参照，不报告实际房间恢复率。',
     '立面窗组规则化/角部例外与阴影低质区域仍有不确定性；观察完整性需逐面继续复核。',
     '实际地面坡度、入口门槛和精确楼板位置未验证；未开展后端模拟。']}
out.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'additional_window_groups':len(additional), 'plan':str(out)}))
