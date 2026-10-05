"""Verify historical diagnostic equality and report presentation-only changes."""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def main():
    before, after = [load(HERE / (s + '.json')) for s in ('before', 'after')]
    assert before['revision']['source_sha256'] == after['revision']['source_sha256']
    assert before['revision']['images'] == after['revision']['images']
    b, a = [load(HERE / 'replies' / f'revise_bim_{s}_full.json') for s in ('before', 'after')]
    a.pop('saved_candidate')
    a.pop('save_effects')
    a['building_precision'].pop('changes')
    assert a == b, 'revision diagnostics or applied geometry changed'
    assert len(before['profiles']) == len(after['profiles']) == 34
    for b, a in zip(before['profiles'], after['profiles']):
        assert b['step'] == a['step']
        assert b['images'] == a['images']
        assert b['measurement_sha256'] == a['measurement_sha256'] == a['full_readback_sha256']
    for b, a in zip(before['precision'], after['precision']):
        assert b['source_sha256'] == a['source_sha256']
        full = copy.deepcopy(a['full'])
        full.pop('changes')
        assert b['full'] == full, f"precision changed in {a['run']}"
    for b, a in zip(before['errors'], after['errors']):
        assert b['step'] == a['step'] and b['error'] == a['error']
        for key in ('geometry_feedback', 'geometry_changes'):
            if b[key].get('reason') == "'z'":
                assert a[key]['object_id'] == 'D2_pass'
                assert a[key]['field'] == 'z'
                assert set(('id', 'kind', 'p1', 'p2', 'z')) <= a[key]['repair_hint']['example'].keys()
    rows = []
    def row(name, b, a):
        rows.append(dict(item=name, before=b, after=a, reduction_percent=round((b-a)/b*100, 2)))
    for key in ('system_prompt_chars', 'tool_description_chars', 'input_schema_json_chars',
                'common_reference_chars', 'instruction_total_chars'):
        row(key, before['instructions'][key], after['instructions'][key])
    assert rows[-1]['after'] <= rows[-1]['before']
    row('default_instruction_total', before['default_instructions']['total'], after['default_instructions']['total'])
    row('revise_bim', before['revision']['characters'], after['revision']['characters'])
    row('34_pixel_profiles', sum(r['characters'] for r in before['profiles']), sum(r['characters'] for r in after['profiles']))
    for b, a in zip(before['precision'], after['precision']):
        row('precision:' + b['run'], b['characters'], a['characters'])
    row('five_precision_sections', sum(r['characters'] for r in before['precision']), sum(r['characters'] for r in after['precision']))
    result = dict(model_requests=0, baseline='a5baa32d', rows=rows,
        source_and_image_hashes_identical=True, profile_full_readback_identical=True,
        full_diagnostics_identical_except_added_save_contract_and_change_labels=True,
        error_steps=[r['step'] for r in after['errors']],
        character_units='Unicode characters; full MCP text for revisions/profiles, compact JSON for precision; same serializer on both sides')
    (HERE / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
