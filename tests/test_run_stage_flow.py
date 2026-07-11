from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.tool_scripts.run_stage as rs
from src.agent.execution import RunManifest, StageOutcome, StageRecord, StepStatus, load_state
from src.agent.execution.manifest import (
    RunManifestV2,
    StageRecordV2,
    ensure_run_manifest_v2,
    hash_file,
    hash_text,
    load_run_manifest,
    save_run_manifest,
)
from src.agent.execution.view_manifest import provision_view_manifest
from src.validator.checks.schema import CheckLayer, CheckReport

_SM21 = Path("case_tests/e2e_tests/sm21_anchor")


def _args(tmp_path, **overrides):
    data = {
        "base_dir": str(tmp_path),
        "case": "case",
        "run": "run",
        "from_stage": "1_correction",
        "to_stage": "1_correction",
        "judge": "off",
        "review": "",
        "geometry": "required",
        "with_ep": False,
        "record": False,
        "record_partial": False,
        "orchestrator": "",
        "llm_config": None,
        "epw": "data/weather/Shenzhen.epw",
        "reading_runner_available": False,
        "run_profile": "exploratory",
        "date": "2026-07-02",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _pass_report(stage: str) -> CheckReport:
    rep = CheckReport(stage=stage)
    rep.add_pass("x", CheckLayer.INVARIANT)
    return rep


def _fake_make_draw_fn(stage, run_dir, *_args, **_kwargs):
    def draw(_fb):
        attempts = run_dir / stage / "attempts"
        n = len([p for p in attempts.glob("*") if p.is_dir()]) if attempts.exists() else 0
        return {"stage": stage, "draw": n + 1}, _pass_report(stage)

    return draw


def _seed_case_data(tmp_path, case: str = "case") -> Path:
    """Minimal real case_data so a run under this case can be V2-provisioned
    (CR-02: cmd_run/flow now provision the trusted view manifest + a V2 run
    identity at entry — a case dir without metadata can no longer host new
    attempt-creating command flows)."""
    import io

    from PIL import Image

    case_dir = tmp_path / case
    (case_dir / "case_data").mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 255, 255)).save(buf, format="PNG")
    (case_dir / "case_data" / "1f_view.png").write_bytes(buf.getvalue())
    (case_dir / "case_data" / "testdata_prompt.json").write_text(
        json.dumps({"Floor plans": [{"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 1}]}),
        encoding="utf-8",
    )
    return case_dir


def _seed_v2_run(case_dir: Path, run_dir: Path, stages: tuple[str, ...] = ()) -> RunManifestV2:
    """A pre-provisioned V2 run with fake accepted base_v2 pointers — what a
    prior flow session leaves behind (replaces the old V1 seeding in tests
    exercising resume/invalidate behavior)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    vm = provision_view_manifest(case_dir, run_dir)
    m = ensure_run_manifest_v2(run_dir, view_manifest_sha256=vm.content_sha256)
    for stage in stages:
        h = hash_text(stage)
        m.accept(
            StageRecordV2(
                stage=stage,
                accepted_attempt=1,
                output_hash=h,
                artifact_contract="base_v2",
                artifact_hashes={"output": h, "checks": hash_text(stage + ".checks")},
            )
        )
    save_run_manifest(m, run_dir)
    return m


def _seed_v1_legacy_run(run_dir: Path, *, stage: str = "0_reading") -> str:
    """A grandfathered legacy run: persisted manifest_version=1 with one
    accepted stage whose real attempt artifacts exist on disk. Returns the
    manifest file's exact bytes for no-write assertions."""
    attempt = run_dir / stage / "attempts" / "001"
    attempt.mkdir(parents=True)
    out_text = json.dumps({"legacy": True})
    (attempt / "output.json").write_text(out_text, encoding="utf-8")
    (attempt / "checks.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    v1 = RunManifest(case=run_dir.parent.name)
    v1.accept(StageRecord(stage=stage, accepted_attempt=1, output_hash=hash_text(out_text)))
    path = v1.save(run_dir)
    return path.read_text(encoding="utf-8")


def test_cmd_run_judge_off_still_writes_correction_renders(tmp_path, monkeypatch):
    def fake_make_draw_fn(stage, run_dir, *_args, **_kwargs):
        def draw(_fb):
            corr = run_dir / "1_correction"
            corr.mkdir(parents=True, exist_ok=True)
            (corr / "correction_geometry_snapped.json").write_text(
                json.dumps(
                    {
                        "footprint_x": [0.0, 10.0],
                        "footprint_y": [0.0, 8.0],
                        "floors": [
                            {
                                "name": "Floor 1",
                                "z_floor": 0.0,
                                "ceiling_height": 3.0,
                                "cells": [
                                    {"id": "A", "role": "office", "x": [0.0, 10.0], "y": [0.0, 8.0]}
                                ],
                            }
                        ],
                        "windows": [],
                    }
                ),
                encoding="utf-8",
            )
            return {"stage": stage}, _pass_report(stage)

        return draw

    monkeypatch.setattr(rs, "_make_draw_fn", fake_make_draw_fn)
    _seed_case_data(tmp_path)

    args = _args(
        tmp_path,
        stage="1_correction",
        force=False,
        capability_profile="rectangular",
    )
    code = rs.cmd_run(args)

    assert code == 0
    corr = tmp_path / "case" / "run" / "1_correction"
    assert (corr / "zones_Floor_1.png").exists()
    assert not (corr / "plan_Floor_1_render.png").exists()
    assert not (corr / "elev_North_render.png").exists()


def test_cmd_resample_invalidates_downstream_before_force_run(tmp_path, monkeypatch):
    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    _seed_v2_run(case_dir, run_dir, stages=tuple(rs._STAGES))
    monkeypatch.setattr(rs, "cmd_run", lambda args: 0)

    code = rs.cmd_resample(
        SimpleNamespace(
            base_dir=str(tmp_path),
            case="case",
            run="run",
            stage="1_correction",
            force=False,
            reading_runner_available=False,
            run_profile="exploratory",
        )
    )

    assert code == 0
    saved = load_run_manifest(run_dir)
    assert set(saved.stages) == {"0_reading", "1_correction"}


def test_flow_human_review_checkpoint_and_approve_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    _seed_case_data(tmp_path)
    args = _args(tmp_path, review="correction")

    code = rs.cmd_flow(args)

    run_dir = tmp_path / "case" / "run"
    assert code == rs.FLOW_EXIT_CHECKPOINT
    assert load_state(run_dir)["stop_reason"] == "awaiting_human_review@1_correction"

    assert rs.cmd_approve_review(
        SimpleNamespace(
            base_dir=str(tmp_path),
            case="case",
            run="run",
            stage="1_correction",
            actor="tester",
            note="ok",
            date="2026-07-02",
        )
    ) == 0
    assert load_state(run_dir)["stop_reason"] is None

    assert rs.cmd_flow(args) == rs.FLOW_EXIT_OK

    manifest = load_run_manifest(run_dir)
    old_hash = manifest.accepted("1_correction").output_hash
    rs.cmd_resample(
        SimpleNamespace(
            base_dir=str(tmp_path),
            case="case",
            run="run",
            stage="1_correction",
            force=False,
            reading_runner_available=False,
            run_profile="exploratory",
            date="2026-07-02",
        )
    )
    new_hash = load_run_manifest(run_dir).accepted("1_correction").output_hash
    assert new_hash != old_hash
    assert rs.cmd_flow(args) == rs.FLOW_EXIT_CHECKPOINT


def test_flow_uses_run_config_defaults_for_judge_and_review(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "run_config.yaml").write_text(
        "\n".join(
            [
                "scope:",
                "  stages: [1_correction]",
                "judge:",
                "  mode: off",
                "review:",
                "  correction: true",
            ]
        ),
        encoding="utf-8",
    )

    code = rs.cmd_flow(_args(tmp_path, review="", judge="stop"))

    assert code == rs.FLOW_EXIT_CHECKPOINT
    assert load_state(run_dir)["stop_reason"] == "awaiting_human_review@1_correction"


def test_flow_first_pass_packet_has_gt_evidence_before_manifest_save(tmp_path, monkeypatch):
    # real sm21 case_data so the run can be V2-provisioned (CR-02)
    shutil.copytree(_SM21 / "case_data", tmp_path / "sm21_anchor" / "case_data")
    output = json.loads(
        (_SM21 / "run_2026-06-20_gpt54_reading/0_reading/attempts/002/output.json")
        .read_text(encoding="utf-8")
    )

    def draw_reading(_stage, _run_dir, *_args, **_kwargs):
        return lambda _fb: (output, _pass_report("0_reading"))

    monkeypatch.setattr(rs, "_make_draw_fn", draw_reading)
    monkeypatch.setattr(rs, "_render_stage", lambda *_args, **_kwargs: [])

    code = rs.cmd_flow(
        _args(
            tmp_path,
            case="sm21_anchor",
            from_stage="0_reading",
            to_stage="0_reading",
            judge="stop",
        )
    )

    run_dir = tmp_path / "sm21_anchor" / "run"
    packet_path = run_dir / "0_reading" / "attempts" / "001" / "judge_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert code == rs.FLOW_EXIT_CHECKPOINT
    assert packet["score_vs_gt"]
    assert Path(packet["score_vs_gt"]).exists()
    assert packet["grade"]
    assert Path(packet["grade"]).exists()
    assert (run_dir / "0_reading" / "grade.png").exists()
    assert packet["score_criteria"]


def test_flow_judge_block_auto_invalidates_and_force_resamples(tmp_path, monkeypatch):
    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    _seed_v2_run(case_dir, run_dir, stages=tuple(rs._STAGES))
    calls = []

    def fake_run_one_stage(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return StageOutcome(
                stage="1_correction",
                status=StepStatus.JUDGE_BLOCK,
                attempts_used=1,
                accepted_attempt=1,
                route_target="1_correction",
                message="block",
            )
        assert kwargs["force_draw"] is True
        return StageOutcome(
            stage="1_correction",
            status=StepStatus.DETERMINISTIC_PASS,
            attempts_used=2,
            accepted_attempt=2,
            report=_pass_report("1_correction"),
            message="pass",
        )

    monkeypatch.setattr(rs, "run_one_stage", fake_run_one_stage)
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)

    code = rs.cmd_flow(_args(tmp_path, judge="stop"))

    assert code == rs.FLOW_EXIT_OK
    assert len(calls) == 2
    saved = load_run_manifest(run_dir)
    assert isinstance(saved, RunManifestV2)
    assert set(saved.stages) == {"0_reading", "1_correction"}


def test_flow_terminal_stop_returns_20(tmp_path, monkeypatch):
    def fake_run_one_stage(**kwargs):
        return StageOutcome(
            stage=kwargs["stage"],
            status=StepStatus.JUDGE_BLOCK_HUMAN,
            attempts_used=1,
            accepted_attempt=1,
            message="human",
        )

    monkeypatch.setattr(rs, "run_one_stage", fake_run_one_stage)
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    _seed_case_data(tmp_path)

    assert rs.cmd_flow(_args(tmp_path, judge="stop")) == rs.FLOW_EXIT_STOP


def test_flow_geometry_auto_records_auto_policy(tmp_path, monkeypatch):
    calls = {"n": 0, "approval": None}

    def fake_run_one_stage(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return StageOutcome(
                stage="3_split_pairing",
                status=StepStatus.AWAITING_GEOMETRY_APPROVAL,
                attempts_used=1,
                accepted_attempt=1,
                message="need geometry",
            )
        return StageOutcome(
            stage="3_split_pairing",
            status=StepStatus.DETERMINISTIC_PASS,
            attempts_used=1,
            accepted_attempt=1,
            report=_pass_report("3_split_pairing"),
            message="pass",
        )

    def fake_approve_geometry(*_args, **kwargs):
        calls["approval"] = kwargs
        return SimpleNamespace(digest="digest", actor=kwargs["actor"], policy=kwargs["policy"])

    monkeypatch.setattr(rs, "run_one_stage", fake_run_one_stage)
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_geometry_viewer", lambda *_args, **_kwargs: "viewer.html")
    monkeypatch.setattr(rs, "approve_geometry", fake_approve_geometry)
    _seed_case_data(tmp_path)

    code = rs.cmd_flow(
        _args(
            tmp_path,
            from_stage="3_split_pairing",
            to_stage="3_split_pairing",
            geometry="auto",
        )
    )

    assert code == rs.FLOW_EXIT_OK
    assert calls["approval"]["actor"] == "flow:auto"
    assert calls["approval"]["policy"] == "auto"


# --------------------------------------------------------------------------- #
# CR-06②: judge-only path is a READ-ONLY view-manifest consumer (§4.4)
# --------------------------------------------------------------------------- #
def _synthetic_judge_case(tmp_path):
    """Minimal real case_data (tiny PNG + metadata) + a run with one accepted
    0_reading attempt, so cmd_judge can run end-to-end without any LLM."""
    import io

    from PIL import Image

    case_dir = tmp_path / "case"
    run_dir = case_dir / "run"
    (case_dir / "case_data").mkdir(parents=True)
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 255, 255)).save(buf, format="PNG")
    (case_dir / "case_data" / "1f_view.png").write_bytes(buf.getvalue())
    (case_dir / "case_data" / "testdata_prompt.json").write_text(
        json.dumps({"Floor plans": [{"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 1}]}),
        encoding="utf-8",
    )
    attempt = run_dir / "0_reading" / "attempts" / "001"
    attempt.mkdir(parents=True)
    (attempt / "output.json").write_text("{}", encoding="utf-8")
    manifest = RunManifest(case="run")
    manifest.accept(StageRecord(stage="0_reading", accepted_attempt=1, output_hash="x"))
    manifest.save(run_dir)
    verdict_path = tmp_path / "verdict.json"
    verdict_path.write_text(
        json.dumps({"stage": "0_reading", "rubric_id": "J0", "criteria": []}),
        encoding="utf-8",
    )
    return case_dir, run_dir, verdict_path


def test_cmd_judge_missing_view_manifest_is_not_applicable(tmp_path, capsys):
    """A run that predates the view-manifest wire judges exactly as before
    (NOT_APPLICABLE) — and the read-only judge path never provisions one."""
    case_dir, run_dir, verdict_path = _synthetic_judge_case(tmp_path)

    args = _args(tmp_path, stage="0_reading", verdict=str(verdict_path))
    code = rs.cmd_judge(args)

    assert code == 0
    out = capsys.readouterr().out
    assert "NOT_APPLICABLE" in out
    # read-only: judging must not have provisioned a manifest
    assert not (run_dir / "_run" / "view_manifest.json").exists()


def test_cmd_judge_drifted_view_manifest_fails_without_writing(tmp_path, capsys):
    """A present-but-drifted manifest is an INVARIANT fail: exit 2, no verdict
    persisted, and the drifted manifest is never 'fixed' (no provision)."""
    from src.agent.execution.view_manifest import provision_view_manifest

    case_dir, run_dir, verdict_path = _synthetic_judge_case(tmp_path)
    provision_view_manifest(case_dir, run_dir)
    vm_path = run_dir / "_run" / "view_manifest.json"
    tampered_bytes_before = json.loads(vm_path.read_text(encoding="utf-8"))
    # drift: case_data image changes under the committed manifest
    (case_dir / "case_data" / "1f_view.png").write_bytes(
        (case_dir / "case_data" / "1f_view.png").read_bytes() + b"\x00"
    )

    args = _args(tmp_path, stage="0_reading", verdict=str(verdict_path))
    code = rs.cmd_judge(args)

    assert code == 2
    out = capsys.readouterr().out
    assert "INVARIANT" in out
    # nothing judged, nothing repaired: verdict absent, manifest bytes untouched
    assert not (run_dir / "0_reading" / "attempts" / "001" / "judge.json").exists()
    assert json.loads(vm_path.read_text(encoding="utf-8")) == tampered_bytes_before


# --------------------------------------------------------------------------- #
# CR-02: grandfather hard gate at all three attempt-creating entrances +
# V2-by-default for new runs (B-M §5.1)
# --------------------------------------------------------------------------- #
def test_cmd_run_refuses_persisted_v1_run(tmp_path, monkeypatch):
    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    _seed_v1_legacy_run(run_dir)
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)

    with pytest.raises(SystemExit, match="grandfathered"):
        rs.cmd_run(_args(tmp_path, stage="1_correction", force=False))

    # no new attempt was created anywhere
    assert not (run_dir / "1_correction").exists()


def test_cmd_flow_refuses_persisted_v1_run(tmp_path, monkeypatch):
    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    _seed_v1_legacy_run(run_dir)
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)

    with pytest.raises(SystemExit, match="grandfathered"):
        rs.cmd_flow(_args(tmp_path))

    assert not (run_dir / "1_correction").exists()


def test_cmd_resample_refuses_persisted_v1_before_any_write(tmp_path, monkeypatch):
    """terra r1 point-named: the refusal must fire BEFORE resample's
    invalidate()/save() — the persisted V1 manifest's bytes are untouched."""
    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    v1_bytes = _seed_v1_legacy_run(run_dir)
    monkeypatch.setattr(rs, "cmd_run", lambda args: 0)  # must never be reached

    with pytest.raises(SystemExit, match="grandfathered"):
        rs.cmd_resample(
            SimpleNamespace(
                base_dir=str(tmp_path),
                case="case",
                run="run",
                stage="0_reading",
                force=False,
                reading_runner_available=False,
                run_profile="exploratory",
            )
        )

    assert (run_dir / "_run" / "run_manifest.json").read_text(encoding="utf-8") == v1_bytes
    assert not (run_dir / "_run" / "view_manifest.json").exists()


def test_new_run_flow_smoke_produces_v2_base_v2_records(tmp_path, monkeypatch):
    """New-run end-to-end flow smoke (CR-02): a fresh run is V2-by-default and
    every accepted stage record is a base_v2 StageRecordV2 whose
    artifact_hashes are the REAL recomputed hashes of the attempt files."""
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *_a, **_k: [])
    monkeypatch.setattr(rs, "geometry_is_approved", lambda *_a, **_k: True)

    code = rs.cmd_flow(_args(tmp_path, from_stage="0_reading", to_stage="5_intakeoutput"))

    assert code == rs.FLOW_EXIT_OK
    saved = load_run_manifest(run_dir)
    assert isinstance(saved, RunManifestV2)
    assert saved.run_inputs.view_manifest_sha256
    assert set(saved.stages) == set(rs._STAGES)
    for stage, rec in saved.stages.items():
        assert rec.artifact_contract == "base_v2", stage
        adir = run_dir / stage / "attempts" / f"{rec.accepted_attempt:03d}"
        assert rec.artifact_hashes["output"] == hash_file(adir / "output.json")
        assert rec.artifact_hashes["checks"] == hash_file(adir / "checks.json")
        assert rec.output_hash == rec.artifact_hashes["output"]


def test_v1_run_resumable_after_explicit_migration(tmp_path, monkeypatch):
    """The sanctioned unlock path: a refused V1 run becomes writable again
    only through the explicit `provision --migrate`, keeping the migration's
    run identity and writing new records as base_v2."""
    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    _seed_v1_legacy_run(run_dir)  # accepted 0_reading with real artifacts
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *_a, **_k: [])

    with pytest.raises(SystemExit, match="grandfathered"):
        rs.cmd_run(_args(tmp_path, stage="1_correction", force=False))

    assert rs.cmd_provision(
        SimpleNamespace(base_dir=str(tmp_path), case="case", run="run", migrate=True)
    ) == 0
    migrated = load_run_manifest(run_dir)
    assert isinstance(migrated, RunManifestV2)
    assert migrated.stages["0_reading"].artifact_contract == "migrated_v1"

    code = rs.cmd_run(_args(tmp_path, stage="1_correction", force=False))

    assert code == 0
    saved = load_run_manifest(run_dir)
    assert saved.run_id == migrated.run_id  # identity survives the resume
    assert saved.stages["0_reading"].artifact_contract == "migrated_v1"
    assert saved.stages["1_correction"].artifact_contract == "base_v2"
