"""Check complete repaired GLBs; format support does not certify visual quality."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from src.agent.geometry.mesh_observation import MeshObservation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, default=HERE / 'repaired_buildings')
    args = parser.parse_args()
    paths = sorted(args.input_root.glob('*/input.glb'))
    if not paths:
        raise ValueError(f'No GLBs in {args.input_root}; run review_buildings.py first')
    results = []
    for path in paths:
        try:
            description = MeshObservation(path).describe()
            results.append({'building_id': path.parent.name, 'status': 'pass', 'description': description})
        except ValueError as error:
            results.append({'building_id': path.parent.name, 'status': 'unsupported', 'reason': str(error)})
    report = {'scope': 'format and observation compatibility only, not conversion fidelity or visual quality',
              'checked': len(results), 'passed': sum(r['status'] == 'pass' for r in results), 'results': results}
    (args.input_root / 'compatibility.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
