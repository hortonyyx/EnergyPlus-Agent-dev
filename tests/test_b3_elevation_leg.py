"""B3 -- the as-drawn elevation leg (dispatch 2026-09-03j).

WHAT THIS FILE LOCKS
--------------------
The six acceptance rules of the dispatch sheet, §六, as rules ⛔ not as
transcripts of this run's readings:

1. the four REAL sm25 elevation products are classified
   ``as_drawn_elevation_v0`` with disposition ``ADAPT`` by the classifier
   (⛔ never by file name) and all four go through the adapter;
2. every z of every opening claim and every floor level dereferences back
   to the exact frozen byte it names (all of them, not a sample);
3. the floor-line selection is a RULE: a synthetic three-storey
   2.9 / 3.3 / 4.2 elevation yields exactly its own four levels, and a
   re-shaped ladder (different count, different heights) yields the new
   ladder -- no sm25 reading appears anywhere in the production code;
4. the same bytes produce a bit-identical ``content_sha256``;
5. bad inputs fail LOUDLY with named codes (z missing / chain not closed /
   degenerate ladder), and the validator catches the carrier swaps the
   adapter cannot see from inside a healthy product (a value drifted from
   its byte, a dropped level, a vertical line claimed as a level);
6. a windowless facade is an honest zero-run (absent + debt), ⛔ not an
   error.

The synthetic fixture deliberately violates every sm25 reading (three
storeys, mixed storey heights) so that any constant smuggled from the real
corpus would break these tests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.agent.correction.evidence_adapters import (
    ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
    adapt_as_drawn_elevation,
)
from src.agent.correction.evidence_contract import (
    CHANNEL_PAYLOAD_MEMBERS,
    CorrectionEvidenceBundleV1,
    EvidenceContractError,
    as_drawn_elevation_floor_lines,
    finalize_bundle,
    resolve_json_pointer,
    validate_evidence_bundle,
)
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_ELEVATION_V0,
    Disposition,
    classify_vector_json,
)

_PRODUCTS = Path(
    "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_FACADES = ("east", "west", "north", "south")


def _real_raw(facade: str) -> bytes:
    p = _PRODUCTS / f"sm25_{facade}_as_drawn.json"
    # ⛔ never skip on a missing fixture -- that is a red, not a pass
    assert p.is_file(), f"tracked elevation product missing: {p}"
    return p.read_bytes()


# ── the synthetic fixture: three storeys, 2.9 / 3.3 / 4.2 ─────────────────── #
def _synthetic_elevation(
    storey_mm: list[float], *, openings: tuple = ()
) -> dict:
    """Build a minimal ``as_drawn_elevation_v0`` product for ANY ladder.

    ⭐ The ladder comes in as data (per-storey heights); the fixture derives
    everything (cumulative levels, chains, pixel geometry) from it, so the
    same factory serves a 2-storey and a 3-storey drawing and any heights
    -- whatever rule the production code uses must follow the DATA, and a
    rule that hardcoded sm25's readings fails the 3-storey case below.
    """
    levels_mm: list[float] = []
    total = 0.0
    for h in storey_mm:
        total += h
        levels_mm.append(total)
    # chains: z closes by construction; x is a plain 2-segment chain
    z_values = [float(h) for h in storey_mm]
    z_cum = [0.0, *levels_mm]
    x_values = [5000.0, 4000.0]
    x_cum = [0.0, 5000.0, 9000.0]
    # pixel geometry: any self-consistent scale (fixture data, ⛔ never a
    # production-side constant); 10 mm/px keeps every derived value tidy
    mm_per_px = 10.0
    z_px = [level / mm_per_px for level in z_cum]
    x_px = [v / mm_per_px for v in x_cum]

    structure_lines = []
    for i, level in enumerate(z_cum):
        structure_lines.append({
            "id": f"L{i:02d}",
            "axis": "row",
            "constant_quantity": "z",
            "pos_px": z_px[i],
            "pos_m": level / 1000.0,
            "cols_px": [int(z_px[i]), int(z_px[i]) + 1],
            "runs_px": [[x_px[0], x_px[-1]]],
            "runs_m": [[0.0, x_cum[-1] / 1000.0]],
            "gaps": [],
            "covered_px": int(x_px[-1] - x_px[0]),
            "span_ratio": 1.0,
        })
    for j, xpos in enumerate(x_cum):
        structure_lines.append({
            "id": f"V{j:02d}",
            "axis": "col",
            "constant_quantity": "x",
            "pos_px": x_px[j],
            "pos_m": xpos / 1000.0,
            "cols_px": [int(x_px[j]), int(x_px[j]) + 1],
            "runs_px": [[z_px[0], z_px[-1]]],
            "runs_m": [[0.0, z_cum[-1] / 1000.0]],
            "gaps": [],
            "covered_px": int(z_px[-1] - z_px[0]),
            "span_ratio": 1.0,
        })

    opening_nodes = []
    for k, (z_low_m, z_high_m) in enumerate(openings):
        base_px = z_low_m * 1000.0 / mm_per_px
        opening_nodes.append({
            "id": f"O{k:02d}",
            "z_range_m": [z_low_m, z_high_m],
            "x_range_m": [0.5, 1.5],
            "width_m": 1.0,
            "height_m": z_high_m - z_low_m,
            "edge_witnesses": {
                "z_low": {"measured_px": base_px, "nearest_tick_px": base_px,
                          "distance_px": 0.0, "distance_mm": 0.0,
                          "dimension_refs": [f"L{k:02d}"]},
                "z_high": {"measured_px": base_px + 1, "nearest_tick_px": base_px,
                           "distance_px": 1.0, "distance_mm": 10.0,
                           "dimension_refs": [f"L{k:02d}"]},
            },
        })

    return {
        "schema": "as_drawn_elevation_v0",
        "facade_label": "Synthetic",
        "image_label": "Synthetic elevation",
        "calibration": {
            "x": {
                "values_mm": x_values, "cum_mm": x_cum,
                "overall_mm": x_cum[-1], "matched_px": x_px,
                "origin_px": x_px[0], "mm_per_px": mm_per_px,
                "residual_px": [0.0] * len(x_px), "rmse_px": 0.0,
                "max_abs_residual_px": 0.0, "chain_closure_mm": 0.0,
            },
            "z": {
                "values_mm": z_values, "cum_mm": z_cum,
                "overall_mm": z_cum[-1], "matched_px": z_px,
                "origin_px": z_px[0], "mm_per_px": mm_per_px,
                "residual_px": [0.0] * len(z_px), "rmse_px": 0.0,
                "max_abs_residual_px": 0.0, "chain_closure_mm": 0.0,
            },
        },
        "structure_lines": structure_lines,
        "openings": opening_nodes,
    }


def _synthetic_bytes(storey_mm: list[float], *, openings: tuple = ()) -> bytes:
    return json.dumps(
        _synthetic_elevation(storey_mm, openings=openings), indent=1
    ).encode("utf-8")


def _frozen_doc(artifact) -> dict:
    assert len(artifact.frozen_sources) == 1
    return json.loads(artifact.frozen_sources[0].raw_bytes)


# ── acceptance 1: the real four, classified by the classifier ──────────────── #
@pytest.mark.parametrize("facade", _FACADES)
def test_real_facade_classified_adapt_and_bundle(facade):
    raw = _real_raw(facade)
    decision = classify_vector_json(json.loads(raw))
    assert decision.contract_id == CONTRACT_AS_DRAWN_ELEVATION_V0
    assert decision.disposition is Disposition.ADAPT

    artifact = adapt_as_drawn_elevation(
        raw, input_id=f"sm25_{facade}_elev", facade_ref=facade.capitalize()
    )
    states = {s.channel: s.state for s in artifact.bundle.channel_status}
    assert states["elevation_openings"] == "present"
    assert states["floor_levels"] == "present"
    assert len(artifact.bundle.elevation_opening_claims) == len(
        json.loads(raw)["openings"]
    )
    # the ladder claims exactly what the rule selects from the same bytes
    rule_says = set(as_drawn_elevation_floor_lines(json.loads(raw)))
    assert {c.structure_line_id for c in artifact.bundle.floor_level_claims
            } == rule_says


# ── acceptance 2: EVERY z and EVERY level dereferences to its byte ─────────── #
@pytest.mark.parametrize("facade", _FACADES)
def test_every_z_and_level_points_at_its_frozen_byte(facade):
    raw = _real_raw(facade)
    artifact = adapt_as_drawn_elevation(
        raw, input_id=f"sm25_{facade}_elev", facade_ref=facade.capitalize()
    )
    doc = _frozen_doc(artifact)
    for claim in artifact.bundle.elevation_opening_claims:
        for value, ref in (
            (claim.z_low_m, claim.z_low_ref), (claim.z_high_m, claim.z_high_ref)
        ):
            byte = resolve_json_pointer(doc, ref.json_pointer)
            assert value == byte, (facade, claim.opening_id, ref.json_pointer)
            # the pointer is anchored into THIS artifact's frozen bytes
            assert ref.source_output_sha256 == hashlib.sha256(
                artifact.frozen_sources[0].raw_bytes
            ).hexdigest()
    for claim in artifact.bundle.floor_level_claims:
        assert claim.z_m == resolve_json_pointer(doc, claim.z_ref.json_pointer)


# ── acceptance 3: the floor rule follows the DATA, not sm25 ────────────────── #
def test_three_storey_mixed_heights_select_their_own_ladder():
    raw = _synthetic_bytes([2900.0, 3300.0, 4200.0],
                           openings=((0.1, 2.1), (3.0, 5.5), (6.6, 9.9)))
    artifact = adapt_as_drawn_elevation(
        raw, input_id="synth3", facade_ref="Synthetic"
    )
    levels = sorted(c.z_m for c in artifact.bundle.floor_level_claims)
    assert levels == [0.0, 2.9, 6.2, 10.4]
    # the ladder's adjacent differences ARE the input storey heights
    diffs = [round(b - a, 9) for a, b in zip(levels, levels[1:])]
    assert diffs == [2.9, 3.3, 4.2]
    # ⛔ none of sm25's readings may show up as a selected level
    assert 3.6 not in levels and 7.2 not in levels


def test_reshaped_ladder_selects_the_new_ladder():
    """Same factory, different count AND different heights: the rule must
    select the new ladder.  A list masquerading as a rule fails here."""
    raw = _synthetic_bytes([3050.0, 2750.0], openings=((0.2, 2.2),))
    artifact = adapt_as_drawn_elevation(
        raw, input_id="synth2", facade_ref="Synthetic"
    )
    levels = sorted(c.z_m for c in artifact.bundle.floor_level_claims)
    assert levels == [0.0, 3.05, 5.8]


def test_vertical_structure_lines_are_never_levels():
    raw = _synthetic_bytes([2900.0, 3300.0])
    doc = json.loads(raw)
    selected = as_drawn_elevation_floor_lines(doc)
    vertical = {s["id"] for s in doc["structure_lines"]
                if s["constant_quantity"] == "x"}
    assert vertical, "fixture must carry vertical lines for this check"
    assert not (set(selected) & vertical)


# ── acceptance 4: bit-identical hash for the same bytes ────────────────────── #
@pytest.mark.parametrize("facade", _FACADES)
def test_content_sha256_reproduces(facade):
    raw = _real_raw(facade)
    a1 = adapt_as_drawn_elevation(
        raw, input_id=f"sm25_{facade}_elev", facade_ref=facade.capitalize()
    )
    a2 = adapt_as_drawn_elevation(
        raw, input_id=f"sm25_{facade}_elev", facade_ref=facade.capitalize()
    )
    assert a1.bundle.content_sha256 == a2.bundle.content_sha256
    assert json.dumps(json.loads(a1.bundle.model_dump_json()), sort_keys=True
                      ) == json.dumps(json.loads(a2.bundle.model_dump_json()),
                                      sort_keys=True)


def test_content_sha256_moves_on_any_byte_change():
    raw = _synthetic_bytes([2900.0, 3300.0, 4200.0], openings=((0.1, 2.1),))
    doc = json.loads(raw)
    doc["openings"][0]["z_range_m"] = [0.2, 2.1]
    other = json.dumps(doc, indent=1).encode("utf-8")
    a1 = adapt_as_drawn_elevation(raw, input_id="s", facade_ref="S")
    a2 = adapt_as_drawn_elevation(other, input_id="s", facade_ref="S")
    assert a1.bundle.content_sha256 != a2.bundle.content_sha256


# ── acceptance 5: bad inputs fail loudly, with a NAME ───────────────────────── #
def test_z_missing_is_loud():
    doc = _synthetic_elevation([2900.0, 3300.0, 4200.0],
                               openings=((0.1, 2.1),))
    del doc["openings"][0]["z_range_m"]
    raw = json.dumps(doc, indent=1).encode("utf-8")
    with pytest.raises(EvidenceContractError) as excinfo:
        adapt_as_drawn_elevation(raw, input_id="bad_z", facade_ref="B")
    assert excinfo.value.code == "ELEVATION_OPENING_Z_MISSING"


def test_z_inverted_is_loud():
    doc = _synthetic_elevation([2900.0], openings=((2.1, 0.1),))
    raw = json.dumps(doc, indent=1).encode("utf-8")
    with pytest.raises(EvidenceContractError) as excinfo:
        adapt_as_drawn_elevation(raw, input_id="bad_dir", facade_ref="B")
    assert excinfo.value.code == "ELEVATION_OPENING_Z_MISSING"


def test_chain_not_closed_is_loud():
    doc = _synthetic_elevation([2900.0, 3300.0, 4200.0])
    # break the x chain's overall claim only (sum vs cum still fine):
    doc["calibration"]["x"]["overall_mm"] = 9001.0
    raw = json.dumps(doc, indent=1).encode("utf-8")
    with pytest.raises(EvidenceContractError) as excinfo:
        adapt_as_drawn_elevation(raw, input_id="bad_chain", facade_ref="B")
    assert excinfo.value.code == "CALIBRATION_CHAIN_NOT_CLOSED"
    assert excinfo.value.context["axis"] == "x"


def test_chain_values_do_not_sum_is_loud():
    doc = _synthetic_elevation([2900.0, 3300.0])
    doc["calibration"]["z"]["values_mm"] = [2900.0, 3301.0]
    raw = json.dumps(doc, indent=1).encode("utf-8")
    with pytest.raises(EvidenceContractError) as excinfo:
        adapt_as_drawn_elevation(raw, input_id="bad_sum", facade_ref="B")
    assert excinfo.value.code == "CALIBRATION_CHAIN_NOT_CLOSED"


def test_degenerate_ladder_is_loud():
    """One horizontal structure line only -- the z-shape of the
    spans-the-whole-building premise failing (a partial elevation)."""
    doc = _synthetic_elevation([2900.0, 3300.0])
    doc["structure_lines"] = [
        s for s in doc["structure_lines"] if s["id"] == "L00"
    ]
    raw = json.dumps(doc, indent=1).encode("utf-8")
    with pytest.raises(EvidenceContractError) as excinfo:
        adapt_as_drawn_elevation(raw, input_id="degenerate", facade_ref="B")
    assert excinfo.value.code == "FLOOR_LADDER_DEGENERATE"


# ── acceptance 5, validator side: the carrier swaps a healthy product
#    cannot see from inside ──────────────────────────────────────────────────── #
def _validated_synthetic():
    raw = _synthetic_bytes(
        [2900.0, 3300.0, 4200.0], openings=((0.1, 2.1), (3.0, 5.5))
    )
    return adapt_as_drawn_elevation(raw, input_id="synth", facade_ref="S")


def test_validator_catches_a_drifted_z_value():
    """Carrier swap: the claim's z stops matching the byte it names."""
    art = _validated_synthetic()
    claim = art.bundle.elevation_opening_claims[0]
    drifted = claim.model_copy(update={"z_low_m": claim.z_low_m + 0.5})
    bundle = art.bundle.model_copy(update={
        "elevation_opening_claims": [
            drifted if c.opening_id == claim.opening_id else c
            for c in art.bundle.elevation_opening_claims
        ]
    })
    bundle = finalize_bundle(bundle)
    with pytest.raises(EvidenceContractError) as excinfo:
        validate_evidence_bundle(art.model_copy(update={"bundle": bundle}))
    assert excinfo.value.code == "ELEVATION_Z_VALUE_DRIFTED_FROM_SOURCE"


