"""Freeze reviewed opening/roof evidence and revise hypothetical storeys in window gaps."""
from pathlib import Path
import hashlib, json, re

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-09-15_voimatalo_developer_walkthrough'
def read(p):return json.loads(p.read_text())
def write(p,x):
    assert not p.exists(), 'Do not overwrite frozen assembly inputs'
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

plan=read(HERE/'roof_plan.json')
# Actual section feedback exposed the short courtyard setback as well. Keep the
# continuous core inside the final outline; intersect the hypothetical service
# room with this outline during assembly, rather than shifting observed windows.
plan['attic_outline']=[[-11.6,-31.5],[-.1,-31.5],[-.1,9.5],[6.5,9.5],[6.5,12.7],[18.5,12.7],
                       [18.5,24],[-12.8,24],[-12.8,16],[-11.6,16]]
plan['roof_volumes']['ROOF']['rectangles']=[[-11,-31.3,.8,-20.8],[-11,-20.8,-.1,10],
                                         [-10.8,10,6.5,23.6],[6.5,12.7,16.8,23.6],[-12.6,16,-10.8,23.6]]
plan['attic_feedback_revision']={'source_refs':['roof/sections.json:z26.5,z27.9','roof/court_short.png','roof/initial_window_queries.json'],
    'before':read(HERE/'roof_plan.json')['attic_outline'],'after':plan['attic_outline'],
    'reason':'Short-wing upper inner face visibly retreats to y about12.7 for x>6.5; old normal-storey y8.8 extends into courtyard. Corner retains y9.5 supporting three measured windows. Service-room clipping is an explicit change to the interior hypothesis; no observed opening is clipped.'}
obs=read(OLD/'assembly_observations.json')
add=read(HERE/'openings/assembly_windows.json')
actions=read(HERE/'openings/opening_actions.json')
obs['openings']+=add['openings']
obs['completion_actions']=actions
obs['roof_opening_decisions']=read(HERE/'roof/opening_decisions.json')
obs['inherited_evidence_root']=str(OLD)
obs['new_evidence_root']=str(HERE/'openings')
obs['completion_source_sha256']=hashlib.sha256((HERE/'openings/assembly_windows.json').read_bytes()).hexdigest()
oldmap={r['id']:r for r in read(OLD/'candidate_02/opening_mapping.json')}
heights={n:[] for n in range(1,9)}
for row in obs['openings']+plan['additional_openings']:
    owner=row.get('space_id',oldmap.get(row['id'],{}).get('owner',''))
    match=re.match(r'F([1-8])_',owner)
    number=int(match.group(1)) if match else (8 if row['id'].startswith('attic_') else None)
    if number is not None:heights[number].append(row)
levels=list(plan['storey_levels_m']);changes=[]
for n in range(2,8):
    below=heights[n];above=heights[n+1]
    lo=max(r['z_m'][1] for r in below);hi=min(r['z_m'][0] for r in above)
    assert hi-lo>.1, f'No supported inter-row gap at F{n}/F{n+1}; do not clip windows'
    old=levels[n]
    selected=old if lo+.05<=old<=hi-.05 else round((lo+hi)/2,2)
    assert lo+.04<selected<hi-.04
    levels[n]=selected
    changes.append({'interface':f'F{n}/F{n+1}','previous_z_m':old,'selected_z_m':selected,
        'observed_clear_gap_m':[lo,hi],
        'lower_constraint_ids':[r['id'] for r in below if abs(r['z_m'][1]-lo)<1e-6],
        'upper_constraint_ids':[r['id'] for r in above if abs(r['z_m'][0]-hi)<1e-6],
        'reason':'Keep existing level if it lies inside observed gap; otherwise choose gap midpoint. Slab remains inferred, not measured. No observed opening moved or trimmed.'})
plan['storey_levels_m']=levels
plan['storey_basis']='Eight storeys retained. Interfaces F2/F3 through F7/F8 re-estimated from full nonstandard windows and neighbouring row gaps; actual slabs remain unknown. F1 top and roof base unchanged.'
plan['storey_revision']=changes
for action in actions['door_actions']:
    assert action['operation']=='replace_metadata_keep_geometry'
    row=next(r for r in plan['inferred_entrances'] if r['id']==action['id'])
    assert row['span_m']==action['span_m'] and row['z_m']==action['z_m']
    row['source_refs']=[str(HERE/'openings'/p) for p in action['source_refs']]
    row['note']=action['decision']
plan['assumptions'][2]='主体仍按八层；普通层界线结合完整例外大窗与相邻窗排间隙重新估计。实际楼板位置未测得；原244窗保持坐标，假设内门随新层底平移，外门不动。'
plan['assumptions'].append('新增例外窗按逐层可见重复估测，凹入/起伏表面规整到主墙；残缺窗允许明确的同列重复推断。38个新增窗表达的已见/推断部分分别留证，数量不代表全楼窗完整率。')
plan['unresolved']=[
 '首层西侧补入可见店面玻璃，原西入口保留且新增纹理依据；窗/玻璃门细分类、远端暗面、北侧与内院首层缺扫描处仍未知。',
 '退台西面局部玻璃、角部竖窗及屋顶主要高低体量已处理；西/北暗带、金属小槽和局部残片的开口语义仍未确定。弧面、坡度和局部突出仍为屋盖棱柱简化。',
 '原单体裁剪缺失的两短端及局部凸出体仍保留未知；未使用父瓦片补出实际窗洞。',
 '内部房间、服务分隔、交通核心和内门仍为方案假设；没有真实内部参照。八层楼板按窗间空隙调整，不是实测楼层标高。',
 '例外窗包含重复推断与表面规整；残窗补全及旧短内院G02最低排下沿仍有不确定性，不能以开口全部装配成功宣称全楼窗完整。',
 '实际地面坡度、入口门槛及门类、屋盖构造和内部交通实体未验证；未开展后端模拟。',
 '原九条例外逐项处理、新首层剩余未知及六条退台/屋顶取舍保存在源provenance.aperture_input_metadata。原始未决记录保留，新增决策不改写历史观察。',
]
write(HERE/'case_plan.json',plan)
write(HERE/'assembly_observations.json',obs)
write(HERE/'storey_revision.json',{'levels_before_m':read(HERE/'roof_plan.json')['storey_levels_m'],'levels_after_m':levels,
    'interfaces':changes,'unchanged_window_ids':list(oldmap),
    'door_change_policy':'32 hypothetical internal doors keep XY/width/height, shift base with their declared storey. Two exterior door geometries retained.',
    'method':'Developer interpretation + deterministic interval arithmetic; frozen previous source is recovery input, not GT.'})
print(json.dumps({'levels':levels,'new_main_windows':len(add['openings'])},ensure_ascii=False))
