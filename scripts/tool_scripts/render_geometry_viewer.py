"""Self-contained OFFLINE interactive 3D viewer for building_geometry.json (#3).

The geometry-confirmation gate (contracts §1 2/3 ②a) is a HUMAN gate: the user
inspects the deterministic build in 3D before the run continues. Real interactive
3D: orbit/zoom, wall translucency, section cuts, exploded view
(by floor or by zone, always upward), CAD-style vertex-snap measure, click-select,
save-PNG, a small ground compass + axis ticks.

ONE fully self-contained ``geometry_viewer.html``:
  - three.js (r0.137.5 UMD global) + OrbitControls INLINED from vendor/ → offline,
    file:// double-click, no CDN.
  - geometry embedded inline as ``window.GEO`` (script-safe via ``_js_embed``).
  - ALL faces are kept (each zone stays a closed box, preserving the EP reciprocal
    split-pairing). z-fighting is avoided WITHOUT deleting geometry: at explode=0 one
    face of each coincident reciprocal pair is HIDDEN (solid clean shell, no gaps);
    at explode>0 all faces show, separated by the explode offset. Windows are pushed
    proud of their wall (WIN_POP) so they render clean and stay pickable.

Headless note: the rendered result needs a browser to confirm (no browser here);
generation + ``node --check`` of the app JS is the automated guard.

Usage:
    python scripts/tool_scripts/render_geometry_viewer.py <building_geometry.json> [--out viewer.html]
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

_VENDOR = Path(__file__).resolve().parent / "vendor"


def _js_embed(obj) -> str:
    """JSON for inline embedding in a <script> — escape the chars that could break
    out of the script element / be mis-tokenised (``<`` → ``</script>``, plus & and
    the JS line separators U+2028/U+2029). These become \\u00xx, which a JS object
    literal parses back to the original char."""
    return (
        json.dumps(obj, ensure_ascii=False)
        .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        .replace(" ", "\\u2028").replace(" ", "\\u2029")
    )


# --------------------------------------------------------------------------- #
# viewer app (classic script; global THREE + THREE.OrbitControls + window.GEO).
# Standalone constant so it can be `node --check`ed.
# --------------------------------------------------------------------------- #
_APP_JS = r"""
(function () {
  const GEO = window.GEO || { zones: [], surfaces: [], windows: [] };
  const $ = (id) => document.getElementById(id);
  const SURF = (GEO.surfaces || []).filter(s => (s.verts || []).length >= 3);
  const WINS = (GEO.windows || []).filter(w => (w.verts || []).length >= 3);
  const ZONES = (GEO.zones || []).slice().sort((a, b) => b.length - a.length);
  // resolve a window's zone: its parent surface's zone first (parent = "<wall>_<i>"),
  // then a zone-name prefix, then the nearest zone centroid — never returns '?' so a
  // window always pops out + groups/explodes with a real zone.
  const _surfZoneByName = {};
  SURF.forEach(s => { if (s.name) _surfZoneByName[s.name] = s.zone || '?'; });
  const _surfNames = Object.keys(_surfZoneByName).sort((a, b) => b.length - a.length);
  function zoneOfWindow(w){
    const p = w.parent || '';
    for (const n of _surfNames) if (p.startsWith(n)) return _surfZoneByName[n];
    const z = ZONES.find(z => p.startsWith(z)); if (z) return z;
    let cx=0,cy=0,cz=0; const vs=w.verts||[]; vs.forEach(v=>{cx+=v[0];cy+=v[1];cz+=v[2];}); const n=vs.length||1;
    const wc=new THREE.Vector3(cx/n,cy/n,cz/n); let best=ZONES[0]||'?', bd=1e18;
    for (const z in zoneCentroid){ const d=zoneCentroid[z].distanceToSquared(wc); if(d<bd){bd=d;best=z;} }
    return best;
  }

  const FLOOR_COLORS = [0xb0d0e8,0xffe0b2,0xc8e6c9,0xf4c7c7,0xd1c4e9,0xfff59d,0xb2dfdb,0xd7ccc8];
  const TYPE_COLORS = { Wall:0xdfe3e6, Floor:0xc8a165, Ceiling:0x9fa8da, Roof:0xfff3b0 };
  const WINDOW_COLOR = 0x1e5ad2, WHITE = 0xffffff, SEL_COLOR = 0xff9800;
  // Geometry is drawn at TRUE positions (so measure is exact + no inset gaps).
  // z-fighting is avoided by: (a) at explode=0, HIDING one face of each coincident
  // reciprocal (split-paired) pair — solid clean shell, no gaps; (b) at explode>0,
  // showing ALL faces (each zone a closed box) separated by the explode offset;
  // (c) windows pushed proud of their wall by WIN_POP (also makes them pickable).
  const WIN_POP = 0.03;  // metres

  // ---- floors: bases from FLOOR-type surfaces, per-zone assignment ----
  const zmin = (s) => Math.min(...s.verts.map(v => v[2]));
  function cluster(zs){ const u=[...new Set(zs.map(z=>Math.round(z*10)/10))].sort((a,b)=>a-b);
    const b=[]; for(const z of u) if(!b.length||Math.abs(z-b[b.length-1])>0.3) b.push(z); return b.length?b:[0]; }
  function nearestBase(z,bases){ let bi=0,bd=1e9; bases.forEach((b,i)=>{const d=Math.abs(z-b); if(d<bd){bd=d;bi=i;}}); return bi; }
  const floorSurf = SURF.filter(s => s.type === 'Floor');
  const BASES = cluster((floorSurf.length ? floorSurf : SURF).map(zmin));
  const _zFloorZ = {}, _zMinZ = {};
  SURF.forEach(s => { const z=s.zone||'?', mn=zmin(s); _zMinZ[z]=Math.min(_zMinZ[z]??1e9,mn);
    if(s.type==='Floor') _zFloorZ[z]=Math.min(_zFloorZ[z]??1e9,mn); });
  const zoneFloor = {};
  Object.keys(_zMinZ).forEach(z => { zoneFloor[z]=nearestBase(_zFloorZ[z]??_zMinZ[z], BASES); });

  // ---- zone centroids (explode-by-zone + window pop-out) ----
  const zoneSum = {};
  SURF.forEach(s => { const z=s.zone||'?'; const a=zoneSum[z]||(zoneSum[z]=[0,0,0,0]);
    s.verts.forEach(v=>{a[0]+=v[0];a[1]+=v[1];a[2]+=v[2];a[3]++;}); });
  const zoneCentroid = {};
  Object.keys(zoneSum).forEach(z=>{const a=zoneSum[z]; zoneCentroid[z]=new THREE.Vector3(a[0]/a[3],a[1]/a[3],a[2]/a[3]);});
  // translate a window's verts a few cm AWAY from its zone centroid → proud of the wall
  const popOut = (verts, zone) => { const c=zoneCentroid[zone]; if(!c) return verts;
    let cx=0,cy=0,cz=0; verts.forEach(v=>{cx+=v[0];cy+=v[1];cz+=v[2];}); const n=verts.length||1; cx/=n;cy/=n;cz/=n;
    const dx=cx-c.x, dy=cy-c.y, dz=cz-c.z; const L=Math.hypot(dx,dy,dz)||1; const t=WIN_POP/L;
    return verts.map(v=>[v[0]+dx*t, v[1]+dy*t, v[2]+dz*t]); };

  // ---- bbox ----
  const bb = new THREE.Box3();
  SURF.forEach(s => s.verts.forEach(v => bb.expandByPoint(new THREE.Vector3(v[0],v[1],v[2]))));
  if (bb.isEmpty()) bb.set(new THREE.Vector3(0,0,0), new THREE.Vector3(10,10,3));
  const center = bb.getCenter(new THREE.Vector3());
  const size = bb.getSize(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z) || 10;
  const zoneDir = {};  // full 3D radial from building centre (zone explode = all directions)
  Object.keys(zoneCentroid).forEach(z=>{ const d=zoneCentroid[z].clone().sub(center);
    zoneDir[z] = d.lengthSq()<1e-6 ? new THREE.Vector3(0,0,0) : d.normalize(); });

  // ---- renderer / scene / camera ----
  const renderer = new THREE.WebGLRenderer({ antialias:true, preserveDrawingBuffer:true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.localClippingEnabled = true;
  renderer.setClearColor(0xf2f4f7);
  $('app').appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 0.05, radius*200);
  camera.up.set(0,0,1);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  function defaultView(){ camera.position.set(center.x+radius*1.6, center.y-radius*1.8, center.z+radius*1.3);
    controls.target.copy(center); controls.update(); }
  scene.add(new THREE.AmbientLight(0xffffff, 0.8));
  const dl=new THREE.DirectionalLight(0xffffff,0.6); dl.position.set(1,-1,2); scene.add(dl);
  const dl2=new THREE.DirectionalLight(0xffffff,0.3); dl2.position.set(-1,1,0.5); scene.add(dl2);
  const grid=new THREE.GridHelper(radius*4,20,0xcccccc,0xe6e6e6); grid.rotateX(Math.PI/2);
  grid.position.set(center.x, center.y, bb.min.z); scene.add(grid);

  // ---- small text labels (axes + compass) ----
  function label(txt, color, scl){
    const c=document.createElement('canvas'); c.width=c.height=64; const x=c.getContext('2d');
    x.fillStyle=color; x.font='bold 46px sans-serif'; x.textAlign='center'; x.textBaseline='middle'; x.fillText(txt,32,34);
    const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c), depthTest:false, transparent:true}));
    sp.scale.set(scl, scl, 1); return sp;
  }
  // small axis ticks at the origin corner
  const aL=radius*0.18, aLab=radius*0.05;
  const axes=new THREE.AxesHelper(aL); axes.position.copy(bb.min); scene.add(axes);
  [['x',0xcc1111,new THREE.Vector3(aL*1.25,0,0)],['y',0x11aa11,new THREE.Vector3(0,aL*1.25,0)],
   ['z',0x1111cc,new THREE.Vector3(0,0,aL*1.25)]].forEach(([t,col,off])=>{
    const s=label(t,'#'+col.toString(16).padStart(6,'0'),aLab); s.position.copy(bb.min).add(off); scene.add(s); });
  // compass: small flat 2D ring on the ground, N = +Y (EnergyPlus convention)
  const cR=radius*0.16, cC=new THREE.Vector3(bb.min.x-radius*0.32, bb.min.y-radius*0.32, bb.min.z+0.02);
  const ring=new THREE.Mesh(new THREE.RingGeometry(cR*0.86, cR, 48),
    new THREE.MeshBasicMaterial({color:0x9aa0a6, side:THREE.DoubleSide})); ring.position.copy(cC); scene.add(ring);
  const ntick=new THREE.Line(new THREE.BufferGeometry().setFromPoints(
    [cC.clone(), cC.clone().add(new THREE.Vector3(0,cR,0))]), new THREE.LineBasicMaterial({color:0xd32f2f}));
  scene.add(ntick);
  const nlab=label('N','#d32f2f',radius*0.06); nlab.position.copy(cC).add(new THREE.Vector3(0,cR*1.25,0)); scene.add(nlab);

  // ---- clip planes (section cuts) ----
  const AX = [
    {key:'X', base:new THREE.Vector3(-1,0,0), min:bb.min.x, max:bb.max.x},
    {key:'Y', base:new THREE.Vector3(0,-1,0), min:bb.min.y, max:bb.max.y},
    {key:'Z', base:new THREE.Vector3(0,0,-1), min:bb.min.z, max:bb.max.z},
  ];
  AX.forEach(a=>{ a.enabled=false; a.flip=false; a.pos=a.max; a.plane=new THREE.Plane(a.base.clone(), a.max); });
  function updatePlane(a){ a.plane.normal.copy(a.flip?a.base.clone().negate():a.base.clone()); a.plane.constant=a.flip?-a.pos:a.pos; }
  function activePlanes(){ return AX.filter(a=>a.enabled).map(a=>a.plane); }

  // ---- build meshes (keep ALL faces; reciprocal dup hidden at rest, windows popped out) ----
  const surfMeshes=[], winMeshes=[], edgeSegs=[];
  const root=new THREE.Group(); scene.add(root);
  function ringGeom(ring){ const pos=[],idx=[]; ring.forEach(v=>pos.push(v[0],v[1],v[2]));
    for(let i=1;i<ring.length-1;i++) idx.push(0,i,i+1);
    const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
    g.setIndex(idx); g.computeVertexNormals(); return g; }
  function edgeGeom(ring){ const pos=[]; for(let i=0;i<ring.length;i++){const a=ring[i],b=ring[(i+1)%ring.length];
    pos.push(a[0],a[1],a[2], b[0],b[1],b[2]);} const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3)); return g; }
  const isDup = (s) => s.obc==='Surface' && s.obc_obj && s.name > s.obc_obj;  // one of each reciprocal pair
  SURF.forEach(s=>{
    const zone=s.zone||'?', fi=zoneFloor[zone] ?? nearestBase(zmin(s),BASES), dup=isDup(s);
    const m=new THREE.MeshStandardMaterial({side:THREE.DoubleSide, transparent:true, opacity:1, roughness:0.9, metalness:0.0});
    const mesh=new THREE.Mesh(ringGeom(s.verts), m);
    mesh.userData={zone, floor:fi, type:s.type||'Wall', name:s.name, kind:'surface', dup, area:polyArea(s.verts)};
    surfMeshes.push(mesh); root.add(mesh);
    const em=new THREE.LineSegments(edgeGeom(s.verts), new THREE.LineBasicMaterial({color:0x303030}));
    em.userData={zone, floor:fi, dup}; edgeSegs.push(em); root.add(em);
  });
  WINS.forEach(w=>{
    const zone=zoneOfWindow(w), sv=popOut(w.verts, zone);  // proud of wall → clean + pickable
    const m=new THREE.MeshStandardMaterial({color:WINDOW_COLOR, side:THREE.DoubleSide, roughness:0.4});
    const mesh=new THREE.Mesh(ringGeom(sv), m);
    mesh.userData={zone, floor:nearestBase(Math.min(...w.verts.map(v=>v[2])),BASES), type:'Window', name:w.name, kind:'window', dup:false, area:polyArea(w.verts)};
    winMeshes.push(mesh); root.add(mesh);
  });
  const allMeshes = () => surfMeshes.concat(winMeshes);

  function applyClipping(){ const p=activePlanes();
    allMeshes().forEach(m=>{m.material.clippingPlanes=p; m.material.needsUpdate=true;});
    edgeSegs.forEach(e=>{e.material.clippingPlanes=p; e.material.needsUpdate=true;}); }

  // ---- geometric measures (on TRUE geometry) ----
  function polyArea(r){ let nx=0,ny=0,nz=0; const n=r.length;  // Newell → planar polygon area
    for(let i=0;i<n;i++){ const a=r[i],b=r[(i+1)%n]; nx+=(a[1]-b[1])*(a[2]+b[2]); ny+=(a[2]-b[2])*(a[0]+b[0]); nz+=(a[0]-b[0])*(a[1]+b[1]); }
    return Math.hypot(nx,ny,nz)/2; }
  const zoneVol={};  // closed-zone volume via divergence theorem over its faces
  SURF.forEach(s=>{ const z=s.zone||'?', r=s.verts; let v=zoneVol[z]||0;
    for(let i=1;i<r.length-1;i++){ const a=r[0],b=r[i],c=r[i+1];
      v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0]))/6; }
    zoneVol[z]=v; });
  Object.keys(zoneVol).forEach(z=>zoneVol[z]=Math.abs(zoneVol[z]));

  // ---- select-by modes + uniform-colour selection ----
  let selected=new Set(); const selGroup=new THREE.Group(); scene.add(selGroup);
  function refreshColors(){
    const mode=$('colorBy').value;
    surfMeshes.forEach(m=>{ let c; if(mode==='floor') c=FLOOR_COLORS[m.userData.floor%FLOOR_COLORS.length];
      else if(mode==='zone'||mode==='edge') c=WHITE; else c=TYPE_COLORS[m.userData.type] ?? 0xcccccc;
      m.userData.baseColor=c; });
    winMeshes.forEach(m=>m.userData.baseColor=WINDOW_COLOR);
    allMeshes().forEach(m=>m.material.color.setHex(selected.has(m) ? SEL_COLOR : m.userData.baseColor));
  }
  function clearSelGroup(){ while(selGroup.children.length) selGroup.remove(selGroup.children[0]); }
  function setSelection(arr, lbl){ clearSelGroup(); selected=new Set(arr);
    allMeshes().forEach(m=>m.material.color.setHex(selected.has(m)?SEL_COLOR:(m.userData.baseColor??0xcccccc)));
    $('sel').textContent=lbl||''; $('sel').style.display=lbl?'block':'none'; }
  function clearSelection(){ setSelection([], ''); }

  // ---- measure (button; CONTINUOUS; CAD-style screen-space vertex snap on true geometry) ----
  let measuring=false, measurePts=[]; const mGroup=new THREE.Group(); scene.add(mGroup);
  const BALL=radius*0.008;
  const snap=new THREE.Mesh(new THREE.SphereGeometry(BALL,16,16),
    new THREE.MeshBasicMaterial({color:0x00e5ff, depthTest:false})); snap.visible=false; scene.add(snap);
  const CAND=[];  // {v: true world Vector3, zone}
  SURF.forEach(s=>s.verts.forEach(v=>CAND.push({v:new THREE.Vector3(v[0],v[1],v[2]), zone:s.zone||'?'})));
  WINS.forEach(w=>{const z=zoneOfWindow(w); w.verts.forEach(v=>CAND.push({v:new THREE.Vector3(v[0],v[1],v[2]), zone:z}));});
  function clearPair(){ while(mGroup.children.length) mGroup.remove(mGroup.children[0]); measurePts=[]; }
  function clearMeasure(){ measuring=false; snap.visible=false; clearPair();
    $('meas').style.display='none'; renderer.domElement.style.cursor='default'; }
  function startMeasure(){ clearMeasure(); measuring=true; renderer.domElement.style.cursor='crosshair';
    $('meas').style.display='block'; $('meas').textContent='measure: snap vertex 1  (Esc to exit)'; }
  function marker(p){ const s=new THREE.Mesh(new THREE.SphereGeometry(BALL,16,16),
    new THREE.MeshBasicMaterial({color:0xd81b60, depthTest:false})); s.position.copy(p); mGroup.add(s); }
  function snapAt(cx, cy){ const r=renderer.domElement.getBoundingClientRect();
    let best=null, bd=24*24; // 24px radius
    for(const c of CAND){ const w=c.v.clone().add(explodeOffset(c.zone)); const p=w.clone().project(camera);
      if(p.z<-1||p.z>1) continue; const sx=(p.x*0.5+0.5)*r.width, sy=(-p.y*0.5+0.5)*r.height;
      const d=(sx-cx)**2+(sy-cy)**2; if(d<bd){bd=d; best=w;} }
    return best; }

  // ---- edge select (screen-space nearest segment → length) ----
  const EDGES=[];  // {a,b: true world Vector3, zone, len, floor, dup, kind}
  function pushEdges(verts, zone, floor, dup, kind){ for(let i=0;i<verts.length;i++){ const a=verts[i], b=verts[(i+1)%verts.length];
    EDGES.push({a:new THREE.Vector3(a[0],a[1],a[2]), b:new THREE.Vector3(b[0],b[1],b[2]), zone, floor, dup, kind,
      len:Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2])}); } }
  SURF.forEach(s=>{ const z=s.zone||'?'; pushEdges(s.verts, z, zoneFloor[z]??nearestBase(zmin(s),BASES), isDup(s), 'surface'); });
  WINS.forEach(w=>{ const z=zoneOfWindow(w); pushEdges(w.verts, z, nearestBase(Math.min(...w.verts.map(v=>v[2])),BASES), false, 'window'); });
  // only pick an edge whose source face is currently shown (same predicate as applyFilter)
  function edgeVisible(e){ const f=parseInt($('floorSel').value,10); const exploded=parseFloat($('explode').value)>0;
    if(!(f<0||e.floor===f)) return false;
    if(!exploded && e.dup) return false;
    return (e.kind==='window') ? $('showWin').checked : $('showWalls').checked; }
  function segDist(px,py,ax,ay,bx,by){ const dx=bx-ax,dy=by-ay, L2=dx*dx+dy*dy||1;
    let t=((px-ax)*dx+(py-ay)*dy)/L2; t=Math.max(0,Math.min(1,t));
    return (px-(ax+t*dx))**2 + (py-(ay+t*dy))**2; }
  function edgePick(ev){ const r=renderer.domElement.getBoundingClientRect();
    const cx=ev.clientX-r.left, cy=ev.clientY-r.top; let best=null, bd=18*18;
    for(const e of EDGES){ if(!edgeVisible(e)) continue; const o=explodeOffset(e.zone);
      const pa=e.a.clone().add(o).project(camera), pb=e.b.clone().add(o).project(camera);
      if(pa.z<-1||pa.z>1||pb.z<-1||pb.z>1) continue;  // skip if EITHER endpoint is behind/clipped
      const ax=(pa.x*.5+.5)*r.width, ay=(-pa.y*.5+.5)*r.height, bx=(pb.x*.5+.5)*r.width, by=(-pb.y*.5+.5)*r.height;
      const d=segDist(cx,cy,ax,ay,bx,by); if(d<bd){bd=d; best=e;} }
    clearSelection(); if(!best) return;
    const o=explodeOffset(best.zone), A=best.a.clone().add(o), B=best.b.clone().add(o);
    selGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([A,B]), new THREE.LineBasicMaterial({color:SEL_COLOR, depthTest:false})));
    [A,B].forEach(p=>{ const s=new THREE.Mesh(new THREE.SphereGeometry(BALL,12,12), new THREE.MeshBasicMaterial({color:SEL_COLOR, depthTest:false})); s.position.copy(p); selGroup.add(s); });
    $('sel').textContent='edge · length '+best.len.toFixed(3)+' m'; $('sel').style.display='block'; }

  // ---- selection picking (face raycast, for click-select only) ----
  const raycaster=new THREE.Raycaster();
  function pick(ev){ const r=renderer.domElement.getBoundingClientRect();
    const mouse=new THREE.Vector2(((ev.clientX-r.left)/r.width)*2-1, -((ev.clientY-r.top)/r.height)*2+1);
    raycaster.setFromCamera(mouse,camera);
    const hits=raycaster.intersectObjects(allMeshes().filter(m=>m.visible),false); return hits.length?hits[0]:null; }
  function describe(mode,o){ const u=o.userData;
    if(mode==='floor') return 'floor F'+(u.floor+1);
    if(mode==='zone') return 'zone '+u.zone+' · volume '+(zoneVol[u.zone]||0).toFixed(2)+' m³';
    // surface: gross area (a wall's polygon is the FULL rectangle — window openings are
    // separate child surfaces and are NOT subtracted)
    return u.type+' '+u.name+' · area '+(u.area||0).toFixed(2)+' m²'+
      (u.type==='Wall' ? ' (gross — window openings not deducted)' : '');
  }
  function handleClick(ev){
    if(measuring){ const r=renderer.domElement.getBoundingClientRect();
      const p=snapAt(ev.clientX-r.left, ev.clientY-r.top); if(!p) return;
      if(measurePts.length>=2) clearPair();  // continuous: a new click starts a fresh pair (only latest shown)
      marker(p); measurePts.push(p);
      if(measurePts.length<2){ $('meas').textContent='measure: snap vertex 2  (Esc to exit)'; }
      else { const d=measurePts[0].distanceTo(measurePts[1]); const g=new THREE.BufferGeometry().setFromPoints(measurePts);
        mGroup.add(new THREE.Line(g,new THREE.LineBasicMaterial({color:0xd81b60, depthTest:false})));
        $('meas').textContent='distance: '+d.toFixed(3)+' m  (click=next, Esc=exit)'; }
      return; }
    const mode=$('colorBy').value;
    if(mode==='edge'){ edgePick(ev); return; }
    const hit=pick(ev); if(!hit){ clearSelection(); return; }
    const o=hit.object;
    let sel; if(mode==='floor') sel=allMeshes().filter(m=>m.userData.floor===o.userData.floor);
    else if(mode==='zone') sel=allMeshes().filter(m=>m.userData.zone===o.userData.zone); else sel=[o];
    setSelection(sel, describe(mode,o));
  }
  // click vs orbit-drag: only a near-stationary press is a click
  let downXY=null;
  renderer.domElement.addEventListener('pointerdown', e=>{ if(e.button===0) downXY=[e.clientX,e.clientY]; });
  renderer.domElement.addEventListener('pointerup', e=>{ if(e.button!==0||!downXY) return;
    const moved=Math.hypot(e.clientX-downXY[0], e.clientY-downXY[1]); downXY=null; if(moved<=5) handleClick(e); });
  renderer.domElement.addEventListener('pointermove', e=>{ if(!measuring) return;
    const r=renderer.domElement.getBoundingClientRect(); const p=snapAt(e.clientX-r.left, e.clientY-r.top);
    if(p){ snap.position.copy(p); snap.visible=true; } else snap.visible=false; });

  // ---- display toggles + explode ----
  // At explode=0 the duplicate of each coincident reciprocal pair is HIDDEN (solid
  // clean shell, no gaps, no z-fight); at explode>0 ALL faces show (each zone a
  // closed box) separated by the offset.
  function applyFilter(){ const f=parseInt($('floorSel').value,10);
    const exploded=parseFloat($('explode').value)>0;
    const sw=$('showWalls').checked, swin=$('showWin').checked, se=$('showEdges').checked;
    const okF=(u)=>(f<0||u.floor===f) && (exploded || !u.dup);
    surfMeshes.forEach(m=>m.visible = sw && okF(m.userData));
    winMeshes.forEach(m=>m.visible = swin && okF(m.userData));
    edgeSegs.forEach(e=>e.visible = se && okF(e.userData)); }
  function explodeOffset(zone){ const amt=parseFloat($('explode').value); if(amt<=0) return new THREE.Vector3();
    if($('explodeMode').value==='floor') return new THREE.Vector3(0,0, (zoneFloor[zone]||0)*amt*radius*1.0);
    return (zoneDir[zone]||new THREE.Vector3()).clone().multiplyScalar(amt*radius*1.2);  // zone: full 3D radial
  }
  function applyExplode(){ surfMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    winMeshes.forEach(m=>m.position.copy(explodeOffset(m.userData.zone)));
    edgeSegs.forEach(e=>e.position.copy(explodeOffset(e.userData.zone)));
    applyFilter(); }  // re-evaluate dup visibility when crossing explode 0 ↔ >0

  // ---- right-side info (structured) ----
  function row(k,v){ return '<div class="kv"><span>'+k+'</span><b>'+v+'</b></div>'; }
  $('hud').innerHTML =
    '<div class="hh">MODEL</div>' + row('zones',(GEO.zones||[]).length) + row('surfaces',SURF.length) + row('windows',WINS.length) +
    '<div class="hh">BOUNDING BOX</div>' + row('width (x)',size.x.toFixed(2)+' m') + row('depth (y)',size.y.toFixed(2)+' m') +
    row('height (z)',size.z.toFixed(2)+' m') + row('floors',BASES.length);

  // ---- section controls ----
  const secDiv=$('sections'); secDiv.innerHTML='<h2>section cuts</h2>';
  AX.forEach(a=>{ const wrap=document.createElement('div'); wrap.className='sec'; const step=((a.max-a.min)/200)||0.01;
    wrap.innerHTML='<label class="chk"><input type="checkbox" id="en'+a.key+'"> cut '+a.key+'</label>'+
      '<input type="range" id="pos'+a.key+'" min="'+a.min+'" max="'+a.max+'" step="'+step+'" value="'+a.max+'">'+
      '<label class="chk"><input type="checkbox" id="flip'+a.key+'"> flip side</label>';
    secDiv.appendChild(wrap);
    const refresh=()=>{a.enabled=$('en'+a.key).checked; a.flip=$('flip'+a.key).checked; a.pos=parseFloat($('pos'+a.key).value); updatePlane(a); applyClipping();};
    $('en'+a.key).onchange=refresh; $('pos'+a.key).oninput=refresh; $('flip'+a.key).onchange=refresh; });

  // ---- floor select + wiring ----
  const fs=$('floorSel'); BASES.forEach((b,i)=>{const o=document.createElement('option'); o.value=i; o.textContent='F'+(i+1)+' (z='+b.toFixed(2)+')'; fs.appendChild(o);});
  $('colorBy').onchange=()=>{ refreshColors(); clearSelection(); }; fs.onchange=applyFilter;
  $('showWalls').onchange=applyFilter; $('showWin').onchange=applyFilter; $('showEdges').onchange=applyFilter;
  $('opacity').oninput=e=>{const v=parseFloat(e.target.value); surfMeshes.forEach(m=>{m.material.opacity=v; m.material.transparent=v<1;});};
  $('explode').oninput=applyExplode; $('explodeMode').onchange=applyExplode;
  $('measure').onclick=()=>{ measuring ? clearMeasure() : startMeasure(); };  // toggle
  $('clearMeasure').onclick=clearMeasure;
  window.addEventListener('keydown', e=>{ if(e.key==='Escape' && measuring) clearMeasure(); });
  $('reset').onclick=defaultView;
  $('savePng').onclick=()=>{ renderer.render(scene,camera); const a=document.createElement('a');
    a.download='geometry_view.png'; a.href=renderer.domElement.toDataURL('image/png'); a.click(); };

  refreshColors(); applyFilter(); applyExplode(); applyClipping(); defaultView();
  window.addEventListener('resize',()=>{ camera.aspect=window.innerWidth/window.innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight); });
  (function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();
})();
"""

_PANEL_HTML = r"""
<div id="panel">
  <h1>Geometry inspection</h1>
  <div class="subtitle">__TITLE__</div>

  <h2>select by</h2>
  <select id="colorBy"><option value="floor">floor</option><option value="zone">zone</option><option value="surface">surface</option><option value="edge">edge</option></select>
  <div class="hint">click to select &middot; floor / zone (volume) / surface (area) / edge (length)</div>

  <h2>floor</h2>
  <select id="floorSel"><option value="-1">all floors</option></select>

  <h2>display</h2>
  <label class="rng">wall opacity</label>
  <input type="range" id="opacity" min="0.05" max="1" step="0.05" value="1">
  <label class="rng">exploded view</label>
  <select id="explodeMode"><option value="floor">by floor</option><option value="zone">by zone</option></select>
  <input type="range" id="explode" min="0" max="1" step="0.02" value="0">
  <label class="chk"><input type="checkbox" id="showWalls" checked> wall / floor / roof faces</label>
  <label class="chk"><input type="checkbox" id="showWin" checked> windows</label>
  <label class="chk"><input type="checkbox" id="showEdges" checked> edges</label>

  <div id="sections"></div>

  <h2>tools</h2>
  <button id="measure">measure (vertex &rarr; vertex)</button>
  <button id="clearMeasure">clear measure</button>
  <button id="savePng">save PNG</button>
  <button id="reset">reset view</button>
