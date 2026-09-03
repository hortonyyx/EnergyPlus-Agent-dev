"""B2 — multi-floor assembly (dispatch 2026-09-03ai).

WHAT THIS FILE LOCKS (the §六 acceptance table, as RULES, ⛔ not as transcripts
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

⚠️ Everything here is SYNTHETIC (the B3 factory's three-storey / mixed-height
fixture), so any sm25 constant smuggled into the production code breaks these
tests — and it keeps the whole file gt-free.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

import src.agent.pipeline as pipeline
from src.agent.correction.evidence_adapters import (
    adapt_as_drawn_elevation,
    adapt_as_drawn_plan,
)
from src.agent.correction.evidence_contract import resolve_json_pointer
from src.agent.correction.multifloor import (
    DerivedFloorLevel,
    MultiFloorAssemblyError,
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
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    assert len(levels) == 3
    for level in levels:
        # z_floor's own byte
        assert level.z_floor_m == resolve_json_pointer(
            doc, level.z_floor_ref.json_pointer
        )
        # ceiling_height is a DERIVED difference — BOTH operands trace to bytes
        top = resolve_json_pointer(doc, level.z_top_ref.json_pointer)
        assert level.ceiling_height_m == pytest.approx(
            top - level.z_floor_m
        )
        # the pointer is anchored into THIS artifact's frozen source
        assert level.z_floor_ref.source_output_sha256 == (
            art.frozen_sources[0].artifact.source_output_sha256
        )


def test_derived_heights_are_the_input_storey_heights():
    art = _elevation([2900.0, 3300.0, 4200.0])
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    assert [round(l.z_floor_m, 6) for l in levels] == [0.0, 2.9, 6.2]
    assert [round(l.ceiling_height_m, 6) for l in levels] == [2.9, 3.3, 4.2]


# ── acceptance 3: two-storey assembly passes the EXISTING continuity check ─── #
def test_two_storey_assembles_and_passes_pipeline_zstack_check():
    art = _elevation([2900.0, 3300.0])  # 3 rungs -> 2 storeys
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    assert len(levels) == 2
    geom = assemble_multifloor_geometry(
        levels, [_square_floor("f0", _RECT), _square_floor("f1", _RECT)]
    )
    assert len(geom.floors) == 2
    assert [(round(f.z_floor, 6), round(f.ceiling_height, 6)) for f in geom.floors] == [
        (0.0, 2.9),
        (2.9, 3.3),
    ]
    # ⭐ T3: pass pipeline.py:661-668's ACTUAL check, not a private copy. A
    # clean assembly has no issue at all (and specifically no z-stack break).
    issues = pipeline.correction_draw_issues(geom, 0)
    assert issues == [], issues
    assert not any("z-stack" in msg for msg in issues)


# ── acceptance 4: storey count / heights come from the DATA ────────────────── #
def test_three_storey_mixed_heights_assemble_three_floors():
    art = _elevation([2900.0, 3300.0, 4200.0])  # 4 rungs -> 3 storeys
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    geom = assemble_multifloor_geometry(
        levels, [_square_floor(f"f{i}", _RECT) for i in range(3)]
    )
    assert len(geom.floors) == 3
    assert [round(f.ceiling_height, 6) for f in geom.floors] == [2.9, 3.3, 4.2]
    assert pipeline.correction_draw_issues(geom, 0) == []


def test_reshaped_ladder_yields_a_new_floor_count():
    """A two-storey ladder gives two floors from the SAME code — the count is
    not a constant.  (A code that hardcoded 3 storeys fails here.)"""
    art = _elevation([3050.0, 2750.0])
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    geom = assemble_multifloor_geometry(
        levels, [_square_floor("f0", _RECT), _square_floor("f1", _RECT)]
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
    art = _elevation([2900.0, 3300.0, 4200.0])  # 3 storeys
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(
            levels, [_square_floor("f0", _RECT), _square_floor("f1", _RECT)]
        )  # only 2 plan products for 3 storeys
    assert exc.value.code == "FLOOR_PLAN_COUNT_MISMATCH"
    assert exc.value.detail["n_storeys_from_ladder"] == 3
    assert exc.value.detail["n_plan_products"] == 2


def test_non_ascending_ladder_is_loud():
    """Two floor lines at the same z: the ladder does not strictly ascend
    ("标高不单调"), which is exactly the degenerate zero-height case."""
    art = _elevation([2900.0, 3300.0])
    claims = list(art.bundle.floor_level_claims)
    # forge a duplicate rung by re-pointing one claim's z onto another's z
    lo = min(claims, key=lambda c: c.z_m)
    dup = claims[-1].model_copy(update={"z_m": lo.z_m})
    with pytest.raises(MultiFloorAssemblyError) as exc:
        derive_floor_ladder([*claims, dup])
    assert exc.value.code == "FLOOR_LADDER_NOT_ASCENDING"
    assert exc.value.detail["rise_m"] == 0.0


def test_degenerate_ladder_is_loud():
    art = _elevation([2900.0, 3300.0])
    one = [min(art.bundle.floor_level_claims, key=lambda c: c.z_m)]
    with pytest.raises(MultiFloorAssemblyError) as exc:
        derive_floor_ladder(one)
    assert exc.value.code == "FLOOR_LADDER_DEGENERATE"


def test_nonpositive_ceiling_is_loud():
    """The assembly boundary check even if a caller hand-built a level that
    bypassed ``derive_floor_ladder`` with a non-physical height."""
    from src.agent.correction.evidence_contract import ArtifactPointerV1

    ref = ArtifactPointerV1(
        input_id="x",
        source_contract_id="c",
        source_output_sha256="0" * 64,
        json_pointer="/structure_lines/0/pos_m",
    )
    bad = DerivedFloorLevel(
        floor_index=0,
        z_floor_m=0.0,
        ceiling_height_m=0.0,  # ← non-positive
        z_floor_claim_id="L0",
        z_floor_ref=ref,
        z_top_claim_id="L1",
        z_top_ref=ref,
    )
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry([bad], [_square_floor("f0", _RECT)])
    assert exc.value.code == "NONPOSITIVE_CEILING_HEIGHT"


def test_per_floor_footprint_mismatch_is_loud():
    """Invariant #6: assembly is common-footprint only; different per-floor
    footprints (setback) are refused by name, ⛔ not silently allowed."""
    art = _elevation([2900.0, 3300.0])
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    other = [[0.0, 0.0], [7.0, 0.0], [7.0, 4.0], [0.0, 4.0]]  # wider
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(
            levels, [_square_floor("f0", _RECT), _square_floor("f1", other)]
        )
    assert exc.value.code == "PER_FLOOR_FOOTPRINT_MISMATCH"


def test_duplicate_floor_id_is_loud():
    art = _elevation([2900.0, 3300.0])
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
    with pytest.raises(MultiFloorAssemblyError) as exc:
        assemble_multifloor_geometry(
            levels, [_square_floor("dup", _RECT), _square_floor("dup", _RECT)]
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
    run_correction with ``evidence_chain=True`` and the z of each DERIVED
    rung — captured here, ⛔ never a caller-declared value."""
    art = _elevation([2900.0, 3300.0])  # storeys: (0, 2.9), (2.9, 3.3)
    levels = derive_floor_ladder(art.bundle.floor_level_claims)
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
    geom = pipeline.run_multifloor_correction(art.bundle.floor_level_claims, runs)
    fed = [
        (k["evidence_chain_z_floor_m"], k["evidence_chain_ceiling_height_m"])
        for k in seen
    ]
    assert fed == [(l.z_floor_m, l.ceiling_height_m) for l in levels]
    assert [(f.z_floor, f.ceiling_height) for f in geom.floors] == fed


