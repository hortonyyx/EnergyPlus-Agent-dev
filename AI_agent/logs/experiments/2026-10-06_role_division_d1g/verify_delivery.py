"""Register D1g and run its offline checks; keep all scratch files inside d1g.

This invokes the normal registry CLI parser. Its temporary catalog probe is
relocated from the repository root to the required local_backup directory.
No registry/core implementation or Git metadata is changed by this helper.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import time
import types
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
REPORT = Path(__file__).parent
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1g"
VERSION = "t1-20261006-d1g.1"
BASELINE = "b6417ee38ace983895d435750eb5812cd71b4758"
NEW_MODULES = [f"src/agent/runtime_roles/{name}.py" for name in (
    "coordinates", "levels", "lineage", "height_writes")]


def save(name, value):
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8", newline="\n")


def register():
    from src.agent_runtime.agent_registry import main
    path = ROOT / "src/agent_runtime/agent_versions.json"
    before = json.loads(subprocess.check_output(["git", "show", BASELINE + ":src/agent_runtime/agent_versions.json"], cwd=ROOT))
    actual = json.loads(path.read_bytes())
    temporary_directory = tempfile.TemporaryDirectory
    def local_temporary(*args, **kwargs):
        kwargs["dir"] = SCRATCH
        return temporary_directory(*args, **kwargs)
    with contextlib.redirect_stdout(io.StringIO()), patch("tempfile.TemporaryDirectory", local_temporary):
        if VERSION not in actual["versions"]:
            args = ["register", "--root", str(ROOT), "--version", VERSION]
            for name in NEW_MODULES:
                args.extend(["--add-file", "tool:" + name])
            assert main(args) == 0
        assert main(["verify", "--root", str(ROOT), "--version", VERSION]) == 0
    after = json.loads(path.read_bytes())
    assert all(after["versions"][k] == v for k, v in before["versions"].items())
    assert after["current_version"] == VERSION
    old_catalogs = before["versions"][before["current_version"]]["tool_catalog_sha256"]
    current = after["versions"][VERSION]
    assert current["tool_catalog_sha256"] == old_catalogs
    save("registration.json", {"version": VERSION, "previous_version": before["current_version"],
        "previous_versions_preserved": len(before["versions"]), "source_commit": current["source_commit"],
        "source_is_uncommitted_worktree": True, "registered_file_count": len(current["files"]),
        "added_files": NEW_MODULES, "single_model_catalogs_unchanged": True,
        "tool_catalog_sha256": current["tool_catalog_sha256"]})
    print("Registered and verified", VERSION, flush=True)


def test_files():
    selected = set(ROOT.glob("tests/test_role_*.py"))
    # References to every changed package and its shared configuration module.
    selected.update(ROOT / p for p in subprocess.check_output([
        "rg", "-l", "runtime_roles|runtime_configuration|bim_agent_role_heights", "tests", "-g", "test_*.py"],
        cwd=ROOT, text=True).splitlines())
    selected.update(ROOT / "tests" / name for name in ("test_bim_claims.py", "test_runtime_agent_registry.py"))
    return sorted(p.relative_to(ROOT).as_posix() for p in selected)


def summarize(files, *, exit_code=None, elapsed_seconds=None):
    import src.agent
    (REPORT / "checks.xml").write_text((SCRATCH / "checks.xml").read_text(encoding="utf-8"),
                                       encoding="utf-8", newline="\n")
    junit = ET.parse(SCRATCH / "checks.xml").getroot()
    suites = list(junit) if junit.tag == "testsuites" else [junit]
    counts = {k: sum(int(row.attrib.get(k, 0)) for row in suites) for k in ("tests", "failures", "errors", "skipped")}
    if exit_code is None:
        exit_code = int(bool(counts["failures"] or counts["errors"]))
    if elapsed_seconds is None:
        elapsed_seconds = sum(float(row.attrib["time"]) for row in suites)
    deliveries = []
    for path in (SCRATCH / "pytest").rglob("delivery_selection.json"):
        if path.parent.parent.name not in {"sm21-role-run", "sm24-role-run", "sm25-role-run"}:
            continue  # Other unit fixtures intentionally omit delivery fields.
        selection = json.loads(path.read_bytes())
        deliveries.append({"fixture": path.relative_to(SCRATCH / "pytest").as_posix(),
            "candidate_count": len(list(path.parent.glob("candidate_*"))),
            "candidate": selection["candidate"], "source_model_sha256": selection["source_model_sha256"]})
    save("checks.json", {"version": VERSION, "python": sys.executable, "agent_module": src.agent.__file__,
        "pytest_files": files, "pytest_options": "-n 2 --basetemp AI_agent/archive/local_backup/d1g/pytest -q --tb=short",
        "exit_code": exit_code, "counts": counts, "elapsed_seconds": round(elapsed_seconds, 2),
        "deliveries": deliveries, "model_service_requests": 0,
        "service_boundary": "Existing no-billed-calls fixture blocks providers; scripted adapters are local fixtures."})
    assert exit_code == 0, "Review checks_output.md; never relax a protective assertion to make it pass."
    assert len(deliveries) == 6 and max(row["candidate_count"] for row in deliveries) <= 24
    print("Checks and six role deliveries summarized:", counts, flush=True)


def main():
    import src.agent
    assert Path(src.agent.__file__).resolve().is_relative_to(ROOT)
    files = test_files()
    if "--summarize-only" in sys.argv:
        summarize(files)
        return
    SCRATCH.mkdir(parents=True, exist_ok=True)
    register()
    from src.agent.runtime_roles.guidance import guidance_catalog
    baseline = types.ModuleType("src.agent.runtime_roles.d1g_baseline_guidance")
    code = subprocess.check_output(["git", "show", BASELINE + ":src/agent/runtime_roles/guidance.py"], cwd=ROOT)
    exec(compile(code, str(ROOT / "src/agent/runtime_roles/guidance.py"), "exec"), baseline.__dict__)
    save("guidance_counts.json", {"before": baseline.guidance_catalog(), "after": guidance_catalog()})
    command = [sys.executable, "-m", "pytest", "-n", "2", "--basetemp", str(SCRATCH / "pytest"),
               *files, "-q", "--tb=short", "--junitxml", str(SCRATCH / "checks.xml")]
    started = time.monotonic()
    with (REPORT / "checks_output.md").open("w", encoding="utf-8", newline="\n") as log:
        log.write("```text\n")
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8")
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        exit_code = process.wait()
        log.write("```\n")
    summarize(files, exit_code=exit_code, elapsed_seconds=time.monotonic() - started)


if __name__ == "__main__":
    main()
