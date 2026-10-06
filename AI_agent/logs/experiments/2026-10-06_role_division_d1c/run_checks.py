"""Run the D1c affected offline checks and retain small, LF-only evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TEMP = ROOT / "AI_agent/archive/local_backup/d1c"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--follow-up", action="store_true", help="check the final cross-task review inheritance fix")
    args = parser.parse_args()
    extra = subprocess.check_output([
        "rg", "-l", r"src\.agent\.runtime_roles\.(trial|plan_review|readers|submission|guidance|session|plan_format)|PlanTrial|ReaderSubmission|PLAN_READER_GUIDANCE",
        "tests", "-g", "test_*.py",
    ], cwd=ROOT, text=True).splitlines()
    files = sorted({path.relative_to(ROOT).as_posix() for path in (ROOT / "tests").glob("test_role*.py")}
                   | {Path(path).as_posix() for path in extra}
                   | {"tests/test_runtime_agent_registry.py", "tests/test_runtime_frozen_tools.py",
                      "tests/test_bim_agent_plan_partition.py"})
    if args.follow_up:
        files = ["tests/test_role_session.py", "tests/test_role_rework_handoff.py"]
    label = "checks_followup" if args.follow_up else "checks"
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1", OPENBLAS_NUM_THREADS="1",
               TEMP=str(TEMP / "tmp"), TMP=str(TEMP / "tmp"))
    (TEMP / "tmp").mkdir(parents=True, exist_ok=True)
    if json.loads((ROOT / "src/agent_runtime/agent_versions.json").read_bytes())["current_version"] != "t1-20261006-d1c.1":
        env["BIM_AGENT_REGISTRY_PATH"] = str(TEMP / "agent_versions.json")
    basetemp = TEMP / ("pytest-followup" if args.follow_up else "pytest-roles")
    xml = TEMP / (label + ".xml")
    command = [sys.executable, "-m", "pytest", "-n", "2", "--basetemp", str(basetemp),
               "-o", "cache_dir=" + str(TEMP / "pytest-cache"), "--junitxml", str(xml), "-q", *files]
    code_files = sorted((ROOT / "src/agent/runtime_roles").glob("*.py"))
    hashes = lambda: {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in code_files}
    before = hashes()
    started = time.monotonic()
    log = TEMP / (label + ".txt")
    with log.open("w", encoding="utf-8", newline="\n") as output:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace")
        for line in process.stdout:
            output.write(line)
            output.flush()
            print(line, end="", flush=True)
        status = process.wait()
    suites = ET.parse(xml).getroot()
    summary = {"exit_code": status, "elapsed_seconds": round(time.monotonic() - started, 3),
               "model_service_requests": 0, "workers": 2, "files": files,
               "console_output": log.read_text(encoding="utf-8"),
               "code_sha256": before, "code_unchanged_during_checks": hashes() == before,
               "counts": {key: sum(int(row.get(key, 0)) for row in suites.iter("testsuite"))
                          for key in ("tests", "failures", "errors", "skipped")},
               "failures": [{"name": row.get("name"), "detail": row.findtext("failure") or row.findtext("error")}
                            for row in suites.iter("testcase") if row.find("failure") is not None or row.find("error") is not None],
               "pipeline_and_recovery": [{"name": row.get("name"), "seconds": row.get("time"),
                   "passed": row.find("failure") is None and row.find("error") is None}
                   for row in suites.iter("testcase") if row.get("classname", "").endswith("test_role_end_to_end")],
               "deliveries": []}
    for delivery in sorted(basetemp.rglob("delivery.json")):
        folder = delivery.parent
        if folder.name == "bim":
            summary["deliveries"].append({"path": delivery.relative_to(TEMP).as_posix(),
                "candidate_count": len(list(folder.glob("candidate_*"))),
                "delivery_sha256": hashlib.sha256(delivery.read_bytes()).hexdigest()})
    (HERE / (label + ".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: summary[key] for key in ("counts", "elapsed_seconds", "exit_code")}))
    raise SystemExit(status)


if __name__ == "__main__":
    main()
