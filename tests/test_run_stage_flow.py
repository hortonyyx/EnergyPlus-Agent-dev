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


@pytest.mark.parametrize(
    "config_line,cli_profile,expected",
    [
        ("capability_profile: orthogonal_polygon", "rectangular", "orthogonal_polygon"),
        ("", "orthogonal_polygon", "orthogonal_polygon"),
    ],
)
def test_flow_run_config_capability_profile_overrides_only_when_present(
    tmp_path, monkeypatch, config_line, cli_profile, expected
):
    seen = []

    def capture_draw_fn(stage, run_dir, testdata_text, td_path, policy, manifest=None):
        seen.append(policy.capability_profile)
        return _fake_make_draw_fn(
            stage, run_dir, testdata_text, td_path, policy, manifest=manifest
        )

    monkeypatch.setattr(rs, "_make_draw_fn", capture_draw_fn)
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "run_config.yaml").write_text(
        "\n".join(filter(None, ["judge:", "  mode: off", config_line])),
        encoding="utf-8",
    )

    assert rs.cmd_flow(
        _args(tmp_path, capability_profile=cli_profile, judge="off")
    ) == rs.FLOW_EXIT_OK
    assert seen == [expected]


@pytest.mark.parametrize(
    "config_line,cli_profile,expected",
    [
        ("capability_profile: orthogonal_polygon", "rectangular", "orthogonal_polygon"),
        ("", "orthogonal_polygon", "orthogonal_polygon"),
    ],
)
def test_cmd_run_config_capability_profile_overrides_only_when_present(
    tmp_path, monkeypatch, config_line, cli_profile, expected
):
    seen = []

    def capture_draw_fn(stage, run_dir, testdata_text, td_path, policy, manifest=None):
        seen.append(policy.capability_profile)
        return _fake_make_draw_fn(
            stage, run_dir, testdata_text, td_path, policy, manifest=manifest
        )

    monkeypatch.setattr(rs, "_make_draw_fn", capture_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *args, **kwargs: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "run_config.yaml").write_text(config_line, encoding="utf-8")

    assert rs.cmd_run(
        _args(
            tmp_path,
            stage="1_correction",
            force=False,
            capability_profile=cli_profile,
        )
    ) == 0
    assert seen == [expected]


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
    import src.agent.execution.manifest as manifest_module

    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    _seed_v1_legacy_run(run_dir)
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    calls = []
    real_guard = manifest_module.reading_attempt_allowed

    def recording_guard(path):
        calls.append(path)
        return real_guard(path)

    monkeypatch.setattr(manifest_module, "reading_attempt_allowed", recording_guard)

    with pytest.raises(SystemExit, match="grandfathered"):
        rs.cmd_run(_args(tmp_path, stage="1_correction", force=False))

    assert calls == [run_dir]
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


# --------------------------------------------------------------------------- #
# R1-1 (S-2): flow/run SOP path — both profiles same source rule + freeze the
# effective policy in the provision_run transaction (r0 wired only isolation +
# cmd_provision; cmd_run/cmd_flow left the resolver legacy_defaulted every time,
# so a run_config.yaml declaring regression silently ran exploratory).
# --------------------------------------------------------------------------- #
_USABLE_ORIGIN = {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None}


def _non_closing_plan_payload():
    """A plan view JSON whose only fault is a non-closing dimension chain
    (overall 6.0 ≠ Σ segments 2.0+3.0 = 5.0) → dimension_chain_closure FAILs.
    Every other field is well-formed so the refusal can only come from the
    closure check (the R1-1 regression-block signal)."""
    return {
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}},
        ],
        "dimensions": [
            {"id": "D0", "text_verbatim": "6.0", "value_m": 6.0, "chain_id": "c",
             "role": "overall", "order": 0, "axis": "x", "from": [0, 0], "to": [6, 0]},
            {"id": "D1", "text_verbatim": "2.0", "value_m": 2.0, "chain_id": "c",
             "role": "segment", "order": 1, "axis": "x", "from": [0, 0], "to": [2, 0]},
            {"id": "D2", "text_verbatim": "3.0", "value_m": 3.0, "chain_id": "c",
             "role": "segment", "order": 2, "axis": "x", "from": [2, 0], "to": [5, 0]},
        ],
        "scale_origin": dict(_USABLE_ORIGIN),
    }


