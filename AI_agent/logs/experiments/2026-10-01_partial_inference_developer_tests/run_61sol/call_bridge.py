import json, subprocess, sys
from pathlib import Path
run=Path('/tmp/ep-partial-developer-tests-20261001/run_61sol')
name=sys.argv[1]
request=run/(name+'.json')
r=subprocess.run(['/opt/venv/bin/python','/tmp/ep-partial-developer-tests-20261001/runtime_61sol/scripts/tool_scripts/bim_agent_bridge.py','--run',str(run),str(request)],capture_output=True,text=True)
(run/(name+'_reply.json')).write_text(r.stdout)
if r.stderr: print(r.stderr)
try: d=json.loads(r.stdout)
except Exception: print(r.stdout);sys.exit(1)
print('RECORD',d.get('record'),'COMPLETED',d.get('completed'))
lines=[]
for reply in d.get('replies',[]):
 print('TOOL',reply.get('tool'),'ERROR',reply.get('isError'))
 if reply.get('structuredContent') is not None:
  lines.append({'tool':reply['tool'],'value':reply['structuredContent']})
  print(json.dumps(reply['structuredContent'],indent=2))
 for c in reply.get('content',[]):
  if c.get('type')=='text':
   try: v=json.loads(c['text'])
   except Exception: v=c['text']
   lines.append({'tool':reply['tool'],'value':v})
   if isinstance(v,dict) and reply['tool']=='view_mesh':
    print(json.dumps({k:v.get(k) for k in ['observation','bounds','yaw_degrees_counterclockwise_about_positive_z','resolution_px','camera_request','artifacts','remaining_seconds']},indent=2))
   else: print(json.dumps(v,indent=2) if isinstance(v,dict) else v)
  else: print(c)
(run/(name+'_decoded.json')).write_text(json.dumps(lines,indent=2))
