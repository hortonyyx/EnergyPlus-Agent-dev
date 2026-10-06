import asyncio
import base64
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from src.agent.runtime_roles.trial import PlanTrial, PlanTrialSession, canonical_plan_sha256
from tests.test_bim_agent_plan_partition import example
from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session


ROOT = Path(__file__).resolve().parents[1]


class Tools:
    def __init__(self, ready=True, workspace=None):
        self.ready = ready
        self.workspace = workspace
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        compiled_sha = hashlib.sha256(arguments["plan_json"].encode("utf-8")).hexdigest()
        if self.ready and self.workspace is not None:
            candidate = self.workspace / "candidate_01"
            candidate.mkdir(exist_ok=True)
            (candidate / "source_model.json").write_text(json.dumps({
                "spaces": [{"id": "C1", "role": "corridor"}, {"id": "C2", "role": "corridor"}],
                "boundaries": [],
            }))
            (candidate / "precision_report.json").write_text(json.dumps({
                "status": "reported", "items": [{"type": "thin_space", "space_id": "C1"}]
            }))
        body = {
            "source_geometry_ready": self.ready,
            "candidate": "candidate_01" if self.ready else None,
            "plan_input": {"plan_file": "plan_drafts/draft_001/plan.json", "plan_sha256": compiled_sha},
            "drawing_differences": {"total": 1, "items": [{"kind": "unsupported_declared_divider"}]},
            "building_precision": {"items": [{"kind": "thin_space"}]},
            "source_plan_views": [{"image": "candidate_01/plan.png"}],
        }
        if not self.ready:
            body.update(error="opening W1 has no full host", repair_hint={"path": "plan.openings[0]"})
        image = base64.b64encode(b"trial-png").decode()
        return {"content": [{"type": "image", "data": image, "mimeType": "image/png"},
                            {"type": "text", "text": "ignored"}], "structuredContent": body}

    def image_origins(self, raw):
        digest = hashlib.sha256(b"trial-png").hexdigest()
        return {digest: {"sent_sha256": digest, "origin_status": "trial overlay"}}


def test_trial_hashes_exact_plan_preserves_checks_and_requires_same_success(tmp_path):
    async def scenario():
        value = {"floor_id": "F1", "unresolved": []}
        trial = PlanTrial(Tools(), image_name="plan.png", receipt_directory=tmp_path)
        envelope = await trial.call(value)
        receipt = envelope["structuredContent"]
        assert receipt["status"] == "passed"
        assert receipt["plan_sha256"] == canonical_plan_sha256(value)
        assert receipt["original_plan_sha256"] == receipt["plan_sha256"]
        assert receipt["compiled_numeric_plan_sha256"] == receipt["compiled_plan_sha256"]
        assert receipt["drawing_differences"]["total"] == 1
        assert receipt["building_precision"]["items"][0]["kind"] == "thin_space"
        assert "corridor" in receipt["corridor_review"]["hint"].lower()
        assert trial.require_success(value) == receipt
        assert trial.delivery_receipt(value)["validation_passed"] is True
        with pytest.raises(ValueError, match="has not been run"):
            trial.require_success({**value, "floor_id": "F2"})
        assert (tmp_path / "trial_001.json").is_file()
    asyncio.run(scenario())


def test_failed_trial_is_retained_but_not_accepted():
    async def scenario():
        value = {"floor_id": "F1"}
        trial = PlanTrial(Tools(ready=False), image_name="plan.png")
        receipt = await trial.run(value)
        assert receipt["status"] == "failed"
        assert receipt["reason"] == "opening W1 has no full host"
        with pytest.raises(ValueError, match="no successful isolated trial"):
            trial.require_success(value)
        delivery = trial.delivery_receipt(value)
        assert delivery["validation_passed"] is False
        assert delivery["reason"] == "opening W1 has no full host"
    asyncio.run(scenario())


def test_resolution_error_is_a_repairable_failed_receipt(tmp_path):
    async def scenario():
        (tmp_path / "images").mkdir()
        (tmp_path / "images" / "plan.png").write_bytes(b"original")
        tools = Tools()
        plan = {
            "floor_id": "F1",
            "x_anchors": [[{"profile": "profile_001", "candidate": "C01"}, 0], [10, 1]],
        }
        trial = PlanTrial(
            tools,
            image_name="plan.png",
            receipt_directory=tmp_path / "trial_receipts",
            workspace=tmp_path,
            profile_directory=tmp_path / "pixel_profiles",
        )
        envelope = await trial.call(plan)
        receipt = envelope["structuredContent"]
        assert envelope["isError"] is True
        assert "trial_plan_bim failed" in envelope["content"][-1]["text"]
        assert receipt["status"] == "failed"
        assert receipt["original_plan_sha256"] == canonical_plan_sha256(plan)
        assert receipt["compiled_numeric_plan_file"] is None
        assert receipt["repair_hint"]["example"]
        assert tools.calls == []
        assert trial.delivery_receipt(plan)["validation_passed"] is False
        resumed = PlanTrial(
            Tools(),
            image_name="plan.png",
            receipt_directory=tmp_path / "trial_receipts",
            workspace=tmp_path,
            profile_directory=tmp_path / "pixel_profiles",
        )
        assert resumed.delivery_receipt(plan)["reason"] == receipt["reason"]

    asyncio.run(scenario())


