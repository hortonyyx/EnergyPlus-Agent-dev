"""Hash-check and purely replay the three saved sm25 alignment failures."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

from PIL import Image
from shapely.geometry import Polygon


REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from src.agent.correction.config import load_core_tolerances  # noqa: E402
from src.agent.geometry.plan_dimension_alignment import align_plan_to_dimensions  # noqa: E402
from src.agent.geometry.plan_feedback import resolve_plan_lengths  # noqa: E402
from src.agent.geometry.plan_ink_alignment import align_plan_to_ink  # noqa: E402
from src.agent.geometry.plan_input import normalize_plan_fields  # noqa: E402
from src.agent.geometry.profile_observation_binding import resolve_plan_pixels  # noqa: E402


RUN = Path("AI_agent/archive/local_backup/sm25_v53/sm25_role_v53")
DIAGNOSTIC = Path("AI_agent/logs/experiments/2026-10-08_sm25_domain_v53/unknown_write_diagnostic")
F1_TASK = "97f2c471dfd10e769ca8e2baed161258dace8e21a450ccdc0f19143fb238194b"
F2_TASK = "02dcc55f6a0322d1831e6c2c636fab6109aa9cff6ebd002d14174d8610090c96"


def _task_path(task: str, relative: str) -> Path:
    return RUN / "tasks" / task / "bim/trial_workspace" / relative


CASES = {
    "stop_iteration": (
        DIAGNOSTIC / "trial_003_plan.json", DIAGNOSTIC / "1f_view.png",
        "a2ceb00bf82b8dc8470a6c75409cc6ab1e6d30ad399997b32fd06e309cb045d0",
        "6512c86e46a0c9c2623abd4445a53cb8d12b8b4191436420a1b8ba6d94ab9644",
    ),
    "near_junction": (
        _task_path(F1_TASK, "trial_receipts/trial_002_plan.json"),
        _task_path(F1_TASK, "images/1f_view.png"),
        "13c7ffea0f0a2cbd3950e65c32b01df5eb22a0363f35b4557e8cd0c6d7d757b4",
        "6512c86e46a0c9c2623abd4445a53cb8d12b8b4191436420a1b8ba6d94ab9644",
    ),
    "short_step": (
        _task_path(F2_TASK, "trial_receipts/trial_005_plan.json"),
        _task_path(F2_TASK, "images/2f_view.png"),
        "061329a3952d4d32c2e9d198707f9099c430370b2687bf20cdd7f092d79c3ad1",
        "bde78c1276b79d96ebbf6cea7f31cbbbf6d84bae70b5caa85b27331ce609b322",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(main_root: Path, name: str):
    plan_rel, image_rel, plan_sha, image_sha = CASES[name]
    plan_path, image_path = main_root / plan_rel, main_root / image_rel
    assert plan_path.is_file() and image_path.is_file(), f"missing saved input for {name}"
    assert _sha256(plan_path) == plan_sha, f"plan hash changed for {name}"
    assert _sha256(image_path) == image_sha, f"image hash changed for {name}"
    source = {
        "plan_path": plan_rel.as_posix(), "plan_sha256": plan_sha,
        "image_path": image_rel.as_posix(), "image_sha256": image_sha,
    }
    return json.loads(plan_path.read_bytes()), image_path, source


def _align(plan, image_path: Path, image_sha: str):
    original = copy.deepcopy(plan)
    numeric, aliases = normalize_plan_fields(plan)
    numeric, lengths = resolve_plan_lengths(numeric)

    def no_profile(profile_id: str):
        raise AssertionError(f"unexpected measurement profile: {profile_id}")

    numeric, measurements = resolve_plan_pixels(
        numeric, image=image_path.name, image_sha256=image_sha, load_profile=no_profile,
    )
    assert not aliases and not lengths and not measurements
    with Image.open(image_path) as image:
        aligned, ink = align_plan_to_ink(image, numeric)
    aligned, dimensions = align_plan_to_dimensions(aligned)
    assert plan == original, "replay mutated a saved input"
    return aligned, (ink, dimensions)


def _pairs(points):
    return list(zip(points, [*points[1:], points[0]]))


def _orthogonal(first, second) -> bool:
    return math.isclose(first[0], second[0], abs_tol=1e-9) or math.isclose(
        first[1], second[1], abs_tol=1e-9,
    )


def _on_segment(point, first, second) -> bool:
    if math.isclose(first[0], second[0], abs_tol=1e-9):
        return (math.isclose(point[0], first[0], abs_tol=1e-9)
                and min(first[1], second[1]) <= point[1] <= max(first[1], second[1]))
    return (math.isclose(point[1], first[1], abs_tol=1e-9)
            and min(first[0], second[0]) <= point[0] <= max(first[0], second[0]))


def _counts_preserved(before, after) -> bool:
    return all(len(before.get(key, [])) == len(after.get(key, []))
               for key in ("partitions", "openings", "space_seeds"))


def replay(main_root: Path):
    plans = {name: _load(main_root, name) for name in CASES}
    results = {}

    plan, image, source = plans["stop_iteration"]
    aligned, _ = _align(plan, image, source["image_sha256"])
    ring = aligned["footprint_pixels"]
    result = {
        **source, "alignment_completed": True,
        "footprint_valid": Polygon(ring).is_valid,
        "footprint_orthogonal": all(_orthogonal(*pair) for pair in _pairs(ring)),
        "object_counts_preserved": _counts_preserved(plan, aligned),
    }
    assert all(result[key] for key in (
        "alignment_completed", "footprint_valid", "footprint_orthogonal",
        "object_counts_preserved",
    ))
    results["stop_iteration"] = result

    plan, image, source = plans["near_junction"]
    aligned, _ = _align(plan, image, source["image_sha256"])
    walls = {str(row["id"]): row["points"] for row in aligned["partitions"]}
    horizontal, vertical = walls["p_cor_s"], walls["p_rooms_e"]
    result = {
        **source, "junction_on_host": _on_segment(vertical[0], horizontal[0], horizontal[-1]),
        "horizontal_end": horizontal[-1], "vertical_start": vertical[0],
        "partitions_orthogonal": all(
            _orthogonal(first, second) for points in walls.values()
            for first, second in zip(points, points[1:])
        ),
        "object_counts_preserved": _counts_preserved(plan, aligned),
    }
    assert result["junction_on_host"] and result["partitions_orthogonal"]
    assert result["object_counts_preserved"]
    results["near_junction"] = result

    plan, image, source = plans["short_step"]
    aligned, reports = _align(plan, image, source["image_sha256"])
    ring, minimum = aligned["footprint_pixels"], load_core_tolerances().min_edge_length_m
    pairs, x_anchors = _pairs(ring), aligned["x_anchors"]
    lengths = [math.dist(*pair) for pair in pairs]
    x_scale = abs((x_anchors[1][1] - x_anchors[0][1])
                  / (x_anchors[1][0] - x_anchors[0][0]))
    reasons = [row["reason"] for report in reports for row in report.get("rejections", [])
               if "footprint edge 2" in str(row.get("reason", ""))]
    result = {
        **source, "edge_2_length_px": round(lengths[2], 6),
        "edge_2_length_m": round(lengths[2] * x_scale, 9), "minimum_edge_m": minimum,
        "zero_length_edges": sum(length <= 1e-9 for length in lengths),
        "footprint_valid": Polygon(ring).is_valid,
        "footprint_orthogonal": all(_orthogonal(*pair) for pair in pairs),
        "rejection_reasons": reasons,
        "object_counts_preserved": _counts_preserved(plan, aligned),
    }
    assert result["edge_2_length_m"] >= minimum - 1e-9
    assert result["zero_length_edges"] == 0 and result["footprint_valid"]
    assert result["footprint_orthogonal"] and result["object_counts_preserved"]
    assert any("below min_edge_length_m" in reason for reason in reasons)
    results["short_step"] = result

    return {
        "schema_version": "kernel_failure_replay_v1",
        "scope": "saved inputs; deterministic preprocessing only; no model, API, MCP, or BIM write",
        "all_assertions_passed": True,
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, required=True)
    result = replay(parser.parse_args().main_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
