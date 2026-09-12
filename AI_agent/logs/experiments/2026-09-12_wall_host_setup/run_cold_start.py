"""Independent original-images-only reconstruction with the current toolset."""
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

if __name__ == "__main__":
    run_experiment(SimpleNamespace(
        images=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run18/images",
        out=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run19",
        resume_candidate=None,
        timeout=720,
        scope=("Reconstruct the single building shown in all supplied original plan and elevation "
               "drawings as a viewable lightweight BIM. Preserve the actual rooms, physical partitions, "
               "windows, doors and connections. Establish drawing directions and dimensional bases "
               "from the originals, use deterministic tools for calculations, and distinguish direct "
               "evidence from assumptions. Produce a first viewable candidate early enough to "
               "compare it with the drawings and make useful corrections. Calibrated overlays and "
               "local detail review are available when helpful; inspect and respond to actual tool "
               "feedback. Prioritize correct spatial structure and openings over tiny coordinate "
               "differences. Report the scope actually checked and unresolved facts honestly, then "
               "select a candidate for delivery within budget. Do not simulate downstream."),
    ))
