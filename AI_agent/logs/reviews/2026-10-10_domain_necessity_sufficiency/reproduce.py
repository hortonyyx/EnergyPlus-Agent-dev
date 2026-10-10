"""Offline counterexamples for the 2026-10-10 domain review, not product tests.

Run from the repository root with its Python environment. No image files,
network, models, GT or production mutations are involved. Writes only the
adjacent diagnostic JSON when invoked as a script.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from src.agent.geometry.lite_bim_regularization import regularize_lite_plan
from src.agent.geometry.plan_dimension_alignment import align_plan_to_dimensions
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.geometry.plan_regularization import PlanRegularizationError


def reproduce() -> dict:
    base = {
        "floor_id": "F1", "z_floor": 0, "ceiling_height": 3,
        "x_anchors": [[100, 0], [1100, 10]],
        "y_anchors": [[100, 10], [1100, 0]],
        "footprint_pixels": [[100, 100], [1100, 100], [1100, 1100], [100, 1100]],
        "partitions": [], "space_seeds": [], "openings": [],
        "basis": "synthetic 10m square", "assumptions": [], "unresolved": [],
    }
    output = {"reviewed_commit": "b45a9db7565dca304fced570ba06c1927bd44b76"}
    plan = copy.deepcopy(base)
    plan["partitions"] = [{"id": "wall", "points": [[500, 100], [502, 1100]],
                           "source_refs": ["synthetic drawing"]}]
    plan["space_seeds"] = [{"id": "L", "point": [300, 500]}, {"id": "R", "point": [800, 500]}]
    try:
        _, report = regularize_lite_plan(plan, image_size=(1201, 1201))
        output["near_axis"] = {"status": report["status"]}
    except PlanRegularizationError as error:
        output["near_axis"] = {"error": str(error), "rejections": error.report["rejections"]}
    plan["partitions"][0]["points"][1][0] = 500
    _, report = regularize_lite_plan(plan, image_size=(1201, 1201))
    output["exact_axis_control"] = {"status": report["status"], "topology": report["topology"]["status"]}

    plan = copy.deepcopy(base)
    plan["dimension_chains"] = [
        {"id": "outer-a", "axis": "x", "segments_mm": [10000], "tick_pixels": [100, 1100],
         "source_refs": ["synthetic drawing overall a"]},
        {"id": "outer-b", "axis": "x", "segments_mm": [10000], "tick_pixels": [105, 1095],
         "source_refs": ["synthetic drawing overall b"]},
    ]
    adopted, report = align_plan_to_dimensions(plan, grid_step_m=0.1)
    output["agreeing_dimension_chains"] = {
        "rejections": report["rejections"], "adopted_x_anchors": adopted["x_anchors"],
    }

    plan = copy.deepcopy(base)
    plan["partitions"] = [{"id": "core", "points": [[400, 400], [700, 400], [700, 700], [400, 700], [400, 400]],
                           "source_refs": ["synthetic drawing"]}]
    plan["space_seeds"] = [{"id": "core", "point": [500, 500]}, {"id": "office", "point": [250, 250]}]
    try:
        compile_plan_partition(plan, image_size=(1201, 1201), image_name="synthetic")
        output["annular_space"] = {"status": "accepted"}
    except ValueError as error:
        output["annular_space"] = {"error": str(error), "scope": "general capability, not proven sm25 blocker"}
    return output


if __name__ == "__main__":
    result = reproduce()
    destination = Path(__file__).with_name("reproduction.json")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
