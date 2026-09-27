"""Offline replay, actual MCP feedback and runner setup; no model invocation."""
import asyncio
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from scripts.tool_scripts import run_bim_agent as runner
from tests.test_bim_agent_tools import _run_with_one_image, _two_floor_proposal, _json_result
from . import server, run_batch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def replay():
    config = json.loads((HERE.parent / "2026-09-27_reconstruction_quality_monitor/runs.json").read_text())
    rows = []
    for entry in config["runs"]:
        run = ROOT / entry["run"]
        candidate = json.loads((run / "delivery.json").read_text())["candidate"]
        path = run / candidate / "source_model.json"
        before_hash = runner.digest(path)
        source = json.loads(path.read_text())
        old = server.BASELINE.room_use_review(source)
        full = server.CURRENT_REVIEW(source)
        saved = server.CURRENT_REVIEW(source, include_next_action=False)
        assert old == full
        assert saved == {k: v for k, v in old.items() if k != "next_action"}
        assert before_hash == runner.digest(path)
        rows.append({"run": run.name, "candidate": candidate, "source_sha256": before_hash,
                     "coverage_and_explicit_action_exact": True,
                     "automatic_reply_chars_removed": len(json.dumps(old)) - len(json.dumps(saved))})
    return rows


async def mcp():
    catalogs, outputs, sources = {}, {}, {}
    with tempfile.TemporaryDirectory(prefix="use-guidance-mcp-") as folder:
        for variant in ("before", "after"):
            run = _run_with_one_image(Path(folder) / variant)
            runner.dump(run / "experiment_condition.json", {"variant": variant})
            params = StdioServerParameters(command=sys.executable,
                args=[str(HERE / "server.py"), "serve", str(run)], cwd=str(ROOT))
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    catalogs[variant] = {t.name: t.model_dump(mode="json") for t in (await client.list_tools()).tools}
                    built = _json_result(await client.call_tool("build_bim", {"proposal_json": _two_floor_proposal()}))
                    candidate = built["candidate"]
                    inspected = _json_result(await client.call_tool("inspect_candidate", {"candidate": candidate}))
                    finished = _json_result(await client.call_tool("finish_bim", {"candidate": candidate}))
                    outputs[variant] = {"saved": built["room_use_review"],
                                        "inspected": inspected["room_use_review"],
                                        "finished": finished["room_use_review"]}
                    sources[variant] = json.loads((run / candidate / "source_model.json").read_text())
                    assert outputs[variant]["inspected"] == outputs[variant]["finished"]
            active = json.loads((run / "runtime_use_guidance.json").read_text())
            expected = run_batch.conditions()
            assert active["guide_sha256"] == expected["guide_sha256"][variant]
            assert active["review_method_sha256"] == expected["review_method_sha256"][variant]
            assert active["references_sha256"] == expected["references_sha256"]
        previous = json.loads((HERE.parent / "2026-09-27_sm21_runtime_surface_setup/current_tools.json").read_text())
        assert catalogs["before"] == catalogs["after"] == previous
        assert sources["before"] == sources["after"]
        assert outputs["before"]["inspected"] == outputs["after"]["inspected"]
        assert "next_action" in outputs["before"]["saved"] and "next_action" not in outputs["after"]["saved"]
        assert outputs["after"]["saved"] == {k: v for k, v in outputs["before"]["saved"].items() if k != "next_action"}
    return {"variants": ["before", "after"], "tool_count": len(catalogs["after"]),
            "catalog_exact": True, "actual_source_exact": True,
            "automatic_save_only_omits_action": True, "inspection_and_delivery_exact": True}


def dry_runner():
    class StopBeforeModel(Exception):
        pass

    seen = []

    def intercepted(run, *args, **kwargs):
        frozen = json.loads((run / "experiment_condition.json").read_text())
        assert runner.__file__ == str(run_batch.HERE / "server.py")
        assert server.sha(runner.GUIDE) == frozen["guide_sha256"][frozen["variant"]]
        manifest = json.loads((run / "inputs.json").read_text())
        assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
        assert (run / "runtime_snapshot/scripts/tool_scripts/run_bim_agent.py").is_file()
        assert (run / "experiment_snapshot/baseline_guide.json").is_file()
        seen.append({"case": frozen["case"], "variant": frozen["variant"]})
        raise StopBeforeModel()

    def no_process(*args, **kwargs):
        raise AssertionError("Dry setup must not start a subscription process")

    prepared = run_batch.conditions()
    original_file, original_guide = runner.__file__, runner.GUIDE
    with tempfile.TemporaryDirectory(prefix="use-guidance-dry-") as folder:
        fake_here = Path(folder) / "setup"
        fake_here.mkdir()
        for name in prepared["experiment_sha256"]:
            shutil.copyfile(HERE / name, fake_here / name)
        runner.dump(fake_here / "proposed_batch.json", {"conditions": prepared})
        with patch.object(run_batch, "HERE", fake_here), patch.object(run_batch, "conditions", lambda: prepared), \
                patch.object(runner, "subscription", intercepted), patch.object(runner.subprocess, "Popen", no_process), \
                patch.object(run_batch.subprocess, "check_output", lambda *a, **kw: "offline-dry-run\n"):
            for arm in run_batch.ARMS:
                try:
                    run_batch.run_arm(arm["case"], arm["variant"])
                except StopBeforeModel:
                    pass
                else:
                    raise AssertionError("Expected to stop before model")
                assert runner.__file__ == original_file and runner.GUIDE == original_guide
    return {"arms_stopped_at_model_boundary": seen, "model_calls": 0}


def main():
    report = {"historical_replay": replay(), "mcp": asyncio.run(mcp()),
              "dry_runner": dry_runner(), "guide_chars": {
                  "before": len(server.BEFORE_GUIDE), "after": len(server.CURRENT_GUIDE)}, "model_calls": 0}
    runner.dump(HERE / "preflight.json", report)
    print(json.dumps({"saved_sources_replayed": len(report["historical_replay"]),
                      "mcp": report["mcp"], "dry_runner": report["dry_runner"],
                      "guide_chars": report["guide_chars"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
