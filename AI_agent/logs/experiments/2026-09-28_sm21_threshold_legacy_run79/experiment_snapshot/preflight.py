"""Offline historical requests, stdio variants and model-boundary preparation."""
import asyncio
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from PIL import Image
from scripts.tool_scripts import run_bim_agent as runner
from . import legacy_view_profile, run_pair

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def old_fields(data):
    result = copy.deepcopy(data)
    result.pop("threshold_excluded_support", None)
    result["cross_axis_profile"].pop("threshold_excluded_support", None)
    result.pop("remaining_seconds", None)
    return result


def historical_replay():
    records, examples = [], []
    for number in (57, 58, 73, 74, 75, 76):
        original = next(HERE.parent.glob(f"*run{number}"))
        log = original / "tools.jsonl"
        before_hashes = {p: runner.digest(p) for p in [log, original / "inputs.json",
            *original.glob("images/*.png"), *original.glob("pixel_profiles/*"),
            *original.glob("candidate_*/source_model.json")]}
        rows = [json.loads(line) for line in log.read_text().splitlines()]
        with tempfile.TemporaryDirectory(prefix="threshold-replay-") as folder:
            root = Path(folder)
            for arm in ("legacy", "current"):
                run = root / arm
                run.mkdir()
                (run / "images").symlink_to(original / "images", target_is_directory=True)
                (run / "inputs.json").write_bytes((original / "inputs.json").read_bytes())
            legacy, current = (runner.Toolkit(root / arm) for arm in ("legacy", "current"))
            for ordinal, row in enumerate(rows):
                if row["action"] != "view_pixel_profile":
                    continue
                logged = row["data"]["result"]
                args = {key: logged[key] for key in ("name", "axis", "rgb", "tolerance", "min_fraction")}
                args["box"] = logged["box_original_pixels"]
                old = json.loads(legacy_view_profile.view_profile(legacy, **args)[1])
                new = json.loads(current.view_profile(**args)[1])
                # Numbering, table, actual PNG bytes, coordinate frame and all
                # previous notes are exact. Only elapsed time is nondeterministic.
                assert old_fields(old) == old_fields(logged) == old_fields(new), (number, ordinal)
                added = new["threshold_excluded_support"]
                entry = {"run": original.name, "tool_log_index": ordinal,
                    "profile_id": logged["profile_id"], "request": args,
                    "old_reply_and_image_exact": True,
                    "excluded_coordinates": added["coordinate_count"],
                    "excluded_matching_pixels": added["matching_pixels"],
                    "old_json_chars": len(json.dumps(old)), "new_json_chars": len(json.dumps(new))}
                records.append(entry)
                if number == 75 and logged["profile_id"] == "profile_010":
                    assert {"pixels": [370, 617], "min_count": 1, "max_count": 1} in added["intervals"]
                    examples.append({**entry, "before": old, "after": new,
                        "interpretation": "Old primary-axis candidates omit y=370..617 because one matching pixel is below the two-pixel threshold. The old cross-axis already reports x=1346 support y=370..618. The model received that evidence; the patch exposes the omission, not a newly discovered wall or proof of causation."})
        assert all(runner.digest(path) == value for path, value in before_hashes.items())
    runner.dump(HERE / "historical_replay.json", {
        "mode": "offline developer replay; no autonomous generation",
        "records": records, "examples": examples, "historical_files_unchanged": True})
    return {"requests_replayed": len(records), "historical_runs": [57, 58, 73, 74, 75, 76],
        "old_fields_and_images_exact": True, "historical_files_unchanged": True,
        "max_added_json_chars": max(r["new_json_chars"] - r["old_json_chars"] for r in records),
        "max_new_json_chars": max(r["new_json_chars"] for r in records)}


