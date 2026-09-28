"""Replay with the exact historical producer; no model calls or GT loading."""
import base64
import gzip
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys

from run_old import HERE, ROOT, RUN, TREE, load, producer, save


def audit_original_views(runner):
    from PIL import Image
    path = RUN / "agent_stream.jsonl.gz"
    raw = gzip.decompress(path.read_bytes()) if path.exists() else (RUN / "agent_stream.jsonl").read_bytes()
    calls, views = {}, []
    for line in raw.splitlines():
        parts = json.loads(line).get("message", {}).get("content", [])
        for block in parts if isinstance(parts, list) else []:
            if block.get("type") == "tool_use":
                calls[block["id"]] = block["name"]
            if block.get("type") != "tool_result" or block.get("is_error"):
                continue
            if calls.get(block["tool_use_id"]) != "mcp__bim__view_image":
                continue
            pictures, metas = [], []
            for part in block.get("content", []):
                if part.get("type") == "image":
                    pictures.append(part)
                elif part.get("type") == "text":
                    try:
                        value = json.loads(part["text"])
                    except ValueError:
                        continue
                    if isinstance(value, dict) and "box_original_pixels" in value:
                        metas.append(value)
            assert len(pictures) == len(metas) == 1
            meta = metas[0]
            png = base64.b64decode(pictures[0]["source"]["data"])
            with Image.open(RUN / "images" / meta["name"]) as original:
                expected = original.convert("RGB").crop(meta["box_original_pixels"])
            if meta["display_scale_requested"] == 1:
                expected.thumbnail((1600, 1600))
            else:
                expected = expected.resize(tuple(meta["returned_size"]), Image.Resampling.NEAREST)
            if meta["coordinate_grid"]["shown"]:
                expected, _ = runner.coordinate_grid_view(expected, meta["box_original_pixels"])
            with Image.open(io.BytesIO(png)) as actual:
                assert actual.size == expected.size and actual.convert("RGB").tobytes() == expected.tobytes()
            views.append(dict(image=meta["name"], box=meta["box_original_pixels"],
                returned_png_sha256=hashlib.sha256(png).hexdigest(), pixels_match_original=True))
    save(RUN / "original_view_transport.json", dict(views=views, count=len(views),
        actual_pixels_match=True, limit="Transport only; not proof of image interpretation."))
    return len(views)


def audit():
    runner, prior, expected, modules, images = producer()
    sys.path.insert(1, str(ROOT))
    summary, receipt, manifest, delivery = [load(RUN / name) for name in
        ("summary.json", "agent_receipt.json", "inputs.json", "delivery.json")]
    assert summary["agent_response_completed"] and receipt["returncode"] == 0
    assert not receipt.get("timed_out") and not receipt.get("routing_error")
    assert not receipt["result"].get("is_error")
    assert load(RUN / "agent_request.json") == expected
    assert len(list(RUN.glob("*_receipt.json"))) == 1
    shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
    shared.ROOT = TREE
    inputs = shared.verify_inputs(RUN, load(HERE / "frozen.json"), manifest, cold=True)
    for name, value in load(RUN / "producer_snapshot.json").items():
        assert runner.digest(RUN / "runtime_snapshot" / name) == value == runner.digest(TREE / name)
    candidate = delivery["candidate"]
    source, proposal, display = shared.replay_final(RUN, candidate)
    assemblies = shared.replay_assemblies(RUN, manifest)
    toolkit = runner.Toolkit(RUN)
    from src.agent.execution.bim_height_coverage import height_coverage
    assert toolkit.input_view_status() == delivery["input_view_status"]
    assert height_coverage(toolkit.claims(), candidate) == delivery["height_coverage"]
    assert source["source_model_sha256"] == delivery["source_model_sha256"]
    assert all(Path(m.__file__).resolve().is_relative_to(TREE) for m in modules)
    rows = [json.loads(line) for line in (RUN / "tools.jsonl").read_text().splitlines()]
    assert not any(row["action"] == "review_detail" for row in rows)
    report = dict(candidate=candidate, source_model_sha256=source["source_model_sha256"],
        source_display_replay_exact=True, assemblies_replayed=assemblies,
        input_and_producer_hashes_verified=True, inputs=inputs,
        original_request_matches_run58=True, model_calls_for_audit=0,
        generator_invocations=1, nested_model_calls=0,
        imported_modules={m.__name__: m.__file__ for m in modules},
        height_coverage=delivery["height_coverage"]["summary"],
        actual_model=receipt["actual_model"], elapsed_seconds=summary["elapsed_seconds"],
        actual_original_views_verified=audit_original_views(runner))
    save(RUN / "producer_replay.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in
        ("inputs", "assemblies_replayed", "imported_modules")}, ensure_ascii=False))


if __name__ == "__main__":
    audit()
