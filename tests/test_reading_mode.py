"""R4-a: reading_mode lane/provenance accounting (CLAUDE.md §1.5 #7).

Locks (see AI_agent/logs/reviews/request/2026-08-04_batchD_and_R4a_dispatch.md
§2 and the execution log for the placement rationale):

  - L-R1: a ``controlled`` run's reading score carries a ``controlled``
    annotation in the report; changing the declared lane to ``autonomous``
    changes the rendered text (proves the label is not decorative).
  - L-R2: a NEW run recorded through the real official-record entry point
    (``run_stage.py flow --record``) without a declared ``reading_mode:``
    fails closed.
  - L-R3: a historical run with no frozen reading_mode.json resolves to
    ``legacy_unknown`` on read-only replay — never raises, never impersonates
    a lane.
  - L-R4: ``dev_function=true`` renders an explicit "not an official score"
    flag in the report.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.tool_scripts.run_stage as rs
from src.agent.execution.reading_mode import (
    ReadingAgentInfo,
    ReadingModeRecord,
    ReadingModeResolution,
    ReadingWorkerAgentInfo,
    provision_reading_mode,
    require_reading_mode,
    resolve_reading_mode,
)
from tests.test_run_stage_flow import _args, _fake_make_draw_fn, _seed_case_data


def _controlled_declared() -> dict:
    return {
        "lane": "controlled",
        "dev_function": False,
        "reading_agent": {"model": "glm-5.2", "sees_images": False, "rework_rounds": 1},
        "reading_worker_agent": {"model": "haiku-4.5", "effort": "high"},
        "toolbox_version": "cv-toolbox-v3",
        "isolation_profile": "hard-isolation-v2",
    }


def _autonomous_declared() -> dict:
    return {
        "lane": "autonomous",
        "dev_function": False,
        "reading_agent": None,
        "reading_worker_agent": {"model": "target-vlm", "effort": "high"},
        "toolbox_version": "cv-toolbox-v3",
        "isolation_profile": "hard-isolation-v2",
    }


# --------------------------------------------------------------------------- #
# Unit-level: provision / resolve / require (the transaction itself)
# --------------------------------------------------------------------------- #

def test_provision_reading_mode_fails_closed_on_absence(tmp_path):
    """L-R2 unit slice: declared=None (no reading_mode: section) raises."""
    with pytest.raises(ValueError, match="reading_mode_not_declared"):
        provision_reading_mode(tmp_path, declared=None)
    assert not (tmp_path / "_run" / "reading_mode.json").exists()


def test_provision_reading_mode_fails_closed_on_bad_lane(tmp_path):
    """A declared-but-invalid lane value (typo / invented third lane, e.g.
    'tool_invention' being written as a lane — the exact mistake the dispatch
    warns against) is fail-closed, not silently coerced."""
    bad = _controlled_declared()
    bad["lane"] = "tool_invention"
    with pytest.raises(ValueError, match="reading_mode_invalid"):
        provision_reading_mode(tmp_path, declared=bad)


def test_provision_reading_mode_idempotent_same_value(tmp_path):
    first = provision_reading_mode(tmp_path, declared=_controlled_declared())
    second = provision_reading_mode(tmp_path, declared=_controlled_declared())
    assert first == second
    assert (tmp_path / "_run" / "reading_mode.json").exists()


def test_provision_reading_mode_drift_raises(tmp_path):
    provision_reading_mode(tmp_path, declared=_controlled_declared())
    with pytest.raises(ValueError, match="reading_mode_drift"):
        provision_reading_mode(tmp_path, declared=_autonomous_declared())


def test_resolve_reading_mode_present(tmp_path):
    provision_reading_mode(tmp_path, declared=_controlled_declared())
    resolution = resolve_reading_mode(tmp_path)
    assert resolution.status == "present"
    assert resolution.record.lane == "controlled"


def test_L_R3_resolve_reading_mode_legacy_unknown_never_raises(tmp_path):
    """L-R3: a run dir with no reading_mode.json (historical run) resolves to
    legacy_unknown and never raises — read-only replay must not be blocked."""
    resolution = resolve_reading_mode(tmp_path)
    assert resolution.status == "legacy_unknown"
    assert resolution.record is None
    # must not impersonate either lane
    assert resolution.status not in ("autonomous", "controlled")


def test_require_reading_mode_raises_when_legacy_unknown(tmp_path):
    with pytest.raises(ValueError, match="reading_mode_missing"):
        require_reading_mode(tmp_path)


def test_require_reading_mode_returns_record_when_present(tmp_path):
    provision_reading_mode(tmp_path, declared=_autonomous_declared())
    record = require_reading_mode(tmp_path)
    assert record.lane == "autonomous"
    assert record.reading_agent is None


def test_lane_reading_agent_contract_autonomous_rejects_reading_agent(tmp_path):
    """autonomous IS DEFINED as zero reading-agent (CLAUDE.md §1.5 #7); a
    declaration that pairs autonomous with a present reading_agent is not a
    legal record."""
    bad = _autonomous_declared()
    bad["reading_agent"] = {"model": "x", "sees_images": False, "rework_rounds": 0}
    with pytest.raises(ValueError, match="reading_mode_invalid"):
        provision_reading_mode(tmp_path, declared=bad)


def test_lane_reading_agent_contract_controlled_requires_reading_agent(tmp_path):
    bad = _controlled_declared()
    bad["reading_agent"] = None
    with pytest.raises(ValueError, match="reading_mode_invalid"):
        provision_reading_mode(tmp_path, declared=bad)


# --------------------------------------------------------------------------- #
# L-R2: fail-closed at the REAL entry point (run_stage.py flow --record), not
# fed to the internal function directly.
# --------------------------------------------------------------------------- #

def test_L_R2_flow_record_fails_closed_without_declared_reading_mode(tmp_path, monkeypatch, capsys):
    """A NEW run walked through the real `flow --record` CLI command, with NO
    reading_mode: section in run_config.yaml, must fail closed rather than
    silently recording an (implicitly autonomous-looking) score.

    Neuter: remove the `require_reading_mode=True` line from cmd_flow's
    record_baseline() call (run_stage.py) — the exact-message assertion below
    goes red (record either succeeds, or fails for an unrelated reason with a
    different message) with zero connected changes elsewhere.
    """
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    # No reading_mode: section declared.
    (run_dir / "run_config.yaml").write_text("judge:\n  mode: off\n", encoding="utf-8")

    exit_code = rs.cmd_flow(_args(
        tmp_path, from_stage="0_reading", to_stage="0_reading",
        judge="off", geometry="auto", record=True, orchestrator="test-harness",
    ))
    out = capsys.readouterr().out
    assert exit_code == rs.FLOW_EXIT_EP_RECORD
    assert "reading_mode_not_declared" in out
    # fail-closed BEFORE record_baseline wrote anything reading_mode-shaped
    assert not (run_dir / "_run" / "reading_mode.json").exists()
    assert not (run_dir / "_run" / "baseline.json").exists()


def test_L_R2_flow_record_succeeds_with_declared_reading_mode(tmp_path, monkeypatch, capsys):
    """Positive counterpart: the same real entry point, WITH a valid
    reading_mode: section declared, records cleanly and freezes
    _run/reading_mode.json."""
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\n"
        "reading_mode:\n"
        "  lane: controlled\n"
        "  dev_function: false\n"
        "  reading_agent:\n"
        "    model: glm-5.2\n"
        "    sees_images: false\n"
        "    rework_rounds: 1\n"
        "  reading_worker_agent:\n"
        "    model: haiku-4.5\n"
        "    effort: high\n"
        "  toolbox_version: cv-toolbox-v3\n"
        "  isolation_profile: hard-isolation-v2\n",
        encoding="utf-8",
    )

    exit_code = rs.cmd_flow(_args(
        tmp_path, from_stage="0_reading", to_stage="0_reading",
        judge="off", geometry="auto", record=True, orchestrator="test-harness",
    ))
    out = capsys.readouterr().out
    assert exit_code == rs.FLOW_EXIT_OK, out
    assert (run_dir / "_run" / "reading_mode.json").exists()
    frozen = json.loads((run_dir / "_run" / "reading_mode.json").read_text(encoding="utf-8"))
    assert frozen["lane"] == "controlled"
    baseline = json.loads((run_dir / "_run" / "baseline.json").read_text(encoding="utf-8"))
    assert baseline["reading_mode"]["status"] == "present"
    assert baseline["reading_mode"]["record"]["lane"] == "controlled"


# --------------------------------------------------------------------------- #
# M-1 (r3 batchC dispatch §2 MAJOR): reading_mode must freeze at the SAME
# choke point as run_policy — the attempt-creating entrance
# (_manifest_for_attempts) — not at record time. Before this fix, the ONLY
# writer was record_baseline()'s own provision_reading_mode call, invoked at
# RECORD time: a run could execute 0_reading as controlled, then have
# run_config.yaml edited to autonomous before `flow --record`, and the record
# would freeze from the EDITED declaration with nothing to compare it against
# (sol 2026-08-04 batch C r2 review §4, "LATE_FREEZE_PROBE").
# --------------------------------------------------------------------------- #

def test_M1_late_edit_after_reading_executed_fails_closed_not_recorded_as_autonomous(
    tmp_path, monkeypatch,
):
    """The exact repro: a REAL first `flow` invocation executes 0_reading
    under a declared `lane: controlled` (a reading-agent genuinely present)
    and does NOT record. `run_config.yaml` is then edited to `lane:
    autonomous` on the SAME run. A REAL second `flow --record` invocation
    must NOT silently record the edited (autonomous) declaration — it must
    fail closed with `reading_mode_drift`, because reading already executed
    under the original (controlled) declaration, and the frozen record must
    still say controlled.

    Neuter: drop the `reading_mode=run_config.reading_mode` kwarg from any of
    cmd_run/cmd_resample/cmd_flow's `_manifest_for_attempts` call sites (or
    drop the opportunistic freeze block inside `_manifest_for_attempts`
    itself, run_stage.py) ⇒ this lock reds — the second call no longer raises,
    the run records successfully, and `_run/baseline.json` ends up with
    `reading_mode.record.lane == "autonomous"` despite reading having executed
    under `controlled` — exactly the bug this lock exists to catch."""
    monkeypatch.setattr(rs, "_make_draw_fn", _fake_make_draw_fn)
    monkeypatch.setattr(rs, "_render_stage", lambda *a, **k: [])
    _seed_case_data(tmp_path)
    run_dir = tmp_path / "case" / "run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\n"
        "reading_mode:\n"
        "  lane: controlled\n"
        "  dev_function: false\n"
        "  reading_agent:\n"
        "    model: glm-5.2\n"
        "    sees_images: false\n"
        "    rework_rounds: 1\n"
        "  reading_worker_agent:\n"
        "    model: haiku-4.5\n"
        "    effort: high\n"
        "  toolbox_version: cv-toolbox-v3\n"
        "  isolation_profile: hard-isolation-v2\n",
        encoding="utf-8",
    )

    # First real flow invocation: 0_reading actually executes under the
    # declared controlled lane. Does NOT record.
    first_exit = rs.cmd_flow(_args(
        tmp_path, from_stage="0_reading", to_stage="0_reading",
        judge="off", geometry="auto", record=False, orchestrator="test-harness",
    ))
    assert first_exit == rs.FLOW_EXIT_OK
    frozen = json.loads((run_dir / "_run" / "reading_mode.json").read_text(encoding="utf-8"))
    assert frozen["lane"] == "controlled"
    assert not (run_dir / "_run" / "baseline.json").exists()

    # Edit the SAME run's declaration to autonomous — reading already
    # executed under controlled.
    (run_dir / "run_config.yaml").write_text(
        "judge:\n  mode: off\n"
        "reading_mode:\n"
        "  lane: autonomous\n"
        "  dev_function: false\n"
        "  reading_agent: null\n"
        "  reading_worker_agent:\n"
        "    model: target-vlm\n"
        "    effort: high\n"
        "  toolbox_version: cv-toolbox-v3\n"
        "  isolation_profile: hard-isolation-v2\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="reading_mode_drift"):
        rs.cmd_flow(_args(
            tmp_path, from_stage="0_reading", to_stage="0_reading",
            judge="off", geometry="auto", record=True, orchestrator="test-harness",
        ))

    # the frozen record still says controlled — the edit never took effect
    still_frozen = json.loads((run_dir / "_run" / "reading_mode.json").read_text(encoding="utf-8"))
    assert still_frozen["lane"] == "controlled"
    # and no baseline/report was ever written recording it as autonomous
    assert not (run_dir / "_run" / "baseline.json").exists()


# --------------------------------------------------------------------------- #
# L-R1 / L-R4: report_assembly lane annotation
# --------------------------------------------------------------------------- #

def _format_reading_mode():
    from scripts.tool_scripts import report_assembly as ra
    return ra._format_reading_mode


def test_L_R1_report_lane_label_changes_with_declared_lane():
    fmt = _format_reading_mode()
    controlled = ReadingModeResolution(
        status="present",
        record=ReadingModeRecord(
            lane="controlled", dev_function=False,
            reading_agent=ReadingAgentInfo(model="glm-5.2", sees_images=False, rework_rounds=1),
            reading_worker_agent=ReadingWorkerAgentInfo(model="haiku-4.5", effort="high"),
            toolbox_version="cv-toolbox-v3", isolation_profile="hard-isolation-v2",
        ),
    ).model_dump(mode="json")
    autonomous = ReadingModeResolution(
        status="present",
        record=ReadingModeRecord(
            lane="autonomous", dev_function=False,
            reading_agent=None,
            reading_worker_agent=ReadingWorkerAgentInfo(model="target-vlm", effort="high"),
            toolbox_version="cv-toolbox-v3", isolation_profile="hard-isolation-v2",
        ),
    ).model_dump(mode="json")

    controlled_lines = "\n".join(fmt(controlled))
    autonomous_lines = "\n".join(fmt(autonomous))
    assert "controlled" in controlled_lines
    assert "autonomous" in autonomous_lines
    # proves the label is not decorative: the two renders actually differ
    assert controlled_lines != autonomous_lines


def test_L_R4_report_flags_dev_function_as_not_official():
    fmt = _format_reading_mode()
    dev = ReadingModeResolution(
        status="present",
        record=ReadingModeRecord(
            lane="controlled", dev_function=True,
            reading_agent=ReadingAgentInfo(model="opus", sees_images=True, rework_rounds=0),
            reading_worker_agent=ReadingWorkerAgentInfo(model="haiku-4.5", effort="high"),
            toolbox_version="cv-toolbox-v3", isolation_profile="hard-isolation-v2",
        ),
    ).model_dump(mode="json")
    lines = "\n".join(fmt(dev))
    assert "不作为正式成绩" in lines

    official = ReadingModeResolution(
        status="present",
        record=ReadingModeRecord(
            lane="controlled", dev_function=False,
            reading_agent=ReadingAgentInfo(model="opus", sees_images=True, rework_rounds=0),
            reading_worker_agent=ReadingWorkerAgentInfo(model="haiku-4.5", effort="high"),
            toolbox_version="cv-toolbox-v3", isolation_profile="hard-isolation-v2",
        ),
    ).model_dump(mode="json")
    official_lines = "\n".join(fmt(official))
    assert "不作为正式成绩" not in official_lines


def test_L_R3_report_legacy_unknown_does_not_crash_and_does_not_impersonate_lane():
    fmt = _format_reading_mode()
    lines = "\n".join(fmt(None))
    assert "legacy_unknown" in lines
    assert "autonomous" not in lines
    assert "controlled" not in lines

    legacy_status_only = "\n".join(fmt({"status": "legacy_unknown"}))
    assert "legacy_unknown" in legacy_status_only
