"""②-1d rework2: the boundary-basis exclusion branch is no longer an unbounded
hole.

Background (cross-family verdict 2026-08-30): the reconcile gate granted a
converter zone an exclusion whenever the PRODUCER's own re-derivation
(``derive_boundary_edges(view, 0.0)``) failed to yield a ring for its cavity.
That judgement is co-caused with the producer, so a co-cause failure (a real
enclosed room the producer cannot ring, or a hallucinated zone parked in a
shared non-logical cavity) was silently absorbed as a "natural NA cavity" and
the gate's headline claim ("every converter zone accounted for") stayed green.

The fix consumes the hash-covered ``boundary_ring_losses`` ledger as the
independent exclusion anchor and adds a uniqueness rule.  Every lock below is
"green anchor then red mutation": the legitimate form is asserted to pass first,
so the red is proven to come from the defect, not from a gate that reddens
everything ([[offline-fixtures-test-gate-discriminating-power]]).

Real sm25 substrate throughout (⛔ not a hand-built world): the three cavities
are the live 88.27 / 28.68 / 70.34 m² enclosed rooms whose rings today's
producer cannot derive (F-153/F-154; the ring fix is a separate line, F-155).
"""
from __future__ import annotations

import inspect
from copy import deepcopy
from pathlib import Path

import pytest

from src.agent.judge import answer_compiler as ac
from src.agent.judge.answer_compiler import (
    UNITS_PER_METRE,
    _cavity_id,
    _footprint_polygon,
    _wall_region,
    read_facts_for_compilation,
    reconcile_boundary_basis,
)
from src.agent.judge.gt_revisions import AsSignedV1
from src.agent.judge.tarch_converter_schema import (
    ConversionReportV1,
    PolygonIRV1,
    RingV1,
    TarchConversionRequestV1,
    ZoneEdgeReportV1,
    ZoneReportV1,
)

REPO = Path(__file__).resolve().parents[1]
SM25_GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor"
SM25_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"

# The three live sm25 exclusion cavities and the zones that claim them.
CAVITY_88 = "cavity:8bd127719198fd63"          # plan-F1, 88.27 m², owner_count
CAVITY_SHARED = "cavity:04e1293098b1a95a"      # plan-F1, 28.68 m², hosts z4 AND z5
CAVITY_70 = "cavity:495501ce9b36f0f3"          # plan-F2, 70.34 m², owner_count


def _real_inputs():
    _measured, _ledger, signed = read_facts_for_compilation("sm25-L_anchor")
    request = TarchConversionRequestV1.model_validate_json(
        (SM25_SOURCE / "request_as_measured.json").read_text())
    report = ConversionReportV1.model_validate_json(
        (SM25_GT / "review/conversion_report.json").read_bytes())
    return signed, request, report


def _plan_f1_view(signed):
    return next(view for view in signed.views if view.view_id == "plan-F1")


# --------------------------------------------------------------------------
# Acceptance #3 (mechanical): the exclusion decision is NOT co-caused with the
# producer.  ⛔ "rename the function and call it again" does not count, so this
# checks the whole reconcile source, not just the import line.
# --------------------------------------------------------------------------
def test_reconcile_never_re_derives_the_ring_it_judges():
    source = inspect.getsource(reconcile_boundary_basis)
    assert "derive_boundary_edges" not in source
    # the module must not even import it any more (the only prior call site)
    assert "derive_boundary_edges" not in inspect.getsource(ac).split(
        "def reconcile_boundary_basis")[0].split("class BoundaryBasisExclusionV1")[0]


