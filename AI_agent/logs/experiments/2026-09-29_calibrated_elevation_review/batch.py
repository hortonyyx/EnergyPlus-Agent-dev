"""One proposed saved-proposal repair; prepare never starts a model process; run requires recorded approval."""
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
PRIOR = HERE.parent / "2026-09-28_sm21_paired_elevation_recovery_run88"
SEED = PRIOR / "candidate_01"
RUN = HERE.parent / "2026-09-29_sm21_calibrated_elevation_recovery_run89"
load = lambda p: json.loads(p.read_text())
sha = runner.digest
save = runner.dump
SCOPE = ("Review the supplied unverified saved whole-building BIM against the six original drawings. "
         "Compare the relevant original elevations with actual source openings. For an axis-aligned drawing, "
         "view_elevation_candidate can overlay the source in the original frame using horizontal_anchors, "
         "z_anchors and basis. Choose those references from observed original dimensions and absolute floor datums; "
         "do not fit the calibration to the generated openings. Keep observed references fixed after revisions. "
         "Resolve supported discrepancies from each opening outline and its dimension chain; preserve reliable "
         "spaces, walls, apertures and connectivity through local revisions. Inspect the resulting geometry against "
         "the originals before delivery. Assumptions are allowed where information is absent. No EP/materials. "
         "One Sonnet 5 session only; do not call review_detail or any other model.")


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
    # Development observations of the outer width and whole-building height.
    # These values and the following checks are not included in the model's task/input.
    frames = {
        "East": dict(horizontal_anchors=[[286, 0], [746, 8]], z_anchors=[[554, 0], [174, 6.6]],
            basis="Developer offline observation: outer wall endpoints of the 8000 mm width, base and roof endpoints of the 6600 mm total height. World y increases right; absolute base z=0."),
        "South": dict(horizontal_anchors=[[313, 0], [1177, 15]], z_anchors=[[569, 0], [189, 6.6]],
            basis="Developer offline observation: outer wall endpoints of the 15000 mm width, base and roof endpoints of the 6600 mm total height. World x increases right; absolute base z=0."),
    }
    records = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name: t.model_dump(mode="json") for t in (await session.list_tools()).tools}
            for facade, frame in frames.items():
                result = await session.call_tool("view_elevation_candidate", {
                    "candidate": "seed", "facade": facade, "image": f"{facade}_view.png", **frame})
                assert not result.isError
                meta = result.structuredContent
                pictures = [base64.b64decode(c.data) for c in result.content if c.type == "image"]
                assert len(pictures) == 2
                original = Image.open(run / "images" / f"{facade}_view.png").convert("RGB")
                original.thumbnail((1600, 1600))
                actual = Image.open(io.BytesIO(pictures[0])).convert("RGB")
                assert original.size == actual.size and ImageChops.difference(original, actual).getbbox() is None
                assert hashlib.sha256(pictures[0]).hexdigest() == meta["original_view"]["returned_png_sha256"]
                saved = Image.open(run / meta["elevation_image"]).convert("RGB")
                saved.thumbnail((1600, 1600))
                actual_overlay = Image.open(io.BytesIO(pictures[1])).convert("RGB")
                assert saved.size == actual_overlay.size and ImageChops.difference(saved, actual_overlay).getbbox() is None
                assert meta["mode"] == "source_elevation_overlay" and meta["drawing_fidelity"] == "not_evaluated"
                assert meta["source_model_sha256"] == load(run / "seed/source_model.json")["source_model_sha256"]
                openings = {row["id"]: row for row in meta["projected_openings"]}
                checks = []
                # Independently read outer opening heads on the originals, for offline evaluation only.
                observed_heads = {"F1:W7": 393, "F2:W7": 220} if facade == "East" else {"F1:W4": 448}
                for opening_id, observed_pixel in observed_heads.items():
                    row = openings[opening_id]
                    actual_pixel = min(point[1] for point in row["pixel_vertices"])
                    checks.append(dict(opening_id=opening_id, observed_head_pixel=observed_pixel,
                                       projected_head_pixel=actual_pixel, difference_pixels=actual_pixel-observed_pixel))
                if facade == "East":
                    assert 10 < checks[0]["difference_pixels"] < 13
                    assert abs(checks[1]["difference_pixels"]) < 2
                else:
                    assert abs(checks[0]["difference_pixels"]) < 2
                records.append(dict(facade=facade, metadata=meta, head_checks=checks,
                                    exact_original_and_overlay_transport=True))
    old, current = load(SEED / "source_model.json"), load(run / "seed/source_model.json")
    provenance = dict(before=old["generation"]["provenance"], after=current["generation"]["provenance"])
    old["generation"].pop("provenance")
    current["generation"].pop("provenance")
    old.pop("source_model_sha256")
    current.pop("source_model_sha256")
    assert old == current
    assert all(sha(path) == value for path, value in protected.items())
    save(HERE / "offline_replay.json", dict(model_calls=0,
        source_fields_except_provenance_and_digest_unchanged=True, expected_provenance_changes=provenance,
        first_attempt="Overly broad whole-JSON equality failed on recovery provenance and its digest; all remaining source fields are exactly unchanged. First two review records retained. No model process started.",
        protected_files=len(protected), developer_supplied_calibration=True, source_images_returned=2,
        original_images_returned=2, records=records,
        limit="Developer-selected original references; shows a visible residual, not autonomous adoption or quality recovery. No GT or corrected proposal is supplied to the model."))
    return tools


