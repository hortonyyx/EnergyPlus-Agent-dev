"""②-2 module 1: the as-drawn plan producer owns its own type (2026-08-30).

Dispatch: ``AI_agent/logs/reviews/request/
2026-08-30_o22m1_as_drawn_producer_types_dispatch.md``

What was wrong before: ``vector_contract`` recognised ``as_drawn_plan_v2`` by a
KEY LIST (``schema`` string + three top-level keys).  Anything at all could live
inside those three keys and the file was still filed as a well-formed product,
so ``MALFORMED_DECLARED_CONTRACT`` had no teeth -- the malformation was not
readable anywhere.

⭐ Every "has teeth" test below proves its own premise: it re-states the rule
this dispatch replaced and asserts that rule ACCEPTED the same input, so a
green here can never be the always-green kind
([[regression-case-must-prove-its-own-premise]],
[[gate-with-only-negative-assertions-is-unobservable]]).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.agent.reading.as_drawn.as_drawn_v2 as A
from src.agent.reading.as_drawn.schema import (
    DEFERRED_CHANNELS,
    FACE_DISPOSITION_BUCKETS,
    SCHEMA,
    AsDrawnPlanV2,
    HypothesesV2,
    ObservationsV2,
    validate_as_drawn_plan,
)
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_PLAN,
    CONTRACT_READING_VIEW_LEGACY,
    CONTRACT_UNKNOWN,
    CONTRACTS,
    Disposition,
    classify_vector_json,
)

_PRODUCTS = Path(
    "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_TRACKED = ("sm25_1f_v2.json", "sm25_2f_v2.json", "sm24_1f_v2.json")


def _load(name: str) -> dict:
    p = _PRODUCTS / name
    # ⛔ never `if p.exists()` + skip: a vanished fixture must be a red, not a
    # quiet pass ([[absent-file-read-as-passing-check]]).
    assert p.is_file(), f"tracked as-drawn product missing: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _detector_before_this_dispatch(raw: dict) -> bool:
    """The EXACT rule this dispatch replaced, restated so the tests can prove
    that the inputs below used to be accepted.

    Verbatim from ``vector_contract.py`` before 2026-08-30::

        lambda raw: _is_declared(raw, AS_DRAWN_PLAN_SCHEMA)
        and _has_keys(raw, "observations", "declarations", "hypotheses")
    """
    return raw.get("schema") == SCHEMA and all(
        k in raw for k in ("observations", "declarations", "hypotheses")
    )


# =========================================================================== #
# 验收 1 -- HAS TEETH: an element-level malformation is now loud, and the same
#            input was accepted by the rule this replaced.
# =========================================================================== #
def _bucket_value_is_a_dict(d):
    d["hypotheses"]["unpaired_wall_faces"]["L012"] = {"state": "ink_present_unpromoted"}


def _bucket_value_is_a_number(d):
    d["hypotheses"]["non_wall_face_lines"]["L001"] = 42


def _bucket_is_a_list(d):
    d["hypotheses"]["ambiguous_face_lines"] = ["L001", "L002"]


def _bucket_grows_an_untyped_sibling(d):
    d["hypotheses"]["probably_wall_face_lines"] = {"L001": "invented bucket"}


def _face_line_loses_its_id(d):
    del d["observations"]["face_lines"][0]["id"]


def _face_line_runs_become_a_string(d):
    d["observations"]["face_lines"][0]["runs_px"] = "0-100"


def _face_line_axis_is_a_world_axis(d):
    d["observations"]["face_lines"][0]["axis"] = "x"


def _pair_loses_face_b(d):
    del d["hypotheses"]["pairs"][0]["face_b"]


def _pair_spacing_arrives_as_text(d):
    d["hypotheses"]["pairs"][0]["spacing_m"] = "0.24"


def _pairs_become_a_dict(d):
    d["hypotheses"]["pairs"] = {"p0": ["L001", "L002"]}


def _opening_candidate_loses_its_span(d):
    del d["hypotheses"]["opening_candidates"][0]["span_m"]


def _opening_types_values_become_dicts(d):
    key = next(iter(d["hypotheses"]["opening_types"]))
    d["hypotheses"]["opening_types"][key] = {"kind": "window"}


def _gap_span_grows_a_third_number(d):
    """⭐ A three-element "interval" is a malformed element, ⛔ not a longer one."""
    for face in d["observations"]["face_lines"]:
        if face["gaps"]:
            face["gaps"][0]["span_m"] = [*face["gaps"][0]["span_m"], 9.99]
            return
    raise AssertionError("fixture carries no gap to corrupt")


def _face_line_support_loses_one_end(d):
    d["observations"]["face_lines"][0]["support_cols_px"] = [
        d["observations"]["face_lines"][0]["support_cols_px"][0]
    ]


def _ink_profile_loses_span_ratio(d):
    for face in d["observations"]["face_lines"]:
        if face["gaps"]:
            del face["gaps"][0]["ink_by_family"]["F0"]["span_ratio"]
            return
    raise AssertionError("fixture carries no gap to corrupt")


_MALFORMED_ELEMENTS = (
    _bucket_value_is_a_dict,
    _bucket_value_is_a_number,
    _bucket_is_a_list,
    _bucket_grows_an_untyped_sibling,
    _face_line_loses_its_id,
    _face_line_runs_become_a_string,
    _face_line_axis_is_a_world_axis,
    _pair_loses_face_b,
    _pair_spacing_arrives_as_text,
    _pairs_become_a_dict,
    _opening_candidate_loses_its_span,
    _opening_types_values_become_dicts,
    _gap_span_grows_a_third_number,
    _face_line_support_loses_one_end,
    _ink_profile_loses_span_ratio,
)


@pytest.mark.parametrize("corrupt", _MALFORMED_ELEMENTS, ids=lambda f: f.__name__)
def test_malformed_element_is_loud_and_used_to_be_silent(corrupt):
    """⭐⭐⭐ The headline. Real product, one element broken, three top-level
    keys still present, ``schema`` string still right."""
    doc = _load("sm25_2f_v2.json")
    corrupt(doc)

    # -- premise: the rule this dispatch replaced said YES to exactly this ---
    assert _detector_before_this_dispatch(doc), (
        "this input does not exercise the change: the OLD key-list rule already "
        "rejected it, so a red below would prove nothing"
    )
    assert doc["schema"] == SCHEMA
    assert all(k in doc for k in ("observations", "declarations", "hypotheses"))

    # -- the fix -----------------------------------------------------------
    decision = classify_vector_json(doc)
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is None
    assert SCHEMA in (decision.reason or ""), "the refusal must name what was declared"


@pytest.mark.parametrize("corrupt", _MALFORMED_ELEMENTS, ids=lambda f: f.__name__)
def test_malformed_element_is_named_by_the_producer_type(corrupt):
    """The classifier only says yes/no; the TYPE says which path is wrong.
    ⛔ Without this, "loud" would mean "refused for some reason"."""
    doc = _load("sm25_2f_v2.json")
    corrupt(doc)
    with pytest.raises(ValidationError) as exc:
        validate_as_drawn_plan(doc)
    locs = {".".join(str(p) for p in e["loc"]) for e in exc.value.errors()}
    assert locs, "a refusal with no location names nothing"
    assert any(loc.startswith(("observations", "hypotheses")) for loc in locs), locs


# =========================================================================== #
# 验收 2 -- the real products pass, and passing changes nothing about them
# =========================================================================== #
@pytest.mark.parametrize("name", _TRACKED)
def test_every_tracked_product_validates(name):
    validate_as_drawn_plan(_load(name))


@pytest.mark.parametrize("name", _TRACKED)
def test_validation_returns_the_same_object_untouched(name):
    """⭐ ``model_dump()`` would re-order keys, coerce numerics and drop the
    extras the envelope allows -- i.e. quietly rewrite the product while
    claiming to check it. Byte-identity has to be structural, ⛔ not hoped for."""
    doc = _load(name)
    before = copy.deepcopy(doc)
    out = validate_as_drawn_plan(doc)
    assert out is doc
    assert out == before
    assert json.dumps(out, indent=2) == json.dumps(before, indent=2)


# =========================================================================== #
# 验收 3 -- the producer really goes through it (⭐ neuter-sensitive)
# =========================================================================== #
class _FakeAxis:
    mm_per_px = 10.0

    def as_dict(self):
        return {"mm_per_px": 10.0}


class _FakeRuler:
    fx = _FakeAxis()
    fy = _FakeAxis()
    mm_per_px = 10.0
    x_zero = 0.0
    y_zero = 0.0
    tick_map: dict = {}


def _assemble(percept: dict) -> dict:
    """Call the real ``assemble`` with the smallest arguments it accepts.

    ⛔ Not a stand-in for ``assemble``: it IS ``assemble``. Only the inputs are
    minimal ([[lock-must-exercise-real-entry-point]]).
    """
    cfg = {
        "image": "x.png",
        "image_label": "1f",
        "chains": {},
        "declared_thickness_mm": [],
        "drawing_box": [0, 0, 10, 10],
    }
    pal = {"families": [], "achromatic_only": False, "unassigned_pct": 0.0}
    return A.assemble(cfg, percept, pal, {}, {}, _FakeRuler(), [], [], {},
                      [], "SELECTED", "note", [])


def test_assemble_accepts_an_honest_product():
    doc = _assemble({"non_wall_face_lines": {"L001": "callout text, not a wall"}})
    assert doc["schema"] == SCHEMA
    assert doc["hypotheses"]["non_wall_face_lines"] == {"L001": "callout text, not a wall"}


def test_assemble_refuses_to_emit_a_malformed_product():
    """⭐⭐ THE neuter probe. Delete ``validate_as_drawn_plan`` from
    ``assemble`` and this test goes red -- nothing else in the tree does.

    ⛔ It is not asserting that perception is validated (that would be a
    judgement about content); it asserts that a product whose bucket holds a
    non-reason cannot LEAVE the producer.
    """
    with pytest.raises(ValidationError):
        _assemble({"non_wall_face_lines": {"L001": {"reason": "structured, one day"}}})


def test_schema_value_has_exactly_one_definition():
    """``as_drawn_v2.SCHEMA`` re-exports ``schema.SCHEMA``; ``vector_contract``
    imports it from ``as_drawn_v2``. A second literal anywhere on that chain is
    a second definition that stops matching the day one of them moves."""
    import src.agent.reading.as_drawn.schema as S

    assert A.SCHEMA is S.SCHEMA
    src = Path("src/agent/reading/as_drawn/as_drawn_v2.py").read_text(encoding="utf-8")
    assert f'"{SCHEMA}"' not in src, "⛔ the value must not be re-stated here"


def test_the_axis_vocabulary_has_exactly_one_definition_too():
    """Same rule one level down: ``row``/``col`` is ``_plan_ink.Axis``, not two
    words re-spelled in the type."""
    from src.agent.reading.as_drawn._plan_ink import Axis
    from src.agent.reading.as_drawn.schema import FaceLineV2

    assert FaceLineV2.model_fields["axis"].annotation == Axis
    schema_src = Path("src/agent/reading/as_drawn/schema.py").read_text(encoding="utf-8")
    assert '"row"' not in schema_src and '"col"' not in schema_src


# =========================================================================== #
# 验收 4 -- how many face-disposition buckets, and on what evidence
# =========================================================================== #
def test_there_are_exactly_four_buckets_and_pairs_is_not_one_of_them():
    """⭐ The verdict wrote "五桶" without enumerating. Counted here against the
    products themselves: four ``dict[face_id, reason]`` buckets. The fifth
    accounting slot is ``pairs``, which is a different shape and is already
    named separately -- ⛔ counting it as a bucket would double-count it."""
    assert len(FACE_DISPOSITION_BUCKETS) == 4
    assert "pairs" not in FACE_DISPOSITION_BUCKETS

    typed_as_reason_buckets = {
        name
        for name, field in HypothesesV2.model_fields.items()
        if str(field.annotation) in ("dict[str, str]", "typing.Dict[str, str]")
    }
    assert typed_as_reason_buckets == set(FACE_DISPOSITION_BUCKETS)

    for name in _TRACKED:
        hyp = _load(name)["hypotheses"]
        present = {k for k, v in hyp.items() if isinstance(v, dict)
                   and all(isinstance(x, str) for x in v.values())
                   and k.endswith(("_face_lines", "_wall_faces", "_walls"))}
        assert present == set(FACE_DISPOSITION_BUCKETS), name


@pytest.mark.parametrize("name", _TRACKED)
def test_the_fifth_slot_is_pairs_measured_on_the_real_products(name):
    """The producer's own completeness invariant, restated on data: every face
    line is accounted for by one of FIVE slots -- the four buckets plus being
    half of a selected pair. This is the evidence for the count above."""
    doc = _load(name)
    hyp = doc["hypotheses"]
    assert hyp["pairs_status"] == "SELECTED", "premise: this product claims completeness"
    accounted: set[str] = {f for p in hyp["pairs"] for f in (p["face_a"], p["face_b"])}
    by_bucket_only = set().union(*(set(hyp[b]) for b in FACE_DISPOSITION_BUCKETS))
    every_face = {f["id"] for f in doc["observations"]["face_lines"]}

    assert every_face - (accounted | by_bucket_only) == set(), "five slots must cover all"
    assert every_face - by_bucket_only, (
        f"{name}: the four buckets alone already cover every face line, so this "
        "product cannot show that `pairs` is a needed slot"
    )


# =========================================================================== #
# 验收 5 -- the deferred channels are declared, not swallowed
# =========================================================================== #
def _deferred_fields() -> set[str]:
    """Dotted paths of every field the model declares but does not check."""
    found = set()
    for prefix, model in (("", AsDrawnPlanV2),
                          ("observations", ObservationsV2),
                          ("hypotheses", HypothesesV2)):
        for name, field in model.model_fields.items():
            if (field.description or "").startswith("deferred"):
                found.add(f"{prefix}.{name}" if prefix else name)
    return found


def test_deferred_roster_matches_the_model_exactly():
    """⭐ ⛔ Not an ``extra="allow"`` shrug: every unchecked channel is a named
    field, and the roster and the model are locked to each other so the answer
    to "what is not checked yet" cannot drift into prose."""
    assert set(DEFERRED_CHANNELS) == _deferred_fields()
    assert len(DEFERRED_CHANNELS) == len(set(DEFERRED_CHANNELS))


def test_the_in_scope_families_are_not_on_the_deferred_roster():
    """The trim is "wall + opening families". If one of them ever slid onto the
    deferred roster the module would still look complete."""
    in_scope = {"observations.face_lines", "hypotheses.pairs",
                "hypotheses.pair_candidates", "hypotheses.opening_candidates",
                "hypotheses.opening_types",
                *(f"hypotheses.{b}" for b in FACE_DISPOSITION_BUCKETS)}
    assert in_scope.isdisjoint(set(DEFERRED_CHANNELS))


def test_every_in_scope_node_forbids_unknown_keys():
    """⛔ ``extra="allow"`` on a node would make every teeth test above vacuous
    for that node."""
    for model in (ObservationsV2, HypothesesV2):
        assert model.model_config.get("extra") == "forbid", model
        assert model.model_config.get("strict") is True, model
    assert AsDrawnPlanV2.model_config.get("extra") == "allow", (
        "the ENVELOPE is open on purpose -- see the F-97 ambiguity lock below"
    )


# =========================================================================== #
# 验收 6 -- the disposition is untouched (⛔ this dispatch does not wire it)
# =========================================================================== #
def test_as_drawn_is_still_known_but_not_consumed():
    spec = next(s for s in CONTRACTS if s.contract_id == CONTRACT_AS_DRAWN_PLAN)
    assert spec.disposition is Disposition.KNOWN_NOT_CONSUMED
    assert classify_vector_json(_load("sm25_2f_v2.json")).disposition is (
        Disposition.KNOWN_NOT_CONSUMED
    )


def test_no_new_contract_became_consumable():
    consuming = {s.contract_id for s in CONTRACTS if s.disposition is Disposition.CONSUME}
    assert consuming == {CONTRACT_READING_VIEW_LEGACY}


# =========================================================================== #
# The two F-97 behaviours this change could have broken. ⭐ Pinned here on
# purpose: both were checked deliberately, ⛔ neither was left to luck.
# =========================================================================== #
def test_the_declared_skeleton_is_now_a_loud_unknown():
    """⭐ NF-1 (2026-09-01), FLIPPED from ``..._is_still_recognised``.

    The boundary moved on purpose.  ``observations.face_lines`` is now required
    (no default), and the producer's ``assemble()`` writes that key
    unconditionally -- so the empty ``{observations:{}, declarations:{},
    hypotheses:{}}`` skeleton is something the producer CANNOT emit.  It is
    hand-made or corrupt, and ``vector_contract``'s BLK-A rule turns it into a
    LOUD unknown that names the declared schema.  ⛔ NOT recognised as
    ``as_drawn_plan`` any more, ⛔ NOT silently dropped.
    ⚠️ This teeth is on the PRESENCE of the key -- an honest EMPTY reading
    ``{observations: {face_lines: []}}`` is a different thing and is STILL
    recognised (locked in ``test_f97_vector_contract`` NF-1 tests)."""
    skeleton = {"schema": SCHEMA, "observations": {}, "declarations": {},
                "hypotheses": {}}
    decision = classify_vector_json(skeleton)
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is None
    assert SCHEMA in (decision.reason or ""), "the refusal must name what was declared"


def test_an_empty_skeleton_hybrid_that_looks_legacy_is_loud_unknown_not_consumed():
    """⭐ NF-1 (2026-09-01), FLIPPED from ``..._is_still_ambiguous_not_consumed``.

    ⭐ The invariant that MATTERS is unchanged and still holds: a file that also
    looks legacy is ⛔ NOT consumed (F-97 stays shut).  What changed is the
    PATH: with ``face_lines`` required, the empty-skeleton half legitimately
    fails the as-drawn type, so this is no longer a genuine double match -- it is
    a malformed declaration and comes out of BLK-A as a loud unknown, ⛔ never
    pasted into the correction prompt.  The genuine as-drawn+legacy double match
    (a REAL product plus ``strokes``) still returns AMBIGUOUS and is locked in
    ``test_f97_vector_contract`` (R2 / R5 / double-match), now carrying one real
    face line."""
    hybrid = {"schema": SCHEMA, "observations": {}, "declarations": {},
              "hypotheses": {},
              "strokes": [{"id": "s1", "pen": "wall", "geometry": {}}]}
    decision = classify_vector_json(hybrid)
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is not Disposition.CONSUME
    assert "malformed declaration" in (decision.reason or "")


def test_a_type_failure_never_downgrades_a_file_into_being_consumed():
    """⭐ The direction that matters. A malformed as-drawn product that ALSO
    looks like a legacy view must not become consumable now that the as-drawn
    detector can say no. ``classify_vector_json``'s BLK-A rule is what holds
    this, and this asserts it on a real malformed product."""
    doc = _load("sm25_2f_v2.json")
    _bucket_value_is_a_number(doc)
    doc["strokes"] = [{"id": "s1", "pen": "wall", "geometry": {}}]
    decision = classify_vector_json(doc)
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is not Disposition.CONSUME


# =========================================================================== #
# N-1 (cross-family, 2026-08-30): the sixth ``counterface_state``.
# =========================================================================== #
def test_n1_the_sixth_counterface_state_exists_only_as_prose_today():
    """⭐ sm25 2F ``L012``: the counterface ink IS there and the reader dropped
    it -- ``ink_present_unpromoted``. Today the only carrier is a sentence, so
    it is structurally indistinguishable from any other lone-face reason.

    ⛔ This module does NOT invent a structured slot for it (an unexercised
    union member with zero real instances is where defects hide, and the state
    belongs to module 2's evidence contract). What it does is pin the instance,
    so the day a producer emits structure there, the type has to be changed on
    purpose instead of absorbing it silently.
    """
    lone = _load("sm25_2f_v2.json")["hypotheses"]["unpaired_wall_faces"]
    assert set(lone) == {"L012"}
    reason = lone["L012"]
    assert isinstance(reason, str)
    assert "ink is there" in reason and "column 655" in reason, (
        "the evidence for the sixth state lives in free prose -- if this wording "
        "changed, re-read N-1 before touching the type"
    )

    # ⛔ and a structured value there is NOT quietly accepted today
    doc = _load("sm25_2f_v2.json")
    doc["hypotheses"]["unpaired_wall_faces"]["L012"] = {
        "state": "ink_present_unpromoted", "witness_col_px": 655,
    }
    with pytest.raises(ValidationError):
        validate_as_drawn_plan(doc)
