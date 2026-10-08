"""Replay immutable historical deliveries through local frozen tools; no model calls."""
from __future__ import annotations

import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent.runtime_entry import prepare_inputs
from src.agent.runtime_roles.lineage import metadata
from src.agent.runtime_roles.session import RoleSession
from src.agent.runtime_tools import FrozenBimTools, coordinator_role, frozen_bim_client
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore

HISTORY = Path("C:/Users/Horton/Desktop/EnergyPlus-Agent-dev/AI_agent/archive/local_backup")
SOURCES = {"d1l": HISTORY / "speed2/sm25_role_d1l", "n1": HISTORY / "merged/sm25_role_n1"}


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def historical_calls(source):
    rows = []
    for line in (source / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        payload = event["payload"]
        if event["task_id"] == "coordinator" and payload.get("event_type") == "tool_invocation":
            rows.append(payload)
    first = next(i for i, row in enumerate(rows) if row["tool_name"] == "assemble_from_readers")
    edit_kinds = Counter()
    for row in rows[first:]:
        if row["tool_name"] == "edit_bim":
            edit_kinds.update({edit["action"] for edit in row["full_arguments"].get("edits", [])})
    return rows[first]["full_arguments"]["task_ids"], {
        "all_coordinator_calls": dict(Counter(row["tool_name"] for row in rows)),
        "post_reader_calls": dict(Counter(row["tool_name"] for row in rows[first:])),
        "post_reader_total": len(rows[first:]),
        "post_reader_edit_calls_by_action": dict(edit_kinds),
        "delivered": (source / "bim/delivery.json").is_file(),
    }


def copy_reader_inputs(source, output, selected):
    """Copy only the six first-assembly deliveries and their hash-bound evidence."""
    watched = {}
    def copy(path):
        relative = path.relative_to(source)
        raw = path.read_bytes()
        watched[relative.as_posix()] = hashlib.sha256(raw).hexdigest()
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    for path in (source / "tasks").glob("*/reader_record.json"):
        record = json.loads(path.read_bytes())
        if record["task_id"] not in selected:
            continue
        assert record["status"] == "completed"
        for name in ("reader_record.json", "reader_task.json", "reader_artifact.json"):
            copy(path.with_name(name))
        for ref in (record["record_blob"], record["artifact"]["blob"]):
            copy(source / ref["uri"])
        if record["role_id"] == "plan_reader":
            candidate = record["validation"]["candidate"]
            copy(path.parent / "bim/trial_workspace" / candidate / "source_model.json")
            compiled = record["validation"].get("compiled_numeric_plan_file")
            if compiled:
                copy(path.parent / "bim/trial_workspace" / compiled)
    for path in (source / "bim/images").iterdir():
        if path.is_file():
            watched[path.relative_to(source).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return watched


async def replay(name, source, output):
    selected, old_calls = historical_calls(source)
    manifest = json.loads((source / "bim/inputs.json").read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    run, _, _ = prepare_inputs(output, images=source / "bim/images", mesh=None,
        building_input=None, scope=manifest["scope"], image_kind="drawings", max_candidates=24,
        floor_plan_images=manifest["floor_plan_images"], started_epoch=time.time(), seconds=3600)
    watched = copy_reader_inputs(source, output, selected)
    limits = RunLimits(model_calls=1, tool_calls=80, seconds=3600, tokens=None)
    public_calls, internal_calls, results = Counter(), Counter(), {}
    def no_model(*args, **kwargs):
        raise AssertionError("Historical replay must not request a model")
    with EventStore(output, run_id=output.name, task_id="coordinator", budget_limit=limits.ledger_limit()) as store:
        async with frozen_bim_client(run_directory=run, repository_root=ROOT) as client:
            frozen = FrozenBimTools(client, coordinator_role(limits.ledger_limit()), run_directory=run)
            raw_call = frozen.call_tool
            async def counted(tool, args):
                internal_calls[tool] += 1
                return await raw_call(tool, args)
            frozen.call_tool = counted
            session = RoleSession(store=store, frozen=frozen, routes={}, adapter_factory=no_model,
                                  limits=limits, root=ROOT)
            await session.list_tools()
            async def call(tool, arguments):
                public_calls[tool] += 1
                value = await session.call_tool(tool, arguments)
                results[tool] = value
                dump(output / "replay_calls" / f"{tool}_{public_calls[tool]:02d}.json", value)
                return metadata(value)
            assembled = await call("assemble_from_readers", {"task_ids": selected})
            reviewed = []
            if assembled.get("status") == "assembly_review_required":
                review = session.assembly.current()
                changes = review["changes"]
                # Developer-reviewed historical Q1 host correction. This is a
                # real relation change, not an automatic regularization waiver.
                assert name == "n1" and len(changes) == 1, changes
                change = changes[0]
                assert (change["floor_id"], change["item"]) == ("F2", "openings:WLONG"), change
                before, after = change["before"], change["after"]
                assert before["space_ids"] == ["S-e4"] and after["space_ids"] == ["S-corr-s"], change
                assert before["kind"] == after["kind"] == "window" and before["exterior"] and after["exterior"], change
                assert before["xy"] == [[15.292321, 5.997819], [23.298429, 5.997819]], change
                assert after["xy"] == [[15.292321, 5.980498], [23.298429, 5.980498]], change
                reason = ("Developer reviewed the historical duplicate-wall removal: WLONG retains its "
                          "horizontal span and width and follows the audited exterior wall alignment "
                          "from y=5.997819 to 5.980498 m. The removed 0.109051254 m overlap strip no longer "
                          "attaches it to S-e4. Its surviving exterior host belongs to S-corr-s. "
                          "Accept this explicit space-relation correction, not a blanket geometry waiver.")
                reviewed.append({"change": change, "reason": reason})
                decision = await call("review_role_assembly", {"review_id": review["review_id"],
                    "decisions": [{"change_id": change["change_id"], "reason": reason}]})
                assert decision["status"] == "reviewed", decision
                assembled = await call("assemble_from_readers", {"task_ids": selected})
                assert assembled.get("status") != "assembly_review_required", assembled
            candidate = assembled.get("candidate")
            if candidate:
                await call("check_openings", {"candidate": candidate, "heights_only": True})
                await call("inspect_candidate", {"candidate": candidate, "include_geometry": False})
                await call("finish_bim", {"candidate": candidate})
            review = session.assembly.current()
            positions = session.positions.summary()
            delivery_path = run / "delivery.json"
            delivery = json.loads(delivery_path.read_bytes()) if delivery_path.exists() else None
            source_model = session._source(candidate) if candidate else None
            checks = metadata(results["check_openings"]) if "check_openings" in results else None
    unchanged = all(hashlib.sha256((source / path).read_bytes()).hexdigest() == digest
                    for path, digest in watched.items())
    assert unchanged, "Historical input changed"
    summary = {"case": name, "source": str(source), "output": str(output), "task_ids": selected,
        "historical": old_calls, "replay_coordinator_calls": dict(public_calls),
        "replay_frozen_tool_calls": dict(internal_calls), "external_model_requests": 0,
        "delivered": delivery is not None, "candidate": candidate,
        "assembly_status": assembled.get("status"), "assembly_review_status": (review or {}).get("status"),
        "assembly_geometry_changes": len((review or {}).get("changes", [])),
        "audited_regularization_changes": len((review or {}).get("regularization_changes", [])),
        "position_summary": positions, "opening_check": checks,
        "assembly_height_write": assembled.get("height_write"),
        "explicit_developer_reviews": reviewed,
        "source_counts": ({key: len(source_model[key]) for key in ("spaces", "boundaries", "openings")}
                          if source_model else None),
        "original_inputs_unchanged": unchanged, "verified_input_files": len(watched),
        "original_input_sha256": watched,
        "finish": metadata(results["finish_bim"]) if "finish_bim" in results else None}
    dump(output / "replay_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("case", "delivered", "candidate", "assembly_status",
          "assembly_review_status", "replay_coordinator_calls", "replay_frozen_tool_calls")}), flush=True)
    return summary


async def main():
    suffix = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d_%H%M%S")
    outputs = ROOT / "AI_agent/archive/local_backup/g1" / ("historical_replay_" + suffix)
    results = [await replay(name, source, outputs / name) for name, source in SOURCES.items()]
    dump(Path(__file__).with_name("historical_replay.json"), {"mode": "offline replay of already delivered artifacts",
        "not_a_new_cold_start_or_speed_benchmark": True, "model_requests": 0, "results": results})
    assert all(row["delivered"] for row in results), "Historical replay did not deliver both cases"


if __name__ == "__main__":
    asyncio.run(main())
