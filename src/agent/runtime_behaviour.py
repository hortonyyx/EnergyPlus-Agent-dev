"""Read current EventEnvelope logs and the two historical BIM-agent log forms.

Behaviour metrics mention BIM tool families, facades, claims and saved source
BIM files, so this adapter belongs to the building layer.  It only reads the
domain-neutral runtime event contract; the runtime core never imports it.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from src.harness_contracts import EventEnvelope


FACADES = ("north", "south", "east", "west")
FIRST_DRAFT_TOOLS = {"build_plan_bim", "build_bim", "build_parametric_bim"}
WRITE_TOOLS = FIRST_DRAFT_TOOLS | {
    "assemble_plan_bim", "revise_plan_bim", "revise_bim", "finish_bim"
}


def _stamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


def _facade(value: Any) -> str | None:
    text = str(value or "").lower()
    return next((name for name in FACADES if name in text), None)


def _captured(value: Any, log_root: Path) -> Any:
    """Resolve a runtime blob beneath its run directory and verify its digest."""
    if value is None:
        return None
    data = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    if data.get("kind") == "inline":
        return data.get("value")
    if data.get("kind") == "blob":
        blob = data.get("blob") or {}
        uri = blob.get("uri")
        if not isinstance(uri, str):
            raise ValueError("blob capture has no relative URI")
        root = log_root.resolve()
        path = (root / uri).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"blob URI escapes event-log directory: {uri}")
        if not path.is_file():
            raise ValueError(f"blob URI does not exist below event-log directory: {uri}")
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != blob.get("sha256"):
            raise ValueError(f"blob hash mismatch for {uri}: expected {blob.get('sha256')}, got {actual}")
        media_type = str(blob.get("media_type") or "")
        if media_type == "application/json" or media_type.endswith("+json"):
            try:
                return json.loads(raw)
            except (UnicodeDecodeError, ValueError) as error:
                raise ValueError(f"JSON blob cannot be decoded: {uri}") from error
        if media_type.startswith("text/"):
            try:
                return _json(raw.decode("utf-8"))
            except UnicodeDecodeError as error:
                raise ValueError(f"text blob is not UTF-8: {uri}") from error
        return {"blob": blob, "verified_bytes": len(raw)}
    return {"missing": data.get("reason")}


def _relative_times(steps: list[dict[str, Any]], origin: float | None) -> None:
    if origin is None:
        return
    for step in steps:
        absolute = step.pop("_absolute_time", None)
        step["t_call"] = None if absolute is None else round(absolute - origin, 3)


def _read_event_log(path: Path) -> dict[str, Any]:
    events: list[EventEnvelope] = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    events.append(EventEnvelope.model_validate_json(line))
                except Exception as error:
                    raise ValueError(f"{path}:{number}: invalid EventEnvelope: {error}") from error
    if not events:
        raise ValueError(f"empty event log: {path}")
    if len({event.run_id for event in events}) != 1:
        raise ValueError(f"event log contains multiple run IDs: {path}")
    sequences = [event.sequence for event in events]
    if sequences != sorted(set(sequences)):
        raise ValueError(f"event sequences are duplicate or out of order: {path}")
    event_ids = [event.event_id for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError(f"event IDs are not unique: {path}")

    presentations: dict[str, tuple[EventEnvelope, Any]] = {}
    for event in events:
        payload = event.payload
        if payload.event_type != "tool_presentation":
            continue
        target = payload.tool_execution_event_id
        if target in presentations:
            raise ValueError(f"multiple presentation events target tool execution {target}")
        presentations[target] = (event, payload)
    known_execution_ids = {
        event.event_id for event in events if event.payload.event_type == "tool_execution"
    }
    unknown_presentations = sorted(set(presentations) - known_execution_ids)
    if unknown_presentations:
        raise ValueError(f"tool presentations reference unknown executions: {unknown_presentations}")

    responses: dict[str, dict[str, Any]] = {}
    requests: list[dict[str, Any]] = []
    response_records: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    texts: list[str] = []
    usage: list[dict[str, Any]] = []
    origins = [e.occurred_at.value.timestamp() for e in events if e.occurred_at.kind == "known"]
    origin = min(origins) if origins else None
    for event in events:
        payload = event.payload
        kind = payload.event_type
        absolute = event.occurred_at.value.timestamp() if event.occurred_at.kind == "known" else None
        if kind == "adapter_request":
            requests.append({
                "event_id": event.event_id,
                "adapter": payload.adapter,
                "final_request_body": _captured(payload.final_request_body, path.parent),
                "injected_content": [item.model_dump(mode="json") for item in payload.injected_content],
                "images": [item.model_dump(mode="json") for item in payload.images],
                "parameters": payload.parameters.model_dump(mode="json"),
                "versions": payload.versions.model_dump(mode="json"),
            })
        elif kind == "model_response":
            row = {
                "event_id": event.event_id,
                "request_event_id": payload.request_event_id,
                "text": "\n\n".join(payload.visible_text),
                "thinking": [item.model_dump(mode="json") for item in payload.thinking],
                "usage": payload.usage.model_dump(mode="json"),
                "raw_response": _captured(payload.raw_response, path.parent),
                "tool_calls": [item.model_dump(mode="json") for item in payload.tool_calls],
            }
            response_records.append(row)
            texts.extend(payload.visible_text)
            usage.append(row["usage"])
            for call in payload.tool_calls:
                responses[call.call_id] = row
        elif kind == "tool_execution":
            response = responses.get(payload.call_id, {})
            raw = _captured(payload.raw_result, path.parent)
            prepared = _captured(payload.shown_result, path.parent)
            presentation = presentations.get(event.event_id)
            if payload.presentation_status == "sent":
                visible, delivered, presentation_id = prepared, True, None
            elif presentation is not None:
                presentation_event, presentation_payload = presentation
                visible = _captured(presentation_payload.shown_result, path.parent)
                if visible != prepared:
                    raise ValueError(
                        f"tool presentation {presentation_event.event_id} differs from prepared result {event.event_id}"
                    )
                delivered, presentation_id = True, presentation_event.event_id
            else:
                visible, delivered, presentation_id = None, False, None
            steps.append({
                "index": len(steps) + 1,
                "execution_event_id": event.event_id,
                "_absolute_time": absolute,
                "tool": payload.tool_name,
                "arguments": payload.full_arguments,
                "prepared_result": prepared,
                "model_visible_result": visible,
                "delivered_to_model": delivered,
                "presentation_status": payload.presentation_status,
                "presentation_event_id": presentation_id,
                "raw_result": raw,
                "outcome": payload.outcome,
                "is_error": payload.outcome == "failed",
                "model_text_before": response.get("text", ""),
                "thinking_before": response.get("thinking", []),
                "capture_scope": payload.capture_scope,
            })
    _relative_times(steps, origin)
    return {
        "source_format": "event_envelope_jsonl",
        "run": events[0].run_id,
        "invocations": [{"invocation": 1, "stream": path.name, "steps": steps}],
        "model": None,
        "elapsed_seconds": (max(origins) - min(origins)) if origins else None,
        "usage": usage,
        "visible_text": texts,
        "requests": requests,
        "responses": response_records,
        "events": [event.model_dump(mode="json") for event in events],
        "event_counts": dict(Counter(event.payload.event_type for event in events)),
        "gaps": [],
        "source_files": [str(path)],
    }


def _legacy_streams(run: Path) -> list[Path]:
    compressed = sorted(p for p in run.glob("*_stream.jsonl.gz") if p.stat().st_size)
    plain = sorted(p for p in run.glob("*_stream.jsonl")
                   if p.stat().st_size and p.with_suffix(".jsonl.gz") not in compressed)
    return sorted(compressed + plain, key=lambda item: item.name)


def _read_cli_stream(path: Path, invocation: int) -> dict[str, Any]:
    opener = gzip.open(path, "rt") if path.suffix == ".gz" else path.open()
    with opener as stream:
        events = [json.loads(line) for line in stream if line.strip()]
    origin = next((_stamp(e["timestamp"]) for e in events if e.get("timestamp")), None)
    steps: list[dict[str, Any]] = []
    pending: dict[str, dict[str, Any]] = {}
    texts: list[str] = []
    thinking = 0
    usage: dict[str, dict[str, Any]] = {}
    init: dict[str, Any] = {}
    result: dict[str, Any] = {}
    last = origin
    for event in events:
        if event.get("timestamp"):
            last = _stamp(event["timestamp"])
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            init = {key: event.get(key) for key in
                    ("model", "claude_code_version", "apiKeySource", "permissionMode")}
        elif kind == "system" and event.get("subtype") == "thinking_tokens":
            thinking += int(event.get("estimated_tokens_delta") or 0)
        elif kind == "assistant":
            message = event.get("message") or {}
            if message.get("id") and message.get("usage"):
                previous = usage.get(message["id"], {})
                current = message["usage"]
                if (current.get("output_tokens") or 0) >= (previous.get("output_tokens") or 0):
                    usage[message["id"]] = current
            for block in message.get("content") or []:
                if block.get("type") == "text" and block.get("text"):
                    texts.append(block["text"])
                elif block.get("type") == "tool_use":
                    step = {
                        "index": len(steps) + 1,
                        "_absolute_time": last,
                        "tool": block["name"].replace("mcp__bim__", ""),
                        "arguments": block.get("input") or {},
                        "model_text_before": "\n\n".join(texts),
                        "thinking_tokens_before": thinking,
                    }
                    texts, thinking = [], 0
                    pending[block["id"]] = step
                    steps.append(step)
        elif kind == "user":
            content = (event.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                step = pending.pop(block.get("tool_use_id"), None)
                if step is None:
                    continue
                parts = block.get("content")
                parts = parts if isinstance(parts, list) else [{"type": "text", "text": str(parts or "")}]
                text = "\n".join(item.get("text", "") for item in parts if item.get("type") == "text")
                images = []
                for item in parts:
                    if item.get("type") != "image":
                        continue
                    source = item.get("source") or {}
                    raw = base64.b64decode(source.get("data") or "")
                    images.append({"media_type": source.get("media_type"), "bytes": len(raw),
                                   "sha256": hashlib.sha256(raw).hexdigest()})
                step.update(result_text=text, result_images=images,
                            model_visible_result=_json(text),
                            delivered_to_model=True, delivery_evidence="CLI tool_result message",
                            is_error=bool(block.get("is_error")), outcome=("failed" if block.get("is_error") else "succeeded"))
        elif kind == "result":
            result = {key: event.get(key) for key in
                      ("subtype", "is_error", "num_turns", "duration_ms", "total_cost_usd",
                       "stop_reason", "terminal_reason", "result", "usage", "modelUsage")}
    for step in pending.values():
        step.update(result_text=None, model_visible_result=None,
                    delivered_to_model=False, is_error=None, outcome="unknown", unanswered=True)
    _relative_times(steps, origin)
    return {"invocation": invocation, "stream": path.name, "steps": steps, "init": init,
            "message_usage": list(usage.values()), "result": result,
            "final_text_after_last_tool": "\n\n".join(texts),
            "trailing_thinking_tokens": thinking}


def _read_cli(run: Path) -> dict[str, Any]:
    invocations = [_read_cli_stream(path, number)
                   for number, path in enumerate(_legacy_streams(run), 1)]
    receipt_path = next(iter(sorted(run.glob("*_receipt.json"))), None)
    receipt = json.loads(receipt_path.read_text()) if receipt_path else {}
    return {
        "source_format": "claude_cli_stream",
        "run": run.name,
        "invocations": invocations,
        "model": receipt.get("actual_model") or (invocations[0].get("init") or {}).get("model"),
        "elapsed_seconds": receipt.get("elapsed_seconds"),
        "usage": [row for inv in invocations for row in inv["message_usage"]],
        "visible_text": [step["model_text_before"] for inv in invocations for step in inv["steps"]
                         if step.get("model_text_before")],
        "gaps": [
            "CLI launch request is not the final provider request body.",
            "Tool results are the CLI-visible transformed results, not guaranteed raw MCP bytes.",
            "Thinking content is unavailable; only CLI-estimated token deltas and signatures may exist.",
        ],
        "source_files": [str(path) for path in _legacy_streams(run)] + ([str(receipt_path)] if receipt_path else []),
    }


def _read_bridge(run: Path) -> dict[str, Any]:
    tool_path = run / "tools.jsonl"
    rows = [json.loads(line) for line in tool_path.read_text().splitlines() if line.strip()]
    origin = min((float(row["time"]) for row in rows if row.get("time") is not None), default=None)
    steps = []
    for row in rows:
        data = row.get("data") or {}
        action = row.get("action", "unknown")
        # The audit stream records returned data, not original arguments.  Keep a few
        # unambiguous selectors useful for behaviour metrics and disclose the rest.
        arguments = {}
        for key in ("name", "image", "box", "candidate", "topic", "facade", "floor_id"):
            if key in data:
                arguments[key] = data[key]
        steps.append({"index": len(steps) + 1, "_absolute_time": row.get("time"),
                      "tool": action, "arguments": arguments, "model_visible_result": data,
                      "delivered_to_model": True,
                      "delivery_evidence": "legacy result-side audit; exact transport unverified",
                      "is_error": bool(data.get("error")),
                      "outcome": "failed" if data.get("error") else "succeeded",
                      "arguments_capture": "historical_result_only"})
    _relative_times(steps, origin)
    controller = run / "controller_receipt.json"
    receipt = json.loads(controller.read_text()) if controller.is_file() else {}
    dev_calls = run / "dev_calls.jsonl"
    sources = [str(tool_path)] + ([str(dev_calls)] if dev_calls.is_file() else []) + ([str(controller)] if controller.is_file() else [])
    return {
        "source_format": "legacy_bridge_audit",
        "run": run.name,
        "invocations": [{"invocation": 1, "stream": tool_path.name, "steps": steps}],
        "model": receipt.get("provider_actual_model_receipt") or receipt.get("requested_model"),
        "elapsed_seconds": receipt.get("elapsed_seconds_to_final_tool"),
        "usage": [],
        "visible_text": [],
        "gaps": [
            "Bridge tools.jsonl stores result-side audit rows, not complete call arguments or model-visible transport.",
            "Final provider request/response, visible model text, thinking and per-message usage were not archived.",
            "Requested model is retained when present; provider actual-model identity is unverified when its receipt is absent.",
        ],
        "source_files": sources,
    }


def load_behaviour(path: str | Path) -> dict[str, Any]:
    """Load a run directory, current ``events.jsonl``, CLI stream, or bridge audit."""
    path = Path(path)
    if path.is_dir() and (path / "events.jsonl").is_file():
        record = _read_event_log(path / "events.jsonl")
    elif path.is_file() and path.name == "events.jsonl":
        record = _read_event_log(path)
    elif path.is_dir() and _legacy_streams(path):
        record = _read_cli(path)
    elif path.is_dir() and (path / "tools.jsonl").is_file():
        record = _read_bridge(path)
    else:
        raise ValueError(f"no supported behaviour log found at {path}")
    record["_source_root"] = str(path if path.is_dir() else path.parent)
    record["summary"] = summarise(record)
    record.pop("_source_root")
    return record


def _view_detail(step: dict[str, Any]) -> dict[str, Any]:
    arguments = step.get("arguments") or {}
    visible = step.get("model_visible_result")
    result = visible if isinstance(visible, dict) else {}
    box = result.get("box_original_pixels") or arguments.get("box")
    size = result.get("original_size")
    scale = result.get("display_scale_actual")
    if isinstance(scale, list):
        scale = min(scale)
    return {"image": arguments.get("name") or result.get("name"), "box": box, "scale": scale,
            "full": bool(size) and box in (None, [0, 0, *size])}


def _polygon_centroid(points: list[list[float]]) -> tuple[float, float] | None:
    if len(points) < 3:
        return None
    area2 = sum(a[0] * b[1] - b[0] * a[1]
                for a, b in zip(points, points[1:] + points[:1]))
    if abs(area2) < 1e-12:
        return None
    x = sum((a[0] + b[0]) * (a[0] * b[1] - b[0] * a[1])
            for a, b in zip(points, points[1:] + points[:1])) / (3 * area2)
    y = sum((a[1] + b[1]) * (a[0] * b[1] - b[0] * a[1])
            for a, b in zip(points, points[1:] + points[:1])) / (3 * area2)
    return x, y


def _opening_facades(run: Path, candidate: Any, identities: set[str]) -> dict[str, str]:
    path = run / str(candidate or "") / "source_model.json"
    if not candidate or not path.is_file():
        return {}
    try:
        source = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    centres = {row["id"]: _polygon_centroid(row.get("polygon") or [])
               for row in source.get("spaces", [])}
    found: dict[str, str] = {}
    for opening in source.get("openings", []):
        if (opening.get("id") not in identities or not opening.get("exterior")
                or not opening.get("space_ids")):
            continue
        centre = centres.get(opening["space_ids"][0])
        vertices = opening.get("vertices") or []
        if centre is None or not vertices:
            continue
        xs, ys = [row[0] for row in vertices], [row[1] for row in vertices]
        x, y = sum(xs) / len(xs), sum(ys) / len(ys)
        if max(xs) - min(xs) >= max(ys) - min(ys):
            found[opening["id"]] = "north" if y > centre[1] else "south"
        else:
            found[opening["id"]] = "east" if x > centre[0] else "west"
    return found


def _claim_detail(step: dict[str, Any], run: Path) -> dict[str, Any]:
    arguments = step.get("arguments") or {}
    visible = step.get("model_visible_result")
    result = visible if isinstance(visible, dict) else {}
    claim = result.get("claim") or arguments
    objects = [item.get("id") for item in claim.get("objects") or [] if isinstance(item, dict)]
    sources = [item.get("image") for item in result.get("sources") or [] if isinstance(item, dict)]
    source_facades = sorted({name for name in map(_facade, sources) if name})
    targets = sorted(set(_opening_facades(run, claim.get("candidate"), set(objects)).values()))
    return {"id": result.get("id"), "objects": objects, "sources": sources,
            "resolved": result.get("resolved_values"), "source_facades": source_facades,
            "target_facades": targets,
            "cross_facade": bool(targets and source_facades and set(targets) - set(source_facades)),
            "reason": claim.get("reason"), "t": step.get("t_call")}


def summarise(record: dict[str, Any]) -> dict[str, Any]:
    steps = [step for invocation in record["invocations"] for step in invocation["steps"]]
    tools = Counter(step["tool"] for step in steps)
    first = next((step.get("t_call") for step in steps if step["tool"] in FIRST_DRAFT_TOOLS), None)
    views = [dict(_view_detail(step), t=step.get("t_call")) for step in steps
             if step["tool"] == "view_image" and step.get("delivered_to_model", True)]
    before = [step for step in steps if first is None or (step.get("t_call") is not None and step["t_call"] < first)]
    views_before = [view for view in views if first is None or (view.get("t") is not None and view["t"] < first)]
    crops = [view for view in views if not view["full"]]
    overlays = Counter(_facade((step.get("arguments") or {}).get("image") or
                               (step.get("arguments") or {}).get("name") or
                               (step.get("model_visible_result") or {}).get("facade"))
                       for step in steps if step["tool"] == "view_elevation_candidate")
    run = Path(record.get("_source_root", "."))
    claims = [_claim_detail(step, run) for step in steps
              if step["tool"] == "record_claim" and not step.get("is_error")
              and step.get("delivered_to_model", True)]
    height_sources = Counter(name for claim in claims for name in claim["source_facades"])
    return {
        "run": record["run"], "source_format": record["source_format"], "model": record.get("model"),
        "elapsed_seconds": record.get("elapsed_seconds"), "tool_calls": len(steps),
        "tool_errors": sum(bool(step.get("is_error")) for step in steps), "tools": dict(tools),
        "prepared_tool_results": sum("prepared_result" in step for step in steps),
        "delivered_tool_results": sum(step.get("delivered_to_model") is True for step in steps),
        "undelivered_tool_results": sum(step.get("delivered_to_model") is False for step in steps),
        "first_draft_s": first, "calls_before_first_draft": len(before),
        "full_views_before_first_draft": sum(view["full"] for view in views_before),
        "crops_before_first_draft": sum(not view["full"] for view in views_before),
        "pixel_tools_before_first_draft": sum("pixel" in step["tool"] for step in before),
        "elevation_crops_by_facade": dict(Counter(name for name in map(lambda row: _facade(row["image"]), crops) if name)),
        "elevation_overlays_by_facade": {key: value for key, value in overlays.items() if key},
        "height_provenance_claims": claims, "height_provenance_facades": dict(height_sources),
        "cross_facade_height_claims": sum(claim["cross_facade"] for claim in claims),
        "plan_builds": sum(tools[name] for name in FIRST_DRAFT_TOOLS),
        "candidate_revisions": tools["revise_bim"], "gaps": record["gaps"],
    }


def _short(value: Any, limit: int = 180) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = re.sub(r"\s+", " ", text or "")
    return text if len(text) <= limit else text[:limit] + f" …(+{len(text) - limit})"


def render_timeline(record: dict[str, Any]) -> str:
    summary = record["summary"]
    lines = [f"# 行为记录：{summary['run']}", "",
             f"来源格式 `{summary['source_format']}`；型号 `{summary['model'] or '未核实'}`；"
             f"{summary['tool_calls']} 次工具调用（报错 {summary['tool_errors']}）；"
             f"首稿 {summary['first_draft_s']} 秒。", ""]
    if summary["gaps"]:
        lines += ["## 历史缺口", ""] + [f"- {gap}" for gap in summary["gaps"]] + [""]
    for invocation in record["invocations"]:
        lines += [f"## 调用 {invocation['invocation']}（{invocation['stream']}）", "",
                  "| # | 时间 s | 工具 | 参数 | 返回 |", "|---:|---:|---|---|---|"]
        for step in invocation["steps"]:
            lines.append(f"| {step['index']} | {step.get('t_call')} | {step['tool']} | "
                         f"{_short(step.get('arguments')).replace('|', '/')} | "
                         f"{_short(step.get('model_visible_result')).replace('|', '/')} |")
        lines.append("")
    return "\n".join(lines)


def write_behaviour_report(path: str | Path, out: str | Path) -> dict[str, Any]:
    record = load_behaviour(path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(record["summary"], ensure_ascii=False, indent=2) + "\n")
    (out / "timeline.md").write_text(render_timeline(record) + "\n")
    with gzip.open(out / "record.json.gz", "wt", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=1)
    return record["summary"]
