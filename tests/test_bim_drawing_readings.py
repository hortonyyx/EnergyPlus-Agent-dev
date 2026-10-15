"""Adopted elevation geometry, immutable provenance and source comparison."""

import copy
import hashlib
import json

import pytest
from PIL import Image, ImageDraw

from scripts.tool_scripts.bim_agent_drawing_readings import (
    compare_reading, load_reading, prepare_elevation_reading,
)
from scripts.tool_scripts.run_bim_agent import Toolkit
from src.agent.geometry.source_model import _digest


def _fixture(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    picture = Image.new("RGB", (220, 180), "white")
    draw = ImageDraw.Draw(picture)
    draw.rectangle((60, 96, 100, 120), outline="black")
    draw.rectangle((120, 36, 160, 60), outline="black")
    original = images / "North.png"
    picture.save(original)
    (tmp_path / "inputs.json").write_text(json.dumps({"images": {
        "North.png": {"sha256": hashlib.sha256(original.read_bytes()).hexdigest()}}}), encoding="utf-8")
    reading = {"x_calibration": {"pixel_start": 20, "pixel_end": 200,
        "distance_start_m": 0, "distance_end_m": 9, "facade_length_m": 9},
        "z_calibration": {"pixel_start": 20, "pixel_end": 140, "world_start_m": 6, "world_end_m": 0},
        "elevations": [
            {"id": "floor-F1", "floor_id": "F1", "kind": "floor", "value_m": 0,
             "evidence_type": "annotation", "bbox": [20, 139, 200, 141]},
            {"id": "floor-F2", "floor_id": "F2", "kind": "floor", "value_m": 3.04,
             "evidence_type": "annotation", "bbox": [20, 79, 200, 81]},
            {"id": "roof", "kind": "roof", "value_m": 6,
             "evidence_type": "annotation", "bbox": [20, 19, 200, 21]}],
        "openings": [
            {"id": "W1", "floor_id": "F1", "kind": "window", "evidence_type": "pixels",
             "opening_bbox": [57, 99, 103, 117]},
            {"id": "W2", "floor_id": "F2", "kind": "window", "evidence_type": "pixels",
             "opening_bbox": [117, 39, 163, 57]}],
        "counts": [{"floor_id": floor, "window_count": 1, "door_count": 0} for floor in ("F1", "F2")],
        "unresolved": []}
    return Toolkit(tmp_path), reading, original


def _prepare(toolkit, reading):
    return prepare_elevation_reading(toolkit, "North.png", "North", json.dumps(reading))


def _candidate(toolkit, *, second_height=(4.0, 5.2), horizontal_shift=0.0, extra=False, missing=False):
    source = {"floors": [{"id": "F1", "z_floor": 0}, {"id": "F2", "z_floor": 3}],
        "spaces": [{"id": f"room-{floor}", "floor_id": floor} for floor in ("F1", "F2")],
        "boundaries": [{"id": f"north-{floor}", "vertices": [[9, 10, z], [0, 10, z],
            [0, 10, z + 3], [9, 10, z + 3]]} for floor, z in (("F1", 0), ("F2", 3))], "openings": []}
    for index, (floor, span, heights) in enumerate((
        ("F1", (5.0, 7.0), (1.0, 2.2)), ("F2", (2.0, 4.0), second_height)), 1):
        left, right = [value + horizontal_shift for value in span]
        sill, head = heights
        source["openings"].append({"id": f"bim-W{index}", "kind": "window", "exterior": True,
            "space_ids": [f"room-{floor}"], "host_boundary_id": f"north-{floor}",
            "vertices": [[left, 10, sill], [right, 10, sill], [right, 10, head], [left, 10, head]]})
    if missing:
        source["openings"].pop()
    if extra:
        row = copy.deepcopy(source["openings"][0])
        row["id"] = "bim-extra"
        row["vertices"] = [[p[0] - 4, p[1], p[2]] for p in row["vertices"]]
        source["openings"].append(row)
    source["source_model_sha256"] = _digest(source)
    folder = toolkit.run / "candidate_01"
    folder.mkdir(exist_ok=True)
    path = folder / "source_model.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    return path


def test_source_floor_level_conflicts_with_adopted_elevation_level(tmp_path):
    toolkit, reading, _ = _fixture(tmp_path)
    _, metadata = _prepare(toolkit, reading)
    path = _candidate(toolkit)
    source = json.loads(path.read_bytes())
    source["floors"][1]["z_floor"] = 3.2
    source.pop("source_model_sha256")
    source["source_model_sha256"] = _digest(source)
    path.write_text(json.dumps(source), encoding="utf-8")
    report = compare_reading(toolkit, metadata["reading_id"], "candidate_01")
    assert not report["current_consistent"]
    assert any(row["type"] == "floor_level_difference" and row["floor_id"] == "F2" for row in report["issues"])


def test_equivalent_anchor_order_and_opening_order_keep_adopted_values_and_original_submission(tmp_path):
    toolkit, reading, _ = _fixture(tmp_path)
    # Two same-floor openings exercise the former left-to-right rejection.
    reading["openings"][1]["floor_id"] = "F1"
    reading.pop("counts")
    _, first = _prepare(toolkit, reading)
    original_artifact = load_reading(toolkit, first["reading_id"])["artifact"]
    reading["openings"].reverse()
    for name, prefix in (("x_calibration", "distance"), ("z_calibration", "world")):
        cal = reading[name]
        for a, b in (("pixel_start", "pixel_end"), (prefix + "_start_m", prefix + "_end_m")):
            cal[a], cal[b] = cal[b], cal[a]
    _, second = _prepare(toolkit, reading)
    saved = load_reading(toolkit, second["reading_id"])
    assert saved["artifact"] == original_artifact
    assert saved["submitted"] == reading
    assert len(saved["normalization"]) == 4
    assert saved["artifact"]["counts"] == [
        {"floor_id": "F1", "window_count": 2, "door_count": 0},
        {"floor_id": "F2", "window_count": 0, "door_count": 0}]


@pytest.mark.parametrize("conflict", ["direction", "counts"])
def test_normalization_does_not_silently_repair_semantic_conflicts(tmp_path, conflict):
    toolkit, reading, _ = _fixture(tmp_path)
    if conflict == "direction":
        reading["x_calibration"].update(distance_start_m=9, distance_end_m=0)
    else:
        reading["counts"][0]["window_count"] = 0
    with pytest.raises(ValueError):
        _prepare(toolkit, reading)
    assert not list((toolkit.run / "drawing_readings").glob("reading_*.json"))


def test_overlay_uses_adopted_numeric_width_and_absolute_height_not_submitted_box(tmp_path):
    toolkit, reading, original = _fixture(tmp_path)
    opening = reading["openings"][0]
    opening.update(evidence_type="annotation", x_px=[60, 100], width_m=1.64, sill_m=1.62,
                   head_m=2.26, bbox=[50, 90, 110, 125])
    before = original.read_bytes()
    images, metadata = _prepare(toolkit, reading)
    saved = load_reading(toolkit, metadata["reading_id"])
    adopted = saved["adopted_openings"][0]
    assert adopted["width_m"] == 1.6 and adopted["sill_m"] == 1.6 and adopted["head_m"] == 2.3
    assert adopted["overlay_bbox_px"] == pytest.approx([64, 94, 96, 108])
    assert adopted["overlay_bbox_px"] != opening["opening_bbox"]
    assert saved["levels"][1]["value_m"] == 3.0 and saved["levels"][1]["overlay_y_px"] == 80
    assert saved["submitted"] == reading
    assert any(row["type"] == "width_span_conflict" for row in saved["issues"])
    assert any(row["type"] == "retained_ink_conflict" for row in saved["issues"])
    assert saved["artifact"]["regularization"]["changes"]
    assert original.read_bytes() == before
    with Image.open(original) as unchanged:
        assert images[0].tobytes() == unchanged.convert("RGB").tobytes()
    assert images[1].getpixel((80, 108)) == (0, 115, 235)
    assert images[0].getpixel((80, 108)) == (255, 255, 255)
    assert metadata["independently_verified"] is False


def test_pixel_alignment_two_floor_absolute_z_and_immutable_versions(tmp_path):
    toolkit, reading, original = _fixture(tmp_path)
    before = original.read_bytes()
    _, first = _prepare(toolkit, reading)
    first_bytes = (toolkit.run / first["reading_file"]).read_bytes()
    _, second = _prepare(toolkit, reading)
    assert first["reading_id"] == "reading_0001" and second["reading_id"] == "reading_0002"
    assert first["artifact_sha256"] == second["artifact_sha256"]
    assert (toolkit.run / first["reading_file"]).read_bytes() == first_bytes
    saved = load_reading(toolkit, second["reading_id"])
    assert saved["adopted_openings"][0]["overlay_bbox_px"] == pytest.approx([60, 96, 100, 120])
    assert saved["adopted_openings"][1]["overlay_bbox_px"] == pytest.approx([120, 36, 160, 60])
    assert [(row["sill_m"], row["head_m"]) for row in saved["artifact"]["openings"]] == [(1.0, 2.2), (4.0, 5.2)]
    assert saved["artifact"]["ink_alignment"]["summary"]["applied_field_count"] > 0
    assert original.read_bytes() == before


@pytest.mark.parametrize("broken", ["nan", "coordinate", "calibration", "count"])
def test_invalid_readings_leave_no_saved_version(tmp_path, broken):
    toolkit, reading, _ = _fixture(tmp_path)
    if broken == "nan":
        reading["z_calibration"]["world_start_m"] = float("nan")
    elif broken == "coordinate":
        reading["openings"][0]["opening_bbox"][2] = 999
    elif broken == "calibration":
        reading["z_calibration"]["pixel_end"] = 999
    else:
        reading["counts"][0]["window_count"] = 2
    with pytest.raises(ValueError):
        _prepare(toolkit, reading)
    assert not (toolkit.run / "drawing_readings").exists()


@pytest.mark.parametrize("broken", ["artifact", "original", "overlay", "id"])
def test_load_refuses_changed_inputs_artifacts_overlay_and_unsafe_id(tmp_path, broken):
    toolkit, reading, original = _fixture(tmp_path)
    _, metadata = _prepare(toolkit, reading)
    identity = metadata["reading_id"]
    if broken == "artifact":
        path = toolkit.run / metadata["reading_file"]
        record = json.loads(path.read_bytes())
        record["artifact"]["openings"][0]["head_m"] += 0.1
        # Even a recomputed envelope must not bypass the adopted artifact hash.
        record["record_sha256"] = _digest({k: v for k, v in record.items() if k != "record_sha256"})
        path.write_text(json.dumps(record), encoding="utf-8")
    elif broken == "original":
        Image.new("RGB", (220, 180), "black").save(original)
    elif broken == "overlay":
        (toolkit.run / metadata["overlay_file"]).write_bytes(b"altered")
    else:
        identity = "../reading_0001"
    with pytest.raises(ValueError):
        load_reading(toolkit, identity)


@pytest.mark.parametrize("changes,consistent,issue", [
    ({}, True, None), ({"second_height": (3.7, 4.9)}, False, "height_difference"),
    ({"missing": True}, False, "missing_in_bim"), ({"extra": True}, False, "extra_in_bim"),
    ({"horizontal_shift": 0.2}, True, None),
    ({"horizontal_shift": 0.32}, False, "horizontal_difference_over_30cm"),
])
def test_compare_reuses_matcher_and_reports_height_counts_and_horizontal_conflicts(tmp_path, changes, consistent, issue):
    toolkit, reading, _ = _fixture(tmp_path)
    _, metadata = _prepare(toolkit, reading)
    source_path = _candidate(toolkit, **changes)
    before = source_path.read_bytes()
    comparison = compare_reading(toolkit, metadata["reading_id"], "candidate_01")
    assert comparison["current_consistent"] is consistent
    assert (issue in {row["type"] for row in comparison["issues"]}) if issue else not comparison["issues"]
    path = toolkit.run / comparison["comparison_file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == comparison["comparison_sha256"]
    full = json.loads(path.read_bytes())
    assert full["match"]["artifact_sha256"] == metadata["artifact_sha256"]
    assert full["height_differences"]
    if changes.get("horizontal_shift") == 0.2:
        assert all(row["bucket"] == "10_30cm" for row in full["match"]["position_comparisons"])
    assert source_path.read_bytes() == before
    assert compare_reading(toolkit, metadata["reading_id"], "candidate_01") == comparison


def test_compare_rejects_source_hash_change(tmp_path):
    toolkit, reading, _ = _fixture(tmp_path)
    _, metadata = _prepare(toolkit, reading)
    path = _candidate(toolkit)
    source = json.loads(path.read_bytes())
    source["openings"][0]["vertices"][0][2] += 0.1
    path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="source model hash mismatch"):
        compare_reading(toolkit, metadata["reading_id"], "candidate_01")
