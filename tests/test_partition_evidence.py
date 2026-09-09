"""Independent source references reach J1 without inventing room identities."""
import copy
import json
import shutil
from pathlib import Path

import pytest

from src.agent.judge.gt import load_gt_document
from src.agent.judge.partition_evidence import attempt_partition_evidence, partition_evidence

SM24 = Path("case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading")
SM21 = Path("case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e")
SM25 = Path("AI_agent/logs/experiments/2026-09-09_m0_endpoint_connections_run01")


def test_reading_alone_finds_known_sm24_extra_seams_without_room_groups():
    result = attempt_partition_evidence(SM24, SM24 / "1_correction/attempts/002")
    pairs = {frozenset(f["space_ids"]) for f in result["reading_boundary_support"]["findings"]}
    assert pairs >= {frozenset(ids) for ids in [
        ["cell_corridor_upper", "cell_corridor_lower"],
        ["cell_office_right_bottom_upper", "cell_office_right_bottom_mid"],
        ["cell_office_right_bottom_mid", "cell_office_right_bottom_lower"],
    ]}
    assert result["reference_partition"]["status"] == "not_evaluated"
    assert result["reading_boundary_support"]["scope"] == "partial_upstream_wall_support_only"
    # Doorway gaps remain review evidence, not automatically removed walls.
    assert all(f["severity"] == "review" for f in result["reading_boundary_support"]["findings"])


@pytest.mark.parametrize("case,run,attempt,count", [
    ("sm24_anchor", SM24, "002", 8), ("sm25-L_anchor", SM25, "001", 29),
])
def test_real_independent_references_find_source_splits(case, run, attempt, count):
    document = load_gt_document(case)
    original = document.model_dump_json()
    result = attempt_partition_evidence(run, run / f"1_correction/attempts/{attempt}", document=document)
    ref = result["reference_partition"]
    assert ref["comparison"]["reference_count"] == count
    assert ref["status"] == "severe"
    assert any(f["code"] == "source_space_split" for f in ref["topology_findings"])
    assert document.model_dump_json() == original
    if case == "sm25-L_anchor":
        assert result["identity"]["reading_basis"] == "frozen_attempt_inputs"
        assert result["reading_boundary_support"]["status"] == "not_evaluated"


def test_sm21_exterior_reference_offset_is_not_called_source_split():
    result = attempt_partition_evidence(SM21, SM21 / "1_correction/attempts/001", document=load_gt_document("sm21_anchor"))
    ref = result["reference_partition"]
    assert ref["comparison"]["status"] == "severe"  # raw 100 mm offset remains visible
    assert ref["status"] == "not_evaluated"
    assert not ref["topology_findings"]
    assert ref["boundary_offset_review_required"]
    assert result["reading_boundary_support"]["status"] == "pass"


def _two_rooms(split=5.):
    return {"footprint_x": [0., 15.], "footprint_y": [0., 8.],
            "floors": [{"name": "Floor 1", "z_floor": 0., "ceiling_height": 3.,
                        "cells": [{"id": "left", "x": [0., split], "y": [0., 8.]},
                                  {"id": "right", "x": [split, 15.], "y": [0., 8.]}]}]}


def _reference():
    document = copy.deepcopy(load_gt_document("sm21_anchor"))
    raw = document.model_dump(mode="json", by_alias=True)
    raw["floors"] = [raw["floors"][0]]
    raw["floors"][0].update(zone_count=2, zones=[
        {"id": "one", "role": "office", "rect_m": [0., 0., 5., 8.]},
        {"id": "two", "role": "office", "rect_m": [5., 0., 15., 8.]},
    ])
    return type(document).model_validate(raw)


@pytest.mark.parametrize("shift,expected", [(0., "pass"), (.01, "minor"), (1., "severe")])
def test_same_count_wrong_internal_partition_is_not_hidden_as_frame_offset(shift, expected):
    result = partition_evidence(_two_rooms(5.+shift), document=_reference())
    assert result["reference_partition"]["status"] == expected
    if expected == "severe":
        assert any(f["code"] == "internal_partition_boundary_changed" for f in result["reference_partition"]["topology_findings"])


