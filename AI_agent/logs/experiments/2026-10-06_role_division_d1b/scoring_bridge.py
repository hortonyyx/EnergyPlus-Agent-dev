"""Bridge role-reader artifacts into the frozen D1-A neutral scorer format.

The bridge never reads evaluation references while converting an answer.  It
keeps assigned-role scoring separate from complete-reference scoring so an
unassigned floor or facade is reported as out of scope instead of becoming a
role-answer error.  The D1-A scorer is loaded unchanged from the adjacent
experiment directory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence

from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.runtime_roles.elevation import validate_elevation_artifact
from src.agent.runtime_roles.readers import validate_plan_artifact


HERE = Path(__file__).resolve().parent
D1A_SCORER = HERE.parent / "2026-10-06_role_division_analysis" / "score_role_answers.py"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _load_json(value: Mapping[str, Any] | str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if isinstance(value, Mapping):
        result = copy.deepcopy(dict(value))
        return result, {"path": None, "sha256": _sha256(result)}
    path = Path(value).resolve()
    raw = path.read_bytes()
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return result, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


@lru_cache(maxsize=1)
def d1a_scorer() -> ModuleType:
    """Load the accepted D1-A scorer without copying or modifying it."""

    spec = importlib.util.spec_from_file_location("role_division_d1a_scorer", D1A_SCORER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load D1-A scorer from {D1A_SCORER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _opening_row(row: Mapping[str, Any], floor_id: str) -> dict[str, Any]:
    p1 = [float(value) for value in row["p1_world_m"]]
    p2 = [float(value) for value in row["p2_world_m"]]
    if abs(p1[0] - p2[0]) <= 1e-8:
        axis, span, cross = "y", sorted([p1[1], p2[1]]), (p1[0] + p2[0]) / 2
    elif abs(p1[1] - p2[1]) <= 1e-8:
        axis, span, cross = "x", sorted([p1[0], p2[0]]), (p1[1] + p2[1]) / 2
    else:
        raise ValueError(f"plan opening {row.get('opening_id')!r} is not axis aligned")
    return {
        "id": row["opening_id"],
        "floor_id": floor_id,
        "kind": row["kind"],
        "axis": axis,
        "span_m": span,
        "cross_m": cross,
        "width_m": float(row["width_m"]),
        "host_room_ids": list(row["space_ids"]),
        "exterior": bool(row["exterior"]),
    }


def _validate_submitted_plan_artifact(
    value: Mapping[str, Any], *, image_name: str | None,
) -> dict[str, Any]:
    """Validate the immutable trial plan without discarding delivery-only notes.

    ``submit_plan_reading`` keeps ``artifact.plan`` byte-for-byte equivalent to
    the successful trial, while the artifact's outer ``unresolved`` list may add
    delivery questions.  The base validator intentionally requires those two
    lists to match for pre-submit drafts, so validate a copy against the trial
    plan and restore the accepted outer list afterwards.
    """

    if not isinstance(value, Mapping):
        raise ValueError("plan artifact must be an object")
    submitted = copy.deepcopy(dict(value))
    outer_unresolved = copy.deepcopy(submitted.get("unresolved"))
    if not isinstance(outer_unresolved, list) or any(
        not isinstance(row, str) or len(row) < 1 for row in outer_unresolved
    ):
        raise ValueError("plan artifact unresolved must be a list of non-empty strings")
    plan = submitted.get("plan")
    if not isinstance(plan, Mapping) or "unresolved" not in plan:
        raise ValueError("plan artifact plan.unresolved is required")
    verification = copy.deepcopy(submitted)
    verification["unresolved"] = copy.deepcopy(plan["unresolved"])
    normalized = validate_plan_artifact(verification, image_name=image_name)
    missing = [row for row in normalized["plan"]["unresolved"] if row not in outer_unresolved]
    if missing:
        raise ValueError(f"plan artifact outer unresolved dropped trial items: {missing}")
    normalized["unresolved"] = outer_unresolved
    return normalized


def neutral_plan_from_artifact(
    artifact: Mapping[str, Any] | str | Path,
    *,
    image_size: tuple[int, int],
    image_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile a numeric plan artifact into one neutral plan question.

    Tagged profile quantities must already have been expanded by the trial
    receipt.  Callers with a saved passed-trial source should use
    :func:`neutral_plan_from_trial_source` instead.
    """

    value, identity = _load_json(artifact)
    normalized = _validate_submitted_plan_artifact(value, image_name=image_name)
    proposal, metadata = compile_plan_partition(
        normalized["plan"], image_size=image_size, image_name=image_name,
    )
    geometry = proposal["geometry"]
    floor = geometry["floors"][0]
    floor_id = str(floor["name"])
    footprint = metadata["footprint"]["world_polygon_m"]
    partitions = {
        "type": "MultiLineString",
        "coordinates": [row["world_points_m"] for row in metadata["partition_mapping"]],
    }
    rooms = [
        {
            "id": row["id"],
            "name": None,
            "role": row.get("role"),
            "polygon_m": row["polygon"],
        }
        for row in floor["cells"]
    ]
    openings = [
        _opening_row(row, floor_id)
        for row in metadata["opening_hosts"]
        if row["kind"] in {"door", "window"}
    ]
    neutral = {
        "floor_id": floor_id,
        "z_floor_m": float(floor["z_floor"]),
        "ceiling_height_m": float(floor["ceiling_height"]),
        "exterior_m": footprint,
        "partitions_m": partitions,
        "rooms": rooms,
        "openings": openings,
    }
    audit = {
        "kind": "plan_artifact",
        **identity,
        "image": image_name,
        "image_size": list(image_size),
        "floor_id": floor_id,
        "evidence_count": len(normalized["evidence"]),
        "unresolved": list(normalized["unresolved"]),
        "counts": {"rooms": len(rooms), "openings": len(openings)},
    }
    return neutral, audit


