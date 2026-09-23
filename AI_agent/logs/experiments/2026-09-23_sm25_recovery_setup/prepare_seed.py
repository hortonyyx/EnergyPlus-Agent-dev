"""Explicit legacy adapter for this historical candidate; no geometry repair or GT."""
import copy
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.execution.source_proposal import export_source_proposal

ROOT = Path(__file__).resolve().parents[4]
OLD = ROOT / 'AI_agent/logs/experiments/2026-09-09_m0_wall_gap_review_run01/1_correction/attempts/001/output.json'
SOURCE = ROOT / 'AI_agent/logs/experiments/2026-09-09_source_bim_run04/sm25/source_model.json'
OUT = Path(__file__).resolve().parent


def prepare(out):
    geometry = json.loads(OLD.read_text())
    geometry['schema_version'] = '2'
    # These carry the old v3 authority/proof, which this editable adapter does not claim.
    geometry.pop('deterministic_core_stamp')
    geometry.pop('facade_segments')
    proposal = {'geometry': geometry, 'assumptions': [
        'Historical assisted correction imported as an editable proposal; not cold start. Existing representative wall planes and 2.1 m assumed door heights are retained.'],
        'unresolved': [
        'Two historical positive opening observations near the second-floor northern corridor junction remain unbuilt; their number does not establish the number of physical doors. See geometry.unsupported for exact records.',
        'Whole-building drawing fidelity, door heights/states and room roles remain unverified.']}
    return export_source_proposal(proposal, out, provenance={
        'mode': 'historical_assisted_correction_import', 'input': str(OLD.relative_to(ROOT)),
        'input_sha256': digest(OLD), 'original_source_sha256': digest(SOURCE)})


def audit(out, audit_path=None):
    old, new = (json.loads(p.read_text()) for p in (SOURCE, out / 'source_model.json'))
    same = {k: old[k] == new[k] for k in ('spaces', 'floors', 'boundaries', 'connections', 'unsupported')}
    assert all(same.values())
    old_openings = {o['id']: o for o in old['openings']}
    assert set(old_openings) == {o['id'] for o in new['openings']}
    max_error = 0.0
    for row in new['openings']:
        before = copy.deepcopy(old_openings[row['id']]); after = copy.deepcopy(row)
        a, b = sorted(before.pop('vertices')), sorted(after.pop('vertices'))
        assert before == after
        max_error = max(max_error, *(abs(x-y) for p,q in zip(a,b) for x,y in zip(p,q)))
    assert max_error < 1e-12
    result = {'mode': 'historical_assisted_recovery_adapter', 'input_sha256': digest(OLD),
        'original_source_sha256': digest(SOURCE), 'unchanged': same, 'all_opening_ids_and_semantics_preserved': True,
        'max_opening_vertex_difference_m': max_error,
        'vertex_order_note': 'Legacy cardinal projection can rotate vertex start index; vertex sets are preserved within floating arithmetic.',
        'two_unbuilt_observations_preserved': len(new['unsupported']) == 2,
        'model_calls': 0, 'gt_used': False}
    dump(audit_path or out / 'adapter_audit.json', result)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.out:
        print(prepare(args.out))
        print(audit(args.out))
    else:
        print(audit(OUT / 'seed', OUT / 'adapter_audit.json'))
