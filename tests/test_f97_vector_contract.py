"""F-97: 1_correction consumes only declared contracts; undeclared shapes fail loudly.

Before this, `discover_vector_files` sorted `0_reading/*.json` into plans /
elevations / **others** and the correction prompt pasted every one verbatim, so a
JSON of any contract reached the model as untyped text past every reading gate.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.pipeline import _build_correction_messages, discover_vector_files
from src.agent.reading.as_drawn.as_drawn_v2 import SCHEMA as PRODUCER_AS_DRAWN_SCHEMA
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_ELEVATION_V0,
    CONTRACT_AS_DRAWN_PLAN,
    CONTRACT_AS_DRAWN_PLAN_V0,
    CONTRACT_READING_VIEW_LEGACY,
    CONTRACT_STAGE_CHECK_REPORT,
    CONTRACT_UNKNOWN,
    Disposition,
    UnconsumableVectorFile,
    classify_vector_dir,
    classify_vector_json,
    ledger_for,
)

_SM25_R0 = Path(
    "case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0/0_reading"
)


def _legacy_view(**extra) -> dict:
    view = {
        "image_label": "1f",
        "image_kind": "plan",
        "strokes": [
            {"id": "S1", "pen": "wall", "points": [[0.0, 0.0], [1.0, 0.0]]},
        ],
    }
    view.update(extra)
    return view


def _write(d: Path, name: str, payload: dict) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# B1' — the contract in production today is recognized, and consumed unchanged
# --------------------------------------------------------------------------- #
def test_b1_real_sm25_reading_products_are_all_legacy_and_all_consumed():
    names = discover_vector_files(_SM25_R0)
    assert len(names) == 6, names
    decision = classify_vector_dir(_SM25_R0, names)
    assert decision.consumed == names, "byte-identical prompt requires identical order"
    assert {r.contract_id for r in decision.rows} == {CONTRACT_READING_VIEW_LEGACY}


def test_b1_prompt_bytes_unchanged_for_a_legacy_only_dir(tmp_path):
    """⭐ B1' is the easiest criterion to fake green: a discriminator that shrugged
    ("can't tell ⇒ legacy") would keep the defect intact and still pass a
    "nothing crashed" check. So compare the assembled prompt BYTES."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(
        vdir,
        "East_view.json",
        _legacy_view(image_label="East", image_kind="elevation"),
    )
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    names = discover_vector_files(vdir)
    expected = "".join(
        f"\n[reading vector] {n}:\n```json\n"
        f"{(vdir / n).read_text(encoding='utf-8').strip()}\n```\n"
        for n in names
    )
    _system, human = _build_correction_messages(vdir, "{}")
    assert expected in human
    assert classify_vector_dir(vdir, names).consumed == names


# --------------------------------------------------------------------------- #
# B2' — an undeclared shape fails loudly AND names the file
# --------------------------------------------------------------------------- #
def test_b2_unknown_contract_raises_and_names_the_file(tmp_path):
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "mystery.json", {"hello": 1})
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    with pytest.raises(UnconsumableVectorFile) as exc:
        _build_correction_messages(vdir, "{}")
    msg = str(exc.value)
    assert "mystery.json" in msg, "the offending file must be named"
    assert "unknown contract" in msg
    assert "hello" in msg, "the reason should show what it actually saw"


