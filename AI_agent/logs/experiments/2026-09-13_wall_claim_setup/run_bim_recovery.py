"""Use an unmodified local observation as a hypothesis in source-BIM recovery."""
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

OBSERVATION = ROOT / "AI_agent/logs/experiments/2026-09-13_sm24_dimension_observation_sonnet"
OUT = ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run03"
SCOPE = """Resume this saved BIM from the original drawings, focusing on physical
room partitions and continuous spaces. A separate local model observation of
two annotation chains follows unchanged. It is a hypothesis from the original,
not a GT answer: verify its labels and endpoint meaning against the supplied
plan before relying on it. Distinguish room/footprint subdivisions from chains
of window and door widths/gaps; a sum alone does not establish a partition.
Use available deterministic chain/pixel calculations for arithmetic. Small
detail crops may use display_scale=4 while all locations remain original pixels.
Inspect the seed source plan, compare actual wall extents to the annotated
divisions and visible physical boundaries, and revise substantive discrepancies.
Preserve genuine continuous/nonrectangular spaces; do not invent a wall to make
rectangles or assume separate furniture groups are separate rooms. The seed and
its statements of verification may be wrong. Preserve reliable exterior aperture
geometry, and reassign hosts consistently if the physical spaces change. A
rejected inferred partition may require removing a falsely inferred door with
explicit drawing evidence; distinct visible doors must not be silently dropped.
Use a full revised proposal if local edits cannot represent the required change.
Save useful changes early, inspect the resulting source against the original,
record unresolved items honestly, and select the saved candidate with finish_bim.
This is a local-observation-assisted recovery, not a new cold start. Do not do
another whole-building reading or spend this budget refining wall thickness.

UNMODIFIED LOCAL OBSERVATION:
"""

if __name__ == "__main__":
    observation = json.loads((OBSERVATION / "response.json").read_text())
    if not observation.get("completed"):
        raise SystemExit("The local observation did not complete; no model call made.")
    if OUT.exists():
        raise SystemExit("Use a fresh recovery run; never overwrite an existing experiment.")
    args = SimpleNamespace(
        images=ROOT / "case_tests/e2e_tests/sm24_anchor/case_data", out=OUT,
        resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run02/candidate_01",
        timeout=480, scope=SCOPE + observation["result"],
    )
    run_experiment(args)
    shutil.copy2(OBSERVATION / "response.json", OUT / "supplied_observation.json")
    dump(OUT / "observation_provenance.json", {
        "response_path": str(OBSERVATION / "response.json"), "response_sha256": digest(OBSERVATION / "response.json"),
        "request_sha256": digest(OBSERVATION / "detail_01_request.json"),
        "mode": "full_unmodified_local_model_response_in_scope; no evaluation injected",
        "developer_intervention": "selected annotation task, selected completed observation, and requested partition recovery; no supplied coordinates/counts",
    })
