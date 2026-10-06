"""Check final level rules against the already verified full-case build inputs."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from src.agent.runtime_roles.levels import apply_resolved_levels, resolve_levels

ROOT = Path(__file__).resolve().parents[4]
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1h"
REPORT = Path(__file__).parent


def main():
    checked = []
    for base in (SCRATCH / "pytest/final", SCRATCH / "reader_replays"):
        for path in base.rglob("role_assemblies/*.json"):
            state = json.loads(path.read_bytes())
            if not state.get("complete"):
                continue
            folder = path.parent.parent
            records = {r["task_id"]: r for p in (folder / "tasks").glob("*/reader_record.json")
                       for r in [json.loads(p.read_bytes())]}
            artifacts = {k: json.loads((folder / r["artifact"]["path"]).read_bytes())
                         for k, r in records.items() if r.get("artifact")}
            registry = SimpleNamespace(records=records, read=lambda task_id, **kw: artifacts[task_id])
            plans, elevations = {}, {}
            for ref in state["inputs"]["deliveries"]:
                artifact = artifacts[ref["task_id"]]
                if ref["role_id"] == "plan_reader":
                    plans[artifact["plan"]["floor_id"]] = artifact["plan"]
                else:
                    elevations[ref["task_id"]] = artifact
            levels, _ = resolve_levels(registry, plans, elevations)
            assert levels == state["inputs"]["levels"], path
            builds = 0
            for op_path in (folder / "role_operations").glob("*.json"):
                operation = json.loads(op_path.read_bytes())
                if operation["tool"] != "build_plan_bim":
                    continue
                ref = operation["reference"]
                row = records[ref["task_id"]]
                numeric = row["validation"].get("compiled_numeric_plan_file")
                if numeric:
                    artifact_path = folder / row["artifact"]["path"]
                    numeric_path = artifact_path.parent / "bim/trial_workspace" / numeric
                    raw = numeric_path.read_bytes()
                    assert hashlib.sha256(raw).hexdigest() == row["validation"]["compiled_numeric_plan_sha256"]
                    plan = json.loads(raw)
                else:
                    plan = artifacts[ref["task_id"]]["plan"]
                assert apply_resolved_levels(plan, ref["levels"]) == json.loads(operation["arguments"]["plan_json"])
                builds += 1
            checked.append({"receipt": path.relative_to(SCRATCH).as_posix(), "builds_identical": builds,
                            "candidate": state["candidate"], "levels_identical": True})
    assert sum(any(case + "-role-run/" in r["receipt"] for case in ("sm21", "sm24", "sm25"))
               for r in checked) == 7
    assert all(any("reader_replays/" + case in r["receipt"] for r in checked)
               for case in ("sm24_run3", "sm24_run4"))
    result = {"scope": "Final unit/mixed-label/conflicting-order fixes leave every previously verified numeric case's exact level resolution and expanded build input unchanged.",
              "model_service_requests": 0, "checked": checked}
    (REPORT / "level_compatibility.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                                     encoding="utf-8", newline="\n")
    print("Unchanged level resolutions and build inputs:", len(checked))


if __name__ == "__main__":
    main()
