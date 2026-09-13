"""Post-run replay of original image views, including opt-in display magnification."""
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

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(run):
    assert (run / "response.json").exists(), "wait for generation to finish"
    child = run / "detail_01"
    request = json.loads((run / "detail_01_request.json").read_text())
    receipt = json.loads((run / "detail_01_receipt.json").read_text())
    manifest = json.loads((child / "inputs.json").read_text())
    source = receipt["observation_source"]
    checks = {
        "question_unchanged": sha(child / "question.txt") == manifest["question_sha256"],
        "manifest_matches_receipt": sha(child / "inputs.json") == source["input_sha256"],
        "originals_unchanged": all(sha(child / "images" / n) == row["sha256"] == sha(run / "images" / n)
                                  for n, row in manifest["images"].items()),
        "only_plan": set(manifest["images"]) == {"1f_view.png"},
        "readonly": request["readonly"],
        "no_bim": not (child / "seed").exists() and not list(child.glob("candidate_*")),
    }
    path = run / "detail_01_stream.jsonl"
    if path.exists():
        lines = path.read_text().splitlines()
    else:
        lines = gzip.decompress(path.with_suffix(".jsonl.gz").read_bytes()).decode().splitlines()
    calls, views, errors = {}, [], []
    for line in lines:
        event = json.loads(line)
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                calls[block["id"]] = block
            if block.get("type") != "tool_result" or block.get("tool_use_id") not in calls:
                continue
            call = calls[block["tool_use_id"]]
            name = call["name"].split("__")[-1]
            if block.get("is_error"):
                errors.append(name)
                continue
            if name != "view_image":
                continue
            args = call["input"]
            content = block["content"]
            image = next(c for c in content if c["type"] == "image")
            metadata = json.loads(next(c["text"] for c in content if c["type"] == "text"))
            actual = Image.open(io.BytesIO(base64.b64decode(image["source"]["data"]))).convert("RGB")
            expected = Image.open(child / "images" / args["name"]).convert("RGB")
            box = args.get("box") or [0, 0, expected.width, expected.height]
            expected = expected.crop(box)
            requested = args.get("display_scale", 1)
            if requested == 1:
                expected.thumbnail((1600, 1600))
            else:
                scale = min(requested, 1600 / max(expected.size))
                expected = expected.resize(tuple(max(1, round(n * scale)) for n in expected.size), Image.Resampling.NEAREST)
            if args.get("coordinate_grid", True):
                expected, _ = coordinate_grid_view(expected, box)
            match = actual.size == expected.size and ImageChops.difference(actual, expected).getbbox() is None
            mapping = [(box[2]-box[0])/actual.width, (box[3]-box[1])/actual.height]
            views.append({"box": box, "display_scale_requested": requested, "returned_size": list(actual.size),
                          "pixels_match": match, "coordinates_match": metadata["box_original_pixels"] == box
                              and metadata["original_pixels_per_returned_pixel"] == mapping,
                          "remaining_seconds": metadata.get("remaining_seconds")})
    names = [c["name"].split("__")[-1] for c in calls.values()]
    checks["only_readonly_tools"] = set(names) <= {"inputs", "view_image", "pixel_profile", "map_pixels", "map_dimension_chain"}
    report = {"checks": checks, "views": views, "tool_names": names, "tool_errors": errors,
              "scope": "Input isolation, returned image pixels and coordinate transport only; not drawing fidelity."}
    assert all(checks.values()) and all(v["pixels_match"] and v["coordinates_match"] for v in views)
    (run / "execution_verification.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"run": str(run), "verified_views": len(views), "tool_errors": errors}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    verify(parser.parse_args().run.resolve())
