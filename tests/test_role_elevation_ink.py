from __future__ import annotations

import asyncio
import copy
import hashlib
import json

import pytest
from PIL import Image, ImageDraw

from src.agent.runtime_roles.elevation import (
    ElevationReaderTools,
    elevation_submission_tool,
    expand_elevation_submission,
    validate_elevation_artifact,
)
from src.agent.runtime_roles.elevation_ink import align_elevation_artifact
from src.agent.runtime_roles.height_evidence import derive_z_calibration, height_locations
from tests.test_role_readers import Frozen


def _artifact(*, opening: dict, mirrored: bool = False, with_z: bool = True) -> dict:
    artifact = {
        "x_calibration": {
            "pixel_start": 0,
            "pixel_end": 100,
            "world_start_m": 10 if mirrored else 0,
            "world_end_m": 0 if mirrored else 10,
        },
        "openings": [{"evidence_type": "pixels", **opening}],
    }
    if with_z:
        artifact["z_calibration"] = {
            "pixel_start": 10,
            "pixel_end": 110,
            "world_start_m": 10,
            "world_end_m": 0,
        }
    return artifact


def _outlined_rectangle(box, *, fill=0, width=1):
    image = Image.new("L", (140, 120), 255)
    ImageDraw.Draw(image).rectangle(box, outline=fill, width=width)
    return image


def test_aligns_all_four_edges_and_ignores_legacy_evidence_box_as_geometry():
    image = _outlined_rectangle((40, 30, 90, 80))
    artifact = _artifact(
        opening={
            "id": "W1",
            "x_px": [37, 93],
            "width_m": 5.6,
            "sill_m": 3.3,
            "head_m": 7.7,
            # Deliberately much larger: this is only an evidence crop.
            "bbox": [10, 5, 125, 112],
        }
    )

    result = align_elevation_artifact(image, artifact, search_distance_m=0.5)
    aligned = result["openings"][0]

    assert aligned["geometry_source"] == "legacy_x_px_and_calibrated_heights"
    assert aligned["original_bbox_px"] == pytest.approx([37, 33, 93, 77])
    assert aligned["aligned_bbox_px"] == pytest.approx([40, 30, 90, 80])
    assert {edge["status"] for edge in aligned["edges"].values()} == {"aligned"}
    assert aligned["aligned_values"]["x_px"] == pytest.approx([40, 90])
    assert aligned["aligned_values"]["width_m"] == pytest.approx(5)
    assert aligned["aligned_values"]["sill_m"] == pytest.approx(3)
    assert aligned["aligned_values"]["head_m"] == pytest.approx(8)


def test_preserves_mirrored_world_coordinates_while_width_stays_positive():
    image = _outlined_rectangle((30, 20, 70, 60))
    artifact = _artifact(
        mirrored=True,
        opening={
            "id": "D1",
            "opening_bbox": [28, 22, 72, 58],
            "x_px": [28, 72],
            "width_m": 4.4,
            "sill_m": 5.2,
            "head_m": 8.8,
            "bbox": [25, 18, 75, 62],
        },
    )

    aligned = align_elevation_artifact(
        image, artifact, search_distance_m=0.4
    )["openings"][0]

    assert aligned["aligned_values"]["x_px"] == pytest.approx([30, 70])
    assert aligned["aligned_values"]["world_span_m"] == pytest.approx([7, 3])
    assert aligned["aligned_values"]["width_m"] == pytest.approx(4)


