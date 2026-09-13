"""Post-run source differences and deterministic replay, without GT/model calls."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from shapely.geometry import Polygon
from shapely.ops import unary_union
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.proposal_edits import apply_proposal_edits

read = lambda p: json.loads(p.read_text())
keyed = lambda rows: {row['id']: row for row in rows}

def physical_opening(row):
    return {key: row.get(key) for key in
            ('kind', 'vertices', 'space_ids', 'exterior', 'connectivity')}

def dimensions(row):
    v = row['vertices']
    xs, ys, zs = zip(*v)
    return {'width_m': ((max(xs)-min(xs))**2 + (max(ys)-min(ys))**2)**.5,
            'height_m': max(zs)-min(zs)}

def main(run):
    summary = read(run/'summary.json')  # Never audit an active run.
    selected = summary['delivery']['candidate']
    before, after = [read(run/name/'source_model.json') for name in ('seed', selected)]
    old_spaces, new_spaces = keyed(before['spaces']), keyed(after['spaces'])
    old_openings, new_openings = keyed(before['openings']), keyed(after['openings'])
    old_connections, new_connections = [
        {row['opening_id']: row for row in source['connections']} for source in (before, after)]
    common = old_openings.keys() & new_openings.keys()
    changed_openings = {k: {'before': physical_opening(old_openings[k]),
                            'after': physical_opening(new_openings[k]),
                            'before_dimensions': dimensions(old_openings[k]),
                            'after_dimensions': dimensions(new_openings[k])}
                        for k in sorted(common)
                        if physical_opening(old_openings[k]) != physical_opening(new_openings[k])}
    changed_spaces = {k: {'before': old_spaces[k]['polygon'], 'after': new_spaces[k]['polygon']}
                      for k in sorted(old_spaces.keys() & new_spaces.keys())
                      if not Polygon(old_spaces[k]['polygon']).equals(Polygon(new_spaces[k]['polygon']))}
    old_union = unary_union([Polygon(s['polygon']) for s in before['spaces']])
    new_union = unary_union([Polygon(s['polygon']) for s in after['spaces']])
    replay = []
    for path in sorted(run.glob('candidate_*/proposal.json')):
        candidate = path.parent
        report = read(candidate/'report.json')
        provenance = report['provenance']
        proposal = read(path)
        operations_path = candidate/'operations.json'
        row = {'candidate': candidate.name}
        if operations_path.exists():
            record = read(operations_path)
            parent = provenance['parent_candidate']
            rebuilt = apply_proposal_edits(read(run/parent/'proposal.json'), record)
            row['operations_reproduce_proposal'] = rebuilt == proposal
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/'reexport'
            export_source_proposal(proposal, output, provenance=provenance)
            row['source_reexport_sha256_matches'] = (
                read(output/'source_model.json')['source_model_sha256'] ==
                read(candidate/'source_model.json')['source_model_sha256'])
        replay.append(row)
    checks = {
        'space_ids_preserved': old_spaces.keys() == new_spaces.keys(),
        'opening_ids_preserved': old_openings.keys() == new_openings.keys(),
        'connection_ids_preserved': old_connections.keys() == new_connections.keys(),
        'whole_floor_coverage_preserved': old_union.symmetric_difference(new_union).area < 1e-9,
        'space_overlap_absent': sum(Polygon(s['polygon']).area for s in after['spaces'])-new_union.area < 1e-9,
        'window_geometry_and_space_ids_preserved': all(
            k in new_openings and physical_opening(o) == physical_opening(new_openings[k])
            for k, o in old_openings.items() if o['kind'] == 'window'),
        'exterior_openings_preserved': all(
            k in new_openings and physical_opening(o) == physical_opening(new_openings[k])
            for k, o in old_openings.items() if o.get('exterior')),
        'no_unbuilt_openings': not after['unbuilt_openings'],
        'all_operation_and_source_replays_match': all(all(v for k,v in row.items() if k != 'candidate') for row in replay),
    }
    result = {'selected': selected, 'checks': checks,
              'changed_spaces': changed_spaces, 'changed_openings': changed_openings,
              'opening_dimensions_changed': [k for k in sorted(common) if any(
                  abs(dimensions(old_openings[k])[axis]-dimensions(new_openings[k])[axis]) > 1e-6
                  for axis in ('width_m','height_m'))],
              'whole_floor_symmetric_difference_m2': old_union.symmetric_difference(new_union).area,
              'replay': replay,
              'limits': 'Source preservation and deterministic replay only. No image fidelity verdict; explicit opening dimension changes require image review.'}
    (run/'source_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'checks':checks,'changed_spaces':list(changed_spaces),
                      'changed_openings':list(changed_openings),
                      'opening_dimensions_changed':result['opening_dimensions_changed']},indent=2))
    assert all(checks.values()), checks

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    main(parser.parse_args().run.resolve())
