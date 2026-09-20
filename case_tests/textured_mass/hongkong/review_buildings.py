"""Repack complete source scenes and review them offline without altering old GLBs.

This is a dataset repair/inspection utility, not a BIM generator. The viewer is
unlit and double-sided; it retains all scene parts and alpha but is not PBR.
"""
from __future__ import annotations

import argparse
import base64
import html
import hashlib
import io
import json
from pathlib import Path
import sys
import struct

import numpy as np
import trimesh
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from src.agent.geometry.mesh_observation import MeshObservation
from pack_building import pack_building


def encoded(array, dtype):
    return base64.b64encode(np.asarray(array, dtype=dtype).tobytes()).decode("ascii")


def write_viewer(asset: Path, target: Path, bid: str):
    scene = trimesh.load(asset, force="scene", process=False)
    raw = asset.read_bytes()
    json_length = struct.unpack_from("<I", raw, 12)[0]
    doc = json.loads(raw[20:20 + json_length])
    binary_start = 20 + json_length + 8
    textures = {}
    for entry in doc["images"]:
        view = doc["bufferViews"][entry["bufferView"]]
        offset = binary_start + view.get("byteOffset", 0)
        data = raw[offset:offset + view["byteLength"]]
        decoded = Image.open(io.BytesIO(data)).convert("RGBA")
        key = (decoded.size, hashlib.sha256(decoded.tobytes()).hexdigest())
        textures[key] = (entry["mimeType"], base64.b64encode(data).decode("ascii"))
    parts = []
    for node in scene.graph.nodes_geometry:
        transform, key = scene.graph.get(node)
        mesh = scene.geometry[key]
        material = mesh.visual.material
        image = getattr(material, "baseColorTexture", None)
        if image is None:
            image = getattr(material, "image", None)
        if image is None:
            raise ValueError(f"{node}: missing texture")
        # Reuse the original compressed bytes; prove the decoded image matches
        # this material before binding it, rather than assuming part order.
        decoded = image.convert("RGBA")
        mime, texture = textures[(decoded.size, hashlib.sha256(decoded.tobytes()).hexdigest())]
        factor = getattr(material, "baseColorFactor", None)
        factor = np.ones(4) if factor is None else np.asarray(factor, dtype=float)
        if factor.max() > 1:
            factor = factor / 255
        parts.append({"node": node, "position": encoded(trimesh.transform_points(mesh.vertices, transform), "<f4"),
            "uv": encoded(mesh.visual.uv, "<f4"), "indices": encoded(mesh.faces, "<u4"),
            "texture": texture, "textureMime": mime,
            "factor": factor.tolist(), "alphaMode": getattr(material, "alphaMode", None) or "OPAQUE",
            "alphaCutoff": getattr(material, "alphaCutoff", None) or 0.5,
            "faces": len(mesh.faces)})
    payload = json.dumps({"parts": parts, "bounds": scene.bounds.tolist()}, separators=(",", ":"))
    template = r'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>__BID__ · 完整场景核查</title><style>body{margin:0;font:14px system-ui;background:#edf2f7}aside{position:absolute;top:10px;left:10px;right:10px;background:#ffffffdf;padding:10px;z-index:2;line-height:1.5}button{margin:5px}canvas{display:block}</style>
