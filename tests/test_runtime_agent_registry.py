from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from src.agent_runtime.agent_registry import (
    AgentVersionMismatch,
    agent_version_record,
    load_agent_registry,
    main,
    register_agent_version,
)
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts import BudgetAmounts


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "src/agent_runtime/agent_versions.json"
HISTORICAL_CONDITION = (
    ROOT / "AI_agent/logs/experiments/2026-10-02_sm24_glm_baseline/experiment_condition.json"
)


def _copy_registered_agent(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    registry = load_agent_registry(ROOT)
    for relative in registry["versions"][registry["current_version"]]["files"]:
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    registry_path = root / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return root, registry_path


def test_historical_frozen_agent_is_a_verified_registry_version():
    registry = load_agent_registry(ROOT)
    record = agent_version_record(ROOT)
    historical = registry["versions"]["5bb10538"]
    assert record["version_id"] == registry["current_version"]
    assert historical["source_commit"] == "5bb10538"
    expected_files = json.loads(HISTORICAL_CONDITION.read_text(encoding="utf-8"))[
        "implementation_sha256"
    ]
    assert {path: item["sha256"] for path, item in historical["files"].items()} == expected_files
    assert {item["kind"] for item in historical["files"].values()} == {
        "tool", "guidance", "task_description"
    }
    assert set(historical["tool_catalog_sha256"]) == {
        "coordinator", "readonly", "coordinator_mesh", "readonly_mesh"
    }


@pytest.mark.parametrize("changed_relative", [
    "scripts/tool_scripts/run_bim_agent.py",
    "scripts/tool_scripts/bim_agent_guidance.py",
    "scripts/tool_scripts/bim_agent_inputs.py",
    "scripts/tool_scripts/bim_agent_inference.py",
    "scripts/tool_scripts/bim_agent_mesh.py",
    "scripts/tool_scripts/bim_agent_budget.py",
    "scripts/tool_scripts/bim_agent_facade_checks.py",
    "scripts/tool_scripts/bim_agent_feedback.py",
])
def test_each_registered_file_change_fails_until_a_new_version_is_registered(
    tmp_path: Path, changed_relative: str,
):
    root, registry_path = _copy_registered_agent(tmp_path)
    changed = root / changed_relative
    changed.write_bytes(changed.read_bytes() + b"\n# registered-version-test\n")
    with pytest.raises(AgentVersionMismatch, match=changed_relative):
        agent_version_record(root, registry_path=registry_path)

    old_registry = load_agent_registry(root, registry_path)
    old_record = json.loads(json.dumps(old_registry["versions"]["5bb10538"]))
    registered = register_agent_version(
        root,
        "test-next",
        registry_path=registry_path,
        catalog_hashes=old_record["tool_catalog_sha256"],
    )
    assert registered["files"][changed_relative]["sha256"] == hashlib.sha256(
        changed.read_bytes()
    ).hexdigest()
    assert agent_version_record(root, registry_path=registry_path)["version_id"] == "test-next"
    updated = load_agent_registry(root, registry_path)
    assert updated["versions"]["5bb10538"] == old_record


def test_tool_dependency_change_outside_original_five_is_rejected(tmp_path: Path):
    root, registry_path = _copy_registered_agent(tmp_path)
    dependency = root / "src/agent/geometry/plan_partition.py"
    dependency.write_bytes(dependency.read_bytes() + b"\n# changed tool dependency\n")
    with pytest.raises(AgentVersionMismatch, match="plan_partition.py"):
        agent_version_record(root, registry_path=registry_path)


def test_verify_cli_and_runtime_manifest_record_current_agent_version(tmp_path, capsys):
    current = load_agent_registry(ROOT)["current_version"]
    assert main(["verify", "--root", str(ROOT)]) == 0
    assert json.loads(capsys.readouterr().out)["version_id"] == current

    run = tmp_path / "run"
    with EventStore(
        run,
        run_id="agent-version-test",
        task_id="task",
        budget_limit=BudgetAmounts(tokens=100, calls=1),
    ) as store:
        manifest = make_versions(
            store,
            root=ROOT,
            prompt="test",
            tools=[],
            parameters={"max_tokens": 1},
            route={"route_id": "offline", "model": "test"},
        )
        assert manifest.agent_version is not None
        assert manifest.agent_version.identifier == current
        evidence = manifest.agent_version.evidence
        assert evidence is not None
        assert json.loads(store.get_bytes(evidence.blob))["version_id"] == current


def test_registration_can_add_a_new_tool_file_without_changing_history(tmp_path):
    root, registry_path = _copy_registered_agent(tmp_path)
    new_tool = root / "scripts/tool_scripts/bim_agent_new_tool.py"
    new_tool.write_text("def register_new_tool(server):\n    return server\n", encoding="utf-8")
    registry = load_agent_registry(root, registry_path)
    old_record = json.loads(json.dumps(registry["versions"]["5bb10538"]))

    register_agent_version(
        root,
        "with-new-tool",
        registry_path=registry_path,
        catalog_hashes=old_record["tool_catalog_sha256"],
        additional_files={"scripts/tool_scripts/bim_agent_new_tool.py": "tool"},
    )
    current = agent_version_record(root, registry_path=registry_path)
    assert current["files"]["scripts/tool_scripts/bim_agent_new_tool.py"] == {
        "kind": "tool", "sha256": hashlib.sha256(new_tool.read_bytes()).hexdigest()
    }
    assert load_agent_registry(root, registry_path)["versions"]["5bb10538"] == old_record
    new_tool.write_text("changed", encoding="utf-8")
    with pytest.raises(AgentVersionMismatch, match="bim_agent_new_tool.py"):
        agent_version_record(root, registry_path=registry_path)
