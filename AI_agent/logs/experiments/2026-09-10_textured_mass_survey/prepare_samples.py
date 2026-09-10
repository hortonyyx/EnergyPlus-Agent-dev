"""Inspect acquired SUM tiles; export geometry/texture only and material previews.

This is a survey utility, not a BIM generator. Original labelled PLY files stay
in raw/. Only newly constructed position/index/UV/texture arrays enter derived/.
The PNG preview uses one texture sample per face and is for selecting scenes;
the HTML viewer preserves the original UV texture mapping.
"""
from pathlib import Path
import base64
import hashlib
import io
import json
import math

import numpy as np
from PIL import Image, ImageDraw
import trimesh

REPO = Path(__file__).resolve().parents[4]
ASSETS = REPO / "case_tests/textured_mass"
EVIDENCE = Path(__file__).resolve().parent
VENDOR = REPO / "scripts/tool_scripts/vendor"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preview(mesh, target, azimuth):
    vertices = mesh.vertices - mesh.bounds.mean(axis=0)
    a, e = math.radians(azimuth), math.radians(38)
    right = np.array([-math.sin(a), math.cos(a), 0])
    up = np.array([-math.cos(a)*math.sin(e), -math.sin(a)*math.sin(e), math.cos(e)])
    front = np.cross(right, up)
    xy = np.column_stack((vertices @ right, vertices @ up))
    xy *= 1250 / max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]) * 1.45)
    xy[:, 0] += 700
    xy[:, 1] = 450 - xy[:, 1]
    faces = mesh.faces
    uv = mesh.visual.uv[faces].mean(axis=1)
    colors = trimesh.visual.color.uv_to_color(uv, mesh.visual.material.image)[:, :3]
    order = np.argsort((vertices @ front)[faces].mean(axis=1))
    result = Image.new("RGB", (1400, 900), (238, 242, 246))
    draw = ImageDraw.Draw(result)
    for index in order:
        draw.polygon([tuple(p) for p in xy[faces[index]]], fill=tuple(colors[index]))
    result.save(target)


def viewer(mesh, target, title):
    center = mesh.bounds.mean(axis=0)
    b64 = lambda array: base64.b64encode(array.tobytes()).decode()
    positions = (mesh.vertices - center).astype("<f4")
    uv = mesh.visual.uv.astype("<f4")
    faces = mesh.faces.astype("<u4")
    buf = io.BytesIO()
    mesh.visual.material.image.convert("RGB").save(buf, "JPEG", quality=95)
    texture = base64.b64encode(buf.getvalue()).decode()
    payload = json.dumps({"position": b64(positions), "uv": b64(uv),
                          "indices": b64(faces), "texture": texture})
    page = '''<!doctype html><html lang="zh"><meta charset="utf-8">
<title>__TITLE__</title><style>body{margin:0;font:15px sans-serif;background:#edf2f7}aside{position:absolute;top:12px;left:12px;background:#fffe;padding:14px;max-width:440px;z-index:2;line-height:1.6}button{margin:6px}</style>
<aside><b>__TITLE__</b><br>原始实景几何与图片贴图；尚未生成 BIM。拖动旋转，滚轮缩放。<br>无房间/门窗语义；数据集标签未带入。<br>City of Helsinki / SUM · Gao et al., 2021<br><button onclick="resetView()">整体</button><button onclick="material.wireframe=!material.wireframe">网格</button><button onclick="material.map=material.map?null:texture;material.needsUpdate=true">贴图</button><br><span id="state">加载中</span></aside>
<script>__THREE__</script><script>__ORBIT__</script><script>
const data=__DATA__;
function bytes(s){const v=atob(s);return Uint8Array.from(v,c=>c.charCodeAt(0)).buffer;}
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputEncoding=THREE.sRGBEncoding;document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0xedf2f7);
const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,0.1,5000);camera.up.set(0,0,1);
const controls=new THREE.OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(bytes(data.position)),3));geometry.setAttribute('uv',new THREE.BufferAttribute(new Float32Array(bytes(data.uv)),2));geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(bytes(data.indices)),1));
const texture=new THREE.TextureLoader().load('data:image/jpeg;base64,'+data.texture,()=>{document.getElementById('state').textContent='已加载几何与贴图';},undefined,()=>{document.getElementById('state').textContent='贴图加载失败';});texture.encoding=THREE.sRGBEncoding;
const material=new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide});scene.add(new THREE.Mesh(geometry,material));
function resetView(){camera.position.set(220,-260,230);controls.target.set(0,0,0);controls.update();}resetView();
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
function tick(){requestAnimationFrame(tick);controls.update();renderer.render(scene,camera);}tick();
</script></html>'''
    page = (page.replace("__TITLE__", title)
            .replace("__THREE__", (VENDOR / "three.min.js").read_text())
            .replace("__ORBIT__", (VENDOR / "OrbitControls.js").read_text())
            .replace("__DATA__", payload))
    target.write_text(page, encoding="utf-8")


