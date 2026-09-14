"""Narrow target-model observation after aspect fix; no previous geometry/angle supplied."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from scripts.tool_scripts.run_bim_agent import subscription,dump,digest
from scripts.tool_scripts.bim_agent_mesh import freeze_mesh
from scripts.tool_scripts.bim_agent_inputs import freeze_building_input
run=ROOT/'AI_agent/logs/experiments/2026-09-14_voimatalo_native_alignment_run01';run.mkdir(exist_ok=False)
(run/'images').mkdir()
mesh=freeze_mesh(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/input.glb',run)
building=freeze_building_input(Path(__file__).parent/'building_input.json',run,{})
question='Determine a defensible local xy yaw to align the main walls of this original textured building mesh. Choose your own views and metric span, then measure well-separated surface points tied to the SAME visibly straight facade/roof edge to verify direction; verify an independent edge or an aligned view. Use the returned point differences and horizontal heading rather than trusting apparent pixel slope alone. Explain the chosen coordinate transform and uncertainty. Do not model interiors or create a BIM; this is a bounded native geometry observation. No earlier views, candidate, alignment angle or numerical answer are supplied.'
code_paths=['scripts/tool_scripts/run_bim_agent.py','scripts/tool_scripts/bim_agent_mesh.py','src/agent/geometry/mesh_observation.py','scripts/tool_scripts/bim_agent_guidance.py','scripts/tool_scripts/bim_agent_inputs.py']
manifest={'images':{},'mesh_input':mesh,'building_input':building,'scope':question,'input_mode':'native_mesh_alignment_observation','source_input_mode':'native_mesh_with_building_declaration','deadline_epoch':time.time()+480,'implementation_sha256':{p:digest(ROOT/p) for p in code_paths},'only_input':'Original single-building GLB and same user building declaration; no previous candidate, views, angle or evaluation.'}
dump(run/'inputs.json',manifest)
record=subscription(run,question,model='sonnet',name='agent',timeout=480,readonly=True,effort='medium',receipt_context={'experiment':'post-aspect-fix alignment observation','developer_selected_subtask':True,'previous_angle_or_candidate_supplied':False})
dump(run/'summary.json',{'actual_model':record.get('actual_model'),'elapsed_seconds':record['elapsed_seconds'],'completed':bool(record.get('result')) and not record['result'].get('is_error',False),'bim_generation':False,'developer_selected_subtask':True,'changes_vs_full_run':['narrow alignment task','Sonnet instead of exploratory Opus','equal metric pixel aspect','computed point-pair heading'],'controlled_ablation':False})
print(json.dumps(json.loads((run/'summary.json').read_text()),ensure_ascii=False))
