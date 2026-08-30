"""②-2 module 1 — the as-drawn producer owns its type, and the detector uses it.

Dispatch: ``AI_agent/logs/reviews/request/2026-08-30_o22m1_as_drawn_producer_types_dispatch.md``

What was wrong before 2026-08-30
--------------------------------
``as_drawn_v2.assemble()`` returned a bare ``dict`` and the only thing that ever
inspected an as-drawn product was ``vector_contract``'s detector, whose whole
body was (verbatim, ``820caf0``)::

    lambda raw: _is_declared(raw, AS_DRAWN_PLAN_SCHEMA)
    and _has_keys(raw, "observations", "declarations", "hypotheses"),

⇒ schema string right + three top-level keys present = "recognised product",
whatever the buckets held.  ``validator/checks/as_drawn.py``'s eleven gt-free
gates are **not** wired into ``run_pipeline`` (``affected_tests_rules.yaml``
says so in as many words), so nothing else covered for it either.

⭐ The teeth group below is therefore built to answer the one question that
matters: **would these inputs have passed before?**  Each mutant is asserted
green under a frozen transcription of the old predicate and red under the new
one, in the same test — because "it is red today" alone is compatible with a
gate that is red at everything ([[gate-with-only-negative-assertions-is-unobservable]]).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

import src.agent.reading.as_drawn.as_drawn_v2 as A
from src.agent.pipeline import _build_correction_messages
from src.agent.reading.as_drawn.schema import (
    PERCEPTION_BUCKET_FIELDS,
    AsDrawnPlanContractError,
    AsDrawnPlanV2,
    Deferred,
    HypothesesV2,
    deferred_channels,
    explain_rejection,
    validate_plan_document,
)
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_PLAN,
    CONTRACT_UNKNOWN,
    MALFORMED_DECLARED_PREFIX,
    UNEXPECTED_FAILURE_PREFIX,
    Disposition,
    UnconsumableVectorFile,
    classify_vector_json,
)

# The three real as-drawn products in the tree.  ⭐ Real, not synthetic: the
# mutants below are one edit away from a product that a reader actually
# produced, so "the buckets do not have the right element shape" is measured
# against reality rather than against a fixture written to be caught.
_OUT = Path("AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out")
_REAL_PRODUCTS = ("sm24_1f_v2.json", "sm25_1f_v2.json", "sm25_2f_v2.json")


def _real(name: str) -> dict:
    path = _OUT / name
    # ⛔ Not `skipif`: a vanished fixture must be a red test, never a silent
    # pass ([[absent-file-read-as-passing-check]]).
    assert path.is_file(), f"tracked as-drawn product missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _pre_2026_08_30_detector(raw: dict) -> bool:
    """Frozen transcription of the detector this dispatch replaced (``820caf0``).

    ⚠️ Deliberately a second implementation, and deliberately never used as a
    gate: its only job is to be the "before" reading in the same process as the
    "after" one, so that the teeth claim is a measurement rather than a memory.
    """
    return raw.get("schema") == A.SCHEMA and all(
        k in raw for k in ("observations", "declarations", "hypotheses")
    )


# --------------------------------------------------------------------------- #
# Mutants: schema string right, three top keys present, bucket ELEMENTS wrong.
# --------------------------------------------------------------------------- #
def _m_bucket_value_is_an_object(doc: dict) -> str:
    """⭐ The N-1 shape: someone structures the counterface story in place.

    sm25 2F's ``L012`` is a wall face whose counterface ink is present in the
    image and was dropped by the reader (F-86); the whole story lives in a free
    text reason.  A consumer that wanted ``counterface_state`` typed would be
    tempted to write exactly this.  ⛔ Changing the product's shape is module
    2's business, and until then it must not slip in unannounced."""
    doc["hypotheses"]["unpaired_wall_faces"] = {
        "L012": {"state": "ink_present_unpromoted", "reason": "F-86"}
    }
    return "unpaired_wall_faces"


