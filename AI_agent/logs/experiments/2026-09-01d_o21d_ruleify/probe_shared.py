"""Prototype: two zones inside ONE licensed ringless cavity -- disjoint (green)
vs overlapping (red).  Rule-driven, guaranteed stock."""
import copy
from pathlib import Path
from src.agent.judge.answer_compiler import (
    UNITS_PER_METRE, read_facts_for_compilation, reconcile_boundary_basis,
    _footprint_polygon, _wall_region, _cavity_id)
from src.agent.judge.gt_revisions import AsSignedV1
from src.agent.judge.tarch_converter_schema import ConversionReportV1

REPO = Path(__file__).resolve().parents[4]
_m, _l, signed = read_facts_for_compilation("sm25-L_anchor")
report = ConversionReportV1.model_validate_json(
    (REPO / "case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json").read_bytes())
base = reconcile_boundary_basis(signed, report)

view_areas = {}
for v in signed.views:
    fp, _ = _footprint_polygon(v)
    g = fp.difference(_wall_region(v))
    for p in getattr(g, "geoms", [g]):
        if p.geom_type == "Polygon" and not p.is_empty and p.area > 0:
            view_areas[(v.view_id, _cavity_id(v.view_id, p))] = p.area

proof = max(base.pairings, key=lambda p: view_areas[(p.view_id, p.cavity_id)])
area = view_areas[(proof.view_id, proof.cavity_id)]
print("rule pick:", proof.view_id, proof.cavity_id, proof.converter_zone_id,
      "area_m2=", round(area / UNITS_PER_METRE**2, 3))

SPAN = {"axis": "y", "const": 1, "lo": 0, "hi": 1000, "side": 1,
        "p1": [1, 1000], "p2": [1, 0]}

raw_signed = signed.model_dump(mode="json")
for v in raw_signed["views"]:
    if v["view_id"] == proof.view_id:
        v["boundary_edges"] = [e for e in v["boundary_edges"]
                               if e["cavity_id"] != proof.cavity_id]
        v["boundary_ring_losses"] = v["boundary_ring_losses"] + [{
            "cavity_id": proof.cavity_id, "area_units2": int(area),
            "span": SPAN, "reason": "merged_lt_3", "owner_count": None}]
licensed = AsSignedV1.model_validate(raw_signed)

def two_zones(disjoint: bool):
    raw = report.model_dump(mode="python")
    zone = next(z for z in raw["zones"] if z["zone_id"] == proof.converter_zone_id)
    verts = zone["polygon_m"]["exterior"]["vertices"]
    xs = [p[0] for p in verts]; ys = [p[1] for p in verts]
    mid = (min(ys) + max(ys)) / 2.0
    lower = copy.deepcopy(zone); upper = copy.deepcopy(zone)
    upper["zone_id"] = zone["zone_id"] + "-second"
    upper["name"] = "second"
    if disjoint:
        lower["polygon_m"]["exterior"]["vertices"] = [
            [min(xs), min(ys)], [max(xs), min(ys)], [max(xs), mid], [min(xs), mid]]
        upper["polygon_m"]["exterior"]["vertices"] = [
            [min(xs), mid], [max(xs), mid], [max(xs), max(ys)], [min(xs), max(ys)]]
    raw["zones"] = [z for z in raw["zones"]
                    if z["zone_id"] != zone["zone_id"]] + [lower, upper]
    return ConversionReportV1.model_validate(raw)

for label, dis in (("DISJOINT", True), ("OVERLAPPING", False)):
    a = reconcile_boundary_basis(licensed, two_zones(dis))
    print(f"--- {label}: passed={a.passed} acc={a.accounted_converter_zones}/{a.converter_zones}")
    for s in a.structural_failures:
        print("     F:", s)
    for e in a.exclusions:
        if e.facts_cavity_id == proof.cavity_id:
            print("     X:", e.converter_zone_id, e.evidence)