def test_R1_1_flow_config_run_profile_overrides_cli_default(tmp_path, monkeypatch):
    """R1-1a: run_config.yaml declares regression; CLI --run-profile is left at
    its exploratory default ⇒ cmd_flow resolves run_profile=regression (both
    profiles now follow the same config-wins rule; previously run_profile came
    from CLI only and the declaration was silently discarded). Neuter: revert
    run_profile to args.run_profile ⇒ seen == [('exploratory', ...)] ⇒ red."""
    seen = []

    def capture(stage, run_dir, testdata_text, td_path, policy, manifest=None):
        seen.append((policy.run_profile, policy.capability_profile))
        return _fake_make_draw_fn(stage, run_dir, testdata_text, td_path, policy, manifest=manifest)

    monkeypatch.setattr(rs, "_make_draw_fn", capture)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\n"
        "run_profile: regression\ncapability_profile: orthogonal_polygon\n",
        encoding="utf-8",
    )

    assert rs.cmd_flow(_args(tmp_path, run_profile="exploratory", judge="off")) == rs.FLOW_EXIT_OK
    assert seen == [("regression", "orthogonal_polygon")]


def test_R1_1_flow_freezes_run_policy_not_legacy_defaulted(tmp_path, monkeypatch):
    """R1-1b: cmd_flow on a NEW run freezes the effective policy via the
    provision_run transaction (_manifest_for_attempts) ⇒ _run/run_policy.json
    exists with source=structured_config + legacy_defaulted=false. Neuter: skip
    the provision_run wiring in _manifest_for_attempts ⇒ run_policy.json absent
    ⇒ resolver returns legacy_defaulted=true ⇒ red."""
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\n"
        "run_profile: regression\ncapability_profile: orthogonal_polygon\n",
        encoding="utf-8",
    )

    assert rs.cmd_flow(_args(tmp_path, run_profile="exploratory", judge="off")) == rs.FLOW_EXIT_OK
    record = resolve_frozen_run_policy(run_dir)
    assert record.run_profile == "regression"
    assert record.capability_profile == "orthogonal_polygon"
    assert record.source == "structured_config"
    assert not record.legacy_defaulted


def test_R1_1_flow_regression_freezes_to_reading_checks_header(tmp_path, monkeypatch):
    """R1-1c (派工单 §1.4): 端到端真实 cmd_flow + 真实 _draw_reading —
    run_config.yaml 声明 regression+orthogonal，不传 CLI --run-profile（args 默认
    exploratory）⇒ 0_reading attempt 的 checks.json 头部 run_profile=regression /
    capability_profile=orthogonal_polygon / run_policy_sha256 非 None /
    run_policy_source=structured_config，且非闭合尺寸链的 dimension_chain_closure
    在 regression 下 BLOCK。Neuter: 两字段同来源退回（run_profile=args）⇒ 头部退回
    exploratory + run_policy_sha256=None（legacy_defaulted）⇒ 头部断言红。"""
    from src.validator.checks.schema import CheckStatus

    case_dir = _seed_case_data(tmp_path)
    run_dir = case_dir / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "run_profile: regression\ncapability_profile: orthogonal_polygon\n",
        encoding="utf-8",
    )
    rdir = run_dir / "0_reading"
    rdir.mkdir()
    (rdir / "1f_view.json").write_text(
        json.dumps(_non_closing_plan_payload()), encoding="utf-8"
    )
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])

    rs.cmd_flow(_args(
        tmp_path, from_stage="0_reading", to_stage="0_reading",
        run_profile="exploratory", judge="off",
    ))

    checks_path = run_dir / "0_reading" / "attempts" / "001" / "checks.json"
    assert checks_path.exists(), "0_reading attempt checks.json must be filed even on block"
    report = CheckReport.model_validate_json(checks_path.read_text(encoding="utf-8"))
    # header fields — the declared regression actually took effect on the SOP path
    assert report.run_profile == "regression"
    assert report.capability_profile == "orthogonal_polygon"
    assert report.run_policy_sha256
    assert report.run_policy_source == "structured_config"
    # check-id row — the non-closing chain BLOCKs under regression (FLAG under exploratory)
    closure = next(r for r in report.results
                   if r.check_id == "1f_view.reading.dimension_chain_closure")
    assert closure.status is CheckStatus.FAIL
    assert any(r.check_id == "1f_view.reading.dimension_chain_closure"
               for r in report.blocking())


