"""Offline historical replay and real MCP checks for the proposed feedback pair."""
import asyncio
import gzip
import importlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from scripts.tool_scripts import run_bim_agent as runner
from . import legacy_profile, run_pair, server

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def legacy_fields(result):
    out = {k: result[k] for k in ("axis", "runs", "matching_pixels", "empty_filter_diagnostics") if k in result}
    out["runs"] = [{k: row[k] for k in ("pixels", "peak", "max_count")} for row in out["runs"]]
    return out


def requests(run):
    calls, replies = {}, {}
    for line in gzip.open(run / "agent_stream.jsonl.gz", "rt"):
        content = json.loads(line).get("message", {}).get("content", [])
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_use":
                calls[block["id"]] = {"ordinal": len(calls) + 1, **block}
            elif block.get("type") == "tool_result":
                parts = block.get("content", [])
                for part in parts if isinstance(parts, list) else []:
                    if part.get("type") != "text":
                        continue
                    try:
                        value = json.loads(part["text"])
                    except ValueError:
                        continue
                    if isinstance(value, dict):
                        replies[block["tool_use_id"]] = value
    return calls, replies


def historical_replay():
    report, examples = [], []
    for number in (69, 71, 72):
        old_run = next(HERE.parent.glob(f"*run{number}"))
        calls, replies = requests(old_run)
        with tempfile.TemporaryDirectory(prefix="profile-replay-") as folder:
            run = Path(folder)
            (run / "images").symlink_to(old_run / "images", target_is_directory=True)
            (run / "inputs.json").write_bytes((old_run / "inputs.json").read_bytes())
            toolkit = runner.Toolkit(run)
            for key, call in calls.items():
                if call["name"] != "mcp__bim__pixel_profile":
                    continue
                args = {"tolerance": 70, **call["input"]}
                if key not in replies:
                    # All archived failures here are invalid image names, not lost JSON.
                    assert args["name"] not in toolkit.manifest["images"]
                    continue
                before = legacy_profile.profile(toolkit, **args)
                after = toolkit.profile(**args)
                assert before == replies[key] == legacy_fields(after)
                record = {"run": old_run.name, "ordinal": call["ordinal"], "request": args,
                          "legacy_values_exact": True, "runs": len(after["runs"]),
                          "runs_with_multiple_peaks": sum(len(r["support_peaks"]) > 1 for r in after["runs"]),
                          "old_json_chars": len(json.dumps(before)), "new_json_chars": len(json.dumps(after))}
                report.append(record)
                if number == 71 and call["ordinal"] in (15, 17):
                    first = next(c for c in calls.values() if c["name"] == "mcp__bim__build_plan_bim")
                    plan = json.loads(first["input"]["plan_json"])
                    examples.append({**record, "before": before, "after": after,
                                     "later_first_plan_anchors": plan[args["axis"] + "_anchors"]})
    runner.dump(HERE / "historical_profile_replay.json", {
        "mode": "offline original-request replay, not autonomous generation", "requests": report,
        "adoption_examples": examples, "old_runs_modified": False,
        "interpretation": "Coincident later anchors establish the adopted values, not the model's hidden reasoning. Support peaks are not independently a semantic endpoint verdict."})
    return {"successful_requests_replayed": len(report),
            "legacy_values_exact": True,
            "max_new_json_chars": max(r["new_json_chars"] for r in report),
            "examples": [{"axis": x["request"]["axis"], "old": x["before"]["runs"],
                          "new_peaks": [r["support_peaks"] for r in x["after"]["runs"]]}
                         for x in examples]}


