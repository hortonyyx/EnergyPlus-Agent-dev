"""Summarize pytest XML without hiding failures, skips or previous attempts."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def summarize(path):
    xml = ET.parse(path).getroot()
    files, failed = defaultdict(Counter), []
    for case in xml.iter("testcase"):
        module = case.get("classname", "<collection>").split(".")
        file = "/".join(module[:2]) + ".py" if module[0] == "tests" else module[0] + ".py"
        status = "passed" if case.get("classname") else "unreported"
        for kind in ("error", "failure", "skipped"):
            child = case.find(kind)
            if child is not None:
                status = "xfailed" if kind == "skipped" and "xfail" in child.get("type", "") else kind
                if kind in ("error", "failure"):
                    failed.append({"test": file + "::" + case.attrib["name"],
                                   "status": status, "message": child.get("message", "")})
                break
        files[file][status] += 1
    totals = Counter()
    for counts in files.values():
        totals.update(counts)
    scopes = {}
    references = ("src.agent_runtime", "src.harness_contracts", "runtime_entry",
                  "runtime_configuration", "bim_agent_budget", "bim_agent_guidance")
    consumers = {str(test.relative_to(ROOT)) for test in (ROOT / "tests").glob("test*.py")
                 if any(name in test.read_text() for name in references)}
    for label, paths in {
        "runtime_and_contracts": [p for p in files if p.startswith(("tests/test_runtime_", "tests/test_harness_"))
                                  or p == "tests/test_agent_runtime.py"],
        "bim_consumers": [p for p in files if p.startswith("tests/test_bim_")],
        "changed_module_references": sorted(consumers & files.keys()),
    }.items():
        count = Counter()
        for file in paths:
            count.update(files[file])
        scopes[label] = {"files": len(paths), "outcomes": dict(count), "paths": sorted(paths)}
    return {"xml": str(path.relative_to(HERE)),
            "suite_seconds": [float(suite.get("time", "0")) for suite in xml.iter("testsuite")],
            "files": len(files), "outcomes": dict(totals), "failed": failed,
            "referencing_files_not_collected": sorted(consumers - files.keys()),
            "scope": scopes, "by_file": {key: dict(value) for key, value in sorted(files.items())}}


if __name__ == "__main__":
    result = {path.stem: summarize(path) for path in sorted((HERE / "checks").glob("*.xml"))}
    (HERE / "validation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for name, row in result.items():
        print(name, row["outcomes"], row["suite_seconds"])
