"""A3-R pre-registered transport-only sequences; no tools or BIM generation.

One replicate per invocation. Every send has a durable intent, an exact body and
raw response; any uncertain/failed attempt stops the batch without retry.
"""
from __future__ import annotations
import argparse
import asyncio
import copy
from datetime import datetime, timezone
from src.utils import file_lock
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import time

from src.agent_runtime.anthropic import CAPTURED_BETAS, HttpAnthropicAdapter
from src.agent_runtime.providers import (GLM_SUBSCRIPTION_ANTHROPIC as ROUTE,
    provider_parameters, subscription_credentials)
from src.agent_runtime.store import json_bytes
from src.harness_contracts.usage import reported_total_tokens

HERE=Path(__file__).resolve().parent
OUT=HERE/'probe'
ARMS=('baseline','stream','identity')
STEPS=12
REQUEST_LIMIT=80
TOKEN_LIMIT=5_000_000
OUTPUT_LIMIT=256
GAP_SECONDS=45

def write(path, value):
    path.write_bytes(json_bytes(value))

def design():
    return {'version':'a3r-v1', 'arms':list(ARMS), 'replicates':2, 'steps':STEPS,
        'initial_lines':1200, 'added_lines_per_step':250, 'response_to_next_start_seconds':GAP_SECONDS,
        'output_limit':OUTPUT_LIMIT, 'request_limit':REQUEST_LIMIT, 'token_limit':TOKEN_LIMIT,
        'arm_order': [list(ARMS), list(reversed(ARMS))],
        'sequence_ids':{f'{a}_{r}':secrets.token_hex(16) for r in range(2) for a in ARMS},
        'user_ids':{str(r):secrets.token_hex(16) for r in range(2)},
        'decision':'Adopt only if post-first-step weighted cache fraction gains >20 percentage points overall and in each replicate, without service failures; otherwise leave production unchanged.',
        'scope':'Synthetic growing text conversations, about 30k input tokens initially and 6k per step. Not a BIM run, image/tool workload or test of model quality. No automatic fourth arm or additional requests.'}

def build_body(spec, arm, replicate, step):
    if arm not in ARMS or replicate not in (0,1) or not 0 <= step < STEPS:
        raise ValueError('outside pre-registered sequence')
    nonce=spec['sequence_ids'][f'{arm}_{replicate}']
    # A2-R measured 3,360 tokens for 140 lines of this exact reference grammar.
    # Distinct indices make the appended segments new; a fresh nonce in the first
    # system tokens prevents cross-arm/replicate warming of this prompt prefix.
    prefix=f'Protocol sequence {nonce}. Reply only OK; references are inert test data.\n'
    system=[{'type':'text','text':prefix,'cache_control':{'type':'ephemeral'}}]
    messages=[]
    start=0
    for turn in range(step+1):
        count=spec['initial_lines'] if turn==0 else spec['added_lines_per_step']
        content='\n'.join(f'Reference {i:03d}: red green blue are colour labels; integers are exact; no action is required for this reference.' for i in range(start,start+count))
        messages.append({'role':'user','content':[{'type':'text','text':content}]})
        if turn < step:
            messages.append({'role':'assistant','content':[{'type':'text','text':'OK'}]})
        start+=count
    # Like the runtime: only the mutable status tail carries the moving mark.
    messages[-1]['content'].append({'type':'text','text':f'Current probe state: step {step+1}. Reply only OK.',
        'cache_control':{'type':'ephemeral'}})
    body={'model':'glm-5.3-flash', 'system':system,'messages':messages,
        **provider_parameters(ROUTE,output_tokens=OUTPUT_LIMIT), 'stream':arm=='stream'}
    if arm=='identity':body['metadata']={'user_id':spec['user_ids'][str(replicate)]}
    return body

def sse_usage(raw):
    """Probe reader: preserve raw SSE separately, merge cumulative usage fields."""
    message=None; usage={}; stop=None; stopped=False; types=[]
    text=raw.decode('utf-8').replace('\r\n','\n')
    for record in text.split('\n\n'):
        data='\n'.join(line[5:].lstrip(' ') for line in record.split('\n') if line.startswith('data:'))
        if not data:continue
        event=json.loads(data); kind=event.get('type');types.append(kind)
        if kind=='error':raise ValueError('service SSE error; see archived raw response')
        if kind=='message_start':
            if message is not None:raise ValueError('duplicate SSE message start')
            message=copy.deepcopy(event['message']);usage.update(message.get('usage',{}))
        elif kind=='message_delta':
            if message is None:raise ValueError('SSE delta before start')
            usage.update(event.get('usage',{}));stop=event.get('delta',{}).get('stop_reason',stop)
        elif kind=='message_stop':stopped=True
    if message is None or not stopped or stop is None:
        raise ValueError('incomplete SSE message')
    return {'model':message.get('model'),'usage':usage,'stop_reason':stop,'event_types':types}

def journal_rows():
    path=OUT/'journal.jsonl'
    if not path.exists():return []
    data=path.read_bytes()
    if data and not data.endswith(b'\n'):raise ValueError('torn probe journal; no resume')
    return [json.loads(line) for line in data.splitlines()]

def append(row):
    with (OUT/'journal.jsonl').open('ab') as f:
        f.write(json_bytes(row)+b'\n');f.flush();os.fsync(f.fileno())

