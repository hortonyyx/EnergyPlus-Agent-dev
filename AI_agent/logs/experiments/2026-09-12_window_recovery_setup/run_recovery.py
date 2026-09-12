"""Original-elevation recovery from the latest cold-start-derived source."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

if __name__ == "__main__":
    run_experiment(SimpleNamespace(
        images=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run20/images",
        out=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run21",
        resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run20/candidate_01",
        timeout=600,
        scope=("Review the original elevations against this saved source, focusing on floor "
               "levels and windows: completeness, physical facade, horizontal span, sill/head "
               "heights and room attribution. Use the original drawings and their dimension "
               "chains, including distinct window types. Correct supported discrepancies and "
               "retain explicit assumptions where evidence is insufficient. Preserve existing "
               "room partitions and all doors and connections; if a floor datum needs correction, "
               "preserve the floor-relative positions of its hosted openings. Do not delete visible "
               "apertures to clear errors. Unsupported local edits can use a complete build_bim "
               "proposal preserving all reliable objects and IDs. Save a useful revised candidate "
               "early enough to inspect it, and review its windows against the actual drawings "
               "before finish. This is a bounded elevation/window recovery, not a new cold start "
               "or a rereading of unrelated plan dimensions."),
    ))
