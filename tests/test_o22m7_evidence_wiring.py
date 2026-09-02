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
no-coordinate diagnostic and the strict type on their way into the executor.

v3 rework (2026-09-02, GPT cross-review B-1/B-2/NF-1) adds three families:

* B-1: the beat loads its llm.yaml section BY ITS REAL NAME (no silent
  intake_correction fallback), and the route records the RESOLVED
  section/model read from the loaded dict -- never the request's echo;
* B-2: the coordinate defence moved from the lexical regex to the TYPE
  layer -- every model-minted string is a CodeToken over [A-Z_] with no
  digit at all, so the measured coordinate notations (and any other) are
  UNREPRESENTABLE, not detected;
* NF-1: per-round raw archives, so each round's decision hash recomputes
  from the archive without trusting the report.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.agent.pipeline as pipeline
import src.agent.reading.vector_contract as vc
from src.agent.correction.decision_executor import (
    DecisionLoopError,
    build_decision_packet,
    compile_wall_ir,
    decision_hash,
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


#: The already-resolved section dict handed to the provider in provider-mode
#: tests: the chain resolves the real config once (_load_decision_beat_section)
#: and the provider holds THAT dict, so tests inject the dict directly.
_TEST_SECTION = {
    "api_key": "test-key", "base_url": "http://unused",
    "model_name": "fake", "temperature": 0.0,
}


def _smuggled_payload(packet) -> dict:
    """The v2 cross-review's B-2 probe, verbatim in shape: an INTEGER
    coordinate pair inside reason_code.  This exact form passed BOTH the
    runtime guard (decimal-pairs only) and the then-free string field; the
    v3 type layer (CodeToken) must be what kills it now."""
    return {
        "packet_hash": packet.packet_hash,
        "item_decisions": [{
            "item_id": packet.open_items[0].item_id,
            "action": "reject_all",
            "reason_code": "wall endpoint is at (12, 34)",
        }],
        "whole_building_review": {"verdict": "accept"},
    }


def test_5_guard_passes_legal_and_rejects_every_smuggle_channel():
    """The beat's pre-construction DIAGNOSTIC keeps its own semantics
    (v3: the guard is advisory, the closed type is the defence -- see
    decision_schema).  One dimension in prose passes; a numeric leaf, a
    decimal pair and a lowercase axis assignment are named-and-refused."""
    legal = {
        "packet_hash": "a" * 64,
        "item_decisions": [{
            "item_id": "i1", "action": "reject_all",
            "reason_code": "SPACING_EXCEEDS_DECLARED_BAND",
        }],
        "whole_building_review": {"verdict": "accept"},
        # a prose string on an unconstrained key: the guard is a payload
        # walk that runs BEFORE construction, so it still documents its
        # own "one dimension in prose is fine" semantics here.
        "note": "one dimension in prose, spacing 0.24, is fine",
    }
    assert_response_payload_carries_no_coordinates(legal)
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
    """The wiring lock (v3): the cross-review's integer-pair draw -- the
    form the old regex MISSED -- still dies inside the beat, now at the
    type layer (CodeToken construction) instead of the lexical guard,
    measured through the provider with a fake transport so the real
    _call_json_llm retry + validate path is what runs."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    monkeypatch.setattr(
        pipeline, "OpenAI",
        lambda **kwargs: _fake_openai_returning([_smuggled_payload(packet)]),
    )
    provider = pipeline._make_decision_response_provider(
        section=_TEST_SECTION, out_dir=out_dir
    )
    with pytest.raises(RuntimeError, match="failed after") as exc_info:
        provider(packet)
    assert isinstance(exc_info.value.__cause__, ValidationError)
    assert "string_pattern_mismatch" in {
        e["type"] for e in exc_info.value.__cause__.errors()
    }


def test_5_neuter_the_type_layer_and_the_smuggle_sails_through(
    tmp_path, monkeypatch
):
    """⭐ v3 successor of the guard-neuter lock: the load-bearing wall is
    now the TYPE.  Widen reason_code back to free text (the disarm) and
    the SAME integer-pair payload -- which the lexical guard never saw --
    sails through the beat untouched.  This is exactly why the previous
    lock must exist and stay green: its green is carried by the CodeToken
    constraint, not by the (demoted, guard-transparent) regex and not by
    tautology."""
    import src.agent.correction.decision_schema as ds

    class _FreeTextItemDecision(ds.ItemDecisionV1):
        reason_code: str  # the disarm: the v2 shape, verbatim

    class _FreeTextResponse(ds.CorrectionDecisionResponseV1):
        item_decisions: tuple[_FreeTextItemDecision, ...] = ()

    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    monkeypatch.setattr(
        pipeline, "OpenAI",
        lambda **kwargs: _fake_openai_returning([_smuggled_payload(packet)]),
    )
    monkeypatch.setattr(
        ds, "CorrectionDecisionResponseV1", _FreeTextResponse
    )
    provider = pipeline._make_decision_response_provider(
        section=_TEST_SECTION, out_dir=out_dir
    )
    response = provider(packet)  # disarmed: no raise
    assert "wall endpoint is at (12, 34)" in response.item_decisions[0].reason_code


# =========================================================================== #
# v3 rework B-2 -- the TYPE layer is the defence (no free-text channel exists)
# =========================================================================== #
#: The dispatcher's three measured misses plus two forms they did NOT list
#: ('x:12;y:34' colon/semicolon axes; '12 34' space-separated bare pair).
#: All five are transparent to the demoted lexical guard -- asserted below,
#: so the lock demonstrably bites on guard-missed forms, not on ones the
#: old regex already caught.
_COORDINATE_NOTATIONS = [
    "(12, 34)",          # integer pair in parens (the B-2 probe itself)
    "X = 12, Y = 34",    # uppercase + spaces axis assignment
    "[12, 34]",          # bracketed pair
    "x:12;y:34",         # colon/semicolon axis pair (v3 addition)
    "12 34",             # space-separated bare pair (v3 addition)
]

#: Every string field the model may MINT itself (v3, B-2).  The echoed
#: ids (item_id / candidate_id / entity ids) are deliberately absent:
#: their closure is the executor's packet-membership check, a different
#: lock's business.
_MINTED_CHANNELS = (
    "item.reason_code",
    "finding.finding_id",
    "finding.kind",
    "finding.rationale",
    "reperception.reason_code",
)


def _payload_with(channel: str, value: str) -> dict:
    """A response payload carrying `value` in ONE minted string channel,
    with every other minted field holding a legal token -- so a rejection
    can only be about the channel under test."""
    payload = {
        "packet_hash": "a" * 64,
        "item_decisions": [],
        "whole_building_review": {"verdict": "accept"},
    }
    if channel == "item.reason_code":
        payload["item_decisions"].append({
            "item_id": "i1", "action": "reject_all", "reason_code": value,
        })
        return payload
    finding = {
        "finding_id": "FIND_ONE",
        "kind": "WHOLE_BUILDING_SHAPE",
        "rationale": "PROBE",
        "affected_entity_ids": ["w1"],
        "requested_effect": {
            "kind": "review_alignment",
            "subject_entity_ids": ["w1"],
            "reference_entity_ids": ["w1"],
            "relation": "collinear",
        },
    }
    if channel == "finding.finding_id":
        finding["finding_id"] = value
    elif channel == "finding.kind":
        finding["kind"] = value
    elif channel == "finding.rationale":
        finding["rationale"] = value
    elif channel == "reperception.reason_code":
        finding["requested_effect"] = {
            "kind": "request_wall_reperception",
            "wall_item_entity_ids": ["w1"],
            "reason_code": value,
        }
    else:  # pragma: no cover - channel list is closed above
        raise AssertionError(channel)
    payload["whole_building_review"] = {
        "verdict": "findings", "findings": [finding],
    }
    return payload


#: one LEGAL token per minted channel -- the positive control that the
#: matrix below is discriminating (legal constructs, illegal dies), not
#: a blanket rejection of everything.
_LEGAL_TOKENS = {
    "item.reason_code": "SPACING_EXCEEDS_DECLARED_BAND",
    "finding.finding_id": "FIND_ALIGNMENT_REVIEW",
    "finding.kind": "WHOLE_BUILDING_SHAPE",
    "finding.rationale": "WALL_MISALIGNED_WITH_NEIGHBOUR",
    "reperception.reason_code": "CANNOT_READ_BAND",
}


def test_b2_every_coordinate_notation_is_unrepresentable_in_every_minted_field():
    """The general rule, not the five examples: EVERY string field the
    model may mint itself is a CodeToken, so no coordinate notation is
    CONSTRUCTIBLE into the response.  Positive control first (legal tokens
    construct in every channel), then each measured form goes into each
    minted channel and must die at construction (string_pattern_mismatch)
    while staying transparent to the lexical guard -- i.e. it is genuinely
    the type that rejects, not the demoted regex."""
    for channel, token in _LEGAL_TOKENS.items():
        parsed = CorrectionDecisionResponseV1.model_validate_json(
            json.dumps(_payload_with(channel, token))
        )
        assert parsed.packet_hash == "a" * 64  # constructed, not just no-error
    for form in _COORDINATE_NOTATIONS:
        for channel in _MINTED_CHANNELS:
            payload = _payload_with(channel, form)
            # guard-transparent: the diagnostic does NOT see these forms
            assert_response_payload_carries_no_coordinates(payload)
            with pytest.raises(ValidationError) as exc:
                CorrectionDecisionResponseV1.model_validate_json(
                    json.dumps(payload)
                )
            assert "string_pattern_mismatch" in {
                e["type"] for e in exc.value.errors()
            }, (form, channel)


# =========================================================================== #
# v3 rework B-1 -- the configured model seat is actually loaded, and the
# route records the RESOLVED section/model, never the request's echo
# =========================================================================== #
def _sentinel_config(tmp_path: Path, *, include_decision: bool = True) -> Path:
    """An active llm.yaml whose two sections point at DIFFERENT model
    sentinels, so "which section was loaded" is measurable in the dict the
    beat's LLM call actually receives."""
    lines = [
        "intake_correction:",
        "  provider: openai",
        "  model_name: sentinel-intake-model",
        "  api_key: literal-key",
    ]
    if include_decision:
        lines += [
            "correction_decision:",
            "  provider: openai",
            "  model_name: sentinel-decision-model",
            "  api_key: literal-key",
        ]
    cfg = tmp_path / "llm.yaml"
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cfg


def _route_record(tmp_path: Path) -> dict:
    return json.loads(
        (tmp_path / "_run" / "evidence_chain_route.json").read_text(encoding="utf-8")
    )


def test_b1_the_provider_actually_gets_the_named_section(tmp_path, monkeypatch):
    """Acceptance 1: two DIFFERENT model sentinels -- the section dict the
    beat's LLM call actually receives must be correction_decision's.  ⛔
    "no error" would not count: the v2 run silently loaded
    intake_correction and still succeeded, which is exactly why the sentinels
    must differ."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    monkeypatch.setenv("EP_AGENT_LLM_CONFIG", str(_sentinel_config(tmp_path)))
    captured: dict = {}

    def _capture(section, *args, **kwargs):
        captured.update(section)
        return {
            "packet_hash": packet.packet_hash,
            "item_decisions": [],
            "whole_building_review": {"verdict": "accept"},
        }

    monkeypatch.setattr(pipeline, "_call_json_llm", _capture)
    pipeline.run_correction_evidence_chain(
        vector_dir, "sm25_2f_v2.json", out_dir=out_dir, round_budget=1
    )
    assert captured["model_name"] == "sentinel-decision-model"
    assert captured["model_name"] != "sentinel-intake-model"
    route = _route_record(tmp_path)
    assert route["llm_section_requested"] == "correction_decision"
    assert route["llm_section_resolved"] == "correction_decision"
    assert route["llm_model_resolved"] == "sentinel-decision-model"
    assert route["response_source"] == "model:correction_decision"


def test_b1_route_reports_the_resolved_model_not_the_request_echo(
    tmp_path, monkeypatch
):
    """Acceptance 2: make requested and actually-loaded DIFFER (the exact
    shape of the v2 bug -- a resolution handing back a section the request
    name does not imply, here simulated at the loader boundary) and prove
    the route follows the ACTUAL dict, not the name.  An echo -- of the
    request name, or of the repo config's deepseek-v4-pro -- fails here."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    monkeypatch.setattr(
        pipeline, "load_llm_section",
        lambda name: {
            "api_key": "k", "base_url": "http://unused",
            "model_name": "whoami-diverged-model", "temperature": 0.0,
        },
    )
    monkeypatch.setattr(
        pipeline, "_call_json_llm",
        lambda section, *a, **k: {
            "packet_hash": packet.packet_hash,
            "item_decisions": [],
            "whole_building_review": {"verdict": "accept"},
        },
    )
    pipeline.run_correction_evidence_chain(
        vector_dir, "sm25_2f_v2.json", out_dir=out_dir, round_budget=1
    )
    route = _route_record(tmp_path)
    assert route["llm_model_resolved"] == "whoami-diverged-model"


