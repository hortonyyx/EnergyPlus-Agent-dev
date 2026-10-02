"""Run one role on admitted case inputs using the frozen BIM tool service.

CLI: python -m src.agent.runtime_entry --help
No model call occurs unless --provider paratera or an explicit scripted fixture
is selected. Tool preparation never starts the historical subscription runner.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image

from scripts.tool_scripts.bim_agent_guidance import build_guide
from scripts.tool_scripts.bim_agent_inputs import freeze_building_input
from scripts.tool_scripts.bim_agent_mesh import freeze_mesh
from src.agent.runtime_tools import (
    FrozenBimTools, coordinator_role, local_observer_role, frozen_bim_client,
    write_frozen_materials, write_frozen_tool_catalog,
)
from src.agent_runtime.adapter import HttpChatAdapter, ScriptedAdapter
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore
from src.agent_runtime.versions import make_versions


ROOT = Path(__file__).resolve().parents[2]


def prepare_inputs(output: Path, *, images: Path | None, mesh: Path | None,
                   building_input: Path | None, scope: str, image_kind: str,
                   max_candidates: int) -> tuple[Path, str, str]:
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
    manifest = {"images": inventory, "image_kind": image_kind if inventory else None,
        "scope": scope, "max_candidates": max_candidates, "deadline_epoch": None,
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
    limits = RunLimits(model_calls=args.model_calls, tool_calls=args.tool_calls,
                       seconds=args.seconds, tokens=args.tokens)
    if args.provider == "scripted" and args.script is None:
        raise ValueError("--provider scripted requires --script")
    if args.resume:
        run = output / "bim"
        guide, task = (output / "guide.txt").read_text(), (output / "task.txt").read_text()
    else:
        output.mkdir(parents=True, exist_ok=False)
        run, guide, task = prepare_inputs(output, images=args.images, mesh=args.mesh,
            building_input=args.building_input, scope=args.scope, image_kind=args.image_kind,
            max_candidates=args.max_candidates)
    role = (local_observer_role if args.role == "local_observer" else coordinator_role)(limits.ledger_limit())
    adapter = None
    try:
        with EventStore(output, run_id=output.name, task_id=args.role, budget_limit=limits.ledger_limit()) as store:
            async with frozen_bim_client(run_directory=run, readonly=role.read_only, repository_root=ROOT) as client:
                tools = FrozenBimTools(client, role, run_directory=run)
                catalog = await tools.list_tools()
                if not args.resume:
                    write_frozen_materials(output / "frozen", repository_root=ROOT)
                    write_frozen_tool_catalog(output / "frozen", catalog, readonly=role.read_only)
                parameters = {"max_tokens": args.output_tokens, "temperature": args.temperature,
                              "enable_thinking": args.thinking}
                if args.provider == "scripted":
                    adapter = ScriptedAdapter(json.loads(args.script.read_bytes()))
                    route = {"route_id": "offline-scripted", "model": "scripted-model"}
                else:
                    base_url, key = paratera_credentials(args.credentials_file)
                    adapter = HttpChatAdapter(base_url=base_url, api_key=key)
                    route = {"route_id": "paratera", "model": args.model, "base_url": base_url}
                specs = [{"type": "function", "function": {"name": t["name"],
                    "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in catalog]
                versions = make_versions(store, root=ROOT, prompt=guide, tools=specs,
                    parameters=parameters, route=route, code_paths=("src/agent/runtime_entry.py",
                        "src/agent/runtime_tools.py", "scripts/tool_scripts", "src/agent/geometry",
                        "src/agent/correction", "src/agent/execution"))
                # A refused resume must not replace the original run's evidence.
                # The runtime checks current versions against its saved checkpoint.
                if not args.resume:
                    store.write_json("versions.json", versions.model_dump(mode="json"))
                originals, user_content = {}, [{"type": "text", "text": task}]
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
                    {"role": "user", "content": user_content if args.attach_image else task}]
                engine = Runtime(store=store, adapter=adapter, tools=tools, role=role,
                    model=route["model"], parameters=parameters, versions=versions, limits=limits)
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
    p.add_argument("--mesh", type=Path)
    p.add_argument("--building-input", type=Path)
    p.add_argument("--image-kind", choices=("drawings", "mesh_views", "photos", "unknown"), default="drawings")
    p.add_argument("--scope", default="Build the supplied building at the requested detail; inspect saved results and report limitations.")
    p.add_argument("--role", choices=("coordinator", "local_observer"), default="coordinator")
    p.add_argument("--provider", choices=("scripted", "paratera"), required=True)
    p.add_argument("--script", type=Path, help="explicit offline Chat Completions response fixture")
    p.add_argument("--model", default="Qwen3.8-27B")
    p.add_argument("--credentials-file", type=Path, help="read only PARATERA_BASE_URL and PARATERA_API_KEY")
    p.add_argument("--model-calls", type=int, default=6)
    p.add_argument("--tool-calls", type=int, default=12)
    p.add_argument("--seconds", type=float, default=180.0)
    p.add_argument("--tokens", type=int, default=5_000_000)
    p.add_argument("--output-tokens", type=int, default=2048)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--thinking", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--max-candidates", type=int, default=4)
    p.add_argument("--attach-image", action="append", default=[])
    p.add_argument("--resume", action="store_true")
    return p


def main():
    args = parser().parse_args()
    result = asyncio.run(execute(args))
    print(json.dumps({key: result[key] for key in ("status", "model_calls", "tool_calls", "reported_tokens", "billing_usd")}, ensure_ascii=False))
    raise SystemExit(0 if result["status"] in {"completed", "model_budget_exhausted", "tool_budget_exhausted", "time_budget_exhausted", "token_budget_exhausted"} else 1)


if __name__ == "__main__":
    main()
