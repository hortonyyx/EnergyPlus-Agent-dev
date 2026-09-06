"""Run the same new inputs against baseline object code or current worktree code."""
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
baseline = '--baseline' in sys.argv
print('MODE', 'git object 94e899e5 (in memory)' if baseline else 'current worktree')
if baseline:
    for name in ('tick_claim', 'opening_adjudication'):
        module_name = 'src.agent.correction.' + name
        path = 'src/agent/correction/' + name + '.py'
        module = types.ModuleType(module_name)
        module.__file__ = '94e899e5:' + path
        sys.modules[module_name] = module
        source = subprocess.check_output(['git', 'show', '94e899e5:' + path], cwd=ROOT)
        exec(compile(source, module.__file__, 'exec'), module.__dict__)

from src.agent.correction.tick_claim import TickClaimError
from test_tick_claim_consumption_recheck import CASES, decided_session, forged_case

healthy, batch = decided_session()
print('HEALTHY_BATCH_SHA256', batch.batch_id)
print('HEALTHY_FACTS', [(f.edge_id, f.value_u) for f in healthy.consume(batch.batch_id)])
for name, expected in CASES:
    session, batch_id = forged_case(name)
    try:
        facts = session.consume(batch_id)
        print(name, 'ACCEPTED', [(f.edge_id, f.value_u, f.debt_id) for f in facts])
    except TickClaimError as exc:
        print(name, 'REJECTED', exc.code)
        if not baseline:
            assert exc.code == expected, (name, exc.code, expected)
    else:
        if not baseline:
            raise AssertionError((name, 'should have been rejected', expected))