async def mcp_pair():
    import sys
    from PIL import Image
    catalogs, outputs = {}, {}
    with tempfile.TemporaryDirectory(prefix="profile-mcp-") as folder:
        for variant in ("legacy", "current"):
            run = Path(folder) / variant
            (run / "images").mkdir(parents=True)
            pic = Image.new("RGB", (18, 12), "white")
            for x in range(2, 16):
                pic.putpixel((x, 6), (0, 0, 0))
            for x in (4, 13):
                for y in range(2, 10):
                    pic.putpixel((x, y), (0, 0, 0))
            path = run / "images/plan.png"
            pic.save(path)
            runner.dump(run / "inputs.json", {"images": {"plan.png": {
                "size": list(pic.size), "sha256": runner.digest(path)}}})
            runner.dump(run / "experiment_condition.json", {"variant": variant})
            params = StdioServerParameters(command=sys.executable,
                args=[str(HERE / "server.py"), "serve", str(run)], cwd=str(ROOT))
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    catalogs[variant] = {t.name: t.model_dump(mode="json") for t in (await client.list_tools()).tools}
                    result = await client.call_tool("pixel_profile", dict(name="plan.png",
                        box=[1, 1, 17, 11], axis="x", rgb=[0, 0, 0], tolerance=0))
                    assert not result.isError
                    outputs[variant] = result.structuredContent or json.loads(result.content[0].text)
            active = json.loads((run / "runtime_profile.json").read_text())
            assert active["variant"] == variant
            assert active["method_sha256"] == run_pair.conditions()["method_sha256"][variant]
            assert active["guide_sha256"] == run_pair.conditions()["guide_sha256"]
            assert active["references_sha256"] == run_pair.conditions()["references_sha256"]
        assert catalogs["legacy"] == catalogs["current"]
        previous = json.loads((HERE.parent /
            "2026-09-27_sm21_runtime_surface_setup/current_tools.json").read_text())
        assert catalogs["current"] == previous, "Tool inventory/schema/description changed"
        assert legacy_fields(outputs["current"]) == outputs["legacy"]
        assert outputs["current"]["runs"][0]["support_peaks"] == [
            {"pixels": [4, 4], "count": 8}, {"pixels": [13, 13], "count": 8}]
    return {"stdio_variants_checked": ["legacy", "current"], "exposed_tools": len(catalogs["current"]),
            "catalog_exactly_matches_prechange": True, "old_measurements_preserved": True,
            "active_method_hashes_verified": True}


def dry_runner():
    # Exercise the real run setup, manifest and snapshot creation up to the
    # subscription boundary; deliberately stop before ANY model invocation.
    class StopBeforeModel(Exception):
        pass

    observations = []
    def intercepted(run, *args, **kwargs):
        assert runner.__file__ == str(run_pair.HERE / "server.py")
        manifest = json.loads((run / "inputs.json").read_text())
        assert manifest["implementation_sha256"]["scripts/tool_scripts/run_bim_agent.py"] == runner.digest(ROOT / "scripts/tool_scripts/run_bim_agent.py")
        assert (run / "runtime_snapshot/scripts/tool_scripts/run_bim_agent.py").is_file()
        assert (run / "experiment_snapshot/server.py").is_file()
        observations.append(json.loads((run / "experiment_condition.json").read_text())["variant"])
        raise StopBeforeModel()

    with tempfile.TemporaryDirectory(prefix="profile-dry-parent-") as folder:
        fake_here = Path(folder) / "setup"
        fake_here.mkdir()
        for script in HERE.glob("*.py"):
            (fake_here / script.name).write_bytes(script.read_bytes())
        prepared = run_pair.conditions()
        # ROOT and conditions stay real; only destinations and copied adapter
        # files change. The MCP subprocess itself is checked separately above.
        runner.dump(fake_here / "proposed_batch.json", {"conditions": prepared})
        original_file = runner.__file__
        def no_process(*a, **kw):
            raise AssertionError("Dry runner must never start a subscription process")
        with patch.object(run_pair, "HERE", fake_here), patch.object(run_pair, "conditions", lambda: prepared), \
                patch.object(runner, "subscription", intercepted), patch.object(runner.subprocess, "Popen", no_process), \
                patch.object(run_pair.subprocess, "check_output", lambda *a, **kw: "offline-dry-run\n"):
            for variant in ("legacy", "current"):
                try:
                    run_pair.run(variant, f"dry_{variant}")
                except StopBeforeModel:
                    pass
                else:
                    raise AssertionError("Expected stop before model")
                assert runner.__file__ == original_file
    assert observations == ["legacy", "current"]
    return {"variants_stopped_at_model_boundary": observations, "model_calls": 0}


def main():
    report = {"historical_replay": historical_replay(), "mcp": asyncio.run(mcp_pair()),
              "dry_runner": dry_runner(), "production_calls": 0}
    runner.dump(HERE / "preflight.json", report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
