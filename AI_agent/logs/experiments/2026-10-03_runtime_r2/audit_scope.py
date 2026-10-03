"""Audit the R2 worktree against its assigned baseline; no repository mutation."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[4]
DELIVERY = Path(__file__).resolve().parent
BASELINE = "543beae3"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main():
    branch = git("branch", "--show-current").strip()
    assert branch == "dev/astra-r2-20261003", branch
    protected = ["scripts/tool_scripts", "src/agent/geometry", "src/agent/correction",
        "src/agent/execution", "AI_agent/Agent.md", "AI_agent/project",
        "AI_agent/logs/experiments/2026-10-03_runtime_r1",
        "AI_agent/logs/experiments/2026-10-03_runtime_r2/brief.md"]
    assert not git("diff", "--name-only", BASELINE, "--", *protected).strip()
    git("diff", "--check", BASELINE)
    paths = set(git("diff", "--name-only", BASELINE).splitlines())
    paths.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    prefix = str(DELIVERY.relative_to(ROOT)) + "/"
    paths.update(prefix + name for name in ("scope_audit.json", "change_manifest.json"))
    allowed = ("src/agent_runtime/", "src/agent/runtime_", "src/harness_contracts/",
        "tests/test_runtime_", "AI_agent/design/", "AI_agent/logs/worklog/", prefix)
    assert all(path.startswith(allowed) for path in paths)
    files = []
    for path in sorted(paths):
        item = {"path": path}
        if (ROOT / path).is_file() and path not in {prefix + "scope_audit.json", prefix + "change_manifest.json"}:
            data = (ROOT / path).read_bytes()
            item.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        files.append(item)
    evidence_bytes = sum(row.get("bytes", 0) for row in files if row["path"].startswith(prefix))
    assert evidence_bytes < 2_000_000, evidence_bytes
    head = git("rev-parse", "HEAD").strip()
    commits = [{"commit": line.split(" ", 1)[0], "subject": line.split(" ", 1)[1]}
               for line in git("log", "--reverse", "--format=%H %s", BASELINE + "..HEAD").splitlines()]
    metadata = {"baseline": BASELINE, "audited_head": head, "branch": branch,
        "generated_utc": datetime.now(UTC).isoformat(),
        "note": "Includes committed and pending delivery files. The subsequent metadata closure commit is intentionally outside this snapshot's commit list."}
    (DELIVERY / "change_manifest.json").write_text(json.dumps({**metadata,
        "commits": commits, "files": files}, indent=2) + "\n")
    report = {**metadata, "status": "passed", "changed_files": len(files),
        "forbidden_changes": [], "protected_paths_verified": protected,
        "delivery_bytes_excluding_self_describing_indexes": evidence_bytes,
        "evidence_limit_bytes": 2_000_000, "merged": False, "pushed": False}
    (DELIVERY / "scope_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "changed_files",
        "delivery_bytes_excluding_self_describing_indexes", "forbidden_changes")}))


if __name__ == "__main__":
    main()
