"""②-2 module 3: the two evidence adapters (2026-08-31).

Dispatch: ``AI_agent/logs/reviews/request/
2026-08-31_o22m3_evidence_adapters_dispatch.md`` (seven acceptance items).

What is locked here, per acceptance item
----------------------------------------
1  the three REAL as-drawn products each adapt, and the per-product
   disposition counts CLOSE (faces = claimed + non_wall + ambiguous, expected
   values recomputed from the product, ⛔ not from the adapter's own output);
2  the two REAL legacy views adapt and EVERY wall trace lands
   ``source_basis="unknown"`` -- with the premise proven first: the two files
   carry contradictory basis claims ONLY in free-text notes (``外皮线`` vs
   ``centreline``), so any note-reading adapter would emit two different bases
   here and fail this test;
3  module 2's pin is retired: an UNSELECTED dangling ``pair_candidates`` entry
   that passes module 2's layer today is refused by this adapter
   (``PAIR_CANDIDATE_REFERENCES_UNKNOWN_FACE``);
4  paired-face fidelity at THIS layer, both directions: unequal-length faces
   stay ONE claim with full segmentation evidence (and are never re-bucketed),
   equal-length faces produce no fragment of any kind; the tail segmentation
   itself belongs to module 4's compiler -- the old pin was flipped onto the
   real implementation by module 4's dispatch (see
   ``test_tail_segmentation_is_delivered_by_module_4``);
5  a cleared ``pairs`` selection is never rebuilt from the candidate graph:
   the real-product shape (pairs=None, buckets untouched) refuses loudly with
   ``PAIRS_SELECTION_ABSENT``; the honest covered shape travels with a
   ``pairs_selection_absent`` debt and ZERO pair claims;
6  this module wires nothing (import probe; the as-drawn disposition is still
   ``KNOWN_NOT_CONSUMED``; the git-diff half of the reading is in the
   execution report);
7  determinism: same bytes twice → identical bundle hash and bytes.

Every red test proves its own premise first (the uncorrupted input adapts and
validates green), and the corruption premises that mirror module 1/2 blind
spots re-measure "today still says yes" instead of trusting the older report.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.correction.evidence_adapters import (
    LEGACY_BASIS_VALUES,
    adapt_as_drawn_plan,
    adapt_legacy_reading_view,
)
from src.agent.correction.evidence_contract import (
    SOURCE_CONTRACT_AS_DRAWN,
    EvidenceContractError,
    resolve_json_pointer,
    validate_evidence_bundle,
)
from src.agent.correction.window_sources import canonical_json_bytes
from src.agent.reading.as_drawn.schema import SCHEMA, AsDrawnPlanV2
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_PLAN,
    CONTRACT_READING_VIEW_LEGACY,
    Disposition,
    CONTRACTS,
    classify_vector_json,
)

_PRODUCTS = Path(
    "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_TRACKED = ("sm25_1f_v2.json", "sm25_2f_v2.json", "sm24_1f_v2.json")
_LEGACY = {
    "f9": Path("tests/fixtures/f9_window_host_crash/0_reading/1f_view.json"),
    "sm22": Path(
        "case_tests/e2e_tests/smalloffice_22/0_reading/1f_view.json"
    ),
}


# ── shared fixture helpers ─────────────────────────────────────────────────── #
def _raw_product(name: str) -> bytes:
    p = _PRODUCTS / name
    # ⛔ no exists()-and-skip: a vanished tracked fixture must be a red.
    assert p.is_file(), f"tracked as-drawn product missing: {p}"
    return p.read_bytes()


def _adapts(name: str, floor: str):
    return adapt_as_drawn_plan(
        _raw_product(name), input_id=name.removesuffix(".json"), floor_ref=floor
    )


def _today_says_yes_as_drawn(doc: dict) -> None:
    """The 'before' premise: today's producer type and classifier accept it."""
    AsDrawnPlanV2.model_validate(doc)
    decision = classify_vector_json(doc)
    assert decision.contract_id == CONTRACT_AS_DRAWN_PLAN, decision.reason


def _adapt_doc(doc: dict, input_id: str, floor: str):
    raw = json.dumps(doc, indent=1).encode("utf-8")
    return adapt_as_drawn_plan(raw, input_id=input_id, floor_ref=floor)


