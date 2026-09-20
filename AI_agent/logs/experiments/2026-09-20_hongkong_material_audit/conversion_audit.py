"""Recheck source glTF, legacy input.glb, and lossless packed GLB for 15 buildings."""

import argparse
import copy
import hashlib
import json
import shutil
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[4]
CASES = ROOT / "case_tests/textured_mass/hongkong/single_buildings"
sys.path.insert(0, str(CASES.parent))
from pack_building import pack_building  # noqa: E402


def glb(path: Path):
    data = path.read_bytes()
    magic, version, total = struct.unpack_from("<4sII", data)
    if (magic, version, total) != (b"glTF", 2, len(data)):
        raise ValueError(f"Invalid GLB header: {path}")
    at = 12
    length, chunk_type = struct.unpack_from("<I4s", data, at)
    if chunk_type != b"JSON":
        raise ValueError("First GLB chunk must be JSON")
    document = json.loads(data[at + 8:at + 8 + length])
    at += 8 + length
    length, chunk_type = struct.unpack_from("<I4s", data, at)
    if chunk_type != b"BIN\x00":
        raise ValueError("Second GLB chunk must be BIN")
    return document, data[at + 8:at + 8 + length]


def primitive_faces(document):
    return [document["accessors"][p["indices"]]["count"] // 3
            for mesh in document.get("meshes", [])
            for p in mesh["primitives"]]


def material_refs(document):
    return [p.get("material") for mesh in document.get("meshes", [])
            for p in mesh["primitives"]]


def image_bytes(document, binary, index):
    image = document["images"][index]
    view = document["bufferViews"][image["bufferView"]]
    a = view.get("byteOffset", 0)
    return binary[a:a + view["byteLength"]]


def world_vertices(scene, offset=None):
    arrays = []
    for node in scene.graph.nodes_geometry:
        matrix, key = scene.graph.get(node)
        vertices = trimesh.transform_points(scene.geometry[key].vertices, matrix)
        if offset is not None:
            vertices -= offset
        arrays.append(vertices)
    vertices = np.concatenate(arrays)
    return vertices[np.lexsort((vertices[:, 2], vertices[:, 1], vertices[:, 0]))]


def check_case(directory: Path, temporary: Path):
    bid = directory.name
    source_path = next(directory.glob("*.gltf"))
    record = json.loads((directory / "record.json").read_text())
    source_crc_match = all(
        len((directory / item["name"]).read_bytes()) == item["bytes"] and
        f"{zlib.crc32((directory / item['name']).read_bytes()) & 0xffffffff:08x}" == item["crc32"]
        for item in record["files"]
    )
    original = json.loads(source_path.read_text())
    old_doc, old_bin = glb(directory / "input.glb")
    source_scene = trimesh.load(source_path, process=False)
    packed_path = temporary / f"{bid}.glb"
    pack_meta = pack_building(source_path, packed_path)
    packed_doc, packed_bin = glb(packed_path)
    packed_scene = trimesh.load(packed_path, process=False)

    source_faces = primitive_faces(original)
    old_faces = primitive_faces(old_doc)
    packed_faces = primitive_faces(packed_doc)
    origin = np.asarray(pack_meta["origin_y_up"])
    source_world = world_vertices(source_scene, origin)
    packed_world = world_vertices(packed_scene)
    max_position_error = (float(np.max(np.abs(source_world - packed_world)))
                          if source_world.shape == packed_world.shape else None)
    source_img_hashes = [hashlib.sha256((source_path.parent / im["uri"]).read_bytes()).hexdigest()
                         for im in original.get("images", [])]
    packed_img_hashes = [hashlib.sha256(image_bytes(packed_doc, packed_bin, i)).hexdigest()
                         for i in range(len(packed_doc.get("images", [])))]
    old_img_hashes = [hashlib.sha256(image_bytes(old_doc, old_bin, i)).hexdigest()
                      for i in range(len(old_doc.get("images", [])))]
    source_geometries = list(source_scene.geometry.values())
    packed_geometries = list(packed_scene.geometry.values())
    uv_exact = (len(source_geometries) == len(packed_geometries) and
                all(np.array_equal(a.visual.uv, b.visual.uv) for a, b in
                    zip(source_geometries, packed_geometries)))
    all_materials_preserved = original.get("materials") == packed_doc.get("materials")
    node_prefix_preserved = original.get("nodes") == packed_doc.get("nodes", [])[:-1]
    source_buffer = (source_path.parent / original["buffers"][0]["uri"]).read_bytes()
    source_buffer_exact = packed_bin[:len(source_buffer)] == source_buffer
    pass_checks = (source_crc_match and source_faces == packed_faces and uv_exact and
                   source_img_hashes == packed_img_hashes and
                   all_materials_preserved and node_prefix_preserved and
                   source_buffer_exact and original.get("meshes") == packed_doc.get("meshes") and
                   max_position_error is not None and max_position_error < 1e-6)
    return {
        "building_id": bid,
        "source_record_file_crc32_match": source_crc_match,
        "source_primitives": len(source_faces), "source_faces": source_faces,
        "legacy_primitives": len(old_faces), "legacy_faces": old_faces,
        "legacy_missing_faces": sum(source_faces) - sum(old_faces),
        "source_material_refs": material_refs(original),
        "legacy_material_refs": material_refs(old_doc),
        "source_alpha_modes": [m.get("alphaMode", "OPAQUE") for m in original.get("materials", [])],
        "source_node_matrix": original["nodes"][0].get("matrix"),
        "source_scene_bounds_y_up": source_scene.bounds.tolist(),
        "legacy_bounds_z_up": trimesh.load(directory / "input.glb", process=False).bounds.tolist(),
        "legacy_first_image_byte_exact": bool(source_img_hashes and old_img_hashes and
                                              source_img_hashes[0] == old_img_hashes[0]),
        "packed_faces": packed_faces,
        "packed_origin_y_up": pack_meta["origin_y_up"],
        "packed_max_world_position_error_m": max_position_error,
        "packed_uv_exact": uv_exact,
        "packed_all_image_bytes_exact": source_img_hashes == packed_img_hashes,
        "packed_all_materials_exact": all_materials_preserved,
        "packed_all_meshes_exact": original.get("meshes") == packed_doc.get("meshes"),
        "packed_source_buffer_bytes_exact": source_buffer_exact,
        "packed_original_nodes_exact": node_prefix_preserved,
        "packed_pass": pass_checks,
        "source_sha256": pack_meta["source_sha256"],
        "legacy_sha256": hashlib.sha256((directory / "input.glb").read_bytes()).hexdigest(),
        "packed_sha256": pack_meta["output_sha256"],
    }


