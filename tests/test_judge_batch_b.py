from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

import scripts.tool_scripts.run_stage as rs
from src.agent.execution import RunManifest
from src.agent.judge.correction_score import score_correction_geometry
from src.agent.judge.gt import load_gt
from src.agent.judge.verdict import StageVerdict
from src.validator.checks.schema import CheckLayer, CheckReport

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_grade  # noqa: E402
from _grade_transform import plan_transform  # noqa: E402


_SM21 = Path("case_tests/e2e_tests/sm21_anchor")


def _pass_report(stage: str) -> CheckReport:
    rep = CheckReport(stage=stage)
    rep.add_pass("x", CheckLayer.INVARIANT)
    return rep


def _copy_run_subset(tmp_path: Path, run_name: str, files: list[tuple[str, str]]) -> Path:
    case_dir = tmp_path / "sm21_anchor"
    run_dir = case_dir / "run"
    (run_dir / "_run").mkdir(parents=True)
    shutil.copy2(_SM21 / run_name / "_run" / "run_manifest.json", run_dir / "_run" / "run_manifest.json")
    for src_rel, dst_rel in files:
        dst = run_dir / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_SM21 / run_name / src_rel, dst)
    return run_dir


def test_judge_packet_scores_accepted_reading_attempt_not_mutable_flat(tmp_path, monkeypatch):
    run_dir = _copy_run_subset(
        tmp_path,
        "run_2026-06-20_gpt54_reading",
        [
            ("0_reading/attempts/002/output.json", "0_reading/attempts/002/output.json"),
            ("0_reading/1f_view.json", "0_reading/1f_view.json"),
        ],
    )
    case_dir = tmp_path / "sm21_anchor"
    flat = run_dir / "0_reading" / "1f_view.json"
    flat.write_text(json.dumps({"image_kind": "plan", "strokes": []}), encoding="utf-8")
    monkeypatch.setattr(rs, "_render_stage", lambda *_args, **_kwargs: [])

    packet = rs._judge_packet(
        "0_reading",
        "sm21_anchor",
        case_dir,
        run_dir,
        run_dir / "0_reading" / "attempts" / "002",
        _pass_report("0_reading"),
    )

    sidecar_path = Path(packet["score_vs_gt"])
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    rec = RunManifest.load(run_dir).accepted("0_reading")
    assert sidecar["stage"] == "0_reading"
    assert sidecar["attempt"] == 2
    assert sidecar["source"] == "attempt_output"
    assert sidecar["output_hash"] == rec.output_hash
    assert sidecar["tolerances"] == {"wall_tol_m": 0.3, "window_centre_tol_m": 0.4}
    assert packet["grade"] == str(run_dir / "0_reading" / "attempts" / "002" / "grade.png")
    assert Path(packet["grade"]).exists()
    assert packet["score_criteria"] == sidecar["score_criteria"]
    assert {c["criterion"] for c in packet["score_criteria"]} >= {
        "walls_complete",
        "windows_placed",
        "no_oversplit",
    }
    assert all("suggested_status" in c for c in packet["score_criteria"])
    with pytest.raises(Exception):
        StageVerdict.model_validate(
            {
                "stage": "0_reading",
                "rubric_id": "J0",
                "criteria": [],
                "suggested_status": "pass",
            }
        )

    # Reuse is hash-bound: corrupt the sidecar hash and ensure packet regenerates it
    # from accepted attempts/002/output.json, not from the already-tampered flat file.
    sidecar["output_hash"] = "wrong"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    packet2 = rs._judge_packet(
        "0_reading",
        "sm21_anchor",
        case_dir,
        run_dir,
        run_dir / "0_reading" / "attempts" / "002",
        _pass_report("0_reading"),
    )
    sidecar2 = json.loads(Path(packet2["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar2["output_hash"] == rec.output_hash
    assert sidecar2["scores"]

    sidecar2["tolerances"] = {"wall_tol_m": 9.9, "window_centre_tol_m": 9.9}
    sidecar_path.write_text(json.dumps(sidecar2), encoding="utf-8")
    packet3 = rs._judge_packet(
        "0_reading",
        "sm21_anchor",
        case_dir,
        run_dir,
        run_dir / "0_reading" / "attempts" / "002",
        _pass_report("0_reading"),
    )
    sidecar3 = json.loads(Path(packet3["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar3["tolerances"] == {"wall_tol_m": 0.3, "window_centre_tol_m": 0.4}


def test_correction_scorer_maps_f1_f2_to_gt_floors():
    gt = load_gt("sm21_anchor")
    output = json.loads(
        (_SM21 / "run_2026-06-20_sonnet_reading/1_correction/attempts/001/output.json")
        .read_text(encoding="utf-8")
    )

    result = score_correction_geometry(output, gt)

    assert result.floor_map == {"F1": "Floor 1", "F2": "Floor 2"}
    assert result.evidence == []
    assert set(result.scores) == {"F1", "F2"}
    assert result.scores["F1"].wall_hits() == (4, 4)
    assert result.scores["F2"].wall_hits() == (5, 5)
    assert result.scores["F1"].window_hits() == (7, 7)
    assert result.scores["F2"].window_hits() == (8, 8)


def test_judge_packet_scores_correction_attempt_and_records_floor_map(tmp_path, monkeypatch):
    run_dir = _copy_run_subset(
        tmp_path,
        "run_2026-06-20_sonnet_reading",
        [("1_correction/attempts/001/output.json", "1_correction/attempts/001/output.json")],
    )
    monkeypatch.setattr(rs, "_render_stage", lambda *_args, **_kwargs: [])

    packet = rs._judge_packet(
        "1_correction",
        "sm21_anchor",
        tmp_path / "sm21_anchor",
        run_dir,
        run_dir / "1_correction" / "attempts" / "001",
        _pass_report("1_correction"),
    )

    sidecar = json.loads(Path(packet["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar["stage"] == "1_correction"
    assert sidecar["source"] == "attempt_output"
    assert sidecar["tolerances"] == {"wall_tol_m": 0.3, "window_centre_tol_m": 0.4}
    assert sidecar["floor_map"] == {"F1": "Floor 1", "F2": "Floor 2"}
    assert sidecar["evidence"] == []
    assert Path(packet["grade"]).exists()
    assert packet["score_criteria"] == sidecar["score_criteria"]


def test_judge_side_renders_every_attempt_and_promotes_accepted_grade(tmp_path):
    run_dir = _copy_run_subset(
        tmp_path,
        "run_2026-06-20_gpt54_reading",
        [
            ("0_reading/attempts/001/output.json", "0_reading/attempts/001/output.json"),
            ("0_reading/attempts/002/output.json", "0_reading/attempts/002/output.json"),
        ],
    )
    manifest = RunManifest.load(run_dir)
    gt = load_gt("sm21_anchor")

    artifacts = rs._render_all_attempt_grades(
        "0_reading",
        "sm21_anchor",
        run_dir,
        gt,
        manifest=manifest,
        grade=rs.GradeConfig(),
    )

    assert set(artifacts) == {1, 2}
    for attempt in (1, 2):
        adir = run_dir / "0_reading" / "attempts" / f"{attempt:03d}"
        assert (adir / "score_vs_gt.json").exists()
        assert (adir / "grade.png").exists()
        sidecar = json.loads((adir / "score_vs_gt.json").read_text(encoding="utf-8"))
        assert sidecar["attempt"] == attempt
        assert sidecar["tolerances"] == {"wall_tol_m": 0.3, "window_centre_tol_m": 0.4}

    accepted = run_dir / "0_reading" / "attempts" / "002" / "grade.png"
    assert (run_dir / "0_reading" / "grade.png").read_bytes() == accepted.read_bytes()


def test_grade_uses_shared_metric_transform_for_gt_and_sidecar_pixels():
    gt = {
        "case": "tiny",
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {
                "name": "Floor 1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "zones": [
                    {"id": "A", "role": "office", "rect_m": [0.0, 0.0, 5.0, 4.0]},
                    {"id": "B", "role": "office", "rect_m": [5.0, 0.0, 10.0, 4.0]},
                ],
            }
        ],
        "windows": [],
        "doors": [],
    }
    sidecar = {
        "stage": "1_correction",
        "attempt": 1,
        "source": "attempt_output",
        "tolerances": {"wall_tol_m": 0.3, "window_centre_tol_m": 0.4},
        "scores": {
            "Floor 1": {
                "floor": "Floor 1",
                "vwalls": [{"truth": 5.0, "read": 5.0, "delta": 0.0}],
                "hwalls": [],
                "extra_vwalls": [],
                "extra_hwalls": [],
                "windows": {"N": [], "S": [], "E": [], "W": []},
                "extra_windows": {"N": [], "S": [], "E": [], "W": []},
            }
        },
    }

    img = render_grade.render_grade("1_correction", sidecar, gt)
    tr = plan_transform(
        10.0,
        4.0,
        scale=render_grade.SCALE,
        offset_x=0,
        offset_y=render_grade.HEADER + render_grade.LABEL_H,
        margin_m=render_grade.PLAN_MARGIN_M,
    )
    split_px = tuple(round(v) for v in tr.px(5.0, 2.0))
    fill_px = tuple(round(v) for v in tr.px(2.0, 2.0))

    assert img.mode == "RGB"
    assert img.getpixel(split_px) == render_grade.GREEN
    assert img.getpixel(fill_px) == render_grade.GT_FILL
