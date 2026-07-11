"""C2 B-M §5.1: RunManifestV1/V2 + StageRecordV1/V2 wire — versioned serializer,
explicit migration + commit protocol, and the artifact-contract negatives."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.execution.manifest import (
    RunInputs,
    RunManifest,
    RunManifestV1,
    RunManifestV2,
    StageRecord,
    StageRecordV1,
    StageRecordV2,
    assert_stage_artifact_contracts,
    ensure_run_manifest_v2,
    hash_text,
    load_run_manifest,
    migrate_run_to_v2,
    new_run_id,
    reading_attempt_allowed,
    save_run_manifest,
)
from src.agent.execution.run_meta import run_meta_path
from src.agent.execution.view_manifest import (
    VIEW_MANIFEST_NAME,
    provision_view_manifest,
    verify_view_manifest,
)

HEX64 = "a" * 64


def _seed_v1_run(run_dir: Path, *, stage: str = "0_reading", attempt: int = 1) -> RunManifest:
    """A minimal legacy v1 run: one accepted stage with real attempt files on
    disk (output.json + checks.json), the shape a real pre-B-M run has."""
    attempt_dir = run_dir / stage / "attempts" / f"{attempt:03d}"
    attempt_dir.mkdir(parents=True)
    out_text = json.dumps({"a": 1})
    (attempt_dir / "output.json").write_text(out_text, encoding="utf-8")
    (attempt_dir / "checks.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    v1 = RunManifest(case=run_dir.name)
    v1.accept(StageRecord(stage=stage, accepted_attempt=attempt, output_hash=hash_text(out_text)))
    v1.save(run_dir)
    return v1


# --------------------------------------------------------------------------- #
# aliases are literal, not lookalikes
# --------------------------------------------------------------------------- #
def test_v1_aliases_are_the_same_class():
    assert StageRecordV1 is StageRecord
    assert RunManifestV1 is RunManifest


# --------------------------------------------------------------------------- #
# 1. v1 load-save bytes unchanged
# --------------------------------------------------------------------------- #
def test_v1_load_save_bytes_unchanged(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    v1 = RunManifest(case="run")
    v1.accept(StageRecord(stage="1_correction", accepted_attempt=1, output_hash="a" * 64))
    path = v1.save(run_dir)
    text1 = path.read_text(encoding="utf-8")
    reloaded = RunManifest.load(run_dir)
    text2 = reloaded.save(run_dir).read_text(encoding="utf-8")
    assert text1 == text2
    assert json.loads(text1)["manifest_version"] == "1"
    assert set(json.loads(text1)["stages"]["1_correction"]) == {
        "stage", "accepted_attempt", "output_hash", "input_hashes",
        "stage_version", "check_version", "capability", "check_passed",
    }


# --------------------------------------------------------------------------- #
# 2. v1 read-only: no manifest yet is allowed; a legacy v1 file blocks new
#    0_reading attempts
# --------------------------------------------------------------------------- #
def test_fresh_run_no_manifest_allows_reading_attempts(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    allowed, reason = reading_attempt_allowed(run_dir)
    assert allowed and reason == ""


def test_v1_run_blocks_new_reading_attempts(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _seed_v1_run(run_dir)
    allowed, reason = reading_attempt_allowed(run_dir)
    assert not allowed
    assert "v1" in reason and "grandfathered" in reason


def test_migrate_then_reading_attempts_allowed(tmp_path: Path, monkeypatch):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _seed_v1_run(run_dir)
    v2 = migrate_run_to_v2(case_dir, run_dir)
    assert isinstance(v2, RunManifestV2)
    allowed, _ = reading_attempt_allowed(run_dir)
    assert allowed


# --------------------------------------------------------------------------- #
# 3. migration backfill: real pointer validation + legal sidecar omission
# --------------------------------------------------------------------------- #
def test_migration_backfills_real_hashes_and_legal_omissions(tmp_path: Path):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _seed_v1_run(run_dir, stage="0_reading", attempt=1)
    v2 = migrate_run_to_v2(case_dir, run_dir)

    rec = v2.stages["0_reading"]
    assert rec.artifact_contract == "migrated_v1"
    assert rec.artifact_hashes["output"] == rec.output_hash
    assert "checks" in rec.artifact_hashes
    # audit/feature_states never existed pre-B2 — legal omission, not fabricated
    assert "audit" not in rec.artifact_hashes
    assert "feature_states" not in rec.artifact_hashes


def test_migration_rejects_pointer_whose_output_changed_since_accept(tmp_path: Path):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _seed_v1_run(run_dir)
    # tamper the accepted attempt's output.json after acceptance
    (run_dir / "0_reading" / "attempts" / "001" / "output.json").write_text(
        json.dumps({"a": 999}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="does not match"):
        migrate_run_to_v2(case_dir, run_dir)


def test_migration_of_run_with_no_accepted_stages_is_legal(tmp_path: Path):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    v1 = RunManifest(case="run")
    v1.save(run_dir)
    v2 = migrate_run_to_v2(case_dir, run_dir)
    assert v2.stages == {}


# --------------------------------------------------------------------------- #
# 4. orphan view_manifest handling: V1 loader ignores it; retry reuses/overwrites
# --------------------------------------------------------------------------- #
def test_v1_loader_ignores_orphan_view_manifest(tmp_path: Path):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    provision_view_manifest(case_dir, run_dir)  # orphan: no run_manifest.json at all
    assert not (run_dir / "_run" / "run_manifest.json").exists()
    loaded = RunManifest.load(run_dir)  # V1 API path — never looks at view_manifest.json
    assert loaded.manifest_version == "1"
    assert loaded.stages == {}


def test_migration_reuses_consistent_orphan_view_manifest(tmp_path: Path):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    provision_view_manifest(case_dir, run_dir)
    vm_path = run_dir / "_run" / VIEW_MANIFEST_NAME
    mtime_before = vm_path.stat().st_mtime_ns
    _seed_v1_run(run_dir)

    migrate_run_to_v2(case_dir, run_dir)
    assert vm_path.stat().st_mtime_ns == mtime_before  # reused byte-for-byte, not rewritten


def test_migration_overwrites_inconsistent_orphan_view_manifest(tmp_path: Path):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    provision_view_manifest(case_dir, run_dir)
    vm_path = run_dir / "_run" / VIEW_MANIFEST_NAME
    vm = json.loads(vm_path.read_text(encoding="utf-8"))
    vm["content_sha256"] = "0" * 64  # corrupt: an interrupted prior migration attempt
    vm_path.write_text(json.dumps(vm), encoding="utf-8")
    _seed_v1_run(run_dir)

    v2 = migrate_run_to_v2(case_dir, run_dir)
    result = verify_view_manifest(case_dir, run_dir)
    assert result.ok
    assert result.on_disk.content_sha256 == v2.run_inputs.view_manifest_sha256


def test_migration_idempotent_crash_recovery(tmp_path: Path):
    case_dir = Path("case_tests/e2e_tests/sm21_anchor")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _seed_v1_run(run_dir)
    v2_first = migrate_run_to_v2(case_dir, run_dir)
    v2_second = migrate_run_to_v2(case_dir, run_dir)  # re-run after a hypothetical crash
    assert v2_first.run_id == v2_second.run_id
    assert v2_first.model_dump_json() == v2_second.model_dump_json()


# --------------------------------------------------------------------------- #
# 5. ensure_run_manifest_v2: binds fresh, agrees on match, rejects drift/v1
# --------------------------------------------------------------------------- #
def test_ensure_run_manifest_v2_binds_fresh_and_is_idempotent(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    v2a = ensure_run_manifest_v2(run_dir, view_manifest_sha256=HEX64)
    v2b = ensure_run_manifest_v2(run_dir, view_manifest_sha256=HEX64)
    assert v2a.run_id == v2b.run_id


def test_ensure_run_manifest_v2_rejects_input_drift(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ensure_run_manifest_v2(run_dir, view_manifest_sha256=HEX64)
    with pytest.raises(ValueError, match="drifted"):
        ensure_run_manifest_v2(run_dir, view_manifest_sha256="b" * 64)


def test_ensure_run_manifest_v2_rejects_grandfathered_v1(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _seed_v1_run(run_dir)
    with pytest.raises(ValueError, match="grandfathered"):
        ensure_run_manifest_v2(run_dir, view_manifest_sha256=HEX64)


# --------------------------------------------------------------------------- #
# 6. StageRecordV2 contract validators
# --------------------------------------------------------------------------- #
def _v2_rec(**overrides) -> dict:
    fields = dict(
        stage="1_correction", accepted_attempt=1, output_hash="a" * 64,
        artifact_contract="base_v2", artifact_hashes={"output": "a" * 64, "checks": "b" * 64},
    )
    fields.update(overrides)
    return fields


def test_missing_required_artifact_key_rejected():
    with pytest.raises(ValidationError):
        StageRecordV2(**_v2_rec(artifact_hashes={"output": "a" * 64}))


def test_unknown_artifact_key_rejected():
    with pytest.raises(ValidationError):
        StageRecordV2(**_v2_rec(artifact_hashes={"output": "a" * 64, "checks": "b" * 64, "bogus": "c" * 64}))


def test_output_double_hash_disagreement_rejected():
    with pytest.raises(ValidationError):
        StageRecordV2(**_v2_rec(output_hash="a" * 64, artifact_hashes={"output": "f" * 64, "checks": "b" * 64}))


def test_forged_migrated_v1_with_audit_key_rejected():
    with pytest.raises(ValidationError):
        StageRecordV2(**_v2_rec(
            artifact_contract="migrated_v1",
            artifact_hashes={"output": "a" * 64, "audit": "d" * 64},
        ))


def test_native_v2_correction_reporting_base_v2_rejected_by_cross_check(tmp_path: Path):
    m = RunManifestV2(run_id=new_run_id(), run_inputs=RunInputs(view_manifest_sha256=HEX64))
    m.accept(StageRecordV2(**_v2_rec(stage="1_correction", artifact_contract="base_v2")))
    with pytest.raises(ValueError, match="not in the allowed set"):
        assert_stage_artifact_contracts(
            m, {"1_correction": frozenset({"correction_b2_v1", "migrated_v1"})}
        )
    # a stage the caller's allowlist doesn't mention is untouched
    assert_stage_artifact_contracts(m, {"4_mep": frozenset({"base_v2"})})


# --------------------------------------------------------------------------- #
# 7. versioned serializer shared by both writers
# --------------------------------------------------------------------------- #
def test_save_run_manifest_shared_by_v1_and_v2(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    v1 = RunManifest(case="run")
    save_run_manifest(v1, run_dir)
    assert json.loads(run_meta_path(run_dir, "run_manifest.json").read_text())["manifest_version"] == "1"

    v2 = RunManifestV2(run_id=new_run_id(), run_inputs=RunInputs(view_manifest_sha256=HEX64))
    save_run_manifest(v2, run_dir)
    assert json.loads(run_meta_path(run_dir, "run_manifest.json").read_text())["manifest_version"] == "2"


def test_load_run_manifest_dispatches_by_version(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    assert load_run_manifest(run_dir) is None
    RunManifest(case="run").save(run_dir)
    assert isinstance(load_run_manifest(run_dir), RunManifestV1)

    run_dir2 = tmp_path / "run2"
    run_dir2.mkdir()
    save_run_manifest(RunManifestV2(run_id=new_run_id(), run_inputs=RunInputs(view_manifest_sha256=HEX64)), run_dir2)
    assert isinstance(load_run_manifest(run_dir2), RunManifestV2)
