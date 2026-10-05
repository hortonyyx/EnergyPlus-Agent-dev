"""Score finished legs of the C3 boundary node regression with the current evaluator (no model calls).

Usage: python evaluate.py <leg> [<leg> ...]   legs: sm24_claude_code, sm24_runtime_anthropic,
sm25_runtime_anthropic, sm24_qwen27b_c3. Writes evaluation/<leg>/ and evaluation_<leg>.json.
Original run files and the GT are hashed before and after and must be unchanged.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.evaluate_bim_agent import evaluate  # noqa: E402

NATIVE = Path("/root/bim-agent-runs/node-regression-c3")
LEGS = {
    "sm24_claude_code": ("sm24_anchor", HERE / "runs/sm24_claude_code"),
    "sm24_runtime_anthropic": ("sm24_anchor", NATIVE / "sm24_runtime_anthropic"),
    "sm25_runtime_anthropic": ("sm25-L_anchor", NATIVE / "sm25_runtime_anthropic"),
    "sm24_qwen27b_c3": ("sm24_anchor", NATIVE / "sm24_qwen27b_c3"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(leg):
    case, root = LEGS[leg]
    run = root / "bim" if (root / "bim").is_dir() else root
    selected = json.loads((run / "delivery.json").read_bytes())["candidate"]
    guarded = [run / "inputs.json", run / "delivery.json", ROOT / "case_tests/test_baseline/gt" / case / "gt.json"]
    guarded += sorted(run.glob("candidate_*/source_model.json"))
    before = {str(p): digest(p) for p in guarded}
    target = HERE / "evaluation" / leg
    evaluate(root, case, modelling_task="reconstruction",
             reference_scope="C3 boundary node regression; scored after the run ended, GT unchanged.", out=target)
    assert before == {str(p): digest(p) for p in guarded}, "evaluation changed a run or GT file"
    quality = json.loads((target / f"{selected}_delivery_quality.json").read_bytes())
    raw = json.loads((target / f"{selected}_partition.json").read_bytes())
    row = dict(leg=leg, case=case, candidate=selected,
               delivery=json.loads((run / "delivery.json").read_bytes()).get("selection_origin")
               or json.loads((run / "delivery_selection.json").read_bytes()).get("origin")
               if (run / "delivery_selection.json").is_file() else None,
               strict_partition=raw["comparison"]["status"], partition=quality["partition"]["status"],
               delivery_quality=quality["status"],
               openings={k: quality["opening_inventory"].get(k)
                         for k in ("reference_count", "matched", "positions", "hosts", "door_connections")},
               heights={k: quality["exterior_heights"].get(k) for k in ("expected", "matched", "within")},
               severe=[f for f in quality["retained_findings"] if f["severity"] == "severe"],
               conventions=[d["category"] for d in quality["convention_differences"]],
               report=str((target / "index.html").relative_to(ROOT)), model_requests=0)
    (HERE / f"evaluation_{leg}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: row[k] for k in ("leg", "candidate", "strict_partition", "partition",
                                          "delivery_quality", "openings", "heights")}, ensure_ascii=False))
    for finding in row["severe"]:
        print("  severe:", json.dumps(finding, ensure_ascii=False)[:300])


if __name__ == "__main__":
    for leg in sys.argv[1:]:
        score(leg)
