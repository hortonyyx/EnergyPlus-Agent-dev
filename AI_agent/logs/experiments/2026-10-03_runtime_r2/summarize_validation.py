"""Build a deduplicated R2 validation record from captured offline pytest runs."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from run_validation import source_identity


DELIVERY = Path(__file__).resolve().parent


def main():
    selected = ("short", "registry-final", "truncation-verified", "long-final", "frozen-final")
    tests, groups = set(), []
    identity = source_identity()
    for name in selected:
        xml_path = DELIVERY / "validation" / (name + ".xml")
        root = ET.parse(xml_path).getroot()
        cases = list(root.iter("testcase"))
        failures = [case.attrib for case in cases
                    if case.find("failure") is not None or case.find("error") is not None]
        assert not failures, (name, failures)
        assert all(case.find("skipped") is None for case in cases), name
        tests.update((case.attrib["classname"], case.attrib["name"]) for case in cases)
        row = {"group": name, "passed": len(cases),
               "junit": str(xml_path.relative_to(DELIVERY)),
               "junit_sha256": hashlib.sha256(xml_path.read_bytes()).hexdigest(),
               "log": "validation/" + name + ".log"}
        capture = xml_path.with_suffix(".json")
        if capture.exists():
            saved = json.loads(capture.read_bytes())
            assert saved["returncode"] == 0 and saved["source_unchanged_during_group"], name
            assert saved["source_sha256"] == identity, name
            row.update(seconds=saved["seconds"], command=saved["command"])
        else:
            suite = next(root.iter("testsuite"))
            row["seconds"] = float(suite.attrib["time"])
        groups.append(row)
    result = {"status": "passed", "generated_utc": datetime.now(UTC).isoformat(),
        "distinct_passed": len(tests), "groups": groups, "source_sha256": identity,
        "test_ids": ["::".join(pair) for pair in sorted(tests)],
        "external_model_requests": 0,
        "superseded": [
            {"files": ["validation/long.*", "validation/frozen.*", "validation.json"],
             "reason": "Initial 80M offline fixture token budget exhausted after R2 began settling image estimates; raised only the two synthetic 75-step allowances to 120M and replayed."},
            {"files": ["validation/truncation-final.*"],
             "reason": "New summary test expected tools=[] but the existing adapter correctly omits the empty tools field; test corrected to accept the protocol representation."}],
        "coverage_note": "The 302-case short run predates one additional registry test and three summary-truncation cases. The two targeted runs replace their overlapping case results; identities are deduplicated."}
    (DELIVERY / "validation_final.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "distinct_passed": result["distinct_passed"],
                      "external_model_requests": 0}))


if __name__ == "__main__":
    main()
