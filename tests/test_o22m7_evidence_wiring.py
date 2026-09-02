"""②-2 module 7 (v2 dispatch, 2026-09-02): the evidence chain's wiring.

Dispatch: ``AI_agent/logs/reviews/request/
2026-09-02a_wiring_module7_dispatch_v2.md``; authority: the approved
evidence-contract design §6.1–§6.3 + §9.1 step 7 ("new and old sources both
go through the bundle").  This file locks the WIRING, not the modules --
modules 1–6 keep their own locked files.  One lock per dispatch acceptance
row (4 / 4b / 5 / plus the B/D switch and failure contract), each green
anchor on the slice IT owns.

The chain under test (run_correction_evidence_chain):

    frozen reading bytes → adapt_* → CorrectionEvidenceBundleArtifactV1
      → compile_wall_ir → WallCompilationV1
      → build_decision_packet → CorrectionDecisionPacketV1
      → [the model beat] → CorrectionDecisionResponseV1
      → run_decision_loop → DecisionLoopOutcomeV1  ← this module's terminus

No lock in this file calls a real model: the model beat is driven either by
``fixed_responses`` (the dispatch's sanctioned escape hatch) or by a fake
OpenAI client -- what IS locked is that the beat's payloads pass through the
no-coordinate guard and the strict type on their way into the executor.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import src.agent.pipeline as pipeline
import src.agent.reading.vector_contract as vc
from src.agent.correction.decision_executor import (
    DecisionLoopError,
    build_decision_packet,
    compile_wall_ir,
    run_decision_loop,
)
from src.agent.correction.decision_schema import (
    CorrectionDecisionResponseV1,
    CoordinateSmuggledInResponse,
    ItemDecisionV1,
    assert_response_payload_carries_no_coordinates,
)
from src.agent.correction.evidence_adapters import (
    adapt_as_drawn_plan,
    adapt_legacy_reading_view,
)
from src.agent.correction.evidence_contract import EvidenceContractError
from src.agent.correction.wall_compiler import WallCompilerError
from src.agent.reading.as_drawn.schema import SCHEMA

_V2_OUT = Path(
    "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_LEGACY_VIEW = Path(
    "case_tests/e2e_tests/sm25-L_anchor/"
    "run_2026-08-25_c2_rescore_R0/0_reading/1f_view.json"
)


# ── shared fixtures ---------------------------------------------------------- #
def _stage(tmp_path: Path) -> tuple[Path, Path]:
    """(vector_dir with the real sm25 new-format product, stage out_dir)."""
    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    src = _V2_OUT / "sm25_2f_v2.json"
    (vector_dir / src.name).write_bytes(src.read_bytes())
    out_dir = tmp_path / "1_correction"
    out_dir.mkdir()
    return vector_dir, out_dir


def _accept_empty(packet) -> CorrectionDecisionResponseV1:
    """The minimal honest fixed response: bind the packet, decide nothing,
    accept nothing conditional -- an empty-decision accept."""
    return CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=(),
        whole_building_review={"verdict": "accept"},
    )


def _round0_packet(vector_dir: Path, filename: str, profile: str = "exploratory"):
    raw = (vector_dir / filename).read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if vc.classify_vector_json(doc).contract_id == vc.CONTRACT_AS_DRAWN_PLAN:
        artifact = adapt_as_drawn_plan(
            raw, input_id=Path(filename).stem, floor_ref="2f"
        )
    else:
        artifact = adapt_legacy_reading_view(
            raw, input_id=Path(filename).stem, floor_ref="1f"
        )
    return build_decision_packet(
        compile_wall_ir(artifact, profile=profile), bundle=artifact, round_index=0
    )


class _PastedLegTouched(RuntimeError):
    """Booby trap: raised iff the pasted-JSON leg is touched at all."""


@pytest.fixture()
def booby_trap_pasteed_leg(monkeypatch):
    """Acceptance 3's per-link companion: the evidence chain must NEVER
    fall back to (or even assemble) the pasted-JSON prompt."""
    def _touch(*args, **kwargs):
        raise _PastedLegTouched("the pasted-JSON leg was touched")
    monkeypatch.setattr(pipeline, "_build_correction_messages", _touch)


# =========================================================================== #
# Acceptance 4 -- route selection, three directions, each its own lock
# =========================================================================== #
def test_route_direction_1_new_format_plan_takes_the_as_drawn_adapter(tmp_path):
    """A REAL sm25 new-format plan product routes through
    ``adapt_as_drawn_plan`` and reaches the terminus with the route record
    naming the adapter (the dispatch's own measured premise, now a rule)."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    outcome = pipeline.run_correction_evidence_chain(
        vector_dir,
        "sm25_2f_v2.json",
        out_dir=out_dir,
        fixed_responses=[_accept_empty(packet)],
    )
    route = json.loads(
        (tmp_path / "_run" / "evidence_chain_route.json").read_text(encoding="utf-8")
    )
    assert route["contract"] == "as_drawn_plan"
    assert route["adapter"] == "adapt_as_drawn_plan"
    assert route["response_source"].startswith("fixed_responses")
    assert route["outcome_success"] == outcome.success
    assert route["exit_reason"] == outcome.exit_reason


