# ???? V1 ????????

?????? `checks.json`????????????????

## registry-tests

```text
bringing up nodes...
bringing up nodes...

....................................................                     [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
52 passed in 44.42s
```

## integration-tests

```text
bringing up nodes...
bringing up nodes...

.........................F.................                              [100%]
================================== FAILURES ===================================
___ test_claude_receipt_identifies_registered_agent_without_starting_model ____
[gw0] win32 -- Python 3.12.10 D:\EnergyPlus-Agent-worktrees\v1\.venv\Scripts\python.exe

tmp_path = WindowsPath('D:/EnergyPlus-Agent-worktrees/v1/AI_agent/archive/local_backup/v1/pytest/popen-gw0/test_claude_receipt_identifies0')

    def test_claude_receipt_identifies_registered_agent_without_starting_model(tmp_path):
        run = tmp_path / "expired"
        run.mkdir()
        (run / "inputs.json").write_text(json.dumps({"images": {}, "started_epoch": 1, "deadline_epoch": 2}))
        with patch.object(runner.subprocess, "Popen", side_effect=AssertionError("model launch forbidden")):
>           receipt = runner.subscription(run, "offline expired run", model="sonnet", name="agent")
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\test_runtime_r3.py:175: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
scripts\tool_scripts\run_bim_agent.py:348: in subscription
    version_identity = external_run_identity(ROOT, mode="single_model", role_models=role_models)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\agent_runtime\versions.py:107: in external_run_identity
    "mode": mode, "role_models": role_models, "git_commit": source_commit(root)}
                                                            ^^^^^^^^^^^^^^^^^^^
src\agent_runtime\agent_registry.py:99: in source_commit
    return _git(root, "rev-parse", "HEAD")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\agent_runtime\agent_registry.py:93: in _git
    return subprocess.check_output(["git", "--no-optional-locks", *args], cwd=root,
C:\Users\Horton\AppData\Local\Programs\Python\Python312\Lib\subprocess.py:466: in check_output
    return run(*popenargs, stdout=PIPE, timeout=timeout, check=True,
C:\Users\Horton\AppData\Local\Programs\Python\Python312\Lib\subprocess.py:548: in run
    with Popen(*popenargs, **kwargs) as process:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Horton\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py:1139: in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Horton\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py:1143: in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <MagicMock name='Popen' id='2804407920224'>
args = (['git', '--no-optional-locks', 'rev-parse', 'HEAD'],)
kwargs = {'cwd': WindowsPath('D:/EnergyPlus-Agent-worktrees/v1'), 'encoding': 'utf-8', 'stdout': -1, 'text': True}
effect = AssertionError('model launch forbidden')

    def _execute_mock_call(self, /, *args, **kwargs):
        # separate from _increment_mock_call so that awaited functions are
        # executed separately from their call, also AsyncMock overrides this method
    
        effect = self.side_effect
        if effect is not None:
            if _is_exception(effect):
>               raise effect
E               AssertionError: model launch forbidden

C:\Users\Horton\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py:1198: AssertionError
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
=========================== short test summary info ===========================
FAILED tests/test_runtime_r3.py::test_claude_receipt_identifies_registered_agent_without_starting_model
1 failed, 42 passed in 489.19s (0:08:09)
```

## final-tests

```text
bringing up nodes...
bringing up nodes...

.....................                                                    [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
21 passed in 63.49s (0:01:03)
```
