"""Re-evaluate sm24/sm25 delivered candidates (GT partition at 0.02/0.10/0.30 m) and read original-plan checks.

Usage: PYTHONPATH=<tree> /opt/venv/bin/python3 reevaluate_sm24_sm25.py  (writes sm24_sm25_evaluation.json)
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from reevaluate_partitions import evaluate  # noqa: E402

RUNS = ["run53", "run54", "run55", "run56", "run59", "run60", "run61", "run62",
        "run63", "run64", "run65", "run66", "run67", "run68"]


def main():
    out = {}
    for rn in RUNS:
        d = glob.glob(os.path.join(EXP, "*_" + rn))[0]
        s = json.load(open(os.path.join(d, "summary.json")))
        cand = (s.get("delivery") or {}).get("candidate")
        paths = [os.path.join(d, "evaluation", f"{cand}_partition.json"), os.path.join(d, "evaluation", "partition.json")]
        p = next((x for x in paths if os.path.exists(x)), None)
        row = {"cand": cand}
        if p:
            e = evaluate(p)
            row["gt"] = {t: (e[t]["object_topology"], e[t]["internal_missing_m"], e[t]["internal_extra_m"]) for t in ("0.02", "0.1", "0.3")}
            row["gt_hd_iou"] = (e["max_hausdorff_m"], e["min_iou"], e["ref_count"], e["cand_count"])
        op = os.path.join(d, "evaluation", "original_partition.json")
        if os.path.exists(op):
            c = json.load(open(op)).get("comparison") or {}
            row["orig"] = (c.get("status"), c.get("reference_count"), c.get("candidate_count"), c.get("matched_count"),
                           sorted({f["code"] for f in c.get("findings", []) if f.get("severity") == "severe"}))
        oa = os.path.join(d, "evaluation", "original_openings.json")
        if os.path.exists(oa):
            comps = json.load(open(oa)).get("comparisons") or []
            row["orig_open_position_match"] = [sum(1 for c in comps if c.get("position_match")), len(comps)]
            row["orig_open_host_match"] = [sum(1 for c in comps if c.get("host_match")), len(comps)]
        out[rn] = row
        print(rn, json.dumps(row, ensure_ascii=False)[:400])
    json.dump(out, open(os.path.join(HERE, "sm24_sm25_evaluation.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
