"""Post-generation checks for the instruction-fix sm21 runs (no model calls, no repair).

Reuses the unchanged sm21 audit (original-image positions/hosts/connections, GT
partition, exterior opening parameters) and adds the criteria agreed on 09-30:
- spaces_one_to_one: every reference room seed lies in its own candidate space
  (host/connection counts stay full when rooms are merged, as in run94);
- strict_heights: every matched exterior opening's sill/head against the legacy GT
  within 0.05 m (the old 0.3 m judge tolerance passed run94's south door and east
  window), listed per object;
- drawing_differences: what each plan build reported and whether a later draft of the
  same floor still reported it (behaviour diagnosis only, never a pass criterion).
"""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
load = lambda path: json.loads(Path(path).read_text())
STRICT_HEIGHT_M = 0.05


def is_full(view):
    return view.get("box_original_pixels") == [0, 0, *view["original_size"]]


def behaviour(run):
    rows = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    start = rows[0]["time"]
    first = next((i for i, r in enumerate(rows) if r["action"] in ("build_plan_bim", "build_bim")), None)
    before = rows[:first] if first is not None else rows
    views = [r["data"] for r in rows if r["action"] == "view_image" and not is_full(r["data"])]
    api_calls = set()
    with gzip.open(run / "agent_stream.jsonl.gz", "rt") if (run / "agent_stream.jsonl.gz").exists() \
            else (run / "agent_stream.jsonl").open() as stream:
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
        crop_magnification_actual=sorted(round(min(v["display_scale_actual"]), 2) for v in views),
        capped_crops=sum("magnification_note" in v for v in views),
        last_tool_seconds=round(rows[-1]["time"] - start), tool_calls_total=len(rows),
        api_calls=len(api_calls), actions=dict(Counter(r["action"] for r in rows)))


def difference_trace(run):
    """Items each saved draft reported, and whether the next draft of that image still did."""
    drafts = []
    for folder in sorted((run / "plan_drafts").glob("draft_*")):
        report = folder / "drawing_differences.json"
        if report.is_file():
            data = load(report)
            drafts.append(dict(draft=folder.name, image=load(folder / "input.json")["image"],
                               status=data["status"], total=data["total"], counts=data["counts"],
                               items=[{k: v for k, v in item.items() if k not in ("check", "look_box")}
                                      for item in data["items"]]))
    by_image = {}
    for row in drafts:
        by_image.setdefault(row["image"], []).append(row)
    near = lambda a, b: (a["type"] == b["type"] and a.get("axis") == b.get("axis")
                         and all(abs(u - v) <= 12 for u, v in zip(_coords(a), _coords(b))))
    for rows in by_image.values():
        for row, following in zip(rows, rows[1:]):
            row["next_draft"] = following["draft"]
            for item in row["items"]:
                item["still_reported_in_next_draft"] = any(near(item, other) for other in following["items"])
    return drafts


def _coords(item):
    """Pixel position of an item for matching it across drafts (not identity)."""
    place = item.get("declared") or item
    values = [place.get("x_px"), place.get("y_px")]
    return [v for pair in values for v in (pair if isinstance(pair, list) else [pair]) if v is not None]


# The original audit pairs candidate floors with the 1F/2F plans by z order, whatever
# the model named them (run99 used 1F/2F, earlier runs F1/F2); check the same floors.
EXPECTED_FLOOR_COUNT = 2


def spaces_one_to_one(original, source):
    """Every reference seed in exactly one candidate space, each candidate space holding
    exactly one seed, on every expected floor of a completed original-image audit."""
    if original.get("status") == "not_run" or not original.get("floors"):
        return dict(pass_=False, findings=[dict(issue="original-image audit not run", detail=original.get("reason"))])
    findings = []
    floors = {floor["floor_id"]: floor.get("space_identity_by_interior_point", {}) for floor in original["floors"]}
    expected = [floor["id"] for floor in sorted(source["floors"], key=lambda floor: floor["z_floor"])]
    if len(expected) != EXPECTED_FLOOR_COUNT:
        findings.append(dict(issue="floor count mismatch", expected=EXPECTED_FLOOR_COUNT, source=len(expected)))
    for floor_id in expected:
        if floor_id not in floors:
            findings.append(dict(floor=floor_id, issue="floor missing from the audit"))
            continue
        mapping = floors[floor_id]
        holders = Counter(ids[0] for ids in mapping.values() if len(ids) == 1)
        for seed, ids in mapping.items():
            if len(ids) != 1:
                findings.append(dict(floor=floor_id, seed=seed, candidate_spaces=ids, issue="not exactly one space"))
            elif holders[ids[0]] > 1:
                findings.append(dict(floor=floor_id, seed=seed, candidate_space=ids[0],
                                     issue="shared with another reference room"))
        for space in source["spaces"]:
            if space.get("floor_id") == floor_id and space["id"] not in holders:
                findings.append(dict(floor=floor_id, candidate_space=space["id"], issue="no reference room"))
    return dict(pass_=not findings, findings=findings)


