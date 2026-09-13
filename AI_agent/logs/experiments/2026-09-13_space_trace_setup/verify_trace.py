"""Verify selected trace transport and geometric replay after the observer ends."""
import argparse
import base64
import gzip
import io
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from PIL import Image, ImageChops
from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.geometry.space_trace import render_space_trace

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);args=parser.parse_args()
    run=args.run.resolve();assert (run/'response.json').exists()
    child=run/'detail_01';manifest=json.loads((child/'inputs.json').read_text())
    assert digest(child/'question.txt')==manifest['question_sha256']
    for name,row in manifest['images'].items():assert digest(child/'images'/name)==row['sha256']
    receipt=json.loads((run/'detail_01_receipt.json').read_text())
    assert digest(child/'inputs.json')==receipt['observation_source']['input_sha256']
    assert not (child/'seed').exists() and not list(child.glob('candidate_*'))
    regions=[]
    from src.agent.geometry.pixel_region import render_pixel_region
    for path in sorted((child/'pixel_regions').glob('region_*.json')):
        m=json.loads(path.read_text())
        assert m['image_sha256']==digest(child/'images'/m['name'])
        with Image.open(child/'images'/m['name']) as raw_image:
            expected, metadata=render_pixel_region(raw_image,**{k:m[k] for k in ['seed_pixel','background_rgb','tolerance','simplify_pixels']})
        actual=Image.open(child/m['region_image']).convert('RGB')
        assert all(m[k]==v for k,v in metadata.items())
        assert actual.size==expected.size and ImageChops.difference(actual,expected).getbbox() is None
        regions.append({'region_id':m['region_id'],'seed_pixel':m['seed_pixel'],'pixel_count':m['region_pixel_count'],'replay_matches':True})
    rows=[]
    for p in sorted((child/'space_traces').glob('trace_*.json')):
        m=json.loads(p.read_text());assert m['image_sha256']==digest(child/'images'/m['name'])
        with Image.open(child/'images'/m['name']) as original:
            replay,meta=render_space_trace(original,**{k:m[k] for k in ['polygon_pixels','openings','x_anchors','y_anchors','basis']})
        actual=Image.open(child/m['trace_image'])
        assert all(m[k]==v for k,v in meta.items())
        assert actual.size==replay.size and ImageChops.difference(actual.convert('RGB'),replay.convert('RGB')).getbbox() is None
        rows.append({'trace':p.stem,'geometry_errors':m['geometry_errors'],'replay_matches':True})
    p=run/'detail_01_stream.jsonl'
    raw=p.read_text() if p.exists() else gzip.decompress(p.with_suffix('.jsonl.gz').read_bytes()).decode()
    calls={};views=[];names=[]
    for line in raw.splitlines():
        event=json.loads(line)
        for b in event.get('message',{}).get('content',[]):
            if b.get('type')=='tool_use':calls[b['id']]=b;names.append(b['name'].split('__')[-1])
            if b.get('type')!='tool_result' or b.get('is_error'):continue
            call=calls.get(b.get('tool_use_id'),{})
            if not call.get('name','').endswith(('__preview_space_trace','__view_space_trace','__view_pixel_region')):continue
            m=json.loads(next(i['text'] for i in b['content'] if i['type']=='text'))
            encoded=next(i['source']['data'] for i in b['content'] if i['type']=='image')
            returned=Image.open(io.BytesIO(base64.b64decode(encoded))).convert('RGB')
            saved=Image.open(child/m.get('trace_image',m.get('region_image'))).convert('RGB')
            assert returned.size==saved.size and ImageChops.difference(returned,saved).getbbox() is None
            views.append({'tool':call['name'],'artifact':m.get('trace_id',m.get('region_id')),'image_matches':True})
    assert set(names)<={'inputs','view_image','pixel_profile','view_pixel_profile','map_pixels','map_dimension_chain','preview_space_trace','view_space_trace','select_space_trace','view_pixel_region'}
    selected=None
    if (child/'trace_selection.json').exists():
        selected=json.loads((child/'trace_selection.json').read_text());assert selected['trace_sha256']==digest(child/'space_traces'/f"{selected['trace_id']}.json")
    dump(run/'trace_verification.json',{'source_isolation_and_hashes_match':True,'traces':rows,'pixel_regions':regions,'returned_images':views,'selection':selected,'tool_names':names,'limits':'Geometry/transport only; no original wall or door semantic certification.'})
    print(json.dumps({'traces':len(rows),'returned_images':len(views),'selected':selected}))
