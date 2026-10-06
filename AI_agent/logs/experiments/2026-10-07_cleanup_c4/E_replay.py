"""Offline C4-E replay of sm24 run6 candidate_02 through revise and delivery."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, dump
from src.agent.execution.bim_claim_state import project
from src.agent.execution.bim_height_coverage import height_coverage
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore


MAIN_RUN = Path(
    r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup"
    r"\role_debug\sm24_run6"
)
HERE = Path(__file__).resolve().parent
REPLAY = (
    HERE.parents[2] / "archive" / "local_backup" / "c4" / "e_replay"
).resolve()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_tree(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target)


def prepare_replay() -> dict:
    expected_parent = (
        HERE.parents[2] / "archive" / "local_backup" / "c4"
    ).resolve()
    if REPLAY.parent != expected_parent or REPLAY.name != "e_replay":
        raise ValueError("refusing to replace an unexpected replay directory")
    if REPLAY.exists():
        shutil.rmtree(REPLAY)
    replay_bim = REPLAY / "bim"
    replay_store = REPLAY / "store"
    replay_bim.mkdir(parents=True)
    replay_store.mkdir(parents=True)

    source_bim = MAIN_RUN / "bim"
    for name in ("candidate_01", "candidate_02", "claims", "images",
                 "image_overlays", "overlay_calibrations", "elevation_reviews",
                 "plan_drafts", "tool_reports"):
        copy_tree(source_bim / name, replay_bim / name)
    for name in ("inputs.json", "tools.jsonl"):
        copy_file(source_bim / name, replay_bim / name)

    copied_blobs = set()
    task_count = 0
    for source_record in sorted((MAIN_RUN / "tasks").glob("*/reader_record.json")):
        task_count += 1
        source_task = source_record.parent
        target_task = replay_store / "tasks" / source_task.name
        record = json.loads(source_record.read_bytes())
        for name in ("reader_task.json", "reader_record.json", "reader_artifact.json"):
            if (source_task / name).is_file():
                copy_file(source_task / name, target_task / name)
        references = [record["record_blob"]]
        if record.get("artifact"):
            references.append(record["artifact"]["blob"])
        for reference in references:
            relative = Path(reference["uri"])
            copy_file(MAIN_RUN / relative, replay_store / relative)
            copied_blobs.add(reference["sha256"])
        validation = record.get("validation") or {}
        if record.get("role_id") == "plan_reader" and validation.get("candidate"):
            relative = Path("bim") / "trial_workspace" / validation["candidate"] / "source_model.json"
            copy_file(source_task / relative, target_task / relative)

    copy_tree(MAIN_RUN / "role_operations", replay_store / "role_operations")
    for name in ("role_floor_sources.json",):
        copy_file(MAIN_RUN / name, replay_store / name)

    copied_files = [path for path in REPLAY.rglob("*") if path.is_file()]
    return {
        "source_run_bytes": sum(path.stat().st_size for path in MAIN_RUN.rglob("*") if path.is_file()),
        "copied_bytes_before_replay": sum(path.stat().st_size for path in copied_files),
        "copied_files_before_replay": len(copied_files),
        "reader_tasks": task_count,
        "referenced_blobs": len(copied_blobs),
        "candidate_02_source_sha256": sha256(source_bim / "candidate_02" / "source_model.json"),
    }


class FrozenAdapter:
    def __init__(self, run_directory: Path):
        self.run_directory = run_directory
        self.toolkit = Toolkit(run_directory)

    async def list_tools(self):
        object_schema = {
            "type": "object",
            "properties": {
                "candidate": {"type": "string"},
                "operations_json": {"type": "string"},
            },
            "required": ["candidate", "operations_json"],
            "additionalProperties": False,
        }
        finish_schema = {
            "type": "object",
            "properties": {"candidate": {"type": "string"}},
            "required": ["candidate"],
            "additionalProperties": False,
        }
        return [
            {"name": "revise_bim", "description": "offline real implementation", "inputSchema": object_schema},
            {"name": "finish_bim", "description": "offline real implementation", "inputSchema": finish_schema},
        ]

    def repeatability(self, name):
        return "non_idempotent_write" if name in {"revise_bim", "finish_bim"} else "read_only"

    async def call_tool(self, name, arguments):
        if name == "revise_bim":
            return envelope(self.toolkit.revise(
                arguments["candidate"], arguments["operations_json"]
            ))
        if name == "finish_bim":
            result = self.toolkit.delivery(
                arguments["candidate"], selection_origin="agent_selected"
            )
            dump(self.run_directory / "delivery_selection.json", {
                "candidate": arguments["candidate"],
                "source_model_sha256": result["source_model_sha256"],
            })
            self.toolkit.log("finish_bim", result)
            return envelope(result)
        raise ValueError(name)

    def snapshot_state(self):
        return {}

    def artifacts(self):
        return []

    def image_origins(self, raw):
        return []


def metadata(result: dict) -> dict:
    return result.get("structuredContent") or {}


def window_z(run: Path, candidate: str, identity: str) -> list[float]:
    proposal = json.loads((run / candidate / "proposal.json").read_bytes())
    return next(row["z"] for row in proposal["geometry"]["windows"] if row["id"] == identity)


def candidate_summary(toolkit: Toolkit, candidate: str) -> dict:
    state = project(toolkit.claims(), candidate)
    delivery_height = toolkit.located_heights(candidate, state, compact=False)
    claim_height = height_coverage(toolkit.claims(), candidate, state)
    tracked_ids = {
        "D1", "D2", "D3", "W_T1", "W_E1", "W_E2", "W_E3", "W_B1"
    }
    tracked_delivery = {
        row["opening_id"]: {
            key: row.get(key)
            for key in ("status", "evidence", "issues")
            if key in row
        }
        for row in delivery_height.get("openings", [])
        if row.get("opening_id") in tracked_ids
    }
    tracked_claims = {
        row["opening_id"]: {
            "coverage_state": row.get("coverage_state"),
            "image_height_evidence_linked": row.get("image_height_evidence_linked"),
            "retained_claim_ids": sorted({
                evidence["claim_id"]
                for evidence in row.get("retained_image_evidence", [])
            }),
        }
        for row in claim_height.get("openings", [])
        if row.get("opening_id") in tracked_ids
    }
    return {
        "candidate": candidate,
        "source_model_sha256": sha256(toolkit.run / candidate / "source_model.json"),
        "claim_states": {
            row["id"]: row["state"] for row in state.get("claims", [])
        },
        "claim_height_summary": claim_height.get("summary"),
        "delivery_height_summary": delivery_height.get("summary"),
        "tracked_claim_height_rows": tracked_claims,
        "tracked_delivery_height_rows": tracked_delivery,
        "w_e2_z": window_z(toolkit.run, candidate, "W_E2"),
    }


def delivery_summary(result: dict) -> dict:
    value = metadata(result)
    height = value.get("height_coverage") or {}
    selection_file = REPLAY / "bim" / "delivery_selection.json"
    selection = (
        json.loads(selection_file.read_bytes()) if selection_file.is_file() else None
    )
    return {
        "is_error": result.get("isError", False),
        "candidate": value.get("candidate"),
        "selection_origin": value.get("selection_origin"),
        "generation_status": value.get("generation_status"),
        "delivery_blocked": height.get("delivery_blocked"),
        "selection_persisted": selection,
        "adopted_unapplied_claims": value.get("adopted_unapplied_claims"),
        "height_summary": height.get("summary"),
        "assembly_review": value.get("assembly_review"),
    }


async def replay() -> dict:
    copy = prepare_replay()
    run = REPLAY / "bim"
    store_dir = REPLAY / "store"
    frozen = FrozenAdapter(run)
    limits = RunLimits(model_calls=1, tool_calls=20, seconds=600, tokens=1000)
    with EventStore(
        store_dir,
        run_id="c4-e-replay",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as store:
        session = RoleSession(
            store=store,
            frozen=frozen,
            routes={},
            adapter_factory=lambda *args: None,
            limits=limits,
            root=HERE.parents[3],
        )
        await session.list_tools()
        baseline_delivery = frozen.toolkit.delivery(
            "candidate_02", selection_origin="offline_baseline_probe"
        )
        baseline = candidate_summary(frozen.toolkit, "candidate_02")

        old_z = baseline["w_e2_z"]
        height_operation = [{
            "op": "update_window",
            "id": "W_E2",
            "changes": {"z": [old_z[0], round(old_z[1] + 0.01, 6)]},
            "reason": "Offline C4-E bounded replay: test a 0.01 m height-only revision.",
            "source_refs": ["offline replay; no new drawing evidence"],
        }]
        height_result = await session.call_tool("revise_bim", {
            "candidate": "candidate_02",
            "operations_json": json.dumps(height_operation, ensure_ascii=False),
        })
        height_meta = metadata(height_result)
        if height_result.get("isError") or not height_meta.get("candidate"):
            raise RuntimeError("height revision failed: " + json.dumps(height_meta, ensure_ascii=False))
        height_candidate = height_meta["candidate"]
        height_full_review = session.assembly.check(height_candidate, require_all=True)
        height_finish = delivery_summary(
            await session.call_tool("finish_bim", {"candidate": height_candidate})
        )

        proposal = json.loads((run / "candidate_02" / "proposal.json").read_bytes())
        old_note = proposal["assumptions"][0]
        note_operation = [{
            "op": "replace_note",
            "field": "assumptions",
            "old": old_note,
            "replacement": [old_note + " Offline replay clarification; geometry unchanged."],
            "reason": "Offline C4-E finite non-geometry revision.",
            "source_refs": ["offline replay of the saved candidate"],
        }]
        note_result = await session.call_tool("revise_bim", {
            "candidate": "candidate_02",
            "operations_json": json.dumps(note_operation, ensure_ascii=False),
        })
        note_meta = metadata(note_result)
        if note_result.get("isError") or not note_meta.get("candidate"):
            raise RuntimeError("note revision failed: " + json.dumps(note_meta, ensure_ascii=False))
        note_candidate = note_meta["candidate"]
        note_full_review = session.assembly.check(note_candidate, require_all=True)
        note_finish = delivery_summary(
            await session.call_tool("finish_bim", {"candidate": note_candidate})
        )

        result = {
            "source": {
                "main_run": str(MAIN_RUN),
                "external_model_requests": 0,
                **copy,
            },
            "baseline": {
                **baseline,
                "delivery": {
                    "adopted_unapplied_claims": baseline_delivery.get("adopted_unapplied_claims"),
                    "height_summary": (baseline_delivery.get("height_coverage") or {}).get("summary"),
                },
            },
            "height_plus_0_01m": {
                "parent": "candidate_02",
                "candidate": height_candidate,
                "claim_application": {
                    key: height_meta.get("claim_application", {}).get(key)
                    for key in ("status", "parameters_without_claims", "outside_declared_scope")
                },
                "source_geometry_ready": height_meta.get("source_geometry_ready"),
                "assembly_review_from_revise": height_meta.get("assembly_review"),
                "full_delivery_review": height_full_review,
                "candidate_state": candidate_summary(frozen.toolkit, height_candidate),
                "finish": height_finish,
            },
            "note_only_revision": {
                "parent": "candidate_02",
                "candidate": note_candidate,
                "claim_application": {
                    key: note_meta.get("claim_application", {}).get(key)
                    for key in ("status", "parameters_without_claims", "outside_declared_scope")
                },
                "source_geometry_ready": note_meta.get("source_geometry_ready"),
                "assembly_review_from_revise": note_meta.get("assembly_review"),
                "full_delivery_review": note_full_review,
                "candidate_state": candidate_summary(frozen.toolkit, note_candidate),
                "finish": note_finish,
            },
        }

    files = [path for path in REPLAY.rglob("*") if path.is_file()]
    result["replay_directory"] = {
        "path": str(REPLAY),
        "files_after_replay": len(files),
        "bytes_after_replay": sum(path.stat().st_size for path in files),
    }
    (REPLAY / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


if __name__ == "__main__":
    print(json.dumps(asyncio.run(replay()), ensure_ascii=False, sort_keys=True))