def test_route_direction_2_legacy_view_takes_the_legacy_adapter(tmp_path):
    """A REAL legacy reading view routes through ``adapt_legacy_reading_view``
    -- "new and old sources both go through the bundle" (§9.1 step 7), not a
    compatibility shim around the pasted-JSON leg."""
    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    (vector_dir / _LEGACY_VIEW.name).write_bytes(_LEGACY_VIEW.read_bytes())
    out_dir = tmp_path / "1_correction"
    out_dir.mkdir()
    packet = _round0_packet(vector_dir, _LEGACY_VIEW.name)
    outcome = pipeline.run_correction_evidence_chain(
        vector_dir,
        _LEGACY_VIEW.name,
        out_dir=out_dir,
        fixed_responses=[_accept_empty(packet)],
    )
    route = json.loads(
        (tmp_path / "_run" / "evidence_chain_route.json").read_text(encoding="utf-8")
    )
    assert route["contract"] == "reading_view_legacy"
    assert route["adapter"] == "adapt_legacy_reading_view"
    assert route["outcome_success"] == outcome.success


def test_route_direction_3_damaged_new_format_is_unknown_never_legacy(tmp_path):
    """The direction the dispatch marks as the point: a STRUCTURALLY DAMAGED
    new-format product comes out of the classifier UNKNOWN (BLK-A measured on
    a real product, ⛔ not read off its comment), and is refused by the
    legacy adapter too -- no silent fall back to legacy recognition on either
    face."""
    src = _V2_OUT / "sm25_2f_v2.json"
    raw = json.loads(src.read_text(encoding="utf-8"))
    damaged = dict(raw)
    damaged.pop("observations")  # declared schema, failed contract keys
    damaged_bytes = json.dumps(damaged).encode("utf-8")
    # and the disguise: append legacy structure so structural recognition
    # WOULD have a target if the BLK-A rule did not hold
    damaged["strokes"] = [{"id": "S1", "pen": "wall", "points": [[0, 0], [1, 0]]}]
    disguised_bytes = json.dumps(damaged).encode("utf-8")

    for payload in (damaged_bytes, disguised_bytes):
        decision = vc.classify_vector_json(json.loads(payload))
        assert decision.contract_id == vc.CONTRACT_UNKNOWN, decision.reason
        with pytest.raises(EvidenceContractError) as exc:
            adapt_legacy_reading_view(
                payload, input_id="damaged", floor_ref="1f"
            )
        assert exc.value.code == "ADAPTER_CONTRACT_MISMATCH"

    # and through the chain's own front door: loud adapt-link refusal
    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    (vector_dir / "damaged.json").write_bytes(disguised_bytes)
    with pytest.raises(EvidenceContractError) as exc:
        pipeline.run_correction_evidence_chain(vector_dir, "damaged.json")
    assert exc.value.code == "EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED"


# =========================================================================== #
# Acceptance 3 -- a failure at EACH link: uncaught, recorded, no success product
# =========================================================================== #
def _failure_record(tmp_path: Path) -> dict:
    return json.loads(
        (tmp_path / "_run" / "evidence_chain_failure.json").read_text(encoding="utf-8")
    )


