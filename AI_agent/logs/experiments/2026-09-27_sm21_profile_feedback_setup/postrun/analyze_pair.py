"""Post-generation intervention exposure and coordinate-use audit, without GT."""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def trace(run):
    assert (run / "summary.json").is_file(), "Wait for generation to finish"
    archived = run / "agent_stream.jsonl.gz"
    opener = gzip.open if archived.exists() else open
    path = archived if archived.exists() else run / "agent_stream.jsonl"
    calls, results, reply_events = {}, {}, {}
    with opener(path, "rt") as stream:
        for event_index, line in enumerate(stream):
            event = json.loads(line)
            blocks = event.get("message", {}).get("content", [])
            for block in blocks if isinstance(blocks, list) else []:
                if block.get("type") == "tool_use":
                    calls[block["id"]] = {"ordinal": len(calls) + 1,
                        "request_event": event_index,
                        "name": block["name"].removeprefix("mcp__bim__"), "input": block["input"]}
                if block.get("type") == "tool_result":
                    reply_events[block["tool_use_id"]] = event_index
                    parts = block.get("content", [])
                    for part in parts if isinstance(parts, list) else []:
                        if part.get("type") == "text":
                            try:
                                value = json.loads(part["text"])
                            except ValueError:
                                continue
                            if isinstance(value, dict):
                                results[block["tool_use_id"]] = value
    profiles, plans = [], []
    for key, call in calls.items():
        result = results.get(key, {})
        if call["name"] == "pixel_profile" and "runs" in result:
            profiles.append({**call, "reply_event": reply_events[key],
                             "result": result, "new_feedback_received": "evidence_note" in result})
        if call["name"] == "build_plan_bim":
            plan = json.loads(call["input"]["plan_json"])
            associations = []
            for axis in ("x", "y"):
                for pixel, world in plan[axis + "_anchors"]:
                    matching = []
                    for profile in profiles:
                        if profile["reply_event"] >= call["request_event"]:
                            continue  # A requested-but-not-yet-returned profile cannot inform this call.
                        args = profile["input"]
                        if args["name"] != call["input"]["image"] or args["axis"] != axis:
                            continue
                        rows = profile["result"]["runs"]
                        extent = any(pixel in row["pixels"] for row in rows)
                        first_max = any(pixel == row["peak"] for row in rows)
                        local_peak = any(p["pixels"][0] <= pixel <= p["pixels"][1]
                                         for row in rows for p in row.get("support_peaks", []))
                        if extent or first_max or local_peak:
                            matching.append({"profile_ordinal": profile["ordinal"],
                                "raw_extent_end": extent, "first_maximum": first_max,
                                "within_reported_local_peak": local_peak})
                    associations.append({"axis": axis, "pixel": pixel, "world_metres": world,
                                         "earlier_value_coincidences": matching})
            plans.append({"ordinal": call["ordinal"], "request_event": call["request_event"],
                "image": call["input"]["image"],
                **{k: plan.get(k) for k in ("floor_id", "x_anchors", "y_anchors", "basis")},
                "coordinate_value_coincidences": associations,
                "source_geometry_ready": result.get("source_geometry_ready"),
                "candidate": result.get("candidate")})
    active = load(run / "runtime_profile.json")
    first_exposure = min((p for p in profiles if p["new_feedback_received"]),
                         key=lambda p: p["reply_event"], default=None)
    return {"run": run.name, "variant": active["variant"],
            "tool_calls": list(calls.values()), "successful_profiles": profiles,
            "first_new_feedback_ordinal": first_exposure["ordinal"] if first_exposure else None,
            "first_new_feedback_reply_event": first_exposure["reply_event"] if first_exposure else None,
            "first_build_ordinal": plans[0]["ordinal"] if plans else None,
            "build_plan_inputs": plans,
            "received_new_feedback_before_first_build": bool(first_exposure and plans
                and first_exposure["reply_event"] < plans[0]["request_event"]),
            "limit": "Coordinate coincidences and recorded basis are observations, not proof of hidden reasoning or autonomous correctness."}


def main():
    runs = [HERE.parent / "2026-09-27_sm21_profile_legacy_run73",
            HERE.parent / "2026-09-27_sm21_profile_current_run74"]
    traces = [trace(run) for run in runs]
    left, right = [t["tool_calls"] for t in traces]
    prefix = 0
    for a, b in zip(left, right):
        if (a["name"], a["input"]) != (b["name"], b["input"]):
            break
        prefix += 1
    report = {"same_tool_call_prefix_length": prefix,
              "first_different_tool_calls": [calls[prefix] if prefix < len(calls) else None
                                             for calls in (left, right)],
              "runs": traces,
              "limits": ["Only two independent invocations; no paired sampling seed or provider-internal context available.",
                         "A changed outcome cannot establish causality, especially if actions differ before exposure.",
                         "No GT, previous geometry or this audit enters production generation."]}
    (HERE / "intervention_exposure.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"same_tool_call_prefix_length": prefix,
                     "runs": [{k: t[k] for k in ("run", "first_new_feedback_ordinal", "first_build_ordinal",
                                                "received_new_feedback_before_first_build")}
                              for t in traces]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