# --------------------------------------------------------------------------- #
# R1-2 (S-2): a present-but-invalid run_profile (one-letter typo) is
# fail-closed on the NEW-run provisioning path, not warn+ignore. r0's
# _parse_run_profile warned + returned None, which _resolve_run_profiles then
# fell back past to the CLI exploratory default — so 'regresion' silently ran
# exploratory (派工单 §1.2).
# --------------------------------------------------------------------------- #
def test_R1_2_flow_typo_run_profile_fails_closed(tmp_path, monkeypatch):
    """R1-2 (派工单 §1.2): run_config.yaml 把 run_profile 拼错一个字母
    (regresion) ⇒ cmd_flow（真实 CLI 命令函数）fail-closed，不静默降回
    exploratory、不冻结任何 policy。Neuter: _parse_run_profile 回 warn+None ⇒
    load_run_config 不 raise ⇒ cmd_flow 成功跑 exploratory ⇒ pytest.raises
    失败 ⇒ 红。"""
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\nrun_profile: regresion\n",  # one-letter typo
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="run_profile_invalid"):
        rs.cmd_flow(_args(tmp_path, run_profile="exploratory", judge="off"))
    # fail-closed BEFORE any freeze: no run policy, no run manifest minted
    assert not (run_dir / "_run" / "run_policy.json").exists()
    assert not (run_dir / "_run" / "run_manifest.json").exists()


def test_R1_2_absent_run_profile_still_cli_authoritative(tmp_path, monkeypatch):
    """R1-2 对照：run_config.yaml 完全不声明 run_profile（absent，legacy）⇒ 不
    fail-closed，CLI --run-profile 兜底（G-6 legacy/CLI 权威）。证明 R1-2 只对
    『显式声明了非法值』fail-closed，不对『未声明』fail-closed。"""
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text("judge:\n  mode: off\n", encoding="utf-8")

    assert rs.cmd_flow(_args(tmp_path, run_profile="regression", judge="off")) == rs.FLOW_EXIT_OK
    # CLI regression froze (absent config ⇒ CLI authoritative, NOT fail-closed)
    record = resolve_frozen_run_policy(run_dir)
    assert record.run_profile == "regression"
    # r2-2: neither profile declared in config ⇒ source is "cli" (not the
    # vacuous "structured_config" the hardcoded constant produced before).
    assert record.source == "cli"


# --------------------------------------------------------------------------- #
# r2-1 (ruling 2026-08-04 §r2-1): a present-but-invalid capability_profile
# (one-letter typo) is fail-closed on the NEW-run provisioning path — the
# symmetric counterpart of R1-2. r0's _parse_capability_profile warned + returned
# None, so 'orthogonal_polygone' silently demoted to rectangular (CLI default),
# and capability decides correction v2 vs v3 schema (wider than judging strictness).
# --------------------------------------------------------------------------- #
def test_r2_1_flow_typo_capability_profile_fails_closed(tmp_path, monkeypatch):
    """r2-1: run_config.yaml 把 capability_profile 拼错一个字母
    (orthogonal_polygone) ⇒ cmd_flow（真实 CLI 命令函数）fail-closed，不静默降回
    rectangular、不冻结任何 policy。形态照抄 R1-2 typo 锁。
    Neuter: _parse_capability_profile 回 warn+None ⇒ load_run_config 不 raise ⇒
    cmd_flow 成功跑 rectangular ⇒ pytest.raises 失败 ⇒ 红。"""
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\nrun_profile: regression\n"
        "capability_profile: orthogonal_polygone\n",  # one-letter typo
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="capability_profile_invalid"):
        rs.cmd_flow(_args(tmp_path, run_profile="regression", judge="off"))
    # fail-closed BEFORE any freeze: no run policy, no run manifest minted
    assert not (run_dir / "_run" / "run_policy.json").exists()
    assert not (run_dir / "_run" / "run_manifest.json").exists()


def test_r2_1_absent_capability_profile_still_cli_authoritative(tmp_path, monkeypatch):
    """r2-1 对照：run_config.yaml 完全不声明 capability_profile（absent）⇒ 不
    fail-closed，CLI 默认 rectangular 兜底冻结（G-6 legacy/CLI 权威）。证明 r2-1
    只对『显式声明了非法值』fail-closed，不对『未声明』fail-closed。形态照抄
    R1-2 absent 对照锁。"""
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    # declares run_profile but NOT capability_profile (absent)
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\nrun_profile: regression\n", encoding="utf-8"
    )

    assert rs.cmd_flow(_args(tmp_path, run_profile="regression", judge="off")) == rs.FLOW_EXIT_OK
    # absent capability ⇒ CLI default rectangular froze (CLI authoritative, NOT fail-closed)
    record = resolve_frozen_run_policy(run_dir)
    assert record.capability_profile == "rectangular"
    assert record.run_profile == "regression"
    # r2-2: run_profile declared in config, capability CLI-sourced ⇒ "mixed"
    assert record.source == "mixed"