def test_link_failure_source_read(tmp_path, booby_trap_pasteed_leg):
    vector_dir, out_dir = _stage(tmp_path)
    with pytest.raises(OSError):
        pipeline.run_correction_evidence_chain(
            vector_dir, "missing_file.json", out_dir=out_dir,
            fixed_responses=[],
        )
    assert _failure_record(tmp_path)["failed_stage"] == "source_read"
    assert not (out_dir / "decision_loop_outcome.json").exists()


def test_link_failure_adapt(tmp_path, booby_trap_pasteed_leg):
    vector_dir, out_dir = _stage(tmp_path)
    (vector_dir / "broken.json").write_bytes(b"{not json")
    with pytest.raises(json.JSONDecodeError):
        pipeline.run_correction_evidence_chain(
            vector_dir, "broken.json", out_dir=out_dir, fixed_responses=[]
        )
    assert _failure_record(tmp_path)["failed_stage"] == "adapt"
    assert not (out_dir / "decision_loop_outcome.json").exists()


def _face(fid: str, axis: str, world_axis: str, col: int, runs_px: list) -> dict:
    runs_m = [[lo / 10.0, hi / 10.0] for lo, hi in runs_px]
    return {
        "id": fid, "axis": axis, "constant_world_axis": world_axis,
        "pos_px": float(col), "pos_m": 0.01 * col,
        "support_cols_px": [col, col + 1], "edges_m": [0.0, 0.02],
        "support_width_m": 0.02, "runs_px": runs_px, "runs_m": runs_m,
        "gaps": [], "ink_coverage_per_run": [1.0] * len(runs_px),
        "covered_px": sum(hi - lo for lo, hi in runs_px),
        "support_px": sum(hi - lo for lo, hi in runs_px) + 1,
    }


def _pair(face_a: str, face_b: str, spacing_px: float) -> dict:
    return {
        "face_a": face_a, "face_b": face_b,
        "spacing_px": spacing_px, "spacing_m": spacing_px / 100.0,
        "matched_declared_mm": [int(spacing_px)],
        "overlap_px": 80, "source": "selected",
    }


def test_link_failure_compile(tmp_path, booby_trap_pasteed_leg):
    """strict profile + an ambiguous face debt: module 4's own named refusal
    (⭐ measured through the chain, not unit-style against compile alone)."""
    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": [
            _face("F01", "col", "x", 100, [[10, 100]]),
            _face("F02", "col", "x", 112, [[10, 100]]),
            _face("F09", "row", "y", 300, [[4, 8]]),
        ]},
        "declarations": {},
        "hypotheses": {
            "pairs": [_pair("F01", "F02", 12.0)],
            "pair_candidates": [
                {k: v for k, v in _pair("F01", "F02", 12.0).items()
                 if k != "source"}
            ],
            "opening_candidates": [], "opening_types": None,
            "pairs_status": "SELECTED",
            "non_wall_face_lines": {},
            "unpaired_wall_faces": {},
            "solid_band_walls": {},
            "ambiguous_face_lines": {"F09": "wall or furniture"},
        },
    }
    (vector_dir / "amb.json").write_text(
        json.dumps(doc), encoding="utf-8"
    )
    out_dir = tmp_path / "1_correction"
    out_dir.mkdir()
    with pytest.raises(WallCompilerError):
        pipeline.run_correction_evidence_chain(
            vector_dir, "amb.json", out_dir=out_dir,
            profile="strict", fixed_responses=[],
        )
    assert _failure_record(tmp_path)["failed_stage"] == "compile"
    assert not (out_dir / "decision_loop_outcome.json").exists()


def test_link_failure_model(tmp_path, booby_trap_pasteed_leg, monkeypatch):
    """The model beat's transport dies: the RuntimeError from the beat's own
    retry exhaustion propagates uncaught, named as the model link."""
    vector_dir, out_dir = _stage(tmp_path)

    def _dead_call(*args, **kwargs):
        raise RuntimeError("provider transport dead")

    monkeypatch.setattr(pipeline, "_call_json_llm", _dead_call)
    with pytest.raises(RuntimeError, match="provider transport dead"):
        pipeline.run_correction_evidence_chain(
            vector_dir, "sm25_2f_v2.json", out_dir=out_dir
        )
    assert _failure_record(tmp_path)["failed_stage"] == "model"
    assert not (out_dir / "decision_loop_outcome.json").exists()