def test_weak_ink_and_missing_vertical_calibration_leave_values_unchanged():
    image = _outlined_rectangle((40, 30, 90, 80), fill=225)
    opening = {
        "id": "W1",
        "x_px": [37, 93],
        "width_m": 5.6,
        "sill_m": 2.0,
        "head_m": 8.0,
        "bbox": [10, 5, 125, 112],
    }
    artifact = _artifact(opening=opening, with_z=False)

    aligned = align_elevation_artifact(
        image, artifact, search_distance_m=0.5
    )["openings"][0]

    assert aligned["original_bbox_px"] == [37.0, None, 93.0, None]
    assert aligned["edges"]["left"]["status"] == "no_strong_line"
    assert aligned["edges"]["right"]["status"] == "no_strong_line"
    assert aligned["edges"]["top"]["status"] == "missing_calibration"
    assert aligned["edges"]["bottom"]["status"] == "missing_calibration"
    assert aligned["aligned_values"]["x_px"] == opening["x_px"]
    assert aligned["aligned_values"]["width_m"] == opening["width_m"]
    assert aligned["aligned_values"]["sill_m"] == opening["sill_m"]
    assert aligned["aligned_values"]["head_m"] == opening["head_m"]


def test_reader_submission_binds_image_alignment_and_reloads_immutably(tmp_path):
    async def scenario():
        image_dir = tmp_path / "images"
        image_dir.mkdir()
        image_path = image_dir / "North.png"
        _outlined_rectangle((40, 30, 90, 80)).save(image_path)
        digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
        (tmp_path / "inputs.json").write_text(
            json.dumps({"images": {"North.png": {"sha256": digest}}}),
            encoding="utf-8",
        )
        arguments = {
            "x_calibration": {
                "pixel_start": 0,
                "pixel_end": 100,
                "distance_start_m": 0,
                "distance_end_m": 10,
                "facade_length_m": 10,
            },
            "z_calibration": {
                "pixel_start": 10,
                "pixel_end": 110,
                "world_start_m": 10,
                "world_end_m": 0,
            },
            "elevations": [
                {"id": "roof", "kind": "roof", "value_m": 10,
                 "evidence_type": "pixels", "bbox": [0, 9, 120, 11]},
                {"id": "ground", "kind": "ground", "value_m": 0,
                 "evidence_type": "pixels", "bbox": [0, 109, 120, 111]},
            ],
            "openings": [
                {"id": "W1", "floor_id": "F1", "kind": "window",
                 "evidence_type": "pixels", "opening_bbox": [37, 33, 93, 77]},
            ],
            "counts": [{"floor_id": "F1", "window_count": 1, "door_count": 0}],
            "unresolved": [],
        }
        tools = ElevationReaderTools(
            Frozen(tmp_path),
            role_id="elevation_reader",
            image_name="North.png",
            target="North/F1",
        )
        accepted = await tools.call_tool("submit_elevation_reading", arguments)
        assert not accepted["isError"], accepted
        saved = tools.submission.read()
        artifact = saved["artifact"]
        assert artifact["openings"][0]["x_px"] == pytest.approx([40, 90])
        assert artifact["openings"][0]["width_m"] == pytest.approx(5)
        assert artifact["openings"][0]["sill_m"] == pytest.approx(3)
        assert artifact["openings"][0]["head_m"] == pytest.approx(8)
        assert artifact["openings"][0]["opening_bbox"] == [37.0, 33.0, 93.0, 77.0]
        assert artifact["ink_alignment"]["openings"][0]["aligned_bbox_px"] == pytest.approx(
            [40, 30, 90, 80]
        )
        assert saved["validation"]["image_sha256"] == digest
        assert saved["validation"]["ink_alignment_sha256"]
        assert (await tools.call_tool("submit_elevation_reading", arguments)) == accepted

        resumed = ElevationReaderTools(
            Frozen(tmp_path),
            role_id="elevation_reader",
            image_name="North.png",
            target="North/F1",
        )
        assert resumed.submission.read() == saved
        changed = Image.new("L", (140, 120), 255)
        changed.save(image_path)
        with pytest.raises(ValueError):
            ElevationReaderTools(
                Frozen(tmp_path),
                role_id="elevation_reader",
                image_name="North.png",
                target="North/F1",
            )

    asyncio.run(scenario())