<aside><b>__BID__</b> · 完整原场景转换，尚非 BIM<br>© 香港特别行政区政府 地政总署 · 仅局部平移，保留全部网格、贴图、轴向变换与透明材质。用途未核实。<br>
<button onclick="setView(35)">A 面</button><button onclick="setView(125)">B 面</button><button onclick="setView(215)">C 面</button><button onclick="setView(305)">D 面</button><button onclick="meshes.forEach(m=>m.material.wireframe=!m.material.wireframe)">网格</button><span id="state">载入贴图…</span></aside>
<script>__THREE__</script><script>__ORBIT__</script><script>
const data=__DATA__;
function bytes(s){return Uint8Array.from(atob(s),c=>c.charCodeAt(0)).buffer;}
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(1);renderer.outputEncoding=THREE.sRGBEncoding;document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0xedf2f7);
const camera=new THREE.PerspectiveCamera(40,innerWidth/innerHeight,0.01,10000);camera.up.set(0,1,0);
const controls=new THREE.OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
const meshes=[];window.AUDIT={expectedParts:data.parts.length,loadedTextures:0,faces:0,textureErrors:[]};
for(const p of data.parts){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(bytes(p.position)),3));g.setAttribute('uv',new THREE.BufferAttribute(new Float32Array(bytes(p.uv)),2));g.setIndex(new THREE.BufferAttribute(new Uint32Array(bytes(p.indices)),1));
const tex=new THREE.TextureLoader().load('data:'+p.textureMime+';base64,'+p.texture,()=>{AUDIT.loadedTextures++;document.getElementById('state').textContent=AUDIT.loadedTextures+'/'+AUDIT.expectedParts+' 贴图已载入';},undefined,()=>AUDIT.textureErrors.push(p.node));tex.encoding=THREE.sRGBEncoding;tex.wrapS=tex.wrapT=THREE.RepeatWrapping;
const mat=new THREE.MeshBasicMaterial({map:tex,side:THREE.DoubleSide,color:new THREE.Color(p.factor[0],p.factor[1],p.factor[2]),transparent:p.alphaMode==='BLEND',opacity:p.factor[3],alphaTest:p.alphaMode==='MASK'?p.alphaCutoff:0});
const m=new THREE.Mesh(g,mat);scene.add(m);meshes.push(m);AUDIT.faces+=p.faces;}
const lo=new THREE.Vector3(...data.bounds[0]),hi=new THREE.Vector3(...data.bounds[1]);const centre=lo.clone().add(hi).multiplyScalar(.5),radius=hi.clone().sub(lo).length()/2;
window.setView=function(degrees){const a=degrees*Math.PI/180,e=12*Math.PI/180;const fov=Math.min(camera.fov*Math.PI/180,2*Math.atan(Math.tan(camera.fov*Math.PI/360)*camera.aspect));const dist=radius/Math.sin(fov/2)*1.18;camera.position.set(centre.x+dist*Math.cos(e)*Math.sin(a),centre.y+dist*Math.sin(e),centre.z+dist*Math.cos(e)*Math.cos(a));controls.target.copy(centre);controls.update();};setView(35);
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
function tick(){requestAnimationFrame(tick);controls.update();renderer.render(scene,camera);}tick();
</script></html>'''
    vendor = REPO / "scripts/tool_scripts/vendor"
    target.write_text(template.replace("__BID__", html.escape(bid))
        .replace("__THREE__", (vendor / "three.min.js").read_text())
        .replace("__ORBIT__", (vendor / "OrbitControls.js").read_text())
        .replace("__DATA__", payload))
    return {"parts": len(parts), "faces": sum(p["faces"] for p in parts),
            "bounds_y_up_m": scene.bounds.tolist(),
            "viewer_mode": "unlit double-sided texture and alpha inspection; not PBR"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only")
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((HERE / "single_buildings/manifest.json").read_text())
    out = HERE / "repaired_buildings"
    out.mkdir(exist_ok=True)
    results = []
    for rec in manifest["buildings"]:
        bid = rec["building_id"]
        if args.only and bid != args.only:
            continue
        original = HERE / "single_buildings" / bid
        target = out / bid
        target.mkdir(exist_ok=True)
        packed = pack_building(original / (bid + ".gltf"), target / "input.glb")
        view = write_viewer(target / "input.glb", target / "viewer.html", bid)
        item = {"building_id": bid, "original_record": f"../../single_buildings/{bid}/record.json",
                "conversion": packed, "viewer": view, "building_use": "not_verified"}
        try:
            obs = MeshObservation(target / "input.glb")
            item["mesh_observation"] = {"status": "pass", "description": obs.describe()}
        except ValueError as error:
            item["mesh_observation"] = {"status": "unsupported", "reason": str(error)}
        (target / "repair.json").write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n")
        results.append(item)
        print(bid, view["parts"], view["faces"], item["mesh_observation"]["status"], flush=True)
    if args.screenshots:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
            for item in results:
                target = out / item["building_id"]
                context = browser.new_context(viewport={"width": 1000, "height": 850}, offline=True)
                page = context.new_page()
                errors, requests = [], []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("requestfailed", lambda r: errors.append(r.url))
                page.on("request", lambda r: requests.append(r.url) if r.url.startswith(("http:", "https:")) else None)
                page.goto((target / "viewer.html").as_uri())
                page.wait_for_function("window.AUDIT && AUDIT.loadedTextures===AUDIT.expectedParts", timeout=60000)
                snapshots = []
                for label, angle in zip("ABCD", (35, 125, 215, 305)):
                    page.evaluate("a => setView(a)", angle)
                    page.wait_for_timeout(150)
                    snapshots.append(page.locator("canvas").screenshot(path=str(target / f"view_{label}.png")))
                check = page.evaluate("AUDIT")
                assert not errors and not requests and not check["textureErrors"], (errors, requests, check)
                assert check["faces"] == item["viewer"]["faces"]
                assert snapshots[0] != snapshots[1]
                item["browser"] = {**check, "page_errors": errors, "external_requests": requests,
                                   "four_views_differ": len(set(snapshots)) == 4}
                context.close()
            browser.close()
    (out / ("review_" + args.only + ".json" if args.only else "review.json")).write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