def _expect_error(thunk, code: str):
    with pytest.raises(EvidenceContractError) as exc:
        thunk()
    assert exc.value.code == code, (
        f"expected {code}, got {exc.value.code}: {exc.value.context}"
    )
    return exc.value


# ── synthetic as-drawn shapes (real products cannot exhibit these) ────────── #
def _gap() -> dict:
    return {
        "lo_px": 20, "hi_px": 24, "len_px": 4,
        "ink_by_family": {"F0": {"on_line": 2, "by_distance_px": {"2": 1},
                                  "span_ratio": 0.5, "nearest_px": 0}},
        "span_m": [1.1, 1.14], "len_m": 0.04,
    }


def _face(fid: str, axis: str, world_axis: str, col: int,
          runs_px: list, runs_m: list, gaps: list | None = None) -> dict:
    return {
        "id": fid, "axis": axis, "constant_world_axis": world_axis,
        "pos_px": float(col), "pos_m": 0.01 * col,
        "support_cols_px": [col, col + 1], "edges_m": [0.0, 0.02],
        "support_width_m": 0.02, "runs_px": runs_px, "runs_m": runs_m,
        "gaps": gaps if gaps is not None else ([_gap()] if fid == "F01" else []),
        "ink_coverage_per_run": [1.0] * len(runs_px),
        "covered_px": sum(hi - lo for lo, hi in runs_px),
        "support_px": sum(hi - lo for lo, hi in runs_px) + 1,
    }


def _pair_doc(runs_a_px: list, runs_b_px: list) -> dict:
    """Three faces: F01/F02 paired (with the run lengths the caller wants),
    F03 disposed non_wall.  Minimal honest shape for the fidelity tests."""
    runs_a_m = [[lo / 10.0, hi / 10.0] for lo, hi in runs_a_px]
    runs_b_m = [[lo / 10.0, hi / 10.0] for lo, hi in runs_b_px]
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": [
            _face("F01", "col", "x", 100, runs_a_px, runs_a_m),
            _face("F02", "col", "x", 112, runs_b_px, runs_b_m),
            _face("F03", "row", "y", 200, [[5, 9]], [[0.5, 0.9]]),
        ]},
        "declarations": {},
        "hypotheses": {
            "pairs": [
                {"face_a": "F01", "face_b": "F02", "spacing_px": 12.0,
                 "spacing_m": 0.12, "matched_declared_mm": [120],
                 "overlap_px": 30, "source": "selected"},
            ],
            "pair_candidates": [
                {"face_a": "F01", "face_b": "F02", "spacing_px": 12.0,
                 "spacing_m": 0.12, "matched_declared_mm": [120],
                 "overlap_px": 30},
            ],
            "opening_candidates": [],
            "opening_types": None,
            "pairs_status": "SELECTED",
            "non_wall_face_lines": {"F03": "a furniture edge on this dialect"},
            "unpaired_wall_faces": {},
            "solid_band_walls": {},
            "ambiguous_face_lines": {},
        },
    }
    AsDrawnPlanV2.model_validate(doc)  # premise: this IS a legal product
    return doc


def _legacy_doc(strokes: list[dict]) -> dict:
    doc = {"image_label": "legacy plan", "strokes": strokes}
    decision = classify_vector_json(doc)
    assert decision.contract_id == CONTRACT_READING_VIEW_LEGACY, decision.reason
    return doc


def _adapt_legacy(strokes: list[dict]):
    raw = json.dumps(_legacy_doc(strokes), indent=1).encode("utf-8")
    return adapt_legacy_reading_view(
        raw, input_id="legacy_synth", floor_ref="8f"
    )


_WALL_STROKE = {
    "id": "W01", "pen": "wall",
    "geometry": {"p1": [0, 0], "p2": [100, 0], "thickness_m": None},
    "note": "outer skin line (prose only -- ⛔ never parsed)",
}


