#!/usr/bin/env python3
"""Drive the 07-07 reproduction reader, recording BOTH directions verbatim.

Why this exists: the 07-07 run cannot be audited — it kept no record of what the
orchestrator said to the reader, nor of what the reader read. This script makes
the same configuration reproducible AND auditable, without changing anything the
reader experiences:

  * the reader runs in the 723b0f9 worktree, with prompt-level isolation only,
    exactly as on 07-07 (gt and ten prior runs remain physically reachable);
  * every prompt the orchestrator sends is appended verbatim to interventions.md
    BEFORE it is sent, so an intervention cannot be quietly rewritten afterwards;
  * every turn's full result JSON is kept;
  * Claude Code's own transcript (which records each tool call with its inputs)
    is copied next to the run, so "did it read the answers?" is answerable.

Usage:
    drive_reader.py --prompt-file <f> [--session <id>] [--label pilot_review]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKTREE = Path("/workspaces/ep_707_tree")
MODEL = "claude-haiku-4-5-20251001"
TOOLS = "Read,Write,Edit,Bash,Glob,Grep"
TRANSCRIPT_DIR = Path("/root/.claude/projects/-workspaces-ep-707-tree")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--session")
    ap.add_argument("--label", default="turn")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--timeout", type=int, default=3600)
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    turns_dir = run_dir / "_run" / "turns"
    turns_dir.mkdir(parents=True, exist_ok=True)
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    index = len(list(turns_dir.glob("*.json"))) + 1

    # Record the intervention BEFORE sending it. If the run dies mid-turn, the
    # record still shows what was said — the opposite of the 07-07 situation.
    log = run_dir / "_run" / "interventions.md"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## Turn {index:03d} — {args.label} — {stamp}\n"
                 f"resume_session: {args.session or '(new session)'}\n\n"
                 f"```\n{prompt}\n```\n")

    cmd = ["claude", "-p"]
    if args.session:
        cmd += ["--resume", args.session]
    cmd += [prompt, "--model", MODEL, "--allowedTools", TOOLS, "--output-format", "json"]

    proc = subprocess.run(cmd, cwd=WORKTREE, capture_output=True, text=True, timeout=args.timeout)
    raw = proc.stdout
    (turns_dir / f"{index:03d}_{args.label}.raw").write_text(raw + "\n---STDERR---\n" + proc.stderr,
                                                             encoding="utf-8")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"rc={proc.returncode} — non-JSON output, see {turns_dir}/{index:03d}_{args.label}.raw")
        return 1

    (turns_dir / f"{index:03d}_{args.label}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    sid = result.get("session_id", "")
    transcript = TRANSCRIPT_DIR / f"{sid}.jsonl"
    if transcript.exists():
        shutil.copy2(transcript, run_dir / "_run" / f"transcript_{sid}.jsonl")

    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n**reader reply** (session `{sid}`, turns={result.get('num_turns')}, "
                 f"cost=${result.get('total_cost_usd', 0):.3f}):\n\n"
                 f"```\n{result.get('result', '')}\n```\n")

    print(f"rc={proc.returncode} session={sid} turns={result.get('num_turns')} "
          f"cost=${result.get('total_cost_usd', 0):.3f}")
    print(f"NEXT_SESSION={sid}")
    print("--- reply ---")
    print(result.get("result", "")[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
