"""Recheck historical inputs under the user's strict position decision rule."""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from replay import ROOT, SOURCES, dump, replay


async def main():
    suffix = sys.argv[1] if len(sys.argv) > 1 else "takeover_strict"
    outputs = ROOT / "AI_agent/archive/local_backup/g1" / ("historical_replay_" + suffix)
    results = [await replay(name, source, outputs / name) for name, source in SOURCES.items()]
    report = {
        "mode": "offline replay of immutable historical reader artifacts",
        "product_decision": "Over-30 cm discrepancies require explicit review before delivery",
        "not_a_new_cold_start_or_speed_benchmark": True,
        "model_requests": 0,
        "results": results,
    }
    # Keep the original permissive-policy evidence unchanged and distinguish
    # successful enforcement of the new rule from successful BIM delivery.
    dump(Path(__file__).with_name("takeover_historical_replay.json"), report)
    by_name = {row["case"]: row for row in results}
    pending = by_name["d1l"]["position_summary"]["delivery_blocking"]
    assert pending, "The historical unresolved discrepancies must remain visible"
    assert not by_name["d1l"]["delivered"], "Unresolved positions must block delivery"
    assert by_name["d1l"]["candidate"], "Position review must not block safe assembly"
    assert by_name["d1l"]["assembly_review_status"] != "needs_review"
    assert by_name["n1"]["delivered"], "The reviewed comparison case must still deliver"
    assert all(row["original_inputs_unchanged"] for row in results)


if __name__ == "__main__":
    asyncio.run(main())
