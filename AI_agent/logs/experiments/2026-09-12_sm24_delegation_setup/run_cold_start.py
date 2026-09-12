"""Original-only sm24 reconstruction with an actual bounded Haiku delegation."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

if __name__ == "__main__":
    run_experiment(SimpleNamespace(
        images=ROOT / "case_tests/e2e_tests/sm24_anchor/case_data",
        out=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm24_run01",
        resume_candidate=None,
        timeout=720,
        scope=("Reconstruct the single building from all supplied plan and elevation originals. "
               "Preserve the physical room partitions, continuous spaces, windows, doors and "
               "connections. Do not split a continuous space merely to make rectangular cells, "
               "and do not drop observed apertures to clear a build error. This experiment also "
               "tests lightweight-model delegation: early in the run, use review_detail for one "
               "bounded substantive original-image task of your choice, such as one facade's "
               "aperture inventory or one local dimension chain. Ask a neutral evidence question "
               "without supplying your expected answer. Haiku's observation is a hypothesis to "
               "verify against the drawing; you retain responsibility for geometry and corrections. "
               "Do not delegate whole-building reconstruction. Save a useful first candidate "
               "early, then inspect the actual source plan and elevation views and use original "
               "image feedback to revise substantive discrepancies. Retain explicit assumptions "
               "and unresolved scope and finish with the selected saved candidate within budget."),
    ))
