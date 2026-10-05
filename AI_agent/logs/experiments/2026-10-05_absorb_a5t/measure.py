"""Reproduce the four-term metric with baseline parameter annotations isolated."""
import asyncio
import importlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import bim_agent_guidance as guidance, run_bim_agent as runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = 'f4d48cf7'


def default_catalog(module, guide, run, *, mesh=False):
    servers = []
    with patch.object(FastMCP, 'run', lambda server: servers.append(server)):
        module.serve(run)
    full = [t.model_dump(mode='json', by_alias=True) for t in asyncio.run(servers[0].list_tools())]
    enabled = guide.filter_tool_catalog(full)
    result = dict(tool_count=len(enabled), tool_description_chars=sum(len(t.get('description','')) for t in enabled),
        input_schema_json_chars=sum(len(json.dumps(t['inputSchema'])) for t in enabled),
        system_prompt_chars=len(guide.build_guide(mesh=True) if mesh else guide.build_guide(images='drawings')),
        common_reference_chars=sum(len(guide.REFERENCES[k]) for k in ('plan_partition', 'claims')))
    result['instruction_total_chars'] = sum(v for k,v in result.items() if k != 'tool_count')
    return result


def main():
    measure = importlib.import_module('AI_agent.logs.experiments.2026-10-03_tool_package_t1.measure_instructions')
    old_guide = measure.baseline_module('scripts/tool_scripts/bim_agent_guidance.py', 'a5t_old_guide', BASE)
    old_runner = measure.baseline_module('scripts/tool_scripts/run_bim_agent.py', 'a5t_old_runner', BASE)
    old_feedback = measure.baseline_module('scripts/tool_scripts/bim_agent_feedback.py', 'a5t_old_feedback', BASE)
    # The generic old helper imports present-day ImageFilename into its baseline
    # runner, contaminating old schemas when this shared annotation changes.
    old_runner.ImageFilename = old_feedback.ImageFilename
    old_runner.filter_tool_catalog = old_guide.filter_tool_catalog
    with tempfile.TemporaryDirectory(prefix='measure-', dir=ROOT/'.tmp_a5t') as directory:
        run = Path(directory)
        runner.dump(run/'inputs.json', dict(images={}, scope='offline catalog measurement'))
        before = measure.measure(old_runner, old_guide, run)
        after = measure.measure(runner, guidance, run)
        defaults = dict(before=default_catalog(old_runner, old_guide, run),
                        after=default_catalog(runner, guidance, run))
        runner.dump(run/'inputs.json', dict(images={}, scope='offline native mesh catalog',
            mesh_input=dict(sha256='0'*64, frozen_path='assets/catalog-placeholder.glb')))
        mesh_defaults = dict(before=default_catalog(old_runner, old_guide, run, mesh=True),
                             after=default_catalog(runner, guidance, run, mesh=True))
    initial = json.loads((HERE/'instructions_before.json').read_text())
    assert before == initial['after'], 'Baseline must reproduce the pristine pre-edit measurement'
    assert defaults['before']['instruction_total_chars'] == initial['default_enabled_catalog']['instruction_total_chars']
    mesh = {label: dict(legacy_or_assembled_constant_chars=len(guide.MESH_GUIDE),
                default_system_chars=len(guide.build_guide(mesh=True)))
            for label,guide in (('before', old_guide), ('after', guidance))}
    result = dict(baseline_commit=BASE, model_requests=0, before=before, after=after,
        delta={k:after[k]-before[k] for k in before if k != 'references_chars'},
        default_catalog=defaults, mesh_system=mesh, mesh_default_catalog=mesh_defaults,
        method='Same historical four terms: drawing system prompt + all registered tool descriptions + json.dumps input schemas + plan_partition/claims references; Unicode characters. Full catalog includes replay handlers. Baseline ImageFilename restored from the same commit; pristine pre-edit snapshot independently matched.')
    assert after['instruction_total_chars'] < before['instruction_total_chars']
    (HERE/'instruction_comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(before=before['instruction_total_chars'], after=after['instruction_total_chars'],
        default_before=defaults['before']['instruction_total_chars'], default_after=defaults['after']['instruction_total_chars'], mesh=mesh)))


if __name__ == '__main__': main()