# --------------------------------------------------------------------------
# Penetration #3 / acceptance #5: the three cavities go through EXPLICIT
# registration pointing at the ledger evidence, ⛔ not "既有 NA cavity".
# --------------------------------------------------------------------------
def test_three_live_cavities_are_registered_exclusions_citing_the_loss_ledger():
    signed, _request, report = _real_inputs()
    audit = reconcile_boundary_basis(signed, report)
    assert audit.passed
    assert (audit.accounted_converter_zones, audit.converter_zones) == (29, 29)
    # every exclusion is licensed by a named ledger loss, with the measured area
    # carried through as the pointer to the F-153 evidence.
    by_cavity = {(e.view_id, e.facts_cavity_id): e for e in audit.exclusions}
    assert all(e.evidence == "registered_ring_loss" for e in audit.exclusions)
    assert all(e.registered_loss_reason == "owner_count" for e in audit.exclusions)
    # 88.27 / 28.68 / 70.34 m² -> the three known-defect rooms, in units².
    assert by_cavity[("plan-F1", CAVITY_88)].registered_loss_area_units2 == 8826560000
    assert by_cavity[("plan-F1", CAVITY_SHARED)].registered_loss_area_units2 == 2868321200
    assert by_cavity[("plan-F2", CAVITY_70)].registered_loss_area_units2 == 7033920000


def test_deregistering_a_live_cavity_reddens_instead_of_silently_excluding():
    """Penetration ② (real-cause form): an above-threshold enclosed room whose
    ring is absent AND whose ledger acknowledgement is missing is a silent gap,
    not a free exclusion.  Removing the evidence must flip green -> red."""
    signed, _request, report = _real_inputs()
    # green anchor: with the ledger entry present, it is a legitimate exclusion.
    assert reconcile_boundary_basis(signed, report).passed
    assert any(e.facts_cavity_id == CAVITY_88
               for e in reconcile_boundary_basis(signed, report).exclusions)

    # red mutation: strip ONLY the 88 m² cavity's ledger loss; its ring stays
    # absent.  The exclusion is no longer licensed -> facts_boundary_ring_missing.
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        view["boundary_ring_losses"] = [
            loss for loss in view["boundary_ring_losses"]
            if loss["cavity_id"] != CAVITY_88]
    audit = reconcile_boundary_basis(AsSignedV1.model_validate(raw), report)
    assert not audit.passed
    assert (f"facts_boundary_ring_missing:plan-F1:{CAVITY_88}:converter=F1-z0"
            in audit.structural_failures)
    # the OTHER two cavities are untouched and still legitimately excluded.
    assert {e.facts_cavity_id for e in audit.exclusions} == {CAVITY_SHARED, CAVITY_70}


# --------------------------------------------------------------------------
# Penetration ① + acceptance ③ (one-cavity-many-zone uniqueness).
# --------------------------------------------------------------------------
def test_two_disjoint_rooms_may_share_one_na_cavity():
    """Green anchor for the uniqueness lock: sm25 z4 and z5 legitimately share
    one under-segmented NA cavity (disjoint interiors) and must stay green."""
    signed, _request, report = _real_inputs()
    audit = reconcile_boundary_basis(signed, report)
    assert audit.passed
    sharers = sorted(e.converter_zone_id for e in audit.exclusions
                     if e.facts_cavity_id == CAVITY_SHARED)
    assert sharers == ["F1-z4", "F1-z5"]


def test_phantom_zone_parked_on_a_real_excluded_zone_reddens():
    """Penetration ①: a hallucinated zone parked ON TOP of z5 inside the shared
    NA cavity used to be absorbed as its own exclusion (passed=True, 30/30).
    Two claimed zones cannot occupy the same space -> red."""
    signed, _request, report = _real_inputs()
    raw = report.model_dump(mode="python")
    z5 = next(z for z in raw["zones"] if z["zone_id"] == "F1-z5")
    phantom = deepcopy(z5)
    phantom["zone_id"] = "F1-halluc-in-shared-cavity"
    phantom["name"] = "halluc"
    raw["zones"].append(phantom)
    audit = reconcile_boundary_basis(signed, ConversionReportV1.model_validate(raw))
    assert not audit.passed
    assert any(item.startswith("converter_zones_overlap_in_shared_exclusion_cavity:"
                               f"plan-F1:{CAVITY_SHARED}:")
               for item in audit.structural_failures)


