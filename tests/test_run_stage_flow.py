from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.tool_scripts.run_stage as rs
from src.agent.execution import RunManifest, StageOutcome, StageRecord, StepStatus, load_state
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
    run_dir = tmp_path / "case" / "run"
    manifest = RunManifest(case="run")
    for stage in rs._STAGES:
        manifest.accept(StageRecord(stage=stage, accepted_attempt=1, output_hash=stage))
    manifest.save(run_dir)
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
    saved = RunManifest.load(run_dir)
    assert set(saved.stages) == {"0_reading", "1_correction"}


def test_flow_human_review_checkpoint_and_approve_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
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

    manifest = RunManifest.load(run_dir)
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
    new_hash = RunManifest.load(run_dir).accepted("1_correction").output_hash
    assert new_hash != old_hash
    assert rs.cmd_flow(args) == rs.FLOW_EXIT_CHECKPOINT


def test_flow_uses_run_config_defaults_for_judge_and_review(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
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
    run_dir = tmp_path / "case" / "run"
    manifest = RunManifest(case="run")
    for stage in rs._STAGES:
        manifest.accept(StageRecord(stage=stage, accepted_attempt=1, output_hash=stage))
    manifest.save(run_dir)
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
    saved = RunManifest.load(run_dir)
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
