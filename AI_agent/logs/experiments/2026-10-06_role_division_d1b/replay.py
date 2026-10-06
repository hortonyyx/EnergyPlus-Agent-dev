"""Run the D1b offline scripted role pipeline for sm21/sm24/sm25.

The fixtures replay accepted 10-01 readings through the real frozen MCP. They
exercise submission, assembly, height application and recovery without calling
an external model. Raw runs stay under archive/local_backup; this directory
keeps only the compact result summary.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DEFAULT_OUTPUT_ROOT = ROOT / "AI_agent/archive/local_backup/d1b/offline"
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

from role_d1_fixtures import assembly_review, event_counts, make_fixture  # noqa: E402
from src.agent.runtime_roles.entry import execute  # noqa: E402


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def summarize(case_name: str, output: Path, result: dict) -> dict:
    counts = event_counts(output)
    selection_path = output / "bim/delivery_selection.json"
    selection = json.loads(selection_path.read_bytes()) if selection_path.is_file() else None
    source_path = (
        output / "bim" / selection["candidate"] / "source_model.json"
        if selection is not None else None
    )
    source = json.loads(source_path.read_bytes()) if source_path and source_path.is_file() else None
    candidates = sorted(
        path.name
        for path in (output / "bim").glob("candidate_[0-9][0-9]")
        if (path / "source_model.json").is_file()
    )
    assembly = assembly_review(output) or {}
    return {
        "case": case_name,
        "mode": "offline_scripted_fixture_not_model_quality",
        "agent_version": result.get("agent_version"),
        "status": result.get("status"),
        "delivery_status": (result.get("finalization") or {}).get("status"),
        "output": relative(output),
        "receipt": relative(output / "receipt.json"),
        "delivery_html": relative(output / "bim/delivery.html") if (output / "bim/delivery.html").is_file() else None,
        "events": relative(output / "events.jsonl"),
        "delivery_selection_sha256": file_sha256(selection_path) if selection_path.is_file() else None,
        "source_model_sha256": source.get("source_model_sha256") if source else None,
        "floors": sorted({space["floor_id"] for space in source["spaces"]}) if source else [],
        "reader_artifact_count": len(list((output / "tasks").glob("*/reader_record.json"))),
        "elevation_match_count": len(list((output / "role_matches").glob("*.json"))),
        "saved_candidate_count": len(candidates),
        "saved_candidates": candidates,
        "height_transaction_count": len(list((output / "bim/claims").glob("transaction_*.json"))),
        "height_application_count": len(list((output / "bim/claims").glob("application_*.json"))),
        "event_count": len((output / "events.jsonl").read_text(encoding="utf-8").splitlines()),
        "model_requests": counts.model_requests,
        "tool_invocations": counts.tools,
        "assembly_review_status": assembly.get("status"),
        "assembly_change_count": len(assembly.get("changes", [])),
        "assembly_changes": assembly.get("changes", []),
        "role_accounting": result.get("role_accounting"),
    }


def replay(case_name: str, output_root: Path) -> dict:
    fixture = make_fixture(case_name, output_root)
    fixture.output = output_root / case_name
    fixture.args.out = fixture.output
    if fixture.output.exists():
        raise FileExistsError(
            f"offline replay already exists: {fixture.output}; move it aside explicitly"
        )
    result = asyncio.run(execute(fixture.args, adapter_factory=fixture.adapter_factory))
    return summarize(case_name, fixture.output, result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", choices=("sm21", "sm24", "sm25"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--summarize-existing", action="store_true")
    args = parser.parse_args()
    cases = args.cases or ["sm21", "sm24", "sm25"]
    output_root = args.output_root.resolve()
    if not output_root.is_relative_to(ROOT.resolve()):
        raise ValueError("output root must stay inside this worktree")
    output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_name in cases:
        output = output_root / case_name
        if args.summarize_existing:
            rows.append(
                summarize(case_name, output, json.loads((output / "receipt.json").read_bytes()))
            )
        else:
            rows.append(replay(case_name, output_root))
    summary = {
        "schema_version": "d1b_offline_scripted_replay_v1",
        "offline_only": True,
        "external_model_or_api_calls": 0,
        "candidate_limit": 24,
        "scope": (
            "real frozen MCP submission, orchestration, assembly and recovery evidence; "
            "not fresh model reading quality"
        ),
        "cases": rows,
    }
    path = HERE / "offline_replay.json"
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(path)
    failed = [row for row in rows if row["status"] != "completed"]
    changed = [row for row in rows if row["assembly_change_count"]]
    if failed or changed:
        raise SystemExit(
            "offline replay needs review: "
            + json.dumps({"failed": failed, "assembly_changed": changed}, ensure_ascii=False)
        )


if __name__ == "__main__":
    main()
