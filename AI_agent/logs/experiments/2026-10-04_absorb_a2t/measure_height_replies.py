"""Compare real old/new tool replies on the same saved T1 geometry, offline.

Save re-exports the first saved proposal through build_bim's shared save path.
Revision repeats the last successful historical revision. Checks and delivery
use the final saved candidate. Final saved views/calibrations are held constant
on both sides; this is a controlled API replay, not another model experiment.
"""
import asyncio
from contextlib import nullcontext
import copy
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import run_bim_agent as current
from src.agent.execution.bim_claims import geometry_state
from src.agent.runtime_behaviour import tool_result_data

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / ".tmp_a2t"
BASELINE = "365f6a6b757dba2f08d22f1a6c077f8c6aa21e62"
measure = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.measure_instructions")


def fixture(case, category, side, steps):
    history = WORK / "history" / f"2026-10-03_{case}_glm_tools_t1"
    run = WORK / "height_replies" / case / category / side
    if run.exists():
        shutil.rmtree(run)
    shutil.copytree(history, run)
    manifest = json.loads((run / "inputs.json").read_text())
    manifest.pop("deadline_epoch", None)
    manifest["max_candidates"] = 24
    current.dump(run / "inputs.json", manifest)
    final = max(p.name for p in run.glob("candidate_*") if p.is_dir())
    if category == "save":
        proposal = json.loads((run / "candidate_01/proposal.json").read_text())
        for candidate in run.glob("candidate_*"):
            shutil.rmtree(candidate)
        shutil.rmtree(run / "claims")
        return run, "build_bim", dict(proposal_json=json.dumps(proposal)), dict(
            proposal="candidate_01/proposal.json", path="shared candidate save", candidate="candidate_01")
    if category == "revise":
        step = next(s for s in reversed(steps) if s["tool"] == "revise_bim" and not s["is_error"])
        arguments = step["arguments"]
        result = tool_result_data(step["result_text"])
        next_candidate = result["candidate"]
        for candidate in run.glob("candidate_*"):
            if candidate.name >= next_candidate:
                shutil.rmtree(candidate)
        # The original result application is not part of the pre-call state.
        for path in (run / "claims").glob("application_*.json"):
            row = json.loads(path.read_text())
            if row.get("candidate", "") >= next_candidate:
                path.unlink()
        return run, "revise_bim", arguments, dict(step=step["index"], candidate=next_candidate)
    tool = "check_openings" if category == "check" else "finish_bim"
    arguments = dict(candidate=final)
    if category == "check":
        arguments["heights_only"] = True
    return run, tool, arguments, dict(candidate=final, state="final saved candidate and evidence")


def capture(module, run, tool, arguments, old_facades=None):
    # Baseline runner imports the facade implementation inside its methods.
    # Bind that dependency to baseline bytes as well, not to the edited module.
    context = (patch.dict(sys.modules, {"scripts.tool_scripts.bim_agent_facade_checks": old_facades})
               if old_facades is not None else nullcontext())
    with context:
        servers = []
        with patch.object(FastMCP, "run", lambda server: servers.append(server)):
            module.serve(run)
        result = asyncio.run(servers[0].call_tool(tool, copy.deepcopy(arguments)))
    assert not getattr(result, "isError", False), result
    content = result.content if hasattr(result, "content") else result
    text_blocks = [item.text for item in content if item.type == "text"]
    data = getattr(result, "structuredContent", None) or next(
        json.loads(text) for text in text_blocks if text.startswith("{"))
    # Same pretty-print metric used by the CLI and instruction measurements.
    return data, len(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    (HERE / "height_replies").mkdir(exist_ok=True)
    old_facades = measure.baseline_module("scripts/tool_scripts/bim_agent_facade_checks.py", "a2t_old_facades", BASELINE)
    old_runner = measure.baseline_module("scripts/tool_scripts/run_bim_agent.py", "a2t_old_runner", BASELINE)
    rows = []
    for case in ("sm24", "sm25"):
        record = HERE.parent / "2026-10-01_behaviour_records/records" / f"2026-10-03_{case}_glm_tools_t1/record.json.gz"
        steps = json.loads(gzip.decompress(record.read_bytes()))["invocations"][0]["steps"]
        for category in ("save", "revise", "check", "delivery"):
            captures = {}
            proposals = {}
            for side, module, facade_module in (("old", old_runner, old_facades), ("new", current, None)):
                run, tool, arguments, source = fixture(case, category, side, steps)
                data, chars = capture(module, run, tool, arguments, facade_module)
                height_keys = [key for key in ("height_coverage", "located_height_coverage") if key in data]
                if side == "new":
                    assert height_keys == ["height_coverage"]
                    assert data["height_coverage"]["schema_version"] == "opening_heights_v2"
                captures[side] = dict(reply_chars=chars, height_fields=height_keys,
                    height_chars=sum(len(json.dumps(data[key], ensure_ascii=False, indent=2)) for key in height_keys),
                    height_summary=data.get("height_coverage", {}).get("summary"),
                    response_compacted=data.get("response_compacted", False),
                    detail_level=data.get("detail_level"))
                proposals[side] = geometry_state(json.loads((run / source["candidate"] / "proposal.json").read_text()))
                current.dump(HERE / "height_replies" / f"{case}_{category}_{side}.json", data)
            assert proposals["old"] == proposals["new"]
            row = dict(case=case, category=category, tool=tool, source=source,
                historical_record_sha256=hashlib.sha256(record.read_bytes()).hexdigest(),
                geometry_and_roles_equal=True, **captures,
                delta_chars=captures["new"]["reply_chars"]-captures["old"]["reply_chars"])
            rows.append(row)
            print(json.dumps({key: row[key] for key in ("case", "category", "delta_chars")}), flush=True)
    current.dump(HERE / "height_reply_comparison.json", dict(
        baseline_commit=BASELINE, model_requests=0, rows=rows,
        method=__doc__, chars="Unicode characters in json.dumps(reply, ensure_ascii=False, indent=2); no image payloads",
        note="Actual old/new handlers, identical saved proposals and final view/calibration context. No model behavior, drawing truth or time improvement is inferred."))


if __name__ == "__main__":
    main()