def test_link_failure_loop(tmp_path, booby_trap_pasteed_leg):
    """A fixed response deciding an item THIS packet does not hold: the
    executor's own DecisionLoopError family propagates uncaught."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    bad = CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=(ItemDecisionV1(
            item_id="item_not_in_this_packet",
            action="reject_all",
            reason_code="FABRICATED",
        ),),
        whole_building_review={"verdict": "accept"},
    )
    with pytest.raises(DecisionLoopError):
        pipeline.run_correction_evidence_chain(
            vector_dir, "sm25_2f_v2.json", out_dir=out_dir, fixed_responses=[bad]
        )
    assert _failure_record(tmp_path)["failed_stage"] == "loop"
    assert not (out_dir / "decision_loop_outcome.json").exists()


# =========================================================================== #
# The B/D switch: explicit, off by default, terminal instead of a fallback
# =========================================================================== #
def test_evidence_chain_switch_defaults_off():
    """The default is OFF -- every existing caller keeps the pasted-JSON leg
    (acceptance 2's premise, pinned so a default flip cannot slip in)."""
    params = inspect.signature(pipeline.run_correction).parameters
    assert params["evidence_chain"].default is False


def test_switch_on_reaches_the_terminus_loudly(tmp_path, booby_trap_pasteed_leg):
    """evidence_chain=True drives the chain to its terminus and raises
    EvidenceChainTerminal -- ⛔ no CorrectedGeometry is invented, ⛔ no
    fallback to the pasted-JSON leg (booby trap), and the message carries
    the as-measured success / exit_reason."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    with pytest.raises(pipeline.EvidenceChainTerminal) as exc:
        pipeline.run_correction(
            vector_dir,
            "{}",
            out_dir=out_dir,
            evidence_chain=True,
            evidence_chain_product="sm25_2f_v2.json",
            evidence_chain_fixed_responses=[_accept_empty(packet)],
        )
    outcome = json.loads(
        (out_dir / "decision_loop_outcome.json").read_text(encoding="utf-8")
    )
    msg = str(exc.value)
    assert f"success={outcome['success']}" in msg
    assert f"exit_reason={outcome['exit_reason']!r}" in msg


def test_switch_on_without_a_product_is_a_loud_value_error(tmp_path):
    vector_dir, _ = _stage(tmp_path)
    with pytest.raises(ValueError, match="evidence_chain_product"):
        pipeline.run_correction(
            vector_dir, "{}", evidence_chain=True,
        )


# =========================================================================== #
# Acceptance 4b -- the flipped pin is a RULE that still goes red
# =========================================================================== #
def _wiring_sets(contracts) -> tuple[set[str], set[str]]:
    """The rule's criterion, shared by the lock and its own mutation check:
    the consuming set and the adapting set are each EXACTLY the one named
    contract.  ⚠️ Explicit parameter -- a module-level default would bind at
    def time and neuter the monkeypatch the mutation test relies on."""
    consuming = {
        s.contract_id for s in contracts
        if s.disposition is vc.Disposition.CONSUME
    }
    adapting = {
        s.contract_id for s in contracts
        if s.disposition is vc.Disposition.ADAPT
    }
    return consuming, adapting


def test_4b_the_wiring_rule_holds_on_the_real_contracts():
    consuming, adapting = _wiring_sets(vc.CONTRACTS)
    assert consuming == {vc.CONTRACT_READING_VIEW_LEGACY}
    assert adapting == {vc.CONTRACT_AS_DRAWN_PLAN}


def test_4b_a_third_contract_quietly_turning_adapting_goes_red(monkeypatch):
    """The mutation the dispatch names: smuggle a THIRD contract into the
    adapting set; the rule above must fail on it (measured through the same
    criterion function -- ⛔ not a re-quoted copy of the assertion)."""
    smuggled = vc.ContractSpec(
        "contract_smuggled_wire",
        vc.Disposition.ADAPT,
        lambda raw: False,
        "smuggled wire for the mutation lock",
    )
    monkeypatch.setattr(vc, "CONTRACTS", vc.CONTRACTS + (smuggled,))
    with pytest.raises(AssertionError):
        assert _wiring_sets(vc.CONTRACTS) == (
            {vc.CONTRACT_READING_VIEW_LEGACY},
            {vc.CONTRACT_AS_DRAWN_PLAN},
        )


def test_4b_a_third_contract_quietly_turning_consuming_goes_red(monkeypatch):
    """Same mutation on the OTHER direction: the consuming set must stay
    exactly the legacy leg -- a second contract turning consumable is the
    F-97 shape the original pin existed for."""
    smuggled = vc.ContractSpec(
        "contract_smuggled_paste",
        vc.Disposition.CONSUME,
        lambda raw: False,
        "smuggled paste wire for the mutation lock",
    )
    monkeypatch.setattr(vc, "CONTRACTS", vc.CONTRACTS + (smuggled,))
    with pytest.raises(AssertionError):
        assert _wiring_sets(vc.CONTRACTS) == (
            {vc.CONTRACT_READING_VIEW_LEGACY},
            {vc.CONTRACT_AS_DRAWN_PLAN},
        )


# =========================================================================== #
# A -- the ADAPT ledger contract: named, not consumed, not an offender
# =========================================================================== #
def test_adapt_files_are_named_not_consumed_not_offenders(tmp_path):
    """The dispatch's three-row table for ADAPT, measured on one directory
    holding all three shapes: legacy (consume), as-drawn (adapt), sidecar
    (exclude)."""
    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir()
    (vector_dir / "1f_view.json").write_text(
        json.dumps({
            "image_label": "1f", "image_kind": "plan",
            "strokes": [
                {"id": "S1", "pen": "wall", "points": [[0.0, 0.0], [1.0, 0.0]]},
            ],
        }),
        encoding="utf-8",
    )
    (vector_dir / "sm25_2f_v2.json").write_bytes(
        (_V2_OUT / "sm25_2f_v2.json").read_bytes()
    )
    (vector_dir / "1f_view_checks.json").write_text(
        json.dumps({
            "stage": "0_reading", "results": [], "report_schema_version": "1",
            "artifact_hash": "abc", "attempt_hash": "def",
            "capability_profile": "rectangular",
        }),
        encoding="utf-8",
    )

    names = pipeline.discover_vector_files(vector_dir)
    ledger = vc.ledger_for(vector_dir, names)
    assert ledger["consumed"] == ["1f_view.json"]
    assert ledger["adapted"] == ["sm25_2f_v2.json"]
    assert ledger["counts"] == {"consume": 1, "adapt": 1, "exclude": 1}
    adapt_row = next(r for r in ledger["files"] if r["file"] == "sm25_2f_v2.json")
    assert adapt_row["disposition"] == "adapt"
    assert "adapter" in adapt_row["reason"]

    # not an offender: the directory classifier raises for nothing here
    decision = vc.classify_vector_dir(vector_dir, names)
    assert decision.adapted == ["sm25_2f_v2.json"]


# =========================================================================== #
# C -- the model beat's seat, and acceptance 5 (no coordinates, provably)
# =========================================================================== #
class _FakeMessage:
    def __init__(self, content: str):
        self.content = content
        self.reasoning_content = None


class _FakeCompletion:
    def __init__(self, content: str):
        self.choices = [
            type("Choice", (), {
                "message": _FakeMessage(content),
                "finish_reason": "stop",
            })()
        ]
        self.usage = type("Usage", (), {
            "prompt_tokens": 1, "completion_tokens": 1,
        })()


def _fake_openai_returning(payloads: list[dict]):
    """A fake pipeline.OpenAI whose completions return the given payload
    dicts as JSON, one per call (then the last one repeats)."""
    import itertools

    stream = itertools.chain(payloads, itertools.repeat(payloads[-1]))

    class _Completions:
        def create(self, **kwargs):
            return _FakeCompletion(json.dumps(next(stream)))

    class _Client:
        chat = type("Chat", (), {"completions": _Completions()})()

    return _Client


def _smuggled_payload(packet) -> dict:
    """A response payload that is LEGAL at the type layer (a plain string
    reason_code) but carries a coordinate PAIR inside that string -- the
    channel only the runtime guard can see."""
    return {
        "packet_hash": packet.packet_hash,
        "item_decisions": [{
            "item_id": packet.open_items[0].item_id,
            "action": "reject_all",
            "reason_code": "wall sits at 12.34, 56.78 per the drawing",
        }],
        "whole_building_review": {"verdict": "accept"},
    }


def test_5_guard_passes_legal_and_rejects_every_smuggle_channel():
    legal = {
        "packet_hash": "a" * 64,
        "item_decisions": [{
            "item_id": "i1", "action": "reject_all",
            "reason_code": "spacing 0.24 exceeds the band",
        }],
        "whole_building_review": {"verdict": "accept"},
    }
    assert_response_payload_carries_no_coordinates(legal)  # one dimension in prose is fine
    smuggles = [
        {"whole_building_review": {"verdict": "accept", "x": 1.5}},
        {"item_decisions": [{"item_id": "i", "action": "reject_all",
                             "reason_code": "at 12.34, 56.78"}]},
        {"item_decisions": [{"item_id": "i", "action": "reject_all",
                             "reason_code": "shift x=12.3 left"}]},
    ]
    for payload in smuggles:
        with pytest.raises(CoordinateSmuggledInResponse):
            assert_response_payload_carries_no_coordinates(payload)


def test_5_the_beat_rejects_smuggled_coordinates_end_to_end(
    tmp_path, monkeypatch
):
    """The wiring lock: a draw that passes the TYPE layer but smuggles a
    coordinate pair inside a string dies at the beat's own validation --
    measured through the provider with a fake transport, so the real
    _call_json_llm retry + validate path is what runs."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    monkeypatch.setattr(
        pipeline, "OpenAI",
        lambda **kwargs: _fake_openai_returning([_smuggled_payload(packet)]),
    )
    monkeypatch.setattr(
        pipeline, "_section", lambda name: {
            "api_key": "test-key", "base_url": "http://unused",
            "model_name": "fake", "temperature": 0.0,
        },
    )
    provider = pipeline._make_decision_response_provider(
        section_name="correction_decision", out_dir=out_dir
    )
    with pytest.raises(RuntimeError, match="failed after") as exc_info:
        provider(packet)
    assert isinstance(exc_info.value.__cause__, CoordinateSmuggledInResponse)


