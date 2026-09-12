"""Compare the model's actual image-view responses with the frozen originals."""
import argparse
import base64
import gzip
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageChops
from scripts.tool_scripts.run_bim_agent import coordinate_grid_view

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
run = parser.parse_args().run.resolve()
assert (run / "summary.json").exists(), "wait until generation finishes"
stream = run / "agent_stream.jsonl"
opener = open
if not stream.exists():
    stream = run / "agent_stream.jsonl.gz"
    opener = gzip.open
calls, rows = {}, []
with opener(stream, "rt") as f:
    for line in f:
        event = json.loads(line)
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block["name"].endswith("__view_image"):
                calls[block["id"]] = block["input"]
            if block.get("type") != "tool_result" or block.get("tool_use_id") not in calls or block.get("is_error"):
                continue
            args = calls[block["tool_use_id"]]
            content = block.get("content", [])
            images = [c for c in content if isinstance(c, dict) and c.get("type") == "image"]
            assert len(images) == 1
            with Image.open(run / "images" / args["name"]) as original:
                pic = original.convert("RGB")
                region = args.get("box") or [0, 0, pic.width, pic.height]
                pic = pic.crop(region)
                pic.thumbnail((1600, 1600))
                grid = {"shown":False}
                if args.get("coordinate_grid", True):
                    pic, grid = coordinate_grid_view(pic, region)
            actual = Image.open(io.BytesIO(base64.b64decode(images[0]["source"]["data"]))).convert("RGB")
            same = pic.size == actual.size and ImageChops.difference(pic, actual).getbbox() is None
            rows.append({"tool_use_id":block["tool_use_id"],"image":args["name"],"box":region,
                         "grid_shown":grid["shown"],"actual_response_pixels_match":same})
report = {"mode":"actual model image response audit", "views":rows,
          "all_passed":bool(rows) and all(r["actual_response_pixels_match"] for r in rows),
          "limits":"Labels/coordinates were delivered correctly; this does not certify the model read them correctly."}
(run / "presentation_verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
assert report["all_passed"], report
print(json.dumps({"view_count":len(rows),"grid_views":sum(r["grid_shown"] for r in rows),"all_passed":report["all_passed"]}))
