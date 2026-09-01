"""F-156: the cavity ring's corners come from intersecting adjacent support
lines, and a wall END CAP is admitted as a corner-maker without ever becoming
an edge record.

⛔ None of the criteria in this file is a count, a ``valid`` flag or an area.
Each of those was tried in an earlier round of this same defect and each let a
wrong ring through: a ring can have the right number of edges, be
``is_valid``, and have the right area while still being the wrong room.  What
is asserted here instead:

* the facts ring, carried out to the basis the ANSWER declares for each of its
  own edges, is the answer's zone -- symmetric difference exactly ``0``, with
  no tolerance anywhere (``test_projected_ring_*``);
* a cavity that covers more than one answer zone fails loudly instead of
  silently pairing with whichever one happens to contain a point
  (``test_cavity_that_covers_two_zones_*``);
* an end cap is admitted only when the wall really stops on a measured face of
  a wall parallel to that segment -- stated as a RULE and exercised by
  perturbing a wall that currently satisfies it, ⛔ never by naming a cavity
  (``test_endcap_admissibility_*``);
* an end cap contributes no edge record (``test_every_edge_sits_on_a_measured
  _face_of_its_own_wall_band``);
* corners come from intersections, ⛔ not from chaining the measured span end
  points (``test_chaining_span_end_points_instead_of_intersecting_*``).
"""
from __future__ import annotations

import copy

import pytest
from shapely.geometry import Polygon

import src.agent.judge.as_measured as am
from src.agent.judge.answer_compiler import (UNITS_PER_METRE,
                                             read_facts_for_compilation,
                                             reconcile_boundary_basis)
from src.agent.judge.as_measured import AsMeasuredViewV1
from src.agent.judge.gt_revisions import AsSignedV1
from src.agent.judge.tarch_converter_schema import ConversionReportV1
from src.agent.judge.gt_schema import REPO_ROOT

CASE = "sm25-L_anchor"
CONVERSION_REPORT = (
    REPO_ROOT / "case_tests/test_baseline/gt" / CASE / "review/conversion_report.json")
MIN_ROOM_AREA_M2 = 5.0

#: Both readings of the one condition F-157 owns (the answer-side
#: ``outer_skin``<->``wall_axis`` switch part way along a single support line).
DEFERRED_PROJECTION_CODES = ("facts_projected_ring_is_not_the_converter_zone",
                             "facts_projected_ring_unavailable")


@pytest.fixture(scope="module")
def facts():
    _measured, _ledger, signed = read_facts_for_compilation(CASE)
    return signed


@pytest.fixture(scope="module")
def report():
    return ConversionReportV1.model_validate_json(CONVERSION_REPORT.read_bytes())


def _derive(view_json: dict) -> am._BoundaryDerivation:
    return am._derive_boundary_facts(
        AsMeasuredViewV1.model_validate(view_json),
        min_room_area_m2=MIN_ROOM_AREA_M2)


def _rings(view_json: dict) -> dict[str, list]:
    by_cavity: dict[str, list] = {}
    for edge in _derive(view_json).edges:
        by_cavity.setdefault(edge.cavity_id, []).append(edge)
    return {cavity: sorted(edges, key=lambda edge: edge.sequence)
            for cavity, edges in by_cavity.items()}


def _deferred_cavities(audit) -> set[str]:
    return {f"cavity:{item.split(':')[3]}"
            for item in audit.structural_failures
            if item.startswith(DEFERRED_PROJECTION_CODES)}


# =========================================================================== #
# Acceptance 1 -- zero-threshold ring identity, in BOTH directions
# =========================================================================== #
def test_projected_ring_identity_holds_with_no_tolerance_at_all(facts, report):
    """Every cavity that reaches the per-edge comparison lands on its zone
    EXACTLY.  ⛔ Read the assertion: it is ``== 0``, not ``< something``.  The
    clear-span ring and the zone are on different bases and differ by 1.0-3.5 m²
    before projection, so a threshold here could only have been read off the
    data it is judging."""
    audit = reconcile_boundary_basis(facts, report)
    residuals = [item for item in audit.structural_failures
                 if item.startswith(DEFERRED_PROJECTION_CODES[0])]
    assert residuals == []          # nobody is merely "close enough"
    assert audit.mismatches == []
    # and the comparison really ran on real rooms, ⛔ not on an empty set
    assert len(audit.pairings) == 25
    assert audit.paired_edges == 100