# =========================================================================== #
# Acceptance 1 -- the three real products: per-product counts CLOSE
# =========================================================================== #
@pytest.mark.parametrize("name,floor", [
    ("sm25_1f_v2.json", "1f"),
    ("sm25_2f_v2.json", "2f"),
    ("sm24_1f_v2.json", "1f"),
])
def test_acceptance_1_real_products_counts_close(name, floor):
    art = _adapts(name, floor)
    validate_evidence_bundle(art)  # the green premise every red test leans on
    doc = json.loads(_raw_product(name))
    hyp = doc["hypotheses"]

    # expected counts RECOMPUTED from the product (the producer's five
    # accounting slots), ⛔ not read back from the adapter
    expected = {
        "claimed_wall": 2 * len(hyp.get("pairs") or [])
        + len(hyp.get("solid_band_walls") or {})
        + len(hyp.get("unpaired_wall_faces") or {}),
        "non_wall": len(hyp.get("non_wall_face_lines") or {}),
        "ambiguous": len(hyp.get("ambiguous_face_lines") or {}),
    }
    total_faces = len(doc["observations"]["face_lines"])

    got = {"claimed_wall": 0, "non_wall": 0, "ambiguous": 0}
    for d in art.bundle.face_dispositions:
        got[d.status] += 1
    assert got == expected, f"{name}: {got} != recomputed {expected}"
    # ⭐ the closure itself: every face disposed exactly once, no bucket leaks
    assert sum(got.values()) == total_faces, (
        f"{name}: {sum(got.values())} dispositions over {total_faces} face "
        "lines -- a face leaked between buckets or got dropped"
    )
    assert len(art.bundle.wall_claims) == (
        len(hyp.get("pairs") or []) + len(hyp.get("solid_band_walls") or {})
        + len(hyp.get("unpaired_wall_faces") or {})
    )
    # sm24's four solid bands must be four claims with no invented partner
    if name == "sm24_1f_v2.json":
        bands = [c for c in art.bundle.wall_claims if c.kind == "solid_band"]
        assert len(bands) == 4


# =========================================================================== #
# Acceptance 2 -- the two real legacy views: every basis lands unknown
# =========================================================================== #
@pytest.mark.parametrize("key", sorted(_LEGACY))
def test_acceptance_2_legacy_real_products_all_unknown(key):
    path = _LEGACY[key]
    assert path.is_file(), f"tracked legacy fixture missing: {path}"
    raw = path.read_bytes()
    doc = json.loads(raw)
    walls = [s for s in doc["strokes"] if s.get("pen") == "wall"]
    assert walls, "fixture premise broke: no wall strokes"

    # ⭐ PREMISE, measured not remembered: the only basis carriers in these
    # products are free-text notes, and they CONTRADICT each other -- so an
    # adapter that read notes would emit non-unknown bases here.
    notes = [s.get("note") or "" for s in walls]
    basis_keys = sum(
        1 for s in walls if "basis" in (s.get("geometry") or {})
    )
    assert basis_keys == 0, "a fixture grew a structured basis; update me"
    if key == "f9":
        assert any("外皮" in n for n in notes)
        assert any("中线" in n for n in notes)
    else:
        assert any("centerline" in n.lower() for n in notes)

    art = adapt_legacy_reading_view(
        raw, input_id=f"{key}_1f", floor_ref="1f"
    )
    validate_evidence_bundle(art)
    traces = [c for c in art.bundle.wall_claims
              if c.kind == "legacy_wall_trace"]
    assert len(traces) == len(walls)
    # ⭐ the acceptance: EVERY trace is unknown, with NO basis evidence --
    # the mechanical conclusion of "no structured declaration exists"
    assert all(c.source_basis == "unknown" for c in traces)
    assert all(c.basis_evidence_ref is None for c in traces)
    # f9 carries 7 window strokes: they are NAMED in the plan_openings debt,
    # ⛔ not silently dropped
    if key == "f9":
        windows = sum(
            1 for s in doc["strokes"] if s.get("pen") == "window"
        )
        debt = next(
            d for d in art.bundle.evidence_debts
            if d.channel == "plan_openings"
        )
        assert debt.description.startswith(f"{windows} window/door stroke")


