"""S1 — 1_correction deterministic check adapter (M2a, gate ①).

Wraps the A0 §7 geometry validator (agent/correction/geometry_validator.py) and
the facade translator (agent/correction/facade.py) into a CheckReport, and adds
the two checks that live at the adapter level:

  - **cross-image reconcile** (flag): the reconciled footprint width/depth must
    match the elevation facade widths, when elevation reading-views are supplied.
  - **delta/audit completeness** (block): if the deterministic core changed the
    geometry (snapped ≠ raw) or the correction relied on testdata, there must be
    a sourced ``corrections``/``conflicts`` entry — so the "0_reading was wrong"
    attribution is never silently erased (the 2f corridor-split class).

Severity→layer: coverage/nondegenerate/zstack/audit = INVARIANT (block);
window-on-wall/zone-count/reconcile = CROSS_CHECK (flag).
"""

from __future__ import annotations

from src.agent.correction.geometry_validator import (
    GeometryFinding,
    validate_corrected_geometry,
)
from src.agent.correction.schema import CorrectedGeometry
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus

# Which geometry findings are hard invariants vs soft cross-checks.
_INVARIANT_CHECKS = {
    "correction.coverage",
    "correction.nondegenerate",
    "correction.zstack_continuity",
}
_CROSSCHECK_CHECKS = {
    "correction.zone_count_tripwire",
    "correction.window_on_wall",
}


def _layer_of(check_id: str) -> CheckLayer:
    return (
        CheckLayer.INVARIANT
        if check_id in _INVARIANT_CHECKS
        else CheckLayer.CROSS_CHECK
    )


def _add_finding(rep: CheckReport, f: GeometryFinding) -> None:
    layer = _layer_of(f.check_id)
    if f.ok:
        rep.add_pass(f.check_id, layer, evidence=f.evidence)
    else:
        rep.add_fail(f.check_id, layer, f.message, evidence=f.evidence)


def check_correction(
    geom: CorrectedGeometry,
    *,
    expected_zone_total: int | None = None,
    raw_geom: CorrectedGeometry | None = None,
    relied_on_testdata: bool = False,
    elevation_widths: dict[str, float] | None = None,
    capability_profile: str = "rectangular",
) -> CheckReport:
    rep = CheckReport(stage="1_correction", capability_profile=capability_profile)

    for f in validate_corrected_geometry(geom, expected_zone_total=expected_zone_total):
        _add_finding(rep, f)

    _cross_image_reconcile(rep, geom, elevation_widths)
    _audit_completeness(rep, geom, raw_geom, relied_on_testdata)
    return rep


def _cross_image_reconcile(
    rep: CheckReport,
    geom: CorrectedGeometry,
    elevation_widths: dict[str, float] | None,
) -> None:
    """Footprint width/depth vs elevation facade widths (flag)."""
    if not elevation_widths:
        rep.add("correction.cross_image_reconcile", CheckStatus.NOT_APPLICABLE,
                CheckLayer.CROSS_CHECK, message="no elevation widths supplied")
        return
    width = abs(max(geom.footprint_x) - min(geom.footprint_x))   # N/S facade width
    depth = abs(max(geom.footprint_y) - min(geom.footprint_y))   # E/W facade width
    expected = {"North": width, "South": width, "East": depth, "West": depth}
    mismatches = []
    for facade, w in elevation_widths.items():
        exp = expected.get(facade)
        if exp is None:
            continue
        if abs(w - exp) > 0.10:
            mismatches.append({"facade": facade, "elevation_width": w,
                               "footprint_width": round(exp, 3)})
    if mismatches:
        rep.add_fail(
            "correction.cross_image_reconcile", CheckLayer.CROSS_CHECK,
            f"{len(mismatches)} facade width(s) disagree with the footprint",
            evidence={"mismatches": mismatches})
    else:
        rep.add_pass("correction.cross_image_reconcile", CheckLayer.CROSS_CHECK,
                     evidence={"facades_checked": len(elevation_widths)})


def _geom_signature(geom: CorrectedGeometry) -> list:
    """Coordinate signature for detecting whether the core changed geometry."""
    return [
        [fl.name, fl.z_floor, fl.ceiling_height,
         sorted([c.id, *map(float, c.x), *map(float, c.y)] for c in fl.cells)]
        for fl in sorted(geom.floors, key=lambda f: f.name)
    ]


def _audit_completeness(
    rep: CheckReport,
    geom: CorrectedGeometry,
    raw_geom: CorrectedGeometry | None,
    relied_on_testdata: bool,
) -> None:
    """If geometry was materially changed (snapped ≠ raw) or testdata was relied
    on, there must be a sourced corrections/conflicts entry (block)."""
    changed = False
    if raw_geom is not None:
        changed = _geom_signature(geom) != _geom_signature(raw_geom)
    needs_audit = changed or relied_on_testdata
    if not needs_audit:
        rep.add("correction.audit_completeness", CheckStatus.NOT_APPLICABLE,
                CheckLayer.INVARIANT,
                message="no material change / no testdata reliance detected")
        return
    audit_entries = list(geom.corrections) + list(geom.conflicts)
    if not audit_entries:
        rep.add_fail(
            "correction.audit_completeness", CheckLayer.INVARIANT,
            "geometry was changed (or relied on testdata) but no correction/"
            "conflict was recorded — attribution to 0_reading would be erased",
            evidence={"changed": changed, "relied_on_testdata": relied_on_testdata})
        return
    # Each audit entry must be attributable — carry at least one provenance marker
    # (the A0 audit schema uses rule_id / stage / claim_type / method_profile;
    # a lighter hand-written entry may use source / reason / rule / type).
    _PROVENANCE_KEYS = {
        "source", "reason", "rule", "rule_id", "type", "claim_type", "kind",
        "what", "stage", "method_profile",
    }
    unsourced = [
        i for i, e in enumerate(audit_entries)
        if isinstance(e, dict) and not (e.keys() & _PROVENANCE_KEYS)
    ]
    if unsourced:
        rep.add_fail(
            "correction.audit_completeness", CheckLayer.INVARIANT,
            f"{len(unsourced)} correction/conflict entry(ies) lack a source/reason",
            evidence={"unsourced_indices": unsourced})
    else:
        rep.add_pass("correction.audit_completeness", CheckLayer.INVARIANT,
                     evidence={"audit_entries": len(audit_entries)})
