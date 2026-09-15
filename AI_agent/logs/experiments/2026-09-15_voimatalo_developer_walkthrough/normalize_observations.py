"""Convert observed pixel boxes to endpoint intervals for the source assembler.

The observation producer's span_m field is a width, not an absolute interval.
Retain that original and compute the interval from the frozen camera mapping.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
HERE = Path(__file__).resolve().parent
source = HERE / 'aperture_observations/openings.json'
target = HERE / 'assembly_observations.json'
assert not target.exists()
rows = json.loads(source.read_text())
planes = {'west_main':'west','north_main':'north','court_long_main':'court_long',
          'court_long_south_segment':'court_long','court_short_main':'court_short','court_corner_y':'court_corner_y'}
result = []
for row in rows:
    meta = json.loads((HERE / 'evidence_01' / (row['view']+'.json')).read_text())
    m = meta['pixel_center_mapping']
    origin, dx, dy = [np.array(m[k]) for k in ('top_left_pixel_center_plane_xyz','column_step_world_xyz','row_step_world_xyz')]
    left, top, right, bottom = row['pixel_box']
    assert row['pixel_box_convention']=='left/top inclusive; right/bottom exclusive'
    a = origin + (left-.5)*dx + (top-.5)*dy
    b = origin + (right-.5)*dx + (bottom-.5)*dy
    axis = int(np.argmax(abs(dx)))
    span = sorted([float(a[axis]),float(b[axis])])
    zz = sorted([float(a[2]),float(b[2])])
    assert abs((span[1]-span[0])-row['span_m']) < 1e-4
    assert np.allclose(zz,row['z_m'],atol=1e-4)
    result.append({**row,'observation_plane_key':row['plane_key'],'plane_key':planes[row['plane_key']],
                   'observed_span_width_m':row['span_m'],'span_m':span,'z_m':zz})
pending = json.loads((HERE/'aperture_observations/unresolved_observations.json').read_text())
target.write_text(json.dumps({'openings':result,'unresolved_observations':pending,
    'normalization':{'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'method':'pixel-box edges through frozen orthographic camera; retain width and resolve local plane names',
        'source_pixels_modified':False,'opening_count_preserved':len(rows)}},ensure_ascii=False,indent=2)+'\n')
print(f'Converted {len(result)} pixel boxes; retained {len(pending)} unresolved/excluded observations')