def test_b2_unknown_is_never_silently_dropped(tmp_path):
    """⛔ Silent skip is F-64's shape: indistinguishable downstream from
    'the file was never there'."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "mystery.json", {"hello": 1})
    with pytest.raises(UnconsumableVectorFile):
        classify_vector_dir(vdir, discover_vector_files(vdir))


def test_b2_empty_object_is_unknown_not_legacy():
    """⚠️ ReadingView is extra='allow' with every field defaulted, so it
    validates `{}`. 'Parses as ReadingView' alone would recognize anything."""
    assert classify_vector_json({}).contract_id == CONTRACT_UNKNOWN


def test_b2_non_object_json_is_unknown():
    assert classify_vector_json([1, 2, 3]).contract_id == CONTRACT_UNKNOWN


# --------------------------------------------------------------------------- #
# B3' — as-drawn is KNOWN but NOT CONSUMED (a third behaviour, not the other two)
# --------------------------------------------------------------------------- #
def test_b3_as_drawn_plan_is_known_but_not_consumed():
    raw = {
        "schema": PRODUCER_AS_DRAWN_SCHEMA,
        "image": "x.png",
        "image_label": "1f",
        "observations": {},
        "declarations": {},
        "hypotheses": {},
        "ledger": {},
    }
    decision = classify_vector_json(raw)
    assert decision.contract_id == CONTRACT_AS_DRAWN_PLAN
    assert decision.disposition is Disposition.KNOWN_NOT_CONSUMED


def test_b3_as_drawn_raises_and_says_known_not_unknown(tmp_path):
    """⛔ Not pasted as `others`, ⛔ not 'pretend we don't recognize it'.
    When the reading/correction unification lands, 'not wired yet' and 'never
    heard of it' must stay tellable apart."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(
        vdir,
        "sm25_1f_v2.json",
        {
            "schema": PRODUCER_AS_DRAWN_SCHEMA,
            "observations": {},
            "declarations": {},
            "hypotheses": {},
        },
    )
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    with pytest.raises(UnconsumableVectorFile) as exc:
        _build_correction_messages(vdir, "{}")
    msg = str(exc.value)
    assert "sm25_1f_v2.json" in msg
    assert "no wire for it" in msg and "NOT unknown" in msg
    assert "unknown contract" not in msg


def test_b3_as_drawn_schema_value_comes_from_its_producer():
    """⭐ The value is imported from `as_drawn_v2.SCHEMA`, never copied. A literal
    here would be a second definition that stops matching the day the producer's
    value changes -- which is exactly how this dispatch's own anchor went stale
    (it named the retired `as_drawn_plan_v0`)."""
    import inspect

    import src.agent.reading.vector_contract as vc

    src = inspect.getsource(vc)
    assert "from src.agent.reading.as_drawn.as_drawn_v2 import SCHEMA" in src
    assert '"as_drawn_plan_v2"' not in src, "⛔ the live value must not be a literal"
    assert vc.AS_DRAWN_PLAN_SCHEMA == PRODUCER_AS_DRAWN_SCHEMA


def test_b3_historical_as_drawn_prototypes_are_known_contracts():
    plan_v0 = {
        "schema": "as_drawn_plan_v0",
        "wall_bands": [],
        "dimension_witnesses": [],
    }
    elev_v0 = {
        "schema": "as_drawn_elevation_v0",
        "openings": [],
        "structure_lines": [],
    }
    assert classify_vector_json(plan_v0).contract_id == CONTRACT_AS_DRAWN_PLAN_V0
    assert classify_vector_json(elev_v0).contract_id == CONTRACT_AS_DRAWN_ELEVATION_V0
    for raw in (plan_v0, elev_v0):
        assert classify_vector_json(raw).disposition is Disposition.KNOWN_NOT_CONSUMED


# --------------------------------------------------------------------------- #
# B3'' — check-report sidecars: excluded AND named (⛔ not red, ⛔ not silent)
# --------------------------------------------------------------------------- #
def _sidecar() -> dict:
    return {
        "stage": "0_reading",
        "results": [],
        "report_schema_version": "1",
        "artifact_hash": "abc",
        "attempt_hash": "def",
        "capability_profile": "rectangular",
    }


