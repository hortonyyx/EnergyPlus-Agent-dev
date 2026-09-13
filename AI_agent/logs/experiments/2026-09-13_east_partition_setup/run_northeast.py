"""Narrow recovery; excludes run08's rejected change and all evaluation inputs."""
from argparse import Namespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import run_experiment

SCOPE = """Recover only the northeastern small room immediately below the full-width
northern room, its shared physical partition with the large eastern meeting
room below it, and the corridor doors serving these two rooms. In the seed
these rooms are TopRightRoom and MeetingRoomBig. Keep the southeast room and
its openings unchanged. Do not spend this run reviewing the lower east wing.
Use the original plan to establish the actual straight wall and door jamb
segments. Register an original-image/world coordinate frame before edits.
Keep whole-building external dimensions separate from exterior aperture chains
and interior partition chains: a window jamb does not locate a partition.
For uncertain wall identity use a local background-region view or complete
room-contour preview. Use map_pixels/map_dimension_chain for conversions.
Apply a supported local revision via revise_bim within 120 seconds, then view
the same-frame automatic overlay and actual new source plan. Check the affected
door inventory/hosts before finish_bim. Code edits should retain other rooms,
windows and exterior doors; include explicit associated door moves if needed,
preserving their width/height unless own image evidence requires a change.
If no supported edit is found, finish the seed with an explicit explanation.
Do not call a wall or opening verified without comparing its actual drawn
segment in that common coordinate frame. Keep saved limitations honest.
This is development-directed local recovery, not cold start. The scope names
existing room IDs but supplies no correct geometry or pixel coordinates.
No prior local observation, rejected candidate or GT is supplied. 240 seconds.
"""

if __name__ == '__main__':
    run_experiment(Namespace(
        images=ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run04/images',
        out=ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run09',
        resume_candidate=ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run07/candidate_01',
        scope=SCOPE, timeout=240, effort='low',
    ))
