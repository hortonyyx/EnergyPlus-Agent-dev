"""Score a finished sm24 role-division debug run with the same evaluator as the 10-05 C3 legs (no model calls).

Usage: python evaluate.py <run> [<run> ...]   runs: names under AI_agent/archive/local_backup/role_debug.
Writes evaluation/<run>/ and evaluation_<run>.json. Run files and the GT are hashed before and after.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.evaluate_bim_agent import evaluate  # noqa: E402

RUNS = ROOT / "AI_agent/archive/local_backup/role_debug"
CASE = "sm24_anchor"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(name):
    root = RUNS / name
    run = root / "bim"
    delivery = json.loads((run / "delivery.json").read_bytes())
    selected = delivery["candidate"]
    guarded = [run / "inputs.json", run / "delivery.json", ROOT / "case_tests/test_baseline/gt" / CASE / "gt.json"]
    guarded += sorted(run.glob("candidate_*/source_model.json"))
    before = {str(p): digest(p) for p in guarded}
    target = HERE / "evaluation" / name
    evaluate(root, CASE, modelling_task="reconstruction",
             reference_scope="sm24 role-division debug; scored after the run ended, GT unchanged.", out=target)
    assert before == {str(p): digest(p) for p in guarded}, "evaluation changed a run or GT file"
    quality = json.loads((target / f"{selected}_delivery_quality.json").read_bytes())
    raw = json.loads((target / f"{selected}_partition.json").read_bytes())
    row = dict(run=name, case=CASE, candidate=selected, candidates_saved=len(list(run.glob("candidate_*"))),
               strict_partition=raw["comparison"]["status"], partition=quality["partition"]["status"],
               delivery_quality=quality["status"],
               openings={k: quality["opening_inventory"].get(k)
                         for k in ("reference_count", "matched", "positions", "hosts", "door_connections")},
               heights={k: quality["exterior_heights"].get(k) for k in ("expected", "matched", "within")},
               severe=[f for f in quality["retained_findings"] if f["severity"] == "severe"],
               conventions=[d["category"] for d in quality["convention_differences"]],
               report=str((target / "index.html").relative_to(ROOT)), model_requests=0)
    (HERE / f"evaluation_{name}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8", newline="\n")
    print(json.dumps({k: row[k] for k in ("run", "candidate", "candidates_saved", "strict_partition", "partition",
                                          "delivery_quality", "openings", "heights")}, ensure_ascii=False))
    for finding in row["severe"]:
        print("  severe:", json.dumps(finding, ensure_ascii=False)[:300])


if __name__ == "__main__":
    for name in sys.argv[1:]:
        score(name)
