"""Verify every probe wire/response and apply the pre-registered decision rule."""
import gzip
import hashlib
import importlib
import json
from pathlib import Path

probe=importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3r.sequence_probe')
HERE=Path(__file__).resolve().parent

def fraction(rows):
    read=sum(r['usage'].get('cache_read_input_tokens',0) for r in rows)
    inp=sum(sum(r['usage'].get(k,0) for k in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens')) for r in rows)
    return {'read':read,'input':inp,'fraction':read/inp if inp else None}

def main():
    spec=json.loads((probe.OUT/'design.json').read_bytes())
    registered=json.loads((HERE/'preregistered_design.json').read_bytes())
    assert hashlib.sha256((probe.OUT/'design.json').read_bytes()).hexdigest()==registered.pop('design_sha256')
    assert spec==registered
    journal=probe.journal_rows();rows=[r for r in journal if r['event']=='result']
    attempts=[r for r in journal if r['event']=='attempt']
    by_ticket={r['ticket']:r for r in attempts}
    verified=0
    for row in rows:
        stem=f"{row['replicate']}_{row['arm']}_{row['step']+1:02d}"
        wire=gzip.decompress((probe.OUT/(stem+'.request.json.gz')).read_bytes())
        raw=gzip.decompress((probe.OUT/(stem+'.response.raw.gz')).read_bytes())
        assert hashlib.sha256(wire).hexdigest()==by_ticket[row['ticket']]['wire_sha256']
        assert wire==probe.json_bytes(probe.build_body(spec,row['arm'],row['replicate'],row['step']))
        assert hashlib.sha256(raw).hexdigest()==row['raw_sha256']
        if row['status']=='completed':
            parsed=probe.sse_usage(raw) if row['arm']=='stream' else json.loads(raw)
            assert parsed['usage']==row['usage']
            assert probe.reported_total_tokens(row['usage'])==row['total_tokens']
        verified+=1
    good=[r for r in rows if r['status']=='completed']
    result={'design_commit':'91749d6c','complete':len(good)==72 and len(attempts)==72,
        'requests':len(attempts),'verified_wire_and_raw_responses':verified,
        'reported_total_tokens':sum(r['total_tokens'] for r in good),
        'usage_components':{k:sum(r['usage'].get(k,0) for r in good) for k in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens','output_tokens')},
        'paratera_requests':0,'deepseek_requests':0,'groups':{},'decision':{},'steps':good}
    for arm in probe.ARMS:
        rep=[]
        for repeat in range(2):
            group=sorted([r for r in good if r['arm']==arm and r['replicate']==repeat],key=lambda r:r['step'])
            # Journal gap events start before body preparation. Use the later
            # durable send-intent timestamp for the actual comparison interval.
            gaps=[b['started_epoch']-a['finished_epoch'] for a,b in zip(group,group[1:])]
            inputs=[sum(r['usage'].get(k,0) for k in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens')) for r in group]
            valid=(len(group)==12 and len(gaps)==11 and sum(30<=v<=60 for v in gaps)>=10
                and bool(inputs) and 25000<=inputs[0]<=35000)
            rep.append({'replicate':repeat,'complete_and_conditions_met':valid,'cache_reads':[r['usage'].get('cache_read_input_tokens',0) for r in group],
                'input_totals':inputs,'output_tokens':[r['usage']['output_tokens'] for r in group],
                'gaps_seconds':gaps,'post_first':fraction(group[1:]),'all_steps':fraction(group),
                'total_request_seconds':sum(r['seconds'] for r in group)})
        result['groups'][arm]={'replicates':rep,'post_first':fraction([r for r in good if r['arm']==arm and r['step']>0]),
            'all_steps':fraction([r for r in good if r['arm']==arm])}
    base=result['groups']['baseline']
    result['all_sequence_conditions_met']=all(r['complete_and_conditions_met']
        for g in result['groups'].values() for r in g['replicates'])
    result['acceptance_B_fully_met']=result['complete'] and result['all_sequence_conditions_met']
    for arm in ('stream','identity'):
        candidate=result['groups'][arm]
        delta=(candidate['post_first']['fraction']-base['post_first']['fraction']) if candidate['post_first']['fraction'] is not None and base['post_first']['fraction'] is not None else None
        individual=[]
        for a,b in zip(candidate['replicates'],base['replicates']):
            individual.append(a['post_first']['fraction']-b['post_first']['fraction'] if a['post_first']['fraction'] is not None and b['post_first']['fraction'] is not None else None)
        conditions=result['complete'] and all(r['complete_and_conditions_met'] for g in (candidate,base) for r in g['replicates'])
        result['decision'][arm]={'eligible':conditions,'aggregate_gain_percentage_points':None if delta is None else 100*delta,
            'replicate_gains_percentage_points':[None if d is None else 100*d for d in individual],
            'adopt':conditions and delta>0.20 and all(d>0.20 for d in individual)}
    (HERE/'sequence_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('complete','requests','reported_total_tokens','decision')},indent=2))
    for arm,group in result['groups'].items():
        for rep in group['replicates']:
            print(arm,rep['replicate'],rep['cache_reads'],rep['post_first']['fraction'])

if __name__=='__main__':main()
