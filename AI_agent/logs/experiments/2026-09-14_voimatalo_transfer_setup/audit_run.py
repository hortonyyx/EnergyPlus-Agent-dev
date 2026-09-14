"""Post-run input/transport/expansion/source audit; never feeds evaluation to generation."""
from __future__ import annotations
import argparse
import base64
from collections import Counter
import hashlib
import gzip
import io
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import coordinate_grid_view
from src.agent.geometry.parametric_proposal import expand_parametric_proposal
from src.agent.execution.source_proposal import export_source_proposal


def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('--out-name',default='execution_audit');args=parser.parse_args()
    run=args.run.resolve();out=run/args.out_name;out.mkdir(exist_ok=False)
    manifest=json.loads((run/'inputs.json').read_text())
    checks={name:sha((run/'images'/name).read_bytes())==m['sha256'] for name,m in manifest['images'].items()}
    code={name:sha((ROOT/name).read_bytes())==digest for name,digest in manifest['implementation_sha256'].items()}
    declaration=json.loads((run/'building_input.json').read_text())
    assert declaration==manifest['building_input']['declaration']
    assert sha((run/'building_input.json').read_bytes())==manifest['building_input']['raw_sha256']
    calls={};counts=Counter();views=[];transport=[];input_delivered=False
    stored={sha(p.read_bytes()):str(p.relative_to(run)) for p in run.rglob('*.png') if 'execution_audit' not in str(p)}
    stream=run/'agent_stream.jsonl'
    raw_stream=stream.read_text() if stream.exists() else gzip.decompress(stream.with_suffix('.jsonl.gz').read_bytes()).decode()
    for line in raw_stream.splitlines():
        event=json.loads(line)
        for block in event.get('message',{}).get('content',[]):
            if not isinstance(block,dict):continue
            if block.get('type')=='tool_use':
                calls[block['id']]=block;counts[block['name']]+=1
            if block.get('type')!='tool_result':continue
            call=calls.get(block.get('tool_use_id'))
            if not call:continue
            content=block.get('content',[])
            if not isinstance(content,list):continue
            if call['name'].endswith('__inputs'):
                for c in content:
                    if c.get('type')=='text':
                        actual=json.loads(c['text'])
                        input_delivered=actual['building_input']['declaration']==declaration and actual['images']==manifest['images']
            images=[base64.b64decode(c['source']['data']) for c in content if c.get('type')=='image']
            if call['name'].endswith('__view_image') and images:
                a=call['input'];pic=Image.open(run/'images'/a['name']).convert('RGB')
                region=a.get('box') or [0,0,pic.width,pic.height]
                if a.get('box'):pic=pic.crop(a['box'])
                scale=a.get('display_scale',1)
                if scale==1:pic.thumbnail((1600,1600))
                else:
                    scale=min(scale,1600/max(pic.size))
                    pic=pic.resize(tuple(max(1,round(v*scale)) for v in pic.size),Image.Resampling.NEAREST)
                if a.get('coordinate_grid',True):pic,_=coordinate_grid_view(pic,region)
                expected=io.BytesIO();pic.save(expected,'PNG')
                actual=Image.open(io.BytesIO(images[0])).convert('RGB')
                same_size=actual.size==pic.size
                mae=float(np.abs(np.asarray(actual,dtype=float)-np.asarray(pic,dtype=float)).mean()) if same_size else None
                exact=images[0]==expected.getvalue()
                transport.append({'tool':call['name'],'input':a,'exact':exact,
                    'returned_encoding':Image.open(io.BytesIO(images[0])).format,'same_size':same_size,
                    'mean_absolute_channel_error':mae,
                    'consistent_with_expected_render':exact or (same_size and mae<6),
                    'note':'JPEG recompression is lossy; measured pixel agreement is not byte identity' if not exact else 'exact PNG'})
                views.append(a['name'])
            else:
                for image in images:
                    digest=sha(image)
                    transport.append({'tool':call['name'],'exact':digest in stored,'consistent_with_expected_render':digest in stored,'stored_png':stored.get(digest)})
    replay=[]
    for candidate in sorted(run.glob('candidate_*/source_model.json')):
        directory=candidate.parent
        proposal=json.loads((directory/'proposal.json').read_text())
        report=json.loads((directory/'report.json').read_text())
        compact=directory/'parametric_plan.json'
        matches=[d for d in run.glob('parametric_drafts/*.json') if expand_parametric_proposal(json.loads(d.read_text()))==proposal]
        expanded=expand_parametric_proposal(json.loads(compact.read_text())) if compact.exists() else None
        item={'candidate':directory.name,'compact_saved_with_candidate':compact.exists(),
              'matching_raw_drafts':[str(d.relative_to(run)) for d in matches],
              'expanded_proposal_matches':expanded==proposal if compact.exists() else bool(matches)}
        replay_dir=out/directory.name
        fresh=export_source_proposal(proposal,replay_dir,provenance=report.get('provenance'))
        item.update(source_matches=json.loads((replay_dir/'source_model.json').read_text())==json.loads(candidate.read_text()),
            source_sha256=fresh.get('source_model_sha256'),validation=report.get('source_geometry_self_consistency'),counts=report.get('counts'))
        replay.append(item)
    receipt=json.loads((run/'agent_receipt.json').read_text())
    result={'input_hashes':checks,'code_hashes':code,'input_declaration_delivered':input_delivered,
        'actual_model':receipt.get('actual_model'),'requested_model':receipt.get('requested_model'),
        'elapsed_seconds':receipt.get('elapsed_seconds'),'calls':dict(counts),'images_viewed':sorted(set(views)),
        'images_unexamined':sorted(set(manifest['images'])-set(views)), 'image_transport':transport,
        'source_replay':replay,'input_condition':'developer-prepared mesh views; not autonomous GLB observation',
        'fidelity_or_real_interior_truth':'not established by this audit'}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert all(checks.values()) and all(code.values()) and input_delivered
    assert all(t['consistent_with_expected_render'] for t in transport),transport
    assert all(r['expanded_proposal_matches'] and r['source_matches'] for r in replay),replay
    print(json.dumps({'actual_model':result['actual_model'],'tool_calls':sum(counts.values()),
                      'transport_images':len(transport),'replayed_candidates':len(replay),'passed':True}))

if __name__=='__main__':main()
