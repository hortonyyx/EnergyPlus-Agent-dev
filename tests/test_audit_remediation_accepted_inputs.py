from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.tool_scripts.run_stage as run_stage
from src.agent.correction.window_sources import (
    WindowResolverInputError,
    build_verified_window_inputs_from_run,
)
from src.agent.execution.manifest import RunManifest
from src.agent.execution.policy import RunPolicy
from src.agent.execution.stage_runner import StageRunner
from src.validator.checks.schema import CheckLayer, CheckReport


def _pass_report(stage: str) -> CheckReport:
    report = CheckReport(stage=stage)
    report.add_pass("fixture", CheckLayer.INVARIANT)
    return report


def _accepted_reading_run(tmp_path):
    run_dir = tmp_path / "run"
    reading_dir = run_dir / "0_reading"
    reading_dir.mkdir(parents=True)
    accepted_view = {
        "image_kind": "plan",
        "strokes": [{"id": "accepted"}],
        "uncaptured": [],
    }
    (reading_dir / "plan_view.json").write_text(
        json.dumps(accepted_view), encoding="utf-8"
    )
    manifest = RunManifest(case="case")
    StageRunner(run_dir, manifest).record(
        stage="0_reading",
        stage_dir=reading_dir,
        output_obj={"plan_view": accepted_view},
        report=_pass_report("0_reading"),
    )
    manifest.save(run_dir)
    (reading_dir / "plan_view.json").write_text(
        json.dumps({**accepted_view, "strokes": [{"id": "blocked-later-draw"}]}),
        encoding="utf-8",
    )
    return run_dir, reading_dir


def test_draw_correction_rejects_nonaccepted_reading_before_llm_consumes_it(
    tmp_path, monkeypatch
):
    run_dir, _reading_dir = _accepted_reading_run(tmp_path)
    called = {"run_correction": False}

    def must_not_run(*args, **kwargs):
        called["run_correction"] = True
        raise AssertionError("run_correction consumed untrusted reading bytes")

    monkeypatch.setattr("src.agent.pipeline.run_correction", must_not_run)

    with pytest.raises(WindowResolverInputError) as exc:
        run_stage._draw_correction(
            run_dir, "{}", None, False, RunPolicy()
        )

    assert exc.value.code == "source_identity_invalid"
    assert called["run_correction"] is False


def test_window_source_builder_rejects_nonaccepted_reading_at_its_own_entry(tmp_path):
    run_dir, reading_dir = _accepted_reading_run(tmp_path)

    with pytest.raises(WindowResolverInputError) as exc:
        build_verified_window_inputs_from_run(
            producer_draw=object(),
            run_dir=run_dir,
            reading_dir=reading_dir,
        )

    assert exc.value.context["artifact"] == "reading_stage_root"
    assert exc.value.context["reason"] == "accepted_attempt_mismatch"


def test_reading_guard_rejects_tampered_accepted_archive(tmp_path):
    run_dir, reading_dir = _accepted_reading_run(tmp_path)
    accepted_path = run_dir / "0_reading" / "attempts" / "001" / "output.json"
    accepted_path.write_text('{"tampered":true}', encoding="utf-8")

    with pytest.raises(WindowResolverInputError) as exc:
        build_verified_window_inputs_from_run(
            producer_draw=object(),
            run_dir=run_dir,
            reading_dir=reading_dir,
        )

    assert exc.value.context == {
        "artifact": "accepted_reading",
        "reason": "output_hash_mismatch",
    }


def test_draw_correction_without_accepted_reading_preserves_standalone_path(
    tmp_path, monkeypatch
):
    run_dir = tmp_path / "run"
    (run_dir / "0_reading").mkdir(parents=True)
    reached = {"value": False}

    class ReachedRunCorrection(RuntimeError):
        pass

    def probe(*args, **kwargs):
        reached["value"] = True
        raise ReachedRunCorrection

    monkeypatch.setattr("src.agent.pipeline.run_correction", probe)

    with pytest.raises(ReachedRunCorrection):
        run_stage._draw_correction(run_dir, "{}", None, False, RunPolicy())

    assert reached["value"] is True


