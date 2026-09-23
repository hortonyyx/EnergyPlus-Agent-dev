"""Offline checks that both coordinator and local observation stay on GLM."""
import json

import pytest

from scripts.tool_scripts import run_bim_agent as runner
from tests.test_bim_agent_tools import _run_with_one_image


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
    assert command[0] == str(runner.ROOT / "scripts/glm_code.sh")
    assert command[command.index("--model") + 1] == "glm-5.3-flash"
    assert kwargs["env"]["GLM_SMALL_MODEL"] == "glm-5.3-flash"
    assert receipt["requested_model"] == "glm-5.3-flash"
    assert receipt["provider"] == "glm" and receipt["actual_model"] == actual
    assert bool(receipt.get("routing_error")) == (actual != "glm-5.3-flash")
    assert len(calls) == 1  # No fallback on routing mismatch.


def test_glm_and_opus_cannot_be_mixed(tmp_path):
    run = _run_with_one_image(tmp_path)
    manifest = json.loads((run / "inputs.json").read_text())
    runner.dump(run / "inputs.json", {**manifest, "provider": "glm"})
    with pytest.raises(ValueError, match="cannot be combined"):
        runner.subscription(run, "unused", model="opus", name="agent", exploratory_opus=True)
