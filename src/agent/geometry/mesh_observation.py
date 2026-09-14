"""Deterministic observations of a textured binary glTF building mesh.

The source glTF convention is Y-up.  Public coordinates from this module are
BIM-local Z-up coordinates, using ``(x, y, z) -> (x, -z, y)`` after each scene
node transform.  An operation may additionally rotate that frame counter-
clockwise around +Z with ``yaw_degrees``.

This module reports and renders mesh evidence.  A mesh surface, its horizontal
extent, or a face-centroid selection is not evidence of rooms, enclosure, or a
true building footprint.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

import numpy as np
from PIL import Image
import trimesh


_MAX_IMAGE_SIDE = 1600
_MAX_IMAGE_PIXELS = _MAX_IMAGE_SIDE**2
_MAX_VIEW_SPAN_M = 1_000_000.0
_BACKGROUND = np.array([238, 242, 246], dtype=np.uint8)
_Y_UP_TO_Z_UP = np.array(
    [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, -1.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ],
    dtype=np.float64,
)


@dataclass(frozen=True)
class _MeshPart:
    vertices: np.ndarray
    faces: np.ndarray
    uv: np.ndarray
    texture: Image.Image
    base_color_factor: np.ndarray
    node_name: str
    geometry_name: str
    face_offset: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_self_contained_glb(path: Path) -> None:
    """Reject non-GLB and external buffer/image references before loading."""

    with path.open("rb") as stream:
        header = stream.read(20)
        if len(header) < 20 or header[:4] != b"glTF":
            raise ValueError(f"mesh input must be a binary glTF (GLB) file: {path}")
        version, total_length, json_length, json_kind = struct.unpack_from(
            "<IIII", header, 4
        )
        if version != 2 or total_length != path.stat().st_size:
            raise ValueError(f"invalid GLB v2 header: {path}")
        if json_kind != 0x4E4F534A or json_length <= 0:
            raise ValueError(f"GLB first chunk must contain JSON: {path}")
        json_bytes = stream.read(json_length)
    try:
        document = json.loads(json_bytes.rstrip(b" \t\r\n\x00"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid GLB JSON chunk: {path}") from exc
    for collection in ("buffers", "images"):
        for index, item in enumerate(document.get(collection, [])):
            uri = item.get("uri")
            if uri is not None and not str(uri).startswith("data:"):
                raise ValueError(
                    f"GLB {collection}[{index}] has external URI {uri!r}; "
                    "mesh observations require self-contained assets"
                )
    if "KHR_texture_transform" in document.get("extensionsUsed", []):
        raise ValueError(
            "GLB uses KHR_texture_transform, which this rasterizer does not support"
        )
    for index, sampler in enumerate(document.get("samplers", [])):
        wrap_s = sampler.get("wrapS", 10497)
        wrap_t = sampler.get("wrapT", 10497)
        if wrap_s != 10497 or wrap_t != 10497:
            raise ValueError(
                f"GLB sampler[{index}] uses unsupported texture wrap modes "
                f"wrapS={wrap_s}, wrapT={wrap_t}; only glTF REPEAT is supported"
            )


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def _finite_vector(name: str, value: Any, length: int) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (length,) or not np.isfinite(result).all():
        raise ValueError(f"{name} must contain {length} finite numbers")
    return result


def _validated_yaw(yaw_degrees: float) -> float:
    try:
        yaw = float(yaw_degrees)
    except (TypeError, ValueError) as exc:
        raise ValueError("yaw_degrees must be finite") from exc
    if not math.isfinite(yaw):
        raise ValueError("yaw_degrees must be finite")
    return yaw


def _yaw_matrix(yaw_degrees: float) -> np.ndarray:
    angle = math.radians(_validated_yaw(yaw_degrees))
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array(
        [
            [cosine, -sine, 0.0],
            [sine, cosine, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def _validated_bounds(bounds: Any | None) -> np.ndarray | None:
    if bounds is None:
        return None
    result = np.asarray(bounds, dtype=np.float64)
    if result.shape != (2, 3) or not np.isfinite(result).all():
        raise ValueError("bounds must be [[xmin, ymin, zmin], [xmax, ymax, zmax]]")
    if np.any(result[1] <= result[0]):
        raise ValueError("each bounds maximum must be greater than its minimum")
    return result


def _material_texture(
    mesh: trimesh.Trimesh, label: str
) -> tuple[Image.Image, np.ndarray]:
    if mesh.visual.kind != "texture":
        raise ValueError(
            f"{label} uses unsupported visual kind {mesh.visual.kind!r}; "
            "a UV-mapped base-color texture is required"
        )
    uv = getattr(mesh.visual, "uv", None)
    if uv is None or np.asarray(uv).shape != (len(mesh.vertices), 2):
        raise ValueError(f"{label} has no per-vertex TEXCOORD_0 UV mapping")
    material = getattr(mesh.visual, "material", None)
    if material is None or material.__class__.__name__ == "MultiMaterial":
        raise ValueError(f"{label} uses an unsupported multi-material scheme")
    image = getattr(material, "baseColorTexture", None)
    if image is None:
        image = getattr(material, "image", None)
    if image is None or not isinstance(image, Image.Image):
        raise ValueError(f"{label} has UVs but no supported base-color texture image")
    alpha_mode = getattr(material, "alphaMode", None)
    if alpha_mode not in (None, "OPAQUE"):
        raise ValueError(
            f"{label} uses unsupported material alpha mode {alpha_mode!r}"
        )
    rgba = image.convert("RGBA")
    alpha_min, alpha_max = rgba.getchannel("A").getextrema()
    if alpha_min != 255 or alpha_max != 255:
        raise ValueError(
            f"{label} has transparency; alpha blending is not supported by this rasterizer"
        )
    factor = getattr(material, "baseColorFactor", None)
    if factor is None:
        factor_rgb = np.ones(3, dtype=np.float64)
    else:
        factor_array = np.asarray(factor, dtype=np.float64)
        if factor_array.shape not in ((3,), (4,)) or not np.isfinite(factor_array).all():
            raise ValueError(f"{label} has an invalid baseColorFactor")
        if factor_array.max(initial=0.0) > 1.0:
            factor_array = factor_array / 255.0
        if np.any(factor_array < 0.0) or np.any(factor_array > 1.0):
            raise ValueError(f"{label} has an out-of-range baseColorFactor")
        if len(factor_array) == 4 and factor_array[3] < 1.0:
            raise ValueError(
                f"{label} has transparent baseColorFactor; alpha blending is unsupported"
            )
        factor_rgb = factor_array[:3]
    return rgba.convert("RGB"), factor_rgb


def _apply_linear_rgb_factor(
    sampled_srgb: np.ndarray, factor_linear: np.ndarray
) -> np.ndarray:
    """Apply glTF's linear baseColorFactor to sRGB texture samples."""

    srgb = sampled_srgb.astype(np.float64) / 255.0
    linear = np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + 0.055) / 1.055) ** 2.4,
    )
    factored = np.clip(linear * factor_linear[None, :], 0.0, 1.0)
    encoded = np.where(
        factored <= 0.0031308,
        factored * 12.92,
        1.055 * factored ** (1.0 / 2.4) - 0.055,
    )
    return np.rint(encoded * 255.0).clip(0, 255).astype(np.uint8)


