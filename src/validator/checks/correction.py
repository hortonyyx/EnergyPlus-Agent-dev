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

from typing import TYPE_CHECKING, Any

from src.agent.correction.geometry_validator import (
    GeometryFinding,
    validate_corrected_geometry,
)
from src.agent.correction.envelope import (
    envelope_candidates_from_elevation_widths,
    resolve_authoritative_envelope,
)
from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry.capability import (
    CHECK_CAPABILITY_PROFILE_SHAPES,
    CHECK_SCHEMA_VERSION_SUPPORTED,
    SUPPORTED_SCHEMA_VERSIONS,
    allowed_shapes,
    capability_profile_allows,
    declared_shapes,
    schema_version_of,
    schema_version_supported,
)
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus, RunProfile

if TYPE_CHECKING:
    from src.agent.execution.evidence_preflight import EvidenceDebt

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
_DEFERRED_RESIDUAL_CHECKS = (
    "correction.facade_area_residuals",
    "correction.wwr_residuals",
    "correction.area_residuals",
    "correction.unsupported_count_by_severity",
)


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
    run_profile: RunProfile = "exploratory",
    evidence_debt: EvidenceDebt | dict | None = None,
) -> CheckReport:
    rep = CheckReport(
        stage="1_correction",
        capability_profile=capability_profile,
        run_profile=run_profile,
    )

    _schema_profile_compatibility(rep, geom, capability_profile)
    for f in validate_corrected_geometry(geom, expected_zone_total=expected_zone_total):
        _add_finding(rep, f)

    _cross_image_reconcile(rep, geom, elevation_widths)
    _audit_completeness(rep, geom, raw_geom, relied_on_testdata)
    _evidence_debt_coverage(rep, geom, evidence_debt)
    _deferred_residual_placeholders(rep)
    return rep


def _schema_profile_compatibility(
    rep: CheckReport, geom: CorrectedGeometry, capability_profile: str
) -> None:
    version = schema_version_of(geom)
    if not schema_version_supported(geom):
        rep.add_fail(
            CHECK_SCHEMA_VERSION_SUPPORTED,
            CheckLayer.INVARIANT,
            f"unsupported correction schema_version {version!r}",
            evidence={
                "schema_version": version,
                "supported_versions": sorted(SUPPORTED_SCHEMA_VERSIONS),
            },
        )
        return
    rep.add_pass(
        CHECK_SCHEMA_VERSION_SUPPORTED,
        CheckLayer.INVARIANT,
        evidence={"schema_version": version},
    )

    data_shapes = declared_shapes(geom)
    profile_shapes = allowed_shapes(capability_profile)
    if not capability_profile_allows(geom, capability_profile):
        rep.add_fail(
            CHECK_CAPABILITY_PROFILE_SHAPES,
            CheckLayer.INVARIANT,
            "capability_profile does not allow all shapes declared by "
            "correction schema_version",
            evidence={
                "capability_profile": capability_profile,
                "declared_shapes": sorted(data_shapes),
                "allowed_shapes": sorted(profile_shapes),
            },
        )
        return
    rep.add_pass(
        CHECK_CAPABILITY_PROFILE_SHAPES,
        CheckLayer.INVARIANT,
        evidence={
            "capability_profile": capability_profile,
            "declared_shapes": sorted(data_shapes),
            "allowed_shapes": sorted(profile_shapes),
        },
    )


def check_evidence_debt_coverage(
    geom: CorrectedGeometry,
    evidence_debt: EvidenceDebt | dict | None,
    *,
    capability_profile: str = "rectangular",
    run_profile: RunProfile = "exploratory",
) -> CheckReport:
    rep = CheckReport(
        stage="1_correction",
        capability_profile=capability_profile,
        run_profile=run_profile,
    )
    _evidence_debt_coverage(rep, geom, evidence_debt)
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
    envelope = resolve_authoritative_envelope(
        envelope_candidates_from_elevation_widths(elevation_widths),
        footprint={"x": (min(geom.footprint_x), max(geom.footprint_x)),
                   "y": (min(geom.footprint_y), max(geom.footprint_y))},
        footprint_tolerance_m=0.10,
    )
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
            evidence={
                "mismatches": mismatches,
                "authoritative_envelope": envelope.to_dict(),
            })
    else:
        rep.add_pass("correction.cross_image_reconcile", CheckLayer.CROSS_CHECK,
                     evidence={
                         "facades_checked": len(elevation_widths),
                         "authoritative_envelope": envelope.to_dict(),
                     })


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