def synthetic_check(temporary: Path):
    """Exercise two primitive materials and a second translated mesh instance."""
    src = CASES / "B415681874001063A0"
    folder = temporary / "synthetic"
    folder.mkdir()
    for path in src.iterdir():
        if path.suffix in (".gltf", ".bin", ".jpg"):
            shutil.copy2(path, folder / path.name)
    path = next(folder.glob("*.gltf"))
    doc = json.loads(path.read_text())
    second = copy.deepcopy(doc["meshes"][0]["primitives"][0])
    second["material"] = 1
    doc["meshes"][0]["primitives"].append(second)
    doc["nodes"].append({"mesh": 0, "translation": [7.0, 0.0, -3.0]})
    doc["nodes"][0]["children"].append(len(doc["nodes"]) - 1)
    (folder / "extra.bin").write_bytes(b"abc")
    doc["buffers"].append({"uri": "extra.bin", "byteLength": 3})
    doc["bufferViews"].append({"buffer": 1, "byteOffset": 0, "byteLength": 3})
    path.write_text(json.dumps(doc))
    packed = folder / "synthetic.glb"
    meta = pack_building(path, packed)
    out, binary = glb(packed)
    source_scene = trimesh.load(path, process=False)
    packed_scene = trimesh.load(packed, process=False)
    original_vertices = world_vertices(source_scene, np.asarray(meta["origin_y_up"]))
    new_vertices = world_vertices(packed_scene)
    error = float(np.max(np.abs(original_vertices - new_vertices)))
    extra_view = out["bufferViews"][-2]  # The image view is appended last.
    extra_preserved = binary[extra_view["byteOffset"]:extra_view["byteOffset"] + 3] == b"abc"
    return {"source_primitives": len(primitive_faces(doc)),
            "packed_primitives": len(primitive_faces(out)),
            "source_scene_faces": sum(len(x.faces) for x in source_scene.geometry.values()) * 2,
            "packed_scene_faces": sum(len(x.faces) for x in packed_scene.geometry.values()) * 2,
            "position_error_m": error,
            "materials_exact": doc["materials"] == out["materials"],
            "mesh_primitives_exact": doc["meshes"] == out["meshes"],
            "second_buffer_preserved": extra_preserved,
            "passed": len(primitive_faces(out)) == 2 and error < 1e-6 and
            doc["materials"] == out["materials"] and
            doc["meshes"] == out["meshes"] and extra_preserved}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_suffix(".json"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="hk-conversion-audit-") as temp:
        temporary = Path(temp)
        cases = [check_case(d, temporary) for d in sorted(CASES.iterdir()) if
                 d.is_dir() and (d / "input.glb").is_file()]
        synthetic = synthetic_check(temporary)
    summary = {
        "case_count": len(cases),
        "legacy_missing_face_cases": [x["building_id"] for x in cases if x["legacy_missing_faces"]],
        "legacy_total_missing_faces": sum(x["legacy_missing_faces"] for x in cases),
        "legacy_reencoded_first_images": sum(not x["legacy_first_image_byte_exact"] for x in cases),
        "packed_pass_count": sum(x["packed_pass"] for x in cases),
        "synthetic_pass": synthetic["passed"],
    }
    result = {"summary": summary, "cases": cases, "synthetic": synthetic}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["packed_pass_count"] != len(cases) or not synthetic["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
