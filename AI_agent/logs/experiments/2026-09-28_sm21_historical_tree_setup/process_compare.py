"""Compare public tool actions and saved geometry, never private reasoning."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
load = lambda path: json.loads(path.read_text())
RUNS = ["2026-09-26_sm21_whole_building_claude_run57",
        "2026-09-27_sm21_whole_building_repeat_claude_run58",
        "2026-09-28_sm21_threshold_legacy_run79",
        "2026-09-28_sm21_threshold_current_run80",
        "2026-09-28_sm21_historical_tree_run81"]
PHYSICAL = {
    "floors": ["id", "footprint", "height", "z_floor"],
    "spaces": ["id", "floor_id", "polygon", "height", "z_floor"],
    "boundaries": ["id", "adjacent_space_ids", "counterpart_ids", "geometry_type", "kind", "space_id", "vertices"],
    "openings": ["id", "kind", "vertices", "space_ids", "host_boundary_id", "exterior", "connectivity"],
    "connections": ["opening_id", "kind", "space_ids", "exterior", "state"],
}


def analyze(run):
    assert load(run / "summary.json")["agent_response_completed"], "Only complete runs"
    calls, seen, pending = [], set(), {}
    path = run / "agent_stream.jsonl.gz"
    opener = gzip.open if path.exists() else open
    if not path.exists():
        path = run / "agent_stream.jsonl"
    with opener(path, "rt") as stream:
        for line in stream:
            parts = json.loads(line).get("message", {}).get("content", [])
            for part in parts if isinstance(parts, list) else []:
                if part.get("type") == "tool_use" and part["id"] not in seen:
                    seen.add(part["id"])
                    raw = part.get("input", {})
                    item = dict(ordinal=len(calls) + 1, tool=part["name"].removeprefix("mcp__bim__"),
                        tool_use_id=part["id"], input_summary={k: raw[k] for k in
                            ["name", "image", "candidate", "floor_id", "facade", "topic", "box", "axis", "rgb", "heights_only"] if k in raw})
                    for key in ["plan_json", "operations_json", "floors_json"]:
                        if key not in raw:
                            continue
                        try:
                            data = json.loads(raw[key]) if isinstance(raw[key], str) else raw[key]
                        except ValueError:
                            item["input_summary"][key] = "invalid JSON"
                            continue
                        if key == "plan_json" and isinstance(data, dict):
                            item["declaration"] = {k: data.get(k) for k in
                                ["floor_id", "z_floor", "ceiling_height", "x_anchors", "y_anchors", "footprint", "basis"]}
                            item["declaration"].update(partitions=len(data.get("partitions", [])),
                                openings=len(data.get("openings", [])), space_seeds=len(data.get("space_seeds", [])))
                        else:
                            item["input_summary"][key] = data
                    pending[part["id"]] = item
                    calls.append(item)
                elif part.get("type") == "tool_result" and part.get("tool_use_id") in pending:
                    item = pending[part["tool_use_id"]]
                    content = part.get("content", [])
                    texts = [p["text"] for p in content if p.get("type") == "text"] if isinstance(content, list) else [str(content)]
                    item["image_count"] = sum(p.get("type") == "image" for p in content) if isinstance(content, list) else 0
                    item["text_chars"] = sum(map(len, texts))
                    item["tool_error"] = bool(part.get("is_error"))
                    if item["tool_error"]:
                        item["error_texts"] = texts
                    for text in texts:
                        try:
                            value = json.loads(text)
                        except ValueError:
                            continue
                        if isinstance(value, dict):
                            if value.get("error"):
                                item["returned_error"] = value["error"]
                            if value.get("candidate"):
                                item["returned_candidate"] = value["candidate"]
                            if value.get("source_geometry_ready"):
                                item["saved_ready"] = True
                                item["counts"] = value.get("counts")
    candidates = []
    last_physical = None
    for path in sorted(run.glob("candidate_*/source_model.json")):
        source = load(path)
        physical = {kind: [{k: row.get(k) for k in fields} for row in source[kind]] for kind, fields in PHYSICAL.items()}
        candidates.append(dict(candidate=path.parent.name, floors=len(source["floors"]),
            spaces=len(source["spaces"]), openings=len(source["openings"]),
            roles=dict(Counter(s["role"] for s in source["spaces"])),
            physical_sha256=hashlib.sha256(json.dumps(physical, sort_keys=True).encode()).hexdigest(),
            same_physical_fields_as_previous=physical == last_physical if last_physical is not None else None))
        last_physical = physical
    first = next((item["ordinal"] for item in calls if item.get("saved_ready")), None)
    manifest, receipt = load(run / "inputs.json"), load(run / "agent_receipt.json")
    result = dict(run=run.name, elapsed_seconds=receipt["elapsed_seconds"],
        actual_model=receipt["actual_model"], candidate_limit=manifest.get("max_candidates", 6),
        tool_calls=len(calls), tools=dict(Counter(item["tool"] for item in calls)),
        first_ready_ordinal=first,
        tools_before_first_ready=dict(Counter(item["tool"] for item in calls if first and item["ordinal"] < first)),
        source_elevation_calls=[item for item in calls if item["tool"] == "view_elevation_candidate"],
        declarations=[item for item in calls if "declaration" in item],
        revisions=[item for item in calls if item["tool"] in ["revise_bim", "revise_plan_bim"]],
        tool_error_count=sum(bool(item.get("tool_error") or item.get("returned_error")) for item in calls),
        saved_candidates=candidates, timeline=calls,
        limit="Public tool requests/replies and saved physical fields only. Counts/order are diagnostic observations, not proof of cause or semantic understanding.")
    return result


if __name__ == "__main__":
    reports = [analyze(HERE.parent / name) for name in RUNS if (HERE.parent / name / "summary.json").exists()]
    (HERE / "process_comparison.json").write_text(json.dumps({"runs": reports, "model_calls": 0}, ensure_ascii=False, indent=2) + "\n")
    for row in reports:
        print(json.dumps({k: row[k] for k in ["run", "elapsed_seconds", "tool_calls", "first_ready_ordinal", "tools", "tool_error_count"]}, ensure_ascii=False))