def test_5_neuter_the_guard_and_the_rejection_disappears(
    tmp_path, monkeypatch
):
    """⭐ The dispatch's "摘掉相应实现会变红" half: with the guard neutered to
    a no-op, the SAME type-legal smuggled payload sails through the beat.
    The previous lock's green is therefore carried by the guard
    implementation -- not by the type layer (which cannot see it) and not by
    tautology.  (This test asserts the DISARMING, which is exactly why the
    previous test must exist and stay green.)"""
    import src.agent.correction.decision_schema as ds

    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    monkeypatch.setattr(
        pipeline, "OpenAI",
        lambda **kwargs: _fake_openai_returning([_smuggled_payload(packet)]),
    )
    monkeypatch.setattr(
        pipeline, "_section", lambda name: {
            "api_key": "test-key", "base_url": "http://unused",
            "model_name": "fake", "temperature": 0.0,
        },
    )
    monkeypatch.setattr(
        ds,
        "assert_response_payload_carries_no_coordinates",
        lambda payload: None,
    )
    provider = pipeline._make_decision_response_provider(
        section_name="correction_decision", out_dir=out_dir
    )
    response = provider(packet)  # disarmed: no raise
    assert "12.34, 56.78" in response.item_decisions[0].reason_code


def test_provider_seats_the_model_in_the_loop(tmp_path):
    """run_decision_loop(response_provider=...): the provider receives EACH
    round's freshly built packet (bound hash) and its response drives the
    loop -- the executor keeps owning packets, validation and rebuilds."""
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": [
            _face("F01", "col", "x", 100, [[10, 100]]),
            _face("F02", "col", "x", 112, [[10, 100]]),
        ]},
        "declarations": {},
        "hypotheses": {
            "pairs": [_pair("F01", "F02", 12.0)],
            "pair_candidates": [
                {k: v for k, v in _pair("F01", "F02", 12.0).items()
                 if k != "source"}
            ],
            "opening_candidates": [], "opening_types": None,
            "pairs_status": "SELECTED",
            "non_wall_face_lines": {}, "unpaired_wall_faces": {},
            "solid_band_walls": {}, "ambiguous_face_lines": {},
        },
    }
    artifact = adapt_as_drawn_plan(
        json.dumps(doc).encode("utf-8"), input_id="one_pair", floor_ref="1f"
    )
    seen_packets = []

    def provider(packet):
        seen_packets.append(packet)
        return _accept_empty(packet)

    outcome = run_decision_loop(
        artifact, profile="exploratory",
        response_provider=provider, round_budget=2,
    )
    assert len(seen_packets) == 2
    assert [p.round_index for p in seen_packets] == [0, 1]
    assert seen_packets[0].packet_hash != seen_packets[1].packet_hash
    # an identical decision set repeating verbatim = the loop's own
    # decision_hash_cycle exit, caught at the head of the NEXT round
    # (module 6's design: cycle detection fires before the stall counter
    # could expire it -- and the provider mode inherits that behaviour)
    assert outcome.exit_reason == "decision_hash_cycle"
    assert outcome.success is False


