"""Read-only historical audit; write findings only in this new experiment."""
from collections import Counter
import importlib
import json
from pathlib import Path
import subprocess
import tempfile

from scripts.tool_scripts.run_bim_agent import dump, digest
from src.agent.execution.source_proposal import export_source_proposal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
load = lambda p: json.loads(p.read_text())
RUNS = ['2026-09-27_sm21_whole_building_repeat_claude_run58',
        '2026-09-27_sm21_current_tools_claude_run69']
PHYSICAL = ['floors', 'boundaries', 'openings', 'opening_hosts', 'connections',
            'boundary_relations', 'unbuilt_openings']
SPACE_GEOMETRY = ['id', 'floor_id', 'polygon', 'z_floor', 'height']


def main():
    reports = []
    for name in RUNS:
        run = HERE.parent / name
        manifest = load(run / 'inputs.json')
        request = load(run / 'agent_request.json')
        actions = [json.loads(l) for l in (run / 'tools.jsonl').read_text().splitlines()]
        candidates = []
        for file in sorted(run.glob('candidate_*/source_model.json')):
            source = load(file)
            proposal = load(file.parent / 'proposal.json')
            with tempfile.TemporaryDirectory(prefix='bim-regression-replay-') as tmp:
                target = Path(tmp) / 'candidate'
                report = export_source_proposal(proposal, target,
                    provenance=source['generation']['provenance'])
                assert report['source_geometry_ready']
                replay = load(target / 'source_model.json')
                for key in PHYSICAL:
                    assert source[key] == replay[key], (name, file.parent.name, key)
                geometry = lambda obj: [{k:s[k] for k in SPACE_GEOMETRY} for s in obj['spaces']]
                assert geometry(source) == geometry(replay)
                assert load(file.parent / 'proposal.json') == proposal
            candidates.append(dict(candidate=file.parent.name, physical_replay_exact=True,
                source_sha256=source['source_model_sha256']))
        start = actions[0]['time']
        reports.append(dict(run=name, candidates=candidates,
            tools=dict(Counter(r['action'] for r in actions)),
            event_sequence=[dict(action=r['action'], seconds=round(r['time']-start, 2),
                candidate=r['data'].get('candidate'), topic=r['data'].get('topic'))
                for r in actions if r['action'] not in {'view_image', 'pixel_profile','view_pixel_profile'}],
            primary_elapsed=load(run / 'agent_receipt.json')['elapsed_seconds'],
            image_hashes={k:v['sha256'] for k,v in manifest['images'].items()},
            scope=manifest['scope'], primary_user_prompt=request['prompt'],
            guide_characters=len(request['system_prompt']),
            continuation_rounds=manifest.get('continuation_rounds',0)))
    assert reports[0]['scope'] == reports[1]['scope']
    assert reports[0]['primary_user_prompt'] == reports[1]['primary_user_prompt']
    assert reports[0]['image_hashes'] == reports[1]['image_hashes']
    core = ['plan_partition.py','plan_assembly.py','plan_revision.py','dimension_chain.py',
            'source_image_overlay.py','source_elevation_view.py','source_space_relations.py']
    changed = subprocess.check_output(['git','diff','--name-only','468d83f7..HEAD','--',
        *['src/agent/geometry/'+p for p in core]],cwd=ROOT,text=True).strip()
    assert not changed, changed
    dump(HERE / 'historical_replay.json', dict(runs=reports,
        same_images_scope_primary_prompt=True, unchanged_core=core,
        physical_replays=sum(len(r['candidates']) for r in reports),
        limits=['Exact replay checks calculation for saved declarations, not their image interpretation.',
                'Naming and role/evidence metadata may differ; all physical fields checked exactly.',
                'Errors precede continuation and first height claim; no causal attribution to guidance established.']))
    print('Physical candidate replays:', sum(len(r['candidates']) for r in reports))


if __name__ == '__main__':
    main()
