"""Plan reader alone on sm24 F1 (GLM subscription, at most 30 requests).

One reader task, no coordinator model, no elevation readers, no whole-building
run. Same task text as the D1/D1b small tests; only the request ceiling is 30.
References are read only after the reader stopped.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
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
OUTPUT_ROOT = ROOT / "AI_agent/archive/local_backup/plan_reader_probe"
ORIGINALS = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm24/images"
D1B = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1b"
REFERENCE = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/sm24_anchor.json"
AUTHORIZED_CREDENTIALS = ROOT / ".env"
EXPECTED_AGENT = "t1-20261006-d1b.2"
MAX_REQUESTS = 30
ROUTES = {role: {"provider": GLM_SUBSCRIPTION_ANTHROPIC, "model": "glm-5.3-flash",
                "reasoning_effort": "medium", "output_tokens": 32768}
          for role in ("coordinator", "plan_reader", "elevation_reader")}
TASK = {"task_id": "sm24-plan", "role_id": "plan_reader", "image": "1f_view.png", "target": "F1",
        "instructions": "Read this ground-floor plan as F1. Use metres; world origin is the southwest outer corner, "
            "+X east/right, +Y north/up. Read scale from the drawing dimensions. Infer heights only if needed and label "
            "them assumptions, as no elevation is supplied to you. Preserve physical room/wall and opening relationships. "
            "Tie each plan item to a localized original-image box. Use the isolated trial then submit_plan_reading "
            "with its successful plan_sha256 and unresolved items. Do not retype the plan in the submission or final text.",
        "budget": {"model_calls": MAX_REQUESTS, "tool_calls": 100}}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


async def run(output, credentials):
    if credentials.resolve() != AUTHORIZED_CREDENTIALS.resolve():
        raise ValueError("use the main-tree .env read-only")
    if output.exists():
        raise ValueError("output already exists; no automatic rerun")
    agent = agent_version_record(ROOT)
    if agent["version_id"] != EXPECTED_AGENT:
        raise ValueError(f"expected Agent {EXPECTED_AGENT}, found {agent['version_id']}")
    output.mkdir(parents=True)
    started = time.time()
    limits = RunLimits(model_calls=MAX_REQUESTS, tool_calls=120, tokens=3_000_000, seconds=10800,
                       max_model_retries=2, retry_backoff_seconds=1)
    run_dir, _, _ = prepare_inputs(output, images=ORIGINALS, mesh=None, building_input=None,
        scope="Plan reader probe: one single-image plan reader only. No coordinator model or whole-building generation.",
        image_kind="drawings", max_candidates=24, floor_plan_images=["1f_view.png"],
        started_epoch=started, seconds=limits.seconds)
    write(output / "probe_manifest.json", {"schema_version": "plan-reader-probe-v1", "task": TASK,
        "roles": ROUTES, "limits": limits.model_dump(mode="json"), "max_actual_requests": MAX_REQUESTS,
        "coordinator_model_requests": 0, "agent": agent,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "credentials_policy": "main-tree .env read-only; no content copied",
        "reference_policy": "assessment only, never reader input", "guidance": guidance_catalog()})
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        base, key = subscription_credentials(credentials, provider=GLM_SUBSCRIPTION_ANTHROPIC)
        actual_requests = 0

        class GuardedAdapter(HttpAnthropicAdapter):
            async def send(self, request, *, timeout):
                nonlocal actual_requests
                if actual_requests >= MAX_REQUESTS:
                    raise ValueError("approved request ceiling reached before HTTP")
                actual_requests += 1
                write(output / "http_boundary.json", {"attempted_http_requests": actual_requests,
                    "maximum": MAX_REQUESTS, "provider": GLM_SUBSCRIPTION_ANTHROPIC, "whole_building_runs": 0})
                print(f"GLM subscription request {actual_requests}/{MAX_REQUESTS}", flush=True)
                return await super().send(request, timeout=timeout)

        def factory(task_id, configuration, child):
            if (task_id != TASK["task_id"] or configuration["provider"] != GLM_SUBSCRIPTION_ANTHROPIC
                    or configuration["model"] != "glm-5.3-flash"):
                raise ValueError("only the approved GLM subscription plan reader may request")
            return GuardedAdapter(base_url=base, api_key=key)

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(frozen_bim_client(run_dir, repository_root=ROOT))
            frozen = FrozenBimTools(client, coordinator_role(limits.ledger_limit()), run_directory=run_dir)
            session = RoleSession(store=store, frozen=frozen, routes=load_roles(ROUTES),
                adapter_factory=factory, limits=limits, root=ROOT, max_concurrent_readers=1, started_epoch=started)
            outcomes = await session.delegate_many([TASK])
            accounting = role_accounting(store, session.registry)
            unchanged = agent_version_record(ROOT) == agent
            write(output / "probe_result.json", {"wall_seconds": time.time() - started,
                "results": outcomes["results"], "accounting": accounting, "actual_http_requests": actual_requests,
                "agent_unchanged": unchanged, "whole_building_runs": 0, "paratera_requests": 0, "deepseek_requests": 0})
            store.write_json("role_state.json", session.state())
            if not unchanged:
                raise ValueError("Agent changed during the probe; evidence invalid")
    from src.agent.runtime_behaviour import write_behaviour_report
    write_behaviour_report(output / "events.jsonl", output / "behaviour")
    return evaluate(output)


def _last_passed_trial(output):
    """Diagnosis only when nothing was submitted: newest passed isolated trial."""
    best = None
    for path in sorted(output.rglob("trial_*.json")):
        receipt = json.loads(path.read_bytes())
        if receipt.get("status") != "passed" or not receipt.get("receipt_file"):
            continue
        workspace = next((parent for parent in path.parents
                          if (parent / receipt["receipt_file"]).resolve() == path.resolve()), None)
        if workspace is not None:
            best = (path, workspace, receipt)
    return best


def evaluate(output):
    sys.path.insert(0, str(D1B))
    from scoring_bridge import convert_role_artifacts, score_scoped_answer

    result = json.loads((output / "probe_result.json").read_bytes())
    record = result["results"][0]
    options = {"case": "sm24_anchor", "assigned_plan_floors": ["F1"], "assigned_elevation_facades": []}
    scored_input = None
    if record.get("artifact"):
        path = output / record["artifact"]["path"]
        receipt = record["validation"]
        trial = path.parent / "bim/trial_workspace"
        options.update(plan_artifact=path, plan_trial_source=trial / receipt["candidate"] / "source_model.json",
                       plan_trial_receipt=trial / receipt["receipt_file"])
        scored_input = "submitted_artifact"
    else:
        found = _last_passed_trial(output)
        if found is not None:
            path, workspace, receipt = found
            options.update(plan_trial_source=workspace / receipt["candidate"] / "source_model.json",
                           plan_trial_receipt=path)
            scored_input = "last_passed_trial_not_delivered"
    scores = None
    if scored_input is not None:
        converted = convert_role_artifacts(**options)
        scores = score_scoped_answer(REFERENCE, converted)
        write(HERE / "probe_role_score.json", scores)
    floor = (scores["assigned_role_score"]["questions"][0]["raw"]["floors"][0]
             if scores and scores["assigned_role_score"]["questions"] else None)
    substance = None
    if floor is not None:
        rooms = floor["rooms"]
        openings = floor["openings"]
        substance = {
            "rooms_reference": rooms.get("reference_count"), "rooms_answer": rooms.get("candidate_count"),
            "rooms_matched": rooms.get("matched_count"),
            "room_iou_min": min((m["iou"] for m in rooms.get("matches", [])), default=None),
            "room_boundary_hausdorff_max_m": max((m["boundary_hausdorff_m"] for m in rooms.get("matches", [])), default=None),
            "openings_reference": openings.get("reference_count"), "openings_matched": openings.get("matched"),
            "opening_positions_within_tolerance": openings.get("positions"),
            "opening_endpoint_error_max_m": max((row["max_endpoint_error_m"] for row in openings.get("comparisons", [])), default=None),
            "partition_tolerance_m": floor["partitions"].get("tolerance_m"),
            "partition_missing_length_m": floor["partitions"].get("missing_length_m"),
            "partition_extra_length_m": floor["partitions"].get("extra_length_m"),
        }
    summary = {"run": output.relative_to(ROOT).as_posix(), "wall_seconds": result["wall_seconds"],
        "actual_http_requests": result["actual_http_requests"], "accounting": result["accounting"],
        "agent_unchanged": result["agent_unchanged"], "task": {k: record.get(k) for k in ("task_id", "status", "reason")},
        "scored_input": scored_input,
        "strict": None if floor is None else {k: floor[k]["status"] for k in ("exterior", "partitions", "rooms", "openings")},
        "substance": substance, "whole_building_runs": 0, "paratera_requests": 0, "deepseek_requests": 0}
    write(HERE / "probe_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("actual_http_requests", "wall_seconds", "task", "scored_input", "strict", "substance")},
                     ensure_ascii=False), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("output must stay under the probe's local evidence directory")
    if args.evaluate_only:
        evaluate(output)
    elif args.credentials_file is None:
        parser.error("--credentials-file must explicitly name the main-tree .env")
    else:
        asyncio.run(run(output, args.credentials_file))


if __name__ == "__main__":
    main()
