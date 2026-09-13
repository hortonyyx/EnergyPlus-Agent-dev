"""Apply or reject an unchanged local observation against original evidence."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

OBSERVATION = ROOT/'AI_agent/logs/experiments/2026-09-13_sm24_pixel_support_observation'
OUT = ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run05'
SCOPE = """Continue this saved reconstruction with one bounded local correction.
Focus on the southeast space boundary and its opening, preserving the other
reliable geometry. An unchanged independent local model observation follows.
It is a fallible hypothesis, not a correct answer. Inspect its cited original
locations with the original plan and deterministic measurement tools as needed;
resolve contradictions before applying geometry. Preserve the corridor recovery
and other existing rooms. Do not invent partitions to make rectangles. Use
reshape_spaces plus explicit update_opening operations for affected existing
objects, instead of rewriting the whole building. Preserve reliable aperture
widths/heights; any changed width or host needs actual local evidence and explicit
source notes. Do not silently delete openings or claim all were checked.
Sonnet should decide how evidence changes the saved proposal, not redo a full
reading. No further worker is required; use one only for a remaining bounded
ambiguity if the budget permits. Aim to save with at least 70 seconds left.
Inspect the actual new source plan and affected openings after saving. If a
revision cannot be supported, retain the seed with an honest limitation.
Select the saved candidate using finish_bim. This is observation-assisted saved
candidate recovery, not cold start. Total wall-clock budget 300 seconds.
No GT/evaluation/developer-corrected coordinates are supplied.

UNMODIFIED LOCAL MODEL OBSERVATION:
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', type=Path, default=OBSERVATION)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    OBSERVATION, OUT = args.observation.resolve(), args.out.resolve()
    observation = json.loads((OBSERVATION/'response.json').read_text())
    if not observation.get('completed'):
        raise SystemExit('No completed observation; recovery not invoked.')
    run_experiment(SimpleNamespace(images=ROOT/'case_tests/e2e_tests/sm24_anchor/case_data',
        out=OUT, resume_candidate=ROOT/'AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run04/candidate_01',
        timeout=300, scope=SCOPE+observation['result']))
    shutil.copy2(OBSERVATION/'response.json', OUT/'supplied_observation.json')
    dump(OUT/'observation_provenance.json', {
        'response_path': str(OBSERVATION/'response.json'), 'response_sha256': digest(OBSERVATION/'response.json'),
        'request_sha256': digest(OBSERVATION/'detail_01_request.json'),
        'mode': 'full_unmodified_local_model_response; no evaluation injected',
        'developer_intervention': 'selected local boundary task and recovery scope; no supplied coordinates or rewritten observation',
    })
