#!/usr/bin/env python3
"""Single-purpose MCP for the bounded historical sm21 1F reading pilot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any

from mcp.server.fastmcp import FastMCP, Image
from mcp.types import CallToolResult, TextContent
from PIL import Image as PILImage, ImageDraw


RULES = {
    "session_kickoff": "skills/intake_pipeline/0_reading/session_kickoff.md",
    "guide": "skills/intake_pipeline/0_reading/guide.md",
    "reading_guide": "skills/intake_pipeline/0_reading/reading_guide.md",
    "pen_library": "skills/intake_pipeline/0_reading/pen_library.md",
    "cv_toolbox": "skills/intake_pipeline/0_reading/cv_toolbox.md",
}
EXPECTED_PROJECTED_PATHS = frozenset(
    {
        *RULES.values(),
        "scripts/tool_scripts/cv_probe.py",
        "scripts/tool_scripts/render_vector_to_png.py",
        "src/__init__.py",
        "src/agent/__init__.py",
        "src/agent/reading/__init__.py",
        "src/agent/reading/schema.py",
        "src/agent/reading/legacy.py",
        "src/agent/reading/cv_toolbox/__init__.py",
        "src/agent/reading/cv_toolbox/tools.py",
        "src/agent/reading/cv_toolbox/recipes.py",
        "src/agent/reading/cv_toolbox/sidecar.py",
        "case_data/1f_view.png",
        "case_data/testdata_prompt.json",
    }
)
IMAGE_PATH = "case_data/1f_view.png"
DECLARATION_PATH = "case_data/testdata_prompt.json"
ARTIFACT_ID = re.compile(r"^A\d{4}$")
CV_LOCK = threading.Lock()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("path escaped the bounded reading workspace") from error
    return resolved


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _finite_optional(value: Any, name: str) -> float | None:
    return None if value is None else _finite_number(value, name)


def _integer_scale(value: Any, name: str, maximum: int) -> int:
    number = _finite_number(value, name)
    if not number.is_integer() or not 1 <= number <= maximum:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}")
    return int(number)


def _assert_finite_json(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite number at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"object key at {path} must be a string")
            _assert_finite_json(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_finite_json(child, f"{path}[{index}]")


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        manifest_path = _inside(self.root / "projection_manifest.json", self.root)
        if not manifest_path.is_file():
            raise RuntimeError("projection_manifest.json is missing")
        self.projection = json.loads(manifest_path.read_text(encoding="utf-8"))
        projected = {row["projected_path"] for row in self.projection.get("files", [])}
        if projected != EXPECTED_PROJECTED_PATHS:
            raise RuntimeError("projection manifest does not match the fixed allowlist")
        if any(
            forbidden in row.get("source", "").lower()
            for row in self.projection["files"]
            for forbidden in ("smalloffice_20", "test_baseline", "/gt/", "score_vs_gt")
        ):
            raise RuntimeError("projection manifest contains a forbidden answer source")
        for row in self.projection["files"]:
            path = _inside(self.root / row["projected_path"], self.root)
            if not path.is_file() or _digest(path) != row["sha256"]:
                raise RuntimeError(f"projected input hash mismatch: {row['projected_path']}")
        self.image = _inside(self.root / IMAGE_PATH, self.root)
        self.output = _inside(self.root / "0_reading", self.root)
        self.requests = _inside(self.root / "requests", self.root)
        self.output.mkdir(exist_ok=True)
        self.requests.mkdir(exist_ok=True)
        self.registry_path = self.root / "artifact_registry.json"
        self.log_path = self.root / "mcp_tools.jsonl"
        with PILImage.open(self.image) as picture:
            self.image_size = picture.size

    def log(self, action: str, details: dict[str, Any]) -> None:
        entry = {"time": time.time(), "action": action, "details": details}
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")

    def registry(self) -> dict[str, dict[str, Any]]:
        if not self.registry_path.is_file():
            return {}
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("artifact registry is corrupt")
        return data

    def register(self, paths: list[Path]) -> list[dict[str, Any]]:
        registry = self.registry()
        known = {row["path"]: artifact_id for artifact_id, row in registry.items()}
        created = []
        for path in sorted(paths):
            resolved = _inside(path, self.output)
            relative = str(resolved.relative_to(self.root))
            if relative in known:
                artifact_id = known[relative]
            else:
                artifact_id = f"A{len(registry) + 1:04d}"
                suffix = resolved.suffix.lower()
                kind = "image" if suffix in {".png", ".jpg", ".jpeg"} else "json"
                registry[artifact_id] = {
                    "path": relative,
                    "kind": kind,
                    "sha256": _digest(resolved),
                    "bytes": resolved.stat().st_size,
                }
                known[relative] = artifact_id
            created.append({"id": artifact_id, **registry[artifact_id]})
        _dump(self.registry_path, registry)
        return created

    def artifact_path(self, artifact_id: str, *, image_only: bool = False) -> Path:
        if not ARTIFACT_ID.fullmatch(artifact_id):
            raise ValueError("artifact id must look like A0001; paths are not accepted")
        row = self.registry().get(artifact_id)
        if row is None:
            raise ValueError("unknown artifact id")
        if image_only and row["kind"] != "image":
            raise ValueError("artifact is not an image")
        path = _inside(self.root / row["path"], self.output)
        if not path.is_file() or _digest(path) != row["sha256"]:
            raise RuntimeError("artifact changed after registration")
        return path

    def validate_box(self, box: list[float] | None) -> list[int] | None:
        if box is None:
            return None
        if not isinstance(box, list) or len(box) != 4:
            raise ValueError("box must be [left, top, right, bottom]")
        numeric = [_finite_number(value, "box coordinate") for value in box]
        if any(not value.is_integer() for value in numeric):
            raise ValueError("box coordinates must be integer original pixels")
        x0, y0, x1, y1 = [int(value) for value in numeric]
        width, height = self.image_size
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError("box must stay inside the 2133x1345 original image")
        return [x0, y0, x1, y1]

    def view_original(self, box: list[float] | None, scale: float) -> CallToolResult:
        box = self.validate_box(box)
        scale = _integer_scale(scale, "scale", 6)
        if box is None and scale == 1:
            data = self.image.read_bytes()
            shown_size = list(self.image_size)
            transform = {"source_x": "local_x", "source_y": "local_y"}
        else:
            with PILImage.open(self.image) as original:
                if box is None:
                    box = [0, 0, original.width, original.height]
                picture = original.convert("RGB").crop(tuple(box))
                if scale != 1:
                    picture = picture.resize(
                        (round(picture.width * scale), round(picture.height * scale)),
                        PILImage.Resampling.NEAREST,
                    )
                payload = io.BytesIO()
                picture.save(payload, "PNG")
                data = payload.getvalue()
                shown_size = list(picture.size)
            transform = {
                "source_x": f"{box[0]} + local_x / {scale}",
                "source_y": f"{box[1]} + local_y / {scale}",
            }
        metadata = {
            "source_image": "1f_view.png",
            "source_size": list(self.image_size),
            "source_sha256": _digest(self.image),
            "box_source_pixels": box,
            "display_scale": scale,
            "display_scale_xy": [scale, scale],
            "shown_size": shown_size,
            "local_to_source": transform,
        }
        self.log("view_original", {"box": box, "scale": scale})
        return CallToolResult(
            content=[
                Image(data=data, format="png").to_image_content(),
                TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False)),
            ],
            structuredContent=metadata,
        )

    def _cv_command(self, tool: str, options: list[str]) -> list[str]:
        return [
            sys.executable,
            str(_inside(self.root / "scripts/tool_scripts/cv_probe.py", self.root)),
            tool,
            "--image",
            str(self.image),
            "--out-dir",
            str(self.output),
            "--recipe",
            "clean_vector_v1",
            *options,
        ]

    def run_cv(self, tool: str, options: list[str], request: dict[str, Any]) -> CallToolResult:
        with CV_LOCK:
            before = {path.resolve() for path in self.output.rglob("*") if path.is_file()}
            command = self._cv_command(tool, options)
            env = {
                key: os.environ[key]
                for key in ("PATH", "LANG", "LC_ALL")
                if key in os.environ
            }
            env["PYTHONPATH"] = str(self.root)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            started = time.monotonic()
            completed = subprocess.run(
                command,
                cwd=self.root,
                env=env,
                text=True,
                capture_output=True,
                timeout=120,
                check=False,
            )
            receipt_dir = self.requests / "cv_invocations"
            receipt_dir.mkdir(exist_ok=True)
            receipt_path = receipt_dir / f"{len(list(receipt_dir.glob('*.json'))) + 1:03d}_{tool}.json"
            public_command = [
                Path(part).name if index in {0, 1} else part
                for index, part in enumerate(command)
            ]
            _dump(
                receipt_path,
                {
                    "tool": tool,
                    "request": request,
                    "command": public_command,
                    "returncode": completed.returncode,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                },
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"frozen cv_probe {tool} failed with status {completed.returncode}: "
                    f"{completed.stderr[-1000:]}"
                )
            after = {path.resolve() for path in self.output.rglob("*") if path.is_file()}
            new_files = sorted(after - before)
            new_sidecars = [path for path in new_files if path.suffix == ".json"]
            if len(new_sidecars) != 1:
                raise RuntimeError("frozen cv_probe did not create exactly one sidecar")
            artifacts = self.register(new_files)
            sidecar = json.loads(new_sidecars[0].read_text(encoding="utf-8"))
            public_sidecar = copy.deepcopy(sidecar)
            if public_sidecar.get("overlay_path"):
                public_sidecar["overlay_path"] = Path(public_sidecar["overlay_path"]).name
            for result in public_sidecar.get("results", []):
                if result.get("output_image"):
                    result["output_image"] = Path(result["output_image"]).name
            response = {
                "tool": tool,
                "sidecar": public_sidecar,
                "artifacts": artifacts,
                "note": "Candidates are pixel measurements, not semantic classifications.",
            }
            content = []
            for row in artifacts:
                if row["kind"] == "image":
                    path = self.artifact_path(row["id"], image_only=True)
                    content.append(Image(data=path.read_bytes(), format="png").to_image_content())
            content.append(TextContent(type="text", text=json.dumps(response, ensure_ascii=False)))
            self.log(tool, {"request": request, "artifact_ids": [row["id"] for row in artifacts]})
            return CallToolResult(content=content, structuredContent=response)

    def _request_json(self, stem: str, value: Any) -> Path:
        _assert_finite_json(value)
        folder = self.requests / "structured"
        folder.mkdir(exist_ok=True)
        path = folder / f"{len(list(folder.glob('*.json'))) + 1:03d}_{stem}.json"
        _dump(path, value)
        return _inside(path, self.requests)

    def cv_crop_zoom(self, bbox: list[float], scale: float) -> CallToolResult:
        bbox = self.validate_box(bbox)
        assert bbox is not None
        scale = _integer_scale(scale, "scale", 8)
        return self.run_cv(
            "crop_zoom",
            ["--bbox", ",".join(str(value) for value in bbox), "--scale", str(scale)],
            {"bbox": bbox, "scale": scale},
        )

    def cv_wall_line_profiler(
        self, axis: str, bbox: list[float] | None, scale: float
    ) -> CallToolResult:
        if axis not in {"row", "col"}:
            raise ValueError("axis must be row or col")
        bbox = self.validate_box(bbox)
        scale = _integer_scale(scale, "scale", 8)
        options = ["--axis", axis, "--scale", str(scale)]
        if bbox is not None:
            options.extend(["--bbox", ",".join(str(value) for value in bbox)])
        return self.run_cv(
            "wall_line_profiler", options, {"axis": axis, "bbox": bbox, "scale": scale}
        )

    def cv_storey_line_profiler(
        self, bbox: list[float] | None, scale: float
    ) -> CallToolResult:
        bbox = self.validate_box(bbox)
        scale = _integer_scale(scale, "scale", 8)
        options = ["--scale", str(scale)]
        if bbox is not None:
            options.extend(["--bbox", ",".join(str(value) for value in bbox)])
        return self.run_cv(
            "storey_line_profiler", options, {"bbox": bbox, "scale": scale}
        )

    def cv_px_m_calibrator(
        self,
        anchors: list[dict[str, Any]],
        residual_warn_px: float | None,
        residual_warn_m: float | None,
    ) -> CallToolResult:
        if not isinstance(anchors, list) or not anchors:
            raise ValueError("anchors must be a non-empty list")
        width, height = self.image_size
        for index, anchor in enumerate(anchors):
            if not isinstance(anchor, dict):
                raise ValueError("each anchor must be an object")
            if set(anchor) - {"axis", "px_a", "px_b", "value_m", "dimension_ref"}:
                raise ValueError(f"anchor {index} has unsupported fields")
            axis = anchor.get("axis")
            if axis not in {"x", "y", "xy"}:
                raise ValueError("anchor axis must be x, y or xy")
            limit = width if axis == "x" else height
            if axis in {"x", "y"}:
                a = _finite_number(anchor.get("px_a"), "px_a")
                b = _finite_number(anchor.get("px_b"), "px_b")
                if not (0 <= a < limit and 0 <= b < limit and a != b):
                    raise ValueError("axis anchor pixels must be distinct and inside the image")
            else:
                for key in ("px_a", "px_b"):
                    point = anchor.get(key)
                    if not isinstance(point, list) or len(point) != 2:
                        raise ValueError("xy anchors need [x,y] px_a and px_b")
                    x, y = [_finite_number(value, key) for value in point]
                    if not (0 <= x < width and 0 <= y < height):
                        raise ValueError("xy anchor point is outside the image")
            if _finite_number(anchor.get("value_m"), "value_m") <= 0:
                raise ValueError("anchor value_m must be positive")
            if not isinstance(anchor.get("dimension_ref"), str) or not anchor["dimension_ref"]:
                raise ValueError("anchor dimension_ref must be non-empty text")
        residual_warn_px = _finite_optional(residual_warn_px, "residual_warn_px")
        residual_warn_m = _finite_optional(residual_warn_m, "residual_warn_m")
        anchors_path = self._request_json("anchors", anchors)
        options = ["--anchors-json", str(anchors_path)]
        if residual_warn_px is not None:
            options.extend(["--residual-warn-px", str(residual_warn_px)])
        if residual_warn_m is not None:
            options.extend(["--residual-warn-m", str(residual_warn_m)])
        return self.run_cv(
            "px_m_calibrator",
            options,
            {
                "anchors": anchors,
                "residual_warn_px": residual_warn_px,
                "residual_warn_m": residual_warn_m,
            },
        )

    def cv_window_cc_detector(
        self,
        bbox: list[float] | None,
        scale: float,
        thresholds: dict[str, float | int | None],
    ) -> CallToolResult:
        bbox = self.validate_box(bbox)
        scale = _integer_scale(scale, "scale", 8)
        option_names = {
            "min_area": "--min-area",
            "min_width": "--min-width",
            "min_height": "--min-height",
            "max_width": "--max-width",
            "max_height": "--max-height",
            "min_aspect": "--min-aspect",
            "max_aspect": "--max-aspect",
            "merge_gap": "--merge-gap",
            "merge_overlap_ratio": "--merge-overlap-ratio",
            "merge_iou": "--merge-iou",
        }
        options = ["--scale", str(scale)]
        if bbox is not None:
            options.extend(["--bbox", ",".join(str(value) for value in bbox)])
        public_thresholds = {}
        for name, value in thresholds.items():
            if value is None:
                continue
            number = _finite_number(value, name)
            if number < 0:
                raise ValueError(f"{name} must be non-negative")
            if name == "min_area":
                number = int(number)
            public_thresholds[name] = number
            options.extend([option_names[name], str(number)])
        return self.run_cv(
            "window_cc_detector",
            options,
            {"bbox": bbox, "scale": scale, **public_thresholds},
        )

    def cv_overlay_logger(self, candidates: list[dict[str, Any]]) -> CallToolResult:
        if not isinstance(candidates, list):
            raise ValueError("candidates must be a list")
        allowed_status = {"accepted", "rejected", "undecided", "uncertain"}
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError("each candidate must be an object")
            if candidate.get("status") not in allowed_status:
                raise ValueError(f"candidate {index} has unsupported status")
            if not isinstance(candidate.get("reason"), str) or not candidate["reason"].strip():
                raise ValueError(f"candidate {index} needs a reason")
            if not isinstance(candidate.get("candidate_id"), str) or not candidate["candidate_id"]:
                raise ValueError(f"candidate {index} needs candidate_id")
        candidates_path = self._request_json("candidates", candidates)
        return self.run_cv(
            "overlay_logger",
            ["--candidates-json", str(candidates_path)],
            {"candidates": candidates},
        )

    def _frame_axis(self, frame: dict[str, Any], axis: str) -> tuple[float, float]:
        anchors = frame.get(f"{axis}_anchors")
        if not isinstance(anchors, list) or len(anchors) != 2:
            raise ValueError(f"coordinate_frame.{axis}_anchors needs two [pixel, metre] anchors")
        parsed = []
        limit = self.image_size[0 if axis == "x" else 1]
        for anchor in anchors:
            if not isinstance(anchor, list) or len(anchor) != 2:
                raise ValueError(f"coordinate_frame.{axis}_anchors needs [pixel, metre]")
            pixel = _finite_number(anchor[0], f"{axis} pixel")
            metre = _finite_number(anchor[1], f"{axis} metre")
            if not 0 <= pixel < limit:
                raise ValueError(f"coordinate_frame.{axis} pixel is outside the original image")
            parsed.append((pixel, metre))
        (p0, m0), (p1, m1) = parsed
        if p0 == p1 or m0 == m1:
            raise ValueError(f"coordinate_frame.{axis} anchors must be distinct")
        slope = (p1 - p0) / (m1 - m0)
        intercept = p0 - slope * m0
        return slope, intercept

    def _reading_overlay(self, reading: dict[str, Any], frame: dict[str, Any], output: Path) -> None:
        sx, bx = self._frame_axis(frame, "x")
        sy, by = self._frame_axis(frame, "y")

        def point(value: list[float]) -> tuple[float, float]:
            return sx * float(value[0]) + bx, sy * float(value[1]) + by

        with PILImage.open(self.image) as source:
            base = source.convert("RGBA")
        layer = PILImage.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        colors = {
            "wall": (230, 40, 40, 205),
            "window": (30, 100, 240, 220),
            "wall_fill": (230, 140, 20, 170),
            "outline": (170, 20, 180, 210),
        }
        for stroke in reading.get("strokes", []):
            geometry = stroke.get("geometry") or {}
            color = colors.get(stroke.get("pen"), (40, 190, 70, 190))
            kind = geometry.get("kind")
            if kind == "line" and geometry.get("p1") and geometry.get("p2"):
                draw.line([point(geometry["p1"]), point(geometry["p2"])], fill=color, width=4)
            elif kind == "polyline" and len(geometry.get("points") or []) >= 2:
                draw.line([point(item) for item in geometry["points"]], fill=color, width=4)
            elif kind == "rect":
                xr = geometry.get("x_range_m")
                yr = geometry.get("y_range_m")
                if isinstance(xr, list) and len(xr) == 2 and isinstance(yr, list) and len(yr) == 2:
                    p0 = point([xr[0], yr[0]])
                    p1 = point([xr[1], yr[1]])
                    draw.rectangle(
                        [min(p0[0], p1[0]), min(p0[1], p1[1]),
                         max(p0[0], p1[0]), max(p0[1], p1[1])],
                        outline=color,
                        width=4,
                    )
        for axis in ("x", "y"):
            for pixel, _metre in frame[f"{axis}_anchors"]:
                if axis == "x":
                    draw.line([(pixel, 0), (pixel, base.height)], fill=(255, 120, 0, 90), width=1)
                else:
                    draw.line([(0, pixel), (base.width, pixel)], fill=(255, 120, 0, 90), width=1)
        PILImage.alpha_composite(base, layer).convert("RGB").save(output)

    def submit(
        self,
        reading: dict[str, Any],
        coordinate_frame: dict[str, Any],
        candidate_ledger: list[dict[str, Any]],
        self_check: dict[str, Any],
    ) -> CallToolResult:
        if not isinstance(reading, dict) or not isinstance(coordinate_frame, dict):
            raise ValueError("reading and coordinate_frame must be objects")
        if not isinstance(candidate_ledger, list) or not isinstance(self_check, dict):
            raise ValueError("candidate_ledger must be a list and self_check an object")
        _assert_finite_json(reading)
        _assert_finite_json(coordinate_frame)
        _assert_finite_json(candidate_ledger)
        _assert_finite_json(self_check)
        if reading.get("image_kind") != "plan":
            raise ValueError("the one-image pilot requires image_kind=plan")
        for key in ("strokes", "dimensions", "ocr_texts", "uncaptured"):
            if not isinstance(reading.get(key), list):
                raise ValueError(f"reading.{key} must be a list")
        if not isinstance(reading.get("self_check"), dict):
            raise ValueError("reading.self_check must be an object")
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        from src.agent.reading.schema import ReadingView

        ReadingView.model_validate(reading)
        self._frame_axis(coordinate_frame, "x")
        self._frame_axis(coordinate_frame, "y")
        allowed_status = {"accepted", "rejected", "uncertain", "undecided"}
        for index, row in enumerate(candidate_ledger):
            if not isinstance(row, dict):
                raise ValueError("candidate ledger rows must be objects")
            if row.get("status") not in allowed_status:
                raise ValueError(f"candidate ledger row {index} has unsupported status")
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                raise ValueError(f"candidate ledger row {index} needs a reason")

        submissions = self.output / "submissions"
        submissions.mkdir(exist_ok=True)
        version = len([path for path in submissions.iterdir() if path.is_dir()]) + 1
        folder = submissions / f"{version:03d}"
        folder.mkdir()
        reading_path = folder / "1f_view.json"
        frame_path = folder / "coordinate_frame.json"
        ledger_path = folder / "candidate_ledger.json"
        self_check_path = folder / "pilot_self_check.json"
        _dump(reading_path, reading)
        _dump(frame_path, coordinate_frame)
        _dump(ledger_path, candidate_ledger)
        _dump(self_check_path, self_check)

        render_path = folder / "1f_view_render.png"
        renderer = _inside(self.root / "scripts/tool_scripts/render_vector_to_png.py", self.root)
        completed = subprocess.run(
            [sys.executable, str(renderer), str(reading_path), "--out", str(render_path)],
            cwd=self.root,
            env={
                **{key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ},
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"frozen reading renderer failed: {completed.stderr[-1000:]}")
        overlay_path = folder / "1f_view_source_overlay.png"
        self._reading_overlay(reading, coordinate_frame, overlay_path)

        for source, name in (
            (reading_path, "1f_view.json"),
            (frame_path, "coordinate_frame.json"),
            (ledger_path, "candidate_ledger.json"),
            (self_check_path, "pilot_self_check.json"),
            (render_path, "1f_view_render.png"),
            (overlay_path, "1f_view_source_overlay.png"),
        ):
            shutil.copy2(source, self.output / name)
        created = [path for path in folder.iterdir() if path.is_file()]
        artifacts = self.register(created)
        response = {
            "submission": f"{version:03d}",
            "reading_sha256": _digest(reading_path),
            "coordinate_frame_sha256": _digest(frame_path),
            "candidate_ledger_sha256": _digest(ledger_path),
            "self_check_sha256": _digest(self_check_path),
            "artifacts": artifacts,
            "counts_reported_only": {
                "strokes": len(reading["strokes"]),
                "dimensions": len(reading["dimensions"]),
                "candidate_ledger_rows": len(candidate_ledger),
            },
            "verdict": "not_evaluated; awaits external source-only review",
            "note": "No element-count, crop-count or candidate-count threshold was applied.",
        }
        self.log(
            "submit_pilot",
            {
                "submission": response["submission"],
                "reading_sha256": response["reading_sha256"],
                "counts_reported_only": response["counts_reported_only"],
            },
        )
        return CallToolResult(
            content=[
                Image(data=render_path.read_bytes(), format="png").to_image_content(),
                Image(data=overlay_path.read_bytes(), format="png").to_image_content(),
                TextContent(type="text", text=json.dumps(response, ensure_ascii=False)),
            ],
            structuredContent=response,
        )


def create_server(workspace_path: Path) -> FastMCP:
    workspace = Workspace(workspace_path)
    server = FastMCP("reading", log_level="WARNING")

    @server.tool()
    def manifest() -> dict[str, Any]:
        """Return the admitted 1F input declaration, hashes and experiment boundary."""
        declaration = json.loads(
            (workspace.root / DECLARATION_PATH).read_text(encoding="utf-8")
        )
        image_row = next(
            row for row in workspace.projection["files"] if row["projected_path"] == IMAGE_PATH
        )
        result = {
            "case": "sm21_anchor",
            "scope": "one image only: 1f_view.png",
            "image": {
                "name": "1f_view.png",
                "size": list(workspace.image_size),
                "sha256": image_row["sha256"],
            },
            "building_declaration": declaration,
            "rules": sorted(RULES),
            "worked_example": "deliberately unavailable because it duplicates the target wall layout",
            "evaluation": "GT, old runs, scores and prior answers are unavailable",
            "output": "submit one historical-schema plan reading, evidence ledger and self-check",
        }
        workspace.log("manifest", {})
        return result

    @server.tool()
    def get_rule(name: str) -> dict[str, Any]:
        """Read one exact 723 rule by enum name; arbitrary paths are not accepted."""
        relative = RULES.get(name)
        if relative is None:
            raise ValueError("unknown rule name; choose one returned by manifest")
        path = _inside(workspace.root / relative, workspace.root)
        result = {"name": name, "sha256": _digest(path), "text": path.read_text(encoding="utf-8")}
        workspace.log("get_rule", {"name": name})
        return result

    @server.tool()
    def view_original(box: list[float] | None = None, scale: float = 1.0) -> CallToolResult:
        """View the fixed original 1F image or a bounded crop in original pixels."""
        return workspace.view_original(box, scale)

    @server.tool()
    def cv_crop_zoom(bbox: list[float], scale: float = 2.0) -> CallToolResult:
        """Run frozen 723 crop_zoom on the fixed original; bbox is half-open source pixels."""
        return workspace.cv_crop_zoom(bbox, scale)

    @server.tool()
    def cv_wall_line_profiler(
        axis: str, bbox: list[float] | None = None, scale: float = 1.0
    ) -> CallToolResult:
        """Run frozen 723 wall_line_profiler; peaks are candidates, not walls."""
        return workspace.cv_wall_line_profiler(axis, bbox, scale)

    @server.tool()
    def cv_storey_line_profiler(
        bbox: list[float] | None = None, scale: float = 1.0
    ) -> CallToolResult:
        """Run frozen 723 storey_line_profiler on a bounded source region."""
        return workspace.cv_storey_line_profiler(bbox, scale)

    @server.tool()
    def cv_px_m_calibrator(
        anchors: list[dict[str, Any]],
        residual_warn_px: float | None = None,
        residual_warn_m: float | None = None,
    ) -> CallToolResult:
        """Run frozen 723 px_m_calibrator with structured, in-image anchors."""
        return workspace.cv_px_m_calibrator(anchors, residual_warn_px, residual_warn_m)

    @server.tool()
    def cv_window_cc_detector(
        bbox: list[float] | None = None,
        scale: float = 1.0,
        min_area: int | None = None,
        min_width: float | None = None,
        min_height: float | None = None,
        max_width: float | None = None,
        max_height: float | None = None,
        min_aspect: float | None = None,
        max_aspect: float | None = None,
        merge_gap: float | None = None,
        merge_overlap_ratio: float | None = None,
        merge_iou: float | None = None,
    ) -> CallToolResult:
        """Run frozen 723 window CC detector; results still require visual classification."""
        return workspace.cv_window_cc_detector(
            bbox,
            scale,
            {
                "min_area": min_area,
                "min_width": min_width,
                "min_height": min_height,
                "max_width": max_width,
                "max_height": max_height,
                "min_aspect": min_aspect,
                "max_aspect": max_aspect,
                "merge_gap": merge_gap,
                "merge_overlap_ratio": merge_overlap_ratio,
                "merge_iou": merge_iou,
            },
        )

    @server.tool()
    def cv_overlay_logger(candidates: list[dict[str, Any]]) -> CallToolResult:
        """Run frozen 723 overlay_logger for accepted/rejected/uncertain decisions."""
        return workspace.cv_overlay_logger(candidates)

    @server.tool()
    def list_artifacts() -> dict[str, Any]:
        """List only files created by this run, using opaque artifact IDs."""
        registry = workspace.registry()
        rows = [{"id": artifact_id, **row} for artifact_id, row in sorted(registry.items())]
        workspace.log("list_artifacts", {"count": len(rows)})
        return {"artifacts": rows}

    @server.tool()
    def view_artifact(artifact_id: str) -> CallToolResult:
        """View a registered run-produced image by opaque ID; paths are rejected."""
        path = workspace.artifact_path(artifact_id, image_only=True)
        row = workspace.registry()[artifact_id]
        public = {"id": artifact_id, "kind": row["kind"], "sha256": row["sha256"]}
        workspace.log("view_artifact", {"artifact_id": artifact_id})
        return CallToolResult(
            content=[
                Image(data=path.read_bytes(), format="png").to_image_content(),
                TextContent(type="text", text=json.dumps(public)),
            ],
            structuredContent=public,
        )

    @server.tool()
    def submit_pilot(
        reading: dict[str, Any],
        coordinate_frame: dict[str, Any],
        candidate_ledger: list[dict[str, Any]],
        self_check: dict[str, Any],
    ) -> CallToolResult:
        """Version and render one old-schema 1F reading; no count threshold is applied."""
        return workspace.submit(reading, coordinate_frame, candidate_ledger, self_check)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["serve"])
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    create_server(args.workspace).run()


if __name__ == "__main__":
    main()
