"""Manual coordinator wrapper for the second sm25 run.

This wrapper never starts a coordinator model.  It initializes one independent
runtime run, delegates explicitly supplied reader tasks through RoleSession, and
lets the root dev model invoke deterministic coordinator tools.  It has no
provider or model fallback and rejects DeepSeek/Claude routes.

Preparation-only validation (zero model requests):
  python manual_dispatch.py validate --config tier4_candidate.json

After the first GPT-6 Sol run is complete:
  python manual_dispatch.py init --config tier4_candidate.json --after-first-run-complete
  python manual_dispatch.py delegate --config tier4_candidate.json --tasks tasks.json
  python manual_dispatch.py tool --config tier4_candidate.json --name role_state --arguments empty.json
  python manual_dispatch.py tool --config tier4_candidate.json --name read_role_artifact --arguments read.json
  python manual_dispatch.py tool --config tier4_candidate.json --name assemble_from_readers --arguments assemble.json
  python manual_dispatch.py status --config tier4_candidate.json

Task and tool argument files are authored by the root dev model at execution
time.  This file deliberately contains no sm25 answers, counts, dimensions,
calibrations, prior geometry, or GT-derived task text.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from src.agent.runtime_entry import paratera_credentials, prepare_inputs  # noqa: E402
from src.agent.runtime_roles.accounting import role_accounting  # noqa: E402
from src.agent.runtime_roles.artifacts import ArtifactRegistry  # noqa: E402
from src.agent.runtime_roles.config import load_roles  # noqa: E402
from src.agent.runtime_roles.guidance import guidance_catalog  # noqa: E402
from src.agent.runtime_roles.session import RoleSession  # noqa: E402
from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client  # noqa: E402
from src.agent.runtime_behaviour import write_behaviour_report  # noqa: E402
from src.agent_runtime.accounting import require_cny_price_schedule  # noqa: E402
from src.agent_runtime.adapter import HttpChatAdapter  # noqa: E402
from src.agent_runtime.agent_registry import agent_version_record  # noqa: E402
from src.agent_runtime.loop import RunLimits  # noqa: E402
from src.agent_runtime.store import EventStore  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_inside_root(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"path escapes repository root: {value}")
    return path


def limits_from(config: dict) -> RunLimits:
    raw = config["limits"]
    return RunLimits(
        model_calls=raw["model_calls"],
        tool_calls=raw["tool_calls"],
        tokens=raw.get("tokens"),
        money_cny=Decimal(str(raw["money_cny"])),
        seconds=raw["seconds"],
        max_model_retries=raw.get("model_retries", 2),
        retry_backoff_seconds=raw.get("retry_backoff_seconds", 2.0),
    )


def validate_config(path: Path) -> tuple[dict, Path, Path, Path, RunLimits, dict]:
    config = read_json(path)
    if config.get("schema_version") != 1 or config.get("mode") != "manual_coordinator_role_division":
        raise ValueError("unsupported manual-dispatch configuration")
    if config.get("status") != "prepared_not_started":
        raise ValueError("configuration must remain a prepared, unstarted plan")
    constraints = config.get("execution_constraints") or {}
    if constraints.get("coordinator_model_requests_allowed") != 0:
        raise ValueError("manual coordinator must allow zero coordinator model requests")
    if constraints.get("automatic_provider_fallback") is not False:
        raise ValueError("automatic provider fallback must be disabled")
    if constraints.get("deepseek_allowed") is not False:
        raise ValueError("DeepSeek must remain disabled")
    routes = load_roles(config["roles"])
    for role, route in routes.items():
        if route.provider != "paratera":
            raise ValueError(f"{role} must use the reviewed Paratera route")
        if "deepseek" in route.model.casefold() or "claude" in route.model.casefold():
            raise ValueError(f"forbidden model in {role}")
        require_cny_price_schedule(route.model, route_id=route.provider)
    limits = limits_from(config)
    if limits.money_cny is None or limits.money_cny > Decimal("20"):
        raise ValueError("this prepared batch requires a CNY hard cap no greater than 20")
    source = resolve_inside_root(config["input"])
    if not source.is_dir():
        raise ValueError(f"input directory is missing: {source}")
    for name in config["floor_plan_images"]:
        if Path(name).name != name or not (source / name).is_file():
            raise ValueError(f"invalid floor plan image: {name}")
    output = resolve_inside_root(config["output"])
    credentials = resolve_inside_root(config["credentials_file"])
    if not credentials.is_file():
        raise ValueError("explicit credentials file is missing")
    agent = agent_version_record(ROOT, verify=True)
    return config, source, output, credentials, limits, routes


def manifest_path(output: Path) -> Path:
    return output / "manual_dispatch_manifest.json"


def load_initialized(config_path: Path):
    config, source, output, credentials, limits, routes = validate_config(config_path)
    path = manifest_path(output)
    if not path.is_file():
        raise ValueError("run is not initialized")
    manifest = read_json(path)
    if manifest["configuration_sha256"] != digest(config_path):
        raise ValueError("configuration changed after initialization")
    if manifest["agent"] != agent_version_record(ROOT, verify=True):
        raise ValueError("runtime/domain version changed after initialization")
    run = output / "bim"
    if not (run / "inputs.json").is_file():
        raise ValueError("initialized BIM input manifest is missing")
    started = read_json(run / "inputs.json").get("started_epoch")
    if not isinstance(started, (int, float)):
        raise ValueError("initialized run has no durable start time")
    return config, source, output, credentials, limits, routes, manifest, run, float(started)


def action_name(prefix: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"manual_receipts/{prefix}_{stamp}.json"


def agent_identity(record: dict) -> dict:
    return {key: record[key] for key in ("version_id", "source_commit") if key in record}


def refresh_reports(output: Path, store: EventStore, session: RoleSession) -> dict:
    accounting = role_accounting(store, session.registry)
    store.write_json("role_state.json", session.state())
    write_json(output / "accounting.json", accounting)
    return accounting


def explicit_task_roles(tasks: list[dict]) -> dict[str, str]:
    """Freeze the only task identities and roles that may reach an adapter."""

    task_roles: dict[str, str] = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("every task must be one JSON object")
        task_id, role_id = task.get("task_id"), task.get("role_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("every task needs a non-empty task_id")
        if task_id == "coordinator":
            raise ValueError("reader task_id cannot equal coordinator")
        if role_id not in {"plan_reader", "elevation_reader"}:
            raise ValueError(f"task {task_id} needs plan_reader or elevation_reader")
        if task_id in task_roles:
            raise ValueError("task IDs must be unique in this dispatch")
        task_roles[task_id] = role_id
    return task_roles


def explicit_reader_factory(*, task_roles, routes, adapter_type, base_url, api_key):
    """Bind each admitted task directly to its reviewed role route.

    The decision uses only the caller's frozen task_id -> role_id map.  It does
    not infer identity from a child directory or any mutable runtime file.
    """

    frozen_roles = dict(task_roles)
    if not frozen_roles:
        raise ValueError("model-enabled session needs an explicit task-role map")
    if set(frozen_roles.values()) - {"plan_reader", "elevation_reader"}:
        raise ValueError("task-role map contains a non-reader role")

    def factory(task_id, configuration, child):
        role_id = frozen_roles.get(task_id)
        if role_id is None or task_id == "coordinator":
            raise ValueError("only explicitly supplied reader task IDs may make model requests")
        expected = routes[role_id]
        expected = expected.model_dump(mode="json") if hasattr(expected, "model_dump") else dict(expected)
        actual = configuration.model_dump(mode="json") if hasattr(configuration, "model_dump") else dict(configuration)
        if actual != expected or actual.get("provider") != "paratera":
            raise ValueError("reader route differs from frozen role configuration")
        return adapter_type(base_url=base_url, api_key=api_key)

    return factory


def request_counting_adapter(adapter_type, counter):
    """Count adapter sends without second-guessing Runtime's durable budget.

    Runtime records the reservation and adapter_request immediately before it
    calls ``send``.  Reading aggregate accounting here therefore mistakes the
    current in-flight request for an older request with missing usage.  The
    Runtime budget has already admitted this request against the root EventStore
    ledger, so this adapter only records that the transport boundary was reached.
    """

    class RequestCountingAdapter(adapter_type):
        async def send(self, request, *, timeout):
            counter["http_requests"] += 1
            return await super().send(request, timeout=timeout)

    return RequestCountingAdapter


async def open_session(config_path: Path, *, permit_models: bool, task_roles=None):
    loaded = load_initialized(config_path)
    config, source, output, credentials, limits, routes, manifest, run, started = loaded
    stack = AsyncExitStack()
    await stack.__aenter__()
    try:
        store = EventStore(
            output,
            run_id=output.name,
            task_id="coordinator",
            budget_limit=limits.ledger_limit(),
        )
        stack.callback(store.close)
        client = await stack.enter_async_context(frozen_bim_client(run, repository_root=ROOT))
        frozen = FrozenBimTools(client, coordinator_role(limits.ledger_limit()), run_directory=run)
        state = {"session": None, "http_requests": 0}
        if permit_models:
            base, key = paratera_credentials(credentials)
            factory = explicit_reader_factory(
                task_roles=task_roles or {},
                routes=routes,
                adapter_type=request_counting_adapter(HttpChatAdapter, state),
                base_url=base,
                api_key=key,
            )
        else:
            def factory(task_id, configuration, child):
                raise ValueError("this command permits zero model requests")
        session = RoleSession(
            store=store,
            frozen=frozen,
            routes=routes,
            adapter_factory=factory,
            limits=limits,
            root=ROOT,
            max_concurrent_readers=config["max_concurrent_readers"],
            started_epoch=started,
        )
        state["session"] = session
        return stack, loaded, store, session, state
    except BaseException:
        await stack.aclose()
        raise


def command_validate(config_path: Path) -> None:
    config, source, output, credentials, limits, routes = validate_config(config_path)
    print(json.dumps({
        "status": "prepared_not_started",
        "batch_id": config["batch_id"],
        "agent": agent_identity(agent_version_record(ROOT, verify=True)),
        "input_files": len([p for p in source.rglob("*") if p.is_file()]),
        "output_exists": output.exists(),
        "credentials_file_exists": credentials.is_file(),
        "money_cny": str(limits.money_cny),
        "routes": {role: {"provider": route.provider, "model": route.model} for role, route in routes.items()},
        "coordinator_model_requests_allowed": 0,
        "model_requests_made": 0,
    }, ensure_ascii=False, indent=2))


def command_self_test(config_path: Path) -> None:
    """Exercise adapter authorization locally without credentials or network."""

    config, source, output, credentials, limits, routes = validate_config(config_path)

    class MockAdapter:
        def __init__(self, *, base_url, api_key):
            self.base_url, self.api_key = base_url, api_key

    task_roles = {"mock-plan": "plan_reader", "mock-elevation": "elevation_reader"}
    factory = explicit_reader_factory(
        task_roles=task_roles,
        routes=routes,
        adapter_type=MockAdapter,
        base_url="mock://no-network",
        api_key="not-a-credential",
    )
    plan = factory("mock-plan", routes["plan_reader"], object())
    elevation = factory("mock-elevation", routes["elevation_reader"], object())
    rejected = []
    for label, task_id, route in (
        ("unlisted_task", "not-authorized", routes["plan_reader"]),
        ("coordinator", "coordinator", routes["coordinator"]),
        ("route_mismatch", "mock-plan", routes["elevation_reader"]),
    ):
        try:
            factory(task_id, route, object())
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError(f"factory failed to reject {label}")
    assert plan.base_url == elevation.base_url == "mock://no-network"
    assert plan.api_key == elevation.api_key == "not-a-credential"
    pending_current_event = {"requests": 1, "estimated_cost_cny": None}

    class MockSendAdapter:
        def __init__(self, *, base_url, api_key):
            self.base_url, self.api_key = base_url, api_key
            self.send_calls = 0

        async def send(self, request, *, timeout):
            self.send_calls += 1
            return {"request": request, "timeout": timeout}

    counter = {"http_requests": 0}
    counted_type = request_counting_adapter(MockSendAdapter, counter)
    counted = counted_type(base_url="mock://no-network", api_key="not-a-credential")
    sent = asyncio.run(counted.send({"pending_event": pending_current_event}, timeout=1))
    assert counted.send_calls == counter["http_requests"] == 1
    assert sent["request"]["pending_event"] == pending_current_event
    print(json.dumps({
        "status": "passed",
        "authorized": sorted(task_roles),
        "rejected": rejected,
        "pending_current_event_forwarded": True,
        "runtime_budget_owner": "Runtime root EventStore ledger",
        "child_runtime_file_reads": 0,
        "credentials_read": False,
        "network_requests": 0,
        "model_requests": 0,
    }, ensure_ascii=False, indent=2))


def command_init(config_path: Path, gate: bool) -> None:
    if not gate:
        raise ValueError("init requires --after-first-run-complete")
    config, source, output, credentials, limits, routes = validate_config(config_path)
    if output.exists():
        raise ValueError("output already exists; no automatic overwrite or rerun")
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    run, _, _ = prepare_inputs(
        output,
        images=source,
        mesh=None,
        building_input=None,
        scope=config["scope"],
        image_kind=config["image_kind"],
        max_candidates=config["max_candidates"],
        floor_plan_images=config["floor_plan_images"],
        started_epoch=started,
        seconds=limits.seconds,
    )
    manifest = {
        "schema_version": "manual-dispatch-v1",
        "batch_id": config["batch_id"],
        "configuration": str(config_path.resolve()),
        "configuration_sha256": digest(config_path),
        "initialized_utc": datetime.now(UTC).isoformat(),
        "sequence_gate_acknowledged": True,
        "agent": agent_version_record(ROOT, verify=True),
        "roles": {name: route.model_dump(mode="json") for name, route in routes.items()},
        "limits": limits.model_dump(mode="json"),
        "coordinator_model_requests_allowed": 0,
        "automatic_provider_fallback": False,
        "credentials_policy": "explicit main-tree .env read-only; only Paratera URL/key read during delegate",
        "task_policy": "root dev model supplies original-image-only tasks after first run; no prior answer or GT",
        "guidance": guidance_catalog(),
    }
    write_json(manifest_path(output), manifest)
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        store.write_json("role_state.json", {"records": {}, "coordinator_model_requests": 0})
    print(json.dumps({"status": "initialized", "output": str(output), "run": str(run), "model_requests_made": 0}, ensure_ascii=False))


async def command_delegate(config_path: Path, task_path: Path) -> None:
    raw = read_json(task_path)
    tasks = raw["tasks"] if isinstance(raw, dict) else raw
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks file must be a non-empty list or an object with a tasks list")
    task_roles = explicit_task_roles(tasks)
    task_ids = list(task_roles)
    stack, loaded, store, session, state = await open_session(
        config_path, permit_models=True, task_roles=task_roles
    )
    output = loaded[2]
    try:
        first = not session.registry.records
        if first:
            _, auto_added = session._with_plan_floors(tasks, add_missing=True)
            if auto_added:
                raise ValueError(
                    "first dispatch must explicitly cover every declared plan/cardinal drawing; "
                    "runtime would auto-add: " + json.dumps(auto_added, ensure_ascii=False)
                )
        result = await session.delegate_many(tasks)
        accounting = refresh_reports(output, store, session)
        receipt = {
            "action": "delegate",
            "occurred_utc": datetime.now(UTC).isoformat(),
            "tasks_file": str(task_path.resolve()),
            "tasks_sha256": digest(task_path),
            "task_ids": task_ids,
            "result": result,
            "accounting": accounting,
            "http_requests_this_command": state["http_requests"],
            "coordinator_model_requests": 0,
            "automatic_fallback": False,
        }
        store.write_json(action_name("delegate"), receipt)
    finally:
        await stack.aclose()
    write_behaviour_report(output / "events.jsonl", output / "behaviour", source_root=ROOT)
    print(json.dumps({"status": "completed", "task_ids": task_ids, "http_requests": state["http_requests"], "accounting": accounting}, ensure_ascii=False, default=str))


async def command_tool(config_path: Path, name: str, arguments_path: Path) -> None:
    if name in {"delegate_readers", "review_detail"}:
        raise ValueError(f"{name} is not available through the manual tool command")
    arguments = read_json(arguments_path)
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be one JSON object")
    stack, loaded, store, session, state = await open_session(config_path, permit_models=False)
    output = loaded[2]
    try:
        available = {row["name"] for row in await session.list_tools()}
        if name not in available:
            raise ValueError(f"tool is not in the coordinator catalog: {name}")
        result = await session.call_tool(name, arguments)
        accounting = refresh_reports(output, store, session)
        receipt = {
            "action": "tool",
            "occurred_utc": datetime.now(UTC).isoformat(),
            "tool": name,
            "arguments_file": str(arguments_path.resolve()),
            "arguments_sha256": digest(arguments_path),
            "arguments": arguments,
            "result": result,
            "accounting": accounting,
            "coordinator_model_requests": 0,
        }
        store.write_json(action_name("tool_" + name), receipt)
    finally:
        await stack.aclose()
    write_behaviour_report(output / "events.jsonl", output / "behaviour", source_root=ROOT)
    body = result.get("structuredContent") if isinstance(result, dict) else result
    print(json.dumps({"tool": name, "isError": result.get("isError", False), "result": body, "model_requests_made": 0}, ensure_ascii=False, default=str))


def command_status(config_path: Path) -> None:
    config, source, output, credentials, limits, routes, manifest, run, started = load_initialized(config_path)
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        registry = ArtifactRegistry(store)
        accounting = role_accounting(store, registry)
        result = {
            "output": str(output),
            "agent": manifest["agent"],
            "elapsed_wall_seconds": max(0.0, time.time() - started),
            "reader_records": registry.state(),
            "accounting": accounting,
            "coordinator_model_requests": 0,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "self-test", "init", "delegate", "tool", "status"):
        child = sub.add_parser(name)
        child.add_argument("--config", type=Path, required=True)
        if name == "init":
            child.add_argument("--after-first-run-complete", action="store_true")
        elif name == "delegate":
            child.add_argument("--tasks", type=Path, required=True)
        elif name == "tool":
            child.add_argument("--name", required=True)
            child.add_argument("--arguments", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    if args.command == "validate":
        command_validate(config_path)
    elif args.command == "self-test":
        command_self_test(config_path)
    elif args.command == "init":
        command_init(config_path, args.after_first_run_complete)
    elif args.command == "delegate":
        asyncio.run(command_delegate(config_path, args.tasks.resolve()))
    elif args.command == "tool":
        asyncio.run(command_tool(config_path, args.name, args.arguments.resolve()))
    else:
        command_status(config_path)


if __name__ == "__main__":
    main()