def test_validator_catches_a_dropped_level():
    """The rule is enforced at the exit: a bundle that drops one selected
    level must be FLOOR_LADDER_NOT_EXHAUSTIVE, ⛔ never silently fewer."""
    art = _validated_synthetic()
    kept = list(art.bundle.floor_level_claims)[1:]
    bundle = art.bundle.model_copy(update={"floor_level_claims": kept})
    bundle = finalize_bundle(bundle)
    with pytest.raises(EvidenceContractError) as excinfo:
        validate_evidence_bundle(art.model_copy(update={"bundle": bundle}))
    assert excinfo.value.code == "FLOOR_LADDER_NOT_EXHAUSTIVE"
    assert excinfo.value.context["dropped"], "the dropped id must be named"


def test_validator_catches_a_vertical_line_claimed_as_a_level():
    art = _validated_synthetic()
    doc = _frozen_doc(art)
    # re-point one floor claim at a VERTICAL structure line's node
    vertical = next(
        (i, s) for i, s in enumerate(doc["structure_lines"])
        if s["constant_quantity"] == "x"
    )
    i, line = vertical
    from src.agent.correction.evidence_contract import (
        ArtifactPointerV1, FloorLevelClaimV1, ObservationRefV1,
    )
    from src.agent.correction.window_sources import source_locator
    sha = art.frozen_sources[0].artifact.source_output_sha256
    contract = art.frozen_sources[0].artifact.source_contract_id
    forged = FloorLevelClaimV1(
        structure_line_id=line["id"],
        source_ref=ObservationRefV1(
            input_id="synth", source_contract_id=contract,
            source_output_sha256=sha, json_pointer=f"/structure_lines/{i}",
            observation_id=line["id"],
            source_locator=source_locator(
                input_id="synth", observation_id=line["id"], output_sha256=sha
            ),
            pixel_witness_pointers=(f"/structure_lines/{i}/pos_px",),
            evidence_resolution="pixel_backed",
        ),
        z_m=float(line["pos_m"]),
        z_ref=ArtifactPointerV1(
            input_id="synth", source_contract_id=contract,
            source_output_sha256=sha, json_pointer=f"/structure_lines/{i}/pos_m",
        ),
    )
    bundle = art.bundle.model_copy(update={
        "floor_level_claims": [
            *art.bundle.floor_level_claims, forged
        ]
    })
    bundle = finalize_bundle(bundle)
    with pytest.raises(EvidenceContractError) as excinfo:
        validate_evidence_bundle(art.model_copy(update={"bundle": bundle}))
    assert excinfo.value.code == "FLOOR_LINE_NOT_HORIZONTAL"


