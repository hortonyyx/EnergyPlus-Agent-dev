"""One explicitly resumed, previously unstarted cold run; no loop or retries."""
import argparse
import asyncio
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from scripts.tool_scripts import run_bim_agent as runner

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = importlib.import_module('AI_agent.logs.experiments.2026-09-28_reconstruction_behavior.batch')
RUN = HERE.parent / '2026-09-28_sm21_behavior_repeat_run83'
load = lambda p: json.loads(p.read_text())


def frozen_conditions():
    expected = load(OLD.HERE / 'proposed_batch.json')['conditions']
    assert expected == OLD.conditions(), 'Production or task changed since the approved proposal'
    return expected


def prepare():
    conditions = frozen_conditions()
    assert not RUN.exists(), 'Do not overwrite a prior attempt'
    class BeforeModel(Exception):
        pass
    def no_launch(*args, **kwargs):
        raise BeforeModel()
    with tempfile.TemporaryDirectory(prefix='bim-resume-preflight-') as tmp:
        run = Path(tmp) / 'run'
        with patch.object(runner.subprocess, 'Popen', no_launch):
            try:
                runner.run_experiment(OLD.arguments(run))
            except BeforeModel:
                pass
            else:
                raise AssertionError('Expected stop before model process')
        manifest, request = load(run / 'inputs.json'), load(run / 'agent_request.json')
        assert manifest['images'] == conditions['images']
        assert manifest['implementation_sha256'] == conditions['implementation_sha256']
        assert request['requested_role'] == 'sonnet' and request['effort'] == 'medium'
        assert not manifest['input_contents']['saved_generated_proposal']['included']
        mcp = asyncio.run(OLD.check_reference(run))
    runner.dump(HERE / 'preflight.json', dict(model_calls=0, model_process_blocked=True,
        original_scope_and_production_unchanged=True, previous_run_unstarted=True,
        original_images_only=True, implementation_files=len(conditions['implementation_sha256']), **mcp))
    print(json.dumps(dict(status='preflight_pass', model_calls=0, **mcp)), flush=True)


def execute():
    authorization = load(HERE / 'authorization.json')
    assert authorization['status'] == 'authorized' and authorization['primary_invocations'] == 1
    assert authorization['run'] == RUN.name
    assert authorization['prior_proposal_sha256'] == runner.digest(OLD.HERE / 'proposed_batch.json')
    conditions = frozen_conditions()
    assert not RUN.exists(), 'Never overwrite or automatically retry'
    invoke_subscription = runner.subscription
    calls = 0
    def invoke(path, *args, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and kwargs['model'] == 'sonnet' and not kwargs.get('readonly')
        manifest = load(path / 'inputs.json')
        assert manifest['images'] == conditions['images']
        assert manifest['implementation_sha256'] == conditions['implementation_sha256']
        runner.dump(path / 'experiment_condition.json', conditions)
        for name, sha in conditions['implementation_sha256'].items():
            assert runner.digest(ROOT / name) == sha
            target = path / 'runtime_snapshot' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        runner.dump(HERE / 'launch.json', dict(started_at=datetime.now(timezone.utc).isoformat(),
            run=RUN.name, primary_invocations=1, code_baseline=authorization['current_commit'],
            method_and_production_frozen=True))
        return invoke_subscription(path, *args, **kwargs)
    try:
        with patch.object(runner, 'subscription', invoke):
            runner.run_experiment(OLD.arguments(RUN))
    finally:
        if (RUN / 'agent_receipt.json').exists():
            receipt = load(RUN / 'agent_receipt.json')
            runner.dump(HERE / 'execution_receipt.json', dict(run=RUN.name,
                subscription_invocations=calls, actual_model=receipt.get('actual_model'),
                returncode=receipt.get('returncode'), timed_out=receipt.get('timed_out', False),
                is_error=(receipt.get('result') or {}).get('is_error'),
                elapsed_seconds=receipt.get('elapsed_seconds'),
                api_error_status=receipt.get('api_error_status'),
                next_invocation='none; inspect real receipt and saved results'))
    assert calls == 1
    OLD.completed(RUN)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    action = parser.parse_args().action
    prepare() if action == 'prepare' else execute()
