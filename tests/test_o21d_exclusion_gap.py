"""②-1d rework3: the boundary-basis exclusion branch separates the two authors.

Background (cross-family verdicts 2026-08-30 .. 2026-09-02).  The reconcile gate
used to grant a converter zone a *silent* exclusion whenever a hash-covered
``boundary_ring_losses`` entry named its cavity.  But that ledger is
PRODUCER-authored -- the hash only stops a third party tampering with it, not
the producer itself writing a loss for every cavity it failed to ring -- so a
producer that floods the ledger could waive nearly every converter zone while
every per-cavity check stayed green (②-1d rework2 blocker 2 / F-156 v3 阻断 1).
An earlier per-view ``excluded > paired`` aggregate tooth tried to catch that,
but it leaked at the balanced ``excluded == paired`` point, and it also counted
the *independently provable* below-threshold drops, so an honest building with
many sub-threshold shafts went false-red (blocker 1).

rework3 splits the two authors:

* ``registered_ring_loss`` -> ⛔ FAIL-LOUD.  Every producer-written loss is its
  own NAMED structural failure
  (``converter_zone_excluded_by_producer_written_ring_loss:<view>:<cavity>:``
  ``<zone>:reason=<r>:area_units2=<a>``).  On the real sm25 substrate the sole
  surviving ledger entry is F-153 form B -- a wall coordinate 0.1 mm off its
  three siblings that keeps a fully enclosed real room from ringing (verified
  three ways in this batch's dispatch: 28.683212 m², wall
  ``w_x_99430_100630_52401_88800``, delta=1) -- so reddening it is CORRECT, and
  the red clears itself the moment that upstream defect is fixed (the producer
  then emits a ring and writes no loss).  ⛔ No cavity id or area is baked in.
  This is the '哪个方向没有锁' rule from memory: the answer was '加了就会红', so
  the defect itself was blocking the lock.
* ``below_request_area_threshold`` -> INDEPENDENTLY provable and by design
  unlimited.  The gate recomputes the raw cavity area itself and the threshold
  comes from the request (a different author), so a producer cannot forge it.
  It silently licenses an exclusion and ⛔ never counts toward any quota: honest
  sub-threshold drops, no matter how many, do not redden.

⭐ Every criterion below is one of exactly two kinds and says which it is
(dispatch §九, dispatcher error #58):

* **RULE** -- true for any substrate, forever.  ⛔ No cavity id, no zone id and
  no measured number appears in a rule.  Fixtures are chosen BY RULE from
  whatever the substrate currently holds, and are *constructed* so the lock
  keeps its stock (and its teeth) after the upstream ring producer improves
  ([[gate-teeth-direction-follows-fixture-inventory]]).
* **READING** -- a number that moves as upstream is repaired, asserted against a
  SECOND independently parsed document rather than a literal, so it stays true
  while the number moves and exists only to make the movement visible.

⭐ Scope of every green anchor.  On the real substrate the audit already carries
the F-153 form B fail-loud reds and F-157's two deferred projection reds, so a
test may ⛔ NOT assert global cleanliness or ``audit.passed`` as its tooth -- that
would make every lock a hostage of a defect it does not own
([[acceptance-bar-must-not-be-written-from-the-result]],
[[invalidation-blast-radius-must-be-scoped]]).  Each test scopes its assertion to
its OWN named code / cavity / probe zones.  The one global-completeness lock,
``test_honest_substrate_branch_reds_are_exactly_the_known_defect``, is written as
a RULE against the ledger, ⛔ not against 28.68.

Real sm25 substrate throughout (⛔ not a hand-built world).
"""
from __future__ import annotations

import inspect

import pytest
from shapely.geometry import Polygon