# ── acceptance 5, structure: the honest exits stay legal ────────────────────── #
def test_windowless_facade_is_an_honest_zero_run():
    raw = _synthetic_bytes([2900.0, 3300.0])  # no openings at all
    artifact = adapt_as_drawn_elevation(
        raw, input_id="blank", facade_ref="Gable"
    )
    states = {s.channel: s.state for s in artifact.bundle.channel_status}
    assert states["elevation_openings"] == "absent"
    assert states["floor_levels"] == "present"
    debts = {d.channel for d in artifact.bundle.evidence_debts
             if d.kind == "missing_channel"}
    assert "elevation_openings" in debts
    validate_evidence_bundle(artifact)  # the whole artifact stays valid


def test_payload_members_table_covers_both_new_channels():
    """The routing table: both B3 channels have their payload members named
    in the ONE table every closure direction reads."""
    assert CHANNEL_PAYLOAD_MEMBERS["elevation_openings"] == (
        "elevation_opening_claims",
    )
    assert CHANNEL_PAYLOAD_MEMBERS["floor_levels"] == ("floor_level_claims",)


def test_bundle_default_carries_the_new_members():
    """A default-constructed bundle exposes both new lists (typing sanity
    for downstream consumers like B2/B4)."""
    bundle = CorrectionEvidenceBundleV1(
        schema_version="correction_evidence_bundle_v1"
    )
    assert bundle.elevation_opening_claims == []
    assert bundle.floor_level_claims == []


