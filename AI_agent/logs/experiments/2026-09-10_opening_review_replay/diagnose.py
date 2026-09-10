"""Reconcile historical developer observations; never input to the cold start."""
import hashlib
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.opening_review import review_openings


def main():
    observations = json.loads((RUN / 'observations.json').read_text())
    reports = {}
    for label, directory in [('before', '2026-09-10_bim_agent_sm21_run04'),
                             ('after', '2026-09-10_bim_agent_sm21_run05')]:
        previous = RUN.parent / directory
        source = json.loads((previous / 'candidate_01/source_model.json').read_text())
        images = json.loads((previous / 'inputs.json').read_text())['images']
        report = review_openings(source, observations, images)
        report['diagnostic_mode'] = 'historical_developer_observations_replayed_offline'
        report['source_path'] = str((previous / 'candidate_01/source_model.json').relative_to(ROOT))
        report['observations_sha256'] = hashlib.sha256((RUN / 'observations.json').read_bytes()).hexdigest()
        (RUN / f'{label}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        reports[label] = report
    assert {x['opening_id'] for x in reports['before']['findings'] if x['code'] == 'unaccounted_model_opening'} == {'D_F1_N2_Cb', 'D_F1_S2_Cb'}
    assert not reports['after']['findings']
    assert all(r['drawing_fidelity'] == 'not_evaluated' for r in reports.values())
    print(json.dumps({key: {'conclusion':r['conclusion'], 'findings':r['findings']} for key,r in reports.items()}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
