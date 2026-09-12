"""Bounded original-image wall-host recovery; Claude subscription only."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

if __name__ == "__main__":
    run_experiment(SimpleNamespace(
        images=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run17/images",
        out=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run18",
        resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run17/candidate_02",
        timeout=480,
        scope=("Continue reconstruction by establishing whether the saved local wall-thickness "
               "and dimension evidence actually refers to its declared source wall segments. "
               "Previous notes are claims, not a verified image reading. Inspect the original plan "
               "and relevant local marks, compare with the actual source segment extents and use "
               "a plan overlay when helpful. It now labels both saved evidence pixels and their "
               "declared wall segments. Establish your own calibration from the original; no old "
               "frame is supplied. Correct unsupported host attribution or explicitly distinguish "
               "direct observation from transfer/inference. Retain both existing dimension records "
               "and raw labels; only revise recorded pixels if the original gives a specific reason. "
               "Preserve reliable rooms, openings and connections. Prioritize the existing local "
               "evidence rather than full-building measurement or a fresh reading. Save a useful "
               "revision early, inspect the source and any returned new projection, persist real "
               "limitations and finish within budget. No downstream simulation is needed."),
    ))
