"""Bounded original-image recovery of sm24/run07; no evaluation inputs."""
from argparse import Namespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

SCOPE = """Continue reconstruction from the saved proposal and supplied original drawings.
Focus this increment on the remaining east-side physical partitions and their
associated interior doors. Retain reliable west-side rooms, the recovered
southeast room contour and exterior apertures unless original evidence shows a
necessary related change. The seed's notes and coordinates are hypotheses.
Use a bounded original-image observation to identify the actual wall segments,
matching dimension endpoints and wall-hosted door jambs. Distinguish furniture,
door leaves/arcs and physical partitions. Background-region and complete-contour
previews are available if useful, but they do not certify wall identity.
Act as coordinator: local measurement, arithmetic and geometry edits belong in
tools. You may ask review_detail one small question with a short explicit time
budget, then inspect material conflicts; do not redo a full building reading.
Apply supported local changes yourself through revise_bim, retaining stable
room/opening IDs. Keep each opening's width/height unless its own drawing
evidence justifies changing it; shifting walls is not evidence for resizing.
Use reshape_spaces or replace_space_region if appropriate. These preserve
openings, so any affected door must be updated explicitly in the same revision.
Register a drawing frame with observed original-pixel anchors and inspect the
new source overlay, actual plan and affected opening hosts before finish_bim.
Save the useful correction with at least 75 seconds left for these checks.
Keep unresolved calibration/face differences explicit in saved notes. If no
change is supported, retain the seed and explain the particular missing evidence.
This is development-directed local recovery from an assisted seed, not an
independent full-building cold start. No GT, old local observations, correct
coordinates or evaluation report are supplied. Total budget is 360 seconds.
"""

if __name__ == "__main__":
    run_experiment(Namespace(
        images=ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run04/images",
        out=ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run08",
        resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run07/candidate_01",
        scope=SCOPE, timeout=360,
    ))
