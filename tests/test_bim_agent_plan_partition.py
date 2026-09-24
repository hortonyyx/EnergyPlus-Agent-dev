"""The pixel compiler is a source-producing MCP tool, with immutable input evidence."""
import asyncio
import base64
import hashlib
import io
import json
import pytest

from PIL import Image, ImageChops

from src.agent.geometry.plan_partition import OpeningHostError, compile_plan_partition
from scripts.tool_scripts.bim_agent_guidance import REFERENCES
from scripts.tool_scripts.run_bim_agent import Toolkit
from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session


def test_internal_compiler_fault_is_not_reported_as_repairable_declaration(tmp_path, monkeypatch):
    import src.agent.geometry.plan_partition as compiler

    def fail(*args, **kwargs):
        raise RuntimeError("internal compiler fault")

    run = _run_with_one_image(tmp_path)
    monkeypatch.setattr(compiler, "compile_plan_partition", fail)
    raw = json.dumps(example())
    with pytest.raises(RuntimeError, match="internal compiler fault"):
        Toolkit(run).build_plan("plan.png", raw)
    draft = run / "plan_drafts" / "draft_001"
    assert (draft / "plan.json").read_text() == raw
    assert (draft / "draft_view.png").is_file()
    assert not list(run.glob("candidate_*"))


def example():
    reference = REFERENCES["plan_partition"]
    return json.JSONDecoder().raw_decode(reference[reference.index("{"):])[0]


def test_concave_plan_tool_keeps_recess_and_returns_actual_source_feedback(tmp_path):
    run = _run_with_one_image(tmp_path)
    plan = example()
    plan["footprint_pixels"] = [[1, 1], [11, 1], [11, 7], [8, 7], [8, 6], [1, 6]]
    plan["partitions"][0]["points"][-1] = [6, 6]
    plan["openings"][1].update(p1=[8, 6.2], p2=[8, 6.8])
    result = Toolkit(run).build_plan("plan.png", json.dumps(plan))
    assert result["source_geometry_ready"], result
    source = json.loads((run / result["candidate"] / "source_model.json").read_text())
    assert len(source["floors"][0]["footprint"]) == 6
    assert len(source["spaces"]) == 2 and len(source["openings"]) == 2
    assert result["source_image_projections"][0]["source_model_sha256"] == source["source_model_sha256"]
    assert (run / result["plan_input"]["compilation_file"]).is_file()