</div>
<div id="rinfo">
  <div id="hud"></div>
  <div id="sel"></div>
  <div id="meas"></div>
</div>
"""

_STYLE = r"""
  * { box-sizing: border-box; }
  html, body { margin:0; height:100%; overflow:hidden; font:13px/1.4 system-ui, sans-serif; }
  #app { position:fixed; inset:0; }
  #panel { position:absolute; top:14px; left:14px; width:280px; max-height:calc(100% - 28px); overflow-y:auto;
    background:rgba(255,255,255,0.96); border:1px solid #d7dbe0; border-radius:10px; padding:16px 18px;
    box-shadow:0 4px 16px rgba(0,0,0,0.14); color:#222; }
  #panel h1 { font-size:16px; font-weight:600; margin:0 0 2px; }
  #panel .subtitle { color:#8a9099; font-size:12px; margin-bottom:6px; }
  #panel .hint { color:#8a9099; font-size:11.5px; margin:5px 0 2px; }
  #panel h2 { font-size:11px; font-weight:700; margin:18px 0 7px; color:#5b6b86; text-transform:uppercase; letter-spacing:.06em; }
  #panel label { display:block; }
  #panel label.rng { font-size:12.5px; color:#555; margin:10px 0 5px; }
  #panel label.chk { font-size:13px; margin:7px 0; cursor:pointer; }
  #panel label.chk input { margin-right:7px; vertical-align:-1px; }
  #panel input[type=range] { width:100%; margin:2px 0 4px; accent-color:#3b6ea5; }
  #panel select { width:100%; padding:6px 8px; font-size:13px; border:1px solid #cfd4da; border-radius:6px; background:#fff; }
  #panel button { width:100%; padding:8px; margin-top:8px; font-size:13px; cursor:pointer;
    border:1px solid #cfd4da; border-radius:7px; background:#f4f6f8; color:#2a3340; transition:background .12s; }
  #panel button:hover { background:#e7ebf0; }
  .sec { border-top:1px solid #ebedf0; padding-top:9px; margin-top:9px; }
  #rinfo { position:absolute; top:12px; right:12px; width:300px; display:flex; flex-direction:column; gap:10px; }
  #hud { background:rgba(20,28,44,0.88); color:#eef; padding:12px 16px; border-radius:8px; font-size:15px; }
  #hud .hh { font-size:12px; letter-spacing:.05em; color:#8fb0e0; margin:8px 0 3px; text-transform:uppercase; }
  #hud .hh:first-child { margin-top:0; }
  #hud .kv { display:flex; justify-content:space-between; padding:2px 0 2px 10px; }
  #hud .kv span { color:#c7d2e0; }
  #hud .kv b { color:#fff; font-weight:600; }
  #sel { display:none; background:rgba(38,50,80,0.92); color:#cfe3ff; padding:10px 16px; border-radius:8px; font-size:16px; font-weight:600; }
  #meas { display:none; background:#d81b60; color:#fff; padding:11px 16px; border-radius:8px; font-size:19px; font-weight:700; box-shadow:0 2px 8px rgba(216,27,96,0.45); }
"""

_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Geometry inspection — __TITLE__</title>
<style>__STYLE__</style></head>
<body>
<div id="app"></div>
__PANEL__
<script>__THREE_JS__</script>
<script>__ORBIT_JS__</script>
<script>window.GEO = __GEO_JSON__;</script>
<script>__APP_JS__</script>
</body></html>
"""


def app_js() -> str:
    """The viewer app script (for embedding + standalone syntax checking)."""
    return _APP_JS


def build_viewer_html(data: dict, *, title: str = "building geometry") -> str:
    three_js = (_VENDOR / "three.min.js").read_text(encoding="utf-8")
    orbit_js = (_VENDOR / "OrbitControls.js").read_text(encoding="utf-8")
    geo = {
        "zones": data.get("zones", []),
        "surfaces": data.get("surfaces", []),
        "windows": data.get("windows", []),
    }
    safe_title = html.escape(title)  # HTML-context (title tag + panel text)
    return (
        _HTML
        .replace("__STYLE__", _STYLE)
        .replace("__PANEL__", _PANEL_HTML.replace("__TITLE__", safe_title))
        .replace("__THREE_JS__", three_js)
        .replace("__ORBIT_JS__", orbit_js)
        .replace("__GEO_JSON__", _js_embed(geo))  # script-safe (no </script> breakout)
        .replace("__APP_JS__", _APP_JS)
        .replace("__TITLE__", safe_title)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="building_geometry.json")
    ap.add_argument("--out", help="output HTML (default: <json dir>/geometry_viewer.html)")
    ap.add_argument("--title", default="")
    args = ap.parse_args()
    j = Path(args.json)
    data = json.loads(j.read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else j.with_name("geometry_viewer.html")
    title = args.title or j.parent.parent.name or j.stem
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_viewer_html(data, title=title), encoding="utf-8")
    kb = out.stat().st_size // 1024
    print(f"wrote {out}  ({kb} KB, offline; orbit / opacity / sections / explode / vertex-measure)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