def test_b3_check_report_sidecar_is_excluded_not_raised(tmp_path):
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "1f_view_checks.json", _sidecar())
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    names = discover_vector_files(vdir)
    assert "1f_view_checks.json" in names, "the old code really did pick this up"
    decision = classify_vector_dir(vdir, names)
    assert decision.consumed == ["1f_view.json"]

    _system, human = _build_correction_messages(vdir, "{}")
    assert "1f_view_checks.json" not in human
    assert "report_schema_version" not in human


def test_b3_excluded_sidecar_is_named_in_the_ledger(tmp_path):
    """⛔ Not a silent skip: F-64's shape is 'nobody can tell it happened'.
    Exclusion is only legitimate because the ledger names the file."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "1f_view_checks.json", _sidecar())

    ledger = ledger_for(vdir, discover_vector_files(vdir))
    rows = {r["file"]: r for r in ledger["files"]}
    assert rows["1f_view_checks.json"]["contract"] == CONTRACT_STAGE_CHECK_REPORT
    assert rows["1f_view_checks.json"]["disposition"] == "exclude"
    assert rows["1f_view_checks.json"]["reason"]
    assert rows["1f_view.json"]["disposition"] == "consume"
    assert ledger["counts"] == {"consume": 1, "exclude": 1}


def test_b3_ledger_is_written_into_the_run_meta_dir(tmp_path):
    from src.agent.pipeline import _write_vector_contract_ledger

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "1f_view_checks.json", _sidecar())
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()

    path = _write_vector_contract_ledger(vdir, stage_dir)
    assert path == tmp_path / "_run" / "reading_vector_contract_ledger.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    assert ledger["consumed"] == ["1f_view.json"]


def test_b3_ledger_is_filed_even_when_classification_fails(tmp_path):
    """A run that fails classification must still leave a readable record."""
    from src.agent.pipeline import _write_vector_contract_ledger

    vdir = tmp_path / "0_reading"
    _write(vdir, "mystery.json", {"hello": 1})
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()

    path = _write_vector_contract_ledger(vdir, stage_dir)
    ledger = json.loads(path.read_text(encoding="utf-8"))
    assert ledger["files"][0]["file"] == "mystery.json"
    assert ledger["files"][0]["contract"] == CONTRACT_UNKNOWN


# --------------------------------------------------------------------------- #
# B3''' — two contracts at once is an AMBIGUITY, ⛔ never first-match-wins
# --------------------------------------------------------------------------- #
def test_b3_double_match_reports_ambiguity_instead_of_picking_one():
    hybrid = {
        "schema": PRODUCER_AS_DRAWN_SCHEMA,
        "observations": {},
        "declarations": {},
        "hypotheses": {},
        # ...and simultaneously a valid legacy view
        "strokes": [{"id": "S1", "pen": "wall", "points": [[0.0, 0.0], [1.0, 0.0]]}],
    }
    decision = classify_vector_json(hybrid)
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is None
    assert "AMBIGUOUS" in (decision.reason or "")
    assert CONTRACT_READING_VIEW_LEGACY in decision.reason
    assert CONTRACT_AS_DRAWN_PLAN in decision.reason


def test_b3_ambiguous_file_fails_loudly(tmp_path):
    vdir = tmp_path / "0_reading"
    _write(
        vdir,
        "1f_view.json",
        {
            "schema": PRODUCER_AS_DRAWN_SCHEMA,
            "observations": {},
            "declarations": {},
            "hypotheses": {},
            "strokes": [
                {"id": "S1", "pen": "wall", "points": [[0.0, 0.0], [1.0, 0.0]]}
            ],
        },
    )
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    with pytest.raises(UnconsumableVectorFile) as exc:
        _build_correction_messages(vdir, "{}")
    assert "AMBIGUOUS" in str(exc.value)


# --------------------------------------------------------------------------- #
# The legacy signature must NOT be the induced key list that the dispatch
# originally proposed: `dimensions` is absent from 6 real historical products.
# --------------------------------------------------------------------------- #
def test_legacy_view_without_dimensions_is_still_legacy():
    raw = {
        "image_label": "1f",
        "image_kind": "plan",
        "scale_origin": {},
        "strokes": [{"id": "S1", "pen": "wall", "points": [[0.0, 0.0], [1.0, 0.0]]}],
        "uncaptured_visual_elements": [],
        "facade_axis_note": "n",
    }
    assert "dimensions" not in raw
    assert classify_vector_json(raw).contract_id == CONTRACT_READING_VIEW_LEGACY


@pytest.mark.parametrize(
    "path",
    sorted(
        Path(
            "case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading"
        ).glob("*_view.json")
    ),
)
def test_real_historical_views_lacking_dimensions_are_recognized(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "dimensions" not in raw
    assert classify_vector_json(raw).contract_id == CONTRACT_READING_VIEW_LEGACY


# =========================================================================== #
# Cross-family rework (2026-08-27, GPT sol): three blockers, each with a lock
# that goes through a REAL entry point.
# =========================================================================== #
_STROKE = {"id": "S1", "pen": "wall", "points": [[0.0, 0.0], [1.0, 0.0]]}


def _unregistered_but_legacy_shaped() -> dict:
    """B-01's fixture: declares a contract nobody registered, yet still carries
    a `strokes` list that `ReadingView` happily validates."""
    return {
        "schema": "future_reading_contract_v99",
        "image_label": "1f",
        "image_kind": "plan",
        "strokes": [_STROKE],
    }


def _malformed_sidecar() -> dict:
    """B-02's fixture: the three key names are present, the types are junk."""
    return {
        "stage": 7,
        "results": "not-a-result-list",
        "report_schema_version": {"not": "a version"},
    }


