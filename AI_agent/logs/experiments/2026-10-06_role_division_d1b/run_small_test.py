"""Approved D1b three-reader GLM subscription batch on sealed final Agent bytes.

No coordinator model, whole-building generation, other provider or automatic
second batch. References are loaded only after the three readers have stopped.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from contextlib import AsyncExitStack
from pathlib import Path

from src.agent.runtime_entry import prepare_inputs
from src.agent.runtime_roles.accounting import role_accounting
from src.agent.runtime_roles.config import load_roles
from src.agent.runtime_roles.guidance import guidance_catalog
from src.agent.runtime_roles.session import RoleSession
from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client
from src.agent_runtime.agent_registry import agent_version_record
from src.agent_runtime.anthropic import HttpAnthropicAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.providers import GLM_SUBSCRIPTION_ANTHROPIC, subscription_credentials
from src.agent_runtime.store import EventStore


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUT_ROOT = ROOT / "AI_agent/archive/local_backup/d1b"
ORIGINALS = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm24/images"
AUTHORIZED_CREDENTIALS = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\.env")
ROUTES = {role: {"provider": GLM_SUBSCRIPTION_ANTHROPIC, "model": "glm-5.3-flash",
                "reasoning_effort": "medium", "output_tokens": 32768}
          for role in ("coordinator", "plan_reader", "elevation_reader")}
TASKS = [
    {"task_id": "sm24-plan", "role_id": "plan_reader", "image": "1f_view.png", "target": "F1",
     "instructions": "Read this ground-floor plan as F1. Use metres; world origin is the southwest outer corner, "
         "+X east/right, +Y north/up. Read scale from the drawing dimensions. Infer heights only if needed and label "
         "them assumptions, as no elevation is supplied to you. Preserve physical room/wall and opening relationships. "
         "Tie each plan item to a localized original-image box. Use the isolated trial then submit_plan_reading "
         "with its successful plan_sha256 and unresolved items. Do not retype the plan in the submission or final text.",
     "budget": {"model_calls": 24, "tool_calls": 80}},
    {"task_id": "sm24-north", "role_id": "elevation_reader", "image": "North_view.png", "target": "North/F1",
     "instructions": "Read the North facade from outside looking South, one storey F1. World origin is the southwest "
         "outer corner, +X east, +Y north. Image left-to-right decreases world X. Calibrate from printed dimensions. "
         "Use facade ground line Z=0, not an assumed finished-floor origin. Report every window and door with width, "
         "absolute sill/head, level marks and actual original-image evidence. Call submit_elevation_reading to deliver.",
     "budget": {"model_calls": 8, "tool_calls": 30}},
    {"task_id": "sm24-east", "role_id": "elevation_reader", "image": "East_view.png", "target": "East/F1",
     "instructions": "Read the East facade from outside looking West, one storey F1. World origin is the southwest "
         "outer corner, +X east, +Y north. Image left-to-right increases world Y. Calibrate from printed dimensions. "
         "Use facade ground line Z=0, not an assumed finished-floor origin. Report every window and door with width, "
         "absolute sill/head, level marks and actual original-image evidence. Call submit_elevation_reading to deliver.",
     "budget": {"model_calls": 8, "tool_calls": 30}},
]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


async def run(output, credentials):
    if credentials.resolve() != AUTHORIZED_CREDENTIALS.resolve():
        raise ValueError("use the explicit authorized main-tree .env read-only")
    if output.exists():
        raise ValueError("output already exists; no second batch or automatic rerun")
    final_agent = agent_version_record(ROOT)
    if not final_agent["version_id"].startswith("t1-20261006-d1b.") or ".dev" in final_agent["version_id"]:
        raise ValueError("register and verify the final D1b Agent before this real batch")
    output.mkdir(parents=True)
    started = time.time()
    limits = RunLimits(model_calls=40, tool_calls=160, tokens=3_000_000, seconds=10800,
                       max_model_retries=2, retry_backoff_seconds=1)
    run_dir, _, _ = prepare_inputs(output, images=ORIGINALS, mesh=None, building_input=None,
        scope="D1b approved three single-image readers only. No coordinator model or whole-building generation.",
        image_kind="drawings", max_candidates=24, floor_plan_images=["1f_view.png"],
        started_epoch=started, seconds=limits.seconds)
    write(output / "small_test_manifest.json", {"schema_version": "d1b-small-test-v1", "tasks": TASKS,
        "roles": ROUTES, "limits": limits.model_dump(mode="json"), "max_reader_tasks": 3,
        "max_actual_requests": 40, "coordinator_model_requests": 0, "agent": final_agent,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "credentials_policy": "explicit read-only authorized main-tree .env; no content copied",
        "reference_policy": "assessment only, never reader input", "guidance": guidance_catalog()})
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        base, key = subscription_credentials(credentials, provider=GLM_SUBSCRIPTION_ANTHROPIC)
        actual_requests = 0

        class GuardedAdapter(HttpAnthropicAdapter):
            async def send(self, request, *, timeout):
                nonlocal actual_requests
                requests = [event for event in store.all_events if event.payload.event_type == "adapter_request"]
                if (len(requests) > 40 or actual_requests >= 40
                        or {event.task_id for event in requests} - {task["task_id"] for task in TASKS}):
                    raise ValueError("approved request/task boundary reached before HTTP")
                actual_requests += 1
                write(output / "http_boundary.json", {"attempted_http_requests": actual_requests,
                    "maximum": 40, "provider": GLM_SUBSCRIPTION_ANTHROPIC, "whole_building_runs": 0})
                print(f"GLM subscription request {actual_requests}/40", flush=True)
                return await super().send(request, timeout=timeout)

        def factory(task_id, configuration, child):
            if (task_id not in {task["task_id"] for task in TASKS}
                    or configuration["provider"] != GLM_SUBSCRIPTION_ANTHROPIC
                    or configuration["model"] != "glm-5.3-flash"):
                raise ValueError("only the three approved GLM subscription readers may request")
            return GuardedAdapter(base_url=base, api_key=key)

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(frozen_bim_client(run_dir, repository_root=ROOT))
            frozen = FrozenBimTools(client, coordinator_role(limits.ledger_limit()), run_directory=run_dir)
            session = RoleSession(store=store, frozen=frozen, routes=load_roles(ROUTES),
                adapter_factory=factory, limits=limits, root=ROOT, max_concurrent_readers=4, started_epoch=started)
            outcomes = await session.delegate_many(TASKS)
            accounting = role_accounting(store, session.registry)
            assert actual_requests <= accounting["requests"] <= 40
            assert accounting["by_role"]["coordinator"]["requests"] == 0
            unchanged = agent_version_record(ROOT) == final_agent
            write(output / "small_test_result.json", {"wall_seconds": time.time() - started,
                "results": outcomes["results"], "accounting": accounting, "actual_http_requests": actual_requests,
                "agent_unchanged": unchanged, "whole_building_runs": 0, "paratera_requests": 0, "deepseek_requests": 0})
            store.write_json("role_state.json", session.state())
            if not unchanged:
                raise ValueError("Agent changed during the small test; report invalid final-code evidence")
    from src.agent.runtime_behaviour import write_behaviour_report
    write_behaviour_report(output / "events.jsonl", output / "behaviour")
    return evaluate(output)


def evaluate(output):
    # Assessment dependencies and reference data are never passed to a reader.
    from scoring_bridge import convert_role_artifacts, score_scoped_answer
    result = json.loads((output / "small_test_result.json").read_bytes())
    options = {"case": "sm24_anchor", "assigned_plan_floors": ["F1"],
               "assigned_elevation_facades": ["North", "East"], "elevation_artifacts": []}
    for record in result["results"]:
        if not record.get("artifact"):
            continue
        path = output / record["artifact"]["path"]
        if record["role_id"] == "plan_reader":
            receipt = record["validation"]
            trial = path.parent / "bim/trial_workspace"
            options.update(plan_artifact=path, plan_trial_source=trial / receipt["candidate"] / "source_model.json",
                           plan_trial_receipt=trial / receipt["receipt_file"])
        else:
            options["elevation_artifacts"].append(path)
    converted = convert_role_artifacts(**options)
    scores = score_scoped_answer(ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/sm24_anchor.json", converted)
    write(HERE / "small_test_role_answer.json", converted)
    write(HERE / "small_test_role_score.json", scores)
    summary = {"run": output.relative_to(ROOT).as_posix(), "wall_seconds": result["wall_seconds"],
        "accounting": result["accounting"], "actual_http_requests": result["actual_http_requests"],
        "agent_unchanged": result["agent_unchanged"], "tasks": result["results"],
        "assigned_role_score": scores["assigned_role_score"], "coverage": scores["coverage"],
        "whole_building_runs": 0, "paratera_requests": 0, "deepseek_requests": 0}
    write(HERE / "small_test_summary.json", summary)
    print(json.dumps({"requests": result["accounting"]["requests"], "wall_seconds": result["wall_seconds"],
        "scores": [{"question": row["question"], "status": row["status"]}
                   for row in scores["assigned_role_score"]["questions"]]}, ensure_ascii=False), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUTPUT_ROOT / "small_test_d1b")
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("output must remain in the D1b local evidence directory")
    if args.evaluate_only:
        evaluate(output)
    elif args.credentials_file is None:
        parser.error("--credentials-file must explicitly name the approved file")
    else:
        asyncio.run(run(output, args.credentials_file))


if __name__ == "__main__":
    main()
