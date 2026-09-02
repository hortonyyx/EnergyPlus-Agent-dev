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
independent exclusion anchor and adds a uniqueness rule.

⭐⭐⭐ 2026-09-01, dispatch §九 (dispatcher error #58) -- THE SHAPE OF THIS FILE
--------------------------------------------------------------------------
The first version of this file pinned THE CURRENT STATE: it asserted that
*those three* cavities (88.27 / 28.68 / 70.34 m²) were registered exclusions
with *those* areas.  A criterion written that way measures the existence of the
defect, so the moment the defect is fixed the lock reddens -- and F-156 v3
(``85b96d6``) fixed two thirds of it within the day: the two corridor cavities
now yield rings and the ledger went 3 entries -> 1.

So every criterion here is now one of exactly two kinds, and says which it is:

* **RULE** -- true for any substrate, forever.  ⛔ No cavity id, no zone id and
  no measured number appears in a rule.  Fixtures are chosen BY RULE from
  whatever the substrate currently holds, and are *constructed* so the lock
  keeps its stock (and therefore its teeth) after the upstream ring producer
  improves ([[gate-teeth-direction-follows-fixture-inventory]]).
* **READING** -- a number that moves as upstream is repaired.  It is asserted
  against a SECOND, independently parsed document rather than against a
  literal, so it stays true while the number moves and exists only to make the
  movement visible.

⭐ Scope of the green anchor.  This file owns ONE branch of the audit: how a
converter zone whose facts cavity has no stored ring is accounted for.  It
deliberately does ⛔ NOT assert ``audit.passed``, because that would make every
lock here a hostage of every other condition the audit checks -- today, of the
answer-side basis switch that F-156 v3 explicitly deferred to F-157 (see
``tests/test_f156_ring_from_intersection.py``'s ``DEFERRED_PROJECTION_CODES``,
which filters the very same two codes for the very same reason).  Narrowing a
green anchor is how gates get quietly de-fanged, so the narrowing is closed by
``test_honest_substrate_raises_no_unaccounted_structural_failure`` below: any
structural failure that is neither this file's branch nor a code another lock
explicitly owns reddens loudly.

⚠️ Corollary, stated so nobody reads more into it than is there: the
``assert not audit.passed`` lines in the red halves below are, WHILE the
deferred condition is outstanding, satisfied for free -- the audit's global
verdict is already False on this substrate.  They carry no discriminating power
today and regain it when F-157 lands.  In every one of those tests the teeth are
the NAMED structural failure asserted alongside, ⛔ never the global verdict.
The mutation matrix that measures which lock reddens for which injected defect
is ``AI_agent/logs/experiments/2026-09-01d_o21d_ruleify/``.

Real sm25 substrate throughout (⛔ not a hand-built world).
"""
from __future__ import annotations

import copy
import inspect

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
from src.agent.judge.gt_schema import REPO_ROOT

CASE = "sm25-L_anchor"
SM25_GT = REPO_ROOT / "case_tests/test_baseline/gt" / CASE
SM25_SOURCE = REPO_ROOT / "case_tests/test_baseline/gt_sources" / CASE

#: The structural-failure codes this file's branch emits: everything the audit
#: says about a converter zone whose facts cavity holds no stored ring, plus the
#: branch's own completeness claim.  This is the branch's COMPLETE emission set,
#: enumerated off every ``structural.append`` in ``reconcile_boundary_basis``
#: (⛔ not a subset chosen because it happens to be empty today -- the
#: enumeration and its classification are in this file's experiment README).
#: ⭐ Whatever is not here and not in ``CODES_OWNED_BY_ANOTHER_LOCK`` reddens
#: ``test_honest_substrate_raises_no_unaccounted_structural_failure``, so a code
#: missing from this tuple cannot become a silently unguarded direction.
EXCLUSION_BRANCH_CODES = (
    "facts_boundary_ring_missing",
    "converter_zones_overlap_in_shared_exclusion_cavity",
    "converter_zone_facts_cavity_pairing_not_unique",
    "converter_zone_polygon_invalid",
    "converter_zone_unclaimed_by_facts",
    "facts_boundary_footprint_unusable",
    "boundary_exclusions_exceed_pairings_in_view",
)

#: Codes another lock owns and has explicitly deferred.  ⛔ This is a POINTER,
#: not an amnesty: the list is copied from
#: ``tests/test_f156_ring_from_intersection.py::DEFERRED_PROJECTION_CODES``,
#: where F-156 v3 named the answer-side ``outer_skin``<->``wall_axis`` switch as
#: F-157's single outstanding condition.  When F-157 lands these stop occurring
#: and nothing here changes.
CODES_OWNED_BY_ANOTHER_LOCK = (
    "facts_projected_ring_is_not_the_converter_zone",
    "facts_projected_ring_unavailable",
)

#: A schema-legal failure span for a synthesised ledger entry.  The schema
#: places no relation between a loss's span and its cavity (see
#: ``AsMeasuredBoundaryFailureSpanV1``), so this carries no claim about the
#: geometry -- it exists only to make the synthesised entry parse.
SYNTHETIC_SPAN = {"axis": "y", "const": 1, "lo": 0, "hi": 1000, "side": 1,
                  "p1": [1, 1000], "p2": [1, 0]}


# --------------------------------------------------------------------------
# Substrate + rule-driven fixture construction
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real_inputs():
    _measured, _ledger, signed = read_facts_for_compilation(CASE)
    request = TarchConversionRequestV1.model_validate_json(
        (SM25_SOURCE / "request_as_measured.json").read_text())
    report = ConversionReportV1.model_validate_json(
        (SM25_GT / "review/conversion_report.json").read_bytes())
    return signed, request, report


def _raw_cavity_areas(signed) -> dict[tuple[str, str], float]:
    """(view_id, cavity_id) -> area, recomputed the way the gate splits them."""
    areas: dict[tuple[str, str], float] = {}
    for view in signed.views:
        footprint, _ = _footprint_polygon(view)
        geometry = footprint.difference(_wall_region(view))
        for part in getattr(geometry, "geoms", [geometry]):
            if part.geom_type == "Polygon" and not part.is_empty and part.area > 0:
                areas[(view.view_id, _cavity_id(view.view_id, part))] = part.area
    return areas


def _exclusion_branch_failures(audit) -> list[str]:
    return [item for item in audit.structural_failures
            if item.startswith(EXCLUSION_BRANCH_CODES)]


def _biggest_paired_cavity(signed, report):
    """Pick a fixture BY RULE: the largest cavity that today pairs cleanly.

    ⛔ Not "cavity:<hash>".  Largest is chosen so the fixture is provably above
    the production area threshold (the tests that use it assert exactly that),
    which is what makes the below-threshold amnesty a separate, testable exit
    rather than an accident of which cavity got picked.
    """
    baseline = reconcile_boundary_basis(signed, report)
    areas = _raw_cavity_areas(signed)
    assert baseline.pairings, (
        "no cavity pairs on the honest substrate -- this file's constructed "
        "fixtures have no stock and every lock below would be vacuous")
    proof = max(baseline.pairings, key=lambda item: areas[(item.view_id, item.cavity_id)])
    return proof, areas[(proof.view_id, proof.cavity_id)]


def _strip_ring(signed, proof, area, *, licensed: bool) -> AsSignedV1:
    """Make one real cavity ringless, with or without a ledger license.

    ⭐ This is the guaranteed-stock fixture.  The honest substrate's own
    registered exclusions are consumed as upstream is repaired (3 -> 1 today,
    plausibly 0 tomorrow), so a lock that could only mutate *those* would lose
    its teeth silently.  This one holds stock for as long as ANY cavity yields
    a ring, and ``_biggest_paired_cavity`` asserts that premise.
    """
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        if view["view_id"] != proof.view_id:
            continue
        view["boundary_edges"] = [edge for edge in view["boundary_edges"]
                                  if edge["cavity_id"] != proof.cavity_id]
        if licensed:
            view["boundary_ring_losses"] = view["boundary_ring_losses"] + [{
                "cavity_id": proof.cavity_id, "area_units2": int(area),
                "span": SYNTHETIC_SPAN, "reason": "merged_lt_3",
                "owner_count": None}]
    return AsSignedV1.model_validate(raw)


def _second_zone_in_the_same_cavity(report, zone_id: str, *, disjoint: bool):
    """Put a SECOND claimed zone inside one cavity, overlapping or not."""
    raw = report.model_dump(mode="python")
    zone = next(item for item in raw["zones"] if item["zone_id"] == zone_id)
    vertices = zone["polygon_m"]["exterior"]["vertices"]
    xs = [point[0] for point in vertices]
    ys = [point[1] for point in vertices]
    middle = (min(ys) + max(ys)) / 2.0
    first = copy.deepcopy(zone)
    second = copy.deepcopy(zone)
    second["zone_id"] = f"{zone_id}-second"
    second["name"] = "second"
    if disjoint:
        first["polygon_m"]["exterior"]["vertices"] = [
            [min(xs), min(ys)], [max(xs), min(ys)], [max(xs), middle], [min(xs), middle]]
        second["polygon_m"]["exterior"]["vertices"] = [
            [min(xs), middle], [max(xs), middle], [max(xs), max(ys)], [min(xs), max(ys)]]
    raw["zones"] = [item for item in raw["zones"]
                    if item["zone_id"] != zone_id] + [first, second]
    return ConversionReportV1.model_validate(raw)


# --------------------------------------------------------------------------
# RULE.  Acceptance #3 (mechanical): the exclusion decision is NOT co-caused
# with the producer.  ⛔ "rename the function and call it again" does not count,
# so this checks the whole reconcile source, not just the import line.
# --------------------------------------------------------------------------
def test_reconcile_never_re_derives_the_ring_it_judges():
    source = inspect.getsource(reconcile_boundary_basis)
    assert "derive_boundary_edges" not in source
    # the module must not even import it any more (the only prior call site)
    assert "derive_boundary_edges" not in inspect.getsource(ac).split(
        "def reconcile_boundary_basis")[0].split("class BoundaryBasisExclusionV1")[0]


# --------------------------------------------------------------------------
# RULE.  Acceptance #5, rewritten per dispatch §九: EVERY exclusion is licensed
# by a named ledger loss it genuinely points at.  ⛔ Says nothing about WHICH
# cavities those are, or how many.
# --------------------------------------------------------------------------
def test_every_exclusion_is_licensed_by_evidence_it_actually_points_at(real_inputs):
    """An exclusion may only exist with independent evidence, and the citation
    must resolve: a ``registered_ring_loss`` must name a loss that is really in
    the hash-covered ledger, carrying the ledger's OWN reason and area.

    ⛔ The point is that the gate may not invent its own licence.  A gate that
    copied the numbers out of thin air, or cited a loss that is not in the
    ledger, reddens here whatever the cavities happen to be.  Zero exclusions
    satisfies this vacuously -- correctly so; the teeth live in
    ``test_removing_the_licence_...`` below, whose stock is constructed.
    """
    signed, _request, report = real_inputs
    audit = reconcile_boundary_basis(signed, report)

    # this file's branch is clean on the honest substrate
    assert _exclusion_branch_failures(audit) == []
    # and every converter zone has a home -- ⛔ a rule, not the number 29
    assert audit.accounted_converter_zones == audit.converter_zones

    ledger = {(view.view_id, loss.cavity_id): loss
              for view in signed.views for loss in view.boundary_ring_losses}
    for exclusion in audit.exclusions:
        key = (exclusion.view_id, exclusion.facts_cavity_id)
        if exclusion.evidence == "registered_ring_loss":
            assert key in ledger, (
                f"exclusion cites a loss that is not in the ledger: {key}")
            assert exclusion.registered_loss_reason == ledger[key].reason
            assert exclusion.registered_loss_area_units2 == ledger[key].area_units2
        else:
            assert exclusion.evidence == "below_request_area_threshold"
            assert exclusion.registered_loss_reason is None
            assert exclusion.registered_loss_area_units2 is None


def test_a_cavity_is_never_both_ringed_and_registered_as_a_loss(real_inputs):
    """RULE, and ⚠️ read the caveat: THIS ONE CANNOT CURRENTLY GO RED.

    The claim is that the two outcomes are mutually exclusive, so an exclusion
    can never be granted for a cavity that in fact has a ring (which would let a
    paired room be double-counted as an accounted absence).

    ⚠️ Measured, ⛔ not assumed: the mutation matrix
    (``AI_agent/logs/experiments/2026-09-01d_o21d_ruleify``, mode
    ``forged_licence``) shows the document schema refuses to build such a
    substrate at all -- ``AsMeasuredViewV1._ledger_identity`` raises
    ``as_measured_boundary_cavity_has_edges_and_loss``.  So the teeth here are
    the SCHEMA's, not this test's, and through the real entry point this
    assertion is structurally always green
    ([[gate-with-only-negative-assertions-is-unobservable]]).  It is kept
    deliberately and only as a cheap tripwire for that validator being relaxed
    later; ⛔ it must not be counted as coverage of the exclusion branch.
    """
    signed, _request, report = real_inputs
    for view in signed.views:
        ringed = {edge.cavity_id for edge in view.boundary_edges}
        registered = {loss.cavity_id for loss in view.boundary_ring_losses}
        assert not (ringed & registered)
    audit = reconcile_boundary_basis(signed, report)
    ringed_pairs = {(view.view_id, edge.cavity_id)
                    for view in signed.views for edge in view.boundary_edges}
    for exclusion in audit.exclusions:
        assert (exclusion.view_id, exclusion.facts_cavity_id) not in ringed_pairs


def test_honest_substrate_raises_no_unaccounted_structural_failure(real_inputs):
    """RULE, and the reason the narrowed green anchor above is not a de-fanging.

    The anchor is scoped to this file's branch, so an unrelated failure would
    otherwise pass unnoticed here.  This closes that: on the honest substrate a
    structural failure must be EITHER this branch's (and there are none) OR a
    code another lock explicitly owns.  An undeclared code reddens loudly
    ([[declare-the-dialect-plus-consumption-ledger]]).

    ⭐ When F-157 lands, ``CODES_OWNED_BY_ANOTHER_LOCK`` simply stops occurring
    and this stays green -- it never required them to be present.
    """
    signed, _request, report = real_inputs
    audit = reconcile_boundary_basis(signed, report)
    unaccounted = [item for item in audit.structural_failures
                   if not item.startswith(EXCLUSION_BRANCH_CODES)
                   and not item.startswith(CODES_OWNED_BY_ANOTHER_LOCK)]
    assert unaccounted == []
    assert _exclusion_branch_failures(audit) == []


# --------------------------------------------------------------------------
# READING (⛔ not a rule) -- dispatch §九's second half.
# --------------------------------------------------------------------------
def test_reading_the_ledger_the_gate_consumes_is_the_ledger_the_facts_layer_stores(
        real_inputs):
    """⭐ READING, ⛔ NOT A RULE.  It exists to make a moving number visible.

    The ledger size and the exclusion count both move every time the ring
    producer improves -- F-156 v3 took the ledger from 3 entries to 1, and
    F-157 may take it to 0.  So this is asserted against a SECOND, independently
    parsed document (``as_measured.json`` vs ``as_signed.json``, two files, two
    parses) instead of against a literal.  It stays true while the numbers move,
    and it reddens only if the two documents disagree -- i.e. if the gate is
    consuming a ledger that is not the one the facts layer stored.

    ⛔ Do not "fix" a change in these counts by editing a number here; there is
    no number here to edit.
    """
    signed, _request, _report = real_inputs
    measured, _ledger, _signed_again = read_facts_for_compilation(CASE)

    def ledger_of(document):
        return sorted(
            (view.view_id, loss.cavity_id, loss.reason, loss.area_units2)
            for view in document.views for loss in view.boundary_ring_losses)

    assert ledger_of(signed) == ledger_of(measured)
    # the moving reading itself, surfaced in the failure message rather than pinned
    assert len(ledger_of(signed)) == len(ledger_of(measured)), ledger_of(signed)


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  Penetration ② (real-cause form): an above-threshold
# cavity with no ring and no ledger acknowledgement is a silent gap, ⛔ not a
# free exclusion.  Green anchor first, then the red.
# --------------------------------------------------------------------------
def test_removing_the_licence_from_an_excluded_cavity_reddens(real_inputs):
    signed, request, report = real_inputs
    proof, area = _biggest_paired_cavity(signed, report)
    # the fixture proves its own premise: it is above the production threshold,
    # so the below-threshold amnesty is not what is being exercised.
    assert area / (UNITS_PER_METRE ** 2) > request.min_room_area_m2
    missing = (f"facts_boundary_ring_missing:{proof.view_id}:{proof.cavity_id}:"
               f"converter={proof.converter_zone_id}")

    # ⭐ green anchor 1: the honest substrate does not raise it at all.
    assert missing not in reconcile_boundary_basis(signed, report).structural_failures

    # ⭐ green anchor 2: ringless BUT licensed -> a legitimate exclusion whose
    # citation resolves against the ledger entry that licenses it.
    licensed = reconcile_boundary_basis(
        _strip_ring(signed, proof, area, licensed=True), report)
    assert _exclusion_branch_failures(licensed) == []
    granted = [item for item in licensed.exclusions
               if item.facts_cavity_id == proof.cavity_id]
    assert [item.evidence for item in granted] == ["registered_ring_loss"]
    assert granted[0].registered_loss_area_units2 == int(area)

    # ⭐ red: the SAME ringless cavity with the licence withheld.
    unlicensed = reconcile_boundary_basis(
        _strip_ring(signed, proof, area, licensed=False), report)
    assert missing in unlicensed.structural_failures
    assert not unlicensed.passed
    assert not [item for item in unlicensed.exclusions
                if item.facts_cavity_id == proof.cavity_id]
    # and the zone is still counted, so the gap is a NAMED red, ⛔ not a zone
    # that quietly fell out of the population.
    assert unlicensed.accounted_converter_zones == unlicensed.converter_zones


def test_deregistering_each_live_registered_exclusion_reddens(real_inputs):
    """RULE, exercised on whatever the substrate really holds today.

    ⭐ Complementary to the constructed fixture above, ⛔ not a replacement:
    this one runs on the real known-defect cavities, so it covers the real
    cause form, but its stock is consumed as upstream is repaired.  It is
    written to iterate over ``audit.exclusions`` rather than over a list of
    ids, so it neither reddens nor needs editing when that stock reaches zero.
    """
    signed, _request, report = real_inputs
    baseline = reconcile_boundary_basis(signed, report)
    live = [item for item in baseline.exclusions
            if item.evidence == "registered_ring_loss"]

    for exclusion in live:
        raw = signed.model_dump(mode="json")
        for view in raw["views"]:
            view["boundary_ring_losses"] = [
                loss for loss in view["boundary_ring_losses"]
                if not (view["view_id"] == exclusion.view_id
                        and loss["cavity_id"] == exclusion.facts_cavity_id)]
        audit = reconcile_boundary_basis(AsSignedV1.model_validate(raw), report)
        expected = (f"facts_boundary_ring_missing:{exclusion.view_id}:"
                    f"{exclusion.facts_cavity_id}:"
                    f"converter={exclusion.converter_zone_id}")
        assert expected in audit.structural_failures
        assert not audit.passed
        # the OTHER licences are untouched and still grant their exclusions.
        survivors = {(item.view_id, item.facts_cavity_id, item.converter_zone_id)
                     for item in audit.exclusions}
        assert (exclusion.view_id, exclusion.facts_cavity_id,
                exclusion.converter_zone_id) not in survivors


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  Penetration ① / acceptance #3: one licensed cavity
# may host several real rooms, but ⛔ two claimed zones may not occupy the same
# space inside it.
# --------------------------------------------------------------------------
def test_disjoint_rooms_may_share_one_licensed_cavity(real_inputs):
    """Green anchor for the uniqueness rule: an under-segmented cavity that
    hosts two rooms with disjoint interiors is legitimate and must stay green."""
    signed, _request, report = real_inputs
    proof, area = _biggest_paired_cavity(signed, report)
    licensed_facts = _strip_ring(signed, proof, area, licensed=True)
    split = _second_zone_in_the_same_cavity(
        report, proof.converter_zone_id, disjoint=True)

    audit = reconcile_boundary_basis(licensed_facts, split)
    sharers = sorted(item.converter_zone_id for item in audit.exclusions
                     if item.facts_cavity_id == proof.cavity_id)
    # the premise really holds: two distinct zones landed in the one cavity
    assert len(sharers) == 2
    assert _exclusion_branch_failures(audit) == []

    # the honest substrate's own shared cavities (if any) are green too, and
    # their sharers really are pairwise interior-disjoint.
    honest = reconcile_boundary_basis(signed, report)
    assert not [item for item in honest.structural_failures
                if item.startswith("converter_zones_overlap_in_shared_exclusion_cavity")]


def test_two_zones_overlapping_inside_one_licensed_cavity_reddens(real_inputs):
    """Penetration ①: a hallucinated zone parked ON TOP of a real excluded zone
    used to be absorbed as its own exclusion.  Two claimed zones cannot occupy
    the same space -> a named red.

    ⛔ This deliberately does not assert ``not audit.passed``: with an unrelated
    deferred condition outstanding that is currently true for free, so it would
    be a criterion with no discriminating power at all.  The named failure, and
    its absence from the disjoint anchor, are what carry the teeth.
    """
    signed, _request, report = real_inputs
    proof, area = _biggest_paired_cavity(signed, report)
    licensed_facts = _strip_ring(signed, proof, area, licensed=True)
    overlap_code = ("converter_zones_overlap_in_shared_exclusion_cavity:"
                    f"{proof.view_id}:{proof.cavity_id}:")

    disjoint = reconcile_boundary_basis(
        licensed_facts,
        _second_zone_in_the_same_cavity(report, proof.converter_zone_id,
                                        disjoint=True))
    assert not [item for item in disjoint.structural_failures
                if item.startswith(overlap_code)]

    stacked = reconcile_boundary_basis(
        licensed_facts,
        _second_zone_in_the_same_cavity(report, proof.converter_zone_id,
                                        disjoint=False))
    named = [item for item in stacked.structural_failures
             if item.startswith(overlap_code)]
    assert len(named) == 1, stacked.structural_failures
    assert named[0].endswith(f"{proof.converter_zone_id}:"
                             f"{proof.converter_zone_id}-second")


# --------------------------------------------------------------------------
# RULE.  Acceptance #4 + N3': a by-design below-threshold cavity keeps a legit
# exit; aligning 0.0 with the production threshold removes the reverse false
# alarm, and the exit is ⛔ not a blanket amnesty.
# --------------------------------------------------------------------------
def _tiny_subthreshold_cavity(signed):
    """The smallest raw cavity anywhere in the substrate, chosen BY RULE.

    ⛔ Not "the smallest one in plan-F1": naming a view is one more way for a
    fixture to be pinned to today's drawing.  The caller asserts the premise
    (that it really is below the production threshold) rather than assuming it.
    """
    best = None
    for view in signed.views:
        footprint, _ = _footprint_polygon(view)
        geometry = footprint.difference(_wall_region(view))
        for part in getattr(geometry, "geoms", [geometry]):
            if (part.geom_type != "Polygon" or part.is_empty or part.area <= 0):
                continue
            if best is None or part.area < best[0].area:
                best = (part, view)
    assert best is not None, "the substrate holds no raw cavity at all"
    tiny, view = best
    return tiny, _cavity_id(view.view_id, tiny), view


def _zone_over(cavity, zone_id, floor_id):
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
        zone_id=zone_id, floor_id=floor_id, name="shaft", role="shaft",
        role_source="cad_label",
        seed_point_world_m=[(lo_x + hi_x) / 2, (lo_y + hi_y) / 2],
        polygon_m=PolygonIRV1(exterior=RingV1(vertices=verts)),
        edges=[edge(verts[0], verts[1]), edge(verts[1], verts[2]),
               edge(verts[2], verts[3]), edge(verts[3], verts[0])])


def test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold(
        real_inputs):
    signed, request, report = real_inputs
    tiny, tiny_id, view = _tiny_subthreshold_cavity(signed)
    # the fixture proves its own premise by RULE, ⛔ not against a literal area
    assert tiny.area / (UNITS_PER_METRE ** 2) < request.min_room_area_m2
    probe_id = "shaft-probe"
    raw = report.model_dump(mode="python")
    raw["zones"].append(
        _zone_over(tiny, probe_id, view.floor_id).model_dump(mode="python"))
    report_with_shaft = ConversionReportV1.model_validate(raw)

    # ⭐ red first: with no threshold the gate is fail-loud -- a no-ring cavity
    # that is not in the ledger reddens (this is the aligned replacement for the
    # old derive(0.0) false alarm, N3').
    fail_loud = reconcile_boundary_basis(signed, report_with_shaft)
    assert (f"facts_boundary_ring_missing:{view.view_id}:{tiny_id}:"
            f"converter={probe_id}") in fail_loud.structural_failures
    assert not fail_loud.passed

    # ⭐ green with the production threshold: a named below_request_area_threshold
    # exclusion, ⛔ not a red, ⛔ not a threshold tuned to the number.
    aligned = reconcile_boundary_basis(
        signed, report_with_shaft, min_room_area_m2=request.min_room_area_m2)
    assert _exclusion_branch_failures(aligned) == []
    shaft = next(item for item in aligned.exclusions
                 if item.converter_zone_id == probe_id)
    assert shaft.evidence == "below_request_area_threshold"
    assert shaft.registered_loss_reason is None


def test_above_threshold_unlicensed_cavity_still_reddens_even_with_the_threshold(
        real_inputs):
    """The threshold exit is ⛔ not a blanket amnesty: an above-threshold cavity
    with no ring and no ledger entry reddens even when the production threshold
    is supplied (guards against 'pass the threshold to make everything green').
    """
    signed, request, report = real_inputs
    proof, area = _biggest_paired_cavity(signed, report)
    assert area / (UNITS_PER_METRE ** 2) > request.min_room_area_m2
    audit = reconcile_boundary_basis(
        _strip_ring(signed, proof, area, licensed=False), report,
        min_room_area_m2=request.min_room_area_m2)
    assert (f"facts_boundary_ring_missing:{proof.view_id}:{proof.cavity_id}:"
            f"converter={proof.converter_zone_id}") in audit.structural_failures
    assert not audit.passed


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  F-156 v4 -- the FLOODING ('灌证') direction.
# Every lock above withdraws a licence to force a red, so the mirror attack
# sails through: a producer that WRITES many true-looking losses can license
# excluding nearly every converter zone (F-156 v3 阻断 1 / ②-1d B1: 27/29 zones
# waived, ``passed=True``).  Per cavity a flooded exclusion is indistinguishable
# from a legitimate one, so the tooth is aggregate: within a view, exclusions
# may not outnumber edge-pairings -- the exception may not become the rule.
# --------------------------------------------------------------------------
def _flood(signed, report, drop_pairs):
    """Drop the stored ring of each named ``(view_id, cavity_id)`` and license
    it with a schema-legal loss whose area is the cavity's own -- exactly the
    entry a producer that just failed to ring it would write.  ⛔ No count is
    baked in; the caller picks ``drop_pairs`` BY RULE from the live pairings."""
    areas = _raw_cavity_areas(signed)
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        drop = {cavity_id for (view_id, cavity_id) in drop_pairs
                if view_id == view["view_id"]}
        if not drop:
            continue
        view["boundary_edges"] = [edge for edge in view["boundary_edges"]
                                  if edge["cavity_id"] not in drop]
        view["boundary_ring_losses"] = view["boundary_ring_losses"] + [
            {"cavity_id": cavity_id,
             "area_units2": int(areas[(view["view_id"], cavity_id)]),
             "span": SYNTHETIC_SPAN,
             "reason": "merged_span_has_no_supporting_witness",
             "owner_count": None}
            for cavity_id in sorted(drop)]
    return AsSignedV1.model_validate(raw)


def _paired_by_view(audit) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for proof in audit.pairings:
        out.setdefault(proof.view_id, []).append(proof.cavity_id)
    return out


def _flood_code_views(audit) -> set[str]:
    return {item.split(":")[1] for item in audit.structural_failures
            if item.startswith("boundary_exclusions_exceed_pairings_in_view")}


def test_flooding_the_loss_ledger_cannot_waive_the_majority_of_a_view(real_inputs):
    """§五#1 -- the balanced flood the cross-family verdict drove straight
    through.  Keep exactly ONE paired cavity in each view and license every
    other one out as a loss.  Before this tooth the audit passed with almost
    every zone waived; now every view whose exclusions outnumber its pairings is
    NAMED.  ⛔ The dropped cavities are not pinned -- chosen by the rule 'all but
    one paired cavity per view', so the lock keeps its teeth as upstream moves.
    """
    signed, _request, report = real_inputs
    baseline = reconcile_boundary_basis(signed, report)
    paired = _paired_by_view(baseline)
    assert paired and all(len(cavities) >= 2 for cavities in paired.values()), (
        "a view has <2 live pairs -- 'keep one, drop the rest' has no stock")

    # green anchor: the honest substrate validates far more than it waives, so
    # the tooth does ⛔ NOT fire there (it is not a fire-always assertion).
    assert _flood_code_views(baseline) == set()

    drop = [(view_id, cavity_id)
            for view_id, cavities in paired.items()
            for cavity_id in cavities[1:]]
    flooded = reconcile_boundary_basis(_flood(signed, report, drop), report)

    # every view is now majority-waived -> every view is named (⛔ a rule, not a
    # count: whichever views exist must all appear).
    assert _flood_code_views(flooded) == set(paired), flooded.structural_failures
    assert not flooded.passed


def test_a_flood_in_one_view_reddens_where_a_global_count_would_stay_green(real_inputs):
    """§五#1b -- a DIFFERENT shape, chosen to defeat the obvious weaker fix.

    Flood only the view with FEWER pairings (keep one so it does not go
    trivially empty) and leave the other whole.  A GLOBAL exclusion<=pairing
    count stays green -- the untouched view's pairings outnumber the flooded
    view's exclusions -- yet the flooded view has plainly stopped being
    validated.  The per-view rule names it; a global count would miss it, which
    is why the tooth is per-view ([[gate-teeth-direction-follows-fixture-inventory]]).
    """
    signed, _request, report = real_inputs
    baseline = reconcile_boundary_basis(signed, report)
    paired = _paired_by_view(baseline)
    assert len(paired) >= 2, "need two views to concentrate a flood in one"
    victim = min(paired, key=lambda view_id: len(paired[view_id]))
    assert len(paired[victim]) >= 2, "victim view has no stock to flood"

    drop = [(victim, cavity_id) for cavity_id in paired[victim][1:]]
    flooded = reconcile_boundary_basis(_flood(signed, report, drop), report)

    # a global count really would stay green: total exclusions <= total pairings.
    assert len(flooded.exclusions) <= len(flooded.pairings), (
        len(flooded.exclusions), len(flooded.pairings))
    # the per-view rule names exactly the flooded view, ⛔ not the healthy one.
    assert _flood_code_views(flooded) == {victim}, flooded.structural_failures
    assert not flooded.passed