# ── acceptance 5, R2-b: the span debt travels in the PRODUCT ────────────────── #
def _span_debt(artifact):
    """The downstream's ONLY view: read the bundle, ⛔ never the source --
    a source comment stops nobody (the rework sheet's criterion verbatim:
    downstream does not read source comments, only products)."""
    return [
        d for d in artifact.bundle.evidence_debts
        if d.debt_id.startswith("debt_elevation_chain_span_unchecked_")
    ]


@pytest.mark.parametrize("facade", _FACADES)
def test_span_equality_gap_travels_as_a_named_debt(facade):
    """⭐ R2-b (B3 rework 1, 2026-09-03): the half of the named premise this
    leg cannot check single-sourced -- chain total == the plan side's
    outer-skin span -- must be an EXPLICIT debt in every elevation bundle,
    naming B4's equality gate as owner.  ``other_known_missing`` blocks no
    profile by ruling, so the debt travels with the artifact instead of
    making success unreachable; and ``channel=None`` keeps it an ownership
    claim, ⛔ never a channel excuse."""
    artifact = adapt_as_drawn_elevation(
        _real_raw(facade), input_id=facade, facade_ref=facade
    )
    span = _span_debt(artifact)
    assert len(span) == 1, (
        f"the span-equality gap must travel as exactly one named debt, "
        f"found {len(span)} -- without it the gap lives only in a source "
        "comment, which downstream never reads"
    )
    debt = span[0]
    assert debt.kind == "other_known_missing"
    assert debt.channel is None, "an ownership claim, ⛔ not a channel excuse"
    assert "B4" in debt.description, "the debt must name its owner"
    assert ELEVATION_CHAIN_SPANS_WHOLE_BUILDING in debt.description
    # the debt's refs must dereference into THIS artifact's frozen source
    assert [r.input_id for r in debt.affected_refs] == [facade]
    # the artifact with the debt on board stays wholly valid
    validate_evidence_bundle(artifact)


