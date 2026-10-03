"""Replay the exact T1 failure arguments and the revision with duplicated evidence.

Immutable source bytes come from existing mainline records / T1's source commit;
all generated geometry stays in a temporary directory inside this worktree.
"""
import asyncio
import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts.run_bim_agent import Toolkit, serve

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RECORDS = HERE.parent/'2026-10-01_behaviour_records/records'
T1 = '74e27da33d8f957334b6e77c40e788acf015ea55'


def steps(case):
    path = RECORDS/f'2026-10-03_{case}_glm_tools_t1/record.json.gz'
    with gzip.open(path, 'rt') as stream:
        record = json.load(stream)
    return record['invocations'][0]['steps'], dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def member_span(text, key):
    """Find one direct JSON member without reformatting floats or other fields."""
    decoder = json.JSONDecoder()
    cursor = 1
    while True:
        while text[cursor].isspace() or text[cursor] == ',':
            cursor += 1
        name, cursor = decoder.raw_decode(text, cursor)
        while text[cursor].isspace() or text[cursor] == ':':
            cursor += 1
        start = cursor
        _, cursor = decoder.raw_decode(text, cursor)
        if name == key:
            return start, cursor
        if text[cursor:].lstrip().startswith('}'):
            raise KeyError(key)


def main():
    report = dict(model_requests=0, input_commit=T1)
    with tempfile.TemporaryDirectory(prefix='.c2-feedback-', dir=ROOT) as temporary:
        root = Path(temporary)
        bad = root/'bad'; bad.mkdir()
        prefix25 = 'AI_agent/logs/experiments/2026-10-03_sm25_glm_tools_t1'
        paths25 = subprocess.check_output(['git','ls-tree','-r','--name-only',T1,prefix25],cwd=ROOT,text=True).splitlines()
        restored = {}
        for name in paths25:
            relative = Path(name).relative_to(prefix25)
            if (relative.as_posix() == 'inputs.json' or relative.parts[0] == 'images'
                    or len(relative.parts) == 3 and relative.parts[:2] in {
                        ('plan_drafts', 'draft_004'), ('plan_drafts', 'draft_005')}
                    and relative.name in {'input.json', 'plan.json'}):
                raw = subprocess.check_output(['git','show',f'{T1}:{name}'],cwd=ROOT)
                target = bad/relative; target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw)
                restored[str(relative)] = hashlib.sha256(raw).hexdigest()
        manifest = json.loads((bad/'inputs.json').read_bytes())
        servers=[]
        with patch.object(FastMCP,'run',lambda s: servers.append(s)):
            serve(bad)
        rows, source = steps('sm25')
        errors=[]
        for index in (63,65):
            step=next(s for s in rows if s['index']==index)
            args=step['arguments']
            # Real Toolkit, source-image hash, saved draft hash, compiler and
            # MCP feedback. Only the clock is fixed to the historical call.
            with patch('scripts.tool_scripts.bim_agent_budget.time.time',
                       return_value=manifest['started_epoch']+step['t_call']):
                result=asyncio.run(servers[0].call_tool('revise_plan_bim',args))
            text='\n'.join(c.text for c in result.content if c.type=='text')
            assert result.isError and '需要列表' in text and text!='0'
            errors.append(dict(step=index,tool=step['tool'],arguments_sha256=hashlib.sha256(json.dumps(args,sort_keys=True).encode()).hexdigest(),before=step['result_text'],after=text))
        report['repair_hint']=dict(source=source,replays=errors,
            execution='Real MCP/Toolkit with original saved drafts and images; only clock frozen',
            restored_files_sha256=restored)
        # Recreate the immutable state before sm24 step 71, not a later candidate.
        run=root/'revision'; run.mkdir()
        prefix='AI_agent/logs/experiments/2026-10-03_sm24_glm_tools_t1'
        paths=subprocess.check_output(['git','ls-tree','-r','--name-only',T1,prefix],cwd=ROOT,text=True).splitlines()
        selected=[]
        for name in paths:
            relative=Path(name).relative_to(prefix)
            if (relative.as_posix()=='inputs.json' or relative.parts[0] in {'images','candidate_01'}
                    or relative.parts[0]=='claims' and relative.name in {
                        *(f'claim_{n:04d}.json' for n in range(1,5)),
                        *(f'decision_{n:04d}.json' for n in range(1,5))}):
                target=run/relative; target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(subprocess.check_output(['git','show',f'{T1}:{name}'],cwd=ROOT))
                selected.append(str(relative))
        rows,source=steps('sm24'); step=next(s for s in rows if s['index']==71)
        original=step['result_text']; old,end=json.JSONDecoder().raw_decode(original)
        expected=copy.deepcopy(old)
        expected['provenance']['claim_application']={'file':old['provenance']['claim_application']['file']}
        # Keep the archived number formatting and trailing truncation notice.
        compact=lambda v: json.dumps(v,ensure_ascii=False,separators=(',',':'))
        start, stop = member_span(original, 'provenance')
        inner_start, inner_stop = member_span(original[start:stop], 'claim_application')
        projected = (original[:start+inner_start] + compact(expected['provenance']['claim_application'])
                     + original[start+inner_stop:])
        assert json.JSONDecoder().raw_decode(projected)[0] == expected
        toolkit=Toolkit(run)
        with patch.object(Toolkit,'remaining_seconds',return_value=3941):
            actual=toolkit.revise(**step['arguments'])
        assert actual['provenance']['claim_application']==expected['provenance']['claim_application']
        relative='claims/application_0001.json'
        old_bytes=subprocess.check_output(['git','show',f'{T1}:{prefix}/{relative}'],cwd=ROOT)
        new_bytes=(run/relative).read_bytes()
        assert old_bytes==new_bytes, 'revision evidence file changed'
        for name in ('source_model.json','proposal.json'):
            archived=subprocess.check_output(['git','show',f'{T1}:{prefix}/candidate_02/{name}'],cwd=ROOT)
            assert archived==(run/'candidate_02'/name).read_bytes(), name
        report['revise_bim']=dict(source=source,step=71,
            before_chars=len(original),after_chars=len(projected),removed_chars=len(original)-len(projected),
            measured_surface='Exact archived CLI JSON, replacing only provenance.claim_application; original number formatting and trailing truncation notice retained. Actual Toolkit replay verifies the new provenance and byte-identical evidence/source/proposal.',
            provenance_before_chars=len(compact(old['provenance']['claim_application'])),
            provenance_after=actual['provenance']['claim_application'],
            application_sha256=hashlib.sha256(new_bytes).hexdigest(),application_bytes_equal=True,
            source_model_bytes_equal=True,proposal_bytes_equal=True,
            unchanged_result_fields=[key for key in old if key!='provenance'])
    (HERE/'feedback_replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
