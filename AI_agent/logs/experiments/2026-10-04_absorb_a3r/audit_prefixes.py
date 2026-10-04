"""Offline, byte-verified inspection of archived native Messages requests."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from pydantic import TypeAdapter
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts.events import CapturedValue

HERE = Path(__file__).resolve().parent
STATE = 'Current runtime state (machine generated; epistemic status is authoritative): '

class Reader(EventStore):
    def __init__(self, directory):
        self.directory = directory
        self.cache = {}
    def get_bytes(self, ref):
        if ref.uri not in self.cache:
            self.cache[ref.uri] = (self.directory / ref.uri).read_bytes()
        raw = self.cache[ref.uri]
        if hashlib.sha256(raw).hexdigest() != ref.sha256:
            raise ValueError('archived blob hash mismatch')
        return raw

def marks(value, path=''):
    found = []
    if isinstance(value, dict):
        if 'cache_control' in value:
            found.append({'path': path, 'type': value.get('type'), 'value': value['cache_control']})
        for key, child in value.items():
            found.extend(marks(child, path + '/' + key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(marks(child, path + '/' + str(i)))
    return found

def content_units(body, *, strip_cache=False, strip_tail=True):
    # Compare native blocks including their roles; adjacent user messages may merge.
    units = [(m['role'], copy.deepcopy(b)) for m in body['messages'] for b in m['content']]
    if strip_tail and units and units[-1][1].get('type') == 'text' and units[-1][1].get('text', '').startswith(STATE):
        units.pop()
    if strip_cache:
        for _, block in units:
            block.pop('cache_control', None)
    return units

def prefix_result(previous, current, strip_cache=False):
    left = content_units(previous, strip_cache=strip_cache)
    right = content_units(current, strip_cache=strip_cache)
    matched = 0
    for a, b in zip(left, right):
        if json_bytes(a) != json_bytes(b):
            break
        matched += 1
    result = {'prefix': matched == len(left), 'previous_blocks': len(left), 'matching_blocks': matched}
    if not result['prefix']:
        result['first_difference'] = {'previous_type': left[matched][1].get('type'),
            'current_type': right[matched][1].get('type') if matched < len(right) else 'absent',
            'previous_sha256': hashlib.sha256(json_bytes(left[matched])).hexdigest(),
            'current_sha256': hashlib.sha256(json_bytes(right[matched])).hexdigest() if matched < len(right) else None}
    return result

def load_run(path):
    reader = Reader(path)
    adapter = TypeAdapter(CapturedValue)
    events = [json.loads(line) for line in (path/'events.jsonl').read_bytes().splitlines()]
    requests, responses = [], {}
    for e in events:
        p = e['payload']
        if p['event_type'] == 'adapter_request':
            wire = reader.capture_bytes(adapter.validate_json(json.dumps(p['final_request_body'])))
            assert hashlib.sha256(wire).hexdigest() == p['wire_sha256']
            requests.append((e, json.loads(wire)))
        elif p['event_type'] == 'model_response':
            raw = reader.resolve(adapter.validate_json(json.dumps(p['raw_response'])))
            responses[p['request_event_id']] = raw
    return requests, responses, events

def audit_run(path):
    requests, responses, events = load_run(path)
    rows = []
    for i, (event, body) in enumerate(requests):
        response = responses.get(event['event_id'], {})
        usage = response.get('usage', {})
        row = {'step': i+1, 'event_id': event['event_id'], 'timestamp': event['occurred_at'],
            'wire_sha256': event['payload']['wire_sha256'], 'wire_bytes': len(json_bytes(body)),
            'usage': usage, 'cache_marks': marks(body),
            'thinking_blocks': sum(b.get('type') in {'thinking','redacted_thinking'} for _, b in content_units(body)),
            'message_blocks': len(content_units(body))}
        originals = [responses[e['event_id']].get('content', []) for e, _ in requests[:i]]
        retained = [m['content'] for m in body['messages'] if m['role'] == 'assistant']
        row['all_retained_assistant_blocks_exact'] = all(any(json_bytes(m) == json_bytes(x) for x in originals) for m in retained)
        if i:
            prev_e, prev = requests[i-1]
            row['exact_except_state_tail'] = prefix_result(prev, body)
            row['content_except_state_and_cache'] = prefix_result(prev, body, True)
            row['static_fields_equal'] = all(json_bytes(prev.get(k)) == json_bytes(body.get(k)) for k in set(body)|set(prev) if k != 'messages')
            prior_response = responses[prev_e['event_id']]
            sent = [b for m in body['messages'] if m['role'] == 'assistant' for b in m['content']]
            thought = [b for b in prior_response.get('content', []) if b['type'] in {'thinking','redacted_thinking'}]
            row['prior_thinking_count'] = len(thought)
            row['prior_thinking_replayed_exactly'] = all(any(json_bytes(b)==json_bytes(x) for x in sent) for b in thought)
            between = [x for x in events if prev_e['sequence'] < x['sequence'] <= event['sequence']]
            row['context_events'] = [{'event_id':x['event_id'],'payload':x['payload']} for x in between if x['payload']['event_type'] == 'context']
            row['explicit_compaction'] = any(x['payload']['action']=='compact' for x in row['context_events'])
        rows.append(row)
    summary = {'requests_reconstructed': len(rows),
        'exact_prefix_pairs':sum(r.get('exact_except_state_tail',{}).get('prefix',False) for r in rows),
        'content_prefix_pairs':sum(r.get('content_except_state_and_cache',{}).get('prefix',False) for r in rows),
        'thinking_replay_pairs':sum(r.get('prior_thinking_replayed_exactly',False) for r in rows),
        'static_equal_pairs':sum(r.get('static_fields_equal',False) for r in rows)}
    summary['compaction_steps'] = [r['step'] for r in rows if r.get('explicit_compaction')]
    summary['unexplained_content_break_steps'] = [r['step'] for r in rows[1:] if not r['content_except_state_and_cache']['prefix'] and not r['explicit_compaction']]
    summary['all_retained_assistant_blocks_exact'] = all(r['all_retained_assistant_blocks_exact'] for r in rows)
    return {'summary':summary, 'rows':rows}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('scratch',type=Path); args=parser.parse_args()
    out = {'method':__doc__, 'model_requests':0, 'runs':{}}
    for name in ('sm24','sm25'):
        path=args.scratch/(name+'_runtime_anthropic')
        out['runs'][name]=audit_run(path)
        print(name, out['runs'][name]['summary'], flush=True)
    captures=HERE.parent/'2026-10-03_migration_comparison/evidence/claude_code_request_capture'
    out['claude_code']={}
    for p in captures.glob('*.json'):
        body=json.loads(p.read_bytes())['body']
        out['claude_code'][p.name]={'file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'cache_marks':marks(body),'stream':body.get('stream'),'metadata_present':bool(body.get('metadata'))}
    (HERE/'prefix_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__': main()
