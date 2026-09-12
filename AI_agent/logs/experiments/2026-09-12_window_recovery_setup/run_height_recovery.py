"""Use source elevation inspection to review aperture heights against originals."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

if __name__ == "__main__":
    run_experiment(SimpleNamespace(
        images=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run21/images",
        out=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run22",
        resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm21_run21/candidate_03",
        timeout=480,
        scope=("Review aperture vertical placement in this saved candidate against the original "
               "elevations. Use view_elevation_candidate to see the actual source geometry before "
               "and after your changes, alongside the corresponding original images. Establish "
               "which floor and opening type each dimension chain refers to; distinguish floor "
               "datum, sill, opening height and head clearance. Prior proposal notes are hypotheses "
               "to check, not independent evidence. Preserve current room partitions, horizontal "
               "opening positions, identities, windows, doors and connections; correct only supported "
               "vertical discrepancies and inaccurate notes. Do not infer new partitions from paired "
               "windows. Make a useful local revision early, inspect its actual elevation and "
               "retain honest unresolved scope before finish. This bounded recovery does not "
               "reread the whole plan or introduce new apertures."),
    ))
