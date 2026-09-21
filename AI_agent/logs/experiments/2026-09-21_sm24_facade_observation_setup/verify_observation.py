"""Audit completed local observations and actual tool returns, without GT."""
import argparse
import base64
from collections import Counter
import gzip
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.geometry.facade_span_comparison import compare


def read(path):
    return json.loads(path.read_text())


def same_pixels(a, b):
    with Image.open(io.BytesIO(a)) as first, Image.open(io.BytesIO(b)) as second:
        return first.size == second.size and first.convert("RGB").tobytes() == second.convert("RGB").tobytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    summary = read(run / "summary.json")
    manifest = read(run / "inputs.json")
    receipt = read(run / "agent_receipt.json")
    stream = run / "agent_stream.jsonl"
    if stream.exists():
        events = [json.loads(line) for line in stream.read_text().splitlines()]
    else:
        with gzip.open(str(stream) + ".gz", "rt") as handle:
            events = [json.loads(line) for line in handle]
    calls, tool_rows, crops, comparisons = {}, [], [], []
    with tempfile.TemporaryDirectory(prefix="facade-observation-replay-") as temp:
        replay = Path(temp)
        shutil.copyfile(run / "inputs.json", replay / "inputs.json")
        shutil.copytree(run / "images", replay / "images")
        toolkit = Toolkit(replay, readonly=True)
        for event in events:
            for part in event.get("message", {}).get("content", []):
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "tool_use":
                    calls[part["id"]] = part
                if part.get("type") != "tool_result":
                    continue
                call = calls.get(part.get("tool_use_id"), {})
                name = call.get("name", "").rsplit("__", 1)[-1]
                tool_rows.append({"name": name, "input": call.get("input"),
                                  "is_error": bool(part.get("is_error"))})
                if part.get("is_error"):
                    continue
                content = part.get("content", [])
                if not isinstance(content, list):
                    content = [{"type": "text", "text": content}]
                if name == "view_image":
                    returned = [x for x in content if x.get("type") == "image"]
                    expected = toolkit.view(**call["input"])[0].to_image_content()
                    crops.append({"input": call["input"], "returned_count": len(returned),
                                  "pixels_match": len(returned) == 1 and same_pixels(
                                      base64.b64decode(returned[0]["source"]["data"]),
                                      base64.b64decode(expected.data))})
                if name == "compare_facade_spans":
                    payloads = []
                    for item in content:
                        if item.get("type") == "text":
                            try:
                                payloads.append(json.loads(item["text"]))
                            except (ValueError, TypeError):
                                pass
                    returned = next((x for x in payloads if isinstance(x, dict) and "record" in x), {})
                    saved = read(run / returned["record"]) if returned.get("record") else None
                    args_ = call["input"]
                    calculated = compare(json.loads(args_["observations_json"]),
                                         args_.get("ambiguity_tolerance_m", 0.05))
                    comparisons.append({"record": returned.get("record"),
                                        "returned_equals_saved": returned == saved,
                                        "input_equals_saved": saved is not None and saved["observations"] == json.loads(args_["observations_json"]),
                                        "calculation_replays": saved is not None and all(saved.get(k) == v for k, v in calculated.items()),
                                        "original_hashes_match": saved is not None and all(
                                            x["sha256"] == manifest["images"][x["image"]]["sha256"]
                                            for x in saved["original_images"].values())})
    helper_path = ROOT / "AI_agent/logs/experiments/2026-09-20_sm24_method_transfer_run01/verify_run.py"
    spec = importlib.util.spec_from_file_location("old_verify", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    transport = helper.image_transport(run)
    inputs = [{"image": name, "frozen_hash_matches": digest(run / "images" / name) == info["sha256"],
               "original_hash_matches": digest(ROOT / "case_tests/e2e_tests/sm24_anchor/case_data" / name) == info["sha256"]}
              for name, info in manifest["images"].items()]
    implementations = {name: digest(ROOT / name) == sha for name, sha in manifest["implementation_sha256"].items()}
    report = {"scope": summary["scope"], "receipt_completed": receipt.get("returncode") == 0 and
              not receipt.get("timed_out") and not receipt.get("result", {}).get("is_error", True),
              "inputs": inputs, "implementations": implementations,
              "no_source_or_seed": not any(run.glob("candidate*")) and not (run / "seed").exists(),
              "tool_counts": dict(Counter(x["name"] for x in tool_rows)),
              "tool_errors": [x for x in tool_rows if x["is_error"]],
              "view_image_replays": crops, "saved_image_transport": transport,
              "comparisons": comparisons, "tool_calls": tool_rows,
              "model_usage": helper.model_usage(run, {**summary, "subscription_invocations": 1}),
              "limits": "Mechanics and evidence transport only; no semantic accuracy or BIM acceptance."}
    report["mechanics_pass"] = (report["receipt_completed"] and report["no_source_or_seed"] and
        all(x["frozen_hash_matches"] and x["original_hash_matches"] for x in inputs) and
        all(implementations.values()) and bool(crops) and all(x["pixels_match"] for x in crops) and
        all(x["pixels_match"] for x in transport["comparisons"]) and bool(comparisons) and
        all(all(x[k] for k in ("returned_equals_saved", "input_equals_saved", "calculation_replays", "original_hashes_match")) for x in comparisons))
    with (run / "verification.json").open("x") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with (run / "answer.md").open("x") as handle:
        handle.write(receipt.get("result", {}).get("result", "No final answer.") + "\n")
    print(json.dumps({"mechanics_pass": report["mechanics_pass"], "tool_counts": report["tool_counts"],
                      "comparison_count": len(comparisons), "view_image_count": len(crops)}))


if __name__ == "__main__":
    main()
