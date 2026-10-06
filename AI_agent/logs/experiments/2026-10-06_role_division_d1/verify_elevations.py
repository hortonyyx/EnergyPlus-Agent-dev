"""Offline evidence for D1 elevation artifact validation and ordered matching.

No model or network service is called.  sm24 replays the retained four-facade
reference readings, including their original-image pixel boxes and independent
horizontal calibration.  sm21/sm25 remain accepted-source self-consistency
checks and are labelled accordingly.
"""

from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from src.agent.runtime_roles.elevation import (
    _boundary_orientation,
    _source_rows,
    match_elevation,
    validate_elevation_artifact,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CASES = {
    "sm21": ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm21",
    "sm24": ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm24",
    "sm25": ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm25",
}
OUT = HERE / "elevation_verification.json"
SM24_FACADE_REFERENCES = (
    ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_references.json"
)
SM24_OBSERVATIONS = (
    ROOT
    / "AI_agent/logs/experiments/2026-09-16_sm24_developer_reconstruction/elevation_observations.json"
)
VIEW_DIRECTION = {
    "North": "South",
    "South": "North",
    "East": "West",
    "West": "East",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def facade_extent(source, orientation):
    axis = 0 if orientation in {"North", "South"} else 1
    values = []
    for boundary in source["boundaries"]:
        if boundary.get("geometry_type") != "wall":
            continue
        try:
            facade = _boundary_orientation(boundary)
        except ValueError:
            continue
        if facade == orientation:
            values.extend(vertex[axis] for vertex in boundary["vertices"])
    if not values:
        raise ValueError(f"no exterior extent for {orientation}")
    return min(values), max(values)


def claim_references(case_root):
    references = {}
    for path in sorted((case_root / "claims").glob("claim_*.json")):
        claim = load_json(path)
        if "height" not in claim.get("resolved_values", {}):
            continue
        source = claim.get("sources", [{}])[0]
        for obj in claim["claim"].get("objects", []):
            references[obj["id"]] = {
                "height": claim["resolved_values"]["height"],
                "image": source.get("image"),
                "source_bbox": source.get("box"),
                "basis": claim["claim"].get("basis"),
                "claim_id": claim["id"],
            }
    return references


def image_size(case_root, image_name):
    with Image.open(case_root / "images" / image_name) as image:
        return image.size


def source_artifact(case_name, case_root, source, orientation, references):
    if case_name == "sm24":
        return sm24_reference_artifact(source, orientation)
    rows, source_conflicts = _source_rows(source, orientation)
    if source_conflicts:
        raise ValueError(f"{case_name} {orientation}: source conflicts {source_conflicts}")
    image_name = f"{orientation}_view.png"
    width_px, height_px = image_size(case_root, image_name)
    world_min, world_max = facade_extent(source, orientation)
    direction = VIEW_DIRECTION[orientation]
    # Outside-view convention: looking North/West makes the corresponding
    # fixed world axis increase from image left to right.
    increases = direction in {"North", "West"}
    world_start, world_end = (
        (world_min, world_max) if increases else (world_max, world_min)
    )

    def world_to_pixel(value):
        return (value - world_start) / (world_end - world_start) * width_px

    z_by_floor = {}
    for space in source["spaces"]:
        z_by_floor.setdefault(space["floor_id"], float(space["z_floor"]))
    openings = []
    expected = {}
    for row in sorted(
        rows,
        key=lambda item: (
            z_by_floor[item["floor_id"]],
            world_to_pixel(item["world_coordinate_m"]),
            item["kind"],
            item["source_id"],
        ),
    ):
        center = world_to_pixel(row["world_coordinate_m"])
        pixels_per_m = abs(width_px / (world_end - world_start))
        half = row["width_m"] * pixels_per_m / 2
        x_px = sorted([center - half, center + half])
        reference = references.get(row["source_id"])
        height = row["absolute_z_m"]
        evidence_type = "declared"
        if case_name == "sm24" and reference is not None:
            height = reference["height"]
            evidence_type = (
                "annotation_and_pixels"
                if reference["basis"] == "annotation_and_pixels"
                else "pixels"
            )
        # The x interval is projected into the actual original image coordinate
        # system.  Full image height is retained because old claims located the
        # dimension chain, not a per-opening vertical crop.
        bbox = [
            max(0.0, x_px[0] - 2.0),
            0.0,
            min(float(width_px), x_px[1] + 2.0),
            float(height_px),
        ]
        artifact_id = f"reference:{row['source_id']}"
        openings.append(
            {
                "id": artifact_id,
                "floor_id": row["floor_id"],
                "kind": row["kind"],
                "x_px": x_px,
                "width_m": row["width_m"],
                "sill_m": height[0],
                "head_m": height[1],
                "evidence_type": evidence_type,
                "bbox": bbox,
            }
        )
        expected[artifact_id] = row["source_id"]

    floor_counts = defaultdict(Counter)
    for row in openings:
        floor_counts[row["floor_id"]][row["kind"]] += 1
    levels = [
        {
            "id": f"floor:{floor_id}",
            "floor_id": floor_id,
            "kind": "floor",
            "value_m": z,
            "evidence_type": "declared",
            "bbox": [0, max(0, height_px - 2), width_px, height_px],
        }
        for floor_id, z in sorted(z_by_floor.items(), key=lambda item: item[1])
    ]
    top = max(
        float(space["z_floor"]) + float(space["height"])
        for space in source["spaces"]
    )
    levels.append(
        {
            "id": "roof:top",
            "kind": "roof",
            "value_m": top,
            "evidence_type": "declared",
            "bbox": [0, 0, width_px, 2],
        }
    )
    artifact = {
        "artifact_id": f"{case_name}:{orientation}",
        "image": image_name,
        "orientation": orientation,
        "view_direction": direction,
        "x_calibration": {
            "pixel_start": 0,
            "pixel_end": width_px,
            "world_start_m": world_start,
            "world_end_m": world_end,
        },
        "elevations": levels,
        "openings": openings,
        "counts": [
            {
                "floor_id": floor_id,
                "window_count": counts["window"],
                "door_count": counts["door"],
            }
            for floor_id, counts in sorted(
                floor_counts.items(), key=lambda item: z_by_floor[item[0]]
            )
        ],
        "unresolved": [],
    }
    return artifact, expected


SM24_EXPECTED_IDS = {
    "north": {"N1": "W_N", "north_external_door": "D_N"},
    "south": {"S1": "W_S1", "south_external_door": "D_S", "S2": "W_S2"},
    "east": {
        "east_external_door": "D_E",
        "E3": "W_E3",
        "E2": "W_E2",
        "E1": "W_E1",
    },
    "west": {f"W{number}": f"W_W{number}" for number in range(1, 6)},
}


def sm24_reference_artifact(source, orientation):
    """Build an artifact from retained original-image reference readings."""

    facade_name = orientation.lower()
    observations = load_json(SM24_OBSERVATIONS)["facades"][facade_name]
    facade_cases = {
        row["facade"]: row for row in load_json(SM24_FACADE_REFERENCES)["cases"]
    }
    window_reference = facade_cases[facade_name]
    observed_windows = [
        row
        for row in observations["openings_screen_left_to_right"]
        if row["kind"] == "window"
    ]
    if len(observed_windows) != len(window_reference["expected_windows"]):
        raise ValueError(f"sm24 {orientation}: retained window references disagree")

    image_width, image_height = observations["image_size_px"]
    wall = observations["wall_reference_px"]
    world_min, world_max = facade_extent(source, orientation)
    direction = VIEW_DIRECTION[orientation]
    increases = direction in {"North", "West"}
    world_start, world_end = (
        (world_min, world_max) if increases else (world_max, world_min)
    )

    reference_by_id = {}
    for observed, reference in zip(
        observed_windows, window_reference["expected_windows"], strict=True
    ):
        reference_by_id[observed["id"]] = {
            "bbox": reference["expected_bbox_px"],
            "width_m": reference["width_mm"] / 1000.0,
            "sill_m": reference["sill_m"],
            "head_m": reference["head_m"],
        }

    openings = []
    expected = {}
    for observed in observations["openings_screen_left_to_right"]:
        if observed["kind"] == "window":
            retained = reference_by_id[observed["id"]]
        else:
            retained = {
                "bbox": observed["cyan_bbox_px"],
                "width_m": observed["width_mm"] / 1000.0,
                "sill_m": observed["bottom_z_mm"] / 1000.0,
                "head_m": observed["top_z_mm"] / 1000.0,
            }
        bbox = [float(value) for value in retained["bbox"]]
        artifact_id = f"reference:{observed['id']}"
        openings.append(
            {
                "id": artifact_id,
                "floor_id": "F1",
                "kind": "door" if observed["kind"] == "external_door" else "window",
                "x_px": [bbox[0], bbox[2]],
                "width_m": retained["width_m"],
                "sill_m": retained["sill_m"],
                "head_m": retained["head_m"],
                "evidence_type": "annotation_and_pixels",
                "bbox": bbox,
            }
        )
        expected[artifact_id] = SM24_EXPECTED_IDS[facade_name][observed["id"]]

    counts = Counter(row["kind"] for row in openings)
    artifact = {
        "artifact_id": f"sm24:{orientation}:retained-reference",
        "image": Path(observations["image"]).name,
        "orientation": orientation,
        "view_direction": direction,
        "x_calibration": {
            "pixel_start": wall["left"],
            "pixel_end": wall["right"],
            "world_start_m": world_start,
            "world_end_m": world_end,
        },
        "elevations": [
            {
                "id": "floor:F1",
                "floor_id": "F1",
                "kind": "floor",
                "value_m": 0.0,
                "evidence_type": "annotation",
                "bbox": [wall["left"], wall["bottom"] - 2, wall["right"], wall["bottom"]],
            },
            {
                "id": "roof:top",
                "kind": "roof",
                "value_m": 4.5,
                "evidence_type": "annotation",
                "bbox": [wall["left"], wall["top"], wall["right"], wall["top"] + 2],
            },
        ],
        "openings": openings,
        "counts": [
            {
                "floor_id": "F1",
                "window_count": counts["window"],
                "door_count": counts["door"],
            }
        ],
        "unresolved": [],
    }
    if max(max(row["bbox"][0], row["bbox"][2]) for row in openings) > image_width:
        raise ValueError(f"sm24 {orientation}: bbox exceeds original image width")
    if max(max(row["bbox"][1], row["bbox"][3]) for row in openings) > image_height:
        raise ValueError(f"sm24 {orientation}: bbox exceeds original image height")
    return artifact, expected


def verify_case(case_name, case_root):
    selected = load_json(case_root / "delivery_selection.json")["candidate"]
    source_path = case_root / selected / "source_model.json"
    source = load_json(source_path)
    references = claim_references(case_root)
    facades = []
    correct = total = 0
    for orientation in ("North", "South", "East", "West"):
        rows, _ = _source_rows(source, orientation)
        if not rows:
            continue
        artifact, expected = source_artifact(
            case_name, case_root, source, orientation, references
        )
        report = match_elevation(source, artifact, candidate=selected)
        pairs = {
            row["artifact_opening_id"]: row["source_opening_id"]
            for row in report["matches"]
        }
        facade_correct = sum(pairs.get(key) == value for key, value in expected.items())
        facade_total = len(expected)
        correct += facade_correct
        total += facade_total
        facades.append(
            {
                "orientation": orientation,
                "view_direction": artifact["view_direction"],
                "world_axis": validate_elevation_artifact(artifact)["x_calibration"]["world_axis"],
                "opening_count": facade_total,
                "correct_matches": facade_correct,
                "accuracy": facade_correct / facade_total if facade_total else None,
                "elevation_only": len(report["elevation_only"]),
                "source_only": len(report["source_only"]),
                "conflicts": len(report["conflicts"]),
                "match_id": report["match_id"],
            }
        )
    return {
        "case": case_name,
        "candidate": selected,
        "source_model": source_path.relative_to(ROOT).as_posix(),
        "source_model_sha256": source["source_model_sha256"],
        "reference_mode": (
            "retained_four_facade_original_pixel_references_with_independent_horizontal_calibration"
            if case_name == "sm24"
            else "accepted_source_bim_self_consistency_projection"
        ),
        "independent_image_reading_accuracy": case_name == "sm24",
        "facades": facades,
        "correct_matches": correct,
        "expected_matches": total,
        "alignment_accuracy": correct / total if total else None,
    }


def synthetic_fixture():
    source = {
        "source_model_sha256": "f" * 64,
        "spaces": [{"id": "room", "floor_id": "F1"}],
        "boundaries": [
            {
                "id": "north",
                "geometry_type": "wall",
                "vertices": [[10, 10, 0], [0, 10, 0], [0, 10, 3], [10, 10, 3]],
            }
        ],
        "openings": [],
    }

    def opening(identity, kind, start, end, z):
        source["openings"].append(
            {
                "id": identity,
                "kind": kind,
                "exterior": True,
                "host_boundary_id": "north",
                "space_ids": ["room"],
                "vertices": [
                    [start, 10, z[0]],
                    [end, 10, z[0]],
                    [end, 10, z[1]],
                    [start, 10, z[1]],
                ],
            }
        )

    opening("W1", "window", 1, 2, [1, 2.2])
    opening("W2", "window", 2.08, 3.08, [1, 2.2])
    opening("D1", "door", 6, 7, [0, 2.1])
    artifact = {
        "image": "synthetic.png",
        "orientation": "North",
        "view_direction": "South",
        "x_calibration": {
            "pixel_start": 0,
            "pixel_end": 1000,
            "world_start_m": 10,
            "world_end_m": 0,
        },
        "elevations": [
            {
                "id": "ground",
                "kind": "ground",
                "value_m": 0,
                "evidence_type": "pixels",
                "bbox": [0, 900, 100, 950],
            }
        ],
        "openings": [
            {
                "id": "read-D1",
                "floor_id": "F1",
                "kind": "door",
                "x_px": [300, 400],
                "width_m": 1,
                "sill_m": 0,
                "head_m": 2.1,
                "evidence_type": "annotation",
                "bbox": [295, 100, 405, 900],
            },
            {
                "id": "read-W2",
                "floor_id": "F1",
                "kind": "window",
                "x_px": [692, 792],
                "width_m": 1,
                "sill_m": 1,
                "head_m": 2.2,
                "evidence_type": "pixels",
                "bbox": [687, 200, 797, 700],
            },
            {
                "id": "read-W1",
                "floor_id": "F1",
                "kind": "window",
                "x_px": [800, 900],
                "width_m": 1,
                "sill_m": 1,
                "head_m": 2.2,
                "evidence_type": "pixels",
                "bbox": [795, 200, 905, 700],
            },
        ],
        "counts": [{"floor_id": "F1", "window_count": 2, "door_count": 1}],
        "unresolved": [],
    }
    return source, artifact


def counterexamples():
    source, base = synthetic_fixture()
    results = []

    tight = match_elevation(source, base)
    results.append(
        {
            "name": "two_tight_windows_and_exterior_door",
            "passed": len(tight["matches"]) == 3 and not tight["conflicts"],
            "matched_ids": [row["source_opening_id"] for row in tight["matches"]],
        }
    )

    missing = copy.deepcopy(base)
    missing["openings"].pop(1)
    missing["counts"][0]["window_count"] = 1
    report = match_elevation(source, missing)
    results.append(
        {
            "name": "one_opening_missing",
            "passed": [row["source_id"] for row in report["source_only"]] == ["W2"],
            "source_only": [row["source_id"] for row in report["source_only"]],
        }
    )

    extra = copy.deepcopy(base)
    duplicate = copy.deepcopy(extra["openings"][1])
    duplicate.update(
        id="read-extra", x_px=[500, 550], width_m=0.5, bbox=[495, 200, 555, 700]
    )
    extra["openings"].insert(1, duplicate)
    extra["counts"][0]["window_count"] = 3
    report = match_elevation(source, extra)
    results.append(
        {
            "name": "one_opening_extra",
            "passed": [row["artifact_opening_id"] for row in report["elevation_only"]]
            == ["read-extra"],
            "elevation_only": [
                row["artifact_opening_id"] for row in report["elevation_only"]
            ],
        }
    )

    shifted = copy.deepcopy(base)
    for row in shifted["openings"]:
        row["x_px"] = [value + 100 for value in row["x_px"]]
        row["bbox"] = [
            row["bbox"][0] + 100,
            row["bbox"][1],
            row["bbox"][2] + 100,
            row["bbox"][3],
        ]
    report = match_elevation(source, shifted)
    shift_conflicts = [
        row for row in report["conflicts"] if row.get("type") == "position_or_width_conflict"
    ]
    results.append(
        {
            "name": "whole_elevation_shifted",
            "passed": len(shift_conflicts) == 3 and not report["matches"],
            "conflict_count": len(shift_conflicts),
        }
    )

    reversed_artifact = copy.deepcopy(base)
    reversed_artifact["x_calibration"].update(world_start_m=0, world_end_m=10)
    try:
        validate_elevation_artifact(reversed_artifact)
        reversal = {"name": "left_right_reversed", "passed": False, "error": None}
    except ValueError as error:
        reversal = {
            "name": "left_right_reversed",
            "passed": "contradicts view_direction" in str(error),
            "error": str(error),
        }
    results.append(reversal)
    return results


def main():
    cases = [verify_case(name, path) for name, path in CASES.items()]
    counters = counterexamples()
    total_correct = sum(case["correct_matches"] for case in cases)
    total_expected = sum(case["expected_matches"] for case in cases)
    payload = {
        "schema_version": "d1_elevation_verification_v1",
        "method": {
            "offline_only": True,
            "model_or_api_calls": 0,
            "coordinate_contract": (
                "North/South use fixed world X; East/West use fixed world Y; "
                "view_direction fixes image left-to-right sign; sill/head are absolute building Z."
            ),
            "matching": (
                "ordered by floor and kind, then checked against position and width tolerances; "
                "one-sided and conflicting rows are never emitted as safe height applications."
            ),
            "position_tolerance_m": 0.35,
            "width_tolerance_m": 0.25,
        },
        "cases": cases,
        "overall": {
            "correct_matches": total_correct,
            "expected_matches": total_expected,
            "alignment_accuracy": total_correct / total_expected,
        },
        "counterexamples": counters,
        "counterexamples_passed": all(row["passed"] for row in counters),
        "limitations": [
            "sm21 and sm25 are accepted-source self-consistency checks, not independent image-reading accuracy.",
            "sm24 replays retained developer-read four-facade references from original pixels; it evaluates matching independently of accepted-source horizontal projections, not fresh working-model image-reading quality.",
            "The matcher supports cardinal, axis-aligned exterior source boundaries in this D1 base version.",
            "The script prepares claim_transaction parameters but does not mutate any historical candidate.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["overall"], ensure_ascii=False))
    print(f"counterexamples_passed={payload['counterexamples_passed']}")
    print(OUT)


if __name__ == "__main__":
    main()