def prepare():
    offline = HERE / "offline_replay"
    class Boundary(Exception):
        pass
    def stop(command, **kwargs):
        assert command[0] == "claude" and command[command.index("--model") + 1] == "claude-sonnet-5"
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
    frozen = dict(mode="saved_proposal_calibrated_elevation_recovery", baseline_commit="cfbf9451",
        scope=SCOPE, images=manifest["images"], implementation_sha256=manifest["implementation_sha256"],
        execution_sha256=execution, seed_proposal_sha256=sha(SEED / "proposal.json"),
        seed_source_sha256=sha(SEED / "source_model.json"), guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        request=request, cli_version=subprocess.check_output(["claude", "--version"], text=True).strip(), requested_model="claude-sonnet-5", batch_script_sha256=sha(Path(__file__)), provider="claude", role="sonnet", effort="medium",
        timeout_seconds=3000, max_candidates=24, continuation_rounds=0, primary_invocations=1,
        local_model_invocations=0, denied_tools=["mcp__bim__review_detail"], run=RUN.name,
        limits=["Saved run88 proposal plus six originals; not a cold start.",
            "Calibrated tool, CLI version and method-specific scope differ from run88; not a causal ablation.",
            "No previous claims, error locations, target dimensions, audits or GT supplied.",
            "No retry, continuation, local model, paid API or fallback. One repair cannot prove stable generation."])
    save(HERE / "frozen.json", frozen)
    save(HERE / "preflight.json", dict(model_calls=0, model_process_intercepted=True, real_stdio=True,
        tools=tools, production_files=len(execution), tests="31 focused elevation, subscription and routing checks; final result recorded in validation.json"))
    print(json.dumps(dict(prepared=True, model_calls=0, production_files=len(execution), frozen_sha256=sha(HERE / "frozen.json"))))


def run():
    frozen, approval = load(HERE / "frozen.json"), load(HERE / "approval.json")
    assert approval["approved"] and approval["frozen_sha256"] == sha(HERE / "frozen.json")
    assert sha(Path(__file__)) == frozen["batch_script_sha256"]
    assert all(sha(ROOT / name) == value for name, value in frozen["execution_sha256"].items())
    assert sha(SEED / "proposal.json") == frozen["seed_proposal_sha256"]
    assert sha(SEED / "source_model.json") == frozen["seed_source_sha256"]
    assert subprocess.check_output(["claude", "--version"], text=True).strip() == frozen["cli_version"]
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
            assert command[command.index("--model") + 1] == "claude-sonnet-5"
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
        and not receipt.get("result", {}).get("is_error")
        and receipt.get("actual_model") == "claude-sonnet-5"
        and set(receipt.get("result", {}).get("modelUsage", {})) == {"claude-sonnet-5"})
    save(HERE / "execution_receipt.json", dict(completed=completed, counts=counts,
        actual_model=receipt.get("actual_model"), elapsed_seconds=receipt["elapsed_seconds"], retry=False,
        receipt_file=str((RUN / "agent_receipt.json").relative_to(ROOT))))
    print(json.dumps(dict(completed=completed, counts=counts, retry=False)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    prepare() if parser.parse_args().action == "prepare" else run()
