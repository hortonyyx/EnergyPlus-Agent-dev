"""F-A producer-half locks: the consistency readouts the converter ALREADY computed.

The F-126 cross-review (2026-08-29, finding F-A) named the half this file locks:
``run_p1_plan_view`` assembles G1-G5 gate verdicts, S4 closure counts
(``dangles``/``cuts``/``invalid``) and localised diagnostics -- and
``denominator()`` handed the downstream only a ``diagnostics`` list with the
localisation fields stripped, dropping everything else on the floor.  "Is this
wall closed / is there an orphan segment / did the upstream's own G1 refuse
this input" was computed upstream and invisible in the artifact.

MEASURED before writing any lock (both fixtures shipped in
``gt_sources/sm25-L_anchor/``; the re-signed request is built in ``tmp_path``,
⛔ no DXF is written anywhere, ``gt_sources/``/``gt/`` stay untouched):

    fixture                        view      gates            s4 d/c/i   BLOCK
    sm25-L_t3.dxf (signed)         plan-F1   G1..G3,G5 pass   0/0/0      0
    sm25-L_t3.dxf (signed)         plan-F2   G1..G3,G5 pass   0/0/0      0
    ..._as_received (re-signed)    plan-F1   G1 F, G5 F       4/0/0      3
    ..._as_received (re-signed)    plan-F2   G1..G3,G5 pass   0/0/0      0

⭐ TWO fixture-direction notes that decide whether these locks have teeth
([[gate-teeth-direction-follows-fixture-inventory]]):

  * "all gates pass" on the SIGNED drawing is a property of the FIXTURE, not a
    lock -- against code that never exposes ``gates`` at all it can never run
    (L5 would KeyError, fine), but as an *assertion* it is a tautology.  The
    re-signed as-received ``plan-F1`` is the inventory: G1 False + G5 False.
    L6 exists to prove the same assertion shape goes RED there.
  * The as-received drawing's lesions are confined to ``plan-F1``: the SAME
    file at ``plan-F2`` measures all-pass / 0/0/0.  Pinned deliberately -- it
    proves the readout reports per-view geometry, not a file-level flag.

Label numbering L5.. continues ``test_as_drawn_denominator_f126.py`` (L1..L4b).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent.judge.as_drawn.denominator import (
    DenominatorUnavailable,
    _diagnostic_records,
    denominator,
)
from src.agent.judge.tarch_converter_schema import (
    TarchConversionRequestV1,
    compute_request_sha256,
)

ANCHOR = Path(__file__).resolve().parents[1] / (
    "case_tests/test_baseline/gt_sources/sm25-L_anchor")
SIGNED_DXF = ANCHOR / "sm25-L_t3.dxf"
AS_RECEIVED_DXF = ANCHOR / "sm25-L_t3_as_received.dxf"
REQUEST = ANCHOR / "request.json"

# MEASURED 2026-08-29, before any of this landed (see the table in the module
# docstring).  ⚠️ G4 is ABSENT on purpose: P1 does not emit it (the outer-skin
# conservation gate lands in P2 -- emitting a stub G4=pass at P1 would be a
# false-lock, per the comment in ``_assemble_gates``), so pinning this exact
# list also pins that no such stub appeared.
ALL_PASS = [("G1", True), ("G2", True), ("G3", True), ("G5", True)]

# The one degenerate line the signed drawing carries (MEASURED): handle 13DC at
# (-19349.0, 33973.6) DXF mm.  Its ``context`` is {} -- the converter keeps the
# localisation in source_entity_handles / source_points_dxf_mm, which the old
# passthrough dropped.
DEGENERATE_HANDLE = "13DC"


@pytest.fixture(scope="module")
def anchor_present() -> None:
    """⛔ Assert the fixtures EXIST before any check reads them
    ([[absent-file-read-as-passing-check]])."""
    for path in (SIGNED_DXF, AS_RECEIVED_DXF, REQUEST):
        assert path.is_file(), f"missing F-A fixture: {path}"


def _resigned_request(tmp_path: Path) -> Path:
    """Same construction as the F-126 file's: re-sign, in ``tmp_path``, the
    shipped request against the as-received drawing's own hash, so the
    converter actually runs geometry on it.  Nothing is edited in the drawing
    and nothing is written into the protected answer roots."""
    raw = json.loads(REQUEST.read_text())
    raw["source_dxf_sha256"] = hashlib.sha256(AS_RECEIVED_DXF.read_bytes()).hexdigest()
    raw["request_sha256"] = "0" * 64
    raw["request_sha256"] = compute_request_sha256(
        TarchConversionRequestV1.model_validate(raw))
    out = tmp_path / "resigned_request.json"
    out.write_text(json.dumps(raw, ensure_ascii=False))
    return out


# --------------------------------------------------------------------------- #
# L5 -- gates ride out on the success path (positive fixture, both views)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("view_id", ["plan-F1", "plan-F2"])
def test_l5_gates_ride_out_on_the_signed_drawing(anchor_present, view_id):
    """The converter's own verdicts are IN THE ARTIFACT, with the exact shape
    id/name/passed -- json-safe, no leaked Enum, no evidence dict.

    ⚠️ Read together with L6: on this fixture "all pass" is a tautology; the
    lock's teeth are proven there, not here.
    """
    result = denominator(SIGNED_DXF, REQUEST, view_id)

    assert [(g["id"], g["passed"]) for g in result["gates"]] == ALL_PASS
    for g in result["gates"]:
        assert set(g) == {"id", "name", "passed"}
        assert isinstance(g["id"], str) and g["id"].startswith("G")
        assert isinstance(g["name"], str) and g["name"]
        assert g["passed"] is True
    # ⭐ main() serialises the whole dict; a leaked Enum or tuple would only
    # surface there.
    json.dumps(result, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# L6 -- the same assertion shape goes RED: gates discriminate (anti-tautology)
# --------------------------------------------------------------------------- #
def test_l6_gates_discriminate_on_the_blocked_geometry(anchor_present, tmp_path):
    """⛔ THE anti-tautology fixture.  A ``gates`` lock that only ever ran on
    the signed drawing could not tell "readout exposed" from "readout pinned
    to True"; this is the inventory that separates them (MEASURED: G1 False
    -- ``tarch_wall_nonorthogonal`` is a G1 code -- and G5 False with 4
    dangles), plus the per-view control: the SAME drawing file at ``plan-F2``
    measures all-pass, so the verdict must follow the view's geometry.
    """
    request_path = _resigned_request(tmp_path)

    blocked = denominator(AS_RECEIVED_DXF, request_path, "plan-F1")
    verdict = {g["id"]: g["passed"] for g in blocked["gates"]}
    assert verdict == {"G1": False, "G2": True, "G3": True, "G5": False}

    control = denominator(AS_RECEIVED_DXF, request_path, "plan-F2")
    assert [(g["id"], g["passed"]) for g in control["gates"]] == ALL_PASS


def test_l6b_gates_ride_out_on_the_exception_too(anchor_present):
    """The hash-mismatch empty geometry still carries ASSEMBLED gates (G1
    False, G2 False -- MEASURED); F-126's exception contract says everything
    the empty run knew rides out, and gates were known.  Dropping them here
    would be the same silence F-126 closed on the success path."""
    with pytest.raises(DenominatorUnavailable) as excinfo:
        denominator(AS_RECEIVED_DXF, REQUEST, "plan-F1")

    exc = excinfo.value
    assert [(g["id"], g["passed"]) for g in exc.gates] == [
        ("G1", False), ("G2", False), ("G3", True), ("G5", True)]
    # json-safe there too
    json.dumps(exc.gates)


# --------------------------------------------------------------------------- #
# L7 -- every exposed diagnostic is POINTABLE, or says it is not
# --------------------------------------------------------------------------- #
def test_l7_diagnostics_carry_localisation_not_just_context(anchor_present):
    """The named lesion: ``tarch_wall_degenerate_line`` says "there is a
    degenerate line" with ``context == {}`` -- the converter localises it via
    handle + DXF point, and the old passthrough dropped exactly those two
    fields, so every diagnostic arrived saying WHAT, never WHERE."""
    result = denominator(SIGNED_DXF, REQUEST, "plan-F1")

    degenerate = [d for d in result["diagnostics"]
                  if d["code"] == "tarch_wall_degenerate_line"]
    assert len(degenerate) == 1, "fixture no longer carries the degenerate line"
    assert degenerate[0]["handles"] == [DEGENERATE_HANDLE]
    assert degenerate[0]["points_dxf_mm"], "the handle's DXF point vanished"
    assert degenerate[0]["locatable"] is True


def test_l7b_block_diagnostics_are_localisable_and_fields_always_present(
        anchor_present, tmp_path):
    """Every record carries the three fields (a silent KeyError is not
    "visible un-localisability"), and every BLOCK record is localisable --
    the pair (handles, points) mirrors the schema's own BLOCK-localisability
    validator.  The re-signed as-received plan-F1 holds the BLOCK inventory
    (3 records, MEASURED); the signed drawing holds none, so this lock must
    run on the fixture that carries the inventory."""
    result = denominator(AS_RECEIVED_DXF, _resigned_request(tmp_path), "plan-F1")

    blocked = [d for d in result["diagnostics"] if d["severity"] == "BLOCK"]
    assert len(blocked) == 3, "fixture no longer carries 3 BLOCK records"
    for d in result["diagnostics"]:
        assert set(d) >= {"handles", "points_dxf_mm", "locatable"}
    for d in blocked:
        assert d["locatable"] is True
        assert d["handles"] or d["points_dxf_mm"]
    # ...and the dangle BLOCK localises in the point (MEASURED: no handle)
    free_end = next(d for d in blocked if d["code"] == "tarch_wall_free_end")
    assert free_end["points_dxf_mm"]


def test_l7c_unlocalisable_is_stated_not_silent():
    """The branch with NO shipped inventory: a diagnostic carrying neither a
    handle nor a point must say ``locatable: False`` -- the requirement is
    that "cannot be located" is VISIBLE, so the absence itself is what this
    seam test exercises (synthetic input, clearly not a fixture claim; same
    discipline as the F-126 file's L2b).  ⛔ Nothing fabricates a location."""
    fake = SimpleNamespace(
        code="tarch_wall_degenerate_line", severity="INFO", stage="S1_COLLECT",
        action_code="drop", context={},
        source_entity_handles=[], source_points_dxf_mm=[])
    records = _diagnostic_records(SimpleNamespace(diagnostics=[fake]))
    assert records == [{
        "code": "tarch_wall_degenerate_line", "severity": "INFO",
        "stage": "S1_COLLECT", "action_code": "drop", "context": {},
        "handles": [], "points_dxf_mm": [], "locatable": False}]


# --------------------------------------------------------------------------- #
# L8 -- S4's closure counts ride out, and agree with the gate they feed
# --------------------------------------------------------------------------- #
def test_l8_s4_closure_counts_ride_out(anchor_present, tmp_path):
    """``s4_dangles``/``s4_cuts``/``s4_invalid`` in the ledger, pinned to the
    measured values on both fixtures -- zeros on the signed drawing (both
    views), 4 dangles on the re-signed as-received plan-F1 that carries the
    inventory, and zeros again on the same file's clean plan-F2."""
    for view_id in ("plan-F1", "plan-F2"):
        signed = denominator(SIGNED_DXF, REQUEST, view_id)
        assert (signed["ledger"]["s4_dangles"], signed["ledger"]["s4_cuts"],
                signed["ledger"]["s4_invalid"]) == (0, 0, 0)
        # consistency: a passing G5 must be backed by zero residuals
        assert next(g for g in signed["gates"] if g["id"] == "G5")["passed"] is True

    blocked = denominator(AS_RECEIVED_DXF, _resigned_request(tmp_path), "plan-F1")
    assert (blocked["ledger"]["s4_dangles"], blocked["ledger"]["s4_cuts"],
            blocked["ledger"]["s4_invalid"]) == (4, 0, 0)
    # ⭐ the two new readouts agree WITH EACH OTHER: G5 is literally computed
    # from these counts, so a nonzero residual with a passing G5 (or the
    # reverse, absent an area mismatch) means one of the two passthroughs
    # stopped mirroring the converter.
    assert next(g for g in blocked["gates"] if g["id"] == "G5")["passed"] is False

    # the exception path's ledger carries the counts too (empty geometry = zeros)
    with pytest.raises(DenominatorUnavailable) as excinfo:
        denominator(AS_RECEIVED_DXF, REQUEST, "plan-F1")
    assert excinfo.value.ledger["s4_dangles"] == 0