def test_contradictory_alias_failure_receipt_can_resume(tmp_path):
    async def scenario():
        bad = {"partitions": [{
            "id": "P1", "points": [[1, 2], [3, 4]], "pixels": [[1, 2], [3, 4]],
        }]}
        receipts = tmp_path / "trial_receipts"
        trial = PlanTrial(Tools(), image_name="plan.png", receipt_directory=receipts, workspace=tmp_path)
        result = await trial.call(bad)
        assert result["isError"] and "both pixels and points" in result["structuredContent"]["reason"]
        resumed = PlanTrial(Tools(), image_name="plan.png", receipt_directory=receipts, workspace=tmp_path)
        assert resumed.receipts[0]["reason"] == result["structuredContent"]["reason"]

    asyncio.run(scenario())


def test_trial_persists_images_and_resume_reuses_verified_receipt(tmp_path):
    async def scenario():
        workspace = tmp_path / "trial_workspace"
        workspace.mkdir()
        (workspace / "images").mkdir()
        (workspace / "images" / "plan.png").write_bytes(b"one-original")
        receipts = workspace / "trial_receipts"
        value = {"floor_id": "F1"}
        tools = Tools(workspace=workspace)
        first = PlanTrial(tools, image_name="plan.png", receipt_directory=receipts, workspace=workspace)
        envelope = await first.call(value)
        assert envelope["content"][0]["type"] == "image"
        assert envelope["structuredContent"]["corridor_review"]["status"] == "warning"
        assert envelope["structuredContent"]["returned_images"][0]["origin"]["origin_status"] == "verified trial input lineage"
        origins = first.image_origins(envelope)
        image_sha = envelope["structuredContent"]["returned_images"][0]["sha256"]
        assert origins[image_sha]["source_image_name"] == "plan.png"
        assert origins[image_sha]["original_sha256"] == hashlib.sha256(b"one-original").hexdigest()
        assert first.durable_snapshot()["snapshot_sha256"]
        numeric = workspace / envelope["structuredContent"]["compiled_numeric_plan_file"]
        assert hashlib.sha256(numeric.read_bytes()).hexdigest() == envelope["structuredContent"]["compiled_numeric_plan_sha256"]
        assert any(path.name == "source_model.json" for path in first.artifacts())
        resumed_tools = Tools(workspace=workspace)
        resumed = PlanTrial(resumed_tools, image_name="plan.png", receipt_directory=receipts, workspace=workspace)
        reused = await resumed.call(value)
        assert resumed_tools.calls == []
        assert reused["content"][0]["data"] == envelope["content"][0]["data"]
        assert resumed.delivery_receipt(value)["validation_passed"] is True
    asyncio.run(scenario())


def test_alias_normalization_has_one_trial_identity():
    alias = {"floor_id": "F1", "partitions": [{"id": "P1", "pixels": [[1, 2], [3, 4]]}]}
    canonical = {"floor_id": "F1", "partitions": [{"id": "P1", "points": [[1, 2], [3, 4]]}]}
    assert canonical_plan_sha256(alias) == canonical_plan_sha256(canonical)

    async def scenario():
        trial = PlanTrial(Tools(), image_name="plan.png")
        receipt = await trial.run(alias)
        assert receipt["field_aliases"] == [
            "plan.partitions[0].pixels accepted as plan.partitions[0].points; coordinates unchanged."
        ]
        assert trial.require_success(canonical) == receipt

    asyncio.run(scenario())


