"""Offline checks that both coordinator and local observation stay on GLM."""
import json
import os
import sys

import pytest

from scripts.tool_scripts import run_bim_agent as runner
from tests.test_bim_agent_tools import _run_with_one_image


@pytest.fixture(autouse=True)
def offline_git_identity(monkeypatch):
    # Popen below substitutes only the model client. Keep the independent Git
    # metadata lookup out of that fake client while exercising real verification.
    monkeypatch.setattr("src.agent_runtime.versions.source_commit", lambda root: "offline-git-fixture")


@pytest.mark.parametrize("readonly", [False, True])
@pytest.mark.parametrize("actual", ["glm-5.3-flash", "wrong-model"])
def test_explicit_glm_route_and_receipt(tmp_path, monkeypatch, readonly, actual):
    run = _run_with_one_image(tmp_path)
    manifest = json.loads((run / "inputs.json").read_text())
    manifest["provider"] = "glm"
    runner.dump(run / "inputs.json", manifest)
    toolkit = runner.Toolkit(run)
    child, _ = runner.prepare_detail_observation(toolkit, "Read the image", ["plan.png"], "detail_01")
    assert json.loads((child / "inputs.json").read_text())["provider"] == "glm"
    calls = []

    class OfflineProcess:
        returncode = 0

        def __init__(self, command, **kwargs):
            calls.append((command, kwargs))
            kwargs["stdout"].write(json.dumps({"type": "system", "subtype": "init", "model": actual}) + "\n")
            kwargs["stdout"].write(json.dumps({"type": "result", "is_error": False, "result": "fixture"}) + "\n")

        def communicate(self, prompt, timeout):
            assert prompt == "offline only"

    monkeypatch.setattr(runner.subprocess, "Popen", OfflineProcess)
    receipt = runner.subscription(child if readonly else run, "offline only",
        model="haiku" if readonly else "sonnet", name="agent", readonly=readonly)
    command, kwargs = calls[0]
    if os.name == "nt":
        assert command[:2] == [sys.executable, str(runner.ROOT / "scripts/glm_code.py")]
    else:
        assert command[0] == str(runner.ROOT / "scripts/glm_code.sh")
    assert command[command.index("--model") + 1] == "glm-5.3-flash"
    assert kwargs["env"]["GLM_SMALL_MODEL"] == "glm-5.3-flash"
    assert receipt["requested_model"] == "glm-5.3-flash"
    assert receipt["provider"] == "glm" and receipt["actual_model"] == actual
    assert receipt["runtime_version"].startswith("runtime-v")
    assert receipt["domain_version"].startswith("domain-v")
    assert receipt["git_commit"] == "offline-git-fixture"
    assert json.loads(((child if readonly else run) / "agent_versions.json").read_bytes())["role_models"] == receipt["role_models"]
    assert bool(receipt.get("routing_error")) == (actual != "glm-5.3-flash")
    assert len(calls) == 1  # No fallback on routing mismatch.


def test_glm_and_opus_cannot_be_mixed(tmp_path):
    run = _run_with_one_image(tmp_path)
    manifest = json.loads((run / "inputs.json").read_text())
    runner.dump(run / "inputs.json", {**manifest, "provider": "glm"})
    with pytest.raises(ValueError, match="cannot be combined"):
        runner.subscription(run, "unused", model="opus", name="agent", exploratory_opus=True)


@pytest.mark.parametrize("used", ["claude-sonnet-5", "claude-sonnet-5-5"])
def test_claude_recovery_pins_version_and_detects_usage_drift(tmp_path, monkeypatch, used):
    run = _run_with_one_image(tmp_path)
    calls = []

    class OfflineProcess:
        returncode = 0

        def __init__(self, command, **kwargs):
            calls.append(command)
            kwargs["stdout"].write(json.dumps({"type": "system", "subtype": "init",
                                               "model": "claude-sonnet-5"}) + "\n")
            kwargs["stdout"].write(json.dumps({"type": "result", "is_error": False,
                                               "modelUsage": {used: {}}}) + "\n")

        def communicate(self, prompt, timeout):
            pass

    monkeypatch.setattr(runner.subprocess, "Popen", OfflineProcess)
    receipt = runner.subscription(run, "offline only", model="sonnet", name="agent", effort="medium")
    assert calls[0][calls[0].index("--model") + 1] == "claude-sonnet-5"
    assert receipt["requested_role"] == "sonnet" and receipt["requested_model"] == "claude-sonnet-5"
    assert bool(receipt.get("routing_error")) == (used != "claude-sonnet-5")
    assert len(calls) == 1
    command = calls[0]
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--allowedTools") + 1] == "mcp__bim__*"
    assert "--agents" not in command and "--disallowedTools" not in command


@pytest.mark.parametrize("used", [("claude-sonnet-5-5", "claude-haiku-4-5-20251001"),
                                  ("claude-sonnet-5-5", "claude-sonnet-5")])
def test_sonnet55_main_with_haiku_worker(tmp_path, monkeypatch, used):
    run = _run_with_one_image(tmp_path)
    calls = []

    class OfflineProcess:
        returncode = 0

        def __init__(self, command, **kwargs):
            calls.append((command, kwargs))
            kwargs["stdout"].write(json.dumps({"type": "system", "subtype": "init",
                                               "model": "claude-sonnet-5-5"}) + "\n")
            kwargs["stdout"].write(json.dumps({"type": "result", "is_error": False,
                                               "modelUsage": {name: {} for name in used}}) + "\n")

        def communicate(self, prompt, timeout):
            pass

    monkeypatch.setattr(runner.subprocess, "Popen", OfflineProcess)
    receipt = runner.subscription(run, "offline only", model="sonnet", name="agent",
                                  main_model="claude-sonnet-5-5", workers="haiku")
    command, kwargs = calls[0]
    assert command[command.index("--model") + 1] == "claude-sonnet-5-5"
    assert command[command.index("--tools") + 1] == "Agent"
    denied = command[command.index("--disallowedTools") + 1].split(",")
    assert "Agent(general-purpose)" in denied and "Agent(worker)" not in denied
    worker = json.loads(command[command.index("--agents") + 1])["worker"]
    assert worker["model"] == "claude-haiku-4-5-20251001"
    assert worker["prompt"].endswith(runner.run_guide(run))
    assert kwargs["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"
    if os.name == "nt":  # the CLI's Python tool server must read UTF-8 run files
        assert kwargs["env"]["PYTHONUTF8"] == "1"
    assert receipt["worker_model"] == "claude-haiku-4-5-20251001"
    assert receipt["role_models"]["worker"]["model"] == "claude-haiku-4-5-20251001"
    assert receipt["role_models"]["worker"]["output_tokens"] is None
    assert bool(receipt.get("routing_error")) == ("claude-sonnet-5" in used)
    with pytest.raises(ValueError, match="main_model must be"):
        runner.subscription(run, "unused", model="sonnet", name="x", main_model="claude-opus-5-5")
