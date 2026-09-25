"""Developer-only check of historical source identities, never generation input."""
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.geometry.source_space_relations import review_space_relations

HERE = Path(__file__).resolve().parent
PAIRS = [{'id': 'historical_continuous_space', 'points': [[745,900],[745,1000]],
          'expected': 'same_space',
          'evidence': 'Developer historical audit of the original continuous floor-plan region.'}]


def main():
    reports = {}
    for name, candidate in [('2026-09-24_sm25_continuous_space_glm_run44', 'candidate_03'),
                            ('2026-09-24_sm25_partition_feedback_glm_run45', 'candidate_01')]:
        run = HERE.parent / name
        source_path = run / candidate / 'source_model.json'
        source = json.loads(source_path.read_text())
        calibration_path = sorted((run / 'overlay_calibrations').glob('*.json'))[-1]
        calibration = json.loads(calibration_path.read_text())
        manifest = json.loads((run / 'inputs.json').read_text())
        image = calibration['image']
        report = review_space_relations(source, floor_id='F1',
            image_size=manifest['images'][image]['size'],
            x_anchors=calibration['x_anchors'], y_anchors=calibration['y_anchors'], observations=PAIRS)
        reports[name] = dict(source_file=str(source_path), source_file_sha256=digest(source_path),
            calibration_file=str(calibration_path), calibration_sha256=digest(calibration_path),
            report=report)
    assert reports['2026-09-24_sm25_continuous_space_glm_run44']['report']['conflict_count'] == 1
    assert reports['2026-09-24_sm25_partition_feedback_glm_run45']['report']['conflict_count'] == 0
    target = HERE / 'developer_replay.json'
    assert not target.exists()
    dump(target, {'mode': 'developer_only_historical_replay_not_model_generation', 'reports': reports})
    print({name: row['report']['observations'][0]['actual_relation'] for name, row in reports.items()})


if __name__ == '__main__':
    main()
