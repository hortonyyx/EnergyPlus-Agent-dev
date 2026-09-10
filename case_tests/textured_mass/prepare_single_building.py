#!/usr/bin/env python3
"""Extract one textured building from a label-free city-tile GLB.

The target footprint and source transform are explicit in selection.json.  This
tool never reads the labelled SUM PLY: it crops the already sanitised tile GLB,
keeps its UV texture, recentres the selected building, and writes inspectable
static views plus machine-readable checks.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import shapely
from shapely.geometry import Polygon
import trimesh


REPO = Path(__file__).resolve().parents[2]
VENDOR = REPO / "scripts/tool_scripts/vendor"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def material_image(mesh: trimesh.Trimesh) -> Image.Image:
    material = mesh.visual.material
    image = getattr(material, "image", None)
    if image is None:
        image = getattr(material, "baseColorTexture", None)
    if image is None:
        raise ValueError("source mesh has UVs but no texture image")
    return image.convert("RGB")


def mask_texture_to_selected_faces(mesh: trimesh.Trimesh) -> tuple[Image.Image, int, int]:
    """Blank atlas pixels not referenced by the selected building faces."""
    source = material_image(mesh)
    mask = Image.new("L", source.size, 0)
    draw = ImageDraw.Draw(mask)
    width, height = source.size
    for triangle in mesh.visual.uv[mesh.faces]:
        points = [
            (float(uv[0]) * (width - 1), (1.0 - float(uv[1])) * (height - 1))
            for uv in triangle
        ]
        draw.polygon(points, fill=255)
    # Preserve a two-pixel sampling margin around triangle edges.
    mask = mask.filter(ImageFilter.MaxFilter(5))
    histogram = mask.histogram()
    retained = sum(histogram[1:])
    neutral = Image.new("RGB", source.size, (127, 127, 127))
    return Image.composite(source, neutral, mask), retained, width * height


def render_preview(mesh: trimesh.Trimesh, target: Path, azimuth: float, elevation: float) -> None:
    # Work in a conventional Z-up view frame for this small software renderer.
    vertices = np.column_stack((mesh.vertices[:, 0], -mesh.vertices[:, 2], mesh.vertices[:, 1]))
    vertices -= vertices.mean(axis=0)
    azimuth_rad, elevation_rad = math.radians(azimuth), math.radians(elevation)
    right = np.array([-math.sin(azimuth_rad), math.cos(azimuth_rad), 0.0])
    up = np.array([
        -math.cos(azimuth_rad) * math.sin(elevation_rad),
        -math.sin(azimuth_rad) * math.sin(elevation_rad),
        math.cos(elevation_rad),
    ])
    front = np.cross(right, up)
    xy = np.column_stack((vertices @ right, vertices @ up))
    span = max(float(np.ptp(xy[:, 0])), float(np.ptp(xy[:, 1])) * 1.45)
    xy *= 1300.0 / span
    xy[:, 0] += 750.0
    xy[:, 1] = 500.0 - xy[:, 1]

    faces = mesh.faces
    uv = mesh.visual.uv[faces].mean(axis=1)
    colors = trimesh.visual.color.uv_to_color(uv, material_image(mesh))[:, :3]
    order = np.argsort((vertices @ front)[faces].mean(axis=1))
    result = Image.new("RGB", (1500, 1000), (238, 242, 246))
    draw = ImageDraw.Draw(result)
    for face_id in order:
        draw.polygon([tuple(point) for point in xy[faces[face_id]]], fill=tuple(colors[face_id]))
    result.save(target, optimize=True)


def render_footprint_overlay(
    mesh: trimesh.Trimesh, footprint: Polygon, footprint_center: np.ndarray, target: Path
) -> None:
    xz = mesh.vertices[:, [0, 2]]
    outline = np.asarray(footprint.exterior.coords)
    outline = np.column_stack((
        outline[:, 0] - footprint_center[0],
        -(outline[:, 1] - footprint_center[1]),
    ))
    all_points = np.vstack((xz, outline))
    lower, upper = all_points.min(axis=0), all_points.max(axis=0)
    span = np.maximum(upper - lower, 1e-9)
    scale = min(1300.0 / span[0], 850.0 / span[1])

    def project(points: np.ndarray) -> np.ndarray:
        result = (points - (lower + upper) / 2.0) * scale
        result[:, 0] += 750.0
        result[:, 1] = 500.0 - result[:, 1]
        return result

    projected = project(xz.copy())
    faces = mesh.faces
    uv = mesh.visual.uv[faces].mean(axis=1)
    colors = trimesh.visual.color.uv_to_color(uv, material_image(mesh))[:, :3]
    # Looking down: low surfaces first and roof surfaces last.
    order = np.argsort(mesh.triangles_center[:, 1])
    image = Image.new("RGB", (1500, 1000), (238, 242, 246))
    draw = ImageDraw.Draw(image)
    for face_id in order:
        draw.polygon([tuple(point) for point in projected[faces[face_id]]], fill=tuple(colors[face_id]))
    draw.line([tuple(point) for point in project(outline.copy())], fill=(220, 55, 45), width=5, joint="curve")
    draw.rectangle((25, 25, 545, 78), fill=(255, 255, 255), outline=(220, 55, 45), width=2)
    draw.text((43, 42), "public OSM footprint (crop adds 0.35 m buffer)", fill=(90, 25, 20))
    image.save(target, optimize=True)


def write_offline_viewer(mesh: trimesh.Trimesh, target: Path, title: str) -> None:
    """Reuse the survey viewer pattern with Y-up coordinates for this crop."""
    encode = lambda array: base64.b64encode(array.tobytes()).decode("ascii")
    positions = mesh.vertices.astype("<f4")
    uv = mesh.visual.uv.astype("<f4")
    faces = mesh.faces.astype("<u4")
    texture_buffer = io.BytesIO()
    material_image(mesh).save(texture_buffer, "JPEG", quality=95)
    payload = json.dumps({
        "position": encode(positions),
        "uv": encode(uv),
        "indices": encode(faces),
        "texture": base64.b64encode(texture_buffer.getvalue()).decode("ascii"),
    })
    page = '''<!doctype html><html lang="zh"><meta charset="utf-8">
<title>__TITLE__</title><style>body{margin:0;font:15px sans-serif;background:#edf2f7}aside{position:absolute;top:12px;left:12px;background:#fffe;padding:14px;max-width:500px;z-index:2;line-height:1.6}button{margin:6px}</style>
<aside><b>__TITLE__</b><br>公开轮廓裁出的实景表面与完整 UV 贴图；尚未生成 BIM。拖动旋转，滚轮缩放。<br>无房间/门窗语义，无 SUM 标签；裁剪网格不闭合。<br>City of Helsinki / SUM · Gao et al., 2021<br><button onclick="resetView()">整体</button><button onclick="material.wireframe=!material.wireframe">网格</button><button onclick="material.map=material.map?null:texture;material.needsUpdate=true">贴图</button><br><span id="state">加载中</span></aside>
<script>__THREE__</script><script>__ORBIT__</script><script>
const data=__DATA__;
function bytes(s){const v=atob(s);return Uint8Array.from(v,c=>c.charCodeAt(0)).buffer;}
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputEncoding=THREE.sRGBEncoding;document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0xedf2f7);
const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,0.1,2000);camera.up.set(0,1,0);
const controls=new THREE.OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(bytes(data.position)),3));geometry.setAttribute('uv',new THREE.BufferAttribute(new Float32Array(bytes(data.uv)),2));geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(bytes(data.indices)),1));
const texture=new THREE.TextureLoader().load('data:image/jpeg;base64,'+data.texture,()=>{document.getElementById('state').textContent='已加载完整 UV 贴图';},undefined,()=>{document.getElementById('state').textContent='贴图加载失败';});texture.encoding=THREE.sRGBEncoding;
const material=new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide});scene.add(new THREE.Mesh(geometry,material));
function resetView(){camera.position.set(95,80,115);controls.target.set(0,15,0);controls.update();}resetView();
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
function tick(){requestAnimationFrame(tick);controls.update();renderer.render(scene,camera);}tick();
</script></html>'''
    page = (
        page.replace("__TITLE__", title)
        .replace("__THREE__", (VENDOR / "three.min.js").read_text(encoding="utf-8"))
        .replace("__ORBIT__", (VENDOR / "OrbitControls.js").read_text(encoding="utf-8"))
        .replace("__DATA__", payload)
    )
    target.write_text(page, encoding="utf-8")


def read_glb_json(path: Path) -> dict:
    raw = path.read_bytes()
    if raw[:4] != b"glTF":
        raise ValueError(f"not a binary glTF file: {path}")
    chunk_length, chunk_kind = struct.unpack_from("<II", raw, 12)
    if chunk_kind != 0x4E4F534A:
        raise ValueError("first GLB chunk is not JSON")
    return json.loads(raw[20 : 20 + chunk_length])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--tile-glb", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"use a new output directory; refusing to overwrite {args.out}")

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    actual_source_sha = sha256(args.tile_glb)
    expected_source_sha = selection["source_tile"]["sanitised_input_sha256"]
    if actual_source_sha != expected_source_sha:
        raise ValueError(f"source hash changed: expected {expected_source_sha}, got {actual_source_sha}")

    scene = trimesh.load(args.tile_glb, force="scene", process=False)
    if len(scene.geometry) != 1:
        raise ValueError(f"expected one source mesh, found {len(scene.geometry)}")
    source_mesh = next(iter(scene.geometry.values()))
    if source_mesh.visual.kind != "texture":
        raise ValueError(f"source mesh is not textured: {source_mesh.visual.kind}")

    origin = np.asarray(selection["source_tile"]["input_transform"]["origin_original"], dtype=float)
    # Sanitised tile mapping: original (x,y,z) -> (x-ox,z-oz,-(y-oy)).
    tile_centres = source_mesh.triangles_center
    original_centres = np.column_stack((
        tile_centres[:, 0] + origin[0],
        -tile_centres[:, 2] + origin[1],
        tile_centres[:, 1] + origin[2],
    ))
    footprint = Polygon(selection["footprint"]["helsinki_local_xy_m"])
    if not footprint.is_valid:
        raise ValueError("target footprint is invalid")
    buffered = footprint.buffer(float(selection["crop"]["horizontal_buffer_m"]))
    selected = shapely.contains_xy(buffered, original_centres[:, 0], original_centres[:, 1])
    face_ids = np.flatnonzero(selected)
    if not len(face_ids):
        raise ValueError("footprint selected no mesh faces")

    cropped = source_mesh.submesh([face_ids], append=True, repair=False)
    # Recentre without changing scale or orientation. Y remains vertical in GLB.
    footprint_center = np.asarray(footprint.centroid.coords[0])
    original_vertices = np.column_stack((
        cropped.vertices[:, 0] + origin[0],
        -cropped.vertices[:, 2] + origin[1],
        cropped.vertices[:, 1] + origin[2],
    ))
    base_elevation = float(original_vertices[:, 2].min())
    cropped.vertices = np.column_stack((
        original_vertices[:, 0] - footprint_center[0],
        original_vertices[:, 2] - base_elevation,
        -(original_vertices[:, 1] - footprint_center[1]),
    ))

    # Remove surrounding-tile pixels from the atlas while retaining the target
    # face texels and a two-pixel sampling margin. Then preserve the UV mapping
    # but recompress lossily as JPEG quality 95 to keep the input bounded.
    masked_texture, retained_texture_pixels, total_texture_pixels = mask_texture_to_selected_faces(cropped)
    texture_buffer = io.BytesIO()
    masked_texture.save(texture_buffer, "JPEG", quality=95)
    texture_buffer.seek(0)
    jpeg_texture = Image.open(texture_buffer)
    if hasattr(cropped.visual.material, "baseColorTexture"):
        cropped.visual.material.baseColorTexture = jpeg_texture
    else:
        cropped.visual.material.image = jpeg_texture

    args.out.mkdir(parents=True, exist_ok=False)
    output_glb = args.out / "input.glb"
    def strip_export_extras(tree: dict) -> None:
        for exported_mesh in tree.get("meshes", []):
            exported_mesh.pop("extras", None)
            for primitive in exported_mesh.get("primitives", []):
                primitive.pop("extras", None)

    output_glb.write_bytes(trimesh.exchange.gltf.export_glb(
        trimesh.Scene(cropped), tree_postprocessor=strip_export_extras
    ))
    render_preview(cropped, args.out / "view_northwest.png", azimuth=-35, elevation=28)
    render_preview(cropped, args.out / "view_southeast.png", azimuth=145, elevation=28)
    render_preview(cropped, args.out / "view_top.png", azimuth=-35, elevation=89.5)
    render_footprint_overlay(cropped, footprint, footprint_center, args.out / "view_footprint_overlay.png")
    write_offline_viewer(cropped, args.out / "viewer.html", selection["target"]["name"])

    header = read_glb_json(output_glb)
    attribute_sets = []
    extras_present = False
    for item in header.get("meshes", []):
        extras_present |= "extras" in item
        for primitive in item.get("primitives", []):
            attribute_sets.append(sorted(primitive.get("attributes", {})))
            extras_present |= "extras" in primitive
    allowed_attributes = {"POSITION", "NORMAL", "TEXCOORD_0"}
    if any(set(names) - allowed_attributes for names in attribute_sets) or extras_present:
        raise ValueError("unexpected attributes or extras in cropped GLB")

    reread = trimesh.load(output_glb, force="scene", process=False)
    reread_faces = sum(len(mesh.faces) for mesh in reread.geometry.values())
    if reread_faces != len(cropped.faces):
        raise ValueError(f"GLB roundtrip lost faces: {len(cropped.faces)} -> {reread_faces}")
    if not all(mesh.visual.kind == "texture" for mesh in reread.geometry.values()):
        raise ValueError("GLB roundtrip lost texture mapping")

    extents = cropped.extents
    report = {
        "case_id": selection["case_id"],
        "source_tile_glb": selection["source_tile"]["sanitised_input_path"],
        "source_tile_sha256": actual_source_sha,
        "output_glb": "input.glb",
        "output_glb_sha256": sha256(output_glb),
        "selection_method": "face centroid inside public footprint plus documented horizontal buffer",
        "crop_buffer_m": selection["crop"]["horizontal_buffer_m"],
        "footprint_area_m2": footprint.area,
        "footprint_bounds_helsinki_local_m": list(footprint.bounds),
        "source_face_count": len(source_mesh.faces),
        "selected_face_count": len(cropped.faces),
        "selected_vertex_count": len(cropped.vertices),
        "output_bounds_m": cropped.bounds.tolist(),
        "output_extents_m": {
            "east_west": float(extents[0]),
            "vertical": float(extents[1]),
            "north_south": float(extents[2]),
        },
        "original_base_elevation_m_n2000_estimate": base_elevation,
        "watertight": bool(cropped.is_watertight),
        "glb_attribute_sets": attribute_sets,
        "glb_extras_present": extras_present,
        "label_attributes_exported": False,
        "texture_mapping_roundtrip": "pass",
        "texture_encoding": "unused atlas pixels neutralised; selected face texels and 2 px margin recompressed lossily to JPEG quality 95; UV mapping retained",
        "texture_pixels_retained_before_jpeg": retained_texture_pixels,
        "texture_pixels_total": total_texture_pixels,
        "static_views": [
            "view_northwest.png",
            "view_southeast.png",
            "view_top.png",
            "view_footprint_overlay.png",
        ],
        "browser_runtime": "not_tested_no_browser_available",
        "offline_viewer": "viewer.html",
        "bim_generation": "not_run",
    }
    (args.out / "inspection.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
