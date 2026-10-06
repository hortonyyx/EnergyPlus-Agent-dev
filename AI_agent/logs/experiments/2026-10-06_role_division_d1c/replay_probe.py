"""Replay the 17 saved tool arguments against the real local frozen service, offline."""

from __future__ import annotations

import asyncio
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import ep_no_billed_gate  # noqa: E402,F401 -- installs network/model blocking before project imports
from PIL import Image  # noqa: E402

from src.agent.runtime_roles.readers import ReaderTools  # noqa: E402
from src.agent.runtime_roles.trial import PlanTrialSession  # noqa: E402

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / "2026-10-06_plan_reader_probe/probe_trial_arguments.json"
OLD = HERE.parent / "2026-10-06_plan_reader_probe/probe_trials.json"
WORK = ROOT / "AI_agent/archive/local_backup/d1c/probe-replay"


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Counted:
    def __init__(self, wrapped):
        self.wrapped, self.calls = wrapped, []

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    async def call_tool(self, name, arguments):
        self.calls.append(name)
        return await self.wrapped.call_tool(name, arguments)


async def run():
    started = time.monotonic()
    source = json.loads(INPUT.read_bytes())
    old = {row["request"]: row for row in json.loads(OLD.read_bytes())["rows"]}
    image = ROOT / source["image"]
    if WORK.exists():
        raise ValueError(f"fresh replay directory required: {WORK}")
    (WORK / "images").mkdir(parents=True)
    shutil.copyfile(image, WORK / "images" / image.name)
    with Image.open(image) as original:
        size = list(original.size)
    write(WORK / "inputs.json", {"images": {image.name: {"size": size, "sha256": digest(image)}},
          "image_kind": "drawings"})
    rows = []
    async with PlanTrialSession(WORK, image.name, root=ROOT) as trial:
        counted = Counted(trial.tools)
        trial.tools = counted
        reader = ReaderTools(counted, role_id="plan_reader", image_name=image.name, trial=trial, target="F1")
        for index, record in enumerate(source["trials"], 1):
            arguments = record["arguments"]
            before_calls = len(counted.calls)
            baseline = trial.baseline()[1]
            result = await reader.call_tool("trial_plan_bim", {"plan": arguments["plan"]})
            receipt = result["structuredContent"]
            category = ("format" if receipt.get("error_type") == "plan_format" else
                        "passed" if receipt.get("source_geometry_ready") else
                        "rejected" if receipt.get("status") == "rejected" else "geometry_or_compile")
            row = {"trial": index, "request": record["request"], "old_class": old[record["request"]]["class"],
                   "new_class": category, "removed_parameters": sorted(set(arguments) - {"plan"}),
                   "input_plan_sha256": hashlib.sha256(json.dumps(arguments["plan"], sort_keys=True,
                       ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
                   "baseline_before": baseline, "baseline_after": trial.baseline()[1],
                   "frozen_calls": counted.calls[before_calls:], "format_error_count": len(receipt.get("format_errors", [])),
                   "receipt": receipt}
            rows.append(row)
            print(f'{index:02d} request={record["request"]}: {category}, format_errors={row["format_error_count"]}', flush=True)
            write(HERE / "probe_replay.json", {"status": "running", "model_service_requests": 0, "rows": rows})
    summary = {"status": "completed", "model_service_requests": 0, "paratera_requests": 0,
               "deepseek_requests": 0, "real_model_tests": 0, "full_model_runs": 0,
               "method": "sequential original tool plans; only base_plan_sha256/changes removed; real frozen MCP compiler",
               "source_arguments": {"path": INPUT.relative_to(ROOT).as_posix(), "sha256": digest(INPUT)},
               "source_image": {"path": image.relative_to(ROOT).as_posix(), "sha256": digest(image)},
               "elapsed_seconds": round(time.monotonic() - started, 3),
               "by_class": dict(Counter(row["new_class"] for row in rows)), "rows": rows,
               "frozen_tool_calls": dict(Counter(counted.calls)),
               "saved_candidates": len(list((WORK / "trial_workspace").glob("candidate_*")))}
    write(HERE / "probe_replay.json", summary)
    assert len(rows) == 17
    assert all(row["new_class"] != "rejected" for row in rows if row["baseline_before"] is None)
    assert all(row["receipt"]["repair_hint"]["example"] for row in rows if row["new_class"] == "format")
    print(json.dumps({key: summary[key] for key in ("by_class", "frozen_tool_calls", "saved_candidates", "elapsed_seconds")}), flush=True)


if __name__ == "__main__":
    asyncio.run(run())