def neutral_plan_from_trial_source(
    source: Mapping[str, Any] | str | Path,
    receipt: Mapping[str, Any] | str | Path,
    *,
    case: str,
    floor_ids: Iterable[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert only a source proven to belong to a passed isolated trial."""

    source_value, source_identity = _load_json(source)
    receipt_value, receipt_identity = _load_json(receipt)
    if receipt_value.get("status") != "passed" or receipt_value.get("source_geometry_ready") is not True:
        raise ValueError("plan trial receipt is not a passed, source-geometry-ready trial")
    expected = receipt_value.get("candidate_source_sha256")
    if expected != source_identity["sha256"]:
        raise ValueError(
            "passed plan trial source hash mismatch: "
            f"receipt={expected!r}, source={source_identity['sha256']!r}"
        )
    answer = d1a_scorer().source_answer(source_value, case)
    selected = None if floor_ids is None else set(floor_ids)
    rows = [
        row for row in answer["plan_questions"]
        if selected is None or row["floor_id"] in selected
    ]
    if selected is not None and {row["floor_id"] for row in rows} != selected:
        missing = sorted(selected - {row["floor_id"] for row in rows})
        raise ValueError(f"passed plan trial source is missing assigned floors: {missing}")
    audit = {
        "kind": "passed_trial_source",
        "source": source_identity,
        "receipt": receipt_identity,
        "receipt_status": receipt_value["status"],
        "receipt_candidate": receipt_value.get("candidate"),
        "floors": [row["floor_id"] for row in rows],
        "counts": {
            "rooms": sum(len(row["rooms"]) for row in rows),
            "openings": sum(len(row["openings"]) for row in rows),
        },
    }
    return rows, audit


def neutral_elevation_from_artifact(
    artifact: Mapping[str, Any] | str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    value, identity = _load_json(artifact)
    normalized = validate_elevation_artifact(value)
    calibration = normalized["x_calibration"]
    pixel_start = float(calibration["pixel_start"])
    pixel_end = float(calibration["pixel_end"])
    world_start = float(calibration["world_start_m"])
    world_end = float(calibration["world_end_m"])
    if pixel_start == pixel_end:
        raise ValueError("elevation horizontal calibration has zero pixel span")

    def world(pixel: float) -> float:
        fraction = (float(pixel) - pixel_start) / (pixel_end - pixel_start)
        return world_start + fraction * (world_end - world_start)

    facade = normalized["orientation"]
    openings = []
    for row in normalized["openings"]:
        span = sorted([world(row["x_px"][0]), world(row["x_px"][1])])
        openings.append({
            "id": f"{facade}:{row['id']}",
            "facade": facade,
            "floor_id": row["floor_id"],
            "kind": row["kind"],
            "span_m": span,
            "width_m": float(row["width_m"]),
            "sill_m": float(row["sill_m"]),
            "head_m": float(row["head_m"]),
            "host_room_id": None,
        })
    openings.sort(key=lambda row: (row["floor_id"], row["span_m"][0], row["kind"]))
    neutral = {
        "facade": facade,
        "openings": openings,
        "counts": {
            kind: sum(row["kind"] == kind for row in openings)
            for kind in ("door", "window")
        },
    }
    audit = {
        "kind": "elevation_artifact",
        **identity,
        "facade": facade,
        "world_axis": calibration["world_axis"],
        "unresolved": list(normalized["unresolved"]),
        "counts": neutral["counts"],
    }
    return neutral, audit


def convert_role_artifacts(
    *,
    case: str,
    plan_artifact: Mapping[str, Any] | str | Path | None = None,
    plan_image_size: tuple[int, int] | None = None,
    plan_image_name: str | None = None,
    plan_trial_source: Mapping[str, Any] | str | Path | None = None,
    plan_trial_receipt: Mapping[str, Any] | str | Path | None = None,
    elevation_artifacts: Sequence[Mapping[str, Any] | str | Path] = (),
    assigned_plan_floors: Iterable[str] | None = None,
    assigned_elevation_facades: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Return a neutral answer plus explicit assigned/submitted scope."""

    if not isinstance(case, str) or not case.strip():
        raise ValueError("case must be a non-empty string")
    if plan_trial_source is not None and plan_trial_receipt is None:
        raise ValueError("plan_trial_source requires its passed trial receipt")
    if plan_trial_receipt is not None and plan_trial_source is None:
        raise ValueError("plan_trial_receipt requires its saved trial source")
    plan_rows: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    requested_floors = None if assigned_plan_floors is None else sorted(set(assigned_plan_floors))
    if plan_trial_source is not None:
        plan_rows, audit = neutral_plan_from_trial_source(
            plan_trial_source,
            plan_trial_receipt,
            case=case,
            floor_ids=requested_floors,
        )
        inputs.append(audit)
        if plan_artifact is not None:
            artifact_value, identity = _load_json(plan_artifact)
            image_name = plan_image_name or artifact_value.get("plan", {}).get("image")
            normalized = _validate_submitted_plan_artifact(artifact_value, image_name=image_name)
            inputs.append({
                "kind": "plan_artifact_metadata",
                **identity,
                "floor_id": normalized["plan"]["floor_id"],
                "evidence_count": len(normalized["evidence"]),
                "unresolved": list(normalized["unresolved"]),
                "geometry_source": "passed_trial_source",
            })
    elif plan_artifact is not None:
        if plan_image_size is None or plan_image_name is None:
            raise ValueError("direct plan artifact conversion requires plan_image_size and plan_image_name")
        row, audit = neutral_plan_from_artifact(
            plan_artifact, image_size=plan_image_size, image_name=plan_image_name,
        )
        plan_rows = [row]
        inputs.append(audit)

    elevation_rows = []
    for artifact in elevation_artifacts:
        row, audit = neutral_elevation_from_artifact(artifact)
        elevation_rows.append(row)
        inputs.append(audit)
    submitted_floors = sorted(row["floor_id"] for row in plan_rows)
    submitted_facades = sorted(row["facade"] for row in elevation_rows)
    assigned_floors = submitted_floors if requested_floors is None else requested_floors
    assigned_facades = (
        submitted_facades
        if assigned_elevation_facades is None
        else sorted(set(assigned_elevation_facades))
    )
    extra_floors = sorted(set(submitted_floors) - set(assigned_floors))
    extra_facades = sorted(set(submitted_facades) - set(assigned_facades))
    if extra_floors or extra_facades:
        raise ValueError(
            f"submitted role answers exceed assigned scope: floors={extra_floors}, facades={extra_facades}"
        )
    answer = {
        "schema_version": "role_answer_v1",
        "case": case,
        "coordinate_frame": "building_axis_world_m",
        "plan_questions": plan_rows,
        "elevation_questions": elevation_rows,
    }
    return {
        "schema_version": "role_scoring_bridge_v1",
        "case": case,
        "answer": answer,
        "scope": {
            "assigned": {
                "plan_floors": assigned_floors,
                "elevation_facades": assigned_facades,
            },
            "submitted": {
                "plan_floors": submitted_floors,
                "elevation_facades": submitted_facades,
            },
            "missing_assigned": {
                "plan_floors": sorted(set(assigned_floors) - set(submitted_floors)),
                "elevation_facades": sorted(set(assigned_facades) - set(submitted_facades)),
            },
        },
        "inputs": inputs,
        "limits": [
            "Conversion uses only submitted role artifacts or a source bound to a passed trial receipt.",
            "A passed isolated trial is not relabelled as a validated final reader delivery.",
            "Unassigned reference questions are reported by complete scoring but do not reduce assigned-role scoring.",
        ],
    }


def _filter_reference(reference: Mapping[str, Any], floors: set[str], facades: set[str]) -> dict[str, Any]:
    result = copy.deepcopy(dict(reference))
    result["plan_questions"] = [
        row for row in reference["plan_questions"] if row["floor_id"] in floors
    ]
    result["elevation_questions"] = [
        row for row in reference["elevation_questions"] if row["facade"] in facades
    ]
    return result


def _filter_answer(answer: Mapping[str, Any], floors: set[str], facades: set[str]) -> dict[str, Any]:
    result = copy.deepcopy(dict(answer))
    result["plan_questions"] = [
        row for row in answer["plan_questions"] if row["floor_id"] in floors
    ]
    result["elevation_questions"] = [
        row for row in answer["elevation_questions"] if row["facade"] in facades
    ]
    return result


def score_scoped_answer(
    reference: Mapping[str, Any] | str | Path,
    conversion: Mapping[str, Any],
) -> dict[str, Any]:
    """Score assigned questions and the complete reference as distinct results."""

    reference_value, reference_identity = _load_json(reference)
    scope = conversion["scope"]
    assigned_floors = set(scope["assigned"]["plan_floors"])
    assigned_facades = set(scope["assigned"]["elevation_facades"])
    answer = conversion["answer"]
    scoped_reference = _filter_reference(reference_value, assigned_floors, assigned_facades)
    scoped_answer = _filter_answer(answer, assigned_floors, assigned_facades)
    scorer = d1a_scorer()
    scoped_raw = scorer.score(scoped_reference, scoped_answer)
    complete_raw = scorer.score(reference_value, answer)

    questions = []
    for floor_id in sorted(assigned_floors):
        raw = scorer.score(
            _filter_reference(reference_value, {floor_id}, set()),
            _filter_answer(answer, {floor_id}, set()),
        )
        questions.append({"role": "plan_reader", "question": floor_id, "status": raw["status"], "raw": raw})
    for facade in sorted(assigned_facades):
        raw = scorer.score(
            _filter_reference(reference_value, set(), {facade}),
            _filter_answer(answer, set(), {facade}),
        )
        questions.append({
            "role": "elevation_reader", "question": facade,
            "status": raw["status"], "raw": raw,
        })
    pass_count = sum(row["status"] == "pass" for row in questions)
    reference_floors = {row["floor_id"] for row in reference_value["plan_questions"]}
    reference_facades = {row["facade"] for row in reference_value["elevation_questions"]}
    return {
        "schema_version": "role_scoped_score_v1",
        "case": reference_value.get("case"),
        "reference": reference_identity,
        "assigned_role_score": {
            "status": scoped_raw["status"] if questions else "not_scored",
            "questions_passed": pass_count,
            "questions_total": len(questions),
            "questions": questions,
            "raw": scoped_raw,
        },
        "complete_reference_score": {
            "status": complete_raw["status"],
            "raw": complete_raw,
            "warning": "This includes unassigned questions; use assigned_role_score for role delivery acceptance.",
        },
        "coverage": {
            "assigned": copy.deepcopy(scope["assigned"]),
            "submitted": copy.deepcopy(scope["submitted"]),
            "missing_assigned": copy.deepcopy(scope["missing_assigned"]),
            "complete_reference": {
                "plan_floors": sorted(reference_floors),
                "elevation_facades": sorted(reference_facades),
            },
            "unassigned_reference": {
                "plan_floors": sorted(reference_floors - assigned_floors),
                "elevation_facades": sorted(reference_facades - assigned_facades),
            },
            "assigned_not_in_reference": {
                "plan_floors": sorted(assigned_floors - reference_floors),
                "elevation_facades": sorted(assigned_facades - reference_facades),
            },
        },
    }


def write_json(path: str | Path, value: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _image_size(value: str) -> tuple[int, int]:
    parts = value.lower().split("x")
    if len(parts) != 2 or any(not part.isdigit() or int(part) <= 0 for part in parts):
        raise argparse.ArgumentTypeError("image size must be WIDTHxHEIGHT")
    return int(parts[0]), int(parts[1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--plan-artifact", type=Path)
    parser.add_argument("--plan-image-size", type=_image_size)
    parser.add_argument("--plan-image-name")
    parser.add_argument("--plan-trial-source", type=Path)
    parser.add_argument("--plan-trial-receipt", type=Path)
    parser.add_argument("--elevation", type=Path, action="append", default=[])
    parser.add_argument("--assigned-plan-floor", action="append")
    parser.add_argument("--assigned-facade", action="append")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    conversion = convert_role_artifacts(
        case=args.case,
        plan_artifact=args.plan_artifact,
        plan_image_size=args.plan_image_size,
        plan_image_name=args.plan_image_name,
        plan_trial_source=args.plan_trial_source,
        plan_trial_receipt=args.plan_trial_receipt,
        elevation_artifacts=args.elevation,
        assigned_plan_floors=args.assigned_plan_floor,
        assigned_elevation_facades=args.assigned_facade,
    )
    result = {"conversion": conversion, "scoring": score_scoped_answer(args.reference, conversion)}
    write_json(args.out, result)
    print(json.dumps({
        "case": args.case,
        "assigned_status": result["scoring"]["assigned_role_score"]["status"],
        "complete_status": result["scoring"]["complete_reference_score"]["status"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
