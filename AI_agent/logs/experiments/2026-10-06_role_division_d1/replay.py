"""Create durable offline scripted D1 role-pipeline evidence for sm24/sm25.

This replays accepted artifacts through the real frozen MCP.  It verifies the
runtime integration and audit trail; it is not a fresh model-quality score.
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
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

from role_d1_fixtures import event_counts, make_fixture  # noqa: E402
from src.agent.runtime_roles.entry import execute  # noqa: E402


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(case_name: str, output: Path, result: dict) -> dict:
    selection_path = output / "bim/delivery_selection.json"
    selection = json.loads(selection_path.read_bytes())
    source_path = output / "bim" / selection["candidate"] / "source_model.json"
    source = json.loads(source_path.read_bytes())
    counts = event_counts(output)
    event_count = len((output / "events.jsonl").read_text(encoding="utf-8").splitlines())
    return {
        "case": case_name,
        "mode": "offline_scripted_fixture_not_model_quality",
        "agent_version": result["agent_version"],
        "status": result["status"],
        "delivery_status": result["finalization"]["status"],
        "output": output.relative_to(ROOT).as_posix(),
        "delivery_html": (output / "bim/delivery.html").relative_to(ROOT).as_posix(),
        "events": (output / "events.jsonl").relative_to(ROOT).as_posix(),
        "receipt": (output / "receipt.json").relative_to(ROOT).as_posix(),
        "delivery_selection_sha256": file_sha256(selection_path),
        "source_model_sha256": source["source_model_sha256"],
        "floors": sorted({space["floor_id"] for space in source["spaces"]}),
        "reader_artifact_count": len(list((output / "tasks").glob("*/reader_record.json"))),
        "elevation_match_count": len(list((output / "role_matches").glob("*.json"))),
        "height_transaction_count": len(list((output / "bim/claims").glob("transaction_*.json"))),
        "height_application_count": len(list((output / "bim/claims").glob("application_*.json"))),
        "event_count": event_count,
        "model_requests": counts.model_requests,
        "tool_invocations": counts.tools,
        "role_accounting": result["role_accounting"],
    }


def replay(case_name: str, output_root: Path) -> dict:
    fixture = make_fixture(case_name, output_root)
    fixture.output = output_root / case_name
    fixture.args.out = fixture.output
    if fixture.output.exists():
        raise FileExistsError(
            f"durable replay already exists: {fixture.output}; move it aside explicitly"
        )
    result = asyncio.run(execute(fixture.args, adapter_factory=fixture.adapter_factory))
    if result["status"] != "completed":
        raise RuntimeError(f"{case_name} replay stopped: {result['status']}")
    return summarize(case_name, fixture.output, result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", choices=("sm24", "sm25"))
    parser.add_argument("--summarize-existing", action="store_true")
    args = parser.parse_args()
    cases = args.cases or ["sm24", "sm25"]
    output_root = HERE / "offline_replay"
    output_root.mkdir(exist_ok=True)
    rows = []
    for case_name in cases:
        output = output_root / case_name
        if args.summarize_existing:
            rows.append(summarize(case_name, output, json.loads((output / "receipt.json").read_bytes())))
        else:
            rows.append(replay(case_name, output_root))
    summary = {
        "schema_version": "d1_offline_scripted_replay_v1",
        "offline_only": True,
        "external_model_or_api_calls": 0,
        "scope": "real frozen MCP orchestration and recovery evidence; not fresh model reading quality",
        "cases": rows,
    }
    path = HERE / "offline_replay.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