# --------------------------------------------------------------------------
# Acceptance #4 + N3': a by-design below-threshold cavity keeps a legit exit;
# aligning 0.0 with the production threshold removes the reverse false alarm.
# --------------------------------------------------------------------------
def _tiny_subthreshold_cavity(signed):
    view = _plan_f1_view(signed)
    footprint, _ = _footprint_polygon(view)
    geometry = footprint.difference(_wall_region(view))
    cavities = [part for part in getattr(geometry, "geoms", [geometry])
                if part.geom_type == "Polygon" and not part.is_empty and part.area > 0]
    tiny = min(cavities, key=lambda part: part.area)
    assert tiny.area / (UNITS_PER_METRE ** 2) < 0.1   # ~0.058 m² wall-nub
    return tiny, _cavity_id("plan-F1", tiny)


def _zone_over(cavity, zone_id):
    minx, miny, maxx, maxy = cavity.bounds
    pad = 0.02
    lo_x, lo_y = minx / UNITS_PER_METRE + pad, miny / UNITS_PER_METRE + pad
    hi_x, hi_y = maxx / UNITS_PER_METRE - pad, maxy / UNITS_PER_METRE - pad
    verts = [[lo_x, lo_y], [hi_x, lo_y], [hi_x, hi_y], [lo_x, hi_y]]

    def edge(p1, p2):
        return ZoneEdgeReportV1(p1=p1, p2=p2, basis="outer_skin",
                                thickness_m=0.24, offset_m=0.12,
                                source_handles=["A"])

    return ZoneReportV1(
        zone_id=zone_id, floor_id="F1", name="shaft", role="shaft",
        role_source="cad_label",
        seed_point_world_m=[(lo_x + hi_x) / 2, (lo_y + hi_y) / 2],
        polygon_m=PolygonIRV1(exterior=RingV1(vertices=verts)),
        edges=[edge(verts[0], verts[1]), edge(verts[1], verts[2]),
               edge(verts[2], verts[3]), edge(verts[3], verts[0])])


def test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold():
    signed, request, report = _real_inputs()
    tiny, tiny_id = _tiny_subthreshold_cavity(signed)
    raw = report.model_dump(mode="python")
    raw["zones"].append(_zone_over(tiny, "F1-shaft-probe").model_dump(mode="python"))
    report_with_shaft = ConversionReportV1.model_validate(raw)

    # ⭐ red first: with no threshold the gate is fail-loud -- a no-ring cavity
    # that is not in the ledger reddens (this is the aligned replacement for the
    # old derive(0.0) false alarm, N3').
    fail_loud = reconcile_boundary_basis(signed, report_with_shaft)
    assert not fail_loud.passed
    assert (f"facts_boundary_ring_missing:plan-F1:{tiny_id}:converter=F1-shaft-probe"
            in fail_loud.structural_failures)

    # ⭐ green with the production threshold: 0.058 m² < 5.0 m² -> a named
    # below_request_area_threshold exclusion, ⛔ not a red, ⛔ not a threshold
    # tuned to the number.
    assert request.min_room_area_m2 == 5.0
    aligned = reconcile_boundary_basis(
        signed, report_with_shaft, min_room_area_m2=request.min_room_area_m2)
    assert aligned.passed
    shaft = next(e for e in aligned.exclusions
                 if e.converter_zone_id == "F1-shaft-probe")
    assert shaft.evidence == "below_request_area_threshold"
    assert shaft.registered_loss_reason is None


def test_above_threshold_unregistered_cavity_still_reddens_even_with_threshold():
    """The threshold exit is ⛔ not a blanket amnesty: an above-threshold cavity
    with no ring and no ledger entry reddens even when the production threshold
    is supplied (guards against 'pass the threshold to make everything green')."""
    signed, request, report = _real_inputs()
    # deregister the 88 m² cavity, keep the ring absent, then supply the threshold.
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        view["boundary_ring_losses"] = [
            loss for loss in view["boundary_ring_losses"]
            if loss["cavity_id"] != CAVITY_88]
    audit = reconcile_boundary_basis(
        AsSignedV1.model_validate(raw), report,
        min_room_area_m2=request.min_room_area_m2)
    assert not audit.passed
    assert (f"facts_boundary_ring_missing:plan-F1:{CAVITY_88}:converter=F1-z0"
            in audit.structural_failures)
