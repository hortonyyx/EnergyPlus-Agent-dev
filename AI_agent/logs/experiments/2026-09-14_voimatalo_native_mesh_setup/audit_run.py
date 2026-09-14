"""Audit native asset admission, actual tool images, mesh renders and source replay."""
from pathlib import Path
import base64,gzip,hashlib,io,json,sys,tempfile
from collections import Counter
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation
from src.agent.execution.source_proposal import export_source_proposal

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 run=Path(sys.argv[1]).resolve();out=run/'execution_audit';out.mkdir(exist_ok=False)
 manifest=json.loads((run/'inputs.json').read_text())
 asset=run/manifest['mesh_input']['frozen_path'];mesh=MeshObservation(asset)
 checks={'asset_bytes':sha(asset.read_bytes())==manifest['mesh_input']['sha256'],
         'no_prepared_images':manifest['images']=={},'no_seed':'seed' not in manifest,
         'declaration_bytes':sha((run/'building_input.json').read_bytes())==manifest['building_input']['raw_sha256']}
 code={p:sha((ROOT/p).read_bytes())==h for p,h in manifest['implementation_sha256'].items()}
 raw=run/'agent_stream.jsonl'
 stream=raw.read_text() if raw.exists() else gzip.decompress(raw.with_suffix('.jsonl.gz').read_bytes()).decode()
 calls={};counts=Counter();transport=[];delivered=False
 pngs={sha(p.read_bytes()):p for p in run.rglob('*.png')}
 for line in stream.splitlines():
  event=json.loads(line)
  for block in event.get('message',{}).get('content',[]):
   if not isinstance(block,dict):continue
   if block.get('type')=='tool_use':calls[block['id']]=block;counts[block['name']]+=1
   if block.get('type')!='tool_result':continue
   call=calls.get(block.get('tool_use_id'));content=block.get('content',[])
   if not call or not isinstance(content,list):continue
   texts=[]
   for c in content:
    if c.get('type')=='text':
     try:texts.append(json.loads(c['text']))
     except (ValueError,TypeError):pass
   if call['name'].endswith('__inputs'):
    delivered=any(isinstance(t,dict) and t.get('mesh_input')==manifest['mesh_input'] and t.get('images')=={} and t.get('building_input')==manifest['building_input'] for t in texts)
   for c in content:
    if c.get('type')!='image':continue
    b=base64.b64decode(c['source']['data']);exact=pngs.get(sha(b));expected=exact
    if not expected:
     obs=next((t.get('observation') for t in texts if isinstance(t,dict) and t.get('observation')),None)
     if not obs and call['name'].endswith('__view_mesh_observation'):obs=call['input']['observation']
     if obs:expected=run/'mesh_observations'/f'{obs}.png'
    item={'tool':call['name'],'exact_png':bool(exact),'expected':str(expected.relative_to(run)) if expected else None}
    if expected:
     a=Image.open(io.BytesIO(b)).convert('RGB');e=Image.open(expected).convert('RGB')
     same=a.size==e.size;mae=float(np.abs(np.asarray(a,dtype=float)-np.asarray(e,dtype=float)).mean()) if same else None
     item.update(same_size=same,mean_absolute_channel_error=mae,consistent=bool(exact) or (same and mae<6),encoding=Image.open(io.BytesIO(b)).format)
    else:item['consistent']=False
    transport.append(item)
 renders=[];measurements=[]
 logs=[json.loads(line) for line in (run/"tools.jsonl").read_text().splitlines()]
 with tempfile.TemporaryDirectory(prefix='native-mesh-replay-') as tmp:
  for path in sorted((run/'mesh_observations').glob('mesh_*.json')):
   m=json.loads(path.read_text());yaw=m['source_coordinate_transform']['yaw_degrees_counterclockwise_about_positive_z'];cam=m['camera'];size=m['resolution_px'];span=m['view_span_m']
   pic,_=mesh.render(Path(tmp)/path.stem,eye=cam['eye'],target=cam['target'],width_m=span['width'],height_m=span['height'],width_px=size['width'],height_px=size['height'],yaw_degrees=yaw,bounds=m['selection_bounds'])
   exact=sha((Path(tmp)/path.stem).with_suffix('.png').read_bytes())==sha(path.with_suffix('.png').read_bytes())
   renders.append({'observation':path.stem,'exact_replay':exact,'mesh_hash':m['mesh_sha256'],'yaw':yaw})
   for log in logs:
    if log['action']=='measure_mesh_pixels' and log['data']['observation']==path.stem:
     data=log['data'];fresh=mesh.pixel_query(Path(tmp)/path.stem,data['pixels']);old=data['result']
     measurements.append({'observation':path.stem,'points':len(data['pixels']),'queries_match':fresh['queries']==old['queries'],'distances_match':fresh['first_two_distance']==old['first_two_distance']})
 source=[]
 for path in sorted(run.glob('candidate_*/source_model.json')):
  proposal=json.loads((path.parent/'proposal.json').read_text());report=json.loads((path.parent/'report.json').read_text())
  export_source_proposal(proposal,out/path.parent.name,provenance=report.get('provenance'))
  source.append({'candidate':path.parent.name,'source_matches':json.loads((out/path.parent.name/'source_model.json').read_text())==json.loads(path.read_text())})
 result={'input_checks':checks,'input_manifest_delivered':delivered,'code_hashes':code,'tool_calls':dict(counts),'image_transport':transport,'mesh_render_replay':renders,'surface_measurement_replay':measurements,'source_replay':source,'note':'PNG exact or measured JPEG approximation; these checks do not establish architectural fidelity.'}
 result['passed']=all(checks.values()) and all(code.values()) and delivered and all(t['consistent'] for t in transport) and all(r['exact_replay'] for r in renders) and all(s['source_matches'] for s in source) and all(m['queries_match'] and m['distances_match'] for m in measurements)
 (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'passed':result['passed'],'tools':sum(counts.values()),'images':len(transport),'mesh_views':len(renders),'candidates':len(source)}))
 assert result['passed']
if __name__=='__main__':main()
