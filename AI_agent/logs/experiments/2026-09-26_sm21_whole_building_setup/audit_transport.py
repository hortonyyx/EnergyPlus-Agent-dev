"""Actual CLI result audit after lossless archive, no model calls."""
from collections import Counter
import gzip
import json
from pathlib import Path
from scripts.tool_scripts.run_bim_agent import dump
RUN=Path(__file__).resolve().parent.parent/'2026-09-26_sm21_whole_building_claude_run57'
def audit(run=RUN):
    ids={};errors=[];finish=[]
    with gzip.open(run/'agent_stream.jsonl.gz','rt') as stream:
        for line in stream:
            content=json.loads(line).get('message',{}).get('content',[])
            for block in content if isinstance(content,list) else []:
                if block.get('type')=='tool_use':ids[block['id']]=block['name']
                if block.get('type')!='tool_result':continue
                tool=ids.get(block['tool_use_id'],'unknown');result=block.get('content',[])
                texts=[result] if isinstance(result,str) else [r['text'] for r in result if r.get('type')=='text']
                if block.get('is_error'):errors.append(dict(tool=tool,text=texts))
                if tool.endswith('finish_bim'):
                    for text in texts:
                        try:payload=json.loads(text)
                        except ValueError:payload={}
                        finish.append(dict(characters=len(text),parseable_summary=bool(payload.get('candidate')),
                            detached_output_notice='persisted-output' in text or 'Full output saved to' in text))
    dump(run/'evaluation/tool_transport.json',dict(actual_tool_call_counts=dict(Counter(ids.values())),
        tool_errors=errors,finish_results=finish,note='Actual CLI tool results; transport is not semantic acceptance.'))
    assert finish and all(r['parseable_summary'] and not r['detached_output_notice'] for r in finish)
    print(json.dumps(dict(errors=len(errors),finish=finish,calls=dict(Counter(ids.values()))),indent=2))
if __name__=='__main__':audit()
