"""Read-only sm25 height-evidence replay for the G1 handoff."""

from __future__ import annotations

import asyncio
import copy
import json
import shutil
import tempfile
from pathlib import Path

from scripts.tool_scripts.bim_agent_facade_checks import located_height_report
from scripts.tool_scripts.run_bim_agent import Toolkit
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.runtime_roles.config import load_roles
from src.agent.runtime_roles.elevation import match_elevation, validate_elevation_artifact
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore


RUN = Path(
    r"C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup"
    r"\speed2\sm25_role_d1l"
)
PREFIX = "Atomic role elevation height batch: "


class _LocalTools:
    def __init__(self, run):
        self.run_directory = run
        self.toolkit = Toolkit(run)

    async def call_tool(self, name, arguments):
        if name == "claim_transaction":
            return envelope(self.toolkit.claim_transaction(
                arguments["candidate"], arguments["entries_json"]
            ))
        raise AssertionError(name)


def _routes():
    return load_roles({role: {
        "provider": "scripted", "model": "scripted-model",
        "reasoning_effort": "medium", "output_tokens": 1000,
    } for role in ("coordinator", "plan_reader", "elevation_reader")}, allow_scripted=True)


def explicit_replay(old_values):
    scratch_root = Path(__file__).resolve().parents[3] / "archive/local_backup/g1"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="height-replay-", dir=scratch_root) as temporary:
        workspace = Path(temporary)
        run = workspace / "bim"
        run.mkdir()
        shutil.copytree(RUN / "bim/images", run / "images")
        shutil.copy2(RUN / "bim/inputs.json", run / "inputs.json")
        proposal = json.loads((RUN / "bim/candidate_11/proposal.json").read_bytes())
        result = export_source_proposal(proposal, run / "candidate_01")
        if not result["source_geometry_ready"]:
            raise RuntimeError(result)
        limits = RunLimits(model_calls=1, tool_calls=100, tokens=10_000, seconds=600)
        with EventStore(workspace / "journal", run_id="g1-height-replay", task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            session = RoleSession(store=store, frozen=_LocalTools(run), routes=_routes(),
                adapter_factory=lambda *args: (_ for _ in ()).throw(
                    AssertionError("offline replay must not call a model")),
                limits=limits, root=Path(__file__).resolve().parents[4])
            delivered = {}
            for record_path in sorted((RUN / "tasks").glob("*/reader_record.json")):
                old_record = json.loads(record_path.read_bytes())
                if old_record.get("role_id") != "elevation_reader":
                    continue
                artifact = validate_elevation_artifact(json.loads(
                    (RUN / old_record["artifact"]["path"]).read_bytes()
                ))
                task_id = old_record["task_id"]
                task = session._task({"task_id": task_id, "role_id": "elevation_reader",
                    "image": artifact["image"], "target": artifact["orientation"],
                    "instructions": "Offline immutable sm25 height replay."})
                saved = session.registry.save(task, status="completed", artifact=artifact)
                report = match_elevation(session._source("candidate_01"), artifact,
                                         candidate="candidate_01")
                pairs = [*report["matches"], *[
                    row for row in report["conflicts"]
                    if row.get("type") == "position_or_width_conflict" and not row.get("ambiguous")
                ]]
                by_id = {row["id"]: row for row in artifact["openings"]}
                for pair in pairs:
                    delivered[pair["source_opening_id"]] = {
                        "task_id": task_id, "sha256": saved["artifact"]["sha256"],
                        "artifact": by_id[pair["artifact_opening_id"]],
                    }
            if len(delivered) != 33:
                raise RuntimeError(f"expected 33 unique delivered mappings, got {len(delivered)}")
            edits, adjustments = [], []
            for opening_id in sorted(delivered):
                item = delivered[opening_id]
                artifact = item["artifact"]
                new_height = [artifact["sill_m"], artifact["head_m"]]
                old_height = old_values[opening_id]
                difference = max(abs(a - b) for a, b in zip(old_height, new_height, strict=True))
                if difference:
                    adjustments.append({"opening_id": opening_id,
                        "old_height_m": old_height, "artifact_height_m": new_height,
                        "max_abs_difference_m": difference})
                edits.append({"action": "height", "id": opening_id,
                    "sill_m": new_height[0], "head_m": new_height[1],
                    "reason": "Offline replay of the immutable delivered reader opening row.",
                    "reader_evidence": {"task_id": item["task_id"],
                        "sha256": item["sha256"], "opening_id": artifact["id"]}})
            response = asyncio.run(session.call_tool("edit_bim", {
                "candidate": "candidate_01", "edits": edits,
            }))
            if response.get("isError"):
                raise RuntimeError(response)
            candidate = response["structuredContent"]["candidate"]
            located = located_height_report(session.frozen.toolkit, candidate)
            return {"candidate": candidate, "summary": located["summary"],
                "artifact_reference_count": len(edits),
                "review_receipt_count": len(list((run / "elevation_reviews").glob("review_*.json"))),
                "new_view_count": len(list((run / "image_views").glob("view_*.json"))),
                "adjustments": adjustments}


def main():
    toolkit = Toolkit(RUN / "bim")
    report = {}
    for candidate in ("candidate_09", "candidate_11", "candidate_15"):
        located = located_height_report(toolkit, candidate)
        report[candidate] = located["summary"]

    claim = json.loads((RUN / "bim/claims/claim_0002.json").read_bytes())
    trace = json.loads(claim["claim"]["reason"][len(PREFIX):])["per_opening"]
    source = json.loads((RUN / "bim/candidate_11/source_model.json").read_bytes())
    delivered_rows = []
    matched = {}
    for record_path in sorted((RUN / "tasks").glob("*/reader_record.json")):
        record = json.loads(record_path.read_bytes())
        if record.get("role_id") != "elevation_reader":
            continue
        artifact = validate_elevation_artifact(json.loads(
            (RUN / record["artifact"]["path"]).read_bytes()
        ))
        delivered_rows.extend((artifact["image"], row) for row in artifact["openings"])
        match = match_elevation(source, artifact, candidate="candidate_11")
        identity_pairs = [*match["matches"], *[
            row for row in match["conflicts"]
            if row.get("type") == "position_or_width_conflict" and not row.get("ambiguous")
        ]]
        matched.update({row["source_opening_id"]: (artifact["image"], row["artifact_opening_id"])
                        for row in identity_pairs})

    exact, exact_and_matched, unresolved = 0, 0, []
    value_differences = []
    for row in trace:
        target = row["object"]["id"]
        value = claim["resolved_values"][row["value"]]
        choices = [opening for image, opening in delivered_rows
                   if image == row["source"]["image"]
                   and opening["bbox"] == row["source"]["box"]
                   and [opening["sill_m"], opening["head_m"]] == value]
        paired = next((opening for image, opening in delivered_rows
                       if (image, opening["id"]) == matched.get(target)), None)
        if paired is not None:
            value_differences.append({"opening_id": target,
                "max_abs_difference_m": max(abs(a - b) for a, b in zip(
                    value, [paired["sill_m"], paired["head_m"]], strict=True))})
        if len(choices) == 1:
            exact += 1
            if matched.get(target) == (row["source"]["image"], choices[0]["id"]):
                exact_and_matched += 1
                continue
        unresolved.append({"opening_id": target, "exact_artifact_rows": [r["id"] for r in choices],
                           "fresh_match_artifact_opening_id": matched.get(target)})
    report["claim_0002_exact_rows"] = exact
    report["claim_0002_exact_rows_with_fresh_match"] = exact_and_matched
    report["claim_0002_value_difference_max_m"] = max(
        row["max_abs_difference_m"] for row in value_differences
    )
    report["claim_0002_value_differences_over_1mm"] = [
        row for row in value_differences if row["max_abs_difference_m"] > 0.001
    ]
    report["claim_0002_unresolved"] = unresolved
    old_values = {row["object"]["id"]: claim["resolved_values"][row["value"]]
                  for row in trace}
    report["explicit_artifact_replay"] = explicit_replay(old_values)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
