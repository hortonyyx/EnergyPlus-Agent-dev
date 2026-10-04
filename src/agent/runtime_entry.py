"""Run one role on admitted case inputs using the frozen BIM tool service.

CLI: python -m src.agent.runtime_entry --help
Real requests require an explicit live provider. Tool preparation never starts
the historical subscription runner.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import time
from decimal import Decimal
from pathlib import Path

from PIL import Image

from scripts.tool_scripts.bim_agent_guidance import build_guide
from scripts.tool_scripts.bim_agent_inputs import freeze_building_input
from scripts.tool_scripts.bim_agent_mesh import freeze_mesh
from src.agent.runtime_tools import (
    FrozenBimTools, coordinator_role, local_observer_role, frozen_bim_client,
    write_frozen_materials, write_frozen_tool_catalog,
)
from src.agent.runtime_context import update_building_context
from src.agent.runtime_delivery import finalize_runtime_building
from src.agent_runtime.adapter import HttpChatAdapter, ScriptedAdapter
from src.agent_runtime.anthropic import HttpAnthropicAdapter
from src.agent_runtime.budget import PriceSchedule
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.estimation import get_model_profile
from src.agent_runtime.output_limits import default_output_tokens, validate_output_limit
from src.agent_runtime.providers import (GLM_SUBSCRIPTION, GLM_SUBSCRIPTION_ANTHROPIC, SUBSCRIPTION_PROVIDERS, LIVE_PROVIDERS,
    provider_parameters, subscription_credentials, validate_provider_model)
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions


ROOT = Path(__file__).resolve().parents[2]


def runtime_model_profile(provider: str, model: str):
    """Select the compatibility or reviewed profile for this CLI route."""
    validate_provider_model(provider, model)
    strict = provider in LIVE_PROVIDERS
    return get_model_profile(model if strict else "scripted-model", strict=strict)


def prepare_inputs(output: Path, *, images: Path | None, mesh: Path | None,
                   building_input: Path | None, scope: str, image_kind: str,
                   max_candidates: int, floor_plan_images: list[str] | None = None,
                   started_epoch: float | None = None,
                   seconds: float | None = None) -> tuple[Path, str, str]:
    """Freeze originals in a fresh run, using the unchanged existing input helpers."""
    run = output / "bim"
    run.mkdir(parents=True, exist_ok=False)
    (run / "images").mkdir()
    inventory = {}
    for source in sorted(images.glob("*.png")) if images else []:
        target = run / "images" / source.name
        shutil.copyfile(source, target)
        with Image.open(target) as image:
            size = list(image.size)
        inventory[source.name] = {"size": size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    if not inventory and mesh is None:
        raise ValueError("provide original PNG images or a GLB mesh")
    if floor_plan_images is not None and any(name not in inventory for name in floor_plan_images):
        raise ValueError("floor_plan_images must use admitted input filenames")
    floor_scope_source = "explicit_input_filenames" if floor_plan_images is not None else "input_filename_hint"
    if floor_plan_images is None:
        floor_plan_images = sorted(name for name in inventory
            if re.fullmatch(r"\d+f(?:_view)?\.png", name, re.I)) if image_kind == "drawings" else []
    if (started_epoch is None) != (seconds is None):
        raise ValueError("started_epoch and seconds must be supplied together")
    manifest = {"images": inventory, "image_kind": image_kind if inventory else None,
        "scope": scope, "max_candidates": max_candidates,
        "started_epoch": started_epoch, "time_budget_seconds": seconds,
        "deadline_epoch": started_epoch + seconds if started_epoch is not None else None,
        "floor_plan_images": floor_plan_images,
        "floor_scope_source": floor_scope_source if floor_plan_images else "not_declared",
        "provider": "runtime", "input_mode": "runtime_original_inputs",
        "only_input": "admitted original images/mesh, user scope and optional building brief; no GT/evaluation"}
    if mesh:
        manifest["mesh_input"] = freeze_mesh(mesh, run)
    if building_input:
        manifest["building_input"] = freeze_building_input(building_input, run, inventory)
    (run / "inputs.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    guide = build_guide(images=image_kind if inventory else None, mesh=bool(mesh))
    task = scope
    (output / "guide.txt").write_text(guide, encoding="utf-8")
    (output / "task.txt").write_text(task, encoding="utf-8")
    return run, guide, task


def paratera_credentials(path: Path | None) -> tuple[str, str]:
    """Read only the two permitted keys, without sourcing/exporting an .env file."""
    values = {}
    if path:
        from dotenv import dotenv_values
        private = dotenv_values(path, interpolate=False)
        values = {name: private.get(name) for name in ("PARATERA_BASE_URL", "PARATERA_API_KEY")}
    base_url = values.get("PARATERA_BASE_URL") or os.environ.get("PARATERA_BASE_URL", "https://llmapi.paratera.com/v1")
    key = values.get("PARATERA_API_KEY") or os.environ.get("PARATERA_API_KEY")
    if not key:
        raise ValueError("PARATERA_API_KEY was not supplied")
    return base_url, key


async def execute(args) -> dict:
    output = args.out.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("this development entry writes only inside its own worktree")
    strict_model_profile = args.provider in LIVE_PROVIDERS
    # Reject an unreviewed real route before creating a run or reading credentials.
    runtime_model_profile(args.provider, args.model)
    effective_model = args.model if strict_model_profile else "scripted-model"
    args.output_tokens = args.output_tokens if args.output_tokens is not None else default_output_tokens(effective_model)
    validate_output_limit(effective_model, args.output_tokens, reason=args.low_output_limit_reason)
    parameters = provider_parameters(args.provider, output_tokens=args.output_tokens,
        temperature=args.temperature, thinking=args.thinking, reasoning_effort=args.reasoning_effort)
    if args.provider in SUBSCRIPTION_PROVIDERS and (args.price_schedule or args.money_usd is not None):
        raise ValueError("subscription route has no usage-based money estimate; use token/time budgets")
    limits = RunLimits(model_calls=args.model_calls, tool_calls=args.tool_calls,
        seconds=args.seconds, tokens=args.tokens, money_usd=args.money_usd,
        near_limit=args.near_limit, min_output_tokens=args.min_output_tokens,
        context_tokens=args.context_tokens, max_model_retries=args.model_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        max_consecutive_truncations=args.max_consecutive_truncations,
        max_total_truncations=args.max_total_truncations,
        summary_every=args.summary_every)
    context_policy = ContextPolicy(active_window_messages=args.context_window,
        compact_at_tokens=args.compact_at_tokens,
        large_result_bytes=args.large_result_bytes, max_images=args.max_images,
        max_image_bytes=args.max_image_bytes, pinned_tags=tuple(args.pin_tag)) if args.context else None
    pricing = PriceSchedule.model_validate_json(args.price_schedule.read_bytes()) if args.price_schedule else None
    if args.repair_tail and not args.resume:
        raise ValueError("--repair-tail requires --resume")
    if args.provider == "scripted" and args.script is None:
        raise ValueError("--provider scripted requires --script")
    if args.resume:
        run = output / "bim"
        guide, task = (output / "guide.txt").read_text(), (output / "task.txt").read_text()
    else:
        output.mkdir(parents=True, exist_ok=False)
        started_epoch = time.time()
        run, guide, task = prepare_inputs(output, images=args.images, mesh=args.mesh,
            building_input=args.building_input, scope=args.scope, image_kind=args.image_kind,
            max_candidates=args.max_candidates, floor_plan_images=args.floor_plan_images,
            started_epoch=started_epoch, seconds=limits.seconds)
    manifest = json.loads((run / "inputs.json").read_bytes())
    started_epoch = manifest.get("started_epoch")
    role = (local_observer_role if args.role == "local_observer" else coordinator_role)(limits.ledger_limit())
    adapter = None
    try:
        with EventStore(output, run_id=output.name, task_id=args.role,
                budget_limit=limits.ledger_limit(), recover_tail=args.repair_tail) as store:
            async with frozen_bim_client(run_directory=run, readonly=role.read_only, repository_root=ROOT) as client:
                tools = FrozenBimTools(client, role, run_directory=run)
                catalog = await tools.list_tools()
                if not args.resume:
                    write_frozen_materials(output / "frozen", repository_root=ROOT)
                    write_frozen_tool_catalog(output / "frozen", await client.list_tools(), readonly=role.read_only)
                if args.provider == "scripted":
                    fixture = args.script.read_bytes()
                    # The local fixture gives one response per request ticket. A
                    # resumed unknown ticket consumes its position, never replays it.
                    offset = sum(e.payload.event_type == "adapter_request" for e in store.events)
                    adapter = ScriptedAdapter(json.loads(fixture)[offset:])
                    route = {"route_id": "offline-scripted", "model": "scripted-model",
                        "fixture_sha256": hashlib.sha256(fixture).hexdigest()}
                else:
                    base_url, key = (subscription_credentials(args.credentials_file, provider=args.provider)
                        if args.provider in SUBSCRIPTION_PROVIDERS else paratera_credentials(args.credentials_file))
                    adapter_type = HttpAnthropicAdapter if args.provider == GLM_SUBSCRIPTION_ANTHROPIC else HttpChatAdapter
                    adapter = adapter_type(base_url=base_url, api_key=key)
                    route = {"route_id": args.provider, "model": args.model, "base_url": base_url,
                        "billing_mode": "subscription" if args.provider in SUBSCRIPTION_PROVIDERS else "metered"}
                specs = [{"type": "function", "function": {"name": t["name"],
                    "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in catalog]
                versions = make_versions(store, root=ROOT, prompt=guide, tools=specs,
                    parameters=parameters, route=route, code_paths=("src/agent/runtime_entry.py",
                        "src/agent/runtime_delivery.py",
                        "src/agent/runtime_tools.py", "scripts/tool_scripts", "src/agent/geometry",
                        "src/agent/runtime_context.py", "src/agent/runtime_behaviour.py",
                        "src/agent/correction", "src/agent/execution"))
                # A refused resume must not replace the original run's evidence.
                # The runtime checks current versions against its saved checkpoint.
                if not args.resume:
                    store.write_json("versions.json", versions.model_dump(mode="json"))
                originals, user_content = {}, [{"type": "text", "text": task}]
                # Keep admitted user declarations in the initial requirement
                # record, so a later activity window cannot discard constraints
                # that were otherwise visible only in the inputs tool reply.
                admitted = json.loads((run / "inputs.json").read_bytes()).get("building_input")
                if admitted:
                    user_content.append({"type": "text", "text":
                        "Additional user-supplied building declaration; not independently verified: "
                        + json.dumps({key: admitted[key] for key in ("raw_sha256", "declaration",
                            "field_semantics", "conflict_policy")}, ensure_ascii=False)})
                for name in args.attach_image:
                    if Path(name).name != name:
                        raise ValueError("--attach-image needs an admitted filename")
                    image_path = run / "images" / name
                    raw = image_path.read_bytes()
                    ref = store.put_bytes(raw, "image/png")
                    originals[ref.sha256] = ref
                    user_content += [{"type": "text", "text": f"Input image: {name}"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode()}}]
                messages = [{"role": "system", "content": guide},
                    {"role": "user", "content": user_content if len(user_content) > 1 else task}]
                engine = Runtime(store=store, adapter=adapter, tools=tools, role=role,
                    model=route["model"], parameters=parameters, versions=versions, limits=limits,
                    context_policy=context_policy, pricing=pricing,
                    context_update=update_building_context,
                    required_view_ids=tuple(args.keep_view_id),
                    retrieve_images=tuple(tuple(pair) for pair in args.retrieve_image),
                    start_epoch=started_epoch,
                    finalize_run=finalize_runtime_building,
                    strict_model_profile=strict_model_profile)
                engine.low_output_limit_reason = args.low_output_limit_reason
                result = await engine.run(messages, image_originals=originals, resume=args.resume)
        from src.agent.runtime_behaviour import write_behaviour_report
        write_behaviour_report(output / "events.jsonl", output / "behaviour")
        return result
    finally:
        if isinstance(adapter, HttpChatAdapter):
            await adapter.close()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--images", type=Path)
    p.add_argument("--floor-plan-image", dest="floor_plan_images", action="append",
                   help="Explicit expected floor-plan filename; repeat for all floors (same as Claude Code)")
    p.add_argument("--mesh", type=Path)
    p.add_argument("--building-input", type=Path)
    p.add_argument("--image-kind", choices=("drawings", "mesh_views", "photos", "unknown"), default="drawings")
    p.add_argument("--scope", default="Build the supplied building at the requested detail; inspect saved results and report limitations.")
    p.add_argument("--role", choices=("coordinator", "local_observer"), default="coordinator")
    p.add_argument("--provider", choices=("scripted", *LIVE_PROVIDERS), required=True)
    p.add_argument("--script", type=Path, help="explicit offline Chat Completions response fixture")
    p.add_argument("--model", default="Qwen3.8-27B")
    p.add_argument("--credentials-file", type=Path, help="read only this provider credentials file; required for GLM subscription")
    p.add_argument("--model-calls", type=int, default=6)
    p.add_argument("--tool-calls", type=int, default=12)
    p.add_argument("--seconds", type=float, default=180.0)
    p.add_argument("--tokens", type=int, default=5_000_000)
    p.add_argument("--money-usd", type=Decimal, help="total estimate ceiling; needs a sourced price schedule")
    p.add_argument("--price-schedule", type=Path, help="PriceSchedule JSON; estimates are not provider bills")
    p.add_argument("--near-limit", choices=("stop", "reduce_output"), default="stop")
    p.add_argument("--min-output-tokens", type=int, default=1)
    p.add_argument("--model-retries", type=int, default=2)
    p.add_argument("--retry-backoff-seconds", type=float, default=1.0)
    p.add_argument("--max-consecutive-truncations", type=int, default=2,
                   help="maximum consecutive output-limit recoveries; zero disables recovery")
    p.add_argument("--max-total-truncations", type=int, default=3,
                   help="maximum output-limit recoveries across this root run, including children and summaries")
    p.add_argument("--context", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--context-tokens", type=int, help="optional local context ceiling; the runtime also enforces the model profile limit and uses the smaller value")
    p.add_argument("--context-window", type=int, help="explicit legacy message-window replay; production defaults to token compaction")
    p.add_argument("--compact-at-tokens", type=int, default=150_000,
                   help="compact only when estimated input tokens reach this threshold")
    p.add_argument("--large-result-bytes", type=int, default=8192)
    p.add_argument("--max-images", type=int, help="optional image count target at compaction; unset by default")
    p.add_argument("--max-image-bytes", type=int, default=32_000_000)
    p.add_argument("--pin-tag", action="append", default=[])
    p.add_argument("--keep-view-id", action="append", default=[])
    p.add_argument("--retrieve-image", nargs=2, action="append", default=[], metavar=("VIEW_ID", "SHA256"))
    p.add_argument("--summary-every", type=int, default=0, help="optional constrained model summary after N tool calls; shares the root budget")
    p.add_argument("--output-tokens", type=int, help="defaults to the reviewed model recommendation")
    p.add_argument("--low-output-limit-reason", help="explicit reason for an output cap below the recommendation")
    p.add_argument("--temperature", type=float, help="default: Paratera 0.0; subscription service default")
    p.add_argument("--thinking", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--reasoning-effort", choices=("low", "medium", "high", "max"),
                   help="provider-native reasoning level; when set, omit enable_thinking")
    p.add_argument("--max-candidates", type=int, default=4)
    p.add_argument("--attach-image", action="append", default=[])
    p.add_argument("--resume", action="store_true")
    p.add_argument("--repair-tail", action="store_true", help="explicitly preserve and repair a torn final event during resume")
    return p


def main():
    args = parser().parse_args()
    result = asyncio.run(execute(args))
    print(json.dumps({key: result[key] for key in ("status", "model_calls", "tool_calls", "reported_tokens", "billing_usd")}, ensure_ascii=False))
    raise SystemExit(0 if result["status"] in {"completed", "model_budget_exhausted", "tool_budget_exhausted", "time_budget_exhausted", "token_budget_exhausted", "money_budget_exhausted", "model_profile_context_limit_exhausted", "configured_context_limit_exhausted"} else 1)


if __name__ == "__main__":
    main()