def test_moving_one_converter_edge_by_a_tenth_of_a_millimetre_reddens(facts, report):
    """Teeth for the criterion above, at the smallest representable step.

    A 1-unit (0.1 mm) move of one converter zone edge must redden.  ⭐ This is
    what makes ``== 0`` meaningful: if the gate tolerated anything at all, the
    smallest possible perturbation would pass."""
    baseline = reconcile_boundary_basis(facts, report)
    target_zone = baseline.pairings[0].converter_zone_id
    raw = report.model_dump(mode="python")
    zone = next(item for item in raw["zones"] if item["zone_id"] == target_zone)
    step = 1.0 / UNITS_PER_METRE
    zone["polygon_m"]["exterior"]["vertices"] = [
        [point[0], point[1] + step] if index == 0 else point
        for index, point in enumerate(zone["polygon_m"]["exterior"]["vertices"])]

    audit = reconcile_boundary_basis(
        facts, ConversionReportV1.model_validate(raw))
    named = [item for item in audit.structural_failures
             if item.startswith(DEFERRED_PROJECTION_CODES[0])
             and f":{target_zone}:" in item]
    assert len(named) == 1, audit.structural_failures
    assert not audit.passed


# =========================================================================== #
# Acceptance 2 -- one cavity may not quietly stand in for two answer zones
# =========================================================================== #
def test_cavity_that_covers_two_zones_fails_loudly_instead_of_taking_one(facts, report):
    """⛔ The pre-existing test is "which zone contains the ring's
    representative point", and that ALWAYS names exactly one -- it cannot see
    that the cavity also covers a second zone.  Splitting a paired zone in two
    (both halves inside the same cavity) must therefore redden."""
    baseline = reconcile_boundary_basis(facts, report)
    proof = baseline.pairings[0]
    raw = report.model_dump(mode="python")
    zone = next(item for item in raw["zones"]
                if item["zone_id"] == proof.converter_zone_id)
    vertices = zone["polygon_m"]["exterior"]["vertices"]
    xs = [point[0] for point in vertices]
    ys = [point[1] for point in vertices]
    middle = (min(ys) + max(ys)) / 2.0
    lower = copy.deepcopy(zone)
    upper = copy.deepcopy(zone)
    lower["polygon_m"]["exterior"]["vertices"] = [
        [min(xs), min(ys)], [max(xs), min(ys)], [max(xs), middle], [min(xs), middle]]
    upper["zone_id"] = f"{zone['zone_id']}-upper"
    upper["polygon_m"]["exterior"]["vertices"] = [
        [min(xs), middle], [max(xs), middle], [max(xs), max(ys)], [min(xs), max(ys)]]
    raw["zones"] = [item for item in raw["zones"]
                    if item["zone_id"] != zone["zone_id"]] + [lower, upper]

    audit = reconcile_boundary_basis(
        facts, ConversionReportV1.model_validate(raw))
    assert any(item.startswith("facts_cavity_occupies_multiple_converter_zones")
               and proof.cavity_id in item
               for item in audit.structural_failures), audit.structural_failures
    assert not audit.passed


# =========================================================================== #
# Acceptance 3 -- the end-cap admissibility RULE, exercised by perturbation
# ⛔ No cavity id appears in any criterion here.  The fixture is built by
# breaking the rule's premise on whatever cavity currently satisfies it, so it
# keeps working after the cavities themselves change.
# =========================================================================== #
def _first_endcap_carrying_cavity(view_json: dict):
    """Return (cavity_id, axis, const) for a ring whose derivation used an end
    cap -- found by RULE (a ring segment with no face owner and exactly one
    perpendicular band ending on it), ⛔ not by id."""
    view = AsMeasuredViewV1.model_validate(view_json)
    groups = am._boundary_wall_groups(view)
    footprint, _records = am._boundary_footprint(view)
    region = am._boundary_wall_region(view)
    geometry = footprint.difference(region)
    threshold = MIN_ROOM_AREA_M2 * UNITS_PER_METRE * UNITS_PER_METRE
    cavities = sorted(
        [part for part in getattr(geometry, "geoms", [geometry])
         if part.geom_type == "Polygon" and not part.is_empty
         and part.area > threshold],
        key=lambda cavity: tuple(round(value, 6) for value in cavity.bounds))
    rings = _rings(view_json)
    for cavity in cavities:
        cavity_id = am._boundary_cavity_id(view.view_id, cavity)
        if cavity_id not in rings:
            continue
        ring = [(int(round(x)), int(round(y)))
                for x, y in list(cavity.exterior.coords)[:-1]]
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a[0] == b[0]:
                axis, const, lo, hi = "y", a[0], min(a[1], b[1]), max(a[1], b[1])
            else:
                axis, const, lo, hi = "x", a[1], min(a[0], b[0]), max(a[0], b[0])
            if am._boundary_owners(groups, axis, const, lo, hi):
                continue
            caps = am._boundary_endcap_groups(groups, axis, const, lo, hi)
            if len(caps) == 1 and am._boundary_parallel_measured_faces(
                    groups, axis, const):
                return cavity_id, axis, const
    raise AssertionError("no admissible end cap in this view")


