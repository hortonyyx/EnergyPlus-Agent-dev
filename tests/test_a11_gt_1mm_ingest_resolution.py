"""A-11 (user 2026-09-05, 「走乙」): the gt facts INGEST RESOLUTION is 1 mm.

Two statements that must stay distinct (the module docstring of
``src/agent/judge/as_measured.py`` now carries both):

  * STORAGE unit  = 0.1 mm integers -- a representation choice (user
    2026-08-29), ⛔ not a snap;
  * INGEST resolution = 1 mm -- a deliberate snap (:func:`_geom_units`),
    ruled by the user to belong to the MEASUREMENT REPRESENTATION, ⛔ never
    to the ``revisions`` ledger as a signed ``drawing_error``.

Dispatch ``2026-09-05g_A11_gt_1mm`` acceptance mapping (§三, rule-shaped):

  #1  every geometric coordinate of the re-emitted facts is a 1 mm multiple
        -> test_snapped_documents_scan_green / test_staged_trio_scans_green
  #2  IDENTITY lock: an on-grid value is never moved by the snap
        -> test_snap_is_the_identity_on_grid_values (unit level, every grid
           point in range) + test_identity_lock_document_level (per-handle,
           value-by-value on the real sm25 build)
  #3  configuration quantities untouched
        -> test_external_quantities_are_bit_identical (verbatim converter
           subtrees, counts, RAW pre-snap observations -- every exempt leaf
           the snap does not own, compared bit-for-bit plain vs snapped)
  #4  the criterion can go RED
        -> test_the_scan_goes_red_when_the_snap_is_removed (monkeypatch the
           one door shut, rebuild, the scan must report -- pinned to the
           dispatch's own measured baseline: 74 violations in the
           orchestrator's four buckets, 100 under this file's wider
           everything-is-checked-by-default extension)
  #5  max move reported honestly -- asserted ≤ 0.5 mm here
        -> test_max_coordinate_move_is_within_half_a_millimetre
  #7  staged trio re-emitted and reproducible is covered by
        ``test_gt_facts_staging_sm25.py`` (bit-for-bit rebuild) + this file's
        ``test_staged_trio_scans_green``.

⛔ The violation counts below (100 total / 74 in the orchestrator's buckets)
are RED-direction fixture inventory -- the count of what the UNSNAPPED build
of the committed sm25 fixture produces.  They move only if the fixture DXF
changes or the snap's coordinate extension changes, both of which must be a
conscious act; that is exactly what pinning them buys.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

import src.agent.judge.as_measured as as_measured
from src.agent.judge.as_measured import (
    INGEST_NON_COORDINATE_PATHS,
    INGEST_RESOLUTION_LABEL,
    INGEST_RESOLUTION_UNITS,
    UNITS_PER_METRE,
    _iter_int_leaves,
    _path_matches,
    build_as_measured,
    scan_ingest_resolution_violations,
    snap_to_ingest_resolution,
    to_units,
)
from src.agent.judge.gt_facts_staging import read_facts_candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
SM25 = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
SM24 = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm24_anchor"

#: The orchestrator's four measured buckets (dispatch §三#1): face_lines 46 ·
#: walls 11 · openings 10 · evidence-class 7 (evidence consts + member_consts
#: + ring-loss span consts) = 74.
BUCKETS = {"face_lines": 46, "walls": 11, "openings": 10, "evidence": 7}
#: Derived coordinate violations the orchestrator's table did not itemise
#: (boundary edge p1/p2/span_lo/span_hi, loss-span p1/p2 + nearest-face
#: delta, evidence footprint_edge_points, non-orthogonal endpoints,
#: axis-snap after-points, footprint ring points).
DERIVED_VIOLATIONS = 26
#: The same unsnapped build under THIS file's exit scan (every integer
#: checked by default): the four buckets above plus the derived paths.
TOTAL_UNSAPPED_VIOLATIONS = 100


def _bucket_of(path: str) -> str:
    if ".face_lines." in path:
        return "face_lines"
    if ".walls." in path:
        return "walls"
    if ".openings." in path:
        return "openings"
    if ("evidence.raw_face_const" in path
            or "evidence.opposite_face_const" in path
            or "member_consts" in path
            or "boundary_ring_losses" in path and ".span.const" in path):
        return "evidence"   # the orchestrator's fourth bucket, exactly
    return "derived"        # derived coordinate paths the orchestrator's
                            # distribution table did not itemise


@pytest.fixture(scope="module")
def snapped_as_received():
    return build_as_measured(SM25 / "sm25-L_t3_as_received.dxf",
                             SM25 / "request_as_measured.json")


@pytest.fixture(scope="module")
def plain_as_received():
    """The SAME build with the snap's one door monkeypatched shut
    (``_geom_units -> to_units``) -- i.e. what the tree produced before
    A-11, proven bit-for-bit identical to the committed pre-A-11 staged
    file by ``test_gt_facts_staging_sm25.test_1_...``'s counterpart below."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(as_measured, "_geom_units", to_units)
        return build_as_measured(SM25 / "sm25-L_t3_as_received.dxf",
                                 SM25 / "request_as_measured.json")


