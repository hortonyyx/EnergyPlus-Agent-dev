"""The approved three-reader GLM subscription test; never a whole-building run.

Run from the worktree with an explicit credentials file. The evaluator alone
loads references, after the readers stop. Existing output cannot start a second
batch. No Paratera, DeepSeek, coordinator model or provider fallback is present.
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
from src.agent_runtime.anthropic import HttpAnthropicAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.providers import GLM_SUBSCRIPTION_ANTHROPIC, subscription_credentials
from src.agent_runtime.store import EventStore


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
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
         "Return the existing build_plan_bim plan with each item tied to a localized original-image box. "
         "Use the isolated trial before final JSON. If trial cannot pass, retain the draft and explain the specific failure.",
     "budget": {"model_calls": 24, "tool_calls": 80}},
    {"task_id": "sm24-north", "role_id": "elevation_reader", "image": "North_view.png", "target": "North/F1",
     "instructions": "Read the North facade from outside looking South, one storey F1. World origin is the southwest "
         "outer corner, +X east, +Y north. Image left-to-right decreases world X. Calibrate from printed dimensions. "
         "Use facade ground line Z=0, not an assumed finished-floor origin. Report every window and door with width, "
         "absolute sill/head, level marks and actual original-image evidence. Return one flat elevation artifact JSON.",
     "budget": {"model_calls": 8, "tool_calls": 30}},
    {"task_id": "sm24-east", "role_id": "elevation_reader", "image": "East_view.png", "target": "East/F1",
     "instructions": "Read the East facade from outside looking West, one storey F1. World origin is the southwest "
         "outer corner, +X east, +Y north. Image left-to-right increases world Y. Calibrate from printed dimensions. "
         "Use facade ground line Z=0, not an assumed finished-floor origin. Report every window and door with width, "
         "absolute sill/head, level marks and actual original-image evidence. Return one flat elevation artifact JSON.",
     "budget": {"model_calls": 8, "tool_calls": 30}},
]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def run(output: Path, credentials: Path):
    if credentials.resolve() != AUTHORIZED_CREDENTIALS.resolve():
        raise ValueError("this approved small test requires the explicitly authorized main-tree .env")
    if output.exists():
        raise ValueError("small-test output already exists; no second batch or automatic rerun")
    output.mkdir(parents=True)
    started = time.time()
    limits = RunLimits(model_calls=40, tool_calls=160, tokens=3_000_000, seconds=10800,
                       max_model_retries=2, retry_backoff_seconds=1)
    run_dir, _, _ = prepare_inputs(output, images=ORIGINALS, mesh=None, building_input=None,
        scope="D1 approved three single-image readers only. No coordinator model or whole-building generation.",
        image_kind="drawings", max_candidates=12, floor_plan_images=["1f_view.png"],
        started_epoch=started, seconds=limits.seconds)
    write(output / "small_test_manifest.json", {"schema_version": "d1-small-test-v1", "tasks": TASKS,
        "roles": ROUTES, "limits": limits.model_dump(mode="json"), "max_reader_tasks": 3,
        "max_actual_requests": 40, "coordinator_model_requests": 0,
        "credentials_policy": "explicit read-only authorized main-tree .env; no content copied",
        "reference_policy": "assessment only, never reader input", "guidance": guidance_catalog()})
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        # Credentials never become environment variables, task files or log fields.
        base, key = subscription_credentials(credentials, provider=GLM_SUBSCRIPTION_ANTHROPIC)
        class GuardedAdapter(HttpAnthropicAdapter):
            async def send(self, request, *, timeout):
                requests = [event for event in store.all_events if event.payload.event_type == "adapter_request"]
                if len(requests) > 40 or {event.task_id for event in requests} - {task["task_id"] for task in TASKS}:
                    raise ValueError("approved small-test request/task boundary reached before HTTP")
                return await super().send(request, timeout=timeout)

        def factory(task_id, configuration, child):
            if task_id not in {task["task_id"] for task in TASKS} or configuration["provider"] != GLM_SUBSCRIPTION_ANTHROPIC:
                raise ValueError("only the three approved GLM subscription reader tasks may request")
            return GuardedAdapter(base_url=base, api_key=key)

        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(frozen_bim_client(run_dir, repository_root=ROOT))
            frozen = FrozenBimTools(client, coordinator_role(limits.ledger_limit()), run_directory=run_dir)
            session = RoleSession(store=store, frozen=frozen, routes=load_roles(ROUTES),
                adapter_factory=factory, limits=limits, root=ROOT, max_concurrent_readers=4, started_epoch=started)
            outcomes = await session.delegate_many(TASKS)
            accounting = role_accounting(store, session.registry)
            assert accounting["requests"] <= 40
            assert accounting["by_role"]["coordinator"]["requests"] == 0
            write(output / "small_test_result.json", {"wall_seconds": time.time() - started,
                "results": outcomes["results"], "accounting": accounting,
                "whole_building_runs": 0, "paratera_requests": 0, "deepseek_requests": 0})
            store.write_json("role_state.json", session.state())
    from src.agent.runtime_behaviour import write_behaviour_report
    write_behaviour_report(output / "events.jsonl", output / "behaviour")
    return evaluate(output)


def evaluate(output):
    """References enter only this post-run evaluator, never the reader factory."""
    result = json.loads((output / "small_test_result.json").read_bytes())
    reference_path = ROOT / "AI_agent/logs/experiments/2026-09-16_sm24_developer_reconstruction/elevation_observations.json"
    references = json.loads(reference_path.read_bytes())
    assessment = {"reference": str(reference_path.relative_to(ROOT)),
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "tolerances": {"width_m": 0.05, "sill_m": 0.05, "head_m": 0.05}, "tasks": []}
    for record in result["results"]:
        row = {"task_id": record["task_id"], "role": record["role_id"], "status": record["status"]}
        if not record.get("artifact"):
            row.update(reason=record.get("reason"), assessment="no validated delivery")
        else:
            artifact = json.loads((output / record["artifact"]["path"]).read_bytes())
            if record["role_id"] == "plan_reader":
                validation = record["validation"]
                row.update(trial_passed=validation["validation_passed"], trial_reason=validation.get("reason"),
                           summary=record["summary"])
                trial = output / record["artifact"]["path"]
                trial = trial.parent / "bim/trial_workspace"
                candidate = validation.get("candidate")
                if candidate and (trial / candidate / "source_model.json").exists():
                    source = json.loads((trial / candidate / "source_model.json").read_bytes())
                    row["source_counts"] = {"spaces": len(source["spaces"]),
                        "windows": sum(o["kind"] == "window" for o in source["openings"]),
                        "doors": sum(o["kind"] == "door" for o in source["openings"])}
                    good_root = ROOT / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm24"
                    chosen = json.loads((good_root / "delivery_selection.json").read_bytes())["candidate"]
                    good = json.loads((good_root / chosen / "source_model.json").read_bytes())
                    row["known_good_counts"] = {"spaces": len(good["spaces"]),
                        "windows": sum(o["kind"] == "window" for o in good["openings"]),
                        "doors": sum(o["kind"] == "door" for o in good["openings"])}
                    from shapely.geometry import Polygon
                    from shapely.ops import unary_union
                    geometry = lambda s: [Polygon(r["polygon"]) for r in s["spaces"]]
                    actual_spaces, expected_spaces = geometry(source), geometry(good)
                    actual, expected = unary_union(actual_spaces), unary_union(expected_spaces)
                    row["footprint_iou"] = actual.intersection(expected).area / actual.union(expected).area
                    row["space_best_iou"] = [max(a.intersection(e).area / a.union(e).area for a in actual_spaces)
                                              for e in expected_spaces]
                    row["quality_boundary"] = "Best-overlap and counts are diagnostics, not one-to-one topology or user acceptance."
            else:
                expected = references["facades"][artifact["orientation"].lower()]["openings_screen_left_to_right"]
                actual = artifact["openings"]
                measures = []
                for index, reference in enumerate(expected):
                    observed = actual[index] if index < len(actual) else None
                    target_kind = "window" if reference["kind"] == "window" else "door"
                    errors = ({"width_m": abs(observed["width_m"] - reference["width_mm"] / 1000),
                               "sill_m": abs(observed["sill_m"] - reference["bottom_z_mm"] / 1000),
                               "head_m": abs(observed["head_m"] - reference["top_z_mm"] / 1000)} if observed else None)
                    measures.append({"reference_id": reference["id"], "observed_id": observed["id"] if observed else None,
                        "kind_correct": bool(observed and observed["kind"] == target_kind), "absolute_errors": errors,
                        "correct_within_5cm": bool(observed and observed["kind"] == target_kind
                                                   and all(value <= 0.05 + 1e-9 for value in errors.values()))})
                row.update(expected_openings=len(expected), observed_openings=len(actual),
                           count_correct=len(expected) == len(actual), measures=measures,
                           correct_within_5cm=sum(m["correct_within_5cm"] for m in measures))
        assessment["tasks"].append(row)
    write(output / "small_test_assessment.json", assessment)
    write(HERE / "small_test_summary.json", {"run": str(output.relative_to(ROOT)),
        "wall_seconds": result["wall_seconds"], "accounting": result["accounting"], "assessment": assessment})
    print(json.dumps({"requests": result["accounting"]["requests"], "wall_seconds": result["wall_seconds"],
                      "tasks": assessment["tasks"]}, ensure_ascii=False))
    return assessment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "small_test")
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--evaluate-only", action="store_true")
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(HERE):
        raise ValueError("small-test output must remain in this D1 experiment directory")
    if args.evaluate_only:
        evaluate(output)
    elif args.credentials_file is None:
        parser.error("--credentials-file must explicitly name the approved file")
    else:
        asyncio.run(run(output, args.credentials_file))


if __name__ == "__main__":
    main()
