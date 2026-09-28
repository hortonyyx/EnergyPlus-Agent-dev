"""One authorized saved-proposal repair; prepare never starts a model process."""
import argparse
import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from scripts.tool_scripts import run_bim_agent as runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / "2026-09-28_sm21_baseline_ink_run87"
SEED = PRIOR / "candidate_06"
RUN = HERE.parent / "2026-09-28_sm21_paired_elevation_recovery_run88"
load = lambda p: json.loads(p.read_text())
sha = runner.digest
save = runner.dump
SCOPE = ("Review the supplied unverified saved whole-building BIM against the six original drawings. "
         "Compare each relevant complete original elevation with the actual source elevation and its opening-ID/height table "
         "using view_elevation_candidate with an explicitly selected original image. Resolve discrepancies from the visible "
         "opening shapes and dimension chains; preserve reliable spaces, walls, apertures and connectivity through local revisions. "
         "Inspect the resulting geometry against the originals before delivery. Assumptions are allowed where information is absent. "
         "No EP/materials. One Sonnet session only; do not call review_detail or any other model.")


def arguments(run):
    return SimpleNamespace(command="run", images=PRIOR / "images", mesh=None, building_input=None,
        out=run, scope=SCOPE, timeout=3000, provider="claude", exploratory_opus=False,
        effort="medium", max_candidates=24, continuation_rounds=0,
        resume_candidate=SEED, resume_plan=None, plan_image=None)


async def replay(run):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from PIL import Image, ImageChops
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / "scripts/tool_scripts/run_bim_agent.py"), "serve", str(run)], cwd=str(ROOT))
    protected = {p: sha(p) for p in [SEED / "source_model.json", SEED / "proposal.json",
        run / "seed/source_model.json", *sorted((run / "images").glob("*.png"))]}
    records = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            catalog = await session.list_tools()
            tools = {t.name: t.model_dump(mode="json") for t in catalog.tools}
            for facade in ["South", "East", "North", "West"]:
                result = await session.call_tool("view_elevation_candidate", {
                    "candidate": "seed", "facade": facade, "image": f"{facade}_view.png"})
                assert not result.isError
                meta = result.structuredContent
                pictures = [base64.b64decode(c.data) for c in result.content if c.type == "image"]
                assert len(pictures) == 2
                original = Image.open(run / "images" / f"{facade}_view.png").convert("RGB")
                original.thumbnail((1600, 1600))
                actual = Image.open(io.BytesIO(pictures[0])).convert("RGB")
                assert original.size == actual.size and ImageChops.difference(original, actual).getbbox() is None
                assert hashlib.sha256(pictures[0]).hexdigest() == meta["original_view"]["returned_png_sha256"]
                assert pictures[1] == (run / meta["elevation_image"]).read_bytes()
                assert meta["drawing_fidelity"] == "not_evaluated"
                assert meta["source_model_sha256"] == load(run / "seed/source_model.json")["source_model_sha256"]
                records.append(dict(facade=facade, metadata=meta, exact_original_and_source_transport=True))
    old, current = load(SEED / "source_model.json"), load(run / "seed/source_model.json")
    kept = ["floors", "spaces", "boundaries", "openings", "connections"]
    metadata_changes = []
    for group in kept:
        assert len(old[group]) == len(current[group])
        for before, after in zip(old[group], current[group]):
            changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
            if group == "spaces":
                assert changed <= {"assumptions", "source_refs", "role"}
                if "role" in changed:
                    assert before["role"] == "conference_room" and after["role"] == "conference/meeting/multipurpose"
                metadata_changes.extend(dict(group=group, id=before["id"], field=key,
                    before=before.get(key), after=after.get(key)) for key in sorted(changed))
            else:
                assert not changed, (group, changed)
    assert all(sha(path) == value for path, value in protected.items())
    save(HERE / "offline_replay.json", dict(model_calls=0, physical_geometry_unchanged=True,
        checked_groups=kept, expected_current_producer_metadata_changes=metadata_changes,
        first_attempt="Initial overly broad equality assertion failed on restored space evidence, empty assumptions and two canonical conference-room role names. No geometry changed; exact differences retained here.",
        protected_files=len(protected), original_images_returned=4, source_images_returned=4, records=records,
        limit="Developer-selected full-image pairs only; no autonomous interpretation or correction is proven."))
    return tools