def test_response_sources_are_mutually_exclusive(tmp_path):
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": [
            _face("F01", "col", "x", 100, [[10, 100]]),
            _face("F02", "col", "x", 112, [[10, 100]]),
        ]},
        "declarations": {},
        "hypotheses": {
            "pairs": [_pair("F01", "F02", 12.0)],
            "pair_candidates": [
                {k: v for k, v in _pair("F01", "F02", 12.0).items()
                 if k != "source"}
            ],
            "opening_candidates": [], "opening_types": None,
            "pairs_status": "SELECTED",
            "non_wall_face_lines": {}, "unpaired_wall_faces": {},
            "solid_band_walls": {}, "ambiguous_face_lines": {},
        },
    }
    artifact = adapt_as_drawn_plan(
        json.dumps(doc).encode("utf-8"), input_id="one_pair", floor_ref="1f"
    )
    packet = build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"),
        bundle=artifact, round_index=0,
    )
    fixed = _accept_empty(packet)
    with pytest.raises(DecisionLoopError) as exc:
        run_decision_loop(
            artifact, responses=[fixed], response_provider=lambda p: None,
            round_budget=1,
        )
    assert exc.value.code == "RESPONSE_SOURCE_AMBIGUOUS"


def test_provider_mode_requires_an_explicit_round_budget(tmp_path):
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": [
            _face("F01", "col", "x", 100, [[10, 100]]),
        ]},
        "declarations": {},
        "hypotheses": {
            "pairs": [], "pair_candidates": [],
            "opening_candidates": [], "opening_types": None,
            "pairs_status": "SELECTED",
            "non_wall_face_lines": {"F01": "not a wall"},
            "unpaired_wall_faces": {}, "solid_band_walls": {},
            "ambiguous_face_lines": {},
        },
    }
    artifact = adapt_as_drawn_plan(
        json.dumps(doc).encode("utf-8"), input_id="empty", floor_ref="1f"
    )
    with pytest.raises(DecisionLoopError):
        run_decision_loop(artifact, response_provider=lambda p: None)


# =========================================================================== #
# D -- the outcome lands as measured; no success product is invented
# =========================================================================== #
def test_outcome_lands_with_as_measured_success_and_exit_reason(tmp_path):
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    outcome = pipeline.run_correction_evidence_chain(
        vector_dir, "sm25_2f_v2.json",
        out_dir=out_dir, fixed_responses=[_accept_empty(packet)],
    )
    landed = json.loads(
        (out_dir / "decision_loop_outcome.json").read_text(encoding="utf-8")
    )
    assert landed["success"] is outcome.success
    assert landed["exit_reason"] == outcome.exit_reason
    assert landed["success"] is False or landed["exit_reason"] == "success"
    # D's negative rule: a non-success exit is never filed as a success product
    if landed["exit_reason"] != "success":
        assert landed["success"] is False
