"""Compare unchanged single-model bytes and isolate the one C4 response addition."""
import copy
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from tests import test_plan_drawing_differences as differences
from tests.test_role_single_parity import FIRST_REQUEST_SOURCES


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def main():
    baseline = "5349e0a0"
    relative = "src/agent/geometry/plan_drawing_differences.py"
    previous = types.ModuleType("d1b_previous_differences")
    previous.__file__ = str(ROOT / relative)
    exec(compile(subprocess.check_output(["git", "show", f"{baseline}:{relative}"], cwd=ROOT),
                 previous.__file__, "exec"), previous.__dict__)
    captured = {}
    current = differences.drawing_differences

    def compare(image, plan):
        old, new = previous.drawing_differences(image, plan), current(image, plan)
        cleaned = copy.deepcopy(new)
        modifications = []
        suffix = " " + differences.CONTINUOUS_SPACE_CHECK
        for index, row in enumerate(cleaned["items"]):
            if row.get("check", "").endswith(suffix):
                modifications.append({"item_index": index, "opening": row.get("opening"),
                                      "type": row["type"], "added_text": suffix})
                row["check"] = row["check"][:-len(suffix)]
        assert encoded(old) == encoded(cleaned)
        captured.update(before_bytes=len(encoded(old)), after_bytes=len(encoded(new)),
            before_sha256=hashlib.sha256(encoded(old)).hexdigest(),
            after_sha256=hashlib.sha256(encoded(new)).hexdigest(),
            all_other_bytes_identical=True, modifications=modifications)
        return new

    with patch.object(differences, "drawing_differences", compare):
        differences.test_sm25_gap_across_full_channel_adds_continuous_space_hint()
    first_request = {}
    for path in FIRST_REQUEST_SOURCES:
        raw = (ROOT / path).read_bytes()
        assert raw == subprocess.check_output(["git", "show", f"{baseline}:{path}"], cwd=ROOT), path
        first_request[path] = hashlib.sha256(raw).hexdigest()
    report = {"baseline": baseline, "model_or_service_calls": 0,
              "first_request_source_bytes_identical": first_request, "c4_return_difference": captured,
              "scope": "single-mode shared request sources unchanged; real sm25 flagged response changes only its check text"}
    (HERE / "single_compatibility.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(captured, ensure_ascii=False))


if __name__ == "__main__":
    main()
