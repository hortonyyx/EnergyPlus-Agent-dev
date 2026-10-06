"""D1h registration and scoped offline checks, with scratch confined to d1h."""

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
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1h"
BASELINE = "5927bb5f"
VERSION = "t1-20261007-d1h.4"


def save(name, value):
    (REPORT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8", newline="\n")


def register():
    from src.agent_runtime.agent_registry import main
    path = ROOT / "src/agent_runtime/agent_versions.json"
    before = json.loads(subprocess.check_output([
        "git", "--no-optional-locks", "show", BASELINE + ":src/agent_runtime/agent_versions.json"], cwd=ROOT))
    actual = json.loads(path.read_bytes())
    temporary_directory = tempfile.TemporaryDirectory
    def local_temporary(*args, **kwargs):
        kwargs["dir"] = SCRATCH
        return temporary_directory(*args, **kwargs)
    with contextlib.redirect_stdout(io.StringIO()), patch("tempfile.TemporaryDirectory", local_temporary):
        if VERSION not in actual["versions"]:
            # Initial unshipped iterations registered a target helper that was
            # replaced by Opus's E fix. Derive this file set from the main baseline;
            # retain every historical record, including those two iterations.
            actual["current_version"] = before["current_version"]
            scratch_registry = SCRATCH / "registration_input.json"
            scratch_registry.write_text(json.dumps(actual) + "\n", encoding="utf-8", newline="\n")
            assert main(["register", "--root", str(ROOT), "--registry", str(scratch_registry),
                         "--version", VERSION, "--add-file", "tool:src/agent/runtime_roles/assembly.py"]) == 0
            path.write_text(scratch_registry.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        assert main(["verify", "--root", str(ROOT), "--version", VERSION]) == 0
    after = json.loads(path.read_bytes())
    assert all(after["versions"][k] == v for k, v in before["versions"].items())
    assert after["current_version"] == VERSION
    record = after["versions"][VERSION]
    assert record["tool_catalog_sha256"] == before["versions"][before["current_version"]]["tool_catalog_sha256"]
    save("registration.json", {"version": VERSION, "baseline_version": before["current_version"],
        "previous_versions_preserved": True, "source_commit": record["source_commit"],
        "uncommitted_worktree": True, "registered_files": len(record["files"]),
        "single_model_tool_catalogs_unchanged": True, "tool_catalog_sha256": record["tool_catalog_sha256"]})
    print("Registered and verified", VERSION, flush=True)


def test_files():
    selected = set(ROOT.glob("tests/test_role_*.py"))
    selected.update(ROOT / p for p in subprocess.check_output([
        "rg", "-l", "runtime_roles|runtime_configuration|bim_agent_role_heights", "tests", "-g", "test_*.py"],
        cwd=ROOT, text=True).splitlines())
    selected.update(ROOT / "tests" / name for name in ("test_bim_claims.py", "test_runtime_agent_registry.py"))
    return sorted(p.relative_to(ROOT).as_posix() for p in selected)


def summarize(files, code=None, elapsed=None):
    import src.agent
    xml = SCRATCH / "checks.xml"
    (REPORT / "checks.xml").write_text(xml.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    junit = ET.parse(xml).getroot()
    suites = list(junit) if junit.tag == "testsuites" else [junit]
    counts = {k: sum(int(row.attrib.get(k, 0)) for row in suites) for k in ("tests", "failures", "errors", "skipped")}
    if code is None:
        code = int(bool(counts["failures"] or counts["errors"]))
    deliveries = []
    for p in (SCRATCH / "pytest/final").rglob("delivery_selection.json"):
        output = p.parent.parent
        if output.name not in {"sm21-role-run", "sm24-role-run", "sm25-role-run"}:
            continue
        selection = json.loads(p.read_bytes())
        events = [json.loads(line) for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        calls = [r["payload"]["tool_name"] for r in events if r["payload"].get("event_type") == "tool_execution"
                 and r["task_id"] == "coordinator"]
        deliveries.append({"fixture": p.relative_to(SCRATCH / "pytest/final").as_posix(),
            "saved_candidates": len(list(p.parent.glob("candidate_*/report.json"))),
            "candidate": selection["candidate"], "coordinator_tool_calls": len(calls), "tools": calls,
            "source_model_sha256": selection["source_model_sha256"]})
    save("checks.json", {"version": VERSION, "python": sys.executable, "agent_module": src.agent.__file__,
        "pytest_files": files, "counts": counts, "exit_code": code,
        "elapsed_seconds": round(elapsed or sum(float(r.attrib["time"]) for r in suites), 2),
        "deliveries": deliveries, "model_service_requests": 0,
        "service_boundary": "Provider requests blocked by suite fixture; all adapters scripted."})
    old = json.loads((REPORT.parent / "2026-10-06_role_division_d1g/checks.json").read_bytes())
    comparisons = []
    for case, floors in (("sm21", 2), ("sm24", 1), ("sm25", 2)):
        after = next(r for r in deliveries if "test_scripted_role_pipeline_" in r["fixture"] and case + "-role-run" in r["fixture"])
        before = next(r for r in old["deliveries"] if "test_scripted_role_pipeline_" in r["fixture"] and case + "-role-run" in r["fixture"])
        mechanical = floors + 4 + floors + 8 + (3 if floors > 1 else 0)
        comparisons.append({"case": case, "saved_candidates_before": before["candidate_count"],
            "saved_candidates_after": after["saved_candidates"], "coordinator_calls_before": mechanical + 5,
            "coordinator_calls_after": after["coordinator_tool_calls"], "mechanical_calls_before": mechanical,
            "mechanical_calls_after": after["tools"].count("assemble_from_readers")})
    save("comparison.json", {"baseline": BASELINE,
        "baseline_counts_source": "D1g checks.json; baseline test_role_end_to_end.py call-count assertions (expanded per floor/facade)",
        "after_counts_source": "D1h root events filtered by task_id=coordinator, and real saved candidate reports",
        "cases": comparisons})
    print("Checks", counts, "deliveries", len(deliveries), flush=True)
    assert not counts["failures"] and not counts["errors"], "Inspect checks_output.md; preserve protective assertions."
    assert len(deliveries) == 7 and max(r["saved_candidates"] for r in deliveries) <= 24


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
    baseline = types.ModuleType("src.agent.runtime_roles.d1h_baseline_guidance")
    code = subprocess.check_output(["git", "--no-optional-locks", "show", BASELINE + ":src/agent/runtime_roles/guidance.py"], cwd=ROOT)
    exec(compile(code, str(ROOT / "src/agent/runtime_roles/guidance.py"), "exec"), baseline.__dict__)
    save("guidance_counts.json", {"before": baseline.guidance_catalog(), "after": guidance_catalog()})
    command = [sys.executable, "-m", "pytest", "-n", "2", "-p", "no:cacheprovider",
        "--basetemp", str(SCRATCH / "pytest/final"), *files, "-q", "--tb=short", "--junitxml", str(SCRATCH / "checks.xml")]
    start = time.monotonic()
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
    summarize(files, exit_code, time.monotonic() - start)


if __name__ == "__main__":
    main()
