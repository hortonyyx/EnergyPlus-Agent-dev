"""Replay finish_bim on temporary copies, leaving both real experiments immutable."""
import asyncio
import json
from pathlib import Path
import shutil
import tempfile

from scripts.tool_scripts.run_bim_agent import digest, dump
from tests.test_bim_agent_tools import _json_result, _server_session

HERE = Path(__file__).resolve().parent


async def main():
    reports = []
    for name in ("2026-09-26_sm25_height_review_claude_run52", "2026-09-26_sm25_height_cold_claude_run53"):
        run = HERE.parent / name
        saved = json.loads((run / "delivery.json").read_text())
        before = digest(run / "delivery.json")
        with tempfile.TemporaryDirectory(prefix="bim-delivery-transport-") as tmp:
            copy = Path(tmp) / "run"
            shutil.copytree(run, copy, ignore=shutil.ignore_patterns("*.gz", "evaluation", "browser_qa"))
            async with _server_session(copy, readonly=False) as session:
                response = await session.call_tool("finish_bim", {"candidate": saved["candidate"]})
                reply = _json_result(response)
                size = len(json.dumps(reply, ensure_ascii=False, indent=2))
                assert size <= 18000
                assert reply["source_model_sha256"] == saved["source_model_sha256"]
                assert reply["height_coverage"]["summary"] == saved["height_coverage"]["summary"]
                full = json.loads((copy / "delivery.json").read_text())
                assert full["current_claim_state"] == saved["current_claim_state"]
                assert full["height_coverage"] == saved["height_coverage"]
            assert digest(run / "delivery.json") == before
            reports.append(dict(run=name, mcp_stdio_return_ok=True, pretty_characters=size,
                source_sha256=reply["source_model_sha256"], full_evidence_preserved=True,
                original_delivery_unchanged=True, live_model_called=False))
    dump(HERE / "delivery_transport_replay.json", reports)
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