# --------------------------------------------------------------------------- #
# r2-2 (ruling 2026-08-04 §r2-2): the frozen record's ``source`` must reflect
# where (run_profile, capability_profile) came from — structured_config / cli /
# mixed — not be a hardcoded "structured_config" constant. r0/r1 hardcoded it in
# _build_record, so a pure --run-profile run (no config declaration) was
# mislabeled "from structured config" and R1-1b's assert was vacuous (恒真).
# Drift re-verification is scoped to config-declared fields, so source makes the
# applicability machine-visible.
# --------------------------------------------------------------------------- #
def test_r2_2_cli_only_run_source_is_cli(tmp_path, monkeypatch):
    """r2-2 lock A: run_config.yaml declares NEITHER run_profile nor
    capability_profile, CLI --run-profile regression is the only authority ⇒
    frozen record source == "cli" (NOT "structured_config"). A pure CLI run must
    not be mislabeled as structured-config-sourced.
    Neuter: _resolve_run_profiles 回硬编码 source="structured_config" ⇒ 断言红。"""
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text("judge:\n  mode: off\n", encoding="utf-8")

    assert rs.cmd_flow(_args(tmp_path, run_profile="regression", judge="off")) == rs.FLOW_EXIT_OK
    record = resolve_frozen_run_policy(run_dir)
    assert record.source == "cli"
    assert record.source != "structured_config"


def test_r2_2_structured_decl_source_is_structured(tmp_path, monkeypatch):
    """r2-2 lock B: run_config.yaml declares BOTH run_profile and
    capability_profile ⇒ frozen source == "structured_config". This is the
    formerly-vacuous assertion, now meaningful (cli/mixed are real alternatives).
    Neuter: _resolve_run_profiles 回硬编码 ⇒ 断言可被 cli/mixed 撕裂（见 lock A/C）。"""
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\n"
        "run_profile: regression\ncapability_profile: orthogonal_polygon\n",
        encoding="utf-8",
    )

    assert rs.cmd_flow(_args(tmp_path, run_profile="exploratory", judge="off")) == rs.FLOW_EXIT_OK
    record = resolve_frozen_run_policy(run_dir)
    assert record.source == "structured_config"


def test_r2_2_mixed_decl_source_is_mixed(tmp_path, monkeypatch):
    """r2-2 lock C (third state): config declares run_profile only (capability
    CLI-sourced) ⇒ source == "mixed". 证明三态分类对『只声明一个』给出独立第三值，
    不是塞进 structured_config 或 cli。
    Neuter: _resolve_run_profiles 回硬编码 ⇒ 断言红。"""
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\nrun_profile: regression\n", encoding="utf-8"
    )

    assert rs.cmd_flow(_args(tmp_path, run_profile="regression", judge="off")) == rs.FLOW_EXIT_OK
    record = resolve_frozen_run_policy(run_dir)
    assert record.source == "mixed"


# --------------------------------------------------------------------------- #
# R1-7 (派工单 §1.7): a structured config declaration and an EXPLICIT CLI flag
# that DISAGREE is fail-closed, not silent "config wins". The argparse CLI
# default (exploratory) counts as "not passed" — config still wins there.
# --------------------------------------------------------------------------- #
def test_R1_7_config_cli_run_profile_conflict_raises(tmp_path, monkeypatch):
    """R1-7: run_config.yaml 声明 regression + CLI --run-profile golden（显式不同的
    严格档）⇒ cmd_flow fail-closed raise 'run_profile conflict'，不静默取 config。
    r0/R1-1 的 'config or CLI' 静默取 config ⇒ 冻结的严格声明被 CLI 偷换而无人知。
    Neuter: _resolve_run_profiles 去掉冲突检测 ⇒ config 赢、不 raise ⇒ 红。"""
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text("run_profile: regression\n", encoding="utf-8")
    with pytest.raises(ValueError, match="run_profile conflict"):
        rs.cmd_flow(_args(tmp_path, run_profile="golden", judge="off"))