def test_b1_a_missing_section_is_a_loud_config_error(tmp_path, monkeypatch):
    """No silent fallback: a config without a correction_decision section
    refuses to seat a model at all (v2 silently loaded intake_correction
    here), and the refusal is filed as a MODEL-link failure with no success
    product.  The OpenAI fake keeps the old code's red honest: without it,
    the v2 fallback would die on a real network call instead of plainly
    succeeding, and a transport error could masquerade as the refusal."""
    vector_dir, out_dir = _stage(tmp_path)
    packet = _round0_packet(vector_dir, "sm25_2f_v2.json")
    monkeypatch.setenv(
        "EP_AGENT_LLM_CONFIG",
        str(_sentinel_config(tmp_path, include_decision=False)),
    )
    monkeypatch.setattr(
        pipeline, "OpenAI",
        lambda **kwargs: _fake_openai_returning([{
            "packet_hash": packet.packet_hash,
            "item_decisions": [],
            "whole_building_review": {"verdict": "accept"},
        }]),
    )
    # match the loader's OWN wording: a loose match on the section name
    # would also catch the beat's transport RuntimeError (whose prefix is
    # the same name) and read a network failure as a config refusal.
    with pytest.raises(RuntimeError, match="has no 'correction_decision' section"):
        pipeline.run_correction_evidence_chain(
            vector_dir, "sm25_2f_v2.json", out_dir=out_dir, round_budget=1
        )
    assert _failure_record(tmp_path)["failed_stage"] == "model"
    assert not (out_dir / "decision_loop_outcome.json").exists()


