"""Check actual CLI tool-result transport, not a locally regenerated summary."""
from collections import Counter
import gzip
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

BASE = Path(__file__).resolve().parent.parent
RUN = BASE/'2026-09-26_sm25_height_repeat_claude_run54'


def main():
    ids, reports, errors = {}, [], []
    with gzip.open(RUN/'agent_stream.jsonl.gz','rt') as stream:
        for line in stream:
            event=json.loads(line); content=event.get('message',{}).get('content',[])
            for block in content if isinstance(content,list) else []:
                if block.get('type')=='tool_use': ids[block['id']]=block['name']
                if block.get('type')!='tool_result': continue
                name=ids.get(block['tool_use_id'],'unknown'); result=block.get('content','')
                strings=[result] if isinstance(result,str) else [b.get('text','') for b in result if b.get('type')=='text']
                if block.get('is_error'): errors.append(dict(tool=name,text=strings))
                if not name.endswith('finish_bim'): continue
                for txt in strings:
                    try: payload=json.loads(txt); parsed=True
                    except (ValueError,TypeError): payload={}; parsed=False
                    reports.append(dict(tool=name,text_characters=len(txt),parseable_json=parsed,keys=list(payload),
                        candidate=payload.get('candidate'),height_coverage=payload.get('height_coverage'),
                        detached_output_notice=('Full output saved to' in txt or 'persisted-output' in txt)))
    load=lambda p:json.loads(p.read_text())
    previous=load(BASE/'2026-09-26_sm25_height_cold_claude_run53/inputs.json'); current=load(RUN/'inputs.json')
    assert reports and all(r['parseable_json'] and not r['detached_output_notice'] for r in reports)
    report=dict(finish_tool_results=reports,actual_tool_errors=errors,actual_tool_call_counts=dict(Counter(ids.values())),
        same_scope_as_run53=previous['scope']==current['scope'],same_image_hashes_as_run53=previous['images']==current['images'],
        changed_implementation_paths=[k for k,v in current['implementation_sha256'].items() if previous['implementation_sha256'].get(k)!=v],
        interpretation='Actual parseable summary returned to model; this is transport evidence, not proof of semantic understanding. tools.jsonl may contain multiple events per call.')
    dump(RUN/'evaluation/repeat_transport.json',report)
    print(json.dumps({k:report[k] for k in ('same_scope_as_run53','same_image_hashes_as_run53','changed_implementation_paths','actual_tool_call_counts')},indent=2))


if __name__=='__main__': main()