def test_trial_session_prepares_exactly_one_image_workspace(tmp_path):
    reader = tmp_path / "reader"
    (reader / "images").mkdir(parents=True)
    raw = b"one-original"
    (reader / "images" / "plan.png").write_bytes(raw)
    (reader / "inputs.json").write_text(json.dumps({
        "images": {"plan.png": {"size": [12, 8], "sha256": hashlib.sha256(raw).hexdigest()}},
        "image_kind": "drawings", "started_epoch": 1, "deadline_epoch": 10,
    }))
    session = PlanTrialSession(reader, "plan.png", root=tmp_path)
    session._prepare()
    manifest = json.loads((reader / "trial_workspace" / "inputs.json").read_text())
    assert list(manifest["images"]) == ["plan.png"]
    assert manifest["scope"] == "one plan-reader image; no parent building draft"
    assert (reader / "trial_workspace" / "images" / "plan.png").read_bytes() == raw


def test_real_profile_is_resolved_to_recoverable_independent_numeric_plan(tmp_path):
    async def scenario():
        reader = _run_with_one_image(tmp_path)
        image = Image.new("RGB", (12, 8), "black")
        draw = ImageDraw.Draw(image)
        for x in (5, 7):
            draw.line((x, 0, x, 7), fill=(128, 128, 128))
        image.save(reader / "images" / "plan.png")
        manifest = json.loads((reader / "inputs.json").read_text())
        manifest["images"]["plan.png"]["sha256"] = hashlib.sha256(
            (reader / "images" / "plan.png").read_bytes()
        ).hexdigest()
        (reader / "inputs.json").write_text(json.dumps(manifest))

        async with _server_session(reader, readonly=True) as service:
            response = await service.call_tool("view_pixel_profile", {
                "name": "plan.png", "box": [0, 0, 12, 8], "axis": "x",
                "rgb": [128, 128, 128], "tolerance": 0, "min_fraction": 0.5,
                "include_image": False,
            })
            assert not response.isError
            profile = json.loads(response.content[0].text)
        assert [row["peak"] for row in profile["candidates"]] == [5, 7]

        plan = example()
        midpoint = {"midpoint": [
            {"profile": profile["profile_id"], "candidate": "C01"},
            {"profile": profile["profile_id"], "candidate": "C02"},
        ]}
        for point in plan["partitions"][0]["points"]:
            point[0] = midpoint
        for key in ("p1", "p2"):
            plan["openings"][0][key][0] = midpoint

        async with PlanTrialSession(reader, "plan.png", root=ROOT) as trial:
            receipt = await trial.run(plan)
            assert receipt["status"] == "passed", receipt
            assert len(receipt["measurement_bindings"]) == 4
            assert receipt["measurement_profiles"] == [{
                "profile_id": profile["profile_id"],
                "file": f"trial_receipts/trial_001_profiles/{profile['profile_id']}.json",
                "sha256": hashlib.sha256(
                    (reader / "pixel_profiles" / f"{profile['profile_id']}.json").read_bytes()
                ).hexdigest(),
            }]
            numeric_path = reader / "trial_workspace" / receipt["compiled_numeric_plan_file"]
            numeric_bytes = numeric_path.read_bytes()
            assert hashlib.sha256(numeric_bytes).hexdigest() == receipt["compiled_numeric_plan_sha256"]
            numeric = json.loads(numeric_bytes)
            assert numeric["partitions"][0]["points"] == [[6, 1], [6, 7]]
            assert receipt["compiled_plan_sha256"] == receipt["compiled_numeric_plan_sha256"]

        # The saved numeric plan compiles from a clean run containing no profiles.
        independent = tmp_path / "independent"
        (independent / "images").mkdir(parents=True)
        (independent / "images" / "plan.png").write_bytes(
            (reader / "images" / "plan.png").read_bytes()
        )
        (independent / "inputs.json").write_bytes((reader / "inputs.json").read_bytes())
        from scripts.tool_scripts.run_bim_agent import Toolkit
        built = Toolkit(independent).build_plan("plan.png", numeric_bytes.decode("utf-8"))
        assert built["source_geometry_ready"] and not (independent / "pixel_profiles").exists()

        # Resume reuses the verified receipt. Both derived products are tamper-evident.
        async with PlanTrialSession(reader, "plan.png", root=ROOT) as resumed:
            assert resumed.require_success(plan)["compiled_numeric_plan_sha256"] == receipt["compiled_numeric_plan_sha256"]
        numeric_path.write_bytes(numeric_bytes + b" ")
        with pytest.raises(ValueError, match="numeric plan changed"):
            async with PlanTrialSession(reader, "plan.png", root=ROOT):
                pass
        numeric_path.write_bytes(numeric_bytes)
        copied_profile = reader / "trial_workspace" / receipt["measurement_profiles"][0]["file"]
        copied_profile.write_bytes(copied_profile.read_bytes() + b" ")
        with pytest.raises(ValueError, match="measurement profile changed"):
            async with PlanTrialSession(reader, "plan.png", root=ROOT):
                pass

    asyncio.run(scenario())
