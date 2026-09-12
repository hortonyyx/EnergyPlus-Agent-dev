"""Post-generation source preservation and actual source-plan response audit."""
import base64
import gzip
import io
import json
from pathlib import Path
import sys
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.opening_review import facade_inventory

run = Path(sys.argv[1]).resolve()
read = lambda p: json.loads(p.read_text())
summary = read(run / "summary.json")
selected = summary["delivery"]["candidate"]
before = read(run / "seed/source_model.json")
after = read(run / selected / "source_model.json")

def keyed(rows, fields, key="id"):
    return {r[key]: {k:r.get(k) for k in fields} for r in rows}

door_fields = ["id", "kind", "vertices", "host_boundary_id", "space_ids", "exterior", "connectivity"]
doors = lambda source: keyed([o for o in source["openings"] if o["kind"] != "window"], door_fields)
checks = {
    "space_geometry_and_roles_preserved": keyed(before["spaces"], ["polygon", "floor_id", "z_floor", "height", "role"]) == keyed(after["spaces"], ["polygon", "floor_id", "z_floor", "height", "role"]),
    "boundaries_preserved": before["boundaries"] == after["boundaries"],
    "door_geometry_and_hosts_preserved": doors(before) == doors(after),
    "connections_preserved": before["connections"] == after["connections"],
    "no_unbuilt_openings": not after["unbuilt_openings"],
}
old_windows = {o["id"]:o for o in before["openings"] if o["kind"] == "window"}
new_windows = {o["id"]:o for o in after["openings"] if o["kind"] == "window"}
checks["existing_window_ids_retained"] = old_windows.keys() <= new_windows.keys()
stream = run / "agent_stream.jsonl"
opener = open
if not stream.exists():
    stream = run / "agent_stream.jsonl.gz"
    opener = gzip.open
calls, views, elevations, actions = {}, [], [], []
with opener(stream, "rt") as f:
    for line in f:
        event = json.loads(line)
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                actions.append({"name":block["name"], "tool_use_id":block["id"]})
                if block["name"].endswith("__view_candidate"):
                    calls[block["id"]] = ("plan", block["input"])
                elif block["name"].endswith("__view_elevation_candidate"):
                    calls[block["id"]] = ("elevation", block["input"])
            if block.get("type") != "tool_result" or block.get("tool_use_id") not in calls or block.get("is_error"):
                continue
            kind, args = calls[block["tool_use_id"]]
            blocks = [b for b in block["content"] if b.get("type") == "image"]
            assert len(blocks) == 1
            actual = Image.open(io.BytesIO(base64.b64decode(blocks[0]["source"]["data"]))).convert("RGB")
            name = ("plan_" + args["floor_id"].replace("/", "_") if kind == "plan"
                    else "elevation_" + args["facade"])
            saved = Image.open(run / args["candidate"] / (name + ".png")).convert("RGB")
            row = {**args, "actual_response_pixels_match": actual.size == saved.size and ImageChops.difference(actual, saved).getbbox() is None}
            if kind == "elevation":
                from src.agent.geometry.source_elevation_view import render_source_elevation
                source = read(run / args["candidate"] / "source_model.json")
                replay, metadata = render_source_elevation(source, args["facade"])
                row["source_render_replay_matches"] = replay.size == saved.size and ImageChops.difference(replay, saved).getbbox() is None
                row["source_model_sha256"] = metadata["source_model_sha256"]
                saved_metadata = read(run / args["candidate"] / (name + ".json"))
                text_blocks = [b for b in block["content"] if b.get("type") == "text"]
                row["metadata_response_matches_saved"] = len(text_blocks) == 1 and json.loads(text_blocks[0]["text"]) == saved_metadata
                row["source_render_metadata_matches"] = all(saved_metadata.get(k) == v for k,v in metadata.items())
                elevations.append(row)
            else:
                views.append(row)

report = {
    "selected_candidate":selected, "source_sha256":after["source_model_sha256"],
    "preservation_checks":checks,
    "windows": {"before":len(old_windows), "after":len(new_windows),
                "added":sorted(new_windows.keys()-old_windows.keys()),
                "removed":sorted(old_windows.keys()-new_windows.keys()),
                "changed":sorted(k for k in old_windows.keys() & new_windows.keys() if old_windows[k] != new_windows[k])},
    "source_facade_inventory":facade_inventory(after), "actual_source_plan_views":views,
    "actual_source_elevation_views":elevations,
    "selected_candidate_viewed":any(v["candidate"] == selected for v in views + elevations),
    "actual_tool_actions":actions,
    "limits":"Preservation and transport checks only. Image fidelity is evaluated separately; a plan cannot verify window heights.",
}
(run / "recovery_verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
assert all(checks.values()), checks
assert report["selected_candidate_viewed"] and all(v["actual_response_pixels_match"] for v in views + elevations), views + elevations
assert all(v["source_render_replay_matches"] for v in elevations), elevations
assert all(v["metadata_response_matches_saved"] and v["source_render_metadata_matches"] for v in elevations), elevations
print(json.dumps({"checks":checks,"windows":report["windows"],"source_plan_views":views,
                  "source_elevation_views":elevations}, ensure_ascii=False, indent=2))
