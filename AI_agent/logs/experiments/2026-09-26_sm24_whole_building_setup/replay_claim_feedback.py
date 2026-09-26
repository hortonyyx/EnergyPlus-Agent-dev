"""Replay a real rejected claim through MCP in a temporary copy, without a model."""
import asyncio
import copy
import gzip
import json
from pathlib import Path
import shutil
import tempfile

from scripts.tool_scripts.run_bim_agent import digest, dump
from tests.test_bim_agent_tools import _error_text, _json_result, _server_session

HERE=Path(__file__).resolve().parent
RUN=HERE.parent/'2026-09-26_sm24_whole_building_claude_run55'


def first_failed_claim():
    calls={}
    with gzip.open(RUN/'agent_stream.jsonl.gz','rt') as stream:
        for line in stream:
            content=json.loads(line).get('message',{}).get('content',[])
            for block in content if isinstance(content,list) else []:
                if block.get('type')=='tool_use':calls[block['id']]=block
                if block.get('type')=='tool_result' and block.get('is_error'):
                    call=calls[block['tool_use_id']]
                    if call['name'].endswith('record_claim'):
                        return json.loads(call['input']['claim_json'])
    raise AssertionError('Expected a preserved failed record_claim call')


async def main():
    rejected=first_failed_claim();candidate=rejected['candidate']
    originals=[RUN/candidate/n for n in ('source_model.json','proposal.json')]
    original_hashes={str(p.relative_to(RUN)):digest(p) for p in originals}
    with tempfile.TemporaryDirectory(prefix='claim-kind-feedback-') as directory:
        run=Path(directory)
        shutil.copy2(RUN/'inputs.json',run/'inputs.json')
        shutil.copytree(RUN/'images',run/'images')
        shutil.copytree(RUN/candidate,run/candidate)
        async with _server_session(run,readonly=False) as session:
            failure=_error_text(await session.call_tool('record_claim',dict(claim_json=json.dumps(rejected))))
            assert 'same exact id' in failure and '"kind": "window"' in failure
            assert not list((run/'claims').glob('claim_*.json'))
            unknown=copy.deepcopy(rejected)
            unknown['objects']=[dict(kind='window',id='nonexistent-feedback-check')]
            missing=_error_text(await session.call_tool('record_claim',dict(claim_json=json.dumps(unknown))))
            assert 'same exact id' not in missing and 'Inspect the current candidate' in missing
            assert not list((run/'claims').glob('claim_*.json'))
            corrected=copy.deepcopy(rejected)
            for ref in corrected['objects']:ref['kind']='window'
            accepted=_json_result(await session.call_tool('record_claim',dict(claim_json=json.dumps(corrected))))
            assert accepted['claim']['objects']==corrected['objects']
            assert len(list((run/'claims').glob('claim_*.json')))==1
        assert all(digest(run/name)==sha for name,sha in original_hashes.items())
    assert all(digest(RUN/name)==sha for name,sha in original_hashes.items())
    report=dict(source_run=RUN.name,rejected_objects=rejected['objects'],
        actual_wrong_kind_mcp_error=failure,actual_missing_id_mcp_error=missing,
        correct_explicit_objects=corrected['objects'],correct_claim_resolved_values=accepted['resolved_values'],
        rejected_claims_not_saved=True,no_automatic_rebinding=True,source_and_proposal_unchanged=True,
        original_run_unchanged=True,model_calls=0,
        scope='Post-generation current-code MCP replay; not evidence that a live model will use the new feedback correctly.')
    dump(HERE/'claim_feedback_replay.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':asyncio.run(main())
