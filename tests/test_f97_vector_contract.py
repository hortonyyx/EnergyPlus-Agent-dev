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


# --------------------------------------------------------------------------- #
# N-B: the corpus-wide checks below assert INVARIANTS, not snapshot counts.
#
# They used to hard-assert `== 43` / `== 328`.  That froze the corpus at its
# 2026-08-27 size: the moment batch step ③ ("produce new-scheme artefacts")
# lands a single new `0_reading/*.json`, legitimate growth would read as
# failure, and the natural next move -- bump the number -- would gut these
# tests of any remaining meaning.  What they actually guard is unchanged by
# growth: no corpus file should be unclassifiable, and the two real shapes the
# corpus is known to contain (stage-check-report sidecars, legacy views) must
# stay recognized as themselves.
#
# ⛔⛔ The corpus root was also `Path(".")` -- cwd-dependent.  Converting the
# assertions to invariants makes an EMPTY corpus a silent, vacuous pass (every
# "for all files, P(file)" loop is trivially true over zero files) where the
# old exact-count form would at least have failed loudly (0 != 43).  Anchoring
# to the repo root closes the cwd hole; `_require_nonempty_corpus` closes the
# vacuous-pass hole, and is itself exercised against a real empty directory by
# test_n_b_empty_corpus_root_is_a_loud_red_not_a_silent_pass below.
# --------------------------------------------------------------------------- #
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _corpus_0_reading_json_files(root: Path = _REPO_ROOT) -> list[Path]:
    """Every `0_reading/*.json` file under ``root``, repo-anchored by default."""
    return [
        p
        for d in root.rglob("0_reading")
        if ".git" not in d.parts
        for p in sorted(d.glob("*.json"))
    ]


def _require_nonempty_corpus(files: list[Path]) -> list[Path]:
    """The shared guard: an empty corpus must fail loudly, never pass vacuously."""
    assert files, (
        "0_reading/*.json corpus is empty -- every invariant below would pass "
        "vacuously (a 'for all X in corpus' check over zero files is trivially true)"
    )
    return files


def test_n_b_empty_corpus_root_is_a_loud_red_not_a_silent_pass(tmp_path):
    """⭐ Proves the non-empty lower bound has teeth, per the dispatch's own
    requirement: point the corpus root at a directory with no 0_reading/
    anywhere under it and confirm the SAME guard the two tests below actually
    use really does fire, rather than letting an empty corpus vacuously pass."""
    files = _corpus_0_reading_json_files(tmp_path)
    assert files == [], "premise of this test is a genuinely empty corpus"
    with pytest.raises(AssertionError, match="corpus is empty"):
        _require_nonempty_corpus(files)


def test_r3_every_real_sidecar_still_parses_as_the_producer_type():
    """Compatibility half of R3: the stricter path must not cost real artifacts.
    Measured over every `0_reading/*.json` in the tree, not a sample.

    Invariant, not a snapshot count: every sidecar the classifier recognizes as
    a stage-check-report must actually validate as one (CheckReport must not
    raise) -- and the "excluded" set itself must be non-empty, or that
    per-file check would run zero times and pass vacuously regardless of
    whether the whole corpus is empty."""
    from src.validator.checks.schema import CheckReport

    sidecars = _require_nonempty_corpus(_corpus_0_reading_json_files())
    excluded = []
    for path in sidecars:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if classify_vector_json(raw).contract_id == CONTRACT_STAGE_CHECK_REPORT:
            excluded.append(path)
            CheckReport.model_validate(raw)  # must not raise
    assert excluded, (
        "no corpus file classified as a stage-check-report sidecar -- the "
        "CheckReport-parses check above ran zero times"
    )


