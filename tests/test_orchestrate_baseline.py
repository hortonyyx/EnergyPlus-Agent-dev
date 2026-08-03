"""Tests for the dev-baseline orchestration helpers + record_baseline tool."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from src.agent.execution import (
    RunManifest,
    StageRunner,
    file_stage_attempt,
    run_meta_path,
    summarize_gates,
)
from src.agent.judge import StageVerdict
from src.validator.checks.schema import CheckLayer, CheckReport

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import record_baseline  # noqa: E402
import report_assembly  # noqa: E402

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")
_RUN_NAME = "run_2026-06-15_baseline"
_SM21 = Path("case_tests/e2e_tests/sm21_anchor")
_GPT54_RUN = "run_2026-06-20_gpt54_reading"
_SONNET_RUN = "run_2026-06-20_sonnet_reading"
_RERECORD_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="deterministic-naming golden re-record pending sm21 batch",
)


def _minimal_run(tmp_path: Path) -> Path:
    run = tmp_path / "synthetic_case" / "run_audit"
    run.mkdir(parents=True)
    return run


def test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback(tmp_path):
    """The real baseline recorder must consume its FROZEN TIER + the caller's
    per-invocation require_ep.  r2-4 (ruling 2026-08-04 §2): require_ep is NO
    LONGER read from frozen context — it is the caller's operational knob
    (--with-ep / --require-ep).  A frozen regression/orthogonal run recorded
    with the caller passing require_ep=True keeps its frozen tier header AND
    surfaces the downstream.build blocking row because the CALLER asked for EP
    (not because the frozen context said so).

    r2c-1 (ruling 2026-08-04 §1): the tier header (run_profile /
    capability_profile) now comes from the SAME policy fed to validate_case
    (effective_run_policy), not from ``frozen`` directly.  Neuter: replace
    effective_run_policy with RunPolicy(require_ep=require_ep) (keep the caller
    knob, drop the tier) ⇒ policy.run_profile/capability_profile fall to the
    RunPolicy defaults (exploratory/rectangular) ⇒ this header assertion reds
    (the caller knob still brings downstream.build, so only the TIER dimension
    is lost — which is exactly what this header now witnesses)."""
    from src.agent.execution.run_policy_freeze import provision_run_policy

    run = _minimal_run(tmp_path)
    provision_run_policy(
        run,
        run_profile="regression",
        capability_profile="orthogonal_polygon",
    )

    baseline = record_baseline.record_baseline(
        run,
        date="2026-08-04",
        orchestrator="test",
        require_ep=True,
        run_profile="exploratory",
    )

    policy_header = baseline["run_policy"]
    assert policy_header["source"] == "structured_config"
    assert policy_header["legacy_defaulted"] is False
    assert policy_header["run_profile"] == "regression"
    assert policy_header["capability_profile"] == "orthogonal_polygon"
    assert policy_header["policy_hash"]
    # downstream.build is blocking because the CALLER passed require_ep=True
    # (r2-4: require_ep comes from the caller, never from frozen context).
    assert any(
        row["stage"] == "downstream" and row["check"] == "downstream.build"
        for row in baseline["blocking"]
    )


def test_R1_5_record_baseline_regression_tier_surfaces_blocking_check_row(tmp_path):
    """r2c-1 (ruling 2026-08-04 §1) second layer: the regression tier must be
    visible on ``baseline["blocking"]`` — not only on the run_policy header.  A
    non-closing dimension chain (overall != Σ segments) is an EVIDENCE check
    (``reading.dimension_chain_closure``); its disposition is tier-gated
    (BLOCK under regression, FLAG under exploratory — schema.disposition).  So a
    frozen regression run that feeds that FAIL to validate_case must surface it
    as a blocking row, and the same FAIL fed under an exploratory policy would
    NOT.  Neuter: replace effective_run_policy with RunPolicy(require_ep=...)
    (drop the tier, keep the caller knob) ⇒ policy.run_profile becomes
    exploratory ⇒ the closure FAIL is FLAG, not BLOCK ⇒ this row disappears from
    ``baseline["blocking"]`` ⇒ reds.  This is the test_L10/L11 form applied to
    record_baseline: it binds the TIER dimension the header lock above can no
    longer witness once require_ep is split out."""
    from src.agent.execution.run_policy_freeze import provision_run_policy

    run = _minimal_run(tmp_path)
    provision_run_policy(
        run,
        run_profile="regression",
        capability_profile="orthogonal_polygon",
    )
    # A plan view with a NON-closing chain: overall=6.0 but segments sum to 5.0
    # ⇒ check_reading_view emits reading.dimension_chain_closure FAIL (mismatch),
    # which is a tier-gated EVIDENCE check (BLOCK under regression).
    rdir = run / "0_reading"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "1f_view.json").write_text(
        json.dumps(
            {
                "image_kind": "plan",
                "uncaptured": [],
                "strokes": [
                    {"id": "S1", "pen": "wall", "provenance": "seen",
                     "confidence": "high", "geometry": {"kind": "line",
                                                        "p1": [0, 0], "p2": [10, 0]}},
                    {"id": "S2", "pen": "wall", "provenance": "seen",
                     "confidence": "high", "geometry": {"kind": "line",
                                                        "p1": [0, 8], "p2": [10, 8]}},
                ],
                "dimensions": [
                    {"id": "D0", "text_verbatim": "6.0", "value_m": 6.0,
                     "chain_id": "c", "role": "overall", "order": 0, "axis": "x",
                     "from": [0, 0], "to": [6, 0]},
                    {"id": "D1", "text_verbatim": "2.0", "value_m": 2.0,
                     "chain_id": "c", "role": "segment", "order": 1, "axis": "x",
                     "from": [0, 0], "to": [2, 0]},
                    {"id": "D2", "text_verbatim": "3.0", "value_m": 3.0,
                     "chain_id": "c", "role": "segment", "order": 2, "axis": "x",
                     "from": [2, 0], "to": [5, 0]},
                ],
                "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0,
                                 "world_z_m": None},
            }
        ),
        encoding="utf-8",
    )

    baseline = record_baseline.record_baseline(
        run,
        date="2026-08-04",
        orchestrator="test",
        require_ep=False,
        run_profile="exploratory",
    )

    # The non-closing chain FAIL is a BLOCK only because the tier fed to
    # validate_case was regression (an exploratory policy would FLAG it).
    assert any(
        row["stage"] == "0_reading"
        and row["check"] == "reading.dimension_chain_closure"
        for row in baseline["blocking"]
    )



def test_R1_5_record_baseline_marks_unfrozen_run_legacy(tmp_path):
    """An unfrozen replay remains readable but can never impersonate a strict
    TIER: its baseline header must say legacy-defaulted/exploratory/rectangular
    regardless of any CLI run_profile request.  r2-4: require_ep is now a
    caller knob (independent of legacy status); this control records a legacy
    replay with no EP request (require_ep=False) ⇒ legacy tier markers and no
    downstream.build row.  The binding is the legacy-defaulted tier
    (resolve_frozen_run_policy returns legacy_defaulted for an unfrozen run)."""
    baseline = record_baseline.record_baseline(
        _minimal_run(tmp_path),
        date="2026-08-04",
        orchestrator="test",
        require_ep=False,
        run_profile="regression",
    )

    assert baseline["run_policy"]["source"] == "legacy_defaulted"
    assert baseline["run_policy"]["legacy_defaulted"] is True
    assert baseline["run_policy"]["run_profile"] == "exploratory"
    assert baseline["run_policy"]["capability_profile"] == "rectangular"
    assert not any(
        row["stage"] == "downstream" and row["check"] == "downstream.build"
        for row in baseline["blocking"]
    )


def test_R1_5_record_baseline_context_tamper_does_not_change_blocking(tmp_path):
    """r2-4 (ruling 2026-08-04 §2.5): tampering ``<run>/_run/run_policy.json``'s
    ``context.require_ep`` AND recomputing ``content_sha256`` must NOT change
    baseline accounting — because effective_run_policy no longer reads context
    for decisions (require_ep comes from the caller per-invocation).  A frozen
    regression/orthogonal run is provisioned with context.require_ep=False, then
    the frozen file is tampered to context.require_ep=True with a freshly
    recomputed self-hash so the record still loads.  Recording with the CALLER's
    require_ep=False must still produce NO downstream.build blocking row — the
    tampered context is ignored.  Neuter (b): make effective_run_policy read
    context.require_ep again ⇒ the tampered True wins over the caller's False ⇒
    downstream.build appears ⇒ this lock reds."""
    from src.agent.execution.manifest import hash_obj
    from src.agent.execution.run_meta import run_meta_path
    from src.agent.execution.run_policy_freeze import (
        RUN_POLICY_NAME,
        provision_run_policy,
    )

    run = _minimal_run(tmp_path)
    provision_run_policy(
        run,
        run_profile="regression",
        capability_profile="orthogonal_polygon",
        context={"require_ep": {"value": False, "source": "cli"}},
    )
    # Tamper: flip context.require_ep to True and recompute the record's self-hash
    # (content_sha256) so the edited record still passes its integrity check —
    # this is exactly the threat the r2-4 (b) rule removes by not consuming context.
    policy_path = run_meta_path(run, RUN_POLICY_NAME)
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    payload["context"]["require_ep"]["value"] = True
    payload["content_sha256"] = hash_obj(
        {k: v for k, v in payload.items() if k != "content_sha256"}
    )
    policy_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, separators=(",", ": ")),
        encoding="utf-8",
    )

    baseline = record_baseline.record_baseline(
        run,
        date="2026-08-04",
        orchestrator="test",
        require_ep=False,  # caller's per-invocation value — the authority
        run_profile="exploratory",
    )

    # frozen tier still consumed (the tamper only touched context, not the tier)
    assert baseline["run_policy"]["run_profile"] == "regression"
    assert baseline["run_policy"]["capability_profile"] == "orthogonal_polygon"
    # downstream.build is ABSENT because the CALLER passed require_ep=False; the
    # tampered context.require_ep=True is ignored (r2-4 (b)).
    assert not any(
        row["stage"] == "downstream" and row["check"] == "downstream.build"
        for row in baseline["blocking"]
    )


def _mixed_audit_payload() -> dict:
    corrections = [
        {
            "id": "corr_a1",
            "stage": "A1",
            "rule_id": "A1_local_to_world",
            "target": "global_world_frame",
            "source_ids": ["1f_view", "South_view"],
            "original_value": "local coordinates",
            "resolved_value": "world coordinates",
            "delta": "(-0.24,-0.24)m",
            "changes_topology": False,
            "method_profile": "room_identity",
        },
        {
            "stage": "core",
            "rule_id": "deterministic_core.snap",
            "target": "x.axis[4.9100]",
            "axis": "x",
            "original_value": 4.91,
            "resolved_value": 4.9,
            "delta": -0.01,
            "tolerance_name": "SNAP_GRID",
        },
    ]
    corrections.extend(
        {"id": f"bulk_{i}", "stage": "A2", "rule_id": "bulk_rule", "target": f"axis_{i}"}
        for i in range(23)
    )
    return {
        "corrections": corrections,
        "conflicts": [
            {
                "id": "conf_1",
                "stage": "A3",
                "conflict_type": "stroke_vs_dimension",
                "candidates": [
                    {"value": 4.9, "source_ids": ["S7"]},
                    {"value": 4.94, "source_ids": ["D4", "D5"]},
                ],
                "reason_unresolved": "dimension and stroke disagree",
                "fallback_action": "used dimension chain",
            }
        ],
        "unsupported": [
            {
                "id": "unsup_1",
                "reason": "door found in elevation; doors are not modeled here",
                "regime_assumption_violated": "windows only",
            }
        ],
    }


# --------------------------------------------------------------------------- #
# orchestrate
# --------------------------------------------------------------------------- #
def test_file_stage_attempt_writes_output_checks_judge(tmp_path):
    manifest = RunManifest(case="t")
    runner = StageRunner(tmp_path, manifest)
    rep = CheckReport(stage="1_correction")
    rep.add_pass("x", CheckLayer.INVARIANT)
    verdict = StageVerdict(
        stage="1_correction", rubric_id="J1",
        criteria=[{"criterion": "redraw", "status": "pass"}],
    )
    rec = file_stage_attempt(
        runner, stage="1_correction", stage_dir=tmp_path / "1_correction",
        output_obj={"v": 1}, report=rep, verdict=verdict,
    )
    adir = Path(rec.attempt_dir)
    assert (adir / "output.json").exists()
    assert (adir / "checks.json").exists()
    assert (adir / "judge.json").exists()
    assert rec.accepted is True  # report passed → accepted
    assert manifest.accepted("1_correction").accepted_attempt == rec.attempt_index


def test_file_stage_attempt_appends_not_overwrites(tmp_path):
    manifest = RunManifest(case="t")
    runner = StageRunner(tmp_path, manifest)
    bad = CheckReport(stage="1_correction")
    bad.add_fail("x", CheckLayer.INVARIANT, "bad")
    r1 = file_stage_attempt(runner, stage="1_correction",
                            stage_dir=tmp_path / "1_correction",
                            output_obj={"v": 1}, report=bad)
    good = CheckReport(stage="1_correction")
    good.add_pass("x", CheckLayer.INVARIANT)
    r2 = file_stage_attempt(runner, stage="1_correction",
                            stage_dir=tmp_path / "1_correction",
                            output_obj={"v": 2}, report=good)
    assert r1.attempt_index == 1 and r2.attempt_index == 2
    assert r1.accepted is False and r2.accepted is True
    # both drafts survive
    assert (tmp_path / "1_correction" / "attempts" / "001" / "output.json").exists()
    assert (tmp_path / "1_correction" / "attempts" / "002" / "output.json").exists()


def test_summarize_gates_rolls_up():
    reading = CheckReport(stage="0_reading")
    reading.add_pass("a", CheckLayer.INVARIANT)
    reading.add_fail("b", CheckLayer.CROSS_CHECK, "soft")  # flag
    kernel = CheckReport(stage="2_modelling")
    kernel.add_fail("c", CheckLayer.INVARIANT, "hard")     # block
    s = summarize_gates({"0_reading::1f_view": reading, "2_modelling": kernel})
    assert s["gates"]["0_reading"]["pass"] == 1
    assert s["gates"]["0_reading"]["flag"] == 1
    assert s["gates"]["2_modelling"]["block"] == 1
    assert len(s["flags"]) == 1 and s["flags"][0]["check"] == "b"
    assert len(s["blocking"]) == 1 and s["blocking"][0]["check"] == "c"
    assert s["signals"]["reading_syntax_valid"] is True
    assert s["signals"]["reading_evidence_clean"] is True


def test_reading_evidence_signal_turns_report_status_red():
    reading = CheckReport(stage="0_reading", run_profile="regression")
    reading.add_fail(
        "reading.dimensions_present",
        CheckLayer.CROSS_CHECK,
        "dimensioned view has empty dimensions[]",
        evidence={"legacy_migrated": False},
    )
    s = summarize_gates({"0_reading::1f_view": reading})
    assert s["signals"]["reading_syntax_valid"] is True
    assert s["signals"]["reading_evidence_clean"] is False
    assert s["gates"]["0_reading"]["block"] == 1

    baseline = {
        "run_state": {"status": "completed_clean"},
        "signals": s["signals"],
    }
    assert report_assembly._status_tldr(baseline) == "reading_evidence_debt"


# --------------------------------------------------------------------------- #
# record_baseline on the real anchor
# --------------------------------------------------------------------------- #
@_RERECORD_XFAIL
def test_record_baseline_on_anchor(tmp_path):
    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    run = case / _RUN_NAME
    (run / "RUN_REPORT.md").unlink(missing_ok=True)
    checks_before = (run / "1_correction" / "correction_checks.json").read_bytes()
    b = record_baseline.record_baseline(run, date="2026-06-16", orchestrator="test")
    assert b["blocked"] is False
    assert b["case"] == "sm20_anchor" and b["run"] == _RUN_NAME
    assert b["geometry"] == {"zones": 19, "surfaces": 135, "windows": 16}
    assert b["geometry_digest"] is not None
    # files written into the run dir
    bj = json.loads(run_meta_path(run, "baseline.json").read_text())
    assert bj["case"] == "sm20_anchor"
    assert "evidence_index" in bj
    assert "run_state" not in bj
    report = (run / "report" / "REPORT.md").read_text()
    assert report.startswith("<!-- GEN:START model_config -->")
    assert "## 本次模型配置" in report
    assert "## 事实卡" in report
    assert "## 肉视检验索引" in report
    assert not (run / "report" / "FACTS.md").exists()
    assert not (run / "report" / "REPORT.template.md").exists()
    assert "肉视检验" in report
    assert "结论" in report
    assert "## 建议" in report
    assert not (run / "RUN_REPORT.md").exists()
    # record_baseline must not rewrite load-bearing gate artifacts.
    assert (run / "1_correction" / "correction_checks.json").read_bytes() == checks_before
    assert (run / "1_correction" / "correction_checks.json").exists()


def test_record_baseline_report_lists_eyeball_items(tmp_path):
    case = tmp_path / "sm21_anchor"
    shutil.copytree(_SM21, case)
    run = case / _GPT54_RUN
    record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")
    baseline = json.loads(run_meta_path(run, "baseline.json").read_text())
    assert "signals" in baseline
    assert "reading_evidence_clean" in baseline["signals"]

    eye = run / "report" / "eyeball"
    assert (eye / "1_correction_zones.png").exists()
    assert (eye / "1_correction_elev.png").exists()
    assert (eye / "0_reading_1f_view_render.png").exists()
    assert (eye / "case_data_1f_view.png").exists()
    report = (run / "report" / "REPORT.md").read_text()
    assert "reading_evidence_clean" in report
    assert "report/eyeball/1_correction_zones.png" in report
    assert "[3D geometry viewer](../manual_review/geometry_viewer.html)" in report
    assert (run / "manual_review" / "geometry_viewer.html").exists()
    assert not (run / "report" / "FACTS.md").exists()


def test_record_baseline_state_aware_report_suppresses_dead_viewer(tmp_path):
    case = tmp_path / "sm21_anchor"
    shutil.copytree(_SM21, case)
    run = case / _SONNET_RUN
    record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")

    report = (run / "report" / "REPORT.md").read_text()
    assert "root_stopped: human_redraw_required@1_correction" in report
    assert "### 连带缺失下游件" in report
    assert "2_modelling/building_geometry.json" in report
    assert "3D geometry viewer unavailable" in report
    assert "../manual_review/geometry_viewer.html" not in report


def test_record_baseline_missing_corrections_sidecar_does_not_change_gates(tmp_path):
    run = _minimal_run(tmp_path)
    b = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")

    assert b["corrections_summary"]["present"] is False
    assert b["corrections_summary"]["parse_status"] == "missing"
    assert b["corrections_summary"]["sidecar_path"] == "1_correction/corrections.json"
    assert b["corrections_summary"]["counts"] == {
        "corrections": 0,
        "conflicts": 0,
        "unsupported": 0,
    }
    assert b["flags"] == []
    assert all(agg["flag"] == 0 for agg in b["gates"].values())
    report = (run / "report" / "REPORT.md").read_text()
    assert "### 校正审计摘要" in report
    assert "sidecar: `1_correction/corrections.json` (missing)" in report


def test_record_baseline_correction_audit_summary_is_separate_from_flags(tmp_path):
    run = _minimal_run(tmp_path)
    before = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")
    before_flags = before["flags"]
    before_gates = before["gates"]

    audit = _mixed_audit_payload()
    sidecar = run / "1_correction" / "corrections.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")

    after = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")
    summary = after["corrections_summary"]
    assert summary["present"] is True
    assert summary["parse_status"] == "ok"
    assert summary["sidecar_path"] == "1_correction/corrections.json"
    assert summary["counts"] == {"corrections": 25, "conflicts": 1, "unsupported": 1}
    assert summary["by_rule_id"] == {
        "A1_local_to_world": 1,
        "bulk_rule": 23,
        "deterministic_core.snap": 1,
    }
    assert summary["by_stage"]["A1"] == 1
    assert summary["by_stage"]["A2"] == 23
    assert summary["by_stage"]["A3"] == 1
    assert summary["by_stage"]["core"] == 1
    assert summary["corrections"]["total"] == 25
    assert summary["corrections"]["shown"] == 20
    assert summary["corrections"]["cap"] == 20
    assert len(summary["corrections"]["rows"]) == 20
    assert summary["corrections"]["rows"][0] == {
        "id": "corr_a1",
        "rule_id": "A1_local_to_world",
        "target": "global_world_frame",
        "source_ids": ["1f_view", "South_view"],
        "original_value": "local coordinates",
        "resolved_value": "world coordinates",
        "delta": "(-0.24,-0.24)m",
        "changes_topology": False,
    }
    assert summary["conflicts"] == audit["conflicts"]
    assert summary["unsupported"] == audit["unsupported"]

    assert after["flags"] == before_flags
    assert after["gates"] == before_gates
    ids = {entry["id"] for entry in after["evidence_index"]}
    assert "E:corr:corrections:corr_a1" in ids
    assert "E:corr:corrections:r2" in ids
    assert "E:corr:corrections:bulk_22" in ids
    assert "E:corr:conflicts:conf_1" in ids
    assert "E:corr:unsupported:unsup_1" in ids
    assert len([eid for eid in ids if eid.startswith("E:corr:")]) == 27

    report = (run / "report" / "REPORT.md").read_text()
    assert "### 校正审计摘要" in report
    assert "corrections=25, conflicts=1, unsupported=1" in report
    assert "audit-derived [corrections_summary]" in report
    assert "`E:corr:corrections:bulk_22`" in report


def test_record_baseline_malformed_corrections_sidecar_is_best_effort(tmp_path):
    run = _minimal_run(tmp_path)
    sidecar = run / "1_correction" / "corrections.json"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("{not-json", encoding="utf-8")

    b = record_baseline.record_baseline(run, date="2026-06-22", orchestrator="test")
    assert b["corrections_summary"]["present"] is True
    assert b["corrections_summary"]["parse_status"] == "malformed_json"
    assert b["corrections_summary"]["counts"] == {
        "corrections": 0,
        "conflicts": 0,
        "unsupported": 0,
    }
    report = (run / "report" / "REPORT.md").read_text()
    assert "malformed_json" in report


def test_record_baseline_models_structured_from_run_config_and_llm(tmp_path):
    run = _minimal_run(tmp_path)
    (run / "run_config.yaml").write_text(
        "\n".join(
            [
                "models:",
                "  reading:",
                "    model_id: claude-sonnet-5",
                "    effort: high",
                "  correction: deepseek-v4-pro",
                "  orchestrator: codex-5",
            ]
        ),
        encoding="utf-8",
    )
    (run / "llm.yaml").write_text(
        "\n".join(
            [
                "default:",
                "  model_name: downstream-default",
                "intake_mep:",
                "  model_name: mep-model",
                "  reasoning_effort: max",
            ]
        ),
        encoding="utf-8",
    )

    models = record_baseline._models_from_llm_yaml(run, orchestrator="fallback-orch")

    assert models["reading"] == {
        "model_id": "claude-sonnet-5",
        "effort": "high",
        "source": "run_config.yaml:models.reading",
    }
    assert models["correction"]["model_id"] == "deepseek-v4-pro"
    assert models["mep"] == {
        "model_id": "mep-model",
        "effort": "max",
        "source": "llm.yaml:intake_mep",
    }
    assert models["default"]["model_id"] == "downstream-default"
    assert models["orchestrator"]["model_id"] == "codex-5"


def test_record_baseline_models_missing_run_config_uses_unknown_and_warns(tmp_path):
    run = _minimal_run(tmp_path)
    (run / "llm.yaml").write_text(
        "intake_correction:\n  model_name: correction-model\n  reasoning_effort: high\n",
        encoding="utf-8",
    )

    with pytest.warns(RuntimeWarning, match="run_config.yaml"):
        models = record_baseline._models_from_llm_yaml(run)

    assert models["reading"]["model_id"] == "unknown"
    assert models["correction"] == {
        "model_id": "correction-model",
        "effort": "high",
        "source": "llm.yaml:intake_correction",
    }
    assert models["mep"]["source"] == "llm.yaml:intake_correction(fallback)"
    assert models["default"]["model_id"] == "unknown"
    assert models["orchestrator"]["model_id"] == "unknown"


def test_record_baseline_verdict_blocking_is_recoverability_aware():
    j0_recoverable = {
        "stage": "0_reading",
        "rubric_id": "J0",
        "criteria": [
            {
                "criterion": "stroke_vs_dimension",
                "status": "severe",
                "recoverability": "correction_recoverable",
            }
        ],
    }
    assert record_baseline._verdict_blocking(j0_recoverable) is False

    j1_recoverable = {**j0_recoverable, "stage": "1_correction", "rubric_id": "J1"}
    assert record_baseline._verdict_blocking(j1_recoverable) is True

    legacy = {
        "stage": "0_reading",
        "rubric_id": "J0",
        "criteria": [{"criterion": "legacy", "status": "severe"}],
    }
    assert record_baseline._verdict_blocking(legacy) is True


def _ok_stage(stage: str, status: str = "deterministic_pass") -> dict:
    return {
        "stage": stage,
        "status": status,
        "attempts_used": 1,
        "accepted_attempt": 1,
        "message": f"{status}@{stage}",
    }


def _all_stage_state(overrides: dict[str, str] | None = None) -> dict:
    statuses = {
        "0_reading": "judge_pass",
        "1_correction": "judge_pass",
        "2_modelling": "deterministic_pass",
        "3_split_pairing": "deterministic_pass",
        "4_mep": "deterministic_pass",
        "5_intakeoutput": "deterministic_pass",
    }
    statuses.update(overrides or {})
    return {"stages": {stage: _ok_stage(stage, status) for stage, status in statuses.items()}}


def test_run_state_completed_clean_real_geometry_gate_shape():
    state = json.loads(run_meta_path(_SM21 / _GPT54_RUN, "orchestration_state.json").read_text())
    derived = report_assembly.derive_run_state(state, geometry_approved=True)
    assert derived["status"] == "completed_clean"
    assert derived["completed_clean"] is True
    assert derived["pending"] is None
    assert derived["ignored_pending"][0]["stage"] == "3_split_pairing"


@pytest.mark.parametrize(
    ("stage", "status"),
    [
        ("0_reading", "awaiting_judge"),
        ("1_correction", "judge_block"),
        ("0_reading", "awaiting_reread"),
        ("3_split_pairing", "awaiting_geometry_approval"),
    ],
)
def test_run_state_pending_cases(stage, status):
    derived = report_assembly.derive_run_state(
        _all_stage_state({stage: status}), geometry_approved=False)
    assert derived["status"] == "pending"
    assert derived["completed_clean"] is False
    assert derived["pending"]["stage"] == stage
    assert derived["pending"]["status"] == status


def test_run_state_non_human_terminal_precedes_pending():
    derived = report_assembly.derive_run_state(
        _all_stage_state({
            "4_mep": "quarantined",
            "5_intakeoutput": "awaiting_judge",
        }),
        geometry_approved=False,
    )
    assert derived["status"] == "root_stopped"
    assert derived["root_stop"]["stage"] == "4_mep"
    assert derived["root_stop"]["status"] == "quarantined"
    assert derived["pending"] is None
    assert derived["pending_candidates"][0]["stage"] == "5_intakeoutput"


def test_evidence_index_duplicate_id_assertion():
    with pytest.raises(AssertionError, match="duplicate evidence ids"):
        report_assembly.assert_unique_evidence_ids([
            {"id": "E:gate:0_reading::1f_view:x"},
            {"id": "E:gate:0_reading::1f_view:x"},
        ])


def _valid_recommendation_report(evidence_id: str) -> str:
    return f"""# report

