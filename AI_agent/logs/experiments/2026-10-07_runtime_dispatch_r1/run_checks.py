"""RT1 offline checks using the existing explicit scratch-registry mechanism."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TEMP = ROOT / "AI_agent/archive/local_backup/rt1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="checks_followup")
    parser.add_argument("--failed-from", type=Path)
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()
    files = args.files
    if args.failed_from:
        if args.failed_from.suffix == ".json":
            identities = json.loads(args.failed_from.read_bytes())["failed_tests"]
            files += [name.split("::")[0].replace(".", "/") + ".py::" + name.split("::", 1)[1]
                      for name in identities]
        else:
            suites = ET.parse(args.failed_from).getroot()
            files += [row.get("classname").replace(".", "/") + ".py::" + row.get("name")
                      for row in suites.iter("testcase")
                      if row.find("failure") is not None or row.find("error") is not None]
    if not files:
        files = [p.relative_to(ROOT).as_posix() for pattern in
                 ("test_runtime*.py", "test_role*.py", "test_agent_runtime.py")
                 for p in (ROOT / "tests").glob(pattern)]
    whole_files = {path for path in files if "::" not in path}
    files = sorted({path for path in files if "::" not in path or path.split("::")[0] not in whole_files})

    from src.agent_runtime.agent_registry import register_agent_version
    import src.agent_runtime
    assert Path(src.agent_runtime.__file__).resolve().is_relative_to(ROOT)
    official = ROOT / "src/agent_runtime/agent_versions.json"
    official_before = official.read_bytes()
    scratch = TEMP / "registry/agent_versions.json"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(official, scratch)
    registry = json.loads(official_before)
    catalog_hashes = registry["versions"][registry["current_version"]]["tool_catalog_sha256"]
    # The actual tool catalogs are still checked by the normal verification.
    # Domain files/catalogs are unchanged by RT1. Never update the release file.
    register_agent_version(ROOT, "t1-20261007-rt1-offline", registry_path=scratch,
                           catalog_hashes=catalog_hashes)
    code = [p for p in (ROOT / "src/agent_runtime").iterdir() if p.suffix in (".py", ".json")]
    hashes = lambda: {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(code)}
    before = hashes()
    (TEMP / "tmp").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1", OPENBLAS_NUM_THREADS="1",
               TEMP=str(TEMP / "tmp"), TMP=str(TEMP / "tmp"),
               BIM_AGENT_REGISTRY_PATH=str(scratch),
               STAGE2_FROZEN_REPLAY_OUT=str(TEMP / "frozen-replay"))
    xml, log = TEMP / (args.label + ".xml"), TEMP / (args.label + ".log")
    command = [sys.executable, "-m", "pytest", "-n", "2", "--basetemp",
               str(TEMP / ("pytest-" + args.label)), "-o", "cache_dir=" + str(TEMP / "pytest-cache"),
               "--junitxml", str(xml), "-q", *files]
    started = time.monotonic()
    with log.open("w", encoding="utf-8", newline="\n") as output:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
    suites = ET.parse(xml).getroot()
    summary = {
        "command": command, "exit_code": result.returncode, "workers": 2,
        "elapsed_seconds": round(time.monotonic() - started, 3), "model_service_requests": 0,
        "counts": {key: sum(int(row.get(key, 0)) for row in suites.iter("testsuite"))
                   for key in ("tests", "failures", "errors", "skipped")},
        "official_registry_unchanged": official.read_bytes() == official_before,
        "scratch_registry": str(scratch.relative_to(ROOT)),
        "code_unchanged_during_checks": hashes() == before, "code_sha256": before,
        "cases": [{"id": row.get("classname") + "::" + row.get("name"),
                   "seconds": float(row.get("time", 0)),
                   "passed": row.find("failure") is None and row.find("error") is None,
                   **({"failure": row.findtext("failure") or row.findtext("error")}
                      if row.find("failure") is not None or row.find("error") is not None else {})}
                  for row in suites.iter("testcase")],
    }
    (HERE / (args.label + ".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2)
                                              + "\n", encoding="utf-8", newline="\n")
    print(log.read_text(encoding="utf-8")[-10000:])
    print(json.dumps({key: summary[key] for key in
                     ("counts", "elapsed_seconds", "exit_code", "official_registry_unchanged")}))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
