"""Independent six-output interface follow-up, sharing the original 60 tickets."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from run_role_tests import MODELS, run_case


async def main(args):
    args.out, args.baseline = args.out.resolve(), args.baseline.resolve()
    if not args.out.is_relative_to(ROOT) or not args.baseline.is_relative_to(ROOT):
        raise ValueError("follow-up outputs and quota must stay inside this worktree")
    baseline_index = json.loads((args.baseline / "index.json").read_bytes())
    if len(baseline_index) != 20:
        raise ValueError("all baseline outcomes must be retained before the follow-up")
    args.quota_journal = args.baseline / "role_requests.jsonl"
    if args.run_prefix == "final_":
        if args.followup is None or not args.followup.resolve().is_relative_to(ROOT):
            raise ValueError("final batch requires the preserved follow-up inside this worktree")
        followup_index = json.loads((args.followup / "index.json").read_bytes())
        if len(followup_index) != 6:
            raise ValueError("the complete six-output follow-up must be retained")
    tickets = [json.loads(line) for line in args.quota_journal.read_text().splitlines()]
    initial_attempts = sum(t["event"] == "attempt" for t in tickets)
    args.budget_limits = {"model_calls": 3, "tool_calls": 6, "tokens": 100000, "seconds": 600}
    manifest = json.loads((HERE / "role_cases/manifest.json").read_bytes())
    cases = [c for c in manifest["cases"] if c["test_group"] == "drawing"]
    assert len(cases) == 3
    args.out.mkdir(parents=True, exist_ok=True)
    source_files = [*sorted((ROOT / "src/agent_runtime").glob("*.py")),
        *sorted((ROOT / "src/agent").glob("runtime_*.py")),
        ROOT / "src/agent_runtime/model_profiles.json", HERE / "run_role_tests.py", Path(__file__).resolve()]
    protocol_path = args.out / "protocol.json"
    prior = json.loads(protocol_path.read_bytes()) if protocol_path.exists() else None
    if prior is None and initial_attempts + 18 > 60:
        raise ValueError("insufficient shared quota for this bounded six-output follow-up")
    protocol = {"manifest_sha256": hashlib.sha256((HERE / "role_cases/manifest.json").read_bytes()).hexdigest(),
        "source_files": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        "models": list(MODELS), "temperature": 0.0, "enable_thinking": True, "max_tokens": 16384,
        "case_ids": [c["case_id"] for c in cases], "questions_per_model": 3,
        "run_prefix": args.run_prefix,
        "max_model_calls_per_question": 3, "max_requests_this_batch": 18, "max_batch_requests": 60,
        "budget_limits": args.budget_limits, "shared_quota": str(args.quota_journal.relative_to(ROOT)),
        "baseline_attempts_at_start": 21,
        "retries": 0, "fallback": False,
        "selection": "all three pre-existing drawing questions, both models, one output each",
        "comparison_notice": "Independent interface follow-up: explicit limits/filenames and known scope-error feedback; tool cap 2->6, model cap 2->3, time 360->600. Not a same-condition model ranking."}
    if args.run_prefix == "final_":
        prior_attempts = prior["prior_attempts_at_start"] if prior else initial_attempts
        if prior_attempts != 21 + sum(row["model_requests"] for row in followup_index):
            raise ValueError("final start quota differs from the retained prior batches")
        protocol["prior_attempts_at_start"] = prior_attempts
        protocol["comparison_notice"] = (
            "Final independent six-output check after fixing observer budget state revision. "
            "Same questions, models and limits as the failed follow-up; every earlier outcome retained. "
            "No further answer-based sampling after this fixed matrix.")
    if prior and prior != protocol:
        raise ValueError("resumed follow-up configuration or code changed")
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n")
    results = []
    for index, case in enumerate(cases, 1):
        for model in MODELS:
            row = await run_case(args, case, model, index)
            results.append({k: row[k] for k in ("case_id", "model", "run_id", "test_group", "input_kind",
                "information_sufficiency", "photo_surrogate", "status", "model_requests", "usage")})
            (args.out / "index.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"case": row["case_id"], "model": model, "status": row["status"],
                              "requests": row["model_requests"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--followup", type=Path)
    p.add_argument("--run-prefix", choices=("followup_", "final_"), default="followup_")
    p.add_argument("--credentials-file", type=Path, required=True)
    asyncio.run(main(p.parse_args()))
