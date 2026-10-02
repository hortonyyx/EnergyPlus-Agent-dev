"""Complete behaviour record of one BIM agent run, for run-to-run comparison.

Offline, no model calls. Reads the run's raw CLI stream(s) and receipt and writes
records/<run>/:
- record.json.gz: every step in order - time, tool, full arguments, full text result (images
  reduced to type/size/sha256), error flag, the model's visible text and the thinking-token
  estimate before it - plus per-message token usage and every quota-window reading;
- timeline.md: the same steps as a readable table (long arguments shortened, full in JSON);
- summary.json: the comparison metrics read by compare.py.
The CLI stream carries thinking only as signed empty blocks, so thinking is kept as token
counts; everything the model did through tools and every result it saw is kept in full.
User request 10-01: "从现在开始模型行为要完全记录，这样方便后续比对".
"""
import argparse
import base64
from collections import Counter
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
FACADES = ("north", "south", "east", "west")
PLAN_BUILD = {"build_plan_bim", "build_bim"}
PLAN_EDIT = {"revise_plan_bim", "edit_plan_bim"}


def facade(image):
    name = str(image or "").lower()
    return next((f for f in FACADES if f in name), None)


def stamp(text):
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def parse(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def streams(run):
    found = sorted(run.glob("*_stream.jsonl.gz")) + sorted(
        p for p in run.glob("*_stream.jsonl") if not p.with_suffix(".jsonl.gz").exists())
    return sorted(found, key=lambda p: p.name)


def read_stream(path, invocation):
    opener = gzip.open(path, "rt") if path.suffix == ".gz" else path.open()
    with opener as handle:
        events = [json.loads(line) for line in handle if line.strip()]
    t0 = next((stamp(e["timestamp"]) for e in events if e.get("timestamp")), None)
    steps, pending, texts, thinking, last_t = [], {}, [], 0, 0.0
    usage, quota, init, result = {}, [], {}, {}
    for event in events:
        kind = event.get("type")
        if event.get("timestamp") and t0 is not None:
            last_t = round(stamp(event["timestamp"]) - t0, 1)
        if kind == "system" and event.get("subtype") == "init":
            init = {k: event.get(k) for k in ("model", "claude_code_version", "apiKeySource", "permissionMode")}
        elif kind == "system" and event.get("subtype") == "thinking_tokens":
            thinking += int(event.get("estimated_tokens_delta") or 0)
        elif kind == "rate_limit_event":
            info = event.get("rate_limit_info") or {}
            windows = info.get("unifiedWindows") or {}
            quota.append(dict(t=last_t, status=info.get("status"),
                              five_hour=(windows.get("five_hour") or {}).get("utilization"),
                              seven_day=(windows.get("seven_day") or {}).get("utilization")))
        elif kind == "assistant":
            message = event.get("message") or {}
            if message.get("id") and message.get("usage"):
                previous = usage.get(message["id"], {})
                if (message["usage"].get("output_tokens") or 0) >= (previous.get("output_tokens") or 0):
                    usage[message["id"]] = dict(message["usage"], t=last_t)
            for block in message.get("content") or []:
                if block.get("type") == "text" and block.get("text"):
                    texts.append(block["text"])
                elif block.get("type") == "tool_use":
                    step = dict(invocation=invocation, index=len(steps) + 1, t_call=last_t,
                                tool=block["name"].replace("mcp__bim__", ""), arguments=block.get("input"),
                                model_text_before="\n\n".join(texts), thinking_tokens_before=thinking)
                    texts, thinking = [], 0
                    pending[block["id"]] = step
                    steps.append(step)
        elif kind == "user":
            content = (event.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                    continue
                step = pending.pop(block.get("tool_use_id"), None)
                if step is None:
                    continue
                parts = block.get("content")
                parts = parts if isinstance(parts, list) else [dict(type="text", text=str(parts or ""))]
                text = "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")
                images = []
                for p in parts:
                    if p.get("type") == "image":
                        data = (p.get("source") or {}).get("data") or ""
                        raw = base64.b64decode(data) if data else b""
                        images.append(dict(media_type=(p.get("source") or {}).get("media_type"),
                                           bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
                step.update(t_result=last_t, is_error=bool(block.get("is_error")), result_text=text,
                            result_images=images)
        elif kind == "result":
            result = {k: event.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms",
                                                "total_cost_usd", "stop_reason", "terminal_reason", "result")}
            result["usage"], result["modelUsage"] = event.get("usage"), event.get("modelUsage")
    for step in pending.values():
        step.update(t_result=None, is_error=None, result_text=None, result_images=[], unanswered=True)
    return dict(invocation=invocation, stream=path.name, init=init, steps=steps,
                final_text_after_last_tool="\n\n".join(texts), trailing_thinking_tokens=thinking,
                message_usage=list(usage.values()), quota=quota, result=result)


def view_detail(step):
    data = parse(step.get("result_text")) or {}
    box = data.get("box_original_pixels") or step["arguments"].get("box")
    scale = data.get("display_scale_actual")
    if isinstance(scale, list):
        scale = min(scale)
    size = data.get("original_size")
    full = bool(size) and box in (None, [0, 0, *size])
    return dict(image=step["arguments"].get("name"), box=box, scale=scale, full=full)


def opening_facades(run, candidate, ids):
    """Facade of each exterior opening from saved geometry: wall direction from the opening's
    vertices, outward side away from its host space centroid (+Y north, +X east)."""
    path = run / str(candidate or "") / "source_model.json"
    if not candidate or not path.is_file():
        return {}
    from shapely.geometry import Polygon
    source = json.loads(path.read_text())
    spaces = {s["id"]: Polygon(s["polygon"]).centroid for s in source.get("spaces", [])}
    found = {}
    for opening in source.get("openings", []):
        if opening["id"] not in ids or not opening.get("exterior") or not opening.get("space_ids"):
            continue
        xs = [v[0] for v in opening["vertices"]]
        ys = [v[1] for v in opening["vertices"]]
        centre, x, y = spaces.get(opening["space_ids"][0]), sum(xs) / len(xs), sum(ys) / len(ys)
        if centre is None:
            continue
        if max(xs) - min(xs) >= max(ys) - min(ys):
            found[opening["id"]] = "north" if y > centre.y else "south"
        else:
            found[opening["id"]] = "east" if x > centre.x else "west"
    return found


def claim_detail(step, run):
    data = parse(step.get("result_text")) or {}
    claim = data.get("claim") or step["arguments"]
    objects = [o.get("id") for o in claim.get("objects") or []]
    sources = [s.get("image") for s in data.get("sources") or []]
    by_geometry = opening_facades(run, claim.get("candidate"), set(objects))
    applied = [a for v in (data.get("facts") or {}).get("values") or [] for a in v.get("applied_to") or []]
    hosts = sorted(set(by_geometry.values()) or {str(a.get("host")).lower() for a in applied if a.get("host")})
    source_facades = sorted({f for f in map(facade, sources) if f})
    return dict(id=data.get("id"), objects=objects, sources=sources, resolved=data.get("resolved_values"),
                source_facades=source_facades, target_facades=hosts,
                cross_facade=bool(hosts and source_facades and set(hosts) - set(source_facades)),
                reason=claim.get("reason"))


def summarise(run, invocations, receipt):
    steps = [s for inv in invocations for s in inv["steps"]]
    tools = Counter(s["tool"] for s in steps)
    first_build = next((s["t_call"] for s in steps if s["tool"] in PLAN_BUILD), None)
    assembled = next((s["t_call"] for s in steps if s["tool"] == "assemble_plan_bim" and not s.get("is_error")), None)
    finish = max((s["t_call"] for s in steps if s["tool"] == "finish_bim"), default=None)
    views = [dict(view_detail(s), t=s["t_call"]) for s in steps if s["tool"] == "view_image"]
    before = [s for s in steps if first_build is None or s["t_call"] < first_build]
    views_before = [v for v in views if first_build is None or v["t"] < first_build]
    crops = [v for v in views if not v["full"]]
    elevation_crops = Counter(facade(v["image"]) for v in crops if facade(v["image"]))
    overlays = Counter(facade((s["arguments"] or {}).get("image") or (s["arguments"] or {}).get("name"))
                       for s in steps if s["tool"] == "view_elevation_candidate")
    claims = [dict(claim_detail(s, run), t=s["t_call"]) for s in steps if s["tool"] == "record_claim" and not s.get("is_error")]
    errors = [dict(t=s["t_call"], tool=s["tool"], text=(s.get("result_text") or "")[:300])
              for s in steps if s.get("is_error")]
    model_usage = {}
    for inv in invocations:
        for name, row in ((inv["result"] or {}).get("modelUsage") or {}).items():
            agg = model_usage.setdefault(name, Counter())
            for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens",
                        "thinkingTokens", "costUSD"):
                agg[key] += row.get(key) or 0
    quota = [q for inv in invocations for q in inv["quota"]]
    five = [q["five_hour"] for q in quota if q["five_hour"] is not None]
    texts = [s["model_text_before"] for s in steps if s["model_text_before"]]
    texts += [inv["final_text_after_last_tool"] for inv in invocations if inv["final_text_after_last_tool"]]
    return dict(
        run=run.name, invocations=len(invocations),
        model=receipt.get("actual_model") or (invocations[0]["init"] or {}).get("model"),
        cli=(invocations[0]["init"] or {}).get("claude_code_version"),
        elapsed_seconds=receipt.get("elapsed_seconds"),
        turns=sum((inv["result"] or {}).get("num_turns") or 0 for inv in invocations),
        tool_calls=len(steps), tool_errors=len(errors), tools=dict(tools),
        references=[(s["arguments"] or {}).get("topic") for s in steps if s["tool"] == "get_bim_reference"],
        first_build_s=first_build, first_assembly_s=assembled, finish_s=finish,
        calls_before_first_build=len(before),
        full_views_before_first_build=sum(v["full"] for v in views_before),
        crops_before_first_build=sum(not v["full"] for v in views_before),
        pixel_tools_before_first_build=sum("pixel" in s["tool"] for s in before),
        crop_scales=sorted(round(v["scale"], 2) for v in crops if isinstance(v["scale"], (int, float))),
        elevation_crops_by_facade=dict(elevation_crops),
        elevation_crops_after_first_build=sum(1 for v in crops if facade(v["image"]) and first_build is not None
                                              and v["t"] >= first_build),
        elevation_overlays_by_facade=dict(overlays),
        plan_builds=tools["build_plan_bim"] + tools["build_bim"], plan_edits=sum(tools[t] for t in PLAN_EDIT),
        candidate_revisions=tools["revise_bim"],
        claims=claims, cross_facade_claims=sum(c["cross_facade"] for c in claims),
        errors=errors, model_usage={k: dict(v) for k, v in model_usage.items()},
        cost_usd_cli=sum((inv["result"] or {}).get("total_cost_usd") or 0 for inv in invocations),
        thinking_tokens_estimated=sum(s["thinking_tokens_before"] for s in steps)
        + sum(inv["trailing_thinking_tokens"] for inv in invocations),
        visible_text_chars=sum(len(t) for t in texts),
        five_hour_window=[five[0], five[-1]] if five else None,
        final_text=(invocations[-1]["result"] or {}).get("result"))


def short(value, limit=160):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = re.sub(r"\s+", " ", text or "")
    return text if len(text) <= limit else text[:limit] + f" …(+{len(text) - limit})"


def key_arguments(step):
    args = step["arguments"] or {}
    if step["tool"] == "view_image":
        detail = view_detail(step)
        return f"{detail['image']} box={detail['box']} x{detail['scale']}"
    return short(args)


def result_summary(step):
    if step.get("unanswered"):
        return "(no result)"
    data = parse(step.get("result_text"))
    prefix = "ERROR " if step.get("is_error") else ""
    if isinstance(data, dict):
        keys = [k for k in ("status", "candidate", "candidate_id", "id", "draft_id", "drawing_differences",
                            "resolved_values", "errors", "warnings") if k in data]
        picked = {k: data[k] for k in keys}
        if isinstance(picked.get("drawing_differences"), dict):
            dd = picked["drawing_differences"]
            picked["drawing_differences"] = {k: dd[k] for k in dd if k in ("count", "total", "items", "status")}
        text = short(picked or data, 200)
    else:
        text = short(step.get("result_text"), 200)
    images = f" [+{len(step['result_images'])} image]" if step.get("result_images") else ""
    return prefix + text + images


def timeline(summary, invocations):
    lines = [f"# 行为记录：{summary['run']}", "",
             f"型号 {summary['model']}，CLI {summary['cli']}，{summary['elapsed_seconds']} 秒，"
             f"{summary['turns']} 轮，{summary['tool_calls']} 次工具调用（报错 {summary['tool_errors']}），"
             f"CLI 估价 {summary['cost_usd_cli']:.2f} 美元（非账单），思考约 {summary['thinking_tokens_estimated']} token，"
             f"5 小时窗口 {summary['five_hour_window']}。思考内容 CLI 不提供，仅记数量；完整参数与返回见 record.json.gz。", ""]
    for inv in invocations:
        lines += [f"## 调用 {inv['invocation']}（{inv['stream']}）", "",
                  "| # | 时间 s | 工具 | 主要参数 | 返回 | 之前的思考 token / 模型文字 |", "|---|---|---|---|---|---|"]
        for step in inv["steps"]:
            said = short(step["model_text_before"], 400).replace("|", "/")
            lines.append(f"| {step['index']} | {step['t_call']} | {step['tool']} | "
                         f"{key_arguments(step).replace('|', '/')} | {result_summary(step).replace('|', '/')} | "
                         f"{step['thinking_tokens_before']} / {said} |")
        if inv["final_text_after_last_tool"]:
            lines += ["", "最终回复：", "", inv["final_text_after_last_tool"]]
        lines.append("")
    return "\n".join(lines)


def record(run):
    run = run if run.is_absolute() else EXPERIMENTS / run
    receipt_path = next(iter(sorted(run.glob("*_receipt.json"))), None)
    receipt = json.loads(receipt_path.read_text()) if receipt_path else {}
    invocations = [read_stream(path, i) for i, path in enumerate(streams(run), 1)]
    if not invocations:
        raise SystemExit(f"{run.name}: no CLI stream to record")
    summary = summarise(run, invocations, receipt)
    out = HERE / "records" / run.name
    out.mkdir(parents=True, exist_ok=True)
    with gzip.open(out / "record.json.gz", "wt") as handle:
        json.dump(dict(run=run.name, receipt=receipt, invocations=invocations), handle, ensure_ascii=False, indent=1)
    (out / "timeline.md").write_text(timeline(summary, invocations))
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run directory names under logs/experiments")
    for name in parser.parse_args().runs:
        s = record(Path(name))
        print(json.dumps({k: s[k] for k in ("run", "model", "elapsed_seconds", "tool_calls", "tool_errors",
                                            "first_build_s", "cost_usd_cli", "five_hour_window")}, ensure_ascii=False))