def test_plan_tool_source_images_provenance_and_revised_calibration(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        raw = json.dumps(example(), ensure_ascii=False, indent=4) + "\n"
        async with _server_session(run, readonly=True) as session:
            assert "build_plan_bim" not in {tool.name for tool in (await session.list_tools()).tools}
            assert _json_result(await session.call_tool("get_bim_reference", {
                "topic": "plan_partition"}))["reference"] == REFERENCES["plan_partition"]
        async with _server_session(run, readonly=False) as session:
            response = await session.call_tool("build_plan_bim", {"image": "plan.png", "plan_json": raw})
            built = _json_result(response)
            assert built["source_geometry_ready"], built
            assert len([block for block in response.content if block.type == "image"]) == 2
            record = built["plan_input"]
            assert (run / record["plan_file"]).read_bytes() == raw.encode()
            assert record["plan_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
            draft_view = record["draft_view"]
            assert (run / draft_view["image_file"]).is_file()
            assert (run / draft_view["metadata_file"]).is_file()
            assert draft_view["draft_only"] and draft_view["drawing_fidelity"] == "not_evaluated"
            assert built["plan_compilation"] == json.loads((run / record["compilation_file"]).read_text())
            source = json.loads((run / built["candidate"] / "source_model.json").read_text())
            assert source["generation"]["provenance"]["plan_input"] == record
            assert len(source["spaces"]) == 2
            assert sorted(row["kind"] for row in source["openings"]) == ["door", "window"]
            assert not source["unbuilt_openings"]
            overlay = built["source_image_projections"][0]
            assert overlay["anchors"]["x"] == example()["x_anchors"]
            assert overlay["source_model_sha256"] == source["source_model_sha256"]
            revised = _json_result(await session.call_tool("revise_bim", {
                "candidate": built["candidate"], "operations_json": json.dumps([
                    {"op": "update_opening", "id": "D1", "changes": {"z": [0, 2.2]},
                     "reason": "synthetic height revision", "source_refs": ["synthetic"]}])}))
            assert revised["source_geometry_ready"]
            assert revised["source_image_projections"][0]["anchors"] == overlay["anchors"]
            assert revised["source_model_sha256"] != built["source_model_sha256"]
    asyncio.run(scenario())


def test_plan_compile_failures_preserve_raw_input_without_candidate(tmp_path):
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    raw = '{"broken": '
    result = toolkit.build_plan("plan.png", raw)
    assert result["status"] == "error"
    assert (run / result["plan_input"]["plan_file"]).read_text() == raw
    assert result["plan_input"]["draft_view_errors"][0]["path"] == "plan_json"

    # A patterned original makes the untouched left panel independently checkable.
    original = Image.new("RGB", (12, 8))
    original.putdata([(x * 17, y * 29, (x + y) * 11)
                      for y in range(8) for x in range(12)])
    original.save(run / "images" / "plan.png")
    manifest = json.loads((run / "inputs.json").read_text())
    manifest["images"]["plan.png"]["sha256"] = hashlib.sha256(
        (run / "images" / "plan.png").read_bytes()).hexdigest()
    (run / "inputs.json").write_text(json.dumps(manifest))

    plan = example()
    plan["partitions"][0]["points"][-1] = [6, 6]
    failed_raw = json.dumps(plan)
    host_plan = example()
    host_plan["openings"][0]["p1"] = [7, 3]
    host_plan["openings"][0]["p2"] = [7, 4.5]
    host_raw = json.dumps(host_plan)
    exact_host_error = (
        "opening D1 at pixels [7.0, 3.0] -> [7.0, 4.5] "
        "requires one exterior or two interior full-boundary hosts; found []"
    )
    with pytest.raises(OpeningHostError) as captured:
        compile_plan_partition(host_plan, image_size=(12, 8), image_name="plan.png")
    assert str(captured.value) == exact_host_error
    assert captured.value.opening_id == "D1"
    assert captured.value.p1_pixel == [7.0, 3.0]
    assert captured.value.p2_pixel == [7.0, 4.5]

    async def failed_mcp():
        async with _server_session(run, readonly=False) as session:
            results = []
            for raw, expected_error, image_count in (
                (failed_raw, "polygonize produced dangles", 1),
                (host_raw, exact_host_error, 2),
            ):
                response = await session.call_tool(
                    "build_plan_bim", {"image": "plan.png", "plan_json": raw})
                result = _json_result(response)
                assert result["status"] == "error"
                assert expected_error in result["error"]
                images = [block for block in response.content if block.type == "image"]
                assert len(images) == image_count
                returned = Image.open(io.BytesIO(base64.b64decode(images[0].data)))
                assert returned.size == (440, 32)
                if raw == host_raw:
                    local = Image.open(io.BytesIO(base64.b64decode(images[1].data))).convert("RGB")
                    view = result["plan_input"]["host_failure_view"]
                    saved = Image.open(run / view["image_file"]).convert("RGB")
                    assert local.size == saved.size and ImageChops.difference(local, saved).getbbox() is None
                    metadata = json.loads((run / view["metadata_file"]).read_text())
                    assert view["metadata"] == metadata
                    assert "panel origin + (original pixel - original crop origin)" in view["metadata"]["mapping"]
                    assert "Left is the clean original" in view["metadata"]["note"]
                    assert metadata["image"]["sha256"] == result["plan_input"]["image_sha256"]
                    assert metadata["plan"]["sha256"] == result["plan_input"]["plan_sha256"]
                    assert metadata["opening"]["id"] == "D1"
                    assert metadata["opening"]["p1_original_pixels"] == [7.0, 3.0]
                    assert metadata["opening"]["p2_original_pixels"] == [7.0, 4.5]
                    assert metadata["opening"]["full_declared_segment_preserved"]
                    crop = metadata["crop_original_pixels"]
                    left = metadata["panels"]["clean_original"]
                    expected = Image.open(run / "images" / "plan.png").convert("RGB").crop(tuple(crop))
                    expected = expected.resize(tuple(metadata["panel_size_pixels"]), Image.Resampling.NEAREST)
                    actual = local.crop(tuple(left))
                    assert actual.size == expected.size
                    assert ImageChops.difference(actual, expected).getbbox() is None
                    assert max(local.size) <= 1600
                assert not list(run.glob("candidate_*"))
                assert not (run / "overlay_calibrations").exists()
                results.append(result)
            return results

    result, host_result = asyncio.run(failed_mcp())
    record = result["plan_input"]
    assert (run / record["plan_file"]).read_text() == failed_raw
    sidecar = json.loads((run / record["draft_view"]["metadata_file"]).read_text())
    assert sidecar["declaration"] == plan
    assert sidecar["rendered"]["partitions"][0]["declared_pixel_points"] == [[6, 1], [6, 6]]
    assert sidecar["draft_only"] and sidecar["drawing_fidelity"] == "not_evaluated"
    assert sidecar["source_geometry_ready"] is False
    assert record["draft_view"]["unrenderable_count"] == 0
    assert sidecar["plan"]["sha256"] == record["plan_sha256"]
    assert sidecar["image"]["sha256"] == record["image_sha256"]
    host_sidecar = json.loads(
        (run / host_result["plan_input"]["draft_view"]["metadata_file"]).read_text())
    assert host_sidecar["rendered"]["openings"][0]["declared_p1"] == [7, 3]
    assert host_sidecar["rendered"]["openings"][0]["declared_p2"] == [7, 4.5]
    assert host_result["error"] == exact_host_error
    assert (run / host_result["plan_input"]["plan_file"]).read_text() == host_raw
    assert not list(run.glob("candidate_*"))
    assert len(list((run / "plan_drafts").glob("draft_*"))) == 3
    assert len((run / "tools.jsonl").read_text().splitlines()) == 3
