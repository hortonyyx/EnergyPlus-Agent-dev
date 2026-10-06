"""Opt-in drawing role runtime, preserving the single-model entrypoint."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from contextlib import AsyncExitStack

from src.agent.runtime_entry import ROOT, parser as single_parser, prepare_inputs, paratera_credentials, publish_tool_budget
from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client, write_frozen_materials, write_frozen_tool_catalog
from src.agent_runtime.adapter import HttpChatAdapter, ScriptedAdapter
from src.agent_runtime.anthropic import HttpAnthropicAdapter
from .context_policy import role_context_policy
from src.agent_runtime.loop import Runtime, RunLimits
from src.agent_runtime.providers import GLM_SUBSCRIPTION_ANTHROPIC, SUBSCRIPTION_PROVIDERS, LIVE_PROVIDERS, subscription_credentials
from src.agent_runtime.run_paths import resolve_run_output
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions
from src.harness_contracts.roles import ToolGrant

from .accounting import role_accounting
from .assembly_review import finalize_role_building
from .config import load_roles
from .guidance import get_role_guide
from .session import RoleSession, update_role_context, role_parameters


def parser():
    result = single_parser()
    result.description = __doc__
    result.add_argument("--roles-json", required=True, help="explicit JSON object with all three role routes")
    result.add_argument("--max-concurrent-readers", type=int, default=8)
    return result


async def execute(args, *, adapter_factory=None, fault_hook=None, reader_fault_hook=None):
    if args.mesh or args.image_kind != "drawings":
        raise ValueError("role_division v1 accepts drawing images only")
    routes = load_roles(json.loads(args.roles_json), allow_scripted=args.provider == "scripted" and args.script is not None)
    primary = routes["coordinator"].model_dump(mode="json")
    if (args.provider, args.model) != (primary["provider"], primary["model"]):
        raise ValueError("coordinator route must match the explicit case route")
    if args.money_usd is not None or args.price_schedule:
        raise ValueError("role_division uses the shared route-aware CNY ledger; per-run USD price overrides are not supported")
    if args.money_cny is not None and any(role.provider in SUBSCRIPTION_PROVIDERS for role in routes.values()):
        raise ValueError("subscription roles cannot participate in a usage-priced money ceiling")
    limits = RunLimits(model_calls=args.model_calls, tool_calls=args.tool_calls, seconds=args.seconds,
        tokens=args.tokens, money_cny=args.money_cny, near_limit=args.near_limit,
        min_output_tokens=args.min_output_tokens, context_tokens=args.context_tokens,
        max_model_retries=args.model_retries, retry_backoff_seconds=args.retry_backoff_seconds,
        max_consecutive_truncations=args.max_consecutive_truncations, max_total_truncations=args.max_total_truncations,
        summary_every=args.summary_every)
    output = resolve_run_output(args.out, repository_root=ROOT, run_root=args.run_root)
    if args.repair_tail and not args.resume:
        raise ValueError("--repair-tail requires --resume")
    if args.provider == "scripted" and args.script is None:
        raise ValueError("scripted role runs require an explicit response fixture")
    guide = get_role_guide("coordinator")
    configuration = {"roles": {key: role.model_dump(mode="json") for key, role in routes.items()},
                     "max_concurrent_readers": args.max_concurrent_readers}
    if args.resume:
        if json.loads((output / "role_configuration.json").read_bytes()) != configuration:
            raise ValueError("role configuration changed on resume")
        if (output / "guide.txt").read_text(encoding="utf-8") != guide:
            raise ValueError("coordinator guidance changed on resume")
        run, task = output / "bim", (output / "task.txt").read_text(encoding="utf-8")
    else:
        output.mkdir(parents=True, exist_ok=False)
        run, _, task = prepare_inputs(output, images=args.images, mesh=None, building_input=args.building_input,
            scope=args.scope, image_kind="drawings", max_candidates=args.max_candidates,
            floor_plan_images=args.floor_plan_images, started_epoch=time.time(), seconds=limits.seconds)
        (output / "guide.txt").write_text(guide, encoding="utf-8", newline="\n")
    manifest = json.loads((run / "inputs.json").read_bytes())
    parameters = role_parameters(primary)
    scripted = json.loads(args.script.read_bytes()) if args.script else None
    if scripted is not None and not isinstance(scripted, dict):
        raise ValueError("role fixture needs coordinator and tasks response lists")

    def factory(task_id, config, store):
        if adapter_factory is not None:
            return adapter_factory(task_id, config, store)
        if config["provider"] == "scripted":
            responses = scripted["coordinator"] if task_id == "coordinator" else scripted["tasks"][task_id]
            offset = sum(event.payload.event_type == "adapter_request" for event in store.events)
            return ScriptedAdapter(responses[offset:])
        credentials = args.credentials_file
        base, key = (subscription_credentials(credentials, provider=config["provider"])
                     if config["provider"] in SUBSCRIPTION_PROVIDERS else paratera_credentials(credentials))
        cls = HttpAnthropicAdapter if config["provider"] == GLM_SUBSCRIPTION_ANTHROPIC else HttpChatAdapter
        return cls(base_url=base, api_key=key)

    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit(),
                    recover_tail=args.repair_tail) as store:
        if not args.resume:
            store.write_json("role_configuration.json", configuration)
        async with AsyncExitStack() as stack:
            client = await stack.enter_async_context(frozen_bim_client(run_directory=run, repository_root=ROOT))
            base_role = coordinator_role(limits.ledger_limit())
            frozen = FrozenBimTools(client, base_role, run_directory=run)
            tools = RoleSession(store=store, frozen=frozen, routes=routes, adapter_factory=factory,
                limits=limits, root=ROOT, max_concurrent_readers=args.max_concurrent_readers,
                started_epoch=manifest["started_epoch"], reader_fault_hook=reader_fault_hook)
            catalog = await tools.list_tools()
            specs = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                       "parameters": t["inputSchema"]}} for t in catalog]
            role = base_role.model_copy(update={"tool_whitelist": tuple(
                ToolGrant(tool_name=tool["name"], access="read" if tools.repeatability(tool["name"]) == "read_only" else "write")
                for tool in catalog)})
            route = {"route_id": primary["provider"], "model": primary["model"], "roles": configuration}
            if args.script:
                route["fixture_sha256"] = hashlib.sha256(args.script.read_bytes()).hexdigest()
            versions = make_versions(store, root=ROOT, prompt=guide, tools=specs, parameters=parameters,
                route=route, code_paths=("src/agent/runtime_roles", "src/agent/runtime_tools.py", "src/agent/runtime_context.py",
                                        "src/agent/runtime_delivery.py", "src/agent/bim_inputs.py", "scripts/tool_scripts", "src/agent/geometry"))
            if args.resume:
                saved = store.latest_checkpoint()
                if saved and saved[1]["versions"] != versions.model_dump(mode="json"):
                    raise ValueError("runtime implementation or roles changed; refusing recovery before any work")
            else:
                store.write_json("versions.json", versions.model_dump(mode="json"))
                write_frozen_materials(output / "frozen", repository_root=ROOT)
                write_frozen_tool_catalog(output / "frozen", await client.list_tools(), readonly=False)
            adapter = factory("coordinator", primary, store)
            if hasattr(adapter, "close"):
                stack.push_async_callback(adapter.close)
            engine = Runtime(store=store, adapter=adapter, tools=tools, role=role, model=primary["model"],
                parameters=parameters, versions=versions, limits=limits,
                context_policy=role_context_policy("coordinator", compact_at_tokens=args.compact_at_tokens,
                    active_window_messages=args.context_window, large_result_bytes=args.large_result_bytes,
                    max_images=args.max_images, max_image_bytes=args.max_image_bytes),
                context_update=update_role_context, root_tool_calls=limits.tool_calls,
                start_epoch=manifest["started_epoch"], finalize_run=finalize_role_building,
                tool_budget_update=publish_tool_budget, strict_model_profile=primary["provider"] in LIVE_PROVIDERS,
                low_output_limit_reason=primary.get("low_output_limit_reason"), fault_hook=fault_hook)
            if args.resume:
                saved = store.latest_checkpoint()
                if saved and saved[1].get("config", engine._config()) != engine._config():
                    raise ValueError("runtime configuration changed; refusing recovery before any work")
                await tools.recover_pending()
            content = task
            if manifest.get("building_input"):
                content += "\nUser-supplied declaration: " + json.dumps(manifest["building_input"], ensure_ascii=False)
            result = await engine.run([{"role": "system", "content": guide}, {"role": "user", "content": content}], resume=args.resume)
            accounting = role_accounting(store, tools.registry)
            store.write_json("role_accounting.json", accounting)
            store.write_json("role_state.json", tools.state())
            result["role_accounting"] = accounting
            store.write_json("receipt.json", result)
            from src.agent.bim_inputs import dump
            delivery = result.get("finalization", {}).get("delivery")
            dump(run / "summary.json", {
                "input_mode": manifest.get("input_mode"), "source_input_mode": manifest.get("source_input_mode"),
                "input_contents": manifest.get("input_contents"),
                "agent_response_completed": result["status"] == "completed", "runtime_status": result["status"],
                "elapsed_seconds": result.get("elapsed_seconds"),
                "delivery": ({**delivery, "report": "delivery.json", "viewer": "delivery.html"} if delivery else None),
                "receipt": "../receipt.json", "drawing_fidelity": "not_evaluated", "runtime_mode": "role_division"})
    from src.agent.runtime_behaviour import write_behaviour_report
    write_behaviour_report(output / "events.jsonl", output / "behaviour")
    return result


def main():
    args = parser().parse_args()
    result = asyncio.run(execute(args))
    print(json.dumps({"status": result["status"], "usage": result["role_accounting"]}, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