## 建议

### 机制问题

- action: add a sharper gate
  evidence: [{evidence_id}]
  owner: scaffold

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

> note: context is allowed when explicitly marked.
- action: add a judge checklist item
  evidence: [{evidence_id}]
  owner: scaffold

### 修法

本 run 无可证据支持的建议
"""


def test_citation_linter_passes_structured_recommendations():
    index = [{"id": "E:geom:digest"}]
    assert report_assembly.lint_report_citations(
        _valid_recommendation_report("E:geom:digest"), index) == []


@pytest.mark.parametrize(
    "text",
    [
        _valid_recommendation_report("E:missing"),
        """# report

## 建议

### 机制问题

free prose is not allowed here

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

本 run 无可证据支持的建议

### 修法

本 run 无可证据支持的建议
""",
        """# report

## 建议

### 机制问题

- action: cite nothing
  evidence:
  owner: scaffold

### 能力升级

本 run 无可证据支持的建议

### 脚手架建议

本 run 无可证据支持的建议

### 修法

本 run 无可证据支持的建议
""",
    ],
)
def test_citation_linter_fails_bad_recommendations(text):
    errors = report_assembly.lint_report_citations(text, [{"id": "E:geom:digest"}])
    assert errors
    assert all("AGENT:recommendations" in error for error in errors)


def _recommendation_block(evidence_id: str) -> str:
    return _valid_recommendation_report(evidence_id).removeprefix("# report\n\n")


def _replace_agent_region(text: str, key: str, body: str) -> str:
    body_text = body if body.endswith("\n") else body + "\n"
    pattern = re.compile(
        rf"<!-- AGENT:START {re.escape(key)} -->\n.*?<!-- AGENT:END {re.escape(key)} -->\n?",
        re.S,
    )
    replacement = f"<!-- AGENT:START {key} -->\n{body_text}<!-- AGENT:END {key} -->\n"
    new, count = pattern.subn(replacement, text, count=1)
    assert count == 1
    return new


def test_record_baseline_marker_merge_preserves_agent_edits_and_is_idempotent(tmp_path):
    case = tmp_path / "sm21_anchor"
    shutil.copytree(_SM21, case)
    run = case / _GPT54_RUN
    first = record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")
    evidence_id = first["evidence_index"][0]["id"]
    report_path = run / "report" / "REPORT.md"
    authored = report_path.read_text(encoding="utf-8")
    authored = _replace_agent_region(
        authored,
        "conclusion",
        "## 一句话结论\n\nCustom narrative survives.\n",
    )
    authored = _replace_agent_region(
        authored,
        "recommendations",
        _recommendation_block(evidence_id),
    )
    report_path.write_text(authored, encoding="utf-8")

    record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")
    after_one = report_path.read_text(encoding="utf-8")
    assert "Custom narrative survives." in after_one
    assert "- action: add a sharper gate" in after_one

    record_baseline.record_baseline(run, date="2026-06-21", orchestrator="test")
    assert report_path.read_text(encoding="utf-8") == after_one

    record_baseline.record_baseline(
        run, date="2026-06-21", orchestrator="test", force_template=True)
    assert "Custom narrative survives." not in report_path.read_text(encoding="utf-8")


def test_record_baseline_missing_agent_region_gets_placeholder(tmp_path):
    run = _minimal_run(tmp_path)
    record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
    report_path = run / "report" / "REPORT.md"
    text = report_path.read_text(encoding="utf-8")
    text = re.sub(
        r"<!-- AGENT:START focus -->\n.*?<!-- AGENT:END focus -->\n?",
        "",
        text,
        count=1,
        flags=re.S,
    )
    report_path.write_text(text, encoding="utf-8")

    record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
    report = report_path.read_text(encoding="utf-8")
    assert "<!-- AGENT:START focus -->" in report
    assert "AGENT-FILL: 说明这轮在测什么" in report


def test_record_baseline_duplicate_agent_marker_fails_before_write(tmp_path):
    run = _minimal_run(tmp_path)
    record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
    report_path = run / "report" / "REPORT.md"
    original = report_path.read_text(encoding="utf-8")
    report_path.write_text(
        original + "\n<!-- AGENT:START focus -->\nduplicate\n<!-- AGENT:END focus -->\n",
        encoding="utf-8",
    )

    with pytest.raises(report_assembly.ReportMarkerError, match="duplicate AGENT marker"):
        record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")


def test_record_baseline_nested_agent_marker_fails_before_write(tmp_path):
    run = _minimal_run(tmp_path)
    record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
    report_path = run / "report" / "REPORT.md"
    text = _replace_agent_region(
        report_path.read_text(encoding="utf-8"),
        "conclusion",
        "## 一句话结论\n\n<!-- AGENT:START focus -->\n",
    )
    report_path.write_text(text, encoding="utf-8")

    with pytest.raises(report_assembly.ReportMarkerError, match="nested AGENT marker"):
        record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("<!-- AGENT:END focus -->\n", "reversed/unmatched AGENT end"),
        ("<!-- AGENT:START focus -->\nopen\n", "unclosed AGENT marker"),
    ],
)
def test_agent_marker_reversed_or_unclosed_fails(text, match):
    with pytest.raises(report_assembly.ReportMarkerError, match=match):
        report_assembly.extract_agent_regions(text)


def test_agent_marker_like_text_inside_gen_payload_is_ignored(tmp_path):
    run = _minimal_run(tmp_path)
    record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
    report_path = run / "report" / "REPORT.md"
    text = report_path.read_text(encoding="utf-8").replace(
        "<!-- GEN:START facts_card -->\n",
        "<!-- GEN:START facts_card -->\n<!-- AGENT:START recommendations -->\n",
        1,
    )
    report_path.write_text(text, encoding="utf-8")

    record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
    report = report_path.read_text(encoding="utf-8")
    assert report.count("<!-- AGENT:START recommendations -->") == 1


def test_record_baseline_stale_recommendation_evidence_fails_with_agent_block(tmp_path):
    run = _minimal_run(tmp_path)
    record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
    report_path = run / "report" / "REPORT.md"
    text = _replace_agent_region(
        report_path.read_text(encoding="utf-8"),
        "recommendations",
        _recommendation_block("E:stale:id"),
    )
    report_path.write_text(text, encoding="utf-8")

    with pytest.raises(AssertionError, match="AGENT:recommendations.*E:stale:id"):
        record_baseline.record_baseline(run, date="2026-06-23", orchestrator="test")