# --- R1: unknown explicit schema must not fall back to legacy --------------- #
def test_r1_unregistered_schema_is_unknown_not_legacy():
    decision = classify_vector_json(_unregistered_but_legacy_shaped())
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is None
    assert "future_reading_contract_v99" in (decision.reason or "")


def test_r1_unregistered_schema_fails_loudly_through_the_real_entry(tmp_path):
    """⛔ Not a discriminator-level assertion: this goes through the same
    `_build_correction_messages` the production stage calls."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "2f_view.json", _unregistered_but_legacy_shaped())
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    with pytest.raises(UnconsumableVectorFile) as exc:
        _build_correction_messages(vdir, "{}")
    msg = str(exc.value)
    assert "2f_view.json" in msg
    assert "future_reading_contract_v99" in msg


def test_r1_unregistered_schema_never_reaches_the_prompt(tmp_path):
    """The point of B-01: such a file must not be pasted as untyped text."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _unregistered_but_legacy_shaped())
    assert classify_vector_dir.__module__  # sanity: real symbol, not a stub
    with pytest.raises(UnconsumableVectorFile):
        classify_vector_dir(vdir, discover_vector_files(vdir))


# --- R2: registered declaration + legacy structure is STILL ambiguous ------- #
def test_r2_registered_schema_plus_legacy_is_still_ambiguous():
    """⚠️ Regression guard for the B-01 fix: tightening 'declared ⇒ not legacy'
    must NOT collapse a genuine double match into one verdict."""
    hybrid = {
        "schema": PRODUCER_AS_DRAWN_SCHEMA,
        "observations": {},
        "declarations": {},
        "hypotheses": {},
        "strokes": [_STROKE],
    }
    decision = classify_vector_json(hybrid)
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert "AMBIGUOUS" in (decision.reason or "")
    assert CONTRACT_READING_VIEW_LEGACY in decision.reason
    assert CONTRACT_AS_DRAWN_PLAN in decision.reason


def test_r2_undeclared_legacy_still_recognized():
    """The other side of the same fix: no `schema` key ⇒ structural fallback
    still works, which is what keeps 328 historical products consumable."""
    assert (
        classify_vector_json({"image_kind": "plan", "strokes": [_STROKE]}).contract_id
        == CONTRACT_READING_VIEW_LEGACY
    )