def test_neutered_derivation_fails_loud_never_falls_back(monkeypatch):
    """Acceptance #2: remove the derivation (it returns nothing) and the new
    path must fail LOUDLY — ⛔ it must not silently fall back to a hand-filled
    z (there is none to fall back to)."""
    import src.agent.correction.multifloor as mf

    monkeypatch.setattr(pipeline, "run_correction", lambda *a, **k: _square_floor("x", _RECT))
    monkeypatch.setattr(mf, "derive_floor_ladder", lambda claims: ())
    # the pipeline function imports derive_floor_ladder locally from mf, so the
    # patch on the module reaches it
    art = _elevation([2900.0, 3300.0])
    runs = [pipeline.MultiFloorPlanRun(Path("v0"), "p0.json", Path("o0"))]
    with pytest.raises(MultiFloorAssemblyError) as exc:
        pipeline.run_multifloor_correction(art.bundle.floor_level_claims, runs)
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
    geom = pipeline.run_multifloor_correction(
        art.bundle.floor_level_claims, [run]
    )
    assert len(geom.floors) == 1
    assert (round(geom.floors[0].z_floor, 6), round(geom.floors[0].ceiling_height, 6)) == (
        0.0,
        2.9,
    )
    assert geom.floors[0].cells, "the real product must yield cells"


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