def _coerce_debt(evidence_debt: EvidenceDebt | dict | None) -> Any | None:
    if evidence_debt is None:
        return None
    from src.agent.execution.evidence_preflight import EvidenceDebt

    if isinstance(evidence_debt, EvidenceDebt):
        return evidence_debt
    if isinstance(evidence_debt, dict):
        return EvidenceDebt.model_validate(evidence_debt)
    return None


def _row_text(row: dict) -> str:
    return str(row)


def _audit_rows(geom: CorrectedGeometry) -> list[dict]:
    return [
        row
        for row in [*list(geom.conflicts), *list(geom.corrections)]
        if isinstance(row, dict)
    ]


def _mentions(row: dict, values: list[str]) -> bool:
    text = _row_text(row)
    return any(value and value in text for value in values)


def _covered_by_audit(item, rows: list[dict]) -> bool:
    if item.scope == "element_local":
        return bool(item.offender_ids) and all(
            any(_mentions(row, [offender]) for row in rows)
            for offender in item.offender_ids
        )
    needles = [item.check_id, item.canonical_check_id]
    if item.view:
        needles.append(item.view)
    return any(_mentions(row, needles) for row in rows)


def _evidence_debt_coverage(
    rep: CheckReport,
    geom: CorrectedGeometry,
    evidence_debt: EvidenceDebt | dict | None,
) -> None:
    """A8.3b: check only that reading evidence debt was explicitly covered.

    Element-local debt is strong enough to block in golden/regression via
    ``disposition()``. View/global debt cannot be mapped to a specific cell/window,
    so it remains advisory even under those profiles.
    """
    debt = _coerce_debt(evidence_debt)
    if debt is None or not debt.debts:
        return

    rows = _audit_rows(geom)
    element_missing = []
    advisory_missing = []
    for item in debt.debts:
        if _covered_by_audit(item, rows):
            continue
        payload = {
            "check_id": item.check_id,
            "canonical_check_id": item.canonical_check_id,
            "view": item.view,
            "message": item.message,
        }
        if item.scope == "element_local":
            element_missing.append({**payload, "offender_ids": item.offender_ids})
        else:
            advisory_missing.append(payload)

    if element_missing:
        rep.add_fail(
            "correction.evidence_debt_coverage",
            CheckLayer.CROSS_CHECK,
            f"{len(element_missing)} element-local evidence debt item(s) were not "
            "covered by conflicts/corrections",
            evidence={"scope": "element_local", "missing": element_missing},
        )
    if advisory_missing:
        rep.add_fail(
            "correction.evidence_debt_coverage",
            CheckLayer.CROSS_CHECK,
            f"{len(advisory_missing)} view/global evidence debt item(s) were not "
            "mentioned in correction audit",
            evidence={"scope": "view_global", "missing": advisory_missing},
        )
    if not element_missing and not advisory_missing:
        rep.add_pass(
            "correction.evidence_debt_coverage",
            CheckLayer.CROSS_CHECK,
            evidence={"scope": "all", "debt_items": len(debt.debts)},
        )


def _deferred_residual_placeholders(rep: CheckReport) -> None:
    """A0 residual soft checks are visible placeholders until evidence improves."""
    for check_id in _DEFERRED_RESIDUAL_CHECKS:
        rep.add(
            check_id,
            CheckStatus.NOT_APPLICABLE,
            CheckLayer.CROSS_CHECK,
            message="deferred until evidence is richer",
        )
