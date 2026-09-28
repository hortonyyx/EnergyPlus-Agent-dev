"""Re-run the unchanged GT partition comparator on saved sm21 spaces at several tolerances.

Post-hoc evaluation only: reads the reference/candidate spaces already stored in
evaluation/gt/<candidate>_partition.json and never feeds GT back to generation.
Separates object topology defects (merge/split/missing/extra) from boundary
offsets that only exceed the 0.02 m default tolerance.

Usage: PYTHONPATH=<tree> /opt/venv/bin/python3 reevaluate_partitions.py
"""
import glob
import json
import os
import re
from itertools import combinations

from shapely.geometry import Polygon
from shapely.ops import unary_union

from src.agent.judge.source_partition import compare_partitions

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
TOLERANCES = (0.02, 0.10, 0.30)
TOPOLOGY = {"source_space_split", "source_spaces_merged", "extra_source_space",
            "missing_source_space", "floor_assignment_changed", "vertical_extent_changed",
            "candidate_spaces_overlap", "invalid_candidate_space"}


def internal_lines(refs, cands, tol):
    """Same construction as partition_evidence.evaluate_partition_evidence."""
    rows = []
    for fid in sorted({s["floor_id"] for s in refs}):
        ref_polys = [Polygon(s["polygon"]) for s in refs if s["floor_id"] == fid]
        cand_polys = [Polygon(s["polygon"]) for s in cands if s["floor_id"] == fid]
        if not ref_polys or not cand_polys or any(not p.is_valid for p in cand_polys):
            continue
        common = unary_union(ref_polys).intersection(unary_union(cand_polys))
        ref_l = unary_union([a.boundary.intersection(b.boundary) for a, b in combinations(ref_polys, 2)]).intersection(common)
        cand_l = unary_union([a.boundary.intersection(b.boundary) for a, b in combinations(cand_polys, 2)]).intersection(common)
        band = common.boundary.buffer(tol + 1e-9)
        missing = ref_l.difference(cand_l.buffer(tol + 1e-9)).difference(band)
        extra = cand_l.difference(ref_l.buffer(tol + 1e-9)).difference(band)
        rows.append({"floor": fid, "missing_m": round(missing.length, 2), "extra_m": round(extra.length, 2)})
    return rows


def evaluate(path):
    part = json.load(open(path))
    refs, cands = part["reference_spaces"], part["candidate_spaces"]
    out = {}
    for tol in TOLERANCES:
        comp = compare_partitions(refs, cands, tolerance_m=tol)
        topo = sorted({f["code"] for f in comp["findings"] if f["code"] in TOPOLOGY and f["severity"] == "severe"})
        details = [
            {"code": f["code"], "ref": f.get("reference_ids"), "cand": f.get("candidate_ids")}
            for f in comp["findings"] if f["code"] in TOPOLOGY and f["severity"] == "severe"
        ]
        lines = internal_lines(refs, cands, tol)
        out[str(tol)] = {
            "object_topology": topo,
            "object_topology_details": details,
            "matched": comp["matched_count"],
            "match_status": {s: sum(1 for m in comp["matches"] if m["status"] == s) for s in ("pass", "minor", "severe")},
            "internal_missing_m": round(sum(r["missing_m"] for r in lines), 2),
            "internal_extra_m": round(sum(r["extra_m"] for r in lines), 2),
        }
    hd = [m.get("boundary_hausdorff_m") for m in part["comparison"]["matches"] if m.get("boundary_hausdorff_m") is not None]
    iou = [m.get("iou") for m in part["comparison"]["matches"] if m.get("iou") is not None]
    out["max_hausdorff_m"] = round(max(hd), 3) if hd else None
    out["min_iou"] = round(min(iou), 3) if iou else None
    out["ref_count"], out["cand_count"] = len(refs), len(cands)
    return out


def main():
    results = {}
    for run_dir in sorted(glob.glob(os.path.join(EXP, "*_sm21_*run[0-9][0-9]"))):
        num = int(re.search(r"run(\d+)$", run_dir).group(1))
        if not 53 <= num <= 83:
            continue
        summary = json.load(open(os.path.join(run_dir, "summary.json")))
        delivered = (summary.get("delivery") or {}).get("candidate")
        per_candidate = {}
        for path in sorted(glob.glob(os.path.join(run_dir, "evaluation", "gt", "candidate_*_partition.json"))):
            cand = os.path.basename(path).replace("_partition.json", "")
            per_candidate[cand] = evaluate(path)
        results[num] = {"dir": os.path.basename(run_dir), "delivered": delivered, "candidates": per_candidate}
    with open(os.path.join(HERE, "partition_tolerance_reevaluation.json"), "w") as handle:
        json.dump(results, handle, indent=1)
    print("run deliv | maxHD minIOU ref/cand | tol0.02 topo; int miss/extra | tol0.10 | tol0.30")
    for num in sorted(results):
        row = results[num]
        d = row["candidates"].get(row["delivered"])
        if not d:
            print(num, row["delivered"], "no GT file")
            continue
        cells = []
        for tol in TOLERANCES:
            t = d[str(tol)]
            cells.append(f"{','.join(t['object_topology']) or '-'}; {t['internal_missing_m']}/{t['internal_extra_m']}")
        print(f"{num} {row['delivered']} | {d['max_hausdorff_m']} {d['min_iou']} {d['ref_count']}/{d['cand_count']} | " + " | ".join(cells))


if __name__ == "__main__":
    main()
