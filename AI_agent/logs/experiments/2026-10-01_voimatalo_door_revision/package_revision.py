"""Reuse the prior source viewer and expose the doorway revision for inspection."""
from __future__ import annotations
import html
import json
import runpy
import sys
from pathlib import Path

from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
PREVIOUS = HERE.parent / '2026-09-30_voimatalo_user_revision'


def plan(source, audit, output):
    """Saved-source plan; hinge/swing lines are explicitly illustrative hypotheses."""
    scale, margin = 16, 38
    def point(p):
        return margin+(p[0]+13.7)*scale, margin+(26.1-p[1])*scale
    def points(rows):
        return ' '.join(f'{x:.2f},{y:.2f}' for x,y in map(point, rows))
    from src.agent.roles import ROOM_TYPES
    floor = next(f for f in source['floors'] if f['id'] == 'F3')
    rooms = [s for s in source['spaces'] if s['floor_id'] == 'F3' or s['id'] in floor['spanning_space_ids']]
    ids = {s['id'] for s in rooms}
    body = []
    for s in rooms:
        poly = Polygon(s['polygon']); name = source['public_names']['spaces'][s['id']]
        body.append(f'<polygon points="{points(s["polygon"])}" fill="{ROOM_TYPES[s["role"]]["color"]}" fill-opacity=".5" stroke="#404040" stroke-width="1.3"><title>{html.escape(name)}</title></polygon>')
    # Draw apertures from source coordinates; only the hinge/leaf symbols come from audit.
    for o in source['openings']:
        if not ids.intersection(o['space_ids']):
            continue
        zs = [v[2] for v in o['vertices']]
        if min(zs) < 8.8-1e-6 or max(zs) > 12+1e-6:
            continue
        endpoints = list(dict.fromkeys(tuple(v[:2]) for v in o['vertices']))
        color, width = ('#2169ac', 3.6) if o['kind'] == 'window' else ('white', 4)
        body.append(f'<polyline points="{points(endpoints)}" stroke="{color}" stroke-width="{width}" fill="none"/>')
    for d in audit['changed_doors']:
        if d['floor'] != 'F3':
            continue
        sw = d['swing']
        title = html.escape(f'{d["room"]} → {d["after"]["other_space_id"]}; {d["pair"] or "single"}')
        body.append(f'<g stroke="#a75518" stroke-width="1.25" fill="none"><title>{title}</title><polyline points="{points(sw["arc_xy"])}"/><polyline points="{points(sw["leaf_open_xy"])}"/></g>')
    for s in rooms:
        center = Polygon(s['polygon']).representative_point(); x,y = point((center.x,center.y))
        label = s['id'].removeprefix('F3_')
        body.append(f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" dominant-baseline="middle" fill="#283440" font-size="9">{html.escape(label)}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 1030" style="max-height:90vh;max-width:95vw;background:white">{"".join(body)}</svg>'
    (output / 'F3_doors.svg').write_text(svg)
    (output / 'doors.html').write_text('''<!doctype html><html lang="zh"><meta charset="utf-8"><title>F3 房门布置 · 修订02</title>
<style>body{font:15px/1.7 sans-serif;background:#f2f4f6;color:#263442;margin:24px}main{display:flex;gap:28px;align-items:flex-start}aside{max-width:360px;position:sticky;top:24px}a{color:#175b9a}</style>
<main>''' + svg + '''<aside><h2>标准层 F3 · 房门布置</h2>
<p>相邻房间在隔墙两侧成对布门，门扇向各自房间内开。蓝色为窗；棕色为推断的门扇和开启弧。</p>
<p>本层19组成对房门、3樘端部／特殊接入单门。普通房门洞宽0.90 m，洞边距隔墙代表线0.25 m；这里未展开实体墙厚。</p>
<p>仅门扇／开启弧为查看示意，门洞、隔墙和窗来自同一份源模型。楼梯平台门和电梯门不套用普通房间规则。</p>
<p><a href="index.html">返回三维模型</a> · <a href="../door_layout.json">逐门调整记录</a></p></aside></main></html>''')


def main():
    output = HERE / 'result_02'
    source = json.loads((HERE / 'candidate_02/source_model.json').read_text())
    audit = source['generation']['provenance']['door_layout']
    package = runpy.run_path(str(PREVIOUS / 'package_revision.py'))['package']
    package(HERE / 'candidate_02', output, refresh='--refresh' in sys.argv)
    page = (output / 'index.html').read_text()
    page = page.replace('修订 01', '修订 02').replace('../candidate_01/', '../candidate_02/')
    page = page.replace('标准层主要一窗一间；前厅两层；楼梯、电梯井分开；顶层为阁楼及设备附属空间。',
                        '房门改为隔墙两侧成对布置、优先接走廊；两端无窗属推断；前厅交通保留。')
    page = page.replace('<a href="rooms.csv">房间类型与命名表</a>',
                        '<a href="rooms.csv">房间类型与命名表</a> · <a href="doors.html" target="_blank">F3门位平面</a>')
    page = page.replace('主楼标准层 3.2 m，普通窗台 1.2 m／窗高 1.6 m，主要尺寸按 50 mm 规整。',
                        '普通房门洞宽0.90 m，洞边距隔墙代表线0.25 m；相邻入口成对镜像，向房内开启（示意）。主楼标准层3.2 m。')
    old = "function boundaryEvidence(b,key){ return evidenceText([...(b&&b[key]||[]),...(b&&b.enclosure_regions||[]).flatMap(r=>r[key]||[])]); }"
    new = """function boundaryEvidence(b,key){
      const e=(SOURCE.generation.provenance.end_wall_inference||[]).find(e=>e.boundary_id===b?.id);
      return evidenceText([...(b&&b[key]||[]),...(b&&b.enclosure_regions||[]).flatMap(r=>r[key]||[]),...(e&&e[key]||[])]);
    }"""
    assert page.count(old) == 1
    page = page.replace(old, new)
    anchor = "    if(u.kind==='opening' && mode!=='zone') return"
    extra = r'''
    if(u.kind==='opening' && mode!=='zone'){
      const d=SOURCE.generation.provenance.door_layout.changed_doors.find(d=>d.id===u.sourceId);
      if(d) return '<div class="hh">推断房门</div>'+kv([
        ['名称',objectName(u.name)],['源开口 ID',u.sourceId],
        ['连接',spaceName(d.room)+' ↔ '+spaceName(d.after.other_space_id)],
        ['布置',d.pair?'隔墙双侧成对 · '+d.pair:'端部／特殊接入，靠墙留门垛'],
        ['成对房间',d.paired_space?spaceName(d.paired_space):'—'],
        ['门洞宽','0.90 m'],['洞边距隔墙代表线','0.25 m（推断预留）'],
        ['开启','向房内；仅示意，未指定实际五金'],['源房门 ID',d.id]]);
    }
'''
    assert page.count(anchor) == 1
    page = page.replace(anchor, extra+anchor)
    # Three.js raycasting itself ignores material clipping planes. Without this
    # filter an invisible clipped ceiling intercepts the click on a visible door.
    old_pick = 'const hits=raycaster.intersectObjects(allPickables().filter(m=>m.visible),false); return hits.length?hits[0]:null;'
    new_pick = 'const hits=raycaster.intersectObjects(allPickables().filter(m=>m.visible),false).filter(h=>activePlanes().every(p=>p.distanceToPoint(h.point)>=-0.0001)); return hits.length?hits[0]:null;'
    assert page.count(old_pick) == 1
    page = page.replace(old_pick, new_pick)
    page = page.replace("revisionView('whole');", "revisionView('standard');")
    (output / 'index.html').write_text(page)
    plan(source, audit, output)


if __name__ == '__main__':
    main()
