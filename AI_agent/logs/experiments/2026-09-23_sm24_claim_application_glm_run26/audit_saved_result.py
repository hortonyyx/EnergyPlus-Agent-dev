"""Post-run source comparison; never part of the generation input."""
import hashlib
import json
from pathlib import Path


def main():
    run = Path(__file__).resolve().parent
    load = lambda name: json.loads((run / name).read_text())
    seed, candidate = load('seed/source_model.json'), load('candidate_01/source_model.json')
    before, after = load('seed/proposal.json'), load('candidate_01/proposal.json')
    for field in ('spaces', 'boundaries', 'connections'):
        assert seed[field] == candidate[field], field
    old_openings = {o['id']: o for o in seed['openings']}
    new_openings = {o['id']: o for o in candidate['openings']}
    assert old_openings.keys() == new_openings.keys()
    changed = [key for key in old_openings if old_openings[key] != new_openings[key]]
    assert changed == ['ED1_door'], changed
    assert sorted({v[2] for v in old_openings['ED1_door']['vertices']}) == [0, 2.4]
    assert sorted({v[2] for v in new_openings['ED1_door']['vertices']}) == [.2, 2.6]
    for kind in ('floors', 'windows'):
        assert before['geometry'][kind] == after['geometry'][kind]
    old = next(o for o in before['geometry']['openings'] if o['id'] == 'ED1_door')
    new = next(o for o in after['geometry']['openings'] if o['id'] == 'ED1_door')
    for key in old.keys() | new.keys():
        if key not in {'z', 'source_refs'}:
            assert old.get(key) == new.get(key), key
    application = load('claims/application_0001.json')
    assert application['status'] == 'applied'
    assert application['parameters_without_claims'] == []
    assert application['outside_declared_scope'] == []
    assert application['evidence']['bindings'][0]['resolved_value'] == [.2, 2.6]
    for source in load('claims/claim_0001.json')['sources']:
        assert source['sha256'] == hashlib.sha256((run / 'images' / source['image']).read_bytes()).hexdigest()
    receipt = load('agent_receipt.json')
    assert receipt['requested_model'] == receipt['actual_model'] == 'glm-5.3-flash'
    result = {'scope': 'post-run East vertical extent and edit isolation check; not whole-building evaluation',
        'ground_truth_used': False, 'original_elevation_inspected_by_developer': True,
        'source_check': 'pass', 'changed_source_opening_ids': changed,
        'old_door_z': [0, 2.4], 'new_door_z': [.2, 2.6],
        'spaces_boundaries_connections_and_other_openings_preserved': True,
        'computed_claim_value_applied': True, 'profile_refs_used_as_edit_parameters': False,
        'known_limitations': ['Inherited all-doors-base-zero assumption text was not updated.',
            'Confirmed unchanged windows remain adopted-unapplied claims; this does not imply failed edits.',
            'Developer selected facade and seed; not autonomous task selection or cold-start reconstruction.',
            'Other facades/interior partitions not evaluated; this is not a new adopted whole-building baseline.']}
    (run / 'postrun_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