def test_r3_all_real_legacy_views_still_consumed():
    """R5's compatibility half, asserted rather than only measured by hand.

    Invariant, not a snapshot count: "still consumed" means no corpus file
    falls to CONTRACT_UNKNOWN (the B-01 fix must not have tightened
    classification into rejecting a real historical shape), and that legacy
    views specifically remain a real, non-empty, recognized slice of the
    corpus rather than "however many there happen to be right now"."""
    files = _require_nonempty_corpus(_corpus_0_reading_json_files())
    unknown = []
    legacy = 0
    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        contract = classify_vector_json(raw).contract_id
        if contract == CONTRACT_UNKNOWN:
            unknown.append(path)
        elif contract == CONTRACT_READING_VIEW_LEGACY:
            legacy += 1
    assert not unknown, f"{len(unknown)} corpus file(s) fell to CONTRACT_UNKNOWN: {unknown[:10]}"
    assert legacy > 0, "no corpus file was recognized as a legacy view"


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


# =========================================================================== #
# Cross-family rework ROUND 2 (2026-08-27, GLM verdict): BLK-A / BLK-B / BLK-C.
#
# ⭐ What made round 1 insufficient was not that its fixes were wrong but that
# each one was scoped to the ONE input that had been shown to it. Every group
# below therefore locks the SHAPE CLASS -- all three registered values, several
# missing-key variants, several filesystem realities -- not the single fixture
# the reviewer happened to send.
# =========================================================================== #
_REGISTERED_VALUES = (
    PRODUCER_AS_DRAWN_SCHEMA,
    "as_drawn_plan_v0",
    "as_drawn_elevation_v0",
)

# Each registered value paired with a key set that is INCOMPLETE for its own
# contract -- the BLK-A shape: declared something real, then failed to be it.
_MALFORMED_DECLARATIONS = (
    (PRODUCER_AS_DRAWN_SCHEMA, {}),
    (PRODUCER_AS_DRAWN_SCHEMA, {"observations": {}}),
    (PRODUCER_AS_DRAWN_SCHEMA, {"observations": {}, "declarations": {}}),
    ("as_drawn_plan_v0", {}),
    ("as_drawn_plan_v0", {"wall_bands": []}),
    ("as_drawn_elevation_v0", {}),
    ("as_drawn_elevation_v0", {"openings": []}),
)

# The full key set for each registered value: declaration + key set + legacy
# structure is a GENUINE double match and must stay AMBIGUOUS.
_COMPLETE_DECLARATIONS = (
    (PRODUCER_AS_DRAWN_SCHEMA, {"observations": {}, "declarations": {}, "hypotheses": {}},
     CONTRACT_AS_DRAWN_PLAN),
    ("as_drawn_plan_v0", {"wall_bands": [], "dimension_witnesses": []},
     CONTRACT_AS_DRAWN_PLAN_V0),
    ("as_drawn_elevation_v0", {"openings": [], "structure_lines": []},
     CONTRACT_AS_DRAWN_ELEVATION_V0),
)


def _malformed_declared_view(schema_value: str, keys: dict) -> dict:
    """Declares a REGISTERED contract, misses its key set, still looks legacy."""
    return {
        "schema": schema_value,
        "image_label": "1f",
        "image_kind": "plan",
        **keys,
        "strokes": [_STROKE],
    }


# --- R5 (BLK-A): a registered value declared MALFORMED is unknown, not legacy #
@pytest.mark.parametrize("schema_value,keys", _MALFORMED_DECLARATIONS)
def test_r5_registered_but_malformed_declaration_is_unknown_not_legacy(
    schema_value, keys
):
    """⛔ Round 1 fixed only the *unregistered* half of 'declared ⇒ not legacy'.
    A file that declares `as_drawn_plan_v2` and then fails that contract's key
    set fell straight through to structural legacy recognition and was CONSUMED
    -- pasted verbatim into the prompt, which is F-97 in a new shape."""
    from src.agent.reading.vector_contract import UNEXPECTED_FAILURE_PREFIX

    decision = classify_vector_json(_malformed_declared_view(schema_value, keys))
    assert decision.contract_id == CONTRACT_UNKNOWN
    assert decision.disposition is None
    reason = decision.reason or ""
    assert schema_value in reason, "the refusal must name what was declared"
    assert UNEXPECTED_FAILURE_PREFIX not in reason, (
        "must be a reasoned verdict, ⛔ not the last-resort net standing in for it"
    )