def strict_heights(run):
    diagnostic = load(run / "evaluation/gt/final_opening_diagnostic.json")
    rows = []
    for row in diagnostic["matched"]:
        delta = [round(abs(a - b), 3) for a, b in zip(row["reference_z_m"], row["candidate_z_m"])]
        rows.append(dict(opening_id=row["opening_id"], reference_id=row["reference_id"], floor=row["floor"],
                         facade=row["facade"], kind=row["kind"], reference_z_m=row["reference_z_m"],
                         candidate_z_m=row["candidate_z_m"], z_delta_m=delta,
                         within_strict=max(delta) <= STRICT_HEIGHT_M))
    within = sum(r["within_strict"] for r in rows)
    return dict(tolerance_m=STRICT_HEIGHT_M, matched=len(rows), within=within,
                pass_=(within == len(rows) and not diagnostic["unmatched_reference"]
                       and not diagnostic["unmatched_built_exterior"]),
                mismatches=[r for r in rows if not r["within_strict"]],
                unmatched_reference=diagnostic["unmatched_reference"],
                unmatched_built_exterior=diagnostic["unmatched_built_exterior"], all=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run.resolve()
    summary, receipt = load(run / "summary.json"), load(run / "agent_receipt.json")
    completed = (summary.get("agent_response_completed") is True and receipt.get("returncode") == 0
                 and not (receipt.get("result") or {}).get("is_error"))
    result = dict(run=run.name, completed=completed, elapsed_seconds=receipt.get("elapsed_seconds"),
                  actual_model=receipt.get("actual_model"), behaviour=behaviour(run),
                  drawing_differences=difference_trace(run))
    if completed:
        condition = load(run / "experiment_condition.json")
        scope = load(run / "inputs.json")["scope"]
        assert hashlib.sha256(scope.encode()).hexdigest() == condition["scope_sha256"]
        frozen = dict(scope=scope, provider="claude",
                      image_sha256={k: v["sha256"] for k, v in load(run / "inputs.json")["images"].items()},
                      mode="instruction_fix_original_only_cold", continuation_rounds=0, max_candidates=24)
        target = HERE / f"{run.name}_frozen.json"
        if target.exists():
            assert load(target) == frozen
        else:
            target.write_text(json.dumps(frozen, ensure_ascii=False, indent=1))
        base = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm21_current_tools_setup.audit_run")
        started = time.time()
        try:
            with patch.object(base, "HERE", HERE):
                base.audit(run)
            result["run58_same_task_comparison"] = "written"
        except AssertionError:
            line = traceback.extract_tb(sys.exc_info()[2])[-1].line or ""
            if ("old_inputs['scope'] == manifest['scope']" not in line
                    or (run / "postrun_audit.json").stat().st_mtime < started):
                raise
            result["run58_same_task_comparison"] = "not written: scope differs from run58"
        audit = load(run / "postrun_audit.json")
        result.update(counts=audit["counts"], strict_partition_status=audit["strict_partition_status"],
                      space_identity_findings=audit["space_identity_findings"],
                      spaces_one_to_one=spaces_one_to_one(audit["original_openings"], load(
                          run / audit["candidate"] / "source_model.json")),
                      original_openings=audit["original_openings"],
                      exterior_matched=audit["matched_exterior"],
                      exterior_parameters_match_old_tolerance=audit["exterior_parameters_match"],
                      strict_heights=strict_heights(run),
                      unresolved=audit["unresolved"], source_assumptions=audit["source_assumptions"])
    else:
        result["quality"] = "unknown: response did not complete; stop the batch, no retry"
    (run / "fix_evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    brief = {k: v for k, v in result.items() if k not in ("drawing_differences", "original_openings", "strict_heights")}
    if "strict_heights" in result:
        brief["strict_heights"] = {k: v for k, v in result["strict_heights"].items() if k != "all"}
    print(json.dumps(brief, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