@pytest.fixture(scope="module")
def snapped_signed():
    return build_as_measured(SM25 / "sm25-L_t3.dxf", SM25 / "request.json")


# ── the declaration point (#single) ─────────────────────────────────────────── #
def test_the_declaration_point():
    assert INGEST_RESOLUTION_UNITS == 10
    assert INGEST_RESOLUTION_LABEL == "1mm"
    # 1 mm must be an exact number of storage units, or "grid point" is a
    # fiction the integer arithmetic cannot deliver.
    assert UNITS_PER_METRE % INGEST_RESOLUTION_UNITS == 0
    # The storage conversion itself stays pure (representation, ⛔ no snap):
    # pinned separately by test_r2_to_units_is_the_declared_scale; here the
    # composition is what carries the snap, never to_units alone.
    assert snap_to_ingest_resolution(to_units(0.1234567)) % INGEST_RESOLUTION_UNITS == 0


# ── acceptance #2: the identity lock ────────────────────────────────────────── #
def test_snap_is_the_identity_on_grid_values():
    """Unit level, EXHAUSTIVE over the grid in range: every multiple of the
    resolution between -50 m and +50 m maps to itself.  ⛔ Not a sample."""
    for units in range(-500_000, 500_001, INGEST_RESOLUTION_UNITS):
        assert snap_to_ingest_resolution(units) == units


def test_snap_bankers_rounding_and_bounds():
    # half-way cases tie to even, matching to_units' documented convention
    assert snap_to_ingest_resolution(5) == 0        # 0.5 mm -> 0 (even)
    assert snap_to_ingest_resolution(15) == 20      # 1.5 mm -> 2 (even)
    assert snap_to_ingest_resolution(-15) == -20
    assert snap_to_ingest_resolution(4) == 0
    assert snap_to_ingest_resolution(6) == 10
    # the snap never moves anything by more than half the resolution
    for units in range(-205, 206):
        assert abs(snap_to_ingest_resolution(units) - units) <= 5


