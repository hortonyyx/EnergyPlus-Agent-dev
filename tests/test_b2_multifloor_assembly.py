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

import hashlib
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


def test_nonpositive_ceiling_is_loud(monkeypatch):
    """The assembly boundary check.  ⭐ Rework-3: the round-2 way of reaching it
    — ``ValidatedFloorLadder((bad,))`` with a hand-built zero-height level — is
    now IMPOSSIBLE one step earlier (the constructor is sealed), so this test
    (a) locks that seal refusal for the same bad input, and (b) still exercises
    the ``NONPOSITIVE_CEILING_HEIGHT`` branch itself by injecting the bad level
    through the derivation core (the sanctioned monkeypatch seam this file
    already uses for ``mf.derive_floor_ladder``)."""
    import src.agent.correction.multifloor as mf
    from src.agent.correction.multifloor import _DerivedFloorLevel

    art = _elevation([2900.0, 3300.0])
    z0 = _claim_at(art, 0.0)
    bad = _DerivedFloorLevel(
        floor_index=0, lower=z0, upper=z0, frozen_docs=_docs(art)
    )
    assert bad.ceiling_height_m == 0.0  # ← non-positive, byte-resolved
    # (a) the forged-carrier route to this check is gone at the TYPE layer
    with pytest.raises(MultiFloorAssemblyError) as seal_exc:
        ValidatedFloorLadder((bad,))
    assert seal_exc.value.code == "LADDER_MINT_SEAL_REQUIRED"
    # (b) the boundary check itself still fires loud on a zero-height level
    monkeypatch.setattr(mf, "_levels_of", lambda art_: (bad,))
    ladder = mf.derive_floor_ladder(art)
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(ladder, [_square_floor("f0", _RECT)])
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