def _m_pair_missing_a_face(doc: dict) -> str:
    doc["hypotheses"]["pairs"][0].pop("face_b")
    return "face_b"


def _m_pair_smuggles_geometry(doc: dict) -> str:
    """⛔ reading writes no centreline (batch guide, hard boundary)."""
    doc["hypotheses"]["pairs"][0]["centerline_m"] = 3.14
    return "centerline_m"


def _m_run_has_three_numbers(doc: dict) -> str:
    doc["observations"]["face_lines"][0]["runs_px"][0] = [10, 20, 30]
    return "runs_px"


def _m_span_has_one_number(doc: dict) -> str:
    doc["hypotheses"]["opening_candidates"][0]["span_m"] = [1.0]
    return "span_m"


def _m_opening_type_is_a_number(doc: dict) -> str:
    key = next(iter(doc["hypotheses"]["opening_types"]))
    doc["hypotheses"]["opening_types"][key] = 3
    return "opening_types"


def _m_axis_is_not_an_axis(doc: dict) -> str:
    doc["observations"]["face_lines"][0]["axis"] = "diagonal"
    return "axis"


def _m_measurement_is_a_string(doc: dict) -> str:
    """A number arriving as text: lax validation would coerce it silently."""
    doc["hypotheses"]["pair_candidates"][0]["spacing_m"] = "0.24"
    return "spacing_m"


def _m_face_line_loses_its_support(doc: dict) -> str:
    doc["observations"]["face_lines"][0].pop("support_cols_px")
    return "support_cols_px"


def _m_pairs_status_invented(doc: dict) -> str:
    doc["hypotheses"]["pairs_status"] = "PROBABLY_FINE"
    return "pairs_status"


_MUTANTS = (
    _m_bucket_value_is_an_object,
    _m_pair_missing_a_face,
    _m_pair_smuggles_geometry,
    _m_run_has_three_numbers,
    _m_span_has_one_number,
    _m_opening_type_is_a_number,
    _m_axis_is_not_an_axis,
    _m_measurement_is_a_string,
    _m_face_line_loses_its_support,
    _m_pairs_status_invented,
)


def _mutate(mutant, source: str = "sm25_2f_v2.json") -> tuple[dict, str]:
    doc = copy.deepcopy(_real(source))
    return doc, mutant(doc)


# --------------------------------------------------------------------------- #
# 验收 1 — teeth, and proof that the teeth are new
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("mutant", _MUTANTS, ids=lambda m: m.__name__[3:])
def test_malformed_bucket_was_accepted_before_and_is_refused_now(mutant):
    doc, offending = _mutate(mutant)

    assert _pre_2026_08_30_detector(doc), (
        "the mutant must be one the OLD detector accepted, otherwise this test "
        "proves nothing about what changed"
    )

    decision = classify_vector_json(doc)
    assert decision.contract_id != CONTRACT_AS_DRAWN_PLAN
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is None
    reason = decision.reason or ""
    assert reason.startswith(MALFORMED_DECLARED_PREFIX)
    assert offending in reason, "the refusal must name the field it choked on"
    assert UNEXPECTED_FAILURE_PREFIX not in reason, (
        "must be a reasoned verdict, ⛔ not the last-resort net standing in "
        "for the mechanism under test"
    )


def test_the_unmutated_real_products_are_still_recognised():
    """⭐ The other half of discriminating power: the gate must also say YES."""
    for name in _REAL_PRODUCTS:
        decision = classify_vector_json(_real(name))
        assert decision.contract_id == CONTRACT_AS_DRAWN_PLAN, name
        assert decision.disposition is Disposition.KNOWN_NOT_CONSUMED, name
        assert decision.reason is None, name


def test_malformed_bucket_fails_loudly_through_the_real_entry(tmp_path):
    """⛔ Not a discriminator-level assertion: the entry 1_correction calls."""
    doc, offending = _mutate(_m_bucket_value_is_an_object)
    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    (vdir / "sm25_2f_v2.json").write_text(json.dumps(doc), encoding="utf-8")
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    with pytest.raises(UnconsumableVectorFile) as exc:
        _build_correction_messages(vdir, "{}")
    msg = str(exc.value)
    assert "sm25_2f_v2.json" in msg
    assert MALFORMED_DECLARED_PREFIX in msg
    assert offending in msg