def test_identity_lock_document_level(snapped_as_received, plain_as_received):
    """Document level, value-by-value (⛔ not a total): for every face line
    the plain build stored ON-grid, the snapped build must store the SAME
    value under the SAME (view, handle, field) -- and no on-grid value may
    vanish from the document's checked leaves."""
    for snapped_view, plain_view in zip(snapped_as_received.views,
                                        plain_as_received.views):
        by_id_snapped = {f.id: f for f in snapped_view.face_lines}
        by_id_plain = {f.id: f for f in plain_view.face_lines}
        assert set(by_id_snapped) == set(by_id_plain), \
            "the snap must not add or drop a stroke"
        for handle, plain_face in by_id_plain.items():
            for field in ("const", "along_min", "along_max"):
                if plain_face.model_dump()[field] % INGEST_RESOLUTION_UNITS == 0:
                    assert by_id_snapped[handle].model_dump()[field] \
                        == plain_face.model_dump()[field], \
                        f"identity lock broken: {handle}.{field}"
    # multiset form: every on-grid value present in the plain build's
    # checked leaves is still present in the snapped build's
    def on_grid_checked(payload) -> Counter:
        return Counter(
            str(value) for path, value in _iter_int_leaves(payload)
            if not any(_path_matches(path, pattern)
                       for pattern in INGEST_NON_COORDINATE_PATHS)
            and value % INGEST_RESOLUTION_UNITS == 0)
    plain_counts = on_grid_checked(plain_as_received.model_dump(mode="json"))
    snapped_counts = on_grid_checked(snapped_as_received.model_dump(mode="json"))
    lost = {value: plain_counts[value] - snapped_counts.get(value, 0)
            for value in plain_counts if snapped_counts.get(value, 0) < plain_counts[value]}
    assert not lost, f"on-grid values lost by the snap: {lost}"


# ── acceptance #1: the scan is green on the snapped builds ──────────────────── #
@pytest.mark.parametrize("doc_fixture", ["snapped_as_received", "snapped_signed"])
def test_snapped_documents_scan_green(doc_fixture, request):
    document = request.getfixturevalue(doc_fixture)
    violations = scan_ingest_resolution_violations(document.model_dump(mode="json"))
    assert violations == [], violations[:10]


def test_sm24_snapped_scan_is_green():
    document = build_as_measured(SM24 / "source.dxf", SM24 / "request.json")
    assert scan_ingest_resolution_violations(document.model_dump(mode="json")) == []


def test_staged_trio_scans_green():
    """Acceptance #1 on the COMMITTED staging trio (both as_measured and
    as_signed -- the exit scan is shape-identical for both)."""
    for case in ("sm25-L_anchor", "sm24_anchor"):
        as_measured_doc, _revisions, as_signed_doc = read_facts_candidate(case)
        for label, document in (("as_measured", as_measured_doc),
                                ("as_signed", as_signed_doc)):
            violations = scan_ingest_resolution_violations(
                document.model_dump(mode="json"))
            assert violations == [], f"{case}/{label}: {violations[:10]}"


# ── acceptance #4: the criterion can go RED ─────────────────────────────────── #
def test_the_scan_goes_red_when_the_snap_is_removed(plain_as_received):
    """Shut the one door (the plain fixture already did) and the exit scan
    MUST report -- pinned to the dispatch's own measured baseline."""
    violations = scan_ingest_resolution_violations(
        plain_as_received.model_dump(mode="json"))
    assert violations, "a criterion that cannot go red is not a criterion"
    buckets = Counter(_bucket_of(v.rsplit(" = ", 1)[0]) for v in violations)
    for bucket, expected in BUCKETS.items():
        assert buckets[bucket] == expected, \
            f"{bucket}: {buckets[bucket]} != dispatch baseline {expected}"
    assert buckets["derived"] == DERIVED_VIOLATIONS
    assert len(violations) == TOTAL_UNSAPPED_VIOLATIONS


def test_the_exemption_table_cannot_rot_onto_a_coordinate():
    """The exempt table is the A-11 "coordinate vs non-coordinate" boundary;
    these REPRESENTATIVE coordinate paths (one per producer family) must
    never be matched by any exemption pattern -- if one is, the exit scan
    has gone blind on real coordinates."""
    coordinate_paths = [
        ("views", "0", "face_lines", "3", "const"),
        ("views", "0", "face_lines", "3", "along_max"),
        ("views", "0", "walls", "2", "face_lo"),
        ("views", "0", "walls", "2", "along_min"),
        ("views", "0", "openings", "1", "cross_hi"),
        ("views", "0", "footprint", "rings", "0", "points", "*", "0"),
        ("views", "0", "boundary_edges", "5", "span_lo"),
        ("views", "0", "boundary_edges", "5", "p2", "1"),
        ("views", "0", "boundary_edges", "5", "evidence", "raw_face_const"),
        ("views", "0", "boundary_edges", "5", "evidence",
         "footprint_edge_points", "*", "1"),
        ("views", "0", "boundary_ring_losses", "0", "span", "const"),
        ("views", "0", "non_orthogonal_lines", "0", "p1", "0"),
        ("views", "0", "converter_readouts", "axis_snapped_lines", "0",
         "after_p0", "1"),
        ("views", "0", "converter_readouts",
         "face_groups_with_a_split_const", "0", "member_consts", "0"),
        ("views", "0", "converter_readouts",
         "unresolved_opening_carriers", "0", "cross_lo"),
    ]
    for path in coordinate_paths:
        for pattern in INGEST_NON_COORDINATE_PATHS:
            assert not _path_matches(tuple(path), pattern), \
                f"exemption {pattern!r} swallows coordinate path {'.'.join(path)!r}"


