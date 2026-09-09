from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.agent.execution import automatic_reading, isolation
from src.agent.execution.isolation import (
    build_isolation_workspace,
    clean_spawn_env,
    reader_invocations_path,
    spawn_command,
)
from src.agent.execution.manifest import RunManifestV2, load_run_manifest
from src.agent.execution.run_provision import provision_run


CASE = Path("case_tests/e2e_tests/sm21_anchor")
REAL_OUTPUT = CASE / "run_2026-06-20_gpt54_reading/0_reading/attempts/002/output.json"


def _prepared_run(tmp_path: Path) -> tuple[Path, Path]:
    case_dir = tmp_path / "sm21_anchor"
    # The isolation builder needs only the original inputs.  Do not copy the
    # many checked-in historical runs merely to exercise a new empty run.
    shutil.copytree(CASE / "case_data", case_dir / "case_data")
    run_dir = tmp_path / "new_run"
    run_dir.mkdir()
    provision_run(
        case_dir,
        run_dir,
        run_profile="exploratory",
        capability_profile="orthogonal_polygon",
    )
    return case_dir, run_dir


def test_automatic_reading_runs_one_subscription_draw_and_reuses_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir, run_dir = _prepared_run(tmp_path)
    calls: list[dict] = []

    def fake_spawn(staging_root: Path, **kwargs):
        calls.append(kwargs)
        audit = staging_root.parent / f"{staging_root.name}.audit"
        audit.mkdir(exist_ok=True)
        stdout = audit / "reader_stdout.txt"
        stderr = audit / "reader_stderr.txt"
        stdout.write_text('{"usage": {"input_tokens": 1}}', encoding="utf-8")
        stderr.write_text("", encoding="utf-8")
        (audit / "reader_invocations.jsonl").write_text(json.dumps({
            "argv_redacted": ["claude", "-p", "<prompt sha256=fake>"],
            "stdout_path": str(stdout),
            "stderr_path": str(stderr),
            "response_usage": {"input_tokens": 1},
        }) + "\n", encoding="utf-8")
        (staging_root / "out" / "output.json").write_text(
            json.dumps({"views": json.loads(REAL_OUTPUT.read_text(encoding="utf-8"))}),
            encoding="utf-8",
        )
        (staging_root / "out" / "reading_summary.md").write_text(
            "mock subscription reading\n", encoding="utf-8"
        )
        return ["claude", "-p", "redacted prompt"]

    monkeypatch.setattr(automatic_reading, "spawn_command", fake_spawn)
    result = automatic_reading.run_automatic_reading(
        case_dir, run_dir, model="haiku", timeout_seconds=12
    )

    assert result["status"] == "accepted"
    assert Path(result["attempt_dir"]).is_dir()
    assert calls == [{
        "model": "claude-haiku-4-5-20251001",
        "execute": True,
        "timeout_seconds": 12,
        "subscription_only": True,
    }]
    report = json.loads((run_dir / "_run" / "automatic_reading.json").read_text())
    assert report["status"] == "accepted"
    manifest = load_run_manifest(run_dir)
    assert isinstance(manifest, RunManifestV2)
    assert manifest.accepted("0_reading") is not None

    initial_report = (run_dir / "_run" / "automatic_reading.json").read_text()
    reused = automatic_reading.run_automatic_reading(case_dir, run_dir, model="haiku")
    assert reused["status"] == "reused"
    assert (run_dir / "_run" / "automatic_reading.json").read_text() == initial_report
    assert len(calls) == 1


def test_automatic_reading_refuses_implicit_retry_and_invalid_model(tmp_path: Path) -> None:
    case_dir, run_dir = _prepared_run(tmp_path)
    stage = run_dir / "0_reading"
    stage.mkdir()
    (stage / "partial.json").write_text("{}", encoding="utf-8")

    blocked = automatic_reading.run_automatic_reading(case_dir, run_dir, model="sonnet")
    assert blocked["status"] == "blocked"
    invalid = automatic_reading.run_automatic_reading(case_dir, run_dir, model="opus")
    assert invalid["status"] == "error"


def test_prior_failed_automatic_report_blocks_a_second_draw(tmp_path: Path) -> None:
    case_dir, run_dir = _prepared_run(tmp_path)
    report_path = run_dir / "_run" / "automatic_reading.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text('{"status":"error","staging_root":"/tmp/kept"}\n')

    result = automatic_reading.run_automatic_reading(case_dir, run_dir, model="haiku")

    assert result["status"] == "blocked"
    assert report_path.read_text() == '{"status":"error","staging_root":"/tmp/kept"}\n'


def test_subscription_environment_omits_api_and_endpoint_selectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-pass")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://provider.invalid")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "must-not-pass")
    monkeypatch.setenv("ANTHROPIC_MODEL", "provider-model")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "subscription-token")
    env = clean_spawn_env(tmp_path, subscription_only=True)
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "subscription-token"
    assert not any(key.startswith("ANTHROPIC_") for key in env)


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (
            subprocess.TimeoutExpired(
                ["claude"], 1, output='{"usage":{"input_tokens":2}}', stderr="interrupted"
            ),
            subprocess.TimeoutExpired,
        ),
        (
            subprocess.CompletedProcess(
                ["claude"], 0, '{"is_error":true,"error":"error_max_turns"}', ""
            ),
            RuntimeError,
        ),
    ],
)
def test_subscription_spawn_archives_timeout_and_soft_error_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: object,
    expected: type[BaseException],
) -> None:
    case_dir, _ = _prepared_run(tmp_path)
    staging = build_isolation_workspace(case_dir, staging_root=tmp_path / "staging").staging_root

    def fake_run(command, **kwargs):
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "2.1.198", "")
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(isolation.subprocess, "run", fake_run)
    with pytest.raises(expected):
        spawn_command(
            staging,
            model="claude-haiku-4-5-20251001",
            execute=True,
            timeout_seconds=1,
            subscription_only=True,
        )
    invocation = json.loads(reader_invocations_path(staging).read_text().splitlines()[-1])
    assert Path(invocation["stdout_path"]).read_text()
    assert invocation["stdout_path"].startswith(str(staging.parent / f"{staging.name}.audit"))
