"""Small audited CLI around the existing BIM bridge.

This helper never calls a model and never reads evaluation ground truth itself.
The existing bridge remains responsible for executing BIM MCP tools and saving
the complete request/reply/image record under ``<run>/bridge/<uuid>/``.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.tool_scripts import bim_agent_bridge as bridge  # noqa: E402


_SERVER_PARAMETERS = bridge.StdioServerParameters


def utf8_server_parameters(*args, **kwargs):
    """Add Windows UTF-8 mode to the bridge-spawned server only.

    MCP's default environment allowlist does not inherit PYTHONUTF8 from this
    wrapper. Supplying it on StdioServerParameters fixes unqualified read_text()
    calls in the child while retaining the production bridge implementation.
    """
    env = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", **(kwargs.pop("env", None) or {})}
    return _SERVER_PARAMETERS(*args, env=env, **kwargs)


def resolve(path: Path) -> Path:
    """Resolve command-line paths relative to the repository root."""
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, default):
    """Tolerate a bridge file being replaced while an active call is observed."""
    try:
        return load_json(path), None
    except (OSError, json.JSONDecodeError) as error:
        return default, f"{type(error).__name__}: {error}"


def text_errors(reply: dict) -> list[str]:
    rows = []
    for block in reply.get("content", []):
        if block.get("type") == "text" and block.get("text"):
            text = " ".join(str(block["text"]).split())
            rows.append(text[:1200] + ("..." if len(text) > 1200 else ""))
    structured = reply.get("structuredContent")
    if isinstance(structured, dict):
        for key in ("error", "errors", "reason"):
            if structured.get(key):
                value = json.dumps(structured[key], ensure_ascii=False)
                rows.append(value[:1200] + ("..." if len(value) > 1200 else ""))
    return rows


def reply_summary(index: int, reply: dict) -> dict:
    images = [block["path"] for block in reply.get("content", [])
              if block.get("type") == "image" and block.get("path")]
    structured = reply.get("structuredContent")
    useful = {}
    if isinstance(structured, dict):
        for key in ("status", "candidate", "draft_id", "claim_id", "completed",
                    "details_file", "next_offset", "source_geometry_ready"):
            if key in structured:
                useful[key] = structured[key]
    return {
        "index": index,
        "tool": reply.get("tool"),
        "is_error": bool(reply.get("isError")),
        "images": images,
        "result": useful,
        "errors": text_errors(reply) if reply.get("isError") else [],
    }


def batch_summary(result: dict) -> dict:
    replies = result.get("replies", [])
    return {
        "record": result.get("record"),
        "completed": result.get("completed"),
        "call_count": len(replies),
        "calls": [reply_summary(index, reply) for index, reply in enumerate(replies, 1)],
    }


async def call(run: Path, requests_path: Path) -> int:
    requests = load_json(requests_path)
    original_parameters = bridge.StdioServerParameters
    bridge.StdioServerParameters = utf8_server_parameters
    try:
        result = await bridge.invoke(run, requests)
    finally:
        bridge.StdioServerParameters = original_parameters
    print(json.dumps(batch_summary(result), ensure_ascii=False, indent=2))
    return 0 if result.get("completed") else 1


def history(run: Path) -> int:
    bridge = run / "bridge"
    batches = []
    for requests_path in bridge.glob("*/requests.json") if bridge.is_dir() else []:
        replies_path = requests_path.with_name("replies.json")
        stat = requests_path.stat()
        requests, requests_read_error = try_load_json(requests_path, [])
        replies, replies_read_error = try_load_json(replies_path, []) if replies_path.is_file() else ([], None)
        reply_time = (datetime.fromtimestamp(replies_path.stat().st_mtime, timezone.utc).isoformat()
                      if replies_path.is_file() else None)
        batches.append({
            "time_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "reply_time_utc": reply_time,
            "record": str(requests_path.parent),
            "requested_tools": [row.get("tool") for row in requests],
            "reply_count": len(replies),
            "completed": len(replies) == len(requests) and
                         not requests_read_error and not replies_read_error and
                         not any(bool(row.get("isError")) for row in replies),
            "read_error": requests_read_error or replies_read_error,
            "calls": [reply_summary(index, reply)
                      for index, reply in enumerate(replies, 1)],
        })
    batches.sort(key=lambda row: (row["time_utc"], row["record"]))

    build_tools = {"build_plan_bim", "build_parametric_bim", "build_bim"}

    def first_request(tools: set[str]) -> str | None:
        return next((row["time_utc"] for row in batches
                     if any(tool in tools for tool in row["requested_tools"])), None)

    def first_success(tools: set[str]) -> str | None:
        return next((row["reply_time_utc"] for row in batches
                     if row["reply_time_utc"] and any(
                         call["tool"] in tools and not call["is_error"] for call in row["calls"])), None)

    requested_count = sum(len(row["requested_tools"]) for row in batches)
    replied_count = sum(row["reply_count"] for row in batches)
    failed_count = sum(call["is_error"] for row in batches for call in row["calls"])
    summary = {
        "requested_tool_call_count": requested_count,
        "replied_tool_call_count": replied_count,
        "successful_tool_call_count": replied_count - failed_count,
        "failed_tool_call_count": failed_count,
        "pending_or_unreadable_tool_call_count": max(0, requested_count - replied_count),
        "image_count": sum(len(call["images"]) for row in batches for call in row["calls"]),
        "first_build_attempt_utc": first_request(build_tools),
        "first_successful_build_reply_utc": first_success(build_tools),
        "first_assembly_attempt_utc": first_request({"assemble_plan_bim"}),
        "first_successful_assembly_reply_utc": first_success({"assemble_plan_bim"}),
        "first_finish_attempt_utc": first_request({"finish_bim"}),
        "first_successful_finish_reply_utc": first_success({"finish_bim"}),
        "timestamp_basis": ("attempt=requests.json mtime; success=replies.json batch mtime. "
                            "The latter is the end of its bridge batch, not a per-call server clock."),
        "counting_basis": ("Top-level bridge requests/replies only. Server tools.jsonl actions, including "
                           "nested record_claim actions, are not counted as model tool calls."),
        "provider_tokens": "unknown",
        "provider_cost": "unknown",
    }
    print(json.dumps({
        "run": str(run),
        "batch_count": len(batches),
        "tool_call_count": requested_count,
        "error_count": failed_count,
        "image_count": summary["image_count"],
        "summary": summary,
        "batches": batches,
    }, ensure_ascii=False, indent=2))
    return 0


def evaluate(run: Path, case: str, out: Path | None, candidate: str | None) -> int:
    command = [sys.executable, str(ROOT / "scripts/dev/evaluate_run.py"), str(run),
               "--case", case]
    if out is not None:
        command += ["--out", str(out)]
    if candidate:
        command += ["--candidate", candidate]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)

    call_cmd = commands.add_parser("call", help="Execute one existing requests JSON through the bridge")
    call_cmd.add_argument("--run", type=Path, required=True)
    call_cmd.add_argument("requests", type=Path)

    history_cmd = commands.add_parser("history", help="Summarize all saved bridge batches without changing the run")
    history_cmd.add_argument("--run", type=Path, required=True)

    evaluate_cmd = commands.add_parser("evaluate", help="Run the existing offline evaluator after generation ends")
    evaluate_cmd.add_argument("--run", type=Path, required=True)
    evaluate_cmd.add_argument("--case", choices=("sm21", "sm24", "sm25"), required=True)
    evaluate_cmd.add_argument("--out", type=Path)
    evaluate_cmd.add_argument("--candidate")
    return cli


def main() -> int:
    args = parser().parse_args()
    run = resolve(args.run)
    if not (run / "inputs.json").is_file() and not (run / "bim" / "inputs.json").is_file():
        raise SystemExit(f"run has no inputs.json: {run}")
    if args.command == "call":
        bridge_run = run / "bim" if (run / "bim" / "inputs.json").is_file() else run
        return asyncio.run(call(bridge_run, resolve(args.requests)))
    if args.command == "history":
        bridge_run = run / "bim" if (run / "bim" / "inputs.json").is_file() else run
        return history(bridge_run)
    return evaluate(run, args.case, resolve(args.out) if args.out else None, args.candidate)


if __name__ == "__main__":
    raise SystemExit(main())
