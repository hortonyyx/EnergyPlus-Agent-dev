"""Run pre-A3 and A3 local MCP handlers on the five saved historical runs.

Each call uses an independent copy of the saved run, pruned before the historical
candidate/draft being created. Saved views/calibrations are held at the archived
final state; claims used by a saved application use its actual decision snapshot,
and future application files are removed by that application's sequence number.
All context preparation is identical on both sides. This isolates API output and
geometry; it is not a model re-run or a reconstruction of unseen model behavior.
"""
import argparse
import asyncio
from collections import Counter, defaultdict
import copy
import hashlib
import importlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import run_bim_agent as current
from src.agent.execution.bim_claims import geometry_state
from src.agent.geometry import plan_partition
from src.agent_runtime.agent_registry import agent_version_record

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
WORK=ROOT/'.tmp_a3t'
BASELINE='ea802787'
audit=importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3t.audit_usage')
measure=importlib.import_module('AI_agent.logs.experiments.2026-10-03_tool_package_t1.measure_instructions')


def fixture(name, call, side):
    notes=dict(application_cutoff=None,removed_applications=[],removed_later_decisions=[])
    origin=WORK/'history'/name
    if (origin/'bim').is_dir():origin=origin/'bim'
    run=WORK/'mcp_replay'/name/str(call['index'])/side
    if run.exists():shutil.rmtree(run)
    original=audit.result(call)
    building=call['tool'] in {'build_bim','build_plan_bim','build_parametric_bim','revise_bim','revise_plan_bim','assemble_plan_bim'}
    cutoff=original.get('candidate') if building else None
    draft_file=original.get('plan_input',{}).get('plan_file')
    draft_cutoff=Path(draft_file).parent.name if draft_file and call['tool'] in {'build_plan_bim','revise_plan_bim'} else None
    def ignored(directory,names):
        relative=Path(directory).relative_to(origin)
        skip=[]
        for name in names:
            if name=='tools.jsonl' or name=='tool_reports':skip.append(name)
            elif relative==Path('.') and cutoff and name.startswith('candidate_') and name>=cutoff:skip.append(name)
            elif relative==Path('plan_drafts') and draft_cutoff and name.startswith('draft_') and name>=draft_cutoff:skip.append(name)
            elif Path(name).suffix.lower() in {'.png','.jpg','.jpeg'} and 'images' not in relative.parts:skip.append(name)
        return skip
    shutil.copytree(origin,run,copy_function=shutil.copyfile,ignore=ignored)
    manifest=json.loads((run/'inputs.json').read_text());manifest.pop('deadline_epoch',None);manifest['max_candidates']=100
    current.dump(run/'inputs.json',manifest)
    original=audit.result(call)
    if call['tool'] in {'build_bim','build_plan_bim','build_parametric_bim','revise_bim','revise_plan_bim','assemble_plan_bim'}:
        candidate=original.get('candidate')
        if candidate:
            for p in run.glob('candidate_*'):
                if p.is_dir() and p.name>=candidate:shutil.rmtree(p)
            application=original.get('claim_application',{})
            application_cutoff=application.get('id')
            notes['application_cutoff']=application_cutoff
            for p in (run/'claims').glob('application_*.json'):
                row=json.loads(p.read_text())
                remove=p.stem>=application_cutoff if application_cutoff else row.get('candidate','')>=candidate
                if remove:
                    p.unlink();notes['removed_applications'].append(p.stem)
            for claim_id,snapshot in application.get('evidence',{}).get('claims',{}).items():
                decision=snapshot['decision']
                assert json.loads((run/'claims'/f'{claim_id}.json').read_text())==snapshot['record']
                assert json.loads((run/'claims'/f'{decision["id"]}.json').read_text())==decision
                for p in (run/'claims').glob('decision_*.json'):
                    row=json.loads(p.read_text())
                    if row['claim_id']==claim_id and p.stem>decision['id']:
                        p.unlink();notes['removed_later_decisions'].append(p.stem)
        plan_file=original.get('plan_input',{}).get('plan_file')
        if plan_file and call['tool'] in {'build_plan_bim','revise_plan_bim'}:
            target=Path(plan_file).parent.name
            for p in (run/'plan_drafts').glob('draft_*'):
                if p.is_dir() and p.name>=target:shutil.rmtree(p)
    return run,notes


