"""Additional developer observations, selected after inspecting the whole asset."""
from pathlib import Path
import json
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation

out = HERE / 'additional_views'
out.mkdir(exist_ok=False)
mesh = MeshObservation(ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb')
yaw = json.loads((HERE / 'evidence_01/direction.json').read_text())['used_yaw_degrees']
operations = [
    dict(name='annex_east', eye=[80,-6,4], target=[13,-6,4], width_m=35, height_m=11,
         width_px=1200, height_px=377, bounds=[[9,-24,-1],[16,10,10]]),
    dict(name='ground_west', eye=[-100,-3,3], target=[0,-3,3], width_m=70, height_m=8,
         width_px=1200, height_px=137, bounds=None),
    dict(name='roof_court', eye=[100,-11,27], target=[0,-11,27], width_m=47, height_m=8,
         width_px=1200, height_px=204, bounds=[[-25,-36,24],[8,9,36]]),
]
for row in operations:
    args = {key: value for key, value in row.items() if key != 'name'}
    mesh.render(out / row['name'], yaw_degrees=yaw, **args)
queries = {}
for name, points in [('street', [[780,100],[780,135],[496,215]]), ('courtyard', [[296,216],[766,111]])]:
    queries[name] = mesh.pixel_query(HERE / 'evidence_01' / name, points)
(out / 'operations.json').write_text(json.dumps({'mode':'developer_selected_observations', 'operations': operations, 'yaw_degrees': yaw,
    'queries': queries, 'notes':['Three early street pixel picks missed the mesh and supplied no coordinates.',
    'Courtyard chimney and northern roof point picks hit real surfaces; they do not establish full box dimensions.',
    'Bounds select triangle centroids and may reveal rear surfaces.']}, indent=2) + '\n')
