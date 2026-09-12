"""Audit actual parent/Haiku images and source views after generation completes."""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops
from scripts.tool_scripts.run_bim_agent import coordinate_grid_view
from src.agent.geometry.source_elevation_view import render_source_elevation

read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def same(a, b):
    return a.size == b.size and ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None

def audit_stream(run, prefix, image_root):
    stream = run / (prefix + "_stream.jsonl")
    opener = open
    if not stream.exists():
        stream = stream.with_suffix(".jsonl.gz")
        opener = gzip.open
    calls, original_views, source_views, detail_responses, errors = {}, [], [], [], []
    with opener(stream, "rt") as f:
        for line in f:
            event = json.loads(line)
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls[block["id"]] = block
                if block.get("type") != "tool_result" or block.get("tool_use_id") not in calls:
                    continue
                call = calls[block["tool_use_id"]]
                name, args = call["name"].split("__")[-1], call["input"]
                if block.get("is_error"):
                    errors.append({"tool":name,"tool_use_id":block["tool_use_id"]})
                    continue
                content = block.get("content", [])
                if not isinstance(content, list):
                    continue
                images = [b for b in content if b.get("type") == "image"]
                texts = [b["text"] for b in content if b.get("type") == "text"]
                if name == "review_detail":
                    response = json.loads(texts[0])
                    detail_responses.append({"question":args["question"],"images":args["images"],"response":response})
                if name not in {"view_image", "view_candidate", "view_elevation_candidate"}:
                    continue
                assert len(images) == 1
                actual = Image.open(io.BytesIO(base64.b64decode(images[0]["source"]["data"])))
                if name == "view_image":
                    original = Image.open(image_root / args["name"]).convert("RGB")
                    box = args.get("box") or [0,0,original.width,original.height]
                    expected = original.crop(box)
                    expected.thumbnail((1600,1600))
                    grid = {"shown":False}
                    if args.get("coordinate_grid", True):
                        expected, grid = coordinate_grid_view(expected, box)
                    original_views.append({"image":args["name"],"box":box,"grid_shown":grid["shown"],"pixels_match":same(actual, expected)})
                else:
                    stem = "plan_" + args["floor_id"].replace("/", "_") if name == "view_candidate" else "elevation_" + args["facade"]
                    directory = run / args["candidate"]
                    saved = Image.open(directory / (stem + ".png"))
                    row = {"tool":name,**args,"pixels_match":same(actual, saved)}
                    if name == "view_elevation_candidate":
                        source = read(directory / "source_model.json")
                        replay, metadata = render_source_elevation(source, args["facade"])
                        persisted = read(directory / (stem + ".json"))
                        row.update(source_replay_matches=same(replay, saved),
                                   response_metadata_matches=json.loads(texts[0]) == persisted,
                                   source_metadata_matches=all(persisted.get(k) == v for k,v in metadata.items()))
                    source_views.append(row)
    return {"tool_names":[c["name"].split("__")[-1] for c in calls.values()],
            "original_views":original_views,"source_views":source_views,"detail_responses":detail_responses,"tool_errors":errors}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run.resolve()
    summary = read(run / "summary.json")
    manifest = read(run / "inputs.json")
    parent = audit_stream(run, "agent", run / "images")
    children = []
    for request in sorted(run.glob("detail_*_request.json")):
        name = request.name.removesuffix("_request.json")
        child = run / name
        child_manifest = read(child / "inputs.json")
        receipt = read(run / (name + "_receipt.json"))
        question = (child / "question.txt").read_text()
        checks = {
            "question_hash":hashlib.sha256(question.encode()).hexdigest() == child_manifest["question_sha256"],
            "selected_originals_match":all(sha(child/"images"/n) == v["sha256"] == manifest["images"][n]["sha256"] for n,v in child_manifest["images"].items()),
            "only_selected_images":set(p.name for p in (child/"images").iterdir()) == set(child_manifest["images"]),
            "no_candidate_or_evaluation_files":set(p.name for p in child.iterdir()) <= {"images","inputs.json","question.txt","tools.jsonl"},
            "receipt_input_hash":receipt["observation_source"]["input_sha256"] == sha(child/"inputs.json"),
        }
        responses = [r for r in parent["detail_responses"] if r["response"].get("observation_source", {}).get("run") == name]
        checks["returned_to_parent_unchanged"] = len(responses) == 1 and responses[0]["question"] == question and responses[0]["response"]["result"] == receipt.get("result", {}).get("result", "No completed answer")
        evidence = audit_stream(run, name, child / "images")
        checks["readonly_tools_only"] = set(evidence["tool_names"]) <= {"inputs","view_image","pixel_profile","map_pixels","map_dimension_chain"}
        children.append({"name":name,"question":question,"actual_model":receipt.get("actual_model"),
                         "elapsed_seconds":receipt["elapsed_seconds"],"checks":checks,**evidence})
    transport_ok = all(v["pixels_match"] for stream in [parent,*children] for v in stream["original_views"] + stream["source_views"])
    transport_ok = transport_ok and all(all(v.get(k, True) for k in ["source_replay_matches","response_metadata_matches","source_metadata_matches"]) for v in parent["source_views"])
    selected = summary.get("delivery", {}).get("candidate") if summary.get("delivery") else None
    report = {"parent":parent,"children":children,"all_transport_checks_passed":transport_ok,
              "all_child_isolation_checks_passed":all(all(c["checks"].values()) for c in children),
              "substantive_haiku_observation_completed":bool(children) and all(c["original_views"] for c in children) and any(r["response"].get("completed") for r in parent["detail_responses"]),
              "selected_source_viewed":any(v["candidate"] == selected for v in parent["source_views"]),
              "limits":"Checks transport, source rendering and isolation. Neither a completed answer nor consistent pixels certify correct interpretation or geometry."}
    (run / "execution_verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    assert transport_ok and report["all_child_isolation_checks_passed"], report
    print(json.dumps({k:v for k,v in report.items() if k not in ["parent","children"]},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
