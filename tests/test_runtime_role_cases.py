from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLE_CASES = (
    ROOT
    / "AI_agent/logs/experiments/2026-10-02_harness_stage3/role_cases"
)


def _load(name: str):
    return json.loads((ROLE_CASES / name).read_text(encoding="utf-8"))


def _helper():
    path = ROLE_CASES / "evaluate.py"
    spec = importlib.util.spec_from_file_location("stage3_role_case_evaluate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_role_case_manifest_and_reference_assets_validate_by_hash_and_dimensions():
    result = _helper().validate_suite()
    assert result == {
        "ok": True,
        "case_count": 10,
        "test_group_counts": {
            "drawing": 3,
            "information_insufficient": 2,
            "mesh_render": 3,
            "photo_surrogate": 2,
        },
        "input_kind_counts": {"drawing": 3, "mesh_render": 5, "photo": 2},
        "information_sufficiency_counts": {
            "insufficient": 4,
            "locally_sufficient": 3,
            "partially_sufficient": 3,
        },
        "errors": [],
    }


def test_four_test_groups_are_covered_without_equating_format_and_sufficiency():
    cases = _load("manifest.json")["cases"]
    groups = Counter(case["test_group"] for case in cases)
    assert set(groups) == {
        "drawing",
        "mesh_render",
        "photo_surrogate",
        "information_insufficient",
    }
    assert all(count >= 2 for count in groups.values())

    insufficient = [case for case in cases if case["test_group"] == "information_insufficient"]
    assert {case["input_kind"] for case in insufficient} == {"mesh_render"}
    assert {case["information_sufficiency"] for case in insufficient} == {"insufficient"}
    assert all(case["input_kind"] != case["information_sufficiency"] for case in cases)

    photos = [case for case in cases if case["input_kind"] == "photo"]
    assert len(photos) == 2
    assert all(case["photo_surrogate"] for case in photos)
    assert all("代替" in case["images"][0]["view_source"] for case in photos)


def test_runtime_manifest_does_not_inline_evaluation_answers_or_rubrics():
    manifest = _load("manifest.json")
    serialized = json.dumps(manifest["cases"], ensure_ascii=False)
    for forbidden in (
        "reference_answer",
        "expected_localizations",
        "rubric",
        "honesty_only",
        "max_points",
    ):
        assert forbidden not in serialized

    questions = "\n".join(case["question"] for case in manifest["cases"])
    for leaked_answer in ("3.4 m", "2.8 m", "10000 mm", "20000 mm", "900 mm"):
        assert leaked_answer not in questions

    assert manifest["evaluation"]["reference_file"] == "references.json"
    assert manifest["evaluation"]["automatic_correctness"] is False


def test_each_case_requires_three_part_observation_and_original_pixel_localization():
    manifest = _load("manifest.json")
    assert manifest["response_contract"]["schema"] == "localized_evidence_result_v1"
    assert manifest["response_contract"]["required_sections"] == [
        "directly_seen",
        "interpretations",
        "uncertain",
    ]
    assert manifest["coordinate_convention"]["box_space"] == "original_image_pixels"

    for case in manifest["cases"]:
        assert case["images"]
        for image in case["images"]:
            assert image["available_bbox_px"] == [
                0,
                0,
                image["width_px"],
                image["height_px"],
            ]
            assert image["coordinate_relation"] == {
                "original_space": "original_image_pixels",
                "referenced_space": "original_image_pixels",
                "relation": "identity",
            }
            assert image["path"] == str(Path(image["path"]))
            assert len(image["sha256"]) == 64
            assert image["view_source"]
            assert image["coordinate_source"]


def test_reference_rubrics_are_structured_and_honesty_only_when_truth_is_missing():
    references = _load("references.json")
    rows = {row["case_id"]: row for row in references["cases"]}
    assert len(rows) == 10
    assert {
        case_id for case_id, row in rows.items() if row["honesty_only"]
    } == {
        "photo_surrogate_voimatalo_front_fragment",
        "photo_surrogate_voimatalo_side_fragment",
        "insufficient_voimatalo_hidden_end_windows",
        "insufficient_voimatalo_annex_fragment_count",
    }
    for row in rows.values():
        assert row["max_points"] == 10
        assert sum(item["points"] for item in row["rubric"]) == 10
        assert row["reference_answer"]["directly_seen"]
        assert row["reference_answer"]["uncertain"]
        assert row["basis"]


def test_review_helper_only_flags_structure_and_leaves_human_scores_blank():
    helper = _helper()
    response = {
        "drawing_sm24_east_window_levels": {
            "directly_seen": [
                {
                    "observation_id": "seen:1",
                    "statement": "An opening is visible.",
                    "location": {
                        "image_ref": "role_view_sm24_east",
                        "box_original_pixels": [100, 100, 200, 200],
                    },
                }
            ],
            "interpretations": [],
            "uncertain": [],
        }
    }
    packet = helper.prepare_review_packet(response)
    assert packet["automatic_correctness"] is False
    assert len(packet["cases"]) == 10
    first = packet["cases"][0]
    assert first["case_id"] == "drawing_sm24_east_window_levels"
    assert first["response_structure_issues"] == []
    assert first["reference_answer"]
    assert first["human_judgement"] == {
        "criterion_scores": {},
        "total": None,
        "verdict": None,
        "notes": "",
    }
    assert all(
        row["response_structure_issues"] == ["missing response"]
        for row in packet["cases"][1:]
    )