# --------------------------------------------------------------------------- #
# 验收 2 — the type is a gate, ⛔ never a normalizer
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", _REAL_PRODUCTS)
def test_real_products_pass_the_producer_type_unchanged(name, tmp_path):
    raw = (_OUT / name).read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    validate_plan_document(doc)
    # ⭐ Re-serialised through the producer's OWN writer — ⛔ not a second
    # json.dumps with hand-picked kwargs, which would compare this test's
    # opinion of the format against the tracked file rather than the
    # producer's ([[recompute-gate-must-mirror-producer-definition]]).
    out = tmp_path / name
    A.dump(doc, out)
    assert out.read_bytes() == raw


def test_validation_api_has_nothing_to_serialise():
    """⭐ NF-1's lesson, applied at the type layer: the wrong path does not exist.

    ``validate_plan_document`` returns ``None``, so a caller cannot write
    ``return validate_plan_document(doc)`` and quietly ship a model dump in
    place of the product.  ⛔ Prose forbidding it would not survive a rewrite;
    a return type does.
    """
    import inspect

    assert validate_plan_document(_real("sm25_1f_v2.json")) is None
    assert (
        inspect.signature(validate_plan_document).return_annotation == "None"
    ), "⛔ the moment this returns an object, byte-identity becomes a promise"


# --------------------------------------------------------------------------- #
# 验收 3 — the gate is really on the producer's exit (and it is removable)
# --------------------------------------------------------------------------- #
class _Fit:
    mm_per_px = 5.0

    def as_dict(self) -> dict:
        return {"mm_per_px": 5.0}


class _Ruler:
    def __init__(self) -> None:
        self.fx = _Fit()
        self.fy = _Fit()
        self.mm_per_px = 5.0
        self.x_zero = 0.0
        self.y_zero = 0.0
        self.tick_map: dict = {}


_CFG = {
    "image": "x.png",
    "image_label": "1f",
    "chains": {},
    "declared_thickness_mm": [240],
    "drawing_box": [0, 0, 10, 10],
}
_PAL = {"families": [], "achromatic_only": False, "unassigned_pct": 0.0}
_FACE_LINE = {
    "id": "L001",
    "axis": "col",
    "constant_world_axis": "x",
    "pos_px": 252,  # ⭐ an int on purpose — see the byte-identity test below
    "pos_m": 0.1,
    "support_cols_px": [247, 258],
    "edges_m": [-0.02, 0.28],
    "support_width_m": 0.3,
    "runs_px": [[150, 170]],
    "runs_m": [[19.47, 20.02]],
    "gaps": [],
    "ink_coverage_per_run": [1.0],
    "covered_px": 20,
    "support_px": 20,
}


def _assemble(percept: dict, face_lines: list | None = None) -> dict:
    return A.assemble(
        cfg=dict(_CFG),
        percept=percept,
        pal=_PAL,
        masks={"F0": np.zeros((3, 3), dtype=bool)},
        roles={"structure": "F0"},
        ruler=_Ruler(),
        face_lines=[dict(_FACE_LINE)] if face_lines is None else face_lines,
        candidates=[],
        by_face={},
        pairs=[],
        pairs_status="SELECTED",
        pairs_note="",
        opening_candidates=[],
    )


def test_assemble_refuses_to_emit_a_product_with_a_wrong_shaped_bucket():
    """⭐ The realistic failure: ``perception/<case>.json`` is written OUTSIDE
    this repo's control (today by hand, tomorrow by the reading model) and its
    buckets land in ``hypotheses`` verbatim.

    ⛔ This is the test that must go red if ``validate_plan_document(doc)`` is
    deleted from ``assemble`` — the lock has to be removable to be a lock
    ([[lock-must-exercise-real-entry-point]]).
    """
    with pytest.raises(AsDrawnPlanContractError) as exc:
        _assemble({"unpaired_wall_faces": {"L012": {"state": "ink_present"}}})
    assert "unpaired_wall_faces" in str(exc.value)


