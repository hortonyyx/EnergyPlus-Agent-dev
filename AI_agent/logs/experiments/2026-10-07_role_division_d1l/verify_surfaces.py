"""Offline catalog comparison and isolated verification snapshot; no model calls."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[4]
REPORT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.agent import version_fingerprints as surfaces
from src.agent.runtime_roles.guidance import ROLE_GUIDANCE, guidance_catalog
from src.agent_runtime.agent_registry import register_versions, release_records
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore


def old_module(name):
    path = f"src/agent/runtime_roles/{name}.py"
    module = types.ModuleType(f"src.agent.runtime_roles._d1l_before_{name}")
    module.__file__ = str(ROOT / path)
    module.__package__ = "src.agent.runtime_roles"
    raw = subprocess.check_output(["git", "--no-optional-locks", "show", f"875a3ba3:{path}"], cwd=ROOT)
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module


def write(name, value):
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


async def main():
    captured = []
    original = surfaces._fingerprint

    def capture(tools, guidance, task):
        captured.append((tools, guidance, task))
        return original(tools, guidance, task)

    surfaces._fingerprint = capture
    try:
        fingerprints = await surfaces.domain_fingerprints(ROOT)
    finally:
        surfaces._fingerprint = original
    official_path = ROOT / "src/agent_runtime/agent_versions.json"
    official_bytes = official_path.read_bytes()
    official = json.loads(official_bytes)
    prior = official["domain_versions"][official["current_domain_version"]]
    single_keys = [key for key in fingerprints["mode_fingerprints"] if key.startswith("single_model/")]
    assert all(fingerprints["mode_fingerprints"][key] == prior["mode_fingerprints"][key] for key in single_keys)

    scratch = ROOT / "AI_agent/archive/local_backup/d1l/surface-snapshot"
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "inputs.json").write_text('{"images": {}}\n', encoding="utf-8", newline="\n")
    common = "review=False/continuation=False"
    old_readers, old_session = old_module("readers"), old_module("session")
    budget = RunLimits(model_calls=1, tool_calls=1, seconds=1, tokens=1)
    with EventStore(scratch / "catalog", run_id="d1l-catalog", task_id="coordinator", budget_limit=budget.ledger_limit()) as store:
        coordinator = old_session.RoleSession(store=store,
            frozen=surfaces._Catalog(captured[0][0][common], scratch), routes={}, adapter_factory=None,
            limits=budget, root=ROOT)
        reader = old_readers.ReaderTools(surfaces._Catalog(captured[1][0][common], scratch),
            role_id="plan_reader", image_name="<image>", trial=types.SimpleNamespace())
        before_tools = {"coordinator": await coordinator.list_tools(), "plan_reader": await reader.list_tools(),
                        "elevation_reader": captured[6][0]}
    before = json.loads((REPORT / "guidance_before.json").read_bytes())
    rows = {}
    for index, role in enumerate(("coordinator", "plan_reader", "elevation_reader"), 4):
        old, new = before_tools[role], captured[index][0]
        rows[role] = {
            "guidance_before": len(before["guidance"][role]), "guidance_after": len(ROLE_GUIDANCE[role]),
            "tool_descriptions_before": sum(len(row.get("description", "")) for row in old),
            "tool_descriptions_after": sum(len(row.get("description", "")) for row in new),
            "tools_before": old, "tools_after": new,
        }
    write("surface_comparison.json", {"baseline_commit": "875a3ba3", "roles": rows,
        "single_mode_fingerprints_unchanged": single_keys, "after_guidance": guidance_catalog(),
        "note": "Elevation implementation unchanged; catalog remains identical to its registered fingerprint.",
        "model_requests": 0})
    comparison = "# 平面读图员指引原文对照\n\n改前来自 875a3ba3，改后来自实际导入的角色指引；含完整方法和交付约定。\n\n## 改前\n\n```text\n" + before["guidance"]["plan_reader"] + "\n```\n\n## 改后\n\n```text\n" + ROLE_GUIDANCE["plan_reader"] + "\n```\n"
    (REPORT / "guidance_comparison.md").write_text(comparison, encoding="utf-8", newline="\n")
    snapshot_path = scratch / "agent_versions.json"
    shutil.copyfile(official_path, snapshot_path)
    registered = register_versions(ROOT, registry_path=snapshot_path, fingerprints=fingerprints)
    records = release_records(ROOT, registry_path=snapshot_path)
    assert official_path.read_bytes() == official_bytes
    assert registered["changed_lines"] == ["domain"]
    assert registered["changed_modes"] == ["role_division/coordinator", "role_division/plan_reader"]
    write("verification_snapshot.json", {"temporary_snapshot": str(snapshot_path), **registered,
        "official_registry_sha256": hashlib.sha256(official_bytes).hexdigest(),
        "official_registry_unchanged": True, "files": {line: record["files"] for line, record in records.items()},
        "scope": "Temporary offline verification only, not a release registration; delete after testing."})
    print(json.dumps({"snapshot": str(snapshot_path), "roles": {key: {field: value for field, value in row.items()
        if not field.startswith("tools_")} for key, row in rows.items()}, "changed_modes": registered["changed_modes"]}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