def test_the_span_debt_is_a_property_of_the_family_not_the_fixture():
    """A synthetic three-storey facade carries the same debt: it cannot
    silently depend on which fixture ran (the same family-rule shape as
    acceptance 3's ladder locks)."""
    artifact = adapt_as_drawn_elevation(
        _synthetic_bytes([2900.0, 3300.0]),
        input_id="synthetic", facade_ref="East",
    )
    assert len(_span_debt(artifact)) == 1
    validate_evidence_bundle(artifact)


# =========================================================================== #
# Acceptance 7 (dispatch v2 T7): "wired" cashed at the REAL entry point.
# Measured before the branch existed: the ledger printed "recognized; wired
# to the correction evidence adapter (module 7)" for an elevation product
# while the real if/elif refused the very same bytes with
# EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED — a claim the pipeline did not
# honour.
# =========================================================================== #
def _stage_real_east(tmp_path: Path) -> tuple[Path, Path]:
    """Stage the REAL east facade product + a stage out_dir (route record
    lands in ``out_dir.parent/_run/``)."""
    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    raw = _real_raw("east")
    (vector_dir / "sm25_east_as_drawn.json").write_bytes(raw)
    out_dir = tmp_path / "1_correction"
    out_dir.mkdir()
    return vector_dir, out_dir


