#!/usr/bin/env python3
"""Package Voimatalo revision_02 as the standard offline geometry viewer.

This is deliberately a presentation wrapper.  It reads the display projections
created by the geometry work, embeds them in the existing native viewer, and
writes only the two root-level showcase pages.  It never rebuilds or changes
the source BIM or either display JSON.

The wrapper keeps the standard viewer's panel, HUD, palette and interaction.
Its local floor predicate uses each displayed object's z extent, rather than
the floor first assigned to its space.  That lets a continuous vertical space
remain inspectable at every intersecting storey, while an actual Floor face is
still available on its own storey.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SHOWCASE = ROOT / "showcase/2026-09-11-research-report/demos/textured-mass"
REVISION = SHOWCASE / "revision_02"

sys.path.insert(0, str(ROOT))

from scripts.tool_scripts.render_geometry_viewer import build_viewer_html  # noqa: E402


EXTRA_PANEL = """
  <div id=\"voimatalo-links\">
    <h2>Voimatalo 资源</h2>
    <div class=\"hint\">交通用途及内部布局为推断。</div>
    <a href=\"input_viewer.html\">原始贴图输入</a>
    <a href=\"__OTHER_PAGE__\">__OTHER_LABEL__</a>
    <a href=\"revision_02/__VARIANT__/source_model.json\" download>下载源 BIM JSON</a>
  </div>
