"""Audit a completed saved-candidate recovery without changing its artifacts."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

def read(path):
    return json.loads(path.read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fields(before, after):
    return {k: {'before': before.get(k), 'after': after.get(k)}
            for k in sorted(before.keys() | after.keys()) if before.get(k) != after.get(k)}

def objects(before, after, key='id'):
    old, new = ({item[key]: item for item in items} for items in (before, after))
    return {'added': [new[k] for k in sorted(new.keys() - old.keys())],
            'removed': [old[k] for k in sorted(old.keys() - new.keys())],
            'updated': {k: fields(old[k], new[k]) for k in sorted(old.keys() & new.keys()) if old[k] != new[k]}}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
args = parser.parse_args()
run = args.run.resolve()
summary, manifest = read(run / 'summary.json'), read(run / 'inputs.json')
checks = {}
for name, record in manifest['images'].items():
    checks[f'image:{name}'] = digest(run / 'images' / name) == record['sha256']
for name, expected in manifest['implementation_sha256'].items():
    checks[f'implementation:{name}'] = digest(ROOT / name) == expected
checks['seed_proposal'] = digest(Path(manifest['seed']['source']) / 'proposal.json') == manifest['seed']['proposal_sha256']
seed = read(run / 'seed' / 'proposal.json')
final = read(run / summary['delivery']['candidate'] / 'proposal.json')
a, b = seed['geometry'], final['geometry']
rows = [json.loads(line) for line in (run / 'tools.jsonl').read_text().splitlines()]
details = []
for path in sorted(run.glob('detail_*/inputs.json')):
    child = path.parent
    local = read(path)
    receipt = read(run / f'{child.name}_receipt.json')
    source = receipt['observation_source']
    checks[f'{child.name}:manifest'] = digest(path) == source['input_sha256']
    checks[f'{child.name}:question'] = digest(child / 'question.txt') == local['question_sha256']
    checks[f'{child.name}:selected_image_inventory'] = set(local['images']) == set(source['images'])
    checks[f'{child.name}:no_parent_context_fields'] = not any(k in local for k in ('seed', 'scope', 'evaluation'))
    for name, record in local['images'].items():
        checks[f'{child.name}:image:{name}'] = digest(child / 'images' / name) == record['sha256'] == source['images'][name]
    details.append({'run': child.name, 'images': list(local['images']),
                    'question': (child / 'question.txt').read_text(),
                    'actual_model': receipt.get('actual_model'), 'elapsed_seconds': receipt.get('elapsed_seconds'),
                    'question_independence': 'requires semantic inspection; file hashes do not prove an unbiased question'})
result = {'checks': checks, 'selected_candidate': summary['delivery']['candidate'],
          'tool_actions': dict(Counter(row['action'] for row in rows)),
          'floors_equal': a['floors'] == b['floors'],
          'floor_changes': objects(a['floors'], b['floors'], 'name'),
          'footprint_equal': all(a[k] == b[k] for k in ('footprint_x', 'footprint_y')),
          'geometry_changes': {k: objects(a.get(k, []), b.get(k, [])) for k in ('windows', 'openings')},
          'prose_changes': fields({k:v for k,v in seed.items() if k != 'geometry'},
                                 {k:v for k,v in final.items() if k != 'geometry'}),
          'local_observations': details}
assert all(checks.values()), checks
out = run / 'artifact_verification.json'
with out.open('x') as stream:
    stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'all_hash_checks_passed': True, 'selected_candidate': result['selected_candidate'],
                  'tool_actions': result['tool_actions'], 'floors_equal': result['floors_equal'],
                  'local_observations': len(details)}, ensure_ascii=False, indent=2))