def _round0_elevation_packet(vector_dir: Path):
    """Build the round-0 packet exactly as the chain's loop does, so the
    fixed response can bind its hash (same shape as the wiring lock in
    ``test_o22m7``)."""
    from src.agent.correction.decision_executor import build_decision_packet
    from src.agent.correction.decision_executor import compile_wall_ir

    raw = (vector_dir / "sm25_east_as_drawn.json").read_bytes()
    artifact = adapt_as_drawn_elevation(
        raw, input_id="sm25_east_as_drawn", facade_ref="East"
    )
    return build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"),
        bundle=artifact,
        round_index=0,
    )


def _booby_trap_the_model_seat(monkeypatch):
    """⭐ R3 (B3 rework 1, 2026-09-03): make the model seat EXPLODE the
    moment anything sits on it.  Both T7 locks prove a MODEL-FREE exit --
    that proof must not depend on the refusal happening before the seat is
    even built: if a future route change ever seats a provider under these
    locks, the trap fires instead of a billed network call."""
    import src.agent.pipeline as pipeline

    def _trapped(*, section, out_dir):
        def _never(packet):
            raise AssertionError(
                "MODEL SEAT OCCUPIED: this lock must stay model-free "
                "(fixed_responses is the sanctioned escape hatch; a green "
                "here must never cost a billed call)"
            )
        return _never

    monkeypatch.setattr(pipeline, "_make_decision_response_provider", _trapped)