def test_assemble_returns_its_own_object_not_a_model_dump():
    """⭐ Byte-identity, locked at the seam where it could actually be lost.

    ``pos_px`` is typed ``float`` and handed in as the int ``252``.  Pydantic
    would render that ``252.0``; the product must still say ``252``, which is
    only true while ``assemble`` returns the dict it built.
    """
    doc = _assemble({})
    assert isinstance(doc, dict)
    assert type(doc["observations"]["face_lines"][0]["pos_px"]) is int


def test_assemble_accepts_a_well_formed_perception():
    doc = _assemble(
        {
            "non_wall_face_lines": {"L003": "stroke of a '240' callout text"},
            "unpaired_wall_faces": {"L012": "IS a wall face; counterface missing"},
            "_produced_by": "orchestrator, by hand",
        }
    )
    assert doc["schema"] == A.SCHEMA
    assert explain_rejection(doc) is None


# --------------------------------------------------------------------------- #
# 验收 4 — how many perception buckets there are, and why
# --------------------------------------------------------------------------- #
def test_there_are_exactly_four_perception_buckets():
    """⭐ FOUR, not the "五桶" of the cut — the reasoning is in the module
    docstring of ``reading/as_drawn/schema.py``.  The check below is the
    mechanical half of it: a bucket is a face-id-keyed ``dict[str, str]`` in
    ``hypotheses``, and there are four of those.
    """
    assert PERCEPTION_BUCKET_FIELDS == (
        "non_wall_face_lines",
        "unpaired_wall_faces",
        "solid_band_walls",
        "ambiguous_face_lines",
    )
    typed_as_buckets = tuple(
        name
        for name, field in HypothesesV2.model_fields.items()
        if field.annotation == dict[str, str]
    )
    assert typed_as_buckets == PERCEPTION_BUCKET_FIELDS
    # ⛔ the design draft §4.3 rules the tempting fifth out by name:
    # "pair_candidates 是代码枚举的候选关系图，不是第五或第七种墙".
    assert "pair_candidates" not in PERCEPTION_BUCKET_FIELDS


@pytest.mark.parametrize("name", _REAL_PRODUCTS)
def test_real_products_carry_those_four_buckets_and_no_other(name):
    """⭐ Measured on the products, ⛔ not read off the guide's table.

    A bucket accounts for a FACE LINE, so its keys are face-line ids.  That is
    the discrimination that keeps ``opening_types`` out: it is also a
    ``dict[str, str]``, but it is keyed by gap-candidate id (``L001g0``), and a
    counter that only looked at value types would have made it a fifth bucket.
    """
    doc = _real(name)
    face_ids = {f["id"] for f in doc["observations"]["face_lines"]}
    hyp = doc["hypotheses"]
    face_id_keyed = tuple(
        k
        for k, v in hyp.items()
        if isinstance(v, dict)
        and all(isinstance(x, str) for x in v.values())
        and set(v) <= face_ids
    )
    assert face_id_keyed == PERCEPTION_BUCKET_FIELDS, name

    # The premise of the discrimination above, asserted rather than assumed:
    # `opening_types` really is a non-empty `dict[str, str]` that is NOT keyed
    # by face lines, so it is excluded by measurement, not by a hard-coded name.
    opening_types = hyp["opening_types"] or {}
    assert opening_types, name
    assert all(isinstance(v, str) for v in opening_types.values()), name
    assert not set(opening_types) <= face_ids, name


def test_the_producer_accounts_for_a_face_line_through_five_sources():
    """⭐ Where "五" most likely came from, recorded so nobody re-derives it.

    ``select_pairs`` counts a face line as accounted for through the four
    buckets **plus the faces named by ``pairs`` itself** — five sources of
    accounting, four buckets.
    """
    import inspect

    src = inspect.getsource(A.select_pairs)
    read_from_perception = tuple(
        f for f in PERCEPTION_BUCKET_FIELDS if f'percept.get("{f}"' in src
    )
    assert read_from_perception == PERCEPTION_BUCKET_FIELDS
    assert 'p["face_a"], p["face_b"]' in src, (
        "the fifth accounting source is `pairs`, ⛔ not a fifth bucket"
    )


