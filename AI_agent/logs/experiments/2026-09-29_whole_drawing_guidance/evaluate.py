"""Post-generation checks for the approved sm21 runs (no model calls, no repair).

Reuses the unchanged sm21 audit (original-image positions/hosts/connections, GT
partition, exterior opening parameters) and adds the public behaviour that the
guidance package targets: references read, time and calls before the first build.
"""
import argparse
from collections import Counter
import gzip
import importlib
import json
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
BASELINE = EXPERIMENTS / "2026-09-27_sm21_whole_building_repeat_claude_run58"
load = lambda path: json.loads(Path(path).read_text())


def is_full(view):
    return view.get("box_original_pixels") == [0, 0, *view["original_size"]]


def behaviour(run):
    rows = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    start = rows[0]["time"]
    first = next((i for i, r in enumerate(rows) if r["action"] in ("build_plan_bim", "build_bim")), None)
    before = rows[:first] if first is not None else rows
    api_calls = set()
    packed = run / "agent_stream.jsonl.gz"
    with (gzip.open(packed, "rt") if packed.exists() else (run / "agent_stream.jsonl").open()) as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("type") == "assistant":
                api_calls.add(event["message"]["id"])
    return dict(
        references_read=[r["data"].get("topic") for r in rows if r["action"] == "get_bim_reference"],
        first_build_seconds=round(rows[first]["time"] - start) if first is not None else None,
        tool_calls_before_first_build=len(before),
        full_views_before_first_build=sum(r["action"] == "view_image" and is_full(r["data"]) for r in before),
        crops_before_first_build=sum(r["action"] == "view_image" and not is_full(r["data"]) for r in before),
        pixel_tools_before_first_build=sum("pixel" in r["action"] for r in before),
        tool_calls_total=len(rows), api_calls=len(api_calls),
        actions=dict(Counter(r["action"] for r in rows)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run.resolve()
    summary, receipt = load(run / "summary.json"), load(run / "agent_receipt.json")
    completed = (summary.get("agent_response_completed") is True and receipt.get("returncode") == 0
                 and not (receipt.get("result") or {}).get("is_error"))
    result = dict(run=run.name, completed=completed, elapsed_seconds=receipt.get("elapsed_seconds"),
                  actual_model=receipt.get("actual_model"), behaviour=behaviour(run))
    if completed:
        condition = load(run / "experiment_condition.json")
        frozen = dict(scope=load(BASELINE / "inputs.json")["scope"], provider="claude",
                      image_sha256=condition["image_sha256"], mode="whole_drawing_guidance_original_only_cold",
                      continuation_rounds=0, max_candidates=24)
        target = HERE / f"{run.name}_frozen.json"
        if target.exists():
            assert load(target) == frozen
        else:
            target.write_text(json.dumps(frozen, ensure_ascii=False, indent=1))
        base = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm21_current_tools_setup.audit_run")
        with patch.object(base, "HERE", HERE):
            base.audit(run)
        audit = load(run / "postrun_audit.json")
        result.update(counts=audit["counts"], strict_partition_status=audit["strict_partition_status"],
                      space_identity_findings=audit["space_identity_findings"],
                      original_openings=audit["original_openings"],
                      exterior_matched=audit["matched_exterior"],
                      exterior_parameters_match=audit["exterior_parameters_match"],
                      height_mismatches=audit["height_mismatches"],
                      unmatched_reference=audit["unmatched_reference"],
                      unmatched_built_exterior=audit["unmatched_built_exterior"])
    else:
        result["quality"] = "unknown: response did not complete; stop the batch, no retry"
    (run / "whole_drawing_evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k not in ("height_mismatches",)},
                     ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
