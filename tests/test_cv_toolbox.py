from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from src.agent.reading.cv_toolbox import (
    allocate_sidecar_path,
    crop_zoom,
    overlay_logger,
    px_m_calibrator,
    storey_line_profiler,
    wall_line_profiler,
    window_cc_detector,
    write_sidecar,
)


GRAY = (128, 128, 128)


def _save_plan(path: Path) -> Path:
    img = Image.new("RGB", (220, 160), "white")
    draw = ImageDraw.Draw(img)
    for x in (20, 80, 150):
        draw.rectangle((x - 2, 10, x + 2, 150), fill=GRAY)
    for y in (30, 110):
        draw.rectangle((10, y - 2, 210, y + 2), fill=GRAY)
    draw.line((5, 5, 215, 5), fill="black")
    img.save(path)
    return path


def _save_windows(path: Path) -> Path:
    img = Image.new("RGB", (120, 90), "white")
    draw = ImageDraw.Draw(img)
    for bbox in ((10, 10, 28, 28), (45, 10, 63, 28), (80, 10, 98, 28), (10, 50, 28, 68)):
        draw.rectangle(bbox, fill=GRAY)
    # Two close pieces should merge into one bbox.
    draw.rectangle((45, 50, 54, 68), fill=GRAY)
    draw.rectangle((56, 50, 65, 68), fill=GRAY)
    img.save(path)
    return path


def test_wall_and_storey_line_profiler_known_peaks(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")

    payload, _ = wall_line_profiler(image, axis="col", source_name=image.name)
    xs = [round(r["position_px"]) for r in payload["results"]]
    assert xs == pytest.approx([20, 80, 150], abs=1)
    assert all(r["strength"] > 0 for r in payload["results"])
    assert all(abs(r["width_px"] - 5) <= 2 for r in payload["results"])

    payload, _ = storey_line_profiler(image, source_name=image.name)
    ys = [round(r["position_px"]) for r in payload["results"]]
    assert ys == pytest.approx([30, 110], abs=1)
    assert all(r["candidate_kind"] == "storey_line" for r in payload["results"])


def test_px_m_calibrator_exact_and_residuals():
    exact = px_m_calibrator(
        [
            {"axis": "x", "px_a": 0, "px_b": 300, "value_m": 3.0, "dimension_ref": "a"},
            {"axis": "y", "px_a": 10, "px_b": 510, "value_m": 5.0, "dimension_ref": "b"},
        ]
    )
    result = exact["results"][0]
    assert result["px_per_m"] == pytest.approx(100.0, abs=1e-9)
    assert result["m_per_px"] == pytest.approx(0.01, abs=1e-12)
    assert result["rmse_px"] == pytest.approx(0.0, abs=1e-9)
    assert all(abs(r["residual_px"]) < 1e-9 for r in result["residuals"])

    residual = px_m_calibrator(
        [
            {"axis": "x", "px_a": 0, "px_b": 300, "value_m": 3.0},
            {"axis": "y", "px_a": 0, "px_b": 520, "value_m": 5.0},
        ],
        residual_warn_px=1,
    )
    assert residual["results"][0]["rmse_px"] > 0
    assert residual["results"][0]["warnings"]

    single = px_m_calibrator([{"axis": "x", "px_a": 0, "px_b": 250, "value_m": 2.5}])
    assert single["results"][0]["residuals"] is None
    assert single["results"][0]["rmse_px"] is None


def test_window_cc_detector_count_bbox_and_merge(tmp_path: Path):
    image = _save_windows(tmp_path / "elevation.png")
    payload, _ = window_cc_detector(image, min_area_px=20, source_name=image.name)
    boxes = [r["bbox_px"] for r in payload["results"]]
    assert len(boxes) == 5
    assert boxes[0] == pytest.approx([10, 10, 29, 29], abs=1)
    assert boxes[-1] == pytest.approx([45, 50, 66, 69], abs=1)
    assert payload["results"][-1]["merge_reason"] == "gap_x_overlap_y"


def test_crop_round_trip_sidecar_schema_and_append_only(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")
    payload, _crop, crop_chain = crop_zoom(
        image,
        [50, 20, 150, 100],
        scale=2,
        output_path=tmp_path / "crop.png",
        source_name=image.name,
    )
    step = crop_chain[0]
    local_x, local_y = 20, 30
    source_x = step["bbox_px"][0] + local_x / step["scale"]
    source_y = step["bbox_px"][1] + local_y / step["scale"]
    restored_x = (source_x - step["bbox_px"][0]) * step["scale"]
    restored_y = (source_y - step["bbox_px"][1]) * step["scale"]
    assert (restored_x, restored_y) == pytest.approx((local_x, local_y))

    sidecar = allocate_sidecar_path(tmp_path / "out", image, "crop_zoom", "001_crop_zoom")
    written = write_sidecar(sidecar, image, payload, crop_chain=crop_chain)
    data = json.loads(written.read_text(encoding="utf-8"))
    assert data["cv_schema"] == "1"
    assert data["source_image"]["name"] == "plan.png"
    assert len(data["source_image"]["sha256"]) == 12
    assert data["crop_chain"][0]["op"] == "crop_zoom"
    assert data["results"][0]["anchor_px"]["kind"] == "bbox"
    with pytest.raises(FileExistsError):
        write_sidecar(sidecar, image, payload, crop_chain=crop_chain)


def test_overlay_logger_smoke(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")
    out = tmp_path / "overlay.png"
    payload = overlay_logger(
        image,
        [
            {
                "candidate_id": "c1",
                "geometry": {"kind": "bbox", "bbox_px": [10, 10, 40, 40]},
                "status": "accepted",
                "reason": "known fixture",
            },
            {
                "candidate_id": "c2",
                "geometry": {"kind": "line", "axis": "col", "x_px": 80},
                "status": "rejected",
                "reason": "test rejection",
            },
        ],
        output_path=out,
    )
    assert out.exists()
    assert payload["diagnostics"]["decisions"][1]["status"] == "rejected"


def test_real_sm21_case_data_plan_smoke():
    image = Path("case_tests/e2e_tests/sm21_anchor/case_data/1f_view.png")
    assert image.exists()
    payload, _ = wall_line_profiler(image, axis="col", source_name=image.name)
    assert len(payload["results"]) >= 5


def test_cv_probe_cli_end_to_end(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")
    cmd = [
        sys.executable,
        "scripts/tool_scripts/cv_probe.py",
        "wall_line_profiler",
        "--image",
        str(image),
        "--out-dir",
        str(tmp_path / "reading"),
        "--axis",
        "col",
    ]
    subprocess.run(cmd, check=True)
    sidecars = sorted((tmp_path / "reading" / "cv_evidence" / "plan").glob("*.json"))
    overlays = sorted((tmp_path / "reading" / "cv_evidence" / "plan").glob("*_overlay.png"))
    assert len(sidecars) == 1
    assert len(overlays) == 1
    data = json.loads(sidecars[0].read_text(encoding="utf-8"))
    assert data["tool"] == "wall_line_profiler"
    assert data["results"]
    assert data["diagnostics"]["overlay_decisions"][0]["reason"] == "cv_probe automatic overlay"
