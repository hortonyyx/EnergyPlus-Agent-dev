"""Audit the R2b/R2c branch against its supplied merge base, without model calls."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
BASE = "d3a09a90"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main():
    assert ROOT == Path("/workspaces/EnergyPlus-Agent-dev/.worktrees/astra-r2")
    assert git("branch", "--show-current").strip() == "dev/astra-r2-20261003"
    protected = ["scripts/tool_scripts", "src/agent/geometry", "src/agent/correction", "src/agent/execution",
        "AI_agent/Agent.md", "AI_agent/project", "AI_agent/workflow/models.md",
        "AI_agent/logs/experiments/2026-10-03_runtime_r1",
        "AI_agent/logs/experiments/2026-10-03_runtime_r2/brief.md",
        "AI_agent/logs/experiments/2026-10-03_runtime_r2/brief_r2bc.md",
        "AI_agent/logs/experiments/2026-10-03_runtime_r2/image_accounting_calibration.json",
        "AI_agent/logs/experiments/2026-10-03_runtime_r2/live_truncation_probe.tar.xz"]
    assert not git("diff", "--name-only", BASE, "--", *protected).strip()
    git("diff", "--check", BASE)
    paths = set(git("diff", "--name-only", BASE).splitlines())
    paths.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    prefix = str(HERE.relative_to(ROOT)) + "/"
    allowed = ("src/agent_runtime/", "src/agent/runtime_", "src/harness_contracts/", "tests/test_runtime_", prefix)
    documents = {"AI_agent/design/runtime_image_accounting.md",
        "AI_agent/logs/experiments/2026-10-03_runtime_r2/image_accounting_calibration.md",
        "AI_agent/logs/experiments/2026-10-03_runtime_r2/README.md"}
    assert all(path.startswith(allowed) or path in documents for path in paths), sorted(paths)
    scope_path = str((HERE / "scope_audit.json").relative_to(ROOT))
    rows = []
    for name in sorted(paths - {scope_path}):
        path = ROOT / name
        data = path.read_bytes()
        rows.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    evidence = sum(row["bytes"] for row in rows if row["path"].startswith(prefix))
    assert evidence < 2_000_000
    commits = [dict(zip(("commit", "subject"), line.split(" ", 1)))
        for line in git("log", "--reverse", "--format=%H %s", BASE + "..HEAD").splitlines()]
    credentials = json.loads((HERE / "credential_scan.json").read_bytes())
    assert credentials["status"] == "passed" and not credentials["credential_value_present"]
    result = {"status": "passed", "baseline": BASE, "audited_head": git("rev-parse", "HEAD").strip(),
        "branch": git("branch", "--show-current").strip(), "generated_utc": datetime.now(UTC).isoformat(),
        "protected_paths_verified": protected, "forbidden_changes": [], "files": rows,
        "delivery_bytes_excluding_this_index": evidence, "commits": commits,
        "credential_scan": credentials, "merged": False, "pushed": False,
        "note": "Subsequent closure commit contains only final delivery documentation/evidence; its hash is reported in the final handoff."}
    (HERE / "scope_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "passed", "changed_files": len(rows), "evidence_bytes": evidence,
        "commits": commits, "forbidden_changes": []}))


if __name__ == "__main__":
    main()