def test_real_draw_reading_archive_is_accepted_by_correction_guard(tmp_path, monkeypatch):
    """Happy-path parity lock: _draw_reading's exact output reaches correction."""
    from src.agent.execution.case_metadata import dimensioned_view_names

    source_case = Path("case_tests/e2e_tests/sm21_anchor")
    source_reading = source_case / "run_2026-06-20_gpt54_reading" / "0_reading"
    case_dir = tmp_path / "sm21_anchor"
    run_dir = case_dir / "run"
    reading_dir = run_dir / "0_reading"
    shutil.copytree(source_case / "case_data", case_dir / "case_data")
    reading_dir.mkdir(parents=True)
    for path in sorted(source_reading.glob("*_view.json")):
        shutil.copy2(path, reading_dir / path.name)

    output_obj, report = run_stage._draw_reading(
        run_dir,
        RunPolicy(),
        dimensioned_view_names(case_dir),
    )
    assert report.passed
    manifest = RunManifest(case="sm21_anchor")
    recorded = StageRunner(run_dir, manifest).record(
        stage="0_reading",
        stage_dir=reading_dir,
        output_obj=output_obj,
        report=report,
    )
    assert recorded.accepted
    manifest.save(run_dir)

    class ReachedRunCorrection(RuntimeError):
        pass

    def probe(*args, **kwargs):
        raise ReachedRunCorrection

    monkeypatch.setattr("src.agent.pipeline.run_correction", probe)

    with pytest.raises(ReachedRunCorrection):
        run_stage._draw_correction(run_dir, "{}", None, False, RunPolicy())


def test_b5_orientation_enrichment_is_idempotent_on_reentry(monkeypatch, tmp_path):
    verified = SimpleNamespace(
        ref=SimpleNamespace(
            schema_version="3",
            artifact_contract="correction_b5_orientation_v1",
        )
    )
    monkeypatch.setattr(
        "src.agent.output_coordinates.load_verified_accepted_correction",
        lambda **kwargs: verified,
    )

    def must_not_enrich(**kwargs):
        raise AssertionError("already-enriched B5 output re-entered orientation resolution")

    monkeypatch.setattr(
        "src.agent.correction.orientation.resolve_orientation_from_run_dir",
        must_not_enrich,
    )

    assert run_stage._ensure_orientation_enriched(
        tmp_path, RunPolicy(capability_profile="orthogonal_polygon"), object()
    ) is verified


def test_assembly_reads_and_binds_accepted_mep_not_stage_root(tmp_path):
    from src.agent._share import ensure_schema_initialized
    from tests.test_output_coordinate_identity import (
        _clean_report,
        _mep_model,
        _stepwise_e4_run,
    )

    ensure_schema_initialized()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, _bundle, _enrichment = _stepwise_e4_run(run_dir)
    accepted_mep = _mep_model()
    StageRunner(run_dir, manifest).record(
        stage="4_mep",
        stage_dir=run_dir / "4_mep",
        output_obj=accepted_mep,
        report=_clean_report("4_mep"),
    )
    manifest.save(run_dir)
    root_payload = accepted_mep.model_dump(mode="json")
    root_payload["building"]["name"] = "BLOCKED LATER DRAW"
    (run_dir / "4_mep" / "mep_output.json").write_text(
        json.dumps(root_payload), encoding="utf-8"
    )

    write, report = run_stage._draw_assembly(
        run_dir,
        RunPolicy(capability_profile="orthogonal_polygon"),
        manifest,
    )

    mep_record = manifest.accepted("4_mep")
    assert "assembly.mep_identity" not in {row.check_id for row in report.blocking()}
    assert write.intake.building.name == accepted_mep.building.name
    assert dict(write.input_hashes)["4_mep"] == mep_record.output_hash


def test_assembly_rejects_tampered_accepted_mep_archive(tmp_path):
    from src.agent._share import ensure_schema_initialized
    from tests.test_output_coordinate_identity import (
        _clean_report,
        _mep_model,
        _stepwise_e4_run,
    )

    ensure_schema_initialized()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, _bundle, _enrichment = _stepwise_e4_run(run_dir)
    StageRunner(run_dir, manifest).record(
        stage="4_mep",
        stage_dir=run_dir / "4_mep",
        output_obj=_mep_model(),
        report=_clean_report("4_mep"),
    )
    manifest.save(run_dir)
    record = manifest.accepted("4_mep")
    accepted_path = (
        run_dir / "4_mep" / "attempts" / f"{record.accepted_attempt:03d}" / "output.json"
    )
    payload = json.loads(accepted_path.read_text(encoding="utf-8"))
    payload["building"]["name"] = "TAMPERED"
    accepted_path.write_text(json.dumps(payload), encoding="utf-8")

    _output, report = run_stage._draw_assembly(
        run_dir,
        RunPolicy(capability_profile="orthogonal_polygon"),
        manifest,
    )

    assert not report.passed
    assert [row.check_id for row in report.blocking()] == ["assembly.mep_identity"]
