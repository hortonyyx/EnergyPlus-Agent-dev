"""Local edits preserve unmentioned evidence and still undergo full compilation."""
import asyncio
import copy
import json

import pytest

from src.agent.geometry.plan_revision import apply_plan_revision
from scripts.tool_scripts.bim_agent_inputs import freeze_plan_input
from scripts.tool_scripts.run_bim_agent import Toolkit, digest
from tests.test_bim_agent_plan_partition import example
from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session


def operation(op, **fields):
    return dict(op=op, reason="synthetic correction", source_refs=["synthetic"], **fields)


def test_local_operations_preserve_unmentioned_rows_and_parent():
    parent = example()
    before = copy.deepcopy(parent)
    revised, report = apply_plan_revision(parent, [
        operation("update", collection="openings", id="D1", changes={"z": [0, 2.2]}),
        operation("remove", collection="space_seeds", id="left"),
        operation("add", collection="space_seeds", value=dict(id="right", point=[8, 4])),
        operation("set", field="unresolved", value=["height unknown"]),
    ])
    assert parent == before and revised["partitions"] == parent["partitions"]
    assert revised["openings"][1] == parent["openings"][1]
    assert report["unchanged_ids"]["openings"] == ["W1"]
    assert report["unchanged_ids"]["partitions"] == ["wall-A"]
    assert revised["space_seeds"] == [dict(id="right", point=[8, 4])]


@pytest.mark.parametrize("bad", [
    operation("update", collection="partitions", id="missing", changes={"points": []}),
    operation("update", collection="openings", id="D1", changes={"id": "renamed"}),
    operation("add", collection="openings", value=dict(id="D1")),
    operation("set", field="partitions", value=[]),
    operation("remove", collection="openings", id="D1"),  # already updated in batch
])
def test_rejected_batch_is_atomic(bad):
    parent = example()
    before = copy.deepcopy(parent)
    with pytest.raises(ValueError):
        apply_plan_revision(parent, [
            operation("update", collection="openings", id="D1", changes={"z": [0, 2.2]}), bad])
    assert parent == before


def test_resume_and_failed_revision_keep_parent_and_full_evidence(tmp_path):
    run = _run_with_one_image(tmp_path)
    parent = tmp_path / "parent.json"
    parent.write_text(json.dumps(example()))
    manifest = json.loads((run / "inputs.json").read_text())
    manifest["plan_recovery"] = freeze_plan_input(parent, run, manifest["images"], "plan.png")
    (run / "inputs.json").write_text(json.dumps(manifest))
    toolkit = Toolkit(run)
    saved = toolkit.inspect_plan("resume")
    with pytest.raises(ValueError, match="stale"):
        toolkit.revise_plan("resume", "wrong", "[]")
    assert not (run / "plan_drafts").exists()
    result = toolkit.revise_plan("resume", saved["plan_sha256"], json.dumps([
        operation("update", collection="partitions", id="wall-A", changes={"points": [[6, 1], [6, 6]]})]))
    assert not result["source_geometry_ready"] and "dangles" in result["error"]
    record = result["plan_input"]
    assert (run / record["draft_view"]["image_file"]).is_file()
    assert digest(run / record["revision"]["file"]) == record["revision"]["sha256"]
    assert toolkit.inspect_plan("resume") == saved
    assert toolkit.inspect_plan("draft_001")["declaration"]["openings"] == example()["openings"]
    assert not list(run.glob("candidate_*"))


def test_revision_mcp_source_feedback_and_bound_preservation(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=True) as session:
            names = {t.name for t in (await session.list_tools()).tools}
            assert not {"inspect_plan_draft", "revise_plan_bim"} & names
        async with _server_session(run, readonly=False) as session:
            built = _json_result(await session.call_tool("build_plan_bim", {
                "image": "plan.png", "plan_json": json.dumps(example())}))
            saved = _json_result(await session.call_tool("inspect_plan_draft", {"draft_id": "draft_001"}))
            response = await session.call_tool("revise_plan_bim", dict(draft_id="draft_001",
                expected_plan_sha256=saved["plan_sha256"], operations_json=json.dumps([
                    operation("update", collection="openings", id="D1", changes={"z": [0, 2.2]})])))
            result = _json_result(response)
            assert result["source_geometry_ready"] and result["candidate"] != built["candidate"]
            assert len([b for b in response.content if b.type == "image"]) == 2
            source = json.loads((run / result["candidate"] / "source_model.json").read_text())
            assert source["generation"]["provenance"]["plan_input"] == result["plan_input"]
            revision = result["plan_input"]["revision"]
            assert digest(run / revision["file"]) == revision["sha256"]
            assert result["plan_revision"]["unchanged_ids"]["openings"] == ["W1"]
            assert Toolkit(run).inspect_plan("draft_001") == saved
    asyncio.run(scenario())
