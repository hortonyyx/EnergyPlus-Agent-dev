"""Compare every available saved plan with the pre-A1-T compiler, without models.

Run materialize.py first. Byte hashes link selected evidence to its original
archive. Compile-only replays isolate the new guard from geometry and rendering;
the sm25 original first call is additionally replayed through real local MCP.
"""
from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts.run_bim_agent import serve
from src.agent.geometry.input_scale import ScaleMismatchError
from src.agent.geometry.plan_feedback import resolve_plan_lengths
from src.agent.geometry.plan_partition import compile_plan_partition

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / ".tmp_a1t" / "history"
BASELINE = "6deee38c548284b2e1b165d882a34b8e02bba210"
KNOWN_MM_RUNS = {"2026-09-27_sm21_guidance_ablation_run72", "sm25_runtime_subscription",
                 "2026-09-28_sm21_method_control_run85"}  # Independently confirmed in additional_run85_case.json.


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def baseline_compiler():
    relative = "src/agent/geometry/plan_partition.py"
    module = ModuleType("a1t_baseline_plan_partition")
    module.__file__ = str(ROOT / relative)
    sys.modules[module.__name__] = module
    raw = subprocess.check_output(["git", "show", f"{BASELINE}:{relative}"], cwd=ROOT)
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module.compile_plan_partition, digest(raw)


def invoke(compiler, raw, size, image):
    try:
        value, _ = resolve_plan_lengths(json.loads(raw))
        original = copy.deepcopy(value)
        result = compiler(value, image_size=size, image_name=image)
        assert value == original, "compiler mutated declaration"
        return dict(accepted=True, output_sha256=digest(canonical(result)))
    except (ValueError, TypeError, KeyError, IndexError) as error:
        return dict(accepted=False, error_type=type(error).__name__, error=str(error),
                    scale_rejected=isinstance(error, ScaleMismatchError))


def corpus():
    tracked = subprocess.check_output(["git", "ls-files", "AI_agent/logs/experiments"], cwd=ROOT, text=True)
    paths = [ROOT / name for name in tracked.splitlines()
             if "/plan_drafts/" in name and name.endswith("/plan.json") and "/runtime_snapshot/" not in name]
    paths.extend(WORK.rglob("plan_drafts/*/plan.json"))
    return sorted(set(paths))


def sm25_mcp_replay():
    record_path = WORK / "sm25_runtime_subscription/behaviour/record.json.gz"
    record = json.loads(gzip.decompress(record_path.read_bytes()))
    steps = [step for inv in record["invocations"] for step in inv["steps"]]
    step = next(step for step in steps if step["tool"] == "build_plan_bim")
    origin = WORK / "sm25_runtime_subscription/bim"
    manifest = json.loads((origin / "inputs.json").read_bytes())
    with tempfile.TemporaryDirectory(prefix="sm25-mcp-", dir=ROOT / ".tmp_a1t") as temporary:
        run = Path(temporary)
        shutil.copyfile(origin / "inputs.json", run / "inputs.json")
        shutil.copytree(origin / "images", run / "images")
        servers = []
        with patch.object(FastMCP, "run", lambda server: servers.append(server)):
            serve(run)
        with patch("scripts.tool_scripts.bim_agent_budget.time.time",
                   return_value=manifest["started_epoch"] + step["t_call"]):
            result = asyncio.run(servers[0].call_tool("build_plan_bim", step["arguments"]))
        reply = "\n".join(block.text for block in result.content if block.type == "text")
        stored = json.loads((run / "plan_drafts/draft_001/result.json").read_bytes())
        assert not stored["source_geometry_ready"] and "plan.x_anchors" in reply and "毫米" in reply
        assert not list(run.glob("candidate_*"))
        saved = (run / "plan_drafts/draft_001/plan.json").read_bytes()
        assert saved == step["arguments"]["plan_json"].encode()
        return dict(record_sha256=digest(record_path.read_bytes()), step=step["index"],
                    tool=step["tool"], arguments_sha256=digest(canonical(step["arguments"])),
                    plan_sha256=digest(saved), error=stored["error"], reply_contains_error=True,
                    original_input_bytes_preserved=True, candidate_count=0, model_requests=0)


def main():
    old_compiler, compiler_sha = baseline_compiler()
    rows, grouped = [], defaultdict(Counter)
    for path in corpus():
        run = path.parents[2]
        label = str(path.relative_to(WORK)) if path.is_relative_to(WORK) else str(path.relative_to(ROOT))
        name = run.name if run.name != "bim" else run.parent.name
        entry = dict(path=label, run=name, plan_sha256=digest(path.read_bytes()),
                     expected_units="known_mm_misuse" if name in KNOWN_MM_RUNS else "normal_or_original_invalid")
        binding = json.loads(path.with_name("input.json").read_bytes())
        manifest = json.loads((run / "inputs.json").read_bytes())
        image = binding["image"]
        size = tuple(manifest["images"][image]["size"])
        entry.update(image=image, image_size=list(size),
                     image_sha256=manifest["images"][image]["sha256"],
                     original_compilation_saved=path.with_name("compilation.json").exists())
        raw = path.read_text()
        before = invoke(old_compiler, raw, size, image)
        after = invoke(compile_plan_partition, raw, size, image)
        entry.update(before=before, after=after)
        if before["accepted"] and after["accepted"]:
            assert before["output_sha256"] == after["output_sha256"], label
            outcome = "accepted_unchanged"
        elif after.get("scale_rejected"):
            outcome = "known_mm_rejected" if name in KNOWN_MM_RUNS else "unexpected_scale_rejection"
        elif before == after:
            outcome = "original_invalid_unchanged"
        else:
            outcome = "unexpected_difference"
        entry["outcome"] = outcome
        grouped[name][outcome] += 1
        rows.append(entry)
    summary = Counter(row["outcome"] for row in rows)
    mcp = sm25_mcp_replay()
    report = dict(baseline_commit=BASELINE, baseline_compiler_sha256=compiler_sha,
                  current_compiler_sha256=digest((ROOT / "src/agent/geometry/plan_partition.py").read_bytes()),
                  model_requests=0, total=len(rows), unique_plan_sha256=len({r["plan_sha256"] for r in rows}),
                  run_labels=len(grouped), saved_run_directories=len({str(p.parents[2]) for p in corpus()}),
                  summary=dict(summary),
                  unique_accepted_normal=len({r["plan_sha256"] for r in rows if r["outcome"] == "accepted_unchanged"}),
                  original_accepted_normal=sum(r["before"]["accepted"] and r["run"] not in KNOWN_MM_RUNS for r in rows),
                  originally_compiled_mm=sum(r["original_compilation_saved"] and r["run"] in KNOWN_MM_RUNS for r in rows),
                  groups={k: dict(v) for k, v in sorted(grouped.items())}, sm25_first_call=mcp, plans=rows,
                  scope="Every tracked saved pixel-plan draft, plus selected hash-verified migration/subscription/node/T1 archives; same pre-A1-T and current compilers, exact proposal+metadata comparison. Original schema/topology errors retained, not counted as accepted normal plans.")
    (HERE / "replay_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"plans", "groups"}}, ensure_ascii=False, indent=2))
    assert not summary["unexpected_scale_rejection"] and not summary["unexpected_difference"], summary


if __name__ == "__main__":
    main()
