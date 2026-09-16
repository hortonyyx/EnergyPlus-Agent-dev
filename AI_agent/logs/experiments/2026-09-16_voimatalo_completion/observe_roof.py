"""New raw-asset roof observations; diagnostic sections do not create slabs."""
from pathlib import Path
import json, runpy, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = HERE.parent / '2026-09-15_voimatalo_developer_walkthrough'
sys.path.insert(0, str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation

out = HERE / 'roof'
out.mkdir(exist_ok=False)
mesh = MeshObservation(ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb')
yaw = json.loads((OLD / 'evidence_01/direction.json').read_text())['used_yaw_degrees']
views = [
    ('west', [-100,-3,28], [0,-3,28], 68, 13, None),
    ('north', [2,100,28], [2,0,28], 42, 13, None),
    ('court_short', [10,-100,28], [10,10,28], 25, 13, [[0,6,24],[25,30,36]]),
    ('south_box', [80,-26,30], [0,-26,30], 18, 10, [[-16,-35,24],[2,-21,36]]),
    ('top', [2,-3,100], [2,-3,28], 43, 67, [[-18,-36,26],[24,30,36]]),
]
for name, eye, target, width, height, bounds in views:
    scale = 1600 / max(width, height)
    mesh.render(out / name, eye=eye, target=target, width_m=width, height_m=height,
                width_px=round(width*scale), height_px=round(height*scale), yaw_degrees=yaw, bounds=bounds)
triangles = np.concatenate([p.vertices[p.faces] for p in mesh._parts])
a = np.radians(yaw)
triangles = triangles @ np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1]])
section = runpy.run_path(str(OLD / 'prepare_evidence.py'))['section']
rows = []
canvas = Image.new('RGB', (1440,1080),'white'); d = ImageDraw.Draw(canvas)
for i,z in enumerate([26.5,27.9,29.0,30.5,31.5,33.0]):
    segments = section(triangles,z); rows.append({'z_m':z,'segments':segments})
    x0,y0=30+(i%3)*480,45+(i//3)*530
    def pt(p): return (x0+(p[0]+18)*7,y0+(30-p[1])*7)
    d.text((x0,y0-25),f'Raw sections z={z:g} m (NOT slabs)',fill='black')
    for x in range(-15,25,5):
        d.line([pt([x,-35]),pt([x,30])],fill='#ddd'); d.text(pt([x,30]),str(x),fill='#777')
    for y in range(-35,31,5):
        d.line([pt([-18,y]),pt([24,y])],fill='#ddd'); d.text(pt([24,y]),str(y),fill='#777')
    for s in segments: d.line([pt(p) for p in s['endpoints_xyz_m']],fill='#125477',width=2)
canvas.save(out/'sections.png')
(out/'sections.json').write_text(json.dumps({'mesh_sha256':mesh.mesh_sha256,'yaw_degrees':yaw,'sections':rows},indent=2)+'\n')
(out/'operations.json').write_text(json.dumps({'views':views,'yaw_degrees':yaw,'source':'original single-building GLB only','mode':'developer_selected_observations'},indent=2)+'\n')
print('Saved five roof views and six diagnostic sections')
