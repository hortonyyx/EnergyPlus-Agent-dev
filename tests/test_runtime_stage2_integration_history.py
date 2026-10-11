"""Optional archived transport replay; synthetic current boundaries remain separate."""
import asyncio
import json
import tempfile
from pathlib import Path
from tests.archive_paths import archive_path
from src.agent.runtime_entry import execute, parser
from src.agent_runtime.context import ContextManager
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts

ROOT = Path(__file__).resolve().parents[1]
STAGE1 = archive_path("AI_agent/logs/experiments/2026-10-02_harness_stage1")


def test_real_frozen_entry_builds_offline_and_completed_resume_does_not_write_again(tmp_path):
    # This calls the real frozen BIM MCP service, with a five-response script.
    # It is a small transport fixture, not a model-driven whole-case generation.
    # Explicit run ownership keeps this optional replay in the development cache.
    with tempfile.TemporaryDirectory(prefix="stage2-entry-test-", dir=tmp_path) as temporary:
        test_directory = Path(temporary)
        brief = test_directory / "building-input.json"
        brief.write_text(json.dumps({"constraints": ["Do not merge the two physical rooms"],
            "thermal_zones": 1}))
        args = parser().parse_args(["--out", str(test_directory / "run"),
            "--run-root", str(test_directory),
            "--images", str(STAGE1 / "offline_inputs"), "--provider", "scripted",
            "--building-input", str(brief),
            "--script", str(STAGE1 / "offline_responses.json"), "--context-window", "3",
            "--model-calls", "6", "--seconds", "180"])
        first = asyncio.run(execute(args))
        assert first["status"] == "completed"
        output = args.out
        before = (output / "events.jsonl").read_bytes()
        bim_before = (output / "bim/candidate_01/source_model.json").read_bytes()
        journal = json.loads((output / "journal.json").read_bytes())
        with EventStore(output, run_id=output.name, task_id="coordinator",
                budget_limit=BudgetAmounts.model_validate_json(json.dumps(journal["budget_limit"]))) as store:
            _, checkpoint, _ = store.latest_checkpoint()
            manager = ContextManager.load(store, checkpoint["context"])
            checklist = manager.checklist()
            requirement = checklist.entries("user_requirement")[0]
            assert "Do not merge the two physical rooms" in json.dumps(requirement.value)
            assert "not a measured" in json.dumps(requirement.value)
            first_request = next(e.payload for e in store.events if e.payload.event_type == "adapter_request")
            assert "Do not merge the two physical rooms" in json.dumps(store.resolve(first_request.final_request_body))
            for category in ("user_requirement", "constraint", "evidence_reference", "artifact_version",
                             "dimension", "object_id", "geometry"):
                assert checklist.entries(category), category
            # This fixture has no open items. C1 retires empty placeholders,
            # while preserving the exact saved report and source references.
            assert not checklist.entries("unresolved") and not checklist.entries("todo")
            states = {entry.key: entry for entry in manager.state}
            unresolved = states["source-bim-unresolved"]
            assert not unresolved.active and unresolved.source_refs
            assert all(not value for value in unresolved.value.values())
            assert not states["source-bim-todo"].active
            manifest = json.loads((output / "versions.json").read_bytes())
            assert len(manifest["dependency_lock"]["identifier"]) == 64
        args.resume = True
        resumed = asyncio.run(execute(args))
        assert resumed["resume_status"] == "already_completed"
        assert (output / "events.jsonl").read_bytes() == before
        assert (output / "bim/candidate_01/source_model.json").read_bytes() == bim_before