def _copy_legacy(tmp_path):
    for path in ("_run/run_manifest.json", "0_reading/attempts/001/output.json", "1_correction/attempts/002/output.json"):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SM24 / path, target)
    return tmp_path / "1_correction/attempts/002"


def test_reading_comes_from_accepted_attempt_not_mutable_root(tmp_path):
    attempt = _copy_legacy(tmp_path)
    before = attempt_partition_evidence(tmp_path, attempt)
    (tmp_path / "0_reading/1f_view.json").write_text('{"strokes":[]}')
    after = attempt_partition_evidence(tmp_path, attempt)
    assert before == after


def test_corrupt_accepted_reading_is_not_replaced_by_flat_fallback(tmp_path):
    attempt = _copy_legacy(tmp_path)
    shutil.copyfile(SM24 / "0_reading/1f_view.json", tmp_path / "0_reading/1f_view.json")
    (tmp_path / "0_reading/attempts/001/output.json").write_text('{}')
    result = attempt_partition_evidence(tmp_path, attempt)
    assert result["reading_boundary_support"]["status"] == "not_evaluated"
    assert "accepted_reading_hash_mismatch" in result["reading_boundary_support"]["input_status"]


def test_changed_accepted_candidate_is_rejected(tmp_path):
    attempt = _copy_legacy(tmp_path)
    (attempt / "output.json").write_text(json.dumps(_two_rooms()))
    with pytest.raises(ValueError, match="accepted_correction_hash_mismatch"):
        attempt_partition_evidence(tmp_path, attempt)


def test_corrupt_frozen_marker_does_not_fall_back_to_accepted_legacy_reading(tmp_path):
    attempt = _copy_legacy(tmp_path)
    (attempt / "window_resolver_inputs.json").write_text('{}')
    result = attempt_partition_evidence(tmp_path, attempt)
    assert result["reading_boundary_support"]["status"] == "not_evaluated"
    assert result["reading_boundary_support"]["input_status"].startswith("reading_reference_rejected")


def test_bad_wall_stroke_makes_partial_reference_unusable():
    doc = {"strokes": [{"id": "bad", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 0]}}]}
    result = partition_evidence(_two_rooms(), readings=[{"input_id": "1f_view", "floor_ref": "1f", "raw_bytes": json.dumps(doc).encode()}])
    assert result["reading_boundary_support"]["status"] == "not_evaluated"


def test_ambiguous_floor_identity_does_not_fall_back_to_order():
    raw = _two_rooms()
    raw["floors"][0]["name"] = "unknown"
    ref = _reference()
    ref.floors.append(ref.floors[0].model_copy(update={"name": "other"}))
    result = partition_evidence(raw, document=ref)
    assert result["reference_partition"]["reason"] == "ambiguous_floor_correspondence"


def test_j1_packet_consumes_partition_evidence_without_extra_model_call(tmp_path, monkeypatch):
    import scripts.tool_scripts.run_stage as rs
    from src.validator.checks.schema import CheckReport

    attempt = _copy_legacy(tmp_path)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    monkeypatch.setattr(rs, "_source_images", lambda *a, **k: [])
    monkeypatch.setattr(rs, "_grade_typed_attempt_artifacts", lambda *a, **k: {"score_vs_gt": None, "grade": None, "score_criteria": []})
    packet = rs._judge_packet("1_correction", "sm24_anchor", SM24.parent, tmp_path, attempt, CheckReport(stage="1_correction"))
    saved = json.loads(Path(packet["source_partition_evidence"]).read_text())
    assert packet["source_partition_criterion"] == saved["criterion"]
    assert saved["criterion"]["suggested_status"] == "severe"
    assert saved["identity"]["reference_sha256"]