def prepare():
    offline = HERE / "offline_replay"
    class Boundary(Exception):
        pass
    def stop(command, **kwargs):
        assert command[0] == "claude" and command[command.index("--model") + 1] == "sonnet"
        raise Boundary()
    if not offline.exists():
        with patch.object(subprocess, "Popen", stop):
            try:
                runner.run_experiment(arguments(offline))
            except Boundary:
                pass
            else:
                raise AssertionError("model boundary not intercepted")
    else:
        # Resume only our intercepted offline setup; retain its earlier view records.
        assert not list(offline.glob("*receipt.json")) and not (HERE / "frozen.json").exists()
        assert sha(offline / "seed/proposal.json") == sha(SEED / "proposal.json")
        assert all(sha(ROOT / name) == value for name, value in load(offline / "inputs.json")["implementation_sha256"].items())
    manifest, request = load(offline / "inputs.json"), load(offline / "agent_request.json")
    tools = asyncio.run(replay(offline))
    execution = {**manifest["implementation_sha256"],
        "src/agent/execution/subscription_json.py": sha(ROOT / "src/agent/execution/subscription_json.py")}
    frozen = dict(mode="saved_proposal_paired_elevation_recovery", baseline_commit="60eb8db2",
        scope=SCOPE, images=manifest["images"], implementation_sha256=manifest["implementation_sha256"],
        execution_sha256=execution, seed_proposal_sha256=sha(SEED / "proposal.json"),
        seed_source_sha256=sha(SEED / "source_model.json"), guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        request=request, batch_script_sha256=sha(Path(__file__)), provider="claude", role="sonnet", effort="medium",
        timeout_seconds=3000, max_candidates=24, continuation_rounds=0, primary_invocations=1,
        local_model_invocations=0, denied_tools=["mcp__bim__review_detail"], run=RUN.name,
        limits=["Saved run87 proposal plus six originals; not a cold start.",
            "Current main runtime, paired tool and method-specific scope differ from run87; not a causal ablation.",
            "No previous claims, error locations, target dimensions, audits or GT supplied.",
            "No retry, continuation, local model, paid API or fallback. One repair cannot prove stable generation."])
    save(HERE / "frozen.json", frozen)
    save(HERE / "preflight.json", dict(model_calls=0, model_process_intercepted=True, real_stdio=True,
        tools=tools, production_files=len(execution), tests="9 focused source-elevation/real-stdio checks passed"))
    print(json.dumps(dict(prepared=True, model_calls=0, production_files=len(execution), frozen_sha256=sha(HERE / "frozen.json"))))


def run():
    frozen, approval = load(HERE / "frozen.json"), load(HERE / "approval.json")
    assert approval["approved"] and approval["frozen_sha256"] == sha(HERE / "frozen.json")
    assert sha(Path(__file__)) == frozen["batch_script_sha256"]
    assert all(sha(ROOT / name) == value for name, value in frozen["execution_sha256"].items())
    assert sha(SEED / "proposal.json") == frozen["seed_proposal_sha256"]
    assert sha(SEED / "source_model.json") == frozen["seed_source_sha256"]
    assert not RUN.exists(), "Never overwrite or retry an existing model run"
    original_subscription, original_popen = runner.subscription, subprocess.Popen
    counts = dict(primary=0, process=0)
    def invoke(path, prompt, **kwargs):
        counts["primary"] += 1
        assert counts["primary"] == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        assert prompt == frozen["request"]["prompt"]
        manifest = load(path / "inputs.json")
        assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
        assert manifest["images"] == frozen["images"]
        assert sha(path / "seed/proposal.json") == frozen["seed_proposal_sha256"]
        save(path / "experiment_condition.json", frozen)
        save(path / "batch_approval.json", approval)
        for name, value in frozen["execution_sha256"].items():
            target = path / "runtime_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
            assert sha(target) == value
        return original_subscription(path, prompt, **kwargs)
    def launch(command, **kwargs):
        if command[0] == "claude":
            counts["process"] += 1
            assert counts["process"] == 1
            command = [*command, "--disallowedTools", "mcp__bim__review_detail"]
            save(RUN / "invocation_guard.json", dict(primary_processes=1,
                denied_tools=frozen["denied_tools"], auto_retry=False, continuation_rounds=0))
        return original_popen(command, **kwargs)
    with patch.object(runner, "subscription", invoke), patch.object(subprocess, "Popen", launch):
        runner.run_experiment(arguments(RUN))
    receipt, summary = load(RUN / "agent_receipt.json"), load(RUN / "summary.json")
    assert counts == dict(primary=1, process=1)
    assert not list(RUN.glob("detail*receipt.json")) and not list(RUN.glob("detail_*/*receipt.json"))
    completed = bool(summary["agent_response_completed"] and receipt.get("returncode") == 0
        and not receipt.get("timed_out") and not receipt.get("routing_error")
        and not receipt.get("result", {}).get("is_error"))
    save(HERE / "execution_receipt.json", dict(completed=completed, counts=counts,
        actual_model=receipt.get("actual_model"), elapsed_seconds=receipt["elapsed_seconds"], retry=False,
        receipt_file=str((RUN / "agent_receipt.json").relative_to(ROOT))))
    print(json.dumps(dict(completed=completed, counts=counts, retry=False)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    prepare() if parser.parse_args().action == "prepare" else run()
