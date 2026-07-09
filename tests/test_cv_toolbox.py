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
    get_recipe,
    overlay_logger,
    prescan_elevation,
    prescan_plan,
    px_m_calibrator,
    storey_line_profiler,
    wall_line_profiler,
    window_cc_detector,
    write_sidecar,
)
from src.agent.reading.cv_toolbox.tools import _mask_clean_vector


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


def _save_l_mask(path: Path) -> Path:
    img = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((18, 10, 22, 90), fill=GRAY)
    draw.rectangle((20, 18, 70, 22), fill=GRAY)
    img.save(path)
    return path


def _save_dimension_ticks(path: Path) -> Path:
    img = Image.new("RGB", (120, 80), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((10, 58, 100, 62), fill=GRAY)
    draw.rectangle((8, 52, 12, 68), fill=GRAY)
    draw.rectangle((98, 52, 102, 68), fill=GRAY)
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


def test_sidecar_rejects_path_escape_and_uses_exclusive_create(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")
    payload, _crop, crop_chain = crop_zoom(image, [50, 20, 150, 100], source_name=image.name)

    with pytest.raises(ValueError):
        allocate_sidecar_path(tmp_path / "out", image, "crop_zoom", "../../../escaped")
    with pytest.raises(ValueError):
        allocate_sidecar_path(tmp_path / "out", image, "crop_zoom", "/tmp/escaped")

    sidecar = allocate_sidecar_path(tmp_path / "out", image, "crop_zoom", "001_crop_zoom")
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_sidecar(sidecar, image, payload, crop_chain=crop_chain)
    assert sidecar.read_text(encoding="utf-8") == "existing"


def test_fractional_crop_chain_uses_actual_integer_crop_bounds():
    img = Image.new("RGB", (20, 20), "white")
    img.putpixel((1, 2), GRAY)

    _payload, crop, crop_chain = crop_zoom(img, [1.9, 2.9, 11.1, 12.1], scale=1)

    assert crop.getpixel((0, 0)) == GRAY
    step = crop_chain[0]
    assert step["bbox_px"] == [1.0, 2.0, 12.0, 13.0]
    source_x = step["bbox_px"][0] + 0 / step["scale"]
    source_y = step["bbox_px"][1] + 0 / step["scale"]
    assert (source_x, source_y) == (1.0, 2.0)


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


def test_overlay_logger_rejects_candidate_without_drawable_geometry(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")
    with pytest.raises(ValueError, match="drawable geometry"):
        overlay_logger(
            image,
            [{"candidate_id": "c1", "status": "undecided", "reason": "missing geometry"}],
            output_path=tmp_path / "overlay.png",
        )


def test_transparent_gray_rgba_is_not_clean_vector_mask():
    img = Image.new("RGBA", (4, 4), (128, 128, 128, 0))

    mask = _mask_clean_vector(img, get_recipe())
    payload, _ = wall_line_profiler(img, axis="col")

    assert int(mask.sum()) == 0
    assert payload["results"] == []


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


def test_prescan_plan_schema_and_combined_overlay(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")

    candidates_path, overlay_path = prescan_plan(image, out_dir=tmp_path / "reading")

    assert candidates_path == tmp_path / "reading" / "cv_evidence" / "plan" / "prescan" / "candidates.json"
    assert overlay_path.exists()
    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    assert data["cv_schema"] == "1"
    assert data["tool"] == "prescan-plan"
    assert data["params"]["advisory_only"] is True
    assert data["capability_profile"]["requested"] == "orthogonal_polygon"
    assert {"rectangular", "orthogonal_polygon"} <= set(data["capability_profile"]["supported"])
    assert data["results"]
    allowed = {"line_band_candidate", "cc_box_candidate", "tick_candidate"}
    assert {result["kind"] for result in data["results"]} <= allowed
    for result in data["results"]:
        assert not result["kind"].startswith(("wall_", "window_"))
        if result["kind"] == "cc_box_candidate":
            assert len(result["bbox_px"]) == 4
        else:
            assert len(result["p1_px"]) == 2
            assert len(result["p2_px"]) == 2
            assert "strength" in result
            assert "fwhm_px" in result


def test_prescan_bounded_segments_do_not_span_full_l_mask(tmp_path: Path):
    image = _save_l_mask(tmp_path / "l_shape.png")
    candidates_path, _overlay_path = prescan_plan(image, out_dir=tmp_path / "reading", include_cc=False)
    data = json.loads(candidates_path.read_text(encoding="utf-8"))

    row_segments = [
        result
        for result in data["results"]
        if result["kind"] == "line_band_candidate"
        and result["axis"] == "row"
        and abs(result["p1_px"][1] - 20) <= 2
    ]
    assert row_segments
    assert any(15 <= seg["p1_px"][0] <= 25 and 65 <= seg["p2_px"][0] <= 75 for seg in row_segments)
    assert all(not (seg["p1_px"][0] <= 1 and seg["p2_px"][0] >= 99) for seg in row_segments)


def test_prescan_idempotent_candidates_json(tmp_path: Path):
    image = _save_l_mask(tmp_path / "stable.png")

    candidates_path, _overlay_path = prescan_plan(image, out_dir=tmp_path / "reading")
    first = candidates_path.read_bytes()
    candidates_path, _overlay_path = prescan_plan(image, out_dir=tmp_path / "reading")
    second = candidates_path.read_bytes()

    assert first == second


def test_prescan_unsupported_capability_profile_raises(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")

    with pytest.raises(NotImplementedError, match="capability_profile"):
        prescan_plan(image, out_dir=tmp_path / "reading", capability_profile="sloped_polygon")


def test_prescan_triage_filters_line_bands_but_never_ticks(tmp_path: Path):
    image = _save_dimension_ticks(tmp_path / "dimension.png")

    full_path, _ = prescan_plan(image, out_dir=tmp_path / "reading", include_cc=False)
    triage_path, _ = prescan_plan(
        image,
        out_dir=tmp_path / "reading",
        include_cc=False,
        min_strength=0.08,
        min_line_len_px=50,
        label="prescan_triage",
    )

    assert triage_path != full_path
    full = json.loads(full_path.read_text(encoding="utf-8"))
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    full_lines = [r for r in full["results"] if r["kind"] == "line_band_candidate"]
    triage_lines = [r for r in triage["results"] if r["kind"] == "line_band_candidate"]
    assert len(triage_lines) < len(full_lines)
    for cand in triage_lines:
        x0, y0 = cand["p1_px"]
        x1, y1 = cand["p2_px"]
        assert cand["strength"] >= 0.08
        assert ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 >= 50
    # Ticks are calibration anchors: identical geometry with and without the filter.
    tick_geoms = lambda data: [  # noqa: E731
        (r["p1_px"], r["p2_px"]) for r in data["results"] if r["kind"] == "tick_candidate"
    ]
    assert tick_geoms(triage) == tick_geoms(full)
    assert triage["params"]["min_strength"] == 0.08
    assert triage["params"]["min_line_len_px"] == 50
    assert triage["params"]["label"] == "prescan_triage"
    diag = triage["diagnostics"]
    assert diag["line_band_candidate_count_prefilter"] == len(full_lines)
    assert diag["line_band_candidate_count"] == len(triage_lines)


def test_prescan_axis_summary_groups_candidates_per_peak(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")

    candidates_path, _ = prescan_plan(image, out_dir=tmp_path / "reading", include_cc=False)

    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    summary = data["diagnostics"]["axis_summary"]
    assert len(summary) == data["diagnostics"]["projection_peak_count"]
    by_id = {r["candidate_id"]: r for r in data["results"]}
    line_ids = {cid for cid, r in by_id.items() if r["kind"] == "line_band_candidate"}
    seen: set[str] = set()
    for entry in summary:
        assert entry["axis"] in {"row", "col"}
        assert entry["run_count"] == len(entry["candidate_ids"])
        for cid in entry["candidate_ids"]:
            assert cid in line_ids
            assert by_id[cid]["axis"] == entry["axis"]
        seen.update(entry["candidate_ids"])
    # Every emitted line-band candidate is reachable from exactly one peak group.
    assert seen == line_ids


def test_prescan_rejects_unsafe_label(tmp_path: Path):
    image = _save_plan(tmp_path / "plan.png")

    with pytest.raises(ValueError, match="label"):
        prescan_plan(image, out_dir=tmp_path / "reading", label="../escape")


def test_prescan_tick_detection_on_dimension_line(tmp_path: Path):
    image = _save_dimension_ticks(tmp_path / "dimension.png")
    candidates_path, _overlay_path = prescan_plan(image, out_dir=tmp_path / "reading", include_cc=False)
    data = json.loads(candidates_path.read_text(encoding="utf-8"))

    ticks = [result for result in data["results"] if result["kind"] == "tick_candidate"]
    assert ticks
    assert any(result["axis"] == "col" and 6 <= abs(result["p2_px"][1] - result["p1_px"][1]) <= 25 for result in ticks)


def test_prescan_elevation_cli_writes_candidates_and_overlay(tmp_path: Path):
    image = _save_dimension_ticks(tmp_path / "elevation.png")
    cmd = [
        sys.executable,
        "scripts/tool_scripts/cv_probe.py",
        "prescan-elevation",
        "--image",
        str(image),
        "--out-dir",
        str(tmp_path / "reading"),
    ]
    subprocess.run(cmd, check=True)

    candidates = tmp_path / "reading" / "cv_evidence" / "elevation" / "prescan" / "candidates.json"
    overlay = tmp_path / "reading" / "cv_evidence" / "elevation" / "prescan" / "combined_overlay.png"
    assert candidates.exists()
    assert overlay.exists()
    data = json.loads(candidates.read_text(encoding="utf-8"))
    assert data["tool"] == "prescan-elevation"
    assert data["capability_profile"]["requested"] == "rectangular"
