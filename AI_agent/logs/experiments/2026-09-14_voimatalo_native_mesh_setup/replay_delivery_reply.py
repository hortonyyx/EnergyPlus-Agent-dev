"""Replay the real large handoff through MCP after response-size fix, without a model."""
from pathlib import Path
import asyncio,json,shutil,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters,stdio_client
run=ROOT/'AI_agent/logs/experiments/2026-09-14_voimatalo_native_mesh_run01'
out=run/'delivery_reply_replay';out.mkdir(exist_ok=False)
original=run/'candidate_02';shutil.copytree(original,out/'candidate_01')
(out/'images').mkdir();(out/'inputs.json').write_text(json.dumps({'images':{},'scope':'Offline replay of actual source handoff; no generation or model call.'}))
async def main():
 params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'scripts/tool_scripts/run_bim_agent.py'),'serve',str(out)],cwd=str(ROOT))
 async with stdio_client(params) as (read,write):
  async with ClientSession(read,write) as session:
   await session.initialize();result=await session.call_tool('finish_bim',{'candidate':'candidate_01'})
   assert not result.isError,result
   reply=result.structuredContent if result.structuredContent is not None else json.loads(result.content[0].text)
   full=json.loads((out/'delivery.json').read_text());before=json.loads((run/'delivery.json').read_text())
   assert reply['response_compacted'] and len(json.dumps(reply))<20000
   for field in ['source_model_sha256','source_validation','counts','unbuilt_openings','assumptions','generation','drawing_fidelity']:
    assert reply[field]==full[field]==before[field],field
   assert (out/'candidate_01/source_model.json').read_bytes()==(original/'source_model.json').read_bytes()
   assert 'opening_inventory' in full and 'facade_inventory' in full
   record={'model_calls':0,'source_unchanged':True,'actual_mcp_finish_succeeded':True,'reply_characters':len(json.dumps(reply)),
           'full_report_characters':len(json.dumps(full)),'counts':reply['counts'],'reply':reply}
   (out/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
   print(json.dumps({k:v for k,v in record.items() if k!='reply'}))
asyncio.run(main())
