"""Inspect public tool requests/results and saved adoption, never reasoning blocks."""
import argparse
import gzip
import json
from pathlib import Path


def audit(run):
    assert (run / "summary.json").is_file(), "wait for the completed invocation"
    path = run / "agent_stream.jsonl.gz"
    opener = gzip.open
    if not path.exists():
        path, opener = run / "agent_stream.jsonl", open
    calls, feedback, references = {}, [], []
    with opener(path, "rt") as stream:
        for line in stream:
            blocks = json.loads(line).get("message", {}).get("content", [])
            for block in blocks if isinstance(blocks, list) else []:
                if block.get("type") == "tool_use":
                    calls[block["id"]] = dict(tool=block["name"].removeprefix("mcp__bim__"), input=block.get("input", {}))
                if block.get("type") != "tool_result":
                    continue
                request = calls.get(block.get("tool_use_id"), {})
                content = block.get("content", [])
                parts = content if isinstance(content, list) else [dict(type="text", text=content)]
                for part in parts:
                    if part.get("type") != "text":
                        continue
                    try:
                        value = json.loads(part["text"])
                    except (TypeError, ValueError):
                        continue
                    if not isinstance(value, dict):
                        continue
                    if request.get("tool") == "get_bim_reference":
                        references.append(dict(topic=request["input"].get("topic"), returned_reference=value.get("reference")))
                    selected = {key:value[key] for key in ("candidate", "source_geometry_ready", "error") if key in value}
                    if value.get("plan_input", {}).get("geometry_feedback"):
                        selected["geometry_feedback"] = value["plan_input"]["geometry_feedback"]
                    if value.get("plan_revision", {}).get("geometry_changes"):
                        selected["geometry_changes"] = value["plan_revision"]["geometry_changes"]
                    if value.get("location_check"):
                        selected.update(location_check=value["location_check"], findings=value.get("findings", []))
                    if any(key in selected for key in ("geometry_feedback", "geometry_changes", "location_check")):
                        feedback.append(dict(tool=request.get("tool"), result=selected))
    bindings = []
    for path in sorted(run.glob("plan_drafts/*/measurement_bindings.json")):
        row = json.loads(path.read_text())
        bindings.append(dict(file=str(path.relative_to(run)), pixels=row.get("bindings", []), lengths=row.get("length_bindings", [])))
    reviews = [json.loads(p.read_text()) for p in sorted(run.glob("opening_reviews/review_*.json"))]
    result = dict(references=references, returned_feedback=feedback, saved_bindings=bindings,
        review_count=len(reviews), located_plan_reviews=sum(r.get("location_check", {}).get("status") == "checked_against_supplied_plan_boxes" for r in reviews),
        unmodeled_mark_count=sum(f["code"] == "unmodeled_observed_mark" for r in reviews for f in r["findings"]),
        units_bound=sum(len(r["lengths"]) for r in bindings), pixels_bound=sum(len(r["pixels"]) for r in bindings),
        limits="Exposure and adopted inputs only; outcome and actual correction require independent original/source review. This is not a behavior score.")
    (run / "feedback_adoption.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key:result[key] for key in ("review_count", "located_plan_reviews", "unmodeled_mark_count", "units_bound", "pixels_bound")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
