"""D1j local evidence replay; never calls a model or writes source archives.

Run from the worktree root after activate_windows.ps1. Disposable copies live
only in AI_agent/archive/local_backup/d1j. Reference BIM is evaluation-only.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import copy
import hashlib
import importlib.util
import json
import subprocess
import time
import types
from collections import Counter, defaultdict
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit
from src.agent.runtime_roles import elevation, guidance, session as role_session
from src.agent.runtime_roles.assembly import select_deliveries
from src.agent.runtime_roles.assembly_review import floor_facts
from src.agent.runtime_roles.lineage import opening_plan
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent.runtime_roles.submission import ELEVATION_SCHEMA, SUBMISSION_TOOLS
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore, json_bytes

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASE = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup")
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1j"
REFERENCES = HERE.parent / "2026-10-06_role_division_analysis/references"
RUNS = [("sm24_run" + str(i), "sm24") for i in range(3, 8)] + [
    ("sm21_run1", "sm21"), ("sm25_run1", "sm25-L"), ("qwen27b_r1", "sm24")]


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def baseline(name):
    code = subprocess.check_output(["git", "show", "HEAD:src/agent/runtime_roles/" + name + ".py"], cwd=ROOT).decode()
    module = types.ModuleType("src.agent.runtime_roles._d1j_old_" + name)
    exec(compile(code, "HEAD:" + name, "exec"), module.__dict__)
    return module


def archive(name):
    return BASE / ("reader_model_probe" if name == "qwen27b_r1" else "role_debug") / name


def deliveries(folder):
    for path in sorted((folder / "tasks").glob("*/reader_record.json")):
        record = read(path)
        if record["status"] == "completed" and record["role_id"] == "elevation_reader":
            yield record["task_id"], read(path.parent / "reader_artifact.json")


def reference_source(reference):
    """Only for runs without any assembled source (run4 and 27B plan failed)."""
    source = {"spaces": [], "boundaries": [], "openings": []}
    for question in reference["elevation_questions"]:
        facade = question["facade"]
        for row in question["openings"]:
            identity = row["id"]
            source["spaces"].append({"id": identity, "floor_id": row["floor_id"]})
            a, b = row["span_m"]
            points = ([[a, 0], [b, 0]] if facade in {"North", "South"} else [[0, a], [0, b]])
            if facade in {"North", "West"}:
                points.reverse()
            low, high = row["sill_m"], row["head_m"]
            polygon = [[*points[0], low], [*points[1], low], [*points[1], high], [*points[0], high]]
            source["boundaries"].append({"id": identity, "vertices": polygon})
            source["openings"].append({"id": identity, "exterior": True, "host_boundary_id": identity,
                "space_ids": [identity], "kind": row["kind"], "vertices": polygon})
    source["source_model_sha256"] = hashlib.sha256(json_bytes(source)).hexdigest()
    return source


def verify_pair(pair, reference, facade):
    options = [row for question in reference["elevation_questions"] if question["facade"] == facade
               for row in question["openings"] if row["floor_id"] == pair["floor_id"] and row["kind"] == pair["kind"]]
    ranked = sorted(options, key=lambda r: abs(sum(r["span_m"]) / 2 - pair["source_world_coordinate_m"]))
    if not ranked:
        return {"status": "no_reference_opening"}
    ref = ranked[0]
    center = sum(ref["span_m"]) / 2
    source_ok = abs(center - pair["source_world_coordinate_m"]) <= .4 and abs(ref["width_m"] - pair["source_width_m"]) <= .4
    # Independent reference identity check: nearest located opening in the
    # original reading, not the fitted coordinates. 0.75 m admits the measured
    # 0.52 m drift but must still name the SAME nearest reference as the source.
    reader_ref = min(options, key=lambda r: abs(sum(r["span_m"]) / 2 - pair["artifact_world_coordinate_m"]))
    reader_ok = reader_ref["id"] == ref["id"] and abs(center - pair["artifact_world_coordinate_m"]) <= .75 and abs(ref["width_m"] - pair["artifact_width_m"]) <= .4
    return {"reference_id": ref["id"], "reference_span_m": ref["span_m"],
        "reader_nearest_reference_id": reader_ref["id"],
        "source_center_error_m": pair["source_world_coordinate_m"] - center,
        "reader_center_error_m": pair["artifact_world_coordinate_m"] - center,
        "reference_sill_m": ref["sill_m"], "reference_head_m": ref["head_m"],
        "height_within_reference_tolerance": abs(pair["sill_m"] - ref["sill_m"]) <= .3 and abs(pair["head_m"] - ref["head_m"]) <= .3,
        "identity_correct": source_ok and reader_ok}


def matching_replay():
    old = baseline("elevation")
    result = {"baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "scope": "All accepted real facade deliveries, paired with each run's final saved source. Runs with no source use an explicitly evaluation-only reference fixture. Also replay every archived match context.",
        "reference_check": "Each pair: source within reference 0.4 m along/width; raw reader must independently select the same nearest reference within 0.75 m along and 0.4 m width. Z compared separately at 0.3 m. No reference is given to production code.",
        "deliveries": [], "archived_contexts": []}
    for name, case in RUNS:
        folder = archive(name)
        reference = read(REFERENCES / (case + "_anchor.json"))
        candidates = sorted((folder / "bim").glob("candidate_*/source_model.json"))
        source = read(candidates[-1]) if candidates else reference_source(reference)
        candidate = candidates[-1].parent.name if candidates else "evaluation_reference_only"
        by_task = dict(deliveries(folder))
        for task_id, artifact in by_task.items():
            before = old.match_elevation(source, artifact, candidate=candidate)
            after = elevation.match_elevation(source, artifact, candidate=candidate)
            before_ids = {(p["artifact_opening_id"], p["source_opening_id"]) for p in before["matches"]}
            pairs = [{**p, "new": (p["artifact_opening_id"], p["source_opening_id"]) not in before_ids,
                      "reference": verify_pair(p, reference, artifact["orientation"])} for p in after["matches"]]
            added = [p for p in pairs if p["new"]]
            assert all(p["reference"]["identity_correct"] and p["reference"]["height_within_reference_tolerance"] for p in added), (name, task_id, added)
            assert before_ids <= {(p["artifact_opening_id"], p["source_opening_id"]) for p in pairs}
            result["deliveries"].append({"run": name, "task_id": task_id, "facade": artifact["orientation"],
                "candidate": candidate, "artifact_sha256": artifact["artifact_sha256"],
                "before": len(before["matches"]), "after": len(after["matches"]), "reading_count": len(artifact["openings"]),
                "source_file_sha256": hashlib.sha256(candidates[-1].read_bytes()).hexdigest() if candidates else None,
                "fits": after["horizontal_fits"], "pairs": pairs, "conflicts": after["conflicts"],
                "elevation_only": after["elevation_only"], "source_only": after["source_only"]})
        for path in sorted((folder / "role_matches").glob("*.json")):
            saved = read(path)
            artifact = by_task.get(saved["task_id"])
            source_path = folder / "bim" / saved["candidate"] / "source_model.json"
            if artifact is None or not source_path.is_file():
                raise AssertionError((name, path))
            actual = read(source_path)
            before = old.match_elevation(actual, artifact, candidate=saved["candidate"])
            after = elevation.match_elevation(actual, artifact, candidate=saved["candidate"])
            previous = {(p["artifact_opening_id"], p["source_opening_id"]) for p in before["matches"]}
            added = [{**p, "reference": verify_pair(p, reference, artifact["orientation"])} for p in after["matches"]
                     if (p["artifact_opening_id"], p["source_opening_id"]) not in previous]
            assert all(p["reference"]["identity_correct"] and p["reference"]["height_within_reference_tolerance"] for p in added)
            result["archived_contexts"].append({"run": name, "task_id": saved["task_id"], "candidate": saved["candidate"],
                "before": len(before["matches"]), "after": len(after["matches"]), "new_pairs": added})
    result["summary"] = {"deliveries": len(result["deliveries"]), "before": sum(r["before"] for r in result["deliveries"]),
        "after": sum(r["after"] for r in result["deliveries"]), "new_wrong_pairs": 0,
        "archived_match_contexts": len(result["archived_contexts"])}
    save(HERE / "matching.json", result)
    rows = ["# 全部真实立面交付逐项对位", "", "最终源稿；无源稿的 run4/27B 使用仅供评测的参照 fixture。完整误差、旧冲突及高度差见 matching.json。", "",
            "| 运行 / 交付 | 对位基准 | 改前 | 改后 | 新增 |", "|---|---|---:|---:|---:|"]
    for r in result["deliveries"]:
        rows.append(f"| {r['run']} / {r['task_id']} | {r['candidate']} | {r['before']} | {r['after']} | {r['after'] - r['before']} |")
    rows += ["", "每个已对上对象（新增标为 +；原有不符项保留显示）：", "", "| 运行 / 交付 | 图中 ID → 源 ID | 参照 ID | 身份核对 | 高度核对 | 新增 |", "|---|---|---|---|---|---|"]
    for r in result["deliveries"]:
        for p in r["pairs"]:
            ref = p["reference"]
            rows.append(f"| {r['run']} / {r['task_id']} | {p['artifact_opening_id']} → {p['source_opening_id']} | {ref.get('reference_id', '-')} | {'通过' if ref.get('identity_correct') else '原有偏差'} | {'通过' if ref.get('height_within_reference_tolerance') else '原有偏差'} | {'+' if p['new'] else ''} |")
    (HERE / "pair_table.md").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return result["summary"]


def invocations(folder, tool):
    # Root events already contain child events; do not duplicate child journals.
    for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines():
        payload = json.loads(line).get("payload", {})
        if payload.get("event_type") == "tool_invocation" and payload.get("tool_name") == tool:
            args = payload["full_arguments"]
            yield json.loads(args) if isinstance(args, str) else args


def direction_replay():
    rows = []
    for run, facade in [("sm24_run5", "East"), ("sm24_run6", "West"), ("sm24_run6", "North")]:
        call = next(a for a in invocations(archive(run), "submit_elevation_reading") if a["orientation"] == facade)
        compact = {k: v for k, v in call.items() if k not in {"orientation", "view_direction", "x_calibration"}}
        c = call["x_calibration"]
        length = 10 if facade == "North" else 20
        # All three faulty initial calls already supplied the increasing
        # image-left dimension-chain distances. Keep those observations.
        compact["x_calibration"] = {"pixel_start": c["pixel_start"], "pixel_end": c["pixel_end"],
            "distance_start_m": min(c["world_start_m"], c["world_end_m"]),
            "distance_end_m": max(c["world_start_m"], c["world_end_m"]), "facade_length_m": length}
        expanded = elevation.expand_elevation_submission(compact, facade + "/F1")
        normalized = elevation.validate_elevation_artifact(expanded, image_name=facade + "_view.png")
        rows.append({"run": run, "facade": facade, "old_parameters": call, "new_parameters": compact,
                     "derived": {k: normalized[k] for k in ("orientation", "view_direction", "x_calibration")},
                     "first_validation_passed": True, "dimensions_source": "Archived drawing overall chain: North 10 m, East/West 20 m; local pixel anchors and local distances unchanged."})
    # Validate all archived legacy artifacts without converting their meaning.
    count = sum(1 for name, _ in RUNS for _, a in deliveries(archive(name))
                if elevation.validate_elevation_artifact(a)["artifact_sha256"] == a["artifact_sha256"])
    save(HERE / "directions.json", {"replays": rows, "legacy_artifacts_readable": count})
    return {"first_validation_passed": len(rows), "legacy_artifacts_readable": count}


def helper():
    spec = importlib.util.spec_from_file_location("d1i_replay_helpers", HERE.parent / "2026-10-07_role_division_d1i/replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalTools:
    def __init__(self, run):
        self.run_directory, self.toolkit, self.calls = run, Toolkit(run), []

    async def list_tools(self):
        return [{"name": "finish_bim", "inputSchema": {"type": "object", "properties": {
            "candidate": {"type": "string"}}, "required": ["candidate"], "additionalProperties": False}}]

    async def call_tool(self, name, args):
        self.calls.append(name)
        if name == "build_plan_bim":
            value = self.toolkit.build_plan(args["image"], args["plan_json"])
        elif name == "assemble_plan_bim":
            value = self.toolkit.assemble_plans(args["floors_json"])
        elif name == "claim_transaction":
            value = self.toolkit.claim_transaction(args["candidate"], args["entries_json"])
        elif name == "revise_bim":
            value = self.toolkit.revise(args["candidate"], args["operations_json"])
        elif name == "finish_bim":
            value = self.toolkit.delivery(args["candidate"], selection_origin="agent_selected")
        else:
            raise AssertionError(name)
        return envelope(value)


def no_model(*args):
    raise AssertionError("D1j prohibits model requests")


def make_session(folder, store, limits):
    tools = LocalTools(folder / "bim")
    return RoleSession(store=store, frozen=tools, routes={}, adapter_factory=no_model, limits=limits, root=ROOT), tools


async def assembly_replay(case=None):
    helpers = helper()
    results = read(HERE / "assemblies.json")["replays"] if case and (HERE / "assemblies.json").exists() else []
    for name in ("sm24_run7", "sm21_run1", "sm25_run1"):
        if case and name != case:
            continue
        folder = SCRATCH / ("assembly_" + name + "_" + str(time.time_ns()))
        copied = helpers.prepare(archive(name), folder)
        # run7 first deliveries only: no East rework is available in this replay.
        if name == "sm24_run7":
            for p in (folder / "tasks").glob("*/reader_record.json"):
                if read(p)["task_id"] == "elev_east_r2":
                    import shutil
                    disposable = p.parent.resolve()
                    assert disposable.is_relative_to(SCRATCH.resolve())
                    shutil.rmtree(disposable)
        limits = RunLimits(model_calls=1, tool_calls=150, seconds=3600, tokens=None)
        with EventStore(folder, run_id="d1j-" + name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
            session, tools = make_session(folder, store, limits)
            args = next(invocations(archive(name), "assemble_from_readers")) if name != "sm24_run7" else {}
            response = await session.call_tool("assemble_from_readers", args)
            assert not response.get("isError"), response
            meta = response["structuredContent"]
            assert meta["source_geometry_ready"], meta
            source = session._source(meta["candidate"])
            used = [row for row in source["spaces"] if row["role"] != "unknown"]
            assert all(row.get("role_evidence") and row["role_evidence"]["source_refs"] for row in used)
            calls = list(tools.calls)
            assert (await session.call_tool("assemble_from_readers", args))["structuredContent"] == meta
            assert tools.calls == calls
            before_uses = next(read(p) for p in sorted((folder / "bim").glob("candidate_*/source_model.json"))
                               if len(read(p)["floors"]) == len(source["floors"]))
            # Uses and heights may change; all opening XY/host bindings must not.
            assert opening_plan(before_uses) == opening_plan(source)
            assert all(floor_facts(before_uses, f["id"]) == floor_facts(source, f["id"]) for f in source["floors"])
            coverage = tools.toolkit.located_heights(meta["candidate"], compact=False)
            matches = [read(p) for p in (folder / "role_matches").glob("*.json")]
            if name == "sm24_run7":
                assert len(used) == 8
                assert sum(len(r["result"]["matches"]) for r in matches) == 14
                assert tools.calls.count("claim_transaction") == 1
            results = [r for r in results if r["run"] != name]
            results.append({"run": name, "arguments": args, "candidate": meta["candidate"], "assembly": meta,
                "roles_before": [{"id": s["id"], "role": s["role"], "role_evidence": s.get("role_evidence")} for s in before_uses["spaces"]],
                "roles_after": [{"id": s["id"], "role": s["role"], "role_evidence": s.get("role_evidence")} for s in source["spaces"]],
                "known_uses": len(used), "uses_with_evidence": len(used), "height_coverage": coverage,
                "matches": matches, "opening_xy_and_hosts_unchanged": True, "repeat_created_candidates": 0,
                "internal_tools": tools.calls, "copied_inputs": copied, "source_archives_unchanged": all(
                    helpers.digest(archive(name) / p) == digest for p, digest in copied.items()),
                **helpers.saved_evidence(folder)})
            save(HERE / "assemblies.json", {"scope": "Three deterministic archived-delivery assemblies, not three new work-model runs.", "replays": results})
            print("ASSEMBLY", name, "uses", len(used), "coverage", coverage["summary"], flush=True)
    return [{"run": r["run"], "uses": r["known_uses"], "heights": r["height_coverage"]["summary"]} for r in results]


async def edit_replay():
    helpers = helper()
    results = []
    import shutil
    for index, call in enumerate(invocations(archive("sm24_run7"), "revise_bim"), 1):
        operations = json.loads(call["operations_json"])
        if isinstance(operations, dict):
            operations = operations["operations"]
        edits = []
        for op in operations:
            reason = op.get("reason", op.get("evidence", "; ".join(op.get("source_refs", []))))
            if op["op"] == "set_opening_height":
                edits.append({"action": "height", "id": op["opening_id"], "sill_m": op["z"][0], "head_m": op["z"][1],
                    "image": "East_view.png", "bbox": [2062, 383, 2216, 565] if op["opening_id"] == "W-r1" else [1724, 383, 1850, 565], "reason": reason})
            elif op["op"] == "set_space_role":
                # Furniture-based classifications are inference, including the
                # old sixth call which had labelled them observed.
                edits.append({"action": "use", "id": op["space_id"], "role": op["role"], "image": "1f_view.png", "reason": reason})
            elif op["op"] == "add_note":
                edits.append({"action": "note", "text": op["text"], "reason": "Preserve coordinator's located resolution note"})
            else:
                raise AssertionError(op)
        folder = SCRATCH / ("edit_" + str(index) + "_" + str(time.time_ns()))
        helpers.prepare(archive("sm24_run7"), folder, saved=True)
        for original in sorted((archive("sm24_run7") / "bim").glob("candidate_*")):
            if original.name <= call["candidate"] and not (folder / "bim" / original.name).exists():
                shutil.copytree(original, folder / "bim" / original.name)
        limits = RunLimits(model_calls=1, tool_calls=50, seconds=3600, tokens=None)
        with EventStore(folder, run_id="d1j-edit-" + str(index), task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
            session, tools = make_session(folder, store, limits)
            args = {"candidate": call["candidate"], "edits": edits}
            result = await session.call_tool("edit_bim", args)
            assert not result.get("isError"), result
            current = result["structuredContent"]["candidate"]
            saved_source = session._source(current)
            assert opening_plan(saved_source) == opening_plan(session._source(call["candidate"]))
            saved_values = []
            from src.agent.roles import require_role
            for edit in edits:
                if edit["action"] == "height":
                    item = next(r for r in saved_source["openings"] if r["id"] == edit["id"])
                    value = sorted({p[2] for p in item["vertices"]})
                    assert value == [edit["sill_m"], edit["head_m"]]
                elif edit["action"] == "use":
                    item = next(r for r in saved_source["spaces"] if r["id"] == edit["id"])
                    assert item["role"] == require_role(edit["role"]) and item["role_evidence"]["basis"] == "inferred"
                    assert "image:" + edit["image"] in item["role_evidence"]["source_refs"]
                    value = {"role": item["role"], "evidence": item["role_evidence"]}
                else:
                    value = read(folder / "bim" / current / "proposal.json")["unresolved"]
                    assert edit["text"] in value
                saved_values.append({"action": edit["action"], "id": edit.get("id"), "saved": value})
            count = len(tools.calls)
            assert (await session.call_tool("edit_bim", args))["structuredContent"] == result["structuredContent"]
            assert len(tools.calls) == count
            results.append({"ordinal": index, "old_arguments": call, "new_arguments": args,
                "result": result["structuredContent"], "first_attempt_success": True,
                "saved_values": saved_values, "opening_xy_and_hosts_unchanged": True, "repeat_mutations": 0})
    assert len(results) == 7
    save(HERE / "edits.json", {"scope": "Re-express all seven recorded intents using the new tool; no automatic repair of invalid old JSON and no work-model run.", "replays": results})
    return {"first_attempt_success": len(results)}


def metrics():
    old_guide = baseline("guidance")
    old_tools = baseline("session")
    chars = lambda row: len(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    rows = {role: {"before": len(old_guide.get_role_guide(role)), "after": len(guidance.get_role_guide(role))}
            for role in ("coordinator", "elevation_reader", "plan_reader")}
    before_desc = {t["name"]: t["description"] for t in old_tools.EXTRA_TOOLS}
    after_desc = {t["name"]: t["description"] for t in role_session.EXTRA_TOOLS}
    tree = ast.parse((ROOT / "scripts/tool_scripts/run_bim_agent.py").read_text(encoding="utf-8"))
    old_edit_doc = ast.get_docstring(next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "revise_bim"))
    result = {"counting": "Unicode characters; default json.dumps separators for the 2317-character schema comparison; compact sizes also reported.",
        "guides": rows, "elevation_schema": {"before": len(json.dumps(ELEVATION_SCHEMA, ensure_ascii=False)),
            "after": len(json.dumps(elevation.elevation_submission_tool()["inputSchema"], ensure_ascii=False)),
            "compact_before": chars(ELEVATION_SCHEMA), "compact_after": chars(elevation.elevation_submission_tool()["inputSchema"])},
        "elevation_tool_description": {"before": len(SUBMISSION_TOOLS["elevation_reader"]["description"]),
                                       "after": len(elevation.elevation_submission_tool()["description"])},
        "role_tool_descriptions": {name: {"before": len(before_desc.get(name, "")), "after": len(text)} for name, text in after_desc.items()},
        "local_edit_tool_description": {"before_tool": "revise_bim", "before": len(old_edit_doc),
                                        "after_tool": "edit_bim", "after": len(after_desc["edit_bim"])},
        "plan_guide_identical": old_guide.get_role_guide("plan_reader") == guidance.get_role_guide("plan_reader")}
    assert result["plan_guide_identical"]
    save(HERE / "metrics.json", result)
    return result


async def main(part, case=None):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for name, fn in (("matching", matching_replay), ("directions", direction_replay), ("metrics", metrics),
                     ("assemblies", assembly_replay), ("edits", edit_replay)):
        if part not in ("all", name):
            continue
        result = await fn(case) if name == "assemblies" else await fn() if name == "edits" else fn()
        print(name, json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=("all", "matching", "directions", "metrics", "assemblies", "edits"), default="all")
    parser.add_argument("--case", choices=("sm24_run7", "sm21_run1", "sm25_run1"))
    args = parser.parse_args()
    asyncio.run(main(args.part, args.case))
