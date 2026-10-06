import asyncio
import base64
import hashlib
import json

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
    assert hashlib.sha256(base64.b64decode(envelope["content"][0]["data"])).hexdigest() == image_sha
    assert len(pictures) == 2 and len(image_refs) == 1
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == complete