def _endcap_losses_at(derivation, const: int) -> list:
    return [item for item in derivation.losses
            if item.reason == "endcap_const_not_a_measured_parallel_face"
            and item.span.const == const]


def test_endcap_admissibility_rule_has_teeth_on_a_one_unit_move(facts):
    """Green -> red on 0.1 mm.

    Pick, BY RULE, a ring segment this view currently accepts as an end cap
    (no face owner, exactly one perpendicular band ending on it, and that
    constant is a measured face of a parallel band).  Move that wall's end one
    single unit off the face it stops on.  The cavity behind it must lose its
    ring and be NAMED, with the miss distance carried in the ledger entry.
    ⛔ No cavity id appears anywhere in this test.
    """
    view_json = facts.views[0].model_dump(mode="json")
    _cavity_id, axis, const = _first_endcap_carrying_cavity(view_json)
    assert _endcap_losses_at(_derive(view_json), const + 1) == []   # green anchor

    perturbed = copy.deepcopy(view_json)
    moved = 0
    for wall in perturbed["walls"]:
        if wall["axis"] == axis:
            continue
        for field in ("along_min", "along_max"):
            if wall[field] == const:
                wall[field] = const + 1
                moved += 1
    assert moved >= 1, "the fixture moved nothing"

    losses = _endcap_losses_at(_derive(perturbed), const + 1)
    assert len(losses) == 1, [item.reason for item in _derive(perturbed).losses]
    assert losses[0].span.axis == axis
    # and the rule's own evidence: the constant it moved to is not a measured
    # face of any parallel band, while the one it left was.
    groups = am._boundary_wall_groups(AsMeasuredViewV1.model_validate(perturbed))
    assert am._boundary_parallel_measured_faces(groups, axis, const + 1) == []
    assert am._boundary_parallel_measured_faces(groups, axis, const) != []


def test_removing_the_endcap_rule_admits_the_ring_the_rule_refuses(facts):
    """Acceptance 5(c): neuter the rule on the SAME perturbed input and the
    refusal disappears -- so the rule, and nothing else, is what refused it."""
    view_json = facts.views[0].model_dump(mode="json")
    _cavity_id, axis, const = _first_endcap_carrying_cavity(view_json)
    perturbed = copy.deepcopy(view_json)
    for wall in perturbed["walls"]:
        if wall["axis"] == axis:
            continue
        for field in ("along_min", "along_max"):
            if wall[field] == const:
                wall[field] = const + 1
    with_rule = _derive(perturbed)
    assert len(_endcap_losses_at(with_rule, const + 1)) == 1

    original = am._boundary_parallel_measured_faces
    am._boundary_parallel_measured_faces = lambda *args, **kwargs: [("*", 0, 0)]
    try:
        without_rule = _derive(perturbed)
    finally:
        am._boundary_parallel_measured_faces = original
    assert _endcap_losses_at(without_rule, const + 1) == []
    assert (len({edge.cavity_id for edge in without_rule.edges})
            > len({edge.cavity_id for edge in with_rule.edges}))


# =========================================================================== #
# Acceptance 2 of §二 -- an end cap is a corner maker, never an edge record
# =========================================================================== #
def test_every_edge_sits_on_a_measured_face_of_its_own_wall_band(facts):
    """An end cap crosses a band's THICKNESS; a face-borne edge lies ON one of
    that band's faces.  So "no edge came from an end cap" is checkable without
    counting anything: every record's ``cavity_const`` is one of the two
    measured face constants of the band it names."""
    for view in facts.views:
        groups = am._boundary_wall_groups(view)
        by_walls = {tuple(group.wall_ids): group for group in groups.values()}
        assert view.boundary_edges
        for edge in view.boundary_edges:
            group = by_walls[tuple(edge.wall_ids)]
            assert edge.axis == group.axis
            assert edge.cavity_const in (group.face_lo, group.face_hi), edge.id


def test_letting_endcaps_become_edges_breaks_that_invariant(facts):
    """Acceptance 5(b): the invariant above is not vacuous -- put the end caps
    back into the edge-bearing set and it fails."""
    view_json = facts.views[0].model_dump(mode="json")
    original = am._boundary_support_lines

    def with_endcaps(merged):
        lines: list[list] = []
        for span in merged:
            key = (span.axis, span.cavity_const)
            if lines and (lines[-1][0].axis, lines[-1][0].cavity_const) == key:
                lines[-1].append(span)
            else:
                lines.append([span])
        return lines

    am._boundary_support_lines = with_endcaps
    try:
        derivation = _derive(view_json)
    finally:
        am._boundary_support_lines = original
    view = AsMeasuredViewV1.model_validate(view_json)
    groups = am._boundary_wall_groups(view)
    by_walls = {tuple(group.wall_ids): group for group in groups.values()}
    offenders = [edge.id for edge in derivation.edges
                 if edge.cavity_const not in (
                     by_walls[tuple(edge.wall_ids)].face_lo,
                     by_walls[tuple(edge.wall_ids)].face_hi)]
    production = {edge.cavity_id for edge in _derive(view_json).edges}
    mutated = {edge.cavity_id for edge in derivation.edges}
    # Either an end cap is carried as an edge (invariant above broken), or the
    # rings that depended on end caps collapse into named losses.  ⛔ What must
    # NOT happen is "nothing changes".
    assert offenders or production - mutated, "mutation changed nothing -- no teeth"
    assert all(cavity in {item.cavity_id for item in derivation.losses}
               for cavity in production - mutated)


