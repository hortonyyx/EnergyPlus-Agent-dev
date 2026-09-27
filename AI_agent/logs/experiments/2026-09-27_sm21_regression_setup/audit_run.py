"""Unchanged post-generation quality checks plus actual guidance verification."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

HERE = Path(__file__).resolve().parent


def audit(run):
    load = lambda p: json.loads(p.read_text())
    frozen = load(HERE / f'{run.name}_frozen.json')
    request = load(run / 'agent_request.json')
    assert hashlib.sha256(request['system_prompt'].encode()).hexdigest() == frozen['guide_sha256']
    assert request['timeout_seconds'] == frozen['timeout_seconds']
    assert request['effort'] == frozen['effort']
    base = importlib.import_module(
        'AI_agent.logs.experiments.2026-09-27_sm21_current_tools_setup.audit_run')
    base.HERE = HERE
    base.audit(run)
    report = load(run / 'postrun_audit.json')
    report['guidance_comparison'] = {k:frozen[k] for k in
        ('variant','guide_sha256','controlled_difference','limits')}
    report['limits'][0] = 'One arm of a controlled guidance pair; no statistical causal conclusion.'
    dump(run / 'postrun_audit.json', report)
    importlib.import_module(
        'AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views').audit(run)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    audit(parser.parse_args().run.resolve())
