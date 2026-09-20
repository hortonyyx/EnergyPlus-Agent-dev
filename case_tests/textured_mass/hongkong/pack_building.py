"""Pack one source glTF building into a self-contained, local Y-up GLB.

The source node hierarchy, primitives, UVs, materials and image bytes are kept.
Only a new translation root is added to the default scene to remove the large
map coordinates. Usage: python pack_building.py source.gltf output.glb
"""

import argparse
import base64
import copy
import hashlib
import json
import mimetypes
import os
import struct
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pad(data: bytes, byte: bytes) -> bytes:
    return data + byte * ((-len(data)) % 4)


def _resource(source: Path, uri: str) -> bytes:
    if uri.startswith("data:"):
        head, separator, body = uri.partition(",")
        if not separator:
            raise ValueError("Malformed data URI")
        return base64.b64decode(body) if head.endswith(";base64") else unquote(body).encode()
    parts = urlsplit(uri)
    if parts.scheme or parts.netloc or parts.query or parts.fragment:
        raise ValueError(f"Only local glTF resources are supported: {uri!r}")
    path = (source.parent / unquote(parts.path)).resolve()
    if not path.is_relative_to(source.parent.resolve()) or not path.is_file():
        raise ValueError(f"Resource escapes source directory or is missing: {uri!r}")
    return path.read_bytes()


def _mime(uri: str, data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    kind = mimetypes.guess_type(uri)[0]
    if kind in ("image/jpeg", "image/png", "image/webp"):
        return kind
    raise ValueError(f"Unsupported image format: {uri!r}")


def _origin(source: Path) -> list[float]:
    import trimesh

    scene = trimesh.load(source, process=False)
    if not isinstance(scene, trimesh.Scene) or not len(scene.geometry):
        raise ValueError("Source must contain a nonempty glTF scene")
    bounds = scene.bounds
    if bounds is None:
        raise ValueError("Source scene has no bounds")
    return [float((bounds[0, 0] + bounds[1, 0]) / 2),
            float(bounds[0, 1]),
            float((bounds[0, 2] + bounds[1, 2]) / 2)]


def pack_building(source: str | Path, target: str | Path) -> dict:
    """Write a GLB and return hashes, local origin, wrapper matrix and counts."""
    source, target = Path(source), Path(target)
    if source.suffix.lower() != ".gltf" or target.suffix.lower() != ".glb":
        raise ValueError("Expected a .gltf source and .glb target")
    if source.resolve() == target.resolve():
        raise ValueError("Source and target must differ")
    source_bytes = source.read_bytes()
    document = json.loads(source_bytes)
    if document.get("asset", {}).get("version") != "2.0":
        raise ValueError("Only glTF 2.0 is supported")
    if not document.get("buffers") or not document.get("scenes"):
        raise ValueError("Source needs buffers and scenes")
    scene_index = document.get("scene", 0)
    if not 0 <= scene_index < len(document["scenes"]):
        raise ValueError("Invalid default scene index")

    origin = _origin(source)
    matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
              -origin[0], -origin[1], -origin[2], 1]
    packed = copy.deepcopy(document)
    old_roots = list(packed["scenes"][scene_index].get("nodes", []))
    packed.setdefault("nodes", [])
    root_index = len(packed["nodes"])
    packed["nodes"].append({"name": "local_origin", "matrix": matrix,
                            "children": old_roots})
    packed["scenes"][scene_index]["nodes"] = [root_index]

    binary = bytearray()
    offsets = []
    resource_hashes = {}
    for buffer in packed["buffers"]:
        if "uri" not in buffer:
            raise ValueError("A .gltf buffer must have a URI")
        data = _resource(source, buffer["uri"])
        if len(data) < buffer["byteLength"]:
            raise ValueError(f"Buffer shorter than declared: {buffer['uri']}")
        offsets.append(len(binary))
        binary.extend(_pad(data, b"\x00"))
        resource_hashes[buffer["uri"]] = _sha256(data)
    for view in packed.get("bufferViews", []):
        old_buffer = view.get("buffer", 0)
        if not 0 <= old_buffer < len(offsets):
            raise ValueError("Invalid bufferView buffer index")
        view["byteOffset"] = offsets[old_buffer] + view.get("byteOffset", 0)
        view["buffer"] = 0

    for image in packed.get("images", []):
        uri = image.pop("uri", None)
        if uri is None:
            continue  # Already points to a bufferView.
        data = _resource(source, uri)
        image["mimeType"] = _mime(uri, data)
        image["bufferView"] = len(packed.setdefault("bufferViews", []))
        packed["bufferViews"].append({"buffer": 0,
                                      "byteOffset": len(binary),
                                      "byteLength": len(data)})
        binary.extend(_pad(data, b"\x00"))
        resource_hashes[uri] = _sha256(data)
    packed["buffers"] = [{"byteLength": len(binary)}]

    json_chunk = _pad(json.dumps(packed, ensure_ascii=False, separators=(",", ":"))
                      .encode("utf-8"), b" ")
    bin_chunk = bytes(binary)
    glb = (struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(json_chunk) +
                       8 + len(bin_chunk)) +
           struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk +
           struct.pack("<I4s", len(bin_chunk), b"BIN\x00") + bin_chunk)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.",
                                     suffix=".tmp", delete=False) as output:
        temp_path = Path(output.name)
        output.write(glb)
    try:
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "source": str(source), "target": str(target),
        "source_sha256": _sha256(source_bytes), "output_sha256": _sha256(glb),
        "resource_sha256": resource_hashes,
        "origin_y_up": origin, "translation_matrix_column_major": matrix,
        "source_counts": {
            "nodes": len(document.get("nodes", [])),
            "meshes": len(document.get("meshes", [])),
            "primitives": sum(len(m.get("primitives", [])) for m in document.get("meshes", [])),
            "materials": len(document.get("materials", [])),
            "images": len(document.get("images", [])),
            "buffers": len(document["buffers"]),
        },
        "output_counts": {
            "nodes": len(packed["nodes"]),
            "meshes": len(packed.get("meshes", [])),
            "primitives": sum(len(m.get("primitives", [])) for m in packed.get("meshes", [])),
            "materials": len(packed.get("materials", [])),
            "images": len(packed.get("images", [])),
            "buffers": 1,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(json.dumps(pack_building(args.source, args.target), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
