"""A selected measurement reaches saved geometry without manual coordinate copying."""
import asyncio
import copy
import json

import pytest
from PIL import Image, ImageDraw

from scripts.tool_scripts.run_bim_agent import Toolkit, digest
from src.agent.geometry.profile_observation_binding import resolve_plan_pixels
from tests.test_bim_agent_plan_partition import example
from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session


def ref(candidate="C01", **extra):
    return dict(profile="profile_001", candidate=candidate, **extra)


def measured_input(tmp_path):
    run = _run_with_one_image(tmp_path)
    picture = Image.new("RGB", (12, 8), "black")
    draw = ImageDraw.Draw(picture)
    for x in (5, 7):
        draw.line((x, 0, x, 7), fill=(128, 128, 128))
    picture.save(run / "images/plan.png")
    manifest = json.loads((run / "inputs.json").read_text())
    manifest["images"]["plan.png"]["sha256"] = digest(run / "images/plan.png")
    (run / "inputs.json").write_text(json.dumps(manifest))
    return run


def selected_plan():
    plan = example()
    mid = {"midpoint": [ref(), ref("C02")]}
    for point in plan["partitions"][0]["points"]:
        point[0] = mid
    for field in ("p1", "p2"):
        plan["openings"][0][field][0] = mid
    return plan


def test_pixel_slots_resolve_but_world_values_and_input_remain_unchanged():
    profile = dict(record=dict(name="plan.png", image_sha256="image-hash", axis="x",
        candidates=[dict(id="C01", pixels=[5, 5], peak=5),
                    dict(id="C02", pixels=[7, 7], peak=7)]), sha256="profile-hash")
    plan = selected_plan()
    plan["x_anchors"][0][0] = ref()
    plan["footprint_pixels"][0][0] = ref("C02", at="end")
    plan["space_seeds"][0]["point"][0] = ref()
    original = copy.deepcopy(plan)
    loaded = []

    def load(identity):
        loaded.append(identity)
        return profile

    result, bindings = resolve_plan_pixels(plan, image="plan.png", image_sha256="image-hash", load_profile=load)
    assert plan == original and loaded == ["profile_001"]
    assert result["partitions"][0]["points"] == [[6, 1], [6, 7]]
    assert result["openings"][0]["p1"] == [6, 3]
    assert result["openings"][0]["z"] == example()["openings"][0]["z"]
    assert result["x_anchors"][0] == [5, 0]
    assert result["y_anchors"] == example()["y_anchors"]
    assert result["footprint_pixels"][0] == [7, 1]
    assert result["space_seeds"][0]["point"] == [5, 4]
    assert len(bindings) == 7
    assert all(b["image_sha256"] == "image-hash" for b in bindings)
    result, bindings = resolve_plan_pixels(example(), image="plan.png", image_sha256="image-hash",
                                          load_profile=lambda _: pytest.fail("numeric plans need no profiles"))
    assert result == example() and not bindings


@pytest.mark.parametrize("problem", ["wrong_image", "wrong_axis", "changed_image", "unknown_candidate", "bad_midpoint"])
def test_invalid_measurements_preserve_submitted_draft_without_geometry(tmp_path, problem):
    run = measured_input(tmp_path)
    toolkit = Toolkit(run)
    toolkit.view_profile("plan.png", [0, 0, 12, 8], "x", [128]*3, 0, 0.5)
    path = run / "pixel_profiles/profile_001.json"
    record = json.loads(path.read_text())
    plan = selected_plan()
    if problem == "wrong_image":
        record["name"] = "other.png"
    elif problem == "wrong_axis":
        record["axis"] = "y"
    elif problem == "changed_image":
        record["image_sha256"] = "obsolete"
    elif problem == "unknown_candidate":
        plan["partitions"][0]["points"][0][0] = ref("missing")
    else:
        plan["partitions"][0]["points"][0][0] = {"midpoint": [ref(), 7]}
    path.write_text(json.dumps(record))
    raw = json.dumps(plan, indent=2)
    result = toolkit.build_plan("plan.png", raw)
    assert result["error_stage"] == "measurement_binding"
    assert not result["source_geometry_ready"]
    assert (run / result["plan_input"]["plan_file"]).read_text() == raw
    assert not list(run.glob("candidate_*"))


def test_mcp_measured_wall_door_revision_and_assembly_keep_numeric_drafts(tmp_path):
    async def scenario():
        run = measured_input(tmp_path)
        original_hash = digest(run / "images/plan.png")
        async with _server_session(run, readonly=False) as session:
            response = await session.call_tool("view_pixel_profile", dict(name="plan.png",
                box=[0, 0, 12, 8], axis="x", rgb=[128]*3, tolerance=0, min_fraction=0.5))
            assert not response.isError
            profile = json.loads(response.content[1].text)
            assert [c["peak"] for c in profile["candidates"]] == [5, 7]
            raw = json.dumps(selected_plan(), indent=2) + "\n"
            result = _json_result(await session.call_tool("build_plan_bim", dict(image="plan.png", plan_json=raw)))
            assert result["source_geometry_ready"]
            record = result["plan_input"]
            assert (run / record["submitted_plan_file"]).read_text() == raw
            assert digest(run / record["submitted_plan_file"]) == record["submitted_plan_sha256"]
            assert json.loads((run / record["plan_file"]).read_text()) == example()
            saved = _json_result(await session.call_tool("inspect_plan_draft", dict(draft_id="draft_001")))
            assert saved["declaration"] == example()
            audit = record["measurement_bindings"]
            assert digest(run / audit["file"]) == audit["sha256"] and audit["count"] == 4
            assert {b["resolved_pixel"] for b in json.loads((run / audit["file"]).read_text())["bindings"]} == {6}
            source = json.loads((run / result["candidate"] / "source_model.json").read_text())
            assert len(source["spaces"]) == 2 and len(source["connections"]) == 1
            door = next(o for o in source["openings"] if o["id"] == "D1")
            assert {p[0] for p in door["vertices"]} == {3}
            # A profile-backed local edit goes through the same path and keeps W1.
            changed = _json_result(await session.call_tool("revise_plan_bim", dict(draft_id="draft_001",
                expected_plan_sha256=saved["plan_sha256"], operations_json=json.dumps([dict(
                    op="update", collection="openings", id="D1",
                    changes={"p1": [{"midpoint": [ref(), ref("C02")]}, 3], "z": [0, 2.2]},
                    reason="synthetic local correction", source_refs=["synthetic measured plane"])]))))
            assert changed["source_geometry_ready"]
            assert changed["plan_revision"]["unchanged_ids"]["openings"] == ["W1"]
            second = _json_result(await session.call_tool("inspect_plan_draft", dict(draft_id="draft_002")))
            assert second["declaration"]["openings"][0]["p1"] == [6, 3]
            floors = [dict(draft_id=draft, expected_plan_sha256=saved_plan["plan_sha256"],
                           floor_id=floor, z_floor=z, evidence="synthetic assembly")
                      for draft, saved_plan, floor, z in [("draft_001", saved, "F1", 0), ("draft_002", second, "F2", 3)]]
            assembled = _json_result(await session.call_tool("assemble_plan_bim", dict(floors_json=json.dumps(floors))))
            assert assembled["source_geometry_ready"]
            merged = json.loads((run / assembled["candidate"] / "source_model.json").read_text())
            assert len(merged["floors"]) == 2 and len(merged["spaces"]) == 4
            assert len(merged["openings"]) == 4 and len(merged["connections"]) == 2
            assert digest(run / "images/plan.png") == original_hash
    asyncio.run(scenario())
