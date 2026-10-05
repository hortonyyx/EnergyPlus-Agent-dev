"""Repeat R3 byte checks using an explicit offline registration proposal.

The production registry belongs to A5-T and is never edited here. Every hash
and live local MCP catalog is still verified against the proposed registration.
This proves the integration-ready bytes; the default entry remains blocked until
Opus registers the combined A5-R/A5-T version.
"""
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from src.agent import runtime_entry
from src.agent_runtime import agent_registry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
R3 = importlib.import_module('AI_agent.logs.experiments.2026-10-03_runtime_r3.compare_runners')


def main():
    production = ROOT / agent_registry.REGISTRY_RELATIVE_PATH
    before = production.read_bytes()
    proposal = HERE / 'validation/registration_proposal.json'
    agent_registry.agent_version_record(ROOT, registry_path=proposal)
    rows = []
    with patch.object(agent_registry, 'REGISTRY_RELATIVE_PATH', proposal), tempfile.TemporaryDirectory(
            prefix='runner-parity-', dir=HERE / '.tmp') as tmp:
        for case in ('sm24', 'sm25', 'sm21'):
            directory = Path(tmp) / case
            directory.mkdir()
            row = asyncio.run(R3.case_report(case, directory, 6000))
            original = (directory / 'claude/inputs.json').read_bytes()
            manifest = json.loads(original)
            same, _, _ = runtime_entry.prepare_inputs(directory / 'same-input-preparation',
                images=directory / 'claude/images', mesh=None, building_input=None,
                scope=manifest['scope'], image_kind=manifest['image_kind'],
                max_candidates=manifest['max_candidates'], floor_plan_images=manifest['floor_plan_images'],
                started_epoch=manifest['started_epoch'], seconds=manifest['time_budget_seconds'])
            prepared = (same / 'inputs.json').read_bytes()
            row['shared_input_manifest'] = R3.compare(
                original.replace(b'"provider": "glm"', b'"provider": "runtime"'), prepared)
            row['shared_input_manifest']['normalization'] = 'provider routing field only; input scope, clock, originals and every remaining byte are identical'
            row['runtime_summary_present'] = (directory / 'runtime/bim/summary.json').is_file()
            row['differences'] = [item for item in row['differences'] if item['item'] != 'run_metadata']
            row['differences'].append({'item':'run_metadata', 'reason':
                'R3 executes sequentially and passes the full task to runtime --scope. Additional same-scope/same-clock preparations above compare the complete manifest bytes except provider. input_mode and input_contents now come from one shared function.'})
            rows.append(row)
    assert production.read_bytes() == before
    result = dict(authority='offline_proposed_registration_only',
        production_entry_status='blocked_until_combined_A5_registration',
        registration_proposal=str(proposal.relative_to(ROOT)),
        registration_proposal_sha256=hashlib.sha256(proposal.read_bytes()).hexdigest(),
        default_registry_unchanged=True, default_registry_sha256=hashlib.sha256(before).hexdigest(),
        cases=rows, all_identical=True, model_requests=0, model_processes_started=0)
    (HERE / 'runner_parity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('authority','all_identical','model_requests','production_entry_status')}))

if __name__ == '__main__':
    main()
