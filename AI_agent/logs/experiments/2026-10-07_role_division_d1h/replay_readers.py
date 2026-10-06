"""Replay immutable run3/run4 deliveries through local tools; no model adapter."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import time
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit
from src.agent.runtime_roles.artifacts import ArtifactRegistry
from src.agent.runtime_roles.assembly import select_deliveries
from src.agent.runtime_roles.elevation import match_elevation
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore

ROOT = Path(__file__).resolve().parents[4]
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1h"
OUTPUT = Path(__file__).with_name("reader_replay.json")


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalTools:
    def __init__(self, run):
        self.run_directory, self.toolkit, self.calls = run, Toolkit(run), []

    async def call_tool(self, name, args):
        self.calls.append(name)
        if name == "build_plan_bim":
            value = self.toolkit.build_plan(args["image"], args["plan_json"])
        elif name == "assemble_plan_bim":
            value = self.toolkit.assemble_plans(args["floors_json"])
        elif name == "claim_transaction":
            value = self.toolkit.claim_transaction(args["candidate"], args["entries_json"])
        else:
            raise AssertionError(name)
        return envelope(value)


def forbidden_adapter(*args):
    raise AssertionError("D1h permits zero model service requests")


def source_summary(source, elevations):
    z = {r["id"]: sorted({p[2] for p in r["vertices"]}) for r in source["openings"]}
    heights = {}
    for floor in {r["floor_id"] for r in source["spaces"]}:
        spaces = [r for r in source["spaces"] if r["floor_id"] == floor]
        heights[floor] = {"z_floor": sorted({r["z_floor"] for r in spaces}),
                         "ceiling_height": sorted({r["height"] for r in spaces})}
    matches = []
    for task_id, artifact in elevations.items():
        match = match_elevation(source, artifact)
        by_id = {r["id"]: r for r in artifact["openings"]}
        for row in match["matches"]:
            expected = by_id[row["artifact_opening_id"]]
            matches.append({"task_id": task_id, "source_id": row["source_opening_id"],
                "artifact_opening_id": row["artifact_opening_id"], "actual_z": z[row["source_opening_id"]],
                "expected_z": [expected["sill_m"], expected["head_m"]]})
    return {"floor_heights": heights, "opening_heights": z, "facade_matches": matches,
            "matched_heights_correct": all(r["actual_z"] == r["expected_z"] for r in matches),
            "spaces": len(source["spaces"]), "openings": len(z)}


async def replay(archive):
    folder = SCRATCH / "reader_replays" / (archive.name + "-" + str(time.time_ns()))
    folder.mkdir(parents=True)
    # Readers and their original hash receipts remain byte-for-byte unchanged.
    for name in ("tasks", "blobs"):
        shutil.copytree(archive / name, folder / name)
    run = folder / "bim"
    run.mkdir()
    shutil.copytree(archive / "bim/images", run / "images")
    manifest = json.loads((archive / "bim/inputs.json").read_bytes())
    assert manifest["max_candidates"] == 24
    manifest.update(started_epoch=time.time(), seconds=3600)
    save(run / "inputs.json", manifest)
    limits = RunLimits(model_calls=1, tool_calls=100, tokens=None, seconds=3600)
    with EventStore(folder, run_id="d1h-" + archive.name, task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        frozen = LocalTools(run)
        session = RoleSession(store=store, frozen=frozen, routes={}, adapter_factory=forbidden_adapter,
                              limits=limits, root=ROOT)
        records = {p.relative_to(archive).as_posix(): digest(p)
                   for p in (archive / "tasks").glob("*/reader_record.json")}
        strict = {"status": "accepted_deliveries_only"}
        try:
            _, elevations, _ = select_deliveries(session)
        except ValueError as error:
            strict = {"status": "no_accepted_plan", "reason": str(error), "candidate": None,
                "action": "Dispatch a new plan task with normalized target F1; the failed/running run4 plans are not deliveries."}
            # A labelled supplemental comparison tests the actual run4 facade
            # deliveries. This is not represented as a successful run4 replay.
            prior = SCRATCH / "runs/sm24_run3"
            inherited = []
            for task in (prior / "tasks").glob("*/reader_task.json"):
                if json.loads(task.read_bytes())["role_id"] == "plan_reader":
                    shutil.copytree(task.parent, folder / "tasks" / task.parent.name)
                    inherited.append(task.parent.name)
            shutil.copytree(prior / "blobs", folder / "blobs", dirs_exist_ok=True)
            session.registry = ArtifactRegistry(store)
            _, elevations, _ = select_deliveries(session)
            strict["supplement"] = "run3 accepted plan + run4 accepted facades (no fabricated or failed plan)"
            strict["inherited_plan_directories"] = inherited
        raw = await session.call_tool("assemble_from_readers", {})
        assert not raw.get("isError"), raw
        value = raw["structuredContent"]
        assert value["source_geometry_ready"], value
        count = len(list(run.glob("candidate_*/report.json")))
        calls = list(frozen.calls)
        repeated = await session.call_tool("assemble_from_readers", {})
        assert repeated["structuredContent"] == raw["structuredContent"] and frozen.calls == calls
        assert len(list(run.glob("candidate_*/report.json"))) == count <= 24
        source = session._source(value["candidate"])
        baseline = ROOT / "AI_agent/archive/local_backup/d1h/runs/sm24_run3/bim/candidate_18/source_model.json"
        return {"archive": archive.name, "reader_records": records, "strict_replay": strict, "report": value,
                "result": source_summary(source, elevations),
                "run3_final": {"candidate": "candidate_18", "sha256": digest(baseline),
                    **source_summary(json.loads(baseline.read_bytes()), elevations)},
                "saved_candidates": count, "internal_tool_calls": calls,
                "coordinator_assembly_calls": 1, "identical_repeat_new_candidates": 0,
                "source_sha256": digest(run / value["candidate"] / "source_model.json"),
                "model_service_requests": 0}


async def main():
    rows = []
    for name in ("sm24_run3", "sm24_run4"):
        archive = SCRATCH / "runs" / name
        if archive.is_dir():
            row = await replay(archive)
            rows.append(row)
            save(OUTPUT, {"scope": "Offline saved-reader replay, not new interpretation or a live case.",
                          "model_service_requests": 0, "replays": rows})
            print(name, row.get("status", row.get("report", {}).get("status")), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
