"""Read-only live progress and timestamped snapshots; no model calls."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

EXPERIMENT = Path(__file__).resolve().parent
ROOT = EXPERIMENT.parents[3]
sys.path.insert(0, str(ROOT))
from scripts.dev.observe_run import observe_events
from src.harness_contracts import HashedBlobRef
from src.agent_runtime.json_tree import read_json_tree

RUN = Path('D:/EnergyPlus-Agent-worktrees/run-sm25-v53-20261008/AI_agent/archive/local_backup/sm25_v53/sm25_role_v53')
KEY_TOOLS = {'trial_plan_bim', 'submit_plan_reading', 'submit_elevation_reading',
             'assemble_from_readers', 'finish_bim', 'resolve_opening_position',
             'confirm_assembly_review', 'check_bim'}


def result(payload):
    ref = payload.get('raw_result') or {}
    blob = ref.get('blob') or ref
    if blob.get('uri'):
        def read_blob(reference):
            path = (RUN / reference.uri).resolve()
            assert path.is_relative_to(RUN.resolve())
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == reference.sha256
            return data
        value = read_json_tree(HashedBlobRef.model_validate(blob), read_blob)
    else:
        value = ref.get('value', ref)
    if isinstance(value, dict):
        body = value.get('structuredContent')
        if not isinstance(body, dict):
            for part in value.get('content', []):
                if part.get('type') == 'text':
                    try:
                        body = json.loads(part['text'])
                        break
                    except (ValueError, KeyError):
                        pass
        if not isinstance(body, dict):
            body = value
        keys = ('status', 'reason', 'error', 'candidate', 'candidate_id', 'draft_id', 'valid', 'success', 'next_action')
        return {'isError': value.get('isError'), **{k: body[k] for k in keys if k in body}}
    return {'value': str(value)[:300]}


def main():
    events = []
    for line in (RUN / 'events.jsonl').read_text(encoding='utf-8').splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    start = datetime.fromisoformat(events[0]['occurred_at']['value'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    previous_path = EXPERIMENT / 'live_snapshot.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else {}
    cutoff = previous.get('last_event_id', '')
    updates = []
    for event in events:
        if event['event_id'] <= cutoff:
            continue
        payload = event['payload']
        kind = payload.get('event_type')
        tool = payload.get('tool_name')
        if kind in {'model_failure', 'response_truncation'} or kind == 'run_lifecycle' and payload.get('action') == 'stop' or kind == 'tool_execution' and tool in KEY_TOOLS:
            minute = (datetime.fromisoformat(event['occurred_at']['value'].replace('Z', '+00:00')) - start).total_seconds() / 60
            updates.append({'event': event['event_id'], 'min': round(minute, 2), 'task': event['task_id'],
                            'tool': tool, 'outcome': payload.get('outcome'), 'result': result(payload) if kind == 'tool_execution' else str(payload)[:450]})
    observation = observe_events(RUN)
    tasks = [{k: v for k, v in task.items() if k in ('task', 'requests', 'refused', 'output_tokens', 'tools', 'end_min')} for task in observation['tasks']]
    snapshot = {'observed_utc': now.isoformat(), 'elapsed_min': round((now-start).total_seconds()/60, 2),
                'last_event_id': events[-1]['event_id'], 'event_age_seconds': round((now-datetime.fromisoformat(events[-1]['occurred_at']['value'].replace('Z', '+00:00'))).total_seconds(), 1),
                'delivery_file': (RUN/'bim/delivery.json').exists(), 'updates': updates, 'tasks': tasks}
    previous_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    with (EXPERIMENT/'live_snapshots.jsonl').open('a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False)+'\n')
    print(json.dumps(snapshot, ensure_ascii=False))


if __name__ == '__main__':
    main()
