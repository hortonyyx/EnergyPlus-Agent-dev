"""F-146: promoted answer-root facts are reverified at their consumer exit."""
from __future__ import annotations

import pytest

import src.agent.judge.answer_compiler as ac
from src.agent.judge.as_measured import canonical_bytes
from src.agent.judge.gt_revisions import (
    AsSignedReproductionError,
    canonical_as_signed_bytes,
    canonical_revisions_bytes,
)
from tests.answer_compiler_fixtures import synthetic_signed_facts


def _write_answer_root(root, measured, ledger, signed):
    facts = root / "case_tests/test_baseline/gt" / measured.case / "facts"
    facts.mkdir(parents=True)
    (facts / "as_measured.json").write_bytes(canonical_bytes(measured))
    (facts / "revisions.json").write_bytes(canonical_revisions_bytes(ledger))
    (facts / "as_signed.json").write_bytes(canonical_as_signed_bytes(signed))
    return facts


def test_answer_root_read_reverifies_a_genuine_trio(tmp_path, monkeypatch):
    measured, ledger, signed, _request = synthetic_signed_facts()
    _write_answer_root(tmp_path, measured, ledger, signed)
    monkeypatch.setattr(ac, "REPO_ROOT", tmp_path)
    got = ac.read_facts_for_compilation(measured.case)
    assert got[0].model_dump(mode="json") == measured.model_dump(mode="json")
    assert got[1].model_dump(mode="json") == ledger.model_dump(mode="json")
    assert got[2].model_dump(mode="json") == signed.model_dump(mode="json")


def test_answer_root_read_rejects_bytes_that_arrived_by_an_ungated_route(
        tmp_path, monkeypatch):
    measured, ledger, signed, _request = synthetic_signed_facts()
    facts = _write_answer_root(tmp_path, measured, ledger, signed)
    raw = signed.model_dump(mode="json")
    raw["views"][0]["face_lines"][0]["along_max"] -= 1
    # Schema-valid and deliberately written without the staging writer: the
    # exit gate must be immune to how the bytes arrived.
    import json
    (facts / "as_signed.json").write_text(
        json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n")
    monkeypatch.setattr(ac, "REPO_ROOT", tmp_path)
    with pytest.raises(AsSignedReproductionError):
        ac.read_facts_for_compilation(measured.case)


def test_present_but_incomplete_answer_trio_never_falls_back_to_staging(
        tmp_path, monkeypatch):
    measured, _ledger, _signed, _request = synthetic_signed_facts()
    facts = tmp_path / "case_tests/test_baseline/gt" / measured.case / "facts"
    facts.mkdir(parents=True)
    monkeypatch.setattr(ac, "REPO_ROOT", tmp_path)
    with pytest.raises(ac.AnswerCompilerInputError, match="trio_is_incomplete"):
        ac.read_facts_for_compilation(measured.case)
