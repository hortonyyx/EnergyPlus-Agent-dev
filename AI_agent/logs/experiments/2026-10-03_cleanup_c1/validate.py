"""Run C1 and all stage 0–3 / R1–R3 checks within the assigned worktree."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=("all", "short", "long", "frozen"))
    args = parser.parse_args()
    previous = json.loads((HERE.parent / "2026-10-03_runtime_r2/r2bc/validation.json").read_bytes())
    files = [a for a in previous["groups"][0]["command"] if a.startswith("tests/")]
    if args.group in {"short", "all"}:
        files += ["tests/test_runtime_r3.py", "tests/test_runtime_c1.py"]
        if args.group == "all":
            files += ["tests/test_runtime_long_task.py", "tests/test_runtime_frozen_long_task.py"]
    else:
        files = ["tests/test_runtime_long_task.py" if args.group == "long" else "tests/test_runtime_frozen_long_task.py"]
    temp = ROOT / ".c1-tmp" / ("validation-" + args.group)
    temp.mkdir(parents=True, exist_ok=True)
    out = HERE / "validation"
    out.mkdir(exist_ok=True)
    paths = [*files, *(str(p.relative_to(ROOT)) for pattern in (
        "src/agent_runtime/*.py", "src/harness_contracts/*.py", "src/agent/runtime_*.py") for p in ROOT.glob(pattern))]
    hashes = lambda: {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(paths)}
    before = hashes()
    command = [sys.executable, "-m", "pytest", "-q", "-n", "2", "-s", *files,
        "--basetemp=" + str(temp / "pytest"), "--junitxml=" + str(out / (args.group + ".xml")),
        "-o", "cache_dir=" + str(temp / "cache")]
    start = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    with (out / (args.group + ".log")).open("w") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temp)})
    suites = ET.parse(out / (args.group + ".xml")).getroot().findall("testsuite")
    counts = {name: sum(int(s.get(name, 0)) for s in suites) for name in ("tests", "failures", "errors", "skipped")}
    record = {"group": args.group, "command": command, "started_utc": start,
        "seconds": round(time.monotonic() - clock, 3), "returncode": result.returncode,
        **counts, "passed": counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"],
        "source_unchanged_during_run": before == hashes(), "source_sha256": before, "model_requests": 0}
    if args.group == "all":
        groups = {name: {key: 0 for key in ("tests", "passed", "failures", "errors", "skipped")}
                  for name in ("short", "long", "frozen")}
        for suite in suites:
            for case in suite.findall("testcase"):
                filename = case.get("classname", "").split(".")[-1]
                name = ("long" if filename == "test_runtime_long_task" else
                        "frozen" if filename == "test_runtime_frozen_long_task" else "short")
                status = next((key for tag, key in (("failure", "failures"), ("error", "errors"),
                    ("skipped", "skipped")) if case.find(tag) is not None), "passed")
                groups[name]["tests"] += 1
                groups[name][status] += 1
        record["groups"] = groups
    (out / (args.group + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("group", "passed", "failures", "errors", "seconds", "source_unchanged_during_run")}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
