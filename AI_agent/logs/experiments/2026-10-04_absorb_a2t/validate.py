"""Run A2-T offline acceptance checks in this worktree with two workers."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
C2 = importlib.import_module("AI_agent.logs.experiments.2026-10-03_cleanup_c2.validate")


def files_for(group):
    if group == "short":
        return sorted(set(C2.files_for("short") + ["tests/test_runtime_c1.py", "tests/test_runtime_r3.py"]))
    if group == "tools":
        return C2.files_for("t1")
    return ["tests/test_plan_partition.py", "tests/test_plan_assembly.py",
            "tests/test_parametric_proposal.py", "tests/test_source_proposal.py"]


def hashes(group):
    registry = json.loads((ROOT / "src/agent_runtime/agent_versions.json").read_bytes())
    paths = set(registry["versions"][registry["current_version"]]["files"])
    for pattern in ("src/agent_runtime/*.py", "src/harness_contracts/*.py", "src/agent/runtime_*.py"):
        paths.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    paths.update(files_for(group))
    paths.add("src/agent_runtime/agent_versions.json")
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(paths)}


def run(group, label):
    output = HERE / "validation" / label
    output.mkdir(parents=True, exist_ok=True)
    work = ROOT / ".tmp_a2t" / "validation" / label / group
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", "-n", "2", "-s", *files_for(group),
               "--basetemp=" + str(work / "pytest"), "-o", "cache_dir=" + str(work / "cache"),
               "--junitxml=" + str(output / f"{group}.xml")]
    before = hashes(group)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    with (output / f"{group}.log").open("w") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
                 "TMPDIR": str(work), "R3_EVIDENCE_OUT": str(output / "r3_counterexamples")})
    after = hashes(group)
    suites = ET.parse(output / f"{group}.xml").getroot().findall("testsuite")
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    record = dict(group=group, started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
                  seconds=round(time.monotonic() - clock, 3), command=command, returncode=result.returncode,
                  model_requests=0, **counts,
                  passed=counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"],
                  source_unchanged_during_run=before == after, source_sha256=after,
                  test_ids=[t.get("classname") + "::" + t.get("name") for s in suites for t in s.findall("testcase")])
    (output / f"{group}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("group", "passed", "failures", "errors", "skipped", "seconds", "source_unchanged_during_run")} ), flush=True)
    return result.returncode or (0 if before == after else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=("all", "short", "tools", "geometry"))
    parser.add_argument("--label", default="final", help="Use a new label to preserve failed attempts")
    args = parser.parse_args()
    groups = ("short", "tools") if args.group == "all" else (args.group,)
    for group in groups:
        code = run(group, args.label)
        if code:
            raise SystemExit(code)


if __name__ == "__main__":
    main()
