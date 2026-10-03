"""Run the required offline R1 groups with durable commands and source hashes."""

import argparse
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
    parser.add_argument("group", choices=("short", "long", "frozen"))
    parser.add_argument("--revision", choices=("r1", "r1b"), default="r1")
    parser.add_argument("--attempt", choices=("final", "final-runtime"), default="final")
    args = parser.parse_args()
    accepted = json.loads((HERE.parent / "2026-10-02_harness_stage3/validation.json").read_text())
    prior = next(row for row in accepted["groups"] if row["group"] == args.group)
    tests = [arg for arg in prior["command"] if arg.startswith("tests/")]
    if args.group == "short":
        tests += ["tests/test_runtime_parallel_delegation.py",
                  "tests/test_runtime_r1_preparation.py", "tests/test_runtime_r1_facade.py"]
        if args.revision == "r1b":
            tests.append("tests/test_runtime_r1b_budget.py")
    work = ROOT / f".{args.revision}-work/validation/{args.attempt}"
    work.mkdir(parents=True, exist_ok=True)
    output = HERE / ("validation" if args.revision == "r1" else "r1b/validation")
    if args.attempt != "final":
        output /= args.attempt
    output.mkdir(parents=True, exist_ok=True)
    junit = output / f"{args.group}.xml"
    log = output / f"{args.group}.log"
    command = [sys.executable, "-m", "pytest", "-q", "-n", "2", "-s", *tests,
        f"--basetemp={work / (args.group + '-tmp')}", f"--junitxml={junit}",
        "-o", f"cache_dir={work / (args.group + '-cache')}"]
    sources = [ROOT / name for name in tests]
    for directory in ("src/agent_runtime", "src/harness_contracts", "src/building_contracts"):
        sources.extend((ROOT / directory).rglob("*.py"))
        sources.extend((ROOT / directory).rglob("*.json"))
    sources.extend((ROOT / "src/agent").glob("runtime_*.py"))
    identity = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(set(sources))}
    env = {**os.environ, "PYTHONPATH": f"{ROOT}:{ROOT / 'tests'}",
           "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(work)}
    started = time.monotonic()
    with log.open("w") as stream:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
    report = {"group": args.group, "returncode": completed.returncode,
        "seconds": round(time.monotonic() - started, 3), "command": command,
        "log": str(log.relative_to(HERE)), "junit": str(junit.relative_to(HERE)),
        "source_sha256": identity, "real_provider_calls": 0,
        "status": "passed" if completed.returncode == 0 else "failed"}
    if junit.is_file():
        suites = ET.parse(junit).getroot()
        report.update({key: sum(int(suite.get(key, "0")) for suite in suites)
                       for key in ("tests", "failures", "errors", "skipped")})
        report["passed"] = report["tests"] - report["failures"] - report["errors"] - report["skipped"]
    (output / f"{args.group}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in {"command", "source_sha256"}}))
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
