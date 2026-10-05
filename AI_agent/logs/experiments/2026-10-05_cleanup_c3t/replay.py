"""Exact local MCP replay and static instruction counts, without a model process.

Run before with PYTHONPATH=.tmp_c3t/baseline:<worktree>, after with <worktree>.
Baseline tool scripts are git-archive a5baa32d; unchanged geometry comes from the
worktree. Every historical input is hash-verified by prepare.py first.
"""
import argparse
import asyncio
import copy
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import run_bim_agent as runner, bim_agent_guidance as guidance
from scripts.tool_scripts.bim_agent_precision import building_precision
from scripts.tool_scripts.bim_agent_replies import summarize_reply, read_report
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.runtime_behaviour import load_behaviour

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / '.tmp_c3t'
helper = importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3t.replay_tools')
measure = importlib.import_module('AI_agent.logs.experiments.2026-10-03_tool_package_t1.measure_instructions')
helper.WORK = WORK


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def readback(run, data):
    if not data.get('details_file'):
        return None
    pages, offset = [], 0
    while True:
        page = read_report(run, data['details_file'], offset, 12000)
        pages.append(page['text'])
        if page['next_offset'] is None:
            break
        offset = page['next_offset']
    raw = ''.join(pages).encode()
    assert raw == (run/data['details_file']).read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), characters=len(raw.decode()),
                full=json.loads(raw))


def steps(name):
    record = load_behaviour(WORK / "history" / name)
    return [s for invocation in record["invocations"] for s in invocation["steps"]]


def main(side):
    report = dict(side=side, baseline='a5baa32d', model_requests=0, profiles=[], precision=[], errors=[])
    run = WORK / ('catalog_' + side)
    run.mkdir(exist_ok=True)
    runner.dump(run/'inputs.json', dict(images={}, scope='local catalog only'))
    report['instructions'] = measure.measure(runner, guidance, run)
    servers = []
    with patch.object(FastMCP, 'run', lambda s: servers.append(s)):
        runner.serve(run, enabled_only=True)
    catalog = asyncio.run(servers[0].list_tools())
    report['default_instructions'] = dict(tools=len(catalog),
        descriptions=sum(len(t.description or '') for t in catalog),
        schemas=sum(len(json.dumps(t.inputSchema)) for t in catalog))
    report['default_instructions']['total'] = (report['instructions']['system_prompt_chars']
        + report['instructions']['common_reference_chars']
        + report['default_instructions']['descriptions'] + report['default_instructions']['schemas'])
    output = HERE / (side + '.json')
    save(output, report)
    name = 'sm25_runtime_anthropic'
    calls = steps(name)
    call = next(c for c in calls if c['index'] == 118)
    assert call['tool'] == 'revise_bim'
    run, preparation = helper.fixture(name, call, side)
    data, pictures, geometry, texts = helper.capture(runner, run, call, compile_plan_partition)
    full = readback(run, data)
    report['revision'] = dict(step=118, tool=call['tool'], characters=sum(map(len, texts)),
        source_sha256=sha(run/data['candidate']/'source_model.json'), images=pictures,
        full_readback_sha256=full['sha256'] if full else None, fixture=preparation)
    save(HERE/'replies'/f'revise_bim_{side}.json', data)
    if full:
        save(HERE/'replies'/f'revise_bim_{side}_full.json', full['full'])
    save(output, report)
    shutil.rmtree(run)
    name = 'sm24_qwen27b_after_a2'
    origin = WORK/'history'/name/'bim'
    run = WORK/('profiles_' + side)
    if run.exists():
        shutil.rmtree(run)
    run.mkdir()
    shutil.copytree(origin/'images', run/'images')
    manifest = json.loads((origin/'inputs.json').read_bytes())
    manifest.pop('deadline_epoch', None)
    runner.dump(run/'inputs.json', manifest)
    calls = [c for c in steps(name)
             if c['tool'] == 'view_pixel_profile']
    assert len(calls) == 34
    profile_evidence = []
    for call in calls:
        data, pictures, _, texts = helper.capture(runner, run, call, compile_plan_partition)
        assert data.get('profile_id'), data
        full = readback(run, data)
        original = json.loads((run/data['profile_record']).read_bytes())
        if full:
            assert full['full'] == original
        report['profiles'].append(dict(step=call['index'], characters=sum(map(len, texts)),
            images=pictures, measurement_sha256=sha(run/data['profile_record']),
            full_readback_sha256=full['sha256'] if full else None))
        profile_evidence.append(dict(step=call['index'], returned=data, full=original))
    with gzip.open(HERE/'replies'/f'profiles_{side}.json.gz', 'wt') as stream:
        json.dump(profile_evidence, stream, ensure_ascii=False, indent=2)
    save(output, report)
    shutil.rmtree(run)
    names = ['sm24_runtime_anthropic', 'sm25_runtime_anthropic', 'sm24_claude_code',
             'sm24_qwen27b_paratera', 'sm24_qwen27b_after_a2']
    for name in names:
        original = WORK/'history'/name
        if (original/'bim').is_dir():
            original = original/'bim'
        run = WORK/('precision_' + side)
        if run.exists():
            shutil.rmtree(run)
        shutil.copytree(original, run)
        candidate = json.loads((run/'delivery.json').read_text())['candidate']
        before_hash = sha(run/candidate/'source_model.json')
        full = building_precision(runner.Toolkit(run), candidate)
        compact = summarize_reply(dict(building_precision=full))['building_precision']
        assert sha(run/candidate/'source_model.json') == before_hash
        report['precision'].append(dict(run=name, candidate=candidate, total=full['total'],
            characters=len(json.dumps(compact, ensure_ascii=False, separators=(',', ':'))),
            source_sha256=before_hash, full=full, returned=compact))
        save(output, report)
        shutil.rmtree(run)
    name = 'sm25_runtime_anthropic'
    calls = steps(name)
    for call in calls:
        original = helper.audit.result(call)
        if call['tool'] != 'revise_plan_bim' or "'z'" not in json.dumps(original):
            continue
        run, _ = helper.fixture(name, call, side)
        data, pictures, geometry, texts = helper.capture(runner, run, call, compile_plan_partition)
        report['errors'].append(dict(step=call['index'], error=data.get('error'),
            geometry_feedback=data.get('plan_input', {}).get('geometry_feedback'),
            geometry_changes=data.get('plan_revision', {}).get('geometry_changes')))
        save(HERE/'replies'/f'error_{call["index"]}_{side}.json', data)
        shutil.rmtree(run)
    assert len(report['errors']) == 4, report['errors']
    save(output, report)
    print(json.dumps(dict(side=side, instructions=report['instructions']['instruction_total_chars'],
        revision=report['revision']['characters'], profiles=sum(r['characters'] for r in report['profiles']),
        precision=[r['characters'] for r in report['precision']], error_steps=[r['step'] for r in report['errors']])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('side', choices=['before', 'after'])
    main(parser.parse_args().side)