from src.agent.judge import answer_compiler as ac
from src.agent.judge.answer_compiler import (
    UNITS_PER_METRE,
    _cavity_id,
    _footprint_polygon,
    _wall_region,
    _world_point_to_units,
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

#: The named producer-written-ring-loss fail-loud code (task ②): a loss a
#: converter zone CONSUMES (forward pass).
PRODUCER_LOSS_CODE = "converter_zone_excluded_by_producer_written_ring_loss"

#: rework4 T1 (阻断 2): the OUTPUT-side reverse-sweep code -- a producer loss NO
#: converter zone consumes, caught by sweeping the ledger itself rather than only
#: looking it up while walking zones.
UNCONSUMED_LOSS_CODE = "producer_ring_loss_unrepresented_by_any_converter_zone"

#: The structural-failure codes this file's branch emits: everything the audit
#: says about a converter zone whose facts cavity holds no stored ring.  This is
#: the branch's COMPLETE emission set, enumerated off every ``structural.append``
#: in ``reconcile_boundary_basis``'s no-stored-ring accounting.  ⭐ Whatever is
#: not here and not in ``CODES_OWNED_BY_ANOTHER_LOCK`` reddens
#: ``test_honest_substrate_branch_reds_are_exactly_the_known_defect`` below, so a
#: code missing from this tuple cannot become a silently unguarded direction.
#: ⛔ ``boundary_exclusions_exceed_pairings_in_view`` is gone: rework3 catches the
#: flood per-loss (fail-loud), not per-view, so there is no aggregate quota.
EXCLUSION_BRANCH_CODES = (
    PRODUCER_LOSS_CODE,
    UNCONSUMED_LOSS_CODE,
    "facts_boundary_ring_missing",
    "converter_zones_overlap_in_shared_exclusion_cavity",
    "converter_zone_facts_cavity_pairing_not_unique",
    "converter_zone_polygon_invalid",
    "converter_zone_unclaimed_by_facts",
    "facts_boundary_footprint_unusable",
)

#: Codes another lock owns and has explicitly deferred.  ⛔ A POINTER, not an
#: amnesty: copied from
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
#: geometry -- it exists only to make a synthesised entry parse.
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


def _producer_loss_reds(audit) -> list[str]:
    return [item for item in audit.structural_failures
            if item.startswith(PRODUCER_LOSS_CODE)]


def _exclusion_branch_failures(audit) -> list[str]:
    return [item for item in audit.structural_failures
            if item.startswith(EXCLUSION_BRANCH_CODES)]


def _ledger_pairs(document) -> set[tuple[str, str]]:
    return {(view.view_id, loss.cavity_id)
            for view in document.views for loss in view.boundary_ring_losses}


def _biggest_paired_cavity(signed, report):
    """Pick a fixture BY RULE: the largest cavity that today pairs cleanly.

    ⛔ Not "cavity:<hash>".  Largest is chosen so the fixture is provably above
    the production area threshold (the tests that use it assert exactly that),
    making the below-threshold amnesty a separate, testable exit rather than an
    accident of which cavity got picked.
    """
    baseline = reconcile_boundary_basis(signed, report)
    areas = _raw_cavity_areas(signed)
    assert baseline.pairings, (
        "no cavity pairs on the honest substrate -- this file's constructed "
        "fixtures have no stock and every lock below would be vacuous")
    proof = max(baseline.pairings,
                key=lambda item: areas[(item.view_id, item.cavity_id)])
    return proof, areas[(proof.view_id, proof.cavity_id)]


def _strip_ring(signed, proof, area, *, licensed: bool) -> AsSignedV1:
    """Make one real cavity ringless, with or without a producer loss entry.

    ⭐ The guaranteed-stock fixture.  The substrate's own registered losses are
    consumed as upstream is repaired (1 today, plausibly 0 tomorrow), so a lock
    that could only mutate *those* would lose its teeth silently.  This one holds
    stock for as long as ANY cavity yields a ring, and ``_biggest_paired_cavity``
    asserts that premise.

    ⛔ Note the inversion vs rework2: ``licensed=True`` now produces a FAIL-LOUD
    producer-loss red, ⛔ not a green exclusion -- a producer-written loss is no
    licence.
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


def _flood(signed, report, drop_pairs):
    """Drop the stored ring of each named ``(view_id, cavity_id)`` and license it
    with a schema-legal loss whose area is the cavity's own -- exactly the entry a
    producer that just failed to ring it would write.  ⛔ No count is baked in;
    the caller picks ``drop_pairs`` BY RULE from the live pairings."""
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


def _unconsumed_raw_cavities(signed, report):
    """Raw cavities BY RULE that the FORWARD zone pass never consumes: no stored
    ring, no ledger loss, and no converter zone whose representative point lands
    in them.

    ⭐ This is the exact '无 ring、无既有 loss、无 zone 命中' cavity the cross-family
    verdict (§三) forged its silent loss onto -- the one the forward pass is
    structurally blind to, so ONLY the reverse ledger sweep can catch a loss aimed
    at it.  Returns ``[(view_id, cavity_id, area_units2_float), ...]``.  ⛔ No
    cavity hash baked in: chosen from whatever the substrate currently holds.
    """
    converter_by_floor: dict = {}
    for zone in report.zones:
        converter_by_floor.setdefault(zone.floor_id, []).append(zone)
    out = []
    for view in signed.views:
        ringed = {edge.cavity_id for edge in view.boundary_edges}
        registered = {loss.cavity_id for loss in view.boundary_ring_losses}
        footprint, _ = _footprint_polygon(view)
        geometry = footprint.difference(_wall_region(view))
        raw_by_id = {
            _cavity_id(view.view_id, part): part
            for part in getattr(geometry, "geoms", [geometry])
            if (part.geom_type == "Polygon" and not part.is_empty and part.area > 0)}
        consumed = set()
        for zone in converter_by_floor.get(view.floor_id, []):
            zone_polygon = Polygon([_world_point_to_units(pt)
                                    for pt in zone.polygon_m.exterior.vertices])
            if (zone_polygon.is_empty or not zone_polygon.is_valid
                    or zone_polygon.area <= 0):
                continue
            rep = zone_polygon.representative_point()
            matches = [cid for cid, cav in raw_by_id.items() if cav.covers(rep)]
            if len(matches) == 1:
                consumed.add(matches[0])
        for cid, part in sorted(raw_by_id.items(), key=lambda kv: kv[1].area):
            if cid not in ringed and cid not in registered and cid not in consumed:
                out.append((view.view_id, cid, part.area))
    return out


def _zone_over(cavity, zone_id, floor_id, *, y_lo=0.0, y_hi=1.0):
    """A converter zone parked inside ``cavity``'s bounds, covering the vertical
    band ``[y_lo, y_hi]`` (fractions of the cavity height) so several zones can
    share one cavity disjointly or overlapping.  ⭐ The insets are FRACTIONAL (not
    a fixed pad), so arbitrarily many thin bands stay non-degenerate and, when the
    caller leaves gaps between them, genuinely disjoint."""
    minx, miny, maxx, maxy = cavity.bounds
    span_x = (maxx - minx) / UNITS_PER_METRE
    span_y = (maxy - miny) / UNITS_PER_METRE
    x0 = minx / UNITS_PER_METRE
    y0 = miny / UNITS_PER_METRE
    lo_x = x0 + 0.1 * span_x
    hi_x = x0 + 0.9 * span_x
    lo_y = y0 + y_lo * span_y
    hi_y = y0 + y_hi * span_y
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


def _report_with_zones(report, zones):
    raw = report.model_dump(mode="python")
    raw["zones"] = raw["zones"] + [z.model_dump(mode="python") for z in zones]
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
# RULE.  Task ② + acceptance #2: EVERY producer-written ring loss is fail-loud,
# ⛔ never an exclusion -- including on the honest substrate, where the one
# surviving entry (F-153 form B) is correctly red.
# --------------------------------------------------------------------------
def test_a_producer_written_ring_loss_is_fail_loud_never_an_exclusion(real_inputs):
    """The producer's own ledger can no longer license a silent waiver.  A
    producer-written ``boundary_ring_losses`` entry surfaces as a NAMED fail-loud
    red carrying that entry's OWN cavity, reason and area, and NO exclusion in the
    audit is a registered one (the schema no longer even models that value).

    ⭐ Two halves (rework4 T2, [[acceptance-bar-must-not-be-written-from-the-result]]):
    the fail-loud RULE is proven on a CONSTRUCTED fixture that always has stock, so
    the teeth survive the real ring producer improving the live ledger to 0; the
    real-substrate part is a READING that ⛔ does NOT pin the ledger non-empty (an
    empty ledger is honestly empty and ⛔ must not redden).
    """
    signed, _request, report = real_inputs
    audit = reconcile_boundary_basis(signed, report)

    # RULE: every audit exclusion is a by-design sub-threshold drop, ⛔ never a
    # producer licence.  (0 of them on the honest substrate -- correctly.)
    for exclusion in audit.exclusions:
        assert exclusion.evidence == "below_request_area_threshold"

    # RULE: the schema itself no longer offers the producer-licence evidence value.
    assert set(ac.BoundaryBasisExclusionV1.model_fields["evidence"].annotation.__args__) == {
        "below_request_area_threshold"}

    # RULE + guaranteed stock: CONSTRUCT a producer loss (strip a real ring, write
    # a loss for that same cavity) -> a named fail-loud red carrying its own
    # fingerprint, ⛔ never an exclusion.  Independent of the live ledger, so this
    # half keeps its teeth even when the real ledger has reached 0.
    proof, area = _biggest_paired_cavity(signed, report)
    constructed = reconcile_boundary_basis(
        _strip_ring(signed, proof, area, licensed=True), report)
    assert (f"{PRODUCER_LOSS_CODE}:{proof.view_id}:{proof.cavity_id}:"
            f"{proof.converter_zone_id}:reason=merged_lt_3:area_units2={int(area)}"
            ) in constructed.structural_failures
    assert not [item for item in constructed.exclusions
                if item.facts_cavity_id == proof.cavity_id]

    # READING (⛔ NOT a rule, ⛔ no non-empty assertion): whatever the live ledger
    # holds today surfaces as a named fail-loud red -- either a converter-consumed
    # red (forward) or an unrepresented-loss red (reverse sweep).  Vacuous, and
    # correctly green, once the producer has improved the ledger to 0.
    reds = [item for item in audit.structural_failures
            if item.startswith((PRODUCER_LOSS_CODE, UNCONSUMED_LOSS_CODE))]
    for view in signed.views:
        for loss in view.boundary_ring_losses:
            assert any(
                (item.startswith(f"{PRODUCER_LOSS_CODE}:{view.view_id}:"
                                 f"{loss.cavity_id}:")
                 or item.startswith(f"{UNCONSUMED_LOSS_CODE}:{view.view_id}:"
                                    f"{loss.cavity_id}:"))
                and item.endswith(f":reason={loss.reason}:"
                                  f"area_units2={loss.area_units2}")
                for item in reds), (view.view_id, loss.cavity_id, reds)

    # RULE: every converter zone still has a home -- ⛔ a rule, not the number 29.
    assert audit.accounted_converter_zones == audit.converter_zones


def test_a_cavity_is_never_both_ringed_and_registered_as_a_loss(real_inputs):
    """RULE with real teeth (rework4 T3, verdict §九#3).

    The claim: a cavity may not carry BOTH a stored ring edge AND a producer loss
    -- admitted and lost are mutually exclusive outcomes for one cavity.  ⛔ On the
    honest substrate this is structurally always true and so cannot go red
    ([[gate-with-only-negative-assertions-is-unobservable]]); the old version
    asserted exactly that and had NO teeth (摘掉校验器仍绿).  Instead CONSTRUCT the
    forbidden object through an UNVALIDATED payload -- an object that ⛔ should not
    pass validation -- and require ``AsSignedV1.model_validate`` to raise the
    precise ``as_measured_boundary_cavity_has_edges_and_loss`` error naming that
    cavity.  Neuter that raise in ``AsMeasuredViewV1._ledger_identity`` and this
    lock reds (mutation verified in the execution log).
    """
    signed, _request, _report = real_inputs
    raw = signed.model_dump(mode="json")
    # RULE: pick any cavity that today carries a stored ring (guaranteed stock),
    # ⛔ no cavity id baked in.
    target = None
    for view in raw["views"]:
        if view["boundary_edges"]:
            target = (view, view["boundary_edges"][0]["cavity_id"])
            break
    assert target is not None, "no stored ring anywhere -- this lock has no stock"
    view, cavity_id = target

    # write a loss for the SAME cavity -> the forbidden both-outcomes object.  The
    # cavity already has an edge, so this is exactly what the schema must reject.
    view["boundary_ring_losses"] = view["boundary_ring_losses"] + [{
        "cavity_id": cavity_id, "area_units2": 1, "span": SYNTHETIC_SPAN,
        "reason": "merged_lt_3", "owner_count": None}]

    with pytest.raises(ValueError) as excinfo:
        AsSignedV1.model_validate(raw)
    message = str(excinfo.value)
    assert "as_measured_boundary_cavity_has_edges_and_loss" in message
    assert cavity_id in message


# --------------------------------------------------------------------------
# RULE.  Acceptance #3/#4 (the one global-completeness lock): on the honest
# substrate the branch's ONLY reds are producer-loss reds whose (view, cavity)
# set is EXACTLY the live ledger, and every non-branch red belongs to F-157.
# Written against the ledger, ⛔ not against 28.68, so it auto-empties when the
# defect is fixed.
# --------------------------------------------------------------------------
def test_honest_substrate_branch_reds_are_exactly_the_known_defect(real_inputs):
    """RULE, and the reason a scoped green anchor is not a de-fanging: an
    undeclared code that leaked in would show up here loudly
    ([[declare-the-dialect-plus-consumption-ledger]]).

    ⭐ It is a RULE against the ledger, not a literal: the set of cavities the
    branch reddens must equal the set of cavities the facts layer actually
    registered a loss for.  When F-153 form B is fixed the ledger empties and
    both sides go to the empty set -- the lock stays green with no edit
    ([[acceptance-bar-must-not-be-written-from-the-result]]).
    """
    signed, _request, report = real_inputs
    audit = reconcile_boundary_basis(signed, report)

    branch = _exclusion_branch_failures(audit)
    # the only branch reds today are producer-loss reds ...
    assert all(item.startswith(PRODUCER_LOSS_CODE) for item in branch), branch
    # ... and the cavities they name are EXACTLY the live ledger's cavities.
    red_pairs = {(item.split(":")[1], f"cavity:{item.split(':')[3]}")
                 for item in _producer_loss_reds(audit)}
    assert red_pairs == _ledger_pairs(signed)

    # everything that is NOT this branch is a code F-157 explicitly owns.
    non_branch = [item for item in audit.structural_failures
                  if not item.startswith(EXCLUSION_BRANCH_CODES)]
    assert all(item.startswith(CODES_OWNED_BY_ANOTHER_LOCK)
               for item in non_branch), non_branch


# --------------------------------------------------------------------------
# READING (⛔ not a rule): the ledger the gate consumes is the ledger the facts
# layer stored.  Surfaces a moving number without pinning it.
# --------------------------------------------------------------------------
def test_reading_the_ledger_the_gate_consumes_is_the_ledger_the_facts_layer_stores(
        real_inputs):
    """⭐ READING, ⛔ NOT A RULE.  Exists to make a moving number visible.

    The ledger size moves every time the ring producer improves (F-156 v3 took
    it 3 -> 1; F-157 or the F-153 fix may take it to 0).  So it is asserted
    against a SECOND, independently parsed document (``as_measured.json`` vs
    ``as_signed.json``, two files, two parses) instead of against a literal.  It
    reddens only if the two documents disagree.  ⛔ There is no number here to
    "fix" if the count changes.
    """
    signed, _request, _report = real_inputs
    measured, _ledger, _signed_again = read_facts_for_compilation(CASE)

    def ledger_of(document):
        return sorted(
            (view.view_id, loss.cavity_id, loss.reason, loss.area_units2)
            for view in document.views for loss in view.boundary_ring_losses)

    assert ledger_of(signed) == ledger_of(measured)


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  The inversion: stripping a real above-threshold
# cavity's ring and writing a producer loss for it is FAIL-LOUD, ⛔ not a green
# exclusion (rework2's ``licensed=True`` green anchor is now a red).
# --------------------------------------------------------------------------
def test_stripping_a_ring_with_a_producer_loss_is_fail_loud_not_a_green_exclusion(
        real_inputs):
    signed, request, report = real_inputs
    proof, area = _biggest_paired_cavity(signed, report)
    # the fixture proves its own premise: above the production threshold, so the
    # below-threshold amnesty is not what is being exercised here.
    assert area / (UNITS_PER_METRE ** 2) > request.min_room_area_m2

    # ⭐ green anchor: the honest substrate does not name THIS cavity at all
    # (it pairs cleanly today).
    honest = reconcile_boundary_basis(signed, report)
    assert not any(proof.cavity_id in item and item.startswith(EXCLUSION_BRANCH_CODES)
                   for item in honest.structural_failures)

    # ⭐ red 1: ringless + producer loss -> FAIL-LOUD, ⛔ not an exclusion.
    licensed = reconcile_boundary_basis(
        _strip_ring(signed, proof, area, licensed=True), report)
    expected_loss_red = (
        f"{PRODUCER_LOSS_CODE}:{proof.view_id}:{proof.cavity_id}:"
        f"{proof.converter_zone_id}:reason=merged_lt_3:area_units2={int(area)}")
    assert expected_loss_red in licensed.structural_failures
    assert not licensed.passed
    assert not [item for item in licensed.exclusions
                if item.facts_cavity_id == proof.cavity_id]
    # the zone is still accounted (named red, ⛔ not a silent drop from the pop).
    assert licensed.accounted_converter_zones == licensed.converter_zones

    # ⭐ red 2: the SAME ringless cavity with NO loss -> a plain missing-ring red
    # (a different named code, so the two authors stay distinguishable).
    unlicensed = reconcile_boundary_basis(
        _strip_ring(signed, proof, area, licensed=False), report)
    missing = (f"facts_boundary_ring_missing:{proof.view_id}:{proof.cavity_id}:"
               f"converter={proof.converter_zone_id}")
    assert missing in unlicensed.structural_failures
    assert not unlicensed.passed
    assert unlicensed.accounted_converter_zones == unlicensed.converter_zones


def test_deregistering_each_live_loss_clears_exactly_its_own_red(real_inputs):
    """RULE + READING, exercised on whatever the substrate really holds today.

    Acceptance #3: for each ledger entry the substrate really carries, removing
    it (the shape of F-153 form B being fixed: the producer would then emit a
    ring and write no loss) makes THAT entry's fail-loud red disappear and leaves
    the others.

    ⭐ READING (⛔ NOT a rule): iterates the live ledger, so it neither reddens nor
    needs editing when the stock reaches 0 (F-157 or the F-153 fix may take it
    there) -- the loop is simply vacuous then, ⛔ no non-empty assertion pins the
    ledger (rework4 T2, [[acceptance-bar-must-not-be-written-from-the-result]]).
    The fail-loud teeth of this direction live on the CONSTRUCTED fixtures
    (``test_stripping_a_ring_with_a_producer_loss_is_fail_loud_not_a_green_exclusion``),
    which have guaranteed stock.  ⛔ No cavity id or area literal anywhere.
    """
    signed, _request, report = real_inputs
    live = sorted(_ledger_pairs(signed))

    for view_id, cavity_id in live:
        raw = signed.model_dump(mode="json")
        for view in raw["views"]:
            if view["view_id"] == view_id:
                view["boundary_ring_losses"] = [
                    loss for loss in view["boundary_ring_losses"]
                    if loss["cavity_id"] != cavity_id]
        audit = reconcile_boundary_basis(AsSignedV1.model_validate(raw), report)

        # this entry's producer-loss red is gone ...
        assert not [item for item in _producer_loss_reds(audit)
                    if f":{view_id}:{cavity_id}:" in item]
        # ... but the cavity did not vanish silently: with no ring and no loss it
        # reddens as a plain missing ring instead (still accounted, still red).
        assert any(f"facts_boundary_ring_missing:{view_id}:{cavity_id}:" in item
                   for item in audit.structural_failures)
        assert audit.accounted_converter_zones == audit.converter_zones
        # ... the OTHER entries' reds survive untouched.
        for other_view, other_cavity in live:
            if (other_view, other_cavity) == (view_id, cavity_id):
                continue
            assert any(f":{other_view}:{other_cavity}:" in item
                       for item in _producer_loss_reds(audit))


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  Acceptance #1 (rework4 T1 / verdict §三): OUTPUT-side
# exhaustiveness.  A producer loss NO converter zone consumes used to be silent;
# the reverse ledger sweep now catches it.
# --------------------------------------------------------------------------
def test_a_producer_loss_no_converter_zone_consumes_is_still_fail_loud(real_inputs):
    """The forward zone pass only looked up ``loss_by_id`` while walking converter
    zones, so a producer loss on a cavity NO zone consumes was completely silent
    (the cross-family attack: ``structural_failures`` identical before and after).
    The producer-authored ledger is the authority on what failed to ring, so it is
    now the traversal START: every entry is swept and a loss aimed at an unconsumed
    cavity reddens with its OWN cavity + reason + area fingerprint, ⛔ no zone and
    no ring required ([[gate-measures-right-but-carrier-gets-swapped]]: the swapped
    carrier is the traversal start).

    ⛔ Guaranteed stock, chosen BY RULE; ⛔ no ``cavity:1bf74ff8...`` literal.
    """
    signed, _request, report = real_inputs
    unconsumed = _unconsumed_raw_cavities(signed, report)
    assert unconsumed, "no forward-unconsumed raw cavity -- this lock has no stock"
    view_id, cavity_id, area = unconsumed[0]

    # premise: today, with no loss, this cavity is completely silent -- the
    # forward pass is structurally blind to it (⛔ the exact silent gap attacked).
    baseline = reconcile_boundary_basis(signed, report)
    assert not any(cavity_id in item for item in baseline.structural_failures)

    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        if view["view_id"] == view_id:
            view["boundary_ring_losses"] = view["boundary_ring_losses"] + [{
                "cavity_id": cavity_id, "area_units2": int(area),
                "span": SYNTHETIC_SPAN,
                "reason": "merged_span_has_no_supporting_witness",
                "owner_count": None}]
    attacked = reconcile_boundary_basis(AsSignedV1.model_validate(raw), report)

    # the forged loss reds from the ledger side, fingerprinted, ⛔ though NO
    # converter zone touches it.
    assert (f"{UNCONSUMED_LOSS_CODE}:{view_id}:{cavity_id}:"
            f"reason=merged_span_has_no_supporting_witness:area_units2={int(area)}"
            ) in attacked.structural_failures
    assert not attacked.passed
    # ⛔ and it did not sneak in as a silent exclusion.
    assert not [item for item in attacked.exclusions
                if item.facts_cavity_id == cavity_id]


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  Acceptance #6 -- MY OWN different-shape attack (⛔ not
# the same shape as #1): the reverse sweep must not inherit the below-threshold
# amnesty, and it must be EXHAUSTIVE, not first-one-only.
# --------------------------------------------------------------------------
def test_own_attack_unconsumed_losses_do_not_ride_the_below_threshold_amnesty(
        real_inputs):
    """A different shape from #1.  Every forward-unconsumed cavity here is
    genuinely SUB-THRESHOLD, and the production threshold IS supplied.  A narrow
    fix that swept the ledger but skipped below-threshold cavities -- betting they
    inherit the silent ``below_request_area_threshold`` amnesty -- would leak here.
    It must not: that amnesty lives ONLY in the forward zone path (it needs a zone
    and a recomputed area); a bare ledger entry is fail-loud on its own author,
    threshold or no threshold.  Floods EVERY unconsumed cavity in one view at once,
    so it also proves the sweep is exhaustive, ⛔ not first-one-only.
    """
    signed, request, report = real_inputs
    unconsumed = _unconsumed_raw_cavities(signed, report)
    assert unconsumed, "no forward-unconsumed raw cavity -- this lock has no stock"
    first_view = unconsumed[0][0]
    batch = [(v, c, a) for (v, c, a) in unconsumed if v == first_view]
    assert len(batch) >= 2, "need >=2 unconsumed cavities to prove exhaustiveness"
    # premise: every one is genuinely below the production threshold, so the
    # amnesty really is the tempting leak being closed.
    for _v, _c, a in batch:
        assert a / (UNITS_PER_METRE ** 2) < request.min_room_area_m2

    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        if view["view_id"] == first_view:
            view["boundary_ring_losses"] = view["boundary_ring_losses"] + [{
                "cavity_id": c, "area_units2": int(a), "span": SYNTHETIC_SPAN,
                "reason": "merged_lt_3", "owner_count": None}
                for (_v, c, a) in batch]
    attacked = reconcile_boundary_basis(
        AsSignedV1.model_validate(raw), report,
        min_room_area_m2=request.min_room_area_m2)

    reds = [item for item in attacked.structural_failures
            if item.startswith(UNCONSUMED_LOSS_CODE)]
    for _v, c, a in batch:
        assert any(item.startswith(f"{UNCONSUMED_LOSS_CODE}:{first_view}:{c}:")
                   and item.endswith(f":reason=merged_lt_3:area_units2={int(a)}")
                   for item in reds), (c, reds)
    assert not attacked.passed
    # ⛔ none was laundered into a silent below_request exclusion.
    forged_ids = {c for (_v, c, a) in batch}
    assert not [item for item in attacked.exclusions
                if item.facts_cavity_id in forged_ids]


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  Task ①: honest below-threshold drops never redden,
# no matter how many -- the mirror of the removed aggregate quota.
# --------------------------------------------------------------------------
def test_below_threshold_exclusions_never_redden_no_matter_how_many(real_inputs):
    """A building with MANY sub-threshold shafts must stay green on this branch:
    below_request drops are independently provable, so they carry no quota.

    Stack N disjoint zones over the smallest cavity (N chosen large enough to
    have beaten the old ``excluded > paired`` quota) and assert none of them
    reddens and each is a named below_request exclusion.  ⛔ Scoped to the probe
    zones -- the substrate's own F-153 / F-157 reds are on other cavities and are
    not this lock's business.
    """
    signed, request, report = real_inputs
    tiny, tiny_id, view = _tiny_subthreshold_cavity(signed)
    assert tiny.area / (UNITS_PER_METRE ** 2) < request.min_room_area_m2

    # ⭐ N chosen BY RULE to exceed this view's live pairing count, so the OLD
    # per-view ``excluded > paired`` quota would definitely have fired here --
    # that is what gives this test teeth against the removed quota, ⛔ not a
    # round number picked out of the air.
    paired_here = len(_paired_by_view(reconcile_boundary_basis(signed, report))
                      .get(view.view_id, []))
    n = paired_here + 2
    probe_ids = [f"shaft-probe-{i}" for i in range(n)]
    zones = [_zone_over(tiny, probe_ids[i], view.floor_id,
                        y_lo=i / n + 0.005, y_hi=(i + 1) / n - 0.005)
             for i in range(n)]
    report_with_shafts = _report_with_zones(report, zones)

    audit = reconcile_boundary_basis(
        signed, report_with_shafts, min_room_area_m2=request.min_room_area_m2)

    # every probe is a named below_request exclusion ...
    probe_exclusions = [item for item in audit.exclusions
                        if item.converter_zone_id in set(probe_ids)]
    assert sorted(item.converter_zone_id for item in probe_exclusions) == sorted(probe_ids)
    assert all(item.evidence == "below_request_area_threshold"
               for item in probe_exclusions)
    # ... and NONE of them reddens (no code names a probe zone or the tiny
    # cavity as a failure of this branch).
    assert not [item for item in audit.structural_failures
                if any(pid in item for pid in probe_ids)]
    # ... and the removed aggregate quota does not resurrect: even with
    # exclusions outnumbering pairings in this view, ⛔ no per-view quota red.
    assert not [item for item in audit.structural_failures
                if item.startswith("boundary_exclusions_exceed_pairings_in_view")]


def test_disjoint_rooms_may_share_one_below_threshold_cavity(real_inputs):
    """Green anchor for the uniqueness rule: an under-segmented sub-threshold
    cavity that hosts two rooms with disjoint interiors is legitimate and stays
    green."""
    signed, request, report = real_inputs
    tiny, tiny_id, view = _tiny_subthreshold_cavity(signed)
    assert tiny.area / (UNITS_PER_METRE ** 2) < request.min_room_area_m2

    zones = [_zone_over(tiny, "shaft-a", view.floor_id, y_lo=0.0, y_hi=0.45),
             _zone_over(tiny, "shaft-b", view.floor_id, y_lo=0.55, y_hi=1.0)]
    audit = reconcile_boundary_basis(
        signed, _report_with_zones(report, zones),
        min_room_area_m2=request.min_room_area_m2)

    sharers = sorted(item.converter_zone_id for item in audit.exclusions
                     if item.facts_cavity_id == tiny_id)
    assert sharers == ["shaft-a", "shaft-b"]  # the premise really holds
    assert not [item for item in audit.structural_failures
                if item.startswith("converter_zones_overlap_in_shared_exclusion_cavity")]


def test_two_zones_overlapping_inside_one_below_threshold_cavity_reddens(real_inputs):
    """Penetration ①: a hallucinated zone parked ON TOP of a real below-threshold
    zone used to be absorbed as its own exclusion.  Two claimed zones cannot
    occupy the same space -> a named red.

    ⛔ Does not assert ``not audit.passed`` -- the honest substrate is already
    False for free (F-153 / F-157), so the global verdict carries no
    discriminating power here.  The named overlap failure, and its absence from
    the disjoint anchor, are the teeth.
    """
    signed, request, report = real_inputs
    tiny, tiny_id, view = _tiny_subthreshold_cavity(signed)
    assert tiny.area / (UNITS_PER_METRE ** 2) < request.min_room_area_m2
    overlap_code = ("converter_zones_overlap_in_shared_exclusion_cavity:"
                    f"{view.view_id}:{tiny_id}:")

    disjoint = reconcile_boundary_basis(
        signed,
        _report_with_zones(report, [
            _zone_over(tiny, "shaft-a", view.floor_id, y_lo=0.0, y_hi=0.45),
            _zone_over(tiny, "shaft-b", view.floor_id, y_lo=0.55, y_hi=1.0)]),
        min_room_area_m2=request.min_room_area_m2)
    assert not [item for item in disjoint.structural_failures
                if item.startswith(overlap_code)]

    stacked = reconcile_boundary_basis(
        signed,
        _report_with_zones(report, [
            _zone_over(tiny, "shaft-a", view.floor_id, y_lo=0.0, y_hi=1.0),
            _zone_over(tiny, "shaft-b", view.floor_id, y_lo=0.0, y_hi=1.0)]),
        min_room_area_m2=request.min_room_area_m2)
    named = [item for item in stacked.structural_failures
             if item.startswith(overlap_code)]
    assert len(named) == 1, stacked.structural_failures
    assert named[0].endswith("shaft-a:shaft-b")


# --------------------------------------------------------------------------
# RULE.  Task ① + N3': a by-design below-threshold cavity keeps a legit exit
# only WITH the production threshold; the exit is ⛔ not a blanket amnesty.
# --------------------------------------------------------------------------
def test_below_threshold_cavity_has_a_legit_exit_only_with_the_production_threshold(
        real_inputs):
    signed, request, report = real_inputs
    tiny, tiny_id, view = _tiny_subthreshold_cavity(signed)
    assert tiny.area / (UNITS_PER_METRE ** 2) < request.min_room_area_m2
    probe_id = "shaft-probe"
    report_with_shaft = _report_with_zones(
        report, [_zone_over(tiny, probe_id, view.floor_id)])

    # ⭐ red: with NO threshold the gate is fail-loud -- a no-ring, no-loss cavity
    # reddens (the aligned replacement for the old derive(0.0) false alarm, N3').
    fail_loud = reconcile_boundary_basis(signed, report_with_shaft)
    assert (f"facts_boundary_ring_missing:{view.view_id}:{tiny_id}:"
            f"converter={probe_id}") in fail_loud.structural_failures

    # ⭐ green: WITH the production threshold, a named below_request exclusion,
    # ⛔ not a red, ⛔ not a threshold tuned to the number.
    aligned = reconcile_boundary_basis(
        signed, report_with_shaft, min_room_area_m2=request.min_room_area_m2)
    shaft = next(item for item in aligned.exclusions
                 if item.converter_zone_id == probe_id)
    assert shaft.evidence == "below_request_area_threshold"
    assert not [item for item in aligned.structural_failures if probe_id in item]


def test_above_threshold_unlicensed_cavity_still_reddens_even_with_the_threshold(
        real_inputs):
    """The threshold exit is ⛔ not a blanket amnesty: an above-threshold cavity
    with no ring and no ledger entry reddens even when the production threshold is
    supplied (guards against 'pass the threshold to make everything green')."""
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
# RULE + guaranteed stock.  §五#2 -- the FLOODING ('灌证') direction, now caught
# PER-LOSS.  A producer that WRITES many true-looking losses no longer waives a
# view; every loss is its own named fail-loud red.
# --------------------------------------------------------------------------
def _paired_by_view(audit) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for proof in audit.pairings:
        out.setdefault(proof.view_id, []).append(proof.cavity_id)
    return out


def test_flooding_the_loss_ledger_is_fail_loud_per_loss(real_inputs):
    """§五#2 -- the balanced flood the cross-family verdict drove straight through
    the rework2 per-view quota.  Keep exactly ONE paired cavity per view and
    license every other one out as a loss.  Under rework2 the audit passed with
    almost every zone waived; now every dropped cavity is its OWN named fail-loud
    red -- the count of reds equals the count of forged losses.  ⛔ The dropped
    cavities are chosen by the rule 'all but one paired cavity per view', so the
    lock keeps its teeth as upstream moves; ⛔ no count is pinned.
    """
    signed, _request, report = real_inputs
    baseline = reconcile_boundary_basis(signed, report)
    paired = _paired_by_view(baseline)
    assert paired and all(len(cavities) >= 2 for cavities in paired.values()), (
        "a view has <2 live pairs -- 'keep one, drop the rest' has no stock")

    drop = [(view_id, cavity_id)
            for view_id, cavities in paired.items()
            for cavity_id in cavities[1:]]
    flooded = reconcile_boundary_basis(_flood(signed, report, drop), report)

    # each forged loss is its own named fail-loud red -- ⛔ not silently waived.
    reds = _producer_loss_reds(flooded)
    flooded_pairs = {(item.split(":")[1], f"cavity:{item.split(':')[3]}")
                     for item in reds}
    for view_id, cavity_id in drop:
        assert (view_id, cavity_id) in flooded_pairs, (view_id, cavity_id)
    assert not flooded.passed
    # ⛔ NO exclusion was granted for any flooded cavity (they are reds, not waivers).
    assert not [item for item in flooded.exclusions
                if (item.view_id, item.facts_cavity_id) in set(drop)]


def test_a_single_balanced_producer_loss_still_reddens(real_inputs):
    """§五#2, the exact point the old quota leaked: ``excluded == paired``.

    Drop ONE paired cavity and license it -- the most balanced flood possible.
    The rework2 per-view cut only fired on ``excluded > paired`` and so waved
    this through; fail-loud does not care about balance -- one forged loss is one
    named red.
    """
    signed, _request, report = real_inputs
    proof, area = _biggest_paired_cavity(signed, report)
    flooded = reconcile_boundary_basis(
        _flood(signed, report, [(proof.view_id, proof.cavity_id)]), report)

    assert any(item.startswith(f"{PRODUCER_LOSS_CODE}:{proof.view_id}:"
                               f"{proof.cavity_id}:")
               for item in flooded.structural_failures)
    assert not flooded.passed
    assert not [item for item in flooded.exclusions
                if item.facts_cavity_id == proof.cavity_id]


# --------------------------------------------------------------------------
# RULE + guaranteed stock.  §五#5 -- MY OWN different-shape attack: the SEAM
# between the two authors.  A producer loss must not be launderable into the
# silent below-threshold exit by aiming it at a genuinely sub-threshold cavity
# and supplying the threshold.  The producer-author branch must win first.
# --------------------------------------------------------------------------
def test_own_attack_a_producer_loss_cannot_masquerade_as_a_below_threshold_drop(
        real_inputs):
    """A new attack, not a re-run of the flood.  The one silent exit left is
    ``below_request_area_threshold``.  So the natural evasion is: aim a
    producer-written loss at a cavity that WOULD qualify for that silent exit (a
    real sub-threshold shaft) and supply the threshold, betting the gate treats
    'ringless + threshold present' leniently and lets the loss ride in silently.

    It must not: the producer-author branch is checked BEFORE the threshold
    branch, so a producer loss on a sub-threshold cavity is fail-loud, ⛔ never a
    silent below_request exclusion.  Same cavity, same threshold, WITHOUT the
    forged loss, is the legitimate silent exit -- proving it is the forged loss,
    not the geometry, that draws the red.
    """
    signed, request, report = real_inputs
    tiny, tiny_id, view = _tiny_subthreshold_cavity(signed)
    assert tiny.area / (UNITS_PER_METRE ** 2) < request.min_room_area_m2
    probe_id = "shaft-launder"
    report_with_shaft = _report_with_zones(
        report, [_zone_over(tiny, probe_id, view.floor_id)])

    # control: same sub-threshold cavity, threshold supplied, NO forged loss ->
    # the legitimate silent below_request exit (⛔ no red on this cavity).
    control = reconcile_boundary_basis(
        signed, report_with_shaft, min_room_area_m2=request.min_room_area_m2)
    assert next(item for item in control.exclusions
                if item.converter_zone_id == probe_id
                ).evidence == "below_request_area_threshold"
    assert not [item for item in control.structural_failures if probe_id in item]

    # attack: forge a producer loss for that same sub-threshold cavity, still
    # supply the threshold -> FAIL-LOUD, ⛔ not laundered into a silent exclusion.
    raw = signed.model_dump(mode="json")
    forged_area = int(tiny.area)
    for v in raw["views"]:
        if v["view_id"] == view.view_id:
            v["boundary_ring_losses"] = v["boundary_ring_losses"] + [{
                "cavity_id": tiny_id, "area_units2": forged_area,
                "span": SYNTHETIC_SPAN, "reason": "merged_lt_3",
                "owner_count": None}]
    attacked = reconcile_boundary_basis(
        AsSignedV1.model_validate(raw), report_with_shaft,
        min_room_area_m2=request.min_room_area_m2)

    assert (f"{PRODUCER_LOSS_CODE}:{view.view_id}:{tiny_id}:{probe_id}:"
            f"reason=merged_lt_3:area_units2={forged_area}"
            ) in attacked.structural_failures
    # ⛔ the loss did NOT ride in as a silent below_request exclusion.
    assert not [item for item in attacked.exclusions
                if item.facts_cavity_id == tiny_id]
    assert not attacked.passed