def main():
    rows = []
    for source in sorted(ASSETS.glob("raw/Tile*/*.ply")):
        tile = source.parent.name
        loaded = trimesh.load(source, process=False)
        assert loaded.visual.kind == "texture"
        # Reconstruct from an explicit allowlist. Never export _ply_raw, labels,
        # face colors, segment IDs or annotation probabilities into inputs.
        mesh = trimesh.Trimesh(vertices=loaded.vertices.copy(), faces=loaded.faces.copy(),
            visual=trimesh.visual.TextureVisuals(uv=loaded.visual.uv.copy(),
                image=loaded.visual.material.image.copy()), process=False)
        assert np.isfinite(mesh.vertices).all() and np.isfinite(mesh.visual.uv).all()
        assert mesh.faces.min() >= 0 and mesh.faces.max() < len(mesh.vertices)
        dest = ASSETS / "derived" / tile
        dest.mkdir(parents=True, exist_ok=True)
        origin = mesh.bounds.mean(axis=0)
        exported = mesh.copy()
        exported.vertices -= origin
        exported.vertices = exported.vertices[:, [0, 2, 1]] * [1, 1, -1]
        glb = dest / "input.glb"
        glb.write_bytes(trimesh.Scene(exported).export(file_type="glb"))
        # Check serialized output too, rather than relying on an in-memory copy.
        import struct
        raw = glb.read_bytes()
        n, kind = struct.unpack_from("<II", raw, 12)
        assert kind == 0x4E4F534A
        header = json.loads(raw[20:20+n])
        for item in header["meshes"]:
            assert not item.get("extras")
            for primitive in item["primitives"]:
                assert set(primitive["attributes"]) <= {"POSITION", "NORMAL", "TEXCOORD_0"}
        reread = trimesh.load(glb, force="scene", process=False)
        assert sum(len(m.faces) for m in reread.geometry.values()) == len(mesh.faces)
        assert all(m.visual.kind == "texture" for m in reread.geometry.values())
        for angle in [-50, 130]:
            preview(mesh, EVIDENCE / f"{tile}_{angle}.png", angle)
        viewer(mesh, dest / "viewer.html", tile)
        row = {"id": tile, "source": str(source.relative_to(REPO)),
            "input": str(glb.relative_to(REPO)), "source_sha256": sha(source),
            "input_sha256": sha(glb), "vertices_after_uv_seam_split": len(mesh.vertices),
            "triangles": len(mesh.faces), "bounds_original": mesh.bounds.tolist(),
            "texture_size": list(mesh.visual.material.image.size),
            "input_transform": {"origin_original": origin.tolist(), "mapping": "(x,y,z) -> (x-origin_x,z-origin_z,-(y-origin_y))"},
            "label_attributes_exported": False, "texture_roundtrip": "pass",
            "browser_runtime": "not_tested", "bim_generation": "not_run"}
        rows.append(row)
        print(json.dumps(row), flush=True)
    (ASSETS / "inspection.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2)+"\n")


if __name__ == "__main__":
    main()
