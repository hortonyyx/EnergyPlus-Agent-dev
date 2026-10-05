"""Record developer original-image review of the small novel diagnostic set.

This is evaluation-only: frozen reference labels and manual judgements are never
imported by production code. Counts are per saved draft, not independent runs.
"""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def main():
    replay=json.loads((HERE/'plan_replay.json').read_text())
    groups={key:dict(drafts=0,new_items=0,frozen_label_matches=0,manual_supported=0,
                     new_false_positives=0,unresolved=0) for key in ('frozen_108','sm25_two_runs','sm24_run100')}
    reviewed=[]
    for row in replay['rows']:
        group=('frozen_108' if row['frozen_108'] else
               'sm24_run100' if row['run'].endswith('run100') else 'sm25_two_runs')
        stats=groups[group];stats['drafts']+=1
        for index,item in enumerate(row['novel_items']):
            labelled=bool(row.get('novel_matches',[])[index]) if row['frozen_108'] else False
            if item['type']=='unsupported_open_separator' and item['opening']=='PASS_corr_s':
                assert item['y_px']==957 and item['x_px']==[695,792]
                reason='Original crop [658,920,829,995]: continuous inkless corridor between real room walls. '
                reason+='Frozen F1_S13 is a declared space without a reference; this diagnostic locates its artificial open separator.'
            elif item['type']=='unsupported_open_separator' and item['opening']=='D_core':
                assert item['y_px']==496 and item['x_px']==[741,793]
                reason='Original crop [704,459,830,534]: no wall/jamb/door arc across the corridor head. '
                reason+='candidate_07 opening F1:D_core joins F1:S_C to F1:S_corr along this same separator.'
            elif item['type']=='undeclared_wall_line' and 'sm21_' in row['run']:
                assert item['y_px']==624 and item['x_px']==[894,1816]
                reason='Original crop [819,549,1891,699]: real corridor paired faces near y=618/629, interrupted by doors. '
                reason+='Draft declares the north corridor wall at y=600 (about 0.26 m away). '
                reason+='This is a misplaced existing wall, not an instruction to add a second wall; frozen room-seed labels do not label this offset.'
            elif group=='sm24_run100' and item['type']=='undeclared_wall_line':
                assert (item.get('x_px'),item.get('y_px')) in (
                    (459,[300,583]),([461,612],585),([402,457],753),(459,[700,751]))
                reason='Original run100 draft_002 image: the corridor east double line, its lower cross wall, '
                reason+='and two legs of the lower room return are drawn and absent from the declaration; all four look_box regions inspected.'
            else:
                raise AssertionError(('Unexpected new item: manual review required',row['run'],item))
            stats['new_items']+=1
            stats['frozen_label_matches']+=labelled
            stats['manual_supported']+=not labelled
            reviewed.append(dict(run=row['run'],draft=row['draft'],image=row['image'],
                image_sha256=row['image_sha256'],plan_sha256=row['plan_sha256'],item=item,
                frozen_label_match=labelled,decision='supported_difference',reason=reason))
    frozen=[r for r in replay['rows'] if r['frozen_108']]
    reference_delta=dict(before=sum(e['before_detected'] for r in frozen for e in r['labels']),
        after=sum(e['after_detected'] for r in frozen for e in r['labels']),
        added=sum(e['after_detected'] and not e['before_detected'] for r in frozen for e in r['labels']),
        lost=sum(e['before_detected'] and not e['after_detected'] for r in frozen for e in r['labels']))
    source=ROOT/'.tmp_a4t/history/sm25_runtime_anthropic/bim/candidate_07/source_model.json'
    model=json.loads(source.read_text())
    opening=next(o for o in model['openings'] if o['id']=='F1:D_core')
    assert set(opening['space_ids'])=={'F1:S_C','F1:S_corr'}
    output=dict(model_requests=0,method=__doc__,groups=groups,frozen_label_detection=reference_delta,
        candidate_07=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            opening=opening,matching_drafts=['draft_009','draft_011']),reviewed=reviewed,
        limitations='Only newly added items are adjudicated here; no claim of zero false positives for the pre-existing checker. '
                    'The old subscription sm25 has an implausible millimetre-as-metre calibration: all three drafts are explicitly not_checked. '
                    'Frozen labels cover room seeds/doors, not every wall coordinate.')
    (HERE/'plan_adjudication.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(groups=groups,frozen_label_detection=reference_delta),indent=2))


if __name__=='__main__':main()
