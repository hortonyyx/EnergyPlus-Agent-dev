#!/usr/bin/env python3
"""Validate the role-case fixture and prepare a human review packet.

This helper deliberately does not decide correctness.  It joins model returns to
the evaluation-only references and flags only structural omissions so a reviewer
can score every rubric item after reading the image, return, and reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
MANIFEST = HERE / "manifest.json"
REFERENCES = HERE / "references.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_suite() -> dict[str, Any]:
    manifest = _load(MANIFEST)
    references = _load(REFERENCES)
    errors: list[str] = []
    cases = manifest.get("cases", [])
    refs = references.get("cases", [])
    ids = [row.get("case_id") for row in cases]
    ref_ids = [row.get("case_id") for row in refs]

    if not 8 <= len(cases) <= 12:
        errors.append(f"expected 8..12 cases, got {len(cases)}")
    if len(ids) != len(set(ids)):
        errors.append("manifest case_id values are not unique")
    if len(ref_ids) != len(set(ref_ids)):
        errors.append("reference case_id values are not unique")
    if set(ids) != set(ref_ids):
        errors.append("manifest and reference case IDs differ")
    if manifest.get("suite_id") != references.get("suite_id"):
        errors.append("manifest and reference suite IDs differ")
    if not references.get("evaluation_side_only"):
        errors.append("references must be marked evaluation_side_only")

    group_counts = Counter(row.get("test_group") for row in cases)
    for group in ("drawing", "mesh_render", "photo_surrogate", "information_insufficient"):
        if group_counts[group] < 2:
            errors.append(f"test_group {group!r} has only {group_counts[group]} cases")

    for case in cases:
        case_id = case.get("case_id", "<missing>")
        if case.get("input_kind") not in {"drawing", "mesh_render", "photo"}:
            errors.append(f"{case_id}: invalid input_kind")
        if case.get("information_sufficiency") not in {
            "locally_sufficient", "partially_sufficient", "insufficient"
        }:
            errors.append(f"{case_id}: invalid information_sufficiency")
        if case.get("input_kind") == "photo" and not case.get("photo_surrogate"):
            errors.append(f"{case_id}: repository has no approved real-photo fixture")
        if not str(case.get("question", "")).strip():
            errors.append(f"{case_id}: question is empty")
        for image in case.get("images", []):
            rel = Path(image.get("path", ""))
            if rel.is_absolute() or ".." in rel.parts:
                errors.append(f"{case_id}: image path must be repository-relative")
                continue
            path = REPO / rel
            if not path.is_file():
                errors.append(f"{case_id}: missing image {rel}")
                continue
            if _sha256(path) != image.get("sha256"):
                errors.append(f"{case_id}: sha256 mismatch for {rel}")
            with Image.open(path) as opened:
                if [opened.width, opened.height] != [image.get("width_px"), image.get("height_px")]:
                    errors.append(f"{case_id}: image dimensions mismatch for {rel}")
            bbox = image.get("available_bbox_px")
            expected = [0, 0, image.get("width_px"), image.get("height_px")]
            if bbox != expected:
                errors.append(f"{case_id}: available bbox must cover exact original image")
            if image.get("coordinate_relation") != {
                "original_space": "original_image_pixels",
                "referenced_space": "original_image_pixels",
                "relation": "identity",
            }:
                errors.append(f"{case_id}: role-case image coordinates must be identity original pixels")
            if not image.get("view_source") or not image.get("coordinate_source"):
                errors.append(f"{case_id}: view/coordinate source is missing")

    ref_by_id = {row.get("case_id"): row for row in refs}
    for case_id in ids:
        ref = ref_by_id.get(case_id, {})
        rubric = ref.get("rubric", [])
        if sum(item.get("points", 0) for item in rubric) != ref.get("max_points"):
            errors.append(f"{case_id}: rubric points do not sum to max_points")
        if not ref.get("basis"):
            errors.append(f"{case_id}: reference basis is empty")
        for basis in ref.get("basis", []):
            rel = Path(basis.get("path", ""))
            path = REPO / rel
            if rel.is_absolute() or ".." in rel.parts or not path.is_file():
                errors.append(f"{case_id}: invalid reference basis path {rel}")
            elif _sha256(path) != basis.get("sha256"):
                errors.append(f"{case_id}: reference basis hash mismatch for {rel}")

    return {
        "ok": not errors,
        "case_count": len(cases),
        "test_group_counts": dict(sorted(group_counts.items())),
        "input_kind_counts": dict(sorted(Counter(row.get("input_kind") for row in cases).items())),
        "information_sufficiency_counts": dict(
            sorted(Counter(row.get("information_sufficiency") for row in cases).items())
        ),
        "errors": errors,
    }


def _response_map(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("responses"), list):
        payload = payload["responses"]
    if isinstance(payload, list):
        return {str(row["case_id"]): row.get("response") for row in payload}
    if isinstance(payload, dict):
        return {str(key): value for key, value in payload.items()}
    raise ValueError("responses must be an object keyed by case_id or a responses list")


def _structure_issues(response: Any) -> list[str]:
    if response is None:
        return ["missing response"]
    if not isinstance(response, dict):
        return ["response is not an object"]
    issues: list[str] = []
    for field in ("directly_seen", "interpretations", "uncertain"):
        if field not in response:
            issues.append(f"missing {field}")
        elif not isinstance(response[field], list):
            issues.append(f"{field} is not a list")
    for index, row in enumerate(response.get("directly_seen", [])):
        location = row.get("location", {}) if isinstance(row, dict) else {}
        box = location.get("box_original_pixels")
        if not isinstance(box, list) or len(box) != 4:
            issues.append(f"directly_seen[{index}] lacks a four-number original-pixel box")
    return issues


def prepare_review_packet(responses: Any) -> dict[str, Any]:
    manifest = _load(MANIFEST)
    references = _load(REFERENCES)
    response_by_id = _response_map(responses)
    reference_by_id = {row["case_id"]: row for row in references["cases"]}
    rows = []
    for case in manifest["cases"]:
        case_id = case["case_id"]
        response = response_by_id.get(case_id)
        reference = reference_by_id[case_id]
        rows.append({
            "case_id": case_id,
            "test_group": case["test_group"],
            "input_kind": case["input_kind"],
            "information_sufficiency": case["information_sufficiency"],
            "photo_surrogate": case["photo_surrogate"],
            "question": case["question"],
            "images": case["images"],
            "response": response,
            "response_structure_issues": _structure_issues(response),
            "reference_scope": reference["reference_scope"],
            "honesty_only": reference["honesty_only"],
            "reference_answer": reference["reference_answer"],
            "expected_localizations": reference["expected_localizations"],
            "rubric": reference["rubric"],
            "max_points": reference["max_points"],
            "human_judgement": {
                "criterion_scores": {},
                "total": None,
                "verdict": None,
                "notes": ""
            }
        })
    unknown = sorted(set(response_by_id) - {row["case_id"] for row in manifest["cases"]})
    return {
        "schema_version": "local_observer_human_review_packet_v1",
        "suite_id": manifest["suite_id"],
        "automatic_correctness": False,
        "unknown_response_case_ids": unknown,
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    prepare = sub.add_parser("prepare-review")
    prepare.add_argument("--responses", type=Path, required=True)
    prepare.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "validate":
        result = validate_suite()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    packet = prepare_review_packet(_load(args.responses))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(packet["cases"]), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
