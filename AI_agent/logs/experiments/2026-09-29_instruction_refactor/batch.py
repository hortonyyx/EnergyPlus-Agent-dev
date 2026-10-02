"""Instruction-layer refactor: offline preflight, then separately approved single runs.

The system prompt is assembled by input type (principles, drawing method, tool
index, delivery), references keep only formats/interfaces, the cold-start
sentence is neutral, and the task scope states only the task, delivery
requirements and experiment constraints. ``prepare`` stops every case at the
model-process boundary (0 calls). ``run --run runNN`` launches exactly one
approved run; read its receipt before starting the next in a separate step.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[3]
EXPERIMENTS = HERE.parent
IMAGES = {"sm21": "case_tests/e2e_tests/sm21_anchor/case_data",
          "sm24": "case_tests/e2e_tests/sm24_anchor/case_data",
          "sm25": "case_tests/e2e_tests/sm25-L_anchor/case_data"}
PLAN = {"run94": ("sm21", "2026-09-29_sm21_instruction_refactor_run94"),
        "run95": ("sm21", "2026-09-29_sm21_instruction_refactor_run95"),
        "run96": ("sm24", "2026-09-29_sm24_instruction_refactor_run96"),
        "run97": ("sm25", "2026-09-29_sm25_instruction_refactor_run97")}
SCOPE = (
    "Reconstruct one inspectable lightweight BIM of the whole building shown in the supplied "
    "original plans and elevations. This is an original-image-only run: no saved plans, generated "
    "BIM, prior observations, calibration, reference counts, target heights or GT are supplied. "
    "Use build_plan_bim for each distinct floor and, if there are several, assemble_plan_bim; do "
    "not invent a floor merely to use assembly.\n"
    "Delivery requirements: exterior opening heights observed on the elevations are saved as "
    "located claims confirmed or applied on the delivered candidate, distinct from assumptions; "
    "unobserved internal door heights may remain explicit assumptions. The delivered candidate's "
    "saved notes match its actual state. Report what was observed, assumed and left unverified.\n"
    "Experiment constraints: work directly with the deterministic and visual tools, without "
    "review_detail or other delegation.")

sys.path.insert(0, str(RUNTIME))
os.environ["PYTHONPATH"] = str(RUNTIME)
from scripts.tool_scripts import run_bim_agent as runner  # noqa: E402
from scripts.tool_scripts.bim_agent_guidance import build_guide  # noqa: E402

assert Path(runner.__file__).resolve().is_relative_to(RUNTIME.resolve()), runner.__file__
load = lambda path: json.loads(Path(path).read_text())
GUIDE = build_guide(drawings=True, mesh=False)


def arguments(case, run):
    return SimpleNamespace(
        command="run", images=RUNTIME / IMAGES[case], mesh=None, building_input=None, out=run,
        scope=SCOPE, timeout=3000, provider="claude", exploratory_opus=False, effort="medium",
        max_candidates=24, continuation_rounds=0, resume_candidate=None, resume_plan=None,
        plan_image=None)


def conditions(case, names):
    return dict(
        case=case, scope_sha256=hashlib.sha256(SCOPE.encode()).hexdigest(),
        implementation_sha256={name: runner.digest(RUNTIME / name) for name in names},
        guide_sha256=hashlib.sha256(GUIDE.encode()).hexdigest(),
        references_sha256={k: hashlib.sha256(v.encode()).hexdigest() for k, v in runner.REFERENCES.items()},
        batch_script_sha256=runner.digest(Path(__file__)), provider="claude", role="sonnet",
        effort="medium", timeout_seconds=3000, max_candidates=24, continuation_rounds=0,
        delegation="prohibited by the scope")


async def served(run):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    params = StdioServerParameters(command=sys.executable, cwd=str(RUNTIME),
        args=[str(RUNTIME / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            descriptions = sum(len(tool.description or "") for tool in tools.tools)
            result = await session.call_tool("get_bim_reference", {"topic": "reconstruction"})
            payload = result.structuredContent or json.loads(result.content[0].text)
            assert not result.isError and payload["reference"] == runner.REFERENCES["reconstruction"]
            return dict(tool_names=sorted(tool.name for tool in tools.tools),
                        tool_description_chars=descriptions)


def instruction_volume(request, exposure):
    default_refs = ("plan_partition", "plan_assembly", "claims")
    return dict(system_prompt=len(request["system_prompt"]), user_prompt=len(request["prompt"]),
                references_usually_read=sum(len(runner.REFERENCES[k]) for k in default_refs),
                references_usually_read_topics=list(default_refs),
                tool_descriptions=exposure["tool_description_chars"])


def prepare():
    class StoppedAtModelBoundary(Exception):
        pass

    def stop(*args, **kwargs):
        raise StoppedAtModelBoundary()

    summary = {}
    for run_id, (case, _) in PLAN.items():
        with tempfile.TemporaryDirectory(prefix="bim-refactor-") as directory:
            run = Path(directory) / "run"
            with patch.object(runner.subprocess, "Popen", stop):
                try:
                    runner.run_experiment(arguments(case, run))
                except StoppedAtModelBoundary:
                    pass
                else:
                    raise AssertionError("the model launch must be blocked")
            manifest, request = load(run / "inputs.json"), load(run / "agent_request.json")
            frozen = conditions(case, sorted(manifest["implementation_sha256"]))
            assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
            assert not manifest["input_contents"]["saved_generated_proposal"]["included"]
            assert request["system_prompt"] == GUIDE and request["effort"] == "medium"
            assert "mesh_input" not in request["system_prompt"]
            exposure = asyncio.run(served(run))
            volume = instruction_volume(request, exposure)
            runner.dump(HERE / f"preflight_{run_id}.json", dict(
                run_id=run_id, case=case, status="prepared_pending_user_decision", model_calls=0,
                model_process_blocked=True, original_images_only=True,
                image_sha256={k: v["sha256"] for k, v in manifest["images"].items()},
                prompt=request["prompt"], instruction_volume=volume, conditions=frozen, **exposure))
            summary[run_id] = dict(case=case, **volume)
    print(json.dumps(dict(model_calls=0, runs=summary), indent=1))


def run_one(run_id):
    case, name = PLAN[run_id]
    RUN = EXPERIMENTS / name
    approval = load(HERE / "approval.json")
    assert run_id in approval["approved_runs"], "record the user's approval for this exact run first"
    order = list(PLAN)
    for earlier in order[:order.index(run_id)]:
        if earlier not in approval["approved_runs"]:
            continue
        receipt = load(EXPERIMENTS / PLAN[earlier][1] / "agent_receipt.json")
        assert receipt.get("returncode") == 0 and not (receipt.get("result") or {}).get("is_error"), \
            f"{earlier} did not end normally; stop the batch"
    prepared = load(HERE / f"preflight_{run_id}.json")["conditions"]
    assert prepared == conditions(case, sorted(prepared["implementation_sha256"])), "prepared runtime changed"
    assert not RUN.exists(), "do not overwrite or retry an experiment"
    original, calls = runner.subscription, []

    def invoke(path, *call_args, **kwargs):
        calls.append(1)
        assert len(calls) == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        manifest = load(path / "inputs.json")
        assert manifest["implementation_sha256"] == prepared["implementation_sha256"]
        runner.dump(path / "experiment_condition.json", dict(run_id=run_id, **prepared))
        for relative in manifest["implementation_sha256"]:
            destination = path / "runtime_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((RUNTIME / relative).read_bytes())
        return original(path, *call_args, **kwargs)

    with patch.object(runner, "subscription", invoke):
        runner.run_experiment(arguments(case, RUN))
    assert len(calls) == 1
    receipt = load(RUN / "agent_receipt.json")
    print(json.dumps(dict(run=RUN.name, returncode=receipt.get("returncode"),
        elapsed_seconds=receipt.get("elapsed_seconds"), actual_model=receipt.get("actual_model"),
        is_error=(receipt.get("result") or {}).get("is_error"))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--run", choices=sorted(PLAN))
    args = parser.parse_args()
    prepare() if args.action == "prepare" else run_one(args.run)
