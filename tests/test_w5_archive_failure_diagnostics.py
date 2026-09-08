"""W#5: archive rejection retains gate① without publishing a trusted attempt."""
import dataclasses
import hashlib
import json

import pytest

from src.agent.execution.stage_runner import StageRunner
from src.validator.checks.schema import CheckLayer, CheckReport
from tests.test_w3_chain_replay_lock import _chain_bundle


def test_real_replay_rejection_keeps_gate_report_and_retry_does_not_overwrite(tmp_path):
    bundle = _chain_bundle(tmp_path)
    runner = StageRunner(bundle.run_dir, bundle.manifest)
    stage_dir = bundle.run_dir / "1_correction"
    original_manifest = bundle.manifest.model_dump()
    original_output = (bundle.attempt / "output.json").read_bytes()
    stripped = dataclasses.replace(bundle.result, chain_provenance=None)
    report = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    report.add_pass("correction.coverage", CheckLayer.INVARIANT)
    report.add_fail("correction.test_observation", CheckLayer.CROSS_CHECK, "retain this exact gate finding")
    first_checks = None
    for index in (1, 2):
        with pytest.raises(ValueError, match="writer_core_projection_drift"):
            runner.record(stage="1_correction", stage_dir=stage_dir,
                          output_obj=stripped, report=report)
        directory = stage_dir / "record_failures" / f"{index:03d}"
        checks = (directory / "checks.json").read_bytes()
        failure = json.loads((directory / "failure.json").read_text())
        restored = CheckReport.model_validate_json(checks)
        assert restored.results == report.results
        assert failure["checks_sha256"] == hashlib.sha256(checks).hexdigest()
        assert failure["error"] == "writer_core_projection_drift"
        assert failure["accepted"] is False
        assert set(p.name for p in directory.iterdir()) == {"checks.json", "failure.json"}
        assert bundle.manifest.model_dump() == original_manifest
        assert (bundle.attempt / "output.json").read_bytes() == original_output
        assert not (stage_dir / "attempts/002").exists()
        if index == 1:
            first_checks = checks
    clean_report = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    rec = runner.record(stage="1_correction", stage_dir=stage_dir,
                        output_obj=bundle.result, report=clean_report)
    assert rec.accepted and rec.attempt_index == 2
    assert (stage_dir / "record_failures/001/checks.json").read_bytes() == first_checks
    assert (stage_dir / "attempts/002/deterministic_core_proof.json").exists()


def test_diagnostic_io_failure_does_not_mask_original_rejection(tmp_path, monkeypatch):
    import src.agent.execution.stage_runner as module
    from src.agent.execution.manifest import RunManifest

    def fail_diagnostic(*args):
        raise OSError("diagnostic storage unavailable")

    monkeypatch.setattr(module, "_record_archive_failure", fail_diagnostic)
    runner = StageRunner(tmp_path, RunManifest(case="w5"))
    with pytest.raises(TypeError, match="not JSON serializable") as error:
        runner.record(stage="0_reading", stage_dir=tmp_path / "0_reading",
                      output_obj=object(), report=CheckReport(stage="0_reading"))
    assert any("diagnostic storage unavailable" in note for note in error.value.__notes__)
