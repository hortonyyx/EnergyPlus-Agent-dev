"""B2 — multi-floor assembly (dispatch 2026-09-03ai / rework-2 2026-09-04g).

WHAT THIS FILE LOCKS (the §四 acceptance table, as RULES, ⛔ not as transcripts
of one run's readings):

1. every derived storey z (z_floor AND ceiling_height's two operands)
   dereferences back to the exact frozen byte it names (T1);
2. the new multi-floor path takes its z ONLY from the derivation: neuter the
   derivation and it fails LOUDLY, ⛔ it never falls back to a hand-filled z
   (T5) — and the entry point has no z parameter to fall back to;
3. a two-storey case assembles ``floors[]`` and passes the EXISTING z-stack
   continuity check (pipeline.py:661 ``correction_draw_issues``), ⛔ not a
   relaxed copy (T3);
4. the storey count is COUNTED from the data and heights COMPUTED from it: a
   synthetic three-storey 2.9 / 3.3 / 4.2 elevation assembles 3 floors with
   those heights, and ⛔ no sm25 elevation reading (3.6 / 7.202 …) appears in
   the new production code;
5. bad inputs fail loudly with named codes (plan/ladder count mismatch,
   non-ascending ladder, non-positive ceiling);
7. ⛔ zero gt contact: the new module and this test import neither the gt
   loader module nor read the signed-gt directory (the needles are built by
   concatenation below so this file does not self-match its own scan).

REWORK-2 (2026-09-04g) — the type-layer closure the first two rounds missed:
  * B-1: z drift is a MACHINE gate — ``derive_floor_ladder`` consumes the SEALED
    carrier and runs B3's ``validate_evidence_bundle`` as its first act, so a
    ref-kept / value-drifted claim goes red as
    ``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`` (⛔ not a two-sample spot-check);
  * B-2: the hand-fill z path does not exist at the type layer — assembly
    accepts ONLY a ``ValidatedFloorLadder`` minted by ``derive_floor_ladder``,
    and every derived z is RESOLVED FROM THE FROZEN BYTES, so a ``model_copy`` on
    ``z_m`` (round 2's bypass) or a hand-forged level cannot move the assembled z
    (see the §三 self-attack tests below);
  * B-3: the footprint relabel is decided by an EXPLICIT pre-construction
    footprint compare; every construction ``ValidationError`` propagates RAW.

⚠️ Everything here is SYNTHETIC (the B3 factory's three-storey / mixed-height
fixture), so any sm25 constant smuggled into the production code breaks these
tests — and it keeps the whole file gt-free.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import src.agent.pipeline as pipeline
from src.agent.correction.evidence_adapters import (
    adapt_as_drawn_elevation,
    adapt_as_drawn_plan,
)
from src.agent.correction.evidence_contract import resolve_json_pointer
from src.agent.correction.multifloor import (
    MultiFloorAssemblyError,
    ValidatedFloorLadder,
    assemble_multifloor_geometry,
    derive_floor_ladder,
)
from src.agent.correction.schema import CorrectedGeometryV3

from tests.test_b3_elevation_leg import _synthetic_bytes

REPO = Path(__file__).resolve().parents[1]
_PLAN_PRODUCTS = (
    REPO
    / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)


# ── synthetic building blocks ─────────────────────────────────────────────── #
def _elevation(storey_mm: list[float]):
    """An adapted as-drawn elevation artifact for the given storey ladder."""
    return adapt_as_drawn_elevation(
        _synthetic_bytes(storey_mm), input_id="synth_elev", facade_ref="S"
    )


def _docs(art) -> dict:
    """The frozen-source doc map a ``_DerivedFloorLevel`` resolves z against."""
    return {
        s.artifact.input_id: json.loads(s.raw_bytes) for s in art.frozen_sources
    }


def _claim_at(art, z_m: float):
    """The honest floor-level claim whose FROZEN BYTE z equals ``z_m`` — its
    ``z_ref`` points at that byte, so a level built from it byte-resolves to
    ``z_m`` (⛔ regardless of what ``claim.z_m`` says)."""
    doc = _docs(art)[art.frozen_sources[0].artifact.input_id]
    for c in art.bundle.floor_level_claims:
        if round(resolve_json_pointer(doc, c.z_ref.json_pointer), 6) == round(z_m, 6):
            return c
    raise AssertionError(f"no honest claim at z={z_m}")


def _square_floor(
    floor_id: str, footprint: list[list[float]]
) -> CorrectedGeometryV3:
    """A clean one-cell single-floor geometry over ``footprint`` (a simple
    rectangle ring, CCW, open).  z is a throwaway 999 — assembly re-stamps it
    from the derived ladder, so what it carries must not matter (T5)."""
    xs = [p[0] for p in footprint]
    ys = [p[1] for p in footprint]
    return CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[min(xs), max(xs)],
        footprint_y=[min(ys), max(ys)],
        floors=[
            {
                "id": floor_id,
                "name": floor_id,
                "z_floor": 999.0,
                "ceiling_height": 999.0,
                "footprint": {"vertices": footprint},
                "cells": [
                    {
                        "id": f"{floor_id}-c0",
                        "x": [min(xs), max(xs)],
                        "y": [min(ys), max(ys)],
                        "polygon": footprint,
                    }
                ],
            }
        ],
        windows=[],
        facade_segments=[],
    )


_RECT = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]


# ── acceptance 1: every derived z dereferences back to its frozen byte ─────── #
def test_derived_z_dereferences_back_to_the_frozen_bytes():
    art = _elevation([2900.0, 3300.0, 4200.0])
    doc = json.loads(art.frozen_sources[0].raw_bytes)
    ladder = derive_floor_ladder(art)
    assert len(ladder) == 3
    for level in ladder:
        # z_floor's own byte
        assert level.z_floor_m == resolve_json_pointer(
            doc, level.z_floor_ref.json_pointer
        )
        # ceiling_height is a DERIVED difference — BOTH operands trace to bytes
        top = resolve_json_pointer(doc, level.z_top_ref.json_pointer)
        assert level.ceiling_height_m == pytest.approx(top - level.z_floor_m)
        # the pointer is anchored into THIS artifact's frozen source
        assert level.z_floor_ref.source_output_sha256 == (
            art.frozen_sources[0].artifact.source_output_sha256
        )


def test_derived_heights_are_the_input_storey_heights():
    ladder = derive_floor_ladder(_elevation([2900.0, 3300.0, 4200.0]))
    assert [round(l.z_floor_m, 6) for l in ladder] == [0.0, 2.9, 6.2]
    assert [round(l.ceiling_height_m, 6) for l in ladder] == [2.9, 3.3, 4.2]


# ── acceptance 3: two-storey assembly passes the EXISTING continuity check ─── #
def test_two_storey_assembles_and_passes_pipeline_zstack_check():
    ladder = derive_floor_ladder(_elevation([2900.0, 3300.0]))  # 3 rungs -> 2
    assert len(ladder) == 2
    geom = assemble_multifloor_geometry(
        ladder, [_square_floor("f0", _RECT), _square_floor("f1", _RECT)]
    )
    assert len(geom.floors) == 2
    assert [
        (round(f.z_floor, 6), round(f.ceiling_height, 6)) for f in geom.floors
    ] == [(0.0, 2.9), (2.9, 3.3)]
    # ⭐ T3: pass pipeline.py:661-668's ACTUAL check, not a private copy.
    issues = pipeline.correction_draw_issues(geom, 0)
    assert issues == [], issues
    assert not any("z-stack" in msg for msg in issues)


# ── acceptance 4: storey count / heights come from the DATA ────────────────── #
def test_three_storey_mixed_heights_assemble_three_floors():
    ladder = derive_floor_ladder(_elevation([2900.0, 3300.0, 4200.0]))
    geom = assemble_multifloor_geometry(
        ladder, [_square_floor(f"f{i}", _RECT) for i in range(3)]
    )
    assert len(geom.floors) == 3
    assert [round(f.ceiling_height, 6) for f in geom.floors] == [2.9, 3.3, 4.2]
    assert pipeline.correction_draw_issues(geom, 0) == []


def test_reshaped_ladder_yields_a_new_floor_count():
    """A two-storey ladder gives two floors from the SAME code — the count is
    not a constant.  (A code that hardcoded 3 storeys fails here.)"""
    ladder = derive_floor_ladder(_elevation([3050.0, 2750.0]))
    geom = assemble_multifloor_geometry(
        ladder, [_square_floor("f0", _RECT), _square_floor("f1", _RECT)]
    )
    assert len(geom.floors) == 2
    assert [round(f.z_floor, 6) for f in geom.floors] == [0.0, 3.05]


def test_no_sm25_elevation_reading_is_hardcoded_in_new_code():
    """Acceptance #4's grep, as a lock: no sm25 storey/level reading
    (3.6 / 3600 / 7.202 / 7202) appears in the new B2 production source."""
    src = (REPO / "src/agent/correction/multifloor.py").read_text("utf-8")
    b2_block = pipeline_b2_source()
    for needle in ("3.6", "3600", "7.202", "7202"):
        assert needle not in src, (needle, "multifloor.py")
        assert needle not in b2_block, (needle, "pipeline B2 block")


def pipeline_b2_source() -> str:
    """The B2 region of pipeline.py (run_multifloor_correction + its
    NamedTuple), sliced by its banner comments so this lock reads only the
    code this dispatch added."""
    text = (REPO / "src/agent/pipeline.py").read_text("utf-8")
    start = text.index("# B2 multi-floor assembly")
    end = text.index("# 4_mep — physical-information authoring", start)
    return text[start:end]


# ── acceptance 5: bad inputs fail loudly with NAMED codes ──────────────────── #
def test_plan_count_mismatch_is_loud():
    ladder = derive_floor_ladder(_elevation([2900.0, 3300.0, 4200.0]))  # 3
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(
            ladder, [_square_floor("f0", _RECT), _square_floor("f1", _RECT)]
        )  # only 2 plan products for 3 storeys
    assert exc.value.code == "FLOOR_PLAN_COUNT_MISMATCH"
    assert exc.value.detail["n_storeys_from_ladder"] == 3
    assert exc.value.detail["n_plan_products"] == 2


def test_non_ascending_ladder_is_loud():
    """Two floor lines at the same FROZEN BYTE z: the ladder does not strictly
    ascend ("标高不单调"), the degenerate zero-height case.  Exercised through
    ``_mint_ladder`` (the byte-resolving core), with a duplicate rung forged by
    re-pointing one claim's ``z_ref`` at another's frozen byte."""
    from src.agent.correction.multifloor import _mint_ladder

    art = _elevation([2900.0, 3300.0])
    docs = _docs(art)
    lo = _claim_at(art, 0.0)
    hi = _claim_at(art, 2.9)
    # a duplicate rung: point hi's z_ref at lo's frozen byte (both -> 0.0)
    dup = hi.model_copy(update={"z_ref": lo.z_ref, "structure_line_id": "DUP"})
    with pytest.raises(MultiFloorAssemblyError) as exc:
        _mint_ladder([lo, dup], docs)
    assert exc.value.code == "FLOOR_LADDER_NOT_ASCENDING"
    assert exc.value.detail["rise_m"] == 0.0


def test_degenerate_ladder_is_loud():
    """Fewer than MIN_FLOOR_LEVELS rungs is loud in the derivation core.  (The
    production adapter also refuses a single-level elevation up front, with the
    same code — tested in test_b3_elevation_leg; here we lock the core.)"""
    from src.agent.correction.multifloor import _mint_ladder

    art = _elevation([2900.0, 3300.0])
    with pytest.raises(MultiFloorAssemblyError) as exc:
        _mint_ladder([_claim_at(art, 0.0)], _docs(art))
    assert exc.value.code == "FLOOR_LADDER_DEGENERATE"


def test_nonpositive_ceiling_is_loud():
    """The assembly boundary check: even a FORGED sealed ladder whose level's
    bounding claims resolve to the SAME byte z (a non-physical zero height) is
    stopped here.  ⭐ There is no z keyword to forge a bare z with (B-2); the
    forge must supply claims, and ceiling is byte-resolved from them."""
    from src.agent.correction.multifloor import _DerivedFloorLevel

    art = _elevation([2900.0, 3300.0])
    z0 = _claim_at(art, 0.0)
    bad = _DerivedFloorLevel(
        floor_index=0, lower=z0, upper=z0, frozen_docs=_docs(art)
    )
    assert bad.ceiling_height_m == 0.0  # ← non-positive, byte-resolved
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(
            ValidatedFloorLadder((bad,)), [_square_floor("f0", _RECT)]
        )
    assert exc.value.code == "NONPOSITIVE_CEILING_HEIGHT"


def test_per_floor_footprint_mismatch_is_loud():
    """Invariant #6: assembly is common-footprint only; different per-floor
    footprints (setback) are refused by name, ⛔ not silently allowed."""
    ladder = derive_floor_ladder(_elevation([2900.0, 3300.0]))
    other = [[0.0, 0.0], [7.0, 0.0], [7.0, 4.0], [0.0, 4.0]]  # wider
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(
            ladder, [_square_floor("f0", _RECT), _square_floor("f1", other)]
        )
    assert exc.value.code == "PER_FLOOR_FOOTPRINT_MISMATCH"


def test_duplicate_floor_id_is_loud():
    ladder = derive_floor_ladder(_elevation([2900.0, 3300.0]))
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(
            ladder, [_square_floor("dup", _RECT), _square_floor("dup", _RECT)]
        )
    assert exc.value.code == "DUPLICATE_FLOOR_ID"


# ── acceptance 2 / T5: the new path takes z ONLY from the derivation ───────── #
def test_run_multifloor_has_no_z_parameter():
    """Structural half of T5: the entry point cannot be hand-fed a z."""
    import inspect

    params = set(inspect.signature(pipeline.run_multifloor_correction).parameters)
    assert not any("z_floor" in p or "ceiling_height" in p for p in params)
    assert not any(
        "z_floor" in f or "ceiling_height" in f
        for f in pipeline.MultiFloorPlanRun._fields
    )


def test_wiring_feeds_the_derived_z_into_the_chain(monkeypatch):
    """Behavioural half of T5 + T1: run_multifloor_correction calls
    run_correction with ``evidence_chain=True`` and the byte-validated level of
    each DERIVED rung — captured here, ⛔ never a caller-declared value."""
    art = _elevation([2900.0, 3300.0])  # storeys: (0, 2.9), (2.9, 3.3)
    ladder = derive_floor_ladder(art)
    seen: list[dict] = []

    def _fake_run_correction(*args, **kwargs):
        seen.append(kwargs)
        assert kwargs["evidence_chain"] is True
        fid = f"f{len(seen) - 1}"
        return _square_floor(fid, _RECT)

    monkeypatch.setattr(pipeline, "run_correction", _fake_run_correction)
    runs = [
        pipeline.MultiFloorPlanRun(Path("v0"), "p0.json", Path("o0")),
        pipeline.MultiFloorPlanRun(Path("v1"), "p1.json", Path("o1")),
    ]
    geom = pipeline.run_multifloor_correction(art, runs)
    fed = [
        (
            k["evidence_chain_level"].z_floor_m,
            k["evidence_chain_level"].ceiling_height_m,
        )
        for k in seen
    ]
    assert fed == [(l.z_floor_m, l.ceiling_height_m) for l in ladder]
    assert [(f.z_floor, f.ceiling_height) for f in geom.floors] == fed


def test_neutered_derivation_fails_loud_never_falls_back(monkeypatch):
    """Acceptance #2: remove the derivation (it returns nothing) and the new
    path must fail LOUDLY — ⛔ it must not silently fall back to a hand-filled
    z (there is none to fall back to)."""
    import src.agent.correction.multifloor as mf

    monkeypatch.setattr(
        pipeline, "run_correction", lambda *a, **k: _square_floor("x", _RECT)
    )
    monkeypatch.setattr(mf, "derive_floor_ladder", lambda art: ())
    # the pipeline imports derive_floor_ladder locally from mf, so the patch on
    # the module reaches it.  A neutered derivation yields zero storeys -> loud
    # count mismatch, ⛔ never a fall-back to a hand-filled z.
    art = _elevation([2900.0, 3300.0])
    runs = [pipeline.MultiFloorPlanRun(Path("v0"), "p0.json", Path("o0"))]
    with pytest.raises(MultiFloorAssemblyError) as exc:
        pipeline.run_multifloor_correction(art, runs)
    assert exc.value.code == "FLOOR_PLAN_COUNT_MISMATCH"


# ── acceptance 3 (integration): the REAL evidence chain, one storey ────────── #
def _chain_floor_ref(filename: str) -> str:
    m = re.search(r"(\d+)\s*f", Path(filename).stem, re.I)
    return m.group(0).lower() if m else Path(filename).stem


def _drive_plan_to_success(vector_dir: Path, filename: str):
    """Round-0 select-all + round-1 accept, built with the SAME floor_ref the
    chain derives from the file name (so the packet hashes match)."""
    from src.agent.correction.decision_executor import (
        build_decision_packet,
        compile_wall_ir,
        decision_hash,
    )
    from src.agent.correction.decision_schema import (
        CorrectionDecisionResponseV1,
        ItemDecisionV1,
    )
    from src.agent.correction.wall_compiler import FixedDecisionV1

    art = adapt_as_drawn_plan(
        (vector_dir / filename).read_bytes(),
        input_id=Path(filename).stem,
        floor_ref=_chain_floor_ref(filename),
        view_type="plan",
    )
    p0 = build_decision_packet(
        compile_wall_ir(art, profile="exploratory"), bundle=art, round_index=0
    )
    picks = tuple(
        (i.item_id, i.candidates[0].candidate_id) for i in p0.open_items
    )
    select = CorrectionDecisionResponseV1(
        packet_hash=p0.packet_hash,
        item_decisions=tuple(
            ItemDecisionV1(
                item_id=a,
                action="select_candidate",
                candidate_id=b,
                reason_code="WIRING_LOCK",
            )
            for a, b in picks
        ),
        whole_building_review={"verdict": "accept"},
    )
    p1 = build_decision_packet(
        compile_wall_ir(
            art,
            profile="exploratory",
            decisions=tuple(FixedDecisionV1(item_id=a, candidate_id=b) for a, b in picks),
        ),
        bundle=art,
        round_index=1,
        previous_decision_hashes=(decision_hash(select),),
    )
    return [
        select,
        CorrectionDecisionResponseV1(
            packet_hash=p1.packet_hash, whole_building_review={"verdict": "accept"}
        ),
    ]


def test_real_chain_one_storey_takes_z_from_the_ladder(tmp_path):
    """End to end through the REAL evidence chain (model-free via
    fixed_responses): a one-storey synthetic elevation (2 rungs → 0.0 / 2.9)
    drives a real sm25 plan product; the assembled floor's z comes from the
    ladder, ⛔ never sm25's own 3.6.  One floor, so the common-footprint
    assumption is trivially satisfied."""
    product = "sm25_2f_v2.json"
    source = _PLAN_PRODUCTS / product
    if not source.is_file():
        pytest.skip(f"plan product missing: {source}")
    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    (vector_dir / product).write_bytes(source.read_bytes())
    out_dir = tmp_path / "1_correction"
    out_dir.mkdir()

    art = _elevation([2900.0])  # 2 rungs -> exactly one storey
    run = pipeline.MultiFloorPlanRun(
        vector_dir=vector_dir,
        product_filename=product,
        out_dir=out_dir,
        fixed_responses=_drive_plan_to_success(vector_dir, product),
    )
    geom = pipeline.run_multifloor_correction(art, [run])
    assert len(geom.floors) == 1
    assert (
        round(geom.floors[0].z_floor, 6),
        round(geom.floors[0].ceiling_height, 6),
    ) == (0.0, 2.9)
    assert geom.floors[0].cells, "the real product must yield cells"


# ── rework acceptance 1: z drift is a MACHINE gate, not a spot-check ────────── #
def test_tampered_z_is_rejected_by_the_gate_before_any_chain(monkeypatch):
    """Rework §四 #1: keep the frozen ``z_ref``, hand-edit ``z_m`` on one
    claim, re-seal the carrier — the FORMAL entry must reject it with the B3
    value↔byte gate (``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE``) BEFORE any
    per-floor chain runs.  ⛔ Not "I spot-checked two"."""
    from src.agent.correction.evidence_contract import (
        CorrectionEvidenceBundleArtifactV1,
        EvidenceContractError,
        finalize_bundle,
    )

    art = _elevation([2900.0, 3300.0])
    claims = list(art.bundle.floor_level_claims)
    target = max(claims, key=lambda c: c.z_m)  # keep its z_ref, drift its value
    tampered = target.model_copy(update={"z_m": 12.34})
    bundle = art.bundle.model_copy(
        update={
            "floor_level_claims": [
                tampered if c is target else c for c in claims
            ]
        }
    )
    bundle = finalize_bundle(bundle)
    tampered_art = CorrectionEvidenceBundleArtifactV1(
        bundle=bundle, frozen_sources=art.frozen_sources
    )

    chain_calls: list = []
    monkeypatch.setattr(
        pipeline,
        "run_correction",
        lambda *a, **k: chain_calls.append(k) or _square_floor("x", _RECT),
    )
    runs = [pipeline.MultiFloorPlanRun(Path("v0"), "p0.json", Path("o0"))]
    with pytest.raises(EvidenceContractError) as exc:
        pipeline.run_multifloor_correction(tampered_art, runs)
    assert exc.value.code == "FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE"
    assert chain_calls == [], "the gate must fire BEFORE any per-floor chain"


def test_honest_carrier_passes_the_gate_and_derives():
    """The gate is a real gate, not a wall: the honest sealed carrier passes
    ``validate_evidence_bundle`` and the ladder derives from its claims."""
    from src.agent.correction.evidence_contract import validate_evidence_bundle

    art = _elevation([2900.0, 3300.0, 4200.0])
    validate_evidence_bundle(art)  # ⛔ must not raise on the honest carrier
    ladder = derive_floor_ladder(art)
    assert [round(l.z_floor_m, 6) for l in ladder] == [0.0, 2.9, 6.2]


# ── rework §四 #2 / §三: the hand-fill z path does not exist at the type layer  #
def test_no_raw_z_hand_fill_path_exists():
    """§四 #2 / §二: the reviewer's direct bypass
    ``DerivedFloorLevel(z_floor_m=12.34, ceiling_height_m=5.67)`` cannot be
    constructed — the carrier is private and has NO raw-z keyword.  z is
    byte-resolved from the bounding claims' refs, and its properties are
    read-only."""
    import src.agent.correction.multifloor as mf

    # the old public raw-z carrier is gone from the module's surface
    assert not hasattr(mf, "DerivedFloorLevel")
    assert "DerivedFloorLevel" not in mf.__all__

    # the private carrier has no z_floor_m / ceiling_height_m constructor keyword
    with pytest.raises(TypeError):
        mf._DerivedFloorLevel(z_floor_m=12.34, ceiling_height_m=5.67)

    # z_floor_m / ceiling_height_m are read-only, byte-resolved PROPERTIES
    art = _elevation([2900.0, 3300.0])
    level = mf._DerivedFloorLevel(
        floor_index=0,
        lower=_claim_at(art, 0.0),
        upper=_claim_at(art, 2.9),
        frozen_docs=_docs(art),
    )
    assert (level.z_floor_m, round(level.ceiling_height_m, 6)) == (0.0, 2.9)
    with pytest.raises((AttributeError, TypeError)):
        level.z_floor_m = 99.0  # frozen + property: no setter


def test_reviewer_round2_bypass_is_dead_at_the_public_helpers():
    """§三 #1 — the reviewer's EXACT round-2 path, replayed verbatim: keep both
    claims' honest ``z_ref``, ``model_copy`` their ``z_m`` to 12.34 / 17.91, and
    try to walk the PUBLIC helper.  ``derive_floor_ladder`` now takes only the
    sealed carrier and runs the gate, so the drifted ``z_m`` is a named red — the
    two-public-helper combination that assembled last round no longer exists."""
    from src.agent.correction.evidence_contract import (
        CorrectionEvidenceBundleArtifactV1,
        EvidenceContractError,
        finalize_bundle,
    )

    art = _elevation([2900.0, 3300.0])
    ordered = sorted(art.bundle.floor_level_claims, key=lambda c: c.z_m)
    forged_values = {ordered[0].structure_line_id: 12.34,
                     ordered[1].structure_line_id: 17.91}
    tampered_claims = [
        c.model_copy(update={"z_m": forged_values[c.structure_line_id]})
        if c.structure_line_id in forged_values else c
        for c in art.bundle.floor_level_claims
    ]
    bundle = finalize_bundle(
        art.bundle.model_copy(update={"floor_level_claims": tampered_claims})
    )
    tampered_art = CorrectionEvidenceBundleArtifactV1(
        bundle=bundle, frozen_sources=art.frozen_sources
    )
    with pytest.raises(EvidenceContractError) as exc:
        derive_floor_ladder(tampered_art)  # ← the only public entry now
    assert exc.value.code == "FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE"

    # and there is no Sequence[FloorLevelClaimV1] overload to slip past the gate
    with pytest.raises((AttributeError, TypeError)):
        derive_floor_ladder(tampered_claims)


def test_my_own_same_shape_forge_the_sealed_ladder_cannot_inject_a_hand_z():
    """§三 #2 — my OWN same-shape attack, one the reviewer did NOT run: skip the
    gate entirely and hand-forge the sealed carrier.  Build a
    ``ValidatedFloorLadder`` directly from a level whose bounding claims had
    their ``z_m`` ``model_copy``'d to 12.34 / 17.91 (honest ``z_ref`` kept), then
    assemble.  Because z is byte-resolved, the assembled storey z is the HONEST
    byte (0.0 / 2.9), ⛔ NEVER the hand-filled 12.34 — the swap has no effect."""
    from src.agent.correction.multifloor import _DerivedFloorLevel

    art = _elevation([2900.0, 3300.0])
    lo = _claim_at(art, 0.0).model_copy(update={"z_m": 12.34})   # keep z_ref
    hi = _claim_at(art, 2.9).model_copy(update={"z_m": 17.91})   # keep z_ref
    forged_level = _DerivedFloorLevel(
        floor_index=0, lower=lo, upper=hi, frozen_docs=_docs(art)
    )
    # the level ignores the hand ``z_m`` and reads the frozen bytes
    assert forged_level.z_floor_m == 0.0
    assert round(forged_level.ceiling_height_m, 6) == 2.9
    geom = assemble_multifloor_geometry(
        ValidatedFloorLadder((forged_level,)), [_square_floor("f0", _RECT)]
    )
    assert (geom.floors[0].z_floor, round(geom.floors[0].ceiling_height, 6)) == (
        0.0,
        2.9,
    )
    assert geom.floors[0].z_floor != 12.34


def test_assemble_refuses_a_bare_level_sequence():
    """§三 #2 (cont.): the low-level helpers cannot be recombined into assembly —
    ``assemble_multifloor_geometry`` type-refuses a bare list of levels; only a
    ``ValidatedFloorLadder`` (minted by the gate-running ``derive_floor_ladder``)
    is accepted."""
    from src.agent.correction.multifloor import _DerivedFloorLevel

    art = _elevation([2900.0, 3300.0])
    level = _DerivedFloorLevel(
        floor_index=0,
        lower=_claim_at(art, 0.0),
        upper=_claim_at(art, 2.9),
        frozen_docs=_docs(art),
    )
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry([level], [_square_floor("f0", _RECT)])
    assert exc.value.code == "UNSEALED_FLOOR_LADDER"


def test_run_correction_refuses_a_bare_z_requires_validated_level(tmp_path):
    """§三 #2 (cont.): the migrated ``run_correction`` face — a bare hand-filled z
    is refused (``TypeError``), and a missing level is a loud ``ValueError``; the
    old ``evidence_chain_z_floor_m`` float param no longer exists."""
    import inspect

    params = set(inspect.signature(pipeline.run_correction).parameters)
    assert "evidence_chain_z_floor_m" not in params
    assert "evidence_chain_ceiling_height_m" not in params
    assert "evidence_chain_level" in params

    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    out_dir = tmp_path / "1_correction"
    # a bare float where a validated level is required -> TypeError
    with pytest.raises(TypeError):
        pipeline.run_correction(
            vector_dir, "{}", out_dir=out_dir, evidence_chain=True,
            evidence_chain_product="p.json", evidence_chain_level=12.34,
        )
    # no level at all -> loud ValueError before the chain runs
    with pytest.raises(ValueError, match="evidence_chain_level"):
        pipeline.run_correction(
            vector_dir, "{}", out_dir=out_dir, evidence_chain=True,
            evidence_chain_product="p.json",
        )


# ── rework §四 #4 / §三 #3: footprint relabel is STRUCTURAL, ⛔ not substring ── #
def test_footprint_relabel_is_from_an_explicit_precheck_only():
    """§四 #4 / §三 #3: ``PER_FLOOR_FOOTPRINT_MISMATCH`` comes ONLY from the
    explicit pre-construction footprint compare.  Every OTHER model-level schema
    error reaching the construction propagates RAW — it is NEVER relabeled as a
    footprint mismatch.  Shown with the reviewer's empty-floor-id case AND a
    second today-reachable error (duplicate id), plus a genuine mismatch."""
    from pydantic import ValidationError

    # (a) reviewer's empty floor id, model_copy'd past re-validation so it
    # reaches the final construction — surfaces RAW, ⛔ not footprint.
    good = _square_floor("F1", [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]])
    empty_id = good.model_copy(
        update={"floors": [good.floors[0].model_copy(update={"id": ""})]}
    )
    ladder1 = derive_floor_ladder(_elevation([2900.0]))
    with pytest.raises(ValidationError) as exc_a:
        assemble_multifloor_geometry(ladder1, [empty_id])
    assert "floor ids must be non-empty" in str(exc_a.value)
    assert not isinstance(exc_a.value, MultiFloorAssemblyError)

    # (b) my own second reachable error: a duplicate floor id — caught by the
    # named DUPLICATE_FLOOR_ID check, ⛔ never PER_FLOOR_FOOTPRINT_MISMATCH.
    ladder2 = derive_floor_ladder(_elevation([2900.0, 3300.0]))
    with pytest.raises(MultiFloorAssemblyError) as exc_b:
        assemble_multifloor_geometry(
            ladder2, [_square_floor("same", _RECT), _square_floor("same", _RECT)]
        )
    assert exc_b.value.code == "DUPLICATE_FLOOR_ID"

    # (c) a GENUINE footprint mismatch IS caught by name (the pre-check).
    square = [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]]
    wide = [[0.0, 0.0], [12.0, 0.0], [12.0, 8.0], [0.0, 8.0]]
    with pytest.raises(MultiFloorAssemblyError) as exc_c:
        assemble_multifloor_geometry(
            ladder2, [_square_floor("g0", square), _square_floor("g1", wide)]
        )
    assert exc_c.value.code == "PER_FLOOR_FOOTPRINT_MISMATCH"


def test_no_loctype_or_substring_footprint_predicate_remains():
    """§四 #4 / §二: the round-1 structural predicate (``loc``/``type`` over all
    model-level value_errors) and any substring-of-``str(exc)`` footprint
    decision are GONE.  ``PER_FLOOR_FOOTPRINT_MISMATCH`` is raised only by the
    explicit pre-check, and the construction is not wrapped in an ``except
    ValidationError`` at all — so no schema error can be mislabeled by SHAPE or
    by TEXT.  A source-level lock that turns 'we removed the predicate' into a
    checkable rule."""
    src = (REPO / "src/agent/correction/multifloor.py").read_text("utf-8")
    assert "_is_footprint_mismatch_error" not in src  # round-1 predicate gone
    assert ".errors()" not in src  # no loc/type inspection of a ValidationError
    assert "except ValidationError" not in src  # construction propagates raw
    # the footprint sentence is not compared as a substring anywhere
    sentence = "must have identical" + " geometry"
    assert sentence not in src


# ── acceptance 7: zero gt contact by the new files ─────────────────────────── #
def test_new_files_never_touch_gt():
    # needles built by concatenation so this scan does not match its OWN
    # source (a bare literal here would be a self-inflicted false positive)
    gt_module = "judge" + ".gt"
    gt_module_slash = "judge" + "/gt"
    gt_loader = "load" + "_gt"
    gt_dir = "case_tests/" + "test_baseline/" + "gt/"
    sources = {
        "multifloor.py": (REPO / "src/agent/correction/multifloor.py").read_text("utf-8"),
        "test_b2": (REPO / "tests/test_b2_multifloor_assembly.py").read_text("utf-8"),
        "pipeline_b2_block": pipeline_b2_source(),
    }
    for name, text in sources.items():
        assert gt_module not in text, name
        assert gt_module_slash not in text, name
        assert gt_loader not in text, name
        assert gt_dir not in text, name
