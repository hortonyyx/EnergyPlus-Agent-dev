"""Read-only scope and Agent-version audit; write only the R3 audit report."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = "0b883a41"
T1_SOURCE = "74e27da3"
T1_IMPORT = "21243528"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    branch = git("branch", "--show-current").decode().strip()
    assert branch == "dev/astra-r3-20261003"
    imported = git("diff-tree", "--no-commit-id", "--name-only", "-r", T1_IMPORT).decode().splitlines()
    imported_bytes = {}
    for name in imported:
        original = git("show", f"{T1_SOURCE}:{name}")
        taken = git("show", f"{T1_IMPORT}:{name}")
        assert original == taken, name
        imported_bytes[name] = {"bytes": len(taken), "sha256": digest(taken)}
    changed = git("diff", "--name-only", BASE, "HEAD").decode().splitlines()
    forbidden = ("src/agent/geometry/", "src/agent/correction/", "src/agent/execution/",
        "AI_agent/project/", "AI_agent/Agent.md")
    assert not [name for name in changed if name.startswith(forbidden)]
    for name in imported:
        if name != "scripts/tool_scripts/run_bim_agent.py":
            assert (ROOT / name).read_bytes() == git("show", f"{T1_SOURCE}:{name}"), name
    for name in ("2026-10-03_sm24_glm_tools_t1", "2026-10-03_sm25_glm_tools_t1",
                 "2026-10-03_sm24_glm_tools_t1_setup_failed_no_env"):
        assert not git("ls-tree", "HEAD", "AI_agent/logs/experiments/" + name)
    registry_path = "src/agent_runtime/agent_versions.json"
    registry = json.loads((ROOT / registry_path).read_bytes())
    historical = json.loads(git("show", f"{BASE}:{registry_path}"))["versions"]["5bb10538"]
    assert registry["versions"]["5bb10538"] == historical
    current = registry["versions"][registry["current_version"]]
    assert all(digest((ROOT / name).read_bytes()) == row["sha256"] for name, row in current["files"].items())
    # Reading bytes cannot rewrite or load a module from the active main tree.
    main_root = Path("/workspaces/EnergyPlus-Agent-dev")
    main_frozen = {name: digest((main_root / name).read_bytes()) == row["sha256"]
                   for name, row in historical["files"].items()}
    assert all(main_frozen.values()), "main tree Agent no longer matches the frozen version"
    evidence_dirs = [HERE, HERE.parent / "2026-10-03_tool_package_t1",
        HERE.parent / "2026-10-01_behaviour_records/records/2026-10-03_sm24_glm_tools_t1",
        HERE.parent / "2026-10-01_behaviour_records/records/2026-10-03_sm25_glm_tools_t1"]
    evidence_sizes = {str(directory.relative_to(ROOT)): sum(p.stat().st_size for p in directory.rglob("*")
        if p.is_file() and p.name != "scope_audit.json") for directory in evidence_dirs}
    result = {"checked_utc": datetime.now(timezone.utc).isoformat(), "branch": branch,
        "base_commit": BASE, "t1_source_commit": T1_SOURCE, "t1_import_commit": T1_IMPORT,
        "model_requests": 0, "main_tree_files_written": 0, "pushed": False, "merged": False,
        "imported_files": imported_bytes, "imported_file_count": len(imported),
        "changed_tracked_files": changed,
        "geometry_correction_execution_project_changes": [],
        "raw_t1_runs_present": [], "historical_registry_record_unchanged": True,
        "current_version": registry["current_version"], "registered_files": len(current["files"]),
        "registration_source_commit": current["source_commit"],
        "tool_catalog_sha256": current["tool_catalog_sha256"],
        "main_tree_frozen_files_checked_readonly": main_frozen,
        "evidence_bytes": evidence_sizes, "total_evidence_bytes": sum(evidence_sizes.values())}
    (HERE / "scope_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("branch", "current_version", "registered_files",
        "imported_file_count", "historical_registry_record_unchanged", "total_evidence_bytes")}))


if __name__ == "__main__":
    main()