def test_R1_7_config_cli_same_value_no_conflict(tmp_path, monkeypatch):
    """R1-7 对照: run_config.yaml 声明 regression + CLI --run-profile regression
    （显式传但与 config 相同）⇒ 不报错（cli == cfg，无冲突）。证明 R1-7 只对
    『不同的值』raise，CLI 显式确认 config 的同值不误伤。"""
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\nrun_profile: regression\n", encoding="utf-8"
    )
    assert rs.cmd_flow(_args(tmp_path, run_profile="regression", judge="off")) == rs.FLOW_EXIT_OK
    record = resolve_frozen_run_policy(run_dir)
    assert record.run_profile == "regression"


# --------------------------------------------------------------------------- #
# R1-1 context wiring (J-1 §1.2, orchestrator ruling 2026-08-03): the non-hash
# audit context is wired for real (4 toggles + sources) and does NOT enter the
# drift hash. R1-1 left context=None pending the ruling.
# --------------------------------------------------------------------------- #
def test_R1_1_context_recorded_with_sources(tmp_path, monkeypatch):
    """J-1 §1.2: provision 的 context 真接上（含 validation_scope/require_ep/
    confirmation_policy/judge_enabled 的值+来源）且写进 run_policy.json。r0/R1-1 的
    context=None ⇒ context={}（其余 toggle 从未记录，收窄的正当性落空）。
    Neuter: _run_policy_context 返回 {} ⇒ context 空 ⇒ KeyError ⇒ 红。"""
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: stop\nrun_profile: regression\n", encoding="utf-8"
    )
    rs.cmd_flow(_args(tmp_path, run_profile="exploratory", judge="off", with_ep=True))
    from src.agent.execution.run_policy_freeze import resolve_frozen_run_policy

    record = resolve_frozen_run_policy(run_dir)
    ctx = record.context
    assert {"judge_enabled", "confirmation_policy", "validation_scope", "require_ep"} <= set(ctx)
    # judge_mode from structured_config (run_config.yaml mode: stop), NOT CLI --judge off
    assert ctx["judge_enabled"]["judge_mode"] == "stop"
    assert ctx["judge_enabled"]["source"] == "structured_config"
    assert ctx["judge_enabled"]["value"] is True          # stop != off
    assert ctx["require_ep"]["value"] is True              # --with-ep
    assert ctx["require_ep"]["source"] == "cli"
    assert ctx["confirmation_policy"]["value"] == "required"
    assert ctx["validation_scope"]["value"] == "full"


def test_R1_1_context_not_in_hash_no_drift(tmp_path):
    """J-1 §1.2: context 不进 policy_hash —— 同 (capability, run_profile) + 不同 context
    ⇒ policy_hash 逐字相同 + 第二次 provision 不 drift（idempotent，返回 existing）。
    Neuter: _run_policy_hash 纳入 context ⇒ 两次 policy_hash 不同 ⇒ 第二次 raise
    run_policy_drift ⇒ 红。"""
    from src.agent.execution.run_policy_freeze import provision_run_policy

    run_dir = tmp_path / "run_ctx"
    run_dir.mkdir()
    rec1 = provision_run_policy(
        run_dir, run_profile="regression", capability_profile="rectangular",
        context={"judge_enabled": {"value": True, "judge_mode": "stop", "source": "structured_config"}},
    )
    # re-provision with DIFFERENT context but identical profiles ⇒ idempotent, no drift
    rec2 = provision_run_policy(
        run_dir, run_profile="regression", capability_profile="rectangular",
        context={"judge_enabled": {"value": False, "judge_mode": "off", "source": "cli"}},
    )
    assert rec2.policy_hash == rec1.policy_hash   # context not in hash
    assert rec2.context == rec1.context            # idempotent: existing record returned


