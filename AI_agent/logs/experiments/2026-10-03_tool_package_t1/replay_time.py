"""Replay sm25's real save timeline against the new 6000-second budget."""
import importlib
import json
from pathlib import Path
import shutil
import tempfile

from scripts.tool_scripts.run_bim_agent import Toolkit, dump, digest
from scripts.tool_scripts.bim_agent_budget import time_status, fallback_selection, saved_floor_status

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
helpers = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.replay_errors")


def main():
    original = HERE.parent / "2026-10-02_sm25_glm_baseline"
    manifest = json.loads((original / "inputs.json").read_text())
    start = manifest["deadline_epoch"] - 3000
    events = [json.loads(line) for line in (original / "tools.jsonl").read_text().splitlines()]
    saved_at = {event["data"]["candidate"]: event["time"] - start for event in events
                if event["data"].get("source_geometry_ready") and event["data"].get("candidate")}
    with tempfile.TemporaryDirectory(dir=ROOT / ".tmp_t1", prefix="time-") as directory:
        run = Path(directory)
        helpers.copy_run(original, run)
        manifest.update(started_epoch=start, deadline_epoch=start + 6000, time_budget_seconds=6000,
                        floor_plan_images=["1f_view.png", "2f_view.png"], floor_scope_source="explicit_input_filenames")
        dump(run / "inputs.json", manifest)
        samples = []
        # Include the exact tool-return times and the new policy boundaries. There
        # was no historical tool call at 3000s: the old process was being stopped.
        moments = sorted(set([event["time"] - start for event in events] + [3000, 5101, 6000]))
        for elapsed in moments:
            for candidate, created in saved_at.items():
                visible, hidden = run / candidate, run / ("hidden_" + candidate)
                if elapsed < created and visible.exists():
                    visible.rename(hidden)
                elif elapsed >= created and hidden.exists():
                    hidden.rename(visible)
            status = time_status(Toolkit(run), now=start + elapsed)
            samples.append(dict(elapsed_seconds=round(elapsed, 3), line=status["line"],
                missing_draft_images=status["floors"]["missing_draft_images"],
                at_original_tool_return=any(abs(event["time"] - start - elapsed) < .001 for event in events)))
        fifty = next(row for row in samples if row["elapsed_seconds"] == 3000)
        assert "时间已过半" in fifty["line"] and fifty["missing_draft_images"] == ["2f_view.png"]
        assert fallback_selection(Toolkit(run))[0] == "candidate_01"
        assert saved_floor_status(Toolkit(run), "candidate_01")["complete_building"] is False
    dump(HERE / "time_replay.json", dict(model_calls=0, source_run=original.name,
        source_tools_sha256=digest(original / "tools.jsonl"), actual_save_seconds=saved_at,
        interpretation="6000-second policy on preserved historical state, not a new model run. 50-minute boundary is simulated; the old 3000-second run had already stopped.",
        samples=samples))
    print(json.dumps(dict(model_calls=0, fifty_minute=fifty)))


if __name__ == "__main__":
    main()
