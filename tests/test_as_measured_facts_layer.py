"""Locks for the facts layer's first cut -- ``AsMeasuredV1`` (dispatch ②-1a).

Three things are locked, one per section below:

  R1  the as-received drawing can be converted WITHOUT touching a signed byte
  R2  what P1 measured lands in the document, and the three forbidden fields
      (``basis`` / expanded endpoints / ``boundary_condition``) do not
  R3  the document is reproducible BIT FOR BIT across fresh processes, ⛔ with
      no ``PYTHONHASHSEED`` propping it up

⚠️ FIXTURE DIRECTION ([[gate-teeth-direction-follows-fixture-inventory]]).  The
two DXFs that ship side by side in ``gt_sources/sm25-L_anchor/`` do NOT have the
same inventory, and the difference is exactly where this unit lives:

    fixture                        wall_lines  non-orth  BLOCK        S4 dangles
    sm25-L_t3.dxf      (signed)    225          0        none         0
    ..._as_received.dxf            223          1        2 codes      4

⇒ ⛔ A lock written only against the signed drawing is blind in every direction
this unit cares about: it has no skew stroke to itemise, no content-level BLOCK
to carry out, and no failing gate to record.  The as-received drawing is the one
with the stock, so it is the primary fixture here and the signed drawing is kept
as the CONTRAST (F-129's measured difference), ⛔ not as the subject.

⛔ Nothing here writes into ``gt_sources/`` or ``gt/``.  Everything derived is
built in ``tmp_path``.
"""
from __future__ import annotations

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
EXPECTED = {
    ("as_received", "plan-F1"): {"face_lines": 222, "walls": 44, "openings": 31,
                                 "wall_lines_total": 223, "non_orthogonal": 1,
                                 "dangles": 4, "gates_failed": ["G1", "G5"],
                                 "block_codes": ["tarch_wall_free_end",
                                                 "tarch_wall_nonorthogonal"],
                                 "walls_missing_a_face_line": 11},
    ("as_received", "plan-F2"): {"face_lines": 222, "walls": 39, "openings": 30,
                                 "wall_lines_total": 222, "non_orthogonal": 0,
                                 "dangles": 0, "gates_failed": [],
                                 "block_codes": [],
                                 "walls_missing_a_face_line": 7},
    ("signed", "plan-F1"): {"face_lines": 225, "walls": 45, "openings": 31,
                            "wall_lines_total": 225, "non_orthogonal": 0,
                            "dangles": 0, "gates_failed": [], "block_codes": [],
                            "walls_missing_a_face_line": 9},
    ("signed", "plan-F2"): {"face_lines": 222, "walls": 39, "openings": 30,
                            "wall_lines_total": 222, "non_orthogonal": 0,
                            "dangles": 0, "gates_failed": [], "block_codes": [],
                            "walls_missing_a_face_line": 7},
}


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
    assert len(readouts.walls_missing_a_face_line) == want["walls_missing_a_face_line"]


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
    # the three handles F-129 names: two never collected, one collected but skew
    skew_codes = {d["code"]: sorted(h for h in d["handles"])
                  for d in f1_a.converter_readouts.diagnostics
                  if d["code"] == "tarch_wall_nonorthogonal"}
    rejected = sorted(h for d in f1_a.converter_readouts.diagnostics
                      if d["code"] == "tarch_wall_nonorthogonal" for h in d["handles"])
    assert rejected == ["13AD", "13AE"], skew_codes
    assert [n.id for n in f1_a.converter_readouts.non_orthogonal_lines] == ["13AF"]
    assert not f1_s.converter_readouts.non_orthogonal_lines


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
                assert opening.carrier_wall_id is None or opening.carrier_wall_id in wall_ids


def test_r2_every_opening_names_its_carrier_wall(as_received_doc, signed_doc):
    """MEASURED: 31/31 and 30/30 on BOTH drawings -- the carrier reference the
    dispatch worried might be missing is fully derivable inside P1."""
    for doc in (as_received_doc, signed_doc):
        for view in doc.views:
            unresolved = [o.id for o in view.openings if o.carrier_wall_id is None]
            assert unresolved == [], f"{doc.source_dxf_label}/{view.view_id}"
            assert view.converter_readouts.unresolved_opening_carriers == []


