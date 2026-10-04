#!/usr/bin/env python3
"""Run or evaluate the fixed sm24 four-facade concurrency experiment.

``run`` is the only command that can contact Paratera.  It uses the real
runtime coordinator MCP process and its ``delegate_to_roles`` tool for both the
four-way and max-concurrency-one conditions.  ``validate`` and ``evaluate`` are
offline.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from facade_support import (build_tasks, evaluate_batches, load_json,
    validate_protocol, validate_run_manifest)
from src.agent_runtime.mcp_tools import McpToolClient


MANIFEST = HERE / "facade_cases.json"
REFERENCES = HERE / "facade_references.json"
MODES = (("concurrent", 4), ("sequential", 1))


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def journal_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise ValueError("quota journal has a torn tail; do not retry")
    return [json.loads(line) for line in data.splitlines()]


def attempt_count(rows: list[dict]) -> int:
    return sum(row.get("event") == "attempt" for row in rows)


def usage_for_tickets(rows: list[dict], first_ticket: int, last_ticket: int) -> dict:
    responses = [row for row in rows if row.get("event") == "response"
                 and first_ticket <= row.get("ticket", 0) <= last_ticket]
    usages = [row.get("usage") for row in responses if isinstance(row.get("usage"), dict)]
    return {
        "reported_requests": len(usages),
        "missing_usage_requests": max(0, last_ticket - first_ticket + 1 - len(usages)),
        "prompt_tokens": sum(row.get("prompt_tokens", 0) for row in usages),
        "completion_tokens": sum(row.get("completion_tokens", 0) for row in usages),
        "total_tokens": sum(row.get("total_tokens", 0) for row in usages),
    }


def protocol() -> dict:
    sources = [Path(__file__).resolve(), HERE / "facade_support.py",
               ROOT / "src/agent/runtime_coordinator.py", ROOT / "src/agent/runtime_delegation.py",
               ROOT / "src/agent_runtime/loop.py", ROOT / "src/agent_runtime/model_profiles.json"]
    return {
        "schema_version": "runtime-r1-facade-protocol/v1",
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sources},
        "model": "Qwen3.8-27B", "temperature": 0.0, "enable_thinking": True,
        "output_tokens": 16384, "conditions": {"concurrent": 4, "sequential": 1},
        "questions_per_condition": 4, "max_model_calls_per_question": 2,
        "shared_request_limit": 20, "failed_and_timed_out_requests_count": True,
        "root_limits_per_condition": {"model_calls": 8, "tool_calls": 8,
                                      "tokens": 400000, "seconds": 1800},
        "child_limits": {"model_calls": 2, "tool_calls": 0,
                         "tokens": 90000, "seconds": 360},
        "sampling": "one fixed four-question concurrent condition and one fixed sequential condition; no added samples",
        "reference_isolation": "facade_references.json is not opened by run",
    }


def prepare_inputs(out: Path, manifest: dict) -> Path:
    inputs = out / "driver" / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    for case in manifest["cases"]:
        source = ROOT / case["image"]
        target = inputs / case["image_name"]
        if target.is_file() and target.read_bytes() != source.read_bytes():
            raise ValueError(f"resumed input differs: {target}")
        if not target.exists():
            shutil.copyfile(source, target)
    return inputs


async def run_mode(args, manifest: dict, mode: str, concurrency: int, quota: Path) -> dict:
    out = args.out / mode
    completed = out / "batch_result.json"
    if completed.is_file():
        return load_json(completed)
    inputs = prepare_inputs(out, manifest)
    coordinator = out / "coordinator"
    before_rows = journal_rows(quota)
    before_attempts = attempt_count(before_rows)
    command = ["-m", "src.agent.runtime_coordinator", "--out", str(coordinator),
        "--images", str(inputs), "--image-kind", "drawings", "--provider", "paratera",
        "--model", "Qwen3.8-27B", "--credentials-file", str(args.credentials_file),
        "--quota-journal", str(quota), "--quota-limit", "20",
        "--model-calls", "8", "--tool-calls", "8", "--tokens", "400000",
        "--seconds", "1800", "--output-tokens", "16384",
        "--max-concurrent-observers", str(concurrency),
        "--scope", "Fixed sm24 four-facade read-only observation experiment; no BIM edits or whole-case run."]
    if coordinator.is_dir():
        command.append("--resume")
    async with McpToolClient(command=sys.executable, args=command, cwd=ROOT,
                             run_directory=out / "driver", env={"PYTHONPATH": str(ROOT)}) as client:
        catalog = await client.list_tools()
        if "delegate_to_roles" not in {tool["name"] for tool in catalog}:
            raise ValueError("coordinator does not expose delegate_to_roles")
        state = (await client.call_tool("runtime_state", {}))["structuredContent"]
        existing_names = {view["image_name"] for view in state["views"]}
        for case in manifest["cases"]:
            if case["image_name"] in existing_names:
                continue
            raw = await client.call_tool("view_image", {
                "name": case["image_name"], "coordinate_grid": False})
            if raw.get("isError"):
                raise ValueError(f"view_image failed for {case['image_name']}")
        state = (await client.call_tool("runtime_state", {}))["structuredContent"]
        view_ids = {view["image_name"]: view["reference"]["reference"]["value"]
                    for view in state["views"]}
        tasks = build_tasks(manifest, view_ids, mode)
        started = time.monotonic()
        gateway = await client.call_tool("delegate_to_roles", {"tasks": tasks})
        wall_seconds = round(time.monotonic() - started, 3)
        payload = gateway.get("structuredContent", {})
        if payload.get("status") != "completed" or len(payload.get("results", [])) != 4:
            raise ValueError(f"batch gateway did not preserve four results: {payload.get('status')}")
    after_rows = journal_rows(quota)
    after_attempts = attempt_count(after_rows)
    requests = after_attempts - before_attempts
    if requests > 8:
        raise ValueError("condition exceeded four questions x two requests")
    result = {
        "schema_version": "runtime-r1-facade-batch/v1", "mode": mode,
        "max_concurrent_observers": concurrency, "wall_seconds": wall_seconds,
        "requests": requests, "ticket_range": [before_attempts + 1, after_attempts],
        "reported_usage": usage_for_tickets(after_rows, before_attempts + 1, after_attempts),
        "gateway_error": gateway.get("isError", False), "results": payload["results"],
    }
    dump(completed, result)
    return result


async def run(args) -> None:
    args.out = args.out.resolve()
    if not args.out.is_relative_to(ROOT):
        raise ValueError("experiment output must remain inside this worktree")
    # The live path deliberately does not open the evaluation reference file.
    checked = validate_run_manifest(ROOT, MANIFEST)
    if not checked["ok"]:
        raise ValueError(checked["errors"])
    args.out.mkdir(parents=True, exist_ok=True)
    protocol_path = args.out / "protocol.json"
    expected_protocol = protocol()
    if protocol_path.is_file() and load_json(protocol_path) != expected_protocol:
        raise ValueError("resumed experiment protocol or source changed")
    dump(protocol_path, expected_protocol)
    quota = args.out / "request_quota.jsonl"
    manifest = load_json(MANIFEST)
    batches = {}
    for mode, concurrency in MODES:
        batches[mode] = await run_mode(args, manifest, mode, concurrency, quota)
        dump(args.out / "batch_results.json", batches)
    if attempt_count(journal_rows(quota)) > 20:
        raise ValueError("shared request quota exceeded")
    print(json.dumps({mode: {"wall_seconds": row["wall_seconds"], "requests": row["requests"],
                                   "tokens": row["reported_usage"]["total_tokens"]}
                      for mode, row in batches.items()}, ensure_ascii=False))


def render_report(evaluation: dict) -> str:
    con, seq = evaluation["modes"]["concurrent"], evaluation["modes"]["sequential"]
    speedup = seq["wall_seconds"] / con["wall_seconds"] if con["wall_seconds"] else None
    lines = ["# sm24 四立面并发／依次实验报告", "",
        "> 固定四题、Qwen3.8-27B；并发一次、依次一次；失败和超时照计票，不追加抽样。", "",
        "## 总表", "", "| 条件 | 墙钟秒 | 请求 | 实报 token | 用量缺失请求 | 5 cm 内窗高 | 数窗正确 | 宽松定位 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for label, row in (("四题并发", con), ("四题依次", seq)):
        lines.append(f"| {label} | {row['wall_seconds']:.3f} | {row['requests']} | "
                     f"{row['reported_usage']['total_tokens']} | {row['reported_usage']['missing_usage_requests']} | "
                     f"{row['height_windows_correct']}/{row['height_windows_total']} | "
                     f"{row['facade_counts_correct']}/{row['facade_counts_total']} | "
                     f"{row['loose_localizations_correct']}/{row['localizations_total']} |")
    lines += ["", f"依次／并发墙钟比：{speedup:.3f}×。" if speedup is not None else "墙钟比未取得。", "",
              "## 接口状态", "", "| 条件 | 立面 | 运行状态 | 接口收下 | 未解析陈述数 |", "|---|---|---|---|---:|"]
    for mode, row in evaluation["modes"].items():
        for case in row["cases"]:
            lines.append(f"| {mode} | {case['facade']} | {case['runtime_status']} | "
                         f"{'是' if case['interface_accepted'] else '否'} | "
                         f"{len(case['unparsed_statements'])} |")
    lines += ["", "## 逐立面、逐窗结果", ""]
    for mode, row in evaluation["modes"].items():
        lines += [f"### {mode}", "", "| 立面 | 数窗 | 顺序 | 期望/实际宽 mm | 期望窗台/窗顶 m | 实际窗台/窗顶 m | 5 cm | 宽松定位 |", "|---|---:|---:|---|---|---|---|---|"]
        for case in row["cases"]:
            for window in case["windows"]:
                actual = window["actual"] or {}
                lines.append(f"| {case['facade']} | {'对' if case['count_correct'] else '错'} | {window['order']} | "
                    f"{window['expected']['width_mm']}/{actual.get('width_mm', '无')} | "
                    f"{window['expected']['sill_m']:.2f}/{window['expected']['head_m']:.2f} | "
                    f"{actual.get('sill_m', '无')}/{actual.get('head_m', '无')} | "
                    f"{'对' if window['height_within_5cm'] else '错'} | "
                    f"{'对' if window['loose_localization_matches_window'] else '错'} |")
        lines.append("")
    lines += ["## 两扇 4800 mm 大窗", "", "| 条件 | 立面 | 结果 | 实际宽 mm | 实际窗台/窗顶 m |", "|---|---|---|---:|---|"]
    for mode, row in evaluation["modes"].items():
        for special in row["special_4800"]:
            actual = special["actual"] or {}
            lines.append(f"| {mode} | {special['facade']} | {'对' if special['correct'] else '错'} | "
                         f"{actual.get('width_mm', '无')} | "
                         f"{actual.get('sill_m', '无')}/{actual.get('head_m', '无')} |")
    lines += ["", "## 失败、超时与边界", "",
              "所有固定结果均保留在 evaluation.json；接口拒收、无答案、超时和缺失 usage 不按零或正确处理。",
              "评价参照仅由离线 evaluate 命令读取；运行题面、notes 和图片不含参照答案或 GT。",
              "本报告结束后不因结果好坏追加抽样。", ""]
    return "\n".join(lines)


def evaluate(args) -> None:
    checked = validate_protocol(ROOT, MANIFEST, REFERENCES)
    if not checked["ok"]:
        raise ValueError(checked["errors"])
    batches = load_json(args.out / "batch_results.json")
    evaluation = evaluate_batches(batches, load_json(REFERENCES))
    dump(args.out / "evaluation.json", evaluation)
    (args.out / "REPORT.md").write_text(render_report(evaluation), encoding="utf-8")
    print(json.dumps({mode: {key: value for key, value in row.items() if key in {
        "wall_seconds", "requests", "height_within_5cm_ratio", "facade_counts_correct",
        "facade_counts_total"}} for mode, row in evaluation["modes"].items()}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--out", type=Path, required=True)
    run_parser.add_argument("--credentials-file", type=Path, required=True)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "validate":
        result = validate_protocol(ROOT, MANIFEST, REFERENCES)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["ok"] else 1)
    if args.command == "run":
        asyncio.run(run(args))
    else:
        args.out = args.out.resolve()
        if not args.out.is_relative_to(ROOT):
            raise ValueError("experiment output must remain inside this worktree")
        evaluate(args)


if __name__ == "__main__":
    main()