def test_legacy_structured_basis_declaration_is_honoured():
    """``unknown`` is the mechanical default, ⛔ not a blind one: a TYPED
    ``geometry.basis`` key in the closed domain upgrades the claim and carries
    its evidence pointer; a key outside the domain is a loud malformed
    declaration (silence would swallow the producer's intent behind a typo)."""
    strokes = [
        {**_WALL_STROKE, "id": "W01",
         "geometry": {**_WALL_STROKE["geometry"], "basis": "centerline"}},
        {**_WALL_STROKE, "id": "W02"},
    ]
    art = _adapt_legacy(strokes)
    validate_evidence_bundle(art)
    by_id = {c.trace_ref.observation_id: c for c in art.bundle.wall_claims}
    assert by_id["W01"].source_basis == "centerline"
    assert by_id["W01"].basis_evidence_ref is not None
    assert by_id["W01"].basis_evidence_ref.json_pointer == \
        "/strokes/0/geometry/basis"
    assert by_id["W02"].source_basis == "unknown"

    bad = [
        {**_WALL_STROKE, "geometry": {**_WALL_STROKE["geometry"],
                                      "basis": "middle"}},
    ]
    err = _expect_error(
        lambda: _adapt_legacy(bad), "LEGACY_BASIS_DECLARATION_INVALID"
    )
    assert err.context["domain"] == list(LEGACY_BASIS_VALUES)


# =========================================================================== #
# Acceptance 3 -- module 2's pin retired: unselected dangling candidate
# =========================================================================== #
def test_acceptance_3_unselected_dangling_candidate_now_fails():
    """The exact corruption module 2 pinned to this module (its test
    ``test_nf4_5_..._module3_4_pinned`` measures it PASSING module 2's layer
    today): a ``pair_candidates`` entry NO selected pair uses, whose ``face_b``
    names a face that does not exist."""
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    selected = {
        frozenset((p["face_a"], p["face_b"]))
        for p in doc["hypotheses"]["pairs"]
    }
    victim = next(
        (k, c) for k, c in enumerate(doc["hypotheses"]["pair_candidates"])
        if frozenset((c["face_a"], c["face_b"])) not in selected
    )
    victim[1]["face_b"] = "L999"
    _today_says_yes_as_drawn(doc)  # BEFORE: module 1's type still accepts

    # BEFORE, at module 2's layer: the dangling id appears in NO selected pair
    # and NO bucket, so nothing that layer dereferences can see it.
    stray = "L999"
    in_pairs = any(
        stray in (p["face_a"], p["face_b"]) for p in doc["hypotheses"]["pairs"]
    )
    in_buckets = any(
        stray in (doc["hypotheses"].get(b) or {})
        for b in ("non_wall_face_lines", "unpaired_wall_faces",
                  "solid_band_walls", "ambiguous_face_lines")
    )
    assert not in_pairs and not in_buckets

    # AFTER: the adapter walks the WHOLE candidate graph -- selected or not.
    err = _expect_error(
        lambda: _adapt_doc(doc, "pin_candidate", "2f"),
        "PAIR_CANDIDATE_REFERENCES_UNKNOWN_FACE",
    )
    assert err.context["candidate_index"] == victim[0]
    assert err.context["observation_id"] == "L999"
    # ⭐ and the control: the SAME product with the dangling entry REMOVED
    # adapts green -- the refusal is about the dangling reference, not about
    # the product.
    del doc["hypotheses"]["pair_candidates"][victim[0]]
    control = _adapt_doc(doc, "pin_candidate_control", "2f")
    validate_evidence_bundle(control)


# =========================================================================== #
# Acceptance 4 -- paired-face fidelity at this layer, both directions;
#                tail segmentation pinned to module 4
# =========================================================================== #
def _assert_one_pair_claim(art):
    """The invariants that must hold for a selected pair at THIS layer, with
    equal OR unequal runs: one claim, both faces consumed by it and by
    nothing else, full segmentation evidence travelling on each ref."""
    pairs = [c for c in art.bundle.wall_claims if c.kind == "paired_faces"]
    assert len(pairs) == 1
    claim = pairs[0]
    assert {claim.face_a_ref.observation_id,
            claim.face_b_ref.observation_id} == {"F01", "F02"}
    for fid in ("F01", "F02"):
        disp = next(
            d for d in art.bundle.face_dispositions
            if d.face_ref.observation_id == fid
        )
        assert disp.status == "claimed_wall"
        assert disp.consuming_claim_id == claim.claim_id
        ref = (claim.face_a_ref if fid == "F01" else claim.face_b_ref)
        witnessed = {p.rsplit("/", 1)[-1]
                     for p in ref.pixel_witness_pointers}
        # the design's own required-witness set for a paired face
        # (§4.1: support_cols_px / runs_px / gaps) -- the compiler segments
        # from these nodes; extra witnesses beyond it are fine
        assert {"support_cols_px", "runs_px", "gaps"} <= witnessed
    # ⛔ no face of the pair may be re-bucketed for having unequal runs:
    # that would be correction re-making reading's pairing decision.
    others = [c for c in art.bundle.wall_claims if c.kind != "paired_faces"]
    consumed_by_others = [
        c for c in others
        if getattr(c, "face_ref", getattr(c, "band_face_ref", None))
        and getattr(getattr(c, "face_ref", None), "observation_id", None)
        in ("F01", "F02")
        or getattr(getattr(c, "band_face_ref", None), "observation_id", None)
        in ("F01", "F02")
    ]
    assert consumed_by_others == []


