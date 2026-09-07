"""F-126 locks: the as-drawn scoreable denominator must never be silently empty.

⭐⭐ These are the FIRST tests this module has ever had.  MEASURED before writing
them (2026-08-29): ``grep -rln "as_drawn.denominator" tests/`` returned nothing,
so "the whole suite is green" carried exactly zero protection for
``src.agent.judge.as_drawn.denominator`` -- the file that decides what a
reading is scored against.

The defect being locked: fed a DXF that the upstream converter refuses (source
hash gate ``tarch_input_source_hash_mismatch``, severity BLOCK),
``denominator()`` used to RETURN NORMALLY with ``targets: []``, dropping the
BLOCK diagnostic entirely -- its return dict had nowhere to put it.  A zero
denominator then looks, in the artifact, exactly like "the product is perfect".

G-c closed the real as-received joints and admitted 13AF as a face.  L4's
old non-orthogonal/free-end inventory is gone.  L4 now copies the drawing into
``tmp_path`` and adds an isolated sub-q stroke straddling a quantization cell
boundary.  Tier 0 admits it without rotation; its quantized endpoints remain
non-orthogonal, so the denominator must itemise it.  Its free ends also supply
the success-path BLOCK diagnostic.  A >5-degree stroke would be dropped in S1
and could not exercise this downstream list.  The original answer roots are
only read; the new DXF and hash-declaring request live in ``tmp_path``.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

import pytest

from src.agent.judge.as_drawn.denominator import (
    REASON_UPSTREAM_BLOCK,
    REASON_ZERO_TARGETS,
    DenominatorUnavailable,
    denominator,
)
from src.agent.judge.tarch_converter_schema import (
    TarchConversionRequestV1,
    compute_request_sha256,
    resolve_converter_tooling,
)

ANCHOR = Path(__file__).resolve().parents[1] / (
    "case_tests/test_baseline/gt_sources/sm25-L_anchor")
SIGNED_DXF = ANCHOR / "sm25-L_t3.dxf"
AS_RECEIVED_DXF = ANCHOR / "sm25-L_t3_as_received.dxf"
REQUEST = ANCHOR / "request.json"

HASH_GATE_CODE = "tarch_input_source_hash_mismatch"

# MEASURED 2026-08-29 on the signed drawing, before any of this change landed.
# ⭐ Two views, not one: [[rework-review-needs-the-same-shape-input]] -- a fix
# proven on ``plan-F1`` alone only proves ``plan-F1`` was fixed.
# ⭐ F-D (F-126 cross-review, 2026-08-29): counts alone cannot tell "the
# numbers are the same" from "the counts still agree but the COORDINATES
# rotted" -- every target a centimetre longer leaves every count untouched.
# The ledger already carries two geometric quantities; pin them too.
SIGNED_EXPECTED = {
    "plan-F1": {"targets": 110, "openings": 31, "segments": 225,
                "total_scoreable_length_m": 282.28, "face_lines_after_grouping": 44},
    "plan-F2": {"targets": 106, "openings": 30, "segments": 222,
                "total_scoreable_length_m": 289.04, "face_lines_after_grouping": 44},
}


@pytest.fixture(scope="module")
def anchor_present() -> None:
    """⛔ Assert the fixtures EXIST before any check reads them.

    [[absent-file-read-as-passing-check]]: a missing input must fail as a
    missing input, never drain out through a check that then reports "passed".
    """
    for path in (SIGNED_DXF, AS_RECEIVED_DXF, REQUEST):
        assert path.is_file(), f"missing F-126 fixture: {path}"


def _resigned_request(tmp_path: Path, dxf: Path) -> Path:
    """A request in ``tmp_path`` that legitimately declares ``dxf``'s own hash.

    The request names the supplied DXF's actual bytes, including when L4 has
    constructed a temporary copy with an extra stroke.  Both edited files
    stay in the temporary directory; the shipped answer roots are only read.
    """
    raw = json.loads(REQUEST.read_text())
    raw["source_dxf_sha256"] = hashlib.sha256(dxf.read_bytes()).hexdigest()
    raw["request_sha256"] = "0" * 64
    raw["request_sha256"] = compute_request_sha256(
        TarchConversionRequestV1.model_validate(raw))
    out = tmp_path / "resigned_request.json"
    out.write_text(json.dumps(raw, ensure_ascii=False))
    return out


# --------------------------------------------------------------------------- #
# L1 -- the good input still produces exactly the denominator it used to
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("view_id", sorted(SIGNED_EXPECTED))
def test_l1_signed_drawing_still_yields_the_same_denominator(anchor_present, view_id):
    """⛔ The loud-failure path must not have moved the honest numbers."""
    want = SIGNED_EXPECTED[view_id]
    result = denominator(SIGNED_DXF, REQUEST, view_id)

    assert len(result["targets"]) == want["targets"]
    assert len(result["opening_targets"]) == want["openings"]
    assert result["ledger"]["wall_layer_segments_collected"] == want["segments"]
    assert result["view_id"] == view_id
    # ⭐ F-D: the counts agree AND the geometry they summarise still weighs
    # what it weighed -- "same counts, rotted coordinates" is the shape these
    # two lines exist to catch (the by-hand cmp -s that used to catch it went
    # away with the allowlist entry in 48f1d10).
    assert result["ledger"]["total_scoreable_length_m"] == want["total_scoreable_length_m"]
    assert result["ledger"]["face_lines_after_grouping"] == want["face_lines_after_grouping"]


# --------------------------------------------------------------------------- #
# L2 -- the blocked input fails LOUDLY, and names the code that blocked it
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("view_id", sorted(SIGNED_EXPECTED))
def test_l2_blocked_input_raises_and_names_the_blocking_code(anchor_present, view_id):
    """⛔ Not "returns something empty" -- there must be NO dict to keep using.

    Same shape, both views: this is a property of ``denominator()``, not a patch
    applied to one example.
    """
    with pytest.raises(DenominatorUnavailable) as excinfo:
        denominator(AS_RECEIVED_DXF, REQUEST, view_id)

    exc = excinfo.value
    assert exc.reason == REASON_UPSTREAM_BLOCK
    assert HASH_GATE_CODE in exc.blocking_codes
    # ⭐ named in the MESSAGE too: whoever sees only the traceback still learns
    # which gate refused, without having to catch and introspect.
    assert HASH_GATE_CODE in str(exc)
    assert exc.view_id == view_id


def test_l2b_the_two_ways_of_being_empty_do_not_share_one_exit(monkeypatch, tmp_path):
    """⛔ [[absence-conflates-causes-in-observables]] -- an empty denominator whose
    geometry ran CLEAN must not be reported as an upstream block.

    The upstream refuses geometry only via a BLOCK diagnostic, so no real DXF in
    the repo reaches "clean run, zero targets" (checked: moving the clip box off
    the drawing raises ``tarch_view_frame_missing``, i.e. still a BLOCK).  The
    branch is reachable in principle -- a view whose every stroke is a jamb cap
    leaves D3 with no groups -- so it is exercised at the seam, by handing
    ``denominator()`` a real empty ``P1PlanViewGeometry`` carrying no
    diagnostics.  ⭐ The classification under test is the real one; only the
    upstream geometry is substituted.
    """
    from shapely.geometry import Polygon

    from src.agent.judge import tarch_normalize
    from src.agent.judge.as_drawn import denominator as den_mod

    def _clean_but_empty(dxf_path, request, plan_view, tooling):
        return tarch_normalize.P1PlanViewGeometry(
            plan_view.id, plan_view.floor_id, 1.0,
            [], 0, {}, {}, {}, {}, [], [], [], [], 0, 0, 0, 0.0, 0.0, Polygon(),
            diagnostics=[])

    monkeypatch.setattr(den_mod, "run_p1_plan_view", _clean_but_empty)

    with pytest.raises(DenominatorUnavailable) as excinfo:
        denominator(SIGNED_DXF, REQUEST, "plan-F1")

    exc = excinfo.value
    assert exc.reason == REASON_ZERO_TARGETS
    assert exc.reason != REASON_UPSTREAM_BLOCK
    assert exc.blocking_codes == []
    # ⛔ and it must not borrow the other branch's wording
    assert HASH_GATE_CODE not in str(exc)
    assert "zero" in str(exc)


# --------------------------------------------------------------------------- #
# L3 -- the diagnostics are IN THE RESULT, not only on stdout
# --------------------------------------------------------------------------- #
def test_l3_diagnostics_ride_out_on_both_paths(anchor_present, capsys):
    """⭐ [[self-report-more-compliant-than-artifact]]: a printed diagnostic is not
    an exposed diagnostic.  What the downstream reads is the returned object.
    """
    # (a) failure path: retrievable from the exception, with severity attached
    with pytest.raises(DenominatorUnavailable) as excinfo:
        denominator(AS_RECEIVED_DXF, REQUEST, "plan-F1")
    diags = excinfo.value.diagnostics
    assert diags, "the BLOCK diagnostic was dropped again"
    blocked = [d for d in diags if d["severity"] == "BLOCK"]
    assert [d["code"] for d in blocked] == [HASH_GATE_CODE]
    assert blocked[0]["stage"]

    # ⛔ and NOT merely printed: nothing was written to stdout by the call above
    assert HASH_GATE_CODE not in capsys.readouterr().out

    # (b) success path: the key exists there too, so a consumer can always look
    result = denominator(SIGNED_DXF, REQUEST, "plan-F1")
    assert "diagnostics" in result
    assert result["diagnostics"], "signed run has 14 INFO diagnostics, measured"
    assert {d["severity"] for d in result["diagnostics"]} == {"INFO"}

    # ⭐ ``main()`` serialises this dict; a leaked Enum would only surface there.
    json.dumps(result, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# L4 -- discarded non-orthogonal strokes are itemised, not just counted
# --------------------------------------------------------------------------- #
def test_l4_discarded_non_orthogonal_segments_are_itemised(anchor_present, tmp_path):
    """Rebuild the downstream discard and BLOCK-on-success samples.

    A 0.6*q deviation is tier 0, but its endpoints at 0.2*q and 0.8*q
    round to adjacent q cells.  This constructs the input shape D1 owns,
    without changing a gate or relying on the repaired 13AF stroke.
    The same assertions are exercised with missing items/diagnostics and
    corrupted frame data, so a broken passthrough demonstrably reddens.
    """
    clean = denominator(AS_RECEIVED_DXF, _resigned_request(tmp_path, AS_RECEIVED_DXF),
                        "plan-F1")
    assert clean["excluded_non_orthogonal_segments"] == []
    assert not [d for d in clean["diagnostics"] if d["severity"] == "BLOCK"]
    dxf, request_path, handle = _l4_nonorthogonal_fixture(tmp_path)
    result = denominator(dxf, request_path, "plan-F1")
    _assert_l4_itemisation(result, request_path, handle)
    for defect in ("items", "block", "frame", "handle"):
        damaged = deepcopy(result)
        if defect == "items":
            damaged["excluded_non_orthogonal_segments"] = []
        elif defect == "block":
            damaged["diagnostics"] = [d for d in damaged["diagnostics"]
                                      if d["severity"] != "BLOCK"]
        elif defect == "frame":
            damaged["excluded_non_orthogonal_segments"][0]["length_m"] += 1
        else:
            damaged["excluded_non_orthogonal_segments"][0]["handle"] = "WRONG"
        with pytest.raises(AssertionError):
            _assert_l4_itemisation(damaged, request_path, handle)


def _l4_nonorthogonal_fixture(tmp_path):
    import ezdxf
    from src.agent.judge.tarch_normalize import _tols_from

    request = TarchConversionRequestV1.model_validate_json(REQUEST.read_text())
    repo = Path(__file__).resolve().parents[1]
    tooling = resolve_converter_tooling(repo / "src" / "configs" / "judge_gt.yaml",
                                        repo / "src" / "configs" / "correction.yaml")
    q = _tols_from(tooling, request.metres_per_unit).quant_native
    doc = ezdxf.readfile(AS_RECEIVED_DXF)
    line = doc.modelspace().add_line((-36000, 20000 + 0.2*q),
                                     (-35000, 20000 + 0.8*q),
                                     dxfattribs={"layer": "WALL"})
    path = tmp_path / "l4_subquant_noise.dxf"
    doc.saveas(path)
    return path, _resigned_request(tmp_path, path), line.dxf.handle


def _assert_l4_itemisation(result, request_path, handle):
    assert result["targets"], "BLOCK must ride alongside a nonempty denominator"
    assert {d["code"] for d in result["diagnostics"] if d["severity"] == "BLOCK"} == {
        "tarch_wall_free_end"}
    assert {item["handle"] for item in result["excluded_non_orthogonal_segments"]} == {handle}
    items = result["excluded_non_orthogonal_segments"]
    count = result["ledger"]["excluded_non_orthogonal"]

    assert count > 0, "fixture no longer carries a non-orthogonal stroke"
    assert len(items) == count

    metres_per_unit = TarchConversionRequestV1.model_validate_json(
        request_path.read_text()).metres_per_unit

    for item in items:
        # ⭐ "which stroke", answerable: a handle and real endpoints in BOTH
        # frames.  Field names state their frame on purpose
        # ([[cross-representation-mutation-must-be-equivalent]]).
        assert item["handle"]
        assert item["p0_dxf"] != item["p1_dxf"]
        assert item["p0_m"] != item["p1_m"]
        assert item["length_m"] > 0
        # it really is non-orthogonal: neither coordinate is shared
        assert item["p0_dxf"][0] != item["p1_dxf"][0]
        assert item["p0_dxf"][1] != item["p1_dxf"][1]
        # ⭐ F-C: the two frames must agree ON THE SAME STROKE.  Each frame
        # separately can look healthy while the metres side lies -- an affine
        # or rounding regression hits exactly this new path, and the signed
        # drawing holds ZERO inventory here, so L1 cannot see it.
        dxf_len = math.hypot(item["p1_dxf"][0] - item["p0_dxf"][0],
                             item["p1_dxf"][1] - item["p0_dxf"][1])
        assert abs(item["length_m"] - dxf_len * metres_per_unit) < 1e-3


def test_l4b_signed_drawing_has_no_non_orthogonal_inventory(anchor_present):
    """⭐ The premise L4 rests on, asserted rather than assumed
    ([[regression-case-must-prove-its-own-premise]]): if the signed drawing ever
    grows a downstream non-orthogonal stroke, this control says so; L4's
    negative inventory is constructed independently in a temporary copy.
    """
    result = denominator(SIGNED_DXF, REQUEST, "plan-F1")
    assert result["ledger"]["excluded_non_orthogonal"] == 0
    assert result["excluded_non_orthogonal_segments"] == []
