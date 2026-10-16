"""2D reading compilation keeps unknown heights unknown without weakening XY checks."""
from __future__ import annotations

import copy

import pytest

from src.agent.geometry.lite_bim_regularization import compiled_grid_report, regularize_lite_plan
from src.agent.geometry.plan_partition import OpeningHostError, compile_plan_partition
from src.agent.geometry.plan_regularization import PlanRegularizationError, regularize_plan


SIZE = (1501, 1001)


def reading() -> dict:
    return {
        "reading_type": "plan", "floor_id": "F1",
        "x_anchors": [[100, 0], [1300, 12]], "y_anchors": [[100, 8], [900, 0]],
        "footprint_pixels": [[100, 100], [1300, 100], [1300, 900], [100, 900]],
        "partitions": [{"id": "P", "points": [[494, 100], [494, 900]],
                        "source_refs": ["drawing:partition"]}],
        "space_seeds": [{"id": "L", "point": [200, 300]},
                        {"id": "R", "point": [1000, 300]}],
        "openings": [{"id": "D", "kind": "door", "p1": [494, 420], "p2": [494, 514],
                      "source_refs": ["drawing:door"]},
                     {"id": "W", "kind": "window", "p1": [950, 100], "p2": [1094, 100],
                      "source_refs": ["drawing:window"]}],
        "basis": "synthetic calibrated plan; no height observations",
        "assumptions": [], "unresolved": ["Opening heights require elevation evidence."],
    }


def compile_reading(plan):
    return compile_plan_partition(plan, image_size=SIZE, image_name="plan.png")


def assert_no_heights(plan, proposal, metadata):
    assert "z_floor" not in plan and "ceiling_height" not in plan
    floor = proposal["geometry"]["floors"][0]
    assert "z_floor" not in floor and "ceiling_height" not in floor
    assert all("z" not in row for row in plan["openings"])
    assert all("z" not in row for collection in ("openings", "windows")
               for row in proposal["geometry"][collection])
    assert all("z_absolute_m" not in row for row in metadata["opening_hosts"])


def test_2d_compilation_preserves_legacy_xy_and_hosts_without_inventing_height():
    plan = reading()
    before = copy.deepcopy(plan)
    proposal, metadata = compile_reading(plan)
    assert_no_heights(plan, proposal, metadata)
    assert proposal["geometry"]["reading_type"] == metadata["reading_type"] == "plan"
    hosts = {row["opening_id"]: row["space_ids"] for row in metadata["opening_hosts"]}
    assert hosts == {"D": ["L", "R"], "W": ["R"]}
    legacy = copy.deepcopy(plan)
    legacy.pop("reading_type")
    legacy.update(z_floor=0, ceiling_height=3.2)
    for opening in legacy["openings"]:
        opening["z"] = [0, 2.1] if opening["kind"] == "door" else [0.9, 2.4]
    legacy_proposal, _ = compile_reading(legacy)
    geometry = legacy_proposal["geometry"]
    geometry["floors"][0].pop("z_floor")
    geometry["floors"][0].pop("ceiling_height")
    for opening in [*geometry["openings"], *geometry["windows"]]:
        opening.pop("z")
    geometry["reading_type"] = "plan"
    assert legacy_proposal == proposal
    assert plan == before


def test_2d_grid_keeps_original_observations_and_is_idempotent():
    plan = reading()
    before = copy.deepcopy(plan)
    adopted, report = regularize_lite_plan(plan, image_size=SIZE)
    proposal, metadata = compile_reading(adopted)
    assert_no_heights(adopted, proposal, metadata)
    assert adopted["partitions"][0]["points"][0][0] == 490
    assert adopted["openings"][0]["p1"][0] == 490
    assert report["topology"]["before"] == report["topology"]["after"]
    assert report["topology"]["before"]["opening_count"] == 2
    assert report["topology"]["before"]["space_count"] == 2
    item = next(row for row in report["items"] if row["path"] == "partitions:P.points[0].x")
    assert item["original_m"] == pytest.approx(3.94)
    assert item["adopted_m"] == 3.9
    assert not any(".z[" in row["path"] or row["path"] in {"z_floor", "z_top", "ceiling_height"}
                   for row in report["items"])
    assert compiled_grid_report(proposal)["status"] == "pass"
    again, second_report = regularize_lite_plan(adopted, image_size=SIZE)
    assert again == adopted and second_report == report
    final, final_report = regularize_plan(adopted, image_size=SIZE, image_name="plan.png")
    assert_no_heights(final, *compile_reading(final))
    assert final_report["lite_bim"]["compiled_grid"]["status"] == "pass"
    assert plan == before


@pytest.mark.parametrize("known", [
    {"z_floor": 0.02}, {"ceiling_height": 3.94},
    {"z_floor": 0.02, "ceiling_height": 3.94},
])
def test_2d_optional_known_floor_heights_are_checked_and_quantized_without_filling_other_fields(known):
    plan = reading()
    plan.update(known)
    adopted, report = regularize_lite_plan(plan, image_size=SIZE)
    proposal, _ = compile_reading(adopted)
    floor = proposal["geometry"]["floors"][0]
    for field in ("z_floor", "ceiling_height"):
        assert (field in floor) == (field in known)
        assert (field in adopted) == (field in known)
    assert compiled_grid_report(proposal)["status"] == "pass"
    assert all("z" not in row for row in adopted["openings"])
    assert report["topology"]["status"] == "preserved"