def test_acceptance_4_unequal_runs_stay_one_claim_with_full_evidence():
    doc = _pair_doc(runs_a_px=[[10, 100]], runs_b_px=[[10, 40]])
    art = _adapt_doc(doc, "unequal_pair", "9f")
    validate_evidence_bundle(art)  # green premise
    _assert_one_pair_claim(art)

    # the segmentation evidence in the FROZEN BYTES is intact and unequal --
    # the adapter neither stretched the short face nor trimmed the long one
    source = json.loads(art.frozen_sources[0].raw_bytes)
    runs_a = resolve_json_pointer(
        source, f"/observations/face_lines/{0}/runs_px"
    )
    runs_b = resolve_json_pointer(
        source, f"/observations/face_lines/{1}/runs_px"
    )
    assert runs_a == [[10, 100]]
    assert runs_b == [[10, 40]]
    assert runs_a != runs_b  # premise: this really is the unequal shape


def test_acceptance_4_equal_runs_produce_no_fragment_claims():
    doc = _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]])
    art = _adapt_doc(doc, "equal_pair", "9f")
    validate_evidence_bundle(art)  # green premise
    _assert_one_pair_claim(art)
    # the second direction of the acceptance: with nothing to cut, NO claim
    # kind besides the pair (and no disposition beyond the three faces) --
    # an adapter that unconditionally shreds pairs into single faces fails.
    kinds = {c.kind for c in art.bundle.wall_claims}
    assert kinds == {"paired_faces"}
    assert len(art.bundle.face_dispositions) == 3


def test_tail_segmentation_is_delivered_by_module_4():
    """PIN FLIPPED by module 4's dispatch (its carried mandate ①).  This
    used to be ``test_tail_segmentation_is_pinned_to_module_4`` and asserted
    only the negative half -- segmentation does NOT happen at the adapter
    layer.  Module 4's compiler now exists, so the pin points at the real
    implementation: unequal runs must surface as ``single_face_fragment``
    pieces that still name the original claim, and equal runs must produce
    none.

    The module-3 boundary half stays and keeps its teeth: the BUNDLE is
    shape-identical for equal and unequal runs -- if the difference ever
    surfaced here, THIS layer would be computing geometry (design §4.1: a
    claim carries ⛔ no geometry values, so "which interval is a tail" has
    no type slot at this layer).
    """
    from src.agent.correction.wall_compiler import compile_wall_ir

    unequal = _adapt_doc(
        _pair_doc(runs_a_px=[[10, 100]], runs_b_px=[[10, 40]]),
        "pin_module4_unequal", "9f",
    )
    equal = _adapt_doc(
        _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]]),
        "pin_module4_equal", "9f",
    )
    validate_evidence_bundle(unequal)
    validate_evidence_bundle(equal)
    # the bundle is shape-identical for equal and unequal runs: the
    # difference must surface downstream, in the compiler's segmentation --
    # if it ever surfaced here, THIS layer would be computing geometry.
    def _shape(art):
        return [
            (c.kind,
             c.face_a_ref.observation_id if c.kind == "paired_faces" else None,
             c.face_b_ref.observation_id if c.kind == "paired_faces" else None)
            for c in art.bundle.wall_claims
        ]
    assert _shape(unequal) == _shape(equal)
    assert all(c.kind != "single_face" for c in unequal.bundle.wall_claims)

    # ── the flipped half: the compiler segments, faithfully both ways ─────
    compiled_unequal = compile_wall_ir(unequal)
    pair_walls = [
        w for w in compiled_unequal.walls if w.claim_kind == "paired_faces"
    ]
    assert len(pair_walls) == 1
    wall = pair_walls[0]
    # A's unshared stretch [4, 10] survives as a fragment STILL OWNED by the
    # claim; the double-face wall covers only the joint stretch [1, 4]
    assert len(wall.unshared_tail_fragments) == 1
    fragment = wall.unshared_tail_fragments[0]
    assert fragment.source_claim_id == wall.source_claim_ids[0]
    assert fragment.tail_of == "face_a"
    assert fragment.face_ref.observation_id == "F01"
    assert fragment.along_interval_m == (4.0, 10.0)
    assert wall.double_face_intervals == ((1.0, 4.0),)
    assert wall.resolved_along_intervals == ((1.0, 10.0),)

    compiled_equal = compile_wall_ir(equal)
    equal_wall = next(
        w for w in compiled_equal.walls if w.claim_kind == "paired_faces"
    )
    assert equal_wall.unshared_tail_fragments == ()
    assert equal_wall.double_face_intervals == ((1.0, 8.0),)


