"""Fixed local-observation batch via the real external MCP gateway.

No evaluation-side references enter a request. One attempt per question/model;
the child may make one follow-up after a read-only tool call. A durable shared
quota counts all sends, including failures. Restart reuses completed outcomes.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent_runtime.mcp_tools import McpToolClient
from src.agent_runtime.store import EventStore

HERE = Path(__file__).resolve().parent
MODELS = ("Qwen3.8-27B", "Qwen3.8-Flash")


async def run_case(args, case, model, index):
    identifier = f"{index:02d}_{model.rsplit('-', 1)[-1].lower()}"
    out = args.out / identifier
    driver = args.out / (identifier + "_driver")
    completed = out / "role_case.json"
    if completed.is_file():
        return json.loads(completed.read_bytes())
    driver.mkdir(parents=True, exist_ok=True)
    inputs = driver / "inputs"
    inputs.mkdir(exist_ok=True)
    for row in case["images"]:
        data = (ROOT / row["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("fixed input hash changed")
        destination = inputs / Path(row["path"]).name
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError("resumed input differs")
        if not destination.exists():
            shutil.copyfile(ROOT / row["path"], destination)
    image_kind = {"drawing": "drawings", "mesh_render": "mesh_views", "photo": "photos"}[case["input_kind"]]
    arguments = ["-m", "src.agent.runtime_coordinator", "--out", str(out),
        "--images", str(inputs), "--image-kind", image_kind, "--provider", "paratera",
        "--model", model, "--credentials-file", str(args.credentials_file),
        "--quota-journal", str(args.out / "role_requests.jsonl"), "--quota-limit", "60",
        "--model-calls", "2", "--tool-calls", "8", "--tokens", "120000", "--seconds", "900",
        "--output-tokens", "16384", "--scope", case["question"]]
    if out.is_dir():
        arguments.append("--resume")
    async with McpToolClient(command=sys.executable, args=arguments, cwd=ROOT,
                             run_directory=driver, env={"PYTHONPATH": str(ROOT)}) as client:
        await client.list_tools()
        state = (await client.call_tool("runtime_state", {}))["structuredContent"]
        if not state["views"]:
            for row in case["images"]:
                result = await client.call_tool("view_image", {
                    "name": Path(row["path"]).name, "coordinate_grid": False})
                if result.get("isError"):
                    raise ValueError("fixed input view failed")
            state = (await client.call_tool("runtime_state", {}))["structuredContent"]
        task = {"task_id": case["case_id"], "question": case["question"],
            "view_ids": [v["reference"]["reference"]["value"] for v in state["views"]],
            "notes": ["Input kind: " + case["input_kind"],
                "Photo surrogate, not a real photograph: " + str(case["photo_surrogate"]),
                *[row["view_source"] + "; " + row["coordinate_source"] for row in case["images"]]],
            "budget": {"model_calls": 2, "tool_calls": 2, "tokens": 60000, "seconds": 360}}
        result = await client.call_tool("delegate_to_role", task)
        outcome = result.get("structuredContent", {})
        state = (await client.call_tool("runtime_state", {}))["structuredContent"]
    events = EventStore.read_events(out / "events.jsonl")
    responses = [e.payload for e in events if e.payload.event_type == "model_response"]
    usage = [r.usage.model_dump(mode="json") for r in responses]
    report = {"case_id": case["case_id"], "model": model, "run_id": identifier,
        "test_group": case["test_group"], "input_kind": case["input_kind"],
        "information_sufficiency": case["information_sufficiency"],
        "photo_surrogate": case["photo_surrogate"], "status": outcome.get("status", "gateway_error"),
        "outcome": outcome, "gateway_error": result.get("isError", False),
        "model_requests": sum(e.payload.event_type == "adapter_request" for e in events),
        "tool_invocations": sum(e.payload.event_type == "tool_invocation" for e in events),
        "usage": usage, "root_budget": state["budget"],
        "protocol_notice": "Runtime validity is not correctness. Human evaluation is separate."}
    completed.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


async def main(args):
    args.out = args.out.resolve()
    if not args.out.is_relative_to(ROOT):
        raise ValueError("all outputs must stay inside the assigned worktree")
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE / "role_cases/manifest.json").read_bytes())
    source_files = [*sorted((ROOT / "src/agent_runtime").glob("*.py")),
        *sorted((ROOT / "src/agent").glob("runtime_*.py")),
        ROOT / "src/agent_runtime/model_profiles.json", Path(__file__).resolve()]
    protocol = {"manifest_sha256": hashlib.sha256((HERE / "role_cases/manifest.json").read_bytes()).hexdigest(),
        "source_files": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        "models": list(MODELS), "temperature": 0.0, "enable_thinking": True,
        "max_tokens": 16384, "questions_per_model": len(manifest["cases"]),
        "max_model_calls_per_question": 2, "max_batch_requests": 60,
        "retries": 0, "fallback": False, "selection": "all fixed questions; no answer-based filtering",
        "images": "frozen view_image full view; maximum edge 1600; no grid; actual bytes logged",
        "guide": "new local-observer role guidance; frozen coordinator guide unchanged",
        "comparison_notice": "Prior elevation probe used a different prompt and temperature 0.7; this is not a controlled model ranking."}
    protocol_path = args.out / "protocol.json"
    if protocol_path.exists() and json.loads(protocol_path.read_bytes()) != protocol:
        raise ValueError("resumed batch protocol changed")
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n")
    results = []
    for index, case in enumerate(manifest["cases"], 1):
        for model in MODELS:
            row = await run_case(args, case, model, index)
            results.append({k: row[k] for k in ("case_id", "model", "run_id", "test_group", "input_kind",
                "information_sufficiency", "photo_surrogate", "status", "model_requests", "usage")})
            (args.out / "index.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"case": row["case_id"], "model": model, "status": row["status"],
                              "requests": row["model_requests"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
