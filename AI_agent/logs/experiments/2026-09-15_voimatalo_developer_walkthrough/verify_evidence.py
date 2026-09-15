"""Independent section check and offline evidence-page inspection."""
import json
from pathlib import Path
import sys
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
out = Path(sys.argv[1]).resolve()
manifest = json.loads((out / 'manifest.json').read_text())
direction = json.loads((out / 'direction.json').read_text())
records = json.loads((out / 'sections.json').read_text())
scene = trimesh.load(manifest['input']['mesh_path'], force='scene', process=False)
vertices, faces, offset = [], [], 0
angle = np.radians(direction['used_yaw_degrees'])
rotation = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
for node in scene.graph.nodes_geometry:
    transform, geometry = scene.graph[node]
    mesh = scene.geometry[geometry]
    world = trimesh.transform_points(mesh.vertices, transform)
    local = np.column_stack((world[:, 0], -world[:, 2], world[:, 1])) @ rotation.T
    vertices.append(local)
    faces.append(mesh.faces + offset)
    offset += len(local)
mesh = trimesh.Trimesh(vertices=np.concatenate(vertices), faces=np.concatenate(faces), process=False)
results = []
for record in records['sections']:
    lines, ids = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, record['z_m']], return_faces=True)
    actual = {r['face_id']: np.asarray(r['endpoints_xyz_m']) for r in record['segments']}
    assert set(actual) == set(ids), (record['z_m'], len(actual), len(ids))
    errors = [min(np.max(abs(actual[int(i)] - line)), np.max(abs(actual[int(i)] - line[::-1]))) for i, line in zip(ids, lines)]
    assert max(errors) < 1e-8
    results.append({'z_m': record['z_m'], 'segments': len(ids), 'max_endpoint_error_m': float(max(errors))})

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1400, 'height': 1000})
    errors, external = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: external.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    page.context.set_offline(True)
    page.goto((out / 'index.html').as_uri(), wait_until='load')
    images = page.locator('img').evaluate_all('(items)=>items.map(i=>({src:i.getAttribute("src"),loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight}))')
    assert len(images) == 8 and all(i['loaded'] for i in images)
    assert not errors and not external
    page.screenshot(path=str(out / 'page_qa.png'), full_page=True)
    browser.close()
report = {'status': 'pass', 'independent_section_engine': 'trimesh.intersections.mesh_plane', 'sections': results,
          'offline_page_images': images, 'page_errors': errors, 'external_requests': external,
          'scope': 'Section geometry and saved page loading only; not BIM fidelity or method transfer.'}
(out / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'pass', 'sections': len(results), 'images': len(images)}))