# =========================================================================== #
# Acceptance 5 -- a cleared pairs selection is never rebuilt from candidates
# =========================================================================== #
def test_acceptance_5_cleared_pairs_refuses_instead_of_pairing():
    """The real-product shape of "the model did not select": ``pairs=None``
    with ``pairs_status=ABSENT_NO_MODEL_SELECTION`` and the buckets untouched
    (exactly what the producer returns when no perception input arrives).
    The adapter must refuse with the pairing gap named -- 303 candidates were
    available to invent from, and none was used."""
    doc = json.loads(_raw_product("sm25_2f_v2.json"))
    doc["hypotheses"]["pairs"] = None
    doc["hypotheses"]["pairs_status"] = "ABSENT_NO_MODEL_SELECTION"
    _today_says_yes_as_drawn(doc)  # BEFORE: still a legal product

    err = _expect_error(
        lambda: _adapt_doc(doc, "pairs_cleared", "2f"),
        "PAIRS_SELECTION_ABSENT",
    )
    assert err.context["remedy"] == "reperception_required"
    assert err.context["candidate_count"] == 303  # ⭐ there WAS material to
    # invent from -- the refusal is a policy, not an empty graph
    assert len(err.context["unaccounted_face_lines"]) == 42


def test_absent_pairs_but_covered_faces_travel_with_debt():
    """The honest covered shape: no selection, but every face line sits in one
    of the four buckets.  The bundle adapts GREEN with a structured
    ``pairs_selection_absent`` debt and ZERO pair claims -- the debt is the
    compiler's cue to demand reperception, ⛔ never licence to pair."""
    doc = _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]])
    hyp = doc["hypotheses"]
    hyp["pairs"] = None
    hyp["pairs_status"] = "ABSENT_NO_MODEL_SELECTION"
    hyp["unpaired_wall_faces"] = {
        "F01": "lone face: perception paired nothing",
        "F02": "lone face: perception paired nothing",
    }
    art = _adapt_doc(doc, "pairs_absent_covered", "9f")
    validate_evidence_bundle(art)
    assert not [c for c in art.bundle.wall_claims
                if c.kind == "paired_faces"]
    assert len([c for c in art.bundle.wall_claims
                if c.kind == "single_face"]) == 2
    debt = next(
        d for d in art.bundle.evidence_debts
        if d.kind == "pairs_selection_absent"
    )
    assert debt.channel == "walls"


def test_explicit_empty_selection_is_a_product_not_a_debt():
    """``pairs=[]`` CLAIMS a selection was made and chose nothing -- a legal
    product when every face is bucketed.  It carries no absent-selection debt
    (that word is reserved for "no selection supplied")."""
    doc = _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]])
    hyp = doc["hypotheses"]
    hyp["pairs"] = []
    hyp["pairs_status"] = "SELECTED"
    hyp["unpaired_wall_faces"] = {
        "F01": "lone face", "F02": "lone face",
    }
    art = _adapt_doc(doc, "pairs_empty_list", "9f")
    validate_evidence_bundle(art)
    assert not [d for d in art.bundle.evidence_debts
                if d.kind == "pairs_selection_absent"]
    assert not [c for c in art.bundle.wall_claims
                if c.kind == "paired_faces"]


