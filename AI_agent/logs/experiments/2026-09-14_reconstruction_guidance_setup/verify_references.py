"""Verify actual static-reference responses against the frozen implementation."""
import argparse
import ast
import gzip
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
run = parser.parse_args().run.resolve()
assert (run/'summary.json').is_file(), 'wait for generation completion'
source = run/'implementation/scripts/tool_scripts/bim_agent_guidance.py'
tree = ast.parse(source.read_text())
references = ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id == 'REFERENCES' for t in n.targets)))
rows = []
for request in sorted(run.glob('*_request.json')):
    prefix = request.name.removesuffix('_request.json')
    stream = run/f'{prefix}_stream.jsonl'
    opener = open
    if not stream.exists():
        stream = stream.with_suffix('.jsonl.gz')
        opener = gzip.open
    calls = {}
    with opener(stream,'rt') as f:
        for line in f:
            event = json.loads(line)
            for block in event.get('message',{}).get('content',[]):
                if block.get('type') == 'tool_use':
                    calls[block['id']] = block
                if block.get('type') != 'tool_result':
                    continue
                call = calls.get(block.get('tool_use_id'),{})
                if call.get('name','').split('__')[-1] != 'get_bim_reference':
                    continue
                assert not block.get('is_error'), block
                texts = [b['text'] for b in block['content'] if b.get('type') == 'text']
                result = json.loads(texts[0])
                topic = call['input']['topic']
                rows.append({'session':prefix,'topic':topic,
                    'frozen_reference_matches':result['topic']==topic and result['reference']==references[topic]})
report = {'responses':rows,'all_returned_references_match':all(r['frozen_reference_matches'] for r in rows),
          'scope':'Static parameter documentation transport only; no drawing interpretation verdict.'}
(run/'reference_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert report['all_returned_references_match']
print(json.dumps(report,ensure_ascii=False,indent=2))
