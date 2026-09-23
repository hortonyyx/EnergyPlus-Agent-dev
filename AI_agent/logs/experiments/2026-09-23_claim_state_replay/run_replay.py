"""Developer replay of run26 state defects; no model calls or fresh observations."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, dump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    run = parser.parse_args().out.resolve()
    original = ROOT/'AI_agent/logs/experiments/2026-09-23_sm24_claim_application_glm_run26'
    run.mkdir(parents=True, exist_ok=False)
    for name in ('images', 'seed', 'candidate_01', 'claims'):
        shutil.copytree(original/name, run/name)
    manifest = json.loads((original/'inputs.json').read_text())
    manifest.update(input_mode='developer_state_replay', provider='offline_no_model',
                    scope='Replay already saved observations; no fresh image interpretation')
    manifest.pop('deadline_epoch', None)
    dump(run/'inputs.json', manifest)
    toolkit = Toolkit(run)
    checks = [{'op': 'update_window', 'id': identity,
               'changes': {'z': {'claim': claim_id, 'value': 'z'}},
               'reason': 'Replay saved GLM conclusion; verify current value without mutation'}
              for identity, claim_id in [('EW1_window', 'claim_0002'), ('EW2_window', 'claim_0003'),
                                         ('EW3_window', 'claim_0003')]]
    toolkit.confirm_claims('seed', json.dumps(checks))
    result = toolkit.revise('candidate_01', json.dumps([{
        'op': 'replace_note', 'field': 'assumptions',
        'old': 'All doors assumed 2.4m height, base 0 (floor level).',
        'replacement': ['ED1_door bottom/head are 0.2/2.6m from the East elevation; other doors retain the inherited 0/2.4m assumption and were not checked in this bounded run.'],
        'reason': 'Saved applied East-door observation supersedes the all-doors base-zero statement only for ED1.',
        'source_refs': ['claim_0001']}]))
    assert result['source_geometry_ready']
    old = json.loads((run/'candidate_01/source_model.json').read_text())
    new = json.loads((run/result['candidate']/'source_model.json').read_text())
    for field in ('spaces', 'boundaries', 'openings', 'connections'):
        assert old[field] == new[field]
    delivery = toolkit.delivery(result['candidate'], selection_origin='developer_state_replay',
        generation_status={'state': 'completed', 'model_calls': 0})
    states = {r['id']: r['state'] for r in delivery['current_claim_state']['claims']}
    assert states == {'claim_0001': 'applied_current', 'claim_0002': 'confirmed_unchanged', 'claim_0003': 'confirmed_unchanged'}
    assert not delivery['adopted_unapplied_claims']
    assert 'The drawing does not label' in (run/'delivery.html').read_text()
    assert len(delivery['current_claim_state']['superseded_notes']) == 1
    dump(run/'summary.json', {'states': states, 'geometry_preserved': True, 'model_calls': 0,
        'method': 'developer structured replay of existing observations and replacement text',
        'independent_observation': False, 'adopted_building_model': False})
    print('Real run26 replay: all three states correct; obsolete note replaced; geometry unchanged.')


if __name__ == '__main__':
    main()
