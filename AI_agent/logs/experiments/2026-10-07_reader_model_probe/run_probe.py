"""Readers only, on one model route: sm24 plan F1 and the four facades, no coordinator model.

Step 6 of the role-division plan ("swap models role by role") starts with a profile of a
candidate model in the two reader roles. Same images and targets as the D1b small tests;
role allowances are the runtime defaults (plan 40 requests, facade 16). A request guard
stops new requests once the run's estimated Paratera cost reaches --cap-cny. References
are read only after the readers stopped (evaluate()).

Usage: python run_probe.py --model Qwen3.8-27B --name qwen27b_r1 --credentials-file <main-tree .env>
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from contextlib import AsyncExitStack
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1b"))

from src.agent.runtime_entry import paratera_credentials, prepare_inputs  # noqa: E402
from src.agent.runtime_roles.accounting import role_accounting  # noqa: E402
from src.agent.runtime_roles.config import load_roles  # noqa: E402
from src.agent.runtime_roles.guidance import guidance_catalog  # noqa: E402
from src.agent.runtime_roles.session import RoleSession  # noqa: E402
from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client  # noqa: E402
from src.agent_runtime.adapter import HttpChatAdapter  # noqa: E402
from src.agent_runtime.agent_registry import agent_version_record  # noqa: E402
from src.agent_runtime.loop import RunLimits  # noqa: E402
from src.agent_runtime.store import EventStore  # noqa: E402

OUTPUT_ROOT = ROOT / "AI_agent/archive/local_backup/reader_model_probe"
ORIGINALS = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm24/images"
AUTHORIZED_CREDENTIALS = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\.env")  # main tree, read-only
REFERENCE = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/sm24_anchor.json"
FACADE_DIRECTION = {"North": "decreases world X", "South": "increases world X",
                    "East": "increases world Y", "West": "decreases world Y"}
LOOKING = {"North": "South", "South": "North", "East": "West", "West": "East"}
PLAN_TASK = {"task_id": "sm24-plan", "role_id": "plan_reader", "image": "1f_view.png", "target": "F1",
    "instructions": "Read this ground-floor plan as F1. World origin is the southwest outer corner. Read scale "
        "from the drawing dimensions. Infer heights only if needed and label them assumptions, as no elevation "
        "is supplied to you. Preserve physical room/wall and opening relationships. Tie each plan item to a "
        "localized original-image box. Use the isolated trial then submit_plan_reading with its successful "
        "plan_sha256 and unresolved items.",
    "origin": "southwest outer corner of the building"}


def facade_task(facade):
    return {"task_id": f"sm24-{facade.lower()}", "role_id": "elevation_reader", "image": f"{facade}_view.png",
        "target": f"{facade}/F1", "origin": "southwest outer corner of the building",
        "instructions": f"Read the {facade} facade from outside looking {LOOKING[facade]}, one storey F1. "
            f"Image left-to-right {FACADE_DIRECTION[facade]}. Calibrate from printed dimensions. Use facade "
            "ground line Z=0. Report every window and door with width, absolute sill/head, level marks and "
            "actual original-image evidence. Call submit_elevation_reading to deliver."}


TASKS = [PLAN_TASK, *(facade_task(f) for f in ("North", "South", "East", "West"))]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
                    encoding="utf-8", newline="\n")


def routes_for(model, output_tokens, temperature):
    reader = {"provider": "paratera", "model": model, "reasoning_effort": None,
              "output_tokens": output_tokens, "temperature": temperature, "enable_thinking": True}
    return {"coordinator": reader, "plan_reader": reader, "elevation_reader": reader}


async def run(output, credentials, *, model, cap_cny, output_tokens, temperature):
    if credentials.resolve() != AUTHORIZED_CREDENTIALS.resolve():
        raise ValueError("use the main-tree .env read-only")
    if output.exists():
        raise ValueError("output already exists; no automatic rerun")
    agent = agent_version_record(ROOT)
    routes = routes_for(model, output_tokens, temperature)
    output.mkdir(parents=True)
    started = time.time()
    limits = RunLimits(model_calls=40 + 4 * 16, tool_calls=400, tokens=12_000_000, seconds=5400,
                       max_model_retries=2, retry_backoff_seconds=2)
    run_dir, _, _ = prepare_inputs(output, images=ORIGINALS, mesh=None, building_input=None,
        scope="Reader model probe: single-image plan and facade readers only. "
              "No coordinator model or whole-building generation.",
        image_kind="drawings", max_candidates=24, floor_plan_images=["1f_view.png"],
        started_epoch=started, seconds=limits.seconds)
    write(output / "probe_manifest.json", {"schema_version": "reader-model-probe-v1", "tasks": TASKS,
        "roles": routes, "limits": limits.model_dump(mode="json"), "cap_cny": str(cap_cny),
        "coordinator_model_requests": 0, "agent": agent,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "credentials_policy": "main-tree .env read-only; only PARATERA_BASE_URL/API_KEY read",
        "reference_policy": "assessment only, never reader input", "guidance": guidance_catalog()})
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        base, key = paratera_credentials(credentials)
        state = {"requests": 0, "session": None}

        class GuardedAdapter(HttpChatAdapter):
            async def send(self, request, *, timeout):
                session = state["session"]
                if session is not None:
                    spent = role_accounting(store, session.registry).get("estimated_cost_cny")
                    if spent is not None and Decimal(str(spent)) >= cap_cny:
                        raise ValueError(f"probe cost cap {cap_cny} CNY reached before HTTP (estimated {spent})")
                state["requests"] += 1
                return await super().send(request, timeout=timeout)

        def factory(task_id, configuration, child):
            if task_id not in {task["task_id"] for task in TASKS} or configuration["provider"] != "paratera":
                raise ValueError("only the Paratera readers of this probe may request")
            return GuardedAdapter(base_url=base, api_key=key)

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(frozen_bim_client(run_dir, repository_root=ROOT))
            frozen = FrozenBimTools(client, coordinator_role(limits.ledger_limit()), run_directory=run_dir)
            session = RoleSession(store=store, frozen=frozen, routes=load_roles(routes),
                adapter_factory=factory, limits=limits, root=ROOT, max_concurrent_readers=8,
                started_epoch=started)
            state["session"] = session
            outcomes = await session.delegate_many(TASKS)
            accounting = role_accounting(store, session.registry)
            write(output / "probe_result.json", {"wall_seconds": time.time() - started,
                "results": outcomes["results"], "accounting": accounting, "http_requests": state["requests"],
                "agent_unchanged": agent_version_record(ROOT) == agent})
            store.write_json("role_state.json", session.state())
    from src.agent.runtime_behaviour import write_behaviour_report
    write_behaviour_report(output / "events.jsonl", output / "behaviour")
    return evaluate(output)


def evaluate(output):
    # Assessment dependencies and reference data are never passed to a reader.
    from scoring_bridge import convert_role_artifacts, score_scoped_answer
    result = json.loads((output / "probe_result.json").read_bytes())
    delivered = [r for r in result["results"] if r.get("artifact")]
    options = {"case": "sm24_anchor", "assigned_plan_floors": [], "assigned_elevation_facades": [],
               "elevation_artifacts": []}
    for record in delivered:
        path = output / record["artifact"]["path"]
        if record["role_id"] == "plan_reader":
            receipt = record["validation"]
            trial = path.parent / "bim/trial_workspace"
            options["assigned_plan_floors"] = ["F1"]
            options.update(plan_artifact=path, plan_trial_source=trial / receipt["candidate"] / "source_model.json",
                           plan_trial_receipt=trial / receipt["receipt_file"])
        else:
            options["elevation_artifacts"].append(path)
            options["assigned_elevation_facades"].append(record["target"].split("/")[0])
    scores = None
    if delivered:
        converted = convert_role_artifacts(**options)
        scores = score_scoped_answer(REFERENCE, converted)
        write(HERE / f"{output.name}_role_answer.json", converted)
        write(HERE / f"{output.name}_role_score.json", scores)
    accounting = result["accounting"]
    by_task = {task: {k: row.get(k) for k in ("requests", "provider_reported_tokens",
                                                "reported_cache_read_tokens", "estimated_cost_cny")}
               for task, row in accounting.get("by_task", {}).items()}
    summary = {"run": output.relative_to(ROOT).as_posix(), "wall_seconds": result["wall_seconds"],
        "http_requests": result["http_requests"], "agent_unchanged": result["agent_unchanged"],
        "requests": accounting.get("requests"), "provider_reported_tokens": accounting.get("provider_reported_tokens"),
        "estimated_cost_cny": accounting.get("estimated_cost_cny"), "by_task": by_task,
        "tasks": [{k: r.get(k) for k in ("task_id", "status", "reason")} for r in result["results"]],
        "scores": scores and [{"question": q["question"], "status": q["status"]}
                              for q in scores["assigned_role_score"]["questions"]]}
    write(HERE / f"{output.name}_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, default=str)[:3000], flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--cap-cny", type=Decimal, default=Decimal("8"))
    parser.add_argument("--output-tokens", type=int, default=16384)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args()
    output = (OUTPUT_ROOT / args.name).resolve()
    if args.evaluate_only:
        evaluate(output)
    elif args.credentials_file is None:
        parser.error("--credentials-file must explicitly name the authorized file")
    else:
        asyncio.run(run(output, args.credentials_file, model=args.model, cap_cny=args.cap_cny,
                        output_tokens=args.output_tokens, temperature=args.temperature))


if __name__ == "__main__":
    main()
