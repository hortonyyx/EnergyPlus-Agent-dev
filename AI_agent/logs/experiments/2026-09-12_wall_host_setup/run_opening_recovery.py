"""Recover the original failed door declarations; no GT/answer injection."""
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

if __name__ == "__main__":
    run_experiment(SimpleNamespace(
        images=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run19/images",
        out=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run20",
        resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run19/candidate_02",
        timeout=300,
        scope=("Resolve the actual source opening-host failures in this saved candidate, which "
               "retains its original declared apertures. Inspect the production findings and "
               "submitted geometry, use the originals when their interpretation is needed, and "
               "make a local correction that preserves the visible doors and their declared room "
               "connections. Do not remove apertures to clear build errors. Preserve the existing "
               "rooms and other openings while fixing the supported cause. Save and inspect the "
               "revised source, retain honest assumptions and unexamined scope, then finish within "
               "budget. This bounded recovery is not a full-building rereading or window repair; "
               "do not spend the budget on global calibration or unrelated dimensions."),
    ))