@pytest.mark.parametrize("schema_value", _REGISTERED_VALUES)
def test_r5_registered_but_malformed_fails_loudly_through_the_real_entry(
    tmp_path, schema_value
):
    """⛔ Not a discriminator-level assertion: the same
    `_build_correction_messages` the production stage calls."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    _write(vdir, "2f_view.json", _malformed_declared_view(schema_value, {}))
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")

    with pytest.raises(UnconsumableVectorFile) as exc:
        _build_correction_messages(vdir, "{}")
    msg = str(exc.value)
    assert "2f_view.json" in msg
    assert schema_value in msg


@pytest.mark.parametrize("schema_value", _REGISTERED_VALUES)
def test_r5_registered_but_malformed_never_reaches_the_prompt(tmp_path, schema_value):
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _malformed_declared_view(schema_value, {}))
    with pytest.raises(UnconsumableVectorFile):
        classify_vector_dir(vdir, discover_vector_files(vdir))


@pytest.mark.parametrize("schema_value,keys,contract_id", _COMPLETE_DECLARATIONS)
def test_r5_complete_declaration_plus_legacy_is_still_ambiguous(
    schema_value, keys, contract_id
):
    """⛔⛔ The regression this fix has now nearly caused TWICE.

    Round 1 draft #1 wrote 'has a `schema` key ⇒ not legacy' and collapsed the
    genuine double match from AMBIGUOUS to a single verdict. The BLK-A rule is
    therefore guarded by `len(matches) == 1`: a file that declares a registered
    value AND satisfies that contract's key set AND matches legacy structure has
    two honest claims on it, and picking one silently is exactly what ⛔
    first-match-wins forbids. R2 covered `as_drawn_plan_v2` only; all three
    registered values are locked here."""
    hybrid = {"schema": schema_value, **keys, "strokes": [_STROKE]}
    decision = classify_vector_json(hybrid)
    assert decision.contract_id == CONTRACT_UNKNOWN
    reason = decision.reason or ""
    assert "AMBIGUOUS" in reason
    assert CONTRACT_READING_VIEW_LEGACY in reason
    assert contract_id in reason


def test_r5_registered_but_malformed_through_run_correction_leaves_a_ledger(tmp_path):
    from src.agent.pipeline import run_correction

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _malformed_declared_view(PRODUCER_AS_DRAWN_SCHEMA, {}))
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()

    with pytest.raises(UnconsumableVectorFile) as exc:
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert PRODUCER_AS_DRAWN_SCHEMA in str(exc.value)
    ledger = json.loads(
        (tmp_path / "_run" / "reading_vector_contract_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    assert ledger["consumed"] == []
    assert ledger["files"][0]["contract"] == CONTRACT_UNKNOWN


# --- R6 (BLK-B): the COMPOSITE entry files the ledger before any view is read #
_POISON_VIEWS = (
    ("non_object", b"[1, 2, 3]"),
    ("invalid_json", b"{not json at all"),
    ("invalid_utf8", b"\xff\xfe\x00"),
)


def _poisoned_run(tmp_path, payload: bytes, name: str = "1f_view.json"):
    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    (vdir / name).write_bytes(payload)
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    out_dir = tmp_path / "run"
    out_dir.mkdir()
    return vdir, out_dir


@pytest.mark.parametrize("label,payload", _POISON_VIEWS)
def test_r6_run_pipeline_artifacts_names_the_file_and_files_the_ledger(
    tmp_path, label, payload
):
    """⭐ BLK-B: round 1 hoisted the ledger above the evidence preflight INSIDE
    `run_correction` -- and the composite entry production actually calls had
    already parsed every `*_view.json` three times about forty lines upstream.
    `_preflight_vector_contracts`'s docstring claimed 'runs before ANY consumer'
    and that claim was the load-bearing part: entry LEVEL is part of 'any', not
    a detail below it. Same fixture, one entry point out, and neither F-b nor
    F-c existed."""
    from src.agent.pipeline import run_pipeline_artifacts

    vdir, out_dir = _poisoned_run(tmp_path, payload)
    with pytest.raises(UnconsumableVectorFile) as exc:
        run_pipeline_artifacts(vdir, "{}", out_dir=out_dir)
    assert "1f_view.json" in str(exc.value)

    ledger_path = out_dir / "_run" / "reading_vector_contract_ledger.json"
    assert ledger_path.exists(), "F-c: a failed run still owes a ledger"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["consumed"] == []
    assert ledger["files"][0]["file"] == "1f_view.json"
    assert ledger["files"][0]["contract"] == CONTRACT_UNKNOWN


def test_r6_run_pipeline_wrapper_covers_the_same_ground(tmp_path):
    """`run_pipeline` is a thin wrapper, but 'thin' is an assumption; the whole
    blocker was an entry point nobody had exercised."""
    from src.agent.pipeline import run_pipeline

    vdir, out_dir = _poisoned_run(tmp_path, b"[1, 2, 3]")
    with pytest.raises(UnconsumableVectorFile) as exc:
        run_pipeline(vdir, "{}", out_dir=out_dir)
    assert "1f_view.json" in str(exc.value)
    assert (out_dir / "_run" / "reading_vector_contract_ledger.json").exists()


@pytest.mark.parametrize(
    "label,make",
    [
        ("directory_named_view", lambda v: (v / "2f_view.json").mkdir()),
        ("dangling_symlink_view", lambda v: __import__("os").symlink(
            "/nonexistent/target", v / "2f_view.json")),
        ("directory_named_non_view", lambda v: (v / "backup.json").mkdir()),
    ],
)
def test_r6_filesystem_shapes_also_stop_at_the_composite_entry(tmp_path, label, make):
    """⭐ BLK-B x BLK-C: the two blockers meet here. These are not malformed
    JSON, they are ordinary directory entries, and on the composite entry each
    one died inside `load_reading_view` / the ledger writer with a bare
    `IsADirectoryError` -- no name, no ledger."""
    from src.agent.pipeline import run_pipeline_artifacts

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    make(vdir)
    out_dir = tmp_path / "run"
    out_dir.mkdir()

    with pytest.raises(UnconsumableVectorFile):
        run_pipeline_artifacts(vdir, "{}", out_dir=out_dir)
    assert (out_dir / "_run" / "reading_vector_contract_ledger.json").exists()
    # ⭐ "it raised and there is a ledger" is delivered by `run_correction`'s own
    # preflight too, so for a non-`_view` name that assertion alone stayed green
    # with the composite-entry hoist removed -- it locked an outcome that two
    # independent mechanisms both produce. The load-bearing claim is that
    # NOTHING DOWNSTREAM RAN: with the hoist gone, `:1368` computes the reading
    # report over the good view and files this artifact before anyone refuses.
    assert not (out_dir / "0_reading" / "reading_checks.json").exists(), (
        "the refusal must precede the reading report, not follow it"
    )


def test_r6_ledger_is_on_disk_before_every_view_consumer(tmp_path, monkeypatch):
    """⭐ The lock that does NOT depend on guessing a poison payload.

    Round 1's gap was found by an input nobody had tried; enumerating inputs is
    how it was missed in the first place. So measure the ORDERING directly: wrap
    each of the composite entry's three `*_view.json` consumers and assert the
    ledger was already on disk the moment each was first called. A fourth
    ⚠️ This spy names the three consumers that exist today, so it cannot see a
    FOURTH one added upstream tomorrow -- which is exactly how BLK-B survived
    round 1. The test below closes that half by intercepting the READ instead of
    the consumer; this one stays because it also pins the call ORDER and gives a
    readable failure when the order moves.

    Runs the v3 profile so the observation-reference catalog (v3-only, the third
    consumer) is exercised; it then fails on its own missing view manifest,
    which is fine -- the ordering assertions have already fired, and F-c says
    even that failure owes a ledger."""
    import src.agent.correction.window_sources as window_sources
    import src.agent.pipeline as pipeline
    import src.agent.reading as reading

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    out_dir = tmp_path / "run"
    out_dir.mkdir()
    ledger_path = out_dir / "_run" / "reading_vector_contract_ledger.json"
    seen: list[str] = []

    def _spy(label, fn):
        def wrapper(*args, **kwargs):
            seen.append(label)
            assert ledger_path.exists(), (
                f"{label} parsed 0_reading before the contract ledger existed"
            )
            return fn(*args, **kwargs)

        return wrapper

    monkeypatch.setattr(
        pipeline,
        "compute_reading_report_from_vector_dir",
        _spy("reading_report", pipeline.compute_reading_report_from_vector_dir),
    )
    monkeypatch.setattr(
        reading, "load_reading_view", _spy("load_view", reading.load_reading_view)
    )
    monkeypatch.setattr(
        window_sources,
        "build_observation_reference_catalog_from_run",
        _spy("v3_catalog", window_sources.build_observation_reference_catalog_from_run),
    )

    with pytest.raises(Exception):
        pipeline.run_pipeline_artifacts(
            vdir, "{}", out_dir=out_dir, capability_profile="orthogonal_polygon"
        )
    assert seen == ["reading_report", "load_view", "v3_catalog"], seen
    assert ledger_path.exists(), "F-c: even the catalog's own failure owes a ledger"


# --- R7 (BLK-C): the ledger survives ordinary filesystem / encoding reality -- #
def _dangling_symlink(vdir: Path) -> None:
    import os

    os.symlink("/nonexistent/target", vdir / "broken.json")


def _symlink_loop(vdir: Path) -> None:
    import os

    os.symlink(str(vdir / "loop.json"), vdir / "loop.json")


_UNREADABLE_SHAPES = (
    ("nonstring_schema_list", "1f_view.json",
     lambda v: (v / "1f_view.json").write_text('{"schema": [], "strokes": []}'),
     "non-string schema"),
    ("nonstring_schema_dict", "1f_view.json",
     lambda v: (v / "1f_view.json").write_text('{"schema": {}, "strokes": []}'),
     "non-string schema"),
    ("nonstring_schema_null", "1f_view.json",
     lambda v: (v / "1f_view.json").write_text('{"schema": null, "strokes": []}'),
     "non-string schema"),
    ("invalid_utf8", "bad.json",
     lambda v: (v / "bad.json").write_bytes(b"\xff\xfe\x00"), "not valid UTF-8"),
    ("utf16_product", "bad.json",
     lambda v: (v / "bad.json").write_bytes(b"\xff\xfe{\x00}\x00"), "not valid UTF-8"),
    ("latin1_byte", "bad.json",
     lambda v: (v / "bad.json").write_bytes(b'{"a": "caf\xe9"}'), "not valid UTF-8"),
    ("directory", "backup.json", lambda v: (v / "backup.json").mkdir(),
     "not a readable regular file"),
    ("dangling_symlink", "broken.json", _dangling_symlink,
     "not a readable regular file"),
    ("symlink_loop", "loop.json", _symlink_loop, "not a readable regular file"),
)


@pytest.mark.parametrize("label,offender,make,expect_reason", _UNREADABLE_SHAPES)
def test_r7_unreadable_shapes_become_a_named_ledger_row(
    tmp_path, label, offender, make, expect_reason
):
    """⭐ BLK-C: `ledger_for` promised 'never raises' and it was false three ways
    at once. Each of these killed the ledger writer itself -- so the F-c record
    was missing exactly for the runs it exists to explain. ⛔ None of these is an
    adversarial input: a truncated UTF-16 product, a stray `mkdir`, a symlink
    whose target moved."""
    from src.agent.reading.vector_contract import UNEXPECTED_FAILURE_PREFIX

    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    make(vdir)

    ledger = ledger_for(vdir, discover_vector_files(vdir))  # ⭐ must not raise
    row = next(r for r in ledger["files"] if r["file"] == offender)
    assert row["contract"] == CONTRACT_UNKNOWN
    assert row["disposition"] == "error"
    assert expect_reason in (row["reason"] or ""), row
    assert UNEXPECTED_FAILURE_PREFIX not in (row["reason"] or ""), (
        "each of these has a NAMED path; ⛔ the last-resort net must not be the "
        "thing making this test green, or neutering the named path stays green"
    )
    assert offender not in ledger["consumed"]


def test_r7_a_name_that_vanished_between_listing_and_read(tmp_path):
    """`ledger_for` takes the name list from its caller, so the file can be gone
    by the time it is read -- a plain TOCTOU, not an attack."""
    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    ledger = ledger_for(vdir, ["1f_view.json", "vanished.json"])
    row = next(r for r in ledger["files"] if r["file"] == "vanished.json")
    assert row["disposition"] == "error"
    # ⭐ The reason is load-bearing, ⛔ not "it did not crash": with only the
    # disposition asserted this test stayed green under EVERY read-path neuter,
    # so it locked nothing at all ([[gate-with-only-negative-assertions-is-unobservable]]).
    assert "not a readable regular file" in (row["reason"] or ""), row
    assert ledger["consumed"] == ["1f_view.json"]


def test_r7_a_fifo_named_json_does_not_block_forever(tmp_path):
    """⚠️ Worse than the three named crashes: `read_text` on a fifo HANGS, and no
    `except` clause can catch a hang. This is why the guard is `is_file()` -- a
    boundary that admits only regular files -- and ⛔ not a fourth exception
    type appended to a list. Fenced with a real alarm so a regression fails the
    suite instead of wedging it."""
    import os
    import signal

    if not hasattr(signal, "SIGALRM"):  # pragma: no cover - Linux CI
        pytest.skip("SIGALRM unavailable")

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    os.mkfifo(vdir / "pipe.json")

    def _boom(signum, frame):
        raise TimeoutError("ledger_for blocked on a fifo named *.json")

    previous = signal.signal(signal.SIGALRM, _boom)
    signal.setitimer(signal.ITIMER_REAL, 10.0)
    try:
        ledger = ledger_for(vdir, discover_vector_files(vdir))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous)
    row = next(r for r in ledger["files"] if r["file"] == "pipe.json")
    assert row["disposition"] == "error"
    assert "not a readable regular file" in (row["reason"] or "")


def test_r7_the_last_resort_net_exists_and_is_reachable(tmp_path):
    """⭐ The reason the fix is a boundary and not an exception list.

    `OSError` + `UnicodeDecodeError` + `JSONDecodeError` was the returned
    verdict's literal prescription, and it does NOT cover this: JSON nested
    deeply enough makes `json.loads` raise `RecursionError`, which is none of
    the three. Enumerating exception types is the same shape of defence as
    enumerating filename patterns -- it can never be finished
    ([[lexical-guard-cannot-be-completed]]). The net turns the leftover tail
    into a named row instead of a dead ledger."""
    from src.agent.reading.vector_contract import UNEXPECTED_FAILURE_PREFIX

    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    (vdir / "deep.json").write_text("[" * 200_000 + "]" * 200_000, encoding="utf-8")

    ledger = ledger_for(vdir, discover_vector_files(vdir))  # ⭐ must not raise
    row = ledger["files"][0]
    assert row["contract"] == CONTRACT_UNKNOWN
    assert row["disposition"] == "error"
    assert UNEXPECTED_FAILURE_PREFIX in (row["reason"] or "")
    assert "RecursionError" in (row["reason"] or ""), "the net must name what blew up"


@pytest.mark.parametrize(
    "label,payload,expect_reason",
    [
        ("nonstring_schema", b'{"schema": [], "strokes": []}', "non-string schema"),
        ("invalid_utf8", b"\xff\xfe\x00", "not valid UTF-8"),
    ],
)
def test_r7_real_run_correction_names_them_and_files_the_ledger(
    tmp_path, label, payload, expect_reason
):
    from src.agent.reading.vector_contract import UNEXPECTED_FAILURE_PREFIX
    from src.agent.pipeline import run_correction

    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    (vdir / "1f_view.json").write_bytes(payload)
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()

    with pytest.raises(UnconsumableVectorFile) as exc:
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert "1f_view.json" in str(exc.value)
    ledger_path = tmp_path / "_run" / "reading_vector_contract_ledger.json"
    assert ledger_path.exists()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["consumed"] == []
    # ⭐ "a ledger exists" is satisfied by the last-resort net too, so asserting
    # only that left this test green while its own mechanism was removed.
    reason = ledger["files"][0]["reason"] or ""
    assert expect_reason in reason, ledger
    assert UNEXPECTED_FAILURE_PREFIX not in reason


def test_r7_directory_named_json_reaches_run_correction_with_a_ledger(tmp_path):
    from src.agent.pipeline import run_correction

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    (vdir / "backup.json").mkdir()
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()

    with pytest.raises(UnconsumableVectorFile) as exc:
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert "backup.json" in str(exc.value)
    ledger = json.loads(
        (tmp_path / "_run" / "reading_vector_contract_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    row = next(r for r in ledger["files"] if r["file"] == "backup.json")
    assert "not a readable regular file" in (row["reason"] or ""), row


def test_r7_a_hostile_run_dir_does_not_eat_the_named_refusal(tmp_path):
    """⭐ The fourth way 'never raises' was false, and the one that costs most.

    `_run` already existing as a FILE makes the ledger write raise
    `FileExistsError` from inside `_write_vector_contract_ledger` -- so the run
    died with a bare filesystem error and F-b (the NAMED refusal) went down with
    F-c. Losing the ledger to an unusable run dir is unavoidable; losing the
    named refusal too is a strict regression, so the write failure is logged and
    the classification verdict still lands."""
    from src.agent.pipeline import run_correction

    vdir = tmp_path / "0_reading"
    vdir.mkdir(parents=True)
    (vdir / "1f_view.json").write_text("[1, 2, 3]", encoding="utf-8")
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()
    (tmp_path / "_run").write_text("not a directory", encoding="utf-8")

    with pytest.raises(UnconsumableVectorFile) as exc:
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert "1f_view.json" in str(exc.value)


def test_r7_ledger_writer_itself_never_raises_on_a_hostile_run_dir(tmp_path):
    from src.agent.pipeline import _write_vector_contract_ledger

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()
    (tmp_path / "_run").write_text("not a directory", encoding="utf-8")

    assert _write_vector_contract_ledger(vdir, stage_dir) is None


def test_r6_no_reading_file_is_read_before_the_ledger_is_on_disk(tmp_path, monkeypatch):
    """⭐ The consumer-agnostic half: locks the PROMISE, not today's consumer list.

    F-c says a run that touches `0_reading` and fails still owes a ledger naming
    the offender. Round 1 delivered that for `run_correction` and it evaporated
    one entry point out, because the fix was measured against the consumers
    somebody had thought of. So stop enumerating consumers: intercept the read.
    Every `Path.read_text` / `Path.read_bytes` of a file in the vector dir whose
    call stack does not pass through the discriminator itself must find the
    ledger already written. A fourth consumer wired in upstream trips this the
    day it lands, with ⛔ no fixture and no new spy.

    (The discriminator's own reads are excluded because they are what PRODUCES
    the ledger — it cannot be expected to exist before the read that writes it.)
    """
    import sys

    import src.agent.pipeline as pipeline

    vdir = tmp_path / "0_reading"
    _write(vdir, "1f_view.json", _legacy_view())
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    out_dir = tmp_path / "run"
    out_dir.mkdir()
    ledger_path = out_dir / "_run" / "reading_vector_contract_ledger.json"
    too_early: list[str] = []

    real_text, real_bytes = Path.read_text, Path.read_bytes

    def _note(target: Path) -> None:
        if Path(target).parent != vdir or ledger_path.exists():
            return
        frames, frame = [], sys._getframe()
        while frame is not None:
            frames.append(frame.f_code.co_filename)
            frame = frame.f_back
        if any(f.endswith("vector_contract.py") for f in frames):
            return  # this read is the one that writes the ledger
        too_early.append(f"{Path(target).name} <- {Path(frames[2]).name}")

    def _text_spy(self, *args, **kwargs):
        _note(self)
        return real_text(self, *args, **kwargs)

    def _bytes_spy(self, *args, **kwargs):
        _note(self)
        return real_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _text_spy)
    monkeypatch.setattr(Path, "read_bytes", _bytes_spy)

    with pytest.raises(Exception):
        pipeline.run_pipeline_artifacts(
            vdir, "{}", out_dir=out_dir, capability_profile="orthogonal_polygon"
        )
    assert too_early == [], (
        "F-c: these reads of 0_reading happened while no ledger existed: "
        f"{too_early}"
    )
    assert ledger_path.exists()
