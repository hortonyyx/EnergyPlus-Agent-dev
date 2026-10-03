"""Counterexamples from the first full review; all model boundaries stay offline."""
import asyncio
import gzip
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from mcp.server.fastmcp import FastMCP

from scripts.tool_scripts import bim_agent_feedback as feedback
from scripts.tool_scripts.bim_agent_guidance import build_guide, filter_tool_catalog
from scripts.tool_scripts.run_bim_agent import Toolkit, serve
from tests.test_bim_agent_tools import _run_with_one_image


RECORDS = Path(__file__).resolve().parents[1] / "AI_agent/logs/experiments/2026-10-01_behaviour_records/records"


@pytest.mark.parametrize("index", [63, 65])
def test_t1_sm25_original_bad_edits_explain_list_and_keep_original_error(tmp_path, index):
    with gzip.open(RECORDS / "2026-10-03_sm25_glm_tools_t1/record.json.gz", "rt") as stream:
        steps = json.load(stream)["invocations"][0]["steps"]
    arguments = next(s["arguments"] for s in steps if s["index"] == index)
    assert isinstance(json.loads(arguments["operations_json"]), dict)
    run = _run_with_one_image(tmp_path)
    servers = []
    with patch.object(FastMCP, "run", lambda server: servers.append(server)):
        serve(run)
    from src.agent.geometry.plan_revision import apply_plan_revision
    with patch.object(Toolkit, "revise_plan", lambda *_: apply_plan_revision({}, json.loads(arguments["operations_json"]))):
        reply = asyncio.run(servers[0].call_tool("revise_plan_bim", arguments))
    assert reply.isError
    text = reply.content[0].text
    assert "operations" in text and "list" in text and "需要列表" in text
    assert text != "0" and not list(run.glob("candidate_*"))


@pytest.mark.parametrize("ops", [[0], [None], ["update"], [[], {}]])
def test_hint_checks_every_list_element_before_reading_fields(ops):
    hint = feedback.repair_hint(None, "revise_plan_bim", {"operations_json": json.dumps(ops)}, "operation 0 invalid")
    assert "element" in hint and "object" in hint


def test_hint_failure_never_replaces_original_rejection(tmp_path):
    run = _run_with_one_image(tmp_path)
    servers = []
    with patch.object(FastMCP, "run", lambda server: servers.append(server)):
        serve(run)
    with patch.object(feedback, "repair_hint", side_effect=RuntimeError("broken explainer")):
        reply = asyncio.run(servers[0].call_tool("view_image", {"name": "not-an-image"}))
    assert reply.isError and "unknown input image filename" in reply.content[0].text
    assert "broken explainer" not in reply.content[0].text


@pytest.mark.parametrize("review,continuation", [(False, False), (True, False), (False, True), (True, True)])
def test_capability_catalog_and_guidance_agree_without_removing_inference(tmp_path, review, continuation):
    run = _run_with_one_image(tmp_path)
    manifest = json.loads((run / "inputs.json").read_text())
    manifest.update(review_detail_enabled=review, continuation_rounds=int(continuation))
    (run / "inputs.json").write_text(json.dumps(manifest))
    servers = []
    with patch.object(FastMCP, "run", lambda server: servers.append(server)):
        serve(run)
        serve(run, enabled_only=True)
    full = [t.model_dump(mode="json", by_alias=True, exclude_none=True)
            for t in asyncio.run(servers[0].list_tools())]
    actual = [t.model_dump(mode="json", by_alias=True, exclude_none=True)
              for t in asyncio.run(servers[1].list_tools())]
    assert len(full) == 42
    assert actual == filter_tool_catalog(full, review_detail=review, continuation=continuation)
    names = {t["name"] for t in actual}
    assert ("review_detail" in names) == review
    assert ("record_work_review" in names) == continuation
    assert {"record_inference", "inspect_inference", "audit_inference_candidate",
            "build_parametric_bim", "inspect_parametric_plan"} <= names
    for kind in ("drawings", "mesh_views", "photos", "unknown"):
        guide = build_guide(images=kind, review_detail=review, continuation=continuation)
        assert ("review_detail" in guide) == review
        assert ("does not reset it" in guide) == continuation
