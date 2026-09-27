"""Candidate exports remain bounded without silently sharing a six-save quota."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts.tool_scripts import run_bim_agent as runner
from tests.test_bim_agent_tools import _json_result, _server_session
from tests.test_bim_claims import setup_run
from tests.test_source_proposal import _proposal


def test_seventh_revision_persists_and_explicit_limit_preserves_prior_candidates(tmp_path):
    run, _ = setup_run(tmp_path)
    manifest = json.loads((run / 'inputs.json').read_text())
    manifest['max_candidates'] = 7
    runner.dump(run / 'inputs.json', manifest)
    toolkit = runner.Toolkit(run)
    parent = 'seed'
    hashes = {}
    for index in range(1, 8):
        result = toolkit.revise(parent, json.dumps([dict(op='set_notes',
            assumptions=[f'synthetic revision {index}'], unresolved=[])]))
        assert result['source_geometry_ready']
        parent = result['candidate']
        hashes[parent] = runner.digest(run / parent / 'source_model.json')
    assert parent == 'candidate_07'
    assert result['candidate_budget'] == {'limit': 7, 'used': 7, 'remaining': 0}
    # Reload as a separate MCP/continuation server would; the quota is shared.
    toolkit = runner.Toolkit(run)
    blocked = toolkit.build(_proposal())
    assert 'candidate budget exhausted' in blocked['error']
    assert blocked['candidate_budget'] == result['candidate_budget']
    assert not (run / 'candidate_08').exists()
    assert all(runner.digest(run / name / 'source_model.json') == sha for name, sha in hashes.items())


def test_legacy_manifest_still_reports_six_and_stdio_exposes_configured_budget(tmp_path):
    async def scenario():
        run, toolkit = setup_run(tmp_path)
        assert toolkit.candidate_budget() == {'limit': 6, 'used': 0, 'remaining': 6}
        manifest = json.loads((run / 'inputs.json').read_text())
        manifest['max_candidates'] = 11
        runner.dump(run / 'inputs.json', manifest)
        async with _server_session(run, readonly=False) as session:
            response = _json_result(await session.call_tool('inputs', {}))
            assert response['candidate_budget'] == {'limit': 11, 'used': 0, 'remaining': 11}
            tools = {t.name:t for t in (await session.list_tools()).tools}
            assert 'Six immutable candidates maximum' not in tools['build_bim'].description
    asyncio.run(scenario())


@pytest.mark.parametrize('value', [0, -1, True, 2.5, '24'])
def test_invalid_limit_does_not_create_run_or_invoke_model(tmp_path, value):
    with pytest.raises(ValueError, match='max_candidates'):
        runner.run_experiment(SimpleNamespace(out=tmp_path / 'new', max_candidates=value))
    assert not (tmp_path / 'new').exists()


def test_new_run_freezes_default_and_configured_limit(tmp_path, monkeypatch):
    old, _ = setup_run(tmp_path)
    limits = []
    def invoke(run, prompt, **kwargs):
        manifest = json.loads((run / 'inputs.json').read_text())
        limits.append(manifest['max_candidates'])
        assert runner.Toolkit(run).candidate_budget()['limit'] == manifest['max_candidates']
        record = {'returncode':0, 'elapsed_seconds':1,
                  'result':{'is_error':False, 'result':'No candidate in synthetic test', 'total_cost_usd':0}}
        runner.dump(run / 'agent_receipt.json', record)
        return record
    monkeypatch.setattr(runner, 'subscription', invoke)
    for name, options in [('default', {}), ('custom', {'max_candidates':9})]:
        runner.run_experiment(SimpleNamespace(images=old / 'images', out=tmp_path / name,
            scope='synthetic budget configuration', timeout=60, **options))
    assert limits == [24, 9]
