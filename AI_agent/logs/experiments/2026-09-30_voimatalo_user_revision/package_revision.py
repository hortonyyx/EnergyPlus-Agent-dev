"""Case-local inspection controls; the shared viewer and source remain authoritative."""
from __future__ import annotations
import argparse
import csv
import json
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

FLOOR_HELPERS = r'''
  function revisionFloor(){
    const index=Number($('floorSel').value);
    return index<0 ? null : SOURCE.floors.find(f=>f.id===NAMED_FLOORS[index].id);
  }
  function revisionMember(u){
    const f=revisionFloor(); if(!f) return true;
    const sid=(SOURCE_MAP.zones||{})[u.zone]||u.zone;
    if(SOURCE_SPACES[sid]?.floor_id!==f.id && !(f.spanning_space_ids||[]).includes(sid)) return false;
    if(u.zmax!==undefined && (u.zmax<f.z_floor-0.001 || u.zmin>f.z_floor+f.height+0.001)) return false;
    return true;
  }
  function revisionDuplicate(u){
    if(!u.dup) return true;
    if(!revisionFloor()) return false;
    const bid=(SOURCE_MAP.surfaces||{})[u.name]||u.name;
    const b=SOURCE_BOUNDARIES[bid];
    if(!b) return false;
    return !(b.adjacent_space_ids||[]).some(sid=>revisionMember({zone:sid}));
  }
'''

CONTROLS = r'''
  function revisionView(name){
    TRANSFER.mode('bim');
    ['X','Y','Z'].forEach(axis=>{$('flip'+axis).checked=false;$('flip'+axis).dispatchEvent(new Event('change'));});
    $('colorBy').value='zone';$('colorBy').dispatchEvent(new Event('change'));
    let target=[0,-4,14], position=[77,-93,63];
    const fid={standard:'F3',annex1:'ANNEX_F1',annex2:'ANNEX_F2'}[name];
    if(fid){
      $('floorSel').value=NAMED_FLOORS.findIndex(f=>f.id===fid);
      $('floorSel').dispatchEvent(new Event('change'));
      const f=revisionFloor();
      $('enZ').checked=true;$('posZ').value=f.z_floor+Math.min(2.1,f.height-.3);
      $('enZ').dispatchEvent(new Event('change'));
      if(fid==='F3'){target=[0,-4,f.z_floor+1];position=[37,-48,f.z_floor+81];}
      else {target=[6.5,-6.2,f.z_floor+1];position=[43,-47,f.z_floor+43];}
    } else if(name==='street') {position=[-75,69,60];}
    else if(name==='roof') {
      $('enZ').checked=true;$('flipZ').checked=true;$('posZ').value=24.75;
      $('enZ').dispatchEvent(new Event('change'));target=[0,-3,28];position=[43,-43,75];
    } else if(name==='circulation') {
      $('floorSel').value=NAMED_FLOORS.findIndex(f=>f.id==='F3');$('floorSel').dispatchEvent(new Event('change'));
      $('enZ').checked=true;$('posZ').value=10.7;$('enZ').dispatchEvent(new Event('change'));
      target=[-2.5,-25.3,9.7];position=[13,-39,31];
    }
    camera.position.set(...position);controls.target.set(...target);controls.update();
    document.body.dataset.reviewView=name;
  }
  document.querySelectorAll('[data-review-view]').forEach(b=>b.onclick=()=>revisionView(b.dataset.reviewView));
  window.REVISION={view:revisionView,source:SOURCE,spaces:SOURCE_SPACES,floors:NAMED_FLOORS,
    meshes:surfMeshes,windows:winMeshes,doors:openingMeshes,
    stats:()=>({mode:document.body.dataset.mode,view:document.body.dataset.reviewView,
      visibleSpaces:[...new Set(surfMeshes.filter(m=>m.visible).map(m=>m.userData.zone))],
      visibleWindows:winMeshes.filter(m=>m.visible).length,
      visibleDoors:openingMeshes.filter(m=>m.visible).length,
      floor:revisionFloor()?.id||'all'})};
  revisionView('whole');
'''