# --------------------------------------------------------------------------- #
# 验收 5 — every deferred channel is declared, and the list is derived
# --------------------------------------------------------------------------- #
def test_deferred_channels_are_enumerable_and_each_says_why():
    channels = deferred_channels()
    assert channels, "a version that defers nothing should say so by being empty"
    pointers = [p for p, _ in channels]
    assert len(set(pointers)) == len(pointers)
    for pointer, why in channels:
        assert pointer.startswith("/")
        assert len(why) > 20, f"{pointer} has no usable reason"
    assert "/ledger" in pointers
    assert "/hypotheses/family_roles" in pointers


def test_nothing_is_deferred_by_silence():
    """⛔ No ``Any`` anywhere in the tree without a ``Deferred`` mark, and ⛔ no
    ``extra="allow"`` quietly standing in for "we have not typed this yet"."""
    from pydantic import BaseModel

    seen: set[type] = set()
    unmarked: list[str] = []

    def walk(model: type[BaseModel], prefix: str) -> None:
        if model in seen:
            return
        seen.add(model)
        assert model.model_config.get("extra") in {"forbid", "ignore"}, (
            f"{model.__name__} must not carry extra='allow'"
        )
        for name, field in model.model_fields.items():
            pointer = f"{prefix}/{field.alias or name}"
            marked = any(isinstance(m, Deferred) for m in field.metadata)
            from typing import Any as _Any

            if field.annotation is _Any and not marked:
                unmarked.append(pointer)
            for sub in _nested(field.annotation):
                walk(sub, pointer)

    def _nested(annotation) -> list[type]:
        from typing import get_args

        from pydantic import BaseModel as _BM

        if isinstance(annotation, type) and issubclass(annotation, _BM):
            return [annotation]
        out: list[type] = []
        for arg in get_args(annotation):
            out.extend(_nested(arg))
        return out

    walk(AsDrawnPlanV2, "")
    assert not unmarked, f"untyped and unexplained: {unmarked}"


# --------------------------------------------------------------------------- #
# 验收 6 — ⛔ this dispatch does NOT wire as-drawn into correction
# --------------------------------------------------------------------------- #
def test_as_drawn_is_still_known_not_consumed():
    from src.agent.reading.vector_contract import CONTRACTS

    (spec,) = [s for s in CONTRACTS if s.contract_id == CONTRACT_AS_DRAWN_PLAN]
    assert spec.disposition is Disposition.KNOWN_NOT_CONSUMED, (
        "⛔ pointing this at an adapter is module 3, not module 1"
    )


# --------------------------------------------------------------------------- #
# N-1 — the debt this type deliberately does not settle
# --------------------------------------------------------------------------- #
def test_l012_counterface_story_is_still_only_free_text():
    """⭐ Anchors the cross-family finding N-1 on the real product it came from.

    sm25 2F's ``L012`` is the third of the three products module 1 had to cover,
    and it is the one that proves ``counterface_state``'s two-value enum is not
    enough: the counterface's ink IS in the image (column 655 carries 170 px)
    and the reader dropped it (F-86).  Today that fact exists **only** inside a
    free-text reason, and this type keeps it that way on purpose — ⛔ module 1
    must not invent a structured counterface field, and ⛔ nothing may parse the
    prose into one.
    """
    reason = _real("sm25_2f_v2.json")["hypotheses"]["unpaired_wall_faces"]["L012"]
    assert isinstance(reason, str)
    assert "F-86" in reason
    fields = set(HypothesesV2.model_fields)
    assert not [f for f in fields if "counterface" in f or "state" in f], (
        "a typed counterface state belongs to module 2's evidence contract"
    )
