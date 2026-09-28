"""Read-only survey of runs 53-83: inputs, request, receipt, tool actions, delivery, GT partition.

Usage: python survey_runs.py  (writes runs_survey.json / runs_survey.md next to this file)
Only public request/receipt/tool fields are read; stream thinking fields are never opened.
"""
import collections
import glob
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def load(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def receipt_fields(rec):
    if not rec:
        return {}
    res = rec.get("result") or {}
    usage = res.get("usage") or {}
    return {
        "actual_model": rec.get("actual_model"),
        "effort": rec.get("effort"),
        "elapsed_s": rec.get("elapsed_seconds"),
        "returncode": rec.get("returncode"),
        "subtype": res.get("subtype"),
        "terminal_reason": res.get("terminal_reason"),
        "is_error": res.get("is_error"),
        "api_error_status": res.get("api_error_status"),
        "num_turns": res.get("num_turns"),
        "cost_usd": res.get("total_cost_usd"),
        "output_tokens": usage.get("output_tokens"),
        "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
        "cache_read": usage.get("cache_read_input_tokens"),
        "subagents": (res.get("subagent_stats") or {}).get("spawned"),
    }


def partition_eval(run_dir, candidate):
    if not candidate:
        return None
    part = load(os.path.join(run_dir, "evaluation", "gt", f"{candidate}_partition.json"))
    if not part:
        return None
    comp = part.get("comparison") or {}
    matches = comp.get("matches") or []
    statuses = collections.Counter(m.get("status") for m in matches)
    internal = part.get("internal_boundary_comparison") or []
    return {
        "status": part.get("status"),
        "ref": comp.get("reference_count"),
        "cand": comp.get("candidate_count"),
        "matched": comp.get("matched_count"),
        "match_status": dict(statuses),
        "topology_findings": len(part.get("topology_findings") or []),
        "missing_int_m": round(sum(x.get("missing_length_m") or 0 for x in internal), 2),
        "extra_int_m": round(sum(x.get("extra_length_m") or 0 for x in internal), 2),
    }


def window_eval(run_dir, candidate):
    if not candidate:
        return None
    win = load(os.path.join(run_dir, "evaluation", "gt", f"{candidate}_windows.json"))
    if not win:
        return None
    gt = read = 0
    statuses = collections.Counter()
    for floors in (win.get("scores") or {}).values():
        for score in floors.values():
            gt += score.get("gt_count") or 0
            read += score.get("read_count") or 0
            for match in score.get("matches") or []:
                statuses[match.get("status")] += 1
    return {"gt": gt, "read": read, "status": dict(statuses)}


def tool_actions(run_dir):
    counts = collections.Counter()
    first = None
    last = None
    path = os.path.join(run_dir, "tools.jsonl")
    if not os.path.exists(path):
        return {}, 0, None
    with open(path) as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            counts[row.get("action")] += 1
            first = first or row.get("time")
            last = row.get("time")
    span = round(last - first, 1) if first and last else None
    return dict(counts), sum(counts.values()), span


def main():
    rows = []
    for run_dir in sorted(glob.glob(os.path.join(EXP, "*_run[0-9][0-9]"))):
        match = re.search(r"run(\d+)$", run_dir)
        num = int(match.group(1))
        if not 53 <= num <= 83:
            continue
        name = os.path.basename(run_dir)
        case = re.search(r"_(sm\d+)_", name).group(1)
        req = load(os.path.join(run_dir, "agent_request.json")) or {}
        rec = load(os.path.join(run_dir, "agent_receipt.json"))
        inputs = load(os.path.join(run_dir, "inputs.json")) or {}
        summary = load(os.path.join(run_dir, "summary.json")) or {}
        cont = load(os.path.join(run_dir, "continuation.json"))
        images = inputs.get("images") or {}
        image_set = sha(json.dumps(sorted((k, v.get("sha256")) for k, v in images.items())))
        delivery = summary.get("delivery") or {}
        cand = delivery.get("candidate")
        dcounts = None
        for item in summary.get("candidate_results") or []:
            if item.get("candidate") == cand:
                dcounts = item.get("counts")
        actions, n_actions, span = tool_actions(run_dir)
        cont_receipts = []
        for path in sorted(glob.glob(os.path.join(run_dir, "continuation_*_receipt.json"))):
            cont_receipts.append(receipt_fields(load(path)))
        rows.append({
            "run": num,
            "dir": name,
            "case": case,
            "seeded": os.path.isdir(os.path.join(run_dir, "seed")),
            "image_set": image_set,
            "n_images": len(images),
            "scope_sha": sha(inputs.get("scope") or ""),
            "requested_model": req.get("requested_model"),
            "effort": req.get("effort"),
            "timeout_s": req.get("timeout_seconds"),
            "prompt_sha": sha(req.get("prompt") or ""),
            "prompt_len": len(req.get("prompt") or ""),
            "system_sha": sha(req.get("system_prompt") or ""),
            "system_len": len(req.get("system_prompt") or ""),
            "receipt": receipt_fields(rec),
            "continuations": cont_receipts,
            "continuation_turns": len((cont or {}).get("turns") or []),
            "delivery_candidate": cand,
            "selection_origin": delivery.get("selection_origin"),
            "n_candidates": len(summary.get("candidate_results") or []),
            "delivery_counts": dcounts,
            "partition": partition_eval(run_dir, cand),
            "windows": window_eval(run_dir, cand),
            "tool_actions": actions,
            "n_tool_actions": n_actions,
            "tool_span_s": span,
        })
    with open(os.path.join(HERE, "runs_survey.json"), "w") as handle:
        json.dump(rows, handle, indent=1, ensure_ascii=False)
    lines = [
        "| run | case | seed | imgset | model/effort | elapsed | end | turns | out_tok | sys_sha/len | prompt_sha/len | tools | cands | deliv | spaces/open/conn | GT part ref/cand/match | int miss/extra m | win gt/read |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        rc = r["receipt"]
        dc = r["delivery_counts"] or {}
        pt = r["partition"] or {}
        wn = r["windows"] or {}
        lines.append(
            f"| {r['run']} | {r['case']} | {'Y' if r['seeded'] else ''} | {r['image_set'][:6]} | "
            f"{rc.get('actual_model')}/{rc.get('effort')} | {rc.get('elapsed_s')} | "
            f"{rc.get('subtype')}/{rc.get('api_error_status')} | {rc.get('num_turns')} | {rc.get('output_tokens')} | "
            f"{r['system_sha'][:6]}/{r['system_len']} | {r['prompt_sha'][:6]}/{r['prompt_len']} | {r['n_tool_actions']} | "
            f"{r['n_candidates']} | {r['delivery_candidate']} | {dc.get('spaces')}/{dc.get('openings')}/{dc.get('connections')} | "
            f"{pt.get('status')} {pt.get('ref')}/{pt.get('cand')}/{pt.get('matched')} | {pt.get('missing_int_m')}/{pt.get('extra_int_m')} | "
            f"{wn.get('gt')}/{wn.get('read')} |"
        )
    with open(os.path.join(HERE, "runs_survey.md"), "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