def test_saved_level_calibration_requires_two_consistent_horizontal_bands():
    levels = [
        {"id": "roof", "kind": "roof", "value_m": 10,
         "evidence_type": "pixels", "bbox": [0, 9, 120, 11]},
    ]
    assert derive_z_calibration(levels)["status"] == "missing_two_horizontal_level_bands"

    levels.append(
        {"id": "ground", "kind": "ground", "value_m": 0,
         "evidence_type": "pixels", "bbox": [0, 109, 120, 111]}
    )
    derived = derive_z_calibration(levels)
    assert derived["status"] == "derived_from_saved_level_lines"
    assert derived["calibration"] == {
        "pixel_start": 10.0,
        "pixel_end": 110.0,
        "world_start_m": 10.0,
        "world_end_m": 0.0,
    }

    inconsistent = copy.deepcopy(levels)
    inconsistent.append(
        {"id": "middle", "kind": "floor", "floor_id": "F1", "value_m": 7,
         "evidence_type": "pixels", "bbox": [0, 59, 120, 61]}
    )
    assert derive_z_calibration(inconsistent)["status"] == (
        "rejected_inconsistent_saved_level_lines"
    )


def test_height_evidence_uses_aligned_opening_box_for_its_source_region():
    artifact = {
        "artifact_sha256": "a" * 64,
        "x_calibration": {
            "pixel_start": 0, "pixel_end": 100,
            "world_start_m": 0, "world_end_m": 10,
        },
        "z_calibration": {
            "pixel_start": 0, "pixel_end": 100,
            "world_start_m": 10, "world_end_m": 0,
        },
        "elevations": [],
        "openings": [{
            "id": "W1", "floor_id": "F1", "kind": "window",
            "x_px": [40, 60], "width_m": 2, "sill_m": 4, "head_m": 7,
            "evidence_type": "pixels", "bbox": [5, 5, 95, 95],
            "opening_bbox": [38, 28, 62, 62],
        }],
        "ink_alignment": {"openings": [{"id": "W1", "aligned_bbox_px": [40, 30, 60, 60]}]},
    }
    match = {
        "tolerances_m": {"position": 0.2, "width": 0.2},
        "matches": [{"source_opening_id": "source-W1", "artifact_opening_id": "W1"}],
    }

    located = height_locations(artifact, match, [100, 100])["openings"]["W1"]

    assert located["aligned_opening_bbox"] == [40, 30, 60, 60]
    assert located["original_bbox"] == [5, 5, 95, 95]
    assert located["source_box"] == [37, 28, 63, 62]


def test_legacy_expanded_recording_stays_readable_but_is_not_public_schema():
    x_schema = elevation_submission_tool()["inputSchema"]["properties"]["x_calibration"]
    assert "world_start_m" not in x_schema["properties"]
    recorded = {
        "orientation": "North",
        "view_direction": "South",
        "x_calibration": {
            "pixel_start": 100,
            "pixel_end": 900,
            "world_start_m": 10,
            "world_end_m": 0,
            "world_axis": "x",
        },
    }

    expanded = expand_elevation_submission(recorded, "North/F1")

    assert expanded == recorded
    with pytest.raises(ValueError):
        expand_elevation_submission({**recorded, "orientation": "South"}, "North/F1")


@pytest.mark.parametrize("basis", ["annotation", "annotation_and_pixels", "visual_estimate", "assumption", "declared"])
def test_numeric_and_mixed_evidence_is_checked_without_replacing_any_value(basis):
    opening = {"id": "W1", "evidence_type": basis, "opening_bbox": [37, 33, 93, 77],
               "x_px": [37, 93], "width_m": 5.7, "sill_m": 3.3, "head_m": 7.7}
    result = align_elevation_artifact(_outlined_rectangle((40, 30, 90, 80)),
        _artifact(opening=opening), search_distance_m=0.5)["openings"][0]
    assert all(result["aligned_values"][key] == opening[key] for key in ("x_px", "width_m", "sill_m", "head_m"))
    assert not result["applied_fields"]
    assert {r["field"] for r in result["inconsistencies"]} == {"x_px", "width_m", "sill_m", "head_m"}
    assert result["candidate_bbox_px"] == pytest.approx([40, 30, 90, 80])
    assert result["effective_bbox_px"] == pytest.approx([37, 33, 93, 77])
    assert result["tolerance_m"] == pytest.approx({"x": 0.2, "z": 0.2})


