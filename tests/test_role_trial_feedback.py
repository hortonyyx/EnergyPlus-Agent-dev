import asyncio
import base64
import hashlib
import io
import json

import pytest
from PIL import Image

from src.agent.runtime_roles.trial import PlanTrial
from src.agent_runtime.adapter import convert_tool_result
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore


class InjectedTrial(PlanTrial):
    def __init__(self, receipt, images):
        super().__init__(object(), image_name="plan.png")
        self.injected_receipt = receipt
        self.injected_images = images

    async def run(self, plan=None, *, operations=None):
        return self.injected_receipt

    def _image_content(self, receipt):
        return list(self.injected_images)


def _receipt(tmp_path, *, passed):
    image = b"exact-overlay-bytes"
    image_sha = hashlib.sha256(image).hexdigest()
    complete = {
        "status": "passed" if passed else "failed",
        "plan_sha256": "plan-hash",
        "source_geometry_ready": passed,
        "candidate": "candidate_01" if passed else None,
        "receipt_file": "trial_receipts/trial_001.json",
        "returned_images": [{
            "file": "trial_receipts/trial_001_images/01_overlay.png",
            "sha256": image_sha,
            "mime_type": "image/png",
            "origin": {
                "source_image_name": "plan.png",
                "raw_metadata": {"large_marker": "origin-only-on-disk" * 100},
            },
        }],
        "drawing_differences": {"status": "reported", "items": [{"id": "DIFF-1"}]},
        "building_precision": {"status": "reported", "items": [{"id": "PREC-1"}]},
        "topology_issues": [{"id": "TOPO-1", "divider": "P1"}],
        "topology_dividers": {"P1": [[1, 2], [3, 4]]},
        "changes": [{"path": "plan.openings:W1", "before": [1, 2], "after": [2, 3]}],
        "operations": [{"op": "update", "id": "W1", "changes": {"p1": [2, 3]}}],
        "plan_revision": {"actual_changes": [{"path": "plan.openings:W1"}]},
    }
    if not passed:
        complete.update({
            "reason": "opening W1 has no full host; repro_marker",
            "repair_hint": {"path": "plan.openings[0]", "example": "move onto wall"},
            "unhosted_openings": [{"id": "W1", "p1": [2, 3], "p2": [4, 3]}],
            "source_findings": [{"code": "opening_overlap", "opening_ids": ["W1"]}],
        })
    receipt_path = tmp_path / complete["receipt_file"]
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(complete), encoding="utf-8", newline="\n")
    block = {"type": "image", "data": base64.b64encode(image).decode(), "mimeType": "image/png"}
    return complete, block, receipt_path, image_sha


def _convert(tmp_path, envelope):
    limits = RunLimits(model_calls=1, tool_calls=1, seconds=10, tokens=10_000)
    with EventStore(
        tmp_path / "events", run_id="trial-feedback", task_id="plan-reader",
        budget_limit=limits.ledger_limit(),
    ) as store:
        return convert_tool_result("trial-call", envelope, store)


def test_trial_model_projection_keeps_actionable_feedback_and_full_disk_receipt(tmp_path):
    complete, image, receipt_path, image_sha = _receipt(tmp_path, passed=True)
    envelope = asyncio.run(InjectedTrial(complete, [image]).call({}))
    visible = envelope["structuredContent"]

    assert visible["returned_images"] == [{
        "file": complete["returned_images"][0]["file"], "sha256": image_sha,
    }]
    assert "origin" not in visible["returned_images"][0]
    assert visible["drawing_differences"] == complete["drawing_differences"]
    assert visible["building_precision"] == complete["building_precision"]
    assert visible["topology_issues"] == complete["topology_issues"]
    assert visible["changes"] == complete["changes"]
    assert visible["audit_refs"]["operations"]["receipt_file"] == complete["receipt_file"]
    assert "operations" not in visible and "plan_revision" not in visible
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == complete
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["returned_images"][0]["origin"]
    assert hashlib.sha256(base64.b64decode(envelope["content"][0]["data"])).hexdigest() == image_sha

    message, pictures, _, image_refs = _convert(tmp_path, envelope)
    assert json.loads(message["content"]) == visible
    assert len(pictures) == 2 and len(image_refs) == 1