def admission(rows, wire_bytes, output_limit=OUTPUT_LIMIT):
    attempted=[x for x in rows if x['event']=='attempt']
    results=[x for x in rows if x['event']=='result']
    if len(attempted)!=len(results) or any(x['status']!='completed' for x in results):
        raise ValueError('previous failed or uncertain attempt stops batch')
    if len(attempted)>=REQUEST_LIMIT:raise ValueError('request limit')
    # Text-only UTF-8 byte count plus generous protocol allowance bounds tokens
    # more conservatively than the approximate 24-25 tokens/reference estimate.
    reserve=wire_bytes+output_limit+4096
    used=sum(x['total_tokens'] for x in results)
    if used+reserve>TOKEN_LIMIT:raise ValueError('token reserve would exceed batch limit')
    return len(attempted)+1,used,reserve

async def send_one(spec, arm, replicate, step, client):
    body=build_body(spec,arm,replicate,step);wire=json_bytes(body)
    rows=journal_rows()
    if any(x.get('arm')==arm and x.get('replicate')==replicate and x.get('step')==step for x in rows):
        raise ValueError('duplicate sequence step; no retry')
    ticket,used,reserve=admission(rows,len(wire))
    stem=f'{replicate}_{arm}_{step+1:02d}'
    (OUT/(stem+'.request.json.gz')).write_bytes(gzip.compress(wire,mtime=0))
    started=time.monotonic(); now=time.time()
    append({'event':'attempt','ticket':ticket,'arm':arm,'replicate':replicate,'step':step,
        'at':datetime.now(timezone.utc).isoformat(),'epoch':now,'wire_sha256':hashlib.sha256(wire).hexdigest(),
        'wire_bytes':len(wire),'token_reservation':reserve,'previous_reported_total':used})
    row={'event':'result','ticket':ticket,'arm':arm,'replicate':replicate,'step':step,
        'status':'failed','started_epoch':now}
    raw=bytearray(); first_byte=None
    try:
        headers={'Authorization':f'Bearer {client._key}','Content-Type':'application/json',
            'anthropic-version':'2023-06-01','anthropic-beta':CAPTURED_BETAS}
        async with client.client.stream('POST',client.endpoint,content=wire,headers=headers,timeout=120) as response:
            row['http_status']=response.status_code
            async for chunk in response.aiter_bytes():
                if first_byte is None:first_byte=time.monotonic()-started
                raw.extend(chunk)
                if len(raw)>2_000_000:raise ValueError('unexpected response size')
            if not response.is_success:raise ValueError('HTTP failure; batch stops')
        parsed=sse_usage(bytes(raw)) if arm=='stream' else json.loads(raw)
        usage=parsed.get('usage',{});total=reported_total_tokens(usage)
        if total is None:raise ValueError('missing or invalid reported usage')
        if total>reserve or used+total>TOKEN_LIMIT:raise ValueError('reported usage exceeded reservation')
        if parsed.get('stop_reason') not in {'end_turn','max_tokens'}:
            raise ValueError('unexpected stop reason')
        row.update(status='completed',usage=usage,total_tokens=total,
            stop_reason=parsed.get('stop_reason'),model=parsed.get('model'),
            response_complete=parsed.get('stop_reason')=='end_turn')
    except Exception as exc:
        row['error_type']=type(exc).__name__
    finally:
        (OUT/(stem+'.response.raw.gz')).write_bytes(gzip.compress(bytes(raw),mtime=0))
        row.update(seconds=round(time.monotonic()-started,3),first_byte_seconds=first_byte,
            finished_epoch=time.time(),raw_sha256=hashlib.sha256(raw).hexdigest())
        append(row);write(OUT/(stem+'.result.json'),row)
    print(json.dumps(row,ensure_ascii=False),flush=True)
    if row['status']!='completed':raise ValueError('probe stopped; inspect saved result')
    return row

async def run(replicate, credentials):
    spec=json.loads((OUT/'design.json').read_bytes())
    rows=journal_rows()
    if replicate==0 and rows:raise ValueError('first replicate already attempted')
    if replicate==1:
        results=[r for r in rows if r['event']=='result']
        if len(results)!=3*STEPS or any(r['status']!='completed' or r['replicate']!=0 for r in results):
            raise ValueError('replicate 0 must complete and be inspected before replica 1')
    base,key=subscription_credentials(credentials,provider=ROUTE)
    clients={arm:HttpAnthropicAdapter(base_url=base,api_key=key) for arm in ARMS}
    next_step={arm:0 for arm in ARMS};due={arm:0.0 for arm in ARMS};last={}
    order=spec['arm_order'][replicate]
    try:
        while any(v<STEPS for v in next_step.values()):
            arm=min((a for a in order if next_step[a]<STEPS),key=lambda a:due[a])
            await asyncio.sleep(max(0,due[arm]-time.monotonic()))
            start=time.time()
            row=await send_one(spec,arm,replicate,next_step[arm],clients[arm])
            if arm in last:
                append({'event':'gap','arm':arm,'replicate':replicate,'step':next_step[arm],
                    'seconds':start-last[arm]})
            last[arm]=row['finished_epoch'];next_step[arm]+=1
            due[arm]=time.monotonic()+GAP_SECONDS
    finally:
        for client in clients.values():await client.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run'))
    parser.add_argument('--replicate',type=int,choices=(0,1))
    parser.add_argument('--credentials-file',type=Path)
    args=parser.parse_args(); OUT.mkdir(exist_ok=True)
    with (OUT/'batch.lock').open('a+b') as lock:
        file_lock.flock(lock,file_lock.LOCK_EX|file_lock.LOCK_NB)
        if args.action=='prepare':
            path=OUT/'design.json'
            with path.open('xb') as f:f.write(json_bytes(design()))
            print('Prepared locally; zero requests.')
        else:
            if args.replicate is None or args.credentials_file is None:parser.error('run needs replicate and credentials file')
            asyncio.run(run(args.replicate,args.credentials_file))