# ── acceptance #3: configuration quantities untouched ───────────────────────── #
def test_external_quantities_are_bit_identical(snapped_as_received,
                                               plain_as_received):
    """Everything the snap does NOT own, compared bit-for-bit between the
    plain and snapped builds of the same drawing:

      * the converter's VERBATIM subtrees (diagnostics / gates /
        jamb_cap_bands) -- including their deepest ``context`` integers;
      * every converter readout count;
      * the RAW pre-snap observations (``before_p0`` / ``before_p1``) and
        the length observation ``minor_leg_units``;
      * identity strings (handles, layers, axes, view ids).

    ⚠️ The boundary-derived subtrees (``boundary_edges`` /
    ``boundary_ring_losses``) are excluded from this bit-identity lock on
    purpose: they are FUNCTIONS of the coordinates (on this fixture the snap
    legitimately turns one lost cavity into a closed ring -- edges 83 -> 91,
    losses 1 -> 0 -- so their enumerations and witness values move with the
    geometry).  Their COORDINATES are still exit-scanned as hard as
    everything else; this test is about inputs the snap must not touch, and
    those live outside the boundary subtrees."""
    snapped = snapped_as_received.model_dump(mode="json")
    plain = plain_as_received.model_dump(mode="json")

    def external_leaves(payload) -> Counter:
        return Counter(
            (".".join(path), value)
            for path, value in _iter_int_leaves(payload)
            if any(_path_matches(path, pattern)
                   for pattern in INGEST_NON_COORDINATE_PATHS)
            and "boundary_edges" not in path
            and "boundary_ring_losses" not in path)

    assert external_leaves(snapped) == external_leaves(plain), \
        "an exempt quantity outside the boundary derivation moved"

    for snapped_view, plain_view in zip(snapped["views"], plain["views"]):
        assert [(f["id"], f["layer"], f["axis"])
                for f in snapped_view["face_lines"]] == \
               [(f["id"], f["layer"], f["axis"])
                for f in plain_view["face_lines"]], "identity strings moved"
        assert snapped_view["view_id"] == plain_view["view_id"]


# ── acceptance #5: max move reported honestly ───────────────────────────────── #
def test_max_coordinate_move_is_within_half_a_millimetre(snapped_as_received,
                                                         plain_as_received):
    """The dispatch's stop-report line: the snap's largest single move on
    the real fixture must stay within half the resolution.  The measured
    maximum (asserted, not just reported) is 4 units = 0.4 mm, on the
    orchestrator's own outlier value 15939.6 mm -> 15940.0 mm."""
    worst = 0
    witness = None
    for snapped_view, plain_view in zip(snapped_as_received.views,
                                        plain_as_received.views):
        by_id_snapped = {f.id: f for f in snapped_view.face_lines}
        for plain_face in plain_view.face_lines:
            snapped_face = by_id_snapped[plain_face.id]
            for field in ("const", "along_min", "along_max"):
                plain_value = plain_face.model_dump()[field]
                delta = abs(snapped_face.model_dump()[field] - plain_value)
                if delta > worst:
                    worst = delta
                    witness = (plain_face.id, field, plain_value)
    assert worst <= 5, f"max move {worst} units exceeds 0.5 mm: {witness}"
