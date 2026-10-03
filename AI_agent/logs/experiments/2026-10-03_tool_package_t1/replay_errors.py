"""Replay all 50 failed calls from the prescribed 12 histories, without models.

Original immutable candidates/profiles/views/claims are copied into a temporary
run. Only decisions already returned before the failed call are admitted. The
failed request is unchanged. Outputs are diagnostics, never new cold-start BIM.
"""
import asyncio
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult
from scripts.tool_scripts.run_bim_agent import serve

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RECORDS = HERE.parent / "2026-10-01_behaviour_records/records"


def selected_records():
    for path in sorted(RECORDS.glob("*/record.json.gz")):
        if any(tag in path.parent.name for tag in (
                "run53", "run54", "run55", "run56", "run57", "run58",
                "run98", "run99", "run100", "glm")):
            yield path


def copy_run(original, target):
    target.mkdir(exist_ok=True)
    for path in original.rglob("*.json"):
        relative = path.relative_to(original)
        if relative.parts[0] in {"runtime_snapshot", "evaluation", "bridge"}:
            continue
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    (target / "images").mkdir(exist_ok=True)
    for path in (original / "images").iterdir():
        (target / "images" / path.name).symlink_to(path.resolve())


def unpack(result):
    if isinstance(result, CallToolResult):
        return bool(result.isError), result.content, result.structuredContent
    if isinstance(result, tuple):
        return False, result[0], result[1]
    if isinstance(result, dict):
        return False, [], result
    return False, result, None


async def replay():
    reports = []
    temp_root = ROOT / ".tmp_t1"
    temp_root.mkdir(exist_ok=True)
    for record_path in selected_records():
        record = json.loads(gzip.decompress(record_path.read_bytes()))
        original = HERE.parent / record_path.parent.name
        steps = [step for inv in record["invocations"] for step in inv["steps"]]
        with tempfile.TemporaryDirectory(dir=temp_root, prefix="errors-") as directory:
            target = Path(directory)
            copy_run(original, target)
            for prefix in ("decision", "confirmation", "application"):
                for path in (target / "claims").glob(prefix + "_*.json"):
                    path.unlink()
            servers = []
            with patch.object(FastMCP, "run", lambda server: servers.append(server)):
                serve(target)
            server = servers[0]
            failures = []
            for step in steps:
                if not step.get("is_error"):
                    if step["tool"] == "decide_claim":
                        a = step["arguments"]
                        server.toolkit.claims().decide(a["claim_id"], a["disposition"], a["reason"])
                    continue
                result = await server.call_tool(step["tool"], step["arguments"])
                failed, blocks, structured = unpack(result)
                texts = [block.text for block in blocks if getattr(block, "type", None) == "text"]
                failures.append(dict(index=step["index"], tool=step["tool"],
                    arguments=step["arguments"], old_error=step["result_text"],
                    new_is_error=failed, new_text=texts, new_structured=structured,
                    disposition="actionable_rejection" if failed else "accepted"))
            reports.append(dict(run=original.name,
                record_sha256=hashlib.sha256(record_path.read_bytes()).hexdigest(),
                historical_tool_calls=len(steps), error_count=len(failures), replay=failures))
    summary = dict(model_calls=0, runs=len(reports),
        errors=sum(r["error_count"] for r in reports),
        accepted=sum(not e["new_is_error"] for r in reports for e in r["replay"]),
        rejected=sum(e["new_is_error"] for r in reports for e in r["replay"]))
    (HERE / "error_replay.json").write_text(json.dumps(dict(summary=summary, runs=reports), ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    asyncio.run(replay())
