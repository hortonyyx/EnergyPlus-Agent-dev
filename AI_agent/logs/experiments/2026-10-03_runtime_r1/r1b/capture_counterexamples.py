"""Rebuild R1b counterexamples from the original GLM response, fully offline."""

from pathlib import Path
import hashlib, json, tarfile, tempfile
import test_runtime_r1b_budget as checks
Path('.r1b-work').mkdir(exist_ok=True)
base = Path(tempfile.mkdtemp(prefix='counterexamples-', dir='.r1b-work'))
for limit, reason, exceeded in [(100, None, False), (54, 'token_budget_exhausted', True)]:
    for allowance in (0, 32):
        case = base / f'root-{limit}-margin-{allowance}'
        case.mkdir()
        checks.test_glm_overrun_request_evidence_and_recovery_are_durable(case, limit, reason, exceeded, allowance)
child = base / 'child-isolation'
child.mkdir()
checks.test_child_overrun_stops_child_while_root_charges_actual_and_sibling_continues(child)
late = base / 'late-response'
late.mkdir()
checks.test_token_and_time_overrun_preserves_full_tokens_and_time_violation_on_resume(late)
rows = []
for events in sorted(base.rglob('events.jsonl')):
    records = [json.loads(line) for line in events.read_bytes().splitlines()]
    settlements = [e['payload']['settlement'] for e in records if e['payload']['event_type'] == 'budget' and e['payload']['action'] == 'settle']
    overruns = [e['payload'] for e in records if e['payload']['event_type'] == 'budget_overrun']
    if not settlements:
        continue
    assert sum(s['actual']['tokens'] for s in settlements) == 55
    assert len(settlements) == len(overruns) == 1
    rows.append({'case': str(events.relative_to(base)), 'events_sha256': hashlib.sha256(events.read_bytes()).hexdigest(), 'charged_tokens':55, 'settlements':settlements, 'overruns':overruns})
assert len(rows) == 6
out = Path('AI_agent/logs/experiments/2026-10-03_runtime_r1/r1b')
archive = out / 'counterexamples.tar.xz'
with tarfile.open(archive, 'w:xz') as tar:
    tar.add(base, arcname='counterexamples')
report = {'status':'passed','source':'R1 glm_calibration/responses.json rows[0] (original request/response)','original_reservation':54,'actual_tokens':55,'cases':rows,'recovery':'Every root and late-response case reopens its EventStore and re-settles without duplicating charge/overrun; child case reconstructs root/child ledgers and admits sibling.', 'new_allowance_cases':'Allowance 32 paired with legacy reservation 54 is explicit offline under-reservation fault injection, not a historical live run.', 'archive':archive.name, 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'real_provider_calls':0}
(out / 'counterexamples.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print({'cases':len(rows),'archive_bytes':archive.stat().st_size,'status':'passed'})
