import json

import pytest

from src.agent.pipeline import (
    _build_correction_messages,
    _write_vector_contract_ledger,
    run_correction,
)
from src.agent.reading.as_drawn.as_drawn_v2 import SCHEMA as AS_DRAWN_SCHEMA
from src.agent.reading.vector_contract import (
    CONTRACT_READING_VIEW_LEGACY,
    CONTRACT_UNKNOWN,
    UnconsumableVectorFile,
    classify_vector_json,
)


STROKE = {"id": "S1", "pen": "wall", "points": [[0.0, 0.0], [1.0, 0.0]]}


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_new_b01_exact_fixture_is_blocked_at_prompt_entry(tmp_path):
    raw = {"schema": "future_reading_contract_v99", "strokes": [STROKE]}
    assert classify_vector_json(raw).contract_id == CONTRACT_UNKNOWN
    vdir = tmp_path / "0_reading"
    _write(vdir / "1f_view.json", raw)
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    with pytest.raises(UnconsumableVectorFile, match="future_reading_contract_v99"):
        _build_correction_messages(vdir, "{}")


def test_new_b02_exact_fixture_is_blocked_at_prompt_entry(tmp_path):
    raw = {
        "stage": 7,
        "results": "not-a-result-list",
        "report_schema_version": {"not": "a version"},
    }
    assert classify_vector_json(raw).contract_id == CONTRACT_UNKNOWN
    vdir = tmp_path / "0_reading"
    _write(vdir / "1f_view.json", {"strokes": [STROKE]})
    _write(vdir / "1f_view_checks.json", raw)
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    with pytest.raises(UnconsumableVectorFile, match="1f_view_checks.json"):
        _build_correction_messages(vdir, "{}")


def test_new_b03_exact_fixture_is_named_and_ledgered_at_real_run(tmp_path):
    vdir = tmp_path / "0_reading"
    vdir.mkdir()
    (vdir / "1f_view.json").write_text("[1, 2, 3]", encoding="utf-8")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()
    with pytest.raises(UnconsumableVectorFile, match="1f_view.json"):
        run_correction(vdir, "{}", out_dir=stage_dir)
    ledger = tmp_path / "_run" / "reading_vector_contract_ledger.json"
    assert ledger.exists()
    assert json.loads(ledger.read_text())["files"][0]["contract"] == CONTRACT_UNKNOWN


def test_registered_but_malformed_declaration_still_falls_back_and_is_consumed(tmp_path):
    raw = {"schema": AS_DRAWN_SCHEMA, "strokes": [STROKE]}
    assert classify_vector_json(raw).contract_id == CONTRACT_READING_VIEW_LEGACY
    vdir = tmp_path / "0_reading"
    _write(vdir / "1f_view.json", raw)
    (vdir / "reading_summary.md").write_text("summary", encoding="utf-8")
    _, human = _build_correction_messages(vdir, "{}")
    assert AS_DRAWN_SCHEMA in human


@pytest.mark.parametrize("schema_value", [[], {}])
def test_unhashable_schema_crashes_before_ledger(schema_value, tmp_path):
    vdir = tmp_path / "0_reading"
    _write(vdir / "1f_view.json", {"schema": schema_value, "strokes": [STROKE]})
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()
    with pytest.raises(TypeError, match="unhashable type"):
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert not (tmp_path / "_run" / "reading_vector_contract_ledger.json").exists()


def test_invalid_utf8_crashes_before_ledger(tmp_path):
    vdir = tmp_path / "0_reading"
    vdir.mkdir()
    (vdir / "1f_view.json").write_bytes(b"\xff\xfe\x00")
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()
    with pytest.raises(UnicodeDecodeError):
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert not (tmp_path / "_run" / "reading_vector_contract_ledger.json").exists()


@pytest.mark.parametrize("payload", [b"", b"\xef\xbb\xbf{}"])
def test_empty_and_bom_files_are_named_and_ledgered(payload, tmp_path):
    vdir = tmp_path / "0_reading"
    vdir.mkdir()
    (vdir / "1f_view.json").write_bytes(payload)
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()
    with pytest.raises(UnconsumableVectorFile, match="1f_view.json"):
        run_correction(vdir, "{}", out_dir=stage_dir)
    assert (tmp_path / "_run" / "reading_vector_contract_ledger.json").exists()


def test_uppercase_and_nested_json_are_absent_from_ledger_inventory(tmp_path):
    vdir = tmp_path / "0_reading"
    _write(vdir / "1f_view.json", {"strokes": [STROKE]})
    _write(vdir / "MYSTERY.JSON", {"unknown": True})
    _write(vdir / "nested" / "mystery.json", {"unknown": True})
    stage_dir = tmp_path / "1_correction"
    stage_dir.mkdir()
    ledger_path = _write_vector_contract_ledger(vdir, stage_dir)
    names = [row["file"] for row in json.loads(ledger_path.read_text())["files"]]
    assert names == ["1f_view.json"]
