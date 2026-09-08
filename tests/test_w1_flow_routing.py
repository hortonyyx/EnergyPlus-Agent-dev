"""W-1 T3 rework S4 — the flow entry routes 1_correction by the classifier.

WHAT THIS FILE LOCKS (dispatch 2026-09-07p S4 / wip-review BLK-C):

1. a full-legacy product set routes to the legacy leg (the existing
   behavior, byte-identical);
2. a full as_drawn product set (plan products at plan slots, elevation
   products at elevation slots) routes to the new leg AND the new-leg draw
   runs end-to-end through the flow's standard (result, report) shape —
   gate① zero blocking;
3. every bad shape is LOUD (ratified T2-⑦ table): a legacy/as_drawn mix, an
   as_drawn product at the wrong slot, as_drawn plans with ZERO elevations —
   ⛔ never a silent fall back to the legacy leg;
4. the chain-profile translation: permissive RunProfiles ride the chain's
   "exploratory"; the strict side rides "strict" (where the S1 debt blocks
   by ratified design).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "tool_scripts"))

from run_stage import (  # noqa: E402
    _draw_correction_as_drawn,
    _make_policy,
    _w1_route_correction,
)
from src.agent.correction.schema import CorrectedGeometryV3  # noqa: E402

_AS_DRAWN_OUT = (
    REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_LEGACY_RUN = REPO / "case_tests/e2e_tests/sm25-L_anchor/run_t1_probe2"
_MANIFEST_SRC = _LEGACY_RUN / "_run" / "view_manifest.json"

# manifest input_id -> as_drawn product file in the 08-23 prototype dir
_AS_DRAWN_PRODUCTS = {
    "1f_view": "sm25_1f_v2.json",
    "2f_view": "sm25_2f_v2.json",
    "East_view": "sm25_east_as_drawn.json",
    "North_view": "sm25_north_as_drawn.json",
    "South_view": "sm25_south_as_drawn.json",
    "West_view": "sm25_west_as_drawn.json",
}


def _stage_as_drawn_run(tmp_path: Path, *, drop_elevations: bool = False) -> Path:
    """A run dir whose frozen manifest and 0_reading stage hold the as_drawn
    products under their manifest expected_output_id names."""
    run_dir = tmp_path / "run_x"
    rdir = run_dir / "0_reading"
    rdir.mkdir(parents=True)
    (run_dir / "_run").mkdir(parents=True)
    (run_dir / "_run" / "view_manifest.json").write_bytes(_MANIFEST_SRC.read_bytes())
    for input_id, name in _AS_DRAWN_PRODUCTS.items():
        if drop_elevations and input_id.endswith(("East_view", "North_view", "South_view", "West_view")):
            continue
        (rdir / f"{input_id}.json").write_bytes(
            (_AS_DRAWN_OUT / name).read_bytes()
        )
    return run_dir


def test_legacy_product_set_routes_to_the_legacy_leg():
    assert _w1_route_correction(
        _LEGACY_RUN / "0_reading", _LEGACY_RUN
    ) == "legacy"


def test_as_drawn_product_set_routes_to_the_new_leg(tmp_path):
    run_dir = _stage_as_drawn_run(tmp_path)
    assert _w1_route_correction(run_dir / "0_reading", run_dir) == "as_drawn"


def test_no_manifest_run_keeps_its_existing_legacy_leg(tmp_path):
    run_dir = _stage_as_drawn_run(tmp_path)
    (run_dir / "_run" / "view_manifest.json").unlink()
    assert _w1_route_correction(run_dir / "0_reading", run_dir) == "legacy"


def test_mixed_contracts_refuse_loudly(tmp_path):
    run_dir = _stage_as_drawn_run(tmp_path)
    # swap ONE elevation slot back to a legacy reading view
    legacy_src = _LEGACY_RUN / "0_reading" / "East_view.json"
    (run_dir / "0_reading" / "East_view.json").write_bytes(legacy_src.read_bytes())
    with pytest.raises(SystemExit) as exc:
        _w1_route_correction(run_dir / "0_reading", run_dir)
    assert "CORRECTION_MIXED_CONTRACTS" in str(exc.value)


def test_wrong_slot_refuses_loudly(tmp_path):
    run_dir = _stage_as_drawn_run(tmp_path)
    # an as_drawn PLAN product parked at an elevation slot
    (run_dir / "0_reading" / "East_view.json").write_bytes(
        (_AS_DRAWN_OUT / "sm25_1f_v2.json").read_bytes()
    )
    with pytest.raises(SystemExit) as exc:
        _w1_route_correction(run_dir / "0_reading", run_dir)
    assert "CORRECTION_MIXED_CONTRACTS" in str(exc.value)


def test_zero_elevations_refuse_loudly(tmp_path):
    """as_drawn plans with ZERO as_drawn elevations — the ratified table's
    ELEVATION_EVIDENCE_MISSING shape (the elevation slots hold LEGACY
    products, i.e. genuinely no as_drawn ladder source)."""
    run_dir = _stage_as_drawn_run(tmp_path)
    for view in ("East_view", "North_view", "South_view", "West_view"):
        (run_dir / "0_reading" / f"{view}.json").write_bytes(
            (_LEGACY_RUN / "0_reading" / f"{view}.json").read_bytes()
        )
    with pytest.raises(SystemExit) as exc:
        _w1_route_correction(run_dir / "0_reading", run_dir)
    assert "ELEVATION_EVIDENCE_MISSING" in str(exc.value)


def _square_two_storey() -> CorrectedGeometryV3:
    """assembled through the REAL assemble_multifloor_geometry (z re-stamped
    from the derived ladder) — a raw hand-z geometry would false-red the
    z-stack invariant exactly like a broken chain would."""
    from src.agent.correction.multifloor import (
        assemble_multifloor_geometry,
        derive_floor_ladder,
    )

    ladder = derive_floor_ladder(_east_evidence())
    rect = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]
    floors = []
    for fid in ("1f", "2f"):
        floors.append({
            "id": fid, "name": fid, "z_floor": 999.0,
            "ceiling_height": 999.0,
            "footprint": {"vertices": rect},
            "cells": [{
                "id": f"{fid}-c0", "x": [0.0, 6.0], "y": [0.0, 4.0],
                "polygon": rect,
            }],
        })
    raw = CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[0.0, 6.0],
        footprint_y=[0.0, 4.0],
        floors=floors,
        windows=[],
        facade_segments=[],
    )
    single = [
        CorrectedGeometryV3(
            schema_version="3",
            footprint_x=[0.0, 6.0],
            footprint_y=[0.0, 4.0],
            floors=[floor],
            windows=[],
            facade_segments=[],
        )
        for floor in raw.floors
    ]
    return assemble_multifloor_geometry(ladder, single)


def _fixed_responses(rdir: Path, product_filename: str):
    """The deterministic model beat (the ``test_w3_chain_replay_lock`` shape):
    round 0 selects every open item's FIRST candidate, round 1 accepts —
    ⛔ zero billed provider calls."""
    from src.agent.correction.decision_executor import (
        FixedDecisionV1,
        build_decision_packet,
        compile_wall_ir,
        decision_hash,
    )
    from src.agent.correction.decision_schema import (
        CorrectionDecisionResponseV1,
        ItemDecisionV1,
    )
    from src.agent.correction.evidence_adapters import adapt_as_drawn_plan

    stem = Path(product_filename).stem
    raw = (rdir / product_filename).read_bytes()
    artifact = adapt_as_drawn_plan(
        raw, input_id=stem, floor_ref=stem.removesuffix("_view"), view_type="plan"
    )
    packet0 = build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"), bundle=artifact, round_index=0
    )
    picks = tuple(
        (item.item_id, item.candidates[0].candidate_id)
        for item in packet0.open_items
    )
    select = CorrectionDecisionResponseV1(
        packet_hash=packet0.packet_hash,
        item_decisions=tuple(
            ItemDecisionV1(
                item_id=item_id,
                action="select_candidate",
                candidate_id=candidate_id,
                reason_code="WIRED_LOCK",
            )
            for item_id, candidate_id in picks
        ),
        whole_building_review={"verdict": "accept"},
    )
    packet1 = build_decision_packet(
        compile_wall_ir(
            artifact,
            profile="exploratory",
            decisions=tuple(
                FixedDecisionV1(item_id=i, candidate_id=c) for i, c in picks
            ),
        ),
        bundle=artifact,
        round_index=1,
        previous_decision_hashes=(decision_hash(select),),
    )
    accept = CorrectionDecisionResponseV1(
        packet_hash=packet1.packet_hash,
        whole_building_review={"verdict": "accept"},
    )
    return [select, accept]


def test_new_leg_draw_runs_through_the_flow_shape(tmp_path, monkeypatch):
    """The routed flow draw is LIVE and runs the REAL chain: window
    population (31 windows — the ⛔ windows=0 false-green trap) →
    finalize → gate① zero blocking, in the standard (result, report)
    shape the StageRunner archives.

    The model beat is the ONLY thing replaced: ``run_correction`` is
    wrapped to inject the deterministic fixed-responses decision (the
    production-supported beat), so run_multifloor_correction, the
    population, the marker, the provenance carrier and the finalize all
    run for real.  (The old shape mocked mfc to return a synthetic
    6×4 two-storey box against the REAL sm25 window sources — legal while
    the leg produced zero windows, structurally incompatible once
    population went live: every opening fell outside the box and the
    resolver refused, by design.)
    """
    import src.agent.pipeline as pipeline

    real_run_correction = pipeline.run_correction

    def _deterministic_run_correction(vector_dir, payload, **kwargs):
        if (
            kwargs.get("evidence_chain")
            and kwargs.get("evidence_chain_fixed_responses") is None
        ):
            kwargs["evidence_chain_fixed_responses"] = _fixed_responses(
                Path(vector_dir), kwargs["evidence_chain_product"]
            )
        return real_run_correction(vector_dir, payload, **kwargs)

    monkeypatch.setattr(pipeline, "run_correction", _deterministic_run_correction)
    run_dir = _stage_as_drawn_run(tmp_path)
    policy = _make_policy(capability_profile="orthogonal_polygon",
                          run_profile="exploratory")
    result, rep = _draw_correction_as_drawn(run_dir, None, False, policy)
    # the flow's standard shape
    assert result.window_host_claims is not None
    assert not rep.blocking(), [
        (r.check_id, r.message) for r in rep.blocking()
    ]
    # ⭐ population is wired at the flow entry: a building WITHOUT windows
    # must never archive as a success (the windows=0 false-green trap)
    assert len(result.geom.windows) == 31
    # storey order came from the manifest's declared floor_ref
    assert [
        p.name for p in sorted((run_dir / "1_correction").glob("floor_*"))
    ] == ["floor_1", "floor_2"]
    for floor in ("floor_1", "floor_2"):
        assert (
            run_dir / "1_correction" / floor / "evidence_chain_compilation.json"
        ).exists()
    # the S1/S2 ledgers landed where the flow expects them
    assert (run_dir / "1_correction" / "footprint_snap_ledger.json").exists()
    assert (run_dir / "1_correction" / "evidence_debt.json").exists()
    filed = json.loads(
        (run_dir / "1_correction" / "evidence_debt.json").read_text("utf-8")
    )
    # ⭐ 2026-09-08h 债退休（实测条件化）：staged 平面产物声明了 window 洞口
    # ⇒ 窗证据有自己的台账载体（opening 目录 + claim links + 有牙影子门），
    # 「on chain NOT on ledger」不再为真 ⇒ 落一份【空债账】记账退休，
    # ⛔ 不是删除（平面侧 window 证据归零时 S1 会重新落债并 strict 拒绝）。
    assert filed["debts"] == [], filed["debts"]
    # and the window account is filed as a signal, not a silence
    account = json.loads(
        (run_dir / "1_correction" / "as_drawn_window_account.json").read_text("utf-8")
    )
    assert account["windows_built"] == 31
    assert len(account["plan_records_folded"]) == 29


def test_strict_run_profile_rides_the_chain_strict_side(tmp_path, monkeypatch):
    import src.agent.pipeline as pipeline

    seen: dict = {}

    def _fake_mfc(evidence, plan_runs, *, snap_ledger_path=None,
                  evidence_debt_path=None):
        seen["profiles"] = [r.profile for r in plan_runs]
        # reproduce the REAL wiring's strict behavior (S1): file the debt,
        # then fail closed on it
        from src.agent.correction.multifloor import MultiFloorAssemblyError
        from src.agent.execution.evidence_preflight import (
            WINDOW_EVIDENCE_CHANNEL_SPLIT_DEBT_ID,
            window_evidence_channel_split_debt,
            write_evidence_debt,
        )

        debt = window_evidence_channel_split_debt(
            chain_profile=plan_runs[0].profile
        )
        if evidence_debt_path is not None:
            write_evidence_debt(evidence_debt_path, debt)
        if debt.blocking:
            raise MultiFloorAssemblyError(
                WINDOW_EVIDENCE_CHANNEL_SPLIT_DEBT_ID,
                {"evidence_chain_profile": plan_runs[0].profile},
            )
        return _square_two_storey()

    monkeypatch.setattr(pipeline, "run_multifloor_correction", _fake_mfc)
    import run_stage

    monkeypatch.setattr(
        run_stage,
        "_w1_cross_check_elevation_ladders",
        lambda entries, rdir: _east_evidence(),
    )
    run_dir = _stage_as_drawn_run(tmp_path)
    policy = _make_policy(capability_profile="orthogonal_polygon",
                          run_profile="golden")
    with pytest.raises(Exception) as exc:
        _draw_correction_as_drawn(run_dir, None, False, policy)
    # the strict chain profile is what the S1 debt blocks on
    assert seen["profiles"] == ["strict", "strict"]
    assert "WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER" in str(exc.value)


def _east_evidence():
    from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation

    return adapt_as_drawn_elevation(
        (_AS_DRAWN_OUT / "sm25_east_as_drawn.json").read_bytes(),
        input_id="East_view",
        facade_ref="East",
    )


def test_real_products_now_agree_strictly_on_declared_ticks(tmp_path):
    """丁 LOCK (ruling 2026-09-07x §一 flipped the S4 stop-report lock):
    the four REAL sm25 elevation products DISAGREED on the measured z
    sequences (the S4 stop-report — spread 1.0–13.5 mm of pixel-side
    scatter), and the ruling moved the VALUE to each drawing's own DECLARED
    ``calibration.z.cum_mm`` ticks (recognition stays the ink).  The strict
    cross-check — unchanged text, still tuple equality, ⛔ zero threshold —
    now compares declared INTEGERS and the four facades agree BY
    CONSTRUCTION (3600/7200 are the same integers in all four chains,
    chain_closure 0.0).  The scatter did not vanish: it is a readout
    (``ink_snap_residual_mm``) and this test pins both halves."""
    import run_stage
    from src.agent.correction.multifloor import derive_floor_ladder
    from src.agent.execution.view_manifest import ViewManifest

    run_dir = _stage_as_drawn_run(tmp_path)
    manifest = ViewManifest.model_validate_json(
        (run_dir / "_run" / "view_manifest.json").read_text("utf-8")
    )
    elevation_entries = [
        e for e in manifest.required_entries() if e.view_type == "elevation"
    ]
    # the strict check itself: PASSES now (no SystemExit), returns a bundle
    artifact = run_stage._w1_cross_check_elevation_ladders(
        elevation_entries, run_dir / "0_reading"
    )
    assert artifact is not None
    # and the ink-side scatter the ruling set aside is still OBSERVABLE:
    # the four ladders' readouts are non-identical (pixel-side product)
    residuals = set()
    for entry in elevation_entries:
        raw = (run_dir / "0_reading" / f"{entry.expected_output_id}.json").read_bytes()
        ladder = derive_floor_ladder(_adapt_elevation(raw, entry))
        residuals.add(
            tuple(
                (round(level.ink_snap_residual_mm, 3),
                 round(level.ink_snap_residual_upper_mm, 3))
                for level in ladder
            )
        )
    assert len(residuals) == 4, (
        "the four facades' ink residuals should stay four distinct "
        f"readouts (pixel-side scatter), got {residuals!r}"
    )


def _adapt_elevation(raw: bytes, entry):
    from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation

    doc = json.loads(raw.decode("utf-8"))
    facade_label = doc.get("facade_label") if isinstance(doc, dict) else None
    return adapt_as_drawn_elevation(
        raw,
        input_id=entry.input_id,
        facade_ref=(
            facade_label
            if isinstance(facade_label, str) and facade_label
            else entry.input_id
        ),
    )


def test_declared_tick_uniqueness_has_teeth(tmp_path):
    """丁 discriminating lock: mutate ONE facade product's declared tick
    chain so a rung's second-nearest tick falls INSIDE its own noise bound
    (a denser chain than the ink can resolve) ⇒ the ladder derivation is a
    NAMED refusal (FLOOR_LINE_TICK_UNPROVEN), ⛔ never a silent snap onto an
    ambiguous tick.  The unmutated products stay green through the same
    code path — the red is the mutation's, not the fixture's."""
    import run_stage
    from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
    from src.agent.correction.multifloor import (
        MultiFloorAssemblyError,
        derive_floor_ladder,
    )

    run_dir = _stage_as_drawn_run(tmp_path)
    raw = (run_dir / "0_reading" / "East_view.json").read_bytes()
    artifact = adapt_as_drawn_elevation(
        raw, input_id="East_view", facade_ref="East"
    )
    derive_floor_ladder(artifact)  # unmutated: green

    doc = json.loads(raw.decode("utf-8"))
    # denser than the ink can resolve: east's noise bound is 2.808 mm and
    # its mid rung's ink sits AT the 3600 tick — ticks 1 mm either side put
    # the SECOND-nearest at 1.0 mm, inside the bound ⇒ ambiguous snap.
    # (The chain still closes: sum(values_mm) == cum_mm[-1] == overall.)
    doc["calibration"]["z"]["cum_mm"] = [0.0, 1000.0, 2600.0, 3599.0, 3601.0,
                                         4600.0, 6200.0, 7199.0, 7200.0]
    mutated = json.dumps(doc).encode("utf-8")
    mutated_artifact = adapt_as_drawn_elevation(
        mutated, input_id="East_view", facade_ref="East"
    )
    with pytest.raises(MultiFloorAssemblyError) as exc:
        derive_floor_ladder(mutated_artifact)
    assert "FLOOR_LINE_TICK_UNPROVEN" in str(exc.value)
    assert "second_nearest_tick_inside_noise_bound" in str(exc.value)


def test_declared_tick_missing_declaration_is_loud(tmp_path):
    """丁 stop-trigger lock: a product that does NOT declare calibration.z
    cannot have its storey z taken from the declared chain ⇒ a NAMED
    refusal (FLOOR_TICK_DECLARATION_MISSING), ⛔ no invented tolerance and
    ⛔ no silent fallback to the measured ink."""
    from src.agent.correction.evidence_adapters import adapt_as_drawn_elevation
    from src.agent.correction.multifloor import (
        MultiFloorAssemblyError,
        derive_floor_ladder,
    )

    run_dir = _stage_as_drawn_run(tmp_path)
    raw = (run_dir / "0_reading" / "East_view.json").read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    doc["calibration"]["z"] = None
    mutated = json.dumps(doc).encode("utf-8")
    # the adapter's own chain-closure recompute refuses a broken chain
    # first (CALIBRATION_CHAIN_MALFORMED) — also loud, also named
    with pytest.raises(Exception) as exc:
        adapt_as_drawn_elevation(
            mutated, input_id="East_view", facade_ref="East"
        )
    assert "CALIBRATION" in str(exc.value) or "FLOOR_TICK" in str(exc.value)

    # the ladder-side refusal shape: declare a chain that CLOSES but lacks
    # the residual/mm_per_px the uniqueness proof needs
    doc2 = json.loads(raw.decode("utf-8"))
    z = doc2["calibration"]["z"]
    z.pop("residual_px")
    z.pop("mm_per_px")
    # keep the chain closed: recompute the summary fields the adapter checks
    z["values_mm"] = [
        z["cum_mm"][i + 1] - z["cum_mm"][i] for i in range(len(z["cum_mm"]) - 1)
    ]
    mutated2 = json.dumps(doc2).encode("utf-8")
    artifact2 = adapt_as_drawn_elevation(
        mutated2, input_id="East_view", facade_ref="East"
    )
    with pytest.raises(MultiFloorAssemblyError) as exc2:
        derive_floor_ladder(artifact2)
    assert "FLOOR_TICK_DECLARATION_MISSING" in str(exc2.value)