def test_failed_trial_is_one_json_after_adapter_and_loses_no_error_location(tmp_path):
    complete, image, receipt_path, image_sha = _receipt(tmp_path, passed=False)
    envelope = asyncio.run(InjectedTrial(complete, [image]).call({}))
    message, pictures, _, image_refs = _convert(tmp_path, envelope)

    assert message["content"].startswith("Tool error (isError=true):\n{")
    json_text = message["content"].split("\n", 1)[1]
    visible = json.loads(json_text)
    assert message["content"].count("repro_marker") == 1
    assert visible["reason"] == complete["reason"]
    assert visible["repair_hint"] == complete["repair_hint"]
    assert visible["unhosted_openings"] == complete["unhosted_openings"]
    assert visible["source_findings"] == complete["source_findings"]
    assert visible["topology_issues"] == complete["topology_issues"]
    assert visible["drawing_differences"] == complete["drawing_differences"]
    assert visible["building_precision"] == complete["building_precision"]
    assert visible["message"].startswith("trial_plan_bim failed")
    assert visible["next_action"]["objects"] == ["plan.openings[0]"]
    assert "Preserve all other observed walls, openings and room topology" in visible["next_action"]["instruction"]
    assert hashlib.sha256(base64.b64decode(envelope["content"][0]["data"])).hexdigest() == image_sha
    assert len(pictures) == 2 and len(image_refs) == 1
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == complete


def test_large_failed_trial_keeps_located_actions_and_references_repeated_audit_detail(tmp_path):
    complete, image, receipt_path, _ = _receipt(tmp_path, passed=False)
    complete["reason"] = "many dangles; " + ("repeated compiler detail " * 200)
    complete["repair_hint"] = {
        "path": "plan.partitions[0].points[1]",
        "note": "Move only the named endpoint using the original drawing.",
        "junction_repairs": [{"path": f"plan.partitions[{i}].points[1]"} for i in range(20)],
    }
    complete["changes"] = [{"path": f"plan.partitions:{i}"} for i in range(30)]
    complete["alignment"] = {
        "schema_version": "reader_alignment.v1", "status": "rejected",
        "fallback": {"status": "not_applied", "aligned_compile_error": "x" * 5000,
                     "original_compile_error": "y" * 5000},
        "junction_preparation": {"status": "rolled_back", "compile_error": "z" * 5000,
                                 "changes": list(range(20)), "attempted_changes": list(range(20))},
    }
    receipt_path.write_text(json.dumps(complete), encoding="utf-8", newline="\n")
    visible = asyncio.run(InjectedTrial(complete, [image]).call({}))["structuredContent"]

    assert visible["next_action"]["objects"] == ["plan.partitions[0].points[1]"]
    assert len(visible["repair_hint"]["junction_repairs"]) == 8
    assert visible["repair_hint"]["junction_repairs_remaining"] == 12
    assert len(visible["changes"]) == 12 and visible["changes_remaining"] == 18
    assert visible["alignment"]["junction_preparation"]["has_compile_error"] is True
    assert "compile_error" not in visible["alignment"]["junction_preparation"]
    assert {"reason", "repair_hint", "changes"} <= set(visible["audit_refs"])
    assert len(json.dumps(visible)) < 6000
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["reason"] == complete["reason"]


def _large_precision():
    # Reproduce the observed shape, not case answers: three repeated ledgers,
    # each change containing the complete before/after geometry snapshot.
    geometry = [{"id": f"synthetic-{i}", "points": [[i, j] for j in range(28)]} for i in range(32)]
    changes = [{"path": f"partitions:P{i}", "before": geometry, "after": geometry} for i in range(24)]
    return {"status": "pass", "total": 0, "counts": {}, "items": [],
            "not_checked": ["drawing fidelity", "opening heights"],
            "regularization": {"reports": [{"status": "applied", "changes": changes,
                "reading_alignment": {"changes": changes}, "regularization_inputs": {"changes": changes}}]}}


