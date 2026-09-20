"""Bounded historical reading experiment; no pipeline/provider fallback.

Prepare freezes the pre-prescan 07-07 tools. Each invoke is explicitly a pilot,
rework, or batch turn of the same Claude subscription session. Controller review
and evaluation stay outside the reader workspace. This retains historical
prompt-level Bash isolation; it is not an OS security sandbox.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REV = "723b0f9"
STAGE = Path("/tmp/ep_reading_reproduction_20260916_sm24")


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def prepare():
    if STAGE.exists():
        raise SystemExit(f"Refusing existing workspace: {STAGE}")
    STAGE.mkdir()
    names = subprocess.check_output([
        "git", "ls-tree", "-r", "--name-only", REV,
        "skills/intake_pipeline/0_reading", "src/agent/reading",
        "scripts/tool_scripts/cv_probe.py",
        "case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json",
    ], cwd=REPO, text=True).splitlines()
    records = []
    for name in names:
        if Path(name).name == "judge_rubric.md":
            continue
        data = subprocess.check_output(["git", "show", f"{REV}:{name}"], cwd=REPO)
        target = STAGE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        records.append({"path": name, "source": f"git:{REV}:{name}",
                        "sha256": hashlib.sha256(data).hexdigest()})
    for name in ("src/__init__.py", "src/agent/__init__.py"):
        (STAGE / name).write_text("")
    case = REPO / "case_tests/e2e_tests/sm24_anchor/case_data"
    shutil.copytree(case, STAGE / "case_data")
    for path in sorted((STAGE / "case_data").iterdir()):
        records.append({"path": str(path.relative_to(STAGE)),
                        "source": str((case / path.name).relative_to(REPO)),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (STAGE / "0_reading").mkdir()
    (STAGE / "requests").mkdir()
    settings = {"disableAllHooks": True, "permissions": {
        "defaultMode": "dontAsk",
        "allow": [f"Read(/{STAGE}/**)", f"Write(/{STAGE}/0_reading/**)",
                  f"Edit(/{STAGE}/0_reading/**)", f"Write(/{STAGE}/requests/**)",
                  f"Edit(/{STAGE}/requests/**)", "Bash"],
        "deny": [f"Read(/{REPO}/**)", "Read(//root/**)", "Read(//home/**)",
                 "WebFetch", "WebSearch", "Agent", "Task", "mcp__*"]}}
    dump(STAGE / "settings.json", settings)
    dump(HERE / "input_manifest.json", {"revision": REV, "workspace": str(STAGE),
        "case": "sm24_anchor", "files": records,
        "differences": [
            "Historical sm24 recorded a 723b0f9-to-891356d version window; exact active bytes are unknown. This run explicitly freezes 723b0f9 before prescan.",
            "Claude subscription CLI replaces historical Agent transport; actual model and CLI version recorded per invocation.",
            "Developer Astra performs external pilot review instead of historical Fable. All feedback archived; no GT feedback.",
            "Original unrelated smalloffice_20 format example retained; original case images and declaration unmodified.",
            "No correction, DeepSeek, EnergyPlus, or current BIM tools available in this reader workspace.",
            "Pilot prompt front-loads documented historical successful/rework disciplines; not a verbatim recovery of the unavailable original dispatch or first failed turn.",
            "Filesystem copies and restricted native tools plus prompt-level Bash isolation; not an OS sandbox.",
        ]})
    prompt = """You are reproducing the historical reading method on sm24_anchor.
Read and follow skills/intake_pipeline/0_reading/session_kickoff.md and its required
rule documents and worked example. The actual inputs are the five original PNGs
and unmodified building declaration in case_data/. Its path strings identify the
same basenames here; do not follow paths outside this workspace.

For this run cv_toolbox.md is REQUIRED, not optional: measure before drawing.
Use the provided historical scripts/tool_scripts/cv_probe.py tools. Calibrate from
dimension ticks, measure walls/windows, crop to classify candidates and retain
accepted/rejected decisions with reasons. Pixel measurement of unlabeled components
is allowed with honest provenance and no invented dimension references.

Complete ONE pilot, case_data/1f_view.png, write 0_reading/1f_view.json plus its
CV evidence and self-check, then STOP for external review. Do not batch other
images until explicitly approved. Follow the historical JSON schema rather than
inventing a room/BIM output. Keep the exact image pixel frame; no resizing originals.

You may use Read, Write, Edit and Bash/Python within THIS workspace only. Do not
read repository/history/results/GT, other workspaces, credentials, or home files.
No network commands, subprocess model calls, or other agents. Do not modify supplied
src/, scripts/, skills/, case_data/ or the format example. Put any helper scripts in
requests/ and generated artifacts in 0_reading/. All calculations may use Python.
The external review is part of this experiment; report your actual unexamined items.
"""
    (HERE / "pilot_prompt.md").write_text(prompt)
    shutil.copytree(STAGE, HERE / "frozen_input")
    print(json.dumps({"workspace": str(STAGE), "files": len(records)}))


def invoke(prompt_path, label, resume, timeout):
    invocation_dir = HERE / "invocations" / label
    invocation_dir.mkdir(parents=True, exist_ok=False)
    prompt = Path(prompt_path).read_text()
    (invocation_dir / "prompt.md").write_text(prompt)
    env = {key: value for key, value in os.environ.items()
           if key in {"PATH", "HOME", "LANG", "LC_ALL", "CLAUDE_CODE_OAUTH_TOKEN"}}
    env["PYTHONPATH"] = str(STAGE)
    command = ["claude", "-p", "--model", "claude-haiku-4-5-20251001",
        "--tools", "Read,Write,Edit,Bash,Glob,Grep", "--permission-mode", "dontAsk",
        "--strict-mcp-config", "--setting-sources", "",
        "--settings", str(STAGE / "settings.json"),
        "--output-format", "stream-json", "--verbose"]
    if resume:
        command += ["--resume", (HERE / "session_id.txt").read_text().strip()]
    version = subprocess.check_output(["claude", "--version"], env=env, text=True).strip()
    started = time.monotonic()
    timed_out = False
    with (invocation_dir / "events.jsonl").open("w") as output, (invocation_dir / "stderr.txt").open("w") as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output,
            stderr=errors, cwd=STAGE, env=env, text=True, start_new_session=True)
        try:
            process.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    events = []
    for line in (invocation_dir / "events.jsonl").read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    session = next((e.get("session_id") for e in events if e.get("session_id")), None)
    if session:
        (HERE / "session_id.txt").write_text(session)
    record = {"model_requested": "claude-haiku-4-5-20251001", "cli_version": version,
        "channel": "subscription; no API credentials or fallback", "resume": resume,
        "elapsed_seconds": round(time.monotonic() - started, 3), "timeout_seconds": timeout,
        "timed_out": timed_out, "returncode": process.returncode, "result": result,
        "actual_models": sorted({e.get("message", {}).get("model") for e in events
                                 if e.get("message", {}).get("model")})}
    dump(invocation_dir / "receipt.json", record)
    shutil.copytree(STAGE / "0_reading", invocation_dir / "0_reading")
    shutil.copytree(STAGE / "requests", invocation_dir / "requests")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "invoke"])
    parser.add_argument("--prompt")
    parser.add_argument("--label")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    else:
        invoke(args.prompt, args.label, args.resume, args.timeout)
