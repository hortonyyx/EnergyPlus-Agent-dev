import asyncio
import json

import pytest

from src.agent.runtime_roles.readers import ReaderTools, validate_plan_artifact


def plan():
    return {
        "floor_id": "F1", "z_floor": 0, "ceiling_height": 3,
        "x_anchors": [[10, 0], [110, 10]], "y_anchors": [[10, 10], [110, 0]],
        "basis": "observed dimension anchors", "footprint_pixels": [[10, 10], [110, 10], [110, 110], [10, 110]],
        "partitions": [{"id": "P1", "points": [[60, 10], [60, 110]], "source_refs": ["plan.png: wall"]}],
        "openings": [{"id": "W1", "kind": "window", "p1": [10, 30], "p2": [10, 40],
                      "z": [1, 2.4], "source_refs": ["plan.png: window; heights assumed"]}],
        "space_seeds": [{"id": "left", "point": [30, 50]}],
        "assumptions": ["window height assumed"], "unresolved": ["verify sill from elevation"],
    }


def artifact():
    return {"plan": plan(), "evidence": [
        {"item": "plan.x_anchors", "source": "plan.png", "bbox": [5, 5, 115, 15]},
        {"item": "plan.y_anchors", "source": "plan.png", "bbox": [5, 5, 15, 115]},
        {"item": "plan.footprint_pixels", "source": "plan.png", "bbox": [10, 10, 110, 110]},
        {"item": "plan.partitions:P1", "source": "plan.png", "bbox": [58, 10, 62, 110]},
        {"item": "plan.openings:W1", "source": "plan.png", "bbox": [8, 28, 13, 42]},
        {"item": "plan.space_seeds:left", "source": "plan.png", "bbox": [20, 40, 40, 60]},
    ], "unresolved": ["verify sill from elevation"]}


def test_plan_artifact_is_normalized_and_every_item_has_local_evidence():
    result = validate_plan_artifact(json.dumps(artifact()), image_name="plan.png")
    assert result["plan"]["partitions"][0]["id"] == "P1"
    assert {row["item"] for row in result["evidence"]} == {
        "plan.x_anchors", "plan.y_anchors", "plan.footprint_pixels",
        "plan.partitions:P1", "plan.openings:W1", "plan.space_seeds:left",
    }


def test_plan_artifact_errors_name_item_and_minimum_example():
    value = artifact()
    value["evidence"] = value["evidence"][:-1]
    with pytest.raises(ValueError, match=r"plan\.space_seeds:left.*Minimum correct example"):
        validate_plan_artifact(value, image_name="plan.png")
    value = artifact()
    value["evidence"][0]["source"] = "other.png"
    with pytest.raises(ValueError, match=r"one original image.*Minimum correct example"):
        validate_plan_artifact(value, image_name="plan.png")


class Frozen:
    def __init__(self, run_directory=None):
        self.calls = []
        if run_directory is not None:
            self.run_directory = run_directory

    async def list_tools(self):
        from src.agent.runtime_roles.readers import ELEVATION_READER_TOOL_NAMES
        return [{"name": name, "description": name, "inputSchema": {"type": "object"}}
                for name in ELEVATION_READER_TOOL_NAMES if name != "pixel_profile"]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        body = {"profile_id": "profile_001"} if name == "view_pixel_profile" else {"ok": True}
        return {"content": [{"type": "text", "text": json.dumps(body)}], "structuredContent": body}

    def repeatability(self, name):
        return "read_only"

    def snapshot_state(self):
        return {"files": {}}

    def artifacts(self):
        return []

    def image_origins(self, result):
        return {}


class Trial:
    async def call(self, value):
        return {"content": [{"type": "text", "text": "{}"}], "structuredContent": {"status": "passed"}}

    def durable_snapshot(self):
        return {"snapshot_sha256": "0" * 64}

    def artifacts(self):
        return []

    def image_origins(self, result):
        return {}


def test_reader_tools_filter_catalog_enforce_one_image_and_reference_provenance():
    async def scenario():
        frozen = Frozen()
        tools = ReaderTools(frozen, role_id="plan_reader", image_name="plan.png", trial=Trial())
        catalog = await tools.list_tools()
        assert {row["name"] for row in catalog} >= {"pixel_profile", "view_pixel_profile", "trial_plan_bim"}
        trial_description = next(row["description"] for row in catalog if row["name"] == "trial_plan_bim")
        assert "segments_mm" in trial_description
        assert "printed_segments_mm" not in trial_description
        assert "tick_pixels has one more item than segments_mm" in trial_description
        assert "Never omit an observed wall/opening or change room topology to pass" in trial_description
        with pytest.raises(ValueError, match="only image"):
            await tools.call_tool("view_image", {"name": "other.png"})
        with pytest.raises(ValueError, match="not returned"):
            await tools.call_tool("map_pixels", {"profile": "profile_999"})
        await tools.call_tool("view_pixel_profile", {"name": "plan.png"})
        await tools.call_tool("map_pixels", {"profile": "profile_001"})
        await tools.call_tool("pixel_profile", {"name": "plan.png"})
        assert frozen.calls[-1] == ("view_pixel_profile", {"name": "plan.png", "include_image": False})
        assert tools.repeatability("trial_plan_bim") == "non_idempotent_write"
    asyncio.run(scenario())


def test_reader_reference_provenance_survives_resume_and_enters_snapshot(tmp_path):
    async def scenario():
        (tmp_path / "inputs.json").write_text(json.dumps({
            "images": {"plan.png": {"sha256": "a" * 64}}
        }))
        first = ReaderTools(Frozen(tmp_path), role_id="plan_reader", image_name="plan.png", trial=Trial())
        await first.call_tool("view_pixel_profile", {"name": "plan.png"})
        sidecar = tmp_path / "reader_issued_references.json"
        assert sidecar.is_file()
        resumed_frozen = Frozen(tmp_path)
        resumed = ReaderTools(resumed_frozen, role_id="plan_reader", image_name="plan.png", trial=Trial())
        await resumed.call_tool("map_pixels", {"profile": "profile_001"})
        snapshot = resumed.snapshot_state()
        assert snapshot["reader_scope"]["references"] == ["profile_001"]
        assert snapshot["reader_scope"]["sidecar_sha256"]
        assert snapshot["trial"]["snapshot_sha256"] == "0" * 64
    asyncio.run(scenario())


def test_inherited_profile_enters_new_reader_reference_scope(tmp_path):
    class InheritedTrial(Trial):
        def inherited_reference_ids(self):
            return {"profile_009"}

    async def scenario():
        (tmp_path / "inputs.json").write_text(json.dumps({
            "images": {"plan.png": {"sha256": "a" * 64}}
        }))
        frozen = Frozen(tmp_path)
        tools = ReaderTools(
            frozen, role_id="plan_reader", image_name="plan.png", trial=InheritedTrial())
        await tools.call_tool("map_pixels", {"profile": "profile_009"})
        assert frozen.calls[-1] == ("map_pixels", {"profile": "profile_009"})
        saved = json.loads((tmp_path / "reader_issued_references.json").read_text())
        assert saved["references"] == ["profile_009"]

    asyncio.run(scenario())
