"""Locks for the facts layer's first cut -- ``AsMeasuredV1`` (dispatch ②-1a).

Three things are locked, one per section below:

  R1  the as-received drawing can be converted WITHOUT touching a signed byte
  R2  what P1 measured lands in the document, and the three forbidden fields
      (``basis`` / expanded endpoints / ``boundary_condition``) do not
  R3  the document is reproducible BIT FOR BIT across fresh processes, ⛔ with
      no ``PYTHONHASHSEED`` propping it up

G-c (2026-09-07) closed the as-received drawing's joints.  Its geometry
inventory now matches the signed drawing; the audit retains three tier-1
snaps (13AD/13AE/13AF).  The old 10 mm / 1-degree thresholds are historical:
the current ladder uses q, half the request's minimum wall thickness, and
5 degrees.  Real non-orthogonal rows and BLOCK diagnostics have disappeared.

The negative inventory is therefore constructed: sub-millimetre skew rows
exercise RAW evidence, tier-2 records exercise arbitration, and a temporary
orphan stroke exercises BLOCK diagnostics on a successful facts build.  Each
snap record is removed individually so the larger list cannot replace the
single-missing-entry sample with a multiple-deletion sample.

⛔ Nothing here writes into ``gt_sources/`` or ``gt/``.  Everything derived is
built in ``tmp_path``.
"""
from __future__ import annotations

import collections
import copy
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import src.agent.judge.as_measured as am
from src.agent.judge.as_measured import (
    AsMeasuredUnavailable,
    AsMeasuredV1,
    REQUEST_AS_MEASURED_ALLOWED_DELTA,
    assert_request_is_pure_source_swap,
    build_as_measured,
    build_view,
    canonical_bytes,
    content_sha256,
    derive_as_measured_request,
    request_file_bytes,
    to_units,
)
from src.agent.judge.gt_manifest import load_gt_tooling_config
from src.agent.judge.tarch_converter_schema import (
    TarchConversionRequestV1,
    compute_request_sha256,
)

REPO = Path(__file__).resolve().parents[1]
ANCHOR = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
SIGNED_DXF = ANCHOR / "sm25-L_t3.dxf"
AS_RECEIVED_DXF = ANCHOR / "sm25-L_t3_as_received.dxf"
SIGNED_REQUEST = ANCHOR / "request.json"
AS_MEASURED_REQUEST = ANCHOR / "request_as_measured.json"
SM24 = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor"

#: The signatures this unit promised not to move.  ⭐ Both halves are pinned:
#: the CANONICAL hash (what the converter checks) and the FILE hash (what the
#: canonical hash cannot see -- a reformat leaves the former alone).
SIGNED_CANONICAL = {
    "sm25 request": (SIGNED_REQUEST,
                     "d738d0ac230f21ae20f477b1cc084549f1308bff295a3f6de8956da98d25a135"),
    "sm24 request": (SM24 / "request.json",
                     "ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2"),
}
SIGNED_FILE_BYTES = {
    SIGNED_REQUEST: "e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396df",
    SM24 / "request.json": "34b7d74959e8a8c644d7082d952fddcf9a16bb9407c620ad1dfa303cff1e23b9",
    SM24 / "manifest.json": "4daca5539e77fe11521b5f14b45acf7cff321f99c1139457b7f625784ec289bc",
    SIGNED_DXF: "1251f65153829c9c4502e401b7962a22172e3b636732d4ddf91a40a7b049f8b9",
    AS_RECEIVED_DXF: "4a94922489d391692da20a3b081511ab268d707fa7b61ae4413aae5268753245",
}
SM24_MANIFEST_SHA256 = "c40cbc8bb566e4d8fc3999ad5ccb07bd27747b9f57f9ad30fe6691c7189bac21"

# MEASURED 2026-08-28 with this change in the tree.  ⭐ Both drawings, both
# views: a number proven on one view only proves that view.
#: ⭐⭐ ②-1a-R: ``walls`` is now PAIRED FACE LINES, and ``thickness_mm`` is the
#: acceptance that actually catches the defect -- the counts alone would have
#: been just as green on the ghost-wall build (45/39/44/39 walls looked fine).
#: The drawing declares 120 and 240 mm and contains nothing else.
EXPECTED = {
    # ⭐ ②-1b-S R1: 13AD/13AE are now SNAPPED (admitted), not S1-discarded --
    # face_lines/wall_lines_total each +2, the "tarch_wall_nonorthogonal"
    # BLOCK and its G1 gate failure are gone, ``walls``/``thickness_mm`` now
    # match the SIGNED drawing exactly (the pair completes a real 120 mm
    # wall), and S4 dangles goes 4->8 (see the module docstring's ②-1b-S
    # UPDATE note -- a real, out-of-scope topology consequence, not a defect
    # in the snap itself; ``tarch_wall_free_end`` was already a BLOCK before).
    #
    # ⭐ A-11 (2026-09-05, 1 mm ingest snap, user 「走乙」) moved exactly
    # three readouts, each with a stated cause: ``split_const_groups`` 2/4
    # -> 0/0 on plan-F1 (the 0.1 mm representation residue those groups
    # existed to name is absorbed, so the groups honestly stop existing);
    # as-received-F1 ``bands_missing_a_face_line`` 11 -> 9 (two bands whose
    # face sat 0.1 mm off a drawn stroke now reconcile against the snapped
    # ``face_lines[*].const`` -- the by_const lookup key snaps with it); and
    # the boundary-edge total pinned in test_r2_projection_fields_are_
    # absent_but_boundary_condition_is_first_class (one cavity that was a
    # ring LOSS on the unsnapped build now closes into a ring, 83 -> 91
    # edges on as-received F1).  Everything else in this table is UNCHANGED
    # by the snap.
    # ⭐⭐⭐ G-c (2026-09-07, the four-tier ladder + the anchor-end rule): this
    # row is now IDENTICAL to ("signed", "plan-F1") in every column.  ⛔ That is
    # not a copy-paste slip, it is the unit's whole claim: the as-received
    # drawing's one crooked wall is recovered to the geometry the signed
    # drawing has, bit for bit, so every count, gate, BLOCK code and histogram
    # converges.  MEASURED deltas from the pre-ladder row, each with its cause:
    #   face_lines 224 -> 225  (13AF used to fall between ``tau_axis`` and the
    #     exact-equality face-line test and vanish from BOTH tables; it is now
    #     a real face line)
    #   non_orthogonal 1 -> 0  (same stroke, same reason)
    #   dangles 8 -> 0, gates_failed ["G5"] -> [], block_codes
    #     ["tarch_wall_free_end"] -> []  (the west end cap now closes onto the
    #     two faces it caps -- the anchor rule moves their west ends and the
    #     cap FOLLOWS, so S4 has no free end left to report)
    #   jamb_cap_bands 44 -> 45  (13AF is 120 mm long and inside the declared
    #     thickness range, so it is a cap the S2 pass can finally see)
    # ⛔ The one thing that still separates the two drawings is the snap
    # ledger, which is exactly what it exists for -- see
    # ``test_r2_the_as_received_drawing_differs_from_the_signed_one_as_f129_measured``.
    ("as_received", "plan-F1"): {"face_lines": 225, "walls": 55, "openings": 31,
                                 "wall_lines_total": 225, "non_orthogonal": 0,
                                 "dangles": 0, "gates_failed": [],
                                 "block_codes": [],
                                 "thickness_mm": {120: 28, 240: 27},
                                 "jamb_cap_bands": 45,
                                 "bands_missing_a_face_line": 9,
                                 "split_const_groups": 0},
    ("as_received", "plan-F2"): {"face_lines": 222, "walls": 53, "openings": 30,
                                 "wall_lines_total": 222, "non_orthogonal": 0,
                                 "dangles": 0, "gates_failed": [],
                                 "block_codes": [],
                                 "thickness_mm": {120: 28, 240: 25},
                                 "jamb_cap_bands": 39,
                                 "bands_missing_a_face_line": 7,
                                 "split_const_groups": 0},
    ("signed", "plan-F1"): {"face_lines": 225, "walls": 55, "openings": 31,
                            "wall_lines_total": 225, "non_orthogonal": 0,
                            "dangles": 0, "gates_failed": [], "block_codes": [],
                            "thickness_mm": {120: 28, 240: 27},
                            "jamb_cap_bands": 45,
                            "bands_missing_a_face_line": 9,
                            "split_const_groups": 0},
    ("signed", "plan-F2"): {"face_lines": 222, "walls": 53, "openings": 30,
                            "wall_lines_total": 222, "non_orthogonal": 0,
                            "dangles": 0, "gates_failed": [], "block_codes": [],
                            "thickness_mm": {120: 28, 240: 25},
                            "jamb_cap_bands": 39,
                            "bands_missing_a_face_line": 7,
                            "split_const_groups": 0},
}

#: ⛔ Read from the request, ⛔ not typed in: the D2 cap test is bounded by the
#: DECLARED widest wall, and a literal here could drift away from the request
#: without anything going red.
T_MAX_M = max(float(x) for x in json.loads(
    AS_MEASURED_REQUEST.read_text(encoding="utf-8"))["wall_thickness_range_m"])