def test_multiple_strong_strokes_do_not_authorize_pixel_replacement():
    image = _outlined_rectangle((40, 30, 90, 80))
    ImageDraw.Draw(image).line((45, 30, 45, 80), fill=0)
    opening = {"id": "W1", "x_px": [43, 93], "width_m": 5, "sill_m": 3.3, "head_m": 7.7}
    result = align_elevation_artifact(image, _artifact(opening=opening), search_distance_m=0.5)["openings"][0]
    assert len(result["edges"]["left"]["candidates"]) == 2
    assert result["aligned_values"]["x_px"] == opening["x_px"]
    assert result["aligned_values"]["width_m"] == opening["width_m"]
    assert "x_px" not in result["applied_fields"]


def test_confirmed_pixel_edges_do_not_reround_original_numeric_values():
    opening = {"id": "W1", "x_px": [40, 90], "width_m": 4.98, "sill_m": 3, "head_m": 8}
    result = align_elevation_artifact(_outlined_rectangle((40, 30, 90, 80)),
        _artifact(opening=opening))["openings"][0]
    assert not result["applied_fields"] and not result["inconsistencies"]
    assert result["aligned_values"]["width_m"] == 4.98


def test_floor_contact_sill_is_not_replaced_by_another_lower_ink_line():
    opening = {"id": "D1", "kind": "door", "floor_id": "F1", "opening_bbox": [37, 33, 93, 110],
               "x_px": [37, 93], "width_m": 5.6, "sill_m": 0, "head_m": 7.7}
    artifact = _artifact(opening=opening)
    artifact["elevations"] = [{"id": "floor", "kind": "floor", "floor_id": "F1", "value_m": 0,
                               "evidence_type": "annotation", "bbox": [0, 109, 130, 111]}]
    result = align_elevation_artifact(_outlined_rectangle((40, 30, 90, 114)), artifact,
        search_distance_m=0.5)["openings"][0]
    assert len(result["edges"]["bottom"]["candidates"]) == 1
    assert result["ink_values"]["sill_m"] == pytest.approx(-0.4)
    assert result["aligned_values"]["sill_m"] == 0
    assert result["effective_bbox_px"][3] == 110
    assert result["floor_contact"][0]["id"] == "floor"
    assert result["field_decisions"]["sill_m"] == "retained_floor_contact"
    assert any(r["field"] == "sill_m" for r in result["inconsistencies"])
    # A raised threshold or a different-floor line does not establish contact.
    artifact["openings"][0]["sill_m"] = 0.2
    raised = align_elevation_artifact(_outlined_rectangle((40, 30, 90, 114)), artifact,
        search_distance_m=0.5)["openings"][0]
    assert not raised["floor_contact"]


def test_normalization_retains_explicit_annotated_values_beside_a_rough_box():
    from src.agent.runtime_roles.guidance import COMPACT_ELEVATION_EXAMPLE
    args = copy.deepcopy(COMPACT_ELEVATION_EXAMPLE)
    args["openings"][0].update(evidence_type="annotation_and_pixels", x_px=[205, 297],
                               width_m=1.1, sill_m=1.05, head_m=2.55)
    normalized = validate_elevation_artifact(expand_elevation_submission(args, "North/F1"), image_name="North.png")
    opening = normalized["openings"][0]
    assert [opening[key] for key in ("x_px", "width_m", "sill_m", "head_m")] == [[205, 297], 1.1, 1.05, 2.55]
    args["openings"][0].pop("width_m")
    with pytest.raises(ValueError):
        validate_elevation_artifact(expand_elevation_submission(args, "North/F1"), image_name="North.png")