def package(candidate, output, refresh=False):
    output.mkdir(parents=True, exist_ok=refresh)
    source = json.loads((candidate / 'source_model.json').read_text())
    display = json.loads((candidate / 'display_geometry.json').read_text())
    builder = runpy.run_path(str(HERE.parent / '2026-09-16_voimatalo_completion/package_candidate.py'))['build_overlay_viewer']
    page = builder(source, display, ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/viewer.html')
    page = page.replace('Voimatalo · 开发示范修订（内部为假设）', 'Voimatalo · 演示版修订 01 · 待验收')
    old = '  function activePlanes(){ return AX.filter(a=>a.enabled).map(a=>a.plane); }'
    new = FLOOR_HELPERS + '''
  function activePlanes(){
    const p=AX.filter(a=>a.enabled).map(a=>a.plane), f=revisionFloor();
    if(f){p.push(new THREE.Plane(new THREE.Vector3(0,0,1),-f.z_floor+.005));
      p.push(new THREE.Plane(new THREE.Vector3(0,0,-1),f.z_floor+f.height+.005));}
    return p;
  }'''
    assert page.count(old) == 1
    page = page.replace(old, new)
    page = page.replace("em.userData={zone, floor:fi, dup};", "em.userData={zone, floor:fi, dup, name:s.name};")
    page = page.replace('const okF=(u)=>(f<0||u.floor===f) && (exploded || !u.dup);',
                        'const okF=(u)=>revisionMember(u) && (exploded || revisionDuplicate(u));')
    page = page.replace("if(!(f<0||e.floor===f)) return false;", "if(!revisionMember(e)) return false;")
    page = page.replace('fs.onchange=applyFilter;', '''fs.onchange=()=>{
      const f=revisionFloor();
      if(f && $('enZ').checked && !$('flipZ').checked){
        $('posZ').value=f.z_floor+Math.min(2.1,f.height-.3);$('posZ').dispatchEvent(new Event('input'));
      }
      applyFilter();applyClipping();clearSelection();};''')
    page = page.replace("o.textContent=floorName(i)+' (z='+b.toFixed(2)+')';",
                        "o.textContent=NAMED_FLOORS[i].id+' · '+floorName(i)+' (z='+b.toFixed(2)+')';")
    # Bound the continuous core's openings by the selected physical storey.
    anchor = '  refreshColors(); applyFilter(); applyExplode(); applyClipping(); defaultView();'
    bound = '''
  allMeshes().concat(edgeSegs,logicalLines,enclosureLines).forEach(m=>{
    m.geometry.computeBoundingBox();const b=m.geometry.boundingBox;
    m.userData.zmin=b.min.z;m.userData.zmax=b.max.z;
  });
'''
    assert page.count(anchor) == 1
    page = page.replace(anchor, bound + anchor)
    window_anchor = '    // Area of the selected visible fragment: wall apertures are cut out;'
    window_detail = r'''
    if(u.kind==='window'){
      const id=(SOURCE_MAP.windows||{})[u.name],
        evidence=(SOURCE.generation.provenance.opening_mapping||[]).find(o=>o.id===id);
      return '<div class="hh">窗组</div>'+kv([
        ['名称',objectName(u.name)],['源窗 ID',id],['所属房间',spaceName(u.zone)],
        ['源楼层',evidence?.floor],['类型',evidence?.source_kind==='inferred_completion'?'遮挡／缺图处推断补窗':'保留图上窗组，按建筑尺度规整'],
        ['净宽',evidence?(evidence.span[1]-evidence.span[0]).toFixed(2)+' m':''],
        ['净高',evidence?(evidence.z[1]-evidence.z[0]).toFixed(2)+' m':''],
        ['依据',evidence?.evidence?.view],['假设',evidence?.evidence?.note]]);
    }
'''
    assert page.count(window_anchor) == 1
    page = page.replace(window_anchor, window_detail + window_anchor)
    loop = '  (function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();'
    page = page.replace(loop, CONTROLS + loop)
    toolbar = '<nav id="reviewViews" style="position:fixed;top:59px;left:310px;z-index:210;background:#fffffff2;padding:7px;border-radius:5px">'
    for key, text in [('whole', '整体·内院'), ('street', '沿街'), ('standard', '标准层 F3'),
                      ('annex1', '前厅一层'), ('annex2', '前厅二层'), ('circulation', '交通核心'), ('roof', '屋顶')]:
        toolbar += f'<button data-review-view="{key}" style="margin:2px">{text}</button>'
    toolbar += '</nav>'
    toolbar += '''<aside style="position:fixed;bottom:12px;left:310px;z-index:200;background:#fffffff2;padding:10px;max-width:660px;border-radius:6px;font:13px/1.6 sans-serif">
<b>演示版修订 01 · 内部与遮挡处为推断，待验收</b><br>
标准层主要一窗一间；前厅两层；楼梯、电梯井分开；顶层为阁楼及设备附属空间。<br>
<a href="../candidate_01/source_model.json">源模型</a> · <a href="../validation.json">检查记录</a> · <a href="rooms.csv">房间类型与命名表</a>
<details><summary>尺度、命名与依据</summary>
主楼标准层 3.2 m，普通窗台 1.2 m／窗高 1.6 m，主要尺寸按 50 mm 规整。前厅楼层为 0–3.3 m、3.3–6.9 m。<br>
类型与还原共用功能表。Z 编号全楼唯一，自动扩为三位；F 公开序号遵循既有命名协议，并列显示源楼层 ID，不能当作实际楼层号。<br>
楼梯间保留连续空间及楼层门，踏步未展开；阁楼、机电与空腔用途尚无室内证据。露出缺图面补实并推断窗，贴邻界面按邻楼上下文判断。<br>
保留原演示版 GLB 与有限父瓦片上下文。屋顶参照既有网格剖切记录，曲面仍简化。</details></aside>'''
    page = page.replace('<body>', '<body>' + toolbar, 1)
    (output / 'index.html').write_text(page)
    from src.agent.roles import ROOM_TYPES
    with (output / 'rooms.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['源空间ID', '公开名称', '源楼层ID', '类型', '中文类型', '底标高m', '高度m', '面积m2'])
        for s in source['spaces']:
            from shapely.geometry import Polygon
            writer.writerow([s['id'], source['public_names']['spaces'][s['id']], s['floor_id'], s['role'],
                             ROOM_TYPES[s['role']]['label_zh'], s['z_floor'], s['height'], round(Polygon(s['polygon']).area, 2)])
    print(output / 'index.html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, default=HERE / 'candidate_01')
    parser.add_argument('--out', type=Path, default=HERE / 'result_01')
    parser.add_argument('--refresh', action='store_true', help='Refresh only this revision inspection package after UI fixes.')
    args = parser.parse_args()
    package(args.candidate, args.out, args.refresh)