def thickness_hist_mm(walls) -> dict[int, int]:
    """Thickness histogram in whole millimetres -- the acceptance ① readout."""
    return dict(sorted(collections.Counter(w.thickness // 10 for w in walls).items()))


@pytest.fixture(scope="module", autouse=True)
def fixtures_present():
    """⛔ Assert the inputs EXIST first ([[absent-file-read-as-passing-check]])."""
    for path in (SIGNED_DXF, AS_RECEIVED_DXF, SIGNED_REQUEST, AS_MEASURED_REQUEST,
                 SM24 / "request.json", SM24 / "manifest.json"):
        assert path.is_file(), f"missing ②-1a fixture: {path}"


@pytest.fixture(scope="module")
def as_received_doc() -> AsMeasuredV1:
    return build_as_measured(AS_RECEIVED_DXF, AS_MEASURED_REQUEST)


@pytest.fixture(scope="module")
def signed_doc() -> AsMeasuredV1:
    return build_as_measured(SIGNED_DXF, SIGNED_REQUEST)


def _doc(name: str, as_received_doc, signed_doc) -> AsMeasuredV1:
    return as_received_doc if name == "as_received" else signed_doc


# =========================================================================== #
# R1 -- the as-received drawing converts, and no signed byte moved
# =========================================================================== #
def test_r1_every_signed_signature_is_bit_identical():
    """⭐ Acceptance 1.  ⛔ The whole unit is void if one of these moves.

    Two independent pins, because they fail on different things: the canonical
    hash is what ``run_p1_plan_view``'s gate compares, and it is blind to how
    the file is laid out; the file hash catches a reformat that the canonical
    hash would forgive.
    """
    for label, (path, expected) in SIGNED_CANONICAL.items():
        request = TarchConversionRequestV1.model_validate_json(path.read_bytes())
        assert request.request_sha256 == expected, label
        assert compute_request_sha256(request) == expected, f"{label}: recomputed"
    manifest = json.loads((SM24 / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_sha256"] == SM24_MANIFEST_SHA256
    for path, digest in SIGNED_FILE_BYTES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path.name


def test_r1_the_as_measured_request_is_recomputed_not_authored():
    """⛔ The second request file must not be MAINTAINED -- it is DERIVED.

    ⭐ This is what keeps road 甲's cost from coming due.  Two request files can
    drift apart in a clip box, a selector or an affine and nothing would say so
    (F-130's shape).  Here the shipped file is compared BYTE FOR BYTE against a
    fresh derivation from the signed request, so an edit to either one that the
    other did not receive is a red test, ⛔ not a discrepancy someone has to
    notice.
    """
    assert AS_MEASURED_REQUEST.read_bytes() == derive_as_measured_request(
        SIGNED_REQUEST, AS_RECEIVED_DXF)


def test_r1_the_formatter_is_the_one_that_wrote_the_signed_file():
    """⛔ Guards the guard above: byte comparison only means something if the
    formatter is the repo's own.  ⭐ MEASURED: re-dumping the signed request
    through it reproduces that file exactly (25909 bytes)."""
    raw = json.loads(SIGNED_REQUEST.read_text(encoding="utf-8"))
    assert request_file_bytes(raw) == SIGNED_REQUEST.read_bytes()


def test_r1_delta_is_exactly_the_four_declared_keys():
    delta = assert_request_is_pure_source_swap(SIGNED_REQUEST, AS_MEASURED_REQUEST)
    assert sorted(delta) == sorted(REQUEST_AS_MEASURED_ALLOWED_DELTA)
    assert delta["source_dxf_sha256"] == (
        hashlib.sha256(SIGNED_DXF.read_bytes()).hexdigest(),
        hashlib.sha256(AS_RECEIVED_DXF.read_bytes()).hexdigest())


def test_r1_the_drift_gate_goes_red_on_a_real_drift(tmp_path):
    """⛔ Not a range check: change ANY other key and it must refuse.

    ``min_room_area_m2`` is picked deliberately -- it is a domain parameter that
    changes what the converter DOES, and it is exactly the kind of value someone
    would "just tweak on the as-received copy to see".
    """
    raw = json.loads(AS_MEASURED_REQUEST.read_text(encoding="utf-8"))
    raw["min_room_area_m2"] = raw["min_room_area_m2"] + 1.0
    drifted = tmp_path / "drifted.json"
    drifted.write_bytes(request_file_bytes(raw))
    with pytest.raises(ValueError, match="as_measured_request_drifted_on"):
        assert_request_is_pure_source_swap(SIGNED_REQUEST, drifted)


def test_r1_the_drift_gate_goes_red_when_nothing_was_swapped(tmp_path):
    """⛔ The other direction: a copy of the SIGNED request is not an
    as-received request, however correct every field in it looks."""
    same = tmp_path / "same.json"
    same.write_bytes(SIGNED_REQUEST.read_bytes())
    with pytest.raises(ValueError, match="as_measured_request_is_not_a_source_swap"):
        assert_request_is_pure_source_swap(SIGNED_REQUEST, same)


def test_r1_the_drift_gate_notices_an_added_or_removed_key(tmp_path):
    raw = json.loads(AS_MEASURED_REQUEST.read_text(encoding="utf-8"))
    raw.pop("north_axis")
    short = tmp_path / "short.json"
    short.write_bytes(request_file_bytes(raw))
    with pytest.raises(ValueError, match="as_measured_request_key_set_differs"):
        assert_request_is_pure_source_swap(SIGNED_REQUEST, short)


def test_r1_the_signed_request_still_refuses_the_as_received_drawing():
    """⭐⭐ The lock that proves the new request is doing real work.

    ⛔ If this ever stops raising, the hash gate has been loosened and the whole
    of R1 became unnecessary for the wrong reason.  MEASURED: the refusal names
    ``tarch_input_source_hash_mismatch`` and its stage is ``S0_input``.
    """
    with pytest.raises(AsMeasuredUnavailable) as excinfo:
        build_as_measured(AS_RECEIVED_DXF, SIGNED_REQUEST, view_ids=["plan-F1"])
    exc = excinfo.value
    assert exc.reason == "upstream_identity_block"
    assert "tarch_input_source_hash_mismatch" in exc.blocking_codes
    assert "tarch_input_source_hash_mismatch" in str(exc)


# =========================================================================== #
# R2 -- what P1 measured is what the document holds
# =========================================================================== #
@pytest.mark.parametrize("which,view_id", sorted(EXPECTED))
def test_r2_measured_inventory(which, view_id, as_received_doc, signed_doc):
    """⭐ Acceptance 2.  ⛔ Counts AND the readouts behind them.

    ⚠️ [[whole-stage-redraw-cannot-fix-systematic-field-confusion]]'s cousin:
    pinning only ``len(face_lines)`` cannot tell "the same walls" from "the same
    NUMBER of walls", so the gate verdicts and BLOCK codes are pinned too --
    they are what actually differs between the two drawings.
    """
    want = EXPECTED[(which, view_id)]
    doc = _doc(which, as_received_doc, signed_doc)
    view = next(v for v in doc.views if v.view_id == view_id)
    readouts = view.converter_readouts
    assert len(view.face_lines) == want["face_lines"]
    assert len(view.walls) == want["walls"]
    assert len(view.openings) == want["openings"]
    assert readouts.wall_lines_total == want["wall_lines_total"]
    assert len(readouts.non_orthogonal_lines) == want["non_orthogonal"]
    assert readouts.dangles == want["dangles"]
    assert [g["id"] for g in readouts.gates if not g["passed"]] == want["gates_failed"]
    assert sorted({d["code"] for d in readouts.diagnostics
                   if d["severity"] == "BLOCK"}) == want["block_codes"]
    assert thickness_hist_mm(view.walls) == want["thickness_mm"], (
        "⛔ ②-1a-R acceptance ①: a thickness the drawing does not contain means "
        "``walls`` is being built from something that is not a pair of faces")
    assert len(readouts.jamb_cap_bands) == want["jamb_cap_bands"]
    assert (len(readouts.jamb_cap_bands_missing_a_face_line)
            == want["bands_missing_a_face_line"])
    assert (len(readouts.face_groups_with_a_split_const)
            == want["split_const_groups"])


def test_r2_the_as_received_drawing_differs_from_the_signed_one_as_f129_measured(
        as_received_doc, signed_doc):
    """⭐ Acceptance 2's contrast half, ⛔ stated as F-129 measured it.

    F-129: the five retouched lines all sit on 1F, so ``plan-F2`` must come out
    IDENTICAL on both drawings and ``plan-F1`` must not.  ⛔ Without the F2 half
    this test could pass on a build that simply produced garbage for both.
    """
    def view(doc, view_id):
        return next(v for v in doc.views if v.view_id == view_id)

    f2_a = view(as_received_doc, "plan-F2").model_dump(mode="json")
    f2_s = view(signed_doc, "plan-F2").model_dump(mode="json")
    assert f2_a == f2_s, "F-129: the retouched entities are all on 1F"

    f1_a, f1_s = view(as_received_doc, "plan-F1"), view(signed_doc, "plan-F1")
    assert f1_a.model_dump(mode="json") != f1_s.model_dump(mode="json")

    # ⭐⭐⭐ G-c (2026-09-07): WHAT still differs is now the interesting part.
    # The ladder recovers the as-received geometry to the signed one, so
    # ⛔ every geometric table below is EQUAL -- and the ONE remaining
    # difference is the snap ledger.  That is precisely the property the ledger
    # was built for (GLM's R2 demand): "被吸附过" and "本来就是正的" must never
    # look the same.  ⛔ If this ever collapses to full equality, the record has
    # lost the fact that one of these drawings was retouched by the converter.
    for field in ("face_lines", "walls", "openings", "footprint",
                  "boundary_edges", "boundary_ring_losses"):
        assert (f1_a.model_dump(mode="json")[field]
                == f1_s.model_dump(mode="json")[field]), field
    assert sorted(s.id for s in f1_a.converter_readouts.axis_snapped_lines) == [
        "13AD", "13AE", "13AF"]
    assert not f1_s.converter_readouts.axis_snapped_lines, (
        "the signed drawing has no skew to snap -- all three are already exact")
    # one rigid-body rotation of 329 arcsec: all three read the same angle
    assert all(0.091 <= s.angle_deg <= 0.092
               for s in f1_a.converter_readouts.axis_snapped_lines)
    # ⛔ and nothing was refused on either drawing, on any tier:
    for doc_view in (f1_a, f1_s):
        rejected = sorted(h for d in doc_view.converter_readouts.diagnostics
                          if d["code"] == "tarch_wall_nonorthogonal"
                          for h in d["handles"])
        assert rejected == []
        assert doc_view.converter_readouts.non_orthogonal_lines == []
        assert doc_view.converter_readouts.axis_snap_arbitrations == []


def test_r2_every_wall_thickness_recomputes_from_its_two_stored_faces(
        as_received_doc, signed_doc):
    """⛔ ``thickness`` is stored, and it must be the INTEGER difference.

    ⭐ That is what makes "derived but persisted" safe: the check is exact, so
    a thickness that drifted from its faces cannot hide behind a tolerance.
    """
    for doc in (as_received_doc, signed_doc):
        for view in doc.views:
            for wall in view.walls:
                assert wall.thickness == wall.face_hi - wall.face_lo, wall.id
                assert wall.thickness > 0


def test_r2_every_reference_resolves(as_received_doc, signed_doc):
    for doc in (as_received_doc, signed_doc):
        for view in doc.views:
            ids = {f.id for f in view.face_lines}
            wall_ids = {w.id for w in view.walls}
            for wall in view.walls:
                assert set(wall.face_line_ids_lo) <= ids
                assert set(wall.face_line_ids_hi) <= ids
            for opening in view.openings:
                assert set(opening.carrier_wall_ids) <= wall_ids


def test_r2_every_opening_names_its_carrier_wall(as_received_doc, signed_doc):
    """MEASURED: 31/31 and 30/30 on BOTH drawings -- the carrier reference the
    dispatch worried might be missing is fully derivable inside P1.

    ⭐ ②-1a-R made the reference PLURAL, and this pins the reason rather than
    the convenience: D4 never merges a face-line run across an opening, so an
    opening sits BETWEEN two runs of one wall.  MEASURED on all four views --
    every opening touches EXACTLY 2 runs, strictly overlaps 0 of them, and both
    runs carry the SAME face pair.  So the WALL is unambiguous; "which of its
    two runs" is a question with no answer, and ⛔ picking one would put a false
    statement ("the opening is inside this run") into the record.
    """
    for doc in (as_received_doc, signed_doc):
        for view in doc.views:
            unresolved = [o.id for o in view.openings if not o.carrier_wall_ids]
            assert unresolved == [], f"{doc.source_dxf_label}/{view.view_id}"
            assert view.converter_readouts.unresolved_opening_carriers == []
            by_id = {w.id: w for w in view.walls}
            for opening in view.openings:
                assert len(opening.carrier_wall_ids) == 2, opening.id
                faces = {(by_id[i].axis, by_id[i].face_lo, by_id[i].face_hi)
                         for i in opening.carrier_wall_ids}
                assert len(faces) == 1, (
                    f"{opening.id}: its runs disagree about which wall it is in")
                assert faces == {(opening.axis, opening.cross_lo, opening.cross_hi)}


def test_r2_a_band_whose_second_face_was_never_drawn_is_named_not_dropped(
        as_received_doc, signed_doc):
    """⚠️⚠️ ②-1a measured this and ②-1a-R explains it: ``wall_bands`` is NOT a
    list of walls, and the bands one of whose faces has no ink are the proof.

    The converter calls a stroke a jamb cap on LENGTH alone (inside
    ``wall_thickness_range_m`` = [0.06, 0.50] m), so a 0.36 m stroke drawn on
    the WALL layer that is not a cap still produces a "band".  MEASURED on the
    SIGNED drawing, ``plan-F1``: band ``w_x_35853.6_36213.6`` has two face lines
    on its low face and NONE on its high face, whose nearest neighbours are
    +/- 60 -- the two faces of a 120 mm wall whose CENTRE it lands on.

    ⭐ ②-1a-R: the bands are still carried (⛔ a converter readout is never
    dropped) but they are no longer called ``walls``, and this count is now a
    statement ABOUT THE BANDS.  ⛔ It is kept, not deleted, because it is the
    measurement that shows band grouping and face pairing are different things.
    """
    for doc in (as_received_doc, signed_doc):
        for view in doc.views:
            readouts = view.converter_readouts
            named = set(readouts.jamb_cap_bands_missing_a_face_line)
            known = {b["band_id"] for b in readouts.jamb_cap_bands}
            assert named <= known, f"{doc.source_dxf_label}/{view.view_id}"
            # ⛔ and the gap is real inventory, not an empty promise
            assert named, "this assertion would be vacuous with no such band"
            # ⭐ every wall, by contrast, names ink on BOTH faces -- structurally
            assert all(w.face_line_ids_lo and w.face_line_ids_hi for w in view.walls)


def test_r2_projection_fields_are_absent_but_boundary_condition_is_first_class(
        as_received_doc):
    """②-1d keeps topology while S7 projection choices remain forbidden.

    Checked on the SERIALISED document, not on the class definitions: a field
    can arrive through a verbatim passthrough without ever being declared.
    """
    text = canonical_bytes(as_received_doc).decode("utf-8")
    for forbidden in ('"basis"', '"offset_m"',
                      '"outer_skin"', '"zone_edges"'):
        assert forbidden not in text, forbidden
    assert '"boundary_condition"' in text
    # 171 pre-A-11 -> 179: the 1 mm ingest snap lets one as-received-F1
    # cavity that was a ring LOSS close into a ring (83 -> 91 edges; the
    # ring_losses readout goes 1 -> 0 -- see the EXPECTED table's A-11 note).
    assert sum(len(view.boundary_edges) for view in as_received_doc.views) == 179


def test_r2_no_s7_dependency_in_the_module_source():
    """⭐ Acceptance 5, ⛔ measured on the file, not asserted in prose."""
    import ast

    path = REPO / "src/agent/judge/as_measured.py"
    source = path.read_text(encoding="utf-8")
    forbidden = ("ZoneEdgeReportV1", "ZoneExpansion", "s7_expand_zones",
                 "run_p2_conversion", "extract_gt_v3", "ZoneEdge")
    # ⭐ Two independent checks, because they fail on different things.
    # (a) TEXT: the raw grep the acceptance item asks for -- it also catches a
    #     name reached by getattr/string, which an AST walk would miss.
    for name in forbidden:
        assert name not in source, f"{name} appears in {path}"
    # (b) REFERENCES: every identifier the module actually names.  A text grep
    #     alone conflates "not used" with "not spelled"
    #     ([[grep-zero-hits-conflates-unused-with-nonexistent]]); this is the
    #     half that says the module never *reaches* S5-S7.
    tree = ast.parse(source)
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    used |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            used |= {alias.name for alias in node.names}
            used.add(node.module or "")
        elif isinstance(node, ast.Import):
            used |= {alias.name for alias in node.names}
    assert not (set(forbidden) & used), sorted(set(forbidden) & used)
    # ⛔ and the module reaches P1 only
    assert "run_p1_plan_view" in used


def test_r2_every_coordinate_is_an_integer(as_received_doc, signed_doc):
    """⭐ Acceptance 6.  ⛔ Not "the coordinates I remembered to check" -- the
    whole tree is walked, and the ONE subtree allowed to hold floats is named.

    ``converter_readouts`` carries the converter's own records in the
    converter's own frames (``points_dxf_mm``, and whatever a diagnostic's
    ``context`` holds).  Rounding those would be recomputing them, which is
    precisely what "原样搬" forbids.
    """
    def walk(node, path):
        if isinstance(node, float):
            yield path
        elif isinstance(node, dict):
            for key, value in node.items():
                yield from walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from walk(value, f"{path}[{index}]")

    for doc in (as_received_doc, signed_doc):
        floats = list(walk(doc.model_dump(mode="json"), "$"))
        stray = [p for p in floats if ".converter_readouts." not in p]
        assert stray == [], stray
        assert all(isinstance(f.const, int) and isinstance(f.along_min, int)
                   for v in doc.views for f in v.face_lines)


def test_r2_the_ledger_identity_has_teeth(as_received_doc):
    """⛔ Prove the "every stroke is accounted for" validator can go red.

    [[gate-with-only-negative-assertions-is-unobservable]]: an identity that
    only ever holds is indistinguishable from one that is never evaluated.
    """
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["face_lines"].pop()          # a stroke silently leaves the record
    with pytest.raises(ValueError, match="as_measured_wall_line_ledger_broken"):
        AsMeasuredV1.model_validate(raw)


def test_r2_a_dangling_reference_is_refused(as_received_doc):
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    wall = next(w for w in view["walls"] if w["face_line_ids_lo"])
    wall["face_line_ids_lo"] = ["FFFF"]
    with pytest.raises(ValueError, match="as_measured_dangling_face_line_ref"):
        AsMeasuredV1.model_validate(raw)


# =========================================================================== #
# F-136/A3 (②-1b-R R4): the WIDER S1 handle ledger has teeth
# =========================================================================== #
def test_r4_the_wider_s1_identity_is_real_on_as_received_plan_f1(as_received_doc):
    """⭐ Sanity, MEASURED: AS-RECEIVED plan-F1 has 226 collected handles.

    ⚠️ ②-1b-S UPDATE: this used to read 223 in ``wall_lines_total`` with
    13AD/13AE itemized in ``s1_nonorthogonal_discarded_handles`` (both S1
    -discarded, pre-snap).  Dispatch ②-1b-S R1 ADMITTED both via the snap
    path instead of discarding them, so they moved INTO ``wall_lines_total``
    and ``s1_nonorthogonal_discarded_handles`` became empty.

    ⚠️ G-c UPDATE (2026-09-07): ``wall_lines_total`` is UNCHANGED at 225 --
    ⭐ and that is the point worth reading.  13AF was already inside
    ``wall_lines_total`` before the ladder (it reached ``geo.wall_lines`` as a
    SKEW stroke, which is a different population from the S1 discards); what
    the ladder changed is that it is now axis-aligned there, so it also
    becomes a ``face_lines`` entry instead of a ``non_orthogonal_lines`` one.
    ⇒ this identity moves not at all, and the snap list gains one handle.

    ⚠️ MUST use as-received, not signed: on the signed drawing all three lines
    are already exact (no snap needed), so the snap list there is empty.
    """
    view = next(v for v in as_received_doc.views if v.view_id == "plan-F1")
    r = view.converter_readouts
    assert len(r.all_wall_handles) == 226
    assert r.wall_lines_total == 225
    assert r.s1_nonorthogonal_discarded_handles == []
    assert sorted(s.id for s in r.axis_snapped_lines) == ["13AD", "13AE", "13AF"]
    assert r.degenerate_line_handles == ["13DC"]
    assert r.degenerate_line_count == 1
    assert (len(r.all_wall_handles)
           == r.wall_lines_total + len(r.s1_nonorthogonal_discarded_handles)
           + r.degenerate_line_count)


def test_r4_removing_13dc_from_the_itemized_list_turns_the_identity_red(as_received_doc):
    """⭐⭐ Verification (dispatch ②-1b-R R4): "把 13DC 从零长清单里删掉 ⇒
    恒等式必须红" -- this is the self-proof that the new ledger has teeth
    and is not merely vacuously true today."""
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    assert "13DC" in view["converter_readouts"]["degenerate_line_handles"]
    view["converter_readouts"]["degenerate_line_handles"] = []
    with pytest.raises(ValueError, match="as_measured_degenerate_line_handles_count_mismatch"):
        AsMeasuredV1.model_validate(raw)


def test_r4_removing_13dc_and_its_count_together_breaks_the_primary_identity(as_received_doc):
    """The SAME tamper, isolating the PRIMARY (all_wall_handles) identity
    from the secondary (list-length-matches-count) one: drop 13DC from both
    the itemized list AND the count it feeds, so only the wider identity can
    catch it."""
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["converter_readouts"]["degenerate_line_handles"] = []
    view["converter_readouts"]["degenerate_line_count"] = 0
    with pytest.raises(ValueError, match="as_measured_s1_handle_ledger_broken"):
        AsMeasuredV1.model_validate(raw)


def test_r4_consumed_wall_handles_field_is_gone(as_received_doc):
    """F-136/A3: the field was structurally always empty (zero write sites
    repo-wide) and is now deleted, not silently carried forward."""
    readouts = as_received_doc.views[0].converter_readouts
    assert not hasattr(readouts, "consumed_wall_handles")
    assert "consumed_wall_handles" not in readouts.model_dump(mode="json")


# =========================================================================== #
# ②-1b-S R1/R2/R3 -- the snap list ("吸附清单") is real, real data holds two
# entries, and the ledger it feeds has teeth (⛔ delete an entry -> must go red)
# =========================================================================== #
def test_o21bs_the_real_snap_list_has_exactly_the_three_known_handles(as_received_doc):
    """⭐ Acceptance 1: the real as-received sm25 plan-F1 snap list, and every
    field R2/F-148 demands on each entry (handle, before, axis, magnitude,
    angle).

    ⚠️ G-c UPDATE (2026-09-07): THREE handles, ⛔ not two.  13AF joins them --
    it is the same wall's 120 mm west end cap, tilted by the same 329 arcsec
    rotation, and it used to fall into the gap between the snap branch's old
    ``tau_axis`` entrance (1 mm) and the face-line classifier's exact-equality
    test, so it was refused by both and appeared in neither table.  The ladder
    enters on ``q`` (0.1 mm), which is the real noise floor.
    """
    view = next(v for v in as_received_doc.views if v.view_id == "plan-F1")
    snapped = {s.id: s for s in view.converter_readouts.axis_snapped_lines}
    assert sorted(snapped) == ["13AD", "13AE", "13AF"]
    for s in snapped.values():
        assert s.before_p0 != s.before_p1          # was genuinely skew before
        assert s.angle_deg == pytest.approx(0.0914, abs=5e-4)
    for handle in ("13AD", "13AE"):                # the two long faces
        s = snapped[handle]
        assert s.snapped_axis == "y"
        assert s.after_p0[1] == s.after_p1[1]       # exactly axis-aligned after
        assert 55 <= s.minor_leg_units <= 60, (     # ~5.81 mm == 58 units of 0.1mm
            "minor_leg_units drifted away from the measured ~5.81 mm skew")
    cap = snapped["13AF"]                           # the end cap
    assert cap.snapped_axis == "x"
    assert cap.after_p0[0] == cap.after_p1[0]
    assert cap.minor_leg_units == 2, (              # 0.1915 mm -> 2 units of 0.1 mm
        "the end cap's skew is ~0.19 mm -- the value that used to disappear")


def test_f148_snap_list_angle_is_required_and_bound_to_its_diagnostic(as_received_doc):
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    del view["converter_readouts"]["axis_snapped_lines"][0]["angle_deg"]
    with pytest.raises(ValueError):
        AsMeasuredV1.model_validate(raw)

    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["converter_readouts"]["axis_snapped_lines"][0]["angle_deg"] += 0.1
    with pytest.raises(
            ValueError, match="as_measured_axis_snapped_angle_disagrees_with_diagnostic"):
        AsMeasuredV1.model_validate(raw)


def test_o21bs_deleting_a_snap_entry_turns_the_ledger_red(as_received_doc):
    """⭐⭐ Dispatch ②-1b-S R3's explicit self-proof requirement: "把吸附清单
    里任一条删掉 -> 恒等式必须红".  The face line itself (still 13AD, still a
    real orthogonal stroke) is untouched -- only its itemisation entry in
    ``axis_snapped_lines`` is removed, proving the CROSS-COUNT check (not
    just "the list is non-empty") is what has teeth here."""
    original = as_received_doc.model_dump(mode="json")
    view = next(v for v in original["views"] if v["view_id"] == "plan-F1")
    snapped = view["converter_readouts"]["axis_snapped_lines"]
    assert len(snapped) == 3, "premise: the fixture really holds 3 entries"
    for removed in snapped:
        raw = copy.deepcopy(original)
        target = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
        target["converter_readouts"]["axis_snapped_lines"] = [
            row for row in snapped if row["id"] != removed["id"]]
        with pytest.raises(ValueError, match="as_measured_axis_snapped_ledger_broken"):
            AsMeasuredV1.model_validate(raw)


def test_o21bs_a_snapped_handle_must_be_a_real_face_line(as_received_doc):
    """⭐ GLM's exact demand (R2): "被吸附过" and "本来就是正的" must never look
    the same, AND a snap entry can never point at a handle that is not
    actually IN the answer -- itemised-and-then-also-dropped is refused."""
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    fabricated = dict(view["converter_readouts"]["axis_snapped_lines"][0])
    fabricated["id"] = "FFFF"   # not a real face line handle anywhere
    view["converter_readouts"]["axis_snapped_lines"].append(fabricated)
    # keep the cross-count check quiet by also faking a matching diagnostic,
    # isolating the OTHER validator (dangling-handle) this test targets
    view["converter_readouts"]["diagnostics"].append({
        "code": "tarch_wall_axis_snapped", "severity": "INFO", "stage": "S1_QUANTIZE",
        "action_code": None, "handles": ["FFFF"], "points_dxf_mm": [],
        "context": {"angle_deg": fabricated["angle_deg"]}})
    with pytest.raises(ValueError, match="as_measured_axis_snapped_not_a_face_line"):
        AsMeasuredV1.model_validate(raw)


def test_o21bs_a_handle_cannot_be_both_snapped_and_s1_discarded(as_received_doc):
    """Admitted and refused are mutually exclusive outcomes for one stroke --
    a real tier-1 snap entry cannot ALSO claim to have been S1-discarded."""
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    handle = view["converter_readouts"]["axis_snapped_lines"][0]["id"]
    view["converter_readouts"]["s1_nonorthogonal_discarded_handles"].append(handle)
    with pytest.raises(ValueError, match="as_measured_axis_snapped_also_discarded"):
        AsMeasuredV1.model_validate(raw)


def test_r2_readouts_are_the_converters_own_numbers(as_received_doc, tmp_path):
    """Compare readouts against P1 on both clean and constructed BLOCK stock.

    G-c removed every real BLOCK from the as-received drawing.  Comparing
    only that drawing no longer detects a producer that strips all BLOCKs.
    An isolated axial stroke supplies a real free-end diagnostic and G5 red,
    while the nonempty geometry still builds facts successfully.
    """
    from tests.test_as_drawn_denominator_consistency_readout import (
        _as_received_with_an_orphan_segment)
    from src.agent.judge.tarch_normalize import run_p1_plan_view

    geo, view_intent = _geo_for("plan-F1")
    view = next(v for v in as_received_doc.views if v.view_id == "plan-F1")
    _assert_converter_readouts_match(view.converter_readouts, geo)

    dxf, request_path = _as_received_with_an_orphan_segment(tmp_path)
    request = TarchConversionRequestV1.model_validate_json(request_path.read_text())
    tooling = load_gt_tooling_config(REPO / "src" / "configs" / "judge_gt.yaml",
                                     REPO / "src" / "configs" / "correction.yaml")
    intent = next(v for v in request.plan_views if v.id == "plan-F1")
    blocked_geo = run_p1_plan_view(dxf, request, intent, tooling)
    assert any(d.severity == "BLOCK" for d in blocked_geo.diagnostics)
    assert blocked_geo.dangles > 0
    blocked_view = build_view(blocked_geo, intent.world_from_source_m,
                              t_max_m=max(request.wall_thickness_range_m))
    assert blocked_view.face_lines and blocked_view.walls
    _assert_converter_readouts_match(blocked_view.converter_readouts, blocked_geo)


def _assert_converter_readouts_match(readouts, geo):
    assert (readouts.dangles, readouts.cuts, readouts.invalid) == (
        geo.dangles, geo.cuts, geo.invalid)
    assert readouts.degenerate_line_count == geo.degenerate_line_count
    assert readouts.wall_lines_total == len(geo.wall_lines)
    assert [d["code"] for d in readouts.diagnostics] == [
        str(getattr(d.code, "value", d.code)) for d in geo.diagnostics]
    assert [(g["id"], g["passed"]) for g in readouts.gates] == [
        (g.id, g.passed) for g in geo.gates]


def test_r2_a_rotating_affine_is_refused_not_mislabelled():
    """⛔ A constant-coordinate face line does not exist under a rotation, and
    the layer must say so instead of writing an axis it invented."""
    request = TarchConversionRequestV1.model_validate_json(
        AS_MEASURED_REQUEST.read_text(encoding="utf-8"))
    affine = request.plan_views[0].world_from_source_m
    rotated = affine.model_copy(update={"m01": 0.001, "m10": -0.001})
    with pytest.raises(AsMeasuredUnavailable, match="non_axis_aligned_affine"):
        am._axis_aligned(rotated, "plan-F1")


def test_r2_to_units_is_the_declared_scale():
    assert to_units(1.0) == 10_000
    assert to_units(0.0001) == 1
    assert to_units(-0.0) == 0
    assert to_units(9.94) == 99_400


# =========================================================================== #
# R3 -- bit reproducibility, ⛔ with no PYTHONHASHSEED holding it up
# =========================================================================== #
_SUBPROCESS = """
import hashlib, json, sys
from pathlib import Path
from src.agent.judge.as_measured import build_as_measured, canonical_bytes
import src.agent.judge.as_measured as module
doc = build_as_measured(Path(sys.argv[1]), Path(sys.argv[2]))
print(json.dumps({
    "code_from": module.__file__,
    "hash_randomization": bool(sys.flags.hash_randomization),
    "str_hash": hash("as_measured_reproducibility_probe"),
    "sha256": hashlib.sha256(canonical_bytes(doc)).hexdigest(),
    "bytes": len(canonical_bytes(doc)),
}))
"""


def _fresh_process_build() -> dict:
    """⭐ ``PYTHONPATH`` forced and ``CODE_FROM`` self-reported.

    [[reproduce-the-form-not-the-run]] / the ②-1a dispatch §六.1: a probe run as
    ``python /tmp/x.py`` puts the SCRIPT's directory on ``sys.path[0]`` and then
    silently resolves ``src`` through the editable install -- the last unit's
    reviewer compared the main tree against itself that way and read "zero
    difference".  ``-c`` plus an explicit ``PYTHONPATH`` plus the reported
    ``__file__`` makes that failure impossible to miss.
    """
    env = os.environ.copy()
    env.pop("PYTHONHASHSEED", None)       # ⛔ the whole point: no seed pinning
    env["PYTHONPATH"] = str(REPO)
    completed = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS, str(AS_RECEIVED_DXF), str(AS_MEASURED_REQUEST)],
        cwd=REPO, env=env, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_r3_three_fresh_processes_agree_bit_for_bit():
    """⭐⭐ Acceptance 3.  ⛔ ``PYTHONHASHSEED`` is REMOVED from the environment.

    The repo already carries the known defect this gate has to survive: the
    converter's DXF bytes and ``content_sha256`` are hash-order dependent, and
    the existing lock for that (``test_tarch_converter_reproducibility``) pins
    three explicit seeds.  ⛔ Pinning a seed here would prove nothing about the
    default configuration, which is the one every real run uses.

    ⭐ And the runs SELF-PROVE that the seeds actually differed: if every
    process reported the same ``hash("...")`` then randomisation was off and
    "the three agreed" would be vacuous ([[gate-with-only-negative-assertions-is-unobservable]]).
    """
    runs = [_fresh_process_build() for _ in range(3)]
    for run in runs:
        assert run["code_from"] == str(REPO / "src/agent/judge/as_measured.py"), run
        assert run["hash_randomization"], "hash randomisation is off; gate is vacuous"
    assert len({r["str_hash"] for r in runs}) == 3, (
        "the three processes drew the SAME string-hash seed; this run cannot "
        f"tell a seed-independent builder from a lucky one: {runs}")
    assert len({r["sha256"] for r in runs}) == 1, runs
    assert len({r["bytes"] for r in runs}) == 1, runs


def test_r3_the_digest_reads_the_coordinates(as_received_doc):
    """⭐ Acceptance 4, mutation direction 1: move one face line by 0.1 mm.

    ⛔ The smallest representable move.  If the digest survived it, the gate
    would be pinning something other than the geometry.
    """
    before = content_sha256(as_received_doc)
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["face_lines"][0]["const"] += 1
    assert content_sha256(AsMeasuredV1.model_validate(raw)) != before


def test_r3_the_digest_reads_the_readouts(as_received_doc):
    """⭐ Acceptance 4, mutation direction 2: a converter readout, not a
    coordinate.  [[neuter-proves-wiring-not-discriminating-power]] -- one
    mutation direction only proves that direction."""
    before = content_sha256(as_received_doc)
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["converter_readouts"]["dangles"] += 1
    assert content_sha256(AsMeasuredV1.model_validate(raw)) != before


def _geo_for(view_id: str):
    import shutil
    import tempfile

    from src.agent.judge.tarch_normalize import run_p1_plan_view

    request = TarchConversionRequestV1.model_validate_json(
        AS_MEASURED_REQUEST.read_text(encoding="utf-8"))
    tooling = load_gt_tooling_config(REPO / "src/configs/judge_gt.yaml",
                                     REPO / "src/configs/correction.yaml")
    view_intent = next(v for v in request.plan_views if v.id == view_id)
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / AS_RECEIVED_DXF.name
        shutil.copy2(AS_RECEIVED_DXF, staged)
        return run_p1_plan_view(staged, request, view_intent, tooling), view_intent


def canonical_bytes_of_view(view) -> bytes:
    return json.dumps(view.model_dump(mode="json"), sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _reversed_geo(geo):
    """The same measurement, delivered in the opposite order.

    ⛔ ``all_wall_handles`` is handed over as a LIST, not a set, on purpose: a
    set cannot be given an order to reverse, so a set-based probe could not tell
    "the builder sorts" from "the two sets happened to iterate alike".  A list
    makes the input order real and therefore makes the neuter below observable.
    """
    return dataclasses.replace(
        geo,
        wall_lines=list(reversed(geo.wall_lines)),
        wall_bands=list(reversed(geo.wall_bands)),
        openings=list(reversed(geo.openings)),
        all_wall_handles=list(reversed(sorted(geo.all_wall_handles))))


def test_r3_upstream_iteration_order_cannot_move_the_digest():
    """⭐⭐ Acceptance 4, mutation direction 3 -- the direction the SEED attacks.

    ⛔ The two mutations above change the CONTENT.  This one changes only the
    ORDER in which the same content arrives, which is exactly what a different
    string-hash seed does upstream: ``all_wall_handles`` is a ``set[str]`` and
    ``str`` is the type Python randomises.  Reversing every input list must
    leave the document byte-identical.
    """
    geo, view_intent = _geo_for("plan-F1")
    affine = view_intent.world_from_source_m
    straight = canonical_bytes_of_view(build_view(geo, affine, t_max_m=T_MAX_M))
    flipped = canonical_bytes_of_view(
        build_view(_reversed_geo(geo), affine, t_max_m=T_MAX_M))
    assert straight == flipped


#: ⭐ Four INDEPENDENT ordering seams, neutered one at a time.
#: [[neuter-proves-wiring-not-discriminating-power]] and the ②-1a dispatch §六.2:
#: "the teeth of a lock are spread across different mutation directions" -- a
#: single neuter would prove only that ONE of the four sorts is load-bearing,
#: and the other three could be dead code holding nothing up.
#: ⚠️⚠️ ②-1a-R REPLACED ``_wall_sort_key`` here with ``_band_sort_key``, and the
#: swap is a measurement, ⛔ not tidying ([[moving-a-gate-to-a-new-measurement-point]]):
#: walls no longer come from ``geo.wall_bands`` in upstream order, they come
#: from ``face_line_targets``, which sorts its own groups.  So reversing the
#: input leaves the wall order alone EVEN WITH ``_wall_sort_key`` neutered --
#: this seam has no teeth in the reversal direction any more, and leaving it in
#: the list would have made the test fail honestly rather than pass vacuously.
#: ⭐ ``_wall_sort_key`` still uniquely holds the DOCUMENTED TOTAL ORDER up, and
#: ``test_r3_the_wall_sort_key_is_what_makes_walls_totally_ordered`` measures it
#: in that direction.  ``geo.wall_bands`` IS still delivered in upstream order,
#: so ``_band_sort_key`` inherits the reversal tooth this slot needs.
_ORDERING_SEAMS = ("_face_line_sort_key", "_band_sort_key", "_opening_sort_key",
                   "_sorted_handles")


@pytest.mark.parametrize("seam", _ORDERING_SEAMS)
def test_r3_each_ordering_seam_is_load_bearing(monkeypatch, seam):
    """⛔ Guards the guard: with this seam neutered, the lock above goes RED.

    Neutering a sort KEY to a constant is a no-op sort (Python's sort is
    stable), so the builder's output order becomes the INPUT's order -- and the
    reversed input then produces different bytes.  ⭐ If it did not, that seam
    would be protecting nothing and the reproducibility gate would be resting on
    luck in that direction.

    The patch is applied to the MODULE object because that is where the builder
    resolves the name at call time ([[shadow-module-swap-must-touch-parent-attr]]:
    ``from X import Y`` binds through the parent attribute, so patching
    ``sys.modules`` would silently miss).
    """
    geo, view_intent = _geo_for("plan-F1")
    affine = view_intent.world_from_source_m
    neuter = (lambda values: list(values)) if seam == "_sorted_handles" else (lambda item: 0)
    monkeypatch.setattr(am, seam, neuter)
    straight = canonical_bytes_of_view(build_view(geo, affine, t_max_m=T_MAX_M))
    flipped = canonical_bytes_of_view(
        build_view(_reversed_geo(geo), affine, t_max_m=T_MAX_M))
    assert straight != flipped, (
        f"neutering {seam} changed nothing -- that seam is not what keeps the "
        "document order-independent, so the gate has no teeth in its direction")


def test_r3_the_builder_leaves_every_list_in_a_total_order(as_received_doc, signed_doc):
    """The property the fresh-process gate depends on, stated directly."""
    for doc in (as_received_doc, signed_doc):
        assert [v.view_id for v in doc.views] == sorted(v.view_id for v in doc.views)
        for view in doc.views:
            faces = view.face_lines
            assert faces == sorted(
                faces, key=lambda f: (f.axis, f.const, f.along_min, f.along_max, f.id))
            walls = view.walls
            assert walls == sorted(walls, key=lambda w: (
                w.axis, w.face_lo, w.face_hi, w.along_min, w.along_max, w.id))
            openings = view.openings
            assert openings == sorted(openings, key=lambda o: (
                o.axis, o.cross_lo, o.cross_hi, o.along_min, o.along_max, o.id))
            readouts = view.converter_readouts
            assert readouts.all_wall_handles == sorted(readouts.all_wall_handles)
            for name in ("jamb_cap_bands_missing_a_face_line",
                         "face_lines_excluded_as_jamb_caps",
                         "face_lines_not_paired_into_a_wall",
                         "s1_nonorthogonal_discarded_handles",
                         "degenerate_line_handles"):
                got = getattr(readouts, name)
                assert got == sorted(got), name
            assert ([b["band_id"] for b in readouts.jamb_cap_bands]
                    == sorted(b["band_id"] for b in readouts.jamb_cap_bands))
            for wall in walls:
                assert wall.face_line_ids_lo == sorted(wall.face_line_ids_lo)
                assert wall.face_line_ids_hi == sorted(wall.face_line_ids_hi)
            for opening in openings:
                assert opening.jamb_handles == sorted(opening.jamb_handles)
                assert opening.carrier_wall_ids == sorted(opening.carrier_wall_ids)


def test_r3_in_process_rebuild_is_byte_identical():
    """The cheap half of the gate: same process, same bytes."""
    first = build_as_measured(AS_RECEIVED_DXF, AS_MEASURED_REQUEST, view_ids=["plan-F1"])
    second = build_as_measured(AS_RECEIVED_DXF, AS_MEASURED_REQUEST, view_ids=["plan-F1"])
    assert canonical_bytes(first) == canonical_bytes(second)
    assert content_sha256(first) == content_sha256(second)


def test_r3_a_deep_copy_of_the_document_hashes_the_same(as_received_doc):
    assert content_sha256(copy.deepcopy(as_received_doc)) == content_sha256(as_received_doc)


# =========================================================================== #
# ②-1a-R -- ``walls`` comes from PAIRED FACE LINES, ⛔ not from ``wall_bands``
# =========================================================================== #
def _thicknesses_from_wall_bands_mm(geo, affine) -> dict[int, int]:
    """②-1a's mapping, kept HERE and nowhere in ``src`` -- ⛔ its only job is to
    prove the acceptance above can go RED.

    A gate that only ever sees the fixed build cannot tell "the walls are right"
    from "this assertion is true of anything"
    ([[gate-with-only-negative-assertions-is-unobservable]]).
    """
    sx, tx, sy, ty = affine.m00, affine.m02, affine.m11, affine.m12
    out = []
    for band in geo.wall_bands:
        if band.axis == "x":               # runs along x, faces are y coords
            lo, hi = to_units(sy * band.face_lo_mm + ty), to_units(sy * band.face_hi_mm + ty)
        else:
            lo, hi = to_units(sx * band.face_lo_mm + tx), to_units(sx * band.face_hi_mm + tx)
        lo, hi = (lo, hi) if lo <= hi else (hi, lo)
        out.append((hi - lo) // 10)
    return dict(sorted(collections.Counter(out).items()))


def test_r1_the_old_wall_band_source_makes_the_thickness_gate_go_red():
    """⭐⭐ Acceptance ④ (anti-vacuity): put the OLD source back, gate must fail.

    MEASURED on signed ``plan-F1``: the band mapping yields 45 "walls" whose
    thicknesses are {100, 120, 240, 296, 300, 304, 356, 360, 364, 500} mm.  The
    drawing contains 120 and 240 only -- 300 mm appears SIXTEEN times and is a
    door/window jamb paired with the face of a real 120 mm partition 300 mm
    away.  ⛔ The counts alone would not have caught this (45 walls looks like a
    plausible number); only the THICKNESS does.
    """
    geo, view_intent = _geo_for("plan-F1")
    band_hist = _thicknesses_from_wall_bands_mm(geo, view_intent.world_from_source_m)
    assert set(band_hist) - {120, 240}, (
        "the band source no longer produces impossible thicknesses -- then this "
        "guard proves nothing and the acceptance above is vacuous")
    assert band_hist.get(300, 0) >= 10, band_hist
    paired = build_view(geo, view_intent.world_from_source_m, t_max_m=T_MAX_M)
    assert set(thickness_hist_mm(paired.walls)) == {120, 240}, "the fixed build"


def test_r1_pairing_every_collected_face_line_puts_the_ghost_walls_back():
    """⛔⛔ The trap the rework order names in bold: 225 face lines, 110 pairable.

    The exclusion is not a detail of the pairing -- it IS the fix.  Pairing
    every collected stroke (i.e. skipping D2, which is what "just pair the face
    lines" would mean if taken literally) reproduces the same impossible
    thicknesses, because the other 115 strokes ARE the jamb caps and stubs.

    ⭐ This is the direction that proves the REUSE is load-bearing: the shared
    ``face_line_targets`` pass, not the two-line pairing loop, is what deletes
    the ghosts.
    """
    geo, view_intent = _geo_for("plan-F1")
    view = build_view(geo, view_intent.world_from_source_m, t_max_m=T_MAX_M)
    # ⭐ ②-1b-S R1 admitted 13AD/13AE (222 -> 224); ⭐ G-c admitted 13AF as
    # well (224 -> 225).  Still as-received plan-F1.
    assert len(view.face_lines) == 225
    every_stroke = [{"axis": "y" if f.axis == "x" else "x",   # ⚠️ into DEN's frame
                     "const_m": f.const / am.UNITS_PER_METRE,
                     "lo_m": f.along_min / am.UNITS_PER_METRE,
                     "hi_m": f.along_max / am.UNITS_PER_METRE,
                     "handles": [f.id]}
                    for f in view.face_lines]
    ghosts, _unpaired = am._pair_face_lines_into_walls(
        every_stroke, {f.id for f in view.face_lines})
    ghost_hist = thickness_hist_mm(ghosts)
    assert set(ghost_hist) - {120, 240}, (
        "pairing ALL 225 strokes produced only real thicknesses -- then D2's "
        "exclusion is not what is holding the fix up and this unit is wrong "
        f"about why it works: {ghost_hist}")
    assert set(thickness_hist_mm(view.walls)) == {120, 240}


def test_r1_a_wall_cannot_be_built_without_ink_on_both_faces():
    """⭐ Acceptance ③ (zero ghosts) as a STRUCTURAL impossibility, ⛔ not a scan.

    ②-1a could record a wall whose second face had no stroke at all; that is
    what a jamb-cap band is.  Making it a schema refusal means a future edit
    cannot reintroduce the class by forgetting to run a filter.
    """
    from pydantic import ValidationError

    good = dict(id="w_x_0_1200_0_1000", axis="x", face_lo=0, face_hi=1200,
                thickness=1200, along_min=0, along_max=1000,
                face_line_ids_lo=["1A"], face_line_ids_hi=["1B"])
    am.AsMeasuredWallV1(**good)                      # the premise: this is legal
    for side in ("face_line_ids_lo", "face_line_ids_hi"):
        with pytest.raises(ValidationError):
            am.AsMeasuredWallV1(**{**good, side: []})


def test_r1_the_face_line_consumption_ledger_has_teeth(signed_doc):
    """⛔ Prove the 225-vs-110 ledger can go red, in BOTH of its directions.

    A stroke that is neither in a wall, nor excluded as a cap, nor named as
    unpaired has left the record silently -- which is exactly the failure mode
    the whole unit is about.
    """
    raw = signed_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    assert view["converter_readouts"]["face_lines_excluded_as_jamb_caps"]

    dropped = copy.deepcopy(raw)
    v = next(x for x in dropped["views"] if x["view_id"] == "plan-F1")
    v["converter_readouts"]["face_lines_excluded_as_jamb_caps"].pop()
    with pytest.raises(Exception, match="consumption_ledger_broken"):
        AsMeasuredV1.model_validate(dropped)

    doubled = copy.deepcopy(raw)
    v = next(x for x in doubled["views"] if x["view_id"] == "plan-F1")
    a_wall = v["walls"][0]["face_line_ids_lo"][0]
    v["converter_readouts"]["face_lines_excluded_as_jamb_caps"].append(a_wall)
    with pytest.raises(Exception, match="face_line_in_two_buckets"):
        AsMeasuredV1.model_validate(doubled)


def test_r1_the_wall_axis_and_its_face_lines_agree_after_the_one_flip(
        signed_doc, as_received_doc):
    """⚠️⚠️ The axis flip, measured -- ⛔ not asserted in a comment.

    ``denominator``'s ``axis`` names the axis the CONSTANT sits on; this
    module's names the axis a line RUNS ALONG.  They are opposite, and both the
    orchestrator and this seat mis-read it once while diagnosing the ghosts.
    If the single flip in ``_pair_face_lines_into_walls`` were dropped, every
    wall would claim the running axis of the perpendicular family and this goes
    red on all four views ([[cross-representation-mutation-must-be-equivalent]]).
    """
    for doc in (signed_doc, as_received_doc):
        for view in doc.views:
            by_id = {f.id: f for f in view.face_lines}
            split = {c for g in view.converter_readouts.face_groups_with_a_split_const
                     for c in g["member_consts"]}
            assert view.walls
            for wall in view.walls:
                for const, refs in ((wall.face_lo, wall.face_line_ids_lo),
                                    (wall.face_hi, wall.face_line_ids_hi)):
                    for handle in refs:
                        face = by_id[handle]
                        assert face.axis == wall.axis, (
                            f"{wall.id}/{handle}: the denominator->document axis "
                            "flip is wrong")
                        assert face.const == const or face.const in split, (
                            wall.id, handle, face.const, const)


def test_r3_the_wall_sort_key_is_what_makes_walls_totally_ordered():
    """⭐ ``_wall_sort_key``'s tooth MOVED; this measures it where it now is.

    It is no longer what makes a reversed input produce identical bytes (the
    upstream ``face_line_targets`` sorts its own groups), so it was taken out of
    ``_ORDERING_SEAMS``.  ⛔ Taking it out without measuring it somewhere else
    would have left a sort nothing proves -- so: neuter it, and the documented
    total order must break.
    """
    geo, view_intent = _geo_for("plan-F1")
    affine = view_intent.world_from_source_m
    key = (lambda w: (w.axis, w.face_lo, w.face_hi, w.along_min, w.along_max, w.id))

    ordered = build_view(geo, affine, t_max_m=T_MAX_M).walls
    assert ordered == sorted(ordered, key=key)

    original = am._wall_sort_key
    try:
        am._wall_sort_key = lambda wall: 0
        neutered = build_view(geo, affine, t_max_m=T_MAX_M).walls
    finally:
        am._wall_sort_key = original
    assert neutered != sorted(neutered, key=key), (
        "with _wall_sort_key neutered the walls came out totally ordered anyway "
        "-- then that key is holding nothing up in any direction")


# =========================================================================== #
# ②-1a-R rework audit ③ -- "a DIFFERENT input of the same shape still works"
# =========================================================================== #
#  ⛔ The two halves above only ever prove "this example is fixed".  A SYNTHETIC
#  plan is the third input whose answer is known BY CONSTRUCTION, so it can be
#  asked the question the two real drawings cannot: is the JAMB-CAP EXCLUSION
#  what removes the ghosts, or did sm25 just happen to come out clean?
# =========================================================================== #
def _synthetic_geo():
    """A 10 x 6 m room, 240 mm envelope, one 120 mm partition with a door.

    Coordinates are DXF-native millimetres; the affine below is the usual
    ``x/1000`` used by both shipped anchors.  ⭐ The two 120 mm strokes at the
    door reveal are REAL jamb caps -- the very shape that produced sm25's 16
    fictitious "300 mm walls" when the record was built from ``wall_bands``.
    """
    from src.agent.judge.tarch_normalize import P1PlanViewGeometry

    def h(x0, y0, x1, y1):
        return (x0, y0, x1, y1)

    strokes = {
        # envelope: two faces per side, 240 mm apart
        "A1": h(0, 0, 10000, 0),        "A2": h(0, 240, 10000, 240),
        "A3": h(0, 5760, 10000, 5760),  "A4": h(0, 6000, 10000, 6000),
        "A5": h(0, 0, 0, 6000),         "A6": h(240, 0, 240, 6000),
        "A7": h(9760, 0, 9760, 6000),   "A8": h(10000, 0, 10000, 6000),
        # 120 mm partition, each face drawn as TWO runs because a door splits it
        "B1": h(4940, 240, 4940, 2000), "B2": h(4940, 2900, 4940, 5760),
        "B3": h(5060, 240, 5060, 2000), "B4": h(5060, 2900, 5060, 5760),
        # the door's two jamb caps -- 120 mm long, spanning BETWEEN the faces
        "C1": h(4940, 2000, 5060, 2000),
        "C2": h(4940, 2900, 5060, 2900),
    }
    wall_lines = [(k, *v) for k, v in sorted(strokes.items())]
    return P1PlanViewGeometry(
        view_id="plan-SYN", floor_id="F1", quant_step_native=1.0,
        wall_lines=wall_lines, degenerate_line_count=0,
        jamb_caps_v={}, jamb_caps_h={}, cap_handles_v={}, cap_handles_h={},
        wall_bands=[], openings=[], opening_fills=[], faces=[],
        dangles=0, cuts=0, invalid=0, sum_area_m2=0.0, footprint_area_m2=0.0,
        footprint_polygon=None,
        wall_line_layers={k: "WALL" for k in strokes},
        diagnostics=[], gates=[],
        all_wall_handles=set(strokes))


def _synthetic_affine():
    from src.agent.judge.gt_manifest import Affine2D
    return Affine2D(m00=0.001, m01=0.0, m02=0.0, m10=0.0, m11=0.001, m12=0.0)


def test_r3_audit_a_synthetic_plan_yields_exactly_the_walls_it_was_built_from():
    """⭐⭐ Rework audit ③: a DIFFERENT input, whose answer is known a priori.

    Built into the fixture: 4 envelope walls of 240 mm and one 120 mm partition
    that a door cuts into 2 runs => 6 walls, {240: 4, 120: 2}, and ⛔ NOTHING
    else.  The two jamb caps must contribute no wall at all.
    """
    view = build_view(_synthetic_geo(), _synthetic_affine(), t_max_m=0.5)
    assert thickness_hist_mm(view.walls) == {120: 2, 240: 4}, [
        (w.id, w.thickness) for w in view.walls]
    readouts = view.converter_readouts
    assert readouts.face_lines_excluded_as_jamb_caps == ["C1", "C2"], (
        "the two door jambs are what D2 must exclude; if they are not here the "
        "next assertion is not measuring the exclusion")
    assert readouts.face_lines_not_paired_into_a_wall == []
    assert all(w.face_line_ids_lo and w.face_line_ids_hi for w in view.walls)
    # the partition really did come out as two runs, ⛔ not one welded through
    partitions = [w for w in view.walls if w.thickness == 1200]
    assert sorted((w.along_min, w.along_max) for w in partitions) == [
        (2400, 20000), (29000, 57600)]


def test_r3_audit_the_synthetic_plan_shows_the_caps_are_what_make_the_ghosts():
    """⛔ The other direction on the SAME fixture: skip the exclusion, and the
    ghost class comes straight back.

    MEASURED: the two jamb caps, paired with each other, invent a 900 mm "wall"
    -- the synthetic twin of sm25's 300 mm ghosts, which were a jamb paired
    with a real partition face.  ⭐ This is what makes the check above a test of
    the MECHANISM rather than of this fixture's luck.
    """
    view = build_view(_synthetic_geo(), _synthetic_affine(), t_max_m=0.5)
    every_stroke = [{"axis": "y" if f.axis == "x" else "x",   # ⚠️ into DEN's frame
                     "const_m": f.const / am.UNITS_PER_METRE,
                     "lo_m": f.along_min / am.UNITS_PER_METRE,
                     "hi_m": f.along_max / am.UNITS_PER_METRE,
                     "handles": [f.id]}
                    for f in view.face_lines]
    ghosts, _unpaired = am._pair_face_lines_into_walls(
        every_stroke, {f.id for f in view.face_lines})
    ghost_hist = thickness_hist_mm(ghosts)
    assert set(ghost_hist) - {120, 240}, ghost_hist
    assert 900 in ghost_hist, (
        f"expected the two jamb caps to invent a 900 mm wall, got {ghost_hist}")


def test_r3_audit_sm24_a_different_building_has_only_real_thicknesses():
    """⭐⭐ Rework audit ③, the real-drawing half: sm24 is a DIFFERENT building.

    ⚠️ The rework order expected this to be impossible ("sm24 已知会 BLOCK,
    F-132 晋升件漂移").  MEASURED, it is not: the request's declared
    ``source_dxf_label`` is ``sm24_source.dxf`` while the file on disk is
    ``source.dxf``, but the identity gate hashes BYTES, not names, and those
    match.  ⇒ sm24 runs, and it is the strongest of the three inputs because
    nothing about it was tuned by this unit.

    ⭐ Its 17 partitions at 120 mm are also the direct answer to the batch
    guide's §一 warning: filtering candidate pairs by declared thickness is what
    once deleted that whole family, and this pairing has no such filter.
    """
    doc = build_as_measured(SM24 / "source.dxf", SM24 / "request.json")
    view = next(v for v in doc.views if v.view_id == "plan-F1")
    assert thickness_hist_mm(view.walls) == {120: 17, 240: 18}
    assert all(w.face_line_ids_lo and w.face_line_ids_hi for w in view.walls)
    assert view.converter_readouts.face_lines_not_paired_into_a_wall == []


# =========================================================================== #
# B1 -- ②-1b R3: the "stated absence" is now a real (widened) fingerprint
# =========================================================================== #
def test_b1_the_field_is_no_longer_a_stated_none(as_received_doc):
    """The ②-1a placeholder was ``converter_implementation_fingerprint: None``.
    It must now be a real Hex64, and specifically the WIDENED (F-D, R4)
    conversion-closure fingerprint -- not some other, unrelated hash."""
    import re

    from src.agent.judge.tarch_normalize import converter_sha256

    value = as_received_doc.converter_implementation_fingerprint
    assert value is not None
    assert re.fullmatch(r"[0-9a-f]{64}", value)
    assert value == converter_sha256()


def test_b1_schema_no_longer_accepts_the_none_placeholder():
    """⛔ Structural, not just "the builder happens to fill it in": the type
    itself must refuse the ②-1a shape now that B1 is solved."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AsMeasuredV1.model_validate({
            "case": "probe", "source_dxf_label": "x.dxf",
            "source_dxf_sha256": "a" * 64, "request_sha256": "b" * 64,
            "converter_implementation_fingerprint": None,
            "views": [],
        })


def test_b1_two_documents_from_the_same_tree_agree_on_the_fingerprint(
        as_received_doc, signed_doc):
    """The fingerprint is a property of the IMPLEMENTATION, not of which
    drawing was measured -- as-received and signed docs share one value."""
    assert (as_received_doc.converter_implementation_fingerprint
            == signed_doc.converter_implementation_fingerprint)


def test_b1_content_sha256_covers_the_fingerprint_field(as_received_doc):
    """⭐ Acceptance-adjacent: FACTS' own hash must move if the fingerprint
    field is tampered, i.e. the field is inside the signed surface
    ``content_sha256`` actually covers -- not bolted on beside it."""
    before = content_sha256(as_received_doc)
    raw = as_received_doc.model_dump(mode="json")
    raw["converter_implementation_fingerprint"] = "0" * 64
    assert content_sha256(AsMeasuredV1.model_validate(raw)) != before


# =========================================================================== #
# ⭐⭐⭐ G-c / A-11-d3 (2026-09-07) -- the exemption the A-11 argument stopped
# one field-family short of.
#
# ⛔⛔ WHY THIS SECTION IS SYNTHETIC, stated so nobody reads it as a
# convenience: after the ladder landed there is NO real specimen left.  13AF
# used to be the corpus' only ``non_orthogonal_lines`` row and it is now a
# proper face line, so ``non_orthogonal_lines`` is EMPTY on every view of both
# cases (measured).  An empty table cannot demonstrate that its rows keep their
# resolution -- so the stock has to be built.  ⭐ "The table is empty" is
# exactly the reason to build a fixture, ⛔ never a reason to skip.
# =========================================================================== #
class _StubGeo:
    """The two attributes ``_face_line_records`` reads, and nothing else."""

    def __init__(self, wall_lines):
        self.wall_lines = wall_lines
        self.wall_line_layers = {row[0]: "WALL" for row in wall_lines}


def test_gc_a11d3_a_non_orthogonal_row_keeps_its_sub_millimetre_evidence():
    """⭐ The row's ONLY claim is "this stroke is neither horizontal nor
    vertical".  If both endpoints are snapped onto the 1 mm ingest grid that
    claim can become unreadable on its own record -- which is what happened to
    13AF: stored ``p0=[52400, 100660]`` / ``p1=[52400, 99460]``, two identical
    x, from a drawing that has 52400.742 and 52398.827.

    Here the same shape is built deliberately: a stroke leaning by 0.1 mm.
    ⛔ Under the pre-fix ``_geom_units`` both x collapse to one value and the
    row contradicts itself; the exemption keeps them apart.
    """
    #   sx/sy = 0.001 (native millimetres -> world metres), tx/ty = 0 -- the
    #   corpus' own frame, so a native mm becomes 10 storage units of 0.1 mm.
    skew = [("AAAA", 5240.0, 10060.0, 5240.1, 9946.0)]
    faces, non_orthogonal, _degenerate = am._face_line_records(
        _StubGeo(skew), 0.001, 0.0, 0.001, 0.0)
    assert faces == []
    assert len(non_orthogonal) == 1
    row = non_orthogonal[0]
    # ⭐ the two x are DIFFERENT -- the lean survived storage
    assert row.p0[0] != row.p1[0]
    assert row.p1[0] - row.p0[0] == 1        # 0.1 mm, one storage unit
    # ⛔ and they are NOT on the 1 mm ingest grid, which is the whole point:
    assert row.p0[0] % am.INGEST_RESOLUTION_UNITS or row.p1[0] % am.INGEST_RESOLUTION_UNITS
    # the counterfactual, computed the way the code did before the fix:
    assert (am._geom_units(0.001 * 5240.0) == am._geom_units(0.001 * 5240.1)), (
        "premise: the pre-fix quantisation really did collapse these two")


def test_gc_a11d3_the_exit_scan_exempts_that_row_and_would_flag_it_otherwise(
        as_received_doc, monkeypatch):
    """⭐⭐ The other half, and the one that proves the exemption is what is
    doing the work: inject an off-grid ``non_orthogonal_lines`` row into a real
    serialised document and scan it twice -- once with the exemption table as
    shipped (must be silent) and once with the two new entries REMOVED (must
    name both paths).  ⛔ Without the second half this test could not tell "the
    scan exempts it" from "the scan never looked".
    """
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    assert view["converter_readouts"]["non_orthogonal_lines"] == [], (
        "premise: the ladder left this table empty on the real corpus")
    view["converter_readouts"]["non_orthogonal_lines"] = [
        {"id": "AAAA", "layer": "WALL", "p0": [52401, 100659], "p1": [52399, 99459]}]

    assert am.scan_ingest_resolution_violations(raw) == []

    without = dict(am.INGEST_NON_COORDINATE_PATHS)
    for path in ("views[*].converter_readouts.non_orthogonal_lines[*].p0",
                 "views[*].converter_readouts.non_orthogonal_lines[*].p1"):
        assert without.pop(path, None) is not None, (
            f"premise: {path} really is in the shipped exemption table")
    monkeypatch.setattr(am, "INGEST_NON_COORDINATE_PATHS", without)
    flagged = am.scan_ingest_resolution_violations(raw)
    prefix = "views.*.converter_readouts.non_orthogonal_lines.*."
    assert sorted(flagged) == sorted([
        prefix + "p0.* = 52401", prefix + "p0.* = 100659",
        prefix + "p1.* = 52399", prefix + "p1.* = 99459",
    ]), flagged


# =========================================================================== #
# ⭐⭐ G-c -- the TIER-2 arbitration ledger.  Empty on both real cases (every
# real skew stroke lands on tier 1, which is the outcome the user asked for),
# so its teeth are demonstrated on built stock, ⛔ not asserted from emptiness.
# =========================================================================== #
def _with_a_tier2_row(raw):
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    readouts = view["converter_readouts"]
    readouts["diagnostics"].append({
        "code": "tarch_wall_nonorthogonal", "severity": "BLOCK",
        "stage": "S1_QUANTIZE", "action_code": "tarch_wall_nonorthogonal",
        "handles": ["BBBB"], "points_dxf_mm": [[0.0, 0.0], [1000.0, 20.0]],
        "context": {"ladder_tier": 2, "refused_by": ["deviation_over_cap"],
                    "angle_deg": 1.1458, "minor_leg_mm": 20.0,
                    "major_leg_mm": 1000.0, "length_mm": 1000.2,
                    "deviation_limit_mm": 6.0, "cap_mm": 6.0}})
    readouts["axis_snap_arbitrations"] = [
        {"id": "BBBB", "layer": "WALL", "ladder_tier": 2,
         "reason": "deviation_over_cap", "p0": [0, 0], "p1": [10000, 200],
         "deviation_units": 200, "deviation_limit_units": 60, "cap_units": 60,
         "angle_deg": 1.1458}]
    return raw


def test_gc_the_arbitration_row_validates_and_carries_what_a_signer_needs(
        as_received_doc):
    doc = AsMeasuredV1.model_validate(_with_a_tier2_row(
        as_received_doc.model_dump(mode="json")))
    view = next(v for v in doc.views if v.view_id == "plan-F1")
    row = view.converter_readouts.axis_snap_arbitrations[0]
    assert (row.id, row.ladder_tier, row.reason) == (
        "BBBB", 2, "deviation_over_cap")
    # ⭐ the two numbers that say WHY it could not be done automatically, and
    # ⛔ they are lengths, so they are exempt from the ingest grid:
    assert row.deviation_units > row.cap_units
    assert am.scan_ingest_resolution_violations(doc.model_dump(mode="json")) == []


def test_gc_deleting_an_arbitration_row_turns_the_ledger_red(as_received_doc):
    """⭐⭐ The same self-proof the snap list already has, for the new list:
    quietly emptying it must be impossible.  ⛔ Otherwise "改判据顺手把红掉的
    锁拆了" applies to the arbitration ledger itself."""
    raw = _with_a_tier2_row(as_received_doc.model_dump(mode="json"))
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["converter_readouts"]["axis_snap_arbitrations"] = []
    with pytest.raises(ValueError,
                       match="as_measured_axis_snap_arbitration_ledger_broken"):
        AsMeasuredV1.model_validate(raw)


def test_gc_an_arbitration_row_cannot_disagree_with_its_diagnostic(as_received_doc):
    """Angle and reason both bound, ⛔ not just the handle set -- a row that
    keeps the id but rewrites what happened is the same forgery one field in."""
    raw = _with_a_tier2_row(as_received_doc.model_dump(mode="json"))
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["converter_readouts"]["axis_snap_arbitrations"][0]["angle_deg"] = 2.0
    with pytest.raises(
            ValueError,
            match="as_measured_axis_snap_arbitration_angle_disagrees_with_diagnostic"):
        AsMeasuredV1.model_validate(raw)

    raw = _with_a_tier2_row(as_received_doc.model_dump(mode="json"))
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["converter_readouts"]["axis_snap_arbitrations"][0]["reason"] = (
        "both_ends_anchored_suspected_true_slant")
    with pytest.raises(
            ValueError,
            match="as_measured_axis_snap_arbitration_reason_disagrees_with_diagnostic"):
        AsMeasuredV1.model_validate(raw)


def test_gc_tier3_does_not_enter_the_arbitration_ledger(as_received_doc):
    """⛔ A genuine diagonal is not a suspected drafting error, so it must NOT
    cost a person anything.  A tier-3 diagnostic with no row is valid; ⭐ and a
    row claiming that tier-3 handle is refused."""
    raw = as_received_doc.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    view["converter_readouts"]["diagnostics"].append({
        "code": "tarch_wall_nonorthogonal", "severity": "BLOCK",
        "stage": "S1_QUANTIZE", "action_code": "tarch_wall_nonorthogonal",
        "handles": ["CCCC"], "points_dxf_mm": [[0.0, 0.0], [100.0, 100.0]],
        "context": {"ladder_tier": 3, "refused_by": ["angle_beyond_envelope"],
                    "angle_deg": 45.0, "minor_leg_mm": 100.0,
                    "major_leg_mm": 100.0, "length_mm": 141.4,
                    "deviation_limit_mm": 30.0, "cap_mm": 30.0}})
    AsMeasuredV1.model_validate(raw)          # must not raise

    view["converter_readouts"]["axis_snap_arbitrations"] = [
        {"id": "CCCC", "layer": "WALL", "ladder_tier": 2,
         "reason": "angle_beyond_envelope", "p0": [0, 0], "p1": [1000, 1000],
         "deviation_units": 1000, "deviation_limit_units": 300,
         "cap_units": 300, "angle_deg": 45.0}]
    with pytest.raises(ValueError,
                       match="as_measured_axis_snap_arbitration_ledger_broken"):
        AsMeasuredV1.model_validate(raw)
