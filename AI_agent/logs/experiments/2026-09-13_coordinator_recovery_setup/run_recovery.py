"""One bounded recovery: Sonnet chooses a local Haiku task and code edits."""
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

SCOPE = """Continue reconstruction from the saved proposal and original drawings.
Focus on ONE substantive unresolved plan-layout issue recorded in the seed.
Act primarily as coordinator: inspect the saved state, choose one bounded
original-image question for Haiku via review_detail (aim 90 seconds), inspect
the returned local evidence for contradictions, and decide a useful correction.
The worker must identify observable marks/labels and their original-pixel
locations, not confirm the seed's coordinates or a suggested correct answer.
For chained dimensions, request the identity of the dimension line, actual
label boxes and adjacent extension endpoints before trusting the arithmetic.
Do not reconstruct the entire drawing yourself or write a new whole-building
proposal when a local code edit can express the change. Keep Sonnet effort
focused on task selection, evidence conflicts, edit decisions and final checks.
Use reshape_spaces for existing room polygons if needed; it preserves other
objects, so any necessary opening movement must be an explicit separate edit
in the same revision. Preserve reliable opening widths/heights; moving a wall
does not justify proportionally resizing doors or windows. Uncertain geometry
must remain labelled uncertain, not forced to match a closed sum or room count.
Aim to save a useful correction with at least 75 seconds left, inspect the
actual resulting source plan and affected openings, then finish the selected
candidate. If the evidence cannot support a correction, retain the seed and
say exactly what remains unresolved. At most one focused follow-up question
is useful; do not repeat a full reading. Total wall-clock limit is 300 seconds,
including worker time. We will inspect actual parent/worker time and usage.
No independent evaluation, GT, corrected coordinates or external observation
is provided. This is saved-candidate recovery, not a cold start.
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run04")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(SCOPE)
    else:
        run_experiment(SimpleNamespace(
            images=ROOT / "case_tests/e2e_tests/sm24_anchor/case_data",
            resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run03/candidate_01",
            out=args.out, timeout=300, scope=SCOPE))
