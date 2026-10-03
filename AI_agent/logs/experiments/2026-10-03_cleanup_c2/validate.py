"""Reproduce one offline C2 validation group with exactly two pytest workers."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def source_hashes(group):
    registry = json.loads((ROOT / "src/agent_runtime/agent_versions.json").read_bytes())
    paths = set(registry["versions"][registry["current_version"]]["files"])
    paths.update(str(p.relative_to(ROOT)) for pattern in (
        "src/agent_runtime/*.py", "src/agent/runtime_*.py", "src/harness_contracts/*.py",
        "src/agent/contracts/*.py") for p in ROOT.glob(pattern))
    paths.update(files_for(group))
    if group == "short":
        paths.add("AI_agent/logs/experiments/2026-10-02_harness_stage0/build_samples.py")
    paths.add("src/agent_runtime/agent_versions.json")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(paths)}


def files_for(group):
    previous = json.loads((HERE.parent / "2026-10-03_runtime_r2/r2bc/validation.json").read_bytes())
    if group == "short":
        return [arg for arg in previous["groups"][0]["command"] if arg.startswith("tests/")] + ["tests/test_behaviour_c2.py"]
    if group == "t1":
        return sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests").glob("test_bim*.py"))
    return {"long": ["tests/test_runtime_long_task.py"],
        "frozen": ["tests/test_runtime_frozen_long_task.py"],
        "r3": ["tests/test_runtime_r3.py"]}[group]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=("short", "long", "frozen", "t1", "r3"))
    parser.add_argument("--final", action="store_true", help="Keep patch-version checks separate from initial checks")
    parser.add_argument("--retry", action="store_true", help="Preserve a previous failed run; write a separate retry record")
    args = parser.parse_args()
    label = "final_retry" if args.retry else "final" if args.final else ""
    target = HERE / "validation"
    if label:
        target = target / label
    target.mkdir(parents=True, exist_ok=True)
    work = ROOT / ".tmp_c2" / ("validation-" + args.group + ("-" + label if label else ""))
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", "-n", "2", "-s", *files_for(args.group),
        "--basetemp=" + str(work / "pytest"), "--junitxml=" + str(target / (args.group + ".xml")),
        "-o", "cache_dir=" + str(work / "cache")]
    before = source_hashes(args.group)
    version = json.loads((ROOT / "src/agent_runtime/agent_versions.json").read_bytes())["current_version"]
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    with (target / (args.group + ".log")).open("w") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
                 "TMPDIR": str(work), "R3_EVIDENCE_OUT": str(HERE / "counterexamples" / "final"
                    if args.final else HERE / "counterexamples")})
    after = source_hashes(args.group)
    suites = ET.parse(target / (args.group + ".xml")).getroot().findall("testsuite")
    counts = {name: sum(int(s.get(name, 0)) for s in suites)
              for name in ("tests", "failures", "errors", "skipped")}
    record = {"group": args.group, "agent_version": version, "started_utc": started,
        "completed_utc": datetime.now(timezone.utc).isoformat(), "seconds": round(time.monotonic() - clock, 3),
        "returncode": result.returncode, "model_requests": 0, "command": command, **counts,
        "passed": counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"],
        "source_unchanged_during_run": before == after, "source_sha256": after,
        "test_ids": [t.get("classname") + "::" + t.get("name") for s in suites for t in s.findall("testcase")]}
    (target / (args.group + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: record[key] for key in ("group", "passed", "failures", "errors", "seconds",
        "source_unchanged_during_run", "returncode")}))
    if result.returncode == 0:
        shutil.rmtree(work)
    raise SystemExit(result.returncode or (0 if before == after else 1))


if __name__ == "__main__":
    main()