def test_wiring_feeds_the_derived_z_into_the_chain(monkeypatch, tmp_path):
    """Behavioural half of T5 + T1: run_multifloor_correction calls
    run_correction with ``evidence_chain=True`` and the byte-validated level of
    each DERIVED rung — captured here, ⛔ never a caller-declared value.

    The fake chain ALSO files the per-floor source record the REAL chain files
    at source_read (rework BLK-E): the wiring's post-chain re-read of the plan
    products is reconciled against that record, so the fixture materializes
    the products on disk just like production."""
    art = _elevation([2900.0, 3300.0])  # storeys: (0, 2.9), (2.9, 3.3)
    ladder = derive_floor_ladder(art)
    seen: list[dict] = []

    def _fake_run_correction(*args, **kwargs):
        seen.append(kwargs)
        assert kwargs["evidence_chain"] is True
        fid = f"f{len(seen) - 1}"
        _file_chain_source_record({**kwargs, "vector_dir": args[0]})
        return _square_floor(fid, _RECT)

    monkeypatch.setattr(pipeline, "run_correction", _fake_run_correction)
    runs = [
        _materialized_plan_run(tmp_path, "p0"),
        _materialized_plan_run(tmp_path, "p1"),
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
    """§三 #2 — my OWN same-shape attack (round-2 form, replayed under the
    rework-3 seal): hand-forge the sealed carrier from a level whose bounding
    claims had their ``z_m`` ``model_copy``'d to 12.34 / 17.91 (honest
    ``z_ref`` kept).  Two independent walls now stop it: the constructor is
    SEALED (named ``LADDER_MINT_SEAL_REQUIRED``), and even the level itself
    ignores the hand ``z_m`` — z is byte-resolved, so the drift moves nothing."""
    from src.agent.correction.multifloor import _DerivedFloorLevel

    art = _elevation([2900.0, 3300.0])
    lo = _claim_at(art, 0.0).model_copy(update={"z_m": 12.34})   # keep z_ref
    hi = _claim_at(art, 2.9).model_copy(update={"z_m": 17.91})   # keep z_ref
    forged_level = _DerivedFloorLevel(
        floor_index=0, lower=lo, upper=hi, frozen_docs=_docs(art)
    )
    # wall 2 is independent of wall 1: the level reads the frozen bytes, so the
    # hand ``z_m`` never moves z even if a level object is obtained somehow
    assert forged_level.z_floor_m == 0.0
    assert round(forged_level.ceiling_height_m, 6) == 2.9
    assert forged_level.z_floor_m != 12.34
    # wall 1: the forged level cannot even be placed into a carrier
    with pytest.raises(MultiFloorAssemblyError) as exc:
        ValidatedFloorLadder((forged_level,))
    assert exc.value.code == "LADDER_MINT_SEAL_REQUIRED"


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


# ── rework-3 §二: the carrier ITSELF cannot be forged (round-3's bypass) ───── #
def _drifted_artifact(art, z_lo: float, z_hi: float):
    """A REAL sealed artifact whose two lowest claims' ``z_m`` drifted (honest
    ``z_ref`` kept, bundle re-finalized) — built exactly like the round-2/3
    reviewers built theirs, from PUBLIC API only."""
    from src.agent.correction.evidence_contract import (
        CorrectionEvidenceBundleArtifactV1,
        finalize_bundle,
    )

    claims = list(art.bundle.floor_level_claims)
    ordered = sorted(claims, key=lambda c: c.z_m)
    drift = {ordered[0].structure_line_id: z_lo, ordered[1].structure_line_id: z_hi}
    drifted = [
        c.model_copy(update={"z_m": drift[c.structure_line_id]})
        if c.structure_line_id in drift else c
        for c in claims
    ]
    bundle = finalize_bundle(
        art.bundle.model_copy(update={"floor_level_claims": drifted})
    )
    return CorrectionEvidenceBundleArtifactV1(
        bundle=bundle, frozen_sources=art.frozen_sources
    )


def test_reviewer_round3_replay_public_constructor_is_sealed():
    """§二 #1 as a permanent lock — the reviewer's EXACT round-3 shape: a
    hand-filled ``SimpleNamespace`` level into the PUBLIC constructor, then
    assembly.  It now dies AT THE CONSTRUCTOR with the named
    ``LADDER_MINT_SEAL_REQUIRED``; assembly is never reached, and no evidence
    artifact / frozen bytes / byte gate were ever involved."""
    from types import SimpleNamespace

    hand_level = SimpleNamespace(
        floor_index=0, z_floor_m=12.34, ceiling_height_m=5.57
    )
    with pytest.raises(MultiFloorAssemblyError) as exc:
        ValidatedFloorLadder((hand_level,))
    assert exc.value.code == "LADDER_MINT_SEAL_REQUIRED"
    with pytest.raises(MultiFloorAssemblyError) as sealed:
        assemble_multifloor_geometry(
            ValidatedFloorLadder((hand_level,)),  # ← must not mint, must red
            [_square_floor("f0", _RECT)],
        )
    assert sealed.value.code == "LADDER_MINT_SEAL_REQUIRED"


def test_posthoc_artifact_swap_is_gated_at_consumption():
    """§二 #2 path A ("先合法拿到一个真载体再替换它的内容"): take an HONEST
    ladder, swap its only field post-hoc with ``object.__setattr__`` (bypassing
    the frozen dataclass guard) to a REAL-but-drifted sealed artifact — the
    assembled z is still decided by the re-run gate: a named
    ``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`` red, ⛔ never the hand z."""
    from src.agent.correction.evidence_contract import EvidenceContractError

    art = _elevation([2900.0, 3300.0])
    ladder = derive_floor_ladder(art)
    object.__setattr__(ladder, "_artifact", _drifted_artifact(art, 12.34, 17.91))
    with pytest.raises(EvidenceContractError) as exc:
        assemble_multifloor_geometry(ladder, [_square_floor("f0", _RECT)])
    assert exc.value.code == "FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE"


def test_object_new_shell_cannot_assemble_a_hand_z():
    """§二 #2 path B: ``object.__new__`` bypasses every ``__init__`` (which no
    constructor-side seal can stop), so the shell is the strongest forge left.
    Three sub-shapes: a duck-typed artifact with hand z (refused by name), a
    REAL drifted sealed artifact (the re-run gate refuses it), and a bare
    attribute-less shell (refused by name).  None can assemble a value that was
    merely SET on an instance."""
    from types import SimpleNamespace

    from src.agent.correction.evidence_contract import EvidenceContractError

    # (a) duck-typed artifact carrying hand-authored content — refused BY NAME
    duck = SimpleNamespace(
        bundle=SimpleNamespace(floor_level_claims=()),
        frozen_sources=[
            SimpleNamespace(
                artifact=SimpleNamespace(input_id="x"),
                raw_bytes=b'{"structure_lines": []}',
            )
        ],
    )
    shell = object.__new__(ValidatedFloorLadder)
    object.__setattr__(shell, "_artifact", duck)
    with pytest.raises(MultiFloorAssemblyError) as duck_exc:
        assemble_multifloor_geometry(shell, [_square_floor("f0", _RECT)])
    assert duck_exc.value.code == "LADDER_CARRIER_CORRUPT"

    # (b) a REAL sealed artifact with drifted claims — the re-run gate refuses
    art = _elevation([2900.0, 3300.0])
    shell2 = object.__new__(ValidatedFloorLadder)
    object.__setattr__(shell2, "_artifact", _drifted_artifact(art, 12.34, 17.91))
    with pytest.raises(EvidenceContractError) as gate_exc:
        assemble_multifloor_geometry(shell2, [_square_floor("f0", _RECT)])
    assert gate_exc.value.code == "FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE"

    # (c) an attribute-less shell (nothing set at all) — refused by name too
    with pytest.raises(MultiFloorAssemblyError) as bare_exc:
        assemble_multifloor_geometry(object.__new__(ValidatedFloorLadder), [])
    assert bare_exc.value.code == "LADDER_CARRIER_CORRUPT"


def test_subclassing_the_carrier_is_refused_at_class_creation():
    """§二 #2 path C: an ``isinstance``-passing subclass with an overridden
    constructor cannot even be DEFINED — ``__init_subclass__`` raises the named
    ``LADDER_SEALED_NO_SUBCLASS`` at class-creation time."""
    with pytest.raises(MultiFloorAssemblyError) as exc:
        class FakeLadder(ValidatedFloorLadder):
            def __init__(self, levels):
                object.__setattr__(self, "_levels", levels)

    assert exc.value.code == "LADDER_SEALED_NO_SUBCLASS"


def test_dataclasses_replace_cannot_rebuild_the_carrier():
    """§二 #2 path D: ``dataclasses.replace`` cannot mint a modified carrier.
    replace rebuilds init kwargs from FIELD names (the decorator's init=False
    only suppresses GENERATING ``__init__`` — the field's init flag stays
    True), so both shapes re-enter the sealed constructor and die on the NAMED
    seal error — with the drifted artifact swapped in, and bare."""
    import dataclasses

    art = _elevation([2900.0, 3300.0])
    ladder = derive_floor_ladder(art)
    # replacing the artifact field: the seal refuses the mint
    with pytest.raises(MultiFloorAssemblyError) as swapped:
        dataclasses.replace(ladder, _artifact=_drifted_artifact(art, 12.34, 17.91))
    assert swapped.value.code == "LADDER_MINT_SEAL_REQUIRED"
    # a bare replace (no changes) re-enters the same sealed constructor
    with pytest.raises(MultiFloorAssemblyError) as exc:
        dataclasses.replace(ladder)
    assert exc.value.code == "LADDER_MINT_SEAL_REQUIRED"


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


# ── W-1 rework BLK-A (2026-09-07): the channel-split debt is FILED, not narrated ── #

def _snap_declared_plan_doc() -> dict:
    """The minimal plan product whose OWN declarations the snap tolerance
    derives from (``read_plan_calibration_declaration`` reads exactly these):
    per-axis calibration chains with a self-report that matches the recomputed
    max residual, plus positive wall-thickness callouts.  W#6 additionally
    has the reconciliation read the DECLARED exterior frame, so the chains'
    declared overall extents are here too (matching the 6×4 square below)."""
    return {
        "observations": {
            "calibration": {
                **{
                    axis: {
                        "mm_per_px": 3.0,
                        "residual_px": [0.5, -0.25, 0.125],
                        "max_abs_residual_px": 0.5,
                    }
                    for axis in ("x", "y")
                },
                "x": {
                    "mm_per_px": 3.0,
                    "residual_px": [0.5, -0.25, 0.125],
                    "max_abs_residual_px": 0.5,
                    "overall_mm": 6000.0,
                },
                "y": {
                    "mm_per_px": 3.0,
                    "residual_px": [0.5, -0.25, 0.125],
                    "max_abs_residual_px": 0.5,
                    "overall_mm": 4000.0,
                },
            }
        },
        "declarations": {"thickness_callouts_mm": [200.0]},
    }


def _materialized_plan_run(root: Path, name: str, **overrides):
    """A plan run whose product REALLY exists on disk (the wiring re-reads it
    after the chains to derive the snap tolerance)."""
    vector_dir = root / "v0"
    vector_dir.mkdir(parents=True, exist_ok=True)
    (vector_dir / f"{name}.json").write_text(
        json.dumps(_snap_declared_plan_doc()), encoding="utf-8"
    )
    fields = {
        "vector_dir": vector_dir,
        "product_filename": f"{name}.json",
        "out_dir": root / "out" / name,
    }
    fields.update(overrides)
    return pipeline.MultiFloorPlanRun(**fields)


def _file_chain_source_record(chain_kwargs: dict) -> None:
    """What the REAL chain does at source_read (rework BLK-E): file the
    per-floor record of the bytes it consumed, keyed by the sha256 of the
    product file as it stands AT CHAIN TIME.  W#6 additionally has the
    wiring consume the chain's own filed cut lines (post-exterior-frame-
    snap) and final compilation, so a faithful fake chain files those too:
    a 6×4 square of axis-snapped walls (t=200 ⇒ axis frame [0.1, 5.9] ×
    [0.1, 3.9]) whose projection is the square these tests' geometries
    have always described."""
    out_dir = Path(chain_kwargs["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = (
        Path(chain_kwargs["vector_dir"]) / chain_kwargs["evidence_chain_product"]
    ).read_bytes()
    (out_dir / "chain_source_record.json").write_text(
        json.dumps(
            {
                "schema": "chain_source_record_v1",
                "product_filename": chain_kwargs["evidence_chain_product"],
                "source_bytes_sha256": hashlib.sha256(raw).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    level = chain_kwargs.get("evidence_chain_level")
    z_floor = getattr(level, "z_floor_m", 0.0)
    ceiling = getattr(level, "ceiling_height_m", 3.0)
    floor_ref = Path(chain_kwargs["evidence_chain_product"]).stem
    compilation_hash = hashlib.sha256(b"w6-mock-compilation").hexdigest()
    walls = [
        {"axis": "y", "pos_m": 0.1, "along": [0.1, 3.9]},
        {"axis": "y", "pos_m": 5.9, "along": [0.1, 3.9]},
        {"axis": "x", "pos_m": 0.1, "along": [0.1, 5.9]},
        {"axis": "x", "pos_m": 3.9, "along": [0.1, 5.9]},
    ]
    (out_dir / "cut_lines.json").write_text(
        json.dumps(
            {
                "schema": "cut_lines_v1",
                "lines": [
                    {
                        "axis": w["axis"],
                        "pos_m": w["pos_m"],
                        "along_lo_m": w["along"][0],
                        "along_hi_m": w["along"][1],
                        "half_thickness_m": 0.1,
                        "kind": "wall",
                        "origin_id": f"{floor_ref}-{index}",
                    }
                    for index, w in enumerate(walls)
                ],
                "project": {
                    "resolution_m": 0.0,
                    "resolution_source": "mock chain (test fixture)",
                    "source_resolved_sha256": compilation_hash,
                    "floor_id": floor_ref,
                    "floor_name": floor_ref,
                    "z_floor_m": z_floor,
                    "ceiling_height_m": ceiling,
                    "view_id": floor_ref,
                    "floor_ref": floor_ref,
                    "origin_label": floor_ref,
                },
            }
        ),
        encoding="utf-8",
    )
    (out_dir / "evidence_chain_compilation.json").write_text(
        json.dumps(
            {
                "schema_version": "wall_compilation_v1",
                "profile": "exploratory",
                "bundle_content_sha256": "0" * 64,
                "walls": [],
                "open_items": [],
                "completion": "complete",
                "content_sha256": compilation_hash,
            }
        ),
        encoding="utf-8",
    )


def test_new_leg_files_the_channel_split_debt(monkeypatch, tmp_path):
    """Lock ① (rework BLK-A): walking the new leg FILES the window
    channel-split debt — the identifier exists as a filed JSON artifact on
    disk, ⛔ not only inside docstrings.  Under the default exploratory chain
    profile it is a FLAG, and the walk completes."""
    made: list[str] = []

    def _fake_chain(*args, **kwargs):
        made.append(f"f{len(made)}")
        _file_chain_source_record({**kwargs, "vector_dir": args[0]})
        return _square_floor(made[-1], _RECT)

    monkeypatch.setattr(pipeline, "run_correction", _fake_chain)
    art = _elevation([2900.0, 3300.0])
    debt_path = tmp_path / "1_correction" / "evidence_debt.json"
    runs = [
        _materialized_plan_run(tmp_path, "p0"),
        _materialized_plan_run(tmp_path, "p1"),
    ]
    pipeline.run_multifloor_correction(art, runs, evidence_debt_path=debt_path)
    filed = json.loads(debt_path.read_text(encoding="utf-8"))
    items = [d for d in filed["debts"]
             if d["check_id"] == "WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER"]
    assert items, "the channel-split debt must be FILED on the new leg"
    assert items[0]["disposition"] == "flag"
    assert items[0]["evidence"]["evidence_chain_profile"] == "exploratory"
    assert filed["source_stage"] == "1_correction"


def test_strict_profile_blocks_the_channel_split_after_filing(monkeypatch, tmp_path):
    """Lock ② (rework BLK-A): under a STRICT chain profile the channel-split
    debt BLOCKS — and it blocks (a) AFTER the debt is filed, so the refusal
    is auditable on disk, and (b) BEFORE any chain runs, so a strict refusal
    costs no chain budget (the fake run_correction must never fire)."""
    fired: list[dict] = []

    def _must_not_fire(*args, **kwargs):
        fired.append(kwargs)
        raise AssertionError("a strict refusal must precede every chain run")

    monkeypatch.setattr(pipeline, "run_correction", _must_not_fire)
    art = _elevation([2900.0, 3300.0])
    debt_path = tmp_path / "evidence_debt.json"
    runs = [
        _materialized_plan_run(tmp_path, "p0", profile="strict"),
        _materialized_plan_run(tmp_path, "p1", profile="strict"),
    ]
    with pytest.raises(MultiFloorAssemblyError) as exc:
        pipeline.run_multifloor_correction(art, runs, evidence_debt_path=debt_path)
    assert exc.value.code == "WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER"
    assert not fired
    # the block itself is auditable: the debt hit the disk BEFORE the raise
    filed = json.loads(debt_path.read_text(encoding="utf-8"))
    item = next(d for d in filed["debts"]
                if d["check_id"] == "WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER")
    assert item["disposition"] == "block"
    assert item["evidence"]["evidence_chain_profile"] == "strict"


def test_mixed_plan_run_profiles_refuse_loudly(tmp_path):
    """A leg whose floors would run under DIFFERENT chain profiles has no
    single filed account — loud ``PLAN_RUN_PROFILE_MIXED``, ⛔ not a silent
    pick of either word."""
    art = _elevation([2900.0, 3300.0])
    runs = [
        _materialized_plan_run(tmp_path, "p0", profile="exploratory"),
        _materialized_plan_run(tmp_path, "p1", profile="strict"),
    ]
    with pytest.raises(MultiFloorAssemblyError) as exc:
        pipeline.run_multifloor_correction(art, runs)
    assert exc.value.code == "PLAN_RUN_PROFILE_MIXED"


# ── W-1 rework BLK-E (2026-09-07): the tolerance derives from the chain's bytes ── #

def test_reconciled_read_passes_and_derives(tmp_path, monkeypatch):
    """Sanity half of the BLK-E lock: when the on-disk product still IS what
    the chain consumed (hashes agree), the reconciliation is invisible — the
    walk completes and the tolerance derivation gets its docs.  (Without this
    green half, the drift lock below could be red for the wrong reason.)"""
    art = _elevation([2900.0])
    run = _materialized_plan_run(tmp_path, "p0")
    _file_chain_source_record(
        {
            "out_dir": run.out_dir,
            "vector_dir": run.vector_dir,
            "evidence_chain_product": run.product_filename,
        }
    )
    monkeypatch.setattr(
        pipeline, "run_correction", lambda *a, **k: _square_floor("f0", _RECT)
    )
    geom = pipeline.run_multifloor_correction(art, [run])
    # W#6: the walk now re-partitions from the chain's OWN filed cut lines,
    # so the floor id is the sidecar's floor_id (= the chain's floor_ref) —
    # the same thing the real chain's geometry always carried.
    assert [f.id for f in geom.floors] == ["p0"]


def test_drifted_product_bytes_are_a_named_red(tmp_path, monkeypatch):
    """Lock ① (rework BLK-E): a product file that changed between the chain's
    freeze and the wiring's re-read is a NAMED red — the snap tolerance must
    derive from the bytes the chain actually consumed, ⛔ never from an
    unverified second read."""
    art = _elevation([2900.0])
    run = _materialized_plan_run(tmp_path, "p0")

    def _chain_then_swap(*args, **kwargs):
        _file_chain_source_record({**kwargs, "vector_dir": args[0]})
        # the bytes mutate AFTER the chain froze them — exactly the window
        # BLK-E closes
        (run.vector_dir / run.product_filename).write_text(
            json.dumps(_snap_declared_plan_doc(), indent=1), encoding="utf-8"
        )
        return _square_floor("f0", _RECT)

    monkeypatch.setattr(pipeline, "run_correction", _chain_then_swap)
    with pytest.raises(MultiFloorAssemblyError) as exc:
        pipeline.run_multifloor_correction(art, [run])
    assert exc.value.code == "PLAN_PRODUCT_BYTES_DRIFTED_FROM_CHAIN"
    assert exc.value.detail["run"] == "p0.json"


def test_missing_source_record_is_a_named_red(tmp_path, monkeypatch):
    """A chain run that filed NO record of its consumed bytes leaves the
    re-read unanchorable — a named ``CHAIN_SOURCE_RECORD_MISSING`` red, ⛔ not
    a silent unverified derive."""
    art = _elevation([2900.0])
    run = _materialized_plan_run(tmp_path, "p0")
    monkeypatch.setattr(
        pipeline, "run_correction", lambda *a, **k: _square_floor("f0", _RECT)
    )
    with pytest.raises(MultiFloorAssemblyError) as exc:
        pipeline.run_multifloor_correction(art, [run])
    assert exc.value.code == "CHAIN_SOURCE_RECORD_MISSING"


def test_chain_files_the_source_record_at_source_read(tmp_path):
    """The ANCHOR half: the chain itself files ``chain_source_record.json``
    per floor at the source_read freeze — before adapt, before the loop — so
    even a chain that dies at the next link leaves the record of what it
    consumed.  (A deliberately unparseable product: the chain must raise at
    adapt, and STILL have filed the record.)"""
    from src.agent.correction.evidence_contract import EvidenceContractError

    vector_dir = tmp_path / "v0"
    vector_dir.mkdir()
    (vector_dir / "p0.json").write_bytes(b"not-json-at-all")
    out_dir = tmp_path / "out" / "p0"
    with pytest.raises(Exception):
        pipeline.run_correction_evidence_chain(
            vector_dir, "p0.json", out_dir=out_dir
        )
    record = json.loads(
        (out_dir / "chain_source_record.json").read_text(encoding="utf-8")
    )
    assert record["source_bytes_sha256"] == hashlib.sha256(
        b"not-json-at-all"
    ).hexdigest()
    # ⚠️ the run-level ROUTE record is only written when the chain runs to its
    # end — this chain died at adapt, so the per-floor sidecar above is the
    # ONLY surviving record, which is exactly why the reconciliation anchor
    # is the sidecar, ⛔ not the route (route-key lock lives where a chain
    # completes: test_o22m7's route-direction tests).
