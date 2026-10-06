"""Replay real reader deliveries through local tools, without model requests."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import time
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, dump
from src.agent.runtime_roles.assembly import select_deliveries
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore, json_bytes

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
ARCHIVES = Path(r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\role_debug")
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1i"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def prepare(archive, destination, *, saved=False):
    copied = {}

    def copy(relative):
        source, target = archive / relative, destination / relative
        if not source.is_file():
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied[str(relative).replace("\\", "/")] = digest(source)
        assert digest(target) == copied[str(relative).replace("\\", "/")]

    for name in ("images", *(('candidate_01', 'candidate_02', 'claims', 'elevation_reviews') if saved else ())):
        for path in (archive / "bim" / name).rglob("*"):
            if path.is_file():
                copy(path.relative_to(archive))
    copy(Path("bim/inputs.json"))
    if saved:
        copy(Path("bim/tools.jsonl"))
    else:
        for path in sorted((archive / "tasks").glob("*/reader_record.json")):
            task_path = path.parent.relative_to(archive)
            row = json.loads(path.read_bytes())
            for name in ("reader_task.json", "reader_record.json", "reader_artifact.json"):
                copy(task_path / name)
            for ref in (row.get("record_blob"), (row.get("artifact") or {}).get("blob")):
                if ref:
                    copy(Path(ref["uri"]))
            validation = row.get("validation") or {}
            if row["role_id"] == "plan_reader" and validation.get("candidate"):
                trial = task_path / "bim/trial_workspace"
                copy(trial / validation["candidate"] / "source_model.json")
                if validation.get("compiled_numeric_plan_file"):
                    copy(trial / validation["compiled_numeric_plan_file"])
    manifest = json.loads((destination / "bim/inputs.json").read_bytes())
    # Only the local replay clock is refreshed; frozen images and readings stay intact.
    manifest.update(started_epoch=time.time(), seconds=3600)
    manifest.pop("deadline_epoch", None)
    save(destination / "bim/inputs.json", manifest)
    return copied


class LocalTools:
    def __init__(self, run):
        self.run_directory, self.toolkit, self.calls = run, Toolkit(run), []

    async def list_tools(self):
        return [{"name": "finish_bim", "inputSchema": {"type": "object", "properties": {
            "candidate": {"type": "string"}}, "required": ["candidate"], "additionalProperties": False}}]

    def repeatability(self, name):
        return "non_idempotent_write"

    async def call_tool(self, name, args):
        self.calls.append(name)
        if name == "build_plan_bim":
            value = self.toolkit.build_plan(args["image"], args["plan_json"])
        elif name == "assemble_plan_bim":
            value = self.toolkit.assemble_plans(args["floors_json"])
        elif name == "claim_transaction":
            value = self.toolkit.claim_transaction(args["candidate"], args["entries_json"])
        elif name == "finish_bim":
            value = self.toolkit.delivery(args["candidate"], selection_origin="agent_selected")
            dump(self.run_directory / "delivery_selection.json", {
                "candidate": args["candidate"], "source_model_sha256": value["source_model_sha256"]})
        else:
            raise AssertionError(name)
        return envelope(value)


def geometry(source):
    return {name: [{key: value for key, value in row.items()
                   if key not in {"provenance", "source_refs", "notes"}}
                  for row in source.get(name, [])]
            for name in ("floors", "spaces", "boundaries", "openings", "connections")}


def saved_evidence(folder):
    """Keep calibration derivations after the disposable replay trees are removed."""
    return {
        "calibrations": [json.loads(p.read_bytes()) for p in sorted(
            (folder / "bim/elevation_reviews").glob("review_*.json"))],
        "height_write_references": [row["reference"] for p in sorted(
            (folder / "role_operations").glob("*.json"))
            if "match_ids" in (row := json.loads(p.read_bytes())).get("reference", {})],
    }


async def replay(name, label):
    archive = ARCHIVES / name
    folder = SCRATCH / (label + "_" + name + "_" + str(time.time_ns()))
    copied = prepare(archive, folder)
    limits = RunLimits(model_calls=1, tool_calls=100, seconds=3600, tokens=None)
    with EventStore(folder, run_id="d1i-" + name, task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        tools = LocalTools(folder / "bim")

        def forbidden(*args):
            raise AssertionError("No model requests in D1i")

        session = RoleSession(store=store, frozen=tools, routes={}, adapter_factory=forbidden,
                              limits=limits, root=ROOT)
        _, elevations, refs = select_deliveries(session)
        result = await session.call_tool("assemble_from_readers", {})
        assert not result.get("isError"), result
        meta = result["structuredContent"]
        assert meta.get("source_geometry_ready"), meta
        candidate = meta["candidate"]
        calls = list(tools.calls)
        repeated = await session.call_tool("assemble_from_readers", {})
        assert repeated["structuredContent"] == meta and tools.calls == calls
        finish = await session.call_tool("finish_bim", {"candidate": candidate})
        assert not finish.get("isError"), finish
        coverage = finish["structuredContent"]["height_coverage"]
        source = session._source(candidate)
        matches = [json.loads(p.read_bytes()) for p in (folder / "role_matches").glob("*.json")]
        return {"run": name, "label": label, "scratch": str(folder), "candidate": candidate,
            "source_file_sha256": digest(folder / "bim" / candidate / "source_model.json"),
            "geometry_sha256": hashlib.sha256(json_bytes(geometry(source))).hexdigest(),
            "geometry": geometry(source), "copied_inputs": copied, "deliveries": refs,
            "assembly": meta, "matches": matches, "height_coverage": coverage,
            "internal_tools": tools.calls, "repeat_created_candidates": 0,
            "saved_candidates": len(list((folder / "bim").glob("candidate_*/report.json"))),
            "selected": json.loads((folder / "bim/delivery_selection.json").read_bytes()),
            "reader_bytes_unchanged": all(digest(folder / p) == h for p, h in copied.items()
                                           if p.startswith(("tasks/", "blobs/"))),
            "source_archives_unchanged": all(digest(archive / p) == h for p, h in copied.items()),
            "model_service_requests": 0, **saved_evidence(folder)}


async def main(label):
    result = {"scope": "Offline real reader deliveries, not new interpretation or a live case.",
              "model_service_requests": 0, "replays": []}
    if label == "before":
        archive = ARCHIVES / "sm24_run6"
        folder = SCRATCH / ("saved_run6_" + str(time.time_ns()))
        copied = prepare(archive, folder, saved=True)
        toolkit = Toolkit(folder / "bim")
        result["saved_run6_candidate_02"] = {"source_file_sha256": digest(archive / "bim/candidate_02/source_model.json"),
            "scratch": str(folder), "copied_inputs": copied,
            **saved_evidence(folder),
            "coverage": toolkit.located_heights("candidate_02", compact=False)}
    for name in ("sm24_run6", "sm24_run3"):
        row = await replay(name, label)
        result["replays"].append(row)
        save(HERE / (label + ".json"), result)
        print(name, row["height_coverage"]["summary"], flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=("before", "after"), required=True)
    asyncio.run(main(parser.parse_args().label))