# =========================================================================== #
# Acceptance 4 -- adjacent support lines are perpendicular once end caps are
# out of the edge-bearing set, and a violation is loud
# =========================================================================== #
def test_adjacent_support_lines_of_every_stored_ring_are_perpendicular(facts):
    for view in facts.views:
        for _cavity, edges in _rings(view.model_dump(mode="json")).items():
            lines = []
            for edge in edges:
                key = (edge.axis, edge.cavity_const)
                if not lines or lines[-1] != key:
                    lines.append(key)
            assert len(lines) >= 3
            for index, line in enumerate(lines):
                assert line[0] != lines[index - 1][0], (view.view_id, lines)


def test_a_parallel_junction_is_a_named_loss_not_a_silent_ring(facts):
    """Acceptance 4's red half.  Forcing the end caps into the edge-bearing set
    leaves rings whose support lines no longer alternate; that must surface as a
    named ledger loss, ⛔ never as a quietly wrong ring."""
    view_json = facts.views[0].model_dump(mode="json")
    original = am._boundary_support_lines

    def faced_only_without_grouping(merged):
        return [[span] for span in merged if span.kind == "faced"]

    am._boundary_support_lines = faced_only_without_grouping
    try:
        derivation = _derive(view_json)
    finally:
        am._boundary_support_lines = original
    assert any(item.reason == "adjacent_support_lines_parallel"
               for item in derivation.losses), [
        item.reason for item in derivation.losses]


# =========================================================================== #
# Acceptance 5(a) -- corners come from intersections, not from span end points
# =========================================================================== #
def _corner_rule_violations(edges_by_cavity: dict[str, list]) -> list[str]:
    """A ring TURNS only at the intersection of its two support lines.

    At every transition from one support line to the next, the two records must
    meet at one single point, and that point must lie on BOTH support lines.
    Chaining the measured span end points instead leaves a diagonal jump
    wherever an end cap was skipped -- which is precisely the defect.
    """
    violations = []
    for cavity, edges in edges_by_cavity.items():
        for index, edge in enumerate(edges):
            following = edges[(index + 1) % len(edges)]
            if (edge.axis, edge.cavity_const) == (following.axis,
                                                  following.cavity_const):
                continue          # same support line, not a turn
            on_this = (edge.p2[0] if edge.axis == "y" else edge.p2[1])
            on_next = (following.p1[0] if following.axis == "y"
                       else following.p1[1])
            if not (edge.p2 == following.p1
                    and on_this == edge.cavity_const
                    and on_next == following.cavity_const):
                violations.append(f"{cavity}:{index}")
    return violations


def test_every_ring_turns_exactly_on_its_support_line_intersections(facts):
    for view in facts.views:
        rings = _rings(view.model_dump(mode="json"))
        assert rings
        assert _corner_rule_violations(rings) == []
        for cavity, edges in rings.items():
            polygon = Polygon([edge.p1 for edge in edges])
            assert polygon.is_valid and polygon.area > 0, cavity


@pytest.mark.parametrize("view_index", (0, 1))
def test_chaining_span_end_points_breaks_the_corner_rule(facts, view_index):
    """Acceptance 5(a): the defect itself.  Same spans, same classification --
    only the corner rule changes -- and rings stop turning on their support
    lines, leaving a diagonal jump wherever an end cap was skipped."""
    view_json = facts.views[view_index].model_dump(mode="json")
    original = am._boundary_ring_corners

    def chain_span_end_points(lines):
        return [tuple(line[0].p1) for line in lines], None

    am._boundary_ring_corners = chain_span_end_points
    try:
        derivation = am._derive_boundary_facts(
            AsMeasuredViewV1.model_validate(view_json),
            min_room_area_m2=MIN_ROOM_AREA_M2)
    finally:
        am._boundary_ring_corners = original
    by_cavity: dict[str, list] = {}
    for edge in derivation.edges:
        by_cavity.setdefault(edge.cavity_id, []).append(edge)
    chained = {cavity: sorted(edges, key=lambda item: item.sequence)
               for cavity, edges in by_cavity.items()}
    assert _corner_rule_violations(chained), "no teeth"
