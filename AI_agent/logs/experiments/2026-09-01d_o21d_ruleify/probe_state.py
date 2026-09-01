"""Read out the REAL post-F156v3 audit state on sm25 (no mutation)."""
import json
from pathlib import Path
from src.agent.judge.answer_compiler import (
    UNITS_PER_METRE, read_facts_for_compilation, reconcile_boundary_basis)
from src.agent.judge.tarch_converter_schema import (
    ConversionReportV1, TarchConversionRequestV1)

REPO = Path(__file__).resolve().parents[4]
SM25_GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor"
SM25_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"

_m, _l, signed = read_facts_for_compilation("sm25-L_anchor")
request = TarchConversionRequestV1.model_validate_json(
    (SM25_SOURCE / "request_as_measured.json").read_text())
report = ConversionReportV1.model_validate_json(
    (SM25_GT / "review/conversion_report.json").read_bytes())

print("=== ledger (boundary_ring_losses) as stored in facts ===")
for v in signed.views:
    print(f"  view={v.view_id} floor={v.floor_id} n_losses={len(v.boundary_ring_losses)}")
    for loss in v.boundary_ring_losses:
        print(f"    {loss.cavity_id} reason={loss.reason} "
              f"area_units2={loss.area_units2} "
              f"area_m2={loss.area_units2/(UNITS_PER_METRE**2):.2f}")

print()
print("=== cavities that HAVE stored boundary_edges (i.e. a ring) ===")
for v in signed.views:
    ids = sorted({e.cavity_id for e in v.boundary_edges})
    print(f"  view={v.view_id} n_edges={len(v.boundary_edges)} n_ring_cavities={len(ids)}")
    for cid in ids:
        print(f"    {cid}")

for label, kwargs in (("min_room_area_m2=None", {}),
                      ("min_room_area_m2=5.0", {"min_room_area_m2": request.min_room_area_m2})):
    audit = reconcile_boundary_basis(signed, report, **kwargs)
    print()
    print(f"=== audit ({label}) ===")
    print(f"  passed={audit.passed} paired_edges={audit.paired_edges} "
          f"converter_zones={audit.converter_zones} "
          f"accounted={audit.accounted_converter_zones} rows={len(audit.rows)}")
    print(f"  exclusions ({len(audit.exclusions)}):")
    for e in audit.exclusions:
        print(f"    {e.view_id} {e.facts_cavity_id} zone={e.converter_zone_id} "
              f"evidence={e.evidence} reason={e.registered_loss_reason} "
              f"area={e.registered_loss_area_units2}")
    print(f"  structural_failures ({len(audit.structural_failures)}):")
    for s in audit.structural_failures:
        print(f"    {s}")