def test_real_entry_point_takes_real_elevation_bytes(monkeypatch, tmp_path):
    """⛔ NOT a direct ``adapt_as_drawn_elevation`` call: the dispatch's
    whole point (v2 T7) is that the DISPOSITION'S claim -- "recognized;
    wired to the correction evidence adapter (module 7)" -- is true at
    ``pipeline.run_correction_evidence_chain``, the real if/elif.  The
    frozen bytes are fed THERE; ``fixed_responses`` drives the model beat
    (the model is NOT called -- this lock proves wiring, ⛔ never a model
    result), and the route record must name the elevation adapter and the
    product's own facade label.

    ⭐ R3-a: the model-free exit is held MECHANICALLY on BOTH sides -- the
    ``response_source`` assertion below (red the moment the fixed
    responses stop driving the loop) AND a booby-trapped model seat (so
    the very mutation that would seat a model detonates here, ⛔ never on
    the network)."""
    from src.agent.correction.decision_executor import run_decision_loop  # noqa: F401  (proves the import path the chain drives)
    from src.agent.correction.decision_schema import CorrectionDecisionResponseV1

    import src.agent.pipeline as pipeline

    _booby_trap_the_model_seat(monkeypatch)
    vector_dir, out_dir = _stage_real_east(tmp_path)
    packet = _round0_elevation_packet(vector_dir)
    outcome = pipeline.run_correction_evidence_chain(
        vector_dir,
        "sm25_east_as_drawn.json",
        out_dir=out_dir,
        fixed_responses=[
            CorrectionDecisionResponseV1(
                packet_hash=packet.packet_hash,
                item_decisions=(),
                whole_building_review={"verdict": "accept"},
            )
        ],
    )
    route = json.loads(
        (tmp_path / "_run" / "evidence_chain_route.json").read_text(
            encoding="utf-8"
        )
    )
    assert route["contract"] == "as_drawn_elevation_v0"
    assert route["adapter"] == "adapt_as_drawn_elevation"
    assert route["response_source"].startswith("fixed_responses"), (
        "the model beat must NOT be called by this lock"
    )
    assert route["outcome_success"] == outcome.success


def test_real_entry_point_without_the_branch_goes_red_unwired(
    monkeypatch, tmp_path
):
    """The STANDING neuter lock (dispatch acceptance 7-②): make the
    elevation branch's condition unreachable -- exactly what removing the
    branch does -- by rebinding the module constant the branch compares
    against; the REAL entry point must then refuse the very same bytes
    with ``EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED``.

    ⭐ Premise is proven by the green twin above: with the branch intact
    the same call does NOT raise, so a red here can only mean the branch.

    ⭐ R3-b (B3 rework 1): the ``UNWIRED`` refusal fires at the adapt link,
    BEFORE any route record exists -- so ``response_source`` is unreadable
    here, and this lock used to have NO mechanical hold on the model-free
    exit at all (dropping ``fixed_responses=[]`` left it green: B-3).  The
    equivalent hold the cross-review named, now in place: (a) the CALL'S
    OWN PARAMETERS are captured by a wrapper that forwards to the real
    entry untouched -- the refusal must be proven to happen on a call that
    carries ``fixed_responses``, so deleting that argument is a red; and
    (b) the model seat is booby-trapped, so a future route that seats a
    model before refusing detonates here instead of on the network."""
    import src.agent.pipeline as pipeline
    import src.agent.reading.vector_contract as vector_contract

    _booby_trap_the_model_seat(monkeypatch)
    monkeypatch.setattr(
        vector_contract,
        "CONTRACT_AS_DRAWN_ELEVATION_V0",
        "as_drawn_elevation_v0_branch_removed",
    )
    # (a) parameter capture: forward to the REAL entry, record what the
    # call itself carried (the wrapper adds nothing and removes nothing).
    real_entry = pipeline.run_correction_evidence_chain
    seen_kwargs: dict = {}

    def _recording_entry(*args, **kwargs):
        seen_kwargs.update(kwargs)
        return real_entry(*args, **kwargs)

    monkeypatch.setattr(
        pipeline, "run_correction_evidence_chain", _recording_entry
    )
    vector_dir, out_dir = _stage_real_east(tmp_path)
    with pytest.raises(EvidenceContractError) as raised:
        pipeline.run_correction_evidence_chain(
            vector_dir,
            "sm25_east_as_drawn.json",
            out_dir=out_dir,
            fixed_responses=[],
        )
    assert "EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED" in str(raised.value)
    assert seen_kwargs.get("fixed_responses") == [], (
        "the refusal was proven on a call WITHOUT the model-free hatch "
        f"(kwargs seen: {sorted(seen_kwargs)}) -- this lock must keep "
        "calling the real entry WITH fixed_responses, or it proves "
        "nothing about the model-free exit (B-3)"
    )