def test_r2_a_band_whose_second_face_was_never_drawn_is_named_not_dropped(
        as_received_doc, signed_doc):
    """⚠️⚠️ The dispatch's §一.2 said P1 carries "两条面线的引用" for every wall.
    MEASURED, it does not, and this test pins the gap rather than papering it.

    ``wall_bands`` is NOT a list of walls: the converter calls a stroke a jamb
    cap on LENGTH alone (inside ``wall_thickness_range_m`` = [0.06, 0.50] m), so
    a 0.36 m stroke drawn on the WALL layer that is not a cap still produces a
    "band".  MEASURED on the SIGNED drawing, ``plan-F1``: band
    ``w_x_35853.6_36213.6`` has two face lines on its low face and NONE on its
    high face, whose nearest neighbours are +/- 60 (the two faces of a 120 mm
    wall whose centre it lands on).  This is the same false-positive the
    denominator's D2 clause already refuses to inherit.

    ⛔ So the layer neither filters those bands out (that would be a judgement
    this unit is not authorised to make) nor pretends they have two faces: they
    are recorded with empty reference lists and named in
    ``walls_missing_a_face_line`` ([[absence-conflates-causes-in-observables]]).
    """
    for doc in (as_received_doc, signed_doc):
        for view in doc.views:
            named = set(view.converter_readouts.walls_missing_a_face_line)
            actual = {w.id for w in view.walls
                      if not w.face_line_ids_lo or not w.face_line_ids_hi}
            assert named == actual, f"{doc.source_dxf_label}/{view.view_id}"
            # ⛔ and the gap is real inventory, not an empty promise
            assert named, "this assertion would be vacuous with no such band"


def test_r2_the_three_forbidden_fields_are_absent(as_received_doc):
    """⭐ Acceptance: ⛔ ``basis`` / expanded endpoints / ``boundary_condition``.

    Checked on the SERIALISED document, not on the class definitions: a field
    can arrive through a verbatim passthrough without ever being declared.
    """
    text = canonical_bytes(as_received_doc).decode("utf-8")
    for forbidden in ('"basis"', '"boundary_condition"', '"offset_m"',
                      '"outer_skin"', '"zone_edges"'):
        assert forbidden not in text, forbidden


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


def test_r2_readouts_are_the_converters_own_numbers(as_received_doc):
    """⛔ Carried, ⛔ not recomputed: compared against a fresh P1 run.

    ⭐ Including the BLOCK diagnostics on a SUCCESSFUL path -- F-B measured that
    filtering those out passed an entire suite, because nothing looked.
    """
    import shutil
    import tempfile

    from src.agent.judge.tarch_normalize import run_p1_plan_view

    request = TarchConversionRequestV1.model_validate_json(
        AS_MEASURED_REQUEST.read_text(encoding="utf-8"))
    tooling = load_gt_tooling_config(REPO / "src/configs/judge_gt.yaml",
                                     REPO / "src/configs/correction.yaml")
    view_intent = next(v for v in request.plan_views if v.id == "plan-F1")
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / AS_RECEIVED_DXF.name
        shutil.copy2(AS_RECEIVED_DXF, staged)
        geo = run_p1_plan_view(staged, request, view_intent, tooling)

    view = next(v for v in as_received_doc.views if v.view_id == "plan-F1")
    readouts = view.converter_readouts
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
        all_wall_handles=list(reversed(sorted(geo.all_wall_handles))),
        consumed_wall_handles=list(reversed(sorted(geo.consumed_wall_handles))))


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
    straight = canonical_bytes_of_view(build_view(geo, affine))
    flipped = canonical_bytes_of_view(build_view(_reversed_geo(geo), affine))
    assert straight == flipped


#: ⭐ Four INDEPENDENT ordering seams, neutered one at a time.
#: [[neuter-proves-wiring-not-discriminating-power]] and the ②-1a dispatch §六.2:
#: "the teeth of a lock are spread across different mutation directions" -- a
#: single neuter would prove only that ONE of the four sorts is load-bearing,
#: and the other three could be dead code holding nothing up.
_ORDERING_SEAMS = ("_face_line_sort_key", "_wall_sort_key", "_opening_sort_key",
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
    straight = canonical_bytes_of_view(build_view(geo, affine))
    flipped = canonical_bytes_of_view(build_view(_reversed_geo(geo), affine))
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
            assert readouts.consumed_wall_handles == sorted(readouts.consumed_wall_handles)
            assert readouts.walls_missing_a_face_line == sorted(
                readouts.walls_missing_a_face_line)
            for wall in walls:
                assert wall.cap_handles == sorted(wall.cap_handles)
                assert wall.face_line_ids_lo == sorted(wall.face_line_ids_lo)
                assert wall.face_line_ids_hi == sorted(wall.face_line_ids_hi)
            for opening in openings:
                assert opening.jamb_handles == sorted(opening.jamb_handles)


def test_r3_in_process_rebuild_is_byte_identical():
    """The cheap half of the gate: same process, same bytes."""
    first = build_as_measured(AS_RECEIVED_DXF, AS_MEASURED_REQUEST, view_ids=["plan-F1"])
    second = build_as_measured(AS_RECEIVED_DXF, AS_MEASURED_REQUEST, view_ids=["plan-F1"])
    assert canonical_bytes(first) == canonical_bytes(second)
    assert content_sha256(first) == content_sha256(second)


def test_r3_a_deep_copy_of_the_document_hashes_the_same(as_received_doc):
    assert content_sha256(copy.deepcopy(as_received_doc)) == content_sha256(as_received_doc)
