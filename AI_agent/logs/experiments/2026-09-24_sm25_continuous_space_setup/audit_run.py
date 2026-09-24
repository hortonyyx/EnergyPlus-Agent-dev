"""Reuse the existing independent recovery audit with this run's frozen inputs."""
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump


def compare_recovery(run, previous=None):
    load = lambda p: json.loads(p.read_text())
    previous = previous or run.parent / '2026-09-24_sm25_local_plan_glm_run43/candidate_02'
    selected = load(run / 'delivery.json')['candidate']
    old, new = load(previous / 'source_model.json'), load(run / selected / 'source_model.json')
    new_spaces = {s['id']:s for s in new['spaces']}
    old_openings = {o['id']:o for o in old['openings']}
    new_openings = {o['id']:o for o in new['openings']}
    unchanged_rooms = [s['id'] for s in old['spaces']
        if s['id'] in new_spaces and new_spaces[s['id']]['polygon'] == s['polygon']]
    real_openings = {k:v for k,v in old_openings.items() if v['kind'] in ('door','window')}
    preserved = [k for k,v in real_openings.items() if k in new_openings and
        v['vertices'] == new_openings[k]['vertices'] and v['kind'] == new_openings[k]['kind']]
    original = load(run / 'evaluation/original_comparison.json')
    gt = load(run / 'evaluation/gt_partition.json')
    topology_codes = {'source_space_split','source_spaces_merged','extra_source_space','missing_source_space'}
    checks = {'original':original['comparison'], **gt['comparisons']}
    result = dict(previous_candidate=str(previous), selected_candidate=selected,
        old_spaces=len(old['spaces']), new_spaces=len(new['spaces']),
        unchanged_room_polygons=unchanged_rooms,
        preserved_original_door_window_geometry=preserved,
        missing_or_changed_original_door_window_geometry=sorted(real_openings.keys()-set(preserved)),
        removed_openings=sorted(old_openings.keys()-new_openings.keys()),
        new_openings=sorted(new_openings.keys()-old_openings.keys()),
        topology_findings={name:[f for f in data['findings'] if f['code'] in topology_codes]
            for name,data in checks.items()},
        note='Independent after-generation comparison; no expected count or geometry supplied to the model.')
    dump(run / 'evaluation/recovery_delta.json', result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    audit = importlib.import_module('AI_agent.logs.experiments.2026-09-24_sm25_local_plan_setup.audit_run')
    audit.HERE = Path(__file__).resolve().parent
    audit.RUN = audit.HERE.parent / '2026-09-24_sm25_continuous_space_glm_run44'
    audit.main()
    compare_recovery(audit.RUN)