# =========================================================================== #
# Acceptance 6 -- this module wires nothing
# =========================================================================== #
def test_the_adapters_import_no_pipeline():
    """Behavioural half of the zero-wiring reading: a clean interpreter that
    imports ONLY this module must never reach the pipeline.  Permanent -- the
    adapter layer is never allowed to grow an orchestration import."""
    probe = (
        "import sys; import src.agent.correction.evidence_adapters; "
        "print(any(m == 'src.agent.pipeline' for m in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_as_drawn_is_still_not_consumed():
    """The one-line gate from the wiring survey stays untouched BY THIS
    DISPATCH: registering this adapter is module 7's on-purpose flip."""
    spec = next(s for s in CONTRACTS
                if s.contract_id == CONTRACT_AS_DRAWN_PLAN)
    assert spec.disposition is Disposition.KNOWN_NOT_CONSUMED


# =========================================================================== #
# Acceptance 7 -- determinism, and the module-2 weak spot this module closes
# =========================================================================== #
@pytest.mark.parametrize("name,floor", [
    ("sm25_1f_v2.json", "1f"),
    ("sm25_2f_v2.json", "2f"),
    ("sm24_1f_v2.json", "1f"),
])
def test_acceptance_7_same_bytes_twice_is_byte_identical(name, floor):
    first = _adapts(name, floor)
    second = _adapts(name, floor)
    assert first.bundle.content_sha256 == second.bundle.content_sha256
    assert (
        canonical_json_bytes(first.bundle.model_dump(mode="json"))
        == canonical_json_bytes(second.bundle.model_dump(mode="json"))
    )


def test_module2_weak_spot_present_channel_requires_payload():
    """Module 2's execution report named its own weakest spot: "walls present
    + zero claims + zero debt" validates at the type layer.  The ADAPTER is
    where that shape must not be minted -- present is only ever emitted with
    real claims behind it; a product yielding no claim gets an absent channel
    with an explicit debt."""
    doc = _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]])
    doc["observations"]["face_lines"] = [doc["observations"]["face_lines"][2]]
    doc["hypotheses"]["pairs"] = []
    # ⚠️ the candidate graph must be cleared together with the faces: leaving
    # it would dangle F01/F02 in it, and the adapter's full-graph walk
    # (acceptance 3) rightly refuses that -- measured while building this
    # very fixture, which is the teeth working, not a nuisance.
    doc["hypotheses"]["pair_candidates"] = []
    doc["hypotheses"]["non_wall_face_lines"] = {"F03": "nothing here"}
    art = _adapt_doc(doc, "empty_walls", "9f")
    validate_evidence_bundle(art)
    walls = next(c for c in art.bundle.channel_status
                 if c.channel == "walls")
    assert walls.state == "absent"
    assert walls.covered_by_debt_ids
    assert art.bundle.wall_claims == []
    # and the positive side: the real products mint present WITH payload
    real = _adapts("sm24_1f_v2.json", "1f")
    real_walls = next(c for c in real.bundle.channel_status
                      if c.channel == "walls")
    assert real_walls.state == "present"
    assert real.bundle.wall_claims


# =========================================================================== #
# The adapters refuse what they are not the adapter for
# =========================================================================== #
def test_adapter_refuses_the_other_contract():
    legacy_raw = json.dumps(
        _legacy_doc([dict(_WALL_STROKE)]), indent=1
    ).encode("utf-8")
    as_drawn_raw = json.dumps(
        _pair_doc(runs_a_px=[[10, 80]], runs_b_px=[[10, 80]]), indent=1
    ).encode("utf-8")
    _expect_error(
        lambda: adapt_as_drawn_plan(
            legacy_raw, input_id="wrong", floor_ref="1f"
        ),
        "ADAPTER_CONTRACT_MISMATCH",
    )
    _expect_error(
        lambda: adapt_legacy_reading_view(
            as_drawn_raw, input_id="wrong", floor_ref="1f"
        ),
        "ADAPTER_CONTRACT_MISMATCH",
    )
    _expect_error(
        lambda: adapt_as_drawn_plan(b"not json", input_id="x", floor_ref="1f"),
        "SOURCE_NOT_JSON",
    )


def test_legacy_duplicate_stroke_id_is_loud():
    strokes = [dict(_WALL_STROKE), dict(_WALL_STROKE)]
    _expect_error(
        lambda: _adapt_legacy(strokes), "DUPLICATE_OBSERVATION_ID"
    )