def test_2d_optional_known_opening_height_stays_local_to_that_opening():
    plan = reading()
    plan["openings"][1]["z"] = [0.94, 2.64]
    adopted, _ = regularize_lite_plan(plan, image_size=SIZE)
    proposal, metadata = compile_reading(adopted)
    assert "z" not in adopted["openings"][0]
    assert "z_floor" not in adopted and "ceiling_height" not in adopted
    assert proposal["geometry"]["windows"][0]["z"] == [0.9, 2.6]
    hosts = {row["opening_id"]: row for row in metadata["opening_hosts"]}
    assert "z_absolute_m" not in hosts["D"]
    assert hosts["W"]["z_absolute_m"] == [0.9, 2.6]


@pytest.mark.parametrize("field,value", [("z_floor", None), ("z_floor", True),
                                         ("ceiling_height", 0), ("ceiling_height", float("inf"))])
def test_2d_supplied_invalid_floor_height_is_not_treated_as_unknown(field, value):
    plan = reading()
    plan[field] = value
    with pytest.raises((ValueError, TypeError), match=field):
        compile_reading(plan)


@pytest.mark.parametrize("interval", [None, [2, 1], [0, float("nan")]])
def test_2d_supplied_invalid_opening_height_is_rejected(interval):
    plan = reading()
    plan["openings"][0]["z"] = interval
    with pytest.raises((ValueError, TypeError), match="opening D.z"):
        compile_reading(plan)


def test_2d_known_vertical_bounds_still_reject_conflicting_opening_observations():
    plan = reading()
    plan.update(z_floor=0, ceiling_height=3)
    plan["openings"][1]["z"] = [1, 3.1]
    with pytest.raises(ValueError, match="outside floor vertical bounds"):
        compile_reading(plan)
    plan.pop("ceiling_height")
    plan["openings"][1]["z"] = [-0.1, 2]
    with pytest.raises(ValueError, match="outside floor vertical bounds"):
        compile_reading(plan)


def test_legacy_without_reading_type_still_requires_all_heights():
    plan = reading()
    plan.pop("reading_type")
    with pytest.raises(ValueError, match="missing ceiling_height, z_floor"):
        compile_reading(plan)
    plan.update(z_floor=0, ceiling_height=3)
    with pytest.raises(ValueError, match="missing z"):
        compile_reading(plan)


def test_2d_wall_metadata_is_inert_deep_copied_and_does_not_move_geometry():
    plan = reading()
    expected, _ = compile_reading(plan)
    plan["wall_metadata"] = [{"wall_id": "P", "thickness_m": 0.24,
                              "source_refs": ["drawing:wall-thickness"]}]
    before = copy.deepcopy(plan)
    actual, metadata = compile_reading(plan)
    assert actual == expected
    assert metadata["wall_metadata"] == plan["wall_metadata"]
    metadata["wall_metadata"][0]["thickness_m"] = 0.9
    assert plan == before


def test_2d_does_not_weaken_literal_topology_or_full_opening_host_checks():
    dangling = reading()
    dangling["partitions"][0]["points"][-1][1] = 700
    with pytest.raises(ValueError, match="polygonize produced"):
        compile_reading(dangling)
    unsupported = reading()
    unsupported["openings"][0]["p1"][0] += 100
    unsupported["openings"][0]["p2"][0] += 100
    with pytest.raises(OpeningHostError, match="requires one exterior or two interior"):
        compile_reading(unsupported)


def test_2d_grid_still_rejects_narrow_room_without_deleting_it():
    plan = reading()
    plan["partitions"].append({"id": "P2", "points": [[534, 100], [534, 900]],
                               "source_refs": ["drawing:second-wall"]})
    plan["space_seeds"].append({"id": "narrow", "point": [510, 300]})
    before = copy.deepcopy(plan)
    with pytest.raises(PlanRegularizationError, match="hard constraint"):
        regularize_lite_plan(plan, image_size=SIZE)
    assert plan == before


def test_2d_missing_sources_bind_only_to_declared_image_and_object_without_mutating_input():
    plan = reading()
    for row in [*plan["partitions"], *plan["openings"]]:
        row.pop("source_refs")
    before = copy.deepcopy(plan)
    proposal, metadata = compile_reading(plan)
    assert metadata["partition_mapping"][0]["source_refs"] == ["image:plan.png#P"]
    assert proposal["geometry"]["windows"][0]["source_refs"] == ["image:plan.png#W"]
    assert proposal["geometry"]["openings"][0]["source_refs"] == ["image:plan.png#D"]
    assert metadata["calibration"]["status"] == "caller_supplied_not_independently_verified"
    adopted, _ = regularize_lite_plan(plan, image_size=SIZE, image_name="plan.png")
    compiled, compiled_metadata = compile_reading(adopted)
    assert compiled_metadata["partition_mapping"][0]["source_refs"] == ["image:plan.png#P"]
    assert compiled["geometry"]["openings"][0]["source_refs"] == ["image:plan.png#D"]
    assert plan == before


@pytest.mark.parametrize("collection", ["partitions", "openings"])
def test_2d_explicit_invalid_sources_are_not_replaced_with_defaults(collection):
    plan = reading()
    plan[collection][0]["source_refs"] = []
    with pytest.raises(TypeError, match="source_refs must be a list of strings with at least one item"):
        compile_reading(plan)
    with pytest.raises(TypeError, match="source_refs must be a list of strings with at least one item"):
        regularize_lite_plan(plan, image_size=SIZE)


def test_legacy_still_requires_explicit_sources():
    plan = reading()
    plan.pop("reading_type")
    plan.update(z_floor=0, ceiling_height=3)
    for row in plan["openings"]:
        row["z"] = [0, 2.1]
    plan["partitions"][0].pop("source_refs")
    with pytest.raises(ValueError, match="missing source_refs"):
        compile_reading(plan)
