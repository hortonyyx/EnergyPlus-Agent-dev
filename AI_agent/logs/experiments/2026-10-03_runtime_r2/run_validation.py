"""Repeat the stage 0-3/R1 offline checks plus R2 counterexamples."""

import asyncio
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[4]
DELIVERY = Path(__file__).resolve().parent
WORK = DELIVERY / ".r2-work"


def source_identity():
    paths = [*sorted((ROOT / "src/agent_runtime").glob("*.py")),
             *sorted((ROOT / "src/agent_runtime").glob("*.json")),
             *sorted((ROOT / "src/agent").glob("runtime_*.py")),
             *sorted((ROOT / "src/harness_contracts").glob("*.py"))]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


async def group(name, tests, attempt=""):
    label = name + ("-" + attempt if attempt else "")
    validation = DELIVERY / "validation"
    validation.mkdir(exist_ok=True)
    work = WORK / label
    work.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", "-n", "2", "-s", *tests,
        "--basetemp=" + str(work / "tmp"), "--junitxml=" + str(validation / (label + ".xml")),
        "-o", "cache_dir=" + str(work / "cache")]
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    if name == "frozen":
        env["STAGE2_FROZEN_REPLAY_OUT"] = str(work / "replay")
    before = source_identity()
    started = time.monotonic()
    print(json.dumps({"group": name, "status": "started", "tests": tests}), flush=True)
    with (validation / (label + ".log")).open("w") as output:
        process = await asyncio.create_subprocess_exec(*command, cwd=ROOT, env=env,
            stdout=output, stderr=asyncio.subprocess.STDOUT)
        code = await process.wait()
    xml = ET.parse(validation / (label + ".xml")).getroot()
    suites = list(xml.iter("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, "0")) for s in suites)
              for key in ("tests", "failures", "errors", "skipped")}
    result = {"group": name, "returncode": code, "seconds": round(time.monotonic() - started, 3),
        "command": command, **totals, "passed": totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"],
        "source_sha256": before, "source_unchanged_during_group": before == source_identity(),
        "log": "validation/" + label + ".log", "junit": "validation/" + label + ".xml",
        "attempt": attempt or "initial",
        "model_calls": 0}
    (validation / (label + ".json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"source_sha256", "command"}}), flush=True)
    return result


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", nargs="+", choices=("short", "long", "frozen"))
    parser.add_argument("--attempt", default="")
    args = parser.parse_args()
    if args.attempt and not all(c.isalnum() or c in "-_" for c in args.attempt):
        parser.error("attempt must be a simple identifier")
    historical = json.loads((ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r1/r1b/validation.json").read_bytes())
    groups = {row["group"]: [arg for arg in row["command"] if arg.startswith("tests/")]
              for row in historical["groups"]}
    groups["short"] += ["tests/test_runtime_r2_truncation.py", "tests/test_runtime_r2_output_limits.py",
        "tests/test_runtime_agent_registry.py", "tests/test_runtime_image_accounting.py"]
    started = datetime.now(UTC).isoformat()
    results = await asyncio.gather(*(group(name, tests, args.attempt) for name, tests in groups.items()
                                    if args.groups is None or name in args.groups))
    result = {"started_utc": started, "completed_utc": datetime.now(UTC).isoformat(), "groups": results,
        "distinct_passed": sum(row["passed"] for row in results),
        "status": "passed" if all(row["returncode"] == 0 and row["source_unchanged_during_group"] for row in results) else "review_required",
        "model_calls": 0}
    filename = "validation" + ("-" + args.attempt if args.attempt else "") + ".json"
    (DELIVERY / filename).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "groups"}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
