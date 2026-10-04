"""Independently cross-check completed SSE usage with the installed official SDK."""
import gzip
import json
from pathlib import Path
import anthropic
from anthropic._models import construct_type
from anthropic.lib.streaming._messages import accumulate_event
from anthropic.types import RawMessageStreamEvent

HERE=Path(__file__).resolve().parent

def main():
    result=json.loads((HERE/'sequence_result.json').read_bytes())
    checks=[]
    for row in result['steps']:
        if row['arm']!='stream':continue
        name=f"{row['replicate']}_stream_{row['step']+1:02d}.response.raw.gz"
        data=gzip.decompress((HERE/'probe'/name).read_bytes()).decode('utf-8').replace('\r\n','\n')
        snapshot=None
        for record in data.split('\n\n'):
            body='\n'.join(line[5:].lstrip(' ') for line in record.split('\n') if line.startswith('data:'))
            if not body:continue
            event=json.loads(body)
            if event['type']=='ping':continue
            typed=construct_type(value=event,type_=RawMessageStreamEvent)
            snapshot=accumulate_event(event=typed,current_snapshot=snapshot)
        assert snapshot is not None
        actual=snapshot.usage.model_dump()
        fields=('input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens')
        assert all((actual.get(k) or 0)==row['usage'].get(k,0) for k in fields)
        assert snapshot.stop_reason==row['stop_reason']
        checks.append({'replicate':row['replicate'],'step':row['step']+1,'sdk_usage':{k:actual.get(k) for k in fields},'equal':True})
    assert len(checks)==24
    proof={'official_sdk_version':anthropic.__version__,'stream_responses':len(checks),
        'all_usage_and_stop_reason_equal':True,'model_requests':0,'checks':checks}
    (HERE/'independent_sse_check.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({k:v for k,v in proof.items() if k!='checks'}))

if __name__=='__main__':main()
