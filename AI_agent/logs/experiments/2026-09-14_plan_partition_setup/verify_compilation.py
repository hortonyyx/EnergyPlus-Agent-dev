"""Post-run replay of original pixel declarations, compilation and transport."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.plan_partition import compile_plan_partition
from scripts.tool_scripts.run_bim_agent import dump, digest

read = lambda path: json.loads(path.read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    assert (run / 'summary.json').exists(), 'Generation must finish first'
    manifest = read(run / 'inputs.json')
    rows = []
    for folder in sorted((run / 'plan_drafts').glob('draft_*')):
        declared = read(folder / 'input.json')
        result = read(folder / 'result.json')
        checks = {
            'raw_plan_hash_matches': digest(folder / 'plan.json') == declared['plan_sha256'],
            'original_image_hash_matches': digest(run / 'images' / declared['image']) == declared['image_sha256'],
        }
        try:
            proposal, metadata = compile_plan_partition(read(folder / 'plan.json'),
                image_size=tuple(manifest['images'][declared['image']]['size']),
                image_name=declared['image'])
        except (ValueError, TypeError, KeyError) as error:
            checks['same_compilation_error'] = result.get('error') == str(error)
            checks['no_candidate_on_compile_error'] = not result.get('candidate')
        else:
            checks['same_compilation_metadata'] = metadata == read(folder / 'compilation.json')
            candidate = result.get('candidate')
            if candidate:
                checks['same_generated_proposal'] = proposal == read(run / candidate / 'proposal.json')
                source = read(run / candidate / 'source_model.json')
                bound = source['generation']['provenance']['plan_input']
                checks['source_binds_raw_plan'] = bound['plan_sha256'] == declared['plan_sha256']
                checks['source_binds_mapping'] = bound['compilation_sha256'] == digest(folder / 'compilation.json')
            else:
                checks['explicit_candidate_budget_error'] = 'budget exhausted' in result.get('error', '')
        rows.append({'draft': folder.name, 'candidate': result.get('candidate'),
                     'error': result.get('error'), 'checks': checks})
    calls, actual_declarations = {}, []
    stream_path = run / 'agent_stream.jsonl'
    open_stream = open
    if not stream_path.exists():
        stream_path = stream_path.with_suffix('.jsonl.gz')
        open_stream = gzip.open
    with open_stream(stream_path, 'rt') as stream:
        for line in stream:
            event = json.loads(line)
            for block in event.get('message', {}).get('content', []):
                if block.get('type') == 'tool_use':
                    calls[block['id']] = block
                    if block['name'].split('__')[-1] == 'build_plan_bim':
                        args = block['input']
                        actual_declarations.append({
                            'image': args['image'],
                            'plan_sha256': hashlib.sha256(args['plan_json'].encode()).hexdigest(),
                        })
    persisted_declarations = [read(folder / 'input.json') for folder in sorted((run / 'plan_drafts').glob('draft_*'))]
    transport = actual_declarations == [{k: row[k] for k in ('image', 'plan_sha256')}
                                        for row in persisted_declarations]
    events = [json.loads(line) for line in (run / 'tools.jsonl').read_text().splitlines()]
    builds = [{'candidate': event['data'].get('candidate'),
               'source_geometry_ready': event['data'].get('source_geometry_ready'),
               'error': event['data'].get('error'),
               'seconds_after_first_tool': event['time'] - events[0]['time']}
              for event in events if event['action'] in {'build_plan_bim', 'build_bim', 'revise_bim'}]
    result = {'drafts': rows, 'actual_model_declarations_match_persisted': transport,
              'all_replays_match': bool(rows) and all(all(row['checks'].values()) for row in rows),
              'builds': builds, 'limits': 'Deterministic replay and input transport only; not visual fidelity.'}
    dump(run / 'compilation_verification.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert transport and result['all_replays_match'], result
