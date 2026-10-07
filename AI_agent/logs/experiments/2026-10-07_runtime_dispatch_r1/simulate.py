"""Reproducible RT1 scheduling evidence. Synthetic service only, no HTTP."""

import asyncio
import json
import time
from pathlib import Path

from src.agent_runtime.dispatch import DispatchPolicy, RouteDispatcher


async def six_requests(queued):
    gate = RouteDispatcher("mock-five-slots", DispatchPolicy(5, 5)) if queued else None
    active, peak = 0, 0
    records = []

    async def one(number):
        nonlocal active, peak
        lease = await gate.acquire(timeout=2) if gate else None
        row = {"request": number, "queue_seconds": lease.evidence["queue_seconds"] if lease else 0}
        try:
            if active == 5:
                row["status"] = "429_temporary_rate_limit"
            else:
                active += 1
                peak = max(peak, active)
                try:
                    await asyncio.sleep(0.05)
                    row["status"] = "accepted"
                finally:
                    active -= 1
        finally:
            if lease:
                lease.release()
            records.append(row)

    start = time.perf_counter()
    await asyncio.gather(*(one(i) for i in range(6)))
    return {"service_capacity": 5, "arrivals": 6, "accepted_peak": peak,
            "accepted": sum(row["status"] == "accepted" for row in records),
            "rejected": sum(row["status"] != "accepted" for row in records),
            "elapsed_seconds": time.perf_counter() - start,
            "requests": sorted(records, key=lambda row: row["request"])}


async def adaptation():
    clock = [0.0]
    gate = RouteDispatcher("mock-changing-capacity", DispatchPolicy(5, 8), clock=lambda: clock[0])
    lease = await gate.acquire(timeout=2)
    states = [{"time": 0, "limit": gate.limit, "event": "initial"}]
    states.append({"time": 0, **lease.rejected()})
    lease.release()
    for tick in (30, 61, 122, 183, 244):
        clock[0] = tick
        lease = await gate.acquire(timeout=2)
        change = lease.succeeded()
        states.append({"time": tick, "event": "accepted", "limit": gate.limit, "change": change})
        lease.release()
    return {"clock": "controlled seconds; not elapsed production time", "states": states}


async def main():
    result = {"live_model_requests": 0, "before": await six_requests(False),
              "after": await six_requests(True), "adaptation": await adaptation(),
              "note": "Before records first-wave rejection, not the subsequent legacy backoff retries. Synthetic elapsed times do not predict whole-case speed."}
    assert result["before"]["rejected"] == 1
    assert result["after"]["rejected"] == 0 and result["after"]["accepted"] == 6
    assert result["adaptation"]["states"][1]["limit"] == 4
    assert result["adaptation"]["states"][-1]["limit"] == 8
    target = Path(__file__).with_name("simulation.json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(target)


if __name__ == "__main__":
    asyncio.run(main())