def capture(module,run,call,compiler):
    servers=[]
    with patch.object(FastMCP,'run',lambda server:servers.append(server)):
        module.serve(run)
    # The runner catches this exact class to render host-error images. Pair it
    # with the compiler's module; mixing old/new class identities drops a view.
    with patch.multiple(plan_partition, compile_plan_partition=compiler,
                        OpeningHostError=compiler.__globals__['OpeningHostError']):
        result=asyncio.run(servers[0].call_tool(call['tool'],copy.deepcopy(call['arguments'])))
    content=result.content if hasattr(result,'content') else result[0] if isinstance(result,tuple) else result
    data=getattr(result,'structuredContent',None)
    if data is None and isinstance(result,tuple):data=result[1]
    if data is None:
        data=next((json.loads(block.text) for block in content if block.type=='text' and block.text.startswith('{')),None)
    if data is None:
        data={'isError':getattr(result,'isError',False),'text':'\n'.join(b.text for b in content if b.type=='text')}
    images=[hashlib.sha256(b.data.encode()).hexdigest() for b in content if b.type=='image']
    candidate=data.get('candidate')
    geometry=None
    if candidate and (run/candidate/'proposal.json').exists():
        geometry=geometry_state(json.loads((run/candidate/'proposal.json').read_text()))
    texts=[block.text for block in content if block.type=='text']
    return data,images,geometry,texts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    registered=agent_version_record(ROOT,verify=True)
    snapshot={p:v['sha256'] for p,v in registered['files'].items()}
    old=measure.baseline_module('scripts/tool_scripts/run_bim_agent.py','a3t_old_runner',BASELINE)
    old_compiler=measure.baseline_module('src/agent/geometry/plan_partition.py','a3t_old_compiler',BASELINE).compile_plan_partition
    new_compiler=plan_partition.compile_plan_partition
    rows=[];totals=defaultdict(lambda:dict(calls=0,before=0,after=0))
    if args.resume:
        saved=json.loads((HERE/'mcp_reply_comparison.json').read_text())
        assert saved['baseline_commit']==BASELINE and saved['source_sha256']==snapshot
        report=saved
        rows=saved['rows']
        for row in rows:
            for group in (row['tool'],'ALL'):
                totals[group]['calls']+=1
                for side in ('before','after'):totals[group][side]+=row[side]['characters']
    completed={(row['run'],row['step']) for row in rows}
    (HERE/'mcp_replies').mkdir(exist_ok=True)
    for name,path in audit.records():
        for call in audit.steps(path):
            if call['tool'] not in audit.TOOLS:continue
            if (name,call['index']) in completed:continue
            captures={}
            for side,module in [('before',old),('after',current)]:
                run,context=fixture(name,call,side)
                data,images,geometry,texts=capture(module,run,call,old_compiler if side=='before' else new_compiler)
                # Preserve raw small replies and hash full bodies; no copied PNGs.
                raw=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
                target=HERE/'mcp_replies'/f'{name}_{call["index"]}_{side}.json'
                target.write_text(raw)
                captures[side]=dict(characters=sum(len(value) for value in texts),
                    text_sha256=[hashlib.sha256(value.encode()).hexdigest() for value in texts],
                    pretty_json_characters=len(raw)-1,sha256=hashlib.sha256(raw.encode()).hexdigest(),
                    status=data.get('status'),error=data.get('error'),candidate=data.get('candidate'),
                    image_sha256=images,geometry=geometry,details_file=data.get('details_file'),
                    field_aliases=data.get('plan_input',{}).get('field_aliases',[]),fixture_context=context)
                if side=='after' and data.get('details_file'):
                    full=json.loads((run/data['details_file']).read_text())
                    assert full.get('height_coverage')==data.get('height_coverage') or call['tool']=='finish_bim'
            before,after=captures['before'],captures['after']
            same=before['geometry']==after['geometry']
            assert same,(name,call['index'],call['tool'],'geometry changed')
            images_equal=before['image_sha256']==after['image_sha256']
            alias_draft_change=bool(not images_equal and after['field_aliases'] and before['geometry'] is None and after['geometry'] is None)
            assert images_equal or alias_draft_change,(name,call['index'],'images changed')
            for group in (call['tool'],'ALL'):
                t=totals[group];t['calls']+=1;t['before']+=before['characters'];t['after']+=after['characters']
            for c in captures.values():
                c['geometry_sha256']=hashlib.sha256(json.dumps(c.pop('geometry'),sort_keys=True).encode()).hexdigest()
            row=dict(run=name,step=call['index'],tool=call['tool'],geometry_equal=same,
                     images_equal=images_equal,alias_draft_rendering_changed=alias_draft_change,**captures)
            rows.append(row)
            print(name,call['index'],call['tool'],before['characters'],after['characters'],flush=True)
            # Keep only result bodies and hashes; fixtures are reproducible from archives.
            shutil.rmtree(WORK/'mcp_replay'/name/str(call['index']))
            report=dict(method=__doc__,counting='Exact MCP text block characters, excluding images and transport envelopes; pretty JSON retained only as evidence.',
                        baseline_commit=BASELINE,model_requests=0,rows=rows,totals=dict(totals))
            report.update(agent_version=registered['version_id'],source_sha256=snapshot)
            current.dump(HERE/'mcp_reply_comparison.json',report)
    for t in totals.values():t['reduction_percent']=round(100*(1-t['after']/t['before']),2)
    current.dump(HERE/'mcp_reply_comparison.json',report)
    print(json.dumps(dict(totals),indent=2),flush=True)
    assert totals['ALL']['reduction_percent'] >= 40

if __name__=='__main__':main()
