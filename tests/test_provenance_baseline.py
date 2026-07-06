"""Tests for record_baseline run-source provenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import record_baseline  # noqa: E402

from src.agent.execution import run_meta_path  # noqa: E402


def _minimal_run(tmp_path: Path) -> Path:
    run = tmp_path / "synthetic_case" / "run_audit"
    run.mkdir(parents=True)
    return run


def test_hash_directory_contents_is_deterministic_and_ignores_pyc(tmp_path):
    root = tmp_path / "tree"
    (root / "b").mkdir(parents=True)
    (root / "a").mkdir()
    (root / "b" / "two.txt").write_bytes(b"two")
    (root / "a" / "one.txt").write_bytes(b"one")
    (root / "a" / "__pycache__").mkdir()
    (root / "a" / "__pycache__" / "one.cpython-312.pyc").write_bytes(b"ignored")

    first = record_baseline._hash_directory_contents(root)
    second = record_baseline._hash_directory_contents(root)

    assert first == second
    (root / "a" / "__pycache__" / "one.cpython-312.pyc").write_bytes(b"changed")
    assert record_baseline._hash_directory_contents(root) == first


def test_hash_directory_contents_changes_on_single_byte(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    path = root / "value.txt"
    path.write_bytes(b"abc")

    before = record_baseline._hash_directory_contents(root)
    path.write_bytes(b"abd")

    assert record_baseline._hash_directory_contents(root) != before


def test_record_baseline_writes_provenance_and_report_summary(tmp_path):
    run = _minimal_run(tmp_path)

    record_baseline.record_baseline(run, date="2026-07-06", orchestrator="test")

    baseline = json.loads(run_meta_path(run, "baseline.json").read_text(encoding="utf-8"))
    provenance = baseline["provenance"]
    assert "collected_at" not in provenance
    assert provenance["git_sha"]
    assert isinstance(provenance["git_dirty"], bool)
    assert isinstance(provenance["git_dirty_paths"], list)
    assert len(provenance["git_dirty_paths"]) <= provenance["git_dirty_paths_cap"] <= 50
    assert provenance["git_dirty_paths_total"] >= len(provenance["git_dirty_paths"])
    assert provenance["skills_intake_hash"]
    assert provenance["reading_src_hash"]
    assert provenance["correction_src_hash"]
    assert provenance["correction_config_hash"]

    report = (run / "report" / "REPORT.md").read_text(encoding="utf-8")
    assert "- provenance: `" in report
    assert f"git={provenance['git_sha'][:12]}" in report
    assert f"skills={provenance['skills_intake_hash'][:12]}" in report
    assert f"corr_cfg={provenance['correction_config_hash'][:12]}" in report


def test_record_baseline_git_failure_is_best_effort(tmp_path, monkeypatch):
    run = _minimal_run(tmp_path)

    def fail_git(args: list[str]) -> str:
        raise RuntimeError(f"git failed: {args}")

    monkeypatch.setattr(record_baseline, "_git_output", fail_git)

    record_baseline.record_baseline(run, date="2026-07-06", orchestrator="test")

    provenance = json.loads(
        run_meta_path(run, "baseline.json").read_text(encoding="utf-8")
    )["provenance"]
    assert provenance["git_sha"] is None
    assert provenance["git_dirty"] is None
    assert provenance["git_dirty_paths"] is None
    assert provenance["git_dirty_paths_total"] is None
    assert "git provenance unavailable" in provenance["collection_error"]
    assert provenance["skills_intake_hash"]
