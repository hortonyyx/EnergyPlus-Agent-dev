"""D1 must not change either existing single-model preparation path."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import subprocess
import types
from pathlib import Path
from unittest.mock import patch

from src.agent import runtime_entry
from src.agent.runtime_configuration import argv_for, load_configuration
from src.agent.runtime_tools import frozen_bim_client
from scripts.tool_scripts.bim_agent_guidance import filter_tool_catalog, tool_capabilities


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "e07764e6"
CONFIGS = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1/configs"
T1 = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.glm_tests")

# run_bim_agent.py also hosts the Claude Code route, which changes for reasons unrelated to
# the first request (N1 display, 10-07 Windows env and worker option); the request bytes
# themselves are pinned by test_three_single_cases_prepare_identical_shared_first_request_bytes.
FIRST_REQUEST_SOURCES = (
    "src/agent/runtime_entry.py",
    "scripts/tool_scripts/bim_agent_guidance.py",
    "src/agent/bim_inputs.py",
    "src/agent/runtime_tools.py",
    "src/agent/runtime_context.py",
    "src/agent/runtime_delivery.py",
    "src/agent_runtime/adapter.py",
    "src/agent_runtime/anthropic.py",
)


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode()



def git_bytes(path: str, commit: str = BASELINE) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def baseline_configuration_module():
    module = types.ModuleType("baseline_runtime_configuration")
    module.__file__ = str(ROOT / "src/agent/runtime_configuration.py")
    exec(compile(git_bytes("src/agent/runtime_configuration.py"), module.__file__, "exec"),
         module.__dict__)
    return module


def test_single_configuration_loading_and_argv_match_the_dispatch_baseline():
    baseline = baseline_configuration_module()
    for name in ("sm21", "sm24", "sm25"):
        path = CONFIGS / f"{name}_single.json"
        current_value = load_configuration(path)
        baseline_value = baseline.load_configuration(path)
        assert canonical(current_value) == canonical(baseline_value)
        assert argv_for(current_value["cases"][0]) == baseline.argv_for(
            baseline_value["cases"][0])


def test_first_request_sources_are_byte_identical_to_the_dispatch_baseline():
    for relative in FIRST_REQUEST_SOURCES:
        assert (ROOT / relative).read_bytes() == git_bytes(relative), relative


def test_single_runtime_keeps_unbounded_per_request_timeout_and_request_bytes(tmp_path):
    from test_agent_runtime import MESSAGES, response, runtime

    engines = []
    for name in ("implicit", "explicit"):
        engine = runtime(tmp_path / name, [response(text="done")])
        if name == "explicit":
            engine.request_timeout_seconds = None
        assert engine.request_timeout_seconds is None
        with engine.store:
            assert asyncio.run(engine.run(MESSAGES))["status"] == "completed"
        engines.append(engine)
    assert engines[0].adapter.requests == engines[1].adapter.requests


async def prepared_case(case_name: str, tmp_path: Path) -> dict:
    class ModelBoundary(Exception):
        pass

    config = load_configuration(CONFIGS / f"{case_name}_single.json")["cases"][0]
    task = config["scope"]
    assert task.startswith("Scope: ") and "\nBudget: 10800 seconds." in task
    scope_body = task[len("Scope: "):task.index("\nBudget: ")]
    old_run = tmp_path / "claude"
    old_args = T1.arguments(case_name, old_run, 10_800)
    old_args.scope = scope_body
    assert old_args.images.resolve() == (ROOT / config["input"]).resolve()
    assert old_args.floor_plan_images == config["floor_plan_images"]

    launches = []

    def stop(command, **kwargs):
        launches.append(command)
        raise ModelBoundary()

    with patch.object(T1.runner.subprocess, "Popen", stop):
        try:
            T1.runner.run_experiment(old_args)
        except ModelBoundary:
            pass
        else:
            raise AssertionError("Claude runner crossed the guarded model boundary")
    assert len(launches) == 1
    old_request = json.loads((old_run / "agent_request.json").read_bytes())
    old_manifest = json.loads((old_run / "inputs.json").read_bytes())

    runtime_output = tmp_path / "runtime"
    runtime_output.mkdir()
    runtime_run, guide, runtime_task = runtime_entry.prepare_inputs(
        runtime_output,
        images=ROOT / config["input"],
        mesh=None,
        building_input=None,
        scope=task,
        image_kind=config["image_kind"],
        max_candidates=config["max_candidates"],
        floor_plan_images=config["floor_plan_images"],
        started_epoch=1_000.0,
        seconds=config["limits"]["seconds"],
    )
    runtime_manifest = json.loads((runtime_run / "inputs.json").read_bytes())
    async with frozen_bim_client(old_run, repository_root=ROOT, enabled_only=True) as client:
        old_catalog = await client.list_tools()
    async with frozen_bim_client(runtime_run, repository_root=ROOT) as client:
        runtime_complete = await client.list_tools()
    runtime_catalog = filter_tool_catalog(
        runtime_complete, **tool_capabilities(runtime_manifest))
    wrapped_old = [{"type": "function", "function": {
        "name": tool["name"], "description": tool.get("description", ""),
        "parameters": tool["inputSchema"]}} for tool in old_catalog]
    wrapped_runtime = [{"type": "function", "function": {
        "name": tool["name"], "description": tool.get("description", ""),
        "parameters": tool["inputSchema"]}} for tool in runtime_catalog]

    assert old_request["system_prompt"].encode() == guide.encode()
    assert old_request["prompt"].encode() == runtime_task.encode() == task.encode()
    assert canonical(wrapped_old) == canonical(wrapped_runtime)
    assert old_manifest["floor_plan_images"] == runtime_manifest["floor_plan_images"]
    old_images = {key: value["sha256"] for key, value in old_manifest["images"].items()}
    runtime_images = {key: value["sha256"] for key, value in runtime_manifest["images"].items()}
    assert old_images == runtime_images
    shared_request = canonical({
        "system": guide,
        "task": task,
        "tools": wrapped_runtime,
    })
    return {
        "case": case_name,
        "shared_first_request_sha256": hashlib.sha256(shared_request).hexdigest(),
        "system_sha256": hashlib.sha256(guide.encode()).hexdigest(),
        "task_sha256": hashlib.sha256(task.encode()).hexdigest(),
        "tools_sha256": hashlib.sha256(canonical(wrapped_runtime)).hexdigest(),
        "tool_count": len(wrapped_runtime),
        "image_sha256": runtime_images,
        "floor_plan_images": runtime_manifest["floor_plan_images"],
        "claude_model_launches_blocked": len(launches),
        "model_requests": 0,
    }


def test_three_single_cases_prepare_identical_shared_first_request_bytes(tmp_path):
    rows = []
    for name in ("sm21", "sm24", "sm25"):
        folder = tmp_path / name
        folder.mkdir()
        rows.append(asyncio.run(prepared_case(name, folder)))
    assert [row["case"] for row in rows] == ["sm21", "sm24", "sm25"]
    assert all(row["tool_count"] > 0 and row["model_requests"] == 0 for row in rows)
