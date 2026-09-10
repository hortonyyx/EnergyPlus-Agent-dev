"""Post-run coordinate diagnosis for the rectangular sm24 exterior-only probe.

Consumes actual source vertices and the verified typed GT, without flattening
GT to v2 or applying a candidate-fitted reflection. This is an ordered geometric
comparison, not the full typed opening-claim score or proof of image identity.
"""
from collections import defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.judge.gt import load_gt_document, gt_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--candidate", default="candidate_01")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    if not (run / "summary.json").exists():
        raise RuntimeError("wait until generation ends")
    source_path = run / args.candidate / "source_model.json"
    source = json.loads(source_path.read_text())
    gt = load_gt_document("sm24_anchor")
    spaces = {s["id"]: s for s in source["spaces"]}
    # This probe has exactly one rectangular floor and one merged source space.
    assert len(spaces) == 1 and len(source["floors"]) == 1
    space = next(iter(spaces.values()))
    xs, ys = zip(*space["polygon"])
    bounds = min(xs), min(ys), max(xs), max(ys)
    assert set(map(tuple, space["polygon"])) == {
        (bounds[0], bounds[1]), (bounds[2], bounds[1]),
        (bounds[2], bounds[3]), (bounds[0], bounds[3])}
    actual, truth = defaultdict(list), defaultdict(list)
    for opening in source["openings"]:
        assert opening["exterior"] and len(opening["space_ids"]) == 1
        vx, vy, vz = zip(*opening["vertices"])
        if max(vx) - min(vx) < 1e-8:
            assert abs(vx[0] - bounds[0]) < 1e-8 or abs(vx[0] - bounds[2]) < 1e-8
            facade = "West" if abs(vx[0] - bounds[0]) < 1e-8 else "East"
            along = vy
        else:
            assert max(vy) - min(vy) < 1e-8
            assert abs(vy[0] - bounds[1]) < 1e-8 or abs(vy[0] - bounds[3]) < 1e-8
            facade = "South" if abs(vy[0] - bounds[1]) < 1e-8 else "North"
            along = vx
        actual[(space["floor_id"], facade, opening["kind"])].append({
            "id": opening["id"], "span": [min(along), max(along)], "z": [min(vz), max(vz)]})
    boundaries = {b.id: b for floor in gt.floors for b in floor.boundary_segments}
    for opening in gt.openings:
        assert opening.z_interval is not None
        facade = boundaries[opening.boundary_segment_id].facade_family
        truth[(opening.floor_id, facade, opening.kind)].append({
            "id": opening.id,
            "span": [opening.world_along_interval.lo, opening.world_along_interval.hi],
            "z": [opening.z_interval.lo, opening.z_interval.hi]})
    comparisons, unresolved = [], []
    for key in sorted(actual.keys() | truth.keys()):
        a, b = actual[key], truth[key]
        if len(a) != len(b):
            unresolved.append({"group": key, "actual": len(a), "reference": len(b),
                               "reason": "unequal counts; no forced pairing"})
            continue
        for av, bv in zip(sorted(a, key=lambda x: x["span"]), sorted(b, key=lambda x: x["span"])):
            deltas = {field: [round(x - y, 9) for x, y in zip(av[field], bv[field])]
                      for field in ["span", "z"]}
            comparisons.append({"group": key, "source": av, "reference": bv,
                                "deltas_m": deltas,
                                "max_endpoint_delta_m": max(abs(v) for vals in deltas.values() for v in vals)})
    result = {
        "mode": "post_generation_typed_reference_coordinate_diagnosis",
        "source_model_sha256": source["source_model_sha256"],
        "reference_file_sha256": hashlib.sha256(gt_path("sm24_anchor").read_bytes()).hexdigest(),
        "pairing": "ordered within equal-count floor/facade/kind groups, no reflection or fitting",
        "limitations": ["Not the full typed opening-claim score", "Order matching does not prove visual identity",
                        "No internal layout comparison; the generator was not given a plan",
                        "No GT or this diagnosis supplied to generation"],
        "comparisons": comparisons, "unresolved": unresolved,
    }
    target = args.out or run / "evaluation/opening_coordinate_diagnostics.json"
    with target.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"compared": len(comparisons), "unresolved": unresolved,
                      "largest_deltas": sorted(comparisons, key=lambda x: -x["max_endpoint_delta_m"])[:3]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
