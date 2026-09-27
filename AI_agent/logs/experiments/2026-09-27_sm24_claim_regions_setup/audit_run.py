"""Use unchanged post-generation diagnostics, explicitly relabel recovery inputs."""
import argparse
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def audit(run):
    frozen = json.loads((HERE / f'{run.name}_frozen.json').read_text())
    prior = ROOT / frozen['prior_run']
    for name, sha in frozen['prior_claim_file_sha256'].items():
        assert digest(prior / 'claims' / name) == sha
    shared = importlib.import_module('AI_agent.logs.experiments.2026-09-27_sm24_continuation_setup.audit_run')
    shared.HERE = HERE
    shared.audit(run)
    scope = json.loads((run / 'evaluation/reference_scope.json').read_text())
    scope['generation_input_note'] = 'Saved proposal, five original PNGs and verbatim unverified old claim declarations in scope. No decisions/confirmations, corrected regions or evaluation supplied. Bounded recovery, not cold generation.'
    dump(run / 'evaluation/reference_scope.json', scope)
    plan = json.loads((run / 'postrun_audit.json').read_text())
    plan['generation_input_note'] = scope['generation_input_note']
    plan['limits'] = [item for item in plan['limits'] if not item.startswith('One bounded cold start')]
    plan['limits'].append('Bounded prior-proposal/claim recovery, not independent cold generation or proof of repeatability.')
    dump(run / 'postrun_audit.json', plan)
    report = json.loads((run / 'continuation_audit.json').read_text())
    report['original_plan'] = plan
    report['input_mode'] = frozen['mode']
    report['limits'][0] = 'Explicit bounded recovery of prior unverified model claims, not autonomous cold generation or a causal prompt/tool comparison.'
    dump(run / 'continuation_audit.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    audit(parser.parse_args().run.resolve())
