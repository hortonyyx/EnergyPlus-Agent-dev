"""Metadata-only replay of an existing model; no new model calls or GT input."""
import copy
import json
from pathlib import Path

from src.agent.execution.source_proposal import export_source_proposal
from src.agent.roles import CATALOG, require_role

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'AI_agent/logs/experiments/2026-09-27_sm21_whole_building_repeat_claude_run58/candidate_04'


def run():
    proposal = json.loads((OLD/'proposal.json').read_text())
    before = copy.deepcopy(proposal)
    new = OUT/'sm21'
    report = export_source_proposal(proposal, new, provenance={
        'mode': 'offline naming/catalog replay', 'original_candidate': str(OLD.relative_to(ROOT)),
        'model_calls': 0, 'geometry_edits': 0})
    assert report['source_geometry_ready'], report
    assert before == proposal == json.loads((new/'proposal.json').read_text())
    old = json.loads((OLD/'source_model.json').read_text())
    source = json.loads((new/'source_model.json').read_text())
    keys = ['floors','boundaries','openings','opening_hosts','connections','boundary_relations','unbuilt_openings']
    for key in keys:
        assert old[key] == source[key], key
    assert source['spaces'] == [{**s,'role':require_role(s['role'])} for s in old['spaces']]
    names = source['public_names']
    for key in ['floors','spaces','boundaries','openings']:
        assert set(names[key]) == {o['id'] for o in source[key]}
        assert len(set(names[key].values())) == len(names[key])
    result = {'status':'pass','source_candidate':str(OLD.relative_to(ROOT)),
              'counts':report['counts'], 'unchanged':keys+['space IDs/geometry','raw proposal'],
              'catalog_sha256':source['room_type_catalog']['sha256'],
              'source_sha256':source['source_model_sha256'], 'model_calls':0,'solver_calls':0,
              'scope':'Naming/catalog/display replay, not a fresh reconstruction or drawing audit.'}
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    run()
