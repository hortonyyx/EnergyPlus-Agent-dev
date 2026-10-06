"""Offline D1g C reproduction from archived run3; never constructs a model adapter.

Run from the worktree root after activate_windows.ps1. All working copies are
under archive/local_backup/d1g. The small JSON result is the retained evidence.
The archived candidate_08 already has all fourteen matched heights: the exact
replay measures redundant saves. A separately labelled control restores only
those Z pairs to the delivered plan assumptions to expose lost parallel writes.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import time
import types
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.runtime_roles.lineage import latest_candidate, opening_plan
from src.agent.runtime_roles.session import RoleSession, envelope
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).with_name("height_replay.json")
SCRATCH = ROOT / "AI_agent/archive/local_backup/d1g"
BASELINE = "b6417ee38ace983895d435750eb5812cd71b4758"
ARCHIVE_REF = "94bab4fd:role_debug_sm24_run3.tar.xz"
ARCHIVE_SHA256 = "c164ce429ce82420f95deeb86ebaaea388b9c43142aa63f11bb903bfc4bab733"
SIDES = ("N", "S", "E", "W")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def evidence():
    raw = subprocess.check_output(["git", "show", ARCHIVE_REF], cwd=ROOT)
    assert digest(raw) == ARCHIVE_SHA256
    folder = SCRATCH / "replay_archive"
    folder.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as archive:
        archive.extractall(folder, filter="data")
    return folder / "sm24_run3"


def baseline_class():
    source = subprocess.check_output(["git", "show", BASELINE + ":src/agent/runtime_roles/session.py"], cwd=ROOT)
    module = types.ModuleType("src.agent.runtime_roles.d1g_baseline_session")
    module.__file__ = str(ROOT / "src/agent/runtime_roles/session.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module.RoleSession, digest(source)


class LocalClaims:
    def __init__(self, run):
        self.run_directory, self.toolkit, self.calls = run, Toolkit(run), []

    async def call_tool(self, name, arguments):
        assert name == "claim_transaction", name
        self.calls.append(arguments["candidate"])
        await asyncio.sleep(0)  # Allow every unguarded writer to pick its base first.
        return envelope(self.toolkit.claim_transaction(arguments["candidate"], arguments["entries_json"]))


def forbidden_adapter(*_):
    raise AssertionError("D1g permits zero model service requests")


def copy_start(archive, folder, *, control):
    run = folder / "bim"
    run.mkdir(parents=True)  # New run per replay; never overwrite old evidence.
    shutil.copy2(archive / "bim/inputs.json", run / "inputs.json")
    for name in ("images", "claims", "plan_drafts", "plan_revisions", "overlay_calibrations"):
        shutil.copytree(archive / "bim" / name, run / name)
    for number in range(1, 9):
        name = f"candidate_{number:02d}"
        shutil.copytree(archive / "bim" / name, run / name)
    inputs = json.loads((run / "inputs.json").read_bytes())
    assert inputs["max_candidates"] == 24
    if control:
        delivered_plan = next(json.loads(p.read_bytes())["plan"]
            for p in (archive / "tasks").glob("*/reader_artifact.json")
            if json.loads((p.parent / "reader_task.json").read_bytes())["task_id"] == "plan_F1_r2")
        original_z = {row["id"]: row["z"] for row in delivered_plan["openings"]}
        proposal = json.loads((run / "candidate_08/proposal.json").read_bytes())
        for row in proposal["geometry"]["windows"] + proposal["geometry"]["openings"]:
            if row["id"] in {"D1", "D2", "D3"} or row["kind"] == "window":
                row["z"] = original_z[row["id"]]
        before = json.loads((run / "candidate_08/source_model.json").read_bytes())
        # Export separately, then replace only this disposable control's copy.
        control_export = folder / "control_export"
        result = export_source_proposal(proposal, control_export)
        assert result["source_geometry_ready"]
        shutil.copytree(control_export, run / "candidate_08", dirs_exist_ok=True)
        after = json.loads((run / "candidate_08/source_model.json").read_bytes())
        assert opening_plan(before) == opening_plan(after)
    return run


def coverage(session, candidate):
    from src.agent.runtime_roles.elevation import match_elevation
    source = session._source(candidate)
    z = {row["id"]: sorted({p[2] for p in row["vertices"]}) for row in source["openings"]}
    result = {}
    for side in SIDES:
        artifact = session.registry.read("elev_" + side)
        match = match_elevation(source, artifact, candidate=candidate)
        assert not any(match[key] for key in ("source_only", "elevation_only", "conflicts"))
        observed = {row["id"]: [row["sill_m"], row["head_m"]] for row in artifact["openings"]}
        rows = [{"source_id": row["source_opening_id"], "actual_z": z[row["source_opening_id"]],
                 "expected_z": observed[row["artifact_opening_id"]]} for row in match["matches"]]
        result[side] = {"openings": rows, "all_heights_present": all(r["actual_z"] == r["expected_z"] for r in rows)}
    return result


async def replay(archive, name, cls, *, control, batches, combined=False):
    folder = SCRATCH / "height_replays" / (name + "-" + str(time.time_ns()))
    run = copy_start(archive, folder, control=control)
    limits = RunLimits(model_calls=1, tool_calls=64, tokens=None, seconds=3600)
    with EventStore(folder / "journal", run_id=name, task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        session = cls(store=store, frozen=LocalClaims(run), routes={},
                      adapter_factory=forbidden_adapter, limits=limits, root=ROOT)
        for path in (archive / "tasks").glob("*/reader_task.json"):
            task = json.loads(path.read_bytes())
            if task["role_id"] != "elevation_reader":
                continue
            task = session._task({k: task[k] for k in ("task_id", "role_id", "image", "target", "instructions")})
            session.registry.save(task, status="completed", artifact=json.loads((path.parent / "reader_artifact.json").read_bytes()))
        initial = coverage(session, "candidate_08")
        initial_bytes = (run / "candidate_08/source_model.json").read_bytes()
        trace = []
        for sides in batches:
            base = latest_candidate(session, "candidate_08")
            ids = [session.match("elev_" + side, base)["match_id"] for side in sides]
            before_count = len(list(run.glob("candidate_*")))
            results = ([await session.apply_heights(ids)] if combined else
                       await asyncio.gather(*(session.apply_heights(identity) for identity in ids)))
            assert all(r["structuredContent"]["status"] == "completed" and not r.get("isError") for r in results), results
            final = latest_candidate(session, base)
            trace.append({"facades": list(sides), "matched_candidate": base, "final_candidate": final,
                "new_candidates": len(list(run.glob("candidate_*"))) - before_count,
                "complete_facades": [s for s, row in coverage(session, final).items() if row["all_heights_present"]]})
        final = latest_candidate(session, "candidate_08")
        result = {"name": name, "control_reset_to_plan_assumptions": control,
            "initial_candidate_count": 8, "new_candidate_count": len(list(run.glob("candidate_*"))) - 8,
            "total_candidate_count": len(list(run.glob("candidate_*"))), "final_candidate": final,
            "initial_coverage": initial, "final_coverage": coverage(session, final), "batches": trace,
            "write_bases": session.frozen.calls,
            "initial_source_unchanged": (run / "candidate_08/source_model.json").read_bytes() == initial_bytes,
            "model_service_requests": 0}
        assert result["total_candidate_count"] <= 24 and result["initial_source_unchanged"]
        return result


async def main():
    archive = evidence()
    old, old_sha = baseline_class()
    rows = []
    actual = (SIDES, SIDES[:3], SIDES[:2], SIDES[:1])
    prescribed = (SIDES, SIDES)
    for control, batches, suffix in ((False, actual, "archive_actual_4_3_2_1"),
                                      (False, prescribed, "archive_two_parallel_batches"),
                                      (True, prescribed, "control_two_parallel_batches"),
                                      (True, actual, "control_actual_4_3_2_1")):
        for label, cls in (("before", old), ("after", RoleSession)):
            row = await replay(archive, label + "_" + suffix, cls, control=control, batches=batches)
            rows.append(row)
            print(row["name"], "+", row["new_candidate_count"], "total", row["total_candidate_count"],
                  "facades", row["batches"][-1]["complete_facades"], flush=True)
    rows.append(await replay(archive, "after_control_one_combined_batch", RoleSession,
                             control=True, batches=(SIDES,), combined=True))
    save(OUTPUT, {"baseline_commit": BASELINE, "baseline_session_sha256": old_sha,
        "archive_git_object": ARCHIVE_REF, "archive_sha256": ARCHIVE_SHA256,
        "scope": "Stored readers and source replay, not a new drawing interpretation or live model case. "
                 "Baseline session uses unchanged shared geometry and the same elevation matcher. "
                 "Control changes only fourteen external Z pairs back to the delivered plan assumptions.",
        "model_service_requests": 0, "replays": rows})
    assert [r["new_candidate_count"] for r in rows] == [10, 0, 8, 0, 8, 4, 10, 4, 1]
    assert rows[4]["batches"][-1]["complete_facades"] == ["W"]
    assert all(row["all_heights_present"] for row in rows[-1]["final_coverage"].values())


if __name__ == "__main__":
    asyncio.run(main())
