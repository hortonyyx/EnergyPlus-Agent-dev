"""Prototype the rule-driven fixture: strip a paired cavity's ring, then run
the audit with and without a ledger license."""
from pathlib import Path
from src.agent.judge.answer_compiler import (
    UNITS_PER_METRE, read_facts_for_compilation, reconcile_boundary_basis,
    _footprint_polygon, _wall_region, _cavity_id)
from src.agent.judge.gt_revisions import AsSignedV1
from src.agent.judge.tarch_converter_schema import (
    ConversionReportV1, TarchConversionRequestV1)

REPO = Path(__file__).resolve().parents[4]
_m, _l, signed = read_facts_for_compilation("sm25-L_anchor")
request = TarchConversionRequestV1.model_validate_json(
    (REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json").read_text())
report = ConversionReportV1.model_validate_json(
    (REPO / "case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json").read_bytes())

base = reconcile_boundary_basis(signed, report)
# RULE: the paired cavity carrying the most edges (ties -> lowest id).
proof = max(base.pairings, key=lambda p: (len(p.facts_edge_ids), p.cavity_id))
print("chosen by rule:", proof.view_id, proof.cavity_id, proof.converter_zone_id,
      "edges=", len(proof.facts_edge_ids))

view = next(v for v in signed.views if v.view_id == proof.view_id)
fp, _ = _footprint_polygon(view)
geom = fp.difference(_wall_region(view))
areas = {_cavity_id(view.view_id, p): p.area
         for p in getattr(geom, "geoms", [geom])
         if p.geom_type == "Polygon" and not p.is_empty and p.area > 0}
area = areas[proof.cavity_id]
print("cavity area m2 =", area / UNITS_PER_METRE**2,
      "above threshold?", area / UNITS_PER_METRE**2 > request.min_room_area_m2)

SPAN = {"axis": "y", "const": 1, "lo": 0, "hi": 1000, "side": 1,
        "p1": [1, 1000], "p2": [1, 0]}

def mutate(license_it):
    raw = signed.model_dump(mode="json")
    for v in raw["views"]:
        if v["view_id"] != proof.view_id:
            continue
        v["boundary_edges"] = [e for e in v["boundary_edges"]
                               if e["cavity_id"] != proof.cavity_id]
        if license_it:
            v["boundary_ring_losses"] = v["boundary_ring_losses"] + [{
                "cavity_id": proof.cavity_id, "area_units2": int(area),
                "span": SPAN, "reason": "merged_lt_3", "owner_count": None}]
    return AsSignedV1.model_validate(raw)

for label, lic in (("UNLICENSED", False), ("LICENSED", True)):
    for tl, kw in (("thr=None", {}), ("thr=5.0", {"min_room_area_m2": request.min_room_area_m2})):
        a = reconcile_boundary_basis(mutate(lic), report, **kw)
        print(f"--- {label} {tl}: passed={a.passed} paired={a.paired_edges} "
              f"acc={a.accounted_converter_zones}/{a.converter_zones}")
        for s in a.structural_failures:
            print("     F:", s)
        for e in a.exclusions:
            print("     X:", e.view_id, e.facts_cavity_id, e.converter_zone_id,
                  e.evidence, e.registered_loss_reason, e.registered_loss_area_units2)
