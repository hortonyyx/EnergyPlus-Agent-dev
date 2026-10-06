"""Read-only Git/byte audit of the D1b delivery; write only this experiment's result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from src.agent_runtime.agent_registry import agent_version_record


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASELINE = "5349e0a07885bd70c36ffbdd7aa8242646a46ccf"


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def main():
    paths = sorted(set(git("ls-files", "-m", "-o", "--exclude-standard", "-z")
                       .decode("utf-8").strip("\0").split("\0")))
    allowed_prefixes = ("src/agent/runtime_roles/", "tests/", HERE.relative_to(ROOT).as_posix() + "/")
    allowed_files = {"src/agent/geometry/plan_drawing_differences.py",
                     "src/agent_runtime/agent_versions.json",
                     "scripts/tool_scripts/bim_agent_role_heights.py"}
    out_of_scope = [path for path in paths if path not in allowed_files and not path.startswith(allowed_prefixes)]
    crlf = [path for path in paths if b"\r" in (ROOT / path).read_bytes()]
    if out_of_scope or crlf:
        raise ValueError({"out_of_scope": out_of_scope, "non_LF": crlf})
    registry_path = "src/agent_runtime/agent_versions.json"
    baseline = json.loads(git("show", BASELINE + ":" + registry_path))
    current = json.loads((ROOT / registry_path).read_bytes())
    assert all(current["versions"][name] == record for name, record in baseline["versions"].items())
    record = agent_version_record(ROOT)
    assert record["version_id"] == "t1-20261006-d1b.2"
    original_checks = {}
    for relative in (
        "AI_agent/logs/experiments/2026-10-06_role_division_analysis/score_role_answers.py",
        "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/sm24_anchor.json",
        "AI_agent/project/roadmap.md", "AI_agent/project/decisions.md",
        "AI_agent/project/unified_agent_acceptance.md",
    ):
        raw = (ROOT / relative).read_bytes()
        # Read binary Git blobs, avoiding PowerShell line-ending conversion.
        assert raw == git("show", BASELINE + ":" + relative), relative
        original_checks[relative] = hashlib.sha256(raw).hexdigest()
    small_runs = []
    for folder in ("small_test_d1b", "small_test_d1b_final"):
        directory = ROOT / "AI_agent/archive/local_backup/d1b" / folder
        manifest = json.loads((directory / "small_test_manifest.json").read_bytes())
        result = json.loads((directory / "small_test_result.json").read_bytes())
        version = manifest["agent"].pop("version_id")
        assert manifest["agent"] == current["versions"][version]
        assert result["agent_unchanged"]
        runner = HERE / ("run_small_test.py" if folder == "small_test_d1b" else "run_small_test_final.py")
        assert hashlib.sha256(runner.read_bytes()).hexdigest() == manifest["runner_sha256"]
        small_runs.append({"run": folder, "version": version, "http_requests": result["actual_http_requests"],
                           "agent_and_runner_match": True})
    total = sum(row["http_requests"] for row in small_runs)
    assert total <= 40
    git("diff", "--check")
    report = {"baseline": BASELINE, "agent_version": record["version_id"],
              "all_changed_files_in_scope": True, "all_changed_text_LF": True,
              "changed_file_count": len(paths), "changed_files": paths,
              "original_versions_preserved": len(baseline["versions"]),
              "original_bytes_unchanged": original_checks,
              "real_runs": small_runs, "cumulative_http_requests": total,
              "git_diff_check": "passed", "git_policy": "read-only operations only; no commits or config writes"}
    (HERE / "delivery_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in report.items() if key != "changed_files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
