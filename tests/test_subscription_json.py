"""Offline contract tests for the Claude subscription JSON correction route."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent import pipeline
from src.agent.execution.subscription_json import call_subscription_json


SECTION = {"provider": "claude_subscription", "model_name": "sonnet"}


def _response(result: object, **extra: object) -> SimpleNamespace:
    payload = {"result": result, "is_error": False, **extra}
    return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")


def test_subscription_cli_is_isolated_tool_free_and_records_cli_usage(tmp_path: Path):
    calls: list[dict] = []

    def runner(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return _response(
            '{"accepted": true}',
            modelUsage={"claude-sonnet-4-6": {"inputTokens": 12}},
            usage={"input_tokens": 12},
            total_cost_usd=0.00125,
        )

    result = call_subscription_json(
        SECTION,
        "system secret-looking API_KEY=do-not-save",
        "human payload",
        out_dir=tmp_path,
        prefix="correction",
        extract_json=pipeline._extract_json,
        runner=runner,
    )

    assert result == {"accepted": True}
    assert len(calls) == 1
    call = calls[0]
    assert call["input"] == "human payload"
    assert call["command"] == [
        "claude", "-p", "--model", "sonnet", "--tools", "",
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--setting-sources", "", "--no-session-persistence", "--output-format",
        "json", "--system-prompt", "system secret-looking API_KEY=do-not-save",
    ]
    assert "--bare" not in call["command"]
    assert Path(call["cwd"]).resolve() != Path.cwd().resolve()
    assert set(call["env"]) <= {"PATH", "HOME", "LANG", "LC_ALL"}
    assert "API_KEY" not in call["env"]
    assert "BASE_URL" not in call["env"]
    assert "AUTH_TOKEN" not in call["env"]

    attempts = list(tmp_path.iterdir())
    assert len(attempts) == 1
    request = json.loads((attempts[0] / "request.json").read_text())
    assert request["command"][-1] == "[prompt supplied separately]"
    assert "human payload" not in (attempts[0] / "request.json").read_text()
    usage = json.loads((attempts[0] / "cli_usage.json").read_text())
    assert usage["modelUsage"] == {"claude-sonnet-4-6": {"inputTokens": 12}}
    assert usage["usage"] == {"input_tokens": 12}
    assert usage["estimated_cost_usd"] == 0.00125
    assert "not a bill" in usage["estimated_cost_note"]


@pytest.mark.parametrize("key", ["api_key", "base_url"])
def test_subscription_rejects_api_route_settings_without_starting_cli(key: str):
    section = {**SECTION, key: "https://example.invalid"}
    called = False

    def runner(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("CLI must not start")

    with pytest.raises(RuntimeError, match=key):
        call_subscription_json(
            section, "system", "human", out_dir=None, prefix="x",
            extract_json=pipeline._extract_json, runner=runner,
        )
    assert not called


def test_subscription_is_error_is_a_loud_failure_without_fallback(tmp_path: Path):
    calls = 0

    def runner(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"is_error": True, "result": "quota exhausted"}),
            stderr="API_KEY=should-not-appear CLAUDE_CODE_OAUTH_TOKEN=also-hidden",
        )

    with pytest.raises(RuntimeError, match="is_error"):
        call_subscription_json(
            SECTION, "system", "human", out_dir=tmp_path, prefix="correction",
            attempts=1, extract_json=pipeline._extract_json, runner=runner,
        )
    assert calls == 1
    stderr = next(tmp_path.iterdir()).joinpath("stderr.txt").read_text()
    assert "should-not-appear" not in stderr
    assert "also-hidden" not in stderr
    assert "[REDACTED]" in stderr


def test_subscription_parse_validation_retry_keeps_format_guidance_and_attempts(tmp_path: Path):
    prompts: list[str] = []
    outcomes = [_response('{"ok": false}'), _response('```json\n{"ok": true}\n```')]

    def runner(_command, **kwargs):
        prompts.append(kwargs["input"])
        return outcomes.pop(0)

    def validate(parsed: dict) -> None:
        if not parsed["ok"]:
            raise ValueError("field path: ok must be true")

    def guide(exc: BaseException) -> str | None:
        assert "field path" in str(exc)
        return "FORMAT CORRECTION: set ok to true."

    assert call_subscription_json(
        SECTION, "system", "human", out_dir=tmp_path, prefix="correction",
        attempts=2, validate=validate, retry_guidance=guide,
        extract_json=pipeline._extract_json, runner=runner,
    ) == {"ok": True}
    assert prompts == ["human", "human\n\nFORMAT CORRECTION: set ok to true."]
    assert len(list(tmp_path.iterdir())) == 2


def test_subscription_transport_retry_is_blind_and_timeout_keeps_output(tmp_path: Path):
    prompts: list[str] = []
    timeout = subprocess.TimeoutExpired("claude", 4, output=b"partial", stderr=b"token=hide")
    outcomes: list[object] = [timeout, _response('{"ok": true}')]

    def runner(_command, **kwargs):
        prompts.append(kwargs["input"])
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    guide_calls = 0

    def guide(_exc: BaseException) -> str:
        nonlocal guide_calls
        guide_calls += 1
        return "must not appear"

    assert call_subscription_json(
        {**SECTION, "timeout_seconds": 4}, "system", "human", out_dir=tmp_path,
        prefix="correction", attempts=2, retry_guidance=guide,
        extract_json=pipeline._extract_json, runner=runner,
    ) == {"ok": True}
    assert prompts == ["human", "human"]
    assert guide_calls == 0
    first = sorted(tmp_path.iterdir())[0]
    assert (first / "stdout.txt").read_text() == "partial"
    assert "hide" not in (first / "stderr.txt").read_text()
    assert json.loads((first / "cli_usage.json").read_text())["timed_out"] is True


def test_pipeline_dispatches_only_explicit_subscription_provider(monkeypatch):
    received: dict = {}

    def fake_call(section, system_prompt, human, **kwargs):
        received.update(section=section, system_prompt=system_prompt, human=human, **kwargs)
        return {"route": "subscription"}

    monkeypatch.setattr(pipeline, "call_subscription_json", fake_call)
    result = pipeline._call_json_llm(
        SECTION, "system", "human", out_dir=None, prefix="correction", attempts=2,
    )
    assert result == {"route": "subscription"}
    assert received["section"] is SECTION
    assert received["extract_json"] is pipeline._extract_json
    assert received["attempts"] == 2
    assert os.environ.get("DEEPSEEK_API_KEY") not in received