def test_failed_compiled_candidate_also_bounds_precision_without_losing_repair_actions(tmp_path):
    complete, image, receipt_path, _ = _receipt(tmp_path, passed=False)
    complete["trial_id"] = "trial_001"
    complete["building_precision"] = _large_precision()
    complete["building_precision"].update(status="failed", total=1,
        items=[{"type": "thin_space", "space_id": "C1", "boundary_ids": ["B1"], "look_box": [1, 2, 3, 4]}])
    receipt_path.write_text(json.dumps(complete), encoding="utf-8")
    original = receipt_path.read_bytes()
    trial = InjectedTrial(complete, [image])
    trial.workspace, trial.receipts = tmp_path, [complete]
    envelope = asyncio.run(trial.call({}))
    visible = envelope["structuredContent"]
    assert len(original) > 1_000_000 and len(json.dumps(visible).encode()) < 20_000
    assert envelope["isError"] and visible["status"] == "failed"
    assert visible["source_geometry_ready"] is False
    assert visible["reason"] == complete["reason"]
    assert visible["repair_hint"] == complete["repair_hint"]
    assert visible["next_action"]["objects"] == ["plan.openings[0]"]
    assert visible["building_precision"]["items"] == complete["building_precision"]["items"]
    assert "submission" not in visible and "tool" not in visible["next_action"]
    leaf = trial.read_draft(field="report:/building_precision/regularization/reports/0/changes/23/before/31")
    assert leaf["value"] == complete["building_precision"]["regularization"]["reports"][0]["changes"][23]["before"][31]
    assert receipt_path.read_bytes() == original

    from src.agent_runtime.adapter import ScriptedAdapter
    from src.agent_runtime.loop import Runtime
    from src.harness_contracts import ToolGrant
    from tests.test_agent_runtime import MESSAGES, response, role, versions

    trial.injected_images = []

    class Boundary:
        async def list_tools(self):
            return [{"name": name, "description": name, "inputSchema": {"type": "object"}}
                    for name in ("trial_plan_bim", "read_plan_draft")]

        def repeatability(self, name):
            return "read_only" if name == "read_plan_draft" else "idempotent_write"

        async def call_tool(self, name, arguments):
            if name == "trial_plan_bim":
                return await trial.call({})
            value = trial.read_draft(**arguments)
            return {"content": [{"type": "text", "text": json.dumps(value)}], "structuredContent": value}

        def snapshot_state(self):
            return {"receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()}

        def artifacts(self):
            return [receipt_path]

    def inspect_after_failure(body):
        tool = next(m for m in reversed(body["messages"]) if m["role"] == "tool")
        value = json.loads(tool["content"].split("\n", 1)[1])
        assert value["status"] == "failed" and value["next_action"]["objects"] == ["plan.openings[0]"]
        assert len(json.dumps(body).encode()) < 30_000
        return response(("read", "read_plan_draft", {
            "field": "report:/building_precision/regularization/reports/0/changes/23/before/31"}))

    def inspected(body):
        tool = next(m for m in reversed(body["messages"]) if m["role"] == "tool")
        value = json.loads(tool["content"])
        assert value["value"] == leaf["value"]
        assert value["trial_status"] == "failed"
        return response(text="Located evidence recovered; next action remains repair, not submit.")

    limits = RunLimits(model_calls=3, tool_calls=2, seconds=60, tokens=200_000, context_tokens=40_000)
    tools_role = role(limits).model_copy(update={"tool_whitelist": (
        ToolGrant(tool_name="trial_plan_bim", access="write"), ToolGrant(tool_name="read_plan_draft", access="read"))})
    with EventStore(tmp_path / "failure-events", run_id="failed-trial", task_id="reader",
                    budget_limit=limits.ledger_limit()) as store:
        engine = Runtime(store=store, adapter=ScriptedAdapter([
            response(("trial", "trial_plan_bim", {})), inspect_after_failure, inspected]),
            tools=Boundary(), role=tools_role, model="test", parameters={"max_tokens": 256},
            versions=versions(), limits=limits)
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed" and result["model_calls"] == 3
        store.validate()
    assert receipt_path.read_bytes() == original


def test_megabyte_passed_receipt_remains_browsable_and_all_topology_decisions_discoverable(tmp_path):
    complete, image, receipt_path, _ = _receipt(tmp_path, passed=True)
    complete["trial_id"] = "trial_001"
    complete["building_precision"] = _large_precision()
    complete["topology_issues"] = [{"issue_id": f"issue-{i}", "divider": f"P{i}",
        "look_box": [i, 1, i + 2, 3], "check": "Resolve this observed separator with a located decision."}
        for i in range(30)]
    receipt_path.write_text(json.dumps(complete), encoding="utf-8")
    original = receipt_path.read_bytes()
    assert len(original) > 1_000_000
    trial = InjectedTrial(complete, [image])
    trial.workspace, trial.receipts = tmp_path, [complete]
    visible = asyncio.run(trial.call({}))["structuredContent"]
    assert len(json.dumps(visible).encode()) < 25_000
    assert visible["building_precision"]["status"] == "pass"
    assert visible["building_precision"]["not_checked"] == ["drawing fidelity", "opening heights"]
    assert visible["submission"]["status"] == "not_submitted"
    assert visible["submission"]["topology_decisions_required"] == 30
    assert visible["next_action"]["tool"] == "submit_plan_reading"
    assert visible["receipt_audit"]["sha256"] == hashlib.sha256(json.dumps(
        complete, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert "receipt_audit" not in complete

    # Traverse all pages; giant nested rows are references, never giant pages.
    args = {"field": "report:/building_precision/regularization/reports/0/changes"}
    indexes = []
    while args:
        page = trial.read_draft(**args)
        assert len(json.dumps(page).encode()) < 20_000
        indexes.extend(row["key"] for row in page["entries"])
        args = page.get("next")
    assert indexes == list(range(24))
    leaf = trial.read_draft(field="report:/building_precision/regularization/reports/0/changes/23/before/31")
    assert leaf["value"] == complete["building_precision"]["regularization"]["reports"][0]["changes"][23]["before"][31]
    issues, args = [], {"field": "report:/topology_issues"}
    while args:
        page = trial.read_draft(**args)
        issues.extend(row["value"]["issue_id"] for row in page["entries"])
        args = page.get("next")
    assert issues == [row["issue_id"] for row in complete["topology_issues"]]
    assert receipt_path.read_bytes() == original
    with pytest.raises(ValueError, match="pointer"):
        trial.read_draft(field="report:/../../outside.json")
    with pytest.raises(ValueError, match="page"):
        trial.read_draft(field="report:/building_precision", object_id="page:-1")
    corrupted = dict(complete, status="failed")
    receipt_path.write_text(json.dumps(corrupted), encoding="utf-8")
    with pytest.raises(ValueError, match="changed since execution"):
        trial.read_draft(field="report:/building_precision")


def test_megabyte_success_continues_through_runtime_adapter_to_explicit_submission(tmp_path):
    from src.agent.runtime_roles.submission import ReaderSubmission, SUBMISSION_TOOLS
    from src.agent_runtime.adapter import ScriptedAdapter
    from src.agent_runtime.loop import Runtime
    from src.harness_contracts import ToolGrant
    from tests.test_agent_runtime import MESSAGES, response, role, versions
    from tests.test_role_readers import plan
    from tests.test_role_trial import Tools

    workspace = tmp_path / "workspace"
    (workspace / "images").mkdir(parents=True)
    original_image = b"hash-stable offline image fixture; no drawing"
    (workspace / "images/plan.png").write_bytes(original_image)
    image_sha = hashlib.sha256(original_image).hexdigest()
    (workspace / "inputs.json").write_text(json.dumps({"images": {"plan.png": {"sha256": image_sha}}}))
    stream = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(stream, "PNG")

    class LargeTools(Tools):
        async def call_tool(self, name, arguments):
            result = await super().call_tool(name, arguments)
            (workspace / "candidate_01/precision_report.json").write_text(json.dumps(_large_precision()))
            result["structuredContent"]["drawing_differences"] = {"status": "reported", "total": 0, "items": []}
            result["content"][0]["data"] = base64.b64encode(stream.getvalue()).decode()
            return result

    compiler = LargeTools(workspace=workspace)
    trial = PlanTrial(compiler, image_name="plan.png", workspace=workspace,
                      receipt_directory=workspace / "trial_receipts")
    submission = ReaderSubmission(role_id="plan_reader", image_name="plan.png", trial=trial,
                                  directory=tmp_path / "submission", target="F1")

    class ReaderBoundary:
        async def list_tools(self):
            return [{"name": "trial_plan_bim", "description": "trial", "inputSchema": {"type": "object"}},
                    SUBMISSION_TOOLS["plan_reader"]]

        def repeatability(self, name):
            return "idempotent_write"

        async def call_tool(self, name, arguments):
            if name == "trial_plan_bim":
                return await trial.call(**arguments)
            saved = submission.submit(arguments)
            return {"content": [{"type": "text", "text": json.dumps(saved)}], "structuredContent": saved}

        def snapshot_state(self):
            return {"trial": trial.durable_snapshot(), "submission": submission.snapshot()}

        def artifacts(self):
            return trial.artifacts() + ([submission.path] if submission.path.is_file() else [])

    def submit_after_trial(body):
        assert submission.read() is None  # passed was not silently promoted to delivery
        tool = next(m for m in reversed(body["messages"]) if m["role"] == "tool")
        visible = json.loads(tool["content"])
        assert visible["status"] == "passed" and visible["source_geometry_ready"]
        assert visible["submission"]["status"] == "not_submitted"
        assert any(m["role"] == "user" and isinstance(m["content"], list) for m in body["messages"])
        assert len(json.dumps(body).encode()) < 40_000
        return response(("submit", "submit_plan_reading", {"trial_id": "latest"}))

    limits = RunLimits(model_calls=3, tool_calls=2, seconds=60, tokens=200_000, context_tokens=40_000)
    reader_role = role(limits).model_copy(update={"tool_whitelist": tuple(
        ToolGrant(tool_name=n, access="write") for n in ("trial_plan_bim", "submit_plan_reading"))})
    adapter = ScriptedAdapter([response(("trial", "trial_plan_bim", {"plan": plan()})),
                               submit_after_trial, response(text="Submitted")])
    with EventStore(tmp_path / "events", run_id="passed-trial", task_id="reader",
                    budget_limit=limits.ledger_limit()) as store:
        engine = Runtime(store=store, adapter=adapter, tools=ReaderBoundary(), role=reader_role, model="test",
                         parameters={"max_tokens": 256}, versions=versions(), limits=limits)
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed", result
        assert result["model_calls"] == 3 and result["tool_calls"] == 2
        assert len(compiler.calls) == 1
        assert not [e for e in store.events if e.payload.event_type == "model_failure"]
        store.validate()
    receipt = trial.receipts[0]
    saved = submission.read()
    assert saved["validation"]["validation_passed"]
    assert saved["artifact"]["plan"] == trial.numeric_plan(receipt)
    assert saved["artifact"]["evidence"]
    full = json.loads((workspace / receipt["receipt_file"]).read_bytes())
    assert full["building_precision"] == _large_precision()
    assert len(json.dumps(full).encode()) > 1_000_000
    identities = {key: receipt[key] for key in ("receipt_file", "plan_sha256", "compiled_numeric_plan_sha256",
                                               "candidate", "candidate_source_sha256")}
    receipt_sha = hashlib.sha256(json.dumps(receipt, ensure_ascii=False, sort_keys=True,
                                            separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    assert trial.verified_unsubmitted_draft(image_sha, **identities,
        expected_receipt_sha256=receipt_sha)[0] == plan()
    with pytest.raises(ValueError, match="event-bound full receipt digest"):
        trial.verified_unsubmitted_draft(image_sha, **identities)
    inherited = PlanTrial(None, image_name="plan.png")
    inherited.inherit_reference(trial, receipt["plan_sha256"], ["plan.openings"])
    assert "building_precision" not in inherited.read_draft()
    inherited_report = inherited.read_draft(field="report:/building_precision/regularization/reports/0/changes")
    assert inherited_report["inherited"] and inherited_report["next"]["trial_id"] == "latest"
    assert inherited.read_draft(**inherited_report["next"])["entries"][0]["key"] == 8
    assert inherited.read_draft(field="report:/topology_issues")["value"] == receipt["topology_issues"]
    receipt_path = workspace / receipt["receipt_file"]
    original_receipt = receipt_path.read_bytes()
    tampered = dict(receipt, topology_issues=[{"issue_id": "changed-obligation"}])
    receipt_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="inherited trial receipt changed"):
        inherited.read_draft(field="report:/topology_issues")
    reloaded = PlanTrial(None, image_name="plan.png", workspace=workspace,
                         receipt_directory=workspace / "trial_receipts")
    with pytest.raises(ValueError, match="full receipt differs"):
        reloaded.verified_unsubmitted_draft(image_sha, **identities, expected_receipt_sha256=receipt_sha)
    receipt_path.write_bytes(original_receipt)
    with pytest.raises(ValueError, match="event result"):
        trial.verified_unsubmitted_draft(image_sha, **{**identities, "candidate_source_sha256": "0" * 64})
    source_path = workspace / receipt["candidate"] / "source_model.json"
    source_path.write_bytes(source_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="source hash"):
        trial.verified_unsubmitted_draft(image_sha, **identities, expected_receipt_sha256=receipt_sha)


def test_bounded_json_browser_preserves_escaped_keys_and_long_text_pages():
    from src.agent.runtime_roles.trial_feedback import bounded_json_view

    text = "located evidence 中文 " * 800
    document = {"a/b~c": {"text": text, "rows": [{"nested": text}] * 20}}
    ref = lambda pointer, value: {"pointer": pointer, "sha256": hashlib.sha256(
        json.dumps(value, sort_keys=True).encode()).hexdigest()}
    pointer = "/a~1b~0c/text"
    parts, offset = [], 0
    while True:
        page = bounded_json_view(document, pointer=pointer, offset=offset, reference_for=ref)
        parts.append(page["text"])
        assert len(json.dumps(page).encode()) < 2500
        if "next_offset" not in page:
            break
        offset = page["next_offset"]
    assert "".join(parts) == text
    page = bounded_json_view(document, pointer="/a~1b~0c/rows", reference_for=ref)
    assert len(page["entries"]) == 8 and page["next_offset"] == 8
    assert len(json.dumps(page).encode()) < 12_000
    assert page["entries"][0]["value"]["full_record"]["pointer"] == "/a~1b~0c/rows/0"
    for pointer in ("/a~2b", "/a~1b~0c/rows/-1", "/a~1b~0c/rows/01"):
        with pytest.raises(ValueError, match="pointer"):
            bounded_json_view(document, pointer=pointer, reference_for=ref)
    with pytest.raises(ValueError, match="offset"):
        bounded_json_view(document, offset=-1, reference_for=ref)
    with pytest.raises(ValueError, match="offset"):
        bounded_json_view(document, offset=True, reference_for=ref)
    with pytest.raises(ValueError, match="beyond"):
        bounded_json_view(document, pointer="/a~1b~0c/rows", offset=20, reference_for=ref)
    with pytest.raises(ValueError, match="beyond"):
        bounded_json_view(document, pointer="/a~1b~0c/text", offset=len(text), reference_for=ref)
