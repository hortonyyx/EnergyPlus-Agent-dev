"""Explicit rigid registration of a source BIM to one original GLB asset.

This records an agent's interpretation; neither validation nor projection fits
the candidate to the mesh or establishes surveyed placement.
"""
from __future__ import annotations

import copy
import math
import re

import numpy as np
from PIL import ImageDraw


def validate_mesh_frame(value):
    fields = {'mesh_sha256', 'yaw_degrees', 'translation_m', 'reason', 'source_refs'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f'mesh_frame requires exactly {sorted(fields)}')
    if not isinstance(value['mesh_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['mesh_sha256']):
        raise ValueError('mesh_frame.mesh_sha256 must identify the original GLB')
    numbers = [value['yaw_degrees']]
    translation = value['translation_m']
    if not isinstance(translation, list) or len(translation) != 3:
        raise ValueError('mesh_frame.translation_m must contain three metres')
    numbers += translation
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in numbers):
        raise ValueError('mesh_frame rotation and translation must be finite numbers')
    if not isinstance(value['reason'], str) or not value['reason'].strip():
        raise ValueError('mesh_frame.reason must explain the placement')
    refs = value['source_refs']
    if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or not r.strip() for r in refs):
        raise ValueError('mesh_frame.source_refs must cite observations or an explicit assumption')
    return copy.deepcopy(value)


def rotate_points(points, yaw):
    angle = math.radians(yaw)
    c, s = math.cos(angle), math.sin(angle)
    return np.asarray(points, dtype=float) @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


def source_to_observation(points, frame, observation_yaw):
    """source = R(frame.yaw) * original_Zup + translation, no scale change."""
    frame = validate_mesh_frame(frame)
    return rotate_points(np.asarray(points, dtype=float) - frame['translation_m'],
                         observation_yaw - frame['yaw_degrees'])


def observation_to_source(points, frame, observation_yaw):
    frame = validate_mesh_frame(frame)
    return rotate_points(points, frame['yaw_degrees'] - observation_yaw) + frame['translation_m']


def render_mesh_bim_overlay(picture, observation, source, *, floor_id=None, exterior_only=True):
    """Project actual source edges onto an unchanged mesh rendering as X-ray lines."""
    from src.agent.geometry.source_model import _digest

    expected = _digest({k: v for k, v in source.items() if k != 'source_model_sha256'})
    if source.get('source_model_sha256') != expected:
        raise ValueError('source BIM digest mismatch')
    frame = validate_mesh_frame(source.get('mesh_frame'))
    if frame['mesh_sha256'] != observation['mesh_sha256']:
        raise ValueError('candidate frame and mesh observation refer to different assets')
    width, height = (observation['resolution_px'][k] for k in ('width', 'height'))
    if picture.size != (width, height):
        raise ValueError('mesh observation image dimensions changed')
    floor_ids = {f['id'] for f in source['floors']}
    if floor_id is not None and floor_id not in floor_ids:
        raise ValueError('unknown floor_id')
    spaces = {s['id'] for s in source['spaces'] if floor_id is None or s['floor_id'] == floor_id}
    bounds = [b for b in source['boundaries'] if b['space_id'] in spaces
              and b['geometry_type'] == 'wall'
              and (not exterior_only or not b.get('adjacent_space_ids'))]
    openings = [o for o in source['openings'] if spaces.intersection(o['space_ids'])
                and (not exterior_only or o['exterior'])]
    yaw = observation['source_coordinate_transform']['yaw_degrees_counterclockwise_about_positive_z']
    camera = observation['camera']
    target = np.asarray(camera['target'])
    right, up = np.asarray(camera['screen_right']), np.asarray(camera['screen_up'])
    span = observation['view_span_m']
    rendered = picture.convert('RGB').copy()
    draw = ImageDraw.Draw(rendered)
    rows = []
    for obj in bounds + openings:
        world = source_to_observation(obj['vertices'], frame, yaw)
        delta = world - target
        screen = np.column_stack(((delta @ right / span['width'] + .5) * width - .5,
                                  (.5 - delta @ up / span['height']) * height - .5))
        kind = obj.get('geometry_type', obj.get('kind'))
        color = {'window': '#00b85b', 'door': '#ff8800', 'passage': '#ff8800'}.get(kind, '#dc24c5')
        points = [tuple(p) for p in screen.tolist()]
        draw.line(points + points[:1], fill=color, width=2)
        rows.append({'id': obj['id'], 'kind': kind, 'observation_xyz': world.tolist(),
                     'projected_pixels': screen.tolist()})
    draw.rectangle((0, 0, min(width, 760), 31), fill='white')
    draw.text((6, 4), 'SOURCE BIM X-RAY: magenta walls / green windows / orange doors', fill='black')
    draw.text((6, 17), 'Hidden source edges shown; mesh gaps are missing evidence. No automatic fitting.', fill='black')
    return rendered, {'mesh_sha256': observation['mesh_sha256'], 'source_model_sha256': expected,
        'mesh_frame': frame, 'floor_id': floor_id, 'exterior_only': exterior_only,
        'projection': 'orthographic source edge X-ray over unchanged original textured mesh image',
        'occlusion': 'source edges are not depth-tested; hidden edges remain visible',
        'fitted_to_mesh': False, 'fidelity': 'not_evaluated',
        'boundary_count': len(bounds), 'opening_count': len(openings), 'objects': rows}