class MeshObservation:
    """Load a GLB once and produce metric, queryable software-rendered views."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise FileNotFoundError(f"mesh asset does not exist: {self.path}")
        _validate_self_contained_glb(self.path)
        self.mesh_sha256 = _sha256(self.path)
        try:
            scene = trimesh.load(self.path, force="scene", process=False)
        except Exception as exc:  # trimesh raises several loader-specific types
            raise ValueError(f"failed to load GLB mesh {self.path}: {exc}") from exc
        if not isinstance(scene, trimesh.Scene) or not scene.graph.nodes_geometry:
            raise ValueError(f"GLB contains no scene mesh geometry: {self.path}")

        parts: list[_MeshPart] = []
        face_offset = 0
        for node_name in scene.graph.nodes_geometry:
            scene_transform, geometry_name = scene.graph.get(node_name)
            mesh = scene.geometry[geometry_name]
            label = f"scene node {node_name!r} geometry {geometry_name!r}"
            if not isinstance(mesh, trimesh.Trimesh):
                raise ValueError(f"{label} is not triangular mesh geometry")
            vertices = np.asarray(mesh.vertices, dtype=np.float64)
            faces = np.asarray(mesh.faces, dtype=np.int64)
            if vertices.ndim != 2 or vertices.shape[1:] != (3,) or not len(vertices):
                raise ValueError(f"{label} has invalid or empty POSITION data")
            if faces.ndim != 2 or faces.shape[1:] != (3,) or not len(faces):
                raise ValueError(f"{label} has invalid or empty triangle indices")
            texture, base_color_factor = _material_texture(mesh, label)
            uv = np.asarray(mesh.visual.uv, dtype=np.float64)
            if not np.isfinite(vertices).all() or not np.isfinite(uv).all():
                raise ValueError(f"{label} has non-finite position or UV data")
            if faces.min() < 0 or faces.max() >= len(vertices):
                raise ValueError(f"{label} has out-of-range triangle indices")
            transformed = trimesh.transform_points(vertices, scene_transform)
            transformed = np.column_stack(
                (transformed[:, 0], -transformed[:, 2], transformed[:, 1])
            )
            parts.append(
                _MeshPart(
                    vertices=transformed,
                    faces=faces,
                    uv=uv,
                    texture=texture,
                    base_color_factor=base_color_factor,
                    node_name=str(node_name),
                    geometry_name=str(geometry_name),
                    face_offset=face_offset,
                )
            )
            face_offset += len(faces)
        self._parts = tuple(parts)
        self.vertex_count = sum(len(part.vertices) for part in self._parts)
        self.face_count = face_offset

    def _operation_parts(
        self, yaw_degrees: float, bounds: Any | None
    ) -> tuple[list[tuple[_MeshPart, np.ndarray, np.ndarray]], np.ndarray | None]:
        yaw = _yaw_matrix(yaw_degrees)
        clip = _validated_bounds(bounds)
        selected: list[tuple[_MeshPart, np.ndarray, np.ndarray]] = []
        for part in self._parts:
            vertices = part.vertices @ yaw.T
            face_ids = np.arange(len(part.faces), dtype=np.int64)
            if clip is not None:
                centres = vertices[part.faces].mean(axis=1)
                inside = np.logical_and(centres >= clip[0], centres <= clip[1]).all(axis=1)
                face_ids = face_ids[inside]
            selected.append((part, vertices, face_ids))
        return selected, clip

    def describe(self, yaw_degrees: float = 0, bounds: Any | None = None) -> dict[str, Any]:
        """Return geometric mesh evidence in the requested operation frame."""

        selected, clip = self._operation_parts(yaw_degrees, bounds)
        selected_faces = sum(len(face_ids) for _, _, face_ids in selected)
        selected_vertex_sets = [
            np.unique(part.faces[face_ids].reshape(-1))
            for part, _, face_ids in selected
            if len(face_ids)
        ]
        selected_vertices = sum(len(ids) for ids in selected_vertex_sets)
        points = [
            vertices[ids]
            for (part, vertices, face_ids), ids in zip(
                (item for item in selected if len(item[2])), selected_vertex_sets, strict=True
            )
        ]
        geometric_bounds = (
            np.vstack((np.vstack(points).min(axis=0), np.vstack(points).max(axis=0)))
            if points
            else None
        )
        yaw = _validated_yaw(yaw_degrees)
        return {
            "mesh_path": str(self.path),
            "mesh_sha256": self.mesh_sha256,
            "coordinate_frame": "BIM-local right-handed Z-up metres",
            "source_coordinate_transform": {
                "order": "scene node transform, then glTF Y-up to BIM Z-up, then operation yaw",
                "y_up_to_z_up": "[X, -Z, Y]",
                "y_up_to_z_up_matrix": _Y_UP_TO_Z_UP.tolist(),
                "yaw_degrees_counterclockwise_about_positive_z": yaw,
                "yaw_matrix": _yaw_matrix(yaw).tolist(),
            },
            "vertex_count": self.vertex_count,
            "face_count": self.face_count,
            "scene_instance_count": len(self._parts),
            "selected_vertex_count": selected_vertices,
            "selected_face_count": selected_faces,
            "bounds": None if geometric_bounds is None else geometric_bounds.tolist(),
            "selection_bounds": None if clip is None else clip.tolist(),
            "selection_method": (
                "all faces"
                if clip is None
                else "triangle centroid inside inclusive bounds in the yaw-rotated BIM frame"
            ),
            "selection_caveat": (
                "A bounded centroid selection can hide intersecting or occluding surfaces; "
                "it is an observation filter, not evidence of enclosure truth."
            ),
            "evidence_caveat": (
                "Bounds and counts describe the supplied surface mesh only; they do not "
                "establish floors, rooms, enclosure, or a true footprint."
            ),
        }

    def render(
        self,
        out_prefix: Path,
        *,
        eye: list[float],
        target: list[float],
        width_m: float,
        height_m: float,
        width_px: int = 1200,
        height_px: int = 900,
        yaw_degrees: float = 0,
        bounds: Any | None = None,
    ) -> tuple[Image.Image, dict[str, Any]]:
        """Render a textured orthographic view and save queryable raster evidence."""

        camera_eye = _finite_vector("eye", eye, 3)
        camera_target = _finite_vector("target", target, 3)
        try:
            view_width, view_height = float(width_m), float(height_m)
        except (TypeError, ValueError) as exc:
            raise ValueError("width_m and height_m must be finite positive numbers") from exc
        if (
            not math.isfinite(view_width)
            or not math.isfinite(view_height)
            or view_width <= 0
            or view_height <= 0
            or view_width > _MAX_VIEW_SPAN_M
            or view_height > _MAX_VIEW_SPAN_M
        ):
            raise ValueError(
                f"width_m and height_m must be positive and no greater than {_MAX_VIEW_SPAN_M:g}"
            )
        if isinstance(width_px, bool) or isinstance(height_px, bool):
            raise ValueError("width_px and height_px must be integers")
        try:
            image_width, image_height = int(width_px), int(height_px)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("width_px and height_px must be integers") from exc
        if image_width != width_px or image_height != height_px:
            raise ValueError("width_px and height_px must be integers")
        if (
            image_width < 1
            or image_height < 1
            or image_width > _MAX_IMAGE_SIDE
            or image_height > _MAX_IMAGE_SIDE
            or image_width * image_height > _MAX_IMAGE_PIXELS
        ):
            raise ValueError(
                f"image resolution must be positive, at most {_MAX_IMAGE_SIDE} per side, "
                f"and at most {_MAX_IMAGE_PIXELS} pixels"
            )

        forward = camera_target - camera_eye
        camera_distance = float(np.linalg.norm(forward))
        if camera_distance <= 1e-9:
            raise ValueError("eye and target must be distinct")
        forward /= camera_distance
        reference_up = np.array([0.0, 0.0, 1.0])
        up_choice = "+Z"
        if abs(float(forward @ reference_up)) > 0.999:
            reference_up = np.array([0.0, 1.0, 0.0])
            up_choice = "+Y fallback because the view is parallel to +Z"
        right = np.cross(forward, reference_up)
        right /= np.linalg.norm(right)
        camera_up = np.cross(right, forward)
        camera_up /= np.linalg.norm(camera_up)

        selected, clip = self._operation_parts(yaw_degrees, bounds)
        if not any(len(face_ids) for _, _, face_ids in selected):
            raise ValueError("bounds selected no mesh faces")

        colors = np.empty((image_height, image_width, 3), dtype=np.uint8)
        colors[:] = _BACKGROUND
        depth = np.full((image_height, image_width), np.inf, dtype=np.float64)
        face_buffer = np.full((image_height, image_width), -1, dtype=np.int32)
        world_buffer = np.full((image_height, image_width, 3), np.nan, dtype=np.float32)
        texture_arrays: dict[int, np.ndarray] = {}
        visible_candidate_faces = 0

        for part, vertices, local_face_ids in selected:
            texture_key = id(part.texture)
            texture = texture_arrays.setdefault(texture_key, np.asarray(part.texture))
            triangles = vertices[part.faces[local_face_ids]]
            triangle_uv = part.uv[part.faces[local_face_ids]]
            relative = triangles - camera_target
            screen_x = relative @ right
            screen_y = relative @ camera_up
            triangle_depth = (triangles - camera_eye) @ forward

            for index, local_face_id in enumerate(local_face_ids):
                sx, sy = screen_x[index], screen_y[index]
                denominator = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (
                    sx[2] - sx[1]
                ) * (sy[0] - sy[2])
                if abs(float(denominator)) <= 1e-14:
                    continue
                col_float = (sx / view_width + 0.5) * image_width - 0.5
                row_float = (0.5 - sy / view_height) * image_height - 0.5
                col_min = max(0, int(math.ceil(float(col_float.min()) - 1e-9)))
                col_max = min(image_width - 1, int(math.floor(float(col_float.max()) + 1e-9)))
                row_min = max(0, int(math.ceil(float(row_float.min()) - 1e-9)))
                row_max = min(image_height - 1, int(math.floor(float(row_float.max()) + 1e-9)))
                if col_min > col_max or row_min > row_max:
                    continue
                visible_candidate_faces += 1
                columns = np.arange(col_min, col_max + 1)
                rows = np.arange(row_min, row_max + 1)
                px = ((columns + 0.5) / image_width - 0.5) * view_width
                py = (0.5 - (rows + 0.5) / image_height) * view_height
                grid_x, grid_y = np.meshgrid(px, py)
                weight0 = (
                    (sy[1] - sy[2]) * (grid_x - sx[2])
                    + (sx[2] - sx[1]) * (grid_y - sy[2])
                ) / denominator
                weight1 = (
                    (sy[2] - sy[0]) * (grid_x - sx[2])
                    + (sx[0] - sx[2]) * (grid_y - sy[2])
                ) / denominator
                weight2 = 1.0 - weight0 - weight1
                inside = (
                    (weight0 >= -1e-10)
                    & (weight1 >= -1e-10)
                    & (weight2 >= -1e-10)
                )
                candidate_depth = (
                    weight0 * triangle_depth[index, 0]
                    + weight1 * triangle_depth[index, 1]
                    + weight2 * triangle_depth[index, 2]
                )
                current = depth[row_min : row_max + 1, col_min : col_max + 1]
                update = inside & (candidate_depth > 1e-9) & (candidate_depth < current)
                if not update.any():
                    continue
                rr, cc = np.nonzero(update)
                global_rows, global_cols = rr + row_min, cc + col_min
                w0, w1, w2 = weight0[update], weight1[update], weight2[update]
                current[update] = candidate_depth[update]
                points = (
                    w0[:, None] * triangles[index, 0]
                    + w1[:, None] * triangles[index, 1]
                    + w2[:, None] * triangles[index, 2]
                )
                uv = (
                    w0[:, None] * triangle_uv[index, 0]
                    + w1[:, None] * triangle_uv[index, 1]
                    + w2[:, None] * triangle_uv[index, 2]
                )
                # glTF's default REPEAT sampler has a period of exactly one in
                # UV space.  PIL rows run downward, hence the V inversion.
                texture_x = np.floor(
                    np.mod(uv[:, 0], 1.0) * texture.shape[1]
                ).astype(np.int64)
                texture_y = np.floor(
                    np.mod(1.0 - uv[:, 1], 1.0) * texture.shape[0]
                ).astype(np.int64)
                colors[global_rows, global_cols] = _apply_linear_rgb_factor(
                    texture[texture_y, texture_x, :3], part.base_color_factor
                )
                face_buffer[global_rows, global_cols] = part.face_offset + int(local_face_id)
                world_buffer[global_rows, global_cols] = points.astype(np.float32)

        image = Image.fromarray(colors, mode="RGB")
        prefix = Path(out_prefix).expanduser().resolve()
        prefix.parent.mkdir(parents=True, exist_ok=True)
        png_path = Path(f"{prefix}.png")
        json_path = Path(f"{prefix}.json")
        npz_path = Path(f"{prefix}.npz")
        image.save(png_path)
        hit_flat = np.flatnonzero(face_buffer.reshape(-1) >= 0).astype(np.int32)
        np.savez_compressed(
            npz_path,
            image_shape=np.asarray((image_height, image_width), dtype=np.int32),
            pixel_indices=hit_flat,
            world_points=world_buffer.reshape(-1, 3)[hit_flat],
            face_ids=face_buffer.reshape(-1)[hit_flat],
            mesh_sha256=np.asarray(self.mesh_sha256),
        )

        pixel_dx = view_width / image_width
        pixel_dy = view_height / image_height
        top_left = (
            camera_target
            + (-view_width / 2.0 + pixel_dx / 2.0) * right
            + (view_height / 2.0 - pixel_dy / 2.0) * camera_up
        )
        description = self.describe(yaw_degrees=yaw_degrees, bounds=bounds)
        metadata = {
            **description,
            "camera": {
                "projection": "orthographic",
                "eye": camera_eye.tolist(),
                "target": camera_target.tolist(),
                "eye_target_distance_m": camera_distance,
                "forward_from_eye": forward.tolist(),
                "screen_right": right.tolist(),
                "screen_up": camera_up.tolist(),
                "up_reference": up_choice,
                "top_view_fallback": (
                    "When the view direction is parallel to Z, +Y is used as the stable "
                    "up reference; otherwise BIM +Z is used."
                ),
            },
            "view_span_m": {"width": view_width, "height": view_height},
            "resolution_px": {"width": image_width, "height": image_height},
            "pixel_center_mapping": {
                "formula": "plane_xyz(row,col)=top_left+col*column_step+row*row_step; surface_xyz additionally advances along camera forward to the visible triangle",
                "top_left_pixel_center_plane_xyz": top_left.tolist(),
                "column_step_world_xyz": (right * pixel_dx).tolist(),
                "row_step_world_xyz": (-camera_up * pixel_dy).tolist(),
                "pixel_width_m": pixel_dx,
                "pixel_height_m": pixel_dy,
                "pixel_coordinates": "zero-based [column, row] with image origin at top-left",
            },
            "rasterizer": {
                "texture_interpolation": "barycentric UV, glTF REPEAT wrap, nearest texture pixel",
                "texture_v_mapping": "PIL image rows are the vertical inverse of glTF UV",
                "depth_test": "nearest positive distance along camera forward",
                "material_display": (
                    "unlit, double-sided geometric observation; sRGB base-color texture is "
                    "decoded to linear RGB, multiplied by baseColorFactor, and encoded back "
                    "to sRGB; this is not PBR-lighting or backface-culling faithful"
                ),
                "candidate_faces_overlapping_view": visible_candidate_faces,
                "visible_pixel_count": int(len(hit_flat)),
            },
            "selection_bounds": None if clip is None else clip.tolist(),
            "artifacts": {
                "png": str(png_path),
                "metadata_json": str(json_path),
                "pixel_buffer_npz": str(npz_path),
                "pixel_buffer_layout": "sorted flat pixel indices with compact world XYZ and global face IDs",
            },
        }
        json_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=_json_value) + "\n",
            encoding="utf-8",
        )
        return image, metadata

    def pixel_query(
        self, out_prefix: Path, pixels: list[list[int]]
    ) -> dict[str, Any]:
        """Query visible world points saved by :meth:`render`."""

        if not isinstance(pixels, list):
            raise ValueError("pixels must be a list of [column, row] pairs")
        prefix = Path(out_prefix).expanduser().resolve()
        npz_path = Path(f"{prefix}.npz")
        if not npz_path.is_file():
            raise FileNotFoundError(f"render pixel buffer does not exist: {npz_path}")
        with np.load(npz_path, allow_pickle=False) as data:
            required = {
                "image_shape",
                "pixel_indices",
                "world_points",
                "face_ids",
                "mesh_sha256",
            }
            if not required.issubset(data.files):
                raise ValueError(f"invalid render pixel buffer: {npz_path}")
            stored_sha = str(data["mesh_sha256"].item())
            if stored_sha != self.mesh_sha256:
                raise ValueError(
                    "render pixel buffer belongs to a different mesh asset: "
                    f"expected {self.mesh_sha256}, found {stored_sha}"
                )
            image_shape = np.asarray(data["image_shape"], dtype=np.int64)
            hit_indices = np.asarray(data["pixel_indices"], dtype=np.int64)
            world_points = np.asarray(data["world_points"], dtype=np.float64)
            face_ids = np.asarray(data["face_ids"], dtype=np.int64)
        if image_shape.shape != (2,) or np.any(image_shape <= 0):
            raise ValueError(f"invalid image shape in render pixel buffer: {npz_path}")
        if (
            hit_indices.ndim != 1
            or world_points.shape != (len(hit_indices), 3)
            or face_ids.shape != (len(hit_indices),)
            or (len(hit_indices) and np.any(hit_indices[1:] <= hit_indices[:-1]))
        ):
            raise ValueError(f"invalid compact arrays in render pixel buffer: {npz_path}")

        height, width = (int(image_shape[0]), int(image_shape[1]))
        results: list[dict[str, Any]] = []
        hit_points: list[np.ndarray | None] = []
        for pixel in pixels:
            if (
                not isinstance(pixel, (list, tuple))
                or len(pixel) != 2
                or isinstance(pixel[0], bool)
                or isinstance(pixel[1], bool)
                or not isinstance(pixel[0], (int, np.integer))
                or not isinstance(pixel[1], (int, np.integer))
            ):
                raise ValueError("each pixel must be an integer [column, row] pair")
            column, row = int(pixel[0]), int(pixel[1])
            if column < 0 or column >= width or row < 0 or row >= height:
                raise ValueError(
                    f"pixel {[column, row]} is outside image bounds "
                    f"[0,{width - 1}] x [0,{height - 1}]"
                )
            flat_index = row * width + column
            location = int(np.searchsorted(hit_indices, flat_index))
            if location < len(hit_indices) and hit_indices[location] == flat_index:
                point = world_points[location]
                results.append(
                    {
                        "pixel": [column, row],
                        "hit": True,
                        "world_xyz": point.tolist(),
                        "face_id": int(face_ids[location]),
                    }
                )
                hit_points.append(point)
            else:
                results.append({"pixel": [column, row], "hit": False, "background": True})
                hit_points.append(None)

        pairwise: dict[str, Any] | None = None
        if len(results) >= 2:
            pairwise = {"pixels": [results[0]["pixel"], results[1]["pixel"]]}
            if hit_points[0] is not None and hit_points[1] is not None:
                pairwise.update(
                    {
                        "available": True,
                        "distance_m": float(np.linalg.norm(hit_points[1] - hit_points[0])),
                    }
                )
            else:
                pairwise.update(
                    {
                        "available": False,
                        "distance_m": None,
                        "reason": "both of the first two pixels must hit the mesh",
                    }
                )
        return {
            "mesh_sha256": self.mesh_sha256,
            "pixel_buffer_npz": str(npz_path),
            "resolution_px": {"width": width, "height": height},
            "queries": results,
            "first_two_distance": pairwise,
        }
