"""First-floor diagnosis of the interrupted sm25 GLM run (timed out with only F1 built).

Same room-identity and opening-matching rules and tolerances as
2026-09-27_sm25_full_inventory_setup/audit_inventory.py (per-floor loop body,
restricted to the first reference floor), because that audit requires both floors.
An interrupted draft is not a final result; this only says how far F1 got.
"""
import importlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, Polygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
PREFIX = "AI_agent.logs.experiments."
full = importlib.import_module(PREFIX + "2026-09-27_sm25_full_inventory_setup.audit_inventory")
cross = importlib.import_module(PREFIX + "2026-09-30_instruction_fix.evaluate_cross_case")
RUN = HERE.parent / "2026-10-02_sm25_glm_baseline"
load = lambda p: json.loads(Path(p).read_text())


def main():
    reference = load(full.HERE / "original_reference.json")
    obs = reference["floors"][0]
    delivery = load(RUN / "delivery.json")
    source = load(RUN / delivery["candidate"] / "source_model.json")
    assert source["source_model_sha256"] == delivery["source_model_sha256"]
    floor = sorted(source["floors"], key=lambda f: f["z_floor"])[0]
    assert full.digest(RUN / "images" / Path(obs["source_image"]).name) == obs["source_sha256"]

    def coordinate(value, axis):
        (p0, v0), (p1, v1) = obs["calibration"][axis + "_anchors"]
        return v0 + (value - p0) * (v1 - v0) / (p1 - p0)

    spaces = {s["id"]: Polygon(s["polygon"]) for s in source["spaces"] if s["floor_id"] == floor["id"]}
    identities = {key: [sid for sid, poly in spaces.items()
                        if poly.contains(Point(coordinate(p[0], "x"), coordinate(p[1], "y")))]
                  for key, p in obs["spaces"].items()}
    rooms = cross.room_bijection(dict(floors=[floor], spaces=[s for s in source["spaces"]
                                 if s["floor_id"] == floor["id"]]),
                                 [dict(floor_id=floor["id"], space_identity_by_interior_point=identities)], [obs])
    actual = []
    for opening in source["openings"]:
        if not any(s in spaces for s in opening["space_ids"]):
            continue
        xy = np.array(opening["vertices"])[:, :2]
        dim = int(np.argmax(np.ptp(xy, axis=0)))
        actual.append(dict(id=opening["id"], kind=opening["kind"], axis="xy"[dim],
            span=[float(xy[:, dim].min()), float(xy[:, dim].max())], cross=float(xy[:, 1 - dim].mean()),
            space_ids=opening["space_ids"], exterior=opening["exterior"]))
    costs = np.full((len(obs["apertures"]), len(actual)), 1e6)
    metrics = {}
    for i, r in enumerate(obs["apertures"]):
        span = sorted(coordinate(v, r["axis"]) for v in r["span_pixels"])
        crossing = coordinate(r["cross_pixel"], "y" if r["axis"] == "x" else "x")
        for j, a in enumerate(actual):
            if (r["kind"], r["axis"]) != (a["kind"], a["axis"]):
                continue
            along = max(abs(x - y) for x, y in zip(span, a["span"]))
            across = abs(crossing - a["cross"])
            costs[i, j] = along + across
            metrics[i, j] = (along, across)
    rows, matched_r, matched_a = [], set(), set()
    for i, j in zip(*linear_sum_assignment(costs)):
        if costs[i, j] >= 1e6:
            continue
        matched_r.add(int(i)); matched_a.add(int(j))
        r, a = obs["apertures"][i], actual[j]
        along, across = metrics[i, j]
        hosts = sorted(s for h in r["hosts"] for s in identities[h])
        exterior = len(r["hosts"]) == 1
        host_ok = (all(len(identities[h]) == 1 for h in r["hosts"]) and len(set(hosts)) == len(r["hosts"])
                   and sorted(a["space_ids"]) == hosts and a["exterior"] == exterior)
        links = [c for c in source["connections"] if c["opening_id"] == a["id"]]
        connected = None if r["kind"] != "door" else bool(host_ok and len(links) == 1 and
            sorted(links[0]["space_ids"]) == hosts and links[0]["exterior"] == exterior)
        tol = obs["tolerance"]
        position = along <= tol["along_m"] and across <= tol["external_cross_m" if exterior else "internal_cross_m"]
        rows.append(dict(reference_id=r["id"], kind=r["kind"], exterior=exterior, opening_id=a["id"],
            max_endpoint_error_m=along, perpendicular_error_m=across, position_match=bool(position),
            host_match=bool(host_ok), connection_match=connected))
    report = dict(run=RUN.name, interrupted=True, built_floors=[f["id"] for f in source["floors"]],
        first_floor=dict(rooms=rooms, reference_openings=len(obs["apertures"]), matched=len(rows),
            positions=sum(r["position_match"] for r in rows), hosts=sum(r["host_match"] for r in rows),
            door_connections=sum(r["connection_match"] is True for r in rows),
            doors=sum(r["kind"] == "door" for r in rows),
            unmatched_reference=[r["id"] for i, r in enumerate(obs["apertures"]) if i not in matched_r],
            unmatched_actual=[a["id"] for i, a in enumerate(actual) if i not in matched_a], openings=rows),
        second_floor="not built before the 3000 s limit",
        limits=["Interrupted draft, not a final result.", "First floor only; heights not assessed."])
    out = RUN / "evaluation"
    out.mkdir(exist_ok=True)
    (out / "interrupted_first_floor.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    f1 = report["first_floor"]
    print(json.dumps(dict(rooms_pass=f1["rooms"]["pass_"], room_findings=f1["rooms"]["findings"],
        reference_openings=f1["reference_openings"], matched=f1["matched"], positions=f1["positions"],
        hosts=f1["hosts"], door_connections=f"{f1['door_connections']}/{f1['doors']}",
        unmatched_reference=f1["unmatched_reference"], unmatched_actual=f1["unmatched_actual"]),
        ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
