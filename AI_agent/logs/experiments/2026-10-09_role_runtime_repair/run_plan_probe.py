"""One approved sm25 F1 reader, using the production role entry; no coordinator LLM.

Run only after offline checks. No saved plan or assessment reference is supplied.
The normal role protection limits remain; there is no automatic rerun or fallback.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
import jsonschema
from contextlib import AsyncExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent.runtime_entry import prepare_inputs
from src.agent.runtime_roles.accounting import role_accounting
from src.agent.runtime_roles.config import load_roles
from src.agent.runtime_roles.guidance import guidance_catalog
from src.agent.runtime_roles.session import ROLE_TASK_BUDGET, TASK_SCHEMA, RoleSession
from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client
from src.agent_runtime.agent_registry import release_records
from src.agent_runtime.anthropic import HttpAnthropicAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.providers import GLM_SUBSCRIPTION_ANTHROPIC, subscription_credentials
from src.agent_runtime.store import EventStore

ROUTES = {role: {"provider": GLM_SUBSCRIPTION_ANTHROPIC, "model": "glm-5.3-flash",
                "reasoning_effort": "medium", "output_tokens": 32000}
          for role in ("coordinator", "plan_reader", "elevation_reader")}
TASK = {"task_id": "plan_f1", "role_id": "plan_reader", "image": "1f_view.png", "target": "F1",
        "origin": "southwest outer corner of the building; metres; +X east/right, +Y north/up; F1 finished floor Z=0",
        "instructions": "Read the supplied original ground-floor plan as F1. "
            "No elevation is supplied; mark necessary unobserved heights as assumptions. "
            "Preserve the drawn walls, rooms, doors, windows and connections. Report unresolved items honestly."}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")


async def run(output, credentials, *, check_only=False):
    versions = release_records(ROOT)
    original = ROOT / "case_tests/e2e_tests/sm25-L_anchor/case_data/1f_view.png"
    image = original.read_bytes()
    limits = RunLimits(model_calls=ROLE_TASK_BUDGET["plan_reader"]["model_calls"],
        tool_calls=ROLE_TASK_BUDGET["plan_reader"]["tool_calls"], tokens=30_000_000,
        seconds=10800, max_model_retries=5, retry_backoff_seconds=4)
    config = {"schema_version": 1, "task": TASK, "roles": ROUTES, "limits": limits.model_dump(mode="json"),
        "reader_limits": ROLE_TASK_BUDGET["plan_reader"], "versions": versions,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "original_sha256": hashlib.sha256(image).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "max_concurrent_readers": 8, "active_readers": 1, "coordinator_model_requests": 0,
        "credentials_policy": "explicit main-tree .env read-only; GLM subscription only",
        "reference_policy": "one original image only; no GT, saved plan, manual calibration or previous task",
        "comparison_limit": "isolated F1; neutral task text and SW origin; not identical coordinator-generated task or full-case timing"}
    load_roles(ROUTES)
    jsonschema.validate(TASK, TASK_SCHEMA)
    if check_only:
        print(json.dumps({k: config[k] for k in ("task", "limits", "reader_limits", "original_sha256", "git_commit")}, ensure_ascii=False))
        return
    authorized = Path("C:/Users/Horton/Desktop/EnergyPlus-Agent-dev/.env")
    if credentials is None or credentials.resolve() != authorized.resolve():
        raise ValueError("credentials must explicitly name the approved main-tree .env")
    if not output.is_relative_to((ROOT / "AI_agent/archive/local_backup").resolve()):
        raise ValueError("probe output must stay in this checkout's local backup directory")
    output.mkdir(parents=True, exist_ok=False)
    input_dir = output / "original_input"
    input_dir.mkdir()
    (input_dir / TASK["image"]).write_bytes(image)
    config["guidance"] = guidance_catalog()
    write(output / "probe_manifest.json", config)
    started = time.time()
    run_dir, _, _ = prepare_inputs(output, images=input_dir, mesh=None, building_input=None,
        scope="One original-image F1 plan reader. Submit a plan reading; no whole-building delivery.",
        image_kind="drawings", max_candidates=64, floor_plan_images=[TASK["image"]],
        started_epoch=started, seconds=limits.seconds)
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        base, key = subscription_credentials(credentials, provider=GLM_SUBSCRIPTION_ANTHROPIC)
        count = 0

        class ObservedAdapter(HttpAnthropicAdapter):
            async def send(self, request, *, timeout):
                nonlocal count
                if count >= limits.model_calls:
                    raise ValueError("single-reader request protection reached before HTTP")
                count += 1
                write(output / "http_boundary.json", {"attempted_http_requests": count,
                    "provider": GLM_SUBSCRIPTION_ANTHROPIC, "model": "glm-5.3-flash"})
                print(f"GLMFlash F1 request {count}", flush=True)
                return await super().send(request, timeout=timeout)

        def factory(task_id, configuration, child):
            if task_id != TASK["task_id"] or configuration != ROUTES["plan_reader"]:
                raise ValueError("only the approved GLMFlash medium F1 reader may request")
            return ObservedAdapter(base_url=base, api_key=key)

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(frozen_bim_client(run_dir, repository_root=ROOT))
            frozen = FrozenBimTools(client, coordinator_role(limits.ledger_limit()), run_directory=run_dir)
            session = RoleSession(store=store, frozen=frozen, routes=load_roles(ROUTES),
                adapter_factory=factory, limits=limits, root=ROOT, max_concurrent_readers=8, started_epoch=started)
            outcome = await session.delegate_many([TASK])
            result = {"wall_seconds": time.time() - started, "results": outcome["results"],
                "accounting": role_accounting(store, session.registry), "actual_http_requests": count,
                "versions_unchanged": release_records(ROOT) == versions,
                "original_unchanged": original.read_bytes() == image,
                "whole_building_runs": 0, "coordinator_model_requests": 0}
            write(output / "probe_result.json", result)
            store.write_json("role_state.json", session.state())
    from scripts.dev.observe_run import observe_events
    write(output / "behavior.json", observe_events(output))
    print(json.dumps({"wall_seconds": result["wall_seconds"], "actual_http_requests": count,
        "tasks": [{k: row.get(k) for k in ("task_id", "status", "reason")} for row in result["results"]]}, ensure_ascii=False))
    if not result["versions_unchanged"] or not result["original_unchanged"]:
        raise ValueError("probe inputs or source versions changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.out.resolve(), args.credentials_file, check_only=args.check_only))