# =========================================================================== #
# v3 rework NF-1 -- per-round archives: every round's decision hash is
# recomputable from the archive by a third party
# =========================================================================== #
def test_nf1_every_rounds_raw_is_archived_and_its_decision_hash_recomputes(
    tmp_path, monkeypatch
):
    """v2 kept ONE shared raw filename, so round 1 overwrote round 0 and
    the 22 first-round decisions became unrecomputable from the archive
    ("the model really ran" travels through the archive -- the v2
    cross-review had to RE-RUN the model to establish it).  With per-round
    filenames both rounds' raw responses land on disk -- driven through
    the REAL chain entry with the REAL _call_json_llm file-writing path
    (only the transport is fake) -- and each round's decision hash
    recomputes from its own file."""
    vector_dir, out_dir = _stage(tmp_path)
    monkeypatch.setenv("EP_AGENT_LLM_CONFIG", str(_sentinel_config(tmp_path)))
    raw = (vector_dir / "sm25_2f_v2.json").read_bytes()
    artifact = adapt_as_drawn_plan(
        raw, input_id="sm25_2f_v2", floor_ref="2f"
    )
    packet0 = build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"),
        bundle=artifact, round_index=0,
    )
    round0 = {
        "packet_hash": packet0.packet_hash,
        "item_decisions": [{
            "item_id": packet0.open_items[0].item_id,
            "action": "reject_all",
            "reason_code": "NO_TRUSTED_EVIDENCE",
        }],
        "whole_building_review": {"verdict": "accept"},
    }
    round0_response = CorrectionDecisionResponseV1.model_validate_json(
        json.dumps(round0)
    )
    # round 1 sees the SAME compilation (a reject executes nothing) with
    # round_index=1 and round 0's decision hash in its history -- built
    # exactly the way the loop builds it, so the fixture can bind it.
    packet1 = build_decision_packet(
        compile_wall_ir(artifact, profile="exploratory"),
        bundle=artifact, round_index=1,
        previous_decision_hashes=(decision_hash(round0_response),),
    )
    round1 = {
        "packet_hash": packet1.packet_hash,
        "item_decisions": [],
        "whole_building_review": {"verdict": "accept"},
    }
    monkeypatch.setattr(
        pipeline, "OpenAI",
        lambda **kwargs: _fake_openai_returning([round0, round1]),
    )
    outcome = pipeline.run_correction_evidence_chain(
        vector_dir, "sm25_2f_v2.json", out_dir=out_dir, round_budget=2
    )
    assert len(outcome.rounds) == 2
    raw0 = (out_dir / "correction_decision_r0_raw.txt").read_text(encoding="utf-8")
    raw1 = (out_dir / "correction_decision_r1_raw.txt").read_text(encoding="utf-8")
    assert raw0 != raw1
    recomputed0 = decision_hash(
        CorrectionDecisionResponseV1.model_validate_json(raw0)
    )
    recomputed1 = decision_hash(
        CorrectionDecisionResponseV1.model_validate_json(raw1)
    )
    assert recomputed0 == outcome.rounds[0].decision_hash
    assert recomputed1 == outcome.rounds[1].decision_hash


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