async def mcp_pair():
    catalogs, outputs = {}, {}
    with tempfile.TemporaryDirectory(prefix="threshold-mcp-") as folder:
        for variant in ("legacy", "current"):
            run = Path(folder) / variant
            (run / "images").mkdir(parents=True)
            pic = Image.new("RGB", (24, 20), "black")
            for x in range(4, 20):
                for y in (8, 11):
                    pic.putpixel((x, y), (128, 128, 128))
            for y in range(5, 15):
                pic.putpixel((19, y), (128, 128, 128))
            path = run / "images/plan.png"
            pic.save(path)
            runner.dump(run / "inputs.json", {"images": {"plan.png": {
                "size": list(pic.size), "sha256": runner.digest(path)}}})
            runner.dump(run / "experiment_condition.json", {"variant": variant})
            params = StdioServerParameters(command=sys.executable,
                args=[str(HERE / "server.py"), "serve", str(run)], cwd=str(ROOT))
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    catalogs[variant] = {t.name: t.model_dump(mode="json") for t in (await session.list_tools()).tools}
                    reply = await session.call_tool("view_pixel_profile", dict(name="plan.png",
                        box=[4, 5, 20, 15], axis="y", rgb=[128, 128, 128], tolerance=0, min_fraction=.2))
                    assert not reply.isError
                    outputs[variant] = json.loads(reply.content[1].text)
                    assert len([c for c in reply.content if c.type == "image"]) == 1
            active = json.loads((run / "runtime_threshold.json").read_text())
            frozen = run_pair.conditions()
            assert active["method_sha256"] == frozen["method_sha256"][variant]
            assert active["guide_sha256"] == frozen["guide_sha256"]
            assert active["references_sha256"] == frozen["references_sha256"]
        previous = json.loads((HERE.parent / "2026-09-27_sm21_runtime_surface_setup/current_tools.json").read_text())
        assert catalogs["legacy"] == catalogs["current"] == previous
        assert "threshold_excluded_support" not in outputs["legacy"]
        assert outputs["current"]["threshold_excluded_support"]["coordinate_count"] == 8
        assert old_fields(outputs["legacy"]) == old_fields(outputs["current"])
    return {"variants": ["legacy", "current"], "tool_count": len(catalogs["current"]),
        "unchanged_catalog_guide_references_images_old_feedback": True, "active_method_verified": True}


def dry_runner():
    class StopBeforeModel(Exception):
        pass

    seen = []
    def stop(run, *args, **kwargs):
        assert runner.__file__ == str(run_pair.HERE / "server.py")
        assert (run / "runtime_snapshot/scripts/tool_scripts/run_bim_agent.py").is_file()
        assert (run / "experiment_snapshot/server.py").is_file()
        seen.append(json.loads((run / "experiment_condition.json").read_text())["variant"])
        raise StopBeforeModel()

    with tempfile.TemporaryDirectory(prefix="threshold-dry-") as folder:
        fake = Path(folder) / "setup"
        fake.mkdir()
        for script in HERE.glob("*.py"):
            (fake / script.name).write_bytes(script.read_bytes())
        prepared = run_pair.conditions()
        runner.dump(fake / "proposed_batch.json", {"conditions": prepared})
        original_file = runner.__file__
        def no_process(*args, **kwargs):
            raise AssertionError("No model process may start during preflight")
        with patch.object(run_pair, "HERE", fake), patch.object(run_pair, "conditions", lambda: prepared), \
                patch.object(runner, "subscription", stop), patch.object(runner.subprocess, "Popen", no_process), \
                patch.object(run_pair.subprocess, "check_output", lambda *a, **kw: "offline-dry-run\n"):
            for variant in ("legacy", "current"):
                try:
                    run_pair.run(variant, f"dry_{variant}")
                except StopBeforeModel:
                    pass
                else:
                    raise AssertionError("Expected model-boundary stop")
                assert runner.__file__ == original_file
    assert seen == ["legacy", "current"]
    return {"stopped_before_model": seen, "model_calls": 0}


def main():
    report = {"historical": historical_replay(), "mcp": asyncio.run(mcp_pair()),
        "dry_runner": dry_runner(), "model_calls": 0}
    report["receipt_check"] = []
    for number in (75, 76, 77, 78):
        run = next(HERE.parent.glob(f"*run{number}"))
        try:
            run_pair.require_completed_run(run)
        except RuntimeError:
            completed = False
        else:
            completed = True
        assert completed == (number == 75)
        report["receipt_check"].append({"run": run.name, "completed": completed})
    audit = importlib.import_module(f"{__package__}.audit_run")
    seen = audit.exposure(HERE.parent / "2026-09-27_sm21_use_guidance_before_run75", "legacy")
    assert len(seen["parsed_replies"]) == 35 and len(seen["unparsed_or_failed_calls"]) == 2
    report["exposure_parser"] = {"archived_run75_parseable_replies": 35, "unparsed_or_failed_calls": 2}
    runner.dump(HERE / "preflight.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