# --------------------------------------------------------------------------- #
# R1-5 · geometry confirmation must validate with the FROZEN policy (J-1
# ruling §1.3).  This goes through the real approve-geometry command function;
# the wrapper only retains the real CheckReport for assertions, it does not
# fabricate the validation result.
# --------------------------------------------------------------------------- #
def test_R1_5_approve_geometry_uses_frozen_policy_check_headers(tmp_path, monkeypatch):
    """A frozen regression/orthogonal run must reach the human geometry gate
    validating at that frozen TIER.  r2-4 (ruling 2026-08-04 §2): require_ep is
    NO LONGER read from frozen context — it is a per-invocation operational knob,
    and the geometry gate (which has no --with-ep) validates at the default
    require_ep=False, so no downstream.build row is produced here.  The frozen
    tier being consumed (not RunPolicy() defaults) is proven by BOTH the
    stage-report headers AND a tier-gated check-id row (r2c-2, cross-review F-4:
    the r2b rewrite had dropped the check-id row half).  Neuter: replace
    effective_run_policy with RunPolicy() ⇒ tier headers become
    exploratory/rectangular AND the non-closing chain FLAGs instead of BLOCKs ⇒
    this lock reds on both halves."""
    from src.agent.execution import validation_run
    from src.agent.execution.run_policy_freeze import provision_run_policy
    from src.validator.checks.schema import CheckStatus

    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir(parents=True)
    provision_run_policy(
        run_dir,
        run_profile="regression",
        capability_profile="orthogonal_polygon",
    )
    # r2c-2: plant a non-closing dimension chain so a TIER-GATED check-id row
    # (reading.dimension_chain_closure: BLOCK under regression, FLAG under
    # exploratory) flows through validate_case — the check-id half r2b dropped.
    rdir = run_dir / "0_reading"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "1f_view.json").write_text(
        json.dumps(_non_closing_plan_payload()), encoding="utf-8")
    real_validate_case = validation_run.validate_case
    seen = {}

    def capture_validate_case(*args, **kwargs):
        result = real_validate_case(*args, **kwargs)
        seen["result"] = result
        return result

    monkeypatch.setattr(validation_run, "validate_case", capture_validate_case)
    code = rs.cmd_approve_geometry(_args(
        tmp_path, actor="reviewer", policy="required", note="",
    ))

    assert code == 2  # intentionally no geometry checkpoint in this focused fixture
    # r2-4: require_ep comes from the caller (default False here), never from
    # frozen context ⇒ no "downstream" report. The frozen TIER consumed is proven
    # by the stage-report headers (regression/orthogonal, not RunPolicy defaults).
    assert "downstream" not in seen["result"].reports
    stage_report = seen["result"].reports["1_correction"]
    assert stage_report.run_profile == "regression"
    assert stage_report.capability_profile == "orthogonal_polygon"
    # r2c-2: the check-id half — the non-closing chain FAIL is BLOCK only because
    # the tier fed to validate_case was regression (exploratory would FLAG it).
    reading_report = seen["result"].reports["0_reading::1f_view"]
    closure = next(r for r in reading_report.results
                   if r.check_id == "reading.dimension_chain_closure")
    assert closure.status is CheckStatus.FAIL
    assert any(r.check_id == "reading.dimension_chain_closure"
               for r in reading_report.blocking())


def test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers(tmp_path, monkeypatch):
    """The resume predicate is the second real geometry caller and must validate
    at the frozen TIER, not RunPolicy() defaults.  r2-4: require_ep no longer
    comes from frozen context (geometry gate uses default require_ep=False ⇒ no
    downstream row).  r2c-2 (cross-review F-4): the check-id row half dropped in
    the r2b rewrite is restored — a tier-gated non-closing chain BLOCKs under
    regression.  Neuter effective_run_policy ⇒ the stage-report tier headers AND
    the check-id row red alongside only the paired approval lock, because both
    callers share that hook."""
    from src.agent.execution import step_orchestrator, validation_run
    from src.agent.execution.run_policy_freeze import provision_run_policy
    from src.validator.checks.schema import CheckStatus

    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir(parents=True)
    provision_run_policy(
        run_dir,
        run_profile="regression",
        capability_profile="orthogonal_polygon",
    )
    # r2c-2: tier-gated check-id row (non-closing chain: BLOCK under regression).
    rdir = run_dir / "0_reading"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "1f_view.json").write_text(
        json.dumps(_non_closing_plan_payload()), encoding="utf-8")
    real_validate_case = validation_run.validate_case
    seen = {}

    def capture_validate_case(*args, **kwargs):
        result = real_validate_case(*args, **kwargs)
        seen["result"] = result
        return result

    monkeypatch.setattr(validation_run, "validate_case", capture_validate_case)
    assert step_orchestrator.geometry_is_approved(run_dir) is False

    assert "downstream" not in seen["result"].reports
    stage_report = seen["result"].reports["1_correction"]
    assert stage_report.run_profile == "regression"
    assert stage_report.capability_profile == "orthogonal_polygon"
    # r2c-2: the check-id half — non-closing chain FAIL BLOCKs under regression.
    reading_report = seen["result"].reports["0_reading::1f_view"]
    closure = next(r for r in reading_report.results
                   if r.check_id == "reading.dimension_chain_closure")
    assert closure.status is CheckStatus.FAIL
    assert any(r.check_id == "reading.dimension_chain_closure"
               for r in reading_report.blocking())