# --- R3: malformed sidecar is loud; real sidecars still excluded ------------ #
def test_r3_malformed_sidecar_is_unknown_not_excluded():
    from src.validator.checks.schema import CheckReport

    with pytest.raises(Exception):
        CheckReport.model_validate(_malformed_sidecar())
    assert classify_vector_json(_malformed_sidecar()).contract_id == CONTRACT_UNKNOWN


def test_r3_malformed_sidecar_fails_loudly_through_the_real_entry(tmp_path):
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "1f_view_checks.json", _malformed_sidecar())
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    with pytest.raises(UnconsumableVectorFile) as exc:
        _build_correction_messages(vdir, "{}")
    assert "1f_view_checks.json" in str(exc.value)


def test_r3_every_real_sidecar_still_parses_as_the_producer_type():
    """Compatibility half of R3: the stricter path must not cost real artifacts.
    Measured over every `0_reading/*.json` in the tree, not a sample."""
    from src.validator.checks.schema import CheckReport

    sidecars = [
        p
        for d in Path(".").rglob("0_reading")
        if ".git" not in d.parts
        for p in sorted(d.glob("*.json"))
    ]
    excluded = []
    for path in sidecars:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if classify_vector_json(raw).contract_id == CONTRACT_STAGE_CHECK_REPORT:
            excluded.append(path)
            CheckReport.model_validate(raw)  # must not raise
    assert len(excluded) == 43, f"expected 43 real sidecars, got {len(excluded)}"


def test_r3_all_real_legacy_views_still_consumed():
    """R5's compatibility half, asserted rather than only measured by hand."""
    legacy = 0
    for d in Path(".").rglob("0_reading"):
        if ".git" in d.parts:
            continue
        for path in sorted(d.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            if classify_vector_json(raw).contract_id == CONTRACT_READING_VIEW_LEGACY:
                legacy += 1
    assert legacy == 328, f"expected 328 legacy views, got {legacy}"


# --- R4: real run_correction entry — named failure AND ledger on disk ------- #
@pytest.mark.parametrize(
    "name,payload,expect_in_message",
    [
        ("non_object", "[1, 2, 3]", "unknown contract"),
        ("invalid_json", "{not json at all", "invalid JSON"),
    ],
)
def test_r4_real_run_correction_names_the_file_and_files_the_ledger(
    tmp_path, name, payload, expect_in_message
):
    """B-03: the reading evidence preflight parses `*_view.json` and dies on a
    non-object with a bare AttributeError. Classification + ledger must come
    FIRST, so the failure is named and the ledger is on disk either way.
    ⛔ Goes through real `run_correction`, not the `_write_..._ledger` helper."""
    from src.agent.pipeline import run_correction

    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    (vdir / "1f_view.json").write_text(payload, encoding="utf-8")
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()

    with pytest.raises(UnconsumableVectorFile) as exc:
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert "1f_view.json" in str(exc.value)
    assert expect_in_message in str(exc.value)

    ledger_path = tmp_path / "_run" / "reading_vector_contract_ledger.json"
    assert ledger_path.exists(), (
        "F-c: a run that fails classification still needs a ledger"
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["files"][0]["file"] == "1f_view.json"
    assert ledger["files"][0]["contract"] == CONTRACT_UNKNOWN
    assert ledger["consumed"] == []


def test_r4_ledger_precedes_the_reading_evidence_preflight(tmp_path):
    """⭐ Ordering is the fix. Before it, this raised `AttributeError: 'list'
    object has no attribute 'get'` from the preflight with no ledger written."""
    from src.agent.pipeline import run_correction

    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    (vdir / "1f_view.json").write_text("[1, 2, 3]", encoding="utf-8")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()

    with pytest.raises(UnconsumableVectorFile):
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert (tmp_path / "_run" / "reading_vector_contract_ledger.json").exists()