"""

EXTRA_STYLE = """
#voimatalo-links { border-top:1px solid #ebedf0; margin-top:14px; padding-top:1px; }
#voimatalo-links a { display:block; color:#3b6ea5; margin:7px 0; text-decoration:none; }
#voimatalo-links a:hover { text-decoration:underline; }
"""


def replace_once(html: str, old: str, new: str, label: str) -> str:
    """Make wrapper drift explicit if the shared viewer changes."""
    count = html.count(old)
    if count != 1:
        raise RuntimeError(f"shared viewer patch point {label!r}: expected 1, got {count}")
    return html.replace(old, new, 1)


def add_z_extent(code: str) -> str:
    """Apply the local display-only vertical-range filter to viewer JavaScript."""
    code = replace_once(
        code,
        "  const zoneFloor = {};\n  Object.keys(_zMinZ).forEach(z => { zoneFloor[z]=nearestBase(_zFloorZ[z]??_zMinZ[z], BASES); });",
        """  const zoneFloor = {};
  Object.keys(_zMinZ).forEach(z => { zoneFloor[z]=nearestBase(_zFloorZ[z]??_zMinZ[z], BASES); });
  // Filter against each rendered object’s true vertical extent.  A vertical
  // core can span several storeys, so assigning it to its base floor alone
  // would make it disappear from every typical-storey inspection.
  const MAX_SURFACE_Z = Math.max(...SURF.flatMap(s=>s.verts.map(v=>v[2])));
  const FLOOR_BANDS = BASES.map((base, i) => [base, BASES[i+1] ?? MAX_SURFACE_Z + 1e-6]);
  function zExtent(verts){ const zs=verts.map(v=>v[2]); return {zMin:Math.min(...zs),zMax:Math.max(...zs)}; }
  function inSelectedFloor(u, floorIndex){
    if(floorIndex < 0) return true;
    const band=FLOOR_BANDS[floorIndex]; if(!band) return false;
    const lo=band[0], hi=band[1], eps=1e-6, z0=u.zMin, z1=u.zMax;
    if(Math.abs(z1-z0) <= eps){
      // A Floor at z=lo belongs to this storey.  A Ceiling at the same height
      // belongs to the preceding storey, avoiding a substituted lower ceiling.
      return u.type==='Floor' ? Math.abs(z0-lo)<=eps : z0>lo+eps && z0<hi-eps;
    }
    return z1>lo+eps && z0<hi-eps;
  }""",
        "floor bands",
    )
    code = replace_once(
        code,
        """      mesh.userData={zone, floor:fi, type:s.type||'Wall', name:s.name, kind:'surface', dup,
        enclosureCondition,
        area:polyArea(part.verts)-(part.holes||[]).reduce((sum,r)=>sum+polyArea(r),0)};""",
        """      mesh.userData={zone, floor:fi, type:s.type||'Wall', name:s.name, kind:'surface', dup,
        ...zExtent(part.verts), enclosureCondition,
        area:polyArea(part.verts)-(part.holes||[]).reduce((sum,r)=>sum+polyArea(r),0)};""",
        "surface z extent",
    )
    code = replace_once(
        code,
        "em.userData={zone, floor:fi, dup}; edgeSegs.push(em); root.add(em);",
        "em.userData={zone, floor:fi, dup, type:s.type||'Wall', ...zExtent(ring)}; edgeSegs.push(em); root.add(em);",
        "surface edge z extent",
    )
    code = replace_once(
        code,
        "{zone,floor:fi,kind:'logical',dup:false}));",
        "{zone,floor:fi,kind:'logical',dup:false,type:s.type||'Wall',...zExtent(s.verts)}));",
        "logical edge z extent",
    )
    code = replace_once(
        code,
        """    const userData={zone,floor:fi,kind:'enclosure-region',condition:r.condition,dup:duplicate,
      boundaryId:r.boundary_id,area:polyArea(r.verts),sourceRefs:r.source_refs||[],assumptions:r.assumptions||[],""",
        """    const userData={zone,floor:fi,kind:'enclosure-region',condition:r.condition,dup:duplicate,
      ...zExtent(r.verts), boundaryId:r.boundary_id,area:polyArea(r.verts),sourceRefs:r.source_refs||[],assumptions:r.assumptions||[],""",
        "enclosure z extent",
    )
    code = replace_once(
        code,
        """    mesh.userData={zone, floor:nearestBase(Math.min(...w.verts.map(v=>v[2])),BASES), type:'Window', name:w.name, kind:'window', dup:false, area:polyArea(w.verts)};""",
        """    mesh.userData={zone, floor:nearestBase(Math.min(...w.verts.map(v=>v[2])),BASES), type:'Window', name:w.name, kind:'window', dup:false, ...zExtent(w.verts), area:polyArea(w.verts)};""",
        "window z extent",
    )
    code = replace_once(
        code,
        """    mesh.userData={zone,floor:zoneFloor[zone]||0,type:o.kind==='door'?'门':'空开口',name:o.name,
      kind:'opening',dup,area:polyArea(o.verts),baseColor:color,sourceId:o.source_opening_id,""",
        """    mesh.userData={zone,floor:zoneFloor[zone]||0,type:o.kind==='door'?'门':'空开口',name:o.name,
      kind:'opening',dup,...zExtent(o.verts),area:polyArea(o.verts),baseColor:color,sourceId:o.source_opening_id,""",
        "opening z extent",
    )
    code = replace_once(
        code,
        "em.userData={zone,floor:zoneFloor[zone]||0,dup,kind:'opening'};edgeSegs.push(em);root.add(em);",
        "em.userData={zone,floor:zoneFloor[zone]||0,dup,kind:'opening',type:o.kind==='door'?'门':'空开口',...zExtent(o.verts)};edgeSegs.push(em);root.add(em);",
        "opening edge z extent",
    )
    code = replace_once(
        code,
        """  function pushEdges(verts, zone, floor, dup, kind){ for(let i=0;i<verts.length;i++){ const a=verts[i], b=verts[(i+1)%verts.length];
    EDGES.push({a:new THREE.Vector3(a[0],a[1],a[2]), b:new THREE.Vector3(b[0],b[1],b[2]), zone, floor, dup, kind,
      len:Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2])}); } }""",
        """  function pushEdges(verts, zone, floor, dup, kind, type){ for(let i=0;i<verts.length;i++){ const a=verts[i], b=verts[(i+1)%verts.length];
    const z0=Math.min(a[2],b[2]), z1=Math.max(a[2],b[2]);
    EDGES.push({a:new THREE.Vector3(a[0],a[1],a[2]), b:new THREE.Vector3(b[0],b[1],b[2]), zone, floor, dup, kind, type, zMin:z0, zMax:z1,
      len:Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2])}); } }""",
        "measurement edge z extent",
    )
    code = replace_once(
        code,
        """  SURF.forEach(s=>{ const z=s.zone||'?'; pushEdges(s.verts, z, zoneFloor[z]??nearestBase(zmin(s),BASES), isDup(s), 'surface'); });
  WINS.forEach(w=>{ const z=zoneOfWindow(w); pushEdges(w.verts, z, nearestBase(Math.min(...w.verts.map(v=>v[2])),BASES), false, 'window'); });
  OPENS.forEach(o=>{const z=_surfZoneByName[o.parent];pushEdges(o.verts,z,zoneFloor[z]||0,Boolean(o.partner&&o.name>o.partner),'opening');});""",
        """  SURF.forEach(s=>{ const z=s.zone||'?'; pushEdges(s.verts, z, zoneFloor[z]??nearestBase(zmin(s),BASES), isDup(s), 'surface', s.type||'Wall'); });
  WINS.forEach(w=>{ const z=zoneOfWindow(w); pushEdges(w.verts, z, nearestBase(Math.min(...w.verts.map(v=>v[2])),BASES), false, 'window', 'Window'); });
  OPENS.forEach(o=>{const z=_surfZoneByName[o.parent];pushEdges(o.verts,z,zoneFloor[z]||0,Boolean(o.partner&&o.name>o.partner),'opening',o.kind==='door'?'门':'空开口');});""",
        "measurement edge calls",
    )
    code = replace_once(
        code,
        "if(!(f<0||e.floor===f)) return false;",
        "if(!inSelectedFloor(e,f)) return false;",
        "measurement filter",
    )
    code = replace_once(
        code,
        """    const okF=(u)=>(f<0||u.floor===f) && (exploded || !u.dup);""",
        """    // Preserve the actual Floor face at this storey's base even if its
    // reciprocal partner sorts as the hidden duplicate at rest.
    const okF=(u)=>inSelectedFloor(u,f) && (exploded || !u.dup ||
      (u.kind==='surface' && u.type==='Floor' && f>=0 && Math.abs(u.zMin-FLOOR_BANDS[f][0])<1e-6));""",
        "display filter",
    )
    code = replace_once(
        code,
        """  const CAND=[];  // {v: true world Vector3, zone}
  SURF.forEach(s=>s.verts.forEach(v=>CAND.push({v:new THREE.Vector3(v[0],v[1],v[2]), zone:s.zone||'?'})));
  WINS.forEach(w=>{const z=zoneOfWindow(w); w.verts.forEach(v=>CAND.push({v:new THREE.Vector3(v[0],v[1],v[2]), zone:z}));});
  OPENS.forEach(o=>o.verts.forEach(v=>CAND.push({v:new THREE.Vector3(...v),zone:_surfZoneByName[o.parent]})));""",
        """  const CAND=[];  // {v: true world Vector3, zone, zMin, zMax, type}
  SURF.forEach(s=>s.verts.forEach(v=>CAND.push({v:new THREE.Vector3(v[0],v[1],v[2]), zone:s.zone||'?',zMin:v[2],zMax:v[2],type:s.type||'Wall'})));
  WINS.forEach(w=>{const z=zoneOfWindow(w); w.verts.forEach(v=>CAND.push({v:new THREE.Vector3(v[0],v[1],v[2]), zone:z,zMin:v[2],zMax:v[2],type:'Window'}));});
  OPENS.forEach(o=>o.verts.forEach(v=>CAND.push({v:new THREE.Vector3(...v),zone:_surfZoneByName[o.parent],zMin:v[2],zMax:v[2],type:o.kind==='door'?'门':'空开口'})));""",
        "measurement vertices",
    )
    code = replace_once(
        code,
        """    for(const c of CAND){ const w=c.v.clone().add(explodeOffset(c.zone)); const p=w.clone().project(camera);""",
        """    const f=parseInt($('floorSel').value,10);
    for(const c of CAND){ if(!inSelectedFloor(c,f)) continue; const w=c.v.clone().add(explodeOffset(c.zone)); const p=w.clone().project(camera);""",
        "measurement vertex filter",
    )
    code = replace_once(
        code,
        """  function activePlanes(){ return AX.filter(a=>a.enabled).map(a=>a.plane); }""",
        """  function activePlanes(){ return AX.filter(a=>a.enabled).map(a=>a.plane); }
  function selectedFloorPlanes(){
    const f=parseInt($('floorSel').value,10);
    // Exploded groups are translated in world space. Their source-floor
    // predicate remains active, but clipping in their original z frame does not.
    if(f<0 || parseFloat($('explode').value)>0) return [];
    const band=FLOOR_BANDS[f]; if(!band) return [];
    // Keep the existing floor just inside the clipping half-space. A plane
    // exactly on the floor produced speckled fragments from float precision.
    // The selected storey's ceiling is excluded by inSelectedFloor above.
    return [new THREE.Plane(new THREE.Vector3(0,0,1),-band[0]+0.002),
            new THREE.Plane(new THREE.Vector3(0,0,-1),band[1])];
  }
  function pointInSelectedFloor(point, userData){
    const f=parseInt($('floorSel').value,10);
    return inSelectedFloor({zMin:point.z,zMax:point.z,type:userData.type},f);
  }""",
        "floor clip planes",
    )
    code = replace_once(
        code,
        """  function applyClipping(){ const p=activePlanes();
    allMeshes().forEach(m=>{m.material.clippingPlanes=p; m.material.needsUpdate=true;});
    edgeSegs.concat(logicalLines,enclosureLines).forEach(e=>{e.material.clippingPlanes=p; e.material.needsUpdate=true;}); }""",
        """  function applyClipping(){ const p=activePlanes().concat(selectedFloorPlanes());
    allMeshes().forEach(m=>{m.material.clippingPlanes=p; m.material.needsUpdate=true;});
    edgeSegs.concat(logicalLines,enclosureLines).forEach(e=>{e.material.clippingPlanes=p; e.material.needsUpdate=true;}); }""",
        "floor clip application",
    )
    code = replace_once(
        code,
        """  function occluded(w){ const from=camera.position; const dir=w.clone().sub(from); const dist=dir.length()||1e-6;
    _ray.set(from, dir.divideScalar(dist)); _ray.near=0; _ray.far=dist-radius*0.01;   // only faces strictly IN FRONT of w
    return _ray.intersectObjects(surfMeshes.filter(m=>m.visible), false).length>0; }""",
        """  function occluded(w){ const from=camera.position; const dir=w.clone().sub(from); const dist=dir.length()||1e-6;
    _ray.set(from, dir.divideScalar(dist)); _ray.near=0; _ray.far=dist-radius*0.01;   // only faces strictly IN FRONT of w
    return _ray.intersectObjects(surfMeshes.filter(m=>m.visible), false).some(hit=>pointInSelectedFloor(hit.point,hit.object.userData)); }""",
        "clipped occlusion",
    )
    code = replace_once(
        code,
        """  function edgeVisible(e){ const f=parseInt($('floorSel').value,10); const exploded=parseFloat($('explode').value)>0;
    if(!inSelectedFloor(e,f)) return false;
    if(!exploded && e.dup) return false;
    return (e.kind==='window') ? $('showWin').checked : (e.kind==='opening') ? $('showOpen').checked : $('showWalls').checked; }""",
        """  function edgeVisible(e){ const f=parseInt($('floorSel').value,10); const exploded=parseFloat($('explode').value)>0;
    if(!inSelectedFloor(e,f)) return false;
    if(!exploded && e.dup) return false;
    return (e.kind==='window') ? $('showWin').checked : (e.kind==='opening') ? $('showOpen').checked : $('showWalls').checked; }
  function clippedEdge(e){
    const f=parseInt($('floorSel').value,10);
    if(f<0 || parseFloat($('explode').value)>0) return {a:e.a,b:e.b};
    const band=FLOOR_BANDS[f]; if(!band) return null;
    const dz=e.b.z-e.a.z, eps=1e-9;
    if(Math.abs(dz)<eps) return pointInSelectedFloor(e.a,e) ? {a:e.a,b:e.b} : null;
    let t0=Math.max(0,Math.min(1,(band[0]-e.a.z)/dz));
    let t1=Math.max(0,Math.min(1,(band[1]-e.a.z)/dz));
    if(t0>t1){ const t=t0;t0=t1;t1=t; }
    if(t1-t0<eps) return null;
    return {a:e.a.clone().lerp(e.b,t0),b:e.a.clone().lerp(e.b,t1)};
  }""",
        "clipped measurement edge",
    )
    code = replace_once(
        code,
        """    for(const e of EDGES){ if(!edgeVisible(e)) continue; const o=explodeOffset(e.zone);
      const A=e.a.clone().add(o), B=e.b.clone().add(o);""",
        """    for(const e of EDGES){ if(!edgeVisible(e)) continue; const segment=clippedEdge(e); if(!segment) continue; const o=explodeOffset(e.zone);
      const A=segment.a.clone().add(o), B=segment.b.clone().add(o);""",
        "clipped edge pick",
    )
    code = replace_once(
        code,
        """    const hits=raycaster.intersectObjects(allPickables().filter(m=>m.visible),false); return hits.length?hits[0]:null; }""",
        """    const hits=raycaster.intersectObjects(allPickables().filter(m=>m.visible),false).filter(hit=>pointInSelectedFloor(hit.point,hit.object.userData)); return hits.length?hits[0]:null; }""",
        "clipped face pick",
    )
    code = replace_once(
        code,
        """  $('colorBy').onchange=()=>{ refreshColors(); clearSelection(); }; fs.onchange=applyFilter;""",
        """  $('colorBy').onchange=()=>{ refreshColors(); clearSelection(); }; fs.onchange=()=>{ applyFilter(); applyClipping(); };""",
        "floor clip refresh",
    )
    code = replace_once(
        code,
        """  function applyExplode(){ surfMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    winMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    openingMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    enclosureMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    edgeSegs.concat(logicalLines,enclosureLines).forEach(e=>e.position.copy(explodeOffset(e.userData.zone)));
    applyFilter(); }  // re-evaluate dup visibility when crossing explode 0 ↔ >0""",
        """  function applyExplode(){ surfMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    winMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    openingMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    enclosureMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    edgeSegs.concat(logicalLines,enclosureLines).forEach(e=>e.position.copy(explodeOffset(e.userData.zone)));
    applyFilter(); applyClipping(); }  // re-evaluate duplicate and floor-clipping visibility""",
        "exploded floor clip refresh",
    )
    return code


def localize_coordinate_frame(html: str) -> str:
    """Use u/v/z labels and remove the generic N compass from the local frame."""
    html = replace_once(
        html,
        "[['x',0xcc1111,new THREE.Vector3(aL*1.25,0,0)],['y',0x11aa11,new THREE.Vector3(0,aL*1.25,0)],\n   ['z',0x1111cc,new THREE.Vector3(0,0,aL*1.25)]].forEach(([t,col,off])=>{",
        "[['u',0xcc1111,new THREE.Vector3(aL*1.25,0,0)],['v',0x11aa11,new THREE.Vector3(0,aL*1.25,0)],\n   ['z',0x1111cc,new THREE.Vector3(0,0,aL*1.25)]].forEach(([t,col,off])=>{",
        "local axis labels",
    )
    compass = re.compile(
        r"  // compass: small flat 2D ring on the ground, N = \+Y \(EnergyPlus convention\)\n"
        r"  const cR=.*?scene\.add\(nlab\);\n",
        re.DOTALL,
    )
    html, count = compass.subn("", html, count=1)
    if count != 1:
        raise RuntimeError("shared viewer patch point 'N compass': expected 1, got " + str(count))
    html = replace_once(html, "{key:'X'", "{key:'U'", "section U")
    html = replace_once(html, "{key:'Y'", "{key:'V'", "section V")
    html = replace_once(html, "row('width (x)'", "row('width (u)'", "HUD u")
    html = replace_once(html, "row('depth (y)'", "row('depth (v)'", "HUD v")
    html = replace_once(
        html,
        """  function defaultView(){ camera.position.set(center.x+radius*1.6, center.y-radius*1.8, center.z+radius*1.3);
    controls.target.copy(center); controls.update(); }""",
        """  // Local presentation view: approach the visible inner-courtyard side and
  // frame the full building between the native left/right inspection panels.
  function defaultView(){ camera.position.set(center.x+radius*1.25, center.y-radius*1.45, center.z+radius*1.05);
    controls.target.copy(center); controls.update(); }""",
        "initial courtyard view",
    )
    return html


def decorate(html: str, *, variant: str, title: str, other_page: str, other_label: str, main_floors: int) -> str:
    """Keep only small Voimatalo navigation inside the native left panel."""
    html = replace_once(html, "</style>", EXTRA_STYLE + "</style>", "extra styles")
    links = (
        EXTRA_PANEL.replace("__OTHER_PAGE__", other_page)
        .replace("__OTHER_LABEL__", other_label)
        .replace("__VARIANT__", variant)
    )
    html = replace_once(html, "</div>\n<div id=\"rinfo\">", links + "</div>\n<div id=\"rinfo\">", "left-panel links")
    html = localize_coordinate_frame(html)
    html = add_z_extent(html)
    html = replace_once(
        html,
        "row('floors',BASES.length);",
        f"row('标高层级',BASES.length) + row('主楼层数','{main_floors} 层');",
        "HUD level labels",
    )
    if "label('N'" in html or "N = +Y" in html:
        raise RuntimeError("local-coordinate viewer unexpectedly retained an N arrow")
    return html


def display_roles(data: dict) -> dict[str, str]:
    """Map Voimatalo's evidence roles onto the native viewer's palette only.

    The source keeps roles such as ``vertical_transport_inferred`` because that
    suffix communicates provenance.  The standard viewer deliberately uses
    compact, cross-case palette names, so this mapping is an HTML display aid;
    it is never written into either source or display geometry JSON.
    """
    native = {
        "office_inferred": "office",
        "corridor_inferred": "corridor",
        "vertical_transport_inferred": "stair",
        "vertical_core_inferred": "stair",
        "services_inferred": "equipment",
        "office_merged": "office",
        "commercial_merged": "retail",
        "annex_merged": "storage",
    }
    return {str(zone): native.get(str(role), str(role))
            for zone, role in (data.get("roles") or {}).items()}


def main_floor_count(data: dict) -> int:
    """Count only F1…Fn storeys; roof/continuous-space levels are not storeys."""
    source = data.get("source_model") or {}
    return sum(bool(re.fullmatch(r"F\d+", str(floor.get("id", "")))) for floor in source.get("floors", []))


def build_variant(variant: str, target: str, title: str, other_page: str, other_label: str) -> Path:
    display_path = REVISION / variant / "display_geometry.json"
    source_path = REVISION / variant / "source_model.json"
    if not display_path.is_file() or not source_path.is_file():
        missing = [str(p.relative_to(ROOT)) for p in (display_path, source_path) if not p.is_file()]
        raise FileNotFoundError("revision_02 is incomplete: " + ", ".join(missing))
    data = json.loads(display_path.read_text(encoding="utf-8"))
    if not isinstance(data.get("source_model"), dict):
        raise ValueError(f"{display_path} must embed source_model for the native viewer HUD")
    html = build_viewer_html(data, title=title, roles=display_roles(data))
    html = decorate(
        html, variant=variant, title=title, other_page=other_page, other_label=other_label,
        main_floors=main_floor_count(data),
    )
    out = SHOWCASE / target
    out.write_text(html, encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-inputs", action="store_true", help="only verify the expected revision_02 inputs")
    args = parser.parse_args()
    expected = [REVISION / v / n for v in ("inferred", "exterior") for n in ("display_geometry.json", "source_model.json")]
    missing = [p for p in expected if not p.is_file()]
    if args.check_inputs:
        print(json.dumps({"revision": str(REVISION.relative_to(ROOT)), "ready": not missing,
                          "missing": [str(p.relative_to(ROOT)) for p in missing]}, ensure_ascii=False))
        return 0 if not missing else 2
    if missing:
        raise FileNotFoundError("revision_02 is incomplete: " + ", ".join(str(p.relative_to(ROOT)) for p in missing))
    outputs = [
        build_variant("inferred", "index.html", "Voimatalo · 内部空间推理方案", "envelope.html", "外壳与楼层补全"),
        build_variant("exterior", "envelope.html", "Voimatalo · 外壳与楼层补全", "index.html", "内部空间推理方案"),
    ]
    for out in outputs:
        print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB; offline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
